# Cubicell P1 scout

## Basis

Scout only at `c51e9767e1f7dbc9653e49e91d256924b2b9fdaa`, where `HEAD`, local
`main`, `origin/main`, and `docs/performance-audit` agree. `PERFORMANCE.md`
sets the common principles: no settled render work, explicit resource cleanup,
amortized capacity, narrow subscriptions, and browser enforced claims
(`PERFORMANCE.md:69-78`). Its measured baseline is 120 settled fps, about 90 ms
for one added cube, 423 KB gzip initial JavaScript, and 3.17 s throttled LCP
(`PERFORMANCE.md:50-67`).

Navigation used a fresh `fmm` index generated and validated at this exact SHA.
Repository searches below were run against the same tree.

## Recommended order

1. **GPU capacity.** Independent root cause with a shipped browser mutation
   harness ready to extend.
2. **Playback derivation.** Establish stable transition plans, the low scope
   staged scene consumer, and the single frame source.
3. **Demand rendering.** Consume that frame source and add producer lifetime
   around camera, playback, scrub, drag, resize, and state changes.
4. **Recording lifetime.** Consolidate terminal ownership and bound output.
5. **Initial delivery.** Split the stable motion and recording seams, then
   enforce bundle and cold load budgets.

This differs from the current table only by placing playback before demand
(`PERFORMANCE.md:408-419`). Demand's own gate requires playback without a
second animation clock (`PERFORMANCE.md:253-258`), while playback explicitly
requires one frame source for sampling and invalidation
(`PERFORMANCE.md:274-288`). Building that source once avoids a scheduler
rewrite.

## 1. Stable GPU capacity and material lifetime

### What

`retainCubePackedInstanceCapacities` retains each exact historical maximum, so
every new maximum still changes capacity (`src/scene/cubeInstanceSlots.ts:82-95`).
`InstancedPartMesh` treats capacity as mesh identity
(`src/scene/InstancedPartMesh.tsx:61-76`), and creation allocates geometry,
material, opacity storage, and an `InstancedMesh`
(`src/scene/instancedPartMeshCore.ts:88-145`). Edge coverage repeats the same
capacity keyed lifecycle (`src/scene/EdgeCoverageLayer.tsx:19-44`).

The gate is geometric growth: no GPU creation within a band, buffers once when
crossing a band, no shader program creation, stable live counts over add/remove
cycles, and a browser regression (`PERFORMANCE.md:200-223`).

### Reuse map

- Stable identities and tombstones: `src/scene/cubeInstanceSlots.ts:createCubeInstanceSlotOwner`
  and `src/scene/instanceSlotRegistry.ts:createInstanceSlotRegistry`. Capacity
  already includes stable slot and patch peaks in
  `src/scene/cubeInstanceSlots.ts:resolveBucket`
  (`src/scene/cubeInstanceSlots.ts:197-212`).
- Mesh updates and cleanup: `src/scene/instancedPartMeshCore.ts:syncInstancedPartMesh`,
  `patchInstancedPartMesh`, and `disposeInstancedPartMesh`
  (`src/scene/instancedPartMeshCore.ts:147-238`).
- Browser observability: `src/scene/instancedPartMeshCore.ts:observeInstancedPartMeshMutations`
  (`src/scene/instancedPartMeshCore.ts:61-78`) plus the production tree driver at
  `tests/incrementalSceneBrowserDriver.tsx:62-180`.
- Geometric capacity policy: **none found**. `fmm similar capacity` and
  `rg "geometric|capacity band|grow.*capacity|doubl" src tests` found no
  candidate.

### Quality map

- **Duplication:** `InstancedPartMesh` and `EdgeCoverageLayer` each recreate and
  dispose an entire mesh when capacity changes
  (`src/scene/InstancedPartMesh.tsx:61-87`,
  `src/scene/EdgeCoverageLayer.tsx:25-44`). The neighbor mesh also supplies an
  exact live length outside the retained bucket policy
  (`src/scene/CubeScene.tsx:511-520`).
- **Dead code:** none confirmed. Exact maximum retention is active and covered
  for shrink and tombstones (`tests/cubeSceneInstanceCapacity.test.tsx:49-100`).
- **Design risk:** buffers remain capacity dependent, while materials and
  programs must survive growth. Translucent meshes attach a capacity sized
  opacity attribute (`src/scene/instancedPartMeshCore.ts:250-260`), and edge
  coverage adds another capacity sized axis attribute plus a custom shader
  (`src/scene/edgeCoverageCore.ts:110-153`). A shared growth primitive must let
  each mesh family replace buffers without recreating material identity.

### Blast radius and effort

**High.** Direct owners are `CubeScene`, `InstancedPartMesh`,
`EdgeCoverageLayer`, `cubeInstanceSlots`, and both mesh cores. The shared mesh
core also serves thumbnail artifacts (`src/thumbnail/thumbnailArtifact.ts:47-78`).
Existing unit coverage proves retention, while the browser driver currently
counts syncs, patches, writes, and upload ranges rather than buffer, material,
program, and live resource events (`tests/incrementalSceneBrowserDriver.tsx:183-260`).

**Dependencies:** independent of the other P1 items. Extend the existing
browser harness now. P2 verification infrastructure should later run the gate
in CI (`PERFORMANCE.md:385-401`).

## 2. Playback derivation and subscription scope

### What

`TransportDriver` owns an independent RAF and writes transport time to Zustand
on every tick (`src/transport/TransportDriver.tsx:15-54`). `useStagedScene`
subscribes to the whole workbench and transport, prepares only comparison
sources, and returns the sampled frame to the app root
(`src/transport/useStagedScene.ts:137-159`, `src/app/App.tsx:37-77`). Piece
sampling therefore reaches `sampleSceneTransition` without a plan and rebuilds
it every transition frame (`src/evaluation/pieceAt.ts:58-90`,
`src/evaluation/sceneTransition.ts:19-44`).

The measured preparation cost is about 2.38 ms for 1,000 cells. The gates are
one preparation per active transition, no shell render on ticks, p95 at or
below 16.7 ms for 2,025 cells, and no pending RAF after pause
(`PERFORMANCE.md:260-288`).

### Reuse map

- Plan and sampler: `src/evaluation/sceneMorph.ts:prepareSceneMorph` and
  `sampleSceneMorph` (`src/evaluation/sceneMorph.ts:67-113`,
  `src/evaluation/sceneMorph.ts:139-180`).
- Transition resolution: `src/evaluation/pieceAt.ts:samplePieceAt` and
  `src/domain/stateTransition.ts:resolveStateTransitionPosition`.
- Clock math: `src/transport/advanceTransportTime.ts:advanceTransportTime`.
- Existing behavioral oracle: `tests/stagedScene.test.ts:45-255`; existing
  prepare/sample benchmark: `tests/sceneMorph.bench.ts:67-83`.
- Stable active transition plan cache: **none found**. `fmm similar plan` found
  `SceneMorphPlan` but no cache or owner. Searches for plan preparation spies or
  shell render counts also found no regression gate.

### Quality map

- **Duplication:** piece and comparison both sample scene transitions through
  `sampleStageSource`, but only comparison receives a prepared plan
  (`src/transport/useStagedScene.ts:88-135`). The optimization is split across
  two source branches.
- **Dead code:** the forced cut branch is explicitly dormant from UI authoring,
  although domain tests still exercise it
  (`src/evaluation/sceneTransition.ts:26-37`,
  `tests/stagedScene.test.ts:189-204`). Preserve semantics while relocating plan
  ownership.
- **Design risk:** comparison sources also embed `progress` and `timeMs`, so
  `[morph]` invalidates their plan during a scrub
  (`src/transport/useStagedScene.ts:34-41`,
  `src/transport/useStagedScene.ts:142-153`). Cache identity must use
  endpoint revisions and transition settings, excluding sample time. State IDs
  alone are unsafe when an existing State pose is updated.

### Blast radius and effort

**High.** The change spans `TransportDriver`, `useStagedScene`, piece and
transition evaluation, the `App` staging boundary, and playhead controls.
`PieceMotionPanel` also subscribes to the complete transport object and renders
the playhead each tick (`src/panels/motion/PieceMotionPanel.tsx:47-68`,
`src/panels/motion/PieceMotionPanel.tsx:186-290`).

**Dependencies:** complete before demand rendering so one frame source owns
transport sampling and viewport invalidation. P2 verification infrastructure is
needed to make the 2,025 cell p95 and shell render assertions release gates.

## 3. Demand driven rendering

### What

`CubeScene` leaves `Canvas` on its continuous default
(`src/scene/CubeScene.tsx:408-429`). The sole production `useFrame` performs
Trackball update, interaction resolution, pose cloning, morph sampling, camera
writes, focus sync, and projection swaps every frame
(`src/camera/cameraFrameWriter.ts:22-119`). The settled baseline is 120 fps. The
gate is zero draws over three seconds while preserving every active motion and
input path (`PERFORMANCE.md:225-258`).

### Reuse map

- Invalidation primitive and precedent: R3F `invalidate`, already used by
  `src/scene/CubeScene.tsx:SceneBackground`
  (`src/scene/CubeScene.tsx:550-559`).
- Camera composition owner: `src/camera/cameraFrameWriter.ts:useSingleCameraWriterFrame`.
- Motion state: `src/interaction/interactionCore.ts:InteractionCore` exposes
  `getState`, `holds.active`, `resolveFrame`, and morph operations
  (`src/interaction/interactionCore.ts:35-71`); its snapshot exposes `poseMode`
  and `morphing`
  (`src/interaction/snapshot.ts:12-39`).
- Gesture and inertia events: `src/camera/cameraGestureRuntime.ts:useCameraGestureControls`
  (`src/camera/cameraGestureRuntime.ts:49-140`) and
  `src/camera/cameraTrackball.ts:createTrackballControls`
  (`src/camera/cameraTrackball.ts:14-34`).
- Render scheduler or producer lifetime abstraction: **none found**. `fmm
  similar scheduler`, `rg "render scheduler|frame scheduler|motion active|frameloop" src`,
  and the full `useFrame|invalidate|requestAnimationFrame` inventory found only
  the background invalidation, camera frame hook, and transport RAF.

### Quality map

- **Duplication:** camera work runs on the R3F clock while playback advances on
  its own RAF (`src/camera/cameraFrameWriter.ts:51-119`,
  `src/transport/TransportDriver.tsx:27-53`).
- **Dead code:** none confirmed.
- **Design risk:** Trackball uses damping and remains dynamic after pointer end
  (`src/camera/cameraTrackball.ts:14-26`). Projection morphs and core pose motion
  also complete over multiple samples. A producer must report liveness through
  its final composed frame. Event only invalidation would strand inertia,
  queued camera motion, or the completing projection swap.

### Blast radius and effort

**High.** Owners include `CubeScene`, `CameraDriver`, the camera writer,
gesture runtime, interaction core, transport frame source, and active scrub and
drag surfaces. Tests must cover settled draw counts plus camera gesture,
inertia, projection, playback, resize, DPR, and document updates.

**Dependencies:** follows playback derivation. Design the producer registration
so the P2 pointer session abstraction can register drags without a second
scheduler (`PERFORMANCE.md:354-369`). Demand mode also removes the continuous
RAF starvation called out by the deferred thumbnail service
(`src/components/ui/thumbnail/thumbnailService.tsx:9-28`).

## 4. Recording memory and cleanup

### What

`startStreamRecording` retains every chunk, configures 12 Mbps, and builds one
final Blob (`src/export/streamRecorder.ts:1-3`,
`src/export/streamRecorder.ts:52-100`). That is about 90 MB
per minute before Blob construction. It has `onstop` but no `onerror`; the
returned contract exposes only `stop` (`src/export/streamRecorder.ts:42-90`).
Canvas unmount only unregisters
the command callback (`src/camera/cameraCaptureRegistration.ts:5-17`). The gates
require bounded memory and exact terminal cleanup on stop, error, unmount, and
repeat cycles (`PERFORMANCE.md:290-314`).

### Reuse map

- Shared media setup, MIME selection, title, and download:
  `src/export/streamRecorder.ts:startStreamRecording`.
- Mutual exclusion: `src/export/streamRecorder.ts:createRecordingGuard` and
  `sharedRecordingGuard` (`src/export/streamRecorder.ts:18-40`).
- Display track termination: `src/export/studioRecorder.ts:createStudioRecorder`
  handles `track.onended` (`src/export/studioRecorder.ts:31-89`).
- Tree owned cleanup pattern: `src/components/ui/thumbnail/thumbnailService.tsx:ThumbnailServiceProvider`
  clears the cache and releases its backend on unmount
  (`src/components/ui/thumbnail/thumbnailService.tsx:76-100`).
- Exact once recorder finalizer, bounded chunk sink, writable recording sink,
  and remaining budget UI: **none found**. Searches for `onerror`, `timeslice`,
  `requestData`, writable stream APIs, recorder limits, and recorder `dispose`
  found no implementation.

### Quality map

- **Duplication:** canvas and studio wrappers separately own
  `activeRecording`, guard acquire/release, toggle stop, and failed start
  handling (`src/export/canvasRecorder.ts:14-44`,
  `src/export/studioRecorder.ts:31-89`).
- **Dead code:** none confirmed. Both capture commands are registered and bound
  (`src/editor/keyboard/keymap.ts:40-69`).
- **Design risk:** wrapper `stop` releases the guard while MediaRecorder
  finalization is asynchronous, and cleanup is distributed between wrapper
  state and `onstop`. Error, unmount, native track end, and user stop can race.
  One idempotent terminal owner must clear handlers, tracks, title, guard,
  chunks or sink, and output exactly once.

### Blast radius and effort

**Medium.** The shared encoder plus two thin wrappers are compact, with call
sites in `CameraDriver` and `useSynchronousEditorCommands`
(`src/camera/CameraDriver.tsx:57-96`,
`src/app/useSynchronousEditorCommands.ts:24-77`). Existing tests cover manual
stop, failed MIME selection, picker cancellation, native track end, and mutual
exclusion, but omit unmount, `MediaRecorder.onerror`, memory bounds, and repeat
cycle residue (`tests/streamRecorder.test.ts:80-219`).

**Dependencies:** behaviorally independent. Complete before initial delivery so
recording has one stable lazy module seam. P2 runtime signal should consume the
new recorder failure outcome (`PERFORMANCE.md:371-383`).

## 5. Initial delivery

### What

`main.tsx` statically imports both editor and design system, then chooses by
pathname (`src/main.tsx:1-23`). The production baseline is one 1,495 KB chunk,
423 KB gzip, with 3.17 s throttled LCP. The gates are at most 350 KB gzip for
the editor entry, no design system code in that entry, LCP at most 2.5 s, and no
initial task above 100 ms (`PERFORMANCE.md:316-337`). No dynamic import exists
under `src`.

### Reuse map

- Route seam: the existing pathname decision in `src/main.tsx:17` can select a
  dynamic root module.
- Motion seam: `src/panels/BottomDock.tsx:BottomDock` owns the whole enabled
  Piece Motion workspace (`src/panels/BottomDock.tsx:16-59`).
- Deferred heavy initialization: `src/components/ui/thumbnail/thumbnailService.tsx:createDeferredThumbnailBackend`
  already delays WebGL creation until the first idle render
  (`src/components/ui/thumbnail/thumbnailService.tsx:31-68`). Module
  loading still remains eager through `BottomDock`.
- Long task observation technique: private
  `tests/cubicellStoreBrowserDriver.ts:observeLongTasks`
  (`tests/cubicellStoreBrowserDriver.ts:647-668`). Extract
  or repeat only after creating a shared browser measurement helper.
- Source lazy boundary, bundle budget, production cold load gate, or Vite chunk
  policy: **none found**. `rg "import\\(|React.lazy|lazy\\(" src` returned no
  matches; `vite.config.ts:1-37` contains test configuration only; searches for
  bundle, gzip, LCP, and throttling found only `PERFORMANCE.md`.

### Quality map

- **Duplication:** no duplicate loader exists yet. The risk is eager barrels:
  `App` imports the panels barrel (`src/app/App.tsx:11-20`), whose `BottomDock`
  import reaches the full motion and thumbnail graph
  (`src/panels/BottomDock.tsx:1-5`). A lazy `BottomDock` behind that same barrel
  can be accidentally defeated by another static export or import.
- **Dead code:** `editorPieceMotionWorkspaceEnabled` is permanently true while
  a TODO asks to remove its disabled fallback
  (`src/config/cubicellConfig.ts:51-59`). Remove that gate while creating the
  load boundary.
- **Design risk:** manual chunk names alone can reshuffle shared code without
  reducing the editor entry. Add a manifest based module and gzip budget first,
  then split the design route, recording, thumbnail renderer, and motion
  workspace based on measured attribution. Preserve Three and the core editor
  on the initial path as required (`PERFORMANCE.md:324-330`).

### Blast radius and effort

**High.** `main.tsx`, `App`, panel imports, `BottomDock`, thumbnail service,
recording call sites, Vite build output, and browser loading tests are in scope.
The editor must keep command registration and keyboard behavior valid while
optional code is absent or loading.

**Dependencies:** follows playback and recording so their final ownership
boundaries become lazy boundaries. P2 verification infrastructure must enforce
the production bundle, LCP, and long task budgets in CI
(`PERFORMANCE.md:385-397`).

## Exit shape

Each item should land with its own deterministic unit coverage and focused
production browser gate. Keep wall time diagnostic where scheduler noise can
vary; use resource counts, preparation counts, render boundaries, draw counts,
pending RAF counts, retained bytes, module membership, and gzip bytes as the
release assertions.
