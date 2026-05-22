from __future__ import annotations

from ui.core.table_rows import log_rows, log_to_row
from ui.core.state import AppState
from ui.components import BaseButton, BaseView, ConfirmDialog, FilterDropdown
from ui.table_page import TableDetailMixin


class LogsView(TableDetailMixin, BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(2, weight=1)
        self.level_filter = "all"
        self._state: AppState | None = None
        self.page_header("Logs", "Operational events from the current session.")
        self.toolbar = self.page_toolbar(row=1)
        self._build_toolbar()

        self.build_table_detail_area(
            row=2,
            columns=["Time", "Level", "Event", "Message", "Path"],
            empty_text="No events yet.",
            detail_title="Log Detail",
        )

    def refresh(self, state: AppState) -> None:
        self._state = state
        self.set_table_rows(log_rows(state.logs, self.level_filter), state, actions=[("View", self._show_detail, "quiet")], page_size=120)

    def _build_toolbar(self) -> None:
        FilterDropdown(
            self.toolbar.left,
            ["All", "Info", "Warning", "Error"],
            command=self._select_filter,
            width=120,
        ).grid(row=0, column=0)
        BaseButton(self.toolbar.right, "Open Folder", self.actions["open_logs_folder"], width=112).grid(row=0, column=0, padx=(0, 8))
        BaseButton(self.toolbar.right, "Clear", self._confirm_clear, variant="danger", width=86).grid(row=0, column=1, padx=(0, 8))
        BaseButton(self.toolbar.right, "Export Logs", self.actions["export_logs"], variant="primary", width=116).grid(row=0, column=2)

    def _select_filter(self, value: str) -> None:
        self.level_filter = value.lower()
        if self._state:
            self.refresh(self._state)

    def _show_detail(self, row: dict[str, object]) -> None:
        self.set_detail(
            str(row.get("Event", "Log")),
            "\n".join(
                [
                    f"Time: {row.get('Time', '')}",
                    f"Level: {row.get('Level', '')}",
                    f"Event: {row.get('Event', '')}",
                    f"Path: {row.get('Path', '') or 'none'}",
                    "",
                    str(row.get("Message", "")),
                ]
            ),
            [],
        )

    def _confirm_clear(self) -> None:
        ConfirmDialog(self, "Clear Logs", "Clear all session log entries?", self.actions["clear_logs"])
