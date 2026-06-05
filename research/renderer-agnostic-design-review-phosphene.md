---
title: Renderer Agnostic Design Review for Phosphene
type: research
tags: [phosphene, renderer, svg, threejs, review]
summary: Adversarial review of whether the current src implementation can migrate to a renderer agnostic Frame contract.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Executive Summary

The current forms can migrate to a renderer agnostic Frame if the contract models two general primitives, polylines and bars, plus per primitive topology, style, transform, material variant, and dirty flags. The risky seam is not the current Waveform or Waterfall path, but making Spectrum and near future radial spectrum fit a generic bar primitive without hard coded spectrum branches.

## Project Metadata

- Language: TypeScript and React.
- Rendering stack: React Three Fiber, drei, three.js, postprocessing.
- Toolchain: Vite Plus via `vp`.
- fmm: unavailable in this checkout, `.fmm.db` was missing.

## Detailed Findings

1. Polyline coverage is strong for Waveform and Waterfall. `src/Waveform.tsx:13-36` writes one `Float32Array` into `Line.geometry.setPositions`. `src/Waterfall.tsx:16-64` writes the newest row positions, then updates per row visibility, z, y, and color. A Frame polyline therefore needs point topology, positions, transform, visible, color, line width, and dirty flags for geometry and style.

2. Bars cover current Spectrum only if the bar primitive is layer capable. `src/Spectrum.tsx:17-113` maintains three instanced meshes: bars, beams, and reflection. They share geometry from `createBarGeometry` at `src/Spectrum.tsx:161-170`, but differ by material and reflected group transform at `src/Spectrum.tsx:148-156`. `src/barMaterial.ts:45-68` adds shader uniforms for color ramp, glow, alpha, and blending. A single plain `bar` kind with only x, width, and height would force special casing.

3. Near future radial spectrum is not covered by the current Spectrum implementation unless bars carry arbitrary placement. `src/spectrumBands.ts:52-59` exposes only linear x positions, while `src/pathShape.ts:20-29` and `src/pathShape.ts:38-60` already solve ring and arc topology for waveform polylines. To avoid a radial spectrum branch, bars should be anchored by path sample or matrix, with tangent and normal orientation, not by linear slot x alone.

4. The contract must carry renderer specific payloads without contaminating form logic. SVG needs topology, style, transforms, visibility, and dirty regions. Three.js needs instance matrices, material variant data, and camera state. Current camera is per form in `FORM_VIEWS` at `src/Visualizer.tsx:16-23`, applied per Canvas in `FormView` at `src/Visualizer.tsx:85-98`.

5. Step 3, forms write a Frame while still rendering three.js, can be behavior preserving if state ownership stays identical. Waveform depends on persistent `target` and `smoothed` buffers at `src/Waveform.tsx:15-17`. Waterfall depends on `createWaterfallState` at `src/Waterfall.tsx:19`. Spectrum depends on persistent `target` and `heights` at `src/Spectrum.tsx:19-20`. A stateless Frame builder would change motion.

6. Embed and multi instance risk is instance scoping, not the primitive contract. `src/App.tsx:8-17` switches on `?embed`. `src/EmbedGallery.tsx:17-47` creates one audio source and four Visualizers. `src/Visualizer.tsx:40-71` creates a separate Canvas, camera, Bloom pass, and Starfield per Visualizer. Any shared global Frame, camera, or renderer cache will leak across panels.

## Dependencies

Critical dependencies are `@react-three/fiber`, `@react-three/drei`, `@react-three/postprocessing`, `postprocessing`, and `three` from `package.json`.

## Verification

`vp check && vp test` was attempted. `vp check` failed before tests on formatting in `reference/gradient-waves.html`. `git status --short --branch` stayed pristine: `## idea/svg-renderer`.

## Recommendation

Before engineering starts, define a Frame schema with `polyline[]`, `barLayer[]`, `camera`, and dirty bitsets, then port the existing three.js renderer to consume that Frame first. Add radial spectrum only after current Waveform, Waterfall, Spectrum, `?embed`, and per form camera match.
