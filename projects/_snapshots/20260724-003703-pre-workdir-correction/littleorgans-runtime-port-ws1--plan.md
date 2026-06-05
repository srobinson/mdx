# WS1 — Runtime Domain API Implementation Plan

> **For agentic workers:** Execution vehicle is **moe-local-batch** (Codex implements against the live tree, Claude reviews the diff, two-phase sign-off per item). Tasks lock exact files, target symbols, design decisions, and acceptance — the engineer ports bodies from the cited source lines and reads the real code; do NOT work from this plan alone. Steps use `- [ ]` for tracking.

**Goal:** Turn `internal/runtime/daemon` into a bounded context with a curated in-process **runtime domain API** on `RuntimeService`, and demote `handle_rpc` to a thin adapter over it — so co-located callers (the session layer, WS2) reach the runtime by direct call, not by socket or self-RPC.

**Architecture:** `RuntimeService` (already the public service factory) gains public async methods that delegate to the existing `pub(crate)` `ServerState` methods and return **public `lilo_rm_core` contract types** (never runtime-crate-internal types). `handle_rpc` becomes `deserialize → authorize_runtime_rpc → domain method → wrap RuntimeResponse`. The `spawn` arm's inline 8-step sequence is extracted into a domain `spawn` method. Authz stays on `handle_rpc` (the wire door); state-change audit at the domain layer is deferred to WS4.

**Tech Stack:** Rust, tokio, sqlx; crates `lilo-runtime-daemon` (impl), `lilo-rm-core` (wire/contract types: `Principal` is `lilo-im-core`).

**Source of truth:** `~/.mdx/projects/littleorgans-runtime-port-boundary--design.md` (§3 two-surface model, §3.1 cleanliness, §4 audit door/domain split, R1 surface discipline). This plan implements WS1 only.

---

## Locked design decisions (do not re-litigate)

- **DD1 — Inherent methods, not a runtime-side trait.** The domain API is public async methods on `RuntimeService` delegating to `pub(crate)` `ServerState`. The only trait is the *session-side* `RuntimePort` (WS2). Keeps `ServerState` crate-private.
- **DD2 — Public return types only (R1).** Every domain method returns a `lilo_rm_core` public payload (or `lilo-im-core`/std), never `EventLogPage`, `KillOutcome`, or other runtime-crate-internal types. The session crate must be able to name every return type. `handle_rpc` wraps the public payload into the matching `RuntimeResponse` variant.
- **DD3 — `spawn` derives append-suppression from the request, no caller flag.** `begin_spawn` already returns `session_backed`; the domain `spawn` keeps `record_running(&request, ready, !session_backed)` exactly as today. Session-backed requests therefore suppress the runtime append automatically, and the session layer publishes post-Tx-B via `append_event` (rev07 d9) in WS2. WS1 adds no flag — it is a pure structural extraction.
- **DD4 — Authz stays at the door.** Domain methods do NOT call `authorize_runtime_rpc`. `handle_rpc` keeps it (handler.rs:133). State-change audit at the domain layer is WS4, not WS1. WS1 is behaviour-preserving.
- **DD5 — `subscribe_events` ships as a long-poll primitive.** WS1 exposes `RuntimeService::poll_events(EventsRequest) -> Result<EventBatch, _>` over the same `events_since_or_wait` the wire path uses. The streaming `watch_events` loop is WS2 (session side).
- **Behaviour preservation:** every existing `lilo-runtime-daemon` test passes unchanged at every commit. WS1 changes structure, not observable behaviour. No file exceeds 700 LOC, no function 150 LOC.

---

## File structure

- Modify: `internal/runtime/daemon/src/service.rs` — add public domain methods (`spawn`, `poll_events`, `status`, `kill_runtime`, `kill_by_pid`, `nudge_runtime`, `capture`, `doctor`; `append_event`/`drain_shims` already public).
- Modify: `internal/runtime/daemon/src/handler.rs` — demote each `handle_rpc` arm to authz + domain call + wrap.
- Modify: `internal/runtime/daemon/src/server/state.rs` — only if a `pub(crate)` method must change its return type to a public contract type (prefer mapping in `service.rs` to avoid touching `ServerState`).
- Possibly create: `internal/runtime/daemon/src/api.rs` — if the domain methods + their doc-contract are cleaner in one `impl RuntimeService` block kept under 700 LOC. Decide during T2; default is to keep them in `service.rs` unless it crosses the limit.
- Test: `internal/runtime/daemon/src/service.rs` `#[cfg(test)]` module + existing handler tests.

---

## Task 1 — `poll_events` in-process primitive

**Files:** Modify `internal/runtime/daemon/src/service.rs`; the `Events` arm in `handler.rs:~205`.

**Decision:** `poll_events` returns the **public** `EventBatch` (`lilo_rm_core`) — the same shape the session watcher already consumes — mapping the internal `EventLogPage` → `EventBatch::Events { events, cursor }` and `CursorExpired { oldest }` → `EventBatch::CursorExpired { oldest }`. The wire `Events` arm and `poll_events` share this one mapping (DRY).

- [ ] **Step 1: Write the failing test.** In `service.rs` tests, build a `RuntimeService`, append one `RuntimeEvent`, then assert `service.poll_events(EventsRequest{since:None, wait_ms:None}).await` returns `EventBatch::Events` whose events + cursor equal what a `handle_rpc(principal, RuntimeRpc::Events(req))` returns (same batch via two doors).
- [ ] **Step 2: Run it, confirm it fails** (`poll_events` undefined).
  Run: `cargo test -p lilo-runtime-daemon poll_events -- --nocapture` → FAIL.
- [ ] **Step 3: Implement `pub async fn poll_events(&self, request: EventsRequest) -> RuntimeResponse`** (or `-> EventBatch`; pick the public return that the session crate can consume — confirm `EventBatch` is `lilo_rm_core` public). Body delegates to the same path the `Events` arm uses (`EventAppender::events` → `events_since_or_wait`, event_log.rs:190) and maps `EventLogPage`/`CursorExpired` → `EventBatch`. Extract the mapping into one helper reused by the `Events` `handle_rpc` arm.
- [ ] **Step 4: Refactor the `Events` `handle_rpc` arm to call `poll_events`** (or the shared mapping helper). No behaviour change.
- [ ] **Step 5: Run tests, confirm pass** (`cargo test -p lilo-runtime-daemon`). All green incl. existing event tests.
- [ ] **Step 6: Commit** — `feat(runtime): add in-process poll_events over events_since_or_wait (WS1)`.

---

## Task 2 — Extract the `spawn` domain method

**Files:** Modify `internal/runtime/daemon/src/service.rs` (+ `handler.rs` Spawn arm). Port the sequence verbatim from `handler.rs:135-173`.

**Sequence to encapsulate** (from the extraction facts):
1. `spawn_preflight::check(&state, &mut request).await?` (136) — may early-return a conflict.
2. `lilo_runtime_launchers::dispatch(&request.runtime)?.launch_spec(&request)?` (139-140).
3. `RuntimeBackends::new(state.config()); backends.prepare_launch(&request, launch)?` (141-142).
4. `state.begin_spawn(&request, launch.clone()).await?` → `BeginSpawn { ready, session_backed }` (143).
5. `backends.spawn(&request, &launch).await?` with cancel-on-error (144-147).
6. `tokio::time::timeout(Duration::from_secs(10), begin.ready).await?` → `ShimReady` (152-155).
7. `state.record_running(&request, ready, append_event).await?` → `(Lifecycle, RuntimeEvent)` (156-158).
8. Build the spawn outcome (the data behind `RuntimeResponse::Spawned(SpawnedPayload{ lifecycle, event, log_dir, stdout_path, stderr_path })`, 167-173) **or** the conflict outcome.

**Decision:** `pub async fn spawn(&self, request: SpawnRequest) -> Result<SpawnOutcome>`, where `SpawnOutcome` is a public enum `{ Spawned(SpawnedPayload), Conflict(SpawnConflictPayload) }` built from existing public `lilo_rm_core` payloads. The method runs steps 1-8 and keeps `record_running(&request, ready, !begin.session_backed)` exactly as today (DD3) — append-suppression is derived from the request, not a caller flag. Pure structural extraction; no behaviour change.

**Phase-A consensus rulings (2026-05-29, both panes):**
- **`SpawnOutcome` lives in the daemon crate** (re-export at crate root), NOT `lilo_rm_core`/`proto.rs`. It is a domain return, never serialized; the wire stays `RuntimeResponse::Spawned`/`SpawnConflict`. DD2 is met because `internal/session/{app,daemon}` already depend on `lilo-runtime-daemon`. Add nothing to `proto.rs` (T1 precedent).
- **Logic on `ServerState`, `RuntimeService::spawn` delegates.** `handle_rpc_result` holds `Arc<ServerState>`, not `RuntimeService` (handler.rs:128) — so the spawn logic is a `pub(crate)` fn over `&ServerState` (mirroring `poll_events_batch`); `RuntimeService::spawn` delegates to it; the Spawn arm calls it and maps `SpawnOutcome → RuntimeResponse`.
- **Narrow the preflight return.** `spawn_preflight::check` currently returns `Result<Option<RuntimeResponse>>` whose `Some` is always `SpawnConflict` (via `conflict()`, spawn_preflight.rs:300). Change `conflict()` to return `SpawnConflictPayload{kind,lifecycle}` and `check` to `Result<Option<SpawnConflictPayload>>`; wrap to `RuntimeResponse::SpawnConflict` only at the wire door. The domain then builds `SpawnOutcome::Conflict(payload)` directly.
- **Test fixture:** reuse the existing synthetic-`ShimReady` fixture (`complete_shim_ready`, state.rs:119; handler/tests.rs:203-204); do not build a parallel harness.

- [ ] **Step 1: Write the failing test.** Assert `service.spawn(test_request()).await` yields a `SpawnOutcome::Spawned` whose `lifecycle` + `event` match what `handle_rpc(principal, RuntimeRpc::Spawn(req))` produced for the same request (two doors, same result). Include a conflict-path test if `spawn_preflight` is unit-reachable.
- [ ] **Step 2: Run it, confirm fail** (`spawn` undefined). `cargo test -p lilo-runtime-daemon spawn_domain -- --nocapture`.
- [ ] **Step 3: Implement `RuntimeService::spawn`** by moving steps 1-8 out of the `handle_rpc` Spawn arm into the method, returning `SpawnOutcome`. Preserve the cancel-on-error (147) and the 10s `ShimReady` timeout (152). Keep `record_running(..., !session_backed)`.
- [ ] **Step 4: Verify the method compiles and the new test passes.**
- [ ] **Step 5: Run full suite** `cargo test -p lilo-runtime-daemon` → all green.
- [ ] **Step 6: Commit** — `refactor(runtime): extract RuntimeService::spawn domain method (WS1)`.

---

## Task 3 — Demote the `handle_rpc` Spawn arm to a thin adapter

> **COLLAPSED INTO TASK 2 (Phase-A consensus, 2026-05-29).** Moving the body into the `ServerState` spawn fn forces the arm to call it to compile, so the thinning happens in the T2 commit. T3 is now a trivial confirmation step (verify the arm is `authz → spawn → match SpawnOutcome → RuntimeResponse`, no leftover logic), not a separate commit. Steps below are retained as the confirmation checklist.

**Files:** Modify `internal/runtime/daemon/src/handler.rs` (Spawn arm, 135-173).

- [ ] **Step 1:** Replace the inline 8-step body with: `let outcome = state.<service-handle>.spawn(request).await?;` then `match outcome { Spawned(p) => RuntimeResponse::Spawned(p), Conflict(c) => RuntimeResponse::SpawnConflict(c) }`. Authz at line 133 stays. (Confirm how the arm reaches the `RuntimeService`/`ServerState` — port the call accordingly; `spawn` may live on `ServerState` if `handle_rpc` only holds `&ServerState`. If so, define `spawn` on `ServerState` and have `RuntimeService::spawn` delegate to it — keep DD2 public return either way.)
- [ ] **Step 2:** Confirm the arm is now < ~15 lines and contains no business logic.
- [ ] **Step 3: Run** `cargo test -p lilo-runtime-daemon` → existing spawn RPC tests pass unchanged (behaviour preserved).
- [ ] **Step 4: Commit** — `refactor(runtime): Spawn handle_rpc arm delegates to domain spawn (WS1)`.

---

## Task 4 — Curate + expose the remaining domain verbs

**Files:** Modify `internal/runtime/daemon/src/service.rs` (+ corresponding `handle_rpc` arms).

For each verb below, add a public `RuntimeService` method delegating to the existing `pub(crate)` `ServerState` method, returning a **public** payload (DD2), and make the matching `handle_rpc` arm call it + wrap:

| Domain method (public) | Delegates to (state.rs) | Public return |
|---|---|---|
| `status(StatusFilter)` | `status` (211) | `Vec<Lifecycle>` (confirm `Lifecycle` is `lilo_rm_core`-public) |
| `kill_runtime(KillRequest)` | `kill_runtime` (140) | public kill payload (map `KillOutcome` → wire payload) |
| `kill_by_pid(KillByPidRequest)` | `kill_pid` (144) | `KillByPidResponse` |
| `nudge_runtime(NudgeRequest)` | `nudge_runtime` (148) | `NudgeResponse` |
| `capture(CaptureRequest)` | `capture_pane` (180) | `CaptureResponse` |
| `doctor(...)` | (current Doctor arm) | public doctor payload |

`append_event` (service.rs:81) and `drain_shims` (104) are already public — no new method, just confirm they're part of the documented surface.

- [ ] **Step 1: Write one failing test per verb** asserting the domain method and the wire arm return equal results for the same input (two doors). Group into one `#[test]` module; one assertion per verb.
- [ ] **Step 2: Run, confirm fail.** `cargo test -p lilo-runtime-daemon domain_surface -- --nocapture`.
- [ ] **Step 3: Implement each public method** delegating to the `pub(crate)` `ServerState` method, mapping internal → public return where needed. If a map is non-trivial (e.g. `KillOutcome` → wire), put the map in one helper, not duplicated in the arm.
- [ ] **Step 4: Refactor each `handle_rpc` arm** to call the domain method + wrap. Arms become thin.
- [ ] **Step 5: Run full suite** → green. Check `service.rs` LOC < 700; if exceeded, move the domain `impl` block to `internal/runtime/daemon/src/api.rs`.
- [ ] **Step 6: Commit** — `refactor(runtime): expose curated domain verbs on RuntimeService (WS1)`.

---

## Task 5 — Lock the surface as a reviewed contract + R1 guard

**Files:** Modify `internal/runtime/daemon/src/service.rs` (doc) + add a cross-crate smoke test.

- [ ] **Step 1:** Add a module/`impl`-level doc comment enumerating the runtime domain API as the curated public surface (the contract reviewed under R1), with one line stating: session vocabulary (`reap_exited`, `terminate`, `watch_events`, `terminate_all`) does NOT appear here — it lives on the WS2 `RuntimePort` and maps onto these verbs.
- [ ] **Step 2: Write a compile-only consumer test** (in this crate's tests, simulating the session crate's view) that names every public domain method + every return type, proving no runtime-internal type leaked (DD2/R1). If any return type is not nameable outside the crate, fix the signature.
- [ ] **Step 3: Run** `cargo test -p lilo-runtime-daemon` and `cargo build --workspace` → green.
- [ ] **Step 4:** `fmm generate && fmm validate` (exports changed).
- [ ] **Step 5: Commit** — `docs(runtime): document the runtime domain API surface + R1 guard test (WS1)`.

---

## Acceptance (WS1 exit)

- `handle_rpc` is `deserialize → authorize_runtime_rpc → domain method → wrap`; no business logic remains in any arm (esp. Spawn).
- Every domain method returns a type nameable by the session crate; no `EventLogPage`/internal type in any public signature (R1).
- `poll_events` and `spawn` return identical results to their wire-RPC counterparts (two-doors-same-result tests pass).
- All pre-existing `lilo-runtime-daemon` tests pass unchanged (behaviour preserved; authz still at the door).
- `just check && just build && just test` green; `fmm validate` clean; no file > 700 LOC, no fn > 150 LOC.

## Out of scope (later workstreams)

- Session `RuntimePort` trait, `InProcessRuntime` adapter, migrating the 7 session sites, `watch_events` loop, deleting `events.rs`/`reconcile.rs`/`polish.rs`/`sessions.rs` socket dials → **WS2**.
- Shutdown ordering → **WS3**. Authz no-bypass + domain state-change audit → **WS4**. Spawn recovery → **WS5**. Conformance + ordering + Linux tests → **WS6**.
