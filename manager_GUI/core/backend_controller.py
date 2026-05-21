from __future__ import annotations

import copy
import csv
import queue
import threading
import time
from pathlib import Path
from typing import Callable

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
from manager_GUI.core.state import AppState
from manager_GUI.models import CandidateRecord, SkillRecord
from skill_manager.backend import ScanService
from skill_manager.backend.models import CancelToken, ScanConfig, ScanEvent as BackendScanEvent
from skill_manager.platform import get_platform_adapter
from skill_manager.platform.base import PlatformAdapter
from skill_manager.storage.repository import Repository


class BackendController:
    def __init__(
        self,
        *,
        adapter: PlatformAdapter | None = None,
        repository: Repository | None = None,
        service: ScanService | None = None,
        open_folder_callback: Callable[[Path], None] | None = None,
    ) -> None:
        self.adapter = adapter or get_platform_adapter()
        self.repository = repository or Repository.default()
        self._backend_events: queue.Queue[BackendScanEvent] = queue.Queue()
        self.service = service or ScanService(
            self.adapter,
            self.repository,
            ScanConfig(min_elapsed_seconds=0),
            self._backend_events,
        )
        self._events: queue.Queue[ScanEvent] = queue.Queue()
        self._state = AppState(
            platform=self.adapter.name,
            claude_config_root=self.adapter.format_path(self.adapter.claude_config_root()),
        )
        self._worker: threading.Thread | None = None
        self._fast_cancel_token = CancelToken()
        self._continuation_cancel_token = CancelToken()
        self._open_folder_callback = open_folder_callback or self.adapter.open_folder
        self._load_existing_repository_state()

    def start_scan(self, scope: Path | None = None) -> bool:
        if self.is_running:
            self._state.add_log("warning", "A scan is already running.")
            return False
        self._fast_cancel_token = CancelToken()
        self._continuation_cancel_token = CancelToken()
        self._worker = threading.Thread(target=self._run_scan, args=(scope,), daemon=True)
        self._worker.start()
        return True

    def cancel_scan(self) -> None:
        if not self.is_running:
            self._state.add_log("warning", "No scan is running.")
            return
        self._fast_cancel_token.cancel()
        self._continuation_cancel_token.cancel()
        self._emit(SCAN_CANCELLED, "Scan cancelled", progress=self._state.progress)

    def pause_scan(self) -> None:
        if not self.is_running:
            self._state.add_log("warning", "No scan is running.")
            return
        self._fast_cancel_token.pause()
        self._continuation_cancel_token.pause()
        self._emit(SCAN_PAUSED, "Paused", progress=self._state.progress)

    def resume_scan(self) -> None:
        if not self.is_running:
            self._state.add_log("warning", "No scan is running.")
            return
        self._fast_cancel_token.resume()
        self._continuation_cancel_token.resume()
        self._emit(SCAN_RESUMED, "Resumed", progress=self._state.progress)

    def set_security_level(self, level: str) -> None:
        if self.is_running:
            self._state.add_log("warning", "Security level can be changed after the current scan finishes.")
            return
        self._state.set_security_level(level)

    def promote_candidate(self, candidate: CandidateRecord) -> None:
        self._state.promote_candidate(candidate)

    def ignore_candidate(self, candidate: CandidateRecord) -> None:
        self._state.ignore_candidate(candidate)

    def copy_path(self, path_text: str, clipboard_set: Callable[[str], None] | None = None) -> None:
        if clipboard_set:
            clipboard_set(path_text)
        self._state.add_log("success", f"Copied path: {path_text}")

    def open_folder(self, path_text: str) -> None:
        path = Path(path_text).expanduser()
        target = path if path.is_dir() else path.parent
        if not target.exists():
            self._state.add_log("warning", f"Folder does not exist: {target}")
            return
        try:
            self._open_folder_callback(target)
        except Exception as error:  # pragma: no cover - OS launcher behavior
            self._state.add_log("error", f"Could not open folder: {error}")
            return
        self._state.add_log("success", f"Opened folder: {target}")

    def clear_logs(self) -> None:
        self._state.clear_logs()

    def export_logs(self, output_path: Path | None = None) -> Path:
        target_path = output_path or (
            self.repository.logs_dir / f"manager_gui_events_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=["timestamp", "level", "event_type", "message"])
            writer.writeheader()
            for log in self._state.logs:
                writer.writerow(
                    {
                        "timestamp": log.timestamp,
                        "level": log.level,
                        "event_type": log.event_type,
                        "message": log.message,
                    }
                )
        self._state.add_log("success", f"Exported logs: {target_path}")
        return target_path

    def open_logs_folder(self) -> None:
        if not self.repository.logs_dir.exists():
            self._state.add_log("warning", f"Logs folder does not exist: {self.repository.logs_dir}")
            return
        try:
            self._open_folder_callback(self.repository.logs_dir)
        except Exception as error:  # pragma: no cover - OS launcher behavior
            self._state.add_log("error", f"Could not open logs folder: {error}")
            return
        self._state.add_log("success", f"Opened logs folder: {self.repository.logs_dir}")

    def poll_events(self) -> list[ScanEvent]:
        self._drain_backend_events()
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

    def _run_scan(self, scope: Path | None) -> None:
        try:
            self._emit(SCAN_STARTED, "Current activity", progress=0.0, payload={"progress_mode": "primary"})
            security_level = self._state.security_level
            if scope:
                previous_respect_hard_ignores = self.service.config.respect_hard_ignores
                self.service.config.respect_hard_ignores = security_level != "advanced"
                try:
                    foreground_result = self.service.run_pipeline(
                        scope,
                        stage1=True,
                        shadow=True,
                        fast_cancel_token=self._fast_cancel_token,
                        shadow_cancel_token=self._continuation_cancel_token,
                    )
                finally:
                    self.service.config.respect_hard_ignores = previous_respect_hard_ignores
            else:
                foreground_result = self.service.run_computer_scan(
                    security_level=security_level,
                    fast_cancel_token=self._fast_cancel_token,
                    shadow_cancel_token=self._continuation_cancel_token,
                )
            if foreground_result is None and (
                self._fast_cancel_token.cancelled or self._continuation_cancel_token.cancelled
            ):
                self._emit(SCAN_CANCELLED, "Scan cancelled", progress=self._state.progress)
        except Exception as error:
            self._emit(SCAN_ERROR, f"Scan failed: {error}")

    def _drain_backend_events(self) -> None:
        while True:
            try:
                event = self._backend_events.get_nowait()
            except queue.Empty:
                break
            self._convert_backend_event(event)

    def _convert_backend_event(self, event: BackendScanEvent) -> None:
        event_type = event.event_type
        payload = event.payload or {}
        if event_type == "foreground_started":
            self._emit(SCAN_PROGRESS, "Current activity", progress=0.02, payload={"progress_mode": "primary"})
            return
        if event_type == "foreground_progress":
            self._emit(
                SCAN_PROGRESS,
                str(payload.get("current_phase") or "Current activity"),
                progress=_estimated_progress(payload, 0.9),
                current_path=str(payload.get("formatted_path") or payload.get("current_path") or ""),
                files_checked=int(payload.get("files_checked", 0)),
                directories_checked=int(payload.get("directories_checked", 0)),
                potential_items=int(payload.get("potential_found", 0)),
                payload={"progress_mode": "primary"},
            )
            return
        if event_type == "snapshot_saved":
            snapshot = self.repository.load_snapshot()
            self._emit(
                SNAPSHOT_COMMITTED,
                "Stable snapshot saved",
                progress=1.0,
                payload={
                    "confirmed_skills": _confirmed_skill_records(snapshot),
                    "commands": _records_by_type(snapshot, {"legacy_command"}),
                    "config_files": _records_by_type(snapshot, {"claude_config", "managed_config"}),
                    "candidates_snapshot": _candidate_records(snapshot, "snapshot"),
                    "progress_mode": "primary",
                },
            )
            return
        if event_type == "shadow_started":
            self._emit(
                CONTINUATION_STARTED,
                "Continuing at reduced budget",
                progress=0.0,
                payload={"progress_mode": "continuation"},
            )
            return
        if event_type == "shadow_progress":
            self._emit(
                CONTINUATION_PROGRESS,
                "Additional findings are being staged",
                progress=_estimated_progress(payload, 0.95),
                current_path=str(payload.get("formatted_path") or payload.get("current_path") or ""),
                files_checked=int(payload.get("files_checked", 0)),
                directories_checked=int(payload.get("directories_checked", 0)),
                potential_items=int(payload.get("candidates_found", 0)) + int(payload.get("confirmed_found", 0)),
                payload={"progress_mode": "continuation"},
            )
            return
        if event_type == "shadow_candidate_found":
            record = _candidate_from_backend_payload(payload, "continuation")
            if record:
                self._emit(
                    CANDIDATE_STAGED,
                    "Candidate staged for review",
                    progress=self._state.progress,
                    current_path=record.path,
                    payload={"candidate": record, "progress_mode": "continuation"},
                )
            return
        if event_type == "shadow_paused":
            self._emit(SCAN_PAUSED, "Paused", progress=self._state.progress)
            return
        if event_type in {"foreground_cancelled", "shadow_cancelled"}:
            self._emit(SCAN_CANCELLED, "Scan cancelled", progress=self._state.progress)
            return
        if event_type == "shadow_finished":
            self._load_shadow_pool_into_state()
            self._emit(
                SCAN_COMPLETED,
                "Scan complete",
                progress=1.0,
                payload={"progress_mode": "continuation"},
            )
            return
        if event_type == "scan_error":
            self._emit(SCAN_WARNING, event.message or "Scan warning", current_path=str(payload.get("path", "")))

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

    def _load_existing_repository_state(self) -> None:
        snapshot = self.repository.load_snapshot()
        self._state.confirmed_skills = _confirmed_skill_records(snapshot)
        self._state.commands = _records_by_type(snapshot, {"legacy_command"})
        self._state.config_files = _records_by_type(snapshot, {"claude_config", "managed_config"})
        self._state.candidates_snapshot = _candidate_records(snapshot, "snapshot")
        self._load_shadow_pool_into_state()

    def _load_shadow_pool_into_state(self) -> None:
        self._state.candidates_staged = _candidate_records(self.repository.load_shadow_pool(), "continuation")


def _estimated_progress(payload: dict, cap: float) -> float:
    files_checked = int(payload.get("files_checked", 0))
    directories_checked = int(payload.get("directories_checked", 0))
    estimate = (files_checked + directories_checked) / 500
    return max(0.02, min(cap, estimate))


def _confirmed_skill_records(records: list) -> list[SkillRecord]:
    return [
        _skill_from_backend_record(record)
        for record in records
        if getattr(record, "record_type", "") in {"personal_skill", "project_skill", "plugin_skill"}
    ]


def _records_by_type(records: list, record_types: set[str]) -> list[SkillRecord]:
    return [
        _skill_from_backend_record(record)
        for record in records
        if getattr(record, "record_type", "") in record_types
    ]


def _candidate_records(records: list, source: str) -> list[CandidateRecord]:
    return [
        _candidate_from_backend_record(record, source)
        for record in records
        if getattr(record, "record_type", "") == "candidate"
    ]


def _skill_from_backend_record(record) -> SkillRecord:
    metadata = getattr(record, "metadata", {}) or {}
    return SkillRecord(
        name=record.name,
        scope=record.scope,
        record_type=record.record_type,
        path=str(record.path),
        confidence=record.confidence,
        status=record.status,
        description=str(metadata.get("description") or metadata.get("summary") or ""),
    )


def _candidate_from_backend_record(record, source: str) -> CandidateRecord:
    metadata = getattr(record, "metadata", {}) or {}
    return CandidateRecord(
        path=str(record.path),
        reason=str(metadata.get("classification_reason") or record.record_type),
        confidence=record.confidence,
        source=source,
        suggested_type=record.record_type,
        status="staged" if source == "continuation" else "warning",
    )


def _candidate_from_backend_payload(payload: dict, source: str) -> CandidateRecord | None:
    if not payload:
        return None
    metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata", {}), dict) else {}
    return CandidateRecord(
        path=str(payload.get("path", "")),
        reason=str(metadata.get("classification_reason") or payload.get("record_type") or "candidate"),
        confidence=float(payload.get("confidence", 0)),
        source=source,
        suggested_type=str(payload.get("record_type", "candidate")),
        status="staged",
    )
