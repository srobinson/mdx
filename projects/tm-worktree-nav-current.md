---
title: Current Worktree Launcher Navigation Behavior
type: research
tags: [transport-matters, launcher, worktree, canvas, command-center]
summary: Selecting a worktree in ⌘K changes the canvas root in place through URL state and canvas store reinitialization. It does not relaunch desktop or spawn an isolated run.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-25
updated: 2026-06-25
---

## Executive Summary

The ⌘K Workdir and Worktree scopes are backed by the persisted Spaces API. Selecting a worktree is a client side canvas root switch: Enter runs `select-worktree`, rewrites the current URL query, and calls `initializeCanvas()` in the existing app. ArrowRight does nothing on a concrete worktree row.

This route is nav only. It does not invoke the desktop relaunch path, and it does not spawn or focus a captured run through RunManager.

## Project Metadata

- Frontend: React 19, TypeScript, Vite, Ark UI Combobox, TanStack Query, Zustand.
- Backend: FastAPI, Pydantic, Psycopg, Postgres backed Spaces store.
- Relevant command center files: `www/src/session-canvas/launcher/commandModel.ts`, `CommandCenter.tsx`, `useCommandCenter.ts`, `useLauncherRows.ts`, `useLauncherInputKeys.ts`.
- Relevant Spaces files: `www/src/api.ts`, `www/src/session-canvas/launcher/useSpaces.ts`, `api/src/transport_matters/api/v1/space_routes.py`, `api/src/transport_matters/space/store.py`, `api/src/transport_matters/space/detection.py`.

## Architecture

### Row data flow

1. Space detection enters the backend through `SpaceStore.resolve_cwd()`, which calls `detect_space()` and persists the result with `upsert_detection()` when creation is enabled. `detect_space()` probes Git with `rev-parse`; for repos it calls `_detect_git_worktrees()`, which runs `git worktree list --porcelain -z`. Evidence: `api/src/transport_matters/space/store.py:SpaceStore.resolve_cwd` lines 51 to 61, `api/src/transport_matters/space/detection.py:detect_space` lines 48 to 100, `_detect_git_worktrees` lines 123 to 152, `SpaceStore.upsert_detection` lines 75 to 103.
2. The launcher itself does not shell out. It calls `useSpaces()`, which uses React Query to call `fetchSpaces()`. `fetchSpaces()` issues `GET /v1/spaces`. The route reads stored spaces through `SpaceStore.list_spaces()` and inlines worktrees in the response. Evidence: `www/src/session-canvas/launcher/useSpaces.ts:useSpaces` lines 11 to 19, `www/src/api.ts:fetchSpaces` lines 415 to 423, `api/src/transport_matters/api/v1/space_routes.py:list_spaces` lines 285 to 305, `api/src/transport_matters/space/store.py:SpaceStore.list_spaces` lines 105 to 130.
3. `CommandCenter` reads `defaultWorktreeId` from `useCanvasStore` and passes it as `activeWorktreeId` into `useCommandCenter()`. `useLauncherRows()` passes that value into `buildScopeRows()`. Evidence: `www/src/session-canvas/launcher/CommandCenter.tsx:CommandCenter` lines 31 to 46, `www/src/session-canvas/launcher/useCommandCenter.ts:useCommandCenter` lines 268 to 282, `www/src/session-canvas/launcher/useLauncherRows.ts:useLauncherRows` lines 54 to 80.

### Current badge logic

- Workdir rows are produced by `buildSpaceRows()`. A single-worktree space gets a direct `select-worktree` action. A multi-worktree space gets an `enter` action into the Worktree sub-scope. The Workdir row shows `Current` only when the space has one worktree and that worktree id equals `activeWorktreeId`. Evidence: `www/src/session-canvas/launcher/commandModel.ts:buildSpaceRows` lines 376 to 412.
- Worktree sub-scope rows are produced by `buildWorktreeRows()`. One row is created for each `space.worktrees` item under the nav param space id. The row shows `Current` when `worktree.worktreeId === activeWorktreeId`. Missing worktrees are disabled and get no action. Evidence: `www/src/session-canvas/launcher/commandModel.ts:buildWorktreeRows` lines 415 to 456.

## Detailed Findings

### What Enter, labeled `↵ run`, does

On a concrete worktree row, `buildWorktreeRows()` assigns a command action:

- `kind: "command"`
- `command.kind: "select-worktree"`
- `spaceId: space.spaceId`
- `worktreeId: worktree.worktreeId`

Evidence: `www/src/session-canvas/launcher/commandModel.ts:buildWorktreeRows` lines 431 to 453.

`select-worktree` is not listed in `COMMAND_INTERACTIONS`, so `interactionFor()` falls back to `RUN_AND_CLOSE`. Enter dispatches the command and closes the palette. Evidence: `www/src/session-canvas/launcher/commandModel.ts` lines 124 to 130 and `interactionFor` lines 136 to 145; `www/src/session-canvas/launcher/useCommandCenter.ts:useLauncherActionInterpreter` lines 95 to 123.

The command handler case rewrites query params and reinitializes the current canvas:

1. `worktreeSwitchUrl()` sets `space_id` and `worktree_id`, deletes `canvas_id`, and preserves other query params.
2. `window.history.replaceState()` applies that URL.
3. `initializeCanvas(parseCanvasLaunchContext(window.location.search))` reroots the canvas store from the new query.

Evidence: `www/src/session-canvas/components/CanvasSurface.tsx:useCanvasCommandHandler` lines 109 to 126, `www/src/session-canvas/route.ts:worktreeSwitchUrl` lines 52 to 64, `www/src/session-canvas/route.ts:parseCanvasLaunchContext` lines 19 to 30.

### What ArrowRight, labeled `→ enter`, does

On a concrete worktree row, ArrowRight does nothing. `interactionFor()` returns `advance: "none"` for `select-worktree` via the default `RUN_AND_CLOSE`. `useLauncherInputKeys()` only calls `applyGesture()` when the ArrowRight lifecycle is not `none`. Evidence: `www/src/session-canvas/launcher/commandModel.ts` lines 124 to 130 and `interactionFor` lines 136 to 145; `www/src/session-canvas/launcher/useLauncherInputKeys.ts:useLauncherInputKeys` lines 50 to 62.

The footer is static outside the root domain view. It always says `↵ run · → enter · ⌫ back · esc close`, even for rows whose ArrowRight behavior is `none`. Evidence: `www/src/session-canvas/launcher/CommandCenter.tsx` line 23 and lines 61 to 67.

### Workdir row nuance

In Workdir scope, the row represents a Space, not always a worktree:

- Multi-worktree repo Space: Enter and ArrowRight both descend into the Worktree sub-scope because the row action is `enter` and `SCOPE_INTERACTION` maps both gestures to `descend`. Evidence: `www/src/session-canvas/launcher/commandModel.ts:buildSpaceRows` lines 391 to 410 and constants at lines 124 to 125.
- Single-worktree plain Space: Enter runs `select-worktree`; ArrowRight does nothing, the same as a concrete Worktree row. Evidence: `www/src/session-canvas/launcher/commandModel.ts:buildSpaceRows` lines 391 to 408 and `interactionFor` lines 136 to 145.

Tests encode this model: multi-worktree Space descends, single-worktree Space selects directly, and Worktree sub-scope rows carry `select-worktree`. Evidence: `www/src/session-canvas/launcher/commandModel.test.ts` lines 429 to 465.

## Which Subsystem It Hits

Subsystem: nav only.

The selected worktree path stays inside the current frontend app. It uses `window.history.replaceState()` and `useCanvasStore.getState().initializeCanvas()`. It does not call the desktop launcher, it does not call `/v1/runs`, it does not call `addCapturedRun()`, and it does not allocate per-run ports.

The captured run path is separate: `spawn` commands call `addCapturedRun()`, which reads the current `defaultWorktreeId` and creates a captured run pane ref. Selecting a worktree only changes the default root used by later captured run spawns. Evidence: `www/src/session-canvas/components/CanvasSurface.tsx:useCanvasCommandHandler` lines 80 to 90 and 109 to 126; `www/src/session-canvas/model/canvasStore.ts` lines 136 to 147.

## Coupling and Quirks

1. One active worktree root per canvas store. The active badge and future captured run spawns are tied to `useCanvasStore.defaultWorktreeId`. Evidence: `www/src/session-canvas/launcher/CommandCenter.tsx:CommandCenter` lines 37 to 45 and `www/src/session-canvas/model/canvasStore.ts` lines 136 to 147.
2. Same Space, different worktree: `defaultCanvasId()` derives the default canvas id from `spaceId`, not `worktreeId`. Switching worktrees inside one repo Space keeps the same `space:<spaceId>` canvas id. `initializeCanvas()` takes the same-canvas path and preserves existing panes/layout while refreshing `defaultWorktreeId`. Evidence: `www/src/session-canvas/route.ts:defaultCanvasId` lines 38 to 42 and `www/src/session-canvas/model/canvasStore.ts` lines 222 to 259.
3. Different Space: the canvas id changes to `space:<newSpaceId>`. `initializeCanvas()` resets to that Space's initial model and rehydrates that canvas cache. Evidence: `www/src/session-canvas/model/canvasStore.ts` lines 222 to 259 and `createInitialCanvasModel` lines 397 to 427.
4. The switch command carries only `spaceId` and `worktreeId`. `worktreeSwitchUrl()` does not compute a selected worktree `workspace_hash`; it preserves whatever was already in the query string. Since `parseCanvasLaunchContext()` reads `workspace_hash` from the URL, session browsing can remain scoped to a preexisting workspace hash after an in-place worktree switch. Evidence: `www/src/session-canvas/launcher/commandModel.ts` lines 95 to 104, `www/src/session-canvas/route.ts:worktreeSwitchUrl` lines 52 to 64, `parseCanvasLaunchContext` lines 19 to 30, and `www/src/session-canvas/launcher/useCommandCenter.ts:useCommandCenter` lines 220 to 226.

## Verification

- Structural navigation used fmm first: top-level topology, command model outlines, symbol reads, and dependency graphs.
- Ran frontend tests: `cd www && pnpm test -- src/session-canvas/launcher/commandModel.test.ts src/session-canvas/launcher/useCommandCenter.test.tsx src/session-canvas/route.test.ts src/session-canvas/model/canvasStore.test.ts`.
- Observed result: `Test Files 146 passed (146)`, `Tests 1057 passed (1057)`.
- Repository worktree remained clean after inspection: `git status --short` produced no output.

## Relevance to Helioy

For Helioy operator UX, the current launcher behavior switches the app's active canvas root rather than creating isolated per-worktree runtime contexts. That makes the feature fast and lightweight, but a user choosing another worktree is not launching a new desktop channel or a contained RunManager session.

## Open Questions

1. Should ArrowRight on a concrete worktree row be hidden or mapped to the same action as Enter so the footer does not overpromise?
2. Should selecting a worktree update `workspace_hash` from the selected worktree summary, or should Sessions move to `spaceId/worktreeId` filtering for this scope?
3. Should same-Space worktree switching preserve panes by design, or should each worktree get its own default canvas id?
## Follow-up: Pane Preservation and Spawn Targeting

- Same-Space worktree switches preserve existing panes. `CanvasSurface.tsx:useCanvasCommandHandler` handles `select-worktree` by replacing the URL query and calling `useCanvasStore.initializeCanvas()`. `initializeCanvas()` computes `switchingCanvas = get().canvasId !== defaultCanvasId(launch)`; when the canvas id is unchanged, it keeps the existing state object and only refreshes `canvasId`, `spaceId`, `defaultWorktreeId`, `launch`, and `workspaceHash`. Evidence: `www/src/session-canvas/components/CanvasSurface.tsx:useCanvasCommandHandler` lines 109 to 126; `www/src/session-canvas/model/canvasStore.ts:useCanvasStore.initializeCanvas` lines 222 to 259; `www/src/session-canvas/route.ts:defaultCanvasId` lines 38 to 42.
- Cross-Space switches are different. If the selected Space changes the default canvas id, `initializeCanvas()` calls `set(createInitialCanvasModel(launch))`, which starts the target canvas from its initial model and then rehydrates its per-canvas cache. Current open panes from the prior canvas are not carried into that target canvas. Evidence: `www/src/session-canvas/model/canvasStore.ts:useCanvasStore.initializeCanvas` lines 236 to 258; `createInitialCanvasModel` lines 397 to 427.
- The launcher has no per-spawn worktree picker. Agent rows emit `spawn` commands with only `harness` and optional `runtimeTemplate`; `useCanvasCommandHandler` forwards those to `addCapturedRun()`, and `addCapturedRun()` reads `get().defaultWorktreeId` to stamp the captured-run ref. `CapturedRunPane` then passes that ref worktree id into `ensureRun()`, which calls `createCapturedRun()` and sends `worktreeId` in the POST body. Evidence: `www/src/session-canvas/launcher/commandModel.ts:agentSpawnRows` lines 207 to 237; `www/src/session-canvas/components/CanvasSurface.tsx:useCanvasCommandHandler` lines 80 to 90; `www/src/session-canvas/model/canvasStore.ts:useCanvasStore.addCapturedRun` lines 136 to 148; `www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx:CapturedRunPane` lines 33 to 60; `www/src/session-canvas/model/capturedRunStore.ts:useCapturedRunStore` lines 146 to 168; `www/src/api.ts:createCapturedRun` lines 447 to 483.
- Coexisting agent panes in different worktrees are reachable only by changing the global default between spawns. Spawn in worktree A, select worktree B, then spawn again. There is no single ⌘K spawn action that carries a chosen worktree independent of `defaultWorktreeId`.

### Follow-up Verification

- Ran `cd www && pnpm test -- src/session-canvas/model/canvasStore.test.ts src/session-canvas/launcher/commandModel.test.ts src/session-canvas/viewers/terminal/CapturedRunPane.test.tsx src/api.test.ts`.
- Observed result: `Test Files 146 passed (146)`, `Tests 1057 passed (1057)`.
