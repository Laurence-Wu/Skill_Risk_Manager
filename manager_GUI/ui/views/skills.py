from __future__ import annotations

import customtkinter as ctk

from manager_GUI.core.state import AppState
from manager_GUI.ui.components import BaseButton, BaseView, DetailPanel, FilterDropdown, SearchBox
from manager_GUI.ui.tables import BaseTable


class SkillsView(BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(2, weight=1)
        self._state: AppState | None = None
        self._selected_record = None
        self.page_header("Skills", "Stable records loaded from the committed snapshot.")
        self.toolbar = self.page_toolbar(row=1)
        self._build_toolbar()

        split = ctk.CTkFrame(self, fg_color="transparent")
        split.grid(row=2, column=0, sticky="nsew", padx=self.theme.spacing("app_padding"), pady=(0, 16))
        split.grid_columnconfigure(0, weight=1)
        split.grid_rowconfigure(0, weight=1)
        self.table = BaseTable(
            split,
            ["Name", "Type", "Scope", "Confidence", "Risk", "Path"],
            empty_text="Skills will appear after a scan result is committed.",
        )
        self.table.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.detail = DetailPanel(split, "Skill Detail")
        self.detail.grid(row=0, column=1, sticky="nsew")

    def refresh(self, state: AppState) -> None:
        self._state = state
        rows = ranked_skill_rows(state.confirmed_skills)
        rows = [row for row in rows if self._matches_filters(row)]
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
        self.risk_filter = FilterDropdown(
            self.toolbar.left,
            ["All Risks", "Critical", "High", "Medium", "Low"],
            command=lambda _value: self._refresh_from_controls(),
            width=120,
        )
        self.risk_filter.grid(row=0, column=1, padx=(0, 8))
        self.scope_filter = FilterDropdown(
            self.toolbar.left,
            ["All Scopes", "Personal", "Project", "Plugin"],
            command=lambda _value: self._refresh_from_controls(),
            width=130,
        )
        self.scope_filter.grid(row=0, column=2)
        BaseButton(self.toolbar.right, "Refresh", self.actions["refresh"], width=92).grid(row=0, column=0, padx=(0, 8))
        BaseButton(self.toolbar.right, "Export Skills", self.actions["export_skills"], variant="primary", width=124).grid(row=0, column=1)

    def _refresh_from_controls(self) -> None:
        if self._state:
            self.refresh(self._state)

    def _matches_filters(self, row: dict[str, object]) -> bool:
        query = self.search.value().lower()
        searchable = " ".join(str(row.get(key, "")) for key in ["Name", "Type", "Scope", "Risk", "Path"]).lower()
        if query and query not in searchable:
            return False
        risk = self.risk_filter.get()
        if risk != "All Risks" and str(row.get("Risk", "")).lower() != risk.lower():
            return False
        scope = self.scope_filter.get()
        if scope != "All Scopes" and scope.lower() not in str(row.get("Scope", "")).lower():
            return False
        return True

    def _show_detail(self, row: dict[str, object]) -> None:
        record = row.get("_record")
        self._selected_record = record
        self.detail.set_content(
            str(row.get("Name", "Skill")),
            self._detail_text(record),
            [
                ("Copy Path", lambda: self._copy_path(row), "secondary"),
                ("Open Folder", lambda: self._open_folder(row), "secondary"),
            ],
        )

    def _detail_text(self, record: object) -> str:
        if record is None:
            return "No detail available."
        return "\n".join(
            [
                f"Name: {getattr(record, 'name', '')}",
                f"Scope: {getattr(record, 'scope', '')}",
                f"Type: {getattr(record, 'record_type', '')}",
                f"Confidence: {getattr(record, 'confidence', 0):.2f}",
                f"Status: {getattr(record, 'status', '')}",
                f"Risk: {getattr(record, 'risk_level', '').title()} ({getattr(record, 'risk_score', 0)})",
                f"Risk summary: {getattr(record, 'risk_summary', '')}",
                f"Risk categories: {', '.join(getattr(record, 'risk_categories', ())) or 'none'}",
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


def ranked_skill_rows(records: list) -> list[dict[str, object]]:
    return sorted((record.to_row() for record in records), key=_skill_rank_key)


def _skill_rank_key(row: dict[str, object]) -> tuple[int, int, str]:
    return (-_int_value(row.get("Score", 0)), -_risk_rank(str(row.get("Risk", ""))), str(row.get("Name", "")).lower())


def _risk_rank(level: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(level.lower(), 0)


def _int_value(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
