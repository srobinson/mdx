---
title: Phosphene Renderer Frame Seam S3
type: sessions
tags: [frontend, phosphene, renderer, frame]
summary: Implemented the Frame seam for oscilloscope and waterfall while preserving the existing three.js renderer path.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Summary

Implemented Slice 3 of the renderer migration for the two line forms. Oscilloscope and waterfall now create and update retained `Frame` objects from `src/render/contract.ts`, and their React components consume those frame primitives while continuing to use the existing drei `Line` upload path.

## Architecture Decisions

- Added `oscilloscopeForm: FormModule<WaveformLook>` in `src/oscilloscope.ts` with one `PolylinePrimitive` backed by the frame's retained positions buffer.
- Kept oscilloscope target, smoothed, and path cache resources in a `WeakMap<Frame, ...>` so `update(frame, signal, look)` can mutate without per frame allocation.
- Added `waterfallForm: FormModule<WaveformLook>` in `src/waterfallState.ts` with one retained `PolylinePrimitive` per row.
- Kept `WaterfallState` and reusable update options in a `WeakMap<Frame, ...>` so the form can push the newest row, place it, and write row visibility, transform, width, and faded color into primitives.
- Left the three renderer extraction deferred. `Waveform.tsx` and `Waterfall.tsx` still own `geometry.setPositions`, material updates, and group transforms, but now read those values from `Frame` primitives.
- Spectrum was intentionally untouched because the mailbox scoped it to S4.

## Performance Notes

- No per frame arrays or option objects are allocated in the new form module update paths.
- Existing `Line2.geometry.setPositions` remains the known per frame allocation point for the three line backend until the later custom polyline resource slice.
- Verification passed on 2026-06-15:
  - `vp check`: all 35 files formatted, no warnings, lint errors, or type errors in 23 files.
  - `vp lint .`: exit 0 with no output.
  - `vp build`: built successfully in 434ms, with the pre-existing Vite chunk size warning.
  - `vp test`: 4 files passed, 20 tests passed.

## Deviations from Spec

- `Frame.camera` uses the current line-form camera values from `FORM_VIEWS`, but the component camera path is not rewired in this slice as requested.
- Waterfall remains pinned to the straight path to preserve current visuals. The broader `pathShape` tangent and waterfall shape migration remains a later migration item.

## Open Items

- S4 should add the spectrum `BarFieldPrimitive` seam and renderer extraction.
- A later slice should move three-specific line upload, material, and transform application behind the renderer layer.
- The custom polyline resource is still needed to remove the `Line2.setPositions` per frame allocation.
