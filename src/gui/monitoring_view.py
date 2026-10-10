"""
Live Monitoring View for Smart Road Vision.
Provides full-featured video surveillance monitoring:
Source selection (File, Webcam, RTSP), video playback controls,
real-time overlay toggles, traffic signal simulator, and telemetry HUD.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np

from .theme import Theme
from .components.video_canvas import VideoCanvas


class MonitoringView(tk.Frame):
    """Full-featured Live Video Monitoring view."""

    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, bg=Theme.BG_MAIN, padx=14, pady=12, **kwargs)
        self.controller = controller

        # Top Control Toolbar
        self._build_top_toolbar()

        # Center Main Area (Video canvas + Right Telemetry Sidebar)
        self._build_center_area()

        # Bottom Controls (Overlays & Signal State)
        self._build_bottom_controls()

    def _build_top_toolbar(self):
        tb = tk.Frame(self, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1, padx=10, pady=8)
        tb.pack(fill=tk.X, pady=(0, 10))

        # Source type selector
        tk.Label(tb, text="SOURCE:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY_BOLD).pack(side=tk.LEFT, padx=(0, 4))
        self.source_var = tk.StringVar(value="file")
        self.combo_source = ttk.Combobox(
            tb,
            textvariable=self.source_var,
            values=["file", "webcam", "rtsp"],
            state="readonly",
            width=8
        )
        self.combo_source.pack(side=tk.LEFT, padx=(0, 8))
        self.combo_source.bind("<<ComboboxSelected>>", self._on_source_type_changed)

        # Source input path / index
        self.entry_source = tk.Entry(
            tb,
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT_PRIMARY,
            insertbackground=Theme.ACCENT_BLUE,
            relief="flat",
            highlightbackground=Theme.BORDER,
            highlightthickness=1,
            width=28,
            font=Theme.FONT_SMALL
        )
        self.entry_source.pack(side=tk.LEFT, padx=(0, 6))
        # Default with sample_traffic.mp4 if present
        if os.path.exists("sample_traffic.mp4"):
            self.entry_source.insert(0, os.path.abspath("sample_traffic.mp4"))

        self.btn_browse = tk.Button(
            tb,
            text="📁 Browse Video",
            bg="#334155",
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SMALL,
            relief="flat",
            command=self._browse_video_file
        )
        self.btn_browse.pack(side=tk.LEFT, padx=(0, 12))

        # Playback Action Buttons
        self.btn_start = tk.Button(
            tb,
            text="▶ Start Monitoring",
            bg="#0284c7",
            fg="#ffffff",
            font=Theme.FONT_BODY_BOLD,
            relief="flat",
            padx=12,
            command=self._start_monitoring
        )
        self.btn_start.pack(side=tk.LEFT, padx=3)

        self.btn_pause = tk.Button(
            tb,
            text="⏸ Pause",
            bg="#334155",
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SMALL,
            relief="flat",
            command=self.controller.pause_monitoring
        )
        self.btn_pause.pack(side=tk.LEFT, padx=3)

        self.btn_resume = tk.Button(
            tb,
            text="⏵ Resume",
            bg="#334155",
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SMALL,
            relief="flat",
            command=self.controller.resume_monitoring
        )
        self.btn_resume.pack(side=tk.LEFT, padx=3)

        self.btn_stop = tk.Button(
            tb,
            text="⏹ Stop",
            bg="#dc2626",
            fg="#ffffff",
            font=Theme.FONT_SMALL,
            relief="flat",
            command=self.controller.stop_monitoring
        )
        self.btn_stop.pack(side=tk.LEFT, padx=3)

        self.btn_reset = tk.Button(
            tb,
            text="↺ Reset",
            bg="#334155",
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SMALL,
            relief="flat",
            command=self.controller.reset_monitoring
        )
        self.btn_reset.pack(side=tk.LEFT, padx=3)

    def _build_center_area(self):
        center = tk.Frame(self, bg=Theme.BG_MAIN)
        center.pack(fill=tk.BOTH, expand=True)

        # Video Canvas Container
        v_frame = tk.Frame(center, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        v_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.video_canvas = VideoCanvas(v_frame, default_width=720, default_height=460)
        self.video_canvas.pack(fill=tk.BOTH, expand=True)

        # Right Telemetry Sidebar
        self.side_hud = tk.Frame(center, bg=Theme.BG_CARD, width=240, highlightbackground=Theme.BORDER, highlightthickness=1, padx=12, pady=10)
        self.side_hud.pack(side=tk.RIGHT, fill=tk.Y)
        self.side_hud.pack_propagate(False)

        tk.Label(
            self.side_hud,
            text="TELEMETRY & HUD",
            bg=Theme.BG_CARD,
            fg=Theme.ACCENT_BLUE,
            font=Theme.FONT_SUBTITLE
        ).pack(anchor="w", pady=(0, 10))

        # Metrics rows
        self.lbl_hud_source = self._add_hud_row("Source:", "Webcam 0")
        self.lbl_hud_fps = self._add_hud_row("Pipeline FPS:", "30.0 FPS")
        self.lbl_hud_active = self._add_hud_row("Active Tracks:", "0")
        self.lbl_hud_density = self._add_hud_row("Density Level:", "LOW")
        self.lbl_hud_signal = self._add_hud_row("Signal Lamp:", "RED")

        # Vehicle breakdown section
        tk.Label(
            self.side_hud,
            text="VEHICLES DETECTED",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_BODY_BOLD
        ).pack(anchor="w", pady=(14, 6))

        self.lbl_cnt_cars = self._add_hud_row("Cars:", "0")
        self.lbl_cnt_bikes = self._add_hud_row("Motorcycles:", "0")
        self.lbl_cnt_buses = self._add_hud_row("Buses:", "0")
        self.lbl_cnt_trucks = self._add_hud_row("Trucks:", "0")

        # Stop Line indicator
        tk.Label(
            self.side_hud,
            text="ROAD VIRTUAL RULES",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_BODY_BOLD
        ).pack(anchor="w", pady=(14, 6))

        sl_info = self.controller.config_mgr.get("red_light", "stop_line", default={"y1": 340})
        self._add_hud_row("Stop Line Y:", f"Y = {sl_info.get('y1', 340)} px")
        exp_dir = self.controller.config_mgr.get("wrong_way", "expected_direction", default="TOP_TO_BOTTOM")
        self._add_hud_row("Allowed Flow:", exp_dir)

    def _add_hud_row(self, label: str, init_val: str) -> tk.Label:
        row = tk.Frame(self.side_hud, bg=Theme.BG_CARD)
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=label, bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_SMALL).pack(side=tk.LEFT)
        val_lbl = tk.Label(row, text=init_val, bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_BODY_BOLD)
        val_lbl.pack(side=tk.RIGHT)
        return val_lbl

    def _build_bottom_controls(self):
        bot = tk.Frame(self, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1, padx=10, pady=8)
        bot.pack(fill=tk.X, pady=(10, 0))

        # Overlays Checkboxes
        tk.Label(bot, text="OVERLAYS:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY_BOLD).pack(side=tk.LEFT, padx=(0, 6))

        self.var_box = tk.BooleanVar(value=True)
        tk.Checkbutton(bot, text="Bounding Boxes", variable=self.var_box, bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, selectcolor=Theme.BG_INPUT, command=self._update_overlay_toggles).pack(side=tk.LEFT, padx=4)

        self.var_tracks = tk.BooleanVar(value=True)
        tk.Checkbutton(bot, text="Tracks", variable=self.var_tracks, bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, selectcolor=Theme.BG_INPUT, command=self._update_overlay_toggles).pack(side=tk.LEFT, padx=4)

        self.var_stopline = tk.BooleanVar(value=True)
        tk.Checkbutton(bot, text="Stop Line", variable=self.var_stopline, bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, selectcolor=Theme.BG_INPUT, command=self._update_overlay_toggles).pack(side=tk.LEFT, padx=4)

        self.var_dir = tk.BooleanVar(value=True)
        tk.Checkbutton(bot, text="Direction Arrow", variable=self.var_dir, bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, selectcolor=Theme.BG_INPUT, command=self._update_overlay_toggles).pack(side=tk.LEFT, padx=4)

        # Traffic Signal Controller on right
        sig_frame = tk.Frame(bot, bg=Theme.BG_CARD)
        sig_frame.pack(side=tk.RIGHT)

        tk.Label(sig_frame, text="TRAFFIC SIGNAL:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY_BOLD).pack(side=tk.LEFT, padx=(0, 6))

        self.btn_sig_red = tk.Button(
            sig_frame,
            text="RED",
            bg="#dc2626",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=8,
            command=lambda: self._set_signal("RED")
        )
        self.btn_sig_red.pack(side=tk.LEFT, padx=2)

        self.btn_sig_yellow = tk.Button(
            sig_frame,
            text="YELLOW",
            bg="#334155",
            fg=Theme.TEXT_SECONDARY,
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=8,
            command=lambda: self._set_signal("YELLOW")
        )
        self.btn_sig_yellow.pack(side=tk.LEFT, padx=2)

        self.btn_sig_green = tk.Button(
            sig_frame,
            text="GREEN",
            bg="#334155",
            fg=Theme.TEXT_SECONDARY,
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=8,
            command=lambda: self._set_signal("GREEN")
        )
        self.btn_sig_green.pack(side=tk.LEFT, padx=2)

    def _browse_video_file(self):
        f = filedialog.askopenfilename(
            title="Select Traffic Video File",
            filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov *.wmv"), ("All Files", "*.*")]
        )
        if f:
            self.source_var.set("file")
            self.entry_source.delete(0, tk.END)
            self.entry_source.insert(0, f)

    def _on_source_type_changed(self, event=None):
        st = self.source_var.get()
        self.entry_source.delete(0, tk.END)
        if st == "webcam":
            self.entry_source.insert(0, "0")
            self.btn_browse.config(state="disabled")
        elif st == "rtsp":
            self.entry_source.insert(0, "rtsp://192.168.1.100:554/live")
            self.btn_browse.config(state="disabled")
        else:
            if os.path.exists("sample_traffic.mp4"):
                self.entry_source.insert(0, os.path.abspath("sample_traffic.mp4"))
            self.btn_browse.config(state="normal")

    def _start_monitoring(self):
        st = self.source_var.get()
        param = self.entry_source.get().strip()
        if st == "webcam":
            try:
                param = int(param)
            except ValueError:
                param = 0
        self.controller.configure_and_start_source(st, param)

    def _update_overlay_toggles(self):
        vp = self.controller.video_processor
        if vp:
            vp.show_bboxes = self.var_box.get()
            vp.show_tracks = self.var_tracks.get()
            vp.show_stop_line = self.var_stopline.get()
            vp.show_direction_arrow = self.var_dir.get()

    def _set_signal(self, state: str):
        self.controller.set_signal_state(state)
        # Update button highlights
        self.btn_sig_red.config(bg="#dc2626" if state == "RED" else "#334155", fg="#ffffff" if state == "RED" else Theme.TEXT_SECONDARY)
        self.btn_sig_yellow.config(bg="#d97706" if state == "YELLOW" else "#334155", fg="#ffffff" if state == "YELLOW" else Theme.TEXT_SECONDARY)
        self.btn_sig_green.config(bg="#16a34a" if state == "GREEN" else "#334155", fg="#ffffff" if state == "GREEN" else Theme.TEXT_SECONDARY)
        self.lbl_hud_signal.config(text=state, fg=Theme.ACCENT_RED if state == "RED" else (Theme.ACCENT_AMBER if state == "YELLOW" else Theme.ACCENT_GREEN))

    def update_telemetry(self, source_name: str, active_count: int, density_result: dict, class_counts: dict, fps: float):
        """Updates side telemetry stats."""
        self.lbl_hud_source.config(text=source_name[:18])
        self.lbl_hud_fps.config(text=f"{fps:.1f} FPS")
        self.lbl_hud_active.config(text=str(active_count))

        if density_result:
            dlvl = density_result.get("level", "LOW")
            dcol = density_result.get("color", Theme.ACCENT_GREEN)
            self.lbl_hud_density.config(text=dlvl, fg=dcol)

        if class_counts:
            self.lbl_cnt_cars.config(text=str(class_counts.get("car", 0)))
            self.lbl_cnt_bikes.config(text=str(class_counts.get("motorcycle", 0)))
            self.lbl_cnt_buses.config(text=str(class_counts.get("bus", 0)))
            self.lbl_cnt_trucks.config(text=str(class_counts.get("truck", 0)))
