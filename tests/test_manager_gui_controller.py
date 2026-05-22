from __future__ import annotations

import time
import unittest
from pathlib import Path

from manager_GUI.core.backend_controller import BackendController
from manager_GUI.core.events import (
    CANDIDATE_STAGED,
    CONTINUATION_PROGRESS,
    CONTINUATION_STARTED,
    SCAN_PROGRESS,
    SNAPSHOT_COMMITTED,
    ScanEvent,
)
from manager_GUI.core.mock_controller import MockController
from manager_GUI.core.record_mapping import candidate_from_backend_record, skill_from_backend_record
from manager_GUI.core.state import AppState
from manager_GUI.ui.tables import _effective_page_size, _logs_signature, _rows_signature
from manager_GUI.ui.shell import NAV_ITEMS, security_label
from manager_GUI.ui.views.logs import log_to_row
from manager_GUI.ui.views.risk import risk_rows_from_state
from manager_GUI.ui.views.scan import scan_toolbar_actions_for_status
from manager_GUI.ui.views.skills import ranked_skill_rows
from skill_manager.backend.models import ScanConfig, ScanEvent as BackendScanEvent, SkillRecord as BackendSkillRecord
from skill_manager.storage.repository import Repository
from tests.test_support import writable_temp_dir


class ManagerGuiControllerTests(unittest.TestCase):
    def test_mock_controller_commits_snapshot_before_staging_candidates(self) -> None:
        controller = MockController(phase_delay_seconds=0)

        self.assertTrue(controller.start_scan())
        self._wait_until_idle(controller)
        events = controller.poll_events()
        event_types = [event.type for event in events]
        state = controller.get_state()

        self.assertIn(SNAPSHOT_COMMITTED, event_types)
        self.assertIn(CANDIDATE_STAGED, event_types)
        self.assertLess(event_types.index(SNAPSHOT_COMMITTED), event_types.index(CANDIDATE_STAGED))
        self.assertEqual(len(state.confirmed_skills), 5)
        self.assertEqual(len(state.candidates_snapshot), 2)
        self.assertEqual(len(state.candidates_staged), 2)
        self.assertEqual(state.progress_mode, "continuation")

    def test_mock_controller_rejects_duplicate_start_while_running(self) -> None:
        controller = MockController(phase_delay_seconds=0.05)

        self.assertTrue(controller.start_scan())
        self.assertFalse(controller.start_scan())
        controller.cancel_scan()
        self._wait_until_idle(controller)
        controller.poll_events()

        self.assertEqual(controller.get_state().scan_status, "cancelled")

    def test_backend_controller_uses_full_computer_scan_and_security_level(self) -> None:
        with writable_temp_dir() as root:
            service = RecordingScanService()
            controller = BackendController(
                repository=Repository(root / "runtime"),
                service=service,
                open_folder_callback=lambda _path: None,
            )

            self.assertTrue(controller.start_scan())
            self._wait_until_idle(controller)
            controller.poll_events()
            controller.set_security_level("advanced")
            self.assertTrue(controller.start_scan())
            self._wait_until_idle(controller)
            controller.poll_events()

            self.assertEqual(service.computer_scan_levels, ["base", "advanced"])

    def test_backend_controller_treats_permission_scan_errors_as_warnings(self) -> None:
        with writable_temp_dir() as root:
            controller = BackendController(
                repository=Repository(root / "runtime"),
                service=RecordingScanService(),
                open_folder_callback=lambda _path: None,
            )
            controller._backend_events.put(  # noqa: SLF001 - exercises backend event conversion boundary.
                BackendScanEvent("scan_error", "Permission denied", {"path": str(root), "error_type": "PermissionError"})
            )

            events = controller.poll_events()
            state = controller.get_state()

            self.assertEqual(events[0].type, "scan_warning")
            self.assertNotEqual(state.scan_status, "error")
            self.assertEqual(state.logs[-1].level, "warning")

    def test_backend_controller_actions_update_state_and_logs(self) -> None:
        with writable_temp_dir() as root:
            opened_folders: list[Path] = []
            controller = BackendController(
                repository=Repository(root / "runtime"),
                service=RecordingScanService(),
                open_folder_callback=opened_folders.append,
            )
            candidate = controller.get_state().candidates_snapshot
            self.assertEqual(candidate, [])

            from manager_GUI.models import CandidateRecord

            staged = CandidateRecord(str(root / "candidate" / "SKILL.md"), "review", 0.7, "snapshot", "candidate")
            controller._state.candidates_snapshot.append(staged)  # noqa: SLF001 - seeds GUI state without scanning.
            controller.promote_candidate(staged)
            controller.copy_path(str(root), lambda _value: None)
            controller.open_folder(str(root / "file.md"))
            exported_path = controller.export_logs(root / "logs.csv")

            state = controller.get_state()
            self.assertEqual(len(state.confirmed_skills), 1)
            self.assertTrue(exported_path.exists())
            self.assertEqual(opened_folders, [root])

    def test_backend_controller_exports_skills_and_risk_report(self) -> None:
        from manager_GUI.models import CandidateRecord, SkillRecord

        with writable_temp_dir() as root:
            controller = BackendController(
                repository=Repository(root / "runtime"),
                service=RecordingScanService(),
                open_folder_callback=lambda _path: None,
            )
            controller._state.confirmed_skills = [  # noqa: SLF001 - seeds GUI state for export boundary.
                SkillRecord(
                    "deploy",
                    "project",
                    "project_skill",
                    "deploy/SKILL.md",
                    0.91,
                    "discovered",
                    risk_score=72,
                    risk_level="high",
                    risk_categories=("command_execution",),
                    top_finding="Shell access",
                )
            ]
            controller._state.candidates_staged = [  # noqa: SLF001 - seeds GUI state for export boundary.
                CandidateRecord(
                    "candidate.md",
                    "review",
                    0.55,
                    "staged",
                    "candidate",
                    risk_score=80,
                    risk_level="critical",
                    risk_categories=("secrets",),
                    top_finding="Secret reference",
                )
            ]

            skills_path = controller.export_skills(root / "skills.csv")
            risk_path = controller.export_risk_report(root / "risk.csv")

            self.assertIn("deploy", skills_path.read_text(encoding="utf-8"))
            self.assertIn("Secret reference", risk_path.read_text(encoding="utf-8"))

    def test_app_state_keeps_global_progress_and_counts_monotonic(self) -> None:
        state = AppState()

        state.apply_event(
            ScanEvent(
                SCAN_PROGRESS,
                progress=0.4,
                files_checked=80,
                directories_checked=10,
                payload={"progress_mode": "primary", "expected_total_files": 200},
            )
        )
        state.apply_event(
            ScanEvent(
                CONTINUATION_STARTED,
                progress=0.2,
                files_checked=80,
                directories_checked=10,
                payload={"progress_mode": "continuation", "expected_total_files": 200},
            )
        )
        state.apply_event(
            ScanEvent(
                CONTINUATION_PROGRESS,
                progress=0.35,
                files_checked=20,
                directories_checked=4,
                payload={"progress_mode": "continuation", "expected_total_files": 100},
            )
        )

        self.assertEqual(state.progress, 0.4)
        self.assertEqual(state.files_checked, 80)
        self.assertEqual(state.directories_checked, 10)
        self.assertEqual(state.expected_total_files, 200)

    def test_gui_record_mapping_extracts_risk_fields(self) -> None:
        backend_record = BackendSkillRecord(
            name="Deploy",
            record_type="personal_skill",
            scope="personal",
            path=Path("SKILL.md"),
            source_type="personal_skill",
            confidence=0.99,
            last_modified=0,
            metadata={
                "risk": {
                    "score": 80,
                    "level": "critical",
                    "categories": ["command_execution"],
                    "summary": "Critical risk: shell execution.",
                    "findings": [{"message": "Shell execution tool access detected."}],
                }
            },
        )

        gui_record = skill_from_backend_record(backend_record)
        candidate_record = candidate_from_backend_record(backend_record, "snapshot")

        self.assertEqual(gui_record.risk_score, 80)
        self.assertEqual(gui_record.risk_level, "critical")
        self.assertEqual(gui_record.suggested_action, "quarantine")
        self.assertEqual(candidate_record.top_finding, "Shell execution tool access detected.")

    def test_app_state_risk_counts_are_global(self) -> None:
        from manager_GUI.models import CandidateRecord, SkillRecord

        state = AppState()
        state.confirmed_skills = [
            SkillRecord("safe", "personal", "personal_skill", "a", 0.9, "discovered", risk_level="low"),
            SkillRecord("danger", "personal", "personal_skill", "b", 0.9, "discovered", risk_level="critical"),
        ]
        state.candidates_snapshot = [
            CandidateRecord("c", "review", 0.6, "snapshot", "candidate", risk_level="high")
        ]
        state.candidates_staged = [
            CandidateRecord("d", "review", 0.6, "continuation", "candidate", risk_level="medium")
        ]

        self.assertEqual(state.risk_counts, {"critical": 1, "high": 1, "medium": 1, "low": 1})

    def test_candidate_actions_preserve_risk_metadata(self) -> None:
        from manager_GUI.models import CandidateRecord

        state = AppState()
        candidate = CandidateRecord(
            "candidate.md",
            "review",
            0.6,
            "snapshot",
            "candidate",
            risk_score=87,
            risk_level="critical",
            risk_summary="Critical risk.",
            risk_categories=("command_execution",),
            top_finding="Shell execution",
            suggested_action="quarantine",
        )
        state.candidates_snapshot = [candidate]

        state.promote_candidate(candidate)
        promoted = state.confirmed_skills[0]

        self.assertEqual(promoted.risk_score, 87)
        self.assertEqual(promoted.risk_level, "critical")
        self.assertEqual(promoted.suggested_action, "quarantine")

    def test_lazy_table_helpers_keep_initial_render_small_and_detect_risk_changes(self) -> None:
        rows = [{"Path": "a.md", "Risk": "Low", "Score": 1}, {"Path": "b.md", "Risk": "High", "Score": 70}]
        changed_rows = [{"Path": "a.md", "Risk": "Critical", "Score": 90}, {"Path": "b.md", "Risk": "High", "Score": 70}]

        self.assertEqual(_effective_page_size(90, lazy=True), 40)
        self.assertEqual(_effective_page_size(25, lazy=True), 25)
        self.assertNotEqual(_rows_signature(rows, None), _rows_signature(changed_rows, None))

    def test_lazy_log_signature_tracks_visible_limit(self) -> None:
        from manager_GUI.models import LogEntry

        logs = [LogEntry("info", "message", 1.0)]

        self.assertNotEqual(_logs_signature(logs, "all", 50), _logs_signature(logs, "all", 120))

    def test_shell_navigation_and_security_label_include_risk_and_mode(self) -> None:
        self.assertIn(("Risk", "risk"), NAV_ITEMS)
        self.assertEqual(security_label("base"), "Base Mode")
        self.assertEqual(security_label("advanced"), "Advanced Mode")

    def test_scan_toolbar_actions_follow_status(self) -> None:
        self.assertEqual(scan_toolbar_actions_for_status("ready"), (("Start Scan", "start_scan", "primary"),))
        self.assertEqual(
            scan_toolbar_actions_for_status("scanning"),
            (("Pause", "pause_scan", "secondary"), ("Cancel", "cancel_scan", "danger")),
        )
        self.assertEqual(
            scan_toolbar_actions_for_status("paused"),
            (("Resume", "resume_scan", "primary"), ("Cancel", "cancel_scan", "danger")),
        )

    def test_risk_rows_include_all_global_records(self) -> None:
        from manager_GUI.models import CandidateRecord, SkillRecord

        state = AppState()
        state.confirmed_skills = [
            SkillRecord("skill", "personal", "personal_skill", "a/SKILL.md", 0.9, "discovered", risk_level="high")
        ]
        state.candidates_snapshot = [
            CandidateRecord("b.md", "review", 0.5, "snapshot", "candidate", risk_level="medium")
        ]
        state.candidates_staged = [
            CandidateRecord("c.md", "review", 0.5, "staged", "candidate", risk_level="critical")
        ]

        rows = risk_rows_from_state(state)

        self.assertEqual(len(rows), 3)
        self.assertEqual({row["Source"] for row in rows}, {"Skills", "Snapshot", "Staged"})

    def test_skills_rank_by_risk_score_descending(self) -> None:
        from manager_GUI.models import SkillRecord

        rows = ranked_skill_rows(
            [
                SkillRecord("low", "personal", "personal_skill", "low.md", 0.9, "discovered", risk_score=10, risk_level="low"),
                SkillRecord("critical", "personal", "personal_skill", "critical.md", 0.9, "discovered", risk_score=92, risk_level="critical"),
                SkillRecord("high", "personal", "personal_skill", "high.md", 0.9, "discovered", risk_score=70, risk_level="high"),
            ]
        )

        self.assertEqual([row["Name"] for row in rows], ["critical", "high", "low"])

    def test_log_to_row_maps_table_columns_and_path(self) -> None:
        from manager_GUI.models import LogEntry

        row = log_to_row(LogEntry("success", "Exported logs: C:\\tmp\\logs.csv", 1.0, "export"))

        self.assertEqual(row["Level"], "Success")
        self.assertEqual(row["Event"], "export")
        self.assertIn("logs.csv", row["Path"])

    def _wait_until_idle(self, controller: MockController) -> None:
        deadline = time.monotonic() + 2
        while controller.is_running and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertFalse(controller.is_running)


class RecordingScanService:
    def __init__(self) -> None:
        self.config = ScanConfig()
        self.computer_scan_levels: list[str] = []

    def run_computer_scan(self, *, security_level, fast_cancel_token, shadow_cancel_token):
        self.computer_scan_levels.append(security_level)
        return None

    def run_pipeline(
        self,
        project_root,
        *,
        stage1,
        shadow,
        fast_cancel_token,
        shadow_cancel_token,
    ):
        return None


if __name__ == "__main__":
    unittest.main()
