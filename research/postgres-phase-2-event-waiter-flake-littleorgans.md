---
title: Postgres Phase 2 Event Waiter Flake Diagnosis For littleorgans
type: research
tags: [littleorgans, postgres, phase-2, flaky-test, event-log, runtime]
summary: The failed event waiter test is a pre-existing transient observation race exposed by heavier Postgres and full workspace contention, not a semantic event log cutover regression.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Executive Summary

`lilo-runtime-app::integration_events_cursor::timed_out_long_poll_releases_waiter` does not point to a semantic Phase 2 event log regression. The event log implementation and watcher polling helper are unchanged from `main`; the failure comes from a test sampling a short lived waiter counter through a separate RPC.

There is one important correction to the implementer framing. The runtime event log itself is file backed and DB free, but the full `Events` and `Watchers` RPC path still writes identity audit rows before reaching the handler. Phase 2 moved those audit writes from SQLite to Postgres, which makes the old timing race easier to expose under full workspace load.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`
- Branch: `feat/postgres-phase-2`
- HEAD: `0fe786a6c51605b3af7af9a0a8f9007c1b9920f3`
- fmm: indexed and valid, `389 files`
- Test target: `lilo-runtime-app::integration_events_cursor::timed_out_long_poll_releases_waiter`
- Local Postgres container: `littleorgans-postgres-1`, host port `55433`

## Architecture

### Event long poll path

- `RuntimeRpc::Events` is accepted by the daemon handler, then authorization runs before dispatch in `internal/runtime/daemon/src/handler.rs:132`.
- Authorization maps `RuntimeRpc::Events` and `RuntimeRpc::Watchers` to `Action::Read` in `internal/runtime/daemon/src/identity.rs:86-87`.
- The stub authorizer records an audit row before allowing the action in `crates/lilo-im-stub/src/lib.rs:49-51`.
- On the Phase 2 branch, that audit insert goes through Postgres in `crates/lilo-im-store/src/sqlite/audit.rs:245-258`.
- The actual event wait happens in `internal/runtime/daemon/src/event_log.rs:190-214`.

### Waiter counter path

- `EventLog` stores waiter count as `AtomicUsize` in `internal/runtime/daemon/src/event_log.rs:37`.
- The waiter guard increments the counter at `internal/runtime/daemon/src/event_log.rs:235-238`.
- The guard is created only after the immediate and second event checks pass, at `internal/runtime/daemon/src/event_log.rs:209`.
- The guard drops and decrements the counter at `internal/runtime/daemon/src/event_log.rs:241-244`.
- `ServerState::watcher_counts` reads the event waiter count at `internal/runtime/daemon/src/server/state.rs:255-260`.

## Detailed Findings

### 1. Relevant event log files did not change versus `main`

`git diff main...HEAD` showed no changes in:

- `internal/runtime/daemon/src/event_log.rs`
- `internal/runtime/daemon/src/server/events.rs`
- `internal/runtime/app/tests/common/wait.rs`
- `internal/runtime/daemon/src/handler.rs`

The event cursor integration test file changed only to mark tests as ignored for Postgres and to switch `write_event_log` from `harness.db_path().parent()` to `harness.data_dir()`.

### 2. The full RPC path is not strictly DB independent

The event log implementation is file backed JSONL plus an in memory waiter counter, but every `Events` and `Watchers` RPC still passes through identity authorization:

- Dispatch authorizes before matching RPC variants: `internal/runtime/daemon/src/handler.rs:132`.
- `Watchers` and `Events` are read actions: `internal/runtime/daemon/src/identity.rs:86-87`.
- Authorization records audit before allow: `crates/lilo-im-stub/src/lib.rs:49-51`.
- Phase 2 audit writes use Postgres: `crates/lilo-im-store/src/sqlite/audit.rs:245-258`.

So the implementer was correct about the event log substrate, but over scoped the DB independence claim. The full integration test path includes audit DB writes before both the long poll request and each watcher sampling request.

### 3. The race is a transient counter sampling bug

The failing test does this:

- Starts a daemon harness: `internal/runtime/app/tests/integration_events_cursor.rs:256`.
- Samples baseline watcher count: `:257`.
- Spawns a thread that performs `runtime_events_rpc_path(..., Some(100))`: `:258-259`.
- Polls until the watcher count reaches `baseline + 1`: `:260`.
- Joins the event waiter after it times out, then checks the count returned to baseline: `:262-268`.

The sampling helper issues a new `RuntimeRpc::Watchers` request on each check in `internal/runtime/app/tests/common/wait.rs:144-156`, and `wait_until` sleeps 25 ms between checks at `internal/runtime/app/tests/common/wait.rs:172-179`.

The sampled state exists only while `EventWaiterGuard` is alive. The guard is created at `internal/runtime/daemon/src/event_log.rs:209` and released when the `select!` completes at `:210-213`. With a 100 ms long poll, the visible interval is intentionally short. Under full workspace load, sampling can miss that interval, especially because each sample itself runs through the audited RPC path.

### 4. Isolated proof did not reproduce the failure

Targeted command used:

```bash
LILO_TEST_DATABASE_URL=postgres://lilo:lilo@localhost:55433/lilo \
CARGO_TARGET_DIR=target/nextest \
cargo nextest run -p lilo-runtime-app \
  --test integration_events_cursor \
  timed_out_long_poll_releases_waiter \
  --run-ignored ignored-only
```

Results:

- First isolated run: passed.
- Six additional isolated runs in a loop: passed.
- Total targeted runs in this session: 7 passed, 0 failed.

This supports a load sensitive flake rather than a deterministic SQL cutover defect.

## Deterministic Fix

Do not keep widening timeout windows or rebuilding runtimes in the polling helper. Replace client side transient polling with daemon side waiter synchronization.

Recommended design:

1. Add a waiter state notification primitive to `EventLog` near `internal/runtime/daemon/src/event_log.rs:33-38`.
   - A `tokio::sync::watch::Sender<usize>` is best because it preserves the latest count and wakes waiters on changes.
   - A `Notify` plus an atomic count also works, but callers must recheck in a loop.
2. Change `EventWaiterGuard::new` at `internal/runtime/daemon/src/event_log.rs:235-238` to publish the incremented count.
3. Change `Drop for EventWaiterGuard` at `internal/runtime/daemon/src/event_log.rs:241-244` to publish the decremented count.
4. Add a daemon internal wait operation, for example `wait_for_event_waiters(at_least, timeout)`, exposed through a debug or test only RPC.
   - The handler should await the daemon state transition once, inside the daemon, rather than making the test process issue repeated `Watchers` RPC calls.
   - The RPC can remain internal to test support and should not add user CLI surface.
5. Update `timed_out_long_poll_releases_waiter` at `internal/runtime/app/tests/integration_events_cursor.rs:260` to await that deterministic waiter state instead of calling `wait_for_event_waiters_at_least`.

A smaller fallback for this one test would remove the pre timeout `baseline + 1` observation and assert only that the count returns to baseline after the waiter joins. That catches leak regressions, but it no longer proves the waiter was registered, so the daemon side sync is the stronger fix.

## Dependencies

- `tokio::sync::Notify` and `tokio::sync::watch` are already part of the runtime daemon dependency surface through Tokio.
- No new external dependency is needed.
- No database schema change is needed.

## Relevance to Helioy

This is the same class of issue as other Helioy control plane tests that observe transient runtime state through a separate audited RPC. When the thing being tested is an in process transition, a sticky or awaitable daemon side signal is more robust than client side polling through the public RPC path.

## Open Questions

- Should the debug wait RPC live in `RuntimeRpc`, or should integration tests launch the daemon with a test synchronization channel? The RPC is cleaner for cross process integration tests, but it needs an internal contract boundary.
- Should `Watchers` and `Events` read only RPCs always audit under tests? Current code does, and that is useful coverage, but it also makes watcher sampling sensitive to audit backend latency.

## Bus Reply Sent

Reply sent to `littleorgans:general:5:2.1` on topic `pg2-flake`:

`FLAKE-DIAG: regression=no; root=internal/runtime/app/tests/integration_events_cursor.rs:260 samples a transient event_log.rs:209 waiter via Watchers RPC, whose wrapper still DB-audits; fix=event_log.rs:33/209 add Notify-backed waiter-state sync plus an internal wait-for-watchers RPC, then have the test await that instead of polling`
