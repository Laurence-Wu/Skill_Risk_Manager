from __future__ import annotations

from ui.shell import MainWindow
from ui.theme import get_theme


def main() -> None:
    get_theme().apply()
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()

