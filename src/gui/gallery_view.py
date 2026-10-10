"""
Evidence Gallery View for Smart Road Vision.
Provides visual grid browsing of captured violation snapshots and collision clips,
category filtering, and preview dialogs.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from .theme import Theme


class GalleryView(tk.Frame):
    """Evidence Gallery thumbnail grid and media inspector."""

    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, bg=Theme.BG_MAIN, padx=14, pady=12, **kwargs)
        self.controller = controller
        self.active_category = "ALL"
        self._thumb_cache = []  # Keep references so Python garbage collector does not delete them

        # Header Bar
        self._build_header()

        # Category Filter Bar
        self._build_filter_bar()

        # Scrollable Thumbnail Grid
        self._build_grid()

    def _build_header(self):
        hdr = tk.Frame(self, bg=Theme.BG_MAIN)
        hdr.pack(fill=tk.X, pady=(0, 10))

        left = tk.Frame(hdr, bg=Theme.BG_MAIN)
        left.pack(side=tk.LEFT)
        tk.Label(
            left,
            text="FORENSIC EVIDENCE REPOSITORY",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_TITLE
        ).pack(anchor="w")
        tk.Label(
            left,
            text="High-resolution timestamped violation snapshots and incident video clips",
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL
        ).pack(anchor="w")

        tk.Button(
            hdr,
            text="🔄 Refresh Gallery",
            bg="#334155",
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_SMALL,
            relief="flat",
            padx=12,
            pady=4,
            command=self.refresh_gallery
        ).pack(side=tk.RIGHT)

    def _build_filter_bar(self):
        fbar = tk.Frame(self, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1, padx=8, pady=6)
        fbar.pack(fill=tk.X, pady=(0, 10))

        tk.Label(fbar, text="CATEGORY:", bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_BODY_BOLD).pack(side=tk.LEFT, padx=(0, 8))

        cats = [
            ("ALL", "ALL"),
            ("WRONG WAY", "wrong_way"),
            ("RED LIGHT", "red_light"),
            ("ACCIDENTS", "possible_accident"),
            ("EMERGENCY", "emergency_vehicle"),
            ("ROAD SAFETY", "road_safety")
        ]

        self.filter_buttons = {}
        for label, cat_val in cats:
            btn = tk.Button(
                fbar,
                text=label,
                bg=Theme.ACCENT_BLUE if cat_val == "ALL" else "#334155",
                fg="#000000" if cat_val == "ALL" else Theme.TEXT_PRIMARY,
                font=Theme.FONT_SMALL,
                relief="flat",
                padx=8,
                command=lambda c=cat_val: self._set_category(c)
            )
            btn.pack(side=tk.LEFT, padx=3)
            self.filter_buttons[cat_val] = btn

    def _build_grid(self):
        container = tk.Frame(self, bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1)
        container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(container, bg=Theme.BG_CARD, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.grid_frame = tk.Frame(self.canvas, bg=Theme.BG_CARD)

        self.grid_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.bind("<Configure>", self._on_resize)
        self.refresh_gallery()

    def _on_resize(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width - 24)

    def _set_category(self, cat: str):
        self.active_category = cat
        for cval, btn in self.filter_buttons.items():
            is_active = (cval == cat)
            btn.config(
                bg=Theme.ACCENT_BLUE if is_active else "#334155",
                fg="#000000" if is_active else Theme.TEXT_PRIMARY
            )
        self.refresh_gallery()

    def refresh_gallery(self):
        """Scans evidence directory and renders thumbnail grid."""
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self._thumb_cache.clear()

        items = self.controller.evidence_manager.get_all_evidence()
        if self.active_category != "ALL":
            items = [it for it in items if it["category"] == self.active_category]

        if not items:
            lbl = tk.Label(
                self.grid_frame,
                text="No evidence files found in this category.\nNew snapshots and clips will appear here when violations or incidents occur.",
                bg=Theme.BG_CARD,
                fg=Theme.TEXT_MUTED,
                font=Theme.FONT_BODY,
                pady=40
            )
            lbl.pack(fill=tk.BOTH, expand=True)
            return

        # Render responsive grid (columns = 4)
        cols = 4
        for idx, it in enumerate(items):
            row_idx = idx // cols
            col_idx = idx % cols
            card = self._create_thumbnail_card(it)
            card.grid(row=row_idx, column=col_idx, padx=8, pady=8, sticky="nsew")

        for c in range(cols):
            self.grid_frame.columnconfigure(c, weight=1)

    def _create_thumbnail_card(self, item_info: dict) -> tk.Frame:
        """Creates an individual thumbnail card widget."""
        card = tk.Frame(
            self.grid_frame,
            bg="#111827",
            highlightbackground=Theme.BORDER,
            highlightthickness=1,
            padx=6,
            pady=6,
            cursor="hand2"
        )

        fpath = item_info["filepath"]
        fname = item_info["filename"]
        is_vid = item_info["is_video"]
        cat = item_info["category"]

        # Category tag
        top_bar = tk.Frame(card, bg="#111827")
        top_bar.pack(fill=tk.X, pady=(0, 4))
        tag = tk.Label(
            top_bar,
            text=f" {cat.upper()} ",
            bg="#1e293b",
            fg=Theme.ACCENT_BLUE,
            font=("Segoe UI", 7, "bold")
        )
        tag.pack(side=tk.LEFT)

        if is_vid:
            tk.Label(top_bar, text="▶ VIDEO CLIP", bg="#dc2626", fg="#ffffff", font=("Segoe UI", 7, "bold")).pack(side=tk.RIGHT)

        # Thumbnail canvas
        img_lbl = tk.Label(card, bg="#050811", height=7, width=22)
        img_lbl.pack(fill=tk.BOTH, expand=True)

        if not is_vid and os.path.exists(fpath):
            try:
                img = Image.open(fpath)
                img.thumbnail((180, 110))
                photo = ImageTk.PhotoImage(img)
                self._thumb_cache.append(photo)
                img_lbl.config(image=photo)
            except Exception:
                img_lbl.config(text="Image File", fg=Theme.TEXT_MUTED)
        else:
            img_lbl.config(text="🎬 MP4 Video Clip\nClick to Play", fg=Theme.TEXT_SECONDARY)

        # File info
        info_lbl = tk.Label(
            card,
            text=f"{fname[:22]}...\n{item_info['size_kb']} KB | {item_info['modified_time'][-8:]}",
            bg="#111827",
            fg=Theme.TEXT_MUTED,
            font=("Segoe UI", 8),
            justify="center"
        )
        info_lbl.pack(pady=(4, 0))

        # Click handler
        for w in (card, top_bar, tag, img_lbl, info_lbl):
            w.bind("<Button-1>", lambda e, it=item_info: self._inspect_evidence(it))

        return card

    def _inspect_evidence(self, item_info: dict):
        """Opens full evidence preview modal or plays video."""
        fpath = item_info["filepath"]
        if not os.path.exists(fpath):
            messagebox.showwarning("File Missing", "The evidence file no longer exists.")
            return

        if item_info["is_video"]:
            os.startfile(os.path.abspath(fpath))
            return

        # Modal preview dialog for images
        dlg = tk.Toplevel(self)
        dlg.title(f"Evidence Inspector - {item_info['filename']}")
        dlg.geometry("740x560")
        dlg.configure(bg=Theme.BG_MAIN)
        dlg.transient(self)
        dlg.grab_set()

        top_info = tk.Frame(dlg, bg=Theme.BG_CARD, padx=12, pady=8)
        top_info.pack(fill=tk.X)
        tk.Label(
            top_info,
            text=f"EVIDENCE: {item_info['filename']}",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_BODY_BOLD
        ).pack(side=tk.LEFT)
        tk.Label(
            top_info,
            text=f"Size: {item_info['size_kb']} KB | Modified: {item_info['modified_time']}",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL
        ).pack(side=tk.RIGHT)

        # Image view
        img_canv = tk.Label(dlg, bg="#050811")
        img_canv.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        try:
            full_img = Image.open(fpath)
            full_img.thumbnail((700, 440))
            dlg_photo = ImageTk.PhotoImage(full_img)
            img_canv.config(image=dlg_photo)
            img_canv.image = dlg_photo  # keep reference
        except Exception as e:
            img_canv.config(text=f"Error displaying image: {e}", fg=Theme.TEXT_MUTED)

        # Bottom buttons
        bbar = tk.Frame(dlg, bg=Theme.BG_MAIN, padx=12, pady=8)
        bbar.pack(fill=tk.X)
        tk.Button(
            bbar,
            text="📂 Open in Windows Photos",
            bg="#0284c7",
            fg="#ffffff",
            font=Theme.FONT_BODY_BOLD,
            relief="flat",
            padx=12,
            command=lambda: os.startfile(os.path.abspath(fpath))
        ).pack(side=tk.LEFT)

        tk.Button(
            bbar,
            text="Close",
            bg="#334155",
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_BODY,
            relief="flat",
            padx=16,
            command=dlg.destroy
        ).pack(side=tk.RIGHT)
