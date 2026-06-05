# F1 Piece Motion state transition audit

## Scope and count

The audited per State visual value is `State.pose`, owned by `src/domain/workbench.ts::State` and typed by `src/domain/scene.ts::Pose`. Vector components and repeated face or edge ids are grouped when they have identical transition behavior.

The complete Pose matrix contains 23 property families:

- 9 interpolate.
- 14 snap.
- 0 are omitted.

Five display properties are missed by interpolation and are the actionable tween gaps: face color, face opacity, edge color, edge opacity, and edge thickness. The remaining snaps are boolean modes, categorical scene or grid modes, coordinate identity, or frame compatibility state.

State metadata (`State.assetId`, `State.id`, and `State.name`) is excluded from the 23 because it identifies and labels a State rather than describing the rendered piece. `CubicellScene.score` is also excluded because `Pose` deliberately omits it and `src/domain/workbench.ts::getStateScene` derives the score from the owning structure.

## Root cause for face and edge color

The playback call chain is:

1. `src/evaluation/pieceAt.ts::samplePieceAt` resolves adjacent States and calls `sampleSceneTransition`.
2. `src/evaluation/sceneTransition.ts::sampleSceneTransition` selects the morph path and calls `prepareSceneMorph` plus `sampleSceneMorph`.
3. `src/evaluation/sceneMorph.ts::prepareSceneMorph` uses `isSameCubeCell`. That comparison includes every face and edge color, opacity, thickness, and visibility field. A color only edit therefore correctly classifies the cube as changed.
4. `src/evaluation/sceneMorph.ts::sampleSceneMorph` computes eased local cube progress and calls `interpolateCell` with `inkAfter = progress >= settings.cutAt`.
5. `src/evaluation/sceneMorph.ts::interpolateCell` chooses one whole endpoint as `ink` and spreads it into the result. It overrides only placement offset, rotation, scale, and size with interpolated values. The complete `faces` and `edges` records come from the selected endpoint, so face color and edge color switch as one discrete local cut. No color blend is calculated.

`CubePartColor`, owned by `src/domain/cube.ts::CubePartColor`, stores the categorical tokens `theme`, `black`, and `white`. `src/scene/cubeInstances.ts::createCubeCellInstances` forwards the selected token, and `src/scene/instancedPartMeshCore.ts::syncInstancedPartMesh` resolves it to a concrete Three color. The renderer updates the endpoint color but adds no interpolation.

This behavior predates the F1 Editor binding. `docs/superpowers/specs/2026-07-13-animation-wave1-design.md::Morph evaluation` specified “geometry glides, ink snaps,” and `docs/superpowers/plans/scene-morph/04-evaluation.md::Sampling contracts` specified that parts and visibility snap. `tests/sceneMorph.test.ts::sampleSceneMorph` codifies the same local cut behavior.

## Complete property matrix

| Per State property family | Status | Transition behavior | Owning model and transition symbol |
| --- | --- | --- | --- |
| Cell identity and membership, `Pose.cells[]` plus `CubeCell.id` | interpolated | Equal ids match. Added ids arrive through `Moment.presence`; removed ids depart through it. Added cell properties use B and removed cell properties use A while presence changes. | `src/domain/scene.ts::Pose`; `src/domain/cube.ts::CubeCell`; `src/evaluation/sceneMorph.ts::prepareSceneMorph`; `src/evaluation/sceneMorph.ts::sampleSceneMorph` |
| `CubeCell.placement.coord.{x,y,z}` | snapped | For a retained id with a changed coord, `interpolateCell` uses B's coord at the first positive local progress. Under the coordinate derived id contract, a normal coordinate move changes the id and uses depart plus arrive instead. | `src/domain/cube.ts::CubePlacement`; `src/evaluation/sceneMorph.ts::interpolateCell` |
| `CubeCell.placement.offset[0..2]` | interpolated | Componentwise numeric lerp at eased local cube progress. | `src/domain/cube.ts::CubePlacement`; `src/evaluation/sceneMorph.ts::interpolateCell`; `src/evaluation/sceneMorph.ts::lerpVec3` |
| `CubeCell.placement.rotation[0..2]` | interpolated | Componentwise numeric lerp at eased local cube progress. | `src/domain/cube.ts::CubePlacement`; `src/evaluation/sceneMorph.ts::interpolateCell`; `src/evaluation/sceneMorph.ts::lerpVec3` |
| `CubeCell.placement.scale[0..2]` | interpolated | Componentwise numeric lerp at eased local cube progress. | `src/domain/cube.ts::CubePlacement`; `src/evaluation/sceneMorph.ts::interpolateCell`; `src/evaluation/sceneMorph.ts::lerpVec3` |
| `CubeCell.size.{depth,height,width}` | interpolated | Each numeric dimension lerps at eased local cube progress. | `src/domain/cube.ts::CubeCell`; `src/evaluation/sceneMorph.ts::interpolateCell` |
| `CubeCell.visible` | snapped | Comes from A before the local cube cut and B at or after it through the endpoint `ink` spread. | `src/domain/cube.ts::CubeCell`; `src/evaluation/sceneMorph.ts::interpolateCell` |
| `CubeCell.edges[edgeId].color` | snapped | The whole edge record switches at the local cube cut. No resolved color blend exists. | `src/domain/cube.ts::CubeEdgeState`; `src/evaluation/sceneMorph.ts::interpolateCell` |
| `CubeCell.edges[edgeId].opacity` | snapped | Numeric opacity switches with the whole edge record at the local cube cut. | `src/domain/cube.ts::CubeEdgeState`; `src/evaluation/sceneMorph.ts::interpolateCell` |
| `CubeCell.edges[edgeId].thickness` | snapped | Numeric thickness switches with the whole edge record at the local cube cut. | `src/domain/cube.ts::CubeEdgeState`; `src/evaluation/sceneMorph.ts::interpolateCell` |
| `CubeCell.edges[edgeId].visible` | snapped | Boolean visibility switches with the whole edge record at the local cube cut. | `src/domain/cube.ts::CubeEdgeState`; `src/evaluation/sceneMorph.ts::interpolateCell` |
| `CubeCell.faces[faceId].color` | snapped | The whole face record switches at the local cube cut. No resolved color blend exists. | `src/domain/cube.ts::CubeFaceState`; `src/evaluation/sceneMorph.ts::interpolateCell` |
| `CubeCell.faces[faceId].opacity` | snapped | Numeric opacity switches with the whole face record at the local cube cut. | `src/domain/cube.ts::CubeFaceState`; `src/evaluation/sceneMorph.ts::interpolateCell` |
| `CubeCell.faces[faceId].visible` | snapped | Boolean visibility switches with the whole face record at the local cube cut. | `src/domain/cube.ts::CubeFaceState`; `src/evaluation/sceneMorph.ts::interpolateCell` |
| `Pose.grid.format.align` | snapped | Selects A or B at the global transition cut. | `src/domain/grid.ts::GridFormat`; `src/evaluation/sceneMorph.ts::interpolateGridState` |
| `Pose.grid.format.cellSize[0..2]` | interpolated | Componentwise numeric lerp at eased global glide progress. | `src/domain/grid.ts::GridFormat`; `src/evaluation/sceneMorph.ts::interpolateGridState`; `src/evaluation/sceneMorph.ts::lerpVec3` |
| `Pose.grid.format.gap[0..2]` | interpolated | Componentwise numeric lerp at eased global glide progress. | `src/domain/grid.ts::GridFormat`; `src/evaluation/sceneMorph.ts::interpolateGridState`; `src/evaluation/sceneMorph.ts::lerpVec3` |
| `Pose.grid.format.gapOverrides.{x,y,z}[interval]` | interpolated | Builds the union of interval keys and lerps effective gap widths, including fallback base gaps. | `src/domain/grid.ts::GridFormat`; `src/evaluation/sceneMorph.ts::interpolateGridState`; `src/domain/grid.ts::getGapWidth` |
| `Pose.grid.format.origin[0..2]` | interpolated | Componentwise numeric lerp at eased global glide progress. | `src/domain/grid.ts::GridFormat`; `src/evaluation/sceneMorph.ts::interpolateGridState`; `src/evaluation/sceneMorph.ts::lerpVec3` |
| `Pose.grid.format.overflow` | snapped | Selects A or B at the global transition cut. | `src/domain/grid.ts::GridFormat`; `src/evaluation/sceneMorph.ts::interpolateGridState` |
| `Pose.frameId` | snapped | In a morph frame it selects A or B at the global cut. Different nonempty frame ids make `resolveTransitionKind` cut the complete pose instead of morphing. | `src/domain/scene.ts::Pose`; `src/domain/stateTransition.ts::scenesAreMorphCompatible`; `src/domain/stateTransition.ts::resolveTransitionKind`; `src/evaluation/sceneMorph.ts::sampleSceneMorph` |
| `Pose.polarity` | snapped | Selects A or B at the global transition cut. | `src/domain/scene.ts::Pose`; `src/evaluation/sceneMorph.ts::sampleSceneMorph` |
| `Pose.projection` | snapped | Selects A or B at the global transition cut. `src/evaluation/pieceAt.ts::PieceFrame` also declares instant projection behavior. | `src/domain/scene.ts::Pose`; `src/evaluation/sceneMorph.ts::sampleSceneMorph`; `src/evaluation/pieceAt.ts::PieceFrame` |

## Missed and snapped properties

### Tween gaps, 5

These visual values have continuous rendered meaning or are explicitly reported as requiring a transition, but `interpolateCell` switches them with endpoint ink:

1. `CubeFaceState.color`
2. `CubeFaceState.opacity`
3. `CubeEdgeState.color`
4. `CubeEdgeState.opacity`
5. `CubeEdgeState.thickness`

### Other snaps, 9

1. `CubeCell.placement.coord`
2. `CubeCell.visible`
3. `CubeFaceState.visible`
4. `CubeEdgeState.visible`
5. `Pose.grid.format.align`
6. `Pose.grid.format.overflow`
7. `Pose.frameId`
8. `Pose.polarity`
9. `Pose.projection`

### Omitted Pose properties

None. `src/evaluation/sceneMorph.ts::isSameCubeCell` detects every `CubeCell` field. `interpolateCell` either interpolates an overridden geometry field or retains it through the selected endpoint spread. `interpolateGridState` covers every `GridFormat` field, and `sampleSceneMorph` supplies every remaining `Pose` field.

## Verification

- Focused evaluator run: `tests/sceneMorph.test.ts` and `tests/pieceMotionEvaluation.test.ts`, 23 tests passed.
- The renderer path was traced through `src/scene/cubeInstances.ts::createCubeCellInstances` and `src/scene/instancedPartMeshCore.ts::syncInstancedPartMesh`; no downstream color interpolation exists.
- The authorized baseline worktree difference is `M src/config/cubicellConfig.ts`, with the Editor Piece Motion workspace flag flip. The report workflow did not edit the worktree.
