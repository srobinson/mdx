---
title: Manicure Codex Event Model Tasks
type: projects
tags: [manicure, codex, transport, events, tasks]
summary: Implementation task breakdown for the Codex event model that layers derived semantic events on top of canonical websocket transport artifacts.
status: active
project: manicure
confidence: high
created: 2026-04-18
updated: 2026-04-18
parent_issue: ALP-1815
---

# Manicure Codex Event Model Tasks

## Goal

Implement a Codex event model that preserves raw websocket transport as canonical while adding a derived semantic timeline and turn summary for API and UI use.

The target artifact shape is:

- `transport.json` remains canonical
- `events.jsonl` stores derived semantic events
- `turn.json` stores a derived turn summary

## Scope

In scope:

- backend event and turn models
- deterministic derivation from captured transport
- persistence of derived artifacts
- exchange detail API exposure
- UI timeline rendering
- fixture and regression coverage

Out of scope for this task set:

- changing the underlying Codex transport capture contract
- session wide archive redesign
- provider neutral event abstraction for every runtime

## Implementation Order

### Phase 1. Formalize Models

Objective:

Define the backend data structures for semantic events and turn summaries.

Tasks:

- add `CodexTransportRef` model
- add `CodexSemanticEvent` model
- add `CodexTurnSummary` model
- define enums or constrained literals for `source`, `kind`, and `status`
- decide whether these models live in `api/src/manicure/codex/transport.py` or a new `api/src/manicure/codex/events.py`

Suggested file touches:

- `api/src/manicure/storage/base.py`
- `api/src/manicure/codex/transport.py`
- or new `api/src/manicure/codex/events.py`

Acceptance criteria:

- models are serializable with stable JSON output
- event envelope includes `transport_ref.message_index`
- turn summary includes status, stop reason, text chars, tool calls, and message range

### Phase 2. Build Event Deriver

Objective:

Create a pure derivation function that converts transport artifacts into semantic events and a turn summary.

Tasks:

- implement a pure function that accepts `TransportArtifacts`
- derive `turn_started` from client `response.create`
- derive `assistant_text_delta` from server `response.output_text.delta`
- derive tool related events from `function_call` and `custom_tool_call` payloads
- derive `response_completed`, `response_failed`, and `turn_finalized`
- derive `websocket_closed` from close summary
- include request curation and breakpoint events when local metadata is available

Suggested file touches:

- new `api/src/manicure/codex/events.py`
- `api/src/manicure/codex/transport.py`

Acceptance criteria:

- derivation is deterministic for the same input artifacts
- derived events preserve message ordering
- each event points back to the source message index where applicable
- summary status is correct for completed, failed, and interrupted turns

### Phase 3. Extend Storage Models

Objective:

Make derived events and turn summaries first class persisted artifacts.

Tasks:

- extend `ExchangeArtifacts` to carry `events` and `turn`
- define disk file names and serialization format
- choose `events.jsonl` for events and `turn.json` for summary
- update storage read and write paths
- ensure missing legacy files degrade safely

Suggested file touches:

- `api/src/manicure/storage/base.py`
- `api/src/manicure/storage/disk.py`
- `api/src/manicure/storage/test_disk.py`
- `api/src/manicure/storage/test_disk_persist.py`

Acceptance criteria:

- new exchanges write `events.jsonl` and `turn.json`
- old exchanges without these files still load cleanly
- partial write failure does not leave the index pointing at broken artifacts

### Phase 4. Integrate Finalization Path

Objective:

Generate derived artifacts at the right moment in Codex exchange persistence.

Tasks:

- call the event deriver during Codex provisional finalization
- decide whether provisional exchanges write provisional events or defer until finalization
- ensure rotated multi turn exchanges each get their own derived event set
- keep handshake failure rows explicit and minimal

Suggested file touches:

- `api/src/manicure/codex/exchange.py`
- `api/src/manicure/addon_handlers.py`
- `api/src/manicure/test_codex_transport_turns.py`
- `api/src/manicure/test_codex_transport.py`

Acceptance criteria:

- a finalized Codex exchange persists transport, events, and turn summary together
- multi turn websocket sessions produce separate turn summaries per exchange
- dropped initial client frames do not emit misleading derived events

### Phase 5. Expose Through API

Objective:

Return derived semantic events and turn summaries from exchange detail endpoints.

Tasks:

- extend `ExchangeDetailResponse`
- add `events` and `turn` fields
- preserve backward compatibility for consumers that only use `transport`
- keep diagnostic generation working with legacy exchanges

Suggested file touches:

- `api/src/manicure/api/v1/exchanges.py`
- `api/src/manicure/api/v1/test_exchanges.py`
- `api/src/manicure/api/v1/test_exchanges_get.py`

Acceptance criteria:

- exchange detail returns derived events when present
- legacy exchanges without derived files still return `transport`
- no frontend consumer is forced to parse raw websocket payloads for common cases

### Phase 6. Add Timeline UI

Objective:

Render the derived semantic timeline in the frontend.

Tasks:

- extend frontend types with event and turn models
- add a semantic timeline component
- link timeline rows back to the raw transport message index
- keep raw transport visible for forensic debugging
- use turn summary for header badges or compact stats

Suggested file touches:

- `www/src/types.ts`
- `www/src/components/detail/ExchangeDetail.tsx`
- `www/src/components/detail/InspectTab.tsx`
- new timeline component files under `www/src/components/detail/`

Acceptance criteria:

- operators can understand a Codex turn without reading raw frames first
- raw transport remains available as a secondary surface
- UI handles missing derived artifacts gracefully

### Phase 7. Fixtures And Regression Tests

Objective:

Lock the event model behavior with focused fixture driven coverage.

Tasks:

- add fixture expectations for successful transport capture
- add multi turn fixture coverage
- add abnormal close coverage
- add failure and handshake failure coverage
- add breakpoint edited turn coverage
- add snapshot or assertion coverage for derived event ordering

Suggested file touches:

- `api/tests/fixtures/`
- `api/src/manicure/test_codex_transport.py`
- `api/src/manicure/test_codex_transport_turns.py`
- `www/src/components/detail/`
- visual or component tests where useful

Acceptance criteria:

- fixtures cover completed, failed, interrupted, and handshake failure paths
- event order and turn summary values are asserted directly
- regressions in message slicing or turn rotation fail loudly

## Task Backlog

### Backend Core

- define event model file location
- implement semantic event models
- implement turn summary model
- write derivation logic
- extend storage artifact models
- persist `events.jsonl`
- persist `turn.json`

### Backend Integration

- wire derivation into Codex exchange finalization
- ensure provisional rotation works across multi turn sessions
- expose derived artifacts through exchange detail API
- keep legacy exchange reads backward compatible

### Frontend

- extend API types
- build semantic timeline view
- link timeline entries to transport frames
- surface turn summary in detail header or summary section

### Testing

- add backend fixture coverage
- add storage round trip coverage
- add API response coverage
- add UI rendering coverage

## Dependencies

Hard dependencies:

- existing transport capture must remain intact
- exchange persistence must keep per turn rotation semantics
- storage layer must tolerate legacy exchanges without derived artifacts

Likely sequencing dependencies:

- model definitions before storage changes
- storage changes before API response expansion
- API response expansion before frontend timeline work

## Risks

### Risk 1. Derived Events Drift From Canonical Transport

Mitigation:

- keep derivation pure and deterministic
- retain `transport_ref.message_index` on every frame derived event
- assert fixture level parity between message slices and derived events

### Risk 2. Multi Turn Rotation Produces Wrong Event Ranges

Mitigation:

- keep `response.create` as the explicit turn boundary
- test turn rotation on consecutive client frames
- assert message range boundaries directly

### Risk 3. Legacy Archive Reads Break

Mitigation:

- treat `events.jsonl` and `turn.json` as optional on read
- default to `None` or empty values when absent
- keep `transport` as the fallback inspection surface

### Risk 4. Frontend Reimplements Parsing Logic

Mitigation:

- expose derived events from the API
- keep transport parsing on the backend
- use frontend only for presentation and filtering

## Done Criteria

This work is done when all of the following are true:

- Codex exchanges persist `transport.json`, `events.jsonl`, and `turn.json`
- exchange detail API returns semantic events and turn summary
- UI shows a semantic timeline by default for Codex exchanges
- multi turn websocket sessions remain correctly split into per turn exchanges
- fixture coverage locks completed, failed, interrupted, and abnormal close paths
- operators can debug a turn without needing to parse raw websocket frames first

## Recommended First Slice

If this should be implemented incrementally, the first useful slice is:

1. define backend event models
2. implement a pure deriver from `TransportArtifacts`
3. expose derived events in memory through the exchange detail API without persisting them yet
4. validate the event taxonomy against real fixtures

That slice proves the model before storage and UI commitments harden the shape.
