# Scout: MODEL.v2 extraction step 5 — camera adapter rehome

Scouted by Fable, 2026-07-10. Basis: main at 32eb07b. Read-only; import graph re-verified with fmm. This is the capstone slice: after it, `src/interaction` is the headless interaction core and the strangler is complete.

## 0. Graph verification

Coordinator findings confirmed, with corrections of detail:

- The adapter cluster is 14 files, 2,085 LOC: 12 `camera*.ts` files + `CameraDriver.tsx` + `orbitDetent.ts`. (`cameraAuthorityRuntime.ts` 647, `cameraProjectionSwap.ts` 309, `orbitDetent.ts` 295, `cameraGestureRuntime.ts` 201, `CameraDriver.tsx` 134, `cameraPanGesture.ts` 123, `cameraDriverMath.ts` 114, `cameraFrameWriter.ts` 75, `cameraGlideCommand.ts` 69, `cameraWheelZoom.ts` 39, `cameraTrackball.ts` 38, `cameraCaptureRegistration.ts` 18, `cameraDriverTypes.ts` 13, `cameraDriverDom.ts` 10.) Post-move `src/interaction` is ~1,350 LOC across 18 files.
- External production deep-imports: exactly two files, both into `CameraDriver.tsx`: `src/scene/CubeScene.tsx` (value `CameraDriver` + type `RegisterCapture`) and `src/app/useSynchronousEditorCommands.ts` (type `RegisterCapture` only). Confirmed.
- The circular edge `authority.ts <-> cameraAuthorityRuntime.ts` is real and is the only cycle. Critically: every OTHER core consumer of `authority.ts` (`interactionCore.ts`, `snapshot.ts`, `commands/registry.ts`, `cameraGlideCommand.ts`) imports **types only** (`CameraAuthority`, `PoseMode`, `CameraFeelConfig`). The only value-level edge into the runtime is `authority.ts`'s own factory `createCameraAuthority` (authority.ts:58-72).
- `createInteractionCore` already takes `authority: CameraAuthority` **injected** (interactionCore.ts:64-82). Dependency inversion is already in place; the composition root is `src/app/useEditorCommands.ts`, the sole production caller of `createCameraAuthority`.
- One extra cross-boundary edge the brief missed: `cameraGestureRuntime.ts` imports `src/scene/sceneSelectionGesture.ts` (pointer gesture arbitration). It moves with the cluster and becomes a camera -> scene edge. Pre-existing; see §5.

## 1. File manifest and the three adjudications

### authority.ts — SPLITS. Types and constants STAY as the core port; the factory MOVES.

`authority.ts` is 72 lines: the `CameraAuthority` port type, `PoseMode`, `CameraFeelConfig`, two config-derived glide constants, and a 15-line factory that delegates to the runtime. The type is the contract `interactionCore`, `snapshot`, and the registry are written against — that is core and must stay. The factory is the adapter constructor — it belongs with the runtime.

Breaking the back-edge is therefore a move of `createCameraAuthority` + the private `createDefaultCameraFeelConfig` into the new home. After that:

- `authority.ts` has zero adapter imports (its `cameraAuthorityRuntime` import disappears; its `morph`/`viewLane` imports are type-only core edges).
- `cameraAuthorityRuntime.ts` imports `type { CameraAuthority, CameraFeelConfig }` from the interaction barrel — adapter depends on core port. Correct direction, cycle gone.
- No other file changes meaning. This is the entire cut; everything else is `git mv` + import re-points.

The glide constants (`glidePanWorldUnitsPerSecond`, `glideZoomFactorPerSecond`) stay in `authority.ts`: they are the feel defaults the port's `CameraFeelConfig` is documented against, they are already re-derived from `defaultInputFeelPreferences` (no magic numbers), and tests import them via the interaction barrel. The moved factory imports them from the barrel.

### orbitDetent.ts — MOVES.

Its only consumer is `cameraAuthorityRuntime.ts` (9 of its 10 exports). It is camera-feel policy (detent tap/glide sampling) that exists solely to serve the runtime. Its own imports (`editor/commands`, `viewReducer`, `motion/easing`, `shared/math`) all point downward into core/shared and survive the move unchanged (viewReducer re-pointed to the barrel's `reduceViewPose`). Conceptually one could argue detent math is "pure policy", but a core module with exactly one adapter consumer is adapter code wearing a core badge. It moves.

### morph.ts — STAYS.

Core: the interaction barrel exports it, `authority.ts` (type) and `interactionCore.ts` consume it, and it has no adapter imports (`motion/easing`, `pose`, `shared/math` only). `cameraDriverMath.ts` and the runtime consume it from the camera side post-move — adapter -> core via the barrel, correct direction. Everything they need (`createProjectionMorph`, `sampleProjectionMorph`, both types) is already on the barrel.

### Full manifest

**MOVES (14 files):** `CameraDriver.tsx`, `cameraAuthorityRuntime.ts`, `cameraCaptureRegistration.ts`, `cameraDriverDom.ts`, `cameraDriverMath.ts`, `cameraDriverTypes.ts`, `cameraFrameWriter.ts`, `cameraGestureRuntime.ts`, `cameraGlideCommand.ts`, `cameraPanGesture.ts`, `cameraProjectionSwap.ts`, `cameraTrackball.ts`, `cameraWheelZoom.ts`, `orbitDetent.ts` — plus the `createCameraAuthority` factory extracted from `authority.ts`.

**STAYS (18 files):** `authority.ts` (types + constants), `bus.ts`, `command.ts`, `framing.ts`, `index.ts`, `interactionCore.ts`, `morph.ts`, `snapshot.ts`, `viewLane.ts`, `viewReducer.ts`, `commands/` (7 files).

Sanity check on the post-move core: nothing left in `src/interaction` imports react, three, or the DOM. The remaining editor/domain/pose/config imports match the step-4 seam sentence.

## 2. New home

**`src/camera/`, flat, with a curated `index.ts` barrel.** Rationale:

- Vocabulary: existing homes are flat single-word role nouns (`domain`, `evaluation`, `transport`, `pose`, `view`, `interaction`). `camera` is the ubiquitous-language name this cluster already uses in every filename. `src/adapters/camera` would introduce a second organizing axis nobody else uses.
- No collision: `pose` owns `CameraState` (camera *data*); `src/camera` owns camera *behavior* (runtime, gestures, driver). The barrels keep this distinction legible.
- Flat beats nested (`camera/{authority,driver}/`): 14 files does not need two levels, and the pure-runtime vs R3F-driver split inside the cluster is visible from imports (`cameraAuthorityRuntime`/`cameraGlideCommand`/`orbitDetent` have no three/react imports; the rest are R3F/DOM-bound).
- Filenames: keep them as-is during the move (pure rehome, one rename event, trivially reviewable). Dropping the `camera` prefix (`src/camera/trackball.ts`) reads better long-term but is optional polish; if taken, do it in the same `git mv` so history stays single-hop. Default: keep names.

Suggested factory placement: `src/camera/createCameraAuthority.ts` (tiny file: factory + default feel config), re-exported by the barrel. Do NOT fold it into `cameraAuthorityRuntime.ts` — that file is 647 LOC, just under the 700 hard cap; nothing gets added to it in this step beyond its import block.

## 3. Barrels and guards

### Camera barrel (`src/camera/index.ts`) — three exports

```ts
export { CameraDriver, type RegisterCapture } from './CameraDriver'
export { createCameraAuthority } from './createCameraAuthority'
```

That is the entire external surface. Everything else is module-private behind the guard. Tests deep-import `cameraDriverMath`, `cameraDriverDom`, `cameraWheelZoom` today; tests are already exempt in the oxlint overrides, so they keep deep imports with updated paths — no test-only exports pollute the barrel.

### Interaction barrel sheds

- `createCameraAuthority` (the only shed export). `PoseMode`, `CameraAuthority`, `CameraFeelConfig`, and the two glide constants stay — they are the port.
- The header comment "Camera/driver/gesture adapters stay deep-imported until step 5" (index.ts:3) is deleted; the barrel is now fully headless with no exceptions.

Do NOT re-export camera symbols from the interaction barrel for compatibility — that would create an interaction -> camera import, the exact wrong-direction edge this step removes.

### Oxlint guard

- **Add** a camera group mirroring the module guards: patterns `**/camera/*`, `*/camera/*`, message "Import from the camera barrel (…/camera), not a deep camera path."
- **Replace** the enumerated per-file interaction group (.oxlintrc.json:31-51) with the uniform whole-module pattern used by domain/pose/view: `**/interaction/*`, `*/interaction/*`. This is a step-5 payoff: the enumeration existed only because adapters were grandfathered. Caveat for the builder: the `commands/` subdirectory means single-`*` globs may not cover `…/interaction/commands/registry`; verify oxlint's glob semantics and add `**/interaction/*/*` (or `**/interaction/**` minus the barrel) as needed. **Gate: prove the guard fires with a deliberate violation before trusting it.**
- **Add** `src/camera/**` to the overrides files list so intra-camera relative imports stay legal.

## 4. Consumer re-points

All through the new barrel; no deep-import exceptions survive.

| File | Today | After |
|---|---|---|
| `src/scene/CubeScene.tsx` | `CameraDriver`, `type RegisterCapture` from `../interaction/CameraDriver` | from `../camera` |
| `src/app/useSynchronousEditorCommands.ts` | `type RegisterCapture` from `../interaction/CameraDriver` | from `../camera` |
| `src/app/useEditorCommands.ts` | `createCameraAuthority` from `../interaction` | from `../camera` (its other interaction imports unchanged) |
| tests: `interaction.authority`, `interaction.core`, `interaction.snapshot`, `interaction.cameraDriver`, `synchronousLane` | `createCameraAuthority` / `CameraDriver` via `../src/interaction`(`/CameraDriver`) | via `../src/camera`; deep test imports (`cameraDriverMath`, `cameraDriverDom`, `cameraWheelZoom`) get path updates only |

Bonus re-point enabled by the uniform guard: `useSynchronousEditorCommands.ts:26` deep-imports `../interaction/commands`; all five symbols it uses (`commandRegistry`, `invokeCanRun`, `invokeRun`, `CommandContext`, `CommandPorts`) are already on the interaction barrel. Re-point it so the uniform guard holds with zero exceptions.

## 5. DRY / dead-surface findings

1. `orbitDetent.getCompatibleOrbitProgress` is exported but only called inside `orbitDetent.ts` itself. De-export (keep the function). Per repo lesson: ran the usage check; it was never imported anywhere in git-tracked src/tests at HEAD — an over-broad export, not a lost feature.
2. The glide constants in `authority.ts` are pure aliases of `defaultInputFeelPreferences` fields, and their only external consumers are two test files. Optional follow-up (not in these slices): tests read `defaultInputFeelPreferences` directly and the aliases disappear.
3. `interactionCore.ts:205` re-exports `SynchronousDispatch` (already exported by `bus.ts` and the barrel). Harmless duplication; fold into the barrel's bus block whenever `interactionCore.ts` is next touched. Not worth a slice.
4. `cameraGestureRuntime -> scene/sceneSelectionGesture` becomes a documented camera -> scene edge. It is pre-existing behavior (pointer arbitration between selection and camera gestures) and MUST NOT be "fixed" inside this step — flag it as the step-5 residual debt in MODEL.v2 alongside step 4's transport-scrub clamp note. `scene` has no barrel yet; that is adapters-and-views follow-on work, not this slice.
5. `cameraAuthorityRuntime.ts` at 647 LOC is 53 lines from the hard cap. This step touches only its import block. Note in MODEL.v2: next substantive change to that file pays the split (state vs runtime seam is already visible at `createCameraAuthorityState`).

## 6. Slices

Each gate: full suite green (`vitest`), `oxlint` clean, plus the named checks. Zero runtime change throughout — every slice is `git mv` + import edits + the one factory extraction.

**PR A — the cut (small, design-bearing).** Create `src/camera/`; move `cameraAuthorityRuntime.ts`, `cameraGlideCommand.ts`, `orbitDetent.ts`; extract `createCameraAuthority` + `createDefaultCameraFeelConfig` from `authority.ts` into `src/camera/createCameraAuthority.ts`; camera barrel v1 exports only `createCameraAuthority`; interaction barrel sheds it; moved files re-point core imports to `../interaction`; re-point `useEditorCommands` + 4 test files. Extra gates: `grep` proves no `src/interaction` file imports `src/camera` (direction check, becomes the review ritual for B and C too); diff of `cameraAuthorityRuntime.ts` and `orbitDetent.ts` shows import-block-only changes; `createDefaultCameraFeelConfig` values byte-identical.
*Drift probe for reviewers:* glide feel and orbit detent taps are covered only indirectly, via `interaction.authority.test.ts` driving the runtime through `createCameraAuthority`. If the factory's default feel config drifts, those tests are the only net. Reviewers should diff the factory move line-by-line.

**PR B — the bulk move (large, mechanical).** Move the remaining 11 driver files; barrel adds `CameraDriver` + `RegisterCapture`; re-point `CubeScene`, `useSynchronousEditorCommands` (RegisterCapture import), and the driver-touching tests. Extra gates: direction grep; diff shows no logic-line changes (import blocks and paths only); `CameraDriver.tsx` external deps (`@react-three/fiber`, three, TrackballControls) unchanged.
*Drift probe:* `cameraGestureRuntime`'s `sceneSelectionGesture` import silently changing to a different symbol or the pan/trackball wiring being "tidied" during the move. The move must be boring.

**PR C — guards and hygiene (small).** Camera guard group; interaction guard collapsed to the uniform pattern; `src/camera/**` added to overrides; `useSynchronousEditorCommands` commands deep-import re-pointed to the barrel; barrel header comments updated; MODEL.v2.md step 5 marked done with the residual-debt notes (camera->scene edge, runtime split debt, constants cleanup); `getCompatibleOrbitProgress` de-exported. Extra gates: deliberate-violation check proves both guard groups actually fire (including a `…/interaction/commands/registry` deep import); suite green.

Recommended sequencing: A and B could merge, but keeping A separate isolates the only non-mechanical change (the factory extraction) into a diff a reviewer can hold in one glance. C last so the guards land only when there is nothing left to grandfather.

## Acceptance for the step

- `src/interaction` contains only the headless core (barrel + 17 files, no react/three/DOM imports) and is uniformly barrel-guarded like domain/pose/view.
- `src/camera` is barrel-guarded with a three-export surface; all production consumers go through barrels; the only remaining deep imports in the repo are tests (exempt by design).
- The authority cycle is gone; dependency direction is camera -> interaction everywhere.
- Zero behavior change: full suite green at every slice with no test assertions modified (path-only test edits).
