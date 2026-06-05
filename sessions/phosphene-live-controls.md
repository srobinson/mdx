---
title: Phosphene Live Halftone Controls
type: sessions
tags: [frontend, phosphene, halftone, leva, r3f]
summary: Added Leva controls for live T0.2 preset tuning with debounced grid rebuilds and mic toggle.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented live browser tuning for the T0.2 phosphene halftone presets. Users can switch presets A, B, and C, tune dot look values, change grid density, and enable the microphone from the Leva panel.

## Architecture Decisions

- Added `leva` through `vp add leva`.
- Added `src/controls.ts` for Leva control state and preset reset logic.
- Kept preset defaults in `src/look.ts`, now including motion defaults for idle yaw and audio gain.
- Kept the Three shader material stable and update dot uniforms live so dot controls do not rebuild geometry.
- Rebuild point geometry only when debounced grid columns or rows change.
- Split geometry disposal and material disposal so grid rebuilds dispose old geometries without disposing the active material.
- Added a Leva microphone boolean that calls `audio.enable()` only from the click path and `audio.disable()` when toggled off.

## Performance Notes

- Grid density changes debounce for 250 ms before raycast grid rebuild.
- Live uniforms update instantly without reallocating geometry or material.
- `vp check && vp test && vp build` passes.
- Source files remain under 300 lines. `src/audio.ts` remains unchanged at 297 lines.

## Deviations from Spec

- The existing bottom audio overlay remains in place alongside the Leva mic toggle. It provides redundant status but does not change the requested control panel behavior.
- The in app Browser connector was unavailable in this session, so local dev verification used headless Playwright with fake microphone permission.

## Open Items

- Production bundle remains above the target because Three, R3F, Drei, and Leva are all included in the main chunk. This was accepted for the look tuning slice.
- `THREE.Clock` emits a deprecation warning from the current R3F stack during dev verification.
