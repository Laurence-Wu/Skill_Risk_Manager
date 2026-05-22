from __future__ import annotations

import csv
from pathlib import Path

from ui.core.state import AppState
from ui.core.table_rows import risk_rows_from_state
from ui.models import LogEntry, SkillRecord


LOG_FIELDS = ["timestamp", "level", "event_type", "message"]
SKILL_FIELDS = ["name", "type", "scope", "confidence", "risk_level", "risk_score", "path", "status"]
RISK_FIELDS = ["record", "score", "level", "categories", "finding", "path", "source"]


def export_logs_to_csv(logs: list[LogEntry], target_path: Path) -> Path:
    _ensure_parent(target_path)
    with target_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=LOG_FIELDS)
        writer.writeheader()
        for log in logs:
            writer.writerow(
                {
                    "timestamp": log.timestamp,
                    "level": log.level,
                    "event_type": log.event_type,
                    "message": log.message,
                }
            )
    return target_path


def export_skills_to_csv(records: list[SkillRecord], target_path: Path) -> Path:
    _ensure_parent(target_path)
    with target_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=SKILL_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "name": record.name,
                    "type": record.record_type,
                    "scope": record.scope,
                    "confidence": f"{record.confidence:.2f}",
                    "risk_level": record.risk_level,
                    "risk_score": record.risk_score,
                    "path": record.path,
                    "status": record.status,
                }
            )
    return target_path


def export_risk_report_to_csv(state: AppState, target_path: Path) -> Path:
    _ensure_parent(target_path)
    with target_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=RISK_FIELDS)
        writer.writeheader()
        for row in risk_rows_from_state(state):
            writer.writerow(
                {
                    "record": row["Record"],
                    "score": row["Score"],
                    "level": str(row["Level"]).lower(),
                    "categories": row["Category"],
                    "finding": row["Top Finding"],
                    "path": row["Path"],
                    "source": str(row["Source"]).lower(),
                }
            )
    return target_path


def _ensure_parent(target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
