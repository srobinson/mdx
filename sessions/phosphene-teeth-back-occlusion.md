---
title: Phosphene teeth and back occlusion fix
type: sessions
tags: [frontend, phosphene, react-three-fiber, occlusion, teeth]
summary: Refined phosphene teeth rendering and hid front-face bleed from rear views.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented the phosphene teeth and rear occlusion fix. Teeth now use denser per-part sampling with a smaller point-size scale, and the lower teeth proxy is scaled down, moved inward, and jaw-driven so it reads as a finer lower row inside the mouth.

Rear views no longer show eyebrow, eye, teeth, or mouth-interior dot clusters. The shader fades the front-only point cloud out as the camera moves behind the face, matching the current front-sampled geometry contract.

## Architecture Decisions

- Kept one fitted display space invariant for dots and occluders.
- Restored eye and teeth depth occluders as rigid feature occluders using `fitMatrix * part.mesh.matrixWorld`.
- Recessed rigid feature occluder geometry so front dots remain visible while the occluders still provide depth backing.
- Added per-point dot scale through `aDotScale`, written from `FaceSurfacePart.pointScale`, so teeth can be smaller without a second point cloud or material.
- Added `uFeatureVisibility`, computed from camera position versus face forward direction, to hide the front-only point cloud from rear views.
- Added lower-teeth proxy tests plus occluder and point-attribute test coverage.

## Performance Notes

- `vp build` passed.
- Build output remains above the default 500 kB warning threshold, consistent with the existing Three and R3F bundle shape: `dist/assets/index-CAoj-vfC.js` is 1,439.68 kB, 412.71 kB gzip.
- No new file exceeds 700 lines.

## Deviations from Spec

- The back proof screenshot is intentionally black because the current geometry samples the front of the face only. Rear views therefore fade out the front-only point cloud rather than showing a dotted back-of-head surface.
- CDP screenshot capture required a forced render in the verification harness because `preserveDrawingBuffer` is false. The committed app code does not include the temporary debug hook used for capture.

## Open Items

- The `THREE.Clock` deprecation warning remains from the upstream R3F stack.
- The production bundle still needs a separate code-splitting pass if the project wants to meet the 200 kB gzip target.
