---
title: Nancy Orchestrator Architecture and Worker Lifecycle
type: research
tags: [nancy, orchestration, worker-lifecycle, ipc, git-worktrees, parallel-agents]
summary: Deep analysis of nancy's orchestration loop, worker supervision, file-based IPC, worktree management, and what exists (and is missing) for parallel multi-worker execution.
status: active
source: codebase-analyst
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Executive Summary

Nancy is a bash-based orchestrator (~14k LOC across shell scripts) that supervises AI coding agents (currently Claude Code) working on Linear issues. It provides a tmux-based split-pane UI with an orchestrator agent, a worker agent, and a message relay. Communication is file-based IPC through inbox/outbox directories. Workers operate in isolated git worktrees. The system currently runs **one worker per task** in a sequential iteration loop. The building blocks for parallel workers exist in embryonic form (worktree isolation, file-based comms, agent role tagging) but the orchestration loop itself is single-threaded and would need structural changes to spawn concurrent workers on different branches.

## Project Metadata

- **Language:** Bash (set -euo pipefail throughout)
- **Dependencies:** tmux, jq, fswatch, gh CLI, claude CLI, git, Linear API (GraphQL)
- **Structure:** ~30 shell files across `src/` with module pattern (each dir has `index.sh`)
- **Version:** 2.0.0
- **Config:** JSON-based, two-tier inheritance (global `.nancy/config.json`, per-task `config.json`)

## 1. Orchestrator Supervision Model

### The Orchestration Loop (`src/cmd/start.sh`)

The core is `cmd::start`, a `while :; do` loop that:

1. Fetches Linear issue context (parent + sub-issues) via GraphQL
2. Generates `ISSUES.md` from Linear sub-issues, sorted by `subIssueSortOrder`
3. Detects the next agent role from the first uncompleted issue's "Agent Role" label
4. Archives stale directives from the previous iteration
5. Renders the worker prompt from `templates/PROMPT.md.template` with variable substitution
6. Launches a background token watcher (`notify::watch_tokens_bg`)
7. Invokes Claude Code via `cli::run_prompt` (streaming JSON, piped through formatters to log files)
8. After Claude exits: checks for STOP sentinel, runs optional code review agent, checks COMPLETE file
9. Checks PAUSE lock file (busy-waits with `sleep 2` until removed)
10. Sleeps 2 seconds, then loops

Each iteration gets a fresh Claude session (new UUID). Sessions are not resumed across iterations. The worker's context window is the unit of work.

### Control Primitives

| Command | Mechanism | Behavior |
|---------|-----------|----------|
| `nancy pause <task>` | Creates `PAUSE` lock file + sends "end turn cleanly" guidance message | Worker completes current turn, then loop busy-waits on lock file |
| `nancy unpause <task>` | Removes `PAUSE` lock file | Loop resumes on next 2-second poll |
| `nancy stop <task>` | Kills worker PID (SIGTERM then SIGKILL after 1s) + writes `STOP` sentinel | Loop exits after pipeline returns |
| `nancy direct <task> "msg"` | Writes message to `worker/inbox/` via comms API | Worker reads on next `nancy inbox` check |
| `nancy status` | Reads task directories, counts sessions, checks COMPLETE file | Pure status query, no side effects |

File paths for control signals:
- `$NANCY_TASK_DIR/$task/PAUSE` - pause lock
- `$NANCY_TASK_DIR/$task/STOP` - stop sentinel
- `$NANCY_TASK_DIR/$task/COMPLETE` - completion marker (written by worker: `echo "done" > COMPLETE`)
- `$NANCY_TASK_DIR/$task/.worker_pid` - Claude process PID

### The Orchestrator Agent (`src/cmd/internal.sh` + `templates/orchestrator.md`)

The orchestrator is a separate Claude Code instance running interactively in tmux pane 0. It receives a prompt (`templates/orchestrator.md`) that instructs it to:

- Monitor formatted logs and token usage
- Read worker messages via `nancy messages`
- Send directives via `nancy direct`
- Create Linear sub-issues for the worker
- Detect worker state by checking whether log files are growing

The orchestrator is advisory. It cannot programmatically control the worker loop. Its only actuators are `nancy direct` (file-based message) and `nancy pause/stop` (sentinel files). The human retains authority.

## 2. Git Worktree Management

### Worktree Creation (`_start_setup_worktree` in `start.sh`)

- Naming convention: `<parent-dir>/<repo-name>-worktrees/nancy-<task>`
- Branch naming: `nancy/<task>` (created with `git worktree add -b`)
- If the worktree already exists, reuses it (idempotent)
- Copies `.env*` files and `.fmm.db` into the worktree
- Runs `just install` if `node_modules` is missing
- The worker `cd`s into the worktree for all subsequent work

### Key Properties

- Workers are fully isolated at the git level. Each task gets its own branch and working directory.
- The main repo is treated as read-only context (the orchestrator template explicitly says so).
- Worktrees share git objects with the main repo, so branch creation is cheap.
- No worktree cleanup mechanism exists. Old worktrees accumulate.

### Parallel Worktree Implications

The worktree setup is already parameterized by task name. Two tasks would get two separate worktrees on two separate branches. The infrastructure for parallel worktrees exists. What does not exist is the orchestrator logic to spawn and supervise multiple workers simultaneously.

## 3. Message-Passing Protocol

### Architecture

File-based IPC with an inbox/outbox pattern per role:

```
$NANCY_TASK_DIR/$task/comms/
  orchestrator/
    inbox/     # Messages FROM worker TO orchestrator
    outbox/    # (unused in current code)
  worker/
    inbox/     # Messages FROM orchestrator TO worker (directives)
    outbox/    # (unused in current code)
  archive/     # Processed messages moved here
```

### Message Format

Markdown files named `<UTC-timestamp>-<seq>.md`:

```markdown
# Message

**Type:** directive
**From:** orchestrator
**Priority:** urgent
**Time:** 2026-03-13T10:30:00Z

## Content

Your guidance text here.
```

### Message Types

| Direction | Types | Purpose |
|-----------|-------|---------|
| Worker to Orchestrator | `blocker`, `progress`, `review-request` | Worker reports status or requests help |
| Orchestrator to Worker | `directive`, `guidance`, `stop` | Orchestrator steers or halts the worker |

### Delivery Mechanism

Messages are not pushed. They are polled:

- **Worker side:** The worker prompt instructs the agent to run `nancy inbox` periodically. The fswatch-based watcher (`notify::inject_directive_check`) can also inject `nancy inbox` into the worker's tmux pane via `tmux send-keys`.
- **Orchestrator side:** `nancy messages` lists the orchestrator inbox. The watcher injects `nancy messages` into the orchestrator pane when a new file appears.
- **Token threshold alerts:** The background token watcher (`notify::watch_tokens_bg`) directly writes directive messages to `worker/inbox/` when usage crosses 65%/75%/85% thresholds.

### Lifecycle

1. Sender writes a `.md` file to the recipient's inbox directory
2. `fswatch` detects the new file, displays it in the Inbox pane, and optionally injects a read command via tmux
3. Recipient reads the message (`nancy read <filename>`)
4. Recipient archives the message (`nancy archive <filename>`)
5. Between iterations, `comms::archive_all` sweeps stale messages

### Limitations for Parallel Workers

The comms system assumes exactly two roles: one orchestrator, one worker. The directory structure is hardcoded to `orchestrator/inbox` and `worker/inbox`. To support multiple parallel workers, you would need either:

- Per-worker inbox directories (`worker-1/inbox`, `worker-2/inbox`)
- Or a bus-style model where messages carry sender/recipient IDs

The comms API functions (`comms::send`, `comms::worker_send`, `comms::orchestrator_send`) would need a worker ID parameter.

## 4. Sequential vs. Parallel Execution

### Current Model: Strictly Sequential

The `cmd::start` loop processes one iteration at a time. Within an iteration, the worker processes issues sequentially (the prompt explicitly says "Work on ONE issue at a time, in list order"). The code review agent runs after the worker exits, also sequentially.

The `NANCY_EXECUTION_MODE` variable supports two modes:
- `loop` (default): infinite iteration loop
- `single-run`: exit after one iteration (used by `cmd::experiment`)

### Agent Role System

Linear issues can have "Agent Role" labels (e.g., labels parented under "Agent Role"). When the first uncompleted issue has a role tag, the worker prompt includes an `AGENT_ROLE_SECTION` that:

- Constrains the worker to only work on issues tagged with its role
- Instructs the worker to hand off when it reaches an issue owned by another specialist
- Warns that "the quality gate will discard unauthorized work"

This is the closest thing to a parallel execution primitive. The intention is visible: multiple specialist workers on different issue subsets. But the actual spawning and scheduling of multiple role-specific workers does not exist in the current codebase. The start loop runs one worker at a time regardless of role.

### Experiment Mode

`cmd::experiment` runs two sequential conditions (A/B) for benchmarking. Each condition gets its own cloned repo (not a worktree), its own task directory, and runs in `single-run` mode. This is sequential A then B execution, not parallel.

## 5. Hooks and Extension Points

### Template System

Prompts are rendered from `templates/*.md.template` files with `{{VARIABLE}}` substitution. Available templates:

- `PROMPT.md.template` - Main worker prompt
- `PROMPT.baseline.md.template` - Baseline worker prompt (for experiments)
- `PROMPT.sidecar-first.md.template` - Alternative worker prompt variant
- `REVIEW.md.template` - Code review agent prompt
- `orchestrator.md` - Orchestrator agent prompt

### Project-Local Prompt Overrides

- `$NANCY_PROJECT_ROOT/PROMPT.md` - Appended to the worker prompt if present
- `$NANCY_PROJECT_ROOT/PROMPT.review.md` - Appended to the review prompt if present

### CLI Driver System

`src/cli/drivers/` contains pluggable CLI backends. Currently `claude.sh` and `copilot.sh`. Each driver implements:

- `cli::<name>::detect` - CLI availability check
- `cli::<name>::run_prompt` - Non-interactive prompt execution
- `cli::<name>::run_interactive` - Interactive session
- `cli::<name>::version`, `session_dir`, `init_session`, etc.

The dispatcher (`src/cli/dispatch.sh`) routes through `NANCY_CLI` config.

### Config Inheritance

Global config at `.nancy/config.json`, overridable per-task at `.nancy/tasks/<task>/config.json`. Supports `cli`, `model`, and `token_threshold` fields.

### Notification System

`src/notify/` provides:

- `watcher.sh` - fswatch-based file watchers for inbox directories and token usage
- `inject.sh` - tmux `send-keys` injection for Claude Code panes
- `os.sh` - OS-level notifications (likely macOS notification center)
- `router.sh` - Notification routing

The injection system (`notify::inject_prompt`) sends text directly into tmux panes, which is how the watcher notifies Claude about new messages without waiting for the agent to poll.

### Linear Integration

Deep integration with Linear for issue tracking:
- Fetches parent/sub-issue hierarchy
- Updates issue states (`In Progress`, `Worker Done`, etc.)
- Adds comments on message sends
- Auto-generates `ISSUES.md` from Linear data

### Code Review Sidecar

When `NANCY_CODE_REVIEW_AGENT_ENABLED=true` (currently the default), a second Claude session runs after each worker iteration using `REVIEW.md.template`. This is a sequential post-processing step, not a parallel reviewer.

## 6. What Exists for Parallel Workers

**Already built and usable:**

1. **Git worktrees** - Each task gets an isolated worktree. The naming and creation logic is parameterized.
2. **File-based IPC** - Messages are independent files. Multiple writers to the same inbox would work (the sequence counter handles same-second collisions).
3. **Agent role labels** - The infrastructure to tag issues with specialist roles and generate role-constrained prompts exists.
4. **tmux layout** - The 3-pane layout could be extended. tmux supports arbitrary pane splitting.
5. **Token tracking** - Per-task token usage files, independent across tasks.
6. **PID management** - Worker PID files for process lifecycle control.

**Missing for true parallel execution:**

1. **Multi-worker orchestration loop** - `cmd::start` is single-threaded. Need a `cmd::parallel_start` or equivalent that spawns N workers in background subshells, each on its own worktree/branch.
2. **Worker identity** - Comms assume one worker. Need worker IDs for routing messages to specific workers.
3. **Merge coordination** - No mechanism to merge multiple worker branches back together or handle conflicts.
4. **Shared state coordination** - No locking or coordination for Linear state updates across concurrent workers.
5. **Worker health monitoring** - The orchestrator monitors one formatted log. Multi-worker monitoring would need a dashboard or aggregated log.
6. **Branch dependency graph** - No concept of "worker B depends on worker A's output" for sequential-then-parallel workflows.

## 7. Relevance to Helioy

Nancy is the MVP prototype for what nancyr (the Rust rewrite) will formalize. Key patterns to preserve:

- **File-based IPC** aligns with helioy-bus's file/message model. The bus could replace the raw filesystem inbox pattern.
- **Worker isolation via git worktrees** is the right primitive. Worktrees are cheaper than clones and share git objects.
- **Prompt templating with variable substitution** works well for bash. nancyr would likely use a proper template engine.
- **The orchestrator-as-agent pattern** (Claude supervising Claude) is architecturally interesting but currently advisory only. nancyr could give the orchestrator real control plane authority.
- **Token budget tracking with progressive alerts** is production-grade. The high-water-mark approach for context window tracking is correct.

## Open Questions

1. How does the code review agent's feedback get back to the worker? It runs after the worker exits. Its output presumably lands in logs, but the next worker iteration would need to read those.
2. The outbox directories (`orchestrator/outbox`, `worker/outbox`) are created but never used. Were they intended for audit trails?
3. What happens when two tasks are started simultaneously from different terminal sessions? The global `NANCY_CURRENT_TASK_DIR` export suggests potential conflicts.
4. The `nancy.init.wip.sh` file suggests an alternative initialization flow was being explored. What was the intent?
5. How would agent role handoffs work across iterations when multiple specialists need to take turns? The current system detects the first uncompleted issue's role but does not schedule role transitions.
