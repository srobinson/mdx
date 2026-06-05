---
title: Aurora SVG Bands Implementation
type: sessions
tags: [frontend, phosphene, svg, renderer, aurora]
summary: Added and refined the Aurora form as a premium retained SVG living wallpaper with gradients, smoothed ridges, controls, URL selection, and tests.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented the Aurora form for Phosphene as stacked filled SVG bands, then refined it into a calmer aurora borealis living wallpaper. The form is selectable through `?renderer=svg&form=aurora` and through Leva controls.

## Architecture Decisions

- Added `BandFieldPrimitive` to the renderer contract so filled bands share the retained primitive model with polylines and bar fields.
- Added `src/auroraBands.ts` to own Aurora frame creation, audio sampling, smoothing, baseline layout, gradient progress, Catmull-Rom ridge densification, and per-band ambient drift.
- Added `auroraColorMid`, `auroraSmoothness`, and `auroraDriftPhaseSpread` controls so the Aurora palette, ridge smoothness, opacity, overlap, and drift can be tuned without changing shared Spectrum keys.
- Added `src/render/svg/svgBands.ts` to render each band as a stable SVG polygon with preallocated points and per-band `<linearGradient>` definitions in `<defs>`.
- Split SVG primitive ordering and transform cache helpers out of `SvgRenderer` to keep renderer files below the project 300 line limit.
- Kept Three Aurora as a graceful fallback to the existing line view for this slice, since the requested scope was SVG only.

## Performance Notes

- Per frame SVG work mutates retained polygon point lists. There is no per-frame SVG `d` string rebuild.
- Per-band gradients are created at reconcile and use cached stop color and opacity attribute writes.
- `vp build` passed in 329 ms and reported the existing large chunk warning: 403.49 kB gzip for the main JavaScript asset.
- Changed source and test files remain under 300 lines. Largest touched files: `SvgRenderer.ts` 272, `svgBands.ts` 241, `primitive.ts` 236, `auroraBands.ts` 184.

## Deviations from Spec

- Aurora uses dedicated look keys such as `auroraColorLow`, `auroraColorMid`, and `auroraFillOpacity` while exposing Leva labels as `colorLow`, `colorMid`, and `fillOpacity` to avoid colliding with Spectrum keys.
- The smoothing requirement was met with dense Catmull-Rom sampled polygon points instead of SVG path Beziers, preserving the retained point-list hot path.
- Browser plugin verification was attempted earlier, but no in app browser instance was available. Local dev serving was checked with HTTP 200 for the Aurora URL.

## Open Items

- Port Aurora to the Three backend in the next slice.
- Revisit bundle splitting separately if the existing 403.49 kB gzip warning becomes part of this feature scope.
