# Cubicell design: local persistence ownership

Agent: `performance-audit:general:6:2.4` (grok)  
Topic: `cubicell-store-design`  
Date: 2026-07-21  
Inputs: STORAGE.md ownership table; PR#106 cutover @ `362d9a3`; scouts `cubicell-scout-clientid-{opus,grok}.md`; codex Major (inactive asset strand after partial hydrate + re-promote).  
Mode: design only (no cubicell checkout writes).

## 0. Problem (category error)

Today one key, `clientId` (sessionStorage, per tab), is used for two roles:

| Role | Correct keying |
|------|----------------|
| Session of one user editing one project | Ephemeral. Owns only **pending** work. |
| Durable local head of a project | Must be **project-owned**, readable by any later session. |

PR#106 fixed the worst symptom (foreign draft drop on hydrate) by reading another client's tip draft. That is a recovery patch, not ownership. Committed project/assets remain under `[projectId, clientId]`. A new client that hydrates only the active asset, then promotes, rewrites only that asset under the new client key and **strands every inactive committed asset** (codex Major at the partial body load path).

This design removes the category error: **nothing durable/committed is keyed by ephemeral clientId**.

## 1. Ownership model (agreed frame, made operational)

| Owner | What | Lifetime |
|-------|------|----------|
| **Project** | Manifest, every asset record, immutable pose revisions, local tip metadata | Durable, shared across all sessions of the same origin/IDB |
| **Client** (`clientId` = per-tab sessionStorage) | Unpromoted working draft, local undo history, outbox rows awaiting hosted ack, failure diagnostics | Private to that session; never the sole home of committed content |
| **User × Project** | Panel layout / active asset preference (`userProjectState`) | Shared across that user's sessions (already client-independent) |

Definitions:

- **Committed (local)** — project tip after a successful local durability transaction. Any later `clientId` must fully recover it without borrowing another client's pending branch.
- **Pending (client)** — work not yet promoted, or promoted-for-local but still in the hosted outbox, or failed promote with retained diagnostics. Other clients must not see or clobber it.
- **Promote** — the missing step: atomic write that moves a validated client snapshot into project-owned committed stores (and optionally retains a client outbox row for hosted sync).

`clientId` remains on operation envelopes (actor session) and on pending rows. It is not part of committed store keys.

## 2. IndexedDB layout and exact keying

DB name: `cubicell.projects` (unchanged).  
Schema version: **bump to 3**. On upgrade: drop all object stores, recreate (zero external users; no legacy reader).

### 2.1 Committed (project-owned)

| Store | keyPath | Value (logical) | Notes |
|-------|---------|-----------------|-------|
| `projects` | `projectId` | `{ projectId, tipCommitId, tipDigest, baseTipCommitId?, bytes }` | Single local head per project. `bytes` = ProjectManifest codec. |
| `assets` | `[projectId, assetId]` | `{ projectId, assetId, tipCommitId, bytes }` | One row per asset. **No clientId.** |
| `poseRevisions` | `[projectId, revisionId]` | `{ projectId, revisionId, bytes }` | Unchanged; immutable add-only. |

Indexes (committed):

- `assets` by `projectId` prefix range for "load all assets for project".
- Optional: `projects` needs no secondary index.

### 2.2 Pending (client-owned)

| Store | keyPath | Value (logical) | Notes |
|-------|---------|-----------------|-------|
| `drafts` | `[projectId, clientId]` | `{ projectId, clientId, baseTipCommitId, commitId?, workingBytes, failure? }` | **One working row per client branch.** Overwrites in place. Failure embeds on same row (or sibling field), never on committed asset rows. |
| `history` | `[projectId, userId, assetKey, clientId]` | history bytes | Local undo; private. Unchanged key shape. |
| `outbox` | autoIncrement `sequence` | `{ sequence, projectId, clientId, commitId, digest, kind, bytes }` | Hosted-sync bag + local promote journal. Still client-keyed. |

Indexes (outbox, keep shape, change semantics of readers):

- `byCommit`: `[projectId, clientId, commitId]` unique
- `byBranchSequence`: `[projectId, clientId, sequence]` unique
- `byProjectSequence`: `[projectId, sequence]` unique — **diagnostics / Phase-4 only**, not hydration source of truth for committed tip

### 2.3 Shared workspace (already correct)

| Store | keyPath |
|-------|---------|
| `userProjectState` | `[projectId, userId]` |

### 2.4 Explicit non-keys

- Committed `projects` / `assets` **must not** include `clientId` in keyPath or as a required identity field for lookup.
- Hydration **must not** select a "source client" to find the project head.
- Foreign `drafts` / `outbox` / `history` / failure are never read except by matching `clientId`.

### 2.5 Key path cheat sheet

```text
COMMITTED
  projects.get(projectId)
  assets.get([projectId, assetId])
  assets.getAll(IDBKeyRange.bound([projectId], [projectId, []]))
  poseRevisions.get([projectId, revisionId])

PENDING (this client only)
  drafts.get([projectId, clientId])
  history.get([projectId, userId, assetKey, clientId])
  outbox index byBranchSequence for (projectId, clientId)
  failure: drafts row.failure | in-memory queue restore from that row

WORKSPACE
  userProjectState.get([projectId, userId])
```

## 3. Promote-to-committed (the missing step)

### 3.1 When

Every successful local durability unit for kind `authored` or `checkpoint` ends in **one** IndexedDB readwrite transaction that:

1. Validates CAS against the current project tip.
2. Promotes project-owned records.
3. Writes this client's pending bookkeeping (draft reset, outbox append, history, clear failure).

In-memory optimistic apply still happens first (Zustand). Promote is the durability unit, not a second async "sync".

### 3.2 Inputs to promote

From existing projection (`projectWorkbenchRecords` / prepare path), plus tip CAS:

```ts
type LocalPromote = {
  projectId: string
  clientId: string
  userId: string
  commitId: string           // new tip commit id
  expectedTipCommitId: string | null  // null only for first local create
  digest: string
  project: StoredProject     // full manifest roster
  assets: StoredAsset[]      // FULL roster materialization (see §3.4)
  poseRevisions: StoredPose[] // new or referenced; add-only
  history: StoredHistory
  outboxPayload: OutboxBytes // hosted-sync envelope for this commit
  draftClear: true           // after promote, pending working matches tip
}
```

### 3.3 Atomic transaction steps

```text
open TX (projects, assets, poseRevisions, drafts, history, outbox, userProjectState)

1. CAS
   current = projects.get(projectId)
   if (expectedTipCommitId === null) assert current === undefined
   else assert current.tipCommitId === expectedTipCommitId
   on mismatch -> abort TX, raise PromoteConflict (not silent overwrite)

2. PROJECT TIP
   projects.put({ projectId, tipCommitId: commitId, tipDigest: digest, bytes: project })

3. ASSETS (merge-put, never orphan)
   for each asset in promote.assets:
     assets.put({ projectId, assetId, tipCommitId: commitId, bytes })
   for each assetId listed in manifest as removed since expected tip:
     assets.delete([projectId, assetId])   // only explicit removals
   // NEVER delete assets merely because they were absent from a partial library

4. POSES
   for each new pose revision: poseRevisions.add (immutable; ignore duplicate same bytes)

5. CLIENT PENDING
   drafts.put({
     projectId, clientId,
     baseTipCommitId: commitId,
     commitId: null,           // no unpromoted working commit
     workingBytes: tipWorkingSnapshot optional cache OR omit
     failure: undefined
   })
   history.put(client history for active asset)
   outbox.add({ projectId, clientId, commitId, digest, kind, bytes })

6. oncomplete -> receipt { projectId, clientId, commitId, outboxSequence }
```

Failed promote: do not touch committed stores. Best-effort write `drafts.failure` with `commitBytes` for retry (same as today's failure draft role, but only on the client draft row). Preceding tip remains intact.

### 3.4 Full roster rule (kills codex Major)

Projection today skips assets missing from the in-memory library (`projectWorkbenchRecords` continues if `findStructureAsset` fails). That is only safe if the library always contains the full committed roster.

**Rule:** before promote, the durability coordinator must ensure `state.workbench.library` contains every asset in `state.project.assets`. If any are missing, load them from committed `assets` (lazy fill) and only then project. Promote payload **must** include one record per manifest asset (or explicit tombstones). Partial library promote is a hard error in dev and a blocked save in prod.

This pairs with hydration (§4): first hydrate loads **all** committed assets (or loads manifest + schedules full roster fill before first promote).

### 3.5 What promote is not

- Not "copy from sourceClientId draft into reader".
- Not last-writer-wins across tabs without CAS.
- Not hosted ack. Outbox row remains until Phase-2+ hosted RPC acknowledges.

## 4. Hydration algorithm

Order is mandatory. No `issueSourceRequests` / source client inheritance.

```text
hydrate(address = { projectId, clientId, userId }):

A. COMMITTED BASE
   project = projects.get(projectId)
   if !project -> empty/new project path (userProjectState only) ; return

   // Full roster (fixes :470 Major)
   assetRows = assets.getAll(projectId range)
   // OR: for each id in project.manifest.assets: assets.get([projectId, id])
   // Prefer getAll-or-by-ids that yields EVERY roster member; missing row = reject/repair signal

   poses = load poseRevisions referenced by loaded structures
   working0 = rebuild workbench from project + ALL assets + poses
            (active asset from userProjectState or first structure;
             inactive assets live in library even if not on canvas)

B. THIS CLIENT PENDING OVERLAY
   draft = drafts.get([projectId, clientId])
   if draft?.failure -> restore failure into branch queue; saveState=failed canRetry
   if draft has unpromoted working (commitId != null or working ahead of tip):
     working = decode draft working (validate draft.clientId === address.clientId)
   else:
     working = working0

   history = history.get([projectId, userId, activeAssetKey, clientId]) // may be empty
   outbox  = outbox byBranchSequence (projectId, clientId) only
             // decode into state.outbox for hosted drain; DO NOT re-apply onto workbench
             // (ops already in committed tip after promote)

C. WORKSPACE
   userProjectState = userProjectState.get([projectId, userId])

D. PUBLISH
   Zustand: project, library(all assets), workbench(working), history, outbox, saveState
   expectedTipCommitId in coordinator memory = project.tipCommitId
```

### 4.1 Fresh clientId reopen (original Blocker)

New tab → new `clientId` → no draft row → working = committed base. **Exact recovery of all committed assets and tip**, default Workbench only when project missing.

### 4.2 Lazy per-asset load

Allowed for **UI** after first paint only if:

1. Initial hydrate still has full **manifest** + active asset body + enough to not promote partial, and
2. Before any promote, coordinator runs `ensureFullRoster()` from committed `assets`.

Safer V1: load all asset rows in the hydrate transaction (projects are small). Defer true lazy streaming to a later size optimization with the same roster invariant.

### 4.3 Paths removed

- `issueSourceRequests` preferring exact client project else latest outbox client
- `readableOutbox(source, reader)` as committed recovery mechanism
- `sourceClientId` on hydration bytes as a stand-in for project ownership
- Dual validation of draft against source client for "inherit committed"

## 5. Multi-tab pending isolation

| Concern | Behavior |
|---------|----------|
| Distinct `clientId` per tab | Unchanged (sessionStorage). |
| Pending draft | Keyed `[projectId, clientId]`; tab B never reads tab A's draft. |
| Outbox / failure | Same. `getFailure({ projectId, clientId })` branch-scoped (already landed in PR#106 fix; keep). |
| Committed tip | Shared. Both tabs hydrate the same project/assets. |
| Clobber | Tab A cannot `drafts.put` tab B's key. IDB key isolation is the guarantee. |
| In-memory durability queues | One queue map entry per `(projectId, clientId)` (existing `ProjectCommitQueues`). |

Isolation test matrix (keep and extend):

- A fails promote → B hydrates committed tip, empty pending, can edit.
- A has unpromoted draft only in memory → B unaffected.
- A and B both open → each has private draft; shared tip advances only on successful promote CAS.

## 6. V1 one-active-writer-per-asset boundary

STORAGE.md: one intended writer per asset; silent last-writer-wins is prohibited; losing tab keeps local branch.

### 6.1 Exact local behavior (this design)

Two concurrent clients start from tip `T0`.

1. Client A promotes commit `Ca` with `expectedTipCommitId = T0` → tip becomes `Ca`. Committed stores update. A's outbox has `Ca`.
2. Client B still has optimistic state from `T0` + its edits. B attempts promote `Cb` with `expectedTipCommitId = T0`.
3. CAS fails (`current.tipCommitId === Ca ≠ T0`).
4. **Do not** write committed stores. **Do not** drop B's pending draft.
5. Surface `saveState = failed` with `PromoteConflict` / conflict name, `canRetry` policy:
   - **Not** auto-overwrite tip.
   - B keeps pending draft + outbox empty of `Cb` (failed unit retained for diagnostics).
   - UI: block further promotes until user acknowledges; V1 resolution = reload from committed tip (discard pending) **or** keep pending offline until Phase-4 OT/rebase (explicit user choice later). Default V1: **preserve pending draft, block promote, show conflict**; user can "Revert to saved" (delete draft, rehydrate tip) or "Retry after reload" once product adds merge.

### 6.2 What never happens

- Silent `projects.put` / `assets.put` that buries the other tab's already-committed tip.
- Deleting committed assets because the losing tab's library was partial.
- Adopting the other tab's pending draft as committed.

### 6.3 Same tip parallel creates of different new assets

If V1 is strictly one writer per **project** locally: CAS on project tip serializes all promotes (simple, correct). That is the chosen default: **one local tip CAS for the whole project**, which implies one successful local promoter at a time even across assets. Finer per-asset CAS is a Phase-4 refinement when hosted revisions exist per asset.

## 7. Phase-4 / hosted forward-compatibility (strict subset)

| Local (this design) | Hosted Phase-2+ | Live Phase-4 |
|---------------------|-----------------|--------------|
| `projects` / `assets` / `poseRevisions` | Mirror of Postgres project/asset/revision rows | Same stores; apply remote commits into committed keys |
| `outbox` client-keyed | Drain oldest pending via commit RPC; ack removes row | Unchanged client private until ack |
| `drafts` client-keyed | Still private unpromoted / conflict branch | Presence stays memory; drafts stay private |
| Tip CAS `expectedTipCommitId` | Maps to `observedRevision` / asset `committed_revision` checks | Remote tip advance is the CAS input |
| Conflict surface | Hosted conflict flow (keep local branch) | Same; Realtime batch is another tip advance source |

Nothing to rip out: PR#106's "read foreign draft as tip" goes away because tip is not foreign. `clientId` on operations remains for actor attribution. Realtime slots in as: receive committed batch → apply to committed stores (same put rules) → if local draft.baseTipCommitId behind, mark conflict without deleting draft.

## 8. Migration

- Zero external users; pre-release rule in STORAGE.md applies.
- `indexedDbProjectStorageVersion`: 2 → **3**.
- `onupgradeneeded`: delete every object store; `createIndexedDbProjectSchema` with new keyPaths.
- No dual-read, no promote-from-legacy-client-keys, no background migrator.
- Optional: if version 2 data present, wipe is enough; user loses local-only drafts (acceptable).
- Memory storage twin updates to the same key model in the same PR.
- Preference `clientId` generation unchanged.

## 9. Blast radius (slices 1–4) and test matrix

### 9.1 Code that changes

| Area | Change |
|------|--------|
| `indexedDbSchema.ts` | Version 3; projects/assets keyPaths drop clientId; drafts keyPath `[projectId, clientId]` |
| `storageRecords.ts` / prepare | Committed records without clientId; CAS fields; remove sourceClientId draft inheritance helpers (`readableOutbox` as commit-recovery dies or shrinks to client-only filter) |
| `indexedDbProjectStorage.ts` | Promote TX; hydrate without source client; full asset load; loadAsset by project keys |
| `indexedDbHydrationBytes.ts` | Physical validators use project keys; drop address.clientId draft equality for committed bytes |
| `indexedDbFailureState.ts` | Failure only on client draft row; restore scoped by client |
| `memoryProjectStorage.ts` | Twin of above |
| `projectRecordHydration.ts` | Hydrate from committed roster first; draft overlay only if `draft.clientId === seed.clientId` |
| `projectDurability.ts` | Track `expectedTipCommitId`; `ensureFullRoster` before project; conflict saveState |
| `projectCommitProjection` / workbench records | Fail promote if roster incomplete |
| `storagePort.ts` | Receipt/failure types; optional `getTip`; `getFailure(branch)` stays |
| Tests | Contract, persistence, Chromium drivers, failure isolation |
| `STORAGE.md` | Align "local head is project-owned" language with this model |
| Remove | PR#106 inherit hacks that treat source client tip draft as shared committed |

Out of scope for the ownership PR (unless cheap): hosted RPC, Realtime, OT merge UI beyond conflict flag.

### 9.2 Test matrix (proof)

| # | Gate | Assertion |
|---|------|-----------|
| T1 | Fresh clientId after promote | New sessionStorage client recovers tip + **all** assets exact (digest of project+library+workbench); outboxDepth 0 for new client |
| T2 | Inactive asset survival | Project with assets A,B; edit A; promote; new client; switch to B; B body intact; promote again; A still loadable |
| T3 | Partial library blocked | Library missing B; promote throws/blocks; committed tip unchanged |
| T4 | Multi-tab pending | A fails promote; B hydrates tip, cannot see A's failure draft; B can promote |
| T5 | Dual promote CAS | A promotes; B promote with stale expectedTip → conflict; tip remains A's; B draft preserved |
| T6 | No silent LWW | After T5, committed assets equal A's promote payload |
| T7 | Authored drain retry | getFailure null path still canRetry; re-drain; reopen saved |
| T8 | Outbox not re-applied | Hydrate does not double-apply outbox onto workbench |
| T9 | History private | A's undo stack not visible to B |
| T10 | userProjectState shared | Panel layout survives clientId rotation |
| T11 | Memory port contract | Same as IDB for T1–T6 |
| T12 | Real Chromium | T1, T2, T4, T5, T7 in browser project |
| T13 | Schema wipe | Opening v3 DB does not read v2 key shapes |

### 9.3 Risks

| Risk | Mitigation |
|------|------------|
| Large projects: full asset hydrate cost | Accept in V1; roster ensure is correctness gate; optimize later with same keys |
| Draft key shape change loses multi-commit draft history | One row per client is enough; failure embeds commitBytes for single active failure |
| Callers still pass clientId into asset gets | Grep/port type: `loadAsset(projectId, assetId)` no client |
| Projection silently skips missing library assets | Hard error before TX |
| Two tabs thrash CAS | Expected V1; conflict UI; no data loss |

## 10. Implementation order (buildable PR slice)

1. Schema v3 + memory twin key model (compile green).
2. Promote TX with CAS + full roster assert; stop writing client-keyed projects/assets.
3. Hydrate: committed first, client draft overlay; delete source-client inheritance.
4. Durability: `expectedTipCommitId` + ensureFullRoster.
5. Tests T1–T13; delete obsolete "foreign draft as committed" contract expectations; replace with project-tip expectations.
6. STORAGE.md wording pass.
7. Peer consensus then land.

## 11. Core decision (one line)

**Committed local head lives under project keys with tip CAS promote; clientId keys only drafts/outbox/history/failure — full asset roster is mandatory on hydrate and promote so multi-session recovery never strands inactive assets.**

## 12. Mapping from current PR#106 state

| PR#106 / 362d9a3 | This design |
|------------------|-------------|
| projects `[projectId, clientId]` | projects `projectId` |
| assets `[projectId, clientId, assetId]` | assets `[projectId, assetId]` |
| Load source tip draft for foreign reader | Load project tip; ignore foreign drafts |
| `readableOutbox` empty for foreign | Outbox never consulted for committed working state |
| Partial active-asset hydrate | Full roster hydrate + promote assert |
| Tip discovery via outbox project sequence | Tip = `projects.tipCommitId` |
| canRetry / branch getFailure | Keep |

End of design.
