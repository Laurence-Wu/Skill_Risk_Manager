from __future__ import annotations

from platform_manager.detector import detect_platform_name
from platform_manager.linux import LinuxAdapter
from platform_manager.macos import MacOSAdapter
from platform_manager.profile_loader import load_platform_profile
from platform_manager.windows import WindowsAdapter


def get_platform_adapter(platform_name: str | None = None):
    detected_name = platform_name or detect_platform_name()
    if detected_name == "macos":
        return MacOSAdapter(load_platform_profile("macos"))
    if detected_name == "windows":
        return WindowsAdapter(load_platform_profile("windows"))
    if detected_name == "linux":
        return LinuxAdapter(load_platform_profile("linux"))
    raise RuntimeError(f"Unsupported platform: {detected_name}")
