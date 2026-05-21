from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from manager_GUI.core.backend_controller import BackendController
from manager_GUI.core.state import AppState
from manager_GUI.ui.components import BaseButton, StatusBadge, status_kind
from manager_GUI.ui.theme import ThemeManager, get_theme
from manager_GUI.ui.views.candidates import CandidatesView
from manager_GUI.ui.views.config import ConfigView
from manager_GUI.ui.views.dashboard import DashboardView
from manager_GUI.ui.views.logs import LogsView
from manager_GUI.ui.views.scan import ScanView
from manager_GUI.ui.views.skills import SkillsView


POLL_INTERVAL_MS = 50
REFRESH_INTERVAL_SECONDS = 0.16
MAX_BACKEND_EVENTS_PER_TICK = 240
MAX_UI_EVENTS_PER_TICK = 160
IMMEDIATE_REFRESH_EVENTS = {
    "scan_started",
    "snapshot_committed",
    "continuation_started",
    "scan_paused",
    "scan_resumed",
    "scan_cancelled",
    "scan_completed",
    "scan_error",
}


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.theme: ThemeManager = get_theme()
        self.controller = BackendController()
        self.views: dict[str, ctk.CTkFrame] = {}
        self.active_view_key = "dashboard"
        self._last_refresh_at = 0.0
        self._refresh_pending = False

        self.title("Skill Risk Manager")
        self.geometry("1280x800")
        self.minsize(1100, 720)
        self.configure(fg_color=self.theme.color("app_bg"))
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_topbar()
        self._build_sidebar()
        self._build_content()
        self._build_views()
        self.show_view("dashboard")
        self.after(POLL_INTERVAL_MS, self._poll_controller)

    def show_view(self, key: str) -> None:
        if key not in self.views:
            return
        for view in self.views.values():
            view.unmount()
        self.active_view_key = key
        self.views[key].mount()
        self._render_sidebar()
        self.views[key].refresh(self.controller.get_state())

    def _build_topbar(self) -> None:
        self.topbar = ctk.CTkFrame(self, fg_color=self.theme.color("shell_bg"), corner_radius=0, height=self.theme.spacing("topbar_height"))
        self.topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.topbar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.topbar,
            text="Skill Risk Manager",
            font=self.theme.font("section_title"),
            text_color=self.theme.color("text_primary"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=13)
        state = self.controller.get_state()
        self.platform_badge = StatusBadge(self.topbar, state.platform, "ready")
        self.platform_badge.grid(row=0, column=1, padx=(8, 8), pady=13)
        self.status_badge = StatusBadge(self.topbar, "Ready", "ready")
        self.status_badge.grid(row=0, column=2, padx=(0, 16), pady=13)

    def _build_sidebar(self) -> None:
        self.sidebar = ctk.CTkFrame(self, fg_color=self.theme.color("nav_bg"), corner_radius=0, width=self.theme.spacing("sidebar_width"))
        self.sidebar.grid(row=1, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)

    def _build_content(self) -> None:
        self.content = ctk.CTkFrame(self, fg_color=self.theme.color("app_bg"), corner_radius=0)
        self.content.grid(row=1, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

    def _build_views(self) -> None:
        actions: dict[str, Callable] = {
            "start_scan": self._start_scan,
            "cancel_scan": self._cancel_scan,
            "pause_scan": self._pause_scan,
            "resume_scan": self._resume_scan,
            "show_view": self.show_view,
            "set_security_level": self._set_security_level,
            "copy_path": self._copy_path,
            "open_folder": self._open_folder,
            "promote_candidate": self._promote_candidate,
            "ignore_candidate": self._ignore_candidate,
            "clear_logs": self._clear_logs,
            "export_logs": self._export_logs,
            "open_logs_folder": self._open_logs_folder,
        }
        self.views = {
            "dashboard": DashboardView(self.content, actions),
            "scan": ScanView(self.content, actions),
            "skills": SkillsView(self.content, actions),
            "candidates": CandidatesView(self.content, actions),
            "config": ConfigView(self.content, actions),
            "logs": LogsView(self.content, actions),
        }
        for view in self.views.values():
            view.grid(row=0, column=0, sticky="nsew")
            view.unmount()

    def _render_sidebar(self) -> None:
        for child in self.sidebar.winfo_children():
            child.destroy()
        nav_items = [
            ("Dashboard", "dashboard"),
            ("Scan", "scan"),
            ("Skills", "skills"),
            ("Candidates", "candidates"),
            ("Config", "config"),
            ("Logs", "logs"),
        ]
        for row, (label, key) in enumerate(nav_items):
            selected = key == self.active_view_key
            item = ctk.CTkFrame(
                self.sidebar,
                fg_color=self.theme.color("surface_selected") if selected else "transparent",
                corner_radius=0,
            )
            item.grid(row=row, column=0, sticky="ew", padx=0, pady=(10 if row == 0 else 2, 0))
            item.grid_columnconfigure(1, weight=1)
            ctk.CTkFrame(
                item,
                fg_color=self.theme.color("accent_primary") if selected else "transparent",
                width=4,
                corner_radius=0,
            ).grid(row=0, column=0, sticky="nsw")
            BaseButton(
                item,
                label,
                command=lambda view_key=key: self.show_view(view_key),
                variant="quiet",
                width=self.theme.spacing("sidebar_width") - 4,
            ).grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=3)

    def _poll_controller(self) -> None:
        import time

        events = self.controller.poll_events(
            max_backend_events=MAX_BACKEND_EVENTS_PER_TICK,
            max_ui_events=MAX_UI_EVENTS_PER_TICK,
        )
        if events:
            self._refresh_pending = True
        now = time.monotonic()
        has_immediate_event = any(event.type in IMMEDIATE_REFRESH_EVENTS for event in events)
        if self._refresh_pending and (has_immediate_event or now - self._last_refresh_at >= REFRESH_INTERVAL_SECONDS):
            self._refresh_visible()
            self._last_refresh_at = now
            self._refresh_pending = False
        self.after(POLL_INTERVAL_MS, self._poll_controller)

    def _refresh_chrome(self, state: AppState) -> None:
        self.platform_badge.set_status(state.platform, "ready")
        self.status_badge.set_status(state.scan_status.title(), status_kind(state.scan_status))

    def _refresh_all(self) -> None:
        self._refresh_visible()

    def _refresh_visible(self) -> None:
        state = self.controller.get_state()
        self._refresh_chrome(state)
        active_view = self.views.get(self.active_view_key)
        if active_view:
            active_view.refresh(state)

    def _start_scan(self) -> None:
        self.controller.start_scan()
        self._refresh_all()

    def _cancel_scan(self) -> None:
        self.controller.cancel_scan()
        self._refresh_all()

    def _pause_scan(self) -> None:
        self.controller.pause_scan()
        self._refresh_all()

    def _resume_scan(self) -> None:
        self.controller.resume_scan()
        self._refresh_all()

    def _set_security_level(self, level: str) -> None:
        self.controller.set_security_level(level)
        self._refresh_all()

    def _copy_path(self, path_text: str) -> None:
        def set_clipboard(value: str) -> None:
            self.clipboard_clear()
            self.clipboard_append(value)
            self.update()

        self.controller.copy_path(path_text, set_clipboard)
        self._refresh_all()

    def _open_folder(self, path_text: str) -> None:
        self.controller.open_folder(path_text)
        self._refresh_all()

    def _promote_candidate(self, candidate) -> None:
        self.controller.promote_candidate(candidate)
        self._refresh_all()

    def _ignore_candidate(self, candidate) -> None:
        self.controller.ignore_candidate(candidate)
        self._refresh_all()

    def _clear_logs(self) -> None:
        self.controller.clear_logs()
        self._refresh_all()

    def _export_logs(self) -> None:
        self.controller.export_logs()
        self._refresh_all()

    def _open_logs_folder(self) -> None:
        self.controller.open_logs_folder()
        self._refresh_all()
