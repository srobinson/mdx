# Cubicell Scout & Plan — Interaction / Camera / State Model

Read-only audit, 2026-07-08. Repo `cubicell`, main `71fb3f3`, tree pristine.
Yardstick: **P** (projection toggle) is well-modeled — one store truth
(`scene.camera.projection`) observed by the driver, driving a dedicated morph
axis, never entering the coalescing view lane. **F** (focus toggle) is the
reference-bad — two truths that must agree, a stateful toggle smuggled through
the absolute coalescing lane. Everything below is ranked by how badly the
entity is mis-homed, worst first.

## Quality Map (ranked, worst first)

1. **Focus toggle (the F entity itself)** | smell: duplicated-state + wrong-lane | `store editor.selectionFocusActive` (`state/cubicellState.ts:118`, setter `state/cubicellStore.ts:238`) + core `ViewState.focusSnapshot` (`view/viewState.ts:11`); classified absolute in `interaction/command.ts:13` `isAbsoluteViewCommand`; folded last-wins in `interaction/viewLane.ts:24` (`coalesced.absolute = view`) | Two sources of truth for one boolean; the durable half (`focusSnapshot`) rides the absolute lane that drops all-but-last, so a second absolute in the same frame silently discards the toggle. Live workaround: the `focusedSelectionKeyRef` seed in `app/useSelectionFocusCommands.ts:94-100`. | severity: blocker

2. **Focus/reset framing semantics homed in React hooks, not the core** | smell: blurred-seam | `createSelectionFocusTarget` + focus-follows-selection effect `app/useSelectionFocusCommands.ts:49-148`; `createResetTarget` reads `window.innerWidth/Height` `app/useSynchronousEditorCommands.ts:161-182` | The camera's focus/reset target math lives in `src/app/*` hooks that read the DOM and the store, so a headless actor (LLM, test) calling `core.dispatch(focus-toggle)` cannot actually focus — the target is computed in a React closure it can't reach. Violates invariant 6 (core is React/DOM-free) and invariant 3 (no privileged path), the founding "LLM as first-class user" goal. | severity: major

3. **`isAbsoluteViewCommand` conflates idempotent framings with a stateful toggle** | smell: miscategorized | `interaction/command.ts:13-19` buckets `focus`, `reset`, `toggle-focus` all as "absolute" | Last-wins coalescing is correct for `focus`/`reset` (idempotent, order-free) but wrong for `toggle-focus`, whose outcome depends on prior state and count. This miscategorization is the *root* of finding 1; the seed workaround treats the symptom. The deep fix is that a toggle is not an absolute. | severity: major

4. **`reset` bifurcated across two lanes via a two-hop trampoline** | smell: wrong-lane + blurred-seam | `reset` with `target===null` → synchronous lane (`interaction/command.ts:34-38` `isSynchronousViewCommand`); with a target → absolute view lane (`:15`); the `0`/`5`/numpad keys dispatch reset-null (`editor/keyboard/keymap.ts:13,18`), which `app/useSynchronousEditorCommands.ts:119-131` handles by flipping `setSelectionFocusActive(false)` and *re-dispatching* `createResetViewCommand(target)` back into the view lane | One command kind splits across two lanes by payload nullness, then launders itself from the synchronous lane back into the view lane through a hook — the same two-truth, two-lane shape as F. | severity: major

5. **`selectionFocusActive` has many writers and no owner; `resetEditorSession` desyncs it from `focusSnapshot`** | smell: duplicated-state | store flag written by ≥4 paths — `toggleSelectionFocus`, focus-follows-selection effect `app/useSelectionFocusCommands.ts:118`, reset branch `app/useSynchronousEditorCommands.ts:120`, `createInitialEditorSession` `state/cubicellState.ts:164`; core `focusSnapshot` written only by `reduceViewState` | `resetEditorSession()` (wired to the Reset button, `panels/SceneSection.tsx:169`) sets the store flag false but dispatches **no** view command, so core `focusSnapshot` survives: store says "not focused", core still holds a focus snapshot. Concrete latent desync. | severity: major

6. **`toggle-focus` behavior smeared across five modules** | smell: blurred-seam + duplication | handled in `view/viewState.ts:37` (`reduceFocusToggleViewState`), `view/viewPose.ts:149`, `motion/cameraMotion.ts:48`, classified in `interaction/command.ts:17`, and excluded in `editor/commands.ts:246` `canRepeatViewCommand` | The one "focus" concept has no owning module; five files must each special-case it. Contrast P: projection lives cohesively in `domain/scene.ts` + `interaction/morph.ts`. | severity: minor

7. **`cameraDriverRuntime.ts` at 695 LOC, five lines under the hard 700 ceiling** | smell: oversized + duplication | `interaction/cameraDriverRuntime.ts` (695 LOC); duplicate `isPerspectiveCamera`/`isOrthographicCamera` in both `:689,:693` and `interaction/cameraDriverMath.ts:106`; near-duplicate reduced-motion instant-swap blocks `:544-554` vs `:592-602`; `morphFromOrthographicToPerspective:618-653` hand-builds a `PerspectiveCamera` instead of reusing `buildProjectionCamera`; `cancelTrackballMomentum:671-683` casts to reach private `_lastAngle/_panStart/...` | CLAUDE.md hard rule: files over 700 must be refactored before adding code; this file is one edit from breaching and already carries the SceneControls+ProjectionCamera merge. Duplication and private-field reach-ins are merge leftovers. | severity: major

8. **Snapshot `selection` is untyped `unknown` and inertly plumbed** | smell: dead-code + blurred-seam | `interaction/snapshot.ts:12` `SelectionPort = () => unknown`, `:19` `selection: unknown`; fed `selectionSnapshotRef` `app/useEditorCommands.ts:33,42` but never read by the camera path | Invariant 5 says the snapshot is the serializable read model an actor asserts on; `selection` is an untyped hole and currently dead wiring (the driver reads only `.morphing`/`.poseMode`). | severity: minor

9. **`cameraAuthorityRuntime.ts` re-threads `focusSnapshot` 6× and carries dead/parallel bookkeeping** | smell: duplication + dead-code | `interaction/cameraAuthorityRuntime.ts` (622 LOC): `createViewStateFromPose(pose, state.viewState.focusSnapshot)` boilerplate at 6 settle sites (L148,296,304,358,423,458); dead `_nowMs` param in `clearCameraAuthorityHold` (L345); parallel `orbitDetentProgress` + `orbitMotion` fields kept in sync by hand; 3× identical `orbitDetentProgress` construction | The 6× manual re-threading is direct evidence `focusSnapshot` is a bolted-on field, not a modeled axis: every pose settle must remember to carry it or lose focus. | severity: minor

## P-vs-F verdict per finding

1. Focus toggle — **pure F.** Two truths, absolute coalescing lane, live workaround. This is the reference case.
2. Focus/reset framing in hooks — **F.** No headless home; the capability is unreachable through the pure core seam, the opposite of P (which any actor toggles via one store field).
3. `isAbsoluteViewCommand` — **F.** The classification is the mechanism that makes focus behave unlike P; fix it and F can become P-shaped.
4. `reset` trampoline — **F.** Same two-lane, two-truth laundering as focus; reset has no clean home either.
5. `selectionFocusActive` writers — **F.** Duplicated state with no single writer; P has exactly one writer (`updateScene` → `scene.camera.projection`).
6. `toggle-focus` smear — **leans F.** Scattered ownership; P’s projection is cohesive.
7. `cameraDriverRuntime` size — **P-adjacent, hygiene only.** The driver *is* the well-modeled P machinery; the issue is LOC/duplication, not mis-homing.
8. Snapshot `selection` — **neither cleanly.** A half-built read-model seam; not wrong-lane, just incomplete and untyped.
9. Authority bookkeeping — **hygiene only.** Symptom of finding 1 (focusSnapshot has no real home), not an independent mis-home.

## Notes (checked and rejected as fine)

- **Projection (P) toggle** — confirmed well-modeled. `p` key → `toggle-camera-projection` scene op (`editor/commandRegistry.ts:209`) → synchronous lane → `updateScene` flips the single store truth `scene.camera.projection`. Driver observes it as a prop (`CameraDriver.tsx` → `useProjectionCameraSwap`), drives `beginMorph`/`advanceMorph` on the dedicated axis, commits the swap via `takePendingProjectionSwap` (`cameraDriverRuntime.ts:299,311-315`). Never touches `dispatch`/coalesce. One truth, one writer, dedicated axis. The yardstick’s positive pole.
- **Transport (playing/loop/timeMs)** — rejected as a finding. Store-owned in `editor.transport` and *observed* by `anim/TransportDriver.tsx` and `anim/useTransportMoment.ts` via store subscription. This is the same clean observe-a-store-field pattern as P, not a second source of truth. Possession mode is explicitly deferred past slice one.
- **Pose axis vs morph axis being two entry points** (`advance` vs `advanceMorph`, `cameraAuthorityRuntime.ts:79-81`) — rejected. The authority stays headless with two entries by design; the *single* per-frame writer that composes both onto the render camera is `cameraDriverRuntime.ts:composeCameraWrite` (:302), gated off during gesture (:301). Invariant 1 is upheld structurally by the driver.
- **Gesture inversion** (trackball leads, core mirrors) — rejected as by-design per invariant 2. Residual note only: `panCameraByScreenDelta:490` mutates `camera.position` directly and `mirrorPose` reads it back, making the camera the momentary truth mid-pan; deliberate, and the per-frame writer yields during gesture, so no double-write.
- **Snapshot pose composition** (`snapshot.ts:composeSnapshot`) — fine. Pose/mode/projection come from the authority, selection is joined at the boundary exactly as INTERACTIVE.md prescribes; only the `unknown` typing (finding 8) is weak.
- **Core headlessness** — verified clean: `cameraAuthorityRuntime.ts` and `cameraDriverRuntime.ts` import no `react`/`zustand`/`../state` (driver store reads are isolated to the R3F wrapper `CameraDriver.tsx`). Dependency direction (invariant 6) holds for the core proper; the leak is upward into the app hooks (findings 2, 4).
