---
title: Phosphene smooth mask mouth fix
type: sessions
tags: [frontend, phosphene, smooth-skin, gap-fill, morph]
summary: Implemented dynamic rim anchored gap fill so smooth mask mouth motion stays continuous under jaw morphs.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented the phosphene smooth mask mouth fix. Smooth skin gap fill no longer freezes inpainted mouth cells at build time. Gap points now reblend from current deformed rim anchors each morph update, so jaw motion stretches the membrane instead of reopening the mouth cavity.

## Architecture Decisions

- Added `GapFillBinding` metadata on `SurfaceBinding` for dynamic fill points.
- Gap fill records four rim anchors per inpainted point with interpolation weights derived from the build time smooth fill depth.
- Gap and rim normals use neighbor point bindings and are recomputed after all regular morph and rigid bindings update.
- Split morph attribute writes into `morphPointAttributes.ts` to keep existing files under the 300 line project limit.
- Shared fixed and output cell state through `gapFillCellState.ts` to avoid duplicating gap cell predicates.

## Performance Notes

- Per frame work is limited to gap fill points and normal region points.
- The runtime path reuses existing typed arrays and does not allocate inside the morph update loop.
- Verification reported about 120 RAF frames per second in headless Chromium for smooth mask mode with `?audio=0.7` and no console errors.

## Deviations from Spec

No spec deviation. The requested dynamic bridge was implemented for smooth skin gap fill only. Non smooth behavior remains unchanged.

## Open Items

- The production build still reports the pre existing large chunk warning.
- The Browser plugin `iab` backend was unavailable, so screenshot verification used a local Chromium CDP fallback.
