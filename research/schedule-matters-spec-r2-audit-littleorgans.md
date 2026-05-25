---
title: Schedule Matters Spec Round 2 Audit for littleorgans
type: research
tags: [littleorgans, schedule-matters, spec-review, architecture, audit]
summary: Round 2 audit verified the carried polish notes and found two substantive implementation risks in the schedule-matters Phase 1 spec.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-31
updated: 2026-05-31
---

## Executive Summary

The schedule-matters Phase 1 spec already includes the four carried polish notes from round 1. A fresh audit against the live littleorgans crates found two substantive risks: the spec currently points schedule toward a session-owned runtime port, and the authz/audit acceptance requires target schedule ids that the current identity audit types cannot yet encode.

## Project Metadata

- Language and build: Rust 2024 Cargo workspace, version `0.8.0`, Rust `1.95` (`Cargo.toml:1-38`).
- Workspace shape: 365 indexed source files, 48,763 LOC by fmm. Major buckets: `internal/` 293 files, `crates/` 67 files, `tests/` 4 files, `tools/` 1 file.
- fmm status: `.fmmrc.toml` exists, and `fmm validate` reported all 365 files indexed and up to date.
- Key dependencies: `tokio`, `sqlx` SQLite, `serde`, `serde_json`, `uuid`, `clap`, `tracing`, `nix`, `thiserror` (`Cargo.toml:40-95`).
- Operator surface: root `justfile` provides `build`, `test`, `check`, and `regression`; `check` runs fmt, clippy, line cap, and provenance checks (`justfile:90-157`).

## Architecture Context

The current littleorgans control plane has runtime, session, wire, db, identity, and the `lilo` CLI in place. Schedule is still greenfield in the build plan (`~/.mdx/projects/littleorgans-build-plan.md:17-29`). Phase 1 schedule work is meant to add multiplexing and placement on top of existing runtime spawn, nudge, capture, and lilod lifecycle patterns (`~/.mdx/projects/littleorgans-build-plan.md:59-84`).

The cockpit architecture sets the governing constraints:

- `wire` stays a transport agnostic JSON control seam (`~/.mdx/projects/littleorgans-cockpit-architecture.md:52-60`).
- transport-matters owns high bandwidth transcript capture on a separate channel, the dual socket rule (`~/.mdx/projects/littleorgans-cockpit-architecture.md:118-122`).
- schedule-matters owns multiplexing and becomes the sole placement authority after the cutover (`~/.mdx/projects/littleorgans-cockpit-architecture.md:126-157`).
- tmux positional addresses must not be stored as authority; schedule binds opaque occupant tokens to durable pane UIDs and only realizes them as live tmux ids (`~/.mdx/projects/littleorgans-cockpit-architecture.md:163-183`).
- restart policy belongs above schedule-matters and is not part of the thin manifest (`~/.mdx/projects/littleorgans-cockpit-architecture.md:190-215`).
- lower layers must not know their consumers; dependencies point down (`~/.mdx/projects/littleorgans-cockpit-architecture.md:219-302`).

The herdr research corroborates the dual socket separation and versioned snapshot migration pattern, while keeping SQLite as the locked littleorgans storage decision (`~/.mdx/research/ogulcancelik-herdr.md:51-63`, `~/.mdx/research/ogulcancelik-herdr.md:97-98`).

## Key Patterns Verified

- Unified SQLite access is centralized through `LiloDb`; the live accessor set currently exposes only identity, session, and runtime pools (`internal/db/src/lib.rs:58-68`).
- The user-facing CLI dispatch routes `lilo run`, `create`, `get`, `delete`, `mail`, `nudge`, `capture`, `logs`, `wait`, and `mcp` through session commands, while runtime and identity remain substrate namespaces (`crates/lilo/src/cli/mod.rs:43-118`).
- Current user-facing `lilo run` and `lilo create session` both call `spawn_session`, which sends `SessionRpc::Spawn`; this is the interim path to replace during schedule cutover (`internal/session/app/src/cli/run.rs:15-99`).
- The wire envelope currently has only `Session` and `Runtime` variants (`internal/wire/src/lib.rs:5-8`).
- `RuntimeRpc` already has spawn, validate target, kill, nudge, capture, status, events, and daemon operations, but no topology create/list variants yet (`crates/lilo-rm-core/src/proto.rs:88-130`).
- `SessionRpc` owns spawn, namespace operations, mail, nudge, logs, capture, doctor, wait, and MCP bridge (`internal/session/core/src/proto/rpc.rs:16-36`).
- `TmuxGateway` is the single tmux execution layer today for nudge, respawn, liveness, and capture (`internal/runtime/platform/src/tmux.rs:8-115`).

## Detailed Findings

### Carried polish notes are present

1. `LiloDb::schedule_pool()` is explicitly required in the spec, and the current code proves it is not present yet. The spec says schedule must not borrow `session_pool` (`~/.mdx/projects/littleorgans-schedule-matters-spec.md:51`). Live `LiloDb` exposes only `identity_pool`, `session_pool`, and `runtime_pool` (`internal/db/src/lib.rs:58-68`).
2. Authz and audit are promoted into a Phase 1 acceptance section. The spec requires every schedule placement and topology mutation to be identity gated and audited (`~/.mdx/projects/littleorgans-schedule-matters-spec.md:412-421`).
3. `lilo run` remains imperative, not a one pane declarative apply. The spec distinguishes declarative topology from imperative single agent create and place (`~/.mdx/projects/littleorgans-schedule-matters-spec.md:177-187`) and repeats the cutover rule (`~/.mdx/projects/littleorgans-schedule-matters-spec.md:252-260`, `~/.mdx/projects/littleorgans-schedule-matters-spec.md:364-375`).
4. §3.3 verb names are schedule scoped. The spec states rendered methods are `schedule.session.create`, `schedule.pane.split`, and `schedule.events.wait`, then uses `schedule.*` throughout the table (`~/.mdx/projects/littleorgans-schedule-matters-spec.md:121-173`).

### Fresh issue 1: `RuntimePort` is session owned today

The spec says schedule should use `RuntimePort` for launch, liveness, and readback (`~/.mdx/projects/littleorgans-schedule-matters-spec.md:173-175`). The live `RuntimePort` trait lives in `internal/session/driver/src/port.rs:18-53`, imports `lilo_session_core`, and is re-exported by `lilo-session-driver` (`internal/session/driver/src/lib.rs:1-21`). Its dependency graph is session-specific: `internal/session/driver/src/port.rs` depends on `internal/session/core/src/lib.rs`, `internal/session/driver/src/conv.rs`, and `internal/session/driver/src/driver.rs`.

That would make schedule depend on session driver internals, violating the lower layer independence rule from the cockpit architecture (`~/.mdx/projects/littleorgans-cockpit-architecture.md:219-302`). The fix should be explicit in the spec: extract or rehost the existing runtime port into a context-neutral runtime or shared port seam before schedule consumes it. Schedule should not depend on `lilo-session-driver`.

### Fresh issue 2: identity audit types cannot yet encode schedule targets

The spec requires audit records with principal, operation, target schedule ids, and outcome (`~/.mdx/projects/littleorgans-schedule-matters-spec.md:412-421`). Live identity audit rows carry an `Action` and `ResourceSpec` (`crates/lilo-im-core/src/audit.rs:40-52`), but the current `Action` enum has generic actions only and no schedule or topology verbs (`crates/lilo-im-core/src/types.rs:147-160`). `ResourceSpec` can express workspace, role, runtime, session id, and labels, but not `schedule_session_uid`, `schedule_window_uid`, `schedule_pane_uid`, or occupant token (`crates/lilo-im-core/src/types.rs:171-177`).

The spec should add a Phase 1 requirement to extend identity action and resource audit shape for schedule ids, or define a lossless mapping before ScheduleRpc mutation tests are accepted. Without this, §8.8 can pass at the prose level while implementation records ambiguous audit rows.

### Fresh issue 3: acceptance count wording is stale

The spec says Phase 1 acceptance follows the seven build plan items (`~/.mdx/projects/littleorgans-schedule-matters-spec.md:327-330`), then includes eight acceptance subsections because authz/audit was promoted (`~/.mdx/projects/littleorgans-schedule-matters-spec.md:331-421`). This is a low severity polish issue. The fix is to say “seven build plan items plus the authz/audit requirement” or “eight Phase 1 criteria.”

## Dependencies

- `sqlx` SQLite backs the shared `~/.lilo/data/lilo.db` database and all substrate stores (`Cargo.toml:74`).
- `lilo-im-core`, `lilo-im-store`, and `lilo-im-stub` provide the current identity, authz, and audit surface (`Cargo.toml:51-53`).
- `lilo-rm-core`, `lilo-runtime-platform`, `lilo-runtime-daemon`, and `lilo-runtime-app` provide runtime protocol, tmux execution, daemon handling, and app surface (`Cargo.toml:60-65`).
- `lilo-session-core`, `lilo-session-store`, `lilo-session-driver`, `lilo-session-daemon`, and `lilo-session-app` provide the current session protocol, store, runtime driver adapter, daemon, and CLI app layers (`Cargo.toml:66-70`).

## Relevance to Helioy

The audit reinforces the platform split: schedule should become the sole placement authority without importing session driver internals, and identity must be extended deliberately so schedule mutations are auditable by durable schedule ids. The herdr dual socket lesson is already reflected correctly: the schedule spec keeps high bandwidth transcript streaming out of the control envelope.

## Open Questions

1. Where should the context-neutral runtime port live: `internal/runtime/driver`, `internal/runtime/app`, `internal/port`, or a new shared adapter crate?
2. Should identity add schedule-specific `Action` variants, an extensible method string, or a typed resource id enum for schedule ids?
3. Should §8.8 be acceptance criterion eight, or should it be integrated into each mutation acceptance proof?

## Mail Outcome

Phase A findings were mailed to peer `littleorgans:helioy-tools:codebase-analyst:9:4.1` on topic `schedule-spec-r2`. The orchestrator was notified that the older final-close instruction was superseded by the newer round 2 peer audit workflow.

## Peer Debate Update

Peer `littleorgans:helioy-tools:codebase-analyst:9:4.1` accepted this audit lane and independently verified the cited runtime, port, wire, session RPC, and tmux liveness evidence. I accepted the peer's F1 through F5 with one wording adjustment on F1.

Consensus recommendations to the orchestrator:

1. Reword `schedule_pool()` as a named accessor over the same shared `SqlitePool`. Schedule should call `schedule_pool()`, not `session_pool()`, but implementation must not create a second pool or database.
2. Fix acceptance traceability: Phase 1 has the seven build plan items plus a cross-cutting authz/audit requirement, or the build plan needs an eighth item.
3. Rename or drop `SchedulePane.role_hint`; role semantics should stay inside the opaque launch payload. `occupant_hint` or `display_label` would better preserve schedule blindness.
4. Add crate layout implementation notes for `internal/schedule/*`, workspace dependency entries, and the `internal/wire` dependency on `lilo-schedule-core`.
5. Disambiguate `PaneCreate` from `PaneSplit`, or collapse them behind one target-kind argument.
6. Keep the neutral runtime-port issue: schedule must not depend on `lilo-session-driver`; extract or rehost the runtime port before schedule consumes it.
7. Keep the identity audit-shape issue: schedule mutation audit needs typed schedule target ids or a lossless mapping in `Action` and `ResourceSpec`.

## Phase A Consensus

Peer debate converged after the crossed-message reconciliation. Final consensus sent to `helioy:orchestrator`:

1. S1: rehost the runtime port into a neutral runtime port crate. Schedule must not depend on `lilo-session-driver`.
2. S1: extend identity `Action` and `ResourceSpec` for schedule verbs and ids, or define a lossless mapping before ScheduleRpc authz tests.
3. MED: rewrite db pool rationale. `schedule_pool()` is a named accessor over the same shared `SqlitePool`; schedule should not call `session_pool()`, and implementation must not create a second pool or database.
4. MED: fix §8.8 traceability. Phase 1 is the seven build plan items plus a cross-cutting authorization and audit requirement, unless the build plan gains an eighth item.
5. LOW: rename or drop `role_hint` to preserve schedule blindness.
6. LOW: add workspace member and workspace dependency notes for schedule crates, plus the `internal/wire` dependency on `lilo-schedule-core`.
7. LOW: disambiguate `PaneCreate` versus `PaneSplit`, or collapse behind one target-kind argument.

Phase B remains pending until the orchestrator applies edits and asks for live spec re-verification.

## Line Precise Patch Sent

After the orchestrator requested exact edit strings, I sent a line precise patch covering all seven converged items. The patch included verbatim current snippets and replacements for:

1. runtime port rehost across §3.2, §3.3, §4.2, and §7.2;
2. identity authz shape in §8.8;
3. db pool rationale in §2.2;
4. `SchedulePane.role_hint` rename to `occupant_hint`;
5. §8 traceability wording;
6. §3.1 and §9 crate and wire dependency notes;
7. §3.3 `PaneCreate` versus `PaneSplit` disambiguation.

Peer 9:4.1 was notified. Phase B remains pending live spec edits.

## Phase B Sign-off

After the orchestrator applied the round 2 consensus edits, I re-read the live spec and verified the amended sections:

1. §2.2 describes `schedule_pool()` as a shared-pool named alias and keeps one unified `~/.lilo/data/lilo.db`.
2. §2.2 uses `display_label` instead of `role_hint` and marks it opaque output-only metadata.
3. §3.1 includes schedule crate workspace and wire dependency wiring.
4. §3.3 disambiguates `PaneCreate` from `PaneSplit`.
5. §3.3, §4.2, and §7.2 require a context neutral runtime port and bar schedule from depending on `lilo-session-driver`.
6. §8 intro now says the seven build plan items plus the cross-cutting §8.8 authz/audit requirement.
7. §8.8 now includes the identity `Action`/`ResourceSpec` prerequisite for schedule verbs and schedule ids.

Verification commands and checks:

- `fmm validate` reported all 365 files indexed and up to date.
- fmm target reads confirmed current `LiloDb`, `RuntimePort`, `LilodRpc`, `SessionRpc`, and `RuntimeRpc` shapes.
- Direct line check confirmed identity `Action` and `ResourceSpec` still lack schedule verbs and ids, matching the new §8.8 prerequisite.

I mailed `helioy:orchestrator` the clean Phase B sign-off: `I sign off on the schedule-matters spec as currently filed.`

## Reconciled Phase B Sign-off

A later orchestrator message said my line precise patch had crossed with the first apply, then the live spec was reconciled to the full seven item consensus patch. I re-read the current live file and verified:

1. §3.2, §3.3, §4.2, and §7.2 contain the runtime port rehost requirement and bar schedule from depending on `lilo-session-driver`.
2. §8.8 contains the identity `Action` and `ResourceSpec` prerequisite, plus schedule-specific acceptance and proof wording.
3. §2.2 describes `schedule_pool()` as a named alias over the single shared `SqlitePool`, with no second pool or database.
4. §2.2 uses `occupant_hint`, with `role_hint` absent.
5. §8 traces acceptance to the seven build plan items plus the cross-cutting authorization and audit requirement.
6. §3.1 and §9 include the schedule crate and wire dependency wiring.
7. §3.3 disambiguates `PaneCreate` from `PaneSplit`.

I mailed `helioy:orchestrator`: `I sign off on the schedule-matters spec as currently filed`.

## Peer Phase B Stale Delta Check

Peer 9:4.1 later reported two possible deltas: a §3.4 table regression and a §8 count echo. I immediately re-read the current live file and did not reproduce either issue:

- §3.4 lines 183-187 have `lilo create session` for declarative topology and `lilo run` for imperative single-agent placement.
- A heading scan shows §8.1 through §8.8 only, with no §8.9.
- §8 intro line 333 references the cross-cutting authorization and audit requirement in §8.8.

I notified both peer and orchestrator that the peer's deltas appear to be from an intermediate apply state or stale buffer. My clean sign-off stands.

## Peer Retraction and Both Reviewers Clean

Peer 9:4.1 retracted the stale Phase B defect report. They confirmed the earlier §3.4 and §8 issues were false and came from describing content before confirming the live read. No edits were made from that stale report.

Peer 9:4.1 then re-read the 437-line live file, verified all seven consensus edits, and signed off clean: `I sign off on the schedule-matters spec as currently filed.` I acknowledged the retraction, confirmed our live reads now match, and notified `helioy:orchestrator` that both reviewers are clean.
