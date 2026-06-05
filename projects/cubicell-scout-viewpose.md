# Scout: ViewPose + pose math seam (MODEL.v2 extraction step 3)

Read-only scout, 2026-07-10, by cubicell:general:8:6.1. No source
modified. Basis: main at 30ddf37 (steps 1-2 merged). Goal: lift pose
math behind a stable contract so interaction depends on domain and
pose math only, per MODEL.v2's horizontal layering.

## 1. Public contract

`src/view/` fuses two different strata. The pose-math stratum is three
modules; the view-policy stratum is two. The contract question splits
accordingly.

### Pose math (the layer interaction sits on)

- **`viewPose.ts`** (351 loc): `ViewPose` type, `minCameraZoom` /
  `maxCameraZoom` (the canonical zoom boundary),
  `createViewPoseFromCameraState`, `createViewPoseFromCamera`,
  `cloneViewPose`, `applyViewPoseToCamera`, `getViewOffsetDirection`,
  `reduceViewPose`, `getInitialCameraOffset`. Private helpers
  (orbit/pan/zoom/focus reducers, axis math) stay private.
- **`cameraState.ts`** (26 loc): `CameraState`, `defaultCamera`, and
  the `ProjectionMode` re-export (view-layer home per PR #17).
- **`projectionMatch.ts`** (53 loc): `perspectiveFovDegrees`,
  `orthoLikeFovDegrees`, `projectionMorphDurationMs`,
  `projectionMorphFarMarginWorld`, `getFovWorldHeight`,
  `getFovDistanceForWorldHeight`,
  `getPerspectiveDistanceForOrthoZoom`,
  `getOrthoZoomForPerspectiveDistance`,
  `hasMatchedPerspectiveFraming`.

External consumers (file -> symbols):

- `src/interaction/authority.ts` -> CameraState, ProjectionMode, ViewPose (types)
- `src/interaction/cameraAuthorityRuntime.ts` -> cloneViewPose, createViewPoseFromCameraState, reduceViewPose, ViewPose; CameraState, ProjectionMode
- `src/interaction/CameraDriver.tsx` -> createViewPoseFromCameraState; CameraState, ProjectionMode
- `src/interaction/cameraDriverMath.ts` -> applyViewPoseToCamera, cloneViewPose, getViewOffsetDirection, ViewPose; getPerspectiveDistanceForOrthoZoom, perspectiveFovDegrees, projectionMorphFarMarginWorld; ProjectionMode
- `src/interaction/cameraFrameWriter.ts` -> cloneViewPose, ViewPose; ProjectionMode
- `src/interaction/cameraGestureRuntime.ts` -> cloneViewPose, createViewPoseFromCamera, ViewPose
- `src/interaction/cameraPanGesture.ts` -> ViewPose (type)
- `src/interaction/cameraProjectionSwap.ts` -> createViewPoseFromCamera, createViewPoseFromCameraState, getViewOffsetDirection, ViewPose; getFovDistanceForWorldHeight, getFovWorldHeight, hasMatchedPerspectiveFraming, perspectiveFovDegrees, projectionMorphFarMarginWorld; CameraState, ProjectionMode
- `src/interaction/interactionCore.ts` -> ViewPose; CameraState, ProjectionMode (types)
- `src/interaction/morph.ts` -> getFovDistanceForWorldHeight; ProjectionMode
- `src/interaction/orbitDetent.ts` -> cloneViewPose, createViewPoseFromCameraState, getViewOffsetDirection, reduceViewPose, ViewPose; CameraState
- `src/interaction/snapshot.ts` -> ViewPose; ProjectionMode (types)
- `src/interaction/framing.ts` -> CameraState (type)
- `src/motion/cameraMotion.ts` -> cloneViewPose, ViewPose
- `src/scene/CubeScene.tsx` -> CameraState (type)
- `src/state/cubicellState.ts` -> orthoLikeFovDegrees, projectionMorphDurationMs
- `src/view/viewportFocus.ts` -> minCameraZoom, maxCameraZoom, getInitialCameraOffset, viewPose helpers (the cross-stratum consumer)
- Tests: `interaction.authority/cameraDriver/core/framing/morph/snapshot`, `projection`, `view`, `state`

Thirteen of the sixteen production consumers are `src/interaction/`
plus `src/motion/` — this IS the "interaction depends on pose math"
layer, already real in the import graph.

### View policy (stays in src/view)

- **`viewportFocus.ts`** (508 loc): `viewportModes`, `ViewportMode`,
  `ViewportFocusTarget`, `FrameViewportSize`, `GridFrameOptions`,
  `createGridViewportFocus`, `createGridFrameTarget`,
  `createGridFramedCamera`. Consumers: `src/interaction/framing.ts`,
  `src/app/useEditorCommands.ts` (createGridFramedCamera),
  `src/state/cubicellState.ts` + `src/config/cubicellConfig.ts`
  (ViewportMode type).
- **`selectionFocus.ts`** (70 loc): `selectionFocusModes`,
  `SelectionFocusMode`, `ViewportFocusSelection`,
  `createViewportFocusSelection`, `getSelectionVisibleCells`,
  `hasSelectionTarget`. Consumers: `src/scene/CubeScene.tsx`,
  `src/interaction/framing.ts`, `src/state/cubicellState.ts`,
  `src/config/cubicellConfig.ts`.

### Leaks / wrinkles flagged

1. **Pose math imports the command vocabulary.** `viewPose.ts` imports
   `ViewCommand` + `FocusViewOrientation` (type-only) from
   `../editor/commands` for `reduceViewPose`; `viewportFocus.ts`
   imports `FocusViewOrientation` + `FocusViewTarget`. Under MODEL.v2
   the command union is the actor surface, above pose math.
   `reduceViewPose` is a command interpreter living in a math module.
   Type-only, zero runtime coupling, so it does not block step 3;
   resolving it belongs to step 4 (the registry reclassification
   reshapes the command union anyway; at that point either the view
   motion params become the pose-math input and `reduceViewPose`'s
   command switch moves up into interaction, or the shared vocabulary
   types get a lower home). Do not solve it now; record it.
2. **A feel constant lives in pose math.** `projectionMorphDurationMs
   = 320` (projectionMatch.ts) is a surface-feel knob consumed by
   `cubicellState`; per project preference feel numbers belong in
   config/pref knobs, not math modules. Cheap to relocate to
   `cubicellConfig` during the lift; optional.
3. No dead exports: every pose-math export has a production or test
   consumer (`getInitialCameraOffset`'s only consumer is
   `viewportFocus.ts`, cross-stratum, which is fine barrel-to-barrel).

## 2. Home / naming: SPLIT, `src/pose/` + curated `src/view/`

Recommendation: **split now.** Create `src/pose/` holding
`viewPose.ts`, `cameraState.ts`, `projectionMatch.ts` behind a curated
`index.ts`; `src/view/` keeps `viewportFocus.ts` + `selectionFocus.ts`
behind its own curated barrel.

Dependency-direction evidence:

- Interaction + motion consume pose math from 14 files but touch view
  policy only through `framing.ts` (one file). The strata have
  different consumer populations: pose math serves
  interaction/motion; view policy serves scene, state, config, app.
- Internal deps already flow one way: `viewportFocus` ->
  `viewPose`/`cameraState`; nothing in the pose trio imports the
  focus modules. The cut has no cycles.
- MODEL.v2's sentence "Interaction core depends on domain and pose
  math only" needs a nameable pose-math layer to be checkable;
  `src/pose/` makes the oxlint guard expressible.
- No Domain->View inversion found: `cameraState` depends only on
  domain (ProjectionMode re-export, correct direction per PR #17);
  domain imports nothing from view (verified in step 1's gates).
- Honest caveat, not an inversion: `src/interaction/framing.ts`
  consuming view policy means "interaction depends on domain and pose
  math ONLY" is aspirational until step 4; framing commands genuinely
  need focus targets. The step-4 registry work (handlers behind
  ports) is where that dep gets a lawful shape. Step 3 should not
  force it.

Name: `src/pose/` (short, matches "pose math", avoids colliding with
the View state-target or `ViewPose` the type). `src/viewpose/` is
acceptable but redundant once the barrel exports `ViewPose`.

## 3. Carry-forward inventory (the acceptance test)

Must survive verbatim, with exact sites:

- **Single-writer camera.** `applyViewPoseToCamera`
  (`src/view/viewPose.ts`) is the only camera-write primitive and has
  exactly ONE production caller: `src/interaction/cameraDriverMath.ts`,
  driven per-frame by `CameraDriver.tsx` through
  `createCameraAuthority` (`src/interaction/authority.ts`).
  Post-extraction assertion: `applyViewPoseToCamera` still has exactly
  one production call site.
- **Morph dual-axis discipline.** `src/interaction/morph.ts` +
  `src/interaction/cameraProjectionSwap.ts` consuming
  `projectionMatch`'s equivalence math (`perspectiveFovDegrees`,
  `orthoLikeFovDegrees`, `getFovDistanceForWorldHeight`,
  `hasMatchedPerspectiveFraming`, `projectionMorphFarMarginWorld`).
  Pinned by `tests/interaction.morph.test.ts` and
  `tests/projection.test.ts`.
- **ViewPose + canonical zoom boundary.** `minCameraZoom` /
  `maxCameraZoom` + the clamp inside `zoomViewPose` (private, inside
  `reduceViewPose`) in `viewPose.ts`, and the framing clamp in
  `viewportFocus.ts`. Pinned by `tests/interaction.cameraDriver.test.ts`
  ("wheel zoom clamps the core pose at both zoom bounds") and
  `tests/view.test.ts` (frame zoom at `minCameraZoom`).

Acceptance test for step 3: those tests pass with import-path-only
diffs, and all three module bodies move byte-identical (except
imports and, if taken, the `projectionMorphDurationMs` relocation).

## 4. Purity and quality

- **Pose math is pure-with-one-deliberate-exception and touches three
  by design.** `viewPose.ts` and `viewportFocus.ts` use three's math
  primitives (`Vector3`, `Euler`, `Quaternion`, `Matrix4`) — these are
  side-effect-free value types; "pose math depends on three math
  primitives" is acceptable and MODEL.v2's Domain purity rule ("no
  three renderer") does not apply to this layer. The exception:
  `applyViewPoseToCamera` MUTATES the camera argument. That is not a
  leak; it is the single-writer's write primitive, and its
  one-caller discipline is the invariant (section 3). Everything else
  is pure. No React, DOM, or store anywhere in `src/view/`.
- **No duplication or dead code found** across the five modules; all
  exports consumed.
- **`viewportFocus.ts` at 508 loc** is under the 700 hard limit but
  the largest doc-relevant file in the seam; no action required in
  step 3.
- **Boundary enforcement: oxlint works.** Mirror the domain /
  evaluation / transport guard pairs in `.oxlintrc.json`:
  `**/pose/*` + `*/pose/*` and `**/view/*` + `*/view/*`, with
  `src/pose/**` and `src/view/**` added to the override list. Barrel
  imports pass, deep paths fail; no boundary test needed. Note the
  `*/view/*` guard only becomes addable once view has a barrel
  (slice V2), since every consumer currently deep-imports.

## 5. Ordered plan (PR-sized slices)

1. **Slice V1 — pose math behind the contract.** Move `viewPose.ts`,
   `cameraState.ts`, `projectionMatch.ts` to `src/pose/` with a
   curated `index.ts`; re-point the 16 production consumers and 9 test
   files; add the pose oxlint guard; optionally relocate
   `projectionMorphDurationMs` to `cubicellConfig` (feel knob). Gates:
   full suite green, lint clean, the three carry-forward assertions
   from section 3, module bodies byte-identical apart from imports.
2. **Slice V2 — curate the view-policy barrel.** Add
   `src/view/index.ts` exporting the `viewportFocus` +
   `selectionFocus` surface; re-point `framing.ts`,
   `useEditorCommands.ts`, `cubicellState.ts`, `cubicellConfig.ts`,
   `CubeScene.tsx`, and `tests/view.test.ts`; add the view guard.
   Gates: suite green, no deep `view/` imports outside `src/view/**`.
3. **Docs follow-through (in V2 or the merge PR).** ARCHITECTURE.md
   items for `src/pose/`; MODEL.v2 step 3 done annotation; record the
   two step-4 debts (command-type dep in pose math,
   `framing.ts`'s view-policy dep) so the registry reclassification
   picks them up.

Then step 4 (interaction core + finished registry) proceeds per
MODEL.v2, with the two recorded debts as explicit inputs.
