from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Event


@dataclass(frozen=True)
class ScanTarget:
    path: Path
    priority: int
    source_type: str
    max_depth: int
    scan_mode: str
    reason: str


@dataclass
class SkillRecord:
    name: str
    record_type: str
    scope: str
    path: Path
    source_type: str
    confidence: float
    last_modified: float
    status: str = "discovered"
    file_hash: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        raw_record = asdict(self)
        raw_record["path"] = str(self.path)
        return raw_record

    @classmethod
    def from_dict(cls, raw_record: dict) -> "SkillRecord":
        return cls(
            name=str(raw_record["name"]),
            record_type=str(raw_record["record_type"]),
            scope=str(raw_record["scope"]),
            path=Path(raw_record["path"]),
            source_type=str(raw_record.get("source_type", "")),
            confidence=float(raw_record["confidence"]),
            last_modified=float(raw_record.get("last_modified", 0)),
            status=str(raw_record.get("status", "discovered")),
            file_hash=raw_record.get("file_hash"),
            metadata=dict(raw_record.get("metadata", {})),
        )


@dataclass
class ScanEvent:
    event_type: str
    message: str = ""
    payload: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class ScanSummary:
    platform: str
    started_at: float
    finished_at: float | None = None
    foreground_status: str = "not_started"
    shadow_status: str = "not_started"
    files_checked: int = 0
    directories_checked: int = 0
    confirmed_skills: int = 0
    candidates: int = 0
    legacy_commands: int = 0
    claude_configs: int = 0
    errors: int = 0
    remaining_shadow_targets: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw_summary: dict) -> "ScanSummary":
        return cls(**raw_summary)


@dataclass
class ScanConfig:
    min_checked_count: int = 20
    min_elapsed_seconds: float = 0.25
    recent_window_size: int = 25
    discovery_drop_ratio: float = 0.10
    shadow_priority_cutoff: int = 30
    max_shadow_files_per_second: int = 100
    max_shadow_dirs_per_second: int = 60
    shadow_batch_size: int = 100
    shadow_sleep_seconds: float = 0.05
    shadow_max_runtime_seconds: float = 300.0
    shadow_max_candidates: int = 1000
    respect_hard_ignores: bool = True
    risk_preset: str = "base"
    required_source_groups: set[str] = field(
        default_factory=lambda: {"personal", "project", "parent", "plugin", "command"}
    )


@dataclass
class ForegroundScanResult:
    records: list[SkillRecord]
    summary: ScanSummary
    remaining_targets: list[ScanTarget]
    cache_updates: dict[str, dict]


class CancelToken:
    def __init__(self) -> None:
        self._cancelled = Event()
        self._paused = Event()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    @property
    def paused(self) -> bool:
        return self._paused.is_set()

    def cancel(self) -> None:
        self._cancelled.set()

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def wait_if_paused(self, sleep_seconds: float = 0.1) -> None:
        while self.paused and not self.cancelled:
            time.sleep(sleep_seconds)
