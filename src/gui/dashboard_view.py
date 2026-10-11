"""
Dashboard View for Smart Road Vision.
Provides the high-level traffic control room command center:
5 clear KPI metric cards, prominent live surveillance player, 
real-time safety alerts feed, interactive traffic signal switch,
incident statistics breakdown, and viva demonstration guide.
"""

import os
import tkinter as tk
from tkinter import ttk
from .theme import Theme
from .components.stat_card import StatCard
from .components.video_canvas import VideoCanvas
from .components.alerts_ticker import AlertsTicker


class DashboardView(tk.Frame):
    """Command Center Dashboard view with intuitive controls and clear layout."""

    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, bg=Theme.BG_MAIN, padx=14, pady=10, **kwargs)
        self.controller = controller
        self.current_signal = "GREEN"

        # 1. Top Header Bar
        self._build_header()

        # 2. Quick Action & Signal Control Ribbon
        self._build_action_ribbon()

        # 3. 5 Clean, Spacious KPI Metric Cards
        self._build_kpi_row()

        # 4. Main 2-Column Body (Video Stream + Real-Time Alerts & Statistics Breakdown)
        self._build_body()

    def _build_header(self):
        hdr = tk.Frame(self, bg=Theme.BG_MAIN)
        hdr.pack(fill=tk.X, pady=(0, 8))

        left = tk.Frame(hdr, bg=Theme.BG_MAIN)
        left.pack(side=tk.LEFT)

        tk.Label(
            left,
            text="TRAFFIC CONTROL COMMAND CENTER",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_PRIMARY,
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="w")

        tk.Label(
            left,
            text="AI-Powered Intelligent Road Traffic Surveillance, Violation Detection & Safety Analytics",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_MUTED,
            font=("Segoe UI", 9)
        ).pack(anchor="w")

        # Live system status pill
        self.lbl_sys_status = tk.Label(
            hdr,
            text="● SYSTEM READY // AWAITING START",
            bg="#0f172a",
            fg=Theme.ACCENT_BLUE,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
            relief="groove",
            bd=1
        )
        self.lbl_sys_status.pack(side=tk.RIGHT)

    def _build_action_ribbon(self):
        """Action bar with Start button, interactive Traffic Signal, feed dropdown, and view links."""
        ribbon = tk.Frame(
            self,
            bg=Theme.BG_CARD,
            highlightbackground=Theme.BORDER,
            highlightthickness=1,
            padx=10,
            pady=6
        )
        ribbon.pack(fill=tk.X, pady=(0, 8))

        # Main Start / Stop Button (Prominent)
        self.btn_live_toggle = tk.Button(
            ribbon,
            text="▶  START LIVE AI MONITORING",
            bg="#059669",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=5,
            cursor="hand2",
            command=self.controller.toggle_monitoring
        )
        self.btn_live_toggle.pack(side=tk.LEFT, padx=(0, 10))

        # Traffic Signal Control Section
        sig_box = tk.Frame(ribbon, bg=Theme.BG_CARD)
        sig_box.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            sig_box,
            text="SIGNAL:",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_SECONDARY,
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.btn_sig_green = tk.Button(
            sig_box,
            text="🟢 GREEN",
            bg="#064e3b",
            fg="#34d399",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self._set_signal("GREEN")
        )
        self.btn_sig_green.pack(side=tk.LEFT, padx=2)

        self.btn_sig_red = tk.Button(
            sig_box,
            text="🔴 RED",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self._set_signal("RED")
        )
        self.btn_sig_red.pack(side=tk.LEFT, padx=2)

        # Video Feed Selector
        feed_box = tk.Frame(ribbon, bg=Theme.BG_CARD)
        feed_box.pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(
            feed_box,
            text="FEED:",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_SECONDARY,
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT, padx=(0, 4))

        self.source_options = {
            "City Intersection (Real CCTV)": ("file", "sample_traffic.mp4"),
            "Highway Traffic (Real CCTV)": ("file", "real_traffic_highway.mp4"),
            "Synthetic Simulation (Viva)": ("file", "sample_synthetic_traffic.mp4"),
            "Live Webcam (Laptop Camera)": ("webcam", 0)
        }

        self.source_choice_var = tk.StringVar(value="City Intersection (Real CCTV)")
        self.combo_source_dash = ttk.Combobox(
            feed_box,
            textvariable=self.source_choice_var,
            values=list(self.source_options.keys()),
            state="readonly",
            width=23,
            font=("Segoe UI", 8)
        )
        self.combo_source_dash.pack(side=tk.LEFT)
        self.combo_source_dash.bind("<<ComboboxSelected>>", self._on_source_dropdown_changed)

        # Quick Navigation Links on Right
        nav_box = tk.Frame(ribbon, bg=Theme.BG_CARD)
        nav_box.pack(side=tk.RIGHT)

        tk.Button(
            nav_box,
            text="📹 Full Monitor",
            bg="#1e293b",
            fg=Theme.TEXT_PRIMARY,
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self.controller.navigate_to("Live Monitoring")
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            nav_box,
            text="🚨 Violations",
            bg="#1e293b",
            fg=Theme.TEXT_PRIMARY,
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self.controller.navigate_to("Traffic Violations")
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            nav_box,
            text="📋 Logs",
            bg="#1e293b",
            fg=Theme.TEXT_PRIMARY,
            font=("Segoe UI", 8),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self.controller.navigate_to("Event Logs")
        ).pack(side=tk.LEFT, padx=2)

    def _build_kpi_row(self):
        """Builds 5 spacious, clean KPI metric cards across the top."""
        kpi_frame = tk.Frame(self, bg=Theme.BG_MAIN)
        kpi_frame.pack(fill=tk.X, pady=(0, 8))

        # Card 1: Vehicles Count
        self.card_vehicles = StatCard(
            kpi_frame,
            title="🚗 Total Vehicles",
            value="0",
            subtitle="Cars, Bikes, Buses & Trucks",
            accent_color=Theme.ACCENT_BLUE
        )
        self.card_vehicles.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))

        # Card 2: Violations Count
        self.card_violations = StatCard(
            kpi_frame,
            title="🚨 Traffic Violations",
            value="0",
            subtitle="Wrong-Way & Stop-Line",
            accent_color=Theme.ACCENT_RED
        )
        self.card_violations.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

        # Card 3: Potential Accidents
        self.card_accidents = StatCard(
            kpi_frame,
            title="💥 Collision Risks",
            value="0",
            subtitle="Abrupt Deceleration Alerts",
            accent_color=Theme.ACCENT_AMBER
        )
        self.card_accidents.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

        # Card 4: Emergency Vehicles
        self.card_emergency = StatCard(
            kpi_frame,
            title="🚑 Emergency Fleet",
            value="0",
            subtitle="Priority Corridor Dispatches",
            accent_color=Theme.ACCENT_PURPLE
        )
        self.card_emergency.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

        # Card 5: Road Congestion
        self.card_density = StatCard(
            kpi_frame,
            title="🚦 Road Congestion",
            value="LOW",
            subtitle="Normal Traffic Flow",
            accent_color=Theme.ACCENT_GREEN
        )
        self.card_density.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

    def _build_body(self):
        """2-Column Layout: Left Video Surveillance (60%) + Right Alerts & Incident Statistics (40%)."""
        body = tk.Frame(self, bg=Theme.BG_MAIN)
        body.pack(fill=tk.BOTH, expand=True)

        # Left Column: Video Surveillance Screen
        left_col = tk.Frame(body, bg=Theme.BG_MAIN)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        v_box = tk.Frame(
            left_col,
            bg=Theme.BG_CARD,
            highlightbackground=Theme.BORDER,
            highlightthickness=1,
            padx=8,
            pady=8
        )
        v_box.pack(fill=tk.BOTH, expand=True)

        # Video Title Bar
        v_hdr = tk.Frame(v_box, bg=Theme.BG_CARD)
        v_hdr.pack(fill=tk.X, pady=(0, 5))

        tk.Label(
            v_hdr,
            text="LIVE TRAFFIC SURVEILLANCE FEED",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT)

        self.lbl_pipeline_tag = tk.Label(
            v_hdr,
            text="YOLOv8 Nano • ByteTrack • Real-Time AI",
            bg="#101726",
            fg=Theme.ACCENT_BLUE,
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=2
        )
        self.lbl_pipeline_tag.pack(side=tk.RIGHT)

        # Main Video Canvas
        self.video_canvas = VideoCanvas(v_box, default_width=580, default_height=320)
        self.video_canvas.pack(fill=tk.BOTH, expand=True)

        # Bottom Telemetry & Congestion Meter
        tele_bar = tk.Frame(
            v_box,
            bg="#101726",
            padx=10,
            pady=5,
            highlightbackground=Theme.BORDER,
            highlightthickness=1
        )
        tele_bar.pack(fill=tk.X, pady=(6, 0))

        self.lbl_density_val = tk.Label(
            tele_bar,
            text="ROADWAY CONGESTION: LOW (Normal Flow)",
            bg="#101726",
            fg=Theme.ACCENT_GREEN,
            font=("Segoe UI", 9, "bold")
        )
        self.lbl_density_val.pack(side=tk.LEFT)

        self.lbl_signal_rule = tk.Label(
            tele_bar,
            text="STOP LINE: INACTIVE (GREEN)",
            bg="#101726",
            fg="#34d399",
            font=("Segoe UI", 9, "bold")
        )
        self.lbl_signal_rule.pack(side=tk.LEFT, padx=(20, 0))

        self.lbl_active_in_frame = tk.Label(
            tele_bar,
            text="Active in Frame: 0 vehicles",
            bg="#101726",
            fg=Theme.TEXT_SECONDARY,
            font=("Segoe UI", 9)
        )
        self.lbl_active_in_frame.pack(side=tk.RIGHT)

        # Right Column: Live Safety Alerts Ticker + Incident Statistics
        right_col = tk.Frame(body, bg=Theme.BG_MAIN, width=390)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(4, 0))

        # Top Right: Real-Time Alerts Ticker
        ticker_container = tk.Frame(
            right_col,
            bg=Theme.BG_CARD,
            highlightbackground=Theme.BORDER,
            highlightthickness=1
        )
        ticker_container.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.alerts_ticker = AlertsTicker(
            ticker_container,
            on_select_callback=self._on_ticker_alert_selected
        )
        self.alerts_ticker.pack(fill=tk.BOTH, expand=True)

        # Bottom Right: Incident Statistics & Capabilities Breakdown
        stats_panel = tk.Frame(
            right_col,
            bg=Theme.BG_CARD,
            highlightbackground=Theme.BORDER,
            highlightthickness=1,
            padx=10,
            pady=8
        )
        stats_panel.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Label(
            stats_panel,
            text="📊 TRAFFIC DENSITY & INCIDENT BREAKDOWN",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(0, 4))

        # 4 Mini Metric Meters Row
        m_row = tk.Frame(stats_panel, bg=Theme.BG_CARD)
        m_row.pack(fill=tk.X, pady=(0, 6))

        # WW
        self.lbl_ww_cnt = self._build_mini_meter(m_row, "🚫 Wrong Way", "0", Theme.ACCENT_RED)
        self.lbl_ww_cnt.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # RL
        self.lbl_rl_cnt = self._build_mini_meter(m_row, "🛑 Stop Line", "0", Theme.ACCENT_AMBER)
        self.lbl_rl_cnt.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Collision
        self.lbl_col_cnt = self._build_mini_meter(m_row, "💥 Collision", "0", "#f87171")
        self.lbl_col_cnt.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Emergency
        self.lbl_emg_cnt = self._build_mini_meter(m_row, "🚑 Emergency", "0", Theme.ACCENT_PURPLE)
        self.lbl_emg_cnt.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Quick Viva Tip Box
        tip_frame = tk.Frame(stats_panel, bg="#0e1726", padx=6, pady=4, highlightbackground=Theme.BORDER, highlightthickness=1)
        tip_frame.pack(fill=tk.X)

        tk.Label(
            tip_frame,
            text="💡 Viva Demo Tip: ",
            bg="#0e1726",
            fg=Theme.ACCENT_AMBER,
            font=("Segoe UI", 8, "bold")
        ).pack(side=tk.LEFT)

        tk.Label(
            tip_frame,
            text="Toggle signal to RED above to test stop-line violation capture.",
            bg="#0e1726",
            fg=Theme.TEXT_SECONDARY,
            font=("Segoe UI", 8)
        ).pack(side=tk.LEFT)

    def _build_mini_meter(self, parent, label: str, init_val: str, color: str):
        box = tk.Frame(parent, bg="#0e1726", padx=6, pady=4, highlightbackground=Theme.BORDER, highlightthickness=1)
        tk.Label(box, text=label, bg="#0e1726", fg=Theme.TEXT_MUTED, font=("Segoe UI", 7, "bold")).pack(anchor="w")
        val_lbl = tk.Label(box, text=init_val, bg="#0e1726", fg=color, font=("Segoe UI", 11, "bold"))
        val_lbl.pack(anchor="w")
        return box

    def _set_signal(self, color: str):
        """Toggles the simulated traffic signal state."""
        self.current_signal = color
        self.controller.set_signal_state(color)

        if color == "RED":
            self.btn_sig_red.config(bg="#991b1b", fg="#fca5a5")
            self.btn_sig_green.config(bg="#1e293b", fg="#94a3b8")
            self.lbl_signal_rule.config(
                text="STOP LINE: ENFORCED (RED)",
                fg=Theme.ACCENT_RED
            )
        else:
            self.btn_sig_green.config(bg="#064e3b", fg="#34d399")
            self.btn_sig_red.config(bg="#1e293b", fg="#94a3b8")
            self.lbl_signal_rule.config(
                text="STOP LINE: INACTIVE (GREEN)",
                fg="#34d399"
            )

    def _on_source_dropdown_changed(self, event=None):
        """Switches video input feed when user selects from dropdown."""
        choice = self.source_choice_var.get()
        if choice in self.source_options:
            stype, sparam = self.source_options[choice]
            if stype == "file" and os.path.exists(sparam):
                sparam = os.path.abspath(sparam)
            self.controller.configure_and_start_source(stype, sparam)

    def update_mini_chart(self, severity_counts: dict = None):
        """Kept for backward compatibility."""
        pass

    def update_metrics(self, stats: dict, is_monitoring: bool, density_info: dict = None):
        """Updates dashboard numbers, button states, traffic density, and breakdown meters."""
        # 1. Update 5 KPI numbers
        self.card_vehicles.set_value(stats.get("total_vehicles", 0))
        self.card_violations.set_value(stats.get("total_violations", 0))
        self.card_accidents.set_value(stats.get("possible_accidents", 0))
        self.card_emergency.set_value(stats.get("emergency_events", 0))

        # 2. Update breakdown mini meters
        by_type = stats.get("events_by_type", {})
        # Find label widgets inside meter frames
        for meter_frame, key in [
            (self.lbl_ww_cnt, "WRONG_WAY"),
            (self.lbl_rl_cnt, "RED_LIGHT"),
            (self.lbl_col_cnt, "POSSIBLE_ACCIDENT"),
            (self.lbl_emg_cnt, "EMERGENCY_VEHICLE")
        ]:
            val = by_type.get(key, 0)
            children = meter_frame.winfo_children()
            if len(children) >= 2:
                children[1].config(text=str(val))

        # 3. Update monitoring start/stop button and status pill
        if is_monitoring:
            self.lbl_sys_status.config(
                text="● AI MONITORING ACTIVE // RECORDING",
                fg=Theme.ACCENT_GREEN,
                bg="#062b1a"
            )
            self.btn_live_toggle.config(
                text="⏹  STOP MONITORING",
                bg="#dc2626",
                fg="#ffffff"
            )
        else:
            self.lbl_sys_status.config(
                text="● SYSTEM READY // AWAITING START",
                fg=Theme.ACCENT_BLUE,
                bg="#0f172a"
            )
            self.btn_live_toggle.config(
                text="▶  START LIVE AI MONITORING",
                bg="#059669",
                fg="#ffffff"
            )

        # 4. Update density information
        if density_info:
            d_lvl = density_info.get("level", "LOW")
            d_col = density_info.get("color", Theme.ACCENT_GREEN)
            v_cnt = density_info.get("vehicle_count", 0)

            sub = "Normal Traffic Flow" if d_lvl == "LOW" else ("Moderate Traffic" if d_lvl == "MEDIUM" else "Heavy Congestion")
            self.card_density.set_value(d_lvl, subtitle=sub, color=d_col)
            self.lbl_density_val.config(text=f"ROADWAY CONGESTION: {d_lvl} ({sub})", fg=d_col)
            self.lbl_active_in_frame.config(text=f"Active in Frame: {v_cnt} vehicles")

    def _on_ticker_alert_selected(self, ev_data: dict):
        """Navigates to violations view to inspect selected alert."""
        self.controller.navigate_to("Traffic Violations")
