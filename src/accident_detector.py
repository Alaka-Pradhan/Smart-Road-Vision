"""
Possible Accident Detection Module for Smart Road Vision.
Combines Dual-Engine Detection:
1. Deep Learning Vision Engine: Fine-tuned Ultralytics YOLO11x (Enos-123)
   trained specifically on traffic accident surveillance datasets. Runs asynchronously
   in a dedicated worker thread to maintain smooth real-time FPS on CPU.
2. Kinematic & Trajectory Heuristic Engine: Sudden deceleration, multi-vehicle proximity,
   and sustained roadway stoppage verification.
"""

import os
import math
import time
import queue
import logging
import threading
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

from .tracker import TrackedObject

logger = logging.getLogger(__name__)


class PossibleAccidentDetector:
    """
    Dual-engine accident detector combining fine-tuned YOLO11x deep learning
    with trajectory kinematics for intelligent road safety monitoring.
    """

    def __init__(self, config: Dict[str, Any]):
        self._alerted_accident_ids = set()
        self._alerted_locations: List[Tuple[float, float, float]] = []  # (cx, cy, timestamp)
        self._frame_count = 0
        self._cooldown_seconds = 8.0

        # AI Worker Thread state
        self.ai_model = None
        self.ai_classes = {}
        self._latest_ai_detections: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._ai_frame_queue: queue.Queue = queue.Queue(maxsize=1)
        self._stop_worker = threading.Event()
        self._ai_worker_thread: Optional[threading.Thread] = None

        self.update_config(config)

    def update_config(self, config: Dict[str, Any]):
        """Updates detector parameters and initializes/refreshes AI model."""
        cfg = config.get("accident_detection", {})
        self.enabled = cfg.get("enabled", True)
        self.use_ai_model = cfg.get("use_ai_model", True)
        self.ai_model_path = cfg.get("ai_model_path", "models/accident_yolo11x.pt")
        self.ai_conf_threshold = cfg.get("ai_confidence_threshold", 0.30)
        self.ai_imgsz = cfg.get("ai_imgsz", 320)
        self.ai_scan_interval = cfg.get("ai_scan_interval_frames", 15)

        # Heuristic kinematics
        self.speed_drop_ratio = cfg.get("sudden_stop_speed_drop_ratio", 0.75)
        self.min_stationary_frames = cfg.get("min_frames_stationary", 18)
        self.proximity_distance_px = cfg.get("proximity_distance_px", 55)
        self.min_pre_speed = cfg.get("min_pre_accident_speed_px", 5.0)

        # Lazy init AI model
        if self.enabled and self.use_ai_model and self.ai_model is None:
            self._init_ai_model()

    def _init_ai_model(self):
        """Loads the fine-tuned YOLO11x model and starts async inference worker."""
        if not os.path.exists(self.ai_model_path):
            logger.info(f"YOLO11x accident model not found at {self.ai_model_path}. Running heuristic engine.")
            return

        try:
            from ultralytics import YOLO
            logger.info(f"Loading YOLO11x Accident Detection weights from {self.ai_model_path}...")
            self.ai_model = YOLO(self.ai_model_path)
            self.ai_classes = self.ai_model.names or {0: "accident", 1: "vehicle"}
            logger.info(f"YOLO11x loaded successfully. Classes: {self.ai_classes}")

            # Start background async worker
            if self._ai_worker_thread is None or not self._ai_worker_thread.is_alive():
                self._stop_worker.clear()
                self._ai_worker_thread = threading.Thread(
                    target=self._ai_worker_loop,
                    name="YOLO11x-Accident-Worker",
                    daemon=True
                )
                self._ai_worker_thread.start()
                logger.info("Asynchronous YOLO11x accident worker thread started.")
        except Exception as e:
            logger.error(f"Failed to initialize YOLO11x accident model: {e}")
            self.ai_model = None

    def _ai_worker_loop(self):
        """Background thread executing YOLO11x inference without blocking video playback."""
        while not self._stop_worker.is_set():
            try:
                frame_data = self._ai_frame_queue.get(timeout=0.3)
            except queue.Empty:
                continue

            if frame_data is None:
                continue

            frame, frame_idx = frame_data
            try:
                # Run YOLO11x prediction on CPU
                results = self.ai_model.predict(
                    source=frame,
                    imgsz=self.ai_imgsz,
                    conf=self.ai_conf_threshold,
                    verbose=False,
                    device="cpu"
                )

                new_detections = []
                if results and len(results) > 0:
                    boxes = results[0].boxes
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        cls_name = self.ai_classes.get(cls_id, str(cls_id)).lower()
                        conf = float(box.conf[0].item())

                        # Identify 'accident' class (class 0 in Enos-123 model)
                        if cls_name == "accident" or cls_id == 0:
                            xyxy = [int(v.item()) for v in box.xyxy[0]]
                            new_detections.append({
                                "bbox": xyxy,
                                "confidence": conf,
                                "timestamp": time.time(),
                                "frame_idx": frame_idx,
                                "class_name": "accident"
                            })

                with self._lock:
                    if new_detections:
                        self._latest_ai_detections = new_detections
                    else:
                        # Retain recent detections for at least 2.0s before clearing
                        self._latest_ai_detections = [
                            d for d in self._latest_ai_detections
                            if (time.time() - d["timestamp"]) < 2.0
                        ]
            except Exception as e:
                logger.error(f"Error in YOLO11x accident worker: {e}")
            finally:
                self._ai_frame_queue.task_done()

    def analyze(
        self,
        active_tracks: List[TrackedObject],
        frame: Optional[np.ndarray] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyzes vehicle trajectories and frame imagery for collisions.
        Returns a list of detected accident event records.
        """
        if not self.enabled:
            return []

        alerts: List[Dict[str, Any]] = []
        vehicles = [t for t in active_tracks if t.class_name != "person"]
        self._frame_count += 1
        now = time.time()

        # Clean expired alerted locations
        self._alerted_locations = [
            (lx, ly, ts) for (lx, ly, ts) in self._alerted_locations
            if (now - ts) < self._cooldown_seconds
        ]

        # -------------------------------------------------------------
        # 1. Dispatch Frame to AI Vision Queue (Periodic or on Suspicion)
        # -------------------------------------------------------------
        has_suspicious_kinematics = any(
            v.stationary_frames >= 10 and not (v.track_id in self._alerted_accident_ids)
            for v in vehicles
        )

        should_scan_ai = (
            frame is not None
            and self.ai_model is not None
            and self.use_ai_model
            and (self._frame_count % self.ai_scan_interval == 0 or has_suspicious_kinematics)
        )

        if should_scan_ai:
            try:
                # Push frame if queue is empty (non-blocking)
                if self._ai_frame_queue.empty():
                    self._ai_frame_queue.put_nowait((frame.copy(), self._frame_count))
            except queue.Full:
                pass

        # -------------------------------------------------------------
        # 2. Check Fresh AI Vision Detections
        # -------------------------------------------------------------
        ai_boxes_to_process = []
        with self._lock:
            for det in self._latest_ai_detections:
                if (now - det["timestamp"]) < 3.0:
                    ai_boxes_to_process.append(dict(det))

        for ai_det in ai_boxes_to_process:
            bx1, by1, bx2, by2 = ai_det["bbox"]
            cx = (bx1 + bx2) / 2.0
            cy = (by1 + by2) / 2.0

            # Spatial cooldown check
            in_cooldown = any(
                math.hypot(cx - lx, cy - ly) < 80.0
                for (lx, ly, _) in self._alerted_locations
            )

            if not in_cooldown:
                self._alerted_locations.append((cx, cy, now))

                # Match with nearest active tracked vehicle
                matched_track = None
                min_dist = float("inf")
                for v in vehicles:
                    dist = math.hypot(v.center[0] - cx, v.center[1] - cy)
                    if dist < 120.0 and dist < min_dist:
                        min_dist = dist
                        matched_track = v

                track_id = matched_track.track_id if matched_track else "AI_VISION"
                if matched_track:
                    self._alerted_accident_ids.add(matched_track.track_id)

                alerts.append({
                    "event_type": "POSSIBLE_ACCIDENT",
                    "severity": "CRITICAL",
                    "tracking_id": track_id,
                    "confidence": round(float(ai_det["confidence"]), 2),
                    "description": (
                        f"AI Deep Learning Vision (YOLO11x): Traffic accident detected "
                        f"({int(ai_det['confidence'] * 100)}% confidence)"
                        + (f" involving Vehicle #{matched_track.track_id}" if matched_track else "")
                    ),
                    "bbox": ai_det["bbox"],
                    "source": "YOLO11X_ACCIDENT_AI"
                })

        # -------------------------------------------------------------
        # 3. Kinematic Heuristic Rules (Deceleration & Abnormal Proximity)
        # -------------------------------------------------------------
        # Sudden stop + standstill
        for obj in vehicles:
            if obj.track_id in self._alerted_accident_ids:
                continue

            if len(obj.history) < 20:
                continue

            hist = list(obj.history)
            early_pts = hist[:10]
            if len(early_pts) >= 2:
                early_dist = math.hypot(early_pts[-1][0] - early_pts[0][0], early_pts[-1][1] - early_pts[0][1])
                dt = early_pts[-1][3] - early_pts[0][3]
                early_speed = (early_dist / dt) if dt > 0 else 0.0
            else:
                early_speed = 0.0

            curr_pts = hist[-5:]
            if len(curr_pts) >= 2:
                curr_dist = math.hypot(curr_pts[-1][0] - curr_pts[0][0], curr_pts[-1][1] - curr_pts[0][1])
                dt = curr_pts[-1][3] - curr_pts[0][3]
                curr_speed = (curr_dist / dt) if dt > 0 else 0.0
            else:
                curr_speed = 0.0

            if early_speed >= self.min_pre_speed and curr_speed < (early_speed * (1.0 - self.speed_drop_ratio)):
                if obj.stationary_frames >= self.min_stationary_frames:
                    nearby_vehicle = None
                    for other in vehicles:
                        if other.track_id != obj.track_id:
                            dist = math.hypot(obj.center[0] - other.center[0], obj.center[1] - other.center[1])
                            if dist < self.proximity_distance_px * 2.0:
                                nearby_vehicle = other
                                break

                    reason = (
                        f"Vehicle #{obj.track_id} ({obj.class_name}) sudden deceleration "
                        f"({early_speed:.1f} -> {curr_speed:.1f} px/f) followed by sustained stoppage"
                    )
                    if nearby_vehicle:
                        reason += f" in close proximity to Vehicle #{nearby_vehicle.track_id}"

                    self._alerted_accident_ids.add(obj.track_id)
                    alerts.append({
                        "event_type": "POSSIBLE_ACCIDENT",
                        "severity": "CRITICAL",
                        "tracking_id": obj.track_id,
                        "confidence": 0.85 if nearby_vehicle else 0.75,
                        "description": reason,
                        "bbox": obj.bbox,
                        "source": "KINEMATICS_HEURISTIC"
                    })

        # Abnormal close vehicle interaction
        n = len(vehicles)
        for i in range(n):
            for j in range(i + 1, n):
                v1, v2 = vehicles[i], vehicles[j]
                if v1.track_id in self._alerted_accident_ids or v2.track_id in self._alerted_accident_ids:
                    continue

                dist = math.hypot(v1.center[0] - v2.center[0], v1.center[1] - v2.center[1])
                if dist < self.proximity_distance_px:
                    if (v1.is_stationary and v1.stationary_frames >= 12) or (v2.is_stationary and v2.stationary_frames >= 12):
                        self._alerted_accident_ids.add(v1.track_id)
                        self._alerted_accident_ids.add(v2.track_id)
                        alerts.append({
                            "event_type": "POSSIBLE_ACCIDENT",
                            "severity": "CRITICAL",
                            "tracking_id": v1.track_id,
                            "confidence": 0.88,
                            "description": (
                                f"Collision proximity between Vehicle #{v1.track_id} and #{v2.track_id} "
                                f"resulting in roadway stoppage ({dist:.1f} px separation)"
                            ),
                            "bbox": v1.bbox,
                            "source": "KINEMATICS_HEURISTIC"
                        })

        return alerts

    def get_active_accident_boxes(self) -> List[Dict[str, Any]]:
        """Returns recent AI vision accident detections for HUD overlay rendering."""
        now = time.time()
        with self._lock:
            return [
                dict(d) for d in self._latest_ai_detections
                if (now - d["timestamp"]) < 2.5
            ]

    def is_ai_loaded(self) -> bool:
        """Returns True if the YOLO11x model is loaded in memory."""
        return self.ai_model is not None

    def get_model_info(self) -> Dict[str, Any]:
        """Returns model diagnostic metadata."""
        return {
            "model_type": "YOLO11x",
            "model_path": self.ai_model_path,
            "is_loaded": self.is_ai_loaded(),
            "classes": self.ai_classes,
            "conf_threshold": self.ai_conf_threshold,
            "scan_interval": self.ai_scan_interval
        }

    def reset(self):
        """Resets alerted accident IDs, locations, and detections."""
        self._alerted_accident_ids.clear()
        self._alerted_locations.clear()
        with self._lock:
            self._latest_ai_detections.clear()

    def stop(self):
        """Cleanly stops the background AI worker thread."""
        self._stop_worker.set()
        if self._ai_worker_thread and self._ai_worker_thread.is_alive():
            self._ai_worker_thread.join(timeout=1.0)
