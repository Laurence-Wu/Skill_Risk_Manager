from __future__ import annotations

import customtkinter as ctk
from pathlib import Path

from manager_GUI.core.state import AppState
from manager_GUI.ui.components import BaseButton, BaseView, DetailPanel, FilterDropdown, SearchBox
from manager_GUI.ui.tables import BaseTable


RISK_CATEGORIES = [
    "All Categories",
    "tool_access",
    "filesystem",
    "network",
    "command_execution",
    "secrets",
    "mcp",
    "hooks",
    "prompt_injection",
    "persistence",
    "uncertainty",
]


class RiskView(BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(2, weight=1)
        self._state: AppState | None = None
        self._selected_row: dict[str, object] | None = None
        self.page_header("Risk", "Review skill capabilities and potentially dangerous behavior.")
        self.toolbar = self.page_toolbar(row=1)
        self._build_toolbar()

        split = ctk.CTkFrame(self, fg_color="transparent")
        split.grid(row=2, column=0, sticky="nsew", padx=self.theme.spacing("app_padding"), pady=(0, 16))
        split.grid_columnconfigure(0, weight=1)
        split.grid_rowconfigure(0, weight=1)
        self.table = BaseTable(
            split,
            ["Record", "Score", "Level", "Category", "Top Finding", "Path"],
            empty_text="Risk findings will appear after scan results are available.",
        )
        self.table.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.detail = DetailPanel(split, "Risk Detail")
        self.detail.grid(row=0, column=1, sticky="nsew")

    def refresh(self, state: AppState) -> None:
        self._state = state
        rows = [row for row in risk_rows_from_state(state) if self._matches_filters(row)]
        self.table.set_rows(
            rows,
            [
                ("View", self._show_detail, "quiet"),
                ("Open", self._open_folder, "quiet"),
                ("Copy", self._copy_path, "quiet"),
            ],
            page_size=90,
            lazy=state.lazy_updates_enabled,
        )

    def _build_toolbar(self) -> None:
        self.search = SearchBox(self.toolbar.left, command=self._refresh_from_controls)
        self.search.grid(row=0, column=0, padx=(0, 8))
        self.level_filter = FilterDropdown(
            self.toolbar.left,
            ["All Levels", "Critical", "High", "Medium", "Low"],
            command=lambda _value: self._refresh_from_controls(),
            width=120,
        )
        self.level_filter.grid(row=0, column=1, padx=(0, 8))
        self.category_filter = FilterDropdown(
            self.toolbar.left,
            RISK_CATEGORIES,
            command=lambda _value: self._refresh_from_controls(),
            width=160,
        )
        self.category_filter.grid(row=0, column=2)
        BaseButton(self.toolbar.right, "Refresh", self.actions["refresh"], width=92).grid(row=0, column=0, padx=(0, 8))
        BaseButton(
            self.toolbar.right,
            "Export Risk Report",
            self.actions["export_risk_report"],
            variant="primary",
            width=154,
        ).grid(row=0, column=1)

    def _refresh_from_controls(self) -> None:
        if self._state:
            self.refresh(self._state)

    def _matches_filters(self, row: dict[str, object]) -> bool:
        query = self.search.value().lower()
        searchable = " ".join(str(row.get(key, "")) for key in ["Record", "Level", "Category", "Top Finding", "Path"]).lower()
        if query and query not in searchable:
            return False
        level = self.level_filter.get()
        if level != "All Levels" and str(row.get("Level", "")).lower() != level.lower():
            return False
        category = self.category_filter.get()
        if category != "All Categories" and category not in str(row.get("Category", "")):
            return False
        return True

    def _show_detail(self, row: dict[str, object]) -> None:
        self._selected_row = row
        self.detail.set_content(
            str(row.get("Record", "Risk")),
            self._detail_text(row),
            [
                ("Copy Path", lambda: self._copy_path(row), "secondary"),
                ("Open Folder", lambda: self._open_folder(row), "secondary"),
            ],
        )

    def _detail_text(self, row: dict[str, object]) -> str:
        record = row.get("_record")
        return "\n".join(
            [
                f"Level: {row.get('Level', '')}",
                f"Score: {row.get('Score', '')}",
                f"Category: {row.get('Category', '')}",
                f"Source: {row.get('Source', '')}",
                "",
                f"Top finding: {row.get('Top Finding', '')}",
                f"Summary: {getattr(record, 'risk_summary', '')}",
                "",
                f"Path: {row.get('Path', '')}",
            ]
        )

    def _copy_path(self, row: dict[str, object]) -> None:
        self.actions["copy_path"](str(row.get("Path", "")))

    def _open_folder(self, row: dict[str, object]) -> None:
        self.actions["open_folder"](str(row.get("Path", "")))


def risk_rows_from_state(state: AppState) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record, source in [
        *[(record, "Skills") for record in state.confirmed_skills],
        *[(record, "Snapshot") for record in state.candidates_snapshot],
        *[(record, "Staged") for record in state.candidates_staged],
    ]:
        categories = tuple(getattr(record, "risk_categories", ()))
        row = {
            "Record": getattr(record, "name", "") or _record_name_from_path(getattr(record, "path", "")),
            "Score": getattr(record, "risk_score", 0),
            "Level": str(getattr(record, "risk_level", "low")).title(),
            "Category": ", ".join(categories) or "none",
            "Top Finding": getattr(record, "top_finding", "") or getattr(record, "risk_summary", ""),
            "Path": getattr(record, "path", ""),
            "Source": source,
            "_record": record,
            "_row_kind": getattr(record, "risk_level", "low"),
        }
        rows.append(row)
    return rows


def _record_name_from_path(path_text: str) -> str:
    path = Path(path_text)
    if path.name.lower() == "skill.md" and path.parent.name:
        return path.parent.name
    return path.stem or path.name or path_text
