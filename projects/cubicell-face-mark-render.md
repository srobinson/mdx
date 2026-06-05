# Cubicell face mark render scout

## Decision

Use a fixed grid, single channel R8 alpha atlas inside the existing instanced face pass.

The atlas stores form coverage only. The existing `instanceColor` remains the ground region. One new packed `vec4` instance attribute carries the mark region RGB and a tile index. A negative tile index means no mark. The fragment shader samples coverage and mixes the two colors. Both colors must resolve through the supplied `ScenePolarityConfig` and the existing face lightness treatment. No SVG fill, stroke, opacity, or source color enters the render path.

Start with one 2048 square R8 page containing sixteen 512 square slots, including gutters. GPU texture cost is 4 MiB for level zero and 5.33 MiB for a complete mip chain. The new instance attribute costs 16 bytes per face capacity slot. Six exposed faces therefore add at most 96 bytes per cube before power of two capacity rounding.

This recommendation has one acceptance condition. The manicure mark needs a Chromium pixel golden on an actual cube at thumbnail scale, normal workbench scale, close zoom, and DPR 4. The source probes below support a 512 square starting slot. They do not replace that rendered proof.

## Measured asset evidence

Head and merge base are both `7d5e942ea623a097f25c529925b299f31c7af38f`.

`assets/marks/helioy.svg` is 915 bytes, has a 250 square view box, two paths, and 421 bytes of path data. It is a positive form on transparent ground.

`assets/marks/manicure.svg` is 4,425 bytes, has a 214 square view box, three paths, and 2,319 bytes of path data. Its main compound path declares 54 nodes. That path supplies the edge bleeding field and transparent face cutout; the eye and nose are separate positive islands.

An in memory Chromium canvas probe rasterized manicure at 64, 128, 214, 256, 512, and 1024 pixels. At a 50 percent coverage threshold, 64 pixels retained two foreground components while 128 pixels and every larger size retained all three foreground components and both background regions. A 512 pixel raster sampled to 1024 pixels differed from a direct 1024 pixel SVG render on 0.0894 percent of binary coverage pixels, with mean alpha error 0.7696 on a 0 to 255 scale. This establishes topology retention and low coverage error. Eyelash appearance on a projected cube remains unmeasured.

## Exact production seam

The hook belongs in `src/scene/instancedPartMeshCore.ts:createInstancedPartMeshWithGeometry`, with writes owned by `syncInstancedPartMesh` and `patchInstancedPartMesh`.

The live path is:

`src/scene/cubeInstances.ts:createCubeCellInstances`

to `src/scene/incrementalCubeSceneOwner.ts:createCellEntry`

to `src/scene/cubeInstanceSlots.ts:createCubeInstanceSlotOwner`

to `src/scene/instanceSlotRegistry.ts:changedAttributes`

to `src/scene/instancedPartMeshCore.ts:patchInstancedPartMesh`.

The partition collides with four current assumptions:

1. `src/scene/instancedPartMeshCore.ts:resolveInstanceColor` returns one RGB value and `writeColor` uploads one `instanceColor`. The second region needs its own resolved color plus mask tile selection.
2. `src/scene/instancedPartMeshCore.ts:applyInstanceOpacity` owns `material.onBeforeCompile` and `customProgramCacheKey` for translucent meshes. The face mark hook must compose with it. Assigning another hook would silently remove opacity or mark behavior.
3. `src/scene/instanceSlotRegistry.ts:changedAttributes` knows only matrix, color, opacity, and edge axis changes. A mark edit needs one `mark` attribute classification or the incremental path will retain stale GPU data.
4. `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` creates two face meshes without `partKind: "face"`, while `src/scene/renderCubeScenePartLayers.tsx:renderCubeScenePartLayers` sets that part kind for all three workbench face meshes. A shader selected only through `partKind` would disappear from thumbnails. The face mesh construction contract must be shared or made explicit in both consumers.

The prior `spike/shape-shader` work demonstrates the reusable mechanism. `src/scene/edgeShapeShader.ts:applyEdgeShapeShader` at `0aac4a2` used capacity bound instanced attributes, composed a fixed shader hook, and retained mesh and material identity across capacity growth. Its browser gate measured zero new programs after value mutation and capacity crossing. The spike does not establish mask fidelity, texture lifetime, or export parity.

## Representation costs

| Representation | Texture and buffer memory | Draw calls | Programs | Fragment work | Manicure fidelity |
| --- | --- | --- | --- | --- | --- |
| R8 alpha atlas in the face pass | Recommended page is 4 MiB base, 5.33 MiB with mips. One packed `vec4`, 16 bytes per face capacity slot. | No increase. Marked and unmarked faces remain in the existing opaque, translucent, and ghost instance meshes. | Fixed face keys. Initial total program count delta is unknown until a browser measurement. Mark values create no variants. | Unmarked fragments take one coherent presence branch. Marked fragments take one filtered R8 sample and one color mix. | Best measured candidate. A 512 tile retained source topology and had 0.0894 percent threshold mismatch at 1024 output. Actual projected detail still needs the named golden. |
| Single channel SDF | R8 has the same atlas memory. R16F doubles it to 8 MiB base and 10.67 MiB with mips. Instance data is equivalent. | No increase when integrated into the face pass. | Fixed. | One distance sample, derivatives, and a smooth threshold. A geometry crossfade needs two samples. | Loses. Fine opposing contours can collapse inside the distance spread, while acute details soften. It adds generator code and risk without a demonstrated scale requirement. |
| Tessellated path geometry | No texture. Geometry bytes depend on curve flattening tolerance and hole triangulation, so a defensible number is unavailable before tessellating manicure. | Grows with distinct marks and active opacity families because an `InstancedMesh` shares one geometry. At minimum, one base face draw remains and mark geometry is grouped by mark identity. | Material keys can stay fixed across marks. | Cheap filled triangles after tessellation. Vertex cost and overdraw depend on flattened geometry. | Can preserve the vector if tolerance is sufficiently small, but the 54 node compound path, holes, edge bleed, and several mark identities make draw and geometry growth the wrong scaling shape. |
| Coverage co shape overlay | Still needs alpha, SDF, or tessellated geometry. An alpha version keeps the atlas and duplicates marked face instance data. | Adds up to one overlay draw for each opaque, translucent, and ghost family. | Adds overlay program families, though their keys can be fixed. | Repaints marked face pixels and needs deliberate coplanar depth behavior. | Fidelity comes from the underlying representation. The coverage pattern does not solve the partition and adds a pass. It is useful for edge silhouette expansion, which this feature does not require. |

Raster alpha loses only at extreme magnification beyond the tile resolution. SDF loses the thin feature safety margin. Path geometry loses instancing across distinct marks. The coverage overlay loses draw count and introduces a coplanar seam. The R8 atlas is the smallest complete solution.

## Program cache keys

Program keys remain fixed.

Use one literal face mark key, for example `cubicell-face-mark-v1`, and a fixed composed key for the translucent face mark plus instance opacity program. Tile index, mark identity, SVG hash, atlas dimensions, instance capacity, rail values, and morph progress must never enter `customProgramCacheKey` or React mesh dependencies.

Apply the face shader and its attribute at mesh construction, including when no face currently carries a mark. The first mark then changes buffer values and texture contents without replacing the mesh, material, or shader program.

A variant per mark would be a defect.

## GPU count gate and delivery budget

### Expected count movement

The workbench has three face meshes in `renderCubeScenePartLayers`: opaque, translucent, and ghost. One packed mark attribute therefore adds three live WebGL buffer objects after upload. Each face mesh that crosses a geometric capacity band creates and deletes one additional attribute buffer. The separate thumbnail artifact has two face meshes and adds two live buffers while it renders.

One atlas adds one live WebGL texture per WebGL context. The workbench and thumbnail renderer own separate contexts, so the same CPU atlas data is uploaded once to each active context.

Draw submissions remain flat because the partition executes in the existing face draws.

The initial live program count delta is unknown. The face mark shader replaces existing face program bodies and should not add a material family when installed from construction, but only the production browser gate can establish the count. After initial compile, mark value changes, atlas additions, and face capacity crossings must report zero created programs.

Mesh and material identities remain stable. Atlas texture identity must also remain stable across content updates.

### Current gate gaps

`tests/webGlResourceObserver.ts:observeWebGlResources` counts buffers and programs only. It cannot see texture creation, deletion, or churn. Add texture counts before accepting an atlas pipeline.

`tests/incrementalScene.browser.test.ts` currently asserts flat live resources and zero program creation across capacity bands, while buffer creation and deletion are only required to be greater than zero. The mark gate should pin:

* three added live workbench attribute buffers;
* one added live workbench texture;
* stable mesh, material, and texture identity;
* zero draw call increase for one mark and several distinct marks;
* zero created programs across mark edits and capacity growth;
* one 16 byte attribute upload for a mark only face patch;
* bounded texture upload count when adding a tile.

A monolithic `DataTexture.needsUpdate` can upload the full 4 MiB page after one imported mark. That is a byte cost even when all resource counts stay flat. Atlas construction should be document load work, or a texture upload gate should prove tile scoped updates. No per frame atlas upload is acceptable.

### Delivery bytes

The current zero headroom JavaScript ceilings are 408,233 gzip bytes for `shared-renderer` and 439,732 gzip bytes for `default-interactive`. Render pipeline code sits in both closures. Its exact compressed delta is unavailable until implementation and build measurement. Both ceilings must be reset to their measured values in the same delivery.

The two source SVGs total 5,340 bytes. Their individual gzip level 9 sizes are 540 and 1,980 bytes. Vite 8 defaults to a 4,096 byte inline limit. If these files are statically URL imported under the current config, helioy is eligible for JavaScript inlining while manicure is emitted as a separate asset. `scripts/check-delivery-budget.mjs:checkDelivery` sums emitted JavaScript and CSS only, so the emitted manicure asset would not be charged to a delivery ratchet. The exemplars should remain fixtures unless product delivery explicitly requires them. User imported marks should enter from project data rather than the initial bundle.

Use browser SVG rasterization and the existing Three `DataTexture` with `RedFormat` and `UnsignedByteType`. Three 0.185 uses WebGL 2 and maps that pair to GPU R8. No rasterizer dependency is justified, which limits JavaScript growth.

## Scale behavior

Many cubes sharing one mark preserve one atlas texture, the existing face draws, and one fixed shader family. Instance memory grows by 16 bytes per face slot, and fragment work grows with visible marked pixels rather than cube count alone. DPR 4 multiplies fragment demand by sixteen relative to DPR 1 at the same CSS coverage.

Several distinct marks within the sixteen slot page have the same draw and program counts. They change tile indices and atlas occupancy only. The hard boundary is page capacity. A 4096 square R8 page costs 16 MiB base and 21.33 MiB with mips. Multiple 2048 pages require partitioning face instances by page, which adds meshes, buffers, and draw submissions while retaining one fixed program key. This boundary needs a declared maximum or an eviction policy before unbounded imports are supported.

Color rail morphs remain CPU resolved instance values and do not change the shader key. A mark identity morph is different. One tile sample can cut from one geometry to another. A visual crossfade requires two tile indices, a progress value, and two texture samples for every marked fragment during the morph. The current `src/evaluation/scoreAt.ts:Moment` carries part color tweens but no mark geometry tween, so this behavior is presently undefined.

`src/export/streamRecorder.ts:createRecordingController` uses `canvas.captureStream`, which records the workbench framebuffer and therefore receives the exact same mark shader and atlas. The offscreen thumbnail renderer is a separate production renderer. Its artifact must use the same face mesh factory, deterministic tile map, CPU atlas bytes, and polarity based color resolution. GPU texture objects cannot be shared across its WebGL context. A future offscreen video or still exporter must reuse that same artifact path rather than rebuilding SVG appearance.

## Commands run

Read only source inspection used `git status`, `git rev-parse`, `git merge-base`, `git log`, `git show`, `git diff-tree`, `rg`, `sed`, `wc`, and small Node scripts for source byte and path counts. In memory ImageMagick and headless Chromium canvas probes measured mask topology and raster error without writing artifacts. No tests or builds were run because there is no production change and the brief permits only this report write. No repository file was changed.
