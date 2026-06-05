---
title: Phosphene T0.2 Review Fixes
type: sessions
tags: [frontend, phosphene, halftone, leva, r3f, performance]
summary: Fixed T0.2 review findings by caching the BVH raycast source, resetting density on preset switches, and gating mic sync.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented the review fix round for phosphene T0.2. The live tuning panel keeps the same user surface, but preset and density changes no longer rebuild the BVH, preset switches avoid stale density flashes, and programmatic mic status sync no longer re-enters the mic enable or disable path.

## Architecture Decisions

- Split immutable raycast preparation from per-grid point generation in `src/grid.ts`.
- Added `createRaycastSource` and `disposeRaycastSource` so the BVH is computed once per immutable source and reused for each preset or density rebuild.
- Updated `src/DottedFace.tsx` to memoize the prepared raycast source per source, then rebuild only point geometry when debounced grid dimensions change.
- Deferred raycast source disposal through a zero-delay cleanup guard so React StrictMode effect replay does not dispose the active BVH, while real unmounts and source changes still dispose it.
- Updated `src/controls.ts` so preset switches synchronously reset debounced density to 1 and render the new preset defaults immediately.
- Gated the Leva mic toggle `onChange` on `context.fromPanel` so programmatic sync cannot re-enter `audio.enable()` or `audio.disable()`.

## Performance Notes

- Density and preset changes now reuse the prepared BVH and only rerun the raycast grid projection.
- Verified `vp check && vp test && vp build` passed.
- Dev verification used headless Playwright with fake microphone permission. Density changes completed, preset A at density 0.70 switched to B with density 1.00 and B defaults within 90 ms, stayed settled after 460 ms, mic reached active, and no page errors were reported.
- `shot-fix-verified.png` captured the corrected live panel and non black halftone face.

## Deviations from Spec

- The in app Browser connector was unavailable, so dev verification used headless Playwright as the fallback.

## Open Items

- The bundle remains over the target because Three, R3F, Drei, and Leva are still in the main chunk.
- `THREE.Clock` continues to warn in dev from the current R3F stack.
