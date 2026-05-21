from __future__ import annotations

from manager_GUI.models import CandidateRecord, SkillRecord


SKILL_RECORD_TYPES = {"personal_skill", "project_skill", "plugin_skill"}
COMMAND_RECORD_TYPES = {"legacy_command"}
CONFIG_RECORD_TYPES = {"claude_config", "managed_config"}


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
    return SkillRecord(
        name=record.name,
        scope=record.scope,
        record_type=record.record_type,
        path=str(record.path),
        confidence=record.confidence,
        status=record.status,
        description=str(metadata.get("description") or metadata.get("summary") or ""),
    )


def candidate_from_backend_record(record, source: str) -> CandidateRecord:
    metadata = getattr(record, "metadata", {}) or {}
    return CandidateRecord(
        path=str(record.path),
        reason=str(metadata.get("classification_reason") or record.record_type),
        confidence=record.confidence,
        source=source,
        suggested_type=record.record_type,
        status="staged" if source == "continuation" else "warning",
    )


def candidate_from_backend_payload(payload: dict, source: str) -> CandidateRecord | None:
    if not payload:
        return None
    metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata", {}), dict) else {}
    return CandidateRecord(
        path=str(payload.get("path", "")),
        reason=str(metadata.get("classification_reason") or payload.get("record_type") or "candidate"),
        confidence=float(payload.get("confidence", 0)),
        source=source,
        suggested_type=str(payload.get("record_type", "candidate")),
        status="staged",
    )
