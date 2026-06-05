# F1 ink tween Scout and Plan

## Decision summary

All five changed ink values must use the same eased and quantized local cube progress as geometry:

1. Face color
2. Face opacity
3. Edge color
4. Edge opacity
5. Edge thickness

Recommendation: interpolate the three numeric values in the pure evaluator, carry endpoint color tokens plus already eased progress in a transient `Moment` part overlay, and resolve plus blend colors in the instanced renderer. This keeps `CubePartColor` categorical and persisted, keeps theme and Three dependencies out of evaluation, and follows the documented `Moment` extension boundary in `ANIMATION.md::Moment` and `docs/superpowers/specs/2026-07-13-animation-wave1-design.md::Moment extension`.

No implementation was performed.

## Reuse map

| Required capability | Existing owner | Reuse decision and evidence |
| --- | --- | --- |
| Scalar numeric interpolation | `src/shared/math.ts::lerp` | Reuse directly for face opacity, edge opacity, and edge thickness. It is already used by scene, camera, and interaction evaluators. No property specific scalar interpolation helper exists. |
| Vector interpolation | `src/evaluation/sceneMorph.ts::lerpVec3` | Keep for offset, rotation, scale, grid cell size, gap, and origin. It delegates every component to the shared scalar `lerp`. `src/evaluation/cameraTrack.ts::lerpVector` returns a Three `Vector3`, so it does not replace this dependency free `Vec3` helper. |
| Raw local cube progress | `src/evaluation/sceneMorph.ts::classProgress` | Reuse unchanged. It applies each changed cube's stagger and cell duration. |
| Easing and quantization | `src/evaluation/sceneMorph.ts::sampleSceneMorph`, `src/evaluation/scoreAt.ts::easingFor`, and `src/evaluation/scoreAt.ts::quantizeProgress` | Reuse the exact value currently passed to `interpolateCell`. This makes all five ink values follow geometry easing and stop motion quantization. Do not recompute progress in the renderer. |
| Discrete cut selection | `src/evaluation/sceneMorph.ts::sampleSceneMorph` and `src/domain/morphSettings.ts::MorphSettings.cutAt` | Retain only for boolean visibility and the existing discrete scene or grid modes. `sampleSceneMorph` compares raw local progress with `cutAt`, while geometry receives eased and quantized progress. |
| Changed cube detection | `src/evaluation/sceneMorph.ts::isSameCubeCell` | Reuse unchanged. It already compares face color and opacity, edge color, opacity, thickness, and every visibility flag. Color only edits already enter the changed class. |
| Edge and face enumeration | `src/domain/cubeTopology.ts::cubeEdgeIds` and `src/domain/cubeTopology.ts::cubeFaceIds` | Reuse for deterministic traversal of all 12 edges and 6 faces. |
| Edge and face record mapping | `src/domain/cube.ts::mapCubeEdges` and `src/domain/cube.ts::mapCubeFaces` | Exact capability exists but is private. Promote and reexport these owners instead of adding duplicate `Object.fromEntries` loops in `sceneMorph`. Existing `cloneCubeEdges`, `cloneCubeFaces`, `setAllCubeEdgesState`, and `setAllCubeFacesState` already depend on them. |
| State color token model | `src/domain/cube.ts::CubePartColor` | Preserve the categorical `theme | black | white` authoring and persistence contract. Do not widen it with transient RGB values or tween descriptors. |
| Token to concrete color resolution | `src/theme/scenePolarity.ts::resolveCubePartColor` | Reuse in the renderer for both tween endpoints. It owns polarity dependent token resolution. |
| Current per instance color upload | `src/scene/instancedPartMeshCore.ts::syncInstancedPartMesh` | Reuse as the sole color blend call site. It already owns a reusable Three `Color` scratch value and calls `InstancedMesh.setColorAt` for every part. |
| Existing concrete color interpolation | `src/scene/FloorGridChrome.tsx::FloorGridChrome` | Prior art only. It calls Three `Color.lerp` directly for grid chrome. No reusable project helper exists, and its concrete workbench colors do not solve token resolution. |
| Transient, already eased render overlay | `src/evaluation/scoreAt.ts::Moment` | Extend this existing seam with sparse per part color tween descriptors. `Moment` is explicitly pure, derived, transient, and consumed by the instancing layer. The Wave 1 design already names per cell part overrides as its intended extension. |
| Moment composition | `src/evaluation/scoreAt.ts::composeMoments` | Extend deliberately. It currently reconstructs only `presence`, so a color overlay would otherwise disappear when `samplePieceAt` composes morph and assembly Moments. |
| Evaluator to stage transport | `src/evaluation/sceneTransition.ts::SceneTransitionFrame`, `src/evaluation/pieceAt.ts::PieceFrame`, and `src/transport/useStagedScene.ts::StagedScene` | Reuse the existing `moment` field. No parallel color transport object is needed. |
| Stage to instance derivation | `src/scene/CubeScene.tsx::CubeScene`, `src/scene/useCubeSceneInstances.ts::useCubeSceneInstances`, and `src/scene/cubeInstances.ts::createCubeCellInstances` | Thread the sparse color overlay through this path. Add the per cell overlay reference to the instance cache identity so time changes cannot reuse stale colors. |
| Focused evaluator tests | `tests/sceneMorph.test.ts::sampleSceneMorph` | Extend the existing linear, cut, quantize, and endpoint fixtures. |
| Piece composition tests | `tests/pieceMotionEvaluation.test.ts::composeMoments` and `tests/pieceMotionEvaluation.test.ts::samplePieceAt` | Prove the color overlay survives assembly Moment composition. |
| Instance and color upload tests | `tests/instances.test.ts::syncInstancedPartMesh` | Add direct face and edge midpoint color assertions through `InstancedMesh.getColorAt`, plus numeric opacity and thickness derivation assertions. |

### Searches run

- Scalar and vector helpers: `rg "function (lerp|lerpVec3)|const .*lerp|\\blerp\\(" src tests`.
- Color interpolation: `rg "lerpColors|lerpHSL|\\.lerp\\(|interpolate.*color|color.*interpolate|color-mix|new Color" src tests`.
- Token owners and consumers: `rg "CubePartColor|resolveCubePartColor|ScenePolarityConfig|partColors" src tests`.
- Part mapping reuse: `rg "mapCubeEdges|mapCubeFaces|cloneCubeEdges|cloneCubeFaces|cubeEdgeIds.map|cubeFaceIds.map|Object.fromEntries" src tests`.
- Transient overlay transport: `rg "Moment|presence|composeMoments|getMomentCells|applyMomentToLayout" src tests ANIMATION.md`.
- Cell equality reuse: `rg "isSameCubeCell|areCube.*Equal|isCube.*Equal|CubeCell.*equal" src tests`.

Results: `src/shared/math.ts::lerp` is the only reusable scalar helper. No reusable color interpolation function exists. The only JavaScript color blend is the local Three `Color.lerp` use in `FloorGridChrome`; CSS `color-mix` declarations do not apply to instanced Three colors.

## Quality map

| Severity | Finding | Evidence and consequence | Plan response |
| --- | --- | --- | --- |
| High | The evaluator cannot resolve `CubePartColor` correctly without view context. | `theme` resolves through `ScenePolarityConfig`, and `src/app/App.tsx::App` chooses either artifact or workbench palettes. Importing theme or Three into `sceneMorph` would break the pure evaluator boundary. Passing a resolver into every sample call would make preparation and sampling theme dependent. | Keep endpoint tokens in `Moment`; resolve and blend in `syncInstancedPartMesh`. |
| High | `composeMoments` drops every future Moment field. | When two Moments are present it returns a new object containing only multiplied `presence`. Piece Motion always composes morph presence with assembly presence. | Preserve the one color overlay through composition and add an explicit contract test. Define conflict behavior before two color bearing Moments can coexist. |
| High | The instance cache has no transient ink dependency. | `useCubeSceneInstances` reuses a cell's instances from cell, layout, occupancy, edge segments, and selection. A renderer only color tween can change while the selected endpoint `CubeCell` color remains stable. | Include the per cell color overlay reference in `CellInstancesCacheEntry` and its reuse predicate. |
| Medium | `interpolateCell` couples every non geometry field to one endpoint spread. | `const ink = inkAfter ? after : before` makes color, numeric ink, and visibility share cut semantics. Adding isolated overrides without restructuring would be brittle. | Rename `progress` to `glideProgress`, rename `inkAfter` to `afterCut`, rename `ink` to `discrete`, and explicitly rebuild edge and face records. |
| Medium | The color token type is duplicated. | `src/domain/cube.ts::CubePartColor` and `src/theme/scenePolarity.ts::CubePartColorName` declare the same union independently. A new color seam would increase the chance of drift. | Delete `CubePartColorName` and type `resolveCubePartColor` with the domain owner. |
| Medium | Canonical part mappers are private. | `mapCubeEdges` and `mapCubeFaces` already own full record traversal, but evaluation cannot reuse them through the public Domain contract. | Promote and explicitly reexport them. Do not create new traversal helpers. |
| Medium | Equality logic is duplicated across subsystems. | `sceneMorph::isSameCubeCell` repeats face, edge, and size comparisons also held privately in `selectionAspects::areEdgeStatesEqual`, `areFaceStatesEqual`, and `areSizesEqual`. | Do not add another comparator. The tween slice does not need to change equality. Consolidation can be a separate bounded refactor because selection tolerance semantics widen its risk. |
| Medium | The old naming and tests encode a superseded design. | `interpolateCell` says it selects parts, `tests/sceneMorph.test.ts` says parts snap, and the Wave 1 design says “ink snaps.” Stuart has overturned that rule. | Split the test into numeric ink interpolation and visibility cut tests. Update active comments and the current behavior document. Preserve historical superseded plans as history. |
| Low | A naive color helper may allocate one or more `Color` objects per part per frame. | `syncInstancedPartMesh` currently reuses one scratch `Color`. | Give the seam a caller supplied target. Fable's note decides the internal color space and Three API while retaining the no allocation interface. |

No active dead code was found in the transition or color upload path. `cutAt` remains live for visibility and discrete modes. `resolveCubePartColor` remains the token resolution owner. The unrelated helpers marked `unwired` in `src/domain/cube.ts` are outside this change and should not be pulled into it.

## Color seam

### Recommended transient descriptor

```ts
export type PartColorTween = Readonly<{
  from: CubePartColor
  progress: number
  to: CubePartColor
}>

export type CubePartColorTweens = Readonly<{
  edges: ReadonlyMap<CubeEdgeId, PartColorTween>
  faces: ReadonlyMap<CubeFaceId, PartColorTween>
}>

export type Moment = {
  partColors?: ReadonlyMap<string, CubePartColorTweens>
  presence: ReadonlyMap<string, number>
}
```

`sampleSceneMorph` emits entries only for retained, changed cubes and only for parts whose endpoint tokens differ. `progress` is the same eased and quantized local value passed to `interpolateCell`. Added and removed cells keep their current presence animation and do not invent cross endpoint part matches.

### Recommended renderer interface

```ts
export function resolveInterpolatedCubePartColor(
  target: Color,
  from: CubePartColor,
  to: CubePartColor,
  progress: number,
  polarity: ScenePolarityConfig,
): Color
```

Owner: a small scene level module beside `src/scene/instancedPartMeshCore.ts`, or `instancedPartMeshCore` itself if the implementation remains one function.

Call site: `src/scene/instancedPartMeshCore.ts::syncInstancedPartMesh`, for face and edge instances carrying `colorTween`. Stable parts continue through `resolveCubePartColor`. Neighbor slots carry no tween. Picking only edge hit targets do not need blended visual colors.

The function resolves both endpoint tokens through `resolveCubePartColor`, writes the selected interpolation into `target`, and returns `target`. Fable's design note owns the internal color space, interpolation method, and exact Three API. This plan does not choose them.

## Structural fork

| Choice | Reuse | Boundary and blast radius | Assessment |
| --- | --- | --- | --- |
| Resolve and interpolate color in evaluation | Reuses `lerp` and could call `resolveCubePartColor` only by importing Theme or receiving a resolver callback. | Couples `prepareSceneMorph` or `sampleSceneMorph` to workbench versus artifact palette choice, polarity configuration, and possibly Three `Color`. A resolved transient color would require widening `CubeFaceState.color` and `CubeEdgeState.color`, splitting transient cells from persisted cells, or adding another scene field. Every headless evaluator call and cache key would gain view context. | Reject. The shorter apparent call path damages Domain, Evaluation, persistence, and testing boundaries. |
| Carry token pairs and blend in renderer | Reuses `Moment`, `resolveCubePartColor`, per instance colors, and `syncInstancedPartMesh`. | Adds a sparse Moment field, composition preservation, one renderer transport parameter, one cache dependency, optional instance metadata, and focused tests. Persisted `CubePartColor` and `CubicellScene` remain unchanged. | Recommend. More explicit wiring, smaller semantic blast radius, correct palette ownership, and direct alignment with the documented Moment extension. |

Renderer ownership means the evaluator still owns time. It emits endpoint tokens and already eased progress. The renderer owns token resolution and color interpolation only.

## Ordered implementation plan

1. **Lock the transition contract.** In `sceneMorph::sampleSceneMorph`, retain raw local progress solely for `afterCut`. Continue passing eased and quantized progress to geometry and all five ink tweens. Keep forced and incompatible transitions as whole scene cuts. Keep added and removed cells on presence animation.

2. **Consolidate existing owners before new code.** Replace `CubePartColorName` with `CubePartColor` in `theme::resolveCubePartColor`. Promote `cube::mapCubeEdges` and `cube::mapCubeFaces` through `domain/index.ts`. Add no second scalar lerp, color token type, or part traversal helper.

3. **Tween the three numeric ink fields in `interpolateCell`.** Rename its arguments to distinguish `glideProgress` from `afterCut`. Keep `discrete = afterCut ? after : before` for boolean visibility and color token fallback. Rebuild `edges` with `mapCubeEdges`, retaining each discrete edge's `color` and `visible` while setting `opacity = lerp(before.opacity, after.opacity, glideProgress)` and `thickness = lerp(before.thickness, after.thickness, glideProgress)`. Rebuild `faces` with `mapCubeFaces`, retaining discrete `color` and `visible` while setting interpolated opacity.

4. **Emit sparse color tween metadata.** Extend `scoreAt::Moment` with `partColors`. In `sceneMorph::sampleSceneMorph`, collect per face and per edge token pairs for retained changed cubes. Use the same `glideProgress` as `interpolateCell`. Exact start and terminal frames continue returning A and B with no required overlay.

5. **Preserve the overlay through piece composition.** Update `scoreAt::composeMoments` so the single morph color overlay survives multiplication with the assembly Moment. Add and document the temporary invariant that at most one composed Moment owns a given part color tween until PropertyTrack composition defines precedence.

6. **Thread the overlay through existing stage rendering.** Keep `SceneTransitionFrame`, `PieceFrame`, and `StagedScene` on their current `moment` field. Pass `moment.partColors` from `CubeScene` into `useCubeSceneInstances`, then the matching per cell entry into `createCubeCellInstances`. Store that entry in `CellInstancesCacheEntry` and compare its reference before reusing instances.

7. **Attach optional tween metadata to rendered parts.** Add `colorTween?: PartColorTween` to the transient face and edge instance contract in `cubeInstances`. Apply it to visible, translucent, and ghost face or edge instances. Leave authored `CubeCell` and `CubePartColor` unchanged.

8. **Implement the renderer seam after Fable's color note.** Add `resolveInterpolatedCubePartColor` with the signature above. Call it only from `syncInstancedPartMesh` when `colorTween` exists. Retain the current scratch `Color` allocation pattern. The chosen color space and Three method come from Fable.

9. **Repair superseded contracts.** Update the active scene morph comment and test names to say numeric ink and color tween while visibility snaps. Update the current behavior document that governs Scene Morph. Do not rewrite superseded implementation history as current architecture.

## Decisions needed

1. **Evaluator or renderer color ownership.** Recommend renderer, using an already eased `Moment` overlay. This is the only blocking structural decision.
2. **Polarity interaction.** The current contract snaps `Pose.polarity` at the global cut. Recommend resolving both part color tokens against the current snapped `ScenePolarityConfig`, so this change overturns ink snapping only. If polarity itself must color tween, the descriptor and renderer seam need both endpoint polarity contexts, which is a separate wider decision.
3. **Visibility interaction.** Recommend retaining `CubeCell.visible`, face visibility, and edge visibility at the existing local cut. Numeric and color values continue tweening in the overlay even while a part is hidden; visibility decides when the result can be seen.
4. **Multiple color bearing Moments.** Current Piece Motion has one morph color owner and one presence only assembly owner. Recommend preserving the single color overlay now and deferring multi owner precedence until PropertyTrack exists. The contract must be explicit so `composeMoments` cannot silently discard or overwrite future color data.
5. **Color math.** Deferred to Fable by instruction. The seam requires only deterministic endpoint exactness, stable monotonic progress handling, and no per part allocation.

## Tests and gates

### Focused tests

1. `tests/sceneMorph.test.ts::sampleSceneMorph`
   - Linear quarter, midpoint, and three quarter assertions for face opacity, edge opacity, and edge thickness.
   - Separate per face and per edge color descriptors with exact endpoint tokens and eased progress.
   - A color only change proves `isSameCubeCell` still enters the glide class.
   - Quantized glide proves color and numeric ink use the same stepped progress as geometry.
   - Visibility remains before the cut and after it at the existing boundary.
   - Time zero returns exact A; terminal time returns exact B.

2. `tests/pieceMotionEvaluation.test.ts::composeMoments` and `samplePieceAt`
   - Morph color metadata survives assembly presence composition.
   - Presence still multiplies exactly as before.
   - A forced cut emits no morph color tween and returns endpoint ink.

3. `tests/stagedScene.test.ts::sampleStageSource`
   - Both Piece transport and comparison scrub expose the same color overlay through `StagedScene.moment`.

4. `tests/instances.test.ts::createCubeCellInstances` and `syncInstancedPartMesh`
   - Face and edge instances receive their matching sparse tween descriptor.
   - `InstancedMesh.getColorAt` proves exact start, selected midpoint, and exact end colors under the Fable approved math.
   - Theme, black, and white token pairs resolve through both workbench polarities.
   - Midpoint face and edge opacity select the correct translucent bucket.
   - Midpoint edge thickness produces the expected edge instance matrix.

5. A focused hook or renderer test for `useCubeSceneInstances`
   - A new progress overlay invalidates the cached face and edge instances even when the staged `CubeCell.color` token remains the same endpoint value.
   - Stable overlays retain cache reuse.

### Repository gates

- Run the focused Vitest files without cache.
- Run the full `pnpm test` suite.
- Run `pnpm lint`.
- Run `pnpm build`, which exercises the repository's real `tsc -b` type gate.
- Run `git diff --check`.
- Recheck touched file sizes against the 700 line hard limit. `CubeScene.tsx` is currently below the threshold; keep its change to one transport seam rather than placing color logic there.
- Search for stale “ink snaps” and “parts snap” assertions or comments and reconcile current behavior owners.

### Live gate

Use the actual `cubicell-f1` worktree on a unique verified port. Build a two State piece where one retained cube changes all five ink properties. Scrub slowly and play through the transition. Confirm continuous face and edge color, opacity, and thickness; confirm visibility still cuts; confirm explicit cut mode still cuts; confirm comparison scrub and Piece transport match. Preserve the scene for Stuart's direct UX pass.

## Worktree integrity

The authorized baseline remains one intentional modification: `M src/config/cubicellConfig.ts`, setting `editorPieceMotionWorkspaceEnabled` to true. No worktree file was edited during this Scout and Plan.
