# Feature Spec: Activity (Control Center v1)

> Template note: this document is the first instance of the transport-matters
> feature-spec template. Future features copy the numbered skeleton (sections 0
> through 10) and fill their own content. Sections marked (template-fixed)
> describe conventions that apply to every feature, not just this one. Forward
> direction, decision records, and cross-feature standards live in
> `docs/ARCHITECTURE.md` and cm, never inline in the spec.
> Convention source of truth once slice 0 lands: `docs/ARCHITECTURE.md`.

Status: approved design, amended after scout + product correction 2026-07-03;
slice 2 ingestion/materialization contract added 2026-07-04 (§7.1, §10).
Author: brainstorm session, Stuart + Fable. Supersedes the pre-scout draft
(wire-derived status, facts.jsonl transport).

## 0. Product boundary (this feature)

Inspector is a completed product; its UI/UX is frozen and it will never
display canvas activities. Breakpoints and the wire remain its domain and are
out of scope here. All new product work targets Canvas. Activity's status
semantics derive from the transcript, which records all needed metadata
explicitly; nothing is inferred from wire behavior.

**Two-plane rule (2026-07-03).** Python is the capture plane: mitmproxy
integration, tier-1 writes, and the frozen inspector API + session store,
maintained but not extended. TypeScript is the product plane: everything new
(Activity, control-center serving, future Comms/Recall/orchestration) is
built in TS in the pnpm workspace, the language the product already lives in.
The planes meet at the stores: the Postgres session store is the record
contract between planes; run directories hold artifacts referenced by id.
The product plane never reads the capture plane's filesystem. Activity is
the first product-plane context.

## 1. Charter

Activity is the bounded context that owns interpretation of run state. It
consumes the live transcript record stream (Session context) and run
lifecycle facts (Runtime context) and projects three things: per-run status,
per-run overview, and usage rollups. Its product surface is the Control
Center, a canvas face showing what is happening in a workspace right now.

Operational awareness leads v1. The spend ledger is a later read over the
same substrate and ships as its own phase.

## 2. Context map delta (template-fixed structure)

Producers feeding Activity in v1:

| Context | Home today | Provides |
|---|---|---|
| Session | `session/`, `index/` tailing pipeline | normalized transcript records: message roles, tool use, turn boundaries, question asks, usage payloads, timestamps |
| Runtime | RunManager (`api/` app.state), launch lease (`captured_run.py`) | RunStarted, RunExited |

Capture and Intervention remain truth-owning contexts but publish nothing in
v1; they join the fact backbone when a future feature (Log, audit) needs the
wire's own events.

New downstream context: `activity/`. Dependency rule, enforced by
import-linter: dependencies point downstream only. Producers never import
Activity. No module outside `activity/` may compute a status.

## 3. Ubiquitous language

- Transcript record: what the CLI wrote to disk, tailed live by TM. The
  richest available account of agent lifecycle; carries explicit metadata.
- Fact: past-tense statement published by a truth-owning context
  (RunStarted, RunExited in v1).
- RunActivity: the aggregate holding one run's interpreted state.
- Status: one of starting, thinking, running-tools, needs-you, stalled,
  exited. Only Activity assigns these words meaning. Status is a mapping
  from recorded transcript metadata, not an inference.
- Overview: initial prompt plus last agent message, from the transcript.
- Rollup: monotonic usage accumulation from transcript usage payloads.
  Context size is computed per harness, declared in its bundle: Claude is
  `input + cache_creation + cache_read`; Codex `input_tokens` is already the
  total with cache included. Output tokens are never context. Cache-split
  availability is a capability flag, never faked into another harness's
  shape.
- context_tokens: the latest turn's context size, a current-window value that
  rises and falls as context is added and compacted, distinct from the
  monotonic total_usage rollup. Computed with the same per-harness rule.
- Control Center: the canvas surface listing RunActivity for a workspace.

## 4. Package layout (template-fixed shape)

Canonical context package; every new product-plane feature follows this
shape (TS, pnpm workspace; exact package home fixed in slice 0 and recorded
in ARCHITECTURE.md):

```
@tm/activity (workspace package)
  src/index.ts       # explicit export surface; the only import path for other packages
  src/domain/        # pure: RunActivity XState machine, invariants; no IO
  src/events.ts      # facts THIS context emits (none in v1; empty registry)
  src/service/       # use-cases: consume records/facts, run actors, trigger projections
  src/ports.ts       # interfaces: RecordSource, RunLifecycleSource, Clock
  src/adapters/      # port implementations: run-dir discovery, transcript tailer, markers
  src/projections/   # read models: workspace overview, rollups
  src/server/        # HTTP + SSE serving, owner-scoped
  fixtures/          # transcript fixtures per harness per version (v1 corpus home;
                     # consolidation with harnesses/ is part of the bundle follow-on)
```

State machine runtime: XState (pin the current major at slice 0 and verify
against current docs, do not trust training-data recall). Per-run actor,
guarded transitions, stalled timeout as a native delayed transition; the
Stately inspector makes machine state inspectable live.

Effect boundary rule (2026-07-03): `domain/` is pure XState with zero IO.
No `Effect` is ever invoked inside an XState action — that seam is the
documented footgun (`runSync` throws into the executor, `runPromise` loses
fiber interruption; no official adapter). The shell drives the machine from
outside by sending already-resolved events and reading snapshots. The v1
shell is plain, disciplined TS behind `ports.ts`. Whether the shell later
becomes Effect is a separate, reversible decision the ports isolate: port
implementations in `adapters/` can move to Effect without the domain or the
machine changing. If Effect is ever adopted it is shell-only (typed IO
errors, structured concurrency, resource cleanup), never at the action seam;
the only correct seam if that line is ever crossed is genuine `ActorLogic`
with fiber interruption (`@typeonce/effect-xstate` `fromEffect`), which v1
deliberately does not need.

Frontend consumers:

```
www/packages/core/src/activity/    # contract types + fetch/SSE hooks
www/packages/canvas/src/activity/  # Control Center surface
```

Naming register: backend packages are prosaic (`activity`), product surfaces
may be branded (Control Center). No cute names in code paths.

## 5. Contracts

### 5.1 Inputs consumed

- Transcript records read from the Postgres session store (transcripts are
  already in pg; the product plane never reads the capture plane's
  filesystem). The store preserves raw records (`session/ingest.py`
  `build_event` keeps raw META and TURN payloads), which matters because
  the `normalize()` path drops exactly the lifecycle records Activity
  needs; Activity maps raw stored records to a narrow `ActivityRecord` DTO
  at the reader boundary. The reader contract:
  `"event".raw` is the contract, IR columns are advisory; the only pre-pg
  alterations are the `skip_until_user_text` replay anchor and decoded-NUL
  stripping, neither touching any marker. Liveness comes from `LISTEN
  tm_events` (payload: type, session_id, run_id, first_seq/last_seq; range
  query events by seq), extended with a `run_lifecycle` payload type on the
  same channel so there is one listener and one reconnect path; the Python
  listener must ignore unknown payload types gracefully. The Session write
  path is not touched.
- Status markers, fixture-proven per harness:
  Claude session JSONL: `user` record opens a turn; `assistant` `tool_use`
  pending until matching `tool_result`; `stop_reason: end_turn` ends a turn;
  `AskUserQuestion` tool_use is the question-ask marker; `tool_result`
  `is_error` is error evidence; usage on `assistant.message.usage`. Codex
  rollout: `task_started` opens; `function_call`/`function_call_output`
  pending pair; `task_complete` ends; `request_user_input` is the ask
  marker; `turn_aborted` is error evidence; usage on `token_count` events.
- RunStarted { workspace_id, run_id, ts, harness, launch_kind: canvas|detached }
  and RunExited { workspace_id, run_id, ts, exit_reason } — rows in a new
  narrow `run_lifecycle_event` table (not `"event"`: RunStarted can precede
  the first session row). Idempotency: unique (run_id, event_type) with
  insert-or-ignore, so the `_teardown_run` -> `_close_lease` overlap is
  harmless; canvas exits written at `RunManager._teardown_run` after final
  state, detached exits at `CapturedRunLease.close` via an injected sink,
  starts at launch registration with workspace fields. `session_id` is not
  required on lifecycle rows; correlation flows from the `"session"` table's
  `run_id`. The one small capture-plane change v1 makes. Crash cases (no
  exit row ever) fall to the stalled timeout.

### 5.2 Fact contract properties (template-fixed; the forward commitment)

Every fact any context publishes, now and in future features, must be:

1. Self-contained and serializable. No live object references.
2. Schema-versioned.
3. Identity-stamped: workspace_id, run_id, ts, per-producer seq, so ordering,
   dedupe, and replay work later.
4. Content by reference: point at stored artifacts, never embed payload bytes.
   Need-to-know at the event layer; keeps the future Log cheap and audit clean.

### 5.3 Read surface

- `GET /workspaces/{id}/activity`: list of RunActivity projections
  { run_id, harness, launch_kind, status, since_ts, initial_prompt,
  last_message, context_tokens, total_usage, exit_reason? }.
- Workspace-scoped SSE stream of RunActivity deltas (sibling to the existing
  run SSE; `broadcast.py` is run-scoped and stays untouched).
- Owner-scoped, same auth posture as existing session read surfaces.

## 6. Domain

### 6.1 Aggregate and invariants

RunActivity, keyed by run_id, owned by workspace_id. Invariants:

- Status changes only through the defined mapping from recorded metadata and
  lifecycle facts.
- Usage accumulation is monotonic.
- `exited` is terminal.
- Record application is idempotent under replay.

### 6.2 Status mapping

States: starting, thinking, running-tools, needs-you, stalled, exited.

| Recorded input | Status |
|---|---|
| RunStarted, nothing recorded yet | starting |
| user message recorded, assistant turn open | thinking |
| tool use recorded, result pending | running-tools |
| assistant turn ended / harness question asked | needs-you |
| transcript error record, or silence past timeout while a turn is open | stalled (reason recorded) |
| RunExited | exited |

The table above is the domain shape; the authoritative per-harness mapping
from concrete record types is fixed in slice 1 from fixtures and lives in the
harness adapters. The domain never knows which harness it is watching.
Silence timeout is configurable, default 10 minutes; long tool runs are
legitimate. A new record clears stalled. A failed tool call annotates
running-tools and never flips status by itself; only `turn_aborted`-class
records or the timeout degrade to stalled (no flapping; agents recover from
tool errors constantly). Detached run liveness derives from its launch
lease: `CapturedRunLease.close` emits RunExited; crash cases fall to the
stalled timeout in v1.

## 7. Data flow

One TS service, store-fed. Session store notify -> pg reader (raw records +
lifecycle rows) -> `ActivityRecord` mapping -> per-run XState actor ->
workspace projection (in-memory, keyed by workspace identity) -> HTTP + SSE
-> `@tm/core` activity hooks -> canvas Control Center.

Projection state is process-resident. Restart introduces no new persistence:
runs rematerialize lazily by bounded replay from the store (§7.1), pg being
the durable record. Rollups derive from stored usage payloads; persisting
rollups is deferred until the ledger phase needs it. Packaging of the Node service inside the
one-tool install is an open item flagged for slice 3, not a blocker for the
dev-mode slices (users of TM run Node by definition; the CLIs are Node).

### 7.1 Ingestion and materialization (slice 2 contract)

The store is the source of truth for every event: each row commits before its
`tm_events` NOTIFY fires, so anything the live feed carries is already
replayable from the store. The store is therefore the only durable buffer;
ingestion keeps no second in-memory copy that could be lost.

Two-tier projection:

- Coarse workspace index — which runs exist in a workspace and each run's
  latest lifecycle status, derived from a store query at read time. Listing
  runs never spawns an actor.
- Materialized run — the per-run XState actor (status, since_ts, overview,
  context, usage) is spawned lazily on first demand for that run. No
  boot-time scan; nothing is eager.

One reconcile loop per run. The single `tm_events` listener routes every NOTIFY
(record and lifecycle) by run_id. A NOTIFY carries no data the actor applies
directly; it only MARKS the run as needing reconciliation. One per-run reconcile
loop then retries bounded store reads (`readRecordsForRunAfter` for records, the
lifecycle read for facts) until both the record watermark and the lifecycle
cursor are current, applying events in contiguous seq order. The record cursor
is per session (a `(sessionId, seq)` cursor over the session-start total order):
one run can hold multiple primary sessions — a mid-run `/clear` or rollout
rotation mints a new primary session under the same run_id — so a run-global
single cursor would hide the rotated session's records. A read failure
never clears the reconcile-needed state: it retries with backoff and surfaces as
telemetry, so a transient error can never strand a run. Because the loop only
advances a monotonic watermark and always reads from the store, it is lossless
and converges under any arrival rate. The `isNewEvent` seq-cursor dedupe (§6.1)
keeps re-reads idempotent. "Store is truth" lives in this one place.

No in-memory event buffer in v1. The reconcile loop reads the store on each
trigger; a fast-path buffer is a later optimization layered on the correct loop,
never a correctness dependency, and is deliberately omitted in v1.

Materialization trigger: on demand (first read of the run). Truly lazy;
un-materialized runs ignore NOTIFYs and reconcile from the store on first read.

## 8. Error handling

- Ingestion never crashes on bad input. Malformed or unrecognized records are
  skipped, counted, and logged.
- `transport-matters doctor` gains an activity section: records flowing,
  tailer lag, dropped-record count, and detached cursor-registration
  failures (which are logged-and-continue today and would otherwise be a
  silent observability gap; non-fatal, never fails a launch).
- Idempotent application; resync after rotation or truncation dedupes.
- State timestamps come from the record, not receive time.
- Unrecognized record types map conservatively: keep current status, count,
  log.

## 9. Testing and gates

- Domain: model-based tests over the XState machine (`@xstate/test` or the
  current equivalent, verified at slice 0) generating paths through every
  transition, plus table-driven cases for the invariants. Pure, no IO.
- Harness mapping: recorded transcript fixtures (Claude JSONL, Codex rollout)
  asserting mapped status sequences, overview extraction, and usage payloads.
- Ingestion: integration test against a real Postgres for notify-driven
  reads, restart replay from the store, dedupe, and lifecycle rows.
- Server: owner-scope contract tests.
- Boundary: the existing www import-graph discipline extends to the new
  package (only `src/index.ts` importable; core/canvas may not reach into
  internals), red-tested to fail closed.
- Canvas face: Playwright driving status transitions through an SSE fixture.
- Gates are the repo recipes verbatim.

## 10. Slices

0. The standard itself: `docs/ARCHITECTURE.md` opening with the two-plane
   rule, then the canonical package shape, target context map, and
   future-context charters; the `@tm/activity` package skeleton with the
   XState machine, invariants, and model-based tests; boundary gate extended.
1. Producer seams: record-to-status mapping tables and transcript fixtures
   per harness in the package's fixture corpus; the pg reader + notify
   listener and `ActivityRecord` mapping; run lifecycle rows (the one small
   Python change, at launch registration, `_teardown_run`, and lease close).
2. Ingestion and projection: per-run actors driven from the pg reader and the
   live listener, the workspace projection, and lazy materialization with a
   per-run reconcile loop (store-as-truth, retry owns failures) and restart-safe
   store replay (§7.1). The §5.3 read-model
   fields are pulled forward from slice 3 and projected here: `ActivityRecord`
   gains the turn's prompt and agent-message text (parsed from raw in
   `transcriptRecords`), and the machine context retains `initial_prompt` (set
   once), `last_message` (overwritten), and the last turn's `context_tokens`
   (current-window, per-harness, distinct from the monotonic `total_usage`).
   `since_ts` is the ts of the event that set the current status. Slice 3
   exposes these over HTTP + SSE.
3. Read surface: HTTP + workspace SSE + rollups, owner-scoped; packaging
   answer for the Node service.
4. Canvas face: `@tm/core` activity slice, Control Center surface,
   Playwright.

Each slice is one PR, built in a warroom (codex engineer, review weight per
blast radius). Slices 1 and 2 carry the highest review weight.
