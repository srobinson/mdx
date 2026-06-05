# Cubicell Camera Runtime Scout

Baseline: `main` at `71098b4ee21117d8431e71288edef42f61908854`.

Scope: camera runtime only. Evidence comes from the pinned tree through
`git show main:<path>` and symbol inspection. No browser, server, harness, or
runtime process was used.

## Findings

### 1. Runtime authority, authored intent, and frame output

The canonical runtime pose is `ViewPose` in
`src/pose/viewPose.ts:ViewPose`:

```ts
type ViewPose = {
  position: Vector3
  target: Vector3
  up: Vector3
  zoom: number
}
```

The public owner is `src/interaction/authority.ts:CameraAuthority`. Its
implementation is `src/camera/cameraAuthorityRuntime.ts:createCameraAuthorityRuntime`,
backed by private `CameraAuthorityState`.

Three distinct values matter:

| Value | Owner | Meaning |
| --- | --- | --- |
| Durable authored camera intent | `src/domain/cameraTrack.ts:CameraKeyframe.pose` | A `CameraPoseSnapshot` stored in an Animation camera track. |
| Settled runtime command target | `src/camera/cameraAuthorityRuntime.ts:CameraAuthorityState.restingPose` | The destination produced by the latest view command. This value is runtime memory and has no public getter. |
| Current frame output | `src/camera/cameraAuthorityRuntime.ts:CameraAuthorityState.currentPose` | The latest gesture, camera track, motion sample, or settled pose selected by `advanceCameraAuthority`. |

Projection is separate. `CameraState` includes it for an initial seed, while
`InteractionSnapshot` and `CameraKeyframe` carry `projection` beside the pose.
Evidence: `src/pose/cameraState.ts:CameraState`,
`src/interaction/snapshot.ts:InteractionSnapshot`, and
`src/domain/cameraTrack.ts:CameraKeyframe`.

PR #139 introduced retained output storage throughout the production frame
path. The ownership rules are:

| Object | Lifetime and mutation |
| --- | --- |
| `src/camera/CameraDriver.tsx:CameraDriver.latestPoseRef.current` | Retained by the driver and overwritten in place every frame by `InteractionCore.resolveFrameInto`. This is a live alias. A feature must never retain or persist it. |
| `src/camera/cameraAuthorityRuntime.ts:CameraAuthorityState.currentPose` | Retained inside the authority. `advanceCameraAuthority` normally mutates its existing `Vector3` members through `copyViewPose`. Some authority transitions replace the slot with a fresh clone. Raw access is private. |
| `src/camera/cameraAuthorityRuntime.ts:CameraAuthorityState.motionSample.pose` | Retained motion scratch. `src/motion/cameraMotion.ts:getCameraMotionPose` and `interpolateViewPose` mutate it in place on every sample. |
| `src/interaction/interactionCore.ts:createInteractionCore.viewFrameCommands` and `activeHoldCommands` | Retained arrays. `src/interaction/bus.ts:createIntentBus` drains or copies into them after clearing their prior contents. |
| `src/interaction/interactionCore.ts:createInteractionCore.viewFrameScratch` and `holdFrameScratch` | Retained `CoalescedViewScratch` objects. `src/interaction/viewLane.ts:coalesceViewCommandsInto` resets and mutates their result, command objects, and additive array. |
| `src/interaction/interactionCore.ts:createInteractionCore.holdResolveScratch` | Retained command output. `src/interaction/commands/view.commands.ts:resolveViewCommandForProjection` can mutate and return its command members. |
| `src/camera/cameraFrameWriter.ts:useSingleCameraWriterFrame.frameStateRef` | Retained liveness record, mutated before each synchronous report. |

Fresh, safe boundaries already exist:

- `src/camera/cameraAuthorityRuntime.ts:createCameraAuthorityRuntime.getPose`
  returns `cloneViewPose(state.currentPose)`.
- `src/interaction/snapshot.ts:composeSnapshot` converts that clone through
  `toCameraPoseSnapshot`, which allocates fresh number tuples.
- `src/pose/viewPose.ts:cloneViewPose`,
  `createViewPoseFromCameraState`, and `createViewPoseFromSnapshot` create new
  `Vector3` members.
- `src/motion/cameraMotion.ts:createCameraMotionPlan` clones its `from` and
  `to` endpoints once. Those retained endpoints are stable plan inputs rather
  than live frame output.

A naive snapshot of `latestPoseRef.current`, `motionSample.pose`, a coalesced
view result, or any caller owned frame destination will change under the next
frame. `InteractionCore.getState().pose` is the existing safe read.

### 2. Existing persistence, restore, defaults, and reset

Current editor camera pose persistence was not found.

What does exist:

1. Authored camera tracks persist camera poses. A
   `src/domain/cameraTrack.ts:CameraKeyframe` stores
   `CameraPoseSnapshot` plus `ProjectionMode`. Studio capture uses
   `src/studio/CameraTrackControls.tsx:CameraTrackControls.capture` and
   `src/studio/cameraCapture.ts:createCameraCapture`. The Animation asset is
   encoded and decoded through
   `src/persistence/recordCodecs/animationRecordCodec.ts:encodeAnimationRecord`
   and `decodeAnimationRecord`.
2. Focus mode keeps one temporary restore pose in
   `src/camera/cameraAuthorityRuntime.ts:CameraAuthorityState.focusRestorePose`.
   `saveCameraAuthorityFocusRestorePose` samples the authority at the supplied
   time. `takeCameraAuthorityFocusRestorePose` clones and clears it.
   `src/interaction/commands/view.commands.ts:registerViewCommands` restores it
   through the ordinary view lane. This value is memory only.
3. A session starts from
   `src/app/useEditorCommands.ts:useEditorCommands.initialView`, which calls
   `src/view/viewportFocus.ts:createGridFramedCamera` with the working scene and
   current viewport. An empty scene falls back to
   `src/pose/cameraState.ts:defaultCamera`.
4. Reset is the existing home equivalent. `src/editor/commands.ts:createResetViewCommand`
   is enriched by `src/interaction/commands/view.commands.ts:registerViewCommands`
   through `src/view/interactionFraming.ts:computeGridFrame`, which calls
   `src/view/viewportFocus.ts:createGridFrameTarget`. No separate camera home
   symbol exists.

The Zustand state has no current camera pose field.
`src/state/cubicellState.ts:CubicellEditorSession`,
`CubicellPreferences`, and `CubicellUserProjectState` omit `CameraState`,
`ViewPose`, and `CameraPoseSnapshot`. The durable `workbench` can contain
Animation camera tracks, which is the authored persistence described above.

Local storage contains `CubicellPreferenceRecord`, including viewport mode and
camera feel preferences. Session storage contains the client ID. Neither
contains camera pose. Evidence:
`src/state/preferencePort.ts:CubicellPreferenceRecord`,
`createLocalStoragePreferencePort`, and `normalizeGlobalPreferences`.

URL parsing is limited to the capability preview query parameter.
`src/main.tsx` passes `window.location.search` to
`src/studios/capabilityPreview.ts:parseCapabilityPreviewOverrides`. No camera,
view, or pose parameter exists.

Exact persistence and restore searches:

```sh
git grep -n -E 'localStorage|sessionStorage|URLSearchParams|location\.(search|hash)|searchParams' main -- src
git grep -n -E 'CameraPoseSnapshot|ViewPose|CameraState' main -- src/state/cubicellState.ts src/state/cubicellStore.ts src/state/preferencePort.ts
git grep -n -E 'createRestoreViewCommand|saveFocusRestorePose|takeFocusRestorePose|capture-camera-keyframe|createGridFramedCamera|createResetViewCommand' main -- src
git grep -n -E '"home"|homeCamera|cameraHome|HomeCamera' main -- src
```

### 3. Meaning of current camera position at capture time

There are three candidate answers:

| Candidate | Symbol | Consequence |
| --- | --- | --- |
| Settled command target | `src/camera/cameraAuthorityRuntime.ts:CameraAuthorityState.restingPose` | Captures where an ease will finish. During a glide this can describe a position the user has not reached or seen. |
| In flight visual pose | `src/camera/cameraAuthorityRuntime.ts:CameraAuthorityState.currentPose`, exposed safely by `src/interaction/interactionCore.ts:InteractionCore.getState` | Captures the most recently resolved visible frame. |
| Active ease endpoint | `src/motion/cameraMotionPolicy.ts:CameraMotionPlan.to`, created by `src/camera/cameraAuthorityRuntime.ts:requestCameraMotion` | Captures the stable endpoint of the active motion plan. While the lazy motion module is pending, the equivalent target remains `restingPose`. There is no public endpoint getter. |

The correct save result for a human pressing save mid glide is the in flight
visual pose from `InteractionCore.getState().pose`.

Reasons:

- The user asked to preserve the view currently on screen.
- The endpoint may never become visible because camera input can interrupt or
  retarget the motion.
- The existing camera keyframe feature already uses this meaning.
  `src/studios/editor/EditorStudio.tsx:EditorStudio` supplies `core.getState`
  through `src/panels/editorCommandContext.ts:CameraSnapshotReader`.
  `src/studio/CameraTrackControls.tsx:CameraTrackControls.capture` reads that
  snapshot.
- `CameraAuthority.getPose` clones `currentPose`, and
  `toCameraPoseSnapshot` creates fresh tuples. Later frames cannot overwrite
  the captured value.

`getState` reads the last resolved frame. It does not advance motion to the
event timestamp. That matches the visible canvas because the camera changes
only when a frame resolves. Calling `resolveFrameInto` from a save action would
also drain queued commands and mutate frame state, so it would give capture an
unwanted execution side effect.

A projection blend is transient runtime output. The existing snapshot reader
returns the discrete `projection` beside the pose and reports `morphing`
separately. A saved State should not serialize projection matrices,
`orthographicWeight`, or partial morph progress.

### 4. Existing apply, jump, and ease paths

The general apply path already exists:

```ts
dispatch(
  createEditorViewCommand(
    createRestoreViewCommand(snapshot)
  )
)
```

Evidence:

- `src/editor/commands.ts:createRestoreViewCommand` clones the supplied
  `CameraPoseSnapshot`.
- `src/editor/commands.ts:createEditorViewCommand` wraps it for dispatch.
- `src/interaction/command.ts:isAbsoluteViewCommand` classifies `restore` as
  absolute.
- `src/interaction/viewReducer.ts:reduceViewPose` routes it to
  `src/pose/viewPose.ts:restoreViewPose`.
- `restoreViewPose` calls `createViewPoseFromSnapshot` with current zoom bounds.

The production path animates a restore. Normal frame resolution passes
`instant: false`. `src/camera/cameraAuthorityRuntime.ts:applyCameraAuthorityView`
therefore calls `requestCameraMotion`.
`src/motion/cameraMotionPolicy.ts:getViewCommandMotionDuration` assigns restore
the existing focus duration of 260 ms, and `getViewCommandMotionPath` assigns
the linear path. `src/motion/cameraMotion.ts:getCameraMotionPose` applies
`easeOutQuart` while interpolating position, target, up, and zoom.

The runtime also has a jump distinction:

- `src/interaction/interactionCore.ts:InteractionCore.resolveFrame` and
  `resolveFrameInto` accept `{ instant: true }`.
- The instant branch reaches
  `src/camera/cameraAuthorityRuntime.ts:applyInstantViewResult`.
- `src/pose/viewPose.ts:applyViewPoseToCamera` performs the final immediate
  Three camera write, but the single writer owns that call. A feature calling
  it directly would be overwritten by the authority on the next frame.

There is no general command constructor dedicated to a snapped pose restore.
The frame option supplies that distinction internally. Camera track playback
also has `src/interaction/interactionCore.ts:InteractionCore.track.setPose`,
which applies sampled track poses immediately while track possession is
active. That path belongs to playback and should not be repurposed for a saved
State.

If saved State restore should ease, the existing restore command and motion
policy are complete. No camera runtime helper is needed.

### 5. Minimal serializable pose

The minimal existing form is
`src/domain/cameraTrack.ts:CameraPoseSnapshot`:

```ts
type CameraPoseSnapshot = {
  position: [number, number, number]
  target: [number, number, number]
  up: [number, number, number]
  zoom: number
}
```

`position` and `target` together preserve view direction and radius. `up`
preserves roll. `zoom` preserves canonical target plane scale. Projection
remains a separate `ProjectionMode`.

This type is plain structured clone and JSON safe data. It has no Three
objects, matrices, callbacks, refs, derived clip planes, or motion state.
`src/state/cameraTrackValidation.ts:isCameraPose` already validates exact
keys, finite tuples, positive zoom, nonzero view direction, and a noncollinear
up vector.

`ViewPose` is not a serialization type because its vectors are live
`Vector3` instances. A Three `Camera` is also unsuitable because its
projection matrix, inverse, near and far planes, `fov`, and rendered
orthographic position are derived. Use
`src/interaction/snapshot.ts:toCameraPoseSnapshot`.

Viewport sensitivity:

- `src/pose/viewPose.ts:createViewPoseFromCamera` defines `zoom` as
  orthographic pixels per world unit. It converts perspective distance,
  magnification, viewport height, and live `fov` into that canonical number.
- A restored `zoom` preserves target plane pixel scale. A larger or differently
  shaped viewport shows a different world extent, so the composition cannot be
  identical after a resize.
- `src/pose/viewPose.ts:applyViewPoseToCamera` derives perspective
  magnification and orthographic clip safe distance from viewport height.
  Orthographic render camera position is therefore derived from the pose and
  current viewport.
- `src/interaction/interactionCore.ts:InteractionCore.setViewportSize`
  refreshes bounds through
  `src/view/viewportFocus.ts:createGridZoomBounds`. The restore reducer clamps
  saved zoom to the current bounds. A resize or scene change can therefore
  change an extreme saved zoom.
- Aspect ratio and device pixel ratio are absent from the pose. Aspect changes
  horizontal framing. Device pixel ratio should remain a renderer preference,
  outside camera state.

### 6. Exhaustive capability reuse

| Needed capability | Existing owner | Required use |
| --- | --- | --- |
| Read the visible pose | `src/interaction/interactionCore.ts:InteractionCore.getState`, implemented by `src/interaction/snapshot.ts:composeSnapshot` | Read `pose` and `projection`. This returns fresh plain data. |
| Supply the reader to feature UI | `src/panels/editorCommandContext.ts:CameraSnapshotReader`, `CameraSnapshotContext`, and `useCameraSnapshotReader` | Reuse the same context already consumed by Camera Track capture. |
| Validate a pose | `src/state/cameraTrackValidation.ts:isCameraPose` | Reuse the strict exact shape and geometric guard. |
| Validate projection | `src/state/cameraTrackValidation.ts:isProjectionMode` | Reuse if the saved State camera contract includes projection. |
| Convert runtime vectors to wire data | `src/interaction/snapshot.ts:toCameraPoseSnapshot` | Reuse when the caller has a `ViewPose`. UI callers already receive the converted form from `getState`. |
| Convert wire data to runtime vectors | `src/pose/viewPose.ts:createViewPoseFromSnapshot` | Reuse through the restore reducer. It normalizes up and zoom. |
| Apply a pose | `src/editor/commands.ts:createRestoreViewCommand` plus `createEditorViewCommand` | Dispatch through the established view lane. |
| Interpret a pose restore | `src/interaction/viewReducer.ts:reduceViewPose` and `src/pose/viewPose.ts:restoreViewPose` | Reuse without a parallel reducer or direct camera write. |
| Ease to a pose | `src/motion/cameraMotionPolicy.ts:getViewCommandMotionDuration`, `getViewCommandMotionPath`, `src/camera/cameraAuthorityRuntime.ts:requestCameraMotion`, and `src/motion/cameraMotion.ts:getCameraMotionPose` | Existing restore behavior is 260 ms, linear spatial path, `easeOutQuart` timing. |
| Snap internally | `src/interaction/interactionCore.ts:InteractionCore.resolveFrame` or `resolveFrameInto` with `{ instant: true }`, then `src/camera/cameraAuthorityRuntime.ts:applyInstantViewResult` | No new public snap command is needed for an eased saved State restore. |
| Serialize pose data | `src/domain/cameraTrack.ts:CameraPoseSnapshot` | Persist the plain fields inside the saved State owner. No camera specific byte codec is required. |
| Existing durable camera precedent | `src/studio/cameraCapture.ts:createCameraCapture` and `src/persistence/recordCodecs/animationRecordCodec.ts:encodeAnimationRecord` | Use as proof that the snapshot is already durable wire data. Do not call `createCameraCapture` for a saved State because it creates or edits an Animation. |
| Session default | `src/view/viewportFocus.ts:createGridFramedCamera` | Retain for sessions without a saved camera. |
| Reset frame | `src/editor/commands.ts:createResetViewCommand` and `src/view/viewportFocus.ts:createGridFrameTarget` | Retain as the explicit reset behavior. |

Every required camera capability has an existing owner. A new pose type,
camera reader, validator, serializer, direct writer, restore reducer, or ease
helper would duplicate live code.

### 7. Deferred frame path naming convergence

The six caller supplied output spellings are present:

1. `src/interaction/authority.ts:CameraAuthority.advance`
2. `src/interaction/interactionCore.ts:InteractionCore.resolveFrameInto`
3. `src/pose/viewPose.ts:copyViewPose`
4. `src/motion/cameraMotion.ts:getCameraMotionPose`
5. `src/interaction/viewLane.ts:coalesceViewCommandsInto`
6. `src/interaction/bus.ts:IntentBus.drainViewFrame`

A camera snapshot feature does not need to change this frame path.
`InteractionCore.getState` already returns the safe value. Restore already
enters through the command bus. Validation and persistence operate on
`CameraPoseSnapshot`.

The naming convergence does not need to land first if implementation uses
those seams. Treat any proposed edit to the six functions, `CameraDriver`,
`cameraFrameWriter`, `cameraAuthorityRuntime`, or camera motion sampling as a
scope warning. If such an edit becomes genuinely necessary, the parked naming
convergence is the required first slice because the feature would then be the
next change to the frame path.

## Reuse Map

| Layer | Existing vocabulary or seam | Camera in State role |
| --- | --- | --- |
| Domain | `src/domain/cameraTrack.ts:CameraPoseSnapshot` | Reuse as the camera pose value. Keep `ProjectionMode` adjacent and separate. |
| Runtime pose | `src/pose/viewPose.ts:ViewPose` | Remains internal live vector state. |
| Runtime authority | `src/interaction/authority.ts:CameraAuthority` | Remains the sole pose authority. |
| Safe read adapter | `src/interaction/snapshot.ts:composeSnapshot` and `toCameraPoseSnapshot` | Supplies a detached current pose. |
| UI injection | `src/panels/editorCommandContext.ts:CameraSnapshotReader` | Supplies capture without importing camera runtime or Three. |
| Validation | `src/state/cameraTrackValidation.ts:isCameraPose` | Validates untrusted saved State camera data. |
| Command adapter | `src/editor/commands.ts:createRestoreViewCommand` | Applies saved pose through existing command ownership. |
| Motion | `src/motion/cameraMotionPolicy.ts:getViewCommandMotionDuration` | Preserves current restore feel. |
| Renderer | `src/camera/cameraFrameWriter.ts:useSingleCameraWriterFrame` | No feature change. Continues as sole camera writer. |
| Existing durable precedent | `src/studio/cameraCapture.ts:createCameraCapture` | Confirms the pose and projection pair is already captured and persisted elsewhere. |

The shortest lawful path is:

```text
CameraSnapshotReader
  -> plain CameraPoseSnapshot plus ProjectionMode
  -> saved State owner
  -> strict existing validation on load
  -> createRestoreViewCommand
  -> existing camera motion
  -> single camera writer
```

## Quality Map

### Existing strengths

- Domain wire data is dependency neutral.
- The runtime and serialized types are already separated.
- Capture already clones across the live frame boundary.
- Restore already uses the authority and single writer.
- Validation rejects degenerate camera geometry.
- Motion policy already distinguishes normal ease from internal instant
  resolution.
- PR #139 has explicit caller ownership and identity tests around reused
  buffers.

### Risks to preserve

| Risk | Guard |
| --- | --- |
| A saved camera aliases live frame scratch | Read only through `InteractionCore.getState` or `CameraSnapshotReader`. |
| Capture records an unseen ease endpoint | Save `currentPose` through `getState`, not `restingPose` or `CameraMotionPlan.to`. |
| Restore writes Three directly and is clobbered next frame | Dispatch the existing restore view command. |
| Restore duplicates the camera track apply path | Keep saved State restore in the view lane. Track possession remains playback owned. |
| A resized viewport changes framing | Document canonical zoom semantics and verify current bounds behavior. |
| Projection morph internals leak into persistence | Save discrete projection only. Exclude matrices and morph progress. |
| Validation drifts between Camera Track and saved State | Reuse `isCameraPose` and `isProjectionMode`. |
| A small feature expands the frame runtime | Avoid `cameraAuthorityRuntime.ts`, currently 662 lines and close to the 700 line threshold. |
| The parked naming blocker is bypassed | Trigger convergence first if any frame path symbol must change. |

### Verification gates for a later implementation

1. Capture during an active ease and prove the stored pose equals the visible
   in flight frame, differs from the endpoint, and remains unchanged after
   later frames.
2. Capture while idle, during gesture ownership, and during camera track
   ownership.
3. Restore through the command adapter and prove it eases to the saved pose.
4. Prove restore interrupts or detaches active camera track pose following
   through the existing authority behavior.
5. Validate malformed tuples, nonfinite values, zero zoom, zero view direction,
   and collinear up vectors through `isCameraPose`.
6. Resize between capture and restore. Assert the intended canonical zoom and
   current bounds behavior.
7. Prove the renderer remains the sole Three camera writer.
8. Run source ownership and retained identity tests if any frame path file
   changes. Under the recommended plan, those files remain untouched.

## Plan

1. Scout A can reuse the existing camera side contract:
   `CameraPoseSnapshot` plus adjacent `ProjectionMode`. Camera runtime does not
   need another saved shape.
2. At saved State capture, read `CameraSnapshotReader`. Store its detached
   `pose` and `projection` in the owner selected by Scout A.
3. At the saved State read boundary, call `isCameraPose` and
   `isProjectionMode`. Keep load repair with the saved State owner.
4. At apply, dispatch
   `createEditorViewCommand(createRestoreViewCommand(saved.pose))`.
   Preserve the existing 260 ms ease.
5. Apply the discrete projection through its existing consumer owner. Do not
   persist partial projection morph output.
6. Add the focused gates from the Quality Map. The mid glide retained identity
   test is the critical proof.
7. Keep the camera frame path unchanged. Naming convergence stays parked. If
   implementation discovers a true frame path requirement, land convergence
   before the feature edit.

Camera runtime implementation cost should be zero or close to zero. The feature
already has a safe reader, a durable data type, strict validation, a restore
command, and easing. The main work belongs to the saved State owner and its
consumer coordination.
