from __future__ import annotations

from typing import TYPE_CHECKING

from skill_risk_manager.risk.extractors import record_to_text
from skill_risk_manager.risk.models import RiskFinding, RiskLevel, RiskProfile
from skill_risk_manager.risk.policy import RiskPolicy, load_policy
from skill_risk_manager.risk.rules import TEXT_RULES

if TYPE_CHECKING:
    from skill_risk_manager.backend.models import SkillRecord


def analyze_record(record: SkillRecord, policy: RiskPolicy | None = None) -> RiskProfile:
    policy = policy or load_policy("base")
    text = record_to_text(record, policy)
    findings = [finding for rule in TEXT_RULES if (finding := rule.match(text))]
    categories = sorted({finding.category for finding in findings})

    score = max((finding.score for finding in findings), default=0)
    score += _combo_bonus(categories, policy)
    if record.record_type == "candidate" or record.confidence < 0.7:
        score += 10
        categories = sorted({*categories, "uncertainty"})
    if record.scope in {"config", "plugin"}:
        score += 5
    score = max(0, min(100, score))
    level = score_to_level(score, policy)
    return RiskProfile(
        score=score,
        level=level,
        categories=categories,
        findings=sorted(findings, key=lambda finding: finding.score, reverse=True),
        summary=summarize_risk(level, findings),
    )


def attach_risk(record: SkillRecord, policy: RiskPolicy | None = None) -> SkillRecord:
    profile = analyze_record(record, policy)
    record.metadata["risk"] = profile.to_dict()
    if record.record_type == "candidate" and profile.level in {"critical", "high"}:
        record.status = "needs_review"
    return record


def score_to_level(score: int, policy: RiskPolicy | None = None) -> RiskLevel:
    policy = policy or load_policy("base")
    if score >= policy.critical_threshold:
        return "critical"
    if score >= policy.high_threshold:
        return "high"
    if score >= policy.medium_threshold:
        return "medium"
    return "low"


def summarize_risk(level: RiskLevel, findings: list[RiskFinding]) -> str:
    if not findings:
        return "No major risk indicators detected."
    top_finding = max(findings, key=lambda finding: finding.score)
    return f"{level.title()} risk: {top_finding.message}"


def _combo_bonus(categories: list[str], policy: RiskPolicy) -> int:
    category_set = set(categories)
    bonus = 0
    if {"secrets", "network"}.issubset(category_set):
        bonus += policy.combo_bonuses.get("secrets+network", 20)
    if {"command_execution", "filesystem"}.issubset(category_set):
        bonus += policy.combo_bonuses.get("command_execution+filesystem", 15)
    if {"command_execution", "network"}.issubset(category_set):
        bonus += policy.combo_bonuses.get("command_execution+network", 15)
    return bonus
