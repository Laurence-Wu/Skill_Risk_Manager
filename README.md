# Claude Skill Manager

Stage 1 discovers obvious Claude Code skills and Claude-related files quickly. It creates a stable foreground snapshot after fast exit, then can continue with a low-budget shadow scan that stages additional results separately.

## Requirements

- Python 3.11+
- Windows, macOS, or Linux
- `customtkinter` for the GUI

Install runtime dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Run A Fast Search

From the project root:

```powershell
python -m skill_manager scan --stage1
```

List the saved Stage 1 snapshot:

```powershell
python -m skill_manager list
```

Run foreground scan and shadow scan:

```powershell
python -m skill_manager scan --stage1 --shadow
```

Export the current report files:

```powershell
python -m skill_manager export-report .\report
```

## Run The GUI

```powershell
python -m skill_manager
```

The GUI uses the same backend as the CLI. During foreground scan it shows progress only; stable skills and candidates appear after fast exit.

## Output Files

- `skill_manager/data/stage1_snapshot.json` — stable foreground results saved after fast exit.
- `skill_manager/data/stage1_shadow_pool.json` — staged shadow scan results.
- `skill_manager/data/stage1_summary.json` — foreground and shadow summary.
- `skill_manager/data/scan_cache.json` — file stat/hash classification cache.
- `skill_manager/logs/stage1_scan_log.csv` — scan lifecycle events.
- `skill_manager/logs/stage1_error_log.csv` — permission and filesystem errors.

Permission errors for Windows junction folders such as `My Pictures`, `My Music`, or `My Videos` are expected skips, not scan failures.

## Platform Config

Platform-specific behavior is isolated behind adapters in `skill_manager/platform/`. Rich JSON profiles live in:

- `skill_manager/config/platforms/windows.json`
- `skill_manager/config/platforms/macos.json`
- `skill_manager/config/platforms/linux.json`

The loader supports the richer schema keys such as `personal_scope_paths`, `project_scope_paths`, `plugin_scope_paths`, `managed_scope_paths`, and `developer_root_candidates`, then normalizes them into Stage 1 scan targets.

Override the Claude config root with:

```powershell
$env:CLAUDE_CONFIG_DIR="C:\path\to\.claude"
python -m skill_manager scan --stage1
```

## Tests

```powershell
python -m unittest discover -v
```

Optional syntax check:

```powershell
python -m compileall skill_manager tests
```
