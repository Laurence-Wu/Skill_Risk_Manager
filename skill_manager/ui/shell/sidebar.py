from __future__ import annotations

import customtkinter as ctk


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, width: int, on_select, **kwargs) -> None:
        super().__init__(master, width=width, **kwargs)
        self.grid_propagate(False)
        pages = [
            ("Dashboard", "dashboard"),
            ("Fast Scan", "fast_scan"),
            ("Skills", "skills"),
            ("Candidates", "candidates"),
            ("Shadow Scan", "shadow_scan"),
            ("Logs", "logs"),
        ]
        for row_index, (label, page_key) in enumerate(pages):
            button = ctk.CTkButton(self, text=label, anchor="w", command=lambda key=page_key: on_select(key))
            button.grid(row=row_index, column=0, sticky="ew", padx=12, pady=(12 if row_index == 0 else 6, 0))
        self.grid_columnconfigure(0, weight=1)

