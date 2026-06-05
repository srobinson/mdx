# Cubicell incremental authored scene scout

Target: `origin/main` at
`ee484e071ee5abd707cb56f36ee251cfe03214ba`.

Scope: read only scout for `PERFORMANCE.md` delivery order 2, P0 incremental
authored scene updates. The fetched `origin/main` tree matches the checked out
source tree. No source files changed and no build ran.

## Verdict

The first full scene fan out occurs in
`src/scene/useCubeSceneInstances.ts:useCubeSceneInstances`.

A one cell authored edit already preserves every untouched `CubeCell` reference
through `src/domain/cubeOperations.ts:mapCubeCells`. The edit still creates a new
`cells` array. `useStableGridLayout` consequently returns a new layout object.
`useCubeSceneInstances` uses both objects to recreate one shared topology context.
Every cache entry compares that context by reference, so every cell misses the
cache. The newly collected bucket arrays then cause every `InstancedPartMesh` to
run `syncInstancedPartMesh`, which rewrites every matrix, color, and opacity,
marks every attribute dirty, and recomputes bounds.

`sceneOperationMaterialization.ts` is upstream of the fault. Its useful role is
that it turns selection based scopes into explicit durable cube IDs before the
reducer runs. It does not currently produce a render dirty set or reach the
renderer.

## 1. Render path map

### Authored intent to accepted scene

| Stage | Owner | Current behavior |
|---|---|---|
| Scene command | `src/interaction/commands/document.commands.ts:registerDocumentCommands`, lines 24 to 49 | Receives a `SceneOperation`, materializes it, and dispatches an authored scene body. |
| Scope materialization | `src/domain/sceneOperationMaterialization.ts:materializeSceneOperations`, lines 17 to 59 | Resolves selected and selection set scopes into `single`, `ids`, or member targets. This is the earliest reusable source of exact edited cube IDs. |
| Durable operation envelope | `src/state/actions/localAuthoring.ts:createLocalAuthoredOperation`, lines 25 to 44 | Wraps the body with durable identity, target, and observed revision. |
| Store dispatch | `src/state/actions/authoredActions.ts:createAuthoredActions`, lines 18 to 50, and `src/state/actions/authoredDispatcher.ts:createAuthoredDispatcher`, lines 33 to 109 | Applies the reducer synchronously, updates Zustand, and independently queues durability. No render impact metadata is published. |
| Authored reduction | `src/state/actions/authoredReducer.ts:reduceAuthoredOperationState`, lines 50 to 128 | Validates the operation and delegates the body to the domain. |
| Scene body application | `src/state/actions/authoredReducer.ts:applyAuthoredBody`, lines 254 to 285 | Applies every materialized scene operation, then replaces the working pose. |
| Scene operation | `src/domain/cubeOperations.ts:applySceneOperation`, lines 280 to 355 | Routes the authored operation to the relevant scene mutation. |
| Cell mutation | `src/domain/cubeOperations.ts:applyCubeOperation`, lines 358 to 410, and `mapCubeCells`, lines 492 to 503 | Resolves the scope, scans the cell array, replaces only edited cell objects, and returns a new scene and cell array. Untouched cells retain identity. |
| Working pose | `src/domain/workbench.ts:updateWorkingScene`, lines 224 to 297 | Preserves the new cell array in `workingPose`. `getWorkingScene` reconstructs a scene around the same pose references. |

Two upstream costs still scale with total cells for a single ID edit:

1. `resolveCubeScope` creates a fresh resolver and builds its ID map at
   `src/domain/cubeOperations.ts:505-540`.
2. `mapCubeCells` scans the complete array at lines 492 to 503.

They are smaller than the render fan out, but a strict end to end `O(changed)`
claim must eventually account for them.

### Scene to derived instances

| Stage | Owner | Current behavior |
|---|---|---|
| Store subscription | `src/app/App.tsx:useEditorAppModel`, lines 157 to 209 | Selects the working scene and passes the staged authored scene to `CubeScene`. |
| Authored staging | `src/transport/useStagedScene.ts:resolveStageSource` and `sampleStageSource`, lines 63 to 101 | Returns the exact working scene while the authored source owns the stage. |
| Grid layout | `src/scene/CubeScene.tsx:CubeScene`, lines 142 to 172, and `src/scene/useStableGridLayout.ts:useStableGridLayout`, lines 9 to 30 | Recomputes all layout poses when `cells` changes, then reuses value equal pose references. The containing layout object is always new. |
| Topology context | `src/scene/useCubeSceneInstances.ts:useCubeSceneInstances`, lines 26 to 40, and `src/scene/cubeInstances.ts:createCubeSceneInstanceContexts`, lines 111 to 139 | Rebuilds occupancy and all resolved edge segments when `cells` or `layout` changes. The returned context objects are new. |
| Per cell derivation | `src/scene/useCubeSceneInstances.ts:useCubeSceneInstances`, lines 42 to 90, and `src/scene/cubeInstances.ts:createCubeCellInstances`, lines 141 to 247 | Cache reuse requires identical cell, pose, topology context, color overlay, and selection key references. The new topology context invalidates every cell. |
| Bucket collection | `src/scene/cubeInstances.ts:collectCubeSceneInstances`, lines 249 to 277 | Flattens all cell instances into seven packed arrays: opaque, translucent, ghost, and hit target buckets. |

### Derived instances to GPU buffers

| Stage | Owner | Current behavior |
|---|---|---|
| Bucket component | `src/scene/InstancedPartMesh.tsx:InstancedPartMesh`, lines 35 to 72 | A changed `parts` array runs a layout effect for the entire bucket. Pointer lookup also assumes `parts[instanceId]` at lines 74 to 85. |
| Full mesh sync | `src/scene/instancedPartMeshCore.ts:syncInstancedPartMesh`, lines 113 to 162 | Loops over every part, writes every matrix and color, writes every opacity, marks complete attributes dirty, and calls `computeBoundingSphere`. |
| Edge coverage duplicate | `src/scene/EdgeCoverageLayer.tsx:EdgeCoverageLayer`, lines 16 to 30, and `src/scene/edgeCoverageCore.ts:syncEdgeCoverageMesh`, lines 144 to 162 | Repeats the full opaque edge sync, then uploads the complete edge axis attribute. |
| Mesh ownership | `src/scene/CubeScene.tsx:CubeScene`, lines 412 to 491 | Mounts seven authored part buckets plus the edge coverage mesh. Each receives a full capacity derived from total cell count. |

The precise chain for one face opacity edit is:

```text
materializeSceneOperations
  -> dispatchAuthoredEdit
  -> reduceAuthoredOperationState
  -> applySceneOperation
  -> applyCubeOperation
  -> mapCubeCells replaces one CubeCell and the cells array
  -> useStableGridLayout returns a new layout object
  -> useCubeSceneInstances recreates the shared topology context
  -> all CellInstancesCacheEntry.context comparisons fail
  -> all per cell instances and all packed bucket arrays are rebuilt
  -> every InstancedPartMesh runs syncInstancedPartMesh
  -> every bucket uploads all attributes and scans bounds
```

### Important semantic boundary

A face opacity edit is locally bounded, but it can affect more than the edited
face. `isFaceBuried` at `src/domain/exposure.ts:69-139` treats only a visible,
fully opaque neighbor face as a cover. Crossing opacity 1 can reveal or bury the
opposite neighbor face. Edge visibility, opacity, color, and transforms can also
change shared edge ownership and junction trimming through
`src/domain/edgeResolution.ts:resolveEdgeDrawSegments`.

Incremental work therefore needs distinct concepts:

1. Structural occupancy, keyed by grid coordinate.
2. Mutable visual attributes on existing parts.
3. Locally affected face burial and shared edge claims.
4. Bucket membership and stable GPU slots.

## 2. Reuse map

| Needed capability | Existing owner and evidence | Disposition |
|---|---|---|
| Explicit edited cube IDs | `materializeSceneOperations`, `src/domain/sceneOperationMaterialization.ts:17-59` | Reuse. Derive transient render impact from the already materialized operation body. Do not add a second scope resolver in the renderer. |
| Untouched cell identity | `mapCubeCells`, `src/domain/cubeOperations.ts:492-503`; covered by `tests/selectionEditPerformance.test.ts:44-76` | Reuse as a correctness backstop and full scene comparison oracle. Its full array scan remains an upstream cost. |
| Stable unchanged poses | `useStableGridLayout`, `src/scene/useStableGridLayout.ts:9-30` | Reuse its equality and reference stability contract. Move the cache behind the incremental derivation owner rather than creating a parallel layout algorithm. |
| Face and edge instance derivation | `createCubeCellInstances`, `src/scene/cubeInstances.ts:141-247` | Reuse the existing geometry and visual rules. Refactor inputs so a changed cell can be derived against stable indexed context. |
| Occupancy vocabulary | `createOccupancyMap`, `getNeighborCoord`, and coordinate keys in `src/domain/neighbors.ts:38-70` | Reuse. Add incremental ownership around these facts rather than duplicating coordinate logic. |
| Face burial | `isFaceBuried`, `src/domain/exposure.ts:69-139` | Reuse the predicate. Recompute only the edited cell and direct face neighbors whose cover relation can change. |
| Shared edge ownership | `resolveEdgeDrawSegments`, `src/domain/edgeResolution.ts:69-78` | Reuse the authored edge, priority, and trim rules. Its implementation is global and needs indexed incremental decomposition before it can satisfy the gate. |
| Partial Three attribute upload | `getSelectionChromeMatrixUpdateRange` and `syncSelectionChromeMesh`, `src/scene/selectionChromeMeshCore.ts:18-71` | Extract and generalize. It already uses `addUpdateRange`, clears ranges after upload, retains multiple pending ranges, and skips unchanged matrices. Generalize for matrix, color, opacity, and edge axis attributes. |
| Partial upload tests | `tests/selectionChromeMeshCore.test.ts:34-112` | Reuse the test pattern and its pending range proof. Extend the shared primitive rather than copying the logic into authored meshes. |
| Edge axis attribute | `syncEdgeCoverageMesh`, `src/scene/edgeCoverageCore.ts:144-162` | Reuse the mesh and shader. Feed it the same stable opaque edge slots and bounded ranges as the main edge mesh. |
| Real Chromium harness | `tests/viteTestServer.mjs`, `tests/indexedDbBrowserLifecycle.ts`, and the three existing `*.browser.test.ts` suites | Reuse the Vite server and Playwright launch pattern. Add a dedicated incremental scene driver and suite under the existing `pnpm test:browser` target. |
| Unit performance guards | `tests/selectionEditPerformance.test.ts` | Reuse count based assertions. Add scene derivation and buffer write counts that remain constant at 250 and 2,025 cells. |

### None found

Repository searches found no existing owner for:

1. A render dirty set derived from an authored operation.
2. An operation sequence or accumulator delivered from the authored dispatcher
   to `CubeScene`.
3. A stable face or edge part key to GPU slot registry.
4. A reverse `instanceId` to part map independent of packed array position.
5. Incremental occupancy mutation.
6. Incremental face burial state.
7. Incremental shared edge claim or world junction indexes.
8. Partial matrix, color, opacity, or bounds synchronization for authored part
   meshes.

Searches run:

```text
rg -n -i "dirty|dirtySet|dirtyRange|updateRange|addUpdateRange|clearUpdateRanges|needsUpdate|partial update|incremental|stable slot|slot index|slotMap|instance slot" src tests
rg -n "instanceMatrix|instanceColor|InstancedBufferAttribute|setMatrixAt|setColorAt|computeBounding|InstancedMesh" src tests
rg -n -i "retain.*instance|instance.*retain|authored.*bucket|bucket.*authored|selection.*bucket|bucket.*selection" tests src
rg -n "collectCubeSceneInstances|createCubeCellInstances|createCubeSceneInstanceContexts|useCubeSceneInstances|syncInstancedPartMesh" tests
rg -n -i "render.*dirty|dirty.*render|scene.*revision|last.*operation|pending.*scene|scene.*change" src/state src/scene src/app
```

The existing regression at `tests/useCubeSceneInstances.test.tsx:22-62` proves
that cube only selection retains authored buckets. It deliberately observes a
stable `cells` and `layout` pair. It does not exercise an authored cell edit.

## 3. Performance target

`PERFORMANCE.md` sets the governing principle at line 71: work scales with the
changed data rather than total scene size. For delivery order 2, a one cell
authored edit must have bounded derivation and upload work at both 250 and 2,025
cells.

The exact P0 acceptance gates at lines 171 to 180 are:

1. One face opacity edit at 250 cubes has p95 frame time at or below 16.7 ms on
   the reference machine.
2. One face opacity edit at 2,025 cubes has p95 frame time at or below 33.3 ms.
3. A visual edit uploads only affected color or opacity ranges.
4. A visual edit performs no occupancy rebuild and no full bounds scan.
5. A topology edit updates the changed cell and affected neighbors.
6. Browser coverage records buffer upload count and edited cell count for both
   scene sizes.

The implementation should gate deterministic counts and uploaded ranges.
Wall clock p95 remains a recorded reference machine acceptance measurement so
scheduler load cannot make the normal development suite flaky.

## 4. Slice plan

Four slices keep the pure change model, topology derivation, GPU mutation, and
React integration independently testable.

### Slice 1. Pure authored render impact

Add one exhaustive pure classifier for an already materialized
`AuthoredOperationBody`. Its result should distinguish:

```text
full scene
topology
transform
visual attributes
no authored scene effect
```

The result owns exact cube IDs and part IDs where the operation contains them.
It must union every operation in one authored scene body. Document, lattice,
hydration, comparison, and playback paths may request a full rebuild until they
receive their own explicit incremental contract.

Keep this result transient. Derive it from the authored operation schema and
do not persist a second change protocol.

Proof:

1. Exhaustive unit cases for every `AuthoredSceneOperation` kind.
2. Single face edits return one edited cube at 250 and 2,025 cells.
3. Selection and selection set scopes are already materialized to IDs before
   classification.
4. Multi operation bodies union IDs without duplicates.
5. Restore patches, placement, removal, and grid changes choose explicit broad
   categories rather than silently under invalidating.

### Slice 2. Incremental scene derivation indexes

Replace the one shared context reference with a long lived derivation owner.
It should maintain:

1. cells by ID and coordinate;
2. stable per cell layout poses;
3. face burial relations;
4. edge claims, ownership groups, and endpoint junction reverse indexes;
5. per cell derived instance records.

Apply a Slice 1 impact to these indexes. A visual patch should retain occupancy.
A face opacity threshold change should rederive the edited face and the opposite
neighbor relation. A structural change should update its old and new coordinate
neighborhoods. Edge edits should update their four claim group and any old and
new world junction keys.

Refactor the current predicates into this owner. The full derivation remains the
initialization and correctness oracle, expressed through the same rules.

Proof:

1. Compare incremental output with `createCubeSceneInstances` after each edit
   across focused fixtures for color, opacity, visibility, transform, placement,
   removal, burial, shared edges, and junction trimming.
2. Assert one face edit reports one edited cell and a bounded affected set at
   both 250 and 2,025 cells.
3. Assert no occupancy construction for a visual edit after initialization.
4. Assert unaffected per cell instance records retain reference identity.
5. Add randomized edit sequences that compare incremental and full derivation
   after every step.

### Slice 3. Stable bucket slots and bounded mesh patches

Introduce one stable part key and slot registry per render bucket. The registry
must own both directions:

```text
part key -> slot
slot -> current part or empty
```

Use one mesh sync path for initial population and later patches. Generalize the
range handling from `selectionChromeMeshCore` so each changed matrix, color,
opacity, and edge axis contributes the correct Three attribute range. Clear
ranges after upload and retain every range produced before that upload.

Visual color and opacity patches must skip matrix writes and bounds. Matrix or
pickable count changes may update raycast bounds. `frustumCulled` is already
false for authored meshes, so render visibility does not require a bounds scan.

Opacity and visibility can migrate parts between opaque, translucent, and ghost
buckets. Removal and free slot reuse must clear the departed slot without
shifting every later part. `InstancedPartMesh` pointer lookup must use the slot
registry because packed `parts[instanceId]` no longer owns identity.

Proof:

1. After initial sync, one face color edit performs one color write, zero matrix
   writes, zero opacity writes, and zero bounds scans.
2. One opacity edit writes only bounded opacity and any required bucket migration
   slots.
3. Dirty ranges have correct item units for matrix 16, color 3, opacity 1, and
   edge axis 1.
4. Multiple edits before an upload retain all ranges.
5. Slot removal, reuse, bucket migration, and pointer resolution never expose a
   stale part.
6. `EdgeCoverageLayer` consumes the same opaque edge slot plan and updates only
   affected edge axis ranges.

### Slice 4. Authored handoff, React wiring, and Chromium gates

Wire accepted authored reductions to the incremental scene owner without adding
render metadata to durable snapshots. The handoff must preserve every accepted
operation when React batches renders. Hydration and stage source changes reset
the owner through one explicit full initialization path.

`CubeScene` should consume the stable derived bucket state. Each authored edit
patches the changed slots and requests one viewport invalidation. Demand driven
rendering remains delivery order 4, so this slice should avoid widening into the
frame loop work.

Add `tests/incrementalScene.browser.test.ts` and a small browser driver. Reuse
the existing Vite and Playwright harness. Keep it under `pnpm test:browser`,
which remains separate from the fast `pnpm test` unit loop.

For both 250 and 2,025 cubes, drive the real authored command path and one face
opacity edit. Record:

1. edited cell count;
2. affected derivation cell count;
3. matrix, color, opacity, and edge axis write counts;
4. uploaded attribute ranges and bytes;
5. occupancy rebuild count;
6. bounds scan count;
7. frame intervals and p95.

Hard gate the deterministic counts, ranges, and bytes. Record p95 in Chromium
and enforce the 16.7 ms and 33.3 ms thresholds in the reference machine release
benchmark.

After the gates pass, correct the stale rendering claim at
`ARCHITECTURE.md:252` as required by `PERFORMANCE.md:390-394`.

## Riskiest seam

Stable slot ownership across bucket migration is the riskiest seam. Opacity,
visibility, face burial, and shared edge priority can add, remove, or transfer a
part while pointer events still arrive as `instanceId`. A loose implementation
will either shift a bucket tail and restore `O(N)` uploads, or leave stale slot
to part mappings and select the wrong cube. Shared edge junction trimming adds
a second reachability risk because transformed edge endpoints are indexed in
world space, beyond a simple six neighbor grid set.

The safe boundary is one authoritative derivation and slot registry that owns
part identity, bucket membership, reverse picking, and dirty attributes. Every
consumer, including edge coverage, must use that result.
