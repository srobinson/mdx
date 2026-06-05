# Cubicell music visual identity wedge: engineering economics verdict

Basis: committed objects only, `main` at `7d5e942` and `feat/stencil-build` at `66b4d8d`.
The dirty stencil worktree and paused Shell E experiment were not read.

## Decision standard

One slice means one independently reviewable vertical change with focused tests and full required gates.
The campaign is economically sound if prepared content may enter through a concierge build step, audio may be attached in post, and a VJ scene means one live rendered prepared piece.
The current commit is not a self contained music delivery product.

## What `66b4d8d` actually buys

- `src/domain/cube.ts:CubeFaceFigure` gives one face one content identity, semantic colour, form or field region, and margin or bleed fit.
- `src/domain/cube.ts:cubeFaceStateOwner` puts the optional figure through validation, patching, inheritance, compact encoding, selection equality, morph policy, and render impact.
- `src/domain/stencil.ts:StencilAsset` and `createStencilId` establish content addressed SVG metadata and identity.
- `src/domain/seededStencils.ts:seededStencils` owns the exact source, name, region, fit, and colour defaults for two bundled marks.
- `src/scene/stencilAtlas.ts:createStencilAtlas` owns one 2048 square R8 page with sixteen fixed 512 square slots.
- `src/scene/faceStencilShader.ts:applyFaceStencilShader` composes coverage into the existing face material.
- `src/scene/faceStencilShader.ts:writeFaceStencilAttribute` carries slot, region, fit, and figure colour in one `vec4` per face instance.
- `src/scene/cubeInstances.ts:createCubeCellInstances` derives figure state through the existing face instance path.
- `src/scene/instanceSlotRegistry.ts:changedInstanceAttributes` limits figure edits to the stencil attribute.
- `src/editor/controlBindings.ts:faceStencilBinding` applies a bundled mark through the existing `set-face-state` operation and selection scope.
- `src/panels/panelDefinitions.ts:faceBindingIds` adds that selector beside existing face visibility, colour, and opacity controls.
- `src/evaluation/sceneMorph.ts:createPartColorTweens` tweens figure colour when identity, region, and fit remain stable.
- `src/persistence/recordCodecs/stencilRecordCodec.ts:encodeStencilRecord` and `decodeStencilRecord` persist Stencil metadata through the existing asset record path.
- `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` uses the same atlas and face derivation for state thumbnails.
- `tests/stencilRendering.browser.test.ts` proves one face draw, one atlas texture, stable mesh, material and texture identity, no program or texture churn, and four uploaded floats for a stencil edit.

This is low marginal GPU and state cost. New content does not create another render path, draw call, shader identity, state owner, or thumbnail path.

## Foundation gaps and cost

1. Content is compile time only.
   `src/domain/seededStencils.ts:seededStencils`, `src/editor/controlBindings.ts:faceStencilOptions`, and `src/scene/stencilAtlas.ts:rasterizeSeededStencils` all enumerate the bundled registry.
   `src/domain/stencil.ts:StencilAsset` stores metadata without SVG source; `resolveStencilContent` returns unresolved for any nonbundled identity.
   Cost: zero engine slices for a verified campaign content batch, but every batch requires SVG preparation, source addition, hash update, registry edit, tests, and a build.
   A runtime importer would cost at least two slices and is explicitly frozen as general SVG import. The campaign does not require it.
2. Capacity is sufficient only under an explicit content budget.
   `src/scene/stencilAtlas.ts:stencilAtlasCapacity` permits sixteen entries; two are already occupied, leaving fourteen for the campaign.
   Cost: zero slices if the three pieces share or ration fourteen additions. Overflow requires multiple atlas pages, which is explicitly frozen and should stop the content plan rather than expand the engine.
3. The selected bundled asset is not added to the project Library.
   `src/editor/controlBindings.ts:faceStencilBinding` emits only `set-face-state`.
   `src/domain/workbench.ts:getProjectAssetRoster` and `src/persistence/projectRecordProjection.ts:projectRecordContext` derive project ownership only from the Library.
   Cost: one slice to make selection atomically ensure the referenced bundled Stencil asset and to prove save, close, reopen, and deletion integrity.
   Freeze: no. This is completion of the committed persistence contract and is required before merge approval.
4. Figure authoring is narrower than figure state.
   `src/panels/panelDefinitions.ts:faceBindingIds` exposes stencil choice but no figure colour, region, or fit binding.
   `src/scene/faceStencilShader.ts:writeFaceStencilAttribute` packs fit, while the fragment code in `applyFaceStencilShader` does not use fit to alter UV sampling.
   Cost: zero slices when prepared SVGs and seeded defaults carry the art direction; one slice for colour and region controls; one further slice for tested fit semantics.
   Freeze: no named item, but the campaign should add these only after the same break recurs.
5. Colour is intentionally constrained.
   `src/domain/cubeEdgeState.ts:cubePartColors` provides theme, black, white, and accent.
   `src/theme/scenePolarity.ts:scenePolarities` provides two polarities with fixed accent tokens.
   Cost: zero slices for the stated constraint test; two or more slices for project owned palettes across state, persistence, controls, render, thumbnails, and transitions.
   Freeze: broader colour capability is outside the named list, but speculative capability work is frozen.

Foundation conclusion: faces are cheap addressable content surfaces for a curated campaign, while content onboarding remains an engineering operation.
Evidence that would flip this conclusion: one prepared title failing to survive add, select, save, reopen, thumbnail, transition, preview, and recording through the same owners would make the surface claim false.

## Output 1: full music visual

Requirements provided:

- Timed scene sequence: `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel`, `src/evaluation/pieceAt.ts:resolvePieceSample`, and `samplePieceAt`.
- Complete scene transitions: `src/evaluation/sceneTransition.ts:resolveSceneTransitionSample` and `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology`.
- Duration ownership: `src/evaluation/scoreAt.ts:getScoreDurationMs` and `src/state/transportSelectors.ts:getPieceTransportDurationMs`.
- Camera choreography: `src/domain/pieceCameraTrack.ts:compilePieceCameraTrack` and `src/evaluation/cameraTrackSampleAt.ts:cameraTrackSampleAt`.
- Real time canvas capture: `src/export/streamRecorder.ts:createRecordingController`, `startStreamRecording`, and `downloadRecording`.
Gaps:

- `src/export/streamRecorder.ts:studioDisplayMediaOptions` sets `audio: false`; canvas capture also contains no track audio. Final audiovisual delivery needs external playback and muxing. Cost: zero engine slices in campaign operations, or at least two slices for in app audio ingest, synchronized playback, stream composition, persistence, and tests. Audio analysis is frozen; simple playback and muxing are not analysis and are not named freeze items.
- `src/export/recordingConfig.ts` retains 256 MiB at 12 Mbps, about 179 seconds, then `startStreamRecording` requests stop. Cost: one slice for a bounded long form recording path, or zero if external capture is accepted. Freeze: no.
- Recording is real time and manually toggled. No symbol binds record start and stop to exact transport boundaries or fixed frame export. Cost: one slice for transport synchronized real time capture; two to four slices for deterministic offline export. Freeze: no.
Conclusion: a full visual is campaign deliverable with external audio and, for long tracks, external capture or one delivery slice.
Evidence that would flip this section green: one real track, including one over 179 seconds, completes with measured audio sync and no dropped or duplicated boundary frame. A requirement that Cubicell alone emit the finished audiovisual file would flip it red at this commit.

## Output 2: seamless loop

Requirements provided:

- Exact clock wrap: `src/transport/advanceTransportTime.ts:advanceTransportTime` wraps whole pieces and focused windows modulo their duration.
- Renderer owned playback: `src/transport/advanceTransportFrame.ts:advanceTransportFrame` advances the same transport sampled by the stage.
- Loop control and segment preview: `src/panels/motion/PieceMotionPanel.tsx:TransportRow` and `focusWindow`.
- Visual endpoint sampling: `src/evaluation/pieceAt.ts:resolvePieceSample` lands authored states at transition endpoints.
- Duplicate endpoint authoring: `src/panels/stateCapture.ts:createNewStateFromSelected` can create a distinct final State with the first pose.
Gaps:

- `src/domain/stateTransition.ts:repairStructureStateTransitionTrack` permits each State once and creates only `n - 1` transitions. There is no cyclic last to first transition. Authors must duplicate the first pose and camera as a distinct final State. Cost: zero engine slices for that convention; one slice for an explicit closure authoring and validation aid. Freeze: no.
- `tests/playbackFrameBrowserDriver.tsx:verifyExactLoop` proves transport time arithmetic, not pixel equality or recorded seam continuity. Cost: one test slice for first and last frame image and camera equivalence plus synchronized capture. Freeze: no.
Conclusion: the engine can make a seamless loop, but the seam is authored and verified manually.
Evidence that would flip this section green: a recorded loop whose boundary frames and camera pose compare equal within declared tolerances. A repeatable one frame flash, figure cut, or camera discontinuity would flip it red.

## Output 3: vertical social clip

Requirements provided:

- Responsive render surface: `src/app/studio-shell.css:.studio-canvas-region` fills the viewport and `src/scene/CubeScene.tsx:CubeScene` lets the Fiber Canvas derive that size.
- Aspect responsive camera projection: `src/camera/cameraDriverMath.ts:buildProjectionCamera` rebuilds projection from current driver size.
- Reframed camera states: `src/panels/motion/CameraCaptureControl.tsx:CameraCaptureControl` captures the current view into a State.
- Clip playback and capture reuse the same piece transport and `createRecordingController` path as the full visual.
Gaps:

- There is no 9:16 output profile, fixed pixel size, safe area, or project level aspect setting. Current output size is the live viewport. Cost: zero slices for manual portrait viewport setup and camera recapture; one slice for a deterministic portrait preview and capture profile. Freeze: no.
- There is no arbitrary clip in and out owner or transport synchronized range export. Cost: zero slices for a separate short piece and manual capture; one slice for range ownership and capture. Freeze: no.
- Audio and exact delivery inherit the full visual gaps. Cost and freeze classification are unchanged.
Conclusion: a vertical clip is a manual derived project, not a reliable one click derivative.
Evidence that would flip this section green: one 1080 by 1920 capture with intentional reframing, safe title bounds, correct duration, and audio sync. Persistent crop or camera drift after aspect change would flip it red.

## Output 4: title or brand reveal

Requirements provided:

- Whole outlined title or mark: a prepared SVG can be added through `src/domain/seededStencils.ts:seededStencils` and selected through `faceStencilBinding`.
- Addressable placement: `CubeFaceFigure` lives on one face while existing cube size, placement, selection, visibility, face colour, and opacity owners remain available.
- Reveal choreography: `src/evaluation/sceneMorph.ts:sampleSceneMorph` moves, scales, reveals, recolours, and cuts face figure identities through normal State transitions.
- Figure colour tween: `src/evaluation/sceneMorph.ts:createPartColorTweens` and `src/scene/instancedPartMeshCore.ts:writeStencil`.
Gaps:

- `src/scene/stencilAtlas.ts:rasterizeSvgAlpha` draws every SVG into a square slot. Wide typography needs an art directed square canvas or a matching rectangular face because fit has no render semantics. Cost: zero slices for prepared assets; one fit slice if the same optical failure recurs. Freeze: live font layout and a text primitive remain unnecessary and are explicitly frozen.
- Figure identity, region, and fit cut through `cubeFaceStateOwner`; there is no independent figure opacity, path draw, or mask progress channel. Cost: zero slices for cube, face, camera, polarity, and colour reveals; at least two slices for a new animated coverage channel. Freeze: not named, but it is speculative capability during this campaign.
- Runtime title entry and editing do not exist. Cost: zero engine slices for concierge outlined SVGs; live typography and font layout are explicitly frozen.
Conclusion: prepared title reveals fit the committed model when reveal means spatial choreography and polarity, rather than live typesetting or stroke animation.
Evidence that would flip this section green: a real artist and track title remains optically correct on the chosen face and produces a publishable reveal using only current transition channels. Needing live text, arbitrary path animation, extrusion, or relief would flip it red and contradict the freeze.

## Output 5: live VJ scene

Requirements provided:

- Real time renderer and stable face resources: `CubeScene`, `createInstancedPartMesh`, and the Chromium stencil resource gate.
- Continuous playback and looping: `advanceTransportFrame`, `advanceTransportTime`, and `TransportRow`.
- Operator view commands: `src/editor/keyboard/keymap.ts:keyboardCommandIds` and `keyboardCommandIdsByCode` expose orbit, pan, zoom, projection, preview, play, and record commands.
- Camera authority: `src/camera/cameraAuthorityRuntime.ts:createCameraAuthorityRuntime` and `src/camera/CameraDriver.tsx:CameraDriver` own manual and tracked view changes.
- Clean artifact view and recording: `src/app/studio-shell.css` preview selectors hide panels; canvas capture records the artifact.
Gaps:

- `src/evaluation/pieceAt.ts:PieceFrame` sets `interactive: false`, and `src/app/stageInteraction.ts:gateStageMutationHandlers` removes document mutation targets during piece playback. This supports performance of one prepared piece, not live scene editing.
- There is no cue launcher, scene bank, beat clock, MIDI mapping, crossfade, multi output routing, or show recovery owner in the committed tree. Cost: at least three slices for even a narrow cue launcher, with a real suite much larger. Freeze: explicitly frozen as the VJ suite.
- Track audio must run externally. Cost: zero engine slices for a VJ workflow; in app audio inherits the two slice minimum above. Audio analysis remains frozen.
Conclusion: the valid campaign output is one live rendered, looping, manually navigable prepared scene. Calling it a VJ product would overstate the commit.
Evidence that would flip this section green: a complete track length operator session with stable frame pacing, manual view control, loop control, external audio sync, and successful capture. Requiring cue switching or live content mutation to count as the deliverable would flip it red because that work is on the freeze list.

## Engineering economics decision

The branch amortizes face content across the correct owners and adds negligible steady state render cost. That supports using real creative work to test depth before expanding capability.
The campaign has three mandatory operating conditions: keep content within fourteen new bundled entries, repair asset ownership before persistence approval, and accept external audio and delivery operations.
The campaign should log every manual break. Only a break repeated across pieces earns a slice after the campaign, except the existing persistence defect, which already requires one slice.
No evidence shows that rounded cubes, shaping, a text primitive, live font layout, general SVG import, extrusion, SDF relief, multiple atlas pages, audio analysis, or a VJ suite is needed for the narrow campaign.

verdict: conditional — The wedge is the lowest cost credible depth test if concierge SVG seeding, one persistence repair, external audio and delivery, and the narrow prepared scene definition of VJ are accepted campaign constraints.

## Cross-examination

- A: Adopt. The five direction questions are qualitative; numeric thresholds and external raters fixed before piece one prevent post hoc success criteria.
- B: Adopt. `tests/stencilRendering.browser.test.ts` and the campaign can validate engine depth and workflow, while neither supplies market demand evidence. Success permits a music wedge claim, not a durable product home claim.
- C: Rebut. `StencilAsset` persists metadata without source, while `seededStencils` and `rasterizeSeededStencils` own compile time content. Runtime ingestion still lacks source lifecycle, validation, ownership, atlas mutation, and recovery, so “half built” understates the work.
- C′: Adopt. Concierge SVG seeding exercises the committed surface path at zero engine slices and preserves the general SVG import freeze. It remains bounded by the fourteen free atlas slots.
- D: Rebut. `advanceTransportTime`, `keyboardCommandIds`, `CameraDriver`, preview mode, and canvas capture already support a useful prepared live scene test.
- D′: Adopt. `PieceFrame.interactive: false` and `gateStageMutationHandlers` constrain the deliverable to one prepared, looping, manually navigable scene. Cue launching and live content mutation remain outside the claim.
- E: Adopt. `Transition.mode` and `resolveTransitionKind` already own cut semantics, while `TransitionInspector.patchTransition` exposes only `MorphSettings`. One owner completing UI slice should land before piece one.
- F: Adopt. `faceStencilBinding` changes figure state without ensuring `workbench.library.stencils`; persistence approval requires the atomic ownership repair and save, close, reopen proof before the campaign.
- G: Adopt. `studioDisplayMediaOptions.audio: false`, the 179 second retained data budget, and manual capture make external audio and delivery the economical campaign boundary. Audio analysis and new delivery capability stay frozen throughout.

Resolution: C′ replaces C; D′ replaces D.
FINAL conditions: A, B, C′, D′, E, F, G.
verdict: conditional — Proceed after numeric criteria, cut UI, and persistence ownership land, with concierge stencils, external audio and delivery, engine-only success claims, and the narrow prepared-scene VJ definition fixed in advance.
