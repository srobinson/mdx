---
title: PR #96 Dock Drag-Out Spec Fidelity Review
type: research
tags: [transport-matters, captured-canvas, dock-drag-out, pr-review]
summary: PR #96 at 842e56b matches the requested dock drag-out spec areas with no real fidelity issues found.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Executive Summary

Reviewed PR #96 in `/tmp/tm-pr96-842e56b-1H3KDk` at `842e56be4cf1e3efe7671354255a63415db711b8` against base `cf51be2`, focused only on `NOTES/captured-canvas/18-dock-drag-out.md` fidelity. No real issues were found in the requested areas.

## Project Metadata

- Project: `transport-matters`
- Review target: clean checkout `/tmp/tm-pr96-842e56b-1H3KDk`
- Base: `cf51be2322919e813e7efe93c2241f17642b12a8`
- Head: `842e56be4cf1e3efe7671354255a63415db711b8`
- fmm: no `.fmm.db` in the clean checkout, so structural fmm orientation used the available indexed checkout and exact verification used shell reads in `/tmp/tm-pr96-842e56b-1H3KDk`.

## Architecture

The implementation adds dock drag-out through the existing session-canvas surfaces. `PaneDock` becomes the HTML5 drag source, `dockDragSource.ts` owns the custom mime and same-window holder, `useCanvasDropTargets` dispatches pane-ref drags before the external drop path, `canvasDrop.ts` owns `handleDockDrop`, and both production and lab stores expose `restorePaneAtIndex` while keeping their own planning seams.

## Detailed Findings

### Clean findings

- Drag source payload and kill-button opt-out match the spec: `PaneDock` serializes `{ paneId, ref }` to `application/x-tm-pane-ref`, publishes the holder, sets copy or move compatible `effectAllowed`, and prevents the kill button from initiating a row drag. Evidence: `www/src/session-canvas/components/PaneDock.tsx:76-92`, `www/src/session-canvas/components/PaneDock.tsx:97-107`, `www/src/session-canvas/components/PaneDock.tsx:129-153`.
- Holder lifecycle is centralized and bounded: `dockDragSource.ts` owns the mime, set, read, clear, and drop-time parse helpers; the source clears on drag end and the surface drop clears before handling the parsed payload. Evidence: `www/src/session-canvas/dnd/dockDragSource.ts:12-31`, `www/src/session-canvas/dnd/dockDragSource.ts:37-44`, `www/src/session-canvas/components/PaneDock.tsx:97-100`, `www/src/session-canvas/dnd/useCanvasDropTargets.ts:98-119`.
- Dragover branch fidelity holds: pane-ref drags branch on `types.includes(PANE_REF_MIME)`, read the holder for locator-bearing-ness, set terminal only when locator plus paste handle are present, otherwise set surface, and never enter the file-drop hint branch. Evidence: `www/src/session-canvas/dnd/useCanvasDropTargets.ts:53-73`, `www/src/session-canvas/dnd/useCanvasDropTargets.ts:85-93`, `www/src/session-canvas/dnd/useCanvasDropTargets.ts:145-153`.
- `handleDockDrop` implements both branches: locator over terminal pastes escaped text and calls `dockPane`, while non-paste drops compute the shared closest-pane target and call `restorePaneAtIndex`. Evidence: `www/src/session-canvas/dnd/canvasDrop.ts:139-160`, plus the shared locator predicate at `www/src/session-canvas/dnd/canvasDrop.ts:16-20`.
- Both stores compose restore-at-index inside one state update and one planning pass: production delegates tail restore to `restorePaneAtIndex`, removes the docked entry, re-seeds the pane, and passes the index through `planSpawnedAffordancePaneLayout`; lab does the same with `spawnPaneLayout`. Evidence: `www/src/session-canvas/model/canvasStore.ts:189-210`, `www/src/session-canvas/model/layoutPlanning.ts:63-67`, `www/src/session-canvas/lab/canvasLabStore.ts:217-239`, `www/src/session-canvas/lab/canvasLabLayout.ts:60-68`.
- Dock retention and paste bump use the existing dock substrate: `handleDockDrop` calls `dockPane` only for paste, and restore branches remove the docked entry. `parkDockedPane` de-dupes and front-bumps. Evidence: `www/src/session-canvas/dnd/canvasDrop.ts:143-160`, `www/src/session-canvas/model/paneAffordances.ts:311-318`, `www/src/session-canvas/model/paneAffordances.ts:366-372`.

## Verification

- Confirmed checkout was clean before and after review: `git status --short --untracked-files=all` produced no output.
- Ran targeted frontend tests from `www`: `pnpm exec vitest run src/session-canvas/components/PaneDock.test.tsx src/session-canvas/dnd/dockDragSource.test.ts src/session-canvas/dnd/useCanvasDropTargets.test.tsx src/session-canvas/dnd/canvasDrop.test.ts src/session-canvas/model/canvasStore.test.ts src/session-canvas/lab/canvasLabStore.test.ts`.
- Result: 6 test files passed, 89 tests passed.

## Open Questions

None for the requested spec fidelity scope.
