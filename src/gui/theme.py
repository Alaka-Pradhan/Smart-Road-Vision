"""
Theme and Design System for Smart Road Vision.
Defines colors, typography, and TTK style configurations
for a traffic-control-room dark aesthetic.
"""

import tkinter as tk
from tkinter import ttk


class Theme:
    # Color Palette - High-tech Traffic Control Room
    BG_MAIN = "#0b0f19"         # Deep Slate Black
    BG_SIDEBAR = "#0d1322"      # Dark Navy
    BG_CARD = "#141c2e"         # Surface Slate
    BG_CARD_LIGHT = "#1e293b"   # Lighter Surface
    BG_SURFACE = "#101726"      # Surface secondary
    BG_INPUT = "#0f172a"        # Input background
    BORDER = "#334155"          # Defined Divider Border
    BORDER_LIGHT = "#475569"    # High-contrast border
    BORDER_FOCUS = "#38bdf8"    # Active border

    TEXT_PRIMARY = "#f8fafc"    # Bright White
    TEXT_SECONDARY = "#94a3b8"  # Slate Silver
    TEXT_MUTED = "#64748b"      # Muted Gray

    # Status / Alert Colors
    ACCENT_BLUE = "#38bdf8"     # Electric Sky Blue
    ACCENT_GREEN = "#10b981"    # Safe / Normal / Emerald
    ACCENT_AMBER = "#f59e0b"    # Warning / Medium / Amber
    ACCENT_RED = "#ef4444"      # Critical / Violation / Red
    ACCENT_PURPLE = "#8b5cf6"   # Emergency / Special / Violet

    # Fonts
    FONT_TITLE = ("Segoe UI", 16, "bold")
    FONT_SUBTITLE = ("Segoe UI", 12, "bold")
    FONT_BODY = ("Segoe UI", 10)
    FONT_BODY_BOLD = ("Segoe UI", 10, "bold")
    FONT_SMALL = ("Segoe UI", 9)
    FONT_KPI_VAL = ("Segoe UI", 20, "bold")
    FONT_MONO = ("Consolas", 10)

    @classmethod
    def apply_ttk_theme(cls, root: tk.Tk):
        """Applies dark styles to Tkinter ttk widgets."""
        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Treeview styling (tables)
        style.configure(
            "Treeview",
            background=cls.BG_CARD,
            foreground=cls.TEXT_PRIMARY,
            fieldbackground=cls.BG_CARD,
            borderwidth=0,
            font=cls.FONT_BODY,
            rowheight=28
        )
        style.map(
            "Treeview",
            background=[("selected", "#0369a1")],
            foreground=[("selected", "#ffffff")]
        )
        style.configure(
            "Treeview.Heading",
            background="#1e293b",
            foreground=cls.ACCENT_BLUE,
            borderwidth=1,
            relief="flat",
            font=cls.FONT_BODY_BOLD
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#334155")]
        )

        # Scrollbar styling
        style.configure(
            "Vertical.TScrollbar",
            background=cls.BG_CARD,
            troughcolor=cls.BG_MAIN,
            arrowcolor=cls.TEXT_SECONDARY,
            borderwidth=0
        )

        # Notebook / Tabs
        style.configure(
            "TNotebook",
            background=cls.BG_MAIN,
            borderwidth=0
        )
        style.configure(
            "TNotebook.Tab",
            background=cls.BG_CARD,
            foreground=cls.TEXT_SECONDARY,
            padding=[14, 6],
            font=cls.FONT_BODY_BOLD
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", cls.ACCENT_BLUE)],
            foreground=[("selected", "#000000")]
        )

        # Combobox
        style.configure(
            "TCombobox",
            fieldbackground=cls.BG_INPUT,
            background=cls.BG_CARD,
            foreground=cls.TEXT_PRIMARY,
            bordercolor=cls.BORDER,
            arrowcolor=cls.ACCENT_BLUE,
            font=cls.FONT_BODY
        )
