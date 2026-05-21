from __future__ import annotations

import argparse
import json
import queue
import shutil
from pathlib import Path

from skill_manager.backend import ScanService
from skill_manager.backend.models import ScanConfig, ScanEvent
from skill_manager.platform import get_platform_adapter
from skill_manager.platform.base import PlatformAdapter
from skill_manager.storage.repository import Repository


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m skill_manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Run scanner commands")
    scan_parser.add_argument("--stage1", action="store_true", help="Run Stage 1 foreground scan")
    scan_parser.add_argument("--shadow", action="store_true", help="Run shadow scan after Stage 1")
    scan_parser.add_argument("--project-root", type=Path, default=Path.cwd())

    subparsers.add_parser("list", help="List saved Stage 1 records")
    subparsers.add_parser("open-config", help="Open Claude config root")

    export_parser = subparsers.add_parser("export-report", help="Export snapshot and summary JSON")
    export_parser.add_argument("output", type=Path)

    args = parser.parse_args()
    adapter = get_platform_adapter()
    repository = Repository.default()

    if args.command == "scan":
        run_scan(args.stage1, args.shadow, args.project_root, adapter, repository)
    elif args.command == "list":
        list_records(repository)
    elif args.command == "open-config":
        adapter.open_folder(adapter.claude_config_root())
    elif args.command == "export-report":
        export_report(repository, args.output)


def run_scan(
    stage1: bool,
    shadow: bool,
    project_root: Path,
    adapter: PlatformAdapter,
    repository: Repository,
) -> None:
    if not stage1 and not shadow:
        stage1 = True
    if shadow:
        stage1 = True
    event_queue: queue.Queue[ScanEvent] = queue.Queue()
    service = ScanService(adapter, repository, ScanConfig(min_elapsed_seconds=0), event_queue)
    service.run_pipeline(project_root, stage1=stage1, shadow=shadow)
    drain_events(event_queue)


def drain_events(event_queue: queue.Queue[ScanEvent]) -> None:
    while not event_queue.empty():
        event = event_queue.get()
        print(f"{event.event_type}: {event.message}")


def list_records(repository: Repository) -> None:
    records = repository.load_snapshot()
    if not records:
        print("No Stage 1 snapshot found.")
        return
    for record in records:
        print(f"{record.record_type}\t{record.scope}\t{record.name}\t{record.path}")


def export_report(repository: Repository, output_path: Path) -> None:
    output_path.mkdir(parents=True, exist_ok=True)
    if repository.snapshot_path.exists():
        shutil.copy2(repository.snapshot_path, output_path / repository.snapshot_path.name)
    if repository.summary_path.exists():
        shutil.copy2(repository.summary_path, output_path / repository.summary_path.name)
    if repository.shadow_pool_path.exists():
        shutil.copy2(repository.shadow_pool_path, output_path / repository.shadow_pool_path.name)
    manifest = {
        "snapshot": str(output_path / repository.snapshot_path.name),
        "summary": str(output_path / repository.summary_path.name),
        "shadow_pool": str(output_path / repository.shadow_pool_path.name),
    }
    with (output_path / "manifest.json").open("w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, indent=2)
    print(f"Exported report to {output_path}")


if __name__ == "__main__":
    main()
