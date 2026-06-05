# WS2 (+WS3) — Session RuntimePort + In-Process Adapter Implementation Plan

> **For agentic workers:** Execution vehicle is **moe-local-batch** (Codex `backend-engineer` implements against the live tree, Claude `code-reviewer` does two-phase design+diff sign-off per commit). Cards lock exact sites, decisions, and acceptance; the engineer ports bodies from the cited refs and reads the real code. Steps use `- [ ]`.

**Goal:** Make the composed `lilod` session layer reach the runtime through one in-process `RuntimePort` instead of dialing the daemon's own socket (or self-`handle_rpc`), delete the loopback machinery, and stop the session background tasks before `db.close()`.

**Architecture:** Introduce `trait RuntimePort` (session vocabulary). Two adapters over **one shared, socket-agnostic conversion layer** (`conv.rs` + `terminal_child_exit`): `InProcessRuntime` (holds `Arc<RuntimeService>`, calls the WS1 domain API directly) for the composed daemon, and `RtmdDriver` (socket) for the split/v2 topology. `DaemonState` holds `Arc<dyn RuntimePort>` in place of `driver + runtime + rtmd_socket_path`. The runtime returns `lilo_rm_core` types; the shared conv maps them to the session's own types so both adapters are behaviour-identical.

**Tech Stack:** Rust, tokio; crates `lilo-session-driver` (port + adapters + conv), `lilo-session-daemon` (DaemonState + tasks + handlers), `lilo-session-app` (compose), `lilo-runtime-daemon` (the WS1 domain API consumed in-process).

**Source of truth:** `~/.mdx/projects/littleorgans-runtime-port-boundary--design.md` (§3 two surfaces, §3.1 cleanliness, R1; WS2/WS3 rows). Grounding refs below are from merged `main` bb09304.

---

## Locked design decisions (do not re-litigate)

- **DD1 — `RuntimePort` unifies ALL composed runtime access.** The trait covers every site the composed session uses today via either `RtmdDriver` or a raw `RuntimeClient`: `spawn`, `reap_exited`, `validate_target`, `capture`, `probe_session`, `terminate`, `nudge`, `status`, `poll_events`, `doctor`, `terminate_all`. No composed runtime access may bypass the port (no `RuntimeClient::new`, no `runtime.handle_rpc` from the session). Exact method set is confirmed at Phase A against the call sites.
- **DD2 — Shared conversion layer is the DRY core.** Extract the socket-agnostic mappers into a shared module both adapters call: `terminal_child_exit` (rtmd.rs:236-253, `Lifecycle → ChildExit`), `lifecycle_to_probe` (conv.rs:44), `lifecycle_transcript_path` (conv.rs:109), `runtime_kind` (conv.rs:113), `nudge_result`, and the `lilo_rm_core → session DoctorResponse/NudgeResponse/CaptureResponse` maps. Adapters differ ONLY in how they fetch raw `lilo_rm_core` data (in-process call vs socket).
- **DD3 — `InProcessRuntime` over `Arc<RuntimeService>`.** Each port method calls the WS1 domain method then the shared conv: `spawn → runtime.spawn`; `reap_exited → runtime.status(empty) + terminal_child_exit`; `capture → runtime.capture`; `terminate → runtime.kill_runtime (+ terminal wait, port-side)`; `nudge → runtime.nudge_runtime`; `validate_target → runtime.validate_target`(via handle path or a domain method — confirm at Phase A); `probe_session → runtime.status + lifecycle_to_probe`; `status → runtime.status`; `poll_events → runtime.poll_events`; `doctor → runtime.doctor + session map`. No socket, no `handle_rpc`.
- **DD4 — `DaemonState` holds `Arc<dyn RuntimePort>`.** Remove `driver: Arc<RtmdDriver>` and `rtmd_socket_path`; keep `runtime: Arc<RuntimeService>` only if still needed elsewhere (else remove). The composed daemon (session-app `compose`) constructs `InProcessRuntime(Arc::clone(&runtime))` and injects it.
- **DD5 — `spawn` de-RPC.** `spawn.rs:70` `self.runtime.handle_rpc(principal, RuntimeRpc::Spawn{..})` → `port.spawn(..)` (in-process: `runtime.spawn`). `RuntimeResponse::Spawned` unwrap disappears. Identity/authz stays where it is for now (WS4 owns authz; WS2 is behaviour-preserving on the authz axis — confirm spawn still audits as today, since WS1 noted in-process spawn audit rides on the path).
- **DD6 — In-process event loop sheds remote machinery.** `events.rs` `run_event_loop` drops `RuntimeClient::new` per-iteration, `EventWatcher` connect, `BACKOFF_*` / `next_backoff`, and reconnect-on-disconnect. It loops `port.poll_events(since)` and applies via `handle_batch`; the genuine `CursorExpired` reconcile calls `port.status()` + `reconcile_lifecycles`. Cursor persistence semantics unchanged.
- **DD7 — WS3 explicit task lifecycle (same landing).** Background tasks start after `bind` and are explicitly stopped before `runtime.shutdown()`/`remove_socket_file`/`db.close()` (today they drop at end of `main`, after `db.close`). Add `SessionService::shutdown()` (aborts + awaits the tasks) called from `compose.rs` teardown before `db.close`. `eprintln!` → `tracing` in lifecycle.rs/events.rs.
- **DD8 — `RtmdDriver` stays as the socket adapter** implementing `RuntimePort` over the shared conv; delete only what's truly dead in BOTH topologies (e.g. the empty `terminate_all` stub becomes a real impl or the port default). Dead-in-composed-only methods are retained for the socket adapter, not deleted, unless dead everywhere.
- **Behaviour preservation:** every existing test passes at every commit; the wire protocol and DB semantics are unchanged. No file >700 LOC, no fn >150 LOC.

### Open Phase-A questions (warroom adjudicates, like WS1 T2)
- **Q1 — Crate placement.** Recommended: `trait RuntimePort` + both adapters + shared conv all in `lilo-session-driver` (high cohesion), which gains a dep on `lilo-runtime-daemon` for `InProcessRuntime` (no cycle: runtime-daemon does not dep session-driver). Alternative: trait in driver, `InProcessRuntime` in `lilo-session-app` (keeps driver free of the runtime-daemon dep). Reviewer picks.
- **Q2 — `terminate` terminal-wait placement.** `RtmdDriver::terminate` does a status-poll wait-for-terminal loop. In-process, decide whether the wait lives in the adapter or is a port-level shared helper over `status`.
- **Q3 — `validate_target` in-process path** (does `RuntimeService` expose it as a domain method, or must WS2 add it / route via an existing method).

---

## Grounding refs (merged main bb09304)

| Site | File:Line | Current call |
|---|---|---|
| reaper | lifecycle.rs:38-49 | `state.driver.reap_exited()` → `Vec<ChildExit>` |
| watcher | events.rs:47,66,113-125 | `RuntimeClient::new` + `EventWatcher`; `handle_batch`; `CursorExpired`→`status_client.status()`+`reconcile_lifecycles` |
| reconcile | reconcile.rs:13-23 | `RuntimeClient::new().status(empty)` → `StatusPayload` |
| doctor | polish.rs:138 | `RuntimeClient::new().doctor()` → `DoctorResponse` |
| capture/terminate | sessions.rs:49-54,111-118 | `driver.capture` / `driver.terminate` |
| terminate_all | service.rs:108 | `driver.terminate_all()` (no-op) |
| spawn | spawn.rs:70-78 | `runtime.handle_rpc(principal, RuntimeRpc::Spawn{..})` → `RuntimeResponse::Spawned` |
| shared conv | conv.rs:44/109/113 + rtmd.rs:236-253 | `lifecycle_to_probe`, `lifecycle_transcript_path`, `runtime_kind`, `terminal_child_exit`, `nudge_result` |
| state | handler/state.rs:11-44 | `driver: Arc<RtmdDriver>`, `runtime: Arc<RuntimeService>`, `rtmd_socket_path` |
| build | service.rs:57-77 | `RtmdDriver::new`; `LifecycleTask::spawn(state)`; `RuntimeEventTask::spawn(state, socket_path)` |
| shutdown | compose.rs:123-141 | drop(listener)→drain→`runtime.shutdown()`→`remove_socket_file`→`db.close()`; SessionService dropped only at `main` exit |

---

## Commits (on `feat/session-runtime-port` → one PR)

### C1 — Extract shared conversion module (DRY prep, behaviour-preserving)
**Files:** Modify `internal/session/driver/src/conv.rs`; move `terminal_child_exit` from `rtmd.rs:236-253` into `conv.rs`; keep `RtmdDriver` calling the moved fns.
- [ ] Move `terminal_child_exit` (+ any rtmd-local mapping helpers) into `conv.rs` as `pub(crate)` socket-agnostic fns; `RtmdDriver` calls them.
- [ ] Run `cargo test -p lilo-session-driver` + `cargo test -p lilo-session-daemon` → green (pure move, no behaviour change).
- [ ] Commit: `refactor(session-driver): extract socket-agnostic runtime conversions (WS2)`.

### C2 — `RuntimePort` trait + `InProcessRuntime` adapter; `RtmdDriver` impls it; `DaemonState` holds the port
**Files:** `internal/session/driver/src/` (new `port.rs` + `in_process.rs` per Q1); `rtmd.rs` (impl trait); `internal/session/daemon/src/handler/state.rs`; `internal/session/app/src/compose.rs` (+ `service.rs`).
- [ ] **D-line first** (Phase A): resolve Q1/Q2/Q3, the exact trait method set, and the `Arc<dyn RuntimePort>` wiring. Reviewer signs off before code.
- [ ] Define `trait RuntimePort` (DD1) + `InProcessRuntime` (DD3, over `Arc<RuntimeService>`, using shared conv); impl `RuntimePort` for `RtmdDriver` (DD8).
- [ ] `DaemonState` field becomes `runtime: Arc<dyn RuntimePort>` (DD4); `compose`/`build` inject `InProcessRuntime(Arc::clone(&runtime_service))`.
- [ ] Conformance test: both adapters satisfy a shared trait-level test where feasible (in-process always; socket behind a feature/integration gate).
- [ ] `cargo test` workspace-scoped → green; behaviour preserved. Commit: `feat(session): RuntimePort trait + in-process adapter (WS2)`.

### C3 (WS2a) — Migrate reaper + watcher + reconcile onto the port
**Files:** `lifecycle.rs`, `events.rs`, `reconcile.rs`.
- [ ] Reaper: `state.runtime_port.reap_exited()` (DD3); delete the `state.driver` path.
- [ ] Watcher: rewrite `run_event_loop` to loop `port.poll_events(since)` (DD6); delete `RuntimeClient::new`, `EventWatcher`, `BACKOFF_*`, `next_backoff`, reconnect-on-disconnect; keep cursor persistence + `CursorExpired` reconcile via `port.status()`.
- [ ] Reconcile: `port.status()` instead of `RuntimeClient::new().status()`.
- [ ] `eprintln!` → `tracing` here (DD7 logging half).
- [ ] `cargo test` green; assert negative LOC in events.rs/lifecycle.rs. Commit: `refactor(session): reaper/watcher/reconcile via in-process port (WS2a)`.

### C4 (WS2b) — Migrate doctor + capture/terminate/nudge/validate_target/probe_session + spawn-de-RPC
**Files:** `polish.rs`, `handler/sessions.rs`, `handler/messaging.rs`, `handler/target.rs`, `handler/spawn.rs`.
> **NARROWED (C4 Phase-A adjudication, 2026-05-29): C4 = DOCTOR MIGRATION ONLY.** capture/terminate/nudge already moved to the port in C2; validate_target/probe_session deleted in C6. The spawn de-RPC + the other spawn.rs self-RPCs DEFER to WS4: de-RPCing a MUTATING verb drops a real runtime `Action` decision-audit row that only WS4's domain state-change audit replaces.

- [ ] doctor: `polish.rs` `RuntimeClient::doctor` → `state.runtime.doctor()`. Doctor-shape parity (C2 carry-forward): `RuntimeDoctorReport` matches the old `polish.rs` doctor JSON; in-process yields `socket_path: None` + `code: None` vs socket both — acceptable; assert `lilo doctor` user-visible output unchanged.
- [ ] **Read-audit-drop (principle):** doctor is a READ, so dropping its redundant runtime-side `Action::Doctor` door-audit row is acceptable (§4: no domain audit for reads; the session-side audit at `polish.rs:52` remains). UPDATE `assert_delete_flow_audit` (agent_lifecycle.rs:148) from 2 Doctor rows → 1. **WS2 drops a runtime-side door audit ONLY for reads; mutating verbs defer to WS4.**
- [ ] Verify the doctor gate (`polish.rs:128`) still works once doctor uses the port (the `rtmd_socket_path` FIELD removal stays C6).
- [ ] `cargo test` workspace + `just check` green. Commit: `refactor(session): migrate doctor to in-process port (WS2b)`.
- **DEFERRED TO WS4** (spawn-lifecycle self-RPCs in `spawn.rs`, stay on `handle_rpc` with TODOs): `:72` Spawn (mutating), `:165` recovery Kill (mutating), `:272` reconcile Status (read, grouped with the spawn flow). `compose.rs:166` is the external wire door (§4) and stays.

### C5 (WS3) — Background-task shutdown ordering
**Files:** `internal/session/daemon/src/service.rs` (add `SessionService::shutdown()`); `internal/session/app/src/compose.rs`.
- [ ] Add `SessionService::shutdown()` that aborts + awaits `LifecycleTask`/`RuntimeEventTask`.
- [ ] In `compose.rs` teardown, call `session.shutdown().await` BEFORE `runtime.shutdown()`/`remove_socket_file`/`db.close()` (DD7) — mirrors session-matters `sm-daemon/src/server.rs:45-47`. Tasks start after `bind`.
- [ ] Shutdown-ordering test (merged Stop/Ctrl-C/SIGTERM) asserts no task tick after `db.close`. Commit: `fix(session): stop background tasks before db close (WS3)`.

### C6 — Dead-code sweep + fmm
**Files:** `rtmd.rs` (unused-in-both methods, `terminate_all` stub), `state.rs` (`rtmd_socket_path`), any orphaned imports.
- [ ] `fmm` dead-code/glossary sweep on touched modules; delete what's dead in BOTH topologies; resolve `terminate_all` via the port; remove `rtmd_socket_path`.
- [ ] **C3 carry-forward — kill the doctor gate with the field:** `polish.rs:54` gates `reconcile_once` on `rtmd_socket_path.is_some()`. After C3 `reconcile_once` uses the port, so when `rtmd_socket_path` is removed here the gate MUST be removed/replaced at the same time, or doctor's fresh reconcile silently disables.
- [ ] `just check && just build && just test` green; `fmm generate && fmm validate`. Commit: `chore(session): remove dead socket-loopback code (WS2)`.

---

## Acceptance (WS2+WS3 exit)
- **No composed socket dial; `handle_rpc` only on the deferred spawn-lifecycle path**: grep shows zero `RuntimeClient::new` in `internal/session` composed paths, and zero `runtime.handle_rpc` EXCEPT `spawn.rs`'s 3 spawn-lifecycle self-RPCs (Spawn :72, recovery Kill :165, reconcile Status :272), explicitly deferred to WS4. All other runtime access flows through `Arc<dyn RuntimePort>`. (The `compose.rs` wire door serves external clients per §4 — out of scope.)
- Both ENOENT windows gone; clean teardown with no store-after-close (WS3 test).
- Watcher reconnect/backoff machinery deleted (negative LOC in events.rs/lifecycle.rs).
- Behaviour preserved: all pre-existing tests green at every commit; spawn still audited.
- Dual-adapter: `InProcessRuntime` and `RtmdDriver` share the conv layer; conformance test passes.
- `just check && just build && just test` green; `fmm validate` clean; no file >700 / fn >150.

## Out of scope (later)
- WS4 authz no-bypass + domain state-change audit; WS5 spawn-recovery hardening; WS6 conformance + rev03 ordering tests + Linux assertion + the tmux-capture hermeticity fix.
- **WS6 (C2 carry-forward):** runtime-access error-type divergence is inherent — in-process `DriverError::Runtime(String)` vs socket `DriverError::Client(ClientError)`. Conformance pins success/outcome parity, not error parity. Note and decide acceptability in WS6.
- **WS6 (C3 carry-forward):** the watcher loop's `poll_events().await?` is a no-op for the infallible in-process port, but a future **socket** port's `poll_events` Err would end the loop with no retry. Decide loop-resilience for the socket topology in WS6.
- **WS4 (C4 deferral):** de-RPC `spawn.rs`'s 3 spawn-lifecycle self-RPCs (Spawn :72, recovery Kill :165, reconcile Status :272) to the port, landing WITH the domain state-change audit for the mutating ones (Spawn/Kill) so the dropped runtime decision-audit row is replaced (no regression). This is why WS2 leaves them on `handle_rpc`. The session-side `begin_spawn_intent` audit already covers the spawn; the runtime row is redundant de-dup that WS4 formalizes.

## PR-body note (carry-forward)
- Describe `terminate_all → drain_shims` accurately: it is an **idempotent shim reap already in the composed shutdown path** (`RuntimeService::shutdown`/`drop` call it; e68c301), NOT a no-op. It does terminate tracked shims, but C2 adds no new kill (behaviour-preserving).
