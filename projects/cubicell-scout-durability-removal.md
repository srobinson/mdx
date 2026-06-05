# Cubicell forward removal map: outbox and hosted-install durability path

Seat A of 4. Repo `/Users/alphab/Dev/LLM/DEV/helioy/cubicell`, branch `main`, clean tree, read-only survey. Builds on the established facts in `cubicell-scout-outbox-ownership.md`, `-history.md`, `-growth.md`, and `cubicell-store-growth.md`; none were re-derived. Owner directives applied: single user, wire bump plus reset, no migration, KISS.

Scope of removal: the `outbox` object store, everything that writes, reads, supersedes, or drains it, and the `installCommitted` remote-install path that is its only trigger. The draft-source forward rebase (crash recovery) is load-bearing and survives.

## 1. DELETE

### Files (whole)

| Target | Reason |
|---|---|
| `src/persistence/indexedDbOutbox.ts` (`loadIndexedDbOutbox`, `discardIndexedDbOutbox`) | Sole callers are the outbox-source sync path and port wiring; `discardIndexedDbOutbox` has never been called in production in repo history. |
| `src/persistence/storedOutbox.ts` (`decodeStoredOutbox`, `projectOutboxEnvelope`, `requiredProjectOutboxEnvelope`) | Decodes outbox rows only; both callers (`indexedDbOutbox.ts`, memory twin `loadOutbox`) die with it. |

### Port and types

| Target | Reason |
|---|---|
| `src/persistence/storagePort.ts:ProjectStoragePort.loadOutbox` | Only production caller is `ProjectDurabilityForwardRebase.sync` with `source === "outbox"`, which is unreachable. |
| `src/persistence/storagePort.ts:ProjectStoragePort.discardOutbox` | Same single unreachable caller. |
| `src/persistence/storagePort.ts:ProjectStoragePort.installCommitted` | Only caller is `ProjectDurability.installCommitted`, which has no production caller (test-only remote-install harness). |
| `src/persistence/storagePort.ts:ProjectOutboxEnvelope` | Envelope shape of outbox rows; all consumers die. |
| `src/persistence/storagePort.ts:ProjectStorageRebase` outbox variant (`source: "outbox"`, `triggerCommitId`) | Only produced by the outbox-source replay; union collapses to the draft variant. |
| `src/persistence/storageRecordTypes.ts:StoredOutboxBytes` | Row type of the removed store. |
| `src/persistence/storageRecordTypes.ts:PreparedStorageCommit.outbox` | The envelope payload appended per authored promote; nothing ever sends it. Removing it also removes the measured 47 to 67 percent byte share and the 2.7 KB per edit write. |
| `src/persistence/storageRecordTypes.ts:PreparedStorageCommit.writeKind` | Only values are "promote" and "install"; "install" is produced solely by `orderedCommitQueue.ts:ProjectCommitQueues.installCommitted`. Collapses to promote-only, deleting every `writeKind === "install"` branch. |
| `src/persistence/storageRecordTypes.ts:ProjectHeaderBytes.outbox` and `RawProjectHeader.outbox` | Populated with `[]` at every read site (`indexedDbProjectReads.ts`, `storageRecordReads.ts`). |
| `src/persistence/storagePort.ts:ProjectStorageReceipt.outboxSequence` | Carries the autoincrement key of the removed store; receipt consumers use `commitId` and revisions. |
| `src/persistence/storagePort.ts:ProjectHydrationBytes.outbox` | Always `[]` on every IndexedDB read path. |

### Schema

| Target | Reason |
|---|---|
| `src/persistence/indexedDbSchema.ts` `"outbox"` entry in `indexedDbProjectStoreNames` and the `createIndexedDbProjectSchema` outbox store creation | Store removal; see WIRE BUMP. |
| `src/persistence/indexedDbSchema.ts:outboxCommitIndex`, `outboxBranchSequenceIndex` | Indexes of the removed store. |
| `src/persistence/indexedDbSchema.ts:branchSequenceRange` | Only consumer is `indexedDbOutbox.ts`; drafts use `draftClientRange`, history uses `historyUserRange`. |

### Commit path

| Target | Reason |
|---|---|
| `src/persistence/indexedDbCommit.ts:issuePromoteReads` `supersededOutbox` request and `PromoteRequests.supersededOutbox` | Reads the superseded outbox row for a rebase. Draft-source rebase supersedes a commit that never landed, so the lookup only ever hits for the unreachable outbox source. |
| `src/persistence/indexedDbCommit.ts:issuePromoteWrites` outbox `add`, the `"request-error"` fault double-add, and the `plan.supersededOutboxSequence` delete | Writers of the removed store. `completeReceiptWrite` is then called directly instead of from the add's `onsuccess`. |
| `src/persistence/promoteContract.ts:validateOutboxSource` | Validates only the outbox rebase source. |
| `src/persistence/promoteContract.ts:PromoteInput.supersededOutbox` and `PromotePlan.supersededOutboxSequence` | Supersede plumbing for the removed store. |
| `src/persistence/storageRecordPreparation.ts` outbox payload block inside `prepareStorageRecords` (the `head.kind === "authored"` envelope with `rebaseTriggerCommitId`) | Sole producer of `PreparedStorageCommit.outbox`. |

### State layer

| Target | Reason |
|---|---|
| `src/state/projectDurability.ts:ProjectDurabilityRuntime.installCommitted`, its `ProjectDurabilityCoordinator.installCommitted` entry, and the coordinator wiring | The only `source === "outbox"` sync call in the repo; no production caller. |
| `src/state/cubicellStore.ts` `installCommitted: durability.installCommitted` handle entry | Exposes the deleted coordinator method upward; only test drivers call it. |
| `src/state/browserRuntimeRetention.ts:CubicellStoreRuntime.installCommitted` | Type slot for the deleted handle. |
| `src/persistence/orderedCommitQueue.ts:ProjectCommitQueues.installCommitted` | Submits with `writeKind: "install"`; dies with the port method. |
| `src/persistence/indexedDbProjectStorage.ts` and `src/persistence/memoryProjectStorage.ts` wiring for `loadOutbox`, `discardOutbox`, `installCommitted` | Port surface shrinks; memory twin also drops its `outbox: Map`, `loadOutbox`, `nextOutboxSequence`, `supersededOutbox` lookup, and outbox set/delete in its commit path. |
| `src/persistence/projectRecordHydration.ts:decodeOutbox`, `HydratedProjectRecords.outbox`, `RawProjectRecordSet.outbox` | Every production read path passes `outbox: []`; no consumer reads the decoded result (`projectCommitProjectionCore.ts` destructures it away). |
| `src/persistence/projectRecordProjection.ts:ProjectRecordSet.outbox` and `ProjectRecordProjectionInput.outbox` | Both projection callers (`src/state/projectCommitProjectionCore.ts`, `src/state/projectDurabilityHydration.ts`) pass `outbox: []`. |
| `src/persistence/indexedDbFailureValidation.ts` `decodeStoredOutbox` re-export | Test-only convenience export of a deleted symbol. |

### Tests and drivers (die with the harness)

| Target | Reason |
|---|---|
| `tests/projectRebaseContract.ts:runInstallPath` | Drives `installCommitted`. |
| `tests/committedStoreBrowserDriver.ts:runAtomicOutboxSupersedeAbort`, `runOutboxRebaseCrashResume` | Drive `runtime.installCommitted` and observe outbox rows. |
| `tests/committedStore.browser.test.ts` "atomically retains the old outbox when supersede aborts" and "resumes an outbox rebase without replaying landed replacements" | Front the two deleted drivers. |
| `tests/projectStorageRebase.test.ts` "atomically supersedes an outbox envelope with its reminted replacement" and "installs authoritative data without consuming drafts or adding outbox" | Outbox supersede and install semantics. |
| `tests/committedStorePersistence.test.ts` "keeps checkpoints out of the hosted outbox sequence" | The store the checkpoint is kept out of no longer exists. |
| `tests/committedStoreBrowserDriver.ts:inspectBranchDurability` outbox field, `tests/projectStorageFixtures.ts:createProjectStorageFixture` outbox field, `tests/cubicellStoreBrowserDriver.ts:createLargeFixture` outbox field | Fixture surface of the removed store. |

## 2. KEEP

| Target | Why load-bearing |
|---|---|
| `src/state/projectDurabilityForwardRebase.ts:ProjectDurabilityForwardRebase` (draft source) | Crash recovery. `ProjectDurabilityRuntime.publishHydration` (pendingRecovery path) and `ProjectDurabilityRuntime.drainQueue` (on `StalePromoteError`) both call `sync` with the default draft source to replay staged pending drafts onto the committed baseline. This is the path that survives a mid-write crash. |
| `src/state/projectForwardRebase.ts:planForwardRebaseEnvelope`, `pendingBranchEnvelopes` | The replay planner the draft path uses. |
| `drafts` store, `src/persistence/pendingDrafts.ts` in full (`stageIndexedDbPending`, `preparePendingAppends`, `appendPendingDraft`, `loadIndexedDbPending`, `mutateIndexedDbPending`, `ProjectStorageStageFence`) | Pre-promote staging is the durability guarantee for in-flight edits; consumed on successful promote via `promoteContract.ts:consumedDrafts`. |
| `localCommits` store, `src/persistence/indexedDbCommit.ts:completeReceiptWrite` | Idempotency ledger. Read by `issuePromoteReads` (same commitId returns the prior receipt, digest mismatch aborts) and `pendingDrafts.ts:stageIndexedDbPending` (skips staging a landed commit). Its unbounded growth is real but is a separate disposition, out of scope here; at 0.5 KB per record it is not the byte problem the outbox is. |
| `src/persistence/recordCodecs/outboxCommitRecordCodec.ts` (`encodeOutboxCommitRecord`, `decodeOutboxCommitRecord`, `OutboxCommitOperation(s)`, `OutboxCommitRecord`) | Misleading name, load-bearing code. It is the authored-operations codec: `storageRecordPreparation.ts:prepareHead` derives commit identity through it, `pendingDrafts.ts:preparePendingAppendSeed` validates staged envelopes through it, and `projectPendingValidation.ts:decodeProjectPendingEnvelope` decodes draft `pendingOps` through it. Survives under rename (see TRIM). |
| `src/persistence/orderedCommitQueue.ts:ProjectCommitQueues` (minus `installCommitted`) | Per-branch FIFO commit serialization for promote and retry. |
| `src/persistence/indexedDbFailureState.ts`, `indexedDbFailureValidation.ts:decodeStoredFailure`, `storageFailureDraft.ts` | Failed-commit diagnostics and retry live on the draft path. |
| Promote pipeline: `storageRecordPreparation.ts:prepareStorageCommit`, `promoteContract.ts:createPromotePlan`, `indexedDbCommit.ts:executeIndexedDbCommit`, plus the preparation and hydration workers | The single write path for every edit and checkpoint. |
| `src/persistence/indexedDbProjectStorage.ts:deleteIndexedDbProjectStorage`, `createIndexedDbProjectSchema` recreate-all upgrade | The reset mechanism the wire bump relies on. |
| `src/state/projectDurability.ts:ProjectDurabilityRuntime` everything except `installCommitted` | Save queue, staging, retry, recovery, capacity gating all serve live editing. |

## 3. TRIM

| Symbol | What shrinks |
|---|---|
| `src/state/projectDurabilityForwardRebase.ts:ProjectDurabilityForwardRebase.sync` | Drops the `source` and `triggerCommitId` parameters, the `loadOutbox` load and filter, the `outboxIndex` walk, and the `discardOutbox` rejection branch. Becomes a draft-only loop over `loadPending`. |
| `src/state/projectDurabilityForwardRebase.ts:ProjectDurabilityForwardRebase.promoteRebasedEnvelope` | Drops `source` and `triggerCommitId` parameters, the "outbox rebase requires an install trigger" throw, and the outbox rebase argument shape; always passes the draft rebase and always calls `removeAuthoredUnit`. |
| `src/state/projectCommitProjection.ts:projectStorageAuthoredCommitAsync` | `rebase` parameter narrows to the collapsed draft-only `ProjectStorageRebase`. |
| `src/persistence/storagePort.ts:ProjectStorageRebase` | Collapses to `{ source: "draft"; supersedesCommitId: string }`; the `source` discriminant itself can go since one variant remains. |
| `src/persistence/projectStorageRebaseValidation.ts:isProjectStorageRebase` | Drops the outbox arm and `triggerCommitId` check. |
| `src/persistence/storageRecordTypes.ts:pendingHeadCommitId` | `rebase?.source === "draft"` condition becomes `rebase !== null`. |
| `src/persistence/promoteContract.ts:createPromotePlan` | Loses `validateOutboxSource` call and `supersededOutboxSequence` output. |
| `src/persistence/promoteContract.ts:validateDraftHeads`, `validateRevisionGuards`, `resultProjectRevision`, `resultAssetRevisions`, `consumedDrafts` | Every `writeKind === "install"` and `rebase?.source === "outbox"` branch deletes; guards become unconditional for their remaining cases. |
| `src/persistence/indexedDbCommit.ts:executeIndexedDbCommit` | `commit.writeKind === "promote" && commit.rebase?.source !== "outbox"` failure-diagnostic condition becomes unconditional. |
| `src/persistence/indexedDbCommit.ts:issuePromoteWrites` | Loses the `writeKind` guard on history, user state, and draft writes, the two outbox adds, the supersede delete, and the `fault === "request-error"` arm of `IndexedDbCommitFault` (that fault only doubled an outbox add). `completeReceiptWrite` loses its `sequence` parameter. |
| `src/persistence/storageRecords.ts:storageReceipt` | Loses the `sequence` parameter and `outboxSequence` field. |
| `src/persistence/storageRecordPreparation.ts:prepareStorageCommit`, `storageRecordPreparationAsync.ts:prepareStorageCommitAsync`, `storageRecordPreparationProtocol.ts`, `storageRecordPreparationWorker.ts` | `writeKind` parameter and protocol field disappear. |
| `src/persistence/orderedCommitQueue.ts:ProjectCommitQueues.submit` | `writeKind` parameter disappears; `promote` is the only entry. |
| `src/persistence/indexedDbProjectStorage.ts` `retry` | Receipt stub loses `outboxSequence: 0`. |
| `src/persistence/indexedDbFailureValidation.ts:decodePreparedCommit` | Key list drops `outbox` and `writeKind`; rebase check narrows with the collapsed union. |
| `src/persistence/projectRecordHydrationProtocol.ts` | Drops the `outbox: bytes.outbox.map(parseRecord)` field. |
| `src/persistence/storagePort.ts:ProjectSnapshotRecords` | `Omit<ProjectRecordSet, "outbox">` becomes identical to `ProjectRecordSet`; collapse to an alias or delete the Omit. |
| `src/state/projectCommitProjectionCore.ts` | The `outbox: []` input and the `{ outbox: _outbox, ...snapshot }` strip both disappear. |
| `src/state/projectDurabilityHydration.ts` | Its `outbox: []` raw record field disappears. |
| Rename for honesty (same pass, no behavior change): `outboxCommitRecordCodec.ts` and its exports (`OutboxCommitRecord`, `OutboxCommitOperation(s)`, `encodeOutboxCommitRecord`, `decodeOutboxCommitRecord`, `outboxCommitRecordSchemaVersion`, recordKind literal `"outbox-commit"`) become authored-commit naming | The codec describes authored operations in drafts and commit heads, not a hosted queue. The recordKind literal is synthesized in `projectPendingValidation.ts:decodeProjectPendingEnvelope`, never stored in the drafts rows, and the wire bump resets everything regardless, so the rename is wire-safe. |
| Docs: `STORAGE.md` (outbox tiers, hosted worker plan), `ARCHITECTURE.md` "eight store" description, `MODEL.v2.md` pending-branch rows, `PERFORMANCE.md` outbox mentions | Describe the removed store and the never-built hosted worker; rewrite to the surviving draft-recovery story and the new store count of seven. |

## 4. EXTRACTED CORE

Nothing needs extraction. The two candidates examined:

- The authored-operations codec is already the shared reusable piece; it survives in place under an honest name (see TRIM). Creating a new module for it would be movement without value.
- The draft-source forward rebase is the durable core of the removed machinery and already lives in its own file with its own planner (`projectForwardRebase.ts`). After the sync trim it is exactly the crash-recovery engine and nothing else.

No hosted-sync abstraction should be preserved "for later". History shows the hosted layer was never built; if it ever is, it will be designed against the then-current wire, not against a preserved queue shape.

## 5. WIRE BUMP

- Constant: `src/persistence/indexedDbSchema.ts:indexedDbProjectStorageVersion` from 8 to 9. Update the version comment to state that version 9 removes the outbox store and the upgrade recreates every store, resetting data.
- New store set (7): `projects`, `assets`, `poseRevisions`, `drafts`, `history`, `localCommits`, `userProjectState` in `indexedDbSchema.ts:indexedDbProjectStoreNames`.
- Mechanism already exists: `createIndexedDbProjectSchema` deletes every object store and recreates the declared set on `onupgradeneeded`. No migration is written, no data is carried, no fallback reads version 8 rows. Opening the app once after the bump resets the database; that is the intended outcome.
- `committedRecordSchemaVersion` (3) and the codec schema version (3) are unchanged; no record shape changes except deletions of never-read fields.

## 6. TEST FALLOUT

This repo has been bitten by a rewrite deleting its own guard tests. Four surviving invariants currently observe themselves through the outbox and must be re-anchored before the store is deleted, not after.

### Dies with the harness (invariant itself is removed)

- `tests/projectRebaseContract.ts:runInstallPath` and its consumers in `tests/projectDurabilityRebase.test.ts` and via `committedStoreBrowserDriver.ts`.
- `tests/committedStoreBrowserDriver.ts:runAtomicOutboxSupersedeAbort`, `runOutboxRebaseCrashResume` and their two `committedStore.browser.test.ts` fronts.
- `tests/projectStorageRebase.test.ts` outbox supersede and install tests.
- `tests/committedStorePersistence.test.ts` checkpoint-out-of-outbox test.
- `tests/browserRuntimeRetention.test.ts` installCommitted stub field.

### Must be rewritten (invariant survives, observation channel dies)

- `tests/committedStoreHydration.test.ts` asserts the draft rebase reminted a new commitId by reading `loadOutbox`. Re-anchor on the receipt or `localCommits` row: the replayed commit's id differs from the superseded one.
- `tests/projectStorage.test.ts` and `tests/indexedDbStorage.browser.test.ts` assert per-branch FIFO promote order via `outboxSequences === [1,2,3,4]` from `tests/projectStorageContract.ts`. The serialization invariant lives in `orderedCommitQueue.ts` and stays; re-anchor on receipt arrival order or `localCommits` insertion order.
- `tests/projectStorageContract.ts` "outbox is excluded from committed hydration" becomes moot, but its neighbors that use `records.outbox[0].id` as the commit handle (also `tests/projectStorageBrowserDriver.ts`, `tests/projectStorageRecordBrowserDriver.ts`, `tests/projectRebaseContract.ts:runHappyPath` and `runRejectedPath`) must take the commit id from the prepared commit or fixture head instead of the outbox record.
- `tests/cubicellStore.browser.test.ts` "keeps a foreign failed draft and outbox branch private": the draft-privacy half survives; drop the outbox half of the assertion.
- `tests/indexedDbFailureValidation.test.ts` "decodes a complete valid failure and outbox row": the failure-decoding half survives; the outbox row half dies with `decodeStoredOutbox`.
- `tests/projectRecordCodecs.test.ts` "persists one outbox commit without a stale inverse body": the invariant (authored operation encoding omits inverse bodies, the very point of wire version 8) survives with the renamed codec; retitle and keep.
- `tests/recordCodecMetrics.ts`, `tests/projectStorageFixtures.ts`, `tests/poseRevisionIntegrity.test.ts`, `tests/selectionQueryDraft.state.test.ts`, `tests/cubicellStorePersistence.test.ts`, `tests/storageRecordReads.test.ts`: mechanical removal of `outbox: []` fixture fields and `outboxSequence` literals.

### Invariants at risk of losing their only guard

1. Promote transaction atomicity under abort. `runAtomicOutboxSupersedeAbort` is the only test that aborts mid-transaction and asserts no partial write survived. Its subject (outbox supersede) dies, but the invariant (all stores commit or none do, via the single `readwrite` transaction in `indexedDbCommit.ts:promotePreparedCommit`) is core. New guard: inject `takeCommitFault: "abort"` on an ordinary promote and assert `localCommits`, `drafts`, `assets`, and `projects` are all unchanged.
2. Per-branch FIFO commit serialization. Currently observed only through outbox sequences (see above); the rewrite must land before the store deletion or the ordering guard goes dark.
3. Draft rebase remint identity. Currently observed only through `loadOutbox` in `committedStoreHydration.test.ts`; re-anchor as described.
4. Checkpoint versus authored distinction. The dying checkpoint test also guarded "checkpoints do not create authored envelopes". Post-removal the observable is `localCommits.kind === "checkpoint"` and untouched draft `pendingOps` after a checkpoint promote; add that assertion to `committedStorePersistence.test.ts` when the old test dies.
5. Wire upgrade reset. `committedStore.browser.test.ts` "resets a legacy version 5 database into the current empty layout" survives and is the bump's guard; update its expected store list to the seven-store set and keep its controlled-red proof (it must fail if a stale store survives the upgrade).

## 7. ORDER

One step per commit, each leaving the tree green.

1. **Re-anchor surviving observations.** Rewrite the FIFO-order, remint-id, and commit-handle observations (contract runners, hydration test, storage tests) from outbox reads to receipt and `localCommits` reads. Add the atomic-abort guard on an ordinary promote and the checkpoint-kind assertion. Test-only commit; the outbox still exists, so old and new guards are both green and each new guard is proven controlled-red by reverting its subject locally before commit.
2. **Delete the install path.** `ProjectDurability.installCommitted`, the coordinator and store handle entries, `CubicellStoreRuntime.installCommitted`, `ProjectStoragePort.installCommitted`, `ProjectCommitQueues.installCommitted`, `writeKind` collapse across preparation, protocol, worker, contract, and both ports, plus `runInstallPath` and the install tests. After this commit the outbox-source sync is unreachable by construction.
3. **Delete the outbox-source rebase.** Trim `ProjectDurabilityForwardRebase.sync` and `promoteRebasedEnvelope` to draft-only, collapse `ProjectStorageRebase` and `isProjectStorageRebase`, drop `loadOutbox` and `discardOutbox` from the port and both implementations, delete `indexedDbOutbox.ts` and `storedOutbox.ts`, delete the supersede read and delete plumbing (`supersededOutbox`, `supersededOutboxSequence`, `validateOutboxSource`), delete the two crash-resume and supersede-abort drivers and their tests.
4. **Stop writing the queue.** Remove `PreparedStorageCommit.outbox` and its producer block in `prepareStorageRecords`, the outbox adds and `"request-error"` fault arm in `issuePromoteWrites`, `StoredOutboxBytes`, `ProjectStorageReceipt.outboxSequence`, and the `storageReceipt` sequence parameter. Fixture outbox fields go here.
5. **Trim the read and projection surface.** `decodeOutbox`, the `outbox` members of `RawProjectRecordSet`, `HydratedProjectRecords`, `ProjectRecordSet`, `ProjectRecordProjectionInput`, `ProjectHydrationBytes`, `ProjectHeaderBytes`, `RawProjectHeader`, the hydration protocol field, the `outbox: []` literals in reads and state, and the `ProjectSnapshotRecords` Omit collapse.
6. **Wire bump.** Schema version 8 to 9, drop the `outbox` store, its two indexes, `branchSequenceRange`, and the store name; update the legacy-reset browser test's expected layout. First launch after this commit resets the database by design.
7. **Name what remains honestly.** Rename the codec file and exports from outbox-commit to authored-commit naming, retitle the surviving codec test, and rewrite the outbox and hosted-worker sections of `STORAGE.md`, `ARCHITECTURE.md`, `MODEL.v2.md`, and `PERFORMANCE.md` to the shipped shape: drafts stage in-flight work, promotes are final, forward rebase is crash recovery.

Steps 2 through 5 could merge pairwise if the builder prefers fewer commits, but step 1 must precede any deletion and step 6 must follow step 4, since the schema cannot drop a store the commit path still opens a transaction over.
