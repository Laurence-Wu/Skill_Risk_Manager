from __future__ import annotations

from datetime import datetime

import customtkinter as ctk

from manager_GUI.core.state import AppState
from manager_GUI.models import LogEntry
from manager_GUI.ui.components import BaseButton, BaseView, ConfirmDialog, DetailPanel, FilterDropdown
from manager_GUI.ui.tables import BaseTable


class LogsView(BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(2, weight=1)
        self.level_filter = "all"
        self._state: AppState | None = None
        self.page_header("Logs", "Operational events from the current session.")
        self.toolbar = self.page_toolbar(row=1)
        self._build_toolbar()

        split = ctk.CTkFrame(self, fg_color="transparent")
        split.grid(row=2, column=0, sticky="nsew", padx=self.theme.spacing("app_padding"), pady=(0, 16))
        split.grid_columnconfigure(0, weight=1)
        split.grid_rowconfigure(0, weight=1)
        self.table = BaseTable(
            split,
            ["Time", "Level", "Event", "Message", "Path"],
            empty_text="No events yet.",
        )
        self.table.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.detail = DetailPanel(split, "Log Detail")
        self.detail.grid(row=0, column=1, sticky="nsew")

    def refresh(self, state: AppState) -> None:
        self._state = state
        rows = [log_to_row(log) for log in state.logs if self.level_filter == "all" or log.level == self.level_filter]
        self.table.set_rows(
            rows,
            [("View", self._show_detail, "quiet")],
            page_size=120,
            lazy=state.lazy_updates_enabled,
        )

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
        self.detail.set_content(
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


def log_to_row(log: LogEntry) -> dict[str, object]:
    return {
        "Time": datetime.fromtimestamp(log.timestamp).strftime("%H:%M:%S"),
        "Level": log.level.title(),
        "Event": log.event_type,
        "Message": log.message,
        "Path": _path_from_message(log.message),
        "_record": log,
        "_row_kind": log.level,
    }


def _path_from_message(message: str) -> str:
    for marker in [" path: ", "folder: ", "logs: ", "skills: ", "risk report: ", ": "]:
        if marker in message.lower():
            candidate = message.split(":", 1)[-1].strip()
            if "\\" in candidate or "/" in candidate:
                return candidate
    return ""
