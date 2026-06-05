---
title: Ordered gridFit Spec Review for Transport Matters
type: research
tags: [transport-matters, captured-canvas, gridfit, design-review, helioy-bus]
summary: Review of the ordered gridFit canvas spec found two conditional signoff issues around live reflow motion and ViewerRegistration ownership.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Executive Summary

A bus review requested independent signoff for `NOTES/captured-canvas/17-ordered-gridfit.md` against `main` at `46982ad`. The spec direction is feasible overall, but I sent conditional signoff because live reflow depends on pane position motion that current code disables by default, and one cited type is owned by a different file than the spec names.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
- Baseline: `main` at `46982ad`
- fmm: indexed with `.fmm.db`, 687 files and 104,318 LOC
- Frontend: TypeScript, React 19, Vite, Zustand, Framer Motion, `@use-gesture/react`
- Package manager: `pnpm@10.8.1` for `www` and `desktop`
- API: Python `>=3.14`, FastAPI, Pydantic settings, mitmproxy, psycopg, Alembic
- Repo gates named by `just --summary`: `check`, `test`, `www`, `api`, `desktop`, `build`

## Architecture

The relevant canvas stack has three layers:

1. Engine layout primitives in `www/src/engine/` own `EngineLayoutState`, node reducers, layout strategies, and generic React canvas primitives.
2. Session canvas model code in `www/src/session-canvas/model/` and `www/src/session-canvas/lab/` owns active strategy state, spawn flows, pane records, and store actions for `/canvas` and `/canvas-lab`.
3. Session canvas DnD, viewer, and persistence modules in `www/src/session-canvas/dnd/`, `viewers/`, and `persistence/` own terminal drop delivery, viewer registrations, and persisted pane snapshots.

`PlanInput` already carries ordered `paneIds` to every strategy, and `gridFit`, `singleRow`, and `gridOverflow` all place panes by array index. This supports the spec direction of modeling user control as an ordered pane sequence rather than as per pane positions.

## Key Patterns

- Layout strategies are pure planners over `PlanInput.paneIds`, viewport bounds, and parameters. See `www/src/engine/layout/types.ts:39` and `www/src/engine/layout/strategies/gridFit.ts:144`.
- Node lifecycle changes flow through engine reducers such as `upsertNode` and `removeNode`, so adding `EngineLayoutState.order` needs reducer level maintenance. See `www/src/engine/reducers/layoutState.ts:42` and `www/src/engine/reducers/layoutState.ts:111`.
- Store spawn flows in both `/canvas` and `/canvas-lab` consume the same layout planning seam. See `www/src/session-canvas/model/layoutPlanning.ts:55`, `www/src/session-canvas/model/canvasStore.ts:273`, and `www/src/session-canvas/lab/canvasLabLayout.ts:48`.
- Persistence rebuild currently derives open pane order from persisted `paneRects` object iteration after seeding nodes. See `www/src/session-canvas/persistence/canvasPanePersistence.ts:100` and `www/src/session-canvas/persistence/canvasPanePersistence.ts:271`.

## Detailed Findings

### Conditional issue 1, live reflow motion needs an explicit motion path

`17-ordered-gridfit.md` says other panes should spring around during live reflow, with Framer Motion already animating replanned rects. Current `PaneFrame` position animation snaps x and y unless `layoutMotion` is true. `/canvas` does not pass `paneMotion`, and `/canvas-lab` only raises `paneMotion` during explicit fly or pane motion intents.

Evidence:

- `PaneFrame` chooses `SNAP_TRANSITION` for x and y when `layoutMotion` is false in `www/src/engine/react/PaneFrame.tsx:70`, then assigns it to x and y in `www/src/engine/react/PaneFrame.tsx:147` and `www/src/engine/react/PaneFrame.tsx:148`.
- `LayoutCanvas` defaults `paneMotion = false` in `www/src/engine/react/LayoutCanvas.tsx:91` and passes that to `PaneFrame` as `layoutMotion` in `www/src/engine/react/LayoutCanvas.tsx:65`.
- `/canvas` renders `LayoutCanvas` without `paneMotion` in `www/src/session-canvas/components/CanvasSurface.tsx:131` through `www/src/session-canvas/components/CanvasSurface.tsx:142`.
- `/canvas-lab` passes `paneMotion`, but store code only sets it during `startFlyForIntent` or `startFly` in `www/src/session-canvas/lab/canvasLabStore.ts:343` through `www/src/session-canvas/lab/canvasLabStore.ts:358`.

Required spec correction: specify how reorder replans enable motion for non lifted panes, or change the live reflow promise so snapping is the intended behavior.

### Conditional issue 2, ViewerRegistration ownership citation is wrong

The spec says `viewers/registry.tsx ViewerRegistration` gains `bodyDrag?: boolean`. The registry file imports and instantiates viewer registrations, but the `ViewerRegistration` interface is defined in `www/src/session-canvas/model/paneRecords.ts`.

Evidence:

- `ViewerRegistration` definition: `www/src/session-canvas/model/paneRecords.ts:197` through `www/src/session-canvas/model/paneRecords.ts:204`.
- Registry imports the type from `../model/paneRecords`: `www/src/session-canvas/viewers/registry.tsx:3` through `www/src/session-canvas/viewers/registry.tsx:13`.
- The resource viewer registration lives in `www/src/session-canvas/viewers/registry.tsx:71` through `www/src/session-canvas/viewers/registry.tsx:80`, so that file is still the right place to set the resource `bodyDrag` opt in.

Required spec correction: cite `model/paneRecords.ts:ViewerRegistration` as the type owner and `viewers/registry.tsx` as the registration site.

### Other checklist results

- `PlanInput` exists and carries an ordered `paneIds` array: `www/src/engine/layout/types.ts:39` through `www/src/engine/layout/types.ts:43`.
- `gridFit` fills cells by index: `www/src/engine/layout/strategies/gridFit.ts:180` through `www/src/engine/layout/strategies/gridFit.ts:193`.
- `openPaneIds` currently uses `Object.values(layout.nodes)`, so the spec correctly identifies the seam that must switch to `layout.order`: `www/src/session-canvas/model/layoutPlanning.ts:45` through `www/src/session-canvas/model/layoutPlanning.ts:49`.
- `PaneFrame` already has move drag and `onMoveEnd`: `www/src/engine/react/PaneFrame.tsx:80` through `www/src/engine/react/PaneFrame.tsx:123`.
- `deliverPaneDropToTerminal` exists and checks locator plus paste handle before pasting: `www/src/session-canvas/dnd/canvasDrop.ts:107` through `www/src/session-canvas/dnd/canvasDrop.ts:126`.
- `useCanvasDropTargets` handles HTML5 `dragover` and `drop`, and wires pane move end delivery: `www/src/session-canvas/dnd/useCanvasDropTargets.ts:34` through `www/src/session-canvas/dnd/useCanvasDropTargets.ts:68`.
- `partializeCanvasState` persists `paneRects`, dock state, strategy, params, fit state, and expanded pane id today: `www/src/session-canvas/persistence/canvasPersistOptions.ts:59` through `www/src/session-canvas/persistence/canvasPersistOptions.ts:72`.
- The target tree was clean before the bus reply. `git status --short` returned no output.

## Dependencies

- `framer-motion` drives pane transform and layout animations.
- `@use-gesture/react` drives pane move and resize gestures.
- `zustand` and `zustand/middleware` provide canvas state and persisted snapshots.
- The engine layout registry and strategy modules provide pure layout planning.

## Relevance to Helioy

This review keeps the captured canvas model aligned with Helioy design principles: put durable user intent in the model, keep strategy planners pure, and avoid adding a second freeform layout path until product semantics require it. The conditional issues are small but important because they prevent a spec from promising behavior the current motion layer will not produce.

## Open Questions

- Should reorder motion reuse `paneMotion`, add a narrower `reorderMotion` flag, or create a separate transition profile for non lifted panes?
- Should `deliverPaneDropToTerminal` return delivery status, or should the new shared drop target resolver decide terminal delivery before calling it?
- Should `insertionIndexAtWorldPoint` explicitly operate on rects with the lifted pane removed and return `0` for an empty list?
