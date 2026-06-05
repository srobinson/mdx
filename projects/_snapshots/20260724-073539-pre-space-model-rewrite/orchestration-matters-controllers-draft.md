---
title: orchestration-matters v1 draft spec
type: projects
tags: [orchestration-matters, om, rewrite, controllers, lifecycle, warroom, k8s, rust, mcp, cli, draft]
summary: Controllers layer above session-matters. Owns spawn policy / kill / restart / declarative agent state. Warroom is the first controller pattern. Spawns via session-matters' API (not directly via runtime-matters). Rust workspace mirroring cm patterns. Draft spec ready for /linear-workflows once session-matters + runtime-matters land.
status: draft
project: orchestration-matters
confidence: low
created: 2026-05-16
updated: 2026-05-17
related: [helioy-bus-rewrite-charter-draft, session-matters-foundation-draft, runtime-matters-kubelet-draft, agent-matters-config-draft, workflow-matters-choreography-draft]
---

# orchestration-matters v1 draft spec

## Draft caveat

Brainstorm artifact for `/linear-workflows` consumption. Lower confidence than the session-matters and runtime-matters specs because controller design was sketched, not deeply explored. Linear planning may rescope freely and the deeper focused dive should resolve the open questions in flight. The architecture position is settled (between session-matters and workflow-matters); the design surface is sketch.

Naming note: this product was always called `orchestration-matters`; only the products below it have renamed (the former `identity-matters` is now `session-matters`; the former `runtime-matters` persona/config product is now `agent-matters`; the new `runtime-matters` is the per-host kubelet).

## Summary

Controllers layer above session-matters. Spawns agents, manages their lifecycle, holds declarative state about what should be running. Acts as supervisor for spawned agents by setting `supervisor_id` on session records via session-matters' spawn API. Consumes agent-matters configs at spawn time (sibling consumer relationship, not a layered dependency).

Rust 2024 Cargo workspace mirroring cm. MCP + CLI via single binary `om`.

Warroom is the first controller pattern in v1. Other patterns (Daemon, Job, Replicated) are roadmap; the v1 abstraction must not preclude them.

## Motivation

The existing warroom in helioy-bus conflates a single controller pattern with the bus substrate. Carving it out makes the controller-substrate boundary explicit and lets other patterns plug in without changing session-matters or runtime-matters.

Today's warroom works. The rewrite is about giving it a proper home and making the seam to session-matters clean (spawn API + supervisor wiring). It is also the layer that will absorb future controller patterns as the agent fleet grows.

## K8s mapping

| K8s concept | orchestration-matters mapping |
|---|---|
| Controllers (Deployment, Job, DaemonSet, ReplicaSet) | orchestration-matters controllers (Warroom v1; Daemon/Job/Replicated roadmap) |
| Controller manager | `omd` (orchestration-matters daemon; or in-process per controller pattern) |
| Reconciliation loop | v1 reacts to operator commands only; v2+ adds continuous reconciliation |
| Owner references (OwnerRef) | `supervisor_id` field on session records, set at spawn time |

## Goals

1. **Clear seam between "what should be" (orchestration-matters) and "what is" (session-matters).** Controllers declare desired state; session-matters reports observed state.
2. **Pluggable controller pattern abstraction.** Warroom is the first; other patterns must slot in without reshaping the substrate.
3. **First-class supervisor for spawned agents.** Sets `supervisor_id` on the session record at spawn; receives lifecycle notifications when supervised agents die.
4. **Consumes agent-matters configs declaratively.** At spawn time, orchestration-matters takes an agent-matters config name and passes it to session-matters' `sm run --agent-config`.
5. **Same tech stack and codegen pattern as session-matters.** Rust + tools.toml.

## Non-goals

- Live sessions, channels, selectors (session-matters)
- IAM, AuthZ, audit (identity-matters)
- Per-host substrate primitives, kqueue, waitpid, tmux gateway (runtime-matters)
- Workflow choreography (workflow-matters)
- Agent persona / CLAUDE_CONFIG_DIR definitions (agent-matters)
- More than one controller pattern in v1 (warroom only)
- Cross-machine spawning
- Multi-controller composition (deferred to workflow-matters)

## Domain model

### Controller

An object that owns declarative state about a group of agents and reconciles that state by spawning, killing, or modifying agents through session-matters.

```
controller := {
  id:                UUIDv7
  kind:              "warroom" (v1; other kinds in roadmap)
  desired_state:     pattern-specific (e.g., warroom: agent list + tmux layout)
  spawned_session_ids: [session_id, ...]   sessions spawned via session-matters
  workspace:         string
  labels:            { ... }
  created_at:        timestamp
}
```

### Warroom (v1 controller pattern)

Today's `warroom_spawn` semantics, preserved:
- Named group of agents in a tmux window
- Each agent runs a specific runtime + role + agent-matters config
- Group lifecycle: spawn, kill, add member, remove member
- Presets: saved group configurations

New in v1:
- Each spawned agent's session record (in session-matters) has `supervisor_id` set to the warroom's controller id
- When the warroom is killed, orchestration-matters issues `sm delete agent` for each spawned session
- Group operations use session-matters label selectors (e.g., `label:controller_id=<id>`)
- Spawn parameters derived from agent-matters configs (per agent)

### Controller patterns (roadmap, not v1)

| Pattern | Kubernetes analog | Behavior |
|---|---|---|
| Daemon | DaemonSet | One agent per matching workspace (e.g., one Nancy-eng per repo in `helioy/`) |
| Job | Job | Spawn agent, run task, garbage-collect on completion |
| Replicated | Deployment | Always N agents matching label X |

v1 must not preclude these. The controller trait + storage layout must accommodate them as plugins.

## v1 scope

| In scope | Out of scope |
|---|---|
| Warroom controller (spawn / kill / status / discover / add / remove / presets) | Daemon, Job, Replicated controllers |
| Sets session-matters' `supervisor_id` at spawn time | Push-based supervisor protocol (v1 uses mail notifications) |
| Group state persistence (`controllers`, `controller_members` tables in om-store) | Cross-machine spawning |
| MCP server + CLI (single `om` binary) | Web UI |
| Consumes agent-matters configs at spawn time (via `sm run --agent-config`) | Generating agent-matters configs (that's agent-matters' job) |
| Label-based group operations via session-matters selectors | Auto-reconciliation loop (v1 reacts to operator commands; continuous loop deferred) |
| Migration of today's warroom_* MCP tools | Backward-compat with helioy-bus's MCP tool names (clean break) |

## Tech stack

Same as session-matters. See [session-matters-foundation-draft](session-matters-foundation-draft.md#tech-stack) for the full workspace dependencies, release profiles, cargo-dist configuration, and reference-implementation pointers.

In short: Rust 2024, Cargo workspace, sqlx + sqlite, tokio, clap (with complete + mangen + markdown), color-print, tracing, uuid v7, chrono, insta, thiserror 2.0, anyhow. Manual JSON-RPC over stdio for MCP (no rmcp). `tools.toml` at workspace root + per-crate `build.rs`. cargo-dist + release-please. `justfile` + `cargo nextest`.

Read the actual cm code at `~/Dev/LLM/DEV/helioy/context-matters/` rather than relying on docs.

## Proposed Cargo workspace

Mirrors session-matters' layout exactly (which in turn mirrors cm). See [session-matters-foundation-draft → Proposed Cargo workspace](session-matters-foundation-draft.md#proposed-cargo-workspace). Differences:

```
orchestration-matters/
├── Cargo.toml, Cargo.lock, tools.toml, justfile, AGENTS.md, CLAUDE.md, LESSONS.md, PROJECT.md, CHANGELOG.md
├── crates/
│   ├── om-core/                     Controller trait + Warroom domain types
│   ├── om-store/                    sqlx + sqlite for controller state (with sqlite/ submodule)
│   ├── om-controllers/              warroom impl; trait dispatch for future patterns
│   └── om-cli/                      CLI + MCP siblings, single `om` binary
│       ├── build.rs                 reads ../../tools.toml; emits 5+ codegen outputs
│       └── src/
│           ├── lib.rs, main.rs, shared.rs
│           ├── tool_contracts.rs, tool_docs.rs, tool_examples.rs
│           ├── cli/                 clap subcommands
│           ├── mcp/                 stdio JSON-RPC server
│           └── templates/SKILL.md   GEN
└── tests/
```

No `om-runtime` or `om-platform` crate — substrate primitives live in runtime-matters and are accessed indirectly (orchestration-matters never talks to rtmd directly; it goes through session-matters).

## MCP / CLI surface (sketch — kubectl-shaped where it makes sense)

Single binary `om`.

```
om
├── warroom
│   ├── spawn --name <name> --agents <list> [--workspace <path>] [--layout <name>] [--agent-config <name>]
│   ├── kill --name <name>
│   ├── status [--name <name>]
│   ├── discover                     list spawnable patterns + presets
│   ├── add --warroom <name> --agent <id-or-spec>
│   ├── remove --warroom <name> --member <session-id>
│   ├── presets list
│   └── presets save --name <name> --from <warroom-name>
├── get controllers                  kubectl-style list
├── get controller <selector>        single detail
├── delete controller <selector>     kill + cleanup
├── serve                            start MCP server on stdio
├── initdb                           init/migrate controller db
└── completions <shell>
```

All output supports `--json`. `::` and space-separated forms both route via argv rewrite.

`om warroom spawn` internally invokes `sm run` per member (or batch RPC if session-matters supports it), setting `--supervisor <warroom-id>` and `--agent-config <name>`.

## Boundary contracts

### orchestration-matters → session-matters (spawn)

orchestration-matters does not talk to runtime-matters directly. To spawn an agent, it calls session-matters' API:

```rust
// via sm CLI invocation or future programmatic API
sm_client.run(SpawnSpec {
    runtime: agent_spec.runtime,
    role: agent_spec.role,
    workspace,
    agent_config: agent_spec.config_name,
    supervisor_id: Some(warroom.controller_id),
    labels: hashmap! { "controller_id" => warroom.controller_id.to_string() },
    ...
})
```

### orchestration-matters ← session-matters (lifecycle notifications)

When a spawned agent dies, session-matters sends mail to the controller's id (via the `supervisor_id` recorded on the session record). orchestration-matters' daemon (or controller process) consumes that mail and updates its desired-state view.

## Migration from helioy-bus

| helioy-bus surface | orchestration-matters surface |
|---|---|
| `warrooms` table | `controllers` table (typed as kind=warroom); carve into om-store |
| `warroom_members` table | `controller_members` (with session_id pointing into session-matters); carve into om-store |
| MCP `warroom_spawn` | `om warroom spawn` + MCP tool (internally calls `sm run` per member) |
| MCP `warroom_kill` | `om warroom kill` + MCP tool |
| MCP `warroom_status` | `om warroom status` + MCP tool |
| MCP `warroom_discover`, `warroom_spawn_repos` | absorbed into `om warroom discover` (v1) or split (Linear's call) |
| MCP `warroom_add`, `warroom_remove` | `om warroom add` / `om warroom remove` |
| MCP `warroom_presets`, `warroom_save_preset` | `om warroom presets list` / `om warroom presets save` |
| `server/warroom_cli.py` (hand-rolled) | replaced by `om` clap CLI |

Each spawned agent's `supervisor_id` is set to the warroom's controller id (a column in `controllers`). session-matters routes mail to the warroom when the spawned agent terminates.

## Dependencies

External (Rust ecosystem): sqlx, tokio, clap, serde, thiserror, anyhow.

System: `tmux` (required for warroom; controllers in general assume tmux until v2 introduces non-tmux runtimes).

Internal:
- **session-matters** (required at runtime; om spawns through `sm run`; receives lifecycle notifications via mail to `supervisor_id`)
- **agent-matters** (required at spawn; om passes `--agent-config` to session-matters; agent-matters resolves it to spawn params)
- **runtime-matters** (transitive only, through session-matters)
- **identity-matters** (transitive only, through session-matters)

## Open questions for Linear planning

1. **Repository placement.** New repo `~/Dev/LLM/DEV/helioy/orchestration-matters/`? Or co-located with session-matters for v1?
2. **Binary name.** `om`? `orch`? Family convention.
3. **Spawn semantics.** Block until session-matters reports RUNNING for every member, or fire-and-forget with eventual consistency? Affects retry / error handling.
4. **Reconciliation model.** Continuous loop (like K8s) or react-only-to-operator-commands? v1 leans react-only; v2 could add a reconciler.
5. **agent-matters integration.** How does the config flow? Pass an agent-matters config name to `sm run --agent-config`? sm-via-om resolves it? Or om resolves and passes spawn params directly?
6. **Persistence layout.** Own store (om-store) or shared with session-matters? v1 leans own store.
7. **Multi-controller composition.** When workflow-matters wants to spawn through an orchestration-matters controller, what's the supervisor? Deferred to workflow-matters v1.
8. **Preset format.** Today's presets are JSON blobs in the bus DB. Migrate as-is, or restructure?
9. **Warroom MCP tool naming.** Preserve `warroom_*` names, or rename consistently (e.g., `controller_warroom_spawn`)?
10. **Daemon vs CLI-only.** Does om have its own long-running daemon (omd) for reconciliation? v1 could be CLI-only (no reconciler); v2+ adds daemon.

## Success criteria

1. All current `warroom_*` MCP consumers can migrate with config changes only.
2. Session-matters' supervisor wiring is exercised end-to-end: warroom spawns agent → session-matters records supervisor_id → on agent death → mail to supervisor.
3. Spawning a warroom fully populates session records via `sm run` (no missing fields).
4. `tools.toml` is the single source of truth for MCP / CLI / skill docs.
5. Controller trait is generic enough that adding a second controller pattern (e.g., Daemon) does not require om-core changes.
6. om's CLI feels native to operators familiar with the existing `warroom_cli.py`.

## Parent + sub-issue shape (for /linear-workflows)

**Parent:** "orchestration-matters v1: controller layer carve-out, warroom as first pattern"

**Sub-issues (suggested):**
1. Cargo workspace scaffold + tools.toml + build.rs codegen
2. `om-core`: Controller trait + Warroom domain types
3. `om-store`: sqlx schema for controllers + controller_members + migrations
4. `om-controllers`: warroom impl
5. `om-cli`: clap subcommands + MCP server
6. Session-matters integration: spawn via `sm run`; consume lifecycle notifications via mail
7. Agent-matters integration: pass --agent-config; resolve via session-matters
8. Migration: carve warroom out of helioy-bus, port presets, update hooks
9. Integration tests with session-matters + runtime-matters running
10. Doctor surface: list controllers and their declared vs observed state

## Related

- Charter: `helioy-bus-rewrite-charter-draft.md`
- Below (required dependency): `session-matters-foundation-draft.md`
- Below (required dependency, transitively): `runtime-matters-kubelet-draft.md`
- Below (required dependency, transitively): `identity-matters-iam-draft.md`
- Above: `workflow-matters-choreography-draft.md`
- Sibling consumer: agent-matters (the persona/config product; the user is renaming the existing runtime-matters repo)
- Tech reference: `context-matters-spec-mcp-server-and-tools.md`
