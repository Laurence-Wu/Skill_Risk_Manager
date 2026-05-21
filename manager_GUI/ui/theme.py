from __future__ import annotations

import platform

import customtkinter as ctk


DARK_THEME = {
    "app_bg": "#0B1020",
    "shell_bg": "#111827",
    "nav_bg": "#172033",
    "surface": "#1F2937",
    "surface_raised": "#243044",
    "surface_hover": "#2C3A50",
    "surface_selected": "#273449",
    "border": "#3A465B",
    "border_strong": "#4B5A72",
    "text_primary": "#F3F6FA",
    "text_secondary": "#C4CBD7",
    "text_muted": "#8D98AA",
    "text_faint": "#647084",
    "accent_primary": "#6D7DFF",
    "accent_primary_hover": "#7F8DFF",
    "accent_primary_pressed": "#5866D9",
    "accent_focus": "#2DD4BF",
    "progress_primary": "#6D7DFF",
    "progress_continuation": "#F4B860",
    "status_success": "#4ADE80",
    "status_warning": "#F4B860",
    "status_danger": "#F87171",
    "status_info": "#60A5FA",
}

SPACING = {
    "app_padding": 16,
    "section_gap": 14,
    "card_padding": 14,
    "sidebar_width": 230,
    "topbar_height": 56,
    "button_height": 34,
    "table_row_height": 32,
    "radius_card": 10,
    "radius_button": 7,
    "radius_badge": 6,
}

FONTS = {
    "page_title": ("Inter", 22, "bold"),
    "section_title": ("Inter", 15, "bold"),
    "body": ("Inter", 12, "normal"),
    "small": ("Inter", 11, "normal"),
    "caption": ("Inter", 10, "normal"),
    "button": ("Inter", 11, "bold"),
}


class ThemeManager:
    def __init__(self) -> None:
        self.colors = DARK_THEME
        self.spacing_tokens = SPACING
        self.font_tokens = FONTS
        self.font_family = self._font_family()

    def color(self, name: str) -> str:
        return self.colors[name]

    def spacing(self, name: str) -> int:
        return self.spacing_tokens[name]

    def font(self, name: str) -> tuple:
        family, size, weight = self.font_tokens[name]
        return (self.font_family if family == "Inter" else family, size, weight)

    def button_style(self, variant: str = "secondary", state: str = "default") -> dict[str, object]:
        styles: dict[str, dict[str, object]] = {
            "primary": {
                "fg_color": self.color("accent_primary"),
                "hover_color": self.color("accent_primary_hover"),
                "text_color": self.color("text_primary"),
                "border_color": "#9BA5FF",
                "border_width": 1,
            },
            "secondary": {
                "fg_color": self.color("surface_raised"),
                "hover_color": self.color("surface_hover"),
                "text_color": self.color("text_primary"),
                "border_color": self.color("border_strong"),
                "border_width": 1,
            },
            "quiet": {
                "fg_color": "transparent",
                "hover_color": self.color("surface_hover"),
                "text_color": self.color("text_secondary"),
                "border_color": self.color("border"),
                "border_width": 1,
            },
            "danger": {
                "fg_color": self.color("status_danger"),
                "hover_color": "#DC5F5F",
                "text_color": self.color("text_primary"),
                "border_color": "#FCA5A5",
                "border_width": 1,
            },
        }
        style = dict(styles.get(variant, styles["secondary"]))
        if state == "pressed":
            style["fg_color"] = self.color("accent_primary_pressed") if variant == "primary" else self.color("surface_selected")
        elif state == "focus":
            style["border_color"] = self.color("accent_focus")
            style["border_width"] = 1
        elif state == "disabled":
            style["fg_color"] = self.color("surface")
            style["hover_color"] = self.color("surface")
            style["text_color"] = self.color("text_faint")
            style["border_color"] = self.color("border")
        return style

    def badge_style(self, kind: str = "ready") -> dict[str, str]:
        colors = {
            "ready": self.color("status_info"),
            "scanning": self.color("accent_primary"),
            "complete": self.color("status_success"),
            "warning": self.color("status_warning"),
            "error": self.color("status_danger"),
            "staged": self.color("status_warning"),
            "valid": self.color("status_success"),
            "paused": self.color("status_warning"),
            "cancelled": self.color("status_danger"),
        }
        return {"fg_color": colors.get(kind, self.color("status_info")), "text_color": self.color("app_bg")}

    def progress_color(self, mode: str = "primary") -> str:
        if mode == "continuation":
            return self.color("progress_continuation")
        return self.color("progress_primary")

    def apply(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

    def _font_family(self) -> str:
        if platform.system().lower() == "windows":
            return "Segoe UI"
        if platform.system().lower() == "darwin":
            return "Helvetica"
        return "Arial"


THEME = ThemeManager()


def get_theme() -> ThemeManager:
    return THEME
