---
title: Transcript Canvas Slice 6 Resource Refs
type: sessions
tags: [backend, transport-matters, transcript-canvas, resource-refs, session-store]
summary: Implemented and refined conservative timeline resource refs for inline artifacts, native records, and known wire exchanges.
status: active
source: backend-engineer
confidence: high
created: 2026-06-08
updated: 2026-06-08
---

## Summary

Implemented slice 6 for the transcript canvas backend.

Landed work:

* PR #55, branch `feat/transcript-canvas-slice-6`, commit `8f4feba`, merged to main as `0474c2a`.
* PR #56, branch `feat/transcript-canvas-slice-6-followup`, commit `987f9cf`, addressed three review minors.

Key decisions:

* Timeline resource projection stays conservative. It emits refs only for native records, inline artifacts, and known wire exchange ids.
* Native transcript rows now use relation `native-record`, matching the updated spec enum.
* Wire refs are emitted only from Transport Matters owned correlation in `row.ir`; provider raw JSON is not scanned for generic `turn.exchange_id` or `correlation.exchange_id` keys.
* Inline artifact dedup keys by artifact hash, so mismatched stored and displayed block indexes cannot double emit one artifact.
* Tool output refs remain out of projection for this slice. The resource content endpoint slice owns tool output resources.
* Resource projection lives in `api/src/transport_matters/session/timeline_resources.py`, keeping `timeline.py` below the 700 line threshold.
* Existing raw event reads enrich `EventRow.artifacts` from `event_artifact` joined to `artifact`, so inline summaries can use stored media type and size without touching wire capture code.

## API Contract

Existing endpoint:

```typescript
// GET /api/sessions/{session_id}/timeline

type ResourceRelation =
  | "attached"
  | "read"
  | "written"
  | "mentioned"
  | "generated"
  | "wire-evidence"
  | "native-record";

type ResourceConfidence = "verified" | "inferred" | "mentioned";

interface ResourceRef {
  resourceId: string;
  relation: ResourceRelation;
  confidence: ResourceConfidence;
  blockIndex: number | null;
}
```

Emitted refs:

* `native:<session_id>:<seq>` on message and context items, relation `native-record`, confidence `verified`, `blockIndex: null`.
* `inline:<artifact_hash>` on message items with inline image artifacts, relation `attached`, confidence `verified`, block scoped when known.
* `wire:<exchange_id>` on message and context items only when an exchange id is already present in the event IR, relation `wire-evidence`, confidence `verified`, `blockIndex: null`.

Explicitly not emitted in this slice:

* Verified refs for mentioned paths.
* File current or file captured refs.
* Tool output refs.
* Wire refs from provider raw JSON alone.
* Wire refs without a real Transport Matters owned exchange id.

## Database Changes

No schema migration.

Read path change:

* `SessionDao.get_events_with_raw_for_owner` and `AsyncSessionDao.get_events_with_raw_for_owner` load artifact metadata for returned seqs with a second parameterized query.
* `EventRow` has an in memory `artifacts: tuple[EventArtifactRow, ...]` field.
* `EventArtifactRow` carries optional `media_type` and `size_bytes` when read through the joined artifact metadata query.

## Security Considerations

* No live request or response wire path changes.
* No raw bytes endpoint was added.
* Wire resources require an existing non empty exchange id from the IR. Provider raw keys are ignored for wire refs.
* Mentioned file paths remain text only and do not become verified refs.
* SQL uses parameterized psycopg queries, including the seq array lookup.

## Performance Notes

* Timeline raw event reads add one bounded artifact metadata query per page of events.
* The artifact metadata query is scoped by `session_id` and page seqs, using the `event_artifact` primary key and `artifact` primary key join.
* `timeline.py` remained below the hard 700 line threshold by extracting resource projection to `timeline_resources.py`.
* Followup line counts remained below the hard file threshold: `timeline_resources.py` 276 lines, `test_timeline.py` 529 lines, `timeline_models.py` 299 lines.

## Verification

Fail first checks observed:

* Before implementation, `api/.venv/bin/python -m pytest api/src/transport_matters/session/test_timeline.py -q` failed for native relation, provider raw wire conservatism, and inline artifact dedup.

Passing checks observed:

* `api/.venv/bin/python -m pytest api/src/transport_matters/session/test_timeline.py -q`: 32 passed.
* `cd api && just test src/transport_matters/session/test_timeline.py src/transport_matters/session/test_foundation.py src/transport_matters/api/v1/test_session_routes.py -q`: 55 passed.
* `cd api && just ci`: ruff format check, ruff check, mypy, and 1220 pytest tests passed.

## Open Items

* Resource content endpoint remains a later slice.
* Real resource viewers remain a later slice.
* Tool output refs should return only when the content endpoint can serve them.
* File current and file captured refs need verified provenance before projection.
