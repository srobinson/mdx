# Cubicell Interaction-Model Remodel — Design Spec (DRAFT)

Mode 2 spec, 2026-07-08. Repo `cubicell`. Domain doc: `INTERACTIVE.md`. Scope:
FULL (Gap 1 + Gap 2). This is a draft for Stuart's review before any remodel
code. Symbols only, no line numbers.

> **Base note.** The brief named `main = 71fb3f3`. During this read-only pass the
> working tree advanced to `interaction/driver-hygiene @ 2699203` = `71fb3f3` +
> one commit, *"refactor: split camera driver runtime"*. That commit only split
> the driver adapter internals: `cameraDriverRuntime.ts` is **deleted**, its
> single writer `useSingleCameraWriterFrame` now lives in `cameraFrameWriter.ts`,
> and the pieces spread across `cameraCaptureRegistration.ts`, `cameraPanGesture.ts`,
> `cameraProjectionSwap.ts`, `cameraTrackball.ts`, `cameraDriverDom.ts`. **Every
> core-model file this remodel rewrites is unchanged** by the split (verified via
> `git diff --name-only 71fb3f3 HEAD`). This spec cites the post-split homes. The
> split also resolves opus #7 (see §5).

---

## 1. Required inputs (re-read before implementing)

- `INTERACTIVE.md` — the domain contract; six invariants; the two lanes; P as
  the "well modeled" yardstick.
- Scout reports: `~/.mdx/projects/cubicell-scout-model-opus.md` (9 findings,
  worst = focus toggle) and `~/.mdx/projects/cubicell-scout-model-codex.md`
  (adds wheel-zoom, mode-cycle, repeatability findings).
- Live code cited below (all read for this spec): `src/interaction/command.ts`,
  `viewLane.ts`, `bus.ts`, `interactionCore.ts`, `authority.ts`,
  `cameraAuthorityRuntime.ts`, `snapshot.ts`, `cameraWheelZoom.ts`,
  `cameraGestureRuntime.ts`, `CameraDriver.tsx`; `src/view/viewState.ts`,
  `viewPose.ts`, `viewportFocus.ts`, `selectionFocus.ts`;
  `src/editor/commands.ts`, `commandRegistry.ts`; `src/app/useEditorCommands.ts`,
  `useSynchronousEditorCommands.ts`, `useSelectionFocusCommands.ts`,
  `App.tsx`; `src/panels/SceneSection.tsx`; `src/state/cubicellStore.ts`,
  `cubicellState.ts`.
- Test tooling: `vitest run` (`npm test`), suites in `tests/*.test.ts(x)` with a
  per-module convention (`interaction.core.test.ts`, `interaction.command.test.ts`,
  `interaction.viewLane.test.ts`, `interaction.authority.test.ts`,
  `interaction.snapshot.test.ts`, `view.test.ts`, `state.test.ts`,
  `keyboard.test.ts`, `panels.test.tsx`). Gates: `npm test`, `tsc -b`, `oxlint`.

## 2. Decisions already made (do not relitigate)

- **Focus, approach (a).** Resolve the toggle to a **declarative framing intent
  BEFORE the coalescing lane**. Focus OFF → emit frame-to-target; focus ON →
  emit restore-to-saved-pose; **save the restore pose at decision time**. The
  view lane then carries only idempotent framings, so last-wins stays correct.
  Focus is a **single source of truth in the CORE**; the store flag is
  **derived** from the core snapshot, never an independent truth.
- **P is the yardstick.** One store truth, a dedicated axis, observed by the
  driver, never coalesced. The remodeled entities must be P-shaped.

## 3. Reuse Map (existing owner per capability)

Zero-tolerance DRY: every capability below already has an owner and is reused;
only the genuinely new seams are marked NEW.

| Capability | Existing owner (file · symbol) | Action |
|---|---|---|
| Selection framing math | `view/viewportFocus.ts · createGridViewportFocus`; `view/selectionFocus.ts · createViewportFocusSelection`, `hasSelectionTarget` | Reuse from the core (relocate the *call site*, not the math). |
| Grid / reset framing | `view/viewportFocus.ts · createGridFrameTarget`, `toGridFrameTarget` | Reuse from the core. |
| Bootstrap camera + fallback offset | `view/viewportFocus.ts · createGridFramedCamera`; `view/viewPose.ts · getInitialCameraOffset` | Reuse for the reset no-cells fallback (same shape as today's `createResetTarget` fallback). |
| Pose reducer | `view/viewPose.ts · reduceViewPose` | Reuse; add a `restore` case, delete the `toggle-focus` case. |
| Focus pose framing | `view/viewPose.ts · focusViewPose` (private, via `reduceViewPose`) | Reuse unchanged. |
| Motion durations | `motion/cameraMotion.ts · cameraFocusMotionDurationMs`, `cameraResetMotionDurationMs` | Reuse; retarget the `toggle-focus` duration case to `restore`. |
| Per-frame coalescing | `interaction/viewLane.ts · coalesceViewCommands`, `combineViewCommand` | Reuse unchanged (now sees only idempotent absolutes + additive). |
| Single writer | `interaction/cameraFrameWriter.ts · useSingleCameraWriterFrame`; `cameraDriverMath.ts · composeCameraWrite` | Reuse; wheel zoom joins it instead of writing the camera itself. |
| Zoom command | `editor/commands.ts · createZoomViewCommand` | Reuse for the wheel path. |
| Wheel factor (adapter feel) | `interaction/cameraWheelZoom.ts · getWheelZoomFactor` | Reuse (keep); delete the direct-write wrapper around it. |
| Pick-mode cycle order | `editor/commands.ts · getNextPickMode` | Reuse inside a new store `cyclePickMode`. |
| Pick-mode selection conversion | `state/cubicellStore.ts · setPickMode` body (`convertSelectionToPickMode`) | Extract shared helper; reuse in `cyclePickMode`. |
| Build-mode placement clearing | `state/cubicellStore.ts · setBuildModeActive` body | Extract shared helper; reuse in `toggleBuildMode`. |
| Snapshot serialization | `interaction/snapshot.ts · PoseSnapshot`, `composeSnapshot` | Reuse for the `restore` payload and the new `focused` field. |
| Store→driver projection pattern | P: `scene.camera.projection` observed by `CameraDriver` → `useProjectionCameraSwap` | Mirror it (driver→store) for the derived focus flag. |
| Selection typing | `domain/cubicellScene.ts · CubeSelection`, `CubeSelectionSet` | Reuse to replace `snapshot.ts · SelectionPort = () => unknown`. |
| **Framing seam into core** | none found (searched: framing port, viewport-size-into-core, `applyZoomFactor` fanout) | **NEW**: `FramingInputs`, `FramingPort`, `ViewportSize`, `core.setViewportSize`, `computeSelectionFrame`, `computeGridFrame` in `interaction/framing.ts`. |
| **Restore command** | none found | **NEW**: `restore` `ViewCommand` kind + `createRestoreViewCommand`. |
| **Focus axis on the authority** | closest is `viewState.ts · focusSnapshot` (the bolted-on field being removed) | **NEW**: `focusRestorePose` field + focus API on the authority. |
| **In-owner mode transitions** | none found (currently precomputed in `useSynchronousEditorCommands`) | **NEW**: `toggleEditorMode`, `toggleBuildMode`, `cyclePickMode`, `setFocused` store actions. |

## 4. The new model

### 4.1 Types (added / changed / removed)

```ts
// editor/commands.ts — ViewCommand union
//   REMOVE: { kind: 'toggle-focus'; target: FocusViewTarget | null }
//   ADD:    { kind: 'restore'; pose: PoseSnapshot }     // literal, idempotent absolute
//   KEEP:   focus | reset | orbit | pan | zoom
//   KEEP EditorCommand kind 'focus-toggle' (the *intent* an adapter emits;
//          the core resolves it — it is no longer a hook concern).

// interaction/framing.ts — NEW headless seam
type ViewportSize = { height: number; width: number }
type FramingInputs = {                    // one thin read of live store state
  editorMode: 'edit' | 'preview'
  scene: CubicellScene
  selection: CubeSelection | null
  selectionSet: CubeSelectionSet | null
  selectionFocusMode: SelectionFocusMode
  viewportMode: ViewportMode
}
type FramingPort = () => FramingInputs     // injected by the app; reads store
// pure, reuse view math:
function computeSelectionFrame(i: FramingInputs, v: ViewportSize): FocusViewTarget | null
function computeGridFrame(i: FramingInputs, v: ViewportSize, fallback: CameraState): FocusViewTarget

// interaction/snapshot.ts
type SelectionSnapshot = {                 // replaces `unknown`
  selection: CubeSelection | null
  selectionSet: CubeSelectionSet | null
}
type InteractionSnapshot = { …; focused: boolean }   // ADD focused
```

`ViewState` (`view/viewState.ts`) is **deleted** entirely: with focus hoisted to
its own authority field, the resting view is a bare `ViewPose` and the reducer is
`reduceViewPose`. See §5.

### 4.2 The two lanes (unchanged in shape, purified in content)

- **View lane** — every camera intent. After the remodel its absolute set is
  `{ focus, reset, restore }`, all **idempotent framings**; `coalesceViewCommands`
  last-wins is therefore always correct. No stateful toggle ever rides it.
- **Synchronous lane** — every non-camera command, dispatch-order, no merge.
  `focus-toggle` and `reset` **enter** here as intents but are resolved by the
  core into view-lane framings before coalescing (they do not execute store
  logic in a hook). Editor mode/build/pick transitions stay synchronous and
  resolve against current state in their owner (the store).

### 4.3 Ownership

- **Camera Authority** owns pose **and** focus: a dedicated
  `focusRestorePose: ViewPose | null` sits beside `morph` and `motion` as a first-
  class axis. Focus API: `isFocused()`, `saveFocusRestorePose()` (snapshots the
  current resting pose), `takeFocusRestorePose()` (returns + clears), `clearFocus()`.
- **Interaction core** owns *resolution*: `core.dispatch` intercepts the two
  stateful view intents and turns them into idempotent framings using the
  authority's current focus state + the framing port + the core-held viewport
  size. It also owns the viewport size (`setViewportSize`).
- **Store** owns non-camera aggregates and the **derived** focus flag (a read-model
  cache of `snapshot.focused`, written by exactly one path).
- **App/adapters** own event→intent translation only: the keymap emits
  `focus-toggle` / `reset` / `zoom`; the wheel handler emits `zoom`; the
  selection-follow adapter emits `focus` / `focus-toggle`. None computes camera
  math or reads `window`.

### 4.4 Single writer per frame

Restored to strictly one writer. `useSingleCameraWriterFrame` → `core.resolveFrame`
→ `composeCameraWrite` is the *only* camera write. The current second writer —
the wheel handler's direct `composeCameraWrite` — is deleted (§4.9). This closes
the exact race `INTERACTIVE.md` invariant 1 names.

### 4.5 Where focus state lives, and how the toggle resolves

Focus lives once, on the authority (`focusRestorePose`). `core.dispatch` resolves
`focus-toggle` at decision time:

```
dispatch(focus-toggle):
  if authority.isFocused():
     pose = authority.takeFocusRestorePose()          // clear
     push  { kind: 'restore', pose: toPoseSnapshot(pose) }   // idempotent absolute
     return accepted
  else:
     target = computeSelectionFrame(framingPort(), viewportSize)
     if !target: return rejected("No focusable selection")
     authority.saveFocusRestorePose()                 // save current pose NOW
     push  createFocusViewCommand(target.center, target.zoom, target.orientation)
     return accepted
```

Because the toggle's statefulness is consumed here and only an idempotent framing
enters the lane, two toggles in one frame compose correctly (save A + frame-target,
then frame-A + clear → last-wins keeps frame-A, focus ends OFF — back where you
started). The `focusedSelectionKeyRef` coalescing seed becomes unnecessary and is
deleted. `restore` carries a literal `PoseSnapshot` because focus-off must return
to the exact prior pose, which `focus` (which re-derives position from orientation
and initial distance) cannot reproduce.

### 4.6 How the store flag derives

`InteractionSnapshot` gains `focused` (from `authority.isFocused()`). One writer —
the driver's per-frame tick — mirrors it into the store via a new `setFocused`
action, only on change. This is P's projection pattern with the arrow reversed:
P is store→core (driver observes `scene.camera.projection`); focus is core→store
(driver observes `snapshot.focused`). Both are single-writer observed projections.
The three existing consumers keep reading `state.editor.selectionFocusActive`
unchanged — `App.tsx` (`selectionFocusActive ? selectionFocusMode : 'focus'`),
`SceneSection.tsx` (the Isolate switch), `useSelectionFocusCommands` — but the
field is now single-sourced. Every other writer of it is deleted (§5).

### 4.7 How framing intents are shaped, and how viewport size reaches the core

The framing math already lives, pure and DOM-free, in `view/viewportFocus.ts` +
`view/selectionFocus.ts`. The remodel does **not** move or copy it; it moves the
**call site** from React hooks into the core:

- Viewport size becomes typed core state: `core.setViewportSize({ width, height })`,
  called by `CameraDriver` from the R3F `size` (`useThree().size`), never
  `window.innerWidth/Height`.
- `FramingPort` is a thin, injected `() => FramingInputs` that reads live store
  state (scene, selection, prefs). It is built in the app layer where the store is
  reachable; the core depends only on its typed signature.
- `computeSelectionFrame` / `computeGridFrame` are pure functions in
  `interaction/framing.ts` that call the existing view math with
  `(framingPort(), viewportSize)`. A headless test injects a fake port + a size
  and asserts the target. An LLM calling `core.dispatch(focus-toggle)` now truly
  focuses: the core resolves the target headlessly (invariant 3 + 6).

### 4.8 Reset — one home, one lane

`reset` becomes a plain view-lane absolute whose target the core resolves:

```
dispatch(view/reset):        // target always arrives null from the keymap/button
  authority.clearFocus()
  target = computeGridFrame(framingPort(), viewportSize, initialCamera)
  push { kind: 'reset', target }
  return accepted
```

The `target:null`-vs-`target` split, the synchronous re-dispatch trampoline, and
the `window`-reading `createResetTarget` all disappear. The Reset button
(`SceneSection.tsx`) keeps its existing `dispatch(createEditorViewCommand(resetViewCommand))`
(now resolved in the core) and `resetEditorSession()` for the session reset; the
**desync dies** because focus is no longer an independent store field that
`resetEditorSession` must remember to clear — clearing focus is the core's job,
triggered by the reset command the button already sends.

### 4.9 The zoom command path (wheel)

The wheel handler stops touching the camera and becomes a pure adapter:

```
handleWheel(event):
  event.preventDefault()
  core.dispatch(createEditorViewCommand(
    createZoomViewCommand(getWheelZoomFactor(event.deltaY, sensitivity))))
```

`coalesceViewCommands` already multiplies same-frame zoom factors
(`combineViewCommand`), and `useSingleCameraWriterFrame` applies the result. This
removes `applyZoomFactor` from the core, the authority, and the wheel handler, and
removes the wheel's direct `composeCameraWrite`.

> **Decision point for Stuart (feel).** Today wheel zoom applies instantly; a
> keyboard zoom tap eases ~220ms (`getViewCommandMotionDuration` default). Routing
> both through the additive lane forces one policy. Recommendation: apply additive
> **zoom** without a motion plan (instant, per-frame coalesced) so wheel keeps its
> current feel; keyboard zoom taps then snap like orbit taps already do via the
> detent. If you want to keep keyboard easing, the alternative is a per-apply
> instant hint on the wheel dispatch. Flagged, not decided; a test gate pins
> "same `deltaY` → same total zoom, one writer" either way.

## 5. Migration / removal map (DRY — delete, never parallel)

Deletions land **inside the slice that replaces them**, never deferred:

- `app/useSelectionFocusCommands.ts · focusedSelectionKeyRef` seed + comment —
  **delete** (no longer load-bearing). Slim the hook to: dispatch a plain
  idempotent `focus` on selection change while focused, and `focus-toggle` to
  auto-exit when the target is lost. Remove its `setSelectionFocusActive` writes.
- `view/viewState.ts` — **delete the file**: `ViewState`, `createViewState`,
  `createViewStateFromPose`, `reduceViewState`, `reduceFocusToggleViewState`.
  `cameraAuthorityRuntime.ts` switches to a bare `restingPose: ViewPose` +
  `focusRestorePose: ViewPose | null`, using `reduceViewPose` + `cloneViewPose`
  directly. This also erases the 6× `focusSnapshot` re-threading (opus #9).
- `editor/commands.ts` — **delete** `toggle-focus` `ViewCommand` kind +
  `createToggleFocusViewCommand`; drop it from `canRepeatViewCommand`. **Add**
  `restore` + `createRestoreViewCommand`.
- `view/viewPose.ts · reduceViewPose` — **delete** the `toggle-focus` case; add
  `restore`. `motion/cameraMotion.ts · getViewCommandMotionDuration` — retarget
  the `toggle-focus` case to `restore`.
- `interaction/command.ts` — **delete** `isSynchronousViewCommand`; `isViewCommand`
  collapses to `command.kind === 'view'`; `isAbsoluteViewCommand` becomes
  `focus | reset | restore` (a toggle is not an absolute — Gap 1).
- `app/useSynchronousEditorCommands.ts` — **delete** the `view`+`reset` branch,
  `createResetTarget` (the `window` read), and the `focus-toggle` →
  `toggleSelectionFocus` branch (both now resolved in the core). Replace the
  `editor-mode-toggle` / `build-mode-toggle` / `pick-mode-cycle` branches'
  captured-state computation with calls to the new store actions; drop
  `editorMode` / `buildModeActive` / `pickMode` from its dep array.
- `state/cubicellStore.ts` — **remove** `selectionFocusActive` writes from
  `resetEditorSession` and elsewhere; the only writer becomes the new `setFocused`
  projection. **Add** `toggleEditorMode`, `toggleBuildMode`, `cyclePickMode`
  (functional `set`, current-state resolution; reuse extracted helpers).
- `interaction/cameraWheelZoom.ts` — **delete** `applyWheelZoomToCore` and the
  direct `composeCameraWrite` in `createCameraWheelZoomHandler`; keep
  `getWheelZoomFactor`. `interaction/authority.ts`, `interactionCore.ts`,
  `cameraAuthorityRuntime.ts` — **delete** `applyZoomFactor` /
  `applyCameraAuthorityZoomFactor`.

**Already resolved / out of scope.** The `cameraDriverRuntime.ts` size finding
(opus #7, codex #6) is **already fixed** by the `interaction/driver-hygiene`
split now in the base: that file is deleted and the largest interaction module is
`cameraAuthorityRuntime.ts` at 622 LOC, so no file trips the 700-LOC "refactor
before adding" rule and the remodel builds on the split. Considered but not
approved (keep for a later pass): command repeatability object-identity
(`commandRegistry.ts · canRepeatEditorCommand`, codex #5); the one-shot `window`
read in the `useEditorCommands` bootstrap `initialCamera` (outside the
per-command path).

## 6. PR-sized slices (ordered, each independently testable)

Each slice compiles, ships, and is green on its own. Dependencies noted.

### Slice 1 — Mode/build/pick transitions into the store (Gap 1c). *No deps.*
Add `toggleEditorMode`, `toggleBuildMode`, `cyclePickMode` (functional `set`,
resolving from `state.editor.*`; reuse extracted `convertSelectionToPickMode`
and build-mode placement-clear helpers). Repoint the three `runSynchronous`
branches; shrink its dep array. Keep the absolute setters for panel callers.
- **Tests.** `state.test.ts`: two `cyclePickMode` / `toggleBuildMode` in a row
  advance two steps (today's captured-state collapse is gone). `keyboard.test.ts`:
  the mapped keys still transition. **Gate:** `npm test`, `tsc -b`, `oxlint`.

### Slice 2 — Framing seam + typed selection port (Gap 2 substrate). *No deps; no behavior change.*
Add `interaction/framing.ts` (`ViewportSize`, `FramingInputs`, `FramingPort`,
`computeSelectionFrame`, `computeGridFrame` reusing the view math);
`core.setViewportSize`; wire it from `CameraDriver` R3F `size`; inject `FramingPort`
from `useEditorCommands`. Type `snapshot.ts` selection as `SelectionSnapshot`
(replace `unknown`). Nothing consumes the framing yet.
- **Tests.** new `interaction.framing.test.ts` (headless): canned `FramingInputs` +
  size → expected target; no selection → `null`; no cells → fallback;
  `viewportMode !== 'grid'` → `null`. `interaction.snapshot.test.ts`: selection is
  typed and round-trips. **Gate:** as above.

### Slice 3 — Focus toggle resolved in the core (Gap 1a + Gap 2 focus). *Depends on Slice 2.*
Add `restore` command + reducer/motion/classify updates; hoist focus to the
authority (`focusRestorePose` + focus API), delete `view/viewState.ts` and the
`focusSnapshot` re-threading. Intercept `focus-toggle` in `core.dispatch` (§4.5);
add `focused` to the snapshot; project it via `setFocused` from the driver; delete
every other `selectionFocusActive` writer; slim `useSelectionFocusCommands` and
remove the seed; remove `toggle-focus` entirely.
- **Tests.** `interaction.core.test.ts`: OFF→ON saves pose + emits `focus`; ON→OFF
  emits `restore` to the saved pose; two toggles/frame net-idempotent; no target →
  rejected. `interaction.authority.test.ts`: `focusRestorePose` lifecycle.
  `interaction.command.test.ts`: `restore` is absolute, `toggle-focus` gone.
  `view.test.ts`: `reduceViewPose` `restore`. `interaction.snapshot.test.ts`:
  `focused` reflects the authority. `panels.test.tsx`: Isolate switch reads the
  derived flag. **Gate:** as above.

### Slice 4 — Reset unified into one lane (Gap 1b). *Depends on Slice 2 + 3.*
Delete `isSynchronousViewCommand` and the synchronous reset branch +
`createResetTarget`; intercept `reset` in `core.dispatch` (§4.8) using
`computeGridFrame` + `authority.clearFocus`. Confirm the Reset button and the
`0`/`5` keymap now flow one path; `resetEditorSession` no longer touches focus.
- **Tests.** `interaction.command.test.ts`: `reset` classifies view/absolute, never
  synchronous. `interaction.core.test.ts`: reset frames the grid extent and clears
  focus; reset while focused exits focus (no desync). `panels.test.tsx`: Reset
  button issues one resolved reset. **Gate:** as above.

### Slice 5 — Wheel zoom through the command lane (Gap 2 zoom). *No structural dep; last to isolate the feel decision.*
Wheel handler dispatches `zoom` (§4.9); delete `applyZoomFactor` (core + authority +
runtime), `applyWheelZoomToCore`, and the wheel's direct `composeCameraWrite`.
Land the additive-zoom feel decision from §4.9.
- **Tests.** `interaction.core.test.ts` / `interaction.viewLane.test.ts`: dispatched
  zoom factors coalesce (multiply) and apply via `resolveFrame`.
  `interaction.cameraDriver.test.ts`: no camera write outside the single writer
  (assert `composeCameraWrite` count). Feel check: same `deltaY` → same total zoom
  (unit) + optional Playwright smoke. **Gate:** as above.

## 7. Verification summary

Per slice: `npm test` (targeted suite first, then full), `tsc -b`, `oxlint`, all
observed green before the slice is called done. Cross-cutting invariants to assert
across the set: (1) one `composeCameraWrite` per frame; (3) `focus-toggle` / `reset`
/ `zoom` reach the camera identically from keymap, button, and a raw
`core.dispatch` (no privileged path); (4) `restore` and every command remain
serializable data; the coalescing lane only ever receives idempotent absolutes.
