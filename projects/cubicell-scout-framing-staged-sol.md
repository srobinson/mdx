# Cubicell staged scene framing scout

Baseline verified: clean `main` at `71098b4ee21117d8431e71288edef42f61908854`. All source evidence below is from that commit.

## Findings

### 1. Complete key to camera path

1. `src/editor/keyboard/KeyboardShortcuts.tsx:KeyboardShortcuts` installs the document capture listener. Its `handleKeyDown` calls `getKeyboardShortcut` and then `useKeyboardCommandInput.start`.
2. `src/editor/keyboard/keymap.ts:keyboardCommandIds`, `src/editor/keyboard/keymap.ts:keyboardCommandIdsByCode`, and `src/editor/keyboard/keymap.ts:getKeyboardShortcutCommandId` map both `5` and `Numpad5` to `editorCommandIds.viewReset`. `src/editor/keyboard/keymap.ts:getKeyboardShortcut` resolves that ID through `getEditorCommandDefinition`.
3. `src/editor/affordances.ts:editorCommandDefinitions` supplies `createEditorViewCommand(resetViewCommand)`. `src/editor/commands.ts:resetViewCommand` is a reset with a null target.
4. `src/editor/useHeldCommandInput.ts:useHeldCommandInput` dispatches this nonrepeatable command once through `onCommand`. `src/studios/editor/EditorStudio.tsx:EditorApp` supplies `runEditorCommand` from `useEditorCommands`.
5. `src/app/useEditorCommands.ts:dispatchEditorCommand` calls `core.dispatch` and requests the camera render producer after acceptance.
6. `src/interaction/interactionCore.ts:createInteractionCore.dispatch` calls `dispatchCoreCommand`, then `resolveCoreCommand`, then `src/interaction/commands/registry.ts:invokeResolve`.
7. `src/interaction/commands/view.commands.ts:registerViewCommands` owns reset enrichment. It clears active selection focus, calls `core.framing()`, passes the result to `computeGridFrame`, and wraps the returned target with `createResetViewCommand`.
8. `src/view/interactionFraming.ts:computeGridFrame` calls `src/view/viewportFocus.ts:createGridFrameTarget`, which uses `createViewportFocusGeometry` and `toGridFrameTarget` to produce the center, orientation, and zoom.
9. `src/interaction/bus.ts:createIntentBus.dispatch` queues the enriched absolute view command in the view frame lane.
10. `src/camera/cameraFrameWriter.ts:useSingleCameraWriterFrame` runs on the next renderer frame and calls `core.resolveFrameInto`.
11. `src/interaction/interactionCore.ts:createInteractionCore.resolveCoreFrame` drains the view lane, calls `coalesceViewCommandsInto`, synchronizes zoom bounds, and calls the camera authority.
12. `src/camera/cameraAuthorityRuntime.ts:applyCameraAuthorityView` calls `applyCoalescedView`. `src/interaction/viewReducer.ts:reduceViewPose` applies the reset target through `focusViewPose`, and `requestCameraMotion` starts the eased landing.
13. `src/camera/cameraAuthorityRuntime.ts:advanceCameraAuthority` samples that landing on each requested frame.
14. `src/camera/cameraFrameWriter.ts:useSingleCameraWriterFrame` passes the sampled pose to `src/camera/cameraDriverMath.ts:composeCameraWrite`, which writes the Three camera and controls target. That is the visible camera pose.

The framing port is installed once inside the lazy core initializer in `src/app/useEditorCommands.ts:useEditorCommands`. `src/interaction/interactionCore.ts:createInteractionCore` stores it in `createCoreFramingState` and exposes the same function through `CommandResolveContext`.

The port result is live, not memoized. `readStoreFramingInputs(store.getState())` constructs a fresh value whenever the port is invoked.

Read timing is precise:

* Reset and focus toggle read it at command dispatch time in `src/interaction/commands/view.commands.ts:registerViewCommands`.
* Zoom bound synchronization reads it from `src/interaction/interactionCore.ts:syncCameraZoomBounds` when the viewport changes, when a frame contains a view command or active hold, and before a camera track pose is applied.
* Passive camera motion frames only advance the authority. They do not read framing inputs again.
* Zoom bounds are cached by authored scene identity and viewport after the port read.

### 2. Complete framing consumer inventory

The production consumers are complete:

| Consumer | Current use | Decision |
| --- | --- | --- |
| `src/view/interactionFraming.ts:computeGridFrame` through reset resolution | Frames `inputs.scene` | Switch only this computation to the displayed scene. Reset means frame all visible content. |
| `src/view/interactionFraming.ts:computeSelectionFrame` through focus toggle | Locates the current authored selection in `inputs.scene` | Keep the authored scene for this slice. Selection IDs, selection sets, and focus mode belong to the authored workbench. A staged transition can omit or interpolate those IDs while interaction is disabled. |
| `src/view/interactionFraming.ts:computeGridZoomBounds` through `syncCameraZoomBounds` | Derives navigation limits from `inputs.scene` | Keep the authored scene. Staged morph samples can have a fresh identity and changing extents on every sample. Using them would move zoom clamps during active holds, view commands, or camera track writes. |
| `src/app/SelectionFocusDriver.ts:SelectionFocusDriver` | Calls `computeSelectionFrame` directly with `focusInputsRef` | Keep its authored scene. It owns authored selection focus behavior and does not consume the central framing port. |

`src/interaction/interactionCore.ts:createCoreFramingState`, `src/interaction/interactionCore.ts:CommandResolveContext`, and `src/interaction/commands/registry.ts:CommandResolveContext` carry the port and compute functions. They do not inspect scene fields.

`src/view/viewportFocus.ts:createGridFramedCamera` is adjacent but outside the port. It creates the initial camera from the authored scene before the child canvas has produced a staged scene. It should remain unchanged.

Pointing the existing `FramingInputs.scene` field at the staged scene would also redirect `computeGridZoomBounds`. During a morph, the scene object and geometry can change on every sampled frame. `syncCameraZoomBounds` would then recalculate limits whenever camera activity invokes it. The resulting min or max changes can clamp zoom or dolly motion differently across frames, producing jumps or breathing. The correct split is displayed scene for frame all, authored scene for navigation limits.

One additional interaction matters. `src/interaction/viewReducer.ts:reduceViewPose` sends reset targets through `focusViewPose`, which clamps the requested zoom to the camera authority's current bounds. A displayed scene can require a wider frame than the authored scene, so authored bounds alone can clip the displayed reset target. The reset application must widen the current authority bounds once to include the trusted target zoom. That widening should persist until the normal authored scene or viewport invalidation replaces the bounds. This preserves the exact displayed landing without deriving live bounds from every morph sample.

### 3. Staged scene ownership

`src/transport/useStagedScene.ts:useStagedScene` owns a render local derived value:

* `selectAuthoredWorkbench`, `editor.morphScrub`, and `editor.transport.timeMs` are store subscriptions.
* `resolveStageSource` is memoized over those inputs.
* `sampleStageSource` is memoized over the resolved source and workbench.
* `createActiveTransitionPlanCache` is a hook local cache retained for that mounted hook.

The resulting `StagedScene` has no store field and no dedicated React state. It is recomputed for the relevant render and returned by the hook.

`src/studios/editor/EditorStudio.tsx:EditorCanvas` is the sole caller. It passes `staged.scene` and `staged.moment` to `EditorRendererBinding`. `useEditorAppModel` creates `useEditorCommands` in the parent component, so the persistent framing port currently cannot see the child render value.

For the port to see the displayed scene while preserving the current render boundary, `EditorCanvas` must publish its latest committed `staged.scene` through a stable ref owned by `useEditorCommands`, or through an equivalent narrow registration callback. A layout effect can align the ref write with the React commit and prevent an abandoned render from becoming observable to the global keyboard listener. `readStoreFramingInputs` can then combine the live authored store snapshot with that displayed scene ref.

### 4. Existing ref fed precedents

* `src/app/SelectionFocusDriver.ts:focusInputsRef` receives the latest render inputs and is read later by the focus effect. This is the closest value carrier pattern for a displayed scene.
* `src/app/useEditorCommands.ts:projectionRef` lets the persistent interaction core read the latest projection through a stable port. This is directly reusable.
* `src/app/useEditorCommands.ts:syncPortRef` lets the persistent core call the latest synchronous dispatcher without recreating the core. This confirms the same lifetime pattern for a function value.
* `src/studios/editor/useRecordingCapability.ts:canvasRef` is read through a function captured when the capability is created and updated when the canvas registers. This is a usable child to long lived owner registration precedent.

A displayed scene ref follows established ownership. It avoids a new store field, a second stage sampler, and core reconstruction.

### 5. Exact displayed scene predicate

`src/transport/useStagedScene.ts:resolveStageSource` already resolves every case:

* Transport playing: `editor.transport.playing` is true and `withTransportPlaying` ensures `editor.transport.timeMs` is attached. `resolveAttachedPieceSource` uses the nonnull time and attached Structure to return `kind: "piece"`.
* Transport paused mid timeline: `editor.transport.playing` is false while `editor.transport.timeMs` remains nonnull. The same piece source remains displayed.
* Transport seek: `setTransportTime(number)` writes a nonnull `editor.transport.timeMs` and clears `editor.morphScrub`. Playing may remain true or false.
* Comparison scrub: a valid `editor.morphScrub` takes precedence and returns `kind: "comparison"`. `setMorphScrub` stops and detaches transport while the comparison is active.
* Exact State, held cut, and single State playback: these are still `kind: "piece"` whenever `editor.transport.timeMs` is nonnull. The sampled scene can be a static State rather than a transition.
* Detached or unavailable piece: `editor.transport.timeMs === null`, no attached Structure, or a failed piece sample resolves to the authored fallback.

The single existing condition is `staged.source !== "authored"`. It covers playing, paused, seek, static piece, transition, and comparison sources. `playing`, `interactive`, and `moment` each miss valid cases.

The implementation should consume `staged.scene` unconditionally. `sampleStageSource` already returns the authored scene and `source: "authored"` for fallback cases, so another flag or duplicated predicate adds no value.

### 6. Smallest correct change

#### Shape A, recommended: ref fed displayed scene

* `src/interaction/framing.ts:FramingInputs`, about 2 lines: add a clearly named `displayedScene` field while retaining `scene` as the authored scene.
* `src/view/interactionFraming.ts:computeGridFrame`, 1 line: pass `inputs.displayedScene` to `createGridFrameTarget`. Leave `computeSelectionFrame` and `computeGridZoomBounds` on `inputs.scene`.
* `src/app/useEditorCommands.ts:useEditorCommands`, about 7 lines: own a displayed scene ref initialized from the authored scene, expose a stable registration callback, and include the ref value in `readStoreFramingInputs`.
* `src/studios/editor/EditorStudio.tsx:EditorCanvas`, about 6 lines: publish `staged.scene` through that callback in a layout effect so the port tracks the committed render.
* `src/camera/cameraAuthorityRuntime.ts:applyCoalescedView`, about 8 lines: when an absolute reset has a target, widen the retained zoom bounds only enough to include that target before `reduceViewPose` applies it. Later authored scene or viewport invalidation restores the ordinary computed bounds.
* Test support and tests, about 35 lines: add the default field and the focused regressions below.

Estimated production delta: about 24 lines across five existing files. No new store state, renderer contract, or stage sampling path is required.

#### Shape B: lift `useStagedScene` into `EditorApp`

Move the hook above `useEditorAppModel`, pass `staged` down to `EditorCanvas`, and pass `staged.scene` into `useEditorCommands`.

This has superficially direct data flow, but it expands the transport time subscription from the canvas boundary to `EditorApp`. Every published playback time can then rerender shell, panels, capabilities, and command model ownership. The current source places `useStagedScene` in `EditorCanvas` to keep that hot subscription narrow. Reject Shape B.

Also rejected:

* Recomputing `resolveStageSource` and `sampleStageSource` inside the framing port. This duplicates sampling work, bypasses the hook cache, and can observe a store time that has not produced the displayed render.
* Replacing authored `FramingInputs.scene` globally. This destabilizes zoom bounds and changes selection focus semantics.
* Adding a second full framing service or future playback camera extension point. The requested reset behavior needs neither.

### 7. Risks and required behavior

* Ref timing: the persistent core must read the latest committed canvas render value. Update the ref from an `EditorCanvas` layout effect whenever `staged.scene` changes. A stable ref avoids stale closure capture, and commit aligned publication avoids exposing abandoned renders. A test must change the registered scene after core construction and prove the next reset uses it.
* Zoom bounds: retain authored `scene` as the cache key and input to `computeGridZoomBounds`. The displayed scene needs a separate field. Widen the authority's retained bounds once when a displayed reset target lies outside them, so `focusViewPose` cannot clip the landing.
* Focus and selection: retain authored scene use in `computeSelectionFrame` and `SelectionFocusDriver`. Reset continues to call `clearFocus` before framing.
* Playback: reset should leave `editor.transport.playing`, `editor.transport.timeMs`, and `editor.morphScrub` unchanged. The camera frames the visible sample at command time while playback continues.
* Moving target: the reset target is computed once at command dispatch and then eased. Continued playback can move the scene during the landing. Automatic tracking is outside scope.
* Projection: preserve the existing projection port and staged `projectionBehavior`. This slice changes only scene geometry used to calculate the reset target.

### 8. Unit tests

No browser test or repro harness is needed.

1. `tests/interaction.framing.test.ts`, add `test("frames the displayed scene while authored framing policies stay stable")`.
   * Use geometrically distinct authored and displayed scenes.
   * Assert `computeGridFrame` equals `createGridFrameTarget(displayedScene, ...)`.
   * In the same test, assert `computeGridZoomBounds` equals authored bounds and `computeSelectionFrame` uses the authored selection geometry.
   * The current implementation fails the grid assertion because it reads `inputs.scene`. The combined assertions also reject the naive global scene swap.

2. `tests/interaction.core.test.ts`, add `test("reset reads the latest displayed scene at command time")`.
   * Construct the core once with a mutable framing port.
   * Change only `displayedScene`, dispatch reset, resolve the frame instantly, and assert the final target and zoom match that displayed scene.
   * Make the displayed scene large enough that its frame zoom falls outside authored bounds, then assert the reset still lands at the requested zoom and a following small zoom command remains continuous.
   * Change it again and repeat to prove the port is live rather than captured during core creation.
   * The current implementation frames the unchanged authored scene and fails the first target assertion. A partial implementation that keeps authored clamping fails the zoom assertion.

3. `tests/keyboard.test.ts`, add `test("5 frames the scene registered by the canvas")`.
   * Extend the existing `EditorCommandHarness` to expose the core and register a distinct displayed scene through the new callback.
   * Dispatch a `keydown` for `5`, resolve the accepted view frame instantly, and assert the pose matches `computeGridFrame` for the registered displayed scene.
   * The current `readStoreFramingInputs` can only return `getWorkingScene(state.workbench)`, so the pose matches authored geometry and the test fails.

Existing coverage remains useful:

* `tests/stagedScene.test.ts:describe stage source resolution` already proves authored, piece, transition, static State, comparison, precedence, and fallback sampling.
* `tests/interaction.core.test.ts:test refreshes zoom bounds after scene and viewport changes` guards authored zoom bound refresh behavior.
* `tests/keyboard.test.ts:test keydown never promotes a nonrepeatable reset command to a hold` guards the one shot input contract.

## Reuse Map

| Need | Reuse |
| --- | --- |
| Determine what is displayed | `src/transport/useStagedScene.ts:resolveStageSource`, `sampleStageSource`, and `StagedScene.scene` |
| Carry a child render value to a persistent owner | `src/app/SelectionFocusDriver.ts:focusInputsRef`, `src/app/useEditorCommands.ts:projectionRef`, and `src/studios/editor/useRecordingCapability.ts:canvasRef` |
| Compute reset framing | `src/view/interactionFraming.ts:computeGridFrame` and `src/view/viewportFocus.ts:createGridFrameTarget` |
| Preserve authored navigation policy | `src/view/interactionFraming.ts:computeGridZoomBounds` and `src/interaction/interactionCore.ts:syncCameraZoomBounds` |
| Test injected framing | `tests/interactionCoreTestSupport.ts:createTestFramingInputs` and `createTestFramingPort` |

No new stage predicate, framing math, store field, or camera command is warranted.

## Quality Map

| Quality | Proof obligation |
| --- | --- |
| Correctness | Key `5` lands on the frame target calculated from the latest displayed scene. |
| Stability | Zoom bounds and selection focus continue using authored geometry. |
| Reset range | A displayed target outside authored bounds lands exactly, while the widened bound remains stable until normal invalidation. |
| Timing | A scene registered after core construction is visible to the next command dispatch. |
| Performance | `useStagedScene` stays at the `EditorCanvas` boundary, preserving the narrow playback subscription. |
| Scope | Playback state remains unchanged; automatic tracking and browser work remain absent. |
| DRY | Existing stage resolution, ref fed port patterns, framing math, and test helpers are reused. |
| File limits | Every touched production and test file remains below 700 lines with the estimated delta. |

## Plan

1. Add `displayedScene` to `FramingInputs` and its shared test fixture.
2. Route only `computeGridFrame` to `displayedScene`.
3. Add the stable displayed scene ref and registration callback to `useEditorCommands`.
4. Register `staged.scene` from an `EditorCanvas` layout effect without moving `useStagedScene`.
5. Widen retained camera authority bounds once when a reset target falls outside them.
6. Add the three unit regressions above.
7. Run only the named unit test files during implementation, then run the repository required gates permitted by the implementation brief.
