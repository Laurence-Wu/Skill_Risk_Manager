from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SkillRecord:
    name: str
    scope: str
    record_type: str
    path: str
    confidence: float
    status: str
    description: str = ""

    def to_row(self) -> dict[str, object]:
        return {
            "Name": self.name,
            "Scope": self.scope,
            "Type": self.record_type,
            "Path": self.path,
            "Confidence": f"{self.confidence:.2f}",
            "Status": self.status,
            "_record": self,
        }

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateRecord:
    path: str
    reason: str
    confidence: float
    source: str
    suggested_type: str
    status: str = "staged"

    def to_row(self) -> dict[str, object]:
        return {
            "Path": self.path,
            "Reason": self.reason,
            "Confidence": f"{self.confidence:.2f}",
            "Source": self.source,
            "Suggested Type": self.suggested_type,
            "_record": self,
        }

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class LogEntry:
    level: str
    message: str
    timestamp: float
    event_type: str = "info"

