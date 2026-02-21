---
title: Manicure Codex Event Model
type: projects
tags: [manicure, codex, transport, events, architecture]
summary: Proposed event model for ChatGPT authenticated Codex exchanges that preserves raw websocket transport while deriving turn level semantic events for API and UI use.
status: active
project: manicure
confidence: high
created: 2026-04-18
updated: 2026-04-18
parent_issue: ALP-1815
---

# Manicure Codex Event Model

## Summary

Codex transport is not a simple client request and server response pair. The correct shape is a persistent websocket session that carries a sequence of turns. Each turn begins with a client `response.create` frame and is followed by a streamed series of server events such as text deltas, tool related items, completion events, failures, and close state.

Manicure should model this with two layers:

- raw transport artifacts as the canonical record of what happened on the wire
- derived semantic events as the operational model for the API, UI, and diagnostics

This keeps debugging faithful while giving the product a stable event vocabulary that does not require reparsing websocket frames in every surface.

## Why Request Response Is The Wrong Model

A simple request and response abstraction loses critical information:

- one websocket session can contain many turns
- one turn can contain many server events
- streamed output is provisional until completion or failure
- tool activity arrives as intermediate events, not one final response blob
- a websocket close can happen after a completed turn, during a partial turn, or after a failed turn
- proxy edits and breakpoint releases change what was actually forwarded upstream

For Codex, ordering matters more than a parent child tree. The model must preserve sequence and the boundary between captured transport facts and inferred semantic state.

## Current Grounding In Manicure

The current codebase already has the core pieces needed for this model.

- `transport.json` is the canonical persisted websocket artifact. It stores upgrade metadata, close state, and every captured frame. See `DOCS/codex-transport-artifacts.md`.
- `TransportArtifacts` and `TransportMessageArtifact` already persist frame level detail, including direction, parsed JSON, dropped state, and payload size. See `api/src/manicure/storage/base.py`.
- turn rotation already happens on each client `response.create` frame. When a new turn starts, the prior provisional exchange is finalized before the next turn is opened. See `api/src/manicure/addon_handlers.py` and `api/src/manicure/test_codex_transport_turns.py`.
- response summary stats are already derived from websocket messages, not a fake HTTP response body. See `api/src/manicure/codex/transport.py`.

The gap is not transport capture. The gap is the lack of a first class semantic event timeline derived from that capture.

## Design Principles

### 1. Raw Transport Remains Canonical

`transport.json` must remain the source of truth for debugging, audits, and future reparsing. No higher level event model should replace or overwrite it.

### 2. Semantic Events Are Derived

The higher level model should be generated from transport artifacts plus proxy side lifecycle hooks such as breakpoint pause, request curation, and exchange finalization.

### 3. Turn Boundaries Must Be Explicit

The natural turn boundary is the client `response.create` frame. That is already how Manicure slices Codex exchanges today, so the event model should reuse it.

### 4. Provisional State Must Be Represented

Text deltas, partial tool arguments, and open turns are not final output. The model must distinguish provisional state from committed state.

### 5. Every Derived Event Must Point Back To Transport

Any semantic event that comes from a websocket frame should retain a reference to the original message index. This preserves debuggability and lets the UI pivot between semantic and raw views.

## Proposed Domain Model

The model should distinguish four concepts:

- `transport_session`
  One websocket connection, including upgrade metadata and close state.
- `turn`
  One client initiated `response.create` request plus the server event range associated with it.
- `semantic_event`
  A typed, ordered event derived from transport and proxy lifecycle hooks.
- `artifact`
  Persisted files such as `request.raw`, `request.curated.raw`, `transport.json`, and future derived event files.

### Transport Session

A transport session spans the full websocket lifetime. It is useful for diagnostics and for understanding whether multiple turns shared the same connection.

Suggested fields:

- `session_id`
- `provider`
- `scheme`
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

A turn is the primary product level unit for Codex. It begins when the client sends `response.create`.

Suggested fields:

- `turn_id`
- `exchange_id`
- `session_id`
- `turn_index`
- `request_message_index`
- `message_range_start`
- `message_range_end`
- `model`
- `status`
  Allowed values: `open`, `completed`, `failed`, `interrupted`, `abandoned`
- `stop_reason`
- `text_chars`
- `tool_calls`
- `started_at`
- `ended_at`

### Semantic Event

Each event is append only and ordered within the turn.

Suggested envelope:

```json
{
  "event_id": "evt_000017",
  "exchange_id": "ex_123",
  "session_id": "ws_abc",
  "turn_id": "turn_002",
  "seq": 17,
  "ts": "2026-04-18T10:14:03.221Z",
  "source": "client",
  "kind": "turn_started",
  "status": "committed",
  "transport_ref": {
    "message_index": 23
  },
  "data": {}
}
```

Suggested common fields:

- `event_id`
- `exchange_id`
- `session_id`
- `turn_id`
- `seq`
- `ts`
- `source`
  Allowed values: `client`, `server`, `proxy`, `storage`, `ui`
- `kind`
- `status`
  Allowed values: `provisional`, `committed`, `final`
- `transport_ref`
  Usually `{ "message_index": <int> }` when derived from a websocket frame
- `data`
  Event specific payload

## Event Taxonomy

The event set should stay small and operational.

### Session And Transport Events

- `transport_upgrade_request`
- `transport_upgrade_response`
- `websocket_closed`
- `diagnostic_emitted`

### Turn Lifecycle Events

- `turn_started`
- `request_captured`
- `request_curated`
- `breakpoint_paused`
- `breakpoint_released`
- `turn_finalized`

### Assistant Output Events

- `assistant_text_delta`
- `assistant_item_added`
- `assistant_item_completed`
- `assistant_reasoning_delta`

### Tool Activity Events

- `tool_call_started`
- `tool_call_arguments_delta`
- `tool_call_completed`
- `tool_output_submitted`

### Terminal Events

- `response_completed`
- `response_failed`

The exact set can grow later, but V1 should start from events that clearly map to current Codex payloads and current Manicure lifecycle hooks.

## Mapping Rules

The mapping should be deterministic and pure where possible.

### Turn Start

Client `response.create` frame:

- create `turn_started`
- create `request_captured`
- if the proxy modified the outbound request, create `request_curated`

This matches the current flow where Manicure captures the initial request IR, runs the pipeline, persists a provisional exchange, and optionally pauses before forwarding.

### Assistant Text

Server `response.output_text.delta` frame:

- create `assistant_text_delta`
- mark it `provisional`
- include delta text length and any block identifiers available in the payload

Server completion is what commits the accumulated output.

### Tool Calls

When a server payload contains `function_call` or `custom_tool_call` content:

- first observation of a call id creates `tool_call_started`
- argument deltas create `tool_call_arguments_delta`
- a resolved call payload creates `tool_call_completed`

If the client later submits tool outputs on the same session, that should produce `tool_output_submitted`.

### Completion And Failure

Server `response.completed` frame:

- create `response_completed`
- derive `stop_reason`
- create `turn_finalized`
- mark turn status `completed`

Server `response.failed` frame:

- create `response_failed`
- create `turn_finalized`
- mark turn status `failed`

### Websocket Close

Close summary always produces `websocket_closed`.

Its meaning depends on turn state:

- after `response_completed`, it is transport epilogue
- before completion, it may imply interruption or abandonment
- after a dropped initial client frame, no exchange should be finalized

## Persistence Shape

Manicure should persist both canonical transport and derived event artifacts.

### Canonical

Keep the current files:

- `request.raw`
- `request.ir.json`
- `request.curated.raw`
- `request.curated.ir.json`
- `request.audit.json`
- `transport.json`
- `response.raw` for handshake failures

### Derived

Add:

- `events.jsonl`
  One semantic event per line, ordered by `seq`
- `turn.json`
  One summary document for the exchange turn

`events.jsonl` is a better fit than one large JSON array because it preserves append friendly semantics and makes it easier to inspect partial failures.

## API Shape

The exchange detail API should expose both levels.

Suggested additions to the current detail response:

- `transport`
  existing raw transport artifact
- `events`
  derived semantic event list
- `turn`
  derived turn summary

This gives the UI three useful modes:

- raw transport inspection for forensic debugging
- semantic timeline for normal operator use
- compact turn summary for lists and badges

## UI Implications

The UI should not ask operators to read raw websocket frames unless they need forensic detail.

Recommended product surfaces:

- exchange list uses `turn.status`, `turn.stop_reason`, `text_chars`, and `tool_calls`
- detail page defaults to semantic timeline
- raw transport stays available in an Inspect or Transport tab
- each semantic event links back to the underlying websocket frame by message index

This preserves debug power without forcing websocket literacy on every operator.

## Implementation Plan

### Phase 1. Formalize The Event Models

Add Pydantic models for:

- `CodexSemanticEvent`
- `CodexTurnSummary`
- `CodexTransportRef`

These should live near the existing transport models, not inside the UI layer.

### Phase 2. Build A Pure Deriver

Implement a pure function that takes:

- `TransportArtifacts`
- request curation metadata
- optional breakpoint lifecycle data

and returns:

- ordered semantic events
- a turn summary

This function should avoid storage or network side effects.

### Phase 3. Persist Derived Artifacts

Write `events.jsonl` and `turn.json` beside `transport.json` during exchange finalization. For provisional exchanges, either defer writing until finalization or write provisional events and replace them on finalize.

### Phase 4. Expose Through The API

Extend exchange detail responses so consumers can fetch semantic events without reparsing transport payloads in the frontend.

### Phase 5. Update The UI

Add a semantic timeline view that renders typed events and uses `transport_ref.message_index` to jump to raw transport messages when needed.

### Phase 6. Lock The Behavior With Fixtures

Build fixture driven tests from:

- successful multi turn websocket sessions
- failed turns
- abnormal close paths
- handshake failures
- breakpoint edited turns

## Open Questions

### Should Events Be Persisted Or Derived On Read

Persisting events makes the API simple and keeps interpretation stable over time. Deriving on read reduces stored artifacts but moves more logic into read paths. For Manicure, persisted derived events are the better choice because this is a debugging product and historical replay should not depend on future parser changes.

### Do We Need DAG Structure

Not initially. A total order with transport references is enough for V1. Most operator questions are timeline questions, not graph traversal questions.

### Should A Websocket Session Have Its Own Top Level Archive

Not yet. The current per exchange archive is already aligned with turn level debugging and the codebase already rotates per turn. Session level grouping can be added later if operators need a cross turn session view.

## Recommendation

Do not model Codex as request and response. Model it as:

- websocket transport session
- ordered turn stream
- append only transport facts
- derived semantic event timeline

In practical terms, keep `transport.json` canonical, add `events.jsonl` and `turn.json`, and make `response.create` the turn boundary. That matches the transport reality, matches the code already in this repository, and gives Manicure a stable foundation for both debugging and product level representation.
