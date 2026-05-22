from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ui.core.state import AppState
from ui.components import DetailPanel
from ui.tables import BaseTable, TableAction


class TableDetailMixin:
    table: BaseTable
    detail: DetailPanel
    actions: dict[str, Callable]

    def build_table_detail_area(
        self,
        *,
        row: int,
        columns: list[str],
        empty_text: str,
        detail_title: str,
    ) -> None:
        split = ctk.CTkFrame(self, fg_color="transparent")
        split.grid(row=row, column=0, sticky="nsew", padx=self.theme.spacing("app_padding"), pady=(0, 16))
        split.grid_columnconfigure(0, weight=1)
        split.grid_rowconfigure(0, weight=1)
        self.table = BaseTable(split, columns, empty_text=empty_text)
        self.table.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.detail = DetailPanel(split, detail_title)
        self.detail.grid(row=0, column=1, sticky="nsew")

    def set_table_rows(
        self,
        rows: list[dict[str, object]],
        state: AppState,
        *,
        actions: list[TableAction] | None = None,
        page_size: int = 90,
    ) -> None:
        self.table.set_rows(rows, actions or self.standard_row_actions(), page_size=page_size, lazy=state.lazy_updates_enabled)

    def standard_row_actions(self) -> list[TableAction]:
        return [
            ("View", self._show_detail, "quiet"),
            ("Open", self._open_folder, "quiet"),
            ("Copy", self._copy_path, "quiet"),
        ]

    def set_detail(
        self,
        title: str,
        body: str,
        actions: list[tuple[str, Callable[[], None], str]] | None = None,
    ) -> None:
        self.detail.set_content(title, body, actions or [])

    def clear_detail(self, message: str = "Select a row to view details.") -> None:
        self.detail.set_content("No selection", message, [])

    def _copy_path(self, row: dict[str, object]) -> None:
        self.actions["copy_path"](str(row.get("Path", "")))

    def _open_folder(self, row: dict[str, object]) -> None:
        self.actions["open_folder"](str(row.get("Path", "")))
