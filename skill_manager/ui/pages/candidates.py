from __future__ import annotations

import customtkinter as ctk

from skill_manager.backend.models import SkillRecord
from skill_manager.platform.base import PlatformAdapter
from skill_manager.ui.components.skill_table import SkillTable


class CandidatesPage(ctk.CTkFrame):
    def __init__(self, master, adapter: PlatformAdapter, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        self.fast_tab = self.tabs.add("Fast Scan Candidates")
        self.shadow_tab = self.tabs.add("Shadow Scan Candidates")
        self.ignored_tab = self.tabs.add("Ignored")
        for tab in [self.fast_tab, self.shadow_tab, self.ignored_tab]:
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)
        self.fast_table = SkillTable(self.fast_tab, adapter)
        self.fast_table.grid(row=0, column=0, sticky="nsew")
        self.shadow_table = SkillTable(self.shadow_tab, adapter)
        self.shadow_table.grid(row=0, column=0, sticky="nsew")
        self.ignored_label = ctk.CTkLabel(self.ignored_tab, text="Ignored records are not surfaced in Stage 1.")
        self.ignored_label.grid(row=0, column=0, sticky="nw", padx=12, pady=12)

    def set_fast_candidates(self, records: list[SkillRecord]) -> None:
        self.fast_table.set_records(records)

    def set_shadow_candidates(self, records: list[SkillRecord]) -> None:
        self.shadow_table.set_records(records)

