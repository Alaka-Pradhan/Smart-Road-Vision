"""
Event Logger for Smart Road Vision.
Handles persistent thread-safe event storage in CSV and JSON formats,
filtering, verification status updates, and export functionality.
"""

import os
import csv
import json
import threading
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
import pandas as pd

logger = logging.getLogger(__name__)

EVENT_FIELDS = [
    "event_id",
    "timestamp",
    "event_type",
    "severity",
    "camera_or_source",
    "tracking_id",
    "confidence",
    "description",
    "evidence_path",
    "verification_status"
]


class EventLogger:
    """Thread-safe event logger supporting CSV and JSON persistence."""

    def __init__(self, csv_path: str = "data/logs/events.csv", json_path: str = "data/logs/events.json"):
        self.csv_path = csv_path
        self.json_path = json_path
        self._lock = threading.Lock()
        self._init_files()

    def _init_files(self):
        """Ensures log directories and files exist with headers."""
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)

        # Initialize CSV if not present
        if not os.path.exists(self.csv_path) or os.path.getsize(self.csv_path) == 0:
            try:
                with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=EVENT_FIELDS)
                    writer.writeheader()
            except Exception as e:
                logger.error(f"Failed to initialize CSV log: {e}")

        # Initialize JSON if not present
        if not os.path.exists(self.json_path) or os.path.getsize(self.json_path) == 0:
            try:
                with open(self.json_path, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=2)
            except Exception as e:
                logger.error(f"Failed to initialize JSON log: {e}")

    def log_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Logs an event to both CSV and JSON safely.
        Returns True on success, False on failure.
        """
        record = {}
        for field in EVENT_FIELDS:
            record[field] = str(event_data.get(field, "-"))

        with self._lock:
            # 1. Write to CSV
            try:
                file_exists = os.path.exists(self.csv_path) and os.path.getsize(self.csv_path) > 0
                with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=EVENT_FIELDS)
                    if not file_exists:
                        writer.writeheader()
                    writer.writerow(record)
            except Exception as e:
                logger.error(f"Failed to write event to CSV: {e}")
                return False

            # 2. Write to JSON
            try:
                events = []
                if os.path.exists(self.json_path) and os.path.getsize(self.json_path) > 0:
                    try:
                        with open(self.json_path, "r", encoding="utf-8") as f:
                            events = json.load(f)
                    except Exception:
                        events = []
                events.append(record)
                with open(self.json_path, "w", encoding="utf-8") as f:
                    json.dump(events, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to write event to JSON: {e}")

        logger.info(f"Event logged: [{record.get('event_type')}] {record.get('event_id')}")
        return True

    def get_all_events(self) -> List[Dict[str, Any]]:
        """Retrieves all logged events as a list of dicts."""
        with self._lock:
            if not os.path.exists(self.csv_path):
                return []
            try:
                df = pd.read_csv(self.csv_path, dtype=str)
                df.fillna("-", inplace=True)
                return df.to_dict(orient="records")
            except Exception as e:
                logger.error(f"Error reading events: {e}")
                return []

    def get_dataframe(self) -> pd.DataFrame:
        """Returns events as a pandas DataFrame."""
        with self._lock:
            if not os.path.exists(self.csv_path):
                return pd.DataFrame(columns=EVENT_FIELDS)
            try:
                df = pd.read_csv(self.csv_path, dtype=str)
                df.fillna("-", inplace=True)
                return df
            except Exception as e:
                logger.error(f"Error loading dataframe: {e}")
                return pd.DataFrame(columns=EVENT_FIELDS)

    def update_verification_status(self, event_id: str, new_status: str) -> bool:
        """
        Updates the verification status of an event in both CSV and JSON.
        Valid statuses: 'CONFIRMED', 'FALSE POSITIVE', 'REVIEWED', 'PENDING REVIEW'.
        """
        with self._lock:
            # 1. Update CSV via pandas
            try:
                if not os.path.exists(self.csv_path):
                    return False
                df = pd.read_csv(self.csv_path, dtype=str)
                df.fillna("-", inplace=True)
                mask = df["event_id"] == str(event_id)
                if not mask.any():
                    logger.warning(f"Event ID {event_id} not found in CSV.")
                    return False
                df.loc[mask, "verification_status"] = new_status
                df.to_csv(self.csv_path, index=False, encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed updating CSV verification status: {e}")
                return False

            # 2. Update JSON
            try:
                if os.path.exists(self.json_path):
                    with open(self.json_path, "r", encoding="utf-8") as f:
                        events = json.load(f)
                    for ev in events:
                        if ev.get("event_id") == str(event_id):
                            ev["verification_status"] = new_status
                            break
                    with open(self.json_path, "w", encoding="utf-8") as f:
                        json.dump(events, f, indent=2)
            except Exception as e:
                logger.error(f"Failed updating JSON verification status: {e}")

        logger.info(f"Verification status for {event_id} updated to {new_status}")
        return True

    def export_filtered_csv(self, output_path: str, event_type: str = None, status: str = None) -> bool:
        """Exports filtered events to a new CSV file."""
        try:
            df = self.get_dataframe()
            if event_type and event_type != "ALL":
                df = df[df["event_type"].str.upper() == event_type.upper()]
            if status and status != "ALL":
                df = df[df["verification_status"].str.upper() == status.upper()]
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            df.to_csv(output_path, index=False, encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"Failed to export filtered CSV: {e}")
            return False

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Calculates summary statistics for dashboard display."""
        df = self.get_dataframe()
        if df.empty:
            return {
                "total_events": 0,
                "total_violations": 0,
                "possible_accidents": 0,
                "emergency_events": 0,
                "confirmed_count": 0,
                "pending_count": 0,
                "false_positive_count": 0,
                "violations_by_type": {},
                "events_by_severity": {}
            }

        total_events = len(df)
        violations = df[df["event_type"].isin(["WRONG_WAY", "RED_LIGHT", "NO_HELMET"])]
        accidents = df[df["event_type"] == "POSSIBLE_ACCIDENT"]
        emergency = df[df["event_type"] == "EMERGENCY_VEHICLE"]

        v_counts = df["event_type"].value_counts().to_dict()
        s_counts = df["severity"].value_counts().to_dict()

        return {
            "total_events": total_events,
            "total_violations": len(violations),
            "possible_accidents": len(accidents),
            "emergency_events": len(emergency),
            "confirmed_count": len(df[df["verification_status"] == "CONFIRMED"]),
            "pending_count": len(df[df["verification_status"] == "PENDING REVIEW"]),
            "false_positive_count": len(df[df["verification_status"] == "FALSE POSITIVE"]),
            "violations_by_type": v_counts,
            "events_by_severity": s_counts
        }
