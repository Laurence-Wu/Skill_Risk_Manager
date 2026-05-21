from __future__ import annotations

import time
from dataclasses import dataclass, field


SCAN_STARTED = "scan_started"
SCAN_PROGRESS = "scan_progress"
SNAPSHOT_COMMITTED = "snapshot_committed"
CONTINUATION_STARTED = "continuation_started"
CONTINUATION_PROGRESS = "continuation_progress"
CANDIDATE_STAGED = "candidate_staged"
SCAN_PAUSED = "scan_paused"
SCAN_RESUMED = "scan_resumed"
SCAN_CANCELLED = "scan_cancelled"
SCAN_COMPLETED = "scan_completed"
SCAN_ERROR = "scan_error"
SCAN_WARNING = "scan_warning"


@dataclass(frozen=True)
class ScanEvent:
    type: str
    message: str = ""
    progress: float = 0.0
    current_path: str = ""
    files_checked: int = 0
    directories_checked: int = 0
    potential_items: int = 0
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
