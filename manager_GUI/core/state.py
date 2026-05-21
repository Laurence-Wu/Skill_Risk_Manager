from __future__ import annotations

import platform as platform_module
import time
from dataclasses import dataclass, field
from pathlib import Path

from manager_GUI.core.events import (
    CANDIDATE_STAGED,
    CONTINUATION_PROGRESS,
    CONTINUATION_STARTED,
    SCAN_CANCELLED,
    SCAN_COMPLETED,
    SCAN_ERROR,
    SCAN_PAUSED,
    SCAN_PROGRESS,
    SCAN_RESUMED,
    SCAN_STARTED,
    SCAN_WARNING,
    SNAPSHOT_COMMITTED,
    ScanEvent,
)
from manager_GUI.models import CandidateRecord, LogEntry, SkillRecord


@dataclass
class AppState:
    platform: str = field(default_factory=lambda: platform_module.system() or "Unknown")
    claude_config_root: str = field(default_factory=lambda: str(Path.home() / ".claude"))
    scan_status: str = "ready"
    progress: float = 0.0
    progress_mode: str = "primary"
    current_activity: str = "Ready"
    current_path: str = ""
    files_checked: int = 0
    expected_total_files: int = 0
    directories_checked: int = 0
    potential_items: int = 0
    confirmed_skills: list[SkillRecord] = field(default_factory=list)
    commands: list[SkillRecord] = field(default_factory=list)
    config_files: list[SkillRecord] = field(default_factory=list)
    candidates_snapshot: list[CandidateRecord] = field(default_factory=list)
    candidates_staged: list[CandidateRecord] = field(default_factory=list)
    ignored_candidates: list[CandidateRecord] = field(default_factory=list)
    logs: list[LogEntry] = field(default_factory=list)
    last_scan_time: float | None = None
    security_level: str = "base"
    lazy_updates_enabled: bool = False
    last_progress_log_time: float = 0.0

    @property
    def confirmed_count(self) -> int:
        return len(self.confirmed_skills)

    @property
    def candidate_count(self) -> int:
        return len(self.candidates_snapshot) + len(self.candidates_staged)

    @property
    def command_count(self) -> int:
        return len(self.commands)

    @property
    def config_count(self) -> int:
        return len(self.config_files)

    def apply_event(self, event: ScanEvent) -> None:
        if _should_log_event(self, event):
            self.add_log(_level_for_event(event), event.message, event.type, event.timestamp)

        if event.type == SCAN_STARTED:
            self._reset_scan()
            self.scan_status = "scanning"
            self.lazy_updates_enabled = False
            self.current_activity = event.message or "Current activity"
            return

        if event.type in {SCAN_PROGRESS, CONTINUATION_PROGRESS}:
            expected_total_files = int(event.payload.get("expected_total_files", 0) or 0)
            self.scan_status = "scanning"
            self.progress = max(self.progress, event.progress)
            self.progress_mode = event.payload.get("progress_mode", self.progress_mode)
            self.current_activity = event.message or "Current activity"
            self.current_path = event.current_path
            self.files_checked = max(self.files_checked, event.files_checked)
            self.expected_total_files = max(self.expected_total_files, expected_total_files, self.files_checked)
            self.directories_checked = max(self.directories_checked, event.directories_checked)
            self.potential_items = max(self.potential_items, event.potential_items)
            return

        if event.type == SNAPSHOT_COMMITTED:
            expected_total_files = int(event.payload.get("expected_total_files", 0) or 0)
            self.scan_status = "committed"
            self.progress = max(self.progress, event.progress or 0.72)
            self.progress_mode = "primary"
            self.lazy_updates_enabled = False
            self.current_activity = "Stable snapshot saved"
            self.files_checked = max(self.files_checked, event.files_checked)
            self.expected_total_files = max(self.expected_total_files, expected_total_files, self.files_checked)
            self.directories_checked = max(self.directories_checked, event.directories_checked)
            self.potential_items = max(self.potential_items, event.potential_items)
            self.confirmed_skills = list(event.payload.get("confirmed_skills", []))
            self.commands = list(event.payload.get("commands", []))
            self.config_files = list(event.payload.get("config_files", []))
            self.candidates_snapshot = list(event.payload.get("candidates_snapshot", []))
            self.last_scan_time = event.timestamp
            return

        if event.type == CONTINUATION_STARTED:
            expected_total_files = int(event.payload.get("expected_total_files", 0) or 0)
            self.scan_status = "scanning"
            self.progress = max(self.progress, event.progress)
            self.progress_mode = "continuation"
            self.lazy_updates_enabled = True
            self.current_activity = "Continuing at reduced budget"
            self.files_checked = max(self.files_checked, event.files_checked)
            self.expected_total_files = max(self.expected_total_files, expected_total_files, self.files_checked)
            self.directories_checked = max(self.directories_checked, event.directories_checked)
            self.potential_items = max(self.potential_items, event.potential_items)
            return

        if event.type == CANDIDATE_STAGED:
            candidate = event.payload.get("candidate")
            if isinstance(candidate, CandidateRecord):
                self.candidates_staged.append(candidate)
            self.current_activity = event.message or "Additional findings are being staged"
            return

        if event.type == SCAN_PAUSED:
            self.scan_status = "paused"
            self.current_activity = "Paused"
            return

        if event.type == SCAN_RESUMED:
            self.scan_status = "scanning"
            self.current_activity = "Current activity"
            return

        if event.type == SCAN_CANCELLED:
            self.scan_status = "cancelled"
            self.lazy_updates_enabled = False
            self.current_activity = "Cancelled"
            return

        if event.type == SCAN_COMPLETED:
            self.scan_status = "complete"
            self.progress = 1.0
            self.lazy_updates_enabled = False
            self.current_activity = "Scan complete"
            self.last_scan_time = event.timestamp
            return

        if event.type == SCAN_WARNING:
            self.current_activity = event.message or self.current_activity
            return

        if event.type == SCAN_ERROR:
            self.scan_status = "error"
            self.lazy_updates_enabled = False
            self.current_activity = "Error"

    def _reset_scan(self) -> None:
        self.progress = 0.0
        self.progress_mode = "primary"
        self.current_path = ""
        self.files_checked = 0
        self.expected_total_files = 0
        self.directories_checked = 0
        self.potential_items = 0
        self.confirmed_skills = []
        self.commands = []
        self.config_files = []
        self.candidates_snapshot = []
        self.candidates_staged = []
        self.lazy_updates_enabled = False

    def set_security_level(self, level: str) -> None:
        if level not in {"base", "advanced"}:
            return
        self.security_level = level
        label = "Base" if level == "base" else "Advanced"
        self.add_log("info", f"Security level set to {label}.")

    def add_log(
        self,
        level: str,
        message: str,
        event_type: str = "ui_action",
        timestamp: float | None = None,
    ) -> None:
        self.logs.append(LogEntry(level, message, time.time() if timestamp is None else timestamp, event_type))
        self.logs = self.logs[-400:]

    def clear_logs(self) -> None:
        self.logs = []

    def promote_candidate(self, candidate: CandidateRecord) -> None:
        if not self._remove_candidate(candidate):
            return
        name = _name_from_candidate_path(candidate.path)
        self.confirmed_skills.append(
            SkillRecord(
                name=name,
                scope="reviewed",
                record_type=candidate.suggested_type,
                path=candidate.path,
                confidence=candidate.confidence,
                status="valid",
                description=candidate.reason,
            )
        )
        self.add_log("success", f"Promoted candidate: {name}")

    def ignore_candidate(self, candidate: CandidateRecord) -> None:
        if not self._remove_candidate(candidate):
            return
        ignored = CandidateRecord(
            path=candidate.path,
            reason=candidate.reason,
            confidence=candidate.confidence,
            source=candidate.source,
            suggested_type=candidate.suggested_type,
            status="ignored",
        )
        self.ignored_candidates.append(ignored)
        self.add_log("warning", f"Ignored candidate: {candidate.path}")

    def _remove_candidate(self, candidate: CandidateRecord) -> bool:
        for records in [self.candidates_snapshot, self.candidates_staged, self.ignored_candidates]:
            for index, existing in enumerate(records):
                if existing.path == candidate.path:
                    records.pop(index)
                    return True
        return False


def _name_from_candidate_path(path_text: str) -> str:
    path = Path(path_text)
    if path.name.lower() == "skill.md" and path.parent.name:
        return path.parent.name
    return path.stem or path.name or "promoted-candidate"


def _level_for_event(event: ScanEvent) -> str:
    if event.type == SCAN_ERROR:
        return "error"
    if event.type in {SCAN_CANCELLED, SCAN_PAUSED, SCAN_WARNING}:
        return "warning"
    if event.type in {SNAPSHOT_COMMITTED, SCAN_COMPLETED, CANDIDATE_STAGED}:
        return "success"
    return "info"


def _should_log_event(state: AppState, event: ScanEvent) -> bool:
    if event.type in {SCAN_PROGRESS, CONTINUATION_PROGRESS}:
        if event.timestamp - state.last_progress_log_time >= 1.0:
            state.last_progress_log_time = event.timestamp
            return True
        return False
    if event.type == CANDIDATE_STAGED:
        staged_count = len(state.candidates_staged)
        return staged_count < 5 or staged_count % 25 == 0
    return True
