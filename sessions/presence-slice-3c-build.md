---
title: Presence Stage 3 slice 3c build half (real face decode, density shading, palette, knobs)
type: sessions
tags: [frontend, phosphene, presence, meshopt, webgl, perf]
summary: Meshopt-decoded real avatar face curves, precomputed-grid density shading, paletteShift wiring, and tuning leva knobs for the phosphene presence form.
status: active
source: frontend-engineer
confidence: high
created: 2026-07-04
updated: 2026-07-04
---

## Summary

Slice 3c BUILD half (items 1-4) of the phosphene presence form, on `idea/presence`,
four staged commits: decode `2856572`, shading `e49ec3d`, palette `52176b5`, knobs
`7275ede`. Closes the 3b deferral by replacing synthesized placeholder face curves with
the avatar's real geometry, adds density shading that draws features out of dust, wires
`paletteShift`, and adds the tuning leva surface. The live visual tuning and the final
adversarial pass are out of scope (Stuart's session / codex).

Gate: `vp check`/`test`/`build` green, 167 tests, extraction byte-identical on re-run,
perf filtered-median 3.64-3.83ms (< 4ms budget) across 6 runs, all touched files < 300.

## Architecture decisions

- **Meshopt decode (`scripts/faceGlb.ts`)**: `public/face.glb` head mesh is one shared
  `EXT_meshopt_compression` ATTRIBUTES bufferView holding POSITION + all 52 morph deltas
  at stride 8. Decode it once with `meshoptimizer`'s `MeshoptDecoder.decodeGltfBuffer`,
  then read `KHR_mesh_quantization` uint16 POSITION and int16 morph deltas out of the
  decoded bytes. The head node transform is pure translate + uniform scale (no rotation),
  so dequant is `model = T + S*rawU16`. Frontal plane is `(X, -Z)` (up = -Z). Only one
  small script-only devDependency; no gltf-transform, dequant done by hand.
- **Feature segmentation by blendshape (`scripts/faceOutline.ts`)**: each feature is the
  set of verts its ARKit morph moves (eyelids under `eyeBlink_L/R`, brows under
  `browDown`+`browOuterUp`, lips under `mouthClose` split by y). This is principled and
  excludes the back of the head for free. Order (angular loop for eyes, x-arc for
  brows/lips), downsample even, normalize to canonical `[-1,1]` with one uniform scale.
- **Attractors vs shading split**: attractors only *bias motion* into feature regions;
  the density grid *draws* the face. So the provider samples the rich curves down to a
  small 6-attractor budget (perf), while `presenceDensityField` uses every point.
- **Density grid (`presenceDensityField.ts`)**: bake a 64x64 distance + proximity grid
  once at startup; the form samples proximity **nearest-cell, inlined** per particle
  (bitwise round, one array read, no closure) and lifts the glyph weight. Gated by the
  sim's exposed effective `faceWeight` so sleeping stays pure dust.
- **paletteShift**: `writeSkinColors` biases the gradient endpoints data-side (no shader
  change), cross-fading with the row like every other column.
- **Debug outline**: 6 static polylines added to the presence frame. SVG auto-discovers
  polylines; the three renderer needs declared nodes, so `Presence.tsx` adds one node per
  curve. `ThreePolylineResource.draw` already honors `primitive.visible`, so the leva
  toggle works without per-line groupRefs.

## Performance notes

- 3b baseline ~3.5ms; naive per-particle bilinear `distanceAt` via a closure pushed min
  to ~4.1ms (over budget). Fixes, in order of impact: (1) bake a proximity grid and sample
  **nearest-cell inlined** (no closure) → min ~3.9ms; (2) trim the face attractor budget
  8→6 (the grid, not attractors, draws the face) → min ~3.4-3.6ms, filtered median
  3.64-3.83ms with comfortable margin even under warroom load (raw-p50 spiking to 6-9ms).
- The honest filtered-median gate (median of frames <= 2x fastest) from 3b held; reclaiming
  code-cost margin was the right fix, not loosening the gate.

## Deviations from spec

- **Toolchain**: had to pin `pnpm-workspace.yaml` catalog `vite-plus` from `latest` to
  `0.1.24`. `@voidzero-dev/vite-plus-test` has no 0.2.x, so core `latest` (0.2.2) leaves
  `vp test` unable to find the vitest bin. `catalog:latest` + a 0.1.24 lockfile was a latent
  bug that only worked while `latest == 0.1.24`; adding any devDependency surfaced it.
  Pinning to the version the lockfile already resolved is the only consistent toolchain.
- Attractor budget is 6 (not the capacity 16) for perf; the density grid carries legibility.

## Open items

- On-screen face legibility is unproven here by design (Stuart's live tuning session). No
  visual claims made; tests assert structure/bounds/monotonicity/determinism only.
- WebGL debug-outline pixel rendering is unverified in a headless build; the mechanism is
  sound (visible flag respected, toggle + frame structure tested) but should be eyeballed.
- Curve density / feature sizing / shading gain are constants with sensible defaults left
  for the tuning session.
