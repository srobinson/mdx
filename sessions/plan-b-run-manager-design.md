---
title: Plan B RunManager Design
type: sessions
tags: [backend, transport-matters, run-manager, captured-canvas]
summary: Filed and amended the server managed RunManager design for captured agent panes.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Created and amended `NOTES/captured-canvas/plan-b-design.md` for the captured canvas Plan B design. The design moves captured run ownership from pane owned WebSockets to a backend `RunManager` that owns `CapturedRunLease`, PTY lifecycle, scrollback, and attachments.

Round 1 peer consensus amendments were applied on 2026-06-09:

- Every teardown path cancels the drain task and removes the event loop reader before closing the PTY master fd.
- `RunManager.spawn()` rolls back with PTY termination and `CapturedRunLease.close()` after any post prepare failure.
- Captured run cli validation, cwd resolution, and launch preflight move to a public package root seam shared by the manager and the retiring route.
- `POST /api/runs` and `DELETE /api/runs/{runId}` require an HTTP request shaped origin and loopback gate before spawn.
- Replay to live ordering uses an await free synchronous critical section.
- `cwd` must be absolute, exist, and be a directory. B1 does not add an allowed roots policy.
- The B1b to B3 old UI orphan risk is documented with mitigation.
- B1 is split into B1a PTY primitive extraction and B1b RunManager plus registry.

## API Contract

Planned endpoints:

```ts
POST /api/runs
GET /api/runs
WS /api/runs/{runId}/terminal
DELETE /api/runs/{runId}
```

Core types:

```ts
type CapturedRunCli = "claude" | "codex";
type RunState = "starting" | "running" | "stopping" | "exited" | "failed";

interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}
```

## Database Changes

None for B1 through B4. The active correlated store remains Postgres. The run registry is in memory until B5.

## Security Considerations

The design carries over the existing loopback and origin gate before WebSocket accept, adds an HTTP request shaped loopback and origin gate to state changing REST endpoints, keeps `cli` allowlisted to `claude` and `codex`, requires `cwd` to be an absolute existing directory, and avoids exposing launch env or terminal bytes in logs.

## Performance Notes

The manager runs a continuous PTY drain loop independent of attached viewers. It appends PTY bytes to bounded scrollback and fans out through bounded per attachment queues without blocking the PTY drain on WebSocket sends. Teardown removes the loop reader before closing the fd to avoid stale reader callbacks on reused descriptors.

## Open Items

- B5 backend restart recovery.
- B6 cross process curation delivery for nested runs.
- Backend persisted director layout store.
- Final config names for scrollback bytes, max live runs, and idle timeout.
