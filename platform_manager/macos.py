from __future__ import annotations

import subprocess
from pathlib import Path

from .base import PlatformAdapter


class MacOSAdapter(PlatformAdapter):
    name = "macos"

    def open_folder(self, path: Path) -> None:
        target_path = path if path.is_dir() else path.parent
        subprocess.run(["open", str(target_path)], check=False)

