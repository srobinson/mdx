---
title: Transport Matters session store read API and SSE
type: sessions
tags: [backend, transport-matters, session-store, postgres, sse]
summary: Implemented owner scoped session reads, live append SSE, and review fixes for the Postgres session store.
status: active
source: backend-engineer
confidence: high
created: 2026-06-06
updated: 2026-06-06
---

## Summary

Implemented Slice 3 on branch `feat/session-3-read-sse` and opened PR #36.

Commits:

- `58da786`: initial read API and live event stream implementation.
- `a0fcc91`: review fixes folded into the same PR.

Key decisions:

- Session read routes live under `/api/sessions` and delegate SQL to `session.dao`.
- The SSE route subscribes before backlog, loads rows from Postgres, and dedups by monotonic `seq`.
- The existing writer notify payload on `tm_events` is compact. It carries session and seq range metadata only, so the writer was not changed.
- The LISTEN consumer owns one dedicated async connection outside the pool, reconnects on connection drop, and closes cleanly in FastAPI shutdown.
- Session event reads now use a lightweight projection that excludes `raw` and `content_tsv` from the hot path.
- Each successful LISTEN connection publishes a synthetic catch-up signal for active subscribers, so events committed during a reconnect gap are loaded without waiting for a later commit.
- The app can still boot without session database configuration or after listener startup failure. Session endpoints return service unavailable when the pool is missing.

Bus replies sent:

- `done: feat/session-3-read-sse 58da786 PR#36`
- `fixes done: a0fcc91`

Verification completed:

- `git diff --check`
- `fmm validate`, with all 482 files indexed and current
- Runtime import DAG check, with only the pre-existing `override_state.py` and `overrides.py` cycle
- Focused review regression tests, with 5 tests passing
- `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres just ci`, with 1252 tests passing
- LOC check, with touched files under 700 lines
- No em dashes in touched files

## API Contract

```typescript
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
  source_descriptor: Record<string, unknown> | null;
  home_dir: string | null;
  owner: string;
  status: string;
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
  kind: string;
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
  ir: Record<string, unknown> | null;
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

Endpoints:

- `GET /api/sessions`
  - Query: `owner`, `workspace_hash`, `provider`, `cli`, `status`, `limit`, `offset`
  - Response: `SessionSummary[]`
- `GET /api/sessions/{session_id}/events`
  - Query: `owner`, `from_seq`, `to_seq`, `limit`
  - Response: `SessionEventListResponse`
- `GET /api/sessions/{session_id}/events/stream`
  - Query: `owner`, `last_seq`
  - Response: `text/event-stream` frames containing `SessionEventView` JSON
  - Heartbeat: `: keepalive` comment frames

Consistent error behavior:

- Missing session store runtime state returns HTTP 503.
- Wrong owner or unknown session returns HTTP 404.
- Raw CLI record JSON is excluded from read API and stream payloads.

## Database Changes

No migration was required.

The implementation reads existing Postgres tables from Slice 1 and Slice 2:

- `session`
- `event`

DAO methods added:

- `SessionDAO.list_sessions`
- `SessionDAO.get_session_for_owner`
- `SessionDAO.get_events_for_owner`
- Async equivalents for the route layer

Read surface projection:

- Full event APIs that need raw still use `EventRow`.
- Owner scoped read APIs return `EventReadRow`, which omits `raw`.
- `_GET_EVENTS_FOR_OWNER_SQL` explicitly selects only read view columns and never selects `content_tsv`.

The writer notify payload remains unchanged and compact:

```json
{
  "type": "session_events",
  "session_id": "...",
  "run_id": "...",
  "count": 1,
  "first_seq": 0,
  "last_seq": 0
}
```

## Security Considerations

- Routes enforce owner scoping before returning session or event rows.
- The event stream validates owner access before creating the response.
- Notify payloads are not trusted as render data. They only prompt a scoped Postgres fetch.
- Raw event JSON remains in Postgres and is not exposed by list, event, or stream payloads.
- Session database unavailability is reported as HTTP 503 rather than leaking connection details.
- Listener startup failures clear app state, so routes do not expose closed pool errors.

## Performance Notes

- Session events are paginated by `seq` and fetched in bounded batches.
- SSE backlog and live catch-up share the same row loader to avoid duplicate query paths.
- The hot read path excludes raw record JSON and `content_tsv` to reduce database transfer and JSON validation cost.
- Live notifications fan out in process by `session_id` through bounded queues.
- A full subscriber queue drops the current signal, logs a warning, and accepts later range signals after the queue drains.
- The Postgres LISTEN connection is dedicated and not borrowed from the request pool.
- The listener reconnects after dropped connections, publishes catch-up signals after connection, and releases the connection on shutdown.

## Open Items

- Auth is still represented by explicit `owner` scoping. A future auth slice should bind owner from authenticated identity.
- Old `index/*` routes remain in place for later retirement slices.
- Cross process SSE fanout depends on every API process owning its own LISTEN consumer.
