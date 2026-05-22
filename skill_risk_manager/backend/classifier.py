from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skill_risk_manager.backend.parser import has_skill_like_frontmatter


CONFIG_FILENAMES = {"settings.json", "settings.local.json", ".mcp.json", ".claude.json"}
MEMORY_FILENAMES = {"claude.md", "claude.local.md"}
SUSPICIOUS_FOLDERS = {"prompt", "prompts", "agent", "agents", "commands", "skills"}


@dataclass
class Classification:
    record_type: str
    scope: str
    name: str
    confidence: float
    status: str = "discovered"
    metadata: dict = field(default_factory=dict)


def classify_path(path: Path, source_type: str, frontmatter: dict[str, Any] | None = None) -> Classification:
    frontmatter = frontmatter or {}
    filename_lower = path.name.lower()
    parent_names = [part.lower() for part in path.parts]

    if _is_confirmed_skill_path(path):
        if has_skill_like_frontmatter(frontmatter):
            return Classification(
                record_type=_skill_record_type(source_type, parent_names),
                scope=_scope_for_source(source_type, parent_names),
                name=str(frontmatter.get("name") or path.parent.name),
                confidence=0.99,
                metadata=_metadata_from_frontmatter(
                    frontmatter,
                    "Verified SKILL.md under skills/<name>/ with closed YAML frontmatter",
                ),
            )
        return Classification(
            record_type="candidate",
            scope=_scope_for_source(source_type, parent_names),
            name=path.parent.name,
            confidence=0.58,
            metadata={"classification_reason": "SKILL.md path found but required closed name/description metadata is missing"},
        )

    if filename_lower == "skill.md":
        if has_skill_like_frontmatter(frontmatter):
            return Classification(
                record_type="candidate",
                scope=_scope_for_source(source_type, parent_names),
                name=str(frontmatter.get("name") or path.parent.name),
                confidence=0.78,
                metadata=_metadata_from_frontmatter(
                    frontmatter,
                    "SKILL.md outside normal skill folder with closed YAML frontmatter",
                ),
            )
        return Classification(
            record_type="candidate",
            scope=_scope_for_source(source_type, parent_names),
            name=path.parent.name,
            confidence=0.72,
            metadata={"classification_reason": "SKILL.md outside normal skill folder"},
        )

    if filename_lower in MEMORY_FILENAMES:
        return Classification(
            record_type="claude_memory",
            scope="config",
            name=path.name,
            confidence=0.95,
            metadata={"classification_reason": "Claude memory filename"},
        )

    if _is_claude_config_path(filename_lower, parent_names, source_type):
        return Classification(
            record_type="claude_config",
            scope="config",
            name=path.name,
            confidence=0.95,
            metadata={"classification_reason": "Claude config filename"},
        )

    if path.suffix.lower() == ".md" and "commands" in parent_names:
        return Classification(
            record_type="legacy_command",
            scope=_scope_for_source(source_type, parent_names),
            name=path.stem,
            confidence=0.88,
            metadata={"classification_reason": "Markdown file in Claude commands folder"},
        )

    if path.suffix.lower() == ".md" and has_skill_like_frontmatter(frontmatter):
        return Classification(
            record_type="candidate",
            scope=_scope_for_source(source_type, parent_names),
            name=str(frontmatter.get("name") or path.stem),
            confidence=0.65,
            metadata=_metadata_from_frontmatter(frontmatter, "Closed YAML frontmatter with skill-like metadata"),
        )

    if path.suffix.lower() == ".md" and SUSPICIOUS_FOLDERS.intersection(parent_names):
        return Classification(
            record_type="candidate",
            scope=_scope_for_source(source_type, parent_names),
            name=path.stem,
            confidence=0.45,
            metadata={"classification_reason": "Markdown in prompt-like folder"},
        )

    return Classification(
        record_type="regular_markdown" if path.suffix.lower() == ".md" else "unknown",
        scope="unknown",
        name=path.name,
        confidence=0.0,
        status="ignored",
    )


def _is_confirmed_skill_path(path: Path) -> bool:
    parts = [part.lower() for part in path.parts]
    return path.name.lower() == "skill.md" and len(parts) >= 3 and path.parent.parent.name.lower() == "skills"


def _skill_record_type(source_type: str, parent_names: list[str]) -> str:
    if source_type == "plugin_skill" or "plugins" in parent_names:
        return "plugin_skill"
    if source_type in {"project_skill", "parent_project"}:
        return "project_skill"
    return "personal_skill"


def _scope_for_source(source_type: str, parent_names: list[str]) -> str:
    if source_type == "plugin_skill" or "plugins" in parent_names:
        return "plugin"
    if source_type in {"project_skill", "parent_project"}:
        return "project"
    if source_type == "legacy_command":
        return "command"
    if source_type in {"claude_config", "managed_config"}:
        return "config"
    if "plugins" in parent_names:
        return "plugin"
    if ".claude" in parent_names:
        return "project"
    return "personal"


def _is_claude_config_path(filename_lower: str, parent_names: list[str], source_type: str) -> bool:
    if filename_lower in {".mcp.json", ".claude.json"}:
        return True
    if filename_lower not in {"settings.json", "settings.local.json"}:
        return False
    return source_type in {"claude_config", "managed_config"} or ".claude" in parent_names


def _metadata_from_frontmatter(frontmatter: dict[str, Any], classification_reason: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "classification_reason": classification_reason,
        "frontmatter_verified": True,
        "frontmatter": frontmatter,
    }
    for source_key, metadata_key in [
        ("description", "description"),
        ("summary", "summary"),
        ("context", "context"),
        ("allowed-tools", "allowed_tools"),
        ("allowed_tools", "allowed_tools"),
        ("hooks", "hooks"),
    ]:
        if source_key in frontmatter:
            metadata[metadata_key] = frontmatter[source_key]
    if "skills" in frontmatter:
        metadata["referenced_skills"] = _normalize_string_list(frontmatter["skills"])
    return metadata


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value:
        return [value]
    return []
