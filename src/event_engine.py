"""
Central Event Engine for Smart Road Vision.
Coordinates incident generation, duplicate cooldown suppression,
evidence capture dispatch, persistent logging, and GUI notifications.
"""

import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from .event_logger import EventLogger
from .evidence_manager import EvidenceManager

logger = logging.getLogger(__name__)


class EventEngine:
    """Central engine processing events across all traffic monitoring detectors."""

    def __init__(
        self,
        event_logger: EventLogger,
        evidence_manager: EvidenceManager,
        cooldown_seconds: float = 8.0,
        source_name: str = "Live Feed"
    ):
        self.logger = event_logger
        self.evidence_mgr = evidence_manager
        self.cooldown_seconds = cooldown_seconds
        self.source_name = source_name

        # Duplicate suppression table: (event_type, tracking_id) -> last_timestamp
        self._cooldown_table: Dict[tuple, float] = {}
        self._recent_events: List[Dict[str, Any]] = []
        self._event_counter = 0

        # Optional GUI notification callback
        self.on_event_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    def set_source_name(self, name: str):
        """Sets the current video source identifier."""
        self.source_name = name

    def set_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Registers a callback function for real-time GUI event notification."""
        self.on_event_callback = callback

    def dispatch_event(
        self,
        raw_event: Dict[str, Any],
        current_frame: Any = None,
        frame_buffer: Optional[List[Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Processes a raw event from a detector, checks cooldown, creates evidence,
        logs to file, and alerts GUI listeners.
        """
        event_type = raw_event.get("event_type", "ROAD_SAFETY")
        tracking_id = raw_event.get("tracking_id", "-")
        now = time.time()

        # Cooldown check
        cooldown_key = (event_type, str(tracking_id))
        if cooldown_key in self._cooldown_table:
            elapsed = now - self._cooldown_table[cooldown_key]
            if elapsed < self.cooldown_seconds:
                # Suppress duplicate alert within cooldown period
                return None

        self._cooldown_table[cooldown_key] = now
        self._event_counter += 1

        # Generate unique event ID
        dt = datetime.now()
        event_id = f"EVT-{dt.strftime('%Y%m%d-%H%M%S')}-{self._event_counter:03d}"
        iso_timestamp = dt.isoformat(timespec="seconds")

        # Save evidence snapshot
        evidence_path = "-"
        bbox = raw_event.get("bbox")
        if current_frame is not None:
            desc = raw_event.get("description", "")
            saved_img = self.evidence_mgr.save_snapshot(
                frame=current_frame,
                event_id=event_id,
                event_type=event_type,
                bbox=bbox,
                extra_text=desc
            )
            if saved_img:
                evidence_path = saved_img

        # Save evidence clip if requested and available
        if frame_buffer and len(frame_buffer) > 10 and event_type in ["POSSIBLE_ACCIDENT", "RED_LIGHT"]:
            clip_path = self.evidence_mgr.save_clip_from_buffer(
                frame_buffer=frame_buffer,
                event_id=event_id,
                event_type=event_type
            )
            if clip_path and evidence_path == "-":
                evidence_path = clip_path

        # Standardized event record
        event_record = {
            "event_id": event_id,
            "timestamp": iso_timestamp,
            "event_type": event_type,
            "severity": raw_event.get("severity", "MEDIUM"),
            "camera_or_source": self.source_name,
            "tracking_id": str(tracking_id),
            "confidence": f"{float(raw_event.get('confidence', 0.85)):.2f}",
            "description": raw_event.get("description", "Safety alert triggered"),
            "evidence_path": evidence_path,
            "verification_status": "PENDING REVIEW"
        }

        # Persist to CSV and JSON
        self.logger.log_event(event_record)

        # Store in recent cache
        self._recent_events.append(event_record)
        if len(self._recent_events) > 50:
            self._recent_events.pop(0)

        # Notify GUI callback safely
        if self.on_event_callback:
            try:
                self.on_event_callback(event_record)
            except Exception as e:
                logger.error(f"Error executing GUI event callback: {e}")

        return event_record

    def get_recent_events(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Returns the most recent events in reverse chronological order."""
        return list(reversed(self._recent_events[-limit:]))

    def reset(self):
        """Resets cooldowns and in-memory caches."""
        self._cooldown_table.clear()
        self._recent_events.clear()
        self._event_counter = 0
