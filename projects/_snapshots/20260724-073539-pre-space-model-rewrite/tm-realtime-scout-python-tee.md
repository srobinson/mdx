# Scout: realtime Python tee and Activity live seam

Read only scout of `transport-matters` at `ef52af6`, with a clean worktree. All
evidence cites a file and symbol. No line references are used.

**Crux: there is no existing live response block channel from the capture
plane to the Activity product plane.** Two adjacent live surfaces exist, but
they are disconnected from this need. Python has an in process run scoped
`broadcast` queue exposed by `/v1/runs/{run_id}/stream`, consumed by Inspector.
Activity has a Gateway owned workspace SSE stream fed by Postgres reconciliation.
The Anthropic and Codex HTTP response tee feeds neither surface per block. The
durable `ExchangeSink` and `tm_events` wire notification both fire after exchange
finalization.

## Reuse Map

### 1. The tee as implemented

- `handle_response_headers` in
  `api/src/transport_matters/addon_handlers.py` installs the tee through
  `install_response_tee` in `api/src/transport_matters/response_stream.py`.
  `_should_stream_response` selects upstream Anthropic event streams and Codex
  HTTP Responses traffic. WebSocket upgrades, local responses, and status 101
  are excluded.
- `install_response_tee` creates one `bytearray`, saves it in flow metadata,
  and assigns a synchronous `capture_chunk` callback to
  `flow.response.stream`. Every nonempty byte chunk delivered by mitmproxy is
  appended immediately. The exact chunk object is returned unchanged, so
  forwarding continues without waiting for response completion. Empty chunks
  are passed through and do not change the buffer.
- The callback sees transport chunks, not guaranteed SSE record boundaries. A
  chunk can contain several events or part of one event. Every
  `content_block_start`, `content_block_delta`, and `message_delta` byte crosses
  this callback while the upstream response is active, subject to arbitrary
  chunk splitting. `test_response_tee_accumulates_and_passes_chunks_through` in
  `api/src/transport_matters/test_response_stream.py` pins accumulation and
  identity preserving forwarding.
- The callback only appends bytes. It does not parse, classify, broadcast, or
  call an exchange sink.
- `handle_response` in `api/src/transport_matters/addon_handlers.py` runs after
  streaming completes. It first calls `restore_streamed_response`, which moves
  the accumulated bytes into `flow.response.raw_content`, then calls
  `persist_http_exchange`.
- Claude's primary provisional path completes inside
  `_finalize_http_provisional_exchange` in
  `api/src/transport_matters/exchange_recorder.py`. That symbol parses the full
  restored body, persists the completed Tier 1 exchange, then calls
  `emit_to_index` and `emit_exchange`. The nonprovisional branch in
  `persist_http_exchange` follows the same persist then sink then broadcast
  order. `test_streamed_provisional_finalize_matches_buffered_response` in
  `api/src/transport_matters/test_response_stream_capture.py` proves the
  buffered and streamed paths produce identical raw response bytes, response
  IR, and response statistics.

**Timing:** the tee receives bytes live. Response parsing, the durable exchange
sink, wire store submission, and the ordinary exchange broadcast happen at
completion for Anthropic and Codex HTTP responses.

### 2. SSE parsing available for reuse

#### Shared framing

- `iter_sse_data_objects` in `api/src/transport_matters/sse.py` decodes a byte
  buffer, scans `data:` lines, skips empty and `[DONE]` payloads, parses JSON,
  and yields dictionary payloads.
- This function is reusable for complete SSE records. Its interface is
  stateless and whole buffer based. Passing arbitrary tee chunks directly is
  unsafe because a JSON `data:` line can span chunks. The first fragment is
  discarded as invalid JSON and the continuation has no `data:` prefix.
  Repassing the cumulative buffer would redeliver earlier events. A live fold
  therefore needs retained framing state around this parser or an extracted
  stateful equivalent.

#### Anthropic

- `AnthropicAdapter._inbound_response_sse` in
  `api/src/transport_matters/adapters/anthropic.py` is a buffered finalization
  API. It receives the full body, creates local `block_buffers`, walks payloads
  from `iter_sse_data_objects`, and returns one `InternalResponse` after the
  loop.
- The internal branch logic is event incremental:
  - `content_block_start.content_block.type == "thinking"` identifies
    reasoning immediately.
  - `content_block_start.content_block.type == "tool_use"` identifies a
    running tool immediately.
  - `content_block_start.content_block.type == "text"` identifies generation
    immediately.
  - `content_block_delta.delta.type` repeats the useful class as
    `thinking_delta`, `input_json_delta`, or `text_delta`.
  - `message_delta.delta.stop_reason` provides the terminal response reason.
- The existing public method cannot resume across chunks because all state is
  local. Its event loop can be extracted or wrapped, while retaining the same
  event rules.
- `_parse_text_block`, `_parse_thinking_block`, `_parse_tool_use_block`, and
  `AnthropicAdapter._parse_response_content` are complete block to IR helpers.
  They remain useful after `content_block_stop`. `_parse_tool_use_block`
  requires `id`, `name`, and parsed `input`, so it cannot classify the initial
  `tool_use` start before the streamed JSON input is complete. Live activity
  classification should reuse the event types above and reserve these helpers
  for complete IR construction.

#### Codex

- `CodexAdapter.inbound_response` in
  `api/src/transport_matters/codex/adapter.py` delegates to
  `parse_codex_response_sse` in
  `api/src/transport_matters/codex/response_parser.py`. That path is also
  buffered: `parse_sse_event_payloads` builds a full payload list, then
  `parse_codex_response_payloads` folds it.
- The reusable incremental vocabulary already exists in
  `api/src/transport_matters/codex/protocol.py`:
  `codex_payload_event_type`, `codex_terminal_status`,
  `codex_update_open_assistant_items`, and `codex_update_open_tool_calls`.
  `response.output_item.added` exposes item types such as `reasoning`,
  `function_call`, `custom_tool_call`, and `tool_search_call`.
  `response.output_text.delta` identifies generation. `response.completed` and
  `response.failed` are terminal.
- `derive_codex_turn_incremental` and
  `_append_server_payload_events` in
  `api/src/transport_matters/codex/derivation_engine.py` already advance an open
  Codex derivation cursor from newly observed payloads. They maintain open text
  and tool call state and recognize terminal payloads.
- The WebSocket path is already message framed. `handle_codex_websocket_message`
  in `api/src/transport_matters/addon_handlers.py` receives each server frame,
  and `record_codex_websocket_message` in
  `api/src/transport_matters/codex/transport.py` updates transport state. HTTP
  fallback still requires SSE framing before the same payload helpers can be
  applied.

### 3. Live proxy to product channel map

#### Durable finalize channel

- `ExchangeSink` in
  `api/src/transport_matters/storage/exchange_sink.py` is now a multi subscriber
  registry. `register_exchange_sink`, `_fan_out`, and returned unregister
  handles are reusable patterns. Failures are isolated per subscriber and
  never fail Tier 1 persistence.
- Its contract is explicitly post persist and final only. `emit_to_index` fires
  exactly once after a completed exchange is stored. Provisional request only
  rows and live Codex provisional rewrites remain silent. Reusing this exact
  interface for per block events would break its documented semantics.
- `_start_session_capture` in
  `api/src/transport_matters/addon_runtime.py` registers the transcript cursor
  sink and `WireStoreObserver.register` as peer subscribers.
- `WireStoreObserver.on_exchange` in
  `api/src/transport_matters/wire_store_observer.py` builds a
  `WireExchangeWrite` from the completed `ExchangeArtifacts` and schedules
  `SessionWriter.submit_wire_exchange`.
- `SessionWriter.submit_wire_exchange` in
  `api/src/transport_matters/session/writer.py` writes the durable wire store,
  then sends a `wire_exchange` payload on `tm_events`. The payload carries run,
  exchange, workspace, and owner identity. It carries no response block event.
- `createActivityGatewayDeps` in `packages/activity/src/gatewayDeps.ts` wires
  Activity exclusively to `PostgresActivityReader` and
  `TmEventsActivityListener`. `TmEventsActivityListener.dispatchNotification`
  and `parseTmEventsPayload` in
  `packages/activity/src/adapters/tmEvents.ts` treat the notification as a
  reconciliation trigger. `ActivityIngestion.reconcile` then reads lifecycle,
  transcript, and latest finalized wire snapshot rows from Postgres.

This channel is live after a database commit, but the wire contribution begins
only after response finalization.

#### Existing capture plane SSE

- `broadcast.emit` and `broadcast.subscribe` in
  `api/src/transport_matters/broadcast.py` form an in process, run scoped queue.
  `stream_run` in `api/src/transport_matters/api/v1/stream.py` exposes it as
  `GET /v1/runs/{run_id}/stream`.
- `emit_exchange` in `api/src/transport_matters/exchange_recorder.py` publishes
  an `exchange` summary. `ResStats` in
  `api/src/transport_matters/storage/base.py` carries stop reason, token counts,
  text character count, and tool call count. It carries no response block type
  or tool identity.
- Codex WebSocket provisional activity is a partial exception to final only
  timing. `rewrite_codex_provisional_exchange` in
  `api/src/transport_matters/codex/exchange_derivation.py` persists updated
  provisional Tier 1 artifacts and can call `emit_exchange` when the summary
  changes. This can expose open text and tool counts mid turn. It still emits
  summary data rather than provider block events, and Anthropic plus Codex HTTP
  tee chunks do not enter this queue live.
- `useExchangeStream` in
  `www/packages/inspector/src/hooks/useExchangeStream.ts` is the production
  consumer of `/v1/runs/{run_id}/stream`. Activity does not subscribe to it.
- `createActivityRouter` in
  `packages/activity/src/server/activityRouter.ts` serves a separate
  `/workspaces/:workspaceId/activity/stream`. Its deltas come from Activity
  projections after ingestion and reconciliation. Python proxies this Gateway
  route through `create_run_proxy_mount` in
  `api/src/transport_matters/api/v1/run_proxy.py`.

#### Other run channels

- `/v1/runs/{run_id}/terminal`, mounted by `create_run_proxy_mount`, is a
  Gateway owned PTY WebSocket. It transports terminal bytes only.
- The capture RPC in `api/src/transport_matters/capture_rpc.py` and
  `api/src/transport_matters/api/v1/capture_rpc_routes.py` owns prepare,
  release, and health. It carries lifecycle facts and no response stream.
- No product plane run event endpoint consumes provider SSE block events.

**Channel conclusion:** an in process live capture queue exists, and an
Activity workspace stream exists. There is no existing bridge between them,
and the durable ExchangeSink plus `tm_events` path starts at finalization. A
per block feed therefore needs a new live producer contract and a product plane
landing path, even if the eventual design reuses one of the adjacent transports.

### 4. Frozen plane constraint

- `docs/ARCHITECTURE.md`, section `Two plane rule`, assigns mitmproxy, Tier 1,
  the frozen Inspector API, and the Postgres session store to Python. New
  product contexts live in TypeScript. The same document names the Gateway as
  the live seam and requires product packages to avoid capture plane filesystem
  paths.
- `docs/ARCHITECTURE.md`, section `Target context map`, requires producers to
  publish facts and keeps Activity status computation inside Activity.
- `api/CLAUDE.md`, section `Import DAG`, requires `storage` never to import
  `session`. Runtime sinks are injected at `load_runtime`. The current
  `ExchangeSink` registration inside `_start_session_capture` demonstrates this
  dependency inversion.
- Tier 1 remains authoritative. The live signal must remain best effort and
  must not delay, mutate, or fail provider byte forwarding or completed exchange
  persistence.
- `capture_chunk` is synchronous on the mitmproxy response path. A blessed live
  emit seam must preserve exact chunk return, avoid blocking work, isolate
  subscriber failures, and keep provider parsing state outside storage.
- Python should emit provider facts with run identity. Activity owns the
  thinking, tool, generating, idle, and terminal state transitions.

The blessed change can add a narrow emission point to the frozen capture path.
It cannot turn `response_stream.py` into an Activity implementation, create a
`storage` to `session` import, or replace the completion persistence path.

### 5. Empty at spawn

- `CaptureLeaseRegistry.prepare_capture` in
  `api/src/transport_matters/capture_rpc.py` registers the live capture lease,
  stores run facts, then calls `CaptureLeaseRegistry._emit_lifecycle` with
  `run-started`. `_emit_lifecycle` builds a canvas
  `RunLifecycleEventRow` through `build_run_lifecycle_event` in
  `api/src/transport_matters/run_lifecycle.py`.
- `SessionWriter._commit_run_lifecycle_event` in
  `api/src/transport_matters/session/writer.py` inserts that row independently
  through `AsyncSessionDao.insert_run_lifecycle_event`. The lifecycle model
  `RunLifecycleEventRow` in `api/src/transport_matters/session/models.py` has no
  owner field and permits a null `session_id`.
- Session creation follows transcript ingestion. `_start_session_capture` in
  `api/src/transport_matters/addon_runtime.py` makes the tailer callback build
  an `EventBatch`. `TranscriptTailer._poll_cursor` in
  `api/src/transport_matters/index/tailer.py` submits only when complete records
  produce writes. `SessionWriter._commit_batch` then calls
  `AsyncSessionDao.upsert_session` before inserting those events. A launched
  run with no transcript record has a lifecycle row and no session row.
- `RUNS_BY_WORKSPACE_SQL` in
  `packages/activity/src/adapters/postgresRecords.ts`, used by
  `PostgresActivityReader.runsForWorkspace`, starts from
  `run_lifecycle_event` and uses an inner `JOIN session` on run and workspace.
  Its owner gate is `session.owner = $3`, and it applies the primary session
  filter. A lifecycle only run cannot satisfy the join, so workspace discovery
  never materializes its Activity actor and the `starting` state is unreachable.

**Minimal fix shape:** workspace run enumeration must admit lifecycle only rows.
A `LEFT JOIN` is the structural change, with the owner predicate moved out of
the `WHERE` clause so null session rows survive. A plain join keyword change is
insufficient because `session.owner = $3` in `WHERE` would still reject nulls.
The lifecycle table has no owner, so the design must also state how owner scope
is preserved for lifecycle only rows. This is the only unresolved part of the
minimal SQL shape.

## Quality Map

### Strong existing guarantees

1. The tee is byte preserving. Focused tests prove chunk identity forwarding,
   exact accumulation, restoration, and streamed versus buffered persistence.
2. `ExchangeSink._fan_out` provides multi subscriber delivery, idempotent
   unregister handles, and per subscriber exception isolation.
3. Codex already has incremental derivation helpers and tests. The live design
   should reuse those helpers rather than create another payload fold.
4. Activity keeps IO in adapters and services. `RunActivityEventStream` in
   `packages/activity/src/domain/runActivityContext.ts` already includes a
   dedicated `wire` cursor, so live facts need not share transcript ordering.
5. The Activity Gateway stream sends snapshot first, then deltas, with
   keepalives and cleanup in `createActivityRouter`.

### Gaps and risks to carry into design

1. `response_stream.py` keeps an unbounded `bytearray` for the full response.
   A live parser also needs bounded partial frame state without duplicating the
   full buffer.
2. `iter_sse_data_objects` has no incremental framing contract. Chunk split
   tests are required before any callback is treated as an event feed.
3. `broadcast.py` is process resident, has a queue size of 1000, drops on
   overflow, and has no resume cursor or snapshot. It is suitable evidence of a
   transport pattern, not proof of Activity delivery semantics.
4. The capture SSE payload lacks typed response blocks. Its Codex provisional
   summaries are provider specific partial coverage and cannot establish
   Anthropic parity.
5. `ExchangeSink` is deliberately final only. Adding live emissions to it would
   erase a useful semantic boundary between provisional activity and completed
   durable exchanges.
6. `RUNS_BY_WORKSPACE_SQL` has a unit assertion for the session join and owner
   predicate, but no lifecycle only run case. Owner scope for a row without a
   session is currently undefined by the schema.
7. Database backed verification was unavailable in this shell because no
   Transport Matters test database URL is configured. The source trace proves
   the join and insert ordering, while an integration test remains required.

### Verification observed

- Python focused pure tests: 98 passed, 1 database dependent test deselected.
  Coverage included the response tee, streamed capture, exchange sink, wire
  observer, Anthropic adapter, Codex adapter, and Codex incremental derivation.
- Capture RPC tests: 20 passed.
- `@tm/activity` tests: 198 passed, 22 skipped.
- `@tm/activity` TypeScript check: passed with `tsc --noEmit`.
- Database backed tests stopped during fixture setup with
  `MissingDatabaseConfigError`; no database assertions were claimed.
- Worktree remained clean after verification.

## Plan

This scout does not select a transport or prescribe the implementation. The
design round should proceed through these evidence gates:

1. Define one provider neutral live fact vocabulary and map Anthropic start,
   delta, and stop payloads plus Codex item, text, tool, and terminal payloads
   onto it. Preserve provider event identity for diagnostics.
2. Specify incremental SSE framing independently from activity state. Prove
   arbitrary chunk splits, several events per chunk, `[DONE]`, malformed JSON,
   and trailing partial data.
3. Choose the plane crossing with the channel map above in view. Treat the
   Inspector run stream, Postgres `tm_events`, and Activity workspace stream as
   separate contracts unless the design explicitly joins them.
4. Preserve frozen plane invariants with red tests: exact byte pass through,
   no capture path exception leakage, no blocking subscriber work, unchanged
   completed Tier 1 artifacts, and final only `ExchangeSink` behavior.
5. Add lifecycle only workspace discovery as a separable SQL correction. Lock
   owner semantics before changing the join, then prove a fresh never prompted
   run appears as `starting` and remains owner scoped.
6. Finish with provider parity integration tests and the existing Python and
   `@tm/activity` gates, including a configured Postgres run.

