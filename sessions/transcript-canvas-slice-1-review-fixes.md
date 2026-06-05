---
title: Transcript Canvas Slice 1 Review Fixes
type: sessions
tags: [backend, transport-matters, transcript-canvas]
summary: Addressed PR 50 transcript canvas backend review findings and pushed the updated branch.
status: active
source: backend-engineer
confidence: high
created: 2026-06-08
updated: 2026-06-08
---

## Summary

Implemented targeted PR 50 review fixes for transcript canvas slice 1 on `feat/transcript-canvas-slice-1`.

Key decisions:

- Kept frozen timeline models immutable by replacing `MessageItem` instances with `model_copy(update=...)` when adding badges or subagent references.
- Linked child subagents anchored on meta or gap sequences to the nearest preceding visible message.
- Used the requested page lower bound for child subagent visibility so fork anchors without event rows are still emitted on the correct page.
- Grouped sidechain meta rows into virtual sidechain subagents instead of projecting them as top level meta items.
- Removed slice 5 native record resource emission from slice 1 debug output.
- Shared the owner scoped event SQL body between raw and raw stripped reads.

Commit pushed: `60220a8f10c1b956cb32055c10b4a72c94cf2c93`.

## API Contract

Existing endpoint retained:

```typescript
// GET /api/sessions/{sessionId}/timeline
interface TimelineQuery {
  owner?: string;
  fromSeq?: number;
  toSeq?: number;
  limit?: number;
  includeResources?: boolean;
  includeDebug?: boolean;
}
```

Behavioral contract preserved:

- Owner scoped timeline reads still 404 for sessions outside the requested owner.
- Timeline pagination still uses `nextFromSeq`.
- Timeline responses still omit raw event payloads.
- `includeDebug=true` no longer emits native record resource summaries in slice 1.

## Database Changes

No schema or migration changes.

SQL changes:

- Replaced duplicate owner scoped event query bodies with `_get_events_for_owner_sql(event_columns)`.
- Raw stripped and raw preserving reads now share the same join, filter, order, and limit clauses.

## Security Considerations

- Owner scoping remains enforced through `AsyncSessionDao.get_events_with_raw_for_owner` and `_require_session`.
- No raw transcript bytes are added to the timeline response.
- No new write path, auth path, or public resource content route was introduced.

## Performance Notes

- Query shape is unchanged, so existing `(session_id, seq)` pagination behavior remains intact.
- Subagent visibility uses in memory page range checks over already fetched rows.
- Message replacement tracks item indices by sequence to avoid repeated scans during badge and subagent attachment.

Verification run:

- `cd api && just ci`
- Result: `1203 passed`, ruff format check clean, ruff lint clean, mypy clean.

## Open Items

- Resource summaries and native record resource references remain deferred to slice 5.
- Future route level tests may cover page lower bound gap behavior against a real session store fixture if reviewers want endpoint level proof beyond the projector unit coverage.
