---
title: Reveal All Cleanup Implementation
type: sessions
tags: [backend, transcript, session-store, frontend]
summary: Collapsed duplicate owner event SQL and hid raw transcript details when native payloads are null.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented the reveal all cleanup follow up in an isolated worktree on `feat/reveal-all-cleanup`, based on `origin/main` at `146b70b`. Opened draft PR #126: https://github.com/littleorgans/transport-matters/pull/126.

Backend cleanup collapsed duplicate owner event SQL into one shared `GET_EVENTS_FOR_OWNER_SQL` constant. The synchronous and asynchronous DAO methods remain distinct: `get_events_for_owner` still returns `EventReadRow` without artifact enrichment, while `get_events_with_raw_for_owner` still returns `EventRow` and enriches artifacts with the second artifact query.

Frontend cleanup guards raw transcript details behind `message.nativePayload !== null`. Cards with non null native payloads still show `view raw`; null payload cards render their readable metadata fallback without a literal `null` raw panel.

## API Contract

No endpoint shape changed.

Relevant existing transcript event payload field:

```typescript
interface SessionEventView {
  nativePayload: unknown | null;
}
```

UI behavior contract:

```typescript
interface TranscriptMessageModel {
  nativePayload: unknown | null;
}

// If nativePayload is non null, show per card raw JSON details.
// If nativePayload is null, hide raw details and render the existing mapped content blocks.
```

## Database Changes

No schema or migration changes.

SQL cleanup:

```python
GET_EVENTS_FOR_OWNER_SQL = f"""
SELECT {EVENT_OWNER_COLUMNS}
FROM "event" AS e
JOIN "session" AS s ON s.session_id = e.session_id
WHERE e.session_id = %(session_id)s
  AND s.owner = %(owner)s
  AND (%(from_seq)s::integer IS NULL OR e.seq >= %(from_seq)s::integer)
  AND (%(to_seq)s::integer IS NULL OR e.seq <= %(to_seq)s::integer)
ORDER BY e.seq
LIMIT %(limit)s
"""
```

Removed dead duplication:

- `EVENT_READ_COLUMN_NAMES`
- `EVENT_READ_COLUMNS`
- `events_for_owner_sql`
- `GET_EVENTS_WITH_RAW_FOR_OWNER_SQL`

## Security Considerations

Owner scoping is unchanged. Both DAO paths still use the same parameterized owner scoped query, preserving SQL injection protection and session owner isolation. The raw payload is still sourced from the existing owner scoped event read surface. The frontend change only hides the raw details affordance for null payloads.

## Performance Notes

Database behavior is unchanged for owner event reads. `get_events_with_raw_for_owner` still performs one owner event query and one artifact query when events exist. `get_events_for_owner` still performs only the owner event query. The cleanup reduces duplicate SQL constants without adding query work.

Validation completed:

- Fail first: `pnpm --dir www test src/session-canvas/viewers/transcript-chat/TranscriptChatPane.test.tsx`
- Focused pass: `pnpm --dir www test src/session-canvas/viewers/transcript-chat/TranscriptChatPane.test.tsx`
- `TRANSPORT_MATTERS_TEST_DATABASE_URL="postgresql://$(whoami):transport-matters-test@localhost/postgres" just check`
- `TRANSPORT_MATTERS_TEST_DATABASE_URL="postgresql://$(whoami):transport-matters-test@localhost/postgres" just test`
- `just www test`
- `just www test-e2e`

## Open Items

F2 streamed raw size capping was explicitly out of scope for this cleanup.
