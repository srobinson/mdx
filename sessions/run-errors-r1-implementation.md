---
title: R1 Typed Managed Run Errors and Shutdown Cleanup
type: sessions
tags: [backend, transport-matters, plan-b, run-manager, typed-errors]
summary: Implemented typed managed run errors, idempotent stop, and multi run shutdown cleanup for Plan B R1.
status: active
source: backend-engineer
confidence: high
created: 2026-06-11
updated: 2026-06-11
---

## Summary

Implemented Plan B R1 on branch `feat/run-errors-r1` in commit `aee9c31`, opened as PR #93 against `main`.

Key decisions:

* `RunManagerErrorCode` is now a typed union owned by `run_manager.py`.
* `run_stopped` identifies an explicitly stopped run during attach.
* `run_stale` identifies a run whose PTY terminal is no longer live.
* HTTP mapping is centralized in `_RUN_MANAGER_HTTP_STATUS` and covered by a completeness test.
* WebSocket terminal attach forwards the exact run manager error code in `run.error` frames.
* Explicit stop is idempotent and does not duplicate lease cleanup.
* `RunManager.close()` is tested with multiple running runs.

Verification completed:

* `cd api && just ci`, green, 1309 API tests passed.
* `just test`, green, desktop 28 tests, web 684 tests, API 1309 tests passed.
* `cd www && pnpm lint`, green.
* `cd www && pnpm typecheck`, green.
* `cd www && pnpm test`, green, 684 tests passed.

## API Contract

```typescript
interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

type RunManagerErrorCode =
  | "bind_conflict"
  | "invalid_cwd"
  | "launch_failed"
  | "run_manager_closed"
  | "run_not_attachable"
  | "run_stale"
  | "run_stopped"
  | "session_store_unavailable"
  | "unsupported_cli";

// DELETE /api/runs/{runId}
interface StopRunResponse {
  run: {
    runId: string;
    state: "exited";
    stopReason: "explicit-stop";
  };
}

// WS /api/runs/{runId}/terminal
interface RunErrorFrame {
  type: "run.error";
  code: RunManagerErrorCode | "run_not_found";
  message: string;
}
```

Endpoint behavior:

* `DELETE /api/runs/{runId}` can be repeated for an explicitly stopped run and returns the same exited run view.
* `WS /api/runs/{runId}/terminal` returns `run_stopped` for explicitly stopped runs.
* `WS /api/runs/{runId}/terminal` returns `run_stale` when the run has lost its live PTY terminal.
* `POST /api/runs` after manager shutdown returns `503` with `detail.code = "run_manager_closed"`.
* Every `RunManagerErrorCode` has an HTTP status mapping.

## Database Changes

No database schema changes. No migrations were added.

## Security Considerations

Existing origin validation remains in place for HTTP and WebSocket managed run routes. The change improves client safety by preserving machine readable failure codes instead of collapsing attach failures into `launch_failed`. No new public endpoint or authentication flow was added.

## Performance Notes

No new database queries or long running background work were introduced. The HTTP mapping is an in memory dictionary lookup. Shutdown cleanup remains linear in the number of managed runs, and R1 adds coverage for multiple running runs closing cleanly.

## Open Items

* R1 intentionally does not implement live PTY recovery after a manager restart.
* R1 intentionally does not add idle timeouts or max run limits.
* Native CLI resume remains out of scope for this slice.
