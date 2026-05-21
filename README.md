# Skill Risk Manager

Skill Risk Manager is a local desktop tool for discovering Claude Code skills, reviewing uncertain findings, and keeping stable results separate from staged candidates.

The codebase is split into two top-level areas:

- `skill_manager/`: backend scanner, platform adapters, storage, and CLI logic.
- `manager_GUI/`: CustomTkinter desktop UI with a reusable component system and backend controller bridge.

## Requirements

- Python 3.11+
- Windows, macOS, or Linux
- `customtkinter`

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Run The GUI

From the project root:

```powershell
python -m manager_GUI.app
```

This is the only GUI entry point. The `skill_manager` package stays backend/CLI-only.

## Current Status

The desktop app is connected to the Stage 1 scanner through `manager_GUI.core.BackendController`. It uses a worker thread and a thread-safe event queue so scan activity does not mutate Tk widgets from the scanner thread.

The UI has one user-facing Scan area. Primary scan activity uses the indigo progress bar, and reduced-budget continuation uses the amber progress bar. Stable skills appear only after a snapshot is committed; additional uncertain findings are staged in Candidates.

By default, Start Scan scans the local computer. The Scan and Config screens expose a security level:

- Base: scan accessible files and skip protected hard-ignore paths.
- Advanced: attempt protected paths as well; permission failures are logged as warnings.

Progress, file totals, skill counts, command counts, and candidates are global for the scan run rather than tied to a single folder. The progress bar uses a live estimated total and never moves backward during a scan.

During reduced-budget continuation, candidate and log updates are lazy-loaded and batched so the UI remains responsive while new findings are staged.

## UI Structure

- `manager_GUI/core/`: event model, app state, backend controller, progress math, record mapping, and mock controller for isolated UI tests.
- `manager_GUI/ui/theme.py`: centralized colors, spacing, typography, and component state styles.
- `manager_GUI/ui/components.py`: base cards, buttons, badges, progress cards, and view base class.
- `manager_GUI/ui/tables.py`: lazy tables and log panels.
- `manager_GUI/ui/views/`: Dashboard, Scan, Skills, Candidates, Config, and Logs.
- `manager_GUI/ui/shell.py`: top bar, sidebar, routing, and queue polling.

## Backend CLI

The backend scanner CLI remains available:

```powershell
python -m skill_manager scan --stage1
python -m skill_manager list
python -m skill_manager export-report .\report
```

## Output Files

- `skill_manager/data/stage1_snapshot.json`: committed scan results.
- `skill_manager/data/stage1_shadow_pool.json`: staged continuation results.
- `skill_manager/data/stage1_summary.json`: scan summary.
- `skill_manager/data/scan_cache.json`: file stat/hash classification cache.
- `skill_manager/logs/stage1_scan_log.csv`: scan lifecycle events.
- `skill_manager/logs/stage1_error_log.csv`: permission and filesystem warnings.

## Platform Config

Platform-specific behavior is isolated behind adapters in `skill_manager/platform/`. Rich JSON profiles live in `skill_manager/config/platforms/`.

Override the Claude config root with:

```powershell
$env:CLAUDE_CONFIG_DIR="C:\path\to\.claude"
python -m skill_manager scan --stage1
```

## Tests

```powershell
python -B -m unittest discover -v
```

Optional syntax check:

```powershell
python -B -m compileall -q manager_GUI skill_manager tests
```

## Future Work

- Add richer JSON/CSV repository editing workflows for committed snapshots and staged candidates.
- Wire Config view controls to platform and rule files.
- Add platform adapter status/details to the UI.
- Package the desktop app for local installation.
