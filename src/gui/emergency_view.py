"""
Emergency Vehicles View for Smart Road Vision.
Manages priority emergency vehicle alerts, corridor clearance logs,
and custom model integration instructions.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from .theme import Theme


class EmergencyView(tk.Frame):
    """Emergency Vehicle priority surveillance and corridor clearance workspace."""

    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, bg=Theme.BG_MAIN, padx=14, pady=12, **kwargs)
        self.controller = controller
        self.selected_event = None
        self._thumb_photo = None

        # Top Header & Custom Model Architecture Banner
        self._build_header()

        # Split Body (Emergency Events Table on left, Details on right)
        self._build_body()

    def _build_header(self):
        hdr = tk.Frame(self, bg=Theme.BG_MAIN)
        hdr.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            hdr,
            text="PRIORITY EMERGENCY VEHICLE DISPATCH MONITOR",
            bg=Theme.BG_MAIN,
            fg=Theme.ACCENT_PURPLE,
            font=Theme.FONT_TITLE
        ).pack(anchor="w")

        # Architectural explanation banner
        model_status = self.controller.detector.emergency_model_status if self.controller.detector else "Not Configured"

        banner = tk.Frame(self, bg="#1a122e", highlightbackground=Theme.ACCENT_PURPLE, highlightthickness=1, padx=10, pady=8)
        banner.pack(fill=tk.X, pady=(0, 10))

        top_line = tk.Frame(banner, bg="#1a122e")
        top_line.pack(fill=tk.X)

        tk.Label(
            top_line,
            text=f"● EMERGENCY MODEL STATUS: {model_status}",
            bg="#1a122e",
            fg=Theme.ACCENT_PURPLE,
            font=Theme.FONT_BODY_BOLD
        ).pack(side=tk.LEFT)

        tk.Button(
            top_line,
            text="⚙ Configure Custom Model in Settings",
            bg=Theme.ACCENT_PURPLE,
            fg="#ffffff",
            font=Theme.FONT_SMALL,
            relief="flat",
            padx=8,
            command=lambda: self.controller.navigate_to("Settings")
        ).pack(side=tk.RIGHT)

        tk.Label(
            banner,
            text=(
                "Default COCO pretrained YOLO models detect generic vehicle classes (Car, Bus, Truck, Motorcycle). "
                "Detection of specialized ambulances, fire trucks, and police units utilizes the modular custom model pipeline. "
                "Load your custom trained YOLO weights in Settings to enable automatic class tagging without dummy fabrications."
            ),
            bg="#1a122e",
            fg="#d8b4fe",
            font=Theme.FONT_SMALL,
            wraplength=980,
            justify="left"
        ).pack(anchor="w", pady=(4, 0))

    def _build_body(self):
        body = tk.Frame(self, bg=Theme.BG_MAIN)
        body.pack(fill=tk.BOTH, expand=True)

        # Left Table of Emergency Incidents
        t_frame = tk.Frame(body, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        t_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        t_hdr = tk.Frame(t_frame, bg=Theme.BG_CARD, padx=8, pady=6)
        t_hdr.pack(fill=tk.X)
        tk.Label(t_hdr, text="EMERGENCY VEHICLE DETECTION LOG", bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SUBTITLE).pack(side=tk.LEFT)
        tk.Button(t_hdr, text="🔄 Refresh", bg="#334155", fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, relief="flat", padx=8, command=self.refresh_table).pack(side=tk.RIGHT)

        cols = ("event_id", "timestamp", "severity", "tracking_id", "camera_or_source", "verification_status")
        self.tree = ttk.Treeview(t_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("event_id", text="Event ID")
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("severity", text="Priority")
        self.tree.heading("tracking_id", text="Track ID")
        self.tree.heading("camera_or_source", text="Camera / Feed")
        self.tree.heading("verification_status", text="Verification Status")

        self.tree.column("event_id", width=140, anchor="w")
        self.tree.column("timestamp", width=130, anchor="center")
        self.tree.column("severity", width=80, anchor="center")
        self.tree.column("tracking_id", width=70, anchor="center")
        self.tree.column("camera_or_source", width=130, anchor="w")
        self.tree.column("verification_status", width=120, anchor="center")

        scroll = ttk.Scrollbar(t_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_row_selected)

        # Right Detail Pane
        self.detail_pane = tk.Frame(body, bg=Theme.BG_CARD, width=320, highlightbackground=Theme.BORDER, highlightthickness=1, padx=12, pady=12)
        self.detail_pane.pack(side=tk.RIGHT, fill=tk.Y)
        self.detail_pane.pack_propagate(False)

        tk.Label(
            self.detail_pane,
            text="PRIORITY DISPATCH DETAILS",
            bg=Theme.BG_CARD,
            fg=Theme.ACCENT_PURPLE,
            font=Theme.FONT_SUBTITLE
        ).pack(anchor="w", pady=(0, 8))

        # Evidence Canvas
        self.img_canvas = tk.Label(
            self.detail_pane,
            text="Select an emergency event to review",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL,
            height=9
        )
        self.img_canvas.pack(fill=tk.X, pady=(0, 8))

        self.lbl_em_id = self._add_detail_row("Event ID:", "-")
        self.lbl_em_time = self._add_detail_row("Timestamp:", "-")
        self.lbl_em_track = self._add_detail_row("Tracked Unit:", "-")
        self.lbl_em_source = self._add_detail_row("Corridor:", "-")
        self.lbl_em_status = self._add_detail_row("Status:", "-")

        tk.Label(self.detail_pane, text="Details:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_SMALL).pack(anchor="w", pady=(8, 2))
        self.lbl_em_desc = tk.Label(
            self.detail_pane,
            text="No selection",
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SMALL,
            anchor="nw",
            justify="left",
            wraplength=290,
            height=3
        )
        self.lbl_em_desc.pack(fill=tk.X, pady=(0, 10))

        # Button to open snapshot
        self.btn_open_img = tk.Button(
            self.detail_pane,
            text="🔍 Open Full Evidence",
            bg="#334155",
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SMALL,
            relief="flat",
            state="disabled",
            command=self._open_evidence
        )
        self.btn_open_img.pack(fill=tk.X, pady=(0, 12))

        # Verification buttons
        tk.Label(
            self.detail_pane,
            text="DISPATCHER VERIFICATION:",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_BODY_BOLD
        ).pack(anchor="w", pady=(0, 6))

        act_frame = tk.Frame(self.detail_pane, bg=Theme.BG_CARD)
        act_frame.pack(fill=tk.X)

        self.btn_confirm = tk.Button(
            act_frame,
            text="✔ Confirm",
            bg="#16a34a",
            fg="#ffffff",
            font=Theme.FONT_SMALL,
            relief="flat",
            state="disabled",
            command=lambda: self._update_status("CONFIRMED")
        )
        self.btn_confirm.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.btn_false_pos = tk.Button(
            act_frame,
            text="✖ False Alarm",
            bg="#dc2626",
            fg="#ffffff",
            font=Theme.FONT_SMALL,
            relief="flat",
            state="disabled",
            command=lambda: self._update_status("FALSE POSITIVE")
        )
        self.btn_false_pos.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.btn_review = tk.Button(
            act_frame,
            text="Reviewed",
            bg="#0284c7",
            fg="#ffffff",
            font=Theme.FONT_SMALL,
            relief="flat",
            state="disabled",
            command=lambda: self._update_status("REVIEWED")
        )
        self.btn_review.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

    def _add_detail_row(self, label: str, val: str) -> tk.Label:
        row = tk.Frame(self.detail_pane, bg=Theme.BG_CARD)
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=label, bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_SMALL).pack(side=tk.LEFT)
        lbl_v = tk.Label(row, text=val, bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_BODY_BOLD)
        lbl_v.pack(side=tk.RIGHT)
        return lbl_v

    def refresh_table(self):
        for r in self.tree.get_children():
            self.tree.delete(r)

        events = self.controller.event_logger.get_all_events()
        for ev in reversed(events):
            if ev.get("event_type") == "EMERGENCY_VEHICLE":
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        ev.get("event_id"),
                        ev.get("timestamp"),
                        ev.get("severity"),
                        ev.get("tracking_id"),
                        ev.get("camera_or_source"),
                        ev.get("verification_status")
                    )
                )

    def _on_row_selected(self, event):
        sel = self.tree.selection()
        if not sel:
            return

        item = self.tree.item(sel[0])
        event_id = item["values"][0]

        events = self.controller.event_logger.get_all_events()
        target = next((e for e in events if e.get("event_id") == str(event_id)), None)
        if not target:
            return

        self.selected_event = target
        self.lbl_em_id.config(text=target.get("event_id", "-"))
        self.lbl_em_time.config(text=target.get("timestamp", "-")[-8:])
        self.lbl_em_track.config(text=f"Vehicle #{target.get('tracking_id', '-')}")
        self.lbl_em_source.config(text=target.get("camera_or_source", "-")[:16])
        self.lbl_em_status.config(text=target.get("verification_status", "-"))
        self.lbl_em_desc.config(text=target.get("description", "-"))

        self.btn_confirm.config(state="normal")
        self.btn_false_pos.config(state="normal")
        self.btn_review.config(state="normal")

        ev_path = target.get("evidence_path", "-")
        if ev_path != "-" and os.path.exists(ev_path):
            self.btn_open_img.config(state="normal")
            try:
                img = Image.open(ev_path)
                img.thumbnail((290, 150))
                self._thumb_photo = ImageTk.PhotoImage(img)
                self.img_canvas.config(image=self._thumb_photo, text="")
            except Exception:
                self.img_canvas.config(image="", text="Could not load image thumbnail")
        else:
            self.btn_open_img.config(state="disabled")
            self.img_canvas.config(image="", text="No Evidence Snapshot Available")

    def _open_evidence(self):
        if not self.selected_event:
            return
        path = self.selected_event.get("evidence_path", "-")
        if path != "-" and os.path.exists(path):
            os.startfile(os.path.abspath(path))
        else:
            messagebox.showwarning("Evidence Missing", "Evidence snapshot could not be found.")

    def _update_status(self, new_status: str):
        if not self.selected_event:
            return
        eid = self.selected_event.get("event_id")
        self.controller.event_logger.update_verification_status(eid, new_status)
        self.lbl_em_status.config(text=new_status)
        self.refresh_table()
        messagebox.showinfo("Status Updated", f"Emergency Event {eid} marked as {new_status}.")
