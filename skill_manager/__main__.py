from __future__ import annotations

import sys

from .app import main as run_gui
from .cli.main import main as run_cli


def main() -> None:
    if len(sys.argv) > 1:
        run_cli()
        return
    run_gui()


if __name__ == "__main__":
    main()
