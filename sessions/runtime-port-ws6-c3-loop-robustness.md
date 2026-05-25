---
title: Runtime port WS6 C3 loop robustness
type: sessions
tags: [backend, session-daemon, runtime-port, resilience, WS6]
summary: Made the event watcher and spawn reconcile loops resilient to per-iteration errors with focused regression tests.
status: active
source: backend-engineer
confidence: high
created: 2026-05-29
updated: 2026-05-29
---

## Summary

Implemented WS6 Card C3 for ALP-2816 on `feat/runtime-port-conformance`.

Commit: `97a0e34a9332583e9168838e8132399814169ff9`

Key decisions:

- `run_event_loop` now treats `poll_events` errors like batch handling errors: log, sleep `EVENT_ERROR_RETRY`, and retry without advancing the cursor.
- `reconcile_pending_spawn_intents` now logs per-intent failures and continues with later pending intents instead of aborting the whole sweep.
- The watcher regression uses a fault-injecting `RuntimePort` that fails once, then returns an event batch. The test proves the loop retries and persists the later cursor.
- The reconcile regression uses one failing pending intent and one healthy pending intent. The healthy intent resolves in the same sweep.
- The integration contract for Tx B failure now expects the sweep to return `Ok(())` while preserving pending state and avoiding an event append until a later successful reconcile.

## API Contract

No public API endpoints, commands, or wire schemas changed.

Internal runtime port behavior now has this resilience contract:

```rust
// Event watcher
poll_events_error -> log + sleep(EVENT_ERROR_RETRY) + continue

// Spawn reconciliation
single_intent_error -> log + continue remaining pending intents
```

## Database Changes

None.

The Tx B failure integration test still verifies that failed session commit attempts do not append a runtime event and do not resolve the pending spawn intent before the commit succeeds.

## Security Considerations

No auth, permission, or secret handling changed. The changes improve recovery behavior without weakening authorization or audit boundaries.

## Performance Notes

The watcher sleeps `EVENT_ERROR_RETRY` before retrying a poll failure, preventing a tight loop against a failing runtime port. Spawn reconciliation continues after a failed intent, so one bad row no longer blocks recovery for the rest of the backlog.

## Verification

- `cargo test -p lilo-session-daemon events::tests::poll_events_error_retries_and_processes_next_batch -- --nocapture`: PASS.
- `cargo test -p lilo-session-daemon handler::spawn::tests::reconcile_pending_spawn_intents_continues_after_failed_intent -- --nocapture`: PASS.
- `cargo test -p lilo-integration-tests --test session_spawn_contract startup_reconcile_appends_d9_only_after_tx_b_commit -- --nocapture`: PASS.
- `cargo fmt --all && just check && just build && just test`: PASS. `just test` reported `420 tests run: 420 passed, 0 skipped`.
- `fmm generate && fmm validate`: PASS, 364 files indexed and current.
- `git diff --check`: PASS.
- `git status --short --branch`: clean after commit.

## Open Items

- WS6 C1, C2, and C3 are complete and reported. Await review or next directive before pushing.
