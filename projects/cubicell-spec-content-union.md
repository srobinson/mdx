# Cubicell content union foundation specification

Snapshot: `main` at `3725921ae23cd4088b3891b310889c8861ca05eb` on 2026-08-09.

Status: implementation specification. Final variant names and fields must be reconciled with the text, image, and motion specifications before build approval.

## 1. Outcome

Replace the optional face `figure` value with one discriminated, location independent content union. Ship the stencil variant first. Make every persisted Stencil asset self contained, resolve it through the Project Library, and assign active stencils to the existing R8 atlas dynamically. Preserve the single authored writer, single GPU writer, one face draw, one material program, and one texture object.

The future cell model embeds the same canonical content value:

```ts
type ContentOccupant = {
  content: CubicellContent;
  kind: "content";
};
```

The later `CellOccupant` union includes this member beside Cube and Empty. This slice implements only `CubeFaceState.content`. It does not implement `CellOccupant` or change the grid.

## 2. Required inputs

Implementation begins from these inputs:

1. `~/.mdx/projects/cubicell-content-scout-synthesis.md`, especially its reuse map and settled forks.
2. `~/.mdx/projects/cubicell-scout-grid-sol.md`, especially the current owner chain and version inventory.
3. Repository decisions `Content direction: face media first, motion in scope`, `F1 resolved: motion via dynamic RGBA atlas, one-draw intact`, and `Product reframe: cell is a location, occupant is a union`.
4. Current source at the snapshot above. If the implementation head changes any named owner, resurvey that owner before editing.

## 3. Decisions bound

1. `CubeFaceFigure` is replaced. There is no compatibility alias at runtime, parallel `figure` field, dual codec, or migration.
2. `CubeFaceContent` is a semantic alias of one canonical `CubicellContent` union. The future `CellOccupant.Content` uses `CubicellContent` directly. Moving a value between carriers requires no conversion.
3. The first union member is Stencil content. Text, image, video, and generated motion members remain absent until their specifications define them.
4. Face media is the first product surface. Cell occupants remain outside this slice.
5. IndexedDB is bumped and reset. No old record migration is written.
6. The current one draw face invariant remains. Content stays inside the existing instanced face buckets.
7. Stencil source is part of `StencilAsset`. Seeded and Project supplied stencils use the same Library resolution path.
8. The R8 stencil atlas retains one texture object and gains dynamic slots for active Library stencils.
9. The inert `fit` field is removed. A later image specification may introduce defined contain, cover, crop, or focal semantics on its own variant.
10. Unknown but syntactically valid content references remain valid domain state and render empty until resolved.

## 4. Reuse map bindings

The implementation extends these owners:

| Concern | Binding |
|---|---|
| Face state | `src/domain/cube.ts:cubeFaceStateOwner`, `src/domain/cube.ts:setCubeFaceState` |
| Shared field behavior | `src/domain/cubePartStateOwner.ts:createCubePartStateOwner`, `src/domain/cubePartStateOwner.ts:defineCubePartStateField` |
| Stencil identity and payload | `src/domain/stencil.ts:StencilAsset`, `src/domain/stencil.ts:StencilId` |
| Library ownership | `src/domain/workbench.ts:Library`, `src/domain/workbench.ts:findStencilAsset`, `src/domain/workbench.ts:getProjectAssetRoster` |
| Seed catalog | `src/domain/seededStencils.ts:seededStencils`, `src/domain/seededStencils.ts:findSeededStencil` |
| Authoring | `src/editor/controlBindings.ts:faceStencilBinding`, `src/domain/workbenchOperations.ts:StencilDocumentOperation`, `src/state/actions/authoredReducer.ts:applyProjectBody` |
| Compact wire | `src/persistence/recordCodecs/compactPose.ts:encodeCell`, `src/persistence/recordCodecs/compactPose.ts:decodeCell` |
| Asset record | `src/persistence/recordCodecs/stencilRecordCodec.ts:encodeStencilRecord`, `src/persistence/recordCodecs/stencilRecordCodec.ts:decodeStencilRecord` |
| Instance derivation | `src/scene/cubeInstances.ts:createCubeCellInstances`, `src/scene/cubeInstances.ts:createCubeSceneInstances` |
| GPU writer | `src/scene/instancedPartMeshCore.ts:syncInstancedPartMesh`, `src/scene/instancedPartMeshCore.ts:patchInstancedPartMesh` |
| Face shader | `src/scene/faceStencilShader.ts:applyFaceStencilShader`, `src/scene/faceStencilShader.ts:writeFaceStencilAttribute` |
| Atlas | `src/scene/stencilAtlas.ts:createStencilAtlas`, `src/scene/stencilAtlas.ts:getStencilAtlasSlot` |
| Live ownership | `src/scene/CubeScene.tsx:useOwnedStencilAtlas`, `src/scene/CubeScene.tsx:StencilAtlasReadyDriver` |
| Incremental dirtiness | `src/scene/instanceSlotRegistry.ts:changedAttributes` |
| Morph | `src/evaluation/sceneMorph.ts:createPartColorTweens`, `src/evaluation/scoreAt.ts:CubePartColorTweens` |
| Thumbnail parity | `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact`, `src/thumbnail/thumbnailRenderer.ts:createOrthographicThumbnailRenderer`, `src/thumbnail/thumbnailCache.ts:createStateThumbnailCache` |
| Browser invariant | `tests/stencilRenderingBrowserDriver.ts:runStencilRenderingBrowserGate`, `tests/webGlResourceObserver.ts:observeWebGlResources` |
| Delivery | `budgets/initial-delivery.json:deliveries`, `scripts/check-delivery-budget.mjs:checkDelivery` |

No second state owner, resolver, atlas, renderer layer, asset registry, or persistence route is permitted.

## 5. Canonical content contract

Create a narrow domain module, preferably `src/domain/content.ts:CubicellContent`, which owns the union, strict validation, compact variant encoding, equality helpers, and morph eligibility.

```ts
export const stencilContentRegions = ["form", "field"] as const;

export type StencilContent = {
  color: CubePartColor;
  kind: "stencil";
  region: (typeof stencilContentRegions)[number];
  stencilId: StencilId;
};

export type CubicellContent = StencilContent;

export type CubeFaceContent = CubicellContent;
```

`CubicellContent` is the canonical union. `CubeFaceContent` expresses the current carrier without creating a second representation. Later specifications extend `CubicellContent` with complete variant types and leave the alias unchanged.

The union has these rules:

1. `kind` is required and uses a string discriminant in memory.
2. Every member is strict. Missing fields, unknown fields, invalid indexes, and invalid identifiers are rejected.
3. Content carries its own visual meaning. It contains no cube ID, face ID, grid coordinate, selection state, atlas slot, runtime handle, or resolved browser resource.
4. Runtime and cache fields belong to derived scene instances or atlas owners.
5. A syntactically valid unresolved `stencilId` remains valid content.
6. Colour can tween only when both values are Stencil content with the same `stencilId` and `region`. Every structural change remains a discrete cut.

Replace `cubeFaceStateOwner.fields.figure` with `cubeFaceStateOwner.fields.content`. Rename its render attribute from `stencil` to `content`. Preserve optional clear semantics: `{ content: null }` canonicalizes to the absent field, while `{ content: undefined }` is invalid.

Delete the old names throughout the owner chain:

`CubeFaceFigure`, `isCubeFaceFigure`, `encodeCubeFaceFigure`, `decodeCubeFaceFigure`, `isEncodedCubeFaceFigure`, `canTweenCubeFaceFigureColor`, `InstancedFaceFigure`, every `.figure` field, the `figures` tween map, and the `stencil` instance dirty attribute.

Use the corresponding content names. No deprecated export remains.

## 6. Compact wire

Keep the optional content value at face position 4. Add the discriminant inside that value.

```text
face = [faceIndex, colorIndex, opacity, visibleBit, content?]
content = [contentKindIndex, ...variant]
stencil = [0, stencilId, regionIndex, colorIndex]
```

The exact persisted paths remain:

```text
PoseRevisionRecord.document.c[*][8][*]
DraftRecord.document.workingPose.c[*][8][*]
```

Rules:

1. Content kind indexes are append only after this reset. `0` is Stencil.
2. The encoder writes no placeholders for future variants.
3. A default face remains omitted from `CompactPose`.
4. The decoder rejects the old undiscriminated figure tuple.
5. The decoder rejects the removed fit index, unknown kind indexes, extra tuple members, and malformed variant fields.

## 7. Stencil payload and one resolution owner

Extend `src/domain/stencil.ts:StencilAsset` to be self contained:

```ts
export type StencilAsset = {
  byteLength: number;
  id: StencilId;
  kind: "stencil";
  mediaType: "image/svg+xml";
  name: string;
  source: string;
  sourceRegion: (typeof stencilContentRegions)[number];
};
```

`src/state/workbenchValidation/assets.ts:isStencilAsset` must require exactly these fields. `byteLength` must equal the UTF-8 byte length of `source`. Seed construction and import construction must derive `id` from the exact source through `src/domain/stencil.ts:createStencilId`. The existing seeded identity test remains the cryptographic assertion for bundled assets.

Move content resolution to the Library owner. The public contract is:

```ts
type StencilContentResolution =
  | { asset: StencilAsset; kind: "resolved" }
  | { kind: "unresolved"; stencilId: StencilId };

function resolveStencilContent(
  library: Pick<Library, "stencils">,
  stencilId: StencilId,
): StencilContentResolution;
```

`src/domain/workbench.ts:resolveStencilContent` calls the same Library lookup as every other stencil consumer. `src/domain/seededStencils.ts:seededStencils` becomes an authoring catalog only. Each seed owns one complete `StencilAsset` and its default `StencilContent` fields. The renderer and thumbnail code must have no import from `src/domain/seededStencils.ts:seededStencils`.

Do not export source bearing seed values through `src/domain/index.ts:exports`. `src/editor/controlBindings.ts:faceStencilBinding` imports the seed catalog directly from `src/domain/seededStencils.ts:seededStencils`. Type exports and the Library resolver may remain in the domain barrel.

Persistence remains on `src/persistence/recordCodecs/simpleAssetRecordCodec.ts:SimpleAssetRecord`. The complete asset, including SVG source and canonical source region, is the Stencil record document. This solution is specific to small SVG strings. Later binary assets require a payload store and must not use base64 inside `CompactPose`, authored operations, or JSON metadata.

## 8. Dynamic R8 atlas

Refactor `src/scene/stencilAtlas.ts:createStencilAtlas` into a stable runtime owner. It retains the current 2048 square R8 `DataTexture`, sixteen 512 square slots, one pixel gutter, linear filtering, and disabled mipmaps.

The atlas contract must provide:

1. `sync(library, referencedStencilIds)`, which resolves every active ID through `src/domain/workbench.ts:resolveStencilContent`.
2. `getSlot(stencilId)`, which reads only the atlas owned slot map.
3. A readiness or subscription signal for each synchronization generation.
4. One idempotent `dispose` operation.

Synchronization behavior:

1. Collect referenced Stencil IDs from the current scene or thumbnail pose in stable cell and `cubeFaceNames` order. Library entries that no rendered content references consume no slot.
2. Retain slots for IDs that remain active. Free removed IDs. Assign new resolved IDs to the lowest available slots.
3. Rasterize `asset.source` and normalize `asset.sourceRegion` to canonical form coverage through the existing Canvas 2D path.
4. Write pixels into the existing typed array and mark the existing texture dirty. Do not replace the texture.
5. Use a generation token. A completed stale raster job must not overwrite a newer synchronization.
6. An unresolved ID receives no slot and renders the base face.
7. More than sixteen simultaneously referenced resolved stencils is explicit overflow. Return the overflow IDs, render those references empty, and report one diagnostic per synchronization. Never alias two IDs to one slot.
8. Completion wakes demand rendering and causes the content instance attribute to replay. Mesh, material, program, and texture identities remain stable.

`src/scene/CubeScene.tsx:useOwnedStencilAtlas` receives the active `Library` and scene references, runs synchronization, and exposes its generation to the face instance writer. `src/scene/CubeScene.tsx:StencilAtlasReadyDriver` invalidates the demand renderer after the current generation completes and ignores stale completions.

The shared renderer contract must receive the existing `Library` owner. Add `library: Library` to `src/renderer/contract.ts:SharedRendererCanvasProps`. `src/studios/editor/EditorRendererBinding.tsx:EditorRendererBinding` reads that exact object from the store. Avoid a copied stencil registry.

Thumbnails receive the same Library. `src/thumbnail/thumbnailRenderer.ts:createOrthographicThumbnailRenderer` awaits atlas synchronization before constructing and rendering the artifact. `src/thumbnail/thumbnailCache.ts:createStateThumbnailCache` keys output by Pose identity and the relevant `library.stencils` collection identity so a formerly unresolved asset cannot leave a stale cached thumbnail. Unrelated Library edits do not invalidate Stencil thumbnails.

## 9. Shader and instance path

Generalize the current face patch owner now, without adding dormant media branches.

1. Rename `faceStencilShader.ts` to `faceContentShader.ts`.
2. Rename its exported attribute, program key, apply, read, and write symbols from Stencil to Content.
3. Rename `instanceFaceStencil` to `instanceFaceContent` and use a fixed program key such as `cubicell-face-content-v1`.
4. Keep one packed `vec4`: resolved Stencil colour in RGB and slot plus region in the fourth component. Remove the unused fit bit.
5. `src/scene/instancedPartMeshCore.ts:syncInstancedPartMesh` and `src/scene/instancedPartMeshCore.ts:patchInstancedPartMesh` remain the sole attribute writers. Each calls one content writer.
6. `src/scene/instanceSlotRegistry.ts:changedAttributes` emits `content` when derived content changes.
7. A content only patch uploads exactly four floats and no matrix, base colour, or opacity data.
8. Keep one `MeshBasicMaterial` per existing face bucket and one composed `onBeforeCompile` program.

The shader contains only the Stencil branch in this slice. Later specifications extend this owner with fixed samplers and variant flags after their contracts are approved.

## 10. Fit disposition

Remove `fit` from domain state, compact encoding, seeds, morph identity, instance data, shader packing, tests, and editor defaults.

History evidence:

```text
git log --all -S'cubeFaceFigureFits' -- src/domain/cube.ts
git log --all -S'figure.fit' -- src/domain/cube.ts src/scene/faceStencilShader.ts src/evaluation/sceneMorph.ts tests
git log --all -S'fitFlag' -- src/scene/faceStencilShader.ts
```

All three searches return only `c32bb726 feat(scene): render seeded SVG stencils on cube faces (#164)`. That commit introduced the field, tuple index, bit packing, and tests together. `src/scene/faceStencilShader.ts:fragmentPartition` never reads the fit bit, and `src/scene/stencilAtlas.ts:rasterizeSvgAlpha` always stretches the SVG across the same slot. No observable margin or bleed contract exists.

Inventing an inset constant now would create product behavior without a requirement. The clean reset removes the field. Image fit and crop semantics belong to the image variant review.

## 11. Version plan

| Owner | Current | Foundation | Reason |
|---|---:|---:|---|
| `src/persistence/indexedDbSchema.ts:indexedDbProjectStorageVersion` | 9 | 10 | Authorized reset for every changed record |
| `src/persistence/recordCodecs/poseRevisionRecordCodec.ts:poseRevisionRecordSchemaVersion` | 3 | 4 | Compact face tuple changes |
| `src/persistence/recordCodecs/draftRecordCodec.ts:draftRecordSchemaVersion` | 3 | 4 | Working pose uses the same tuple |
| `src/domain/authoredOperations.ts:authoredOperationSchemaVersion` | 4 | 5 | Scene patches rename `figure` to `content`; Stencil asset payload expands |
| `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:outboxCommitRecordSchemaVersion` | 3 | 4 | Outbox embeds authored operations |
| `src/persistence/recordCodecs/localHistoryRecordCodec.ts:localHistoryStepSchemaVersion` | 1 | 2 | JSON patches can contain both changed values |
| `src/persistence/recordCodecs/stencilRecordCodec.ts:stencilRecordSchemaVersion` | 1 | 2 | Stencil document gains source and source region |
| `src/persistence/recordCodecs/localHistoryRecordCodec.ts:localHistoryRecordSchemaVersion` | 4 | unchanged | The spine envelope is unchanged |
| `src/persistence/recordCodecs/projectRecordCodec.ts:projectRecordSchemaVersion` | 2 | unchanged | The roster still carries `stencil` ID, kind, and revision |
| `src/persistence/storageRecordTypes.ts:committedRecordSchemaVersion` | 3 | unchanged | The stored row wrapper and JSON byte field are unchanged |
| `src/persistence/recordCodecs/structureRecordCodec.ts:structureRecordSchemaVersion` | 2 | unchanged | Structure records do not embed face state |

Strict decoders reject every old version. `src/persistence/indexedDbSchema.ts:createIndexedDbProjectSchema` recreates stores at version 10. No migration, fallback decoder, or legacy field adapter remains.

## 12. Requirements intake for specifications 2 through 4

The downstream specifications must reconcile their final fields against this canonical union before implementation. This section records likely demands without predeclaring dormant members.

| Medium | Likely union requirements | Foundation constraint |
|---|---|---|
| Text | Text string, system or asset font reference, size, horizontal and block alignment, colour, direction, language, explicit newline and overflow policy | Location independent JSON value; Canvas raster output is derived; system fonts add no asset payload; project fonts use the future payload store |
| Image | Content addressed image ID, defined contain or cover policy, optional focal position if approved, deterministic decode and colour space | Binary bytes stay in the payload owner; the union stores a reference and authored presentation only; RGBA atlas runtime fields stay derived |
| Video | Content addressed video ID, poster policy, deterministic playhead mapping, loop or hold policy | Playback handles, decoder state, video elements, and atlas slots remain runtime state; demand rendering uses named producers |
| Generated motion | Seeded generator or shader ID plus a bounded, strictly validated parameter value | No arbitrary shader source in face state; one fixed face program samples generated RGBA atlas pixels |
| All kinds | Stable discriminant, strict validation, compact tuple, clear semantics, unresolved reference behavior, morph policy, thumbnail answer, recording answer | Extend `CubicellContent`, `cubeFaceStateOwner`, the one compact content codec, the one instance writer, and the one face shader owner |

Review must settle:

1. Exact variant names and append only wire indexes.
2. Which fields are intrinsic content versus carrier presentation.
3. Shared colour policy across face and standalone occupant rendering.
4. Variant specific structural identity for colour tween eligibility and discrete cuts.
5. Payload IDs and the binary payload owner shared by image, video, and project fonts.
6. Atlas capacity and eviction policy for R8 text masks and the RGBA media page.
7. Deterministic poster and recording semantics for animated sources.

No later specification may create `CubeFaceText`, `CellImageContent`, or another carrier specific union that duplicates `CubicellContent`.

## 13. Exact deliverables

1. Add the canonical content domain module and export its public types and helpers.
2. Replace `figure` with `content` across domain, operations, validation, compact persistence, selection, inheritance, morph, scene instances, thumbnails, editor bindings, and tests.
3. Remove every old Figure symbol and fit field. Repository search for `CubeFaceFigure`, `.figure`, `figures`, `cubeFaceFigureFits`, and `fitFlag` returns no production matches.
4. Put SVG source and canonical source region on `StencilAsset`; keep Library insertion, deletion, projection, hydration, history, and storage on their current owners.
5. Move `resolveStencilContent` to the Library owner and remove every renderer read of `seededStencils`.
6. Make the current R8 atlas a dynamic active reference cache with stable texture identity, generation safety, explicit overflow, and demand invalidation.
7. Generalize the single shader and instance attribute names to Content with no unused future branches.
8. Pass the existing Library through live and thumbnail renderer contracts. Update thumbnail cache identity.
9. Apply the version table exactly and reset IndexedDB without migrations.
10. Add focused unit and Chromium proof. Rebaseline measured delivery ratchets only where the production build changes them.

If a touched file already exceeds 700 lines, refactor before adding behavior. Keep new files below 700 lines and new functions below about 150 lines. In particular, add new morph coverage to a focused test file if `tests/sceneMorph.test.ts:scene morph tests` would cross the threshold.

## 14. Tests

### Unit proof

`tests/cubeFaceStateOwner.test.ts:CubeFaceState owner tests` must prove strict discriminated validation, explicit clear, deep equal no op, inheritance, matching, render impact, Stencil colour tween eligibility, structural cuts, sparse compact round trip, and rejection of the old figure tuple and removed fit member.

`tests/stencilAssets.test.ts:content addressed Stencil assets tests` must prove:

1. Seeded assets contain their exact SVG source and source region.
2. Source UTF-8 length equals `byteLength` and source digest equals `id`.
3. A nonseeded SVG asset round trips through Library, Stencil record, Project projection, commit, reload, and Library resolution.
4. Missing Library entries resolve explicitly as unresolved.
5. Unknown fields, mismatched byte length, and old Stencil record version are rejected.

The face render unit test, renamed if appropriate, must prove dynamic slot assignment for a nonseeded Library stencil, canonical source region normalization, exact four float content uploads, stable fixed shader composition, explicit capacity overflow, and disposal.

Morph tests must prove that only Stencil colour changes with stable kind, ID, and region tween. Kind, ID, region, appearance, and disappearance cut.

Panel tests must prove that seeded selection still authors one idempotent Library insertion followed by one `set-face-state` content patch, clearing removes only face content, and undo or redo preserves the atomic user gesture.

Thumbnail tests must prove a nonseeded Library stencil renders after reload and that a changed `library.stencils` identity invalidates a previously unresolved cached thumbnail.

### Browser proof

Extend `tests/stencilRenderingBrowserDriver.ts:runStencilRenderingBrowserGate` to use a generated nonseeded SVG asset resolved from a Library. Begin with the existing mesh, material, program, and R8 texture. Synchronize the asset into a dynamic slot, patch one face from plain to Stencil content, await the current atlas generation, and render.

The Chromium assertion must prove:

1. The nonseeded SVG produces covered atlas pixels and at least two rendered colours.
2. The display remains one draw.
3. The mutation creates zero programs and zero textures.
4. Mesh, material, program key, and texture identities remain stable.
5. The content patch uploads exactly four floats and no unrelated instance attributes.
6. A stale raster generation cannot overwrite a newer Library synchronization.
7. Disposal returns live GPU resources to baseline.

### Controlled RED and GREEN

Before implementation, land the focused test expectations locally and run them against current code:

1. The Library source round trip test must fail because current `StencilAsset` rejects source fields.
2. The browser dynamic slot test must fail because current `getStencilAtlasSlot` returns `null` for a nonseeded ID.
3. The compact codec test must fail because current state accepts `figure` and lacks the content discriminant.

Keep the failing output as implementation evidence. Do not commit the red state. After implementation, rerun the same tests to GREEN.

If delivery limits change, run the exact budget proof after measuring the production build: lower each changed `maxGzipBytes` by one byte, run `pnpm check:budget`, and capture `ERROR DELIVERY_JS_RATCHET`; restore the measured exact value and rerun to zero violations. Never add padding.

## 15. Gates

Focused gates:

```text
pnpm exec vitest run tests/cubeFaceStateOwner.test.ts tests/stencilAssets.test.ts tests/faceStencilRender.test.ts tests/panels.test.tsx --project unit
pnpm exec vitest run tests/stencilRendering.browser.test.ts --project chromium --disableConsoleIntercept
```

Final gates:

```text
pnpm check
pnpm test
pnpm test:browser
pnpm build
pnpm check:budget
git diff --check
git status --short
```

Acceptance requires all commands to exit zero, no untracked generated files, no old production symbol matches, no renderer import of `seededStencils.ts`, and current browser metric output attached to the implementation report.

## 16. Non goals

This slice does not implement a cell occupant, grid change, text authoring, image import, video playback, generated shader UI, font asset, binary payload store, RGBA media atlas, WebGPU, TSL, new face layer, migration, or compatibility decoder.

## 17. Completion

The foundation is complete when one nonseeded persisted Stencil asset renders on a cube face and in a thumbnail through the Library resolver and dynamic R8 atlas, while the old Figure path and fit field are absent and every unit, Chromium, build, delivery, and cleanliness gate passes.

Implementation completion line:

```text
done: CubeFaceContent foundation replaces figure, Library Stencils render through one dynamic atlas path, fit is removed, and all gates pass.
```
