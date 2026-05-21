from __future__ import annotations

import queue
from pathlib import Path

import customtkinter as ctk

from skill_manager.backend.models import ScanEvent, ScanSummary
from skill_manager.platform import get_platform_adapter
from skill_manager.storage.repository import Repository
from skill_manager.ui.controllers.scan_controller import ScanController
from skill_manager.ui.pages.candidates import CandidatesPage
from skill_manager.ui.pages.dashboard import DashboardPage
from skill_manager.ui.pages.fast_scan import FastScanPage
from skill_manager.ui.pages.logs import LogsPage
from skill_manager.ui.pages.settings import SettingsPage
from skill_manager.ui.pages.shadow_scan import ShadowScanPage
from skill_manager.ui.pages.skills import SkillsPage
from skill_manager.ui.shell.sidebar import Sidebar
from skill_manager.ui.shell.top_bar import TopBar


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.adapter = get_platform_adapter()
        self.repository = Repository.default()
        self.event_queue: queue.Queue[ScanEvent] = queue.Queue()
        self.controller = ScanController(self.adapter, self.repository, self.event_queue)
        self.pages: dict[str, ctk.CTkFrame] = {}

        default_width, default_height = self.adapter.default_window_size()
        minimum_width, minimum_height = self.adapter.minimum_window_size()
        self.geometry(f"{default_width}x{default_height}")
        self.minsize(minimum_width, minimum_height)
        self.title("Claude Skill Manager")

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.top_bar = TopBar(self, self.adapter.name, lambda: self.show_page("settings"))
        self.top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.sidebar = Sidebar(self, self.adapter.sidebar_width(), self.show_page)
        self.sidebar.grid(row=1, column=0, sticky="nsw")

        self.content = ctk.CTkFrame(self)
        self.content.grid(row=1, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self._create_pages()
        self.show_page("dashboard")
        self.after(100, self._poll_events)

    def _create_pages(self) -> None:
        self.pages["dashboard"] = DashboardPage(
            self.content,
            self.adapter,
            self._run_fast_scan,
            lambda: self.show_page("settings"),
            lambda: self.show_page("skills"),
            lambda: self.show_page("candidates"),
            self.controller.cancel_shadow_scan,
        )
        self.pages["fast_scan"] = FastScanPage(self.content, self.controller.cancel_fast_scan)
        self.pages["skills"] = SkillsPage(self.content, self.adapter)
        self.pages["candidates"] = CandidatesPage(self.content, self.adapter)
        self.pages["shadow_scan"] = ShadowScanPage(
            self.content,
            self.controller.pause_shadow_scan,
            self.controller.resume_shadow_scan,
            self.controller.cancel_shadow_scan,
        )
        self.pages["logs"] = LogsPage(self.content)
        self.pages["settings"] = SettingsPage(self.content, self.adapter)

        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_remove()

    def show_page(self, page_key: str) -> None:
        for page in self.pages.values():
            page.grid_remove()
        self.pages[page_key].grid()

    def _run_fast_scan(self) -> None:
        self.show_page("fast_scan")
        self.top_bar.set_scan_status("Scanning")
        self.pages["dashboard"].set_scanning()  # type: ignore[attr-defined]
        self.pages["fast_scan"].mark_running()  # type: ignore[attr-defined]
        self.controller.start_fast_scan(Path.cwd())

    def _poll_events(self) -> None:
        while True:
            try:
                event = self.event_queue.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)
        self.after(100, self._poll_events)

    def _handle_event(self, event: ScanEvent) -> None:
        logs_page: LogsPage = self.pages["logs"]  # type: ignore[assignment]
        logs_page.append(f"{event.event_type}: {event.message}")

        if event.event_type == "foreground_started":
            self.top_bar.set_scan_status("Running")
            self.pages["fast_scan"].mark_running()  # type: ignore[attr-defined]
            return

        if event.event_type == "foreground_progress":
            self.pages["fast_scan"].update_progress(event.payload)  # type: ignore[attr-defined]
            self.pages["dashboard"].update_scan_progress(event.payload)  # type: ignore[attr-defined]
            return

        if event.event_type == "foreground_fast_exit":
            self.pages["fast_scan"].mark_complete()  # type: ignore[attr-defined]
            self.top_bar.set_scan_status("Ready")
            return

        if event.event_type == "snapshot_saved":
            self._load_stable_results(event.payload)
            return

        if event.event_type == "shadow_started":
            self.top_bar.set_scan_status("Shadow Running")
            self.pages["shadow_scan"].set_status("Running")  # type: ignore[attr-defined]
            return

        if event.event_type == "shadow_progress":
            self.pages["shadow_scan"].update_progress(event.payload)  # type: ignore[attr-defined]
            return

        if event.event_type == "shadow_candidate_found":
            self._load_shadow_results()
            return

        if event.event_type == "shadow_paused":
            self.top_bar.set_scan_status("Paused")
            self.pages["shadow_scan"].set_status("Paused")  # type: ignore[attr-defined]
            return

        if event.event_type == "shadow_cancelled":
            self.top_bar.set_scan_status("Cancelled")
            self.pages["shadow_scan"].set_status("Cancelled")  # type: ignore[attr-defined]
            self._load_shadow_results()
            return

        if event.event_type == "shadow_finished":
            self.top_bar.set_scan_status("Complete")
            self.pages["shadow_scan"].set_status("Complete")  # type: ignore[attr-defined]
            self._load_shadow_results()
            return

        if event.event_type == "foreground_cancelled":
            self.top_bar.set_scan_status("Cancelled")
            return

    def _load_stable_results(self, raw_summary: dict) -> None:
        records = self.repository.load_snapshot()
        confirmed_records = [
            record
            for record in records
            if record.record_type in {"personal_skill", "project_skill", "plugin_skill"}
        ]
        candidate_records = [record for record in records if record.record_type == "candidate"]
        self.pages["skills"].set_records(confirmed_records)  # type: ignore[attr-defined]
        self.pages["candidates"].set_fast_candidates(candidate_records)  # type: ignore[attr-defined]
        summary = ScanSummary.from_dict(raw_summary)
        self.pages["dashboard"].set_summary(summary, records)  # type: ignore[attr-defined]

    def _load_shadow_results(self) -> None:
        shadow_records = self.repository.load_shadow_pool()
        self.pages["candidates"].set_shadow_candidates(shadow_records)  # type: ignore[attr-defined]
