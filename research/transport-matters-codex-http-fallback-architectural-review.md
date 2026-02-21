---
title: Transport Matters — Codex HTTP Fallback Architectural Review
type: research
tags: [transport-matters, codex, http-fallback, architecture, slice-plan]
summary: Synthesized architectural review for additively supporting Codex's WS→HTTPS Responses fallback transport. Integrates Python backend, frontend (www), and Codex CLI internals findings into one slice plan with file:line specificity and explicit leverage from the existing Anthropic HTTP path.
status: review
created: 2026-05-13
project: transport-matters
related:
  - transport-matters-codex-http-fallback-review.md
  - transport-matters-codex-http-fallback-review-frontend.md
  - codex-cli-ws-http-fallback-mechanism.md
confidence: high (architectural plan); medium (wire-format claims pending live capture)
---

# Transport Matters: Codex HTTP Fallback — Architectural Review

## Foundation

The fallback is closer to free than the surface suggests. The Codex WebSocket and HTTPS Responses transports differ on the smallest possible surface area: same host, same path, only scheme and HTTP method discriminate them. The streaming format on the HTTP side is plain SSE — the same SSE plumbing already in production for the Anthropic `/v1/messages` path. The Python backend's request parsing, provisional-and-finalize exchange machinery, and turn derivation engine are all already wire-format-neutral. The frontend's Codex rendering stack keys off `provider === "codex"`, not transport, and inherits cleanly. The remaining work is dispatch glue and one type widening on each side.

Three layers preserve, three layers extend, one layer is genuinely new.

| Layer | Disposition |
|---|---|
| WS capture path (`adapter.py`, lifecycle hooks, websocket frame parser) | **Preserve.** Untouched. |
| Anthropic HTTP path (`addon_handlers.py`, SSE plumbing, exchange_recorder) | **Preserve and leverage.** Becomes the model for Codex HTTP. |
| Request parser (`parse_codex_request`) | **Already neutral.** No change. |
| Exchange recorder HTTP provisional-and-finalize | **Already neutral.** No change. |
| Turn derivation engine | **Already neutral** (consumes `CodexTransportMessageFact`, not WS frames). No change for Slice 1. |
| Adapter dispatch (matcher, route gates) | **Extend.** This is where most of the Slice 1 work sits. |
| Storage protocol literal | **Widen.** Single-site change in production code. |
| Frontend type and one panel branch | **Widen + branch.** Most of the rendering surface inherits unchanged. |
| Codex HTTP SSE parser (Slice 2) | **Net new.** Deferred. |

## Cross-layer findings that resolve the open questions

The three reports raised seven questions across layer boundaries. Six resolve cleanly once the findings sit side by side. The seventh is the only thing that needs live wire capture before merging.

### Resolved by the Codex internals research

**Q: Should `TransportArtifacts` model `upgrade` / `close` as optional or as a discriminated union?**
**A: Discriminated union.** Codex HTTP genuinely has no upgrade handshake, no close frame, no `response.processed` ack frames. These artifacts are WS-only by physics, not by convention. The frontend report and the Python review both prefer the union; the internals research confirms it is the honest shape.

**Q: Where does the matcher discriminate WS-Codex from HTTP-Codex?**
**A: HTTP method + path, with header absence as a check.** WS upgrade is `GET` to `/backend-api/codex/responses` with `Upgrade: websocket`. HTTP fallback is `POST` to the same path with `Accept: text/event-stream`. The new `is_codex_http_responses_flow` predicate is a path-match + method-match + upgrade-header-absence triple. Robust.

**Q: How does the frontend stitch a WS-half and HTTP-half of one logical conversation?**
**A: `x-client-request-id` header.** It carries across the WS→HTTP transition. Slice 1 does not need to stitch (each capture is rendered as its own exchange), but the join key exists for when stitching becomes a feature.

### Resolved by the Python review

**Q: For HTTP Codex flows, does `provisional_exchange_id` follow the WS path or the Anthropic HTTP path?**
**A: Anthropic HTTP path.** The HTTP provisional-and-finalize plumbing in `exchange_recorder.py` is already provider-agnostic. HTTP Codex inherits it by routing through `_persist_http_exchange`. The frontend's `BreakpointEditorActions.ts` HTTP branch already does the right thing.

**Q: What is the blast radius of widening `protocol: Literal["websocket"]` to `Literal["websocket", "http"]`?**
**A: Effectively zero.** The only production-code usage of the literal is its definition at `storage/base.py:227`. Every other hit is test fixtures. No production branch reads the field. Mechanical widening.

### Resolved by the frontend review

**Q: Which surfaces inherit for free, which need branches?**
**A: Free**: `ExchangeCard`, `SystemSection`, `ToolsSection`, `MessagesSection`, `ContentBlocks`, `TransportDiagnostics`, `buildSyntheticOverrides`. **Branches**: `CodexTransportPanel.tsx:96-108,176` (WS-specific upgrade/path reads) and `ExchangeTurnCard.tsx:221` (pending-state classification).

### Unresolved — needs live capture

**Q: Are the wire-format claims (SSE event shape, header presence, body envelope) accurate against a real fallback?**
**A: Unknown.** Every wire-format claim in the internals research is sourced from the Codex CLI Rust source. That source is authoritative for what Codex CLI sends, but transport-matters needs to confirm it is what mitmproxy observes. **Capturing one real fallback transcript is a hard prerequisite for Slice 1 merge.**

## Slice 1 — concrete edits

Total surface: nine edits across Python and frontend. All surgical. Every line traces to enabling additive Codex HTTP capture without disturbing the WS path.

### Python (seven edits, all in `api/src/transport_matters/`)

| # | File | Change | Risk |
|---|---|---|---|
| 1 | `codex/transport.py` | Add `is_codex_http_responses_flow(flow)` — path + POST + upgrade-header-absence | Low. New predicate, no callers yet. |
| 2 | `codex/adapter.py` | Widen `CodexAdapter.matches` to accept both WS and HTTP discriminators | Low. OR composition. |
| 3 | `addon_handlers.py:68` | Invert `/v1/messages` gate in `handle_http_request` to also admit Codex HTTP | Medium. Touches the HTTP request hot path. Needs assertion that non-LLM HTTP still falls through. |
| 4 | `addon_handlers.py:282` | Branch `handle_response`: Codex HTTP routes to `_persist_http_exchange` (the Anthropic path), not `_persist_codex_handshake_failure` | Medium. The branching condition must be tight. |
| 5 | `addon.py:86` | Update `addon.error` guard to clean up Codex HTTP provisionals | Low. Mirror of existing Anthropic cleanup. |
| 6 | `storage/base.py:225-230` | Widen `TransportArtifacts.protocol` to `Literal["websocket", "http"]`; convert `upgrade` / `close` to discriminated union by protocol | Low in production; medium for tests (fixtures will need updating). |
| 7 | `addon_handlers.py` (existing `_persist_codex_handshake_failure`) | Leave WS-only. HTTP failures route through the generic HTTP error path. | Decision, not code. |

### Frontend (two edits in `www/src/`)

| # | File | Change | Risk |
|---|---|---|---|
| 8 | `types.ts:358` | Widen `protocol: "websocket"` to `"websocket" \| "http"` on `TransportArtifacts`; convert `upgrade` to discriminated-union-optional matching backend | Low. TypeScript will surface every dependent site. |
| 9 | `CodexTransportPanel.tsx:96-108,176` | Add `protocol === "http"` branch; emit SSE event summary or `JsonView` fallback for minimum ship; remove "No websocket frames captured" message for HTTP rows | Low. Self-contained component. |

### One frontend hardening item that crosses the boundary

`ExchangeTurnCard.tsx:221` currently classifies HTTP Codex pending rows as neither Claude-pending nor Codex-pending. Two equivalent fixes:

- **Backend-side**: populate a minimal `codex_turn` for HTTP rows at request capture. The internals research confirms the HTTP body carries the full `ResponsesApiRequest`, so a minimal turn can be derived synchronously.
- **Frontend-side**: relax the guard to treat `provider === "codex"` as Codex-pending regardless of `codex_turn` presence.

**Recommendation: frontend-side.** It is one line, it costs zero backend complexity, and it correctly handles the Slice 1 reality that HTTP Codex rows arrive without WS-derived turn timelines. The backend minimal-turn approach is reserved for Slice 2 when SSE derivation is in place.

## Leverage from the Anthropic HTTP path — what we explicitly do not reinvent

These are the components the Codex HTTP path consumes as-is. Every item below is a "do not write this twice" marker.

| Surface | Component | Why it works for Codex HTTP |
|---|---|---|
| Backend request capture | The generic HTTP request capture in `handle_http_request` | Already streams bodies, persists provisionals, supports breakpoint editing. Codex HTTP differs only by URL pattern, which the matcher widening handles. |
| Backend SSE response handling | The Anthropic SSE chunk reader | Codex HTTP uses identical `text/event-stream` framing. Same plumbing applies. |
| Backend exchange persistence | `_persist_http_exchange` and `exchange_recorder` HTTP path | Provider-agnostic. Routes by adapter, not by transport. |
| Frontend exchange shell | `ExchangeCard`, `SystemSection`, `ToolsSection`, `MessagesSection`, `ContentBlocks` | Keys on `provider === "codex"`, which stays true for HTTP. |
| Frontend overrides | `buildSyntheticOverrides` | Operates on request shape, not transport shape. |
| Frontend breakpoint UX | `BreakpointEditorActions.ts:38-45` HTTP branch | Already discriminates by transport. Codex HTTP inherits the Anthropic HTTP semantics here. |

Six load-bearing components reused. The Slice 1 footprint is intentionally small because of this leverage.

## Slice 2 — the deferred seam

Full turn-timeline parity for Codex HTTP requires parsing the SSE event stream into the same `CodexTransportMessageFact` records the WS path produces. The seam is `codex/exchange_derivation.py:132-154` — `_codex_transport_message_facts`. Once each parsed SSE event becomes a `TransportMessageArtifact`, the derivation engine consumes it without modification.

Slice 2 is one new file (the SSE parser) and zero changes to the engine. Deferred deliberately so Slice 1 can ship as soon as a real fallback transcript validates the matcher.

## Prerequisites before Slice 1 implementation

1. **Capture one real WS→HTTP fallback transcript.** Force a fallback by killing connectivity mid-stream, or simulate one. This is the single hard gate. Every wire-format claim in this review is sourced from the Codex Rust source and is unverified against mitmproxy's view. (Internals research, open question 1.)
2. **Verify `x-client-request-id` propagation in the capture.** Confirmed in source; needs visual confirmation in the captured headers.
3. **Decide the test fixture strategy.** Widening `Literal["websocket", "http"]` will force fixture updates. Either generate fixtures from the captured transcript or hand-author parallel HTTP fixtures alongside existing WS ones.

## Open questions worth raising before code

- **Cookie / `ChatGPT-Account-Id` propagation across the fallback.** Probable but unverified. (Internals research, open question 1.)
- **`x-codex-turn-state` header presence on the HTTP path.** Unknown. (Internals research, open question 2.)
- **Image-generation turn sub-path.** Codex issue #19643 implies same `/responses` path; one capture would confirm. (Internals research, open question 3.)
- **fmm DB path resolution for the api subdirectory.** The Python review agent noted fmm resolved to `~/Dev/LLM/DEV/helioy/.fmm.db` instead of `~/Dev/LLM/DEV/helioy/transport-matters/api/.fmm.db`. Operational, not architectural, but worth fixing for future analyses.

## Source reports

- Python backend deep dive: `~/.mdx/research/transport-matters-codex-http-fallback-review.md`
- Frontend deep dive: `~/.mdx/research/transport-matters-codex-http-fallback-review-frontend.md`
- Codex CLI internals research: `~/.mdx/research/codex-cli-ws-http-fallback-mechanism.md`
