---
title: Phosphene occlusion fix
type: sessions
tags: [frontend, phosphene, react-three-fiber, occlusion, threejs]
summary: Added a fitted black depth occluder and jaw driven lower teeth proxy for the phosphene point cloud face.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented the phosphene occlusion fix for the dotted face. The sparse point cloud now renders against a fitted black depth occluder, so rear and interior dots no longer read through the head. Added a simple lower teeth proxy that follows jaw open motion so upper and lower teeth are visible through the open mouth.

## Architecture Decisions

- Added `src/faceDepthOccluder.ts` to build black `MeshBasicMaterial` occluder meshes for every face part using the same world to fit transform as the point cloud.
- The occluder writes depth, uses `LessEqualDepth`, renders before the points, and applies a small polygon offset to avoid z fighting with front surface dots.
- Morphing head occlusion copies morph target influences by name from the active facial weights each frame.
- Rigid eye and teeth occluders update from the live source part matrices, matching eye gaze and jaw driven teeth movement.
- Added `src/lowerTeethProxy.ts` to append a lower teeth part derived from the existing teeth mesh and move it down with `jawOpen`.
- Extracted `src/faceGeometry.ts` so cloning and normal generation are shared rather than duplicated.

## Performance Notes

- The depth occluder reuses cloned geometries and one shared material. Per frame work is matrix and morph influence updates only.
- Source files remain below the 300 line gate.
- Verification passed:
  - `vp check`
  - `vp test`
  - `vp build`
- Visual evidence captured:
  - `shot-occ-idle.png`
  - `shot-occ-speak.png`
  - `shot-occ-rotated.png`
- Chrome CDP runtime check for `?audio=0.6` reported zero exceptions and zero warning or error log entries.

## Deviations from Spec

- No matching design spec existed under `~/.mdx/design/`; implementation followed the bus directive and existing phosphene visual system.
- The in-app Browser backend was unavailable, so verification screenshots used dependency free system Chrome CDP.

## Open Items

- Existing build output still warns that the JavaScript chunk exceeds 500 kB gzip thresholds. This predates the occlusion fix and was not in scope.
- Vite dev logs still show the upstream Three Clock deprecation warning during local serving. Runtime screenshot verification did not surface app exceptions.
