# schedule-matters Phase 1 — Implementation Plan-Sequence Map

> **What this is:** the decomposition of build-plan Phase 1 (schedule-matters) into eight
> dependency-ordered executable plans. Each plan produces working, testable software on its own and
> maps to acceptance criteria in `littleorgans-schedule-matters-spec.md`. This is the "what gets
> built when" inside Phase 1; each plan below becomes its own granular TDD document when started
> (Plan 01 is written: `littleorgans-schedule-matters-p1-plan-01-scaffolding.md`).

**Goal:** schedule-matters owns placement end to end — apply a thin manifest into owned tmux
topology, bind occupants by stable id, reconcile drift and restart intent.

**Sequencing principle:** additive scaffolding first, then the store, then the runtime substrate it
drives, then the refactor that lets it consume the runtime, then apply, then cutover, then the
reconciler, then authz. Refactors of working code (the runtime-port rehost) are isolated into their
own plan so a failure blast-radius stays small.

---

## Dependency graph

```
01 scaffolding ──┬─► 02 store ──────────────┐
                 ├─► 03 tmux topology verbs ─┤
                 └─► 04 runtime-port rehost ─┴─► 05 apply + stable-id + binding
                                                       │
                                                       ├─► 06 placement cutover
                                                       └─► 07 reconciler + pane-death + restart/resume
                                                                  │
                                                                  └─► 08 authz + audit
```

02, 03, 04 are mutually independent and can run in parallel once 01 lands. 05 is the convergence
point (needs the store, the topology verbs, and the neutral port). 06 and 07 both build on 05; 08
gates the mutation verbs and can land any time after 05 but must precede Phase-1 sign-off.

---

## Plan 01 — Scaffolding (crates + envelope + pool alias)

- **Goal:** the two schedule crates exist, compile, and are reachable from the wire envelope.
- **Delivers:** `lilo-schedule-core` (with a `ScheduleRpc` enum) and `lilo-schedule-store`
  (skeleton `ScheduleStore`) as workspace members; `LilodRpc::Schedule(ScheduleRpc)` on the wire
  envelope; `LiloDb::schedule_pool()` as the fourth named alias over the single shared pool.
- **Acceptance:** `cargo check` green workspace-wide; a serde round-trip proves the `Schedule`
  variant tags as `"schedule"`; `schedule_pool()` returns the same pool as `session_pool()`.
- **Spec refs:** §3.1 (workspace wiring), §2.2 (single shared `data/lilo.db`), §3.1 envelope.
- **Depends on:** nothing. Pure additive; touches no existing behavior.
- **Key files:** `internal/schedule/core/`, `internal/schedule/store/`, root `Cargo.toml`,
  `internal/wire/src/lib.rs`, `internal/db/src/lib.rs`.

## Plan 02 — Schedule store: data model + snapshot contract

- **Goal:** the five core records persist with durable UIDs.
- **Delivers:** `ScheduleSession`, `ScheduleWindow`, `SchedulePane`, `OccupantBinding`
  (incl. `session_id`, `native_resume_ref`, `restart_policy`), `ScheduleEvent` as SQLite tables
  over `schedule_pool()`, per-table modules mirroring `internal/session/store/src/sqlite/{…}`, the
  versioned snapshot contract (`SNAPSHOT_VERSION`, `serde(default)`, one decode path, a migrator
  seam), with `*_with<E: Executor>` helpers for tx composition.
- **Acceptance:** round-trip persistence per record; UID allocation is stable and opaque;
  positional `s:w.p` is never written as authority; legacy-snapshot decode test once a migration
  exists. (Spec §2.2, §2.4, §8 data-model invariants.)
- **Depends on:** 01. **Key files:** `internal/schedule/store/src/sqlite/{schedule_sessions,
  windows,panes,bindings,events}.rs`, `internal/db` migrations.

## Plan 03 — Runtime tmux topology verbs

- **Goal:** runtime can create and enumerate tmux topology and return stable ids.
- **Delivers:** `TmuxGateway` gains `new_session`/`new_window`/`split_window`/`close_pane`/
  `kill_window`/`list_topology`/`resolve_ids` returning `$session_id`/`@window_id`/`%pane_id` +
  display position; exposed as new `RuntimeRpc` variants (and matching neutral-port methods, or a
  narrow `TmuxTopologyPort`). Single-source tmux execution preserved: no shell-out outside
  runtime/platform.
- **Acceptance:** spec §8.1 proofs 1–4 — a test creates a session, two windows, multiple panes,
  reads back stable ids, and asserts no schedule-side tmux shell-out.
- **Depends on:** 01. **Key files:** `internal/runtime/platform/src/tmux.rs`,
  `crates/lilo-rm-core/src/proto.rs`, `internal/runtime/daemon/src/server/`.

## Plan 04 — Neutral runtime-port rehost

- **Goal:** the `RuntimePort` trait has a context-neutral home both drivers consume.
- **Delivers:** a new `lilo-runtime-port` crate at `internal/runtime/port` (does not exist today —
  members lists only `internal/port`, the unrelated `lilo-port` error kernel). Move the
  `RuntimePort` trait and its owned types (`SpawnLaunch`, `SpawnedProcess`, `ChildExit`,
  `CaptureResult`, `NudgeResult`, `StatusFilter`, `RuntimeDoctorReport`, `RuntimeError`) out of
  `lilo-session-driver` (`internal/session/driver/src/port.rs:18-53`); both the session driver and
  the future schedule driver depend on the neutral crate. No behavior change.
- **Acceptance:** `cargo check`/`just test` green; the session daemon still drives runtime through
  the rehosted trait; schedule may now depend on the neutral crate without depending on
  `lilo-session-driver`. (Spec §3.2, §7.2.)
- **Depends on:** 01. Isolated refactor of working code — kept alone to bound blast radius.

## Plan 05 — Schedule apply + stable-id + occupant binding

- **Goal:** apply a manifest into owned tmux topology with churn-resistant bindings.
- **Delivers:** the §4.1 apply flow (decode/migrate manifest → validate → allocate UIDs → persist
  desired → runtime topology verbs → persist live ids → runtime spawn per occupant → bind
  `occupant_token`→`schedule_pane_uid` → emit `placed`); the stable-id ladder (UID bound to
  `%pane_id`, positional derived for display only); occupant binding survives window churn.
- **Acceptance:** spec §8.1 (end-to-end apply), §8.2 (window insert/delete leaves bindings intact),
  §8.3 (token lookup after churn). **Depends on:** 02, 03, 04.

## Plan 06 — Placement authority cutover

- **Goal:** no path places an agent into a pane except schedule-matters.
- **Delivers:** route `lilo create session` → `ScheduleRpc::SessionCreate` (declarative apply) and
  `lilo run` → `ScheduleRpc::PanePlace` (create-and-place); exec-shaped existing-pane place; delete
  the direct `spawn_session` path (`internal/session/app/src/cli/run.rs:41-99`); raw
  `lilo runtime spawn` stays diagnostic.
- **Acceptance:** spec §8.4 (no non-schedule placement; test fails if run/create call
  `SessionRpc::Spawn` directly after cutover), §8.5 (manifest apply materializes and is owned).
  **Depends on:** 05. Pre-release — replace the old path, no compat shim (§5.3).

## Plan 07 — Reconciler drift + pane-death + restartPolicy/resume

- **Goal:** schedule reconciles liveness and the declared restart intent.
- **Delivers:** drift reconcile via neutral-port `poll_events`/`status` (pull; one liveness path,
  no schedule-side `is_alive` loop); pane-death → `orphaned(token)`; restartPolicy reconciliation
  (`Never`→orphan+stop; `Always`→re-place+resume on any death; `OnFailure`→re-place+resume only on
  terminal failure evidence — nonzero `RuntimeExit` code/signal — else orphan). **Native-resume
  prerequisite:** carry a native resume id on `SpawnRequest` (new field — `argv(request)` currently
  discards it), thread it into `BinaryLauncher::argv`/`resolved_argv` and the per-runtime launchers,
  capture+persist it into `OccupantBinding.native_resume_ref` (distinct from the logical
  `session_id`), inject `--resume <native-id>` on relaunch, with an adapter test proving the flag is
  emitted. Continue-vs-fork jsonl semantics stay at the build-plan P2 gate.
- **Acceptance:** spec §8.6 (orphaned event, no restart), §8.7 (Never dies, Always resumes,
  OnFailure failure-conditional, intent never re-decided). **Depends on:** 05.

## Plan 08 — Authorization and audit

- **Goal:** every schedule mutation is identity-gated and audited.
- **Delivers:** extend identity `Action`/`ResourceSpec` (`crates/lilo-im-core/src/types.rs:147-177`
  — no schedule verbs/ids today) to carry schedule verbs and schedule resource ids, or a lossless
  mapping; gate + audit `ScheduleRpc::SessionCreate`, `PanePlace`, topology delete with principal,
  operation, target schedule ids, outcome.
- **Acceptance:** spec §8.8. **Depends on:** 05 (verbs exist to gate). Must precede Phase-1 sign-off.

---

## Critical path and start order

Critical path to "schedule owns placement": **01 → (02 ‖ 03 ‖ 04) → 05 → 06**. 07 and 08 follow 05.
Start now with **Plan 01**; the moment it lands, 02 / 03 / 04 parallelize.
