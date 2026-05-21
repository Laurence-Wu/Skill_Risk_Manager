from __future__ import annotations

import customtkinter as ctk

from skill_manager.ui.theme.tokens import COLORS


class StatusBadge(ctk.CTkLabel):
    def __init__(self, master, text: str = "Idle", **kwargs) -> None:
        super().__init__(master, text=text, corner_radius=12, padx=10, pady=4, **kwargs)
        self.set_status(text)

    def set_status(self, status: str) -> None:
        normalized_status = status.lower()
        if normalized_status in {"complete", "ready", "idle"}:
            color = COLORS["ok"]
        elif normalized_status in {"running", "paused", "scanning"}:
            color = COLORS["warning"]
        elif normalized_status in {"cancelled", "error", "failed"}:
            color = COLORS["danger"]
        else:
            color = COLORS["muted"]
        self.configure(text=status, fg_color=color)

