from __future__ import annotations

import customtkinter as ctk

from skill_manager.ui.components.progress_panel import ProgressPanel


class FastScanPage(ctk.CTkFrame):
    def __init__(self, master, on_cancel_fast, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.panel = ProgressPanel(self, "Fast Scan")
        self.panel.grid(row=0, column=0, sticky="ew", padx=18, pady=18)
        metrics = [
            ("current_phase", "Current phase"),
            ("formatted_path", "Current path"),
            ("directories_checked", "Directories checked"),
            ("files_checked", "Files checked"),
            ("potential_found", "Potential skills found"),
            ("errors", "Errors"),
        ]
        for row_index, (key, label) in enumerate(metrics, start=2):
            self.panel.add_metric(key, label, row_index)
        ctk.CTkButton(self, text="Cancel Fast Scan", command=on_cancel_fast).grid(row=1, column=0, sticky="w", padx=18, pady=8)

    def mark_running(self) -> None:
        self.panel.set_indeterminate()

    def update_progress(self, payload: dict) -> None:
        for key, value in payload.items():
            self.panel.update_metric(key, value)

    def mark_complete(self) -> None:
        self.panel.set_complete()
        self.panel.update_metric("current_phase", "Fast scan complete")

