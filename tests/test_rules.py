"""
Unit Tests for Traffic Violation Rules and Density Analyzer.
Tests wrong-way trajectory analysis, virtual stop line intersection, and density classification.
"""

import unittest
from src.tracker import TrackedObject
from src.violation_detector import ViolationDetector
from src.traffic_analyzer import TrafficDensityAnalyzer


class TestTrafficRules(unittest.TestCase):

    def setUp(self):
        self.config = {
            "wrong_way": {
                "enabled": True,
                "expected_direction": "TOP_TO_BOTTOM",
                "min_tracking_frames": 5,
                "min_displacement_px": 20,
                "consistency_ratio": 0.70
            },
            "red_light": {
                "enabled": True,
                "stop_line": {"x1": 50, "y1": 200, "x2": 350, "y2": 200},
                "traffic_signal_state": "RED",
                "prohibited_direction": "TOP_TO_BOTTOM"
            },
            "density": {
                "enabled": True,
                "low_threshold": 2,
                "medium_threshold": 5
            }
        }
        self.violation_detector = ViolationDetector(self.config)
        self.density_analyzer = TrafficDensityAnalyzer(self.config)

    def test_wrong_way_detection(self):
        """Verifies wrong-way detection when vehicle moves upwards in a downwards lane."""
        obj = TrackedObject(
            track_id=10,
            class_id=2,
            class_name="car",
            bbox=[100, 250, 150, 300],
            center=(125, 275),
            frame_idx=1
        )
        # Simulate moving upward (y decreasing)
        for i in range(2, 8):
            y_pos = 275 - (i * 10)
            obj.update(bbox=[100, y_pos - 25, 150, y_pos + 25], center=(125, y_pos), frame_idx=i)

        alert = self.violation_detector.check_wrong_way(obj)
        self.assertIsNotNone(alert)
        self.assertEqual(alert["event_type"], "WRONG_WAY")
        self.assertEqual(alert["tracking_id"], 10)

    def test_red_light_stop_line_crossing(self):
        """Verifies red light violation when crossing line y=200 while signal is RED."""
        obj = TrackedObject(
            track_id=20,
            class_id=2,
            class_name="car",
            bbox=[100, 150, 150, 210],
            center=(125, 180),  # Above line
            frame_idx=1
        )
        # Step crossing line from y=180 to y=220
        obj.update(bbox=[100, 190, 150, 250], center=(125, 220), frame_idx=2)

        # 1. When signal is RED -> should trigger
        self.violation_detector.signal_state = "RED"
        alert = self.violation_detector.check_red_light(obj)
        self.assertIsNotNone(alert)
        self.assertEqual(alert["event_type"], "RED_LIGHT")

        # 2. When signal is GREEN -> should NOT trigger
        self.violation_detector.reset()
        self.violation_detector.signal_state = "GREEN"
        obj2 = TrackedObject(
            track_id=21,
            class_id=2,
            class_name="car",
            bbox=[100, 150, 150, 210],
            center=(125, 180),
            frame_idx=1
        )
        obj2.update(bbox=[100, 190, 150, 250], center=(125, 220), frame_idx=2)
        alert2 = self.violation_detector.check_red_light(obj2)
        self.assertIsNone(alert2)

    def test_traffic_density_thresholds(self):
        """Verifies density classification: <=2 is LOW, 3..5 is MEDIUM, >5 is HIGH."""
        # Test LOW (1 vehicle)
        tracks_low = [
            TrackedObject(1, 2, "car", [10, 10, 50, 50], (30, 30), 1)
        ]
        res_low = self.density_analyzer.analyze(tracks_low)
        self.assertEqual(res_low["level"], "LOW")

        # Test MEDIUM (4 vehicles)
        tracks_med = [
            TrackedObject(i, 2, "car", [10, 10, 50, 50], (30, 30), 1)
            for i in range(1, 5)
        ]
        res_med = self.density_analyzer.analyze(tracks_med)
        self.assertEqual(res_med["level"], "MEDIUM")

        # Test HIGH (7 vehicles)
        tracks_high = [
            TrackedObject(i, 2, "car", [10, 10, 50, 50], (30, 30), 1)
            for i in range(1, 8)
        ]
        res_high = self.density_analyzer.analyze(tracks_high)
        self.assertEqual(res_high["level"], "HIGH")

    def test_accident_detector_dual_engine(self):
        """Verifies PossibleAccidentDetector initializes YOLO11x and handles tracks."""
        from src.accident_detector import PossibleAccidentDetector
        acc_cfg = {
            "accident_detection": {
                "enabled": True,
                "use_ai_model": True,
                "ai_model_path": "models/accident_yolo11x.pt",
                "ai_confidence_threshold": 0.30,
                "ai_imgsz": 320,
                "sudden_stop_speed_drop_ratio": 0.75,
                "min_frames_stationary": 5,
                "proximity_distance_px": 60,
                "min_pre_accident_speed_px": 3.0
            }
        }
        detector = PossibleAccidentDetector(acc_cfg)
        self.assertTrue(detector.is_ai_loaded())
        info = detector.get_model_info()
        self.assertEqual(info["model_type"], "YOLO11x")
        self.assertTrue(info["is_loaded"])

        # Test kinematics sudden stop trigger
        v = TrackedObject(1, 2, "car", [100, 100, 150, 150], (125, 125), 1)
        # 15 frames of fast movement (speed = 10 px/f)
        for f in range(2, 22):
            v.update([100, 100 + (f * 10), 150, 150 + (f * 10)], (125, 125 + (f * 10)), f)
        # 13 frames of complete stop
        last_y = 125 + (21 * 10)
        for f in range(22, 35):
            v.update([100, last_y - 25, 150, last_y + 25], (125, last_y), f)

        alerts = detector.analyze([v])
        self.assertTrue(any(a["event_type"] == "POSSIBLE_ACCIDENT" for a in alerts))

        detector.reset()
        self.assertEqual(len(detector._alerted_accident_ids), 0)
        detector.stop()


if __name__ == "__main__":
    unittest.main()

