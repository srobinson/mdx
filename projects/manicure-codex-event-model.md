---
title: Manicure Codex Event Model
type: projects
tags: [manicure, codex, transport, events, architecture]
summary: Event model for ChatGPT authenticated Codex exchanges. Transport stays canonical. Turn events are derived, versioned, and turn scoped.
status: active
project: manicure
confidence: high
created: 2026-04-19
updated: 2026-04-19
parent_issue: ALP-1815
predecessor: manicure-codex-event-model.002.md
sibling: manicure-codex-event-model-tasks.md
---

# Manicure Codex Event Model

## Predecessor

This supersedes `manicure-codex-event-model.002.md`.

The prior revision got the broad direction right:

1. `transport.json` is the canonical record.
2. Codex is a websocket session carrying multiple turns.
3. Product semantics should be derived from wire truth, not treated as first class transport.

That revision still left six contract gaps:

1. It mixed session lifecycle events into a turn scoped event log.
2. It described derivation as pure but did not define versioning or read precedence for persisted derived artifacts.
3. It used `provisional|committed` at the event level without defining which event kinds can transition.
4. It did not specify how incremental derivation and full replay remain byte equivalent.
5. It did not make the operator consequence of dropped initial frames explicit.
6. It left turn range invariants underspecified for interrupted turns.

This revision resolves those gaps.

## Companion Docs

1. [Task plan](./manicure-codex-event-model-tasks.md)
2. [Previous event model revision](./manicure-codex-event-model.002.md)

## One Sentence Summary

Manicure models Codex as a canonical websocket transport session that yields many turn scoped exchanges; each exchange persists raw transport plus a versioned, deterministic, turn only semantic timeline derived from that transport.

## What Codex Is On The Wire

A Codex session is one websocket to `wss://chatgpt.com/backend-api/codex/responses`.

Within that websocket:

1. The client sends `response.create` to start a turn.
2. The server streams item adds, deltas, item completions, and a terminal `response.completed` or `response.failed`.
3. The client may submit tool outputs on the same websocket as part of a later turn.
4. The websocket may close cleanly or abruptly, including during an active turn.

Two facts govern the design:

1. One websocket can contain many turns.
2. A turn has two boundaries: a start boundary at client `response.create`, and a terminal boundary at server terminal frame or websocket close.

## Core Principles

### 1. Transport Is Canonical

`transport.json` is the only authoritative record of Codex wire activity. It stores every captured websocket message with ordering, direction, timestamps, parsed JSON when available, raw bytes, and drop state.

No derived artifact may overwrite or reinterpret transport in place.

### 2. Derived Artifacts Are Deterministic And Versioned

Semantic artifacts are derived from canonical transport plus local Manicure facts that are not present on the wire:

1. request curation metadata
2. breakpoint lifecycle metadata
3. derivation schema version

The deriver is pure with respect to those inputs.

Every persisted derived artifact carries `derivation_version`. Persisted derived artifacts are the default read path. Re-derivation is an explicit repair or migration action, not an implicit read time behavior.

Event timestamps and identifiers must also be deterministic. `ts`, `event_id`, and `seq` are derived from canonical transport ordering plus persisted turn metadata, not from wall clock time at derivation execution. Replay on the same transport slice must therefore reproduce the same serialized event stream.

### 3. Session Scope And Turn Scope Stay Separate

Manicure's primary product unit remains the exchange, and one exchange maps to one turn.

Turn artifacts contain turn scoped semantics only.

Session lifecycle facts such as websocket upgrade and websocket close remain in transport diagnostics and optional session summaries. They are not duplicated into each turn event log.

### 4. Turn Boundaries Are Two Sided

Every turn has:

1. a start boundary at the client `response.create`
2. a terminal boundary at the first of:
   1. server `response.completed`
   2. server `response.failed`
   3. websocket close before either terminal server frame

Both boundaries matter operationally. Detecting only one of them creates one turn lag bugs and shutdown only persistence behavior.

### 5. Provisional State Lives At The Turn Level

Provisional state is represented by an open turn, not by a vague event status bit.

While a turn is open:

1. `turn.json.status = "open"`
2. transport continues to append
3. the UI may render live provisional output from transport plus in memory accumulators

Persisted semantic events are committed facts only. They do not mutate after write.

### 6. Incremental Derivation Must Match Full Replay

The system supports both:

1. incremental derivation while frames arrive
2. full replay from canonical transport

Both paths must produce byte equivalent `events.jsonl` and `turn.json` for the same `derivation_version`.

This requires an explicit derivation cursor and replay contract.

Byte equivalent here means exact serialized equivalence, not merely semantic equivalence. The requirement applies to event ordering, `event_id`, `seq`, and `ts` as well as payload content.

### 7. Semantic Vocabulary Stays Small

Deltas remain transport facts. The semantic layer records operator useful milestones, not every streaming fragment.

## Domain Model

### TransportSession

One websocket lifetime. Used for diagnostics, not as the primary product timeline.

- `session_id`
- `provider`
- `host`
- `path`
- `upgrade_request_headers_redacted`
- `upgrade_response_status_code`
- `upgrade_response_headers_redacted`
- `opened_at`
- `closed_at`
- `close_code`
- `close_reason`
- `closed_by_client`

### Turn

One exchange in the current storage model.

- `turn_id`
- `exchange_id`
- `session_id`
- `turn_index`
- `request_message_index`
- `terminal_message_index`
- `terminal_cause`
- `message_range_start`
- `message_range_end`
- `model`
- `status`
- `stop_reason`
- `text_chars`
- `tool_calls`
- `started_at`
- `ended_at`
- `derivation_version`

Field rules:

1. `message_range_start` is always the index of the client `response.create` for the turn.
2. `message_range_end` is the inclusive index of the last websocket message attributed to the turn.
3. `terminal_message_index` is the index of the terminal server frame for `completed` and `failed` turns, otherwise `null`.
4. `terminal_cause` is one of `response_completed`, `response_failed`, or `websocket_close`.
5. `status` is one of `open`, `completed`, `failed`, or `interrupted`.
6. `stop_reason` is required for `completed` and `failed`, optional for `interrupted`, and absent for `open`.

### SemanticEvent

Ordered, append only, and strictly turn scoped.

Envelope:

```json
{
  "event_id": "evt_000017",
  "exchange_id": "ex_123",
  "session_id": "ws_abc",
  "turn_id": "turn_002",
  "seq": 17,
  "ts": "2026-04-19T10:14:03.221Z",
  "source": "client|server|proxy|operator",
  "kind": "turn_started",
  "transport_ref": { "message_index": 23 },
  "data": {},
  "derivation_version": 1
}
```

Event rows are immutable once written. There is no per event provisional state.

`ts` is the timestamp of the source transport fact or persisted operator action that caused the event, not the time the deriver happened to run.

### DerivationCursor

Stored inside `turn.json` while a turn is open so incremental derivation can resume without replaying the full transport slice on every frame.

- `next_message_index`
- `next_seq`
- `open_assistant_items`
- `open_tool_calls`
- `terminal_seen`

The cursor is an execution detail, not a product API field.

## Event Taxonomy (V1)

Only turn scoped semantics belong here.

### Turn lifecycle

- `turn_started`
- `request_curated`
- `breakpoint_paused`
- `breakpoint_released`
- `turn_finalized`

### Assistant output

- `assistant_item_completed`

### Tool activity

- `tool_call_completed`
- `tool_output_submitted`

### Terminal markers

- `response_completed`
- `response_failed`

That is the complete V1 vocabulary.

## Mapping Rules

The deriver consumes the turn's transport slice in order and emits committed events.

### Start Boundary

On client `response.create`:

1. emit `turn_started`
2. if proxy curation changed the outbound payload, emit `request_curated`
3. if a breakpoint paused the request, emit `breakpoint_paused`
4. if an operator later released the paused request, emit `breakpoint_released`

If the initial frame was dropped before release:

1. no turn begins
2. no exchange is created
3. the operator action remains visible only in transport and breakpoint diagnostics

This is intentional. Dropped attempts are transport history, not turn history.

### Streaming Window

Between start and terminal boundary:

1. accumulate assistant item deltas by item id
2. emit `assistant_item_completed` only when the upstream protocol marks the item complete
3. accumulate tool call arguments by call id
4. emit `tool_call_completed` only when the tool call resolves into a completed call payload
5. emit `tool_output_submitted` when the client sends tool output in a later turn

No delta level semantic events are emitted.

For Codex this usually means the later turn's client `response.create` payload contains `function_call_output` or `custom_tool_call_output` items. The semantic event is therefore derived from request payload contents inside that start frame, not from a separate standalone websocket message.

### Terminal Boundary

On server `response.completed`:

1. emit `response_completed`
2. emit `turn_finalized`
3. rewrite `turn.json` with `status = completed`

On server `response.failed`:

1. emit `response_failed`
2. emit `turn_finalized`
3. rewrite `turn.json` with `status = failed`

On websocket close before either server terminal frame:

1. emit no session lifecycle event into the turn log
2. emit `turn_finalized`
3. rewrite `turn.json` with `status = interrupted` and `terminal_cause = websocket_close`

## Persistence Shape

### Canonical

- `request.raw`
- `request.ir.json`
- `request.curated.raw`
- `request.curated.ir.json`
- `request.audit.json`
- `transport.json`
- `response.raw` when a single raw response body exists outside the websocket frame stream, for example handshake failure, HTTP fallback, or proxy generated error response

### Derived

- `events.jsonl`
- `turn.json`

`events.jsonl` is append only and turn scoped.

`turn.json` is created when the turn starts and rewritten as the cursor and terminal summary advance.

`turn.json` contains:

1. public turn summary fields
2. `derivation_version`
3. internal cursor state while `status = open`

When a turn finalizes, cursor state may be retained for diagnostics or stripped during a compaction pass. The public summary remains stable either way.

## Read And Repair Contract

Read behavior:

1. if `events.jsonl` and `turn.json` exist and their `derivation_version` is supported, return them as authoritative
2. if derived artifacts are missing, a repair path may re-derive them from canonical transport
3. if derived artifacts are present but from an older version, migration is explicit, not implicit

This keeps historical displays stable while preserving the ability to rebuild damaged or missing derived state.

## Crash Consistency And Partial Write Contract

The write order is intentional, but order alone is not the contract. Readers and repair tools must handle partial persistence explicitly.

Allowed states:

1. `transport.json` is ahead of `events.jsonl`
2. `events.jsonl` is ahead of `turn.json`
3. `turn.json` exists with `status = open` while later transport frames already exist

Reader rules:

1. `transport.json` remains the source of truth in every state
2. `events.jsonl` is trusted only through the last durable row
3. `turn.json` is treated as a summary cache and may lag behind transport and events
4. repair may extend `events.jsonl` and rewrite `turn.json`, but it must never rewrite canonical transport

This means a crash after transport append but before semantic persistence is recoverable by replay. A crash after event append but before `turn.json` rewrite is recoverable by rebuilding the turn summary from transport plus durable events.

## API Shape

Exchange detail response gains:

1. `transport`
2. `events`
3. `turn`

The exchange list uses `turn.status`, `turn.stop_reason`, `text_chars`, and `tool_calls`.

Session lifecycle remains a diagnostics concern until there is an explicit session level product surface.

## UI Implications

1. Exchange list shows turn summary fields.
2. Exchange detail defaults to the turn event timeline.
3. Inspect or Transport keeps the raw frame view.
4. Each event deep links to its source frame through `transport_ref.message_index`.
5. Live provisional rendering for open turns comes from transport aware UI state, not mutable event rows.

## Relationship To ALP-1815 Work

1. ALP-1846 established the transport side terminal boundary detection that this model depends on.
2. ALP-1845 removed the late shutdown storage failure that previously made terminal persistence unreliable.
3. ALP-1832 and ALP-1833 established the provisional per turn exchange shape that this document builds on.

## Implementation Plan

Phase names and ordering here are intentionally identical to `manicure-codex-event-model-tasks.md`.

### Phase 0. Confirm Transport Boundary Contract

Treat the current Codex transport turn slicing as fixed input:

1. confirm terminal markers
2. confirm item completion markers
3. confirm websocket close interruption behavior
4. freeze the assumptions the deriver will consume

### Phase 1. Formalize Models

Add frozen models for:

1. `CodexTransportRef`
2. `CodexSemanticEvent`
3. `CodexTurnSummary`
4. `CodexDerivationCursor`

### Phase 2. Define Derivation Contract

Define the explicit replay and incremental contract:

1. `derivation_version = 1`
2. full replay from turn start
3. incremental advance from persisted cursor
4. deterministic `event_id`, `seq`, and serialization rules

### Phase 3. Build Pure Deriver

Implement a deterministic deriver under `api/src/manicure/codex/` with two entry points:

1. full replay from turn start
2. incremental advance from persisted cursor

Both entry points must serialize identically for the same input and `derivation_version`.

### Phase 4. Persist Derived Artifacts

Wire the incremental deriver into websocket message handling so that:

1. `transport.json` appends first
2. new committed semantic events append second
3. `turn.json` rewrites last

This preserves the rule that transport remains canonical if a later write fails.

### Phase 5. Read, Repair, And Migration

Make supported derived artifacts authoritative on read, and keep rebuild behavior explicit:

1. normal reads return supported persisted derived artifacts
2. repair rebuilds missing artifacts
3. migration upgrades unsupported `derivation_version` artifacts
4. no implicit read time re-derivation

### Phase 6. Wire Derivation Into Live Codex Flow

Connect live websocket handling to incremental derivation and per turn persistence.

### Phase 7. API Exposure

Expose `events` and `turn` on exchange detail while keeping `transport` intact.

### Phase 8. Timeline UI

Use `events` and `turn` to make the semantic timeline the default Codex detail view while keeping transport one tab away.

### Phase 9. Fixtures And Regression Coverage

Minimum fixture set:

1. single turn success
2. multi turn success on one websocket
3. `response.failed`
4. websocket close mid turn
5. handshake failure
6. breakpoint edited turn
7. dropped initial frame
8. tool result only continuation turn

## Recommendation

Keep transport canonical. Keep events turn scoped. Keep derivation deterministic and versioned. Treat provisional state as an open turn concern, not an event mutation concern. Make incremental derivation and full replay obey the same contract, then use the semantic timeline as the operator default and raw transport as the forensic layer underneath it.
