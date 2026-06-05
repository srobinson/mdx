---
title: Canvas S3 Expand Composition
type: sessions
tags: [frontend, canvas, layout, expand, grid-overflow]
summary: Implemented S3 expand composition over the registered grid-overflow strategy and completed the DRY fix round.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-11
updated: 2026-06-11
---

## Summary

Implemented S3 for the canvas lab layout path on branch `feat/canvas-s3-expand-composition`, amended commit `4207f598fb206ef8a6a949aec39c5288de0abf09`, PR #87.

The expand path now uses `planExpandLayout`: it splits the viewport into a hero region and a remainder region, places `expandedPaneId` in the hero region, and fills the remainder through the registered `grid-overflow` strategy. The former lab local overflow copy was removed.

The S3 fix round removed duplicated geometry from `canvasLabLayout.test.ts` by exporting and importing the real expand helpers from `expandLayout.ts`.

## Architecture Decisions

- Kept the vocabulary as expand: `planExpandLayout`, `expandedPaneId`, and existing E or UE control behavior.
- Fixed the expand remainder strategy to `grid-overflow` through `EXPAND_REMAINDER_STRATEGY_ID`, using that strategy's defaults rather than the canvas active strategy.
- Preserved one split policy only. No hero placement state or shortcut cycling was introduced.
- Folded expand camera fitting into the transform result through the returned `camera` viewport.
- Kept `planLayout` on one common write path by selecting either the expand transform result or the active strategy result, then applying rects and optional camera fitting once.
- Exported the transform's real helper seam: `splitExpandColumns`, `translateRect`, `translateRects`, `composeExpandFrame`, and `fitExpandFrameCamera`, so tests assert composition without reimplementing production geometry.

## Performance Notes

- `cd www && pnpm build` passed before the DRY fix round.
- Observed production assets remained below the 200 KB gzip target in that build output. Largest gzip sizes included `terminal-pane` at 87.75 KB, `ExchangeDetail` at 87.03 KB, `PaneChrome` at 58.52 KB, and `index` at 57.54 KB.

## Deviations from Spec

None. `planExpandedLayout`, `planRightColumn`, `fitExpandFrameToWidth`, and the old expand grid constants were removed from the lab layout path. A live `rg` check for those retired names returned no matches after the fix round.

## Open Items

None for S3. Hero placement cycling remains deferred by decision #3 in the spec.

## Verification

- `cd www && pnpm exec vitest run src/session-canvas/lab/canvasLabLayout.test.ts src/session-canvas/lab/canvasLabStore.test.ts src/engine/layout/gridOverflow.test.ts` passed after the fix round, 3 files and 39 tests.
- `cd www && just check` passed after the fix round.
- `cd www && just test` passed after the fix round, 100 files and 662 tests.
- `git diff --check` passed after the fix round.
- `rg` for duplicated test helper names returned no matches.
- `rg` for retired expand and grid symbols returned no matches.
- PR #87 remains open at `https://github.com/littleorgans/transport-matters/pull/87`, head `4207f598fb206ef8a6a949aec39c5288de0abf09`.
