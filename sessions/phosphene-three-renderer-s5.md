---
title: Phosphene ThreeRenderer Extraction S5
type: sessions
tags: [frontend, phosphene, renderer, three]
summary: Extracted the per-frame three.js upload path into ThreeRenderer while preserving mounted React nodes.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Summary

Implemented Slice 5 of the phosphene renderer migration. Per-frame three.js uploads now live in `src/render/three/ThreeRenderer.ts` and focused helpers. `Waveform.tsx`, `Waterfall.tsx`, and `Spectrum.tsx` own retained Frames, mount their drei `Line` or `instancedMesh` nodes, run form updates in `useFrame`, then delegate drawing to `ThreeRenderer.draw(frame)`.

## Architecture Decisions

- Added `ThreeRenderer` with mount, reconcile, draw, resize, unmount, and dispose methods. The current slice keeps React-owned node mounting and stores refs in renderer nodes.
- Moved polyline uploads, line style writes, container transforms, and waterfall row transforms into the renderer.
- Moved spectrum layer matrix uploads into `barMatrices.ts`, including base-anchored centers, beam height scaling, and y-mirrored reflection matrices.
- Added `color.ts` as the single RGB to `THREE.Color` bridge for renderer code.
- Added `useStructuralFrame` so retained Frame rebuilds are keyed by each form module's `structuralKeys`, avoiding hand-copied `[count]`, `[rows, count]`, and `[bars]` dependency lists.
- Kept drei `Line` and `setPositions` for S5 as required. The custom owned-buffer line remains deferred to S6.

## Performance Notes

- No new per-frame allocations were introduced in renderer draw paths. Components allocate refs, seed points, geometries, materials, and renderer node descriptors only on structural changes or mount.
- `ThreeRenderer` uses a retained `Object3D` scratch for bar matrix composition.
- Verification:
  - `vp check`: PASS, `All 42 files are correctly formatted`, `Found no warnings, lint errors, or type errors in 30 files`.
  - `vp lint .`: PASS, exit 0 with no output.
  - `vp build`: PASS, `✓ built in 320ms`; existing large chunk warning remains.
  - `vp test`: PASS, `Test Files 4 passed (4)`, `Tests 22 passed (22)`.

## Deviations from Spec

- The Renderer interface is implemented as a practical three backend class while React still owns node creation and disposal for this slice. Renderer resources are scoped per component instance through refs and renderer instances.
- `useStructuralFrame` uses a small ref cache rather than a raw `useMemo` dependency array because the React hooks lint cannot statically validate dependency arrays generated from `structuralKeys`.

## Open Items

- S6 should replace drei `Line` and `setPositions` with an owned `Line2` and direct interleaved buffer writes.
- SVG backend work remains deferred.
