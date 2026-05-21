from __future__ import annotations

import customtkinter as ctk

from manager_GUI.core.state import AppState
from manager_GUI.ui.components import BaseTable, BaseView


class SkillsView(BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(2, weight=1)
        self.page_header("Skills", "Stable records loaded from the committed snapshot.")
        self.table = BaseTable(
            self,
            ["Name", "Scope", "Type", "Path", "Confidence", "Status"],
            empty_text="Skills will appear after a scan result is committed.",
        )
        self.table.grid(row=2, column=0, sticky="nsew", padx=self.theme.spacing("app_padding"), pady=(0, 16))

    def refresh(self, state: AppState) -> None:
        rows = [record.to_row() for record in state.confirmed_skills]
        self.table.set_rows(
            rows,
            [
                ("Open Detail", self._show_detail, "secondary"),
                ("Copy Path", self._copy_path, "secondary"),
                ("Open Folder", self._open_folder, "secondary"),
            ],
        )

    def _show_detail(self, row: dict[str, object]) -> None:
        record = row.get("_record")
        detail_window = ctk.CTkToplevel(self)
        detail_window.title("Skill Detail")
        detail_window.geometry("560x360")
        detail_window.configure(fg_color=self.theme.color("app_bg"))
        detail_window.grid_rowconfigure(0, weight=1)
        detail_window.grid_columnconfigure(0, weight=1)
        text = "No detail available." if record is None else self._detail_text(record)
        textbox = ctk.CTkTextbox(
            detail_window,
            fg_color=self.theme.color("surface"),
            border_color=self.theme.color("border"),
            border_width=1,
            text_color=self.theme.color("text_secondary"),
            font=self.theme.font("small"),
            wrap="word",
        )
        textbox.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        textbox.insert("1.0", text)
        textbox.configure(state="disabled")

    def _detail_text(self, record: object) -> str:
        return "\n".join(
            [
                f"Name: {getattr(record, 'name', '')}",
                f"Scope: {getattr(record, 'scope', '')}",
                f"Type: {getattr(record, 'record_type', '')}",
                f"Confidence: {getattr(record, 'confidence', 0):.2f}",
                f"Status: {getattr(record, 'status', '')}",
                "",
                f"Path: {getattr(record, 'path', '')}",
                "",
                f"Description: {getattr(record, 'description', '') or 'No description available.'}",
            ]
        )

    def _copy_path(self, row: dict[str, object]) -> None:
        self.actions["copy_path"](str(row.get("Path", "")))

    def _open_folder(self, row: dict[str, object]) -> None:
        self.actions["open_folder"](str(row.get("Path", "")))
