# Nancy Rust Rewrite: Ecosystem Research

This document maps every concern in the current Nancy bash implementation to the best Rust crates, with Nancy-specific code examples and gotchas.

For reference, Nancy today is ~2,500 lines of bash that: spawns Claude Code CLI processes in tmux panes, manages file-based IPC (inbox/outbox markdown messages), watches filesystems with `fswatch`, queries Linear's GraphQL API with `curl`, renders prompt templates with `sed`, and manages git worktrees by shelling out.

---

## 1. CLI Framework: `clap` (derive API)

**Why clap.** It is the de facto standard -- 95%+ of Rust CLIs use it. The derive API gives you compile-time validation of your CLI structure, automatic `--help` generation, shell completions, and colored output. The builder API still exists for dynamic CLIs, but Nancy's command set is known at compile time, so derive is the right call.

**Why derive over builder.** Nancy has a fixed set of subcommands (`orchestrate`, `start`, `direct`, `pause`, `unpause`, `status`, `inbox`, `msg`, `experiment`). Derive turns these into an enum where the compiler guarantees exhaustive matching -- you cannot forget to handle a command.

```rust
use clap::{Parser, Subcommand, Args};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "nancy", version, about = "AI agent orchestration")]
pub struct Cli {
    /// Path to project root (defaults to cwd)
    #[arg(short, long, global = true)]
    pub project: Option<PathBuf>,

    /// Verbosity level (-v, -vv, -vvv)
    #[arg(short, long, action = clap::ArgAction::Count, global = true)]
    pub verbose: u8,

    #[command(subcommand)]
    pub command: Command,
}

#[derive(Subcommand)]
pub enum Command {
    /// Start orchestration for a task
    Orchestrate(OrchestrateArgs),

    /// Start a worker on a task
    Start(StartArgs),

    /// Send a directive to a running worker
    Direct(DirectArgs),

    /// Pause a running worker
    Pause { task: String },

    /// Unpause a paused worker
    Unpause { task: String },

    /// Show status of all tasks/workers
    Status,

    /// Read inbox messages for a task
    Inbox(InboxArgs),

    /// Send a message to a worker or orchestrator
    Msg(MsgArgs),

    /// Run a reproducible A/B experiment
    Experiment(ExperimentArgs),
}

#[derive(Args)]
pub struct OrchestrateArgs {
    /// Linear issue ID (e.g., ALP-123)
    pub issue: String,

    /// Skip tmux layout, run headless
    #[arg(long)]
    pub headless: bool,
}

#[derive(Args)]
pub struct StartArgs {
    /// Task name or Linear issue ID
    pub task: String,

    /// Iteration number (for context continuity)
    #[arg(short, long, default_value_t = 1)]
    pub iteration: u32,
}

#[derive(Args)]
pub struct DirectArgs {
    /// Target task
    pub task: String,

    /// Directive message
    pub message: String,

    /// Priority level
    #[arg(short, long, default_value = "normal")]
    pub priority: Priority,
}

#[derive(Args)]
pub struct InboxArgs {
    /// Task to check inbox for
    pub task: String,

    /// Role perspective (orchestrator or worker)
    #[arg(short, long, default_value = "orchestrator")]
    pub role: Role,
}

#[derive(Args)]
pub struct MsgArgs {
    /// Target task
    pub task: String,

    /// Message body
    pub body: String,
}

#[derive(Args)]
pub struct ExperimentArgs {
    /// Linear issue ID for the experiment
    pub issue: String,
}

#[derive(Clone, clap::ValueEnum)]
pub enum Priority {
    Urgent,
    Normal,
    Low,
}

#[derive(Clone, clap::ValueEnum)]
pub enum Role {
    Orchestrator,
    Worker,
}
```

Dispatch becomes a single exhaustive match:

```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Command::Orchestrate(args) => orchestrate::run(args).await,
        Command::Start(args) => start::run(args).await,
        Command::Direct(args) => direct::run(args).await,
        Command::Pause { task } => pause::run(&task).await,
        Command::Unpause { task } => unpause::run(&task).await,
        Command::Status => status::run().await,
        Command::Inbox(args) => inbox::run(args).await,
        Command::Msg(args) => msg::run(args).await,
        Command::Experiment(args) => experiment::run(args).await,
    }
}
```

**Gotchas:**

- Use `#[arg(global = true)]` for flags that apply across all subcommands (verbosity, project path).
- `clap::ValueEnum` derive gives you enum-to-string for free on args like `Priority` and `Role`.
- For shell completions, add `clap_complete` and generate them in a `completions` subcommand or build script.

---

## 2. Async Runtime: `tokio`

**Why tokio.** Nancy is fundamentally a concurrent system: it supervises multiple child processes, watches multiple file paths, relays messages between inboxes, polls Linear for state changes, and renders a TUI -- all simultaneously. Tokio is the only async runtime with mature support for all of these. Its `process`, `fs`, `sync`, and `signal` modules map directly to Nancy's needs.

`async-std` is the alternative, but it lacks `tokio::process` (the single most important module for Nancy) and has a fraction of the ecosystem integration.

**Cargo.toml:**

```toml
[dependencies]
tokio = { version = "1", features = ["full"] }
```

In production you could trim features to `rt-multi-thread`, `macros`, `process`, `fs`, `signal`, `sync`, `io-util`, `time` -- but `full` is fine during development.

**Nancy's concurrent architecture maps to tokio tasks:**

```rust
use tokio::task::JoinSet;
use tokio::signal;

pub async fn orchestrate(task_id: &str) -> anyhow::Result<()> {
    let mut tasks = JoinSet::new();

    // Spawn the worker supervisor (manages claude CLI process lifecycle)
    let tid = task_id.to_string();
    tasks.spawn(async move {
        worker::supervise(&tid).await
    });

    // Spawn the file watcher (monitors inbox directories for new messages)
    let tid = task_id.to_string();
    tasks.spawn(async move {
        watcher::watch_inboxes(&tid).await
    });

    // Spawn the message relay (forwards messages, triggers injections)
    let tid = task_id.to_string();
    tasks.spawn(async move {
        relay::run(&tid).await
    });

    // Spawn the token usage monitor
    let tid = task_id.to_string();
    tasks.spawn(async move {
        tokens::monitor(&tid).await
    });

    // Wait for shutdown signal or any task failure
    tokio::select! {
        _ = signal::ctrl_c() => {
            tracing::info!("Shutdown signal received");
        }
        Some(result) = tasks.join_next() => {
            match result {
                Ok(Ok(())) => tracing::info!("Task completed"),
                Ok(Err(e)) => tracing::error!("Task failed: {e}"),
                Err(e) => tracing::error!("Task panicked: {e}"),
            }
        }
    }

    // Abort remaining tasks on shutdown
    tasks.shutdown().await;
    Ok(())
}
```

**Gotchas:**

- Use `JoinSet` (not raw `tokio::spawn`) to track task handles and propagate errors.
- `tokio::select!` is your orchestration primitive -- it lets you race shutdown signals against task completions.
- Prefer `tokio::sync::mpsc` channels over shared mutable state for inter-task communication.
- Never block the tokio runtime with synchronous I/O. Use `tokio::task::spawn_blocking` for CPU-heavy or blocking operations (like `git2` calls).

---

## 3. Process Management

This is Nancy's core job: spawning `claude` CLI processes, feeding them prompts, capturing their output, and managing their lifecycle.

### 3a. `tokio::process::Command`

The async equivalent of `std::process::Command`. This is what you use for non-interactive claude sessions (prompt mode with `--print`).

```rust
use tokio::process::Command;
use std::process::Stdio;

pub struct WorkerProcess {
    child: tokio::process::Child,
    task_id: String,
}

impl WorkerProcess {
    pub async fn spawn(
        task_id: &str,
        prompt: &str,
        worktree_path: &std::path::Path,
    ) -> anyhow::Result<Self> {
        let session_id = format!("nancy-{task_id}");

        let child = Command::new("claude")
            .args(["--print", "--output-format", "stream-json"])
            .arg("--session-id")
            .arg(&session_id)
            .arg("--prompt")
            .arg(prompt)
            .current_dir(worktree_path)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .stdin(Stdio::null())
            // Set process group so we can kill the whole tree
            .process_group(0)
            .spawn()?;

        Ok(Self {
            child,
            task_id: task_id.to_string(),
        })
    }

    pub async fn wait_with_output(&mut self) -> anyhow::Result<std::process::Output> {
        let output = self.child.wait_with_output().await?;
        Ok(output)
    }

    pub fn kill(&mut self) -> std::io::Result<()> {
        self.child.start_kill()
    }
}
```

### 3b. Interactive sessions with `pty-process`

For interactive Claude Code sessions (the `_worker` pane in tmux), you need a PTY so the process thinks it has a terminal. `pty-process` (3M+ downloads, tokio-native) is the right crate.

```toml
[dependencies]
pty-process = { version = "0.5", features = ["async"] }
```

```rust
use pty_process::{Pty, Command as PtyCommand, Size};
use tokio::io::{AsyncReadExt, AsyncWriteExt};

pub async fn spawn_interactive_worker(
    task_id: &str,
    worktree: &std::path::Path,
) -> anyhow::Result<(Pty, tokio::process::Child)> {
    let (mut pty, pts) = pty_process::open()?;
    pty.resize(Size::new(24, 120))?;

    let mut cmd = PtyCommand::new("claude");
    cmd.arg("--session-id").arg(format!("nancy-{task_id}"));
    cmd.current_dir(worktree);

    let child = cmd.spawn(pts)?;

    // Now you can read/write to `pty` as AsyncRead/AsyncWrite
    // This is how you inject keystrokes (replacing tmux send-keys)
    Ok((pty, child))
}

/// Inject a command into a running interactive session
/// (replaces: tmux send-keys -t "$pane" "nancy inbox" Enter)
pub async fn inject_command(pty: &mut Pty, command: &str) -> anyhow::Result<()> {
    pty.write_all(command.as_bytes()).await?;
    pty.write_all(b"\n").await?;
    pty.flush().await?;
    Ok(())
}
```

### 3c. Signal handling and process groups

```rust
use nix::sys::signal::{self, Signal};
use nix::unistd::Pid;

/// Send SIGTERM to entire process group
pub fn terminate_process_group(pid: u32) -> anyhow::Result<()> {
    let pgid = Pid::from_raw(-(pid as i32)); // negative = process group
    signal::kill(pgid, Signal::SIGTERM)?;
    Ok(())
}
```

**Gotchas:**

- `.process_group(0)` on `Command` creates a new process group -- essential for clean shutdown of claude and its subprocesses.
- `pty-process` requires the `async` feature flag for tokio integration. Without it you only get blocking APIs.
- Claude's `--output-format stream-json` gives you JSONL output you can parse line-by-line for token tracking (replacing the current `tail -F | jq` approach).

---

## 4. Terminal UI

Two viable strategies: native TUI with `ratatui`, or programmatic tmux management from Rust. Here are the tradeoffs.

### Option A: `ratatui` (native TUI)

`ratatui` is the modern Rust TUI framework (successor to `tui-rs`). It gives you full control over the terminal, immediate-mode rendering, and a rich widget set. Nancy could render its entire interface -- worker output, orchestrator status, message inbox, token gauge -- in a single terminal without tmux.

```toml
[dependencies]
ratatui = "0.29"
crossterm = "0.28"
```

```rust
use ratatui::{
    layout::{Constraint, Direction, Layout},
    style::{Color, Modifier, Style},
    widgets::{Block, Borders, Gauge, List, ListItem, Paragraph},
    Frame,
};

pub struct NancyApp {
    pub task_id: String,
    pub worker_output: Vec<String>,
    pub messages: Vec<Message>,
    pub token_percent: f64,
    pub worker_status: WorkerStatus,
    pub active_pane: Pane,
}

pub enum Pane {
    Worker,
    Orchestrator,
    Messages,
}

pub fn draw(frame: &mut Frame, app: &NancyApp) {
    // Main layout: sidebar + content
    let horizontal = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Length(20), Constraint::Min(60)])
        .split(frame.area());

    let sidebar = horizontal[0];
    let content = horizontal[1];

    // Sidebar: navigation + status
    let sidebar_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),  // Title
            Constraint::Length(8),  // Navigation
            Constraint::Length(3),  // Token gauge
            Constraint::Min(0),    // Spacer
        ])
        .split(sidebar);

    // Title
    let title = Paragraph::new(format!(" {} ", app.task_id))
        .block(Block::default().borders(Borders::ALL).title("Nancy"));
    frame.render_widget(title, sidebar_layout[0]);

    // Navigation items
    let nav_items: Vec<ListItem> = vec![
        nav_item("Worker", &app.active_pane, Pane::Worker),
        nav_item("Orchestrator", &app.active_pane, Pane::Orchestrator),
        nav_item("Messages", &app.active_pane, Pane::Messages),
    ];
    let nav = List::new(nav_items)
        .block(Block::default().borders(Borders::ALL).title("Navigation"));
    frame.render_widget(nav, sidebar_layout[1]);

    // Token usage gauge
    let gauge = Gauge::default()
        .block(Block::default().borders(Borders::ALL).title("Tokens"))
        .gauge_style(token_color(app.token_percent))
        .ratio(app.token_percent / 100.0)
        .label(format!("{:.0}%", app.token_percent));
    frame.render_widget(gauge, sidebar_layout[2]);

    // Content area: render active pane
    match app.active_pane {
        Pane::Worker => render_worker(frame, content, app),
        Pane::Orchestrator => render_orchestrator(frame, content, app),
        Pane::Messages => render_messages(frame, content, app),
    }
}

fn token_color(percent: f64) -> Style {
    match percent as u32 {
        0..=49 => Style::default().fg(Color::Green),
        50..=69 => Style::default().fg(Color::Yellow),
        70..=89 => Style::default().fg(Color::Red),
        _ => Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
    }
}
```

### Option B: Programmatic tmux from Rust

Keep the tmux layout but replace bash orchestration with Rust controlling tmux via its CLI/control mode.

```rust
use tokio::process::Command;

pub struct TmuxSession {
    session_name: String,
}

impl TmuxSession {
    pub async fn create(task_id: &str) -> anyhow::Result<Self> {
        let name = format!("nancy-{task_id}");

        Command::new("tmux")
            .args(["new-session", "-d", "-s", &name, "-x", "200", "-y", "50"])
            .status()
            .await?;

        // Split into panes
        Command::new("tmux")
            .args(["split-window", "-t", &name, "-h", "-p", "80"])
            .status()
            .await?;

        Command::new("tmux")
            .args(["split-window", "-t", &format!("{name}.1"), "-v", "-p", "30"])
            .status()
            .await?;

        Ok(Self { session_name: name })
    }

    pub async fn send_keys(&self, pane: u32, keys: &str) -> anyhow::Result<()> {
        Command::new("tmux")
            .args([
                "send-keys",
                "-t",
                &format!("{}.{}", self.session_name, pane),
                keys,
                "Enter",
            ])
            .status()
            .await?;
        Ok(())
    }

    pub async fn kill(&self) -> anyhow::Result<()> {
        Command::new("tmux")
            .args(["kill-session", "-t", &self.session_name])
            .status()
            .await?;
        Ok(())
    }
}
```

### Recommendation

**Start with Option B (tmux management from Rust), migrate to Option A later.** Rationale:

1. The existing workflow uses tmux and users are accustomed to it.
2. Claude Code itself outputs to a terminal -- embedding its raw output in a ratatui widget requires a terminal emulator widget (complex).
3. Option B lets you ship the Rust rewrite faster with the same UX.
4. Option A is the long-term play -- it eliminates the tmux dependency and gives you pixel-perfect control. Build it as a second phase once the core orchestration is solid.

**Gotchas:**

- `ratatui` uses immediate-mode rendering -- you redraw the entire screen every frame. Keep your `draw()` function fast.
- If you embed process output in ratatui, you need a VT100 parser (`vt100` crate) to handle ANSI escape sequences.
- tmux control mode (`tmux -C`) gives you a machine-readable protocol instead of shelling out for every operation. Consider it for Option B.

---

## 5. File System

### 5a. `notify` for file watching

`notify` (v8.x) is the cross-platform file watcher that replaces `fswatch`. It uses FSEvents on macOS (the same backend fswatch uses) and inotify on Linux. This is Nancy's replacement for the `fswatch -0 --event Created` pipeline.

```toml
[dependencies]
notify = "8"
notify-debouncer-mini = "0.5"
```

```rust
use notify::{Config, Event, EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use tokio::sync::mpsc;
use std::path::Path;

pub struct InboxWatcher {
    _watcher: RecommendedWatcher,
    rx: mpsc::Receiver<Event>,
}

impl InboxWatcher {
    pub fn new(
        orchestrator_inbox: &Path,
        worker_inbox: &Path,
    ) -> anyhow::Result<Self> {
        let (tx, rx) = mpsc::channel(100);

        let mut watcher = RecommendedWatcher::new(
            move |result: Result<Event, notify::Error>| {
                if let Ok(event) = result {
                    // Only care about new file creation
                    if matches!(event.kind, EventKind::Create(_)) {
                        let _ = tx.blocking_send(event);
                    }
                }
            },
            Config::default(),
        )?;

        watcher.watch(orchestrator_inbox, RecursiveMode::NonRecursive)?;
        watcher.watch(worker_inbox, RecursiveMode::NonRecursive)?;

        Ok(Self { _watcher: watcher, rx })
    }

    pub async fn next_event(&mut self) -> Option<Event> {
        self.rx.recv().await
    }
}

/// Main watch loop (replaces notify::watch_comms in bash)
pub async fn watch_inboxes(task_id: &str) -> anyhow::Result<()> {
    let task_dir = task_dir(task_id);
    let orch_inbox = task_dir.join("comms/orchestrator/inbox");
    let worker_inbox = task_dir.join("comms/worker/inbox");

    let mut watcher = InboxWatcher::new(&orch_inbox, &worker_inbox)?;

    while let Some(event) = watcher.next_event().await {
        for path in &event.paths {
            if path.extension().map_or(false, |ext| ext == "md") {
                let direction = if path.starts_with(&orch_inbox) {
                    Direction::WorkerToOrchestrator
                } else {
                    Direction::OrchestratorToWorker
                };

                handle_message(task_id, path, direction).await?;
            }
        }
    }

    Ok(())
}
```

### 5b. `tokio::fs` for async file operations

```rust
use tokio::fs;

/// Write a message to a recipient's inbox (replaces comms::send)
pub async fn send_message(
    task_id: &str,
    from: Role,
    to: Role,
    msg_type: MessageType,
    body: &str,
    priority: Priority,
) -> anyhow::Result<std::path::PathBuf> {
    let inbox_dir = inbox_path(task_id, &to);
    fs::create_dir_all(&inbox_dir).await?;

    let timestamp = chrono::Utc::now().format("%Y%m%dT%H%M%SZ");
    let filename = format!("{timestamp}-001.md");
    let filepath = inbox_dir.join(&filename);

    let content = format!(
        "# Message\n\n\
         **Type:** {msg_type}\n\
         **From:** {from}\n\
         **Priority:** {priority}\n\
         **Time:** {}\n\n\
         ## Content\n\n\
         {body}\n",
        chrono::Utc::now().to_rfc3339(),
    );

    fs::write(&filepath, content).await?;
    Ok(filepath)
}
```

**Gotchas:**

- `notify`'s callback runs on its own thread, not the tokio runtime. Use `tx.blocking_send()` (not `.send().await`) to bridge into async.
- On macOS, `notify` uses FSEvents by default which has ~1s latency. For lower latency, use the `PollWatcher` with a short interval or accept the FSEvents delay (Nancy's bash version has the same latency via fswatch).
- `notify-debouncer-mini` is useful if you get duplicate events for a single file write (common on some platforms).

---

## 6. Configuration & Serialization

### `serde` + `serde_json` + `serde_yaml` + `toml`

This replaces Nancy's `config.json` parsing (currently done with `jq` in bash) and YAML-based sidecar files.

```toml
[dependencies]
serde = { version = "1", features = ["derive"] }
serde_json = "1"
serde_yaml = "0.9"
toml = "0.8"
```

```rust
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// nancy.toml -- project-level configuration
#[derive(Debug, Serialize, Deserialize)]
pub struct NancyConfig {
    pub project: ProjectConfig,
    pub linear: LinearConfig,
    pub worker: WorkerConfig,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ProjectConfig {
    /// Project name (used for Linear project matching)
    pub name: String,
    /// CLI to use: "claude" or "copilot"
    #[serde(default = "default_cli")]
    pub cli: String,
    /// Path to worktrees directory
    pub worktrees_dir: Option<PathBuf>,
}

fn default_cli() -> String { "claude".into() }

#[derive(Debug, Serialize, Deserialize)]
pub struct LinearConfig {
    /// Linear API key (or reference to env var)
    pub api_key_env: String,
    /// Team identifier
    pub team: String,
    /// Default project for issue queries
    pub project: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct WorkerConfig {
    /// Maximum concurrent workers
    #[serde(default = "default_max_workers")]
    pub max_concurrent: u32,
    /// Token usage warning threshold (percent)
    #[serde(default = "default_warn_threshold")]
    pub token_warn_threshold: u32,
    /// Token usage critical threshold (percent)
    #[serde(default = "default_critical_threshold")]
    pub token_critical_threshold: u32,
    /// Execution mode: "loop" or "single"
    #[serde(default = "default_execution_mode")]
    pub execution_mode: ExecutionMode,
}

fn default_max_workers() -> u32 { 3 }
fn default_warn_threshold() -> u32 { 50 }
fn default_critical_threshold() -> u32 { 70 }
fn default_execution_mode() -> ExecutionMode { ExecutionMode::Loop }

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ExecutionMode {
    Loop,
    Single,
}

/// Load config from nancy.toml
pub fn load_config(project_root: &std::path::Path) -> anyhow::Result<NancyConfig> {
    let config_path = project_root.join(".nancy/nancy.toml");
    let content = std::fs::read_to_string(&config_path)?;
    let config: NancyConfig = toml::from_str(&content)?;
    Ok(config)
}
```

**Message types as strongly-typed structs** (replacing the markdown parsing):

```rust
/// Parsed inbox message (replaces grep-based metadata extraction)
#[derive(Debug, Serialize, Deserialize)]
pub struct CommsMessage {
    #[serde(rename = "type")]
    pub msg_type: MessageType,
    pub from: Role,
    pub priority: Priority,
    pub time: chrono::DateTime<chrono::Utc>,
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum MessageType {
    Blocker,
    Progress,
    ReviewRequest,
    Directive,
    Guidance,
    Stop,
}
```

**Gotchas:**

- Use `#[serde(default)]` liberally for backwards-compatible config evolution.
- `#[serde(rename_all = "kebab-case")]` matches Nancy's existing message type format ("review-request").
- Consider migrating config from JSON to TOML -- it is the Rust ecosystem standard and supports comments.

---

## 7. HTTP/GraphQL Client

Nancy queries Linear's GraphQL API for issues, comments, workflow states, and status updates. Today this is `curl` piped through `jq`.

### `reqwest` for HTTP

```toml
[dependencies]
reqwest = { version = "0.12", features = ["json"] }
```

### `cynic` for typed GraphQL (recommended over `graphql-client`)

**Why cynic over graphql-client.** Both generate Rust types from a GraphQL schema, but cynic takes a "bring your own types" approach -- you define Rust structs and cynic generates the GraphQL query from them. This is better for Nancy because:

1. You control the struct shape, so your types can directly model Nancy's domain (issues, comments, states).
2. Cynic is actively maintained (v3.12, August 2025) with 100K+ monthly downloads.
3. `graphql-client` generates types from `.graphql` files -- viable but more codegen overhead.

```toml
[dependencies]
cynic = "3"

[build-dependencies]
cynic-codegen = "3"
```

First, register the Linear schema (one-time setup):

```rust
// build.rs
fn main() {
    cynic_codegen::register_schema("linear")
        .from_sdl_file("schemas/linear.graphql")
        .unwrap()
        .as_default()
        .unwrap();
}
```

Then define your query types:

```rust
#[cynic::schema("linear")]
mod schema {}

/// Fetch a single issue by ID
#[derive(cynic::QueryVariables)]
pub struct IssueQueryVariables {
    pub id: String,
}

#[derive(cynic::QueryFragment, Debug)]
#[cynic(graphql_type = "Query", variables = "IssueQueryVariables")]
pub struct IssueQuery {
    #[arguments(id: $id)]
    pub issue: Issue,
}

#[derive(cynic::QueryFragment, Debug)]
pub struct Issue {
    pub id: cynic::Id,
    pub identifier: String,
    pub title: String,
    pub description: Option<String>,
    pub state: WorkflowState,
    pub assignee: Option<User>,
    pub children: IssueConnection,
}

#[derive(cynic::QueryFragment, Debug)]
pub struct WorkflowState {
    pub id: cynic::Id,
    pub name: String,
}

#[derive(cynic::QueryFragment, Debug)]
pub struct User {
    pub name: String,
    pub email: String,
}

#[derive(cynic::QueryFragment, Debug)]
pub struct IssueConnection {
    pub nodes: Vec<ChildIssue>,
}

#[derive(cynic::QueryFragment, Debug)]
#[cynic(graphql_type = "Issue")]
pub struct ChildIssue {
    pub id: cynic::Id,
    pub identifier: String,
    pub title: String,
    pub state: WorkflowState,
}
```

The client:

```rust
pub struct LinearClient {
    http: reqwest::Client,
    api_key: String,
}

impl LinearClient {
    pub fn new(api_key: String) -> Self {
        Self {
            http: reqwest::Client::new(),
            api_key,
        }
    }

    pub async fn get_issue(&self, issue_id: &str) -> anyhow::Result<Issue> {
        use cynic::QueryBuilder;

        let query = IssueQuery::build(IssueQueryVariables {
            id: issue_id.to_string(),
        });

        let response = self
            .http
            .post("https://api.linear.app/graphql")
            .header("Authorization", &self.api_key)
            .header("Content-Type", "application/json")
            .json(&query)
            .send()
            .await?
            .json::<cynic::GraphQlResponse<IssueQuery>>()
            .await?;

        match response.data {
            Some(data) => Ok(data.issue),
            None => anyhow::bail!("No data returned. Errors: {:?}", response.errors),
        }
    }

    pub async fn add_comment(
        &self,
        issue_id: &str,
        body: &str,
    ) -> anyhow::Result<()> {
        // Similar pattern with a mutation type
        todo!()
    }
}
```

**Gotchas:**

- Download Linear's schema SDL once: `curl -H "Authorization: Bearer $TOKEN" https://api.linear.app/graphql` with an introspection query, or get it from Linear's docs.
- cynic's `QueryFragment` derive validates your struct fields against the schema at compile time. A typo in a field name is a compile error, not a runtime surprise.
- For mutations (adding comments, updating status), use `#[derive(cynic::QueryFragment)]` with `graphql_type = "Mutation"`.

---

## 8. Template Engine: `minijinja`

Nancy uses templates for rendering worker prompts (`PROMPT.md.template` with `{{TASK_NAME}}` variables). Today this is `sed` substitution.

**Why minijinja over tera.** Both implement Jinja2 syntax. MiniJinja wins for Nancy because:

1. Minimal dependencies (compiles faster, smaller binary).
2. Created by Armin Ronacher (Jinja2's original author) -- it is the most faithful Jinja2 implementation.
3. 10x performance over tera in benchmarks.
4. Supports template inheritance (`{% extends %}`) which is useful for composable prompts.
5. More actively maintained (activity score 8.9 vs tera's 4.6).

```toml
[dependencies]
minijinja = { version = "2", features = ["loader"] }
```

```rust
use minijinja::{Environment, context};

pub struct PromptRenderer {
    env: Environment<'static>,
}

impl PromptRenderer {
    pub fn new(templates_dir: &std::path::Path) -> anyhow::Result<Self> {
        let mut env = Environment::new();

        // Load templates from disk with auto-reload support
        let dir = templates_dir.to_path_buf();
        env.set_loader(move |name| {
            let path = dir.join(name);
            match std::fs::read_to_string(&path) {
                Ok(content) => Ok(Some(content)),
                Err(_) => Ok(None),
            }
        });

        Ok(Self { env })
    }

    /// Render a worker prompt template
    pub fn render_worker_prompt(
        &self,
        task_name: &str,
        issue_title: &str,
        issue_description: &str,
        branch_name: &str,
    ) -> anyhow::Result<String> {
        let template = self.env.get_template("PROMPT.md.template")?;

        let result = template.render(context! {
            TASK_NAME => task_name,
            ISSUE_TITLE => issue_title,
            ISSUE_DESCRIPTION => issue_description,
            BRANCH_NAME => branch_name,
            TIMESTAMP => chrono::Utc::now().to_rfc3339(),
        })?;

        Ok(result)
    }

    /// Render the sidecar navigation prompt
    pub fn render_sidecar_nav(
        &self,
        task_name: &str,
        inbox_path: &str,
        outbox_path: &str,
    ) -> anyhow::Result<String> {
        let template = self.env.get_template("sidecar-nav.md.template")?;

        let result = template.render(context! {
            TASK_NAME => task_name,
            INBOX_PATH => inbox_path,
            OUTBOX_PATH => outbox_path,
        })?;

        Ok(result)
    }
}
```

Template file (`templates/PROMPT.md.template`):

```jinja
# Task: {{ TASK_NAME }}

## Issue: {{ ISSUE_TITLE }}

{{ ISSUE_DESCRIPTION }}

## Working Branch

`{{ BRANCH_NAME }}`

## Instructions

You are an autonomous AI coding agent. Complete the task described above.

{% if CONSTRAINTS %}
## Constraints
{% for constraint in CONSTRAINTS %}
- {{ constraint }}
{% endfor %}
{% endif %}

Generated: {{ TIMESTAMP }}
```

**Gotchas:**

- MiniJinja's `context!` macro gives you type-safe template variable passing.
- Use the `loader` feature for loading templates from disk at runtime (essential for user-customizable prompts).
- Template syntax errors give clear error messages with line numbers -- a massive improvement over `sed` failures.

---

## 9. Git Integration

Nancy manages git worktrees for task isolation. Each worker gets its own worktree so changes do not interfere.

### `git2` vs shelling out to `git`

| Concern                     | `git2` (libgit2)                           | Shell out to `git`        |
| --------------------------- | ------------------------------------------ | ------------------------- |
| Worktree create/list/remove | Supported (v0.20)                          | Full support              |
| Branch operations           | Full support                               | Full support              |
| Compile time                | Adds ~30s (compiles libgit2 from C source) | Zero overhead             |
| Error handling              | Typed `git2::Error`                        | Parse stderr strings      |
| Async compatibility         | Blocking (must use `spawn_blocking`)       | `tokio::process::Command` |
| Dependency weight           | ~2MB compiled, requires cmake/pkg-config   | Requires git on PATH      |

**Recommendation: Hybrid approach.** Use `git2` for read operations (listing worktrees, checking branch status) where typed APIs pay off, and shell out for mutations (creating worktrees) where git CLI is simpler and well-tested.

```rust
use git2::Repository;

pub struct GitManager {
    repo: Repository,
}

impl GitManager {
    pub fn open(project_root: &std::path::Path) -> anyhow::Result<Self> {
        let repo = Repository::open(project_root)?;
        Ok(Self { repo })
    }

    /// List existing worktrees
    pub fn list_worktrees(&self) -> anyhow::Result<Vec<String>> {
        let worktrees = self.repo.worktrees()?;
        Ok(worktrees.iter().filter_map(|w| w.map(String::from)).collect())
    }

    /// Check if a branch exists
    pub fn branch_exists(&self, name: &str) -> bool {
        self.repo.find_branch(name, git2::BranchType::Local).is_ok()
    }

    /// Get current branch name
    pub fn current_branch(&self) -> anyhow::Result<String> {
        let head = self.repo.head()?;
        let name = head.shorthand().unwrap_or("HEAD");
        Ok(name.to_string())
    }
}

/// Shell out for worktree creation (more reliable than git2 for this)
pub async fn create_worktree(
    project_root: &std::path::Path,
    worktree_name: &str,
    branch: &str,
    worktrees_dir: &std::path::Path,
) -> anyhow::Result<std::path::PathBuf> {
    use tokio::process::Command;

    let worktree_path = worktrees_dir.join(worktree_name);

    // Create branch if it doesn't exist
    Command::new("git")
        .args(["branch", branch, "main"])
        .current_dir(project_root)
        .status()
        .await?;

    // Create worktree
    Command::new("git")
        .args(["worktree", "add"])
        .arg(&worktree_path)
        .arg(branch)
        .current_dir(project_root)
        .status()
        .await?;

    Ok(worktree_path)
}

/// Clean up worktree after task completion
pub async fn remove_worktree(
    project_root: &std::path::Path,
    worktree_path: &std::path::Path,
) -> anyhow::Result<()> {
    use tokio::process::Command;

    Command::new("git")
        .args(["worktree", "remove", "--force"])
        .arg(worktree_path)
        .current_dir(project_root)
        .status()
        .await?;

    Ok(())
}
```

**Gotchas:**

- `git2` calls are blocking. Always wrap them in `tokio::task::spawn_blocking` if called from async context.
- `git2` requires `cmake` and a C compiler to build. The `vendored` feature bundles libgit2 source to avoid system dependency issues.
- An alternative is `gitoxide` (`gix` crate) -- a pure Rust git implementation. It is newer and faster but has less mature worktree support. Worth watching.

---

## 10. State Machine

Nancy tracks task lifecycle (Todo -> InProgress -> Review -> Done) and message types. Rust's enums with pattern matching are the natural replacement for bash string comparisons.

### Enums + `strum`

```toml
[dependencies]
strum = { version = "0.26", features = ["derive"] }
```

```rust
use strum::{Display, EnumString, EnumIter};

/// Task lifecycle states (maps to Linear workflow states)
#[derive(Debug, Clone, PartialEq, Eq, Display, EnumString, EnumIter)]
pub enum TaskState {
    #[strum(serialize = "Todo")]
    Todo,
    #[strum(serialize = "In Progress")]
    InProgress,
    #[strum(serialize = "In Review")]
    InReview,
    #[strum(serialize = "Done")]
    Done,
    #[strum(serialize = "Cancelled")]
    Cancelled,
}

impl TaskState {
    /// Valid transitions from this state
    pub fn valid_transitions(&self) -> &[TaskState] {
        match self {
            TaskState::Todo => &[TaskState::InProgress, TaskState::Cancelled],
            TaskState::InProgress => &[TaskState::InReview, TaskState::Todo, TaskState::Cancelled],
            TaskState::InReview => &[TaskState::Done, TaskState::InProgress],
            TaskState::Done => &[],
            TaskState::Cancelled => &[TaskState::Todo],
        }
    }

    pub fn can_transition_to(&self, target: &TaskState) -> bool {
        self.valid_transitions().contains(target)
    }
}

/// Worker process states
#[derive(Debug, Clone, PartialEq, Eq, Display)]
pub enum WorkerStatus {
    Starting,
    Running { pid: u32, iteration: u32 },
    Paused { pid: u32 },
    Stopping,
    Stopped { exit_code: Option<i32> },
    Failed { error: String },
}

/// Message types with role validation baked into the type system
#[derive(Debug, Clone)]
pub enum WorkerMessage {
    Blocker { description: String },
    Progress { summary: String },
    ReviewRequest { pr_url: String },
}

#[derive(Debug, Clone)]
pub enum OrchestratorMessage {
    Directive { content: String, priority: Priority },
    Guidance { content: String },
    Stop { reason: String },
}

// The compiler prevents you from sending a WorkerMessage as an orchestrator
// or vice versa -- this replaces the bash comms::_validate_type function.
```

### Type-state pattern for task lifecycle

For critical state transitions, you can use Rust's type system to make invalid states unrepresentable:

```rust
pub struct Task<S: TaskPhase> {
    id: String,
    issue_id: String,
    _state: std::marker::PhantomData<S>,
}

pub struct Pending;
pub struct Active;
pub struct Reviewing;
pub struct Complete;

pub trait TaskPhase {}
impl TaskPhase for Pending {}
impl TaskPhase for Active {}
impl TaskPhase for Reviewing {}
impl TaskPhase for Complete {}

impl Task<Pending> {
    pub fn start(self, worker_pid: u32) -> Task<Active> {
        Task { id: self.id, issue_id: self.issue_id, _state: std::marker::PhantomData }
    }
}

impl Task<Active> {
    pub fn submit_for_review(self) -> Task<Reviewing> {
        Task { id: self.id, issue_id: self.issue_id, _state: std::marker::PhantomData }
    }
}

impl Task<Reviewing> {
    pub fn approve(self) -> Task<Complete> {
        Task { id: self.id, issue_id: self.issue_id, _state: std::marker::PhantomData }
    }

    pub fn request_changes(self) -> Task<Active> {
        Task { id: self.id, issue_id: self.issue_id, _state: std::marker::PhantomData }
    }
}
```

**Gotchas:**

- `strum`'s `EnumString` derive gives you `"In Progress".parse::<TaskState>()` for free -- essential for parsing Linear state names.
- The type-state pattern is powerful but adds complexity. Use it for the task lifecycle (where invalid transitions are dangerous) but use regular enums for simpler state like message types.
- `strum::EnumIter` lets you iterate all variants, useful for status displays.

---

## 11. Error Handling

### `thiserror` for domain errors, `anyhow` for the application, `color-eyre` for pretty CLI output

```toml
[dependencies]
thiserror = "2"
anyhow = "1"
color-eyre = "0.6"
```

**Use `thiserror` in library code** (the core logic):

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum NancyError {
    #[error("Task '{0}' not found")]
    TaskNotFound(String),

    #[error("Worker process failed with exit code {exit_code}: {stderr}")]
    WorkerFailed { exit_code: i32, stderr: String },

    #[error("Invalid state transition: {from} -> {to}")]
    InvalidTransition { from: TaskState, to: TaskState },

    #[error("Linear API error: {0}")]
    LinearApi(String),

    #[error("Config error: {0}")]
    Config(#[from] toml::de::Error),

    #[error("Template error: {0}")]
    Template(#[from] minijinja::Error),

    #[error("Git error: {0}")]
    Git(#[from] git2::Error),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Message validation failed: {0}")]
    InvalidMessage(String),

    #[error("Comms directory not initialized for task '{0}'")]
    CommsNotInitialized(String),
}
```

**Use `anyhow` in command handlers** (the CLI layer):

```rust
use anyhow::{Context, Result};

pub async fn run_start(args: StartArgs) -> Result<()> {
    let config = load_config(&project_root())
        .context("Failed to load nancy.toml")?;

    let issue = linear_client()
        .get_issue(&args.task)
        .await
        .context("Failed to fetch Linear issue")?;

    let worktree = create_worktree(&args.task, &issue.identifier)
        .await
        .context("Failed to create git worktree")?;

    let prompt = render_prompt(&issue)
        .context("Failed to render worker prompt")?;

    let worker = WorkerProcess::spawn(&args.task, &prompt, &worktree)
        .await
        .context("Failed to spawn worker process")?;

    Ok(())
}
```

**Use `color-eyre` for the top-level error display:**

```rust
fn main() -> color_eyre::Result<()> {
    color_eyre::install()?;
    // ... rest of main
    Ok(())
}
```

**Gotchas:**

- `thiserror` v2 (released late 2024) supports `#[error(transparent)]` and works with `anyhow` seamlessly.
- The rule: `thiserror` where you define error types, `anyhow` where you propagate them. They compose perfectly.
- `color-eyre` gives you backtraces, span traces (integrates with `tracing`), and colored error output -- exactly what you want for CLI UX.
- `anyhow::Context` is your best friend. `.context("what I was trying to do")` turns cryptic IO errors into actionable messages.

---

## 12. Logging & Tracing

### `tracing` + `tracing-subscriber`

`tracing` is the Rust ecosystem standard for structured, span-based logging. It was built by the tokio team specifically for async systems -- which is exactly what Nancy is.

```toml
[dependencies]
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }
tracing-appender = "0.2"
```

```rust
use tracing::{info, warn, error, debug, instrument, Span};
use tracing_subscriber::{fmt, prelude::*, EnvFilter};

pub fn init_tracing(verbose: u8) -> anyhow::Result<()> {
    let filter = match verbose {
        0 => "nancy=info",
        1 => "nancy=debug",
        2 => "nancy=trace",
        _ => "trace",
    };

    tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| filter.into()))
        .with(fmt::layer().with_target(true).with_thread_ids(false))
        .init();

    Ok(())
}

/// Worker supervision with span-based tracing
#[instrument(skip(config), fields(task_id = %task_id, iteration = %iteration))]
pub async fn supervise_worker(
    task_id: &str,
    iteration: u32,
    config: &WorkerConfig,
) -> anyhow::Result<()> {
    info!("Starting worker supervision");

    let worker = WorkerProcess::spawn(task_id, &prompt, &worktree).await?;
    info!(pid = worker.pid(), "Worker process spawned");

    match worker.wait().await {
        Ok(status) if status.success() => {
            info!("Worker completed successfully");
        }
        Ok(status) => {
            warn!(exit_code = ?status.code(), "Worker exited with non-zero status");
        }
        Err(e) => {
            error!(error = %e, "Worker process failed");
        }
    }

    Ok(())
}

/// Message relay with structured fields
#[instrument(skip(message_body), fields(direction = %direction))]
pub async fn relay_message(
    task_id: &str,
    direction: Direction,
    msg_type: &str,
    message_body: &str,
) -> anyhow::Result<()> {
    debug!(msg_type, body_len = message_body.len(), "Relaying message");
    // ...
    Ok(())
}
```

For per-task log files (replacing `$NANCY_TASK_DIR/$task/logs/`):

```rust
use tracing_appender::non_blocking;
use tracing_appender::rolling;

pub fn init_task_logging(task_id: &str, log_dir: &std::path::Path) -> anyhow::Result<()> {
    let file_appender = rolling::daily(log_dir, format!("nancy-{task_id}"));
    let (non_blocking_writer, _guard) = non_blocking(file_appender);

    tracing_subscriber::registry()
        .with(EnvFilter::new("nancy=debug"))
        .with(
            fmt::layer()
                .json()
                .with_writer(non_blocking_writer)
        )
        .with(
            fmt::layer()
                .with_target(false)
                .with_writer(std::io::stderr)
        )
        .init();

    Ok(())
}
```

**Gotchas:**

- `#[instrument]` auto-creates a span for any function. Use `skip(large_arg)` to avoid logging large values.
- The `_guard` from `non_blocking()` must be held for the lifetime of the program. Drop it and you lose buffered logs.
- `EnvFilter` respects `RUST_LOG` env var, so `RUST_LOG=nancy::comms=trace` lets you debug just the comms module.
- For JSON log output (machine-parseable, like the current JSONL session logs), use `.json()` on the fmt layer.

---

## 13. Testing

### Async tests with `tokio::test`

```toml
[dev-dependencies]
tokio = { version = "1", features = ["test-util", "macros"] }
assert_cmd = "2"
predicates = "3"
tempfile = "3"
assert_fs = "1"
```

**Unit tests:**

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[tokio::test]
    async fn test_send_message_creates_file() {
        let tmp = TempDir::new().unwrap();
        let task_dir = tmp.path().join("tasks/test-task");

        send_message(
            &task_dir,
            Role::Orchestrator,
            Role::Worker,
            MessageType::Directive,
            "Please run the tests",
            Priority::Normal,
        )
        .await
        .unwrap();

        // Verify message file was created in worker inbox
        let inbox = task_dir.join("comms/worker/inbox");
        let entries: Vec<_> = std::fs::read_dir(&inbox)
            .unwrap()
            .collect();
        assert_eq!(entries.len(), 1);

        let content = std::fs::read_to_string(entries[0].as_ref().unwrap().path()).unwrap();
        assert!(content.contains("**Type:** directive"));
        assert!(content.contains("Please run the tests"));
    }

    #[tokio::test]
    async fn test_inbox_watcher_detects_new_message() {
        let tmp = TempDir::new().unwrap();
        let orch_inbox = tmp.path().join("comms/orchestrator/inbox");
        let worker_inbox = tmp.path().join("comms/worker/inbox");
        std::fs::create_dir_all(&orch_inbox).unwrap();
        std::fs::create_dir_all(&worker_inbox).unwrap();

        let mut watcher = InboxWatcher::new(&orch_inbox, &worker_inbox).unwrap();

        // Write a message file
        let msg_path = orch_inbox.join("20240101T000000Z-001.md");
        tokio::fs::write(&msg_path, "# Test message").await.unwrap();

        // Watcher should detect it
        let event = tokio::time::timeout(
            std::time::Duration::from_secs(5),
            watcher.next_event(),
        )
        .await
        .unwrap()
        .unwrap();

        assert!(event.paths.iter().any(|p| p.ends_with("001.md")));
    }

    #[test]
    fn test_task_state_transitions() {
        let state = TaskState::Todo;
        assert!(state.can_transition_to(&TaskState::InProgress));
        assert!(!state.can_transition_to(&TaskState::Done));

        let state = TaskState::InProgress;
        assert!(state.can_transition_to(&TaskState::InReview));
        assert!(!state.can_transition_to(&TaskState::Done));
    }

    #[test]
    fn test_config_deserialization() {
        let toml = r#"
            [project]
            name = "my-project"
            cli = "claude"

            [linear]
            api_key_env = "LINEAR_API_KEY"
            team = "ENG"

            [worker]
            max_concurrent = 2
            token_warn_threshold = 50
        "#;

        let config: NancyConfig = toml::from_str(toml).unwrap();
        assert_eq!(config.project.name, "my-project");
        assert_eq!(config.worker.max_concurrent, 2);
        // Default values should be populated
        assert_eq!(config.worker.token_critical_threshold, 70);
    }

    #[test]
    fn test_message_type_parsing() {
        let msg_type: MessageType = serde_json::from_str("\"review-request\"").unwrap();
        assert!(matches!(msg_type, MessageType::ReviewRequest));
    }
}
```

**CLI integration tests with `assert_cmd`:**

```rust
#[cfg(test)]
mod integration {
    use assert_cmd::Command;
    use predicates::prelude::*;

    #[test]
    fn test_version_flag() {
        Command::cargo_bin("nancy")
            .unwrap()
            .arg("--version")
            .assert()
            .success()
            .stdout(predicate::str::contains("nancy"));
    }

    #[test]
    fn test_status_no_config() {
        let tmp = tempfile::TempDir::new().unwrap();

        Command::cargo_bin("nancy")
            .unwrap()
            .arg("status")
            .current_dir(tmp.path())
            .assert()
            .failure()
            .stderr(predicate::str::contains("nancy.toml"));
    }

    #[test]
    fn test_help_shows_all_subcommands() {
        Command::cargo_bin("nancy")
            .unwrap()
            .arg("--help")
            .assert()
            .success()
            .stdout(predicate::str::contains("orchestrate"))
            .stdout(predicate::str::contains("start"))
            .stdout(predicate::str::contains("direct"))
            .stdout(predicate::str::contains("status"))
            .stdout(predicate::str::contains("inbox"))
            .stdout(predicate::str::contains("msg"));
    }
}
```

**Gotchas:**

- `#[tokio::test]` spins up a single-threaded runtime by default. For tests that spawn tasks, use `#[tokio::test(flavor = "multi_thread")]`.
- `tempfile::TempDir` auto-deletes on drop. Hold the variable for the test's lifetime.
- `assert_cmd` requires the binary name in `Cargo.toml` (`[[bin]] name = "nancy"`).
- For testing file watchers, add a small delay after file creation -- filesystem events are not instantaneous.
- `tokio::time::timeout` prevents tests from hanging if a watcher fails to fire.

---

## Cargo.toml Summary

Here is the consolidated dependency set:

```toml
[package]
name = "nancy"
version = "3.0.0"
edition = "2024"
description = "AI agent orchestration for autonomous coding"

[[bin]]
name = "nancy"
path = "src/main.rs"

[dependencies]
# CLI
clap = { version = "4", features = ["derive"] }

# Async
tokio = { version = "1", features = ["full"] }

# Serialization
serde = { version = "1", features = ["derive"] }
serde_json = "1"
serde_yaml = "0.9"
toml = "0.8"

# HTTP / GraphQL
reqwest = { version = "0.12", features = ["json"] }
cynic = "3"

# File watching
notify = "8"

# Template engine
minijinja = { version = "2", features = ["loader"] }

# Git
git2 = { version = "0.20", features = ["vendored"] }

# State / enums
strum = { version = "0.26", features = ["derive"] }

# Error handling
thiserror = "2"
anyhow = "1"
color-eyre = "0.6"

# Logging
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }
tracing-appender = "0.2"

# PTY (for interactive sessions)
pty-process = { version = "0.5", features = ["async"] }

# TUI (phase 2)
# ratatui = "0.29"
# crossterm = "0.28"

# Time
chrono = { version = "0.4", features = ["serde"] }

# Signal handling
nix = { version = "0.29", features = ["signal", "process"] }

[build-dependencies]
cynic-codegen = "3"

[dev-dependencies]
tokio = { version = "1", features = ["test-util", "macros"] }
assert_cmd = "2"
predicates = "3"
tempfile = "3"
assert_fs = "1"
```

---

## Architecture Mapping: Bash to Rust

| Bash Module                            | Rust Crate(s)                    | Key Improvement                                    |
| -------------------------------------- | -------------------------------- | -------------------------------------------------- |
| `src/cli/dispatch.sh` (case statement) | `clap` derive enum               | Exhaustive matching, compile-time validation       |
| `src/comms/comms.sh` (file IPC)        | `tokio::fs` + `notify` + `serde` | Typed messages, async file ops, real-time watching |
| `src/notify/watcher.sh` (fswatch)      | `notify` crate                   | No external dependency, cross-platform, debouncing |
| `src/linear/issue.sh` (curl + jq)      | `reqwest` + `cynic`              | Typed queries, compile-time schema validation      |
| `src/task/task.sh` (mkdir/find)        | `tokio::fs` + state enums        | Type-safe state machine, async operations          |
| `src/config/config.sh` (jq)            | `serde` + `toml`                 | Strongly typed config, defaults, validation        |
| `src/ui/sidebar.sh` (gum + tmux)       | `ratatui` or tmux via `Command`  | Unified UI, no gum dependency                      |
| `src/cli/drivers/claude.sh`            | `tokio::process` + `pty-process` | Async process management, PTY support              |
| `templates/*.template` (sed)           | `minijinja`                      | Jinja2 syntax, conditionals, includes, inheritance |
| `src/lib/log.sh` (echo)                | `tracing`                        | Structured spans, per-task logs, JSON output       |
| Git worktrees (git CLI)                | `git2` + `Command`               | Typed API for reads, reliable CLI for writes       |
