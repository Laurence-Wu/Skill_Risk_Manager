from __future__ import annotations

import queue
import threading
from pathlib import Path

from skill_manager.backend import ScanService
from skill_manager.backend.models import CancelToken, ScanConfig, ScanEvent, ScanTarget
from skill_manager.platform.base import PlatformAdapter
from skill_manager.storage.repository import Repository


class ScanController:
    def __init__(
        self,
        adapter: PlatformAdapter,
        repository: Repository,
        event_queue: queue.Queue[ScanEvent],
        config: ScanConfig | None = None,
    ) -> None:
        self.event_queue = event_queue
        self.service = ScanService(adapter, repository, config or ScanConfig(), event_queue)
        self.fast_cancel_token = CancelToken()
        self.shadow_cancel_token = CancelToken()
        self.fast_thread: threading.Thread | None = None
        self.shadow_thread: threading.Thread | None = None

    def start_fast_scan(self, project_root: Path) -> None:
        if self.fast_thread and self.fast_thread.is_alive():
            return
        self.fast_cancel_token = CancelToken()
        self.fast_thread = threading.Thread(target=self._run_fast_scan, args=(project_root,), daemon=True)
        self.fast_thread.start()

    def cancel_fast_scan(self) -> None:
        self.fast_cancel_token.cancel()

    def pause_shadow_scan(self) -> None:
        self.shadow_cancel_token.pause()

    def resume_shadow_scan(self) -> None:
        self.shadow_cancel_token.resume()

    def cancel_shadow_scan(self) -> None:
        self.shadow_cancel_token.cancel()

    def _run_fast_scan(self, project_root: Path) -> None:
        result = self.service.run_fast_scan(project_root, self.fast_cancel_token)
        if result and not self.fast_cancel_token.cancelled:
            self.start_shadow_scan(result.remaining_targets)

    def start_shadow_scan(self, targets: list[ScanTarget]) -> None:
        if self.shadow_thread and self.shadow_thread.is_alive():
            return
        self.shadow_cancel_token = CancelToken()
        if not targets:
            self.event_queue.put(ScanEvent("shadow_finished", "No shadow targets remaining"))
            return
        self.shadow_thread = threading.Thread(target=self._run_shadow_scan, args=(targets,), daemon=True)
        self.shadow_thread.start()

    def _run_shadow_scan(self, targets: list[ScanTarget]) -> None:
        self.service.run_shadow(targets, self.shadow_cancel_token)
