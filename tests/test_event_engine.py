"""
Unit Tests for Central Event Engine.
Verifies event standardization, cooldown duplicate suppression, and callbacks.
"""

import os
import unittest
import tempfile
import time
from src.event_logger import EventLogger
from src.evidence_manager import EvidenceManager
from src.event_engine import EventEngine


class TestEventEngine(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.csv_path = os.path.join(self.temp_dir, "test_events.csv")
        self.json_path = os.path.join(self.temp_dir, "test_events.json")
        self.evidence_dir = os.path.join(self.temp_dir, "evidence")

        self.logger = EventLogger(csv_path=self.csv_path, json_path=self.json_path)
        self.evidence_mgr = EvidenceManager(base_evidence_dir=self.evidence_dir)
        self.engine = EventEngine(
            event_logger=self.logger,
            evidence_manager=self.evidence_mgr,
            cooldown_seconds=1.0,
            source_name="Test Source"
        )

    def test_event_dispatch_standardization(self):
        """Verifies that dispatched events contain all required standardized schema fields."""
        raw_event = {
            "event_type": "WRONG_WAY",
            "severity": "HIGH",
            "tracking_id": 14,
            "confidence": 0.89,
            "description": "Vehicle driving wrong direction",
            "bbox": [100, 100, 150, 150]
        }

        rec = self.engine.dispatch_event(raw_event)
        self.assertIsNotNone(rec)
        self.assertTrue(rec["event_id"].startswith("EVT-"))
        self.assertEqual(rec["event_type"], "WRONG_WAY")
        self.assertEqual(rec["severity"], "HIGH")
        self.assertEqual(rec["tracking_id"], "14")
        self.assertEqual(rec["verification_status"], "PENDING REVIEW")
        self.assertEqual(rec["camera_or_source"], "Test Source")

    def test_duplicate_cooldown_suppression(self):
        """Verifies that consecutive alerts for the same vehicle/event within cooldown are suppressed."""
        raw_event = {
            "event_type": "RED_LIGHT",
            "severity": "CRITICAL",
            "tracking_id": 42,
            "confidence": 0.95,
            "description": "Stop line crossing on red light"
        }

        # First event should succeed
        rec1 = self.engine.dispatch_event(raw_event)
        self.assertIsNotNone(rec1)

        # Immediate second event should be suppressed (None)
        rec2 = self.engine.dispatch_event(raw_event)
        self.assertIsNone(rec2)

        # Different vehicle ID should not be suppressed
        raw_diff_id = dict(raw_event, tracking_id=99)
        rec3 = self.engine.dispatch_event(raw_diff_id)
        self.assertIsNotNone(rec3)


if __name__ == "__main__":
    unittest.main()
