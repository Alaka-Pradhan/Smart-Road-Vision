"""
Emergency Vehicle Detection Module for Smart Road Vision.
Handles emergency vehicle identification (Ambulances, Fire Services, Police)
with priority alert routing and custom model integration interface.
"""

import logging
from typing import Dict, List, Optional, Any
from .tracker import TrackedObject

logger = logging.getLogger(__name__)


class EmergencyVehicleDetector:
    """Manages emergency vehicle identification, alerting, and model integration."""

    def __init__(self, config: Dict[str, Any]):
        self.update_config(config)
        self._alerted_emergency_ids = set()

    def update_config(self, config: Dict[str, Any]):
        """Updates module configuration."""
        cfg = config.get("emergency_detection", {})
        self.enabled = cfg.get("enabled", True)
        self.alert_priority = cfg.get("alert_priority", "CRITICAL")
        self.use_custom_model = cfg.get("use_custom_model", False)

    def check_vehicle(self, tracked_obj: TrackedObject, detector_res: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Evaluates whether a tracked vehicle is an emergency vehicle.
        Supports custom trained YOLO models (e.g., custom ambulance/fire brigade classifier).
        """
        if not self.enabled or tracked_obj.track_id in self._alerted_emergency_ids:
            return None

        # 1. Custom model detection result check
        if detector_res and detector_res.get("is_emergency"):
            ev_type = detector_res.get("type", "EMERGENCY_VEHICLE")
            self._alerted_emergency_ids.add(tracked_obj.track_id)
            return {
                "event_type": "EMERGENCY_VEHICLE",
                "severity": "CRITICAL",
                "tracking_id": tracked_obj.track_id,
                "confidence": detector_res.get("confidence", 0.90),
                "description": f"Priority Emergency Vehicle ({ev_type}) #{tracked_obj.track_id} detected in active corridor",
                "bbox": tracked_obj.bbox
            }

        return None

    def reset(self):
        """Resets alerted tracker IDs."""
        self._alerted_emergency_ids.clear()
