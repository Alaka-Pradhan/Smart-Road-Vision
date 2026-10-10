"""
Settings View for Smart Road Vision.
Provides full configuration editing for AI detection, tracking,
wrong-way thresholds, virtual stop line coordinates, signal simulation,
custom model paths, and event cooldowns.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .theme import Theme


class SettingsView(tk.Frame):
    """Configuration and system parameters management workspace."""

    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, bg=Theme.BG_MAIN, padx=16, pady=12, **kwargs)
        self.controller = controller

        # Header Bar
        self._build_header()

        # Tabbed Notebook Configuration Panel
        self._build_notebook()

        # Bottom Save / Reset Toolbar
        self._build_footer()

    def _build_header(self):
        hdr = tk.Frame(self, bg=Theme.BG_MAIN)
        hdr.pack(fill=tk.X, pady=(0, 10))

        left = tk.Frame(hdr, bg=Theme.BG_MAIN)
        left.pack(side=tk.LEFT)
        tk.Label(
            left,
            text="SYSTEM CONFIGURATION & ROAD CALIBRATION",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_TITLE
        ).pack(anchor="w")
        tk.Label(
            left,
            text="Fine-tune computer vision detectors, virtual safety boundaries, thresholds, and custom weights",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL
        ).pack(anchor="w")

        # Test model button on header
        tk.Button(
            hdr,
            text="⚡ Test YOLO Model",
            bg="#334155",
            fg=Theme.ACCENT_BLUE,
            font=Theme.FONT_BODY_BOLD,
            relief="flat",
            padx=12,
            pady=4,
            command=self._test_model
        ).pack(side=tk.RIGHT)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: AI & Detection
        self.tab_detection = tk.Frame(self.notebook, bg=Theme.BG_CARD, padx=16, pady=14)
        self.notebook.add(self.tab_detection, text=" AI Detection & Tracking ")
        self._populate_detection_tab()

        # Tab 2: Traffic Rules & Virtual Lines
        self.tab_rules = tk.Frame(self.notebook, bg=Theme.BG_CARD, padx=16, pady=14)
        self.notebook.add(self.tab_rules, text=" Road Rules & Boundaries ")
        self._populate_rules_tab()

        # Tab 3: Custom Models & Hardware
        self.tab_custom = tk.Frame(self.notebook, bg=Theme.BG_CARD, padx=16, pady=14)
        self.notebook.add(self.tab_custom, text=" Custom Models (Helmet/Fleet) ")
        self._populate_custom_tab()

        # Tab 4: Event Engine & Storage
        self.tab_storage = tk.Frame(self.notebook, bg=Theme.BG_CARD, padx=16, pady=14)
        self.notebook.add(self.tab_storage, text=" Event Engine & Evidence ")
        self._populate_storage_tab()

    def _populate_detection_tab(self):
        cfg = self.controller.config_mgr.get("detection", default={})

        # Model Path
        self._add_section_title(self.tab_detection, "YOLOv8 Detection Weights")
        p_row = tk.Frame(self.tab_detection, bg=Theme.BG_CARD)
        p_row.pack(fill=tk.X, pady=(0, 10))

        tk.Label(p_row, text="Model File Path:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY, width=18, anchor="w").pack(side=tk.LEFT)
        self.ent_model_path = tk.Entry(p_row, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.ent_model_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.ent_model_path.insert(0, cfg.get("model_path", "models/yolov8n.pt"))

        tk.Button(p_row, text="Browse...", bg="#334155", fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, relief="flat", command=self._browse_model).pack(side=tk.RIGHT)

        # Confidence Slider
        self._add_section_title(self.tab_detection, "Inference Confidence & NMS Thresholds")
        c_row = tk.Frame(self.tab_detection, bg=Theme.BG_CARD)
        c_row.pack(fill=tk.X, pady=(0, 6))

        tk.Label(c_row, text="Confidence Threshold:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY, width=18, anchor="w").pack(side=tk.LEFT)
        self.lbl_conf_val = tk.Label(c_row, text=f"{cfg.get('confidence_threshold', 0.35):.2f}", bg=Theme.BG_CARD, fg=Theme.ACCENT_BLUE, font=Theme.FONT_BODY_BOLD, width=6)
        self.lbl_conf_val.pack(side=tk.RIGHT)

        self.slider_conf = tk.Scale(
            c_row,
            from_=0.10,
            to=0.90,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            highlightthickness=0,
            showvalue=0,
            command=lambda v: self.lbl_conf_val.config(text=f"{float(v):.2f}")
        )
        self.slider_conf.set(cfg.get("confidence_threshold", 0.35))
        self.slider_conf.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

        # Tracker Choice
        self._add_section_title(self.tab_detection, "Multi-Object Tracker Algorithm")
        t_row = tk.Frame(self.tab_detection, bg=Theme.BG_CARD)
        t_row.pack(fill=tk.X, pady=(0, 10))

        tk.Label(t_row, text="Tracking Method:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY, width=18, anchor="w").pack(side=tk.LEFT)
        self.tracker_var = tk.StringVar(value=cfg.get("tracker_type", "bytetrack.yaml"))
        self.combo_tracker = ttk.Combobox(
            t_row,
            textvariable=self.tracker_var,
            values=["bytetrack.yaml", "botsort.yaml"],
            state="readonly",
            width=20
        )
        self.combo_tracker.pack(side=tk.LEFT)

    def _populate_rules_tab(self):
        ww_cfg = self.controller.config_mgr.get("wrong_way", default={})
        rl_cfg = self.controller.config_mgr.get("red_light", default={})
        sl = rl_cfg.get("stop_line", {"x1": 80, "y1": 340, "x2": 560, "y2": 340})
        dens_cfg = self.controller.config_mgr.get("density", default={})

        # Wrong Way
        self._add_section_title(self.tab_rules, "Wrong-Way Driving Parameters")
        w_row = tk.Frame(self.tab_rules, bg=Theme.BG_CARD)
        w_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(w_row, text="Allowed Corridor Flow:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY, width=20, anchor="w").pack(side=tk.LEFT)
        self.dir_var = tk.StringVar(value=ww_cfg.get("expected_direction", "TOP_TO_BOTTOM"))
        self.combo_dir = ttk.Combobox(
            w_row,
            textvariable=self.dir_var,
            values=["TOP_TO_BOTTOM", "BOTTOM_TO_TOP", "LEFT_TO_RIGHT", "RIGHT_TO_LEFT"],
            state="readonly",
            width=20
        )
        self.combo_dir.pack(side=tk.LEFT)

        w_row2 = tk.Frame(self.tab_rules, bg=Theme.BG_CARD)
        w_row2.pack(fill=tk.X, pady=(0, 10))

        tk.Label(w_row2, text="Min Displacement (px):", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY, width=20, anchor="w").pack(side=tk.LEFT)
        self.ent_ww_disp = tk.Entry(w_row2, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, width=8, relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.ent_ww_disp.pack(side=tk.LEFT, padx=(0, 16))
        self.ent_ww_disp.insert(0, str(ww_cfg.get("min_displacement_px", 35)))

        tk.Label(w_row2, text="Min Tracking Frames:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY).pack(side=tk.LEFT, padx=(0, 4))
        self.ent_ww_frames = tk.Entry(w_row2, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, width=8, relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.ent_ww_frames.pack(side=tk.LEFT)
        self.ent_ww_frames.insert(0, str(ww_cfg.get("min_tracking_frames", 10)))

        # Stop Line Coordinates
        self._add_section_title(self.tab_rules, "Virtual Stop Line Coordinates (X1, Y1) - (X2, Y2)")
        sl_row = tk.Frame(self.tab_rules, bg=Theme.BG_CARD)
        sl_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(sl_row, text="X1:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY).pack(side=tk.LEFT, padx=(0, 4))
        self.ent_sl_x1 = tk.Entry(sl_row, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, width=6, relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.ent_sl_x1.pack(side=tk.LEFT, padx=(0, 12))
        self.ent_sl_x1.insert(0, str(sl.get("x1", 80)))

        tk.Label(sl_row, text="Y1:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY).pack(side=tk.LEFT, padx=(0, 4))
        self.ent_sl_y1 = tk.Entry(sl_row, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, width=6, relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.ent_sl_y1.pack(side=tk.LEFT, padx=(0, 12))
        self.ent_sl_y1.insert(0, str(sl.get("y1", 340)))

        tk.Label(sl_row, text="X2:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY).pack(side=tk.LEFT, padx=(0, 4))
        self.ent_sl_x2 = tk.Entry(sl_row, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, width=6, relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.ent_sl_x2.pack(side=tk.LEFT, padx=(0, 12))
        self.ent_sl_x2.insert(0, str(sl.get("x2", 560)))

        tk.Label(sl_row, text="Y2:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY).pack(side=tk.LEFT, padx=(0, 4))
        self.ent_sl_y2 = tk.Entry(sl_row, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, width=6, relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.ent_sl_y2.pack(side=tk.LEFT)
        self.ent_sl_y2.insert(0, str(sl.get("y2", 340)))

        # Density Thresholds
        self._add_section_title(self.tab_rules, "Traffic Density Categorization Thresholds")
        d_row = tk.Frame(self.tab_rules, bg=Theme.BG_CARD)
        d_row.pack(fill=tk.X, pady=(0, 10))

        tk.Label(d_row, text="Low / Medium Boundary (Vehicles):", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY).pack(side=tk.LEFT, padx=(0, 6))
        self.ent_dens_low = tk.Entry(d_row, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, width=6, relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.ent_dens_low.pack(side=tk.LEFT, padx=(0, 16))
        self.ent_dens_low.insert(0, str(dens_cfg.get("low_threshold", 3)))

        tk.Label(d_row, text="Medium / High Boundary (Vehicles):", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY).pack(side=tk.LEFT, padx=(0, 6))
        self.ent_dens_med = tk.Entry(d_row, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, width=6, relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.ent_dens_med.pack(side=tk.LEFT)
        self.ent_dens_med.insert(0, str(dens_cfg.get("medium_threshold", 7)))

    def _populate_custom_tab(self):
        det_cfg = self.controller.config_mgr.get("detection", default={})

        self._add_section_title(self.tab_custom, "Custom Safety Helmet Classifier Weights (.pt)")
        tk.Label(
            self.tab_custom,
            text="Optional: Train a custom YOLOv8 model for two-wheeler helmet compliance and point to it below.",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL
        ).pack(anchor="w", pady=(0, 4))

        h_row = tk.Frame(self.tab_custom, bg=Theme.BG_CARD)
        h_row.pack(fill=tk.X, pady=(0, 12))
        self.ent_helmet_path = tk.Entry(h_row, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.ent_helmet_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.ent_helmet_path.insert(0, det_cfg.get("custom_helmet_model", ""))
        tk.Button(h_row, text="Browse...", bg="#334155", fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, relief="flat", command=lambda: self._browse_file_into(self.ent_helmet_path)).pack(side=tk.RIGHT)

        self._add_section_title(self.tab_custom, "Custom Emergency Fleet Classifier Weights (.pt)")
        tk.Label(
            self.tab_custom,
            text="Optional: Specialized model weights for ambulances, fire tenders, and police emergency detection.",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL
        ).pack(anchor="w", pady=(0, 4))

        e_row = tk.Frame(self.tab_custom, bg=Theme.BG_CARD)
        e_row.pack(fill=tk.X, pady=(0, 10))
        self.ent_emerg_path = tk.Entry(e_row, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.ent_emerg_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.ent_emerg_path.insert(0, det_cfg.get("custom_emergency_model", ""))
        tk.Button(e_row, text="Browse...", bg="#334155", fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, relief="flat", command=lambda: self._browse_file_into(self.ent_emerg_path)).pack(side=tk.RIGHT)

    def _populate_storage_tab(self):
        ev_cfg = self.controller.config_mgr.get("event_engine", default={})

        self._add_section_title(self.tab_storage, "Duplicate Suppression Cooldown")
        cd_row = tk.Frame(self.tab_storage, bg=Theme.BG_CARD)
        cd_row.pack(fill=tk.X, pady=(0, 10))

        tk.Label(cd_row, text="Event Cooldown Duration (seconds):", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY).pack(side=tk.LEFT, padx=(0, 8))
        self.ent_cooldown = tk.Entry(cd_row, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, width=8, relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.ent_cooldown.pack(side=tk.LEFT)
        self.ent_cooldown.insert(0, str(ev_cfg.get("cooldown_seconds", 8.0)))

        self._add_section_title(self.tab_storage, "Evidence Capture Options")
        self.var_save_img = tk.BooleanVar(value=ev_cfg.get("save_evidence_snapshots", True))
        tk.Checkbutton(self.tab_storage, text="Save Annotated JPEG Evidence Snapshots", variable=self.var_save_img, bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, selectcolor=Theme.BG_INPUT).pack(anchor="w", pady=2)

        self.var_save_clip = tk.BooleanVar(value=ev_cfg.get("save_evidence_clips", True))
        tk.Checkbutton(self.tab_storage, text="Save Incident Video Clips (MP4) from Rolling Buffer", variable=self.var_save_clip, bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, selectcolor=Theme.BG_INPUT).pack(anchor="w", pady=2)

    def _add_section_title(self, parent: tk.Frame, title: str):
        lbl = tk.Label(parent, text=title, bg=Theme.BG_CARD, fg=Theme.ACCENT_BLUE, font=Theme.FONT_BODY_BOLD)
        lbl.pack(anchor="w", pady=(10, 4))

    def _build_footer(self):
        fbar = tk.Frame(self, bg=Theme.BG_MAIN, pady=10)
        fbar.pack(fill=tk.X)

        tk.Button(
            fbar,
            text="💾 Save Configuration",
            bg="#0284c7",
            fg="#ffffff",
            font=Theme.FONT_BODY_BOLD,
            relief="flat",
            padx=16,
            pady=6,
            command=self._save_settings
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            fbar,
            text="↺ Reset to Defaults",
            bg="#334155",
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_BODY,
            relief="flat",
            padx=14,
            pady=6,
            command=self._reset_defaults
        ).pack(side=tk.LEFT)

    def _browse_model(self):
        p = filedialog.askopenfilename(title="Select YOLO Model Weights", filetypes=[("PyTorch Weights", "*.pt"), ("All Files", "*.*")])
        if p:
            self.ent_model_path.delete(0, tk.END)
            self.ent_model_path.insert(0, p)

    def _browse_file_into(self, entry_widget: tk.Entry):
        p = filedialog.askopenfilename(title="Select Model Weights", filetypes=[("Model Files", "*.pt *.onnx"), ("All Files", "*.*")])
        if p:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, p)

    def _test_model(self):
        mpath = self.ent_model_path.get().strip()
        if not os.path.exists(mpath):
            messagebox.showerror("Model Test Failed", f"File not found at:\n{mpath}")
            return
        try:
            from ultralytics import YOLO
            m = YOLO(mpath)
            messagebox.showinfo("Model Test Success", f"YOLO model successfully loaded!\nNames: {len(m.names)} classes detected.")
        except Exception as e:
            messagebox.showerror("Model Load Error", f"Failed loading model:\n{e}")

    def _save_settings(self):
        cm = self.controller.config_mgr
        try:
            # Detection
            cm.set("detection", "model_path", self.ent_model_path.get().strip())
            cm.set("detection", "confidence_threshold", round(float(self.slider_conf.get()), 2))
            cm.set("detection", "tracker_type", self.tracker_var.get())
            cm.set("detection", "custom_helmet_model", self.ent_helmet_path.get().strip())
            cm.set("detection", "custom_emergency_model", self.ent_emerg_path.get().strip())

            # Wrong Way
            cm.set("wrong_way", "expected_direction", self.dir_var.get())
            cm.set("wrong_way", "min_displacement_px", int(self.ent_ww_disp.get()))
            cm.set("wrong_way", "min_tracking_frames", int(self.ent_ww_frames.get()))

            # Stop Line
            sl_data = {
                "x1": int(self.ent_sl_x1.get()),
                "y1": int(self.ent_sl_y1.get()),
                "x2": int(self.ent_sl_x2.get()),
                "y2": int(self.ent_sl_y2.get())
            }
            cm.set("red_light", "stop_line", sl_data)

            # Density
            cm.set("density", "low_threshold", int(self.ent_dens_low.get()))
            cm.set("density", "medium_threshold", int(self.ent_dens_med.get()))

            # Event Engine
            cm.set("event_engine", "cooldown_seconds", float(self.ent_cooldown.get()))
            cm.set("event_engine", "save_evidence_snapshots", self.var_save_img.get())
            cm.set("event_engine", "save_evidence_clips", self.var_save_clip.get())

            cm.save()
            self.controller.apply_live_configuration()
            messagebox.showinfo("Settings Saved", "System configuration saved and applied successfully!")

        except ValueError as e:
            messagebox.showerror("Validation Error", f"Please check numerical input formats:\n{e}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save settings:\n{e}")

    def _reset_defaults(self):
        if messagebox.askyesno("Confirm Reset", "Reset all settings to default configuration?"):
            self.controller.config_mgr.reset_to_defaults()
            messagebox.showinfo("Reset Complete", "Settings reset to defaults. Please reopen settings to see updated values.")
