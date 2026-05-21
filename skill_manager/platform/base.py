from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path

from skill_manager.backend.models import ScanTarget
from skill_manager.platform.profile_loader import PlatformProfile


class PlatformAdapter(ABC):
    name: str

    def __init__(self, profile: PlatformProfile) -> None:
        self.profile = profile

    def home_dir(self) -> Path:
        return Path.home()

    def claude_config_root(self) -> Path:
        override = os.getenv("CLAUDE_CONFIG_DIR")
        configured_root = override if override else self.profile.claude_config_root
        return self.normalize_path(self._expand_path(configured_root))

    def personal_skill_paths(self) -> list[Path]:
        return self._expand_path_list(self.profile.personal_skill_paths)

    def plugin_paths(self) -> list[Path]:
        return self._expand_path_list(self.profile.plugin_paths)

    def command_paths(self) -> list[Path]:
        return self._expand_path_list(self.profile.command_paths)

    def common_project_roots(self) -> list[Path]:
        return self._expand_path_list(self.profile.common_project_roots)

    def managed_config_paths(self) -> list[Path]:
        return self._expand_path_list(self.profile.managed_config_paths)

    def hard_ignored_roots(self) -> list[Path]:
        return self._expand_path_list(self.profile.hard_ignored_roots)

    def normalize_path(self, path: Path) -> Path:
        return path.expanduser().resolve()

    def path_key(self, path: Path) -> str:
        return str(self.normalize_path(path))

    def is_same_path(self, left: Path, right: Path) -> bool:
        return self.normalize_path(left) == self.normalize_path(right)

    def is_hard_ignored(self, path: Path) -> bool:
        normalized_path = self.normalize_path(path)
        for ignored_root in self.hard_ignored_roots():
            normalized_root = self.normalize_path(ignored_root)
            if normalized_path == normalized_root:
                return True
            try:
                normalized_path.relative_to(normalized_root)
                return True
            except ValueError:
                continue
        return False

    def format_path(self, path: Path) -> str:
        resolved_path = path.expanduser().resolve()
        home_path = self.home_dir().expanduser().resolve()
        try:
            relative_path = resolved_path.relative_to(home_path)
            return f"~/{relative_path.as_posix()}"
        except ValueError:
            return str(resolved_path)

    @abstractmethod
    def open_folder(self, path: Path) -> None:
        pass

    def default_window_size(self) -> tuple[int, int]:
        size = self.profile.ui.get("default_window_size", [1200, 760])
        return int(size[0]), int(size[1])

    def minimum_window_size(self) -> tuple[int, int]:
        size = self.profile.ui.get("minimum_window_size", [1100, 720])
        return int(size[0]), int(size[1])

    def sidebar_width(self) -> int:
        return int(self.profile.ui.get("sidebar_width", 230))

    def build_stage1_targets(self, project_root: Path | None = None) -> list[ScanTarget]:
        targets: list[ScanTarget] = []

        for skill_path in self.personal_skill_paths():
            targets.append(
                ScanTarget(skill_path, 100, "personal_skill", 8, "skill_inventory", "Personal Claude skills")
            )

        for plugin_path in self.plugin_paths():
            targets.append(ScanTarget(plugin_path, 90, "plugin_skill", 10, "skill_inventory", "Claude plugin skills"))

        for command_path in self.command_paths():
            targets.append(ScanTarget(command_path, 85, "legacy_command", 1, "foreground", "Claude legacy commands"))

        claude_root = self.claude_config_root()
        for config_path in [
            claude_root / "settings.json",
            claude_root / "settings.local.json",
            claude_root / "CLAUDE.md",
            self.home_dir() / ".claude.json",
        ]:
            targets.append(ScanTarget(config_path, 75, "claude_config", 0, "foreground", "Claude config or memory"))

        resolved_project_root = (project_root or Path.cwd()).expanduser().resolve()
        for depth, candidate_root in enumerate([resolved_project_root, *resolved_project_root.parents]):
            if self.is_hard_ignored(candidate_root):
                break
            if depth == 0:
                source_type = "project_skill"
                skill_priority = 98
                reason_prefix = "Current project"
            else:
                source_type = "parent_project"
                skill_priority = 95
                reason_prefix = "Parent project"

            targets.extend(
                [
                    ScanTarget(
                        candidate_root / ".claude" / "skills",
                        skill_priority,
                        source_type,
                        8,
                        "skill_inventory",
                        f"{reason_prefix} Claude skills",
                    ),
                    ScanTarget(
                        candidate_root / ".claude" / "commands",
                        max(skill_priority - 13, 80),
                        "legacy_command",
                        1,
                        "foreground",
                        f"{reason_prefix} Claude commands",
                    ),
                    ScanTarget(
                        candidate_root / ".claude" / "settings.json",
                        75,
                        "claude_config",
                        0,
                        "foreground",
                        f"{reason_prefix} Claude settings",
                    ),
                    ScanTarget(
                        candidate_root / ".claude" / "settings.local.json",
                        75,
                        "claude_config",
                        0,
                        "foreground",
                        f"{reason_prefix} Claude local settings",
                    ),
                    ScanTarget(
                        candidate_root / "CLAUDE.md",
                        75,
                        "claude_config",
                        0,
                        "foreground",
                        f"{reason_prefix} Claude memory",
                    ),
                    ScanTarget(
                        candidate_root / ".mcp.json",
                        75,
                        "claude_config",
                        0,
                        "foreground",
                        f"{reason_prefix} MCP config",
                    ),
                ]
            )
            if depth == 0:
                targets.extend(self._project_local_plugin_targets(candidate_root))
            if candidate_root == self.home_dir().expanduser().resolve():
                break

        for managed_path in self.managed_config_paths():
            targets.append(ScanTarget(managed_path, 75, "managed_config", 1, "foreground", "Managed Claude config"))

        for project_path in self.common_project_roots():
            targets.append(
                ScanTarget(
                    project_path,
                    60,
                    "common_project_root",
                    4,
                    "foreground",
                    "Common project root shallow scan",
                )
            )

        return self._dedupe_targets(targets)

    def _project_local_plugin_targets(self, project_root: Path) -> list[ScanTarget]:
        targets = [
            ScanTarget(
                project_root / "plugins",
                97,
                "plugin_skill",
                10,
                "skill_inventory",
                "Current project plugin skills",
            )
        ]
        try:
            children = list(project_root.iterdir()) if project_root.exists() else []
        except OSError:
            children = []
        for child in children:
            if child.is_dir():
                targets.append(
                    ScanTarget(
                        child / "plugins",
                        96,
                        "plugin_skill",
                        10,
                        "skill_inventory",
                        "Current project bundled plugin skills",
                    )
                )
        return targets

    def _expand_path_list(self, path_templates: list[str]) -> list[Path]:
        return [self.normalize_path(self._expand_path(path_template)) for path_template in path_templates]

    def _expand_path(self, path_template: str) -> Path:
        claude_root = os.getenv("CLAUDE_CONFIG_DIR") or self.profile.claude_config_root
        expanded = (
            path_template.replace("{home}", str(self.home_dir()))
            .replace("{claude_config_root}", claude_root)
        )
        return Path(os.path.expandvars(expanded)).expanduser()

    def _dedupe_targets(self, targets: list[ScanTarget]) -> list[ScanTarget]:
        deduped: dict[tuple[str, str, int], ScanTarget] = {}
        for target in targets:
            key = (self.path_key(target.path), target.source_type, target.priority)
            deduped.setdefault(key, target)
        return list(deduped.values())
