# Cubicell structural census

Baseline: `9f766b2c873b4a1ebe02d6a7e782b690571df76f`.

Method:

- Source counts use physical lines from every file under `src/`.
- Function spans come from the TypeScript syntax tree. A function qualifies when its declaration body spans more than 150 physical lines.
- `src/app` modules are TypeScript or TSX files. CSS assets remain outside the count.
- A direct action access point is one source access to a mutating `CubicellStore` member outside `src/app/useSynchronousEditorCommands.ts`, the command executor. A semantic flow is one consuming symbol plus one direct action.
- Production reachability starts at `src/main.tsx` and follows static imports, dynamic imports, worker URLs, and the build preload graph in `viteStudioPreloads.ts`.

## 1. Sizing

Counts first: **10 files over 500 lines; 0 files over 700 lines.** Three of the ten are required touch points for the approved per edge shaping work.

| Lines | File | Shapes work |
| ---: | --- | --- |
| 668 | `src/camera/cameraAuthorityRuntime.ts` | No. Shaping does not alter camera authority. |
| 605 | `src/state/projectDurability.ts` | No. `CubeEdgeState` already travels through the generic authored and durability records. |
| 603 | `src/domain/cubeOperations.ts` | No required edit. `set-edge-state` already carries `Partial<CubeEdgeState>`. |
| 542 | `src/domain/index.ts` | **Yes.** The public domain barrel is explicit and deep imports are closed. `CubeEdgeTreatment` and any shared shape signature contract must be exported here. |
| 538 | `src/persistence/projectRecordHydration.ts` | No. Hydration delegates physical pose validation and codecs. |
| 534 | `src/domain/incrementalCubeRenderResolution.ts` | No required edit. Its generic edge impact path already reindexes and resolves any changed edge attribute and reruns face burial for the source and face neighbors. |
| 526 | `src/domain/selectionQuery.ts` | No required edit. It delegates comparable fields to `src/domain/selectionAspects.ts`. |
| 525 | `src/scene/CubeScene.tsx` | **Yes.** The approved design places edge hover, tap treatment cycling, drag ownership, and pointer suppression at `CubeScene`. |
| 524 | `src/editor/controlBindings.ts` | **Yes.** The approved edit context adds treatment and shape size controls through the binding vocabulary. |
| 509 | `src/domain/incrementalEdgeResolution.ts` | No required edit from the contract alone. Shaped geometry can retain the current ownership and junction topology while geometry variants change the rendered part. |

The current head does not violate the 700 line limit. The three required touch points are already over 500 lines. `src/scene/CubeScene.tsx:CubeScene` is also over the function limit, so it must be decomposed before shape interaction is added. `src/domain/index.ts` is an explicit export ledger, which accounts for its size.

## 2. Function sizing

Count first: **4 functions over 150 lines.**

| Lines | Path and symbol | Shapes work |
| ---: | --- | --- |
| 400 | `src/scene/CubeScene.tsx:CubeScene` | **Yes.** Direct canvas edge interaction belongs here under the approved design. Extract pointer ownership and layer composition before adding it. |
| 398 | `src/panels/StructureSection.tsx:StructureSection` | **Yes.** Slice map corner editing is part of the same approved phase. |
| 177 | `src/panels/motion/PieceStateStrip.tsx:PieceStateStrip` | No. |
| 165 | `src/panels/StructureSliceLayer.tsx:StructureSliceLayer` | **Yes.** The slice corner maps to the physical edge and needs treatment and shape size input. |

The shaping slice intersects three of the four long functions.

## 3. Boundaries

Counts first: **21 `src/app` modules, 3 bootstrap shared modules, 18 editor bound modules.** The claim of 19 modules with 17 editor only modules is stale by two modules, while its ratio remains close.

### Shared bootstrap modules

| Module | Production consumers | Ownership fact |
| --- | --- | --- |
| `src/app/AppBootstrap.tsx:AppBootstrap` | `src/main.tsx` | Hosts any `StudioLoadSession`. It contains no editor model. |
| `src/app/startupIndicator.ts` | `src/main.tsx`, `src/app/AppBootstrap.tsx` | Owns route startup state for every studio. |
| `src/app/startupIndicatorMarkup.ts` | `src/app/startupIndicator.ts`, `viteStudioPreloads.ts` | Owns preload markup shared by route boot. |

### Editor bound modules

| Module | Current production owner or consumer |
| --- | --- |
| `src/app/DockablePanel.tsx:DockablePanel` | Editor shell and panel drag capability |
| `src/app/FloatingKeypad.tsx:FloatingKeypad` | `src/studios/editor/EditorStudio.tsx` |
| `src/app/horizontalScrollPanPort.ts:createHorizontalScrollPanPort` | Motion and panel drag capabilities in the Editor |
| `src/app/panelDragPort.ts:createPanelDragPort` | Editor shell and panel drag capability |
| `src/app/panelResize.ts:beginPanelResize` | Editor panels and panel drag capability |
| `src/app/PersistenceStatus.tsx:PersistenceStatus` | `src/studios/editor/EditorStudio.tsx` |
| `src/app/readEditorState.ts:selectEditorCommandContext` | Editor command and selection adapters |
| `src/app/SelectionFocusDriver.ts:SelectionFocusDriver` | `src/studios/editor/EditorStudio.tsx` |
| `src/app/SelectorTabDriver.ts:SelectorTabDriver` | `src/studios/editor/EditorStudio.tsx` |
| `src/app/stageInteraction.ts:gateStageMutationHandlers` | `src/studios/editor/EditorStudio.tsx` |
| `src/app/StudioShell.tsx:StudioShell` | `src/studios/editor/EditorStudio.tsx` |
| `src/app/useAuthoredScrubGesture.ts:useAuthoredScrubGesture` | Editor panels and parked camera track controls |
| `src/app/useEditorCommands.ts:useEditorCommands` | `src/studios/editor/EditorStudio.tsx` |
| `src/app/usePanelResize.ts:usePanelResize` | `src/app/DockablePanel.tsx` |
| `src/app/usePresentedSelection.ts:usePresentedSelection` | Editor focus, selector, and renderer binding |
| `src/app/useSceneOperations.ts:useSceneOperations` | Editor panels and `EditorStudio` |
| `src/app/useSnapSize.ts:useSnapSize` | `src/app/DockablePanel.tsx` |
| `src/app/useSynchronousEditorCommands.ts:useSynchronousEditorCommands` | Editor command core |

### Consequence

The directory does not prevent a second studio from loading. `src/studios/catalog.ts:beginStudioLoad`, `src/studios/contract.ts:StudioModule`, and `src/studios/StudioHost.tsx:StudioHost` already load the Editor and Design System studios through the same contract.

The directory does prevent clean reuse of its shell code by another product studio. A Browser or Animation studio must either import editor session assumptions from `src/app`, duplicate shell capabilities, or first move the 18 editor modules to `src/studios/editor` and a deliberately shared shell package. Clean shared shell reuse therefore requires boundary extraction. Runtime studio registration already works.

## 4. The side doors

Counts first:

- **47 direct store access points across 25 files.**
- Those access points expand to **52 semantic direct flows** because shared hook bindings in `src/app/useSceneOperations.ts` serve several operations.
- Classification: **40 legitimate, 5 lazy, 7 legacy.**
- The earlier estimate of about 37 across 18 files understates the current tree by 10 access points and 7 files.

Classification rules:

- **Legitimate:** the flow is lifecycle, renderer feedback, transient presentation, preferences, durability, or transaction coordination. An accepted editor command would misstate ownership.
- **Lazy:** an accepted command descriptor or generic accepted command path exists, and the caller bypasses it.
- **Legacy:** the user intent predates the two lane bus introduced in `3c73c18`; the direct path survived enrollment.

| File | Path and symbol plus direct action | Class | Count | Fact |
| --- | --- | --- | ---: | --- |
| `src/app/DockablePanel.tsx` | `DockablePanel` → `patchPanelPlacement` | Legitimate | 1 | Persisted user panel layout, including resize and collapse, is shell state. |
| `src/app/PersistenceStatus.tsx` | `PersistenceStatus` → `recoverToLastCommitted`, `retrySave` | Legitimate | 2 | These are durability recovery operations with external storage effects. |
| `src/app/SelectorTabDriver.ts` | `SelectorTabDriver` → `setSelectorTab` | Legitimate | 1 | Derived synchronization follows selection state; no user command initiates it. |
| `src/app/useAuthoredScrubGesture.ts` | `useAuthoredScrubGesture` → `authoredGesture` | Legitimate | 1 | This is transaction coordination for preview, commit, and cancel. The authored values still dispatch commands. |
| `src/app/useSceneOperations.ts` | `addNeighborAtSlot`, `addNeighborToSelectedFaces` → `dispatchAuthoredEdit` | Legacy | 2 | Both were neighbor growth intents before the bus and need atomic selection results absent from the current scene command. |
| `src/app/useSceneOperations.ts` | `toggleCubeBuilt` → `dispatchAuthoredEdit` | Lazy | 1 | `scene` commands already accept `set-cube-visibility`; this path constructs the authored body directly. |
| `src/app/useSceneOperations.ts` | `updateGridComposerDimensions`, `openGridComposer` → `dispatchAuthoredEdit` | Legacy | 2 | Grid rebuild and initial preset flows predate the bus and retain reset history plus selection result options outside the command payload. |
| `src/app/useSceneOperations.ts` | `updateGridComposerDimensions`, `openGridComposer` → `setGridComposerDimensions` | Legitimate | 2 | Composer draft dimensions are transient editor surface state. |
| `src/app/useSceneOperations.ts` | `openGridComposer`, `closeGridComposer` → `setGridComposerOpen` | Legitimate | 2 | Composer visibility is transient editor surface state. |
| `src/app/useSceneOperations.ts` | `saveGridDefault` → `patchPreferences` | Legitimate | 1 | The saved default is a user preference. |
| `src/camera/CameraDriver.tsx` | `CameraDriver` → `setFocused` | Legitimate | 1 | Camera authority reports focus detachment back to session state. |
| `src/editor/keyboard/useSeamRevealHold.ts` | `useSeamRevealHold` → `setSeamRevealActive` | Legitimate | 1 | The approved seam design requires native keydown, keyup, and blur lifetime. Command hold semantics lack that lifecycle. |
| `src/panels/BottomDock.tsx` | `BottomDock` → `patchPanelLayout` | Legitimate | 1 | Persisted shell layout. |
| `src/panels/CubeSection.tsx` | `CubeSection` → `setAxisHint`, `setCubePanelTab`; `AxisHintZone` → `setAxisHint` | Legitimate | 3 | Axis hints and panel tabs are transient presentation state. |
| `src/panels/LeftRail.tsx` | `LeftRailTabs` → `setLeftRailTab` | Legitimate | 1 | Shell navigation state. |
| `src/panels/SceneSection.tsx` | `SceneSection` → `resetWorkbench`, `resetEditorSession` | Legacy | 2 | The reset intent predates the bus and remains a three call compound UI flow with a separate view reset command. |
| `src/panels/SceneSection.tsx` | `SceneSection` → `setBuildModeActive` | Lazy | 1 | `src/interaction/commands/mode.commands.ts:registerModeCommands` already registers `build-mode-toggle`. |
| `src/panels/SceneSection.tsx` | `SceneSection`, `RenderResolutionField`, `CameraFeelFields` → `patchPreferences` | Legitimate | 3 | Floor, axes, focus presentation, render resolution, and input feel are user preferences. |
| `src/panels/SelectionEditTargetToggle.tsx` | `SelectionEditTargetToggle` → `setPartEditTarget` | Legitimate | 1 | This chooses the inspector edit scope and leaves the document and selection unchanged. |
| `src/panels/SelectionSection.tsx` | `SelectionSection` → `clearSelectionSet` | Legacy | 1 | The control predates the accepted selection command path. `SelectorPanelHeader` already proves clearing can dispatch a `select` command. |
| `src/panels/SelectorPanel.tsx` | `SelectorPanelHeader` → `setSelectorTab` | Lazy | 1 | `selector-tab-toggle` already has validation and truthful rejection in the command registry. |
| `src/panels/StructureSection.tsx` | `StructureSection` → `setHoveredCube`, `setStructSliceAxis` | Legitimate | 2 | Hover synchronization and slice orientation are transient presentation state. |
| `src/panels/motion/MotionInspector.tsx` | `StateInspector` → `selectActiveState` | Lazy | 1 | State restoration is a document intent introduced after the bus and should be a registered command. |
| `src/panels/motion/MotionInspector.tsx` | `StateInspector` → `beginHistoryBatch`, `endHistoryBatch`; `StateComparisonControls` → `setMorphScrub` | Legitimate | 3 | Batch boundaries coordinate several accepted commands. Morph comparison is transient staging state. |
| `src/panels/motion/PieceMotionPanel.tsx` | `PieceMotionPanel` → `selectActiveState` | Lazy | 1 | Same bypass as `StateInspector`. |
| `src/panels/motion/PieceMotionPanel.tsx` | `PieceMotionPanel` → `beginHistoryBatch`, `endHistoryBatch`, `setTransportLoopWindow` | Legitimate | 3 | Batch boundaries and focus derived loop windows are transaction or session coordination. |
| `src/panels/motion/motionFocusController.ts` | `setFocus`, `syncStore` → `setMorphScrub` | Legitimate | 2 | The controller clears mutually exclusive transient comparison state when focus or selection changes. |
| `src/panels/useRetainedSelectionBuilder.ts` | `useRetainedSelectionBuilder` → `setSelectionQueryDraft` | Legitimate | 1 | The draft is transient builder restoration state; accepted query results still dispatch `select-query`. |
| `src/studio/CameraTrackControls.tsx` | `CameraTrackControls` → `beginHistoryBatch`, `endHistoryBatch` | Legitimate | 2 | The parked feature groups several accepted document commands into one history step. |
| `src/studios/editor/EditorStudio.tsx` | `useEditorAppModel` → `setHoveredCube` | Legitimate | 1 | Renderer hover feedback enters session state. |
| `src/studios/editor/MotionCapabilitySlots.tsx` | `MotionDockSlot` → `patchPanelLayout` | Legitimate | 1 | Persisted shell layout. |
| `src/studios/editor/useMotionCapability.ts` | `open` → `patchPanelLayout` | Legitimate | 1 | Capability activation opens the owning shell slot before loading it. |
| `src/studios/editor/usePanelDragCapability.ts` | `usePanelDragCapability` → `patchPanelPlacement` | Legitimate | 1 | Persisted shell layout produced by the drag capability. |
| `src/transport/advanceTransportFrame.ts` | `advanceTransportFrame` → `setTransportTime`, `setTransportPlaying` | Legitimate | 2 | The renderer clock advances playback. User transport intents already enter through commands; routing each frame tick through the command bus would turn a clock sample into user intent. |

### Enrollment order

The five lazy flows have an existing command shape:

1. Route `src/app/useSceneOperations.ts:toggleCubeBuilt` through `createSceneEditorCommand`.
2. Route `src/panels/SceneSection.tsx:SceneSection` build changes through `createBuildModeToggleCommand`, or add an explicit set command if idempotent state is required.
3. Route `src/panels/SelectorPanel.tsx:SelectorPanelHeader` through the registered selector tab command.
4. Register one state activation command and use it from `src/panels/motion/MotionInspector.tsx:StateInspector`.
5. Reuse that command from `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel`.

The seven legacy flows need command payload support for compound reset, selection results, and reset history before enrollment can preserve behavior.

## 5. Duplication

Counts first: **19 capability clusters, expressed as 29 duplicate path and symbol pairs.** The count excludes ordinary JSX mapping callbacks and storage adapter implementations whose representations differ.

| Capability | Path and symbol pair or set | Finding |
| --- | --- | --- |
| Camera pose cloning | `src/domain/cameraOperations.ts:cloneCameraPose` ↔ `src/editor/commands.ts:clonePoseSnapshot` | Byte equivalent clone of `position`, `target`, `up`, and `zoom`. One clone belongs with `CameraPoseSnapshot`. |
| Edge state equality | `src/domain/selectionAspects.ts:areEdgeStatesEqual` ↔ `src/persistence/recordCodecs/compactPose.ts:sameEdge` | Same four fields compared independently. |
| Face state equality | `src/domain/selectionAspects.ts:areFaceStatesEqual` ↔ `src/persistence/recordCodecs/compactPose.ts:sameFace` | Same three fields compared independently. |
| Cube size equality | `src/domain/selectionAspects.ts:areSizesEqual` ↔ `src/persistence/recordCodecs/compactPose.ts:sameSize` | Same dimensions compared independently. |
| Exact `Vec3` equality | `src/domain/cameraOperations.ts:sameVec3` ↔ `src/domain/gridLayout.ts:isSameVec3`; `src/domain/cameraOperations.ts:sameVec3` ↔ `src/evaluation/sceneMorph.ts:isSameVec3`; `src/domain/cameraOperations.ts:sameVec3` ↔ `src/persistence/recordCodecs/compactPose.ts:sameVec3` | Four exact equality implementations. The epsilon comparison in `src/domain/cameraTrack.ts:sameVec3` is a different capability and is excluded. |
| Edge change map cloning | `src/domain/incrementalCubeRenderResolution.ts:cloneEdgeChanges` ↔ `src/domain/incrementalEdgeResolution.ts:cloneEdgeChanges` | Same map and set deep clone. Both are in `src/domain`. |
| Camera vector subtraction | `src/domain/cameraTrack.ts:subtract` ↔ `src/state/cameraTrackValidation.ts:subtract` | Same tuple algebra. |
| Camera vector cross product | `src/domain/cameraTrack.ts:cross` ↔ `src/state/cameraTrackValidation.ts:cross` | Same tuple algebra. |
| Camera vector length | `src/domain/cameraTrack.ts:length` ↔ `src/state/cameraTrackValidation.ts:length` | Same `Math.hypot` calculation. |
| Geometry dot product | `src/domain/exposure.ts:dotVec3` ↔ `src/domain/worldGeometry.ts:dotVec3` | Same reduce based dot product in one package. |
| Nearly ordered comparison | `src/domain/exposure.ts:isLessThanOrNearlyEqual` ↔ `src/domain/worldGeometry.ts:isLessThanOrNearlyEqual` | Same comparison in one package. |
| Orthographic camera guard | `src/camera/cameraDriverMath.ts:isOrthographicCamera` ↔ `src/pose/viewPose.ts:isOrthographicCamera` | Same Three type guard. |
| Perspective camera guard | `src/camera/cameraDriverMath.ts:isPerspectiveCamera` ↔ `src/pose/viewPose.ts:isPerspectiveCamera` | Same Three type guard. |
| JSON parse with null fallback | `src/persistence/indexedDbFailureValidation.ts:parseJson` ↔ `src/persistence/storedOutbox.ts:parseJson` | Byte equivalent decoder. |
| Boolean fallback | `src/state/panelLayoutNormalization.ts:booleanOr` ↔ `src/state/preferencePort.ts:booleanOr` | Byte equivalent guard and fallback. |
| Selected cube IDs | `src/view/selectionFocus.ts:getSelectedCubeIds` ↔ `src/domain/selection.ts:getSelectedCubeIds` | The domain function explicitly claims single source ownership. The view rebuilds the set locally. |
| Cube size tuple | `src/domain/cubeGeometry.ts:toSizeVector` ↔ `src/scene/selectionChromeInstances.ts:cubeSizeToVector` | Same width, height, depth tuple conversion. |
| Edge claim key | `src/domain/edgeClaimResolution.ts:getEdgeClaimKey` ↔ `src/evaluation/sharedEdgeTweens.ts:getSharedEdgeClaimKey` | Same `${cellId}:${edgeId}` identity. |
| Nonnegative integer validation | `src/state/authoredOperationValidation/shared.ts:isNonnegativeInteger` ↔ `src/state/cameraTrackValidation.ts:isValidCameraTime` | Same finite, integer, and lower bound checks. |
| Plain object guard | `src/state/jsonGuards.ts:isJsonObject` ↔ `src/persistence/storageRecordReads.ts:isObject` | Same object, nonnull, nonarray guard. |
| JSON parse with original bytes fallback | `src/persistence/projectRecordHydrationProtocol.ts:parseRecord` ↔ `src/persistence/storageRecordReads.ts:storedValue` | Same parser and fallback semantics. |
| Listener set subscription | `src/app/horizontalScrollPanPort.ts:subscribe` ↔ `src/app/panelDragPort.ts:subscribe`; `src/app/horizontalScrollPanPort.ts:subscribe` ↔ `src/export/streamRecorder.ts:subscribe`; `src/app/horizontalScrollPanPort.ts:subscribe` ↔ `src/panels/motion/motionFocusController.ts:subscribe` | Same listener add and closure delete contract in four owners. |
| Lazy capability activation | `src/studios/editor/useMotionCapability.ts:activate` ↔ `src/studios/editor/useThumbnailCapability.ts:request` | Same prefetch, absent check, and activate request around `createLazyCapability`. |
| Strict grid coordinate validation | `src/state/authoredOperationValidation/shared.ts:isGridCoord` ↔ `src/state/workbenchValidation/pose.ts:isCurrentGridCoord` | Both require an object with only `x`, `y`, and `z`, each finite. |
| Cube operation vocabulary | `src/domain/sceneOperationMaterialization.ts:isCubeOperation` ↔ `src/state/authoredOperationValidation/scene.ts:isCubeOperation` | The kind set is declared independently in the materializer and unknown input validator. A shared kind vocabulary removes drift while validation remains local. |

The table has 25 rows because multi symbol clusters are shown by individual capability. It represents 19 consolidation clusters and 29 canonical owner to duplicate pairs.

The shaping work directly expands four duplicated contracts: edge equality, exact vector comparisons used by geometry, cube size tuple conversion, and cube operation validation. Adding `treatment` and `shapeSize` independently to both edge equality implementations would extend existing drift.

## 6. Dead code

Counts first:

- **1 lost feature cluster:** 3 source modules or symbols.
- **12 unreferenced declaration residues:** no source or test caller beyond an optional barrel export.
- **1 source helper reached only by tests after its production algorithm was replaced.**
- **1 forward declared feature seam with tests and a named future consumer.**
- **1 dormant model contract that has never affected behavior.**

Every item below was checked with `git log -S<symbol>` before classification.

### Lost feature

| Path and symbol | Reachability | History verdict |
| --- | --- | --- |
| `src/studio/CameraTrackControls.tsx:CameraTrackControls` | Tests only. No production importer or mount. | **Lost feature, parked.** Camera controls were mounted from `StripControls` before `6403128`. The Piece Motion cutover removed `StripControls`, moved the controls under `src/studio`, and left no replacement mount. |
| `src/studio/cameraCapture.ts:createCameraCapture` | Reached only by the unmounted controls and their tests. | Part of the same lost feature. |
| `src/studio/index.ts` | Tests only. | Barrel for the same lost feature. |

The camera track model, commands, evaluation, and renderer support remain in production. The missing element is user reachability.

### Unreferenced declaration residue

| Path and symbol | History verdict |
| --- | --- |
| `src/domain/cube.ts:areAllCubeEdgesVisible` | Was used by the original primitive edge toggle. `9786f4e` replaced that control with layer mode and left the function. Superseded residue. |
| `src/domain/cube.ts:setCubeEdgesVisible` | Was called by the same original toggle. `9786f4e` replaced it with `setAllCubeEdgesState`. Superseded residue. |
| `src/domain/cube.ts:areAllCubeFacesVisible` | Introduced with layer controls in `9786f4e`; no caller appears in history. Dead from introduction. |
| `src/domain/worldGeometry.ts:worldBoxContainsCorners` | Introduced in `6f9a58c`; no caller appears in history. Dead from introduction. |
| `src/domain/cubeRenderResolution.ts:getCubeRenderResolutionPasses` | Production use existed in `0ea8573`; `1458bf2` replaced the full pass algorithm with the incremental owner and left the export. Superseded residue. |
| `src/domain/scene.ts:applyGridPresetWithResult` | Had an application consumer; `2aa9362` moved the flow to authored persistence operations and left the export. Superseded residue. |
| `src/domain/selection.ts:isCubeSelected` | Used by the old per cube selection chrome. `43fff38` replaced that path with `createCubeSelectionIndex` and left the export. Superseded residue. |
| `src/persistence/recordCodecs/localCheckpointRecordCodec.ts:decodeLocalCheckpointRecord` | Introduced in `2aa9362`; no caller appears in history. Dead from introduction. |
| `src/state/selectionAssembly.ts:clearJournalFutures` | Introduced in `b4839c8`; no caller appears in history. Dead from introduction. |
| `src/theme/themeTokens.ts:ThemeAlphaTokenName` | Introduced in `6aa6cd9`; no consumer appears in history. Dead type alias. |
| `src/theme/themeTokens.ts:ThemeColorTokenName` | Introduced in `6aa6cd9`; no consumer appears in history. Dead type alias. |
| `src/capabilities/catalogData.ts:CapabilityId` | Introduced in `33a688b`; no consumer appears in history. The catalog value is live through `viteStudioPreloads.ts`; only the exported type is dead. |

### Test only source residue

`src/domain/resolvedRenderClosure.ts:collectResolvedChangeClosure` is imported only by `tests/authoredRenderImpactClosure.test.ts`. It was part of the production classifier in `0ea8573`. `1458bf2` moved closure ownership into `src/domain/incrementalCubeRenderResolution.ts` and removed the production import while retaining one standalone algorithm test. History shows that the replacement preserved the feature. The current source helper is a test oracle in a production directory.

### Forward declaration

`src/thumbnail/assetPoster.ts:resolveAssetPosterState` and `resolveAssetThumbnailSet` have no production caller. `git log -S` shows they were introduced in `1839b13` and never mounted. They are tested, live in the thumbnail package, and have the planned Browser studio as a named consumer. History classifies them as forward code. No product path was removed. Without scheduled Browser work, the present code has no runtime value.

### Dormant model contract

`src/domain/grid.ts:GridOverflow` and `GridFormat.overflow` were introduced in `5f70895`. Source clones, persists, validates, and morphs the value. No layout, placement, culling, or renderer symbol branches on `allow`, `clamp`, or `hide`. History contains no former honoring path. The metadata has been unhonored since introduction.

### Action

The first structural cleanup can remove the 12 unreferenced residues and move `collectResolvedChangeClosure` into test support without changing product behavior. `CameraTrackControls` requires a product decision because deletion would formalize the existing regression, while mounting it would restore a previously reachable capability. `GridOverflow` requires either an implementation contract or deletion from the model and codecs.
