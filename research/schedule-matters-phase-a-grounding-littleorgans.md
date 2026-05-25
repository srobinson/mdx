---
title: schedule-matters Phase A Grounding for littleorgans
type: research
tags: [littleorgans, schedule-matters, phase-a, spec, tmux, session-matters, runtime-matters]
summary: Grounding notes for the Phase A schedule-matters spec, now written and awaiting Phase B review.
status: active
source: codebase-analyst
confidence: medium
created: 2026-05-31
updated: 2026-05-31
---

## Executive Summary

schedule-matters is the greenfield placement substrate for littleorgans. The Phase A outline positions it as the kube-scheduler analogue: sole owner of tmux session, window, pane placement and occupant bindings, while reusing session-matters primitives and runtime-matters launch APIs.

A compact D outline was sent to the reviewer on bus topic `schedule-spec`. The output spec at `/Users/alphab/.mdx/projects/littleorgans-schedule-matters-spec.md` has not been written yet because the protocol requires Phase A sign-off first.

## Project Metadata

- Language: Rust monorepo.
- Structural index: fmm was available and used first. Topology summary: 365 indexed files, 48,763 LOC. `internal/` has 293 files and 37,624 LOC. `crates/` has 67 files and 9,694 LOC.
- Build system: repo instructions identify Cargo as Rust source of truth, Moon for CI orchestration, and `just check && just build && just test` as the standard proof gate.
- Relevant existing components: `internal/session/{app,core,daemon,driver,store}`, `internal/runtime`, `internal/{wire,port}`, `crates/lilo`, `crates/lilo-rm-core`.

## Architecture

### Boundary

schedule-matters should be a new internal substrate. It owns multiplexing and placement only: tmux sessions, windows, panes, reconciliation, and occupant bindings. The cockpit architecture states that schedule-matters owns multiplexing and that `lilo create session` becomes declarative apply while `lilo run` becomes imperative create and place once scheduling lands (`littleorgans-cockpit-architecture.md:126-157`).

It must not implement message passing, nudge, capture, transcript streaming, runtime launch internals, or workflow policy. The build plan says Phase 1 builds on existing runtime spawn, nudge, capture, and lilod reconcile/lifecycle patterns (`littleorgans-build-plan.md:59-84`).

### Existing primitives to reuse

- CLI dispatch already routes public commands through session handling: `crates/lilo/src/cli/mod.rs:50-82` routes `run`, `create`, `get`, `delete`, `label`, `mail`, `nudge`, `capture`, `logs`, `wait`, and `mcp` into session commands.
- The session RPC enum already carries `Spawn`, `List`, `Delete`, `MailSend`, `MailRead`, `MailCheck`, `Nudge`, `Label`, `Logs`, `Capture`, `Doctor`, and `Wait` (`internal/session/core/src/proto/rpc.rs:16-36`).
- `RuntimePort` already exposes the substrate seam schedule-matters should use: spawn, reap, capture, terminate, nudge, status, poll events, doctor, and terminate all (`internal/session/driver/src/port.rs:18-53`).
- `SpawnLaunch` already models the launch request to runtime with runtime, isolation, image, cwd, target, env, mounts, shell resume, and force (`internal/session/driver/src/driver.rs:21-31`).

### Current cutover point

Today `lilo run` calls `spawn_session` with the target from the CLI, while `lilo create session` calls the same function with a headless target (`internal/session/app/src/cli/run.rs:15-39`). `spawn_session` sends `SessionRpc::Spawn` with `SpawnRequest` to the daemon (`internal/session/app/src/cli/run.rs:64-85`). schedule-matters should replace that direct spawn path with mediated placement.

### Storage shape

Use SQLite, modeled on the existing session store. `SqliteStore` wraps `SqlitePool` and exposes open helpers (`internal/session/store/src/sqlite.rs:22-47`). Existing spawn intents show the pattern for draft plus runtime request persistence: `SessionDraft`, `PendingSpawnIntent`, `SessionSpawnIntent`, and `SpawnIntentStatus` (`internal/session/store/src/sqlite/spawn_intents.rs:37-167`).

The manifest and topology snapshot should use a versioned payload migration pattern, not a JSON-only storage model. The herdr review specifically recommends borrowing `SNAPSHOT_VERSION`, `serde(default)`, and legacy migration while keeping SQLite as the locked storage engine (`ogulcancelik-herdr.md:61-63`, `:98`).

## Key Patterns

1. **Durable id first.** Store schedule-owned pane UIDs and bind them to live tmux `%pane_id` values. Derive positional `s:w.p` for display only. The architecture explicitly forbids binding to positional addresses because tmux renumbers them (`littleorgans-cockpit-architecture.md:163-183`).
2. **Mechanism over policy.** schedule-matters emits `orphaned(token)` on pane death and stops. Restart decisions live above it (`littleorgans-cockpit-architecture.md:185-210`).
3. **JSON control, separate stream.** wire carries control JSON, while transport-matters owns the framed transcript stream. The dual-socket rule is grounded in the cockpit doc and corroborated by herdr (`littleorgans-cockpit-architecture.md:118-122`, `ogulcancelik-herdr.md:51`, `:93`).
4. **Pull now, subscribe later.** Phase 1 should expose wait style event access first. Existing `WaitRequest` and `WaitResponse` provide the local shape (`internal/session/core/src/proto/session.rs:63-67`, `:101-104`), and herdr validates wait as the simple primitive before subscribe (`ogulcancelik-herdr.md:57`, `:97`).

## Detailed Findings

### Proposed Phase A partition

- schedule-matters: placement, tmux topology, pane identity, occupant binding, reconciliation, and placement events.
- session-matters: durable agent identity, logical session records, labels/selectors, mail, nudge, capture, logs, wait.
- runtime-matters: process launch, shim behavior, lifecycle, raw runtime status, tmux-backed runtime target execution.
- wire: JSON control envelope.
- transport-matters: high bandwidth transcript stream and observation channel.

### Proposed key types

- `ScheduleSessionUid`, `ScheduleWindowUid`, `SchedulePaneUid`: durable schedule ids.
- `TmuxSessionId`, `TmuxWindowId`, `TmuxPaneId`: live realization ids.
- `PositionalAddress`: derived display value only.
- `OccupantToken`: opaque session-matters identity bound to a schedule pane UID.
- `ThinSessionManifest`: identity plus topology only, with workspace keyed by repo directory or cwd, windows, panes, CLI per pane, repo and cwd.
- `PaneBinding`: pane UID, occupant token, live tmux pane id, state, and last seen timestamp.
- `ScheduleEvent`: `orphaned(token)`, `placed(token, pane_uid)`, `pane_closed(pane_uid)`.
- `RestartPolicy` seam: Phase 1 implements Never behavior and stubs the Always/resume hook for later orchestration work.

### Proposed JSON control verbs

- `session.create`: apply `ThinSessionManifest`, create tmux topology, place occupants.
- `session.get`, `session.list`, `session.delete`: inspect or remove schedule-owned topology and bindings.
- `pane.create`, `pane.split`, `pane.place`: materialize and bind panes by schedule ids.
- `pane.read`: delegate to existing capture path.
- `pane.send_text`, `pane.send_keys`: use session primitives when semantic, raw tmux only for operator pane control.
- `pane.close`: close the pane, update binding state, emit an event.
- `pane.wait_for_output`: pull primitive shaped like existing wait and capture behavior.
- `events.wait`: Phase 1 event access.
- `events.subscribe`: later strict superset.

### Reviewer protocol status

- Received bus directive on topic `schedule-spec` assigning DRAFTER role.
- Read the required architecture, build plan, herdr research, and fmm structural code context.
- Sent compact D outline to reviewer `littleorgans:helioy-tools:codebase-analyst:9:4.1`.
- Sent M milestone to `helioy:orchestrator`.
- Polled topic `schedule-spec` once after sending. No Phase A sign-off message was available yet.

## Dependencies

Critical dependencies are existing project components rather than third party crates for this phase:

- `internal/session/core`: typed RPC and session records.
- `internal/session/app`: CLI implementation for run, create, mail, nudge, capture, wait.
- `internal/session/daemon`: lilod service, reconciliation, lifecycle, runtime event loop.
- `internal/session/store`: SQLite patterns for sessions and spawn intents.
- `internal/session/driver`: runtime port seam.
- `crates/lilo-rm-core`: runtime types, lifecycle, spawn request, capture and nudge contracts.
- `internal/wire`: control envelope namespace, currently `LilodRpc::Session` and `LilodRpc::Runtime` (`internal/wire/src/lib.rs:5-8`).

## Relevance to Helioy

This spec is the first control-track phase toward the local K8s-shaped platform. The design keeps the Helioy matters family separated: schedule-matters handles placement, session-matters handles durable identity and primitives, runtime-matters handles host execution, orchestration-matters handles policy, and workflow-matters handles DAG flow.

## Phase A Review Round 2

Reviewer blocked the first outline on two issues. First, the outline said schedule should call existing runtime spawn, but did not assign tmux topology creation to a concrete layer. Verification confirmed `RuntimePort` has launch and primitive methods but no session, window, or pane creation method (`internal/session/driver/src/port.rs:18-53`). Runtime spawn requires a pre-existing pane: `SpawnCoordinator::validate_target` checks `TmuxGateway::is_alive` and returns `tmux_pane_dead` when absent (`internal/runtime/daemon/src/server/spawn.rs:104-119`). The existing tmux execution surface is centralized in `TmuxGateway`, which owns `nudge`, `respawn_pane`, `is_alive`, and `capture_pane` (`internal/runtime/platform/src/tmux.rs:19-114`).

The corrected design assigns decisions to schedule-matters and tmux execution to runtime/platform. schedule-matters should extend the existing runtime tmux layer through a new runtime topology seam, for example `RuntimeRpc` plus `RuntimePort` topology methods or a `TmuxTopologyPort`. The runtime topology responses must return stable tmux ids, `$session_id`, `@window_id`, and `%pane_id`, plus any derived display position. schedule creates desired topology, receives live ids, binds `SchedulePaneUid` to `%pane_id`, then invokes existing runtime spawn into that pane.

Second, the outline used bare `session.*` and `pane.*` verbs without accounting for the control envelope. Verification showed `LilodRpc` currently has `Session(SessionRpc)` and `Runtime(RuntimeRpc)` (`internal/wire/src/lib.rs:5-8`). The corrected design adds a third substrate, `LilodRpc::Schedule(ScheduleRpc)`. User-facing `lilo create session` remains session-backed, then files or forwards a manifest to `ScheduleRpc::ApplyManifest`. Explicit operator access adds `lilo schedule ...` beside runtime, session, and identity.

The minor correction clarifies that CLI, argv, env, repo, cwd, and role/config identity are opaque launch payload and topology intent in the thin manifest. schedule validates topology and placement only. It does not interpret agent meaning, role behavior, prompts, transcripts, or policy.

D2 was sent to reviewer on bus topic `schedule-spec`. A milestone was sent to `helioy:orchestrator`. Phase A sign-off remains pending.

## Phase A Sign-off and Spec Write

Reviewer `littleorgans:helioy-tools:codebase-analyst:9:4.1` signed off Phase A with: `I sign off on the proposed schedule-matters spec design as filed.` The full spec was written to `/Users/alphab/.mdx/projects/littleorgans-schedule-matters-spec.md` and `C` was sent to the reviewer. A milestone was sent to `helioy:orchestrator`.

The written spec folds in the three Phase A non-blocking review items:

1. Reconciler liveness uses existing runtime signals, specifically `RuntimePort::poll_events/status` and `RuntimeRpc::Events/Status`, rather than a parallel schedule-owned per-pane `is_alive` poller.
2. Schedule SQLite tables live in shared `~/.lilo/data/lilo.db`, modeled on the existing `SqliteStore` plus per-table module pattern.
3. Spawn target validation cites the exact symbol `SpawnCoordinator::validate_target` at `internal/runtime/daemon/src/server/spawn.rs:104-119`.

The file had 420 lines after initial write and zero em dash characters after verification. Phase B response was not available after a short poll on topic `schedule-spec`.

## Open Questions

1. Reviewer Phase A sign-off is pending.
2. The exact Rust crate layout for schedule-matters is not yet selected. The docs only say it is greenfield and reserved.
3. The manifest field-level schema remains open in the cockpit architecture (`littleorgans-cockpit-architecture.md:397`).
4. The exact event persistence shape for schedule events should be aligned with existing session events before implementation.
5. The raw tmux command adapter shape requires implementation research, but the invariant is already settled: never store positional addresses.
