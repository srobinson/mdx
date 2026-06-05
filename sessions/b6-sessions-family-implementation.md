---
title: B6 Sessions Family Implementation
type: sessions
tags: [backend, b6, sessions, api]
summary: Implemented the B6 public sessions API family on `/v1/sessions` with curated session and transcript projections.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented B6 step 3 for the sessions family in PR #124. Session read routes now live under `/v1/sessions`, the legacy `/api/sessions` mount is removed, and the session canvas frontend consumes the curated v1 shapes. A contract note was written at `/Users/alphab/.mdx/design/transport-matters-b6-sessions-family-api.md` before endpoint implementation.

## API Contract

`GET /v1/sessions`

Returns cursor paginated sessions:

```ts
interface ListSessionsResponse {
  items: Session[];
  nextCursor: string | null;
}
```

Supported filters are `owner`, `workspaceId`, `purpose`, `visibility`, `includeInternal`, `limit`, and `cursor`. Cursors lock the filter set.

`GET /v1/sessions/{sessionId}`

Returns one owner scoped public session.

```ts
interface Session {
  sessionId: string;
  workspaceId: string;
  title: string | null;
  status: string;
  provider: string;
  cli: string;
  createdAt: string;
  lastActivityAt: string;
  purpose: "user" | "continuation" | "internal_summary" | "internal_indexing" | "internal_eval" | "system_maintenance";
  visibility: "user_visible" | "hidden" | "diagnostic";
  lineage: {
    parentSessionId: string | null;
    forkedAtSeq: number | null;
    forkedAtTurn: number | null;
  };
  turnCount: number;
  inheritedTurnCount: number;
  lastMessagePreview: string | null;
}
```

`GET /v1/sessions/{sessionId}/events`

Returns curated transcript events:

```ts
interface SessionEventListResponse {
  events: TranscriptEvent[];
  nextFromSeq: number | null;
}

interface TranscriptEvent {
  seq: number;
  turnIndex: number | null;
  kind: string;
  role: string | null;
  ts: string | null;
  body: TranscriptEventBody;
  resourceRefs: TranscriptResourceRef[];
}
```

`GET /v1/sessions/{sessionId}/events/stream`

Streams the same curated `TranscriptEvent` shape over SSE.

Existing timeline, timeline stream, and resource routes remain under the v1 session router and now include `turnIndex` where applicable.

## Database Changes

No migration was required. Existing session classification columns are reused.

New read projections were added in DAO statements and async DAO methods:

- Session list and detail projections aggregate last activity, turn count, inherited turn count, and last message preview.
- The list query applies owner scope, filter defaults, and cursor locked filters in one query.
- A shared turn index helper computes public turn indices for events and timeline items.

## Security Considerations

- Session reads remain owner scoped.
- Public session models hide native session ids, minted state, source descriptors, home directories, raw payloads, and debug fields.
- Transcript events expose curated bodies only.
- Legacy `/api/sessions` is covered by a 404 regression test.
- Public errors continue to use machine readable `code` plus `message` envelopes for session store failures and missing sessions.

## Performance Notes

- The session list projection avoids per session follow up queries by aggregating activity, counts, and previews in SQL.
- Cursor pagination fetches `limit + 1` rows to compute `nextCursor` without a count query.
- Turn index projection is computed once per event page or timeline page.

Verified gates:

- `cd api && just check`
- `just check`
- `just test`
- `just www test-e2e`
- `just www build`

## Review Delta 2026-06-16

Addressed the PR #124 frontend blocker in commit `22a8e3e`. Wire injected turns now map to a dedicated `wire_context` transcript message kind, preserve the event label as `wireLabel`, and render with explicit `data-kind="wire_context"` plus `data-role="wire"` hooks. Transcript chat now displays the wire label in the message header and uses a distinct amber wire context treatment.

Cleanup completed in the same delta:

- Removed hardcoded null `sourcePath` and `sourceLine` fields from `TranscriptMessageModel`.
- Removed the dead `session.cli ?? session.provider` title fallback in `titleForSession`.
- Added mapper and render coverage for wire injected turns, `tool_use`, and `tool_result` transcript bodies.

Fail first proof was captured before the fix with the focused frontend tests, showing the wire injected turn flattened as a normal system message and missing the `data-kind` affordance.

Review delta gates:

- `cd www && pnpm test src/session-canvas/stream/mapIrToChat.test.ts src/session-canvas/viewers/transcript-chat/TranscriptChatPane.test.tsx`
- `just check`
- `just www test`
- `just test`
- `just www test-e2e`

## Open Items

- Timeline search remains deferred by the B6 scope.
- Exact run to session launch resolution now uses the curated session workspace and CLI fields. A future run lookup can restore exact run id matching if the run contract needs it.
