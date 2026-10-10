"""
Evidence Manager for Smart Road Vision.
Handles saving annotated snapshots (JPG) and video clips (MP4)
for traffic violations, accidents, and emergency events.
"""

import os
import cv2
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)

TYPE_FOLDER_MAP = {
    "WRONG_WAY": "wrong_way",
    "RED_LIGHT": "red_light",
    "NO_HELMET": "no_helmet",
    "POSSIBLE_ACCIDENT": "possible_accident",
    "EMERGENCY_VEHICLE": "emergency_vehicle",
    "ROAD_SAFETY": "road_safety"
}


class EvidenceManager:
    """Manages creation, organization, and retrieval of evidence files."""

    def __init__(self, base_evidence_dir: str = "data/evidence"):
        self.base_dir = base_evidence_dir
        self._ensure_folders()

    def _ensure_folders(self):
        """Ensures all evidence category subfolders exist."""
        os.makedirs(self.base_dir, exist_ok=True)
        for folder in TYPE_FOLDER_MAP.values():
            os.makedirs(os.path.join(self.base_dir, folder), exist_ok=True)

    def get_category_folder(self, event_type: str) -> str:
        folder_name = TYPE_FOLDER_MAP.get(event_type.upper(), "road_safety")
        path = os.path.join(self.base_dir, folder_name)
        os.makedirs(path, exist_ok=True)
        return path

    def save_snapshot(
        self,
        frame: Any,
        event_id: str,
        event_type: str,
        bbox: Optional[Tuple[int, int, int, int]] = None,
        extra_text: str = ""
    ) -> Optional[str]:
        """
        Saves an annotated evidence frame to disk as a JPG file.
        Returns the absolute or relative file path if successful, None otherwise.
        """
        if frame is None or frame.size == 0:
            logger.warning("Empty frame provided for evidence snapshot.")
            return None

        try:
            folder = self.get_category_folder(event_type)
            safe_id = event_id.replace(":", "-").replace(" ", "_")
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{event_type.lower()}_{timestamp_str}_{safe_id}.jpg"
            filepath = os.path.join(folder, filename)

            # Create annotated copy
            annotated = frame.copy()
            h, w = annotated.shape[:2]

            # Draw target bounding box if available
            if bbox:
                x1, y1, x2, y2 = [int(v) for v in bbox]
                # Highlighting box
                box_color = (0, 0, 255) if event_type in ["RED_LIGHT", "POSSIBLE_ACCIDENT"] else (0, 165, 255)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 3)
                cv2.rectangle(annotated, (x1 - 1, y1 - 25), (x1 + 160, y1), box_color, -1)
                cv2.putText(
                    annotated,
                    f"TARGET: {event_type}",
                    (x1 + 4, y1 - 7),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA
                )

            # Draw banner at top of evidence
            cv2.rectangle(annotated, (0, 0), (w, 42), (20, 24, 33), -1)
            cv2.line(annotated, (0, 42), (w, 42), (0, 0, 255) if "ACCIDENT" in event_type else (0, 200, 255), 2)

            # Evidence text info
            header_text = f"EVIDENCE [{event_type}] | ID: {event_id} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            cv2.putText(
                annotated,
                header_text,
                (12, 26),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

            if extra_text:
                cv2.putText(
                    annotated,
                    extra_text,
                    (12, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 255, 255),
                    1,
                    cv2.LINE_AA
                )

            # Save JPEG image
            success = cv2.imwrite(filepath, annotated, [cv2.IMWRITE_JPEG_QUALITY, 92])
            if success:
                logger.info(f"Saved evidence snapshot: {filepath}")
                return filepath
            else:
                logger.error(f"cv2.imwrite returned False for {filepath}")
                return None

        except Exception as e:
            logger.error(f"Error saving evidence snapshot: {e}")
            return None

    def save_clip_from_buffer(
        self,
        frame_buffer: List[Any],
        event_id: str,
        event_type: str,
        fps: int = 20
    ) -> Optional[str]:
        """
        Saves a rolling frame buffer to an MP4 video clip.
        Returns the clip file path or None.
        """
        if not frame_buffer:
            return None

        try:
            folder = self.get_category_folder(event_type)
            safe_id = event_id.replace(":", "-").replace(" ", "_")
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{event_type.lower()}_{timestamp_str}_{safe_id}.mp4"
            filepath = os.path.join(folder, filename)

            first_frame = frame_buffer[0]
            h, w = first_frame.shape[:2]

            # Use mp4v codec
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(filepath, fourcc, max(1, int(fps)), (w, h))

            for f in frame_buffer:
                if f is not None and f.shape[:2] == (h, w):
                    writer.write(f)

            writer.release()
            logger.info(f"Saved evidence clip: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save evidence clip: {e}")
            return None

    def get_all_evidence(self) -> List[Dict[str, Any]]:
        """Scans evidence directory and returns all found snapshots and clips."""
        items = []
        if not os.path.exists(self.base_dir):
            return items

        for root, _, files in os.walk(self.base_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in [".jpg", ".jpeg", ".png", ".mp4", ".avi"]:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.base_dir)
                    category = os.path.basename(root)
                    stat = os.stat(full_path)
                    items.append({
                        "filename": file,
                        "filepath": full_path,
                        "category": category,
                        "is_video": ext in [".mp4", ".avi"],
                        "size_kb": round(stat.st_size / 1024, 1),
                        "modified_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        "timestamp": stat.st_mtime
                    })

        # Sort newest first
        items.sort(key=lambda x: x["timestamp"], reverse=True)
        return items
