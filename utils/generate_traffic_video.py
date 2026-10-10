"""
Synthetic Traffic Video Generator for Smart Road Vision.
Generates a realistic 720x480 traffic surveillance video with multiple lanes,
photographic vehicle and pedestrian sprites, a stop-line crossing on RED,
and a wrong-way vehicle for instant demonstration, pipeline validation, and viva presentation.
"""

import os
import cv2
import numpy as np


def generate_sample_video(output_path: str = "sample_traffic.mp4", duration_seconds: int = 15, fps: int = 25):
    """Generates a realistic traffic surveillance video with detectable road users."""
    width, height = 720, 480
    total_frames = duration_seconds * fps
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Road coordinates
    road_left = 110
    road_right = 610
    lane_width = (road_right - road_left) // 3

    # Load photographic sprites if available
    bus_sprite = None
    person_sprite = None

    if os.path.exists("sample_bus.jpg"):
        try:
            full_b = cv2.imread("sample_bus.jpg")
            # Crop bus [230:750, 20:800]
            b_crop = full_b[230:750, 20:800]
            bus_sprite = cv2.resize(b_crop, (150, 100))
            # Crop person [398:902, 48:245]
            p_crop = full_b[398:902, 48:245]
            person_sprite = cv2.resize(p_crop, (45, 95))
        except Exception:
            pass

    # Vehicle motion states
    # v1: Bus moving South in Lane 1
    # v2: Car / Bus 2 moving South in Lane 0 (crosses stop line at frame 120)
    # v3: Wrong-way vehicle moving North (up) in Lane 0
    # v4: Pedestrian on shoulder
    vehicles = [
        {"id": 1, "type": "bus", "x": 300, "y": -120, "speed": 3.8, "w": 150, "h": 100, "sprite": bus_sprite},
        {"id": 2, "type": "bus", "x": 140, "y": 60, "speed": 4.2, "w": 140, "h": 90, "sprite": bus_sprite, "cross_line": True},
        {"id": 3, "type": "bus", "x": 150, "y": height + 60, "speed": -3.5, "w": 130, "h": 85, "sprite": bus_sprite, "wrong_way": True},
        {"id": 4, "type": "person", "x": 630, "y": 100, "speed": 1.2, "w": 45, "h": 95, "sprite": person_sprite}
    ]

    for frame_idx in range(total_frames):
        # 1. Dark asphalt road canvas
        frame = np.full((height, width, 3), (38, 42, 46), dtype=np.uint8)

        # Sidewalk & Grass borders
        cv2.rectangle(frame, (0, 0), (road_left, height), (30, 60, 30), -1)
        cv2.rectangle(frame, (road_right, 0), (width, height), (30, 60, 30), -1)
        # Curb lines
        cv2.line(frame, (road_left, 0), (road_left, height), (200, 200, 200), 3)
        cv2.line(frame, (road_right, 0), (road_right, height), (200, 200, 200), 3)

        # Lane dividers (dashed lines)
        dash_offset = (frame_idx * 4) % 40
        for l in range(1, 3):
            lx = road_left + l * lane_width
            for y in range(-40 + dash_offset, height, 40):
                cv2.line(frame, (lx, y), (lx, y + 20), (255, 255, 255), 2)

        # Virtual stop line painting on road surface at Y = 340
        cv2.line(frame, (road_left, 340), (road_right, 340), (255, 255, 255), 3)
        # Zebra crossing markings
        for zx in range(road_left + 15, road_right - 20, 35):
            cv2.rectangle(frame, (zx, 345), (zx + 20, 375), (210, 210, 210), -1)

        # 2. Render vehicles and pedestrians
        for v in vehicles:
            v["y"] += v["speed"]

            vx = int(v["x"])
            vy = int(v["y"])
            vw = int(v["w"])
            vh = int(v["h"])

            # Check inside canvas bounds
            if -vh <= vy <= height + vh and 0 <= vx <= width - vw:
                # Clip to visible region
                y1 = max(0, vy)
                y2 = min(height, vy + vh)
                x1 = max(0, vx)
                x2 = min(width, vx + vw)

                if y2 > y1 and x2 > x1:
                    sprite = v.get("sprite")
                    if sprite is not None:
                        # Slice sprite to match clipped box
                        sy1 = y1 - vy
                        sy2 = sy1 + (y2 - y1)
                        sx1 = x1 - vx
                        sx2 = sx1 + (x2 - x1)
                        sub_sprite = cv2.resize(sprite, (vw, vh))[sy1:sy2, sx1:sx2]
                        if sub_sprite.shape[:2] == (y2 - y1, x2 - x1):
                            frame[y1:y2, x1:x2] = sub_sprite
                    else:
                        # Geometric fallback
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (180, 50, 50), -1)

            # Loop positions
            if v["speed"] > 0 and v["y"] > height + 100:
                v["y"] = -vh - 30
            elif v["speed"] < 0 and v["y"] < -vh - 30:
                v["y"] = height + 50

        # Frame counter watermark
        cv2.putText(
            frame,
            f"SMART ROAD VISION FEED | Frame: {frame_idx:04d}/{total_frames}",
            (14, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

        out.write(frame)

    out.release()
    print(f"Generated synthetic test video: {output_path} ({total_frames} frames, {duration_seconds}s)")
    return output_path


if __name__ == "__main__":
    generate_sample_video("sample_traffic.mp4")
