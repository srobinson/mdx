---
title: Canvas S1 View State Persistence
type: sessions
tags: [frontend, transport-matters, session-canvas, canvas-lab, persistence]
summary: Persisted core canvas view state on top of the S0 pane persistence seam.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-11
updated: 2026-06-11
---

## Summary

Implemented S1 from `NOTES/lab-migrate-expand-grid-overflow.md` on branch `feat/canvas-s1-view-state`. PR #84 is open against `main` and now points at amended commit `444ae95c93911878f25452532af034cf4648cb36`.

The core persistence seam now stores canvas view state alongside pane records: `activeStrategyId`, sanitized `params`, `fitToContent`, and a guarded `expandedPaneId`. The lab adapter adds only its scaffolding counters on top.

## Architecture Decisions

- Added `PersistedCanvasView` and `PersistedCanvasState` in `www/src/session-canvas/persistence/canvasPanePersistence.ts`.
- Added `rebuildPersistedCanvasState()` to hydrate panes and view controls without re-planning persisted pane rects.
- Kept `rebuildPersistedPanes()` as the pane-only primitive for S0 behavior and narrower tests.
- Moved `seedParams()` and `sanitizeParam()` into `www/src/engine/layout/params.ts`, exported via `www/src/engine/layout/index.ts`.
- Updated `canvasLabStore.persistence.ts` to persist the core view group and bumped the lab storage version to `2`, with no migration path per decision #6.
- Restored `expandedPaneId` only when the rebuilt open set contains the pane and more than one pane is open.
- Fix round: the `expandedPaneId` guard now derives the open set from rebuilt nodes with `lifecycle === "open"`, matching `collectOpenPaneRects()` semantics.
- Fix round: the reload expand test now calls `unexpand()` after reload and asserts `expandedPaneId` clears plus pane rects re-plan back to the active strategy.

## Performance Notes

No runtime performance optimization was targeted. Reload hydration remains linear in the persisted pane count and does not call the layout planner.

Verification:

- Focused fix test: `cd www && pnpm exec vitest run src/session-canvas/persistence/canvasPanePersistence.test.ts src/session-canvas/lab/canvasLabStore.persistence.test.ts` passed with 2 test files and 16 tests.
- Gate: `cd www && just check` passed after format, lint fix, and typecheck.
- Gate: `cd www && just test` passed with 98 test files and 653 tests.
- Branch force-pushed with `--force-with-lease`; PR #84 head verified as `444ae95c93911878f25452532af034cf4648cb36`.

## Deviations from Spec

No intentional deviations. The implementation follows S1 scope only and leaves S2/S3 untouched.

## Open Items

- S2 still needs the `grid-overflow` strategy.
- S3 still needs expand as a composition transform rather than the current expand-specific branch.
