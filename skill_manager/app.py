from __future__ import annotations


def main() -> None:
    try:
        from skill_manager.ui.shell.main_window import MainWindow
    except ModuleNotFoundError as error:
        if error.name == "customtkinter":
            raise SystemExit(
                "CustomTkinter is not installed. Install dependencies with: pip install -r requirements.txt"
            ) from error
        raise

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()

