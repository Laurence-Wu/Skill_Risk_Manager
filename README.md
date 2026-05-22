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
| **Risk-aware review workflow** | Scores discovered records, explains findings, and lets users inspect staged candidates before promotion or rejection. |
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
| **Committed Snapshot** | Stable, trusted scan results. | `public/data/stage1_snapshot.json` |
| **Shadow Candidates** | Uncertain or deferred findings requiring review. | `public/data/stage1_shadow_pool.json` |

---

## UI Preview

The desktop app is organized around six major views:

| View | Purpose |
|---|---|
| **Dashboard** | High-level status, scan summary, and result cards. |
| **Scan** | Foreground and continuation scan progress. |
| **Skills** | Stable committed skill records. |
| **Candidates** | Staged findings awaiting review. |
| **Risk** | Risk score, category, and finding review across skills and candidates. |
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
skill_risk_manager/               ← repo root
│
├── ui/                           ← GUI package and only GUI entry point
│   ├── app.py
│   ├── components.py
│   ├── models.py
│   ├── shell.py
│   ├── table_page.py
│   ├── tables.py
│   ├── theme.py
│   ├── core/
│   │   ├── backend_controller.py
│   │   ├── events.py
│   │   ├── exporters.py
│   │   ├── mock_controller.py
│   │   ├── progress.py
│   │   ├── record_mapping.py
│   │   ├── state.py
│   │   └── table_rows.py
│   └── views/
│       ├── dashboard.py
│       ├── scan.py
│       ├── skills.py
│       ├── candidates.py
│       ├── risk.py
│       ├── config.py
│       └── logs.py
│
├── skill_risk_manager/           ← backend package
│   ├── __main__.py
│   ├── backend/
│   │   ├── cache.py
│   │   ├── classifier.py
│   │   ├── fast_exit.py
│   │   ├── models.py
│   │   ├── parser.py
│   │   ├── priority_queue.py
│   │   ├── scan_service.py
│   │   ├── scanner_utils.py
│   │   ├── shadow_scanner.py
│   │   └── stage1_scanner.py
│   ├── cli/
│   │   └── main.py
│   ├── risk/
│   │   ├── engine.py
│   │   ├── extractors.py
│   │   ├── models.py
│   │   ├── policy.py
│   │   ├── reporter.py
│   │   └── rules.py
│   └── storage/
│       ├── csv_store.py
│       ├── json_store.py
│       └── repository.py
│
├── platform_manager/             ← OS adapters
│   ├── base.py
│   ├── detector.py
│   ├── factory.py
│   ├── linux.py
│   ├── macos.py
│   ├── profile_loader.py
│   └── windows.py
│
├── config/
│   ├── platforms/                ← per-OS scan profiles (JSON)
│   │   ├── windows.json
│   │   ├── macos.json
│   │   └── linux.json
│   ├── skill_manager/            ← skill scan config (CSV + JSON)
│   │   ├── filename_patterns.csv
│   │   ├── ignore_paths.csv
│   │   ├── project_markers.csv
│   │   ├── scan_paths.csv
│   │   └── manifest.json
│   └── risk_manager/             ← risk policy config
│       ├── security_table.json
│       └── presets/
│           ├── base.json
│           └── advanced.json
│
├── public/
│   ├── data/                     ← scan output (generated)
│   └── logs/                     ← scan logs (generated)
│
├── tests/
│   ├── test_manager_gui_controller.py
│   ├── test_parser_classifier.py
│   ├── test_platform.py
│   ├── test_priority_cache_storage.py
│   ├── test_risk_engine.py
│   ├── test_scanner.py
│   └── test_support.py
│
├── requirements.txt
└── README.md
```

---

## Architecture

```text
CustomTkinter UI
      │
      ▼
ui.core.BackendController
      │
      ├── Worker thread
      ├── Thread-safe event queue
      └── UI event conversion
      │
      ▼
skill_risk_manager.backend.ScanService
      │
      ├── Stage1Scanner      → stable foreground snapshot
      └── ShadowScanner      → staged continuation candidates
      │
      ▼
skill_risk_manager.risk.attach_risk
      │
      ├── Extract record metadata and body text
      ├── Apply deterministic risk rules
      └── Store results in SkillRecord.metadata["risk"]
      │
      ▼
Local repository storage
      ├── public/data/*.json
      └── public/logs/*.csv
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
python -m ui.app
```

This is the only GUI entry point. The `ui` package owns the launcher, interface modules, view state, and controller bridge; `skill_risk_manager` owns backend, risk, storage, and CLI code.

---

## Backend CLI

The backend scanner CLI is available directly:

```powershell
# Foreground Stage 1 scan only
python -m skill_risk_manager scan --stage1

# Foreground + shadow continuation scan
python -m skill_risk_manager scan --stage1 --shadow

# List saved Stage 1 records
python -m skill_risk_manager list

# Open the Claude config root folder in Explorer / Finder
python -m skill_risk_manager open-config

# Export snapshot and summary JSON to a directory
python -m skill_risk_manager export-report .\report
```

To override the Claude config root before scanning:

```powershell
$env:CLAUDE_CONFIG_DIR="C:\path\to\.claude"
python -m skill_risk_manager scan --stage1
```

---

## Output Files

| File | Purpose |
|---|---|
| `public/data/stage1_snapshot.json` | Committed foreground scan results. |
| `public/data/stage1_shadow_pool.json` | Staged continuation findings. |
| `public/data/stage1_summary.json` | Scan summary and counters. |
| `public/data/scan_cache.json` | File stat/hash classification cache. |
| `public/logs/stage1_scan_log.csv` | Scan lifecycle events. |
| `public/logs/stage1_error_log.csv` | Permission and filesystem warnings. |

---

## Platform Configuration

Platform-specific behavior is isolated behind adapters in `platform_manager/`. Each adapter (`windows.py`, `macos.py`, `linux.py`) implements path resolution, normalization, hard-ignore enforcement, and folder-opening for its OS.

Rich platform profiles (scan roots, developer root candidates, managed config paths, hard-ignore lists) live in JSON files under:

```text
config/platforms/windows.json
config/platforms/macos.json
config/platforms/linux.json
```

Skill scanner rules (which filenames to match, which paths to ignore, which files signal a project root) are driven by four CSV/JSON files under:

```text
config/skill_manager/filename_patterns.csv
config/skill_manager/ignore_paths.csv
config/skill_manager/project_markers.csv
config/skill_manager/scan_paths.csv
```

Risk policy presets live in:

```text
config/risk_manager/presets/base.json
config/risk_manager/presets/advanced.json
```

This keeps all OS-specific and policy-specific configuration out of the Python source.

---

## Testing

Run the full unit test suite:

```powershell
python -B -m unittest discover -v
```

The `tests/` directory covers:

| Test file | What it covers |
|---|---|
| `test_parser_classifier.py` | Frontmatter parser and skill classifier logic |
| `test_platform.py` | Platform adapter path resolution and hard-ignore behavior |
| `test_priority_cache_storage.py` | Priority queue, classification cache, and storage layer |
| `test_risk_engine.py` | Risk scoring rules and engine output |
| `test_scanner.py` | Stage 1 and shadow scanner pipeline |
| `test_manager_gui_controller.py` | BackendController event queue and UI integration |
| `test_support.py` | Shared test fixtures and helpers |

Optional syntax check across all packages:

```powershell
python -B -m compileall -q ui platform_manager skill_risk_manager tests
```

---

## Current Status

The desktop app is connected to the Stage 1 scanner through `ui.core.BackendController`.

Implemented behavior includes:

- foreground scan execution through a worker thread,
- thread-safe event queue polling,
- stable snapshot loading,
- staged candidate loading,
- deterministic risk scoring on confirmed skills and staged candidates,
- risk columns in Skills and Candidates,
- dedicated Risk page with search, level/category filters, and CSV export,
- shared page header, page toolbar, table, and detail-panel layout,
- dashboard risk summary counters,
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

<div align="center">

**Skill Risk Manager**  
Local discovery, staged review, and safer Claude Code skill management.

</div>
