---
title: Helioy platform charter (K8s-faithful agent control plane)
type: projects
tags: [helioy, helioy-bus, rewrite, charter, k8s, daemon-shim, agent-matters, identity-matters, session-matters, runtime-matters, orchestration-matters, workflow-matters, transport-matters, draft]
summary: Umbrella charter for the K8s-faithful Helioy platform rewrite. Decomposes the current helioy-bus into seven products spanning agent definition, identity/IAM, session control plane, per-host substrate, controllers, choreography, and wire-level observation. Locks the K8s mapping as design principle. Draft for Linear planning.
status: draft
project: helioy
confidence: medium
created: 2026-05-16
updated: 2026-05-17
related: [agent-matters-config-draft, identity-matters-iam-draft, session-matters-foundation-draft, runtime-matters-kubelet-draft, orchestration-matters-controllers-draft, workflow-matters-choreography-draft]
---

# Helioy platform charter (K8s-faithful agent control plane)

## Draft caveat

Brainstorm artifact, not a binding spec. Linear planning may rescope freely. The decisions captured here reflect brainstorm sessions on 2026-05-16 and 2026-05-17 and should be challenged before any implementation work begins. The deeper focused dive that Linear planning produces should treat this charter as input, not constraint.

The product family has gone through several namings during the brainstorm. The names locked here are the final shape; prior names appear in cm history but should not be referenced going forward except as historical pointers.

## Why a rewrite

The current helioy-bus is functional and impressively capable for the amount of hacking that produced it. It is also foundational to every higher-level pattern (Nancy orchestration, warroom dispatch, plugin reload, inter-agent mail). One session of close inspection surfaced multiple compounding fragilities:

- Registration depends on a shell alias being loaded (codex case). Miss the alias → no registration. Alias loaded but SIGKILL → no unregister.
- Liveness has four signals with no single source of truth. PID reuse defeats one. Tmux-less codex agents are invisible to another. `last_seen` is a usage trace mistaken for a liveness signal.
- Eviction is lazy and tmux-centric. Long-lived non-tmux agents accumulate as zombies (`omg:general` from 2026-05-05 was still on the bus when this charter was drafted).
- DB invariants are enforced in shell hooks, not the schema.
- The bus conflates multiple distinct responsibilities into one product.

The fragility compounds upward. Nancy, warroom, and any future enterprise scope all inherit it.

The rewrite responds by taking Kubernetes' control plane shape as the design principle. Each Helioy concern maps to a K8s concept, and each product owns one mapped concern.

## The seven-product family

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  agent-matters (am2)         Persona / CLAUDE_CONFIG_DIR / skills / role     │
│  ────────────────────        ↳ consumed by runtime-matters at spawn          │
│                                                                              │
│  identity-matters (im)       IAM: principals, RBAC, AuthN, AuthZ, audit      │
│  ────────────────────        ↓ authorizes calls to                           │
│                                                                              │
│  session-matters (sm)        Control plane: live sessions, channels,         │
│  ────────────────────        selectors, MCP, spawn API                       │
│                              ↓ delegates execution to                        │
│                                                                              │
│  runtime-matters (rtm)       Per-host kubelet + container runtime:           │
│  ────────────────────        daemon + shim + launchers + kqueue              │
│                              ↓ wraps                                         │
│                                                                              │
│  runtimes                    claude, codex, future                           │
└──────────────────────────────────────────────────────────────────────────────┘

   orchestration-matters (om)  Controllers above session-matters:              
   ────────────────────        Warroom, future Daemon / Job / Replicated       

   workflow-matters (wm)       Choreography above orchestration-matters:       
   ────────────────────        DAGs, state machines, multi-agent handoffs      

   transport-matters (tm)      Wire-level observation (independent axis)       
```

`am2` notation is a placeholder. Actual binary abbreviation TBD; agent-matters may use `agm` or stay un-abbreviated to avoid colliding with `am` (attention-matters).

### Naming history

| Layer | Final name | Prior name(s) |
|---|---|---|
| Persona / config | agent-matters | runtime-matters (renamed 2026-04-23 from agent-matters per ADR 000); reverts to agent-matters as the most literal name once runtime-matters is reassigned |
| IAM | identity-matters | (new; takes over the name from the earlier control-plane draft once that was renamed to session-matters) |
| Control plane | session-matters | identity-matters (in earlier 2026-05-16/17 brainstorm drafts) |
| Per-host substrate | runtime-matters | node-matters (considered briefly during the 2026-05-17 brainstorm) |
| Controllers | orchestration-matters | unchanged |
| Choreography | workflow-matters | unchanged |
| Wire observation | transport-matters | unchanged |

The runtime-matters slot was previously occupied by the persona/config product. The user is handling the actual repo rename; this charter assumes it has happened.

### Per-product ownership

| Product | Owns | Consumed by |
|---|---|---|
| **agent-matters** | Persona definitions: skills, system prompts, role configs, the CLAUDE_CONFIG_DIR contents. Declarative spec for what an agent IS when spawned. | runtime-matters (at spawn time) |
| **identity-matters** | IAM: principals, roles, policies, authentication, authorization, audit log. v1 is a near-stub: local OS user via Unix peer credentials; single admin role; audit log only. | session-matters (every authorized API call) |
| **session-matters** | Control plane state and API: live session records, channels (mail + nudge), selectors, labels, MCP server, the spawn API that calls into runtime-matters. The K8s API-server-plus-etcd equivalent. | cm, fmm, hooks, orchestration-matters, workflow-matters, end users |
| **runtime-matters** | Per-host substrate: the daemon (`rtmd`), the shim (`rtm-shim`), the RuntimeLauncher trait + claude/codex implementations, kqueue / waitpid / SIGCHLD, tmux gateway, process utilities. Knows nothing about identities or sessions; just pids and lifecycle events. | session-matters (via local socket / RPC) |
| **orchestration-matters** | Controllers: spawn policy, kill, restart, declarative agent state, presets. Warroom is the first controller pattern; Daemon, Job, Replicated are roadmap. | Warroom users, workflow-matters supervisors |
| **workflow-matters** | DAGs, state machines, multi-agent handoffs, retries, resumability. | Nancy and other agent-driven processes |
| **transport-matters** | Forensic observation of wire-level transport. Paired with agent-matters as control + observe. | Independent; consumes other products as data sources, not dependencies |

## K8s as design principle (not afterthought)

The whole platform is shaped by Kubernetes' control-plane decomposition. This is structural, not metaphorical.

| K8s concept | Helioy mapping |
|---|---|
| **Pod manifest / PodSpec** | agent-matters (the declarative agent definition) |
| **Pod** (the running thing) | A live session in session-matters (a claude/codex process running under runtime-matters) |
| **ServiceAccount + RBAC + IAM** | identity-matters |
| **AuthN / AuthZ / audit** | identity-matters |
| **API server + etcd** | session-matters (state of the cluster + API surface) |
| **Namespace** | `workspace` field on a session |
| **Label / Selector** | First-class. Addresses sessions in mail, nudge, queries |
| **kubelet** | runtime-matters (daemon, `rtmd`) |
| **CRI (container runtime interface)** | RuntimeLauncher trait |
| **containerd / CRI-O / runc** | runtime-matters' claude/codex launcher implementations |
| **containerd-shim** | `rtm-shim` (per-session reaper) |
| **Controller (Deployment, Job, DaemonSet, ReplicaSet)** | orchestration-matters controllers (Warroom in v1) |
| **Workflow (Argo)** | workflow-matters |
| **kubectl** | `sm` CLI (talks to `smd` over unix socket) |
| **kubectl exec / port-forward / logs** | Session-matters CLI subcommands |
| **Audit log** | sqlite-backed event log inside identity-matters; session-matters writes the events |
| **Service mesh observability** | transport-matters |

Consequences of taking K8s seriously:

1. **Sessions are issued at spawn**, never inferred after the fact. The kubelet places a pod; pods don't self-register. session-matters calls into runtime-matters to spawn; the session id exists before the runtime process does.
2. **Strict membership.** If runtime-matters didn't spawn it, it isn't in the system. No "adoption" of stray processes. Matches "if the kubelet didn't schedule it, it's not in the cluster".
3. **Daemon + shim, not fat parent.** runtime-matters' daemon is the smart per-host control. The shim is a dumb per-session process owning lifecycle signals. The containerd-shim pattern.
4. **Supervision is a launch-time fact.** When orchestration-matters spawns through session-matters, the controller's id is captured on the session record at create time via env propagation.
5. **The daemon IS the MCP server.** Both `smd` (session-matters daemon) and `rtmd` (runtime-matters daemon) are long-running processes that host MCP transports alongside their unix sockets. No one-shot MCP per call (the cm/fmm pattern doesn't fit a control plane).
6. **macOS realities respected.** No `PR_SET_CHILD_SUBREAPER`. runtime-matters uses `kqueue(EVFILT_PROC, NOTE_EXIT)` for belt-and-braces liveness; the shim is the primary reaper.
7. **IAM is its own product.** K8s has RBAC as a distinct subsystem. Helioy does too: identity-matters. v1 is a near-stub; v2+ is where it gains teeth (OIDC, RBAC policies, capability resolution).

## Operating model (the runtime process topology)

```
┌────────────────────────────────────────────────────────────────────┐
│  session-matters daemon (smd)         control plane                │
│  ~10 MB | sqlite | unix socket | MCP server                        │
│  delegates IAM checks to identity-matters (library or process)     │
│  delegates spawn execution to runtime-matters (local socket)       │
└──────┬────────────────────────────────┬────────────────────────────┘
       │                                │
       │ unix socket                    │ unix socket / RPC
       │                                │
   ┌───┴────┐                ┌──────────┴────────────────────────────┐
   │ sm CLI │                │  runtime-matters daemon (rtmd)        │
   │ ephem  │                │  ~10 MB | sqlite | unix socket        │
   └────────┘                │  kqueue watchers | probe sweep        │
                             └───────────────┬────────────────────────┘
                                             │ forks
                                  ┌──────────┴──────────┐
                                  │  rtm-shim           │ (one per session)
                                  │  ~1-2 MB            │
                                  │  fork+exec runtime  │
                                  │  waitpid + report   │
                                  └──────────┬──────────┘
                                             │
                                  ┌──────────┴──────────┐
                                  │  runtime            │
                                  │  claude / codex     │
                                  │  50-200 MB          │
                                  └─────────────────────┘
```

**Three long-running processes** in v1:
- `smd` (session-matters daemon)
- `rtmd` (runtime-matters daemon)
- `rtm-shim` per running session

**Binaries:**
- `sm` — session-matters CLI + daemon binary (`sm daemon` runs smd; CLI subcommands talk to smd via socket)
- `rtm` — runtime-matters CLI + daemon binary (similar shape; `rtm daemon` runs rtmd; `rtm __shim` is internal)
- `im` — identity-matters CLI (v1 is mostly a library inside smd; binary is a thin admin CLI)
- `agm` — agent-matters CLI (manages persona configs)
- `om` — orchestration-matters CLI (controllers)
- `wm` — workflow-matters CLI (workflows; v1 deferred)
- `tm` — transport-matters CLI (independent)

Memory math: 50 sessions = ~20 MB (smd + rtmd) + 50 × 1.5 MB shims = ~95 MB total platform overhead. The runtimes themselves dwarf this.

### Why two daemons, not one

session-matters and runtime-matters are distinct concerns. Splitting them:
- Allows runtime-matters to serve other control planes in v2+ (orchestration-matters could call runtime-matters directly for non-session workloads like build jobs)
- Allows independent restart (smd crash doesn't kill rtmd-managed sessions)
- Maps cleanly to K8s' kubelet (per-node) vs apiserver (cluster-wide) split

For v1 single-host, they could co-locate; we split them at the product boundary even if a future release ships them as one binary.

## Tech stack

Rust 2024 edition. Cargo workspace per product. Pattern reference: context-matters and fmm — world-class MCP/CLI design already in production.

**Read the actual cm code, not the spec docs.** The cm spec doc at `~/.mdx/projects/context-matters-spec-mcp-server-and-tools.md` lags behind the code at `~/Dev/LLM/DEV/helioy/context-matters/`. Always validate patterns against the source.

Workspace dependencies (mirrors cm directly):
- `sqlx` 0.8 (sqlite, tokio runtime, macros, migrate)
- `tokio` 1, `futures` 0.3
- `clap` 4 derive + `clap_complete` + `clap_mangen` + `clap-markdown` + `color-print`
- `serde` + `serde_json` + `toml` 0.8
- `uuid` 1.9 with v7 feature
- `tracing` + `tracing-subscriber` (MCP servers cannot use stdout for logging — stdout is the JSON-RPC channel)
- `chrono` 0.4 with serde
- `thiserror` 2.0 (not 1.0) + `anyhow`
- `insta` for snapshot tests
- Manual JSON-RPC over stdio for MCP (no `rmcp` dependency — deliberate call as cm/fmm)

macOS-specific (for runtime-matters):
- `kqueue` crate or direct libc usage for `EVFILT_PROC` NOTE_EXIT belt-and-braces liveness

Per-crate `build.rs` (lives in `crates/<crate>/build.rs`, not workspace root) reads workspace-root `tools.toml` and generates five+ outputs:
1. `src/mcp/generated_schema.rs` — combined Rust schema constants
2. `src/mcp/generated_schema/` — per-tool JSON files (stale ones auto-removed)
3. `src/mcp/generated_instructions.rs` — MCP `initialize` instructions
4. `src/cli/generated_help.rs` — CLI `--help` text constants
5. `templates/SKILL.md` — Claude Code skill markdown
6. Workspace `README.md` — public tool documentation

The contracts driving codegen (`tool_contracts.rs`, `tool_docs.rs`, `tool_examples.rs`) are typed Rust modules at crate root, imported by `build.rs` via `#[path]`. Same types drive runtime and compile-time codegen — no string templates.

Release: cargo-dist for multi-platform binaries (7 targets: linux gnu+musl × x86_64+aarch64, darwin × x86_64+aarch64, windows msvc x86_64) with shell+powershell installers and github-attestations. release-please for changelogs and version bumps. Dedicated `[profile.dist]` inheriting `release` with `lto = "thin"`.

Build/test/install: `justfile` per project with `cargo nextest` for tests (not raw `cargo test`), separate `test-doc` for doctests.

Reference implementations (read the code):
- `~/Dev/LLM/DEV/helioy/context-matters/` — five-crate workspace (`cm-core`, `cm-store`, `cm-capabilities`, `cm-cli`, `cm-web`). Especially `crates/cm-cli/build.rs` for the codegen pipeline.
- `~/Dev/LLM/DEV/helioy/fmm/` — earlier example of the same pattern.

## What this charter does not decide

- Repository placement per product (in-place carve vs new repos; per-product decisions land in their drafts)
- Final binary name conventions (e.g., `sm` vs `smatters` vs `helioy-sm`)
- DDL per product (drafts sketch; Linear locks)
- Migration timeline from today's helioy-bus
- Order of delivery (session-matters + runtime-matters first is gating; others follow)
- Specific perf budgets

These are left to per-product Linear planning.

## What this charter does decide (subject to challenge)

1. **Seven products.** Not one bus. Not three. Not four. Each owns one K8s-mapped concern.
2. **K8s as design principle.** Pod / ServiceAccount / Namespace / kubelet / containerd-shim mappings drive the architecture.
3. **session-matters is the v1 critical path.** runtime-matters is its required peer; both ship together. identity-matters v1 is a stub. agent-matters is the persona/config product (user is handling the repo rename). orchestration-matters, workflow-matters, transport-matters are deferred.
4. **Strict-only membership.** If runtime-matters didn't spawn it, it isn't in the system. No hook-based self-registration as the primary path.
5. **Daemon + shim architecture.** runtime-matters' `rtmd` is the per-host control; tiny `rtm-shim` is the per-session reaper. Memory budget ~95 MB for 50 sessions across smd + rtmd + shims.
6. **No heartbeat protocol.** Liveness is owned by the shim's `waitpid`, belt-and-braces via daemon kqueue watchers, fallback via probe sweep.
7. **Long-lived sessions are first-class.** No time-based expiry.
8. **Two daemons, one platform.** session-matters and runtime-matters are split at the product boundary even if co-located physically.
9. **The daemons ARE the MCP servers.** Both smd and rtmd host MCP transports alongside their unix sockets.
10. **identity-matters as separate product.** IAM is not embedded in session-matters; it's called into. v1 is a near-stub; v2+ adds teeth.
11. **Rust 2024 edition.** Cargo workspace per product. cm/fmm patterns mirrored. Go was considered and declined for ecosystem consistency.
12. **The earlier helioy-bus CLI design doc is superseded as a product framing.** Salvageable as feature material.

## Related artifacts

- Brainstorm sessions: 2026-05-16 and 2026-05-17. Recoverable from cm at scope `global/project:helioy` with tags `helioy-bus`, `k8s`, `daemon-shim`, `session-matters`.
- Per-product drafts in this directory:
  - `agent-matters-config-draft.md` (TBD — the user owns the rename of the existing runtime-matters repo)
  - `identity-matters-iam-draft.md` (stub for v1)
  - `session-matters-foundation-draft.md` (v1 draft spec, ready for `/linear-workflows`)
  - `runtime-matters-kubelet-draft.md` (v1 draft spec, ready for `/linear-workflows`)
  - `orchestration-matters-controllers-draft.md` (v1 draft spec; references updated to new names)
  - `workflow-matters-choreography-draft.md` (early sketch, deferred)
- Earlier helioy-bus CLI design (superseded as framing): `helioy-bus/docs/superpowers/specs/2026-05-16-helioy-bus-cli-design.md`. CLI shape may inform session-matters v1; product framing is no longer current.
- Plugin re-sync companion spec (still valid, retargets once session-matters CLI ships): `helioy-plugins/docs/superpowers/specs/2026-05-16-plugin-resync-script-design.md`
- Tech-stack reference: `~/Dev/LLM/DEV/helioy/context-matters/Cargo.toml`, `~/.mdx/projects/context-matters-spec-mcp-server-and-tools.md`
