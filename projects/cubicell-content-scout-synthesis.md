# Cubicell content scout — synthesis of six reports

Sources: grid-fable, grid-sol, grid-grok, media-fable, media-sol, media-grok (2026-08-09, main @ 3725921). Citations `file:symbol`.

## 1. Verdict

All six converge: the hypothesis is true about capability and wrong about location. The layout engine is content agnostic; `grid.ts:GridState` and `gridLayout.ts:createSceneGridLayout` never read a face, and `cube.ts:cubeFaceStateOwner` is an extensible field system with a clean single-writer topology. The ceiling is the content vocabulary and the render contract: a face can express only base colour/opacity/visibility plus one optional tinted monochrome stencil from two compiled-in SVGs. Structural blockers: `cube.ts:CubeFaceFigure` has no content payload discriminant; `stencil.ts:StencilAsset` persists no source, so user content cannot round-trip; the renderer is a single-channel 16-slot mask atlas with a two-colour fragment blend behind one shared `MeshBasicMaterial` per face bucket; `cubeEdgeState.ts:cubePartColors` is a closed 4-role enum. Incidental: 14 empty atlas slots, an already-generic asset op pipeline, a picker that merely enumerates seeds. Grok's archaeology shows the walls are mostly deliberate confinement (PRs #151, #158, #163, #164); the one accidental-feeling gap is the half-open stencil library seam. No grid rewrite is indicated; richer SVG content is mostly wiring, images/video need the render contract changed.

## 2. Unified reuse map

Owning symbols any face-media work must bind to. No genuine ownership disagreements across the six maps except one noted below.

- Domain: `cube.ts:cubeFaceStateOwner` (+ `setCubeFaceState`), `cubePartStateOwner.ts:createCubePartStateOwner`, `cube.ts:CubeFaceFigure`, `cubeEdgeState.ts:cubePartColors`, `stencil.ts:StencilAsset`/`StencilId`, `seededStencils.ts:resolveStencilContent`
- Ops/state: `workbenchOperations.ts:StencilDocumentOperation`, `state/actions/authoredReducer.ts` (single authored funnel), `workbench.ts:Library`/`getProjectAssetRoster`, `state/workbenchValidation/assets.ts:readStencils`
- Persistence: `recordCodecs/stencilRecordCodec.ts` over `simpleAssetRecordCodec`, `recordCodecs/projectRecordCodec.ts`, `recordCodecs/compactPose.ts:encodeCell` (face tuple, figure at position 4), version constants per layer (sol-grid §3 has the full bump list)
- Scene: `scene/cubeInstances.ts:createCubeCellInstances`, `scene/instancedPartMeshCore.ts:createInstancedPartMeshWithGeometry`/`syncInstancedPartMesh`/`patchInstancedPartMesh` (sole GPU writer), `scene/faceStencilShader.ts:applyFaceStencilShader`/`writeFaceStencilAttribute`/`fragmentPartition`, `scene/stencilAtlas.ts:createStencilAtlas`/`getStencilAtlasSlot`, `scene/renderCubeScenePartLayers.tsx:renderCubeScenePartLayers` (three face buckets), `scene/CubeScene.tsx:useOwnedStencilAtlas`/`StencilAtlasReadyDriver`
- Demand loop: `scene/renderScheduler.ts:createRenderScheduler`, `scene/renderProducers.ts:renderProducers`, `transport/TransportFrameDriver.tsx:TransportFrameDriver` (pattern for any animated medium)
- Thumbnails: `thumbnail/thumbnailArtifact.ts:createThumbnailArtifact`, `thumbnail/thumbnailRenderer.ts:createOrthographicThumbnailRenderer` (second atlas consumer; every medium needs a poster answer)
- Gates: `tests/webGlResourceObserver.ts:observeWebGlResources`, `tests/stencilRenderingBrowserDriver.ts:runStencilRenderingBrowserGate`, `budgets/initial-delivery.json` + `scripts/check-delivery-budget.mjs` (media UI belongs in a `capabilityIncrements` entry)
- Editor: `editor/controlBindings.ts:faceStencilBinding`/`faceStencilOptions`, `panels/panelDefinitions.ts:faceBindingIds`

Ownership disagreement (sol-grid): `resolveStencilContent` claims to own StencilId→source resolution, but the renderer bypasses it and reads `seededStencils` directly in `stencilAtlas.ts:rasterizeSeededStencils`. Two resolution paths today; any build must unify on one.

## 3. Forks

**F1 — video/shader render strategy.** media-fable: add a dedicated media-face layer in `renderCubeScenePartLayers` that pulls media-bearing faces out of the instanced buckets into individual meshes (explicit break of the one-material-per-bucket invariant); evidence: `VideoTexture` is a whole texture and cannot share the instanced sampler. media-sol: stay inside the fixed `onBeforeCompile` contract; one shared video sampler covers many instances, multiple sources via per-source instanced partitions or per-frame `copyTextureToTexture` into a dynamic RGBA atlas slot; evidence: the browser gate's one-draw/zero-program invariant and the fixed program key rule (`LESSONS.md`). Both agree static images fit an RGBA sibling atlas with zero draw growth; the fork is only video and shaders. Cheap probe: a spike measuring (a) per-frame atlas-copy cost for 1/4/8 concurrent videos vs (b) draw-call and program count of dedicated meshes, both under `observeWebGlResources`, plus frame-time during camera drag. media-grok's scaling table suggests sparse video (poster + play-on-select) makes N small either way.

**F2 — replace vs widen the figure.** grid-sol: replace `CubeFaceFigure` with one discriminated `CubeFaceContent` union, no parallel `figure`+`media` fields (pre-release reset makes replacement cheap). media-fable: "widen the figure or add a parallel media field". Grid-grok's history (PR #158 honesty pass, no-dormant-fields pattern) weighs for replacement. Probe: none needed; this is settled by the repo's own precedent unless Stuart wants staged parallel paths.

**F3 — WebGPU/TSL.** media-sol and media-grok independently reject for this slice (~102–107 KB gzip, ~25% of the shared-renderer ceiling; kills the `onBeforeCompile` seam; program-key mismatch). Convergence, not a live fork; recorded here because it forecloses TSL-style per-face effects until a deliberate migration.

## 4. Disposition table

| Finding | Disposition | Reason |
|---|---|---|
| `createCubePartStateOwner` field system | reuse | correct seam; content = field definition, not rewrite |
| Single writer chains (authored + GPU) | reuse | invariant to preserve; review will check for second writers |
| `CubeFaceFigure` closed to StencilId | refactor-first | replace with discriminated content union before adding kinds (F2) |
| Declared-but-unhonored stencil library (`create-stencil-asset` persists metadata that can never paint; seed-only atlas/resolver) | refactor-first | close the half-open seam: payload on asset, resolution via Library, dynamic slot at `stencilAtlas.ts:getStencilAtlasSlot` |
| Dual resolution paths (resolveStencilContent vs direct seededStencils read) | refactor-first | one owner before new content kinds multiply the divergence |
| Never-shipped `CellContent` / nested grids (grok archaeology; doc-only since `CUBICELL.md`) | defer | product direction, Stuart owns (D1) |
| Binary payload store (JSON/localStorage cannot carry image/video bytes; quota loss is silent) | refactor-first | blocking prerequisite for any imported media; needs a blob owner |
| RGBA sibling atlas for static images | reuse | extends existing atlas pattern, zero draw growth, all reports agree |
| Video/shader batching strategy | defer | fork F1; spike probe first |
| `fit` packed but no shader branch (margin/bleed render identically) | refactor-first | honor or remove per PR #158 pattern; `git log -S` before deciding |
| Closed 4-role colour enum | reuse | append-only by design; arbitrary RGB only if a content kind demands it |
| Compact pose wire + schema versions | reuse | bump-and-reset, single user, no migrations |
| Thumbnail parity (poster frame per medium) | reuse | second consumer; silent divergence otherwise |
| Animated media as named render producers | reuse | `TransportFrameDriver` precedent; private rAF breaks the demand loop |
| Delivery budget `capabilityIncrements` for media UI | reuse | sanctioned growth path; shared-renderer ceiling has zero headroom |
| CSS3D / DOM-on-face | defer | rejected by both media architecture reports (occlusion, recording, raycast, budget) |
| WebGPU/TSL migration | defer | F3; separate deliberate migration, not a media slice |
| Typography branch (structure-as-content, off main) | defer | never merged; relevant only to D1 |

## 5. Open decisions for Stuart

1. **What "content" means.** Face media, cell interiors (`CellContent`), or structure-as-type (typography branch) are three different products. The scouts mapped face media; the other two are doc-only or off-main. Which direction, and which first?
2. **Media ceiling for the first slice.** Static images (and richer SVG) fit the existing render contract cheaply; video and generative shaders force fork F1. Is motion in scope now, or is image-on-face the slice?
3. **The one-draw invariant.** If video/shaders are in scope: may media-bearing faces exit the instanced buckets (dedicated layer, draw calls grow), or must everything stay inside the single-program atlas contract? The probe in F1 informs the cost, but the invariant is a product commitment only Stuart can trade.
