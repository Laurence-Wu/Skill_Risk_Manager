from __future__ import annotations

import customtkinter as ctk

from ui.core.state import AppState
from ui.components import BaseButton, BaseView, FilterDropdown, ProgressCard
from ui.tables import LogPanel


class ScanView(BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(3, weight=1)
        self._rendered_toolbar: tuple[str, str] | None = None
        self.page_header("Scan", "Run local discovery and stage uncertain findings for review.")
        self.toolbar = self.page_toolbar(row=1)

        self.progress_card = ProgressCard(self, "Current Activity")
        self.progress_card.grid(row=2, column=0, sticky="ew", padx=self.theme.spacing("app_padding"), pady=(0, 14))

        self.log_panel = LogPanel(self)
        self.log_panel.grid(row=3, column=0, sticky="nsew", padx=self.theme.spacing("app_padding"), pady=(0, 16))

    def refresh(self, state: AppState) -> None:
        self._render_toolbar(state.scan_status, state.security_level)
        self.progress_card.update_activity(
            state.current_activity,
            state.current_path,
            state.progress,
            state.progress_mode,
            files_checked=state.files_checked,
            expected_total_files=state.expected_total_files,
            directories_checked=state.directories_checked,
            potential_items=state.potential_items,
        )
        self.log_panel.set_logs(state.logs, lazy=state.lazy_updates_enabled)

    def _render_toolbar(self, scan_status: str, selected_level: str) -> None:
        signature = (scan_status, selected_level)
        if self._rendered_toolbar == signature and self.toolbar.left.winfo_children():
            return
        self._rendered_toolbar = signature
        self.toolbar.clear()
        ctk.CTkLabel(
            self.toolbar.left,
            text="Security",
            font=self.theme.font("small"),
            text_color=self.theme.color("text_secondary"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        FilterDropdown(
            self.toolbar.left,
            ["Base", "Advanced"],
            selected=selected_level.title(),
            command=lambda value: self.actions["set_security_level"](value.lower()),
            width=120,
        ).grid(row=0, column=1, sticky="w")
        for column, (label, action_key, variant) in enumerate(scan_toolbar_actions_for_status(scan_status)):
            BaseButton(
                self.toolbar.right,
                label,
                self.actions[action_key],
                variant=variant,
                width=98,
            ).grid(row=0, column=column, padx=(0 if column == 0 else 8, 0))


def scan_toolbar_actions_for_status(scan_status: str) -> tuple[tuple[str, str, str], ...]:
    if scan_status == "scanning":
        return (("Pause", "pause_scan", "secondary"), ("Cancel", "cancel_scan", "danger"))
    if scan_status == "paused":
        return (("Resume", "resume_scan", "primary"), ("Cancel", "cancel_scan", "danger"))
    return (("Start Scan", "start_scan", "primary"),)
