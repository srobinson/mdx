# Stable GPU Capacity Scout

Baseline verified: clean `main` at `346766193bb565950cf5b09cf93a8cfaaf4d53e7`.

The documented P1 is stale on this baseline. Geometric capacity, stable mesh and material identity, WebGL resource counting, and the browser acceptance gate already landed in `ef6a082`, `6e4c628`, and `1efd2d2`. All four documented acceptance gates can be expressed with the existing tooling. They are already encoded in `tests/incrementalScene.browser.test.ts:test keeps live GPU resources flat across capacity bands and reuse cycles`.

## Causal Chain

### Current main

The cell count still affects required slot capacity, but it no longer changes mesh or material identity.

1. `src/scene/CubeScene.tsx:CubeScene` derives `visibleCells`, calls `useCubeSceneInstances`, and passes the result to `resolveCubeInstanceBuckets`.
2. `src/scene/useCubeSceneInstances.ts:useCubeSceneInstances` retains one `IncrementalCubeSceneOwner`.
3. `src/scene/incrementalCubeSceneOwner.ts:renderOwnerState` applies accepted journal entries, updates the stable slot owner, and publishes `CubeInstanceSlotState`.
4. `src/scene/cubeInstanceSlots.ts:resolveCubeInstanceBuckets` resolves each of the seven part buckets.
5. `src/scene/cubeInstanceSlots.ts:resolveBucket` sets required capacity to the maximum of packed length, stable slot array length, and patch slot count. Stable slot length includes tombstones, so a live count cannot understate the highest addressable slot.
6. `src/scene/CubeScene.tsx:CubeScene` passes each resolved bucket into `InstancedPartMesh`. Opaque edges also feed `EdgeCoverageLayer`.
7. `src/scene/InstancedPartMesh.tsx:InstancedPartMesh` and `src/scene/EdgeCoverageLayer.tsx:EdgeCoverageLayer` capture only the initial required capacity in a ref. Their memoized mesh identity is independent of later capacity props.
8. `src/scene/instancedPartMeshCore.ts:createInstancedPartMeshWithGeometry` rounds initial capacity with `resolveGeometricInstanceCapacity`, creates one `MeshBasicMaterial`, and creates one `InstancedMesh`.
9. `src/scene/instancedPartMeshCore.ts:growInstancedPartMesh` retains the same mesh and material. Within a band it emits a retain event. At a boundary it clones and resizes geometry attributes, replaces matrix and color attributes, disposes the old geometry buffers, then requests a full slot sync.
10. React Three Fiber receives the same `<primitive object={mesh}>`. Reconciliation updates props without replacing the Three object. No new material reaches Three's program cache, so no program is compiled.

The current chain stops before shader program creation.

### Historical chain represented by the stale finding

Before `6e4c628`, `src/scene/InstancedPartMesh.tsx:InstancedPartMesh` included `capacity` directly in the mesh `useMemo` dependency list. `src/scene/EdgeCoverageLayer.tsx:EdgeCoverageLayer` did the same.

A capacity change therefore forced this chain:

1. `src/scene/cubeInstanceSlots.ts:resolveBucket` returned a different capacity.
2. `src/scene/InstancedPartMesh.tsx:InstancedPartMesh` created a new mesh because its memo dependency changed.
3. `src/scene/instancedPartMeshCore.ts:createInstancedPartMesh` created new geometry.
4. `src/scene/instancedPartMeshCore.ts:createInstancedPartMeshWithGeometry` created a new `MeshBasicMaterial` and `InstancedMesh`.
5. React Three Fiber reconciled a changed primitive `object`, removed the old Three object, and added the new one.
6. The component cleanup called `src/scene/instancedPartMeshCore.ts:disposeInstancedPartMesh`, which disposed the old geometry and material.
7. `node_modules/three/src/renderers/WebGLRenderer.js:onMaterialDispose` called `deallocateMaterial`, then `releaseMaterialProgramReferences`.
8. `node_modules/three/src/renderers/webgl/WebGLPrograms.js:releaseProgram` destroyed a program when the last material reference for its cache key disappeared.
9. On the next render, `node_modules/three/src/renderers/WebGLRenderer.js:getProgram` called `node_modules/three/src/renderers/webgl/WebGLPrograms.js:acquireProgram`.
10. A cache miss constructed `node_modules/three/src/renderers/webgl/WebGLProgram.js:WebGLProgram`, which called `WebGLRenderingContext.createProgram`.

React and React Three Fiber require replacement once the code supplies a different primitive object. They do not require capacity to be part of object identity. The application created that coupling through the memo dependencies and material construction.

The measured five programs correspond to five rendered program cache key families, rather than five meshes:

1. Opaque, double sided face material.
2. Translucent, double sided face material with the instance opacity shader extension.
3. Opaque, front sided edge and pick material.
4. Translucent, front sided edge, ghost, and slot material with the instance opacity shader extension.
5. Edge coverage material with its own custom program cache key and vertex shader extension.

Materials within a family share a Three program. Replacing all material instances in a family allowed its reference count to reach zero, so the five families were released and compiled again. Selection chrome can add another material variant when it has instances, but it was not part of the documented five program measurement.

## What We Can Already Count

`tests/webGlResourceObserver.ts:observeWebGlResources` patches both `WebGLRenderingContext.prototype` and `WebGL2RenderingContext.prototype`.

It observes:

| Resource | Create | Delete | Live identity set |
|---|---:|---:|---:|
| `WebGLBuffer` | Yes | Yes | Yes |
| `WebGLProgram` | Yes | Yes | Yes |

It provides:

- Separate cumulative counts for created buffers, deleted buffers, created programs, and deleted programs through `snapshot`.
- Current live buffer and program counts through `liveResources`.
- One combined mutation count through `activityCount`, used to wait for quiescence.
- Stable live counts across any sequence observed by one observer instance.
- Restoration of the original WebGL prototype methods through `stop`.

It counts linked shader programs specifically through `createProgram` and `deleteProgram`. It does not count individual vertex or fragment shader objects.

It does not observe textures, framebuffers, renderbuffers, vertex array objects, samplers, queries, transform feedback objects, sync objects, context loss, driver caches, physical allocation bytes, or timing. It also counts every WebGL context in the page because the patch is prototype wide.

The existing acceptance coverage combines this observer with `tests/incrementalSceneBrowserDriver.tsx:observeCapacityEvents`:

- `tests/incrementalSceneBrowserDriver.tsx:runGpuCapacityBrowserGate` mounts the production renderer tree, establishes baseline live counts, performs an edit within a band, performs an edit across a band, then runs repeated remove and add cycles.
- `tests/incrementalSceneBrowserDriver.tsx:summarizeGpuCapacityStage` computes per-stage buffer and program deltas plus live counts.
- `tests/incrementalSceneBrowserDriver.tsx:observeCapacityEvents` separately proves mesh identity, material identity, retain events, grow events, and the mesh family that grew.
- `tests/incrementalScene.browser.test.ts:test keeps live GPU resources flat across capacity bands and reuse cycles` asserts zero resource calls within a band, buffer creation and deletion with zero program creation across a band, stable live counts, and zero resource calls during reuse cycles.

Verdict: yes, all four acceptance gates can be written with existing tooling, and they already are. The phrase "no GPU resource" is implemented as no buffer or program activity. A future requirement covering every WebGL resource class would require extending the observer.

## Headless Validity

Confirmed for the counts this gate claims.

`tests/webGlResourceObserver.ts:observeWebGlResources` intercepts JavaScript WebGL API calls before Chromium passes them to SwiftShader or a hardware driver. `createBuffer`, `deleteBuffer`, `createProgram`, and `deleteProgram` calls remain observable with the same object identity semantics under SwiftShader. The backend can change physical allocation, compilation cost, and timing, but it cannot bypass an application call that passes through the patched WebGL prototype.

The existing driver strengthens this evidence:

- `tests/incrementalScene.browser.test.ts:describe incremental authored scene in real Chromium` launches headless Chromium.
- `tests/incrementalSceneBrowserDriver.tsx:createBrowserSceneHarness` mounts one React root.
- `tests/incrementalSceneProductionTree.tsx:IncrementalSceneProductionTree` renders `EditorRendererBinding` with the production `CubeScene`.
- `tests/incrementalSceneBrowserDriver.tsx:dispatchBrowserEdit` sends the mutation through `dispatchAuthoredEdit`, waits for the journal to drain, then waits for resource and capacity activity to settle.

SwiftShader resource counts are therefore valid as WebGL API call counts. They do not prove physical GPU memory use, driver internal allocations, hardware shader compile cost, or timing. This scout did not run the browser gate because the brief prohibited browser execution.

## Blast Radius

The capacity implementation is aligned with the P0 stable slot rescue.

### Slot allocation and capacity demand

- `src/scene/instanceSlotRegistry.ts:allocateSlot` reuses a free tombstone or appends one slot.
- `src/scene/instanceSlotRegistry.ts:vacateSlot` leaves a tombstone and reserves the prior slot for the same logical key.
- `src/scene/instanceSlotRegistry.ts:takeFreeSlot` prefers the reserved slot, otherwise takes another free slot.
- `src/scene/instanceSlotRegistry.ts:finalizePatches` reports the full slot array length as `slotCount`.
- `src/scene/cubeInstanceSlots.ts:resolveBucket` uses that high water length as required capacity.

This preserves the central invariant: every dirty write index and every `instanceId` remains addressable even when live part count falls.

### Dirty ranges

Within a capacity band, `src/scene/InstancedPartMesh.tsx:InstancedPartMesh` calls `patchInstancedPartMesh`. `src/scene/instancedPartMeshCore.ts:patchInstancedPartMesh` writes only the attributes named by each slot patch and marks only those slot ranges dirty.

At a band crossing, `growInstancedPartMesh` replaces capacity bound buffer attributes. The component deliberately calls `syncInstancedPartMesh` instead of applying the small patch because the new attributes contain no prior data. This is one amortized full upload per band. The next edits return to bounded patches.

### Journal continuity

`src/scene/incrementalCubeSceneOwner.ts:journalContinues` remains the authority for incremental eligibility. On continuity failure, `createOwnerState` rebuilds derivation and slot ownership. The mounted mesh can retain its geometric high water capacity while `syncInstancedPartMesh` writes the rebuilt slot arrays. Capacity policy has no authority over journal acceptance.

### Silent failure modes

- Deriving required capacity from live parts instead of stable slot array length could put a dirty write beyond the buffer. `src/scene/instancedPartMeshCore.ts:assertSlotCapacity` catches the direct overflow.
- Compacting slot arrays independently of logical key locations could make picking return the wrong part. `tests/instanceSlotRegistry.test.ts:test keeps reverse picking exact beside tombstones and after re-add` and `tests/cubeInstanceSlots.test.ts:test matches full cube buckets through edit, migrate, remove, and re-add` catch this.
- Replacing mesh identity during growth could remount the primitive and erase P0 continuity. `tests/incrementalSceneReactMeshHandoff.test.ts:test grows once across a band and releases capacity on teardown` asserts stable mesh and material identity.
- Copying or resizing only known attributes could omit `instanceOpacity` or `instanceEdgeAxis`. `growInstancedPartMesh` resizes every `InstancedBufferAttribute`, then a full sync rewrites active slots. The same React handoff test compares the grown output with a full sync.
- Applying a bounded patch immediately after growth would leave unchanged slots empty in the new buffers. The current `grew` branch prevents this. The full output comparison catches regression.
- Shrinking the mesh while the slot registry retains tombstones could invalidate high slot indices. The current growth policy has no shrink path.
- Resetting or replacing the slot owner during a valid journal continuation would turn cheap edits into full work. `tests/incrementalScene.browser.test.ts:test uses no full sync for one authored face edit at 250 and 2025 cells` checks full sync count, patch count, upload bytes, affected cells, and output equality.

The P0 performance guarantee applies within a capacity band. A boundary crossing intentionally performs one full sync. Power of two bands make that event logarithmic in the lifetime high water mark.

## Minimal Change

No source or test change is required for geometric bands or capacity independent materials on `3467661`.

The implementation already uses a factor of two:

- `src/scene/instancedMeshCapacity.ts:resolveGeometricInstanceCapacity` returns the smallest power of two greater than or equal to the required slot count.
- `src/scene/instancedMeshCapacity.ts:growInstancedMeshCapacity` retains the current band when requirements shrink.
- Zero required slots still allocate capacity one. This gives every mesh a valid positive geometric capacity.
- At large sizes, retained capacity is less than twice the largest required slot count for each bucket.
- Unsafe integer inputs are rejected. Practical typed array and memory limits arrive much earlier than JavaScript's safe integer boundary.

The already landed file footprint is:

| File | Existing responsibility | Approximate implementation size |
|---|---|---:|
| `src/scene/instancedMeshCapacity.ts` | Power of two resolve and grow policy | 32 lines |
| `src/scene/instancedPartMeshCore.ts` | Stable material creation, buffer growth, generic instanced attribute resizing, mutation observation | About 120 added lines across the capacity commits |
| `src/scene/InstancedPartMesh.tsx` | Stable mesh identity and grow versus patch decision | About 15 changed lines |
| `src/scene/EdgeCoverageLayer.tsx` | Same identity and growth discipline for coverage | About 12 changed lines |
| `src/scene/selectionChromeMeshCore.ts` and `src/scene/SelectionChromeLayer.tsx` | Reuse the same geometric grow owner for selection chrome | Existing reuse, no parallel policy |
| `tests/instancedMeshCapacity.test.ts` | Band and validation policy | 36 lines |
| `tests/incrementalSceneReactMeshHandoff.test.tsx` | Mesh, material, buffer, sync, and disposal behavior | About 100 capacity focused lines |
| `tests/webGlResourceObserver.ts` | Browser WebGL buffer and program counts | 144 lines |
| `tests/incrementalSceneBrowserDriver.tsx` and `tests/incrementalScene.browser.test.ts` | Production mutation driver and four acceptance gates | About 160 capacity focused lines |

Chunked instance pages should remain deferred. The current durable target does not justify the extra page registry, draw calls, picking translation, dirty range routing, and cross-page migration logic. Reconsider pages only after measured peak allocation or growth pause evidence exceeds an explicit release budget.

The minimal remaining correction is documentation only: update `PERFORMANCE.md` to mark this P1 complete and cite its production and browser gate owners.

## Compaction

V1 should never shrink a mounted mesh automatically.

Automatic shrink would conflict with stable slot high water marks, create band boundary oscillation, and turn removal into buffer work. Project or renderer teardown already releases all capacity through `src/scene/instancedPartMeshCore.ts:disposeInstancedPartMesh`. A later explicit compaction feature would need to rebuild the slot registry and every mesh atomically after the authored journal drains.

At the 4,500 cell durable target, the no shrink policy is bounded and acceptable:

- An isolated cube contributes at most six faces and twelve edges.
- 27,000 face slots round to 32,768.
- 54,000 edge slots round to 65,536.
- Matrix plus instance color storage is about 76 bytes per opaque slot.
- Translucent slots add a four byte opacity attribute.
- Edge coverage adds a four byte axis attribute.

An all opaque isolated scene is approximately 16.9 MiB of raw instance attributes across faces, rendered edges, edge hit targets, and coverage. A conservative lifetime high water case where opaque, translucent, and ghost face and edge buckets have each separately reached their maximum is approximately 31.9 MiB. These estimates exclude small base geometries, selection chrome, JavaScript slot records, renderer bookkeeping, and transient growth overlap. Dense structures have far fewer exposed parts than the isolated case.

The important peak occurs during growth because old and new buffers coexist until disposal completes. A two times band growth can transiently hold roughly the old capacity plus the new capacity. This remains an observation target, rather than a reason to add compaction now.

Future compaction should require measured memory pressure beyond the durable target and an explicit owner decision. It should run only at an idle, journal drained boundary and use hysteresis. A cell count change alone is not a safe trigger.

## Reuse Map

| Capability | Existing owner |
|---|---|
| Derive initial capacity band | `src/scene/instancedMeshCapacity.ts:resolveGeometricInstanceCapacity` |
| Retain or grow a band | `src/scene/instancedMeshCapacity.ts:growInstancedMeshCapacity` |
| Allocate initial instance geometry, material, and mesh | `src/scene/instancedPartMeshCore.ts:createInstancedPartMeshWithGeometry` |
| Grow instance buffers | `src/scene/instancedPartMeshCore.ts:growInstancedPartMesh` |
| Resize every custom instanced geometry attribute | `src/scene/instancedPartMeshCore.ts:resizeCapacityBoundGeometryAttributes` |
| Resize matrix, color, opacity, and axis attributes | `src/scene/instancedPartMeshCore.ts:resizeInstancedBufferAttribute` |
| Own part material lifetime | `src/scene/InstancedPartMesh.tsx:InstancedPartMesh` and `src/scene/instancedPartMeshCore.ts:disposeInstancedPartMesh` |
| Own edge coverage material lifetime | `src/scene/EdgeCoverageLayer.tsx:EdgeCoverageLayer`, `src/scene/edgeCoverageCore.ts:createEdgeCoverageMesh`, and `src/scene/edgeCoverageCore.ts:disposeEdgeCoverageMesh` |
| Own stable logical slots | `src/scene/instanceSlotRegistry.ts:createInstanceSlotRegistry` |
| Adapt stable slots to render buckets | `src/scene/cubeInstanceSlots.ts:resolveCubeInstanceBuckets` |
| Count browser buffers and programs | `tests/webGlResourceObserver.ts:observeWebGlResources` |
| Observe mesh and material identity | `tests/incrementalSceneBrowserDriver.tsx:observeCapacityEvents` |
| Drive a production scene mutation | `tests/incrementalSceneBrowserDriver.tsx:dispatchBrowserEdit` |
| Mount the production render path | `tests/incrementalSceneProductionTree.tsx:IncrementalSceneProductionTree` |
| Exercise the complete capacity sequence | `tests/incrementalSceneBrowserDriver.tsx:runGpuCapacityBrowserGate` |
| Assert the four documented gates | `tests/incrementalScene.browser.test.ts:test keeps live GPU resources flat across capacity bands and reuse cycles` |

No required capability lacks an existing owner.

Searches run:

- FMM symbol and outline queries for `CubeScene`, `InstancedPartMesh`, `createInstancedPartMeshWithGeometry`, `growInstancedPartMesh`, `resolveGeometricInstanceCapacity`, `growInstancedMeshCapacity`, `observeWebGlResources`, `runGpuCapacityBrowserGate`, the stable slot owners, and the production browser harness.
- `rg -n "createdPrograms|deletedPrograms|liveResources|observeWebGlResources|capacity" PERFORMANCE.md tests src/scene`
- `rg -n "createProgram|acquireProgram|releaseProgram|onMaterialDispose" node_modules/three/src/renderers`
- `git log` and `git show` for `ef6a082`, `6e4c628`, and `1efd2d2`.

## Risks

1. **Peak memory at large scenes.** Geometric growth bounds steady state slack below two times per bucket, but old and new buffers overlap during growth. Typed array allocation can fail or pause long before safe integer validation matters.
2. **High water retention across bucket migration.** Stable slot arrays retain tombstones. A scene that cycles all parts through opaque, translucent, and ghost buckets can retain capacity in every bucket until teardown.
3. **Future attribute initialization.** `growInstancedPartMesh` allocates empty attributes and depends on an immediate full sync. A new caller that grows and then applies only a patch would corrupt unchanged instances.
4. **Future custom attributes.** Generic resizing finds every `InstancedBufferAttribute`, which covers opacity and edge axis today. A future capacity bound resource outside geometry attributes would require explicit growth handling.
5. **Explicit compaction.** Shrinking only meshes, only slot arrays, or only key maps would break addressing and picking. Compaction must be atomic across all three.
6. **Component remounts.** The capacity gate protects prop changes within one mounted production tree. Conditional tree changes or unstable React keys could still dispose materials and compile programs for reasons unrelated to capacity.
7. **Observer coverage.** Existing acceptance gates cannot detect texture, framebuffer, renderbuffer, vertex array, shader object, or driver internal churn.
8. **Physical GPU behavior.** SwiftShader validates API call counts. It cannot validate hardware timing, driver cache behavior, allocation bytes, or frame hitch severity.
9. **Band test scale.** The browser gate crosses a real band with a small scene and covers part, coverage, and selection chrome families. It does not exercise near limit allocation, context loss, or every possible material distribution.
10. **Material churn hidden by program reuse.** Program creation alone could miss a new material that reuses a still live cache entry. The separate stable material and mesh identity assertions close this gap for the tested path.
11. **Boundary upload cost.** A band crossing intentionally performs a full slot sync. The four capacity gates prove amortized resource behavior, but they do not impose a byte or frame time ceiling on that one upload.
12. **Documentation drift.** `PERFORMANCE.md` still presents completed work as an open P1. This can trigger duplicate implementation work or an unnecessary parallel capacity policy.

## Plan

1. Make no source or test change for this P1. The current implementation already matches the stated proposal.
2. Update `PERFORMANCE.md` in a separate authorized change, approximately 15 to 25 lines, to mark stable GPU capacity complete and cite `resolveGeometricInstanceCapacity`, `growInstancedPartMesh`, `observeWebGlResources`, and the browser acceptance test.
3. Preserve power of two growth, stable slot high water capacity, stable mesh and material identity, and full sync only at a band crossing.
4. Keep automatic shrink and chunked pages out of V1.
5. Reopen the design only with measured evidence of a durable target memory breach, a band crossing pause, or a resource class outside the current buffer and program gate.
