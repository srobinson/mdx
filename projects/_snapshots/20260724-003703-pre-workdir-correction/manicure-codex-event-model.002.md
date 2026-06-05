---
title: Manicure Codex Event Model
type: projects
tags: [manicure, codex, transport, events, architecture]
summary: Event model for ChatGPT-authenticated Codex exchanges. Transport is the only source of truth; everything else is derived.
status: active
project: manicure
confidence: high
created: 2026-04-19
updated: 2026-04-19
parent_issue: ALP-1815
predecessor: manicure-codex-event-model.001.md
---

# Manicure Codex Event Model

## Predecessor

This supersedes `manicure-codex-event-model.001.md`. The prior version proposed a similar two-layer shape but got three things wrong that this revision fixes:

1. It treated the client `response.create` frame as *the* turn boundary. In practice a turn has two boundaries: a start (client `response.create`) and an end (server `response.completed` / `response.failed`). Conflating them is the root of ALP-1846.
2. It proposed deferring persistence of derived events until turn finalization. For a debugging tool this is the wrong default; crash-before-finalize loses everything the transport layer just captured.
3. It promoted deltas (`assistant_text_delta`, `tool_call_arguments_delta`, `assistant_reasoning_delta`) into the semantic event layer. Deltas are transport facts. Promoting them to semantics retranscribes `transport.json` and forces operators to scroll through hundreds of low-value events.

The core architectural intuition — raw transport canonical, semantics derived — is preserved and is the foundation of this document.

## One-Sentence Summary

Manicure Codex exchanges are modeled as an ordered stream of **turns** on a persistent **transport session**, where `transport.json` is the only source of truth and every other artifact is a pure function of it plus proxy lifecycle hooks.

## What Codex Actually Is On The Wire

A Codex session is a single persistent websocket to `wss://chatgpt.com/backend-api/codex/responses`. Within that session:

- The client sends a `response.create` frame to start a turn.
- The server emits a stream of typed frames: item additions, text and reasoning deltas, tool-call payloads, tool-call argument deltas, item completions, and a terminal `response.completed` or `response.failed` frame.
- The client may submit tool outputs on the same session as part of a later turn.
- The websocket eventually closes — cleanly, abruptly, or mid-turn.

Two facts drive the whole design:

1. **Turns are sub-session objects.** One connection, many turns.
2. **Turns have a start frame and a terminal frame, both explicit.** Anything that assumes a single boundary will produce one-turn-lag bugs (ALP-1846) or persistence-on-shutdown-only bugs (ALP-1845).

## Core Principles

### 1. Transport Is Canonical

`transport.json` records every frame — direction, raw bytes, parsed JSON, drop state, timestamps. It is append-only within a session and immutable once the exchange is finalized. No derived artifact may replace, rewrite, or reinterpret it.

### 2. Everything Else Is Derived By A Pure Function

A single pure deriver takes `(TransportArtifacts, request curation metadata, breakpoint lifecycle)` and returns `(events, turn summary)`. No storage, no network, no mutation of inputs. If the deriver changes, old exchanges re-derive identically from the same `transport.json`.

### 3. Turn Boundaries Are Two-Sided

Every turn has:

- A **start boundary** — the client `response.create` frame.
- A **terminal boundary** — the first of: server `response.completed`, server `response.failed`, or websocket close.

Both boundaries trigger observable lifecycle events. Both are detection points in code. Collapsing them causes bugs.

### 4. Provisional State Is First-Class

Within a turn, output is provisional until the terminal boundary. The model must name provisional state rather than hide it. The UI shows provisional output immediately; the storage layer commits it on terminal boundary.

### 5. Derived Artifacts Are Written Append-Only, Not Deferred

`events.jsonl` is written as events are derived, not held in memory until the turn finalizes. If the process dies mid-turn, the partial event log plus `transport.json` still reconstruct the session. Final status flips happen via a small `turn.json` rewrite at the terminal boundary, not by holding the whole event stream hostage.

### 6. Every Derived Event References Its Transport Frame

Every event derived from a websocket frame carries `transport_ref.message_index`. This is the invariant that keeps the semantic layer and forensic layer linked forever.

### 7. Small Semantic Vocabulary

The event taxonomy stays short and operational. Deltas live in transport, not in events. If operators later ask for delta-level semantics, we add them; we cannot remove them without breaking consumers.

## Domain Model

### TransportSession

One websocket lifetime. Used for diagnostics and for tying multiple turns to the same connection.

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

The primary product-level unit. One turn is one exchange in today's storage model.

- `turn_id`
- `exchange_id`
- `session_id`
- `turn_index` — 0-based position in the session
- `request_message_index` — transport index of the client `response.create` frame
- `completion_message_index` — transport index of the terminal server frame, or null if interrupted
- `message_range_start`
- `message_range_end`
- `model`
- `status` — `open`, `completed`, `failed`, `interrupted`
- `stop_reason` — present on `completed` or `failed`
- `text_chars` — total assistant text committed at terminal boundary
- `tool_calls` — count of completed tool calls
- `started_at`
- `ended_at`

Note: `abandoned` from v1 is dropped. A turn that never reached a terminal frame is `interrupted`, which is more truthful and fewer states.

### SemanticEvent

Ordered, append-only within a turn. Small vocabulary.

Envelope:

```json
{
  "event_id": "evt_000017",
  "exchange_id": "ex_123",
  "session_id": "ws_abc",
  "turn_id": "turn_002",
  "seq": 17,
  "ts": "2026-04-19T10:14:03.221Z",
  "source": "client|server|proxy",
  "kind": "turn_started",
  "status": "provisional|committed",
  "transport_ref": { "message_index": 23 },
  "data": {}
}
```

## Event Taxonomy (V1)

Intentionally terse. Deltas are excluded — they live in `transport.json`.

### Session lifecycle

- `transport_upgrade_request` — client sent upgrade
- `transport_upgrade_response` — server accepted or rejected upgrade
- `websocket_closed` — session ended, with close code and reason

### Turn lifecycle

- `turn_started` — client `response.create` captured
- `request_curated` — proxy modified the outbound payload
- `breakpoint_paused` — turn held pending operator release
- `breakpoint_released` — operator released (edited or unedited)
- `turn_finalized` — terminal boundary reached; status populated

### Assistant output

- `assistant_item_completed` — one committed item of assistant text or reasoning output (rolled up from the server's streaming deltas)

### Tool activity

- `tool_call_completed` — one resolved tool call (rolled up from `function_call` / `custom_tool_call` stream including argument deltas)
- `tool_output_submitted` — client submitted tool output on the session

### Terminal

- `response_completed` — server terminal frame, success
- `response_failed` — server terminal frame, failure

That is the complete V1 vocabulary. Fifteen event kinds.

## Mapping Rules

The deriver walks `transport.json` once per turn and emits events. Rules are deterministic.

### Start boundary

On client `response.create`:

- emit `turn_started`
- if proxy curation ran, emit `request_curated`
- if breakpoint paused, emit `breakpoint_paused` then `breakpoint_released`

### Streaming window

While walking server frames between start and terminal:

- accumulate text/reasoning deltas per item; emit `assistant_item_completed` when the server emits `response.output_item.done` (or equivalent item-completion marker)
- accumulate tool-call argument deltas per call id; emit `tool_call_completed` on resolution

No events are emitted for individual deltas. Deltas remain visible in the transport view.

### Terminal boundary

On server `response.completed`:

- emit `response_completed`
- emit `turn_finalized` with `status=completed`

On server `response.failed`:

- emit `response_failed`
- emit `turn_finalized` with `status=failed`

On websocket close before either terminal frame:

- emit `websocket_closed`
- emit `turn_finalized` with `status=interrupted`

### Drop and handshake-failure paths

If the initial client frame was dropped by a breakpoint, the turn never begins: no turn events, no `turn.json`. The transport upgrade events still emit.

On handshake failure (no websocket established), only `transport_upgrade_request` and `transport_upgrade_response` emit.

## Persistence Shape

### Canonical (unchanged)

- `request.raw`
- `request.ir.json`
- `request.curated.raw`
- `request.curated.ir.json`
- `request.audit.json`
- `transport.json`
- `response.raw` — handshake-failure bodies only

### Derived (new)

- `events.jsonl` — one event per line, `seq`-ordered, append-only while the turn is open
- `turn.json` — single summary document; written on first event, rewritten on `turn_finalized`

`events.jsonl` is written as events are derived, not held until finalization. If the process dies mid-turn, the last persisted event plus `transport.json` still fully reconstruct what happened.

## API Shape

Exchange detail response gains:

- `transport` — existing raw artifact (unchanged)
- `events` — derived semantic event list
- `turn` — derived turn summary

List endpoints use `turn.status`, `turn.stop_reason`, `text_chars`, `tool_calls` for display without loading transport.

## UI Implications

- Exchange list: turn status, stop reason, text char count, tool-call count
- Detail default view: semantic event timeline
- Detail Inspect / Transport tab: raw frame view (existing)
- Each event in the timeline deep-links to its transport frame via `transport_ref.message_index`

Operators never need to read raw frames unless they're debugging transport itself.

## Relationship To Open Sub-Issues

- **ALP-1846** (finalize on server-side response completion) implements Principle 3 in the transport layer. That work produces the exact terminal-boundary detection this document assumes. Land ALP-1846 first; its detection logic is the deriver's terminal-boundary input.
- **ALP-1845** (shutdown finalization) is orthogonal and already landed. The storage-executor fix keeps the deriver write path viable during shutdown.
- **ALP-1832 / ALP-1833** (provisional exchange per turn) already match Principle 2's "derived by pure function" shape — they just need the deriver plugged in.

## Implementation Plan

### Phase 0. Land ALP-1846

The turn-terminal-boundary detection is a prerequisite, not a follow-up. Without it, the deriver has nothing to hook into for `turn_finalized`.

### Phase 1. Models

Pydantic models for `CodexSemanticEvent`, `CodexTurnSummary`, `CodexTransportRef`. Colocate with `TransportArtifacts` in `api/src/manicure/storage/base.py` (or a sibling module). Respect `frozen=True` for IR-style models.

### Phase 2. Pure Deriver

`derive_events(transport, curation, breakpoint_lifecycle) -> (events, turn_summary)`. No I/O. Unit-tested with fixture transport artifacts. Lives under `api/src/manicure/codex/`.

### Phase 3. Incremental Persistence

Wire the deriver into `handle_codex_websocket_message` and the ALP-1846 terminal-boundary hook. Write events to `events.jsonl` as they are derived. Rewrite `turn.json` on `turn_finalized`.

### Phase 4. API Surface

Extend exchange-detail responses with `events` and `turn`. Keep `transport` unchanged for backward compat.

### Phase 5. UI

Default detail view becomes the semantic timeline. Transport tab remains. Timeline entries link to transport frames by `message_index`.

### Phase 6. Fixture Coverage

Lock behavior with fixture-driven tests:

- single-turn success
- multi-turn success
- mid-turn websocket close (interrupted)
- `response.failed` turn
- handshake failure
- breakpoint-edited turn
- dropped initial frame

## Resolved Questions

Promoted from v1's Open Questions section because the answers are load-bearing.

- **Persist derived vs. derive on read.** Persist. This is a debugging product; historical replay must not depend on future parser changes.
- **DAG vs. total order.** Total order, for V1 and likely forever. Operator questions are timeline questions.
- **Session-level archive.** Not added. Exchange-per-turn matches the storage model and operator workflow today.

## Still Open

- **Cross-turn state beyond the session view.** If operators need to trace "which earlier tool output produced this later turn's behavior," we may need a session-scoped event index. Defer until operators ask.
- **Delta retention window.** `transport.json` currently holds every frame forever. If disk grows unreasonably on long sessions, we may downsample deltas after some watermark. Not a V1 concern.
- **Authoritative terminal-marker schema.** ALP-1846 will pin down the exact Codex server frame kinds that count as `response.completed` / `response.failed` / item-completion. This doc defers to that investigation.

## Recommendation

Codex is not request/response. Model it as a transport session carrying an ordered stream of turns, each turn a two-boundary object wrapping a derivable event timeline. Keep `transport.json` canonical. Add `events.jsonl` (append-only) and `turn.json` (rewritten on finalize). Make the deriver pure and fixture-tested. Land ALP-1846 first — it delivers the terminal-boundary detection everything else depends on.
