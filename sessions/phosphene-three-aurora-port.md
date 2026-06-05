---
title: Phosphene Three.js Aurora Port
type: sessions
tags: [frontend, phosphene, aurora, three, webgl]
summary: Implemented WebGL rendering for the existing Aurora BandFieldPrimitive while preserving SVG and wallpaper modes.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented the Three.js backend for the Aurora form. `form=aurora` now renders through WebGL by default, while `?renderer=svg&form=aurora` keeps the SVG renderer and `?wallpaper` keeps the no UI SVG wallpaper path.

## Architecture Decisions

- Added `src/Aurora.tsx` as the Three.js component for `auroraForm`.
- Added `ThreeBandResource` to own one retained dynamic `BufferGeometry` mesh for the full band stack.
- Added `bandGeometry.ts` for pure ridge plus baseline vertex layout, indexed strip generation, ramp attributes, and in place position writes.
- Split band renderer glue into `ThreeBandRenderer.ts` and transform sharing into `threeTransform.ts` so `ThreeRenderer.ts` stays below 300 lines.
- Used a small additive `ShaderMaterial` with static band ramp attributes and dynamic uniforms for low, mid, high color plus opacity.
- Reused the same `BandFieldPrimitive` emitted by `auroraBands.ts`; the form output and SVG path were not changed.

## Performance Notes

- The WebGL steady path writes into the owned position buffer in place and sets the position attribute dirty. No per frame geometry, mesh, material, or string allocation is added.
- Static band ramp and gradient attributes are created at resource construction. Per frame work is position writes plus uniform updates.
- `vp check` passed, formatting 73 files and lint/type checking 61 files.
- `vp lint .` passed.
- `vp build` passed with the preexisting large chunk warning. Output `index-DOxQA7lj.js` was 405.47 kB gzip.
- `vp test` passed with 13 files and 55 tests.

## Deviations from Spec

- The band geometry is one mesh for the whole stack rather than one mesh per band. The mesh still encodes each band independently with ridge and baseline vertices, and additive blending makes draw order less sensitive while keeping resource ownership simpler.

## Open Items

- Further visual tuning can happen after side by side screenshots of `?form=aurora` and `?renderer=svg&form=aurora`.
