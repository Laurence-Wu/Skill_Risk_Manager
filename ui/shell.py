from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ui.core.backend_controller import BackendController
from ui.core.state import AppState
from ui.components import BaseButton, StatusBadge, status_kind
from ui.theme import ThemeManager, get_theme
from ui.views.candidates import CandidatesView
from ui.views.config import ConfigView
from ui.views.dashboard import DashboardView
from ui.views.logs import LogsView
from ui.views.risk import RiskView
from ui.views.scan import ScanView
from ui.views.skills import SkillsView


POLL_INTERVAL_MS = 50
REFRESH_INTERVAL_SECONDS = 0.16
LAZY_REFRESH_INTERVAL_SECONDS = 0.35
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
NAV_ITEMS = [
    ("Dashboard", "dashboard"),
    ("Scan", "scan"),
    ("Skills", "skills"),
    ("Candidates", "candidates"),
    ("Risk", "risk"),
    ("Config", "config"),
    ("Logs", "logs"),
]


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
        self.geometry("1360x840")
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
        self.topbar = ctk.CTkFrame(
            self,
            fg_color=self.theme.color("shell_bg"),
            corner_radius=0,
            height=self.theme.spacing("topbar_height"),
            border_color=self.theme.color("border"),
            border_width=1,
        )
        self.topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.topbar.grid_propagate(False)
        self.topbar.grid_columnconfigure(0, weight=1)
        title_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w", padx=18, pady=9)
        ctk.CTkLabel(
            title_frame,
            text="[<>]",
            font=self.theme.font("section_title"),
            text_color=self.theme.color("accent_primary"),
            width=46,
            height=44,
            fg_color=self.theme.color("surface_raised"),
            corner_radius=12,
        ).grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))
        ctk.CTkLabel(
            title_frame,
            text="Skill Risk Manager",
            font=self.theme.font("section_title"),
            text_color=self.theme.color("text_primary"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            title_frame,
            text="Local discovery, risk review, stable snapshots",
            font=self.theme.font("caption"),
            text_color=self.theme.color("text_muted"),
            anchor="w",
        ).grid(row=1, column=1, sticky="w")
        state = self.controller.get_state()
        self.platform_badge = StatusBadge(self.topbar, state.platform, "ready")
        self.platform_badge.grid(row=0, column=1, padx=(8, 8), pady=18)
        self.status_badge = StatusBadge(self.topbar, "Ready", "ready")
        self.status_badge.grid(row=0, column=2, padx=(0, 8), pady=18)
        self.security_badge = StatusBadge(self.topbar, security_label(state.security_level), "ready")
        self.security_badge.grid(row=0, column=3, padx=(0, 18), pady=18)

    def _build_sidebar(self) -> None:
        self.sidebar = ctk.CTkFrame(
            self,
            fg_color=self.theme.color("nav_bg"),
            corner_radius=0,
            width=self.theme.spacing("sidebar_width"),
            border_color=self.theme.color("border"),
            border_width=1,
        )
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
            "export_skills": self._export_skills,
            "export_risk_report": self._export_risk_report,
            "save_config": self._save_config,
            "refresh": self._refresh_all,
        }
        self.views = {
            "dashboard": DashboardView(self.content, actions),
            "scan": ScanView(self.content, actions),
            "skills": SkillsView(self.content, actions),
            "candidates": CandidatesView(self.content, actions),
            "risk": RiskView(self.content, actions),
            "config": ConfigView(self.content, actions),
            "logs": LogsView(self.content, actions),
        }
        for view in self.views.values():
            view.grid(row=0, column=0, sticky="nsew")
            view.unmount()

    def _render_sidebar(self) -> None:
        for child in self.sidebar.winfo_children():
            child.destroy()
        for row, (label, key) in enumerate(NAV_ITEMS):
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
        state = self.controller.get_state() if self._refresh_pending else None
        refresh_interval = LAZY_REFRESH_INTERVAL_SECONDS if state and state.lazy_updates_enabled else REFRESH_INTERVAL_SECONDS
        if self._refresh_pending and (has_immediate_event or now - self._last_refresh_at >= refresh_interval):
            self._refresh_visible(state)
            self._last_refresh_at = now
            self._refresh_pending = False
        self.after(POLL_INTERVAL_MS, self._poll_controller)

    def _refresh_chrome(self, state: AppState) -> None:
        self.platform_badge.set_status(state.platform, "ready")
        self.status_badge.set_status(state.scan_status.title(), status_kind(state.scan_status))
        self.security_badge.set_status(security_label(state.security_level), "warning" if state.security_level == "advanced" else "ready")

    def _refresh_all(self) -> None:
        self._refresh_visible()

    def _refresh_visible(self, state: AppState | None = None) -> None:
        state = state or self.controller.get_state()
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

    def _export_skills(self) -> None:
        self.controller.export_skills()
        self._refresh_all()

    def _export_risk_report(self) -> None:
        self.controller.export_risk_report()
        self._refresh_all()

    def _save_config(self) -> None:
        self.controller.save_config()
        self._refresh_all()


def security_label(security_level: str) -> str:
    return "Advanced Mode" if security_level == "advanced" else "Base Mode"
