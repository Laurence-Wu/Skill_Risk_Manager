from __future__ import annotations

import customtkinter as ctk


class ProgressPanel(ctk.CTkFrame):
    def __init__(self, master, title: str = "Progress", **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)
        self.title_label = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=18, weight="bold"))
        self.title_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 8))
        self.progress = ctk.CTkProgressBar(self)
        self.progress.set(0)
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))
        self.labels: dict[str, ctk.CTkLabel] = {}

    def add_metric(self, key: str, label: str, row: int) -> None:
        name_label = ctk.CTkLabel(self, text=label)
        value_label = ctk.CTkLabel(self, text="—", anchor="w")
        name_label.grid(row=row, column=0, sticky="w", padx=14, pady=4)
        value_label.grid(row=row, column=1, sticky="ew", padx=14, pady=4)
        self.labels[key] = value_label

    def update_metric(self, key: str, value: object) -> None:
        if key in self.labels:
            self.labels[key].configure(text=str(value))

    def set_indeterminate(self) -> None:
        self.progress.configure(mode="indeterminate")
        self.progress.start()

    def set_complete(self) -> None:
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(1)

