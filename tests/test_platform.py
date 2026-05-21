from __future__ import annotations

import os
import unittest
from pathlib import Path

from skill_manager.backend.models import ScanTarget
from skill_manager.platform import get_platform_adapter
from skill_manager.platform.factory import get_platform_adapter as factory_get_platform_adapter
from skill_manager.platform.profile_loader import load_platform_profile
from tests.test_support import writable_temp_dir


class PlatformTests(unittest.TestCase):
    def test_factory_creates_supported_adapters(self) -> None:
        self.assertEqual(get_platform_adapter("windows").name, "windows")
        self.assertEqual(get_platform_adapter("macos").name, "macos")
        self.assertEqual(get_platform_adapter("linux").name, "linux")

    def test_profiles_load_required_path_rules(self) -> None:
        profile = load_platform_profile("windows")
        self.assertEqual(profile.name, "windows")
        self.assertEqual(profile.schema_version, 2)
        self.assertEqual(profile.display_name, "Windows")
        self.assertEqual(profile.path_style, "windows")
        self.assertFalse(profile.case_sensitive_paths)
        self.assertIn("{claude_config_root}/skills", profile.personal_skill_paths)
        self.assertIn("{claude_config_root}/commands", profile.command_paths)
        self.assertIn("{claude_config_root}/plugins", profile.plugin_paths)
        self.assertIn("%USERPROFILE%/source/repos", profile.common_project_roots)
        self.assertIn("CLAUDE_CONFIG_DIR", profile.environment_overrides.values())
        self.assertIn("skills", profile.personal_scope_paths)
        self.assertIn("settings", profile.project_scope_paths)
        self.assertIn("skills", profile.plugin_scope_paths)
        self.assertIn("directories", profile.managed_scope_paths)
        self.assertTrue(profile.scan_strategy)
        self.assertTrue(profile.cli_resolution_commands)
        self.assertTrue(profile.packaging)
        self.assertTrue(profile.platform_notes)
        self.assertTrue(profile.doc_sources)
        self.assertTrue(profile.hard_ignored_roots)

    def test_all_platform_profiles_load_with_normalized_stage1_keys(self) -> None:
        for platform_name in ["windows", "macos", "linux"]:
            with self.subTest(platform_name=platform_name):
                profile = load_platform_profile(platform_name)
                self.assertTrue(profile.personal_skill_paths)
                self.assertTrue(profile.plugin_paths)
                self.assertTrue(profile.command_paths)
                self.assertTrue(profile.common_project_roots)
                self.assertTrue(profile.managed_config_paths)
                self.assertTrue(profile.hard_ignored_roots)

    def test_claude_config_override_builds_stage1_targets(self) -> None:
        adapter = get_platform_adapter()
        with writable_temp_dir() as temporary_path:
            temporary_dir = str(temporary_path)
            previous_override = os.environ.get("CLAUDE_CONFIG_DIR")
            os.environ["CLAUDE_CONFIG_DIR"] = str(Path(temporary_dir) / "custom_claude")
            try:
                targets = adapter.build_stage1_targets(Path(temporary_dir) / "project")
                target_paths = [target.path for target in targets]
                expected_skill_path = Path(temporary_dir) / "custom_claude" / "skills"
                self.assertTrue(any(adapter.is_same_path(path, expected_skill_path) for path in target_paths))
            finally:
                if previous_override is None:
                    os.environ.pop("CLAUDE_CONFIG_DIR", None)
                else:
                    os.environ["CLAUDE_CONFIG_DIR"] = previous_override

    def test_unsupported_platform_fails_fast(self) -> None:
        with self.assertRaises(RuntimeError):
            factory_get_platform_adapter("plan9")

    def test_build_stage1_targets_contains_expected_source_types_and_priorities(self) -> None:
        adapter = get_platform_adapter()
        with writable_temp_dir() as root:
            targets = adapter.build_stage1_targets(root / "project" / "child")
            by_source = _targets_by_source(targets)

            self.assertEqual(by_source["personal_skill"].priority, 100)
            self.assertEqual(by_source["plugin_skill"].priority, 90)
            self.assertEqual(by_source["legacy_command"].priority, 85)
            self.assertIn("claude_config", by_source)
            self.assertIn("common_project_root", by_source)

    def test_build_stage1_targets_includes_project_local_plugin_bundles(self) -> None:
        adapter = get_platform_adapter()
        with writable_temp_dir() as root:
            project_root = root / "project"
            bundled_plugins = project_root / "aws-skills" / "plugins"
            bundled_plugins.mkdir(parents=True)

            targets = adapter.build_stage1_targets(project_root)

            self.assertTrue(
                any(
                    target.source_type == "plugin_skill"
                    and target.scan_mode == "skill_inventory"
                    and adapter.is_same_path(target.path, bundled_plugins)
                    for target in targets
                )
            )

    def test_windows_adapter_normalizes_paths_case_insensitively(self) -> None:
        windows_adapter = get_platform_adapter("windows")
        with writable_temp_dir() as root:
            path = root / "MixedCase"
            path.mkdir()

            self.assertEqual(windows_adapter.path_key(path).lower(), windows_adapter.path_key(path))

    def test_format_path_collapses_home_prefix_when_possible(self) -> None:
        adapter = get_platform_adapter()
        formatted = adapter.format_path(adapter.home_dir() / ".claude" / "skills")

        self.assertTrue(formatted.startswith("~"))


def _targets_by_source(targets: list[ScanTarget]) -> dict[str, ScanTarget]:
    by_source: dict[str, ScanTarget] = {}
    for target in targets:
        by_source.setdefault(target.source_type, target)
    return by_source


if __name__ == "__main__":
    unittest.main()
