---
title: Manicure Codex Event Model Tasks
type: projects
tags: [manicure, codex, transport, events, tasks]
summary: Implementation task breakdown for the current Codex event model. Turn events are versioned, deterministic, and strictly turn scoped.
status: active
project: manicure
confidence: high
created: 2026-04-19
updated: 2026-04-19
parent_issue: ALP-1815
predecessor: manicure-codex-event-model-tasks.002.md
sibling: manicure-codex-event-model.md
---

# Manicure Codex Event Model Tasks

## Predecessor

This supersedes `manicure-codex-event-model-tasks.002.md`.

The prior revision kept the broad direction, but still reflected the older event model in four important ways:

1. it still mixed session lifecycle into the turn event taxonomy
2. it still modeled provisional state at the event row level
3. it did not make derivation versioning and repair explicit
4. it did not define the contract between incremental derivation and full replay

This revision aligns the task plan with the current event model:

1. `transport.json` remains canonical
2. `events.jsonl` is turn scoped only
3. `turn.json` carries public turn summary plus open turn cursor state
4. derived artifacts are versioned and authoritative on read
5. repair and migration are explicit backend concerns, not accidental read time behavior

## Companion Docs

1. [Event model](./manicure-codex-event-model.md)
2. [Previous task plan revision](./manicure-codex-event-model-tasks.002.md)

## Goal

Deliver the Codex event model described in `manicure-codex-event-model.md`:

1. `transport.json` remains the sole source of truth
2. `events.jsonl` stores committed, turn scoped semantic events
3. `turn.json` stores the derived turn summary, `derivation_version`, and open turn cursor state
4. exchange detail API returns `transport`, `events`, and `turn`
5. UI defaults to a semantic timeline and keeps transport one tab away

## Scope

In scope:

1. backend models for `CodexTransportRef`, `CodexSemanticEvent`, `CodexTurnSummary`, and `CodexDerivationCursor`
2. pure derivation with full replay and incremental advance entry points
3. versioned persistence of `events.jsonl` and `turn.json`
4. repair and migration path for missing or outdated derived artifacts
5. exchange detail API expansion
6. semantic timeline UI
7. fixture and regression coverage for completed, failed, interrupted, handshake failure, dropped initial frame, breakpoint edited, and tool result only continuation paths

Out of scope:

1. transport capture contract changes beyond already landed Codex transport work
2. session level archive redesign
3. provider neutral event abstraction across Anthropic and Codex
4. implicit read time re-derivation of historical archives

## Implementation Order

Phase names and ordering here intentionally mirror `manicure-codex-event-model.md`.

### Phase 0. Confirm Transport Boundary Contract

Objective: treat transport side turn boundary detection as fixed input to the deriver.

Tasks:

1. confirm the authoritative server side terminal markers already used by the Codex transport path
2. confirm the item completion markers used for assistant item rollup
3. document the current fallback behavior for websocket close before a terminal server frame
4. freeze the turn slicing assumptions the deriver will rely on

Acceptance criteria:

1. the deriver has a stable definition of turn start, item completion, and terminal boundary
2. there is no remaining ambiguity about when a turn becomes `completed`, `failed`, or `interrupted`
3. tests already covering immediate finalization on server terminal frames remain green

### Phase 1. Formalize Models

Objective: define the backend data structures for versioned derived artifacts.

Tasks:

1. add `CodexTransportRef` with `message_index`
2. add `CodexSemanticEvent` without event level provisional state
3. add `CodexTurnSummary` including `terminal_message_index`, `terminal_cause`, `message_range_start`, `message_range_end`, `status`, `stop_reason`, `text_chars`, `tool_calls`, and `derivation_version`
4. add `CodexDerivationCursor` for open turn incremental advance
5. constrain `source`, `kind`, `status`, and `terminal_cause` with literals
6. colocate models in `api/src/manicure/codex/events.py` or a nearby codex module, not in generic storage models

Acceptance criteria:

1. models serialize with stable JSON output
2. event vocabulary matches the current event model and includes only turn scoped kinds:
   1. `turn_started`
   2. `request_curated`
   3. `breakpoint_paused`
   4. `breakpoint_released`
   5. `assistant_item_completed`
   6. `tool_call_completed`
   7. `tool_output_submitted`
   8. `response_completed`
   9. `response_failed`
   10. `turn_finalized`
3. no session lifecycle event kinds appear in the turn event taxonomy
4. no delta event kinds appear in the taxonomy
5. models representing value objects are frozen

### Phase 2. Define Derivation Contract

Objective: specify exactly how replay and incremental advance relate.

Tasks:

1. define `derivation_version = 1`
2. define full replay entry point from turn start
3. define incremental advance entry point from persisted cursor
4. define cursor fields needed to resume rollup safely
5. define byte equivalence requirements between replay and incremental serialization
6. define how `event_id`, `seq`, and timestamps are assigned deterministically from captured state

Acceptance criteria:

1. for a fixed input transport slice and metadata bundle, replay and incremental advance serialize identical `events.jsonl` and `turn.json`
2. cursor semantics are explicit enough to test directly
3. read and repair code can reason about version support without special cases

### Phase 3. Build Pure Deriver

Objective: implement deterministic turn derivation with no I/O.

Tasks:

1. walk the turn transport slice in order
2. emit `turn_started` from the client `response.create`
3. emit `request_curated`, `breakpoint_paused`, and `breakpoint_released` from local metadata when present
4. accumulate assistant deltas by item id and emit `assistant_item_completed` only on upstream item completion
5. accumulate tool call arguments by call id and emit `tool_call_completed` only when the call resolves
6. emit `tool_output_submitted` on client tool output submission frames
7. emit `response_completed` or `response_failed` on terminal server frames
8. emit `turn_finalized` exactly once per turn
9. produce `interrupted` turn summaries on websocket close without terminal server frame
10. attach `transport_ref.message_index` to every frame derived event

Acceptance criteria:

1. deriver is pure
2. deriver is deterministic
3. deriver emits committed facts only
4. no event is emitted for individual deltas
5. dropped initial frames produce no turn events and no turn summary
6. handshake failure produces no turn event log because no turn exists

### Phase 4. Persist Derived Artifacts

Objective: store versioned derived artifacts alongside canonical transport.

Tasks:

1. extend `ExchangeArtifacts` with optional `events` and `turn`
2. append `events.jsonl` as committed events are produced
3. create `turn.json` when the turn starts
4. rewrite `turn.json` as cursor state advances and when the turn finalizes
5. preserve canonical write order so `transport.json` lands before derived artifacts
6. keep the dedicated storage executor intact

Acceptance criteria:

1. new exchanges persist `transport.json`, `events.jsonl`, and `turn.json`
2. `turn.json` includes `derivation_version`
3. `turn.json` includes cursor state only while the turn is open
4. process death mid turn can leave partial but valid derived state without corrupting canonical transport
5. rollback invariants remain intact when a later derived write fails

### Phase 5. Read, Repair, And Migration

Objective: make derived artifacts authoritative on read without turning re-derivation into implicit behavior.

Tasks:

1. treat supported derived artifacts as the default read path
2. tolerate legacy exchanges with no derived files
3. add explicit repair path for missing derived artifacts
4. add explicit migration path for unsupported `derivation_version`
5. define error reporting when canonical transport exists but derived artifacts are inconsistent

Acceptance criteria:

1. legacy exchanges still load cleanly
2. supported derived artifacts are returned without re-deriving on normal reads
3. missing or outdated derived artifacts can be rebuilt intentionally
4. repair and migration do not mutate canonical transport

### Phase 6. Wire Derivation Into Live Codex Flow

Objective: connect the live websocket path to incremental derivation and persistence.

Tasks:

1. on turn start, create the exchange, write initial `turn.json`, and append start phase events
2. as server frames arrive, advance the cursor and append newly committed semantic events
3. on server terminal frame, append terminal events and finalize the turn summary
4. on websocket close without terminal frame, finalize the turn as `interrupted`
5. on dropped initial request, skip exchange creation and skip turn artifact creation
6. keep multi turn websocket sessions split into separate per turn exchanges

Acceptance criteria:

1. turn N finalizes before turn N plus 1 starts
2. no double finalization occurs
3. dropped initial frames do not create misleading turn history
4. tool result only continuation turns still derive correctly

### Phase 7. API Exposure

Objective: return derived artifacts through exchange detail APIs.

Tasks:

1. extend exchange detail response with `events` and `turn`
2. preserve backward compatibility for consumers that only use `transport`
3. surface derivation metadata needed for diagnostics when useful
4. ensure event payloads do not reintroduce sensitive request or response material

Acceptance criteria:

1. exchange detail returns `events` and `turn` when present
2. legacy exchanges still return `transport`
3. common operator workflows do not require frontend parsing of raw websocket payloads
4. redaction guarantees remain intact

### Phase 8. Timeline UI

Objective: make the semantic timeline the primary operator view for Codex turns.

Tasks:

1. extend frontend types with `CodexSemanticEvent` and `CodexTurnSummary`
2. build a semantic timeline component
3. deep link every timeline row to the source transport frame through `transport_ref.message_index`
4. surface turn summary fields in the exchange list and detail header
5. keep raw transport one tab away
6. render open turns as live provisional state derived from turn status, not mutable event rows
7. handle legacy exchanges gracefully

Acceptance criteria:

1. operators can understand a Codex turn from timeline plus summary
2. open turns feel live without inventing provisional event mutations
3. transport remains accessible for forensic work
4. legacy exchanges fall back cleanly

### Phase 9. Fixtures And Regression Coverage

Objective: lock the contract before wider use.

Tasks:

1. build fixture transport artifacts for each canonical path
2. assert replay and incremental advance produce identical bytes
3. snapshot or structurally assert event order, event kinds, summary fields, and range boundaries
4. test repair and migration behavior
5. add frontend tests for timeline rendering and legacy fallback
6. add visual regression coverage for timeline and open turn presentation

Acceptance criteria:

1. fixtures cover:
   1. single turn success
   2. multi turn success on one websocket
   3. `response.failed`
   4. websocket close mid turn
   5. handshake failure
   6. dropped initial frame
   7. breakpoint edited turn
   8. tool result only continuation turn
2. event order and `transport_ref` linkage are asserted directly
3. turn summary invariants are asserted directly
4. replay versus incremental equivalence failures are loud

## Task Backlog

### Models

- `B1.1` add `CodexTransportRef`
- `B1.2` add `CodexSemanticEvent`
- `B1.3` add `CodexTurnSummary`
- `B1.4` add `CodexDerivationCursor`
- `B1.5` define literals for `source`, `kind`, `status`, and `terminal_cause`
- `B1.6` settle codex module layout

### Derivation contract

- `B2.1` define `derivation_version`
- `B2.2` define replay entry point
- `B2.3` define incremental advance entry point
- `B2.4` define deterministic `event_id` and `seq` contract
- `B2.5` define byte equivalence assertions

### Pure deriver

- `B3.1` implement turn start derivation
- `B3.2` implement assistant item rollup
- `B3.3` implement tool call rollup
- `B3.4` implement terminal handling
- `B3.5` implement interrupted turn handling
- `B3.6` integrate curation and breakpoint metadata
- `B3.7` handle dropped initial frame and handshake failure paths correctly

### Storage

- `B4.1` extend `ExchangeArtifacts`
- `B4.2` append `events.jsonl`
- `B4.3` write and rewrite `turn.json`
- `B4.4` preserve canonical first write order
- `B4.5` keep rollback invariants intact

### Read and repair

- `B5.1` support derived artifacts on read
- `B5.2` support legacy exchanges
- `B5.3` add repair path
- `B5.4` add migration path
- `B5.5` add inconsistency diagnostics

### Live integration

- `B6.1` wire start boundary
- `B6.2` wire incremental message advance
- `B6.3` wire terminal finalize
- `B6.4` wire websocket close finalize
- `B6.5` preserve dropped initial frame behavior

### API

- `B7.1` extend exchange detail response
- `B7.2` preserve compatibility
- `B7.3` confirm redaction coverage for event payloads

### Frontend

- `F8.1` add event and turn types
- `F8.2` build semantic timeline
- `F8.3` add transport deep links
- `F8.4` surface turn summary in list and detail
- `F8.5` render open turn live state from `turn.status`
- `F8.6` add legacy fallback handling

### Testing

- `T9.1` deriver unit tests
- `T9.2` replay versus incremental equivalence tests
- `T9.3` storage tests
- `T9.4` repair and migration tests
- `T9.5` API tests
- `T9.6` UI component tests
- `T9.7` visual regression fixtures

## Dependencies

Hard dependencies:

1. current Codex transport turn slicing must remain stable
2. shutdown safe storage writes must remain intact
3. rollback invariants must survive new derived writes

Sequencing:

1. Phase 0 before everything else
2. Phase 1 before Phase 2
3. Phase 2 before Phases 3 and 4
4. Phase 4 before Phase 5
5. Phase 6 depends on Phases 3, 4, and 5
6. Phase 7 after Phase 5
7. Phase 8 after Phase 7
8. Phase 9 runs throughout and locks in at the end

## Risks

### Risk 1. Upstream frame schema shifts

If Codex changes terminal or item completion markers, derivation misclassifies the turn.

Mitigation:

1. isolate frame classification
2. test against captured real fixtures
3. keep websocket close interruption handling conservative

### Risk 2. Replay and incremental advance diverge

One path says a turn has one set of events, the other says something else.

Mitigation:

1. define explicit cursor semantics
2. assert byte equivalence in tests
3. keep event emission rules narrow and deterministic

### Risk 3. Derived artifacts drift from canonical transport

An operator sees a timeline that cannot be explained from the wire record.

Mitigation:

1. require `transport_ref.message_index` on frame derived events
2. keep local lifecycle events narrowly defined
3. make repair derive only from canonical transport plus explicit local metadata inputs

### Risk 4. Legacy archive behavior regresses

Old exchanges fail to load or render.

Mitigation:

1. keep derived reads optional
2. keep transport fallback intact
3. test missing file paths explicitly

### Risk 5. UI reimplements backend parsing

Frontend starts scraping raw payloads to fill modeling gaps.

Mitigation:

1. keep all parsing in backend deriver
2. expose typed summary and typed events
3. treat transport parsing in `www/` as a review failure

### Risk 6. Open turn UX regresses

Removing provisional event rows makes live state feel dead.

Mitigation:

1. model provisional state at the turn level
2. drive live UI from open turn summary plus transport backed live state
3. keep transport tab available for true streaming detail

## Done Criteria

This work is complete when all of the following hold:

1. Codex exchanges persist `transport.json`, `events.jsonl`, and `turn.json`
2. `events.jsonl` contains only turn scoped semantic events
3. `turn.json` carries `derivation_version` and correct range invariants
4. replay and incremental advance serialize identically for the same inputs
5. exchange detail API returns `transport`, `events`, and `turn`
6. semantic timeline is the default Codex detail view
7. legacy exchanges still render safely
8. repair and migration paths exist
9. fixtures lock single turn success, multi turn success, failed, interrupted, handshake failure, dropped initial frame, breakpoint edited, and tool result only continuation paths

## Recommended First Slice

If this is implemented incrementally, the first useful slice is:

1. Phase 1 models
2. Phase 2 derivation contract
3. Phase 3 pure deriver against fixtures
4. Phase 9 equivalence tests
5. minimal API exposure from in memory derivation behind a flag

Persisted derived artifacts should come only after the event vocabulary and replay contract are proven. That keeps bad semantics out of disk format and UI code.
