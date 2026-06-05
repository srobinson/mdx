# Transport Matters — Slice 4 Scout: per-pane vitals on the canvas

- **Mode:** Scout & Plan (read-only). AUDIT existing code, map reuse. No design of a full solution, no code written.
- **Locked design:** cm decision `019f4205` — Control Center v1 = per-pane vitals, NOT a separate board. Concept mock artifact `8d959e3c`.
- **Vitals (5, all "real day-one"):** context used/remaining (bar + used/ceiling + %), $ cost, time, status pill + "needs you". Fed live off the `/v1` workspace activity SSE (slice 3, merged `e294571`).
- **Sources:** five parallel read-only Explore scouts (canvas pane, @tm/core+SSE, @tm/activity model+catalog, token/cost UI, quality/boundaries). All findings cite file+symbol, never line numbers.
- **Tree state:** pristine — confirmed `main`, clean working tree, empty diff before and after; scouts had no write tools; the only artifact is this doc under `~/.mdx/` (outside the repo).

## Headline

The token *granularity* the vitals need is already on the wire; the two gaps are both **greenfield and gate the same two vitals**. (1) `model` is dropped at stage 0 of the TS activity pipeline (the SQL column contract never SELECTs it, though pg stores it twice), and (2) **no model-metadata catalog — context-window ceilings or per-model pricing — exists anywhere in the repo, TS or Python.** `context_tokens` is already on `ActivityWireRun`, so *context-used* is free; *remaining-%* and *$-cost* cannot be real until `model` is surfaced end-to-end AND a ceiling+pricing catalog is authored. Everything else (SSE consumption, the vitals data slice, formatting, the pane mount) is a clean reuse of existing patterns.

---

# Reuse Map

## 1. Canvas captured-run pane + where a vitals strip mounts

| Capability | Owner (file → symbol) | Notes |
|---|---|---|
| Captured-run pane component | `www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx` → `CapturedRunPane` | 136 LOC; the mount surface. Renders only an error banner + progress shimmer today. |
| Pane→run_id resolution | `.../viewers/terminal/CapturedRunPane.tsx` → `CapturedRunPaneProps.runKey` (stable `provider:uuid`) → `.../infrastructure/runtime/useCapturedRunBinding.ts` → `useCapturedRunBinding` returns `{ runId }` → `.../model/capturedRunStore.ts` → `useCapturedRunStore` (`runs[runKey].runId`, persisted) | run_id is available in the pane and survives reload. |
| Title bar owner | `.../workbench/chrome/PaneChrome.tsx` → `PaneChrome` | Renders `<header class="canvas-pane-window__header">` (title-wrap + actions). Decluttered in #204: badge/state deliberately not rendered. |
| **Vitals mount slot** | **None exists.** `PaneChrome` accepts only `children` (routed to `.canvas-pane-window__body`); `.../workbench/PaneWindow.tsx` → `PaneWindow` is the thin `PaneRecord → PaneChrome` adapter passing children through. | Two options (see Decision D2): add a dedicated sub-header slot prop to `PaneChrome` (shared chrome, all panes) OR mount inside `CapturedRunPane`'s own `.terminal-pane` container (per-viewer). |
| Pane live-data today | PTY WebSocket via `.../viewers/terminal/terminalSession.ts` → `useTerminalSession` → `.../infrastructure/runtime/internal/terminalSocket.ts`; plus zustand selectors via `useCapturedRunBinding`. **No SSE, no metrics subscription.** | The vitals SSE is a new subscription for this pane. |
| CSS/token system to match | `.../styles/tokens.css` (`--color-txt/-2/-3`, `--color-surface/-raised`, pastel `--color-sage/rose/amber`, `--pane-header` = 58px, `--font-mono` = JetBrains Mono, `--radius-sm`); runtime override `.../theme/theme.ts` → `applyThemeTokens`; presets `.../theme/presets.ts`. **Sibling to imitate:** `.../viewers/terminal/terminal-pane.css` `.terminal-pane__status` (already a tokenized strip). | Repo rule: **zero Tailwind, vanilla BEM** (`www/packages/canvas` CLAUDE.md). |
| Existing vitals on canvas | **none found** — no token/context/cost/pill UI in canvas src. `RunView` (`www/packages/core/src/transport.ts`) carries **no vitals fields** (only runId, spaceId, worktreeId, sessionId, harness, state, endReason, error, createdAt). | The vitals data source is entirely the new activity slice, not the existing run query. |
| Closest attention primitives | `.../viewers/placeholder/paneState.tsx` → `PaneTone`/`ResourcePaneState` (resource-pane only); `.../ambient/types.ts` → `AmbientSignalState` (`idle|working|waiting|error`) + `.../ambient/createAmbientBackground.ts` → `AmbientBackground.setSignal` | `setSignal` is **unwired** (zero non-test call sites) — a candidate sink if vitals should drive ambient attention, but out of slice-4 scope unless chosen. |

## 2. @tm/core data kernel — home for the activity data slice

| Capability | Owner (file → symbol) |
|---|---|
| API transport / fetch wrapper | `www/packages/core/src/transport.ts` → `createApiTransport` (singleton `apiTransport`, `setApiTransport`/`resetApiTransport` test seam), JSON helpers `requestApiJson`/`requestApiVoid`, `apiUrl`. Domain run verbs already here: `listRuns`, `getRun`, `RunView`, `RunState`, `createCapturedRun`, `terminateRun`. |
| react-query client | `www/packages/core/src/queryClient.ts` → `queryClient` (shared singleton, staleTime 30s). |
| query-key factory | `www/packages/core/src/queryKeys.ts` → `sessionEventsKey` et al. |
| Pure SSE event applier (the pattern to mirror) | `www/packages/core/src/exchangeStreamEvents.ts` → `applyExchangeStreamEvent` + `StreamSideEffects`/`ExchangeStreamEventContext` ports (pure JSON→cache, no socket). |
| **Recommended new homes** | Activity fetch verb + `/v1` workspace-activity URL builder next to `listRuns`/`getRun` in `transport.ts`. A pure per-`run_id` vitals reducer as a new **sibling** `www/packages/core/src/activityStreamEvents.ts` (mirrors `exchangeStreamEvents.ts`), unit-testable without React DOM. |

**Why core:** `@tm/core` is an internal leaf (deps: `react`, `@tanstack/react-query`, `zustand` only; no `@tm/*` deps), imported by both canvas and inspector; the run vocabulary (`RunView`) already lives here. Fetch+parse+reduce is product-agnostic and belongs in core; the socket does not (see area 3).

## 3. Live SSE client — reuse `useSessionEventStream`, do not write a third EventSource shell

| Capability | Owner (file → symbol) | Verdict |
|---|---|---|
| Canvas SSE consumer (prime reuse base) | `www/packages/canvas/src/infrastructure/stream/useSessionEventStream.ts` → `useSessionEventStream` | **Best base.** Already has an injected `onEvents` callback port, a resume cursor (`highestSeq`), `baseUrl` injection, explicit reconnect (`RECONNECT_DELAY_MS`, fixed 1s), gap-backfill over REST, and clean teardown. Companion pure reducer `.../infrastructure/stream/sessionEventReducer.ts` → `sessionEventReducer` (seq-dedup, `findMissingFromSeq`). Per-pane wiring reference: `.../viewers/transcript-chat/TranscriptChatPane.tsx` (one stream per pane). |
| URL builder pattern | `.../infrastructure/api/sessionEvents.ts` → `sessionEventsStreamUrl` | Copy shape for a workspace-activity stream URL. |
| Inspector SSE consumer (the other copy) | `www/packages/inspector/src/hooks/useExchangeStream.ts` → `useExchangeStream` | Thinner but hard-wired to exchange-cache mutation + inspector `useUIStore`; relies on native EventSource auto-reconnect. **Less reusable.** |
| **New home** | New `www/packages/canvas/src/infrastructure/stream/useWorkspaceActivityStream.ts`, sibling of `useSessionEventStream.ts`. | Per repo convention + product CLAUDE.md boundaries, EventSource construction is **product-owned**; core holds no sockets. See Quality Map §Duplication for the `useEventSource` consolidation opportunity. |
| Per-run vitals held-state | New store beside `www/packages/canvas/src/model/capturedRunStore.ts` → `useCapturedRunStore` (already a per-`runKey` zustand store). | Slice 4 is explicitly canvas-scoped ("per-pane vitals on the canvas") → vitals store keyed by `run_id` belongs in `canvas/src/model/`. Promote to core only if inspector must later read vitals. |

## 4. @tm/activity — surfacing `model` + the greenfield model-metadata catalog

**`model` is dropped at stage 0 (the SQL column contract). CLAIM CONFIRMED and stronger than stated:** pg stores `model` twice (the `event.model` column from `api/migrations/versions/0001_session_store_foundation.py`, and inside the row's `raw` JSON), yet the TS reader reads neither.

End-to-end thread required to surface it (each is the exact edit site):

1. `packages/activity/src/server/pgContracts.ts` → `EVENT_COLUMNS` (add `model`).
2. `packages/activity/src/adapters/postgresRecords.ts` → `RECORD_SELECT_COLUMNS` (SELECT it) + `pgActivityEventRecordFromRow` (coerce it).
3. `packages/activity/src/adapters/transcriptRecords.ts` → `PgActivityEventRecord` (add slot). (Alternative source: parse `message.model`/`payload.model` from `raw` in `claudeActivityRecords`/`codexActivityRecords`.)
4. `packages/activity/src/ports.ts` → `ActivityRecord` (add `model`).
5. `packages/activity/src/domain/runActivityContext.ts` → `RunActivityContext` + `initialContext`.
6. `packages/activity/src/projections/workspaceActivity.ts` → `RunActivityProjection` + `runActivityProjection()`.
7. `packages/activity/src/server/activityRouter.ts` → `ActivityWireRun` + `runToWire()`.

Python side already captures/persists `model` fully (for reference, not slice-4 work): parse in `api/src/transport_matters/index/adapters/claude.py` (`NormalizedTurn(model=...)`) / `codex.py` (`model_hint`); IR in `session/ingest.py` (`EventRow(model=...)`); persist in `session/dao_statements.py` (`EVENT_COLUMN_NAMES` includes `model`, `INSERT_EVENT_SQL`); read-back in `session/timeline.py` / `timeline_models.py` (`TimelineEvent.model`).

**Model-metadata catalog: NONE FOUND — greenfield (TS and Python).** Exhaustive search (`pricing`, `price_per`, `cost_per`, `contextWindow`, `context_window`, `ceiling`, `per_million`, `per_token`, `catalog`, `200000`, `1000000`, `MODEL_[A-Z]`, `max_tokens`, `usd`, `billing`) found no ceiling constant, no pricing table, no model→metadata map. Near-hits are all unrelated: `api/src/transport_matters/model_ids.py` (`normalise_model`/`denormalise_model` — prefix string helpers only); `max_tokens` everywhere is the per-request **output cap** on `SamplingParams`, not a context-window ceiling.

- **Recommended home:** new `packages/activity/src/domain/modelMetadata.ts`, sibling of `packages/activity/src/domain/usage.ts`, exported via `packages/activity/src/domain/index.ts`.
- **Why:** `usage.ts` already owns the pure token arithmetic (`UsageTotals`, `addUsage`, `emptyUsage`, `windowTokens` = input+cacheCreation+cacheRead). remaining-% (= windowTokens/ceiling) and $-cost (= buckets × per-model rates) are the same shape of pure, IO-free derivation. `@tm/common` is forbidden (domain-free per `packages/AGENTS.md`); a model→ceiling/price table is domain knowledge. Python has no natural home.

**Usage already on the wire — granularity is sufficient, only inputs are missing:**
- `ActivityWireUsageTotals` (`server/activityRouter.ts`, mapped by `usageToWire`): `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`.
- `ActivityWireRun.context_tokens` (number|null): current-window size (input+cacheCreation+cacheRead of the last turn), computed by `domain/usage.ts` → `windowTokens`.
- Sufficiency: *context-used* SUFFICIENT (already on wire). *remaining-%* needs ceiling + `model`. *$-cost* needs per-model pricing + `model` (the four buckets are the right granularity — cache-write/cache-read price differently).

## 5. Existing token/context/cost UI + formatting

| Capability | Owner (file → symbol) | Reuse verdict |
|---|---|---|
| Canonical context-token formula (input+cache_creation+cache_read) | `www/packages/core/src/formatting.ts` → `contextTokens(UsageStats)` (re-exported via core `index.ts`) | **Reuse directly.** Do not re-inline (already re-inlined twice — see Quality Map). |
| Closest existing "vitals strip" render | `www/packages/inspector/src/components/detail/TokenBar.tsx` → `TokenBar` (stacked input/cache-read/cache-write bar) + `TokenStat` (tokens\|chars readout) | **Pattern only — NOT importable** (no canvas→inspector edge). Canvas vitals bar must be re-authored using canvas tokens/BEM; mirror the structure. |
| tokens-vs-chars display rule | Twin inline logic in `inspector/.../ExchangeDetail.tsx` → `tabReadout` and `canvas/.../viewers/resource/ArkExchangeViewer.tsx` → `tabReadout` (+ `TokenStat` `format` switch) | No shared owner — duplicated. Slice 4's context vital shows real tokens (activity payload has them), so this rule is mostly N/A, but consider extracting if reused. |
| Number/time formatters | `www/packages/core/src/formatting.ts` → `formatCompactChars`, `formatClockTime`, `formatRelativeAge`, `pluralize`, `displayModel` | Core is the home. **Gaps:** no currency formatter, no elapsed/duration formatter. |
| Duration/elapsed (the "time" vital) | Scattered private impls: `inspector/.../ExchangeTurnCard.tsx` → `formatElapsedTime`, `inspector/.../editor/PausedHeader.tsx` → `formatElapsed`, `inspector/.../detail/CodexTimeline.tsx` → `formatDuration` | **No core owner** — consolidate one into `core/formatting.ts` for the time vital. |
| $ cost formatting | **none found** | Greenfield — add a currency formatter to `core/formatting.ts`. |
| Status pill / "needs you" | `inspector/.../ArmToggle.tsx` → `ArmToggle` (armed/disarmed pill, `arm-dot pulse-dot`); `inspector/.../editor/PausedHeader.tsx` → `PausedHeader` (amber "Paused" + live elapsed — closest "needs you" lamp) | Inspector-only, not importable by canvas. Pattern reference; canvas pill re-authored. No literal "needs you" string exists yet. |

---

# Quality Map

## Sizing (700-LOC guardrail)
No source file in any slice-4 target area exceeds 700 LOC. Headroom on every edit site: `CapturedRunPane.tsx` 136, `PaneChrome.tsx` 111 (single render fn ~82 — watch if the vitals row lands directly here), `activityRouter.ts` 278 (`createActivityRouter` ~100), `workspaceActivity.ts` 296 (`WorkspaceActivityProjections` is a ~196-LOC class, largest method ~26), `core/transport.ts` 474 (38 exports). No single function >150 LOC in scope. Only >700 file anywhere in-scope is a test (`canvas/.../canvasStore.test.ts` 910).

## Boundary / dependency direction (the load-bearing constraint)
- Declared deps: **@tm/canvas → @tm/core, @tm/common, @tm/host**; **@tm/core** = internal leaf (`react`, `@tanstack/react-query`, `zustand`, no `@tm/*`); **@tm/activity** → `@tm/common`, `fastify`, `pg`, `xstate` (a Node/Fastify/Postgres server package).
- **Canvas does NOT import @tm/activity — at all, and cannot** (activity pulls `pg`/`fastify`, un-bundleable in the browser). `@tm/activity` is imported only by `packages/gateway`. `@tm/activity` and `@tm/core` have **no dependency in either direction** — no shared TS type package bridges them.
- **Seam:** the only clean canvas↔activity path is the HTTP/SSE **wire**, consumed via `canvas/src/infrastructure/api/*` + `.../stream/*` (mirroring existing SSE). The wire shape (`ActivityWireRun`/`ActivityWireUsageTotals`) must be **re-declared client-side** (canvas or core) — it cannot be imported from `@tm/activity`. This is Decision D3.

## Duplication (slice 4's live risks)
- **EventSource lifecycle shell** is hand-rolled twice (`canvas/.../useSessionEventStream.ts`, `inspector/.../useExchangeStream.ts`) with no shared `useEventSource`. A slice-4 activity stream becomes the **third** copy. Opportunity: extract `useEventSource({ url, onMessage, onOpen, onError })` (home: `canvas/src/infrastructure/stream` or core if kept React-only) to absorb all three. The *pure* side is already well-split (core `exchangeStreamEvents`, canvas `sessionEventReducer`).
- **Context-token math** re-inlined off `contextTokens`: `canvas/.../ArkExchangeViewer.tsx` `tabReadout` and `inspector/.../ExchangeDetail.tsx` `tabReadout` hand-sum the three fields. Slice 4 must call `contextTokens`, not add a third inline copy.
- **Duration formatting** duplicated across 3 private fns (§Reuse area 5) — consolidate for the time vital.

## Dead code / retired scaffolding
- The retired legacy index / block store / diff era is **fully gone** from all three target areas (no `blockStore`/`diffProjection`/`rawFetch` symbols survive). No `vitals` symbol exists anywhere — greenfield naming, no collision.
- Remaining `legacy`-named code is **live back-compat, not dead** (`canvas/.../theme/migrate.ts`, `.../persistence/canvasCacheStorage.ts`, `.../model/paneRecords.ts`, `.../route.ts`). `IndexEntry` in `core/types/exchanges.ts` is the LIVE exchanges index, unrelated to the retired "legacy index" — don't conflate.
- **Pre-merge hacks in scope (flag now):** `canvas/.../viewers/terminal/terminal-pane.css` hardcodes `#ffd700` in `.xterm-bg-59`/`.xterm-bg-237` with an explicit "DEMO (this branch): retune to a theme value before merge" marker — bypasses the token system; resolve before slice-4 touches that file. `AmbientBackground.setSignal` is unwired (zero call sites).

---

# Plan

## DECISION NEEDED (primary)
**The model-metadata catalog (context-window ceilings + per-model pricing) is fully greenfield, and `model` is not on the wire.** These two together gate 2 of the 5 vitals (remaining-% and $-cost) being "real day-one." Stuart to decide: (a) the catalog's authority/maintenance policy — hardcoded TS constants in `activity/domain/modelMetadata.ts` (accepts drift, simplest) vs a sourced/generated table; (b) which Claude/Codex models ship day-one and their ceiling + input/cache-write/cache-read/output rates; (c) fallback behavior for an unknown `model` (hide remaining-%/$ vs show "—").

## Secondary decisions
- **D2 — vitals mount:** shared `PaneChrome` sub-header slot (all panes, threaded through `PaneWindow`) vs per-viewer strip inside `CapturedRunPane`. Recommend the `PaneChrome` slot only if other pane types will get vitals later; otherwise per-viewer keeps blast radius minimal.
- **D3 — wire-type ownership:** where the client-side `ActivityWireRun`/`ActivityWireUsageTotals` shape lives (re-declared in `@tm/core` vs canvas) given canvas cannot import `@tm/activity` and no shared contract package exists. Recommend `@tm/core` (both products can then consume). Consider a lightweight contract test asserting the server and client shapes agree.
- **D4 — "needs you" source:** what drives it for a canvas captured-run pane (run state `waiting` vs breakpoint-armed). Breakpoints are inspector-armed today; canvas has no arm affordance. Likely maps to activity run state, not a breakpoint, for v1.
- **D5 — `useEventSource` extraction:** extract the shared hook now (before the third copy) vs after. Recommend now — it is the cheapest moment.

## Ordered steps (each bound to the reuse map)
1. **Surface `model` end-to-end** through the 7 edit sites in Reuse §4 (`EVENT_COLUMNS` → `RECORD_SELECT_COLUMNS`/coercion → `ActivityRecord` → `RunActivityContext` → `RunActivityProjection` → `ActivityWireRun`/`runToWire`). Server-only; unit-testable in `packages/activity`.
2. **Author `packages/activity/src/domain/modelMetadata.ts`** (ceilings + pricing, sibling of `usage.ts`) and pure derivations `remainingPercent(context, model)` and `estimatedCost(usageTotals, model)` beside `windowTokens`. Emit derived `remaining_pct`/`cost` (or the raw ceiling/rates) onto `ActivityWireRun` per D1/D3.
3. **@tm/core data slice:** add the workspace-activity fetch verb + URL builder to `core/transport.ts`; add pure reducer `core/activityStreamEvents.ts` (mirror `exchangeStreamEvents.ts`) folding events into per-`run_id` vitals; declare the client wire types per D3.
4. **(D5) Extract `useEventSource`** from `useSessionEventStream`/`useExchangeStream`, then build `canvas/.../infrastructure/stream/useWorkspaceActivityStream.ts` on it.
5. **Canvas vitals store** beside `capturedRunStore.ts`, keyed by `run_id`, fed by the stream.
6. **Vitals strip UI** at the D2 mount, using `contextTokens` (reuse), canvas tokens/BEM (imitate `.terminal-pane__status`), a new core currency + duration formatter (consolidate the scattered duration fns), and a status pill mirroring `ArmToggle`/`PausedHeader` patterns. Resolve the `#ffd700` DEMO hack if that file is touched.

## Gates
- `just check` (typecheck/lint gate) and `just test` (full, reliable suite — the repo's stated gate) after each server slice and the FE slice.
- Playwright for the canvas vitals render: `pnpm --filter @tm/shell test:e2e` (chromium/firefox/webkit), plus `test:visual` for the strip snapshot. Per the structural-PR lesson, run the full `@tm/shell` suite, not targeted filters, for anything touching pane chrome.
