---
title: WS5 spawn recovery hardening
type: sessions
tags: [backend, littleorgans, session-daemon, spawn-recovery, WS5]
summary: Implemented direct-spawn inline runtime abort cleanup for Tx-B commit failure while preserving reconcile retry semantics.
status: active
source: backend-engineer
confidence: high
created: 2026-05-29
updated: 2026-05-29
---

## Summary

Implemented and amended WS5 Card C1 in commit `611717b19fdc7fdb4385473a6d343113fa6cb82a`.

`complete_spawn_intent` now uses one shared `abort_running_spawn` helper for permanent cleanup paths and accepts an `OnCommitFailure` policy for Tx-B failure. Direct spawn passes `AbortRunning`, so a Tx-B failure rolls back, best-effort terminates the spawned runtime, aborts the spawn intent, deletes the Forking lifecycle, and returns the original error. Reconcile passes `LeavePending`, so a transient Tx-B failure during startup recovery leaves the pending intent, Forking lifecycle, and live runtime intact for retry.

Namespace deletion still aborts in both direct spawn and reconcile because a deleted namespace is permanent. The generated surface guard and reconcile integration test were reverted to the base `d756059` versions as requested. The invariant test was renamed to describe its actual assertion: `abort_spawn_intent_clears_forking_and_marks_intent_aborted`.

## API Contract

No public CLI, daemon RPC, JSON, or wire contract changed.

Observable internal behavior changed only on direct spawn Tx-B failure: the original commit error is still returned, but the newly spawned runtime and pending intent are cleaned up before return.

## Database Changes

No schema migration was added.

Runtime behavior relies on existing atomic transactions:

- Tx-B rollback restores pre-commit state before cleanup.
- `abort_spawn_intent` updates the intent to `aborted` and deletes the Forking lifecycle in one transaction.
- Direct-spawn regression tests force Tx-B failure with a test-only SQLite trigger on `session_spawn_intents.status = 'resolved'` after a fake runtime returns Running.
- Reconcile retry semantics remain covered by `startup_reconcile_appends_d9_only_after_tx_b_commit`.

## Security Considerations

Authorization flow is unchanged.

The direct-spawn failure path now reduces orphaned runtime risk after a local database failure. Cleanup uses bounded best-effort SIGTERM through the existing runtime port. Cleanup failure is warned with session context while preserving the original Tx-B error for callers.

## Performance Notes

The success path only pays for the existing commit and event append plus an enum policy branch on failure. The new runtime termination path runs only for direct-spawn Tx-B failure and can wait up to the existing five second termination grace.

Verification passed:

- `cargo build -p lilo --bin lilo`, then `CARGO_BIN_EXE_lilo="$PWD/target/debug/lilo" cargo test -p lilo-session-daemon spawn_recovery --test handler -- --nocapture`: 2 passed.
- `cargo test -p lilo-session-daemon namespace_deleted_recovery_kills_runtime_before_abort --lib -- --nocapture`: 1 passed.
- `cargo test -p lilo-integration-tests startup_reconcile_appends_d9_only_after_tx_b_commit --test session_spawn_contract -- --nocapture`: 1 passed.
- `just check && just build && just test`: PASS, 161/161 nextest tests passed.
- `fmm validate`: PASS, 364 files indexed and current.

## Open Items

None for WS5 Card C1. Do not expand this into periodic reconcile work unless a later locked decision changes WS5 scope.
