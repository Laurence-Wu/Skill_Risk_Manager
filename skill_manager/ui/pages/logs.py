from __future__ import annotations

import customtkinter as ctk

from skill_manager.ui.components.log_panel import LogPanel


class LogsPage(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.log_panel = LogPanel(self)
        self.log_panel.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)

    def append(self, message: str) -> None:
        self.log_panel.append(message)

