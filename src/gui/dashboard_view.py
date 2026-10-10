"""
Dashboard View for Smart Road Vision.
Provides the high-level traffic control room command center:
KPI metric cards, mini video preview, density meter, recent events, and summary chart.
"""

import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .theme import Theme
from .components.stat_card import StatCard
from .components.video_canvas import VideoCanvas
from .components.alerts_ticker import AlertsTicker


class DashboardView(tk.Frame):
    """Command Center Dashboard view."""

    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, bg=Theme.BG_MAIN, padx=16, pady=14, **kwargs)
        self.controller = controller

        # Top Header Bar
        self._build_header()

        # KPI Metric Cards Row
        self._build_kpi_row()

        # Main Body Grid (Video preview, Mini Chart, Alerts Ticker)
        self._build_body()

    def _build_header(self):
        hdr = tk.Frame(self, bg=Theme.BG_MAIN)
        hdr.pack(fill=tk.X, pady=(0, 12))

        left = tk.Frame(hdr, bg=Theme.BG_MAIN)
        left.pack(side=tk.LEFT)
        tk.Label(
            left,
            text="COMMAND CENTER DASHBOARD",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_TITLE
        ).pack(anchor="w")
        tk.Label(
            left,
            text="AI-Powered Intelligent Road Traffic Surveillance & Safety Analytics",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL
        ).pack(anchor="w")

        # Status badge on right
        self.lbl_sys_status = tk.Label(
            hdr,
            text="● SYSTEM ARMED // STANDBY",
            bg="#132338",
            fg=Theme.ACCENT_BLUE,
            font=Theme.FONT_BODY_BOLD,
            padx=12,
            pady=4,
            relief="groove",
            bd=1
        )
        self.lbl_sys_status.pack(side=tk.RIGHT)

    def _build_kpi_row(self):
        kpi_frame = tk.Frame(self, bg=Theme.BG_MAIN)
        kpi_frame.pack(fill=tk.X, pady=(0, 14))

        # 6 KPI Cards
        self.card_vehicles = StatCard(
            kpi_frame,
            title="Total Vehicles",
            value="0",
            subtitle="Cumulative Count",
            accent_color=Theme.ACCENT_BLUE
        )
        self.card_vehicles.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.card_violations = StatCard(
            kpi_frame,
            title="Violations",
            value="0",
            subtitle="Wrong-Way & Red-Light",
            accent_color=Theme.ACCENT_RED
        )
        self.card_violations.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.card_accidents = StatCard(
            kpi_frame,
            title="Possible Accidents",
            value="0",
            subtitle="Heuristic Alerts",
            accent_color=Theme.ACCENT_RED
        )
        self.card_accidents.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.card_emergency = StatCard(
            kpi_frame,
            title="Emergency Vehicles",
            value="0",
            subtitle="Priority Corridor",
            accent_color=Theme.ACCENT_PURPLE
        )
        self.card_emergency.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.card_density = StatCard(
            kpi_frame,
            title="Traffic Density",
            value="LOW",
            subtitle="Active Road Flow",
            accent_color=Theme.ACCENT_GREEN
        )
        self.card_density.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.card_status = StatCard(
            kpi_frame,
            title="Feed Status",
            value="READY",
            subtitle="Webcam / File",
            accent_color=Theme.ACCENT_BLUE
        )
        self.card_status.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

    def _build_body(self):
        body = tk.Frame(self, bg=Theme.BG_MAIN)
        body.pack(fill=tk.BOTH, expand=True)

        # Left Column: Mini Video Preview & Quick Controls (45% width)
        left_col = tk.Frame(body, bg=Theme.BG_MAIN)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        # Video Frame container
        v_box = tk.Frame(left_col, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1, padx=8, pady=8)
        v_box.pack(fill=tk.BOTH, expand=True)

        v_hdr = tk.Frame(v_box, bg=Theme.BG_CARD)
        v_hdr.pack(fill=tk.X, pady=(0, 6))
        tk.Label(
            v_hdr,
            text="LIVE STREAM MONITOR",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SUBTITLE
        ).pack(side=tk.LEFT)

        self.btn_live_toggle = tk.Button(
            v_hdr,
            text="▶ START FEED",
            bg="#0369a1",
            fg="#ffffff",
            font=Theme.FONT_SMALL,
            relief="flat",
            padx=10,
            command=self.controller.toggle_monitoring
        )
        self.btn_live_toggle.pack(side=tk.RIGHT)

        self.video_canvas = VideoCanvas(v_box, default_width=440, default_height=260)
        self.video_canvas.pack(fill=tk.BOTH, expand=True)

        # Density bar below video
        self.density_bar_frame = tk.Frame(v_box, bg=Theme.BG_CARD, pady=6)
        self.density_bar_frame.pack(fill=tk.X)
        tk.Label(
            self.density_bar_frame,
            text="ROADWAY CONGESTION LEVEL:",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_SECONDARY,
            font=Theme.FONT_SMALL
        ).pack(side=tk.LEFT)

        self.lbl_density_val = tk.Label(
            self.density_bar_frame,
            text="LOW (Normal Flow)",
            bg=Theme.BG_CARD,
            fg=Theme.ACCENT_GREEN,
            font=Theme.FONT_BODY_BOLD
        )
        self.lbl_density_val.pack(side=tk.RIGHT)

        # Center Column: Event Distribution Chart (28% width)
        center_col = tk.Frame(body, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1, padx=8, pady=8)
        center_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        tk.Label(
            center_col,
            text="INCIDENTS BY SEVERITY",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SUBTITLE
        ).pack(anchor="w", pady=(0, 6))

        self.chart_container = tk.Frame(center_col, bg=Theme.BG_CARD)
        self.chart_container.pack(fill=tk.BOTH, expand=True)
        self._build_mini_chart()

        # Right Column: Recent Alerts Ticker (27% width)
        right_col = tk.Frame(body, bg=Theme.BG_MAIN)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self.alerts_ticker = AlertsTicker(
            right_col,
            on_select_callback=self._on_ticker_alert_selected
        )
        self.alerts_ticker.pack(fill=tk.BOTH, expand=True)

    def _build_mini_chart(self):
        """Embeds a mini Matplotlib bar chart for severity breakdown."""
        self.fig = Figure(figsize=(3.2, 3.0), dpi=90, facecolor=Theme.BG_CARD)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(Theme.BG_CARD)
        self.fig.tight_layout()

        self.chart_canvas = FigureCanvasTkAgg(self.fig, master=self.chart_container)
        self.chart_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.update_mini_chart({"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0})

    def update_mini_chart(self, severity_counts: dict):
        """Updates the mini chart bars."""
        self.ax.clear()
        self.ax.set_facecolor(Theme.BG_CARD)

        labels = ["Critical", "High", "Medium", "Low"]
        keys = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        values = [severity_counts.get(k, 0) for k in keys]
        colors = [Theme.ACCENT_RED, "#f87171", Theme.ACCENT_AMBER, Theme.ACCENT_GREEN]

        bars = self.ax.bar(labels, values, color=colors, width=0.55, edgecolor="#334155")
        self.ax.tick_params(colors=Theme.TEXT_SECONDARY, labelsize=8)
        self.ax.spines["bottom"].set_color(Theme.BORDER)
        self.ax.spines["left"].set_color(Theme.BORDER)
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.yaxis.grid(True, linestyle="--", alpha=0.3, color="#334155")

        # Value annotations on top of bars
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                self.ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    h + 0.1,
                    f"{int(h)}",
                    ha="center",
                    va="bottom",
                    color=Theme.TEXT_PRIMARY,
                    fontsize=8
                )

        self.fig.tight_layout()
        self.chart_canvas.draw_idle()

    def update_metrics(self, stats: dict, is_monitoring: bool, density_info: dict = None):
        """Updates dashboard numbers and status."""
        self.card_vehicles.set_value(stats.get("total_vehicles", 0))
        self.card_violations.set_value(stats.get("total_violations", 0))
        self.card_accidents.set_value(stats.get("possible_accidents", 0))
        self.card_emergency.set_value(stats.get("emergency_events", 0))

        if is_monitoring:
            self.lbl_sys_status.config(
                text="● MONITORING ACTIVE // RECORDING",
                fg=Theme.ACCENT_GREEN,
                bg="#062b1a"
            )
            self.btn_live_toggle.config(text="■ STOP FEED", bg="#dc2626")
            self.card_status.set_value("ACTIVE", subtitle="AI Tracking On", color=Theme.ACCENT_GREEN)
        else:
            self.lbl_sys_status.config(
                text="● SYSTEM ARMED // STANDBY",
                fg=Theme.ACCENT_BLUE,
                bg="#132338"
            )
            self.btn_live_toggle.config(text="▶ START FEED", bg="#0369a1")
            self.card_status.set_value("READY", subtitle="Awaiting Start", color=Theme.ACCENT_BLUE)

        if density_info:
            d_lvl = density_info.get("level", "LOW")
            d_col = density_info.get("color", Theme.ACCENT_GREEN)
            v_cnt = density_info.get("vehicle_count", 0)
            self.card_density.set_value(d_lvl, subtitle=f"{v_cnt} Active in Frame", color=d_col)
            self.lbl_density_val.config(text=f"{d_lvl} ({v_cnt} Vehicles)", fg=d_col)

        sev_counts = stats.get("events_by_severity", {})
        self.update_mini_chart(sev_counts)

    def _on_ticker_alert_selected(self, ev_data: dict):
        """Navigates to event details or opens evidence dialog."""
        self.controller.show_event_dialog(ev_data)
