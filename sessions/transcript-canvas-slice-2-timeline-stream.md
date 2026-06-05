---
title: Transcript Canvas Slice 2 Timeline Stream
type: sessions
tags: [backend, transport-matters, transcript-canvas, timeline-stream]
summary: Implemented the shared projector backed timeline SSE stream for transcript canvas slice 2.
status: active
source: backend-engineer
confidence: high
created: 2026-06-08
updated: 2026-06-08
---

## Summary

Implemented slice 2 on `feat/transcript-canvas-slice-2` in PR #51. The backend now exposes a live timeline SSE stream that packages slice 1 timeline projections without forking projection logic. The raw event SSE stream and the new timeline SSE stream share one subscription, keepalive, catchup, and race dedupe loop.

## API Contract

```typescript
type TimelineStreamEvent =
  | { kind: "timeline-item"; item: TimelineItem; resources: Record<string, ResourceSummary> }
  | { kind: "subagent-updated"; subagent: SubagentSummary }
  | { kind: "resource-updated"; resource: ResourceSummary }
  | { kind: "session-updated"; session: SessionHeader };

interface TimelineStreamEnvelope {
  id: string;
  revision: number;
  emittedAt: string;
  event: TimelineStreamEvent;
}
```

Endpoint: `GET /api/sessions/{session_id}/timeline/stream?owner=local&last_seq=-1` returning `text/event-stream`. Stable ids use `timeline:<session_id>:<seq>`, `resource:<session_id>:<resource_id>`, `subagent:<parent_session_id>:<subagent_id>`, and `session:<session_id>`.

## Database Changes

No schema changes and no new tables. The stream reads existing owner scoped `session`, `event`, and child session rows through `AsyncSessionDao`.

## Security Considerations

The route checks session ownership before returning the stream and every catchup load uses owner scoped DAO calls. Raw event bytes remain excluded from the stream payload. The endpoint reuses the existing FastAPI dependency path for the session pool and event hub.

## Performance Notes

The stream reuses the existing `SessionEventHub` and `STREAM_FETCH_LIMIT` batch catchup flow. Timeline live batches call the same `project_timeline` projector used by backlog reads, then serialize envelopes. The full API gate passed with `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres just ci`, including Ruff format check, Ruff lint, mypy, and 1208 pytest cases.

## Open Items

Resource content endpoints, frontend consumption, projection persistence, and deeper resource extraction remain out of scope for this slice.
