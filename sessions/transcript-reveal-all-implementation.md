---
title: Transcript Reveal All Implementation
type: sessions
tags: [backend, transcript, session-store, frontend]
summary: Exposed persisted transcript native payloads through v1 session events and transcript chat.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented S1 transcript reveal all in PR #125. The v1 session event read surface now publishes persisted transcript `raw` JSON as `nativePayload`, and transcript chat uses that payload to show records that previously rendered as empty metadata cards.

Key decisions:

- Kept ingest, adapters, writes, ACL checks, and `_event_body` unchanged.
- Reused the existing `event.raw` JSONB column. No migration was needed.
- Preserved the public omission of internal row fields such as `raw`, `nativeTurnId`, and `searchText`; only the intentional content field `nativePayload` is exposed.
- Added a per card `view raw` disclosure so every transcript card can reveal its native payload.

## API Contract

```typescript
interface TranscriptEventView {
  seq: number;
  turnIndex: number | null;
  kind: string;
  role: string | null;
  ts: string | null;
  body: TranscriptEventBody;
  nativePayload: Record<string, unknown> | null;
  resourceRefs: TranscriptResourceRef[];
}

interface SessionEventListResponse {
  events: TranscriptEventView[];
  nextFromSeq: number | null;
}
```

Affected endpoints:

- `GET /v1/sessions/{session_id}/events`
- `GET /v1/sessions/{session_id}/events/stream`

Both list and SSE paths now include `nativePayload` on each event.

## Database Changes

No schema changes.

Implementation details:

- `EVENT_READ_COLUMN_NAMES` now includes `raw`.
- `EventReadRow` carries `raw: JsonObject | None`.
- Existing `event_read_row` validation threads the selected JSON through unchanged after nested NUL cleanup.

## Security Considerations

- Owner scoping remains enforced by the existing session join and owner filter.
- The raw database field name is not exposed on the API response.
- This intentionally reveals transcript native content, including hook, attachment, and session metadata payloads, per the product requirement that transcript visibility should be complete.
- No new input surface or mutation path was added.

## Performance Notes

- Query shape is unchanged except selecting the already persisted JSONB `raw` column.
- No additional round trips were introduced.
- Rendering uses existing transcript event state and maps the native payload to pretty JSON only when building chat item blocks or opening the per card disclosure.

Validation completed:

- Fail first API tests showed `EventReadRow` lacked `raw` and v1 events lacked `nativePayload`.
- Fail first frontend tests showed meta and empty wire injected cards still rendered metadata only and lacked `view raw`.
- `TRANSPORT_MATTERS_TEST_DATABASE_URL="postgresql://$(whoami):transport-matters-test@localhost/postgres" just check`
- `TRANSPORT_MATTERS_TEST_DATABASE_URL="postgresql://$(whoami):transport-matters-test@localhost/postgres" just test`
- `just www test`
- `just www test-e2e`
- `just www build`

## Open Items

- S2 denylist or JSON path filtering remains out of scope.
- PR #125 is draft and awaiting split review from the backend code reviewer and frontend engineer.
