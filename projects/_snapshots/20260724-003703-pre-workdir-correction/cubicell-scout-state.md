# Cubicell authored mutation scout

2026-07-20, `docs/performance-audit` at `5be2968b779ec52dbd9a2f2398e679c3c4a5ff84`. Read only scout for Slice 1: durable UUID identity, serializable authored operation envelopes, and ID targeted deterministic reducers. Storage remains unchanged.

## Reuse Map

### Current authored mutation route

The state surface has two operation routes and two replacement routes.

- `src/state/actions/types.ts` `CubicellStateActions.applyDocumentEdit` accepts a `WorkbenchOperation`. `src/state/actions/documentActions.ts` `applyDocumentEditState` applies it through `applyWorkbenchOperation`, then records history, reconciles selection, repairs session references, and stops playback when required.
- `src/state/actions/types.ts` `CubicellStateActions.applyLatticeEdit` accepts a `LatticeOperation`. `src/state/actions/documentActions.ts` `applyLatticeEditState` applies it through `applyLatticeOperation`, consumes the returned rename map, records history, reconciles selection assembly, and repairs session references.
- `src/state/actions/types.ts` `CubicellStateActions.updateScene` accepts a scene, a `SceneEditResult`, or a callback. `src/state/actions/documentActions.ts` `updateSceneState` executes the callback inside Zustand's `set()` callback and writes the returned scene into the Workbench.
- `src/state/actions/types.ts` `CubicellStateActions.replaceWorkbench` accepts a complete Workbench. `src/state/actions/documentActions.ts` `createDocumentActions.replaceWorkbench` installs it directly after recording history and repairing session references.

Scene intent exists before the state boundary. `src/interaction/commands/document.commands.ts` `registerDocumentCommands` receives a serializable `SceneOperation`, then wraps `applySceneOperation` in an `updateScene` callback. The operation object therefore disappears before history and persistence see the mutation. The same file's delete selection command also uses an `updateScene` callback. `src/app/useSceneOperations.ts` uses direct callbacks for neighbor growth, visibility, and grid rebuilding.

Answer 1: authored edits use both models. Workbench and lattice edits already route through operation objects. Scene edits and complete Workbench replacement still reach State as callbacks or replacement values. No `AuthoredOperation` envelope exists in `src`.

The reusable reducer core is substantial:

- `src/domain/workbenchOperations.ts` `DocumentOperation` and `applyDocumentOperation`, exported as `WorkbenchOperation` and `applyWorkbenchOperation`, form a pure, reference preserving reducer over Workbench intent.
- `src/domain/cubeOperations.ts` `SceneOperation` and `applySceneOperation` form the pure scene reducer. `CubeScope` already supports explicit `cubeId` and `cubeIds` targets.
- `src/domain/lattice.ts` `LatticeOperation` and `applyLatticeOperation` form the pure lattice reducer and already return session reconciliation information through `LatticeEditResult.renames`.
- `src/state/actions/documentActions.ts` `repairSessionReferences`, `editorWithReconciledSelection`, and the coordination in `applyDocumentEditState`, `applyLatticeEditState`, and `updateSceneState` are the existing post reducer belt. The envelope path should call this belt instead of duplicating it.
- `src/state/actions/historyCoordinator.ts` `HistoryCoordinator.recordEdit` owns batching, action journal updates, snapshot capture, and redo invalidation. This remains the history coordination owner.

### Identity and targeting

Cube operations generally resolve targets by ID. `src/domain/cubeOperations.ts` `resolveCubeScope` produces cube IDs and `applyCubeOperation` maps the cell array while matching `cell.id`. Selection types also carry `cubeId`. No cube edit reducer targets `scene.cells` by mutable array index.

Those IDs are not durable today:

- `src/domain/scene.ts` `createGridCellId` derives an ID from lattice coordinates as `cube-x-y-z`.
- `src/domain/scene.ts` `createCubeGrid` assigns those coordinate derived IDs to new cells.
- `src/domain/lattice.ts` `shiftCells` creates a new ID after a coordinate shift and reports old to new ID mappings.
- `src/domain/scene.ts` `resizeGridSceneWithResult` matches by coordinate and replaces surviving IDs with template coordinate IDs when the occupied extent is normalized.
- `src/domain/neighbors.ts` uses `createGridCellId` for new neighbor cubes and neighbor slot IDs.

Array position appears in authored sequence operations:

- `src/domain/structureOperations.ts` `StructureSequenceDocumentOperation` uses `from` and `to` for `move-keyframe`, and `index` for `remove-keyframe` and `patch-transition`.
- `src/domain/structureOperations.ts` `applyStructureSequenceOperation` indexes `asset.stateIds` and transition keyframes with those positions.
- `src/domain/lattice.ts` `LatticeOperation.index` and `src/domain/cubeOperations.ts` `CubeScope` plane `index` are lattice coordinates, not cell array positions. Their naming should remain spatially explicit during the refactor.

Index addressing already crosses the persistence boundary through local history. `src/shared/jsonDiff.ts` `createJsonDiff` delegates to `fast-json-patch`, which emits RFC 6902 paths against arrays. `src/state/historyDiff.ts` `encodePersistedHistory` writes those paths into `WireHistoryStep.ops`. `src/state/wireEncode.ts` `encodeWireStates` also writes positional RFC 6902 paths between ordered State poses. The current operation objects themselves are not persisted.

Answer 2: cube reducers match string IDs rather than cell array indexes, while the current cube IDs are coordinate identities that change when lattice coordinates change. Mutable sequence positions exist in structure operations, and array positions are embedded in persisted RFC 6902 history paths.

Current identity generators are:

- `src/domain/workbench.ts` `createId`, used by `createStructureAssetId`, `createAnimationAssetId`, `createStateId`, and `createKeyframeId`, combines `Date.now()` with a process local counter. UI callers such as `src/panels/stateCapture.ts` and `src/studio/cameraCapture.ts` generate these values before reducer application.
- `src/domain/scene.ts` `createCoordinateFrameId` combines `Date.now()` with a module counter. `createDefaultScene` and `resizeGridSceneWithResult` call it inside domain behavior.
- `src/domain/scene.ts` `createGridCellId` generates coordinate derived cube IDs.

No `crypto.randomUUID`, `randomUUID`, or UUID helper is used anywhere under `src`. There is no generator for Project, operation, client session, or actor identity in the inspected surface.

Answer 3: identity generation exists, but it uses coordinate strings or time plus process counters. Native UUID generation is absent. `createCoordinateFrameId` also makes grid rebuilding environment dependent inside the domain path.

### History and inverse information

Runtime history stores reference snapshots. `src/state/documentHistory.ts` `DocumentHistoryEntry` contains the pre edit Workbench, `activeStateId`, selection, selection set, and view policy. `DocumentHistory` holds `past` and `future` stacks capped by `documentHistoryLimit` at 100. `pushDocumentHistory`, `undoDocumentHistory`, and `redoDocumentHistory` move entries between those stacks. Structural sharing keeps unchanged domain objects shared.

Persisted history stores backward RFC 6902 diffs. `src/state/wireEncode.ts` `createWireEncoder` caps history through `capPersistedHistory`, then calls `encodePersistedHistory`. `src/state/historyDiff.ts` `encodePersistedHistory` walks from the present Workbench toward older snapshots and stores one backward diff per step. `src/state/cubicellHistory.ts` `restoreWireHistory` applies each diff and reconstructs snapshot entries. Redo is omitted by `capPersistedHistory`.

The backward diffs contain structural inverse data for local snapshot restoration. They do not identify the authored operation, its target, actor, client, observed revision, or schema. They also encode document shape and array position, which `STORAGE.md` excludes from the shared domain protocol.

Operation specific inverse information must be computed against the pre edit state. Several current bodies lack the prior value needed for inversion: rename operations lack the old name, delete operations lack deleted content and relative placement, State update and restore operations lack the prior pose or attachment, and scene patches lack prior property values. `SceneEditResult.renames` repairs session references and does not describe an inverse operation.

Answer 4: history uses Workbench snapshots in memory and backward RFC 6902 diffs on the wire. Carrying inverse domain information requires the authored reducer boundary to return or record a validated inverse body derived from the pre edit state. The existing snapshot and diff history can remain the undo implementation during Slice 1, while the applied operation record carries the semantic inverse for later outbox and hosted work.

### Validation, wire encoding, guards, and normalization

Reuse these existing owners:

- `src/state/jsonGuards.ts` `isJsonObject`, `isFiniteNumber`, and `isVec3` are the shared primitives for unknown input validation. New envelope and body validators should import them.
- `src/state/persistedValidation.ts` demonstrates validator composition through `isWireHistoryStep`, `isWireStateStep`, and `isRfc6902Operation`. Its RFC 6902 validator remains specific to local wire data.
- `src/state/workbenchValidation.ts` `isPersistedWorkbench`, `isPersistedPose`, `completePersistedWorkbench`, and `completePersistedPose` own snapshot validation and repair.
- `src/state/persistedStateNormalization.ts` `normalizePersistedState` and `restoreWorkbenchAndHistory` own rehydrate repair. Operation validation should run before reducer application and should not duplicate snapshot normalization.
- `src/state/wireEncode.ts` `createWireEncoder`, `encodeWireStates`, and the degradation functions own the current localStorage wire shape. Slice 1 can leave this module unchanged.
- `src/shared/jsonDiff.ts` `createJsonDiff`, `src/state/historyDiff.ts` `encodePersistedHistory` and `applyHistoryDiff`, and `src/state/cubicellHistory.ts` `restorePersistedHistory` remain the compact local undo codec. They should not become the authored operation protocol.
- `src/state/cubicellHistory.ts` `createPresentEntry` and `applyHistoryStep` retain selection, active State, view policy, and session repair semantics around undo and redo.

No validator for `DocumentOperation`, `SceneOperation`, `LatticeOperation`, or an authored envelope exists under `src`. `src/domain/cubeOperations.ts` `isViewLaneSceneOperation` classifies view intent and is not an unknown input validator.

Answer 5: reuse the pure domain reducers, the State post reducer belt, history coordinator, JSON guards, snapshot validators and normalization, and the existing wire codec. Add one authored operation validation owner. Do not duplicate wire validation or use RFC 6902 as domain intent.

## Quality Map

### Durable identity

High risk. `CubeCell.id` is used as identity throughout selection, score order, and cube reducers, while `createGridCellId`, `shiftCells`, and `resizeGridSceneWithResult` bind it to placement. A lattice move therefore changes identity. `createId` and `createCoordinateFrameId` depend on clocks and process state. This conflicts with `STORAGE.md` `Durable identity`, which requires UUIDv4 values generated before reducer application and preserved when placement changes.

### Serializable intent boundary

High risk. `DocumentOperation` and `LatticeOperation` reach State intact, while `SceneOperation` becomes a callback in `registerDocumentCommands`. `updateScene` also accepts arbitrary callbacks, scene replacements, and `SceneEditResult` values. `replaceWorkbench` is a complete document replacement. History sees only before and after state.

Some current Scene operation bodies depend on private session context. `src/domain/cubeOperations.ts` `CubeScope` includes `selected` and `selection-set`. `applySceneOperation` passes `CubeScopeContext` into cube resolution and derives assembly order origin from the current selection. Durable bodies must materialize explicit cube IDs and any derived origin before envelope creation.

### Deterministic reducer boundary

Partial. `applyDocumentOperation`, `applySceneOperation`, and `applyLatticeOperation` are pure for supplied inputs. Determinism is weakened by reducer adjacent creation in `createCoordinateFrameId`, coordinate based cell identity, and operation bodies that consult selection context. Caller supplied IDs already exist for State, asset, and keyframe creation operations and provide the pattern to extend.

### Stable ordered targets

High risk. Camera operations already target `keyframeId` in `src/domain/cameraOperations.ts`. Structure sequence operations still use `from`, `to`, and `index`. The reusable direction is visible in camera operations: locate by ID, then derive a local index inside the reducer. Structure moves need a moving keyframe ID plus a relative anchor such as `beforeId` or `afterId`; remove and transition patch operations need a keyframe or transition owner ID.

### Inverse contract

Missing at the semantic operation layer. `DocumentHistoryEntry` has no operation or inverse field. Backward history diffs restore snapshots and cannot serve as a stable shared command inverse. The inverse must be derived while the pre edit Workbench is available in `applyDocumentEditState`, `applyLatticeEditState`, or their replacement unified boundary.

### Action file and function sizes

No threshold violations exist in `src/state/actions`.

- `documentActions.ts`: 389 lines.
- `editorActions.ts`: 155 lines.
- `historyCoordinator.ts`: 62 lines.
- `index.ts`: 18 lines.
- `selectionActions.ts`: 102 lines.
- `transportActions.ts`: 173 lines.
- `types.ts`: 108 lines.

The largest parsed function is `createTransportActions` at 114 lines. `createEditorActions` is 102 lines and `createDocumentActions` is 68 lines. Every file remains below 700 lines and every function remains below approximately 150 lines.

Answer 6: there are no current size violations. Envelope types, validators, and reducer orchestration have distinct ownership and should use focused modules instead of expanding `documentActions.ts` into a second domain layer.

## Plan

1. **Introduce durable identity at the caller boundary.** Add one UUIDv4 factory backed by native `crypto.randomUUID()`. Use it for Structure, Animation, State, keyframe, coordinate frame, cube, and operation creation. Pass every created ID in the operation body. Remove `createId`, coordinate derived use of `createGridCellId` as identity, and clock or counter generation from reducer reachable code. Keep `getGridCoordKey` as the coordinate occupancy key.

2. **Separate cube identity from placement.** Change lattice shifts and grid normalization to preserve `CubeCell.id` while changing `placement.coord`. New cube operations carry `{ id, coord }` creation material. Reuse the reconciliation role of `LatticeEditResult.renames` during the mechanical move, then delete rename specific behavior in the same slice once stable IDs make it obsolete.

3. **Normalize existing operation unions into durable bodies.** Reuse `DocumentOperation`, `SceneOperation`, and `LatticeOperation` behavior. Resolve `CubeScope.selected`, `CubeScope.selection-set`, selection derived score origin, and direct delete callbacks into explicit IDs and values before envelope construction. Replace structure sequence `from`, `to`, and `index` bodies with ID and relative anchor bodies. Keep view lane, selection, hover, transport, panels, and preferences outside authored operations.

4. **Add one envelope and validation owner.** Define `OperationTarget` and `AuthoredOperation<TBody>` from `STORAGE.md`, with `id`, target, actor, client, observed revision, schema version, and body. Compose strict unknown input validators from `jsonGuards.ts`. Body validation delegates to one validator per existing operation family. Snapshot and RFC 6902 validators retain their current ownership.

5. **Create one authored reducer boundary.** Validate the envelope, select the existing pure reducer by body family, apply it, then run the current history, selection, playback, and session repair belt. Return a reference preserving no op when validation or domain preconditions reject the body. Remove `updateScene` callback and complete Workbench replacement as authored mutation routes after all callers migrate. Keep an explicit non authored load or reset boundary for rehydration and clean slate creation.

6. **Capture semantic inverse information before application.** Add an applied operation record containing the validated envelope and an operation specific inverse body derived from the pre edit state. Reuse `HistoryCoordinator` for batching and stack coordination. Keep `DocumentHistoryEntry` snapshots and the existing RFC 6902 wire history as the active undo and persistence implementation in Slice 1, so `createWireEncoder`, `CubicellWireState`, storage version, localStorage, and rehydrate normalization do not change.

7. **Migrate callers and delete parallel paths.** Route `registerDocumentCommands`, `useSceneOperations`, State capture, camera capture, lattice commands, and delete selection through envelope creation and the unified authored dispatch. Delete the callback mutation API once its final caller moves. Resolve projection and polarity ownership in this slice: while they remain fields of the persisted Pose, route them through authored envelopes and make their inverses explicit; if they are private workspace view, move them out of Workbench. No persisted callback route remains.

8. **Prove the slice.** Add focused tests for UUIDv4 creation before reducer entry, stable cube IDs across lattice insert, lattice delete, resize, and movement, JSON round trip of every envelope body, rejection of malformed envelopes, replay equality from the same observed state, ID anchored sequence edits, and semantic inverse round trips for destructive operations. Reuse `tests/workbenchOperations.test.ts`, `tests/sceneOperation.placeCubes.test.ts`, `tests/lattice.*.test.ts`, `tests/workbenchEdit.state.test.ts`, `tests/stateHistory.test.ts`, `tests/historyPersistence.test.ts`, and `tests/wireEncode.test.ts`. Run the repository's real TypeScript gate with `pnpm exec tsc -b --pretty false --force`, then the complete test suite. Confirm the existing wire payload and storage version are unchanged.

The largest reuse opportunity is the existing pure reducer families and State repair belt. The largest risk is that current IDs and scene dispatch erase the durable intent needed for replay: cube identity follows coordinates, sequence intent uses positions, and scene operations become callbacks before State records them.
