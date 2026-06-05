# Cubicell face-choreography scout

Scout pass, read-only, 2026-08-07. Inputs: ANIMATION.md, STUDIO.ANIMATION.md, ANIMATION.KNOBS.md, the music-visual-identity direction doc, main at `7d5e942`, stencil branch read via `git show 66b4d8d:<path>`. Mission: map what already exists to choreograph face content before any spec is written. Citations are file+symbol; branch-only symbols are marked (66b4d8d).

Headline: the choreography engine and the stencil surface are already joined. At `66b4d8d` the figure colour tween rides the same Moment overlay, OKLab resolution, and instanced write path as every other part colour, end to end from morph evaluator to shader attribute. The knob catalogue understates the shipped surface: all five face-relevant channels the campaign needs are reachable today through two-state morphs with zero new model.

## 1. Reuse Map

### Moment overlay and evaluators
- **Moment type and staging**: `src/evaluation/scoreAt.ts` — `Moment`, `PartColorTween`, `CubePartColorTweens`, `getMomentCells`, `stageSceneGeometry`, `applyMomentToLayout`. Presence plus sparse part-colour tweens; already eased (ANIMATION.md, Primitives: Moment). At 66b4d8d `CubePartColorTweens` gains an optional `figures` map keyed by `CubeFaceId` — the overlay already carries figure colour tweens.
- **Assembly evaluation**: `src/evaluation/scoreAt.ts` — `scoreAt`, `applyAssemblyTrack`, `easingFor`, `quantizeProgress`. Presence only; assembly produces no colour tweens on main or branch.
- **Scene morph**: `src/evaluation/sceneMorph.ts` — `prepareSceneMorphTopology`, `prepareSceneMorphSchedule`, `sampleSceneMorph`, `interpolateCell`, `createPartColorTweens`, `interpolateGridState`. Classifies added/removed/changed, plans per-class motion (order, stagger, easing, quantize), tweens pose, size, gaps, face opacity, edge thickness, and part colours. At 66b4d8d face change classification and interpolation route through `cubeFaceStateOwner.getMorphChanges` / `interpolateMorph` (66b4d8d, `src/domain/cubePartStateOwner.ts`), so figure changes are classified and morphed by the shared part-state owner, and `createPartColorTweens` emits figure tweens gated by `canTweenCubeFaceFigureColor` (66b4d8d, `src/domain/cube.ts`).
- **Piece handoff**: `src/evaluation/pieceAt.ts` — `resolvePieceSample`, `samplePieceAt`, `PieceFrame`. Assembly holds the first State; each State transition then exclusively owns presence and properties (settled contract in the file header).
- **Shared edges**: `src/evaluation/sharedEdgeTweens.ts` — `planSharedEdgeTweens`; one physical edge tweens as one group.
- **Overlay to renderer**: `src/scene/useCubeSceneRenderState.ts` passes `moment.partColors` into `src/scene/cubeInstances.ts` (`CubeInstanceOptions.partColors`), consumed per cell by `src/scene/incrementalCubeSceneOwner.ts` (`colorTweens` comparison for incremental rewrites).

### Stencil face path (66b4d8d)
- **Figure state owner**: `src/domain/cube.ts` — `CubeFaceFigure` (`stencilId`, `region` form|field, `color`, `fit` margin|bleed), owned as a `cubePartStateOwner` field (`src/domain/cubePartStateOwner.ts`, `cubeFaceStateOwner`) with encode/decode, validation, and morph semantics (`color-tween` when structure matches, `discrete-cut` otherwise). One figure state owner, per stop rule 1 of the synthesis doc.
- **Attribute write**: `src/scene/cubeInstances.ts` attaches `figure` (plus its `colorTween`) to `InstancedPart`; `src/scene/instancedPartMeshCore.ts` — `syncInstancedPartMesh` and the partial-write path both call `writeStencil`, which resolves the figure colour through the same `resolveTreatedPartColor` / `resolvePartColor` (`src/scene/colorSpace.ts`, OKLab) path as faces and edges, then `writeFaceStencilAttribute`. One colour resolution path shared with everything else.
- **Shader**: `src/scene/faceStencilShader.ts` — `applyFaceStencilShader` injects one vec4 instanced attribute and one atlas sampler into the existing face material; region flag selects form/field colour roles; no second draw, no per-glyph material.
- **Atlas**: `src/scene/stencilAtlas.ts` — `createStencilAtlas`, `getStencilAtlasSlot`; 2048px single page, 16 slots of 512px, `slotByStencilId` built from `seededStencils` at module load. Thumbnails share the same atlas (`src/thumbnail/thumbnailRenderer.ts` creates and passes it), honouring the one-delivery-path stop rule.
- **Content identity**: `src/domain/stencil.ts` — `StencilId` is `sha256:` content-addressed; `src/domain/seededStencils.ts` — `seededStencils`, `resolveStencilContent`. Resolution reaches only the bundled registry; the direction doc's high persistence finding (bundled selection bypasses the project Library) is mechanically confirmed there and must land before merge.
- **Authoring surface**: `src/editor/controlBindings.ts` — `face.stencil` enum binding (None plus seeded marks) applying the stencil's `defaultFigure`. Region, figure colour, and fit have no dedicated control binding yet; they change only via the applied default.

### Transition and morph model
- **Model**: `src/domain/score.ts` — `Score`, `PieceScore`, `AssemblyTrack` (cadence, easing, quantize, exit, orderMode), `StateTransitionTrack`, `Transition`, `TransitionMode = "auto" | "cut"`. The file's own NOTE marks `cut` as a working, tested capability with no Editor control: `src/panels/motion/MorphInspector.tsx` authors `cutAt` but never `mode`, so the whole-scene beat cut (`src/evaluation/sceneTransition.ts`, `sampleSceneTransition` forced-cut path) runs only from persisted or programmatic data.
- **Settings**: `src/domain/morphSettings.ts` — `MorphSettings` (per-class `ClassMotion` with order/easing/quantize/stagger, `cutAt`, `arriveForm`/`departForm` grow|slide|drop|turn), fully authored by `MorphInspector`.
- **Order and cadence generators**: `src/domain/assemblyOrder.ts` — `OrderMode` creation|sweep|radial|shell|spiral|random, all implemented; `src/domain/assemblyTiming.ts` evaluates `CadenceCurve` accelerando|ritardando|swing; `AssemblyExit` (build-out with hold, reverse order) is implemented in `applyAssemblyTrack`.

### Camera track
- **Compile**: `src/domain/pieceCameraTrack.ts` — `compilePieceCameraTrack` turns captured State views into a `CameraTrack` with move and boundary-cut segments.
- **Sample**: `src/evaluation/cameraTrackSampleAt.ts` — `cameraTrackSampleAt`, clamped holds, cut and eased paths, projection blend; loaded through `src/evaluation/cameraTrackSamplerPort.ts` on its own chunk.
- **Possession**: `src/studios/editor/useCameraTrackFrame.ts` drives the renderer during Play; `src/panels/motion/CameraCaptureControl.tsx` authors views. This loop is live in production, which contradicts two stale passages (Quality Map, below).

### Transport and delivery
- **Transport**: `src/state/actions/transportActions.ts` — play/pause/stop, `setTransportLoop`, `setTransportLoopWindow`; wall-clock playback (ANIMATION.md, slice one).
- **Recording**: `src/export/streamRecorder.ts` — `createRecordingController`, `RecordingSource = "canvas" | "studio"`; webm only, `audio: false`, wall-clock capture. No fixed-step deterministic clock (the seam ANIMATION.md names as future work).

## 2. Quality Map

1. **Persistence Library bypass (known, high)**: `resolveStencilContent` (66b4d8d, `src/domain/seededStencils.ts`) resolves only through the bundled registry; selecting a seeded stencil never adds the asset to the project Library. Direction doc already requires repair before merge. Nothing in a choreography spec should build on the unrepaired path.
2. **Stale camera claims in ANIMATION.md**: invariant 2 ("no production caller drives it yet") and the Track primitive ("no evaluator or production surface drives it yet") contradict the same document's status section and the shipped `useCameraTrackFrame` loop. Doc drift, not a code defect; reconcile before the spec cites ANIMATION.md as authority on camera status.
3. **Knob catalogue status drift**: ANIMATION.KNOBS.md rates quantize, order modes, cadence curves, and disassembly `[near]`; all are `[now]` (`ClassMotion.quantize`, `OrderMode`, `CadenceCurve`, `AssemblyExit` all implemented and surfaced). The catalogue undersells the shipped instrument; a spec sequencing "build the near knobs" would rebuild existing code.
4. **Unhonoured `fit` declaration**: `CubeFaceFigure.fit` is authored, validated, persisted, and packed into the shader attribute (`fitFlag` in `faceStencilShader.ts`), but the fragment shader never reads the bit; margin and bleed render identically. Matches the synthesis doc's "no proven visual effect at this head". Per the audit rule, treat as a not-yet-honoured feature, not dead code; decide, do not silently remove.
5. **Figure swaps are cuts, not crossfades**: `canTweenCubeFaceFigureColor` allows tweening colour only when stencilId, region, and fit match; any other figure change is `discrete-cut` at the class cut point. A mark-to-mark or form-to-field transition is therefore a hard swap. This is a deliberate boundary (two-value composition), but the title reveal design must not assume stencil crossfade.
6. **No colour tweens during assembly**: `scoreAt` emits presence only; `Moment.partColors` is produced solely by `sampleSceneMorph`. All face-content choreography must be expressed as State pairs, which is the intended authoring model (KNOBS section 7, editor as keyframe tool) but worth stating as a hard boundary in the spec.
7. **Atlas seeding is a code change**: `slotByStencilId` is built from `seededStencils` at module load; 16 slots, one page. Each campaign mark is a commit (SVG asset, seed entry, budget rebaseline), not a runtime import. Consistent with the freeze; the spec should cost it per piece, not hide it.
8. **No boundary duplication found** where the stencil path meets the tween and overlay path: figure tweens reuse `collectPartColorTweens`, `PartColorTween`, `resolvePartColor`, and the shared incremental write machinery. The stop rules held.

## 3. Face-relevant knob channels, costed against the stencil surface

Bound to the campaign's two highest-identity outputs: title reveal and seamless loop. "Via states" means authored as a two-State morph in the shipped model, zero new code.

| Channel | Mechanism today | Cost given the stencil surface | Title reveal | Seamless loop |
| --- | --- | --- | --- | --- |
| Face mask | Face `opacity` tweens continuously (`interpolateCell` numericInk); `visible` flips at cut | None; via states. Figure fades with its face (no independent figure opacity channel) | High: mark fades in on the face | Medium: shimmer via opacity states |
| Shell state | Face opacity + edge thickness both continuous (`cubeEdgeStateOwner.interpolateMorph`) | None; via states | Medium: wireframe resolves to solid behind the mark | High: solid/wire breathing is loop-native |
| Local invert | Part colours tween in OKLab; figure colour tweens when structure matches; region form/field flip is a discrete cut | None; via states. The synthesis doc's polarity-poster direction is exactly this | High: role swap on the mark is a signature beat | High: A→B→A invert is inherently loopable |
| Polarity strike | `sampleSceneMorph` switches `scene.polarity` at `globalCut` | None via states, but timing is bound to `cutAt` inside a morph; a clean beat strike wants the unexposed cut mode (Plan step 2) | High: the one-bit signature move on the reveal beat | High: paired strikes close a loop |
| Quantize | `ClassMotion.quantize` + `AssemblyTrack.quantize` via `quantizeProgress`, surfaced in `MorphInspector` | None; shipped | Medium: mechanical arrival of the mark | High: stop-motion cadence hides loop seams |

The single genuine gap behind all five: nothing choreographs face content *within* one State (no PropertyTrack). Under the freeze that is correct; the two-State morph is the campaign's authoring unit.

## 4. Plan

### Decisions the owner must make first
1. **Expose the cut transition mode** in `MorphInspector` (authors `Transition.mode`)? The beat cut is built and tested (`sampleSceneTransition`); polarity strike and title-reveal beats want it. Recommended yes; it surfaces existing capability, adds none.
2. **`fit` flag**: honour it in the shader, or strip the field? It is persisted state with zero visual effect. Either is small; carrying it silently through the campaign is the only wrong option.
3. **Per-piece mark seeding**: accept commit-per-mark concierge seeding for all three pieces (SVG + `seededStencils` entry + budget rebaseline), deferring runtime ingestion per the freeze?
4. **Loop capture fidelity**: accept wall-clock webm capture for piece one, promoting the fixed-step clock seam only if the loop seam visibly breaks? The seam is already named in ANIMATION.md.
5. **Figure authoring depth**: is the stencil enum plus `defaultFigure` enough, or do region/figure-colour need control bindings before piece one? (Today they are reachable only through the applied default.)

### Ordered spec steps, bound to the reuse map
1. **Land the Library-bypass repair** (`resolveStencilContent` path). Gate: existing `tests/stencilAssets.test.ts` extended with a controlled-red proving a selected seeded stencil persists into the project Library; full unit + Chromium gates.
2. **Surface `TransitionMode` in `MorphInspector`** (decision 1). Reuses `Transition.mode`, `resolveTransitionKind`, `sampleSceneTransition`. Tests: `tests/panels.test.tsx` authoring path; a `sceneTransition` unit asserting the cut boundary at `cutAt * durationMs`, red first against the unexposed control.
3. **Concierge seeding recipe as a documented step, not code**: per mark, add `assets/marks/<name>.svg`, one `seededStencils` entry, budget rebaseline. Gate: `tests/stencilRendering.browser.test.ts` and budget checks green per mark.
4. **Author piece one entirely from shipped channels** (table above): states, morph classes, arrive/depart forms, quantize, camera views, polarity at the cut. No new tracks, no new fields. Gate: the campaign's own external pass criteria; live UX check before merge per the seam-layer lesson.
5. **Only on a proven repeat break**: fixed-step export clock at the transport seam (`transportActions` + `createRecordingController`), then loop-perfect capture. Do not build ahead of evidence.
6. **Doc reconciliation** alongside step 2: correct the two stale camera passages in ANIMATION.md and the shipped-status drift in ANIMATION.KNOBS.md so future specs inherit true status.
