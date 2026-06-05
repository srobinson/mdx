---
title: Scene Control Palettes Slice 1
type: sessions
tags: [frontend, little-background-lab, gradient-waves, scene-control, palettes]
summary: Implemented end to end preset palettes for gradient-waves with persistence and host-resolved WebGL uniforms.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Summary

Implemented Slice 1 of the Scene Control System on `feat/scene-control-system`, commit `1e4f380`. Gradient waves now exposes `forest`, `dusk`, and `slate` preset palettes, renders a palette card grid, persists `scenePaletteId`, and resolves palette colors in the host before uploading `uGradientStart` and `uGradientEnd` to the shader.

## Architecture Decisions

- Added `Rgb01` and `ScenePalette` to the ambient scene contract, with scene-owned `palettes` and `defaultPaletteId` projected through `sceneRegistry` metadata.
- Kept palette persistence additive and schema compatible by adding optional `ThemeSettings.scenePaletteId`, then validating and normalizing it exactly through the existing theme validation choke point.
- Moved gradient daylight color mixing out of GLSL and into `createAmbientBackground` using `computeDaylight` and `resolvePaletteGradient`.
- Extended `AmbientBackground` with `setScenePalette`, called from `main.ts` after theme validation.
- Kept `forest` byte-identical to the previous baked shader endpoints at default day progress by returning exact endpoints at daylight boundaries.

## Performance Notes

- `pnpm build` output stayed well under the 200KB gzipped target: JS 27.57KB gzip, CSS 4.61KB gzip.
- Palette resolution is per frame but constant time and only uploads two `vec3` uniforms for scenes that declare palettes.

## Deviations from Spec

- Skipped local browser shader visual verification because the orchestrator explicitly said they would perform the live shader-error visual check.
- Added palette-specific CSS to `src/theme/panel/panel.css` instead of `src/styles.css` because `src/styles.css` is already over the 700 line threshold.

## Open Items

- Visual designer may tune the `dusk` and `slate` palette values later.
- Slice 2 randomize controls and Slice 3 day modulation remain out of scope for this commit.
