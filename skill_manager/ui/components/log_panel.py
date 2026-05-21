from __future__ import annotations

import customtkinter as ctk


class LogPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.textbox = ctk.CTkTextbox(self, wrap="word")
        self.textbox.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

    def append(self, message: str) -> None:
        self.textbox.insert("end", message + "\n")
        self.textbox.see("end")

