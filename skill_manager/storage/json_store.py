from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonStore:
    def read(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as json_file:
            return json.load(json_file)

    def write(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        with temporary_path.open("w", encoding="utf-8") as json_file:
            json.dump(value, json_file, indent=2, sort_keys=True)
        temporary_path.replace(path)

