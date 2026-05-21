from __future__ import annotations

import customtkinter as ctk

from skill_manager.ui.components.progress_panel import ProgressPanel


class ShadowScanPage(ctk.CTkFrame):
    def __init__(self, master, on_pause, on_resume, on_cancel, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.panel = ProgressPanel(self, "Shadow Scan")
        self.panel.grid(row=0, column=0, sticky="ew", padx=18, pady=18)
        metrics = [
            ("status", "Status"),
            ("formatted_path", "Current path"),
            ("files_checked", "Shadow files checked"),
            ("directories_checked", "Shadow directories checked"),
            ("candidates_found", "Additional candidates"),
            ("confirmed_found", "Additional skills"),
        ]
        for row_index, (key, label) in enumerate(metrics, start=2):
            self.panel.add_metric(key, label, row_index)
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=1, column=0, sticky="w", padx=18, pady=8)
        ctk.CTkButton(button_frame, text="Pause", command=on_pause).grid(row=0, column=0, padx=6, pady=8)
        ctk.CTkButton(button_frame, text="Resume", command=on_resume).grid(row=0, column=1, padx=6, pady=8)
        ctk.CTkButton(button_frame, text="Cancel Shadow Scan", command=on_cancel).grid(row=0, column=2, padx=6, pady=8)

    def set_status(self, status: str) -> None:
        self.panel.update_metric("status", status)

    def update_progress(self, payload: dict) -> None:
        for key, value in payload.items():
            self.panel.update_metric(key, value)

