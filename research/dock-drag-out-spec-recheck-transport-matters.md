---
title: Dock Drag-Out Spec Recheck for Transport Matters
type: research
tags: [transport-matters, captured-canvas, dock-drag-out, spec-review]
summary: Recheck of 18-dock-drag-out.md against merged main cf51be2 reached final signoff after stale citation fixes.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Executive Summary

`NOTES/captured-canvas/18-dock-drag-out.md` was rechecked after the dnd-kit ordered-gridFit work landed on main as `cf51be2`. The initial recheck found two stale citations; after those were fixed, the exact spots were re-read live and final signoff was sent.

## Project Metadata

- Project: `transport-matters`
- Area: React canvas UI under `www/src/session-canvas`
- Verification target: merged main commit `cf51be2`
- Source working tree at review time: `ff76086`, clean
- Clean verification checkout: `/tmp/tm-main-cf51be2-cEXur7`
- Relevant frontend tooling from `www/package.json`: React 19, TypeScript 5.9, Vite 8, Vitest 4, Playwright 1.59, dnd-kit core 6.3.1, dnd-kit sortable 10.0.0, Zustand 5.0.12

## Architecture

The dock drag-out spec extends the captured canvas drag model. It is meant to join the existing HTML5 drop path in `www/src/session-canvas/dnd/useCanvasDropTargets.ts`, the drop target store in `www/src/session-canvas/dnd/dropTargetStore.ts`, and the dnd-kit world-space collision path in `www/src/session-canvas/dnd/dndSpace.ts`.

Main `cf51be2` exposes the required substrate:

- `deliveryTargetAt` exists in `www/src/session-canvas/dnd/paneDndCallbacks.ts:47-58` and uses private `locatorForRef` at `paneDndCallbacks.ts:33-40`.
- `createWorldSpaceCollision` exists in `www/src/session-canvas/dnd/dndSpace.ts:68-104` with pointer-within plus closest-center targeting.
- `dropTargetStore` exposes only `surface`, `hint`, and `terminal` target kinds in `www/src/session-canvas/dnd/dropTargetStore.ts:8-11`.
- `useCanvasDropTargets` writes drop targets during `dragover` in `www/src/session-canvas/dnd/useCanvasDropTargets.ts:37-60` and clears on leave/drop at lines 62-67.
- `runDockPaneFlow` exists in `www/src/session-canvas/model/paneAffordances.ts:358-365`.
- `parkDockedPane` de-dupes by prepending the new entry over `removeDockedPane(docked, paneId)` in `www/src/session-canvas/model/paneAffordances.ts:303-311`.
- `removeDockedPane` exists in `www/src/session-canvas/model/paneAffordances.ts:313-315`.
- Production `dockPane` routes through `runDockPaneFlow` in `www/src/session-canvas/model/canvasStore.ts:216-230`.
- Lab `dockPane` routes through `runDockPaneFlow` in `www/src/session-canvas/lab/canvasLabStore.ts:172-177`.
- Production restore removes the dock entry and replans through `planSpawnedAffordancePaneLayout` in `www/src/session-canvas/model/canvasStore.ts:187-200`.
- Lab restore removes the dock entry and re-seeds through `spawnPaneLayout` in `www/src/session-canvas/lab/canvasLabStore.ts:217-232`.
- Persistence rebuild keeps docked entries and order in `www/src/session-canvas/persistence/canvasPanePersistence.ts:90-123`, `145-207`, and `278-323`.

## Key Patterns

- The current canvas drag model uses one shared module-scoped drop target store for HTML5 drags and pane-lift move ticks.
- Terminal delivery is guarded by a locator predicate and a registered paste handle, not just by being over a terminal pane.
- Dock parking is deliberately side-effect-light for unopened panes: `runDockPaneFlow` parks without mutating layout, and `parkDockedPane` handles de-dupe and recency.
- Ordered grid semantics are target-slot based: dnd-kit collision first checks pointer containment, then falls back to closest center.

## Detailed Findings

### Passed checks

The requested main-code symbol sweep passed in `/tmp/tm-main-cf51be2-cEXur7` at `cf51be2`. The recheck script confirmed `deliveryTargetAt`, private `locatorForRef`, `createWorldSpaceCollision`, `runDockPaneFlow`, both-store `dockPane`, `parkDockedPane` de-dupe, `removeDockedPane`, both restore re-seed paths, drop target kinds `surface`/`hint`/`terminal`, and dragover writes in `useCanvasDropTargets`.

The semantic description for dock drops mostly tracks the post dnd-kit model. `NOTES/captured-canvas/18-dock-drag-out.md:167-177` specifies world conversion, a shared `closestPaneAtWorldPoint(orderedRects, point)` extraction from `createWorldSpaceCollision`, `layout.order.indexOf(targetPaneId)`, and target-slot semantics rather than between-slot insertion. `NOTES/captured-canvas/18-dock-drag-out.md:201-212` specifies the terminal paste branch calling `dockPane(ref)` so `parkDockedPane` de-dupes and bumps recency instead of performing a no-op.

The testing section is coherent with the amended design. `NOTES/captured-canvas/18-dock-drag-out.md:257-281` covers drag source behavior, dragover resolver behavior, dock drop handling, both-store `restorePaneAtIndex`, shared `locatorForPaneRef`, `just check && just test`, and a Playwright dock drag-out scenario.

### Blocking issues sent on the bus

1. `NOTES/captured-canvas/18-dock-drag-out.md:7-8` still says `ff76086` is the baseline for all code citations and frames PR #95 as future work. The recheck target was merged main `cf51be2`, so that status text is stale.
2. `NOTES/captured-canvas/18-dock-drag-out.md:216-217` still cites the deleted `paneReorder.ts onMoveEnd` seam and `locatorFor`. Main `cf51be2` has no `paneReorder` reference under `www/src/session-canvas`, and the live pane release path is `paneDndCallbacks.ts` `deliveryTargetAt` plus private `locatorForRef`.

Bus reply sent to `transport-matters:general:1:4.1` on topic `tm-dock-dragout-recheck` with conditional signoff withheld until those stale citations were updated.

## Dependencies

- `@dnd-kit/core` and `@dnd-kit/sortable`: pane lift, reorder, collision, sortable strategy.
- Zustand: `dropTargetStore` module-scoped UI state.
- React/Vite/Vitest/Playwright: frontend runtime and validation stack.

## Relevance to Helioy

This review protects the captured canvas spec chain from drifting across the dnd-kit pivot. The important architectural lesson is that dock drag-out should reuse the shared target geometry and delivery substrate, not revive deleted pre dnd-kit seams.

### Final signoff pass

After the orchestrator updated the document, the two corrected spots were re-read live. `NOTES/captured-canvas/18-dock-drag-out.md:6-7` now says PR #95 is merged on main `cf51be2` and that the spec is implementable now. `NOTES/captured-canvas/18-dock-drag-out.md:212-217` now cites `dnd/paneDndCallbacks.ts` release handling gated by `deliveryTargetAt` and the shared locator predicate. A focused grep for the deleted seams and stale phrases returned no matches, and `git status --short` was clean. Final bus reply: `signoff: I sign off on 18-dock-drag-out.md as currently filed`.

## Open Questions

None.
