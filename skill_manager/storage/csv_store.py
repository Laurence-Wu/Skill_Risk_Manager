from __future__ import annotations

import csv
from pathlib import Path


class CsvStore:
    def append_row(self, path: Path, fieldnames: list[str], row: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not path.exists()
        with path.open("a", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(row)

