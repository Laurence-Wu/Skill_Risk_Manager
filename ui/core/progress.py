from __future__ import annotations


PRIMARY_PROGRESS_CAP = 0.70
SNAPSHOT_PROGRESS = 0.72
CONTINUATION_PROGRESS_RANGE = 0.26
MAX_CONTINUATION_PROGRESS = 0.98


def estimated_phase_progress(payload: dict, cap: float = 0.95) -> float:
    files_checked = int(payload.get("files_checked", 0))
    directories_checked = int(payload.get("directories_checked", 0))
    estimate = (files_checked + directories_checked) / 500
    return max(0.02, min(cap, estimate))


def primary_scan_progress(payload: dict) -> tuple[float, float]:
    phase_progress = estimated_phase_progress(payload)
    return max(0.02, min(PRIMARY_PROGRESS_CAP, phase_progress * PRIMARY_PROGRESS_CAP)), phase_progress


def continuation_scan_progress(payload: dict) -> tuple[float, float]:
    phase_progress = estimated_phase_progress(payload)
    overall_progress = SNAPSHOT_PROGRESS + phase_progress * CONTINUATION_PROGRESS_RANGE
    return max(SNAPSHOT_PROGRESS, min(MAX_CONTINUATION_PROGRESS, overall_progress)), phase_progress


def expected_total_files(files_checked: int, progress: float) -> int:
    if files_checked <= 0:
        return 0
    safe_progress = max(0.01, min(progress, MAX_CONTINUATION_PROGRESS))
    return max(files_checked, int(files_checked / safe_progress))


def snapshot_expected_total(files_checked: int) -> int:
    if files_checked <= 0:
        return 0
    return max(files_checked, int(files_checked / SNAPSHOT_PROGRESS))
