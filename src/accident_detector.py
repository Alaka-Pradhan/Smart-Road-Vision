"""
Possible Accident Detection Module for Smart Road Vision.
Uses heuristic multi-indicator analysis combining trajectory changes,
sudden deceleration, multi-vehicle proximity, and persistent roadway standstill.
NOTE: These rules are heuristic indicators designed for safety alert triage
and require calibration on domain-specific collision datasets.
"""

import math
import logging
from typing import Dict, List, Tuple, Optional, Any
from .tracker import TrackedObject

logger = logging.getLogger(__name__)


class PossibleAccidentDetector:
    """Heuristic detector for suspicious road incidents and potential vehicle accidents."""

    def __init__(self, config: Dict[str, Any]):
        self.update_config(config)
        self._alerted_accident_ids = set()

    def update_config(self, config: Dict[str, Any]):
        """Updates heuristic parameters from configuration dictionary."""
        cfg = config.get("accident_detection", {})
        self.enabled = cfg.get("enabled", True)
        self.speed_drop_ratio = cfg.get("sudden_stop_speed_drop_ratio", 0.75)
        self.min_stationary_frames = cfg.get("min_frames_stationary", 18)
        self.proximity_distance_px = cfg.get("proximity_distance_px", 55)
        self.min_pre_speed = cfg.get("min_pre_accident_speed_px", 5.0)

    def analyze(self, active_tracks: List[TrackedObject]) -> List[Dict[str, Any]]:
        """
        Analyzes active vehicle trajectories for collision patterns.
        Returns a list of detected possible accident event descriptors.
        """
        if not self.enabled or len(active_tracks) == 0:
            return []

        alerts = []
        vehicles = [t for t in active_tracks if t.class_name != "person"]

        # 1. Check sudden stop + standstill
        for obj in vehicles:
            if obj.track_id in self._alerted_accident_ids:
                continue

            # Need sufficient history to inspect pre-stop behavior
            if len(obj.history) < 20:
                continue

            # Inspect speed before and currently
            hist = list(obj.history)
            # Speeds during earlier phase (e.g. 15-20 frames ago)
            early_pts = hist[:10]
            if len(early_pts) >= 2:
                early_dist = math.hypot(early_pts[-1][0] - early_pts[0][0], early_pts[-1][1] - early_pts[0][1])
                dt = early_pts[-1][3] - early_pts[0][3]
                early_speed = (early_dist / dt) if dt > 0 else 0.0
            else:
                early_speed = 0.0

            # Current speed over last 5 frames
            curr_pts = hist[-5:]
            if len(curr_pts) >= 2:
                curr_dist = math.hypot(curr_pts[-1][0] - curr_pts[0][0], curr_pts[-1][1] - curr_pts[0][1])
                dt = curr_pts[-1][3] - curr_pts[0][3]
                curr_speed = (curr_dist / dt) if dt > 0 else 0.0
            else:
                curr_speed = 0.0

            # Condition A: Vehicle was moving at reasonable speed (> min_pre_speed)
            # and experienced severe deceleration (> speed_drop_ratio)
            # and has remained stationary for min_stationary_frames
            if early_speed >= self.min_pre_speed and curr_speed < (early_speed * (1.0 - self.speed_drop_ratio)):
                if obj.stationary_frames >= self.min_stationary_frames:
                    # Check if there is another vehicle nearby (interaction proxy)
                    nearby_vehicle = None
                    for other in vehicles:
                        if other.track_id != obj.track_id:
                            dist = math.hypot(obj.center[0] - other.center[0], obj.center[1] - other.center[1])
                            if dist < self.proximity_distance_px * 2.0:
                                nearby_vehicle = other
                                break

                    reason = (
                        f"Vehicle #{obj.track_id} ({obj.class_name}) sudden deceleration "
                        f"({early_speed:.1f} -> {curr_speed:.1f} px/f) followed by sustained roadway stoppage"
                    )
                    if nearby_vehicle:
                        reason += f" in close proximity to Vehicle #{nearby_vehicle.track_id}"

                    self._alerted_accident_ids.add(obj.track_id)
                    alerts.append({
                        "event_type": "POSSIBLE_ACCIDENT",
                        "severity": "CRITICAL",
                        "tracking_id": obj.track_id,
                        "confidence": 0.82 if nearby_vehicle else 0.72,
                        "description": reason,
                        "bbox": obj.bbox
                    })

        # 2. Check multi-vehicle abnormal close interaction
        n = len(vehicles)
        for i in range(n):
            for j in range(i + 1, n):
                v1, v2 = vehicles[i], vehicles[j]
                if v1.track_id in self._alerted_accident_ids or v2.track_id in self._alerted_accident_ids:
                    continue

                # Center distance
                dist = math.hypot(v1.center[0] - v2.center[0], v1.center[1] - v2.center[1])
                if dist < self.proximity_distance_px:
                    # Both or one stopped after close interaction
                    if (v1.is_stationary and v1.stationary_frames >= 12) or (v2.is_stationary and v2.stationary_frames >= 12):
                        self._alerted_accident_ids.add(v1.track_id)
                        self._alerted_accident_ids.add(v2.track_id)
                        alerts.append({
                            "event_type": "POSSIBLE_ACCIDENT",
                            "severity": "CRITICAL",
                            "tracking_id": v1.track_id,
                            "confidence": 0.85,
                            "description": (
                                f"Collision proximity between Vehicle #{v1.track_id} and #{v2.track_id} "
                                f"resulting in abnormal roadway stoppage ({dist:.1f} px separation)"
                            ),
                            "bbox": v1.bbox
                        })

        return alerts

    def reset(self):
        """Resets alerted accident sets."""
        self._alerted_accident_ids.clear()
