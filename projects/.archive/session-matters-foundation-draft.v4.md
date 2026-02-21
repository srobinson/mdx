---
title: session-matters v1 draft spec
type: projects
tags: [session-matters, sm, rewrite, foundation, control-plane, k8s, sessions, channels, selectors, mail, nudge, rust, mcp, cli, draft]
summary: Control plane for the Helioy agent platform. Owns live session records, channels (mail + nudge), selectors, labels, the public API (CLI + MCP), and the spawn flow that delegates execution to runtime-matters. Calls into identity-matters for AuthZ. Rust 2024 workspace mirroring context-matters. Draft spec ready for /linear-workflows.
status: draft
project: session-matters
confidence: medium
created: 2026-05-16
updated: 2026-05-18
related: [helioy-bus-rewrite-charter-draft, agent-matters-config-draft, identity-matters-iam-draft, runtime-matters-kubelet-draft, orchestration-matters-controllers-draft, workflow-matters-choreography-draft, kubernetes-sigs-agent-sandbox, helioy-controller-conventions, helioy-sm-codebase-2026-05]
---

# session-matters v1 draft spec

## Draft caveat

Brainstorm artifact for `/linear-workflows` consumption. Linear planning may rescope freely. The decisions here reflect brainstorm sessions on 2026-05-16 and 2026-05-17 and should be challenged before code lands. The deeper focused dive Linear planning produces should take this as input, break it into a parent issue plus sub-issues, and resolve the open questions in flight.

This product was called `identity-matters` in earlier drafts during the same brainstorm. It is now `session-matters`, since "identity" is reserved for the IAM product. See the [charter](helioy-bus-rewrite-charter-draft.md) for the full family taxonomy.

## Summary

Control plane for the Helioy platform. Owns live session records, channels (mail durable + nudge ephemeral), selectors and labels, the public CLI + MCP API, and the spawn flow that delegates execution to runtime-matters. K8s analog: API server + etcd.

Strict membership: if runtime-matters didn't spawn it (via session-matters), it isn't in the system. No hook-based self-registration. No adoption of stray processes. Sessions are issued at spawn by session-matters; runtime-matters executes the spawn and reports lifecycle.

Calls into identity-matters for AuthN / AuthZ on every authorized operation. v1 identity-matters is a stub (local OS user via Unix peer creds; single admin role); session-matters' integration is built so identity-matters can gain teeth in v2+ without session-matters changing.

Rust 2024 Cargo workspace mirroring context-matters' actual code layout. `tools.toml` plus per-crate `build.rs` codegen for MCP / CLI / skill / README parity. cargo-dist + release-please.

## Motivation

Compressed from the [charter](helioy-bus-rewrite-charter-draft.md). The current helioy-bus is a passive registry conflating multiple concerns into one product. session-matters is the control plane carved out of that bus: it owns "what exists" and "how to address it" while delegating "how to execute" to runtime-matters and "who can do what" to identity-matters.

The rewrite inverts the model: instead of session-matters observing what happened (registries, hooks, probes), session-matters causes things to happen (the daemon orders the spawn; runtime-matters executes; lifecycle reports flow back). Observation becomes secondary; declaration is primary.

## Goals

1. **session-matters owns the public API.** All agent platform interactions enter through the `sm` CLI or session-matters' MCP server. No competing entry points.
2. **Sessions issued at spawn.** UUIDv7 assigned before runtime-matters forks anything. The session id is the stable handle.
3. **Strict membership.** Only sessions spawned through session-matters appear in `sm` queries.
4. **Long-lived sessions are first-class.** Days-long sessions are normal. No time-based eviction.
5. **One daemon, multiple transports.** `smd` hosts unix socket (CLI), MCP stdio bridge (AI callers), event ingest from runtime-matters.
6. **Schema and API stable enough** to support v2 identity-matters teeth (RBAC, capabilities) without session-matters changing.
7. **MCP / CLI / skill / README parity** via `tools.toml` codegen, matching cm.
8. **Hot-path subcommands under 50ms** cold-start. `sm mail check` budget must hold (CLI talks to local socket; smd does the work).
9. **Clean migration path.** Existing helioy-bus consumers migrate with config changes only; old MCP names are not preserved.

## Non-goals

- Forking runtime processes (runtime-matters)
- Per-host substrate primitives: kqueue, waitpid, tmux gateway, RuntimeLauncher impls (runtime-matters)
- IAM enforcement teeth: OIDC, RBAC policies, capability resolution (identity-matters v2+)
- Lifecycle policy (which agents to spawn, when to kill, retries) — orchestration-matters
- Workflow choreography — workflow-matters
- Agent persona / CLAUDE_CONFIG_DIR definition — agent-matters
- Cross-machine federation (v2+; schema must not preclude)
- Web UI (v2; doctor surface is CLI-first in v1)
- Backward-compatibility with helioy-bus's MCP tool surface (clean break)

## K8s mapping (session-matters' specific role)

| K8s concept | session-matters mapping |
|---|---|
| API server | smd's unix socket + MCP server |
| etcd | smd's sqlite store of session records, mail, labels |
| kubectl | `sm` CLI |
| Pod (the entity, not the running process) | A session record |
| Namespace | `workspace` field on a session |
| Label / Selector | First-class; addresses sessions in mail, nudge, queries |
| RBAC subsystem | identity-matters (separate product, called into) |
| Container runtime interface | runtime-matters' socket protocol (separate product, called out to) |

## Operating model

Two long-running daemons at platform runtime; session-matters owns one of them:

```
┌────────────────────────────────────────────────────────────────┐
│  smd  (session-matters daemon)         control plane           │
│  ~10 MB | sqlite | unix socket | MCP server                    │
└──┬──────────────────────────┬─────────────────────┬────────────┘
   │ unix socket              │ library / RPC       │ unix socket
   │                          │                     │
┌──┴─────────┐         ┌──────┴───────┐    ┌────────┴────────────┐
│  sm CLI    │         │ identity-    │    │ runtime-matters     │
│ ephemeral  │         │ matters      │    │ daemon (rtmd)       │
└────────────┘         │ (v1: lib)    │    └─────────────────────┘
                       └──────────────┘
                          ↑ AuthZ check
                            on every API call
```

**One binary** `sm` with mode subcommands:
- `sm daemon` — runs smd (typically launched on demand or via launchd)
- `sm run <runtime>` — spawn flow: smd → identity-matters (AuthZ) → rtmd (execute) → session record updated
- `sm get / delete / wait / logs / probe / describe` — session queries and lifecycle ops (kubectl-shaped)
- `sm mail send / read / check / stop-check` — durable channel
- `sm nudge` — ephemeral channel (delegates tmux send-keys to runtime-matters)
- `sm doctor` — diagnostic view; lists LOST sessions, IAM stub state, runtime-matters reachability
- `sm mcp` — bridges MCP stdio to daemon socket (for AI agent callers)

session-matters does NOT host shims, fork processes, or talk kqueue. Those live in runtime-matters.

## Domain model

### Session record

```
session := {
  id:               UUIDv7, stable, opaque, issued at spawn by smd
  workspace:        "transport-matters"     namespace
  role:             "pm" | "engineer" | "general" | ...
  runtime:          "claude" | "codex" | ...
  agent_config?:    string                  ref into agent-matters (persona spec name/id)
  runtime_session?: opaque string from runtime (codex session_id) when linked back
  transcript_path?: filesystem path when linked back
  locator:          { runtime_pid, start_time, shim_pid, tmux_pane? }
                    populated by runtime-matters; smd just stores
  supervisor_id?:   session_id of controller that spawned us, captured at spawn
  labels:           { ... arbitrary kv ... }
  capabilities?:    [ ... ]                  v2 placeholder; populated from identity-matters
  state:            SPAWNING | RUNNING | TERMINATED | LOST
  principal:        OS user who initiated spawn (from identity-matters; v1: getuid)
  issued_at:        timestamp
  started_at?:      timestamp (when rtmd reported RUNNING)
  terminated_at?:   timestamp
  exit_code?:       integer
  last_active:      timestamp                observational only; usage trace
}
```

**Key shifts from the prior helioy-bus schema:**
- `id` is issued by smd, not derived from coordinates
- `state` is explicit lifecycle (SPAWNING → RUNNING → TERMINATED, with LOST for orphans found at reconciliation)
- `locator.start_time` defeats PID reuse
- `principal` records the OS user (from identity-matters AuthN)
- `runtime_session` and `transcript_path` are optional (filled by link-back from the runtime's SessionStart hook)
- `agent_config` references the persona definition in agent-matters (replaces ad-hoc role config)
- `last_active` renamed from `last_seen` to clarify it's observational

### Channels

```
send(to: Selector, content) → durable mail to recipient inbox(es)
nudge(to: Selector, content) → ephemeral; delegates to runtime-matters' tmux gateway
read(from: Selector | self) → drain unread mail (archives on read)
```

Mail is fully owned by session-matters (sqlite-backed, durable). Nudge is a session-matters API surface that calls into runtime-matters' tmux gateway for the actual send-keys.

```
Selector :=
  | id:<uuid>                              exact session
  | label:<key>=<value>                    match by single label
  | label:<key> in (v1, v2)                set membership
  | workspace:<workspace>                  all in a workspace
  | role:<role>                            convenience for label:role=<role>
  | all                                    universe
```

Channel ACLs delegated to identity-matters when it gains teeth (v2+). v1 is open within the local user.

### Supervisor wiring

Supervision is a **launch-time fact**, not a probe-time question:

1. When a controller (orchestration-matters) invokes `sm run`, it sets its own session_id as `HELIOY_SUPERVISOR_ID` in env or passes `--supervisor`.
2. smd captures `supervisor_id` on the new session row before runtime-matters spawns.
3. When the session ends, smd notifies the supervisor via mail using the recorded `supervisor_id`.

Pull-based queries (`is this session alive?`) hit smd directly; smd reads sqlite (truth maintained by runtime-matters lifecycle events).

### Spawn flow

```
1. user / controller invokes: sm run claude --role pm --workspace transport-matters
2. sm CLI opens ~/.sm/sock, sends Spawn{runtime, role, workspace, labels, ...}
3. smd:
     a. validates request
     b. calls identity-matters: authorize(principal=$peer_uid, action="spawn", resource=spec)
        - v1: always allow if local user; record in audit log
     c. issues UUIDv7 session_id
     d. resolves agent_config from agent-matters (gets CLAUDE_CONFIG_DIR path, env, ...)
     e. resolves supervisor_id from caller env or arg
     f. writes session row, state = SPAWNING
     g. calls runtime-matters' rtmd via socket: Spawn{session_id, runtime, agent_config, env}
        env carries: HELIOY_SESSION_ID, HELIOY_RUNTIME, HELIOY_ROLE, HELIOY_WORKSPACE,
                     HELIOY_SUPERVISOR_ID, CLAUDE_CONFIG_DIR (or equivalent), ...
4. runtime-matters does its work (shim, fork, waitpid, kqueue) and reports back
5. smd updates session row as events arrive:
     - RUNNING when rtmd confirms shim+runtime are alive
     - TERMINATED on shim's waitpid report
     - LOST if reconciliation finds a mismatch
```

Reconciliation: smd periodically queries rtmd for ground-truth state and reconciles its sqlite against rtmd's view. Verification-on-startup catches state lost across smd restart.

### Runtime link-back (optional)

The runtime, on startup, can call `sm link --runtime-session <its-session-id> --transcript <path>` from its SessionStart hook. Links runtime's own session id to our session_id and records `transcript_path`. Powers `sm logs`.

For codex (validated 2026-05-17), the SessionStart hook stdin payload carries:

```json
{
  "session_id":      "019e31e6-606f-70d1-a818-57c088b37763",
  "transcript_path": "/Users/alphab/.codex/sessions/...rollout-...jsonl",
  "cwd":             "/Users/alphab/Dev/LLM/DEV/helioy",
  "hook_event_name": "SessionStart",
  "source":          "startup"
}
```

Same `session_id` returns on resume (stable across resume). One-line hook reads stdin, calls `sm link`. Idempotent. Not load-bearing.

Claude Code follows the same stdin-JSON pattern; one hook design serves both.

## v1 scope

| In scope | Out of scope |
|---|---|
| `smd` daemon (single process, unix socket, sqlite, MCP server) | Forking runtime processes (runtime-matters) |
| Session record with full v1 shape | Shim, kqueue, waitpid, tmux gateway (runtime-matters) |
| Spawn flow that calls into runtime-matters | RuntimeLauncher impls (runtime-matters) |
| Strict-only membership | RBAC enforcement (identity-matters v2+) |
| Three-layer liveness coordination (consume events from rtmd; reconcile) | Substrate-level liveness (runtime-matters) |
| Channels (mail durable + nudge surface) | Nudge implementation (runtime-matters' tmux gateway) |
| Selectors and labels | Push-based supervisor protocol (v1 is local mail-based) |
| MCP server hosted by smd | Web UI |
| `sm logs <selector>` (read-only / one-shot in v0.1.2; `--follow` is CLI-side file tail, not server-streamed) | rmcp dependency |
| `sm doctor` | Backward-compat with helioy-bus MCP tool names |
| `sm link` for runtime → session link-back | Generating agent-matters configs |
| `tools.toml` codegen | Cross-machine federation |
| identity-matters integration point (lib call v1; socket v2+) | identity-matters teeth (separate product) |

**v0.1.2 MCP transport (2026-05-18).** v1 ships MCP as a stdio bridge over the existing unix socket via a `McpBridge` RPC envelope, not as a hosted MCP server inside smd. `sm mcp` reads stdio from the AI client, marshals each line into an `McpBridgeRequest`, sends it over the smd socket; smd's `mcp_bridge::handle_line` (`sm-daemon/src/mcp_bridge.rs:16-31`) dispatches and returns the JSON-RPC response. Source: `sm-cli/src/mcp/server.rs:7-36`. Implication: smd has no HTTP listener in v1; future axum-based MCP transport (Streamable HTTP) is a later pass. The transport-matters WS upgrade brief options A/B/C all bind on that future pass.

## Tech stack

Rust 2024 edition. Cargo workspace. Mirrors `~/Dev/LLM/DEV/helioy/context-matters/`.

### Workspace dependencies

```toml
[workspace.dependencies]
sqlx = { version = "0.8", default-features = false, features = ["runtime-tokio", "sqlite", "macros", "migrate"] }
tokio = { version = "1", features = ["macros", "rt-multi-thread", "io-std", "io-util", "signal", "time", "net"] }
futures = { version = "0.3", default-features = false, features = ["std"] }
clap = { version = "4", features = ["derive"] }
clap_complete = "4.5"
clap_mangen = "0.2"
clap-markdown = "0.1"
color-print = "0.3"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
toml = "0.8"
uuid = { version = "1.9", features = ["v7", "serde"] }
anyhow = "1"
thiserror = "2.0"
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }
chrono = { version = "0.4", features = ["serde"] }
nix = { version = "0.29", features = ["socket"] }  # for SO_PEERCRED / LOCAL_PEERCRED (v1 IAM stub)
insta = { version = "1", features = ["json", "redactions"] }
```

session-matters does NOT depend on `kqueue` or process-substrate crates — those live in runtime-matters.

### Reference implementation

`~/Dev/LLM/DEV/helioy/context-matters/` — read the actual code.

## Proposed Cargo workspace

```
session-matters/
├── Cargo.toml, Cargo.lock
├── tools.toml                       single source of truth for tool docs
├── justfile, AGENTS.md, CLAUDE.md, LESSONS.md, PROJECT.md, CHANGELOG.md, README.md
├── .release-please-manifest.json, .config/
├── crates/
│   ├── sm-core/                     domain types + traits (no IO)
│   │   └── src/{lib,error,types,store,proto,query}.rs
│   ├── sm-store/                    sqlx + sqlite persistence
│   │   └── src/{lib,schema,config}.rs + sqlite/{mod,sessions,mail,labels,audit}.rs
│   ├── sm-daemon/                   the long-running daemon (smd)
│   │   └── src/{lib,server,socket,handler,reconcile,runtime_client,identity_client,mcp_bridge}.rs
│   └── sm-cli/                      CLI + MCP, single binary `sm`
│       ├── Cargo.toml, build.rs, templates/SKILL.md (GEN)
│       └── src/
│           ├── lib.rs, main.rs, shared.rs
│           ├── tool_contracts.rs, tool_docs.rs, tool_examples.rs
│           ├── cli/{mod, cli_def, colors, help_text, generated_help (GEN),
│           │        run, get, describe, delete, logs, probe, wait, label,
│           │        doctor, link, mail, nudge, daemon, mcp}.rs
│           └── mcp/{mod, protocol, transport, server, response, instructions,
│                     schema, panic_guard, generated_schema (GEN),
│                     generated_instructions (GEN), generated_schema/ (GEN), tools/}.rs
└── tests/                           integration tests across crates
```

`tool_contracts.rs`, `tool_docs.rs`, `tool_examples.rs` imported by `build.rs` via `#[path]`. Same types drive runtime and codegen.

`sm-daemon` is a library crate. `sm-cli` is the only binary; `sm daemon` starts the daemon in the same process.

## Codegen pipeline

`crates/sm-cli/build.rs` reads `../../tools.toml` at compile time and produces:

| Output | Path | Purpose |
|---|---|---|
| MCP tool schema (Rust constants) | `src/mcp/generated_schema.rs` | MCP `tools/list` response |
| Per-tool JSON schemas | `src/mcp/generated_schema/<tool>.json` | One file per tool |
| MCP server instructions | `src/mcp/generated_instructions.rs` | MCP `initialize` |
| CLI help text constants | `src/cli/generated_help.rs` | Embedded into clap `#[arg(long_help)]` |
| Skill markdown | `templates/SKILL.md` | Claude Code skill documentation |
| Workspace README | `../../README.md` | Public tool documentation |

`write_if_changed` semantics. `cargo:rerun-if-changed` watches `tools.toml`, `build.rs`, and contract sources.

## CLI surface (kubectl-shaped sketch; final shape driven by `tools.toml`)

```
sm
├── daemon                              run smd
├── run <runtime> [--role R] [--workspace W] [--label k=v] [--supervisor S]
│   [--agent-config NAME] [--detach] [-- runtime-args...]
│                                       spawn (kubectl run analog)
├── get agents [--selector S]           list (kubectl get pods)
├── get agent <selector>                single detail (kubectl get pod X)
├── describe agent <selector>           verbose detail
├── delete agent <selector> [--signal SIG] [--grace S]
├── logs <selector> [-f]                tail transcript_path (requires link-back)
├── probe <selector>                    on-demand substrate recheck via runtime-matters
├── wait <selector> --for=<cond>        block on condition (running|terminated|count=N)
├── label <selector> k=v|k-             add/remove labels
├── doctor                              LOST sessions + IAM stub status + runtime-matters reachability
├── link --runtime-session ID --transcript PATH
│                                       optional runtime → session link-back
├── mail
│   ├── send --to <selector> --content <text>
│   ├── read [--from <selector>] [--peek]
│   ├── check                           hot-path hook
│   └── stop-check
├── nudge --to <selector> --content <text>
├── mcp                                 bridge MCP stdio to daemon socket
├── initdb                              init / migrate daemon db
└── completions <shell>
```

`sm run` is the marquee. All other commands except `daemon` are daemon RPC clients.

**v0.1.2 reality (2026-05-18):** detached mode is the only mode in v1. `--detach` is parsed and ignored. Attached mode is deferred; the terminal-attached interactive path will come with the future `/attach/:session_id` WS route covered in the transport-matters brief. The forkpty substrate is already in place (`sm-driver/src/inprocess.rs:23-26`), so v2 attach is cheap.

`get agents` / `get agent` / `delete agent` follow kubectl verb-resource grammar. Aliases: `agent` ≡ `agents` ≡ `a`. `sm get a` works.

Both `agent_get` (MCP tool name) and `get agent` (CLI form) route through the same handler.

## Boundary contracts

### session-matters → identity-matters (AuthZ)

```rust
// v1: in-process library call
identity_matters::authorize(Principal::Local(peer_uid), Action::Spawn, &resource_spec)
    .await
    .map_err(SmError::Unauthorized)?;
```

In v2+ this becomes an out-of-process call without session-matters changing if the trait shape holds.

### session-matters → runtime-matters (v1: in-process driver; v2+: cross-process)

v0.1.2 substitutes a `SpawnDriver` trait in the same process for the planned cross-process unix-socket boundary. The local-socket boundary lands in a later pass. The trait shape preserves the future contract; consumers do not change when the implementation swaps to a socket-backed driver.

```rust
// crates/sm-driver/src/driver.rs:60-78 (v1 contract)
#[async_trait]
pub trait SpawnDriver: Send + Sync {
    async fn spawn(&self, request: SpawnRequest) -> Result<SpawnHandle>;
    async fn terminate(&self, session_id: Uuid, signal: i32, grace_secs: u32) -> Result<()>;
    async fn probe_session(&self, session_id: Uuid) -> Result<SessionProbe>;
    async fn nudge(&self, session_id: Uuid, content: String) -> Result<()>;
    async fn reap_exited(&self) -> Result<Vec<ReapedSession>>;
}
```

v1 implements `InProcessDriver` (forkpty + waitpid + SIGCHLD) behind the trait. The future cross-process driver (likely targeting rtmd's published `lilo-rm-client` per the runtime-matters review) is the substrate-isolation pass. Trait callers do not change. The `RuntimeRpc::*` envelope and `RuntimeEvent::*` shapes that previously appeared here are removed from this draft until the cross-process pass lands; see runtime-matters draft for the wire contract that pass will adopt.

### Nudge → runtime-matters (tmux send-keys)

```rust
RuntimeRpc::Nudge { session_id: Uuid, content: String }
// runtime-matters resolves session_id → tmux_pane (it knows the locator); sends keys
```

## Migration from helioy-bus

| helioy-bus surface | session-matters surface |
|---|---|
| `agents` table | `sessions` table (new schema) |
| `agent_id` (coordinate-derived) | `id` (UUIDv7, smd-issued) |
| `cwd` | `workspace` |
| `agent_type` | `role` |
| `tmux_target`, `pid` | `locator.tmux_pane`, `locator.runtime_pid` + `start_time` (populated by runtime-matters) |
| `last_seen` | `last_active` |
| `register_agent` MCP tool | **REMOVED**. Strict-only. |
| `send_message` MCP tool | `mail_send` |
| `nudge_message` MCP tool | `nudge` |
| `list_agents` MCP tool | `agent_list` |
| `bus-register.sh`, `bus-unregister.sh` | **DELETED** |
| `check-mail.sh`, `stop-check-mail.sh` | `sm mail check`, `sm mail stop-check` |
| `_self_agent_id()` 5-step resolver | **REMOVED**. Runtime reads `$HELIOY_SESSION_ID` from env. |
| Codex `codex-launch.sh` shell alias | **DELETED**. `sm run codex` instead. |
| `token-capture.sh` | optional `sm link` invocation from SessionStart hook |

Phases: ship parallel → new work uses sm → migrate hooks across plugins → decommission bus.

## Dependencies

External (Rust): see [Tech stack](#tech-stack).

System: none for session-matters itself.

Internal:
- **identity-matters** (required at runtime; v1 lib call, v2+ socket)
- **runtime-matters** (required at runtime; socket for spawn/kill/status; event channel for lifecycle)
- **agent-matters** (required at spawn; resolves persona configs)

## Build / test / release tooling

Mirrors cm's `justfile` with daemon recipes added. `cargo nextest`, `insta` snapshots, `cargo-dist`, `release-please`.

## Open questions for Linear planning

1. **Repository placement.** New repo `~/Dev/LLM/DEV/helioy/session-matters/`? Leaning new.
2. **Daemon lifecycle.** Charter brainstorm leaned Model D (explicit `sm up` / `sm down` / `sm status` or similar). Final verb/grammar TBD in Linear.
3. **Socket path.** [RESOLVED 2026-05-18] `~/.sm/sock` via `SM_HOME` env var or `$HOME/.sm/` (`sm-core/src/paths.rs:16-22`). Linux-specific `XDG_RUNTIME_DIR` not adopted in v1.
4. **Daemon DB recovery.** On smd restart, reconcile via runtime-matters status query? Leaning yes.
5. **session-matters ↔ runtime-matters co-location.** v1 separate daemons (clean product boundary) or co-located (simpler ops)? Leaning separate.
6. **identity-matters call shape.** Library call in v1 (compiled in); socket in v2+. Trait stable enough to swap?
7. **agent-matters resolution.** When `sm run --agent-config NAME` is invoked, how does session-matters resolve NAME? Library? sqlite? filesystem?
8. **MCP tool naming.** [RESOLVED 2026-05-18] Fresh names shipped in v0.1.2; the code matches the decided set plus the surprise addition `agent_label` (mirrors the `sm label` CLI verb).
9. **`sm run` block vs detach default.** Block for interactive. `--detach` for controllers.
10. **Reconciliation cadence.** [RESOLVED 2026-05-18] Hybrid: SIGCHLD-driven within-process reap (`lifecycle.rs:57`) plus periodic full reconcile (`reconcile.rs:79`). Both flow through the in-process `SpawnDriver`; the cross-process variant adopts the same shape over `RuntimeRpc::Events` polling per the runtime-matters review.
11. **Probe semantics.** Is `sm probe X` the same as `sm get agent X --refresh`?

## External validation: agent-sandbox `computeReadyCondition` pattern (2026-05-18)

Per the dedicated agent-sandbox review (`~/.mdx/research/kubernetes-sigs-agent-sandbox.md`, cm `019e3784-2194-7b91-87ae-84e3b3545767`):

### Centralised state machine for session conditions

agent-sandbox's `controllers/sandbox_controller.go:313` (`computeReadyCondition`) takes one set of inputs (sandbox + error + service + pod) and returns one Condition with a deterministic status and reason. The reasoning chain is layered: replica count zero implies Suspended, error implies ReconcilerError, pod missing implies "Pod does not exist", pod Pending implies still-not-ready, pod Running but not Ready implies ContainerStartup phase. All condition-deriving logic lives in one function so the reconciler body stays a sequence of resource reconciles plus one call to `computeConditions` at the end.

**Helioy mapping.** smd surfaces session conditions through `sm get agents`, `sm get agent <selector>`, `sm wait <selector> --for=<cond>`, and the MCP `agent_get` / `agent_describe` tools. Today the session record state (`SPAWNING | RUNNING | TERMINATED | LOST`) is derived inline from event handlers (`RuntimeEvent::SessionRunning` sets state=RUNNING, `RuntimeEvent::SessionTerminated` sets state=TERMINATED, etc.). v1 ships fine that way, but the centralised pattern saves rework when:

- Session conditions grow richer (Ready vs Started vs Suspended become orthogonal)
- Multiple inputs determine one condition (lifecycle event + runtime-matters health probe + identity-matters audit-row presence + tmux pane reachability)
- Reasoning needs to be testable in isolation (unit-test `compute_session_condition(inputs) -> Condition` directly)

**Recommendation for v1.** Adopt the centralised pattern from the start:

```rust
// In sm-core or sm-daemon
fn compute_session_condition(
    session: &SessionRecord,
    last_runtime_event: Option<&RuntimeEvent>,
    rtmd_reachability: RtmdReachability,
) -> SessionCondition {
    // single decision tree returns SessionCondition with reason + last_transition_time
}
```

All call sites that need "what's the session's current condition?" call this function rather than reading individual fields and composing inline. Reconcile-task body becomes: ingest event → update store → call `compute_session_condition` → write the condition into the session row (or compute on read; either works, but ONE place computes).

**Anti-pattern to avoid.** Do not scatter `set_session_state(RUNNING)` / `set_session_state(TERMINATED)` calls across event handlers. That works for the 3-state v1 enum but does not survive the eventual richer condition model. Centralise from day one.

The lesson is structural, not performance: cost of centralising at v1 is one function and one trait; cost of not centralising is touching every event handler at v2 when conditions grow.

**v0.1.2 status (2026-05-18).** The centralised function was NOT adopted in v1. Four inline sites set `SessionState` directly: `handler.rs:116` (Running on spawn), `handler.rs:311` (Terminated on delete), `lifecycle.rs:57` (Terminated on reap), `reconcile.rs:79` (Lost on probe failure). Lift these behind one `compute_session_condition(session, last_event, probe) -> SessionCondition` before any new state-deriving inputs are added (orchestration-matters probes, identity-matters audit signals, tmux-pane reachability). Linear issue to file before v2 work begins; otherwise the four-sites-now becomes the eight-sites-then.

### Cross-cutting conventions

Six cross-cutting CRD/controller conventions lifted from the same review live in `helioy-controller-conventions.md`. session-matters consumes conventions 4 (Server-Side Apply for status) and 5 (label-selector predicates to scope watches) when smd starts owning any CRD or watching k8s resources directly. v1 smd does neither (no CRDs, no k8s watches; it talks to rtmd via socket), so these conventions don't bite at v1; they bite when session-matters surfaces session records as CRDs in v2+ k8s mode.

## Success criteria

1. `sm run claude --role X` spawns; appears in `sm get agents` as SPAWNING; reaches RUNNING within budget.
2. SIGKILL on runtime reflected in `sm get agents` within 1s (via runtime-matters event channel).
3. SIGKILL on rtm-shim reflected within 5s (runtime-matters kqueue belt-and-braces).
4. smd restart reconciles all RUNNING entries within 30s.
5. `sm logs <selector>` tails transcript_path when link-back has fired.
6. 50 sessions = under 100 MB total platform overhead (smd + rtmd + shims), measured.
7. `sm mail check` cold-start under 50ms.
8. `sm doctor` lists every LOST session with evidence.
9. `tools.toml` is the single source of truth for MCP / CLI / skill / README.
10. Test fixtures parallel cm patterns.
11. cargo-dist + release-please produce signed multi-platform installers.

## Parent + sub-issue shape (for /linear-workflows)

**Status (2026-05-18):** v1 planning artifact. Most of the 10 workers below shipped across v0.1.0–v0.1.2; see `~/.mdx/research/helioy-sm-codebase-2026-05.md` §3 for the per-worker landed status. Reorganise into a "what's left after v0.1.2" parent issue before the next `/linear-workflows` invocation. The known remaining work: lift `compute_session_condition()` (this draft §External validation), wire the future cross-process driver against rtmd's `lilo-rm-client` (runtime-matters draft §"PR #17 contract changes"), ship the HTTP listener pass that activates the transport-matters WS brief.

**Parent:** "session-matters v1: control plane for the K8s-faithful Helioy agent platform"

**Sub-issues (10 workers, ordered by dependency):**

1. **Workspace scaffold + tools.toml + codegen.** Root `Cargo.toml`, profiles, dist metadata, `tools.toml`, contract scaffolding, `sm-cli/build.rs` codegen pipeline, justfile, top-level docs structure.
2. **sm-core.** Types (session, locator, selector, state), `SessionStore` + `MailStore` traits, RPC envelope types (Spawn/Kill/...), runtime-matters RPC client types, selector grammar.
3. **sm-store.** sqlx schema + migrations + session CRUD + mail + labels + audit log; `sqlite/` submodule layout matching cm.
4. **identity-matters integration point.** Consume published crates `lilo-im-core` (trait + types), `lilo-im-stub` (v1 always-allow `StubAuthorizer`), and `lilo-im-store` (`SqliteAuditSink` writing to identity-owned SQLite) as Cargo dependencies. Wire StubAuthorizer + SqliteAuditSink into sm-daemon. Trait lives in the identity-matters repo, not in-process at session-matters; v2+ swaps to a socket-backed Authorizer without changing call sites.
5. **sm-daemon skeleton.** tokio task topology, unix socket accept, RPC dispatch, identity-matters lib call wiring, runtime-matters client wiring.
6. **runtime-matters client.** Unix socket client for runtime-matters' spawn/kill/status RPC + inbound event channel. Reconciliation task. Mock for tests.
7. **sm CLI scaffold.** `lib.rs` + `main.rs` + clap definitions for the kubectl-shaped surface + tracing init + socket client helpers.
8. **`sm run` end-to-end.** Marquee feature. CLI → smd → identity-matters check → runtime-matters spawn → session record update. Both block and `--detach`. Tty passthrough delegated to runtime-matters.
9. **Daemon-hosted MCP server.** Protocol + transport + dispatch, `sm mcp` stdio bridge, panic_guard, generated_schema integration. Tools: `agent_run`, `agent_list`, `agent_get`, `agent_describe`, `agent_delete`, `agent_label`, `mail_send`, `mail_read`, `mail_check`, `nudge`, `link`, `doctor`.
10. **Channels + selectors + doctor + tests.** Mail durable + nudge surface (delegates to runtime-matters), label CRUD, selector grammar end-to-end, `sm doctor`, integration tests (cargo nextest), insta snapshots, perf bench for hot path, kill-the-daemon recovery test.

Optional Phase-2 worker (separate parent or later milestone):

11. **Migration: hooks.json plugin edits + helioy-bus decommission plan.**

## Related

- Charter: `helioy-bus-rewrite-charter-draft.md`
- Peer (required dependency): `runtime-matters-kubelet-draft.md`
- Peer (required dependency, v1 stub): `identity-matters-iam-draft.md`
- Peer (config provider): `agent-matters-config-draft.md`
- Above: `orchestration-matters-controllers-draft.md`, `workflow-matters-choreography-draft.md`
- Reference implementation: `~/Dev/LLM/DEV/helioy/context-matters/`
- Salvageable: `helioy-bus/docs/superpowers/specs/2026-05-16-helioy-bus-cli-design.md`
