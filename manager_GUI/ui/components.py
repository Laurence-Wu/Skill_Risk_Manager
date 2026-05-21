from __future__ import annotations

from datetime import datetime
from typing import Callable

import customtkinter as ctk

from manager_GUI.core.state import AppState
from manager_GUI.models import LogEntry
from manager_GUI.ui.theme import ThemeManager, get_theme


class BaseComponent:
    def _init_component(self, theme: ThemeManager | None = None) -> None:
        self.theme = theme or get_theme()

    def configure_state(self, state: str) -> None:
        if hasattr(self, "configure"):
            self.configure(**self.theme.button_style(getattr(self, "variant", "secondary"), state))


class BaseButton(BaseComponent, ctk.CTkButton):
    def __init__(
        self,
        master,
        text: str,
        command: Callable[[], None] | None = None,
        *,
        variant: str = "secondary",
        theme: ThemeManager | None = None,
        width: int | None = None,
    ) -> None:
        self._init_component(theme)
        self.variant = variant
        style = self.theme.button_style(variant, "default")
        super().__init__(
            master,
            text=text,
            command=command,
            height=self.theme.spacing("button_height"),
            width=width or 92,
            corner_radius=self.theme.spacing("radius_button"),
            font=self.theme.font("button"),
            **style,
        )
        self.bind("<FocusIn>", lambda _event: self.configure_state("focus"))
        self.bind("<FocusOut>", lambda _event: self.configure_state("default"))
        self.bind("<ButtonPress-1>", lambda _event: self.configure_state("pressed"))
        self.bind("<ButtonRelease-1>", lambda _event: self.configure_state("default"))

    def set_enabled(self, enabled: bool) -> None:
        self.configure(state="normal" if enabled else "disabled")
        self.configure_state("default" if enabled else "disabled")


class BaseCard(BaseComponent, ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        title: str = "",
        subtitle: str = "",
        theme: ThemeManager | None = None,
    ) -> None:
        self._init_component(theme)
        super().__init__(
            master,
            fg_color=self.theme.color("surface"),
            border_color=self.theme.color("border"),
            border_width=1,
            corner_radius=self.theme.spacing("radius_card"),
        )
        self.grid_columnconfigure(0, weight=1)
        row = 0
        pad = self.theme.spacing("card_padding")
        if title:
            ctk.CTkLabel(
                self,
                text=title,
                font=self.theme.font("section_title"),
                text_color=self.theme.color("text_primary"),
                anchor="w",
            ).grid(row=row, column=0, sticky="ew", padx=pad, pady=(pad, 2))
            row += 1
        if subtitle:
            ctk.CTkLabel(
                self,
                text=subtitle,
                font=self.theme.font("small"),
                text_color=self.theme.color("text_muted"),
                anchor="w",
            ).grid(row=row, column=0, sticky="ew", padx=pad, pady=(0, 8))
            row += 1
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=row, column=0, sticky="nsew", padx=pad, pady=(0, pad))
        self.body.grid_columnconfigure(0, weight=1)


class MetricCard(BaseCard):
    def __init__(self, master, label: str, value: object = "0", subtitle: str = "") -> None:
        super().__init__(master)
        self.value_label = ctk.CTkLabel(
            self.body,
            text=str(value),
            font=self.theme.font("page_title"),
            text_color=self.theme.color("text_primary"),
            anchor="w",
        )
        self.value_label.grid(row=0, column=0, sticky="w")
        self.label = ctk.CTkLabel(
            self.body,
            text=label,
            font=self.theme.font("small"),
            text_color=self.theme.color("text_secondary"),
            anchor="w",
        )
        self.label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.subtitle = ctk.CTkLabel(
            self.body,
            text=subtitle,
            font=self.theme.font("caption"),
            text_color=self.theme.color("text_muted"),
            anchor="w",
        )
        self.subtitle.grid(row=2, column=0, sticky="w", pady=(2, 0))

    def set_value(self, value: object, subtitle: str | None = None) -> None:
        self.value_label.configure(text=str(value))
        if subtitle is not None:
            self.subtitle.configure(text=subtitle)


class StatusBadge(BaseComponent, ctk.CTkLabel):
    def __init__(self, master, text: str = "Ready", kind: str = "ready") -> None:
        self._init_component()
        style = self.theme.badge_style(kind)
        super().__init__(
            master,
            text=text,
            font=self.theme.font("caption"),
            corner_radius=self.theme.spacing("radius_badge"),
            padx=9,
            pady=4,
            **style,
        )

    def set_status(self, text: str, kind: str = "ready") -> None:
        self.configure(text=text, **self.theme.badge_style(kind))


class ProgressCard(BaseCard):
    def __init__(self, master, title: str = "Scan") -> None:
        super().__init__(master, title=title)
        self.activity_label = ctk.CTkLabel(
            self.body,
            text="Ready",
            font=self.theme.font("section_title"),
            text_color=self.theme.color("text_primary"),
            anchor="w",
        )
        self.activity_label.grid(row=0, column=0, sticky="ew")
        self.path_label = ctk.CTkLabel(
            self.body,
            text="No scan has run yet.",
            font=self.theme.font("small"),
            text_color=self.theme.color("text_muted"),
            anchor="w",
        )
        self.path_label.grid(row=1, column=0, sticky="ew", pady=(3, 10))
        self.progress = ctk.CTkProgressBar(
            self.body,
            height=14,
            progress_color=self.theme.progress_color("primary"),
        )
        self.progress.grid(row=2, column=0, sticky="ew")
        self.progress.set(0)
        self.counter_label = ctk.CTkLabel(
            self.body,
            text="Files: 0 | Directories: 0 | Potential items: 0",
            font=self.theme.font("caption"),
            text_color=self.theme.color("text_muted"),
            anchor="w",
        )
        self.counter_label.grid(row=3, column=0, sticky="ew", pady=(10, 0))

    def update_activity(
        self,
        label: str,
        current_path: str,
        progress: float,
        mode: str,
        *,
        files_checked: int = 0,
        directories_checked: int = 0,
        potential_items: int = 0,
    ) -> None:
        self.activity_label.configure(text=label or "Current activity")
        self.path_label.configure(text=_truncate(current_path or "No current path", 120))
        self.progress.configure(progress_color=self.theme.progress_color(mode))
        self.progress.set(max(0.0, min(1.0, progress)))
        self.counter_label.configure(
            text=f"Files: {files_checked} | Directories: {directories_checked} | Potential items: {potential_items}"
        )


class BaseTable(BaseComponent, ctk.CTkScrollableFrame):
    def __init__(self, master, columns: list[str], *, empty_text: str = "No records to display.") -> None:
        self._init_component()
        super().__init__(
            master,
            fg_color=self.theme.color("surface"),
            border_color=self.theme.color("border"),
            border_width=1,
            corner_radius=self.theme.spacing("radius_card"),
        )
        self.columns = columns
        self.empty_text = empty_text
        self.selected_row: int | None = None
        self.row_frames: list[ctk.CTkFrame] = []
        self.set_rows([])

    def set_rows(
        self,
        rows: list[dict[str, object]],
        actions: list[tuple[str, Callable[[dict[str, object]], None], str]] | None = None,
    ) -> None:
        for child in self.winfo_children():
            child.destroy()
        self.row_frames = []
        self.selected_row = None
        action_width = sum(_button_width(label_text) + 4 for label_text, _callback, _variant in actions or [])
        total_columns = len(self.columns) + (1 if actions else 0)
        for column_index in range(total_columns):
            self.grid_columnconfigure(column_index, weight=1 if column_index == 0 else 0)

        for column_index, column in enumerate(self.columns):
            ctk.CTkLabel(
                self,
                text=column,
                font=self.theme.font("caption"),
                text_color=self.theme.color("text_muted"),
                anchor="w",
            ).grid(row=0, column=column_index, sticky="ew", padx=8, pady=7)
        if actions:
            ctk.CTkLabel(self, text="", width=max(190, action_width)).grid(
                row=0,
                column=len(self.columns),
                sticky="ew",
                padx=8,
                pady=7,
            )

        if not rows:
            ctk.CTkLabel(
                self,
                text=self.empty_text,
                font=self.theme.font("small"),
                text_color=self.theme.color("text_muted"),
                anchor="w",
            ).grid(row=1, column=0, columnspan=total_columns, sticky="ew", padx=8, pady=12)
            return

        for row_index, row in enumerate(rows, start=1):
            row_bg = self.theme.color("surface_raised") if row_index % 2 else self.theme.color("surface")
            row_frame = ctk.CTkFrame(self, fg_color=row_bg, corner_radius=0, height=self.theme.spacing("table_row_height"))
            row_frame.grid(row=row_index, column=0, columnspan=total_columns, sticky="ew", padx=5, pady=1)
            row_frame.grid_columnconfigure(0, weight=1)
            self.row_frames.append(row_frame)
            row_frame.bind("<Button-1>", lambda _event, index=row_index - 1: self._select_row(index))
            for column_index, column in enumerate(self.columns):
                value = _truncate(str(row.get(column, "")), 72 if column.lower() == "path" else 36)
                label = ctk.CTkLabel(
                    row_frame,
                    text=value,
                    font=self.theme.font("small"),
                    text_color=self.theme.color("text_secondary"),
                    anchor="w",
                    height=self.theme.spacing("table_row_height"),
                )
                label.grid(row=0, column=column_index, sticky="ew", padx=8)
                label.bind("<Button-1>", lambda _event, index=row_index - 1: self._select_row(index))
            if actions:
                actions_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
                actions_frame.grid(row=0, column=len(self.columns), sticky="e", padx=4)
                for action_index, (label_text, callback, variant) in enumerate(actions):
                    BaseButton(
                        actions_frame,
                        label_text,
                        command=lambda selected=row, action=callback: action(selected),
                        variant=variant,
                        width=_button_width(label_text),
                    ).grid(row=0, column=action_index, padx=2)

    def _select_row(self, index: int) -> None:
        self.selected_row = index
        for row_index, frame in enumerate(self.row_frames):
            frame.configure(
                fg_color=self.theme.color("surface_selected")
                if row_index == index
                else self.theme.color("surface_raised")
                if row_index % 2 == 0
                else self.theme.color("surface")
            )


class LogPanel(BaseComponent, ctk.CTkScrollableFrame):
    def __init__(self, master) -> None:
        self._init_component()
        super().__init__(
            master,
            fg_color=self.theme.color("surface"),
            border_color=self.theme.color("border"),
            border_width=1,
            corner_radius=self.theme.spacing("radius_card"),
        )
        self.grid_columnconfigure(0, weight=1)

    def set_logs(self, logs: list[LogEntry], level_filter: str = "all") -> None:
        for child in self.winfo_children():
            child.destroy()
        visible_logs = [log for log in logs if level_filter == "all" or log.level == level_filter]
        if not visible_logs:
            ctk.CTkLabel(
                self,
                text="No events yet.",
                font=self.theme.font("small"),
                text_color=self.theme.color("text_muted"),
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=10, pady=10)
            return
        for row_index, log in enumerate(visible_logs[-200:]):
            color = {
                "info": self.theme.color("status_info"),
                "warning": self.theme.color("status_warning"),
                "error": self.theme.color("status_danger"),
                "success": self.theme.color("status_success"),
            }.get(log.level, self.theme.color("text_secondary"))
            timestamp = datetime.fromtimestamp(log.timestamp).strftime("%H:%M:%S")
            ctk.CTkLabel(
                self,
                text=f"{timestamp}  {log.level.upper():7}  {log.message}",
                font=self.theme.font("small"),
                text_color=color,
                anchor="w",
            ).grid(row=row_index, column=0, sticky="ew", padx=10, pady=2)


class BaseView(BaseComponent, ctk.CTkFrame):
    def __init__(self, master, actions: dict[str, Callable], **kwargs) -> None:
        self._init_component()
        super().__init__(master, fg_color=self.theme.color("app_bg"), **kwargs)
        self.actions = actions
        self.grid_columnconfigure(0, weight=1)

    def mount(self) -> None:
        self.grid(row=0, column=0, sticky="nsew")

    def unmount(self) -> None:
        self.grid_remove()

    def refresh(self, state: AppState) -> None:
        raise NotImplementedError

    def bind_events(self, controller) -> None:
        self.controller = controller

    def page_header(self, title: str, subtitle: str = "") -> None:
        ctk.CTkLabel(
            self,
            text=title,
            font=self.theme.font("page_title"),
            text_color=self.theme.color("text_primary"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=self.theme.spacing("app_padding"), pady=(16, 2))
        if subtitle:
            ctk.CTkLabel(
                self,
                text=subtitle,
                font=self.theme.font("small"),
                text_color=self.theme.color("text_muted"),
                anchor="w",
            ).grid(row=1, column=0, sticky="ew", padx=self.theme.spacing("app_padding"), pady=(0, 10))


def status_kind(scan_status: str) -> str:
    return {
        "ready": "ready",
        "scanning": "scanning",
        "committed": "valid",
        "complete": "complete",
        "paused": "paused",
        "cancelled": "cancelled",
        "error": "error",
    }.get(scan_status, "ready")


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


def _button_width(label: str) -> int:
    return max(76, len(label) * 7 + 26)
