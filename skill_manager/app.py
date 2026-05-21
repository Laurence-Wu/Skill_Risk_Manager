from __future__ import annotations


def main() -> None:
    try:
        from manager_GUI.app import main as run_gui
    except ModuleNotFoundError as error:
        if error.name == "customtkinter":
            raise SystemExit(
                "CustomTkinter is not installed. Install dependencies with: pip install -r requirements.txt"
            ) from error
        raise

    run_gui()


if __name__ == "__main__":
    main()
