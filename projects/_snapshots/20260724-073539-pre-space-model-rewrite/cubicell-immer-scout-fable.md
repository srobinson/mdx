# Cubicell undo-history diff scout (Fable)

2026-07-12, main 0e3a875. Read-only scout: immer patch history (LOE-A) vs persist-boundary diff (LOE-B) to fix the QuotaExceededError.

## The core fact the decision turns on

Runtime history is already diff-priced. Domain operations return new objects that share unchanged structure by reference (stated design in `src/state/documentHistory.ts` above `documentHistoryLimit`; visible in `applyCubeOperation`'s `cells.map` in `src/domain/cubeOperations.ts`, which returns untouched cell references). A 100-entry stack in memory costs roughly one document plus the changed slices.

The bloat exists only at the persist boundary: `JSON.stringify` in `src/state/debouncedJsonStorage.ts` explodes that sharing into up to 101 full independent copies of the document (`partialize` in `src/state/cubicellStore.ts` persists `document` plus `capPersistedHistory`, which keeps up to `persistedHistoryLimit = documentHistoryLimit = 100` full entries). A ~50KB scene is enough to breach the ~5MB quota. The state model is not the problem; the encoding is.

A second consequence: because consecutive history entries share references, a reference-aware structural diff between adjacent entries costs O(changed subtree), nearly free. This asset exists today and is exactly what LOE-B exploits.

## 1. Reuse map

Reused untouched by a persist-boundary diff (LOE-B):

- `src/state/documentHistory.ts`: `DocumentHistoryEntry`, `DocumentHistory`, `DocumentHistoryStep`, `pushDocumentHistory`, `undoDocumentHistory`, `redoDocumentHistory`. Runtime shape unchanged.
- `src/state/cubicellHistory.ts`: `createPresentEntry` (capture belt), `applyHistoryStep` (undo/redo restore incl. view-lane graft and assembly reconcile), `withLiveViewLane`, `editorWithReconciledSelection`, `withNormalizedGridFormat` (gapOverrides repair reused verbatim on reconstructed entries), the journal rebuild in `restorePersistedHistory`.
- `src/state/cubicellStore.ts`: `recordEdit`, `updateScene`, `applyLatticeEdit`, `replaceDocument`, `undo`, `redo`, `historyBatch`. All untouched.
- `src/state/persistedStateNormalization.ts`: `normalizePersistedState`, `normalizePersistedScene`, `ensureSceneScore`. One signature change (see B touch points).
- `src/state/debouncedJsonStorage.ts`: unchanged mechanically; optionally hardened (see risks).
- Tests: `tests/historyPersistence.test.ts` `simulateReload` harness and `tests/stateTestHelpers.ts` `createMemoryStorage` are exactly the round-trip rig a diff encoding needs.

Replaced or rewritten per approach:

- LOE-B replaces the bodies of `capPersistedHistory` and `restorePersistedHistory` (`src/state/cubicellHistory.ts`) plus adds one new codec module. Nothing else.
- LOE-A replaces the history entry model itself and the construction discipline of the entire domain layer (below).

## 2. LOE-A: full immer patch history

Each history entry stores `patches` + `inversePatches` instead of a document snapshot; undo applies inverse patches to the present document.

Hard constraint that sets the blast radius: immer only emits granular patches for mutations performed on a draft. Wrapping the existing flow at the store boundary (`produce(document, d => { d.scene = newScene })`) emits one `replace` patch of the whole scene, i.e. a full snapshot again, no size win. So every state-construction site must be re-expressed as draft mutation.

Touch points:

- Domain construction sites, all pure spread-based today: `src/domain/cube.ts` (`setCubeDimension`, `setCubeEdgeState`, `setCubeFaceState`, `setAllCubeEdgesState`, `setAllCubeFacesState`, `setCubeOffsetAxis`, `snapCubeHome`, `setCubeVisible`, `resizeCubeAnchored`), `src/domain/cubeOperations.ts` (`applySceneOperation`, `applyCubeOperation`, `applyPartStateToSelectionSet`), `src/domain/lattice.ts` (`applyLatticeOperation`), `src/domain/neighbors.ts` (`placeCubesAt`), `src/domain/grid.ts` (`setGapOverride`, `setGridGap`), `src/domain/scene.ts` (`setSceneProjection`, `setScenePolarity`, grid format writers), `src/domain/score.ts` (`repairScore`). Roughly 2,000 LOC of the ~5,000 LOC domain layer changes idiom, and every future domain function inherits producer discipline.
- `src/state/cubicellStore.ts`: `recordEdit` (capture patches instead of `createPresentEntry`), `updateScene` (the updater contract itself changes: callers in `src/app/useSceneOperations.ts`, `src/app/useSynchronousEditorCommands.ts`, `src/interaction/commands/document.commands.ts`, `src/interaction/commands/registry.ts`, `src/panels/SceneSection.tsx` pass `applySceneOperation`-built updaters), `applyLatticeEdit`, `replaceDocument` (a document swap has no patches; needs a snapshot-entry escape hatch), `undo`/`redo`.
- `src/state/cubicellHistory.ts`: `createPresentEntry` and `applyHistoryStep` rewritten around patch application; `withLiveViewLane` becomes a patch-path filter problem (see risks).
- `src/state/documentHistory.ts`: entry type and all three stack functions change shape.
- Derived writes outside the mutation: `ensureSceneScore` (`src/state/persistedStateNormalization.ts`, called in `updateScene` and `applyLatticeEdit`) and `historyBatch` merging must fold into the producer or accumulate patches, or entries stop bridging prev to next.
- Persist/rehydrate: patch arrays become the persisted format; `restorePersistedHistory` validates patch shapes; migration from v6 snapshots.
- Tests touching history shape: `tests/documentHistory.test.ts`, `tests/historyPersistence.test.ts`, `tests/selectionUndo.test.ts`, `tests/lattice.storeRepair.test.ts`, `tests/state.test.ts`, plus every test that builds updaters.
- New dependency: `immer` (repo currently has zero utility deps beyond react/three/zustand).

Slice count: ~7 (immer + history types; domain cube ops; lattice/neighbors/grid/scene; store belt + undo/redo; persistence + migration; batching/edge cases; test overhaul). Estimate: 4 to 6 days. Blast radius: high, and permanent (idiom change across Domain and State).

## 3. LOE-B: diff only at the persist boundary

Runtime history stays full snapshots. `partialize` already persists the present `document` in full; encode `history.past` as a backward diff chain hanging off it: `past[i]` stored as a diff from `past[i+1]`, the newest past entry diffed against the present document. `selection`/`selectionSet` per entry are tiny and persist verbatim.

Touch points, all in State:

- New module, e.g. `src/state/historyDiff.ts`: reference-aware structural diff + immutable apply. Because adjacent entries share subtree references, the diff walk short-circuits on `===` and costs O(changed). Cells array diffed keyed by `cell.id` so lattice renames produce per-cell replaces, not whole-array copies. Roughly 200 LOC hand-rolled, zero new dependencies (fits this repo's dependency posture; `microdiff`/`fast-json-patch` are alternatives but neither exploits reference equality).
- `src/state/cubicellHistory.ts`: `capPersistedHistory` becomes encode (snapshot entries in, `{ baseRelativeSteps }` out); `restorePersistedHistory` becomes decode (apply diffs backwards from the normalized present document, then reuse `withNormalizedGridFormat` and the all-'edit' journal rebuild unchanged). Immutable apply restores structural sharing across reconstructed entries, so the next persist after reload diffs cheaply again.
- `src/state/persistedStateNormalization.ts`: `normalizePersistedState` passes the normalized present document into `restorePersistedHistory` as the decode base. One signature change, one call site.
- `src/config/cubicellConfig.ts`: `cubicellStorageVersion` 6 to 7. `migrate`/`merge` already route through `normalizePersistedState`; `restorePersistedHistory` keeps its existing branch for the v6 full-entry array (it already pattern-matches with `isPersistedHistoryEntry`), so old payloads restore losslessly.
- `src/state/cubicellStore.ts`: `partialize` unchanged in spirit (still calls `capPersistedHistory`); optionally `debouncedJsonStorage.ts` hardened: on `QuotaExceededError`, retry once with history truncated instead of silently dropping the entire write (the current swallow is what turned quota breach into "grid edits don't save").
- Tests: extend `tests/historyPersistence.test.ts` round-trip; new `tests/historyDiff.test.ts`.

Slice count: 2 to 3 (codec + tests; wiring + version bump + migration; optional quota fallback). Estimate: ~1 day, 1.5 with the quota fallback. Blast radius: low, confined to `src/state` plus one config constant. Undo/redo semantics untouched.

## 4. Risks

LOE-A:

- Undo correctness vs the view lane: `recordHistory: false` writes (projection, polarity via `isViewLaneSceneOperation` in `src/domain/cubeOperations.ts`) mutate the document between an entry's capture and its undo. Inverse patches touching `scene.projection`/`scene.polarity` would clobber live view state; `withLiveViewLane`'s graft must become a patch-path filter, easy to get subtly wrong. This is the single sharpest correctness risk in A.
- Batching: `historyBatch` currently skips recording within a batch; with patches, skipping breaks the prev-to-next bridge, so batching must switch to patch accumulation.
- `replaceDocument` and `resetHistory` need snapshot escape hatches inside a patch model (mixed entry types).
- Selection/selectionSet per entry: unaffected in either model (stored alongside, not patched).
- immer's default freeze may surprise any downstream consumer that mutates scene objects (none found in Domain, but three/r3f adapters were not audited).
- Dependency trust: immer is well-maintained and ubiquitous; fine, but it is a new axis of trust for the whole state layer, not just persistence.

LOE-B:

- Diff/apply correctness is the whole risk surface, and it is fully containable by a round-trip property test (encode then decode must deep-equal the entries).
- Chain fragility: one corrupt step invalidates all older entries. Mitigation: validate per step on decode and truncate history at the first failure (strictly better than today's all-or-nothing clean slate in `restorePersistedHistory`).
- Worst-case diff size: a lattice insert/delete renames every shifted cell (`applyLatticeOperation` in `src/domain/lattice.ts` rebuilds ids), so one step's diff can approach one snapshot. Bounded and rare; a payload size cap that drops oldest steps closes the residual quota risk.
- View-lane graft, gapOverrides normalization, selection reconcile: all reused as-is (`withLiveViewLane`, `withNormalizedGridFormat`, `applyHistoryStep` untouched), so no new risk.
- Rehydrate-then-persist: JSON.parse breaks reference sharing, but decode-by-immutable-apply rebuilds it, so only a payload that skipped decode would diff expensively. Non-issue in practice.

## 5. Recommendation: B

The memory model is already patch-shaped via structural sharing; only the serialization is snapshot-shaped. LOE-B fixes the actual defect at roughly one fifth the cost of A, with zero new dependencies, no idiom change to Domain, and no touch to undo/redo semantics. A buys nothing at runtime that structural sharing does not already provide, and its view-lane patch filtering and batch accumulation introduce undo-correctness risks that B simply never takes on. If a future feature needs semantic deltas (collaborative editing, op log), revisit A then; it is not needed to fix persistence.

Migration path: bump `cubicellStorageVersion` to 7; `restorePersistedHistory` keeps the existing v6 full-entry branch (already shape-sniffed via `isPersistedHistoryEntry`) and adds the diff-chain branch, so both payloads rehydrate losslessly and no data is dropped on upgrade.

Round-trip test strategy: in `tests/historyPersistence.test.ts`'s existing `simulateReload` rig, drive a mixed edit sequence through real store actions (gap scrub batch, lattice insert and delete, place-cubes, part edits over a selection set), then assert (1) reconstructed history deep-equals the pre-reload `capPersistedHistory` entries, (2) undoing to the bottom of the stack yields identical scenes pre and post reload, (3) the serialized payload with 100 steps stays under a fixed budget (e.g. 10x one document, versus ~101x today), and (4) a payload with one corrupted step decodes to a truncated, still-consistent history.
