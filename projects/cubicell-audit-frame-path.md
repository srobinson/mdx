# Cubicell architecture audit — the frame path

Agent 3 of 4. Baseline `main` @ `71098b4`, clean checkout. Read-only, no builds,
no browser, no repros. Slice: `src/interaction/`, `src/camera/`, `src/motion/`,
`src/pose/`, `src/view/`, `src/renderer/`, `src/transport/`, and `src/scene/`
(added by addendum), plus `PERFORMANCE.md`, `CAMERA.md`, `INTERACTIVE.md`,
and `ARCHITECTURE.md`'s scene-model and rendering sections.

Slice size: 99 files, 10,394 LOC. No file exceeds the 700-line ceiling; largest
are `cameraAuthorityRuntime.ts` (662) and `CubeScene.tsx` (525). No duplicate
clusters found by structural clustering across `src/camera/` (81 candidates) or
`src/view/` (51 candidates). No dependency cycles observed.

The addendum makes recursive composition the primary question. It is answered
first, then the frame-path findings that stand independently of it.

## Verdict

**RESTRUCTURE.** Keep the model, move two boundaries. Recursion does not change
that answer; it converges on the same two boundaries and adds a third, smaller
one inside `src/scene/`.

### Does the frame path survive recursive composition?

**Yes, almost entirely, and the one part that must be reshaped is the same seam
that is already wrong for an unrelated reason.**

This is the strongest structural result in the audit, and it is a credit to the
existing design. The camera never sees the scene. `CameraAuthority`,
`IntentBus`, `viewLane`, `viewReducer`, `src/pose/`, and `src/motion/` operate on
`ViewPose` (world-space position, target, up, canonical zoom), `ViewCommand`, and
`ZoomBounds`. `CAMERA.md` states the rule explicitly — "pure pose functions take
bounds as arguments and never see the scene" — and the source honors it. Nesting
grids changes what produces world coordinates; it does not change world
coordinates. Every one of those modules survives recursion untouched.

Exactly one part of the frame path reads scene structure, and it reads it flat:

- `view/viewportFocus.createViewportFocusGeometry` calls
  `createSceneGridLayout(scene.grid, scene.cells)` — one grid, one flat cell list.
- `view/viewportFocus.getGridInteriorZoomMax` computes
  `Math.min(...scene.grid.format.cellSize)`. Under recursion "the smallest cell"
  is the smallest cell at any depth, and each nested grid has its own
  `GridFormat`.
- `view/focusGeometry.getFocusBounds` walks a flat cell array.
- `interaction/framing.FramingInputs.scene` is typed `CubicellScene`, which is
  what admits all of the above.

That is the framing seam, and it is the same seam as T2, which today feeds
framing the authored scene while the renderer draws the staged scene. One
boundary move fixes both: `FramingPort` should deliver what the viewport
contains, as a type that is neither `CubicellScene` nor assumed flat. Two
independent forces pushing on one seam is the clearest possible signal about
where the boundary belongs.

### Is the incremental scene owner reusable under recursion?

**It needs reshaping. It is not foreclosing, and most of it is reusable.**

This was the sharpest question and it deserves the precise answer.

**What survives unchanged.** The stable-slot machinery
(`instanceSlotRegistry.ts`, `cubeInstanceSlots.ts`) is a key-to-slot allocator.
It requires that keys be stable and unique; it does not care that they are flat.
The patch protocol — derive changed cells, `slots.apply(changed)`, emit dirty
attribute ranges — is topology-agnostic. The journal continuity discipline in
`incrementalCubeSceneOwner.journalContinues` is about operation sequencing
(`sequence`, `previous`/`next` scene identity), not about scene shape.

**The load-bearing reason it survives: `CubeLayoutPose` is already a composed
transform.** `domain/gridLayout.ts` produces `{ cubeId, homePosition,
renderPosition, rotation, scale }` per cell, and `SceneGridLayout` is a
`Record<cellId, CubeLayoutPose>` — an indirection the renderer consumes instead
of grid coordinates. Nothing downstream of the layout knows what a grid
coordinate is. A recursive layout builder that walks a placement tree and
composes transforms produces the same value type at the leaves and feeds the
existing instancing layer with no change. That is the single most important
reusability fact in `src/scene/`, and it was not an accident: the layout
indirection plus `useStableGridLayout` (which preserves pose object identity
across recomputes so identity-based change detection skips unchanged cells) is
precisely the seam recursion needs.

**What breaks, concretely.** Topology resolution is computed in one flat integer
lattice with no grid identity in the key.
`domain/incrementalCubeRenderResolution.ts` keys occupancy with
`getGridCoordKey(cell.placement.coord)`, which is `` `${coord.x}.${coord.y}.${coord.z}` ``,
and finds neighbors with `getNeighborCoord` — integer arithmetic in that one
lattice. Burial, shared face ownership, and shared edge resolution all derive
from it. Under nesting:

- Two cells in different grids at local `(0,0,0)` collide on the key `"0.0.0"`.
  The occupancy map would silently treat them as one slot. This is a
  correctness break, not a performance one.
- Nested grids carry their own `cellSize` and `gap`, so the integer lattice is
  not even the same scale between levels.
- Cubes that are physically adjacent in world space across a grid boundary have
  no coordinate relationship at all.

`CubeSelection` (`{ cubeId, kind }`) and `CubeSceneInstanceRenderState`'s
`Map<string, CellInstanceEntry>` share the same flat-string-id assumption, and
change together with it.

**The incremental path, in steps.**

1. Path-qualify the key namespace: `gridPath + coord` for occupancy,
   `gridPath + cellId` for slot and entry keys, a placement path for selection.
   Mechanical, and it restores correctness for adjacency *within* each nested
   grid, which stays incremental exactly as it is today because each grid is its
   own independent lattice.
2. Make the layout builder a tree walk composing placement transforms. Output
   type unchanged.
3. Decide cross-grid burial. Two nested grids whose cubes touch in world space
   is the genuinely new derivation. Two options: declare burial per-grid and
   always draw cross-grid faces, or add a bounding-box broadphase and resolve
   burial only where grid boxes intersect.

Step 3 is a **product decision, not a technical wall**, and the per-grid answer
is defensible: a nested piece is a compositional unit and arguably should render
its own faces regardless of what it sits next to. If per-grid burial is
acceptable, the incremental owner survives recursion with steps 1 and 2, which
are both mechanical.

**One honest consequence.** Under recursion, editing a placement transform high
in the tree legitimately changes the pose of every descendant. The
identity-based change detection in `collectPresentationChangeIds` will correctly
report the whole subtree as changed. `PERFORMANCE.md` principle 2 ("work scales
with the changed data") still holds — the subtree *is* the changed data — but the
P0 gate's "one cell edit, five affected derivation cells" shape does not
generalize to placement edits, and a new gate is needed for them. That is a
gate-authoring obligation, not a defect.

### Does the camera evaluator absorb a per-channel segment model?

**There is no camera evaluator to absorb or replace. This part of the addendum
overstates the cost.**

Verified: `CameraSample` (`{ endpointProjection, orthographicWeight, pose }`) is
declared in `domain/cameraTrack.ts` and consumed in `camera/cameraTrackFrame.ts`.
**Nothing in `src` ever constructs one.** Grepping `orthographicWeight` outside
the projection-morph code returns only the type declaration and the consumer. So
`domain/cameraTrack.ts` is a persisted shape, an orbit-arc geometry helper set,
and validation — not a sampler. `getCameraTrackDurationMs` and
`sortCameraKeyframes` are the only track-level functions, and neither samples.

So the work is a wire bump plus a **greenfield evaluator**, not a migration.
Writing the `CAMERA.md` 7-channel sampler from nothing is cheaper than converting
a 2-channel one, and the repository's stated single-user, no-migration policy
makes the wire bump a version increment and a reset rather than a migration
branch. The persisted shape genuinely is two-channel and none of `CameraFraming`,
`rigTranslation`, `lock-target-height`, `moveId`, `CameraTargetRef`,
`perspectiveMagnification`, `orthographicHeight`, `OrbitSegment`, or
`PerspectiveLensSegment` appears anywhere in `src` — that part of the addendum is
exactly right. But the shipped orbit-arc work (`deriveShortestCameraOrbitArc`,
`resolveCameraOrbitArc`, `isCameraOrbitArcEndpointCompatible`,
`reverseCameraOrbitSweep`, `addCameraOrbitFullTurn`) is the endpoint-compatible
signed sweep that `CAMERA.md`'s orbit channel explicitly adopts as "the shipped
endpoint-compatible signed sweep arc". It carries forward verbatim into the
`OrbitSegment` route.

And the frame-side consumer already has the right shape. `cameraTrackFrame.ts`
takes `frame.sample.pose`, `frame.sample.orthographicWeight`, and
`frame.sample.endpointProjection`, and the possession authority converts through
`createViewPoseFromSnapshot`. A 7-channel keyframe resolves down to exactly those
three values. The runtime seam absorbs the richer model without change; only the
producer side is new.

### Three strongest pieces of evidence

- **`sampleActiveMotion` in `cameraAuthorityRuntime.ts` allocates on one branch
  and reuses scratch on the other.** The linear/dolly branch threads
  `state.motionSample` into `getCameraMotionPose`. The orbit branch returns a
  freshly built `{ complete, pose }` whose pose came from `reduceViewPose`
  through `orbitViewPose`. Orbit tap is the most-used camera control. The two
  branches sit in one seven-line function.
- **The framing seam is the only part of the frame path recursion touches, and
  it is already broken for an unrelated reason.** Grid framing, selection focus,
  and zoom bounds all read `getWorkingScene` through one `FramingPort` while the
  renderer draws `staged.scene`, and all three additionally assume one flat grid.
  One boundary move answers both.
- **The camera track subsystem is dark end to end, in four independent places.**
  No producer supplies a non-null `cameraTrack` prop; no `CameraSample` is ever
  constructed; `src/studio/` (`CameraTrackControls.tsx`, `cameraCapture.ts`,
  `index.ts`) has **zero production importers**, only
  `tests/studioCameraControls.test.tsx`; and the possession authority is fully
  implemented and tested behind all of it.

Not a rebuild: every finding below has a concrete incremental path, and I could
not construct a capability in `CAMERA.md`, `ARCHITECTURE.md`'s scene-model
direction, or recursive composition that the current shape forecloses.

## Walls

**None.**

The two strongest rebuild candidates in the slice, examined and rejected:

**Verifiability (T4).** The incremental path is additive: attach a frame-pacing
and allocation probe to the existing `CameraRenderLiveness.report` seam, which
already receives a per-producer liveness record every frame; assert budgets in a
browser fixture the way `PERFORMANCE.md`'s P0 gates already do for mesh
synchronization counts. It does not break anywhere, and a rebuild would need the
same probe on the same seam. Not a wall — but see the elevation note at the end
of T4, because under recursion this becomes the item that gates the decision.

**The flat-lattice topology index.** Detailed above. The break is real and it is
at the key level, but path-qualifying a key is mechanical, per-grid burial stays
incremental unchanged, and the only genuinely new derivation (cross-grid burial)
has a defensible product answer that avoids it entirely. A wall requires that
incremental change cannot reach the capability; here it reaches it in two
mechanical steps plus one scoping decision.

I also checked whether the live `ViewPose` forecloses `CAMERA.md`'s authored
camera model. It does not: `viewPose.applyViewPoseToCamera` already performs the
distance-plus-canonical-zoom conversion in both directions that `CAMERA.md`'s
`CameraFraming` formulas require, and the authored keyframe is a superset that
resolves down to a `ViewPose`.

## Taxes

### T1. The scratch-buffer regime is a per-feature manual obligation with no enforcement (question 1)

**The cost is real and recurring, and it is currently being paid incorrectly in
at least four places.**

What #139 actually covered, and it holds: the publish step of
`advanceCameraAuthority`, the bus drain into `IntentBus.drainViewFrame`'s caller
array, view coalescing through `CoalescedViewScratch`, projection resolution
scratch in `view.commands.createViewCommandResolveScratch`, the linear/dolly
motion sampler through `state.motionSample`, and the liveness record in
`cameraFrameWriter.frameStateRef`.

What it did not cover, all still allocating every frame on live paths:

- **The glide hold path**, which is the reported symptom. `PERFORMANCE.md` P1
  records the originating symptom as "a rare, random hitch while dollying with
  the keyboard". A held keyboard dolly runs `applyCameraAuthorityHold` →
  `applyGlideHoldFrame` every frame: `createGlideCommand` (allocates via
  `createZoomViewCommand`), `reduceViewPose` → `zoomViewPose` →
  `setViewPoseDistance` (three cloned `Vector3`, a default-allocated direction
  vector, a result object), then `state.currentPose =
  cloneViewPose(state.restingPose)`. Roughly ten allocations per frame per held
  command, on the exact control the PR was motivated by. `reduceViewPose` in
  `viewReducer.ts` has no destination parameter at all; every arm of its switch
  returns a fresh `ViewPose`.
- **The orbit detent path.** `sampleOrbitDetentMotion` in `orbitDetent.ts`
  allocates `createOrbitDetentProgress` (spread direction plus `cloneViewPose`)
  and `getOrbitPose` → `reduceViewPose` → `orbitViewPose` → `getViewPoseAxes`
  (four cloned `Vector3` plus a result object) plus `getOrbitRotationAxis` (`new
  Vector3()`) plus the sample object, then `sampleActiveMotion` wraps the result
  in one more object. Around a dozen `Vector3` and half a dozen objects per
  frame, every frame of every orbit tap animation.
- **The gesture path.** `createGestureSession.mirrorPose` runs on every trackball
  `change` event, which can fire more than once per frame: `createViewPoseFromCamera`
  (three clones plus object), conditionally `setViewPoseDistance` (four more),
  `cloneViewPose` to reassign `latestPoseRef.current`, then `core.gesture.mirror`
  → `mirrorCameraAuthorityGesture` which clones twice more.
- **The track possession path.** `getFollowingCameraTrackPose` in
  `cameraTrackAuthority.ts` calls `cloneViewPose` to answer what is usually a
  boolean question. It is called from `advanceCameraAuthority` once per frame and
  from `getCameraAuthorityPoseMode`, which `cameraFrameWriter` calls twice per
  frame. With `setCameraTrackPose` → `createViewPoseFromSnapshot` and
  `anchorCameraAuthorityPose`'s two clones, possessed playback would allocate
  roughly eight `ViewPose` per frame before `advance` runs. Also
  `resolveCameraProjectionSample` allocates an object literal every frame while
  projection following is armed. (Currently unreachable — see G2 — but this is
  the path the camera track work lights up.)

**Two ownership regimes on one field.** `state.currentPose` is retained scratch
in `advanceCameraAuthority`, which writes through with `copyViewPose` at four
sites, and a freshly allocated object in ten other functions of the same file:
`applyGlideHoldFrame`, `applyCameraAuthorityView`, `applyInstantViewResult`,
`applyInstantZoomCommand`, `anchorCameraAuthorityPose`,
`prepareRestingPoseForView`, `beginCameraAuthorityGesture`,
`endCameraAuthorityGesture`, `mirrorCameraAuthorityGesture`, and the
`requestCameraMotion` callback all reassign it with `cloneViewPose`.

**The invariant is violated by production code.** `mirrorPose` in
`cameraGestureRuntime.ts` executes `latestPoseRef.current = cloneViewPose(pose)`.
`latestPoseRef.current` is the exact object `cameraFrameWriter` passes to
`resolveFrameInto` as the caller-owned retained destination. Every trackball
change event replaces the retained buffer #139 established. Nothing notices.

**Size of the tax.** Every future feature touching pose or command flow must
know, unwritten in the type system, whether a value it received is owned,
borrowed for the frame, or freshly allocated. `PERFORMANCE.md` names two
invariants governing this, and `cameraFrameWriter` carries two identical
five-line comment blocks warning against retention. Prose is the enforcement
mechanism. The audit brief notes a feature was scoped this session partly around
not capturing one of these aliases: the tax is being paid in design time, not
just review time.

**Is there a shape that keeps the performance without the hazard?** Yes:

1. Push destinations to the leaves. `reduceViewPose` and the four pose operations
   it calls (`orbitViewPose`, `translateViewPose`, `zoomViewPose`,
   `focusViewPose`) each gain a required destination parameter, exactly as
   `copyViewPose` and `interpolateViewPose` already have, and as
   `getViewOffsetDirection(position, target, destination)` already demonstrates
   inside `viewPose.ts`. Once the leaves take destinations, `applyGlideHoldFrame`
   and the orbit sampler become allocation-free with no new convention.
2. Brand the ownership. `Borrowed<ViewPose>` on frame-scoped returns,
   `Owned<ViewPose>` on retained fields. The existing erased-constraint trick in
   `copyViewPose` and `interpolateViewPose` shows the codebase already reaches
   for type-level enforcement when it can.
3. Make `state.currentPose` write-through only. Delete the ten reassignments.

This is the price of a real-time frame path only if you accept an allocating pose
algebra. The algebra is fifteen small pure functions in one 393-line file.

### T2. Two sources of scene truth, and one flat-scene assumption, in the same seam (question 6)

**Not isolated. Four instances, three through one seam — and the same seam
recursion forces open.**

The renderer draws `staged.scene`: `EditorStudio.EditorCanvas` passes
`scene={staged.scene}` from `useStagedScene` into `EditorRendererBinding`. Every
consumer below reads `getWorkingScene(state.workbench)`, the authored scene.

1. **Grid framing / Reset view.** `useEditorCommands.readStoreFramingInputs` →
   `FramingPort` → the `view` command's `resolve` → `computeGridFrame` →
   `viewportFocus.createGridFrameTarget`. This is the seam that failed today.
2. **Selection focus.** Same port → `computeSelectionFrame` →
   `viewportFocus.createGridViewportFocus`.
3. **Zoom bounds.** Same port → `computeZoomBounds` →
   `viewportFocus.createGridZoomBounds`, called from
   `interactionCore.syncCameraZoomBounds` on every frame carrying a view command
   or an active hold. Zoom clamps derive from authored geometry and the authored
   smallest cell size. The identity guard `state.zoomBoundsScene === inputs.scene`
   compares the authored scene object, so it never invalidates during playback.
4. **A parallel fourth assembly.** `SelectionFocusDriver` builds its own
   `SelectionFramingInputs` from `getWorkingScene` and calls
   `computeSelectionFrame` directly, bypassing the port. Fixing the port alone
   leaves this one wrong.

`SelectionFocusDriver` and `KeyboardShortcuts` are both mounted in `EditorStudio`
outside any `canvasInteractive` gate, so all four are reachable while the
transport drives the stage.

**Why the class exists, and why recursion lands here too.**
`interaction/framing.ts` declares `FramingInputs.scene: CubicellScene`. That type
cannot distinguish authored truth from staged truth, so any store read
type-checks — and it cannot distinguish flat from nested either, which is why
`createGridZoomBounds` reaches straight through to `scene.grid.format.cellSize`
and `createSceneGridLayout(scene.grid, scene.cells)`. One type is carrying two
wrong assumptions. `useStagedScene.sampleStageSource` already produces the value
the port should receive.

### T3. Six spellings of one idea, and two take their arguments in opposite orders (question 2)

**GROOM in appearance, TAX in substance, with one hazard TypeScript cannot see.**

The vocabulary: `destination` (`CameraAuthority.advance`,
`InteractionCore.resolveFrameInto`, `copyViewPose`, `IntentBus.drainViewFrame`,
`IntentBus.activeHolds`, `getViewOffsetDirection`, `interpolatePosition`),
`sample` (`getCameraMotionPose`), `scratch` (`coalesceViewCommandsInto`,
`resetCoalescedViewScratch`, `appendCoalescedViewCommand`,
`CommandResolveContext.viewCommandScratch`), and `pose` (`interpolateViewPose`).
Position varies (last, third-of-three, first). Optionality varies (required,
optional, optional-with-allocating-default).

The substantive hazard is inside `cameraAuthorityRuntime.ts`. Two functions
called in adjacent lines take `(ViewPose, ViewPose)` with **opposite** meanings
for the first argument:

- `copyViewPose(destination, source)` — first argument is written.
- `publishCameraAuthorityPose(pose, destination)` — first argument is read.

`advanceCameraAuthority` calls both, one after the other, in all four of its
branches. A transposition compiles, passes tests that assert value equality, and
silently corrupts pose truth. Unifying the spelling without introducing a
type-level distinction fixes the cosmetics and leaves the hazard. Unpark this
with the branding work in T1, not with a rename PR.

### T4. Nothing in the repository can falsify a performance claim (question 5)

**TAX, not a wall — and under recursion it becomes the item that gates the
decision.**

`PERFORMANCE.md` states it against its own P1 entry: "No repository test measures
frame pacing or garbage collection pressure, so this PR cannot verify that the
hitch is gone." Its shipped gates for that entry are entirely structural —
identity retention tests, exhaustiveness checks, and "the absence of allocating
production wrappers on the frame path". None can observe a hitch, and as T1
documents, allocating production paths were present the whole time on the very
control the symptom named.

The cost compounds through the delivery order. Items 3 through 5 of
`PERFORMANCE.md`'s table (GPU capacity, demand rendering, playback derivation)
carry gates phrased as measurements: "no draw calls during a three second
observation", "p95 frame time at or below 16.7 ms". The P0 sections got real
browser fixtures counting deterministic work; the frame path got prose.

**The elevation.** The addendum notes the flat model has already needed two
architecture-level rescues inside its stated 2,025-to-4,500 cell band, and that
recursion adds transform depth and multiplies cell counts on top of it with no
stated target for recursion depth, pieces per stage, or placements per piece.
Those two facts together are the real finding: **the go/no-go on recursion is
currently unanswerable, not because the architecture forecloses it, but because
nothing in the repository can measure whether the resulting scale is
survivable.** The missing targets and the missing measurement are the same gap.
Fix the probe first, state the capacity targets second, and the recursion
decision becomes a measurement rather than an argument. Every other item in this
report can wait behind that one.

## Grooming

### G1. `claimEditPointer` has no production caller — and that is documented and deliberate (question 3)

Its consumers are fully wired: `isEditPointerClaimed` in `cameraWheelZoom` and
`cameraPanGesture`, `subscribeEditPointerClaim` in `cameraGestureRuntime` driving
`controls.enabled`. `git log -S` puts the symbol in `114998a` (#65, the seam
reveal layer); the only commit containing the call `claimEditPointer()` is an
untracked-files stash commit on `feat/seam-verbs-headers`. Six tests keep it
green.

**Correction to my own first read:** this is not an accidental orphan.
`ARCHITECTURE.md` records it explicitly under Canvas Input Policy —
"`src/interaction/editPointerClaim.ts` is the infrastructure for seam drags and
future edge scrubs. Because the seam surface is parked, no live seam drag
currently claims the pointer" — and under Current Feature Status, that
`seamSurfacesEnabled` is `false` because the hit slabs interfered with selection.
A parked feature with a documented reason, a named future consumer, and its
suppression contract already wired is a well-designed seam awaiting its consumer.
Carry it forward. No action beyond leaving it alone.

### G2. The camera track subsystem is dark end to end, and three documents say otherwise (question 3)

Four independent gaps, verified:

1. **No prop producer.** `cameraTrack` is optional on `CubeSceneProps` in
   `renderer/contract.ts`, defaulted to `null` in `CubeScene`, forwarded to
   `CameraDriver`. Nothing in the tree ever supplies a non-null value;
   `EditorRendererBinding` does not pass it, and no test does either.
2. **No evaluator.** `CameraSample` has no producer anywhere in `src`.
3. **No authoring surface in the build.** `src/studio/` — `CameraTrackControls.tsx`,
   `cameraCapture.ts`, `index.ts` — has **zero production importers**. Its only
   importer in the repository is `tests/studioCameraControls.test.tsx`. It is
   test-only code living in `src/`. (Note the near-collision with `src/studios/`,
   which is live; the singular directory is the dark one.)
4. **A fully implemented authority behind all of it.** `cameraTrackAuthority.ts`,
   `cameraTrackFrame.ts`, the `track` pose mode, independent pose and projection
   detach, and rearm-by-epoch are complete and tested.

`INTERACTIVE.md` asserts "transport camera possession is shipped" and that
`syncCameraTrackFrame` "bridges authored samples each frame"; `ANIMATION.md` and
`STUDIO.ANIMATION.md` make the same claim. `MODEL.v2.md` says no runtime producer
drives it. **The code sides with `MODEL.v2.md`.** The subsystem is unreachable by
a user.

**Judgment: well-designed seams awaiting a consumer, not speculative
generality.** The possession model is exactly what `CAMERA.md` needs — one
authored claimant, pose and projection detaching on independent axes, rearm by
epoch, release on asset change — and the consumer is identified, specified, and
under active design. What is missing is not a design; it is three connections
(evaluator, prop threading in `EditorRendererBinding`, mounting `src/studio/`).
Carry it forward. But the documentation claim is false and should be corrected
now, because three documents currently assert a shipped capability that no user
can reach, and a rebuild decision made from those documents would be made on
false premises.

### G3. The test seam is in the wrong place (question 4)

`resolveFrame` appears twice in `src` (declaration and implementation) and 54
times across four test files. `resolveFrameInto` appears exactly twice in tests,
both in one assertion pair in `tests/interaction.core.test.ts`. `resolveFrame`
passes `authority.getPose()` as its destination, and `getPose` is
`cloneViewPose(state.currentPose)` — a fresh object every call, discarded.
Production passes `latestPoseRef.current`, retained across frames.

**How serious.** Moderate alone, severe in combination. The clone destination
means a retention bug cannot manifest by construction, so the 54-call corpus is
structurally blind to the one defect class the #139 regime introduced. Worse, it
makes the regime's own tests uninformative: an assertion that frame N's output is
independent of frame N+1 passes trivially when every frame gets a new object.
Right shape: tests allocate one destination in a fixture helper and reuse it, so
test lifetime equals production lifetime, and `resolveFrame` is deleted. Same for
`coalesceViewCommands`, whose seven assertions in
`tests/interaction.viewLane.test.ts` sit exactly where reused-scratch carry bugs
would show.

### G4. Smaller items

- **`getState()` allocates a pose snapshot to read a boolean.**
  `cameraProjectionSwap` calls `core.getState().morphing` at two sites while
  `InteractionCore.isMorphing()` exists on the same interface.
  `composeSnapshot` calls `authority.getPose()` (a clone),
  `toCameraPoseSnapshot` (three arrays), and the selection port on every call.
- **Holds are resolved by two near-identical loops.** `resolveActiveCoreHolds`
  and `coalesceActiveCoreHoldsInto` in `interactionCore.ts` differ only in sink
  and in which `CommandResolveContext` they use. `resolveContext` has no
  `viewCommandScratch`, so `holds.active()` allocates where the frame path does
  not. Fold into one loop parameterized by sink.
- **`cameraAuthorityRuntime.ts` at 662 lines carries eleven responsibilities.**
  Under the ceiling, and its functions are individually small and well named,
  which is why it reads fine. The cohesion problem is the file: pose publish,
  glide hold, view application, instant zoom, gesture inversion, track
  anchoring, focus restore, orbit bookkeeping, motion port lifecycle, zoom
  bounds, and feel config. It is the natural landing site for T1's restructure as
  a three-way split.
- **`resolveCoreCommand` uses exceptions for control flow.**
  `commandRegistry.get(command.kind)` is wrapped in `try { } catch { return
  command }`, putting a thrown-and-swallowed error on a path that runs per hold
  per frame. A `has`/`tryGet` removes the throw.
- **`createViewportFocusGeometry` rebuilds a full cell map per call.**
  `createSceneGridLayout` plus `new Map(scene.cells.map(...))` on every
  `createGridZoomBounds`. Guarded by scene identity in `syncCameraZoomBounds`, so
  it is once per (edit, camera-input) pair rather than per frame — acceptable
  today, and it becomes a tree walk under recursion, so fold it into the T2
  boundary move rather than optimizing it in place.

## Fine

Leave these alone. They are healthy and a rebuild should reproduce them as-is.

- **`src/pose/` as a pure algebra.** `viewPose.ts` and `projectionMatch.ts` carry
  the canonical-zoom model: pose position is spatial truth, canonical zoom is
  orthographic pixels per world unit, and `applyViewPoseToCamera` is the one
  place the two projections convert into each other. `CAMERA.md`'s framing
  formulas are derivable from what is here. Aside from missing destination
  parameters (T1), this is the best code in the slice.
- **The camera's independence from the scene.** The single most valuable
  property in the slice, and the reason recursion is survivable. Preserve it
  deliberately: the fix for T2 must keep scene knowledge on the view-policy side
  of the port and out of the authority.
- **`CubeLayoutPose` as the render contract.** A composable TRS per cell,
  consumed by the instancing layer instead of grid coordinates, with
  `useStableGridLayout` preserving identity across recomputes. This is what makes
  recursion a layout-builder change rather than a renderer rewrite.
- **The port boundary between `interaction` and `view`.** `interaction/framing.ts`
  declares `ComputeGridFrame`, `ComputeSelectionFrame`, and `ComputeZoomBounds`
  as signatures only, with an explicit comment that interaction must not depend
  on the view barrel; `view/interactionFraming.ts` supplies the implementations.
  A correctly inverted dependency. T2 is a defect in what crosses the port, not
  in the port.
- **The two-lane bus.** 73 lines doing exactly what `INTERACTIVE.md` says: view
  commands buffer into a frame lane, everything else goes straight through
  `ports.runSynchronous` in dispatch order, holds are a keyed map. No arbitration
  leaks into the synchronous lane.
- **The slot registry and patch protocol.** Key-to-slot allocation with bounded
  dirty ranges, agnostic to where keys come from. Reusable under recursion once
  keys are path-qualified.
- **The journal continuity discipline.** `journalContinues` checks sequence
  adjacency, endpoint scene identity, and intra-batch chaining, and any failure
  falls back to a full rebuild. Conservative in the right direction, and it is
  what makes the incremental owner safe to keep under a model change.
- **Exhaustiveness enforcement.** `appendCoalescedViewCommand`'s `const
  exhaustiveView: never` and the erased `_UnhandledViewPoseField` constraints on
  `copyViewPose` and `interpolateViewPose` make a new command kind or pose field
  a compile error at the sites that must handle it. T1's branding should extend
  this, not replace it.
- **`resetCoalescedViewScratch`'s defence in depth.** The comment explaining why
  the reset block must not be deleted as redundant — first-assignment masks its
  removal, so tests cannot catch it — is exactly the knowledge that usually
  evaporates.
- **`renderer/` as a capability boundary.** The one-line re-exports look odd in
  isolation, but `PERFORMANCE.md`'s Slice 4 result shows `checkRendererOwnership`
  proving every Editor route to a renderer module crosses a declared owner root,
  with camera motion landing as an 804 B deferred increment. Load-bearing for the
  bundle budget.
- **`motion/cameraMotion.ts`.** Module-level scratch vectors and quaternions with
  a comment stating sampling is synchronous and values are copied into the
  caller-owned sample before return. This is the scratch regime done right, and
  the model the rest of T1 should follow.
- **The shipped orbit-arc geometry.** `deriveShortestCameraOrbitArc` and the
  endpoint-compatibility check in `domain/cameraTrack.ts` are the signed sweep
  `CAMERA.md`'s orbit channel adopts by name. Carry forward verbatim.
- **`transport/` shape.** Eight files, 368 LOC, largest 145. `useStagedScene`
  documents itself as "the sole adapter where session time meets authored
  Workbench state", and it is.
- **Orbit detent semantics.** The non-collinear-interrupt comment in
  `getCompatibleOrbitProgress` explaining the corner-key flicker preserves a real
  behavioural insight at the site that carries it. The allocation problem (T1) is
  orthogonal to the logic, which is correct.

## Evidence

### Answers to the original seven questions

1. **Scratch regime cost.** TAX, large. It covers the idle publish, bus, and
   coalescing lanes and misses the glide, orbit, gesture, and possession lanes —
   the four that run during sustained motion. A shape exists that removes the
   hazard: destinations at the leaves of the pose algebra plus branded ownership.
   Not simply the price of a real-time frame path.
2. **Naming divergence.** TAX, symptom of a missing abstraction.
   `copyViewPose(dst, src)` and `publishCameraAuthorityPose(src, dst)` are
   adjacent, same-typed, and opposite. Fix with branding, not renaming.
3. **Possession and `claimEditPointer`.** Both are well-designed seams awaiting
   consumers, not speculative generality — `claimEditPointer` documented as
   parked in `ARCHITECTURE.md`, possession specified in `CAMERA.md` and under
   active design. Carry both forward. Correct `INTERACTIVE.md`, `ANIMATION.md`,
   and `STUDIO.ANIMATION.md`, which claim a shipped capability no user can reach.
4. **Test-facing surface.** GROOM, and a genuine symptom of a misplaced seam.
   54 `resolveFrame` calls versus one `resolveFrameInto` test, with the wrapper
   handing tests a fresh clone where production hands a retained ref.
5. **Verifiability.** TAX, not a wall — but elevated by the addendum to the item
   that gates the recursion decision. See T4.
6. **The failed seam.** A class, four instances, and the same seam recursion
   forces open. Root cause is `FramingInputs.scene: CubicellScene`, one type
   carrying two wrong assumptions (authored-versus-staged, flat-versus-nested).
7. **File and module health.** Good. No file over 700 (largest 662 and 525), no
   function over ~40 lines, no structural duplicate clusters, no cycles, clean
   dependency direction with `oxlint no-restricted-imports` closing deep paths.
   Dark paths: the `cameraTrack` prop chain, the absent `CameraSample` producer,
   the orphaned `src/studio/` tree, `resolveFrame` and `coalesceViewCommands` as
   production exports.

### Answers to the four addendum questions

1. **Is the incremental scene owner reusable under recursion?** Needs reshaping;
   mostly reusable; not foreclosing. Slots, patches, and journal continuity carry
   forward unchanged. The break is the flat integer-lattice key namespace in
   `incrementalCubeRenderResolution`, fixed by path-qualifying keys, plus one
   product decision on cross-grid burial.
2. **Instancing flattening a transform chain, evaluation mapping cue time per
   placement.** The instancing side is already solved: `CubeLayoutPose` is a
   composable TRS and the renderer never sees grid coordinates. The evaluation
   side is the open one: `CubeSceneRenderInput.options.partColors` is a
   `Map<cellId, CubePartColorTweens>` produced from one `Moment` at one time, and
   the identity check `previous.colorTweens !== …get(cell.id)` requires the
   evaluation layer to preserve identity for unchanged placements. Per-placement
   cue time makes that a per-path map with an identity-stability obligation. That
   obligation is new and should be designed deliberately, not discovered.
3. **Does the camera evaluator absorb a per-channel model?** There is no
   evaluator. Greenfield write, not a replacement; the wire bump is a version
   increment under the repository's no-migration policy; the frame-side consumer
   already has the right shape; the shipped orbit-arc math carries forward.
4. **Dark machinery and the document conflict.** The code sides with
   `MODEL.v2.md` — four independent gaps, listed in G2. It does not change my
   judgment that possession is a good seam, but it does mean three documents are
   currently wrong, and any rebuild argument sourced from them is standing on a
   false premise.

### Method and limits

Read-only, using `fmm` for inventory, symbol lookup, structural duplicate
clustering, and dependency direction, plus targeted reads and `git log -S` for
provenance. No builds, no typecheck, no dev server, no browser, no subagents.

**What I did not verify.** Every allocation claim in T1 is a traced call chain
read from source, not a measured count. That distinction matters more than usual
here, because the whole of T4 is that this repository cannot measure. Read the
chains as "this code path constructs these objects", which is checkable by
reading, and not as "this costs N bytes per frame", which is not. Per-frame
counts are approximate and labelled as such at each site. I did not run the test
suite, so statements about coverage rest on grep counts against `tests/` — exact
for symbol occurrences, silent on what the tests assert. My recursion analysis
of `src/scene/` traces the key namespace and the layout contract; I did not audit
`incrementalEdgeResolution.ts` or `authoredRenderImpact.ts` in depth, so the
per-grid-burial claim in step 1 is reasoned from the occupancy key and neighbor
arithmetic rather than from a full read of the edge resolver. I did not audit
`src/state/`, `src/evaluation/`, or `src/domain/` beyond the specific reads needed
to answer the recursion and camera-track questions; siblings own those.
