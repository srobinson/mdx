# Cubicell durability: target shape

Seat B of 4. Repo `/Users/alphab/Dev/LLM/DEV/helioy/cubicell`, `main` at `77b7795`, read-only.
Question answered: what should durability look like for this application, and how much of
today's design survives contact with that answer.

The short version, stated up front because it changes how the rest reads:

**Today's design is already a snapshot store. The commit log is bolted on top of it and
nothing reads it.** Every promote transaction overwrites the whole materialized document
(`projects` put, changed `assets` put, `history` put, `userProjectState` put) and *additionally*
appends to `outbox` and `localCommits`. Hydration
(`src/persistence/indexedDbProjectReads.ts:loadIndexedDbProjectHydrationBytes`) reads
`projects`, `assets`, `poseRevisions`, `drafts`, `history`, `userProjectState` and passes
`outbox: []` unconditionally. Undo reads only `history`. So the target shape is not a new
design. It is the design that is already running, with the append-only half removed and the
concepts that only that half needed removed with it.

---

## 1. REQUIREMENTS

Stated as invariants. These are what durability must provide; everything else is a candidate.

**D1 — Reload fidelity.** After reload the app presents the last accepted authored state, or a
strictly earlier accepted state. Never a torn mixture of two states.

**D2 — Undo depth survives reload.** After reload, undo and redo reach back
`src/state/documentHistory.ts:documentHistoryLimit` accepted steps on the active asset, with
selection and active-State pointer restored per step.

**D3 — Single writer.** One user, one browser, one process authoring one document. No commit
was authored against a base this process did not itself write. There is therefore no conflict
to detect and nothing to reconcile.

**D4 — The document is a whole.** Project manifest, assets, and poses reconstruct the document
with no replay of operations. Export is a read of what is already stored, not a fold over a log.

**D5 — Bytes are a function of the document, not of the session.** Stored size is
O(document size + undo depth + asset count). It is not a function of edit count, session count,
or tab count. *This is the invariant today's design violates, and the only one it violates.*

**D6 — Failure is visible.** A write that does not land leaves the previous state intact and
publishes a blocking save state. No silent loss.

D4 is worth flagging: there is no document export in the codebase today. `src/export/` is
`streamRecorder.ts` and `recordingConfig.ts`, which record video. No command, no serializer.
D4 is therefore an unmet requirement that the target shape must make trivial rather than a
behaviour to preserve.

---

## 2. TARGET SHAPE

### Store set: 8 → 5

Keep `projects`, `assets`, `poseRevisions`, `history`, `userProjectState`.
Drop `outbox`, `localCommits`, `drafts`.

| store | key | holds | grows with |
|---|---|---|---|
| `projects` | `projectId` | manifest bytes, roster, revision, checkpoint bytes when detached | 1 row, fixed |
| `assets` | `[projectId, assetId]` | asset document bytes, `checkpointBytes` for the active asset | asset count |
| `poseRevisions` | `[projectId, revisionId]` | canonical pose bytes + content hash | distinct reachable poses |
| `history` | `[projectId, userId, assetKey]` | encoded undo/redo stack | asset count × undo depth |
| `userProjectState` | `[projectId, userId]` | active asset/State, panel layout | 1 row, fixed |

`userProjectState` stays separate rather than folding into `projects` because
`src/state/projectDurability.ts:ProjectDurabilityRuntime.checkpointUserProjectState` writes it
on panel-layout changes with no authored operation. A light write path that does not touch the
document is worth one store.

`history` stays separate rather than folding into the asset record because
`ProjectStoragePort.loadAsset` (asset switch) must not drag a ~220 KB undo stack into a read
that only needs the document.

### What a write is

One IndexedDB `readwrite` transaction per accepted authored operation, serialized by the
existing FIFO queue (`src/persistence/orderedCommitQueue.ts:ProjectCommitQueues`), containing
exactly:

```
put   projects[projectId]                        <- manifest + roster + revision + 1
put   assets[projectId, assetId]                 <- for each changed asset; checkpointBytes on the active one
add   poseRevisions[projectId, revisionId]       <- for pose ids not already present
put   history[projectId, userId, assetKey]       <- encoded undo stack
put   userProjectState[projectId, userId]        <- unless a lighter user-state write is in flight
```

That is `src/persistence/indexedDbCommit.ts:issuePromoteWrites` with four lines removed: the
`outbox` add, the superseded-outbox delete, the `localCommits` put, and the draft plan. Nothing
is added.

There is no separate staging write. The edit is applied in memory, projected, and committed in
one transaction. `src/state/projectDurability.ts:ProjectDurabilityRuntime.stageAuthored` and the
`staging` promise chain go away, which halves durable writes per edit.

Revision counters stay on `projects` and `assets` as a monotone document version: they are the
export identity and they back the cheap read guard
`src/persistence/storagePort.ts:StaleProjectAssetError`. The *preconditions* built on them go
away (see §4, item 5). A counter is not the same concept as optimistic concurrency control.

### Pose reachability sweep

This is the one genuinely new element, and it exists because it is the only unbounded growth
left after `outbox` and `localCommits` go. Measured: 131 `poseRevisions` rows against a 33-state
document; ~4 rows retained per live State. Nothing collects a pose after the State or history
step referencing it is gone.

A write already computes the complete reachable pose set:
`src/persistence/projectRecordProjection.ts:collectPoseRecords` walks the workbench plus every
history step. So a sweep is a cursor over `poseRevisions` in the same transaction, deleting rows
whose `revisionId` is not in that set. Run it on checkpoint commits only, not on every authored
edit, so the cursor cost lands on the path that already touches everything.

Cheaper alternative worth measuring first: stop *writing* history-only poses. Undo does not read
them. `src/persistence/recordCodecs/localHistoryRecordCodec.ts:hydrateLocalHistoryRecord`
reconstructs each step's workbench from the stored diff ops, which carry the pose inline, and
seeds `extendPoseRevisionRegistry` from the present workbench. A `poseRevisions` row is only ever
read via `src/persistence/storageRecordReads.ts:poseRevisionIds`, which reads the *asset*
document's references. Rows reachable only from history are written and never read. Narrowing
`collectPoseRecords` to the committed roster removes most of the garbage without a sweep at all.

### What undo reads

Unchanged, and this is the load-bearing fact of the whole report. Undo reads one record:
`history[projectId, userId, assetKey]` → `decodeLocalHistoryRecord` → `hydrateLocalHistoryRecord`
applied against the hydrated present. In memory it is
`src/state/documentHistory.ts:undoDocumentHistory` over structurally-shared workbenches.

Undo has never read `outbox`, `localCommits`, or `drafts`. The commit log and the undo stack are
two unrelated mechanisms that happen to be written by the same transaction.

---

## 3. WHAT SURVIVES

Reused unchanged or near-unchanged. This is the larger half of the answer.

**Undo, entire.** Nothing here is touched.
- `src/state/documentHistory.ts:documentHistoryLimit`, `:pushDocumentHistory`, `:undoDocumentHistory`, `:redoDocumentHistory`
- `src/state/historyDiff.ts:encodePersistedHistory`, `:applyHistoryDiff`, `:createHistoryDiff`
- `src/state/cubicellHistory.ts:applyHistoryStep`, `:createPresentEntry`
- `src/persistence/recordCodecs/localHistoryRecordCodec.ts:encodeLocalHistoryRecord`, `:decodeLocalHistoryRecord`, `:hydrateLocalHistoryRecord`

**Record projection and codecs.** The document encoding is correct and stays.
- `src/persistence/projectRecordProjection.ts:projectWorkbenchRecords` (drops its `outbox` field)
- `src/persistence/recordCodecs/structureRecordCodec.ts:encodeStructureRecord`, `:decodeStructureRecord`
- `src/persistence/recordCodecs/animationRecordCodec.ts`, `:projectRecordCodec.ts`, `:poseRevisionRecordCodec.ts`, `:userProjectStateRecordCodec.ts`, `:draftRecordCodec.ts`, `:localCheckpointRecordCodec.ts`
- `src/persistence/poseRevisionRegistry.ts:extendPoseRevisionRegistry`, `:poseRevisionRecords`, `:PoseRevisionConflictError`
- `src/persistence/storageFingerprint.ts:storageBytesFingerprint` (pose content hash)
- `src/persistence/committedPoseIntegrity.ts:assertCommittedPoseIntegrity`

**Roster projection.** The manifest/roster fold survives; only the guards around it go.
- `src/persistence/promoteContract.ts:committedProject`, `:applyRosterChanges`, `:sameRoster`, `:normalizeAssetRevision`, `:resultProjectRevision`, `:resultAssetRevisions`

**Checkpoint bytes.** The working overlay. Survives as a concept and as code; it must move out of
`pendingDrafts.ts` when that file goes, not be rewritten.
- `src/persistence/pendingDrafts.ts:committedDraftBytes`

**Reads and hydration.**
- `src/persistence/indexedDbProjectReads.ts:loadIndexedDbProject`, `:loadIndexedDbProjectHydrationBytes`, `:loadIndexedDbAsset`
- `src/persistence/storageRecordReads.ts:rawProjectHeader`, `:rawAssetRecords`, `:poseRevisionIds`, `:assembleRawProjectRecords`, `:historyCommitMatches`
- `src/persistence/projectRecordHydration.ts:hydrateProjectRecords`, `:hydrateProjectAssetRecords` (drop `decodeOutbox` and the pending arm)

**Save queue and transaction plumbing.**
- `src/state/projectDurability.ts:ProjectDurabilityRuntime.enqueue`, `:drainQueue`, `:checkpoint`, `:hydrate`, `:reserveAuthored`
- `src/config/cubicellConfig.ts:authoredDurabilityQueueMaxDepth`
- `src/state/projectCommitProjection.ts:projectStorageCommitAsync`, `:projectStorageCheckpointAsync`
- `src/persistence/orderedCommitQueue.ts:ProjectCommitQueues` (FIFO serialization survives; its failure-restore surface shrinks)
- `src/persistence/indexedDbTransactions.ts:afterIndexedDbRequests`, `:indexedDbTransactionResult`
- `src/persistence/indexedDbCommit.ts:issuePromoteWrites`, `:transactionReceipt` (minus four write lines)
- the three offload workers: `storageRecordPreparationWorker.ts`, `projectCommitProjectionWorker.ts`, `projectRecordHydrationWorker.ts`

**Test double.** `src/persistence/memoryProjectStorage.ts:createMemoryProjectStorage` stays as the
port's memory twin and shrinks with the port.

Count: **32 symbols reused.**

---

## 4. WHAT DISSOLVES

Each with the concept it was solving for.

**1. `outbox` store.** Concept: an at-least-once delivery queue to a server. Never had a consumer;
seat A of the prior survey established `discardIndexedDbOutbox` has no production caller and the
history survey established no drain worker ever existed on any branch.
Goes: `src/persistence/indexedDbOutbox.ts` (whole file), `src/persistence/storedOutbox.ts` (whole
file), the `outbox` store and both its indexes in
`src/persistence/indexedDbSchema.ts:createIndexedDbProjectSchema`,
`ProjectStoragePort.loadOutbox`/`.discardOutbox`.

**2. `localCommits` store.** Concept: commit idempotency across an unreliable channel — "did this
commit id already land?". A single in-process FIFO queue knows the answer without a durable
ledger. Append-only with no delete path anywhere; 805 rows on the 33-state document.
Goes: the store, `src/persistence/indexedDbCommit.ts:completeReceiptWrite`'s put and the prior-receipt
read in `:issuePromoteReads`, `StoredLocalCommit`.

**3. `drafts` store and the whole staging path.** Concept: a write-ahead log protecting the window
between "operation accepted in memory" and "promote transaction committed", plus a durable record
of a failed commit so it can be retried after reload. The window only exists because there are two
writes; one write closes it.
Goes: `src/persistence/pendingDrafts.ts` (except `committedDraftBytes`),
`src/persistence/projectPendingValidation.ts`, `src/persistence/storageFailureDraft.ts`,
`src/persistence/indexedDbFailureState.ts`, `src/persistence/indexedDbFailureValidation.ts`,
`ProjectStoragePort.stagePending`/`.loadPending`/`.discardPending`,
`src/persistence/pendingDrafts.ts:ProjectStorageStageFence`.

**4. Forward rebase.** Concept: operations authored against a base that moved underneath them —
i.e. a second writer. D3 says there is none.
Goes: `src/state/projectDurabilityForwardRebase.ts` (whole file),
`src/state/projectForwardRebase.ts` (whole file), `src/state/projectPendingHydration.ts`,
`src/persistence/projectStorageRebaseValidation.ts`, `ProjectStorageRebase`,
`PromotePlan.supersededOutboxSequence`.

**5. Optimistic concurrency control.** Concept: detect that stored revisions moved since the
operation observed them. With one writer the precondition is trivially satisfied on every write,
and its only failure handler is the rebase machinery in item 4.
Goes: `src/persistence/promoteContract.ts:validateRevisionGuards`, `:validateDraftHeads`,
`:validateOutboxSource`, `src/persistence/storagePort.ts:StalePromoteError`,
`ProjectStorageAssetChange.expectedRevision` as a precondition. The counters themselves stay.

**6. Remote install.** Concept: an authoritative commit arriving from a server.
Goes: `src/state/projectDurability.ts:ProjectDurabilityRuntime.installCommitted`,
`ProjectStoragePort.installCommitted`, `PreparedStorageCommit.writeKind === "install"` and every
`install` branch in `promoteContract.ts`,
`src/state/browserRuntimeRetention.ts:CubicellStoreRuntime.installCommitted`.

**7. `clientId` / the branch.** Concept: this device's divergent line of history.
`src/state/preferencePort.ts:loadCubicellPreferences` mints it into **sessionStorage**, so every
new tab is a new branch — which means `outbox` and `drafts` rows written by a closed tab are
orphaned permanently, unreachable even by the drain that never runs, since
`ProjectDurabilityForwardRebase.sync` only loads the current branch. Not previously reported and
it compounds the growth measurement.
Goes: `clientId` from `ProjectStorageAddress`, `projectStorageBranchKey`, `ProjectStorageBranch`,
the sessionStorage client key. `userId` stays: `history` is keyed by it and it is localStorage-stable.

**8. Commit digest as durable identity.** Concept: content-addressed dedupe of a replayed commit.
Goes: `src/persistence/storageFingerprint.ts:storageFingerprint` over the whole prepared commit
(the *bytes* fingerprint used for pose content hashes survives), `PreparedStorageCommit.digest`,
`ProjectStorageReceipt.outboxSequence`.

Net: three stores, roughly nine files, and two whole concepts (branch, rebase) leave.

---

## 5. HONEST COST

The target shape is worse at five things. Four are acceptable under the owner directives; one
needs a decision.

**1. The last in-flight edit is lost on a crash.** Today, `stageAuthored` writes the operation
durably *before* the promote, so a tab killed mid-commit can replay it on reload. Target: if the
single transaction does not commit, the edit is gone and storage holds the previous state.
The exposure is one IndexedDB transaction wide. The user just made that edit and can remake it.
This is the price of halving the writes, and it is the right trade for a single author — but it
is a real capability being deleted, not an equivalent rewrite.

**2. No retry-after-reload for a failed save.** `readStoredFailures` currently reconstitutes a
failed commit at storage open so the UI can offer retry across a reload. Target: reload lands on
the last good snapshot and the failed edit is gone. For the quota failure that actually happened
(see the persistence-quota lesson) this is arguably the correct behaviour rather than a loss, but
it removes a path that exists and is wired to save state.

**3. The audit trail goes.** `outbox` + `localCommits` together are a complete log of every
authored operation on the document. Nothing reads it, but deleting it forecloses session replay,
operation-level debugging of "how did this document get into this shape", and any future server
sync — which would want operations, not snapshots. **This is the actual bet being placed: no
server, ever.** The owner directives say exactly that. It should be recorded as a decision, not
discovered later as a constraint.

**4. Two tabs silently last-writer-wins.** Today two tabs are two branches that in principle
reconcile through rebase (in practice they do not, because the drain never runs). Target: the
second tab's writes overwrite the first's with no detection. "One browser" does not by itself mean
one tab, and a second tab is the accessible failure. **This one needs a decision.** The cheap
answer is a single-writer claim — a `projects` row field holding the live session id, refused on
open if held — which is a few lines against the several files of rebase machinery it replaces.
Recommend taking it in the same change.

**5. Rebuild cost is real and concentrated in tests.** Every removed concept has contract tests
attached (`tests/projectRebaseContract.ts`, `tests/projectStorageRebase.test.ts`,
`tests/committedStoreBrowserDriver.ts` are the ones the prior survey named). Those tests are the
current specification of the invariants. Deleting the feature deletes its guards; whatever survives
must be re-guarded deliberately, on the snapshot invariants D1/D2/D5, before the removal is called
done.

---

## 6. SEPARATE CONCERN: `history`

**The target shape does not change `history`, and should not pretend to.** It is a different
growth shape from the commit stream and it needs its own decision.

What it is: one record per `[projectId, userId, assetKey]`, `put` not `add`, holding up to
`documentHistoryLimit` = 100 past and 100 future steps, each step a base-relative RFC-6902 diff
of the workbench (`encodePersistedHistory`) *plus a full `ProjectManifest`*
(`localHistoryRecordCodec.ts:LocalHistoryStep.project`).

**It is bounded per record.** 18.7 KB after two states, ~220 KB per record on the 33-state
document. Once the stack reaches 100 steps the record converges; it does not grow with edit count.
So it is not the same failure as the outbox and it is not urgent.

**It is not bounded across records, and that is a live defect.** The 33-state snapshot showed
**4 history records against a roster of 1 asset**. `issuePromoteWrites` deletes an asset row on
asset delete and never deletes the matching history row; the only history deletion in the codebase
is `src/persistence/indexedDbRecovery.ts` clearing the whole user range during recovery. So every
deleted asset leaks a ~220 KB undo stack forever. That is ~660 KB of the measured 887 KB, and it is
a one-line fix in the same transaction that already deletes the asset. **Do this one with the store
change** — it is a delete on a store that survives, so it is independent of everything else here.

**The remaining two are optimizations, not defects, and want measurement first.**

- *Per-step manifest duplication.* Each of 100 steps carries a near-identical `ProjectManifest`.
  Diffing it against the present the way the workbench already is would cut the record
  substantially. `applyHistoryDiff` is generic over JSON and would need no new machinery.
- *Write amplification.* The real cost is not 220 KB at rest, it is rewriting 220 KB on **every
  single authored edit**, since `issuePromoteWrites` puts the whole history record every promote.
  On the 33-state document that is ~24 rewrites of a 220 KB blob per authored State. This is very
  likely the dominant write cost in the application and it is invisible in a records-and-bytes
  snapshot. **Measure the promote transaction duration before and after touching it.** Nothing in
  the prior reports measured time; they measured size.

---

## Verdict

The target shape is today's materialized-document store with the never-consumed commit log removed
and the multi-writer concepts that only the log needed removed with it: 8 stores to 5, two durable
writes per edit to one, and the branch and rebase concepts gone entirely. 32 existing symbols carry
over; undo is untouched. The honest costs are losing crash-recovery of the single in-flight edit,
losing retry-across-reload, foreclosing a future server, and needing an explicit answer for two
tabs. The `history` store is a separate decision with one real defect in it (orphaned records for
deleted assets) and one unmeasured suspicion (write amplification per edit).
