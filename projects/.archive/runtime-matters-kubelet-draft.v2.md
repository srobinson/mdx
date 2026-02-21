---
title: runtime-matters v1 draft spec (per-host kubelet + container runtime)
type: projects
tags: [runtime-matters, rtm, kubelet, daemon, shim, kqueue, waitpid, sigchld, tmux, k8s, rust, mcp, cli, draft]
summary: Per-host substrate for the Helioy agent platform. Daemon (rtmd) + tiny shim (rtm-shim) per session + RuntimeLauncher trait + claude/codex impls. Owns kqueue/waitpid/SIGCHLD/tmux. Knows nothing about identities or sessions (just pids and lifecycle events). Talks to session-matters via unix socket. Rust 2024. Draft spec ready for /linear-workflows.
status: draft
project: runtime-matters
confidence: medium
created: 2026-05-17
updated: 2026-05-18
related: [helioy-bus-rewrite-charter-draft, session-matters-foundation-draft, identity-matters-iam-draft, agent-matters-config-draft, berriai-litellm-agent-platform, kubernetes-sigs-agent-sandbox]
---

# runtime-matters v1 draft spec (per-host kubelet + container runtime)

## Draft caveat

Brainstorm artifact for `/linear-workflows` consumption. Linear planning may rescope freely. The decisions here reflect brainstorm sessions on 2026-05-16 and 2026-05-17 and should be challenged before code lands.

The name `runtime-matters` was previously the persona/CLAUDE_CONFIG_DIR product (now `agent-matters`). The user is handling the rename of that repo. This document assumes the rename has happened and `runtime-matters` is the new name for the per-host substrate product.

## Summary

Per-host substrate of the Helioy platform. Combines the K8s kubelet (the per-node agent) and the container runtime (the thing that knows how to fork claude/codex). One daemon per host (`rtmd`), one tiny shim per session (`rtm-shim`), one binary (`rtm`).

Knows nothing about identities, sessions, mail, or selectors. Those are session-matters' concerns. runtime-matters only knows: pid, start_time, tmux_pane (optional), runtime kind. It receives Spawn / Kill / Status RPCs from session-matters and emits Lifecycle events back.

Strict membership boundary: rtmd will not spawn anything except in response to session-matters' Spawn RPC. No self-registration, no external spawning, no adoption. Sessions spawned by rtmd carry env vars set by session-matters (HELIOY_SESSION_ID, etc.) so runtimes know who they are.

Rust 2024 Cargo workspace mirroring context-matters. Daemon hosts MCP server for admin / observability (separate from session-matters' MCP); the canonical MCP surface for users is session-matters'.

## Motivation

Compressed from the [charter](helioy-bus-rewrite-charter-draft.md). The current helioy-bus mixes per-host process management with cluster-wide control. Carving these apart makes:

- session-matters cleanly cluster-flavored (records, channels, API)
- runtime-matters cleanly host-flavored (processes, signals, lifecycle)
- The boundary expressible: session-matters calls into runtime-matters via socket; runtime-matters emits events back

It also unlocks future paths: orchestration-matters could in v2+ spawn non-session workloads (build jobs, one-shot tasks) directly via runtime-matters, without going through session-matters' session record machinery.

## Goals

1. **Per-host substrate isolation.** runtime-matters knows pids, not identities. It can be reused by future control planes.
2. **Deterministic lifecycle signals.** Shim's `waitpid` is the primary signal. Daemon's `kqueue(EVFILT_PROC, NOTE_EXIT)` is belt-and-braces. Probe sweep is the fallback.
3. **macOS-first, Linux-ready.** kqueue is the macOS primary; Linux gets pidfd in v2+ (or `prctl(PR_SET_CHILD_SUBREAPER)` if daemon does direct parenting on Linux).
4. **Tiny shim.** Per-session memory cost < 2 MB RSS. Static Rust binary, no allocations after startup ideally.
5. **One MCP server.** rtmd exposes admin/observability tools (e.g., kill-by-pid, runtime version, kqueue watcher status) — not the user surface.
6. **Schema and API stable enough** that session-matters can rely on the contract while runtime-matters' internals evolve.
7. **Long-lived sessions are first-class.** No time-based eviction.
8. **Hot-path RPC latency under 5ms** for `Status` queries (local socket, sqlite-cached).
9. **Clean migration path.** Existing helioy-bus consumers' process-level concerns absorbed cleanly.

## Non-goals

- Session records, channels, mail, nudge user API (session-matters)
- Identity, AuthZ, audit (identity-matters)
- Persona / CLAUDE_CONFIG_DIR definitions (agent-matters; the user owns this rename)
- Lifecycle policy (orchestration-matters)
- Workflow choreography (workflow-matters)
- Cross-machine federation (v2+)
- Backward-compat with helioy-bus's MCP tool surface

## K8s mapping

| K8s concept | runtime-matters mapping |
|---|---|
| kubelet | rtmd (the per-host daemon) |
| Container Runtime Interface (CRI) | RuntimeLauncher trait + rtmd's socket protocol |
| containerd / CRI-O | rtmd as a whole |
| containerd-shim | rtm-shim (the per-session reaper) |
| runc | RuntimeLauncher implementations (claude launcher, codex launcher) |
| Node | The host machine |
| Pod (the running process) | A runtime instance (claude/codex) under a shim |

The K8s kubelet and container runtime are typically separate processes (kubelet talks to containerd via CRI gRPC). For v1, runtime-matters collapses them into one daemon because the boundary doesn't pay yet at single-host scale. v2+ could split if there's value.

## Operating model

```
session-matters smd
        ↓ unix socket
┌───────┴────────────────────────────────────────────────────┐
│  rtmd  (runtime-matters daemon)         per-host           │
│  ~10 MB | sqlite (lifecycle log) | unix socket | MCP       │
│  RuntimeLauncher registry | kqueue watchers | probe sweep  │
└───────┬───────────────────────────────────┬────────────────┘
        │ forks                             │ kqueue NOTE_EXIT
        │ (one per Spawn)                   │ (belt-and-braces)
        ▼                                   │
┌───────────────┐                           │
│  rtm-shim     │ ←─ session-matters env ── │
│  ~1-2 MB      │   set into child          │
│  fork+exec    │                           │
│  waitpid      │ ──→ report exit to rtmd ──┘
└───────┬───────┘
        │ exec
        ▼
┌───────────────┐
│ runtime       │ (claude / codex / future)
│ 50-200 MB     │
└───────────────┘
```

**Three modes of one binary** `rtm`:
- `rtm daemon` — runs rtmd
- `rtm __shim` — internal; rtmd invokes only
- `rtm` other subcommands — admin / diagnostic / observation client

The session-matters CLI (`sm`) is the user surface. `rtm` is the substrate admin surface.

### Memory math

50 sessions = 10 MB rtmd + 50 × 1.5 MB shims = **~85 MB** runtime-matters total, independent of session-matters (~10 MB smd). Platform overhead total ~95 MB.

### Why two daemons split from session-matters

- runtime-matters can serve other control planes (future orchestration-matters direct calls for non-session workloads)
- rtmd restart-able without dropping smd state, and vice versa
- Maps cleanly to K8s' kubelet (per-node) vs apiserver (cluster) split

For v1 single-host, daemons can be physically co-located if Linear chooses; the product boundary is logical regardless.

## Domain model

### Lifecycle record (rtmd-owned)

```rust
struct Lifecycle {
    session_id: Uuid,             // assigned by session-matters; opaque to runtime-matters
    runtime: RuntimeKind,         // Claude, Codex, ...
    shim_pid: u32,
    runtime_pid: u32,
    start_time: u64,              // ms since UNIX epoch (process start_time, not Lifecycle creation)
    tmux_pane: Option<TmuxPane>,  // populated if the runtime is tmux-bound
    state: ShimState,             // Forking | Running | Exited(code) | Lost(evidence)
    spawned_at: DateTime<Utc>,
    exited_at: Option<DateTime<Utc>>,
}

enum ShimState {
    Forking,           // shim spawned, runtime not yet exec'd
    Running,           // runtime alive (per shim's most recent report)
    Exited(i32),       // shim's waitpid returned with exit code
    Lost(LostEvidence) // probe sweep / kqueue detected mismatch
}
```

runtime-matters does NOT store: workspace, role, identity, labels, supervisor. Those are session-matters' fields. runtime-matters keys everything by `session_id` (opaque from its perspective).

### Spawn flow

```
1. session-matters' smd sends RuntimeRpc::Spawn over the socket
   { session_id, runtime, env, cwd, agent_config }
   
2. rtmd:
   a. resolves RuntimeLauncher impl for runtime kind
   b. forks rtm-shim with arguments: --session-id <id> --runtime <kind> [-- runtime-args]
      env merged from caller + runtime defaults + agent_config-derived (CLAUDE_CONFIG_DIR, etc.)
   c. captures shim_pid; writes Lifecycle row state=Forking
   d. waits for shim's ShimReady RPC (or timeout → state=Lost(NeverStarted))

3. rtm-shim:
   a. installs SIGTERM handler that propagates to child
   b. fork+exec runtime (claude / codex / ...) with inherited env + cwd
   c. captures runtime_pid + start_time via /proc (Linux) or sysctl (macOS)
   d. captures tmux_pane via $TMUX_PANE if present
   e. sends ShimReady to rtmd over the rtmd socket: { session_id, runtime_pid, start_time, tmux_pane }
   f. rtmd updates Lifecycle: state=Running
   g. blocks on waitpid(runtime_pid)

4. rtmd registers kqueue EVFILT_PROC NOTE_EXIT watcher on runtime_pid (belt-and-braces)

5. ... runtime runs ...

6. runtime exits:
   - shim's waitpid returns with exit code
   - shim sends ShimExit { session_id, exit_code } to rtmd
   - rtmd updates Lifecycle: state=Exited(code), exited_at=now
   - rtmd emits RuntimeEvent::SessionTerminated to session-matters
   - shim exits cleanly

7. Belt-and-braces path: shim dies before runtime
   - rtmd's kqueue fires when runtime_pid exits
   - rtmd updates Lifecycle from its own observation
   - rtmd emits RuntimeEvent::SessionTerminated (with evidence: "shim died; kqueue observed exit")

8. Probe sweep path: rtmd restart loses shim socket connections
   - On startup, rtmd reads Lifecycle table, for each Running row:
     - check pid alive AND start_time matches
     - if mismatch: state=Lost(evidence); emit SessionLost
     - if match: re-register kqueue watcher; (shim will reconnect if it survived)
```

### Tmux gateway

Three operations:
- `discover(session_id) → Option<TmuxPane>` — used at ShimReady; runs `tmux display-message`
- `nudge(session_id, content)` — `tmux send-keys` to the recorded pane
- `is_alive(tmux_pane) → bool` — `tmux has-session` / `tmux list-panes -F` (sanity check)

Tmux is soft: runtime-matters runs fine without tmux installed; tmux_pane field is None for non-tmux runtimes.

### RuntimeLauncher trait

```rust
#[async_trait]
pub trait RuntimeLauncher: Send + Sync {
    fn kind(&self) -> RuntimeKind;
    fn binary_path(&self) -> Result<PathBuf, LauncherError>;
    fn build_argv(&self, request: &SpawnRequest) -> Vec<OsString>;
    fn build_env(&self, base: &HashMap<String, String>, request: &SpawnRequest)
        -> HashMap<String, String>;
}
```

v1 implementations: `ClaudeLauncher`, `CodexLauncher`. Registered in `rtm-runtime/src/launchers/mod.rs`. New runtimes are added by implementing the trait and registering.

The trait knows nothing about identities or sessions — only how to build the command line and env for a particular runtime kind.

## v1 scope

| In scope | Out of scope |
|---|---|
| `rtmd` daemon | Session records, channels, mail, nudge user API (session-matters) |
| `rtm-shim` reaper | Identity, AuthZ, audit (identity-matters) |
| RuntimeLauncher trait + claude + codex impls | Cross-machine federation |
| kqueue belt-and-braces (macOS) | Linux pidfd parity (v2+; may also work in v1 with feature gate) |
| Probe sweep (substrate-level only) | Substrate-level supervisor protocol |
| Tmux gateway (discover, nudge, alive) | Tmux layout management (warroom in orchestration-matters) |
| Unix socket RPC + event channel for session-matters | rmcp dependency |
| MCP server for admin tools (kill-by-pid, version, watchers status) | User-facing MCP (session-matters) |
| `tools.toml` codegen | Auto-prune by time |
| Lifecycle log sqlite (rtmd-owned, separate from sm-store) | Plain bus migration tooling (separate worker; uses `rtm` admin verbs) |

## Tech stack

Rust 2024 edition. Cargo workspace. Mirrors `~/Dev/LLM/DEV/helioy/context-matters/`.

### Workspace dependencies

```toml
[workspace.dependencies]
sqlx = { version = "0.8", default-features = false, features = ["runtime-tokio", "sqlite", "macros", "migrate"] }
tokio = { version = "1", features = ["macros", "rt-multi-thread", "io-std", "io-util", "signal", "time", "net", "process"] }
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
nix = { version = "0.29", features = ["process", "signal", "socket"] }
libc = "0.2"
insta = { version = "1", features = ["json", "redactions"] }

[target.'cfg(target_os = "macos")'.dependencies]
kqueue = "1"          # evaluate vs direct libc usage in impl

# Future:
# [target.'cfg(target_os = "linux")'.dependencies]
# rustix = { version = "0.38", features = ["process"] }   # pidfd
```

### Reference implementation

`~/Dev/LLM/DEV/helioy/context-matters/` — read the actual code (the cm/fmm pattern for daemon + codegen).

## Proposed Cargo workspace

```
runtime-matters/
├── Cargo.toml, Cargo.lock
├── tools.toml
├── justfile, AGENTS.md, CLAUDE.md, LESSONS.md, PROJECT.md, CHANGELOG.md, README.md
├── .release-please-manifest.json, .config/
├── crates/
│   ├── rtm-core/                    domain types + traits (no IO)
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── error.rs
│   │       ├── types.rs             Lifecycle, ShimState, SpawnRequest, RuntimeEvent, TmuxPane
│   │       ├── proto.rs             RuntimeRpc envelope + event channel types
│   │       └── launcher.rs          RuntimeLauncher trait definition
│   ├── rtm-store/                   sqlx + sqlite persistence (Lifecycle log only)
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── schema.rs            DDL + migrations
│   │       ├── config.rs
│   │       └── sqlite/
│   │           ├── mod.rs
│   │           └── lifecycle.rs
│   ├── rtm-platform/                platform primitives (macOS-first; Linux-ready)
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── process.rs           pid utilities, start_time portability (macOS sysctl + Linux /proc)
│   │       ├── kqueue.rs            macOS NOTE_EXIT watcher
│   │       ├── pidfd.rs             Linux pidfd (v2+; stub in v1)
│   │       ├── signal.rs            SIGCHLD / SIGTERM handling helpers
│   │       └── tmux.rs              TmuxGateway (discover, nudge, alive)
│   ├── rtm-launchers/               RuntimeLauncher impls
│   │   └── src/
│   │       ├── lib.rs               registry
│   │       ├── claude.rs            ClaudeLauncher
│   │       └── codex.rs             CodexLauncher
│   ├── rtm-daemon/                  the long-running daemon (rtmd)
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── server.rs            tokio task topology
│   │       ├── socket.rs            unix socket accept loop
│   │       ├── handler.rs           RuntimeRpc dispatch (Spawn/Kill/Status/Nudge)
│   │       ├── shim_socket.rs       shim connection management (one per session)
│   │       ├── event_channel.rs     pushes RuntimeEvents to session-matters
│   │       ├── reconcile.rs         probe sweep + state reconciliation on startup
│   │       └── mcp_bridge.rs        MCP-stdio-over-socket for admin tools
│   └── rtm-cli/                     CLI + MCP siblings, single binary
│       ├── Cargo.toml               [[bin]] name = "rtm", path = "src/main.rs"
│       ├── build.rs                 reads ../../tools.toml, emits 5+ codegen outputs
│       ├── templates/SKILL.md       GEN
│       └── src/
│           ├── lib.rs, main.rs, shared.rs
│           ├── tool_contracts.rs, tool_docs.rs, tool_examples.rs
│           ├── cli/
│           │   ├── mod.rs, cli_def.rs, colors.rs, help_text.rs, generated_help.rs (GEN)
│           │   ├── daemon.rs        rtm daemon (runs rtmd)
│           │   ├── shim.rs          rtm __shim (internal; rtmd invokes)
│           │   ├── status.rs        list / status of lifecycles
│           │   ├── kill.rs          admin kill by pid or session_id
│           │   ├── nudge.rs         admin nudge (testing)
│           │   ├── version.rs
│           │   ├── doctor.rs        kqueue watchers status, shim sockets, etc.
│           │   └── mcp.rs           rtm mcp (admin MCP stdio bridge)
│           └── mcp/                 standard mcp/ shape (protocol/transport/dispatch/generated)
└── tests/
```

`rtm-daemon` is a library crate. `rtm-cli` is the only binary.

## Codegen pipeline

`crates/rtm-cli/build.rs` reads `../../tools.toml`. Same five+ outputs as session-matters.

## CLI surface (admin / diagnostic; not the user surface)

```
rtm
├── daemon                              run rtmd
├── __shim --session-id ID --runtime KIND [-- runtime-args]
│                                       internal; rtmd invokes only
├── status [--session-id ID] [--runtime KIND] [--state STATE]
│                                       lifecycle list
├── kill --pid N [--signal SIG] [--grace S]
│                                       admin escape hatch
├── nudge --session-id ID --content TEXT
│                                       admin / test (user-facing nudge is sm nudge)
├── doctor                              kqueue watchers, shim sockets, launcher health
├── version                             rtmd version + git sha
├── mcp                                 admin MCP stdio bridge
├── initdb                              init / migrate rtm-store
└── completions <shell>
```

User-facing operations go through session-matters' `sm`. `rtm` is for substrate-level operators.

## Boundary contracts

### runtime-matters → session-matters (event channel)

```rust
enum RuntimeEvent {
    SessionRunning   { session_id: Uuid, runtime_pid: u32, start_time: u64, tmux_pane: Option<TmuxPane> },
    SessionTerminated{ session_id: Uuid, exit_code: i32, evidence: ExitEvidence },
    SessionLost      { session_id: Uuid, evidence: LostEvidence },
}
```

Pushed over a long-lived unix socket connection from rtmd to smd. smd's reconcile task consumes; sqlite is updated.

### session-matters → runtime-matters (RPC)

Already specified in `session-matters-foundation-draft.md`. Mirror here:

```rust
enum RuntimeRpc {
    Spawn  { session_id, runtime, env, cwd, agent_config },
    Kill   { session_id, signal, grace_secs },
    Status { session_id },
    Nudge  { session_id, content },
}
```

### rtmd → rtm-shim (env at fork)

Env vars set on the shim's environment (shim passes most through to the runtime):

| Var | Purpose |
|---|---|
| `HELIOY_SESSION_ID` | Session id (UUIDv7) |
| `HELIOY_RUNTIME` | `claude`, `codex`, ... |
| `HELIOY_ROLE` | Role string (passed through from session-matters) |
| `HELIOY_WORKSPACE` | Workspace string |
| `HELIOY_SUPERVISOR_ID` | Supervisor session id (if any) |
| `HELIOY_RTMD_SOCK` | Path to rtmd's socket (so shim can report back) |
| Plus agent-matters-derived: | `CLAUDE_CONFIG_DIR`, model overrides, etc. |

The runtime sees all of these (env propagation). The runtime's SessionStart hook can read `HELIOY_SESSION_ID` and call `sm link` to enrich.

## Codex SessionStart contract (validated 2026-05-17)

Same finding as in session-matters spec. Relevant for runtime-matters because:

- Codex SessionStart hook fires AFTER rtm-shim has exec'd codex
- Hook stdin carries codex's `session_id` (UUIDv7) — separate from our `HELIOY_SESSION_ID`
- `source: "startup" | "resume"` discriminator
- `transcript_path` provided

runtime-matters does NOT consume this; the link-back hook calls into session-matters (`sm link`) to record the linkage. runtime-matters' role is just to have made `HELIOY_SESSION_ID` available in env so the hook knows which session to link to.

## Migration from helioy-bus

| helioy-bus surface | runtime-matters surface |
|---|---|
| Hook scripts that fork claude/codex | rtm-shim, invoked only via rtmd |
| `_self_agent_id()` 5-step resolver | Removed. Runtime reads `$HELIOY_SESSION_ID`. |
| `codex-launch.sh` shell alias | `sm run codex` → rtmd → rtm-shim. The shell alias goes away. |
| Bash tmux gateway in helioy-bus | Rust TmuxGateway in `rtm-platform::tmux` |
| Bash pid checks | Rust process utilities in `rtm-platform::process` |

Phases:
- Phase 0: runtime-matters ships parallel to helioy-bus
- Phase 1: new work uses `sm run` (which goes through rtmd)
- Phase 2: existing direct claude/codex invocations migrate to `sm run`
- Phase 3: helioy-bus decommissioned (joint with session-matters)

## Dependencies

External (Rust): see [Tech stack](#tech-stack). Notably `nix`, `libc`, `kqueue` (macOS).

System: `tmux` (soft; only for tmux-bound sessions).

Internal: none. runtime-matters is a peer of session-matters, not below it. session-matters depends on runtime-matters; the reverse is false.

## Build / test / release tooling

Mirrors cm's `justfile` with daemon recipes. `cargo nextest`, `insta`, `cargo-dist`, `release-please`.

## Open questions for Linear planning

1. **Repository placement.** New repo `~/Dev/LLM/DEV/helioy/runtime-matters/` once the current runtime-matters is renamed to agent-matters? Leaning new.
2. **Daemon lifecycle.** Like smd: explicit start (Model D) preferred. `rtm daemon start` / `rtm daemon stop` / `rtm daemon status`. Or auto-start when session-matters first tries to connect?
3. **Socket path.** `~/.rtm/sock` per user? `$XDG_RUNTIME_DIR/rtm/sock` on Linux + `~/.rtm/sock` on macOS?
4. **shim-rtmd reconnect.** When rtmd restarts, do shims reconnect to its new socket? Probably yes (containerd-shim does this). Mechanism: shim retries with backoff on socket close.
5. **Linux story for v1.** Ship Linux with pidfd in v1 or defer to v2+ (macOS-only v1)? Pidfd is cleaner than `PR_SET_CHILD_SUBREAPER`. Leaning ship Linux too but defer feature parity if budget tight.
6. **Reconciliation cadence.** Probe sweep every N seconds? On rtmd startup only? Both?
7. **RuntimeLauncher discovery.** Compile-time registry (v1) vs runtime-loaded plugins (v2+).
8. **rtmd's MCP scope.** Admin tools only (kill-by-pid, status), or also expose RuntimeLauncher introspection for future GUI? v1 minimal.
9. **Privilege model.** rtmd runs as the user. v1 keeps it that way. v2+ may need a system-level rtmd for shared infrastructure.

## External validation: agent-sandbox CRD + BerriAI/litellm-agent-platform (2026-05-18)

Two external repos validate runtime-matters' shape against a working production reference. The platform `BerriAI/litellm-agent-platform` (10 days old, MIT, 135 stars, A− grade) ships a Next.js + TypeScript reference impl that consumes the underlying `kubernetes-sigs/agent-sandbox` CRD (~9 months, Apache-2.0, 2.2k stars, official SIG Apps project). Reviewed in `~/.mdx/research/berriai-litellm-agent-platform.md` (cm `019e34ba-881f-7971-924f-a978599015c2`); dedicated agent-sandbox review in flight as of 2026-05-18 (artifact `~/.mdx/research/kubernetes-sigs-agent-sandbox.md` forthcoming).

The platform's per-host product split (sandbox controller + harness per session + warm pool) matches runtime-matters' shape closely enough that the architectural choices Helioy faces are the ones BerriAI has already worked through.

### CRD-targeting decision (pending)

Helioy's k8s endgame (per [[feedback_local_first_is_primitive_k8s_is_goal]]) puts runtime-matters in the position of either consuming agent-sandbox's CRDs or shipping its own. The dedicated agent-sandbox review will land the recommendation. Options on the table:

- **Option A**: target raw `Sandbox` CR via `kube-rs`. Maximum control. Maximum exposure to v1alpha1 churn. **This is what BerriAI does** (they skip `SandboxClaim` from the extensions module).
- **Option B**: target `SandboxClaim` (the extension abstraction). Cleaner. Defers some control to the upstream controller. Why BerriAI skipped this is itself a signal worth understanding.
- **Option C**: build runtime-matters' own CRD; don't consume agent-sandbox at all. Faster v1, slower k8s endgame.
- **Option D**: defer the CRD decision; v1 ships rtmd-on-bare-metal only; CRD targeting decided at v2 once agent-sandbox reaches v1beta1.

The decision interacts with invariant 1 (strict-only membership) and invariant 9 (Rust 2024). It does NOT interact with v1 (which is bare-metal-only by intent). It DOES interact with the rtm-launchers trait shape, because a k8s launcher impl will look different from a bare-metal launcher impl, and the trait must accommodate both without breaking existing callers.

### v1alpha1 pin-and-track

When runtime-matters does consume agent-sandbox (whichever option above), the dependency must pin the CRD version explicitly and track upstream releases deliberately. `v1alpha1` is pre-1.0 with active CRD churn (upstream issue 127 "Strict Sandbox-to-Pod Mapping" still open as of 2026-05-18). Pin-and-track plan:

- Pin `kube-rs` codegen to a specific CRD release tag, not `main`.
- Dependabot or equivalent surfaces upstream releases; absorb only in named minor versions of runtime-matters.
- Treat CRD breaking changes as runtime-matters minor-version bumps; track via a `CRD_VERSIONS.md` table in the runtime-matters repo.
- Build a fixture suite that exercises the CRD shape in isolation; CI runs against pinned + latest to detect upstream drift.

### Per-harness directory shape (pattern to absorb)

BerriAI's `harnesses/` directory uses `{claude-code, codex, hermes, opencode, claude-agent-sdk}/` + a `_shared/` extraction. This maps cleanly to `rtm-launchers/` per-impl files (already specified above as `claude.rs`, `codex.rs`). Two adjustments worth making for runtime-matters v1:

1. Add an `rtm-launchers/_shared/` mod (or `rtm-launchers/common/`) for cross-launcher utilities. Empty in v1; reserved for the inevitable shared code as more launchers land.
2. Per-launcher directories rather than single files for any launcher that grows beyond ~200 LOC. `claude.rs` may stay a single file; `codex.rs` may want a directory once `SessionStart` hook wiring is in place.

### Image snapshot at agent-creation (boundary clarification)

BerriAI snapshots harness image into `task_definition_arn` at agent-creation; existing agents keep their image even after the env var changes. For Helioy, this lives in **agent-matters**, not runtime-matters: agent-matters owns persona/config/skills as immutable at agent-creation time. runtime-matters' RuntimeLauncher impls must respect agent-matters' snapshot and not auto-update binaries between sessions of the same agent. Spec implication: `SpawnRequest.agent_config` carries the snapshotted launcher version, and `RuntimeLauncher::binary_path` must respect it rather than calling `which claude` fresh.

### Single-shot diagnose super-bundle (pattern for `rtm doctor`)

BerriAI's `/diagnose` endpoint (881 LOC, single handler, 9 parallel reads, 8 named detection codes with severity + recommended_action) replaces "run ten kubectls" with one call that returns correlated state. `rtm doctor` should adopt this shape:

- One `rtm doctor [--session-id ID]` invocation returns: kqueue watchers status, all shim socket connection states, launcher health (binary present + version), lifecycle log summary (counts by state), recent SessionLost evidence rows, rtmd process self-stats (RSS, fd count, socket queue depth), tmux gateway reachability, and (if k8s mode) pod/CR status.
- Each detection ships a `recommended_action` string the operator can act on. Not just "kqueue watcher missing" but "kqueue watcher missing for session X; the belt-and-braces path is degraded; restart rtmd OR investigate the watcher leak in rtm-platform::kqueue".
- Severity classes: ok, info, warning, error.
- Output as both human-readable table (default) and JSON (`--json` flag) for tooling.

This is a v1 deliverable. The 881-LOC handler in BerriAI is single-handler-monolithic; for Helioy, decompose by detection (one fn per code) and parallel-await via `tokio::join!`. Keep the response shape flat: a Vec of detections plus an overall status summary.

## Success criteria

1. `sm run claude` reaches the runtime alive within ~200ms (rtmd Spawn → shim ready → runtime exec'd).
2. SIGKILL on the runtime reflected back to session-matters within 1s (shim waitpid → ShimExit → RuntimeEvent::SessionTerminated).
3. SIGKILL on rtm-shim reflected back to session-matters within 5s (kqueue NOTE_EXIT → RuntimeEvent::SessionTerminated with evidence).
4. rtmd restart reconciles its Lifecycle log within 30s; emits SessionLost for any orphaned rows.
5. Tmux nudge: `sm nudge` → smd → rtmd → tmux gateway → keys land in pane within budget.
6. 50 sessions = under 90 MB for rtmd + 50 shims, measured.
7. Probe sweep + kqueue + waitpid combined detect every form of unexpected exit (clean exit, SIGKILL on runtime, SIGKILL on shim, machine sleep/wake).
8. `tools.toml` is the single source of truth for rtm's admin MCP / CLI / skill / README.

## Parent + sub-issue shape (for /linear-workflows)

**Parent:** "runtime-matters v1: per-host kubelet + container runtime for the K8s-faithful Helioy agent platform"

**Sub-issues (8 workers):**

1. **Workspace scaffold + tools.toml + codegen.** Root `Cargo.toml`, profiles, dist metadata, `tools.toml`, contracts scaffolding, `rtm-cli/build.rs` codegen pipeline, justfile, top-level docs structure.
2. **rtm-core.** Types (Lifecycle, ShimState, SpawnRequest, RuntimeEvent, TmuxPane, RuntimeKind), RuntimeLauncher trait definition, RuntimeRpc envelope, event channel types, error.
3. **rtm-store.** sqlx schema + migrations + Lifecycle CRUD. `sqlite/` submodule layout.
4. **rtm-platform.** process (pid + start_time portability macOS + Linux), kqueue (macOS NOTE_EXIT), signal (SIGCHLD + SIGTERM), tmux gateway (discover + nudge + alive). pidfd stub for Linux v2+.
5. **rtm-launchers.** ClaudeLauncher + CodexLauncher implementations. Registry. Argv + env builders. RuntimeLauncher trait conformance tests.
6. **rtm-daemon skeleton.** tokio task topology, unix socket accept, RuntimeRpc dispatch, shim socket connection management, event channel out to session-matters, reconcile task, MCP bridge for admin.
7. **rtm-shim.** Minimal binary mode (`rtm __shim`): fork+exec runtime, capture pid+start_time+tmux_pane, ShimReady RPC, install SIGTERM handler, waitpid, ShimExit RPC. Reconnect-on-rtmd-restart.
8. **Liveness + reconciliation + doctor + tests.** Probe sweep, kqueue watchers, `rtm doctor`, integration tests (cargo nextest), insta snapshots, perf bench. Critical scenarios: SIGKILL runtime, SIGKILL shim, rtmd restart, system sleep/wake.

Optional Phase-2 worker:

9. **Linux pidfd impl** (if v1 ships Linux at all): swap kqueue for pidfd on Linux.

## Related

- Charter: `helioy-bus-rewrite-charter-draft.md`
- Peer (caller): `session-matters-foundation-draft.md`
- Peer (AuthZ caller from smd): `identity-matters-iam-draft.md`
- Peer (config consumer at spawn): `agent-matters-config-draft.md` (the user is handling the rename)
- Reference implementation: `~/Dev/LLM/DEV/helioy/context-matters/`
