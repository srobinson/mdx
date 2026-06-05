---
title: Ordered gridFit Plan Citation Review for Transport Matters
type: research
tags: [transport-matters, captured-canvas, peer-review, gridfit]
summary: Verified ordered gridFit plan citations against main at 46982ad, with one high severity body-drag contract mismatch.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Executive Summary

`NOTES/captured-canvas/17-ordered-gridfit-plan.md` cites real main-line canvas, engine, drag, and terminal-drop seams, and its Task 9 controller wiring mostly matches current contracts on `main` at `46982ad2d0a3f2cab254dbae25d8f33fb98abf72`. The main defect found is that the body-drag plan says resource image pixels will lift the pane, but the current image viewer wraps the image in a button while the proposed drag helper excludes button descendants.

## Project Metadata

- Project: `transport-matters`
- Area: `www` React canvas UI, Zustand stores, `@use-gesture`, Framer Motion, Vitest
- Baseline: `main` resolves to `46982ad2d0a3f2cab254dbae25d8f33fb98abf72`
- Evidence sources: fmm outlines and `git show main:<path>` / `git cat-file -e main:<path>` only for code checks

## Architecture

The plan builds on these existing seams:

- Engine layout primitives in `www/src/engine/types.ts` and `www/src/engine/reducers/layoutState.ts`
- Layout planning in `www/src/session-canvas/model/layoutPlanning.ts`
- Surface adapters in `CanvasSurface.tsx` and `CanvasLabRoute.tsx`
- Drag frame and motion plumbing in `PaneFrame.tsx` and `LayoutCanvas.tsx`
- Terminal paste delivery in `canvasDrop.ts`, `useCanvasDropTargets.ts`, and `pasteRegistry.ts`
- Viewer metadata in `paneRecords.ts` and `registry.tsx`

## Detailed Findings

### Verified citations

- Plan file itself is not tracked on `main`: `git show main:NOTES/captured-canvas/17-ordered-gridfit-plan.md` fails because the file exists only on disk. Code checks used `main`.
- Files cited as existing modifications exist: `types.ts`, `layoutState.ts`, `layoutState.test.ts`, `layoutPlanning.ts`, `canvasPersistOptions.ts`, `canvasPanePersistence.ts`, `canvasStore.ts`, `canvasLabStore.ts`, `canvasLabTypes.ts`, `PaneFrame.tsx`, `LayoutCanvas.tsx`, `paneRecords.ts`, `registry.tsx`, `ImageResourceViewer.tsx`, `CanvasSurface.tsx`, `CanvasLabRoute.tsx`, `useCanvasDropTargets.ts`, `canvasDrop.ts`, and `pasteRegistry.ts`. Evidence: `git cat-file -e main:<path>`.
- Files cited as new are absent on main as expected: `engine/layout/insertionIndex.ts`, `engine/layout/insertionIndex.test.ts`, `session-canvas/dnd/dropTargetStore.ts`, `components/CanvasDropTargetOverlay.tsx`, `session-canvas/dnd/paneReorder.ts`, and `session-canvas/dnd/paneReorder.test.ts`.
- `EngineLayoutState` exists but has only `mode`, `viewport`, `nodes`, and `focusedPaneId`; no `order` yet. Evidence: `git show main:www/src/engine/types.ts` lines 26 to 31.
- `createInitialEngineLayoutState`, `upsertNode`, and `removeNode` exist and currently do not maintain order. Evidence: `layoutState.ts` lines 24 to 30, 42 to 46, 111 to 117.
- `openPaneIds` and `planLayout` exist. `openPaneIds` currently walks `Object.values(layout.nodes)`, and `planLayout` has no `paneIdsOverride` parameter. Evidence: `layoutPlanning.ts` lines 45 to 49 and 74 to 94.
- `LayoutCanvas` already has a `paneMotion?: boolean` prop and threads it to `PaneFrame` as `layoutMotion`. Evidence: `LayoutCanvas.tsx` lines 6 to 23, 60 to 70, 80 to 92, 137 to 145.
- `PaneFrame` already has move drag and `onMoveEnd`; `dragModeForTarget` exists but is private and handle-only. Evidence: `PaneFrame.tsx` lines 80 to 123 and 168 to 172.
- Terminal delivery exists through `deliverPaneDropToTerminal`, `paneIdAtWorldPoint`, `resolvePasteHandle`, and `escapeDropLocator`. Evidence: `canvasDrop.ts` lines 49 to 64 and 107 to 126; `pasteRegistry.ts` lines 13 to 36.
- `CanvasSurface` and `CanvasLabRoute` currently wire `useCanvasDropTargets(...).onMovePaneEnd` directly into `LayoutCanvas`. Evidence: `CanvasSurface.tsx` lines 59 to 64 and 131 to 138; `CanvasLabRoute.tsx` lines 55 to 61 and 235 to 245.
- `ViewerRegistration` exists and has no `bodyDrag` field yet. `titleForRef` exists. Evidence: `paneRecords.ts` lines 197 to 204; `registry.tsx` lines 164 to 166.

### Contract mismatches

1. High, `www/src/session-canvas/viewers/resource/ImageResourceViewer.tsx` plus proposed `PaneFrame.dragModeForTarget`: The plan claims resource panes lift from image pixels, but the current image is inside `<button className="canvas-image__stage">`. The proposed helper excludes `button` ancestors, so dragging the image still returns null. Evidence: `ImageResourceViewer.tsx` lines 88 to 100; plan lines 558 to 584 and 644 to 651.

## Dependencies

Critical dependencies involved: React, Zustand, `@use-gesture/react`, Framer Motion, Vitest, and the existing viewer registry and terminal paste registry.

## Relevance to Helioy

The review supports the captured-canvas ordering slice by validating that the plan mostly reuses existing seams instead of duplicating terminal drop or surface wiring logic.

## Open Questions

- Whether the image viewer should stop using a button stage, or whether `dragModeForTarget` should explicitly allow image drags inside the zoom stage while preserving keyboard zoom accessibility.
