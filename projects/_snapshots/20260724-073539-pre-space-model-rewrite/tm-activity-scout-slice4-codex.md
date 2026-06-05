# Transport Matters Activity Slice 4 Scout

Date: 2026-07-08
Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
SHA inspected: `787fffcbe67f0ddfb8ceb8718a4c7f1b317abe5a`
Scope: Control Center v1, per-pane vitals on the canvas
Mode: read-only repo scout. This artifact is the only allowed write.

Locked product decision from project context: Control Center v1 is per-pane vitals, not a separate board. Each captured-run pane gets a vitals strip under the pane title bar. Day-one vitals are context used, context remaining percent, cost dollars, time, and a status plus needs-you pill. The canvas subscribes once to workspace Activity SSE and fans vitals to panes by `run_id`. Context percent and cost require real model ceiling and pricing constants. No fake numbers.

## Reuse Map

### Pane chrome and placement

Use `www/packages/canvas/src/workbench/chrome/PaneChrome.tsx` as the mounting seam. `PaneChrome` already owns the shared title bar and body split:

1. `header.canvas-pane-window__header` contains title and actions.
2. `div.canvas-pane-window__body` contains viewer content.

The vitals strip belongs between those two regions so it is literally under the title bar and outside terminal content. Keep `PaneChrome` content-agnostic by adding a narrow optional slot or prop rather than making it understand Activity.

`www/packages/canvas/src/workbench/PaneWindow.tsx` is the thin adapter from `PaneRecord` to `PaneChrome`. It is the right place to pass a prepared strip down to chrome, or to pass a slot from `CanvasPaneLayer`.

`www/packages/canvas/src/workbench/CanvasPaneLayer.tsx` already has the full `PaneRecord` and wraps every rendered pane with `PaneWindow`. It can check `pane.contentRef.kind === "captured-run"` and decide whether a vitals strip exists. This keeps viewers as viewers.

Avoid mounting the strip inside `www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx`. That component should keep owning terminal attachment, focus, and spawn errors. Putting vitals inside it would make the terminal body carry cross-cutting pane chrome.

### Run identity

Captured-run pane records intentionally carry `runKey`, not backend `runId`:

1. `www/packages/canvas/src/model/paneRecords.ts` defines the captured-run content ref with `runKey`, provider, labels, template, worktree, and session metadata.
2. `www/packages/canvas/src/model/paneIdentity.ts` uses `runKey` as the pane identity for captured runs.
3. `www/packages/canvas/src/viewers/registry.tsx` passes `runKey` to `CapturedRunPane`.
4. `www/packages/canvas/src/infrastructure/runtime/useCapturedRunBinding.ts` resolves `runKey` to backend `runId`.
5. `www/packages/canvas/src/model/capturedRunStore.ts` stores `runs[runKey].runId`.

Reuse `useCapturedRunStore` as the run-key to run-id source. Do not persist backend `runId` into `PaneRecord` just to render vitals. The strip can render pending, empty, or unavailable until the store has a `runId`.

### Canvas styling

Reuse canvas local styling, not inspector styling:

1. `www/packages/canvas/src/workbench/chrome/pane-window.css` owns pane window header, body, focus, and drag states. Put chrome strip layout here or in a close sibling imported by chrome.
2. `www/packages/canvas/src/styles/tokens.css` owns canvas pane tokens, accents, shadows, and surfaces.
3. `www/packages/canvas/src/viewers/resource/exchange-viewer.css` has useful chip tone patterns in `canvas-exchange__chip[data-tone=...]`, but do not import inspector UI.
4. `www/packages/canvas/src/workbench/canvas.css` has compact label typography patterns for canvas surfaces.

The strip should use stable compact dimensions because `--pane-header` is currently fixed at `58px` and the pane body relies on `min-height: 0`. Let the body flex absorb the strip height. Small panes need truncation and collapse rules, not wrapping that changes terminal sizing unpredictably.

### Activity server surface

`packages/activity/src/server/activityRouter.ts` already exposes workspace activity:

1. List response through `GET /workspaces/:workspaceId(.+)/activity`.
2. Stream response through `GET /workspaces/:workspaceId(.+)/activity/stream`.
3. Gateway mount makes the browser path `/v1/workspaces/{workspaceId}/activity/stream?owner=local`.
4. Stream frames are data-only SSE with `snapshot` and `delta`.
5. `ActivityWireRun` already includes `run_id`, `harness`, `launch_kind`, `status`, `since_ts`, `initial_prompt`, `last_message`, `context_tokens`, `total_usage`, and `exit_reason`.

The route does not yet provide `model`, context ceiling, context remaining percent, or cost dollars. Those are the missing server-side enrichments for slice 4.

### Activity projection and storage

`packages/activity/src/projections/workspaceActivity.ts` owns the current read model through `RunActivityProjection`, `runActivityProjection`, and `sameRunActivityProjection`.

`packages/activity/src/domain/runActivityContext.ts` owns run statuses and context tokens. `packages/activity/src/domain/usage.ts` owns `UsageTotals`, `emptyUsage`, `addUsage`, and `windowTokens`.

Python session storage already captures model:

1. `api/src/transport_matters/session/models.py` has `EventRow.model` and `EventReadRow.model`.
2. `api/src/transport_matters/session/ingest.py` sets event model from normalized turns and meta events.
3. `api/src/transport_matters/session/dao_statements.py` includes `model` in persisted event columns.
4. `api/src/transport_matters/index/adapters/claude.py` reads provider message model.
5. `api/src/transport_matters/index/adapters/codex.py` threads Codex turn-context model hints.

`@tm/activity` currently drops that field:

1. `packages/activity/src/server/pgContracts.ts` does not list `model`.
2. `packages/activity/src/adapters/postgresRecords.ts` does not select it.
3. `packages/activity/src/adapters/transcriptRecords.ts` has no model field.
4. `RunActivityProjection` has no model field.
5. `ActivityWireRun` has no model field.

The reuse path is to thread existing stored model into Activity, then enrich the Activity projection or wire layer. Do not infer model in canvas.

### Browser core surface

`www/packages/core/src/transport.ts` already owns `apiUrl`, `requestApiJson`, and fetch helpers.

`www/packages/core/src/queryKeys.ts` owns shared query key names.

`www/packages/core/src/index.ts` is the browser package public barrel.

`www/packages/core/src/exchangeStreamEvents.ts` is the closest pure reducer pattern: browser code builds EventSource, core applies stream events.

There is no existing browser Activity client or Activity store in `@tm/core`. Add one focused Activity slice rather than putting stream parsing in canvas. That matches the locked design: canvas subscribes once and `@tm/core` fans vitals to panes by `run_id`.

### Existing token and readout reuse

`www/packages/core/src/formatting.ts` exports `contextTokens`, which calculates input plus cache creation plus cache read and excludes output. Reuse that convention in browser display. Do not add a third client-side token formula.

`packages/activity/src/domain/usage.ts` has `windowTokens` for the server domain shape. Reuse it server-side.

`www/packages/inspector/src/components/detail/TokenBar.tsx` is not reusable directly in canvas because canvas must not import inspector UI. It is still useful prior art for information density.

`www/packages/canvas/src/viewers/resource/ArkExchangeViewer.tsx` and `www/packages/inspector/src/components/ExchangeDetail.tsx` already duplicate a `tabReadout` style readout from the locked canvas fork. That duplication predates this slice. Do not add another copy in pane vitals.

No existing cost UI or pricing catalog was found in the scoped searches.

## Quality Map

### Boundary risks

Canvas guidance in `www/packages/canvas/CLAUDE.md` and `www/packages/canvas/src/OWNERSHIP.md` is clear: canvas depends on `@tm/core` and `@tm/host`, not `@tm/inspector`. Viewers render content only. Workbench owns route and pane orchestration. Model owns records and lifecycle. Infrastructure owns API clients, streams, persistence, and runtime.

Do not deep import `@tm/activity` internals from browser packages. Root `packages/AGENTS.md` requires each root package to expose one public entrypoint, and the shell boundary tests enforce that shape.

There is a real contract duplication tension: `ActivityWireRun` lives server-side in `@tm/activity`, while browser DTOs normally live in `@tm/core`. Importing `@tm/activity` into browser code just for types could pull the wrong package boundary. The safer reuse is to define browser-facing DTO types in `@tm/core` and add contract tests or shared fixtures against the Activity route.

### Decision needed

The biggest unresolved decision is the authoritative source of truth and update policy for model context ceilings and pricing. The repo has recommended runtime-template model metadata, but that is not a pricing or context-window catalog.

Recommended constraint: keep model metadata in `@tm/activity` for this slice because the server should enrich Activity with context remaining percent and cost dollars. Unknown models should keep raw tokens and omit percent or dollars rather than estimate. Promote to `@tm/common` only if another bounded context needs the same domain metadata.

### Duplication watch

Known duplication to avoid:

1. Do not duplicate `runKey` to `runId` mapping in pane records. Reuse `capturedRunStore`.
2. Do not duplicate EventSource subscriptions per pane. Subscribe once per canvas workspace and fan out by `run_id`.
3. Do not duplicate token math in canvas. Use `@tm/core/contextTokens` in browser and `@tm/activity/windowTokens` on the server.
4. Do not duplicate inspector `TokenBar` into canvas. Build a canvas-native vitals strip that uses shared core formatting and canvas tokens.
5. Do not invent fallback costs, prices, or context windows.

No dead code was found in the scoped search. No existing Activity browser client exists to replace.

### Size and hygiene

Scoped files are below the 700 line threshold:

1. `PaneChrome.tsx`: 111 lines.
2. `PaneWindow.tsx`: 51 lines.
3. `CanvasPaneLayer.tsx`: 228 lines.
4. `capturedRunStore.ts`: 303 lines.
5. `CapturedRunPane.tsx`: 136 lines.
6. `www/packages/core/src/transport.ts`: 474 lines.
7. `packages/activity/src/server/activityRouter.ts`: 278 lines.
8. `packages/activity/src/projections/workspaceActivity.ts`: 296 lines.

The implementation can stay below thresholds if it adds focused files for model metadata, core Activity state, and pane vitals rather than growing shared workbench files heavily.

## Plan

1. Thread model through Activity.

   Add `model` to the Activity Postgres contract, selected rows, transcript record shape, run context or projection, and `ActivityWireRun`. Use the existing Python session model field as the source. Update focused Activity tests around Postgres contracts, transcript records, projections, and router wire output.

2. Add real model metadata and enrichment in `@tm/activity`.

   Add a pure model metadata table for day-one supported models with context ceilings and pricing. Add helpers for context remaining percent and cost dollars. Unknown models return null or omitted enriched values. Raw token totals remain visible.

3. Add a browser Activity slice in `@tm/core`.

   Add Activity DTO types for the `/v1` response, query keys, list fetcher, stream URL builder, and a pure frame parser or reducer for `snapshot` and `delta`. Export through the public barrel. Keep browser EventSource construction out of low-level parsing.

4. Subscribe once from the canvas workspace.

   In the canvas route or workbench owner, open one workspace Activity stream for the current workspace id and owner. Seed from the snapshot, apply deltas, and store vitals keyed by backend `run_id`. Use existing `apiUrl` and core stream helpers where they fit.

5. Resolve pane vitals by existing run binding.

   For captured-run panes, map `pane.contentRef.runKey` through `useCapturedRunStore.runs[runKey].runId`, then read that run's vitals from the core Activity slice. Show pending or unavailable states until `runId` or Activity data exists.

6. Add the pane strip through chrome.

   Add a `PaneChrome` strip slot or equivalent narrow prop. `CanvasPaneLayer` or `PaneWindow` prepares the strip only for captured-run panes. Keep `CapturedRunPane` terminal logic unchanged.

7. Verify boundaries and behavior.

   Suggested gates for the implementation slice: `pnpm --filter @tm/activity test`, `pnpm --filter @tm/activity typecheck`, `pnpm --filter @tm/core typecheck`, `pnpm --filter @tm/canvas typecheck`, shell boundary tests, `just check`, and `just test`. Add a canvas visual or Playwright check for multiple panes, small panes, no data, unknown model, and needs-you status.

## Headline

Key reuse finding: PaneChrome plus capturedRunStore already provide the right UI and identity seams, and the Activity stream already exposes most per-run data. The missing reusable contract is model-aware Activity enrichment. Single biggest decision-needed: where the authoritative model ceiling and pricing catalog lives and how unknown models are handled without fake numbers.
