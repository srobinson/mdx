---
title: Phosphene Occluder Alignment Fix
type: sessions
tags: [frontend, phosphene, occlusion, react-three-fiber]
summary: Unified the depth occluder with the fitted morph point cloud space and verified rotated alignment.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Fixed the rotated occluder drift in phosphene. The depth skin now uses only the head surface and is baked into the same fitted display space as the morph point cloud. Morph deltas are transformed into that fitted space, and the occluder is recessed slightly behind the sampled skin dots so front surface dots are not clipped.

## Architecture Decisions

- Removed separate eye and teeth occluder entries. The skin depth surface should occlude eyes and teeth through the head openings, rather than letting eye or teeth meshes write their own drifting depth shapes.
- Replaced per frame `fitMatrix * part.mesh.matrixWorld` writes with creation time fitted geometry for the head occluder. The parent display group now supplies idle yaw and OrbitControls perspective identically to dots and occluder.
- Preserved morph binding by converting source morph deltas into fitted display space and writing morph influences each frame.
- Added `tests/faceDepthOccluder.test.ts` to cover the fitted display space contract and fitted morph delta mapping.

## Performance Notes

- The occluder no longer recomputes per part matrices every frame. Per frame work is limited to morph influence writes.
- Validation passed: `vp check --fix`, `vp check`, `vp test`, and `vp build`.
- Visual smoke used Chrome CDP to drag through a full orbit with zero runtime exceptions and zero warning or error log entries.

## Deviations from Spec

None. The implementation follows the occluder and dots same space requirement. The browser plugin was unavailable, so visual verification used local Chrome DevTools Protocol automation.

## Open Items

- Production bundle remains above the default 200 KB gzip target due existing Three and Leva dependencies. This bug fix did not address bundle splitting.
- Keep the captured proof files: `shot-fix-front.png`, `shot-fix-q-left.png`, `shot-fix-q-right.png`, and `shot-fix-profile.png`.
