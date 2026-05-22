from __future__ import annotations

from ui.core.table_rows import RISK_CATEGORIES, RISK_LEVEL_VIEW_FILTERS, filter_rows, risk_rows_from_state
from ui.core.state import AppState
from ui.components import BaseButton, BaseView, FilterDropdown, SearchBox
from ui.table_page import TableDetailMixin


class RiskView(TableDetailMixin, BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(2, weight=1)
        self._state: AppState | None = None
        self._selected_row: dict[str, object] | None = None
        self.page_header("Risk", "Review skill capabilities and potentially dangerous behavior.")
        self.toolbar = self.page_toolbar(row=1)
        self._build_toolbar()

        self.build_table_detail_area(
            row=2,
            columns=["Record", "Score", "Level", "Category", "Top Finding", "Path"],
            empty_text="Risk findings will appear after scan results are available.",
            detail_title="Risk Detail",
        )

    def refresh(self, state: AppState) -> None:
        self._state = state
        rows = filter_rows(
            risk_rows_from_state(state),
            query=self.search.value(),
            search_keys=("Record", "Level", "Category", "Top Finding", "Path"),
            exact_filters=(("Level", self.level_filter.get(), "All Levels"),),
            contains_filters=(("Category", self.category_filter.get(), "All Categories"),),
        )
        self.set_table_rows(rows, state, page_size=90)

    def _build_toolbar(self) -> None:
        self.search = SearchBox(self.toolbar.left, command=self._refresh_from_controls)
        self.search.grid(row=0, column=0, padx=(0, 8))
        self.level_filter = FilterDropdown(
            self.toolbar.left,
            RISK_LEVEL_VIEW_FILTERS,
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

    def _show_detail(self, row: dict[str, object]) -> None:
        self._selected_row = row
        self.set_detail(
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
