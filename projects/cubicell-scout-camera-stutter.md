# Cubicell camera stutter scout

## Scope and baseline

Read only source trace for `e866889451d83b12ee04b2b18d39ca8e6d7c9c00`, current `main` after PR 136 and PR 137.

The requested checkout was pristine on `docs/performance-audit` at the start of the trace. A concurrent worker later switched the checkout to `fix/save-failure-surface` at the same commit and added unrelated durability edits. I did not touch those edits. Every source citation below was verified with `git show e866889:<path>`.

No browser was driven. No source or test file was written. The only write is this report.

## Corrected finding

The reported defect is rare and random. That refutes application repeat cadence as its cause. The 320 ms initial delay, 240 ms repeat interval, and 220 ms tap motion are deterministic. They can explain a constant feel characteristic, but not a hitch that appears occasionally.

The highest current suspect is garbage collection caused by camera frame allocation churn. The allocation sites are verified. Garbage collection as the observed hitch is **UNVERIFIED** without a runtime profile.

The proposed checkpoint lead is also refuted. Camera dolly does not create a document operation, a view lane scene operation, a history entry, or a durability unit. It cannot trigger the full aggregate checkpoint scan.

## Camera dolly does not reach history or durability

### Command identity

`ViewCommand` contains orbit, translate, and zoom. Zoom carries its `dolly` and motion fields: `src/editor/commands.ts:27`, `src/editor/commands.ts:40`, `src/editor/commands.ts:45`.

The wrapper is an `EditorCommand` with `kind: "view"`: `src/editor/commands.ts:63`, `src/editor/commands.ts:67`, `src/editor/commands.ts:219`, `src/editor/commands.ts:223`.

Keyboard `+` and `-` resolve to zoom commands: `src/editor/keyboard/keymap.ts:7`, `src/editor/keyboard/keymap.ts:8`, `src/editor/keyboard/keymap.ts:19`, `src/editor/keyboard/keymap.ts:21`. Their definitions wrap `createZoomViewCommand` in `createEditorViewCommand`: `src/editor/affordances.ts:278`, `src/editor/affordances.ts:284`.

Wheel input also dispatches a wrapped view command. It marks the zoom `instant`: `src/camera/cameraWheelZoom.ts:20`, `src/camera/cameraWheelZoom.ts:32`.

In perspective projection, a zoom that is not already a dolly is rewritten to `dolly: true`, while remaining a view command: `src/interaction/commands/view.commands.ts:101`, `src/interaction/commands/view.commands.ts:112`.

### Local view queue

The view descriptor uses target and lane `view`, is non reversible, and classifies translate and zoom as holdable: `src/interaction/commands/view.commands.ts:14`, `src/interaction/commands/view.commands.ts:24`, `src/interaction/commands/view.commands.ts:115`, `src/interaction/commands/view.commands.ts:127`.

The intent bus routes non view commands to the synchronous port. View commands are appended only to its in memory frame queue: `src/interaction/bus.ts:44`, `src/interaction/bus.ts:53`.

`useEditorCommands` sends camera input to `core.dispatch` and requests the camera render producer. It does not call the store: `src/app/useEditorCommands.ts:73`, `src/app/useEditorCommands.ts:80`.

On the next frame, the core drains and coalesces view commands, applies them to the camera authority, then advances the pose: `src/interaction/interactionCore.ts:119`, `src/interaction/interactionCore.ts:141`.

### The similarly named store path is different

`applyViewSceneOperation` accepts only projection, polarity, and projection toggle scene operations: `src/domain/cubeOperations.ts:251`, `src/domain/cubeOperations.ts:270`.

The scene command runner calls that store path only after `isViewLaneSceneOperation` accepts one of those scene operations: `src/interaction/commands/document.commands.ts:24`, `src/interaction/commands/document.commands.ts:35`.

That store action does create a durability checkpoint: `src/state/actions/authoredActions.ts:25`, `src/state/actions/authoredActions.ts:29`. Camera pose commands never enter it.

`historyCheckpoint` is called by undo and redo, not by camera input: `src/state/actions/documentActions.ts:46`, `src/state/actions/documentActions.ts:72`, `src/state/actions/documentActions.ts:115`.

**Answer:** a camera dolly produces no document operation. Its classification is `EditorCommand.kind === "view"`, which is distinct from a view lane scene operation. Therefore there is no debounce, idle gate, coalescing window, first move condition, or drain trigger that could make camera dolly occasionally reach `historyCheckpoint`. It never reaches it.

## What an actual checkpoint costs

PR 136 did not slim checkpoints. A checkpoint still selects aggregate projection, while a non bootstrap authored commit selects the exact pose revisions named by its operations: `src/state/projectCommitProjectionCore.ts:119`, `src/state/projectCommitProjectionCore.ts:136`.

An actual checkpoint projects both the before and after state: `src/state/projectCommitProjectionCore.ts:43`, `src/state/projectCommitProjectionCore.ts:64`.

Each projection:

- Walks the complete project asset roster and encodes each structure or animation: `src/persistence/projectRecordProjection.ts:73`, `src/persistence/projectRecordProjection.ts:97`.
- Collects pose revisions from the current Workbench, every past Workbench, and every future Workbench: `src/persistence/projectRecordProjection.ts:162`, `src/persistence/projectRecordProjection.ts:183`.
- Encodes and canonicalizes every encountered pose revision before deduplication: `src/persistence/poseRevisionRegistry.ts:23`, `src/persistence/poseRevisionRegistry.ts:37`, `src/persistence/poseRevisionRegistry.ts:45`, `src/persistence/poseRevisionRegistry.ts:59`.
- Compares the before and after asset rosters and serializes records for equality: `src/state/projectStorageChangeSet.ts:72`, `src/state/projectStorageChangeSet.ts:118`.

The history cap is 100 entries: `src/state/documentHistory.ts:45`, `src/state/documentHistory.ts:58`.

The aggregate work scales with asset count, the number of Workbenches across current plus past plus future history, states per Workbench, and encoded pose size. Pose encoding cost grows with the cells and other content in each pose. Checkpoint projection performs that work for both before and after state.

In Chromium, the aggregate projection and comparison run in a worker: `src/state/projectCommitProjection.ts:24`, `src/state/projectCommitProjection.ts:39`, `src/state/projectCommitProjectionWorker.ts:19`, `src/state/projectCommitProjectionWorker.ts:42`. Main thread request serialization is segmented and yields between 128 element cell segments, although its initial skeleton traversal remains synchronous: `src/shared/segmentedJson.ts:11`, `src/shared/segmentedJson.ts:23`, `src/shared/segmentedJson.ts:60`, `src/shared/segmentedJson.ts:74`.

This cost can explain an occasional overlap only when a real checkpoint from undo, redo, projection or polarity change, Workbench reset, or similar prior action remains active. It does not make camera stutter increase with history depth by itself.

## Re-ranked occasional suspects

### 1. Camera frame allocation churn and garbage collection

Every rendered camera frame:

- Resolves a pose and clones it into `latestPoseRef`: `src/camera/cameraFrameWriter.ts:68`, `src/camera/cameraFrameWriter.ts:69`.
- Creates a complete interaction snapshot twice: `src/camera/cameraFrameWriter.ts:71`, `src/camera/cameraFrameWriter.ts:109`.
- Each snapshot clones three `Vector3` values, creates three tuple arrays, and reads selection state: `src/camera/cameraAuthorityRuntime.ts:124`, `src/interaction/snapshot.ts:21`, `src/interaction/snapshot.ts:48`.
- An eased dolly sample allocates a new pose, at least five `Vector3` values, and two `Quaternion` values: `src/motion/cameraMotion.ts:35`, `src/motion/cameraMotion.ts:56`, `src/motion/cameraMotion.ts:73`, `src/motion/cameraMotion.ts:85`, `src/motion/cameraMotion.ts:125`, `src/motion/cameraMotion.ts:131`.
- Authority advance clones the sampled pose into current state and clones it again for the caller: `src/camera/cameraAuthorityRuntime.ts:183`, `src/camera/cameraAuthorityRuntime.ts:193`.

A conservative static count for an active eased dolly frame is at least 20 new `Vector3` objects, two `Quaternion` objects, six pose tuple arrays, and several pose, snapshot, and coalescing objects. Wheel dolly is instant, but still clones poses and builds the two complete snapshots.

**Why occasional:** allocation is continuous, while collection occurs only when heap thresholds and scheduling demand it. Other application allocation changes when that threshold is crossed.

**Causal status:** garbage collection is **UNVERIFIED**.

### 2. Prior durability work landing during camera movement

Authored edits, checkpoints, and user project state changes enqueue durability units and start the drain immediately: `src/state/projectDurability.ts:147`, `src/state/projectDurability.ts:169`, `src/state/projectDurability.ts:178`, `src/state/projectDurability.ts:184`.

There is no durability debounce or idle timer. Adjacent queued user project state units are replaced when neither is in flight: `src/state/projectDurability.ts:159`, `src/state/projectDurability.ts:166`.

The drain is serial. It can remain active across storage reads, worker projection, promotion, and queued units, then publish committed revisions and save state while the camera is moving: `src/state/projectDurability.ts:283`, `src/state/projectDurability.ts:350`.

**Why occasional:** a previous edit, undo, redo, projection or polarity change, panel layout change, or storage delay must still overlap the dolly. Later queued work can resume after an asynchronous storage boundary on an arbitrary camera frame.

**Scaling:** real checkpoints grow with history depth and pose size as described above. Authored commits after PR 136 normally project only operation named pose revisions. Bootstrap authored commits remain aggregate.

**Causal status:** overlap with the reported hitch is **UNVERIFIED**.

### 3. Uncached thumbnail rendering

Mounted State cards request the thumbnail capability: `src/studios/editor/ThumbnailCapabilitySlot.tsx:9`, `src/studios/editor/ThumbnailCapabilitySlot.tsx:18`.

The cache uses immutable pose reference identity. A cache miss renders all three axes concurrently: `src/thumbnail/thumbnailCache.ts:15`, `src/thumbnail/thumbnailCache.ts:39`, `src/thumbnail/thumbnailCache.ts:44`, `src/thumbnail/thumbnailCache.ts:52`.

Each render waits for an idle callback, forced after 300 ms: `src/thumbnail/deferredThumbnailBackend.ts:3`, `src/thumbnail/deferredThumbnailBackend.ts:44`.

**Why occasional:** work appears only when a State card mounts, a pose reference is new, the cache is cleared, or a prior render failed. The 300 ms timeout can force rendering during an interaction.

**Causal status:** overlap with the reported hitch is **UNVERIFIED**.

### 4. One time lazy camera and studio capability work

The first eased camera command dynamically imports the camera motion module: `src/camera/cameraMotionPort.ts:17`, `src/camera/cameraMotionPort.ts:43`. Pending motion keeps the camera render producer live until activation: `src/camera/cameraAuthorityRuntime.ts:577`, `src/camera/cameraAuthorityRuntime.ts:602`.

Wheel zoom is instant and takes the instant branch, so it does not request the lazy motion module: `src/camera/cameraWheelZoom.ts:26`, `src/camera/cameraWheelZoom.ts:31`, `src/camera/cameraAuthorityRuntime.ts:262`, `src/camera/cameraAuthorityRuntime.ts:269`.

After the first committed interactive frame, panel drag prefetches immediately and activates in an idle callback forced after 250 ms: `src/studios/editor/usePanelDragCapability.ts:115`, `src/studios/editor/usePanelDragCapability.ts:123`, `src/studios/editor/usePanelDragCapability.ts:140`, `src/studios/editor/usePanelDragCapability.ts:146`.

If the Motion dock is open, the first interactive commit prefetches and activates the Motion capability: `src/studios/editor/useMotionCapability.ts:50`, `src/studios/editor/useMotionCapability.ts:60`.

**Why occasional:** each branch runs on first use, first interactive commit, remount, or loader generation rather than every movement.

**Causal status:** plausible for a first movement or remount hitch, **UNVERIFIED** for recurring random hitches.

### 5. Unrelated observers and timers

The remaining observer and timer inventory is tied to panel sizing, virtualized panel lists, scrub gestures, transport playhead updates, panel drag click suppression, and recording URL cleanup. None subscribes to live camera pose.

**Why occasional:** a panel resize, list visibility change, scrub, playback update, or recording cleanup can coincide with camera rendering.

**Causal status:** lower probability and **UNVERIFIED**.

## Motion and cadence semantics

The 220 ms value is a named motion constant, `cameraControlMotionDurationMs`, in `src/motion/cameraMotionPolicy.ts:14`. Orbit aliases it at `src/motion/cameraMotionPolicy.ts:15`.

For an isolated keyboard orbit, translate, or zoom tap, the 220 ms motion is a tween from the current pose to a new target pose. The plan stores `from`, `to`, start time, path, and duration: `src/motion/cameraMotion.ts:19`, `src/motion/cameraMotion.ts:32`. It samples eased progress on each rendered frame: `src/motion/cameraMotion.ts:35`, `src/motion/cameraMotion.ts:44`.

Holdable translate and zoom commands run one tweened tap immediately, then promote after 320 ms to frame driven continuous velocity: `src/editor/useHeldCommandInput.ts:63`, `src/editor/useHeldCommandInput.ts:69`, `src/editor/commandHold.ts:15`, `src/editor/commandHold.ts:47`, `src/camera/cameraAuthorityRuntime.ts:204`, `src/camera/cameraAuthorityRuntime.ts:253`.

Orbit remains discrete. Each repeated key command creates another 220 ms detent motion.

The keyboard cadence is named configuration, not a number hardcoded in the handler:

- `editorCommandRepeatDelayMs = 320`: `src/config/cubicellConfig.ts:50`.
- `editorCommandRepeatIntervalMs = 240`: `src/config/cubicellConfig.ts:51`.
- The handler imports those constants: `src/editor/useHeldCommandInput.ts:12`, `src/editor/useHeldCommandInput.ts:16`.

The source establishes named surface feel constants. Product intent beyond that naming is not inferred.

## Discriminating questions for the owner

1. Does the rare hitch occur during wheel dolly, `+` or `-` keyboard dolly, or both? Wheel dolly is instant and excludes the 220 ms tween plus first camera motion import branch.
2. Can it happen after the save indicator has shown Saved for at least five seconds, with no edit, undo, redo, projection, polarity, or panel layout change immediately beforehand? A yes excludes overlap from queued durability work.
3. Can it happen with the Motion dock closed and no State thumbnails mounted? A yes excludes thumbnail rendering and Motion capability activation.

## Verification

- Verified `HEAD` and `main` contain `e866889451d83b12ee04b2b18d39ca8e6d7c9c00`.
- Verified PR 136 commit `c3c2d63` is an ancestor of `e866889`.
- Read only source trace through `git show e866889:<path>`.
- No tests run, browser driven, or runtime profile captured, per brief.
