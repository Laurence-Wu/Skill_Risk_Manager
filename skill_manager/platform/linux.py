from __future__ import annotations

import subprocess
from pathlib import Path

from .base import PlatformAdapter


class LinuxAdapter(PlatformAdapter):
    name = "linux"

    def open_folder(self, path: Path) -> None:
        target_path = path if path.is_dir() else path.parent
        try:
            subprocess.run(["xdg-open", str(target_path)], check=False)
        except FileNotFoundError as error:
            raise RuntimeError("xdg-open is not available on this Linux system") from error

