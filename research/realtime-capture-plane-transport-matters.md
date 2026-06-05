---
title: Realtime Capture Plane and Activity Channel Map
type: research
tags: [transport-matters, realtime, sse, activity, capture-plane, wire]
summary: The live response tee sees every upstream chunk, but no response block channel currently connects Python capture to the Activity product plane.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-10
updated: 2026-07-10
---

## Executive Summary

Transport Matters captures provider traffic in Python and computes live run
status in the TypeScript Activity context. The response tee receives upstream
HTTP chunks in real time, but only buffers them. Completed exchanges reach the
wire store and Postgres notification path after finalization, and no typed
response block channel currently crosses from capture to Activity.

The full scout is
`~/.mdx/projects/tm-realtime-scout-python-tee.md` at repository head
`ef52af6`.

## Project Metadata

- Languages: Python 3.14 and TypeScript
- Python framework: FastAPI with mitmproxy 12.2
- Product server: Fastify
- Activity domain: XState
- Durable store: Postgres through psycopg and `pg`
- Build and package systems: uv and Hatch for Python, pnpm 10 for TypeScript
- Relevant packages: `api/src/transport_matters`, `packages/activity`,
  `www/packages/inspector`, and `www/packages/canvas`
- Helioy signal: the repository is fmm indexed and exposes current structural
  data through the fmm MCP server.

## Architecture

### Capture path

`handle_response_headers` in
`api/src/transport_matters/addon_handlers.py` calls
`install_response_tee` in `api/src/transport_matters/response_stream.py`.
The tee stores one `bytearray` in flow metadata and installs a synchronous
callback that appends nonempty chunks and returns each chunk unchanged.

`handle_response` runs at response completion. It calls
`restore_streamed_response`, then `persist_http_exchange`. Claude's normal
streaming path completes in `_finalize_http_provisional_exchange` in
`api/src/transport_matters/exchange_recorder.py`. Tier 1 persistence precedes
`emit_to_index` and `emit_exchange`.

### Durable wire path

`ExchangeSink` in
`api/src/transport_matters/storage/exchange_sink.py` is a multi subscriber,
post persist registry with isolated observer failures. Its contract is one
emission for each completed exchange. `WireStoreObserver.on_exchange` in
`api/src/transport_matters/wire_store_observer.py` submits the completed
exchange through `SessionWriter.submit_wire_exchange`, which commits Postgres
wire rows and sends a `wire_exchange` notification on `tm_events`.

### Activity path

`createActivityGatewayDeps` in `packages/activity/src/gatewayDeps.ts` composes
`PostgresActivityReader`, `ActivityIngestion`, and
`TmEventsActivityListener`. Notifications trigger reconciliation, then
`ActivityIngestion.reconcile` reads lifecycle, transcript, and latest finalized
wire state from Postgres. `createActivityRouter` in
`packages/activity/src/server/activityRouter.ts` serves snapshot and delta
frames on the workspace Activity SSE stream.

### Adjacent live channels

Python has a run scoped in process queue in
`api/src/transport_matters/broadcast.py`, exposed by `stream_run` in
`api/src/transport_matters/api/v1/stream.py`. Inspector consumes this endpoint
through `useExchangeStream` in
`www/packages/inspector/src/hooks/useExchangeStream.ts`.

The payload is an exchange summary. `ResStats` in
`api/src/transport_matters/storage/base.py` provides stop reason, usage, text
character count, and tool count. Typed response blocks and tool identity are
absent. Activity does not consume this run stream. Its workspace SSE is a
separate Gateway contract.

## Key Patterns

### Byte preserving streaming tee

The provider response callback performs constant surface work: append bytes,
then return the original chunk. Completion parsing sees the same full bytes as
the buffered path. This isolates forwarding from interpretation and is worth
preserving.

### Dependency inverted observers

The storage layer owns an observer registry and imports no session code.
`_start_session_capture` in
`api/src/transport_matters/addon_runtime.py` registers higher level consumers
at the composition root. The pattern preserves the Python import DAG while
supporting several observers.

### Store as data, notification as trigger

Activity treats `tm_events` as a reconciliation signal. Durable Postgres rows
remain the data source. This gives reconnect safety for lifecycle, transcript,
and finalized wire facts, but cannot provide response block timing before a
row exists.

### Provider payload helpers

`iter_sse_data_objects` in `api/src/transport_matters/sse.py` parses complete
SSE data lines from a byte buffer. It has no retained partial frame state.

`AnthropicAdapter._inbound_response_sse` contains event based fold logic for
`content_block_start`, `content_block_delta`, `content_block_stop`, and
`message_delta`, but exposes a whole body interface. `_parse_text_block`,
`_parse_thinking_block`, and `_parse_tool_use_block` build final IR blocks.

Codex has stronger incremental reuse. `codex_payload_event_type`,
`codex_terminal_status`, `codex_update_open_assistant_items`, and
`codex_update_open_tool_calls` live in
`api/src/transport_matters/codex/protocol.py`.
`derive_codex_turn_incremental` and `_append_server_payload_events` in
`api/src/transport_matters/codex/derivation_engine.py` advance open turn state
from newly observed payloads.

## Detailed Findings

### Realtime tee behavior

Every upstream byte reaches the tee while streaming, but mitmproxy chunk
boundaries do not guarantee SSE record boundaries. The current callback does
no parsing or emission. Anthropic and Codex HTTP parsing begins only after
`restore_streamed_response` reconstructs the complete body.

A live parser cannot safely call `iter_sse_data_objects` once per raw chunk.
Split JSON lines would be lost. Reprocessing the cumulative buffer would
duplicate prior events. Retained framing state is required before existing
payload folds can be applied incrementally.

### Response type mapping

Anthropic exposes activity classes at block start:

- `thinking` maps to reasoning.
- `tool_use` maps to running tool.
- `text` maps to generating.
- `message_delta.delta.stop_reason` supplies completion reason.

Codex exposes comparable facts through `response.output_item.added`,
`response.output_text.delta`, `response.completed`, and `response.failed`.
WebSocket traffic is already message framed inside
`handle_codex_websocket_message`. HTTP fallback requires SSE framing first.

### Channel conclusion

No live response block channel reaches Activity. The capture run SSE and the
Activity workspace SSE both exist, but they serve different consumers and
carry different contracts. The durable ExchangeSink and `tm_events` wire path
begin after finalization.

Codex WebSocket provisional rewrites are a partial exception inside the
capture run SSE. `rewrite_codex_provisional_exchange` in
`api/src/transport_matters/codex/exchange_derivation.py` can emit changed text
and tool counts mid turn. This remains an Inspector summary and provides no
Anthropic HTTP parity.

### Empty at spawn

`CaptureLeaseRegistry.prepare_capture` in
`api/src/transport_matters/capture_rpc.py` emits `run-started` after registering
the capture lease. Lifecycle insertion is independent from session insertion.
`RunLifecycleEventRow` has no owner field and permits a null `session_id`.

Session insertion happens when transcript records produce an `EventBatch`.
`SessionWriter._commit_batch` upserts the session immediately before event
insertion. A never prompted run therefore has a lifecycle row and no session
row.

`RUNS_BY_WORKSPACE_SQL` in
`packages/activity/src/adapters/postgresRecords.ts` inner joins lifecycle to
session for owner gating. The lifecycle only run is excluded. A left join must
also move the owner predicate out of `WHERE`, and the design must define owner
scope because lifecycle rows have no owner field.

## Dependencies

- mitmproxy provides response streaming callbacks and HTTP flow metadata.
- FastAPI exposes the frozen capture API and proxies Gateway routes.
- psycopg writes the session, lifecycle, and wire stores and sends
  notifications.
- Fastify serves Activity snapshots and SSE deltas.
- XState owns run status transitions in Activity.
- `pg` supplies Activity reads and LISTEN support.

## Relevance to Helioy

This codebase demonstrates a useful Helioy boundary: capture should publish
facts, while product contexts interpret them. It also shows why durable and
live planes need separate timing contracts. Reusing observer isolation,
provider fold helpers, and Gateway composition can keep a realtime extension
narrow without moving Activity logic into Python.

## Open Questions

1. Which live plane crossing should carry ephemeral block facts: an extension
   of the capture run stream, a new Gateway input, or another explicit
   transport?
2. What replay or snapshot guarantee is required after a Gateway reconnect in
   the middle of a response?
3. What owner value should lifecycle only rows carry before any session exists?
4. Should incremental Anthropic framing be shared with Codex HTTP framing or
   remain provider adapters behind one interface?
5. What bounded memory policy should replace or constrain the current
   full response `bytearray`?

## Verification

- Python focused pure tests: 98 passed, 1 database dependent test deselected.
- Capture RPC tests: 20 passed.
- `@tm/activity` tests: 198 passed, 22 skipped.
- `@tm/activity` typecheck: passed with `tsc --noEmit`.
- Database integration tests were unavailable because no test database URL was
  configured. The worktree remained clean.

