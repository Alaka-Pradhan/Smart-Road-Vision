"""
Video Processor Module for Smart Road Vision.
Runs background video capture, AI detection, multi-object tracking,
rule evaluations, overlay rendering, and thread-safe frame delivery.
"""

import cv2
import time
import queue
import logging
import threading
from collections import deque
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from .detector import ObjectDetector
from .tracker import TrafficTracker
from .violation_detector import ViolationDetector
from .accident_detector import PossibleAccidentDetector
from .emergency_detector import EmergencyVehicleDetector
from .traffic_analyzer import TrafficDensityAnalyzer
from .event_engine import EventEngine

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Manages the video acquisition and computer vision processing pipeline in a background thread."""

    def __init__(
        self,
        config: Dict[str, Any],
        detector: ObjectDetector,
        tracker: TrafficTracker,
        violation_detector: ViolationDetector,
        accident_detector: PossibleAccidentDetector,
        emergency_detector: EmergencyVehicleDetector,
        traffic_analyzer: TrafficDensityAnalyzer,
        event_engine: EventEngine,
        frame_queue: queue.Queue
    ):
        self.config = config
        self.detector = detector
        self.tracker = tracker
        self.violation_detector = violation_detector
        self.accident_detector = accident_detector
        self.emergency_detector = emergency_detector
        self.traffic_analyzer = traffic_analyzer
        self.event_engine = event_engine
        self.frame_queue = frame_queue

        # Source configuration
        self.source_type = "webcam"  # 'file', 'webcam', 'rtsp'
        self.source_param = 0
        self.source_display_name = "Webcam 0"

        # Threading state flags
        self.is_running = False
        self.is_paused = False
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Capture object
        self.cap: Optional[cv2.VideoCapture] = None
        self.video_fps = 30.0
        self.frame_width = 720
        self.frame_height = 480

        # Rolling buffer for evidence clips
        self.rolling_buffer = deque(maxlen=60)

        # Overlay display toggles
        self.show_bboxes = True
        self.show_tracks = True
        self.show_stop_line = True
        self.show_direction_arrow = True
        self.show_hud = True

        # Signal state (can be toggled in real time)
        self.signal_state = self.config.get("red_light", {}).get("traffic_signal_state", "RED")

    def set_source(self, source_type: str, source_param: Any):
        """Configures video input source."""
        self.source_type = source_type
        self.source_param = source_param
        if source_type == "webcam":
            self.source_display_name = f"Webcam {source_param}"
        elif source_type == "file":
            import os
            self.source_display_name = f"Video: {os.path.basename(str(source_param))}"
        elif source_type == "rtsp":
            self.source_display_name = f"RTSP Stream ({source_param})"
        self.event_engine.set_source_name(self.source_display_name)

    def set_signal_state(self, new_state: str):
        """Updates traffic signal state in real-time."""
        self.signal_state = new_state.upper()
        self.violation_detector.signal_state = self.signal_state

    def start(self) -> bool:
        """Starts video processing background thread."""
        if self.is_running:
            logger.warning("Video processor is already running.")
            return True

        self._stop_event.clear()
        self._pause_event.clear()
        self.is_running = True
        self.is_paused = False

        self._thread = threading.Thread(target=self._processing_loop, daemon=True)
        self._thread.start()
        logger.info(f"Started video processing thread for source: {self.source_display_name}")
        return True

    def pause(self):
        """Pauses video playback."""
        self.is_paused = True
        self._pause_event.set()

    def resume(self):
        """Resumes video playback."""
        self.is_paused = False
        self._pause_event.clear()

    def stop(self):
        """Stops video playback and processing thread."""
        self.is_running = False
        self.is_paused = False
        self._stop_event.set()
        self._pause_event.clear()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

        self._release_capture()
        if hasattr(self.accident_detector, "stop"):
            self.accident_detector.stop()
        logger.info("Video processor stopped cleanly.")

    def reset(self):
        """Resets tracking, counters, and rewinds video if playing a file."""
        self.tracker.reset()
        self.violation_detector.reset()
        self.accident_detector.reset()
        self.emergency_detector.reset()
        self.traffic_analyzer.reset()
        self.rolling_buffer.clear()
        if self.cap and self.source_type == "file":
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def _init_capture(self) -> bool:
        """Opens cv2.VideoCapture based on configured source."""
        self._release_capture()

        try:
            if self.source_type == "webcam":
                idx = int(self.source_param)
                self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            elif self.source_type == "file":
                self.cap = cv2.VideoCapture(str(self.source_param))
            elif self.source_type == "rtsp":
                self.cap = cv2.VideoCapture(str(self.source_param))
            else:
                self.cap = cv2.VideoCapture(0)

            if not self.cap or not self.cap.isOpened():
                logger.error(f"Failed to open video source: {self.source_param}")
                return False

            fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.video_fps = fps if (fps and 5.0 <= fps <= 120.0) else 30.0
            return True

        except Exception as e:
            logger.error(f"Exception initializing capture: {e}")
            return False

    def _release_capture(self):
        """Releases video capture resource."""
        if self.cap:
            try:
                self.cap.release()
            except Exception as e:
                logger.warning(f"Error releasing capture: {e}")
            self.cap = None

    def _processing_loop(self):
        """Main loop running inside the background thread."""
        if not self._init_capture():
            self.is_running = False
            return

        frame_interval = 1.0 / self.video_fps

        while not self._stop_event.is_set():
            # Handle pause
            if self._pause_event.is_set():
                time.sleep(0.05)
                continue

            t_start = time.time()

            ret, frame = self.cap.read()
            if not ret or frame is None:
                if self.source_type == "file":
                    # Loop video file for continuous demonstration
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap.read()
                    if not ret or frame is None:
                        break
                else:
                    time.sleep(0.05)
                    continue

            # Resize to standard dimensions for consistent UI display and FPS
            h, w = frame.shape[:2]
            target_w, target_h = 720, 480
            if (w, h) != (target_w, target_h):
                frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

            raw_frame_copy = frame.copy()
            self.rolling_buffer.append(raw_frame_copy)

            # 1. AI Detection & Tracking Inference
            detections = self.detector.track(frame)

            # 2. Update multi-object tracking history
            active_tracks = self.tracker.update(detections)

            # 3. Analyze traffic density
            density_result = self.traffic_analyzer.analyze(active_tracks)
            if density_result.get("event"):
                self.event_engine.dispatch_event(
                    raw_event=density_result["event"],
                    current_frame=raw_frame_copy,
                    frame_buffer=list(self.rolling_buffer)
                )

            # 4. Check traffic violations (Wrong-way, Red-light)
            for track_obj in active_tracks:
                # Wrong-way check
                ww_event = self.violation_detector.check_wrong_way(track_obj)
                if ww_event:
                    self.event_engine.dispatch_event(
                        raw_event=ww_event,
                        current_frame=raw_frame_copy,
                        frame_buffer=list(self.rolling_buffer)
                    )

                # Red-light check
                rl_event = self.violation_detector.check_red_light(track_obj)
                if rl_event:
                    self.event_engine.dispatch_event(
                        raw_event=rl_event,
                        current_frame=raw_frame_copy,
                        frame_buffer=list(self.rolling_buffer)
                    )

                # Emergency check
                em_event = self.emergency_detector.check_vehicle(track_obj)
                if em_event:
                    self.event_engine.dispatch_event(
                        raw_event=em_event,
                        current_frame=raw_frame_copy,
                        frame_buffer=list(self.rolling_buffer)
                    )

            # 5. Check possible accident (Dual-Engine: AI YOLO11x + Kinematics)
            accident_events = self.accident_detector.analyze(active_tracks, frame=raw_frame_copy)
            for acc_event in accident_events:
                self.event_engine.dispatch_event(
                    raw_event=acc_event,
                    current_frame=raw_frame_copy,
                    frame_buffer=list(self.rolling_buffer)
                )

            # 6. Render HUD overlays on frame
            annotated_frame = self._render_overlays(frame, active_tracks, density_result)

            # 7. Push to GUI Queue (drop oldest frame if full to prevent lag)
            try:
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.frame_queue.put_nowait({
                    "frame": annotated_frame,
                    "active_tracks_count": len(active_tracks),
                    "density_result": density_result,
                    "signal_state": self.signal_state
                })
            except Exception as e:
                logger.debug(f"Queue push error: {e}")

            # Sleep to match video fps
            t_elapsed = time.time() - t_start
            t_sleep = max(0.005, frame_interval - t_elapsed)
            time.sleep(t_sleep)

        self._release_capture()
        self.is_running = False

    def _render_overlays(self, frame: np.ndarray, tracks: List[Any], density: Dict[str, Any]) -> np.ndarray:
        """Renders bounding boxes, tracks, stop-lines, direction arrows, and HUD badges."""
        out = frame.copy()
        h, w = out.shape[:2]

        # 1. Draw Virtual Stop Line
        if self.show_stop_line and self.violation_detector.red_light_enabled:
            sl = self.violation_detector.stop_line
            x1, y1 = int(sl["x1"]), int(sl["y1"])
            x2, y2 = int(sl["x2"]), int(sl["y2"])
            line_color = (0, 0, 255) if self.signal_state == "RED" else (0, 220, 0)
            cv2.line(out, (x1, y1), (x2, y2), line_color, 3)
            # Stop line label
            cv2.putText(
                out,
                f"STOP LINE [SIGNAL: {self.signal_state}]",
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                line_color,
                2,
                cv2.LINE_AA
            )

        # 2. Draw Trajectories and Bounding Boxes
        for obj in tracks:
            bx1, by1, bx2, by2 = [int(v) for v in obj.bbox]

            # Trajectory polyline
            if self.show_tracks and len(obj.history) > 1:
                pts = [np.array([int(p[0]), int(p[1])], dtype=np.int32) for p in obj.history]
                for i in range(1, len(pts)):
                    alpha = i / len(pts)
                    thickness = max(1, int(alpha * 3))
                    color = (0, int(255 * alpha), int(255 * (1 - alpha)))
                    cv2.line(out, tuple(pts[i - 1]), tuple(pts[i]), color, thickness)

            # Bounding box
            if self.show_bboxes:
                box_color = (0, 215, 255) if obj.class_name == "car" else (255, 128, 0)
                if obj.is_stationary:
                    box_color = (0, 0, 255)
                cv2.rectangle(out, (bx1, by1), (bx2, by2), box_color, 2)

                # Label tag
                label = f"#{obj.track_id} {obj.class_name} {obj.speed:.1f}px/f"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(out, (bx1, by1 - th - 6), (bx1 + tw + 6, by1), box_color, -1)
                cv2.putText(
                    out,
                    label,
                    (bx1 + 3, by1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 0, 0),
                    1,
                    cv2.LINE_AA
                )

        # 3. Draw AI Accident Vision Detections (YOLO11x)
        if hasattr(self.accident_detector, "get_active_accident_boxes"):
            ai_accidents = self.accident_detector.get_active_accident_boxes()
            for acc in ai_accidents:
                ax1, ay1, ax2, ay2 = acc["bbox"]
                conf = acc.get("confidence", 0.0)
                # Outer flashing red box with double border
                cv2.rectangle(out, (ax1, ay1), (ax2, ay2), (0, 0, 255), 3)
                cv2.rectangle(out, (ax1 - 2, ay1 - 2), (ax2 + 2, ay2 + 2), (50, 50, 255), 1)

                acc_label = f"CRITICAL: ACCIDENT DETECTED (AI YOLO11x: {int(conf * 100)}%)"
                (atw, ath), _ = cv2.getTextSize(acc_label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(out, (ax1, max(0, ay1 - ath - 8)), (ax1 + atw + 8, ay1), (0, 0, 200), -1)
                cv2.putText(
                    out,
                    acc_label,
                    (ax1 + 4, max(ath, ay1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA
                )

        # 4. Direction Arrow Indicator
        if self.show_direction_arrow:
            exp_dir = self.violation_detector.expected_direction
            cv2.putText(
                out,
                f"Lane Direction: {exp_dir}",
                (14, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (220, 220, 220),
                1,
                cv2.LINE_AA
            )
            # Arrow glyph
            p_start, p_end = (140, 35), (140, 55)
            if exp_dir == "TOP_TO_BOTTOM":
                p_start, p_end = (160, 15), (160, 32)
            elif exp_dir == "BOTTOM_TO_TOP":
                p_start, p_end = (160, 32), (160, 15)
            cv2.arrowedLine(out, p_start, p_end, (0, 255, 255), 2, tipLength=0.35)

        # 4. Traffic Signal Lamp Indicator (Top Right)
        sig_color = (0, 0, 255) if self.signal_state == "RED" else ((0, 255, 255) if self.signal_state == "YELLOW" else (0, 255, 0))
        cv2.circle(out, (w - 30, 25), 12, (30, 30, 30), -1)
        cv2.circle(out, (w - 30, 25), 10, sig_color, -1)
        cv2.putText(
            out,
            self.signal_state,
            (w - 95, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            sig_color,
            2,
            cv2.LINE_AA
        )

        # 5. Density and Status HUD Banner (Bottom)
        if self.show_hud:
            cv2.rectangle(out, (0, h - 34), (w, h), (15, 20, 28), -1)
            cv2.line(out, (0, h - 34), (w, h - 34), (40, 50, 70), 1)

            dens_level = density.get("level", "LOW")
            dens_color = (0, 220, 0) if dens_level == "LOW" else ((0, 200, 255) if dens_level == "MEDIUM" else (0, 0, 255))
            veh_count = density.get("vehicle_count", 0)

            hud_text = (
                f"LIVE MONITORING | Active Vehicles: {veh_count} | "
                f"Density: {dens_level} | Source: {self.source_display_name}"
            )
            cv2.putText(
                out,
                hud_text,
                (14, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

        return out
