# Scout: framing vs staged scene, seam design and semantics

Baseline: cubicell main @ 71098b4, clean. Read-only pass. Companion scout owns the mechanical call path; this report owns the boundary and the behaviour.

## Findings

### 1. Where the seam belongs

The framing port (`FramingPort`, `src/interaction/framing.ts`) is a pull contract: the interaction core calls it whenever it needs scene truth (`resolveCoreCommand` for reset and focus-toggle in `src/interaction/commands/view.commands.ts` via `registerViewCommands`, and `syncCameraZoomBounds` in `src/interaction/interactionCore.ts` on every frame that has an active view command or hold). The port implementation `readStoreFramingInputs` (`src/app/useEditorCommands.ts`) answers with `getWorkingScene(state.workbench)`. The staged scene is produced by `useStagedScene` (`src/transport/useStagedScene.ts`), consumed in `EditorCanvas` (`src/studios/editor/EditorStudio.tsx`) and handed to the renderer as `scene={staged.scene}` on `EditorRendererBinding`.

Candidate boundaries:

**(i) Push the staged scene into the store.** Rejected. The staged scene is already a pure derivation of store state: `resolveStageSource(workbench, { morphScrub, transport })` plus `sampleStageSource`, all inputs read from `useCubicellStore` (`selectAuthoredWorkbench`, `state.editor.morphScrub`, `state.editor.transport.timeMs`). Writing the derivation back into the store creates a second source of truth that can lag its own inputs, and it means store writes per transport tick during playback, fanning out to every subscriber. `PERFORMANCE.md` ("Move the high frequency staged scene subscription below the shell boundary") records the codebase deliberately keeping this churn narrow. Ownership reading: the store owns authored facts and session time; the stage is an interpretation of them. Interpretations do not belong in the store.

**(ii) App-owned ref feeding the existing port.** Recommended. `useEditorCommands` already owns exactly this pattern twice: `projectionRef` (`projectionRef.current = scene.projection`, assigned during render, read by the core's `projection` port) and `syncPortRef` (assigned each render, read by `ports.runSynchronous`). A `stagedSceneRef` is the third instance of an established house idiom: the app layer adapts the React render world to the imperative interaction core through render-refreshed refs. `EditorCanvas` already calls `useStagedScene`; it writes `stagedSceneRef.current = staged.scene` in render, identical in shape to the `projectionRef` assignment. `readStoreFramingInputs` reads the ref instead of `getWorkingScene`. Cost: one ref threaded from `useEditorCommands` through the model to `EditorCanvas`. Coupling: none new in dependency terms; the app layer already sits between transport and interaction (it composes both). A cold reader six months out sees a third ref next to two identical ones and a one-line comment; the idiom self-documents.

**(iii) Move framing input assembly to where the staged scene lives.** Rejected as stated. The interaction core is created in `useEditorCommands` (called from `useEditorAppModel`, above `EditorCanvas`) because `EditorRendererBinding`, `KeyboardShortcuts`, and `SelectionFocusDriver` all need `core`. Moving core creation below the canvas inverts the component ownership for one input. Hoisting `useStagedScene` up to the model instead would re-render the whole `EditorApp` shell per transport tick, which is precisely the churn `PERFORMANCE.md` says to keep below the shell boundary. Any workable version of (iii) degenerates into (ii).

**(iv) Derive the staged scene inside the port, statelessly.** The tempting pure option: `readStoreFramingInputs` calls `resolveStageSource` + `sampleStageSource` itself. Correct output (the plan cache in `useStagedScene` is a perf memo, not a semantic input), zero plumbing. Rejected on mechanics: `syncCameraZoomBounds` calls the port every frame during holds and caches zoom bounds by scene identity (`zoomBoundsScene === inputs.scene`). A per-call morph sample allocates a fresh scene object each call, so during a scrub or piece transition plus a camera hold, the identity check fails every frame and full zoom-bounds recomputation plus morph evaluation runs per frame. That is the exact allocation-churn class the last four perf PRs (#119, #120, #137, #139) removed. Smaller diff, wrong grain.

**Recommendation: (ii).** Ownership argument: the interaction core's contract is "give me the scene truth for camera decisions"; the app layer is the composition root that knows which scene is truth. The ref keeps derivation where it already lives (`useStagedScene`, whose doc comment calls itself "the sole adapter where session time meets authored Workbench state"), keeps the port contract (`FramingInputs`) unchanged, and preserves the zoom-bounds identity cache: in the authored case `sampleStageSource` returns `getWorkingScene(workbench)` by identity, so the cache behaves exactly as today outside playback.

### 2. The correct semantic

The right rule is not "authored unless transport owns the stage"; it is **"framing operates on the scene the renderer is drawing."** Operationally: the same `staged.scene` that `EditorCanvas` passes to `EditorRendererBinding`. During a comparison scrub at t=0.4 the renderer draws the blend sample produced by `sampleResolvedSceneTransition`, so "5" frames the blended geometry, which is exactly what the user sees. Framing either endpoint instead would visibly mis-fit the screen content, which is the bug being fixed, just at a different t.

One-sentence user-facing rule: **"Reset view fits the camera to what is on screen right now."**

This also makes zoom bounds correct for free: `computeZoomBounds` consumes the same `FramingInputs.scene`, so zoom limits follow the displayed geometry during playback instead of clamping to the authored structure. That is a semantic improvement, not a side effect to suppress.

### 3. Naming and vocabulary

**No new concept is needed.** "Staged scene" is already ubiquitous language: `StagedScene`, `useStagedScene`, `resolveStageSource`, `sampleStageSource`, `StageSourceKind` (`src/transport/useStagedScene.ts`), `gateStageMutationHandlers` (`src/app/stageInteraction.ts`), and `PERFORMANCE.md`'s "staged scene subscription". CAMERA.md, STORAGE.md, and STUDIO.PROJECT.md contain no competing use of "stage" (STUDIO.PROJECT.md's hits are unrelated; CAMERA.md's are "presets"). Do not coin "displayed scene" or "presented scene"; the fix is stated entirely in existing terms: *the framing port reads the staged scene*. The ref should be named `stagedSceneRef`.

### 4. Bug or feature change

**Bug, by omission.** The framing seam landed in `refactor(interaction): add framing seam (#5)`, e73d7c7, 2026-07-09. The staged-scene foundation landed in `feat(animation): establish scene morph and asset timeline foundation`, a3e6ff1, 2026-07-14, five days later. When `readStoreFramingInputs` was written, the working scene *was* the displayed scene; nothing was ever decided about framing during staging. No doc states that reset frames the authored scene (checked CAMERA.md, INTERACTIVE.md, STUDIO.PROJECT.md, STUDIO.ANIMATION.md, ARCHITECTURE.md for reset/frame language; none found). No doc amendment is required for correctness, though a one-line statement of the rule in CAMERA.md would be cheap insurance.

### 5. What reset means while playing

**Playback continues.** The camera authority is fully independent of transport: nothing in `createInteractionCore` (`src/interaction/interactionCore.ts`) reads or writes transport state, and dispatching a view command touches only the intent bus and `CameraAuthority`. Pressing "5" mid-play computes a one-shot `FocusViewTarget` from the staged scene at press time via `createGridFrameTarget` (`src/view/viewportFocus.ts`) and eases the camera there; the scene keeps animating underneath. Bounds drift during an ongoing morph is bounded by the two endpoint scenes, and the user can press "5" again. One-sentence rule: **"Reset view is a camera command; it never touches time."** Pausing on reset would couple camera to transport, a mode change adjacent to the explicitly out-of-scope auto-framing.

### 6. The simplicity test

Smallest thing that could possibly work: option (iv), a one-function change to `readStoreFramingInputs` deriving the stage from store state inline. It is genuinely smaller (no ref, no plumbing) and its output is correct. It is rejected for the per-frame identity churn and morph re-evaluation documented in Finding 1(iv); it is merely small, not correct under load.

Second candidate: special-case only the reset path (add a second scene field to `FramingInputs`, or a second port used only by `registerViewCommands`' reset resolve). Rejected: it widens the port contract to encode two scene truths, leaves zoom bounds semantically wrong during playback, and forces every future reader to ask "which scene does this consumer get?" One truth ("the scene the renderer draws") is both smaller conceptually and more correct than a reset-only patch.

The recommended fix is three small edits: create and initialize `stagedSceneRef` in `useEditorCommands` (seeded with the authored scene so pre-first-canvas-render dispatches behave as today), assign it in `EditorCanvas` beside the existing `useStagedScene` call, read it in `readStoreFramingInputs`. No contract, type, or registry changes.

### 7. What would make this fix wrong

Searched for cases where framing the displayed scene is the wrong answer:

- **Comparison scrub at t≈0**: "5" frames the saved state's geometry rather than the working scene. That is what is on screen; correct under the rule, even though the user is "in" the working scene conceptually. Self-correcting: releasing the scrub restores the authored stage and "5" reframes.
- **User treats "5" as "go home to my authored view" while previewing**: after the fix they get the display framed instead. But the old behaviour gave them a camera fitted to geometry that is not on screen, which is strictly worse; and the moment the stage returns to authored, the same key gives them the authored frame.
- **Momentarily empty staged scene** (piece sample gap): `createGridFrameTarget` returns null and `computeGridFrame` (`src/view/interactionFraming.ts`) already falls back to the current camera target and `"initial"` orientation. Handled today, unchanged.
- **Selection focus during a blend**: `computeSelectionFrame` receives the staged scene; if a selected cube id is absent from the blend sample, `createGridViewportFocus` returns null and focus-toggle rejects with "No focusable selection". Acceptable degradation, arguably more honest than framing an invisible cube.

Conclusion: no case found where "frame what you see" is the wrong user-facing answer. The rule holds without exceptions, which is itself evidence the semantic in Finding 2 is the right one.

## Reuse Map

- `projectionRef` and `syncPortRef` in `useEditorCommands` (`src/app/useEditorCommands.ts`): the exact render-refreshed-ref idiom the fix should copy; `stagedSceneRef` becomes its third instance.
- `useStagedScene` / `sampleStageSource` (`src/transport/useStagedScene.ts`): already produces the needed scene with plan-cache memoization; reuse its output, never re-derive.
- `sampleStageSource` authored path returns `getWorkingScene(workbench)` by identity, preserving the `zoomBoundsScene` identity cache in `syncCameraZoomBounds` (`src/interaction/interactionCore.ts`) outside playback.
- `computeGridFrame` fallback branch (`src/view/interactionFraming.ts`): existing null-target handling covers empty staged scenes; no new guard needed.
- `FramingInputs` (`src/interaction/framing.ts`): contract stays byte-identical; only the value flowing through `scene` changes meaning, and the doc comment there is the right place to state the rule.

## Quality Map

- `useEditorCommands` subscribes to the full working scene (`useCubicellStore((state) => getWorkingScene(state.workbench))`) only to seed `initialView` and refresh `projectionRef`; every scene edit re-renders the hook's host for a projection field. Pre-existing, out of scope, worth a later look.
- Initial camera (`createGridFramedCamera(scene, viewport)` in `useEditorCommands`) frames the authored scene at mount. If persistence ever restores a session mid-piece, the initial frame and the first displayed frame diverge. Pre-existing and marginal; the fix makes "5" the escape hatch.
- `FramingInputs.scene`'s doc comment should be updated to say "the staged scene (what the renderer draws)" so the port contract states the semantic instead of relying on wiring.

## Plan

1. `src/app/useEditorCommands.ts`: add `stagedSceneRef = useRef<CubicellScene>(scene)` beside `projectionRef`; change `readStoreFramingInputs` to take the ref (or close over it) and supply `scene: stagedSceneRef.current`; return the ref from the hook.
2. `src/studios/editor/EditorStudio.tsx` (`EditorCanvas`): after `const staged = useStagedScene()`, assign `model.stagedSceneRef.current = staged.scene` in render, mirroring the `projectionRef` idiom.
3. `src/interaction/framing.ts`: one-line doc comment on `FramingInputs.scene` stating the rule: framing operates on the staged scene, the scene the renderer draws.
4. Unit test: construct a store state with an active `morphScrub`, run `resolveStageSource`/`sampleStageSource` to get the staged scene, wire a core with the ref-fed port, dispatch reset, assert `computeGridFrame` received the staged scene and not `getWorkingScene`. Companion assertion: authored case passes the working scene by identity (zoom-bounds cache guard).
5. Optional, cheap: one line in CAMERA.md stating "Reset view fits the camera to what is on screen; it never touches time."

Explicitly out of scope, per brief: automatic camera framing during playback; no extension points added for it.
