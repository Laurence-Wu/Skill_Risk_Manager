# Skill Configuration and Scanning

## Part 1 — How Skills Are Configured

### What a Skill Is

A Claude Code skill is usually a Markdown file named `SKILL.md`. The file starts with a YAML frontmatter block that tells Claude what the skill is and when it should be used.

A minimal skill looks like this:

```markdown
---
name: My Skill
description: Use this when the user asks about X.
---

Skill instructions go here.
```

The scanner treats a file as a confirmed skill only when:

- the file is named `SKILL.md`,
- it lives under a `skills/<skill-name>/` folder,
- its frontmatter starts and ends with `---`,
- it has a `name`, and
- it has either a `description` or a `summary`.

The parser reads only the first 8 KB or first 100 lines of a Markdown file. That is enough to inspect frontmatter without loading large files into memory.

### Where Skills Can Live

Skills can be personal, project-local, plugin-provided, or managed by an organization.

| Scope | Example path | Meaning |
|---|---|---|
| Personal | `%USERPROFILE%\.claude\skills\<skill>\SKILL.md` | Available to the user across projects. |
| Project | `<repo>\.claude\skills\<skill>\SKILL.md` | Available only inside that repository. |
| Plugin | `<plugin-root>\skills\<skill>\SKILL.md` | Bundled with an installed plugin. |
| Managed | `C:\Program Files\ClaudeCode\` | Pushed by IT or policy tooling. |

On macOS, the managed location is `/Library/Application Support/ClaudeCode/`. On Linux, it is `/etc/claude-code/`.

The `CLAUDE_CONFIG_DIR` environment variable overrides the normal `~/.claude` root. The platform adapter resolves that value before building scan paths.

### Useful Frontmatter Fields

Beyond `name` and `description`, a skill can include:

- `when_to_use` for extra trigger guidance,
- `allowed-tools` for tool access,
- `user-invocable: false` to hide it from the slash-command menu,
- `disable-model-invocation: true` for slash-only behavior,
- `model` or `effort` for model and reasoning settings,
- `paths` for file-context gating,
- `hooks` for lifecycle behavior.

The scanner keeps these fields in record metadata so the risk engine and GUI can show useful review details.

---

## Part 2 — Scanner Algorithm

The scanner is implemented as a local, two-stage pipeline:

```text
build targets -> foreground scan -> classify -> attach risk -> commit snapshot
              -> continuation scan -> stage candidates -> save shadow pool
```

It does not call remote services. It reads local files, emits local events, and writes local JSON/CSV output.

### 1. Build Scan Targets

`platform_manager/base.py` builds `ScanTarget` objects from the active platform profile.

Each target has:

- a path,
- a priority,
- a source type,
- a max recursion depth,
- a scan mode,
- a human-readable reason.

High-priority targets include personal skills, project skills, project plugin folders, installed plugin folders, command folders, Claude config files, and parent project `.claude` folders. Lower-priority targets are saved for continuation scanning.

For full-computer scans, `ScanService.build_computer_scan_targets()` also adds local root paths:

- Windows: available drive roots such as `C:\`, `D:\`,
- macOS/Linux: `/`, plus `/Volumes/*` on macOS.

Base mode respects hard-ignore paths. Advanced mode attempts protected paths too and logs permission failures.

### 2. Run the Foreground Scanner

`Stage1Scanner.run_foreground()` uses a priority queue, so high-confidence locations are scanned first.

The foreground scanner:

1. loads the classification cache,
2. pops the highest-priority target,
3. skips generated folders, symlinks, and hard-ignored paths,
4. walks directories with an explicit stack and a max depth,
5. scans high-value files immediately,
6. defers low-confidence `.md` and `.json` files to continuation,
7. classifies each scanned file,
8. attaches risk metadata,
9. emits progress events for the GUI,
10. deduplicates records,
11. saves the stable snapshot.

High-value files include:

- `SKILL.md`,
- `CLAUDE.md`,
- `CLAUDE.local.md`,
- `settings.json`,
- `settings.local.json`,
- `.mcp.json`,
- `.claude.json`.

High-value folders include `.claude`, `skills`, `plugins`, `commands`, and `agents`.

### 3. Reuse Cache When Possible

Before parsing a file, the scanner checks `public/data/scan_cache.json`.

If size and modified time still match, the scanner reuses the previous classification. If the file is high-value, it may also compare a content hash. Cached records are still re-scored for risk, so updated risk rules can take effect without forcing a full reparse.

### 4. Classify Files

`classifier.py` assigns a record type and confidence score.

| Condition | Record type | Confidence |
|---|---:|---:|
| Valid `skills/<name>/SKILL.md` | `personal_skill`, `project_skill`, or `plugin_skill` | `0.99` |
| `SKILL.md` path without required frontmatter | `candidate` | `0.58` |
| `SKILL.md` outside the normal skill folder | `candidate` | `0.72` to `0.78` |
| `CLAUDE.md` or `CLAUDE.local.md` | `claude_memory` | `0.95` |
| Claude settings or MCP config | `claude_config` | `0.95` |
| Markdown inside `commands/` | `legacy_command` | `0.88` |
| Markdown with skill-like frontmatter elsewhere | `candidate` | `0.65` |
| Markdown in prompt-like folders | `candidate` | `0.45` |

Ignored files are not saved as records.

### 5. Attach Risk

After classification, `skill_risk_manager.risk.attach_risk()` adds a risk profile to:

```python
record.metadata["risk"]
```

The profile includes score, level, categories, findings, and a summary. High-risk candidates are marked as `needs_review`.

### 6. Decide When the Foreground Scan Can Stop

The foreground scan uses `FastExitTracker`.

It waits until required source groups have been attempted, then checks:

- minimum checked file count,
- minimum elapsed time,
- recent discovery rate,
- overall discovery rate.

If recent discoveries drop below the configured ratio, the scanner commits the stable snapshot and leaves remaining targets for continuation.

### 7. Save the Stable Snapshot

Before saving, records are deduplicated by:

```text
normalized path + lowercase name + scope + file hash
```

The scanner keeps the higher-confidence record when duplicates collide.

Foreground output is written to:

- `public/data/stage1_snapshot.json`,
- `public/data/stage1_summary.json`,
- `public/data/scan_cache.json`,
- `public/logs/stage1_scan_log.csv`,
- `public/logs/stage1_error_log.csv`.

### 8. Run the Continuation Scanner

`ShadowScanner.run()` scans the deferred and lower-priority targets.

It is cancellable, pausable, and budgeted by:

- max runtime,
- max candidates,
- batch size,
- short sleeps between batches.

The continuation scanner stages findings into `public/data/stage1_shadow_pool.json`. It does not mutate the committed snapshot.

Shadow results are also classified, risk-scored, deduplicated, and saved in batches so the GUI stays smooth during long scans.

### 9. UI Event Flow

The backend never updates Tkinter widgets directly. It emits scan events into a queue. `ui.core.BackendController` converts those backend events into UI-safe events, updates global state, and lets the active view refresh on a timer.

That is why scans can run in the background while the GUI remains responsive.
