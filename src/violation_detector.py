"""
Traffic Violation Detection Module for Smart Road Vision.
Includes Wrong-Way Driving, Stop-Line Red-Light Crossing,
and Optional Helmet Detection.
"""

import math
import logging
from typing import Dict, List, Tuple, Optional, Any
from .tracker import TrackedObject

logger = logging.getLogger(__name__)


def ccw(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float]) -> bool:
    """Checks counter-clockwise orientation of three points."""
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])


def lines_intersect(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float], D: Tuple[float, float]) -> bool:
    """Returns True if line segment AB intersects line segment CD."""
    return (ccw(A, C, D) != ccw(B, C, D)) and (ccw(A, B, C) != ccw(A, B, D))


class ViolationDetector:
    """Detects traffic violations based on vehicle tracking trajectories and road rules."""

    def __init__(self, config: Dict[str, Any]):
        self.update_config(config)
        self._alerted_wrong_way_ids = set()
        self._alerted_red_light_ids = set()

    def update_config(self, config: Dict[str, Any]):
        """Updates internal parameters from configuration dict."""
        ww_cfg = config.get("wrong_way", {})
        self.wrong_way_enabled = ww_cfg.get("enabled", True)
        self.expected_direction = ww_cfg.get("expected_direction", "TOP_TO_BOTTOM")
        self.ww_min_frames = ww_cfg.get("min_tracking_frames", 10)
        self.ww_min_disp_px = ww_cfg.get("min_displacement_px", 35)
        self.ww_consistency = ww_cfg.get("consistency_ratio", 0.70)

        rl_cfg = config.get("red_light", {})
        self.red_light_enabled = rl_cfg.get("enabled", True)
        self.stop_line = rl_cfg.get("stop_line", {"x1": 80, "y1": 340, "x2": 560, "y2": 340})
        self.signal_state = rl_cfg.get("traffic_signal_state", "RED").upper()
        self.prohibited_direction = rl_cfg.get("prohibited_direction", "TOP_TO_BOTTOM")

    def check_wrong_way(self, tracked_obj: TrackedObject) -> Optional[Dict[str, Any]]:
        """
        Analyzes vehicle trajectory over time to detect wrong-way movement.
        Requires sustained displacement opposing expected direction.
        """
        if not self.wrong_way_enabled or tracked_obj.class_name == "person":
            return None

        # Ignore if vehicle has already been flagged
        if tracked_obj.track_id in self._alerted_wrong_way_ids:
            return None

        # Check frame observation window
        if len(tracked_obj.history) < self.ww_min_frames:
            return None

        dx, dy, net_dist = tracked_obj.get_net_displacement(frames_back=self.ww_min_frames)

        # Must exceed minimal displacement to filter out stationary jitter
        if net_dist < self.ww_min_disp_px:
            return None

        is_wrong_way = False
        description = ""

        # Check based on configured expected direction
        if self.expected_direction == "TOP_TO_BOTTOM":
            # Expected downward (dy > 0), wrong if moving upward (dy < 0)
            if dy < -self.ww_min_disp_px and abs(dy) > abs(dx) * 0.7:
                is_wrong_way = True
                description = f"Vehicle #{tracked_obj.track_id} driving North in Southbound lane"
        elif self.expected_direction == "BOTTOM_TO_TOP":
            # Expected upward (dy < 0), wrong if moving downward (dy > 0)
            if dy > self.ww_min_disp_px and abs(dy) > abs(dx) * 0.7:
                is_wrong_way = True
                description = f"Vehicle #{tracked_obj.track_id} driving South in Northbound lane"
        elif self.expected_direction == "LEFT_TO_RIGHT":
            # Expected rightward (dx > 0), wrong if moving leftward (dx < 0)
            if dx < -self.ww_min_disp_px and abs(dx) > abs(dy) * 0.7:
                is_wrong_way = True
                description = f"Vehicle #{tracked_obj.track_id} driving West in Eastbound lane"
        elif self.expected_direction == "RIGHT_TO_LEFT":
            # Expected leftward (dx < 0), wrong if moving rightward (dx > 0)
            if dx > self.ww_min_disp_px and abs(dx) > abs(dy) * 0.7:
                is_wrong_way = True
                description = f"Vehicle #{tracked_obj.track_id} driving East in Westbound lane"

        if is_wrong_way:
            self._alerted_wrong_way_ids.add(tracked_obj.track_id)
            return {
                "event_type": "WRONG_WAY",
                "severity": "HIGH",
                "tracking_id": tracked_obj.track_id,
                "confidence": 0.88,
                "description": description,
                "bbox": tracked_obj.bbox
            }

        return None

    def check_red_light(self, tracked_obj: TrackedObject) -> Optional[Dict[str, Any]]:
        """
        Detects vehicle crossing the virtual stop line when signal state is RED.
        """
        if not self.red_light_enabled or tracked_obj.class_name == "person":
            return None

        # Only trigger if signal is RED
        if self.signal_state != "RED":
            return None

        if tracked_obj.track_id in self._alerted_red_light_ids:
            return None

        if len(tracked_obj.history) < 2:
            return None

        # Check line crossing
        p1 = (float(self.stop_line["x1"]), float(self.stop_line["y1"]))
        p2 = (float(self.stop_line["x2"]), float(self.stop_line["y2"]))

        hist = list(tracked_obj.history)
        prev_center = (float(hist[-2][0]), float(hist[-2][1]))
        curr_center = (float(hist[-1][0]), float(hist[-1][1]))

        # Segment intersection check
        if lines_intersect(prev_center, curr_center, p1, p2):
            # Direction check: ensure vehicle crossed in prohibited direction
            crossed_prohibited = True
            if self.prohibited_direction == "TOP_TO_BOTTOM":
                crossed_prohibited = (curr_center[1] > prev_center[1])
            elif self.prohibited_direction == "BOTTOM_TO_TOP":
                crossed_prohibited = (curr_center[1] < prev_center[1])

            if crossed_prohibited:
                self._alerted_red_light_ids.add(tracked_obj.track_id)
                return {
                    "event_type": "RED_LIGHT",
                    "severity": "CRITICAL",
                    "tracking_id": tracked_obj.track_id,
                    "confidence": 0.92,
                    "description": f"Vehicle #{tracked_obj.track_id} ({tracked_obj.class_name}) crossed stop line on RED signal",
                    "bbox": tracked_obj.bbox
                }

        return None

    def check_no_helmet(self, tracked_obj: TrackedObject, detector_res: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluates helmet detection output for motorcycle riders.
        If detector indicates custom helmet model detected missing helmet, generates event.
        """
        if tracked_obj.class_name not in ["motorcycle", "person"]:
            return None

        if detector_res.get("status") == "DETECTED" and not detector_res.get("has_helmet"):
            return {
                "event_type": "NO_HELMET",
                "severity": "MEDIUM",
                "tracking_id": tracked_obj.track_id,
                "confidence": detector_res.get("confidence", 0.75),
                "description": f"Two-wheeler rider #{tracked_obj.track_id} detected riding without safety helmet",
                "bbox": tracked_obj.bbox
            }

        return None

    def reset(self):
        """Resets alerted ID sets."""
        self._alerted_wrong_way_ids.clear()
        self._alerted_red_light_ids.clear()
