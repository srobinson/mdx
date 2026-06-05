---
title: TM realtime agent-state design spec — live wire-driven states
type: design-spec
tags: [transport-matters, activity, realtime, wire, sse, live-status]
summary: Live Thinking/Tools/Responding driven mid-turn by the proxy tee via an ephemeral run_live_status overlay, plus empty-at-spawn; five landable slices.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-10
updated: 2026-07-10
---

# Transport Matters realtime agent-state redesign

Base commit: `main` `ef52af6`. Bound to the two scout reuse maps:
`~/.mdx/projects/tm-realtime-scout-python-tee.md` (capture plane) and
`~/.mdx/projects/tm-realtime-scout-ts-ingestion.md` (product plane). All
citations are file + symbol. No line numbers.

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
   provider-neutral live fact.
2. **Plane crossing (decision B, locked):** a single-row-per-run
   `run_live_status` upsert followed by the existing `tm_events` doorbell
   NOTIFY. The NOTIFY carries no applied data; the store stays the source of
   truth; lossless under listener drops (invariant stated in the
   `ActivityIngestion` class header,
   `packages/activity/src/service/activityIngestion.ts`).
3. **Product plane (TS):** the reconcile pass reads the live row alongside the
   finalize snapshot, admits at most one candidate under an extended
   admission contract, and mints the existing `record.reasoning` /
   `record.tool_use` / `record.generating` events tagged `stream: "wire"`
   via `wireCandidateEvent`. Block stop maps to the existing
   `wire.retracted`. Non-pollution rides `foldWireAsserted` unchanged.
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
                              # None = no active block (block stop / terminal)
  tool_call_id: str | None    # provider tool id when kind = running_tool
  ts: datetime (UTC)          # emitter clock at classification
  provider_event: str         # diagnostics only: the provider event name
```

`phase: start` is a fact with a non-null `kind`; `phase: stop` and turn
terminal are facts with `kind = None`. Collapsing stop/terminal to one row
shape is safe because the machine's reaction to both is the same retraction
path (§5), and the finalize plane, not the live overlay, owns end-of-turn
meaning.

### 2.1 Anthropic mapping

Event rules mirrored from `AnthropicAdapter._inbound_response_sse`
(`api/src/transport_matters/adapters/anthropic.py`); the classifier retains a
per-flow map of block index → kind so `content_block_stop` can be attributed:

| Provider event | Fact |
|---|---|
| `content_block_start`, `content_block.type == "thinking"` | start `reasoning` |
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
`codex_terminal_status`) and the derivation precedent in
`derive_codex_turn_incremental`
(`api/src/transport_matters/codex/derivation_engine.py`):

| Provider event | Fact |
|---|---|
| `response.output_item.added`, item type `reasoning` | start `reasoning` |
| `response.output_item.added`, item type `function_call` / `custom_tool_call` / `tool_search_call` | start `running_tool`, `tool_call_id` = call id when present |
| `response.output_text.delta` | start/affirm `generating` |
| `response.output_item.done` | stop (`kind = None`) |
| `response.completed` / `response.failed` | terminal (`kind = None`) |

Two Codex transports, one classifier:
- **WebSocket** (primary): already message-framed. Hook in
  `handle_codex_websocket_message`
  (`api/src/transport_matters/addon_handlers.py`) feeds payload dicts to the
  classifier directly; no reframer needed.
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

One row per run; plain `ON CONFLICT (run_id) DO UPDATE` last-write-wins. No
seq guard in SQL: ordering is enforced by the emitter (one proxy process per
run, per-run latest-wins slot with a single in-flight write, §4.3), and the
row is an ephemeral overlay whose staleness the admission contract absorbs
(§5.2). Rows are never GC-critical: after `run-exited` the machine's
`exited` guard (`reconcileWireSnapshot` early return in
`packages/activity/src/service/activityIngestion.ts`) makes the row inert.

Workspace and owner columns exist so the doorbell payload can carry routing
identity, symmetric with `_wire_exchange_notify_payload`
(`api/src/transport_matters/session/writer.py`).

### 3.2 Writer method

`SessionWriter.submit_run_live_status(row)` in
`api/src/transport_matters/session/writer.py`, mirroring
`_commit_run_lifecycle_event` / `submit_wire_exchange`: commit the upsert,
then `pg_notify` on the same connection so the NOTIFY fires on commit.
Statement lives in `api/src/transport_matters/session/dao_statements.py`,
row model beside `RunLifecycleEventRow` in
`api/src/transport_matters/session/models.py`.

### 3.3 Doorbell wiring (invariant preserved)

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
"run X needs reconcile" and nothing else. Reconnect reconcile
(`onConnected → reconcileMaterialized` in `activityIngestion.ts`) reads the
current row, so a dropped NOTIFY loses nothing.

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

Retains only the unterminated tail across calls; applies the same record
rules as `iter_sse_data_objects` (scan `data:` lines, skip empty and
`[DONE]`, skip malformed JSON without losing subsequent records). Tail is
capped (1 MiB); on overflow the framing state drops and resyncs at the next
record boundary — the live plane is best-effort by contract.

**Proof tests (required, colocated per api/CLAUDE.md):**
- every-byte-boundary split of a canned multi-event SSE body yields the
  identical payload sequence as the whole-buffer parse;
- multiple events in one chunk;
- `[DONE]` skipped;
- a malformed JSON `data:` line skipped, subsequent events intact;
- trailing partial retained and completed by the next chunk;
- overflow resync.

### 4.2 Classifier (pure)

New module `api/src/transport_matters/live_status.py`: `LiveStatusFact`,
`AnthropicLiveClassifier`, `CodexLiveClassifier`. Both consume payload dicts
and yield facts per §2. Codex reuses `codex_payload_event_type` and
`codex_terminal_status` (`api/src/transport_matters/codex/protocol.py`)
rather than a third payload fold. Anthropic mirrors the branch rules of
`_inbound_response_sse` (the method itself cannot resume across chunks; the
scout confirms all its state is local, so the rules are re-expressed
incrementally, not the method reused). Pure computation stays sync per
api/CLAUDE.md.

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
completion the slot, if changed, is written. Live status is
last-write-wins, so dropping superseded intermediate facts is correct and
bounds both memory and pool usage (one connection, matching the existing
cap noted in `addon_runtime.py`).

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
in `handle_codex_websocket_message` with the classifier only.

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

## 5. TS: mid-turn admission, block stop, exact reuse

### 5.1 Store read

`ActivityStore` (`packages/activity/src/service/activityIngestion.ts`) gains
a fourth read method `readLiveStatusForRun(runId)`; implemented by
`PostgresActivityReader` with `LIVE_STATUS_BY_RUN_SQL` in
`packages/activity/src/adapters/postgresRecords.ts`, columns pinned beside
the existing contracts in `packages/activity/src/server/pgContracts.ts`.
The port is test-doubled everywhere already (`activityIngestion.test.ts`,
`wireIngestion.test.ts`); doubles return `null` until slice 4's tests.

### 5.2 Candidate vocabulary and admission

`WireCandidate` (`packages/activity/src/domain/wireCandidate.ts`) gains
three live variants:

```ts
| { kind: "live-reasoning";    assertId: string; ts: string }
| { kind: "live-running-tool"; assertId: string; ts: string; toolCallId: string | null }
| { kind: "live-generating";   assertId: string; ts: string }
```

`assertId = "live:{runId}:{seq}"` plays the role `exchangeId` plays for
finalize candidates: it stamps `wireAssertedExchangeId` through
`foldWireAsserted` and keys stall suppression and same-assert dedupe. A new
`seq` from the emitter is a new assert; the identical row re-read by a later
reconcile pass is the same assert and neither re-asserts nor retracts —
the same no-flap discipline `reconcileWireSnapshot` documents today.

`wireCandidateAdmitted` extends:
- `live-running-tool` with `toolCallId`: admit iff
  `!context.resolvedToolCallIds.has(toolCallId)` — the identical anchor the
  finalize `running-tools` arm uses; a transcript that already resolved the
  call is strictly fresher. With `toolCallId === null`: **admit**. This
  deliberately differs from the finalize arm's refusal of id-less
  candidates: a finalize assert is a standing end-of-turn claim with no
  later retraction trigger, while a live assert is superseded within
  seconds by the next fact or the turn's finalize snapshot, so an
  unanchored admit is recoverable by construction.
- `live-reasoning` / `live-generating`: admit unconditionally (the `exited`
  guard in the service still applies first). These are **not**
  cold-start-gated like `anomaly` / `idle`: mid-turn the wire is strictly
  fresher than the journaled transcript — the temporal collapse this design
  exists to fix.

`wireAssertSuppressedBySilenceStall` applies unchanged over `assertId`: a
fresh live fact (new seq) clears a silence stall — bytes on the wire are the
definition of not-silent — while the same assert re-read never flaps it.

### 5.3 One resolution step per pass

`reconcileWireSnapshot` (`packages/activity/src/service/activityIngestion.ts`)
becomes the wire-plane resolution step, same position in `reconcile` (after
records, before `run-exited`):

1. Early return on `context.status === "exited"` (unchanged).
2. Read both `readWireSnapshotForRun` and `readLiveStatusForRun`.
3. Derive at most **one** candidate, preserving the existing "at most one
   candidate per pass" property:
   - live row with non-null `kind` and `live.ts > snapshot.ts` (or no
     snapshot) → live candidate via a new `liveCandidateFromRow` beside
     `wireCandidateFromSnapshot`
     (`packages/activity/src/service/runActivityEvents.ts`);
   - otherwise → the finalize candidate via `wireCandidateFromSnapshot`
     (unchanged behavior). A live row with `kind = null` or one dated at or
     before the latest finalized exchange is a spent overlay and yields no
     live candidate.
4. Suppress / admit / refuse / retract exactly as today:
   `wireAssertSuppressedBySilenceStall`, `wireCandidateAdmitted`,
   `wireCandidateEvent`, and the trailing `wireRetractedEvent` when a
   wire-owned status has no admissible candidate.

**Block stop → `wire.retracted`, exact reuse:** a stop or terminal fact
upserts `kind = null`; step 3 yields no live candidate; if the finalize
snapshot also yields none (mid-turn: it cannot, its response has not
committed) the trailing branch sends `wireRetractedEvent`
(`packages/activity/src/domain/wireCandidate.ts`) and
`statusAfterWireRetraction` recomputes from record-owned fields under the
per-state `wireRetractionRestores` guards and `WIRE_RETRACTED_TRANSITIONS`
(`packages/activity/src/domain/runActivityMachine.ts`). No new event type,
no new fold.

### 5.4 Event minting and non-pollution (exact reuse)

`wireCandidateEvent` gains three arms mapping live kinds onto the existing
machine vocabulary: `live-reasoning → record.reasoning`,
`live-running-tool → record.tool_use`, `live-generating →
record.generating`, all with `seq: 0`, `stream: "wire"`, id
`assertId`-derived, `wireExchangeId = assertId`. These are first-class
machine events with dedicated states and folds (`foldReasoning`,
`foldGenerating`, `foldToolUse` in
`packages/activity/src/domain/runActivityContext.ts`); the wire stream
routes them through `foldWireAsserted`, which **never writes
`lastActiveStatus` or `pendingToolCallIds`** — the PR-3 non-pollution
property reused verbatim. Wire events never advance `entry.watermark`
(`isNewEvent` short-circuits for the wire stream), so a dropped or stale
live fact can never corrupt durable, record-owned machine state. The
finalize plane is untouched: `WIRE_SNAPSHOT_BY_RUN_SQL`, the wire store
write path, and the machine's states change not at all.

Projections, SSE router, contract DTOs, and every browser package: zero
change. A mid-turn status change is an ordinary `delta` frame
(`ActivityStreamFrame` in `packages/contract/src/activity/wire.ts`).

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
renders it. Required test: a lifecycle-only run appears in
`listWorkspaceActivity` as `starting`, remains owner-scoped (wrong owner
sees nothing), and an existing-session run's behavior is unchanged.

## 7. PR slice plan

Each slice lands green on its own; the feature turns on only at slice 4.
Slice 5 is orthogonal and can land in any order after slice 0-independence
is confirmed by its own gates.

| # | Slice | Plane | Content | Gates (verbatim) |
|---|---|---|---|---|
| 1 | Dark store + doorbell | Python | Migration 0009 `run_live_status`; row model; DAO upsert; `SessionWriter.submit_run_live_status` + `run_live_status` NOTIFY flavor; writer tests. No producer, no consumer. | `cd api && just check && just test` |
| 2 | Pure incremental machinery | Python | `IncrementalSseFrames` reframer + §4.1 proof suite; `live_status.py` classifiers (Anthropic + Codex) + §2 mapping tests. No wiring. | `cd api && just check && just test` |
| 3 | Blessed emit seam | Python | `install_response_tee` `on_chunk` param; `LiveStatusObserver` + `_start_session_capture` wiring; Codex WS tap; latest-wins slot; §4.4 frozen-plane red tests. Producer live, rows written, nothing reads them. | `cd api && just check && just test` |
| 4 | Product consumer (feature ON) | TS | `run_live_status` payload decode; `readLiveStatusForRun` + SQL + pinned columns; live `WireCandidate` variants + admission + resolution step + `wireCandidateEvent` arms; ingestion/domain tests incl. stop→retraction and live-vs-finalize freshness. | `pnpm --filter @tm/activity test` and `pnpm --filter @tm/shell test` |
| 5 | Empty-at-spawn | Both | Migration 0010 owner on `run_lifecycle_event`; `build_run_lifecycle_event` / `RunLifecycleEventRow` owner; notify payload owner; `RUNS_BY_WORKSPACE_SQL` LEFT JOIN + COALESCE; lifecycle-only-run `starting` test. | `cd api && just check && just test` and `pnpm --filter @tm/activity test` and `pnpm --filter @tm/shell test` |

Risks carried from the scout, addressed in-slice: reframer bounded state
(slice 2 overflow test); `iter_sse_data_objects` never fed raw chunks
(slice 2 keeps it untouched for finalize paths); `ExchangeSink` final-only
semantics preserved by bypassing it entirely (slice 3 red test); database
integration for slice 5 requires the configured Postgres test URL the scout
could not exercise.
