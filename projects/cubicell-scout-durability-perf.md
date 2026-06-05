# Cubicell durability write cost

Scope: read only audit of `main` at `77b779501c78605152d95120165abccc364c15a5` on 2026-08-04. The repository was clean. The established browser measurements in the brief are accepted as facts. I ran one source tree CPU probe and no IndexedDB probe.

## Verdict

The outbox is dead resident growth and should be deleted. On the 33 State document it accounts for 3,684.2 KB, or 5.35 KB per authored edit. Removing it changes measured resident cost from 8.17 KB to 2.83 KB per authored edit.

That cut barely changes the hot write. Every authored promote rewrites the current local history row. The real document has 887.5 KB across four history rows, or 221.88 KB per row. A representative promote therefore writes at least 259.33 KB before transient draft bytes and any new pose revision. Removing the outbox lowers that bound to 253.98 KB. Persisting one new undo delta instead of rebuilding and replacing the whole history row is the largest available win.

## 1. Write path

### Main thread, synchronous authoring

1. `src/state/actions/authoredActions.ts:createAuthoredActions` receives `dispatchAuthoredEdit` and calls `src/state/actions/localAuthoring.ts:createLocalAuthoredOperation`. This allocates operation and commit IDs, resolves the Project or asset target, and captures the observed revision.
2. `src/state/actions/authoredDispatcher.ts:createAuthoredDispatcher` calls `src/state/actions/authoredReducer.ts:reduceAuthoredOperationState` inside the Zustand update. The reducer validates the operation, constructs the next immutable Workbench, runs a deep value comparison through `src/shared/jsonValueEqual.ts:jsonValuesEqual`, derives the in memory inverse, and records undo.
3. `src/state/actions/historyCoordinator.ts:createHistoryCoordinator` calls `src/state/cubicellHistory.ts:createPresentEntry` and `src/state/documentHistory.ts:pushDocumentHistory`. The entry retains the prior Project and Workbench by reference. The history arrays are shallow copied. No deep history clone occurs here.
4. `src/state/actions/localDurabilityPublisher.ts:createLocalDurabilityPublisher` publishes the accepted edit in synchronous reentry order. It calls `src/state/projectDurability.ts:ProjectDurabilityRuntime.enqueue`, which retains the resulting `CubicellState` reference in one authored durability unit.

There is no debounce. Gesture preview defers publication until the gesture commits, and history batching can reuse one undo entry. Every accepted authored operation still becomes a durability unit. `src/state/projectDurability.ts:ProjectDurabilityRuntime.staging`, `src/state/projectDurability.ts:ProjectDurabilityRuntime.drainQueue`, and `src/persistence/orderedCommitQueue.ts:ProjectCommitQueues.submit` serialize FIFO work without coalescing it.

### Deferred pending write

`src/state/projectDurability.ts:ProjectDurabilityRuntime.stageAuthored` is scheduled on a Promise chain immediately after the edit. It is deferred to a microtask and serialized with earlier stages. It is not debounced.

1. `src/state/projectCommitProjection.ts:projectStoragePending` projects the accepted operation and its base revisions.
2. `src/persistence/pendingDrafts.ts:stageIndexedDbPending` calls `src/persistence/pendingDrafts.ts:preparePendingAppendSeed`, which reuses `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:encodeOutboxCommitRecord` to create an operation only pending envelope.
3. `src/persistence/pendingDrafts.ts:stageIndexedDbPending` opens a strict readwrite transaction over `assets`, `drafts`, `localCommits`, and `projects`. It reads duplicate and revision guards, then `src/persistence/pendingDrafts.ts:writeIndexedDbPending` calls `src/persistence/pendingDrafts.ts:appendPendingDraft` and `IDBObjectStore.put` for each touched key. IndexedDB structured clones the complete draft row, including its pending operation list and any retained overlay bytes.

This transaction is the pre promote reload recovery write. A successful promote later consumes its first operation and updates or deletes the draft through `src/persistence/promoteContract.ts:createPromotePlan` and `src/persistence/indexedDbCommit.ts:writeDraftPlan`.

### Deferred commit projection

After pending staging completes, `src/state/projectDurability.ts:ProjectDurabilityRuntime.drainQueue` calls `src/state/projectDurabilityHydration.ts:ensureFullRoster`, then `src/state/projectCommitProjection.ts:projectStorageCommitAsync`.

The expensive history work happens on the main thread before the projection worker:

1. `src/state/projectCommitProjection.ts:projectStorageHeadAsync` calls `src/state/projectCommitProjectionCore.ts:compactProjectionState` with history encoding enabled for an ordinary authored edit.
2. `src/state/projectCommitProjectionCore.ts:compactProjectionState` calls `src/persistence/projectRecordProjection.ts:projectHistoryRecord`.
3. `src/persistence/recordCodecs/localHistoryRecordCodec.ts:encodeLocalHistoryRecord` encodes both branches. `src/persistence/recordCodecs/localHistoryRecordCodec.ts:encodeBranch` calls `src/state/historyDiff.ts:encodePersistedHistory`.
4. `src/state/historyDiff.ts:encodePersistedHistory` calls `src/state/historyDiff.ts:createHistoryDiff` once for every retained history entry. `src/shared/jsonDiff.ts:createJsonDiff` traverses the Workbench pair with `fast-json-patch`. At depth `N`, one edit performs `N` whole Workbench diff comparisons on the main thread, with `N` bounded at 100 in normal runtime state.

The projection request then crosses the first worker boundary:

1. `src/shared/segmentedJson.ts:stringifySegmentedJson` performs a main thread `JSON.stringify` of the request skeleton. Arrays named `cells` or `c` are removed from the skeleton and serialized in 128 item slices, with `src/shared/taskYield.ts:yieldToMain` between slices. The initial skeleton traversal still runs before the first yield.
2. `src/shared/workerRequestClient.ts:createWorkerRequestClient` calls `Worker.postMessage`, which structured clones the segmented request from the main thread.
3. `src/state/projectCommitProjectionWorker.ts:scope.onmessage` parses the request with `src/shared/segmentedJson.ts:parseSegmentedJsonSync`, then calls `src/state/projectCommitProjectionCore.ts:projectStorageHead`.
4. `src/persistence/projectRecordProjection.ts:projectWorkbenchRecords` builds the changed asset, draft, Project, history, user state, and exact pose records. `src/persistence/poseRevisionRegistry.ts:extendPoseRevisionRegistry` canonicalizes each projected pose and `JSON.stringify`s it once for conflict detection.
5. The projection worker serializes the entire `ProjectStorageCommit` through `src/shared/segmentedJson.ts:stringifySegmentedJsonSync`, then `postMessage` structured clones it back.
6. Main parses the response through `src/shared/segmentedJson.ts:parseSegmentedJson`, yielding between large array segments.

### Deferred storage preparation

`src/persistence/indexedDbProjectStorage.ts:createIndexedDbProjectStorage` passes the projected commit to `src/persistence/orderedCommitQueue.ts:ProjectCommitQueues.submit`. Browser preparation uses a second worker.

1. Main calls `src/persistence/storageRecordPreparationAsync.ts:prepareStorageCommitAsync`. `src/shared/segmentedJson.ts:stringifySegmentedJson` serializes the complete commit again, and `src/shared/workerRequestClient.ts:createWorkerRequestClient` structured clones it to the preparation worker.
2. `src/persistence/storageRecordPreparationWorker.ts:prepare` parses it, then calls `src/persistence/storageRecordPreparation.ts:prepareStorageCommit`.
3. `src/persistence/storageRecordPreparation.ts:prepareStorageRecords` validates every record. It `JSON.stringify`s the complete history, outbox operation record, Project manifest, user Project state, each changed asset, and each projected pose. It also calls `src/persistence/pendingDrafts.ts:committedDraftBytes` to stringify the draft checkpoint.
4. `src/persistence/storageRecordPreparation.ts:preparePoseRevisions` calls `src/persistence/storageFingerprint.ts:storageBytesFingerprint` for every pose byte string.
5. `src/persistence/storageRecordPreparation.ts:prepareStorageCommit` calls `src/persistence/storageFingerprint.ts:storageFingerprint`. That hash traverses every serialized record byte plus JSON serializations of rebase metadata, roster changes, the pending envelope, and failure keys. The outbox bytes participate in this digest.
6. `src/persistence/storageRecordPreparationWorker.ts:prepare` serializes the entire prepared commit again. `postMessage` structured clones it back, and main parses it through `src/shared/segmentedJson.ts:parseSegmentedJson`.

Removing the outbox eliminates one operation record `JSON.stringify`, the corresponding bytes from the full commit fingerprint, its prepared payload transfer, and its IndexedDB clone. It does not remove the two whole commit worker round trips or the history diff work.

### Main thread IndexedDB promote

`src/persistence/orderedCommitQueue.ts:OrderedCommitQueue.pump` calls `src/persistence/indexedDbCommit.ts:executeIndexedDbCommit` after preparation.

1. `src/persistence/indexedDbCommit.ts:promotePreparedCommit` opens one strict readwrite transaction over all stores named by `src/persistence/indexedDbSchema.ts:indexedDbProjectStoreNames`.
2. `src/persistence/indexedDbCommit.ts:issuePromoteReads` reads the Project, changed assets, target poses, touched drafts, local commit duplicate guard, user Project state, and an outbox source only when rebasing from that source.
3. `src/persistence/promoteContract.ts:createPromotePlan` validates revisions and consumes one pending head. `src/persistence/promoteContract.ts:normalizeAssetRevision` parses and stringifies each changed asset document. `src/persistence/promoteContract.ts:committedProject` parses the incoming and stored Project manifests and stringifies the resulting manifest.
4. `src/persistence/indexedDbCommit.ts:issuePromoteWrites` puts the Project on every commit, puts each changed asset, adds new poses, replaces the complete history row, usually puts user Project state, consumes the draft, adds one outbox row, and calls `src/persistence/indexedDbCommit.ts:completeReceiptWrite` to put one local commit row.
5. Each `put` or `add` crosses the IndexedDB structured clone boundary. Transaction completion is asynchronous. All JavaScript planning and API calls above run on the main thread, while the browser storage engine performs the physical transaction work outside JavaScript.

## 2. The 5x

The outbox record is the commit payload. The local commit row is only its receipt.

`src/persistence/recordCodecs/outboxCommitRecordCodec.ts:encodeOutboxCommitRecord` stores the full authored operation body plus its actor, client, commit, operation, target, Project, observed revision, and schema identity. Its record envelope repeats actor, client, commit, and Project identity around the operations array. `src/persistence/storageRecordPreparation.ts:prepareStorageRecords` wraps those JSON bytes again with client, commit, Project, kind, rebase trigger, and later digest and sequence fields defined by `src/persistence/storageRecordTypes.ts:StoredOutboxBytes`.

`src/persistence/indexedDbCommit.ts:completeReceiptWrite` writes `src/persistence/storageRecordTypes.ts:StoredLocalCommit`. That row contains changed asset keys, IDs, kind, digest, origin client, and `src/persistence/storageRecords.ts:storageReceipt`. The receipt contains resulting revision numbers and the outbox sequence. It contains no authored operation body, snapshot, history, asset document, pose, or pending envelope.

Therefore the measured 2.7 KB versus 0.5 KB is expected. The extra 2.2 KB is principally the full authored operation body and its nested identity envelope. On the larger document the operation mix is fatter: 3,684.2 KB divided by 689 records is 5.35 KB per outbox record, while 409.4 KB divided by 805 local commits remains 0.51 KB per receipt.

## 3. History shape

Runtime history uses full Project and Workbench snapshots per entry, but those snapshots share unchanged object structure. `src/state/documentHistory.ts:DocumentHistoryEntry` owns the snapshot shape. `src/state/documentHistory.ts:pushDocumentHistory` shallow copies the stack, and `src/state/documentHistory.ts:documentHistoryLimit` caps the normal stack at 100 entries.

The persisted history is not one full Workbench snapshot per step. `src/persistence/recordCodecs/localHistoryRecordCodec.ts:encodeLocalHistoryRecord` writes one `local-history` record whose steps are backwards RFC 6902 diffs from the current Workbench to each older Workbench. `src/state/historyDiff.ts:encodePersistedHistory` creates those diffs newest to oldest. Every step also stores selection, active State, view policy, and a complete Project manifest through `src/persistence/recordCodecs/localHistoryRecordCodec.ts:encodeBranch`.

The 18.7 KB record after two States is one bounded undo record containing its Workbench difference plus step context. The real document's roughly 220 KB rows contain more and larger diffs and repeat Project metadata per step. The record is bounded by count, not byte size. Runtime authoring caps the combined reachable stack at 100. The encoder slices each branch to 100, and `src/persistence/recordCodecs/localHistoryRecordCodec.ts:decodeLocalHistoryRecord` rejects either physical branch above 100.

Every authored edit rebuilds every retained diff on main and replaces the complete encoded row through `src/persistence/storageRecordPreparation.ts:prepareStorageRecords` and `src/persistence/indexedDbCommit.ts:issuePromoteWrites`. Structural sharing saves runtime memory but is erased by diff generation, JSON serialization, worker transfer, and IndexedDB cloning.

## 4. Cost per edit

Two different quantities matter.

### Resident growth

The controlled sample has 12 authored outbox records and 70.0 KB across the measured stores. This is 5.83 KB resident per authored edit. Removing 32.7 KB of outbox leaves 37.3 KB, or 3.11 KB per authored edit.

The 33 State document has 689 authored outbox records and 5,630.9 KB across the listed stores. This is 8.17 KB resident per authored edit. Removing 3,684.2 KB of outbox leaves 1,946.7 KB, or 2.83 KB per authored edit.

These figures divide final resident bytes by authored commit count. They do not claim cumulative bytes written.

### Bytes written by one current promote

The measurements are snapshots, so they cannot recover the sum of every overwritten historical row. Source proves the current whole row write. The following figures are lower bounds using the measured current row sizes. They exclude transient draft row bytes, browser record overhead, and any new pose revision.

| Corpus | Current history row | Changed asset | Local receipt | Outbox | User plus Project | Today | Without outbox |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Controlled sample | 18.7 KB | 3.1 KB | 0.5 KB | 2.7 KB | 1.2 KB | 26.2 KB | 23.5 KB |
| 33 State document | 221.88 KB average | 30.4 KB | 0.51 KB | 5.35 KB | 1.2 KB | 259.33 KB | 253.98 KB |

A pose authoring edit adds about 1.1 KB per new pose in the controlled sample, plus pose serialization and hashing. Pending draft traffic depends on queue depth because each stage clones the current pending operation list and each promote consumes one head. The final snapshot has zero drafts, so the supplied measurements cannot assign those transient bytes without a write trace.

### Serialization work

Today, one authored edit performs:

* `N` whole Workbench history diffs on main, where `N` is the retained undo depth up to 100.
* Two complete request serializations on main, two complete response parses on main, and four worker structured clone crossings.
* Projection worker record construction, pose canonicalization, pose JSON serialization, and complete commit serialization.
* Preparation worker record validation, at least five fixed record JSON serializations, one per changed asset, one per projected pose, pose hashes, one full commit hash, and complete prepared commit serialization.
* One strict pending IndexedDB transaction and one strict promote transaction, with a structured clone for every affected `put` or `add`.
* Main thread asset and Project parse plus stringify during promote planning.

After outbox removal, the same list remains except for outbox record encoding and stringify, outbox bytes in the full digest, one `outbox.add`, its structured clone, and outbox data carried through the preparation response. History work, changed snapshot work, pending recovery, local receipt, and both worker round trips remain.

## 5. Cheapest correct write

The minimum safe cut within the current architecture is:

1. Keep the operation only pending draft stage. It is the reload recovery record before promotion.
2. Keep one atomic strict promote containing only the changed asset or Project snapshot, new content addressed poses, the user's history update, user state when changed, pending consumption, and the local receipt needed by current retry and duplicate guards.
3. Delete the outbox store write and its dead production install and outbox rebase surface. Keep the draft source branch of `src/state/projectDurabilityForwardRebase.ts:ProjectDurabilityForwardRebase.sync` because pending recovery uses it. The operation envelope codec is shared with drafts and must remain, regardless of its current outbox name.

That cut gives the measured 5.35 KB resident saving per real authored edit and removes one append. It does not solve the dominant current write cost.

The larger correction is to persist one new undo delta per edit and prune the oldest delta above 100, instead of reconstructing and replacing one aggregate history record. Reuse `src/state/historyDiff.ts:createHistoryDiff` for the single adjacent Workbench pair and retain the existing selection, active State, view policy, and Project context. A destructive wire bump is appropriate under the owner directive. At the measured real size, eliminating the 221.88 KB aggregate history rewrite offers about 41 times the byte opportunity of deleting a 5.35 KB outbox row, before counting the `N` main thread diff traversals it also removes.

Structural sharing buys no additional persisted bytes. Runtime history already shares structure, and every persistence boundary materializes it. A smaller outbox envelope cannot beat deleting a record with no reader. An additional checkpoint alone does not help: the committed asset is already the current checkpoint, while undo still requires the bounded deltas. A checkpoint plus an append only undo journal can improve reload reconstruction, but the append only history step is the part that cuts per edit work.

## 6. Measurement

### Established browser measurements

The store counts and sizes in the brief are treated as the authoritative real app evidence. I did not reopen or mutate IndexedDB.

### Probe P1: existing codec capacity test

Command:

`pnpm vitest run tests/projectRecordCodecs.test.ts --project unit --reporter=verbose`

Result: 1 file and 21 tests passed. In its small fixture, `tests/recordCodecMetrics.ts:measureRecord` measured local history construction at 0.021 ms for 810 bytes and outbox construction at 0.006 ms for 511 bytes. In its exact 4,500 cube fixture, `src/persistence/projectRecordProjection.ts:projectWorkbenchRecords` took 23.252 ms and produced a 63,544 byte Structure, a 238,828 byte pose revision, and a 238,828 byte draft.

P1 proves that isolated small envelope constructors are cheap and that whole record projection becomes material at document scale. It does not measure the 33 State document, worker clones, main thread history encoding at depth, IndexedDB transaction latency, or disk time. No exact millisecond split is claimed for those unmeasured phases.

## Answer

Delete the dead outbox for correctness and resident growth. Then change persisted history from an aggregate row rebuilt from all retained snapshots to one appended bounded undo delta per edit. The first cut changes real resident cost from 8.17 KB to 2.83 KB per authored edit. The second targets the roughly 221.88 KB row rewrite and the `N` main thread Workbench comparisons that dominate the current path.
