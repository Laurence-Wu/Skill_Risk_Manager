from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from manager_GUI.core.state import AppState
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
        self.body = self._build_body(title, subtitle)

    def _build_body(self, title: str, subtitle: str) -> ctk.CTkFrame:
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
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=row, column=0, sticky="nsew", padx=pad, pady=(0, pad))
        body.grid_columnconfigure(0, weight=1)
        return body


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
        super().__init__(
            master,
            text=text,
            font=self.theme.font("caption"),
            corner_radius=self.theme.spacing("radius_badge"),
            padx=9,
            pady=4,
            **self.theme.badge_style(kind),
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
        expected_total_files: int = 0,
        directories_checked: int = 0,
        potential_items: int = 0,
    ) -> None:
        self.activity_label.configure(text=label or "Current activity")
        self.path_label.configure(text=_truncate(current_path or "No current path", 120))
        self.progress.configure(progress_color=self.theme.progress_color(mode))
        self.progress.set(max(0.0, min(1.0, progress)))
        self.counter_label.configure(
            text=(
                f"Files: {_files_text(files_checked, expected_total_files)} | "
                f"Directories: {directories_checked} | Potential items: {potential_items}"
            )
        )


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


def _files_text(files_checked: int, expected_total_files: int) -> str:
    if expected_total_files:
        return f"{files_checked} / ~{max(expected_total_files, files_checked)}"
    return str(files_checked)


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."
