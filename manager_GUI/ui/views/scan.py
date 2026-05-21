from __future__ import annotations

import customtkinter as ctk

from manager_GUI.core.state import AppState
from manager_GUI.ui.components import BaseButton, BaseView, LogPanel, MetricCard, ProgressCard


class ScanView(BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(6, weight=1)
        self._rendered_security_level = ""
        self.page_header("Scan", "Run discovery, commit stable results, and stage uncertain findings for review.")

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="w", padx=self.theme.spacing("app_padding"), pady=(0, 14))
        BaseButton(controls, "Start Scan", self.actions["start_scan"], variant="primary", width=110).grid(row=0, column=0, padx=(0, 8))
        BaseButton(controls, "Cancel", self.actions["cancel_scan"], variant="danger", width=90).grid(row=0, column=1, padx=(0, 8))
        BaseButton(controls, "Pause", self.actions["pause_scan"], width=90).grid(row=0, column=2, padx=(0, 8))
        BaseButton(controls, "Resume", self.actions["resume_scan"], width=90).grid(row=0, column=3)

        self.security_row = ctk.CTkFrame(self, fg_color="transparent")
        self.security_row.grid(row=3, column=0, sticky="ew", padx=self.theme.spacing("app_padding"), pady=(0, 14))

        self.progress_card = ProgressCard(self, "Current Activity")
        self.progress_card.grid(row=4, column=0, sticky="ew", padx=self.theme.spacing("app_padding"), pady=(0, 14))

        self.counters = self._build_counters()
        self.log_panel = LogPanel(self)
        self.log_panel.grid(row=6, column=0, sticky="nsew", padx=self.theme.spacing("app_padding"), pady=(0, 16))

    def refresh(self, state: AppState) -> None:
        self._render_security_controls(state.security_level)
        self.progress_card.update_activity(
            state.current_activity,
            state.current_path,
            state.progress,
            state.progress_mode,
            files_checked=state.files_checked,
            directories_checked=state.directories_checked,
            potential_items=state.potential_items,
        )
        self.counters["files"].set_value(state.files_checked)
        self.counters["directories"].set_value(state.directories_checked)
        self.counters["potential"].set_value(state.potential_items)
        self.log_panel.set_logs(state.logs)

    def _build_counters(self) -> dict[str, MetricCard]:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=5, column=0, sticky="ew", padx=self.theme.spacing("app_padding"), pady=(0, 14))
        for column in range(3):
            row.grid_columnconfigure(column, weight=1, uniform="scan_counters")
        cards = {
            "files": MetricCard(row, "Files Checked"),
            "directories": MetricCard(row, "Directories Checked"),
            "potential": MetricCard(row, "Potential Items"),
        }
        for column, card in enumerate(cards.values()):
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
        return cards

    def _render_security_controls(self, selected_level: str) -> None:
        if self._rendered_security_level == selected_level and self.security_row.winfo_children():
            return
        self._rendered_security_level = selected_level
        for child in self.security_row.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.security_row,
            text="Security Level",
            font=self.theme.font("small"),
            text_color=self.theme.color("text_secondary"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))
        BaseButton(
            self.security_row,
            "Base",
            lambda: self.actions["set_security_level"]("base"),
            variant="primary" if selected_level == "base" else "secondary",
            width=86,
        ).grid(row=0, column=1, padx=(0, 6))
        BaseButton(
            self.security_row,
            "Advanced",
            lambda: self.actions["set_security_level"]("advanced"),
            variant="primary" if selected_level == "advanced" else "secondary",
            width=104,
        ).grid(row=0, column=2, padx=(0, 12))
        ctk.CTkLabel(
            self.security_row,
            text="Base scans accessible files. Advanced also attempts protected paths.",
            font=self.theme.font("caption"),
            text_color=self.theme.color("text_muted"),
            anchor="w",
        ).grid(row=0, column=3, sticky="w")
