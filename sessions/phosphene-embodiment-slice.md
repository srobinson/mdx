---
title: Phosphene Embodiment Slice
type: sessions
tags: [frontend, phosphene, react-three-fiber, cdp, avatar]
summary: Implemented multi mesh dotted face sampling with rigid eye and teeth bindings, idle gaze, orbit controls, and softened blink motion.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented the phosphene embodiment slice. The dotted avatar now samples the head, both eyeballs, and teeth. Head dots keep morph target barycentric binding. Eye and teeth dots bind to their rigid mesh nodes and are transformed each frame from local space through the live `matrixWorld`.

Added subtle idle gaze on the eyeball nodes, Drei `OrbitControls` with damping and bounded zoom, idle yaw pause during active orbit input, and a smoother randomized blink cadence with occasional double blinks.

## Architecture Decisions

- Kept the original single surface sampler for proxy and tests.
- Added multi surface composition that reuses the existing structured sampler per target, then combines target clouds into one fitted point geometry.
- Classified `public/face.glb` surfaces by ancestor node names: `head`, `eyeLeft`, `eyeRight`, and `teeth`.
- Split rigid binding math into `src/rigidBinding.ts` to keep all files under 300 lines.
- Added `src/eyeGaze.ts` for deterministic slow gaze targets without runtime randomness.
- Added `sourceIndices` to `SurfaceBinding` so each dot can resolve to either morph driven head binding or rigid node binding.

## Performance Notes

- Validation gates:
  - `vp check`: pass
  - `vp test`: pass, 2 files and 4 tests
  - `vp build`: pass
- Build output remains dominated by Three and Drei: `dist/assets/index-m1wV8Bdc.js` is 410.85 kB gzip. This was pre existing dependency weight and not optimized in this slice.
- Screenshot verification used headless Chrome CDP with SwiftShader at 1200 by 1600:
  - `shot-emb-idle.png`: idle eyes open, eyeballs visible
  - `shot-emb-speak.png`: debug audio 0.6, jaw open, dotted teeth visible
  - `shot-emb-rotated.png`: orbit controlled three quarter view

## Deviations from Spec

No phosphene specific design spec was present in `~/.mdx/design/`. Implementation followed the bus directive as the source of truth.

The in app Browser backend was not registered in this session, and the repo does not carry Playwright. Screenshots were captured with the prior dependency free Chrome CDP path instead.

## Open Items

- Bundle code splitting remains open if the project wants to meet a strict sub 200 kB gzip target with Three and Drei.
- Idle life presets and broader expression systems were intentionally left out because this slice explicitly excluded scope creep.
