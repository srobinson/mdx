---
title: Phosphene Aurora Variety Pass
type: sessions
tags: [frontend, phosphene, aurora, wallpaper, renderer]
summary: Expanded Aurora wallpaper presets into distinct scene profiles with geometry, atmosphere, depth, and framing differences.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-22
updated: 2026-06-22
---

## Summary

Implemented the larger Aurora variety pass. The preset layer now drives distinct scene worlds rather than simple color variants: aurora as luminous veils, sunset as warm horizon bands, abyss as pressure waves, synthwave as jagged neon terrain, and ink as a sparse dark wash.

## Architecture Decisions

- Kept `AURORA_PRESETS` as the shared `WaveformLook` data source for palette, motion, density, smoothing, overlap, and bloom.
- Added `AURORA_SCENE_PROFILES` in `src/auroraPresets.ts` for scene specific concerns: layout, atmospheric SVG background, baseline behavior, ripple profile, depth skew, wallpaper scale, and wallpaper rotation.
- Updated `src/auroraBands.ts` so the existing retained `BandFieldPrimitive` mutates differently per scene without creating renderer specific forks.
- Updated `src/appMode.ts` so `?wallpaper=<preset>` uses each scene's framing instead of a single fixed scale.
- Updated `src/render/svg/SvgHost.tsx` to apply Aurora scene backgrounds in SVG mode.
- Updated `src/render/svg/svgProjection.ts` so z offsets project in SVG, making scene depth visible outside WebGL.

## Performance Notes

Validation passed after implementation:

- `vp check`: 75 formatted files, 63 linted and type checked with no warnings or errors.
- `vp lint .`: passed.
- `vp build`: passed with `dist/assets/index-DB3_X19D.js` gzip size 407.44 kB and the existing large chunk warning.
- `vp test`: passed, 14 files and 59 tests.
- Playwright verified `?wallpaper`, `?wallpaper=sunset`, `?wallpaper=abyss`, `?wallpaper=synthwave`, and `?wallpaper=ink` with zero console errors, SVG scene backgrounds, no UI, no scrollbars, and expected polygon and gradient counts.

## Deviations from Spec

No formal Phosphene design spec exists in `~/.mdx/design`, so this was implemented as an exploratory art direction pass from the user's request for the biggest leap and most variety.

## Open Items

- The production build still emits the existing large chunk warning.
- The next visual leap would be a dedicated retained particle or mist primitive shared by SVG and WebGL.
