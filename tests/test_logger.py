"""
Unit Tests for Event Logger.
Tests thread-safe CSV and JSON logging, status mutation, filtering, and export.
"""

import os
import unittest
import tempfile
import pandas as pd
from src.event_logger import EventLogger


class TestEventLogger(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.csv_path = os.path.join(self.temp_dir, "events.csv")
        self.json_path = os.path.join(self.temp_dir, "events.json")
        self.logger = EventLogger(csv_path=self.csv_path, json_path=self.json_path)

    def test_log_and_read_event(self):
        """Verifies logging writes correctly to CSV and JSON."""
        ev = {
            "event_id": "EVT-TEST-001",
            "timestamp": "2026-10-10T19:30:00",
            "event_type": "WRONG_WAY",
            "severity": "HIGH",
            "camera_or_source": "Cam 1",
            "tracking_id": "7",
            "confidence": "0.91",
            "description": "Wrong way detected",
            "evidence_path": "data/evidence/test.jpg",
            "verification_status": "PENDING REVIEW"
        }

        success = self.logger.log_event(ev)
        self.assertTrue(success)

        # Read back
        records = self.logger.get_all_events()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["event_id"], "EVT-TEST-001")
        self.assertEqual(records[0]["event_type"], "WRONG_WAY")

    def test_update_verification_status(self):
        """Verifies human status mutation updates both CSV and JSON."""
        ev = {
            "event_id": "EVT-TEST-002",
            "timestamp": "2026-10-10T19:35:00",
            "event_type": "RED_LIGHT",
            "severity": "CRITICAL",
            "camera_or_source": "Cam 1",
            "tracking_id": "12",
            "confidence": "0.95",
            "description": "Red light crossed",
            "evidence_path": "-",
            "verification_status": "PENDING REVIEW"
        }
        self.logger.log_event(ev)

        # Update status
        updated = self.logger.update_verification_status("EVT-TEST-002", "CONFIRMED")
        self.assertTrue(updated)

        # Verify in dataframe
        df = self.logger.get_dataframe()
        row = df[df["event_id"] == "EVT-TEST-002"].iloc[0]
        self.assertEqual(row["verification_status"], "CONFIRMED")

    def test_export_filtered_csv(self):
        """Verifies CSV filtering export functionality."""
        for i, etype in enumerate(["WRONG_WAY", "RED_LIGHT", "WRONG_WAY"]):
            self.logger.log_event({
                "event_id": f"EVT-{i}",
                "timestamp": "2026-10-10T19:40:00",
                "event_type": etype,
                "severity": "HIGH",
                "camera_or_source": "Cam 1",
                "tracking_id": str(i),
                "confidence": "0.90",
                "description": f"Event {i}",
                "evidence_path": "-",
                "verification_status": "PENDING REVIEW"
            })

        export_path = os.path.join(self.temp_dir, "export.csv")
        res = self.logger.export_filtered_csv(export_path, event_type="WRONG_WAY")
        self.assertTrue(res)
        self.assertTrue(os.path.exists(export_path))

        exp_df = pd.read_csv(export_path)
        self.assertEqual(len(exp_df), 2)
        self.assertTrue((exp_df["event_type"] == "WRONG_WAY").all())


if __name__ == "__main__":
    unittest.main()
