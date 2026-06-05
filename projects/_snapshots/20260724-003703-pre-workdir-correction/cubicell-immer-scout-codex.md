# Cubicell undo history diff scout

Scope: read only review of `main` at `0e3a875`. The repository already contained the untracked `tests/visibilityPersistence.repro.test.ts`; it was left untouched. Focused baseline verification passed 36 tests across `documentHistory`, history persistence, selection undo, lattice repair, debounced storage, and the visibility reproduction.

## Observed failure geometry

`src/state/cubicellState.ts` `CubicellPersistedState`, `src/state/cubicellStore.ts` `partialize`, and `src/state/cubicellHistory.ts` `capPersistedHistory` currently persist `{ document, history, preferences }`. `persistedHistoryLimit` equals `documentHistoryLimit`, so `history.past` contains as many as 100 complete `CubicellDocument` values. Structural sharing keeps the live stack relatively cheap, but `src/state/debouncedJsonStorage.ts` `flush` serializes every entry independently. Its `try` and `catch` logs `cubicell: skipped persisting the workbench` and leaves the previous localStorage value in place after `QuotaExceededError`.

A deterministic probe built 100 gap edits at several scene sizes and measured the JSON payload:

| Cubes | One document | Current payload with preferences | MiB |
| ---: | ---: | ---: | ---: |
| 27 | 39,534 B | 3,999,060 B | 3.81 |
| 64 | 93,295 B | 9,428,921 B | 8.99 |
| 216 | 314,151 B | 31,735,377 B | 30.27 |
| 512 | 744,239 B | 75,174,265 B | 71.69 |

The 64 cube case already exceeds a 5 MiB localStorage budget. The history payload is the dominant term.

## 1. Reuse Map

| Existing path and symbol | Reuse | Change required |
| --- | --- | --- |
| `src/state/documentHistory.ts` `DocumentHistory`, `pushDocumentHistory`, `undoDocumentHistory`, `redoDocumentHistory` | Keep the bounded `past` and `future` stack semantics and redo invalidation. | A replaces entry documents with forward and inverse patches. B leaves the runtime model intact. |
| `src/state/cubicellHistory.ts` `createPresentEntry` | Keep selection reconciliation at the capture belt. | A captures patch metadata beside the reconciled selection. B serializes the existing entry metadata beside each reverse diff. |
| `src/state/cubicellHistory.ts` `applyHistoryStep` | Keep editor restoration, `derivePartEditTarget`, assembly reconciliation, and the returned partial store state. | A derives the document with `applyPatches`. B supplies the reconstructed snapshot and leaves this symbol unchanged. |
| `src/state/cubicellHistory.ts` `withLiveViewLane` | Keep projection and polarity under live session authority during undo and redo. | A must retain the graft for whole document replacement patches. B needs no runtime change. |
| `src/state/cubicellHistory.ts` `capPersistedHistory`, `restorePersistedHistory` | Keep newest first truncation semantics, drop redo on persist, rebuild one edit journal token per restored step, and clear malformed history. | A validates patch pairs. B becomes the wire codec for a reverse patch chain. |
| `src/state/cubicellStore.ts` `recordEdit`, `updateScene`, `applyLatticeEdit`, `replaceDocument` | Keep the single mutation funnel, no op identity guard, history reset, history suppression for the view lane, selection folding, transport pause, and assembly repair. | A must generate patches inside this belt. B leaves it untouched. |
| `src/state/cubicellStore.ts` `historyBatch` | Keep one undo unit per scrub gesture. | A must compose all forward patches in order and all inverse patches in reverse order. B preserves snapshot batching. |
| `src/state/cubicellStore.ts` `partialize` | Keep the persisted slice limited to document, history, and preferences. | A emits patch history directly. B defers conversion until the debounced serialization boundary. |
| `src/state/debouncedJsonStorage.ts` `flush`, `getItem` | Keep max wait scheduling, hidden page flush, last serialized dedupe, and failed write isolation. | B adds a typed encode and decode hook so diff work happens after debounce. A can reuse the current adapter. |
| `src/state/persistedStateNormalization.ts` `normalizePersistedState`, `normalizePersistedScene`, `ensureSceneScore` | Keep current document and preference repair on every rehydrate. | A rejects patch history from a different document schema. B normalizes every reconstructed history document before it becomes undoable. |
| `src/state/selectionAssembly.ts` `reconcileAssemblyAgainstScene`, `remapAssemblySnapshots` | Reuse without persistence. Assembly and assembly journal tokens remain session only. | No storage shape change. A must preserve the call order after patch application. |
| `src/domain/cubeOperations.ts` `applySceneOperation`, `applyCubeOperation` | B reuses all domain code unchanged. | A needs draft recipes at the same dispatch boundaries. |
| `src/domain/cube.ts`, `grid.ts`, `scene.ts`, `neighbors.ts`, `lattice.ts`, `score.ts` | B reuses the current immutable, structurally shared results. | A must route each wired mutation through draft aware cores while retaining pure wrappers for domain callers and tests. |

## 2. LOE A: patch native Immer history

### Target model

Each edit creates `{ patches, inversePatches, selection, selectionSet }`. Undo applies inverse patches to the live document. Redo applies forward patches. Moving an entry between `past` and `future` captures the selection on the side being left, preserving the current snapshot semantics.

`enablePatches()` is required once. `produceWithPatches` supplies the next document and both patch directions. `applyPatches` replays them. Immer documents this use for undo and redo, and also states that generated patches are correct but are not guaranteed to be minimal: [Immer patch documentation](https://immerjs.github.io/immer/patches/).

Wrapping the current immutable operations does not provide useful diffs. A probe on a 64 cube document passed `applySceneOperation` through `produceWithPatches`; Immer emitted one root `replace` patch and the forward plus inverse payload was 186,674 bytes. A direct draft write to `grid.format.gap[0]` emitted one nested patch and the pair was 150 bytes. Fine patches therefore require real draft recipes.

### Complete production touch points

1. Dependency and initialization

   * `package.json` and `pnpm-lock.yaml`: add and pin `immer`. The current lock only mentions Immer as Zustand's optional peer; `pnpm why immer` returns no installed dependency.
   * One state initialization symbol: call `enablePatches()` once. Decide `setAutoFreeze` explicitly after mutation safety tests.

2. History types and algorithms

   * `src/state/documentHistory.ts` `DocumentHistoryEntry`, `DocumentHistoryStep`, `pushDocumentHistory`, `undoDocumentHistory`, `redoDocumentHistory`: replace document snapshots with patch pairs and direction specific selection context.
   * `src/state/cubicellHistory.ts` `createPresentEntry`, `applyHistoryStep`, `capPersistedHistory`, `restorePersistedHistory`, `isPersistedHistoryEntry`: create, apply, validate, persist, and restore patch records. Keep `withLiveViewLane`, editor repair, and assembly reconciliation.
   * `src/state/cubicellState.ts` `CubicellPersistedState`: describe the new patch wire shape.

3. Store capture belt

   * `src/state/cubicellStore.ts` `recordEdit`: recording moves after document production because the patch pair exists only after the recipe runs.
   * `src/state/cubicellStore.ts` `updateScene`: change the arbitrary immutable updater contract to a draft recipe or typed scene operation. Preserve identity no ops, `recordHistory: false`, `resetHistory`, `selectionResult`, score repair, and transport pause.
   * `src/state/cubicellStore.ts` `applyLatticeEdit`: generate patches while retaining `renames` for editor and assembly repair.
   * `src/state/cubicellStore.ts` `replaceDocument`: record a whole document replacement patch. This operation can legitimately remain large.
   * `src/state/cubicellStore.ts` `undo`, `redo`: apply inverse or forward patches, move journal tokens, capture the selection on the departing side, then call the existing reconciliation belt.
   * `src/state/cubicellStore.ts` `historyBatch`: accumulate forward patches chronologically and inverse patches in reverse chronological order. Keeping only the first patch pair would undo only the first scrub update.

   `src/state/cubicellStore.ts` is 685 lines. The repository's 700 line rule requires a cohesive store extraction before this work can add logic.

4. Draft recipe graph

   * `src/domain/cube.ts`: draft cores for `setCubeVisible`, `setCubeDimension`, `setCubeOffsetAxis`, `snapCubeHome`, `resizeCubeAnchored`, `setCubeEdgeState`, `setAllCubeEdgesState`, `setCubeFaceState`, and `setAllCubeFacesState`.
   * `src/domain/grid.ts`: draft cores for `setGridGap` and `setGapOverride`. `remapAxisOverrides` can remain a pure calculator.
   * `src/domain/cubeOperations.ts`: draft forms of `applySceneOperation`, `applyCubeOperation`, `applyPartStateToSelectionSet`, and `applyCubeOperationToCell`.
   * `src/domain/neighbors.ts`: draft forms of `placeCubesAt`, `addNeighborCubes`, and `removeCubesById`.
   * `src/domain/scene.ts`: draft forms of `setScenePolarity`, `setSceneProjection`, `applyGridPreset`, and `resizeGridScene`. Seeds such as `defaultScene`, `createCubeGrid`, and `createCubeCell` remain ordinary constructors.
   * `src/domain/lattice.ts`: draft forms of `insertLatticeLine`, `deleteLatticeLine`, `applyLatticeOperation`, `shiftLattice`, `shiftCells`, and `withAxisOverrides`, with the rename map retained as an out parameter or precomputed edit plan.
   * `src/domain/score.ts`: a draft form of `repairScore` that preserves the current same reference no op behavior at the public wrapper.
   * `src/domain/index.ts`: export the recipe surface from one place.

5. Production adapters

   * `src/interaction/commands/registry.ts` document port type and `src/interaction/commands/document.commands.ts` `registerDocumentCommands`: pass draft recipes or typed operations to the store.
   * `src/app/useSceneOperations.ts` `addNeighborAtSlot`, `addNeighborToSelectedFaces`, `toggleCubeBuilt`, `updateGridComposerDimensions`, and `openGridComposer`: replace immutable scene callbacks with the shared recipe surface.
   * `src/panels/SceneSection.tsx` can retain `replaceDocument` if that action remains a whole document replacement.

6. Persistence and rehydrate

   * `src/config/cubicellConfig.ts` `cubicellStorageVersion`: bump the wire version. Pre release policy allows old history to be cleared instead of migrated.
   * `src/state/persistedStateNormalization.ts` `normalizePersistedState`: validate both patch arrays against the current base, reject a broken chain as a clean history, and keep the present document and preferences.
   * A document schema change requires a storage version bump and a cleared patch history. Rewriting stored patch paths would create a compatibility layer with little value in this pre release repository. The present document continues through the existing normalizer.

### Slices, estimate, blast radius

| Slice | Scope |
| ---: | --- |
| 1 | Extract the document action belt from `cubicellStore.ts`; add Immer and recipe contracts. |
| 2 | Convert cube, grid, and operation dispatch to shared draft cores with pure wrappers. |
| 3 | Convert scene, neighbors, and score repair. |
| 4 | Convert lattice edits and preserve rename, selection, and assembly repair. |
| 5 | Replace snapshot history with patch history, including batch composition and undo or redo selection movement. |
| 6 | Add patch persistence, schema validation, rehydrate, and fail closed behavior. |
| 7 | Complete parity, round trip, performance, full suite, lint, and build gates. |

Estimate: **7 slices, 6 to 9 engineering days**. Blast radius: **high**. The change crosses the document model, every wired scene mutation family, store actions, undo and redo semantics, persistence, and rehydrate.

## 3. LOE B: persisted reverse diffs, snapshot runtime

### Target model

Keep `DocumentHistory` unchanged in memory. Store the current `document` once. Encode each retained past entry as `{ reversePatch, selection, selectionSet }`, where `reversePatch` transforms the next newer document into that entry's document.

Encoding starts at the present document and walks `history.past` from newest to oldest. Rehydrate starts at the persisted present document, applies the same rows from newest to oldest, and places each reconstructed snapshot back at its original index. This produces a contiguous chain and preserves the existing runtime undo implementation.

Use `fast-json-patch` `compare` and `applyPatch` with validation enabled, clone mode enabled, and prototype modification protection enabled. Its format is RFC 6902, its published API includes diff, apply, and validation, and the package reports a 4 KB minified and compressed footprint: [fast-json-patch repository](https://github.com/Starcounter-Jack/JSON-Patch), [RFC 6902](https://datatracker.ietf.org/doc/html/rfc6902).

### Touch points

* `src/state/cubicellHistory.ts` `capPersistedHistory`, `restorePersistedHistory`: add the reverse chain codec, retain selection metadata, cap count, enforce a serialized byte budget, validate each patch, and rebuild the existing full snapshot history plus edit journal.
* `src/state/debouncedJsonStorage.ts` `flush`, `getItem`: add typed encode and decode hooks. Encoding must run inside `flush`, after the 200 ms max wait boundary. Running the diff in `partialize` would execute on every Zustand write, including transport and hover churn. Cache the serialized result by document, history, and preferences references so unchanged persisted slices remain cheap.
* `src/state/cubicellStore.ts` `partialize` and `storage`: keep the partial slice and supply the codec. Keep the store edit small enough to remain below the 700 line limit.
* `src/state/cubicellState.ts` `CubicellPersistedState`: separate the in memory persisted slice type from the wire history type.
* `src/state/persistedStateNormalization.ts` `normalizePersistedState`: normalize the present base and every reconstructed document through one shared document normalizer. If any patch is malformed or does not apply, preserve the present document and preferences and clear history.
* `src/config/cubicellConfig.ts` `cubicellStorageVersion`: bump the schema version and add a conservative payload budget. Existing full snapshot history can be discarded under the pre release reset policy.
* `package.json`, `pnpm-lock.yaml`: add and pin `fast-json-patch`.
* `tests/historyPersistence.test.ts` and `tests/state.test.ts`: replace full snapshot wire assertions with reverse patch and quota assertions. Extend `tests/debouncedStorage.dom.test.ts` for deferred codec invocation.

No domain operation, interaction command, view code, runtime undo algorithm, batching path, or selection assembly code changes.

### Probe results

The probe used `fast-json-patch@3.1.1`, serialized the result, parsed it, validated every operation, rebuilt every historical document, and compared all 100 snapshots for exact JSON equality.

| Workload | Current `{document, history}` | Reverse patch payload | Reduction |
| --- | ---: | ---: | ---: |
| 64 cubes, 100 gap edits | 9,428,229 B | 104,617 B | 98.9% |
| 216 cubes, 100 gap edits | 31,734,685 B | 325,473 B | 99.0% |
| 512 cubes, 100 gap edits | 75,173,573 B | 755,561 B | 99.0% |
| 64 cubes, 100 mixed cube edits | 10,626,176 B | 128,174 B | 98.8% |
| 216 cubes, 100 mixed cube edits | 32,933,022 B | 349,075 B | 98.9% |
| 64 cubes, 100 alternating whole lattice shifts | 9,427,941 B | 1,464,429 B | 84.5% |
| 216 cubes, 100 alternating whole lattice shifts | 31,734,397 B | 4,972,885 B | 84.3% |

The lattice case proves that count alone cannot guarantee a successful write. The encoder should add newest rows until a conservative payload budget is reached, then stop. A 4 MiB workbench payload budget leaves room under the observed 5 MiB limit and keeps the newest contiguous undo tail. The current document can still exceed localStorage by itself at extreme sizes; that requires a separate storage product decision.

Dependency comparison from the same probe:

* `fast-json-patch@3.1.1`: MIT, zero runtime dependencies, RFC 6902 output, diff plus apply plus validation. npm metadata reports its last modification in 2022. Pin the version and keep corruption tests because maintenance is quiet.
* `jsondiffpatch@0.7.6`: MIT, one runtime dependency, active 2026 publication, about 16 KB minified and compressed. It produced 4.92 MB versus 1.46 MB for 64 cube lattice churn and 11.34 MB versus 4.97 MB for 216 cube lattice churn.
* `microdiff@1.5.0`: very small and dependency free, but supplies comparison without a matching patch application contract. Adding a custom applier would create a new correctness surface.

### Slices, estimate, blast radius

| Slice | Scope |
| ---: | --- |
| 1 | Wire codec, deferred storage hooks, schema version, byte budget, and dependency. |
| 2 | Exact round trip, corruption, quota, view lane, selection, lattice, and debounced invocation tests. |

Estimate: **2 slices, 1.5 to 2.5 engineering days**. Blast radius: **low to medium**, confined to persistence and rehydrate.

## 4. Risks

| Risk | A: patch native Immer | B: persisted reverse diffs |
| --- | --- | --- |
| Undo correctness | High. Patch direction, stack movement, root replacement, and scrub composition all change. Forward patches concatenate in edit order; inverse patches concatenate in reverse edit order. | Medium. Runtime undo remains proven. The wire chain depends on exact newest to oldest ordering and an unmodified base. Validate every patch and clear the full chain on failure. |
| Selection and `selectionSet` per entry | Medium. Patch records cover documents only, so selection context must move between stack sides explicitly during undo and redo. | Low. Copy both fields beside each reverse patch and reconstruct the existing `DocumentHistoryEntry` shape. |
| `withLiveViewLane` | Medium. Fine document patches naturally leave projection and polarity alone, but `replaceDocument` can emit a root replacement. Retain the graft after every apply. | Low. Reconstructed snapshots retain historical view values, and the current `applyHistoryStep` graft keeps the live view authoritative. |
| `gapOverrides` and future schema repair | High. Persisted patch paths are schema coupled. Bump the storage version when document shape changes and clear old history. Normalize the current document before use. | Medium. Reconstruct the raw chain against the raw persisted base, then normalize every result through the same function as the current document. Applying old diffs to a differently normalized base can invalidate array and object paths. |
| Dependency trust | Medium. Immer is actively maintained and purpose built for patch capture, but patch optimality is not guaranteed. Auto freeze and proxy overhead require explicit tests. | Medium. `fast-json-patch` is small, standard based, and dependency free, but its current release is old. Pin it, use validation and prototype protection, and retain a codec level conformance suite. |
| No op and identity behavior | High. Current domain functions deliberately return the original reference for no ops. Draft recipes must produce zero patches and the same result reference for the same cases. | Low. Runtime code is unchanged. Empty diffs remain valid. |
| Runtime and rehydrate cost | Medium to high. Every edit crosses Immer proxies. Broad lattice mutations generate many forward and inverse operations. | Medium. Encoding is cheap with current structural sharing when deferred. Rehydrate rebuilds full snapshots and therefore retains the current post reload memory cost. The probe decoded 100 simple entries in about 174 ms for 216 cubes and 406 ms for 512 cubes on this machine. |
| Quota bound | Medium. Fine patches are usually small, but Immer does not guarantee minimal output. A byte budget is still prudent. | Medium. Typical edits are compact; whole lattice churn can approach the quota. Enforce a byte budget in addition to the 100 entry cap. |

## 5. Recommendation

Choose **B** for this failure. It fixes the serialization boundary that causes `QuotaExceededError`, preserves the proven runtime history and mutation graph, and has measured reduction on representative documents. Add a 4 MiB payload budget so structural churn cannot recreate the failure. Keep diff work inside the debounced flush and cache by persisted slice references.

Migration path:

1. Ship B with wire schema version 7. Preserve the current document and preferences. Clear unrecognized history rather than carrying a full snapshot compatibility path.
2. Consider A only if a patch native runtime is later needed for collaboration, audit, or live memory reduction.
3. If A becomes valuable, first convert domain operations to shared draft recipes while retaining snapshot history. This isolates semantic parity from history mechanics.
4. After every production mutation emits fine patches, replace runtime history and scrub composition, then remove the B codec and bump the wire schema again.

Round trip test strategy:

1. Build deterministic chains containing cube part changes, visibility, resize, add and remove, grid gap, gap overrides, lattice insert and delete, score repair, whole document replacement, active selection, and multi selection.
2. Encode, stringify, parse, validate, decode, and assert every reconstructed document and selection field equals the original entry.
3. Simulate reload, undo every step, redo back to the present, and compare a digest after each transition.
4. Interleave polarity and projection changes with edits. After reload, assert undo and redo preserve the live view lane.
5. Feed malformed operations, invalid paths, truncated chains, and prototype paths. Assert the present document and preferences survive while history and its rebuilt journal clear.
6. Use a quota enforcing `Storage` test. A 64 cube, 100 edit state must persist and rehydrate below 5 MiB. A worst case lattice chain must trim oldest rows and still save.
7. Spy on the deferred codec while transport writes faster than the 200 ms interval. Assert one encode per flush window and no repeated localStorage write for an unchanged serialized payload.
8. Run `pnpm test`, `pnpm lint`, and `pnpm build` after implementation. The build command is the repository's effective TypeScript gate.
