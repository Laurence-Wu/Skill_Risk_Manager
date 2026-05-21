from __future__ import annotations

import customtkinter as ctk

from skill_manager.ui.components.status_badge import StatusBadge


class TopBar(ctk.CTkFrame):
    def __init__(self, master, platform_name: str, on_settings, **kwargs) -> None:
        super().__init__(master, height=58, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        title = ctk.CTkLabel(self, text="Claude Skill Manager", font=ctk.CTkFont(size=20, weight="bold"))
        title.grid(row=0, column=0, sticky="w", padx=18, pady=12)
        self.os_badge = StatusBadge(self, platform_name)
        self.os_badge.grid(row=0, column=1, sticky="e", padx=8, pady=12)
        self.status_badge = StatusBadge(self, "Idle")
        self.status_badge.grid(row=0, column=2, sticky="e", padx=8, pady=12)
        settings_button = ctk.CTkButton(self, text="Settings", width=100, command=on_settings)
        settings_button.grid(row=0, column=3, sticky="e", padx=(8, 18), pady=12)

    def set_scan_status(self, status: str) -> None:
        self.status_badge.set_status(status)

