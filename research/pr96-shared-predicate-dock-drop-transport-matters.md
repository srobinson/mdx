---
title: Transport Matters PR 96 shared predicate dock drop review
type: research
tags: [transport-matters, pr-96, review, session-canvas, dnd]
summary: PR #96 at 842e56b was reviewed clean for shared locator predicate consumption and drag/drop regression risk.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Executive Summary

Reviewed `/tmp/tm-pr96-842e56b-1H3KDk` at `842e56be4cf1e3efe7671354255a63415db711b8` against base `cf51be2322919e813e7efe93c2241f17642b12a8`. No real issues were found in the shared locator predicate work or in the pane drag, dock drag, external file, and URL drop paths.

## Project Metadata

- Language: TypeScript and React frontend under `www/`
- Test runner: Vitest and Playwright
- Package manager: pnpm
- fmm status: target checkout has no `.fmm.db`; `fmm validate` failed, so the review used targeted git diff, grep, and line inspections after the fmm attempt.

## Detailed Findings

### Shared locator predicate

- The single delivery predicate is `locatorForPaneRef()` in `www/src/session-canvas/dnd/canvasDrop.ts:16`.
- `deliveryTargetAt()` consumes it directly before terminal targeting in `www/src/session-canvas/dnd/paneDndCallbacks.ts:44`.
- The pane drag release path consumes the same predicate before paste in `www/src/session-canvas/dnd/paneDndCallbacks.ts:96`.
- The dock dragover resolver consumes it through the protected-mode holder in `www/src/session-canvas/dnd/useCanvasDropTargets.ts:59`.
- `handleDockDrop()` consumes it before choosing paste versus restore in `www/src/session-canvas/dnd/canvasDrop.ts:139`.
- Grep found no surviving `locatorForRef` helper. Remaining `source === "path"` mappings in this area are `locatorForPaneRef()`, `refForLocator()` for external drop spawning/docking, registry ID/title derivation, resource rendering, and tests, not a second delivery predicate.

### Regression coverage and behavior

- Dock branch dispatch is isolated by `PANE_REF_MIME` in `www/src/session-canvas/dnd/useCanvasDropTargets.ts:53` and `:106`; external drops fall through to `handleCanvasDrop()` at `:122`.
- External files still resolve through `classifyDrop()` at `www/src/session-canvas/dnd/canvasDrop.ts:43` and unresolved files still show `DROP_HINT_MESSAGE` at `:95`.
- URL drags still parse `text/uri-list` at `www/src/session-canvas/dnd/canvasDrop.ts:55`.
- Dnd-kit pane drag still routes delivery suppression through `deliveryTargetAt()` from `CanvasPaneDnd` at `www/src/session-canvas/dnd/CanvasPaneDnd.tsx:62`, and reorder collision shares the extracted `closestPaneAtWorldPoint()` at `www/src/session-canvas/dnd/dndSpace.ts:72`.
- Dock restore uses the same closest-pane targeting core in `www/src/session-canvas/dnd/canvasDrop.ts:153` and calls `restorePaneAtIndex()` at `:160`.

## Verification

- `git diff --check cf51be2..842e56be4cf1e3efe7671354255a63415db711b8`: passed.
- `cd www && pnpm typecheck`: passed.
- `cd www && pnpm test -- --run ...`: ran the full Vitest suite, 118 files and 815 tests passed.
- `cd www && pnpm exec playwright test tests/e2e/canvas-lab-dock.spec.ts --project=chromium --reporter=line --output=/tmp/tm-pr96-pw-output`: 3 tests passed.
- `git status --short` in the target checkout stayed clean after verification.

## Open Questions

None for the requested scope.
