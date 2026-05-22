# Skill Configuration and Organization-Wide Scanning

## Part 1 — How Skills Are Configured

### What a Skill Is

A Claude Code skill is a Markdown file named **`SKILL.md`** with a YAML frontmatter block at the top. The frontmatter tells Claude when and how to invoke the skill. To be certain of a file that is a skill, we need to scan for the YAML frontmatter block at the top.




 A minimal skill looks like:

```markdown
---
name: My Skill
description: Does X when the user asks about Y.
---

Detailed instructions here.
```

The scanner (in `skill_risk_manager/backend/parser.py`) reads only the first 8 KB / 100 lines of each file, parses the `---`-delimited YAML block, and confirms a skill is real if it contains both a `name:` field and at least one of `description:` or `summary:`.

### Skill Locations and Their Scopes

Skills can live in three scopes. The platform config (`config/platforms/windows.json` and its macOS/Linux equivalents) defines the exact paths:

| Scope | Canonical path (Windows) | When it applies |
|---|---|---|
| **Personal** | `%USERPROFILE%\.claude\skills\<skill-name>\SKILL.md` | Available to the user in every project |
| **Project** | `<repo>\.claude\skills\<skill-name>\SKILL.md` | Available only inside that repository |
| **Plugin** | `<plugin-root>\skills\<skill-name>\SKILL.md` | Bundled with a plugin; enabled when the plugin is installed |
| **Managed (org-wide)** | `C:\Program Files\ClaudeCode\` (Windows) | Pushed by IT / MDM; applies to every user on the machine |

On macOS the managed path is `/Library/Application Support/ClaudeCode/` and on Linux it is `/etc/claude-code/`.

The environment variable `CLAUDE_CONFIG_DIR` overrides the personal `~/.claude` root for all personal-scope paths. Always resolve this variable first before constructing any scan path (see `platform_manager/base.py:claude_config_root`).

More possible locations are defined in the config folder.

### Optional Frontmatter Fields

Beyond `name` and `description`, you can fine-tune skill behavior with:

- `when_to_use` — extra trigger prose read by the model  
- `allowed-tools` — list of tools the skill may call  
- `user-invocable: false` — hides the skill from the `/`-command menu  
- `disable-model-invocation: true` — slash-only, never auto-triggered  
- `model` / `effort` — override the default model or thinking budget  
- `paths` — path glob(s) that gate the skill to certain file contexts  
- `hooks` — lifecycle hooks that fire around skill execution  

---

## Part 2 — Identifying Skills Across an Organization's Laptops

The scanner in this repo runs in two phases, **foreground** and **shadow**, and uses three config files to decide what to scan, what to skip, and what counts as a confirmed skill.

### Step 1 — Resolve the Config Root

Before scanning, compute each user's `claude_config_root`:

1. Check the environment variable `CLAUDE_CONFIG_DIR`. If set, use it.  
2. Otherwise default to `~/.claude` (`%USERPROFILE%\.claude` on Windows).

This is the anchor for all personal-scope paths.

### Step 2 — Run the Foreground Scan (High-Confidence Paths)

The foreground scan (`scan_paths.csv`, phase = `foreground`) covers deterministic, high-signal paths:

- **Personal skills**: `{claude_config_root}/skills/` — recursed up to depth 4  
- **Installed plugins**: `{claude_config_root}/plugins/` — recursed up to depth 8  
- **Project skills**: `{project_root}/.claude/skills/` — recursed up to depth 5  
- **Managed org config** (read-only): `C:\Program Files\ClaudeCode\` / `/Library/Application Support/ClaudeCode/` / `/etc/claude-code/`  

For each `.md` file found, `skill_risk_manager/backend/parser.py` reads only the frontmatter. `skill_risk_manager/backend/classifier.py` then assigns a `record_type` and `confidence` score:

- Path matches `skills/<name>/SKILL.md` with valid frontmatter → **`personal_skill` or `project_skill`, confidence 0.99**  
- Path matches `skills/<name>/SKILL.md` without valid frontmatter → **`candidate`, confidence 0.58**  
- File inside a `commands/` folder → **`legacy_command`, confidence 0.88**  
- Any `.md` with skill-like frontmatter outside a skills folder → **`candidate`, confidence 0.65**  

### Step 3 — Run the Shadow Scan (Broader Developer Roots)

The shadow scan is a low-budget, cancellable expansion across common developer directories (`scan_paths.csv`, phase = `shadow`). On Windows these include:

```
%USERPROFILE%\source\repos, %USERPROFILE%\source,
%USERPROFILE%\dev, %USERPROFILE%\code, %USERPROFILE%\Desktop, …
```

The scan looks for **project markers** (`project_markers.csv`) — files like `.claude` directories, `CLAUDE.md`, `package.json`, `pyproject.toml`, `Cargo.toml` — and, when found, promotes their parent directory for a closer `.claude/skills/` sub-scan. This catches skills living in repositories that haven't been opened as the active project.

### Step 4 — Apply Hard-Ignore Rules

Before descending into any directory, the scanner checks `ignore_paths.csv`:

- **VCS internals** (`.git`, `.hg`, `.svn`) — always skipped  
- **Build and dependency artifacts** (`node_modules`, `.venv`, `dist`, `build`, `target`, `__pycache__`, etc.)  
- **Credential and key directories** (`.ssh`, `.aws`, `.azure`, `.kube`, `.gnupg`, `.docker`, etc.) — hard-ignored even from metadata reads  
- **OS system roots** (`C:\Windows`, `C:\Program Files`, `/System`, `/proc`, etc.)  
- **Privacy-sensitive files** (`.env`, `secrets.json`, `credentials.json`, transcript `.jsonl` files) — opt-in only  

### Step 5 — Deduplicate and Store Results

`skill_risk_manager/backend/scanner_utils.py:deduplicate_records` collapses duplicates by the tuple `(normalized_path, name.lower(), scope, file_hash)`, keeping the record with the higher confidence score. Results are persisted via `skill_risk_manager/storage/` (JSON or CSV store) and can be queried or exported for an org-wide inventory.
