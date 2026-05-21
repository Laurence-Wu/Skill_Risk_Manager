from __future__ import annotations

import customtkinter as ctk

from skill_manager.backend.models import SkillRecord
from skill_manager.platform.base import PlatformAdapter
from skill_manager.ui.components.skill_table import SkillTable


class SkillsPage(ctk.CTkFrame):
    def __init__(self, master, adapter: PlatformAdapter, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.message = ctk.CTkLabel(self, text="Skills will appear after the fast scan completes.", anchor="w")
        self.message.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
        self.table = SkillTable(self, adapter)
        self.table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def set_records(self, records: list[SkillRecord]) -> None:
        self.message.configure(text=f"Stable saved skills: {len(records)}")
        self.table.set_records(records)

