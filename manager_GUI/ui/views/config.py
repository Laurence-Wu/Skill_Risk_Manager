from __future__ import annotations

import customtkinter as ctk

from manager_GUI.core.state import AppState
from manager_GUI.ui.components import BaseButton, BaseCard, BaseView, FilterDropdown, StatusBadge


class ConfigView(BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(3, weight=1)
        self._rendered_security_level = ""
        self.page_header("Config", "Platform rules and scan options for the local environment.")
        self.toolbar = self.page_toolbar(row=1)

        self.platform_card = BaseCard(self, title="Current Platform")
        self.platform_card.grid(row=2, column=0, sticky="ew", padx=self.theme.spacing("app_padding"), pady=(0, 14))
        self.platform_label = ctk.CTkLabel(
            self.platform_card.body,
            text="",
            font=self.theme.font("body"),
            text_color=self.theme.color("text_secondary"),
            anchor="w",
            justify="left",
        )
        self.platform_label.grid(row=0, column=0, sticky="ew")

        split = ctk.CTkFrame(self, fg_color="transparent")
        split.grid(row=3, column=0, sticky="nsew", padx=self.theme.spacing("app_padding"), pady=(0, 16))
        split.grid_columnconfigure(0, weight=1)
        split.grid_columnconfigure(1, weight=1)
        self.files_card = self._files_card(split)
        self.files_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.toggles_card = self._toggles_card(split)
        self.toggles_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    def refresh(self, state: AppState) -> None:
        self._render_toolbar(state.security_level)
        self.platform_label.configure(
            text=f"Platform: {state.platform}\nClaude config root: {state.claude_config_root}"
        )
        protected_enabled = state.security_level == "advanced"
        self.protected_paths_badge.set_status("On" if protected_enabled else "Off", "valid" if protected_enabled else "ready")

    def _render_toolbar(self, selected_level: str) -> None:
        if self._rendered_security_level == selected_level and self.toolbar.left.winfo_children():
            return
        self._rendered_security_level = selected_level
        self.toolbar.clear()
        ctk.CTkLabel(
            self.toolbar.left,
            text="Security",
            font=self.theme.font("small"),
            text_color=self.theme.color("text_secondary"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        FilterDropdown(
            self.toolbar.left,
            ["Base", "Advanced"],
            selected=selected_level.title(),
            command=lambda value: self.actions["set_security_level"](value.lower()),
            width=120,
        ).grid(row=0, column=1, sticky="w")
        BaseButton(self.toolbar.right, "Refresh", self.actions["refresh"], width=92).grid(row=0, column=0, padx=(0, 8))
        BaseButton(self.toolbar.right, "Save Config", self.actions["save_config"], variant="primary", width=116).grid(row=0, column=1)

    def _files_card(self, master) -> BaseCard:
        card = BaseCard(master, title="Rule Files")
        files = [
            "filename_patterns.csv",
            "ignore_paths.csv",
            "scan_paths.csv",
            "project_markers.csv",
            "macos.json",
            "windows.json",
            "linux.json",
        ]
        for row, filename in enumerate(files):
            ctk.CTkLabel(
                card.body,
                text=filename,
                font=self.theme.font("small"),
                text_color=self.theme.color("text_secondary"),
                anchor="w",
            ).grid(row=row, column=0, sticky="ew", pady=3)
        return card

    def _toggles_card(self, master) -> BaseCard:
        card = BaseCard(master, title="Scan Options")
        options = [
            ("Full computer scan", True),
            ("Protected paths", False),
            ("Plugin skills", True),
            ("Legacy commands", True),
            ("Background continuation", True),
            ("Downloads", False),
            ("Prompt history", False),
        ]
        for row, (label, enabled) in enumerate(options):
            ctk.CTkLabel(
                card.body,
                text=label,
                font=self.theme.font("small"),
                text_color=self.theme.color("text_secondary"),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=5)
            badge = StatusBadge(card.body, "On" if enabled else "Off", "valid" if enabled else "ready")
            badge.grid(row=row, column=1, sticky="e", padx=(8, 0))
            if label == "Protected paths":
                self.protected_paths_badge = badge
        card.body.grid_columnconfigure(0, weight=1)
        return card
