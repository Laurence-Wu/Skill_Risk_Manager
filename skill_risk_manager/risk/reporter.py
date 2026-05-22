from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skill_risk_manager.backend.models import SkillRecord


def risk_counts(records: list[SkillRecord]) -> dict[str, int]:
    counts = Counter(_risk_level(record) for record in records)
    return {level: counts.get(level, 0) for level in ["critical", "high", "medium", "low"]}


def _risk_level(record: SkillRecord) -> str:
    risk = (record.metadata or {}).get("risk", {})
    if isinstance(risk, dict):
        return str(risk.get("level", "low"))
    return "low"
