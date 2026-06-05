---
title: littleorgans monorepo architecture review
type: research
tags: [littleorgans, architecture, review, monorepo, bounded-contexts, seams, release]
summary: Full architecture review at 2903ddc. Verdict is keep, do not scrap. Foundations are right; five contracts are declared but unenforced, with the spawn path seam bypass the highest-leverage fix.
status: active
created: 2026-08-25
updated: 2026-08-25
project: littleorgans
confidence: high
---

# littleorgans monorepo architecture review

Reviewed 2026-08-25 at commit `2903ddc`, main branch, clean tree. Method: four parallel expert reviews with file:line evidence (Session context, Runtime context, cross-context seams and shared platform, workspace and delivery), plus baseline checks in the coordinating thread. The three highest-stakes findings were re-verified directly in source before this document was written. Workspace compiles clean, `cargo check --workspace --all-targets` exit 0, zero TODO or FIXME markers, no source file over 700 lines, no function over ~125 lines.

## Verdict

Keep it. Do not scrap. The bounded context decomposition, the K8s-shaped mapping, the two-transaction intent pattern, the evidence-over-inference runtime philosophy, and the code hygiene are all genuinely good, and several of them are unusually good for a project at this stage. The defects the review found are concentrated, nameable, and fixable in flows, while the expensive-to-change decisions (context boundaries, id model, schema discipline, command model, one composed daemon with split-shaped seams) are correct.

Per-slice verdicts:

| Slice | Verdict |
| --- | --- |
| Session context (`internal/session/*`) | Sound with flaws |
| Runtime context (`internal/runtime/*`, `lilo-rm-*`, `lilo-sys`) | Sound with flaws |
| Cross-context seams (`wire`, `port`, `db`, identity, composition) | Seams partly real |
| Workspace and delivery (publish, CI, release, docs fidelity) | Partly coherent |

## What is genuinely strong

- The architecture docs are precise and testable. Ownership tables, explicit deferrals, provenance notes, and a locked launch attachment contract. Most concrete claims checked out against code (table names, composition root, crate maps).
- `authz_plan` is an exhaustive match with no `_` arm (`internal/session/daemon/src/handler/authz.rs:14-49`). A new `SessionRpc` variant fails to compile until its authorization boundary is declared. Best single piece of design in the repo.
- The two-transaction spawn protocol matches its documentation exactly, including audit-commit-on-deny and Tx B failure kill-and-abort, with real crash-window tests (`internal/session/daemon/tests/handler/spawn_recovery.rs`).
- Runtime process identity is proven rather than assumed: pid start-time comparison catches pid reuse (`internal/runtime/daemon/src/reconcile.rs:203-241`), kqueue/pidfd exit watchers, wall-clock gap detection for laptop sleep, and the agent environment travels over UDS after `env_clear()` instead of riding tmux.
- Schema discipline is real: `session_*` / `runtime_*` / `identity_*` prefixes, zero cross-context foreign keys or joins, forward-looking `owner` column.
- Substrate contracts have working gates where they exist: the `lilo_paths::env` const registry plus `scripts/check-env.sh` wired into `just check` and `moon ci`; per-test throwaway Postgres databases; integration tests that spawn the real `lilo daemon start` binary.
- One dispatch spine: CLI and MCP route through the same `SessionRpc` handlers with no duplicated business logic.

## The systemic weakness: declared contracts without enforcement

Every serious finding is an instance of one pattern. The repo declares a contract in docs or types, and no gate makes violating it fail. Documentation discipline is ahead of enforcement discipline.

1. The `RuntimePort` seam is the central architectural bet, and the spawn path bypasses it (details below).
2. `crates/` means "published crates only", and four of ten members cannot publish today, one of them with `publish = true` set (`crates/lilo/Cargo.toml:9`).
3. The docs claim "durable ... cursor addressed events" (`docs/architecture/runtime.md`), and the event log acks appends before fsync with seq recovery from the file tail (`internal/runtime/daemon/src/event_log.rs:19-20,117,447-457`).
4. The adapter parity contract exists (`internal/port`), and `prove_eq` is invoked exactly once in the workspace, in a test suite that compares the in-process port against a canned mock (`internal/session/driver/tests/port_conformance.rs:379-390,498-502`).
5. The runtime version gate exists, and an older client cannot parse a daemon that advertises one unknown capability, so it gets a JSON error instead of a mismatch report (`crates/lilo-rm-core/src/version.rs:105-148`).
6. The audit log records granular decisions ("action: kill, resource: session X, allow") that were actually one uid comparison (`crates/lilo-im-core/src/audit.rs:26-36`).

The general fix: for every contract the docs assert, add the gate that makes violation fail. A compile error, a CI check, or a conformance test against the real daemon. The repo already proves it can do this (`authz_plan`, `check-env.sh`); the pattern just has to reach the other contracts.

## Critical findings

### 1. The spawn path breaks the RuntimePort seam

Found independently by two reviewers, re-verified directly. `DaemonState` holds `Arc<dyn RuntimePort>` and a concrete `Arc<RuntimeService>` and a runtime-owned `LifecycleStore` (`internal/session/daemon/src/handler/state.rs:22-26`). The spawn commit writes `runtime_lifecycle` inside Session transactions (`internal/session/daemon/src/handler/spawn.rs:126,172,244`), the abort path deletes Runtime rows, and after commit Session injects an event into Runtime's log via `runtime_service.append_event`, a method that does not exist on `RuntimePort` (`spawn.rs:203`).

Consequence: split Session and Runtime into two processes, or insert Schedule between them, and the spawn/abort/reconcile protocol does not degrade, it ceases to exist. `RtmdDriver` can never carry production spawn traffic. Everything else (nudge, capture, terminate, status, events, doctor) genuinely goes through the port, which is why this is fixable rather than fatal.

The fix is already half-written in the repo. The reconcile path resolves pending intents by observing runtime evidence (`spawn.rs:254-320`), which is exactly the event-driven protocol the seam needs. Make Runtime the sole writer of `runtime_lifecycle`, let Session commit only its own rows, resolve intents by observing the Running event, and `SessionServiceContext` can take `Arc<dyn RuntimePort>` instead of the concrete service. Routing in-process dispatch through `handle_rpc(principal, ...)` at the same time closes the authz divergence between adapters (the in-process path currently skips `authorize_runtime_rpc`, which the socket path enforces). This must land before Issue 41 and Schedule build on the current shape, or a cheap refactor becomes a migration.

### 2. The event cursor is unsound across a daemon crash

Appends are acked before fsync (batch of 32 or 100 ms, `event_log.rs:19-20`), and `next_seq` recovers from the file tail (`event_log.rs:117`). Crash with an unsynced tail and reused seqs are assigned to new events; a client holding cursor N replays nothing and silently misses events forever, because `events_since` checks only the retention floor. There is no log-epoch identity, so a wiped file stalls watchers without a `CursorExpired`.

The elegant fix is subtraction: Postgres is already a hard dependency, and the 548-line bespoke JSONL engine (in-memory replica, torn-tail recovery, compaction, seq recovery) re-implements what an append-only `runtime_events` table with a sequence column provides for free. It would also let the Running event commit in the same transaction as the lifecycle row, closing a second crash divergence (`server/spawn.rs:186-205`). The JSONL choice reads as inherited from standalone `rtmd`'s no-database era. The v1-v2 note currently locks JSONL in; that lock predates Postgres becoming mandatory and deserves revisiting. Minimum fix if JSONL stays: fsync before ack plus a log epoch in the cursor.

### 3. The publish boundary and release pipeline do not exist yet

The actual publishable set is 6 of 10 `crates/` members (`lilo-common`, `lilo-paths`, `lilo-sys`, `lilo-im-core`, `lilo-im-store`, `lilo-im-stub`). Blocked: `lilo` (13 versionless internal path deps; it is a cargo-dist binary, so mark it `publish = false`), `lilo-rm-core` (versionless build-dep on unpublished `lilo-build-support`, `crates/lilo-rm-core/Cargo.toml:29-30`), and `lilo-rm-client` (normal dep on internal `lilo-wire`, which depends on internal `lilo-session-core`, a boundary inversion where the public runtime client transitively depends on private session types). `.github/workflows/` contains only `pr.yml`: no cargo-dist release workflow, no cargo-release config, no `cliff.toml`. The v0.8.0 release train described in CLAUDE.md is entirely unimplemented. `docs/architecture/runtime.md:188-189` calls `lilo-rm-core` and `lilo-rm-client` "published", which is false today.

## Major findings

- **Forking is never reconciled.** Startup and periodic sweeps iterate only Running rows, and a ShimReady timeout propagates without `cancel_spawn` (`internal/runtime/daemon/src/api.rs:96-98`). A shim that dies between Launch and Ready leaves a permanent Forking row nothing ever marks Lost.
- **Graceful shutdown kills every agent session; only a crash preserves them.** `drain_shims` SIGTERMs all shims on shutdown and even on Drop (`server/state.rs:44-46,337-346`), while the shim's 2.5-minute reconnect loop and `record_reconnected_ready` exist precisely to survive daemon absence. A `lilod` upgrade destroys sessions. Inverted kubelet semantics; adopt-on-restart should be the default and drain a flag.
- **Lost/Terminated diverge across three lifecycle writers.** The 200 ms reaper maps Lost runtime evidence to `TERMINATED` with null exit code (`internal/session/driver/src/conv.rs:83-104`, `daemon/src/lifecycle.rs:49-65`), while the event and reconcile paths map the same evidence to `LOST`. Whichever poller wins decides the terminal state; `mark_session_terminated` and `mark_session_lost` are unguarded, so a later writer can illegally flip them. `SessionState::Lost` is mostly unreachable in practice. One `apply_lifecycle_evidence` funnel with state-guarded SQL fixes this class.
- **Identity is authentication only.** Policy is `peer_uid == daemon_uid`; `Action` and `ResourceSpec` are audit metadata, never policy inputs; the stub is the production authorizer. Meanwhile `caller_session_id` is a client-asserted env var (`handler/dispatch.rs:14-40`), so any same-uid process can impersonate another agent's mail identity or drain its mailbox. Defensible v1 posture, but the RBAC shape has no tested seam for a real policy engine, and agent-level identity needs a daemon-issued credential before any of it means anything. Also `IdentityPort::authorize_in_tx(&mut LiloTransaction, ...)` bakes the shared database into the Identity contract (`internal/session/daemon/src/identity_client.rs:22-28`), which blocks Identity ever becoming a service behind this port.
- **Exit evidence race with a dead recovery branch.** The exit watcher sleeps 300 ms hoping ShimExit lands first; when the watcher wins it records `Exited(None, None)`, and the later accurate ShimExit hits a branch that mutates and returns `false`, which `record_terminal` discards (`crates/lilo-rm-core/src/types/lifecycle.rs:96-103`, `server/termination.rs:136-141`). True exit codes are lost whenever the shim reports slowly.
- **Secrets are durably retained as protocol payload.** The caller-env denylist is 4 names plus 3 prefixes (`crates/lilo-rm-core/src/spawn_context.rs:10-16`); everything else, including provider API keys, rides `SpawnRequest.env` into `session_spawn_intents.spawn_request_json`, which the locked contract retains with no encryption or cleanup. The attachment contract carefully bans secrets in `value` while the sibling field already carries them.
- **No foreign keys anywhere.** The namespace-delete versus spawn race is mitigated with best-effort checks on both sides; `ON DELETE RESTRICT` closes it structurally and deletes both mitigations. TEXT columns hold UUIDs.
- **Gate drift.** Generated surfaces have a working `xtask codegen --check` that no gate runs; `just check` scopes to changed crates, mutates the tree (fmt, clippy --fix), and skips DB tests that only CI runs, so local green and CI green are different claims.

## Minor findings (compressed)

Two selector-matching implementations with drift risk plus an N+1 label load (`store/src/postgres/sessions.rs:210-390`). `NamespaceCreate` authorized and audited as `Action::Kill`. A poison-row hazard where `lost_evidence_to_sql` writes `"unknown"` that `from_sql` cannot read back. `lilo-rm-core` bundles CLI rendering, MCP helpers, and a tools.toml registry behind unconditional tokio and toml deps with zero feature flags, a grab bag rather than a protocol crate. `lilo doctor` opens Postgres directly and names all three contexts' tables (`crates/lilo/src/cli/doctor.rs:241-281`). Mixed error taxonomy at the socket door (session-shaped errors for runtime requests and vice versa). Docker liveness probe blocks the tokio executor inside the sweep. `kill_runtime` signals a pid without the start-time check the repo already owns. Shutdown aborts in-flight connections before the drained marker. Legacy `rtm` and `sm` binaries still build against the one-brand rule. Doc drift: UUIDv7 claim at `docs/reference/env-vars.md:81`, "deleted on resolve" schema comment contradicting the retention contract, session-core "owning" an MCP envelope it re-exports from `lilo_rm_core`. Housekeeping: leftover `[patch.crates-io]` in `.cargo/config.toml`, Python scripts with `.sh` extensions, stale `.moon/workspace.yml` project enumeration, doctests never run in any gate.

## Priority order

1. **Fix the spawn seam** (critical 1). Event-driven intent resolution, Runtime as sole writer of its lifecycle, port-typed `SessionServiceContext`, in-process dispatch through `handle_rpc`. Collapses the seam bypass, the adapter authz divergence, and the driver-on-daemon dependency in one move. Do it before Issue 41 and Schedule land on the current shape.
2. **Move runtime events into Postgres** (critical 2), or minimally fsync-before-ack plus a log epoch. Revisit the JSONL lock with this durability evidence.
3. **One lifecycle evidence funnel** with state-guarded SQL, Forking reconciliation with a spawn deadline, and explicit exit-evidence precedence (shim exit supersedes watcher exit).
4. **Decide restart posture deliberately**: adopt-on-restart default, drain behind a flag.
5. **Repair the delivery story before the v0.8.0 train**: `publish = false` on `lilo`, unblock `lilo-rm-core` and `lilo-rm-client` (publish or inline build-support; move the shared envelope out of internal `lilo-wire`), generate the dist release workflow, add cargo-release and git-cliff config, and gate the boundary with `cargo publish --dry-run` per crate in CI. Wire `codegen --check` into the same gate set.
6. **Make Identity honest**: either shrink the audit vocabulary to the decision actually made, or make actions real policy inputs; issue a daemon-side caller credential; fix `NamespaceCreate` as `Kill`; redesign `authorize_in_tx` away from sqlx handles.
7. **Let Postgres enforce integrity**: foreign keys, UUID columns, guarded transitions.
8. **Seal or scrub spawn env at rest.**

## The scrap question, answered directly

Scrap would be right if the context boundaries were wrong, if the seams were fictional everywhere, or if the code were beyond the team's ability to hold. None of these is true. The boundaries match how the system will actually split. The seams are real for every flow except spawn, and the repo's own reconcile path already demonstrates the correct spawn protocol. Code health is excellent by direct measurement. The honest caveat is that Schedule, Transport, and Canvas are paper designs of high quality that no implementation has yet bent; expect the first vertical slice to amend them, and treat that as the design working, not failing.

The review's one lasting lesson for the project: a contract that no gate enforces will drift into fiction, and this repo now has five worked examples. The instinct to write contracts down is already there and it is the hard part. Adding the enforcement is mechanical.
