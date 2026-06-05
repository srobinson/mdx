# Scout: seeded stencil selection vs project Library

Branch: `feat/stencil-build` @ `66b4d8d` (worktree dirty; committed tree only via `git show` for dirty paths).

Problem: selecting a bundled seeded stencil renders the face figure but never adds the `StencilAsset` to the project Library.

---

## 1) Owning symbol for adding an asset to the project Library

### Library shape and readers

| Role | File | Symbol |
|------|------|--------|
| Library type / empty seed | `src/domain/workbench.ts` | `Library`, `emptyLibrary`, `createDetachedWorkbench` |
| Stencil lookup | `src/domain/workbench.ts` | `findStencilAsset` |
| Project roster from library | `src/domain/workbench.ts` | `getProjectAssetRoster` (includes `library.stencils`) |
| Manifest merge of roster into project | `src/domain/project.ts` | `reconcileProjectAssets` |

### Who writes `library.stencils` today

| Path | File | Symbol | When |
|------|------|--------|------|
| Hydration materialize | `src/persistence/projectRecordHydration.ts` | `materializeLibrary` / asset decode into `stencils` | Load from storage records |
| Lazy load merge | `src/state/projectAssetLibrary.ts` | `mergeProjectAssetLibrary` | `loadProjectAsset` after decode |
| Load action | `src/state/actions/projectAssetActions.ts` | `createProjectAssetActions` → `loadProjectAsset` | Runtime asset fetch |
| Validation restore | `src/state/workbenchValidation/aggregate.ts` | `readStencils` | Persisted workbench parse |
| Encode for commit | `src/persistence/projectRecordProjection.ts` | `projectWorkbenchRecords` + `findStencilAsset` + `encodeStencilRecord` | Only if roster + library already hold the asset |

**Authoring-time writer for stencils: none.**

Compare sibling asset kinds that *do* author into the Library:

| Kind | File | Symbol | Op kind |
|------|------|--------|---------|
| Animation insert | `src/domain/workbenchOperations.ts` | `createAnimationAsset` via `applyDocumentOperation` | `create-animation-asset` |
| Animation project append | `src/state/actions/authoredReducer.ts` | `applyProjectBody` | same |
| Animation storage insert | `src/state/projectStorageChangeSet.ts` | `insertedAssetId` | same |
| Structure insert | `src/domain/structureOperations.ts` | capture / structure create paths | `capture-state` etc. |

`mapLibraryAsset` in `workbench.ts` only maps `"animations" | "structures"`; stencils have no map/create helper there.

### Who wins today

- **Authoring selection of a seeded stencil:** nobody writes Library; face figure state alone changes.
- **Load/hydrate:** `mergeProjectAssetLibrary` / `materializeLibrary` own `library.stencils` by id replace.
- **Commit projection:** roster is derived from Library via `getProjectAssetRoster`; if Library never gained the stencil, project assets and stencil records never appear (`assertCompleteProjection` / `encodeStencilRecord` only emit what Library already holds).

---

## 2) Path: seeded-stencil selection → face render (and where Library insert should land)

```
FaceSection (panelDefinitions face.stencil)
  → ControlBindingField / useControlBinding.setValue
  → faceStencilBinding.createCommand  (src/editor/controlBindings.ts)
       findSeededStencil(value)
       createSceneEditorCommand({
         kind: "set-face-state",
         patch: { figure: { ...defaultFigure, stencilId: asset.id } } | null
       })
  → EditorCommand kind "scene"
  → dispatchAuthoredEdit({ family: "scene", operations: [set-face-state] })
  → reduceAuthoredOperationState
       applyAuthoredBody → applySceneOperation → applyCubeOperationToCell
       → setCubeFaceState (cube face figure only)
       → updateWorkingScene  (workingPose; library untouched)
       applyProjectBody for scene family returns project unchanged
  → Render (independent of Library):
       CubeScene / createStencilAtlas (src/scene/stencilAtlas.ts)
       slotByStencilId built from seededStencils
       createCubeSceneInstances carries face.figure
       writeFaceStencilAttribute / getStencilAtlasSlot(stencilId)
       rasterize from seededStencils[].source (not from Library)
```

**Where Library insertion should have happened**

At the moment selection resolves a `SeededStencil` and commits a non-null figure:

1. **Primary seam:** `faceStencilBinding.createCommand` already holds `stencil.asset` via `findSeededStencil`. That is the first (and only) authoring site that knows which `StencilAsset` was chosen.
2. **Domain apply seam (parallel to animation):** a document op sibling of `create-animation-asset` applied so `workbench.library.stencils` and `project.assets` update under the same durability rules as other Library assets (`applyDocumentOperation`, `applyProjectBody`, `insertedAssetId`).
3. **Not** in `stencilAtlas` / face shader: those correctly consume content-addressed ids from the seeded catalog for draw.

Clearing to `"none"` only needs to clear figure; it need not remove Library membership (same pattern as keeping structure/animation assets after last use until explicit delete).

---

## 3) Root cause (one sentence)

`faceStencilBinding` only emits `set-face-state` with a figure `stencilId` while render resolves pixels from the seeded catalog, so `workbench.library.stencils` (and thus project roster / stencil records) never receive the selected `StencilAsset`.

---

## 4) Least-resistance fix (bound to existing owners)

Reuse the **animation asset create** path; do not invent a second Library write model.

1. **Domain insert (owner: `applyDocumentOperation` / `workbenchOperations`)**  
   Add `create-stencil-asset` parallel to `createAnimationAsset`: idempotent append of a `StencilAsset` to `library.stencils` when `findStencilAsset` misses (guard against structure/animation id collision the same way animations guard structures). Payload is the existing `StencilAsset` from `findSeededStencil(...).asset` / `seededStencilAssets` — no new asset type.

2. **Project + durability (owners already wired for animation)**  
   - `applyProjectBody` in `authoredReducer`: `appendProjectAsset(..., "stencil")` on create.  
   - `insertedAssetId` in `projectStorageChangeSet`: return the new stencil id so authored commits `put` + roster `insert`.  
   - Inverse / validation / `authoredOperations` document family: mirror `create-animation-asset` cases only as far as existing animation wiring requires (delete optional until product needs it).

3. **Selection call site (owner: `faceStencilBinding` + command dispatch)**  
   On select (not on `"none"`): if the seeded asset is not already in Library, issue `document-edit` / `create-stencil-asset` then the existing `set-face-state` scene command (two existing `EditorCommand` kinds; `useControlBinding` today dispatches one command — extend that setValue path to dispatch ensure-then-scene, or dispatch ensure inside the same user gesture before scene). Prefer that over teaching scene ops to mutate Library: scene apply intentionally only updates working scene, and `authoredStorageChanges` only discovers new assets via document `insertedAssetId`.

4. **Do not** use `mergeProjectAssetLibrary` for authoring (load-only owner).  
   **Do not** teach `stencilAtlas` to write Library (render owner).  
   **Do not** new content store: `StencilAsset` remains metadata; bytes stay in `seededStencils` / `resolveStencilContent`.

---

## 5) Existing tests that guard Library insertion

| File | What it guards | Selection → Library? |
|------|----------------|----------------------|
| `tests/stencilAssets.test.ts` | Seeded identity; round-trip when Library **already** has `seededStencilAssets`; storage put/reload of pre-seeded library stencils; unresolved content for unknown ids | **No** |
| `tests/panels.test.tsx` | `face.stencil` enum options; `createCommand` produces `set-face-state` figure; FaceSection click emits scene command | **No** (assert scene only) |
| `tests/faceStencilRender.test.ts` | Atlas slots / instance attributes / shader path | **No** |

**None found** that assert `workbench.library.stencils` (or `project.assets` kind `"stencil"`) grows when the user selects a seeded face stencil.

Searches run: `library.stencils`, `create-stencil`, `addStencil`/`upsertStencil`/`ensureStencil`, `stencils:`, `create-animation-asset` parallels, `face.stencil` / `faceStencilBinding`, tests under `*stencil*` / `*library*` / `*asset*`.

A fix should add a focused test next to `panels.test.tsx` (command/dispatch) and/or `stencilAssets.test.ts` (Library + roster after authored ensure), asserting selection inserts the asset once and is idempotent.

---

## Symbol index (quick)

| Concern | Symbol |
|---------|--------|
| Seeded catalog | `seededStencils`, `findSeededStencil`, `seededStencilAssets`, `resolveStencilContent` (`seededStencils.ts`) |
| Selection authoring | `faceStencilBinding` (`controlBindings.ts`) |
| Face state write | `set-face-state` → `setCubeFaceState` / `applyCubeOperationToCell` |
| Library stencil read | `findStencilAsset`, `getProjectAssetRoster` |
| Library stencil load write | `mergeProjectAssetLibrary`, `materializeLibrary` |
| Library stencil author write | **missing** (mirror `createAnimationAsset`) |
| Render bypass | `createStencilAtlas`, `getStencilAtlasSlot` (`stencilAtlas.ts`) |
