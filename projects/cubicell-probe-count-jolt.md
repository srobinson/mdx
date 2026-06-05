# Probe — the 1→2 cube jolt, measured

Repo `main @ ae44cbf`. Throwaway vitest probe (deleted; `git status --porcelain` shows only the pre-existing untracked `THEORY.md`, nothing under `src/` or `tests/`). Real pipeline: `prepareSceneMorphTopology → prepareSceneMorphSchedule → sampleSceneMorph`, then per frame `createSceneGridLayout(frame.scene.grid, frame.scene.cells)` → `getMomentCells` → `applyMomentToLayout`, mirroring `useCubeSceneRenderState`. Defaults: `durationMs 1200`, grid `cellSize [1,1,1]`, `gap [0.5,0.5,0.5]` (step 1.5), `align "center"`.

## Setup 1: one cube → same cube + one +x neighbor (`addNeighborCubes`)

Default arrive (ease-out-quart, creation order, stagger 40ms):

| t (ms) | dims | pre-existing cube pos (x) | added cube presence | added cube scale |
|---|---|---|---|---|
| 0 | 1x1x1 | 0.0000 | — (not in frame) | — |
| 16 | 2x1x1 | **-0.7500** | 0.0523 | 0.0523 |
| 60 | 2x1x1 | -0.7500 | 0.1855 | 0.1855 |
| 300 | 2x1x1 | -0.7500 | 0.6836 | 0.6836 |
| 600 | 2x1x1 | -0.7500 | 0.9375 | 0.9375 |
| 1200 | 2x1x1 | -0.7500 | 1.0000 | 1.0000 |

Both cubes' y and z stay 0 throughout. The pre-existing cube is classed **retained** (coord unchanged), so no morph class ever touches it.

## Answers

**Q1. Does the pre-existing cube's position change between t=0 and the first frame?** Yes. It snaps **0.75 units on x** (half a grid step: extent grows 1→2 wide, step = cellSize 1 + gap 0.5 = 1.5, centering shifts by step/2) between t=0 and t=16ms, then never moves again. This is the jolt.

**Q2. Does the added cube's presence ramp?** Yes, correctly per `MorphSettings.arrive`: series 0.0523 → 0.1855 → 0.6836 → 0.9375 → 1.0000 (ease-out-quart), scale identical. Arrival is not the jolt.

**Q3. Does `getSceneGridDimensions` change discontinuously?** Yes, 1x1x1 → 2x1x1 between t=0 and t=16ms. But nothing in the layout consumes it (its consumers are display: `GridSection.tsx`, `GridComposer.tsx`). The layout discontinuity enters through `gridLayout.ts:getSceneGridAlignment` → `getAlignmentOffset(align: "center", baseHomes)`, which recomputes the centering offset over the sampled frame's FULL cell set — including presence-0 cells, since `useCubeSceneRenderState` builds `baseLayout` from `scene.cells` before staging. So the full-magnitude recentre lands on the first frame even though every added cube is still invisible.

**Q4. Does `endpointFrame`'s snap produce the discontinuity?** It defines where it lands but is not the cause. At t<=0 the frame scene is `plan.a` (1 cell); at any t>0 `sampleSceneMorph` emits `plan.b.cells` (2 cells). The alignment jump therefore happens across the t=0 → first-frame boundary, and would happen at the standing-scene → first-morph-frame boundary regardless of `endpointFrame`.

**Q5. 2 → 30 cubes (resize 2x1x1 → 5x3x2, originals retained by coord).** Both original cubes snap at t=16ms by the same delta: **[-2.25, -1.5, -0.75]** (magnitude ≈ 2.806 units): cube 1 [-0.75,0,0] → [-3,-1.5,-0.75], cube 2 [0.75,0,0] → [-1.5,-1.5,-0.75]. Same mechanism at larger extent growth; 28 of 30 sampled cells are presence 0 at that frame yet still drive the centering.

**Q6. Do arrive settings change Q1?** No. Re-run with `arrive: {easing: linear, order: axis-x, staggerMs: 300}`: pre-existing cube snap identical (0 → -0.75 on x at t=16ms; only the added cube's presence series changed, 0.0133 at 16ms). The jolt is structurally outside `MorphSettings`: retained cells belong to no morph class, and the shift originates in layout derivation, not in the morph sampler.

## Verdict

The jolt is the **pre-existing cube snapping half the extent growth per axis at the first morph frame**, caused by `align: "center"` recentring `createSceneGridLayout` over the endpoint-B cell set (presence-0 cells included). Presence/arrive machinery works exactly as designed and cannot fix it, matching the user report that no arrive setting helps.
