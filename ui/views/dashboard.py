from __future__ import annotations

import customtkinter as ctk

from ui.core.state import AppState
from ui.components import BaseButton, BaseView


class DashboardView(BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_hero()
        self._build_workspace()

    def refresh(self, state: AppState) -> None:
        primary_progress, continuation_progress = _split_progress(state)
        self.primary_progress.configure(progress_color=self.theme.color("progress_primary"))
        self.primary_progress.set(primary_progress)
        self.continuation_progress.configure(progress_color=self.theme.color("progress_continuation"))
        self.continuation_progress.set(continuation_progress)
        self.primary_percent.configure(text=f"{int(primary_progress * 100)}%")
        self.continuation_percent.configure(text=f"{int(continuation_progress * 100)}%")
        self.primary_counter.configure(text=_files_text(state.files_checked, state.expected_total_files))
        self.continuation_counter.configure(text=f"{len(state.candidates_staged)} staged")
        self.activity_label.configure(text=state.current_activity or "Ready")
        self.path_label.configure(text=_truncate(state.current_path or "No active path", 90))

        self.skill_value.configure(text=str(state.confirmed_count))
        self.skill_note.configure(text=f"{state.command_count} commands")
        self.candidate_value.configure(text=str(state.candidate_count))
        self.candidate_note.configure(text="review needed" if state.candidate_count else "clear")
        self.log_value.configure(text=f"{len(state.logs):,}")
        self.log_note.configure(text=_last_scan_text(state))
        self.config_value.configure(text=state.security_level.title())
        self.config_note.configure(text=_truncate(state.claude_config_root, 26))

        risk_counts = state.risk_counts
        self.risk_text.configure(
            text=(
                f"Critical {risk_counts['critical']}  "
                f"High {risk_counts['high']}  "
                f"Medium {risk_counts['medium']}  "
                f"Low {risk_counts['low']}"
            )
        )
        self.snapshot_count.configure(text=str(state.confirmed_count))
        self.snapshot_subtitle.configure(text=f"{state.config_count} config files tracked")
        self.candidate_count.configure(text=str(state.candidate_count))
        self.candidate_subtitle.configure(text=f"{len(state.candidates_staged)} staged during continuation")

    def _build_hero(self) -> None:
        hero = ctk.CTkFrame(self, fg_color="transparent")
        hero.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 12))
        hero.grid_columnconfigure(0, weight=1)

        title_area = ctk.CTkFrame(hero, fg_color="transparent")
        title_area.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            title_area,
            text="[SRM]",
            width=72,
            height=72,
            corner_radius=18,
            fg_color=self.theme.color("surface_raised"),
            text_color=self.theme.color("accent_primary"),
            font=("Consolas", 18, "bold"),
        ).grid(row=0, column=0, rowspan=2, padx=(0, 16), sticky="w")
        ctk.CTkLabel(
            title_area,
            text="Skill Risk Manager",
            font=self.theme.font("app_title"),
            text_color=self.theme.color("text_primary"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            title_area,
            text="Local desktop tool for discovering skills, reviewing risk, and managing stable vs staged results",
            font=self.theme.font("body"),
            text_color=self.theme.color("text_muted"),
            anchor="w",
        ).grid(row=1, column=1, sticky="w", pady=(4, 0))

        modes = ctk.CTkFrame(hero, fg_color="transparent")
        modes.grid(row=0, column=1, sticky="e")
        self._build_mode_card(modes, "BASE", "Safe defaults", "Lower risk", "base", 0)
        self._build_mode_card(modes, "ADVANCED", "Deeper insights", "Higher detection", "advanced", 1)

    def _build_mode_card(self, master, title: str, line_one: str, line_two: str, level: str, column: int) -> None:
        accent = self.theme.color("accent_amber") if level == "advanced" else self.theme.color("accent_cyan")
        card = ctk.CTkFrame(
            master,
            fg_color=self.theme.color("surface"),
            border_color=accent,
            border_width=1,
            corner_radius=10,
            width=178,
            height=74,
        )
        card.grid(row=0, column=column, padx=(0 if column == 0 else 10, 0), sticky="e")
        card.grid_propagate(False)
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            card,
            text="[<>]" if level == "base" else "[*]",
            width=44,
            text_color=accent,
            font=("Consolas", 16, "bold"),
        ).grid(row=0, column=0, rowspan=2, padx=(12, 8), pady=12)
        ctk.CTkLabel(
            card,
            text=title,
            font=self.theme.font("section_title"),
            text_color=accent,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(13, 0))
        ctk.CTkLabel(
            card,
            text=f"{line_one}\n{line_two}",
            font=self.theme.font("caption"),
            text_color=self.theme.color("text_secondary"),
            anchor="w",
            justify="left",
        ).grid(row=1, column=1, sticky="w")
        card.bind("<Button-1>", lambda _event, selected=level: self.actions["set_security_level"](selected))

    def _build_workspace(self) -> None:
        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        workspace.grid_columnconfigure(0, minsize=168)
        workspace.grid_columnconfigure(1, weight=1)
        workspace.grid_columnconfigure(2, minsize=260)
        workspace.grid_rowconfigure(0, weight=1)

        self._build_workflow(workspace)
        self._build_console(workspace)
        self._build_side_summary(workspace)

    def _build_workflow(self, master) -> None:
        card = ctk.CTkFrame(
            master,
            fg_color=self.theme.color("surface"),
            border_color=self.theme.color("border"),
            border_width=1,
            corner_radius=12,
        )
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        card.grid_columnconfigure(0, weight=1)
        self._workflow_step(card, 0, "1. SCAN", "Local machine discovery", self.theme.color("accent_primary"))
        self._workflow_step(card, 1, "2. REVIEW", "Assess uncertainty and risk", self.theme.color("accent_amber"))
        self._workflow_step(card, 2, "3. COMMIT", "Promote to stable snapshot", self.theme.color("accent_green"))

    def _workflow_step(self, master, row: int, title: str, body: str, color: str) -> None:
        block = ctk.CTkFrame(master, fg_color="transparent")
        block.grid(row=row, column=0, sticky="ew", padx=14, pady=(16 if row == 0 else 10, 8))
        block.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            block,
            text=title,
            font=self.theme.font("button"),
            text_color=color,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            block,
            text=body,
            font=self.theme.font("small"),
            text_color=self.theme.color("text_secondary"),
            anchor="w",
            justify="left",
            wraplength=130,
        ).grid(row=1, column=0, sticky="ew", pady=(5, 0))

    def _build_console(self, master) -> None:
        panel = ctk.CTkFrame(
            master,
            fg_color=self.theme.color("surface"),
            border_color=self.theme.color("border_strong"),
            border_width=1,
            corner_radius=12,
        )
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Scan",
            font=self.theme.font("page_title"),
            text_color=self.theme.color("text_primary"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        BaseButton(header, "Start Scan", self.actions["start_scan"], variant="primary", width=112).grid(row=0, column=1, padx=(8, 0))
        BaseButton(header, "Review", lambda: self.actions["show_view"]("candidates"), width=92).grid(row=0, column=2, padx=(8, 0))
        self.activity_label = ctk.CTkLabel(
            header,
            text="Ready",
            font=self.theme.font("small"),
            text_color=self.theme.color("text_muted"),
            anchor="w",
        )
        self.activity_label.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        self.path_label = ctk.CTkLabel(
            header,
            text="No active path",
            font=self.theme.font("caption"),
            text_color=self.theme.color("text_faint"),
            anchor="w",
        )
        self.path_label.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(2, 0))

        progress_area = ctk.CTkFrame(
            panel,
            fg_color=self.theme.color("app_bg"),
            border_color=self.theme.color("border"),
            border_width=1,
            corner_radius=10,
        )
        progress_area.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))
        progress_area.grid_columnconfigure(1, weight=1)
        self.primary_progress, self.primary_percent, self.primary_counter = self._progress_row(
            progress_area,
            0,
            "Primary scan",
            "Full discovery with highest accuracy",
            self.theme.color("progress_primary"),
        )
        self.continuation_progress, self.continuation_percent, self.continuation_counter = self._progress_row(
            progress_area,
            1,
            "Reduced-budget continuation",
            "Additional findings are staged for review",
            self.theme.color("progress_continuation"),
        )

        metric_area = ctk.CTkFrame(panel, fg_color="transparent")
        metric_area.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        for column in range(4):
            metric_area.grid_columnconfigure(column, weight=1, uniform="dash_tiles")
        self.skill_value, self.skill_note = self._metric_tile(metric_area, 0, "Skills", "0", "committed", "View all", "skills", self.theme.color("accent_primary"))
        self.candidate_value, self.candidate_note = self._metric_tile(metric_area, 1, "Candidates", "0", "review needed", "Review now", "candidates", self.theme.color("accent_amber"))
        self.log_value, self.log_note = self._metric_tile(metric_area, 2, "Logs", "0", "No errors", "View logs", "logs", self.theme.color("accent_cyan"))
        self.config_value, self.config_note = self._metric_tile(metric_area, 3, "Config", "Base", "~/.claude", "Edit config", "config", self.theme.color("text_secondary"))

        risk_strip = ctk.CTkFrame(panel, fg_color=self.theme.color("surface_raised"), corner_radius=10)
        risk_strip.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))
        risk_strip.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            risk_strip,
            text="Risk-aware discovery",
            font=self.theme.font("section_title"),
            text_color=self.theme.color("text_primary"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 0))
        self.risk_text = ctk.CTkLabel(
            risk_strip,
            text="Critical 0  High 0  Medium 0  Low 0",
            font=self.theme.font("small"),
            text_color=self.theme.color("text_secondary"),
            anchor="w",
        )
        self.risk_text.grid(row=1, column=0, sticky="ew", padx=14, pady=(3, 10))
        BaseButton(risk_strip, "Open Risk", lambda: self.actions["show_view"]("risk"), width=96).grid(row=0, column=1, rowspan=2, padx=14, pady=10)

    def _progress_row(self, master, row: int, title: str, subtitle: str, color: str):
        ctk.CTkLabel(
            master,
            text="[scan]" if row == 0 else "[more]",
            text_color=color,
            font=("Consolas", 14, "bold"),
            width=66,
        ).grid(row=row, column=0, sticky="ns", padx=(14, 10), pady=(14, 8))
        text_area = ctk.CTkFrame(master, fg_color="transparent")
        text_area.grid(row=row, column=1, sticky="ew", pady=(14, 8))
        text_area.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            text_area,
            text=title,
            font=self.theme.font("section_title"),
            text_color=self.theme.color("text_primary"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            text_area,
            text=subtitle,
            font=self.theme.font("caption"),
            text_color=self.theme.color("text_muted"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew")
        progress = ctk.CTkProgressBar(text_area, height=10, progress_color=color)
        progress.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        progress.set(0)
        percent = ctk.CTkLabel(
            master,
            text="0%",
            font=self.theme.font("section_title"),
            text_color=color,
            width=54,
        )
        percent.grid(row=row, column=2, sticky="e", padx=(10, 8), pady=(14, 8))
        counter = ctk.CTkLabel(
            master,
            text="0",
            font=self.theme.font("caption"),
            text_color=self.theme.color("text_muted"),
            width=84,
            anchor="e",
        )
        counter.grid(row=row, column=3, sticky="e", padx=(0, 14), pady=(14, 8))
        return progress, percent, counter

    def _metric_tile(self, master, column: int, title: str, value: str, note: str, action: str, target: str, accent: str):
        tile = ctk.CTkFrame(
            master,
            fg_color=self.theme.color("surface_raised"),
            border_color=self.theme.color("border"),
            border_width=1,
            corner_radius=10,
        )
        tile.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
        tile.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            tile,
            text=title,
            font=self.theme.font("section_title"),
            text_color=accent,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 4))
        value_label = ctk.CTkLabel(
            tile,
            text=value,
            font=self.theme.font("page_title"),
            text_color=self.theme.color("text_primary"),
            anchor="w",
        )
        value_label.grid(row=1, column=0, sticky="ew", padx=14)
        note_label = ctk.CTkLabel(
            tile,
            text=note,
            font=self.theme.font("caption"),
            text_color=self.theme.color("text_muted"),
            anchor="w",
        )
        note_label.grid(row=2, column=0, sticky="ew", padx=14, pady=(2, 10))
        BaseButton(tile, action, lambda view_key=target: self.actions["show_view"](view_key), variant="quiet", width=96).grid(row=3, column=0, sticky="w", padx=14, pady=(0, 14))
        return value_label, note_label

    def _build_side_summary(self, master) -> None:
        rail = ctk.CTkFrame(master, fg_color="transparent")
        rail.grid(row=0, column=2, sticky="nsew", padx=(12, 0))
        rail.grid_columnconfigure(0, weight=1)
        rail.grid_rowconfigure(2, weight=1)
        self.snapshot_count, self.snapshot_subtitle = self._summary_card(
            rail,
            0,
            "COMMITTED SNAPSHOT",
            "Stable, reviewed, and trusted",
            "0",
            "Committed skills",
            "Used by Claude Code",
            self.theme.color("accent_cyan"),
            self.theme.color("panel_blue"),
        )
        self.candidate_count, self.candidate_subtitle = self._summary_card(
            rail,
            1,
            "SHADOW / CANDIDATES",
            "Uncertain, under review",
            "0",
            "Candidate skills",
            "Not used until committed",
            self.theme.color("accent_amber"),
            self.theme.color("panel_amber"),
        )

    def _summary_card(
        self,
        master,
        row: int,
        title: str,
        subtitle: str,
        value: str,
        label: str,
        footer: str,
        accent: str,
        background: str,
    ):
        card = ctk.CTkFrame(
            master,
            fg_color=background,
            border_color=accent,
            border_width=1,
            corner_radius=12,
        )
        card.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text=title,
            font=self.theme.font("section_title"),
            text_color=accent,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 0))
        ctk.CTkLabel(
            card,
            text=subtitle,
            font=self.theme.font("caption"),
            text_color=self.theme.color("text_secondary"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(3, 12))
        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=self.theme.font("app_title"),
            text_color=self.theme.color("text_primary"),
            anchor="w",
        )
        value_label.grid(row=2, column=0, sticky="ew", padx=16)
        ctk.CTkLabel(
            card,
            text=label,
            font=self.theme.font("small"),
            text_color=accent,
            anchor="w",
        ).grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
        subtitle_label = ctk.CTkLabel(
            card,
            text=footer,
            font=self.theme.font("caption"),
            text_color=self.theme.color("text_secondary"),
            anchor="w",
        )
        subtitle_label.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))
        return value_label, subtitle_label


def _split_progress(state: AppState) -> tuple[float, float]:
    if state.scan_status == "complete":
        return 1.0, 1.0 if state.candidates_staged else 0.0
    if state.progress_mode == "continuation":
        continuation = max(0.0, min(1.0, (state.progress - 0.72) / 0.28))
        return max(0.72, min(1.0, state.progress)), continuation
    return max(0.0, min(1.0, state.progress)), 0.0


def _files_text(files_checked: int, expected_total_files: int) -> str:
    if expected_total_files:
        return f"{files_checked} / {max(files_checked, expected_total_files)} files"
    return f"{files_checked} files"


def _last_scan_text(state: AppState) -> str:
    if state.scan_status == "error":
        return "Errors need review"
    if state.last_scan_time:
        return "Last scan saved"
    return "No scan yet"


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."
