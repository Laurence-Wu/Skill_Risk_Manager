from __future__ import annotations

import queue
import string
from pathlib import Path

from skill_manager.backend.models import (
    CancelToken,
    ForegroundScanResult,
    ScanConfig,
    ScanEvent,
    ScanTarget,
    SkillRecord,
)
from skill_manager.backend.shadow_scanner import ShadowScanner
from skill_manager.backend.stage1_scanner import Stage1Scanner
from skill_manager.platform.base import PlatformAdapter
from skill_manager.storage.repository import Repository


class ScanService:
    """Application-facing scanner API for CLI and UI orchestration."""

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

    def build_targets(self, project_root: Path) -> list[ScanTarget]:
        return self.adapter.build_stage1_targets(project_root)

    def build_computer_scan_targets(self, security_level: str = "base") -> list[ScanTarget]:
        targets = self.adapter.build_stage1_targets(self.adapter.home_dir())
        for root_path in self._local_scan_roots(include_protected=security_level == "advanced"):
            targets.append(
                ScanTarget(
                    root_path,
                    self.config.shadow_priority_cutoff,
                    "computer_root",
                    16,
                    "shadow",
                    "Local computer scan",
                )
            )
        return self._dedupe_targets(targets)

    def run_fast_scan(
        self,
        project_root: Path,
        cancel_token: CancelToken | None = None,
    ) -> ForegroundScanResult | None:
        return self.run_foreground(self.build_targets(project_root), cancel_token)

    def run_foreground(
        self,
        targets: list[ScanTarget],
        cancel_token: CancelToken | None = None,
    ) -> ForegroundScanResult | None:
        scanner = Stage1Scanner(self.adapter, self.repository, self.config, self.event_queue)
        return scanner.run_foreground(targets, cancel_token)

    def run_computer_scan(
        self,
        *,
        security_level: str = "base",
        fast_cancel_token: CancelToken | None = None,
        shadow_cancel_token: CancelToken | None = None,
    ) -> ForegroundScanResult | None:
        previous_respect_hard_ignores = self.config.respect_hard_ignores
        self.config.respect_hard_ignores = security_level != "advanced"
        try:
            foreground_result = self.run_foreground(
                self.build_computer_scan_targets(security_level),
                fast_cancel_token,
            )
        finally:
            self.config.respect_hard_ignores = previous_respect_hard_ignores
        if foreground_result and not (fast_cancel_token and fast_cancel_token.cancelled):
            previous_respect_hard_ignores = self.config.respect_hard_ignores
            self.config.respect_hard_ignores = security_level != "advanced"
            try:
                self.run_shadow(foreground_result.remaining_targets, shadow_cancel_token)
            finally:
                self.config.respect_hard_ignores = previous_respect_hard_ignores
        return foreground_result

    def run_shadow(
        self,
        targets: list[ScanTarget],
        cancel_token: CancelToken | None = None,
    ) -> list[SkillRecord]:
        scanner = ShadowScanner(self.adapter, self.repository, self.config, self.event_queue)
        return scanner.run(targets, cancel_token or CancelToken())

    def run_pipeline(
        self,
        project_root: Path,
        *,
        stage1: bool = True,
        shadow: bool = False,
        fast_cancel_token: CancelToken | None = None,
        shadow_cancel_token: CancelToken | None = None,
    ) -> ForegroundScanResult | None:
        foreground_result = self.run_fast_scan(project_root, fast_cancel_token) if stage1 else None
        if shadow and foreground_result:
            self.run_shadow(foreground_result.remaining_targets, shadow_cancel_token)
        return foreground_result

    def _local_scan_roots(self, include_protected: bool = False) -> list[Path]:
        if self.adapter.name == "windows":
            roots = [Path(f"{letter}:\\") for letter in string.ascii_uppercase if Path(f"{letter}:\\").exists()]
            return [root for root in roots if include_protected or not self.adapter.is_hard_ignored(root)]
        roots = [Path("/")]
        volumes_path = Path("/Volumes")
        if self.adapter.name == "macos" and volumes_path.exists():
            try:
                roots.extend(path for path in volumes_path.iterdir() if path.is_dir())
            except OSError:
                pass
        return [
            root
            for root in roots
            if root.exists() and (include_protected or not self.adapter.is_hard_ignored(root))
        ]

    def _dedupe_targets(self, targets: list[ScanTarget]) -> list[ScanTarget]:
        deduped: dict[tuple[str, str, int], ScanTarget] = {}
        for target in targets:
            key = (self.adapter.path_key(target.path), target.source_type, target.priority)
            deduped.setdefault(key, target)
        return list(deduped.values())
