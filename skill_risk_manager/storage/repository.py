from __future__ import annotations

import json
import time
from pathlib import Path

from skill_risk_manager.backend.models import ScanEvent, ScanSummary, SkillRecord
from skill_risk_manager.storage.csv_store import CsvStore
from skill_risk_manager.storage.json_store import JsonStore


class Repository:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.data_dir = root_dir / "data"
        self.logs_dir = root_dir / "logs"
        self.json_store = JsonStore()
        self.csv_store = CsvStore()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def default(cls) -> "Repository":
        return cls(Path(__file__).resolve().parents[2] / "public")

    @property
    def snapshot_path(self) -> Path:
        return self.data_dir / "stage1_snapshot.json"

    @property
    def shadow_pool_path(self) -> Path:
        return self.data_dir / "stage1_shadow_pool.json"

    @property
    def scan_cache_path(self) -> Path:
        return self.data_dir / "scan_cache.json"

    @property
    def summary_path(self) -> Path:
        return self.data_dir / "stage1_summary.json"

    @property
    def scan_log_path(self) -> Path:
        return self.logs_dir / "stage1_scan_log.csv"

    @property
    def error_log_path(self) -> Path:
        return self.logs_dir / "stage1_error_log.csv"

    def load_snapshot(self) -> list[SkillRecord]:
        raw_records = self.json_store.read(self.snapshot_path, [])
        return [SkillRecord.from_dict(raw_record) for raw_record in raw_records]

    def save_snapshot(self, records: list[SkillRecord]) -> None:
        self.json_store.write(self.snapshot_path, [record.to_dict() for record in records])

    def load_shadow_pool(self) -> list[SkillRecord]:
        raw_records = self.json_store.read(self.shadow_pool_path, [])
        return [SkillRecord.from_dict(raw_record) for raw_record in raw_records]

    def save_shadow_pool(self, records: list[SkillRecord]) -> None:
        self.json_store.write(self.shadow_pool_path, [record.to_dict() for record in records])

    def load_cache(self) -> dict[str, dict]:
        return dict(self.json_store.read(self.scan_cache_path, {}))

    def save_cache(self, cache: dict[str, dict]) -> None:
        self.json_store.write(self.scan_cache_path, cache)

    def load_summary(self) -> ScanSummary | None:
        raw_summary = self.json_store.read(self.summary_path, None)
        return ScanSummary.from_dict(raw_summary) if raw_summary else None

    def save_summary(self, summary: ScanSummary) -> None:
        self.json_store.write(self.summary_path, summary.to_dict())

    def append_scan_event(self, event: ScanEvent) -> None:
        self.csv_store.append_row(
            self.scan_log_path,
            ["created_at", "event_type", "message", "payload_json"],
            {
                "created_at": event.created_at,
                "event_type": event.event_type,
                "message": event.message,
                "payload_json": json.dumps(event.payload, sort_keys=True),
            },
        )

    def append_error(self, path: Path, error_type: str, message: str) -> None:
        self.csv_store.append_row(
            self.error_log_path,
            ["created_at", "path", "error_type", "message"],
            {
                "created_at": time.time(),
                "path": str(path),
                "error_type": error_type,
                "message": message,
            },
        )
