# Cubicell single face SVG and 3D typography scout

Date: 2026-08-07  
Branch: `feat/stencil-build`  
Exact head: `66b4d8d252fa2a4bc4c75bf4601feb8d58599f6f`

## Core conclusion

The current figure renderer is a two colour partition painted onto a zero thickness cube face plane. It can display bold typography from an SVG whose glyphs are paths. No current figure state can create figure depth, alter the face silhouette, occlude other geometry as a raised form, or occupy the space between opposite faces.

Three distinct extensions are possible:

1. A fixed offset atlas treatment can suggest extrusion while every pixel remains on the face plane. This is a flat optical illusion.
2. Atlas gradients and view dependent sampling can produce bevel, normal, and parallax cues on the same plane. This is shader only 2.5D.
3. Parsed SVG contours can feed cap and side polygons with physical depth. This is true geometry.

The first two extend the existing face shader. True extrusion requires one additional geometry layer, but it can still reuse the current face instances, slot lifecycle, colour resolution, depth rules, and transition data. A second scene derivation or renderer should be rejected.

## Verified current envelope

| Concern | Current fact | Consequence for typography |
|---|---|---|
| Figure schema | `src/domain/cube.ts:CubeFaceFigure` owns `stencilId`, `region`, `color`, and `fit`. `cubeFaceStateOwner` owns validation, codec, inheritance, morph classification, and `stencil` render impact. | There is no depth, bevel, elevation, side colour, light, or extrusion state. |
| Authored control | `src/editor/controlBindings.ts:faceStencilBinding` selects `None`, `Helioy`, or `Manicure` and emits the existing `set-face-state` operation. | The UI can place one seeded stencil on one selected face. It cannot enter text or edit figure colour, region, fit, or depth directly. |
| Content | `src/domain/seededStencils.ts:seededStencils` owns the only two renderable SVG sources and defaults. `resolveStencilContent` can resolve only those sources. | A typography experiment can add one source controlled SVG with outlined glyphs. Arbitrary project stencil metadata has no source path into the atlas yet. |
| Unresolved content | `src/domain/cube.ts:isCubeFaceFigure` accepts any syntactically valid content ID. `src/scene/stencilAtlas.ts:getStencilAtlasSlot` returns `null` for IDs outside the seeded set. `writeFaceStencilAttribute` then writes the plain face sentinel. | Persisted but unresolved stencil figures survive domain validation and render as plain faces. |
| Face geometry | `src/domain/cubeGeometry.ts:createCubeFacePlanes` places each face at one half of the cube size on its axis. `src/scene/instancedPartMeshCore.ts:createInstancedPartMesh` uses `PlaneGeometry(1, 1)` for every face. | A front and back face are separated by the authored cube depth, but both are surfaces with no thickness. The interior is empty. |
| Figure geometry | `src/scene/cubeInstances.ts:createCubeCellInstances` copies the figure into a face instance and uses the same plane matrix. The local face scale is `[width, height, 1]`. | Figure content has no independent transform or geometry. It inherits cube position, rotation, scale, size, presence, and face orientation. |
| Face spacing | Opposite face spacing comes from cube size. Cube centre spacing comes from `src/domain/gridLayout.ts:getGridLinePosition`, using cell size, grid gap, and interval overrides. | Grid gap changes separate cubes. They do not add figure relief or distance from the face. |
| Atlas | `src/scene/stencilAtlas.ts:createStencilAtlas` owns one 2048 by 2048 R8 texture, sixteen fixed 512 slots, one pixel gutters, 510 pixel content, linear filtering, and no mipmaps. Two slots are occupied. | One typography SVG fits the current capacity. Thin strokes and distant viewing have no mip support. |
| Rasterization | `src/scene/stencilAtlas.ts:rasterizeSvgAlpha` draws each SVG into a square 510 canvas. `writeStencilSlot` copies alpha, extends edge pixels into the gutter, and flips rows for texture coordinates. | Typography should be converted to paths and authored in a square view box with its intended margin. Non square fit has no proven behavior. |
| Fit | `src/scene/faceStencilShader.ts:writeFaceStencilAttribute` packs the `fit` flag. `fragmentPartition` never reads that flag for UV scale or crop. | `margin` and `bleed` currently produce identical sampling. Asset whitespace is the effective fit control. |
| UV orientation | `src/domain/cubeTopology.ts:cubeFaceTopology` rotates one plane basis onto each face. `tests/stencilOrientation.test.ts` proves exterior readable U and V axes for all six faces. | Outlined text remains upright and readable from outside each face. The back, left, right, top, and bottom bases deliberately compensate for exterior viewing. |
| Colour | The face plane supplies the field colour. `instanceFaceStencil.rgb` supplies the figure colour. `fragmentPartition` mixes them by normalized form coverage and swaps their roles for `region: field`. | One stencil can partition the plane into two authored colour roles. SVG fill colours, strokes, and opacity are discarded except for raster alpha. |
| Colour vocabulary | `src/domain/cubeEdgeState.ts:cubePartColors` owns `theme`, `black`, `white`, and `accent`. `src/theme/scenePolarity.ts:resolveCubePartColor` maps roles by polarity. `src/scene/instancedPartMeshCore.ts:resolveTreatedPartColor` applies the same face value ramp to the field and figure on the workbench. | Typography uses the existing authored palette and workbench treatment. A new colour resolver would duplicate ownership. |
| Material | `src/scene/instancedPartMeshCore.ts:createInstancedPartMeshWithGeometry` uses unlit `MeshBasicMaterial`. Face meshes are double sided. | There are no scene lights or physical material normals to reveal depth. Any relief shading must be computed in the stencil shader or in a dedicated geometry material extension. |
| Depth | Opaque face materials keep `depthTest` at the Three default and set `depthWrite: true`. Translucent faces keep depth testing but set `depthWrite: false`. `src/scene/CubeScene.tsx:canvasRendererOptions` enables the logarithmic depth buffer. | The stencil shares exactly the face plane depth. It cannot sit above or below the face. It cannot cast, receive, or create geometric occlusion. |
| Fragment behavior | `src/scene/faceStencilShader.ts:fragmentPartition` changes only `diffuseColor.rgb`. It does not move vertices, discard fragments, change alpha, write fragment depth, or sample a height field. | Current output is flat colour partitioning. |
| Draw and resource shape | `applyFaceStencilShader` composes with instance opacity in the existing face program. One packed `vec4` carries figure RGB plus slot and flags. Chromium gates prove one draw, one stable atlas texture, stable mesh and material identity, and a four float stencil patch. | A shader experiment can retain the same mesh, texture, patch path, and draw count. |
| Thumbnail | `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` builds face meshes through the same instanced core and shared atlas contract. | Current flat figures reach thumbnails. A geometry experiment must extend this owner or state an explicit live canvas only experiment boundary. |

## Exact live data and render path

Authored state follows one existing chain:

`faceStencilBinding` -> `set-face-state` -> `cubeFaceStateOwner` -> `authoredRenderImpact` -> `incrementalCubeSceneOwner:createCellEntry` -> `createCubeCellInstances` -> `createCubeInstanceSlotOwner` -> `instanceSlotRegistry:changedAttributes` -> `InstancedPartMesh` -> `patchInstancedPartMesh` -> `writeStencil` -> `writeFaceStencilAttribute` -> `fragmentPartition`

Atlas ownership follows:

`CubeScene:useOwnedStencilAtlas` -> `createStencilAtlas` -> `rasterizeSeededStencils` -> one `DataTexture` -> all opaque, translucent, and ghost face meshes

Thumbnail ownership follows:

`createOrthographicThumbnailRenderer` -> one backend atlas -> `createThumbnailArtifact` -> the same face mesh factory and shader

## Geometry answer

No current figure state can populate a figure shaped volume between front and back faces.

The only solid primitives in the cube renderer are edge and slot boxes created by `createInstancedPartMesh`. Cube size and edge thickness can stretch the topology defined perimeter bars along the depth axis. They cannot turn an arbitrary stencil into volume. Face figures never select box geometry, and `CubeFaceFigure` never reaches a geometry constructor. The front and back planes sit at opposite cube bounds while the interior between their fields remains empty.

An inward extrusion could geometrically span that space after a new contour layer exists. The current opaque front plane would hide it because every sight line into the cube crosses that plane. A visible inlay therefore also needs one of these explicit surface semantics:

- discard the field around the figure on the host plane;
- hide the host face while showing the extruded cap;
- extrude outward from the face;
- expose the volume from another hidden face.

The smallest visible true geometry experiment should extrude outward. An interior volume experiment carries an additional cutout decision and tests a different product idea.

## Animation and morph envelope

`src/domain/cube.ts:canTweenCubeFaceFigureColor` permits a colour tween only when stencil identity, region, and fit are unchanged.

`src/evaluation/sceneMorph.ts:prepareSceneMorphTopology` asks `cubeFaceStateOwner` whether a change is colour, numeric, or discrete. `createPartColorTweens` writes a figure colour overlay into `Moment.partColors.figures`. `src/scene/cubeInstances.ts:createCubeCellInstances` carries that overlay to `InstancedFaceFigure.colorTween`. `src/scene/instancedPartMeshCore.ts:writeStencil` resolves the tween through the same polarity colour path.

Current outcomes:

- figure colour can tween in OKLab through the existing colour overlay;
- stencil identity, region, fit, addition, and removal cut at the transition cut point;
- cube size, placement, rotation, scale, arrival, and departure move the whole face and its figure together;
- there is one atlas sample, so stencil to stencil crossfade has no owner;
- there is no depth or bevel channel to interpolate.

The complete transition path is:

`resolveSceneTransitionSample` -> `sampleResolvedSceneTransition` -> `sampleSceneMorph` -> `Moment` -> `useCubeSceneRenderState` -> `incrementalCubeSceneOwner` -> face instance patches

Any approved depth state belongs in `CubeFaceFigure` and `cubeFaceStateOwner`. Its morph behavior belongs in the same field descriptor and `sceneMorph` overlay system. A render local clock, spring, or parallel animation store would violate the current ownership model.

## Classification

### Flat optical illusion

Mechanism: sample the same R8 coverage several times along a fixed UV vector. Colour the displaced union with a darker side role, then paint the original coverage with the figure role.

Properties:

- zero thickness plane;
- unchanged depth buffer;
- unchanged outer face silhouette;
- fixed apparent direction unless the shader adds camera inputs;
- one face draw and one atlas texture;
- cheapest route to a bold poster style.

This should extend `src/scene/faceStencilShader.ts:fragmentPartition`. It needs no new scene state for a first test. Constants keep the program key fixed and isolate the visual question.

### Shader only 2.5D

Mechanism: treat R8 coverage as a binary height field. Sample neighbouring texels to estimate a bevel normal, then compute a fixed or view relative key light. A small view dependent UV offset can add parallax.

Properties:

- apparent bevel and relief inside the plane;
- no contour polygons or physical side walls;
- no geometric silhouette change;
- no reliable intersection or object level occlusion;
- one face draw and one atlas texture if all parameters are fixed or instance attributes;
- alpha coverage limits the bevel quality. A later signed distance atlas could improve it.

This also belongs in `faceStencilShader`. It should compose with `applyInstanceOpacity` through the existing `onBeforeCompile` chain and retain one fixed `customProgramCacheKey`.

### True geometry

Mechanism: parse SVG fill contours, normalize them into the face local square, triangulate caps, and construct side walls across an authored depth. Three 0.185 already provides `SVGLoader.parse`, `ShapePath.toShapes`, and `ExtrudeGeometry` through the installed `three` package.

Properties:

- real cap and side polygons;
- camera dependent silhouette;
- ordinary depth testing and occlusion;
- possible outward relief or inward volume;
- at least one additional draw for each geometry and material bucket;
- geometry and draw growth when stencil identities differ.

This requires a dedicated layer because one plane cannot become many contour solids in the fragment shader. The layer must consume existing face instances and the existing instanced mesh core. It must not rescan authored scenes or recreate face transforms.

## Smallest user testable experiments

### Experiment 0: typography fidelity baseline

Question: does a bold word remain legible and composed well enough on one cube face before depth cues are considered?

Change boundary:

- add one square SVG fixture under `assets/marks` with glyphs converted to paths;
- register it once in `src/domain/seededStencils.ts:seededStencils` with `region: form`;
- use the existing `faceStencilBinding`, atlas, face pass, and thumbnail path unchanged.

Manual test:

1. Create one cube and select its front face.
2. Choose the typography stencil.
3. Compare black and white scene polarity, orthographic and perspective projection, and near and far framing.
4. Orbit to confirm exterior readability on all six faces.

Acceptance: the word is readable at the intended thumbnail and stage sizes. The expected depth classification is flat.

Reason to run first: the current `fit` flag does not affect UVs. This test settles glyph weight, square view box, margin, and raster resolution without changing renderer architecture.

### Experiment 1: fixed optical extrusion

Question: is a graphic offset extrusion sufficient for the desired boldness?

Change boundary:

- extend only `src/scene/faceStencilShader.ts:fragmentPartition`;
- use a fixed eight step diagonal UV sweep over the current atlas coverage;
- derive one darker side tone from the current face or figure colour inside the shader;
- add a focused shader composition test and one Chromium image comparison.

Acceptance:

- the word gains a clear side mass in front and three quarter views;
- draw count, program count, atlas texture identity, mesh identity, and patch upload size stay at the current values;
- face depth and silhouette remain unchanged, as expected for an optical treatment.

Stop condition: if the user accepts this look, avoid adding geometry.

### Experiment 2: bevel relief in the face shader

Question: does a shallow surface response provide enough dimensionality while preserving the current resource shape?

Change boundary:

- extend `faceStencilShader` with four neighbouring coverage samples and a fixed bevel width;
- add view space position or direction through the same shader patch;
- shade a reconstructed normal with one fixed key vector;
- keep depth writes and geometry untouched.

Acceptance:

- bevel highlights and shadows remain stable under face rotation;
- no extra draw, program variant, texture, mesh, or material is created;
- the browser test identifies at least three tonal bands within the stencil;
- the result is explicitly evaluated as shader relief with a plane silhouette.

Stop condition: if camera orbit exposes the flat boundary as unacceptable, proceed to true geometry.

### Experiment 3: one true extruded word

Question: does physical contour depth materially improve the product compared with the shader experiments?

Change boundary:

- use the Experiment 0 outlined typography SVG;
- resolve its bundled source through `src/domain/seededStencils.ts:resolveStencilContent`;
- build one normalized `ExtrudeGeometry` once for that stencil;
- create one specialized layer following `src/scene/EdgeCoverageLayer.tsx:EdgeCoverageLayer` and `src/scene/edgeCoverageCore.ts:createEdgeCoverageMesh`;
- create its mesh through `src/scene/instancedPartMeshCore.ts:createInstancedPartMeshWithGeometry`;
- derive slots from existing `CubeFaceInstance` records and their matrices;
- place a fixed 0.12 cube unit extrusion outward for the first test;
- extend `src/scene/renderCubeScenePartLayers.tsx:renderCubeScenePartLayers` once;
- state explicitly whether thumbnails are included. If included, extend `createThumbnailArtifact` through the same geometry owner.

Acceptance:

- orbit changes the contour silhouette and reveals side walls;
- the word occludes and is occluded through the ordinary depth buffer;
- hiding or moving the source cube carries the extrusion through the existing instance path;
- arrival, departure, cube rotation, cube scale, and size morphs move the extrusion with the face;
- figure colour morph uses the existing colour overlay;
- one geometry resource is created for one stencil, with measured draw, buffer, program, and delivery budget deltas;
- disposal returns live GPU resources to baseline.

Stop condition: if silhouette and occlusion add little value, retain the shader path. If accepted, the next design decision is outward relief versus a host face cutout for inward volume.

## DRY reuse map

| Responsibility | Existing owner to extend | Parallel path to reject |
|---|---|---|
| Figure state and codec | `src/domain/cube.ts:CubeFaceFigure`, `cubeFaceStateOwner`, `isCubeFaceFigure`, `encodeCubeFaceFigure`, `decodeCubeFaceFigure` | A separate typography or extrusion state store |
| Source identity and defaults | `src/domain/seededStencils.ts:seededStencils`, `resolveStencilContent` | A second stencil registry keyed by names or URLs |
| Atlas bytes and texture | `src/scene/stencilAtlas.ts:createStencilAtlas` | A canvas or texture per face or per cube |
| Face orientation and transform | `src/domain/cubeGeometry.ts:createCubeFacePlanes`, `src/scene/cubeInstances.ts:createCubeCellInstances` | Recomputing face rotations in a new React layer |
| Instance change detection | `src/scene/instanceSlotRegistry.ts:changedAttributes` | A separate diff loop or frame polling |
| Mesh lifecycle | `src/scene/instancedPartMeshCore.ts:createInstancedPartMeshWithGeometry`, `growInstancedPartMesh`, `patchInstancedPartMesh`, `disposeInstancedPartMesh` | Raw meshes per face with independent capacity and disposal logic |
| Specialized layer pattern | `src/scene/EdgeCoverageLayer.tsx:EdgeCoverageLayer`, `src/scene/edgeCoverageCore.ts:createEdgeCoverageMesh` | A second scene graph or renderer |
| Colour roles and workbench treatment | `src/scene/instancedPartMeshCore.ts:resolveTreatedPartColor`, `src/theme/scenePolarity.ts:resolveCubePartColor` | New literal RGB values or duplicated polarity rules |
| Layer composition | `src/scene/renderCubeScenePartLayers.tsx:renderCubeScenePartLayers` | Imperative scene insertion outside the layer owner |
| Morph classification | `src/domain/cube.ts:cubeFaceStateOwner`, `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology` | A render time animation clock |
| Figure colour tween | `src/evaluation/sceneMorph.ts:createPartColorTweens`, `src/evaluation/scoreAt.ts:Moment` | A shader local colour transition |
| Live atlas ownership | `src/scene/CubeScene.tsx:useOwnedStencilAtlas` | Texture creation per mesh |
| Thumbnail parity | `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact`, `src/thumbnail/thumbnailRenderer.ts:createOrthographicThumbnailRenderer` | A separate thumbnail approximation |
| GPU verification | `tests/webGlResourceObserver.ts:observeWebGlResources`, `tests/stencilRenderingBrowserDriver.ts:runStencilRenderingBrowserGate` | Unmeasured visual claims |

## Recommendation

Run Experiment 0, then Experiment 1. They answer the typography and visual boldness questions with the current renderer and resource envelope. Proceed to Experiment 3 only if camera dependent silhouette and real occlusion are essential. Experiment 2 is useful when the desired result is a shallow embossed surface rather than a graphic offset or physical sign.

The path of least resistance for bold typography is one outlined SVG on one face, followed by a fixed optical extrusion inside `faceStencilShader`. The path to actual 3D is a contour geometry layer built from the existing face instances and instanced mesh core.

## Evidence and unknowns

Verified live at the exact head:

- `pnpm exec vitest run tests/faceStencilRender.test.ts tests/stencilOrientation.test.ts tests/sceneMorph.test.ts --project unit`: 3 files and 31 tests passed.
- `pnpm exec vitest run tests/stencilRendering.browser.test.ts --project chromium`: 1 file and 1 Chromium test passed.
- The worktree was clean before the scout.

The current tests prove atlas shape, program composition, one packed stencil patch, stable resources, face UV orientation, figure colour tweening, and discrete figure cuts. They do not prove typography fidelity, optical extrusion quality, bevel quality, SVG contour triangulation, geometry cost, transparent sorting, or delivery budget delta. Those remain experiment outcomes.
