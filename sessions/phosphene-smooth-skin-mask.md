---
title: Phosphene smooth skin mask implementation
type: sessions
tags: [frontend, phosphene, react-three-fiber, gap-fill, verification]
summary: Implemented smooth skin gap filling for hidden eye and teeth openings with verified screenshots and Vite Plus gates.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented a `smooth skin` visibility toggle for phosphene. When eyes and teeth are hidden, the head sampling pass now fills the matching feature gaps into a continuous dotted mask instead of leaving hollow sockets and mouth openings.

## Architecture Decisions

- Added `smoothSkin` to the runtime visibility model, Leva controls, saved presets, cloning, sanitization, and tween snapping.
- Added `createSmoothSkinGapFill` to derive hidden eye and teeth source regions from the rigged face source.
- Added `fillSurfaceGaps` and `gapFillGrid` helpers. Gap filling runs during point cloud rebuild, marks feature gap cells, diffuses grid depth from fixed rim cells, recomputes normals, and emits static filled points.
- Static filled points bypass depth in the shader so the existing head depth occluder does not erase the bridged membrane. This avoids per frame inpainting while preserving normal point cloud rendering for the rest of the face.
- `DottedFace` now rebuilds the point cloud only when grid or smooth skin relevant visibility changes. It keeps the head occluder fit stable so eye and teeth toggles update feature occluder visibility without rebuilding the head occluder.

## Performance Notes

- Inpainting is sample time only. No diffusion or raycast work was added to the frame loop.
- `vp build` passed. Production JS gzip was 421.35 kB with the existing large chunk warning.
- `vp test` passed 9 files and 21 tests.
- `vp check` passed all 84 files and 50 lint/type targets.

## Deviations from Spec

- The inpainted membrane uses static filled points with depth bypass rather than per frame morph interpolation. This keeps jaw openings closed for the featureless mask and avoids new frame cost.
- The browser plugin `iab` backend was unavailable, so visual verification used the existing Chrome CDP fallback path.

## Open Items

- The filled mask is continuous and removes holes, but the eye and mouth bridge still has subtle lighting structure from the bounded grid fill. Future polish could derive a tighter semantic gap mask from projected feature silhouettes rather than feature bounds.
- Bundle size remains above the 200 kB guideline due to the existing three.js dominated bundle.
