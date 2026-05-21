from __future__ import annotations

import customtkinter as ctk

from skill_manager.backend.models import SkillRecord
from skill_manager.platform.base import PlatformAdapter


class SkillTable(ctk.CTkScrollableFrame):
    def __init__(self, master, adapter: PlatformAdapter, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.adapter = adapter
        for column_index in range(9):
            self.grid_columnconfigure(column_index, weight=1 if column_index in {0, 3} else 0)
        self._render_headers()

    def set_records(self, records: list[SkillRecord]) -> None:
        for child in self.winfo_children():
            child.destroy()
        self._render_headers()
        if not records:
            empty_label = ctk.CTkLabel(self, text="No records to display.")
            empty_label.grid(row=1, column=0, columnspan=9, sticky="w", padx=8, pady=10)
            return

        for row_index, record in enumerate(records, start=1):
            values = [
                record.name,
                record.scope,
                record.record_type,
                self.adapter.format_path(record.path),
                f"{record.confidence:.2f}",
                _format_timestamp(record.last_modified),
                record.status,
            ]
            for column_index, value in enumerate(values):
                label = ctk.CTkLabel(self, text=value, anchor="w")
                label.grid(row=row_index, column=column_index, sticky="ew", padx=8, pady=3)
            open_button = ctk.CTkButton(
                self,
                text="Open Folder",
                width=96,
                command=lambda selected_record=record: self.adapter.open_folder(selected_record.path),
            )
            open_button.grid(row=row_index, column=7, sticky="ew", padx=8, pady=3)
            copy_button = ctk.CTkButton(
                self,
                text="Copy Path",
                width=82,
                command=lambda selected_record=record: self._copy_path(selected_record),
            )
            copy_button.grid(row=row_index, column=8, sticky="ew", padx=8, pady=3)

    def _render_headers(self) -> None:
        headers = ["Name", "Scope", "Type", "Path", "Confidence", "Last Modified", "Status", "", ""]
        for column_index, header in enumerate(headers):
            label = ctk.CTkLabel(self, text=header, font=ctk.CTkFont(weight="bold"), anchor="w")
            label.grid(row=0, column=column_index, sticky="ew", padx=8, pady=(8, 6))

    def _copy_path(self, record: SkillRecord) -> None:
        self.clipboard_clear()
        self.clipboard_append(str(record.path))


def _format_timestamp(timestamp: float) -> str:
    if not timestamp:
        return "—"
    from datetime import datetime

    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
