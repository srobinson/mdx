# Scout — Area A: grid/content model, ownership lens

Scout: fable5 (cubicell:general:6:3.1). Read-only pass, 2026-08-09.
Hypothesis under test: "we built a layout engine that does not support content."

## Reuse Map

Every piece of face-visual state, its owning symbol, writers, readers, and precedence.

### Authored face state

- **State shape**: `src/domain/cube.ts:CubeFaceState`, defined entirely by `src/domain/cube.ts:cubeFaceStateOwner`, an instance of `src/domain/cubePartStateOwner.ts:createCubePartStateOwner`. Fields: `color`, `opacity`, `visible` (shared with edges via `src/domain/cubeEdgeState.ts:cubeEdgeStateOwner.fields`) plus optional `figure`.
- **Figure value**: `src/domain/cube.ts:CubeFaceFigure` = `{ stencilId, color, region: "form"|"field", fit: "margin"|"bleed" }`. This is the entire content vocabulary of a face: a reference to a monochrome stencil, a role colour, and two 2-value layout switches.
- **Colour**: `src/domain/cubeEdgeState.ts:CubePartColor`, closed enum `["theme","black","white","accent"]` (`cubePartColors`). Resolved to actual RGB only at render time by `src/theme/scenePolarity.ts:resolveCubePartColor`. No arbitrary colour is expressible in the document.
- **Writers**: domain mutators `src/domain/cube.ts:setCubeFaceState` / `setAllCubeFacesState`, called only from `src/domain/cubeOperations.ts` and `src/domain/cubeCellOperations.ts`, driven by `set-face-state` editor commands authored in `src/editor/controlBindings.ts:faceStencilBinding` (and sibling face bindings). Single write funnel through `src/state/actions/authoredReducer.ts`. No second writer found.
- **Readers**: evaluation (`src/evaluation/sceneMorph.ts`, `src/evaluation/scoreAt.ts`), scene sync, panels.
- **Precedence**: authored document state is the persisted truth; per-frame display state is produced by evaluation (below) and never written back.

### Stencil content (the asset side)

- **Asset type**: `src/domain/stencil.ts:StencilAsset` = `{ id, kind, mediaType, name, byteLength }`. `stencilMediaType` is hard-pinned to `"image/svg+xml"`. Note what is absent: **no payload field**. The asset record carries metadata only.
- **Content resolution**: `src/domain/seededStencils.ts:resolveStencilContent` — the only path from `StencilId` to SVG source — closes over the compile-time array `seededStencils` (two entries: Helioy, Manicure, imported as `?raw` at build time). Runtime writers of stencil content: none.
- **Workbench asset list**: written by `src/state/actions/authoredReducer.ts` applying `src/domain/workbenchOperations.ts:StencilDocumentOperation` (`create-stencil-asset` / `delete-stencil-asset`), staged by `faceStencilBinding.createPreparationCommand`; validated by `src/state/workbenchValidation/assets.ts:readStencils`; persisted via `src/persistence/recordCodecs/stencilRecordCodec.ts` on the generic `simpleAssetRecordCodec`. This pipeline is real and generic, but since the asset has no payload, it can only round-trip references to stencils the build already contains.

### Render-time state

- **Per-frame face state**: produced by `src/evaluation/sceneMorph.ts:createPartColorTweens` and the owner's `interpolateMorph`. The per-field `morphChannel` on `cubeFaceStateOwner` (`color-tween` vs `discrete-cut`, gated by `src/domain/cube.ts:canTweenCubeFaceFigureColor`) decides tween vs cut (PR #165 authors the cuts). Evaluation output wins for display; it never writes the document.
- **GPU attribute**: `instanceFaceStencil` (vec4), sole writer `src/scene/instancedPartMeshCore.ts` (both `syncInstancedPartMesh` and `patchInstancedPartMesh`), funnelled through `src/scene/faceStencilShader.ts:writeFaceStencilAttribute`. Patch path is gated by render attribute `"stencil"` classified in `src/domain/incrementalCubeRenderResolution.ts`. Sync and patch cannot disagree; they share the one write function.
- **Atlas texture**: sole writer `src/scene/stencilAtlas.ts:createStencilAtlas`, filled once by `rasterizeSeededStencils`. Slot mapping `slotByStencilId` is built from `seededStencils` at module load. Second consumer: `src/thumbnail/thumbnailRenderer.ts` / `thumbnailArtifact.ts` take a `stencilAtlas` — any atlas change must keep thumbnails in sync.

## Quality Map

- `createCubePartStateOwner` is a strong, genuinely extensible seam: each field declares decode/encode/equals/inherit/morphChannel/renderAttribute in one place, and state, patches, persistence, morphing, and dirty-attribute routing all derive from it. Adding a new kind of face content is a field definition, not a rewrite.
- The write topology is clean: one authored funnel (editor command → reducer → domain mutator), one render funnel (evaluation → mesh sync → attribute). No competing writers found anywhere in the face path.
- The renderer is deliberately narrow: single-channel `RedFormat` atlas (2048², 16 × 512px slots), slot+region+fit packed into one float (`regionFlag = 16` caps slots at 16), fragment shader blends exactly two solid colours by mask coverage (`faceStencilShader.ts:fragmentPartition`). Elegant for what it does; a hard ceiling for what it doesn't.

## Verdict on the hypothesis

**Confirmed, with a precision that matters: the restriction is not in the grid, it is in the content vocabulary.** The cell/face model (`cubeFaceStateOwner`) is an extensible field system with no structural bias against richer content. What a face can hold today is exactly "a tinted monochrome stencil from a compiled-in set of two." The blockers, classified:

Structural (the model cannot express it):
1. `CubeFaceFigure` has no content payload type beyond `StencilId`; images, video, shaders, arbitrary textures are unrepresentable in the document.
2. `StencilAsset` persists no source; `resolveStencilContent` only knows compile-time `seededStencils`. User-supplied content cannot round-trip.
3. The render contract is mask-only: single-channel atlas, two-colour fragment blend, ≤16 slots by attribute packing. RGBA imagery or per-face textures need a format and packing change, video/shaders need a different material strategy (the shared instanced `MeshBasicMaterial` is one draw call by design).
4. `CubePartColor` is a closed 4-role enum; arbitrary per-face colour is unexpressible.

Incidental (nothing wired yet):
1. Atlas capacity is 16, seeded fill is 2; more SVG masks need only dynamic slot assignment at `stencilAtlas.ts:slotByStencilId`.
2. The asset operation pipeline (`create-stencil-asset`, `stencilRecordCodec`, `readStencils`) already exists and is generic; adding a source payload is a field addition plus schema bump (single user, no migrations).
3. The editor picker (`controlBindings.ts:faceStencilOptions`) enumerates `seededStencils`; an import UI attaches at the same binding, and its `createPreparationCommand` already stages asset creation into the document.

Exact attach seams for richer content: `cube.ts:cubeFaceStateOwner` (new/extended figure field), `seededStencils.ts:resolveStencilContent` (swap compile-time closure for workbench asset lookup), `stencil.ts:StencilAsset` (payload field), `stencilAtlas.ts:createStencilAtlas` + `slotByStencilId` (dynamic slots, format), `faceStencilShader.ts:writeFaceStencilAttribute` + `fragmentPartition` (packing, sampling), `instancedPartMeshCore.ts` (attribute routing, already keyed by render attribute), `controlBindings.ts:faceStencilBinding` (authoring UI).

## None found (searches run)

- User upload/import path: `grep -rn "upload|FileReader|input type=\"file\"|createObjectURL" src/` — hits only thumbnail blob URLs (`CapabilityStateThumbnail.tsx`), export recorder (`streamRecorder.ts`), and the atlas's own SVG rasterization. No import surface exists.
- Texture/image/video loading: `grep -rn "VideoTexture|TextureLoader|CanvasTexture|ImageBitmap" src/` — zero hits.
- Second writer to face state or the stencil attribute: `fmm_glossary(setCubeFaceState)`, `fmm_glossary(writeFaceStencilAttribute)` — writers are exactly the ones named above.
- Arbitrary colour path: `fmm_search(term: CubePartColor)` — all consumers route through the role enum and `resolveCubePartColor`; no RGB escape hatch.
