---
title: PR 96 test quality review for Transport Matters dock drag tests
type: research
tags: [transport-matters, code-review, testing, canvas-lab, dock]
summary: Focused read only review of PR 96 test coverage at 842e56b found no blocking test quality issues.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Executive Summary

Reviewed PR #96 test changes in `/tmp/tm-pr96-842e56b-1H3KDk` at commit `842e56be4cf1e3efe7671354255a63415db711b8` against base `cf51be2`. The target checkout has no `.fmm.db`, so fmm structural inspection could not run there without generating an index; review used git diff and bounded line reads in the clean checkout. No real test quality issues were found in the requested scope.

## Project Metadata

- Project: `transport-matters`
- Area: `www/src/session-canvas` and `www/tests/e2e`
- Commit reviewed: `842e56be4cf1e3efe7671354255a63415db711b8`
- Base: `cf51be2`
- Tooling observed: TypeScript, React, Vitest, Testing Library, Playwright
- Target checkout status before and after review: clean

## Detailed Findings

### Unit coverage

- `www/src/session-canvas/dnd/dockDragSource.test.ts:18-43` covers holder publish, clear, MIME constant, payload parsing, and malformed payload handling.
- `www/src/session-canvas/components/PaneDock.test.tsx:59-96` covers row drag start publishing MIME and holder state, drag end cleanup of holder and overlay, and the kill button not initiating a drag.
- `www/src/session-canvas/dnd/useCanvasDropTargets.test.tsx:128-247` covers the dragover resolver for locator dock drags, non locator dock drags, surface targeting, drop effect selection, paste branch dispatch, restore at index branch dispatch, invalid pane ref drop no op, and holder or overlay cleanup on valid drops.
- `www/src/session-canvas/dnd/canvasDrop.test.ts:44-66` covers `locatorForPaneRef` for path, URL, null, undefined, terminal, and non locator resource refs.
- `www/src/session-canvas/dnd/canvasDrop.test.ts:172-230` covers `handleDockDrop` paste behavior, non locator restore over a paste capable target, nearest slot restore on canvas background, and empty canvas append.
- `www/src/session-canvas/model/canvasStore.test.ts:179-211` and `www/src/session-canvas/lab/canvasLabStore.test.ts:247-280` cover both `restorePaneAtIndex` implementations for insertion at a chosen slot and clamping to the tail.
- `www/src/session-canvas/dnd/canvasDrop.test.ts:69-170` plus `www/src/session-canvas/dnd/useCanvasDropTargets.test.tsx:90-118` cover external file drops through bridge resolution, missing bridge hinting, empty path failure, mixed file resolution, URI list parsing, terminal paste with docked resource, and background spawn.

### Playwright E2E slot assertion

`www/tests/e2e/canvas-lab-dock.spec.ts:70-115` is meaningful for the native drag pipeline and the non append contract. The test minimizes `lab-1`, targets the remaining first frame as slot 0 (`lines 74-85`), drags the dock row through Chromium's native HTML5 drag path, then asserts restored `lab-1` is the top left frame relative to all frames (`lines 91-114`). Given the lab starts with four demo panes, an append restore would leave `lab-1` last rather than top left, so the assertion would catch the regression it names. Non zero slot math is covered by the unit tests above.

## Open Questions

None for the requested test quality scope.
