---
title: Phosphene glyph field renderer hardening
type: sessions
tags: [frontend, phosphene, renderer, glyph-field, performance]
summary: Hardened GlyphFieldPrimitive SVG and WebGL render paths after adversarial review.
status: active
source: frontend-engineer
confidence: high
created: 2026-07-03
updated: 2026-07-03
---

## Summary

Implemented the slice 2b review fixes on `idea/presence` in commit `e2840a1ca2bf224c4cbb08831cee26a92bc884ff`. The changes remove per tick object and closure allocation from the glyph SVG path and mixed polyline sort path, move glyph material ownership into a small module, add reference counted atlas ownership, and strengthen behavioral coverage.

## Architecture Decisions

- SVG glyph nodes now retain their projected point scratch plus cached numeric attributes. Draws reuse node-owned state instead of allocating a projected point object per sampled glyph.
- Shared SVG transform projection logic lives in `svgProjection.ts` so glyphs and polylines use one transform path.
- Polyline depth ordering now uses an in-place insertion sort to avoid a per draw comparator closure.
- `ThreeGlyphFieldResource` owns geometry, material, buffers, and an acquired atlas texture. Atlas lifetime is reference counted in `glyphAtlas.ts` and released when the final glyph resource is disposed.
- Glyph shader material creation and uniform updates moved to `glyphMaterial.ts` to keep resource ownership focused and files under 300 lines.

## Performance Notes

- Removed the reviewed per sampled glyph object allocation in SVG draw.
- Removed the reviewed per multi-polyline draw comparator closure allocation.
- Replaced `BufferAttribute.addUpdateRange`, which pushes a fresh object, with a retained update range slot.
- Verification: `fmm validate`, `pnpm exec vp check`, `pnpm exec vp test` with 103 tests, and `pnpm exec vp build` all passed. Build still reports the preexisting large chunk warning.

## Deviations from Spec

No functional deviations from the slice acceptance. The atlas is disposed when the final glyph resource releases it, rather than on every resource disposal, so multiple glyph resources can safely share the startup-built texture.

## Open Items

- The Vite build still warns that the main JavaScript chunk is larger than 500 kB after minification.
