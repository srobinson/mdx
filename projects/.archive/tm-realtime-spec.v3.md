---
title: TM realtime agent-state design spec — live wire-driven states
type: design-spec
tags: [transport-matters, activity, realtime, wire, sse, live-status]
summary: Live Thinking/Tools/Responding driven mid-turn by the proxy tee via an ephemeral run_live_status overlay, plus empty-at-spawn; five sequenced slices. Amended after MoE review rounds 1 and 2.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-10
updated: 2026-07-10
---

# Transport Matters realtime agent-state redesign

Base commit: `main` `ef52af6`. Bound to the two scout reuse maps:
`~/.mdx/projects/tm-realtime-scout-python-tee.md` (capture plane) and
`~/.mdx/projects/tm-realtime-scout-ts-ingestion.md` (product plane).
Amended per the MoE review rounds (`tm-realtime-review-codex.md`,
`tm-realtime-review-grok.md`, `tm-realtime-review-claude.md`, plus the delta
re-verify); prior text at `.archive/tm-realtime-spec.v1.md` and
`.archive/tm-realtime-spec.v2.md`. All citations are file + symbol. No line
numbers.

## 1. Overview

The product promise is a live view of each agent's work transitioning in real
time: Thinking → Tools → Responding. The wire is the only truly live plane:
`install_response_tee` (`api/src/transport_matters/response_stream.py`)
receives every upstream chunk while the provider is still responding. PR-3
(#260) instead drove wire states from the finalize store
(`readWireSnapshotForRun` in
`packages/activity/src/adapters/postgresRecords.ts` requires a committed
response), which shares the transcript's timing and is not live.

Everything downstream of the machine is already live and unchanged:
`runActivityMachine` → `WorkspaceActivityProjections` → SSE
`GET /v1/workspaces/:id/activity/stream` (`createActivityRouter` in
`packages/activity/src/server/activityRouter.ts`) →
`useWorkspaceActivityStream` → `useRunVitalsStore` → `RunVitalsStrip`. Zero
frontend change in this design.

The one missing link is a live per-block fact crossing from the proxy tee to
Activity. This spec adds it as an **ephemeral overlay on the untouched
lossless finalize plane**:

1. **Capture plane (Python, blessed seam):** a stateful incremental SSE
   reframer classifies each response block transition off the synchronous
   `capture_chunk` path, best-effort and failure-isolated, into a
   provider-neutral live fact. Subagent tracks never emit (§4.3).
2. **Plane crossing (decision B, locked):** a single-row-per-run
   `run_live_status` upsert followed by the existing `tm_events` doorbell
   NOTIFY. The NOTIFY carries no applied data; the store stays the source of
   truth; lossless under listener drops (invariant stated in the
   `ActivityIngestion` class header,
   `packages/activity/src/service/activityIngestion.ts`), with the reconnect
   relist extension in §3.3.
3. **Product plane (TS):** the reconcile pass reads the live row alongside
   the finalize snapshot, selects at most one candidate — **finalize is
   authoritative by construction, never by clock**: the finalize commit
   spends the overlay in its own transaction (§5.3) — admits it under an
   extended admission contract with an admit-once staleness anchor (§5.2),
   and mints the
   existing `record.reasoning` / `record.tool_use` / `record.generating`
   events tagged `stream: "wire"` via `wireCandidateEvent`. Block stop maps
   to the existing `wire.retracted`. Non-pollution requires **two small,
   explicitly owned machine-layer changes** (§5.4): PR-3's wire plane never
   minted reasoning/generating, so those two folds and two state nodes are
   exactly the unwired ones.
4. **Empty-at-spawn (orthogonal):** `RUNS_BY_WORKSPACE_SQL` admits
   lifecycle-only runs via LEFT JOIN, with owner preserved by a new `owner`
   column on `run_lifecycle_event` (resolution in §6).

Scope: live active-work states plus empty-at-spawn. Out: asked /
needs_you{asked} (already durable), gated states (wire-impossible, later
slices).

## 2. Provider-neutral live-fact vocabulary

The classifier emits **facts**; the store holds **current state** (one row per
run, last write wins).

```
LiveStatusFact:
  run_id: str
  seq: int                    # per-run monotonic, emitter-process-local
  kind: "reasoning" | "running_tool" | "generating" | None
                              # None = no active block (block stop / terminal / abort)
  tool_call_id: str | None    # provider tool id when kind = running_tool
  ts: datetime (UTC)          # emitter clock at classification; diagnostics only,
                              # never a freshness authority (§5.3)
  provider_event: str         # diagnostics only: the provider event name
```

`phase: start` is a fact with a non-null `kind`; `phase: stop`, turn
terminal, and flow abort (§4.3) are facts with `kind = None`. Collapsing
these to one row shape is safe because the machine's reaction to all of them
is the same retraction path (§5.3), and the finalize plane, not the live
overlay, owns end-of-turn meaning.

### 2.1 Anthropic mapping

Event rules mirrored from `AnthropicAdapter._inbound_response_sse`
(`api/src/transport_matters/adapters/anthropic.py`); the classifier retains a
per-flow map of block index → kind so `content_block_stop` can be attributed:

| Provider event | Fact |
|---|---|
| `content_block_start`, `content_block.type == "thinking"` | start `reasoning` |
| `content_block_start`, `content_block.type == "redacted_thinking"` | start `reasoning` (redacted blocks stream none of the mapped delta types, so without this row the heal rule never fires and a turn opening redacted shows nothing) |
| `content_block_start`, `content_block.type == "tool_use"` | start `running_tool`, `tool_call_id = content_block.id` |
| `content_block_start`, `content_block.type == "text"` | start `generating` |
| `content_block_delta` (`thinking_delta` / `input_json_delta` / `text_delta`) | affirm current kind; emit only if the tracked kind differs (heals a missed start) |
| `content_block_stop` | stop (`kind = None`) |
| `message_delta` with `delta.stop_reason`, `message_stop` | terminal (`kind = None`) |

`_parse_tool_use_block` and the other complete-block IR helpers are **not**
used here: the scout pins that they require complete streamed input; live
classification uses the event types only.

### 2.2 Codex mapping

Reuses the incremental vocabulary in
`api/src/transport_matters/codex/protocol.py` (`codex_payload_event_type`,
`codex_terminal_status`) and the open-state discipline of
`derive_codex_turn_incremental`
(`api/src/transport_matters/codex/derivation_engine.py`). Codex interleaves
multiple open items, so the classifier is **not single-slot**: it tracks the
open-item set (item id → kind, mirroring the derivation engine's open
tool/text state) and reports as current the kind of the most recently
started still-open item.

| Provider event | Fact |
|---|---|
| `response.output_item.added`, item type `reasoning` | open item; start/affirm `reasoning` |
| `response.output_item.added`, item type `function_call` / `custom_tool_call` / `tool_search_call` | open item; start/affirm `running_tool`, `tool_call_id` = call id when present |
| `response.output_text.delta` | open text; start/affirm `generating` |
| `response.output_item.done` | close that item; emit stop (`kind = None`) **only when the open set empties**, otherwise affirm the newest still-open kind |
| `response.completed` / `response.failed` | terminal (`kind = None`), clears the open set |

Two Codex transports, one classifier:
- **WebSocket** (primary): already message-framed. Hook in
  `handle_codex_websocket_message`
  (`api/src/transport_matters/addon_handlers.py`) feeds payload dicts to the
  classifier — **server frames only** (the handler observes both directions
  via `message.from_client`; the tap pins the server direction and a test
  asserts client frames classify nothing).
- **HTTP fallback**: SSE bytes through the same tee as Anthropic; the
  reframer (§4.1) frames, the classifier consumes.

## 3. The `run_live_status` row, migration, and doorbell

### 3.1 Migration 0009 (alembic, follows `0008_wire_store.py`)

```sql
CREATE TABLE run_live_status (
    run_id text PRIMARY KEY,
    seq bigint NOT NULL,
    kind text CHECK (kind IN ('reasoning', 'running_tool', 'generating')),
    -- NULL kind = no active block
    tool_call_id text,
    provider_event text,
    ts timestamptz NOT NULL,
    workspace_slug text NOT NULL,
    workspace_hash text NOT NULL,
    owner text NOT NULL DEFAULT 'local',
    updated_at timestamptz NOT NULL DEFAULT now()
)
```

One row per run; plain `ON CONFLICT (run_id) DO UPDATE` last-write-wins,
`SET updated_at = now()` for bookkeeping. **No timestamp participates in
live-vs-finalize adjudication** (§5.3): the two planes commit in independent
transactions with separate `now()` clocks (`now()` is transaction-start
time), so cross-writer ordering by timestamp is unsound — supersession is
transactional instead (§3.2). No seq guard in SQL: ordering is enforced by
the emitter (one proxy process per run, per-run latest-wins slot with a
single in-flight write, §4.3), and residual staleness is absorbed by the
admission contract (§5.2/§5.3). Rows are never
GC-critical: after `run-exited` the machine's `exited` guard (early return
in the wire resolution step, `packages/activity/src/service/activityIngestion.ts`)
makes the row inert.

Workspace and owner columns exist so the doorbell payload can carry routing
identity, symmetric with `_wire_exchange_notify_payload`
(`api/src/transport_matters/session/writer.py`).

### 3.2 Writer methods: live upsert, and the finalize spend

`SessionWriter.submit_run_live_status(row)` in
`api/src/transport_matters/session/writer.py`, mirroring
`_commit_run_lifecycle_event` / `submit_wire_exchange`: commit the upsert,
then `pg_notify` on the same connection so the NOTIFY fires on commit.
Statement lives in `api/src/transport_matters/session/dao_statements.py`,
row model beside `RunLifecycleEventRow` in
`api/src/transport_matters/session/models.py`.

**Finalize spends the overlay in the same transaction (required):**
`SessionWriter.submit_wire_exchange`'s commit closure (the one that runs
`write_wire_exchange` + the wire NOTIFY on one connection) additionally
executes `UPDATE run_live_status SET kind = NULL, updated_at = now() WHERE
run_id = $1` — **only when `write.track_role` is not the subagent role**
(mirroring the `WIRE_SNAPSHOT_BY_RUN_SQL` exclusion; a subagent finalize
must never null the parent's active live status mid-turn). After the
finalize transaction commits, the overlay is provably spent: no clock
comparison, no race window, no stale shadow. A no-row `UPDATE` is a no-op,
and no separate `run_live_status` NOTIFY fires for the spend — the wire
NOTIFY in the same transaction already marks the run reconcile-needed. Any
non-null live fact committed after the spend is a NEW assert (new
`assertId` from a new stream) and is correctly admitted. Emitter-side
ordering makes post-spend leftovers of the finalized turn implausible by
construction: block facts precede the in-stream terminal, the latest-wins
slot holds the terminal `kind = NULL` by stream end, and the finalize path
(full-body parse + Tier-1 persist + sink) schedules strictly after stream
end; the residual writer-death window is capped at one flap by admit-once
(§5.2).

### 3.3 Doorbell wiring (invariant preserved) and the reconnect relist

New payload flavor through the existing `_typed_notify_payload`
(`api/src/transport_matters/session/writer.py`):

```json
{"type": "run_live_status", "run_id": "...", "workspace_slug": "...",
 "workspace_hash": "...", "owner": "local"}
```

Identity only — **no kind, no ts, no applied data**. The listener treats it
exactly like the three existing flavors: `parseTmEventsPayload`
(`packages/activity/src/adapters/tmEvents.ts`) gains a fourth branch
returning a `RunLiveStatusPayload` (new member of `TmEventsPayload` in
`packages/activity/src/ports.ts`, type constant beside
`RUN_LIFECYCLE_PAYLOAD_TYPE` in
`packages/activity/src/server/pgContracts.ts`), which routes to
"run X needs reconcile" and nothing else.

**Reconnect relist (required, closes a pre-existing lossless hole this
design now depends on):** `onConnected` today only runs
`reconcileMaterialized` (`ActivityIngestion` handlers in
`packages/activity/src/service/activityIngestion.ts`), and
`WorkspaceActivityProjections.refreshSubscribedWorkspaces`
(`packages/activity/src/projections/workspaceActivity.ts`) re-lists only on
a decoded payload. A run whose lifecycle and live doorbells both drop while
the listener is disconnected has durable rows but no actor, and reconnect
never discovers it. Amendment: on listener reconnect, the projections layer
**re-lists every subscribed workspace from the store** (the same
`listWorkspaceActivity` read the browser snapshot uses), materializing any
run present in rows but absent from actors. Red test (slice 4): a run whose
`run_live_status` NOTIFY was dropped pre-materialization appears after
reconnect; (slice 5) a lifecycle-only run whose `run_lifecycle_event` NOTIFY
was dropped appears as `starting` after reconnect.

## 4. Python: reframer and the blessed emit seam

### 4.1 Incremental SSE reframer (pure, new module)

`iter_sse_data_objects` (`api/src/transport_matters/sse.py`) is stateless and
whole-buffer; the scout proves passing tee chunks directly is unsafe (a
`data:` line can span chunks; repassing the cumulative buffer redelivers).
New sibling class in `api/src/transport_matters/sse.py` (or a colocated
`sse_incremental.py` if size demands):

```
class IncrementalSseFrames:
    def feed(self, chunk: bytes) -> Iterator[dict]: ...
```

Retains only the unterminated tail across calls, **kept as bytes** (or via an
incremental decoder): a per-chunk string decode with a string tail corrupts
JSON when a chunk boundary splits a multi-byte UTF-8 sequence
(`iter_sse_data_objects` decodes whole-buffer with `errors="replace"` and
never faces this). Applies the same record rules as `iter_sse_data_objects`
(scan `data:` lines, skip empty and `[DONE]`, skip malformed JSON without
losing subsequent records). Tail is capped (1 MiB); on overflow the framing
state drops and resyncs at the next record boundary — the live plane is
best-effort by contract.

**Proof tests (required, colocated per api/CLAUDE.md):**
- every-byte-boundary split of a canned multi-event SSE body yields the
  identical payload sequence as the whole-buffer parse, **with non-ASCII
  payload content so multi-byte splits fail red on a string-tail
  implementation**;
- multiple events in one chunk;
- `[DONE]` skipped;
- a malformed JSON `data:` line skipped, subsequent events intact;
- trailing partial retained and completed by the next chunk;
- overflow resync.

### 4.2 Classifier (pure)

New module `api/src/transport_matters/live_status.py`: `LiveStatusFact`,
`AnthropicLiveClassifier`, `CodexLiveClassifier`. Both consume payload dicts
and yield facts per §2. Codex reuses `codex_payload_event_type` and
`codex_terminal_status` (`api/src/transport_matters/codex/protocol.py`) and
tracks the open-item set per §2.2 rather than adding a third payload fold.
Anthropic mirrors the branch rules of `_inbound_response_sse` (the method
itself cannot resume across chunks; the scout confirms all its state is
local, so the rules are re-expressed incrementally, not the method reused).
Pure computation stays sync per api/CLAUDE.md.

**Batch coalescing:** one `feed()` call can frame several events (a stop and
the next start often share a chunk). The classifier reports only the **final
tracked state per feed batch**, and the observer defers a bare stop fact one
slot cycle (§4.3) so an immediately following start supersedes it. This
kills inter-block retraction flicker at the source: no
retract-then-reassert pair ever reaches the store for a stop→start gap that
fits one chunk or one in-flight window.

### 4.3 Emit seam (composition level, storage never imports session)

New `LiveStatusObserver` in
`api/src/transport_matters/live_status_observer.py`, mirroring
`WireStoreObserver` (`api/src/transport_matters/wire_store_observer.py`)
exactly in posture: constructed in `_start_session_capture`
(`api/src/transport_matters/addon_runtime.py`) with the existing
`SessionWriter`, writer loop, and `binding_for_run_id`; schedules
`SessionWriter.submit_run_live_status` via `run_coroutine_threadsafe`. This
keeps `storage` free of `session` imports — the emitter is injected at
runtime like the existing sinks, honoring the Import DAG in `api/CLAUDE.md`.

Backpressure: per-run **latest-wins slot** with one in-flight write (the
`WireStoreObserver` single-write-slot idiom, adapted from queue to
supersede): while a write is in flight, newer facts overwrite the slot; on
completion the slot, if changed, is written. A bare stop fact (`kind =
None` from `content_block_stop` / open-set-empty) is **deferred one slot
cycle** so an immediately following start supersedes it (§4.2); terminal
and abort facts are never deferred. Live status is last-write-wins, so
dropping superseded intermediate facts is correct and bounds both memory
and pool usage (one connection, matching the existing cap noted in
`addon_runtime.py`).

**Subagent exclusion (required):** the request path classifies
`track_assignment.track_role` before response headers
(`handle_http_request` in `api/src/transport_matters/addon_handlers.py`
stores it on `RequestFlowState` in
`api/src/transport_matters/flow_state.py`), and the finalize plane
deliberately excludes `track_role = 'subagent'` from the Activity snapshot
(`WIRE_SNAPSHOT_BY_RUN_SQL`, exercised by
`packages/activity/src/pgWireIntegration.test.ts` T12). The live plane
mirrors that contract at the emit source: the per-flow tap is **not
installed** when the flow's track assignment is subagent, so a same-run
subagent response can never overwrite the parent's single
`run_live_status` row. Red test in slice 3.

**Identity-incomplete skip (required):** the upsert's workspace/owner
columns are NOT NULL, and a partial binding can yield null slugs (the
`WireStoreObserver._resolve_run` precedent). The observer skips scheduling
when identity is incomplete — same best-effort posture as the wire notify —
so no constraint violation can throw into the writer path.

**Abort/error terminal (required):** in-stream terminals (§2.1/§2.2) never
arrive on a killed or errored flow (user Esc, network drop, upstream 5xx
mid-stream), and `handle_response` may never run — without this, the live
row freezes on its last non-null kind for up to the 10-minute stall
timeout. The addon's existing `error` hook
(`TransportMattersAddon.error` in `api/src/transport_matters/addon.py`,
which already routes to `delete_http_provisional_exchange`) and the
per-flow tap teardown emit a best-effort `kind = None` fact for the flow's
run. Red test in slice 3.

Tee hook: `install_response_tee`
(`api/src/transport_matters/response_stream.py`) gains an optional
`on_chunk: Callable[[bytes], None] | None = None`. Inside `capture_chunk`:
append to the buffer first, then invoke the hook inside `try/except
Exception` (log once per flow, never re-raise), then return the exact chunk
object unchanged. `handle_response_headers`
(`api/src/transport_matters/addon_handlers.py`) obtains a per-flow tap from
the runtime observer (reframer + classifier + run identity from the flow's
binding, the same `binding.run_id` resolution `handle_response` uses) and
passes it. `_should_stream_response` selection is unchanged. Codex WS taps
in `handle_codex_websocket_message`, server frames only (§2.2).

The hook does no I/O on the caller thread: it feeds bytes to the reframer,
classifies, and on a **transition only** (tracked kind changes or turn
terminal) updates the slot and schedules. Delta storms cause zero writes.

### 4.4 Frozen-plane red tests (must pass before the seam is blessed)

1. **Exact byte pass-through:** extend
   `test_response_tee_accumulates_and_passes_chunks_through`
   (`api/src/transport_matters/test_response_stream.py`): with a hook
   installed, returned chunk objects are identical and the buffer matches.
2. **No exception leakage:** a hook that raises on every chunk leaves
   forwarding, accumulation, and `restore_streamed_response` behavior
   untouched.
3. **Non-blocking:** the hook performs no awaits/IO on the capture thread;
   test with a stub loop asserting only `run_coroutine_threadsafe`
   scheduling occurs.
4. **Unchanged Tier-1 artifacts:**
   `test_streamed_provisional_finalize_matches_buffered_response`
   (`api/src/transport_matters/test_response_stream_capture.py`) stays
   byte-identical with the live emit active.
5. **`ExchangeSink` untouched:** no live emissions cross
   `register_exchange_sink`
   (`api/src/transport_matters/storage/exchange_sink.py`); its documented
   final-only semantics are preserved by not using it (locked decision).
6. **Import boundary:** `test_private_import_boundary` and the Import DAG
   hold; the observer is composition-level like `wire_store_observer.py`.
7. **Subagent flows emit nothing:** a flow whose `track_assignment` is
   subagent installs no tap and writes no `run_live_status` row.
8. **Abort emits terminal:** the `error` hook / tap teardown upserts
   `kind = None` for a mid-stream-killed flow, best-effort and
   failure-isolated.
9. **Identity-incomplete skip:** a partial binding (null workspace slugs)
   schedules no write and raises nothing.

## 5. TS: mid-turn admission, block stop, and the owned machine changes

### 5.1 Store read

`ActivityStore` (`packages/activity/src/service/activityIngestion.ts`) gains
a fourth read method `readLiveStatusForRun(runId)`; implemented by
`PostgresActivityReader` with `LIVE_STATUS_BY_RUN_SQL` in
`packages/activity/src/adapters/postgresRecords.ts`, columns pinned beside
the existing contracts in `packages/activity/src/server/pgContracts.ts`.
No timestamp columns are surfaced for adjudication — supersession is
transactional (§3.2), so the DTO carries only `run_id`, `seq`, `kind`,
`tool_call_id`. The port is test-doubled everywhere already
(`activityIngestion.test.ts`, `wireIngestion.test.ts`); doubles return
`null` until slice 4's tests.

### 5.2 Candidate vocabulary and admission

`WireCandidate` (`packages/activity/src/domain/wireCandidate.ts`) gains
three live variants:

```ts
| { kind: "live-reasoning";    assertId: string; ts: string }
| { kind: "live-running-tool"; assertId: string; ts: string; toolCallId: string | null }
| { kind: "live-generating";   assertId: string; ts: string }
```

`assertId = "live:{runId}:{seq}"`. **Typing is made precise, not left
"unchanged":** a new domain helper `candidateAssertKey(candidate): string`
returns `exchangeId` for the four finalize kinds and `assertId` for the
three live kinds; `wireAssertSuppressedBySilenceStall`, the
`wireCandidateEvent` id/`wireExchangeId` fields, and the
`wireAssertedExchangeId` stamp all key on `candidateAssertKey`. A new seq
from the emitter is a new assert key; the identical row re-read by a later
pass carries the same key.

`wireCandidateAdmitted` extends:

- **Admit-once staleness anchor (all three live kinds, required):**
  `reconcileWireSnapshot` re-derives and re-sends on every pass and
  `isNewEvent` is unconditionally true for the wire stream, so live kinds
  need a causal anchor the finalize kinds get from tool-id resolution and
  cold-start. Each live `assertId` **admits at most once**. The consumed
  key is tracked on the service's per-run `RunIngestionEntry`
  (`lastLiveAssertId`, beside `watermark` in `activityIngestion.ts`), not
  in machine context: it must survive record-stream supersession (record
  events clear `wireAssertedExchangeId` by design, and without this memory
  a stale row would re-admit after every record pass and flip status back
  — the sticky attention deadlock). Entry state is process-local; on
  gateway restart a stale row can admit once more, then never again —
  bounded single flap, consistent with the ephemeral-overlay posture.
  Re-asserting the same live status legitimately requires a new fact (new
  seq) from the emitter.
- `live-running-tool` with `toolCallId`: additionally refuse iff
  `context.resolvedToolCallIds.has(toolCallId)` — the identical anchor the
  finalize `running-tools` arm uses; a transcript that already resolved the
  call is strictly fresher. With `toolCallId === null`: admit (subject to
  admit-once). This deliberately differs from the finalize arm's refusal of
  id-less candidates: a finalize assert is a standing end-of-turn claim,
  while a live assert is superseded within seconds by the next fact, the
  abort terminal (§4.3), or the finalize snapshot (§5.3), so an unanchored
  admit is recoverable by construction.
- `live-reasoning` / `live-generating`: admit subject to admit-once and the
  `exited` guard. They are **not** cold-start-gated like `anomaly` / `idle`:
  mid-turn the wire is strictly fresher than the journaled transcript — the
  temporal collapse this design exists to fix.

`wireAssertSuppressedBySilenceStall` applies over `candidateAssertKey`: a
fresh live fact (new seq) clears a silence stall — bytes on the wire are the
definition of not-silent — while the same key re-read never flaps it.

### 5.3 One resolution step per pass; finalize authoritative by construction

`reconcileWireSnapshot` (`packages/activity/src/service/activityIngestion.ts`)
becomes the wire-plane resolution step, same position in `reconcile` (after
records, before `run-exited`):

1. Early return on `context.status === "exited"` (unchanged).
2. Read both `readWireSnapshotForRun` and `readLiveStatusForRun`.
3. Derive at most **one** candidate, preserving the existing "at most one
   candidate per pass" property. **No timestamp adjudicates between the
   planes.** The live row is a live candidate iff `kind` is non-null —
   which, by the §3.2 transactional spend, can only be true when no
   finalize row for the current turn has committed: the finalize
   transaction nulls the overlay atomically with the `wire_exchange`
   insert, so a non-null kind is by construction fresher than every
   committed finalize. Clock rules are ruled out entirely: `wire_exchange.ts`
   is minted at provisional **request** time
   (`persist_http_provisional_exchange` →
   `_finalize_http_provisional_exchange` in
   `api/src/transport_matters/exchange_recorder.py` preserve `IndexEntry.ts`
   into `WireExchangeWrite.ts`), and even store-side stamps
   (`updated_at` vs `created_at`) are `now()` values from two independent
   transactions — transaction-start times with no commit-order guarantee —
   so "newer by timestamp across independent writers" is unsound. When the
   live row yields no candidate, the finalize candidate via
   `wireCandidateFromSnapshot`
   (`packages/activity/src/service/runActivityEvents.ts`) proceeds
   unchanged; the live mapping is a sibling `liveCandidateFromRow`.
4. **Same-assert-standing no-op:** if `candidateAssertKey(candidate) ===
   context.wireAssertedExchangeId`, return — the assertion stands; neither
   re-assert (no flap, no `reenter` stall-timer reset) nor retract. This is
   the mechanism behind the "re-read row neither re-asserts nor retracts"
   property, previously asserted without one.
5. Suppress / admit / refuse exactly as §5.2:
   `wireAssertSuppressedBySilenceStall`, extended `wireCandidateAdmitted`,
   `wireCandidateEvent`.
6. Trailing retract as today: when a wire-owned status has no admissible
   candidate, send `wireRetractedEvent`.

**Block stop → `wire.retracted`:** a stop, terminal, or abort fact upserts
`kind = null`; step 3 yields no live candidate; if the finalize snapshot
also yields none (mid-turn: it cannot, its response has not committed) the
trailing branch sends `wireRetractedEvent`
(`packages/activity/src/domain/wireCandidate.ts`) and
`statusAfterWireRetraction` recomputes from record-owned fields under the
per-state `wireRetractionRestores` guards. This path **requires the §5.4
machine changes** — it is dead on `reasoning`/`generating` today.

**Stop/terminal vs finalize ordering (red test, slice 4):** with the
latest-wins slot, reconcile can observe a pre-stop live row while the
in-stream `kind = null` write is still in flight when the finalize NOTIFY
lands, or the reverse. Both orders must converge to the same machine state:
the finalize candidate wins either way — its transaction spent the overlay
in one order, and the live candidate is already null in the other. A named
test drives both interleavings, plus the spend itself: a finalize committed
while the live row still holds a non-null kind leaves the row nulled in the
same commit, and a live delta arriving after finalize is treated as a fresh
assert (new `assertId`), never a survivor.

### 5.4 Owned machine-layer changes and event minting

**PR-3's wire plane never minted reasoning or generating, and the machine
shows it.** Verified against source: the `eventStream(event) === "wire"`
non-pollution branch exists in exactly `foldToolUse`, `foldTurnIdle`,
`foldQuestionAsked`, and `foldTranscriptError`
(`packages/activity/src/domain/runActivityContext.ts`); `foldReasoning` and
`foldGenerating` call `markApplied` directly, writing `lastActiveStatus`
and never stamping `wireAssertedExchangeId`. `WIRE_RETRACTED_TRANSITIONS`
(`packages/activity/src/domain/runActivityMachine.ts`) is registered on
exactly the four PR-3 wire-assertable states (`running-tools`,
`needs-you-asked`, `idle`, `stalled`); the `reasoning` and `generating`
nodes have no `wire.retracted` transition, and xstate silently drops
unhandled events. This spec therefore **owns three machine-layer changes**
(slice 2 — they are pure domain changes, landable dark because nothing
mints wire-stream reasoning/generating events until slice 4; the v1 claim
of "verbatim reuse, machine states change not at all" was false and is
withdrawn):

1. **Wire branches in `foldReasoning` and `foldGenerating`**, mirroring
   `foldToolUse`: on `stream: "wire"`, route through `foldWireAsserted`
   with the status patch only — never write `lastActiveStatus` or
   `pendingToolCallIds`, stamp `wireAssertedExchangeId` from
   `event.wireExchangeId`. Record-stream behavior is untouched.
2. **`WIRE_RETRACTED_TRANSITIONS` on the `reasoning` and `generating` state
   nodes**, so block stop can retract the two states live work occupies.
   `starting` needs no transition: a wire assert moves the machine **out**
   of `starting` (into the asserted state), so `starting` never holds a
   wire-owned status; the existing `retractionRestoresStarting` path
   restores it as the recompute target.
3. **`WireRetractedEvent` doc comment** updated: the "exactly the
   wire-assertable states" list grows by `reasoning` and `generating`.

`wireCandidateEvent` gains three arms mapping live kinds onto the existing
machine vocabulary: `live-reasoning → record.reasoning`,
`live-running-tool → record.tool_use`, `live-generating →
record.generating`, all with `seq: 0`, `stream: "wire"`, id and
`wireExchangeId` from `candidateAssertKey`. With change 1 in place, the
non-pollution property holds for all three: wire events never advance
`entry.watermark` (`isNewEvent` short-circuits for the wire stream), and a
dropped or stale live fact can never corrupt durable, record-owned machine
state. The finalize plane is untouched: `WIRE_SNAPSHOT_BY_RUN_SQL`
semantics, the wire store write path, and the machine's state set change
not at all (two nodes gain one transition entry; no new states, no new
event types, no new folds).

Projections, SSE router, contract DTOs, and every browser package: zero
change. A mid-turn status change is an ordinary `delta` frame
(`ActivityStreamFrame` in `packages/contract/src/activity/wire.ts`).

### 5.5 Red tests pinning the blockers

Machine-layer reds (land with the §5.4 changes, **slice 2**):

- live-reasoning → stop retracts; live-generating → stop retracts;
  live-tool → stop retracts (dead against the unamended machine).
- wire-stream `record.reasoning` / `record.generating` leave
  `lastActiveStatus` and `pendingToolCallIds` unchanged and stamp
  `wireAssertedExchangeId` (fails against the unamended folds).

Admission/resolution reds (**slice 4**):

- double-assert of the same `assertId` is idempotent (same-assert-standing
  no-op, no `reenter` stall-timer reset); retract restores the pre-live
  record-owned baseline.
- finalize with a still-non-null live row leaves the row nulled in the same
  commit; a live delta after finalize is a fresh assert, never a survivor
  (drives the §3.2 transactional spend; fails against any
  timestamp-adjudication rule).
- subagent finalize does NOT spend the parent's live row (§3.2 track-role
  guard).
- Esc-mid-response (abort terminal per §4.3, plus the lost-terminal case):
  a stale `kind='generating'` row admits at most once and never re-admits
  after records journal the interrupt — no sticky Responding.
- stop/terminal vs finalize order convergence (§5.3, both interleavings).
- reconnect relist materializes a run whose doorbells all dropped (§3.3).

Subagent exclusion is enforced and tested **producer-side only** (slice 3,
§4.3/§4.4): `run_live_status` carries no `track_role` column, so a
consumer-side exclusion test is incoherent — the guarantee is that a
subagent response never writes the parent's row in the first place,
mirroring the emit-source contract `pgWireIntegration.test.ts` T12 pins for
the finalize plane.

## 6. Empty-at-spawn: SQL and the resolved owner semantics

### 6.1 The owner resolution (the locked answer)

Investigated at source. **There is no owner fact anywhere in the capture
plane, and none is derivable from the lease.** Evidence:

- `_CaptureRunFacts` (`api/src/transport_matters/capture_rpc.py`) carries
  `working_dir`, `harness`, `space_id`, `worktree_id` only; and
  `CapturedRunRequest` (`api/src/transport_matters/captured_run_models.py`)
  has no owner field. "Coalesce from lease" is therefore impossible today.
- Owner is a single-tenant forward-compat constant threaded by default at
  every seam: `SessionRow.owner` defaults to `"local"`
  (`api/src/transport_matters/session/models.py`) and the ingest
  constructor never overrides it (`SessionRow(...)` in
  `api/src/transport_matters/session/ingest.py`);
  `WireExchangeWrite.owner` defaults to `"local"`
  (`api/src/transport_matters/session/wire_store.py`) and
  `WireStoreObserver.on_exchange` never sets it; the reader side pins
  `DEFAULT_ACTIVITY_OWNER = "local"`
  (`packages/contract/src/activity/wire.ts`), passed by the browser as
  `?owner=` and read by `ownerFromQuery`
  (`packages/activity/src/server/activityRouter.ts`).

**Locked resolution: add `owner` to the lifecycle row at emit.** Migration
0010 adds `owner text NOT NULL DEFAULT 'local'` to `run_lifecycle_event`
(created in `api/migrations/versions/0007_run_lifecycle_event.py`; the
DEFAULT backfills existing rows). `build_run_lifecycle_event`
(`api/src/transport_matters/run_lifecycle.py`) and `RunLifecycleEventRow`
(`api/src/transport_matters/session/models.py`) gain
`owner: str = "local"`, mirroring `SessionRow.owner` exactly, so the value
originates at the same emit sites that already build the row
(`CaptureLeaseRegistry._emit_lifecycle` in
`api/src/transport_matters/capture_rpc.py` and the CLI-path emitter in
`addon_runtime.py`). `_run_lifecycle_notify_payload`
(`api/src/transport_matters/session/writer.py`) adds `owner` to the
payload; `runLifecyclePayload` in
`packages/activity/src/adapters/tmEvents.ts` already parses owner as
optional, so the decode is forward-compatible.

Why this over the alternatives: the capture RPC is the only actor that knows
the run exists before any session row, so the lifecycle row is the only
place a pre-session owner fact can live; it keeps the tenant constant out of
hand-written SQL; and it matches the established pattern — every other
discovery-gating surface (`session`, wire NOTIFY payloads) carries owner
with the same default. When owner becomes a real input, it threads through
`CapturedRunRequest → _CaptureRunFacts → build_run_lifecycle_event` without
schema change.

### 6.2 The SQL change

`RUNS_BY_WORKSPACE_SQL` (`packages/activity/src/adapters/postgresRecords.ts`):

- `JOIN session` → `LEFT JOIN session` (same ON clause: run_id +
  workspace_slug + workspace_hash).
- Owner predicate in `WHERE` becomes
  `COALESCE(s.owner, l.owner) = $3` — session owner is authoritative once a
  session exists (it gates every other read surface); the lifecycle owner
  covers the session-less window. A plain join-keyword flip without this is
  insufficient: `s.owner = $3` rejects NULL rows, as the scout pins.
- `PRIMARY_SESSION_FILTER` stays in `WHERE` unchanged: for an unmatched LEFT
  JOIN row every `s.*` is NULL, the `NOT EXISTS` subquery matches nothing,
  and the filter is vacuously true — lifecycle-only rows survive it.
- Aggregation is per `l.run_id` and all selected columns are lifecycle-side,
  so the GROUP BY is untouched.

Result: a freshly spawned, never-prompted run (a `run-started` row from
`CaptureLeaseRegistry._emit_lifecycle`, no session row — the ordering pinned
by `TranscriptTailer._poll_cursor` submitting only on complete records
before `AsyncSessionDao.upsert_session` runs) materializes an actor whose
machine initial state is `starting` (`createMachine({ initial: "starting" })`
in `packages/activity/src/domain/runActivityMachine.ts`), and
`STATUS_LABELS` in
`www/packages/canvas/src/workbench/chrome/RunVitalsStrip.tsx` already
renders it. Required tests: a lifecycle-only run appears in
`listWorkspaceActivity` as `starting`, remains owner-scoped (wrong owner
sees nothing), an existing-session run's behavior is unchanged, and the
§3.3 reconnect relist surfaces a lifecycle-only run whose NOTIFY dropped.

## 7. PR slice plan

Each slice lands green on its own gate, and the feature turns on only at
slice 4 — but the slices are **sequenced, not order-free**. The dependency
DAG: slice 1 (dark store) → slice 2 (pure machinery, both planes) →
slice 3 (producer emit, needs 1's writer + 2's reframer/classifiers) →
slice 4 (consumer admission + reconnect relist, needs 1's flavor, 2's
machine changes, 3's rows and finalize spend) → slice 5 (empty-at-spawn,
**depends on slice 4's reconnect relist** for its dropped-NOTIFY `starting`
guarantee).

| # | Slice | Plane | Content | Gates (verbatim) |
|---|---|---|---|---|
| 1 | Dark store + doorbell | Python | Migration 0009 `run_live_status`; row model; DAO upsert; `SessionWriter.submit_run_live_status` + `run_live_status` NOTIFY flavor; the §3.2 finalize spend inside `submit_wire_exchange` (track-role-guarded) + its writer tests. No producer, no consumer. | `cd api && just check && just test` |
| 2 | Pure machinery, both planes (dark) | Python + TS | `IncrementalSseFrames` reframer (byte tail) + §4.1 proof suite incl. multi-byte splits; `live_status.py` classifiers (Anthropic incl. `redacted_thinking`; Codex open-item set) + §2 mapping tests incl. one-item-done-while-another-open emits no false stop; batch coalescing. §5.4 machine changes (fold wire branches, `WIRE_RETRACTED_TRANSITIONS` on reasoning/generating, doc comment) + §5.5 machine-layer reds — dark: nothing mints these events yet. No wiring. | `cd api && just check && just test` and `pnpm --filter @tm/activity test` and `pnpm --filter @tm/activity typecheck` |
| 3 | Blessed emit seam | Python | `install_response_tee` `on_chunk` param; `LiveStatusObserver` + `_start_session_capture` wiring; Codex WS tap (server frames only); latest-wins slot + deferred-stop cycle; subagent-track skip (the producer-side enforcement, §5.5); identity-incomplete skip; abort/error terminal emit via the `error` hook; §4.4 red tests 1–9. Producer live, rows written, nothing reads them. | `cd api && just check && just test` |
| 4 | Product consumer (feature ON) | TS | `run_live_status` payload decode; `readLiveStatusForRun` + SQL + pinned columns; live `WireCandidate` variants + `candidateAssertKey`; admit-once entry anchor; §5.3 resolution step (transactional-spend semantics + same-assert no-op); §3.3 reconnect relist; §5.5 admission/resolution red tests, all of them. | `pnpm --filter @tm/activity test` and `pnpm --filter @tm/activity typecheck` and `pnpm --filter @tm/shell test` |
| 5 | Empty-at-spawn | Both | Migration 0010 owner on `run_lifecycle_event`; `build_run_lifecycle_event` / `RunLifecycleEventRow` owner; notify payload owner; `RUNS_BY_WORKSPACE_SQL` LEFT JOIN + COALESCE; lifecycle-only-run `starting` test + owner-scope test + reconnect-relist `starting` test (needs slice 4). | `cd api && just check && just test` and `pnpm --filter @tm/activity test` and `pnpm --filter @tm/activity typecheck` and `pnpm --filter @tm/shell test` |

Risks carried from the scout and review, addressed in-slice: reframer
bounded byte-tail state (slice 2 overflow + multi-byte tests);
`iter_sse_data_objects` never fed raw chunks (slice 2 keeps it untouched
for finalize paths); `ExchangeSink` final-only semantics preserved by
bypassing it entirely (slice 3 red test); the two machine-layer gaps
(slice 2) and the transactional finalize spend (slices 1 and 4) are owned
changes with failing-first reds;
database integration for slices 4–5 requires the configured Postgres test
URL the scout could not exercise.
