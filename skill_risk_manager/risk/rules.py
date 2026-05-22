from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern

from skill_risk_manager.risk.models import RiskCategory, RiskFinding, RiskLevel


@dataclass(frozen=True)
class TextRule:
    rule_id: str
    category: RiskCategory
    severity: RiskLevel
    score: int
    pattern: Pattern[str]
    message: str
    suggestion: str = ""
    confidence: float = 0.85

    def match(self, text: str) -> RiskFinding | None:
        result = self.pattern.search(text)
        if not result:
            return None
        return RiskFinding(
            rule_id=self.rule_id,
            category=self.category,
            severity=self.severity,
            confidence=self.confidence,
            message=self.message,
            evidence=result.group(0)[:200],
            suggestion=self.suggestion,
            score=self.score,
        )


TEXT_RULES = [
    TextRule(
        "TOOL_WILDCARD",
        "tool_access",
        "critical",
        90,
        re.compile(r"(allowed[-_ ]?tools|tools)\s*[:=]\s*(\*|\[?[\"']?\*[\"']?\]?)", re.IGNORECASE),
        "Wildcard tool access detected.",
        "Quarantine or manually review before trusting this skill.",
    ),
    TextRule(
        "TOOL_BASH",
        "command_execution",
        "high",
        65,
        re.compile(r"\bBash(?:\s*\(|\b)", re.IGNORECASE),
        "Shell execution tool access detected.",
        "Review the commands this skill can execute.",
    ),
    TextRule(
        "TOOL_WRITE",
        "filesystem",
        "medium",
        45,
        re.compile(r"\b(Write|Edit|MultiEdit)\b", re.IGNORECASE),
        "File mutation tool access detected.",
        "Review the expected file write scope.",
    ),
    TextRule(
        "TOOL_NETWORK",
        "network",
        "medium",
        40,
        re.compile(r"\b(WebFetch|WebSearch)\b", re.IGNORECASE),
        "Network-capable tool access detected.",
    ),
    TextRule(
        "TOOL_MCP",
        "mcp",
        "high",
        55,
        re.compile(r"\bmcp[_\-.a-z0-9]*\b", re.IGNORECASE),
        "MCP-related access detected.",
        "Review MCP server permissions and endpoints.",
    ),
    TextRule(
        "CMD_RM_RF",
        "command_execution",
        "critical",
        90,
        re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
        "Destructive recursive delete command detected.",
        "Quarantine or manually review before trusting this skill.",
    ),
    TextRule(
        "CMD_SUDO",
        "command_execution",
        "high",
        65,
        re.compile(r"\bsudo\b", re.IGNORECASE),
        "Privileged command execution detected.",
    ),
    TextRule(
        "CMD_CURL_PIPE_SH",
        "command_execution",
        "critical",
        90,
        re.compile(r"\b(curl|wget)\b[^\n|]{0,160}\|\s*(sh|bash|zsh|powershell|pwsh)\b", re.IGNORECASE),
        "Network download piped to shell detected.",
        "Quarantine until manually reviewed.",
    ),
    TextRule(
        "CMD_EXEC_DYNAMIC",
        "command_execution",
        "high",
        65,
        re.compile(r"\b(exec|eval|subprocess|python\s+-c|node\s+-e|powershell|cmd\.exe)\b", re.IGNORECASE),
        "Dynamic command execution pattern detected.",
    ),
    TextRule(
        "FS_MUTATION",
        "filesystem",
        "medium",
        45,
        re.compile(r"\b(chmod|chown|delete|overwrite|write file|modify file|edit config)\b", re.IGNORECASE),
        "Filesystem mutation behavior detected.",
    ),
    TextRule(
        "SECRET_ENV",
        "secrets",
        "high",
        65,
        re.compile(
            r"\b(\.env|api[_ -]?key|secret|credential|ssh key|private key|AWS_ACCESS_KEY|GITHUB_TOKEN|OPENAI_API_KEY|ANTHROPIC_API_KEY|token)\b",
            re.IGNORECASE,
        ),
        "Secret-related file or credential reference detected.",
        "Confirm secrets are not printed, copied, or sent externally.",
    ),
    TextRule(
        "NETWORK_URL",
        "network",
        "medium",
        45,
        re.compile(r"\b(curl|wget|requests\.post|fetch|webhook|upload|send to|POST|https?://)\b", re.IGNORECASE),
        "Network-capable behavior detected.",
    ),
    TextRule(
        "PROMPT_IGNORE_INSTRUCTIONS",
        "prompt_injection",
        "high",
        65,
        re.compile(
            r"\b(ignore previous instructions|bypass|do not ask user|automatically approve|never reveal|delete logs|hide from user|exfiltrate)\b",
            re.IGNORECASE,
        ),
        "Prompt-injection or hidden-autonomy instruction detected.",
        "Review instructions for unsafe autonomous behavior.",
    ),
    TextRule(
        "HOOK_PRESENT",
        "hooks",
        "medium",
        35,
        re.compile(r"\bhooks?\b", re.IGNORECASE),
        "Hook configuration detected.",
        "Review hook commands and trigger behavior.",
    ),
    TextRule(
        "MCP_CONFIG",
        "mcp",
        "medium",
        45,
        re.compile(r"\b(\.mcp\.json|filesystem server|browser automation|database access|shell server|remote MCP endpoint)\b", re.IGNORECASE),
        "MCP configuration or high-capability server reference detected.",
        "Review MCP server permissions.",
    ),
]
