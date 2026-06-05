# Reset View Zoom Fit Regression

Baseline verified: clean `main` at `346766193bb565950cf5b09cf93a8cfaaf4d53e7`.

## First Differing Value

There is no differing framing value between `69326ac` and `3467661` for the authored state.

I ran the same instrumented unit harness in detached worktrees at both commits. The fixture was a 250 cell `25 × 10 × 1` perspective scene in a fixed `1000 × 800` viewport, with editor mode `edit`, viewport mode `grid`, null selection, and no playback or morph scrub.

| Pipeline value | `69326ac` | `3467661` |
|---|---:|---:|
| Framing scene cell count | 250 | 250 |
| Framing scene projection | `perspective` | `perspective` |
| Framing scene is working scene by identity | `true` | `true` |
| Viewport | `1000 × 800` | `1000 × 800` |
| Bounds min | `[-18.5, -7.25, -0.5]` | `[-18.5, -7.25, -0.5]` |
| Bounds max | `[18.5, 7.25, 0.5]` | `[18.5, 7.25, 0.5]` |
| Focus center | `[0, 0, 0]` | `[0, 0, 0]` |
| Focus radius | `26.832841933906295` | `26.832841933906295` |
| Frame orientation | `initial` | `initial` |
| Frame zoom | `16.594672360142344` | `16.594672360142344` |
| Zoom minimum | `10.062296072292842` | `10.062296072292842` |
| Zoom maximum | `3431.211072815294` | `3431.211072815294` |
| Clamp cause | `none` | `none` |
| Clamped zoom | `16.594672360142344` | `16.594672360142344` |
| Final pose position | `[0, 0, 51.69145552184108]` | `[0, 0, 51.69145552184108]` |
| Final pose target | `[0, 0, 0]` | `[0, 0, 0]` |
| Final pose zoom | `16.594672360142344` | `16.594672360142344` |

The first implementation difference is the scene acquisition path in `src/app/useEditorCommands.ts:useEditorCommands`. Before #145 it read `getWorkingScene(state.workbench)`. After #145 it reads `createStagedSceneReader(selectStagedSceneSources(state))`. In the authored state this produces the same scene object by identity, so the difference does not propagate into any framing value.

The ranked hypotheses resolve as follows:

| Hypothesis | Result |
|---|---|
| A. Zoom clamping | Refuted. The target zoom is between both bounds and survives unchanged. |
| B. Projection mismatch | Refuted in authored state. Both paths frame and render `perspective`. |
| C. Viewport size | Refuted for the differential. Both use `1000 × 800`; #145 did not change `src/camera/CameraDriver.tsx:CameraDriver` or `src/interaction/interactionCore.ts:setViewportSize`. |
| D. Editor mode | Refuted. Both inputs are `edit`, so both use the workbench frame option. |
| E. Publish ordering | Refuted for the new implementation. `src/transport/stagedScene.ts:createStagedSceneReader` synchronously derives its first answer from current sources and has no empty seed. |

## Root Cause

Reset view discards the robust perspective fit distance.

`src/view/viewportFocus.ts:createGridFramedCamera` computes two parts of a robust frame:

1. Canonical zoom from the current scene bounds and viewport.
2. A perspective camera distance that places the camera beyond the scene depth.

The session uses that complete result only for its initial camera. The key `5` path takes a narrower route:

1. `src/interaction/commands/view.commands.ts:registerViewCommands` calls `computeGridFrame`.
2. `src/view/interactionFraming.ts:computeGridFrame` returns a `FocusViewTarget`.
3. `src/pose/focusView.ts:FocusViewTarget` carries center, orientation, and zoom. It has no position or distance.
4. `src/editor/commands.ts:createResetViewCommand` preserves only those three values.
5. `src/interaction/viewReducer.ts:reduceViewPose` calls `focusViewPose`.
6. `src/pose/viewPose.ts:focusViewPose` places the new target under `getInitialCameraOffset(initialCamera)`.

If the authored scene has grown since the session captured `initialCamera`, reset applies the current fit zoom at the old camera distance. A deep perspective scene can surround or pass behind that camera.

This became visible at `b4a4487` (`fix(camera): preserve center orbit during perspective dolly`). Before that commit, `src/pose/viewPose.ts:applyViewPoseToCamera` ignored the pose distance for perspective rendering and derived render distance from canonical zoom. The latent reset target omission was masked. Since `b4a4487`, position is spatial truth, so a reset must supply the fitted position as well as the fitted zoom.

PR #145 did not introduce this mechanism. Both `69326ac` and `3467661` reproduce it with identical numbers.

## Reproduction

The authored state reproduces the bug without playback or scrub.

The reproducer models a normal editing session:

1. Start with a `1 × 1 × 1` perspective scene in a `1000 × 800` viewport.
2. Retain the initial camera, as `useEditorCommands` does.
3. Grow the authored scene to `5 × 5 × 10`, totaling 250 cells.
4. Run the key `5` pipeline against the current authored scene.
5. Apply the resulting pose to a real Three `PerspectiveCamera`.

The exact results are identical at `69326ac` and `3467661`:

| Measurement | Current reset | Robust current scene frame |
|---|---:|---:|
| Current scene bounds Z | `[-7.25, 7.25]` | `[-7.25, 7.25]` |
| Target canonical zoom | `44.3169504281644` | `44.3169504281644` |
| Zoom bounds | `[22.782870872446956, 3431.211072815294]` | Same |
| Pose distance | `4.289013841019117` | `19.356087454489444` |
| Render camera Z | `4.289013841019117` | `19.35608745448944` |
| Bounds corners behind camera | `4 of 8` | `0 of 8` |
| Maximum visible NDC X | `0.4493543789157836` | `0.49600000000000016` |
| Maximum visible NDC Y | `0.5616929736447296` | `0.6200000000000002` |

The reset camera is inside the scene because its Z position is `4.289`, while scene geometry reaches Z `7.25`. This produces the reported close, overflowing perspective view even though the zoom target and clamp are correct.

The same authored growth harness at `b31bce7`, immediately before `b4a4487`, renders at Z `19.356087454489444` and leaves zero corners behind the camera. Its pose still contains the old five unit distance, but the previous renderer derives the safe render distance from zoom. This confirms the behavioral transition.

`src/transport/stagedScene.ts:sampleStageSource` still preserves authored identity. Its authored branch returns `scene: source.scene`, and `src/transport/stagedScene.ts:resolveStageSource` obtains that object from `getWorkingScene(workbench)`. The post #145 harness reports:

- Source: `authored`
- Moment: `null`
- Interactive: `true`
- Projection behavior: `animated`
- `staged.scene === getWorkingScene(workbench)`: `true`

Playback and comparison staging are unnecessary for reproduction. They can expose the same distance defect when staged depth exceeds the retained initial distance.

## Proposed Fix

Make grid reset carry the complete pose already computed by `createGridFramedCamera`.

The clean boundary is:

1. Change `src/interaction/framing.ts:ComputeGridFrame` to return a complete camera pose snapshot.
2. Change `src/view/interactionFraming.ts:computeGridFrame` to call `createGridFramedCamera(inputs.scene, viewport, { workbench })`, then return its position, target, up, and zoom. Use the supplied fallback camera for an empty scene.
3. Change the reset target in `src/editor/commands.ts:ViewCommand` and `createResetViewCommand` from `FocusViewTarget` to `CameraPoseSnapshot`. Reuse the existing `clonePoseSnapshot`.
4. Change the reset branch in `src/interaction/viewReducer.ts:reduceViewPose` to use `restoreViewPose` for a resolved target. The authority still owns eased motion, so reset remains animated.
5. Leave selection focus on `FocusViewTarget`. Focus intentionally preserves the current orbit distance; Frame All requires a complete fitted pose.

This removes the parallel partial frame path and reuses the existing robust owner. It also preserves #145:

- `src/app/useEditorCommands.ts:readFramingInputs` continues to supply `readStaged().scene`.
- Projection continues to come from the same staged read.
- `createGridFramedCamera` receives that staged scene and computes both its zoom and its safe distance.
- Authored, playback, and scrub framing continue to follow what is staged.

Do not change zoom bounds, increase margins, clamp the camera farther out, or revert staged scene framing. Those changes would treat a valid zoom as defective and leave the missing distance contract unresolved.

## Guard Test

Add a unit regression in `tests/interaction.core.test.ts` beside `test reset resolves the grid frame headlessly without a synchronous trampoline`.

The test should:

1. Create a `1 × 1 × 1` perspective initial scene and its `createGridFramedCamera` result.
2. Create a `5 × 5 × 10` perspective current scene with 250 cells.
3. Construct the interaction core with the small scene camera as `initialCamera` and the deep current scene in the framing port.
4. Set viewport size to `1000 × 800`.
5. Dispatch `createResetViewCommand(null)` and resolve the frame instantly.
6. Compare the resulting position, target, up, zoom, and pose distance with `createGridFramedCamera(currentScene, viewport)`.
7. Apply the pose to a Three `PerspectiveCamera` and assert all eight current bounds corners are in front of the camera and inside NDC.

Required red evidence on `3467661`:

- Actual pose distance: `4.289013841019117`
- Expected pose distance: `19.356087454489444`
- Actual bounds corners behind camera: `4`
- Expected bounds corners behind camera: `0`

Keep the existing staged framing tests. Add one authored identity assertion through `createStagedSceneReader` if the fix changes the framing return type. No browser test is needed for this deterministic pose contract.

Verification performed for this report:

- Detached worktree harness at `69326ac`: two tests passed.
- Detached worktree harness at `3467661`: two tests passed.
- Historical behavior harness at `b31bce7`: two tests passed.
- Source diff confirmed no #145 change in `CameraDriver`, `interactionCore`, or `viewPose`.
- No browser, development server, or preview server was started.
