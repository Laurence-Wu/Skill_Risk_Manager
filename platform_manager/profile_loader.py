from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PlatformProfile:
    name: str
    claude_config_root: str
    personal_skill_paths: list[str]
    plugin_paths: list[str]
    command_paths: list[str]
    common_project_roots: list[str]
    managed_config_paths: list[str]
    hard_ignored_roots: list[str]
    ui: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1
    display_name: str = ""
    path_style: str = ""
    case_sensitive_paths: bool | None = None
    environment_overrides: dict[str, str] = field(default_factory=dict)
    direct_claude_config_roots: list[str] = field(default_factory=list)
    personal_scope_paths: dict[str, list[str]] = field(default_factory=dict)
    project_scope_paths: dict[str, list[str]] = field(default_factory=dict)
    plugin_scope_paths: dict[str, list[str]] = field(default_factory=dict)
    managed_scope_paths: dict[str, list[str]] = field(default_factory=dict)
    developer_root_candidates: list[str] = field(default_factory=list)
    scan_strategy: dict[str, Any] = field(default_factory=dict)
    cli_resolution_commands: list[str] = field(default_factory=list)
    packaging: dict[str, Any] = field(default_factory=dict)
    platform_notes: list[str] = field(default_factory=list)
    doc_sources: list[dict[str, Any]] = field(default_factory=list)


def platform_profile_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "platforms"


def load_platform_profile(name: str, profile_dir: Path | None = None) -> PlatformProfile:
    profile_path = (profile_dir or platform_profile_dir()) / f"{name}.json"
    with profile_path.open("r", encoding="utf-8") as profile_file:
        raw_profile = json.load(profile_file)
    normalized_profile = _normalize_profile(raw_profile)

    required_fields = {
        "name",
        "claude_config_root",
        "personal_skill_paths",
        "plugin_paths",
        "command_paths",
        "common_project_roots",
        "managed_config_paths",
        "hard_ignored_roots",
    }
    missing_fields = required_fields.difference(normalized_profile)
    if missing_fields:
        missing_text = ", ".join(sorted(missing_fields))
        raise ValueError(f"Platform profile {profile_path} is missing: {missing_text}")

    return PlatformProfile(
        name=str(normalized_profile["name"]),
        claude_config_root=str(normalized_profile["claude_config_root"]),
        personal_skill_paths=list(normalized_profile["personal_skill_paths"]),
        plugin_paths=list(normalized_profile["plugin_paths"]),
        command_paths=list(normalized_profile["command_paths"]),
        common_project_roots=list(normalized_profile["common_project_roots"]),
        managed_config_paths=list(normalized_profile["managed_config_paths"]),
        hard_ignored_roots=list(normalized_profile["hard_ignored_roots"]),
        ui=dict(normalized_profile.get("ui", {})),
        schema_version=int(normalized_profile.get("schema_version", 1)),
        display_name=str(normalized_profile.get("display_name", normalized_profile["name"])),
        path_style=str(normalized_profile.get("path_style", "")),
        case_sensitive_paths=normalized_profile.get("case_sensitive_paths"),
        environment_overrides=dict(normalized_profile.get("environment_overrides", {})),
        direct_claude_config_roots=list(normalized_profile.get("direct_claude_config_roots", [])),
        personal_scope_paths=_scope_dict(normalized_profile.get("personal_scope_paths", {})),
        project_scope_paths=_scope_dict(normalized_profile.get("project_scope_paths", {})),
        plugin_scope_paths=_scope_dict(normalized_profile.get("plugin_scope_paths", {})),
        managed_scope_paths=_scope_dict(normalized_profile.get("managed_scope_paths", {})),
        developer_root_candidates=list(normalized_profile.get("developer_root_candidates", [])),
        scan_strategy=dict(normalized_profile.get("scan_strategy", {})),
        cli_resolution_commands=list(normalized_profile.get("cli_resolution_commands", [])),
        packaging=dict(normalized_profile.get("packaging", {})),
        platform_notes=list(normalized_profile.get("platform_notes", [])),
        doc_sources=list(normalized_profile.get("doc_sources", [])),
    )


def _normalize_profile(raw_profile: dict[str, Any]) -> dict[str, Any]:
    normalized_profile = dict(raw_profile)

    personal_scope_paths = dict(raw_profile.get("personal_scope_paths", {}))
    managed_scope_paths = dict(raw_profile.get("managed_scope_paths", {}))

    normalized_profile.setdefault(
        "personal_skill_paths",
        _parent_directories(personal_scope_paths.get("skills", []), "/<skill-name>/SKILL.md"),
    )
    normalized_profile.setdefault(
        "command_paths",
        _parent_directories(personal_scope_paths.get("commands", []), "/<command>.md"),
    )
    normalized_profile.setdefault(
        "plugin_paths",
        _plugin_roots(raw_profile),
    )
    normalized_profile.setdefault(
        "common_project_roots",
        list(raw_profile.get("developer_root_candidates", [])),
    )
    normalized_profile.setdefault(
        "managed_config_paths",
        list(managed_scope_paths.get("directories", [])),
    )

    return normalized_profile


def _parent_directories(path_templates: list[str], suffix: str) -> list[str]:
    directories: list[str] = []
    for path_template in path_templates:
        if path_template.endswith(suffix):
            directories.append(path_template[: -len(suffix)])
        else:
            directories.append(path_template)
    return directories


def _plugin_roots(raw_profile: dict[str, Any]) -> list[str]:
    direct_roots = raw_profile.get("plugin_paths")
    if direct_roots:
        return list(direct_roots)
    personal_scope_paths = dict(raw_profile.get("personal_scope_paths", {}))
    personal_plugin_roots = _trim_template_suffixes(personal_scope_paths.get("plugins", []))
    if personal_plugin_roots:
        return personal_plugin_roots
    claude_root = raw_profile.get("claude_config_root", "~/.claude")
    return [f"{claude_root}/plugins"]


def _trim_template_suffixes(path_templates: list[str]) -> list[str]:
    trimmed_templates: list[str] = []
    for path_template in path_templates:
        trimmed = path_template
        for suffix in ["/**", "/*", "/<skill-name>/SKILL.md", "/<command>.md", "/<agent>.md"]:
            if trimmed.endswith(suffix):
                trimmed = trimmed[: -len(suffix)]
        trimmed_templates.append(trimmed)
    return trimmed_templates


def _scope_dict(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for key, paths in value.items():
        if isinstance(paths, list):
            normalized[str(key)] = [str(path) for path in paths]
    return normalized
