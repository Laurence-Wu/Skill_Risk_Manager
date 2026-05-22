from __future__ import annotations

import unittest

from skill_risk_manager.backend.cache import cache_metadata, file_hash, stat_matches_cache
from skill_risk_manager.backend.models import ScanEvent, ScanTarget
from skill_risk_manager.backend.priority_queue import ScanPriorityQueue
from skill_risk_manager.storage.repository import Repository
from tests.test_support import writable_temp_dir


class PriorityCacheStorageTests(unittest.TestCase):
    def test_priority_queue_pops_highest_priority_first_and_keeps_insert_order(self) -> None:
        with writable_temp_dir() as root:
            low = ScanTarget(root / "low", 10, "low", 0, "foreground", "low")
            high_first = ScanTarget(root / "high-first", 90, "high", 0, "foreground", "high-first")
            high_second = ScanTarget(root / "high-second", 90, "high", 0, "foreground", "high-second")
            priority_queue = ScanPriorityQueue([low, high_first, high_second])

            self.assertEqual(priority_queue.pop(), high_first)
            self.assertEqual(priority_queue.pop(), high_second)
            self.assertEqual(priority_queue.pop(), low)

    def test_cache_metadata_matches_until_file_changes(self) -> None:
        with writable_temp_dir() as root:
            file_path = root / "SKILL.md"
            file_path.write_text("first", encoding="utf-8")
            metadata = cache_metadata(file_path, file_hash(file_path))

            self.assertTrue(stat_matches_cache(file_path, metadata))

            file_path.write_text("second and longer", encoding="utf-8")

            self.assertFalse(stat_matches_cache(file_path, metadata))

    def test_repository_round_trips_cache_summary_snapshot_and_logs(self) -> None:
        with writable_temp_dir() as root:
            repository = Repository(root / "runtime")
            repository.save_cache({"a": {"size": 1}})
            repository.append_scan_event(ScanEvent("test_event", "message", {"ok": True}))
            repository.append_error(root / "missing", "OSError", "failed")

            self.assertEqual(repository.load_cache()["a"]["size"], 1)
            self.assertTrue(repository.scan_log_path.exists())
            self.assertTrue(repository.error_log_path.exists())
            self.assertEqual(repository.scan_log_path.read_text(encoding="utf-8").count("event_type"), 1)


if __name__ == "__main__":
    unittest.main()

