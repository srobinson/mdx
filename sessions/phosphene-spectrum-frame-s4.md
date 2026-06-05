---
title: Phosphene Spectrum Frame Seam S4
type: sessions
tags: [frontend, phosphene, renderer, spectrum]
summary: Moved the spectrum form onto the Frame seam and cleaned the in-slice legacy update path.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Summary

Implemented Slice 4 for phosphene spectrum rendering. The spectrum form now creates and updates one retained `BarFieldPrimitive` with three ordered layers for bars, beams, and reflection. `Spectrum.tsx` still owns the Three instanced meshes and materials for this slice, but reads per bar geometry and layer style data from the frame primitive instead of computing bars inline.

The fix round removed the dead legacy `updateSpectrum` path, moved the remaining smoothing test onto `spectrumForm`, refreshed material styles without re-running audio sampling, and made the spectrum group transform purely imperative.

## Architecture Decisions

- Added `createBarFieldPrimitive`, `createBarLayer`, and `requireBarField` to `src/render/primitive.ts` so bar fields share the same retained primitive plumbing as polylines.
- Added `spectrumForm: FormModule<WaveformLook>` in `src/spectrumBands.ts` with `structuralKeys: ["bars"]`.
- Kept `target` and raw smoothed heights in a `WeakMap<Frame, SpectrumFrameResources>` so per frame updates allocate nothing.
- Stored raw smoothed bar height in `primitive.heights` and stored `heightScale` on `primitive.transform.scale`, preserving the prior matrix calculation path before Three uploads the instance matrix.
- Modeled the three current passes as layers: bars, beams, and reflection. Beam width fraction and beam height multiplier come from layer style and transform data; reflection mirror scale comes from the reflection layer transform.
- Exported `writeSpectrumLayerStyles` as the style only refresh path for material updates.
- Removed declarative rotation and scale props from the spectrum group. The component now applies `frame.container` through an imperative `applyTransform` helper in `useFrame`.

## Performance Notes

- No new per frame allocations were introduced. The update path mutates retained typed arrays, layer objects, material uniforms, and the module level Three `Object3D` dummy.
- The material effect no longer calls `spectrumForm.update`, so control changes do not resample audio outside the render loop.
- Verification gates passed: `vp check`, `vp lint .`, `vp build`, and `vp test`.
- `vp test` reported 4 files and 21 tests passing.

## Deviations from Spec

- This slice did not extract a `ThreeRenderer`; that is explicitly deferred to Slice 5.
- `BarStyle` in the existing contract has no base alpha field, so reflection and beam base alpha remain applied from `WaveformLook` in `Spectrum.tsx` while the layer style carries the contract fields.

## Open Items

- Slice 5 should move matrix and material application into the renderer boundary.
- A later contract pass may need explicit base alpha or non uniform transform fields for fully renderer neutral beam and reflection parameters.
