---
title: "nancyr Init/Orient Entry Point Design"
type: design
tags: [nancyr, cli, ux, entry-point, workspace-discovery]
summary: "Design for the nancy bare command — workspace orientation, subcommand structure, config cascade, and .nancy/ directory layout"
status: active
project: nancyr
confidence: high
related: [nancyr-architecture, nancyr-domain-model]
---

# nancyr Init/Orient Entry Point

## Problem

When a developer types `nancy` with no arguments, the CLI errors because a prompt is required. This is wrong. The bare `nancy` command should be the primary experience: orient, assess the workspace, show what's in flight, and offer intelligent next steps.

## Decision

Transform the flat CLI (`nancy PROMPT [FLAGS]`) into a subcommand-based architecture where the bare `nancy` command is a first-class citizen.

## CLI Surface

```
nancy                        # Orient — assess workspace, show status
nancy "fix the bug"          # Sugar for `nancy run "fix the bug"`
nancy run "fix the bug"      # Explicit task execution (with --limit, --warn, etc.)
nancy init                   # Initialize .nancy/ in current project
nancy status                 # Detailed status
nancy history [-n 10]        # Session history
```

## .nancy/ Directory Structure

### Global

```
~/.nancy/
  config.toml                # Global defaults (token_limit, warn_threshold, deny_threshold, claude_binary)
```

### Project-Local (git-ignored)

```
<project>/.nancy/
  config.toml                # Project overrides (all fields optional)
  sessions/                  # Session journals (already exists)
  reports/                   # MDX reports (already exists)
  tasks/                     # Task state (future)
```

## Config Cascade

Three layers, each overriding the previous:

1. **Global defaults** — `~/.nancy/config.toml` (or hardcoded defaults if missing)
2. **Project overrides** — `<project>/.nancy/config.toml` (optional fields only)
3. **CLI flags** — `--limit`, `--warn`, `--deny`, `--claude`

Default values:

- `token_limit`: 200,000
- `warn_threshold`: 70.0
- `deny_threshold`: 95.0
- `claude_binary`: "claude"

## Workspace Discovery Algorithm

When nancy starts, `Workspace::discover(pwd)` runs:

1. **Find project root**: Check `$NANCY_HOME` env var → walk up from PWD looking for `.nancy/` (like git finds `.git/`) → fall through to None
2. **Load global config**: Read `~/.nancy/config.toml`, defaults if missing/malformed
3. **Load project config**: If project root found, read `.nancy/config.toml`
4. **Detect git**: `git rev-parse --show-toplevel`, `git rev-parse --abbrev-ref HEAD`, `git status --porcelain`, `git rev-list` for ahead/behind. All non-fatal.
5. **Load recent sessions**: If project root found, `Journal::new(root).recent(5)`

## Orient Output (bare `nancy`)

### Known project with history

```
nancy v0.1.0

  Project: nancyr
  Root:    /Users/alphab/Dev/LLM/DEV/helioy/nancyr
  Branch:  main (clean)

Recent sessions:
  [+] 2026-02-21T14:30:00 "fix the auth bug"             $0.23
  [+] 2026-02-21T09:15:00 "add input validation"          $0.45
  [x] 2026-02-20T16:00:00 "refactor database layer"       $1.20

Usage:
  nancy "<prompt>"    Run a task
  nancy status        Show detailed status
  nancy history       Show session history
```

### Unknown directory — guided init (first-time user)

```
nancy v0.1.0

  Directory: /tmp/scratch
  Git:       not a repo

  This is a new workspace. Let me get you set up.

  Project name: _
```

Nancy walks you through: name → confirm directory → create `.nancy/` → done. Ready to go in 10 seconds.

### Unknown directory — guided init (returning user, ~/.nancy/config.toml exists)

```
nancy v0.1.0

  Directory: /tmp/scratch
  Git:       not a repo

  Welcome back. Initialize this directory as a nancy project?

  Project name: _
```

Recognizes returning user (global config exists), skips first-time fluff.

### Unknown directory — inside a git repo

```
nancy v0.1.0

  Directory: /Users/alphab/Dev/cool-project
  Git:       main (clean)

  This looks like an existing project. Initialize nancy here?

  Project name (cool-project): _
```

Infers project name from directory name, offers it as default. One enter and you're in.

### Design Principle

**Nancy never shows you a wall. She always shows you a door.** No dead-end messages like "not a project." Every state flows into a helpful next step. Orient detects the situation and guides into init when needed — the explicit `nancy init` subcommand still exists but the orient path handles it gracefully.

## Architecture

### Config Types (nancy-core, no I/O)

- `GlobalConfig` — serde struct with defaults
- `ProjectConfig` — all-Optional override struct
- `ResolvedConfig` — merged result
- `CliOverrides` — Optional CLI flag values
- `ResolvedConfig::resolve(global, project, cli)` — cascade logic

### Config Loading (nancy-cli, file I/O)

- `load_global_config()` → GlobalConfig
- `load_project_config(root)` → Option<ProjectConfig>

### Workspace (nancy-cli)

- `Workspace::discover(from)` → full context struct
- `Workspace::resolve_config(cli_overrides)` → ResolvedConfig
- `Workspace::is_initialized()` → bool
- `Workspace::project_name()` → &str

### Command Modules (nancy-cli/src/commands/)

- `orient.rs` — bare nancy experience
- `init.rs` — create .nancy/ structure
- `run.rs` — migrated from current main.rs
- `status.rs` — detailed status
- `history.rs` — session history with count flag

### Clap Dispatch (main.rs)

```rust
#[derive(Parser)]
#[command(args_conflicts_with_subcommands = true)]
struct Cli {
    #[command(subcommand)]
    command: Option<Command>,
    #[arg(trailing_var_arg = true)]
    prompt: Vec<String>,
    #[arg(long, short = 'C', global = true)]
    dir: Option<PathBuf>,
}
```

Routing: `Some(subcommand)` → dispatch, `None + prompt` → run sugar, `None + empty` → orient.

## What This Enables (Future)

This foundation is required before:

- Chat TUI (nancy spawns a full-screen chat session)
- Task management (continue task / new task menu)
- Multi-panel views (when spawning parallel workers)
- Research agents (that write to ~/.mdx)
- SPEC.md generation and Linear issue creation

## Files

### Modified

- `Cargo.toml` (workspace) — add toml dep
- `crates/nancy-cli/Cargo.toml` — add toml dep
- `crates/nancy-core/src/lib.rs` — add config module
- `crates/nancy-cli/src/lib.rs` — add new modules
- `crates/nancy-cli/src/main.rs` — full rewrite to subcommands

### Created

- `crates/nancy-core/src/config.rs`
- `crates/nancy-cli/src/config.rs`
- `crates/nancy-cli/src/workspace.rs`
- `crates/nancy-cli/src/commands/{mod,orient,init,run,status,history}.rs`

### Unchanged

- journal.rs, supervisor.rs, all other crates
