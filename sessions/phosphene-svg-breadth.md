---
title: Phosphene SVG Breadth
type: sessions
tags: [frontend, phosphene, renderer, svg, waterfall, spectrum]
summary: Extended the SVG backend to waterfall rows and opaque spectrum bars, fixed SVG host form selection, and added true SVG waterfall perspective.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented SVG backend breadth for phosphene by extending `SvgRenderer` beyond the oscilloscope polyline path. The renderer now supports multi-polyline waterfall frames with stable SVG row nodes and spectrum `BarFieldPrimitive` frames as SVG polygon bars. The `?renderer=svg` toggle now applies to interactive oscilloscope, waterfall, and spectrum views while `?embed` still falls back to the default renderer.

A follow-up screenshot bug showed that `SvgHost` still fed the oscilloscope frame to every SVG form. The fix added a shared `formModuleFor` selector and wired both `SvgHost` and `Visualizer` through it so SVG and three form selection share one source of truth.

A second screenshot review showed the SVG waterfall was flat because depth used an oblique shear. The latest fix added a three-free per-point perspective path for multi-polyline waterfall frames so far rows narrow and rise toward a vanishing point while the single-polyline oscilloscope path remains affine.

## Architecture Decisions

- Kept the existing Frame and primitive contract unchanged.
- Split SVG rendering helpers by concern under `src/render/svg/`:
  - `svgPolyline.ts` owns stable polyline nodes, point-list sizing, row style caching, and in-place point mutation.
  - `svgBars.ts` owns opaque spectrum bar polygons and exports the pure bar corner projection used by tests.
  - `svgDom.ts` centralizes SVG namespace and cached style writes.
  - `svgProjection.ts` owns the affine SVG projection path and stores camera-derived `viewDistance` for perspective helpers.
  - `svgWaterfallProjection.ts` owns the model, group, and perspective projection math for waterfall rows.
- Waterfall rows are drawn into a stable pool of polylines in far-to-near painter order by sorting source primitives by depth and reusing DOM nodes in visual order.
- The waterfall perspective path clears the SVG group transform and projects row points directly through row transform, group scale and rotations, and a camera-distance perspective divide.
- The oscilloscope stays on the existing affine group-transform path, preserving z-zero planar output.
- Spectrum SVG renders the required opaque bars layer only. Beam and reflection layers remain backend-specific effects for this slice.
- `src/forms.ts` owns the `WaveformForm -> FormModule<WaveformLook>` mapping. It returns stable wrapped modules whose structural keys include `form`, so `useStructuralFrame` rebuilds on oscilloscope, waterfall, and spectrum switches even when numeric structural values collide.
- `SvgHost` uses the selected form module for both `useStructuralFrame` and `tickPhospheneLoop`; its aria label is generic: `Phosphene SVG renderer`.
- `Visualizer` still renders the same three components, but its `FormScene` selects through `formModuleFor` to avoid a parallel form-to-module mapping.

## Performance Notes

- Hot paths mutate `SVGPointList` entries rather than rebuilding `points` strings.
- Waterfall multi-row draws force point mutation after painter-order remapping, but style attributes are cached and only rewritten on value changes.
- Bar geometry mutates four polygon points per bar and caches fill, opacity, and visibility writes.
- Form selector wrappers are module-level constants, so selection adds no per-frame allocation.
- The waterfall sort comparator is hoisted to a renderer field, avoiding a per-draw comparator closure allocation.
- Build output remained dominated by the existing application chunk warning: `dist/assets/index-Dkc63y5Q.js` gzip 401.56 kB.

## Deviations from Spec

- SVG spectrum implements the opaque bars layer only. Beams and reflection were intentionally skipped as optional backend-specific effects for this slice.
- SVG waterfall uses a minimal camera-distance perspective divide with the line-form camera-derived projection. It targets the same receding trapezoid read as the three backend without importing three.js.

## Open Items

- Consider adding SVG beam and reflection layers if product direction needs them.
- Safari `SVGPointList` mutability remains a known browser smoke-test item from the design synthesis.

## Verification

- `vp install`: already up to date.
- `vp check`: PASS, 59 files formatted, 47 files lint/type clean.
- `vp lint .`: PASS, exit 0.
- `vp build`: PASS, 683 modules transformed, built in 324 ms, existing 401.56 kB gzip chunk warning.
- `vp test`: PASS, 9 files, 46 tests.
- `grep -R "three\\|@react-three/drei" -n src/render/svg`: PASS, no matches.
- `wc -l src/render/svg/*`: PASS, all render/svg files below 300 LOC, largest `SvgRenderer.ts` at 277 LOC and `svgProjection.ts` at 262 LOC.
- `wc -l tests/svgProjection.test.ts tests/svgRenderer.test.ts`: PASS, tests below 300 LOC.
- `git diff --check`: PASS, no whitespace errors.
