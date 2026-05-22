from __future__ import annotations

import unittest

from skill_risk_manager.backend.classifier import classify_path
from skill_risk_manager.backend.parser import parse_frontmatter
from tests.test_support import writable_temp_dir


RICH_SKILL_FRONTMATTER = """---
name: aws-cdk-development
description: AWS Cloud Development Kit (CDK) expert for building cloud infrastructure with TypeScript/Python.
context: fork
skills:
  - aws-mcp-setup
allowed-tools:
  - mcp__cdk__*
  - mcp__aws-mcp__*
  - mcp__awsdocs__*
  - Bash(cdk *)
  - Bash(npm *)
  - Bash(npx *)
  - Bash(aws cloudformation *)
  - Bash(aws sts get-caller-identity)
hooks:
  PreToolUse:
    - matcher: Bash(cdk deploy*)
      command: aws sts get-caller-identity --query Account --output text
      once: true
---
Body
"""


class ParserClassifierTests(unittest.TestCase):
    def test_parse_frontmatter_reads_simple_yaml_header(self) -> None:
        header = "---\nname: PDF Helper\ndescription: Reads PDFs\n---\n# Body"

        frontmatter = parse_frontmatter(header)

        self.assertEqual(frontmatter["name"], "PDF Helper")
        self.assertEqual(frontmatter["description"], "Reads PDFs")

    def test_parse_frontmatter_returns_empty_without_opening_marker(self) -> None:
        self.assertEqual(parse_frontmatter("# Plain Markdown\nname: no"), {})

    def test_parse_frontmatter_requires_closing_delimiter(self) -> None:
        header = "---\nname: Incomplete\ndescription: Missing close\n# Body"

        self.assertEqual(parse_frontmatter(header), {})

    def test_parse_frontmatter_reads_rich_skill_metadata(self) -> None:
        frontmatter = parse_frontmatter(RICH_SKILL_FRONTMATTER)

        self.assertEqual(frontmatter["name"], "aws-cdk-development")
        self.assertEqual(frontmatter["context"], "fork")
        self.assertEqual(frontmatter["skills"], ["aws-mcp-setup"])
        self.assertIn("Bash(cdk *)", frontmatter["allowed-tools"])
        self.assertEqual(
            frontmatter["hooks"]["PreToolUse"][0]["command"],
            "aws sts get-caller-identity --query Account --output text",
        )
        self.assertIs(frontmatter["hooks"]["PreToolUse"][0]["once"], True)

    def test_confirmed_skill_classification_by_scope(self) -> None:
        with writable_temp_dir() as root:
            personal = root / ".claude" / "skills" / "pdf-helper" / "SKILL.md"
            project = root / "repo" / ".claude" / "skills" / "test-helper" / "SKILL.md"
            plugin = root / ".claude" / "plugins" / "pack" / "skills" / "plugin-helper" / "SKILL.md"
            frontmatter = {"name": "PDF Helper", "description": "Reads PDFs"}

            self.assertEqual(classify_path(personal, "personal_skill", frontmatter).record_type, "personal_skill")
            self.assertEqual(classify_path(project, "project_skill", frontmatter).record_type, "project_skill")
            self.assertEqual(classify_path(plugin, "plugin_skill", frontmatter).record_type, "plugin_skill")

    def test_skill_path_without_closed_metadata_is_only_candidate(self) -> None:
        with writable_temp_dir() as root:
            skill_path = root / ".claude" / "skills" / "pdf-helper" / "SKILL.md"

            classification = classify_path(skill_path, "personal_skill", {})

            self.assertEqual(classification.record_type, "candidate")
            self.assertFalse(classification.metadata.get("frontmatter_verified", False))

    def test_confirmed_skill_uses_frontmatter_name_and_metadata(self) -> None:
        with writable_temp_dir() as root:
            skill_path = root / ".claude" / "skills" / "folder-name" / "SKILL.md"
            frontmatter = parse_frontmatter(RICH_SKILL_FRONTMATTER)

            classification = classify_path(skill_path, "personal_skill", frontmatter)

            self.assertEqual(classification.record_type, "personal_skill")
            self.assertEqual(classification.name, "aws-cdk-development")
            self.assertEqual(classification.metadata["context"], "fork")
            self.assertEqual(classification.metadata["referenced_skills"], ["aws-mcp-setup"])
            self.assertIn("Bash(cdk *)", classification.metadata["allowed_tools"])

    def test_legacy_command_config_memory_and_candidates(self) -> None:
        with writable_temp_dir() as root:
            command = classify_path(root / ".claude" / "commands" / "build.md", "legacy_command")
            settings = classify_path(root / ".claude" / "settings.json", "claude_config")
            memory = classify_path(root / "CLAUDE.md", "claude_config")
            outside_skill = classify_path(root / "random" / "SKILL.md", "deferred_candidate")
            skill_like = classify_path(
                root / "notes" / "helper.md",
                "deferred_candidate",
                {"name": "Helper", "description": "Useful prompt"},
            )

            self.assertEqual(command.record_type, "legacy_command")
            self.assertEqual(settings.record_type, "claude_config")
            self.assertEqual(memory.record_type, "claude_memory")
            self.assertEqual(outside_skill.record_type, "candidate")
            self.assertEqual(skill_like.record_type, "candidate")

    def test_regular_markdown_is_ignored(self) -> None:
        with writable_temp_dir() as root:
            classification = classify_path(root / "README.md", "common_project_root")

            self.assertEqual(classification.record_type, "regular_markdown")
            self.assertEqual(classification.status, "ignored")

    def test_non_claude_settings_json_is_ignored(self) -> None:
        with writable_temp_dir() as root:
            vscode_settings = classify_path(root / "project" / ".vscode" / "settings.json", "common_project_root")
            claude_settings = classify_path(root / "project" / ".claude" / "settings.json", "common_project_root")

            self.assertEqual(vscode_settings.status, "ignored")
            self.assertEqual(claude_settings.record_type, "claude_config")


if __name__ == "__main__":
    unittest.main()
