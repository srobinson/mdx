# Scout A — Cell identity, presence, and grid size (transitions design)

Repo: `/Users/alphab/Dev/LLM/DEV/helioy/cubicell`, branch `main @ ae44cbf`. Read-only audit for the cube-count / grid-size transition design.

## Reuse Map

### 1. What identifies a cell across states

Identity is `CubeCell.id`, a durable id minted by `src/domain/identity.ts:createDurableId`. It is NOT positional.

- The morph matcher is `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology`: it builds `cellsA` / `cellsB` maps keyed by `cell.id` and classifies `addedCells` (id in B only), `removedCells` (id in A only), `changedCells` (same id, different content). Coord is just another compared property of a retained cell.
- Ids are stable across authored states because each state stores an immutable snapshot of the working pose lineage: `src/domain/workbench.ts:State` carries `pose: PoseRevision` (`src/domain/project.ts:PoseRevision` = `Pose & {assetId, id, stateId}`), captured by `src/domain/structureOperations.ts:captureState` from `workbench.workingPose`.
- A grid resize preserves identity by coordinate: `src/domain/scene.ts:resizeGridSceneWithResult` matches existing cells by normalized coord and reuses the cell object (same id); only newly added territory gets fresh ids from `src/domain/scene.ts:createGridResizePlan`.

Searches: `rg "CubeCell"`, `rg "createDurableId"`, read of `sceneMorph.ts`, `scene.ts`, `workbench.ts`, `project.ts`.

### 2. What happens today to a cell present in only one endpoint

It never pops and never errors; it scales in or out through `Moment.presence`.

- `sceneMorph.ts:sampleSceneMorph`: added cells are emitted from `plan.b.cells` with `presence = arriveEase(classProgress)` over a staggered window planned by `sceneMorph.ts:planClassMotion` from `MorphSettings.arrive`; removed cells are appended to the sampled scene (`[...cells, ...plan.removedCells]`) with `presence = 1 - departEase(progress)` from `MorphSettings.depart`. `sceneMorph.ts:endpointFrame` snaps presence to exactly 0/1 at t<=0 and t>=duration.
- The presence consumers are `src/evaluation/scoreAt.ts:getMomentCells` (presence <= 0 filters the cell out of every downstream derivation: instances, hit targets, chrome, neighbor slots) and `scoreAt.ts:applyMomentToLayout` (pose scale multiplied by presence). Composition site: `src/scene/useCubeSceneRenderState.ts:useCubeSceneRenderState`.
- Viewer experience: an added cell grows from scale 0 at its destination coord on its staggered start; a removed cell shrinks to scale 0 in place. Stagger order comes from `src/domain/assemblyOrder.ts:generateAssemblyOrder` with `resolveOrderOrigin`.

### 3. Where grid size lives

Two different things, with different owners:

- Grid FORMAT (cellSize, gap, gapOverrides, origin, align, overflow) is `CubicellScene.grid: GridState` (`src/domain/grid.ts:GridState`), per scene and therefore per state (each `State.pose` carries its own `grid`). The morph already interpolates it: `sceneMorph.ts:interpolateGridState`.
- Grid DIMENSIONS (cube count per axis) are not stored anywhere. They are derived from the occupied cell extent by `src/domain/scene.ts:getSceneGridDimensions` over `getCellCoordBounds`. "Grid size" IS the cell set.
- Writers that change the cell set: `scene.ts:resizeGridSceneWithResult` (+ `applyGridPreset`, `applyGridPresetWithResult`, plan minted by `createGridResizePlan`), `src/domain/neighbors.ts:addNeighborCubes`, `src/domain/neighbors.ts:removeCubesById`, and `placeCubesAt` via `src/domain/cubeOperations.ts`.
- Cross-state guard that already exists: a resize mints a new `frameId` (`createGridResizePlan`), and `src/domain/workbench.ts:GridLock {frameId}` on `StructureAsset.gridLock` pins captures: `src/domain/structureOperations.ts:captureAllowed` refuses to capture a state whose pose `frameId` differs from the lock, and `setGridLock` only engages when every existing state pose matches. `documentRestoreOperations.ts:poseMatchesGridLock` enforces the same on restore.

### 4. Shape of the cube-count control in the domain

Both operations exist:

- Resize: `src/components/grid-composer/GridComposer.tsx` -> `createGridResizePlan(dimensions)` -> `resizeGridScene` / `applyGridPreset` (crop or extend, identity retained by coord, holes stay empty).
- Add/remove: shadow neighbor slots (`useCubeSceneRenderState.ts` via `getSceneShadowShell` / `getCubeNeighborSlots`) -> `src/app/useSceneOperations.ts:addNeighborAtSlot` and `addNeighborToSelectedFaces` -> `neighbors.ts:addNeighborCubes`; removal via `neighbors.ts:removeCubesById`.

### 5. Precedent: camera route path

CONFIRMED with a location correction: `PoseSegment.arc: CameraOrbitArc {normal, sweepRadians}` lives in `src/domain/cameraTrack.ts` (`CameraOrbitArc`, `PoseSegment`), not in `pieceCameraTrack.ts`.

- Storage and keying: the path rides on the DEPARTING keyframe. `cameraTrack.ts:CameraKeyframe.outgoing: CameraSegment {pose: PoseSegment, projection: ProjectionSegment}`; keyed purely by adjacency in `CameraTrack.keyframes`. This mirrors cell transitions exactly: `src/domain/score.ts:StateTransitionTrack` holds parallel arrays `keyframes` and `transitions`, where `transitions[i]` routes `keyframes[i] -> keyframes[i+1]` (see `src/domain/stateTransition.ts:getStateTransitionSegmentMs` and its use in `pieceCameraTrack.ts:buildLandmarks` as `to.sequenceIndex - 1`).
- Authoring/repair pattern worth copying for cell routes: `cameraTrack.ts:createDefaultCameraSegment` derives a default arc (`deriveShortestCameraOrbitArc`); `resolveCameraOrbitArc` + `isCameraOrbitArcEndpointCompatible` validate a stored arc against its endpoints and fall back to the derived default when incompatible; `src/state/cameraTrackValidation.ts` repairs on load. A cell route entry can use the same endpoint-compatibility-with-fallback contract.
- Caveat: the KISS piece compile (`src/domain/pieceCameraTrack.ts:compilePieceCameraTrack`) currently emits only inert or boundary-cut segments (`arc: null`); non-null arcs flow through validation and persistence, not through the piece compile.

### 6. Occlusion mid-morph

Recomputed per frame against the interpolated layout, not once per pose.

- Render path: each sampled morph frame flows through `useCubeSceneRenderState` -> `src/scene/useCubeSceneInstances.ts` -> `src/scene/incrementalCubeSceneOwner.ts:render`, which diffs the transient scene into occupancy (`src/domain/incrementalCubeRenderResolution.ts`, e.g. `removeCellFromOccupancy`) and re-resolves burial and edge segments (`src/domain/cubeRenderResolution.ts` -> `edgeResolution.ts:resolveEdgeDrawSegments`). Non-incremental path: `src/scene/cubeInstances.ts:createCubeSceneInstanceContexts` -> `createCubeSceneRenderResolution`.
- `src/domain/exposure.ts:isFaceBuried` is geometry-exact, not coord-boolean: structural occupancy (coord adjacency via `neighbors.ts:createOccupancyIndex`) only nominates the candidate; burial then requires equal rotation bases, positive scales, plane coincidence (`areNearlyEqual`), and full coverage on both face axes. A half-arrived cell (presence-scaled below 1) therefore does NOT bury a neighbor's face; burial engages only at exact contact.
- `resolveCoincidentEdgeClaims` runs at two altitudes: once per morph plan on the two endpoint scenes (`src/evaluation/sharedEdgeTweens.ts:planSharedEdgeTweens`) to group shared-edge color tweens, and per frame inside render resolution for draw-segment ownership.
- Coord note: `sceneMorph.ts:interpolateCell` sets `placement.coord: after.placement.coord`, so a gliding cell structurally claims its destination coord from its first interpolated frame; geometry checks prevent false burial while it is in flight.

## Quality Map

- Risk: mid-morph coord collision. A removed cell keeps its old coord while an added cell can occupy the same coord in the same sampled scene; the occupancy map is keyed by coord, so one silently wins nomination. Harmless today (burial still gated by geometry), but a cell-route design that moves cells through occupied coords should not rely on occupancy nomination mid-flight.
- Dormant capability: `score.ts:TransitionMode "cut"` is tested and working but has no editor control (explicit NOTE in `score.ts`); the transitions design should decide its surface deliberately.
- Existing invariant to respect: `gridLock` is the domain's only cross-state grid guard, and it works by frameId lineage, not by dimensions. Any design letting states differ in cube count must decide its relationship to `captureAllowed` (today a resize changes frameId and a locked piece then refuses capture).
- Presence is already the single absence channel (`scoreAt.ts` comment: "Presence zero is absence everywhere", invariant 2). Cell arrival/departure for count changes should stay on this channel rather than invent a parallel visibility mechanism.

## Plan implications (scout view)

1. Identity plumbing for cross-state cube-count morphs already exists end to end: id-keyed diff (`prepareSceneMorphTopology`), presence staging (`getMomentCells` / `applyMomentToLayout`), and per-class arrive/depart scheduling. A count-change transition mostly needs route SETTINGS, not new machinery.
2. The route storage pattern is settled by precedent: adjacency-keyed entries parallel to `StateTransitionTrack.keyframes`, exactly like `Transition` today and like `CameraKeyframe.outgoing` for paths; extend `Transition`/`MorphSettings` rather than adding a new track kind.
3. The endpoint-compatibility-with-derived-fallback contract from `resolveCameraOrbitArc` is the right validation shape for any per-cell or per-class route data.
4. The open domain decision is `gridLock` vs per-state grids: today the lock exists precisely to prevent what the feature wants to animate.

Most surprising finding: grid dimensions are never stored; cube count is purely the derived extent of the cell set (`getSceneGridDimensions`), and the only cross-state grid guard is `gridLock.frameId` pinning capture, which a resize deliberately invalidates by minting a new frameId.
