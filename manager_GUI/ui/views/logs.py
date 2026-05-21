from __future__ import annotations

import customtkinter as ctk

from manager_GUI.core.state import AppState
from manager_GUI.ui.components import BaseButton, BaseView, LogPanel


class LogsView(BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(3, weight=1)
        self.level_filter = "all"
        self.page_header("Logs", "Operational events from the current session.")
        self.filter_row = ctk.CTkFrame(self, fg_color="transparent")
        self.filter_row.grid(row=2, column=0, sticky="ew", padx=self.theme.spacing("app_padding"), pady=(0, 12))
        self._render_filters()
        self.log_panel = LogPanel(self)
        self.log_panel.grid(row=3, column=0, sticky="nsew", padx=self.theme.spacing("app_padding"), pady=(0, 16))
        self._state: AppState | None = None

    def refresh(self, state: AppState) -> None:
        self._state = state
        self.log_panel.set_logs(state.logs, self.level_filter)

    def _render_filters(self) -> None:
        for child in self.filter_row.winfo_children():
            child.destroy()
        for index, level in enumerate(["all", "info", "warning", "error"]):
            BaseButton(
                self.filter_row,
                level.title(),
                command=lambda selected=level: self._select_filter(selected),
                variant="primary" if level == self.level_filter else "secondary",
                width=86,
            ).grid(row=0, column=index, padx=(0 if index == 0 else 6, 0))
        BaseButton(self.filter_row, "Clear", self.actions["clear_logs"], width=86).grid(row=0, column=4, padx=(18, 0))
        BaseButton(self.filter_row, "Export", self.actions["export_logs"], width=86).grid(row=0, column=5, padx=(6, 0))
        BaseButton(self.filter_row, "Open Logs Folder", self.actions["open_logs_folder"], width=140).grid(row=0, column=6, padx=(6, 0))

    def _select_filter(self, level: str) -> None:
        self.level_filter = level
        self._render_filters()
        if self._state:
            self.refresh(self._state)
