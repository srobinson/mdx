---
title: Manicure Codex Event Model Tasks
type: projects
tags: [manicure, codex, transport, events, tasks]
summary: Implementation task breakdown for the Codex event model. Rewritten to align with the event-model v2 rewrite and ALP-1846.
status: active
project: manicure
confidence: high
created: 2026-04-19
updated: 2026-04-19
parent_issue: ALP-1815
predecessor: manicure-codex-event-model-tasks.001.md
sibling: manicure-codex-event-model.md
---

# Manicure Codex Event Model Tasks

## Predecessor

This supersedes `manicure-codex-event-model-tasks.001.md`. The prior breakdown was internally consistent with v1 of the event model doc, but that model has been rewritten. Four changes propagate into this task plan:

1. **ALP-1846 is Phase 0.** Without server-side terminal-boundary detection, the deriver cannot emit `turn_finalized` correctly. The v1 plan ignored this and would have inherited the one-turn-lag bug.
2. **Deltas are not semantic events.** V1 included `assistant_text_delta`, `tool_call_arguments_delta`, `assistant_reasoning_delta` as deriver outputs. The v2 model rolls deltas up into `assistant_item_completed` and `tool_call_completed`. Tasks and acceptance criteria reflect the smaller vocabulary (15 kinds).
3. **Event persistence is append-only, not deferred.** V1 offered "provisional events or defer until finalization" as a live choice. V2 commits to append-as-derived. The Phase 3 / Phase 4 tasks change accordingly.
4. **Turn boundaries are two-sided.** Start boundary is the client `response.create` frame; terminal boundary is server `response.completed` / `response.failed` / websocket close. Every turn-lifecycle task distinguishes these.

The v1 backlog, risks, and mitigations are mostly still valid. This version updates wording where needed and removes items that no longer apply.

## Goal

Deliver the Codex event model described in `manicure-codex-event-model.md`:

- `transport.json` remains the sole source of truth
- `events.jsonl` stores derived semantic events (append-only while a turn is open)
- `turn.json` stores a derived turn summary (rewritten on `turn_finalized`)
- Exchange detail API returns `transport`, `events`, and `turn`
- UI defaults to a semantic timeline, keeps raw transport one tab away

## Scope

In scope:

- backend models for `CodexSemanticEvent`, `CodexTurnSummary`, `CodexTransportRef`
- pure deriver: `(TransportArtifacts, curation, breakpoint_lifecycle) -> (events, turn)`
- incremental persistence of `events.jsonl` and `turn.json`
- exchange detail API expansion
- semantic timeline UI
- fixture and regression coverage for completed, failed, interrupted, handshake-failure, dropped-initial-frame, and breakpoint-edited paths

Out of scope for this task set:

- transport capture contract changes (owned by ALP-1846 and its siblings)
- session-level archive redesign
- provider-neutral event abstraction across Anthropic and Codex

## Implementation Order

### Phase 0. Land ALP-1846

Objective: produce the terminal-boundary detection the deriver depends on.

Tasks:

- identify the authoritative Codex server frame kinds that signal turn completion (`response.completed`, `response.failed`) and item completion (`response.output_item.done` or equivalent)
- add mid-session finalization trigger in `handle_codex_websocket_message` / the codex transport layer, firing on the terminal frame rather than on the next client turn
- keep rotation-on-next-client-frame as a defensive fallback, guarded against double-finalize
- regression test: turn N persists before turn N+1's client frame

Acceptance criteria (from ALP-1846):

- turn N's `transport.json`, `response.raw`, and `response.ir.json` become authoritative as soon as the turn's assistant reply completes
- no double-finalize when a next-client-frame rotation follows a server-terminal finalization
- shutdown-path finalization (ALP-1845) remains correct

Files likely touched:

- `api/src/manicure/addon_handlers.py`
- `api/src/manicure/codex/transport.py`
- `api/src/manicure/codex/exchange.py`
- `api/src/manicure/test_codex_transport_turns.py`

This phase is a hard prerequisite. Later phases assume a reliable terminal-boundary signal.

### Phase 1. Formalize Models

Objective: define the backend data structures for the event model.

Tasks:

- add `CodexTransportRef` with `message_index`
- add `CodexSemanticEvent` envelope (event_id, seq, ts, source, kind, status, transport_ref, data)
- add `CodexTurnSummary` with `status` ∈ {`open`, `completed`, `failed`, `interrupted`}, `stop_reason`, `text_chars`, `tool_calls`, `request_message_index`, `completion_message_index`, `message_range_start`, `message_range_end`
- constrain `source`, `kind`, and `status` with literals; do not use free-form strings
- colocate models in a new `api/src/manicure/codex/events.py` (not in `storage/base.py` — storage should depend on codex models, not the other way around)

Acceptance criteria:

- models serialize with stable JSON output (Pydantic v2, `model_dump(mode="json")`)
- `kind` covers the full V1 taxonomy and nothing more:
  - session: `transport_upgrade_request`, `transport_upgrade_response`, `websocket_closed`
  - turn: `turn_started`, `request_curated`, `breakpoint_paused`, `breakpoint_released`, `turn_finalized`
  - assistant: `assistant_item_completed`
  - tool: `tool_call_completed`, `tool_output_submitted`
  - terminal: `response_completed`, `response_failed`
- deltas are explicitly not in the taxonomy; they remain in `transport.json`
- models are `frozen=True` where they represent IR-style value objects

### Phase 2. Build Pure Deriver

Objective: implement `derive_events(transport, curation, breakpoint_lifecycle) -> (events, turn_summary)` with no I/O.

Tasks:

- walk `TransportArtifacts.messages` in sequence for one turn
- emit `turn_started` from the client `response.create` frame
- emit `request_curated` when curation metadata is present; emit `breakpoint_paused` / `breakpoint_released` when breakpoint lifecycle was invoked
- accumulate text/reasoning deltas per item; emit a single `assistant_item_completed` when the server signals item completion
- accumulate tool-call argument deltas per call id; emit a single `tool_call_completed` on resolution
- emit `tool_output_submitted` on client tool-output frames
- emit `response_completed` or `response_failed` on the terminal server frame; follow with `turn_finalized` and populate `status`
- emit `websocket_closed` when the session closes; if it closes before a terminal server frame, `turn_finalized` carries `status=interrupted`
- every event derived from a frame carries `transport_ref.message_index`

Suggested file touches:

- new `api/src/manicure/codex/events.py` (models + deriver, or split if the file grows)
- `api/src/manicure/codex/test_events.py` (colocated unit tests, per api/CLAUDE.md convention)

Acceptance criteria:

- deriver is a pure function: no storage, no network, no input mutation
- deterministic: identical input produces identical output
- preserves message ordering via `seq`
- fixture-covered for all six canonical paths (single-turn success, multi-turn success, interrupted, failed, handshake failure, breakpoint-edited, dropped-initial-frame)
- no event emitted for individual deltas

### Phase 3. Persistence

Objective: write derived artifacts alongside `transport.json`.

Tasks:

- extend `ExchangeArtifacts` with optional `events: list[CodexSemanticEvent] | None` and `turn: CodexTurnSummary | None`
- write `events.jsonl` incrementally as events are derived during the turn (append-only)
- write `turn.json` on first event (status `open`), rewrite on `turn_finalized`
- make read paths tolerant: legacy exchanges without these files load with `events=None`, `turn=None`
- keep the ALP-1845 dedicated I/O executor — do not reintroduce default-executor `aiofiles` calls in the write path

Suggested file touches:

- `api/src/manicure/storage/base.py`
- `api/src/manicure/storage/disk.py`
- `api/src/manicure/storage/test_disk.py`
- `api/src/manicure/storage/test_disk_persist.py`

Acceptance criteria:

- new exchanges write `events.jsonl` incrementally and `turn.json` on first event
- process death mid-turn leaves a truncated-but-valid `events.jsonl` plus `transport.json` that together reconstruct observed history
- legacy exchanges missing the derived files still load cleanly and render via the transport tab
- partial-write failure does not leave the index pointing at broken artifacts (preserves ALP-1840 invariants)

### Phase 4. Finalization Integration

Objective: wire the deriver into the Codex exchange lifecycle at the right hooks.

Tasks:

- on turn start (client `response.create`): emit `turn_started` / `request_curated` / breakpoint events; create `events.jsonl` and initial `turn.json`
- as server frames arrive: derive events incrementally and append
- on turn terminal (from Phase 0): emit `response_completed` / `response_failed` / `turn_finalized`; rewrite `turn.json`
- on websocket close without terminal frame: emit `websocket_closed` and `turn_finalized` with `status=interrupted`
- dropped initial client frame: emit only `transport_upgrade_*` events; do not create `events.jsonl` or `turn.json`
- handshake failure: emit only `transport_upgrade_request` and `transport_upgrade_response`

Suggested file touches:

- `api/src/manicure/codex/exchange.py`
- `api/src/manicure/addon_handlers.py`
- `api/src/manicure/test_codex_transport_turns.py`
- `api/src/manicure/test_codex_transport.py`

Acceptance criteria:

- finalized Codex exchange persists transport, events, and turn summary together
- multi-turn websocket sessions produce separate `events.jsonl` / `turn.json` per exchange
- dropped initial client frames do not emit misleading derived events
- turn N's derived artifacts complete before turn N+1's client frame arrives

### Phase 5. API Exposure

Objective: return derived artifacts from exchange detail endpoints.

Tasks:

- extend `ExchangeDetailResponse` with `events: list[CodexSemanticEvent] | None` and `turn: CodexTurnSummary | None`
- preserve backward compatibility: consumers that only read `transport` continue to work
- keep diagnostic generation working for legacy exchanges without derived artifacts
- ensure redaction logic from ALP-1826 / ALP-1839 applies to events that embed request or response excerpts

Suggested file touches:

- `api/src/manicure/api/v1/exchanges.py`
- `api/src/manicure/api/v1/test_exchanges.py`
- `api/src/manicure/api/v1/test_exchanges_get.py`

Acceptance criteria:

- exchange detail returns `events` and `turn` when present, null when absent
- legacy exchanges still return `transport`
- no frontend consumer is forced to parse raw websocket payloads for common operator workflows
- sensitive header and body content does not leak through event payloads

### Phase 6. Timeline UI

Objective: make the semantic timeline the default detail view.

Tasks:

- extend frontend types with `CodexSemanticEvent` and `CodexTurnSummary`
- add a semantic timeline component
- deep-link every timeline row to the raw transport frame via `transport_ref.message_index`
- keep the Transport / Inspect tab available for forensic use
- surface turn summary fields (status, stop reason, text chars, tool calls) in the detail header and exchange list
- render provisional events with distinct styling; commit styling on `turn_finalized`

Suggested file touches:

- `www/src/types.ts`
- `www/src/components/detail/ExchangeDetail.tsx`
- `www/src/components/detail/InspectTab.tsx`
- new timeline component files under `www/src/components/detail/`
- visual regression fixtures under `www/tests/visual/`

Acceptance criteria:

- operators can understand a Codex turn from the timeline alone
- raw transport remains one tab away
- UI handles legacy exchanges gracefully (no timeline, transport tab only)
- provisional vs committed events are visually distinguishable

### Phase 7. Fixtures And Regression Coverage

Objective: lock behavior with fixture-driven tests.

Tasks:

- build fixture transport artifacts for each canonical path
- snapshot-test deriver output (events list + turn summary) against each fixture
- assert message range boundaries directly
- assert event ordering and `transport_ref.message_index` linkage
- add frontend tests for timeline rendering and empty-state fallbacks
- add visual regression for the semantic timeline view

Suggested file touches:

- `api/tests/fixtures/`
- `api/src/manicure/codex/test_events.py`
- `api/src/manicure/test_codex_transport.py`
- `api/src/manicure/test_codex_transport_turns.py`
- `www/src/components/detail/`
- `www/tests/visual/`

Acceptance criteria:

- fixtures cover: single-turn success, multi-turn success, interrupted, failed, handshake failure, dropped initial frame, breakpoint-edited turn
- event order, kinds, and `transport_ref` values are asserted directly
- turn summary fields (`status`, `stop_reason`, `text_chars`, `tool_calls`, message range) are asserted
- regressions in message slicing, turn rotation, or delta rollup fail loudly

## Task Backlog

Flat list, for grooming into Linear sub-issues.

### Prerequisite

- **P0.1** ship ALP-1846 (terminal-boundary detection)

### Backend models

- **B1.1** add `CodexTransportRef`
- **B1.2** add `CodexSemanticEvent`
- **B1.3** add `CodexTurnSummary`
- **B1.4** define literal constraints for `source`, `kind`, `status`
- **B1.5** decide module layout (new `codex/events.py` recommended)

### Backend deriver

- **B2.1** implement pure `derive_events`
- **B2.2** delta rollup: assistant items
- **B2.3** delta rollup: tool-call arguments
- **B2.4** terminal-frame handling (completed / failed / interrupted)
- **B2.5** curation and breakpoint lifecycle integration
- **B2.6** handshake-failure and dropped-initial-frame paths

### Storage

- **B3.1** extend `ExchangeArtifacts` with optional `events` and `turn`
- **B3.2** incremental `events.jsonl` append
- **B3.3** `turn.json` write on first event, rewrite on `turn_finalized`
- **B3.4** legacy-tolerant read paths
- **B3.5** ALP-1840 rollback invariants preserved

### Backend integration

- **B4.1** wire deriver into `handle_codex_websocket_message`
- **B4.2** wire deriver into terminal-boundary hook (from ALP-1846)
- **B4.3** wire deriver into websocket-close path
- **B4.4** ensure no event emission for dropped initial frames

### API

- **B5.1** extend `ExchangeDetailResponse`
- **B5.2** redaction coverage for event payloads
- **B5.3** legacy-exchange compatibility

### Frontend types and components

- **F6.1** add event and turn types
- **F6.2** build semantic timeline component
- **F6.3** deep-link timeline rows to transport frames
- **F6.4** surface turn summary in detail header
- **F6.5** surface turn summary in exchange list
- **F6.6** provisional vs committed visual treatment
- **F6.7** graceful fallback for legacy exchanges

### Testing

- **T7.1** deriver unit tests per canonical path
- **T7.2** storage round-trip tests
- **T7.3** API response tests
- **T7.4** UI component tests
- **T7.5** visual regression fixtures

## Dependencies

Hard dependencies:

- **ALP-1846** must land before Phase 2 delivers reliable `turn_finalized` behavior
- **ALP-1845** (shutdown finalization) must remain intact; the new I/O executor is load-bearing for the write path
- **ALP-1840** rollback invariants must survive the new write path
- transport capture contract stays stable

Sequencing:

- Phase 0 before everything
- Phase 1 before Phase 2
- Phase 2 before Phase 3 and Phase 4
- Phase 4 before Phase 5
- Phase 5 before Phase 6
- Phase 7 can run alongside each phase but locks in at the end

## Risks

### Risk 1. Terminal-marker schema shifts upstream

If Codex changes the server-side completion-frame schema, the deriver misclassifies turns.

Mitigation:

- treat frame-kind detection as a small, isolated module
- fixture-test against captured real frames, not synthetic ones
- keep the rotation-on-next-client-frame fallback path (from ALP-1846) as a safety net

### Risk 2. Derived events drift from transport

An operator sees a timeline that disagrees with raw frames.

Mitigation:

- require `transport_ref.message_index` on every frame-derived event
- snapshot-test deriver output against fixture transport
- refuse to emit semantic events that cannot be traced back to a frame or lifecycle hook

### Risk 3. Multi-turn rotation produces wrong event ranges

Turn N's events bleed into turn N+1 or vice versa.

Mitigation:

- explicit start and terminal boundaries per turn
- assert `message_range_start` and `message_range_end` directly in fixtures
- test back-to-back client frames with interleaved server frames

### Risk 4. Legacy archive reads break

Existing exchanges without derived artifacts fail to load.

Mitigation:

- `events` and `turn` are optional on read
- default to `None` or empty when absent
- UI keeps transport tab as the fallback surface

### Risk 5. Frontend reimplements parsing logic

UI starts parsing `transport.json` to fill deriver gaps.

Mitigation:

- all parsing lives in the backend deriver
- frontend consumes typed events only
- any parsing-shaped PR in `www/` is a review red flag

### Risk 6. Delta rollup swallows meaningful signal

Rolling deltas into `_completed` events hides progress information operators relied on.

Mitigation:

- transport tab retains full delta visibility
- timeline shows incremental progress via provisional-status `turn_started` until `turn_finalized`
- if operators ask for delta-level semantics later, introduce them additively

## Done Criteria

This work is complete when all of the following hold:

- ALP-1846 is landed
- Codex exchanges persist `transport.json`, `events.jsonl`, and `turn.json`
- exchange detail API returns `transport`, `events`, and `turn`
- semantic timeline is the default detail view for Codex exchanges
- multi-turn sessions remain correctly split into per-turn exchanges
- fixture coverage locks single-turn success, multi-turn success, interrupted, failed, handshake failure, dropped initial frame, and breakpoint-edited paths
- operators can debug a turn without reading raw frames first
- v1 delta taxonomy has not re-entered the semantic layer

## Recommended First Slice

If this is implemented incrementally, the first useful slice:

1. land ALP-1846 (Phase 0)
2. define Phase 1 models
3. implement Phase 2 deriver against fixture transport, no storage yet
4. expose deriver output through the API in memory (Phase 5 minimal) behind a flag
5. validate taxonomy and rollup logic against real captured Codex sessions

Persisting derived artifacts and rewriting the UI come after the taxonomy is proven. That order protects against baking a bad event vocabulary into disk and frontend code simultaneously.
