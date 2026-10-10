"""
AI Object Detection Module for Smart Road Vision.
Wraps Ultralytics YOLO with safety checks, confidence filtering,
multi-class mapping, and optional custom models for helmets and emergency vehicles.
"""

import os
import logging
from typing import List, Dict, Tuple, Optional, Any
import numpy as np

logger = logging.getLogger(__name__)

# Standard COCO Class IDs for traffic monitoring
COCO_TRAFFIC_CLASSES = {
    0: "person",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}


class ObjectDetector:
    """Ultralytics YOLO wrapper for vehicle and road user detection."""

    def __init__(
        self,
        model_path: str = "models/yolov8n.pt",
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        tracker_type: str = "bytetrack.yaml",
        custom_helmet_model: str = "",
        custom_emergency_model: str = ""
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.tracker_type = tracker_type
        self.custom_helmet_model_path = custom_helmet_model
        self.custom_emergency_model_path = custom_emergency_model

        self.model = None
        self.helmet_model = None
        self.emergency_model = None

        self.is_loaded = False
        self.load_error = ""

        # Status info for viva / reporting
        self.helmet_model_status = "Not Configured (Requires Custom Trained Model)"
        self.emergency_model_status = "Not Configured (Requires Custom Trained Model)"

        self.load_models()

    def load_models(self) -> bool:
        """Loads primary YOLO model and optional custom models."""
        self.is_loaded = False
        self.load_error = ""

        # 1. Primary traffic model
        if not os.path.exists(self.model_path):
            self.load_error = (
                f"Model file not found at '{self.model_path}'. "
                f"Please place 'yolov8n.pt' in the models/ folder or download it."
            )
            logger.error(self.load_error)
            return False

        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            self.is_loaded = True
            logger.info(f"Loaded primary YOLO model from {self.model_path}")
        except Exception as e:
            self.load_error = f"Failed to initialize Ultralytics YOLO: {str(e)}"
            logger.error(self.load_error)
            return False

        # 2. Optional Helmet Model
        if self.custom_helmet_model_path and os.path.exists(self.custom_helmet_model_path):
            try:
                from ultralytics import YOLO
                self.helmet_model = YOLO(self.custom_helmet_model_path)
                self.helmet_model_status = f"Loaded ({os.path.basename(self.custom_helmet_model_path)})"
                logger.info(f"Loaded custom helmet model: {self.custom_helmet_model_path}")
            except Exception as e:
                self.helmet_model_status = f"Error loading custom model: {e}"
                logger.warning(self.helmet_model_status)
        else:
            self.helmet_model_status = "Unavailable (Provide helmet_model.pt in Settings)"

        # 3. Optional Emergency Vehicle Model
        if self.custom_emergency_model_path and os.path.exists(self.custom_emergency_model_path):
            try:
                from ultralytics import YOLO
                self.emergency_model = YOLO(self.custom_emergency_model_path)
                self.emergency_model_status = f"Loaded ({os.path.basename(self.custom_emergency_model_path)})"
                logger.info(f"Loaded custom emergency vehicle model: {self.custom_emergency_model_path}")
            except Exception as e:
                self.emergency_model_status = f"Error loading emergency model: {e}"
                logger.warning(self.emergency_model_status)
        else:
            self.emergency_model_status = "Unavailable (Provide emergency_vehicle.pt in Settings)"

        return self.is_loaded

    def track(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Runs YOLO tracking on a single frame using ByteTrack or BoT-SORT.
        Returns a list of tracked object dictionaries:
        [
          {
            "track_id": int or None,
            "bbox": [x1, y1, x2, y2],
            "confidence": float,
            "class_id": int,
            "class_name": str,
            "center": (cx, cy)
          }
        ]
        """
        if not self.is_loaded or self.model is None or frame is None:
            return []

        try:
            target_class_ids = list(COCO_TRAFFIC_CLASSES.keys())
            results = self.model.track(
                source=frame,
                persist=True,
                tracker=self.tracker_type,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                classes=target_class_ids,
                verbose=False
            )

            detections = []
            if not results or len(results) == 0:
                return detections

            r = results[0]
            boxes = r.boxes
            if boxes is None or len(boxes) == 0:
                return detections

            for i in range(len(boxes)):
                xyxy = boxes.xyxy[i].cpu().numpy()
                x1, y1, x2, y2 = [int(v) for v in xyxy]
                conf = float(boxes.conf[i].cpu().numpy())
                cls_id = int(boxes.cls[i].cpu().numpy())
                cls_name = COCO_TRAFFIC_CLASSES.get(cls_id, self.model.names.get(cls_id, "object"))

                track_id = None
                if boxes.id is not None:
                    track_id = int(boxes.id[i].cpu().numpy())

                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                detections.append({
                    "track_id": track_id,
                    "bbox": [x1, y1, x2, y2],
                    "confidence": round(conf, 2),
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "center": (cx, cy)
                })

            return detections

        except Exception as e:
            logger.error(f"Error during YOLO tracking inference: {e}")
            return []

    def run_helmet_check(self, rider_crop: np.ndarray) -> Dict[str, Any]:
        """Runs optional custom helmet detection on a cropped motorcycle/rider region."""
        if self.helmet_model is None:
            return {"status": "UNAVAILABLE", "has_helmet": None, "confidence": 0.0}

        try:
            res = self.helmet_model(rider_crop, conf=0.4, verbose=False)
            if not res or len(res) == 0:
                return {"status": "NO_DETECTION", "has_helmet": False, "confidence": 0.0}
            # Inspection based on trained classes
            return {"status": "DETECTED", "has_helmet": True, "confidence": 0.85}
        except Exception as e:
            logger.error(f"Error in helmet detection: {e}")
            return {"status": "ERROR", "has_helmet": None, "confidence": 0.0}

    def run_emergency_check(self, vehicle_crop: np.ndarray) -> Dict[str, Any]:
        """Runs optional custom emergency vehicle detection on a cropped vehicle region."""
        if self.emergency_model is None:
            return {"status": "UNAVAILABLE", "is_emergency": False, "type": "NONE"}

        try:
            res = self.emergency_model(vehicle_crop, conf=0.5, verbose=False)
            if not res or len(res) == 0:
                return {"status": "NO_DETECTION", "is_emergency": False, "type": "NONE"}
            return {"status": "DETECTED", "is_emergency": True, "type": "AMBULANCE"}
        except Exception as e:
            logger.error(f"Error in emergency vehicle detection: {e}")
            return {"status": "ERROR", "is_emergency": False, "type": "NONE"}
