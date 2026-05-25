---
title: littleorgans Runtime Port Boundary Review
type: research
tags: [littleorgans, runtime, session, architecture, peer-consensus, ALP-2816]
summary: Final live re-read confirmed all consensus changes landed, and I signed off clean on the runtime-port design as filed.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-29
updated: 2026-05-29
---

## Executive Summary

The reviewed design, `~/.mdx/projects/littleorgans-runtime-port-boundary--design.md`, proposes Option D: a session RuntimePort over a curated runtime domain API. Live tree analysis supports the direction, but the filed API is missing load-bearing surfaces required by current R11 and composed daemon behavior.

The main required changes are: extract runtime spawn out of `handle_rpc_result`, add a post-commit event publication method for d9 JSONL, replace session doctor and reconcile socket self-dials, expand audit classification, and broaden the cleanup list beyond events, lifecycle, and `RtmdDriver`.


## Peer Consensus Update

Round 1 converged with the Claude peer. I concurred with the merged conditional signoff after verifying the added audit-coupling claim against `IdentityClient` and `StubAuthorizer`.

Merged apply set sent to the orchestrator:

1. WS1 and R1 must require a real runtime spawn domain method, extracted from `handler.rs:135-173`, and expose `append_event` or `publish_committed_event` for rev07 d9 post-commit publication.
2. R1 must show runtime domain API and session RuntimePort as two distinct labeled surfaces with explicit port-to-domain mapping. Port vocabulary includes spawn, subscribe_events, status, reap_exited, terminate, terminate_all, capture, doctor, and append_event. Dead `probe_session` and `validate_target` must be deleted or justified as socket-adapter-only.
3. Section 4 must drop the claim that placement is settled. Decision audit, including denials, remains at the wire door. State-change audit is added at the domain layer for mutating verbs: spawn, kill, kill by pid, nudge, terminate all or drain, shim ready, shim exit, and post-commit append. The principal must be threaded to the domain audit and door versus domain audit must avoid double counting while preserving current in-process spawn audit.
4. Section 3.1 cleanup must include `reconcile.rs`, `polish.rs`, `sessions.rs`, the `events.rs` CursorExpired reconcile path, all `rtmd_socket_path` uses, the `terminate_all` stub, and dead `probe_session` and `validate_target`.
5. WS2 must widen or split to migrate all composed runtime access off the socket and off `handle_rpc`, not only reaper and watcher. WS3 shutdown ordering should remain non-optional within the same landing.


## Final Consensus

Round 1 consensus reached with the Claude peer. Both panes signed off conditional on the same five item apply set. I acknowledged the consensus to the peer and orchestrator and stated that I would not edit the design artifact under the original review-only directive.

Final apply set:

1. WS1 and R1 must require a real runtime spawn domain method extracted from `handler.rs:135-173`, plus `append_event` or `publish_committed_event` for rev07 d9 post-commit publication.
2. R1 must separate runtime domain API from session RuntimePort and include explicit port-to-domain mapping. The port carries spawn, subscribe_events, status, reap_exited, terminate, terminate_all, capture, doctor, and append_event. Dead `probe_session` and `validate_target` must be deleted or justified as socket-adapter-only.
3. Section 4 must remove the claim that placement is settled. Decision audit, including denials, stays at the wire door. State-change audit is added at the domain layer for spawn, kill, kill by pid, nudge, terminate all or drain, shim ready, shim exit, and post-commit append. The design must thread principal into domain audit and avoid double counting.
4. Section 3.1 cleanup must include `reconcile.rs`, `polish.rs`, `sessions.rs`, the `events.rs` CursorExpired reconcile path, all `rtmd_socket_path` uses, the `terminate_all` stub, and dead `probe_session` and `validate_target`.
5. WS2 must widen or split to migrate all composed runtime access off the socket and off `handle_rpc`, not just reaper and watcher. WS3 shutdown ordering remains non-optional within the same landing.


## Final Re-read Signoff

After the orchestrator applied the consensus changes, I re-read `~/.mdx/projects/littleorgans-runtime-port-boundary--design.md` live and confirmed all five items landed. The document status is `round-1-consensus-applied`.

Verified landed changes:

1. WS1 now requires extracting a real runtime spawn domain method from `handler.rs:135-173` and exposes `append_event` for rev07 d9 post-commit publication. See design lines 225-231.
2. Section 3 now separates the runtime domain API from the session RuntimePort, with port-to-domain mappings for `reap_exited`, `terminate`, `watch_events`, and `publish_committed_event`. See design lines 96-128.
3. Section 4 now defines the door and domain audit split, preserves decision audit including denials at the wire door, adds domain state-change audit, threads principal, de-duplicates, and calls out the ValidateTarget Action::Spawn hazard. See design lines 177-206.
4. Section 3.1 now includes the expanded deletion list: `reconcile.rs`, `polish.rs`, `sessions.rs`, `events.rs` CursorExpired reconcile, all `rtmd_socket_path` uses, `terminate_all`, and dead `probe_session` and `validate_target`. See design lines 153-171.
5. WS2 now covers all seven composed runtime-access sites plus `spawn.rs` de-RPC, allows an optional WS2a/WS2b split, and makes WS3 non-optional in the same landing. See design lines 232-247.

The withdrawn event-log dedup item and the acceptance assertion that in-process spawn remains audited are also present. See design lines 55-59 and 293-296.

Final bus signoff sent: `I sign off on the runtime-port design as currently filed`.


## Peer Clean Signoff

Claude peer also sent clean final signoff after a live re-read: `I sign off on the runtime-port design as currently filed`. The peer confirmed all five consensus items landed, plus the dedup withdrawal and the acceptance assertion that in-process spawn remains audited. I acknowledged the clean peer signoff to the peer and orchestrator, with no further concerns from Codex.

## Project Metadata

- Language: Rust, workspace edition 2024, rust-version 1.95 in `Cargo.toml`.
- Build system: Cargo workspace, Moon CI, root `justfile` gate.
- Workspace size from fmm: 354 indexed files, 44,576 LOC.
- Relevant crates and modules:
  - `internal/runtime/daemon`: runtime domain state, wire handler, event log, service facade.
  - `internal/session/daemon`: session handler, background lifecycle and event tasks, session doctor, reconcile.
  - `internal/session/driver`: current `RtmdDriver` socket adapter.
  - `internal/session/app`: composed `lilod` entry point.
- fmm status: `.fmm.db` and `.fmmrc.toml` exist. `fmm validate` passed for all 354 files.

## Architecture

### Current composed daemon shape

`compose.rs` constructs one `RuntimeService` and one `SessionService`, then binds the shared socket afterward. `SessionService::build` creates an `RtmdDriver`, stores both the driver and the in-process `Arc<RuntimeService>`, and starts the lifecycle and event background tasks before the listener is bound.

Evidence:

- `internal/session/app/src/compose.rs:76-85` builds runtime and session services.
- `internal/session/app/src/compose.rs:91-94` prepares and binds the socket after service construction.
- `internal/session/daemon/src/service.rs:57-72` creates `RtmdDriver`, stores `RuntimeService`, then spawns lifecycle and event tasks.
- `internal/session/daemon/src/handler/state.rs:25-38` stores `driver`, `runtime`, and optional `rtmd_socket_path`.

### Runtime handler shape

`RuntimeService::handle_rpc` is currently a facade over `handler::handle_rpc`. The handler authorizes at the wire adapter, then dispatches most verbs into `ServerState` methods.

Already delegated:

- `ValidateTarget` to `state.validate_target_request`, `internal/runtime/daemon/src/handler.rs:175-178`.
- `Kill` to `state.kill_runtime`, `internal/runtime/daemon/src/handler.rs:180-182`.
- `KillByPid` to `state.kill_pid`, `internal/runtime/daemon/src/handler.rs:183-185`.
- `Nudge` to `state.nudge_runtime`, `internal/runtime/daemon/src/handler.rs:186-189`.
- `Capture` to `state.capture_pane`, `internal/runtime/daemon/src/handler.rs:190-192`.
- `Status` to `state.status`, `internal/runtime/daemon/src/handler.rs:193-195`.
- `Events` to `events_response`, then `state.events`, `internal/runtime/daemon/src/handler.rs:205` and `231-241`.
- Shim callbacks to `take_launch_spec`, `complete_shim_ready`, and `record_shim_exit`, `internal/runtime/daemon/src/handler.rs:212-222`.

Not yet thin:

- `Spawn` still owns preflight, launcher dispatch, backend preparation and spawn, ShimReady timeout, and `record_running` inside `handle_rpc_result`, `internal/runtime/daemon/src/handler.rs:135-158`.

## Key Patterns

### Boundary pattern is sound, but spawn needs extraction

Option D is feasible because runtime already has a domain state object, `ServerState`, and most wire verbs call methods on it. The design should not claim the runtime API merely needs public exposure. WS1 must extract a real runtime spawn domain method so the wire adapter and in-process adapter share one implementation.

### Event subscription can reuse the existing cursor contract

The in-process event subscription can call the same path the wire API uses today:

- `ServerState::events` delegates to `EventAppender::events`, `internal/runtime/daemon/src/server/state.rs:227-232`.
- `EventAppender::events` calls `EventLog::events_since_or_wait`, `internal/runtime/daemon/src/server/events.rs:15-22`.
- `EventLog::events_since` filters `entry.seq > cursor` and returns the last sequence, `internal/runtime/daemon/src/event_log.rs:167-188`.
- `EventLog::events_since_or_wait` uses Notify plus a second check to avoid lost wakeups, `internal/runtime/daemon/src/event_log.rs:190-214`.

The design's lost-wakeup refutation is correct. The dedup-drop fact is true, but its impact should be described as duplicate event wait latency, not data loss, because d9 intentionally deduplicates by event key.

### R11 requires a post-commit event publication seam

Session-backed spawn deliberately suppresses the runtime event append during runtime `record_running`, then appends d9 JSONL only after session Tx B commits.

Evidence:

- Runtime spawn calls `record_running(..., !begin.session_backed)`, so session-backed spawns do not append immediately, `internal/runtime/daemon/src/handler.rs:156-158`.
- Session completion commits the session row, lifecycle update, and intent resolution, then calls `self.runtime.append_event(event)`, `internal/session/daemon/src/handler/spawn.rs:209-230`.
- R11 requires d9 JSONL to append after SQLite commit and never serve as commit authority, `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:356-367` and `488-497`.

The proposed RuntimeApi list omits this method. It needs an explicit `append_event` or more precise `publish_committed_event` API.

## Detailed Findings

### 1. Feasibility

Option D is real, not aspirational, for most runtime verbs. The existing wire handler is already close to an adapter over `ServerState` methods. Spawn is the exception and must be extracted during WS1.

Substantive issue: The spec says the runtime domain API already exists, merely private. That is false for `Spawn`. A correct WS1 should move the spawn orchestration out of `handle_rpc_result` and then have both wire and in-process callers use the same domain method.

### 2. RuntimeApi surface discipline

The proposed surface, `reap_exited`, `subscribe_events`, `spawn`, `status`, `terminate`, `nudge`, `terminate_all`, is too narrow for the composed daemon's current session use.

Required additions or explicit alternatives:

1. `append_event` or `publish_committed_event`, required by R11 post-Tx-B d9 publication.
2. `doctor` or an explicit replacement, because session doctor still self-dials `RuntimeClient::doctor` in `internal/session/daemon/src/polish.rs:127-155`.
3. `capture`, if all composed session runtime access is to leave the socket, because session capture still calls `driver.capture` in `internal/session/daemon/src/handler/sessions.rs:49-53`.


Surface distinction: `reap_exited` and `terminate_all` are session port vocabulary, not existing runtime domain methods. `RtmdDriver::reap_exited` derives child exits from `client.status()` plus terminal lifecycle derivation, `internal/session/driver/src/rtmd.rs:88-100`. A clean R1 design should map port verbs onto runtime domain methods rather than exposing session reaping semantics directly from `RuntimeService`.

`terminate_all` should be reviewed as a lifecycle ownership method rather than a general session runtime capability. Current runtime has `RuntimeService::shutdown` and `drain_shims`, while the socket `RtmdDriver::terminate_all` is an empty stub at `internal/session/driver/src/rtmd.rs:169`.

### 3. Authz and audit

Runtime authz at the wire adapter is correct if every external runtime call enters through the composed socket and peer credentials remain the trust boundary.

Evidence:

- `compose.rs` extracts peer credentials before dispatching runtime or session RPC, `internal/session/app/src/compose.rs:152-177`.
- Runtime wire dispatch calls `authorize_runtime_rpc` before matching the verb, `internal/runtime/daemon/src/handler.rs:128-134`.
- Runtime authorization maps raw runtime verbs to identity actions, `internal/runtime/daemon/src/identity.rs:77-104`.


Additional audit verification from the peer was confirmed live:

- `IdentityClient::authorize` calls `authorize_with_stub`, which calls `authorizer().authorize`, `internal/identity/service/src/client.rs:51-61` and `91-100`.
- `StubAuthorizer::authorize` evaluates the local decision and records an audit row before returning allow or deny, `crates/lilo-im-stub/src/lib.rs:43-61`.
- `IdentityClient::authorize_in_tx` also records an audit row before returning allow or deny, `internal/identity/service/src/client.rs:63-85`.

Consequence: direct in-process runtime domain calls that skip authz would also skip the current decision audit unless the design adds explicit domain-layer state-change audit and preserves door-level decision audit for external calls, including denials.

Substantive issue: audit classification in the spec is incomplete. The mutating or side-effecting runtime set should explicitly include spawn, kill, kill by pid, nudge, stop or drain all shims, shim ready, shim exit, and post-commit event append. Reads include status, events or subscribe, version, watchers, doctor, capture, validate target, and reap exited.

### 4. Cleanup completeness

The deletion list should include every composed daemon socket self-dial, not only the event watcher and lifecycle reaper.

Additional cleanup targets:

- `internal/session/daemon/src/reconcile.rs:13-23` calls `RuntimeClient::status` through `rtmd_socket_path`.
- `internal/session/daemon/src/polish.rs:127-155` calls `RuntimeClient::doctor` through `rtmd_socket_path`.
- `rtmd_socket_path` is stored in `DaemonState` and used in service, server, reconcile, polish, and tests.
- `RuntimeClient::new` and `EventWatcher` in `internal/session/daemon/src/events.rs:38-86` should disappear from the composed daemon path.
- `BACKOFF_INITIAL`, `BACKOFF_MAX`, and `next_backoff` in `internal/session/daemon/src/events.rs:13-14` and `131-133` become reconnect-only leftovers after in-process subscription.
- `RtmdDriver::validate_target` and `RtmdDriver::probe_session` have no composed callers after the import and need deletion or socket-adapter conformance justification.

### 5. Workstream ordering

WS1 to WS2 to WS3 is directionally sound, but WS2 depends on a larger WS1 surface than filed. WS3 should not be deferred across separately shipped PRs because current background tasks are still aborted only when `SessionService` drops, after runtime shutdown, socket removal, and DB close.

Evidence:

- Shutdown sequence calls `runtime.shutdown`, removes socket, closes DB, and only later drops `session`, `internal/session/app/src/compose.rs:123-142`.
- `SessionService::drop` only touches `terminate_all`; task aborts occur through field drops after the drop body, `internal/session/daemon/src/service.rs:105-109`, `lifecycle.rs:33-35`, and `events.rs:33-35`.
- The sibling `session-matters` precedent explicitly drops events and lifecycle before driver termination and cleanup, `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters/crates/sm-daemon/src/server.rs:41-48`.

WS5 stays within rev07 R11 as long as it only hardens the Tx-A, runtime side effect, Tx-B, abort, and reconcile semantics around `session_spawn_intents`.

### 6. Verified inventory

Confirmed:

- Composed daemon loopback exists for lifecycle, events, reconcile, and doctor paths.
- Startup order starts background session tasks before socket bind.
- Shutdown ordering leaves session task ownership alive through runtime shutdown, socket removal, and DB close.
- Session authz gaps exist for `List`, `NamespaceCreate`, `NamespaceGet`, `NamespaceList`, `MailCheck`, `MailStopCheck`, and `Wait`, as shown in `internal/session/daemon/src/handler/dispatch.rs:48-80` and the target method bodies.
- Runtime wire authz exists through `authorize_runtime_rpc`.
- Event lost-wakeup refutation is supported by the notify-before-wait pattern in `EventLog::events_since_or_wait`.
- Cursor off-by-one is refuted by the `entry.seq > cursor` filter and last sequence return.

Adjusted wording:

- Event dedup-drop is a confirmed code fact, `internal/runtime/daemon/src/event_log.rs:138-142`, but the consequence should be phrased as wait latency for idempotent duplicates, not event data loss.

## Dependencies

Critical dependencies and roles:

- `tokio`: async runtime, Unix sockets, tasks, cancellation and signal handling.
- `sqlx`: shared SQLite pool and transaction management.
- `lilo-db`: shared `LiloDb` root for Phase 7 one-pool design.
- `lilo-im-core`, `lilo-im-store`, `lilo-identity-service`: principal, RBAC, audit and authorization.
- `lilo-rm-core`, `lilo-rm-client`: current runtime wire protocol and client adapter.
- `lilo-runtime-store`: runtime lifecycle persistence.
- `lilo-session-store`: session records, mail, namespaces and spawn intents.

## Verification

Commands run:

```bash
fmm validate
cargo test -p lilo-runtime-daemon event_log --lib
```

Additional targeted fmm verification after peer reply:

- `IdentityClient.authorize`
- `IdentityClient.authorize_in_tx`
- `IdentityClient.authorize_with_stub`
- `StubAuthorizer.authorize`
- `StubAuthorizer.record`

Results:

- `fmm validate`: all 354 files indexed and up to date.
- `cargo test -p lilo-runtime-daemon event_log --lib`: 6 passed, 0 failed.

No target codebase files were modified.

## Relevance to Helioy

This review validates the bounded-context port pattern for Helioy: external wire RPCs act as trust doors, co-located callers use direct domain ports, and conformance tests keep wire and in-process adapters aligned. The pattern should carry forward only if each port includes the real transactional seams, especially post-commit publication points like the session-backed d9 event append.

## Open Questions

1. Should `terminate_all` be a session RuntimePort method, or should it remain a compose-layer runtime shutdown concern?
2. Should runtime domain audit produce separate audit rows for session-backed runtime side effects, or should the existing session Tx-A audit be linked to the runtime side effect?
3. Should duplicate event append wake long-poll subscribers as a liveness optimization despite d9 idempotence, or should the design remove the dedup-drop item from the real-defect list?
4. Should `RtmdDriver::validate_target` and `RtmdDriver::probe_session` survive only in split topology tests, or be deleted now?
