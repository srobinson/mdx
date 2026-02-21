---
title: "Transport Matters: Codex HTTP Fallback — Architectural Review (Frontend)"
type: research
tags: [transport-matters, codex, http-fallback, frontend, www, react, architecture-review]
summary: Frontend impact of widening Codex transport from websocket-only to {websocket, http}; www/ is the load-bearing surface, desktop/ is Electron shell only. One narrow type widening plus one provider+protocol switch unlock Slice 1 with full WebSocket parity untouched.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-13
updated: 2026-05-13
---

# Transport Matters: Codex HTTP Fallback — Architectural Review (Frontend)

## Foundation

`www/` is the entire product UI. `desktop/` is an Electron shell with no view layer (window lifecycle, preload bridge, backend process supervision). Every Codex display change lives in `www/src/`.

The widening is **smaller than it looks**. The frontend already has a discriminated transport seam at `PausedFlow.transport: "http" | "websocket"` (`www/src/types.ts:489`) used by the breakpoint flow, and a provider-scoped switch at `ExchangeDetail.tsx:364` that gates the Codex-specific panel. The only structurally load-bearing literal is `TransportArtifacts.protocol: "websocket"` (`www/src/types.ts:358`). Widen that, branch `CodexTransportPanel`'s rendering by `transport.protocol`, and Slice 1 ships. The WebSocket display path is untouched because every existing call site reads either `transport.provider === "codex"` (still true) or assumes Codex implies websocket (Slice 1 keeps that assumption defensible by gating timeline rendering on the presence of `detail.events` and `detail.turn`, which Slice 1 leaves null for HTTP captures).

Slice 1 (per cm decision `019de422`) is: request curation, breakpoint editing, provisional exchange persistence, final raw response persistence. **Full turn timeline parity is explicitly deferred.** That means `CodexTimeline` and `CodexSemanticEvent[]` stay WebSocket-only for now. Frontend impact is therefore narrow: one type widening, one rendering branch in `CodexTransportPanel`, one defensive guard around `CodexTimeline`. The list row (`ExchangeTurnCard`) and inspect surfaces work as-is because they already key off `entry.codex_turn` (HTTP rows will have it null until Slice 2).

## Surface map

### `desktop/`

Pure Electron shell. 13 source files, all infra:

- `main.ts`, `window.ts` — BrowserWindow + lifecycle
- `preload.ts` — context-isolated bridge
- `backendProcess.ts`, `backendHealth.ts` — supervises the FastAPI backend
- `packageSmoke.ts` — packaging smoke test
- No routes, no views, no Codex-specific code, no transport awareness

**Scope: zero changes.** Confirm by `grep`: no hits for "codex" or "websocket" outside test fixtures.

### `www/`

React 19 + Vite 8 (Rolldown) + TypeScript strict + Tailwind v4 + Zustand + TanStack Query. The exhaustive product UI.

Top-level layout (real layout, ignoring the README's aspirational `features/` description):

```
www/src/
  api.ts                  — REST client (one ApiTransport, ~25 endpoints)
  types.ts                — single source of truth for wire types
  app.tsx, main.tsx       — entry
  routeLayout.tsx         — 3-pane shell
  stores/                 — Zustand: uiStore, overlaysStore, persistence
  hooks/                  — useExchanges, useExchangeStream (SSE), useMeta, useOverrides, useTurnContent, useBreakpoint, useRouteHotkeys
  components/
    ExchangeList.tsx           — virtualized list (left rail)
    ExchangeTurnCard.tsx       — per-turn card (left rail row)
    ExchangeDetail.tsx         — tab host: inspect | request | response | transport
    detail/
      InspectTab.tsx                 — inspect tab body
      ExchangeCard.tsx               — exchange+pipeline summary card
      CodexTimeline.tsx              — Codex semantic events timeline (WS-only)
      CodexTransportPanel.tsx        — Codex transport frames panel (WS-only today)
      JsonView.tsx                   — raw JSON fallback
      ContentBlocks.tsx, mutations.ts, atoms.tsx, ...
    editor/                          — breakpoint editor (sampling, tools, system, messages)
    routes/                          — TraceView, OverlaysView, RecallView
```

## Current state — by layer

### Codex display path (WS)

The Codex path branches at three levels:

1. **List row.** `ExchangeTurnCard.tsx:111-130` derives status colour, "frame range" overlay, and "waiting for Codex transport" hint from `entry.codex_turn` (a `CodexTurnListSummary`, populated only for Codex rows; `null` for Anthropic). The "pending" branch at `:221-222` splits Claude-pending (no `codex_turn`, no `res`) from Codex-pending (`codex_turn.status === "open"`).
2. **Detail header telemetry.** `ExchangeDetail.tsx:18-63` exposes `hasCodexTimeline(detail)` and `codexHeaderTelemetry(detail)`. Both gate on `provider === "codex"` AND `detail.events != null && detail.turn != null`.
3. **Inspect tab.** `InspectTab.tsx:242-274` mounts `<CodexTimeline events={codexEvents} turn={codexTurn} />` under the same `provider === "codex" && events != null && turn != null` guard. The timeline component itself (`CodexTimeline.tsx`) renders semantic events with `transport_ref.message_index` jump buttons that drive `setTab("transport")` and a focused-frame scroll inside `CodexTransportPanel`.
4. **Transport tab.** `ExchangeDetail.tsx:359-374` chooses `<CodexTransportPanel>` iff `detail.transport?.provider === "codex"`, otherwise `<JsonView>`. The panel (`CodexTransportPanel.tsx`) renders frames over `transport.messages`, with hardcoded copy "No websocket frames captured" (`:176`) and a header that prints `scheme://host{path}` + close code, all of which assume the WebSocket upgrade artifact.

The SSE event ingestion (`hooks/exchangeStreamEvents.ts`) parses `paused.transport` (`:159`) and `codex_turn.terminal_cause` (`:97`) using the `"websocket"` literal as a sentinel — these already tolerate the `"http"` alternative without strict narrowing because they use `=== "websocket" ? "websocket" : "http"` patterns.

### Anthropic / Claude display path (HTTP) — the leverageable pattern

There is no Anthropic-specific component. Anthropic rows are the **default** rendering. The four-tab detail view (inspect, request, response, transport) is provider-agnostic, with Codex augmenting via:

- `CodexDerivedArtifactsCard` (in `InspectTab.tsx:179`)
- `CodexTimeline` (in `InspectTab.tsx:268`)
- `CodexTransportPanel` (in `ExchangeDetail.tsx:364`)
- Codex-only header telemetry chips (`ExchangeDetail.tsx:38-63`)

The generic core that an HTTP Codex row inherits for free:

- `ExchangeCard` (`detail/ExchangeCard.tsx`) — token bar, override summary, pipeline tab. `:25` has `provider === "anthropic"` gating only the lazy-fetch token recount (Codex doesn't get count_tokens). HTTP Codex rows will hit this `false` branch fine.
- `SystemSection`, `MessagesSection`, `ToolsSection` from `components/editor/` driven by `request_ir` / `request_curated_ir` via `buildSyntheticOverrides` (`InspectTab.tsx:79-145`). These render IR content blocks (system parts, messages, tools, tool results) generically.
- `JsonView` fallback for `transport` tab when not Codex (`ExchangeDetail.tsx:372`).
- `TransportDiagnostics` (`ExchangeDetail.tsx:116-157`) — provider-neutral.

**Leverage: an HTTP Codex exchange already gets request/response/inspect rendering for free** through the Anthropic-shaped path. Only the "transport" tab needs an HTTP-aware renderer (or fallback to `JsonView`).

### Client data model

The complete shape is in `www/src/types.ts` (523 lines, one file). Key entries:

- `IndexEntry` (`:50-67`) — list row payload. `provider: string`, `codex_turn?: CodexTurnListSummary | null`. Already protocol-agnostic.
- `ExchangeDetail` (`:90-107`) — detail payload. Holds `transport: TransportArtifacts | null` and (optionally) `events`, `turn`, `codex_derived_artifacts`.
- `TransportArtifacts` (`:356-362`) — **the structural pinch point**. `protocol: "websocket"` is a string literal that **must** widen. Also has `upgrade: TransportUpgradeArtifacts` and `close: TransportCloseArtifacts | null`, both of which are HTTP-irrelevant.
- `TransportMessageArtifact` (`:344-354`) — per-frame artifact. Reusable for HTTP if we let the backend emit a `messages` array with `direction`, `is_text`, `payload_text` etc. Most fields are already neutral.
- `PausedFlow` (`:487-517`) — **already protocol-aware** at `:489`: `transport: "http" | "websocket"`. The breakpoint editor branches on this at `BreakpointEditorActions.ts:38-45` to decide whether to wait for stream activity (HTTP) or for a provisional exchange (WebSocket).
- `CodexTerminalCause` (`:152`) — `"response_completed" | "response_failed" | "websocket_close"`. HTTP fallback will not produce `websocket_close`; the union remains compatible.

Codex protocol is **implicit** in the artifacts today. `TransportArtifacts.protocol` is hardcoded `"websocket"`, and `CodexTransportPanel` reads `transport.upgrade.scheme`/`path` and `transport.close.close_code` assuming WS upgrade semantics. No client component reads `protocol` as a discriminator — the discriminator today is `transport?.provider === "codex"`.

### API client

The frontend talks to a FastAPI backend over plain REST + SSE. No GraphQL, no WebSocket from the browser:

- `fetchExchanges(limit, offset, includeHistory)` → `GET /api/exchanges` → `IndexEntry[]` (`api.ts:70-87`)
- `fetchExchange(id)` → `GET /api/exchanges/{id}` → `ExchangeDetail` (`:89-95`)
- `fetchTurnContent(id)` → `GET /api/exchanges/{id}/turn-content` (`:97-103`)
- Breakpoint endpoints (`:213-291`): status, arm, disarm, release, release-unmodified, drop, re-audit, paused detail
- Override endpoints (`:143-211`): list/patch/clear/toggle, scope-aware
- `fetchMeta()` → `GET /api/meta` (`:309-320`)
- SSE stream consumed by `useExchangeStream` → `hooks/exchangeStreamEvents.ts` parses `paused`, `paused_tokens`, `exchange`, `exchange_deleted` events.

The wire contract is the Python Pydantic models in `api/src/transport_matters/api/v1/*`. The frontend's `types.ts` mirrors them by hand (no codegen). **Therefore: when the backend widens `TransportArtifacts.protocol` from `Literal["websocket"]` to `Literal["websocket", "http"]`, the frontend will silently accept HTTP payloads at runtime** (the JSON parser doesn't enforce the literal). What it **won't** do is render them correctly — `CodexTransportPanel` will read `transport.upgrade.scheme` on something that may legitimately have no `upgrade` artifact, and the "No websocket frames captured" copy will mislead the user.

The TypeScript compiler **will** fail when `CodexTransportPanel` consumers pass artifacts containing `protocol: "http"` after the type widens — that is desirable: it forces the rendering branch to be authored.

## Required changes — by slice

### Slice 1 (this work)

- [ ] **Widen `TransportArtifacts.protocol` to `"websocket" | "http"`.** File: `www/src/types.ts:358`.
  - **Why**: Mirror the backend Pydantic widening described in cm `019de422`.
  - **Risk**: Low. TypeScript will surface the one call site (`CodexTransportPanel`) that reads `protocol`. Today no one does, so the strict-narrow break is minimal. Update jsdoc to note that `upgrade` and `close` are WebSocket-only.

- [ ] **Make `upgrade` and `close` nullable on `TransportArtifacts`** (or move them inside a `websocket`-discriminated branch).
  - File: `www/src/types.ts:356-362`.
  - **Why**: HTTP captures have no upgrade handshake and no close frame; rendering must not assume their presence.
  - **Risk**: Medium. `CodexTransportPanel.tsx:96-108` reads `transport.upgrade.scheme`, `transport.upgrade.host`, `transport.upgrade.path`, `transport.upgrade.response_status_code`, `transport.close.close_code`. Either guard each with optional-chaining or split the type into a discriminated union (`{ protocol: "websocket"; upgrade; close; ... } | { protocol: "http"; ... }`). **Recommend the discriminated union** — it makes the panel's branching obligation visible at the type level.

- [ ] **Branch `CodexTransportPanel` by `transport.protocol`.** File: `www/src/components/detail/CodexTransportPanel.tsx`.
  - **Why**: The current panel renders WS upgrade/close metadata and frame counts. HTTP captures need different framing (request/response pair, status line, body chunks if streamed, no close frame). For Slice 1 the minimum is: a separate header that prints HTTP method + path + status, and a frame list that re-uses the existing `transport.messages` rendering (each "frame" becomes a request or response body chunk). The empty-state copy at `:176` ("No websocket frames captured") must become protocol-aware.
  - **Risk**: Medium. The frame-jump anchor (`focusedMessageIndex`) is shared with `CodexTimeline`. Slice 1 won't emit timeline events for HTTP, so the jump path is dormant; keeping the same `messages: TransportMessageArtifact[]` shape preserves the affordance for Slice 2.

- [ ] **Tighten the timeline mount guard in `InspectTab` and `ExchangeDetail`.** Files: `www/src/components/detail/InspectTab.tsx:242-243`, `www/src/components/ExchangeDetail.tsx:18-20`.
  - **Why**: Already gated on `events != null && turn != null`, so HTTP Codex rows (which Slice 1 leaves with both null) will skip the timeline naturally. **No code change required**; this is a deliberate "leave as-is and verify" item.
  - **Risk**: Low; verify behaviour with a test fixture.

- [ ] **Tighten the transport tab branch in `ExchangeDetail`.** File: `www/src/components/ExchangeDetail.tsx:364`.
  - **Why**: The current guard is `detail.transport?.provider === "codex"`. After widening, an HTTP-protocol Codex transport will still satisfy `provider === "codex"` and mount `CodexTransportPanel`. That's correct **once the panel branches internally** (item 3 above). No change at this site unless we want a provider+protocol matrix at the dispatcher — recommend keeping the dispatch single-keyed on provider and handling protocol inside the panel.
  - **Risk**: Low.

- [ ] **Test fixture for HTTP Codex exchange.** Add a fixture under `www/src/components/__test-utils__/` that builds an `ExchangeDetail` with `provider: "codex"`, `transport.protocol: "http"`, no `events`, no `turn`. Cover `ExchangeDetail.test.tsx` and `CodexTransportPanel.test.tsx` (the latter does not exist; create it).
  - **Why**: Lock in the additive contract so future changes can't regress WebSocket rendering when HTTP edits land.
  - **Risk**: Low.

- [ ] **Verify `BreakpointEditorActions` HTTP branch.** File: `www/src/components/editor/BreakpointEditorActions.ts:38-45`.
  - **Why**: `getReleasedFlowCompletion` already returns `shouldWaitForStream: true` for `transport !== "websocket"`. Codex HTTP fallback captures will hit this branch identically to Anthropic HTTP. **No code change**; verify the behaviour matches the backend's post-release event emission for HTTP Codex.
  - **Risk**: Low; behavioural test only.

### Slice 2 (deferred — full turn parity)

- [ ] Emit semantic events for HTTP Codex captures on the backend, then re-enable `CodexTimeline` for HTTP rows by removing the implicit "WS-only" assumption in the timeline copy ("Breakpoint released the turn back to the websocket session." `CodexTimeline.tsx:96`).
- [ ] Populate `entry.codex_turn` for HTTP rows so the list row gets the same turn-aware status border, "frames N→M" pending strip (`ExchangeTurnCard.tsx:314-318`), and turn telemetry header chips. The chunk-range semantics for HTTP are different (SSE chunk count vs WS frame count); decide on a unified "step count" abstraction.
- [ ] Decide whether `CodexTerminalCause` needs `"http_complete"` / `"http_error"` variants or whether `response_completed` / `response_failed` cover it.
- [ ] If the HTTP path can stream (SSE Responses chunks), unify `TransportMessageArtifact` semantics so a "frame" is a chunk; otherwise show the request and response as two pseudo-frames for the jump-from-timeline affordance to remain coherent.

## Leverage opportunities — do not reinvent

Concrete components the HTTP Codex path inherits for free:

- **`ExchangeCard`** (`www/src/components/detail/ExchangeCard.tsx:10`) — token bar, override summary, pipeline savings. The Anthropic-only gate at `:25` is just for the lazy count_tokens recount; non-Anthropic rows render the chars fallback fine. Reuse as-is.
- **`SystemSection`**, **`ToolsSection`**, **`MessagesSection`** (`www/src/components/editor/{System,Tools,Messages}Section.tsx`) — all read-only-capable, driven by IR content blocks. `InspectTab.tsx:276-290` already passes them through `buildSyntheticOverrides`. Reuse as-is.
- **`ContentBlockRow`** (`www/src/components/detail/ContentBlocks.tsx`) — renders text / tool_use / tool_result / thinking / image blocks. Provider-neutral. Reuse for HTTP Codex response_ir content.
- **`JsonView`** (`www/src/components/detail/JsonView.tsx`) — already the fallback for non-Codex transport. If Slice 1 wants to ship with **zero panel-side branching**, use `JsonView` for HTTP Codex transport tab and skip the panel update — but that leaves the user with raw JSON instead of a readable view. Recommend the in-panel branch (item 3 above) over the JsonView fallback.
- **`TransportDiagnostics`** (`www/src/components/ExchangeDetail.tsx:116`) — provider- and protocol-neutral. Reuse as-is.
- **`buildSyntheticOverrides`** (`www/src/components/detail/InspectTab.tsx:79`) — drives the curated-IR-as-overrides rendering. Provider-neutral. Reuse as-is.
- **`useExchangeStream` SSE handler** (`www/src/hooks/exchangeStreamEvents.ts`) — already accepts `paused.transport === "http"` (line 159) and tolerates missing `codex_turn` (`:224` returns null cleanly). No change needed for Slice 1; verify the backend emits the same `exchange` event shape for HTTP captures.
- **`BreakpointEditorActions.getReleasedFlowCompletion`** (`www/src/components/editor/BreakpointEditorActions.ts:37`) — already discriminates HTTP vs WebSocket release semantics. No change needed.

## Open questions

1. **`upgrade` and `close` artifact shape for HTTP**: should the backend emit `null` for both on HTTP, or move them under a discriminated branch? The frontend's preference is the discriminated union (`{ protocol: "websocket"; upgrade; close } | { protocol: "http"; request; response }`), but that requires either the backend to model it the same way or a frontend remapper. Confirm with `api/`.

2. **`TransportMessageArtifact.event_type`**: today this is the WS `event` field. For HTTP SSE chunks it would be the SSE event name; for non-streamed responses it would be `null`. Confirm the backend keeps this generic.

3. **`provisional_exchange_id` semantics for HTTP Codex**: the breakpoint flow at `BreakpointEditorActions.ts:38-45` returns `selectedId: pausedFlow.provisional_exchange_id` for websocket and falls back to "wait for stream" for HTTP. For Codex HTTP fallback breakpoints, which branch is correct? Likely "wait for stream" (matches Anthropic HTTP), but the cm decision lists "provisional exchange persistence" in Slice 1, so the backend may emit a provisional exchange even on HTTP. Confirm.

4. **List row pending UX for HTTP Codex**: `ExchangeTurnCard.tsx:221` defines `isClaudePending` as `!entry.codex_turn && entry.provider !== "codex" && entry.res === null`. An HTTP Codex row with no `codex_turn` and no `res` would fail this guard (`provider === "codex"`) and also fail `isCodexPending` (`codex_turn?.status === "open"` is false because there is no `codex_turn`). Result: the row would render as "not pending" while still genuinely awaiting a response. **Slice 1 needs to either populate `codex_turn` minimally for HTTP rows or relax the `isClaudePending` definition.** Flag this as a Slice 1 follow-up.

5. **Header copy in `CodexTransportPanel`**: the current header prints `scheme://host{path}` from `transport.upgrade`. For HTTP captures this should become method + path + status. Confirm what shape the backend emits for HTTP and design the chip accordingly.

6. **Detail tab disabled-state**: `ExchangeDetail.tsx:293` disables the transport tab when `detail.transport == null`. For HTTP Codex captures the backend will emit `transport` populated; ensure the disabled-state logic still holds.
