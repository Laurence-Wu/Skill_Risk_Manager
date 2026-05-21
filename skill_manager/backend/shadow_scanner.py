from __future__ import annotations

import queue
import time
from pathlib import Path

from skill_manager.backend.cache import file_hash, stat_matches_cache
from skill_manager.backend.classifier import classify_path
from skill_manager.backend.models import CancelToken, ScanConfig, ScanEvent, ScanSummary, ScanTarget, SkillRecord
from skill_manager.backend.parser import parse_markdown_header
from skill_manager.backend.scanner_utils import (
    build_cache_record,
    cached_classification,
    deduplicate_records,
    is_generated_or_test_path,
    is_scan_candidate_path,
)
from skill_manager.platform.base import PlatformAdapter
from skill_manager.storage.repository import Repository


class ShadowScanner:
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
        self.files_checked = 0
        self.directories_checked = 0
        self.candidates_found = 0
        self.confirmed_found = 0
        self.started_at = 0.0

    def run(self, targets: list[ScanTarget], cancel_token: CancelToken) -> list[SkillRecord]:
        self.started_at = time.time()
        self._emit("shadow_started", "Shadow scan started")
        cache = self.repository.load_cache()
        shadow_records = self.repository.load_shadow_pool()

        for target in targets:
            if self._should_stop(cancel_token):
                break
            self._scan_target(target, cache, shadow_records, cancel_token)
            if self._budget_exhausted(shadow_records):
                break

        self.repository.save_cache(cache)
        self.repository.save_shadow_pool(self._deduplicate_records(shadow_records))
        summary = self.repository.load_summary()
        if summary:
            summary.shadow_status = "cancelled" if cancel_token.cancelled else "complete"
            self.repository.save_summary(summary)

        event_type = "shadow_cancelled" if cancel_token.cancelled else "shadow_finished"
        self._emit(event_type, "Shadow scan stopped" if cancel_token.cancelled else "Shadow scan complete")
        return shadow_records

    def _scan_target(
        self,
        target: ScanTarget,
        cache: dict[str, dict],
        shadow_records: list[SkillRecord],
        cancel_token: CancelToken,
    ) -> None:
        target_path = target.path
        if not target_path.exists() or self._should_skip_path(target_path):
            return
        if target_path.is_file():
            self._scan_file(target_path, target, cache, shadow_records)
            self._rate_limit(cancel_token)
            return

        stack: list[tuple[Path, int]] = [(target_path, 0)]
        while stack:
            if self._should_stop(cancel_token):
                return
            directory_path, depth = stack.pop()
            if self._should_skip_path(directory_path):
                continue
            try:
                entries = list(directory_path.iterdir())
            except PermissionError as error:
                self.repository.append_error(directory_path, "PermissionError", str(error))
                self._emit("scan_error", str(error), {"path": str(directory_path), "error_type": "PermissionError"})
                continue
            except OSError as error:
                self.repository.append_error(directory_path, error.__class__.__name__, str(error))
                self._emit("scan_error", str(error), {"path": str(directory_path), "error_type": error.__class__.__name__})
                continue

            self.directories_checked += 1
            for entry in entries:
                if self._should_stop(cancel_token):
                    return
                if entry.is_dir() and depth < target.max_depth and not self._should_skip_path(entry):
                    stack.append((entry, depth + 1))
                    continue
                if entry.is_file() and self._is_shadow_candidate(entry):
                    self._scan_file(entry, target, cache, shadow_records)
                    if self._budget_exhausted(shadow_records):
                        return
                    self._rate_limit(cancel_token)

    def _scan_file(
        self,
        path: Path,
        target: ScanTarget,
        cache: dict[str, dict],
        shadow_records: list[SkillRecord],
    ) -> None:
        self.files_checked += 1
        key = self.adapter.path_key(path)
        cache_record = cache.get(key)
        if stat_matches_cache(path, cache_record):
            raw_cached_classification = cached_classification(cache_record)
            if raw_cached_classification:
                record = SkillRecord.from_dict(raw_cached_classification)
                shadow_records.append(record)
                self._mark_found(record)
                self._emit_progress(path)
                return

        try:
            computed_hash = file_hash(path)
            raw_cached_classification = cached_classification(cache_record)
            if cache_record and computed_hash == cache_record.get("hash") and raw_cached_classification:
                record = SkillRecord.from_dict(raw_cached_classification)
                shadow_records.append(record)
                self._mark_found(record)
                cache[key] = build_cache_record(path, computed_hash, record)
                self._emit_progress(path)
                return

            frontmatter = parse_markdown_header(path).frontmatter if path.suffix.lower() == ".md" else {}
            classification = classify_path(path, target.source_type, frontmatter)
            record = None
            if classification.status != "ignored" and classification.confidence > 0:
                record = SkillRecord(
                    name=classification.name,
                    record_type=classification.record_type,
                    scope=classification.scope,
                    path=path,
                    source_type=target.source_type,
                    confidence=classification.confidence,
                    last_modified=path.stat().st_mtime,
                    status="shadow_staged",
                    file_hash=computed_hash,
                    metadata=classification.metadata,
                )
                shadow_records.append(record)
                self._mark_found(record)
                self.repository.save_shadow_pool(self._deduplicate_records(shadow_records))
                self._emit("shadow_candidate_found", "Shadow result staged", record.to_dict())
            cache[key] = build_cache_record(path, computed_hash, record)
        except OSError as error:
            self.repository.append_error(path, error.__class__.__name__, str(error))
            self._emit("scan_error", str(error), {"path": str(path), "error_type": error.__class__.__name__})
        self._emit_progress(path)

    def _mark_found(self, record: SkillRecord) -> None:
        if record.record_type in {"personal_skill", "project_skill", "plugin_skill"}:
            self.confirmed_found += 1
        else:
            self.candidates_found += 1

    def _deduplicate_records(self, records: list[SkillRecord]) -> list[SkillRecord]:
        return deduplicate_records(records, self.adapter)

    def _is_shadow_candidate(self, path: Path) -> bool:
        return is_scan_candidate_path(path)

    def _should_skip_path(self, path: Path) -> bool:
        if is_generated_or_test_path(path):
            return True
        try:
            return self.adapter.is_hard_ignored(path)
        except OSError:
            return False

    def _should_stop(self, cancel_token: CancelToken) -> bool:
        if cancel_token.cancelled:
            return True
        if cancel_token.paused:
            self._emit("shadow_paused", "Shadow scan paused")
            cancel_token.wait_if_paused()
            if not cancel_token.cancelled:
                self._emit("shadow_started", "Shadow scan resumed")
        return cancel_token.cancelled

    def _budget_exhausted(self, shadow_records: list[SkillRecord]) -> bool:
        runtime_exceeded = time.time() - self.started_at > self.config.shadow_max_runtime_seconds
        candidates_exceeded = len(shadow_records) >= self.config.shadow_max_candidates
        return runtime_exceeded or candidates_exceeded

    def _rate_limit(self, cancel_token: CancelToken) -> None:
        if self.files_checked and self.files_checked % self.config.shadow_batch_size == 0:
            self._emit_progress()
            time.sleep(self.config.shadow_sleep_seconds)
            cancel_token.wait_if_paused()

    def _emit_progress(self, path: Path | None = None) -> None:
        self._emit(
            "shadow_progress",
            "Shadow scan progress",
            {
                "current_path": str(path) if path else "",
                "formatted_path": self.adapter.format_path(path) if path else "",
                "files_checked": self.files_checked,
                "directories_checked": self.directories_checked,
                "candidates_found": self.candidates_found,
                "confirmed_found": self.confirmed_found,
            },
        )

    def _emit(self, event_type: str, message: str = "", payload: dict | None = None) -> None:
        event = ScanEvent(event_type, message, payload or {})
        if self.event_queue:
            self.event_queue.put(event)
