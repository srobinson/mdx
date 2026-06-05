---
title: Phosphene Renderer Line Form Refactor S3.5
type: sessions
tags: [frontend, phosphene, renderer, refactor]
summary: Split shared line geometry and primitive plumbing out of the oscilloscope form without behavior changes.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Summary

Implemented Slice 3.5 as a pure move refactor before the renderer extraction. Shared line geometry math now lives in `src/lineGeometry.ts`, generic Frame primitive helpers now live in `src/render/primitive.ts`, and oscilloscope keeps only oscilloscope form ownership.

## Architecture Decisions

- Moved `sampleDisplacements`, `smoothDisplacements`, `placeAlongPath`, and `DisplacementOptions` to the neutral, three free `src/lineGeometry.ts` module.
- Moved polyline construction, transform and RGB helpers, line form camera setup, degree conversion, and polyline narrowing to `src/render/primitive.ts` for reuse by later renderer primitives.
- Updated waterfall, spectrum, waveform, and test imports so waterfall no longer imports from the oscilloscope form module.
- Kept `structuralKeys` unchanged. Deriving memo dependencies from them remains deferred to the next renderer slice.

## Performance Notes

This was a pure move refactor. The retained buffers and per frame mutation model from Slice 3 remain unchanged. Verification passed with `vp check`, `vp lint .`, `vp build`, and `vp test`; `vp test` reported 20 tests passing.

## Deviations from Spec

No behavioral deviations. The only non move adjustments were the requested removal of the redundant oscilloscope path self assignment, a one line hex color contract comment, and the waterfall JSX narrow once cleanup.

## Open Items

- Slice 4 should add the spectrum bar field seam and consume the reusable primitive helpers.
- A later renderer extraction can centralize polyline upload behavior once the Frame reader exists.
