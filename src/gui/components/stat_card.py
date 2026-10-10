"""
StatCard UI Component for Smart Road Vision.
Renders KPI metric cards with custom accents, values, and subtitles.
"""

import tkinter as tk
from ..theme import Theme


class StatCard(tk.Frame):
    """Modern dark KPI metric card."""

    def __init__(
        self,
        parent,
        title: str,
        value: str = "0",
        subtitle: str = "Normal",
        accent_color: str = Theme.ACCENT_BLUE,
        width: int = 160,
        height: int = 90
    ):
        super().__init__(
            parent,
            bg=Theme.BG_CARD,
            highlightbackground=Theme.BORDER,
            highlightthickness=1,
            bd=0,
            padx=12,
            pady=10
        )
        self.accent_color = accent_color

        # Top Accent stripe
        self.accent_bar = tk.Frame(self, bg=accent_color, height=3)
        self.accent_bar.pack(fill=tk.X, side=tk.TOP, pady=(0, 6))

        # Title
        self.lbl_title = tk.Label(
            self,
            text=title.upper(),
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_SECONDARY,
            font=Theme.FONT_SMALL,
            anchor="w"
        )
        self.lbl_title.pack(fill=tk.X)

        # Value
        self.lbl_value = tk.Label(
            self,
            text=str(value),
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_KPI_VAL,
            anchor="w"
        )
        self.lbl_value.pack(fill=tk.X, pady=(2, 2))

        # Subtitle / status
        self.lbl_sub = tk.Label(
            self,
            text=subtitle,
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL,
            anchor="w"
        )
        self.lbl_sub.pack(fill=tk.X)

    def set_value(self, val: Any, subtitle: str = None, color: str = None):
        """Updates metric value, subtitle, and color."""
        self.lbl_value.config(text=str(val))
        if subtitle is not None:
            self.lbl_sub.config(text=subtitle)
        if color:
            self.lbl_value.config(fg=color)
            self.accent_bar.config(bg=color)
