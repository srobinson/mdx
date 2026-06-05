---
title: Transcript Canvas Timeline Endpoint
type: sessions
tags: [backend, api, session-store, transcript-canvas]
summary: Implemented slice 1 of the transcript canvas backend timeline endpoint over existing session rows.
status: active
source: backend-engineer
confidence: high
created: 2026-06-08
updated: 2026-06-08
---

## Summary

Implemented PR #50 on branch `feat/transcript-canvas-slice-1` at commit `e973560`.

Key decisions:

1. Added `GET /api/sessions/{session_id}/timeline` as a thin FastAPI route.
2. Kept projection logic in shared module `transport_matters.session.timeline` for reuse by live catchup.
3. Split Pydantic API contract models into `transport_matters.session.timeline_models` to keep files under size limits.
4. Stayed on existing Postgres rows. No new tables, columns, or migrations.

## API Contract

Endpoint:

```text
GET /api/sessions/{session_id}/timeline
```

Query parameters:

```text
owner=local
from_seq=<integer>
to_seq=<integer>
limit=<integer>
include_resources=true
include_debug=false
```

Response model:

```python
TimelineResponse(
    session=SessionHeader,
    items=list[TimelineItem],
    resources=dict[str, ResourceSummary],
    subagents=dict[str, SubagentSummary],
    layout_hints=list[LayoutHint],
    next_from_seq=int | None,
)
```

The response serializes with camelCase aliases, including `layoutHints`, `nextFromSeq`, `resourceRefs`, `subagentRefs`, `rawAvailable`, and `irAvailable`.

Implemented timeline item unions:

1. `MessageItem`
2. `StateItem`
3. `SubagentItem`
4. `ContextItem`
5. `DiagnosticItem`

Implemented resource summary unions:

1. `FileResourceSummary`
2. `InlineResourceSummary`
3. `ToolOutputResourceSummary`
4. `WireResourceSummary`
5. `NativeRecordResourceSummary`

## Database Changes

No schema changes.

DAO additions:

1. `get_events_with_raw_for_owner`, a new owner scoped read that includes `event.raw` for meta classification.
2. `list_child_sessions_for_owner`, a child session read with first and last event sequence bounds.
3. `ChildSessionRow`, extending `SessionRow` with `first_seq` and `last_seq`.

The existing `get_events_for_owner` still strips raw payloads.

## Security Considerations

1. Timeline reads remain owner scoped through a session owner check and owner scoped event queries.
2. Raw JSON is used server side for classification but is not emitted by default.
3. The endpoint returns provenance flags and source references, not raw provider bytes.
4. The route reuses the existing session store dependency and 404 behavior for cross owner access.

## Performance Notes

1. The endpoint reads one ordered event page by session id and sequence range.
2. Child session summaries use a single aggregate query over child session events.
3. Projection runs in memory over the returned page only.
4. No persistence cache was added, matching the slice 1 contract.

## Verification

Final gate:

```text
TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://$(whoami):redacted@localhost/postgres just ci
```

Result:

```text
1198 passed
```

Focused coverage added:

1. Turn item projection.
2. Meta projection for all initial rule table rows.
3. Metadata only rows omitted from timeline items.
4. Turn duration badge projection.
5. Child session subagent projection.
6. Virtual sidechain subagent projection.
7. Owner scoped raw DAO read.
8. Timeline endpoint owner scoping, pagination, raw exclusion, and raw based meta classification.

## Open Items

1. Slice 2 should reuse `project_timeline` for live catchup events.
2. Resource content endpoint remains out of scope until slice 6.
3. Wire resources are not emitted unless a real exchange id is known.
4. Virtual sidechain panes still need the later normalization or placeholder viewer decision from the backend spec.
