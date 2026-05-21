from __future__ import annotations

import queue
import unittest
from pathlib import Path
from unittest.mock import patch

from skill_manager.backend import ScanService
from skill_manager.backend.fast_exit import FastExitTracker
from skill_manager.backend.models import CancelToken, ScanConfig, ScanEvent, ScanTarget
from skill_manager.backend.shadow_scanner import ShadowScanner
from skill_manager.backend.stage1_scanner import Stage1Scanner
from skill_manager.platform import get_platform_adapter
from skill_manager.storage.repository import Repository
from tests.test_support import writable_temp_dir


class ScannerTests(unittest.TestCase):
    def test_scan_service_exposes_foreground_and_shadow_facade(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            skill_file = root / "claude" / "skills" / "helper" / "SKILL.md"
            skill_file.parent.mkdir(parents=True)
            skill_file.write_text("---\nname: Helper\ndescription: Test\n---", encoding="utf-8")
            shadow_file = root / "project" / "prompts" / "helper.md"
            shadow_file.parent.mkdir(parents=True)
            shadow_file.write_text("---\nname: Shadow Helper\ndescription: Candidate\n---", encoding="utf-8")
            service = ScanService(
                adapter,
                repository,
                ScanConfig(min_checked_count=1, min_elapsed_seconds=0, required_source_groups=set()),
                queue.Queue[ScanEvent](),
            )

            foreground_result = service.run_foreground(
                [ScanTarget(skill_file.parent.parent, 100, "personal_skill", 2, "foreground", "Skills")]
            )
            shadow_records = service.run_shadow(
                [ScanTarget(shadow_file.parent, 30, "deferred_candidate", 1, "shadow", "Shadow")]
            )

            self.assertIsNotNone(foreground_result)
            self.assertEqual(repository.load_snapshot()[0].name, "Helper")
            self.assertEqual(shadow_records[0].name, "Shadow Helper")

    def test_scan_service_adds_local_roots_for_full_computer_scan(self) -> None:
        with writable_temp_dir() as root:
            service = ScanService(
                get_platform_adapter(),
                Repository(root / "runtime"),
                ScanConfig(min_checked_count=1, min_elapsed_seconds=0, required_source_groups=set()),
                queue.Queue[ScanEvent](),
            )

            targets = service.build_computer_scan_targets("base")

            self.assertTrue(any(target.source_type == "computer_root" for target in targets))

    def test_foreground_scan_saves_stable_snapshot_after_run(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            skill_file = root / "claude" / "skills" / "pdf-helper" / "SKILL.md"
            skill_file.parent.mkdir(parents=True)
            skill_file.write_text("---\nname: PDF Helper\ndescription: Reads PDFs\n---\nBody", encoding="utf-8")
            command_file = root / "claude" / "commands" / "build.md"
            command_file.parent.mkdir(parents=True)
            command_file.write_text("# Build\nRun build.", encoding="utf-8")
            config_file = root / "claude" / "settings.json"
            config_file.write_text("{}", encoding="utf-8")

            targets = [
                ScanTarget(skill_file.parent.parent, 100, "personal_skill", 2, "foreground", "Test skills"),
                ScanTarget(command_file.parent, 85, "legacy_command", 1, "foreground", "Test commands"),
                ScanTarget(config_file, 75, "claude_config", 0, "foreground", "Test config"),
            ]
            config = ScanConfig(min_checked_count=1, min_elapsed_seconds=0, required_source_groups=set())
            scanner = Stage1Scanner(adapter, repository, config, queue.Queue[ScanEvent]())

            result = scanner.run_foreground(targets)

            self.assertIsNotNone(result)
            records = repository.load_snapshot()
            record_types = {record.record_type for record in records}
            self.assertIn("personal_skill", record_types)
            self.assertIn("legacy_command", record_types)
            self.assertIn("claude_config", record_types)
            self.assertTrue(repository.summary_path.exists())
            self.assertTrue(repository.scan_cache_path.exists())

    def test_foreground_cancel_before_work_does_not_save_snapshot(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            target_dir = root / "claude" / "skills"
            target_dir.mkdir(parents=True)
            token = CancelToken()
            token.cancel()
            scanner = Stage1Scanner(adapter, repository, ScanConfig(), queue.Queue[ScanEvent]())

            result = scanner.run_foreground(
                [ScanTarget(target_dir, 100, "personal_skill", 2, "foreground", "Cancelled")],
                token,
            )

            self.assertIsNone(result)
            self.assertFalse(repository.snapshot_path.exists())

    def test_foreground_events_report_snapshot_only_after_fast_exit(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            skill_file = root / "claude" / "skills" / "helper" / "SKILL.md"
            skill_file.parent.mkdir(parents=True)
            skill_file.write_text("---\nname: Helper\ndescription: Test\n---", encoding="utf-8")
            event_queue: queue.Queue[ScanEvent] = queue.Queue()
            scanner = Stage1Scanner(
                adapter,
                repository,
                ScanConfig(min_checked_count=2, min_elapsed_seconds=0, required_source_groups=set()),
                event_queue,
            )

            scanner.run_foreground(
                [ScanTarget(skill_file.parent.parent, 100, "personal_skill", 2, "foreground", "Skills")]
            )

            event_types = [event_queue.get().event_type for _ in range(event_queue.qsize())]
            self.assertLess(event_types.index("foreground_fast_exit"), event_types.index("snapshot_saved"))
            self.assertLess(event_types.index("snapshot_saved"), event_types.index("ui_results_ready"))

    def test_foreground_progress_payload_includes_live_potential_records(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            skill_file = root / "claude" / "skills" / "helper" / "SKILL.md"
            skill_file.parent.mkdir(parents=True)
            skill_file.write_text("---\nname: Helper\ndescription: Test\n---", encoding="utf-8")
            event_queue: queue.Queue[ScanEvent] = queue.Queue()
            scanner = Stage1Scanner(
                adapter,
                repository,
                ScanConfig(min_checked_count=1, min_elapsed_seconds=0, required_source_groups=set()),
                event_queue,
            )

            scanner.run_foreground(
                [ScanTarget(skill_file.parent.parent, 100, "personal_skill", 2, "foreground", "Skills")]
            )

            events = [event_queue.get() for _ in range(event_queue.qsize())]
            progress_payloads = [
                event.payload for event in events if event.event_type == "foreground_progress"
            ]
            discovered_payloads = [
                payload
                for payload in progress_payloads
                if payload.get("potential_records")
            ]
            self.assertTrue(discovered_payloads)
            self.assertEqual(discovered_payloads[-1]["potential_records"][0]["name"], "Helper")
            self.assertEqual(
                discovered_payloads[-1]["potential_records"][0]["metadata"]["description"],
                "Test",
            )

    def test_foreground_persists_rich_skill_metadata(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            skill_file = root / "claude" / "skills" / "aws-cdk" / "SKILL.md"
            skill_file.parent.mkdir(parents=True)
            skill_file.write_text(
                "---\n"
                "name: aws-cdk-development\n"
                "description: AWS CDK expert.\n"
                "context: fork\n"
                "skills:\n"
                "  - aws-mcp-setup\n"
                "allowed-tools:\n"
                "  - mcp__cdk__*\n"
                "  - Bash(cdk *)\n"
                "hooks:\n"
                "  PreToolUse:\n"
                "    - matcher: Bash(cdk deploy*)\n"
                "      command: aws sts get-caller-identity --query Account --output text\n"
                "      once: true\n"
                "---\n",
                encoding="utf-8",
            )
            scanner = Stage1Scanner(
                adapter,
                repository,
                ScanConfig(min_checked_count=1, min_elapsed_seconds=0, required_source_groups=set()),
                queue.Queue[ScanEvent](),
            )

            scanner.run_foreground(
                [ScanTarget(skill_file.parent.parent, 100, "personal_skill", 2, "foreground", "Skills")]
            )

            records = repository.load_snapshot()
            self.assertEqual(records[0].record_type, "personal_skill")
            self.assertEqual(records[0].name, "aws-cdk-development")
            self.assertEqual(records[0].metadata["referenced_skills"], ["aws-mcp-setup"])
            self.assertEqual(records[0].metadata["context"], "fork")
            self.assertIn("Bash(cdk *)", records[0].metadata["allowed_tools"])

    def test_foreground_scans_metadata_markdown_in_agents_folder(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            agent_file = root / "repo" / ".claude" / "agents" / "aws-cdk-development.md"
            agent_file.parent.mkdir(parents=True)
            agent_file.write_text(
                "---\n"
                "name: aws-cdk-development\n"
                "description: AWS CDK expert.\n"
                "context: fork\n"
                "skills:\n"
                "  - aws-mcp-setup\n"
                "allowed-tools:\n"
                "  - mcp__cdk__*\n"
                "---\n",
                encoding="utf-8",
            )
            scanner = Stage1Scanner(
                adapter,
                repository,
                ScanConfig(min_checked_count=1, min_elapsed_seconds=0, required_source_groups=set()),
                queue.Queue[ScanEvent](),
            )

            scanner.run_foreground(
                [ScanTarget(root / "repo", 60, "common_project_root", 3, "foreground", "Common root")]
            )

            records = repository.load_snapshot()
            self.assertEqual(records[0].record_type, "candidate")
            self.assertEqual(records[0].name, "aws-cdk-development")
            self.assertEqual(records[0].metadata["referenced_skills"], ["aws-mcp-setup"])

    def test_stage1_finds_project_bundled_plugin_skill_file(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            project_root = root / "skill_risk_manager"
            skill_file = (
                project_root
                / "aws-skills"
                / "plugins"
                / "aws-agentic-ai"
                / "skills"
                / "aws-agentic-ai"
                / "SKILL.md"
            )
            skill_file.parent.mkdir(parents=True)
            skill_file.write_text(
                "---\n"
                "name: aws-agentic-ai\n"
                "description: AWS Bedrock AgentCore comprehensive expert.\n"
                "context: fork\n"
                "skills:\n"
                "  - aws-mcp-setup\n"
                "allowed-tools:\n"
                "  - mcp__aws-mcp__*\n"
                "  - Bash(aws bedrock-agentcore *)\n"
                "---\n",
                encoding="utf-8",
            )
            targets = [
                target
                for target in adapter.build_stage1_targets(project_root)
                if project_root in [target.path, *target.path.parents]
            ]
            scanner = Stage1Scanner(
                adapter,
                repository,
                ScanConfig(min_checked_count=1, min_elapsed_seconds=0, required_source_groups=set()),
                queue.Queue[ScanEvent](),
            )

            scanner.run_foreground(targets)

            records = repository.load_snapshot()
            self.assertTrue(any(record.path == skill_file for record in records))
            skill_record = next(record for record in records if record.path == skill_file)
            self.assertEqual(skill_record.record_type, "plugin_skill")
            self.assertEqual(skill_record.name, "aws-agentic-ai")
            self.assertEqual(skill_record.metadata["referenced_skills"], ["aws-mcp-setup"])

    def test_fast_exit_waits_until_skill_inventory_targets_complete(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            readme = root / "README.md"
            readme.write_text("# Not a skill", encoding="utf-8")
            skill_file = root / "plugins" / "pack" / "skills" / "late-skill" / "SKILL.md"
            skill_file.parent.mkdir(parents=True)
            skill_file.write_text("---\nname: Late Skill\ndescription: Found after barrier\n---", encoding="utf-8")
            targets = [
                ScanTarget(readme, 100, "common_project_root", 0, "foreground", "Empty first target"),
                ScanTarget(root / "plugins", 90, "plugin_skill", 10, "skill_inventory", "Plugin inventory"),
            ]
            scanner = Stage1Scanner(
                adapter,
                repository,
                ScanConfig(min_checked_count=1, min_elapsed_seconds=0, required_source_groups=set()),
                queue.Queue[ScanEvent](),
            )

            scanner.run_foreground(targets)

            self.assertTrue(any(record.path == skill_file for record in repository.load_snapshot()))

    def test_old_cache_without_metadata_version_is_reparsed(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            skill_file = root / "claude" / "skills" / "helper" / "SKILL.md"
            skill_file.parent.mkdir(parents=True)
            skill_file.write_text("---\nname: New Name\ndescription: Test\n---", encoding="utf-8")
            repository.save_cache(
                {
                    adapter.path_key(skill_file): {
                        "path": str(skill_file),
                        "size": skill_file.stat().st_size,
                        "mtime_ns": skill_file.stat().st_mtime_ns,
                        "hash": None,
                        "previous_classification": {
                            "name": "Old Name",
                            "record_type": "personal_skill",
                            "scope": "personal",
                            "path": str(skill_file),
                            "source_type": "personal_skill",
                            "confidence": 0.99,
                            "last_modified": skill_file.stat().st_mtime,
                            "status": "discovered",
                            "file_hash": None,
                            "metadata": {},
                        },
                        "last_scanned_at": 1,
                    }
                }
            )
            scanner = Stage1Scanner(
                adapter,
                repository,
                ScanConfig(min_checked_count=1, min_elapsed_seconds=0, required_source_groups=set()),
                queue.Queue[ScanEvent](),
            )

            scanner.run_foreground(
                [ScanTarget(skill_file.parent.parent, 100, "personal_skill", 2, "foreground", "Skills")]
            )

            self.assertEqual(repository.load_snapshot()[0].name, "New Name")

    def test_foreground_defers_low_value_markdown_to_shadow_targets(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            candidate_file = root / "repo" / "notes" / "helper.md"
            candidate_file.parent.mkdir(parents=True)
            candidate_file.write_text("---\nname: Helper\ndescription: Candidate\n---", encoding="utf-8")
            scanner = Stage1Scanner(
                adapter,
                repository,
                ScanConfig(min_checked_count=2, min_elapsed_seconds=0, required_source_groups=set()),
                queue.Queue[ScanEvent](),
            )

            result = scanner.run_foreground(
                [ScanTarget(root / "repo", 60, "common_project_root", 2, "foreground", "Common root")]
            )

            self.assertIsNotNone(result)
            self.assertEqual(repository.load_snapshot(), [])
            self.assertTrue(any(target.path == candidate_file for target in result.remaining_targets))

    def test_foreground_deduplicates_same_file_from_multiple_targets(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            skill_file = root / "claude" / "skills" / "helper" / "SKILL.md"
            skill_file.parent.mkdir(parents=True)
            skill_file.write_text("---\nname: Helper\ndescription: Test\n---", encoding="utf-8")
            target = ScanTarget(skill_file.parent.parent, 100, "personal_skill", 2, "foreground", "Skills")
            scanner = Stage1Scanner(
                adapter,
                repository,
                ScanConfig(min_checked_count=1, min_elapsed_seconds=0, required_source_groups=set()),
                queue.Queue[ScanEvent](),
            )

            scanner.run_foreground([target, target])

            self.assertEqual(len(repository.load_snapshot()), 1)

    def test_foreground_reuses_cache_when_size_and_mtime_match(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            skill_file = root / "claude" / "skills" / "helper" / "SKILL.md"
            skill_file.parent.mkdir(parents=True)
            skill_file.write_text("---\nname: Helper\ndescription: Test\n---", encoding="utf-8")
            target = ScanTarget(skill_file.parent.parent, 100, "personal_skill", 2, "foreground", "Skills")
            config = ScanConfig(min_checked_count=1, min_elapsed_seconds=0, required_source_groups=set())
            Stage1Scanner(adapter, repository, config, queue.Queue[ScanEvent]()).run_foreground([target])

            with patch("skill_manager.backend.stage1_scanner.parse_markdown_header") as parser_mock:
                parser_mock.side_effect = AssertionError("cache should avoid parsing unchanged files")
                Stage1Scanner(adapter, repository, config, queue.Queue[ScanEvent]()).run_foreground([target])

            self.assertEqual(len(repository.load_snapshot()), 1)

    def test_foreground_ignores_non_claude_settings_in_project_scan(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            vscode_settings = root / "repo" / ".vscode" / "settings.json"
            claude_settings = root / "repo" / ".claude" / "settings.json"
            vscode_settings.parent.mkdir(parents=True)
            claude_settings.parent.mkdir(parents=True)
            vscode_settings.write_text("{}", encoding="utf-8")
            claude_settings.write_text("{}", encoding="utf-8")
            scanner = Stage1Scanner(
                adapter,
                repository,
                ScanConfig(min_checked_count=2, min_elapsed_seconds=0, required_source_groups=set()),
                queue.Queue[ScanEvent](),
            )

            scanner.run_foreground(
                [ScanTarget(root / "repo", 60, "common_project_root", 3, "foreground", "Common root")]
            )

            paths = {record.path for record in repository.load_snapshot()}
            self.assertIn(claude_settings, paths)
            self.assertNotIn(vscode_settings, paths)

    def test_shadow_scan_stages_results_without_mutating_snapshot(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            repository.save_snapshot([])
            before_snapshot = repository.snapshot_path.read_text(encoding="utf-8")
            shadow_file = root / "project" / "prompts" / "helper.md"
            shadow_file.parent.mkdir(parents=True)
            shadow_file.write_text("---\nname: Helper\ndescription: Candidate\n---\nBody", encoding="utf-8")
            targets = [ScanTarget(shadow_file.parent, 30, "deferred_candidate", 1, "shadow", "Test shadow")]
            config = ScanConfig(shadow_max_runtime_seconds=10, shadow_max_candidates=10)
            scanner = ShadowScanner(adapter, repository, config, queue.Queue[ScanEvent]())

            scanner.run(targets, CancelToken())

            after_snapshot = repository.snapshot_path.read_text(encoding="utf-8")
            shadow_records = repository.load_shadow_pool()
            self.assertEqual(before_snapshot, after_snapshot)
            self.assertEqual(len(shadow_records), 1)
            self.assertEqual(shadow_records[0].record_type, "candidate")

    def test_shadow_scan_respects_candidate_budget(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            shadow_dir = root / "project" / "prompts"
            shadow_dir.mkdir(parents=True)
            for index in range(3):
                (shadow_dir / f"helper-{index}.md").write_text(
                    f"---\nname: Helper {index}\ndescription: Candidate\n---",
                    encoding="utf-8",
                )
            scanner = ShadowScanner(
                adapter,
                repository,
                ScanConfig(shadow_max_candidates=1, shadow_max_runtime_seconds=10),
                queue.Queue[ScanEvent](),
            )

            scanner.run([ScanTarget(shadow_dir, 30, "deferred_candidate", 1, "shadow", "Budget")], CancelToken())

            self.assertEqual(len(repository.load_shadow_pool()), 1)

    def test_shadow_scan_honors_pre_cancelled_token(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            adapter = get_platform_adapter()
            target_dir = root / "project"
            target_dir.mkdir()
            (target_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")
            token = CancelToken()
            token.cancel()
            scanner = ShadowScanner(adapter, repository, ScanConfig(), queue.Queue[ScanEvent]())

            scanner.run([ScanTarget(target_dir, 30, "deferred_candidate", 1, "shadow", "Cancelled")], token)

            self.assertEqual(repository.load_shadow_pool(), [])

    def test_fast_exit_waits_for_required_groups_and_budget(self) -> None:
        config = ScanConfig(
            min_checked_count=3,
            min_elapsed_seconds=0,
            recent_window_size=2,
            required_source_groups={"personal"},
        )
        tracker = FastExitTracker(config)
        tracker.mark_checked(False)
        tracker.mark_checked(False)
        tracker.mark_checked(False)
        self.assertFalse(tracker.should_exit())
        tracker.mark_required_attempted("personal")
        self.assertTrue(tracker.should_exit())

    def test_fast_exit_uses_recent_discovery_drop_after_required_groups(self) -> None:
        config = ScanConfig(
            min_checked_count=6,
            min_elapsed_seconds=0,
            recent_window_size=3,
            discovery_drop_ratio=0.5,
            required_source_groups={"personal"},
        )
        tracker = FastExitTracker(config)
        tracker.mark_required_attempted("personal")
        for found in [True, True, True, False, False, False]:
            tracker.mark_checked(found)

        self.assertTrue(tracker.should_exit())


if __name__ == "__main__":
    unittest.main()
