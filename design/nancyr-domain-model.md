# Nancy Domain Model

> The conceptual core that survives the rewrite. Language-agnostic abstractions
> that define what Nancy IS, extracted from what bash Nancy taught us.

---

## Core Insight

Nancy is not a coding agent. Nancy is a **supervisory control system** for
autonomous coding agents. The agent does the work. Nancy does the orchestration,
communication, isolation, and lifecycle management.

Think air traffic control, not autopilot.

---

## Entities

### Task

The top-level unit of work. Maps 1:1 to a Linear parent issue (epic).

```
Task {
    id: TaskId,              // Linear issue identifier (e.g., "ALP-198")
    name: String,            // Human-friendly name
    state: TaskState,        // Lifecycle state machine
    issues: Vec<Issue>,      // Sub-issues (the actual work items)
    worktree: Worktree,      // Isolated git workspace
    config: TaskConfig,      // Task-specific overrides
    comms: Channel,          // Bidirectional message channel
    sessions: Vec<Session>,  // Execution history
    created_at: DateTime,
    completed_at: Option<DateTime>,
}
```

**State machine:**

```
         ┌──────────┐
         │ Created  │
         └────┬─────┘
              │ orchestrate
         ┌────▼─────┐
    ┌───►│ Running  │◄───┐
    │    └────┬─────┘    │
    │         │ pause    │ unpause
    │    ┌────▼─────┐    │
    │    │ Paused   ├────┘
    │    └──────────┘
    │         │
    │    ┌────▼─────┐
    │    │Completed │  (all issues done, COMPLETE marker)
    │    └────┬─────┘
    │         │
    │    ┌────▼─────┐
    └────┤ Reviewed │  (PR approved/merged)
         └──────────┘
```

### Issue

A discrete unit of implementation work. Maps 1:1 to a Linear sub-issue.

```
Issue {
    id: IssueId,             // Linear identifier (e.g., "ALP-199")
    title: String,
    description: String,     // The spec — what to build
    state: IssueState,       // Todo → InProgress → WorkerDone → Done
    priority: Priority,      // Urgent, High, Normal, Low
    sort_order: f64,         // Manual sort determines execution order
    acceptance_criteria: Vec<Criterion>,
    parent: TaskId,
}
```

**State machine:**

```
  Todo → InProgress → WorkerDone → Done
                  ↑        │
                  └────────┘  (rework after review)
```

### Worker

An autonomous agent process that executes issues. Currently wraps Claude Code
CLI, but the driver abstraction means it could wrap anything.

```
Worker {
    id: WorkerId,
    task: TaskId,
    driver: Driver,          // Which AI CLI to use
    state: WorkerState,      // Idle → Starting → Running → Stopped
    current_issue: Option<IssueId>,
    current_session: Option<SessionId>,
    iterations: u32,         // How many loops completed
    pid: Option<u32>,        // OS process ID when running
}
```

**Key behavior:** The worker LOOPS. Each iteration:

1. Reads git log (learns from previous iterations)
2. Reads ISSUES.md (finds next work item)
3. Checks inbox (processes directives)
4. Executes work (code changes, tests, commits)
5. Updates Linear state
6. Sends progress messages
7. Exits when context is depleted (token threshold)

The loop is Nancy's secret weapon. The agent will make mistakes, but
the loop + git history = self-correction.

### Orchestrator

The supervisory entity. Can be human (interactive terminal) or AI agent.

```
Orchestrator {
    id: OrchestratorId,
    task: TaskId,
    mode: OrchestratorMode,  // Interactive (human) | Autonomous (AI)
    state: OrchestratorState,
}
```

**Responsibilities:**

- Monitor worker progress
- Send directives (immediate instructions)
- Send guidance (suggestions/context)
- Pause/unpause workers
- Trigger reviews
- Create PRs when complete

### Session

A single execution run of a worker. One iteration of the loop.

```
Session {
    id: SessionId,           // UUID
    task: TaskId,
    worker: WorkerId,
    iteration: u32,          // Which loop iteration
    started_at: DateTime,
    ended_at: Option<DateTime>,
    prompt: String,          // The assembled prompt used
    token_usage: TokenUsage, // Input/output/cache tokens
    exit_reason: ExitReason, // Completed | TokenThreshold | Directive | Error
    commits: Vec<CommitHash>,// Git commits made during this session
}
```

Sessions are the audit trail. Each session captures what the worker was told,
what it did, and how much context it consumed.

### Message

A communication unit between orchestrator and worker.

```
Message {
    id: MessageId,           // Timestamp-based, sortable
    from: Role,              // Orchestrator | Worker
    to: Role,
    msg_type: MessageType,   // Typed per role
    priority: Priority,
    content: String,         // Markdown body
    state: MessageState,     // Pending → Read → Archived
    created_at: DateTime,
}
```

**Message types by sender:**

| From Orchestrator          | From Worker                     |
| -------------------------- | ------------------------------- |
| `Directive` — do this now  | `Progress` — status update      |
| `Guidance` — consider this | `Blocker` — I'm stuck           |
| `Stop` — pause execution   | `ReviewRequest` — please review |

### Worktree

Isolated git workspace for a task. Prevents cross-contamination between tasks
and protects the main branch.

```
Worktree {
    task: TaskId,
    path: PathBuf,           // <repo>-worktrees/nancy-<task>/
    branch: String,          // nancy/<task-name>
    base_branch: String,     // main (or whatever the default is)
    created_at: DateTime,
}
```

### Driver

Abstraction over AI CLI tools. Nancy should work with any coding agent that
can be invoked from the terminal.

```
trait Driver {
    fn name(&self) -> &str;
    fn detect(&self) -> bool;
    fn version(&self) -> Result<String>;
    fn run_prompt(&self, prompt: &str, session: &Session) -> Result<ExitStatus>;
    fn run_interactive(&self, session: &Session) -> Result<ExitStatus>;
}
```

Current implementations: Claude Code, Copilot.
Future: Any CLI that accepts a prompt on stdin or as an argument.

### Prompt

Assembled instructions for a worker session. Built from templates + context.

```
Prompt {
    template: PathBuf,       // Source template
    context: PromptContext,  // Variables for interpolation
    rendered: String,        // Final markdown
    metadata: PromptMetadata,// Which fragments were included, token estimate
}

PromptContext {
    task: TaskContext,        // Task name, ID, description
    issues: Vec<IssueContext>,// Current issues and their states
    worktree: WorktreeContext,// Paths and branch info
    session: SessionContext,  // Iteration number, session ID
    project: ProjectContext,  // Language, framework, conventions
    user: UserContext,        // Preferences, identity
}
```

### Channel

Bidirectional communication between orchestrator and worker.

```
Channel {
    task: TaskId,
    orchestrator_inbox: PathBuf,  // Messages TO orchestrator
    worker_inbox: PathBuf,        // Messages TO worker
    archive: PathBuf,             // Processed messages
}
```

**Why file-based IPC stays:**

- Debuggable (just `ls` and `cat`)
- Auditable (archive is permanent)
- Survives process restarts
- No daemon required
- Cross-process (tmux panes, background processes)
- Human-readable (markdown)

---

## Relationships

```
                    ┌───────────────┐
                    │    Project    │
                    │  (git repo)  │
                    └───────┬───────┘
                            │ has many
                    ┌───────▼───────┐
              ┌─────│     Task      │─────┐
              │     │  (epic/parent)│     │
              │     └───────┬───────┘     │
              │             │ has many    │
         has one    ┌───────▼───────┐    has one
              │     │    Issue      │     │
              │     │  (sub-issue)  │     │
              │     └───────────────┘     │
       ┌──────▼──────┐            ┌──────▼──────┐
       │  Worktree   │            │   Channel   │
       │ (git branch)│            │   (comms)   │
       └─────────────┘            └──────┬──────┘
                                         │
                              ┌──────────┴──────────┐
                              │                     │
                    ┌─────────▼────┐    ┌───────────▼──┐
                    │ Orchestrator │    │    Worker     │
                    │ (supervisor) │    │ (autonomous)  │
                    └──────────────┘    └───────┬───────┘
                                                │ has many
                                        ┌───────▼───────┐
                                        │   Session     │
                                        │ (one iteration│
                                        │  of the loop) │
                                        └───────────────┘
```

---

## Key Invariants

1. **One worktree per task** — isolation is non-negotiable
2. **One active worker per task** (for now — multi-worker is a future evolution)
3. **Messages are immutable once written** — append-only, archive to process
4. **Sessions are append-only** — each iteration creates a new session, never modifies old ones
5. **Linear is the source of truth for issue state** — Nancy syncs TO Linear, reads FROM Linear
6. **Git commits are the handover mechanism** — commit messages brief the next iteration
7. **The worker loop is the core primitive** — iterate, self-correct, iterate

---

## What's New in Rust Nancy (Beyond the Port)

These are entities/concepts that bash Nancy doesn't have but Rust Nancy should:

### WorkerPool

Multiple workers executing issues in parallel (where dependency graph allows).

```
WorkerPool {
    task: TaskId,
    workers: Vec<Worker>,
    max_concurrency: usize,
    strategy: SchedulingStrategy,  // Sequential | Parallel | DependencyGraph
}
```

### Event

Everything that happens is an event. Enables reactive UI, logging, and replay.

```
Event {
    id: EventId,
    timestamp: DateTime,
    task: TaskId,
    kind: EventKind,
    // Variants:
    //   WorkerStarted { session }
    //   WorkerCompleted { session, exit_reason }
    //   MessageSent { message }
    //   IssueStateChanged { issue, from, to }
    //   TokenThresholdReached { session, usage }
    //   CommitCreated { hash, message }
    //   DirectiveReceived { message }
    //   PauseRequested
    //   ReviewTriggered { session }
}
```

### EventBus

Internal pub/sub for decoupled components. The TUI, the file watcher,
the process supervisor, and the state manager all subscribe to events.

```
EventBus {
    subscribers: Vec<Box<dyn Subscriber>>,
    history: Vec<Event>,  // For replay/debugging
}
```

### Plugin / Extension

Third-party or user-defined extensions. Hooks into the event system.

```
trait Extension {
    fn name(&self) -> &str;
    fn on_event(&self, event: &Event) -> Result<()>;
    fn commands(&self) -> Vec<Command>;  // Additional CLI commands
}
```

### Review

Formal review of completed work. Can be automated (AI reviewer) or manual.

```
Review {
    id: ReviewId,
    task: TaskId,
    session: SessionId,     // Which session's work is being reviewed
    reviewer: Reviewer,     // AI | Human
    verdict: Verdict,       // Approved | ChangesRequested | Rejected
    comments: Vec<Comment>,
    criteria_results: Vec<CriterionResult>,
}
```

---

## Configuration Hierarchy

```
Defaults (compiled in)
  └─► Global config (~/.config/nancy/config.toml)
        └─► Project config (.nancy/config.toml)
              └─► Task config (.nancy/tasks/<id>/config.toml)
                    └─► CLI overrides (--flag)
```

Each level overrides the previous. TOML over JSON (better for humans to edit).

---

## Directory Structure (Rust Nancy)

```
~/.config/nancy/
├── config.toml              # Global preferences
├── drivers/                 # Custom driver configs
└── extensions/              # Installed extensions

<project>/.nancy/
├── config.toml              # Project config
├── tasks/
│   └── <task-id>/
│       ├── config.toml      # Task overrides
│       ├── issues.toml      # Issue list + state cache
│       ├── prompt.md        # Last rendered prompt
│       ├── comms/
│       │   ├── inbox/       # Pending messages (both directions)
│       │   └── archive/     # Processed messages
│       ├── sessions/
│       │   └── <session-id>.toml  # Session metadata
│       └── events/
│           └── events.jsonl # Append-only event log
└── worktrees/               # Managed by git, symlinked here
```

---

## Open Questions

1. **Should Nancy have a daemon?** Bash Nancy is stateless (reads files each time).
   Rust Nancy could run a background daemon for file watching, event processing,
   and faster CLI response times. Tradeoff: simplicity vs responsiveness.

2. **TUI vs tmux?** Bash Nancy is deeply integrated with tmux. Rust Nancy could
   either: (a) build a native TUI with ratatui, (b) keep managing tmux, or
   (c) support both. Option (c) is probably right — TUI for single-monitor,
   tmux for multi-pane workflows.

3. **Multi-worker coordination?** If two workers are running in parallel on
   different issues, how do they share the worktree? Options: separate worktrees
   per worker, or lock-based coordination on a shared worktree.

4. **How much state in Linear vs local?** Currently Linear is truth and local
   files are cache. Should Rust Nancy be able to work offline (local-first,
   sync to Linear when available)?

5. **Extension API surface?** How much should extensions be able to do?
   Just react to events? Or also modify behavior (middleware pattern)?
