# Scout: Turn (group rotation)

Repo: `/Users/alphab/Dev/LLM/DEV/helioy/cubicell` · `main@ae44cbf`  
Scope: read-only reuse map. No code, no PR.

Capability: rotate a **selection of cubes** about a **shared pivot**, along an **arc** (not chord), with a **signed sweep** so full turn and no turn are distinguishable.

---

## 0. Established baseline (verified)

| Claim | Evidence |
|-------|----------|
| Per-cube rotation about own centre | `createSceneGridLayout` → `CubeLayoutPose.rotation` from `placement.rotation`; `cubeInstances.createCubeCellInstances` builds `cellMatrix` via `createTransformMatrix(pose.renderPosition, pose.rotation, pose.scale)` (`src/shared/three.ts:createTransformMatrix`) |
| No group / pivot / parent | Search `pivot`, `group rotat`, `rotate-selection`, `parentId` under `src/**/*.ts`: **none found** |
| Morph is linear + coord snap | `sceneMorph.interpolateCell`: `coord: after.placement.coord`; offset/rotation/scale via `lerpVec3` |
| Camera signed arc exists | `CameraOrbitArc { normal, sweepRadians }` on `PoseSegment.arc`; sample via `rotateAroundAxis*` × `sweepRadians * fraction` |
| No rotate-selection op | `CubeOperation` union has no turn/rotate-selection kind |

---

## 1. Operation pipeline (template: `set-cube-offset`)

A new scene cube operation kind must register everywhere `set-cube-offset` does. **Miss one and the slice fails.**

### Kind + applier (domain)

| # | Role | Symbol |
|---|------|--------|
| 1 | Kind union | `src/domain/cubeOperations.ts:CubeOperation` |
| 2 | Scene op union (includes CubeOperation) | `src/domain/cubeOperations.ts:SceneOperation` / `AuthoredSceneOperation` |
| 3 | Per-cell switch | `src/domain/cubeCellOperations.ts:applyCubeOperationToCell` |
| 4 | Multi-cell apply entry | `src/domain/cubeOperations.ts:applyCubeOperation` |
| 5 | Scene apply dispatch | `src/domain/cubeOperations.ts:applySceneOperation` |
| 6 | Materialize “is cube op?” filter | `src/domain/sceneOperationMaterialization.ts:isCubeOperation` |

**Deviate note:** `set-cube-offset` is **independent per cell** (`setCubeOffsetAxis`). Group turn is **joint**: one pivot, N cells. Either (a) a multi-cell applier that does not go through pure per-cell map without shared pivot context, or (b) expand `applyCubeOperation` special-case like `set-cube-visibility-intent`. Do not assume `applyCubeOperationToCell` alone is enough.

### Validation / guards

| # | Role | Symbol |
|---|------|--------|
| 7 | Authored body scene op validator | `src/state/authoredOperationValidation/scene.ts:isCubeOperation` (switch cases) |
| 8 | Envelope + schema | `src/state/authoredOperationValidation.ts:validateAuthoredOperation` + `authoredOperationSchemaVersion` (**currently 2**) in `src/domain/authoredOperations.ts` |
| 9 | Scope shapes | `isAuthoredCubeScope` same file (reuse `single` / `ids`; group turn should author as `ids` after materializing selection) |

### Render-impact classifier

| # | Role | Symbol |
|---|------|--------|
| 10 | Per-kind layout vs cell scope | `src/domain/authoredRenderImpact.ts:getAuthoredSceneOperationRenderScope` |
| 11 | Cell id extraction | `src/domain/authoredRenderImpact.ts:getAuthoredOperationCellIds` (default: `getAuthoredScopeCellIds`) |
| 12 | Net impact API | `src/domain/authoredRenderImpact.ts:classifyAuthoredRenderImpact` |

### Undo / inverse

| # | Role | Symbol |
|---|------|--------|
| 13 | Scene inverse (all scene ops) | `src/domain/authoredInverse.ts:deriveInverseBody` → **always** `createSceneRestorePatch(before, after)` for `family: "scene"` |

**Reuse:** scene ops do **not** need a per-kind inverse case. Undo is patch-based.  
**Risk:** large selection restore patches are heavy but consistent with offset.

### Persistence codecs

Scene operations ride inside authored commit JSON bodies; there is **no per-kind pose field codec** for ops.

| # | Role | Symbol |
|---|------|--------|
| 14 | Outbox op body round-trip | `src/persistence/recordCodecs/outboxCommitRecordCodec.ts` + `isAuthoredOperationBody` |
| 15 | Pose endpoints only | `src/persistence/recordCodecs/compactPose.ts:encodeCell` / `decodeCell` (coord, offset, rotation, scale) |
| 16 | Pose revision envelope | `poseRevisionRecordSchemaVersion = 1` (`poseRevisionRecordCodec.ts`) |
| 17 | Structure schema constant | `authoredOperationSchemaVersion = 2` |

New **kind** → bump validation + `authoredOperationSchemaVersion` if wire must reject unknown kinds on old clients.  
New **transition arc field** (see §3) → structure/animation score codecs + their schema versions (see §6).

### Exhaustive switches / kind enumerations (tests + code)

| # | Role | Symbol |
|---|------|--------|
| 18 | Exhaustive kind map (compile-time) | `tests/authoredRenderImpact.test.ts` `satisfies Record<AuthoredSceneOperation["kind"], …>` |
| 19 | Domain unit tests for apply | `tests/domain.test.ts` (`set-cube-offset` / `snap-cube-home` patterns) |
| 20 | Morph benches/tests using offset | `tests/sceneMorph.test.ts`, `tests/sceneMorph.bench.ts`, `tests/incrementalCubeRenderResolution.test.ts` (if turn feeds morph) |
| 21 | Editor command path (if UI) | `createSceneEditorCommand` + bindings like `src/editor/controlBindings.ts` offset binding; `src/interaction/commands/document.commands.ts` |

**Registration point count (must-touch for a new kind): 18 core** (rows 1–18). Rows 19–21 are proof/UI.  
**none found:** dedicated `rotate-selection` command, pivot type, parent transform node.

---

## 2. Render impact

**Classifier:** `classifyAuthoredRenderImpact` → for scene ops, `getAuthoredSceneOperationRenderScope` then `classifySceneRenderImpact` → per-cell `classifyCellRenderImpact`.

**How placement changes classify today**

- `set-cube-offset` / `snap-cube-home` / `resize-cube` → scope **`"layout"`** (`getAuthoredSceneOperationRenderScope`).
- `"layout"` forces layout comparison: `createSceneGridLayout` before/after; `findLayoutChanges` marks cells whose `CubeLayoutPose` differs.
- Per cell: `transform: true` if size changed **or** layoutChanged; `occupancy: true` only if `placement.coord` key changed.
- Result kind is almost always **`{ kind: "cells", cells }`**, not `full-scene`.  
  `full-scene` is for `document` / `lattice` families, or when cell-id extraction returns null (e.g. `set-grid-gap`, `resize-grid`) and the whole scene is scanned—still `kind: "cells"` with all candidates, not `full-scene`.

**Group rotation of many cells**

- If authored with `scope: { kind: "ids", cubeIds }`, impact is **those cells only**, with **`transform: true`** (offset/rotation change layout poses), **`occupancy: false`** if coords unchanged.
- Does **not** force `full-scene` rebuild by kind; incremental owner still re-resolves neighbors if burial/claims depend on world pose (layout-driven). Confirm: burial uses layout poses (`isFaceBuried` + layout), edge claims use layout—so transform-true cells and neighbors may update even when occupancy false. That is **incremental cell impact with layout recompute**, not a full-scene wipe.

---

## 3. CRUX — where signed sweep lives

### What exists

| Layer | Carries route data? | What is stored |
|-------|---------------------|----------------|
| **State / pose** | Endpoints only | `CubePlacement { coord, offset, rotation, scale }` in compact pose; no arc |
| **Piece transition** | Timing + morph settings only | `Transition { mode, settings }` on `StateTransitionTrack.transitions[]` (`score.ts`). **No path, no arc, no sweep** |
| **Morph evaluation** | Derived from two poses | `interpolateCell`: linear offset/rotation/scale; **coord snaps** to `after` |
| **Camera segment** | **Yes — signed sweep** | `PoseSegment.arc: CameraOrbitArc \| null` with `sweepRadians` (signed); `resolveCameraOrbitArc` / `reverseCameraOrbitSweep` / `addCameraOrbitFullTurn` |

### Construction problem

If turn motion is only **diff of two poses**, then a full **2π** group turn that returns every cube to the same `offset`/`rotation` is **identical to no turn**. Linear morph shows **zero motion**. Shortest-arc recovery (like `deriveShortestCameraOrbitArc`) also collapses full turns to 0.

### Where sweep MUST live

| If Turn is… | Sweep storage |
|-------------|----------------|
| **Live edit that commits endpoints only** | Sweep is ephemeral (gesture); final state is pose. Full turns that end equal are **identity ops** unless you record history as a patch of intermediate… still endpoint-equal. For **performable full turns between states**, live-only is insufficient. |
| **Motion between captured States** | **New field required** on the **piece transition route**, analogous to camera: e.g. extend `Transition` (or a sibling segment) with `arc: { pivot, normal, sweepRadians }` or per-cube path. Camera precedent: `PoseSegment.arc`. |
| **Operation log only** | Authored op could store sweep, but **playback morph ignores ops** and diffs state poses. Sweep on op alone does **not** fix morph unless evaluation reads it. |

**Single most important answer:**  
**Signed sweep for Turn must live on the transition route (piece `Transition` or new segment type), not on pose endpoints.** Pose has no place for it; morph has no arc channel today. Camera already solved this with `CameraOrbitArc.sweepRadians` on `PoseSegment`.

**none found:** piece-level orbit/arc; group pivot on score; any `sweepRadians` outside camera domain.

---

## 4. Camera reuse

| Symbol | Location | Generic? |
|--------|----------|----------|
| `CameraOrbitArc` | `src/domain/cameraTrack.ts` | Type is generic (normal + sweepRadians) but named/used only for camera |
| `deriveShortestCameraOrbitArc` | `cameraTrack.ts` | **Camera-coupled**: builds arc from `CameraPoseSnapshot` via `viewDirection(position−target)` |
| `resolveCameraOrbitArc` | `cameraTrack.ts` | Camera-coupled endpoints |
| `rotateAroundAxis` / `rotateAroundAxisInto` | `cameraTrack.ts` **private** | **Generic Rodrigues maths**; not exported; only used inside camera sampling |
| `reverseCameraOrbitSweep` / `addCameraOrbitFullTurn` | `cameraTrack.ts` | Generic signed-sweep utilities (radians + 2π), camera-named only |
| `interpolateCameraPose` orbit branch | `cameraTrack.ts` | Camera-coupled (position about target) |

**Disposition:**  
- **Reuse** the **pattern** (store signed `sweepRadians` + axis/normal on the route; sample with Rodrigues × fraction).  
- **Do not** call `deriveShortestCameraOrbitArc` for cubes (wrong geometry).  
- **Refactor or extract** `rotateAroundAxisInto` to a shared maths module (or export it) so Turn does not reimplement Rodrigues. Today it is **not** public API.

---

## 5. Coord versus offset

| Concept | Meaning | Dependents |
|---------|---------|------------|
| **`placement.coord`** | Logical grid home (occupancy key) | `OccupancyMap` / `getGridCoordKey`; `placeCubesAt` claims; `isFaceBuried` neighbor lookup by coord; selection patterns; assembly order seeds |
| **`placement.offset`** | World delta from home | `createSceneGridLayout`: `renderPosition = homePosition + offset` |
| **`placement.rotation`** | Per-cube Euler about own centre | Instance matrix after translate |
| **Layout pose** | Derived | Burial plane tests, edge claim corners, instance matrices |

**Can group rotation be offset+rotation only?**  
**Yes — and it should.** Keep `coord` fixed; set each cube’s `offset` so `renderPosition` orbits the shared pivot; update `rotation` so local orientation follows the group (or not, product choice). That preserves occupancy, claim keys, and burial topology mid-arc.

**If coord must change** (e.g. “snap homes after turn”):  
- Mid-transition **coord snap** in `interpolateCell` makes occupancy/burial/edge claims jump at cut or stick to `after` only—**no continuous coord motion**.  
- Partial turns that land off-grid cannot be true coords without a new continuous coord model.  
- **Breaks mid-morph:** burial and `resolveCoincidentEdgeClaims` see snapped after-coords while offsets still interpolating → wrong shared edges / holes.

**Recommendation:** Turn = pure offset (+ rotation); optional separate snap-to-grid step after gesture.

---

## 6. Wire cost

| Change | Codec / constant | Cost |
|--------|------------------|------|
| New scene op kind only | Validation switch + `authoredOperationSchemaVersion` (2 → 3 if old readers must fail closed) | Outbox stores full JSON body; no compact table for kinds. Pose codecs **unchanged** if endpoints are still offset/rotation |
| Endpoints after turn | `compactPose` already has offset + rotation | **No pose schema bump** if only values change |
| Signed sweep on piece transition | `Transition` type + structure score codec path (`structureRecordSchemaVersion = 1`) and any animation score path (`animationRecordSchemaVersion = 1`) | **Bump structure (and animation if shared score shape) schema**; decode must default `arc: null` for old records |
| Camera arc | Already on `PoseSegment` | No change |

**Confirm constants to bump when sweep is durable:**  
- `authoredOperationSchemaVersion` if new op kind is committed to outbox with strict validation  
- `structureRecordSchemaVersion` (and possibly animation) if `Transition` gains arc  
- **Not** `poseRevisionRecordSchemaVersion` / CompactPoseV1 unless placement gains fields (it should not for sweep)

---

## 7. Quality map (near seams)

| Issue | Where | Risk |
|-------|--------|------|
| **Duplication of Rodrigues** | Private `rotateAroundAxis*` only in `cameraTrack.ts` | Copy-paste into turn will diverge; extract once |
| **Linear rotation lerp is wrong for large angles** | `interpolateCell` `lerpVec3` on Euler | Even without full turns, 170° group turns chord badly; arc path is the fix, not better Euler lerp alone |
| **Coord snap** | `interpolateCell` | Hostile to any mid-flight home change; reinforces offset-only Turn |
| **Scene inverse always full patch** | `deriveInverseBody` | Correct but heavy for multi-cube turn; acceptable |
| **“layout” vs “transform” naming** | authoredRenderImpact | Offset/rotation mark `transform` via layout compare; easy to miss neighbor re-resolve when testing only instance matrices |
| **Dead/underused cut** | `TransitionMode` `"cut"` | Not related to geometric cut; do not overload for turn |
| **Group vs per-cell apply** | `applyCubeOperation` maps cells independently | Designing turn as N× independent ops loses shared pivot unless each op carries full pivot+sweep (redundant) |

---

## Suggested architecture (scout only)

1. **Live op** `turn-selection` (name TBD): scope `ids`, fields `{ pivot, normal, sweepRadians }` (or axis + signed angle), applies joint offset+rotation updates; instancing unchanged.  
2. **Durable motion:** add optional arc on piece `Transition` (or new path kind) mirroring `PoseSegment.arc`; morph samples group orbit using extracted `rotateAroundAxis`.  
3. **Do not** put sweep on `CubePlacement`.  
4. **Coord** stays put for continuous turns.

---

## DISPOSITIONS

| ID | Finding | Disposition |
|----|---------|-------------|
| D1 | `CubeOperation` + `applyCubeOperationToCell` + `applyCubeOperation` + `isCubeOperation` (materialize + validation) | **reuse** (extend switches/unions) |
| D2 | Group turn as pure per-cell `set-cube-offset` clones | **deviate** (joint pivot apply required) |
| D3 | Scene inverse via `createSceneRestorePatch` | **reuse** |
| D4 | Render scope `"layout"` for placement motion | **reuse** (classify turn like offset) |
| D5 | Impact kind stays `cells` for `ids` scope multi-cube | **reuse** |
| D6 | Piece `Transition` only mode+settings; morph linear endpoints | **deviate** (add signed sweep on transition route) |
| D7 | Pose endpoints for sweep storage | **deviate** (do not; 0≡2π) |
| D8 | Camera `CameraOrbitArc` / `PoseSegment.arc` pattern | **reuse** (pattern + signed sweep semantics) |
| D9 | `deriveShortestCameraOrbitArc` for cubes | **deviate** (camera-coupled; wrong) |
| D10 | `rotateAroundAxisInto` private in cameraTrack | **refactor** (extract/export shared maths) |
| D11 | `reverseCameraOrbitSweep` / `addCameraOrbitFullTurn` | **reuse** (or move beside extracted maths) |
| D12 | Express turn via offset+rotation, coord fixed | **reuse** (layout model already supports) |
| D13 | Express continuous turn via coord changes | **deviate** (coord snap + occupancy break) |
| D14 | CompactPose for endpoints | **reuse** (no new placement fields) |
| D15 | New op kind validation / `authoredOperationSchemaVersion` | **reuse** (bump when kind ships) |
| D16 | Transition arc → structure/animation schema | **deviate** (new field + version bump) |
| D17 | `tests/authoredRenderImpact.test.ts` exhaustive kind map | **reuse** (must add case) |
| D18 | Parent/pivot scene graph | **none found** — **deviate** only if product demands hierarchy; not required for selection turn |
| D19 | Euler lerp for orientation mid-turn | **refactor** (arc sampling replaces lerp for turn channel) |
| D20 | Instancing / capacity | **reuse** (no new mesh kinds; matrix updates only) |

Stuart signs dispositions before build.

---

## Searches run (negative results)

```
pivot | group rotat | rotate-selection | parentId | turn-selection  → none in src/**/*.ts
```
