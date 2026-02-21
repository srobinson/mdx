---
title: Transport Matters: Codex Cross Transport Continuity
type: research
tags: [transport-matters, codex, http-fallback, session-continuity, branch-review, architecture]
summary: Approval note for Codex HTTP fallback continuity. Basic mixed transport exchange capture works, but HTTP fallback turns do not yet preserve Codex session identity, turn identity, turn ordering, or full derived timeline artifacts, so Transport Matters cannot render one coherent Codex thread across WebSocket and HTTP segments.
status: active
created: 2026-05-14
updated: 2026-05-14
project: transport-matters
branch: feat/codex-http-fallback
head: c0bf4c7
related:
  - transport-matters-codex-http-fallback-architectural-review.md
  - transport-matters-codex-http-fallback-review.md
  - transport-matters-codex-http-fallback-review-frontend.md
  - codex-cli-ws-http-fallback-mechanism.md
  - codex-cli-headers-identity-audit.md
confidence: high for branch behavior and identity discrimination; the header-identity audit replaces earlier medium-confidence guesses
reviewed_by:
  - "Claude (Opus 4.7) on 2026-05-14: verified all cited file paths and line numbers against branch HEAD; agreed with diagnosis; tightened test result row, `--force-http-fallback` limitations, fallback-vs-retry turn_index semantics, recommended slice order, and definition of done."
  - "Codex on 2026-05-14: final approval review; added approval ask and thread model; corrected API test verification to 806 passed from a fresh rerun."
  - "Claude (Opus 4.7) on 2026-05-14 (second pass): folded `codex-cli-headers-identity-audit.md` findings; corrected the `x-client-request-id` heuristic (it is session-stable, identical to `thread_id` on both transports); replaced it with `x-codex-turn-metadata` parsed for `turn_id`; tightened Slice C continuity table and test plan; added casing nuance and sub-agent caveat."
  - "Codex on 2026-05-14: revalidated header claims after `/tmp/codex-clone` pull to `12bfb57`; removed defensive underscore-header guidance because this project targets current Codex for one user."
---

# Transport Matters: Codex Cross Transport Continuity

## Executive Diagnosis

The use case is not just "capture Codex HTTP fallback." The use case is that one Codex session can cross transports, and Transport Matters must render that as one coherent Codex thread.

On branch `feat/codex-http-fallback` at `c0bf4c7`, basic exchange capture works. HTTP fallback rows get request and response IR, appear in the index, and render in the frontend list. Existing WebSocket capture remains uncontaminated. What does not work yet is session level continuity across WebSocket and HTTP. The branch captures transport events as separate exchange records, but it does not model the Codex session crossing transports.

The failure mode is specific: HTTP fallback turns get parsed and displayed, but they lose Codex session identity, Codex turn identity, turn sequence, and full derived timeline artifacts.

## Approval Ask

Approve this document as the source of truth for the next implementation slice.

Recommended decision:

1. Treat the current branch as a capture foundation, not as product complete for mixed transport Codex sessions.
2. Approve continuity as the next work, ahead of broader capture polish.
3. Require a scrubbed mixed transport fixture before final merge.
4. Keep WebSocket behavior unchanged unless a line of code directly supports cross transport continuity.

Approval should not mean "merge the current branch as done." It should mean "this is the correct diagnosis and implementation direction."

## Validated Inputs

Local branch review used:

| Input | Value |
|---|---|
| Repo | `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters` |
| Branch | `feat/codex-http-fallback` |
| Head | `c0bf4c7` |
| Live fallback capture | `/Users/alphab/.transport-matters/workspaces/dev-helioy-fmm/6cc7a823/` |
| Capture shape | one WebSocket handshake row plus two HTTP fallback rows |

The live HTTP fallback request bodies carry `client_metadata.x-codex-installation-id` and no request body `session_id`. The two HTTP fallback rows both derive `codex_turn.turn_index = 0`. HTTP fallback rows have no `transport.json`, no `events.jsonl`, and no `turn.json`.

Verification already run on the branch:

| Check | Result |
|---|---|
| `fmm validate` | passed |
| `git diff --check origin/main...HEAD` | passed |
| `cd api && uv run ruff format --check src/` | passed |
| `cd api && uv run ruff check src/` | passed |
| `cd api && uv run mypy src/` | passed |
| `cd api && uv run python -m pytest` | passed, 806 tests |
| `cd www && pnpm typecheck` | passed |
| `cd www && pnpm lint` | passed |
| `cd www && pnpm test` | passed, 347 tests |

## What Works

Basic exchange capture works in mixed transport sessions.

The HTTP fallback request enters the generic HTTP path through `addon_handlers.py`, routes through the Codex adapter, persists a provisional row, finalizes through the HTTP exchange recorder path, and writes request and response IR. The WebSocket capture path remains intact. The frontend list can show the HTTP fallback exchanges because they are normal `IndexEntry` rows with provider `codex`.

The track manager should keep mixed transport rows in the same Transport Matters run and track when they belong to the same launched run and tool chain. That grouping is useful, but it is not Codex session continuity. It does not recover the Codex session id, turn id, or turn sequence.

## Thread Model

A coherent Codex thread does not require physically merging exchange directories.

It does require:

| Requirement | Meaning |
|---|---|
| Same Codex session identity | WebSocket and HTTP turns in one Codex conversation carry the same resolved `thread-id` header (`session-id` is a derived alias of `thread-id` for root CLI sessions) |
| Stable logical turn identity | A failed WS attempt and its HTTP fallback share the same `turn_id` value inside the `x-codex-turn-metadata` JSON header. The same header value also distinguishes that retry from the next logical turn |
| Monotonic turn ordering | A later logical turn gets a later `turn_index`; a fallback retry of the same logical turn keeps the same `turn_index` |
| Transport provenance | Each logical turn can explain which transport segment produced the captured data |
| Normal detail rendering | Each logical turn can expose request IR, response IR, derived Codex events, derived turn summary, and transport diagnostics |

The important distinction is retry versus advance. If HTTP is the fallback for the same logical request, it should inherit the logical turn identity and turn index from the failed WS segment. If HTTP is the next turn after a previous WS turn, it should receive the next turn index in that session.

### Three-case discrimination from headers alone

Verified against `openai/codex` `main` (commit `12bfb57`, 2026-05-14). See `codex-cli-headers-identity-audit.md` for full source citations.

| Case | `thread-id` | `x-codex-turn-metadata.turn_id` |
|---|---|---|
| WS-fail → HTTP-retry of same turn | same | same |
| WS-done → next logical turn | same | different |
| Separate Codex CLI invocation | different | different (irrelevant once `thread-id` differs) |

Minimum discrimination logic:

```
1. If R1.thread-id != R2.thread-id  → separate Codex session (Case 3)
2. Else parse x-codex-turn-metadata JSON; extract turn_id:
   - Same turn_id  → same logical turn, retry (Case 1)
   - Different     → next logical turn (Case 2)
```

Minimum header set required: `thread-id` plus `x-codex-turn-metadata`.

### Corrections to prior assumptions

Three findings from the header audit override earlier guesses in this document and in `codex-cli-ws-http-fallback-mechanism.md`:

1. **`x-client-request-id` is NOT a turn-level discriminator.** Codex sets it to `thread_id` on both transports (`codex-rs/core/src/client.rs:903-904` for WS, `codex-rs/codex-api/src/endpoint/responses.rs:91-92` for HTTP). It is session-stable, identical to `thread-id`. The earlier "match on `x-client-request-id` to link retries" recommendation collapses all turns in a session into one bucket and is not load-bearing. Use `x-codex-turn-metadata.turn_id` instead.

2. **Header names on the wire are kebab-case, not underscored.** Current Codex emits `session-id` and `thread-id`; it does not emit `session_id` or `thread_id` as literal header names (`codex-rs/codex-api/src/requests/headers.rs:8,11`). `transport-matters/api/src/transport_matters/codex/session_metadata.py:41` looking only for the underscored literal will miss the real header. Update the lookup to read the current kebab-case headers. No backward compatibility shim is needed for this project.

3. **`x-codex-installation-id` is body data, not a header on `/responses`.** It lives inside the request body's `client_metadata` map (`client.rs:760-763`). It only appears as a real HTTP header on the `/responses/compact` endpoint (`client.rs:489-490`). The live capture confirms this. Do not look for it in headers on the turn endpoints.

A fourth finding worth noting (not a correction, but an opportunity):

4. **`x-codex-inference-call-id` is fresh per HTTP attempt, HTTP-only** (`codex-rs/rollout-trace/src/inference.rs:343-345`). It gives a free per-attempt discriminator on the HTTP side, useful if the proxy ever needs to dedupe two captures of the same HTTP request.

## Sub-agent caveat

The header audit identifies one important wrinkle for sub-agent flows: `session_id` and `thread_id` are equal for root CLI sessions (`codex-rs/core/src/session/session.rs:811`: `SessionId::from(thread_id)`) but diverge for sub-agents, where `session_id` is inherited from the controlling agent and `thread_id` is fresh. Continuity logic should key on `thread-id`, not `session-id`, to avoid false-grouping sub-agent flows into their parent session. The three-case discrimination matrix above assumes root CLI flows; sub-agent flows add a per-thread isolation requirement that is satisfied by the same `thread-id` key.

## Gap 1: Synthetic Session And Turn Identity

The HTTP fallback request parser only sees request body `client_metadata`.

Relevant code:

| File | Role |
|---|---|
| `api/src/transport_matters/codex/request_parser.py:73` | Parses `data.client_metadata` into request metadata |
| `api/src/transport_matters/codex/request_parser.py:372-388` | Extracts `session_id` only from metadata body fields |
| `api/src/transport_matters/codex/session_metadata.py:38-46` | Centralizes existing Codex session metadata lookup, but currently misses the current wire headers. Update it to read `session-id`, `thread-id`, and `x-codex-turn-metadata`; no underscored header fallback is required |
| `api/src/transport_matters/flow_state.py:29-40` | Stores adapter, request IR, raw body, curated IR, audit, track state, but not request headers |
| `api/src/transport_matters/exchange_recorder.py:219-225` | Calls `derive_codex_http_turn` without headers on new HTTP persist |
| `api/src/transport_matters/exchange_recorder.py:409-415` | Calls `derive_codex_http_turn` without headers on provisional finalize |
| `api/src/transport_matters/codex/http_derivation.py:94-101` | Falls back to `session_id=exchange_id`, `turn_id=exchange_id`, `turn_index=0` |

Headers are available on the mitmproxy flow at capture time. The recorder already reads request headers for auth related token counting. The narrower bug is that HTTP fallback headers are not persisted into a canonical artifact and are not threaded into the HTTP Codex derivation call.

The header audit confirms what specifically needs to be threaded through: `thread-id` (session identity, kebab-case on the wire) and `x-codex-turn-metadata` (per-turn JSON-encoded value carrying `turn_id`). Together they give exact, stateless three-case discrimination. `session_metadata.py` is the right place to centralize this lookup; the gap is that the HTTP fallback persistence path never gives headers to it.

Result: every HTTP fallback turn looks like its own synthetic single turn session to the Codex derivation layer.

## Gap 2: `turn_index` Always Zero

`derive_codex_http_turn` hardcodes `turn_index=0` in `http_derivation.py:98`.

This is the clearest user visible symptom. The frontend list row prefers `entry.codex_turn.turn_index` over its fallback list sequence in `www/src/components/ExchangeTurnCard.tsx:80-83`. Multiple HTTP fallback turns in one session therefore render as repeated `000`, even when they are distinct turns in one Codex conversation.

The root cause is the same as Gap 1. Without real session identity and continuity state, the HTTP derivation code cannot know where the fallback turn sits in the Codex session.

## Gap 3: No Full Derived Artifacts For HTTP Turns

The HTTP fallback branch stores only `CodexTurnListSummary` on the index entry.

Relevant code:

| File | Role |
|---|---|
| `api/src/transport_matters/exchange_recorder.py:215-225` | Derives only `codex_turn_summary` for a new HTTP exchange |
| `api/src/transport_matters/exchange_recorder.py:264-272` | Persists HTTP exchange artifacts without `events` or full `turn` |
| `api/src/transport_matters/exchange_recorder.py:405-415` | Derives only `codex_turn_summary` when finalizing a provisional HTTP exchange |
| `api/src/transport_matters/exchange_recorder.py:443-446` | Updates finalized HTTP artifacts with response raw and response IR only |
| `api/src/transport_matters/storage/base.py:156-158` | `ExchangeArtifacts` can store `transport`, `events`, and `turn`, but HTTP fallback does not populate them |
| `api/src/transport_matters/api/v1/exchanges.py:164-176` | Detail endpoint returns timeline events and turn only from derived artifacts |
| `www/src/components/detail/InspectTab.tsx:240-243` | Codex timeline renders only when both `detail.events` and `detail.turn` exist |

The detail repair path does not currently save HTTP fallback.

`repair_codex_derived_artifacts` can rebuild missing derived artifacts for WebSocket when canonical `TransportArtifacts` exists. HTTP fallback currently has no transport artifact. The repair path therefore reaches `codex_transport_missing` in `api/src/transport_matters/codex/repair.py:222-231` and cannot rebuild a timeline.

Result: opening Inspect on an HTTP fallback exchange shows the request and response IR, but skips `CodexTimeline`.

## Gap 4: No HTTP Transport Provenance Artifact

The original architecture expected the storage protocol to widen from WebSocket only to a protocol union. This branch avoids that by not persisting HTTP transport artifacts.

Current type surface:

| File | Current shape |
|---|---|
| `api/src/transport_matters/storage/base.py:225-230` | `TransportArtifacts.protocol: Literal["websocket"]` with required `upgrade` |
| `www/src/types.ts:356-361` | frontend `TransportArtifacts.protocol: "websocket"` with required `upgrade` |
| `www/src/components/detail/CodexTransportPanel.tsx:96-108` | assumes WebSocket upgrade data |

For exchange level capture this is tolerable. For cross transport thread rendering it is not. The UI needs to show that one Codex thread moved from WebSocket to HTTP, and the backend needs canonical HTTP headers and SSE events for repair and derivation.

The HTTP artifact should not pretend to have a WebSocket upgrade. It should be a protocol variant with HTTP request and response metadata plus parsed SSE message artifacts.

## Gap 5: Live HTTP Codex Pending State

The frontend still treats HTTP Codex provisionals as open but not Codex pending.

Relevant code:

| File | Behavior |
|---|---|
| `www/src/components/ExchangeTurnCard.tsx:217-220` | row is open when `res === null` |
| `www/src/components/ExchangeTurnCard.tsx:221-223` | Codex pending requires `entry.codex_turn?.status === "open"` |

HTTP Codex provisionals have no `codex_turn` until finalization. During the live fallback request, the row does not get the Codex pending behavior.

## Non Blocker: `--force-http-fallback`

The `--force-http-fallback` path is a manual test harness with two limitations worth recording.

First, a query string matcher bug. `force_http_fallback_addon.py:35` checks `path.endswith("/backend-api/codex/responses")` while the production matcher at `transport.py:97` accepts `path == CODEX_RESPONSES_PATH or path.startswith(f"{CODEX_RESPONSES_PATH}?")`. If Codex CLI appends a query string to the upgrade GET, the injector silently misses and the upgrade succeeds. Fix by mirroring the production matcher.

Second, the injector forces HTTP from the first WS upgrade attempt onward. It cannot simulate the real-world failure mode where WS works for turn 1, dies mid-stream, and HTTP takes over for turn 2+. Reproducing that on demand needs a network manipulation tool or a richer injector that gates on a turn counter or a kill-after-N-frames knob.

Neither is a product blocker for session continuity, but the second one is the reason mixed-transport fixture captures cannot be produced from the existing tooling alone.

## Required Design Shift

The next slice should model this explicitly:

> one logical Codex thread, multiple transport segments.

Do not treat HTTP fallback as a special standalone exchange after capture. Treat it as a Codex turn whose transport segment happens to be HTTP SSE instead of WebSocket frames.

That implies three durable identities:

| Identity | Purpose | Source on the wire | Current HTTP fallback state |
|---|---|---|---|
| Codex session id | Groups turns into one Codex conversation across transports | `thread-id` request header (kebab-case; sub-agents may distinguish from `session-id`) | header not snapshotted; falls back to synthetic `exchange_id` |
| Codex turn id | Identifies a logical turn (stable across retries within the turn) | `x-codex-turn-metadata` header value, JSON-decoded `turn_id` field | header not snapshotted; falls back to synthetic `exchange_id` |
| Codex turn index | Orders turns in the session | derived by transport-matters from the sequence of distinct `turn_id` values seen per `thread_id` | hardcoded `0` |

It also implies one transport provenance model:

| Segment | Required artifact |
|---|---|
| WebSocket | existing upgrade, close, and frame messages |
| HTTP fallback | method, URL, request headers, response status, response headers, client request payload, server SSE payload messages |

## Concrete Remediation Slice

### Slice A: Persist HTTP Transport Artifacts

Widen `TransportArtifacts` into a protocol union.

Minimum backend shape:

```python
type TransportArtifacts = WebSocketTransportArtifacts | HttpTransportArtifacts
```

The HTTP variant needs:

| Field | Purpose |
|---|---|
| `provider="codex"` | preserve provider scoped rendering |
| `protocol="http"` | discriminate frontend and repair behavior |
| `request.method`, `request.scheme`, `request.host`, `request.path` | provenance |
| `request.headers` | session metadata, request id, account context, diagnostics |
| `response.status_code`, `response.headers` | provenance and diagnostics |
| `messages` | client request payload plus parsed server SSE payloads |

Use the existing `TransportMessageArtifact` for HTTP messages:

| Message | Direction | Payload |
|---|---|---|
| request body | `client` | parsed request JSON with synthetic `type: response.create` only in the artifact, not on the wire |
| each SSE `data:` payload | `server` | parsed JSON payload |

Extend header redaction for the HTTP variant. Persisting headers must reuse the existing redaction posture for authorization, cookies, session ids, account ids, and other sensitive values.

### Slice B: Derive And Persist Full HTTP Codex Artifacts

Replace or supplement `derive_codex_http_turn` with a function that returns full `CodexDerivedTurnArtifacts`.

Suggested shape:

```python
def derive_codex_http_artifacts(
    *,
    exchange_id: str,
    raw_request: bytes,
    raw_response: bytes,
    request_headers: HeaderLookup,
    model: str,
    ts: datetime,
    continuity: CodexTurnContinuity,
) -> CodexDerivedTurnArtifacts | None:
    ...
```

Then persist:

| Storage field | Source |
|---|---|
| `IndexEntry.codex_turn` | `CodexTurnListSummary.from_turn(derived.turn)` |
| `ExchangeArtifacts.events` | `derived.events` |
| `ExchangeArtifacts.turn` | `derived.turn` |
| `ExchangeArtifacts.transport` | HTTP transport artifact from Slice A |

This lets `api/v1/exchanges.py` return `detail.events` and `detail.turn` for HTTP fallback rows. `InspectTab` then renders `CodexTimeline` without a frontend special case.

### Slice C: Add Codex Continuity State

Add a process local continuity component shared by WebSocket and HTTP Codex paths.

Responsibilities:

| Responsibility | Detail |
|---|---|
| Resolve thread identity | Snapshot the `thread-id` header from `flow.request.headers`. This is the per-CLI-invocation key; everything else is derived from it. |
| Resolve session identity | For root CLI sessions, `session-id` equals `thread-id`. For sub-agents they diverge. Read `session-id` (kebab-case) when present; fall back to `thread-id`. Both are session-lifetime stable. |
| Resolve turn identity | Snapshot `x-codex-turn-metadata`. Parse the value as JSON; extract `turn_id` (which Codex sets to `sub_id`, see `codex-rs/core/src/turn_metadata.rs:181-264` and `session/turn_context.rs:575-587`). This is the per-logical-turn key. |
| Allocate turn index | Maintain a `dict[thread_id, (last_turn_id, next_turn_index)]` per process. On each captured request: if `thread_id` is new, initialize state at `next_turn_index=0`; if `turn_id` matches `last_turn_id`, this is a retry and reuses `next_turn_index - 1`; if `turn_id` is different, increment `next_turn_index` and emit it for the new turn. |
| Record completed turns | Both WS and HTTP finalize paths update the same continuity state through this single API. The existing `CodexTransportState.next_turn_index` (per-WS-flow) is replaced by the per-`thread_id` counter. |
| Discriminate retry from advance | Pure header comparison: same `thread_id` + same `turn_id` → retry, reuse `turn_index`. Same `thread_id` + new `turn_id` → next turn, increment. Different `thread_id` → new session, reset state. No flow correlation, no time windows, no WS-close tracking required. |
| Bonus per-attempt key (HTTP only) | `x-codex-inference-call-id` is fresh per HTTP attempt (UUID v4, `codex-rs/rollout-trace/src/inference.rs:343-345`). Useful for proxy-side dedupe; not load-bearing for turn-index allocation. |

The existing WebSocket `CodexTransportState.next_turn_index` is scoped to one WebSocket flow. That is not enough for transport crossing. The continuity state must be keyed by `thread_id` and updated by both transport paths through one shared API.

If `x-codex-turn-metadata` is absent or unparseable (e.g., older Codex versions, malformed header), the system can still capture the exchange, but it should mark the derived continuity as lossy rather than silently presenting `exchange_id` as the real turn identity. The presence of `thread-id` alone is enough to discriminate Case 3 (separate sessions); only the retry-vs-advance discrimination degrades when `x-codex-turn-metadata` is unavailable.

### Slice D: Frontend Updates

Widen frontend types to match the backend union.

Required frontend updates:

| File | Change |
|---|---|
| `www/src/types.ts` | `TransportArtifacts` becomes websocket or HTTP protocol union |
| `www/src/components/detail/CodexTransportPanel.tsx` | render HTTP request and SSE events without WebSocket upgrade assumptions |
| `www/src/components/ExchangeTurnCard.tsx` | treat `provider === "codex" && res === null` as Codex pending even without `codex_turn` |

The timeline itself should not need an HTTP branch if Slice B persists normal Codex derived events and turns.

## Recommended Implementation Order

Slice C is the load-bearing fix for the stated user need: mixed transport session as one coherent Codex thread. It is the smallest unit that unbreaks the visible symptom: synthetic session ids and `turn_index=0` collisions. C can be implemented before A and B by threading live HTTP headers into derivation and maintaining process local continuity state. Until A and B land, HTTP turns can still skip the full derived timeline.

Slice A and B unlock the Inspect-tab `CodexTimeline` for HTTP turns and provide the canonical headers a richer repair path needs. They should land after C unless an InspectTab regression takes priority.

The pending row part of Slice D can land anytime. The protocol union and `CodexTransportPanel` branch should follow Slice A, because the frontend type should match the backend artifact shape.

Suggested order:

1. Slice C continuity state and real identity threading.
2. Slice D pending row hardening.
3. Slice A HTTP transport artifacts.
4. Slice B full HTTP derived artifact persistence and repair.
5. Slice D protocol union and transport panel rendering.

## Test Plan

Backend tests:

| Test | Assertion |
|---|---|
| HTTP fallback matcher | `POST /backend-api/codex/responses` matches; WebSocket `GET` does not enter HTTP path |
| Thread identity extraction | HTTP fallback with `thread-id` derives real `turn.session_id` |
| Turn metadata extraction | HTTP fallback with `x-codex-turn-metadata` (JSON-encoded) derives real `turn.turn_id` from the parsed `turn_id`/`sub_id` field |
| Two HTTP turns same session | derived `turn_index` increments on each new `turn_id` instead of repeating `0` |
| WS then HTTP same session | HTTP turn index continues from the last WS turn (shared `thread_id` continuity state) |
| WS failed attempt then HTTP fallback same turn | matching `turn_id` from `x-codex-turn-metadata` reuses the same `turn_index`; treated as transport segment of the existing turn, not a new turn |
| Separate Codex sessions in one run | different `thread-id` values produce independent continuity state; turn indices do not bleed across sessions |
| Sub-agent flows | sub-agent thread (`session-id != thread-id`) is keyed on `thread-id`, isolated from parent session continuity |
| Missing `x-codex-turn-metadata` | continuity falls back to per-`thread_id` turn counter; emitted continuity is marked lossy in derived artifacts |
| HTTP artifact persistence | finalized HTTP fallback exchange has `transport.protocol == "http"` |
| Full derived persistence | finalized HTTP fallback exchange has `events` and `turn` |
| Detail endpoint | HTTP fallback detail returns `events`, `turn`, and supported derived artifact state |
| Repair path | missing HTTP derived artifacts can rebuild from HTTP transport messages |
| Redaction | HTTP persisted headers redact sensitive values |
| Force harness | query string path still triggers `--force-http-fallback` |

Frontend tests:

| Test | Assertion |
|---|---|
| HTTP transport panel | renders HTTP metadata and SSE messages |
| HTTP Codex timeline | Inspect shows `CodexTimeline` when detail has events and turn |
| HTTP pending row | pending Codex HTTP row gets Codex pending behavior |
| Mixed list sequence | WS and HTTP turns render increasing turn numbers |

Fixture test:

Use the real fallback capture as a fixture or produce a scrubbed derivative. The fixture should include:

| Artifact | Reason |
|---|---|
| WebSocket segment before fallback | proves continuity from WS |
| Failed or aborted WS attempt | proves fallback boundary |
| HTTP fallback request headers | proves session and request id extraction |
| HTTP request body | proves Codex request parser compatibility |
| HTTP SSE response body | proves parser and timeline derivation |

## Definition Of Done

This feature is done when:

1. A Codex session that starts on WebSocket and later falls back to HTTP renders as one coherent thread: identical Codex `session_id` (resolved from `thread-id`) on every turn, monotonic `turn_index` derived from distinct `x-codex-turn-metadata.turn_id` values, all turns grouped under one transport-matters `track_id`, one `CodexTimeline` panel per logical turn.
2. HTTP fallback turns preserve real session identity from the `thread-id` header and real turn identity from the `x-codex-turn-metadata` header.
3. HTTP fallback turns do not repeat `turn_index=0` in one session. Two HTTP turns with different `turn_id` produce different `turn_index`; an HTTP retry of a failed WS turn (same `turn_id`) reuses the WS turn's `turn_index`.
4. HTTP fallback detail view shows the Codex semantic timeline.
5. The transport tab shows HTTP provenance and SSE messages without WebSocket language.
6. Existing WebSocket capture and timeline behavior remains unchanged.
7. A scrubbed live fallback fixture protects the behavior in tests.

## Merge Readiness Assessment

The current branch is a strong capture foundation but is not merge ready for the stated product use case. It proves that HTTP fallback can be admitted additively and parsed without destabilizing WebSocket capture. It does not yet provide the identity, sequencing, transport provenance, or derived artifacts required to render a mixed transport Codex session as one coherent thread.

The next work should target continuity, not broader capture.
