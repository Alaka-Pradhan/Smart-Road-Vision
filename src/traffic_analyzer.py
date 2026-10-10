"""
Traffic Density Analysis Module for Smart Road Vision.
Estimates real-time traffic density, categorizes traffic levels (LOW / MEDIUM / HIGH),
maintains time-series density observations, and generates congestion notices.
"""

import time
import logging
from collections import deque
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from .tracker import TrackedObject

logger = logging.getLogger(__name__)


class TrafficDensityAnalyzer:
    """Estimates roadway traffic density from active vehicle tracks."""

    def __init__(self, config: Dict[str, Any]):
        self.update_config(config)
        self.history = deque(maxlen=100)  # (timestamp, vehicle_count, level)
        self.current_count = 0
        self.current_level = "LOW"
        self.last_event_time = 0.0

    def update_config(self, config: Dict[str, Any]):
        """Updates density thresholds from configuration dictionary."""
        cfg = config.get("density", {})
        self.enabled = cfg.get("enabled", True)
        self.low_threshold = int(cfg.get("low_threshold", 3))
        self.medium_threshold = int(cfg.get("medium_threshold", 7))
        self.roi_polygon = cfg.get("roi_polygon", None)

    def analyze(self, active_tracks: List[TrackedObject]) -> Dict[str, Any]:
        """
        Calculates current traffic density classification from active vehicles.
        Returns a dictionary with density metrics and optional event trigger.
        """
        # Filter for actual road vehicles (excluding pedestrian)
        vehicles = [t for t in active_tracks if t.class_name != "person"]
        count = len(vehicles)
        self.current_count = count

        if count <= self.low_threshold:
            level = "LOW"
            color = "#10b981"  # Emerald green
        elif count <= self.medium_threshold:
            level = "MEDIUM"
            color = "#f59e0b"  # Amber
        else:
            level = "HIGH"
            color = "#ef4444"  # Coral red

        prev_level = self.current_level
        self.current_level = level

        now_ts = time.time()
        self.history.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "time_epoch": now_ts,
            "vehicle_count": count,
            "level": level
        })

        event_data = None
        # Generate density notification if shifted to HIGH congestion and cooldown passed (30s)
        if level == "HIGH" and prev_level != "HIGH" and (now_ts - self.last_event_time > 30.0):
            self.last_event_time = now_ts
            event_data = {
                "event_type": "TRAFFIC_DENSITY",
                "severity": "MEDIUM",
                "tracking_id": "-",
                "confidence": 0.90,
                "description": f"Heavy traffic congestion detected ({count} vehicles in frame, exceeding threshold of {self.medium_threshold})",
                "bbox": None
            }

        return {
            "vehicle_count": count,
            "level": level,
            "color": color,
            "low_threshold": self.low_threshold,
            "medium_threshold": self.medium_threshold,
            "event": event_data
        }

    def get_history(self) -> List[Dict[str, Any]]:
        """Returns historical time-series density data."""
        return list(self.history)

    def reset(self):
        """Clears current metrics and history."""
        self.history.clear()
        self.current_count = 0
        self.current_level = "LOW"
        self.last_event_time = 0.0
