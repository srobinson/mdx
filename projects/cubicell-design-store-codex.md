# Cubicell local persistence ownership

Status: independent design for peer consensus, 2026-07-21.

Scope: replace the local client branch heuristic in PR #106 with an explicit
ownership and promotion model. This design covers local IndexedDB authority,
local conflicts, hydration, and the seam used later by hosted synchronization
and Realtime.

## Decision

Cubicell has three durable ownership zones.

| Owner | Data | Durable identity |
|---|---|---|
| Project | Manifest, every authored asset, immutable pose revisions, committed working snapshots, local commit results | Project, asset, revision, and commit IDs |
| User | Local history and Project workspace state | Project and user IDs |
| Client session | Staged commits, uncommitted working overlays, hosted outbox, and failure metadata | Project and client IDs |

`clientId` identifies one tab session. It remains useful as operation provenance
and as the owner of pending work. It never selects, keys, or validates committed
Project data.

Two completion states must remain distinct:

1. **Locally committed** means one strict IndexedDB promotion transaction has
   completed. Every client can read the result immediately.
2. **Hosted acknowledged** means Phase 2 has accepted the commit. Until then,
   the originating client's outbox retains the semantic operation envelope.

The current `drafts` store conflates these states. The replacement has separate
shared working snapshots and client owned pending commits. Source client
discovery, latest branch selection, and foreign draft adoption disappear.

## IndexedDB schema

Increment `indexedDbProjectStorageVersion` from 2 to 3 and recreate the database
with the stores below.

### Project owned stores

| Store | `keyPath` | Required row fields | Purpose |
|---|---|---|---|
| `projects` | `projectId` | `projectId`, `revision`, `manifestBytes`, `lastCommitId` | Current committed Project manifest and asset roster |
| `assets` | `[projectId, assetId]` | `projectId`, `assetId`, `kind`, `revision`, `documentBytes`, `lastCommitId` | Current committed document for every manifest asset |
| `poseRevisions` | `[projectId, revisionId]` | `projectId`, `revisionId`, `bytes`, `contentHash` | Immutable pose records shared by reference |
| `workingSnapshots` | `[projectId, assetKey]` | `projectId`, `assetKey`, `headCommitId`, `assetRevision`, `draftBytes` | Latest locally committed working pose for one asset, or detached Project scratch |
| `localCommits` | `[projectId, commitId]` | `projectId`, `commitId`, `originClientId`, `kind`, `digest`, base and result revisions, changed keys | Shared idempotency record and local commit journal |

`assetKey` is an asset UUID or the empty string for detached Project scratch.
UUIDs are nonempty, so the sentinel cannot collide with an asset.

`originClientId` in `localCommits` supplies provenance metadata only and is
excluded from the key.

The Project manifest carries the full asset roster and the current revision of
each asset. An asset write is an explicit `put` or `delete`. Omitting an asset
from a commit means unchanged. It never means delete. Asset promotion patches
only the targeted reference in the current stored manifest, preserving revision
updates made concurrently to other assets. A successful promotion therefore
cannot strand an inactive asset that was not loaded in memory.

### User owned stores

| Store | `keyPath` | Required row fields | Purpose |
|---|---|---|---|
| `history` | `[projectId, userId, assetKey]` | `projectId`, `userId`, `assetKey`, `baseCommitId`, `bytes` | Bounded local undo and redo state |
| `userProjectState` | `[projectId, userId]` | `projectId`, `userId`, `revision`, `bytes` | Active asset, active State, and panel layout |

Neither store includes `clientId`. A new tab for the same user keeps its local
history and workspace state. History is admitted only when `baseCommitId`
matches the committed working head for that asset. A mismatch clears or
quarantines history without affecting Project data.

### Client owned stores

| Store | `keyPath` | Required row fields | Purpose |
|---|---|---|---|
| `clientBranches` | `[projectId, clientId]` | `projectId`, `clientId`, `nextSequence` | Monotonic sequence allocation for one pending branch |
| `pendingCommits` | `[projectId, clientId, sequence]` | Prepared commit, full working overlay, base revisions, digest, optional failure | Durable FIFO of work not yet locally promoted |
| `outbox` | `[projectId, clientId, sequence]` | Authored commit envelope, operations, base revisions, digest | Locally committed work awaiting hosted acknowledgement |

`pendingCommits` has these indexes:

```text
byCommit       [projectId, clientId, commitId] unique
byBranchStatus [projectId, clientId, status, sequence]
```

`outbox` has these indexes:

```text
byCommit [projectId, clientId, commitId] unique
byBranch [projectId, clientId, sequence] unique
```

Failure metadata lives on the first blocked `pendingCommits` row. It is therefore
keyed by the exact Project, client, and commit. There is no database wide failure
singleton and no optional unscoped `getFailure()` API.

An outbox row is private pending hosted work. A later client may synchronize it
using the stored origin identity, but never adopts the operations into its own
branch and never replays them over the committed local snapshot.

## Prepared local commit

Projection produces an explicit change set rather than treating the loaded
Workbench library as a complete Project replacement.

```ts
type ProjectRosterChange =
  | {
      kind: 'insert'
      asset: { id: string; kind: 'structure' | 'animation' }
      beforeId: string | null
    }
  | { kind: 'move'; assetId: string; beforeId: string | null }
  | { kind: 'remove'; assetId: string }

type LocalRevisionBase = {
  projectRevision?: number
  userProjectStateRevision?: number
  assets: Array<{
    assetId: string
    revision: number
    workingHeadCommitId: string | null
  }>
  detachedWorkingHeadCommitId?: string | null
}

type PreparedLocalCommit = {
  projectId: string
  clientId: string
  commitId: string
  sequence: number
  parentCommitId: string | null
  kind: 'authored' | 'checkpoint' | 'user-project-state'
  digest: string
  base: LocalRevisionBase
  projectChange?: {
    metadataBytes?: string
    rosterChanges: ProjectRosterChange[]
    resultRevision: number
  }
  assetChanges: Array<
    | { kind: 'put'; assetId: string; bytes: string; resultRevision: number }
    | { kind: 'delete'; assetId: string; expectedRevision: number }
  >
  poseAdds: Array<{ revisionId: string; bytes: string; contentHash: string }>
  workingChanges: Array<{ assetKey: string; bytes: string; assetRevision: number }>
  historyChanges: Array<{ userId: string; assetKey: string; bytes: string }>
  userProjectStateChange?: { userId: string; bytes: string; resultRevision: number }
  operations: OutboxCommitOperations | null
  overlayBytes: string
  failure?: LocalStorageFailure
}
```

The exact wire types should reuse the current versioned codecs. New codecs are
needed only for the prepared change set, shared working snapshot, and local
commit result.

`parentCommitId` forms the client's pending chain. Rapid edits may stage several
rows. Each follower names the preceding unit and carries the revisions expected
after that unit. Promotion still processes the branch in sequence order.

## Stage and promote protocol

Every accepted edit follows two durable phases. The optimistic Zustand update
still happens first.

### 1. Stage private pending work

Projection runs in the existing worker. A short strict read write transaction
then:

1. Reads or creates `clientBranches[projectId, clientId]`.
2. Allocates and increments `nextSequence`.
3. Writes the complete `PreparedLocalCommit` to `pendingCommits`.
4. Completes without touching any Project or user owned row.

The interface remains `saving`. If projection or staging fails, the in memory
durability unit remains retryable. A deterministic codec or ownership error is
terminal and exposes `canRetry: false`.

### 2. Promote to the shared committed state

`promoteLocalCommit(projectId, clientId, commitId, digest)` opens one strict read
write transaction over every store named by the prepared change set, plus
`pendingCommits`, `localCommits`, and `outbox`.

Within that transaction:

1. Read `localCommits[projectId, commitId]` and the exact pending row.
2. If the local commit exists with the requested digest, return its prior
   receipt even when the pending row is absent. A different digest is a terminal
   identity conflict.
3. Otherwise require the pending row and reject any key, digest, or ownership
   mismatch.
4. Read the current Project, targeted assets, targeted working snapshots, and
   user Project state.
5. Compare every declared base revision and working head. No comparison is made
   against an unrelated asset.
6. Insert immutable pose revisions. Existing identical bytes are idempotent.
   Existing different bytes abort the transaction.
7. Apply explicit Project roster operations and asset puts or deletes to the
   current stored manifest. An asset put patches that asset's revision without
   replacing other references. Unmentioned asset rows and references stay
   untouched. A Project metadata or roster change compares and advances
   `projects.revision`.
8. Preserve the manifest invariant incrementally. Project creation validates
   every initial reference. A roster edit validates every added reference. An
   asset delete removes its reference in this transaction. Previously valid,
   unchanged references need no repeat read.
9. Put each changed shared working snapshot with `headCommitId = commitId`.
10. Put user history and user Project state only after all authored comparisons
   have passed.
11. Insert `localCommits[projectId, commitId]` with the resulting revision map.
12. For an authored commit, move its operation envelope to `outbox` using the
    same client sequence. Checkpoints do not enter the outbox.
13. Delete the exact pending row.

The delete and every shared write are in the same transaction. The transition
from private pending work to shared committed work is therefore atomic. A crash
or abort leaves the preceding shared state and the staged pending row intact.

Only `transaction.oncomplete` returns the local commit receipt and changes the
interface to `saved`. A request error, abort, or quota failure updates the same
pending row with retryable failure metadata in a small followup transaction. If
that diagnostic write also fails, the pending row itself remains the recovery
signal.

The idempotency row covers a lost receipt. Retrying after a completed promotion
returns the original result and cannot append a second outbox entry.

## Complete asset preservation

The current projector serializes assets present in the hydrated Workbench and
silently skips unloaded manifest assets. That behavior is valid only when the
commit payload is a change set.

The new rules are:

1. Project creation must put every asset referenced by its initial manifest.
2. An asset mutation must put that asset and list its expected prior revision.
3. An asset deletion must be explicit and must update the manifest in the same
   promotion transaction.
4. A Project metadata or working snapshot commit leaves every unmentioned asset
   row unchanged.
5. Promotion validates the complete resulting manifest before commit.

Client B can therefore hydrate active Structure S, commit without loading
inactive Animation M, and later load M from `assets[projectId, M]`. Client C does
the same. No source branch or asset copying step is involved.

## Hydration

Hydration always establishes committed state before consulting pending state.

### Shared base

1. Read `projects[projectId]` by Project ID only.
2. Decode the full manifest and asset catalog. The catalog establishes every
   committed asset ID, kind, and revision. Asset document bytes remain lazy.
3. Read `userProjectState[projectId, userId]` and choose the user's active asset.
   Fall back to the first valid Structure or detached scratch.
4. Read the active `assets[projectId, assetId]`, its
   `workingSnapshots[projectId, assetKey]`, and referenced pose revisions in one
   readonly transaction.
5. Validate the asset row against the manifest revision and the working snapshot
   against its asset revision.
6. Read matching user history. Reject history whose `baseCommitId` differs from
   the working snapshot head.
7. Publish the committed Workbench base.

The full committed Project means the complete manifest and shared addressable
asset set. The active asset is loaded eagerly. Inactive asset payloads remain
lazy to preserve the 4,500 cube startup budget.

`loadProjectAsset(projectId, assetId, expectedRevision)` reads the shared asset
key and its working snapshot without `clientId`. It also reads the current
manifest reference in the same transaction. A changed expected revision returns
a typed stale result so the store can refresh or enter conflict rather than mix
two committed revisions.

### Current client overlay

After the shared base is valid:

1. Read `pendingCommits` only for `[projectId, currentClientId]`, in sequence
   order.
2. If there is no row, hydration is ready and locally saved.
3. If the first pending base matches the shared target revisions and the chain
   is contiguous, overlay the latest pending `overlayBytes`. Restore this
   client's failure and retry state from its first blocked row.
4. If the base does not match, keep the shared state as the committed base and
   open the current client's pending overlay in conflict mode. Do not promote,
   replay, or discard it automatically.
5. Load the current client's outbox for synchronization status only. Do not
   replay it into the Workbench because every outbox operation is already in a
   shared local commit.

Foreign pending rows, failures, and outboxes are never part of another client's
editor hydration. A separate Phase 2 synchronization worker may enumerate all
outbox branches and submit each row with its stored origin `clientId`.

This order fixes both known loss paths. A fresh `clientId` reads the same shared
working snapshot, and inactive assets remain reachable through shared asset
keys after the fresh client commits.

## Multi tab behavior and V1 conflicts

IndexedDB serializes the promotion transactions. Revision and working head
comparisons turn that serialization into an explicit compare and set boundary.

### Same asset divergence

When clients A and B diverge from the same asset base:

1. The first valid promotion succeeds.
2. The second promotion observes a changed asset revision or working head and
   aborts before any shared write.
3. The losing pending row remains under its client key and receives
   `LocalRevisionConflict`, `canRetry: false`, the observed base, and the current
   committed revisions.
4. Authoring on that asset is blocked for the losing client.
5. The interface offers two V1 actions: discard the pending branch and reload
   committed state, or preserve it as a new Project. Export is also safe.

V1 performs no automatic rebase and never uses last writer wins for authored
Project data. The winning committed state and losing pending state both remain
durable.

### Different assets

Two clients may promote concurrently when they target different assets and do
not change the Project manifest. Each transaction compares only its target
asset revisions and working heads. Both asset rows survive, and neither full
Project snapshot overwrites the other.

Project manifest operations compare `projects.revision`. Two stale roster or
metadata edits conflict even when they mention different assets because the
manifest is one aggregate.

User Project state has its own revision. A stale panel only checkpoint may be
discarded as superseded after a newer user state commit. It can never block or
overwrite authored Project data.

## Phase 2 and Phase 4 path

This local design is a strict subset of the hosted model in `STORAGE.md`.

| Local record | Hosted destination or role |
|---|---|
| `projects` | `projects` current manifest and revision |
| `assets` | `assets` current checkpoint and revision |
| `poseRevisions` | `pose_revisions` immutable records |
| `localCommits` | `project_commits` and `asset_commit_changes` |
| `outbox.operations` | `commit_operations` submitted to the atomic commit RPC |
| Local revision comparison | Same expected revision rule used by the RPC |

Phase 2 adds a synchronization worker around the outbox. It sends the oldest
eligible commit for each client branch, preserves the original commit and
client IDs, records hosted acknowledgements, and deletes only acknowledged
outbox rows. A stale server revision keeps the local outbox and enters the same
conflict model. Local promotion remains unchanged.

Phase 4 adds committed remote operations through the existing semantic reducer.
After durable hosted reconciliation, the resulting checkpoint is installed into
the same shared Project and asset stores with authoritative hosted revisions.
Realtime delivery is only a low latency signal. Gaps and duplicates reconcile
through the hosted journal before local installation.

No shared key gains `clientId` in either phase. No client pending record becomes
the Project authority. The local compare and set protocol, operation envelope,
commit IDs, immutable poses, and per asset revisions are retained.

## Migration

There are zero external users. Version 3 deletes and recreates the version 2
object stores, then starts from a local reset. There is no legacy reader, source
branch fallback, compatibility shim, or record copying migration.

Small preferences and the cutover marker may remain in localStorage. An active
Project ID whose IndexedDB record was reset opens a new initial Project through
the normal bootstrap promotion.

## Implementation blast

### Storage and codecs

- `indexedDbSchema.ts`: create the version 3 stores and indexes. Delete
  `byProjectSequence`, `draftBranchRange`, and client keyed Project and asset
  keys.
- `storagePort.ts`: separate committed Project lookup from the current client
  branch. Make branch arguments mandatory for pending and failure APIs.
- `storageRecords.ts`: project explicit changes. Stop treating the loaded asset
  list as a complete replacement. Remove `sourceClientId` from hydration.
- `projectRecordProjection.ts` and `projectCommitProjection.ts`: emit base
  revisions, explicit asset changes, shared working changes, and the private
  overlay in the worker.
- Add codecs for `PreparedLocalCommit`, `workingSnapshots`, and `localCommits`.
  Reuse the existing Project, asset, pose, history, outbox, and user state
  codecs.

### IndexedDB and memory ports

- `indexedDbProjectStorage.ts`: split staging, promotion, committed hydration,
  and lazy asset reads into focused modules. Remove source branch selection.
- `indexedDbFailureState.ts`, `indexedDbFailureValidation.ts`, and
  `indexedDbUserProjectState.ts`: replace the global or draft based recovery
  paths with branch scoped pending rows. Delete superseded paths after callers
  move.
- `memoryProjectStorage.ts`: mirror the same stores and promotion contract as
  the fast contract implementation with identical semantics.
- `orderedCommitQueue.ts`: retain FIFO per Project and client. Treat revision
  conflicts as terminal and retryable storage failures as blocking but
  recoverable.

### Store integration

- `projectDurability.ts`: stage, promote, publish receipts, overlay current
  client pending work, and expose typed conflict state. Retry only transient
  failures.
- `projectAssetActions.ts`: lazy load by shared Project and asset key with an
  expected revision fence.
- `cubicellStore.ts`: hydrate shared base first and inject the current branch
  only into pending APIs.
- `preferencePort.ts`: keep `clientId` in sessionStorage. Remove every use of it
  as a committed lookup address.

### Documentation

- Update `STORAGE.md` local persistence and Phase 1 status to name local
  promotion and shared committed ownership.
- Update `ARCHITECTURE.md` source ownership for the new modules.
- Keep `PERFORMANCE.md` eager active asset and lazy inactive asset budgets.
- Record the final conflict and reset decisions in `LESSONS.md` if implementation
  review changes them.

No changed source file may exceed 700 lines and no function or suite callback
may exceed about 150 lines. The IndexedDB implementation should be decomposed by
schema, pending staging, promotion, committed reads, and user state ownership.

## Verification matrix

| Area | Required proof |
|---|---|
| Schema ownership | No Project owned key contains `clientId`; every pending, outbox, and failure lookup requires it |
| Memory contract | Initial promotion, explicit asset put and delete, idempotent retry, branch FIFO, conflict, and lazy load match IndexedDB semantics |
| Atomic promotion | Abort, request error, quota, validation failure, and lost receipt preserve the previous shared state and the exact pending row |
| Complete assets | Project with active Structure and inactive Animation rotates client, commits before loading Animation, then both that client and a third client load Animation exactly |
| Fresh client recovery | New session client hydrates the exact committed Workbench, history policy, user state, Project revision, active asset, and scratch digest |
| Pending isolation | Two real Chromium pages cannot read, clear, retry, or overwrite each other's pending rows or failures |
| Same asset race | Two pages diverge from one base; one promotion wins, the other enters conflict, winner remains committed, loser pending bytes remain exact |
| Different asset race | Two pages change different assets; both promote and every asset plus manifest reference survives |
| Manifest race | Concurrent roster changes produce one winner and one durable conflict with no dangling or deleted asset |
| Retry policy | Worker or transient transaction failure enables retry; ownership, codec, and revision conflicts do not |
| Outbox | Local promotion appends once, fresh clients do not replay or rehome it, hosted acknowledgement deletes only the exact origin row |
| User state | A failed panel checkpoint from client A never blocks client B; stale user state cannot affect authored records |
| History | Client rotation preserves matching history; stale or corrupt history is contained without changing committed Project data |
| Lazy consistency | Lazy reads use shared keys and return a typed stale result rather than mixing manifest and asset revisions |
| Performance | Real Chromium saves and restores 4,500 cubes with no main thread task above 50 ms and does not read inactive asset bytes at startup |
| Migration | Opening version 2 resets to version 3 with no legacy reader or parallel writer |

Run the storage contract against memory and IndexedDB. Run the concurrency,
quota, termination, client rotation, lazy asset, and long task cases in real
Chromium. Repeat the deterministic unit and browser gates three times before
signoff.

## Principal tradeoff

The design chooses strict optimistic conflict over automatic merge for two
clients editing the same asset. That blocks the losing tab and requires an
explicit preserve or discard choice, but it guarantees that a locally committed
asset is never silently replaced. The same revision boundary becomes the
hosted commit boundary later, so this safety does not create a V1 only path.
