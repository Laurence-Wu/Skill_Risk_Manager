from __future__ import annotations

import time
from pathlib import Path

from skill_manager.backend.cache import cache_metadata
from skill_manager.backend.models import SkillRecord
from skill_manager.platform.base import PlatformAdapter


CLASSIFICATION_CACHE_VERSION = 4
GENERATED_FOLDERS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "dist",
    "build",
    "target",
    ".next",
    ".nuxt",
}


def is_generated_or_test_path(path: Path) -> bool:
    lowered_name = path.name.lower()
    return lowered_name in GENERATED_FOLDERS or lowered_name.startswith(".test_")


def is_scan_candidate_path(path: Path) -> bool:
    return path.suffix.lower() in {".md", ".json"} or path.name.lower() == "skill.md"


def cached_classification(cache_record: dict | None) -> dict | None:
    if not cache_record:
        return None
    if cache_record.get("classification_cache_version") != CLASSIFICATION_CACHE_VERSION:
        return None
    return cache_record.get("previous_classification")


def build_cache_record(path: Path, computed_hash: str | None, record: SkillRecord | None) -> dict:
    metadata = cache_metadata(path, computed_hash)
    metadata.update(
        {
            "path": str(path),
            "classification_cache_version": CLASSIFICATION_CACHE_VERSION,
            "previous_classification": record.to_dict() if record else None,
            "last_scanned_at": time.time(),
        }
    )
    return metadata


def deduplicate_records(records: list[SkillRecord], adapter: PlatformAdapter) -> list[SkillRecord]:
    deduped: dict[tuple[str, str, str, str], SkillRecord] = {}
    for record in records:
        key = (
            adapter.path_key(record.path),
            record.name.lower(),
            record.scope,
            record.file_hash or "",
        )
        existing_record = deduped.get(key)
        if not existing_record or record.confidence > existing_record.confidence:
            deduped[key] = record
    return list(deduped.values())
