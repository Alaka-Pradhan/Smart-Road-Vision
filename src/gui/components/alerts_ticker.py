"""
Alerts Ticker Component for Smart Road Vision.
Renders real-time incoming alerts with severity color pills and timestamps.
"""

import tkinter as tk
from typing import List, Dict, Any, Callable, Optional
from ..theme import Theme


class AlertsTicker(tk.Frame):
    """Recent alerts list panel with colored severity indicators."""

    def __init__(self, parent, on_select_callback: Optional[Callable[[Dict[str, Any]], None]] = None, **kwargs):
        super().__init__(parent, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1, **kwargs)
        self.on_select = on_select_callback

        # Header
        hdr = tk.Frame(self, bg=Theme.BG_CARD, padx=10, pady=8)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text="RECENT SAFETY ALERTS",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SUBTITLE
        ).pack(side=tk.LEFT)

        # Scrollable container
        self.canvas = tk.Canvas(self, bg=Theme.BG_CARD, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.items_frame = tk.Frame(self.canvas, bg=Theme.BG_CARD)

        self.items_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.items_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.bind("<Configure>", self._on_resize)
        self.render_empty()

    def _on_resize(self, event):
        """Adjusts canvas width."""
        self.canvas.itemconfig(self.canvas_window, width=event.width - 20)

    def render_empty(self):
        """Shows empty state message."""
        for w in self.items_frame.winfo_children():
            w.destroy()
        lbl = tk.Label(
            self.items_frame,
            text="No recent incidents detected. System monitoring normal.",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL,
            pady=20
        )
        lbl.pack(fill=tk.X)

    def update_events(self, events: List[Dict[str, Any]]):
        """Populates feed with latest events."""
        for w in self.items_frame.winfo_children():
            w.destroy()

        if not events:
            self.render_empty()
            return

        for ev in events[:12]:
            self._create_alert_row(ev)

    def _create_alert_row(self, ev: Dict[str, Any]):
        """Creates a single event alert row item."""
        sev = str(ev.get("severity", "MEDIUM")).upper()
        ev_type = str(ev.get("event_type", "INCIDENT"))
        ts = str(ev.get("timestamp", ""))[-8:]  # time part
        desc = str(ev.get("description", ""))

        color_map = {
            "CRITICAL": Theme.ACCENT_RED,
            "HIGH": Theme.ACCENT_RED,
            "MEDIUM": Theme.ACCENT_AMBER,
            "LOW": Theme.ACCENT_GREEN
        }
        pill_color = color_map.get(sev, Theme.ACCENT_BLUE)

        row = tk.Frame(self.items_frame, bg="#111827", padx=8, pady=6, highlightbackground=Theme.BORDER, highlightthickness=1)
        row.pack(fill=tk.X, padx=6, pady=3)

        top_line = tk.Frame(row, bg="#111827")
        top_line.pack(fill=tk.X)

        # Severity Pill
        pill = tk.Label(
            top_line,
            text=f" {sev} ",
            bg=pill_color,
            fg="#000000",
            font=("Segoe UI", 8, "bold")
        )
        pill.pack(side=tk.LEFT)

        # Type
        tk.Label(
            top_line,
            text=f"  {ev_type}",
            bg="#111827",
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_BODY_BOLD
        ).pack(side=tk.LEFT)

        # Time
        tk.Label(
            top_line,
            text=ts,
            bg="#111827",
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL
        ).pack(side=tk.RIGHT)

        # Description
        desc_lbl = tk.Label(
            row,
            text=desc,
            bg="#111827",
            fg=Theme.TEXT_SECONDARY,
            font=Theme.FONT_SMALL,
            anchor="w",
            wraplength=240,
            justify="left"
        )
        desc_lbl.pack(fill=tk.X, pady=(2, 0))

        if self.on_select:
            row.bind("<Button-1>", lambda e, item=ev: self.on_select(item))
            desc_lbl.bind("<Button-1>", lambda e, item=ev: self.on_select(item))
