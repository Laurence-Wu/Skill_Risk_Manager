from __future__ import annotations

import queue
import time
from pathlib import Path

from skill_manager.backend.cache import file_hash, stat_matches_cache
from skill_manager.backend.classifier import Classification, classify_path
from skill_manager.backend.fast_exit import FastExitTracker, source_group_for_target
from skill_manager.backend.models import (
    CancelToken,
    ForegroundScanResult,
    ScanConfig,
    ScanEvent,
    ScanSummary,
    ScanTarget,
    SkillRecord,
)
from skill_manager.backend.parser import parse_markdown_header
from skill_manager.backend.priority_queue import ScanPriorityQueue
from skill_manager.backend.scanner_utils import (
    build_cache_record,
    cached_classification,
    deduplicate_records,
    is_generated_or_test_path,
    is_scan_candidate_path,
)
from skill_manager.platform.base import PlatformAdapter
from skill_manager.storage.repository import Repository


HIGH_VALUE_FILENAMES = {
    "skill.md",
    "claude.md",
    "claude.local.md",
    "settings.json",
    "settings.local.json",
    ".mcp.json",
    ".claude.json",
}
HIGH_VALUE_FOLDERS = {".claude", "skills", "plugins", "commands", "agents"}


class Stage1Scanner:
    def __init__(
        self,
        adapter: PlatformAdapter,
        repository: Repository,
        config: ScanConfig | None = None,
        event_queue: queue.Queue[ScanEvent] | None = None,
    ) -> None:
        self.adapter = adapter
        self.repository = repository
        self.config = config or ScanConfig()
        self.event_queue = event_queue
        self.records: list[SkillRecord] = []
        self.cache_updates: dict[str, dict] = {}
        self.remaining_targets: list[ScanTarget] = []
        self.files_checked = 0
        self.directories_checked = 0
        self.errors = 0
        self.visited_directories: set[str] = set()

    def run_foreground(
        self,
        targets: list[ScanTarget],
        cancel_token: CancelToken | None = None,
    ) -> ForegroundScanResult | None:
        started_at = time.time()
        scan_summary = ScanSummary(
            platform=self.adapter.name,
            started_at=started_at,
            foreground_status="running",
        )
        self._emit("foreground_started", "Foreground fast scan started")
        target_queue = ScanPriorityQueue(targets)
        cache = self.repository.load_cache()
        fast_exit = FastExitTracker(self.config)
        pending_inventory_targets = {
            self._target_key(target) for target in targets if target.scan_mode == "skill_inventory"
        }

        while len(target_queue) > 0:
            if cancel_token and cancel_token.cancelled:
                self._emit("foreground_cancelled", "Foreground fast scan cancelled")
                return None
            if cancel_token:
                cancel_token.wait_if_paused()
                if cancel_token.cancelled:
                    self._emit("foreground_cancelled", "Foreground fast scan cancelled")
                    return None

            target = target_queue.pop()
            fast_exit.mark_required_attempted(source_group_for_target(target.source_type))

            if target.priority <= self.config.shadow_priority_cutoff:
                self.remaining_targets.append(target)
                self.remaining_targets.extend(target_queue.to_list())
                break

            self._emit(
                "foreground_progress",
                "Scanning target",
                self._progress_payload(current_path=target.path, current_phase=target.reason),
            )
            self._scan_target_foreground(target, cache, fast_exit, cancel_token)
            pending_inventory_targets.discard(self._target_key(target))

            if not pending_inventory_targets and fast_exit.should_exit():
                self.remaining_targets.extend(target_queue.to_list())
                break

        deduped_records = self._deduplicate_records(self.records)
        sorted_records = sorted(
            deduped_records,
            key=lambda record: (-record.confidence, record.scope, record.name.lower(), str(record.path)),
        )
        scan_summary.finished_at = time.time()
        scan_summary.foreground_status = "complete"
        scan_summary.files_checked = self.files_checked
        scan_summary.directories_checked = self.directories_checked
        scan_summary.errors = self.errors
        scan_summary.remaining_shadow_targets = len(self.remaining_targets)
        self._fill_summary_counts(scan_summary, sorted_records)

        cache.update(self.cache_updates)
        self.repository.save_snapshot(sorted_records)
        self.repository.save_summary(scan_summary)
        self.repository.save_cache(cache)
        self.repository.append_scan_event(
            ScanEvent(
                "foreground_fast_exit",
                "Foreground fast scan produced stable snapshot",
                {
                    "files_checked": self.files_checked,
                    "records": len(sorted_records),
                    "remaining_shadow_targets": len(self.remaining_targets),
                },
            )
        )

        self._emit(
            "foreground_fast_exit",
            "Fast scan complete",
            {"records": len(sorted_records), "remaining_shadow_targets": len(self.remaining_targets)},
        )
        self._emit("snapshot_saved", "Stable Stage 1 snapshot saved", scan_summary.to_dict())
        self._emit("ui_results_ready", "Stable results are ready")

        return ForegroundScanResult(sorted_records, scan_summary, self.remaining_targets, self.cache_updates)

    def _scan_target_foreground(
        self,
        target: ScanTarget,
        cache: dict[str, dict],
        fast_exit: FastExitTracker,
        cancel_token: CancelToken | None,
    ) -> None:
        path = target.path
        if self._should_skip_path(path):
            return
        if not path.exists():
            return
        if target.scan_mode == "skill_inventory":
            self._scan_skill_inventory_target(target, cache, fast_exit, cancel_token)
            return
        if path.is_file():
            self._scan_file(path, target, cache, high_value=self._is_high_value_file(path), fast_exit=fast_exit)
            return
        self._scan_directory(path, target, cache, fast_exit, cancel_token)

    def _scan_skill_inventory_target(
        self,
        target: ScanTarget,
        cache: dict[str, dict],
        fast_exit: FastExitTracker,
        cancel_token: CancelToken | None,
    ) -> None:
        root_path = target.path
        if root_path.is_file():
            if root_path.name.lower() == "skill.md":
                self._scan_file(root_path, target, cache, high_value=True, fast_exit=fast_exit)
            return

        stack: list[tuple[Path, int]] = [(root_path, 0)]
        while stack:
            if cancel_token and cancel_token.cancelled:
                return
            if cancel_token:
                cancel_token.wait_if_paused()
                if cancel_token.cancelled:
                    return
            directory_path, depth = stack.pop()
            if self._should_skip_path(directory_path):
                continue
            if not self._mark_directory_seen(directory_path):
                continue
            try:
                entries = list(directory_path.iterdir())
            except PermissionError as error:
                self._record_error(directory_path, "PermissionError", str(error))
                continue
            except OSError as error:
                self._record_error(directory_path, error.__class__.__name__, str(error))
                continue

            self.directories_checked += 1
            entries.sort(key=self._entry_priority)

            for entry in entries:
                if cancel_token and cancel_token.cancelled:
                    return
                if cancel_token:
                    cancel_token.wait_if_paused()
                    if cancel_token.cancelled:
                        return
                if entry.is_dir():
                    if depth >= target.max_depth or self._should_skip_path(entry):
                        continue
                    stack.append((entry, depth + 1))
                    continue
                if entry.is_file() and entry.name.lower() == "skill.md":
                    self._scan_file(entry, target, cache, high_value=True, fast_exit=fast_exit)

    def _scan_directory(
        self,
        root_path: Path,
        target: ScanTarget,
        cache: dict[str, dict],
        fast_exit: FastExitTracker,
        cancel_token: CancelToken | None,
    ) -> None:
        stack: list[tuple[Path, int]] = [(root_path, 0)]
        while stack:
            if cancel_token and cancel_token.cancelled:
                return
            if cancel_token:
                cancel_token.wait_if_paused()
                if cancel_token.cancelled:
                    return
            directory_path, depth = stack.pop()
            if self._should_skip_path(directory_path):
                continue
            if not self._mark_directory_seen(directory_path):
                continue
            try:
                entries = list(directory_path.iterdir())
            except PermissionError as error:
                self._record_error(directory_path, "PermissionError", str(error))
                continue
            except OSError as error:
                self._record_error(directory_path, error.__class__.__name__, str(error))
                continue

            self.directories_checked += 1
            entries.sort(key=self._entry_priority)

            for entry in entries:
                if cancel_token and cancel_token.cancelled:
                    return
                if cancel_token:
                    cancel_token.wait_if_paused()
                    if cancel_token.cancelled:
                        return
                if entry.is_dir():
                    if depth >= target.max_depth or self._should_skip_path(entry):
                        continue
                    stack.append((entry, depth + 1))
                    continue

                if not entry.is_file():
                    continue

                if (
                    self._is_high_value_file(entry)
                    or self._is_command_markdown(entry, target)
                    or self._is_metadata_markdown_in_high_value_folder(entry)
                ):
                    self._scan_file(entry, target, cache, high_value=True, fast_exit=fast_exit)
                elif self._is_deferred_candidate(entry):
                    self.remaining_targets.append(
                        ScanTarget(
                            entry,
                            self.config.shadow_priority_cutoff,
                            "deferred_candidate",
                            0,
                            "shadow",
                            "Deferred low-confidence candidate",
                        )
                    )

                if target.scan_mode != "skill_inventory" and fast_exit.should_exit():
                    return

    def _scan_file(
        self,
        path: Path,
        target: ScanTarget,
        cache: dict[str, dict],
        high_value: bool,
        fast_exit: FastExitTracker,
    ) -> None:
        self.files_checked += 1
        found_record = self._record_from_cache_or_parse(path, target, cache, high_value)
        if found_record:
            self.records.append(found_record)
        fast_exit.mark_checked(found_record is not None)
        self._emit(
            "foreground_progress",
            "Foreground progress",
            self._progress_payload(current_path=path, current_phase=target.reason),
        )

    def _record_from_cache_or_parse(
        self,
        path: Path,
        target: ScanTarget,
        cache: dict[str, dict],
        high_value: bool,
    ) -> SkillRecord | None:
        key = self.adapter.path_key(path)
        cache_record = cache.get(key)
        try:
            stat_result = path.stat()
        except OSError as error:
            self._record_error(path, error.__class__.__name__, str(error))
            return None

        if stat_matches_cache(path, cache_record):
            raw_cached_classification = cached_classification(cache_record)
            if raw_cached_classification:
                return SkillRecord.from_dict(raw_cached_classification)

        computed_hash = file_hash(path) if high_value else None
        if computed_hash and cache_record and computed_hash == cache_record.get("hash"):
            raw_cached_classification = cached_classification(cache_record)
            if raw_cached_classification:
                cached_record = SkillRecord.from_dict(raw_cached_classification)
                self.cache_updates[key] = build_cache_record(path, computed_hash, cached_record)
                return cached_record

        try:
            classification = self._classify_file(path, target)
        except UnicodeDecodeError as error:
            self._record_error(path, "UnicodeDecodeError", str(error))
            return None
        except OSError as error:
            self._record_error(path, error.__class__.__name__, str(error))
            return None

        if not computed_hash and high_value:
            computed_hash = file_hash(path)

        record = None
        if classification.status != "ignored" and classification.confidence > 0:
            record = SkillRecord(
                name=classification.name,
                record_type=classification.record_type,
                scope=classification.scope,
                path=path,
                source_type=target.source_type,
                confidence=classification.confidence,
                last_modified=stat_result.st_mtime,
                status=classification.status,
                file_hash=computed_hash,
                metadata=classification.metadata,
            )

        self.cache_updates[key] = build_cache_record(path, computed_hash, record)
        return record

    def _classify_file(self, path: Path, target: ScanTarget) -> Classification:
        if path.suffix.lower() == ".md":
            parsed_markdown = parse_markdown_header(path)
            return classify_path(path, target.source_type, parsed_markdown.frontmatter)
        return classify_path(path, target.source_type)

    def _deduplicate_records(self, records: list[SkillRecord]) -> list[SkillRecord]:
        return deduplicate_records(records, self.adapter)

    def _fill_summary_counts(self, summary: ScanSummary, records: list[SkillRecord]) -> None:
        summary.confirmed_skills = sum(
            1 for record in records if record.record_type in {"personal_skill", "project_skill", "plugin_skill"}
        )
        summary.candidates = sum(1 for record in records if record.record_type == "candidate")
        summary.legacy_commands = sum(1 for record in records if record.record_type == "legacy_command")
        summary.claude_configs = sum(
            1 for record in records if record.record_type in {"claude_config", "claude_memory"}
        )

    def _is_high_value_file(self, path: Path) -> bool:
        return path.name.lower() in HIGH_VALUE_FILENAMES

    def _is_command_markdown(self, path: Path, target: ScanTarget) -> bool:
        if path.suffix.lower() != ".md":
            return False
        parent_names = {part.lower() for part in path.parts}
        return target.source_type == "legacy_command" or "commands" in parent_names

    def _is_metadata_markdown_in_high_value_folder(self, path: Path) -> bool:
        if path.suffix.lower() != ".md":
            return False
        parent_names = {part.lower() for part in path.parts}
        metadata_folders = {"agents", "skills", "plugins", "prompts", "prompt"}
        return bool(metadata_folders.intersection(parent_names))

    def _is_deferred_candidate(self, path: Path) -> bool:
        return is_scan_candidate_path(path)

    def _entry_priority(self, path: Path) -> tuple[int, str]:
        if path.is_dir() and path.name.lower() in HIGH_VALUE_FOLDERS:
            return 0, path.name.lower()
        if path.is_file() and self._is_high_value_file(path):
            return 0, path.name.lower()
        return 1, path.name.lower()

    def _should_skip_path(self, path: Path) -> bool:
        if is_generated_or_test_path(path):
            return True
        try:
            if path.is_symlink():
                return True
        except OSError:
            return True
        try:
            return self.config.respect_hard_ignores and self.adapter.is_hard_ignored(path)
        except OSError:
            return False

    def _mark_directory_seen(self, path: Path) -> bool:
        try:
            directory_key = self.adapter.path_key(path)
        except OSError:
            return False
        if directory_key in self.visited_directories:
            return False
        self.visited_directories.add(directory_key)
        return True

    def _progress_payload(self, current_path: Path, current_phase: str) -> dict:
        return {
            "current_phase": current_phase,
            "current_path": str(current_path),
            "formatted_path": self.adapter.format_path(current_path),
            "files_checked": self.files_checked,
            "directories_checked": self.directories_checked,
            "potential_found": len(self.records),
            "potential_records": [record.to_dict() for record in self._deduplicate_records(self.records)[-25:]],
            "errors": self.errors,
        }

    def _record_error(self, path: Path, error_type: str, message: str) -> None:
        self.errors += 1
        self.repository.append_error(path, error_type, message)
        self._emit("scan_error", message, {"path": str(path), "error_type": error_type})

    def _emit(self, event_type: str, message: str = "", payload: dict | None = None) -> None:
        event = ScanEvent(event_type, message, payload or {})
        if self.event_queue:
            self.event_queue.put(event)

    def _target_key(self, target: ScanTarget) -> tuple[str, str, str]:
        return (self.adapter.path_key(target.path), target.source_type, target.scan_mode)
