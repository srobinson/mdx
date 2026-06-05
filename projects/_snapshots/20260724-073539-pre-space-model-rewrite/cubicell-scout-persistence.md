# Cubicell persistence scout

Target: pristine `docs/performance-audit` at
`6d6811920fe1d8376f9e6c931d7191db939e62b0`.

Scope: read only audit of the persistence and storage path against
`STORAGE.md` Phase 1 and `PERFORMANCE.md` P0 persistence integrity.

Verification: the focused current path suite passed 6 files and 105 tests:

```text
pnpm exec vitest run tests/debouncedStorage.dom.test.ts \
  tests/quotaPersistence.dom.test.ts tests/wireEncode.test.ts \
  tests/historyDiff.test.ts tests/historyPersistence.test.ts \
  tests/authoredOperations.test.ts --reporter=dot

Test Files  6 passed (6)
Tests      105 passed (105)
```

The passing suite printed the expected `cubicell: skipped persisting the
workbench` warnings. That proves the current tests accept the silent failure
path. It does not satisfy the new forced failure and visible state gates in
`PERFORMANCE.md:117-126`.

## Reuse Map

### Current write path

1. `src/state/cubicellStore.ts:35-90` wraps the complete store with Zustand
   `persist`. Every `set` invokes the persistence middleware. `partialize`
   selects `history`, `preferences`, and `workbench` at
   `src/state/cubicellStore.ts:73-77`.
2. The adapter is `createDebouncedJsonStorage` at
   `src/state/cubicellStore.ts:78-86`. Its `setItem` stores the latest value in
   `pendingWrite` and returns immediately after scheduling one 200 ms timer at
   `src/state/debouncedJsonStorage.ts:142-150`.
3. `flush` clears the timer, removes the pending value, and calls the encoder
   at `src/state/debouncedJsonStorage.ts:80-107`. Playback and hover writes can
   reach this point, but stable source references let the encoder return its
   cached wire object and avoid another stringify at lines 93-103.
4. `createWireEncoder` caches the `workbench`, `history`, and `preferences`
   reference triple at `src/state/wireEncode.ts:20-58`. On a cache miss it:

   - caps history and drops redo through `capPersistedHistory` at
     `src/state/cubicellHistory.ts:68-76`;
   - encodes past history as backward RFC 6902 steps through
     `encodePersistedHistory` at `src/state/historyDiff.ts:21-41`;
   - removes `State` poses from the Library and encodes them as an ordered diff
     chain from `workingPose` through `encodeWireStates` at
     `src/state/wireEncode.ts:44-52,61-75`;
   - returns Zustand's `{ state, version }` wrapper with version 12 at
     `src/state/wireEncode.ts:47-55` and
     `src/config/cubicellConfig.ts:32-34`.
5. `flush` stringifies the complete wire value once at
   `src/state/debouncedJsonStorage.ts:97-106`. `persistWithShedding` attempts
   `localStorage.setItem` at line 62. On a quota exception it serializes and
   retries three degraded values:

   - without history, `shedHistory`, `src/state/wireEncode.ts:78-85`;
   - without preferences, `shedPreferences`,
     `src/state/wireEncode.ts:87-95`;
   - without the Library, `shedLibrary`, `src/state/wireEncode.ts:97-120`.

6. The quota failure happens synchronously inside
   `storage().setItem(name, currentSerialized)` at
   `src/state/debouncedJsonStorage.ts:62`. When the last degradation also
   fails, or when any non quota error occurs, lines 68-71 log a warning and
   return. The previous localStorage value remains intact. The audit observed
   four rejected writes and reload of the previous one cube document at
   `PERFORMANCE.md:83-99`.
7. The false saved contract has two concrete causes:

   - the public adapter `setItem` returns `void` when the value is only queued
     at `src/state/debouncedJsonStorage.ts:142-150`;
   - the later write failure is caught and converted to another `void` return
     at `src/state/debouncedJsonStorage.ts:68-71`.

   Zustand receives no promise representing the real write and no rejection.
   `pendingWrite` has already been cleared at lines 90-91, so the failed unit
   has no durable retry record. `CubicellState` contains only `actionJournal`,
   `editor`, `history`, `preferences`, `selectionAssembly`, and `workbench` at
   `src/state/cubicellState.ts:200-207`. No save state exists. A repository
   search for `saving`, `save failed`, `QuotaExceeded`, and `local durability`
   found only the quota helper and unrelated Saved State interface copy.

### Existing owners and dispositions

| Needed capability | Existing owner and evidence | Disposition |
|---|---|---|
| In memory view and subscriptions | `useCubicellStore`, `src/state/cubicellStore.ts:35-90` | Reuse Zustand as the view and subscription layer. Remove its Project persistence middleware. |
| Serializable authored intent | `AuthoredOperation`, `src/domain/authoredOperations.ts:5-46` | Reuse unchanged as the outbox operation payload. |
| Pure application and semantic inverse | `reduceAuthoredOperationState`, `src/state/actions/authoredReducer.ts:45-112`; `AppliedAuthoredOperation`, `src/domain/authoredOperations.ts:43-46` | Reuse. Enqueue only accepted local reductions. |
| Local operation identity and target | `createLocalAuthoredOperation`, `src/state/actions/localAuthoring.ts:27-40` | Reuse after replacing the `local-project` sentinel and revision zero defaults with loaded durable facts. |
| Undo history compaction | `encodePersistedHistory`, `applyHistoryDiff`, and `isSafeHistoryPath`, `src/state/historyDiff.ts:21-61,43-45` | Reuse for the separate local history record. Extend the durable format to include redo because `STORAGE.md:94` owns undo and redo entries. |
| History coordination | `createPresentEntry`, `capPersistedHistory`, and `restorePersistedHistory`, `src/state/cubicellHistory.ts:68-119,142-160` | Reuse the capture and repair behavior. Move persistence specific encoding behind the storage codec. |
| JSON diff primitive | `createJsonDiff`, `src/shared/jsonDiff.ts:1-27` | Reuse for local history. Do not use RFC 6902 as the shared operation protocol, per `STORAGE.md:177-179`. |
| Workbench repair | `normalizePersistedState`, `src/state/persistedStateNormalization.ts:56-100`; `completePersistedWorkbench`, `src/state/workbenchValidation.ts:159-205` | Reuse the repair rules through new per record decoders. Remove the aggregate Zustand envelope dependency. |
| Session reference repair after load | `repairEditorSessionReferences`, called at `src/state/cubicellStore.ts:54-67` | Reuse after IndexedDB hydration. |
| Stable entity IDs | `createDurableId`, `src/domain/identity.ts:1-4` | Reuse. Project and pose revision records still need model ownership. |
| Compact State pose chain | `encodeWireStates`, `src/state/wireEncode.ts:61-75` | Reuse only the measured compacting idea. Replace the ordered cross record chain because pose revisions must load independently. |
| IndexedDB adapter and storage port | None found. Search: `indexedDB|IDBDatabase|IDBTransaction|openDB|dexie|idb` across `src`, `tests`, and dependencies. | Add one port and one browser adapter. There is no IndexedDB dependency today. |
| Project record | None found. `localProjectId = 'local-project'` is the only runtime Project identity at `src/state/actions/localAuthoring.ts:11-24`. | Add a durable Project manifest and load its ID before local authoring. |
| Pose revision record | None found. `State.pose` and `Workbench.workingPose` embed poses at `src/domain/workbench.ts:29-63`. Search for `poseRevisionId` returned no result. | Add immutable pose revision identity and references before the storage adapter. The adapter must not invent domain identity. |
| Outbox | None found. `AppliedAuthoredOperation` is returned to callers and is not stored. | Add a durable, client keyed outbox in the atomic commit path. |
| Explicit local save state | None found in store or UI. | Add a transient Zustand slice plus durable failed unit metadata in IndexedDB. |
| Migration marker | None found in source. Only `STORAGE.md:223` names one. The current `migrate` callback is a Zustand version reset at `src/state/cubicellStore.ts:69-72`. | Delete the old version gate with the old writer. A new one bit cleanup marker is optional and cannot retain a legacy reader. |

### Storage port

The port should expose domain sized loads and one atomic durability method. It
should not expose one public method per IndexedDB object store because that
would let callers split the snapshot and outbox transaction.

```ts
type LocalSaveState =
  | { status: 'saving'; operationId: string }
  | { status: 'saved'; operationId: string; localRevision: number }
  | { status: 'failed'; operationId: string; failure: LocalDurabilityFailure }

type LocalDurabilityUnit = {
  clientId: string
  commitId: string
  projectId: string
  applied: AppliedAuthoredOperation[]
  records: EncodedLocalRecordChanges
}

type LocalCommitReceipt = {
  localRevision: number
  operationIds: string[]
}

interface CubicellStoragePort {
  loadProject(input: {
    clientId: string
    projectId: string
    activeAssetId?: string
  }): Promise<LocalProjectLoad>
  loadAsset(projectId: string, assetId: string): Promise<LocalAssetLoad>
  commit(unit: LocalDurabilityUnit): Promise<LocalCommitReceipt>
  close(): void
}
```

`commit` is the only write boundary. The IndexedDB adapter opens one
`readwrite` transaction over the touched logical stores, writes the working
records and outbox commit, preserves acknowledged and projected revision
metadata, and resolves only from the transaction completion event. Abort,
quota, and transaction errors reject. The previous valid records survive an
abort through IndexedDB transaction rollback.

The store should be constructed through an injected factory such as
`createCubicellStore({ storagePort, preferencePort })`. Startup loads and
decodes the manifest plus active asset before authoring becomes available.
Accepted local dispatches publish their optimistic update, enqueue one ordered
durability unit, set `saving`, and set `saved` only after `commit` resolves.
Rejection sets `failed` while retaining the optimistic branch and the previous
durable revision. A retry resubmits the same commit ID.

`LocalSaveState` belongs in the in memory Zustand state, outside authored
snapshots and preferences. The durability coordinator is its sole writer. The
blocking failure surface belongs at the Project shell boundary. `App` currently
passes only canvas, dock, inspector, and rail content to `StudioShell` at
`src/app/App.tsx:103-176`; there is no global status surface. The cutover must
add one shell level status and retry surface so a panel choice cannot hide a
failed Project save. The failed unit remains in the in memory durability queue
with its commit ID. Failure metadata belongs in the client keyed outbox when a
subsequent small transaction can persist it, as required by
`STORAGE.md:227-231`. A quota failure cannot guarantee another durable write,
so that diagnostic write cannot be a precondition for reporting failure.

### Logical store map

| IndexedDB store | Current data | Existing durability | Required change |
|---|---|---|---|
| `projects` | The Library arrays imply an asset roster. Operations use the constant `local-project`. | No Project record, name, manifest, revision, or durable Project ID exists. | Add the Project manifest, asset order, active references, and revision metadata. Load the manifest without loading every asset. |
| `assets` | `Workbench.library.structures`, `.animations`, and `.states`; `Workbench.working` identifies the attached Structure or detached scratch. See `src/domain/workbench.ts:21-63`. | All assets are embedded in one Workbench blob. | Store Structure and Animation records separately. Structure records own State metadata and piece motion. Animation records own stage and camera authorship. |
| `poseRevisions` | `State.pose` and `Workbench.workingPose`. | Poses are embedded. They have no revision identity and cannot be shared by reference. | Add immutable Project scoped pose revision records and explicit references. This is net new and must precede the adapter. |
| `drafts` | Detached `working.draftScore` plus `workingPose`; attached drift also lives in the assembled Workbench. | Persisted inside the same blob. | Separate client working snapshots and unsaved Editor scratch. Preserve detached scratch independently from saved assets. |
| `history` | Runtime `DocumentHistory` with past and future at `src/state/documentHistory.ts:25-28`. | `capPersistedHistory` drops all redo at `src/state/cubicellHistory.ts:68-76`; only past steps are embedded in the blob. | Store bounded private history per user and asset. Preserve both undo and redo unless `STORAGE.md:94` is changed. Reuse the safe RFC 6902 codec and repair path. |
| `outbox` | `AppliedAuthoredOperation` contains the accepted operation and its inverse body. | The value exists only on the call stack. No queue, commit ID, sequence, retry state, or revision metadata exists. | Persist ordered commit envelopes and inverse metadata in the same transaction as the working snapshot. |
| `userProjectState` | `preferences.panelLayout` is persisted. `editor.activeStateId`, tabs, selection, and live transport state are session only at `src/state/cubicellState.ts:151-198`. | Panel layout is mixed into global preferences. Other Project session fields are memory only. | Split Project scoped panel and active asset state from global input feel and quality preferences. Presence fields remain memory only. |
| small preferences in localStorage | `CubicellPreferences` includes input feel, quality, grid default, view defaults, and panel layout at `src/state/cubicellState.ts:93-103`. | Embedded in the Project blob. | Keep a small independent preference record in localStorage. Move current Project panel state to `userProjectState`; retain only layout defaults globally. |

### Snapshot format

Replace `CubicellWireState` as the durable top level format. Reuse its proven
pieces.

Reasons:

1. `CubicellWireState` is a Zustand shaped aggregate with optional history,
   preferences, States, and one Workbench at
   `src/state/cubicellState.ts:237-243`. It cannot represent the logical stores
   or lazy asset loading required by `STORAGE.md:181-196`.
2. Its schema version is carried by Zustand's outer `StorageValue`, not by each
   durable record. IndexedDB Project, asset, pose revision, history, draft, and
   outbox records need explicit schema versions.
3. The State pose chain begins at the active `workingPose` and depends on array
   order at `src/state/wireEncode.ts:61-75`. An immutable pose revision must be
   independently addressable and decodable.
4. The full active `workingPose` remains embedded at
   `src/state/wireEncode.ts:45-53`. That is the dominant 4,500 cube payload
   which defeated every degradation tier in `PERFORMANCE.md:83-99`.
5. `createWireEncoder` imports Zustand's `StorageValue` and caches one whole
   Workbench reference triple. That is an adapter concern rather than a durable
   codec contract.

Keep `createJsonDiff`, safe patch application, history capping policy after the
redo decision, validation, and Workbench repair. Extract pure, versioned record
codecs. Add a compact `PoseRevision` codec which round trips independently. The
Project manifest and asset codecs reference revision IDs. Measure snapshot
bytes and encode duration by asset kind and cell count. A 4,500 cube browser
fixture must establish whether encoding stays below the 50 ms main thread gate.
Move encoding to a worker or chunked path when that measurement fails. The
worker decision follows evidence and cannot be inferred from IndexedDB capacity.

### Applied operation to outbox

`reduceAuthoredOperationState` returns
`{ applied: { inverseBody, operation }, update }` at
`src/state/actions/authoredReducer.ts:77-111`. The operation already supplies
`id`, target, actor, client, observed revision, schema version, and semantic
body through `src/domain/authoredOperations.ts:31-46`. This is the main outbox
reuse.

The durable coordinator must sit inside the local dispatch boundary:

1. Create the commit ID and operation before reducer application.
2. Apply the reducer.
3. Ignore rejected and exact no op reductions.
4. Publish the accepted optimistic update.
5. Pair the accepted `AppliedAuthoredOperation` with the post reduction record
   changes.
6. Append the ordered outbox commit and record changes in one IDB transaction.
7. Store `inverseBody` as private local metadata. A later undo wraps it in a
   new operation with a new ID and current observed revision. The inverse body
   alone is not an outbox operation.

Caller level capture is unsafe. `createAuthoredActions` returns the applied
record at `src/state/actions/authoredActions.ts:23-74`, but current application
call sites discard it. `selectActiveState` also calls
`reduceAuthoredOperationState(...).update` directly and discards `.applied` at
`src/state/actions/documentActions.ts:67-99`. Extract one internal authored
dispatcher used by both modules. Local dispatch enqueues. Replay and future
remote application use the same pure reducer without echoing the received
operation into the local outbox.

`createLocalAuthoredOperation` currently hard codes `observedRevision: 0` at
`src/state/actions/localAuthoring.ts:27-40`. The loaded Project and asset
revision must enter `LocalAuthoringContext` before outbox integration. A
constant zero would make stale writer detection impossible.

## Quality Map

| Priority | Finding | Evidence and impact | Disposition |
|---|---|---|---|
| P0 | A queued write is treated as complete. | `setItem` returns after queuing at `src/state/debouncedJsonStorage.ts:142-150`; the real failure is caught at lines 68-71. The old value reloads with no visible failure. | Replace with a promise backed IDB transaction receipt and explicit save state. |
| P0 | The degradation ladder cannot preserve the active large document. | `shedLibrary` still retains full `workingPose` at `src/state/wireEncode.ts:97-120`; the measured active payload is 6,577,988 bytes at `PERFORMANCE.md:83-99`. | Delete the ladder. IndexedDB plus a compact pose codec owns capacity. |
| P0 | Failed units have no retry record. | `flush` clears `pendingWrite` before the attempt at `src/state/debouncedJsonStorage.ts:90-91`; final failure returns at lines 68-71. | Keep the failed unit and commit ID in the durability coordinator, expose failure immediately, and retry the same commit ID. Persist diagnostic failure metadata separately only when storage accepts it. |
| High | Project and pose revision identity are missing. | `localProjectId` is a process constant at `src/state/actions/localAuthoring.ts:17-24`; poses are embedded at `src/domain/workbench.ts:29-63`; no `poseRevisionId` exists. | Finish durable vocabulary before physical storage. The adapter cannot create semantic IDs. |
| High | Accepted authored records can be lost before outbox capture. | `createAuthoredActions` returns applied records, application callers ignore them, and `selectActiveState` discards one directly at `src/state/actions/documentActions.ts:79-99`. | One internal dispatcher owns optimistic update and durability enqueue. |
| High | Remote replay and local authoring need separate durability policy. | `applyAuthoredOperation` and `dispatchAuthoredEdit` share the reducer at `src/state/actions/authoredActions.ts:28-73`, but there is no source or enqueue policy. | Local creation enqueues. Replay and remote application skip outbox append. Keep the reducer shared. |
| High | Current durable history contradicts the canonical ownership table. | Runtime history has `future`; `capPersistedHistory` always replaces it with `[]` at `src/state/cubicellHistory.ts:68-76`; `STORAGE.md:94` specifies undo and redo entries. | Resolve in the codec slice. Default to preserving bounded redo. |
| High | Async hydration can overwrite or race first edits. | Current localStorage hydration is owned by Zustand `persist` at `src/state/cubicellStore.ts:35-90`. No Project loading state exists. | Block authoring until manifest and active asset hydration completes, or prove an ordered replay merge. Blocking is the minimal safe Phase 1 mechanism. |
| High | IDB transaction lifetime and queue ordering are data loss seams. | `STORAGE.md:198-216` requires ordered durability units and one snapshot plus outbox transaction. | Precompute encoded records before opening the transaction. Issue all IDB requests synchronously within it. Resolve only on `complete`; reject on `abort` or `error`. Serialize commits per client and Project. |
| High | Multi tab facts are incomplete. | `clientId` is generated per store instance at `src/state/actions/localAuthoring.ts:19-24`, which gives tabs distinct IDs. Project ID and revision are constant or zero. | Retain per tab client IDs. Key pending branches and failure state by client ID. Load durable Project and asset revisions. |
| Medium | `authoredOperationValidation.ts` is at the hard file threshold. | 694 lines. New files must stay below 700 and this file has only six lines of headroom. | Do not add outbox or storage validation here. Split envelope, document, lattice, and scene body validation before any required addition. |
| Medium | `workbenchValidation.ts` mixes several owners. | 572 lines cover persisted and strict Pose guards, cells, grids, asset readers, score repair, and Workbench completion. Pairs such as `isPersistedGridFormat` and `isGridFormat` at lines 428-454 and `isCubeCell` and `isCurrentCubeCell` at lines 456-504 carry parallel permissive and strict logic. | Split pose, asset, and aggregate snapshot validation during codec extraction. Parameterize the strictness where one shared primitive owns both paths. |
| Medium | Storage types leak into runtime state. | `CubicellPersistedState`, wire steps, and `CubicellWireState` live in `src/state/cubicellState.ts:209-243`; `wireEncode.ts` imports Zustand middleware types. | Move durable record types and codecs to a storage boundary. Keep runtime state types independent. |
| Medium | The old adapter owns global listeners without disposal. | `src/state/debouncedJsonStorage.ts:109-122`; also recorded at `PERFORMANCE.md:331-346`. | Deleting the adapter removes this path. The new port exposes `close()`. |
| Medium | Store imports force localStorage setup in unrelated tests. | Many state and operation tests assign `globalThis.localStorage` before importing the singleton store. | An injected store factory removes ambient storage from pure reducer and state tests. |
| Low | One reexport has no consumer. | `src/state/historyDiff.ts:7` reexports `createJsonDiff`; searches found production consumers import it from `src/shared/jsonDiff.ts` or `src/state/index.ts`. | Delete during codec cleanup after confirming the public state barrel contract. |

Current scoped sizes:

```text
153 src/state/debouncedJsonStorage.ts
120 src/state/wireEncode.ts
 90 src/state/cubicellStore.ts
227 src/state/persistedStateNormalization.ts
 93 src/state/persistedValidation.ts
572 src/state/workbenchValidation.ts
257 src/state/cubicellHistory.ts
162 src/state/historyDiff.ts
694 src/state/authoredOperationValidation.ts
```

No scoped file exceeds 700 lines. `authoredOperationValidation.ts` cannot accept
meaningful new code without crossing the hard limit.

## Plan

### Delete and keep at cutover

Delete completely:

- `src/state/debouncedJsonStorage.ts` and its timer, dedupe, shedding, and global
  listener behavior.
- `shedHistory`, `shedPreferences`, and `shedLibrary` from
  `src/state/wireEncode.ts`.
- The Project `persist(...)` wrapper, `partialize`, storage adapter, aggregate
  `merge`, and version reset callback in `src/state/cubicellStore.ts:35-90`.
- `cubicellStorageName`, `cubicellStorageVersion`, and
  `cubicellStorageDebounceMs` at `src/config/cubicellConfig.ts:32-34`. Give the
  small preference record a new independent key and schema.
- The legacy `cubicell.workbench` reader and writer. Clear that key once during
  cutover. There are zero external users, so no v12 data importer is required.
- Tests whose product contract is quota shedding or the old Zustand wire
  envelope: `tests/debouncedStorage.dom.test.ts`,
  `tests/quotaPersistence.dom.test.ts`, obsolete sections of
  `tests/statePersistence.test.ts`, and degradation assertions in
  `tests/wireEncode.test.ts` and `tests/assetStatePersistence.dom.test.ts`.
  Replace them with IDB transaction, recovery, and explicit state tests. Do not
  retain regression tests for the rejected degradation behavior.

Keep or refactor:

- `AuthoredOperation`, pure reducer dispatch, inverse derivation, stable entity
  identity, and operation validation.
- `createJsonDiff`, safe RFC 6902 apply, history encode and repair semantics.
- Current Workbench and score repair behavior, moved behind per record decoders.
- `repairEditorSessionReferences` after local load.
- Small global preferences in localStorage through a separate, narrow
  preference port. Project panel state moves to `userProjectState`.
- An optional one bit cutover marker allowed by `STORAGE.md:223`. The current
  Zustand `version` plus `migrate` pair is not that marker and must be removed.
  The marker cannot keep a legacy reader or writer alive.

### Proposed slices

#### Slice 1. Durable Project and pose revision vocabulary

Goal: finish the semantic records the physical store must persist.

- Add the durable Project manifest and real Project ID.
- Add immutable pose revision identity and explicit asset or State references.
- Generate Project, pose revision, commit, and operation IDs before reducer
  application, following `STORAGE.md:107-131`.
- Feed loaded Project and asset revisions into local authoring. Remove the
  permanent `observedRevision: 0` assumption.
- Extend operation bodies, inverse derivation, replay validation, and fixtures
  only where pose revision creation requires it.

Reuse: `createDurableId`, `AuthoredOperation`, `deriveInverseBody`, stable
relative order helpers, and the pure authored reducer.

Gate: every changed operation JSON round trips, replays deterministically,
inverts, and preserves pose revision identity across capture, update, restore,
delete, and asset repair.

Blast: high. A missing revision reference can orphan pose data. State creation,
State update, Structure deletion, restore operations, and inverse bodies must
move together. `authoredOperationValidation.ts` is 694 lines, so split it by
operation family before adding any required validation.

This is the recommended first slice. Project and pose revision identity are
semantic facts. Deferring them would force the storage adapter to invent IDs or
write a temporary aggregate schema.

#### Slice 2. Pure versioned record codecs

Goal: define the complete IndexedDB record boundary without changing the live
writer.

- Add versioned codecs for Project manifest, Structure, Animation, immutable
  pose revision, draft, local history, outbox commit, and user Project state.
- Add pure projection from the in memory Workbench and pure hydration back to
  the existing runtime model.
- Preserve bounded undo and redo, or record an explicit doc decision before
  retaining the current redo drop.
- Build an independently decodable compact pose format. Retain safe history
  diffs. Remove the Zustand `StorageValue` dependency from codec functions.
- Split `workbenchValidation.ts` by pose, asset, and aggregate ownership rather
  than adding another validation layer.

Reuse: `encodePersistedHistory`, `applyHistoryDiff`, `createJsonDiff`,
`completePersistedWorkbench`, score repair, and session reference repair.

Gate: round trip Project manifest, Structure, Animation, pose revision, draft,
history, outbox, and user Project state independently; reject or isolate one
corrupt record without discarding unrelated records; prove exact 4,500 cube
asset round trip; record bytes and encode duration; enforce no task above 50 ms
on the reference browser.

Blast: high. The current State pose chain depends on active working pose and
array order. A new codec must not preserve that dependency across independently
addressable revisions. Corrupt record handling must avoid whole Project reset.

#### Slice 3. Atomic IndexedDB storage port

Goal: implement the physical adapter and its contract before UI integration.

- Implement the seven canonical object stores: `projects`, `assets`,
  `poseRevisions`, `drafts`, `history`, `outbox`, and `userProjectState`.
- Implement manifest plus active asset loading, independent asset loading, and
  one atomic `commit` operation.
- Write the snapshot changes and ordered outbox commit in one transaction.
- Key pending units, failure metadata, history, and scratch by Project, asset,
  user where available, and client ID where the docs require a private branch.
- Add ordered queue, retry with the same commit ID, and `close()`.

Reuse: pure codecs from Slice 2 and the `AppliedAuthoredOperation` record from
Slice 1b.

Gate: a shared port contract suite runs against the browser IDB adapter. Forced
quota, explicit abort, request error, and termination preserve the prior
revision. Transaction completion is the only successful receipt. Repeating a
commit ID is idempotent locally. Outbox order remains stable under rapid edits.
Loss tests cover every canonical store.

Blast: critical. Awaiting unrelated work inside an active IDB transaction can
let it auto commit. Encode before transaction start, issue requests together,
and resolve from `transaction.oncomplete`. Verify real Chromium in addition to
an in memory fake.

This slice introduces a tested adapter before the production cutover. Keep
Slices 3 and 4 stacked and merge them together if the project rejects a brief
period of test owned, production unwired code.

#### Slice 4. Store cutover, explicit state, and legacy deletion

Goal: make IndexedDB the sole Project writer and close the P0 gate.

- Extract one internal authored dispatcher. Use it from
  `createAuthoredActions` and `selectActiveState` so every accepted local
  applied record reaches the durability coordinator once.
- Distinguish local enqueue from replay or remote application without forking
  the pure reducer.
- Construct the Zustand store with injected storage and preference ports.
- Hydrate the manifest and active asset before authoring. Apply all existing
  normalization and session reference repair after decode.
- Add `saving`, `saved`, and `failed` state plus a shell level blocking failure
  and retry surface. Mark saved only after the IDB receipt resolves.
- Move Project panel and active asset state to `userProjectState`. Keep small
  global preferences in their separate localStorage record.
- Delete the complete legacy Project path and obsolete tests in the same PR.
  No feature flag, dual writer, fallback reader, or degradation ladder remains.

Gate:

- 4,500 cube active asset saves, reloads, and matches exactly.
- Forced quota preserves the previous valid local revision.
- Forced quota displays a blocking failed state.
- A delayed transaction remains `saving`; only completion becomes `saved`.
- Manifest, Structure, Animation, pose revision, history, draft, outbox, and
  user Project state loss tests pass.
- Refresh, forced termination, and offline restart preserve the last completed
  transaction and pending outbox work.
- No persistence task exceeds 50 ms in the reference browser.
- `pnpm build`, `pnpm lint`, the focused storage suite, the full test suite, and
  tracked tree cleanliness pass.

Blast: critical. Startup hydration can overwrite stored work if the default
store emits before load. Rapid edits can reorder snapshots and operations.
Save state updates can recursively trigger persistence if they enter the record
projection. Remote replay can echo into outbox if origin policy is omitted.
Preference and Project session splitting can silently reset panel state. Each
case needs a direct regression test before cutover.

### Review weight

Slices 1, 2, 3, and 4 all touch data loss or replay invariants and require
high blast review. Slice 4 must receive independent correctness, transaction,
history, and failure state review against the exact P0 browser evidence. Pure
mechanical deletion after the new gates pass needs one reviewer, plus a
repository wide absence scan for `createDebouncedJsonStorage`,
`cubicell.workbench`, the shedding helpers, and the old Zustand migration
contract.
