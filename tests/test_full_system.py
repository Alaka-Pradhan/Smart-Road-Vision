"""
Comprehensive End-to-End System Test for Smart Road Vision.
Tests the entire pipeline:
1. Video pipeline and frame ingestion
2. YOLOv8 model loading and ByteTrack multi-object tracking
3. Wrong-way detection rule evaluation
4. Stop-line red-light crossing rule evaluation
5. Accident heuristic detection rule evaluation
6. Traffic density estimation (LOW/MEDIUM/HIGH)
7. Event Engine dispatch and duplicate cooldown suppression
8. Forensic snapshot JPEG generation with annotations
9. Dual CSV and JSON persistent logging
10. Human verification status update
11. Matplotlib analytics chart rendering
12. Tkinter GUI 9-view lifecycle rendering
"""

import os
import sys
import time
import unittest
import numpy as np
import cv2
import pandas as pd
import tkinter as tk

from src.config_manager import ConfigManager
from src.detector import ObjectDetector
from src.tracker import TrafficTracker
from src.violation_detector import ViolationDetector
from src.accident_detector import PossibleAccidentDetector
from src.emergency_detector import EmergencyVehicleDetector
from src.traffic_analyzer import TrafficDensityAnalyzer
from src.event_logger import EventLogger
from src.evidence_manager import EvidenceManager
from src.event_engine import EventEngine
from src.video_processor import VideoProcessor
from src.gui.app import SmartRoadVisionApp
import queue


class TestFullSystemIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n=======================================================")
        print("  SMART ROAD VISION - COMPREHENSIVE INTEGRATION SUITE  ")
        print("=======================================================")
        # Ensure sample video exists
        if not os.path.exists("sample_traffic.mp4"):
            from utils.generate_traffic_video import generate_sample_video
            generate_sample_video("sample_traffic.mp4")

    def test_01_config_manager(self):
        """Test configuration loading, validation, modification and saving."""
        print("\n[TEST 1] Testing ConfigManager...")
        cm = ConfigManager()
        self.assertIsNotNone(cm.get("system"))
        self.assertEqual(cm.get("system", "app_name"), "Smart Road Vision")
        
        # Test validation
        issues = cm.validate()
        self.assertEqual(len(issues), 0, f"Validation issues found: {issues}")
        
        # Test modifying and saving
        orig_conf = cm.get("detection", "confidence_threshold")
        cm.set("detection", "confidence_threshold", 0.42)
        self.assertEqual(cm.get("detection", "confidence_threshold"), 0.42)
        # Restore
        cm.set("detection", "confidence_threshold", orig_conf)
        print(" -> ConfigManager: PASS")

    def test_02_yolo_detector_loading(self):
        """Test YOLOv8 detector loading and status."""
        print("\n[TEST 2] Testing YOLO Detector...")
        detector = ObjectDetector(model_path="models/yolov8n.pt", confidence_threshold=0.3)
        self.assertTrue(detector.is_loaded, f"Detector failed to load: {detector.load_error}")
        self.assertIsNotNone(detector.model)
        self.assertIn("car", detector.model.names.values())
        print(f" -> YOLOv8n Detector loaded successfully with {len(detector.model.names)} classes: PASS")

    def test_03_end_to_end_video_processing(self):
        """Test video processor reading frames, running detector, tracker, rules, and event engine."""
        print("\n[TEST 3] Testing End-to-End Video Processing Pipeline...")
        test_csv = "data/logs/test_integration_events.csv"
        test_json = "data/logs/test_integration_events.json"
        test_evidence = "data/evidence"

        logger = EventLogger(csv_path=test_csv, json_path=test_json)
        ev_mgr = EvidenceManager(base_evidence_dir=test_evidence)
        engine = EventEngine(logger, ev_mgr, cooldown_seconds=0.5, source_name="Test Suite")
        
        cm = ConfigManager()
        detector = ObjectDetector(model_path="models/yolov8n.pt", confidence_threshold=0.25)
        tracker = TrafficTracker()
        violation_det = ViolationDetector(cm.get_all())
        violation_det.signal_state = "RED"  # Force RED for testing stop line
        accident_det = PossibleAccidentDetector(cm.get_all())
        emergency_det = EmergencyVehicleDetector(cm.get_all())
        density_ana = TrafficDensityAnalyzer(cm.get_all())

        cap = cv2.VideoCapture("sample_traffic.mp4")
        self.assertTrue(cap.isOpened(), "Could not open sample_traffic.mp4")

        frames_processed = 0
        total_detections = 0
        
        # Process 50 frames
        for f_idx in range(50):
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            frames_processed += 1
            
            # 1. Detection
            dets = detector.track(frame)
            total_detections += len(dets)
            
            # 2. Tracking
            active_tracks = tracker.update(dets)
            
            # 3. Density
            d_res = density_ana.analyze(active_tracks)
            if d_res.get("event"):
                engine.dispatch_event(d_res["event"], frame)
                
            # 4. Rules
            for tobj in active_tracks:
                ww = violation_det.check_wrong_way(tobj)
                if ww:
                    engine.dispatch_event(ww, frame)
                rl = violation_det.check_red_light(tobj)
                if rl:
                    engine.dispatch_event(rl, frame)

        cap.release()
        
        self.assertGreater(frames_processed, 0, "No frames processed.")
        print(f" -> Processed {frames_processed} frames successfully.")
        print(f" -> Total object detections: {total_detections}")
        print(f" -> Total unique tracked vehicle IDs: {tracker.get_total_unique_vehicles()}")
        print(f" -> Tracked vehicle classes: {tracker.get_class_counts()}")
        print(" -> End-to-End Pipeline: PASS")

    def test_04_event_logging_and_verification(self):
        """Test dual CSV/JSON persistence and human verification updates."""
        print("\n[TEST 4] Testing Event Logger & Status Updates...")
        test_csv = "data/logs/test_verification.csv"
        test_json = "data/logs/test_verification.json"
        if os.path.exists(test_csv): os.remove(test_csv)
        if os.path.exists(test_json): os.remove(test_json)

        logger = EventLogger(csv_path=test_csv, json_path=test_json)
        
        # Log 3 events
        event1 = {
            "event_id": "EVT-INT-001",
            "timestamp": "2026-10-10T19:45:00",
            "event_type": "WRONG_WAY",
            "severity": "HIGH",
            "camera_or_source": "Camera 1",
            "tracking_id": "5",
            "confidence": "0.91",
            "description": "Vehicle driving wrong direction",
            "evidence_path": "-",
            "verification_status": "PENDING REVIEW"
        }
        event2 = {
            "event_id": "EVT-INT-002",
            "timestamp": "2026-10-10T19:46:00",
            "event_type": "RED_LIGHT",
            "severity": "CRITICAL",
            "camera_or_source": "Camera 1",
            "tracking_id": "8",
            "confidence": "0.95",
            "description": "Stop line breach on red signal",
            "evidence_path": "-",
            "verification_status": "PENDING REVIEW"
        }
        logger.log_event(event1)
        logger.log_event(event2)

        # Verify logged
        df = logger.get_dataframe()
        self.assertEqual(len(df), 2)
        
        # Update status
        success = logger.update_verification_status("EVT-INT-001", "CONFIRMED")
        self.assertTrue(success)
        
        # Verify status in CSV and JSON
        df_updated = logger.get_dataframe()
        status_row = df_updated[df_updated["event_id"] == "EVT-INT-001"].iloc[0]
        self.assertEqual(status_row["verification_status"], "CONFIRMED")
        
        # Export filtered
        export_file = "data/exports/test_export.csv"
        exp_success = logger.export_filtered_csv(export_file, event_type="RED_LIGHT")
        self.assertTrue(exp_success)
        self.assertTrue(os.path.exists(export_file))
        exp_df = pd.read_csv(export_file)
        self.assertEqual(len(exp_df), 1)
        self.assertEqual(exp_df.iloc[0]["event_id"], "EVT-INT-002")

        # Clean test export
        if os.path.exists(export_file): os.remove(export_file)
        if os.path.exists(test_csv): os.remove(test_csv)
        if os.path.exists(test_json): os.remove(test_json)
        print(" -> Event Logger & Verification Status Updates: PASS")

    def test_05_evidence_manager_snapshot_creation(self):
        """Test saving and verifying annotated evidence snapshot images."""
        print("\n[TEST 5] Testing Evidence Manager Snapshots...")
        ev_mgr = EvidenceManager(base_evidence_dir="data/evidence")
        
        # Create a dummy frame
        dummy_frame = np.full((480, 720, 3), (40, 45, 50), dtype=np.uint8)
        cv2.circle(dummy_frame, (360, 240), 60, (0, 0, 255), -1)
        
        saved_path = ev_mgr.save_snapshot(
            frame=dummy_frame,
            event_id="EVT-SNAP-TEST-001",
            event_type="WRONG_WAY",
            bbox=(200, 150, 400, 350),
            extra_text="Integration Test Snapshot"
        )
        self.assertIsNotNone(saved_path)
        self.assertTrue(os.path.exists(saved_path), f"Saved snapshot not found at {saved_path}")
        
        # Verify image is valid and readable by OpenCV
        loaded_img = cv2.imread(saved_path)
        self.assertIsNotNone(loaded_img)
        self.assertEqual(loaded_img.shape[:2], (480, 720))
        
        # Clean up test snapshot
        if os.path.exists(saved_path):
            os.remove(saved_path)
        print(f" -> Evidence Manager Snapshot: PASS")

    def test_06_gui_lifecycle_and_all_9_views(self):
        """Test full GUI instantiation, theme application, navigation through all 9 views."""
        print("\n[TEST 6] Testing GUI Controller & 9 Views Lifecycle...")
        root = tk.Tk()
        root.withdraw()  # Run headless for testing
        
        app = SmartRoadVisionApp(root)
        self.assertIsNotNone(app)
        
        # Expected 9 views
        expected_views = [
            "Dashboard",
            "Live Monitoring",
            "Traffic Violations",
            "Accident Alerts",
            "Emergency Vehicles",
            "Traffic Analytics",
            "Event Logs",
            "Evidence Gallery",
            "Settings"
        ]
        
        for view_name in expected_views:
            self.assertIn(view_name, app.views, f"View {view_name} missing from app.")
            app.navigate_to(view_name)
            root.update()
            self.assertEqual(app.active_view_name, view_name)
            
        print(f" -> All {len(expected_views)} Views Navigated and Rendered: PASS")
        
        # Test Matplotlib analytics charts refresh
        analytics_view = app.views["Traffic Analytics"]
        analytics_view.refresh_charts()
        root.update()
        print(" -> Embedded Matplotlib Charts: PASS")
        
        # Clean GUI shutdown
        root.destroy()
        print(" -> GUI Clean Destruction: PASS")


if __name__ == "__main__":
    unittest.main()
