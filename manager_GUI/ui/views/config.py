from __future__ import annotations

import customtkinter as ctk

from manager_GUI.core.state import AppState
from manager_GUI.ui.components import BaseButton, BaseCard, BaseView, StatusBadge


class ConfigView(BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(4, weight=1)
        self.page_header("Config", "Platform rules and scan options for the local environment.")
        self._rendered_security_level = ""
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

        self.security_card = BaseCard(self, title="Security Level")
        self.security_card.grid(row=3, column=0, sticky="ew", padx=self.theme.spacing("app_padding"), pady=(0, 14))

        split = ctk.CTkFrame(self, fg_color="transparent")
        split.grid(row=4, column=0, sticky="nsew", padx=self.theme.spacing("app_padding"), pady=(0, 16))
        split.grid_columnconfigure(0, weight=1)
        split.grid_columnconfigure(1, weight=1)
        self.files_card = self._files_card(split)
        self.files_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.toggles_card = self._toggles_card(split)
        self.toggles_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    def refresh(self, state: AppState) -> None:
        self.platform_label.configure(
            text=f"Platform: {state.platform}\nClaude config root: {state.claude_config_root}"
        )
        self._render_security_card(state.security_level)
        protected_enabled = state.security_level == "advanced"
        self.protected_paths_badge.set_status("On" if protected_enabled else "Off", "valid" if protected_enabled else "ready")

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
            badge.grid(
                row=row,
                column=1,
                sticky="e",
                padx=(8, 0),
            )
            if label == "Protected paths":
                self.protected_paths_badge = badge
        card.body.grid_columnconfigure(0, weight=1)
        return card

    def _render_security_card(self, selected_level: str) -> None:
        if self._rendered_security_level == selected_level and self.security_card.body.winfo_children():
            return
        self._rendered_security_level = selected_level
        for child in self.security_card.body.winfo_children():
            child.destroy()
        BaseButton(
            self.security_card.body,
            "Base",
            lambda: self.actions["set_security_level"]("base"),
            variant="primary" if selected_level == "base" else "secondary",
            width=86,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        BaseButton(
            self.security_card.body,
            "Advanced",
            lambda: self.actions["set_security_level"]("advanced"),
            variant="primary" if selected_level == "advanced" else "secondary",
            width=104,
        ).grid(row=0, column=1, sticky="w", padx=(0, 12))
        ctk.CTkLabel(
            self.security_card.body,
            text="Base skips protected paths. Advanced attempts files that may require permission.",
            font=self.theme.font("small"),
            text_color=self.theme.color("text_muted"),
            anchor="w",
        ).grid(row=0, column=2, sticky="w")
