---
title: Cubicell renderer spike scout
type: projects
tags: [cubicell, renderer, scout, reuse, optical-lighting, bevels]
summary: Read only reuse and architecture map for comparing flat, optical, and bevelled cube rendering on current main
status: active
created: 2026-08-16
updated: 2026-08-16
project: cubicell
confidence: high
---

# Cubicell renderer spike scout

Baseline: local `main` at `ee511b8a8557c3d4af48079af6dfb4d7a88aab59`. Initial `git status --short` was empty. Repository source, tests, branches, generated files, and configuration were not changed.

## Verdict

The cheapest live path is the existing unlit optical treatment. The editor already shifts each face and every edge in OKLab before writing instance colours. A controlled spike can compare flat and optical cubes by changing only `ScenePolarityConfig`, while retaining the current planes, boxes, instance slots, content shader, picking, selection chrome, motion, capture, and thumbnail machinery.

Small bevelled geometry is suitable as a scratch comparison only. Replacing visible edge boxes with Three's installed `RoundedBoxGeometry` can reuse the shared instanced mesh factory, but it is not promotion ready. Unit rounded geometry is nonuniformly scaled into every edge bar, edge junction resolution assumes rectangular material, the live edge coverage pass remains square, and thumbnails classify edge layers differently. A unified rounded cube would also discard the product's six face and twelve edge ownership model.

Recommendation: run the three way visual comparison in the current live path, with one scratch only build setting. Start with the existing optical ramp. Stop if it gives enough depth during orbit, motion, capture, and thumbnail review. Physical geometry earns a production design only if it produces a clear user visible improvement after those checks.

## Reuse Map

| Needed capability | Existing owner and evidence | Disposition |
| --- | --- | --- |
| Face and edge geometry derivation | `src/domain/cubeGeometry.ts:createCubeFacePlanes` emits six independently positioned planes. `createCubeEdgeSegments` emits twelve independently sized bars. `src/domain/edgeResolution.ts:resolveEdgeDrawSegments` and `src/domain/edgeJunctionResolution.ts:trimJunctionContention` resolve shared bars and junctions. | Reuse. Do not create a parallel cube geometry derivation. |
| Scene instance derivation | `src/scene/cubeInstances.ts:createCubeCellInstances` turns face planes and resolved edge segments into stable matrices and part records. `createCubeSceneInstances` owns the canonical full scene result. | Reuse unchanged for all three variants. |
| Incremental instance ownership | `src/scene/incrementalCubeSceneOwner.ts:createIncrementalCubeSceneOwner`, `src/scene/cubeInstanceSlots.ts:createCubeInstanceSlotState`, and `src/scene/instanceSlotRegistry.ts:createInstanceSlotRegistry` own stable slots and attribute patches. | Reuse unchanged. A renderer treatment is global presentation state, so it must not enter authored operations or slot identity. |
| Shared geometry and material creation | `src/scene/instancedPartMeshCore.ts:createInstancedPartMesh` chooses the current unit `PlaneGeometry` or `BoxGeometry`. `createInstancedPartMeshWithGeometry` accepts any `BufferGeometry`, creates the material and `InstancedMesh`, and installs shared attributes. `syncInstancedPartMesh`, `patchInstancedPartMesh`, `growInstancedPartMesh`, and `disposeInstancedPartMesh` own the full GPU lifecycle. Direct callers are `src/scene/InstancedPartMesh.tsx:InstancedPartMesh`, `src/scene/SelectionChromeLayer.tsx:SelectionChromeBatchMesh`, and `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact`; `src/scene/edgeCoverageCore.ts:createEdgeCoverageMesh` uses the custom geometry seam. | Reuse. Put any scratch geometry substitution at this owner. Scope it to visible authored edges so hit targets, slots, chrome, seams, and the custom coverage mesh retain their current geometry. |
| Current optical treatment | `src/theme/scenePolarity.ts:cubeFaceLightnessDeltaById` is a fixed unlit face ramp. `workbenchScenePolarities` supplies it and `workbenchEdgeLightnessDelta`. `src/scene/colorSpace.ts:shiftLightnessForContrast` preserves hue in OKLab. `src/scene/instancedPartMeshCore.ts:resolveTreatedPartColor` applies the face or edge delta before `InstancedMesh.setColorAt`. | Reuse first. Flat and optical need no material, light, geometry, persistence, or morph change. Use the same background and base palette during the comparison so the ramp is the only variable. |
| Face content and shader composition | `src/scene/stencilAtlas.ts:createStencilAtlas` owns the R8 coverage and RGBA media textures. `src/scene/faceContentShader.ts:applyFaceContentShader` composes the prior material hook and fixed program key, then samples content through the plane UV. `writeFaceContentAttribute` owns per instance content data. `src/scene/instancedPartMeshCore.ts:writeContent` routes stencil and text colours through the same optical colour treatment while image pixels stay untinted. | Reuse unchanged. Do not add bevel identity, radius, or content ids to shader program keys. Any later shader treatment must compose with opacity and face content hooks. |
| Live layer composition | `src/scene/renderCubeScenePartLayers.tsx:renderCubeScenePartLayers` mounts opaque, translucent, ghost, hit target, and slot meshes. It also mounts `src/scene/EdgeCoverageLayer.tsx:EdgeCoverageLayer` ahead of resolved edges. | Reuse for the scratch so the comparison exercises the real canvas. Keep the square coverage pass visible during evaluation and record whether it masks the rounded edge result. |
| Face picking and hover | `src/scene/InstancedPartMesh.tsx:InstancedPartMesh` resolves `event.instanceId` back to the current slot. `src/scene/useCubeSceneInteractions.ts:useCubeSceneInteractions` maps a face hit to cube, face, or perimeter edge grammar. Visible face planes are the raycast surface. | Reuse unchanged for flat and optical. A unified rounded cube is wrong shaped because one cube instance cannot preserve current face slot identity. |
| Edge picking | `src/scene/renderCubeScenePartLayers.tsx:renderCubeScenePartLayers` keeps a separate `edgeHitTargets` box layer on the picking layer. `src/scene/useCubeSceneInteractions.ts:useCubeSceneInteractions` maps the resolved instance to `CubeEdgeInstance`. | Reuse unchanged. A scratch bevel should alter visible edges only and leave these generous boxes intact. |
| Selection chrome and focus | `src/scene/selectionChromeInstances.ts:createSelectedChromeBatches` derives cube, face, and edge frames from `CubeSize` and topology. `src/scene/SelectionChromeLayer.tsx:SelectionChromeLayer` renders separate noninteractive chrome. `src/view/focusGeometry.ts:getFocusBounds` and `getSelectionPartPose` derive framing from the same size, face plane, and edge segment owners. | Reuse unchanged while the bevel remains inside current bounds. Physical geometry outside those bounds requires a deliberate chrome and framing change. |
| Motion and morph | `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology`, `sampleSceneMorph`, and `interpolateCell` own pose, size, scale, opacity, thickness, and colour interpolation. `src/scene/useCubeSceneRenderState.ts:useCubeSceneRenderState` and `src/scene/useCubeSceneInstances.ts:useCubeSceneInstances` feed the same instance path during playback. | Reuse unchanged for a global treatment. Do not add a bevel field to `CubeCell`, face state, edge state, State, or transition data during the spike. |
| Thumbnails | `src/thumbnail/thumbnailRenderer.ts:createOrthographicThumbnailRenderer` owns the separate WebGL context. Its private `renderThumbnail` uses `createCubeSceneInstances` and `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact`, which calls the same instanced mesh core and face content shader. | Reuse and prove parity. The artifact layer descriptors need correct edge classification before a part kind based treatment can be promoted. |
| Capture and storyboard proof | `src/studios/editor/useRecordingCapability.ts:createRecordingController` registers the live canvas and captures PNG bytes. `src/studios/editor/useStudioObservationControl.ts:useStudioObservationControl` exposes capture and storyboard. `scripts/verifyMcpObservation.ts` calls `cubicell_capture` and `cubicell_storyboard` and checks both against the same document revision. | Reuse for live evidence. It covers the real canvas and thumbnail storyboard without a second capture path. |
| Delivery ownership and timing | `budgets/initial-delivery.json` owns shared renderer, editor, thumbnail, and capability size limits. `scripts/check-delivery-budget.mjs` enforces bundle and ownership limits. `scripts/measure-initial-delivery.mjs` measures real WebGL draw calls, first draw, committed frame, and main thread tasks. | Reuse both. Bundle budget alone does not measure the extra vertex work of rounded geometry. |

## Quality Map

### Q1. Live and thumbnail layer metadata has already drifted

Signal: parallel layer declarations. `src/scene/renderCubeScenePartLayers.tsx:renderCubeScenePartLayers` marks live edge meshes with `partKind="edge"`. `src/thumbnail/thumbnailArtifact.ts:layerDescriptors` gives thumbnail edges `geometryKind: "box"`, while `createThumbnailArtifact` supplies `partKind` only for face layers. `src/scene/instancedPartMeshCore.ts:createColorWriteContext` applies edge treatment only when the mesh kind is `edge`.

Impact: a part kind based optical or geometry treatment can reach live edges and miss thumbnail edges. This is a current latent mismatch and a direct promotion blocker.

Disposition: refactor first if the selected treatment depends on part kind. Give the four authored thumbnail layers explicit face or edge classification, then keep visual geometry selection in the shared mesh owner.

### Q2. Material hook composition is order sensitive

Signal: `src/scene/instancedPartMeshCore.ts:applyInstanceOpacity` assigns `onBeforeCompile` and `customProgramCacheKey`. `src/scene/faceContentShader.ts:applyFaceContentShader` deliberately captures and invokes the previous hook. `src/scene/edgeCoverageCore.ts:createEdgeCoverageMesh` owns another custom hook on its private material.

Impact: a new optical shader can silently replace opacity or content behavior if it assigns hooks in the wrong order. Both opacity and content replace shared shader chunks.

Disposition: reuse the current CPU colour ramp for the first optical comparison. If a shader experiment follows, make every patch compose the prior hook and key at the shared material owner. Add one focused real WebGL contract for translucent content before promotion.

### Q3. Rounded edge bars conflict with rectangular junction ownership

Signal: `src/domain/edgeJunctionResolution.ts:collinearButtExtension` requires matching cross sections so end caps coincide vertex for vertex. `flushRetreat` proves coverage with rectangular boxes. `src/domain/cubeGeometry.ts:createCubeEdge` extends hard bars through corners. `src/scene/edgeCoverageCore.ts:createCoverageBoxGeometry` adds a separate square coverage box in the live canvas.

Impact: rounded caps can expose corner gaps, overlap in a different shape than the resolver proves, or appear square again under the coverage pass. Adjacent cells, unequal thicknesses, rotations, and nonuniform scale are the failure cases.

Disposition: scratch only. Do not call rounded edge bars a physical bevel until junctions and coverage are redesigned against the chosen geometry.

### Q4. Installed rounded geometry is expensive and scales the radius incorrectly

Signal: Three `0.185.1` ships `three/addons/geometries/RoundedBoxGeometry.js`. A read only probe on this checkout measured:

| Geometry | Position vertices per shared geometry |
| --- | ---: |
| `BoxGeometry(1,1,1)` | 24 |
| `RoundedBoxGeometry(1,1,1,1,0.06)` | 324 |
| `RoundedBoxGeometry(1,1,1,2,0.06)` | 900 |

Current edge bars use one unit geometry plus nonuniform instance matrices. For a representative scale `[0.04, 2, 0.04]`, the nominal radius becomes `0.0024` on the thin axis and `0.12` on the long axis. `src/domain/cubeTopology.ts:CubeSize` also permits independent width, height, and depth. `src/evaluation/sceneMorph.ts:interpolateCell` changes size and scale continuously.

Impact: one shared rounded unit box gives elliptical and breathing bevels. Segment one multiplies edge vertex work by 13.5. Segment two multiplies it by 37.5, before the unchanged coverage pass.

Disposition: use segment one only for the visual scratch. Treat its result as a proxy. Production physical geometry needs a radius policy that survives nonuniform size and motion, plus a measured frame budget.

### Q5. Current contracts stop before real geometry, material, and picking proof

Signal: `tests/contracts/incremental-scene-equivalence.contract.test.ts` compares derived instance keys, matrices, colours, and opacity. `tests/contracts/thumbnail-camera.contract.test.ts` covers camera direction and cache identity. `tests/contracts/face-media-loop.browser.contract.test.ts` proves persistence and atlas bytes in Chromium. None constructs the live R3F layer tree, asserts geometry selection, clicks the rendered face and edge meshes, or compares live and thumbnail pixels. The current governance file lists no renderer treatment contract.

Impact: unit and browser suites can remain green while a treatment breaks picking, translucent face content, rounded junctions, or thumbnail parity.

Disposition: promotion requires a focused real browser contract and a live capture review. Keep the test below the 700 line governance limit and add it to the correct unit or browser list.

### Q6. No hygiene threshold breach was found in the inspected owners

The largest inspected renderer files remain below the 700 line limit. The relevant functions remain below about 150 lines. Structural duplicate scanning found no function cluster at score `0.90` in `src/scene` or `src/thumbnail`, and the source runtime graph reported no dependency cycle. The concrete duplication is the live and thumbnail layer metadata in Q1.

## Risk classification

| Variant | Geometry and topology | Picking and selection | Motion and morph | Thumbnail and capture | Performance and budgets | Overall |
| --- | --- | --- | --- | --- | --- | --- |
| Current flat artifact | Existing planes and boxes | Existing behavior | Existing behavior | Existing authored colour behavior | Current baseline | Low |
| Existing optical ramp | No geometry change. CPU instance colour only. | No change | Colour writes already follow patch and tween paths | Thumbnail can reuse it after edge classification and an explicit authored colour decision | Negligible geometry cost. Bundle delta can be zero | Low |
| UV or normal based optical shader | Existing geometry. New material hook. | Geometry unchanged | Geometry unchanged | Must compose with the content shader in both WebGL contexts | Small vertex cost, uncertain fragment cost and program count | Medium |
| Rounded visible edge bars | Same twelve edge identities, custom shared geometry | Edge hit boxes can stay unchanged. Chrome stays hard edged | Radius distorts with size and scale morph | Thumbnail needs edge kind parity. Live coverage remains square | 13.5 times edge vertices at segment one | High for promotion |
| Unified rounded cube | Replaces six face and twelve edge instances with one body | Breaks current face and edge instance identity | Needs a new geometry and transition model | Breaks per face content and artifact layers | New draw, material, and geometry design | Reject for this spike |

## Wrong shaped alternatives

1. `MeshStandardMaterial` plus lights. Reject. `src/scene/instancedPartMeshCore.ts:createInstancedPartMeshWithGeometry` creates `MeshBasicMaterial`. `src/scene/CubeScene.tsx:CubeScene` mounts no light. `src/thumbnail/thumbnailRenderer.ts:renderThumbnail` creates a bare `Scene` with no light. This route requires two light rigs, material hook adaptation, and capture parity before it renders correctly.

2. `@react-three/drei/RoundedBox`. Reject. The installed component creates an independent React mesh and extruded geometry. It bypasses stable instance slots, incremental patches, part kind colour treatment, face and edge picking, and the thumbnail artifact owner.

3. One Three `RoundedBoxGeometry` instance per cube. Reject. The current product semantics are six face instances and twelve edge instances. Face content stores one independent content value per face and the handler resolves selection from the instance slot. One cube instance cannot carry those contracts without a new representation.

4. A persisted `bevel` field on cube, face, edge, State, or transition data. Reject for the spike. The comparison is a global visual treatment. Persistence and morph expansion adds risk before user value exists.

5. A second renderer or a Design System only mock. Reject. It would miss incremental ownership, selection, motion, real capture, and thumbnail behavior. The existing shared mesh seam is already small enough for a scratch treatment.

## Plan

### 1. Create one disposable treatment owner

On a scratch branch, add one build setting with the closed values `flat`, `optical`, and `rounded-edges`. A Vite setting such as `VITE_CUBICELL_RENDERER_TREATMENT` is enough. Parse it once in the renderer package. Do not add a UI control, persisted preference, operation, store field, or compatibility path. Delete the setting after the decision.

The flat and optical variants must share the same background and base part colours. Flat supplies no grooming deltas. Optical supplies the existing `cubeFaceLightnessDeltaById` and edge delta. This isolates optical depth from the separate workbench palette.

### 2. Keep geometry substitution inside the current factory

For `rounded-edges`, import Three's installed `RoundedBoxGeometry` directly. Use segment one and a small radius. Select it only in `src/scene/instancedPartMeshCore.ts:createInstancedPartMesh` for visible authored edge meshes. Do not change `createInstancedPartMeshWithGeometry`, because edge coverage already owns explicit geometry there. Do not change picking boxes, neighbor slots, selection chrome, seams, or face planes.

Before thumbnail comparison, correct `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` so authored edge layers carry edge part kind. Keep the same instance arrays, sync path, atlas, camera, and disposal.

### 3. Use one fixed comparison scene

Evaluate the three variants with the same saved document and camera:

1. One cube, then orbit head on and at 45 degrees.
2. A `2 x 2 x 2` block to expose shared edge and corner junctions.
3. One nonuniform cube and one cube with nonuniform placement scale.
4. Thin and thick edge states.
5. Black and white scene polarities.
6. Plain faces, stencil or text, a transparent image, and an opaque image.
7. Cube, face, and edge selection, hover, double click drill, and neighbor placement.
8. A State transition that changes size, scale, edge thickness, opacity, and colour.
9. Live canvas capture and the same States in the thumbnail storyboard.

Stop physical work if optical wins during orbit and both capture paths. Stop rounded edge promotion if it needs the coverage pass disabled, exposes junction gaps, distorts on the nonuniform cube, or disagrees with thumbnails.

### 4. Exact live proof commands

Use a fresh scratch worktree. Run one variant per server start:

```sh
VITE_CUBICELL_RENDERER_TREATMENT=flat pnpm dev --host 127.0.0.1 --port 4173
VITE_CUBICELL_RENDERER_TREATMENT=optical pnpm dev --host 127.0.0.1 --port 4173
VITE_CUBICELL_RENDERER_TREATMENT=rounded-edges pnpm dev --host 127.0.0.1 --port 4173
```

For each running variant, open exactly one visible editor tab, load the same document, set the same camera, and capture the visible page:

```sh
pnpm exec playwright screenshot --browser chromium --viewport-size "1440, 900" --wait-for-selector ".cube-canvas canvas" --wait-for-timeout 1500 http://127.0.0.1:4173 /tmp/cubicell-renderer-flat.png
pnpm exec playwright screenshot --browser chromium --viewport-size "1440, 900" --wait-for-selector ".cube-canvas canvas" --wait-for-timeout 1500 http://127.0.0.1:4173 /tmp/cubicell-renderer-optical.png
pnpm exec playwright screenshot --browser chromium --viewport-size "1440, 900" --wait-for-selector ".cube-canvas canvas" --wait-for-timeout 1500 http://127.0.0.1:4173 /tmp/cubicell-renderer-rounded-edges.png
```

With the same visible tab, prove the real capture and storyboard owners return revision linked PNGs:

```sh
CUBICELL_MCP_VERIFY_WAIT_MS=30000 pnpm verify:mcp
```

Run focused behavioral contracts, then the browser set:

```sh
pnpm exec vitest run tests/contracts/incremental-scene-equivalence.contract.test.ts tests/contracts/thumbnail-camera.contract.test.ts --project unit --no-cache --maxWorkers=1
pnpm test:browser
```

Build and measure each variant independently. The build setting belongs on the build command because measurement reads the completed `dist` tree:

```sh
VITE_CUBICELL_RENDERER_TREATMENT=flat pnpm build:budget
node scripts/check-delivery-budget.mjs
CUBICELL_MEASUREMENT_OUTPUT=/tmp/cubicell-renderer-flat.json pnpm measure:initial-delivery

VITE_CUBICELL_RENDERER_TREATMENT=optical pnpm build:budget
node scripts/check-delivery-budget.mjs
CUBICELL_MEASUREMENT_OUTPUT=/tmp/cubicell-renderer-optical.json pnpm measure:initial-delivery

VITE_CUBICELL_RENDERER_TREATMENT=rounded-edges pnpm build:budget
node scripts/check-delivery-budget.mjs
CUBICELL_MEASUREMENT_OUTPUT=/tmp/cubicell-renderer-rounded-edges.json pnpm measure:initial-delivery
```

Compare `aggregate.firstDrawToCommittedFrame`, `aggregate.gates`, and each run's draw counts and draw call duration. A bundle pass does not clear a rounded geometry regression.

### 5. Promotion boundary

If optical wins, make the chosen grooming values permanent in `src/theme/scenePolarity.ts` and decide explicitly whether authored preview, thumbnails, and export should retain exact authored colours or receive the same optical treatment. Delete the scratch setting and rounded import.

If rounded edges win, stop before merging the scratch. Write a separate production design for radius under nonuniform size and motion, edge junction material, edge coverage, thumbnail layer parity, selection chrome, and real browser proof. Preserve the current face planes and per face content unless that design explicitly replaces the product topology.

## Verification record

- Initial branch: `main`.
- Initial head: `ee511b8a8557c3d4af48079af6dfb4d7a88aab59`.
- Initial `git status --short`: empty.
- Final `git status --short`: empty after the artifact write.
- Repository writes: none.
- Source verification: direct reads of the named files and symbols, caller mapping, dependency closure, current contract tests, package scripts, budget owners, and installed Three geometry source.
- Read only geometry probe: 24 positions for the current box, 324 for rounded segment one, and 900 for rounded segment two.
- Final artifact and repository status are verified after this file is written.
