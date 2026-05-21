from __future__ import annotations

import copy
import platform as platform_module
import queue
import threading
import time
from pathlib import Path

from manager_GUI.core.events import (
    CANDIDATE_STAGED,
    CONTINUATION_PROGRESS,
    CONTINUATION_STARTED,
    SCAN_CANCELLED,
    SCAN_COMPLETED,
    SCAN_PAUSED,
    SCAN_PROGRESS,
    SCAN_RESUMED,
    SCAN_STARTED,
    SNAPSHOT_COMMITTED,
    ScanEvent,
)
from manager_GUI.core.state import AppState
from manager_GUI.models import CandidateRecord, SkillRecord


class MockController:
    def __init__(self, phase_delay_seconds: float = 0.35) -> None:
        self._events: queue.Queue[ScanEvent] = queue.Queue()
        self._state = AppState()
        self._phase_delay_seconds = phase_delay_seconds
        self._worker: threading.Thread | None = None
        self._cancelled = threading.Event()
        self._paused = threading.Event()

    def start_scan(self) -> bool:
        if self._worker and self._worker.is_alive():
            return False
        self._cancelled.clear()
        self._paused.clear()
        self._worker = threading.Thread(target=self._run_scan, daemon=True)
        self._worker.start()
        return True

    def cancel_scan(self) -> None:
        if not self.is_running:
            return
        self._cancelled.set()
        self._paused.clear()
        self._emit(SCAN_CANCELLED, "Scan cancelled", progress=self._state.progress)

    def pause_scan(self) -> None:
        if not self.is_running:
            return
        self._paused.set()
        self._emit(SCAN_PAUSED, "Paused", progress=self._state.progress)

    def resume_scan(self) -> None:
        if not self.is_running:
            return
        self._paused.clear()
        self._emit(SCAN_RESUMED, "Resumed", progress=self._state.progress)

    def poll_events(self) -> list[ScanEvent]:
        events: list[ScanEvent] = []
        while True:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                break
            self._state.apply_event(event)
            events.append(event)
        return events

    def get_state(self) -> AppState:
        return copy.copy(self._state)

    @property
    def is_running(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def _run_scan(self) -> None:
        self._emit(SCAN_STARTED, "Current activity", progress=0.0)
        primary_steps = [
            ("Resolving Claude config root", self._sample_path(".claude"), 0.08, 12, 4, 0),
            ("Checking personal skill folders", self._sample_skill_path("summarize-changes", personal=True), 0.22, 70, 18, 2),
            ("Checking project Claude folders", self._sample_skill_path("repo-review", personal=False), 0.38, 132, 34, 3),
            ("Checking plugin skill folders", self._sample_path(".claude/plugins"), 0.54, 188, 52, 4),
            ("Checking legacy command files", self._sample_path(".claude/commands"), 0.72, 235, 63, 5),
            ("Checking shallow project roots", self._sample_path("Projects/demo"), 0.9, 286, 78, 7),
        ]

        for message, path, progress, files, dirs, potential in primary_steps:
            if not self._wait_if_needed():
                return
            self._emit(
                SCAN_PROGRESS,
                message,
                progress=progress,
                current_path=path,
                files_checked=files,
                directories_checked=dirs,
                potential_items=potential,
                payload={"progress_mode": "primary"},
            )

        skills = self._sample_skills()
        snapshot_candidates = self._snapshot_candidates()
        self._emit(
            SNAPSHOT_COMMITTED,
            "Stable snapshot saved",
            progress=1.0,
            current_path=self._sample_path(".claude"),
            files_checked=302,
            directories_checked=84,
            potential_items=9,
            payload={"confirmed_skills": skills, "candidates_snapshot": snapshot_candidates},
        )

        if not self._wait_if_needed():
            return
        self._emit(
            CONTINUATION_STARTED,
            "Continuing at reduced budget",
            progress=0.0,
            payload={"progress_mode": "continuation"},
        )

        staged = self._staged_candidates()
        for index, candidate in enumerate(staged, start=1):
            if not self._wait_if_needed():
                return
            progress = index / (len(staged) + 1)
            self._emit(
                CONTINUATION_PROGRESS,
                "Additional findings are being staged",
                progress=progress,
                current_path=candidate.path,
                files_checked=302 + index * 28,
                directories_checked=84 + index * 7,
                potential_items=9 + index,
                payload={"progress_mode": "continuation"},
            )
            self._emit(
                CANDIDATE_STAGED,
                "Candidate staged for review",
                progress=progress,
                current_path=candidate.path,
                files_checked=302 + index * 28,
                directories_checked=84 + index * 7,
                potential_items=9 + index,
                payload={"candidate": candidate, "progress_mode": "continuation"},
            )

        if self._cancelled.is_set():
            return
        self._emit(
            SCAN_COMPLETED,
            "Scan complete",
            progress=1.0,
            current_path=self._sample_path(".claude"),
            files_checked=372,
            directories_checked=101,
            potential_items=11,
            payload={"progress_mode": "continuation"},
        )

    def _wait_if_needed(self) -> bool:
        deadline = time.monotonic() + self._phase_delay_seconds
        while time.monotonic() < deadline:
            if self._cancelled.is_set():
                return False
            while self._paused.is_set() and not self._cancelled.is_set():
                time.sleep(0.05)
            time.sleep(0.03)
        return not self._cancelled.is_set()

    def _emit(
        self,
        event_type: str,
        message: str,
        *,
        progress: float = 0.0,
        current_path: str = "",
        files_checked: int = 0,
        directories_checked: int = 0,
        potential_items: int = 0,
        payload: dict | None = None,
    ) -> None:
        self._events.put(
            ScanEvent(
                type=event_type,
                message=message,
                progress=progress,
                current_path=current_path,
                files_checked=files_checked,
                directories_checked=directories_checked,
                potential_items=potential_items,
                payload=payload or {},
            )
        )

    def _sample_skills(self) -> list[SkillRecord]:
        return [
            SkillRecord("summarize-changes", "personal", "personal_skill", self._sample_skill_path("summarize-changes", True), 0.98, "valid", "Summarizes local changes before handoff."),
            SkillRecord("pdf-processor", "project", "project_skill", self._sample_skill_path("pdf-processor", False), 0.96, "valid", "Processes PDF content."),
            SkillRecord("repo-review", "project", "project_skill", self._sample_skill_path("repo-review", False), 0.95, "valid", "Reviews repository risk."),
            SkillRecord("latex-helper", "plugin", "plugin_skill", self._sample_skill_path("latex-helper", True), 0.94, "valid", "Assists with document builds."),
            SkillRecord("deployment-checklist", "personal", "personal_skill", self._sample_skill_path("deployment-checklist", True), 0.93, "valid", "Checks release readiness."),
        ]

    def _snapshot_candidates(self) -> list[CandidateRecord]:
        return [
            CandidateRecord(self._sample_path(".claude/commands/old-build.md"), "Old command markdown", 0.72, "snapshot", "legacy_command", "warning"),
            CandidateRecord(self._sample_path("Projects/demo/SKILL.md"), "Nonstandard SKILL.md location", 0.68, "snapshot", "candidate_skill", "warning"),
        ]

    def _staged_candidates(self) -> list[CandidateRecord]:
        return [
            CandidateRecord(self._sample_path("Documents/prompts/release.md"), "Prompt-like markdown", 0.61, "continuation", "candidate", "staged"),
            CandidateRecord(self._sample_path(".claude/plugins/example/agent.md"), "Plugin candidate", 0.59, "continuation", "plugin_candidate", "staged"),
        ]

    def _sample_skill_path(self, skill_name: str, personal: bool) -> str:
        if personal:
            return str(Path.home() / ".claude" / "skills" / skill_name / "SKILL.md")
        return str(Path.home() / "Projects" / "demo" / ".claude" / "skills" / skill_name / "SKILL.md")

    def _sample_path(self, suffix: str) -> str:
        normalized_suffix = suffix.replace("/", "\\") if platform_module.system().lower() == "windows" else suffix
        return str(Path.home() / normalized_suffix)
