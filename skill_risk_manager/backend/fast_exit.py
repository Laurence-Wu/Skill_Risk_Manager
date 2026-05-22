from __future__ import annotations

import time
from collections import deque

from skill_risk_manager.backend.models import ScanConfig


class FastExitTracker:
    def __init__(self, config: ScanConfig) -> None:
        self.config = config
        self.started_at = time.time()
        self.total_checked = 0
        self.total_found = 0
        self.recent_findings: deque[bool] = deque(maxlen=config.recent_window_size)
        self.required_source_groups_done: set[str] = set()

    def mark_required_attempted(self, source_group: str) -> None:
        if source_group in self.config.required_source_groups:
            self.required_source_groups_done.add(source_group)

    def mark_checked(self, found: bool) -> None:
        self.total_checked += 1
        if found:
            self.total_found += 1
        self.recent_findings.append(found)

    def should_exit(self) -> bool:
        if not self._required_paths_done():
            return False
        if self.total_checked < self.config.min_checked_count:
            return False
        if time.time() - self.started_at < self.config.min_elapsed_seconds:
            return False
        if not self.recent_findings:
            return False
        if self.total_found == 0:
            return True

        average_rate = self.total_found / self.total_checked
        recent_rate = sum(1 for found in self.recent_findings if found) / len(self.recent_findings)
        return recent_rate < self.config.discovery_drop_ratio * average_rate

    def _required_paths_done(self) -> bool:
        return self.config.required_source_groups.issubset(self.required_source_groups_done)


def source_group_for_target(source_type: str) -> str:
    if source_type == "personal_skill":
        return "personal"
    if source_type == "project_skill":
        return "project"
    if source_type == "parent_project":
        return "parent"
    if source_type == "plugin_skill":
        return "plugin"
    if source_type == "legacy_command":
        return "command"
    return source_type

