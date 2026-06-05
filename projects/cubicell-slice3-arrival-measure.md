# Cubicell arrival and departure measurement

Evaluated branch: `slice/transition-panel` at `2b7188d5`.

## Finding

Arrival and departure use a narrower presence path. The evaluator already samples offset, rotation, authored scale, size, colour ink, numeric ink, and shared physical edge colour for retained cubes. Arriving and departing cubes bypass that sampler. An arrival therefore cannot currently slide, rotate, or drop through those channels. It uses the complete destination cell at a fixed destination pose and presence scales that pose from zero. A departure uses the complete source cell at a fixed source pose while presence scales it to zero. [P1]

## Evidence

P1 was a temporary Node Vitest probe under `/tmp`, run with:

```text
pnpm exec vitest run --config /tmp/cubicell-arrival-probe.config.mjs --reporter verbose
```

Four tests passed. The probe measured the render matrices at presence `0.5`, sampled all retained channels at transition midpoint, compared arriving and departing cell identity against their endpoints, and measured a shared physical edge tween on both retained claimant members. The probe and its configuration were deleted after the report was written.

P2 was the existing focused unit suite:

```text
pnpm exec vitest run tests/sceneMorph.test.ts tests/pieceMotionEvaluation.test.ts --project unit --reporter dot
```

Result: 2 files passed, 38 tests passed.

No browser was used.

## 1. What presence drives

### Ownership chain

For a State transition, `src/evaluation/sceneMorph.ts:sampleSceneMorph` evaluates class progress and writes the eased, quantized value into `src/evaluation/scoreAt.ts:Moment.presence`. Arrival writes progress. Departure writes `1 - progress`, clamped to the presence range. Assembly uses the same Moment contract through `src/evaluation/scoreAt.ts:scoreAt` and `src/evaluation/scoreAt.ts:applyAssemblyTrack`. [P1, P2]

`src/transport/stagedScene.ts:sampleStageSource` carries the scene and Moment to `src/studios/editor/EditorStudio.tsx:EditorStudio`, which passes both into the renderer. `src/scene/CubeScene.tsx:CubeScene` delegates staging to `src/scene/useCubeSceneRenderState.ts:useCubeSceneRenderState`.

Two symbols consume presence there:

1. `src/evaluation/scoreAt.ts:getMomentCells` removes cells whose presence is zero or below. That staged cell list owns downstream instances, hit targets, selection chrome inputs, and neighbour slot derivation. P1 measured one cell at presence `0.5` and zero cells at presence `0`. P2 covers endpoint and midpoint staging.
2. `src/evaluation/scoreAt.ts:applyMomentToLayout` multiplies each component of `CubeLayoutPose.scale` by presence. It leaves `homePosition`, `renderPosition`, and rotation unchanged. `src/scene/cubeInstances.ts:createCubeCellInstances` then composes that pose through `src/shared/three.ts:createTransformMatrix`, multiplies it into each face and edge matrix, and `src/scene/instancedPartMeshCore.ts:writeMatrix` writes the result to the Three instance. [P1]

Presence feeds no opacity or colour input. `src/scene/cubeInstances.ts:createCubeCellInstances` obtains face and edge display opacity from their cell states. `src/scene/instancedPartMeshCore.ts:writeOpacity` writes that independent value. Colour comes from cell ink or `Moment.partColors` through `src/scene/colorSpace.ts:resolvePartColor`. [P1]

Presence also leaves authored `CubeCell.size` unchanged. The parent transform scales the resulting geometry in world space, so the visible cube becomes smaller even though its authored size value does not change. [P1]

### Measured value at presence 0.5

For an isolated default cube, P1 produced:

| Value | Measured result |
|---|---|
| Layout scale | `[0.5, 0.5, 0.5]` |
| Render position | `[0, 0, 0]`, unchanged |
| Rotation | `[0, 0, 0]`, unchanged |
| Front face centre | `z = 0.25`, half of the authored `0.5` offset |
| X edge world dimensions | `0.507 × 0.007 × 0.007`, half of `1.014 × 0.014 × 0.014` |
| Face colour and opacity | `theme`, `1`, unchanged |
| Edge colour and opacity | `theme`, `1`, unchanged |
| Cell admission | Present at `0.5`; removed at `0` |

Thus presence `0.5` produces a uniform half scale about the cube origin. It also halves face offsets, edge offsets, edge thickness, and all other geometry carried by the parent matrix. It does not fade ink or modify authored size. [P1]

## 2. Continuously sampled per cube channels

`src/evaluation/sceneMorph.ts:prepareSceneMorphTopology` classifies only cells present at both endpoints as changed cells. `src/evaluation/sceneMorph.ts:sampleSceneMorph` sends those cells to `src/evaluation/sceneMorph.ts:interpolateCell`. Its arrival branch returns the destination cell before that call. Removed cells are appended later from the source endpoint. [P1]

| Channel | Owning sampling symbol | Exact sampled members | Arriving cube | Departing cube |
|---|---|---|---|---|
| Offset | `src/evaluation/sceneMorph.ts:interpolateCell` | `CubeCell.placement.offset`, component lerp | Fixed destination value | Fixed source value |
| Rotation | `src/evaluation/sceneMorph.ts:interpolateCell` | `CubeCell.placement.rotation`, component lerp | Fixed destination value | Fixed source value |
| Authored scale | `src/evaluation/sceneMorph.ts:interpolateCell` | `CubeCell.placement.scale`, component lerp | Fixed destination value, then multiplied by presence | Fixed source value, then multiplied by presence |
| Size | `src/evaluation/sceneMorph.ts:interpolateCell` | `width`, `height`, `depth`, scalar lerp | Fixed destination value | Fixed source value |
| Face colour ink | `src/evaluation/sceneMorph.ts:createPartColorTweens` and `src/evaluation/sceneMorph.ts:collectPartColorTweens` | One `PartColorTween` per changed face | No tween | No tween |
| Edge colour ink | `src/evaluation/sceneMorph.ts:createPartColorTweens` and `src/evaluation/sceneMorph.ts:collectPartColorTweens` | One `PartColorTween` per changed nonshared edge | No tween | No tween |
| Face numeric ink | `src/evaluation/sceneMorph.ts:interpolateCell` | Face opacity, bounded scalar lerp | Fixed destination value | Fixed source value |
| Edge numeric ink | `src/domain/cubeEdgeState.ts:cubeEdgeStateOwner.interpolateMorph`, called by `src/evaluation/sceneMorph.ts:interpolateCell` | Edge opacity and thickness, bounded scalar lerp | Fixed destination values | Fixed source values |
| Shared physical edge colour | `src/evaluation/sharedEdgeTweens.ts:planSharedEdgeTweens` and `src/evaluation/sceneMorph.ts:sharedWindowProgress` | The same `PartColorTween` on every member of a coincident claimant group retained at both endpoints | No tween | No tween |

P1 measured the retained midpoint exactly: offset `[1, 2, 3]`, rotation `[0.1, 0.2, 0.3]`, authored scale `[1.5, 2, 2.5]`, size `{ width: 2, height: 3, depth: 4 }`, face opacity `0.6`, edge opacity `0.7`, edge thickness `0.024`, and face and edge colour tween progress `0.5`. The same probe found the arriving cell reference equal to the destination cell, the departing reference equal to the source cell, and no `partColors` entry for either. [P1]

The shared edge probe changed the two retained claimant colours from white to black. Both claimant members received `{ from: "white", progress: 0.5, to: "black" }`. `src/evaluation/sharedEdgeTweens.ts:planSharedEdgeTweens` matches groups by complete member identity, so a group whose topology gains or loses an arriving or departing member cannot enter this retained group path. [P1]

Cube visibility, face visibility, edge visibility, coordinate selection, frame, polarity, projection, grid alignment mode, and grid overflow mode are discrete selections. Grid cell size, gap, gap overrides, origin, and arrangement offset are continuous scene level channels in `src/evaluation/sceneMorph.ts:interpolateGridState` and `src/evaluation/sceneMorph.ts:sampleSceneMorph`. They are outside the per cube list above.

## 3. Can arrival already slide, rotate, or drop

No. Arrival bypasses the existing retained cube interpolation machinery. [P1]

At each intermediate arrival sample, `src/evaluation/sceneMorph.ts:sampleSceneMorph` reads the destination cell from `plan.b.cells`, writes only its presence value, and returns that destination cell unchanged. It never calls `src/evaluation/sceneMorph.ts:interpolateCell` for that id. The renderer therefore sees the final offset, final rotation, final authored scale, final size, and final ink throughout the arrival. Only `src/evaluation/scoreAt.ts:applyMomentToLayout` changes with time, by multiplying final authored scale by presence. [P1]

The codebase contains samplers capable of expressing translation, rotation, scale, size, and ink motion for retained cubes. Arrival has no source value for those samplers and carries no arrival specific pose overlay. The machinery is therefore present elsewhere in the morph evaluator and unused by the narrower arrival path. A directional slide, drop, or rotation would require arrival to supply a time varying pose channel or participate in a generalized interpolation path. This report makes no design recommendation.

## 4. Departure

Departure has the same presence only visible behaviour as arrival, with the direction reversed. The source cell remains fixed while presence falls from `1` to `0`. At `0.5`, P1 measured the exact source cell reference, presence `0.5`, and no colour tween metadata. Its renderer path is the same scale multiplication and zero presence culling described above. [P1]

The implementation path is separate. Arrival is handled inside the `plan.b.cells.map` branch in `src/evaluation/sceneMorph.ts:sampleSceneMorph`. Departure is handled by a later loop over `plan.removedCells`, then those source cells are appended to the intermediate scene. Both paths bypass `src/evaluation/sceneMorph.ts:interpolateCell`. Their class schedules, easing, ordering, staggering, and quantization are independently authored through `settings.arrive` and `settings.depart`. [P1, P2]

Answer: departure is behaviourally symmetric at the form channel, while its evaluator branch and class schedule are separate.
