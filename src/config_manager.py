"""
Configuration Manager for Smart Road Vision.
Handles loading, validation, saving, and querying application settings.
"""

import os
import json
import copy
import logging

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join("config", "default_config.json")
USER_CONFIG_PATH = os.path.join("config", "user_config.json")


class ConfigManager:
    """Manages application configuration with fallbacks and file persistence."""

    def __init__(self, config_file: str = USER_CONFIG_PATH, default_file: str = DEFAULT_CONFIG_PATH):
        self.config_file = config_file
        self.default_file = default_file
        self._default_data = {}
        self._data = {}
        self.load()

    def load(self):
        """Loads default config and overrides with user config if present."""
        # 1. Load default config
        if os.path.exists(self.default_file):
            try:
                with open(self.default_file, "r", encoding="utf-8") as f:
                    self._default_data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading default config {self.default_file}: {e}")
                self._default_data = self._get_hardcoded_defaults()
        else:
            self._default_data = self._get_hardcoded_defaults()

        # 2. Deep copy to working data
        self._data = copy.deepcopy(self._default_data)

        # 3. Load user config if exists
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                    self._merge_dicts(self._data, user_data)
            except Exception as e:
                logger.warning(f"Could not load user config {self.config_file}, using defaults: {e}")

    def save(self) -> bool:
        """Saves current configuration to user config file."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            logger.info(f"Saved configuration to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def reset_to_defaults(self) -> bool:
        """Resets current configuration back to default configuration."""
        self._data = copy.deepcopy(self._default_data)
        return self.save()

    def get(self, section: str, key: str = None, default=None):
        """Retrieves a configuration section or specific key."""
        sec_data = self._data.get(section)
        if sec_data is None:
            return default
        if key is None:
            return sec_data
        if isinstance(sec_data, dict):
            return sec_data.get(key, default)
        return default

    def set(self, section: str, key: str, value) -> None:
        """Sets a configuration value within a section."""
        if section not in self._data or not isinstance(self._data[section], dict):
            self._data[section] = {}
        self._data[section][key] = value

    def get_all(self) -> dict:
        """Returns a deep copy of all configuration settings."""
        return copy.deepcopy(self._data)

    def validate(self) -> list:
        """Validates configuration parameters and returns a list of warnings/errors."""
        issues = []
        det = self.get("detection", default={})
        conf = det.get("confidence_threshold", 0.35)
        if not (0.05 <= conf <= 0.99):
            issues.append(f"Confidence threshold ({conf}) out of range [0.05, 0.99]")

        dens = self.get("density", default={})
        low_t = dens.get("low_threshold", 3)
        med_t = dens.get("medium_threshold", 7)
        if low_t >= med_t:
            issues.append(f"Density low threshold ({low_t}) must be less than medium threshold ({med_t})")

        return issues

    def _merge_dicts(self, base: dict, overlay: dict):
        """Recursively merges overlay into base dict."""
        for k, v in overlay.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._merge_dicts(base[k], v)
            else:
                base[k] = v

    def _get_hardcoded_defaults(self) -> dict:
        return {
            "system": {"app_name": "Smart Road Vision", "version": "1.0.0"},
            "detection": {
                "model_path": "models/yolov8n.pt",
                "confidence_threshold": 0.35,
                "iou_threshold": 0.45,
                "target_classes": [0, 2, 3, 5, 7],
                "tracker_type": "bytetrack.yaml"
            },
            "density": {"low_threshold": 3, "medium_threshold": 7},
            "wrong_way": {
                "enabled": True,
                "expected_direction": "TOP_TO_BOTTOM",
                "min_tracking_frames": 10,
                "min_displacement_px": 35,
                "consistency_ratio": 0.70
            },
            "red_light": {
                "enabled": True,
                "stop_line": {"x1": 80, "y1": 340, "x2": 560, "y2": 340},
                "traffic_signal_state": "RED",
                "prohibited_direction": "TOP_TO_BOTTOM"
            },
            "accident_detection": {
                "enabled": True,
                "sudden_stop_speed_drop_ratio": 0.75,
                "min_frames_stationary": 18,
                "proximity_distance_px": 55
            },
            "emergency_detection": {"enabled": True},
            "event_engine": {
                "cooldown_seconds": 8.0,
                "csv_log_path": "data/logs/events.csv",
                "json_log_path": "data/logs/events.json",
                "evidence_dir": "data/evidence"
            }
        }
