from __future__ import annotations

import customtkinter as ctk

from skill_manager.platform.base import PlatformAdapter


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, adapter: PlatformAdapter, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        title = ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))
        info = (
            f"Platform: {adapter.name}\n"
            f"Claude config root: {adapter.format_path(adapter.claude_config_root())}\n"
            f"Default window size: {adapter.default_window_size()[0]} × {adapter.default_window_size()[1]}\n"
            "Stage 1 broad Downloads/Desktop/Documents shadow scanning is disabled by default."
        )
        ctk.CTkLabel(self, text=info, justify="left", anchor="w").grid(row=1, column=0, sticky="ew", padx=18, pady=8)

