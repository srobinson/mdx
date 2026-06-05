---
title: Phosphene T0.2 Halftone Presets
type: sessions
tags: [frontend, phosphene, halftone, r3f]
summary: Implemented three true halftone look presets with size driven white dots and verified build plus screenshots.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented the T0.2 look pass for phosphene. The face now reads as a flatter graphic halftone: fragments are uniform white, the lit value drives dot size, and shadowed regions drop to black by removing dots.

## Architecture Decisions

- Added `src/look.ts` as the single source for preset knobs.
- Added URL preset selection through `?preset=A|B|C`.
- Updated `src/grid.ts` so each preset owns its grid resolution without duplicating point projection logic.
- Kept microphone and idle yaw paths intact.
- Kept generated point geometry and shader material disposal in place.

## Performance Notes

- Lowered grid density versus T0.1 for all presets.
- Preset A uses the sparsest grid, B uses the most structured grid, and C is the default balanced option.
- `vp check`, `vp test`, and `vp build` pass.
- Source files remain under 300 lines, including unchanged `src/audio.ts` at 297 lines.

## Deviations from Spec

None.

## Open Items

- Production bundle remains above the 200 KB gzip target due to three, fiber, and drei. This was already present and outside the T0.2 look only scope.
- Screenshots include the existing audio control overlay.
