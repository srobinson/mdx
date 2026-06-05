---
title: Cubicell rounded corner rendering implementation
type: sessions
tags: [frontend, cubicell, renderer, geometry, thumbnails]
summary: Implemented scene owned socketed corner caps while preserving straight rails, full faces, domain edge resolution, and persistence.
status: active
source: frontend-engineer
confidence: high
created: 2026-08-16
updated: 2026-08-16
---

# Summary

Removed the rejected rounded rail spike and restored the rectangular baseline with `defaultCubeEdgeThickness = 0.014`. Added a scene owned `CubeCornerLook`, one shared 54 position socketed corner geometry, distinct corner instance buckets, stable corner keys, eligible incident rail retreat, live rendering, and State thumbnail rendering.

Focused contracts prove radius zero identity, rectangular rails, no more than eight caps per cube, stable keys, hidden edge fallback, zero gap contention fallback, bounded cap geometry, mixed thickness sockets, owner edge presentation state, and shared live plus thumbnail geometry.

# Architecture Decisions

- `src/scene/cubeCornerLook.ts` owns the fixed non-persisted radius, eight corner identities, same-cell eligibility, zero-gap contention checks, owner edge priority, cap transforms, rail retreats, and geometry.
- `createCubeCellInstances` remains the only producer of rendered face, edge, and corner instances. It leaves face matrices and edge hit targets unchanged.
- Corner caps inherit color, opacity, tween, and selected scale from the deterministic owner edge selected through the existing edge claim priority function.
- `cubePartLayerSpecs.ts` is the shared live and thumbnail metadata owner for geometry class, part kind, opacity class, and picking policy.
- Corner geometry uses the existing `createInstancedPartMeshWithGeometry` path. `createInstancedPartMesh` still accepts only box and plane geometry kinds.
- Incremental slots include opaque, translucent, and ghost corner buckets with `corner:<cubeId>:<cornerId>` identity.

# Performance Notes

- Cap geometry has 54 positions, below the 96 position contract.
- Instance count is bounded to eight caps per cube. Geometry is allocated once per mesh, never per cube.
- The production delivery check measured the intentional renderer increase and passed after ratcheting only affected fields: editor studio 387,224 to 389,138 bytes, shared renderer 419,202 to 421,381 bytes, default interactive 455,442 to 457,624 bytes, and motion increment 13,429 to 13,441 bytes.
- `pnpm check:budget` passed. The shared renderer core chunk remained 187.36 kB gzip.

# Deviations from Spec

- The first geometry uses a two-segment spherified outer octant with three full square sockets. This yields 54 positions and stays inside the baseline rail union.
- The fixed radius is half the default edge thickness. Mixed thickness corners clamp to half the smallest incident thickness.
- The requested contract scope is complete. The broader browser matrix from the design document remains follow-up work.

# Open Items

- Add browser contracts for owner edge selection by clicking a cap, hidden edge edits, mixed thickness, nonuniform cube size, zero gap seams, motion scrub, State thumbnails, and Storyboard parity.
- Review the fixed radius head on and at 45 degrees in both polarities with product design.
- Existing development browser runs reported ResizeObserver loop notifications and a deprecated `THREE.Clock` warning. They were present outside the corner contracts and were not changed in this slice.
