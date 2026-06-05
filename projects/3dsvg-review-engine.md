---
title: 3dsvg engine architecture review
type: projects
tags:
  - 3dsvg
  - cubicell
  - architecture
  - renderer
  - comparison
summary: Engine and code architecture comparison of 3dsvg and Cubicell, with ranked reuse recommendations.
status: active
project: cubicell
confidence: high
created: 2026-08-22
updated: 2026-08-22
---

## Engine Architecture, Honestly

This review compares 3dsvg at `424b26e8e9475936836581228d45f5aa1928e172` with Cubicell at `bd43225`. Both worktrees remained clean during the review.

3dsvg has three architectural layers:

1. `packages/engine/src/index.tsx · SVG3D` is a convenient public facade. It accepts text, inline SVG, or a URL, resolves fonts and materials, lazy loads the scene component, and renders a self contained canvas.
2. `packages/engine/src/scene.tsx · SVG3DScene`, `ExtrudedSVG`, and `useExtrudedGeometry` own the Three.js scene, SVG parsing, extrusion, merged geometry, lights, environment, shadows, camera, asset progress, and children injected into the canvas.
3. `packages/engine/src/controls.tsx · IntroAnimation`, `LoopAnimation`, and `SmoothControls` mutate camera or group transforms on every frame. Drag rotation, wheel zoom, cursor response, momentum, intro state, and animation phase live inside React refs rather than in the public props.

The web editor adds a fourth layer. `packages/web/src/app/page.tsx · Home` owns the editable state, `packages/web/src/components/svg-to-3d-canvas.tsx · SVGTo3DCanvas` maps that state into the engine, and injected children recover access to the private canvas for capture, light helpers, and mesh export. This division makes 3dsvg a viable standalone presentation widget. It does not provide a stable authored document, an immutable render input, or a deterministic frame contract.

`SVG3DProps` looks declarative, but the visual result is only partly represented by it. The current dragged pose, cursor pose, zoom, animation phase, intro completion, loaded texture, asset readiness, and export traversal state are imperative. `packages/engine/src/types.ts · defaultProps` covers only part of the public bag, while other defaults live in `SVG3D`, `SVG3DScene`, web state, and the embed generator. The result is observable drift:

- `packages/web/src/app/page.tsx · Home` starts with cursor orbit disabled. `packages/web/src/components/embed-dialog.tsx · generateProps` omits the false value, so the engine default enables it in the generated embed.
- `packages/web/src/lib/types.ts · defaultLightSettings` uses position `[2, 2, 4]`. The serializer treats that position as omittable, while `packages/engine/src/scene.tsx · SVG3DScene` defaults to `[5, 8, 5]`.
- `SVGTo3DCanvas` adds the editor background plane and enables scroll zoom. `generateProps` serializes neither behavior.
- `TextureSettings.repeatY` is editable, but `SVGTo3DCanvas` sends only `repeatX` through the engine's scalar `textureRepeat` prop.
- Uploaded blob texture URLs work only in the editor session that created them.

The package boundary is useful evidence for API ergonomics, but the current implementation would be a trap for Cubicell's renderer extraction. `packages/engine/src/scene.tsx · module initialization` replaces global `console.warn`. `packages/engine/src/controls.tsx · introComplete` shares mutable state across instances. `packages/engine/tsup.config.ts · default export` builds root and subpath entries without shared chunks, so importing both entry paths creates distinct copies of exported objects and the readiness singleton. The root export surface also statically exports the scene that `SVG3D` attempts to lazy load.

Cubicell already has a real internal loading seam through `src/studios/catalog.ts · beginStudioLoad` and `src/renderer/SharedRendererModule.ts · Canvas`. Its gap is deeper. `src/renderer/contract.ts · SharedRendererCanvasProps` still carries React components, Zustand state, `InteractionCore`, journal batches, transport state, selection, DOM capture registration, and editor callbacks. `src/scene/CubeScene.tsx · CubeScene` also owns camera gestures, editor chrome, transport, picking, atlas lifecycle, and rendering. A publishable player wrapped around that contract would preserve the coupling.

The extraction order should therefore be contract, asset closure, adapter, then packaging. The proposed `PROJECT.EXPORT.md · RenderSnapshot` points in the right direction, but remains unimplemented. One runtime neutral render source and immutable frame snapshot should feed editor preview, deterministic export, thumbnails, and a later player. `src/thumbnail/thumbnailArtifact.ts · createThumbnailArtifact` already proves that Cubicell can construct a reusable artifact without mounting the editor canvas.

Code quality reinforces that verdict. `packages/web/src/components/export-bar.tsx` is 782 lines, `packages/web/src/components/controls-panel.tsx` is 676 lines, and `packages/engine/src/scene.tsx` is 654 lines. `ExportModal`, `ControlsPanel`, `SVG3DScene`, and `SmoothControls` each carry too many responsibilities. `Home` uses 37 local state cells, and `ControlsPanelProps` relays 39 props. There is no behavioral test suite. Strict TypeScript checks pass for both 3dsvg packages, but they do not exercise multi instance state, generated embed parity, stale asset completion, disposal, frame rate independence, or export state restoration.

## Worth Leveraging (ranked, highest value first)

| Idea | 3dsvg owner (path + symbol) | Gap it fills in cubicell | Cubicell landing site (path + symbol) | Effort S/M/L |
| --- | --- | --- | --- | --- |
| 1. One runtime neutral render source and immutable frame snapshot | `packages/engine/src/types.ts · SVG3DProps`; `packages/engine/src/index.tsx · SVG3D` | 3dsvg demonstrates the value of one small render input, while its mixed prop bag shows why authored data, evaluated frame state, runtime ports, interaction policy, and callbacks need distinct types. Cubicell's current canvas contract still exposes editor ownership. | `src/renderer/contract.ts · SharedRendererCanvasProps, SharedRendererModule`; `src/studios/editor/EditorRendererBinding.tsx · EditorRendererBinding`; `src/transport/stagedScene.ts · createStagedSceneReader`; proposed `src/renderer/RenderSnapshot.ts · RenderSource, RenderSnapshot` | L |
| 2. Host scoped, explicit player input policy | `packages/engine/src/types.ts · SVG3DProps`; `packages/engine/src/controls.tsx · SmoothControls` | A Cubicell embed needs an explicit static or inspect capability, page safe wheel behavior, host scoped pointer coordinates, and optional keyboard input. The current editor flag suppresses selection presentation but still mounts the camera driver and global listeners. | `src/interaction/authority.ts · CameraAuthority`; `src/camera/cameraGestureRuntime.ts · useCameraGestureControls`; `src/camera/cameraAuthorityRuntime.ts · createCameraAuthorityRuntime`; proposed `src/player/PlayerInputPolicy.ts · PlayerInputPolicy` | M |
| 3. A thin standalone player adapter after contract and asset closure | `packages/engine/src/index.tsx · SVG3D`; `packages/web/src/components/svg-to-3d-canvas.tsx · SVGTo3DCanvas` | Cubicell has internal renderer loading but no standalone HTML, ESM, or React player. The adapter must close over payload bytes or accept a resolver, mount one runtime contract, report readiness, resize, and dispose. It should remain downstream of editor and export independent owners. | `src/renderer/SharedRendererModule.ts · Canvas`; `src/studios/catalog.ts · beginStudioLoad`; `src/shared/imagePayloadSource.ts · ImagePayloadSource`; proposed `src/player/CubicellPlayer.tsx · CubicellPlayer, PlayerHandle` | L |
| 4. Separate presentation transforms by writer | `packages/engine/src/scene.tsx · SVG3DScene`; `packages/engine/src/controls.tsx · LoopAnimation, SmoothControls` | 3dsvg places loop motion and interaction motion on nested groups, which prevents the two writers from overwriting one transform. If Cubicell gains cursor response or idle return in a player, presentation motion needs an equally explicit layer outside authored score evaluation. | `src/evaluation/scoreAt.ts · scoreAt`; `src/camera/cameraAuthorityRuntime.ts · createCameraAuthorityRuntime`; proposed `src/scene/ArtifactPresentationRoot.tsx · ArtifactPresentationRoot` | M |

The first item is the architectural prerequisite. The player should consume the same frame contract as deterministic export. A player specific scene model would create a second source of truth. The render source also needs a dependency complete asset manifest or an injected payload resolver because `PayloadAsset` stores identifiers and metadata while project storage owns the bytes.

The fourth item is deliberately conditional. Authored motion remains in pure score evaluation, camera motion remains in camera authority, and optional output only presentation motion gets its own transform owner. This preserves the distinction between authored state and viewer decoration.

## Cannot Cross The Line

| 3dsvg mechanism | Why it conflicts with Cubicell | Cubicell owner to preserve |
| --- | --- | --- |
| PBR presets, transmission, environment maps, fixed fill lights, and contact shadows | They make light and material response part of runtime physics. Cubicell's palette, face ramp, edge contrast, and polarity are authored visual semantics. | `src/scene/instancedPartMeshCore.ts · createInstancedPartMesh`; `src/scene/cubeInstances.ts · quantizeFaceLightnessDelta`; `src/theme/scenePolarity.ts · ScenePolarityConfig` |
| One merged, anonymous SVG extrusion | Cubicell depends on stable cube, face, edge, neighbor, and instance slot identity for selection, burial, persistence, thumbnails, animation, and incremental GPU writes. | `src/scene/cubeInstances.ts · createCubeCellInstances`; `src/scene/cubeInstanceSlots.ts · getCubeInstancePartKey`; `src/scene/instanceSlotRegistry.ts · createInstanceSlotRegistry` |
| Triplanar mesh textures | Cubicell content is assigned to explicit faces through Library assets, media bindings, atlas slots, and face shaders. A mesh texture would bypass those identities and durability rules. | `src/scene/stencilAtlas.ts · createStencilAtlas`; `src/domain/content.ts · CubicellContent`; `src/scene/faceContentShader.ts · applyFaceContentShader` |
| Direct transform mutation from browser events and frame callbacks | It would create competing camera and artifact writers, bypass semantic commands, and make output depend on event and frame history. | `src/camera/cameraAuthorityRuntime.ts · createCameraAuthorityRuntime`; `src/editor/commands.ts · ViewCommand`; `src/evaluation/scoreAt.ts · scoreAt` |
| Permanent frame callbacks | Cubicell renders on demand and requires every motion producer to wake the shared scheduler. Continuous updates would weaken performance and deterministic frame control. | `src/scene/renderScheduler.ts · createRenderScheduler`; `src/scene/CubeScene.tsx · CubeScene` |
| Component local asset ownership | Cubicell assets require durable identity, payload resolution, atlas lifecycle, stale job protection, and cleanup. | `src/capabilities/media/MediaCapability.ts · importSvgFile, importImageFile, importVideoFile`; `src/scene/stencilAtlas.ts · createStencilAtlas`; `src/state/projectDurability.ts · ProjectDurabilityRuntime` |

SVG may continue to cross the boundary as face content. Spatial SVG extrusion would introduce a new authored object kind and require an explicit product decision plus new topology, selection, persistence, animation, thumbnail, export, and instancing rules.

## Cubicell Already Does This Better

- **One staged scene authority.** `src/transport/stagedScene.ts · createStagedSceneReader` and the evaluation layer derive the displayed stage from authored state. 3dsvg's editor spreads the visual result across local state, refs, loaders, and scene mutations.

- **Stable render identity and incremental GPU ownership.** `src/scene/cubeInstances.ts · createCubeCellInstances`, `src/scene/cubeInstanceSlots.ts · createCubeInstanceSlotOwner`, and `src/scene/instanceSlotRegistry.ts · createInstanceSlotRegistry` preserve explicit parts and stable slots. 3dsvg rebuilds and merges the extrusion when relevant props change.

- **Live and thumbnail parity.** `src/thumbnail/thumbnailArtifact.ts · createThumbnailArtifact` reuses the same layer, material, instance, polarity, and atlas owners. 3dsvg has no comparable artifact contract separate from its canvas.

- **A single camera authority.** `src/camera/cameraAuthorityRuntime.ts · createCameraAuthorityRuntime`, `src/camera/cameraTrackball.ts · createTrackballControls`, and `src/interaction/viewLane.ts · coalesceViewCommandsInto` route view intent through one command driven writer. 3dsvg splits camera and transform writes across intro, cursor, pointer, wheel, pinch, responsive zoom, and loop components.

- **Time based authored motion.** `src/evaluation/scoreAt.ts · scoreAt` and its staging pipeline evaluate authored time as pure data. 3dsvg's loop transforms accumulate from frame history, and its fixed smoothing coefficients vary with frame rate.

- **Asset lifecycle and stale completion safety.** `src/scene/stencilAtlas.ts · createStencilAtlas` has typed pending, written, failed, and absent states, generation safety, stable texture identity, stale assignment rejection, and disposal. 3dsvg's geometry and texture loaders can leak their current resources or let a stale texture request win.

- **Demand rendering.** `src/scene/renderScheduler.ts · createRenderScheduler` coordinates motion producers with `frameloop="demand"`. 3dsvg registers frame callbacks that keep every canvas active.

- **Recording ownership.** `src/export/streamRecorder.ts · createRecordingController` centralizes stream acquisition, state, bounded duration, cleanup, and errors. 3dsvg's export modal combines capture, recording, geometry traversal, UI, renderer mutation, and encoding in one large component.

## Looked At And Rejected

1. **The complete `SVG3D` facade as Cubicell's renderer core.** `packages/engine/src/index.tsx · SVG3D` is useful as shell ergonomics. Its prop bag mixes source acquisition, authored appearance, layout, interaction, animation, runtime callbacks, and escape hatches. Cubicell first needs a renderer contract with no editor, React, storage, or DOM ownership.

2. **The current 3dsvg package build.** `packages/engine/tsup.config.ts · default export` and `packages/engine/src/index.tsx · SVG3DScene public export` defeat the intended lazy scene boundary and permit duplicated module state across root and subpath imports. Cubicell's current internal lazy renderer seam is already sounder.

3. **`SVG3DProps` and `defaultProps` wholesale.** `packages/engine/src/types.ts · SVG3DProps, defaultProps` allow zero or several content sources, type runtime fonts as arbitrary strings, split defaults across owners, and combine frame input with behavior. The material values inside `defaultProps` can also overwrite a selected material preset when consumers spread them in the usual order.

4. **`SmoothControls` as an implementation.** `packages/engine/src/controls.tsx · SmoothControls` uses fixed per frame damping, pointer displacement as velocity, window wide cursor coordinates normalized to the viewport, and incomplete pointer cancellation. The useful interaction ideas must enter Cubicell as semantic camera commands and scheduled, delta aware producers.

5. **`LoopAnimation` as playback.** `packages/engine/src/controls.tsx · LoopAnimation` mutates group transforms from elapsed frame time and can retain transforms when the animation kind changes. Cubicell's score and Moment evaluation already provide a deterministic authored owner.

6. **The material and lighting system.** `packages/engine/src/materials.ts · materialPresets`, `packages/engine/src/materials.ts · resolveMaterial`, and `packages/engine/src/scene.tsx · SVG3DScene` conflict with Cubicell's unlit, quantized visual identity. The apparent opacity control also changes physical transmission rather than mesh opacity.

7. **The extrusion pipeline as a Cubicell object pipeline.** `packages/engine/src/scene.tsx · useExtrudedGeometry, ExtrudedSVG` contains useful parsing and batching ideas, but produces merged geometry without Cubicell part identities. Its disposal also trails by one generation and does not dispose the current result on unmount. Keep imported SVG within the current Library and atlas path unless Stuart approves a new spatial object domain.

8. **The editor state and prop relay.** `packages/web/src/app/page.tsx · Home` and `packages/web/src/components/controls-panel.tsx · ControlsPanelProps` replace a document boundary with 37 state cells and a 39 prop relay. Cubicell's domain, state, evaluation, and capability boundaries are stronger.

9. **Generated embed code as state serialization.** `packages/web/src/components/embed-dialog.tsx · generateProps` changes cursor orbit, light position, background behavior, scroll zoom, and session asset validity. It also drops `repeatY`. An embed must serialize one canonical render source and declared input policy, then pass a parity test against the editor frame.

10. **Raw canvas and scene escape hatches.** `packages/engine/src/types.ts · SVG3DProps.children, registerCanvas`, `packages/web/src/components/export-bar.tsx · collectExtrudedMeshes, buildExportGroup`, and `packages/web/src/components/download-capture.tsx · DownloadCapture` let downstream code traverse scene internals and mutate renderer, camera, visibility, and background state. Cubicell should expose a narrow player handle and render or export jobs with cleanup guarantees.

11. **The duplicated text pipeline.** `packages/web/src/components/text-input.tsx · FONTS, fontCache, textToSvg` duplicates the engine font list, cache, loader, and conversion logic. The implementations currently match, but they can drift. Cubicell should keep text as one domain content kind with one renderer path.

12. **The export modal architecture.** `packages/web/src/components/export-bar.tsx · ExportModal` is roughly 620 lines inside a 782 line file and owns UI, mesh discovery, transforms, texture baking, GLTF, STL, OBJ, recording settings, and downloads. Cubicell's proposed `ExportJob` should remain a typed job boundary outside panels.

## Open Questions For Stuart

1. Should the first Cubicell player be view only, or should it ship orbit, pan, wheel, keyboard, selection, and timeline controls? Each capability changes the public input and focus contract.

2. Which delivery surface should prove the boundary first: standalone HTML, an ESM mount function, or a React component? Package publication should follow a proven external consumer.

3. What belongs in the versioned render source, and what belongs only in a frame snapshot? Camera pose, timeline time, render dimensions, pixel ratio, polarity, asset manifest, and background policy need explicit ownership.

4. Should payload bytes be embedded in the render source, packaged beside it, or resolved through an injected port? This decision controls portability and offline playback.

5. Is cursor response with idle return a desired Cubicell presentation behavior? If yes, should it affect only player presentation, leaving the authored camera track and exported deterministic frame unchanged?

6. Will SVG remain flat face content, or may it become a spatial authored object? The latter requires a new domain model rather than an engine swap.

7. Should `src/renderer/SharedRendererModule.ts · Canvas` remain the editor adapter over a smaller artifact renderer, or should its public meaning change once the runtime neutral contract exists?
