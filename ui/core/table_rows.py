from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ui.models import CandidateRecord, LogEntry

if TYPE_CHECKING:
    from ui.core.state import AppState


RISK_LEVEL_FILTERS = ["All Risks", "Critical", "High", "Medium", "Low"]
RISK_LEVEL_VIEW_FILTERS = ["All Levels", "Critical", "High", "Medium", "Low"]
RISK_CATEGORIES = [
    "All Categories",
    "tool_access",
    "filesystem",
    "network",
    "command_execution",
    "secrets",
    "mcp",
    "hooks",
    "prompt_injection",
    "persistence",
    "uncertainty",
]


def ranked_skill_rows(records: list) -> list[dict[str, object]]:
    return sorted((record.to_row() for record in records), key=_skill_rank_key)


def candidate_records_for_bucket(state: AppState, bucket: str) -> list[CandidateRecord]:
    if bucket == "staged":
        return list(reversed(state.candidates_staged))
    if bucket == "ignored":
        return state.ignored_candidates
    return state.candidates_snapshot


def candidate_rows_for_bucket(state: AppState, bucket: str) -> list[dict[str, object]]:
    return [record.to_row() for record in candidate_records_for_bucket(state, bucket)]


def risk_rows_from_state(state: AppState) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record, source in [
        *[(record, "Skills") for record in state.confirmed_skills],
        *[(record, "Snapshot") for record in state.candidates_snapshot],
        *[(record, "Staged") for record in state.candidates_staged],
    ]:
        categories = tuple(getattr(record, "risk_categories", ()))
        rows.append(
            {
                "Record": getattr(record, "name", "") or name_from_path(getattr(record, "path", "")),
                "Score": getattr(record, "risk_score", 0),
                "Level": str(getattr(record, "risk_level", "low")).title(),
                "Category": ", ".join(categories) or "none",
                "Top Finding": getattr(record, "top_finding", "") or getattr(record, "risk_summary", ""),
                "Path": getattr(record, "path", ""),
                "Source": source,
                "_record": record,
                "_row_kind": getattr(record, "risk_level", "low"),
            }
        )
    return rows


def log_to_row(log: LogEntry) -> dict[str, object]:
    return {
        "Time": datetime.fromtimestamp(log.timestamp).strftime("%H:%M:%S"),
        "Level": log.level.title(),
        "Event": log.event_type,
        "Message": log.message,
        "Path": path_from_message(log.message),
        "_record": log,
        "_row_kind": log.level,
    }


def log_rows(logs: list[LogEntry], level_filter: str = "all") -> list[dict[str, object]]:
    return [log_to_row(log) for log in logs if level_filter == "all" or log.level == level_filter]


def filter_rows(
    rows: list[dict[str, object]],
    *,
    query: str = "",
    search_keys: tuple[str, ...] = (),
    exact_filters: tuple[tuple[str, str, str], ...] = (),
    contains_filters: tuple[tuple[str, str, str], ...] = (),
) -> list[dict[str, object]]:
    return [
        row
        for row in rows
        if row_matches_query(row, query, search_keys)
        and all(row_matches_exact(row, column, selected, all_label) for column, selected, all_label in exact_filters)
        and all(row_matches_contains(row, column, selected, all_label) for column, selected, all_label in contains_filters)
    ]


def row_matches_query(row: dict[str, object], query: str, keys: tuple[str, ...]) -> bool:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return True
    searchable = " ".join(str(row.get(key, "")) for key in keys).lower()
    return normalized_query in searchable


def row_matches_exact(row: dict[str, object], column: str, selected: str, all_label: str) -> bool:
    if selected == all_label:
        return True
    return str(row.get(column, "")).lower() == selected.lower()


def row_matches_contains(row: dict[str, object], column: str, selected: str, all_label: str) -> bool:
    if selected == all_label:
        return True
    return selected.lower() in str(row.get(column, "")).lower()


def name_from_path(path_text: str) -> str:
    path = Path(path_text)
    if path.name.lower() == "skill.md" and path.parent.name:
        return path.parent.name
    return path.stem or path.name or path_text


def path_from_message(message: str) -> str:
    for marker in [" path: ", "folder: ", "logs: ", "skills: ", "risk report: ", ": "]:
        if marker in message.lower():
            candidate = message.split(":", 1)[-1].strip()
            if "\\" in candidate or "/" in candidate:
                return candidate
    return ""


def _skill_rank_key(row: dict[str, object]) -> tuple[int, int, str]:
    return (-_int_value(row.get("Score", 0)), -_risk_rank(str(row.get("Risk", ""))), str(row.get("Name", "")).lower())


def _risk_rank(level: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(level.lower(), 0)


def _int_value(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
