---
title: Tier 2 Slice 3 Run Scoped SSE
type: sessions
tags: [backend, sse, transport-matters]
summary: Implemented run scoped SSE broker and stream route for Transport Matters.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented Tier 2 Slice 3 run scoped SSE for Transport Matters on branch `feat/tier2-slice3-run-scoped-sse`, PR #133. Initial implementation landed in commit `875ad95`; blocker follow up landed in commit `80e3069`.

Key decisions:

* Replaced global browser exchange streaming with `GET /v1/runs/{runId}/stream`.
* Removed the legacy `/api/stream` mount.
* Made the in process broadcaster require a nonempty run id on subscribe and emit.
* Stamped every SSE payload with `run_id` and delivered only to subscribers for that run.
* Routed exchange create, delete, pause, paused token, HTTP provisional, and Codex provisional events through the owning run id.
* Updated the browser exchange stream hook to connect to the run scoped SSE route.
* Removed `require_http_origin` from the SSE GET because same origin `EventSource` requests can omit the `Origin` header.

## API Contract

```typescript
// GET /v1/runs/{runId}/stream
interface StreamConnectedEvent {
  type: "connected";
  run_id: string;
}

interface ExchangeEvent {
  type: "exchange";
  id: string;
  run_id: string;
  flow_id?: string;
  mutated_manually: boolean;
  // Existing exchange payload fields are unchanged.
}

interface ExchangeDeletedEvent {
  type: "exchange_deleted";
  id: string;
  run_id: string;
  flow_id?: string;
}

interface PausedEvent {
  type: "paused";
  flow_id: string;
  run_id: string;
  transport: "http" | "websocket";
  provisional_exchange_id?: string | null;
  track_id?: string | null;
  parent_track_id?: string | null;
  track_display_name?: string | null;
  track_role?: "parent" | "subagent" | null;
  spawn_anchor?: unknown;
}

interface PausedTokensEvent {
  type: "paused_tokens";
  flow_id: string;
  run_id: string;
  tokens_before: number;
}
```

Frontend consumption:

```typescript
new EventSource(`/v1/runs/${encodeURIComponent(runId)}/stream`);
```

## Database Changes

No schema or migration changes.

## Security Considerations

* The stream endpoint is a read only same origin SSE GET. It intentionally does not use `require_http_origin` because browser same origin `EventSource` requests can omit `Origin`.
* Mutating run endpoints continue to use the origin guard.
* The broadcaster rejects missing or empty run ids.
* Events are filtered in process by run id before enqueueing to subscriber queues.
* The legacy global stream route is removed to avoid cross run event exposure.

## Performance Notes

* The broker keeps bounded per subscriber queues with the existing max size.
* Fanout iterates subscribers once and skips nonmatching run ids before enqueue.
* No database work is added to the stream path.

## Verification

Initial slice:

* `cd api && just check && just test`: passed, 1468 tests.
* `just www check && just www test`: passed, 893 tests.
* `just www test-e2e`: passed, 42 Playwright tests across Chromium, Firefox, and WebKit.

Blocker follow up:

* Fail first regression: `cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_stream.py::TestSSEGenerator::test_route_accepts_same_origin_eventsource_without_origin_header` failed with `403 == 200` before the fix.
* Focused regression after fix: passed.
* `cd api && just check && just test`: passed, 1469 tests.
* `just www check && just www test`: passed, 893 tests.

## Open Items

None for this slice.
