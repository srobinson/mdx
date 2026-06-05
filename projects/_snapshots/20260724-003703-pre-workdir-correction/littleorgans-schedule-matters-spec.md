# littleorgans schedule-matters Phase 1 spec

Status: round-1 + round-2 MoE consensus applied; ready for Phase B sign-off
Updated: 2026-05-31
Owner: schedule-matters spec (MoE drafted + peer reviewed)

## 1. Purpose and boundaries

schedule-matters is the local placement substrate for littleorgans. As the kube-scheduler analogue in the matters family, it decides where occupants go, owns tmux session, window, and pane topology, and records the durable placement binding. The v1 target is local tmux. The v2 contract is a schedulable topology manifest that can later map to pods without changing producer intent.

schedule-matters is the sole placement authority. Once this phase lands, no user or system path places an agent into a pane except schedule-matters, declarative or imperative. The current direct spawn path is interim. Today `lilo run` calls `spawn_session` with the requested target, and `lilo create session` calls the same `spawn_session` helper with `headless` (`internal/session/app/src/cli/run.rs:15-39`). The cutover replaces that direct spawn route with mediated placement.

schedule-matters owns:

1. Desired tmux topology for a scheduled unit: sessions, windows, panes.
2. Durable schedule ids for sessions, windows, and panes.
3. Occupant token to pane UID bindings.
4. Reconciliation between desired topology (including each occupant's declared `restartPolicy`), live tmux ids, runtime liveness, and stored bindings, including re-placement of `Always` occupants on pane death.
5. Placement events such as `orphaned(token)`.

schedule-matters does not own:

1. Durable agent meaning, roles, labels, selectors, or mailboxes. Those stay in session-matters. (`restartPolicy` is a declared per-occupant manifest field that schedule reconciles per §6, not a judgment schedule authors.)
2. Process launch internals, shim behavior, lifecycle state, raw status, or tmux command execution. Those stay in runtime-matters.
3. Transcript streaming or high bandwidth observation. That stays in transport-matters.
4. Workflow, orchestration policy, or controller decisions after a pane dies. Those stay above schedule-matters.
5. Security, auth policy, or role compilation. Those stay in identity-matters and agent-matters.

The boundary is reconciliation of declared intent, not authorship of it. If a pane dies, schedule-matters reads the occupant's declared `restartPolicy`: `Never` reports the orphaned occupant and stops; `Always` re-places and relaunches through the native resume mechanism; `OnFailure` does so only on terminal failure evidence (nonzero exit code or signal). The orchestrator authored that intent in the manifest; schedule does not re-decide it. Restart logic beyond a static policy (backoff, max-retries, replace-with-a-different-role) stays in a higher layer.

## 2. Data model

### 2.1 Stable identity ladder

The schedule identity ladder is:

```text
occupant token              opaque identity from session-matters
  bound to
schedule pane UID           durable id in schedule SQLite tables
  currently realized as
live tmux %pane_id          stable during a tmux server lifetime
  displayed as
positional s:w.p            derived for humans, never stored as authority
```

`TmuxAddress` today stores `session`, `window`, and `pane` as positional components (`crates/lilo-rm-core/src/types/spawn.rs:12-16`). Phase 1 must replace that as schedule authority. Positional `s:w.p` can appear in CLI output, debug output, logs, and compatibility fields, but schedule persistence and lookup must use schedule UIDs and live tmux ids. Window insert, delete, and renumber must not change any occupant binding.

### 2.2 Core records

Schedule tables live in the shared `~/.lilo/data/lilo.db` database, under `LILO_HOME` when set. This follows the existing `SqliteStore` pattern, which wraps a substrate pool from `LiloDb` (`internal/session/store/src/sqlite.rs:22-47`). Phase 1 adds `LiloDb::schedule_pool()` as a named accessor over the single shared `SqlitePool`. `LiloDb` holds one pool field, and `identity_pool`, `session_pool`, and `runtime_pool` all return that same `&self.pool` (`internal/db/src/lib.rs:16-18,58-68`; the unified-schema test confirms one database). `schedule_pool()` is a fourth named alias over that shared pool, not a separate pool; keep the single unified `~/.lilo/data/lilo.db`. The implementation should use per-table modules under a schedule store, mirroring `internal/session/store/src/sqlite/{sessions,spawn_intents,...}.rs`.

Core records:

| Record | Fields | Notes |
|---|---|---|
| `ScheduleSession` | `schedule_session_uid`, `manifest_id`, `workspace_key`, `desired_snapshot`, `status`, timestamps | One applied topology unit. `workspace_key` is repo dir or cwd identity. |
| `ScheduleWindow` | `schedule_window_uid`, `schedule_session_uid`, `name`, `ordinal_hint`, `live_tmux_window_id`, timestamps | `ordinal_hint` is display preference, not identity. |
| `SchedulePane` | `schedule_pane_uid`, `schedule_window_uid`, `occupant_hint`, `cwd`, `launch_payload`, `live_tmux_pane_id`, `display_position`, `status`, timestamps | `occupant_hint` is opaque display metadata only; role stays inside the opaque launch payload (blindness rule). `display_position` is cached output only and can be recomputed. |
| `OccupantBinding` | `occupant_token`, `schedule_pane_uid`, `session_id`, `native_resume_ref`, `restart_policy`, `state`, timestamps | The authoritative occupant to pane mapping. `session_id` is the logical lilo session join key (a UUIDv7), not a CLI resume token. `native_resume_ref` is the runtime-captured native resume identity or argv used to relaunch the occupant on restart (§4.3), distinct from `session_id`. `restart_policy` is the declared intent reconciled on pane death (§4.3). |
| `ScheduleEvent` | `event_id`, `schedule_session_uid`, `schedule_pane_uid`, `occupant_token`, `kind`, `payload`, timestamps | Pull first. Subscribe later. |

The occupant token is opaque to schedule-matters. If it corresponds to a session-matters record, schedule stores the join key but does not interpret role, agent type, transcript, or restart policy.

### 2.3 Thin session manifest

The thin session manifest is the Phase 1 proto-CRD. It carries identity plus topology only. It does not carry workflow, coordination, or policy.

Required shape:

```text
manifest_version
metadata:
  name
  labels
workspace:
  key                  # canonical repo dir or cwd
  cwd
windows:
  - uid_hint
    name
    panes:
      - uid_hint
        occupant_token
        restartPolicy        # Never | OnFailure | Always, declared by the orchestrator
        cwd
        launch:
          runtime
          argv
          env
          mounts
          image
          role_or_config_ref
```

`launch` is an opaque pass-through payload. schedule-matters validates that the payload is present and attachable to a pane. It never interprets agent behavior, prompts, role policy, transcript semantics, or CLI-specific config. This preserves the rule that schedule-matters is blind to consumers and to what the agent is. The per-occupant `restartPolicy` is declared lifecycle intent, not agent semantics; schedule reconciles it on pane death (§4.3) without interpreting what the agent is, so blindness holds.

The manifest is stored as a versioned snapshot payload inside SQLite, not as a separate database file. Borrow the migration pattern from herdr only at the schema evolution layer: `SNAPSHOT_VERSION`, `serde(default)`, and explicit legacy migration. Keep SQLite as the storage engine.

### 2.4 Versioned snapshot contract

Each stored manifest and realized topology snapshot has:

```text
SNAPSHOT_VERSION: u32
schema: schedule_manifest_v1 | schedule_topology_v1
payload: serde JSON payload
migrated_from: optional prior version
```

Rules:

1. New optional fields use `serde(default)`.
2. Breaking payload changes add a migrator from the prior version.
3. Schedule code reads legacy snapshots through one decode path.
4. Tests cover the current version and at least one legacy sample once a migration exists.

Existing session store patterns for persisted draft plus runtime request are visible in `SessionDraft`, `PendingSpawnIntent`, and `SessionSpawnIntent` (`internal/session/store/src/sqlite/spawn_intents.rs:67-167`). schedule should mirror that style rather than introduce a second persistence idiom.

## 3. Verb and API contract over wire

### 3.1 Substrate envelope

The control envelope is substrate tagged. Today `LilodRpc` has `Session(SessionRpc)` and `Runtime(RuntimeRpc)` (`internal/wire/src/lib.rs:5-8`). Phase 1 adds a third substrate:

```rust
pub enum LilodRpc {
    Session(lilo_session_core::SessionRpc),
    Runtime(lilo_rm_core::RuntimeRpc),
    Schedule(lilo_schedule_core::ScheduleRpc),
}
```

Schedule verbs are schedule-scoped. If a future method string layer is added, names render as `schedule.session.create`, `schedule.pane.split`, and `schedule.events.wait`, not as unqualified `session.*` or `pane.*`. This avoids collision with session-matters, which already owns `SessionRpc` variants for spawn, namespace operations, delete, mail, nudge, capture, wait, and MCP bridge (`internal/session/core/src/proto/rpc.rs:16-36`).

User-facing `lilo create session` remains a session-backed path. After cutover, the session app files or forwards the thin manifest to `ScheduleRpc::SessionCreate`, whose operation is declarative manifest apply. Explicit substrate access adds `lilo schedule ...` beside existing operator namespaces such as runtime, session, and identity.

The new `lilo-schedule-core` crate, the new neutral runtime-port crate (§7.2), and the `internal/schedule/*` members require workspace wiring before code lands: a `[workspace] members` glob for `internal/schedule/*`, a members entry for the new runtime-port crate, matching `[workspace.dependencies]` entries, and a `wire → lilo-schedule-core` dependency so the envelope can name `ScheduleRpc`.

### 3.2 Runtime topology seam

runtime-matters already owns tmux execution. `TmuxGateway` centralizes tmux calls for nudge, respawn, liveness, and capture (`internal/runtime/platform/src/tmux.rs:19-114`). Runtime spawn does not create topology. It validates that a tmux target already exists through `SpawnCoordinator::validate_target`, which calls `TmuxGateway::is_alive` and returns `tmux_pane_dead` for absent panes (`internal/runtime/daemon/src/server/spawn.rs:104-119`).

Phase 1 therefore adds topology verbs to the runtime substrate, driven by schedule-matters:

| Runtime verb | Owner | Purpose |
|---|---|---|
| `TmuxCreateSession` | runtime/platform | Run `tmux new-session` and return `$session_id`, initial `@window_id`, initial `%pane_id`, and display position. |
| `TmuxCreateWindow` | runtime/platform | Run `tmux new-window` and return `@window_id`, `%pane_id`, and display position. |
| `TmuxSplitPane` | runtime/platform | Run `tmux split-window` under a live target and return new `%pane_id`. |
| `TmuxClosePane` | runtime/platform | Close a pane by live `%pane_id` or runtime-resolved target. |
| `TmuxListTopology` | runtime/platform | Return live tmux session, window, and pane ids for reconciliation. |
| `TmuxResolveIds` | runtime/platform | Resolve live ids to current display position for CLI output. |

The implementation can expose these as new `RuntimeRpc` variants plus matching methods on a context-neutral runtime port, or as a narrow `TmuxTopologyPort` used by the schedule driver. Phase 1 must rehost the current `RuntimePort` trait out of `lilo-session-driver` before schedule consumes it, into a new neutral runtime-port crate created by this phase (e.g. `internal/runtime/port`; it does not exist yet, see §7.2). Both `lilo-session-driver` and the schedule driver may consume that neutral crate; schedule-matters must not depend on `lilo-session-driver`. The rule is single-source tmux execution: no direct tmux shell-out inside schedule-matters.

### 3.3 Schedule RPC verbs

| Schedule RPC | Rendered method | User-facing mapping | Existing primitive reused | New primitive required | Notes |
|---|---|---|---|---|---|
| `ScheduleRpc::SessionCreate` | `schedule.session.create` | `lilo create session` | Session app accepts the request. Runtime spawn launches occupants after panes exist. | Schedule manifest apply plus runtime topology verbs. | Declarative apply. Multi-agent. |
| `ScheduleRpc::SessionGet` | `schedule.session.get` | `lilo get session` plus future `lilo schedule get` | Session `List` for logical sessions, schedule store for topology. | Schedule read model. | Joins logical session identity to placement. |
| `ScheduleRpc::SessionList` | `schedule.session.list` | `lilo get session` and future `lilo schedule list` | Session `List`. | Schedule topology listing. | Selector semantics remain session-matters. |
| `ScheduleRpc::SessionDelete` | `schedule.session.delete` | `lilo delete session` | Session `Delete`, runtime terminate. | Schedule topology cleanup. | Deletes desired topology and closes panes through runtime topology. |
| `ScheduleRpc::PaneCreate` | `schedule.pane.create` | future `lilo schedule pane create` | None. | Runtime `TmuxCreateWindow`. | Creates a new window or top-level pane and allocates a schedule pane UID. |
| `ScheduleRpc::PaneSplit` | `schedule.pane.split` | future `lilo schedule pane split` | None. | Runtime `TmuxSplitPane`. | Splits an existing pane. Takes a schedule pane UID as source, never a stored position. |
| `ScheduleRpc::PanePlace` | `schedule.pane.place` | `lilo run` and future explicit place command | Runtime spawn through existing spawn path. | Schedule binding. | Imperative create-and-place. |
| `ScheduleRpc::PaneRead` | `schedule.pane.read` | `lilo capture`, `lilo logs` | Session `Capture` and `Logs`; runtime `capture`. | Schedule UID lookup. | Reads by occupant or pane UID, delegates capture. |
| `ScheduleRpc::PaneSendText` | `schedule.pane.send_text` | Prefer `lilo mail` for semantic agent input. Raw operator escape hatch can live under `lilo schedule pane send-text`. | Session `MailSend` where semantic. Runtime tmux send for raw pane. | Runtime send text helper if raw. | schedule does not parse content. |
| `ScheduleRpc::PaneSendKeys` | `schedule.pane.send_keys` | Prefer `lilo nudge` for semantic wakeups. Raw operator escape hatch can live under `lilo schedule pane send-keys`. | Session `Nudge` where semantic. Runtime tmux send keys for raw pane. | Runtime send keys helper if raw. | Raw control remains explicit substrate access. |
| `ScheduleRpc::PaneClose` | `schedule.pane.close` | `lilo delete session` or future `lilo schedule pane close` | Runtime terminate if a runtime process is bound. | Runtime `TmuxClosePane`. | Emits close or orphan event as appropriate. |
| `ScheduleRpc::PaneWaitForOutput` | `schedule.pane.wait_for_output` | `lilo wait` plus future pane-scoped wait | Session `Wait`, runtime `Events` and `Status`, capture as needed. | Schedule wait wrapper. | Pull now. Subscribe later. |
| `ScheduleRpc::EventsWait` | `schedule.events.wait` | `lilo wait` and future `lilo schedule events wait` | Runtime `Events`, runtime `Status`. | Schedule event table and cursor. | One-shot condition wait. |
| `ScheduleRpc::EventsSubscribe` | `schedule.events.subscribe` | future streaming API | Runtime event stream when available. | Schedule subscription channel. | Deferred. Strict superset of wait. |

`SessionRpc` already exposes mail, nudge, capture, and wait (`internal/session/core/src/proto/rpc.rs:24-33`). The CLI already routes `Mail`, `Nudge`, `Capture`, `Logs`, and `Wait` through the session command layer (`crates/lilo/src/cli/mod.rs:66-82`). schedule-matters should reuse these for semantic agent interaction.

`RuntimePort` already exposes `spawn`, `capture`, `terminate`, `nudge`, `status`, and `poll_events` (`internal/session/driver/src/port.rs:18-53`). schedule-matters should use this seam for launch, liveness, and readback rather than invent parallel runtime access, but via the context-neutral runtime-port crate (see §7.2), never by depending on `lilo-session-driver`.

### 3.4 Apply, run, exec

The Kubernetes-shaped user model is:

| User intent | littleorgans verb | Schedule shape |
|---|---|---|
| Declarative topology | `lilo create session` | apply manifest. |
| Imperative single agent | `lilo run` | create and place one occupant. |
| Existing live pane | explicit existing-pane run | exec-shaped place into a live pane. |

The direct `spawn_session` helper remains a migration target until schedule placement lands (`internal/session/app/src/cli/run.rs:41-99`).

## 4. Reconciler

### 4.1 Apply flow

`ScheduleRpc::SessionCreate` runs this sequence:

1. Decode and migrate the versioned manifest snapshot.
2. Validate topology intent: workspace, windows, panes, cwd, occupant tokens, and opaque launch payload presence.
3. Allocate schedule UIDs for the desired topology.
4. Persist desired state and pending bindings in schedule SQLite tables inside `data/lilo.db`.
5. Call runtime topology verbs to create tmux session, windows, and panes. Runtime/platform executes tmux and returns `$session_id`, `@window_id`, `%pane_id`, and display position.
6. Persist live tmux ids as current realization metadata.
7. For each occupant, call the existing runtime spawn path into the live pane. Spawn still owns process launch and shim lifecycle.
8. Bind `occupant_token` to `schedule_pane_uid`.
9. Emit `placed(token, pane_uid)` events.
10. Return the logical session plus schedule topology summary to the caller.

If topology creation succeeds but spawn fails, schedule leaves the pane empty and marks the binding failed with error evidence. Cleanup policy is explicit in the caller. Silent deletion would hide debugging state.

### 4.2 Drift reconciliation

The reconciler compares stored desired topology with runtime-reported live topology and runtime liveness. Phase 1 uses pull. Subscribe is deferred.

Preferred liveness source is the existing runtime signal path:

1. Neutral runtime-port `poll_events` for runtime event batches.
2. Neutral runtime-port `status` for current lifecycle snapshots.
3. Runtime topology list for tmux id existence when event or status data needs topology confirmation.

Do not add a separate per-pane `is_alive` polling loop in schedule. `TmuxGateway::is_alive` remains inside runtime/platform. schedule sees liveness through runtime RPC or port methods. This keeps one liveness path.

`RuntimeRpc` already has `Status` and `Events` variants (`crates/lilo-rm-core/src/proto.rs:107-116`), and `RuntimePort` exposes `status` and `poll_events` (`internal/session/driver/src/port.rs:46-48`, rehosted to the neutral runtime-port crate per §7.2). Schedule should build on those.

### 4.3 Pane death

When runtime reports a pane or occupant no longer has a live body:

1. Resolve the affected live `%pane_id` to `schedule_pane_uid`.
2. Resolve `schedule_pane_uid` to `occupant_token`.
3. Read the occupant's declared `restart_policy` from the binding, plus the runtime's terminal evidence (exit code and signal where present).
4. If `Never`: mark the binding `orphaned`, emit `orphaned(token)`, and stop.
5. If `OnFailure`: re-place only on terminal failure evidence (a nonzero exit code or a signal); a clean exit, or a `Lost` body with no exit code, orphans like `Never`.
6. If `Always` (or `OnFailure` with terminal failure evidence): allocate a new pane through the runtime topology verbs, re-bind the occupant token to the new `schedule_pane_uid`, ask runtime to relaunch the occupant with its native resume mechanism (`--resume <native-id>`) using the binding's `native_resume_ref`, and emit `replaced(token, new_pane_uid)`.

schedule-matters reconciles the declared intent; it never authors it. The orchestrator baked `restart_policy` into the manifest at authoring time. Restart logic that cannot be expressed as a static per-occupant policy (backoff, max-retries, replace-with-a-different-role) stays in orchestration-matters.

### 4.4 Positional addresses

The reconciler must never recover identity from `s:w.p`. Position can appear only as current display data returned by runtime topology resolution. If tmux renumbers a window, the next runtime topology refresh updates display position without changing `schedule_pane_uid` or `occupant_token`.

If tmux server restart invalidates `%pane_id`, the binding becomes orphaned unless runtime can prove a safe live id mapping through stable tmux ids. No fallback to position is allowed.

## 5. Placement authority cutover

### 5.1 Current state

The current CLI implementation has one spawn path:

- `run(args)` validates isolation and mounts, then calls `spawn_session` (`internal/session/app/src/cli/run.rs:15-27`).
- `create_session(args)` calls the same `spawn_session` with target `headless` (`internal/session/app/src/cli/run.rs:29-39`).
- `spawn_session` sends `SessionRpc::Spawn` to lilod (`internal/session/app/src/cli/run.rs:64-85`).

This is the pre-schedule state.

### 5.2 Target state

After cutover:

1. `lilo create session` parses or constructs a thin manifest and sends it through session-matters to `ScheduleRpc::SessionCreate`.
2. `lilo run` stays imperative. The handler may desugar its flags into a one-pane schedule unit, but it calls the create-and-place path, `ScheduleRpc::PanePlace`, rather than declarative session apply.
3. Explicit existing-pane run uses the exec-shaped path: schedule resolves the target pane UID or live tmux id, records the binding, then requests runtime spawn into that pane.
4. Raw `lilo runtime spawn` remains diagnostic runtime access. It does not create session records, schedule topology, or occupant bindings.
5. A new operator namespace `lilo schedule ...` exposes direct substrate inspection and repair commands.

### 5.3 Migration posture

This repo is pre-release. No compatibility shim is required for old placement semantics. Replace the old path rather than keep a parallel implementation. The old direct spawn path should be deleted or reduced to the schedule-mediated path once acceptance passes.

## 6. restartPolicy reconciliation

Phase 1 implements `Never` and `Always`/`OnFailure`. The decision is declarative and upstream: the manifest author (the orchestrator) bakes the per-occupant `restartPolicy` into the manifest, and schedule-matters reconciles it.

Rules:

1. `restartPolicy` is a per-occupant field on the thin manifest (`Never | OnFailure | Always`), the same place Kubernetes puts it (on the PodSpec). It is lifecycle intent, not coordination policy, so it does not break the thin rule.
2. Bare `lilo run` defaults to `Never`.
3. On pane death, schedule reconciles the declared intent (§4.3): `Never` emits `orphaned(token)` and stops; `Always` re-places and resumes on any death; `OnFailure` re-places and resumes only on terminal failure evidence (nonzero exit code or signal), and orphans on a clean exit or a `Lost` body with no exit code.
4. schedule reconciles; it never re-decides. The orchestrator authored the intent.
5. Native resume is the baseline resurrection mechanism, but it is not yet wired in the codebase. Today the binding's `session_id` is the logical lilo session UUIDv7 exported only as env (`SessionDraft::running_session` persists `runtime_session: None`; launchers return only the binary argv), so no `--resume <id>` flag is produced. Phase 1 must therefore (a) capture and persist a per-occupant native resume identity or resume argv into `native_resume_ref`, distinct from the logical `session_id`, and (b) inject it on relaunch, with an adapter test proving `--resume <native-id>` or the runtime equivalent is actually emitted. This is a Phase-1 prerequisite for `Always`/`OnFailure`, the same way §8.8 is a prerequisite for authz.
6. Phase 1 owns only the mechanical resume launch. The deeper per-CLI continue-vs-fork jsonl semantics (does `--resume` continue or fork the transcript) stay at the build-plan Phase 2 decision gate, resolved in the transcript adapters.
7. Richer transcript-owned resume (replay, branch, cross-agent) is a separate subsystem, not part of placement reconciliation.

orchestration-matters enters only for restart logic that cannot be expressed as a static per-occupant policy: backoff, max-retries, give-up-and-replace-with-a-different-role.

## 7. Neighbor boundaries

### 7.1 session-matters

session-matters owns logical identity and primitives:

- durable session and agent records
- namespaces, labels, selectors
- mail
- nudge
- capture
- logs
- wait
- restart policy storage

`SessionRpc` is the public proof of that boundary (`internal/session/core/src/proto/rpc.rs:16-36`). schedule-matters can reference session ids and occupant tokens, but it does not replace session primitives.

### 7.2 runtime-matters

runtime-matters owns host execution:

- runtime spawn
- shim lifecycle
- terminate
- raw status
- event polling
- tmux command execution
- tmux topology primitives added by this phase

`RuntimePort` is the daemon seam used by session composition (`internal/session/driver/src/port.rs:18-53`). `TmuxGateway` is the single tmux execution layer (`internal/runtime/platform/src/tmux.rs:19-114`). schedule decides, runtime executes.

Phase 1 rehosts the `RuntimePort` trait out of `internal/session/driver` (`lilo-session-driver`, where it lives today at `internal/session/driver/src/port.rs`) into a new context-neutral runtime-port crate created by this phase (e.g. `internal/runtime/port`; it does not exist yet — `internal/port` is the unrelated `lilo-port` error kernel), consumed by both the session driver and the schedule driver. This new crate must be registered in the workspace-wiring checklist (§3.1, §9). schedule-matters depends on that neutral port crate, never on `lilo-session-driver`.

### 7.3 wire

wire carries JSON control and remains substrate tagged. Add `Schedule(ScheduleRpc)` to the existing envelope. Do not flatten schedule verbs into session or runtime.

### 7.4 transport-matters

transport-matters owns the high bandwidth transcript stream. schedule control responses can include ids, status, and short evidence, but must not carry transcript streams or base64 stuffed terminal frames. `pane.read` delegates to existing capture/read paths and future transport-backed read models.

### 7.5 agent-matters

agent-matters owns role and CLI configuration. schedule treats role/config refs as opaque launch payload. It can place an occupant, but it cannot compile, mutate, or reason about the role.

### 7.6 orchestration-matters and workflow-matters

orchestration-matters consumes schedule placement and session primitives to coordinate live agents. workflow-matters sits above orchestration as DAG flow. Neither is required for schedule Phase 1 acceptance, except that schedule events and restart hooks must be shaped so these later layers can consume them.

## 8. Phase 1 acceptance criteria

The Phase 1 output is schedule-matters owning placement end to end. Acceptance follows the seven build-plan items plus the cross-cutting authorization and audit requirement (§8.8); build-plan.md lists exactly seven items, and authz/audit is the cross-cutting addition, not an eighth build-plan item.

### 8.1 tmux integration

Acceptance: schedule-matters can create a tmux session, add windows and panes, and list them by stable id.

Proof:

1. A schedule integration test applies a manifest with one session, two windows, and multiple panes.
2. Runtime topology RPC returns `$session_id`, `@window_id`, and `%pane_id` for each live object.
3. `lilo schedule get` or equivalent test output lists schedule UIDs and live ids.
4. No schedule code shells out to tmux directly. All tmux execution goes through runtime/platform.

### 8.2 Stable ID model, never positional

Acceptance: a window insert or delete leaves every occupant binding intact.

Proof:

1. Place occupants in two panes.
2. Insert or delete a tmux window.
3. Reconcile.
4. Assert occupant token to schedule pane UID bindings are unchanged.
5. Assert any displayed position changed only as derived output.

### 8.3 Occupant binding

Acceptance: an agent placed in a pane is found by token after arbitrary window churn.

Proof:

1. Bind `occupant_token` to `schedule_pane_uid`.
2. Perform window churn and pane splits.
3. Lookup by token returns the same schedule pane UID and current live `%pane_id`.

### 8.4 Placement authority

Acceptance: no path places an agent into a pane except schedule-matters.

Proof:

1. `lilo run` goes through schedule create-and-place, not direct spawn and not declarative apply.
2. `lilo create session` goes through schedule session create and declarative apply.
3. Explicit existing-pane placement records a schedule binding before runtime spawn.
4. Raw `lilo runtime spawn` remains diagnostic and creates no session record or schedule binding.
5. Tests fail if session app calls `SessionRpc::Spawn` directly from user-facing run/create after cutover.

### 8.5 Thin session manifest plus reconciler

Acceptance: `lilo create session` applies a manifest, and schedule-matters materializes and owns it.

Proof:

1. Manifest fixture decodes through `SNAPSHOT_VERSION`.
2. schedule persists desired topology in `data/lilo.db`.
3. runtime creates live tmux objects.
4. schedule reconciler can rebuild current topology from persisted desired state plus runtime status.

### 8.6 Pane-death event

Acceptance: killing a pane surfaces an `orphaned(token)` event to watchers.

Proof:

1. Create a one-pane scheduled unit.
2. Kill the live tmux pane.
3. Pull runtime events or status through the existing runtime signal path.
4. Run schedule reconcile.
5. Assert `ScheduleEvent::Orphaned { occupant_token }` exists.
6. Assert schedule did not restart the agent.

### 8.7 restartPolicy reconciliation, Never and Always

Phase-1 prerequisite: native resume is not wired today (`SessionDraft::running_session` persists `runtime_session: None`; launchers return only the binary argv; `ShellResume` is an operator `$SHELL` re-exec, not agent resume). Phase 1 must first capture and persist a per-occupant native resume identity into `native_resume_ref` (distinct from the logical lilo `session_id`) and inject it on relaunch, or proof 2 below is unsatisfiable as written. Continue-vs-fork jsonl semantics stay at the build-plan Phase 2 gate.

Acceptance: a `Never` occupant dies with its pane; an `Always` occupant is re-placed and resumed.

Proof:

1. Run a `Never` occupant through schedule, kill its pane, reconcile. Assert the binding is `orphaned`, no replacement pane is created, and `orphaned(token)` is emitted.
2. Run an `Always` occupant through schedule, kill its pane, reconcile. Assert schedule allocates a new pane through the runtime topology verbs, re-binds the same occupant token to the new schedule pane UID, and relaunches the occupant with its native resume mechanism (`--resume <native-id>`) from the persisted `native_resume_ref`. An adapter test asserts the resume argument is actually produced.
3. Assert the restart intent is read from the manifest and binding, never re-decided by schedule.
4. `OnFailure` re-places only on terminal failure evidence (a nonzero exit code or signal, per `RuntimeExit`); a clean exit, or a `Lost` body with no exit code, orphans.

### 8.8 Authorization and audit

Phase-1 prerequisite: the identity `Action`/`ResourceSpec` shape carries no schedule verbs or schedule resource ids today (`crates/lilo-im-core/src/types.rs:147-177`), so the audit record below is unsatisfiable as written. Phase 1 must first extend the identity action/resource shape to cover schedule verbs and schedule ids, or define an explicit lossless mapping, before the ScheduleRpc authz tests can pass.

Acceptance: every schedule placement and topology mutation is identity-gated and audited with schedule-specific action and resource evidence that can name target schedule ids.

Proof:

1. Unauthenticated or unauthorized `ScheduleRpc` mutation requests are rejected before topology or spawn side effects.
2. Authorized mutation requests append an audit record with principal, schedule operation, target schedule ids, and outcome.
3. Tests cover `ScheduleRpc::SessionCreate`, `ScheduleRpc::PanePlace`, and topology delete.
4. Raw runtime spawn remains diagnostic and does not create schedule bindings.

## 9. Open questions carried

1. Exact crate layout and Cargo wiring: likely `internal/schedule/{core,store,driver,daemon,app}` to mirror session, but Phase 1 implementation should confirm the smallest shape before creating files. Add workspace members under `internal/schedule/*`, create and register the new neutral runtime-port crate (§3.2, §7.2 — it does not exist yet), add `[workspace.dependencies]` entries for new schedule crates, and wire `internal/wire` to `lilo-schedule-core` when `LilodRpc::Schedule` lands.
2. Exact schedule manifest field names: this spec fixes the shape and invariants, but implementation should lock serialized names through fixtures before codegen or docs depend on them.
3. Runtime topology API shape: choose between extending `RuntimeRpc` plus `RuntimePort` directly or introducing a narrow `TmuxTopologyPort` adapter. Either way, runtime/platform owns tmux execution.
4. Event storage: align schedule event persistence with existing session and runtime event patterns before implementing subscriptions.
5. Tmux server restart recovery: Phase 1 can orphan when live ids disappear. Any safe remap beyond that needs a separate proof and cannot use positional addresses.
6. CLI raw pane escape hatch: decide exact `lilo schedule pane send-text/send-keys` UX after the control API exists. Semantic drive remains `lilo mail` and `lilo nudge`.
