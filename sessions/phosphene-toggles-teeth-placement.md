---
title: Phosphene toggles and teeth placement
type: sessions
tags: [frontend, phosphene, react-three-fiber, leva, occlusion]
summary: Added visibility toggles, persisted toggle state in presets, and moved the lower teeth proxy forward.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented Leva visibility controls for solid skin, eyes, and teeth. Solid skin off now removes the depth occluder path, making the point cloud see through. Eyes and teeth off now hide their dots and omit their feature occluders. The lower teeth proxy now sits forward under the upper row while still dropping with `jawOpen`.

## Architecture Decisions

- Added `visibility` to `RuntimeLook` and `LookPreset`, with default true values for built in presets.
- Added a small `faceVisibility` helper so point visibility and occluder membership share one rule.
- Used shader part visibility uniforms to hide eye and teeth dots without rebuilding point geometry.
- Made `DottedFace` create no occluder when `solidSkin` is off, so disabled solid skin has no per frame occluder write.
- Persisted visibility state through saved presets and preset selection.

## Performance Notes

- `solidSkin=false` skips depth occluder creation and the `writeFaceDepthOccluder` frame path.
- Point geometry is unchanged by eye and teeth visibility toggles, avoiding rebuild churn.
- Build output remains three.js dominated at 419.07 kB gzip.

## Deviations from Spec

None. The optional preset capture was implemented.

## Open Items

No new open items. Existing bundle size backlog remains unchanged.

## Verification

- `vp test`: pass, 8 files and 19 tests.
- `vp build`: pass, JS gzip 419.07 kB.
- `vp check`: pass, no warnings, lint errors, or type errors.
- Headless Chrome CDP with SwiftShader verified WebGL active, toggle states applied, no severe console logs, and captured `shot-tg-seethrough.png`, `shot-tg-hidden.png`, and `shot-tg-teeth.png`.
