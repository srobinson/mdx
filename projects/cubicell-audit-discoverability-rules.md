# Cubicell audit: discoverability and rules

Auditor 3. Snapshot `9f766b2` (worktree `shapes`, identical to main per brief).
Read-only pass. Goal: cold-start discoverability, current doc truth, and the
smallest enforceable rule set that would have blocked the real failure history.

---

## Part 1. Cold start

### Method

Started at repo root with only README and directory names. Traced one user
gesture through durable state and back to pixels without prior session memory.
Logged where the trail broke.

### Path a newcomer can find

| Surface | What it seems to answer |
| --- | --- |
| `README.md` | How to run and which keys move the camera |
| `PRODUCT.md` | Product identity and principles |
| `ARCHITECTURE.md` | Claimed source map and ownership |
| `src/main.tsx` | Browser entry |
| `src/domain/` | Cube, scene, selection vocabulary |
| `src/panels/`, `src/controls/view/` | Visible UI |
| `src/scene/CubeScene.tsx` | Canvas and Three objects |

From README alone you learn controls and panel placement. You do not learn the
command bus, durability pipeline, or that live camera pose is not workbench
state.

### Gesture → durable state → screen (reconstructed)

**Boot**

1. `src/main.tsx` → `beginRouteLoad` (`src/studios/catalog.ts`) → lazy
   `EditorStudio` + `SharedRendererModule`.
2. `AppBootstrap` → `StudioHost` → studio `Studio` waits on
   `hydrationStatus !== "loading"`.
3. Store construction is `createCubicellStore` (`src/state/cubicellStore.ts`)
   with IndexedDB project storage and preference port. Authored edits later
   flow through `createAuthoredDispatcher` into
   `projectDurability.enqueue`.

**Document edit (example: structure mutation via command)**

1. UI: panel control or keyboard shortcut emits an `EditorCommand`
   (`src/editor/commands.ts`, affordances in `src/editor/affordances.ts`).
2. Keyboard entry is `KeyboardShortcuts` → held-input helper →
   `runEditorCommand` from `useEditorCommands`.
3. `createInteractionCore.dispatch` → `createIntentBus`:
   - non-view commands run synchronously through the registry
     (`src/interaction/commands/registry.ts` + kind files under
     `src/interaction/commands/`);
   - view commands are accepted into a frame drain for the camera authority.
4. Document kinds call ports on `useSynchronousEditorCommands`, which bind
   store methods (`dispatchAuthoredEdit`, selection setters, transport, mode).
5. Durable authored path:
   `dispatchAuthoredEdit` → `createAuthoredDispatcher` →
   `reduceAuthoredOperationState` → workbench update +
   `authoredSceneJournal` append → `durability.enqueue` → IndexedDB outbox /
   commit path under `src/persistence/` and `src/state/projectDurability.ts`.
6. Screen:
   - staged view: `useStagedScene` / `createStagedSceneReader` from
     `src/transport/stagedScene.ts` (not a file named `useStagedScene.ts`);
   - canvas: `EditorRendererBinding` → shared `CubeScene` →
     instanced meshes + chrome;
   - incremental patches: `useAcceptedAuthoredSceneChanges` drains the
     journal into the scene owner.

**Selection (session, not durable authored)**

1. Canvas part pointer: `InstancedPartMesh` / face handlers in `CubeScene` →
   `sceneSelectionGesture` → `onSelectionChange`.
2. `useSceneOperations.updateSelection` → `createSelectCommand` → bus →
   `selection.commands` → `ports.selection.setSelection` →
   `createSelectionActions` / `commitSelectionEditor` on `editor` session
   state.
3. Screen: `usePresentedSelection` + `SelectionChromeLayer`.

Selection is load-bearing and easy to misfile as "document state". It lives
on the editor session; it is not the durability journal path.

**Camera (live pose, also not workbench)**

1. Pointer rotate / pan / wheel: `CameraDriver` +
   `cameraGestureRuntime` / Trackball adapters.
2. Keypad and arrow view commands: bus view lane →
   `cameraAuthorityRuntime` single writer →
   `cameraFrameWriter` / `resolveFrameInto` → Three camera.
3. Projection mode *is* document scene state; live pose is interaction-core
   authority state. `CameraTrack` possession APIs exist under
   `src/camera/cameraTrackAuthority.ts` but no production studio mounts
   `CameraTrackControls` or feeds authored samples into the scene.

### Where the cold start actually got lost

1. **No `App.tsx`.** Entry is `AppBootstrap` + studio host. Grepping for App
   wastes the first minutes.
2. **ARCHITECTURE names `src/transport/useStagedScene.ts`.** The symbol is
   `useStagedScene` exported from `src/transport/stagedScene.ts` via
   `src/transport/index.ts`. The doc points at a file that does not exist.
3. **Two edit paths with no single arrow diagram.** Most work goes command →
   bus → ports → store. Neighbor placement, grid composer rebuilds, visibility
   toggles, and preference toggles still hit store actions directly
   (`useSceneOperations` and related). ARCHITECTURE admits this in prose; the
   tree does not.
4. **Three "state" homes.** Workbench / project durability, editor session
   (selection, transport playhead, hover), and camera authority pose. Nothing
   at the root says "do not look for camera pose in zustand".
5. **Side-effect registration.** `registerAllCommands()` runs at
   `EditorStudio` module load. Command behavior is invisible until you open
   the registry files.
6. **Dead studio surface looks real.** `src/studio/CameraTrackControls.tsx` is
   exported from `src/studio/index.ts` and tested, but never mounted under
   `src/studios/editor/`. A newcomer treats it as a live panel.
7. **Doc pile without a map.** Root has many large contracts
   (`MODEL.v2.md`, `INTERACTIVE.md`, `ANIMATION.md`, `CAMERA.md`,
   `STORAGE.md`, …). There is no `MAP.md` and README does not order them. The
   first useful ownership list is deep inside `ARCHITECTURE.md`, which is also
   the first place that can lie.
8. **Persistence is a second graph.** After finding `cubicellStore`, the path
   to IndexedDB still requires `projectDurability`, codecs under
   `src/persistence/recordCodecs`, and hydration workers. STORAGE.md is the
   target model; the runtime entry is the store factory options.

### Entry points: found vs load-bearing but invisible

| Visible to a cold reader | Load-bearing and easy to miss |
| --- | --- |
| `src/main.tsx` | `beginRouteLoad` / `StudioHost` lifecycle |
| `CubeScene`, panels, keypad | `createInteractionCore` + `createIntentBus` |
| `src/editor/commands.ts` kinds | `src/interaction/commands/*.commands.ts` `run` bodies |
| `useCubicellStore` usage in UI | `createAuthoredDispatcher` + durability enqueue |
| `CameraDriver` in the scene tree | View-lane drain and authority possession |
| `src/domain/cameraTrack.ts` types | Absence of production sampler and unmounted controls |
| README key list | `KeyboardShortcuts` capture-phase document listeners |
| `src/persistence/` directory | That hydration must complete before `EditorApp` mounts |

### File that should have existed

A short root **runtime map** (one page, not another architecture novel):

- boot: `main` → catalog → studio → store hydration → first committed frame;
- input classes: document command, view command, direct store exception list,
  camera gesture;
- three state homes: workbench durable, editor session, camera authority;
- render: staged scene + journal → `CubeScene` instances;
- explicit "not user reachable" list (today: `CameraTrackControls`, camera
  track evaluator).

That file would have prevented most of the grepping above. ARCHITECTURE tries
to be this and fails when paths rot.

---

## Part 2. Doc truth

Method: treat every checked claim as false until a path or symbol in `src/`
confirms it. Spot-check only; not a full doc audit.

### Surviving lies or stale facts

| Claim | Reality | Verdict |
| --- | --- | --- |
| `ARCHITECTURE.md` references `src/transport/useStagedScene.ts` | Symbol lives in `src/transport/stagedScene.ts`; no `useStagedScene.ts` file | **Lie / rot** |
| `ARCHITECTURE.md` snapshot stamp `71098b4` (2026-07-29) | Worktree HEAD `9f766b2` | **Stale stamp** (content may still be mostly true) |
| `PERFORMANCE.md` P1 "Demand driven rendering": Canvas uses continuous frame loop at 120 fps | `CubeScene` sets `frameloop="demand"`; `RenderScheduler` / `RenderSchedulerDriver` own invalidation | **Stale open P1; finding is false today** |
| `PERFORMANCE.md` P1 "Initial delivery" finding: `main.tsx` statically imports design system; no lazy boundary under `src` | `main.tsx` has no design-system import; catalog lazy-loads studios; multiple dynamic imports exist | **Stale finding** (later Slice text partially corrects, but the open P1 finding still states the old world) |
| `PERFORMANCE.md` cites `src/state/debouncedJsonStorage.ts` and `src/state/wireEncode.ts` | Neither file exists under `src/state/` (old persistence design; replaced by IndexedDB project storage) | **Phantom paths** |
| `CAMERA.md`: "The inspector reads the same `CameraTrack` the evaluator samples" | No `sampleCameraTrack` / evaluation module; `CameraTrackControls` unmounted; only tests drive track UI | **Lie: implies a live authoring/playback loop** |
| Approved edge `shapeSize` / `CubeEdgeTreatment` (design + `TYPOGRAPHY.md`) | Zero occurrences in `src/`; `CubeEdgeState` is only `color`, `opacity`, `thickness`, `visible` (`src/domain/cube.ts`) | **Approved design absent from code** (TYPOGRAPHY already admits absence; still a process failure) |

### Claims that are currently true (and useful)

| Claim | Evidence |
| --- | --- |
| `CameraTrackControls` is not mounted in production studios | Component under `src/studio/`; only test import outside its module; `ANIMATION.md` / `STUDIO.ANIMATION.md` / `INTERACTIVE.md` all state this honestly |
| Camera track possession runtime exists | `beginCameraTrackPossession`, `setCameraTrackPose`, `rearmCameraTrackFollow` in `src/camera/cameraTrackAuthority.ts` / `cameraAuthorityRuntime.ts` |
| Demand-driven canvas infrastructure exists | `frameloop="demand"` + `src/scene/renderScheduler.ts` |
| `PERFORMANCE.md` P1 GPU capacity marked COMPLETE (#116) | Section titled complete; matches brief's historical P1 example being fixed |
| Budget gate exists and ratchets gzip ceilings | `budgets/initial-delivery.json` + `scripts/check-delivery-budget.mjs` + `.github/workflows/delivery-budget.yml` |
| CI merge signal is budget-only | `WARROOM.md`; workflow tree only ships `delivery-budget.yml` |

### Partial / nuanced

- **Camera track docs are split-brained.** `ANIMATION.md` and `INTERACTIVE.md`
  correctly park the feature. `CAMERA.md` still describes an inspector and
  evaluator as present tense product surface.
- **PERFORMANCE.md** mixes completed work, historical findings, and open P1s
  without a consistent "status" field. Readers cannot trust section headers
  alone; the demand-driven and initial-delivery openings are the worst traps.
- **ARCHITECTURE.md** remains the best cold map when paths resolve; the
  missing `useStagedScene.ts` path is enough to burn trust on first use.

### Doc rule of evidence used here

Every path in backticks was resolved on disk. Every "user can" claim was
checked for a production mount or production caller, not only for a type or
test.

---

## Part 3. Rules

Derived only from the brief's real failure history. Each rule is one sentence
plus enforcement. A rule without a person or gate check is rejected.

1. **Invariant-bearing tests may not be deleted or rewritten away in the same change that alters the production path they guard unless the same invariant is reasserted at the nearest executable production layer with recorded red-before evidence.**  
   *Prevents:* rewrite ships green after deleting the tests that would have caught the break.  
   *Enforcement:* **review checklist** (diff must show replacement assertion + red-before); optional **CI** script that fails when test files under `tests/` are deleted without a paired addition that references the same invariant tag.

2. **A regression gate is valid only if deleting or bypassing the production fix turns that gate red; tests that inject a test-owned applier, harness, or mock in place of the production handoff do not count as coverage for that fix.**  
   *Prevents:* three reviewers clear a fix whose suite stays green after the production code is removed.  
   *Enforcement:* **CI** controlled-red proof (mutate or strip the production path in a job or local required script) plus **review checklist** ("name the production symbol under test").

3. **Any React effect whose cleanup disposes a shared input or render resource must recreate that resource in setup, and input-critical slices must be proved on both `pnpm dev` (Strict Mode double mount) and `pnpm preview` (production bundle).**  
   *Prevents:* dispose-only effect passes production smoke while dead camera, numpad, and keyboard ship in dev.  
   *Enforcement:* **review checklist** + **discipline/integrator seat** for dual-surface proof; strengthen to **CI** with a Chromium test that mounts the production tree under Strict Mode and asserts listeners or controls are alive after the second mount.

4. **Gate green is only the raw command output from a re-run by someone other than the author (integrator or CI artifact); builder self-report of `pnpm test` / `pnpm test:browser` is not a merge signal.**  
   *Prevents:* self-reported browser green on a SHA that is deterministically red twice for a reviewer.  
   *Enforcement:* **discipline** in warroom process; **CI** where the suite can run (today browser is local-only, so the human integrator rule remains mandatory until CI owns the same command).

5. **Every delivery budget ceiling in `budgets/initial-delivery.json` must be re-baselined to the measured gzip value at zero intentional headroom whenever bytes move; the checker must fail both over-budget and over-slack.**  
   *Prevents:* ~9.8 KB silent headroom masking a regression of that size.  
   *Enforcement:* **CI** (extend `check-delivery-budget.mjs` to fail when `limit - measured` exceeds a fixed zero or single-byte tolerance); until that lands, **review checklist** on any budget file edit. Today the script only ratchets upward overages, so zero-headroom is not yet machine-enforced.

6. **An approved product field or type name that is claimed implemented, or left as an accepted decision without an explicit parked marker, must have at least one `src/` occurrence and one failing-or-passing test that names it; otherwise CI or review fails the claim.**  
   *Prevents:* `shapeSize` / `CubeEdgeTreatment` approved with zero `src/` hits and nobody noticing.  
   *Enforcement:* **CI** inventory (decision table or design IDs → required symbols; `rg` gate) and **review checklist** for design-implementation PRs; docs that say "approved" without "parked / not in src" are defects.

7. **Production-reachable UI requires a production mount or production caller; a component that exists only under `src/` plus tests is dead until a studio or capability mounts it, and docs must not describe it in present-tense user language.**  
   *Prevents:* camera track, and the class of "built but unreachable" features, shipping as if live (reviewers clear types and unit tests while users cannot enter).  
   *Enforcement:* **review checklist** ("show the mount site"); optional **CI** that flags exported studio panels never imported from `src/studios/**`.

8. **Feel-critical browser behavior (canvas input, camera, drag, recording) must have at least one test or integrator proof that drives the production component tree, not only unit pure functions.**  
   *Prevents:* correlated code review missing runtime death; complements rules 2 and 3.  
   *Enforcement:* **CI** for automated cases under `tests/**/*.browser.test.ts`; **discipline** for live UX gate before merge when automation cannot feel.

### Mapping failures → rules

| Historical defect | Rule(s) |
| --- | --- |
| Rewrite deleted invariant tests, shipped green | 1 |
| Fix + three reviews; delete production fix, suite still green | 2, 8 |
| Dispose-only effect; Strict Mode; dead input in dev | 3, 8 |
| Builder self-reported browser green; reviewer red | 4 |
| Budget bucket ~9.8 KB unclaimed headroom | 5 |
| Approved `shapeSize` / `CubeEdgeTreatment` absent from `src/` | 6 |
| Dead camera track / unmounted controls cleared as if live | 7, 2 |

### Smallest set note

Rules 1–6 are the direct answers to the brief's six bullets. Rules 7–8 are
the minimum additions that make 2 and 3 checkable for this codebase's actual
dead-feature and feel-critical patterns; without them, "production path" stays
ambiguous in review.

### What is not a rule (rejected)

- "Reviewers should be careful" without a checklist item or gate.
- "Keep docs updated" without path verification or a mount-site requirement.
- "Prefer good architecture" without a named symbol or command that can fail.

---

## Appendix. Cold-start command for the next agent

```text
main.tsx
  → studios/catalog.beginRouteLoad
  → studios/editor/EditorStudio (registerAllCommands)
  → state/cubicellStore + projectDurability
  → app/useEditorCommands → interaction/interactionCore + bus
  → interaction/commands/* → state actions
  → transport/stagedScene.useStagedScene
  → scene/CubeScene + camera/CameraDriver
```

If a path in ARCHITECTURE.md 404s, trust `src/**/index.ts` barrels and the
symbol, not the path string.
