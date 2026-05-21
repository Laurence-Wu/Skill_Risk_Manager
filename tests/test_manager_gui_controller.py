from __future__ import annotations

import time
import unittest
from pathlib import Path

from manager_GUI.core.backend_controller import BackendController
from manager_GUI.core.events import CANDIDATE_STAGED, SNAPSHOT_COMMITTED
from manager_GUI.core.mock_controller import MockController
from skill_manager.backend.models import ScanConfig, ScanEvent as BackendScanEvent
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
