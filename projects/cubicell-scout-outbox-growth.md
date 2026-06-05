# Cubicell outbox growth scout

## Scope

Read only analysis of `main` at `77b779501c78605152d95120165abccc364c15a5`. The IndexedDB counts in the brief were accepted as measured facts and were not rederived. No browser was driven and no runtime probe was run.

## Verdict

The durable queue is **unbounded**. A normal accepted cube offset edit appends:

| Store | New records | Append site |
|---|---:|---|
| `localCommits` | 1 | `src/persistence/indexedDbCommit.ts:completeReceiptWrite` |
| `outbox` | 1 | `src/persistence/indexedDbCommit.ts:issuePromoteWrites` |
| `poseRevisions` | 0 | `src/state/projectCommitProjectionCore.ts:poseProjection`, governed by `src/domain/authoredOperations.ts:authoredBodyPoseRevisions` |

The record cost for this edit is therefore two newly appended records, plus ordinary overwrites of the current materialized Project, asset, history, and user state records in the same transaction. The exact byte cost varies with the encoded authored operation. The current draft checkpoint is overwritten on the active asset rather than appended as another asset row.

## 1. Per edit trace

A cube offset control creates `set-cube-offset` at `src/editor/controlBindings.ts:createCubeOffsetBinding`. The document command materializes it as `{ family: "scene" }` at `src/interaction/commands/document.commands.ts:registerDocumentCommands`.

One accepted local operation produces one durable unit:

1. `src/state/actions/authoredDispatcher.ts:createAuthoredDispatcher` calls `enqueue` once after the authored reduction is accepted. Gesture previews remain outside persistence and the gesture boundary applies one final commit at release through `src/state/actions/historyCoordinator.ts:createHistoryCoordinator`.
2. `src/state/projectDurability.ts:ProjectDurabilityRuntime.enqueue` creates one `AuthoredDurabilityUnit`.
3. `src/state/projectDurability.ts:ProjectDurabilityRuntime.drainQueue` projects that unit with `projectStorageCommitAsync` and calls `storage.promote` once.
4. `src/persistence/storageRecordPreparation.ts:prepareStorageRecords` gives an authored head a nonnull outbox envelope.
5. `src/persistence/indexedDbCommit.ts:issuePromoteWrites` adds that envelope to `outbox`, then `src/persistence/indexedDbCommit.ts:completeReceiptWrite` puts the unique commit receipt into `localCommits`.

The same transaction calls `poseStore.add` only for `plan.poseWrites`. `src/state/projectCommitProjectionCore.ts:poseProjection` derives exact authored pose writes through `src/domain/authoredOperations.ts:authoredBodyPoseRevisions`. That function returns an empty array for every scene operation, including cube offset and placement edits. A cube move therefore adds zero pose revision rows.

Document operations that introduce a pose have a different cost. `capture-state`, `new-state-from-selected`, `update-state`, and `restore-state-pose` normally contribute one pose revision. Restore operations can contribute several. `src/persistence/promoteContract.ts:createPromotePlan` filters revisions already present, so only new revision IDs are added.

## 2. Bound and retention

There is no row count cap, byte cap, time limit, expiry, periodic pruning, reachability collection, or checkpoint driven compaction for `localCommits`, `outbox`, or `poseRevisions`.

The only durable deletions found are narrow exceptions:

* `src/persistence/indexedDbCommit.ts:issuePromoteWrites` deletes a specifically superseded outbox row during a successful rebase. An outbox sourced rebase also adds its replacement, so that path is normally count neutral for `outbox` while adding another `localCommits` receipt.
* `src/persistence/indexedDbOutbox.ts:discardIndexedDbOutbox` deletes explicitly named outbox commit IDs. Its caller, `src/state/projectDurabilityForwardRebase.ts:ProjectDurabilityForwardRebase.sync`, uses it when replay rejects and discards the rejected remainder.
* `src/persistence/indexedDbSchema.ts:createIndexedDbProjectSchema` recreates every store on a schema upgrade, and `src/persistence/indexedDbProjectStorage.ts:deleteIndexedDbProjectStorage` deletes the whole database. These are data resets, not retention policies.

`src/config/cubicellConfig.ts:authoredDurabilityQueueMaxDepth` limits the transient in memory save queue to 1,024 pending authored edits through `src/state/projectDurability.ts:ProjectDurabilityRuntime.reserveAuthored`. Once the queue drains, every settled durable receipt and outbox row remains. This cap does not bound any IndexedDB store.

Searches run, with stderr unsuppressed:

```text
rg -n 'localCommits|poseRevisions|checkpointBytes|outbox' src/persistence src
rg -n 'objectStore\("(localCommits|outbox|poseRevisions)"\)|\.delete\(|\.clear\(|deleteObjectStore|localCommits|poseRevisions|outbox' src/persistence --glob '*.ts'
rg -n -i 'prun|compact|evict|ttl|expir|retention|cap|limit' src/persistence src/state
rg -n 'objectStore\("(localCommits|outbox|poseRevisions)"\).*(add|put|delete|clear)|poseStore\.(add|put|delete|clear)|outboxStore\.(add|put|delete|clear)|localCommits.*(add|put|delete|clear)' src/persistence src/state
rg -n 'deleteIndexedDbProjectStorage|deleteObjectStore|deleteDatabase' src/persistence src/state
```

## 3. Checkpoint ownership and redundancy

`checkpointBytes` is the encoded current working draft, not the result of scanning or compacting a commit log:

1. `src/persistence/projectRecordProjection.ts:projectWorkbenchRecords` encodes the current workbench as the draft record.
2. `src/persistence/pendingDrafts.ts:committedDraftBytes` removes the client ID and serializes that draft as a committed checkpoint.
3. `src/persistence/storageRecordPreparation.ts:prepareStorageRecords` assigns those bytes to the active asset, or to the Project when the workbench is detached.
4. `src/persistence/promoteContract.ts:normalizeAssetRevision` carries the checkpoint into the materialized asset record.
5. `src/persistence/indexedDbProjectReads.ts:loadIndexedDbProjectHydrationBytes` reads it, and `src/persistence/projectRecordHydration.ts:hydrateProjectRecords` uses it to restore the current working pose.

The materialized Project and asset documents plus `checkpointBytes` make settled `localCommits` rows unnecessary for state reconstruction. Hydration does not read `localCommits`. Its two live readers are idempotence and staging guards:

* `src/persistence/indexedDbCommit.ts:issuePromoteReads` returns a prior receipt when the same commit ID is submitted again.
* `src/persistence/pendingDrafts.ts:stageIndexedDbPending` skips staging when that commit ID is already settled.

There is no declared safe horizon for those guards and no code deletes old receipt rows. Nothing is supposed to delete the redundant prefix in the current implementation.

The checkpoint does not make the outbox prefix redundant under the current collaboration contract. `src/state/projectDurabilityForwardRebase.ts:ProjectDurabilityForwardRebase.sync` loads and replays the outbox after an installed committed update. Pose revisions referenced by the current asset document are also required for hydration. Unreferenced pose revisions are not collected.

## 4. Count arithmetic

The three counts measure different things.

### `803 localCommits`

`src/persistence/indexedDbCommit.ts:completeReceiptWrite` writes one receipt for every successful prepared commit, regardless of whether it is authored, a checkpoint, an install, or a rebase. No receipt is later removed.

### `687 outbox`

`src/persistence/storageRecordPreparation.ts:prepareStorageRecords` creates an outbox payload only for an authored head. `src/persistence/indexedDbCommit.ts:issuePromoteWrites` adds it only when `writeKind === "promote"`. Checkpoints and installs therefore add a `localCommits` receipt without adding an outbox row.

The exact difference is `803 - 687 = 116` retained receipts without an extant corresponding outbox row. Under the code invariants, that gap is produced by checkpoint or install receipts, outbox rebases that replace one row while adding a new receipt, and explicit outbox discards. It is not evidence of outbox compaction.

### `committedRevision = 289`

This is the version of the current asset, not a retained commit count. `src/persistence/promoteContract.ts:resultAssetRevisions` advances it only when a commit puts that asset. An install takes the incoming expected revision plus one. Project edits and edits to other assets do not advance this asset. Deleted assets lose their counters with their asset rows, while their historical local receipts and outbox envelopes remain. A rebased envelope can also contain multiple authored operations while advancing a changed asset once.

Therefore 687 is retained authored branch history across the Project lifetime, while 289 is the current asset lineage version. They should not match.

### `131 poseRevisions`

This is the count of distinct immutable pose IDs ever added. Ordinary scene edits add none. Pose introducing document operations and aggregate bootstrap or checkpoint projections add missing revisions through `src/persistence/promoteContract.ts:createPromotePlan`. No reachability collector removes a pose after a State or asset stops referencing it.

## 5. Failure mode

Quota risk is **high**. Both `localCommits` and ordinary authored `outbox` rows grow with successful edits, and neither has a retention bound. A finite browser storage quota can therefore eventually reject the same IndexedDB transaction that persists an edit.

The error path is:

1. `src/persistence/indexedDbCommit.ts:transactionReceipt` rejects on transaction abort with the transaction error, including `QuotaExceededError`.
2. `src/persistence/indexedDbCommit.ts:executeIndexedDbCommit` attempts to persist failure diagnostics with `writeFailureState`. If the quota also prevents that diagnostic write, its catch preserves the staged draft signal. The original commit error is still rethrown.
3. `src/state/projectDurability.ts:ProjectDurabilityRuntime.drainQueue` catches the rejection and calls `src/state/projectDurability.ts:ProjectDurabilityRuntime.handleUnitFailure`.
4. `src/state/projectDurabilitySaveState.ts:failureSaveState` or `src/state/projectDurabilitySaveState.ts:errorSaveState` publishes a blocking failed save state. `src/state/actions/authoredDispatcher.ts:canApplyLocalEdit` then rejects further local edits until retry or recovery.

The current main error is not swallowed. The secondary diagnostic failure may be swallowed because the database is already full, but the main rejection reaches save state. Unbounded growth can still reach the quota root cause behind the prior reload loss incident.
