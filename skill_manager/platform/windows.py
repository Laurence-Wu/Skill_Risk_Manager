from __future__ import annotations

import os
from pathlib import Path

from .base import PlatformAdapter


class WindowsAdapter(PlatformAdapter):
    name = "windows"

    def normalize_path(self, path: Path) -> Path:
        return Path(str(path.expanduser().resolve()).lower())

    def format_path(self, path: Path) -> str:
        resolved_path = path.expanduser().resolve()
        home_path = self.home_dir().expanduser().resolve()
        resolved_text = str(resolved_path)
        home_text = str(home_path)
        if resolved_text.lower().startswith(home_text.lower()):
            suffix = resolved_text[len(home_text) :].lstrip("\\/")
            return "~" if not suffix else "~\\" + suffix.replace("/", "\\")
        return resolved_text.replace("/", "\\")

    def open_folder(self, path: Path) -> None:
        target_path = path if path.is_dir() else path.parent
        os.startfile(str(target_path))  # type: ignore[attr-defined]

