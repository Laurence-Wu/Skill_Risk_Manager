<div align="center">

# Skill Risk Manager

**A local desktop control plane for discovering Claude Code skills, reviewing risk, and separating trusted skills from staged candidates.**

<p align="center">
  <img src="assets/futuristic_skill_risk_management_ui.png" alt="Skill Risk Manager hero banner" width="100%">
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-blue">
  <img alt="Platform" src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-violet">
  <img alt="UI" src="https://img.shields.io/badge/UI-CustomTkinter-indigo">
  <img alt="Mode" src="https://img.shields.io/badge/Mode-Local%20First-brightgreen">
  <img alt="Status" src="https://img.shields.io/badge/Status-Stage%201%20Scanner-orange">
</p>

</div>

---

## Overview

**Skill Risk Manager** is a local desktop application for discovering, reviewing, and managing Claude Code skills on a user’s machine. It scans Claude-related configuration, detects skill-like files, separates stable results from uncertain candidates, and gives the user a review workflow before staged findings become trusted skills.

The project is built around a two-phase discovery model:

1. **Fast foreground discovery** creates a stable committed snapshot.
2. **Reduced-budget shadow scanning** continues in the background and stages uncertain findings as candidates.

This design keeps high-confidence results available quickly while preserving a review path for deeper, lower-confidence discovery.

---

## Why This Exists

Claude Code skills can live across global config folders, project-local directories, command folders, plugin folders, and ad-hoc experiments. Over time, it becomes hard to answer:

- Which skills are actually present on this machine?
- Which ones are stable enough to trust?
- Which ones are uncertain, stale, incomplete, or risky?
- Which files should be reviewed before being used by Claude Code?

**Skill Risk Manager** adds a local review layer between raw file discovery and trusted skill usage.

---

## Key Capabilities

| Capability | Description |
|---|---|
| **Local skill discovery** | Scans Claude-related paths, skill directories, command files, config files, and project-level skill artifacts. |
| **Stable snapshot management** | Writes high-confidence foreground results into a committed Stage 1 snapshot. |
| **Candidate staging** | Sends lower-confidence findings into a shadow candidate pool instead of treating them as trusted immediately. |
| **Risk-aware review workflow** | Lets users inspect staged candidates before promotion or rejection. |
| **Responsive desktop UI** | Uses a worker thread and event queue so scans do not freeze the CustomTkinter interface. |
| **Cross-platform scanning** | Uses platform adapters for Windows, macOS, and Linux scan behavior. |
| **Local-first privacy model** | Runs on the local machine and stores scan artifacts locally. |

---

## Core Workflow

```text
Local machine
    │
    ▼
Foreground Stage 1 scan
    │
    ├── High-confidence findings ──► Committed snapshot
    │
    ▼
Reduced-budget shadow scan
    │
    ▼
Staged candidates
    │
    ▼
Review / promote / ignore
```

The important separation is:

| Result Type | Meaning | Storage |
|---|---|---|
| **Committed Snapshot** | Stable, trusted scan results. | `skill_manager/data/stage1_snapshot.json` |
| **Shadow Candidates** | Uncertain or deferred findings requiring review. | `skill_manager/data/stage1_shadow_pool.json` |

---

## UI Preview

The desktop app is organized around six major views:

| View | Purpose |
|---|---|
| **Dashboard** | High-level status, scan summary, and result cards. |
| **Scan** | Foreground and continuation scan progress. |
| **Skills** | Stable committed skill records. |
| **Candidates** | Staged findings awaiting review. |
| **Config** | Scan scope, security level, and platform settings. |
| **Logs** | Scan lifecycle events, warnings, and filesystem errors. |

The scan screen uses two progress tracks:

- **Indigo progress bar** — primary foreground scan.
- **Amber progress bar** — reduced-budget continuation scan.

---

## Security Profiles

Skill Risk Manager exposes two scanning profiles:

| Profile | Behavior |
|---|---|
| **Base** | Scans accessible files and skips protected hard-ignore paths. Recommended default. |
| **Advanced** | Attempts protected paths as well. Permission failures are logged as warnings. |

Use **Base** for normal scans. Use **Advanced** when you want deeper discovery and are comfortable with more filesystem warnings.

---

## Project Structure

```text
Skill_Risk_Manager/
├── manager_GUI/
│   ├── app.py
│   ├── core/
│   │   ├── backend_controller.py
│   │   ├── events.py
│   │   ├── progress.py
│   │   ├── record_mapping.py
│   │   └── state.py
│   └── ui/
│       ├── components.py
│       ├── shell.py
│       ├── tables.py
│       ├── theme.py
│       └── views/
│           ├── dashboard.py
│           ├── scan.py
│           ├── skills.py
│           ├── candidates.py
│           ├── config.py
│           └── logs.py
│
├── skill_manager/
│   ├── backend/
│   │   ├── scan_service.py
│   │   ├── stage1_scanner.py
│   │   ├── shadow_scanner.py
│   │   ├── classifier.py
│   │   ├── parser.py
│   │   └── cache.py
│   ├── config/
│   │   └── platforms/
│   ├── data/
│   ├── logs/
│   ├── platform/
│   └── storage/
│
├── tests/
├── requirements.txt
└── README.md
```

---

## Architecture

```text
CustomTkinter UI
      │
      ▼
manager_GUI.core.BackendController
      │
      ├── Worker thread
      ├── Thread-safe event queue
      └── UI event conversion
      │
      ▼
skill_manager.backend.ScanService
      │
      ├── Stage1Scanner      → stable foreground snapshot
      └── ShadowScanner      → staged continuation candidates
      │
      ▼
Local repository storage
      ├── data/*.json
      └── logs/*.csv
```

The GUI does not directly mutate Tk widgets from scanner threads. Backend scan events are converted into UI-safe events and consumed by the visible view during periodic polling.

---

## Requirements

- Python **3.11+**
- Windows, macOS, or Linux
- `customtkinter`

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

---

## Run the Desktop App

From the project root:

```powershell
python -m manager_GUI.app
```

This is the only GUI entry point. The `skill_manager` package remains backend/CLI-only.

---

## Backend CLI

The backend scanner CLI is still available:

```powershell
python -m skill_manager scan --stage1
python -m skill_manager list
python -m skill_manager export-report .\report
```

To override the Claude config root:

```powershell
$env:CLAUDE_CONFIG_DIR="C:\path\to\.claude"
python -m skill_manager scan --stage1
```

---

## Output Files

| File | Purpose |
|---|---|
| `skill_manager/data/stage1_snapshot.json` | Committed foreground scan results. |
| `skill_manager/data/stage1_shadow_pool.json` | Staged continuation findings. |
| `skill_manager/data/stage1_summary.json` | Scan summary and counters. |
| `skill_manager/data/scan_cache.json` | File stat/hash classification cache. |
| `skill_manager/logs/stage1_scan_log.csv` | Scan lifecycle events. |
| `skill_manager/logs/stage1_error_log.csv` | Permission and filesystem warnings. |

---

## Platform Configuration

Platform-specific behavior is isolated behind adapters in:

```text
skill_manager/platform/
```

Rich platform profiles live in:

```text
skill_manager/config/platforms/
```

This keeps OS-specific scan roots, path formatting, hard-ignore behavior, and folder-opening behavior separated from the scanner and UI layers.

---

## Testing

Run the unit test suite:

```powershell
python -B -m unittest discover -v
```

Optional syntax check:

```powershell
python -B -m compileall -q manager_GUI skill_manager tests
```

---

## Current Status

The desktop app is connected to the Stage 1 scanner through `manager_GUI.core.BackendController`.

Implemented behavior includes:

- foreground scan execution through a worker thread,
- thread-safe event queue polling,
- stable snapshot loading,
- staged candidate loading,
- scan progress aggregation,
- foreground-to-continuation transition,
- candidate staging during shadow scanning,
- log export,
- security-level selection,
- and platform-aware scan roots.

---

## Roadmap

- [ ] Add richer JSON/CSV editing workflows for committed snapshots.
- [ ] Add richer candidate review and promotion controls.
- [ ] Wire Config view controls directly into platform and rule files.
- [ ] Add platform adapter diagnostics to the UI.
- [ ] Add packaged desktop builds for Windows, macOS, and Linux.
- [ ] Add richer risk scoring and explanation fields for candidate review.
- [ ] Add import/export workflows for sharing skill inventories across machines.

---

## Design Principles

- **Local first** — scan and store data on the user’s machine.
- **Stable before exhaustive** — produce trusted results quickly, then continue deeper discovery.
- **Review before trust** — uncertain findings remain staged until explicitly promoted.
- **Platform aware** — isolate OS-specific behavior behind adapters.
- **UI-safe scanning** — keep long-running scan work off the Tkinter UI thread.

---

## License

Add your project license here.

---

<div align="center">

**Skill Risk Manager**  
Local discovery, staged review, and safer Claude Code skill management.

</div>
