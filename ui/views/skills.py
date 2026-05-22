from __future__ import annotations

from ui.core.table_rows import RISK_LEVEL_FILTERS, filter_rows, ranked_skill_rows
from ui.core.state import AppState
from ui.components import BaseButton, BaseView, FilterDropdown, SearchBox
from ui.table_page import TableDetailMixin


class SkillsView(TableDetailMixin, BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(2, weight=1)
        self._state: AppState | None = None
        self._selected_record = None
        self.page_header("Skills", "Stable records loaded from the committed snapshot.")
        self.toolbar = self.page_toolbar(row=1)
        self._build_toolbar()

        self.build_table_detail_area(
            row=2,
            columns=["Name", "Type", "Scope", "Confidence", "Risk", "Path"],
            empty_text="Skills will appear after a scan result is committed.",
            detail_title="Skill Detail",
        )

    def refresh(self, state: AppState) -> None:
        self._state = state
        rows = filter_rows(
            ranked_skill_rows(state.confirmed_skills),
            query=self.search.value(),
            search_keys=("Name", "Type", "Scope", "Risk", "Path"),
            exact_filters=(("Risk", self.risk_filter.get(), "All Risks"),),
            contains_filters=(("Scope", self.scope_filter.get(), "All Scopes"),),
        )
        self.set_table_rows(rows, state, page_size=90)

    def _build_toolbar(self) -> None:
        self.search = SearchBox(self.toolbar.left, command=self._refresh_from_controls)
        self.search.grid(row=0, column=0, padx=(0, 8))
        self.risk_filter = FilterDropdown(
            self.toolbar.left,
            RISK_LEVEL_FILTERS,
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

    def _show_detail(self, row: dict[str, object]) -> None:
        record = row.get("_record")
        self._selected_record = record
        self.set_detail(
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
