---
title: Tier 2 Slice 7 Shared Proxy Hardening
type: sessions
tags: [backend, transport-matters, shared-proxy, run-manager]
summary: Hardened shared proxy startup, child transcript snapshots, teardown cleanup, and cross-thread snapshot writer registration for Tier 2 Slice 7.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary

Implemented the Slice 7 review fix rounds on `feat/tier2-slice7-runmanager-integration`. Commit `4d0e93d` made shared proxy subprocess startup failure degrade canvas only, returned a typed unavailable error for external spawns, preserved embedded per-run preparation, registered child subagent cursors for tier 1 transcript snapshots, and hardened lifecycle cleanup. Commit `234c57f` guards `SharedTranscriptSnapshotWriter` maps with a small lock so tailer poll thread child cursor registration cannot race run teardown unregister.

## API Contract

No public request schema changed. Existing `/v1/runs` error handling returns the existing machine-readable `proxy_start_timeout` error with HTTP 503 when the shared proxy is unavailable for external canvas runs.

```typescript
interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

// POST /v1/runs, when web_runtime is external and shared proxy startup failed
// HTTP 503
interface SharedProxyUnavailableError extends ApiError {
  code: "proxy_start_timeout";
  message: string; // "shared proxy unavailable: <reason>"
}
```

## Database Changes

No schema or migration changes. Transcript snapshot writes remain tier 1 filesystem writes under the run storage root. Child and subagent session ids are mapped to the owning run snapshot writer when their tail cursors register, and run teardown removes the owning session plus child cursor sessions atomically under the writer lock.

## Security Considerations

The API no longer turns shared proxy startup failure into whole process unavailability. It fails closed for external canvas spawns with a typed 503 while preserving embedded CLI behavior. Shutdown close calls are individually wrapped and logged so one failing closer does not skip later resource release. Snapshot writer map access is synchronized without holding the lock across snapshot bytes writes or async work.

## Performance Notes

The child cursor registration hook is O(1) and runs only when a new cursor is registered. The snapshot writer lock protects only in-memory map reads and writes, then releases before filesystem snapshot writes. Full API gate passed for the latest race fix: `cd api && just check && just test`, with `1529 passed in 43.87s`.

## Open Items

No known follow-up from this fix round. Future shared proxy road tests should include real canvas runs that spawn Claude Task subagents to validate the unit-level child cursor coverage against live transcript creation.
