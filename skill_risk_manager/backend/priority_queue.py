from __future__ import annotations

import heapq
from dataclasses import dataclass, field

from skill_risk_manager.backend.models import ScanTarget


@dataclass(order=True)
class _QueuedTarget:
    sort_priority: int
    insertion_order: int
    target: ScanTarget = field(compare=False)


class ScanPriorityQueue:
    def __init__(self, targets: list[ScanTarget] | None = None) -> None:
        self._items: list[_QueuedTarget] = []
        self._counter = 0
        if targets:
            self.extend(targets)

    def push(self, target: ScanTarget) -> None:
        heapq.heappush(self._items, _QueuedTarget(-target.priority, self._counter, target))
        self._counter += 1

    def extend(self, targets: list[ScanTarget]) -> None:
        for target in targets:
            self.push(target)

    def pop(self) -> ScanTarget:
        return heapq.heappop(self._items).target

    def to_list(self) -> list[ScanTarget]:
        queued_items = sorted(self._items)
        return [queued_item.target for queued_item in queued_items]

    def __len__(self) -> int:
        return len(self._items)

