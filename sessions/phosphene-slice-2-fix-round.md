---
title: Phosphene Slice 2 Fix Round
type: sessions
tags: [frontend, phosphene, slice-2, react-three-fiber, presets, transitions]
summary: Fixed preset transition snapping, per-frame grid rebuilds, and saved preset persistence gaps.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented the Slice 2 review fix round for phosphene. Preset selection now resolves transition targets the same way the steady state controls resolve them, so density presets such as C tween instead of snapping. Grid geometry is keyed by primitive dimensions, which prevents point-cloud rebuilds on every transition frame.

## Architecture Decisions

- Added `lookFromPreset` as the shared preset to runtime look resolver.
- Initialized and targeted the tween driver with resolved runtime looks rather than raw preset objects.
- Changed the look tween driver to mutate preallocated current, source, and target buffers while exposing a version number for `useSyncExternalStore`.
- Kept grid object identity stable during transition frames and updated grid dimensions only when the target resolution lands.
- Updated face material color writes to reuse RGB scratch storage.
- Added saved preset caps, quota safe persistence, long name trimming, and restore support for `edgeFloor`, `sideFadeStart`, and `sideFadeEnd`.

## Performance Notes

- `vp test`: 8 files, 17 tests passed.
- `vp build`: passed. JS output gzip was 418.53 kB, still dominated by three.js.
- `vp check`: passed. 77 files formatted, no lint or type errors in 44 files.
- Headless Chrome CDP on `vp dev` verified A to B, B to C, and A to C transitions. 100 ms screenshots differed from final settled screenshots, confirming no snap. Frame probes had p95 around 10 ms and no repeated greater than 50 ms rebuild jank.

## Deviations from Spec

None. Existing bundle size remains above the target because of the three.js stack, matching the prior tracked backlog.

## Open Items

- Bundle size remains around 418 kB gzip.
- Existing backlog items for idle full-buffer re-upload, fixed occluder recess constants, and front-only sampling remain open.
