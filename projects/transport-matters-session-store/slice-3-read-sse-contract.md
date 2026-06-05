---
title: Slice 3 Read Surface and SSE Contract
type: design
status: active
created: 2026-06-06
updated: 2026-06-06
---

# Slice 3 Read Surface and SSE Contract

## Scope

FastAPI read endpoints over the Postgres session store. Owner scoping applies to every read. Raw transcript records stay out of list payloads and stream payloads.

## Entity Types

```typescript
type SessionStatus = "active" | "completed" | "archived";
type EventKind = "turn" | "meta";

type JsonObject = Record<string, unknown>;

interface SessionSummary {
  session_id: string;
  provider: string;
  cli: string | null;
  run_id: string;
  cwd: string;
  workspace_slug: string;
  workspace_hash: string;
  native_session_id: string | null;
  minted: boolean;
  source_descriptor: JsonObject | null;
  home_dir: string | null;
  owner: string;
  status: SessionStatus;
  title: string | null;
  parent_session_id: string | null;
  forked_at_seq: number | null;
  started_at: string;
  created_at: string | null;
  updated_at: string | null;
}

interface SessionEventView {
  session_id: string;
  seq: number;
  kind: EventKind;
  native_turn_id: string | null;
  parent_native_id: string | null;
  parent_seq: number | null;
  run_id: string;
  provider: string;
  cli: string;
  role: string | null;
  is_sidechain: boolean;
  ts: string | null;
  model: string | null;
  ir: JsonObject | null;
  source_path: string | null;
  source_line: number | null;
  search_text: string | null;
  created_at: string | null;
}

interface SessionEventListResponse {
  events: SessionEventView[];
  next_from_seq: number | null;
}
```

## Endpoints

### GET /api/sessions

Query:

```typescript
interface ListSessionsQuery {
  owner?: string;          // default "local"
  workspace_hash?: string;
  provider?: string;
  cli?: string;
  status?: SessionStatus;
  limit?: number;          // default 50, min 1, max 500
  offset?: number;         // default 0, min 0
}
```

Response: `SessionSummary[]`, sorted by `started_at` descending.

### GET /api/sessions/{session_id}/events

Query:

```typescript
interface ListSessionEventsQuery {
  owner?: string;          // default "local"
  from_seq?: number;       // inclusive, default null
  to_seq?: number;         // inclusive, default null
  limit?: number;          // default 500, min 1, max 1000
}
```

Response: `SessionEventListResponse`, ordered by `seq` ascending. The payload includes normalized `ir` for rendering. It never includes `raw`.

Authorization behavior: if no session with matching `(owner, session_id)` exists, return 404. Do not reveal whether the session exists for another owner.

### GET /api/sessions/{session_id}/events/stream

Query:

```typescript
interface StreamSessionEventsQuery {
  owner?: string;          // default "local"
  last_seq?: number;       // client has already processed this seq, default -1
}
```

Protocol: `text/event-stream`.

Connect order:

1. Validate `(owner, session_id)`.
2. Subscribe in-process before backlog query.
3. Query backlog with `from_seq = last_seq + 1`.
4. Emit backlog events.
5. Emit live events from the subscriber.
6. Deduplicate by `seq`, so notifications racing with backlog cannot duplicate or drop events.

SSE event frame:

```typescript
interface SessionEventSsePayload extends SessionEventView {}
```

Keepalive: comment frames are sent periodically as `: keepalive`.

## NOTIFY Contract Consumed

Channel: `tm_events`.

Existing writer payload shape:

```typescript
interface SessionEventsNotifyPayload {
  type: "session_events";
  session_id: string;
  run_id: string;
  count: number;
  first_seq: number | null;
  last_seq: number | null;
}
```

This is a small id and range handle. It carries no raw transcript data and no IR. SSE loads rows from Postgres by `(session_id, seq)` and does not trust the payload as the source of render data.

## Error Format

Existing FastAPI routes use `HTTPException` with `detail`. This slice follows that convention:

```typescript
interface ApiError {
  detail: string;
}
```
