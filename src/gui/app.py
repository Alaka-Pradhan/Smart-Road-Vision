"""
Main GUI Application Controller for Smart Road Vision.
Coordinates the dark control-room dashboard, 9 sidebar views,
background video pipeline thread, thread-safe queues, and life-cycle cleanups.
"""

import os
import sys
import queue
import logging
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np

from .theme import Theme
from ..config_manager import ConfigManager
from ..event_logger import EventLogger
from ..evidence_manager import EvidenceManager
from ..detector import ObjectDetector
from ..tracker import TrafficTracker
from ..violation_detector import ViolationDetector
from ..accident_detector import PossibleAccidentDetector
from ..emergency_detector import EmergencyVehicleDetector
from ..traffic_analyzer import TrafficDensityAnalyzer
from ..event_engine import EventEngine
from ..video_processor import VideoProcessor

# Views
from .dashboard_view import DashboardView
from .monitoring_view import MonitoringView
from .violations_view import ViolationsView
from .accidents_view import AccidentsView
from .emergency_view import EmergencyView
from .analytics_view import AnalyticsView
from .logs_view import LogsView
from .gallery_view import GalleryView
from .settings_view import SettingsView

logger = logging.getLogger(__name__)


class SmartRoadVisionApp:
    """Main application orchestrator."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Smart Road Vision — AI Intelligent Traffic Monitoring & Road Safety System")

        # Calculate optimal window dimensions for laptop/desktop screen (e.g. 1366x768)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        target_w = min(1280, max(960, screen_w - 60))
        target_h = min(800, max(560, screen_h - 75))
        pos_x = max(0, (screen_w - target_w) // 2)
        pos_y = max(0, (screen_h - target_h) // 2 - 15)

        self.root.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")
        self.root.minsize(960, 560)
        self.root.configure(bg=Theme.BG_MAIN)

        # Bring window to foreground
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(300, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()

        Theme.apply_ttk_theme(self.root)

        # 1. Initialize Core Business Systems
        self.config_mgr = ConfigManager()
        self.event_logger = EventLogger(
            csv_path=self.config_mgr.get("event_engine", "csv_log_path", "data/logs/events.csv"),
            json_path=self.config_mgr.get("event_engine", "json_log_path", "data/logs/events.json")
        )
        self.evidence_manager = EvidenceManager(
            base_evidence_dir=self.config_mgr.get("event_engine", "evidence_dir", "data/evidence")
        )

        det_cfg = self.config_mgr.get("detection", default={})
        self.detector = ObjectDetector(
            model_path=det_cfg.get("model_path", "models/yolov8n.pt"),
            confidence_threshold=det_cfg.get("confidence_threshold", 0.35),
            iou_threshold=det_cfg.get("iou_threshold", 0.45),
            tracker_type=det_cfg.get("tracker_type", "bytetrack.yaml"),
            custom_helmet_model=det_cfg.get("custom_helmet_model", ""),
            custom_emergency_model=det_cfg.get("custom_emergency_model", "")
        )

        self.tracker = TrafficTracker()
        self.violation_detector = ViolationDetector(self.config_mgr.get_all())
        self.accident_detector = PossibleAccidentDetector(self.config_mgr.get_all())
        self.emergency_detector = EmergencyVehicleDetector(self.config_mgr.get_all())
        self.traffic_analyzer = TrafficDensityAnalyzer(self.config_mgr.get_all())

        self.event_engine = EventEngine(
            event_logger=self.event_logger,
            evidence_manager=self.evidence_manager,
            cooldown_seconds=self.config_mgr.get("event_engine", "cooldown_seconds", 8.0)
        )
        self.event_engine.set_callback(self._on_event_dispatched)

        # 2. Thread-safe Frame Communication Queue
        self.frame_queue = queue.Queue(maxsize=4)

        # 3. Video Processor
        self.video_processor = VideoProcessor(
            config=self.config_mgr.get_all(),
            detector=self.detector,
            tracker=self.tracker,
            violation_detector=self.violation_detector,
            accident_detector=self.accident_detector,
            emergency_detector=self.emergency_detector,
            traffic_analyzer=self.traffic_analyzer,
            event_engine=self.event_engine,
            frame_queue=self.frame_queue
        )

        # Set default source to sample_traffic.mp4 if present
        if os.path.exists("sample_traffic.mp4"):
            self.video_processor.set_source("file", os.path.abspath("sample_traffic.mp4"))

        # 4. Construct Layout: Left Sidebar + Right Main Workspace
        self._build_main_layout()

        # 5. Build 9 Views
        self._build_views()

        # 6. Start GUI Polling Loop for Video Frames
        self.active_view_name = "Dashboard"
        self.navigate_to("Dashboard")
        self.last_density_info = None
        self._poll_frame_queue()
        self._poll_dashboard_metrics()

        # 7. Bind Clean Window Close Protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_main_layout(self):
        # Master container
        self.main_container = tk.Frame(self.root, bg=Theme.BG_MAIN)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Left Sidebar (prominent width 250, distinct dark navy background and border)
        self.sidebar = tk.Frame(
            self.main_container,
            bg=Theme.BG_SIDEBAR,
            width=250,
            highlightbackground=Theme.BORDER,
            highlightthickness=1
        )
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Right Content View Area
        self.view_container = tk.Frame(self.main_container, bg=Theme.BG_MAIN)
        self.view_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_sidebar()

    def _build_sidebar(self):
        # Brand Banner
        brand_frame = tk.Frame(self.sidebar, bg=Theme.BG_SIDEBAR, padx=16, pady=16)
        brand_frame.pack(fill=tk.X)

        tk.Label(
            brand_frame,
            text="🛣 SMART ROAD VISION",
            bg=Theme.BG_SIDEBAR,
            fg=Theme.ACCENT_BLUE,
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        ).pack(fill=tk.X)

        tk.Label(
            brand_frame,
            text="AI Road Traffic & Safety System",
            bg=Theme.BG_SIDEBAR,
            fg=Theme.TEXT_SECONDARY,
            font=("Segoe UI", 9),
            anchor="w"
        ).pack(fill=tk.X, pady=(2, 0))

        tk.Label(
            brand_frame,
            text="B.Tech Final Year Major Project",
            bg=Theme.BG_SIDEBAR,
            fg=Theme.TEXT_MUTED,
            font=("Segoe UI", 8),
            anchor="w"
        ).pack(fill=tk.X, pady=(1, 0))

        # Divider line
        tk.Frame(self.sidebar, bg=Theme.BORDER, height=1).pack(fill=tk.X, pady=(4, 10))

        # 9 Navigation Buttons
        self.nav_items = [
            ("Dashboard", "📊  Dashboard"),
            ("Live Monitoring", "📹  Live Monitoring"),
            ("Traffic Violations", "🚨  Traffic Violations"),
            ("Accident Alerts", "💥  Accident Alerts"),
            ("Emergency Vehicles", "🚑  Emergency Fleet"),
            ("Traffic Analytics", "📈  Traffic Analytics"),
            ("Event Logs", "📋  Event Logs"),
            ("Evidence Gallery", "🖼  Evidence Gallery"),
            ("Settings", "⚙  Settings")
        ]

        self.nav_buttons = {}
        for key, label in self.nav_items:
            btn = tk.Button(
                self.sidebar,
                text=label,
                bg=Theme.BG_SIDEBAR,
                fg=Theme.TEXT_SECONDARY,
                font=Theme.FONT_BODY_BOLD,
                relief="flat",
                anchor="w",
                padx=16,
                pady=9,
                bd=0,
                cursor="hand2",
                command=lambda k=key: self.navigate_to(k)
            )
            btn.pack(fill=tk.X, padx=8, pady=2)

            # Interactive hover highlight
            btn.bind("<Enter>", lambda e, b=btn, k=key: self._on_nav_hover(b, k, True))
            btn.bind("<Leave>", lambda e, b=btn, k=key: self._on_nav_hover(b, k, False))
            self.nav_buttons[key] = btn

        # Bottom System Info Badge
        bot_info = tk.Frame(
            self.sidebar,
            bg="#080d1a",
            padx=14,
            pady=12,
            highlightbackground=Theme.BORDER,
            highlightthickness=1
        )
        bot_info.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        # Model readiness status
        mod_status = "YOLOv8 AI: READY" if self.detector.is_loaded else "MODEL MISSING"
        mod_col = Theme.ACCENT_GREEN if self.detector.is_loaded else Theme.ACCENT_RED
        tk.Label(
            bot_info,
            text=f"● {mod_status}",
            bg="#080d1a",
            fg=mod_col,
            font=("Segoe UI", 9, "bold"),
            anchor="w"
        ).pack(fill=tk.X)

        tk.Label(
            bot_info,
            text="● CCTV PIPELINE: ACTIVE",
            bg="#080d1a",
            fg=Theme.ACCENT_BLUE,
            font=("Segoe UI", 8, "bold"),
            anchor="w"
        ).pack(fill=tk.X, pady=(2, 0))

        tk.Label(
            bot_info,
            text="SafeRoad Intelligence v1.0\nComputer Vision & Road Safety",
            bg="#080d1a",
            fg=Theme.TEXT_MUTED,
            font=("Segoe UI", 7),
            justify="left",
            anchor="w"
        ).pack(fill=tk.X, pady=(4, 0))

    def _on_nav_hover(self, btn: tk.Button, key: str, is_hover: bool):
        """Micro-animation hover effect on sidebar buttons."""
        if key == self.active_view_name:
            return
        if is_hover:
            btn.config(bg="#141e33", fg=Theme.TEXT_PRIMARY)
        else:
            btn.config(bg=Theme.BG_SIDEBAR, fg=Theme.TEXT_SECONDARY)

    def _build_views(self):
        """Initializes all 9 view frames."""
        self.views = {}

        self.views["Dashboard"] = DashboardView(self.view_container, controller=self)
        self.views["Live Monitoring"] = MonitoringView(self.view_container, controller=self)
        self.views["Traffic Violations"] = ViolationsView(self.view_container, controller=self)
        self.views["Accident Alerts"] = AccidentsView(self.view_container, controller=self)
        self.views["Emergency Vehicles"] = EmergencyView(self.view_container, controller=self)
        self.views["Traffic Analytics"] = AnalyticsView(self.view_container, controller=self)
        self.views["Event Logs"] = LogsView(self.view_container, controller=self)
        self.views["Evidence Gallery"] = GalleryView(self.view_container, controller=self)
        self.views["Settings"] = SettingsView(self.view_container, controller=self)

    def navigate_to(self, view_name: str):
        """Switches current visible view."""
        if view_name not in self.views:
            return

        self.active_view_name = view_name

        # Highlight active navigation button
        for k, btn in self.nav_buttons.items():
            if k == view_name:
                btn.config(bg=Theme.BG_CARD_LIGHT, fg=Theme.ACCENT_BLUE)
            else:
                btn.config(bg=Theme.BG_SIDEBAR, fg=Theme.TEXT_SECONDARY)

        # Show target view, hide others
        for k, view in self.views.items():
            if k == view_name:
                view.pack(fill=tk.BOTH, expand=True)
                # Trigger view-specific refreshes
                if hasattr(view, "refresh_table"):
                    view.refresh_table()
                elif hasattr(view, "refresh_charts"):
                    view.refresh_charts()
                elif hasattr(view, "refresh_gallery"):
                    view.refresh_gallery()
            else:
                view.pack_forget()

    def toggle_monitoring(self):
        """Starts or stops video monitoring."""
        if self.video_processor.is_running:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def start_monitoring(self):
        """Starts background video pipeline."""
        if not self.detector.is_loaded:
            messagebox.showwarning(
                "Model Not Loaded",
                f"YOLO model failed to load:\n{self.detector.load_error}\n\nPlease check Settings."
            )
            return

        self.video_processor.start()

    def pause_monitoring(self):
        self.video_processor.pause()

    def resume_monitoring(self):
        self.video_processor.resume()

    def stop_monitoring(self):
        self.video_processor.stop()
        # Reset canvas standby
        if "Dashboard" in self.views:
            self.views["Dashboard"].video_canvas.render_standby()
        if "Live Monitoring" in self.views:
            self.views["Live Monitoring"].video_canvas.render_standby()

    def reset_monitoring(self):
        self.video_processor.reset()

    def configure_and_start_source(self, source_type: str, source_param: Any):
        """Switches source and starts playback."""
        self.video_processor.stop()
        self.video_processor.set_source(source_type, source_param)
        self.video_processor.start()

    def set_signal_state(self, state: str):
        """Updates traffic signal lamp state."""
        self.video_processor.set_signal_state(state)

    def apply_live_configuration(self):
        """Updates live detector and rule thresholds from modified ConfigManager."""
        all_cfg = self.config_mgr.get_all()
        det = all_cfg.get("detection", {})

        self.detector.confidence_threshold = det.get("confidence_threshold", 0.35)
        self.detector.tracker_type = det.get("tracker_type", "bytetrack.yaml")
        self.violation_detector.update_config(all_cfg)
        self.accident_detector.update_config(all_cfg)
        self.emergency_detector.update_config(all_cfg)
        self.traffic_analyzer.update_config(all_cfg)
        self.event_engine.cooldown_seconds = all_cfg.get("event_engine", {}).get("cooldown_seconds", 8.0)

    def _poll_frame_queue(self):
        """Pulls latest processed video frames from queue and dispatches to active canvas."""
        try:
            while not self.frame_queue.empty():
                item = self.frame_queue.get_nowait()
                frame = item.get("frame")
                active_count = item.get("active_tracks_count", 0)
                self.last_density_info = item.get("density_result")

                # Send frame to visible video canvas
                if self.active_view_name == "Dashboard":
                    self.views["Dashboard"].video_canvas.display_frame(frame)
                elif self.active_view_name == "Live Monitoring":
                    self.views["Live Monitoring"].video_canvas.display_frame(frame)

                # Update live telemetry on Monitoring view
                if self.active_view_name == "Live Monitoring":
                    self.views["Live Monitoring"].update_telemetry(
                        source_name=self.video_processor.source_display_name,
                        active_count=active_count,
                        density_result=self.last_density_info,
                        class_counts=self.tracker.get_class_counts(),
                        fps=self.video_processor.video_fps
                    )

        except queue.Empty:
            pass
        except Exception as e:
            logger.debug(f"Queue render exception: {e}")

        # Schedule next queue check (30ms ~ 33fps UI update rate)
        self.root.after(30, self._poll_frame_queue)

    def _poll_dashboard_metrics(self):
        """Refreshes summary statistics and recent alert feed every 1 second."""
        try:
            stats = self.event_logger.get_summary_statistics()
            stats["total_vehicles"] = self.tracker.get_total_unique_vehicles()

            if "Dashboard" in self.views:
                self.views["Dashboard"].update_metrics(
                    stats=stats,
                    is_monitoring=self.video_processor.is_running,
                    density_info=self.last_density_info
                )
                recent_events = self.event_engine.get_recent_events(limit=10)
                self.views["Dashboard"].alerts_ticker.update_events(recent_events)

        except Exception as e:
            logger.debug(f"Dashboard poll error: {e}")

        self.root.after(1000, self._poll_dashboard_metrics)

    def _on_event_dispatched(self, event_record: dict):
        """Callback triggered immediately when EventEngine logs a new incident."""
        # Refresh tables if viewing violations or accidents
        if self.active_view_name in ["Traffic Violations", "Accident Alerts", "Emergency Vehicles", "Event Logs"]:
            active_view = self.views.get(self.active_view_name)
            if hasattr(active_view, "refresh_table"):
                active_view.refresh_table()

    def show_event_dialog(self, event_record: dict):
        """Opens quick event inspector modal."""
        self.navigate_to("Event Logs")

    def on_close(self):
        """Clean shutdown procedure."""
        try:
            self.video_processor.stop()
        except Exception:
            pass
        self.root.destroy()
        sys.exit(0)
