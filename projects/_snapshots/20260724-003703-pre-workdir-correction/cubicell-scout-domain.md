# Scout report: Domain extraction (MODEL.v2 step 1)

Scope: read-only scout of `src/domain/*` for the strangler extraction that
lifts Domain behind a stable contract and evicts the fused camera. Lenses:
reuse/simplification (code-review) + duplication/dead-code/boundary
(code-hygiene). No files modified.

## Premise correction (read first)

The dispatch said "No barrel exists" and "~45 files import via DEEP paths
(e.g. `from '../domain/scene'`)". Neither holds today:

- **A whole-domain barrel already exists**: `src/domain/cubicellScene.ts`
  (`export *` from all ten modules except `cubeGeometry`).
- **47 external files already import through that barrel**; only **13** use
  deep paths, and 6 of those are forced (the barrel omits `cubeGeometry`).

So step 1 is not "introduce a barrel from scratch." It is **curate the
existing `export *` barrel into an explicit contract, rename it to
`index.ts`, and close 13 deep-path bypasses.** The `export *` today leaks the
entire internal surface (~120 symbols) when only **73** are genuinely
consumed outside `src/domain`.

Two naming hazards make the current barrel a de-facto leak:
- `cubicellScene.ts` (the barrel) sits beside `scene.ts` (the aggregate).
  Same word, different jobs. The barrel should become `index.ts`.
- `createCubeFaces` is defined **twice** (`cube.ts` = face *state* record;
  `cubeGeometry.ts` = 3D face *planes*). `cubeGeometry` is excluded from the
  barrel precisely to dodge this collision. Any curated barrel must rename
  the geometry pair before including them.

---

## Reuse Map — the public contract

73 symbols are imported from `src/domain` by code outside it. This is the
exact surface `src/domain/index.ts` should carry. Everything else stays a
module-level `export` (for intra-domain use) but is **not** re-exported.

### cubeTopology.ts (13) — pure topology vocabulary
`Vec3`, `CubeDimensionName`, `CubeSize`, `CubeFaceId`, `CubeFaceName`,
`CubeEdgeId`, `cubeDimensionNames`, `cubeFaceNames`, `cubeEdgeIds`,
`cubeEdgeTopology`, `cubeFaceTopology`, `getCubeDimensionFaceIds`,
`getCubeFaceEdgeIds`

### cube.ts (7)
`CubeCell`, `CubePartColor`, `CubeResizeAnchor`, `getCubeLayerMode`,
`getCubeUniformPartColor`, `getAverageCubeEdgeThickness`,
`getAverageCubeFaceOpacity`

### cubeOperations.ts (3)
`CubeScope`, `SceneOperation`, `applySceneOperation`

### grid.ts (6)
`GridAxisName`, `GridDimensions`, `GridState`, `defaultGridGap`,
`gridAxisNames`, `getGridAxisIndex`

### gridLayout.ts (5)
`CubeLayoutPose`, `SceneGridLayout`, `createSceneGridLayout`,
`isSameCubeLayoutPose`, `getGridStep`

### neighbors.ts (7)
`NeighborFace`, `NeighborSlot`, `getCubeNeighborSlots`, `getSceneShadowShell`,
`getNeighborCubeId`, `placeCubesAt`, `addNeighborCubes`

### scene.ts (12 domain + 2 camera)
Document: `CubicellScene`, `ScenePolarity`, `scenePolarityNames`,
`GridPreset`, `defaultScene`, `getSceneGridDimensions`, `getSceneGridPreset`,
`applyGridPreset`, `cloneGridPreset`, `isSameGridPreset`, `resizeGridScene`,
`getGridDimensionsCellCount`
Camera (LEAK — evict, see below): `CameraState`, `ProjectionMode`

### score.ts (4)
`Score`, `AssemblyTrack`, `emptyScore`, `repairScore`

### selection.ts (11)
`CubeSelection`, `CubePartSelection`, `CubeSelectionKind`,
`CubeSelectionSet`, `SelectionEditTarget`, `createCubeSelectionSet`,
`toggleSelectionInSet`, `convertSelectionToPickMode`, `getSelectedPartIds`,
`isCubeSelected`, `isSameSelection`

### selectionQuery.ts (1)
`resolveSelectionQuery`

### cubeGeometry.ts (2) — RENAME before inclusion
`createCubeEdges`, `createCubeFaces`. Collides with `cube.ts`. Rename on the
way into the contract (e.g. `createCubeEdgeSegments` / `createCubeFacePlanes`)
or keep out of the barrel. See Quality Map.

### Leaks that should NOT be in Domain's permanent contract
- **`CameraState`, `ProjectionMode`** — the fused camera. Evict to the
  view/pose seam (below). They ride the contract only transitionally.
- **`createCubeEdges` / `createCubeFaces` (cubeGeometry.ts)** — these build
  *render geometry* (edge segments, face planes) and are consumed only by
  render code (`scene/cubeInstances.ts`, `scene/AxisHintChrome.tsx`,
  `view/viewportFocus.ts`). Pure today (import only `cube` + `cubeTopology`),
  so they don't break Domain purity, but they are a view concern squatting in
  Domain. Candidate to relocate to a `view/`-side geometry module in a later
  slice; at minimum, keep them out of the general Domain contract.
- `defaultScene`, `emptyScore` — legitimate composition-root seeds. Keep.

---

## Quality Map

### Boundary
- **Domain is renderer-pure**: zero `three` / `react` / `@react-three` / DOM
  references anywhere under `src/domain`. Confirmed. The lift is safe.
- The only boundary defect is the **leaky `export *` barrel** + 13 deep-path
  bypasses. Curating `index.ts` and repointing closes it.

### Deep-path bypasses to repoint (13 files)
- `src/anim/scoreAt.ts`, `src/anim/useTransportMoment.ts` — deep into
  `scene`, `score`, `cube`, `cubeTopology`, `gridLayout`.
- `src/scene/cubeInstances.ts`, `src/scene/useCubeSceneInstances.ts`,
  `src/scene/useStableGridLayout.ts`, `src/scene/AxisHintChrome.tsx` — deep
  into `gridLayout` and `cubeGeometry`.
- `src/view/viewportFocus.ts` — deep into `gridLayout`, `cubeGeometry`.
  (6 of these are forced by the `cubeGeometry` omission; fixing the barrel
  fixes them.)

### Duplication
- **`createCubeFaces` name collision** (`cube.ts` vs `cubeGeometry.ts`). Not
  behavioural duplication (different return types) but a genuine vocabulary
  clash that blocks a clean barrel. Resolve by renaming the geometry builders.

### Dead code (8 exports, defined with zero references anywhere in `src`)
`CubeTarget` (cubeOperations), `areAllCubeEdgesVisible`,
`areAllCubeFacesVisible`, `setCubeEdgesVisible`, `setCubeFace` (cube),
`createCubeLattice`, `createFilledGridScene` (scene), `defaultGridState`
(grid).
Treat as grooming *candidates*, not automatic deletions: per the repo lesson
"audit dead metadata may be regression," run `git log -S <symbol>` on each
before removing — some (`createFilledGridScene`, `createCubeLattice`) read
like intended-but-unwired API.

### oxlint boundary enforcement
Config (`.oxlintrc.json`) is minimal: plugins `react`/`typescript`/`oxc`,
two react rules. oxlint 1.72.0. **Recommended enforcement**: add core
`no-restricted-imports` with a `patterns` group forbidding `**/domain/*`
(deep) while allowing `**/domain` (the barrel). Domain's own intra-imports use
relative `./cube` and won't match a `domain/` pattern, so no per-directory
override is needed. Verify oxlint's `no-restricted-imports` honours the
`patterns`/`group` option at 1.72; if not, fall back to a one-file boundary
test (a vitest that greps the tree for `from '.*domain/<file>'`). Either is
cheap; prefer the lint rule so it fails in the existing `oxlint` script.

---

## Camera eviction

**Recommendation: split `CameraState`; the pose seed goes to `src/view`
(alongside `viewPose.ts`), the projection stays a Document property.**

Traced consumers justify the split:

- `camera` is a field of the **`CubicellScene` aggregate** (`scene.ts:31`),
  seeded by `defaultCamera` (`scene.ts:44-55`). This is the fusion MODEL.v2
  flags.
- **Only `.projection` is ever read or written after seeding**: `useEditorCommands`
  (projectionRef), `editor/controlBindings`, `panels/SceneSection`,
  `scene/CubeScene`, and the `set/toggle-camera-projection` ops in
  `cubeOperations.ts`. Projection is genuinely persisted document state
  (panel-editable, in history/snapshot). **It must stay document-owned.**
- **The pose fields (`position`/`target`/`up`/`zoom`) are a static seed** that
  the document never mutates. Their only readers are `view/viewportFocus.ts`
  and `view/viewPose.ts` via `getInitialCameraOffset(scene.camera)`. This is
  the "stage-owned camera": it belongs with the pose math in `src/view`.
- **`CameraState` / `ProjectionMode` types** are consumed broadly by
  `src/interaction/*` (authority, CameraDriver, morph, snapshot,
  cameraProjectionSwap, interactionCore, …) and `src/view/viewPose.ts`.
  MODEL.v2 layering puts "pose math" below interaction ("interaction depends
  on domain and pose math only"), and `viewPose.ts` already consumes both
  types. So the pose-math seam in `src/view` is the correct low home; both
  interaction and view import from there.
- **`defaultCamera` and `setSceneCameraProjection` have no external
  consumers** (`defaultCamera` → only `defaultScene`; `setSceneCameraProjection`
  → only `cubeOperations`). `defaultCamera` moves with the pose seed to view;
  `setSceneCameraProjection` stays in Domain but reduces to a projection-field
  mutation (rename `setSceneProjection`).

**Why not the other candidates:**
- *A new `src/camera` context*: over-fit. The camera has two owners already
  (Document owns projection, View owns pose). A third context would fragment
  them.
- *`src/interaction`*: interaction owns the *live* camera authority but sits
  *above* pose math in the layer order. Putting the shared types there forces
  view→interaction dependency inversion. The types belong at the pose-math
  level, which is `src/view`.

**Coupling that makes eviction non-trivial (flagged):**
1. `CameraState` is aggregate state. You cannot move the type to `src/view`
   while `CubicellScene.camera: CameraState` remains, or Domain imports up
   into View (layer violation). The eviction therefore requires **reshaping
   the aggregate**: replace `camera: CameraState` with `projection:
   ProjectionMode` on `CubicellScene`, and relocate the pose seed
   (`defaultCamera`) to view. This touches `defaultScene`, snapshot/history
   serialization, and every `scene.camera.projection` reader (5 files).
2. Projection is persisted and user-editable — do **not** evict it; only the
   pose leaves. Getting this wrong would drop projection from history.
3. Clean news: **`scoreAt` / Evaluation never read camera** (verified), and
   `resizeGridScene` / grid never touch it. The camera is isolated to the
   scene aggregate field + the pose readers, so the blast radius is bounded.

One-line home recommendation: **pose seed + `CameraState`/`ProjectionMode`
types → `src/view` (pose-math seam beside `viewPose.ts`); projection stays a
Document field.**

---

## Plan (ordered, bound to the contract)

1. **Curate the contract.** Create `src/domain/index.ts` re-exporting exactly
   the 73 public symbols (grouped as above). Leave module `export`s intact for
   intra-domain use; stop leaking internals. Do **not** delete
   `cubicellScene.ts` yet — make it re-export `index.ts` as a shim.
2. **Resolve the `createCubeFaces` collision.** Rename the `cubeGeometry`
   builders (`createCubeEdgeSegments` / `createCubeFacePlanes`) and repoint
   their 3 consumers, so the geometry pair can enter the contract (or stay
   deliberately out).
3. **Close the 13 deep bypasses.** Repoint `anim/*`, `scene/*`, `view/*` to
   the barrel. The 6 `cubeGeometry`-forced ones resolve once step 2 lands.
4. **Add the boundary guard.** `no-restricted-imports` pattern forbidding
   `**/domain/*` (allow `**/domain`) in `.oxlintrc.json`; fallback boundary
   test if the option is unsupported at oxlint 1.72.
5. **Retire the shim.** Delete `cubicellScene.ts`, repoint its 47 importers to
   `domain` (barrel). Rename resolves the `scene.ts`/`cubicellScene.ts`
   confusion.
6. **Camera eviction (separate slice).** Reshape `CubicellScene` to
   `projection: ProjectionMode`; move `CameraState`/`ProjectionMode`/pose seed
   to `src/view`; rename `setSceneCameraProjection` → `setSceneProjection`;
   repoint the 5 `scene.camera.projection` readers and the interaction/view
   type importers. Acceptance: projection still round-trips through
   history/snapshot; live camera authority unchanged.
7. **Groom (optional, gated).** `git log -S` the 8 dead exports; delete those
   with no lost-feature history.

Acceptance test for the whole extraction (per MODEL.v2 line 352): the three
Moment staging clauses in `CubeScene`'s four consumers still hold — presence-
zero cells absent downstream, arriving cells scale via `applyMomentToLayout`,
arrived pose refs referentially stable.
