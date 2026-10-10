"""
Event Logs View for Smart Road Vision.
Provides comprehensive audit log inspection, multi-criteria filtering,
search, status mutation, and CSV export capabilities.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd

from .theme import Theme


class LogsView(tk.Frame):
    """Event Logs comprehensive data grid and export workspace."""

    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, bg=Theme.BG_MAIN, padx=14, pady=12, **kwargs)
        self.controller = controller
        self.selected_event = None

        # Header Bar
        self._build_header()

        # Search and Filters Bar
        self._build_filters_bar()

        # Main Table Area
        self._build_table()

        # Bottom Action Bar
        self._build_actions_bar()

    def _build_header(self):
        hdr = tk.Frame(self, bg=Theme.BG_MAIN)
        hdr.pack(fill=tk.X, pady=(0, 10))

        left = tk.Frame(hdr, bg=Theme.BG_MAIN)
        left.pack(side=tk.LEFT)
        tk.Label(
            left,
            text="SYSTEM INCIDENT AUDIT LOGS",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_TITLE
        ).pack(anchor="w")
        tk.Label(
            left,
            text="Immutable persistent records of all traffic violations, safety warnings, and emergency detections",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL
        ).pack(anchor="w")

        tk.Button(
            hdr,
            text="📥 Export to CSV",
            bg="#0284c7",
            fg="#ffffff",
            font=Theme.FONT_BODY_BOLD,
            relief="flat",
            padx=12,
            pady=4,
            command=self._export_csv
        ).pack(side=tk.RIGHT)

    def _build_filters_bar(self):
        fbar = tk.Frame(self, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1, padx=10, pady=8)
        fbar.pack(fill=tk.X, pady=(0, 10))

        # Search keyword
        tk.Label(fbar, text="SEARCH:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY_BOLD).pack(side=tk.LEFT, padx=(0, 4))
        self.entry_search = tk.Entry(
            fbar,
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT_PRIMARY,
            insertbackground=Theme.ACCENT_BLUE,
            relief="flat",
            highlightbackground=Theme.BORDER,
            highlightthickness=1,
            width=20,
            font=Theme.FONT_SMALL
        )
        self.entry_search.pack(side=tk.LEFT, padx=(0, 14))
        self.entry_search.bind("<KeyRelease>", lambda e: self.refresh_table())

        # Event type filter
        tk.Label(fbar, text="TYPE:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY_BOLD).pack(side=tk.LEFT, padx=(0, 4))
        self.type_var = tk.StringVar(value="ALL")
        self.combo_type = ttk.Combobox(
            fbar,
            textvariable=self.type_var,
            values=["ALL", "WRONG_WAY", "RED_LIGHT", "NO_HELMET", "POSSIBLE_ACCIDENT", "EMERGENCY_VEHICLE", "TRAFFIC_DENSITY", "ROAD_SAFETY"],
            state="readonly",
            width=16
        )
        self.combo_type.pack(side=tk.LEFT, padx=(0, 14))
        self.combo_type.bind("<<ComboboxSelected>>", lambda e: self.refresh_table())

        # Status filter
        tk.Label(fbar, text="STATUS:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY_BOLD).pack(side=tk.LEFT, padx=(0, 4))
        self.status_var = tk.StringVar(value="ALL")
        self.combo_status = ttk.Combobox(
            fbar,
            textvariable=self.status_var,
            values=["ALL", "PENDING REVIEW", "CONFIRMED", "FALSE POSITIVE", "REVIEWED"],
            state="readonly",
            width=16
        )
        self.combo_status.pack(side=tk.LEFT, padx=(0, 14))
        self.combo_status.bind("<<ComboboxSelected>>", lambda e: self.refresh_table())

        tk.Button(fbar, text="🔄 Reset Filters", bg="#334155", fg=Theme.TEXT_PRIMARY, font=Theme.FONT_SMALL, relief="flat", padx=10, command=self._reset_filters).pack(side=tk.RIGHT)

    def _build_table(self):
        t_frame = tk.Frame(self, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        t_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("event_id", "timestamp", "event_type", "severity", "tracking_id", "confidence", "verification_status", "evidence", "description")
        self.tree = ttk.Treeview(t_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("event_id", text="Event ID")
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("event_type", text="Type")
        self.tree.heading("severity", text="Severity")
        self.tree.heading("tracking_id", text="Track ID")
        self.tree.heading("confidence", text="Conf")
        self.tree.heading("verification_status", text="Audit Status")
        self.tree.heading("evidence", text="Evidence File")
        self.tree.heading("description", text="Description")

        self.tree.column("event_id", width=140, anchor="w")
        self.tree.column("timestamp", width=125, anchor="center")
        self.tree.column("event_type", width=115, anchor="center")
        self.tree.column("severity", width=75, anchor="center")
        self.tree.column("tracking_id", width=65, anchor="center")
        self.tree.column("confidence", width=55, anchor="center")
        self.tree.column("verification_status", width=115, anchor="center")
        self.tree.column("evidence", width=120, anchor="w")
        self.tree.column("description", width=240, anchor="w")

        v_scroll = ttk.Scrollbar(t_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(t_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_row_selected)

    def _build_actions_bar(self):
        abar = tk.Frame(self, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1, padx=10, pady=8)
        abar.pack(fill=tk.X, pady=(10, 0))

        self.lbl_selected_info = tk.Label(
            abar,
            text="Selected: None",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_SECONDARY,
            font=Theme.FONT_BODY_BOLD
        )
        self.lbl_selected_info.pack(side=tk.LEFT, padx=(0, 16))

        # View Evidence
        self.btn_view_ev = tk.Button(
            abar,
            text="🖼 View Evidence",
            bg="#334155",
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SMALL,
            relief="flat",
            state="disabled",
            command=self._view_evidence
        )
        self.btn_view_ev.pack(side=tk.LEFT, padx=4)

        # Verification status modifier buttons
        self.btn_confirm = tk.Button(
            abar,
            text="✔ Confirm",
            bg="#16a34a",
            fg="#ffffff",
            font=Theme.FONT_SMALL,
            relief="flat",
            state="disabled",
            command=lambda: self._set_status("CONFIRMED")
        )
        self.btn_confirm.pack(side=tk.RIGHT, padx=4)

        self.btn_false = tk.Button(
            abar,
            text="✖ False Positive",
            bg="#dc2626",
            fg="#ffffff",
            font=Theme.FONT_SMALL,
            relief="flat",
            state="disabled",
            command=lambda: self._set_status("FALSE POSITIVE")
        )
        self.btn_false.pack(side=tk.RIGHT, padx=4)

        self.btn_reviewed = tk.Button(
            abar,
            text="Reviewed",
            bg="#0284c7",
            fg="#ffffff",
            font=Theme.FONT_SMALL,
            relief="flat",
            state="disabled",
            command=lambda: self._set_status("REVIEWED")
        )
        self.btn_reviewed.pack(side=tk.RIGHT, padx=4)

    def _reset_filters(self):
        self.entry_search.delete(0, tk.END)
        self.type_var.set("ALL")
        self.status_var.set("ALL")
        self.refresh_table()

    def refresh_table(self):
        """Filters and refreshes all log rows."""
        for r in self.tree.get_children():
            self.tree.delete(r)

        events = self.controller.event_logger.get_all_events()
        search_kw = self.entry_search.get().strip().lower()
        filter_type = self.type_var.get()
        filter_status = self.status_var.get()

        for ev in reversed(events):
            etype = ev.get("event_type", "").upper()
            status = ev.get("verification_status", "").upper()
            eid = ev.get("event_id", "").lower()
            desc = ev.get("description", "").lower()
            tid = ev.get("tracking_id", "").lower()

            if filter_type != "ALL" and etype != filter_type.upper():
                continue
            if filter_status != "ALL" and status != filter_status.upper():
                continue
            if search_kw and (search_kw not in eid and search_kw not in desc and search_kw not in tid):
                continue

            ev_path = ev.get("evidence_path", "-")
            ev_label = os.path.basename(ev_path) if (ev_path != "-" and os.path.exists(ev_path)) else ("Yes" if ev_path != "-" else "None")

            self.tree.insert(
                "",
                tk.END,
                values=(
                    ev.get("event_id"),
                    ev.get("timestamp"),
                    ev.get("event_type"),
                    ev.get("severity"),
                    ev.get("tracking_id"),
                    ev.get("confidence"),
                    ev.get("verification_status"),
                    ev_label,
                    ev.get("description")
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
        self.lbl_selected_info.config(text=f"Selected: {event_id} ({target.get('event_type')})")

        self.btn_confirm.config(state="normal")
        self.btn_false.config(state="normal")
        self.btn_reviewed.config(state="normal")

        ev_path = target.get("evidence_path", "-")
        self.btn_view_ev.config(state="normal" if (ev_path != "-" and os.path.exists(ev_path)) else "disabled")

    def _view_evidence(self):
        if not self.selected_event:
            return
        path = self.selected_event.get("evidence_path", "-")
        if path != "-" and os.path.exists(path):
            os.startfile(os.path.abspath(path))
        else:
            messagebox.showwarning("File Missing", "Evidence file is not available on disk.")

    def _set_status(self, new_status: str):
        if not self.selected_event:
            return
        eid = self.selected_event.get("event_id")
        self.controller.event_logger.update_verification_status(eid, new_status)
        self.refresh_table()
        self.lbl_selected_info.config(text=f"Selected: {eid} -> {new_status}")
        messagebox.showinfo("Status Updated", f"Event {eid} marked as {new_status}.")

    def _export_csv(self):
        default_name = f"traffic_events_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        out = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if out:
            success = self.controller.event_logger.export_filtered_csv(
                output_path=out,
                event_type=self.type_var.get(),
                status=self.status_var.get()
            )
            if success:
                messagebox.showinfo("Export Successful", f"Events exported successfully to:\n{out}")
            else:
                messagebox.showerror("Export Failed", "Could not export event logs.")
