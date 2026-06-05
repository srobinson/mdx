---
title: Scene Control Randomize Dice Slice 2
type: sessions
tags: [frontend, little-background-lab, gradient-waves, scene-control, randomize]
summary: Implemented shape and palette dice for gradient waves with pure roll logic, transient undo, and reduced-motion-safe feedback.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Summary

Implemented Slice 2 of the Scene Control System on `feat/scene-control-system` and committed it as `0756ab6`. Gradient waves now exposes randomize metadata, a shape dice for the five shape parameters, a palette dice for preset palettes, a shape-only `tasteful|wild` editor preference, and single-step transient undo.

## Architecture Decisions

- Added `randomizable?: boolean` and `tastefulRange?: AmbientSceneParamRange` to `AmbientSceneParam`.
- Projected randomize metadata through `AmbientSceneParamMetadata`, with live registry metadata defaulting `randomizable` to `true`.
- Kept dice math in `src/theme/panel/randomize.ts` as pure `rollParams(params, mode, rng)` for deterministic tests.
- Kept `tasteful|wild`, undo, and roll feedback as panel module state. No new `ThemeSettings` field was added.
- Shape dice passes only parameters with `tastefulRange`, so it rolls `lines`, `amplitude`, `wavelength`, `stagger`, and `sway`, never `dayProgress` or palette.
- Palette dice excludes the active palette and only writes `scenePaletteId`.

## Performance Notes

- `pnpm test` passed: 100/100 tests.
- `pnpm build` passed.
- Build output stayed well below the 200KB gzip target: JS gzip 28.71KB, CSS gzip 4.83KB.
- Dice spin and slider thumb feedback are CSS-only and gated by `ctx.sim.reducedMotion` plus the existing `.theme-pane--still` rule.

## Deviations from Spec

- No browser visual check was performed in this worker because the orchestrator explicitly owns the live shader visual check.
- The `tasteful|wild` editor preference is in-memory only. No existing panel preference store was present, and it was intentionally not added to `ThemeSettings`.

## Open Items

- Slice 3 day modulation remains out of scope.
- Visual designer may still tune palette and tasteful range values in a follow-up.
