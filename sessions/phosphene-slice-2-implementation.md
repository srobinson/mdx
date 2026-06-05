---
title: Phosphene Slice 2 Implementation
type: sessions
tags: [frontend, phosphene, react-three-fiber, leva, presets, idle-life]
summary: Implemented per-part colors, tweened saved presets, idle-life gestures, and bezier controls for phosphene.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented phosphene Slice 2: per-mesh color tinting, a shared tween core, localStorage-backed named presets, additive idle-life motion, and cubic-bezier controls with a small curve preview. The face now supports warm face dots, cyan eye dots, teeth color, and background color while preserving the halftone brightness treatment.

## Architecture Decisions

- Added `aPartId` to generated point geometry and `uPartColors[8]` to the point shader. The shader multiplies the existing tone by the part color, so tinting does not flatten lighting or speech brightness.
- Centralized color normalization and linear RGB interpolation in `src/colors.ts`.
- Added `src/tween.ts` as the shared cubic-bezier timing primitive used by preset transitions and idle gestures.
- Added `src/lookTween.ts` to hold and advance runtime look snapshots. A small `useFrame` driver in `App.tsx` advances active transitions so React state only changes while animation is active.
- Added `src/presets.ts` for built-in plus saved preset management under localStorage key `phosphene.presets`.
- Added `src/idleLife.ts` for continuous micro-life plus discrete gestures that ease in, hold, and ease back to zero. Idle expression offsets are applied through expanded ARKit morph bindings in `src/faceMotion.ts`.
- Split large touched files under the slice gate: `DottedFace.tsx` now delegates frame helpers and resource hooks; `faceDepthOccluder.ts` delegates geometry creation to `faceDepthGeometry.ts`.

## Performance Notes

- Avoided per-frame allocations in the new idle scheduler. Scheduler offsets, target offsets, and tween state are reused.
- Refactored `eyeGaze` to interpolate scalar pitch and yaw values rather than allocating target objects per frame.
- Runtime preset transitions intentionally hold grid geometry until the transition target so density changes do not rebuild the point cloud every frame.
- Verification build still reports the known three.js-dominated production bundle at 417.97 kB gzip. This remains tracked in `NOTES/BACKLOG.md`.

## Deviations from Spec

- The bezier editor uses numeric x1, x2, y1, y2 Leva controls plus an inline preview overlay instead of adding `@leva-ui/plugin-bezier`. This avoids adding a new dependency while preserving visual curve feedback.
- The in-app Browser plugin reported `iab` unavailable, so screenshot verification used headless Chrome CDP.

## Open Items

- Idle full-buffer re-upload remains open.
- Occluder recess constants remain fixed rather than dot-size-relative.
- Bundle size remains above the 200 kB guideline due to three.js.
- Full 360-degree dotted back-of-head sampling remains a product decision.
