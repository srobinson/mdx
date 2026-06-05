---
title: Transcript Canvas Slice 2 Review Fixes
type: sessions
tags: [backend, transport-matters, transcript-canvas, timeline-stream, api]
summary: Fixed PR 51 live timeline parity findings and pushed the updated slice 2 branch.
status: active
source: backend-engineer
confidence: high
created: 2026-06-08
updated: 2026-06-08
---

## Summary

Implemented the PR 51 slice 2 review fixes at commit `664aace` on branch `feat/transcript-canvas-slice-2`.

Key decisions:

- Preserve the shared projector invariant. Live stream frames still package `project_timeline` output through `project_timeline_stream_envelopes`.
- Anchor split live windows only when the current event window needs prior turn context, currently `system.turn_duration` with no message in the window.
- Re emit the affected prior `timeline:<session_id>:<seq>` envelope with a bumped revision when a later event enriches it.
- Add conservative `tool-output` resource summaries for `tool_result` blocks so the resource subset path is covered by real projector output.
- Keep `session-updated` as a connect snapshot for slice 2. Live session only changes need a session level signal and are deferred with the slice 4 parentless update work.

## API Contract

Existing endpoint remains unchanged:

```typescript
// GET /api/sessions/{sessionId}/timeline/stream?owner=local&lastSeq=-1
// Response: text/event-stream

interface TimelineStreamEnvelope {
  id: string;
  revision: number;
  emittedAt: string;
  event: TimelineStreamEvent;
}

type TimelineStreamEvent =
  | { kind: "timeline-item"; item: TimelineItem; resources: Record<string, ResourceSummary> }
  | { kind: "subagent-updated"; subagent: SubagentSummary }
  | { kind: "resource-updated"; resource: ResourceSummary }
  | { kind: "session-updated"; session: SessionHeader };
```

Stable ids remain:

- `timeline:<session_id>:<seq>`
- `resource:<session_id>:<resource_id>`
- `subagent:<parent_session_id>:<subagent_id>`
- `session:<session_id>`

## Database Changes

No migration.

Added one owner scoped DAO query:

```sql
SELECT e.*
FROM event AS e
JOIN session AS s ON s.session_id = e.session_id
WHERE e.session_id = :session_id
  AND s.owner = :owner
  AND e.kind = 'turn'
  AND e.is_sidechain = false
  AND e.seq < :before_seq
ORDER BY e.seq DESC
LIMIT 1;
```

This query finds the prior message anchor used for live turn duration enrichment.

## Security Considerations

- New DAO access is owner scoped through the session join.
- No raw event bytes are exposed through the stream envelope.
- SSE route still returns 404 for non owners before stream creation.
- All SQL remains parameterized.

## Performance Notes

- Shared `_paginate_seq` removed duplicated pagination loops from raw event and timeline stream loaders.
- The live timeline loader fetches one prior turn only when the current window requires an anchor.
- Query cost is bounded by `(session_id, seq)` ordering and one descending limited lookup.
- File sizes remain below the 700 line threshold.

Verification:

```text
cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres just ci
ruff format --check: 297 files already formatted
ruff check: All checks passed
mypy: Success, no issues found in 297 source files
pytest: 1209 passed in 15.21s
```

## Open Items

- Live `session-updated` after connect remains deferred until the stream has session level signals.
- Subagent or resource changes without a new parent event remain deferred to slice 4 parentless update handling.
- Tool output resources are conservative summaries only. Full resource content endpoints remain future slice work.
