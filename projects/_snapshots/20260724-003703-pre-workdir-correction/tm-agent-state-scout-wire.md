# Scout — wire→activity seam for wire-fed needs_you{asked} (Mode-1)

Feasibility scout for live wire-fed `question-asked` (Slice-1.5), following the
live-bug diagnosis: Claude Code defers journaling the assistant AskUserQuestion
row until answered, so the transcript plane structurally cannot carry a live
`asked`. All citations file + symbol. Repo at `2b8ed01` (clean tree).

**Headline: feasible with ONE narrow frozen-plane touch.** The parsed
`ToolUseBlock(name="AskUserQuestion")` already exists in-process at
response-completion time on the api plane's `ExchangeSink` seam; that sink is
single-slot and occupied, so composing a second observer at its one
registration site (`addon_runtime.py`) is the minimal frozen edit. Everything
else lands in the product plane. No contract change: `needs-you-asked` and
`needsYouForStatus` already exist.

## Reuse Map

### 1. Wire capture point

- Shared mitmproxy addon `TransportMattersAddon` (`api/src/transport_matters/addon.py`)
  for both harnesses. Response bytes stream live only through the in-memory tee:
  `handle_response_headers` (`addon_handlers.py`) → `install_response_tee`
  (`response_stream.py`) accumulates SSE chunks; the `response` hook
  (`handle_response`) fires once at completion → `restore_streamed_response` →
  `persist_http_exchange` (`exchange_recorder.py`). Streaming Claude finalizes
  via `_finalize_http_provisional_exchange`. Codex: same HTTP path for
  `/responses`; websocket turns finalize via `finalize_codex_provisional_exchange`
  (`codex/exchange.py`).
- **Persistence and parse timing: at response completion, live** (not per-chunk,
  not lazy). Tier-1 write via `storage.persist_exchange` (`DiskStorageBackend`).
- **Product-plane observation point: none today.** The capture RPC
  (`capture_rpc.py` ↔ `packages/runtime/src/adapters/CaptureRpcClient.ts`) is
  lifecycle-only (`prepareCapture`/`releaseCapture`/`captureHealth`). The
  `/runs/{run_id}/stream` SSE (`api/v1/stream.py`, fed by `broadcast.emit` via
  `emit_exchange`) already broadcasts wire exchange completions — but its
  payload is `ReqStats`/`ResStats` (`storage/base.py`): stop_reason + tool-call
  **count**, no tool names. Only the browser consumes it
  (`www/packages/core/src/exchangeStreamEvents.ts`).

### 2. Wire→IR parse

- `extract_response` (`exchange_recorder_artifacts.py`) → `parse_response_ir`
  (`exchange_stats.py`) → `adapters/anthropic.py` SSE fold →
  `_parse_tool_use_block` → `ToolUseBlock` (`ir.py`). Codex:
  `parse_codex_response_sse` → `_tool_use_block` → same `ToolUseBlock`.
- **No symbol special-cases AskUserQuestion in the api plane** — the block is
  generic; `.name == "AskUserQuestion"` (Claude) / `"request_user_input"`
  (Codex) is identifiable but only the product plane keys on those literals
  today (`transcriptRecords.ts`). The parsed `InternalResponse` lands on
  `ExchangeArtifacts.response_ir`: written to tier-1, reduced to name-less
  `ResStats`, and handed to the in-process post-persist sink (next).

### 3. The one live seam that already carries the signal

- `ExchangeSink` (`storage/exchange_sink.py`): `set_exchange_sink` /
  `emit_to_index`, fired inside every finalize path with the **full
  `ExchangeArtifacts` including `response_ir`** — the AskUserQuestion
  `ToolUseBlock` reaches this observer live at ask-time.
- It is **single-slot and occupied**: `addon_runtime.py` registers
  `_make_exchange_cursor_sink(...)`, which uses only
  `request_ir.metadata.session_id` and discards `response_ir`.
- Correlation is solved at this seam: `ProxyRunBinding`
  (`shared_proxy/binding.py`) carries `run_id` (asserted by `require_run_id`);
  `persist_exchange`/`emit_exchange` are already run-keyed. The same
  `run_id` is what `SessionBinding` (`session/models.py`) stamps on event rows
  and what activity ingestion routes on — direct join, no inference.

### 4. Activity landing path (product plane, all reusable)

- `event` table has exactly one writer: the tailer commit path
  (`index/tailer.py` `ingest_records` → `session/ingest.py` `build_event_batch`
  → `SessionWriter.submit` → `INSERT_EVENT_SQL` in `session/dao_statements.py`,
  then `pg_notify` on `tm_events`). No wire-derived rows exist anywhere
  (verified: exchange recorder imports nothing from `session/`).
- TS ingestion is LISTEN/NOTIFY-as-trigger, store-as-data:
  `TmEventsActivityListener` (`adapters/tmEvents.ts`, `parseTmEventsPayload`) →
  `ActivityIngestion.handlers()` → `ReconcileLoop` → reads the `ActivityStore`
  port (`readRecordsForRunAfter`, sole impl `PostgresActivityReader` with
  `EVENT_KIND_TURN_FILTER`) → `actor.send(activityRecordToEvent(record))`.
  **There is no public way to push an event to a run's actor** — actors are
  private to `ActivityIngestion`; a wire producer needs a deliberate new method.
- Dedupe identity: `isNewEvent` (`domain/runActivityContext.ts`) partitions by
  `eventStream(event)` into `lifecycle` vs `record`, each with its own cursor in
  `seqCursors`. Record-stream seq is minted by the tailer (`TailCursor.seq`,
  per-session monotonic) — **a wire record must not join the record stream**
  (unknowable seq: too low → silently dropped; too high → shadows and drops
  later genuine transcript rows). A third `"wire"` stream with its own cursor is
  a pure `@tm/activity` domain extension; `markApplied` already advances
  `seqCursors[stream]` generically, and `foldQuestionAsked` +
  `needs-you-asked` + `needsYouForStatus` are reused unchanged.

### 5. Frozen boundary — the load-bearing answer

**A frozen-plane change IS needed, and it is one composition line.** The only
live carrier of the parsed block is the occupied single-slot `ExchangeSink`;
the zero-edit alternatives fail:

- SSE `broadcast`/`emit_exchange`: would require widening `ResStats` or the
  exchange payload to carry block names — a deeper frozen change.
- Capture RPC: lifecycle-only; adding a method changes frozen `capture_rpc.py`.
- `tm_events` NOTIFY: emitted only by `SessionWriter` from transcript commits.
- Watching tier-1 exchange files from the gateway: zero frozen edits but couples
  the product plane to the frozen disk layout with polling — rejected.

**Exact symbol:** the `set_exchange_sink(_make_exchange_cursor_sink(...))`
registration in `api/src/transport_matters/addon_runtime.py`
(`create_session_capture_runtime`). Compose a second observer there (or make
the sink multi-subscriber). The wire hooks, recorder, IR, SessionWriter,
pgContracts, and run_lifecycle all stay untouched. The observer itself is a
NEW api-plane module, not an edit to existing frozen code. **Stuart must bless:
one edited line in `addon_runtime.py` plus one new module in the api plane.**

## Quality Map

1. `response_stream.py` tee accumulates SSE chunks into an unbounded
   `bytearray` per flow — needs a ceiling (frozen; flag only).
2. `persist_http_exchange` vs `_finalize_http_provisional_exchange`
   (`exchange_recorder.py`): near-identical extract/persist/emit blocks with two
   drift-prone `emit_exchange` call sites — a shared helper would fix; frozen,
   flag only.
3. `ExchangeSink` is typed as a general observer but has one implementation
   using ~10% of its payload — over-general today, convenient for exactly this
   extension; making it multi-subscriber legitimizes the abstraction.
4. `ActivityRecord` (`ports.ts`) is a widening optional-field bag; a wire
   record kind should not add more optionals — keep the wire payload minimal
   (toolCallId) and prefer a discriminated shape if it grows.
5. `advancedWatermark`/`ActivityRecordCursor` are record-stream-specific: the
   wire stream must keep its own cursor and never touch the Postgres watermark.
6. `isNewEvent`'s session-rotation shortcut keys off `event.sessionId` in the
   record-stream branch — add the `"wire"` stream to `eventStream()` before any
   wire event carries `sessionId`, so it can never fall into record dedupe.
7. `channel.py` is deployment-channel config, not event fanout — naming trap
   for future readers chasing broadcast surfaces.

## Plan

**Frozen-plane change: NEEDED — `addon_runtime.py` `set_exchange_sink(...)`
registration (compose a second observer); one line plus one new api module.
Everything else is product plane.**

Proposed Slice-1.5 (wire → question-asked → needs-you-asked, live):

1. **api plane (needs Stuart's blessing):** new module (e.g.
   `wire_activity_observer.py`) implementing an `ExchangeSink`-shaped callable:
   inspect `artifacts.response_ir.content` for `ToolUseBlock` with name in
   {`AskUserQuestion`, `request_user_input`}; on hit, `pg_notify` on
   `tm_events` with a new self-contained payload
   `{type: "wire_records", run_id, records: [{kind: "question-asked",
   toolCallId, ordinal, ts}]}` (ordinal = per-run process-monotonic counter).
   Compose it with `_make_exchange_cursor_sink` at the registration site.
   Note: this is deliberately NOTIFY-as-data, diverging from the
   NOTIFY-as-trigger convention, because no store row exists — flagged below.
2. **@tm/activity domain:** extend `RunActivityEventStream` with `"wire"` +
   cursor in `initialSeqCursors()`; new event type routed to `"wire"` by
   `eventStream()`; reuse `foldQuestionAsked` (the machine's
   `record.question_asked` transitions gain a wire twin or the event maps to
   the same fold — implementer's choice, graph test locks it).
3. **@tm/activity adapters/service:** extend `parseTmEventsPayload`
   (`tmEvents.ts`) with the `wire_records` payload; new public
   `ActivityIngestion.applyWireRecords(runId, records)` that materializes the
   run's actor and sends the wire event (does NOT touch the Postgres
   watermark).
4. **Coexistence/dedupe (designed, needs no new mechanism):** independent
   cursors mean the later transcript-fed `question-asked` (journaled when the
   user answers) re-applies as the existing harmless self-transition on
   `needs-you-asked`, immediately followed by the answer's `tool_result` →
   `reasoning`. No double-fire, no shadowing in either direction.
5. **Red-first tests:** wire payload → projection `needs-you-asked` +
   `needs_you {kind:"asked"}` live (fails today); then replay the journaled
   transcript rows (question-asked + tool_result) → `reasoning`, asserting no
   conflict; ordinal replay idempotency on the wire cursor; strip-level "Needs
   you" for a wire-fed ask.
6. **Gates:** `just check`, `just test` (full suite; api suite runs since the
   api plane gains a module).

Decisions for Stuart:
- **(a) Bless the frozen touch** — compose a second observer at
  `addon_runtime.py`'s `set_exchange_sink` registration (recommended) — or
  reject and accept no live `asked` until the PTY/hooks slice.
- **(b) Transport** — NOTIFY-as-data on `tm_events` (recommended: smallest,
  reuses the one listener; breaks the NOTIFY-as-trigger convention for this
  narrow payload) vs a new wire-events table (keeps the convention, adds
  schema + reader) vs HTTP push to the gateway (new surface).
- **(c) Durability** — wire-fed `asked` is process/NOTIFY-resident and lost on
  gateway restart mid-question (the transcript still cannot supply it until
  answered). Recommend accepting: runs themselves are process-resident.
