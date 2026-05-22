from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


PRESET_DIR = Path(__file__).resolve().parent / "presets"


@dataclass(frozen=True)
class RiskPolicy:
    enable_body_scan: bool = True
    enable_frontmatter_scan: bool = True
    enable_config_scan: bool = True
    enable_mcp_deep_scan: bool = False
    enable_prompt_injection_scan: bool = True
    max_file_chars: int = 80_000
    critical_threshold: int = 75
    high_threshold: int = 45
    medium_threshold: int = 20
    combo_bonuses: dict[str, int] = field(
        default_factory=lambda: {
            "secrets+network": 20,
            "command_execution+filesystem": 15,
            "command_execution+network": 15,
        }
    )


def load_policy(name: str = "base") -> RiskPolicy:
    preset_path = PRESET_DIR / f"{name}.json"
    if not preset_path.exists():
        return RiskPolicy()
    with preset_path.open("r", encoding="utf-8") as preset_file:
        raw_policy = json.load(preset_file)
    return RiskPolicy(
        enable_body_scan=bool(raw_policy.get("enable_body_scan", True)),
        enable_frontmatter_scan=bool(raw_policy.get("enable_frontmatter_scan", True)),
        enable_config_scan=bool(raw_policy.get("enable_config_scan", True)),
        enable_mcp_deep_scan=bool(raw_policy.get("enable_mcp_deep_scan", False)),
        enable_prompt_injection_scan=bool(raw_policy.get("enable_prompt_injection_scan", True)),
        max_file_chars=int(raw_policy.get("max_file_chars", 80_000)),
        critical_threshold=int(raw_policy.get("critical_threshold", 75)),
        high_threshold=int(raw_policy.get("high_threshold", 45)),
        medium_threshold=int(raw_policy.get("medium_threshold", 20)),
        combo_bonuses=dict(raw_policy.get("combo_bonuses", RiskPolicy().combo_bonuses)),
    )


def preset_for_security_level(security_level: str) -> str:
    return "advanced" if security_level == "advanced" else "base"
