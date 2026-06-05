---
title: Unified Transcript IR in Transport Matters
type: research
tags: [transport-matters, transcript, ir, codex, claude, session-store]
summary: Claude and Codex transcript turns normalize into a shared NormalizedTurn IR before Postgres persistence, then project to a provider neutral TranscriptEventBody for the UI.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Executive Summary

Transport Matters has a unified session transcript representation for DB backed UI reads. Claude and Codex transcript records enter through provider adapters, normalize into `NormalizedTurn` with shared `ContentBlock` parts, persist before read time, then project into the same public `TranscriptEventBody` union consumed by the React transcript UI.

Verdict: **unified-and-identical for the UI contract**. Provider source semantics can still choose different normalized roles before render, most visibly Codex `developer` `response_item` records becoming `role=system` and therefore `body.kind=wire_injected`.

## Project Metadata

- Language: Python 3.14 for API and capture runtime, TypeScript for web UI.
- Backend framework: FastAPI with Pydantic v2 models, psycopg Postgres access, Alembic migrations. See `api/pyproject.toml`.
- Frontend framework: React 19, Vite, TypeScript, Vitest, pnpm 10. See `www/package.json`.
- Indexed: `.fmm.db` exists at repo root and fmm structural reads were used first.
- Relevant architecture docs: `PROJECT.md` describes the transcript tailer, session store, and split between wire artifacts and transcript events.

## Architecture

### Parse and normalize

The transcript side uses an adapter interface as the anti corruption layer:

- Shared contract: `api/src/transport_matters/index/adapters/base.py:NormalizedTurn` lines 137 to 155.
- Adapter interface: `api/src/transport_matters/index/adapters/base.py:TranscriptAdapter` lines 158 to 188.
- Shared content block union: `api/src/transport_matters/ir.py:ContentBlock` lines 68 to 71.

Provider entry points:

- Claude: `api/src/transport_matters/index/adapters/claude.py:ClaudeAdapter.normalize` lines 111 to 136. It accepts native conversational records, maps role, timestamp, model, parent id, and content into `NormalizedTurn`. `claude.py:_content_to_parts` lines 139 to 144 and `claude.py:_block` lines 147 to 169 convert native Claude blocks into shared text, thinking, tool use, tool result, image, or unknown blocks.
- Codex: `api/src/transport_matters/index/adapters/codex.py:CodexAdapter.normalize` lines 82 to 110. It accepts only `response_item` records. `codex.py:_payload_to_role_and_parts` lines 113 to 127 maps Codex messages, function calls, function outputs, reasoning, and unknown durable items into the same block vocabulary. Codex `developer` messages map to `role=system` at this stage.

`api/src/transport_matters/codex/events.py:CodexSemanticEvent` lines 66 to 86 and `CodexTurnSummary` lines 89 to 183 are Codex wire derivation artifacts for exchange storage. They are not the Postgres session transcript IR.

### Persist

Normalization happens before the DB write:

- `api/src/transport_matters/index/tailer.py:ingest_records` lines 139 to 205 calls `adapter.normalize`, emits a write for every record, advances seq for turns and meta records, and threads Codex `turn_context.model` forward.
- `api/src/transport_matters/session/ingest.py:build_event` lines 115 to 142 writes turn rows from `NormalizedTurn` or meta rows when normalization returns `None`.
- `api/src/transport_matters/session/ingest.py:_turn_ir` lines 166 to 185 persists `turn.model_dump(mode="json")` as normalized JSON, with inline images redacted to artifact refs.
- `api/src/transport_matters/session/ingest.py:_meta_event` lines 145 to 163 persists provider raw for non turn records and sets `ir=None`.

The event table stores both source and normalized data:

- `api/src/transport_matters/session/models.py:EventRow` lines 100 to 122 has `raw` and `ir` fields.
- `api/src/transport_matters/session/dao_rows.py:event_params` lines 99 to 109 wraps both as JSONB parameters.
- `api/src/transport_matters/session/dao_statements.py:INSERT_EVENT_SQL` lines 190 to 219 writes `raw` and `ir` and updates both on conflict.
- `api/src/transport_matters/session/writer.py:SessionWriter._commit_batch` lines 107 to 163 upserts the session, inserts each event, links artifacts, and notifies listeners.

Normal owner scoped event reads omit raw:

- `api/src/transport_matters/session/models.py:EventReadRow` lines 149 to 169 includes `ir`, not `raw`.
- `api/src/transport_matters/session/async_dao.py:AsyncSessionDao.get_events_for_owner` lines 197 to 217 returns `EventReadRow`.

### Read and project

`/v1/sessions/{session_id}/events` builds a public transcript event view from DB rows:

- Route: `api/src/transport_matters/api/v1/session_routes.py:list_session_events` lines 200 to 226.
- View model: `api/src/transport_matters/api/v1/session_models.py:TranscriptEventView` lines 128 to 135.
- Body union: `api/src/transport_matters/api/v1/session_models.py:TranscriptEventBody` lines 112 to 119.
- Projection: `api/src/transport_matters/api/v1/session_models.py:transcript_event_view` lines 189 to 197.
- Body classification: `api/src/transport_matters/api/v1/session_models.py:_event_body` lines 200 to 220.

`_event_body` is provider neutral. It inspects normalized `ir.parts`, then `row.kind` and `row.role`:

1. First tool use block becomes `TranscriptToolUseBody`.
2. First tool result block becomes `TranscriptToolResultBody`.
3. Non turn rows or system role rows become `TranscriptWireInjectedBody`.
4. User role becomes `TranscriptUserBody`.
5. Everything else becomes `TranscriptAssistantBody`.

The timeline read surface uses raw for meta labelling, while turns still use normalized IR:

- `api/src/transport_matters/session/timeline.py:project_timeline` lines 61 to 136 iterates rows.
- `timeline.py:_message_item` lines 151 to 167 uses `_parts(row.ir)` for turn messages.
- `timeline.py:_meta_item` lines 170 to 216 classifies native meta record keys into state, context, diagnostic, or native record items.
- `timeline.py:_parts` lines 427 to 433 extracts normalized parts from `ir.parts` or `ir.content`.

### Render

The React transcript chat receives one shared contract:

- TypeScript body union: `www/src/session-canvas/api/sessionEvents.ts:TranscriptEventBody` lines 8 to 13.
- TypeScript event view: `www/src/session-canvas/api/sessionEvents.ts:SessionEventView` lines 21 to 29.
- Mapping entry point: `www/src/session-canvas/stream/mapIrToChat.ts:mapSessionEventToChatItems` lines 16 to 19.
- Render branch: `www/src/session-canvas/stream/mapIrToChat.ts:mapSessionEventToTranscriptMessage` lines 21 to 28.
- Body blocks: `www/src/session-canvas/stream/mapIrToChat.ts:bodyBlocks` lines 56 to 79.
- Wire rendering: `www/src/session-canvas/stream/mapIrToChat.ts:mapWireInjectedEvent` lines 81 to 87.

The render path branches on `event.kind` and `body.kind`, not provider. Meta events are rendered as `TranscriptMessageModel.kind="meta"` before `body.kind="wire_injected"` is considered, so a meta event with wire injected body remains a meta message in chat.

## Key Patterns

- **Adapter owned normalization.** Provider logic is isolated in `ClaudeAdapter` and `CodexAdapter`. The session store and UI do not read provider native transcript shapes directly.
- **Raw plus normalized storage.** Postgres keeps provider raw for audit and meta classification, plus normalized `ir` JSON for turn rendering.
- **Provider escape hatches.** `provider_data` and `UnknownBlock` preserve provider details without changing the shared body union.
- **Read model projection.** The public API projects DB rows to a curated discriminated union before the UI sees them.

## Detailed Findings

### Verdict

The session transcript path is unified at the durable turn IR and at the UI event contract. It is not two provider specific DB body shapes.

The precise transcript IR type is `NormalizedTurn`, backed by shared `ContentBlock` parts. The older wire exchange IR types `InternalRequest` and `InternalResponse` are still real, but they describe proxied request and response artifacts, not the Postgres transcript timeline.

### Where provider structure is erased

Provider structure is mostly erased at parse time:

- Claude content list or string becomes shared content blocks in `claude.py:_content_to_parts` and `_block`.
- Codex `response_item` payloads become shared roles and blocks in `codex.py:_payload_to_role_and_parts`.
- `session/ingest.py:_turn_ir` serializes the normalized object into `event.ir` before persistence.

Read time projection does not reparse provider raw for normal `/events` reads. It projects from `event.ir`, `event.kind`, and `event.role`.

### What lands in `event`

For turns, `event.raw` is provider native JSON and `event.ir` is normalized `NormalizedTurn` JSON. For meta records, `event.raw` is provider native JSON and `event.ir` is null.

There is no DB column named `body`. `TranscriptEventView.body` is a public API projection produced on read by `api/v1/session_models.py:_event_body`.

### Provider divergence that survives

No provider conditional survives in `api/v1/session_models.py:_event_body` or `mapIrToChat.ts`. Concrete source driven differences still appear because adapters choose roles and event kinds:

- Codex `session_meta` and `turn_context` are not normalized into turns. They become `EventKind.META`, then `TranscriptWireInjectedBody` with label `meta`.
- Codex `response_item` with native role `developer` becomes `role=system`, persists as a turn, then projects as `TranscriptWireInjectedBody` with label `turn`.
- Claude conversational `user` and `assistant` records become normal turn bodies. Non conversational Claude records, when present, take the same meta path as Codex skipped records.

So the contract is identical, but event sequences and classifications can differ because the native providers emit different transcript semantics.

## Dependencies

- Pydantic supplies frozen discriminated models for IR and public read models.
- psycopg and Postgres JSONB persist `raw` and `ir`.
- FastAPI exposes owner scoped `/v1/sessions/{session_id}/events` and `/timeline` surfaces.
- React and TypeScript consume `SessionEventView` and map it to chat messages.

## Verification

Commands and probes run on 2026-06-16:

```bash
cd api && .venv/bin/python -m pytest \
  src/transport_matters/index/adapters/test_codex.py::TestNormalize::test_skips_session_meta_turn_context_and_event_msg \
  src/transport_matters/index/adapters/test_codex.py::TestNormalize::test_developer_message_maps_to_system_role
```

Result: 2 passed.

```bash
cd www && pnpm test -- mapIrToChat.test.ts
```

Result: Vitest reported 131 test files passed and 890 tests passed.

An in memory Codex fixture probe over `api/tests/fixtures/codex_rollout.jsonl` produced:

| Native record | Event kind | Event role | Public body kind | Label |
|---|---|---|---|---|
| `session_meta` | `meta` | null | `wire_injected` | `meta` |
| `turn_context` | `meta` | null | `wire_injected` | `meta` |
| `event_msg` | `meta` | null | `wire_injected` | `meta` |
| user `response_item` | `turn` | `user` | `user` | null |
| developer `response_item` | `turn` | `system` | `wire_injected` | `turn` |
| reasoning `response_item` | `turn` | `assistant` | `assistant` | null |

A DB backed ingest test was attempted but not counted as evidence because this environment lacks `TRANSPORT_MATTERS_TEST_DATABASE_URL` or `TRANSPORT_MATTERS_DATABASE_URL`.

## Relevance to Helioy

This pattern is the right seam for future provider additions. New providers should implement `TranscriptAdapter.normalize` into `NormalizedTurn`, store raw plus normalized JSON, and avoid adding provider branches to `TranscriptEventBody` or frontend render code unless a genuinely new semantic body kind is needed.

## Open Questions

- Should `TranscriptWireInjectedBody.label` distinguish `meta` system context from `turn` system context with clearer product labels?
- Should Codex `developer` messages remain turn scoped wire context, or should they become meta events for closer visual parity with other injected context?
- Should `/timeline` eventually stop using provider native meta keys directly and move meta classification into a normalized meta IR?
