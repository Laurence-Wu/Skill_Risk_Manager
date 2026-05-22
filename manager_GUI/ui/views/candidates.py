from __future__ import annotations

import customtkinter as ctk

from manager_GUI.core.state import AppState
from manager_GUI.ui.components import BaseButton, BaseView, ConfirmDialog, DetailPanel, FilterDropdown, SearchBox
from manager_GUI.ui.tables import BaseTable


class CandidatesView(BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(2, weight=1)
        self._state: AppState | None = None
        self.selected_bucket = "snapshot"
        self._selected_row: dict[str, object] | None = None
        self.page_header("Candidates", "Review uncertain findings before promoting them into the committed snapshot.")
        self.toolbar = self.page_toolbar(row=1)
        self._build_toolbar()

        split = ctk.CTkFrame(self, fg_color="transparent")
        split.grid(row=2, column=0, sticky="nsew", padx=self.theme.spacing("app_padding"), pady=(0, 16))
        split.grid_columnconfigure(0, weight=1)
        split.grid_rowconfigure(0, weight=1)
        self.table = BaseTable(
            split,
            ["Name", "Confidence", "Risk", "Reason", "Source", "Path"],
            empty_text="No candidates in this list.",
        )
        self.table.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.detail = DetailPanel(split, "Candidate Detail")
        self.detail.grid(row=0, column=1, sticky="nsew")

    def refresh(self, state: AppState) -> None:
        self._state = state
        rows = [record.to_row() for record in self._records_for_bucket(state)]
        rows = [row for row in rows if self._matches_filters(row)]
        self.table.set_rows(
            rows,
            [
                ("View", self._show_detail, "quiet"),
                ("Open", self._open_folder, "quiet"),
                ("Copy", self._copy_path, "quiet"),
            ],
            page_size=80,
            lazy=state.lazy_updates_enabled,
        )

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
            ["All Risks", "Critical", "High", "Medium", "Low"],
            command=lambda _value: self._refresh_from_controls(),
            width=120,
        )
        self.risk_filter.grid(row=0, column=2)
        BaseButton(self.toolbar.right, "Refresh", self.actions["refresh"], width=92).grid(row=0, column=0, padx=(0, 8))
        BaseButton(self.toolbar.right, "Review Selected", self._review_selected, variant="primary", width=132).grid(row=0, column=1)

    def _records_for_bucket(self, state: AppState) -> list:
        if self.selected_bucket == "staged":
            return list(reversed(state.candidates_staged))
        if self.selected_bucket == "ignored":
            return state.ignored_candidates
        return state.candidates_snapshot

    def _select_bucket(self, value: str) -> None:
        self.selected_bucket = value.lower()
        self._selected_row = None
        if self._state:
            self.refresh(self._state)

    def _refresh_from_controls(self) -> None:
        if self._state:
            self.refresh(self._state)

    def _matches_filters(self, row: dict[str, object]) -> bool:
        query = self.search.value().lower()
        searchable = " ".join(str(row.get(key, "")) for key in ["Name", "Risk", "Reason", "Source", "Path"]).lower()
        if query and query not in searchable:
            return False
        risk = self.risk_filter.get()
        if risk != "All Risks" and str(row.get("Risk", "")).lower() != risk.lower():
            return False
        return True

    def _review_selected(self) -> None:
        if self._selected_row:
            self._show_detail(self._selected_row)
            return
        self.detail.set_content("No selection", "Select a candidate row first.", [])

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
        self.detail.set_content(str(row.get("Name", "Candidate")), self._detail_text(row), actions)

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

    def _copy_path(self, row: dict[str, object]) -> None:
        self.actions["copy_path"](str(row.get("Path", "")))

    def _open_folder(self, row: dict[str, object]) -> None:
        self.actions["open_folder"](str(row.get("Path", "")))
