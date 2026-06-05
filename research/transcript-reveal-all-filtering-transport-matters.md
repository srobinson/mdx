---
title: Transcript Reveal All Filtering in Transport Matters
type: research
tags: [transport-matters, transcript, reveal-all, filtering, session-store, ui]
summary: Reveal all should expose native transcript payloads through the API, then apply an empty by default UI denylist for presentation only.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Executive Summary

Owner direction supersedes the prior selective `meta_blocks` idea. Transport Matters should reveal every transcript record by default, expose the persisted native payload through the curated `TranscriptEvent` API shape, and apply progressive subtraction in the UI with an empty by default denylist.

Recommendation: **UI filtering, with an API exposure prerequisite**. The API must stop making persisted raw payloads unreachable, but it should not destructively filter transcript content.

## Project Metadata

- Backend: Python 3.14, FastAPI, Pydantic v2, psycopg, Postgres JSONB.
- Frontend: React 19, TypeScript, Vite, Vitest, pnpm 10.
- Build metadata: `api/pyproject.toml`, `www/package.json`.
- fmm: `.fmm.db` exists at repo root and was used for structural navigation.
- Relevant architecture doc: `PROJECT.md` describes the split between wire artifacts and Postgres transcript events.

## Architecture

### Current pipeline

Transcript records are parsed by provider adapters:

- Claude: `api/src/transport_matters/index/adapters/claude.py:ClaudeAdapter.normalize` lines 111 to 136 only normalizes records whose type is in `_CONVERSATIONAL`.
- Codex: `api/src/transport_matters/index/adapters/codex.py:CodexAdapter.normalize` lines 82 to 110 only normalizes `response_item` records.
- Shared turn IR: `api/src/transport_matters/index/adapters/base.py:NormalizedTurn` lines 137 to 155.

Persistence already keeps the full provider record:

- `api/src/transport_matters/session/ingest.py:build_event` lines 115 to 142 writes turn rows with both `raw=dict(record)` and normalized `ir`.
- `api/src/transport_matters/session/ingest.py:_meta_event` lines 145 to 163 writes non normalized records as `kind=meta`, `raw=dict(record)`, and `ir=None`.
- `api/src/transport_matters/session/models.py:EventRow` lines 100 to 122 includes `raw` and `ir`.
- `api/src/transport_matters/session/dao_statements.py:INSERT_EVENT_SQL` lines 190 to 219 writes both columns.

The reveal gap is the read surface:

- `api/src/transport_matters/session/models.py:EventReadRow` lines 149 to 169 has no `raw` field.
- `api/src/transport_matters/session/dao_statements.py:EVENT_READ_COLUMN_NAMES` line 50 excludes `raw` from normal event reads.
- `api/src/transport_matters/session/async_dao.py:AsyncSessionDao.get_events_for_owner` lines 197 to 217 returns those rawless rows.
- `api/src/transport_matters/api/v1/session_routes.py:list_session_events` lines 200 to 226 calls that rawless DAO path.
- `api/src/transport_matters/api/v1/session_models.py:_event_body` lines 200 to 220 can only use normalized `ir`, `row.kind`, `row.role`, and `row.search_text`; meta rows with `ir=None` become empty `wire_injected` bodies.

The frontend then drops the only useful display chance for meta records:

- `www/src/session-canvas/api/sessionEvents.ts:SessionEventView` lines 21 to 29 has no native payload field.
- `www/src/session-canvas/stream/mapIrToChat.ts:mapSessionEventToTranscriptMessage` lines 21 to 28 routes all `event.kind === "meta"` records to `mapMetaEvent` before looking at `body.kind`.
- `www/src/session-canvas/stream/mapIrToChat.ts:mapMetaEvent` lines 30 to 32 renders only `metadataBlock`.
- `www/src/session-canvas/stream/mapIrToChat.ts:metadataBlock` lines 89 to 99 displays kind, seq, turn index, timestamp, and body kind, not the native record.

## Key Patterns

- **Demote to meta stays valid.** `normalize() -> None` should still create a meta event. The defect is that meta content becomes unreachable in the public event view.
- **Raw plus normalized is already persisted.** No DB migration is needed for reveal all because `EventRow.raw` exists.
- **Filtering is presentation, not data access.** Owner scoped API reads still enforce session ACL. Hiding transcript records should be reversible in the UI.
- **Curated noun compatibility.** `nativePayload` is transcript content inside `TranscriptEvent`, not a control surface implementation field such as a proxy port, runtime home, or RunManager detail.

## Detailed Findings

### A. Recommendation: UI filtering after API exposure

Use UI filtering for progressive subtraction. The API should expose complete transcript payloads by default and continue to enforce owner ACL, pagination, and session scoping.

Reasoning:

1. Reveal all requires the full payload to reach the client. A destructive API filter would make a show hidden toggle impossible.
2. The path list is an operator display preference. Iterating it in the UI avoids turning every curation tweak into a backend projection concern.
3. API response size grows, but that is aligned with the product goal. Transcript content is the product. If bandwidth later matters, add an explicit opt in projection flag while keeping reveal all as the default.
4. B6 curated nouns still hold. The curated noun is `TranscriptEvent`; a `nativePayload` field on that noun carries source transcript content, not API internals.

### B. Prerequisite seam

Make the raw payload reachable through the event API:

1. Add `raw` to `api/src/transport_matters/session/models.py:EventReadRow`, or introduce a public read row that includes raw for transcript event reads.
2. Change `api/src/transport_matters/session/dao_statements.py:EVENT_READ_COLUMN_NAMES` so owner scoped event reads include `raw`, or switch `api/src/transport_matters/api/v1/session_routes.py:list_session_events` to `AsyncSessionDao.get_events_with_raw_for_owner`.
3. Add a public field to `api/src/transport_matters/api/v1/session_models.py:TranscriptEventView`, preferably `native_payload` so the JSON API emits `nativePayload`.
4. Set that field in `api/src/transport_matters/api/v1/session_models.py:transcript_event_view`.
5. Update `www/src/session-canvas/api/sessionEvents.ts:SessionEventView` with `nativePayload: unknown`.
6. Change `www/src/session-canvas/stream/mapIrToChat.ts:mapMetaEvent` to render pretty JSON from `event.nativePayload`.
7. Change `www/src/session-canvas/stream/mapIrToChat.ts:mapWireInjectedEvent` to use `event.nativePayload` as the fallback when body parts are empty.

This keeps `api/src/transport_matters/api/v1/session_models.py:_event_body` demotion logic intact. Normal turns still project to user, assistant, tool use, tool result, or wire injected bodies. Meta records gain an accessible raw payload rather than an invented subtype allowlist.

### C. Filter mechanism

Use a UI side denylist with simple dotted paths rooted at `event.nativePayload`.

Proposed first shape in `www/src/session-canvas/stream/transcriptDenylist.ts`:

```ts
export type TranscriptDenyRule = {
  path: string;
  equals?: string | number | boolean | null;
};

export const transcriptDenylist: TranscriptDenyRule[] = [];

// Owner examples to append later, not active by default:
// { path: "type", equals: "session_meta" }
// { path: "type", equals: "turn_context" }
// { path: "type", equals: "event_msg" }
```

Matching rules:

- Path syntax is dotted object keys, for example `type` or `payload.kind`.
- `[]` is the only array wildcard, for example `message.content[].type`.
- No full JSONPath implementation and no arbitrary predicates.
- If `equals` is present, the rule matches when any resolved value equals it.
- If `equals` is absent, the rule matches when the path exists.
- A match hides the record in the UI by default. It does not remove the event from API payloads or client state.

Default denylist should be empty. The owner can append rules over time after seeing real transcript noise.

### D. Blast Radius

Backend:

- `api/src/transport_matters/session/models.py:EventReadRow`
- `api/src/transport_matters/session/dao_statements.py:EVENT_READ_COLUMN_NAMES`
- `api/src/transport_matters/session/async_dao.py:AsyncSessionDao.get_events_for_owner`
- `api/src/transport_matters/api/v1/session_models.py:TranscriptEventView`
- `api/src/transport_matters/api/v1/session_models.py:transcript_event_view`
- `api/src/transport_matters/api/v1/session_routes.py:list_session_events`
- `api/src/transport_matters/api/v1/session_routes.py:_load_event_frame_batches`

Frontend:

- `www/src/session-canvas/api/sessionEvents.ts:SessionEventView`
- `www/src/session-canvas/stream/mapIrToChat.ts:mapMetaEvent`
- `www/src/session-canvas/stream/mapIrToChat.ts:mapWireInjectedEvent`
- `www/src/session-canvas/viewers/transcript-chat/TranscriptChatPane` if the filter is lifted there for a show hidden toggle
- New `www/src/session-canvas/stream/transcriptDenylist.ts`

Tests to update or add:

- API route test proving a meta event includes `nativePayload`.
- API projection test proving `normalize() -> None` meta rows are not empty in the public transcript view.
- Frontend map test proving meta renders raw JSON.
- Frontend map test proving an empty denylist hides nothing.
- Frontend matcher unit tests for dotted path, equality, and array wildcard.

### Smallest First Slice

1. Expose `nativePayload` on `/v1/sessions/{id}/events` and event SSE.
2. Render meta records and empty wire context records as pretty raw JSON in transcript chat.
3. Add an empty UI denylist matcher with no active rules.
4. Add tests for a `session_meta` or Claude `attachment` style meta row that currently renders empty.

No adapter side `meta_blocks`. No subtype allowlist. No provider selective rescue.

## Dependencies

- Pydantic model aliases convert `native_payload` to `nativePayload` through `PublicSessionModel`.
- psycopg JSONB already stores `event.raw`.
- React transcript chat already maps `SessionEventView` through `mapIrToChat.ts`, so the render seam is localized.

## Relevance to Helioy

This decision preserves the Helioy pattern of separating durable capture from UI curation. Complete capture belongs in the data path; curation belongs in a reversible view layer unless it is an access control rule.

## Open Questions

- Should the first slice include a visible show hidden toggle even with an empty denylist, or wait until the first active owner deny rule?
- Should `nativePayload` be top level on `TranscriptEventView`, or nested under a body field such as `source`? Top level is simpler for UI filtering.
- Should very large raw payloads get a viewer affordance or virtualization before reveal all ships broadly?
