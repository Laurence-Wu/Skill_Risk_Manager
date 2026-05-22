<div align="center">

# Skill Risk Manager

**Local-only desktop discovery, risk review, and staged trust management for Claude Code skills.**

<p align="center">
  <img src="assets/futuristic_skill_risk_management_ui.png" alt="Skill Risk Manager hero banner" width="100%">
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-blue">
  <img alt="Platform" src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-violet">
  <img alt="UI" src="https://img.shields.io/badge/UI-CustomTkinter-indigo">
  <img alt="Mode" src="https://img.shields.io/badge/Mode-Local%20Only-brightgreen">
  <img alt="Status" src="https://img.shields.io/badge/Status-Stage%201%20Scanner-orange">
</p>

</div>

---

## What It Does

Skill Risk Manager scans the local machine for Claude Code skills, commands, plugin files, and Claude-related config. It separates trusted records from uncertain findings, attaches risk metadata, and gives the user a review workflow before staged candidates become committed skills.

The runtime scan and review pipeline is local-only. It does not use Wi-Fi, network calls, uploads, telemetry, or remote APIs.

---

## Why The Pipeline Helps

This repo uses a staged pipeline instead of one flat scan:

```text
Discover quickly -> Commit stable records -> Continue deeper -> Stage uncertain findings -> Review before trust
```

| Advantage | Impact |
|---|---|
| Fast useful results | High-confidence records are committed early, before a full-machine crawl finishes. |
| No trust pollution | Uncertain files stay in candidates until explicitly promoted. |
| Risk-first review | Records carry risk score, level, categories, findings, and suggested action. |
| Smooth UI | Worker threads, queues, and lazy table/log updates keep scans from freezing the desktop app. |
| Local-only privacy | Scan artifacts stay under `public/`; the pipeline does not contact the network. |
| Cross-platform behavior | OS-specific path rules live in `platform_manager/` and `config/platforms/`. |
| Configurable depth | Base mode skips protected paths; Advanced mode attempts deeper scans and logs permission failures. |
| Audit-friendly output | Snapshots, staged candidates, summaries, caches, and logs are written to predictable files. |

---

## Workflow

| Stage | Purpose | Output |
|---|---|---|
| Foreground scan | Scan high-confidence Claude locations first. | `public/data/stage1_snapshot.json` |
| Risk scoring | Attach deterministic risk metadata to each record. | `metadata["risk"]` on each record |
| Continuation scan | Continue lower-budget discovery without blocking the UI. | `public/data/stage1_shadow_pool.json` |
| Review | Promote, ignore, inspect, or export records. | Updated GUI state and export files |

The UI uses indigo progress for primary scan activity and amber progress for continuation activity.

---

## Run

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the desktop app:

```powershell
python -m ui.app
```

Run the backend CLI:

```powershell
python -m skill_risk_manager scan --stage1
python -m skill_risk_manager scan --stage1 --shadow
python -m skill_risk_manager list
python -m skill_risk_manager export-report .\report
```

Optional Claude config override:

```powershell
$env:CLAUDE_CONFIG_DIR="C:\path\to\.claude"
python -m skill_risk_manager scan --stage1
```

---

## Security Profiles

| Profile | Behavior |
|---|---|
| Base | Scans accessible files and respects protected hard-ignore paths. |
| Advanced | Attempts protected paths too; permission failures are logged as warnings. |

Base is the safer default. Advanced is for deeper local discovery.

---

## Repository Layout

```text
ui/                    GUI entry point, shell, views, components, UI state
skill_risk_manager/    Backend scanner, CLI, storage, and risk engine
platform_manager/      Windows, macOS, and Linux path adapters
config/                Platform profiles, scan rules, and risk presets
public/                Generated local scan data and logs
tests/                 Unit tests for scanner, risk, platform, storage, and UI controller
```

Only one GUI entry point is reserved: `python -m ui.app`.

---

## Architecture

```text
CustomTkinter UI
  -> ui.core.BackendController
  -> worker thread + event queues
  -> skill_risk_manager.backend.ScanService
  -> Stage1Scanner + ShadowScanner
  -> skill_risk_manager.risk.attach_risk
  -> public/data/*.json and public/logs/*.csv
```

The GUI never mutates Tk widgets from scanner threads. Backend events are converted into UI-safe events and consumed by periodic polling.

---

## Output Files

| File | Purpose |
|---|---|
| `public/data/stage1_snapshot.json` | Stable committed scan results. |
| `public/data/stage1_shadow_pool.json` | Staged continuation candidates. |
| `public/data/stage1_summary.json` | Scan counters and summary state. |
| `public/data/scan_cache.json` | File stat/hash classification cache. |
| `public/logs/stage1_scan_log.csv` | Scan lifecycle events. |
| `public/logs/stage1_error_log.csv` | Permission and filesystem warnings. |

Generated JSON/CSV files under `public/` are ignored by git.

---

## Configuration

| Path | Purpose |
|---|---|
| `config/platforms/` | Windows, macOS, and Linux scan profiles. |
| `config/skill_manager/` | Filename patterns, ignore paths, project markers, and scan paths. |
| `config/risk_manager/presets/` | Base and Advanced risk policy presets. |

Keeping these files outside Python source makes scan behavior easier to audit and tune.

---

## Current Status

Implemented:

- CustomTkinter desktop app with one GUI entry point.
- Stable snapshot and staged candidate separation.
- Foreground scan plus lower-budget continuation scan.
- Risk scoring on confirmed records and candidates.
- Skills, Candidates, Risk, Config, Scan, Logs, and Dashboard views.
- Lazy table/log rendering for smoother UI updates.
- Base and Advanced local scan profiles.
- Windows, macOS, and Linux platform adapters.

---

## Test

Run the full suite:

```powershell
python -B -m unittest discover -v
```

Syntax check:

```powershell
python -B -m compileall -q ui platform_manager skill_risk_manager tests
```

---

## Roadmap

- Richer candidate promotion and review controls.
- Config editing from the GUI.
- Platform diagnostics in the UI.
- Packaged desktop builds for Windows, macOS, and Linux.
- More detailed risk explanations and review history.

