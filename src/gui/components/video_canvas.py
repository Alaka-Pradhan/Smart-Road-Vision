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

    def __init__(self, parent, default_width: int = 720, default_height: int = 480, **kwargs):
        super().__init__(
            parent,
            bg="#050811",
            highlightthickness=1,
            highlightbackground=Theme.BORDER,
            width=default_width,
            height=default_height,
            **kwargs
        )
        self.default_width = default_width
        self.default_height = default_height
        self._current_photo = None
        self._standby_rendered = False
        self.bind("<Configure>", self._on_resize)
        self.render_standby()

    def _on_resize(self, event):
        """Redraws standby if canvas is resized and no active image."""
        if not self._current_photo:
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

            # Draw centered
            self.delete("all")
            pos_x = (canv_w - new_w) // 2
            pos_y = (canv_h - new_h) // 2
            self.create_image(pos_x, pos_y, anchor="nw", image=self._current_photo)
            self._standby_rendered = False

        except Exception:
            pass

    def render_standby(self, message: str = "CAMERA STANDBY // AWAITING STREAM"):
        """Draws a high-tech radar standby placeholder."""
        self.delete("all")
        self._current_photo = None

        cw = max(self.winfo_width(), self.default_width)
        ch = max(self.winfo_height(), self.default_height)

        # Background grid lines
        for x in range(0, cw, 40):
            self.create_line(x, 0, x, ch, fill="#0c1322", width=1)
        for y in range(0, ch, 40):
            self.create_line(0, y, cw, y, fill="#0c1322", width=1)

        cx, cy = cw // 2, ch // 2

        # Concentric radar rings
        for r in [40, 80, 120]:
            self.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#162238", width=1)

        # Crosshairs
        self.create_line(cx - 140, cy, cx + 140, cy, fill="#1e2f4d", width=1)
        self.create_line(cx, cy - 140, cx, cy + 140, fill="#1e2f4d", width=1)

        # Standby text badge
        self.create_rectangle(cx - 180, cy - 20, cx + 180, cy + 20, fill="#111a2e", outline=Theme.BORDER)
        self.create_text(
            cx, cy,
            text=f"● {message}",
            fill=Theme.ACCENT_BLUE,
            font=("Segoe UI", 10, "bold")
        )
        self._standby_rendered = True
