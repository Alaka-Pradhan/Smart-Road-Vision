"""
Traffic Violations View for Smart Road Vision.
Displays filterable violation events (Wrong-Way, Red-Light, No-Helmet),
evidence previews, and human-in-the-loop verification controls.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from .theme import Theme


class ViolationsView(tk.Frame):
    """Traffic Violations monitoring and verification workspace."""

    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, bg=Theme.BG_MAIN, padx=14, pady=12, **kwargs)
        self.controller = controller
        self.selected_event = None
        self.active_filter = "ALL"
        self._thumb_photo = None

        # Header & Filter Bar
        self._build_header_and_filters()

        # Split Body (Table on left, Evidence & Action card on right)
        self._build_body()

    def _build_header_and_filters(self):
        hdr = tk.Frame(self, bg=Theme.BG_MAIN)
        hdr.pack(fill=tk.X, pady=(0, 10))

        left = tk.Frame(hdr, bg=Theme.BG_MAIN)
        left.pack(side=tk.LEFT)
        tk.Label(
            left,
            text="TRAFFIC VIOLATION AUDIT & ENFORCEMENT",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_TITLE
        ).pack(anchor="w")
        tk.Label(
            left,
            text="Wrong-Way Driving, Stop-Line Red-Light Violations, and Safety Audits",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL
        ).pack(anchor="w")

        # Filter Tabs Row
        filter_bar = tk.Frame(self, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1, padx=8, pady=6)
        filter_bar.pack(fill=tk.X, pady=(0, 10))

        tk.Label(filter_bar, text="FILTER BY TYPE:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY_BOLD).pack(side=tk.LEFT, padx=(0, 8))

        self.btn_f_all = tk.Button(filter_bar, text="ALL VIOLATIONS", bg=Theme.ACCENT_BLUE, fg="#000000", font=Theme.FONT_SMALL, relief="flat", padx=10, command=lambda: self._set_filter("ALL"))
        self.btn_f_all.pack(side=tk.LEFT, padx=3)

        self.btn_f_ww = tk.Button(filter_bar, text="WRONG WAY", bg="#334155", fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, relief="flat", padx=10, command=lambda: self._set_filter("WRONG_WAY"))
        self.btn_f_ww.pack(side=tk.LEFT, padx=3)

        self.btn_f_rl = tk.Button(filter_bar, text="RED LIGHT", bg="#334155", fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, relief="flat", padx=10, command=lambda: self._set_filter("RED_LIGHT"))
        self.btn_f_rl.pack(side=tk.LEFT, padx=3)

        self.btn_f_nh = tk.Button(filter_bar, text="NO HELMET", bg="#334155", fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, relief="flat", padx=10, command=lambda: self._set_filter("NO_HELMET"))
        self.btn_f_nh.pack(side=tk.LEFT, padx=3)

        # Refresh button
        tk.Button(filter_bar, text="🔄 Refresh", bg="#334155", fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, relief="flat", padx=10, command=self.refresh_table).pack(side=tk.RIGHT)

    def _build_body(self):
        body = tk.Frame(self, bg=Theme.BG_MAIN)
        body.pack(fill=tk.BOTH, expand=True)

        # Left Table Frame
        t_frame = tk.Frame(body, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        t_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        cols = ("event_id", "timestamp", "event_type", "severity", "tracking_id", "verification_status")
        self.tree = ttk.Treeview(t_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("event_id", text="Event ID")
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("event_type", text="Type")
        self.tree.heading("severity", text="Severity")
        self.tree.heading("tracking_id", text="Track ID")
        self.tree.heading("verification_status", text="Verification Status")

        self.tree.column("event_id", width=140, anchor="w")
        self.tree.column("timestamp", width=130, anchor="center")
        self.tree.column("event_type", width=110, anchor="center")
        self.tree.column("severity", width=80, anchor="center")
        self.tree.column("tracking_id", width=70, anchor="center")
        self.tree.column("verification_status", width=120, anchor="center")

        scroll = ttk.Scrollbar(t_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_row_selected)

        # Right Detail & Verification Pane
        self.detail_pane = tk.Frame(body, bg=Theme.BG_CARD, width=320, highlightbackground=Theme.BORDER, highlightthickness=1, padx=12, pady=12)
        self.detail_pane.pack(side=tk.RIGHT, fill=tk.Y)
        self.detail_pane.pack_propagate(False)

        tk.Label(
            self.detail_pane,
            text="EVIDENCE & VERIFICATION",
            bg=Theme.BG_CARD,
            fg=Theme.ACCENT_BLUE,
            font=Theme.FONT_SUBTITLE
        ).pack(anchor="w", pady=(0, 8))

        # Evidence image canvas
        self.img_canvas = tk.Label(
            self.detail_pane,
            text="Select an event to view evidence",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL,
            height=10
        )
        self.img_canvas.pack(fill=tk.X, pady=(0, 10))

        # Metadata labels
        self.lbl_det_id = self._add_detail_row("Event ID:", "-")
        self.lbl_det_type = self._add_detail_row("Violation:", "-")
        self.lbl_det_time = self._add_detail_row("Timestamp:", "-")
        self.lbl_det_vehicle = self._add_detail_row("Vehicle / ID:", "-")
        self.lbl_det_status = self._add_detail_row("Status:", "-")

        # Description
        tk.Label(self.detail_pane, text="Details:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_SMALL).pack(anchor="w", pady=(8, 2))
        self.lbl_det_desc = tk.Label(
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
        self.lbl_det_desc.pack(fill=tk.X, pady=(0, 10))

        # Open snapshot button
        self.btn_open_img = tk.Button(
            self.detail_pane,
            text="🔍 Open Full Evidence",
            bg="#334155",
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SMALL,
            relief="flat",
            state="disabled",
            command=self._open_evidence_file
        )
        self.btn_open_img.pack(fill=tk.X, pady=(0, 12))

        # Human Verification Actions
        tk.Label(
            self.detail_pane,
            text="OFFICER VERIFICATION ACTION:",
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

    def _set_filter(self, f_type: str):
        self.active_filter = f_type
        # Update button highlights
        self.btn_f_all.config(bg=Theme.ACCENT_BLUE if f_type == "ALL" else "#334155", fg="#000000" if f_type == "ALL" else Theme.TEXT_PRIMARY)
        self.btn_f_ww.config(bg=Theme.ACCENT_BLUE if f_type == "WRONG_WAY" else "#334155", fg="#000000" if f_type == "WRONG_WAY" else Theme.TEXT_PRIMARY)
        self.btn_f_rl.config(bg=Theme.ACCENT_BLUE if f_type == "RED_LIGHT" else "#334155", fg="#000000" if f_type == "RED_LIGHT" else Theme.TEXT_PRIMARY)
        self.btn_f_nh.config(bg=Theme.ACCENT_BLUE if f_type == "NO_HELMET" else "#334155", fg="#000000" if f_type == "NO_HELMET" else Theme.TEXT_PRIMARY)
        self.refresh_table()

    def refresh_table(self):
        """Reloads events into Treeview matching current violation filter."""
        for r in self.tree.get_children():
            self.tree.delete(r)

        events = self.controller.event_logger.get_all_events()
        violation_types = ["WRONG_WAY", "RED_LIGHT", "NO_HELMET"]

        for ev in reversed(events):
            etype = ev.get("event_type", "").upper()
            if etype not in violation_types:
                continue

            if self.active_filter != "ALL" and etype != self.active_filter:
                continue

            self.tree.insert(
                "",
                tk.END,
                values=(
                    ev.get("event_id"),
                    ev.get("timestamp"),
                    ev.get("event_type"),
                    ev.get("severity"),
                    ev.get("tracking_id"),
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
        self.lbl_det_id.config(text=target.get("event_id", "-"))
        self.lbl_det_type.config(text=target.get("event_type", "-"))
        self.lbl_det_time.config(text=target.get("timestamp", "-")[-8:])
        self.lbl_det_vehicle.config(text=f"Track #{target.get('tracking_id', '-')}")
        self.lbl_det_status.config(text=target.get("verification_status", "-"))
        self.lbl_det_desc.config(text=target.get("description", "-"))

        self.btn_confirm.config(state="normal")
        self.btn_false_pos.config(state="normal")
        self.btn_review.config(state="normal")

        # Load evidence thumbnail
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

    def _open_evidence_file(self):
        if not self.selected_event:
            return
        path = self.selected_event.get("evidence_path", "-")
        if path != "-" and os.path.exists(path):
            os.startfile(os.path.abspath(path))
        else:
            messagebox.showwarning("Evidence Missing", "Evidence file could not be found.")

    def _update_status(self, new_status: str):
        if not self.selected_event:
            return
        eid = self.selected_event.get("event_id")
        self.controller.event_logger.update_verification_status(eid, new_status)
        self.lbl_det_status.config(text=new_status)
        self.refresh_table()
        messagebox.showinfo("Status Updated", f"Event {eid} marked as {new_status}.")
