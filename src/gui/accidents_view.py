"""
Possible Accident Alerts View for Smart Road Vision.
Provides incident triage, heuristic collision pattern breakdown,
snapshot/clip playback, and verification actions.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from .theme import Theme


class AccidentsView(tk.Frame):
    """Possible Accident Alerts review and investigation workspace."""

    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, bg=Theme.BG_MAIN, padx=14, pady=12, **kwargs)
        self.controller = controller
        self.selected_event = None
        self._thumb_photo = None

        # Top Header & Academic Disclaimer Banner
        self._build_header()

        # Split Body (Alerts list on left, Incident Investigation on right)
        self._build_body()

    def _build_header(self):
        hdr = tk.Frame(self, bg=Theme.BG_MAIN)
        hdr.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            hdr,
            text="POSSIBLE ACCIDENT & COLLISION ALERTS",
            bg=Theme.BG_MAIN,
            fg=Theme.ACCENT_RED,
            font=Theme.FONT_TITLE
        ).pack(anchor="w")

        # AI Vision Engine Status Banner
        ai_loaded = (
            hasattr(self.controller, "accident_detector")
            and getattr(self.controller.accident_detector, "is_ai_loaded", lambda: False)()
        )
        banner_bg = "#13231e" if ai_loaded else "#2d1515"
        banner_border = Theme.ACCENT_GREEN if ai_loaded else Theme.ACCENT_RED
        banner_fg_title = Theme.ACCENT_GREEN if ai_loaded else Theme.ACCENT_RED
        banner_title = (
            "🤖 DUAL-ENGINE AI VISION ACTIVE: Fine-Tuned Ultralytics YOLO11x (Enos-123) + Kinematics Verification"
            if ai_loaded else
            "⚠ HEURISTIC TRAJECTORY KINEMATICS ENGINE (YOLO11x Deep Learning Standby)"
        )
        banner_desc = (
            "Deep learning accident classifier trained on traffic incident surveillance data. "
            "Operates via asynchronous worker thread with spatial cooldown to guarantee fluid 30 FPS playback."
            if ai_loaded else
            "Analyzes sudden deceleration, multi-vehicle proximity, and sustained roadway standstill. "
            "YOLO11x model weights can be placed in models/accident_yolo11x.pt for direct AI classification."
        )

        note_frame = tk.Frame(self, bg=banner_bg, highlightbackground=banner_border, highlightthickness=1, padx=10, pady=6)
        note_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            note_frame,
            text=banner_title,
            bg=banner_bg,
            fg=banner_fg_title,
            font=Theme.FONT_BODY_BOLD
        ).pack(anchor="w")

        tk.Label(
            note_frame,
            text=banner_desc,
            bg=banner_bg,
            fg="#94a3b8",
            font=Theme.FONT_SMALL,
            wraplength=980,
            justify="left"
        ).pack(anchor="w")

    def _build_body(self):
        body = tk.Frame(self, bg=Theme.BG_MAIN)
        body.pack(fill=tk.BOTH, expand=True)

        # Left Table of Accident Alerts
        t_frame = tk.Frame(body, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        t_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        t_hdr = tk.Frame(t_frame, bg=Theme.BG_CARD, padx=8, pady=6)
        t_hdr.pack(fill=tk.X)
        tk.Label(t_hdr, text="ACTIVE ACCIDENT INCIDENT LOG", bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SUBTITLE).pack(side=tk.LEFT)
        tk.Button(t_hdr, text="🔄 Refresh", bg="#334155", fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, relief="flat", padx=8, command=self.refresh_table).pack(side=tk.RIGHT)

        cols = ("event_id", "timestamp", "severity", "tracking_id", "confidence", "verification_status")
        self.tree = ttk.Treeview(t_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("event_id", text="Event ID")
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("severity", text="Severity")
        self.tree.heading("tracking_id", text="Track ID")
        self.tree.heading("confidence", text="Confidence")
        self.tree.heading("verification_status", text="Verification Status")

        self.tree.column("event_id", width=140, anchor="w")
        self.tree.column("timestamp", width=130, anchor="center")
        self.tree.column("severity", width=80, anchor="center")
        self.tree.column("tracking_id", width=70, anchor="center")
        self.tree.column("confidence", width=80, anchor="center")
        self.tree.column("verification_status", width=120, anchor="center")

        scroll = ttk.Scrollbar(t_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_row_selected)

        # Right Investigation & Evidence Pane
        self.detail_pane = tk.Frame(body, bg=Theme.BG_CARD, width=340, highlightbackground=Theme.BORDER, highlightthickness=1, padx=12, pady=12)
        self.detail_pane.pack(side=tk.RIGHT, fill=tk.Y)
        self.detail_pane.pack_propagate(False)

        tk.Label(
            self.detail_pane,
            text="COLLISION EVIDENCE & IMPACT",
            bg=Theme.BG_CARD,
            fg=Theme.ACCENT_RED,
            font=Theme.FONT_SUBTITLE
        ).pack(anchor="w", pady=(0, 8))

        # Evidence image canvas
        self.img_canvas = tk.Label(
            self.detail_pane,
            text="Select an incident to review evidence",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL,
            height=9
        )
        self.img_canvas.pack(fill=tk.X, pady=(0, 8))

        # Metadata rows
        self.lbl_acc_id = self._add_detail_row("Event ID:", "-")
        self.lbl_acc_time = self._add_detail_row("Timestamp:", "-")
        self.lbl_acc_track = self._add_detail_row("Tracked Vehicle:", "-")
        self.lbl_acc_status = self._add_detail_row("Status:", "-")

        # Heuristic Indicators Breakdown
        tk.Label(self.detail_pane, text="HEURISTIC INDICATORS:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY_BOLD).pack(anchor="w", pady=(8, 2))
        self.lbl_acc_desc = tk.Label(
            self.detail_pane,
            text="No incident selected",
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SMALL,
            anchor="nw",
            justify="left",
            wraplength=310,
            height=3
        )
        self.lbl_acc_desc.pack(fill=tk.X, pady=(0, 10))

        # Media buttons
        media_box = tk.Frame(self.detail_pane, bg=Theme.BG_CARD)
        media_box.pack(fill=tk.X, pady=(0, 12))

        self.btn_open_img = tk.Button(
            media_box,
            text="🖼 Open Snapshot",
            bg="#334155",
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SMALL,
            relief="flat",
            state="disabled",
            command=self._open_evidence_image
        )
        self.btn_open_img.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.btn_play_clip = tk.Button(
            media_box,
            text="▶ Play Video Clip",
            bg="#334155",
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SMALL,
            relief="flat",
            state="disabled",
            command=self._play_evidence_clip
        )
        self.btn_play_clip.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        # Human Verification Actions
        tk.Label(
            self.detail_pane,
            text="OPERATOR TRIAGE ACTION:",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_BODY_BOLD
        ).pack(anchor="w", pady=(0, 6))

        act_frame = tk.Frame(self.detail_pane, bg=Theme.BG_CARD)
        act_frame.pack(fill=tk.X)

        self.btn_confirm = tk.Button(
            act_frame,
            text="✔ Confirm Collision",
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
            if ev.get("event_type") == "POSSIBLE_ACCIDENT":
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        ev.get("event_id"),
                        ev.get("timestamp"),
                        ev.get("severity"),
                        ev.get("tracking_id"),
                        ev.get("confidence"),
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
        self.lbl_acc_id.config(text=target.get("event_id", "-"))
        self.lbl_acc_time.config(text=target.get("timestamp", "-")[-8:])
        self.lbl_acc_track.config(text=f"Vehicle #{target.get('tracking_id', '-')}")
        self.lbl_acc_status.config(text=target.get("verification_status", "-"))
        self.lbl_acc_desc.config(text=target.get("description", "-"))

        self.btn_confirm.config(state="normal")
        self.btn_false_pos.config(state="normal")
        self.btn_review.config(state="normal")

        # Evidence files check
        ev_path = target.get("evidence_path", "-")
        has_file = (ev_path != "-" and os.path.exists(ev_path))

        if has_file:
            self.btn_open_img.config(state="normal")
            if ev_path.lower().endswith((".mp4", ".avi")):
                self.btn_play_clip.config(state="normal")
            else:
                # Look for matching mp4 clip in evidence folder
                clip_guess = os.path.splitext(ev_path)[0] + ".mp4"
                self.btn_play_clip.config(state="normal" if os.path.exists(clip_guess) else "disabled")

            # Try showing image preview
            img_path = ev_path if not ev_path.lower().endswith((".mp4", ".avi")) else (os.path.splitext(ev_path)[0] + ".jpg")
            if os.path.exists(img_path):
                try:
                    img = Image.open(img_path)
                    img.thumbnail((310, 150))
                    self._thumb_photo = ImageTk.PhotoImage(img)
                    self.img_canvas.config(image=self._thumb_photo, text="")
                except Exception:
                    self.img_canvas.config(image="", text="Could not render thumbnail")
            else:
                self.img_canvas.config(image="", text="Video Clip Evidence Recorded")
        else:
            self.btn_open_img.config(state="disabled")
            self.btn_play_clip.config(state="disabled")
            self.img_canvas.config(image="", text="No Evidence Snapshot Available")

    def _open_evidence_image(self):
        if not self.selected_event:
            return
        path = self.selected_event.get("evidence_path", "-")
        if path != "-" and os.path.exists(path):
            os.startfile(os.path.abspath(path))
        else:
            messagebox.showwarning("Evidence Missing", "Evidence snapshot could not be found.")

    def _play_evidence_clip(self):
        if not self.selected_event:
            return
        path = self.selected_event.get("evidence_path", "-")
        clip_path = path if path.lower().endswith((".mp4", ".avi")) else (os.path.splitext(path)[0] + ".mp4")
        if os.path.exists(clip_path):
            os.startfile(os.path.abspath(clip_path))
        else:
            messagebox.showwarning("Clip Missing", "Video clip is not available for this event.")

    def _update_status(self, new_status: str):
        if not self.selected_event:
            return
        eid = self.selected_event.get("event_id")
        self.controller.event_logger.update_verification_status(eid, new_status)
        self.lbl_acc_status.config(text=new_status)
        self.refresh_table()
        messagebox.showinfo("Status Updated", f"Accident Alert {eid} updated to {new_status}.")
