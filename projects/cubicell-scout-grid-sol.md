# Cubicell grid and face content contracts scout

Snapshot: `main` at `3725921ae23cd4088b3891b310889c8861ca05eb`.

Scope: read only survey of current grid, cell, face, persistence, authoring, and render contracts.

## Reuse Map

### 1. Current domain carrier

| Owner | Structural contract | Content consequence |
|---|---|---|
| `src/domain/grid.ts:GridState` | Contains only `format`. `GridFormat` owns cell size, gap, per interval gap overrides, and origin. | Grid layout carries no face content policy. |
| `src/domain/scene.ts:CubicellScene` | Contains `cells: CubeCell[]` beside `grid`, frame, polarity, projection, and score. | Cell content travels with cells, independent of grid formatting. |
| `src/domain/cube.ts:CubeCell` | Contains identity, placement, size, visibility, twelve edges, and six faces. | The cell is the current content carrier. |
| `src/domain/cubeTopology.ts:cubeFaceIds` | Fixes the addressable surfaces to front, back, left, right, top, and bottom. | Every cube has six typed face slots. |
| `src/domain/cube.ts:CubeFaces` | `Record<CubeFaceId, CubeFaceState>`. | Every face has its own authored state. |
| `src/domain/cube.ts:cubeFaceStateOwner` | Required `color`, `opacity`, and `visible`; optional `figure`. | A face structurally supports one optional figure in addition to base material state. |
| `src/domain/cube.ts:CubeFaceFigure` | Exactly `{ stencilId, region, color, fit }`. `stencilId` must be a content addressed `StencilId`. | The optional content slot is closed around a two colour SVG stencil. It cannot represent an image texture, video, or shader reference. |
| `src/domain/stencil.ts:StencilAsset` | Exactly `{ byteLength, id, kind: "stencil", mediaType: "image/svg+xml", name }`. | The Library record stores metadata. It stores no SVG source or binary payload. |

`src/domain/gridLayout.ts:createSceneGridLayout` calculates transforms from `GridState`, placement, and cell size. It never reads a face. `src/domain/cubeGeometry.ts:createCubeFacePlanes` creates one rectangular plane per visible face and reads only face colour and opacity. The grid and layout contracts are therefore content agnostic. The content ceiling begins in `CubeFaceFigure` and continues through assets and rendering.

### 2. Current stencil path, end to end

1. `src/panels/Inspector.tsx:Inspector` and `src/panels/SelectorPanel.tsx:ModifyTab` both reuse `src/panels/PartSection.tsx:FaceSection`.
2. `src/panels/panelDefinitions.ts:faceBindingIds` exposes visible, colour, stencil, and opacity. `src/panels/ControlBindingField.tsx:ControlBindingField` can render boolean, enum, and number controls.
3. `src/editor/controlBindings.ts:faceStencilBinding` offers only `seededStencils`. Its preparation command inserts the chosen `StencilAsset` into the Library, then its scene command writes `patch.figure` through `set-face-state`.
4. `src/domain/cubeOperations.ts:CubeOperation` carries `CubeFaceStatePatch`; `src/domain/cube.ts:setCubeFaceState` delegates validation, equality, patching, morph classification, compact encoding, and render impact to `cubeFaceStateOwner`.
5. `src/domain/workbench.ts:Library` owns persisted stencil metadata in `library.stencils`. `src/domain/workbench.ts:getProjectAssetRoster` exposes those entries to the Project manifest.
6. `src/persistence/projectRecordProjection.ts:projectWorkbenchRecords` writes a `StencilRecord` and pose records. `src/persistence/projectRecordHydration.ts:hydrateProjectRecords` reconstructs the Library and poses.
7. `src/scene/cubeInstances.ts:createCubeCellInstances` copies `face.figure` into `CubeFaceInstance.figure`.
8. `src/scene/instancedPartMeshCore.ts:InstancedFaceFigure` carries it to the shared face mesh. `src/scene/instancedPartMeshCore.ts:writeStencil` packs it into one four float instance attribute.
9. `src/scene/faceStencilShader.ts:writeFaceStencilAttribute` converts the stencil ID to a fixed atlas slot and packs figure colour plus slot, region, and fit flags. `src/scene/faceStencilShader.ts:fragmentPartition` samples one R8 alpha atlas and mixes two colours.
10. `src/scene/stencilAtlas.ts:createStencilAtlas` builds one 2048 square `DataTexture` from bundled `seededStencils`. It has sixteen deterministic slots. It does not read `workbench.library.stencils`.
11. `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` and `src/thumbnail/thumbnailRenderer.ts:createOrthographicThumbnailRenderer` reuse the same atlas and face renderer.

This is a coherent stencil pipeline. It already provides the correct owner chain for a richer face value. Reuse `cubeFaceStateOwner`, `set-face-state`, Project asset projection, and the instance slot registry. Do not add content to `GridState`.

### 3. Persistence wire and versions

| Layer | Version | Current face or asset fields |
|---|---:|---|
| IndexedDB database | `src/persistence/indexedDbSchema.ts:indexedDbProjectStorageVersion` = 9 | An upgrade recreates every store. This is the intended single user reset lever. |
| Stored Project and asset row wrapper | `src/persistence/storageRecordTypes.ts:committedRecordSchemaVersion` = 3 | `StoredAssetBytes` stores `kind` and JSON `documentBytes`; there is no asset payload store. |
| Project record | `src/persistence/recordCodecs/projectRecordCodec.ts:projectRecordSchemaVersion` = 2 | `assets[*] = { id, kind, revision }`; allowed kinds are animation, stencil, and structure. |
| Stencil record | `src/persistence/recordCodecs/stencilRecordCodec.ts:stencilRecordSchemaVersion` = 1 | `document` is the metadata only `StencilAsset`. |
| Structure record | `src/persistence/recordCodecs/structureRecordCodec.ts:structureRecordSchemaVersion` = 2 | Stores State references. Face state lives in separate pose revisions. |
| Pose revision record | `src/persistence/recordCodecs/poseRevisionRecordCodec.ts:poseRevisionRecordSchemaVersion` = 3 | `document` is `CompactPose`. |
| Working draft record | `src/persistence/recordCodecs/draftRecordCodec.ts:draftRecordSchemaVersion` = 3 | `document.workingPose` is the same `CompactPose`. |
| Authored operation | `src/domain/authoredOperations.ts:authoredOperationSchemaVersion` = 4 | A scene operation carries `body.operations[*].patch.figure`. |
| Outbox record | `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:outboxCommitRecordSchemaVersion` = 3 | `operations[*].operation` contains the authored operation. |
| Local history step | `src/persistence/recordCodecs/localHistoryRecordCodec.ts:localHistoryStepSchemaVersion` = 1 | `ops[*]` is an RFC 6902 diff and can contain face figure values or Library asset values. |

`src/persistence/recordCodecs/compactPose.ts:CompactPose` stores `c` cells, `f` frame ID, `g` grid, `p` polarity, and `r` projection. Each compact cell has nine positions. Position 8 is the list of nondefault faces. `src/persistence/recordCodecs/compactPose.ts:encodeCell` currently writes each face as:

```text
[faceIndex, colorIndex, opacity, visibleBit, figure?]

figure = [stencilId, regionIndex, colorIndex, fitIndex]
```

The exact nested wire path is `PoseRevisionRecord.document.c[*][8][*]`, and the same path sits below `DraftRecord.document.workingPose`. A default face is omitted. A face with content includes all three required state fields plus the trailing figure tuple.

### 4. Exact contract changes for image, video, or shader references

The smallest durable change replaces the stencil specific optional face value with one discriminated face content value. Pre release reset semantics make a clean replacement preferable to parallel `figure` and `content` paths.

#### Face value and compact wire

- Replace `src/domain/cube.ts:CubeFaceFigure` with a closed `CubeFaceContent` union that names the reference kind and ID. Image and video variants need fit or crop policy. A shader variant needs a shader ID and a validated parameter value contract.
- Replace `src/domain/cube.ts:cubeFaceStateOwner` field `figure` with `content`. Reuse `defineCubePartStateField` for validation, equality, inheritance, morph policy, compact encoding, and render impact.
- Replace `src/domain/cube.ts:isCubeFaceFigure`, `encodeCubeFaceFigure`, `decodeCubeFaceFigure`, `isEncodedCubeFaceFigure`, and `canTweenCubeFaceFigureColor` with the union equivalents.
- Change compact face position 4 from the stencil tuple to a discriminated content tuple. For example, the first content tuple value must identify stencil, image, video, or shader before the reference ID and variant fields.
- Bump `poseRevisionRecordSchemaVersion` and `draftRecordSchemaVersion`. Bump `indexedDbProjectStorageVersion` for the authorized reset. Bump `committedRecordSchemaVersion` if the stored row contract changes.
- Bump `authoredOperationSchemaVersion`, `outboxCommitRecordSchemaVersion`, and `localHistoryStepSchemaVersion` because pending scene patches and history values can carry the old object shape.

Derived types `CubeFaceState`, `CubeFaceStatePatch`, and `CubeFaceStateRenderAttribute` then update from the owner. `src/state/workbenchValidation/pose.ts:isCurrentFaceState`, `src/state/authoredOperationValidation/scene.ts:isPartPatch`, `src/domain/selectionAspects.ts:attributeAspects`, `src/domain/authoredRenderImpact.ts:changedFaceAttributes`, and `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology` already delegate to that owner. They should remain shared consumers rather than gain variant specific branches.

#### Project owned asset references

A face can hold a syntactically valid reference after the face change alone. A reloadable, resolvable reference also requires these asset contracts:

- Extend `src/domain/project.ts:ProjectAssetKind` with the chosen asset kinds.
- Add the asset metadata types and validated IDs beside `src/domain/stencil.ts:StencilAsset`, or replace the stencil only type with a shared, discriminated face content asset contract.
- Extend `src/domain/workbench.ts:Library`, `emptyLibrary`, `getProjectAssetRoster`, and asset lookup helpers.
- Extend `src/state/workbenchValidation/assets.ts` validators and readers, plus `src/state/workbenchValidation/aggregate.ts:completePersistedWorkbench`.
- Extend `src/domain/workbenchOperations.ts:DocumentOperation`, `src/domain/authoredInverse.ts:deriveInverseBody`, `src/domain/documentRestoreOperations.ts:DocumentRestoreOperation`, `src/state/authoredOperationValidation/document.ts:isDocumentOperation`, `src/state/actions/authoredReducer.ts:applyProjectBody`, `src/state/actions/localAuthoring.ts:resolveOperationTarget`, and `src/state/projectStorageChangeSet.ts:insertedAssetId` and `removedAssetId`.
- Extend `src/state/projectAssetLibrary.ts:isProjectAssetLoaded` and `mergeProjectAssetLibrary`.
- Extend `src/persistence/recordCodecs/projectRecordCodec.ts:decodeProjectRecord` so the Project roster accepts the new kinds. Bump `projectRecordSchemaVersion`.
- Add versioned record codecs beside `stencilRecordCodec`, then extend `src/persistence/projectRecordProjection.ts:projectWorkbenchRecords`, `src/persistence/projectRecordHydration.ts:decodeAssets`, `src/persistence/storageRecordPreparation.ts:prepareAssets`, and `src/persistence/storageRecordReads.ts:assetValue`.

Several of those consumers currently use exhaustive switches. Two persistence paths use a final stencil fallback. Adding a kind without changing them would make the new record decode as a stencil or disappear from projection.

`StoredAssetBytes.documentBytes` is JSON metadata. No current store owns image bytes, video bytes, shader source, or an external resource locator. A usable imported asset therefore needs a payload owner and lifecycle in addition to metadata. Content addressed immutable bytes fit the current `StencilId` direction, but the actual bytes still need storage and resolution.

#### Render consumers that break

| Reference | Reusable surface | Required break or extension |
|---|---|---|
| Image or general texture | Existing rectangular plane, UVs, instance slot registry, opacity path, thumbnails | Replace `CubeFaceInstance.figure` and `InstancedPart.figure`; add a content instance attribute; resolve and own texture resources; implement fit or crop; update dirty attribute classification. Distinct per face textures need an atlas, texture array, or batching policy. |
| Video | Same plane and UV geometry | Add deterministic time and playback ownership, video resource creation and disposal, frame invalidation, pause and scrub policy, and deterministic thumbnail frame selection. A static R8 atlas cannot carry a live stream. |
| Shader | Existing face transform and selection geometry | Define a bounded program and uniform contract. Arbitrary per face programs conflict with `src/scene/instancedPartMeshCore.ts:createInstancedPartMeshWithGeometry`, which owns one `MeshBasicMaterial` for the whole face batch, and with `src/scene/faceStencilShader.ts:faceStencilProgramKey`, which fixes one compiled program. Shader variants require batching by program or one shared program with per instance parameters. |

All three variants affect these current consumers:

- `src/scene/cubeInstances.ts:CubeFaceInstance` and `createCubeCellInstances`
- `src/scene/instancedPartMeshCore.ts:InstancedFaceFigure`, `InstancedPart`, `writeStencil`, and patch upload logic
- `src/scene/instanceSlotRegistry.ts:InstanceSlotAttribute` and `changedAttributes`
- `src/scene/faceStencilShader.ts:applyFaceStencilShader` and `writeFaceStencilAttribute`
- `src/scene/stencilAtlas.ts:StencilAtlas` and `createStencilAtlas`
- `src/scene/renderCubeScenePartLayers.tsx:renderCubeScenePartLayers`
- `src/scene/CubeScene.tsx:CubeScene`
- `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact`
- `src/thumbnail/thumbnailRenderer.ts:createOrthographicThumbnailRenderer`
- `src/editor/controlBindings.ts:ControlValue`, `ControlValueSchema`, `faceStencilBinding`, and `faceStencilOptions`
- `src/panels/panelDefinitions.ts:faceBindingIds`

The renderer is the largest constraint. It deliberately preserves one face draw, one material program, and one atlas texture. Image textures can preserve that envelope through an atlas or array. Live video and arbitrary shaders need a product decision about batching and program bounds.

## Quality Map

### Proven strengths

- `src/domain/cubePartStateOwner.ts:createCubePartStateOwner` centralizes validation, patches, structural equality, sparse compact encoding, inheritance, matching, morph classification, interpolation, and render attributes. This is the correct extension seam.
- `src/domain/cube.ts:cubeFaceStateOwner` accepts absent figure state, rejects malformed figures, and treats unresolved but syntactically valid stencil IDs as domain values.
- `src/editor/controlBindings.ts:faceStencilBinding` now inserts the seeded asset into the active Library before writing the reference. The authored face and Project asset ownership move together.
- `src/persistence/recordCodecs/result.ts:isRecordEnvelope` rejects unknown fields and unsupported versions for versioned records.
- `src/scene/instanceSlotRegistry.ts:changedAttributes` limits a figure edit to the stencil upload path.
- `src/scene/faceStencilShader.ts:applyFaceStencilShader` composes into the existing opacity material and holds one stable program and texture.
- Unit verification passed: `cubeFaceStateOwner`, Project record codecs, stencil assets, panels, and face stencil rendering, 69 tests total.
- Chromium verification passed: `stencilRendering.browser`, one test proving one draw, one stable texture and program, four float stencil patch upload, and resource disposal.

### Current capability ceilings

- `CubeFaceFigure` has no generic reference discriminant. It only names a `StencilId`.
- `StencilAsset` persists metadata only. `src/domain/seededStencils.ts:resolveStencilContent` resolves bundled SVG source, while the renderer bypasses it and reads `seededStencils` directly.
- `src/scene/stencilAtlas.ts:getStencilAtlasSlot` recognizes only bundled seeded IDs. A valid Library stencil with unavailable content remains explicit domain state and renders as no stencil.
- The atlas is one R8 alpha channel page with sixteen slots. It cannot encode full colour images or video.
- `fit` is persisted and packed by `writeFaceStencilAttribute`, but `fragmentPartition` contains no fit branch. Margin and bleed currently render identically.
- The face mesh uses one `MeshBasicMaterial` and one fixed shader composition. Arbitrary per face materials or shader programs are outside the current batch contract.
- Editor controls are static scalar or enum bindings. There is no dynamic Library browser, upload control, parameter editor, or media timeline for face content.
- The persistence store has no generic payload or blob owner for asset content.

### Searches supporting “none found” conclusions

The following searches found no face texture, video, shader asset, generic face content, shader material, video texture, or binary asset payload implementation. The only `DataTexture` match was the stencil atlas. Recording related video matches belong to export capture, not face content.

```text
rg -n --glob '*.{ts,tsx}' '\b(VideoTexture|CanvasTexture|TextureLoader|DataArrayTexture|Data3DTexture|CompressedTexture|ShaderMaterial|RawShaderMaterial|Mesh(Standard|Physical|Lambert|Phong)Material)\b' src tests
rg -n --glob '*.{ts,tsx}' '(texture|video|shader)(Id|Asset|Source|Reference|Content)|face(Content|Media|Texture|Video|Shader)' src tests
rg -n --glob '*.{ts,tsx}' -i 'video|texture asset|shader source|shader asset|face content|media asset|binary asset|asset payload' src tests
rg -n --glob '*.{ts,tsx}' 'new (DataTexture|VideoTexture|CanvasTexture|TextureLoader|ShaderMaterial|RawShaderMaterial)' src tests
rg -n --glob '*.{ts,tsx}' 'library\.stencils|findStencilAsset' src/scene src/thumbnail src/renderer
rg -n --glob '*.{ts,tsx}' 'resolveStencilContent\(' src tests
```

## Verdict on the hypothesis

Verdict: partially supported.

The product currently lacks a general face content model. A face can own base colour, opacity, visibility, and one optional two colour SVG stencil reference. Images, video, general textures, and shader references have no domain variant, Project asset kind, payload store, editor, or renderer lifecycle.

The grid layout engine is content agnostic. It positions cells and face planes without inspecting their content. The self imposed ceiling sits in the closed `CubeFaceFigure` contract, stencil only Project asset vocabulary, compact face tuple, and single material fixed atlas renderer.

The hypothesis identifies a real capability ceiling and assigns it to the wrong layer. The path of least resistance is to generalize the existing optional face value and asset owner chain, then choose a bounded renderer contract. No grid rewrite is indicated.
