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

The `CLAUDE_CONFIG_DIR` environment variable overrides the normal `~/.claude` root. The platform adapter resolves that value before building scan paths. For more comprehensive path list, find that under configura

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

`Stage1Scanner.run_foreground()` is the main discovery algorithm. Its job is to find the most trustworthy records first, save a stable snapshot, and leave noisy work for the continuation scanner.

The foreground scanner uses these strategies:

| Strategy | How it works |
|---|---|
| Priority-first scanning | Targets are pushed into `ScanPriorityQueue`; higher-priority paths are scanned before lower-priority paths. Ties keep insertion order. |
| Required source coverage | The scanner tracks required source groups: personal, project, parent project, plugin, and command. It does not early-exit until those groups have been attempted. |
| Safe skipping | Generated folders, test temp folders, symlinks, and hard-ignored platform paths are skipped before traversal. |
| Stack traversal | Directories are walked with an explicit stack instead of recursion, so depth limits are easy to enforce. |
| High-signal first | Entries named `.claude`, `skills`, `plugins`, `commands`, and `agents` are sorted ahead of ordinary folders. |
| Immediate file scan | High-value files are parsed during foreground discovery because they are likely to contain real Claude records. |
| Deferred noise | Low-confidence `.md` and `.json` files are not parsed immediately. They are converted into continuation targets. |
| Cache reuse | If file stat or hash data still matches, the previous classification is reused and risk is re-scored. |
| Progress events | Each target and scanned file emits progress data for the GUI: current path, counts, potential records, and errors. |
| Fast exit | Once required groups are covered, the scanner exits when recent discoveries drop below the configured discovery-rate threshold. |
| Stable commit | Records are deduplicated, sorted by confidence, saved to the snapshot, and only then shown as committed results. |

At a high level, the foreground loop is:

```text
load cache
build priority queue
while targets remain:
    stop if cancelled
    pop highest-priority target
    move low-priority targets to continuation
    scan files or directories under that target
    stop early if required groups are covered and discovery rate drops
dedupe records
save snapshot, summary, cache, and scan log
emit "results ready"
```

High-value files are scanned immediately:

- `SKILL.md`,
- `CLAUDE.md`,
- `CLAUDE.local.md`,
- `settings.json`,
- `settings.local.json`,
- `.mcp.json`,
- `.claude.json`.

High-value folders are visited first: `.claude`, `skills`, `plugins`, `commands`, and `agents`.

There are two directory modes:

- `skill_inventory` targets only look for `SKILL.md` files under skill/plugin trees.
- Normal foreground targets scan config files, command Markdown, metadata Markdown in high-value folders, and defer lower-signal candidates.

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
