from __future__ import annotations

from ui.models import CandidateRecord, SkillRecord


SKILL_RECORD_TYPES = {"personal_skill", "project_skill", "plugin_skill"}
COMMAND_RECORD_TYPES = {"legacy_command"}
CONFIG_RECORD_TYPES = {"claude_config", "claude_memory", "managed_config"}


def confirmed_skill_records(records: list) -> list[SkillRecord]:
    return records_by_type(records, SKILL_RECORD_TYPES)


def command_records(records: list) -> list[SkillRecord]:
    return records_by_type(records, COMMAND_RECORD_TYPES)


def config_records(records: list) -> list[SkillRecord]:
    return records_by_type(records, CONFIG_RECORD_TYPES)


def records_by_type(records: list, record_types: set[str]) -> list[SkillRecord]:
    return [
        skill_from_backend_record(record)
        for record in records
        if getattr(record, "record_type", "") in record_types
    ]


def candidate_records(records: list, source: str) -> list[CandidateRecord]:
    return [
        candidate_from_backend_record(record, source)
        for record in records
        if getattr(record, "record_type", "") == "candidate"
    ]


def skill_from_backend_record(record) -> SkillRecord:
    metadata = getattr(record, "metadata", {}) or {}
    risk = _risk_fields(metadata)
    return SkillRecord(
        name=record.name,
        scope=record.scope,
        record_type=record.record_type,
        path=str(record.path),
        confidence=record.confidence,
        status=record.status,
        description=str(metadata.get("description") or metadata.get("summary") or ""),
        **risk,
    )


def candidate_from_backend_record(record, source: str) -> CandidateRecord:
    metadata = getattr(record, "metadata", {}) or {}
    risk = _risk_fields(metadata)
    return CandidateRecord(
        path=str(record.path),
        reason=str(metadata.get("classification_reason") or record.record_type),
        confidence=record.confidence,
        source=source,
        suggested_type=record.record_type,
        status=record.status or ("staged" if source == "continuation" else "warning"),
        **risk,
    )


def candidate_from_backend_payload(payload: dict, source: str) -> CandidateRecord | None:
    if not payload:
        return None
    metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata", {}), dict) else {}
    risk = _risk_fields(metadata)
    return CandidateRecord(
        path=str(payload.get("path", "")),
        reason=str(metadata.get("classification_reason") or payload.get("record_type") or "candidate"),
        confidence=float(payload.get("confidence", 0)),
        source=source,
        suggested_type=str(payload.get("record_type", "candidate")),
        status=str(payload.get("status", "staged")),
        **risk,
    )


def _risk_fields(metadata: dict) -> dict[str, object]:
    raw_risk = metadata.get("risk", {}) if isinstance(metadata, dict) else {}
    risk = raw_risk if isinstance(raw_risk, dict) else {}
    findings = risk.get("findings", [])
    first_finding = findings[0] if isinstance(findings, list) and findings else {}
    top_finding = first_finding.get("message", "") if isinstance(first_finding, dict) else ""
    categories = risk.get("categories", [])
    risk_level = str(risk.get("level", "low") or "low")
    risk_score = int(risk.get("score", 0) or 0)
    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_summary": str(risk.get("summary", "No major risk indicators detected.")),
        "risk_categories": tuple(str(category) for category in categories) if isinstance(categories, list) else (),
        "top_finding": str(top_finding),
        "suggested_action": _suggested_action(risk_level),
    }


def _suggested_action(risk_level: str) -> str:
    return {
        "critical": "quarantine",
        "high": "review",
        "medium": "review",
        "low": "trust",
        "none": "trust",
    }.get(risk_level, "review")
