"""
Multi-Object Tracking and Vehicle State Management for Smart Road Vision.
Maintains movement history, velocity vectors, directional estimation,
and unique vehicle counting across video frames.
"""

import time
import math
import logging
from collections import deque
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

logger = logging.getLogger(__name__)


class TrackedObject:
    """Represents a single tracked road object and its movement history."""

    def __init__(self, track_id: int, class_id: int, class_name: str, bbox: List[int], center: Tuple[int, int], frame_idx: int):
        self.track_id = track_id
        self.class_id = class_id
        self.class_name = class_name
        self.bbox = bbox
        self.center = center
        self.first_seen_frame = frame_idx
        self.last_seen_frame = frame_idx

        # Trajectory history: deque of (x, y, timestamp, frame_idx)
        self.history = deque(maxlen=40)
        self.history.append((center[0], center[1], time.time(), frame_idx))

        # Motion metrics
        self.velocity = (0.0, 0.0)  # px/frame (dx, dy)
        self.speed = 0.0  # px/frame
        self.direction_angle = 0.0  # degrees 0-360
        self.cardinal_direction = "UNKNOWN"
        self.is_stationary = False
        self.stationary_frames = 0
        self.total_distance_px = 0.0

    def update(self, bbox: List[int], center: Tuple[int, int], frame_idx: int):
        """Updates object state with new frame detection."""
        prev_center = self.center
        self.bbox = bbox
        self.center = center
        self.last_seen_frame = frame_idx

        dx = center[0] - prev_center[0]
        dy = center[1] - prev_center[1]
        dist = math.hypot(dx, dy)
        self.total_distance_px += dist

        self.history.append((center[0], center[1], time.time(), frame_idx))

        # Smoothed velocity calculation over last 5 points
        if len(self.history) >= 3:
            pts = list(self.history)[-5:]
            dt_frames = pts[-1][3] - pts[0][3]
            if dt_frames > 0:
                smooth_dx = (pts[-1][0] - pts[0][0]) / dt_frames
                smooth_dy = (pts[-1][1] - pts[0][1]) / dt_frames
                self.velocity = (smooth_dx, smooth_dy)
                self.speed = math.hypot(smooth_dx, smooth_dy)
                self.direction_angle = (math.degrees(math.atan2(smooth_dy, smooth_dx)) + 360) % 360

                # Determine direction
                if self.speed < 1.0:
                    self.is_stationary = True
                    self.stationary_frames += 1
                    self.cardinal_direction = "STATIONARY"
                else:
                    self.is_stationary = False
                    self.stationary_frames = 0
                    if 45 <= self.direction_angle < 135:
                        self.cardinal_direction = "TOP_TO_BOTTOM"  # South / Down
                    elif 135 <= self.direction_angle < 225:
                        self.cardinal_direction = "RIGHT_TO_LEFT"  # West / Left
                    elif 225 <= self.direction_angle < 315:
                        self.cardinal_direction = "BOTTOM_TO_TOP"  # North / Up
                    else:
                        self.cardinal_direction = "LEFT_TO_RIGHT"  # East / Right
        else:
            self.speed = dist
            self.velocity = (dx, dy)

    def get_net_displacement(self, frames_back: int = 15) -> Tuple[float, float, float]:
        """
        Returns (dx, dy, net_dist) over the requested number of historical frames.
        """
        if len(self.history) < 2:
            return 0.0, 0.0, 0.0

        hist_list = list(self.history)
        idx = max(0, len(hist_list) - frames_back)
        old_x, old_y = hist_list[idx][0], hist_list[idx][1]
        curr_x, curr_y = self.center[0], self.center[1]

        dx = curr_x - old_x
        dy = curr_y - old_y
        dist = math.hypot(dx, dy)
        return dx, dy, dist


class TrafficTracker:
    """Manages collection of active tracks and unique vehicle counts."""

    def __init__(self, max_missing_frames: int = 30):
        self.max_missing_frames = max_missing_frames
        self.active_tracks: Dict[int, TrackedObject] = {}
        self.unique_vehicle_ids = set()
        self.unique_counts_by_class: Dict[str, int] = {
            "car": 0,
            "motorcycle": 0,
            "bus": 0,
            "truck": 0,
            "person": 0
        }
        self.frame_counter = 0

    def update(self, detections: List[Dict[str, Any]]) -> List[TrackedObject]:
        """
        Updates tracking table with new frame detections.
        Returns list of active TrackedObjects.
        """
        self.frame_counter += 1
        current_seen_ids = set()

        for det in detections:
            track_id = det.get("track_id")
            if track_id is None:
                continue

            current_seen_ids.add(track_id)
            bbox = det["bbox"]
            center = det["center"]
            cls_name = det["class_name"]
            cls_id = det["class_id"]

            if track_id not in self.active_tracks:
                # New track
                self.active_tracks[track_id] = TrackedObject(
                    track_id, cls_id, cls_name, bbox, center, self.frame_counter
                )
                if track_id not in self.unique_vehicle_ids:
                    self.unique_vehicle_ids.add(track_id)
                    if cls_name in self.unique_counts_by_class:
                        self.unique_counts_by_class[cls_name] += 1
                    else:
                        self.unique_counts_by_class[cls_name] = 1
            else:
                # Update existing track
                self.active_tracks[track_id].update(bbox, center, self.frame_counter)

        # Prune stale tracks
        stale_ids = [
            tid for tid, obj in self.active_tracks.items()
            if (self.frame_counter - obj.last_seen_frame) > self.max_missing_frames
        ]
        for tid in stale_ids:
            del self.active_tracks[tid]

        return list(self.active_tracks.values())

    def get_active_count(self) -> int:
        """Returns number of currently visible road vehicles (excluding person)."""
        return sum(1 for obj in self.active_tracks.values() if obj.class_name != "person")

    def get_total_unique_vehicles(self) -> int:
        """Returns cumulative total of unique vehicles counted."""
        return sum(
            count for cname, count in self.unique_counts_by_class.items()
            if cname != "person"
        )

    def get_class_counts(self) -> Dict[str, int]:
        """Returns dictionary of unique vehicle counts by class."""
        return dict(self.unique_counts_by_class)

    def reset(self):
        """Resets all tracking states and cumulative counters."""
        self.active_tracks.clear()
        self.unique_vehicle_ids.clear()
        self.unique_counts_by_class = {
            "car": 0,
            "motorcycle": 0,
            "bus": 0,
            "truck": 0,
            "person": 0
        }
        self.frame_counter = 0
