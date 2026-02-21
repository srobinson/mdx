# Nancy Architecture: The Platform

> Synthesis of research docs 01-07 into a unified architecture.
> This is the blueprint for Nancy v3 — a K8s-native AI agent orchestration platform.

---

## What Nancy Becomes

Nancy v1/v2 was a bash script that managed a single Claude Code process in a tmux
pane. Nancy v3 is a **Kubernetes-native platform** that orchestrates autonomous
coding agents at scale.

The core identity doesn't change: Nancy is supervisory control, not autopilot.
She doesn't write code — she manages the things that write code.

What changes is the substrate. Instead of bash functions, tmux panes, and PID files,
Nancy v3 uses:

- **K8s CRDs** for state (not files on disk)
- **Pods** for worker isolation (not tmux panes)
- **Reconciliation loops** for lifecycle management (not bash if/then/else)
- **gRPC** for real-time communication (not file watchers)
- **A Rust agent loop** for LLM interaction (not shelling out to `claude -p`)
- **OpenAI-compatible API gateway** for model routing (not hardcoded providers)

The result: Nancy can run one agent on your laptop or fifty across a cluster,
with the same codebase, the same CLI, the same mental model.

---

## Design Principles

1. **K8s-first, not K8s-only.** Production runs on Kubernetes. Development runs
   as local processes. The Runtime trait abstracts this. `cargo run` always works.

2. **Nancy owns the agent loop.** No dependency on Claude Code CLI or any specific
   AI SDK. Nancy calls LLM APIs directly via HTTP, manages context windows, executes
   tools, tracks tokens. Multi-model from day one.

3. **File-based IPC survives.** The agent (Claude, GPT, whatever) still reads markdown
   from an inbox and writes to an outbox. The relay sidecar bridges this to gRPC.
   Debuggability is non-negotiable.

4. **Linear is issue truth, K8s is execution truth.** Linear owns what work needs
   doing. K8s owns how that work is being executed. Nancy syncs between them.

5. **The loop is the primitive.** Workers iterate: read context → execute → commit →
   report → exit when depleted. Each iteration is a Session. Self-correction emerges
   from the loop + git history.

6. **Single binary, multiple modes.** One Rust binary: `nancy serve` (control plane),
   `nancy api` (API server), `nancy gateway` (model proxy), `nancy cli` (client),
   `nancy worker` (agent process). Feature flags control what's compiled in.

---

## System Architecture

```
                                    ┌──────────────┐
                                    │   Linear     │
                                    │  (issue SoT) │
                                    └──────┬───────┘
                                           │ webhook + poll
┌──────────────────────────────────────────┼──────────────────────────────┐
│  Nancy Platform                          │                              │
│                                          │                              │
│  ┌───────────────────────────────────────▼───────────────────────────┐  │
│  │                    Control Plane                                   │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐               │  │
│  │  │    Task      │ │   Worker     │ │   Session    │               │  │
│  │  │ Controller   │ │  Controller  │ │  Controller  │               │  │
│  │  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘               │  │
│  │         └────────────────┼────────────────┘                       │  │
│  │                   ┌──────▼──────┐                                 │  │
│  │                   │  kube-rs    │  (reconciliation engine)        │  │
│  │                   │  runtime    │                                 │  │
│  │                   └─────────────┘                                 │  │
│  │  ┌─────────────┐ ┌──────────────┐                                │  │
│  │  │  gRPC Hub    │ │ Linear Sync  │                                │  │
│  │  │ (tonic)      │ │ (reqwest)    │                                │  │
│  │  └──────┬───────┘ └──────────────┘                                │  │
│  └─────────┼─────────────────────────────────────────────────────────┘  │
│            │                                                            │
│  ┌─────────▼─────────────────────────────────────────────────────────┐  │
│  │                      API Server (axum)                             │  │
│  │  REST + WebSocket — for CLI clients, Web UI, integrations         │  │
│  │  CRUDs Nancy CRDs via K8s API                                     │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Model Gateway (optional)                        │  │
│  │  OpenAI-compatible API — routes to Anthropic, OpenAI, Ollama      │  │
│  │  Provider adapters | Routing | Health tracking | Cost metering     │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Worker Pods (dynamic)                           │  │
│  │                                                                    │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐                             │  │
│  │  │Worker 1 │ │Worker 2 │ │Worker N │                             │  │
│  │  │ agent   │ │ agent   │ │ agent   │                             │  │
│  │  │ relay   │ │ relay   │ │ relay   │                             │  │
│  │  │ watchdog│ │ watchdog│ │ watchdog│                             │  │
│  │  │ git-sync│ │ git-sync│ │ git-sync│                             │  │
│  │  └─────────┘ └─────────┘ └─────────┘                             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────┐                                                           │
│  │  CLI    │  nancy task create | nancy status | nancy direct "..."   │
│  └─────────┘                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Components

**Control Plane** — The brain. A Rust binary running kube-rs controllers that
watch Nancy CRDs and reconcile desired vs actual state. Creates/destroys worker
pods, syncs with Linear, relays messages between orchestrators and workers.
Deployed as a K8s Deployment (1 replica, HA-capable with leader election).

**API Server** — The interface. An axum HTTP server that exposes Nancy's
functionality via REST + WebSocket. CLI clients, web dashboards, and CI/CD
integrations talk to this. It CRUDs Nancy CRDs via the K8s API — the control
plane picks up changes through its watchers. Deployed as a separate Deployment
behind an Ingress.

**Model Gateway** — The proxy. An OpenAI-compatible API server that routes LLM
requests to the best provider/deployment. Implements the LiteLLM adapter pattern
in Rust: provider detection, request/response transformation, health tracking
with cooldowns, cost metering, fallback chains. Optional — workers can also call
provider APIs directly. Deployed as a Deployment + Service.

**Worker Pods** — The hands. Each worker pod runs:

- `nancy-agent`: The Rust agent loop. Calls LLM APIs, executes tools (file ops,
  git, bash), reads/writes to inbox/outbox directories.
- `nancy-relay`: Sidecar. Bridges file-based IPC to gRPC. Watches outbox for
  agent messages, writes incoming messages to inbox.
- `nancy-watchdog`: Sidecar. Monitors agent health (heartbeat), tracks token
  usage, enforces budgets, exports Prometheus metrics.
- `nancy-git-sync`: Sidecar. Watches for git commits, pushes to remote on
  schedule, reports changed files.

Created dynamically by the Worker Controller. Destroyed when task completes.
Uses K8s native sidecars (restartable init containers, stable in K8s 1.33+).

**CLI** — The remote control. Thin client that talks to the API Server.
`nancy task create`, `nancy status`, `nancy direct "fix the tests"`,
`nancy pause`, `nancy logs`. Also supports a TUI mode via ratatui for
interactive monitoring.

---

## Data Model (K8s CRDs)

Five Custom Resource Definitions, all in the `nancy.dev` API group:

### NancyTask (namespaced)

The top-level unit of work. Maps 1:1 to a Linear parent issue.

```
NancyTask "alp-198"
  spec:
    linearId: "ALP-198"
    name: "Implement auth middleware"
    issues: [{id: "ALP-199", title: "JWT validation"}, ...]
    repoUrl: "git@github.com:org/repo.git"
    baseBranch: "main"
    driverRef: "claude-sonnet"
    tokenBudget: 500000
  status:
    state: Running | Created | Provisioning | Paused | Completed | Reviewed | Failed
    issueCount: 5
    issuesCompleted: 2
    currentWorker: "alp-198-worker-1"
    totalTokensUsed: 123456
```

**Owns**: NancyWorker(s) — K8s garbage collection cascades deletion.

### NancyWorker (namespaced)

A running agent process. Maps to a Pod.

```
NancyWorker "alp-198-worker-1"
  spec:
    taskRef: "alp-198"
    driverRef: "claude-sonnet"
    image: "ghcr.io/nancy/agent:latest"
    resources: {cpu: "2", memory: "2Gi"}
    sidecars: {relay: enabled, watchdog: enabled, gitSync: enabled}
  status:
    state: Running | Pending | Starting | Stalled | Paused | Completed | Failed
    podName: "alp-198-worker-1-xyz"
    tokensUsed: 45000
    currentIssue: "ALP-199"
    lastHeartbeat: "2026-02-14T10:30:00Z"
```

**Owns**: NancySession(s), NancyChannel, Pod.

### NancySession (namespaced)

A single iteration of the agent loop. Immutable audit trail.

```
NancySession "session-abc123"
  spec:
    workerRef: "alp-198-worker-1"
    issueRef: {id: "ALP-199", title: "JWT validation"}
    promptTemplate: "worker-v3"
    tokenLimit: 100000
  status:
    state: Active | Completed | TimedOut | Failed
    tokensUsed: 23456
    exitReason: "token_threshold"
    gitCommits: ["a1b2c3d", "e4f5g6h"]
    filesChanged: ["src/auth.rs", "tests/auth_test.rs"]
```

### NancyChannel (namespaced)

Communication channel. Bridges file IPC to K8s.

```
NancyChannel "alp-198-channel"
  spec:
    workerRef: "alp-198-worker-1"
    transport: FileBased {inbox: "/comms/inbox", outbox: "/comms/outbox"}
    retention: {maxMessages: 1000, archiveAfter: "24h"}
```

### NancyDriver (cluster-scoped)

AI backend configuration. Shared across namespaces.

```
NancyDriver "claude-sonnet"
  spec:
    driverType: AnthropicApi
    endpoint: "https://api.anthropic.com/v1/messages"
    apiKeySecretRef: {name: "anthropic-key", key: "api-key"}
    model: "claude-sonnet-4-5-20250929"
    defaultTokenLimit: 100000
    costPerMillionInputTokens: 3.0
    costPerMillionOutputTokens: 15.0
```

### Ownership Chain

```
NancyDriver (cluster)  ◄── referenced by ──┐
                                            │
NancyTask (ns) ──owns──► NancyWorker (ns) ─┘
                              │
                              ├──owns──► NancySession (ns)  [many]
                              ├──owns──► NancyChannel (ns)  [one]
                              └──owns──► Pod (ns)           [one]
```

---

## The Agent Loop (Rust-Native)

Nancy v3 implements the agent loop in Rust. No dependency on Claude Code CLI,
no Node.js runtime, no 12-second cold starts.

```
┌─────────────────────────────────────────────────────────┐
│                  Nancy Agent Loop                        │
│                                                          │
│  1. ASSEMBLE CONTEXT                                     │
│     ├── System prompt (from template + project config)   │
│     ├── Conversation history (from session state)        │
│     ├── Tool results (from previous iteration)           │
│     └── Inbox messages (directives, guidance)            │
│                                                          │
│  2. CALL LLM                                             │
│     ├── Via ProviderAdapter (Anthropic, OpenAI, Ollama)  │
│     ├── Streaming response via SSE/NDJSON                │
│     └── Token counting on response                       │
│                                                          │
│  3. EXECUTE TOOLS                                        │
│     ├── File ops: read, write, edit, glob, grep          │
│     ├── Shell: bash command execution                    │
│     ├── Git: commit, diff, log, status                   │
│     └── Nancy: update issue state, send message          │
│                                                          │
│  4. PERSIST STATE                                        │
│     ├── Append tool results to conversation              │
│     ├── Update token counter                             │
│     ├── Write to outbox (progress, blockers)             │
│     └── Git commit if meaningful changes                 │
│                                                          │
│  5. CHECK THRESHOLDS                                     │
│     ├── Token budget exhausted? → exit, new session      │
│     ├── All issues done? → signal completion             │
│     ├── Directive received? → process immediately        │
│     └── Otherwise → loop back to step 1                  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Why Nancy Owns the Loop

From research doc 07, the Agent SDK adds ~12s cold start per invocation and
locks you to Claude. By owning the loop:

- **Multi-model**: Route to Claude, GPT, Gemini, or local models per task
- **Sub-second start**: Direct HTTP, no Node.js subprocess
- **Full control**: Token tracking, context compaction, tool execution — all in Rust
- **K8s-native**: The agent binary IS the pod's main container

The tradeoff: we must implement file operations, context management, and tool
execution ourselves. But these are well-understood problems, and we gain
independence from any single provider's SDK.

---

## Model Layer (LiteLLM-Inspired)

From research doc 05: implement LiteLLM's adapter pattern natively in Rust.

### Provider Adapter Trait

```rust
#[async_trait]
pub trait ProviderAdapter: Send + Sync {
    fn validate_environment(&self, config: &ProviderConfig) -> Result<HeaderMap>;
    fn get_endpoint_url(&self, model: &str, config: &ProviderConfig) -> Result<Url>;
    fn transform_request(&self, request: &ChatRequest, config: &ProviderConfig) -> Result<Value>;
    fn transform_response(&self, raw: &Value, model: &str) -> Result<ChatResponse>;
    fn transform_stream_chunk(&self, chunk: &[u8]) -> Result<Option<StreamChunk>>;
    fn capabilities(&self) -> ProviderCapabilities;
}
```

### Canonical Types (OpenAI-Compatible)

All internal communication uses OpenAI message format as the lingua franca.
Provider adapters translate at the boundary.

### Model Registry (Config-Driven)

```toml
# nancy.toml
[[models]]
name = "fast"                              # user-facing alias
provider = "anthropic"
model = "claude-sonnet-4-5-20250929"
api_key_env = "ANTHROPIC_API_KEY"
rpm = 100
input_cost_per_million = 3.0
output_cost_per_million = 15.0

[[models]]
name = "smart"
provider = "anthropic"
model = "claude-opus-4-6"
api_key_env = "ANTHROPIC_API_KEY"
rpm = 50
input_cost_per_million = 15.0
output_cost_per_million = 75.0

[[models]]
name = "cheap"
provider = "openai"
model = "gpt-4o-mini"
api_key_env = "OPENAI_API_KEY"
rpm = 500
input_cost_per_million = 0.15
output_cost_per_million = 0.60

[[models]]
name = "local"
provider = "ollama"
model = "llama3.3:70b"
endpoint = "http://localhost:11434"
```

### Router

Weighted shuffle (default), with fallback chains:

```toml
[routing]
strategy = "weighted-shuffle"
fallbacks = { fast = ["smart", "cheap"], smart = ["fast"] }
```

### Health Tracking

Per-deployment health with automatic cooldowns. 429 → 5s cooldown. >50% failure
rate → cooldown. Recovery is automatic. Uses `DashMap` for lock-free concurrent
access.

### Cost Tracking

Async, never on the hot path. After each LLM response:

1. Count tokens from response
2. Look up per-token cost from registry
3. `tokio::spawn` background write to SQLite/CRD status

### Implementation Priority

1. `ProviderAdapter` trait + `AnthropicAdapter` (Nancy's primary)
2. `OpenAiAdapter` (most tooling assumes this)
3. `OllamaAdapter` (local dev without API keys)
4. Router with weighted shuffle
5. Health tracking + cooldowns
6. Cost tracking
7. Fallback chains

---

## Communication Architecture

### The Bridge Pattern

The agent still uses file-based IPC (inbox/outbox markdown files). This is
Nancy's most valuable architectural decision — it's debuggable, auditable,
survives restarts, and works with any AI CLI tool.

In K8s, the relay sidecar bridges file IPC to gRPC:

```
                   Pod boundary
                   ─────────────────────────
                   │                        │
Orchestrator ──gRPC──► relay ──file──► agent
                   │     │                  │
                   │     ◄──file── agent    │
Orchestrator ◄─gRPC─── relay               │
                   │                        │
                   ─────────────────────────
```

The agent never knows it's in K8s. It reads `/comms/inbox/*.md` and writes
`/comms/outbox/*.md`. The relay translates.

### Message Types

| Direction             | Type          | Purpose                  |
| --------------------- | ------------- | ------------------------ |
| Orchestrator → Worker | Directive     | Do this now (immediate)  |
| Orchestrator → Worker | Guidance      | Consider this (advisory) |
| Orchestrator → Worker | Stop          | Pause execution          |
| Worker → Orchestrator | Progress      | Status update            |
| Worker → Orchestrator | Blocker       | I'm stuck                |
| Worker → Orchestrator | ReviewRequest | Please review my work    |

Messages are immutable once written. Append-only archive for audit trail.

### Real-Time Updates

The API Server exposes WebSocket endpoints for real-time status:

- Task state changes
- Worker heartbeats
- Token usage updates
- Message delivery
- Git commit notifications

CLI and Web UI subscribe to these for live dashboards.

---

## Runtime Abstraction

Nancy must work without K8s for development. The Runtime trait abstracts
worker execution:

```rust
#[async_trait]
pub trait Runtime: Send + Sync {
    async fn spawn_worker(&self, spec: &WorkerSpec) -> Result<WorkerHandle>;
    async fn stop_worker(&self, handle: &WorkerHandle) -> Result<()>;
    async fn pause_worker(&self, handle: &WorkerHandle) -> Result<()>;
    async fn resume_worker(&self, handle: &WorkerHandle) -> Result<()>;
    async fn worker_status(&self, handle: &WorkerHandle) -> Result<WorkerState>;
    async fn send_message(&self, handle: &WorkerHandle, msg: Message) -> Result<()>;
    async fn recv_messages(&self, handle: &WorkerHandle) -> Result<Vec<Message>>;
}
```

### Three Implementations

**ProcessRuntime** (default for `cargo run`)

- Spawns agent as a child process
- File-based IPC in local directories
- Git worktrees in `<repo>-worktrees/`
- No containers, no cluster
- Fastest iteration cycle

**DockerRuntime** (CI, staging)

- Uses bollard crate to manage containers
- Same images as K8s pods
- Volume mounts for worktree and comms
- Tests containerization without full K8s

**KubernetesRuntime** (production)

- Creates NancyWorker CRDs → controller creates Pods
- Full K8s lifecycle: resource limits, health probes, sidecars
- PVC for persistent worktrees
- gRPC for communication

### Auto-Detection

```
CLI flag → env var → K8s API probe → fallback to ProcessRuntime
```

---

## Task Lifecycle

End-to-end flow of a task through the system:

```
1. USER: nancy task create --linear ALP-198
   └── CLI → API Server → creates NancyTask CRD

2. TASK CONTROLLER reconciles:
   ├── Fetches issue details from Linear
   ├── Creates PVC for git worktree
   ├── Clones repo, creates branch nancy/alp-198
   ├── Updates status: Created → Provisioning → Running
   └── Creates NancyWorker CRD

3. WORKER CONTROLLER reconciles:
   ├── Builds pod spec (agent + 3 sidecars)
   ├── Creates Pod via server-side apply
   ├── Creates NancyChannel CRD
   ├── Updates status: Pending → Starting
   └── Waits for all containers ready → Running

4. AGENT LOOP (inside worker pod):
   ├── Reads ISSUES.md (from ConfigMap or git)
   ├── Picks first unfinished issue
   ├── Assembles prompt (template + context + git log)
   ├── Calls LLM via ProviderAdapter
   ├── Executes tool calls (file ops, bash, git)
   ├── Commits changes with structured message
   ├── Updates Linear issue state
   ├── Writes progress to /comms/outbox
   ├── Relay sidecar forwards to control plane via gRPC
   ├── Checks token budget (watchdog sidecar reports)
   └── Loops or exits when thresholds hit

5. SESSION COMPLETES:
   ├── Worker Controller creates NancySession CRD (audit)
   ├── If more issues remain: new session starts
   ├── If all issues done: Worker status → Completed
   └── git-sync sidecar pushes final commits

6. TASK COMPLETES:
   ├── Task Controller detects all issues done
   ├── Creates/updates GitHub PR
   ├── Updates Linear parent issue → Worker Done
   ├── Task status → Completed
   └── Waits for review

7. REVIEW:
   ├── Human or AI reviews PR
   ├── If approved: merge, Task status → Reviewed
   └── If changes requested: new worker session for rework
```

---

## Project Structure

```
nancyr/
├── Cargo.toml                    # Workspace root
├── Cargo.lock
├── charts/
│   └── nancy/                    # Helm chart
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
├── proto/
│   └── nancy.proto               # gRPC definitions
├── crates/
│   ├── nancy-core/               # Domain types, traits, shared logic
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── task.rs           # Task, Issue types + state machines
│   │   │   ├── worker.rs         # Worker types + state machines
│   │   │   ├── session.rs        # Session types
│   │   │   ├── message.rs        # Message types + channel
│   │   │   ├── driver.rs         # Driver/provider config
│   │   │   ├── prompt.rs         # Prompt assembly + template context
│   │   │   └── config.rs         # Configuration hierarchy
│   │   └── Cargo.toml
│   │
│   ├── nancy-crds/               # K8s Custom Resource Definitions
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── task.rs           # NancyTask CRD
│   │   │   ├── worker.rs         # NancyWorker CRD
│   │   │   ├── session.rs        # NancySession CRD
│   │   │   ├── channel.rs        # NancyChannel CRD
│   │   │   └── driver.rs         # NancyDriver CRD
│   │   └── Cargo.toml
│   │
│   ├── nancy-control-plane/      # K8s controllers
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── task_controller.rs
│   │   │   ├── worker_controller.rs
│   │   │   ├── session_controller.rs
│   │   │   ├── linear_sync.rs    # Linear webhook + polling
│   │   │   ├── grpc_hub.rs       # Worker communication hub
│   │   │   └── metrics.rs
│   │   └── Cargo.toml
│   │
│   ├── nancy-api/                # REST + WebSocket API server
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── routes/
│   │   │   │   ├── tasks.rs
│   │   │   │   ├── workers.rs
│   │   │   │   ├── sessions.rs
│   │   │   │   └── messages.rs
│   │   │   ├── ws.rs             # WebSocket for live updates
│   │   │   └── auth.rs
│   │   └── Cargo.toml
│   │
│   ├── nancy-gateway/            # LLM API gateway
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── provider/
│   │   │   │   ├── mod.rs        # ProviderAdapter trait
│   │   │   │   ├── anthropic.rs
│   │   │   │   ├── openai.rs
│   │   │   │   └── ollama.rs
│   │   │   ├── router/
│   │   │   │   ├── mod.rs        # Router + deployment selection
│   │   │   │   ├── strategy.rs   # Routing strategies
│   │   │   │   └── health.rs     # Health tracking + cooldowns
│   │   │   ├── cost.rs           # Cost tracking
│   │   │   └── stream.rs         # SSE normalization
│   │   └── Cargo.toml
│   │
│   ├── nancy-agent/              # The agent loop (worker main container)
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── loop.rs           # Core agent loop
│   │   │   ├── tools/
│   │   │   │   ├── mod.rs        # Tool dispatch
│   │   │   │   ├── file_ops.rs   # Read, Write, Edit, Glob, Grep
│   │   │   │   ├── bash.rs       # Shell execution
│   │   │   │   ├── git.rs        # Git operations
│   │   │   │   └── nancy.rs      # Nancy-specific (issue updates, messages)
│   │   │   ├── context.rs        # Context window management + compaction
│   │   │   └── session.rs        # Session state persistence
│   │   └── Cargo.toml
│   │
│   ├── nancy-relay/              # Sidecar: file IPC ↔ gRPC bridge
│   │   ├── src/main.rs
│   │   └── Cargo.toml
│   │
│   ├── nancy-watchdog/           # Sidecar: health + token monitoring
│   │   ├── src/main.rs
│   │   └── Cargo.toml
│   │
│   ├── nancy-cli/                # CLI client
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── commands/
│   │   │   │   ├── task.rs       # task create/list/get/pause/unpause
│   │   │   │   ├── direct.rs     # send directive
│   │   │   │   ├── status.rs     # dashboard view
│   │   │   │   └── logs.rs       # stream worker logs
│   │   │   └── tui.rs            # Interactive TUI (ratatui)
│   │   └── Cargo.toml
│   │
│   └── nancy-runtime/            # Runtime trait + implementations
│       ├── src/
│       │   ├── lib.rs            # Runtime trait
│       │   ├── process.rs        # Local process runtime
│       │   ├── docker.rs         # Docker runtime (bollard)
│       │   └── kubernetes.rs     # K8s runtime (kube-rs)
│       └── Cargo.toml
│
├── templates/                    # Prompt templates (Tera/minijinja)
│   ├── worker.md.tera
│   ├── planner.md.tera
│   └── reviewer.md.tera
│
├── config/
│   └── default.toml              # Default configuration
│
└── tests/
    ├── integration/              # Integration tests (need K8s via kind)
    └── fixtures/                 # Test data
```

### Workspace Dependencies

```toml
[workspace]
members = ["crates/*"]
resolver = "2"

[workspace.dependencies]
# Async
tokio = { version = "1", features = ["full"] }
futures = "0.3"

# Serialization
serde = { version = "1", features = ["derive"] }
serde_json = "1"
toml = "0.8"

# K8s
kube = { version = "3", features = ["runtime", "derive", "client", "rustls-tls"] }
k8s-openapi = { version = "0.27", features = ["latest"] }
schemars = "1"

# HTTP
reqwest = { version = "0.12", features = ["json", "stream", "rustls-tls"] }
axum = "0.8"
tower = "0.5"
tower-http = { version = "0.6", features = ["trace", "cors"] }

# gRPC
tonic = "0.12"
prost = "0.13"

# Templates
minijinja = { version = "2", features = ["loader"] }

# Git
git2 = "0.19"

# CLI
clap = { version = "4", features = ["derive"] }

# TUI
ratatui = "0.29"
crossterm = "0.28"

# State machines
strum = { version = "0.26", features = ["derive"] }

# Errors
thiserror = "2"
anyhow = "1"

# Observability
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }

# Concurrency
dashmap = "6"

# Time
chrono = { version = "0.4", features = ["serde"] }
```

---

## Implementation Roadmap

### Phase 0: Skeleton (Week 1-2)

Build the workspace, compile, test infrastructure.

- [ ] Cargo workspace with all crates (empty stubs)
- [ ] CI: cargo check, cargo test, cargo clippy, cargo fmt
- [ ] nancy-core: domain types (Task, Issue, Worker, Session, Message)
- [ ] nancy-core: state machine enums with strum
- [ ] nancy-core: config parsing (TOML hierarchy)
- [ ] nancy-cli: basic clap skeleton (`nancy --help` works)

### Phase 1: Agent Loop + Anthropic (Week 3-5)

The minimum viable agent: call Claude, execute tools, commit code.

- [ ] nancy-gateway: ProviderAdapter trait
- [ ] nancy-gateway: AnthropicAdapter (Messages API, tool use, streaming)
- [ ] nancy-agent: core loop (context → LLM → tools → persist)
- [ ] nancy-agent: file tools (read, write, edit, glob, grep)
- [ ] nancy-agent: bash tool (async process execution)
- [ ] nancy-agent: git tools (commit, diff, log)
- [ ] nancy-agent: context window tracking + token counting
- [ ] nancy-agent: session state persistence (file-based)
- [ ] nancy-runtime: ProcessRuntime (spawn agent as child process)
- [ ] Templates: worker prompt template

**Milestone**: `nancy run --issue ALP-199` spawns an agent that writes code and commits.

### Phase 2: Orchestration + Linear (Week 6-8)

Multi-issue workflow, supervisor control, Linear integration.

- [ ] nancy-core: prompt assembly (template + context interpolation)
- [ ] nancy-core: message system (inbox/outbox, markdown files)
- [ ] nancy-core: worktree management (git2 + git CLI hybrid)
- [ ] nancy-cli: task create, status, direct, pause, unpause
- [ ] Linear integration: fetch issues, sync state, update on completion
- [ ] Worker loop: iterate through issues, read git log for context
- [ ] Worker loop: check inbox for directives between iterations
- [ ] nancy-cli: TUI mode (basic ratatui dashboard)

**Milestone**: `nancy task create --linear ALP-198` orchestrates a full task with
multiple sub-issues, syncing state to Linear.

### Phase 3: K8s-Native (Week 9-12)

CRDs, controllers, pods, the full K8s story.

- [ ] nancy-crds: all 5 CRD definitions with derive macros
- [ ] nancy-control-plane: Task controller
- [ ] nancy-control-plane: Worker controller (pod creation, lifecycle)
- [ ] nancy-control-plane: Session controller
- [ ] nancy-relay: file IPC ↔ gRPC bridge sidecar
- [ ] nancy-watchdog: health monitoring + token tracking sidecar
- [ ] nancy-runtime: KubernetesRuntime
- [ ] Docker images: agent, relay, watchdog, git-sync
- [ ] Helm chart: basic deployment
- [ ] Local K8s dev: k3d setup + docs

**Milestone**: `helm install nancy` deploys to a cluster. `nancy task create`
spawns worker pods that run the agent loop.

### Phase 4: API Server + Gateway (Week 13-16)

HTTP API, WebSocket, model routing, multi-provider.

- [ ] nancy-api: REST endpoints (tasks, workers, sessions, messages)
- [ ] nancy-api: WebSocket for real-time updates
- [ ] nancy-api: auth (K8s ServiceAccount tokens, optional OIDC)
- [ ] nancy-gateway: OpenAI-compatible API server
- [ ] nancy-gateway: OpenAiAdapter, OllamaAdapter
- [ ] nancy-gateway: Router with weighted shuffle
- [ ] nancy-gateway: health tracking + cooldowns
- [ ] nancy-gateway: cost tracking (async, SQLite)
- [ ] nancy-gateway: fallback chains
- [ ] nancy-cli: connect to remote API server (not just local)

**Milestone**: Full platform running. CLI talks to API server. Workers route
through gateway. Multiple model providers. Cost dashboard.

### Phase 5: Polish + Production (Week 17+)

Multi-worker, review system, extensions, hardening.

- [ ] Multi-worker coordination (parallel issue execution)
- [ ] AI reviewer (automated PR review before human)
- [ ] nancy-runtime: DockerRuntime
- [ ] Extension/plugin system (event hooks)
- [ ] Prometheus metrics export
- [ ] Structured logging (JSON, correlatable)
- [ ] Leader election for HA control plane
- [ ] CRD versioning + conversion webhooks
- [ ] Documentation + examples

---

## Key Decisions Summary

| Decision       | Choice                    | Rationale                                                                                                                          |
| -------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Language       | Rust                      | Type safety for state machines, single binary for K8s, kube-rs maturity, zero-cost abstractions for adapter pattern, no GC latency |
| Orchestration  | Kubernetes                | Nancy's concerns map 1:1 to K8s primitives. Operator pattern encodes business logic as reconciliation.                             |
| Agent loop     | Rust-native               | Multi-model, sub-second latency, no Node.js dependency, full control over context management                                       |
| Model API      | OpenAI-compatible gateway | LiteLLM adapter pattern in Rust, config-driven provider registry, pluggable routing                                                |
| IPC            | File-based + gRPC bridge  | Preserve debuggability (ls, cat). Relay sidecar bridges to K8s. Agent never knows it's in a cluster.                               |
| State store    | K8s CRDs (etcd)           | No separate DB for execution state. etcd is proven, consistent, watchable.                                                         |
| Issue tracking | Linear (external)         | Linear remains source of truth for issues. Nancy syncs, doesn't replace.                                                           |
| Config format  | TOML                      | Better than JSON for humans, better than YAML for types. Rust ecosystem standard.                                                  |
| Templates      | Minijinja                 | Jinja2 syntax familiar from Python/Ansible, excellent Rust performance                                                             |
| Single binary  | Yes, with subcommands     | One artifact to build/deploy. Feature flags for compile-time component selection.                                                  |
| Local dev      | ProcessRuntime default    | `cargo run` always works. K8s is opt-in via runtime flag.                                                                          |

---

## What We Deliberately Defer

- **Web UI**: CLI + TUI first. Web dashboard is Phase 5+ or community contribution.
- **Multi-tenancy**: Namespace isolation works. Full RBAC/billing is future.
- **Service mesh**: Not needed initially. Add Linkerd if zero-trust becomes a requirement.
- **100+ providers**: Start with 3 (Anthropic, OpenAI, Ollama). Add more as needed.
- **Agent SDK integration**: Optional "turbo mode" for deep Claude tasks. Not core.
- **Distributed tracing**: OpenTelemetry is Phase 5. Structured logging suffices initially.
- **Windows support**: macOS + Linux only. Windows via WSL2.
