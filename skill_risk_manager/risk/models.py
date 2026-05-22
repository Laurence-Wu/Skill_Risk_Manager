from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


RiskLevel = Literal["none", "low", "medium", "high", "critical"]
RiskCategory = Literal[
    "tool_access",
    "filesystem",
    "network",
    "command_execution",
    "secrets",
    "mcp",
    "hooks",
    "prompt_injection",
    "persistence",
    "uncertainty",
]


@dataclass(frozen=True)
class RiskFinding:
    rule_id: str
    category: RiskCategory
    severity: RiskLevel
    confidence: float
    message: str
    evidence: str = ""
    suggestion: str = ""
    score: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity,
            "confidence": self.confidence,
            "message": self.message,
            "evidence": self.evidence,
            "suggestion": self.suggestion,
        }


@dataclass(frozen=True)
class RiskProfile:
    score: int
    level: RiskLevel
    categories: list[RiskCategory] = field(default_factory=list)
    findings: list[RiskFinding] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "level": self.level,
            "categories": list(self.categories),
            "findings": [finding.to_dict() for finding in self.findings],
            "summary": self.summary,
        }
