---
title: Captured Run Spawn Reliability
type: sessions
tags: [backend, captured-run, performance, run-manager, frontend]
summary: Added bounded captured-run spawning, cached preflight, retryable proxy readiness failures, frontend spawn queueing, and latest-failure spawn classification.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented Tier 1 captured-run spawn reliability on branch `perf/spawn-concurrency-reliability` across commits `40854cc` and `8bd8ec5`.

Key decisions:

- `RunManager` bounds keyless and keyed spawn work with an `asyncio.Semaphore` around the prepare plus PTY spawn region.
- Session-store preflight runs off the event loop through `asyncio.to_thread` and caches successful checks for a short TTL.
- Mitmdump readiness timeout retries use fresh allocated ports for unpinned slots, then surface as typed `proxy_start_timeout` instead of generic `launch_failed`.
- Mixed bind and readiness failures now raise the latest terminal retry failure from `prepare_captured_run`, preserving correct `bind_conflict` versus `proxy_start_timeout` semantics.
- `RunManager.spawn` validates CLI and cwd before semaphore admission and session-store preflight, then reuses one validated cwd and upstream for captured request construction.
- The captured-run frontend queues distinct pane spawns behind a module-level cap while preserving per-pane pending spawn dedupe.

## API Contract

Existing endpoint changed error semantics only.

```typescript
// POST /v1/runs
interface CreateRunRequest {
  cli: "claude" | "codex";
  cwd?: string | null;
  terminal?: { cols: number; rows: number } | null;
  oscColorReplies?: boolean;
  continueFromSessionId?: string | null;
  idempotencyKey?: string | null;
  runtimeTemplate?: string | null;
}

interface CreateRunResponse {
  run: RunView;
}

interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}
```

New or tightened outcomes:

- `proxy_start_timeout`, HTTP 503, retryable by the client or operator after launch pressure drops.
- `bind_conflict`, HTTP 409, emitted when the final retryable terminal failure is a port bind conflict.
- `unsupported_cli`, rejected before session-store preflight and spawn admission.
- `invalid_cwd`, rejected before session-store preflight and spawn admission.

Preserved outcomes:

- `session_store_unavailable`, HTTP 503.
- `launch_failed`, HTTP 500 for non-classified launch failures.

## Database Changes

No schema or migration changes.

Runtime pool behavior changed:

- `Settings.session_pool_min_size` now defaults to `0` so captured-run mitmdump processes do not hold an idle Postgres connection per run.
- Verified `psycopg_pool` accepts `min_size=0` with `max_size=10` using local pool construction with `open=False`.

## Security Considerations

- No new public endpoint or authentication surface was added.
- Existing origin and Host protections on `POST /v1/runs` remain unchanged.
- Error responses continue to use machine-readable API error codes without exposing raw logs or credentials.
- Preflight failures are not cached, so transient or real database failures are rechecked on the next spawn attempt.
- Cheap request validation now rejects invalid CLI and cwd values before opening session-store resources or consuming a spawn slot.

## Performance Notes

- Backend spawn concurrency is configurable through `Settings.captured_run_spawn_concurrency`, default `6`.
- Frontend captured-run spawn concurrency is capped at `5` around `createCapturedRun(...)` and queues excess panes.
- Session-store preflight success cache defaults to 3 seconds to collapse bursty `SELECT 1` checks.
- Mitmdump readiness timeout retries mirror the existing 3 attempt bind retry budget, with small jittered backoff and fresh ports for unpinned slots.
- Invalid spawn requests now fail before semaphore admission, keeping valid concurrent spawns from being blocked by bad input.

Verification observed:

- Commit `40854cc`: `just api check`, pass.
- Commit `40854cc`: `just api test`, pass, 1450 tests.
- Commit `40854cc`: `just www check`, pass with pre-existing CSS `!important` warnings.
- Commit `40854cc`: `just www test`, pass, 893 tests.
- Commit `8bd8ec5`: focused mixed failure and validation tests passed, 4 tests.
- Commit `8bd8ec5`: `just api check`, pass.
- Commit `8bd8ec5`: `just api test`, pass, 1454 tests.
- Focused fail-first checks failed before the first implementation round for the new API and frontend tests, then passed after implementation.

## Open Items

- Tier 2 shared mitmdump was intentionally not implemented.
- Per-run mitmdump process and memory cost remain the structural scaling limit.
- A future batch spawn endpoint could reduce round trips and centralize per-pane result reporting.
