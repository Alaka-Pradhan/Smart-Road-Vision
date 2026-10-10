"""
Traffic Analytics View for Smart Road Vision.
Renders Matplotlib charts embedded in Tkinter:
Violations breakdown, vehicle class distribution, traffic density time series,
and human verification status statistics.
"""

import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np

from .theme import Theme


class AnalyticsView(tk.Frame):
    """Traffic Analytics and visual reporting workspace."""

    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, bg=Theme.BG_MAIN, padx=14, pady=12, **kwargs)
        self.controller = controller

        # Header Bar
        self._build_header()

        # 2x2 Grid of Matplotlib Charts
        self._build_charts_grid()

    def _build_header(self):
        hdr = tk.Frame(self, bg=Theme.BG_MAIN)
        hdr.pack(fill=tk.X, pady=(0, 10))

        left = tk.Frame(hdr, bg=Theme.BG_MAIN)
        left.pack(side=tk.LEFT)
        tk.Label(
            left,
            text="TRAFFIC SAFETY & CORRIDOR ANALYTICS",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_TITLE
        ).pack(anchor="w")
        tk.Label(
            left,
            text="Data-driven statistical visualisations generated from persistent event logs",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL
        ).pack(anchor="w")

        tk.Button(
            hdr,
            text="🔄 Refresh Charts",
            bg="#0284c7",
            fg="#ffffff",
            font=Theme.FONT_BODY_BOLD,
            relief="flat",
            padx=12,
            pady=4,
            command=self.refresh_charts
        ).pack(side=tk.RIGHT)

    def _build_charts_grid(self):
        # Container frame
        grid_frame = tk.Frame(self, bg=Theme.BG_MAIN)
        grid_frame.pack(fill=tk.BOTH, expand=True)

        # 4 Subplot Figure
        self.fig = Figure(figsize=(10, 6.2), dpi=95, facecolor=Theme.BG_MAIN)
        self.fig.subplots_adjust(left=0.08, right=0.96, top=0.92, bottom=0.10, wspace=0.28, hspace=0.38)

        self.ax_violations = self.fig.add_subplot(2, 2, 1)
        self.ax_vehicles = self.fig.add_subplot(2, 2, 2)
        self.ax_density = self.fig.add_subplot(2, 2, 3)
        self.ax_verification = self.fig.add_subplot(2, 2, 4)

        self.canvas = FigureCanvasTkAgg(self.fig, master=grid_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.refresh_charts()

    def refresh_charts(self):
        """Fetches latest real data and redraws all 4 charts."""
        df = self.controller.event_logger.get_dataframe()
        tracker_classes = self.controller.tracker.get_class_counts() if self.controller.tracker else {}
        density_hist = self.controller.traffic_analyzer.get_history() if self.controller.traffic_analyzer else []

        # 1. Chart 1: Violations by Type
        self.ax_violations.clear()
        self.ax_violations.set_facecolor(Theme.BG_CARD)
        self.ax_violations.set_title("Violations & Critical Incidents", color=Theme.TEXT_PRIMARY, fontsize=10, weight="bold")

        if not df.empty:
            v_types = ["WRONG_WAY", "RED_LIGHT", "POSSIBLE_ACCIDENT", "EMERGENCY_VEHICLE"]
            labels = ["Wrong Way", "Red Light", "Accident", "Emergency"]
            counts = [(df["event_type"] == vt).sum() for vt in v_types]
            colors = [Theme.ACCENT_AMBER, Theme.ACCENT_RED, "#dc2626", Theme.ACCENT_PURPLE]

            bars = self.ax_violations.bar(labels, counts, color=colors, width=0.55, edgecolor="#334155")
            self.ax_violations.tick_params(colors=Theme.TEXT_SECONDARY, labelsize=8)
            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    self.ax_violations.text(bar.get_x() + bar.get_width() / 2., h + 0.1, f"{int(h)}", ha="center", va="bottom", color=Theme.TEXT_PRIMARY, fontsize=8)
        else:
            self.ax_violations.text(0.5, 0.5, "No Incident Data Logged", ha="center", va="center", color=Theme.TEXT_MUTED, transform=self.ax_violations.transAxes)

        self._style_axis(self.ax_violations)

        # 2. Chart 2: Vehicle Distribution (Donut / Pie)
        self.ax_vehicles.clear()
        self.ax_vehicles.set_facecolor(Theme.BG_CARD)
        self.ax_vehicles.set_title("Vehicle Classification Breakdown", color=Theme.TEXT_PRIMARY, fontsize=10, weight="bold")

        veh_data = {k: v for k, v in tracker_classes.items() if k != "person" and v > 0}
        if veh_data:
            labels = [k.capitalize() for k in veh_data.keys()]
            values = list(veh_data.values())
            colors = [Theme.ACCENT_BLUE, Theme.ACCENT_GREEN, Theme.ACCENT_AMBER, Theme.ACCENT_PURPLE][:len(values)]
            wedges, texts, autotexts = self.ax_vehicles.pie(
                values,
                labels=labels,
                autopct="%1.0f%%",
                colors=colors,
                startangle=140,
                wedgeprops=dict(width=0.45, edgecolor=Theme.BG_CARD),
                textprops=dict(color=Theme.TEXT_SECONDARY, fontsize=8)
            )
            for at in autotexts:
                at.set_color(Theme.TEXT_PRIMARY)
                at.set_fontsize(8)
                at.set_weight("bold")
        else:
            self.ax_vehicles.text(0.5, 0.5, "No Tracked Vehicles Yet", ha="center", va="center", color=Theme.TEXT_MUTED, transform=self.ax_vehicles.transAxes)

        # 3. Chart 3: Traffic Density Time Series
        self.ax_density.clear()
        self.ax_density.set_facecolor(Theme.BG_CARD)
        self.ax_density.set_title("Real-Time Traffic Density (Vehicle Count History)", color=Theme.TEXT_PRIMARY, fontsize=10, weight="bold")

        if density_hist:
            times = [h["timestamp"] for h in density_hist][-25:]
            counts = [h["vehicle_count"] for h in density_hist][-25:]
            indices = list(range(len(counts)))

            self.ax_density.plot(indices, counts, color=Theme.ACCENT_BLUE, marker="o", markersize=3, linewidth=2)
            self.ax_density.fill_between(indices, counts, color=Theme.ACCENT_BLUE, alpha=0.15)
            self.ax_density.set_xticks(indices[::max(1, len(indices) // 5)])
            self.ax_density.set_xticklabels(times[::max(1, len(times) // 5)], rotation=20, fontsize=7)
            self.ax_density.tick_params(colors=Theme.TEXT_SECONDARY, labelsize=8)
        else:
            self.ax_density.text(0.5, 0.5, "Awaiting Monitoring Session Stream", ha="center", va="center", color=Theme.TEXT_MUTED, transform=self.ax_density.transAxes)

        self._style_axis(self.ax_density)

        # 4. Chart 4: Verification Status Distribution
        self.ax_verification.clear()
        self.ax_verification.set_facecolor(Theme.BG_CARD)
        self.ax_verification.set_title("Human Verification Audit Status", color=Theme.TEXT_PRIMARY, fontsize=10, weight="bold")

        if not df.empty:
            statuses = ["PENDING REVIEW", "CONFIRMED", "FALSE POSITIVE", "REVIEWED"]
            s_labels = ["Pending", "Confirmed", "False Alarm", "Reviewed"]
            s_counts = [(df["verification_status"].str.upper() == st).sum() for st in statuses]
            s_colors = [Theme.ACCENT_AMBER, Theme.ACCENT_GREEN, Theme.ACCENT_RED, Theme.ACCENT_BLUE]

            bars = self.ax_verification.bar(s_labels, s_counts, color=s_colors, width=0.55, edgecolor="#334155")
            self.ax_verification.tick_params(colors=Theme.TEXT_SECONDARY, labelsize=8)
            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    self.ax_verification.text(bar.get_x() + bar.get_width() / 2., h + 0.1, f"{int(h)}", ha="center", va="bottom", color=Theme.TEXT_PRIMARY, fontsize=8)
        else:
            self.ax_verification.text(0.5, 0.5, "No Audit Events Recorded", ha="center", va="center", color=Theme.TEXT_MUTED, transform=self.ax_verification.transAxes)

        self._style_axis(self.ax_verification)

        self.fig.tight_layout()
        self.canvas.draw_idle()

    def _style_axis(self, ax):
        """Applies consistent dark theme borders and grid lines."""
        ax.spines["bottom"].set_color(Theme.BORDER)
        ax.spines["left"].set_color(Theme.BORDER)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.grid(True, linestyle="--", alpha=0.25, color="#334155")
