# Nancy K8s Architecture

> Kubernetes-first design for an autonomous AI agent orchestration platform.
> This is the foundational infrastructure decision -- everything else flows from it.

---

## Why K8s-First

Nancy is a supervisory control system for autonomous coding agents. The agents
do the work. Nancy does orchestration, isolation, lifecycle management, and
communication. This maps _exactly_ to what Kubernetes was designed for.

**The fit is structural, not incidental:**

| Nancy Concern                         | K8s Primitive                                   |
| ------------------------------------- | ----------------------------------------------- |
| Worker isolation                      | Pod                                             |
| Worker lifecycle (start/stop/restart) | Pod controller                                  |
| Resource limits (CPU/memory/tokens)   | Resource quotas, LimitRange                     |
| Git worktree mounting                 | PersistentVolume / hostPath                     |
| Sidecar processes (file watch, relay) | Sidecar containers (native, stable in K8s 1.33) |
| Configuration per task                | ConfigMap                                       |
| Secrets (API keys, tokens)            | Secret                                          |
| Task/Worker/Session state             | Custom Resource Definitions                     |
| Reconciliation loops                  | Controller pattern                              |
| Health monitoring                     | Probes (liveness, readiness, startup)           |
| Scaling                               | HPA or custom scaling logic                     |
| Observability                         | Prometheus metrics, structured logging          |
| Multi-tenancy                         | Namespaces                                      |

Nancy does not need to invent any of these primitives. Kubernetes provides them.
The operator pattern lets us encode Nancy's specific business logic -- what
happens when a task is created, when a worker stalls, when token budget is
exhausted -- as reconciliation loops that drive K8s state toward desired state.

---

## 1. kube-rs: The Rust K8s Ecosystem

### Maturity

kube-rs is a **CNCF Sandbox project** (accepted November 2021). As of early 2026:

- **3.6k+ GitHub stars**, 500+ forks
- **4,300+ total contributors** across the ecosystem
- **2.3M+ downloads/month** on crates.io (kube-client alone)
- Latest release: **kube 3.0.1** (January 2026)
- 100% documented
- Health score: **75 (Healthy)** per CNCF LFX Insights
- Software value estimated at $8.4M
- Active since October 2018

This is not experimental. It is the standard Rust interface to Kubernetes,
analogous to client-go for the Go ecosystem.

### Crate Architecture

The `kube` crate is a facade re-exporting from four specialized crates:

```
kube (facade)
 +-- kube_core    -> core types, Resource trait, metadata, request/response
 +-- kube_client  -> Client, config, discovery, API interface
 +-- kube_derive  -> #[derive(CustomResource)] proc macro
 +-- kube_runtime -> Controller, watcher, reflector, finalizer, events
```

Dependency flow (bottom to top):

```
kube_runtime  (highest-level: controllers, watchers, reflectors)
    |
kube_client   (IO: Client, config, TLS, tower middleware)
    |
kube_core     (types: Resource trait, metadata, params, sans-IO)
    |
kube_derive   (proc macros: CustomResource code generation)
```

External dependency: `k8s-openapi` provides generated Rust structs for all
built-in K8s types (Pod, Deployment, Service, ConfigMap, etc).

### Five Layers of Abstraction

1. **Sans-IO request builder** (`kube_core::Request`) -- builds HTTP requests without IO
2. **IO layer** (`kube_client::Client`) -- tower-based HTTP client with TLS, auth, middleware
3. **Typed API** (`kube_client::Api<K>`) -- generic CRUD for any `Resource`-implementing type
4. **Helpers** (`kube_runtime::watcher`) -- auto-recovering watch streams
5. **High-level abstractions** (`kube_runtime::Controller`) -- full reconciliation loops

### Key Design Properties

- **tower-based**: Client is a `tower::Service`, composable with any tower middleware
- **TLS-flexible**: Choose between rustls (pure Rust) or openssl
- **Async-native**: Built on tokio, uses futures streams throughout
- **Mockable**: Client accepts arbitrary `tower::Service` for testing
- **Generic**: `Api<K>` works with any type implementing the `Resource` trait

### Ecosystem Inspirations

| Rust (kube-rs)              | Go Equivalent           |
| --------------------------- | ----------------------- |
| `kube_core`                 | apimachinery            |
| `kube_client::Client`       | client-go               |
| `kube_runtime::Controller`  | controller-runtime      |
| `#[derive(CustomResource)]` | kubebuilder annotations |

---

## 2. Custom Resource Definitions for Nancy

### CRD Design Principles

Nancy's CRDs encode the domain model (see `04-domain-model.md`) as Kubernetes
resources. The key insight: **Kubernetes becomes the state store**. We don't need
a separate database for task/worker/session state. etcd (via K8s API) is the
single source of truth.

Each CRD gets:

- A Rust struct with `#[derive(CustomResource)]`
- Auto-generated OpenAPI schema (via `schemars`)
- Status subresource for controller-managed state
- Owner references for garbage collection chains
- Finalizers for cleanup logic

### NancyTask

The top-level unit of work. Maps to a Linear parent issue (epic).

```rust
#[derive(CustomResource, Serialize, Deserialize, Clone, Debug, JsonSchema)]
#[kube(
    group = "nancy.dev",
    version = "v1alpha1",
    kind = "NancyTask",
    namespaced,
    status = "NancyTaskStatus",
    shortname = "nt",
    printcolumn = r#"{"name":"State","type":"string","jsonPath":".status.state"}"#,
    printcolumn = r#"{"name":"Issues","type":"integer","jsonPath":".status.issueCount"}"#,
    printcolumn = r#"{"name":"Linear","type":"string","jsonPath":".spec.linearId"}"#,
    printcolumn = r#"{"name":"Age","type":"date","jsonPath":".metadata.creationTimestamp"}"#
)]
pub struct NancyTaskSpec {
    /// Linear parent issue ID (e.g. "ALP-198")
    pub linear_id: String,
    /// Human-friendly name
    pub name: String,
    /// Sub-issues to work on
    pub issues: Vec<IssueRef>,
    /// Git repository URL
    pub repo_url: String,
    /// Branch to create worktree from
    pub base_branch: String,
    /// Driver configuration reference (which AI backend)
    pub driver_ref: String,
    /// Token budget for entire task
    pub token_budget: Option<u64>,
    /// Task-specific prompt overrides
    pub prompt_overrides: Option<PromptOverrides>,
}

#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
pub struct NancyTaskStatus {
    pub state: TaskState,
    pub issue_count: i32,
    pub issues_completed: i32,
    pub current_worker: Option<String>,
    pub current_session: Option<String>,
    pub worktree_path: Option<String>,
    pub total_tokens_used: u64,
    pub last_reconciled: Option<DateTime<Utc>>,
    pub conditions: Vec<Condition>,
}

#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
pub enum TaskState {
    #[default]
    Created,
    Provisioning,  // worktree being set up
    Running,       // worker active
    Paused,
    Completed,     // all issues done
    Reviewed,      // PR approved/merged
    Failed,
}
```

**Ownership chain**: NancyTask owns NancyWorker(s) owns NancySession(s).
When a NancyTask is deleted, K8s garbage collection cascades down.

### NancyWorker

A running AI coding agent. Maps to a Pod (or Pod template).

```rust
#[derive(CustomResource, Serialize, Deserialize, Clone, Debug, JsonSchema)]
#[kube(
    group = "nancy.dev",
    version = "v1alpha1",
    kind = "NancyWorker",
    namespaced,
    status = "NancyWorkerStatus",
    shortname = "nw",
    printcolumn = r#"{"name":"State","type":"string","jsonPath":".status.state"}"#,
    printcolumn = r#"{"name":"Task","type":"string","jsonPath":".spec.taskRef"}"#,
    printcolumn = r#"{"name":"Pod","type":"string","jsonPath":".status.podName"}"#
)]
pub struct NancyWorkerSpec {
    /// Reference to parent NancyTask
    pub task_ref: String,
    /// Driver configuration (which AI + model)
    pub driver_ref: String,
    /// Container image for the worker
    pub image: String,
    /// Resource requirements
    pub resources: WorkerResources,
    /// Volume mounts for git worktree
    pub worktree_volume: VolumeConfig,
    /// Sidecar configuration
    pub sidecars: SidecarConfig,
    /// Environment variables to inject
    pub env: Vec<EnvVar>,
}

#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
pub struct NancyWorkerStatus {
    pub state: WorkerState,
    pub pod_name: Option<String>,
    pub pod_ip: Option<String>,
    pub started_at: Option<DateTime<Utc>>,
    pub tokens_used: u64,
    pub messages_sent: u32,
    pub messages_received: u32,
    pub current_issue: Option<String>,
    pub last_heartbeat: Option<DateTime<Utc>>,
    pub conditions: Vec<Condition>,
}

#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
pub enum WorkerState {
    #[default]
    Pending,
    Starting,
    Running,
    Stalled,     // no heartbeat for threshold duration
    Paused,
    Completed,
    Failed,
    Terminated,
}
```

### NancySession

A single iteration/run of a worker on a specific issue.

```rust
#[derive(CustomResource, Serialize, Deserialize, Clone, Debug, JsonSchema)]
#[kube(
    group = "nancy.dev",
    version = "v1alpha1",
    kind = "NancySession",
    namespaced,
    status = "NancySessionStatus",
    shortname = "ns"
)]
pub struct NancySessionSpec {
    /// Reference to parent NancyWorker
    pub worker_ref: String,
    /// Issue being worked on
    pub issue_ref: IssueRef,
    /// Prompt template to use
    pub prompt_template: String,
    /// Maximum tokens for this session
    pub token_limit: Option<u64>,
    /// Maximum duration
    pub timeout: Option<Duration>,
}

#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
pub struct NancySessionStatus {
    pub state: SessionState,
    pub started_at: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub tokens_used: u64,
    pub exit_reason: Option<String>,
    pub git_commits: Vec<String>,
    pub files_changed: Vec<String>,
}
```

### NancyChannel

Communication channel between orchestrator and worker. This is the K8s
representation of Nancy's file-based IPC pattern.

```rust
#[derive(CustomResource, Serialize, Deserialize, Clone, Debug, JsonSchema)]
#[kube(
    group = "nancy.dev",
    version = "v1alpha1",
    kind = "NancyChannel",
    namespaced,
    status = "NancyChannelStatus",
    shortname = "nc"
)]
pub struct NancyChannelSpec {
    /// Reference to parent NancyWorker
    pub worker_ref: String,
    /// Channel transport mechanism
    pub transport: ChannelTransport,
    /// Message retention policy
    pub retention: RetentionPolicy,
}

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
pub enum ChannelTransport {
    /// File-based IPC (inbox/outbox directories) -- the original Nancy pattern
    FileBased {
        inbox_path: String,
        outbox_path: String,
    },
    /// K8s-native ConfigMap-based messaging (for smaller messages)
    ConfigMap {
        configmap_name: String,
    },
    /// gRPC stream (for real-time, high-throughput)
    Grpc {
        endpoint: String,
        port: u16,
    },
}
```

### NancyDriver

Configuration for which AI backend to use. Cluster-scoped (not namespaced).

```rust
#[derive(CustomResource, Serialize, Deserialize, Clone, Debug, JsonSchema)]
#[kube(
    group = "nancy.dev",
    version = "v1alpha1",
    kind = "NancyDriver",
    status = "NancyDriverStatus",
    shortname = "nd"
    // Note: NOT namespaced -- cluster-wide resource
)]
pub struct NancyDriverSpec {
    /// Driver type
    pub driver_type: DriverType,
    /// API endpoint
    pub endpoint: Option<String>,
    /// Secret reference for API key
    pub api_key_secret_ref: SecretReference,
    /// Model identifier
    pub model: String,
    /// Default token limits
    pub default_token_limit: u64,
    /// Rate limiting
    pub rate_limit: Option<RateLimit>,
    /// Cost tracking
    pub cost_per_million_input_tokens: Option<f64>,
    pub cost_per_million_output_tokens: Option<f64>,
}

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
pub enum DriverType {
    ClaudeCli,        // Claude Code CLI process
    ClaudeApi,        // Anthropic API direct
    OpenAi,           // OpenAI-compatible API
    LiteLlm,          // LiteLLM proxy
    Custom { binary: String },
}
```

### CRD Relationship Map

```
NancyDriver (cluster-scoped)
    referenced by NancyTask.spec.driver_ref
    referenced by NancyWorker.spec.driver_ref

NancyTask (namespaced)
    |
    +-- owns --> NancyWorker (1:1 active, many historical)
    |               |
    |               +-- owns --> NancySession (1:many)
    |               |
    |               +-- owns --> NancyChannel (1:1)
    |
    +-- references --> NancyDriver
```

---

## 3. Worker Pods Architecture

### Pod Design: The Nancy Worker Pod

A Nancy worker pod has one main container and multiple sidecars:

```
┌──────────────────────────────────────────────────────────┐
│ Nancy Worker Pod                                          │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Main Container: nancy-agent                          │  │
│  │ Image: nancy-agent:latest (contains Claude CLI)      │  │
│  │ Command: claude --resume <session> --prompt-file ... │  │
│  │ Mounts:                                              │  │
│  │   /workspace  -> git worktree (PVC)                  │  │
│  │   /comms      -> shared emptyDir (for IPC)           │  │
│  │   /config     -> ConfigMap (prompt templates, etc)   │  │
│  │   /secrets    -> Secret (API keys)                   │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Sidecar: nancy-relay                                 │  │
│  │ Watches /comms/outbox for new messages from agent    │  │
│  │ Relays messages to Nancy control plane via gRPC      │  │
│  │ Writes incoming messages to /comms/inbox             │  │
│  │ Implements the file-based IPC bridge to K8s          │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Sidecar: nancy-watchdog                              │  │
│  │ Monitors agent process health (heartbeat)            │  │
│  │ Tracks token usage (parses Claude CLI output)        │  │
│  │ Enforces token budget limits                         │  │
│  │ Reports metrics to Prometheus                        │  │
│  │ Triggers pause/stop when limits hit                  │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Sidecar: nancy-git-sync                              │  │
│  │ Watches for git commits in /workspace                │  │
│  │ Pushes commits to remote on configurable schedule    │  │
│  │ Reports changed files back to control plane          │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  Shared Volumes:                                          │
│  - workspace-pvc: PersistentVolumeClaim (git worktree)    │
│  - comms: emptyDir (inbox/outbox IPC)                     │
│  - config: ConfigMap (readonly)                           │
│  - secrets: Secret (readonly)                             │
└──────────────────────────────────────────────────────────┘
```

### Native Sidecars (K8s 1.33+)

Kubernetes 1.33 (stable) introduces native sidecar containers -- implemented as
restartable init containers. This is important for Nancy because:

1. **Ordered startup**: Sidecars start before the main agent container
2. **Independent restart**: If a sidecar crashes, it restarts without killing the agent
3. **Clean shutdown**: Sidecars outlive the main container, enabling cleanup

```yaml
spec:
  initContainers:
    - name: nancy-relay
      restartPolicy: Always # <-- makes it a native sidecar
      image: nancy-relay:latest
      volumeMounts:
        - name: comms
          mountPath: /comms
    - name: nancy-watchdog
      restartPolicy: Always
      image: nancy-watchdog:latest
    - name: nancy-git-sync
      restartPolicy: Always
      image: nancy-git-sync:latest
      volumeMounts:
        - name: workspace
          mountPath: /workspace
  containers:
    - name: nancy-agent
      image: nancy-agent:latest
      # ... main container starts after all sidecars are ready
```

### Resource Management

```rust
pub struct WorkerResources {
    /// Main agent container
    pub agent: ResourceRequirements {
        requests: { cpu: "500m", memory: "512Mi" },
        limits:   { cpu: "2",    memory: "2Gi"   },
    },
    /// Relay sidecar (lightweight)
    pub relay: ResourceRequirements {
        requests: { cpu: "50m",  memory: "64Mi"  },
        limits:   { cpu: "200m", memory: "128Mi" },
    },
    /// Watchdog sidecar (lightweight)
    pub watchdog: ResourceRequirements {
        requests: { cpu: "50m",  memory: "32Mi"  },
        limits:   { cpu: "100m", memory: "64Mi"  },
    },
    /// Git sync sidecar
    pub git_sync: ResourceRequirements {
        requests: { cpu: "100m", memory: "128Mi" },
        limits:   { cpu: "500m", memory: "256Mi" },
    },
}
```

### Pod Lifecycle Management

The NancyWorker controller manages pod lifecycle through reconciliation:

```
NancyWorker created (state: Pending)
    -> Controller creates Pod spec
    -> Pod scheduled (state: Starting)
    -> Sidecars become ready
    -> Main container starts (state: Running)
    -> Agent works on issues
    -> Token limit reached OR issues completed (state: Completed)
    -> Finalizer runs cleanup (push final commits, archive logs)
    -> Pod deleted

Stall detection:
    -> Watchdog sidecar reports no heartbeat for N minutes
    -> Controller updates NancyWorker status (state: Stalled)
    -> Controller applies recovery policy (restart, escalate, abandon)

Pause/Resume:
    -> User/orchestrator sets NancyTask.spec.paused = true
    -> Controller sends pause signal to agent via NancyChannel
    -> Agent acknowledges pause
    -> Controller can later unpause by reversing the signal
```

### Volume Strategy

**Git worktrees** are the critical volume concern. Options:

1. **PersistentVolumeClaim (PVC)** -- best for persistent worktrees that survive pod restarts
   - Provisioned per-task, recycled when task completes
   - Supports ReadWriteOnce (sufficient since one worker per worktree)
   - Can use local storage for speed, cloud storage for durability

2. **emptyDir** -- for ephemeral sessions where worktree is cloned fresh
   - Fastest (node-local storage)
   - Lost when pod is evicted
   - Good for short-lived experimental tasks

3. **hostPath** -- for local development, maps directly to host filesystem
   - Matches the current bash Nancy pattern exactly
   - Not suitable for production multi-node clusters

Recommended: **PVC for production**, hostPath for local dev (Kind/minikube).

---

## 4. Service Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nancy System                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Nancy Control Plane (Rust binary, runs as Deployment)     │   │
│  │                                                            │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │   │
│  │  │ Task         │ │ Worker       │ │ Session          │  │   │
│  │  │ Controller   │ │ Controller   │ │ Controller       │  │   │
│  │  └──────┬───────┘ └──────┬───────┘ └──────┬───────────┘  │   │
│  │         │                │                │               │   │
│  │  ┌──────▼────────────────▼────────────────▼───────────┐  │   │
│  │  │              Reconciliation Engine                   │  │   │
│  │  │     (kube-rs Controller::run, tokio runtime)        │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  │                                                            │   │
│  │  ┌─────────────────┐  ┌────────────────────────────────┐  │   │
│  │  │ gRPC Server      │  │ Linear Sync                    │  │   │
│  │  │ (worker comms)   │  │ (webhook + polling)            │  │   │
│  │  └─────────────────┘  └────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Nancy API Server (Rust binary, runs as Deployment)        │   │
│  │                                                            │   │
│  │  REST API for CLI clients + Web UI                         │   │
│  │  Talks to K8s API to CRUD Nancy CRDs                       │   │
│  │  Authentication via K8s ServiceAccount or OIDC             │   │
│  │  WebSocket for real-time task/worker status                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Nancy Gateway (optional, Deployment)                      │   │
│  │                                                            │   │
│  │  Universal model API (OpenAI-compatible)                   │   │
│  │  Routes to different AI providers (Anthropic, OpenAI, etc) │   │
│  │  Token metering and cost tracking                          │   │
│  │  Rate limiting per-task/per-tenant                         │   │
│  │  Could be LiteLLM or custom Rust proxy                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Nancy Worker Pods (created dynamically by Worker Controller) │
│  │                                                            │   │
│  │  [Worker-1] [Worker-2] [Worker-3] ...                      │   │
│  │  Each pod: agent + relay + watchdog + git-sync             │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Communication Patterns

**1. Control Plane <-> K8s API Server**
Standard kube-rs Client. All CRD operations go through the K8s API.
This is the canonical path for state changes.

**2. Control Plane <-> Worker Pods (command channel)**
gRPC bidirectional streaming. The relay sidecar in each worker pod
maintains a gRPC connection back to the control plane.

```
Control Plane                    Worker Pod
     |                               |
     |  gRPC stream (tonic)          |
     | <===========================> |  nancy-relay sidecar
     |                               |       |
     |                               |   writes to /comms/inbox
     |                               |   reads from /comms/outbox
     |                               |       |
     |                               |   nancy-agent (Claude CLI)
```

This preserves Nancy's file-based IPC philosophy. The agent still reads/writes
markdown files in inbox/outbox directories. The relay sidecar bridges that to
gRPC for network transport. The agent never knows it's in K8s.

**3. API Server <-> Control Plane**
Two options:

- **K8s API proxy**: API server creates/modifies CRDs, controller picks up changes.
  Simple, decoupled, eventually consistent. Preferred.
- **Direct gRPC**: For operations needing immediate response (e.g., "send this
  message to worker NOW"). Secondary channel.

**4. Worker <-> Git Remote**
git-sync sidecar handles push/pull on schedule or on-demand trigger from
control plane.

**5. Linear Integration**
Control plane syncs with Linear via webhook (for real-time issue updates) and
polling (for reconciliation). Linear remains source of truth for issue state;
K8s is source of truth for execution state.

### Service Mesh Considerations

**Short answer: don't start with one.**

Nancy's inter-component communication is simple:

- Control plane -> K8s API: standard HTTPS
- Workers -> Control plane: single gRPC stream per worker
- API server -> K8s API: standard HTTPS

A service mesh (Istio, Linkerd) adds:

- mTLS between pods (valuable for security, but K8s NetworkPolicy + Pod Security
  Standards may suffice initially)
- Traffic observability (achievable with OpenTelemetry)
- Retry/circuit-breaking (already handled by tonic/tower)

**Recommendation**: Start without a mesh. Add Linkerd (lightweight, sidecar proxy
is Rust -- low overhead) if/when multi-tenancy or zero-trust networking becomes
a requirement.

---

## 5. Reconciliation Loops

### The Operator Pattern in Nancy

Nancy's control plane runs three main controllers, each as a reconciliation loop:

#### Task Controller

Watches: `NancyTask` resources
Owns: `NancyWorker` resources

```rust
async fn reconcile_task(task: Arc<NancyTask>, ctx: Arc<Context>) -> Result<Action, Error> {
    let client = &ctx.client;
    let ns = task.namespace().unwrap();

    match task.status.as_ref().map(|s| &s.state) {
        Some(TaskState::Created) | None => {
            // 1. Validate Linear issue exists and sync issues
            // 2. Provision git worktree (create PVC, clone repo, create branch)
            // 3. Update status to Provisioning
            // 4. Requeue quickly to check provisioning
            Ok(Action::requeue(Duration::from_secs(5)))
        }
        Some(TaskState::Provisioning) => {
            // 1. Check if PVC is bound and worktree is ready
            // 2. If ready: create NancyWorker, create NancyChannel
            // 3. Update status to Running
            Ok(Action::requeue(Duration::from_secs(5)))
        }
        Some(TaskState::Running) => {
            // 1. Check worker status
            // 2. Sync issue state from Linear
            // 3. Check if all issues completed
            // 4. If all done: update status to Completed
            // 5. If stalled: apply recovery policy
            Ok(Action::requeue(Duration::from_secs(60)))
        }
        Some(TaskState::Completed) => {
            // 1. Ensure final commits pushed
            // 2. Create/update PR
            // 3. Notify Linear
            // 4. Wait for review
            Ok(Action::requeue(Duration::from_secs(300)))
        }
        Some(TaskState::Paused) => {
            // 1. Ensure worker is paused
            // 2. Wait for unpause
            Ok(Action::requeue(Duration::from_secs(120)))
        }
        _ => Ok(Action::requeue(Duration::from_secs(300))),
    }
}
```

#### Worker Controller

Watches: `NancyWorker` resources
Owns: Pods

```rust
async fn reconcile_worker(worker: Arc<NancyWorker>, ctx: Arc<Context>) -> Result<Action, Error> {
    let ns = worker.namespace().unwrap();

    match worker.status.as_ref().map(|s| &s.state) {
        Some(WorkerState::Pending) | None => {
            // 1. Build pod spec (main container + sidecars)
            // 2. Apply pod via server-side apply
            // 3. Update status to Starting
            Ok(Action::requeue(Duration::from_secs(5)))
        }
        Some(WorkerState::Starting) => {
            // 1. Check pod phase (Pending -> Running)
            // 2. Check sidecar readiness
            // 3. When all ready: update status to Running
            Ok(Action::requeue(Duration::from_secs(3)))
        }
        Some(WorkerState::Running) => {
            // 1. Check heartbeat from watchdog sidecar
            // 2. Update token usage from watchdog metrics
            // 3. Check token budget
            // 4. If no heartbeat for threshold: update to Stalled
            // 5. If budget exceeded: send stop signal
            Ok(Action::requeue(Duration::from_secs(30)))
        }
        Some(WorkerState::Stalled) => {
            // 1. Attempt recovery (kill pod, recreate)
            // 2. Or escalate to task controller
            Ok(Action::requeue(Duration::from_secs(10)))
        }
        _ => Ok(Action::requeue(Duration::from_secs(60))),
    }
}
```

#### Session Controller

Watches: `NancySession` resources

```rust
async fn reconcile_session(session: Arc<NancySession>, ctx: Arc<Context>) -> Result<Action, Error> {
    // Sessions are largely informational/observational
    // 1. Track session duration
    // 2. Enforce timeout
    // 3. Record completion metrics
    // 4. Archive session data
    Ok(Action::requeue(Duration::from_secs(60)))
}
```

### Controller Setup (main.rs)

```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt::init();

    let client = Client::try_default().await?;

    // Ensure CRDs are registered
    register_crds(&client).await?;

    // Build shared context
    let ctx = Arc::new(Context {
        client: client.clone(),
        linear_client: LinearClient::new()?,
        metrics: Metrics::new(),
    });

    // Task controller
    let tasks = Api::<NancyTask>::all(client.clone());
    let workers_for_tasks = Api::<NancyWorker>::all(client.clone());

    let task_controller = Controller::new(tasks, watcher::Config::default())
        .owns(workers_for_tasks, watcher::Config::default())
        .shutdown_on_signal()
        .run(reconcile_task, task_error_policy, ctx.clone());

    // Worker controller
    let workers = Api::<NancyWorker>::all(client.clone());
    let pods = Api::<Pod>::all(client.clone());

    let worker_controller = Controller::new(workers, watcher::Config::default())
        .owns(pods, watcher::Config::default())
        .shutdown_on_signal()
        .run(reconcile_worker, worker_error_policy, ctx.clone());

    // Session controller
    let sessions = Api::<NancySession>::all(client.clone());

    let session_controller = Controller::new(sessions, watcher::Config::default())
        .shutdown_on_signal()
        .run(reconcile_session, session_error_policy, ctx.clone());

    // Run all controllers concurrently
    tokio::select! {
        _ = task_controller.for_each(|r| async { log_reconcile(r) }) => {},
        _ = worker_controller.for_each(|r| async { log_reconcile(r) }) => {},
        _ = session_controller.for_each(|r| async { log_reconcile(r) }) => {},
    }

    Ok(())
}
```

---

## 6. Local Development Strategy

### The Problem

K8s-first doesn't mean K8s-only. Developers need to:

1. Run Nancy locally for rapid iteration
2. Test without a cluster
3. Debug without deploying containers

### Approach: Abstraction Layer with Runtime Backends

Nancy should define a **Runtime trait** that abstracts worker execution:

```rust
#[async_trait]
pub trait Runtime: Send + Sync {
    /// Spawn a new worker for a task
    async fn spawn_worker(&self, spec: &NancyWorkerSpec) -> Result<WorkerHandle>;

    /// Stop a running worker
    async fn stop_worker(&self, handle: &WorkerHandle) -> Result<()>;

    /// Pause a running worker
    async fn pause_worker(&self, handle: &WorkerHandle) -> Result<()>;

    /// Resume a paused worker
    async fn resume_worker(&self, handle: &WorkerHandle) -> Result<()>;

    /// Get worker status
    async fn worker_status(&self, handle: &WorkerHandle) -> Result<WorkerState>;

    /// Send message to worker
    async fn send_message(&self, handle: &WorkerHandle, msg: Message) -> Result<()>;

    /// Receive messages from worker
    async fn recv_messages(&self, handle: &WorkerHandle) -> Result<Vec<Message>>;
}
```

### Runtime Implementations

**1. KubernetesRuntime** (production)

```rust
pub struct KubernetesRuntime {
    client: Client,
    namespace: String,
}

impl Runtime for KubernetesRuntime {
    async fn spawn_worker(&self, spec: &NancyWorkerSpec) -> Result<WorkerHandle> {
        // Create NancyWorker CRD -> controller creates Pod
        // Return handle with worker name
    }
    // ...
}
```

**2. ProcessRuntime** (local development)

```rust
pub struct ProcessRuntime {
    work_dir: PathBuf,
}

impl Runtime for ProcessRuntime {
    async fn spawn_worker(&self, spec: &NancyWorkerSpec) -> Result<WorkerHandle> {
        // Spawn Claude CLI as a child process
        // Set up inbox/outbox directories
        // Return handle with PID
    }
    // ...
}
```

**3. DockerRuntime** (intermediate, CI)

```rust
pub struct DockerRuntime {
    docker: Docker, // bollard crate
}

impl Runtime for DockerRuntime {
    async fn spawn_worker(&self, spec: &NancyWorkerSpec) -> Result<WorkerHandle> {
        // Create docker container with same image as K8s pod
        // Mount volumes for worktree and comms
        // Return handle with container ID
    }
    // ...
}
```

### Local Cluster Options

For when you want to test the actual K8s codepath locally:

| Tool              | How it works              | Best for                  | Startup | Resource use |
| ----------------- | ------------------------- | ------------------------- | ------- | ------------ |
| **kind**          | K8s in Docker containers  | CI, testing controllers   | ~30s    | Medium       |
| **k3s** (via k3d) | Lightweight K8s in Docker | Dev + CI, closest to prod | ~20s    | Low          |
| **minikube**      | VM or Docker-based        | Learning, exploration     | ~60s    | High         |

**Recommendation: k3d (k3s in Docker)** for local K8s development.

Reasons:

- Fastest startup
- Lowest resource usage
- Production-grade (k3s is CNCF certified)
- Multi-node clusters easily
- Local registry support built in
- Works great on macOS with Docker Desktop

### Development Workflow

```
Local dev (no cluster):
  cargo run -- --runtime=process
  -> Nancy spawns Claude CLI as child processes
  -> File-based IPC in local directories
  -> Fastest iteration, no containers

Local K8s (with k3d):
  k3d cluster create nancy-dev
  cargo run -- --runtime=kubernetes
  -> Nancy creates real CRDs and Pods
  -> Full K8s behavior, local cluster
  -> Slower iteration, tests real infrastructure

CI:
  kind create cluster
  cargo test --features=integration
  -> Automated integration tests against real K8s API
  -> Controller logic fully tested

Production:
  helm install nancy ./charts/nancy
  -> Real cluster, real everything
```

### Configuration Detection

```rust
pub async fn detect_runtime() -> Box<dyn Runtime> {
    // 1. Check explicit CLI flag
    // 2. Check NANCY_RUNTIME env var
    // 3. Try to connect to K8s API (in-cluster or kubeconfig)
    // 4. Fall back to process runtime

    if let Ok(client) = Client::try_default().await {
        Box::new(KubernetesRuntime::new(client))
    } else {
        tracing::info!("No K8s cluster detected, using process runtime");
        Box::new(ProcessRuntime::new(default_work_dir()))
    }
}
```

---

## 7. Real-World Rust K8s Operators

### Production Examples

**Stackable Data Platform** -- The gold standard for Rust K8s operators.

- 10+ operators for Apache Kafka, Spark, Trino, ZooKeeper, Druid, etc.
- All built with kube-rs + their own `operator-rs` framework
- Open source, production-grade, commercially supported
- Framework includes: PodBuilder, ContainerBuilder, ClusterResources, TLS cert management, CRD versioning with automatic conversion, admission/conversion webhooks
- Proof that Rust operators work at scale for complex distributed systems

**Tembo Operator** -- Rust K8s operator for Postgres.

- Powers Tembo Cloud (managed Postgres platform)
- Built on kube-rs, wraps CloudNativePG
- Manages Postgres extensions, Stacks (use-case-specific configs)
- Demonstrates the pattern of a Rust operator managing complex pod lifecycles

**mirrord Operator** -- By MetalBear.

- Rust operator for their developer tool
- Uses both APIService and Controller patterns
- Shows how to extend K8s API with custom endpoints
- Demonstrates the kube-rs + axum combination

**krator** (Kubernetes Rust stAte machine operaTOR)

- State machine-based operator framework built on kube-rs
- Each resource has explicit state transitions
- Good model for Nancy's worker lifecycle states
- Created by the Krustlet team (Wasm on K8s, also Rust)

**Fluvio** -- Distributed streaming platform.

- Control plane and operator in Rust
- Manages topics, partitions, SPUs as CRDs
- Shows Rust operator managing distributed stateful workloads

### Lessons from the Go World

Even Go-native projects show patterns Nancy should adopt:

**Argo Workflows** -- Workflow engine on K8s.

- Closest conceptual analog to Nancy (orchestrating work as pods)
- Uses CRDs for Workflow, WorkflowTemplate, CronWorkflow
- Worker pods with sidecars for artifact management
- Shows how to handle long-running pod lifecycle

**Tekton** -- CI/CD pipelines as K8s resources.

- Task, Pipeline, PipelineRun as CRDs
- Each step runs as a container in a pod
- Similar to Nancy's session concept

---

## 8. Helm Chart Structure

### Chart Layout

```
charts/nancy/
  Chart.yaml
  values.yaml
  templates/
    _helpers.tpl
    namespace.yaml
    crds/
      nancytask-crd.yaml
      nancyworker-crd.yaml
      nancysession-crd.yaml
      nancychannel-crd.yaml
      nancydriver-crd.yaml
    control-plane/
      deployment.yaml
      service.yaml
      serviceaccount.yaml
      clusterrole.yaml
      clusterrolebinding.yaml
    api-server/
      deployment.yaml
      service.yaml
      ingress.yaml
    gateway/
      deployment.yaml        # optional
      service.yaml
    configmap.yaml            # default config
    secret.yaml               # API key references
    networkpolicy.yaml        # restrict pod-to-pod traffic
    poddisruptionbudget.yaml  # HA for control plane
    prometheusrule.yaml       # alerting rules (optional)
    servicemonitor.yaml       # Prometheus scraping (optional)
```

### values.yaml Structure

```yaml
# Nancy Helm Chart Values

global:
  namespace: nancy-system
  imagePullPolicy: IfNotPresent

controlPlane:
  image:
    repository: ghcr.io/nancy/control-plane
    tag: latest
  replicas: 1 # increase for HA
  resources:
    requests:
      cpu: 250m
      memory: 256Mi
    limits:
      cpu: "1"
      memory: 512Mi
  logLevel: info

apiServer:
  enabled: true
  image:
    repository: ghcr.io/nancy/api-server
    tag: latest
  replicas: 1
  service:
    type: ClusterIP
    port: 8080
  ingress:
    enabled: false
    className: nginx
    host: nancy.example.com

gateway:
  enabled: false
  image:
    repository: ghcr.io/nancy/gateway
    tag: latest

worker:
  image:
    repository: ghcr.io/nancy/agent
    tag: latest
  defaultResources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: "2"
      memory: 2Gi
  sidecars:
    relay:
      image: ghcr.io/nancy/relay:latest
    watchdog:
      image: ghcr.io/nancy/watchdog:latest
    gitSync:
      image: ghcr.io/nancy/git-sync:latest

drivers:
  - name: claude-cli
    type: ClaudeCli
    model: claude-sonnet-4-20250514
    apiKeySecret: claude-api-key
    defaultTokenLimit: 100000

linear:
  enabled: true
  apiKeySecret: linear-api-key
  webhookSecret: linear-webhook-secret

storage:
  worktreeStorageClass: "" # empty = default StorageClass
  worktreeSize: 5Gi

monitoring:
  enabled: false
  serviceMonitor: true
  prometheusRule: true
```

### CRD Management Strategy

Helm best practice for CRDs: **ship CRDs separately from the main chart**.

Options:

1. **crds/ directory** in Helm chart (installed automatically, never upgraded/deleted)
2. **Separate CRD chart** (`nancy-crds`) installed first
3. **Operator self-installs CRDs** on startup (how many kube-rs operators work)

Recommendation: **Option 3 (operator self-installs)** for development,
**Option 2 (separate chart)** for production. The operator can detect if CRDs
exist and apply them via server-side apply:

```rust
async fn register_crds(client: &Client) -> Result<()> {
    let crds: Api<CustomResourceDefinition> = Api::all(client.clone());
    let ssapply = PatchParams::apply("nancy-operator").force();

    for crd in [
        NancyTask::crd(),
        NancyWorker::crd(),
        NancySession::crd(),
        NancyChannel::crd(),
        NancyDriver::crd(),
    ] {
        let name = crd.metadata.name.as_ref().unwrap();
        crds.patch(name, &ssapply, &Patch::Apply(&crd)).await?;
        tracing::info!("CRD registered: {}", name);
    }

    Ok(())
}
```

### RBAC

The operator needs cluster-level permissions:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: nancy-operator
rules:
  # Full access to Nancy CRDs
  - apiGroups: ["nancy.dev"]
    resources: ["*"]
    verbs: ["*"]
  # Manage pods (for worker lifecycle)
  - apiGroups: [""]
    resources: ["pods", "pods/log", "pods/status"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  # Manage PVCs (for worktree storage)
  - apiGroups: [""]
    resources: ["persistentvolumeclaims"]
    verbs: ["get", "list", "watch", "create", "delete"]
  # Read/write ConfigMaps and Secrets
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "watch", "create", "update", "patch"]
  # Publish events
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["create", "patch"]
  # Manage CRDs (self-registration)
  - apiGroups: ["apiextensions.k8s.io"]
    resources: ["customresourcedefinitions"]
    verbs: ["get", "list", "create", "update", "patch"]
```

---

## 9. Crate Dependencies for Nancy

### Core K8s Dependencies

```toml
[dependencies]
# K8s client and runtime
kube = { version = "3", features = ["runtime", "derive", "client", "rustls-tls"] }
k8s-openapi = { version = "0.27", features = ["latest"] }

# Schema generation for CRDs
schemars = "1"

# Async runtime
tokio = { version = "1", features = ["full"] }
futures = "0.3"

# Serialization
serde = { version = "1", features = ["derive"] }
serde_json = "1"
serde_yaml = "0.9"

# Error handling
thiserror = "2"
anyhow = "1"

# gRPC (for worker communication)
tonic = "0.12"
prost = "0.13"

# HTTP server (for API server + webhooks)
axum = "0.8"
tower = "0.5"
tower-http = { version = "0.6", features = ["trace", "cors"] }

# Tracing / observability
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }

# Metrics
prometheus = "0.13"

# Time
chrono = { version = "0.4", features = ["serde"] }
```

### Feature Flags Strategy

```toml
[features]
default = ["kubernetes"]
kubernetes = []       # Full K8s runtime (production)
process = []          # Local process runtime (development)
docker = ["bollard"]  # Docker runtime (CI)
integration = []      # Integration test helpers
```

---

## 10. Open Questions and Risks

### Technical Risks

1. **Claude CLI in a container**: The Claude CLI expects an interactive terminal.
   Running it in a container as a long-lived process needs investigation.
   Mitigation: Use `--print` mode or API instead for initial implementation,
   then add CLI support with a pseudo-terminal (pty) wrapper.

2. **Git worktree persistence**: PVC lifecycle management is fiddly.
   Worktrees must survive pod restarts but be cleaned up when tasks complete.
   Mitigation: Finalizers on NancyTask, background garbage collection controller.

3. **Token tracking accuracy**: Parsing Claude CLI output for token counts is
   fragile (this was a pain point in bash Nancy too).
   Mitigation: Use the API response headers when possible, or the gateway proxy
   to meter tokens at the network level.

4. **etcd size limits**: Kubernetes stores CRD objects in etcd, which has a
   default 1.5MB per-object limit. NancySession objects with large log data
   could hit this.
   Mitigation: Keep CRD status lean, store verbose data externally (S3, PVC).

### Architectural Decisions Still Needed

1. **Single binary vs. multi-binary**: Should control plane, API server, and
   gateway be one binary with subcommands, or separate binaries?
   Leaning: Single binary with subcommands (`nancy serve`, `nancy api`,
   `nancy gateway`). Simpler build, deploy, and version management.

2. **Message format**: Keep markdown-based messages (matching bash Nancy) or
   move to structured protobuf?
   Leaning: Structured protobuf for K8s transport, render to markdown at the
   agent boundary. Best of both worlds.

3. **Multi-tenancy model**: Namespace-per-tenant? Or labels within a shared
   namespace?
   Leaning: Namespace-per-tenant for production, single namespace for dev.

4. **Webhook vs. polling for Linear**: Webhooks are real-time but need ingress.
   Polling is simpler but has latency.
   Leaning: Support both. Webhook when ingress is available, polling as fallback.

---

## Summary: What K8s-First Means for Nancy

K8s-first means:

1. **State lives in CRDs**. No separate database for task/worker/session state.
   etcd is the source of truth for execution state. Linear is the source of
   truth for issue state.

2. **Workers are pods**. Not processes, not threads, not containers-without-orchestration.
   Pods with sidecars, resource limits, health probes, and lifecycle hooks.

3. **Business logic is reconciliation**. Every Nancy behavior is expressed as
   "observe current state, compute desired state, take action to converge."
   No imperative scripts. Declarative, convergent, idempotent.

4. **The operator IS the product**. Nancy's control plane is a K8s operator.
   It extends Kubernetes with domain-specific intelligence about AI agent
   orchestration. `kubectl get nancytasks` is a first-class interface.

5. **Local dev is not second-class**. The Runtime trait abstraction means
   `cargo run` works without a cluster. K8s is the production target, not
   the development requirement.

6. **kube-rs is ready**. CNCF Sandbox, 3.0 stable, millions of downloads,
   proven in production by Stackable (10+ operators), Tembo, MetalBear,
   and others. Rust operators are not experimental.
