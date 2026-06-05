# Cubicell committed store build scout

Status: build slice confirmed against the canonical design on 2026-07-21.

Verified sources:

- Build base: `docs/performance-audit` at `89e3166271b2a3a3822c441edb6df5f56edf9e27`.
- Salvage source: PR #106, `feat/persist-cutover` at
  `362d9a3697105f7fb89b5c0bbdfb7e7f47de1bb2`.
- Canonical design: `~/.mdx/projects/cubicell-design-committed-store.md`.
- The base worktree was clean before this scout. This artifact makes no repository
  change and authorizes no build work.

## 1. Reuse map

### Committed store layout

Required shape: project owned `projects`, `assets`, `poseRevisions`, and
`localCommits`, with `projects.revision` and `assets.committedRevision` as the
ordering authority.

Existing owners on the base:

- `src/persistence/indexedDbSchema.ts:createIndexedDbProjectSchema` owns all
  physical stores and keys. It already recreates stores on upgrade.
- `src/persistence/indexedDbSchema.ts:indexedDbProjectStoreNames` owns the
  transaction store set.
- `src/persistence/recordCodecs/projectRecordCodec.ts:ProjectRecordV1` and
  `encodeProjectRecord`/`decodeProjectRecord` own the project manifest and its
  revision.
- `src/persistence/recordCodecs/structureRecordCodec.ts:StructureRecordV1` and
  `src/persistence/recordCodecs/animationRecordCodec.ts:AnimationRecordV1` own
  asset documents with the existing manifest revision vocabulary.
- `src/persistence/recordCodecs/poseRevisionRecordCodec.ts:PoseRevisionRecordV1`
  owns immutable pose bytes. Its physical key is already
  `[projectId, revisionId]` and is reusable.
- `src/domain/project.ts:ProjectManifest`, `ProjectAssetReference`,
  `getObservedRevision`, and `reconcileProjectAssets` own revision vocabulary.

Required form not found:

- `projects` is currently keyed `[projectId, clientId]`.
- `assets` is currently keyed `[projectId, clientId, assetId]`.
- Asset records have `revision`; no persisted `committedRevision` field exists.
- No `localCommits` store, record, codec, receipt, or index exists.

Build move: retain the codecs and project vocabulary where their semantics still
fit, bump `indexedDbProjectStorageVersion` from 2 to 3, rebuild the physical keys,
add a versioned local commit receipt, and mirror the same model in
`memoryProjectStorage.ts`.

### Client owned pending drafts

Required shape: `drafts[projectId, clientId, assetKey]` with `baseRevision`, an
ordered `pendingOps` envelope log, optional overlay bytes, and branch local failure.

Existing owners on the base:

- `src/persistence/recordCodecs/draftRecordCodec.ts:DraftRecordV1` owns the
  current client draft envelope and validates `projectId` plus `clientId`.
- `src/domain/authoredOperations.ts:AppliedAuthoredOperation` is the required
  replay unit.
- `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:OutboxCommitOperations`
  provides the nonempty per commit envelope shape.
- `src/persistence/indexedDbFailureState.ts:writeFailureState`,
  `readStoredFailures`, and `clearBranchFailureState` provide branch local failure
  behavior that can be adapted.
- `src/persistence/storageRecords.ts:nullAssetKey` already defines the empty
  detached asset sentinel.

Required form not found:

- The current physical key is `[projectId, clientId, commitId]`.
- `DraftRecordV1` stores the current working attachment and pose. It has no
  `assetKey`, `baseRevision`, or `pendingOps`.
- `draftBranchRange` and failure restore assume commit keyed rows.

Build move: replace the draft codec and physical record together. Keep failure on
the client draft row. Delete the commit keyed branch range path once callers move.

### Durable `stagePending` at enqueue

Existing owners on the base:

- `src/state/actions/localAuthoring.ts:createLocalAuthoredOperation` mints the
  durable commit id and records `observedRevision`.
- `src/state/actions/authoredReducer.ts:reduceAuthoredOperationState` produces the
  `AppliedAuthoredOperation` with its inverse.

Required form not found: no `stagePending`, `pendingOps`, or durable enqueue write
exists on `docs/performance-audit`. Local authored actions only update Zustand.

Build move: add `ProjectStoragePort.stagePending` and make
`projectDurability.ts:enqueue` await that strict draft transaction before promote.
Append one commit envelope in FIFO order under every touched asset key. The staged
base comes from the operation's observed revision and the current committed head.

### Atomic revision guarded promote

Required shape: one strict transaction that checks `localCommits` idempotency,
compares expected asset and project revisions, advances committed rows, records one
receipt, adds authored outbox only, and consumes exactly the matching head envelope
from each touched draft.

Existing owners on the base:

- `src/persistence/indexedDbProjectStorage.ts:writePreparedCommit` opens one
  strict read/write transaction across the persistence stores.
- `src/persistence/indexedDbProjectStorage.ts:transactionReceipt` resolves only
  from `transaction.oncomplete` and contains abort, quota, request error, and event
  instrumentation.
- `src/persistence/indexedDbProjectStorage.ts:validateExistingRecords` protects
  immutable pose ids.
- `src/persistence/indexedDbTransactions.ts:afterIndexedDbRequests` and
  `indexedDbTransactionResult` coordinate request completion without awaiting
  inside an IndexedDB transaction.
- `src/persistence/orderedCommitQueue.ts:OrderedCommitQueue.byCommitId` provides
  in memory duplicate coalescing and digest conflict detection.
- `src/persistence/indexedDbProjectStorage.ts:readExistingCommit` and
  `indexedDbSchema.ts:outboxCommitIndex` provide the current durable by commit
  pattern.

Required form not found:

- No `promote`, expected revision compare, `StalePromote`, compare and advance, or
  `localCommits` journal exists.
- `issueCommitWrites` replaces a complete client keyed snapshot and blanket deletes
  the client's draft range before writing one new draft. It cannot be reused for
  head consumption.
- Durable idempotency currently depends on `outbox`; checkpoint commits have no
  independent receipt journal.

Build move: reuse the strict transaction lifecycle and fault harness. Replace the
request set, idempotency source, revision guard, and all write issuance. The guard,
committed writes, local receipt, authored outbox add, history write, and draft head
consume must remain in one transaction.

### Committed first hydration and complete asset reachability

Required shape: read project owned committed state first, eagerly materialize only
the active asset, keep every manifest asset addressable through a client independent
lazy load, then overlay only this client's exact draft.

Existing owners on the base:

- `src/persistence/indexedDbProjectStorage.ts:loadProject` owns the database read
  entry point.
- `src/persistence/indexedDbProjectStorage.ts:loadAsset` and
  `ProjectStoragePort.loadAsset` provide an existing lazy asset seam.
- `src/persistence/projectRecordHydration.ts:hydrateProjectRecords` owns record
  containment and runtime repair.
- `src/persistence/projectRecordHydration.ts:resolveWorking` owns working scene
  selection.
- `src/persistence/projectRecordProjection.ts:projectWorkbenchRecords` owns the
  current project snapshot projection.

Required form not found:

- `loadProject` calls `issueSourceRequests`, which chooses a client branch through
  `outbox.byProjectSequence`.
- Body reads load only the chosen branch's active asset. `loadAsset` repeats that
  branch selection.
- `resolveWorking` treats a client draft as the preferred working scene.
- The projector silently skips manifest assets absent from the loaded library and
  has no explicit change set or complete roster guard.

Build move: delete source branch selection. Read the shared manifest, active asset,
referenced poses, user state, user history, and exact client draft directly. Preserve
lazy inactive bodies through `[projectId, assetId]`. Add `ensureFullRoster` before
projection and make incomplete projection a blocked save.

### Head first `syncForwardRebase`

Existing owners on the base:

- `src/state/actions/authoredReducer.ts:reduceAuthoredOperationState` is the pure
  replay engine. Its `rejectedReduction` result is detected by
  `reduction.applied === null`.
- `src/domain/identity.ts:createDurableId` mints replacement commit ids.
- `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:encodeOutboxCommitRecord`
  and `decodeOutboxCommitRecord` enforce one shared commit id per envelope.
- `src/persistence/orderedCommitQueue.ts:OrderedCommitQueue` provides branch FIFO
  execution.

Required form not found: no rebase, head drain, stale promote recovery, inverse
recomputation, superseded outbox deletion, or committed tip reload exists.
`SupersededStorageCommitError` terminates a stale retry instead of carrying the
work forward.

Build move: add a pure rebase planner around the existing reducer and a coordinator
that drains one durable envelope per promote transaction. Re-read the committed tip
for every envelope, mint one commit id for all operations in that envelope,
recompute every inverse, and atomically replace any superseded outbox record.

### History rekey

Existing owners on the base:

- `src/persistence/recordCodecs/localHistoryRecordCodec.ts:LocalHistoryRecordV1`
  already carries `projectId`, `userId`, and `assetId` without `clientId`.
- `encodeLocalHistoryRecord`, `decodeLocalHistoryRecord`, and
  `hydrateLocalHistoryRecord` own logical history serialization and quarantine.
- `src/persistence/indexedDbSchema.ts:createIndexedDbProjectSchema`,
  `src/persistence/storageRecords.ts:StoredHistoryBytes`, and
  `src/persistence/memoryProjectStorage.ts:historyKey` own the physical client
  dimension.

Required form not found: the physical key is
`[projectId, userId, assetKey, clientId]`; no `[projectId, userId, assetKey]` path or
`baseCommitId` head admission exists.

Build move: remove `clientId` from stored history and both storage implementations.
Retain the logical codec, extend it with committed head admission, and quarantine a
stale history record without changing project data.

### Searches run

The base was searched with `git grep` for:

```text
committedRevision|localCommits|stagePending|pendingOps|baseRevision
syncForwardRebase|StalePromote|expectedRevision|ensureFullRoster|installCommitted
observedRevision|reduceAuthoredOperationState|rejectedReduction|byCommitId
outboxCommitIndex|transaction.oncomplete|durability: 'strict'
issueCommitWrites|draftBranchRange|loadAsset|resolveWorking
clientId.*history|history.*clientId|historyKey|StoredHistoryBytes
LocalHistoryRecordV1|baseCommitId
```

The first two lines produced no required committed store or rebase implementation
matches. The remaining searches identified the partial owners listed above. PR #106
was searched separately for its dispatcher, save state, retry, preference, worker,
and transaction symbols.

## 2. PR #106 salvage map

Reuse selected PR #106 components while rebuilding from the verified base.

| Capability | Reuse without semantic change | Required rework or replacement |
|---|---|---|
| Sole writer wiring | `src/state/actions/localDurabilityPublisher.ts:createLocalDurabilityPublisher` and its reserve/complete ordering can move verbatim. The single dispatch topology in `createCubicellStore`, `createAuthoredDispatcher`, `createAuthoredActions`, `createCheckpointDispatcher`, and `createDocumentActions` is the correct ownership model. | `createAuthoredDispatcher` currently appends directly to in memory `state.outbox`. Pending authorship must enter `drafts` through `stagePending`; `outbox` begins only after promote. The enqueue contract must carry touched keys and expected revisions. Dispatch behavior during `syncing` must preserve FIFO ownership. |
| Save state and failure surface | `src/app/PersistenceStatus.tsx:ProjectOpening` and the blocking failed dialog are reusable. `projectDurability.ts:failureSaveState`, `errorSaveState`, and the rule that `saved` follows the storage receipt are reusable. | `src/state/cubicellState.ts:LocalSaveState` gains `syncing`. `PersistenceStatus` needs that label. `createProjectDurabilityCoordinator`, `drain`, `enqueue`, and `retry` must orchestrate stage, promote, stale rebase, and resume rather than whole snapshot commits. |
| `canRetry` and scoped failure | The `362d9a3` changes to `ProjectStoragePort.getFailure(branch?)`, `ProjectCommitQueues.getFailure(branch?)`, the IndexedDB, memory, and user state adapters, and the default `errorSaveState(..., commitId)` retry policy should be retained. The authored null metadata retry regression remains mandatory. | Draft failure storage must move from commit keyed draft rows to asset keyed pending rows. Stale promote becomes `syncing`, while identity and digest conflicts remain terminal. |
| Legacy localStorage deletion | Removal of Zustand `persist`, `debouncedJsonStorage.ts`, `persistedStateNormalization.ts`, `wireEncode.ts`, and their obsolete persistence tests can be repeated. `preferencePort.ts:loadCubicellPreferences`, `createLocalStoragePreferencePort`, and `clearLegacyProject` can move verbatim. | Land the deletion only with the new runtime activation. Keep `clientId` in session storage for pending provenance; never use it for committed ownership. |
| Atomicity core | Retain `IndexedDbCommitFault`, `IndexedDbTransactionEvent`, strict transaction creation, `transactionReceipt`, request and abort instrumentation, immutable pose checking, `afterIndexedDbRequests`, and the memory parity contract. Retain `segmentedJson.ts`, `taskYield.ts`, `storageFingerprint.ts`, and the projection and hydration worker transport. | Replace `readExistingCommit`'s outbox lookup with `localCommits`. Replace `issueCommitWrites` completely. Rework `writePreparedCommit` requests around the revision guard and head consume. Rework `projectStorageHead` from a full loaded library snapshot to an explicit roster and asset change set. Remove `issueSourceRequests`, `readableOutbox`, `sourceClientId`, and all foreign draft inheritance. |
| Lazy asset and user state support | `projectAssetActions.ts:createProjectAssetActions` and `indexedDbUserProjectState.ts:createIndexedDbUserProjectStateStorage` are good salvage, subject to the new storage port types. | Lazy reads use shared asset keys and validate `committedRevision`. User history moves to its client independent key. |

Hygiene constraint: do not rebuild the 674 line PR #106
`indexedDbProjectStorage.ts` or the 656 line `storageRecords.ts` and then add this
design on top. Split by ownership first. Keep the storage factory thin and place
draft staging, atomic promote, committed reads, and user state in focused modules.
Place pure rebase planning outside `projectDurability.ts`. The PR #106 test driver
is 655 lines and its main persistence unit suite is 681 lines, so committed store
coverage belongs in new focused test and driver modules with shared fixtures.

## 3. Slice plan

The proposed three slice cut is confirmed. Each slice has a narrow contract test
surface. Runtime activation should wait until committed hydration exists, and V1
completion should wait until Slice 3 closes stale writer recovery.

### Slice 1: committed storage and promote contract

Scope:

1. Version 3 schema and project owned keys for projects, assets, poses, local
   commits, and user history.
2. Asset keyed client drafts with `baseRevision`, FIFO pending envelopes, overlay,
   and failure.
3. Storage port vocabulary for `stagePending`, explicit change set projection,
   expected revisions, promote receipt, and typed stale result.
4. Durable stage at coordinator enqueue.
5. One strict promote transaction covering idempotency, revision guard, committed
   advance, authored outbox add, local receipt, history, and exact draft head
   consume.
6. Memory port parity, v2 reset, complete roster enforcement, and the salvaged
   scoped retry policy.

Ownership split:

- `indexedDbProjectStorage.ts`: factory and port composition.
- `indexedDbSchema.ts`: version and physical keys.
- New focused modules: pending draft operations, atomic promote, and committed
  record reads.
- `storageRecords.ts` plus focused record modules: physical validation and
  versioned record preparation without duplicate validators.
- `projectCommitProjection.ts`: explicit changes and expected revisions.
- `projectDurability.ts`: stage then promote orchestration only.

Independent proof: the port can stage and promote without store hydration. Verify
T3, T4 at the raw port boundary, T6b staging restart, T7, T8, T9, T12, and T14.

### Slice 2: committed first hydration

Scope:

1. Shared manifest and active asset read with no source branch lookup.
2. Exact client draft overlay only when its base equals the committed head.
3. Every inactive manifest asset reachable through client independent lazy load
   with typed revision checking.
4. Committed checkpoint as the working canvas when no local draft exists.
5. Outbox used for hosted drain status only and never replayed during hydration.
6. User history admission against the committed head.
7. Salvaged async hydration, worker transport, store factory, save UI, preference
   port, and legacy writer deletion.

Independent proof: seed through the Slice 1 port, then create fresh clients and
hydrate through the Slice 2 reader. A stale draft yields an explicit needs sync
handoff for Slice 3 and never becomes committed authority. Verify T1, T2, T4, T10,
T11, T12, and T13.

### Slice 3: head first sync forward rebase

Scope:

1. Stale promote enters `syncing` and reads the live committed tip.
2. Replay one pending envelope at a time through
   `reduceAuthoredOperationState`, applying every returned update before the next
   operation.
3. Mint one new commit id per envelope, recompute every inverse, promote one
   envelope per transaction, and preserve the unpromoted suffix as the durable
   cursor.
4. Atomically remove each superseded original outbox entry when the reminted
   envelope is written.
5. On contextual rejection, keep already promoted envelopes, delete the entire
   remaining overlay, reload the committed tip, and surface the reload notice.
6. Preserve the Phase 4 ready `installCommitted` contract and provenance input
   without adding Realtime transport, watermarks, ordering, or gap handling.

Independent proof: run the rebase planner against the memory port, then repeat the
crash, competition, and restore cases in real Chromium. Verify T5, T5b, T6, T6b,
T12, T15, and T15b.

### Riskiest seam

`syncForwardRebase` is the single riskiest seam. It combines contextual replay,
inverse recomputation, commit identity reminting, one envelope per revision,
transactional outbox supersession, durable suffix retention across crashes, and
the all remaining overlay rejection policy. A defect can lose work, double sync an
authored commit, collapse journal granularity, or corrupt undo semantics. Keep the
replay planner pure, keep each promote transaction small, and test the coordinator
with injected crash and competing writer boundaries.

## 4. Gates and tests

Real browser persistence tests must continue to launch Playwright Chromium from a
Vite test server. JSDOM or fake IndexedDB cannot sign off storage behavior.

| Slice | Focused unit and memory proof | Real Chromium proof |
|---|---|---|
| 1 | Shared memory and IndexedDB port contract for schema, stage, guard, idempotency, head consume, history key, failure retry, and v2 reset. Projection tests reject partial rosters and validate change sets. | Extend the IndexedDB suite with actual key inspection, same asset competing connections, stage restart, duplicate receipt, digest conflict, and abort, request error, quota, and worker termination atomicity. Assert the draft suffix survives every abort. |
| 2 | Codec and hydration tests for exact committed base, client local overlay, history admission, lazy revision mismatch, and outbox exclusion. Memory and IndexedDB must return the same logical records. | Fresh client exact digest, A/B/C asset reachability, foreign pending and failure isolation, outbox not reapplied, new tab history, 4,500 cube startup, and proof that inactive asset bytes were not read. |
| 3 | Pure reducer driven rebase tests for multi operation envelopes, one shared reminted id, inverse recomputation, reject sentinel, remaining overlay deletion, and install provenance. | Two connections from R, N commit head drain, crash plus third writer between envelopes, reopen and resume, contextual reject mid log, stale outbox removal, exact N receipts, and final exact digest. |

Focused commands after the PR #106 test infrastructure is salvaged:

```sh
pnpm exec vitest run --project unit tests/projectStorage.test.ts tests/projectRecordCodecs.test.ts tests/committedStorePersistence.test.ts
pnpm exec vitest run --project chromium tests/indexedDbStorage.browser.test.ts tests/cubicellStore.browser.test.ts tests/committedStore.browser.test.ts
pnpm lint
pnpm build
git diff --check
```

Final acceptance:

1. Run the complete `pnpm test` suite three times from a clean tree and record the
   observed file and test counts for every run.
2. Run the real Chromium command separately and record its passed test count.
3. PR #106 at `362d9a3` established the supplied baseline of 1,339 passing tests.
   The committed store branch must retain that coverage plus its new cases, with an
   identical total on all three full runs.
4. Run `pnpm lint`, `pnpm build`, and `git diff --check` after the final test edit.
5. Recheck all touched source and test files under 700 lines and all functions near
   or below 150 lines. Consolidate any duplicate memory and IndexedDB contract
   logic before sign off.
