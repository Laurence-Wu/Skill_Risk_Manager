from __future__ import annotations

from ui.core.table_rows import RISK_LEVEL_FILTERS, candidate_rows_for_bucket, filter_rows
from ui.core.state import AppState
from ui.components import BaseButton, BaseView, ConfirmDialog, FilterDropdown, SearchBox
from ui.table_page import TableDetailMixin


class CandidatesView(TableDetailMixin, BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(2, weight=1)
        self._state: AppState | None = None
        self.selected_bucket = "snapshot"
        self._selected_row: dict[str, object] | None = None
        self.page_header("Candidates", "Review uncertain findings before promoting them into the committed snapshot.")
        self.toolbar = self.page_toolbar(row=1)
        self._build_toolbar()

        self.build_table_detail_area(
            row=2,
            columns=["Name", "Confidence", "Risk", "Reason", "Source", "Path"],
            empty_text="No candidates in this list.",
            detail_title="Candidate Detail",
        )

    def refresh(self, state: AppState) -> None:
        self._state = state
        rows = filter_rows(
            candidate_rows_for_bucket(state, self.selected_bucket),
            query=self.search.value(),
            search_keys=("Name", "Risk", "Reason", "Source", "Path"),
            exact_filters=(("Risk", self.risk_filter.get(), "All Risks"),),
        )
        self.set_table_rows(rows, state, page_size=80)

    def _build_toolbar(self) -> None:
        self.search = SearchBox(self.toolbar.left, command=self._refresh_from_controls)
        self.search.grid(row=0, column=0, padx=(0, 8))
        self.bucket_filter = FilterDropdown(
            self.toolbar.left,
            ["Snapshot", "Staged", "Ignored"],
            selected="Snapshot",
            command=self._select_bucket,
            width=120,
        )
        self.bucket_filter.grid(row=0, column=1, padx=(0, 8))
        self.risk_filter = FilterDropdown(
            self.toolbar.left,
            RISK_LEVEL_FILTERS,
            command=lambda _value: self._refresh_from_controls(),
            width=120,
        )
        self.risk_filter.grid(row=0, column=2)
        BaseButton(self.toolbar.right, "Refresh", self.actions["refresh"], width=92).grid(row=0, column=0, padx=(0, 8))
        BaseButton(self.toolbar.right, "Review Selected", self._review_selected, variant="primary", width=132).grid(row=0, column=1)

    def _select_bucket(self, value: str) -> None:
        self.selected_bucket = value.lower()
        self._selected_row = None
        if self._state:
            self.refresh(self._state)

    def _refresh_from_controls(self) -> None:
        if self._state:
            self.refresh(self._state)

    def _review_selected(self) -> None:
        if self._selected_row:
            self._show_detail(self._selected_row)
            return
        self.clear_detail("Select a candidate row first.")

    def _show_detail(self, row: dict[str, object]) -> None:
        self._selected_row = row
        actions = [
            ("Open Folder", lambda: self._open_folder(row), "secondary"),
            ("Copy Path", lambda: self._copy_path(row), "secondary"),
        ]
        if self.selected_bucket != "ignored":
            actions = [
                ("Promote", lambda: self._promote(row), "primary"),
                ("Ignore", lambda: self._confirm_ignore(row), "danger"),
                *actions,
            ]
        self.set_detail(str(row.get("Name", "Candidate")), self._detail_text(row), actions)

    def _detail_text(self, row: dict[str, object]) -> str:
        record = row.get("_record")
        return "\n".join(
            [
                f"Path: {row.get('Path', '')}",
                f"Confidence: {row.get('Confidence', '')}",
                f"Risk: {row.get('Risk', '')} ({row.get('Score', 0)})",
                f"Action: {row.get('Action', '')}",
                f"Source: {row.get('Source', '')}",
                f"Suggested type: {row.get('Suggested Type', '')}",
                "",
                f"Reason: {row.get('Reason', '')}",
                f"Finding: {row.get('Top Finding', '')}",
                f"Categories: {', '.join(getattr(record, 'risk_categories', ())) or 'none'}",
            ]
        )

    def _promote(self, row: dict[str, object]) -> None:
        record = row.get("_record")
        if record:
            self.actions["promote_candidate"](record)

    def _confirm_ignore(self, row: dict[str, object]) -> None:
        ConfirmDialog(self, "Ignore Candidate", "Move this candidate to the ignored list?", lambda: self._ignore(row))

    def _ignore(self, row: dict[str, object]) -> None:
        record = row.get("_record")
        if record:
            self.actions["ignore_candidate"](record)
