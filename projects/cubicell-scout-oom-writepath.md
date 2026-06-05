# Cubicell OOM write path scout

Scope: read only source map of `docs/performance-audit` at
`60da3f7d2fe43da0f3212dc9ee6b9b57d9f79323`, equal to `main` at the time of
inspection. `git status --short` was empty before and after the scout. No source,
test, browser, heap, or runtime mutation was performed.

## Reuse Map

The write path already has one owner at each boundary:

| Responsibility | Existing owner | Evidence |
|---|---|---|
| Transition control emission | `ScrubField` calls `onValueChange` for each pointer move, key step, wheel step, or committed text value | `src/components/ui/scrub-field/ScrubField.tsx:52-60`, `src/components/ui/scrub-field/ScrubField.tsx:72-85`, `src/components/ui/scrub-field/ScrubField.tsx:107-125` |
| Typed transition patch | `MorphInspector` emits `Partial<MorphSettings>` or `Partial<ClassMotion>` | `src/panels/motion/MorphInspector.tsx:73-89`, `src/panels/motion/MorphInspector.tsx:100-137` |
| Document command | `TransitionInspector` creates one `patch-transition` document command per emitted value | `src/panels/motion/MotionInspector.tsx:251-283` |
| Authored operation | The document command registry calls `dispatchAuthoredEdit`; local authoring assigns fresh operation and commit IDs | `src/interaction/commands/document.commands.ts:8-22`, `src/state/actions/authoredActions.ts:31-35`, `src/state/actions/localAuthoring.ts:25-41` |
| Pure transition mutation | `applyStructureSequenceOperation` locates the keyframe and uses the shared `patchTransition` reducer | `src/domain/structureSequenceOperations.ts:51-79`, `src/domain/stateTransition.ts:71-85` |
| Ordered local publication | `createLocalDurabilityPublisher` preserves synchronous Zustand reentry order and deletes completed reservations | `src/state/actions/localDurabilityPublisher.ts:9-38` |
| Durability orchestration | `ProjectDurabilityRuntime` owns staging, the authored FIFO, projection, promotion, retry, and recovery | `src/state/projectDurability.ts:72-116`, `src/state/projectDurability.ts:150-204`, `src/state/projectDurability.ts:255-332` |
| Worker request lifecycle | All three workers use `createWorkerRequestClient`; responses delete request entries and worker errors clear the pending map | `src/shared/workerRequestClient.ts:16-61` |
| Large cell serialization | `segmentedJson` extracts arrays named `cells` or `c`, serializes them in 128 item segments, and yields between segments | `src/shared/segmentedJson.ts:3-23`, `src/shared/segmentedJson.ts:60-74` |
| Storage preparation ordering | `ProjectCommitQueues` serializes preparation, then `OrderedCommitQueue` serializes IndexedDB promotion per branch | `src/persistence/orderedCommitQueue.ts:198-239`, `src/persistence/orderedCommitQueue.ts:38-74`, `src/persistence/orderedCommitQueue.ts:137-163` |
| Atomic bytes at rest | `executeIndexedDbCommit` reads guards, builds one promote plan, and writes the affected records in one strict transaction | `src/persistence/indexedDbCommit.ts:76-132`, `src/persistence/indexedDbCommit.ts:193-269` |

These seams should be reused by any repair. A second debounce, worker client, or
storage queue would duplicate current ownership.

`debouncedJsonStorage` is retired. There is no source file or live import at this
head. `git log --diff-filter=D -- src/state/debouncedJsonStorage.ts` identifies
`2aa9362` as the committed IndexedDB cutover that deleted it. The current
performance document also calls it the retired writer and names
`projectDurability`, `projectCommitProjection`, and `indexedDbProjectStorage` as
the active path: `PERFORMANCE.md:92-101`, `PERFORMANCE.md:128-129`.

## Quality Map

### 1. One transition control change to bytes at rest

1. A pointer drag calls `changeValue` on every `pointermove`. Keyboard and wheel
   input call the same function once per step. No value stream coalescing occurs
   in `ScrubField`: `src/components/ui/scrub-field/ScrubField.tsx:52-55`,
   `src/components/ui/scrub-field/ScrubField.tsx:72-85`,
   `src/components/ui/scrub-field/ScrubField.tsx:107-125`.
2. The transition panel converts the number to a typed patch. Duration and
   stagger are rounded; cut position is passed directly:
   `src/panels/motion/MorphInspector.tsx:73-89`,
   `src/panels/motion/MorphInspector.tsx:112-140`.
3. `TransitionInspector.patchTransition` resolves the gap keyframe and dispatches
   a `DocumentOperation` with kind `patch-transition`, the structure asset ID,
   keyframe ID, and partial settings:
   `src/panels/motion/MotionInspector.tsx:267-283`.
4. The synchronous document command passes the operation to
   `dispatchAuthoredEdit`, which creates one `AuthoredOperation` with fresh
   `id` and `commitId` plus the observed asset revision:
   `src/interaction/commands/document.commands.ts:8-22`,
   `src/state/actions/localAuthoring.ts:25-41`.
5. The pure reducer updates the target transition and constructs the next
   immutable Workbench. `patch-transition` is also explicitly allowed to keep
   playback running, matching the AUTO LOOP reproduction:
   `src/domain/structureSequenceOperations.ts:64-79`,
   `src/domain/stateTransition.ts:71-85`,
   `src/state/actions/authoredReducer.ts:292-303`.
6. The authored dispatcher appends the applied operation to the in memory
   `outbox`, captures the resulting full `CubicellState` as `durableState`, and
   publishes it to `durability.enqueue`:
   `src/state/actions/authoredDispatcher.ts:76-103`.
7. `ProjectDurabilityRuntime.enqueue` appends an `AuthoredDurabilityUnit` that
   retains the applied operation and full `CubicellState`. It immediately starts
   pending staging and the FIFO drain:
   `src/state/projectDurability.ts:49-57`,
   `src/state/projectDurability.ts:150-156`,
   `src/state/projectDurability.ts:598-610`.
8. Pending staging is the only delta sized write before projection.
   `ProjectPendingWrite` carries base revisions and one applied operation:
   `src/state/projectCommitProjection.ts:68-79`. `stageIndexedDbPending` appends
   that envelope to each touched asset draft in a strict IndexedDB transaction:
   `src/persistence/pendingDrafts.ts:184-227`,
   `src/persistence/pendingDrafts.ts:230-261`.
9. The drain waits for that unit's stage, ensures the complete Project roster,
   projects a commit in the projection worker, and passes the resulting
   `ProjectStorageCommit` to `storage.promote`:
   `src/state/projectDurability.ts:255-305`.
10. `ProjectCommitQueues` sends the commit through the storage preparation
    worker, then the branch queue calls `executeIndexedDbCommit`:
    `src/persistence/orderedCommitQueue.ts:208-239`,
    `src/persistence/indexedDbProjectStorage.ts:43-52`.
11. Promotion writes full replacement rows for the Project, changed Structure,
    history, user Project state, and any new poses. It appends an outbox row and a
    local commit row, then consumes one pending draft head:
    `src/persistence/indexedDbCommit.ts:193-269`,
    `src/persistence/promoteContract.ts:295-325`.

For a transition settings edit, the authored operation is a small delta. The
worker and storage payloads are materially larger snapshots.

### 2. Workers and exact payloads

| Worker | Main to worker | Worker to main | Whole or delta |
|---|---|---|---|
| `src/state/projectCommitProjectionWorker.ts` | `projectStorageHeadAsync` constructs `ProjectCommitProjectionRequest`, then serializes it as `SegmentedJson`. The request contains the delta `head`, plus `ProjectProjectionState` containing full `editor`, `history`, `project`, `userProjectState`, and `workbench`, plus the complete library when roster loading supplied it. Construction: `src/state/projectCommitProjection.ts:107-130`. Type: `src/state/projectCommitProjectionProtocol.ts:6-15`. | `ProjectCommitProjectionResponse` with `commit: SegmentedJson<ProjectStorageCommit>`: `src/state/projectCommitProjectionWorker.ts:19-42`, `src/state/projectCommitProjectionProtocol.ts:17-21`. | Input is a whole projection state plus a delta head. Output contains delta metadata and materialized snapshot records. `changedAssetSnapshot` filters `assets` to changed assets, but leaves draft, history, Project, user state, and pose revisions present: `src/state/projectCommitProjectionCore.ts:26-49`, `src/state/projectStorageChangeSet.ts:121-131`. |
| `src/persistence/storageRecordPreparationWorker.ts` | `prepareStorageCommitAsync` constructs `StoragePreparationRequest { commit, id, writeKind }`, where `commit` is the entire `ProjectStorageCommit`, and serializes it as `SegmentedJson`: `src/persistence/storageRecordPreparationAsync.ts:28-41`. Type: `src/persistence/storageRecordPreparationProtocol.ts:5-9`. | `StoragePreparationResponse { id, prepared: SegmentedJson<PreparedStorageCommit> }`: `src/persistence/storageRecordPreparationWorker.ts:20-38`. Type: `src/persistence/storageRecordPreparationProtocol.ts:11-15`. | Whole commit in, whole prepared commit out. The prepared result holds full JSON strings for the changed asset, local history, draft checkpoint, Project manifest, user state, outbox operation, and every projected pose revision: `src/persistence/storageRecordPreparation.ts:33-123`, `src/persistence/storageRecordTypes.ts:103-127`. |
| `src/persistence/projectRecordHydrationWorker.ts` | Recovery and hydration send a JSON string containing `ProjectHydrationRequest { encoded, id, records, seed }`: `src/persistence/projectRecordHydrationAsync.ts:27-40`, `src/persistence/projectRecordHydrationProtocol.ts:5-10`. | It attempts `ProjectHydrationResponse { id, result: SegmentedJson<ProjectHydrationResult> }`: `src/persistence/projectRecordHydrationWorker.ts:17-29`, `src/persistence/projectRecordHydrationProtocol.ts:12-15`. | This worker does not run for the normal write. Recovery uses it to reconstruct a full Project, Workbench, local history, editor seed, and pending result: `src/persistence/projectRecordHydration.ts:75-105`, `src/persistence/projectRecordHydration.ts:129-180`. |

The projection stage gathers pose revisions from the current Workbench and
every past and future history Workbench:
`src/persistence/projectRecordProjection.ts:86-101`,
`src/persistence/projectRecordProjection.ts:113-125`. The preparation stage
serializes every one again:
`src/persistence/storageRecordPreparation.ts:102-102`,
`src/persistence/storageRecordPreparation.ts:204-226`. IndexedDB then reads
every projected pose revision to decide which are new:
`src/persistence/indexedDbCommit.ts:135-177`. Therefore a transition settings
delta still traverses both write workers with all referenced pose records.

The draft checkpoint is smaller than a complete Workbench. It contains the
working attachment and compact working pose:
`src/persistence/recordCodecs/draftRecordCodec.ts:9-41`. The changed Structure
record is a full Structure document, including the complete score and all State
references:
`src/persistence/recordCodecs/structureRecordCodec.ts:14-60`.

### 3. Coalescing, debounce, and batching

No debounce, idle window, or authored edit coalescing exists on this path.

- `debouncedJsonStorage` has no live source or import. It was deleted by the
  IndexedDB cutover described above.
- Pointer scrubbing starts a history batch, but the comment explicitly places
  that batch outside Zustand and persistence. After the first pointer move it
  reuses the same undo history; every value still becomes a fresh authored
  operation and durability unit:
  `src/panels/motion/MorphInspector.tsx:73-89`,
  `src/state/actions/historyCoordinator.ts:13-40`.
- Keyboard and wheel paths call `changeValue` without `onScrubStart` or
  `onScrubEnd`, so they also bypass the undo history batch:
  `src/components/ui/scrub-field/ScrubField.tsx:107-125`.
- `ProjectDurabilityRuntime` coalesces only adjacent
  `user-project-state` units. Authored units always append:
  `src/state/projectDurability.ts:119-142`,
  `src/state/projectDurability.ts:150-156`.
- `ProjectCommitQueues.preparation`, `OrderedCommitQueue`, and
  `ProjectDurabilityRuntime.staging` serialize FIFO work. They do not collapse
  it: `src/state/projectDurability.ts:194-203`,
  `src/persistence/orderedCommitQueue.ts:216-239`.
- `yieldToMain` and segmented cell chunks are scheduler and serialization
  yielding only: `src/shared/taskYield.ts:1-20`,
  `src/shared/segmentedJson.ts:11-23`.

There is no live batching implementation for the transition path to bypass.
The path bypasses only pointer scoped undo history after its first change.

### 4. `pending draft head missing`

The invariant is exact. Before an authored promote, every touched asset must
have a stored draft row and its first `pendingOps` entry must equal the commit
being promoted, or the superseded commit for a draft rebase:
`src/persistence/promoteContract.ts:57-78`.

The staging side appends each accepted operation to `pendingOps` in FIFO
sequence:
`src/persistence/pendingDrafts.ts:77-117`,
`src/persistence/pendingDrafts.ts:120-145`. A successful promote consumes
exactly one head with `slice(1)`, updates the draft base revision, and deletes
the draft when the suffix becomes empty:
`src/persistence/promoteContract.ts:295-325`,
`src/persistence/indexedDbCommit.ts:239-249`.

The observed message suffix
`0cc57329-341a-4cb8-beab-0472174d006e` is the `assetKey` rendered by the
validator. At the promote transaction's read point, that Structure draft row
was absent, empty, or headed by a different commit:
`src/persistence/indexedDbCommit.ts:135-190`,
`src/persistence/promoteContract.ts:64-69`.

The normal in process design serializes stages and promotes units from index
zero:
`src/state/projectDurability.ts:194-203`,
`src/state/projectDurability.ts:255-305`. Source visible mechanisms that can
remove or replace a head are:

- branch reset, which deletes all branch drafts and rebuilds only the current
  pending write's touched keys:
  `src/persistence/pendingDrafts.ts:230-261`;
- successful consumption of a prior head:
  `src/persistence/promoteContract.ts:295-325`;
- explicit pending or recovery discard:
  `src/persistence/indexedDbProjectStorage.ts:73-81`.

**UNVERIFIED:** The exact live event sequence selecting one of those mechanisms
was not established by this static scout. No source path proves that AUTO LOOP
alone reorders the FIFO. Assigning the mismatch to reset, discard, concurrent
IndexedDB transaction ordering, or a prior failure would require runtime
instrumentation of stage transaction start and completion, draft head before
promote, unit head, and commit ID. The verified fact is the violated stored
draft head invariant above.

### 5. Recovery failure and worker response

The second modal follows this path:

1. The user invokes `recoverToLastCommitted`; `recoverFailedBranch` calls
   `preflightCommittedRecovery`. A preflight error becomes
   `recoveryFailureSaveState`: `src/state/projectDurability.ts:356-371`.
2. Preflight loads committed records, hydrates them, and verifies the complete
   roster before any unsaved state is discarded:
   `src/state/projectDurabilityRecovery.ts:15-29`.
3. `loadIndexedDbProject(..., false)` excludes the pending draft but includes
   committed asset poses and matching local history:
   `src/persistence/indexedDbProjectReads.ts:37-61`.
4. `hydrateCommittedProjectState` calls `hydrateProjectRecordsAsync`, which
   selects `projectRecordHydrationWorker` when Worker exists:
   `src/state/projectDurabilityHydration.ts:40-46`,
   `src/state/projectDurabilityHydration.ts:113-132`,
   `src/persistence/projectRecordHydrationAsync.ts:27-40`.
5. The worker attempts to post
   `{ id, result: SegmentedJson<ProjectHydrationResult> }` back to main:
   `src/persistence/projectRecordHydrationWorker.ts:17-29`.
6. If that `postMessage` throws `DataCloneError`, no response payload is
   delivered. The unhandled worker error reaches `workerRequestClient.onerror`,
   which terminates the worker, rejects pending requests, and clears the pending
   map: `src/shared/workerRequestClient.ts:28-42`.
7. The preflight catch stores the worker error as `recovery-failed`; the UI
   renders `Last saved state could not be verified` and the error message:
   `src/state/projectDurabilitySaveState.ts:29-34`,
   `src/app/PersistenceStatus.tsx:10-30`.

This identifies `projectRecordHydrationWorker` as the worker path for the
observed recovery modal. The attempted response is the full hydrated result in
segmented JSON. The failed structured clone means the response itself never
arrived.

### 6. Retention and accumulation

| Retainer | Verified behavior | Bound or release |
|---|---|---|
| `ProjectDurabilityRuntime.units` | Every authored value appends a unit retaining a full `CubicellState`; drain processes units one at a time | No producer side bound or authored coalescing. A unit is removed only after promotion or explicit recovery handling: `src/state/projectDurability.ts:150-156`, `src/state/projectDurability.ts:255-305`, `src/state/projectDurability.ts:613-615`. |
| `CubicellState.outbox` | Every local authored edit copies and appends one `PendingOutboxCommit` | No production success path removes entries. Projection explicitly substitutes `outbox: []`, so this growing array is retained in Zustand and queued state snapshots without being sent to the projection worker: `src/state/actions/authoredDispatcher.ts:76-89`, `src/state/projectCommitProjectionCore.ts:62-79`, `src/state/cubicellState.ts:229-244`. |
| Draft `pendingOps` | Staging can run ahead of promotion and appends every accepted operation to the branch draft | Temporarily unbounded while the producer outruns the single promote drain. Each successful promote consumes one head: `src/state/projectDurability.ts:194-203`, `src/persistence/pendingDrafts.ts:137-145`, `src/persistence/promoteContract.ts:316-324`. |
| IndexedDB `outbox` | Every authored promote adds one full operation envelope | The only source removal is targeted discard during installed head rebase or deletion of a superseded outbox sequence. No current source synchronization worker acknowledges ordinary local commits: `src/persistence/indexedDbCommit.ts:214-233`, `src/state/projectDurability.ts:451-495`, `src/persistence/indexedDbOutbox.ts:20-40`. |
| IndexedDB `localCommits` | Every promote stores one receipt and digest record | No delete path was found: `src/persistence/indexedDbCommit.ts:252-269`, `src/persistence/indexedDbSchema.ts:45-47`. |
| Local undo history | Pointer scrub records one entry, and the live history stack is capped at 100 | Bounded: `src/state/actions/historyCoordinator.ts:26-44`, `src/state/documentHistory.ts:45-59`. Persisted history also enforces the same cap: `src/persistence/recordCodecs/localHistoryRecordCodec.ts:58-94`. |
| Accepted scene journal | Each authored edit records previous and next scenes | Bounded to 32 entries: `src/state/authoredSceneJournal.ts:3-4`, `src/state/authoredSceneJournal.ts:41-50`. |
| Worker request maps | One entry per outstanding request | Deleted on response, deleted on synchronous send failure, and cleared on worker error: `src/shared/workerRequestClient.ts:28-42`, `src/shared/workerRequestClient.ts:47-60`. No leak was found in the handled paths. There is no timeout for a silent worker that neither responds nor errors. Whether that occurs is **UNVERIFIED**. |
| Ordered storage queue | Prepared commits and deferred callers are retained while queued or failed | Success and terminal paths remove map and queue entries. One failed head remains intentionally retryable; followers are rejected and removed: `src/persistence/orderedCommitQueue.ts:50-74`, `src/persistence/orderedCommitQueue.ts:156-194`. |

The source proves two unbounded live accumulators across rapid edits:
`ProjectDurabilityRuntime.units` while work is backlogged, and
`CubicellState.outbox` across the session. The source also proves persistent
growth of ordinary outbox and local commit rows in the current offline
implementation.

**UNVERIFIED:** No heap profile or controlled live reproduction was run, so this
report does not claim one accumulator alone caused the tab death. The observed
worker clone OOM is consistent with the verified combination of an unbounded
full state FIFO and repeated whole pose and history materialization, but causal
weight remains unmeasured.

### Searches performed

The scout inspected the complete named write and recovery boundaries and ran:

- `rg` for `pending draft head missing`, `Last saved state could not be
  verified`, `PROJECT SAVE FAILED`, and `PROJECT RECOVERY UNAVAILABLE`;
- `rg` for `debouncedJsonStorage`, `projectDurability`, `promoteContract`,
  `workerRequestClient`, all three named workers, `postMessage`, `pending`,
  `Map`, `queue`, `draft`, `history`, `outbox`, debounce, idle, batch, and
  coalescing terms;
- `rg` for every `state.outbox` mutation and every `discardOutbox`, outbox
  delete, and local commit delete path;
- `git log -S` for `debouncedJsonStorage` and `pending draft head missing`;
- `git log --diff-filter=D` for the retired debounced storage file;
- `git blame` on authored durability staging, pending draft transactions, and
  the draft head validator;
- bounded line reads of the transition control, command, reducer, durability,
  projection, preparation, promotion, draft, hydration, history, outbox, and
  worker client files cited above.

No runtime heap profile, browser reproduction, or test was run. Conclusions
that need those proofs are explicitly marked **UNVERIFIED**.

## Findings

1. **Major: authored write work is unbounded and snapshot sized.** Every rapid
   control value becomes a new FIFO unit retaining a full `CubicellState`.
   There is no debounce or authored coalescing. The sequential workers and
   strict IndexedDB promotion are consumers, so a control stream can outrun
   them.
2. **Major: a tiny transition delta repeatedly materializes all referenced pose
   revisions and bounded local history through two workers.** The projection
   request carries full projection state. The projection result retains all
   pose records. Storage preparation serializes those records again before
   IndexedDB checks which poses are already present.
3. **Major: the in memory outbox has no production consumer or success
   removal.** It grows once per authored edit and is copied into every queued
   state snapshot, while projection discards it. IndexedDB outbox and local
   commit rows also grow without an ordinary local acknowledgement path.
4. **Confirmed second modal path:** recovery uses
   `projectRecordHydrationWorker`; it attempts to post a full
   `ProjectHydrationResult` back. The observed worker global `DataCloneError`
   means that response clone failed, the worker request rejected, and the UI
   rendered `Last saved state could not be verified`.
5. **Confirmed first modal invariant, live trigger unresolved:** the failing
   Structure draft was absent, empty, or headed by another commit at promote
   read time. Static source establishes the invariant and all mutators, but does
   not establish which live event broke the FIFO. That trigger remains
   **UNVERIFIED**.

## Proposals

### 1. Make one scrub gesture one authored durability unit

- **Defect**: Every accepted control value appends an `AuthoredDurabilityUnit` that owns a full `CubicellState`, and authored units have no producer side bound or coalescing (`src/state/projectDurability.ts:49-57`, `src/state/projectDurability.ts:150-156`).
- **Why it is wrong on its own terms**: Save work and retained state scale with input event frequency instead of user intent, which creates avoidable latency, stale rebases, and failure exposure even without the crash.
- **Minimal fix**: Change `AuthoredDurabilityUnit.state` and `ProjectDurabilityCoordinator.enqueue` to retain the existing `ProjectProjectionState` from `compactProjectionState`, leaving the current FIFO and stage contract unchanged (`src/state/projectCommitProjectionCore.ts:20-59`).
- **Elegant fix**: Refactor the existing `HistoryCoordinator.beginBatch/endBatch` lifecycle into one authored transaction coordinator that assigns one commit ID, collects a nonempty operation tuple, and publishes only the latest compact state at batch end; reuse `OutboxCommitOperations`, `projectStorageAuthoredCommitAsync`, and the existing pending envelope contract rather than adding another batcher (`src/state/actions/historyCoordinator.ts:5-40`, `src/state/projectCommitProjection.ts:50-78`, `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:11-31`).
- **Blast radius**: `ScrubField` batch callers, authored local operation creation, `AuthoredDispatcher`, `LocalDurabilityPublisher`, `ProjectDurabilityCoordinator`, pending stage tests, and retry tests; no generated surface and no persisted shape change because multi operation envelopes already exist.
- **Recommendation**: Elegant, because it removes per value persistence work at the authoring boundary while preserving one owner for undo and durability batching.

### 2. Persist only pose revisions introduced by the authored operation

- **Defect**: Every authored projection walks the current Workbench plus all history Workbenches and sends every referenced pose revision through projection and storage preparation, including pose neutral `patch-transition` commits (`src/persistence/projectRecordProjection.ts:86-125`, `src/persistence/storageRecordPreparation.ts:102`, `src/persistence/storageRecordPreparation.ts:204-226`).
- **Why it is wrong on its own terms**: Immutable pose records are repeatedly encoded, cloned, decoded, and hashed even when the operation cannot change or introduce a pose, so a delta commit performs aggregate sized work unrelated to its change set.
- **Minimal fix**: Add one shared authored pose classifier beside the existing freshness check and emit `poseRevisions: []` when every operation is pose neutral; keep the current complete scan for bootstrap, checkpoint, and pose carrying operations (`src/state/actions/authoredReducer.ts:102-113`, `src/state/projectCommitProjectionCore.ts:26-49`).
- **Elegant fix**: Make authored commits carry an exact immutable pose addition set derived from their existing operation bodies, including restore bodies, and reserve aggregate pose discovery for bootstrap and checkpoint; keep `PoseRevisionRegistry` as the sole canonicalization and conflict owner, then let the second worker prepare only those additions (`src/domain/structureOperations.ts:32-63`, `src/domain/documentRestoreOperations.ts:13-55`, `src/persistence/poseRevisionRegistry.ts:16-44`).
- **Blast radius**: authored operation helpers, projection request and worker contracts, `ProjectStorageCommit.snapshot.poseRevisions`, storage preparation, pose integrity tests, bootstrap tests, checkpoint tests, and undo restore tests; no generated surface and no persisted shape change.
- **Recommendation**: Elegant, because it establishes immutable poses as an operation delta and removes both worker amplification passes for transition edits.

### 3. Remove the local only outbox ledgers

- **Defect**: Local authorship copies and appends `CubicellState.outbox` forever although projection discards it, while successful promotes also append IndexedDB outbox and local commit rows with no ordinary removal path (`src/state/actions/authoredDispatcher.ts:76-89`, `src/state/projectCommitProjectionCore.ts:62-79`, `src/persistence/indexedDbCommit.ts:214-233`, `src/persistence/indexedDbCommit.ts:252-269`).
- **Why it is wrong on its own terms**: A single writer local application has no acknowledgement consumer for these sync ledgers, so live memory and disk usage grow with lifetime edit count; queued snapshots also retain successive copied outbox prefixes.
- **Minimal fix**: Delete `PendingOutboxCommit` and `CubicellState.outbox`, remove the dispatcher append and hydration assignment, and stop reading or writing ordinary IndexedDB outbox and local commit rows while leaving their stores inert; the existing `OrderedCommitQueue`, pending drafts, and persisted failed commit bytes continue to own local ordering, crash recovery, and retry (`src/state/cubicellState.ts:129-132`, `src/state/cubicellState.ts:229-244`, `src/persistence/orderedCommitQueue.ts:38-74`, `src/persistence/indexedDbFailureState.ts:23-38`).
- **Elegant fix**: Delete the outbox, `installCommitted`, outbox rebase, and append only local receipt architecture across state and storage, keep only committed records plus pending drafts, and bump the IndexedDB version so the local database resets without migration (`src/state/projectDurability.ts:177-187`, `src/state/projectDurability.ts:451-539`, `src/persistence/indexedDbSchema.ts:1-47`, `src/persistence/storagePort.ts:177-200`).
- **Blast radius**: `CubicellState`, authored dispatch, hydration, outbox codecs and validation, `ProjectStoragePort`, memory storage, IndexedDB schema and commit code, install and rebase tests, browser storage fixtures, and record metrics; no generated surface; the elegant fix changes persisted shape and requires a version bump with reset.
- **Recommendation**: Minimal first, because it removes the highest confidence live retention amplifier at low cost; follow with the elegant storage deletion as a separate schema slice.

### Ranking (relative 1 to 5 inputs)

| Rank | Proposal | Crash impact | Confidence | Cost | `(impact x confidence) / cost` |
|---:|---|---:|---:|---:|---:|
| 1 | Remove the local only outbox ledgers, minimal slice | 4 | 5 | 2 | 10.0 |
| 2 | Persist only operation introduced poses, elegant slice | 5 | 4 | 3 | 6.7 |
| 3 | Make one scrub gesture one durability unit, elegant slice | 5 | 4 | 4 | 5.0 |

**Ship first**: Remove `CubicellState.outbox` and stop ordinary outbox and local receipt row writes because those ledgers have no product consumer, the functional removal changes no persisted shape, and it immediately eliminates copied outbox prefixes from every queued state snapshot.
