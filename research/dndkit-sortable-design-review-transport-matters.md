---
title: dnd-kit Sortable Design and Implementation Review for Transport Matters
type: research
tags: [transport-matters, captured-canvas, dnd-kit, sortable, review]
summary: The corrected dnd-kit design and final hardening delta were verified clean through ff76086, with earlier scale and hero-droppable blockers resolved.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Executive Summary

Transport Matters replaced the hand rolled session canvas reorder controller with dnd-kit sortable primitives. The corrected design proves the scaled active drag contract, the implementation fixed the expanded hero droppable blocker at `9bc596f`, and the final hardening delta `9bc596f..ff76086` verified clean.

Final bus verdict sent on 2026-06-12: `review: clean 9bc596f..ff76086` and `signoff: I sign off on the dnd-kit implementation at ff76086 as currently filed`.

## Project Metadata

1. Repository: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
2. Branch reviewed: `feat/ordered-gridfit`
3. Final commit reviewed: `ff76086`
4. Deltas reviewed:
   - Design pass at `e7dead7`
   - Initial implementation pass `e7dead7..30ffb44`
   - Hero and ghost-trail correction pass `30ffb44..9bc596f`
   - Final hardening pass `9bc596f..ff76086`
5. fmm status: `.fmm.db` present and used for structural orientation.
6. Frontend stack: React in `www/`, pnpm scripts, Vitest, Playwright, TypeScript project references, Vite.
7. dnd-kit dependencies proposed by the design: `@dnd-kit/core@6.3.1`, `@dnd-kit/sortable@10.0.0`, `@dnd-kit/utilities`.

## Architecture

The dnd-kit implementation uses these seams:

1. `CanvasPaneDnd` owns `DndContext`, world rect measuring, collision detection, and pane drag callbacks. It passes the same planner world measurement seam to draggable and droppable measuring (`www/src/session-canvas/dnd/CanvasPaneDnd.tsx:47-53`).
2. `CanvasSurface` and `CanvasLabRoute` pass `getExpandedPaneId()` into the dnd callbacks and keep side `SortableContext` ids filtered to non-expanded panes (`www/src/session-canvas/components/CanvasSurface.tsx:64-83`; `www/src/session-canvas/lab/CanvasLabRoute.tsx:82-101`).
3. `SortablePane` keeps the expanded hero droppable while disabling only lift for that pane through `disabled: { draggable: liftDisabled, droppable: false }` (`www/src/session-canvas/dnd/SortablePane.tsx:21-39`).
4. `paneDndCallbacks` resolves terminal delivery before reorder, then blocks reorder when `overId` is the expanded pane (`www/src/session-canvas/dnd/paneDndCallbacks.ts:100-123`).
5. `PaneFrame` computes rest positions from exact planner rects and rounds only transform-composed live drag positions through `dndPanePosition()` (`www/src/engine/react/PaneFrame.tsx:96-102`, `185-190`, `214-220`).

## Key Patterns

1. **World measurement is the correctness seam.** dnd-kit screen coordinates are reconciled with Transport Matters world coordinates by measuring panes from planner world rects for both draggable and droppable targets.
2. **Active and sibling transforms have different contracts.** The active pane divides the dnd-kit transform by `viewport.scale` exactly once. Sibling transforms apply raw world pixel shifts (`www/src/session-canvas/dnd/dndSpace.ts:112-120`).
3. **Expanded hero panes are delivery targets, not reorder members.** The side column excludes the hero from sortable ids, but `useSortable` keeps its droppable side enabled so collision can report the hero as `over`.
4. **Delivery mode is represented by no reorder target.** `createWorldSpaceCollision()` returns no collisions while a locator-bearing active hovers a registered paste handle, which stops sibling shifts and keeps the paste target stationary (`www/src/session-canvas/dnd/dndSpace.ts:68-104`).
5. **Cursor language is projected outside React.** `CanvasPaneDnd` reads `dropTargetStore` after the move callback and writes `body[data-pane-drag-cursor]`, avoiding a new PaneLayer subscription or per-tick pane render path (`www/src/session-canvas/dnd/CanvasPaneDnd.tsx:81-90`; `www/src/session-canvas/dnd/dragCursor.ts:10-17`).

## Detailed Findings

### Design correction verified clean

The first design pass had a blocker: at scale `0.78`, the active pane tracked at roughly `1.282` instead of `1.00`, contradicting the stated active transform contract. The corrected design fixed that by replacing dnd-kit's default transform agnostic rect measurement with planner world rect measurement for both draggable and droppable rects.

Observed repro evidence from `NOTES/captured-canvas/19-dndkit-scale-repro.html`:

| Scenario | Scale | Verdict | Visual ratio | Sibling ratio | End over | Order |
| --- | ---: | --- | --- | ---: | --- | --- |
| `contract-world-s078` | `0.78` | PASS | `{x: 1, y: 1}` | `1` | `E` | `BCDEAF` |
| `contract-world-s100` | `1.00` | PASS | `{x: 1, y: 1}` | `1` | `E` | `BCDEAF` |
| `contract-world-s150` | `1.50` | PASS | `{x: 1, y: 1}` | `1` | `E` | `BCDEAF` |

Negative controls failed as intended:

| Mutation | Verdict | s=0.78 ratio | Expected failure |
| --- | --- | --- | --- |
| `?mutate=double` | FAIL | `{x: 1.282, y: 1.282}` | conversion applied twice |
| `?mutate=raw` | FAIL | `{x: 0.78, y: 0.78}` | conversion skipped |

### Initial implementation blocker at 30ffb44

Implementation review of `e7dead7..30ffb44` found one blocker. Expanded hero panes were excluded from `sortablePaneIds` and disabled as both draggable and droppable through `useSortable()`, with no plain `useDroppable` replacement. A side pane released over the expanded hero could miss the hero as an `over` target, fall back to a closest side pane, and reorder the side column.

Evidence at `30ffb44`:

1. `CanvasSurface.tsx:32-34`, `79-80` excluded the expanded pane and made it disabled.
2. `SortablePane.tsx:23-26` passed the disabled flag to both draggable and droppable sides.
3. `paneDndCallbacks.ts:97-102` committed reorder for any non-active `event.over`.
4. No `useDroppable` registration existed under `www/src`.

### Hero blocker resolved at 9bc596f

Commit `c8027e0` resolved the hero blocker. `SortablePane` now computes `liftDisabled` and calls `useSortable({ id: paneId, disabled: { draggable: liftDisabled, droppable: false } })`, so the hero remains a collision target while it cannot be lifted (`www/src/session-canvas/dnd/SortablePane.tsx:21-39`).

Regression coverage:

1. `paneDndCallbacks.test.ts:187-198` verifies non-locator release over the expanded hero is no-op, does not commit reorder, and returns `settle: false`.
2. `paneDndCallbacks.test.ts:200-208` verifies a locator without a paste handle over the expanded hero never reorders.
3. `paneDndCallbacks.test.ts:210-221` verifies a locator over the expanded hero with a paste handle delivers and never reorders.
4. `www/tests/e2e/canvas-lab-drag.spec.ts:176-207` expands the first pane, drags a side pane over the hero, releases, and asserts the side pane returns to its side slot while the hero stays put.

### Ghost-trail quantization resolved at 9bc596f

Commit `9bc596f` added whole world pixel quantization for live drag positions. `dndPanePosition(rect, null)` returns exact planner coordinates, while a live transform returns `roundWorldPoint({ x: rect.x + transform.x, y: rect.y + transform.y })` (`www/src/engine/react/PaneFrame.tsx:214-220`).

Regression coverage:

1. `dndPanePosition.test.ts:7-9` covers exact null transform positions.
2. `dndPanePosition.test.ts:11-16` covers live transform quantization.
3. `dndSpace.test.ts:167-196` still validates the active transform seam across scales `0.5`, `0.78`, `1.0`, and `1.5`, with skipped and doubled conversion guards.

### Final hardening delta verified clean at ff76086

Review of `9bc596f..ff76086` found no remaining blockers.

1. `94e92f1` centralizes pane rounding at `planLayout()` after either the active strategy or `planExpandedLayout()` returns planned rects (`www/src/session-canvas/model/layoutPlanning.ts:83-99`). That covers all strategies and the expanded planner. `fitViewport()` still computes fractional `scale`, `panX`, and `panY` without rounding (`www/src/session-canvas/model/layoutPlanning.ts:117-132`). `moveRect()`, `resizeRect()`, and `dndPanePosition()` all round through the shared geometry helpers (`www/src/engine/reducers/paneLifecycle.ts:22-41`; `www/src/engine/react/PaneFrame.tsx:214-220`). Persistence still collects and rebuilds rects directly, without re-planning or rounding persisted payloads (`www/src/session-canvas/persistence/canvasPersistOptions.ts:59-73`; `www/src/session-canvas/persistence/canvasPanePersistence.ts:68-78`, `280-323`).
2. `42e4e49` changes close/minimize camera behavior only through `dismissPane()` and its two store callers (`www/src/session-canvas/model/paneAffordances.ts:83-97`; `www/src/session-canvas/model/canvasStore.ts:336-350`; `www/src/session-canvas/lab/canvasLabStore.ts:113-123`). `finalizePaneDismissal()` refits stale fit-to-content cameras, keeps zoom-in reset, and preserves fit-to-content-off user cameras (`www/src/session-canvas/model/paneAffordances.ts:219-270`). Tests cover stale wide camera refit, zoom-in reset, already fitted no-op, and fit-to-content-off preservation (`www/src/session-canvas/model/paneAffordances.test.ts:55-95`).
3. `df38418` adds `runDockPaneFlow()` as the shared direct-dock seam (`www/src/session-canvas/model/paneAffordances.ts:352-365`). `canvasStore` and `canvasLabStore` both use it; open refs minimize, never-opened refs park directly in `docked` without mutating layout (`www/src/session-canvas/model/canvasStore.ts:97-273`; `www/src/session-canvas/lab/canvasLabStore.ts:125-350`). Tests prove both stores keep the layout reference unchanged for direct dock (`www/src/session-canvas/model/canvasStore.test.ts:126-140`; `www/src/session-canvas/lab/canvasLabStore.test.ts:51-66`).
4. `55fe86c` adds `deliveryTargetAt()` as the single resolution function for collision suppression, move highlight, and release delivery (`www/src/session-canvas/dnd/paneDndCallbacks.ts:47-58`, `90-123`; `www/src/session-canvas/dnd/CanvasPaneDnd.tsx:57-66`). Collision suppression only engages when the active pane has a locator and the target under the point has a registered paste handle (`www/src/session-canvas/dnd/dndSpace.ts:68-104`). Tests verify suppression over delivery and normal reorder targeting after hover-out (`www/src/session-canvas/dnd/dndSpace.test.ts:142-164`), plus move highlight clear on hover-out (`www/src/session-canvas/dnd/paneDndCallbacks.test.ts:157-170`).
5. `ff76086` adds cursor language by projecting from `dropTargetStore` to a body dataset attribute (`www/src/session-canvas/dnd/CanvasPaneDnd.tsx:81-90`; `www/src/session-canvas/dnd/dragCursor.ts:10-17`). `PaneLayer` remains memoized and only depends on pane and layout props; it has no subscription to cursor state (`www/src/engine/react/LayoutCanvas.tsx:56-64`, `171-184`).

### Final verification

Final verification ran in clean temp checkout `/tmp/tm-clean-ff76086-ydSbEL` at `ff76086`, with `www/node_modules` symlinked from the source checkout.

```bash
git status --short
# no output

cd www && pnpm exec vitest run \
  src/engine/layout/geometry.test.ts \
  src/engine/reducers/paneLifecycle.test.ts \
  src/engine/react/dndPanePosition.test.ts \
  src/session-canvas/model/layoutPlanning.test.ts \
  src/session-canvas/model/paneAffordances.test.ts \
  src/session-canvas/model/canvasStore.test.ts \
  src/session-canvas/lab/canvasLabLayout.test.ts \
  src/session-canvas/lab/canvasLabStore.test.ts \
  src/session-canvas/persistence/canvasPanePersistence.test.ts \
  src/session-canvas/dnd/canvasDrop.test.ts \
  src/session-canvas/dnd/dndSpace.test.ts \
  src/session-canvas/dnd/paneDndCallbacks.test.ts \
  src/session-canvas/dnd/dragCursor.test.ts \
  src/session-canvas/dnd/useCanvasDropTargets.test.tsx
# 14 files passed, 126 tests passed, exit 0

pnpm exec playwright test www/tests/e2e/canvas-lab-drag.spec.ts --project=chromium
# 6 passed, exit 0

pnpm lint
# exit 0, two intentional noImportantStyles warnings for cursor override CSS

pnpm typecheck
# tsc -b --noEmit, exit 0

pnpm build
# tsc -b && vite build, exit 0

git status --short
# no output
```

The Playwright run emitted Vite proxy warnings for `/api/capabilities` with `ECONNREFUSED`, but all 6 Chromium tests passed. This warning was not relevant to the dnd-kit delta.

## Dependencies

1. `@dnd-kit/core@6.3.1` and `@dnd-kit/sortable@10.0.0` were current for their package lines when checked on 2026-06-12.
2. Current upstream `rectSortingStrategy` computes deltas from `newRect - oldRect`, matching the sibling world pixel shift model.
3. Current upstream default measurement uses transform agnostic client rects, which explains why planner world rect measurement is safer under the canvas camera scale.
4. GitHub issue `clauderic/dnd-kit#2041` remains the design reference for newer scale regression behavior.
5. GitHub issue `clauderic/dnd-kit#1582` remains the design reference for active modifier limitations.

## Relevance to Helioy

The final dnd-kit implementation gives Helioy a reusable pattern for integrating third party drag systems with a scaled world canvas: own measurement, keep transform conversion in one seam, and separate collision membership from reorder membership. The final hardening adds a second useful pattern: delivery mode should remove reorder targets rather than layering another state machine on top.

## Open Questions

1. The cursor CSS intentionally uses `!important` to win over nested cursor rules during drag. Biome reports `noImportantStyles` warnings but exits `0`; keep this documented if the lint policy later becomes stricter.
2. Future cleanup can remove stale design language around nonexistent `paneIdsOverride`, but it does not affect the signed implementation.
