# Design: cubicell local persistence ownership model

Independent design round. Baseline `docs/performance-audit` + PR#106 `feat/persist-cutover` @ `362d9a3`. Read-only; this file is the deliverable. Line refs are `git show 362d9a3:<file>`.

## Core model (one sentence)

The **PROJECT** owns all committed data in client-independent, revision-ordered stores (`projects[projectId]`, `assets[projectId, assetId]`, `poseRevisions[projectId, revisionId]`); a **CLIENT** owns only its pending branch (`drafts[projectId, clientId, assetId]`, `outbox[projectId, clientId, …]`, failure); a **PROMOTE** step atomically moves a landed edit from the client-private draft into the shared committed asset checkpoint under an optimistic revision check.

The single category error across slices 1-4 is that committed bytes are keyed by the ephemeral `clientId`. Hydration then guesses "the latest committer branch" (`issueSourceRequests`) and reads committed data through a client key. PR#106 patched the *read* to tolerate a foreign source branch; this design removes the client key from committed data entirely so no guessing and no per-client copies exist. The hosted Postgres model in STORAGE.md already does exactly this (`assets` keyed `(id, project_id)` with `revision`/`checkpoint_revision`) — the local store is simply brought into line with it.

---

## 1. IndexedDB store layout + exact keying

Bump `indexedDbProjectStorageVersion` 2 → 3.

### Committed — shared, client-independent (read by any session)

| Store | keyPath | Holds | Change from today |
|---|---|---|---|
| `projects` | `['projectId']` | manifest: title, asset roster + order, `revision`, `schemaVersion` | **drop `clientId`** (was `[projectId, clientId]`) |
| `assets` | `['projectId', 'assetId']` | per-asset compact checkpoint document + `committedRevision`, `schemaVersion`; the authoritative recoverable content for **every** asset | **drop `clientId`** (was `[projectId, clientId, assetId]`) — fixes codex :470 |
| `poseRevisions` | `['projectId', 'revisionId']` | immutable pose snapshots | unchanged (already correct) |

`assets.committedRevision` is the local mirror of hosted `assets.checkpoint_revision`. Manifest `revision` mirrors hosted `projects.revision`. These bigints, not `clientId`, order committed state.

### Pending — private, client-keyed (one tab's uncommitted branch)

| Store / index | keyPath | Holds | Change from today |
|---|---|---|---|
| `drafts` | `['projectId', 'clientId', 'assetId']` | THIS client's uncommitted working overlay for an asset (the ops applied optimistically but not yet promoted); at most one row per (client, asset) | **re-keyed** from `[projectId, clientId, commitId]` to `[…, assetId]`; role narrows from "committed snapshot + pending" to pending-only |
| `outbox` (`byCommit`) | idx `['projectId','clientId','commitId']` unique | pending commit idempotency | unchanged |
| `outbox` (`byBranchSequence`) | idx `['projectId','clientId','sequence']` unique | per-branch pending order | unchanged |
| `outbox` (`byProjectSequence`) | idx `['projectId','sequence']` unique | diagnostics / hosted drain order | retained for the hosted outbox; **no longer used to resolve committed reads** |

### Private per user (not per client)

| Store | keyPath | Change |
|---|---|---|
| `history` | `['projectId', 'userId', 'assetKey']` | **drop `clientId`** (STORAGE.md: "Private per user and asset"; the `clientId` dimension silently resets undo/redo on a same-user new tab) |
| `userProjectState` | `['projectId', 'userId']` | unchanged (already client-independent per user) |

Net: `clientId` appears **only** on `drafts`, `outbox`, and failure state. Nothing committed or durable-shared is keyed by the ephemeral session id, satisfying the agreed frame.

---

## 2. PROMOTE-to-committed (the currently missing step)

Today `issueCommitWrites` (:337-352) writes the working snapshot into the client-keyed `drafts` row; "committed" and "pending" are the same physical row distinguished only by an absent `failure` field. Replace it with an explicit promote, one strict IndexedDB transaction over `['projects','assets','poseRevisions','drafts','history','outbox']`:

```
promote(commit):                                # commit carries baseRevision per targeted asset
  for each targeted asset A in commit:
    stored = assets.get([projectId, A.assetId])
    if (stored?.committedRevision ?? 0) !== commit.base[A.assetId]:   # optimistic check
      abort transaction -> STALE (see §5); leave draft + outbox intact
  # revisions match -> apply atomically:
  projects.put(manifest, revision = base+1) if roster/order changed
  for each targeted asset A:
    assets.put({ projectId, assetId: A.assetId,
                 document: A.checkpoint, committedRevision: A.base+1, schemaVersion })
  for each new pose: poseRevisions.add(pose) if absent            # immutable, idempotent
  outbox.add(commitEntry)                                          # journal for hosted drain + idempotency
  history.put([projectId, userId, assetKey], entry)
  drafts.delete([projectId, clientId, A.assetId])                 # the promoted overlay is now committed
  userProjectState.put([projectId, userId], …)
```

Key properties: the committed checkpoint is written to the **client-independent** `assets[projectId, assetId]`, so any later session reads it with no client key; the promoted pending draft is deleted in the same transaction (no stale private overlay survives a successful promote); `outbox` remains the hosted-sync journal, not a committed-read source. This is the local instance of STORAGE.md's hosted commit protocol (steps 5-9): the same revision compare-and-advance, run against IndexedDB instead of Postgres.

Rapid edits still batch: the draft overlay accumulates optimistic ops; promote coalesces to one checkpoint write per asset per drain, preserving operation order via the outbox sequence (STORAGE.md "Rapid actions may batch the snapshot write while preserving operation order").

---

## 3. HYDRATION algorithm

Committed-first, client-independent; pending overlay is this client's only client-scoped read.

```
hydrate(projectId, clientId, userId, activeAssetId):
  # 1. COMMITTED, shared, no client key, no source guessing
  manifest = projects.get([projectId])                            # roster + revision
  if !manifest: return fresh Project (first run)
  activeAsset = assets.get([projectId, activeAssetId])            # committed checkpoint
  poses = poseRevisions for activeAsset's referenced revisions
  history = history.get([projectId, userId, activeAssetKey])
  userState = userProjectState.get([projectId, userId])

  # 2. PENDING overlay, this client only
  draft = drafts.get([projectId, clientId, activeAssetId])        # uncommitted ahead of committed
  pending = outbox entries for [projectId, clientId] not yet promoted

  # 3. compose canvas
  working = draft ? draft.working : checkpointToWorking(activeAsset)   # committed checkpoint is the BASE, not a fallback default
  saveState = failureFor([projectId, clientId]) ?? (pending.length ? 'saving' : 'saved')

  # 4. inactive assets load lazily, still client-independent:
  loadAsset(assetId) = assets.get([projectId, assetId])          # every roster asset reachable
```

This fixes both defects at the source:
- **Original Blocker** (fresh-clientId reopen → default Workbench): `working` derives from the committed `assets`/checkpoint keyed by `[projectId, activeAssetId]`, never from a client-keyed draft, so a new tab recovers the exact committed scene. When no pending draft exists the committed checkpoint *is* the canvas.
- **Codex :470 Major** (fresh client commits active asset, strands inactive committed assets): `assets` is keyed `[projectId, assetId]` with no `clientId`, so `loadAsset` reaches every roster asset regardless of which session last committed it. A commit that touches only the active asset advances only that asset's `committedRevision`; the untouched assets keep their existing committed rows and stay reachable. There is no per-client asset copy to strand.

`issueSourceRequests` and the `sourceClientId` / `readableOutbox` machinery added in PR#106 are removed for committed reads (committed reads no longer resolve a "source branch"); the only client-scoped read left is the pending draft/outbox overlay by `[projectId, clientId]`.

---

## 4. Multi-tab pending isolation

- Pending drafts are keyed `[projectId, clientId, assetId]`; two tabs have disjoint `clientId`, so tab A cannot read or overwrite tab B's uncommitted overlay.
- Pending outbox and failure keyed by `[projectId, clientId, …]` (unchanged, already correct — scout §1 CORRECT rows; `orderedCommitQueue.branchKey` :277 stays `[projectId, clientId]`).
- Committed stores are shared but **write-once-per-promote under a revision guard** (§2): the only writer path is promote, which compare-and-swaps `committedRevision`. Two tabs reading the same committed checkpoint is intended and safe; two tabs *promoting* is arbitrated by §5, never by clobber.

No path lets one tab's pending work leak into another: committed reads carry no pending (the draft delete in promote guarantees a committed checkpoint never contains another client's un-promoted overlay), and pending reads are client-keyed.

---

## 5. V1 one-active-writer-per-asset divergence boundary

The accepted V1 limitation is one active writer per asset. Divergence must **never silently lose committed data** (STORAGE.md: "Silent last writer wins is prohibited").

Mechanism: every commit carries `base[assetId] = committedRevision observed at hydration / last promote`. The promote transaction (§2) re-reads the current `committedRevision` inside the transaction and rejects if it moved:

- **Concurrent divergence** (A and B both hydrate rev N, A promotes → N+1, B promotes with base N): B's promote sees N+1 ≠ N → **abort, do not overwrite**. B keeps its pending draft + outbox intact; `saveState` becomes a `conflict` variant carrying `{ assetId, expected: N, actual: N+1 }`. A's committed N+1 is untouched.
- **Recovery from conflict**: B stops that asset's drain, re-reads the committed checkpoint at N+1, replays its pending semantic operations against it through the same deterministic reducer (STORAGE.md §Conflict behavior 3-5); commits the rebased result when every op remains valid, else preserves B's recovered branch and surfaces the choice. Local-only for V1; identical shape to the hosted stale-writer flow.

This upgrades today's silent behavior. Currently the "latest projectSequence branch wins" heuristic means a lower-sequence branch's committed edits are dropped on next open with no signal. Revision-guarded promote converts that into an explicit, non-destructive conflict.

Add a `LocalSaveState` `conflict` arm alongside `saving | saved | failed` (parallels the union at `cubicellState.ts:112`); `retrySave` on a conflict triggers rebase-replay, not a blind re-drain.

---

## 6. Phase-4 forward-compatibility (strict subset, nothing rip-out)

The local layout is a projection of the hosted model already specified in STORAGE.md, so hosted sync is additive:

| Local (this design) | Hosted (STORAGE.md, already specified) | Relationship |
|---|---|---|
| `assets[projectId, assetId]` + `committedRevision` | `assets(id, project_id)` + `revision`/`checkpoint_revision` | same key, same revision semantics |
| `promote()` revision compare-and-advance | commit RPC steps 5-9 | same optimistic protocol, IndexedDB vs Postgres |
| `outbox[projectId, clientId]` journal | `project_commits`/`commit_operations` + sync worker | outbox drains into the RPC unchanged |
| §5 local conflict rebase-replay | §Conflict behavior stale-revision rebase | same reducer, same flow |

Realtime/hosted slots in at two seams with no committed-store change: (a) the sync worker drains `outbox` to the commit RPC (STORAGE.md §Synchronization); (b) a **remote committed batch enters the same `promote()` path** — advance `assets[projectId, assetId]` checkpoint + `committedRevision` via the shared reducer (STORAGE.md live path 1-3). Because committed reads are already client-independent and revision-ordered, adding a second writer (the server) requires no new read path and no re-keying. Presence stays memory-only, never touching these stores.

---

## 7. Migration

Zero external users. Per STORAGE.md §Durable identity ("during pre release development, an incompatible shape can reset local data rather than introduce legacy readers or parallel migration paths") and the project's standing "no migrations, single user" rule: bump `indexedDbProjectStorageVersion` 2 → 3. `createIndexedDbProjectSchema` already `deleteObjectStore`s every store and recreates (`indexedDbSchema.ts:19-21`), so the upgrade path is a clean local reset. No legacy reader, no dual-write, no data-loss flag. The one-time `cubicell.workbench` localStorage clear (`preferencePort.ts:32`) is unaffected.

---

## 8. Blast radius + test matrix

### Code that changes (slices 1-4)

| File | Change |
|---|---|
| `indexedDbSchema.ts` | version 3; `projects` `[projectId]`; `assets` `[projectId, assetId]`; `drafts` `[projectId, clientId, assetId]`; `history` `[projectId, userId, assetKey]`; add `committedRevision` to asset records |
| `indexedDbProjectStorage.ts` | delete `issueSourceRequests` committed-read guessing; committed reads hit `projects[projectId]`/`assets[projectId, assetId]` directly; `issueCommitWrites` → `promote()` with in-transaction revision guard + draft delete; `loadAsset` reads `[projectId, assetId]`; `getFailure(branch)` unchanged (already branch-scoped in `362d9a3`) |
| `storageRecords.ts` | committed records validate by `projectId`/`assetId`/`committedRevision` not `clientId`; drop `sourceClientId`/`readableOutbox` for committed reads; draft (pending) still validated by `clientId`; `activeAssetId` from committed manifest |
| `indexedDbHydrationBytes.ts` | emit committed bytes (no client key) + optional pending overlay bytes; drop `sourceClientId` field |
| `projectRecordHydration.ts` | `resolveWorking` overlays pending draft on the committed checkpoint base; committed checkpoint replaces the detached-default fallback (:339-367) |
| `projectDurability.ts` | promote wiring; add `conflict` save state + rebase-replay in `retry`; `canRetry` already fixed in `362d9a3` |
| `memoryProjectStorage.ts` | mirror the layout (test parity twin) |
| `orderedCommitQueue.ts` | commit carries `base[assetId]`; branch queue key unchanged |
| `preferencePort.ts`, `userProjectState`, `poseRevisions` | unchanged |

`indexedDbProjectStorage.ts` is 674 LOC today; deleting the source-resolution machinery should net negative, staying under 700.

### Test matrix (proves the model)

1. **Fresh-clientId reopen recovers committed work exactly** — seed commit under client A; reopen under a rotated clientId; `committedDigest === recoveredDigest`, `outbox.length === 0`. (Already present at `362d9a3` `runNewClientCommittedRecovery`; keep.)
2. **All committed assets reachable after fresh-client active-only commit (codex :470)** — seed 3 assets under A; reopen under B; edit+promote only the active asset; reopen under C; `loadAsset` each of the 3 → present, correct revision. **NEW, pins the Major.**
3. **Two-tab pending isolation** — A holds an uncommitted draft on asset X; B hydrates → sees committed X only, never A's overlay; B promoting X does not touch A's `drafts`/`outbox`. (Extend `runForeignPendingIsolation`.)
4. **Divergence blocks, never loses committed** — A and B hydrate rev N; A promotes → N+1; B promotes base N → `conflict{expected:N,actual:N+1}`, B's branch preserved, A's committed data intact; B rebase-replay → N+2 with both edits. **NEW, pins §5.**
5. **Promote atomicity** — quota/abort fault mid-promote leaves the prior committed checkpoint + `committedRevision` intact and reports `failed` (existing quota-rollback pattern extended to the new layout).
6. **Retry after authored drain failure with null getFailure** — `canRetry:true`, `retrySave` re-drains to `saved`. (Already present; keep.)
7. **Undo history survives same-user new tab** — history keyed `[projectId, userId, assetKey]`; A builds undo stack; B (same user, new client) hydrates → stack present. **NEW, pins the history re-key.**
8. **Perf gate** — 4,500-cube active asset checkpoint promote + hydrate, no main-thread task > 50 ms (segmentedJson/taskYield path unchanged).

All in real Chromium via the existing `cubicellStore.browser.test.ts` driver harness; unit twins in `cubicellStorePersistence.test.ts` + `projectStorageContract.ts` (the contract already asserts committed-shared/pending-private at `362d9a3` and extends cleanly).

---

## Biggest design decision / tradeoff

Make the per-asset committed checkpoint (`assets[projectId, assetId]` + `committedRevision`) the single authoritative committed store and demote `drafts` to a pure client-private pending overlay, **replacing the "latest-committer branch" source heuristic with revision-ordered committed reads and a revision-guarded promote**. The tradeoff: the working snapshot stops being a per-commit-immutable client artifact — each promote overwrites the shared checkpoint (last-committed-per-asset wins) — so cross-session recovery is resolved by asset revision rather than by preserving every client's branch snapshot. That is precisely the V1 one-writer-per-asset boundary, and §5 converts its failure mode from today's silent lower-sequence loss into an explicit, non-destructive local conflict that the same reducer rebases.
