---
title: Canvas S0 Persistence Core
type: sessions
tags: [frontend, session-canvas, canvas-lab, persistence]
summary: Extracted generic canvas pane persistence from the lab into a core session-canvas module and amended the reload restore coverage.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-11
updated: 2026-06-11
---

## Summary

Implemented S0 from `NOTES/lab-migrate-expand-grid-overflow.md`. Generic pane persistence now lives in `www/src/session-canvas/persistence/canvasPanePersistence.ts`; the lab persistence file is a thin adapter for its storage key, version, and lab scaffolding counters. Branch `feat/canvas-s0-persistence-core` was force-pushed at `38a61b79eff2a098ef404940242650497176d3aa`, and PR #83 remains open to `main`.

## Architecture Decisions

- Added `PersistedCanvasPanes`, `seedPaneFromRecord`, `collectOpenPaneRects`, and `rebuildPersistedPanes` as primitives, not a generic factory.
- Kept `createFrontendPersistStorage` and `FRONTEND_STORAGE_KEYS.canvasLabStore` in the lab adapter because storage backend wiring remains a separate seam.
- Repointed `canvasLabLayout.ts` to the core `seedPaneFromRecord` so spawn and reload continue to share one creation primitive.
- Removed the lab owned `PersistedLabState`, `collectOpenPaneRects`, `seedPaneFromRecord`, and `mergeLabState` path. The lab adapter now folds only `paneCounters` and `nextPaneIndex` back onto the rebuilt core pane set.
- Moved generic persistence behavior into `canvasPanePersistence.test.ts`; left lab labels, per-prefix counters, captured reattach, minimized captured panes, no lab key hydration, and post-reload dock restore coverage in the lab adapter test.

## Performance Notes

No runtime performance optimization was targeted. The change keeps each touched and new file below the 700 line threshold.

## Deviations from Spec

None. `capturedRunStore` was untouched, no migration path was added, and the persisted view state remains out of scope for S0.

## Open Items

- S1 should add core persisted view state for strategy, params, fit preference, and `expandedPaneId` on top of this seam.
- Later product canvases can adopt the same primitives with their own per-surface storage adapter.

## Verification

- `cd www && just check` passed.
- `cd www && just test` passed with 98 files and 648 tests.
- Fix round added the lab adapter test `restores a docked pane after a reload`.
