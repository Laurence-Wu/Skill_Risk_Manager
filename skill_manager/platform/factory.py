from __future__ import annotations

from skill_manager.platform.detector import detect_platform_name
from skill_manager.platform.linux import LinuxAdapter
from skill_manager.platform.macos import MacOSAdapter
from skill_manager.platform.profile_loader import load_platform_profile
from skill_manager.platform.windows import WindowsAdapter


def get_platform_adapter(platform_name: str | None = None):
    detected_name = platform_name or detect_platform_name()
    if detected_name == "macos":
        return MacOSAdapter(load_platform_profile("macos"))
    if detected_name == "windows":
        return WindowsAdapter(load_platform_profile("windows"))
    if detected_name == "linux":
        return LinuxAdapter(load_platform_profile("linux"))
    raise RuntimeError(f"Unsupported platform: {detected_name}")

