---
title: Dock Drag-Out Implementation Review for Transport Matters
type: research
tags: [transport-matters, captured-canvas, dock-drag-out, pr-review]
summary: PR #96 implementing dock drag-out was reviewed clean at 842e56b against main cf51be2.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Executive Summary

PR #96 (`feat/dock-drag-out`) implements `NOTES/captured-canvas/18-dock-drag-out.md` on top of merged dnd-kit ordered grid work. The implementation was reviewed clean at `842e56be4cf1e3efe7671354255a63415db711b8` against main `cf51be2`; no blocking correctness, reuse, decomposition, regression, or test quality issues were found.

## Project Metadata

- Project: `transport-matters`
- Area: captured canvas frontend, `www/src/session-canvas`
- Review target: PR #96 head `842e56be4cf1e3efe7671354255a63415db711b8`
- Base: main `cf51be2`
- Clean checkout: `/tmp/tm-pr96-842e56b-1H3KDk`
- Tooling: React 19, TypeScript 5.9, Vite 8, Vitest 4, Playwright 1.59, dnd-kit core 6.3.1, dnd-kit sortable 10.0.0, Zustand 5.0.12
- Codebase navigation: fmm indexed structural pass, then bounded reads in the clean checkout

## Architecture

Dock drag-out adds a third drag source to the canvas model. Dock rows become HTML5 drag sources, while the existing canvas surface listeners continue to own dragover, drop, target highlighting, terminal paste delivery, and external file or URL drops.

Main implementation seams:

- `www/src/session-canvas/components/PaneDock.tsx:76-92` writes the pane-ref mime payload `{ paneId, ref }`, sets `effectAllowed = "copyMove"`, and publishes the holder.
- `www/src/session-canvas/components/PaneDock.tsx:97-107` clears holder and overlay on dragend and prevents kill-button presses from lifting the row.
- `www/src/session-canvas/dnd/dockDragSource.ts:12-48` owns the mime constant, in-memory holder, and drop-time payload parsing.
- `www/src/session-canvas/dnd/useCanvasDropTargets.ts:53-73` branches dock drags before external file logic, sets terminal only for locator refs over paste handles, and otherwise marks `surface`.
- `www/src/session-canvas/dnd/useCanvasDropTargets.ts:95-119` clears overlay on dragleave or drop, clears the holder on pane-ref drop, and dispatches to `handleDockDrop` without falling through to the external pipeline.
- `www/src/session-canvas/dnd/canvasDrop.ts:16-21` exports the shared `locatorForPaneRef` predicate.
- `www/src/session-canvas/dnd/canvasDrop.ts:133-161` handles dock drops: paste plus dock bump for locator terminal drops, otherwise restore at target slot.
- `www/src/session-canvas/dnd/dndSpace.ts:72-127` extracts `closestPaneAtWorldPoint` and reuses it in `createWorldSpaceCollision`.
- `www/src/session-canvas/model/canvasStore.ts:189-210` and `www/src/session-canvas/lab/canvasLabStore.ts:217-239` add `restorePaneAtIndex` to production and lab stores.

## Key Patterns

- **One shared target geometry.** `closestPaneAtWorldPoint` is the pointer-inside then closest-center core. `createWorldSpaceCollision` calls it directly at `dndSpace.ts:122`, and dock drop calls it at `canvasDrop.ts:158`.
- **One locator predicate.** `locatorForPaneRef` is consumed by `deliveryTargetAt` in `paneDndCallbacks.ts`, dock dragover in `useCanvasDropTargets.ts`, and dock drop in `canvasDrop.ts`. A grep found no surviving `locatorForRef` duplicate.
- **Holder only for protected mode.** The module-scoped holder supplies dragover with a ref because the HTML5 payload cannot be read until drop. The drop handler reads the authoritative mime payload.
- **Restore at index without tail flash.** Both stores seed, splice with `movePaneOrder`, and plan before committing a single update.
- **Dock paste is a read.** Terminal paste calls `dockPane`, so `parkDockedPane` de-dupes and front-bumps the entry; restore branches remove the dock entry.

## Detailed Findings

### Spec fidelity

Clean. `PaneDock` writes the requested payload shape and blocks kill-button drag starts (`components/PaneDock.tsx:76-92`, `104-107`). Holder lifecycle is centralized in `dockDragSource.ts` and clears on pane-ref drop or source dragend (`useCanvasDropTargets.ts:106-112`, `PaneDock.tsx:97-100`). Dock dragover never reaches `hint`: the pane-ref branch returns before the external file branch and emits `terminal` only when `locatorForPaneRef` plus `resolvePasteHandle` both succeed (`useCanvasDropTargets.ts:53-73`, `85-93`).

`handleDockDrop` matches the spec branches. A locator drop over a paste handle escapes and pastes the locator, then calls `dockPane(refForLocator(locator))` and returns (`canvasDrop.ts:139-146`). All other drops convert the point to world space, call `closestPaneAtWorldPoint`, derive `layout.order.indexOf(hit.id)` with append fallback, and call `restorePaneAtIndex` (`canvasDrop.ts:153-160`).

Both stores implement restore-at-index as a single state update. Production removes the dock entry, restores the pane record, and calls `planSpawnedAffordancePaneLayout(..., index)` (`model/canvasStore.ts:194-210`), while lab removes the dock entry and calls `spawnPaneLayout(state, paneId, ref, index)` (`lab/canvasLabStore.ts:222-239`). The shared planning helpers seed, splice via `movePaneOrder`, and plan once (`model/layoutPlanning.ts:63-67`, `lab/canvasLabLayout.ts:60-68`).

### Documented deviations

Clean. The `effectAllowed = "copyMove"` deviation is sound because dragover advertises `copy` over a terminal and `move` over the surface; a narrower `copy` would veto the restore drop effect (`PaneDock.tsx:88-91`, `useCanvasDropTargets.ts:62-71`).

The dragleave split is sound. `dragleave` clears only the overlay, avoiding holder loss on child-boundary dragleave events; holder clearing happens on actual pane-ref drop and source dragend (`useCanvasDropTargets.ts:95-112`, `PaneDock.tsx:97-100`).

The `locatorForPaneRef` placement in `canvasDrop.ts` is sound. `paneDndCallbacks.ts` already imports `paneIdAtWorldPoint` from `canvasDrop.ts`, while `handleDockDrop` in `canvasDrop.ts` also needs the locator predicate. Moving the predicate into `paneDndCallbacks.ts` would create a direct runtime cycle.

### Reuse and regression risk

Clean. `closestPaneAtWorldPoint` is extracted, not duplicated: it is defined at `dndSpace.ts:72-96`, used by `createWorldSpaceCollision` at `dndSpace.ts:122`, and used by dock restore targeting at `canvasDrop.ts:158`. The stricter `paneIdAtWorldPoint` remains the topmost paste hit test, not a reorder fallback copy.

External drops remain separated. The dock branch dispatches on `PANE_REF_MIME` and returns; non pane-ref drags still route to `handleCanvasDrop` (`useCanvasDropTargets.ts:53-73`, `106-122`). Existing file, unresolved file, URI list, terminal paste, and background spawn paths remain in `classifyDrop` and `handleCanvasDrop` (`canvasDrop.ts:39-114`).

Pane-drag dnd-kit paths remain intact. `CanvasPaneDnd` still builds collision from `createWorldSpaceCollision` and delivery suppression through `deliveryTargetAt`; `paneDndCallbacks` still gates paste by `locatorForPaneRef` and commits reorder only when delivery does not apply.

### Test quality

Clean. Unit coverage spans dock source, holder lifecycle, resolver branches, dock drop branches, both store implementations, shared locator predicate, and external drop behavior:

- `components/PaneDock.test.tsx:59-96`
- `dnd/dockDragSource.test.ts:18-43`
- `dnd/useCanvasDropTargets.test.tsx:128-247`
- `dnd/canvasDrop.test.ts:44-230`
- `model/canvasStore.test.ts:179-211`
- `lab/canvasLabStore.test.ts:247-280`

The e2e slot assertion is meaningful. `www/tests/e2e/canvas-lab-dock.spec.ts:70-115` minimizes `lab-1`, drops its dock row onto the remaining first pane, then asserts restored `lab-1` is first in visual reading order. A tail-append restore would leave `lab-1` last, so the assertion would fail on the regression it targets.

## Verification

Observed locally in `/tmp/tm-pr96-842e56b-1H3KDk`:

```bash
git diff --check cf51be2...HEAD
cd www && pnpm exec vitest run \
  src/session-canvas/components/PaneDock.test.tsx \
  src/session-canvas/dnd/canvasDrop.test.ts \
  src/session-canvas/dnd/dndSpace.test.ts \
  src/session-canvas/dnd/dockDragSource.test.ts \
  src/session-canvas/dnd/paneDndCallbacks.test.ts \
  src/session-canvas/dnd/useCanvasDropTargets.test.tsx \
  src/session-canvas/model/canvasStore.test.ts \
  src/session-canvas/lab/canvasLabStore.test.ts \
  src/session-canvas/lab/canvasLabLayout.test.ts \
  src/session-canvas/persistence/canvasPanePersistence.test.ts
pnpm --dir www exec playwright test tests/e2e/canvas-lab-dock.spec.ts --project=chromium
pnpm --dir www exec playwright test tests/e2e/canvas-lab-drag.spec.ts --project=chromium
cd www && pnpm typecheck
```

Results:

- `git diff --check`: passed
- Focused Vitest: 10 files, 137 tests passed
- Chromium `canvas-lab-dock`: 3 tests passed
- Chromium `canvas-lab-drag`: 6 tests passed
- `pnpm typecheck`: passed
- Source checkout and temp checkout `git status --short`: clean

Four explorer subagents independently reviewed spec fidelity, deviation justification, predicate sharing and regression risk, and test quality; all returned clean.

## Dependencies

- `@dnd-kit/core` and `@dnd-kit/sortable`: pane-drag reorder and collision substrate.
- Zustand: shared drop target store.
- React DOM HTML5 drag events: dock row drag source and surface dragover/drop.
- Vitest and Playwright: unit and behavioral validation.

## Relevance to Helioy

The implementation preserves the unified drag model across dock rows, external files, and pane lifts. It keeps Transport Matters canvas behavior aligned with Helioy’s DRY and decomposition rules by sharing locator detection, target geometry, and store flows rather than forking parallel pipelines.

## Open Questions

None for PR #96 at `842e56b`. The orchestrator can amend doc 18 to match the three sound as-built deviations.
