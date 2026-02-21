# Lessons Learned: Nancy Bash to Rust

Research document for the nancyr rewrite, based on analysis of the Nancy v2.0.0 bash
codebase at `/Users/alphab/Dev/LLM/DEV/TMP/nancy/`.

---

## 1. Architecture Overview

Nancy is an autonomous task execution framework built as a collection of ~30 bash
scripts organized into modules. The architecture follows an orchestrator/worker pattern
where:

- A **worker** (Claude Code running autonomously) executes tasks from Linear issues
- An **orchestrator** (another Claude Code instance) supervises and provides guidance
- A **tmux layout** provides the visual shell, with panes for worker, orchestrator, and inbox
- **File-based IPC** connects the components via inbox/outbox directories
- **Linear** is the source of truth for task state

The module structure mirrors what you would build in Rust:

```
nancy (entrypoint)
  src/lib/     - logging, formatting, UUID generation
  src/core/    - UI components (gum wrappers), dependency checks
  src/config/  - JSON config loading via jq
  src/cli/     - CLI driver abstraction (claude, copilot)
  src/task/    - task CRUD, session management, token tracking
  src/comms/   - file-based IPC (inbox/outbox pattern)
  src/notify/  - file watchers (fswatch), token threshold alerts
  src/linear/  - Linear GraphQL API client
  src/gql/     - raw GraphQL query builder
  src/nav/     - tmux navigation menus
  src/cmd/     - command implementations (start, orchestrate, experiment, etc.)
  templates/   - prompt templates with {{variable}} substitution
```

Each module has an `index.sh` that sources its constituent files. The entrypoint
`nancy` sources all indexes, then dispatches to `cmd::*` functions via a case statement.

---

## 2. What Works Well (Preserve in Rust)

### 2.1 File-Based IPC

The comms system (`src/comms/comms.sh`) is the standout architectural decision. Messages
are markdown files dropped into inbox directories:

```
.nancy/tasks/<task>/comms/
  orchestrator/inbox/   - messages TO orchestrator
  orchestrator/outbox/  - messages FROM orchestrator
  worker/inbox/         - messages TO worker
  worker/outbox/        - messages FROM worker
  archive/              - processed messages
```

Each message is a self-describing markdown file with frontmatter-style headers:

```markdown
# Message

**Type:** blocker
**From:** worker
**Priority:** urgent
**Time:** 2026-02-14T10:30:00Z

## Content

I'm stuck on the auth module because...
```

**Why this works:**
- Human-readable without tools (just `cat` a file)
- `git`-friendly, auditable, diffable
- No daemon required; sender writes, receiver reads
- Natural ordering via timestamped filenames (`20260214T103000Z-001.md`)
- Archive is just `mv`; no database cleanup
- fswatch or inotify gives you reactive notifications for free

**Preserve in Rust:** Keep the file-based protocol. Don't replace it with sockets or
channels. The debuggability and auditability of files on disk is a feature, not a
limitation. What Rust adds is typed message construction and proper deserialization
rather than grepping for `**Type:**` with sed:

```bash
# Current: parsing message metadata by grepping markdown (fragile)
msg_type=$(grep -m1 '^\*\*Type:\*\*' "$filepath" | sed 's/.*\*\*Type:\*\*[[:space:]]*//')
msg_from=$(grep -m1 '^\*\*From:\*\*' "$filepath" | sed 's/.*\*\*From:\*\*[[:space:]]*//')
```

### 2.2 Git Worktree Isolation

Each task gets its own git worktree (`_start_setup_worktree` in `src/cmd/start.sh`):

```bash
local worktree_dir="${parent_dir}/${main_repo_name}-worktrees/nancy-${task}"
git worktree add "$worktree_dir" -b "nancy/$task"
```

This is elegant: the worker operates in complete isolation on branch `nancy/<task>`,
commits don't interfere with other work, and the main repo stays clean. The Rust version
should keep this pattern, potentially using `git2` for more control over worktree
lifecycle.

### 2.3 Template-Based Prompt Assembly

The prompt template system (`templates/PROMPT.md.template`) is well-designed. A single
markdown template with `{{VARIABLE}}` placeholders gets rendered with task-specific
context. The template encodes the worker's entire operating protocol: authority model,
sidecar navigation, collaboration model, work loop, completion criteria, and
communication protocol.

This is the right abstraction level. The Rust version should use a proper template engine
(Tera or Handlebars) but preserve the concept of prompts-as-versioned-templates.

### 2.4 Linear as Source of Truth

The system treats Linear as the canonical task state store. Workers update Linear issue
status (`In Progress` / `Worker Done`), the orchestrator reads Linear to understand
progress, and all messaging gets mirrored as Linear comments:

```bash
linear::issue:comment:add "$task" "Message sent: $from -> $to ($msg_type): $message"
```

This means you can always reconstruct what happened by reading the Linear timeline.
Keep this. The Rust version gets proper error handling on API failures (which bash
silently swallows) and can batch updates.

### 2.5 CLI Driver Abstraction

The dispatch pattern in `src/cli/dispatch.sh` is surprisingly clean for bash:

```bash
cli::run_prompt() {
    local cli=$(cli::current)    # "claude" or "copilot"
    "cli::${cli}::run_prompt" "$@"  # dynamic dispatch via string interpolation
}
```

With drivers implementing a common interface: `detect`, `version`, `run_prompt`,
`run_interactive`, `init_session`, `supports_resume`, etc. This is a trait in Rust:

```rust
trait CliDriver {
    fn detect() -> bool;
    fn version() -> String;
    fn run_prompt(&self, prompt: &str, session: &Session) -> Result<ExitStatus>;
    fn run_interactive(&self, prompt: &str) -> Result<ExitStatus>;
}
```

### 2.6 Sidecar-First Navigation Protocol

The prompt template embeds a code navigation protocol that teaches the LLM worker to
read `.fmm` metadata sidecars before opening source files. This is injected via the
template system and is infrastructure-agnostic. The Rust version should continue to
inject navigation protocols via templates, not hard-code them.

---

## 3. What Fights Bash (Rust Fixes)

### 3.1 No Types: State Exists Only as Strings and Files

The system has implicit state machines everywhere but no way to enforce them.

**Task lifecycle** is a set of conventions, not a type:
- Task exists = directory exists (`[[ -d "${NANCY_TASK_DIR}/${task}" ]]`)
- Task complete = sentinel file exists (`[[ -f ".../$task/COMPLETE" ]]`)
- Task paused = sentinel file exists (`[[ -f ".../$task/PAUSE" ]]`)
- Task sessions = count of `*.md` files in `sessions/` directory

**Message types** are validated at runtime by linear search through arrays:

```bash
declare -a COMMS_WORKER_TYPES=("blocker" "progress" "review-request")
declare -a COMMS_ORCHESTRATOR_TYPES=("directive" "guidance" "stop")

comms::_validate_type() {
    # ... loop through array checking string equality
    for valid in "${valid_types[@]}"; do
        if [[ "$msg_type" == "$valid" ]]; then return 0; fi
    done
}
```

**Config** is re-parsed from JSON on every access:

```bash
export NANCY_CLI=$(jq -r '.cli // "copilot"' "$NANCY_CONFIG_FILE")
export NANCY_MODEL=$(jq -r '.model // ""' "$NANCY_CONFIG_FILE")
```

**Rust fix:** Enums for task state, message types, and priorities. Serde for config.
A `Task` struct that carries its state machine. Impossible to send a `"directive"` from
a worker role because the type system prevents it at compile time.

```rust
enum TaskState { Created, InProgress, Paused, WorkerDone, Complete }
enum WorkerMessage { Blocker(String), Progress(String), ReviewRequest(String) }
enum OrchestratorMessage { Directive(String), Guidance(String), Stop }
```

### 3.2 JSON Munging via jq Subshells

Every interaction with structured data spawns one or more `jq` subprocesses. The token
tracking module (`src/task/token.sh`) is the worst offender -- a single `token::update`
call spawns 6 jq processes and 1 awk process:

```bash
token::update() {
    local usage=$(token::parse_usage "$line")       # jq #1
    local input=$(echo "$usage" | jq -r '.input_tokens // 0')    # jq #2
    local cache_creation=$(echo "$usage" | jq -r '.cache_creation_input_tokens // 0')  # jq #3
    local cache_read=$(echo "$usage" | jq -r '.cache_read_input_tokens // 0')    # jq #4
    local output=$(echo "$usage" | jq -r '.output_tokens // 0')  # jq #5
    # ...
    local percent=$(awk "BEGIN {printf \"%.1f\", ($total_input / $TOKEN_CONTEXT_LIMIT) * 100}")
    # ...
    jq -n --argjson total_input "$total_input" ... '{...}' > "$tmp_file"  # jq #6
}
```

This runs inside `tail -F | while read` in the token watcher, meaning it fires on every
assistant message. The overhead is substantial.

The GraphQL layer (`src/gql/index.sh`) builds JSON by string concatenation with manual
escaping:

```bash
gql::query::variables() {
    variables="{"
    for var in "$@"; do
        key=${var%%::*}
        value=${var#*::}
        if [ "${key::1}" == "!" ]; then
            variables+="\"${key:1}\":$value"     # unquoted: injection risk
        else
            local escaped_value=$(jq -n --arg val "$value" '$val')
            variables+="\"$key\":$escaped_value"  # safe but spawns jq per variable
        fi
        # manual comma tracking...
    done
    variables+="}"
}
```

**Rust fix:** `serde_json` eliminates all of this. Parse once, access fields directly.
Zero subprocess overhead. The GraphQL variable builder becomes a struct derive.

### 3.3 No Concurrency Model

The worker loop in `start.sh` is strictly sequential: fetch context, render prompt, run
CLI, wait for exit, maybe run review, check completion, sleep, repeat. The token watcher
and inbox watcher are separate background processes communicating through PID files and
signal handlers:

```bash
# Start watcher as backgrounded subshell
( trap '...' SIGINT SIGTERM; tail -F "$jsonl_file" | while read -r line; do ... done ) &
local watcher_pid=$!
echo "$watcher_pid" > "$pid_file"

# Later, to stop it:
local watcher_pid=$(cat "$pid_file")
kill "$watcher_pid" 2>/dev/null
rm -f "$pid_file"
```

This pattern appears three times: once for the inbox watcher, once for the token watcher,
and implicitly in the tmux pane management. Each has its own PID file, its own cleanup
trap, its own "is it still running?" check. It is the same boilerplate every time, and
all three instances have edge cases around stale PID files and orphaned processes.

The `sleep 0.1` sprinkled through the watcher code is a tell -- bash has no way to know
when a file write has completed, so it guesses:

```bash
fswatch -0 --event Created "$orchestrator_inbox" "$worker_inbox" | while read -r -d '' event; do
    sleep 0.1  # "Brief delay for file write completion"
    if [[ -f "$event" ]]; then
        # ...
    fi
done
```

**Rust fix:** Tokio gives you `select!` over file events, process exits, timers, and
channels simultaneously. A single event loop replaces three background subshells with
PID file management. `notify` crate replaces fswatch dependency. No more `sleep 0.1`
hoping a write finished.

### 3.4 No Real Error Handling

The bash codebase uses three error strategies, all inadequate:

1. **Suppress and continue:** `2>/dev/null || true` (appears ~15 times)
2. **Exit the universe:** `set -e` at the top, `log::fatal` calls `exit 1`
3. **Return codes without context:** functions return 0 or 1 with no structured error

The Linear API client has no retry logic, no rate limit handling, and no structured
error reporting:

```bash
linear::issue:update:status() {
    local state_id=$(
        linear::workflow:states | jq -r "..." # if this returns empty, the next call silently does nothing
    )
    local query=$(gql::query::generate "..." "$variables")
    gql::client::query "$query"  # fire and forget -- no error check
}
```

The comms system silently drops messages if `comms::send` is called before `comms::init`:

```bash
comms::send() {
    comms::init "$task"  # creates dirs if missing -- but what if mkdir fails?
    # ...
    cat > "$filepath" <<EOF   # what if disk is full?
    # ...
    EOF
    # no error check on the write
}
```

**Rust fix:** `Result<T, NancyError>` everywhere. The `?` operator propagates errors
naturally. Retry logic for API calls via tower middleware. Structured error types that
carry context (`TaskNotFound { id: String }` vs `return 1`).

### 3.5 Template Rendering via String Replacement

Prompt rendering is repeated bash string replacement -- the same block appears in
`start.sh`, `experiment.sh`, and the review agent:

```bash
local prompt=$(cat "$template_file")
prompt="${prompt//\{\{NANCY_PROJECT_ROOT\}\}/$NANCY_PROJECT_ROOT}"
prompt="${prompt//\{\{NANCY_CURRENT_TASK_DIR\}\}/$NANCY_CURRENT_TASK_DIR}"
prompt="${prompt//\{\{SESSION_ID\}\}/$session_id}"
prompt="${prompt//\{\{TASK_NAME\}\}/$task}"
prompt="${prompt//\{\{PROJECT_IDENTIFIER\}\}/${project[identifier]}}"
prompt="${prompt//\{\{PROJECT_TITLE\}\}/${project[title]}}"
prompt="${prompt//\{\{PROJECT_DESCRIPTION\}\}/${project[description]}}"
prompt="${prompt//\{\{WORKTREE_DIR\}\}/${worktree[dir]}}"
```

This has no conditionals, no loops, no includes, no escaping. If `PROJECT_DESCRIPTION`
contains the literal string `{{WORKTREE_DIR}}`, it gets double-substituted. If a
variable is missing, the `{{placeholder}}` stays in the output silently.

**Rust fix:** Tera or Handlebars. Conditionals for optional sections. Includes for
composable prompt fragments. Compile-time template validation. The IDEAS.md already
identifies "self-evolving prompts" and "context efficiency" as goals -- a real template
engine is prerequisite infrastructure.

### 3.6 Process Management via Convention

The system manages at least 5 concurrent processes during orchestration:

1. The orchestrator pane (Claude Code interactive)
2. The worker pane (Claude Code autonomous)
3. The inbox/logs pane (fswatch watcher)
4. The token watcher (background `tail -F | while read`)
5. The inbox watcher (background `fswatch | while read`)

Each is started independently, tracked via PID files, and cleaned up via signal traps.
There is no supervisor to restart a crashed watcher. The cleanup handler in `start.sh`
only stops watchers for `_NANCY_CURRENT_TASK` -- if the variable is empty (race
condition during startup), nothing gets cleaned up.

The tmux orchestration (`orchestrate.sh`) sends raw keystrokes to panes:

```bash
tmux send-keys -t "$win.$pane0" "cd '$cwd' && ... '$NANCY_FRAMEWORK_ROOT/nancy' _orchestrator '$task'; echo '[Press Enter to exit]'; read" C-m
```

This is sending a shell command as a string of characters into a terminal emulator.
There is no way to know if the command succeeded, no way to capture its output, and
quoting issues with paths containing special characters will cause silent failures.

**Rust fix:** Process groups with proper supervision. A process manager that owns child
lifecycles, restarts crashed watchers, and handles graceful shutdown. For tmux
integration, use the tmux control mode (`-C`) or tmux CLI directly rather than
keystroke injection.

### 3.7 Module System is Source-Order Dependent

The entrypoint sources all modules in a specific order:

```bash
. "$NANCY_FRAMEWORK_ROOT/src/lib/index.sh"
. "$NANCY_FRAMEWORK_ROOT/src/core/index.sh"
. "$NANCY_FRAMEWORK_ROOT/src/gql/index.sh"
. "$NANCY_FRAMEWORK_ROOT/src/config/index.sh"
. "$NANCY_FRAMEWORK_ROOT/src/cli/index.sh"
. "$NANCY_FRAMEWORK_ROOT/src/task/index.sh"
. "$NANCY_FRAMEWORK_ROOT/src/comms/index.sh"
. "$NANCY_FRAMEWORK_ROOT/src/notify/index.sh"
. "$NANCY_FRAMEWORK_ROOT/src/linear/index.sh"
. "$NANCY_FRAMEWORK_ROOT/src/nav/index.sh"
. "$NANCY_FRAMEWORK_ROOT/src/cmd/index.sh"
```

Everything is in global scope. Every function from every module is visible to every
other module. The `config::load` function has a side effect at source time:

```bash
# Bottom of config.sh
if [[ -d "$NANCY_DIR" ]]; then
    config::load  # side effect on source!
fi
```

The entrypoint then loads config *again*:

```bash
if [[ -f "$NANCY_CONFIG_FILE" ]]; then
    config::load  # also called here
fi
```

**Rust fix:** This is just `mod` and `use`. Explicit dependencies, no global mutable
state, no source-order sensitivity.

### 3.8 Token Tracking is Fragile

Token tracking works by tailing the raw JSONL log output from Claude Code, parsing each
line looking for assistant messages with usage data, and maintaining a separate
`token-usage.json` file:

```bash
tail -n 0 -F "$jsonl_file" 2>/dev/null | while IFS= read -r line; do
    if token::update "$task" "$line" 2>/dev/null; then
        local current_threshold=$(token::check_threshold "$task")
        # ...
    fi
done
```

The fragility is multi-layered:
- Depends on Claude Code's undocumented streaming JSON format
- `tail -F` can miss lines during rapid writes or file rotation
- Each line parse spawns 6+ jq processes (see 3.2)
- Token math has documented uncertainty: `# TODO: verify with more testing`
- The `while read` loop runs in a subshell, so variable updates to `_prev_threshold`
  are scoped correctly only by accident (bash subshells in pipes get their own copies)

**Rust fix:** Parse the JSONL stream in-process with `serde`. Track tokens in a proper
accumulator struct. Use the file watcher event loop (from 3.3) instead of `tail -F`.
Model the token budget as a first-class concept with documented semantics.

---

## 4. What is Missing Entirely

### 4.1 Multi-Worker Coordination

The current architecture is hardcoded to exactly one worker. The tmux layout creates
exactly three panes. The comms system has two roles: `orchestrator` and `worker`. The
IDEAS.md (Idea #10) describes the vision:

```
# Fan-Out Patterns
nancy spawn 3 researchers "Explore authentication approaches"
nancy spawn 3 workers "Implement the auth module"

# Topologies
         +-- Researcher 1 --+
Human -- Orchestrator --+-- Researcher 2 --+-- Synthesis
         +-- Researcher 3 --+
```

Bash cannot deliver this. Dynamic process spawning, inter-worker messaging, result
aggregation, and topology management require a real runtime. The Rust version should
design the comms and process systems to be N-worker from day one:

- Worker IDs instead of a single "worker" role
- Message routing (worker-1 -> orchestrator, worker-2 -> worker-1)
- Process groups per topology
- Fan-in collectors that wait for N results

### 4.2 State Persistence Beyond Files

Task state is scattered across dozens of files and directories:

```
.nancy/tasks/<task>/
  COMPLETE              - sentinel file (task done)
  PAUSE                 - sentinel file (task paused)
  PROMPT.md             - rendered prompt
  ISSUES.md             - issue checklist
  config.json           - task config
  token-usage.json      - current token state
  .watcher_pid          - inbox watcher PID
  .token_watcher_pid    - token watcher PID
  comms/                - message files
  sessions/             - session exports
  session-state/        - raw JSONL copies
  logs/                 - various log files
  outputs/              - (unused in current code)
```

There is no single place to ask "what is the complete state of task X?" You have to
stat files, parse JSON, read markdown, and check PID liveness. There is no transaction
boundary -- a crash between updating Linear and writing COMPLETE leaves state
inconsistent.

**Rust recommendation:** A task state store (SQLite or sled) that provides atomic
state transitions. Keep files for the human-readable audit trail (messages, prompts,
logs) but derive task state from the store, not from filesystem archaeology.

### 4.3 Plugin/Extension System

The CLI driver pattern (`src/cli/dispatch.sh` + `src/cli/drivers/*.sh`) is the closest
thing to a plugin system. But adding a new driver requires modifying the dispatch
layer and adding files in the right directory.

The ROADMAP describes a "Planning Adapter Foundation" (Phase 7) that mirrors the CLI
driver pattern for planning systems. This would be a second copy of the same
hand-rolled plugin mechanism.

**Rust recommendation:** Define traits for the extension points:
- `CliDriver` - how to run an LLM CLI (Claude, Copilot, future tools)
- `PlanningDriver` - how to generate and validate plans (minimal, PRD, future systems)
- `NotificationDriver` - how to alert the user (terminal-notifier, tmux popup, webhook)
- `TaskStore` - where state lives (filesystem, SQLite, remote)

### 4.4 TUI Beyond tmux

The current UI is tmux panes + gum widgets. The navigation system (`src/nav/nav.sh`)
hit a wall trying to implement sidebar navigation:

```
# From ROADMAP.md Phase 4.1:
# "Prototype attempted: Failed - resize-pane approach didn't achieve true collapse."
```

The IDEAS.md describes the desired UI:

```
+----+----------------------------+
| NAV|                            |
|    |                            |
|[W] |    ACTIVE PANE             |
| O  |    (Worker by default)     |
| I  |                            |
|    |                            |
+----+----------------------------+
  15%         85%
```

tmux cannot do this -- it enforces minimum pane sizes and does not support collapsing
panes to zero width. The Rust version can use ratatui for a proper TUI that owns the
entire terminal:

- Tabbed or sidebar navigation between worker, orchestrator, inbox, and future panes
- Unread indicators on tabs
- Scrollback per pane
- Token usage gauge
- Task progress dashboard

### 4.5 Session Intelligence

IDEAS.md items 5a/5b/5c describe session data as an untapped goldmine:

- **Handover documents** generated at session end
- **Completion indexing** that summarizes and indexes session transcripts
- **Session search** across the history ("when did we decide X?")

The bash version copies Claude's JSONL session files and exports markdown summaries, but
has no indexing, search, or summarization capability. This requires structured data
processing that bash cannot provide.

### 4.6 Self-Evolving Prompts

IDEAS.md item 7 describes prompts that evolve based on execution feedback. This requires:

- Observing what worked/failed during execution (parsing session data)
- Generating prompt amendments (LLM call to analyze effectiveness)
- Version-controlling prompt iterations
- Measuring "prompt effectiveness" over time

This is a data pipeline that needs structured storage, LLM API access, and comparative
analysis -- none of which bash can provide cleanly.

---

## 5. Specific Code Patterns to Migrate

### 5.1 The Nameref Pattern

Nancy uses bash namerefs (`local -n`) extensively to return structured data from
functions:

```bash
_start_fetch_linear_context() {
    local task="$1"
    local -n _project_data=$2   # nameref to caller's associative array

    # ...
    _project_data[id]="..."
    _project_data[identifier]="..."
    _project_data[title]="..."
}

# Caller:
declare -A project
_start_fetch_linear_context "$task" project
echo "${project[identifier]}"
```

This is bash's approximation of returning a struct. In Rust, it is just a return value:

```rust
struct ProjectContext {
    id: String,
    identifier: String,
    title: String,
    description: String,
}

fn fetch_linear_context(task: &str) -> Result<ProjectContext> { ... }
```

### 5.2 The Streaming JSON Formatter

The `_claude_format_stream` function in `claude.sh` is a 90-line jq program that
processes streaming JSON events from Claude Code and renders them as colored terminal
output. It handles assistant text, tool calls, tool results, token checks, directives,
session start/end, and result truncation.

This is impressive jq, but it runs as a persistent subprocess with `--unbuffered` and
processes every line of output. In Rust, this becomes a `serde` deserializer feeding a
`ratatui` widget or a simple line formatter, with pattern matching replacing the
nested `if/elif` chains:

```rust
match event {
    Event::System { subtype: "init", model, .. } => { /* session started */ }
    Event::Assistant { message } => {
        for content in &message.content {
            match content {
                Content::Text { text } => { /* display text */ }
                Content::ToolUse { name, input } => { /* display tool call */ }
            }
        }
    }
    Event::Result { subtype, total_cost_usd, duration_ms, .. } => { /* session ended */ }
    _ => {}
}
```

### 5.3 The Threshold State Machine

The token alert system implements a one-way threshold escalation (ok -> info -> warning
-> critical -> danger) using string matching:

```bash
notify::_should_alert_on_threshold() {
    local prev="$1"
    local current="$2"
    case "$prev" in
        ok)       [[ "$current" =~ ^(info|warning|critical|danger)$ ]] && return 0 ;;
        info)     [[ "$current" =~ ^(warning|critical|danger)$ ]] && return 0 ;;
        warning)  [[ "$current" =~ ^(critical|danger)$ ]] && return 0 ;;
        critical) [[ "$current" == "danger" ]] && return 0 ;;
    esac
    return 1
}
```

This is a state machine encoded as string comparison. In Rust:

```rust
#[derive(PartialOrd, Ord, PartialEq, Eq)]
enum Threshold { Ok, Info, Warning, Critical, Danger }

fn should_alert(prev: Threshold, current: Threshold) -> bool {
    current > prev && current > Threshold::Ok
}
```

---

## 6. External Dependencies to Replace

| Bash Dependency | Used For | Rust Replacement |
|---|---|---|
| `jq` | All JSON parsing/creation | `serde_json` |
| `gum` | Terminal UI (choose, confirm, spin, style) | `ratatui` + `crossterm` |
| `fswatch` | File system watching | `notify` crate |
| `tmux` | Pane layout, process hosting | `ratatui` TUI (own process) |
| `curl` | HTTP requests (Linear API) | `reqwest` |
| `gh` | GitHub CLI (experiments) | `octocrab` or `reqwest` |
| `column` | Table formatting | `tabled` or manual formatting |
| `awk` | Float math (token percentages) | Native f64 arithmetic |
| `tail -F` | Following log files | `tokio::fs` + `notify` |
| `terminal-notifier` | macOS notifications | `notify-rust` crate |

---

## 7. Recommended Rust Crate Stack

| Concern | Crate | Rationale |
|---|---|---|
| Async runtime | `tokio` | File watching + process mgmt + HTTP all need async |
| HTTP client | `reqwest` | Linear GraphQL, future webhook integrations |
| GraphQL | `graphql_client` | Typed Linear API queries (code generation from schema) |
| JSON | `serde` + `serde_json` | Replaces all jq usage |
| CLI parsing | `clap` (derive) | Replaces the case statement dispatch |
| Terminal UI | `ratatui` + `crossterm` | Replaces tmux + gum |
| File watching | `notify` | Replaces fswatch dependency |
| Templates | `tera` | Replaces `${prompt//\{\{VAR\}\}/$val}` |
| Git | `git2` | Worktree management, branch operations |
| SQLite | `rusqlite` | Task state persistence |
| Process mgmt | `tokio::process` | Child process supervision |
| Logging | `tracing` | Structured logging with spans |
| Error handling | `thiserror` + `anyhow` | Replaces `return 1` and `2>/dev/null \|\| true` |
| Config | `figment` or `config` | Layered config (defaults -> global -> task) |
| Notifications | `notify-rust` | macOS/Linux native notifications |

---

## 8. Migration Priority

Based on pain-vs-value analysis, the recommended build order for the Rust version:

### Phase 1: Core Data Model
1. **Task state machine** (enum, transitions, persistence) -- fixes 3.1
2. **Message types** (typed IPC, serde serialization) -- fixes 3.1, 3.2
3. **Config loading** (figment with layered sources) -- fixes 3.1, 3.7

### Phase 2: Infrastructure
4. **Template engine** (Tera, prompt rendering) -- fixes 3.5
5. **Linear GraphQL client** (typed, with retries) -- fixes 3.2, 3.4
6. **Git worktree manager** (git2) -- preserves 2.2

### Phase 3: Runtime
7. **Process supervisor** (tokio, child management) -- fixes 3.3, 3.6
8. **File watcher** (notify crate, event loop) -- fixes 3.3
9. **Token tracker** (in-process, typed) -- fixes 3.8
10. **CLI driver trait** (Claude, future CLIs) -- preserves 2.5

### Phase 4: Interface
11. **TUI** (ratatui, replaces tmux layout) -- fixes 4.4
12. **Multi-worker support** (N workers, routing) -- fixes 4.1
13. **Session intelligence** (indexing, search) -- fixes 4.5

---

## 9. Key Design Principles for the Rewrite

1. **Keep files as the communication medium.** The file-based IPC is a feature. Rust
   adds types and atomicity on top of it, not a replacement for it.

2. **State machines for everything.** Task state, message lifecycle, token thresholds,
   session phases -- if it transitions, model it as an enum.

3. **Own the event loop.** One async runtime managing all concurrent concerns (file
   watching, process supervision, HTTP, UI rendering) instead of N background subshells
   with PID files.

4. **Trait-based extension.** CLI drivers, planning systems, notification backends,
   task stores -- define the trait, ship default implementations, allow swapping.

5. **Prompt templates are product.** They encode the operating protocol for AI workers.
   Treat them as first-class versioned artifacts with a proper engine, not string
   replacement.

6. **Linear is source of truth, SQLite is local cache.** Don't try to replace Linear
   with local state. Use local state for fast reads and crash recovery, sync to Linear
   for persistence and collaboration.

7. **Debuggability over elegance.** The bash version's greatest strength is that you
   can `ls` and `cat` your way to understanding system state. The Rust version must
   preserve this quality -- human-readable files on disk, structured logs, no opaque
   binary state.
