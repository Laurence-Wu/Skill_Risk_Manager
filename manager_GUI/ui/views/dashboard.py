from __future__ import annotations

from manager_GUI.core.state import AppState
from manager_GUI.ui.components import BaseButton, BaseView, MetricCard, ProgressCard, StatusBadge, status_kind


class DashboardView(BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(4, weight=1)
        self.page_header("Dashboard", "Stable overview of local Claude Code skill records.")

        self.metrics = self._build_metric_row()
        self.status_card = ProgressCard(self, "Scan Status")
        self.status_card.grid(row=3, column=0, sticky="ew", padx=self.theme.spacing("app_padding"), pady=(0, 14))

        action_row = self._action_row()
        action_row.grid(row=4, column=0, sticky="nw", padx=self.theme.spacing("app_padding"), pady=(0, 16))

    def refresh(self, state: AppState) -> None:
        self.metrics["skills"].set_value(state.confirmed_count)
        self.metrics["candidates"].set_value(state.candidate_count)
        self.metrics["commands"].set_value(state.command_count)
        self.metrics["config"].set_value(state.config_count)
        self.status_badge.set_status(state.scan_status.title(), status_kind(state.scan_status))
        self.status_card.update_activity(
            state.current_activity,
            state.current_path,
            state.progress,
            state.progress_mode,
            files_checked=state.files_checked,
            expected_total_files=state.expected_total_files,
            directories_checked=state.directories_checked,
            potential_items=state.potential_items,
        )

    def _build_metric_row(self) -> dict[str, MetricCard]:
        metric_row = self._transparent_row()
        metric_row.grid(row=2, column=0, sticky="ew", padx=self.theme.spacing("app_padding"), pady=(0, 14))
        for column in range(4):
            metric_row.grid_columnconfigure(column, weight=1, uniform="metrics")
        cards = {
            "skills": MetricCard(metric_row, "Confirmed Skills"),
            "candidates": MetricCard(metric_row, "Candidates"),
            "commands": MetricCard(metric_row, "Commands"),
            "config": MetricCard(metric_row, "Config Files"),
        }
        for column, card in enumerate(cards.values()):
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
        return cards

    def _action_row(self):
        row = self._transparent_row()
        self.status_badge = StatusBadge(row, "Ready", "ready")
        BaseButton(row, "Run Scan", self.actions["start_scan"], variant="primary", width=110).grid(row=0, column=0, padx=(0, 8))
        BaseButton(row, "View Skills", lambda: self.actions["show_view"]("skills"), width=110).grid(row=0, column=1, padx=(0, 8))
        BaseButton(row, "Review Candidates", lambda: self.actions["show_view"]("candidates"), width=140).grid(row=0, column=2, padx=(0, 8))
        BaseButton(row, "Open Config", lambda: self.actions["show_view"]("config"), width=110).grid(row=0, column=3, padx=(0, 8))
        self.status_badge.grid(row=0, column=4, padx=(8, 0))
        return row

    def _transparent_row(self):
        import customtkinter as ctk

        return ctk.CTkFrame(self, fg_color="transparent")
