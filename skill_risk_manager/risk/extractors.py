from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from skill_risk_manager.risk.policy import RiskPolicy

if TYPE_CHECKING:
    from skill_risk_manager.backend.models import SkillRecord


def record_to_text(record: SkillRecord, policy: RiskPolicy | None = None) -> str:
    policy = policy or RiskPolicy()
    metadata = record.metadata or {}
    parts: list[str] = [
        f"name: {record.name}",
        f"record_type: {record.record_type}",
        f"scope: {record.scope}",
        f"source_type: {record.source_type}",
        f"status: {record.status}",
    ]
    if policy.enable_frontmatter_scan:
        parts.append(f"metadata: {json.dumps(metadata, ensure_ascii=False, default=str)}")
    if policy.enable_body_scan:
        body_text = _file_text(Path(record.path), policy.max_file_chars)
        if body_text:
            parts.append(body_text)
    return "\n\n".join(parts)


def _file_text(path: Path, max_chars: int) -> str:
    try:
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except OSError:
        return ""
    return ""
