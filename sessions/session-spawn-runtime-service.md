---
title: Session Spawn Runtime Service Routing
type: sessions
tags: [backend, session, runtime, littleorgans]
summary: Routed session daemon spawn through RuntimeService and removed legacy driver trait indirection.
status: active
source: backend-engineer
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Summary

Implemented ALP-2859 W3 Commit 2 across branch `nancy/ALP-2817`.

Key commits:

- `b1d28fb` structural checkpoint
- `951cb35` session spawn through `RuntimeService`
- `989f19a7` driver trait cleanup follow up

The session daemon spawn path now uses the runtime service as the single launch authority. Legacy driver indirection was removed after Phase B review.

## API Contract

No public HTTP API changed.

Internal daemon contract:

```typescript
interface SessionSpawnIntent {
  sessionId: string;
  argv: string[];
  cwd?: string;
  env?: Record<string, string>;
}

interface RuntimeSpawnRequest {
  sessionId: string;
  argv: string[];
  cwd?: string;
  env?: Record<string, string>;
}

interface RuntimeKillRequest {
  sessionId: string;
  signal: "term" | "kill" | string;
  graceSecs: number;
}
```

Behavioral contract:

- Session spawn persists intent before runtime launch.
- Runtime launch is invoked through `RuntimeService`.
- Failed session spawn rolls back runtime work through `RuntimeRpc::Kill`.
- `RtmdDriver` is concrete and limited to sanctioned non spawn sites.
- `SessionDriver` and `SpawnDriver` traits no longer exist.

## Database Changes

Session spawn intent persistence is part of the W3 work. The behavioral commit uses `BEGIN IMMEDIATE` transactions around spawn intent creation, runtime launch reconciliation, and abort handling.

No new migration file was added in this follow on cleanup commit.

## Security Considerations

- Removed legacy driver abstractions that could bypass the runtime service boundary.
- Rollback termination now uses the runtime RPC path with a local principal.
- Spawn remains identity gated through the runtime service boundary.
- Directive greps for legacy spawn routes are clean.

## Performance Notes

- Removed trait indirection from the daemon driver path.
- Kept runtime service ownership explicit through `Arc<RuntimeService>`.
- File size limits were verified with `scripts/check-loc-limit.sh`.

## Verification

Passed:

- `cargo check -p lilo-session-driver -p lilo-session-daemon`
- `cargo test -p lilo-session-driver -p lilo-session-daemon`
- `git diff --check`
- `git grep -nE 'SessionDriver|trait SpawnDriver|dyn .*Driver' internal/ crates/`
- `git grep -nE 'LegacySpawnInput|spawn_via_driver|SpawnDriver' internal/session/daemon/src/ crates/`
- `git grep -nE 'Legacy' internal/ crates/`
- `bash scripts/check-loc-limit.sh`
- `just check && just build && just test`
- `fmm generate && fmm validate`
- `cargo nextest run -p lilo-runtime-app --test integration_events_cursor timed_out_long_poll_releases_waiter`
- `moon ci`

The first `moon ci` run hit the known intermittent `timed_out_long_poll_releases_waiter`. The targeted rerun passed, and a second `moon ci` passed with 555 tests.

## Open Items

- Orchestrator owns final Linear transition for ALP-2859 after push confirmation.
- W3 to W4 handoff remains orchestrator owned.
