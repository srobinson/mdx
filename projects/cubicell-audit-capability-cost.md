# Cubicell capability cost audit

## Counts first

- Shipped sample: **13 to 25 files per capability**, median **18**, across **5 to 7 layers**, median **6**.
- Shipped sample median composition: **9 production files**, **8 proof files**, and **1 supporting file**.
- Per edge treatment lower bound: **49 files**, comprising **29 production files** and **20 proof files**, across **9 layers**.
- Navigability from `src/domain/cube.ts:CubeEdgeState`: **30 discoverable files**, **19 files that require prior repository knowledge**.
- Cost concentration: the fixed geometry instance seam accounts for **17 of the 49 files**, comprising 10 production owners and 7 direct proofs.

An ordinary authored capability costs about 18 files and 6 layers here. The production portion, about 9 files, is reasonable for a typed editor with persistence and undo. The total is high because each capability carries substantial proof. Per edge treatment crosses into unhealthy tax territory because geometry identity is repeated across the live renderer, stable slot projection, coverage renderer, and thumbnail renderer.

## Method

Probe A uses exact feature commits and `git diff-tree` counts. Counts include every changed file. Production, tests, and supporting artifacts are reported separately.

Probe B follows the approved per edge shaping contract and the current source at `9f766b2c873b4a1ebe02d6a7e782b690571df76f`. The count is a lower bound. It includes files whose current manual field lists, geometry ownership, user surfaces, or executable gates must change for the property to remain correct across editing, persistence, animation, incremental rendering, and thumbnails.

For navigability, the single entry point is `src/domain/cube.ts:CubeEdgeState`. A file is discoverable when it contains an explicit edge state reference, or is one relative import hop from a file containing `CubeEdgeState`, `defaultCubeEdgeState`, `setCubeEdgeState`, `set-edge-state`, or `edge.thickness`. `src/domain/index.ts` is excluded as a traversal hub because its broad barrel would make almost the whole application appear discoverable. New geometry owners and their direct tests count as discoverable because they originate at the entry point.

## Probe A: shipped capabilities

### 1. First class cube visibility

Commit `a7e85b4b7e6c75ec4b07a6fd51ea1b52ce2b4e1c`

**13 files: 9 production, 3 tests, 1 supporting file. Six layers.**

Layers crossed:

1. Domain model and mutation: `src/domain/cube.ts:CubeCell.visibility`, `src/domain/cube.ts:setCubeVisibility`.
2. Scoped operation: `src/domain/cubeOperations.ts:CubeOperation`, `src/domain/cubeOperations.ts:applyCubeOperationToCell`.
3. Similarity semantics: `src/domain/selectionQuery.ts:areCubeStatesEqual`.
4. Command binding and panels: `src/editor/controlBindings.ts:cubeVisibleBinding`, `src/panels/CubeSection.tsx:CubeSection`, `src/panels/StructureSection.tsx:StructureSection`, `src/panels/cubeSelectItems.ts:createCubeSelectItems`.
5. Scene projection and persisted state repair: `src/scene/cubeInstances.ts:createCubeCellInstances`, `src/state/cubicellStore.ts:normalizePersistedState`.
6. Proof: `tests/domain.test.ts:cube visibility`, `tests/instances.test.ts:hidden cubes`, `tests/state.test.ts:persisted store`.

The supporting change was `LESSONS.md`.

### 2. Delete cubes and Escape to deselect

Commit `972e73d528e27669178b3a4c0150df6efccde248`

**18 files: 8 production, 8 tests, 2 design artifacts. Seven layers.**

Layers crossed:

1. Domain topology and selection: `src/domain/neighbors.ts:removeCubesById`, `src/domain/selection.ts:getSelectedCubeIds`, `src/domain/index.ts:removeCubesById`.
2. Command vocabulary: `src/editor/affordances.ts:editorCommandIds`, `src/editor/affordances.ts:editorCommandDefinitions`.
3. Command construction: `src/editor/commands.ts:createDeleteSelectionCommand`.
4. Keyboard adapter: `src/editor/keyboard/keymap.ts:keyboardCommandIds`.
5. Runtime command handler: `src/interaction/commands/document.commands.ts:registerDocumentCommands`.
6. User surface: `src/panels/SelectionSection.tsx:SelectionSection`.
7. Proof and design: `tests/deleteSelection.command.test.ts:delete-selection command`, `tests/editorAdapters.test.ts:editor command registry`, `tests/keyboard.test.ts:KeyboardShortcuts mode transitions`, `tests/keymap.delete.test.ts:delete keymap`, `tests/neighbors.test.ts:removeCubesById`, `tests/selectSimilar.modifiers.test.tsx:the Similar button`, `tests/selectedCubeIds.test.ts:getSelectedCubeIds`, `tests/selectionSection.test.tsx:SelectionSection delete`, `docs/superpowers/specs/2026-07-12-cube-delete-design.md:Cube Delete Design`, `docs/superpowers/plans/2026-07-12-cube-delete.md:Cube Delete Plan`.

### 3. Workbench edge contrast and new cube style inheritance

Commit `277589ddb72c41e6da07768e66e179aa3d104440`

**25 files: 10 production, 15 tests. Five layers.**

Layers crossed:

1. Application operation dispatch: `src/app/useSceneOperations.ts:useSceneOperations`.
2. Domain style inheritance and placement: `src/domain/cube.ts:inheritCubePartStyle`, `src/domain/cubeOperations.ts:SceneOperation`, `src/domain/neighbors.ts:CubeSeed`, `src/domain/neighbors.ts:placeCubesAt`, `src/domain/index.ts:inheritCubePartStyle`.
3. Scene color and coverage: `src/scene/CubeScene.tsx:CubeScene`, `src/scene/colorSpace.ts:shiftLightnessForContrast`, `src/scene/edgeCoverageCore.ts:createEdgeCoverageMesh`, `src/scene/instancedPartMeshCore.ts:syncInstancedPartMesh`.
4. Theme contract: `src/theme/scenePolarity.ts:ScenePolarityConfig`.
5. Proof: 15 files covering color space, edge coverage, edge resolution, exposure, history, instances, neighbor inheritance, Piece Motion, scene morph, scene operations, state, and thumbnails.

The 15 proof files were `tests/assetStateInvariants.test.ts`, `tests/colorSpace.test.ts`, `tests/edgeCoverageCore.test.ts`, `tests/edgeResolution.test.ts`, `tests/exposure.test.ts`, `tests/historyPersistence.test.ts`, `tests/instances.test.ts`, `tests/neighbors.test.ts`, `tests/pieceMotionEvaluation.test.ts`, `tests/pieceMotionSession.test.ts`, `tests/sceneMorph.bench.ts`, `tests/sceneMorph.test.ts`, `tests/sceneOperation.placeCubes.test.ts`, `tests/state.test.ts`, and `tests/thumbnailArtifact.test.ts`.

## Probe A verdict

The observed production cost is tightly grouped at 8 to 10 files. The large spread in total cost comes from proof: 3 to 15 test files. Six layers is normal for an editor capability that must be authored, invoked, rendered, and verified.

The tax appears where one property has several hand maintained representations. Visibility needed model, query, renderer, and persisted repair lists. Edge contrast needed separate live geometry, coverage, polarity, and thumbnail proofs. Those repeated projections predict the larger Probe B result.

## Probe B: per edge treatment

The approved property is `treatment: "sharp" | "round" | "chamfer"` plus `shapeSize: number` on `CubeEdgeState`. The existing `set-edge-state` operation already supplies scoped command and state mutation. `src/domain/cubeOperations.ts:CubeOperation`, `src/domain/cubeCellOperations.ts:applyCubeOperationToCell`, `src/domain/sceneOperationMaterialization.ts:materializeSceneOperations`, `src/interaction/commands/document.commands.ts:registerDocumentCommands`, and `src/state/actions/authoredReducer.ts:reduceAuthoredOperationState` require no new parallel command path.

The lower bound below includes every owner that must change.

### Domain model, comparison, and render impact: 5 production files

1. `src/domain/cube.ts:CubeEdgeState`, `src/domain/cube.ts:defaultCubeEdgeState`, `src/domain/cube.ts:inheritCubePartStyle`
   Add the values, defaults, guards, cloning behavior, and growth inheritance.
2. `src/domain/index.ts:cube.ts public contract`
   Export the treatment vocabulary and validation guard for wire consumers.
3. `src/domain/selectionAspects.ts:edgeStateDistance`, `src/domain/selectionAspects.ts:areEdgeStatesEqual`
   Add exact treatment equality and the shape size distance term required by edge similarity.
4. `src/domain/exposure.ts:isFaceBuried`
   A touching face stops covering when an incident edge is shaped with positive size.
5. `src/domain/authoredRenderImpact.ts:CubeEdgeRenderAttribute`, `src/domain/authoredRenderImpact.ts:changedEdgeAttributes`
   Treatment edits must invalidate geometry and neighbor burial through the incremental owner.

### Persistence and wire validation: 3 production files

6. `src/state/workbenchValidation/pose.ts:isCurrentEdgeState`, `src/state/workbenchValidation/pose.ts:isEdgeState`
   Admit exactly the current edge shape.
7. `src/state/authoredOperationValidation/scene.ts:isPartPatch`
   Admit and validate treatment and shape size on `set-edge-state`.
8. `src/persistence/recordCodecs/compactPose.ts:CompactEdge`, `src/persistence/recordCodecs/compactPose.ts:encodeCell`, `src/persistence/recordCodecs/compactPose.ts:decodeCell`, `src/persistence/recordCodecs/compactPose.ts:sameEdge`
   Carry both values through the compact durable representation.

### Evaluation: 1 production file

9. `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology`, `src/evaluation/sceneMorph.ts:interpolateCell`
   Detect treatment changes, switch the discrete treatment at the authored cut, and interpolate shape size with other numeric ink.

### Command and user surfaces: 10 production files

10. `src/editor/controlBindings.ts:ControlBindingId`, `src/editor/controlBindings.ts:controlBindingList`
    Add treatment and shape size bindings that emit the existing `set-edge-state` command.
11. `src/panels/panelDefinitions.ts:edgeBindingIds`
    Expose both bindings in the selected edge inspector.
12. `src/domain/sliceMap.ts:createSliceMapModel`
    Add the pure slice corner to physical edge mapping.
13. `src/panels/StructureSection.tsx:StructureSection`
    Add the required corner affordance for buried edge access.
14. `src/panels/panels.css:cc-slice cell family`
    Style the slice corner affordance and its active scrub state.
15. `src/app/useSceneOperations.ts:useSceneOperations`
    Convert canvas and slice intents into existing command bus operations.
16. `src/app/stageInteraction.ts:StageMutationHandlers`, `src/app/stageInteraction.ts:gateStageMutationHandlers`
    Gate every treatment mutation when the staged scene is read only.
17. `src/renderer/contract.ts:SharedRendererCanvasProps`
    Carry typed edge cycle and scrub intent across the shared renderer boundary.
18. `src/studios/editor/EditorStudio.tsx:EditorCanvas`, `src/studios/editor/EditorStudio.tsx:useEditorAppModel`
    Bind renderer intent to command dispatch and the authored gesture transaction.
19. `src/config/cubicellConfig.ts:scrub feel constants`
    Own the canvas drag sensitivity and bounded variant cache limit as named product configuration.

### Live rendering, instancing, and secondary rendering: 10 production files

20. `src/scene/cubeInstances.ts:CubeEdgeInstance`, `src/scene/cubeInstances.ts:CubeFaceInstance`, `src/scene/cubeInstances.ts:createCubeCellInstances`
    Project a shape signature into face, edge, and hit target instances.
21. `src/scene/cubeInstanceSlots.ts:CubeInstanceBucket`, `src/scene/cubeInstanceSlots.ts:createCubeInstanceSlotOwner`
    Partition stable slots by geometry signature while preserving tombstones and patch identity.
22. `src/scene/InstancedPartMesh.tsx:InstancedPartMesh`
    Accept variant geometry rather than only fixed `box` or `plane` geometry.
23. `src/scene/CubeScene.tsx:CubeScene`
    Render the variant groups and own edge tap and drag interaction.
24. `src/scene/incrementalCubeSceneOwner.ts:IncrementalCubeSceneOwner`, `src/scene/incrementalCubeSceneOwner.ts:createCellEntry`
    Move an edited cell between variant slot owners without forcing a full scene rebuild.
25. `src/scene/edgeCoverageCore.ts:createEdgeCoverageMesh`
    Generate coverage from the shaped edge silhouette.
26. `src/scene/EdgeCoverageLayer.tsx:EdgeCoverageLayer`
    Render and dispose coverage meshes per signature.
27. `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact`, `src/thumbnail/thumbnailArtifact.ts:ThumbnailArtifact`
    Use the same geometry variants in State thumbnails and dispose them with the artifact.
28. `src/scene/cubeShapeGeometry.ts:createCubeShapeSignature`, `src/scene/cubeShapeGeometry.ts:createCubeShapeGeometry`
    Required new owner, provisional name. One pure signature and geometry factory must replace repeated local derivations.
29. `src/scene/geometryVariantRegistry.ts:GeometryVariantRegistry`
    Required new owner, provisional name. It must bound or reference count geometry lifetime under continuous scrub and unique signatures.

### Required proof: 20 files

1. `tests/domain.test.ts:edge treatment operations`
2. `tests/selectionQuery.test.ts:edge-state aspect matching`
3. `tests/exposure.test.ts:render face burial`
4. `tests/authoredRenderImpact.test.ts:edge treatment render impact`
5. `tests/authoredRenderImpactClosure.test.ts:neighbor treatment closure`
6. `tests/incrementalCubeRenderResolution.test.ts:incremental treatment parity`
7. `tests/sceneMorph.test.ts:edge treatment morph`
8. `tests/authoredOperations.test.ts:authored operation contract`
9. `tests/projectRecordCodecs.test.ts:compact pose revision`
10. `tests/panels.test.tsx:control binding round trips`
11. `tests/sliceMap.test.ts:slice corner edge mapping`
12. `tests/structureSection.test.tsx:StructureSection slice corner controls`
13. `tests/instances.test.ts:shaped face edge and hit instances`
14. `tests/cubeInstanceSlots.test.ts:geometry signature slot migration`
15. `tests/incrementalSceneReactMeshHandoff.test.tsx:variant patch handoff`
16. `tests/edgeCoverageCore.test.ts:shaped edge coverage`
17. `tests/thumbnailArtifact.test.ts:shaped thumbnail artifact`
18. `tests/appSelectionBoundary.test.tsx:edge gesture command bus integration`
19. `tests/cubeShapeGeometry.test.ts:shape signature and geometry invariants`
20. `tests/geometryVariantRegistry.test.ts:bounded disposal and unique signature stress`

These files cover nine layers:

1. Authored domain
2. Selection semantics
3. Command and application dispatch
4. Durable wire and validation
5. Evaluation and morph
6. Render impact and resolution
7. GPU instancing and resource lifetime
8. Inspector, canvas, slice map, and thumbnail surfaces
9. Verification and worst case stress

## Navigability

**30 discoverable, 19 hidden.**

The 19 hidden files are:

- `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology`
- `src/state/workbenchValidation/pose.ts:isCurrentEdgeState`
- `src/domain/sliceMap.ts:createSliceMapModel`
- `src/panels/StructureSection.tsx:StructureSection`
- `src/panels/panels.css:cc-slice cell family`
- `src/app/useSceneOperations.ts:useSceneOperations`
- `src/app/stageInteraction.ts:StageMutationHandlers`
- `src/renderer/contract.ts:SharedRendererCanvasProps`
- `src/studios/editor/EditorStudio.tsx:EditorCanvas`
- `src/config/cubicellConfig.ts:scrub feel constants`
- `src/scene/cubeInstances.ts:createCubeCellInstances`
- `src/scene/cubeInstanceSlots.ts:createCubeInstanceSlotOwner`
- `src/scene/InstancedPartMesh.tsx:InstancedPartMesh`
- `src/scene/CubeScene.tsx:CubeScene`
- `src/scene/incrementalCubeSceneOwner.ts:createCellEntry`
- `src/scene/edgeCoverageCore.ts:createEdgeCoverageMesh`
- `src/scene/EdgeCoverageLayer.tsx:EdgeCoverageLayer`
- `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact`
- `tests/edgeCoverageCore.test.ts:edge coverage`

The broad domain barrel is the main reason a normal import walk fails. Many semantically coupled files import `CubeCell` or the domain barrel, then maintain their own field projections. The source has no edge property manifest that names persistence codecs, evaluation classifiers, render attributes, instance geometry, coverage, and thumbnail consumers together.

## Concentration and abstraction verdict

The single seam inflating cost is **fixed geometry instancing**:

- `src/scene/cubeInstances.ts:createCubeCellInstances` projects parts without geometry identity.
- `src/scene/cubeInstanceSlots.ts:cubeInstanceBucketNames` closes the world to seven fixed buckets.
- `src/scene/InstancedPartMesh.tsx:InstancedPartMesh` owns one fixed geometry.
- `src/scene/CubeScene.tsx:CubeScene` mounts those buckets explicitly.
- `src/scene/edgeCoverageCore.ts:createEdgeCoverageMesh` builds a separate fixed box silhouette.
- `src/thumbnail/thumbnailArtifact.ts:layerDescriptors` repeats the fixed face and edge layer model.

This seam creates 10 production obligations and 7 direct proof obligations in Probe B.

A missing abstraction is justified now: a narrow, signature keyed geometry variant owner shared by the live canvas and thumbnail artifact. It should own geometry generation, stable instance groups, and bounded disposal. The approved capability directly requires multiple geometry identities and worst case unique signatures, so this abstraction has immediate consumers and executable acceptance criteria.

A general visual property registry would be premature. The existing `set-edge-state` operation already collapses command construction, scope materialization, state mutation, history, and authored dispatch. The repeated cost lives in geometry identity and manual field projections. Addressing that seam should reduce future shape capabilities without replacing the parts that already compose well.

