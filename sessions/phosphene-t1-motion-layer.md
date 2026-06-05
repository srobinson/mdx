---
title: Phosphene T1 Motion Layer
type: sessions
tags: [frontend, phosphene, react-three-fiber, threejs, motion, blendshapes]
summary: Implemented and review-fixed a morph-bound ARKit face point cloud with audio-driven jaw motion and speaking brightness.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented the phosphene T1 motion layer. The static LeePerrySmith head was replaced with a stripped three.js Facecap GLB at `public/face.glb`. The renderer now builds the structured dot grid on the neutral mesh, stores each dot's triangle indices and barycentric weights, and updates point positions from active ARKit morph deltas.

A follow-up review round fixed all four minor findings: used morph deltas are filtered to the driven target set, jaw gain is no longer double-applied to mouth energy, morph point updates are skipped when weights are unchanged, and `eyeOpen=1` now drives a visible `eyeWide` morph.

## Architecture Decisions

- Added `src/gridSampling.ts` as the shared structured raycast sampler. It returns point geometry plus barycentric bindings for morph correspondence.
- Added `src/faceRig.ts` to locate the ARKit morph mesh, convert quantized GLTF attributes to Float32 before world transforms, and log morph target names.
- Added `src/morphTargets.ts` as the single source for driven morph names. `faceRig` now stores only those 8 morph deltas.
- Added `src/morphPointCloud.ts` to apply active morph deltas, cache neutral point positions and smooth normals, skip unchanged weight signatures, and restore neutral attributes when no morphs are active.
- Added `src/faceMotion.ts` for idle blink, open-eye baseline, jaw gain, and mouth weights. Jaw gain now applies once to jaw motion, not twice through mouth energy.
- Added `src/faceMaterial.ts` to keep shader code out of `DottedFace.tsx` and remove speech displacement bloom. Audio drives brightness plus a small point-size lift.
- Baked Stuart's locked preset C defaults in `src/look.ts`: grid density 0.55, base dot size 0.12, size by light 0.40, black cutoff 0.00, light flatness 0.45, posterize 5, idle yaw 0.20, audio gain 0.56.
- Kept the Leva panel and added controls for speaking brightness, brightness floor, eye open, and jaw gain.

## Performance Notes

Verification completed after the fix round:

- `vp check`: pass.
- `vp test`: pass, 3 tests.
- `vp build`: pass.
- Files remain under 300 lines. Largest source file is `src/audio.ts` at 297 lines.
- `vp dev` verification completed with screenshots for idle, speaking, jaw gain 1 vs 3, and eye open 0 vs 1. Browser console had no errors.
- `shot-t1-speak.png` uses `?audio=0.6`, shows an open jaw, and has higher mean luminance than idle.
- Jaw screenshots differ when `jaw gain` is changed from 1 to 3, confirming the slider affects jaw motion predictably.
- Eye screenshots differ when `eye open` is changed from 0 to 1, confirming `eyeWide` is now visible.

## Deviations from Spec

- No matching phosphene design file existed in `~/.mdx/design/`; implementation followed the bus directive and cm records instead.
- The downloaded Facecap GLB referenced KTX2 textures and meshopt compression. The texture references were stripped from `public/face.glb` because the renderer only needs geometry and morph targets, while `useGLTF` still loads meshopt-compressed geometry.
- `public/head.glb` was removed because the rigged Facecap asset supersedes the static head.
- `vp check --fix` formatted `review-phosphene-t1.md`, which was already in the workspace and failed the formatter before this fix round.

## Open Items

- Bundle remains above the 200 KB gzip target because Three, React Three Fiber, Drei, and Leva dominate the single chunk. This predates T1 and remains a follow-up optimization.
- The current CPU morph path is intentionally pragmatic. If density increases toward 50k plus points, consider moving deformation to a morph texture or worker-backed path.
