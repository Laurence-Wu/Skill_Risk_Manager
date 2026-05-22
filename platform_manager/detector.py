from __future__ import annotations

import platform


def detect_platform_name() -> str:
    system_name = platform.system().lower()
    if system_name == "darwin":
        return "macos"
    if system_name == "windows":
        return "windows"
    if system_name == "linux":
        return "linux"
    return "unknown"

