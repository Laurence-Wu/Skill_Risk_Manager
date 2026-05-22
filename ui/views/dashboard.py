from __future__ import annotations

from ui.core.state import AppState
from ui.components import BaseButton, BaseCard, BaseView, MetricCard, ProgressCard


class DashboardView(BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(5, weight=1)
        self.page_header("Dashboard", "Stable overview of local Claude Code skill records.")
        self.toolbar = self.page_toolbar(row=1)
        BaseButton(self.toolbar.right, "Review Candidates", lambda: self.actions["show_view"]("candidates"), width=136).grid(row=0, column=0, padx=(0, 8))
        BaseButton(self.toolbar.right, "Start Scan", self.actions["start_scan"], variant="primary", width=108).grid(row=0, column=1)

        self.metrics = self._build_metric_row()
        self.risk_card = self._build_risk_card()
        self.status_card = ProgressCard(self, "Scan Status")
        self.status_card.grid(row=4, column=0, sticky="ew", padx=self.theme.spacing("app_padding"), pady=(0, 14))

    def refresh(self, state: AppState) -> None:
        self.metrics["skills"].set_value(state.confirmed_count)
        self.metrics["candidates"].set_value(state.candidate_count)
        self.metrics["commands"].set_value(state.command_count)
        self.metrics["config"].set_value(state.config_count)
        risk_counts = state.risk_counts
        self.risk_summary.configure(
            text=(
                f"Critical {risk_counts['critical']}   "
                f"High {risk_counts['high']}   "
                f"Medium {risk_counts['medium']}   "
                f"Low {risk_counts['low']}"
            )
        )
        self.risk_note.configure(text=_risk_note(risk_counts))
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

    def _build_risk_card(self) -> BaseCard:
        import customtkinter as ctk

        card = BaseCard(self, title="Risk Summary")
        card.grid(row=3, column=0, sticky="ew", padx=self.theme.spacing("app_padding"), pady=(0, 14))
        self.risk_summary = ctk.CTkLabel(
            card.body,
            text="Critical 0   High 0   Medium 0   Low 0",
            font=self.theme.font("section_title"),
            text_color=self.theme.color("text_primary"),
            anchor="w",
        )
        self.risk_summary.grid(row=0, column=0, sticky="ew")
        self.risk_note = ctk.CTkLabel(
            card.body,
            text="No committed risk indicators yet.",
            font=self.theme.font("caption"),
            text_color=self.theme.color("text_muted"),
            anchor="w",
        )
        self.risk_note.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        return card

    def _transparent_row(self):
        import customtkinter as ctk

        return ctk.CTkFrame(self, fg_color="transparent")


def _risk_note(risk_counts: dict[str, int]) -> str:
    if risk_counts.get("critical", 0):
        return "Critical records need review before trust."
    if risk_counts.get("high", 0):
        return "High-risk records are marked in tables."
    if risk_counts.get("medium", 0):
        return "Medium-risk records may need review."
    if risk_counts.get("low", 0):
        return "Only low-risk records are currently visible."
    return "No committed risk indicators yet."
