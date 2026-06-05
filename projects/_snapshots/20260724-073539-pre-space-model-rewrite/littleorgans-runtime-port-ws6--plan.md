# WS6 — conformance breadth + robustness + tmux hermeticity (runtime-port closeout)

> Cold-read handoff for the WS6 warroom. Branch `feat/runtime-port-conformance`, worktree
> `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans-worktrees/runtime-port-conformance`
> (off `main` @ `8bde1e5`). Last runtime-port workstream. Implement the cards in order.

**Goal:** Finish the runtime-port boundary — make tmux capture tests hermetic (ALP-2607),
broaden dual-adapter conformance to the remaining `RuntimePort` methods + lock
`SpawnConflict` error-parity, and harden two recovery/resilience loops.

## Scope decisions (LOCKED with Stuart — do not re-add)
- **SKIP** a merged shutdown-ordering test — it already exists and is comprehensive
  (`tests/integration/tests/shutdown_contract.rs`, StopRpc/CtrlC/SIGTERM stage order).
- **SKIP** an explicit Linux assertion — CI is **Ubuntu-only** (`.github/workflows/pr.yml`),
  so the Linux cfg-gated seams (SO_PEERCRED, pidfd) already compile AND run on every PR.
- **SKIP** the rev03 full-chain ordering test — the Tx-A ordering is already asserted
  (`session_spawn_contract.rs::session_spawn_persists_fixed_order_across_two_transactions`);
  a full kqueue→record test mostly re-covers the reaper. Marginal.
- **NO production error-type change.** The in-process `Runtime(String)` vs wire
  `Client(ClientError)` split is correct provenance, not a defect (see
  `NOTES/bounded-context-port-error-model.md`). C2 only adds a `SpawnConflict` conformance
  test to lock the one caller-matched variant.

## Card C1 — tmux-capture hermeticity (ALP-2607)

**File:** `internal/runtime/platform/src/test_support.rs` (`TmuxSession`).

Today `TmuxSession::start` uses a unique session **name** (`rtm-capture-{uuid}`) but shares
the **default tmux server** (no `-L` socket). Under parallel `nextest`, every tmux test
hits one server → contention → `wait_for_capture` polling races/timeouts (the ALP-2607
flake; it has bitten real gate runs).

**Fix:** give each `TmuxSession` its **own tmux server** via a unique `-L <socket>` label
(derive from the same UUID). EVERY tmux CLI invocation (`new-session`, `list-panes`,
`capture-pane`, `resize-pane`, `send-keys`, `kill-session`, …) must pass `-L <socket>`.
Teardown (`Drop`) must kill the **server** (`tmux -L <socket> kill-server`), not just the
session, so no orphan server/socket leaks. Keep the graceful "tmux unavailable → skip"
behavior.

**Verify:** `capture_tmux_pane_returns_snapshot_json` (`internal/runtime/app/tests/integration_pass5.rs`)
passes; run the runtime-app tmux tests repeatedly / under nextest parallelism to confirm
no contention. **Acceptance:** per-test tmux server isolation; gate green incl. capture.

## Card C2 — conformance breadth + SpawnConflict parity

**File:** `internal/session/driver/tests/port_conformance.rs` (+ `tests/common/mod.rs` harness if needed).

Current cross-adapter conformance covers nudge, capture, reap_exited, terminate (+ spawn
success via `rtmd_spawn.rs`). **Gaps:** `status`, `poll_events`, `doctor`.

1. Add cross-adapter conformance (InProcessRuntime ≡ RtmdDriver via `mock_rtmd_server`) for
   `status` (StatusFilter → `Vec<Lifecycle>` shape parity), `poll_events` (EventsRequest →
   `EventBatch` parity), `doctor` (`RuntimeDoctorReport` parity). Follow the existing
   per-method harness pattern.
2. Add a **SpawnConflict-parity** test: both adapters yield
   `DriverError::SpawnConflict { kind, message }` for a conflict — in-process via domain
   `Ok(SpawnOutcome::Conflict)` → `spawn_outcome` → `conv::spawn_conflict`; socket via wire
   `SpawnConflict` → `ClientError::SpawnConflict` → `spawn_error` → `conv::spawn_conflict`.
   This locks the one caller-matched error variant (the rule from
   `NOTES/bounded-context-port-error-model.md`).

**Acceptance:** every `RuntimePort` method + the conflict path has cross-adapter
conformance; gate green.

## Card C3 — loop robustness

**File:** `internal/session/daemon/src/{events.rs, handler/spawn.rs}`.

1. **Watcher loop** (`events.rs::run_event_loop`): `poll_events().await?` currently `?`-ends
   the loop on error with no retry; only `handle_batch` errors retry (`EVENT_ERROR_RETRY`
   sleep). Make a `poll_events` error also log + sleep(`EVENT_ERROR_RETRY`) + continue; the
   loop exits only on the shutdown signal. (In-process `poll_events` is infallible today;
   this hardens the future socket port whose `poll_events` can `Err`.)
2. **Reconcile loop** (`spawn.rs::reconcile_pending_spawn_intents`): the per-intent `?`
   aborts the whole sweep on one intent's failure. Log + continue per intent so one bad
   intent doesn't block recovery of the rest. (WS5 carry-forward.)

**Tests:** a reconcile test where one intent fails and the others still reconcile; for the
watcher loop, a test that a `poll_events` error does not terminate the loop (likely needs a
fault-injecting `RuntimePort`, or assert structurally). **Acceptance:** one failing intent
doesn't block others; a poll error doesn't kill the watcher; gate green.

## Out of scope / carry-forward
- Shared error-model for bounded-context ports — design before the 2nd service
  (`NOTES/bounded-context-port-error-model.md`, design §5.1, cm `019e73c2`).
- macOS-in-CI coverage (CI is Ubuntu-only; the macOS seams — getpeereid, kqueue — are only
  exercised locally). Separate CI-infra decision.

## Execution
One warroom (Codex `helioy-tools:backend-engineer` + Claude `superpowers:code-reviewer`),
cards C1→C2→C3 sequential, reviewer audit per commit. Trust nothing agent-reported: verify
SHAs + diffs + the full gate yourself. C1 is the highest-value (real flake); C2/C3 are
test+robustness.
