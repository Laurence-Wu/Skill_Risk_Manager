from __future__ import annotations

import queue
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
