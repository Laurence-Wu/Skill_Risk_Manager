from __future__ import annotations

import copy
import queue
import threading
import time
from pathlib import Path
from typing import Callable

from ui.core.events import (
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
from ui.core.exporters import export_logs_to_csv, export_risk_report_to_csv, export_skills_to_csv
from ui.core.progress import (
    CONTINUATION_PROGRESS_RANGE,
    SNAPSHOT_PROGRESS,
    continuation_scan_progress,
    expected_total_files,
    primary_scan_progress,
    snapshot_expected_total,
)
from ui.core.record_mapping import (
    candidate_from_backend_payload,
    candidate_records,
    command_records,
    config_records,
    confirmed_skill_records,
)
from ui.core.state import AppState
from ui.models import CandidateRecord
from skill_risk_manager.risk.policy import preset_for_security_level
from skill_risk_manager.backend import ScanService
from skill_risk_manager.backend.models import CancelToken, ScanConfig, ScanEvent as BackendScanEvent
from platform_manager import get_platform_adapter
from platform_manager.base import PlatformAdapter
from skill_risk_manager.storage.repository import Repository


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
        self._primary_files_checked = 0
        self._primary_directories_checked = 0
        self._primary_potential_items = 0
        self._load_existing_repository_state()

    def start_scan(self, scope: Path | None = None) -> bool:
        if self.is_running:
            self._state.add_log("warning", "A scan is already running.")
            return False
        self._fast_cancel_token = CancelToken()
        self._continuation_cancel_token = CancelToken()
        self._primary_files_checked = 0
        self._primary_directories_checked = 0
        self._primary_potential_items = 0
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
        export_logs_to_csv(self._state.logs, target_path)
        self._state.add_log("success", f"Exported logs: {target_path}")
        return target_path

    def export_skills(self, output_path: Path | None = None) -> Path:
        target_path = output_path or (
            self.repository.logs_dir / f"manager_gui_skills_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        )
        export_skills_to_csv(self._state.confirmed_skills, target_path)
        self._state.add_log("success", f"Exported skills: {target_path}")
        return target_path

    def export_risk_report(self, output_path: Path | None = None) -> Path:
        target_path = output_path or (
            self.repository.logs_dir / f"manager_gui_risk_report_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        )
        export_risk_report_to_csv(self._state, target_path)
        self._state.add_log("success", f"Exported risk report: {target_path}")
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

    def save_config(self) -> None:
        self._state.add_log("info", "Config save is not required in this prototype.")

    def poll_events(
        self,
        *,
        max_backend_events: int | None = None,
        max_ui_events: int | None = None,
    ) -> list[ScanEvent]:
        self._drain_backend_events(max_backend_events)
        events: list[ScanEvent] = []
        pending_progress: ScanEvent | None = None
        processed = 0
        while True:
            if max_ui_events is not None and processed >= max_ui_events:
                break
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                break
            processed += 1
            if event.type in {SCAN_PROGRESS, CONTINUATION_PROGRESS}:
                pending_progress = event
                continue
            if pending_progress:
                self._state.apply_event(pending_progress)
                events.append(pending_progress)
                pending_progress = None
            self._state.apply_event(event)
            events.append(event)
        if pending_progress:
            self._state.apply_event(pending_progress)
            events.append(pending_progress)
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
                previous_risk_preset = self.service.config.risk_preset
                self.service.config.respect_hard_ignores = security_level != "advanced"
                self.service.config.risk_preset = preset_for_security_level(security_level)
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
                    self.service.config.risk_preset = previous_risk_preset
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

    def _drain_backend_events(self, max_events: int | None = None) -> None:
        pending_progress: BackendScanEvent | None = None
        processed = 0
        while True:
            if max_events is not None and processed >= max_events:
                break
            try:
                event = self._backend_events.get_nowait()
            except queue.Empty:
                break
            processed += 1
            if event.event_type in {"foreground_progress", "shadow_progress"}:
                pending_progress = event
                continue
            if pending_progress:
                self._convert_backend_event(pending_progress)
                pending_progress = None
            self._convert_backend_event(event)
        if pending_progress:
            self._convert_backend_event(pending_progress)

    def _convert_backend_event(self, event: BackendScanEvent) -> None:
        event_type = event.event_type
        payload = event.payload or {}
        if event_type == "foreground_started":
            self._emit(SCAN_PROGRESS, "Current activity", progress=0.02, payload={"progress_mode": "primary"})
            return
        if event_type == "foreground_progress":
            files_checked = int(payload.get("files_checked", 0))
            directories_checked = int(payload.get("directories_checked", 0))
            potential_items = int(payload.get("potential_found", 0))
            overall_progress, phase_progress = primary_scan_progress(payload)
            self._primary_files_checked = max(self._primary_files_checked, files_checked)
            self._primary_directories_checked = max(self._primary_directories_checked, directories_checked)
            self._primary_potential_items = max(self._primary_potential_items, potential_items)
            self._emit(
                SCAN_PROGRESS,
                str(payload.get("current_phase") or "Current activity"),
                progress=overall_progress,
                current_path=str(payload.get("formatted_path") or payload.get("current_path") or ""),
                files_checked=files_checked,
                directories_checked=directories_checked,
                potential_items=potential_items,
                payload={
                    "progress_mode": "primary",
                    "expected_total_files": expected_total_files(files_checked, phase_progress),
                },
            )
            return
        if event_type == "snapshot_saved":
            snapshot = self.repository.load_snapshot()
            self._primary_files_checked = max(self._primary_files_checked, int(payload.get("files_checked", 0)))
            self._primary_directories_checked = max(
                self._primary_directories_checked,
                int(payload.get("directories_checked", 0)),
            )
            self._emit(
                SNAPSHOT_COMMITTED,
                "Stable snapshot saved",
                progress=SNAPSHOT_PROGRESS,
                files_checked=self._primary_files_checked,
                directories_checked=self._primary_directories_checked,
                potential_items=self._primary_potential_items,
                payload={
                    "confirmed_skills": confirmed_skill_records(snapshot),
                    "commands": command_records(snapshot),
                    "config_files": config_records(snapshot),
                    "candidates_snapshot": candidate_records(snapshot, "snapshot"),
                    "progress_mode": "primary",
                    "expected_total_files": snapshot_expected_total(self._primary_files_checked),
                },
            )
            return
        if event_type == "shadow_started":
            self._emit(
                CONTINUATION_STARTED,
                "Continuing at reduced budget",
                progress=SNAPSHOT_PROGRESS,
                files_checked=self._primary_files_checked,
                directories_checked=self._primary_directories_checked,
                potential_items=self._primary_potential_items,
                payload={
                    "progress_mode": "continuation",
                    "expected_total_files": snapshot_expected_total(self._primary_files_checked),
                },
            )
            return
        if event_type == "shadow_progress":
            continuation_files = int(payload.get("files_checked", 0))
            continuation_directories = int(payload.get("directories_checked", 0))
            continuation_potential = int(payload.get("candidates_found", 0)) + int(payload.get("confirmed_found", 0))
            global_files = self._primary_files_checked + continuation_files
            global_directories = self._primary_directories_checked + continuation_directories
            global_potential = self._primary_potential_items + continuation_potential
            overall_progress, phase_progress = continuation_scan_progress(payload)
            self._emit(
                CONTINUATION_PROGRESS,
                "Additional findings are being staged",
                progress=overall_progress,
                current_path=str(payload.get("formatted_path") or payload.get("current_path") or ""),
                files_checked=global_files,
                directories_checked=global_directories,
                potential_items=global_potential,
                payload={
                    "progress_mode": "continuation",
                    "expected_total_files": expected_total_files(
                        global_files,
                        SNAPSHOT_PROGRESS + phase_progress * CONTINUATION_PROGRESS_RANGE,
                    ),
                },
            )
            return
        if event_type == "shadow_candidate_found":
            record = candidate_from_backend_payload(payload, "continuation")
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
        self._state.confirmed_skills = confirmed_skill_records(snapshot)
        self._state.commands = command_records(snapshot)
        self._state.config_files = config_records(snapshot)
        self._state.candidates_snapshot = candidate_records(snapshot, "snapshot")
        self._load_shadow_pool_into_state()

    def _load_shadow_pool_into_state(self) -> None:
        self._state.candidates_staged = candidate_records(self.repository.load_shadow_pool(), "continuation")
