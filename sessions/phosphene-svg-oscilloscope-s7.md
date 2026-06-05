---
title: Phosphene SVG Oscilloscope Renderer S7
type: sessions
tags: [frontend, phosphene, svg, renderer, oscilloscope]
summary: Added and cleaned up an oscilloscope-only SVG backend that consumes the shared Frame behind ?renderer=svg.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Summary

Implemented Slice 7 for phosphene and completed the in-slice fix round. The full-screen oscilloscope can render through an SVG backend with `?renderer=svg&audio=0.7`, while embed mode and non-oscilloscope forms stay on the three.js backend. The SVG backend consumes the same `Frame` as `ThreeRenderer` and leaves `src/oscilloscope.ts`, `src/pathShape.ts`, and `src/render/contract.ts` unchanged.

## Architecture Decisions

- Added `src/render/svg/SvgRenderer.ts` as a `Renderer` implementation that owns one SVG `<g>` and one `<polyline>` for the oscilloscope primitive.
- Reconcile pre-creates the `SVGPointList` items. Draw calls `reconcile(frame)` first, then mutates `points.getItem(i).x/y` in place and never assigns `points`, `d`, or `animatedPoints`.
- Extracted pure projection, point-list writer, and color conversion helpers into `src/render/svg/svgProjection.ts` for DOM separation and S8 headroom. `SvgRenderer.ts` is now 228 LOC and `svgProjection.ts` is 144 LOC.
- Cached SVG stroke, stroke width, visibility, group transform, and projection inputs. Unchanged camera and size values skip the per-frame `hypot` and `tan` projection recompute.
- Added `src/render/svg/SvgHost.tsx` with a minimal `usePhospheneLoop` RAF seed that updates `oscilloscopeForm` and draws the renderer.
- Added a neutral `src/render/renderer.ts` interface and standardized renderer teardown on `unmount()`, removing the dead `ThreeRenderer.dispose()` method.
- Moved `useStructuralFrame` from `src/render/three/` to `src/render/` so SVG and three backends share the same structural frame hook without importing across backend boundaries.
- Updated `src/Visualizer.tsx` so the Canvas camera and line-form views derive from `createLineFormCamera()` instead of duplicating the oscilloscope camera literals.

## Performance Notes

- SVG is parity-oriented, not performance-oriented. Per-frame point geometry work avoids string allocation by mutating `SVGPointList` objects in place.
- `src/render/svg` imports no three.js, R3F, or Drei code. Verified with `rg -n "three|@react-three|drei" src/render/svg`, which produced no matches.
- In-app browser smoke for `http://127.0.0.1:5173/?renderer=svg&audio=0.7` was attempted during the initial S7 pass after starting `vp dev`, but the Browser plugin reported `Browser is not available: iab`; no live browser screenshot was captured.

## Verification

- `vp check`: PASS, `All 48 files are correctly formatted`; `Found no warnings, lint errors, or type errors in 36 files`.
- `vp lint .`: PASS, exit 0 with no output.
- `vp build`: PASS, `✓ built in 334ms`; existing large chunk warning remains.
- `vp test`: PASS, `Test Files 6 passed (6)` and `Tests 27 passed (27)`.
- File sizes stayed under the active caps: `SvgRenderer.ts` 228, `svgProjection.ts` 144, `SvgHost.tsx` 121, `renderer.ts` 9, `useStructuralFrame.ts` 22, `svgProjection.test.ts` 71, `Visualizer.tsx` 120, `ThreeRenderer.ts` 211.

## Deviations from Spec

- The shared `useStructuralFrame` hook moved out of `render/three` and the three components updated imports. This keeps the SVG backend free of three-path imports and avoids duplicating the structural frame cache hook.
- The fix round did not touch `src/render/primitive.ts`; camera single-source ownership was achieved by importing `createLineFormCamera()` into `src/Visualizer.tsx`.

## Open Items

- The Browser plugin was unavailable in this runtime, so visual parity was verified through deterministic geometry unit tests and build gates rather than an in-browser screenshot.
- SVG support remains scoped to oscilloscope only; waterfall and spectrum SVG rendering remain deferred.
