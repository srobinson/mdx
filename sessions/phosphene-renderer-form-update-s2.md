---
title: Phosphene Renderer Form Update S2
type: sessions
tags: [frontend, phosphene, renderer, forms, vite-plus]
summary: Extracted pure per frame form update helpers for oscilloscope, waterfall, and spectrum.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Summary

Implemented renderer migration Slice 2 by extracting pure, three free per frame update helpers from the three active form components. `Waveform`, `Waterfall`, and `Spectrum` still own their existing three.js or drei upload work, preserving visuals while moving signal math and buffer mutation into unit testable modules.

## Architecture Decisions

- Added `updateOscilloscope` in `src/oscilloscope.ts` to compose `sampleDisplacements`, `smoothDisplacements`, and `placeAlongPath` over caller owned `target`, `smoothed`, and `positions` buffers.
- Added `updateWaterfall` in `src/waterfallState.ts` to compose `pushWaterfallFrame` and `placeAlongPath` for the newest row, while leaving row visibility, depth, rise, and color in `Waterfall.tsx`.
- Added `updateSpectrum` in `src/spectrumBands.ts` to compose `sampleBars` and shared `smoothDisplacements` over caller owned `target` and `heights` buffers.
- Components memoize buffer and option objects outside `useFrame`, avoiding new per frame helper argument allocations beyond the existing renderer uploads.
- Did not wire `src/render/contract.ts`, matching the S2 boundary that leaves Frame writing for S3.

## Performance Notes

Verification gates passed on 2026-06-15:

- `vp check`: `All 35 files are correctly formatted`; `Found no warnings, lint errors, or type errors in 23 files`
- `vp lint .`: passed with no output
- `vp build`: passed, `✓ built in 368ms`, with the existing Vite chunk size warning
- `vp test`: `Test Files 4 passed (4)`, `Tests 18 passed (18)`

## Deviations from Spec

No behavioral deviations were introduced. Migration step 2 also mentions future `PathSample` tangent and endpoint mode work, but this slice's mailbox boundary allowed only the three form modules, their components, and tests, so `pathShape.ts` was left unchanged.

## Open Items

- S3 should make forms write the retained `Frame` contract from `src/render/contract.ts`.
- Later migration work still needs the path tangent and endpoint mode extension when the boundary permits touching `pathShape.ts`.
