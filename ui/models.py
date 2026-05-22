from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillRecord:
    name: str
    scope: str
    record_type: str
    path: str
    confidence: float
    status: str
    description: str = ""
    risk_score: int = 0
    risk_level: str = "low"
    risk_summary: str = "No major risk indicators detected."
    risk_categories: tuple[str, ...] = ()
    top_finding: str = ""
    suggested_action: str = "trust"

    def to_row(self) -> dict[str, object]:
        return {
            "Name": self.name,
            "Type": self.record_type,
            "Scope": self.scope,
            "Risk": self.risk_level.title(),
            "Score": self.risk_score,
            "Summary": self.risk_summary,
            "Path": self.path,
            "Confidence": f"{self.confidence:.2f}",
            "Status": self.status,
            "_record": self,
            "_row_kind": self.risk_level,
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
    risk_score: int = 0
    risk_level: str = "low"
    risk_summary: str = "No major risk indicators detected."
    risk_categories: tuple[str, ...] = ()
    top_finding: str = ""
    suggested_action: str = "trust"

    def to_row(self) -> dict[str, object]:
        return {
            "Name": _name_from_path(self.path),
            "Path": self.path,
            "Risk": self.risk_level.title(),
            "Score": self.risk_score,
            "Top Finding": self.top_finding or self.risk_summary,
            "Action": self.suggested_action.title(),
            "Confidence": f"{self.confidence:.2f}",
            "Source": self.source,
            "Suggested Type": self.suggested_type,
            "Reason": self.reason,
            "_record": self,
            "_row_kind": self.risk_level,
        }

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class LogEntry:
    level: str
    message: str
    timestamp: float
    event_type: str = "info"


def _name_from_path(path_text: str) -> str:
    path = Path(path_text)
    if path.name.lower() == "skill.md" and path.parent.name:
        return path.parent.name
    return path.stem or path.name or path_text
