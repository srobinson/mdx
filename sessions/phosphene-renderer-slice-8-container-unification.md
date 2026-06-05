---
title: Phosphene Renderer Slice 8 Container Unification
type: sessions
tags: [frontend, phosphene, renderer, pathshape, spectrum, waterfall, embed, ring, svg, polyline]
summary: Routed curved container placement through shared path shapes, added gallery showcases, and fixed closed ring polylines across three.js and SVG.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Summary

Implemented Slice 8 container unification and follow up ring seam hardening. `PathSample` carries tangent fields, spectrum bars project through `pathShape`, and waterfall rows use `look.shape` plus `arcSpanDeg` instead of a pinned straight path. The embed gallery includes URL addressable panels for radial spectrum and curved waterfall.

A later seam fix added a shared closed polyline contract. Ring shapes, plus full circle arcs, now sample line vertices with distributed `i / count` placement and render an explicit last to first join. Open straight lines and partial arcs keep inclusive `i / (count - 1)` placement.

## Architecture Decisions

- Extended `PathSample` with `tx` and `ty` while keeping existing `placeAlongPath` callers compatible through an optional closed parameter.
- Added retained spectrum path resources, including the path function and a scratch sample, to avoid per frame allocation.
- Preserved the straight spectrum axis with the old inclusive slot placement, while ring and arc bars use distributed `slot / bars` placement to avoid closed ring seam duplication.
- Used `angle = atan2(ny, nx) - PI / 2` so the existing three.js bar matrix writer rotates bars along the path normal.
- Mirrored the oscilloscope path refresh pattern in waterfall state so shape changes update without structural frame rebuilds.
- Added `EmbedGallery` panels by extending the existing `PANELS` data array only, keeping panel rendering unchanged.
- Added `isClosedPathShape` as the single shape ownership helper for deciding whether a line primitive is closed.
- Added `PolylinePrimitive.closed` so closed state flows from form modules through retained frames into renderers.
- Updated three.js line resources to allocate `count` segments for closed polylines and write the closing segment without per frame allocation.
- Updated SVG line rendering to keep one extra point that duplicates the first projected point for closed polylines, while continuing to mutate the existing point list in place.

## Performance Notes

Verification passed on 2026-06-15 for the engine slice:

- `vp check`: PASS, 48 files formatted, 36 files linted and type checked.
- `vp lint .`: PASS, exit 0.
- `vp build`: PASS, 677 modules transformed, built in 317 ms.
- `vp test`: PASS, 6 test files and 29 tests.

Verification passed again after the embed gallery addition:

- `vp check`: PASS, 48 files formatted, 36 files linted and type checked.
- `vp lint .`: PASS, exit 0.
- `vp build`: PASS, 677 modules transformed, built in 385 ms.
- `vp test`: PASS, 6 test files and 29 tests.

Ring seam bug fix verification:

- Fail first targeted tests failed before implementation with missing `closed` contract, duplicate ring seam placement, absent three.js closing segment, and absent SVG closing point behavior.
- Focused regression tests passed after implementation: `vp test tests/waveform.test.ts tests/waterfall.test.ts tests/threePolylineResource.test.ts tests/svgProjection.test.ts`, 4 files and 28 tests.
- `vp check`: PASS, 48 files formatted, 36 files linted and type checked.
- `vp lint .`: PASS, exit 0.
- `vp build`: PASS, 677 modules transformed, built in 339 ms, JavaScript gzip 400.03 kB with the existing large chunk warning.
- `vp test`: PASS, 6 test files and 37 tests.
- `git diff --check`: PASS.

Changed files remain under the project thresholds. Current line counts: `lineGeometry.ts` 64, `pathShape.ts` 81, `render/contract.ts` 91, `oscilloscope.ts` 139, `waterfallState.ts` 257, `ThreePolylineResource.ts` 168, `ThreeRenderer.ts` 221, `SvgRenderer.ts` 233, `svgProjection.ts` 173, `waveform.test.ts` 231, `waterfall.test.ts` 165, `threePolylineResource.test.ts` 69, and `svgProjection.test.ts` 90.

## Deviations from Spec

- Straight spectrum bars keep the prior inclusive slot math to satisfy the byte identical straight axis regression gate.
- Ring and arc bars use the distributed periodic slot math required for the new curved container capability.
- The seam bug fix intentionally touched SVG renderer code because the confirmed bug was geometry level and appeared in both three.js and SVG.

## Open Items

- SVG breadth for spectrum and waterfall remains a later slice by boundary.
- The production build still reports the pre existing large chunk warning at 400.03 kB gzip.
