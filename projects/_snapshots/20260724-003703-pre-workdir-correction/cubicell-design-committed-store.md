# Cubicell committed-store model (canonical)

Status: canonical design for consensus sign-off then implementation, 2026-07-21.
Synthesizes `cubicell-design-store-{opus,codex,grok}.md` plus the divergence
semantics settled by the owner and orchestrator. Supersedes the targeted
clientId patch on PR#106 (`feat/persist-cutover`); the committed store is a
fresh slice. References cite file + symbol, never line numbers.

Owning doc for physical shape remains `STORAGE.md`; this document specifies the
local IndexedDB committed-store slice it calls for.

---

## 0. The category error and the fix in one paragraph

`clientId` is a per-tab `sessionStorage` session id (`preferencePort` `readClientId`).
Slices 1-4 key committed project data by it (`projects[projectId, clientId]`,
`assets[projectId, clientId, assetId]`, the committed working scene inside
`drafts[projectId, clientId, commitId]`). Hydration then *guesses* the latest
committer branch (`issueSourceRequests` in `indexedDbProjectStorage.ts`) and
reads committed data through a foreign client key. PR#106 patched the read to
tolerate a foreign branch; it did not remove the client key. This design removes
it: committed data becomes client-independent and per-asset revision-ordered, a
`promote` step moves a landed edit into it under an optimistic revision guard,
and a behind session **syncs forward by rebasing its pending operations** onto the
ahead session's committed result. The same rule serves two tabs now (pull) and
Realtime later (push) with zero storage rework.

---

## 1. Ownership and exact IndexedDB layout

Three ownership zones. `clientId` is operation provenance and the owner of pending
work; it never keys, selects, or validates committed data.

Bump `indexedDbProjectStorageVersion` 2 → 3 in `indexedDbSchema.ts`;
`createIndexedDbProjectSchema` already deletes and recreates every store.

### Committed — Project-owned, client-independent, revision-ordered

| Store | `keyPath` | Row (logical) | Purpose |
|---|---|---|---|
| `projects` | `['projectId']` | `projectId`, `revision`, `manifestBytes` (roster + order + per-asset revision map), `schemaVersion` | Committed manifest; one row per project |
| `assets` | `['projectId', 'assetId']` | `projectId`, `assetId`, `kind`, `committedRevision`, `documentBytes`, `lastCommitId`, `schemaVersion` | Committed checkpoint for **every** manifest asset |
| `poseRevisions` | `['projectId', 'revisionId']` | `projectId`, `revisionId`, `bytes`, `contentHash` | Immutable, add-only, shared by reference |
| `localCommits` | `['projectId', 'commitId']` | `projectId`, `commitId`, `originClientId`, `kind`, `digest`, base+result revision map, changed asset keys | Idempotency journal + local commit receipt (see §2) |

`assets.committedRevision` is the local mirror of hosted `assets.checkpoint_revision`;
`projects.revision` mirrors hosted `projects.revision`. These bigints, not
`clientId`, order committed state. `localCommits.originClientId` is provenance
only and is excluded from the key.

### Pending — client-owned, private to one tab session

| Store / index | `keyPath` | Row (logical) | Purpose |
|---|---|---|---|
| `drafts` | `['projectId', 'clientId', 'assetKey']` | `projectId`, `clientId`, `assetKey`, `baseRevision`, ordered `pendingOps: AppliedAuthoredOperation[]`, cached `overlayBytes?`, `failure?` | This client's un-promoted branch for one asset; `pendingOps` is the replay log for rebase (§4) |
| `outbox` (`byBranchSequence`) | idx `['projectId','clientId','sequence']` unique | authored commit envelope awaiting hosted ack | Hosted-sync journal only |
| `outbox` (`byCommit`) | idx `['projectId','clientId','commitId']` unique | — | Hosted-sync idempotency |

`assetKey` is the asset UUID, or the empty string sentinel for detached
pre-first-State scratch (UUIDs are non-empty, so no collision — from codex).
Failure lives on the blocked `drafts` row, not on any committed row and not in a
database-wide singleton. `orderedCommitQueue.ts` keeps its per-`[projectId, clientId]`
FIFO and its `byCommitId` idempotency map.

### User-owned — per user, already client-independent

| Store | `keyPath` | Change |
|---|---|---|
| `history` | `['projectId', 'userId', 'assetKey']` | **drop `clientId`** (STORAGE.md "Private per user and asset"; the `clientId` dimension silently resets undo/redo on a same-user new tab). Admitted on hydrate only if its `baseCommitId` matches the committed head, else quarantined without touching project data |
| `userProjectState` | `['projectId', 'userId']` | unchanged |

**Removed keys/paths:** `outbox.byProjectSequence` as a committed-read source;
`draftBranchRange`; the client dimension on `projects`/`assets`/`history`;
`issueSourceRequests` source-branch selection; `readableOutbox`/`sourceClientId`
committed-recovery machinery from PR#106.

Net: `clientId` appears only on `drafts` and `outbox`. Nothing committed or
durable-shared is keyed by the ephemeral session id.

---

## 2. Atomic PROMOTE (the currently-missing step)

Today `issueCommitWrites` writes the working scene straight into the client-keyed
`drafts` row; committed and pending share one physical row. Replace with an
explicit promote: one strict `readwrite` transaction, `durability: 'strict'`, no
`await` across the transaction boundary, receipt only on `transaction.oncomplete`.

**The local-edit lifecycle has two durable steps: `stagePending` then `promote`.**
The optimistic Zustand apply still happens first. `stagePending` is a first-class
part of the lifecycle, not an implementation detail: when an authored edit is
enqueued (`projectDurability.ts` enqueue path, before promote), the client's
`drafts[projectId, clientId, assetKey]` row is durably written with `baseRevision`
(the `committedRevision` the edit was authored against) and the appended ordered
`pendingOps: AppliedAuthoredOperation[]` log. This staged row is the **source of
truth for rebase**: without it, a stale promote discovered after a browser restart
would have no durable pending log to replay, so the rebase (§4) would not be
buildable. `stagePending` writes only the client-owned `drafts` row (one short
strict transaction) and touches no committed store; the interface stays `saving`.

**Projection is a change set, not a full-Workbench replacement.** The current
projector (`projectCommitProjection.ts`, `storageRecords.ts`) serializes only the
assets present in the loaded library and silently skips unloaded manifest assets.
The promote payload instead declares explicit roster ops (`insert|move|remove`
with `beforeId` anchors) and per-asset `put|delete` with an `expectedRevision`.
Omitting an asset means unchanged, never delete. This is the source-level fix for
the strand (§3), independent of keying.

```
promote(projectId, clientId, commitId, digest, base, changes):
  TX readwrite over
    [projects, assets, poseRevisions, drafts, history, outbox, localCommits]

  1. IDEMPOTENCY (reuse byCommit pattern from ProjectCommitQueues.byCommitId)
     prior = localCommits.get([projectId, commitId])
     if prior && prior.digest === digest: return prior.receipt   # replayed promote, no second write
     if prior && prior.digest !== digest: abort -> terminal identity conflict

  2. REVISION GUARD (compare-and-advance, per targeted asset)
     for each asset A in changes.assets:
       stored = assets.get([projectId, A.assetId])
       if (stored?.committedRevision ?? 0) !== A.expectedRevision:
         abort TX -> StalePromote{ assetId, expected, actual }   # §4 sync-forward
     if changes.project: assert projects.get([projectId]).revision === base.projectRevision

  3. ADVANCE (revisions matched -> apply atomically)
     for each new pose: poseRevisions.add (idempotent on identical bytes; differing bytes abort)
     for each asset A: assets.put({ …A.document, committedRevision: A.expectedRevision + 1, lastCommitId: commitId })
     apply roster insert/move/remove to manifest; projects.put(manifest, revision+1) if project changed
     history.put([projectId, userId, assetKey], entry)
     localCommits.put({ projectId, commitId, digest, originClientId: clientId, result revision map, changed keys })
     for authored kind: outbox.add(envelope)                     # checkpoints do not enter the outbox
     # CONSUME the promoted commit from the pending log, head-first (see "Draft consumption"):
     for each assetKey in changes.touchedAssetKeys (plus '' if changes.project/detached):
       row = drafts.get([projectId, clientId, assetKey])
       remove this commit's ops from the HEAD of row.pendingOps    # only this envelope
       if row.pendingOps now empty: drafts.delete([projectId, clientId, assetKey])
       else:                        drafts.put(row)               # RETAIN the unpromoted suffix

  4. oncomplete -> receipt{ projectId, commitId, result revisions }; saveState 'saved'
```

**Draft consumption is head-first, one envelope per atomic tx.** The `drafts` row's
`pendingOps` is a durable FIFO of un-promoted commit envelopes; each promote (single
or a rebase iteration in §4) removes **only its own** head envelope from every
touched-asset row and the project/detached sentinel (`assetKey === ''`), retaining
the unpromoted suffix, and deletes the row **only when it becomes empty**. It is
**not** a blanket delete of the whole row after the first of N envelopes — a crash or
competing promote between envelopes must leave envelopes 2..N durable (§4). A single
authored commit spanning several assets (e.g. deleting a Structure while repairing a
dependent Animation) is one envelope, so its head-removal across those touched keys
happens in the one transaction and leaves no orphan overlay.

Atomicity: the head-consume and every committed write share one transaction, so
the private→shared transition is atomic per envelope; a crash/abort leaves the prior
committed state and the still-unpromoted `pendingOps` suffix intact. Idempotency: the
`localCommits` row
covers a lost receipt — retry returns the original receipt and never appends a
second outbox entry, matching the merged Slice 3 `byCommitId` guard and the hosted
commit RPC's "return prior result when commit ID exists" (STORAGE.md §Commit
protocol 3). A failed promote writes `drafts.failure` in a small follow-up
transaction; if that also fails, the staged `drafts` row is itself the recovery
signal. `canRetry` follows the merged `362d9a3` policy (transient/worker failures
retryable; `SupersededStorageCommitError` and identity/digest conflicts terminal).

---

## 3. HYDRATION

Committed-first, client-independent, all assets reachable; then this client's
pending overlay. No `issueSourceRequests`, no source-branch inheritance.

```
hydrate(projectId, clientId, userId):
  # A. COMMITTED BASE (shared, no client key)
  manifest = projects.get([projectId])
  if !manifest: return fresh/new project bootstrap
  activeAssetId = userProjectState.get([projectId, userId]).activeAssetId
                  ?? first valid Structure ?? detached scratch
  activeAsset = assets.get([projectId, activeAssetId])
  poses       = poseRevisions referenced by activeAsset
  history     = history.get([projectId, userId, activeAssetKey])   # admit iff baseCommitId matches committed head
  # manifest establishes the full roster; every roster asset is reachable via
  # assets.get([projectId, assetId]) with NO clientId. Inactive bodies stay lazy.

  # B. THIS CLIENT'S PENDING OVERLAY (only client-scoped read)
  draft = drafts.get([projectId, clientId, activeAssetKey])
  if draft:
     if draft.baseRevision === activeAsset.committedRevision:
        working = decode(draft.overlayBytes)            # contiguous: overlay directly
        pendingOps = draft.pendingOps
     else:
        working, pendingOps = syncForwardRebase(draft, activeAsset)   # §4 (behind at open time)
     saveState = draft.failure ? restoreFailed(draft) : (pendingOps.length ? 'saving' : 'saved')
  else:
     working = checkpointToWorking(activeAsset)         # committed checkpoint IS the canvas
     saveState = 'saved'

  # C. lazy inactive asset load, still client-independent
  loadProjectAsset(assetId, expectedRevision):
     row = assets.get([projectId, assetId])             # typed-stale if row.committedRevision !== expectedRevision
```

This fixes both loss paths at the source:

- **Fresh-clientId reopen Blocker:** `working` derives from committed
  `assets[projectId, activeAssetId]`, never from a client-keyed draft; a new tab
  with no draft recovers the exact committed scene, default Workbench only when the
  project is genuinely absent.
- **Inactive-asset strand (`indexedDbProjectStorage.ts` partial-body path, codex
  Major):** `assets` carries no `clientId`, so `loadProjectAsset` reaches every
  roster asset regardless of which session last promoted it; and because promote
  is a change set (§2) that advances only targeted assets, a commit touching only
  the active asset leaves untouched assets' committed rows intact and reachable.
  Both the keying and the projection change are required; either alone still
  strands. Before any promote, the coordinator runs `ensureFullRoster()` (lazy-fill
  missing library members from committed `assets`) so a partial library can never
  produce a partial promote — partial promote is a hard dev error and a blocked
  save in prod.

Outbox is loaded for hosted-drain status only and is **never re-applied** onto the
Workbench — its operations are already in the committed checkpoint after promote.

---

## 4. DIVERGENCE — committed revision is authoritative; behind syncs forward (the settled refinement)

The V1 boundary is one active writer per asset. Committed data is never
overwritten by a stale writer, and the behind writer's work is not blocked behind
a UI — it is rebased forward automatically.

```
Clients A and B both hold committed asset revision R and local edits.
A promotes first: guard R === R, advance -> committedRevision R+1.
B promotes with expected R: guard sees R+1 ≠ R -> StalePromote (no committed write).

syncForwardRebase(B):
  # HEAD-FIRST DRAIN: one envelope per atomic tx, re-reading the committed tip each
  # iteration so a competing promote or a crash between envelopes is safe.
  while B.draft.pendingOps is non-empty:                 # the draft row IS the durable cursor
     env = head envelope of B.draft.pendingOps           # one commit's ops, oldest first
     base' = assets.get([projectId, assetId])            # CURRENT committed tip (may have advanced since last env)
     working' = checkpointToWorking(base')
     coordinator' = fresh HistoryCoordinator seeded from base'
     newCommitId = createDurableId()                     # ONE new id for the whole rebased envelope
     ops = []
     for op in env.operations (in order):
        reduction = reduceAuthoredOperationState(working', op.operation, coordinator')
        if reduction.applied === null:                   # rejectedReduction sentinel -> contextual reject
           -> ABORT: drop the REMAINING pendingOps (env..tail), reload to committed tip (policy below)
        apply reduction.update to (working', coordinator')
        ops.push({
          operation:  { ...op.operation, commitId: newCommitId },  # SAME id for every op in this envelope
          inverseBody: reduction.applied.inverseBody,    # RECOMPUTED per op against the current base'
        })
     ATOMIC TX (this envelope only):
        promote(..., base = base'.committedRevision, commitId = newCommitId, operations = ops)
          -> compare-and-advance base'.committedRevision -> +1     # guard re-checked against the CURRENT tip
          -> write this envelope's OWN localCommits receipt
          -> supersede this envelope's pre-rebase outbox entry (see "Supersede" below)
          -> remove ONLY this head envelope from drafts.pendingOps; RETAIN the unpromoted suffix
          -> if pendingOps now empty: delete the drafts row (fully drained)
  # N pending commits -> N sequential advances (each guard-checked against the live tip),
  # N receipts, consumed head-first. A crash or competing promote between envelopes leaves
  # env..tail durable in drafts.pendingOps; the loop resumes from the new committed tip.
```

**Reject detection (consensus #1).** Contextual replay rejection is detected via
`reduceAuthoredOperationState` in `src/state/actions/authoredReducer.ts`: on any
context failure (target not in `state`, project mismatch, invalid reference,
missing inverse, etc.) it returns the `rejectedReduction` sentinel
(`{ applied: null, update: {} }`). The signal is `reduction.applied === null`, and
on a successful op the caller **must apply `reduction.update`** (the returned
`CubicellState` + `HistoryCoordinator` update) before the next op — the reducer is
the state transition, not a predicate. `validateAuthoredOperation`
(`src/state/authoredOperationValidation.ts`, `unknown -> AuthoredOperation | null`)
is **schema validation only** and is **not** the unreplayable signal; it is used
only to parse a stored envelope, never to decide replayability.

**Commit identity on rebase — one id per envelope, not per op (consensus #1).**
`src/persistence/recordCodecs/outboxCommitRecordCodec.ts` `encodeOutboxCommitRecord`
derives the envelope `id` from `first.commitId`, and `decodeOutboxCommitRecord`
**rejects any envelope in which some `operations[i].operation.commitId !== value.id`**.
Therefore `syncForwardRebase` mints exactly **one** new `commitId` (`createDurableId`)
**per rebased commit envelope** and assigns that same id to **every operation
embedded in that envelope**; it does **not** mint per op. The original commit
grouping is preserved through the rebase — a rebased commit remains one envelope of
its ops sharing one id. `inverseBody` is still recomputed **per op** against `base'`
(from each op's `reduction.applied`). A per-op id (the prior draft of this design)
would produce an envelope whose non-first ops carry a different `commitId` than
`value.id` and fail `decodeOutboxCommitRecord`; a carried-over id or stale inverse
would corrupt the outbox/idempotency journal.

**Supersede the pre-rebase outbox atomically (consensus #2).** In the **same**
atomic transaction that adds each reminted envelope, `syncForwardRebase` must delete
(or replace) every superseded pre-rebase `outbox` envelope it replaces — matched by
the original `commitId` via the `byCommit` index. Otherwise the Phase-2 sync worker
could drain **both** the stale and the rebased commit for the same authored work.
After a rebase, no stale outbox entry for a superseded commit remains; only the
reminted envelopes are drainable.

**Per-commit granularity is preserved through the rebase.** When the pending log
holds N commits, each rebased envelope re-promotes as its **own** atomic revision
compare-and-advance with its **own** `localCommits` receipt, in original commit
order, consumed head-first from `pendingOps` (one envelope per transaction). Absent
interference the tip walks `R+1 -> R+2 -> ... -> R+1+N`; because each iteration
re-reads the live committed tip and re-checks the guard, a competing same-asset
promote may interleave (advancing the tip further) and the next envelope simply
rebases onto the newer revision — still one advance and one receipt per pending
commit, none skipped or collapsed. The local commit journal after a rebase therefore
mirrors exactly the shape the hosted `project_commits` journal would carry (one row
per commit), keeping Phase-2 sync a straight one-envelope-per-RPC drain.

Properties:

- **Automatic and lossless on the happy path.** No conflict dialog, no user
  "decline" flow in V1. The ahead work is adopted; the behind session's own edits
  are rebased on top, reminted, and re-promoted. `reduceAuthoredOperationState` (the
  same pure reducer used for local apply and for future remote apply) and the
  `AppliedAuthoredOperation` `{ operation, inverseBody }` log (slices 1/1b) are
  reused directly — no new merge engine.
- **Unreplayable policy — abort the remaining rebase and reload to committed tip
  (consensus #2, owner-decided).** On **any** op that
  `reduceAuthoredOperationState` rejects (`reduction.applied === null`) while
  rebasing the current head envelope, the rebase aborts and the session reloads to
  the committed tip. The **entire remaining uncommitted overlay** — the current
  rejected envelope and the whole still-un-promoted `pendingOps` tail, including
  replayable envelopes behind the rejected one — is dropped in one delete of the
  `drafts` row; hydration re-derives `working` from the committed checkpoint. Any
  envelopes **already** promoted earlier in this same head-first drain stay
  committed (they durably advanced the tip and are not overlay); everything still in
  `pendingOps` at the moment of rejection is dropped together. Within the un-promoted
  overlay there is **no partial apply, no surviving replayable tail, and no
  permanently-failing draft left behind** — not skip-the-op-and-continue, not a
  stuck-draft state. Rare (a pending op whose target was removed upstream),
  acceptable V1 behavior, no UI beyond a "reloaded to latest" notice.
- **Never silent last-writer-wins:** committed writes happen only behind the
  revision guard; the stale promote writes nothing until its rebase re-promotes at
  the advanced revision.

Add a `syncing` transition to `LocalSaveState` (`cubicellState.ts`) between
`saving` and `saved` for the rebase window; `failed` remains for genuine storage
failure. Same-asset serialization is guaranteed by IndexedDB transaction ordering;
the revision guard turns that ordering into the compare-and-advance boundary.

---

## 5. Two-tab (V1) and Realtime (Phase 4) are the same rule

The committed store, revision guard, and sync-forward-rebase are transport
independent. **Zero storage rekey, two write paths** — the shared stores and keys
are identical; only which function advances them differs:

| | Transport | How the advance is discovered | Write path | Rebase source |
|---|---|---|---|---|
| **V1 (pull)** | none | at promote time: the guard rejects a stale base | `promote` (local authorship) | this client's `drafts.pendingOps` |
| **Phase 4 (push)** | Supabase Broadcast (STORAGE.md live path) | a committed operation batch streamed live/incrementally | `installCommitted(remote)` | `drafts.pendingOps`, or the `outbox` for already-promoted-but-unacked work (below) |

**Two write paths, not one (consensus #6).** `installCommitted(remote)` is a
distinct function from `promote`, sharing the guard, the shared storage keys, and
the `localCommits` idempotency journal, but differing in ownership side effects:

- `installCommitted` advances `projects` / `assets` / `poseRevisions` /
  `localCommits` under the **same** per-asset revision guard and the **same** shared
  keys (zero rekey).
- It **must not** delete this client's other pending `drafts` rows (they are local
  authorship the remote commit did not promote), and it **must not** `outbox.add` —
  a remote commit is not this client's outgoing authorship.
- After installing, if a locally pending draft's `baseRevision` is now behind, it
  is rebased forward by the same `syncForwardRebase` (with remint + re-inverse),
  exactly as a stale local promote.

**Rebase source for locally-promoted-but-hosted-unacknowledged commits
(consensus #6 / codex#3).** When a remote commit advances a base that this client
has already *locally promoted* but the hosted sync has not yet acknowledged, the
`drafts` row was already deleted by `promote` (§2), so the pending overlay is no
longer the rebase source. The rebase source is the **`outbox`** — the committed
envelopes awaiting hosted ack. `syncForwardRebase` replays those outbox operations
(reminting commitId + re-inverse) onto the newly installed committed base and
re-promotes, so locally-committed-not-yet-synced work is carried forward losslessly
under the same rule. Draft is the rebase source before local promote; outbox is the
rebase source after.

This is why the guard and rebase are built now rather than a throwaway two-tab
patch: the two-tab pull path *is* the collaboration path minus the wire, and the
only Phase-4 addition is the transport (a sync worker draining `outbox` to the
commit RPC + a Realtime `installCommitted`) over this exact committed store.

Forward-compat mapping (strict subset of STORAGE.md hosted model):

| Local (this design) | Hosted destination |
|---|---|
| `projects` / `assets` + `committedRevision` | `projects` / `assets` + `revision`/`checkpoint_revision` |
| `poseRevisions` | `pose_revisions` |
| `localCommits` | `project_commits` + `asset_commit_changes` |
| `outbox` envelopes | `commit_operations` via the commit RPC |
| revision guard | RPC expected-revision compare (STORAGE.md §Commit protocol 5-6) |
| `syncForwardRebase` | §Conflict behavior stale-revision rebase-replay |

No shared key gains `clientId` in any phase; no client pending row becomes project
authority.

### Phase 4 (deferred): local-speculative vs remote-authoritative reconciliation

Scoped to Phase 4; **not implemented in V1**, defined here so the guard and rebase
built now are reused rather than reworked. Local promote advances an asset
`committedRevision` *speculatively* — locally authoritative, but hosted-unacked
until the sync worker's commit RPC acknowledges it. A hosted authoritative commit
for the same asset can arrive at base R while this client has already speculatively
advanced R → R+1.

Rule: **the remote hosted commit is authoritative; the local R+1 is speculative.**
`installCommitted` must adopt the authoritative revision rather than be rejected by
the shared revision guard as if it were a stale *local* promote. The guard must
therefore distinguish **authoritative-remote-install** from **local-promote**:

- A **local promote** at a stale base is rejected → `syncForwardRebase` (V1 rule).
- An **authoritative-remote-install** is never rejected by the guard. It installs
  the hosted revision over the local speculative one, then rebases the local
  speculative work — sourced from the **`outbox`** (the speculative commit was
  already promoted locally, so its draft is gone) — onto the authoritative base via
  the same `syncForwardRebase` (same remint-per-envelope, re-inverse, supersede-old-
  outbox rules), and re-promotes. The local speculative commit is thus reconciled
  onto the hosted authority losslessly, or reloads if a pending op is unreplayable.

The guard input carries a provenance tag (`authoritative` vs `speculative-local`)
so the incoming hosted batch is installed and its outbox replayed, never dropped by
the guard before replay. This is the only Phase-4-specific reconciliation; the V1
two-tab path never produces a speculative-vs-authoritative split because all local
promotes are equally authoritative until hosting exists.

**Out of scope for this design (owner decision).** The remote-streaming
*reconciliation mechanics* — a durable authoritative revision watermark, rejection
of duplicate and out-of-order remote events, and revision-gap handling — are **not**
specified here and will be defined in the dedicated Phase-4 design when the realtime
transport is built. This V1 spec fixes only the storage layout, promote, revision
guard, hydration, `stagePending`, and the local `syncForwardRebase`; it deliberately
does not specify the remote transport protocol. The committed store + guard + rebase
are the reused foundation, and the transport-reconciliation layer sits **above**
them — it consumes `installCommitted` and the guard's provenance tag but adds its own
watermark/ordering/gap logic. Nothing in that later layer re-keys or reworks the V1
storage.

---

## 6. Migration

Zero external users. Per STORAGE.md §Durable identity ("an incompatible shape can
reset local data rather than introduce legacy readers or parallel migration paths")
and the standing single-user/no-migration rule: bump
`indexedDbProjectStorageVersion` 2 → 3; `onupgradeneeded` deletes every v2 store and
recreates with the new keyPaths. No legacy reader, no dual-write, no record-copying
migrator, no source-branch fallback. The memory-storage twin
(`memoryProjectStorage.ts`) moves to the same key model in the same PR. The one-time
`cubicell.workbench` localStorage clear (`preferencePort` `clearLegacyProject`) and
`clientId` generation are unaffected.

---

## 7. Supersedes PR#106 — what survives, what is replaced

This design replaces the targeted clientId patch on `feat/persist-cutover`. The
committed store is a fresh slice, not a follow-up commit on that branch.

**Survives (keep from the cutover):**
- Sole-writer / dispatcher-driven durability wiring (`authoredDispatcher.ts`,
  `localDurabilityPublisher.ts` reserve/complete ordering).
- Explicit `LocalSaveState` and the "never saved before `transaction.oncomplete`"
  contract (`projectDurability.ts`), extended with `syncing`.
- The `canRetry` / branch-scoped `getFailure(branch)` fix landed in `362d9a3`.
- Legacy-path deletion (`debouncedJsonStorage`, partialize, the localStorage
  Workbench writer) and the one-time legacy clear.
- The strict-transaction atomicity core, worker projection, `segmentedJson` /
  `taskYield` main-thread budget, and the `byCommitId` idempotency pattern.

**Replaced (delete):**
- Client-keyed committed stores (`projects[projectId, clientId]`,
  `assets[projectId, clientId, assetId]`) and the committed working scene living in
  the client-keyed `drafts` row.
- Source-branch head selection (`issueSourceRequests`) and foreign-draft
  inheritance (`readableOutbox`, `sourceClientId` on hydration bytes,
  `draftValue` validated against the reader's client).
- `outbox.byProjectSequence` as the committed-tip discovery mechanism.
- The full-library-as-complete-project projection assumption.

---

## 8. Blast radius and test matrix

### Code that changes (slices 1-4)

| File / symbol | Change |
|---|---|
| `indexedDbSchema.ts` | version 3; `projects['projectId']`, `assets['projectId','assetId']`, `drafts['projectId','clientId','assetKey']`, `history['projectId','userId','assetKey']`; add `localCommits`; drop `byProjectSequence` committed use and `draftBranchRange` |
| `indexedDbProjectStorage.ts` | delete `issueSourceRequests`; `promote()` with revision guard + `localCommits` idempotency + head-first `pendingOps` consume (delete row only when drained); committed-first hydration; `loadAsset` by `[projectId, assetId]`. Decompose (schema / staging / promote / committed reads / user state) to stay < 700 |
| `storageRecords.ts` | change-set projection; committed records validated by projectId/assetId/`committedRevision`; remove `sourceClientId`/`readableOutbox` committed machinery; draft validated by `clientId` |
| `projectCommitProjection.ts` | emit base revisions + explicit roster/asset change set; fail on incomplete roster |
| `indexedDbHydrationBytes.ts` | committed validators use project keys; drop `address.clientId` draft equality and `sourceClientId` field |
| `projectRecordHydration.ts` `resolveWorking` | committed checkpoint is the base; pending draft overlays it; detached default only when project absent |
| `projectDurability.ts` | `stagePending` (durable `drafts` `baseRevision` + `pendingOps[]` at enqueue, before promote); track `expectedRevision`; `ensureFullRoster` before promote; `syncForwardRebase` via `reduceAuthoredOperationState` (reject = `rejectedReduction`, `applied === null`) with commitId remint + `inverseBody` recompute; add `syncing` save state |
| `authoredReducer.ts` (`reduceAuthoredOperationState`, `rejectedReduction`) | reused as the rebase replay + reject-detection seam; no change beyond being driven by `syncForwardRebase` |
| `outboxCommitRecordCodec.ts` | unchanged; constrains rebase to remint `commitId` + re-derive envelope `id` (`encodeOutboxCommitRecord`) so `decodeOutboxCommitRecord`'s `commitId === id` check holds |
| `indexedDbUserProjectState.ts` / `indexedDbFailureState.ts` | failure only on the client `drafts` row; branch-scoped restore |
| `memoryProjectStorage.ts` | mirror the layout + promote/guard/rebase contract (test-parity twin) |
| `orderedCommitQueue.ts` | commit carries `expectedRevision`; FIFO + `byCommitId` unchanged; stale promote is a distinct non-blocking `syncing` outcome, not a terminal failure |
| `projectStorageContract.ts` | replace foreign-draft expectations with committed-shared + rebase expectations |
| `STORAGE.md` | name local promote + shared committed ownership in Phase 1 status |

### Test matrix (real Chromium `cubicellStore.browser.test.ts` + memory/unit twins, x3 pre-signoff)

| # | Gate | Assertion |
|---|---|---|
| T1 | Fresh-clientId reopen | rotated `clientId` recovers committed digest (project + library + workbench) exactly; `outbox.length === 0` |
| T2 | Multi-asset reachability | assets A,B,C; edit+promote only active A under client X; reopen under Y; `loadProjectAsset(B)`/`(C)` present at correct revision; reopen under Z, A still exact |
| T3 | Partial-library promote blocked | library missing B; promote → hard error/blocked save; committed tip unchanged |
| T4 | Two-tab pending isolation | A holds an un-promoted/failed draft on X; B hydrates committed X only, never A's overlay/failure; B can edit and promote |
| T5 | Stale promote → sync-forward-rebase | A and B from rev R; A promotes → R+1; B's pending log holds **N commits, at least one a multi-op envelope**; B rebases onto R+1 → each envelope re-promotes in order to its **own** sequential revision `R+2 … R+1+N` with its **own** `localCommits` receipt (no collapse, no skipped revision); **both A's and B's edits present**; committed never regressed; each reminted envelope (incl. the multi-op one) round-trips through `encodeOutboxCommitRecord`/`decodeOutboxCommitRecord` (every op's `commitId === envelope.id`); reminted ids distinct from originals |
| T5b | Crash + competing promote mid-rebase | B has N≥3 pending commits rebasing onto R+1; inject a crash **and** a competing same-asset promote (advancing the tip) between envelope 1's and envelope 2's atomic tx; assert envelope 1 stayed committed, envelopes 2..N remained durable in `drafts.pendingOps`, and on resume they rebase onto the **new** committed revision with no loss, no double-apply, no reorder — each still one sequential revision + one receipt; final `pendingOps` empty and its `drafts` row deleted |
| T6 | Mid-log unreplayable op → remaining-overlay reload | B's `pendingOps` = [env1 replayable, env2 targets an entity A deleted, env3 replayable]; env1 promotes (committed, tip advances); on env2 `reduceAuthoredOperationState` returns `rejectedReduction` (`applied === null`) → rebase aborts, env1 stays committed, the **remaining** overlay (env2 **and** the replayable env3 tail) is dropped in one `drafts` row delete, no partial apply, no stuck/permanently-failing draft, reopen hydrates the committed tip |
| T6b | stagePending survives restart | B stages pending ops, closes tab before promote; reopen under same `clientId` rebuilds `pendingOps` from the durable `drafts` row; a stale promote then rebases from it |
| T7 | Promote idempotency | replay the same `commitId`/digest → returns original receipt, no second `outbox`/`localCommits` row, no double revision advance |
| T8 | Atomic promote | abort/request-error/quota mid-promote leaves prior committed checkpoint + `committedRevision` intact and the staged draft recoverable; `saved` only on `oncomplete` |
| T9 | Authored drain retry (regression) | worker failure with null `getFailure` → `canRetry:true`, `retrySave` re-drains to `saved` |
| T10 | Outbox not re-applied | hydration does not double-apply outbox ops onto the Workbench |
| T11 | History survives new tab | undo stack keyed `[projectId,userId,assetKey]` present under a rotated `clientId`; stale `baseCommitId` quarantined without touching project data |
| T12 | Memory ↔ IndexedDB contract | promote, guard, rebase, idempotency, lazy load identical across both ports |
| T13 | Performance | 4,500-cube active asset promote + hydrate; no main-thread task > 50 ms; inactive asset bytes not read at startup |
| T14 | Migration | opening a v2 DB resets to v3 with no legacy reader |
| T15 | installCommitted split (Phase-4-ready) | a remote committed batch advances `projects`/`assets`/`localCommits` under the guard, does **not** delete this client's other pending drafts and does **not** `outbox.add`; a locally-promoted-but-unacked commit whose base a remote advance moves rebases from the **`outbox`** (draft already deleted), carrying it forward losslessly |
| T15b | Rebase supersedes stale outbox + N receipts | after rebasing N pending commits, querying `outbox` by each superseded original `commitId` (via `byCommit`) returns nothing; exactly N reminted envelopes are drainable and N sequential `localCommits` receipts exist (`R+2 … R+1+N`, none skipped); the sync worker cannot drain both stale and rebased commit for any of the N |

---

## 9. Single riskiest part to implement

`syncForwardRebase` (§4): replaying a behind session's pending operation log —
sourced from `drafts.pendingOps` before local promote, or from the `outbox` for
already-promoted-but-hosted-unacknowledged work — onto the freshly-adopted
committed base through `reduceAuthoredOperationState`, minting **one `commitId` per
rebased envelope** (shared by all its ops, preserving the original commit grouping)
and recomputing `inverseBody` per op, then re-promoting **each envelope in order as
its own atomic revision advance and receipt** (N commits → `R+2 … R+1+N`, no
collapse) while superseding its pre-rebase outbox entry. The reject path uses the
reducer's own `rejectedReduction` sentinel (`reduction.applied === null`), **not**
`validateAuthoredOperation` (schema-only); on any reject it must abort the
**entire** rebase and reload to the committed tip, dropping the whole overlay (no
partial apply, no surviving tail, no stuck draft). Everything else (schema re-key,
committed-first hydration, revision-guarded promote, change-set projection,
`stagePending`) is mechanical; the rebase is the novel correctness-critical seam,
and it is the exact path Phase-4 `installCommitted` reuses (with the deferred
speculative-vs-authoritative reconciliation in §5), so it must be right the first
time. Gated by T5, T6, T6b, T15, and T15b.
