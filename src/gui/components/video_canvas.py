"""
VideoCanvas UI Component for Smart Road Vision.
Renders OpenCV video frames inside Tkinter with aspect ratio preservation
and modern standby graphics when inactive.
"""

import cv2
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
from ..theme import Theme


class VideoCanvas(tk.Canvas):
    """Custom Tkinter Canvas optimized for real-time video display."""

    def __init__(self, parent, default_width: int = 720, default_height: int = 420, **kwargs):
        super().__init__(
            parent,
            bg="#080e1a",
            highlightthickness=1,
            highlightbackground=Theme.BORDER,
            width=default_width,
            height=default_height,
            **kwargs
        )
        self.default_width = default_width
        self.default_height = default_height
        self._current_photo = None
        self._image_item = None
        self._standby_rendered = False
        self.bind("<Configure>", self._on_resize)
        self.after(50, self.render_standby)

    def _on_resize(self, event):
        """Redraws standby if canvas is resized and no active image."""
        if not self._current_photo or self._standby_rendered:
            self.render_standby()

    def display_frame(self, bgr_frame: np.ndarray):
        """Converts an OpenCV BGR frame to ImageTk and renders centered on canvas."""
        if bgr_frame is None or bgr_frame.size == 0:
            return

        try:
            canv_w = self.winfo_width()
            canv_h = self.winfo_height()
            if canv_w < 50 or canv_h < 50:
                canv_w = self.default_width
                canv_h = self.default_height

            fh, fw = bgr_frame.shape[:2]

            # Aspect ratio calculation
            scale = min(canv_w / fw, canv_h / fh)
            new_w = max(1, int(fw * scale))
            new_h = max(1, int(fh * scale))

            # Resize OpenCV image
            resized = cv2.resize(bgr_frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

            # Pillow image
            img = Image.fromarray(rgb_frame)
            self._current_photo = ImageTk.PhotoImage(image=img)

            pos_x = (canv_w - new_w) // 2
            pos_y = (canv_h - new_h) // 2

            if self._standby_rendered or self._image_item is None:
                self.delete("all")
                self._image_item = self.create_image(pos_x, pos_y, anchor="nw", image=self._current_photo)
                self._standby_rendered = False
            else:
                self.coords(self._image_item, pos_x, pos_y)
                self.itemconfig(self._image_item, image=self._current_photo)

        except Exception:
            pass

    def render_standby(self, message: str = "AI SURVEILLANCE FEED READY"):
        """Draws a modern high-contrast standby HUD placeholder with clear instructions."""
        self.delete("all")
        self._current_photo = None
        self._image_item = None

        cw = self.winfo_width() if self.winfo_width() > 50 else self.default_width
        ch = self.winfo_height() if self.winfo_height() > 50 else self.default_height

        # 1. Cybernetic grid background (high contrast)
        for x in range(0, cw, 40):
            self.create_line(x, 0, x, ch, fill="#121d30", width=1)
        for y in range(0, ch, 40):
            self.create_line(0, y, cw, y, fill="#121d30", width=1)

        cx, cy = cw // 2, ch // 2

        # 2. Concentric radar telemetry circles
        for r in [50, 100, 160]:
            if r * 2 < min(cw, ch):
                self.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#1d2e4a", width=1)

        # 3. Precision reticle crosshairs
        self.create_line(max(10, cx - 180), cy, min(cw - 10, cx + 180), cy, fill="#253858", width=1)
        self.create_line(cx, max(10, cy - 140), cx, min(ch - 10, cy + 140), fill="#253858", width=1)

        # 4. Viewport corner brackets
        corner_sz = 16
        pad = 12
        # Top-Left
        self.create_line(pad, pad, pad + corner_sz, pad, fill=Theme.ACCENT_BLUE, width=2)
        self.create_line(pad, pad, pad, pad + corner_sz, fill=Theme.ACCENT_BLUE, width=2)
        # Top-Right
        self.create_line(cw - pad, pad, cw - pad - corner_sz, pad, fill=Theme.ACCENT_BLUE, width=2)
        self.create_line(cw - pad, pad, cw - pad, pad + corner_sz, fill=Theme.ACCENT_BLUE, width=2)
        # Bottom-Left
        self.create_line(pad, ch - pad, pad + corner_sz, ch - pad, fill=Theme.ACCENT_BLUE, width=2)
        self.create_line(pad, ch - pad, pad, ch - pad - corner_sz, fill=Theme.ACCENT_BLUE, width=2)
        # Bottom-Right
        self.create_line(cw - pad, ch - pad, cw - pad - corner_sz, ch - pad, fill=Theme.ACCENT_BLUE, width=2)
        self.create_line(cw - pad, ch - pad, cw - pad, ch - pad - corner_sz, fill=Theme.ACCENT_BLUE, width=2)

        # 5. Top Left HUD status text
        self.create_text(
            pad + 24, pad + 10,
            text="CAM 01 // MAIN CORRIDOR [STANDBY]",
            fill="#38bdf8",
            font=("Segoe UI", 9, "bold"),
            anchor="w"
        )
        self.create_text(
            cw - pad - 10, pad + 10,
            text="FPS: 30.0  |  720p HD",
            fill="#64748b",
            font=("Segoe UI", 9),
            anchor="e"
        )

        # 6. Center Standby Card (Vibrant, high-contrast, informative)
        card_w = min(220, (cw - 60) // 2)
        card_h = 48
        self.create_rectangle(
            cx - card_w, cy - card_h,
            cx + card_w, cy + card_h,
            fill="#0f1b2e",
            outline="#0284c7",
            width=2
        )

        # Glowing green status dot + header
        self.create_oval(cx - card_w + 16, cy - 24, cx - card_w + 24, cy - 16, fill="#10b981", outline="")
        self.create_text(
            cx - card_w + 32, cy - 20,
            text=message,
            fill="#38bdf8",
            font=("Segoe UI", 11, "bold"),
            anchor="w"
        )

        # Primary action prompt
        self.create_text(
            cx, cy + 4,
            text="Click '▶ START LIVE AI MONITORING' to launch detection",
            fill="#f8fafc",
            font=("Segoe UI", 10, "bold")
        )

        # Tech stack pill
        self.create_text(
            cx, cy + 26,
            text="Ultralytics YOLOv8 • ByteTrack Tracker • Road Safety Rules",
            fill="#94a3b8",
            font=("Segoe UI", 8)
        )

        self._standby_rendered = True
