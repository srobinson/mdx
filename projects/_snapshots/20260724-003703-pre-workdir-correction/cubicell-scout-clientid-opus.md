# Scout: clientId / committed-vs-pending model (cubicell)

Scope: merged slices 1-4 on `docs/performance-audit` + PR#106 `feat/persist-cutover` @ `4c7fff3`. Read-only design audit. All line numbers are `git show origin/feat/persist-cutover:<file>`.

## TL;DR

**Root cause (Blocker):** there is no client-independent committed project store. The authoritative committed working scene is persisted only in the client-keyed `drafts` row, and hydration is doubly locked to the reader's clientId — it *drops* a foreign branch's draft (`indexedDbProjectStorage.ts:495`) and, even if loaded, *rejects* it because `draftValue` validates the draft against `address.clientId` instead of the source branch (`storageRecords.ts:164` + `:501-504`). clientId is `sessionStorage`-scoped (`preferencePort` `readClientId`), so every new tab / browser restart gets a new clientId, resolves the old branch as source, then discards its working snapshot and rebuilds the default Workbench via `resolveWorking`'s fallback (`projectRecordHydration.ts:345-367`). Committed edits vanish.

**Minimal fix:** make the committed working snapshot read client-independently — (a) at `indexedDbProjectStorage.ts:495` always load `drafts.get([projectId, sourceClientId, latest.commitId])` when a committed `latest` exists (drop the `sourceClientId !== address.clientId` term, keep the `!latest` guard); (b) pass `sourceClientId` (not `address.clientId`) into `draftValue` and validate the draft's identity against the source branch. Keying strictly by the *latest committed* commitId keeps a foreign client's uncommitted/failed-ahead draft private, so multi-tab pending isolation is preserved. This is a strict subset of the Phase-2 direction (relocate the committed snapshot to a client-independent store), so nothing here is rip-out.

---

## 1. Reuse Map — every clientId keying/branching site, classified

Legend: **CORRECT** = keys pending/unsynced/private work · **BUG** = client-keys committed/shared data or drops committed data on clientId change · **SUSPECT** = private but over-keyed.

### Schema — `indexedDbSchema.ts`
| Store / index | Key | Class | Note |
|---|---|---|---|
| `projects` | `[projectId, clientId]` :23 | **BUG** | STORAGE.md ownership table marks *Project metadata → Shared*; stored per-client. Faked shared at read via source fallback. |
| `assets` | `[projectId, clientId, assetId]` :26 | **BUG** | *Authored asset → Shared*; stored per-client. |
| `poseRevisions` | `[projectId, revisionId]` :29 | CORRECT | Client-independent, "Shared by reference". |
| `drafts` | `[projectId, clientId, commitId]` :32 | **BUG (role-conflated)** | Holds BOTH the committed working snapshot AND uncommitted/failed pending drafts. Committed snapshot must be shared; pending must be private. One store, two lifecycles. |
| `history` | `[projectId, userId, assetKey, clientId]` :35 | SUSPECT | STORAGE.md: *Local history → Private per user and asset*. The `clientId` dimension over-keys it, so a same-user new tab silently loses undo/redo. |
| `outbox` byCommit/byBranchSequence | `[projectId, clientId, …]` :43,48 | CORRECT | Pending commit identity / per-branch ordering. |
| `outbox` byProjectSequence | `[projectId, sequence]` :53 | CORRECT | Client-independent project-wide ordering; the one lever that lets source resolution find another client's branch. |

### Read path — `indexedDbProjectStorage.ts`
- `issueSourceRequests` :454-471 — source = exact `projects[projectId, myClientId]` else `latest` project-wide committer via byProjectSequence. **CORRECT** mechanism (client-independent fallback).
- `issueProjectHeaderRequests:495` `if (sourceClientId !== address.clientId || !latest) → { draft: undefined }`. **BUG** — discards the committed working snapshot for any foreign source branch.
- `rawProjectHeader` call → `draftValue(stored.draft, projectId, address.clientId, …)` (`storageRecords.ts:164`). **BUG** — the draft is the only record validated against the *reader's* clientId; `projectValue`/`assetValue`/`historyValue` correctly use `sourceClientId`.
- Write side :343 `draftStore.delete(draftBranchRange(projectId, commit.clientId)); draft.put`, :152/:221/:225 outbox/draft keyed by `commit.clientId`. **CORRECT** (writing my own branch).
- `loadAsset`/`issueAssetRequests` use `source.clientId` :444,606,610. **CORRECT** (assets survive cross-client).

### `storageRecords.ts`
- `draftValue` :493-507 requires `stored.clientId === clientId` and `decoded.value.clientId === clientId`; caller passes `address.clientId`. **BUG** (should be `sourceClientId`).
- `projectValue`/`assetValue`/`historyValue` :480-595 validate against the passed `clientId` = `sourceClientId`. **CORRECT**.
- `validateSnapshotOwnership` :430-456 asserts `snapshot.draft.clientId === head.clientId` and `decodedDraft.value.clientId === address.clientId` on write. **CORRECT** for write; cements the draft-is-mine assumption that the read path then can't undo.
- `storageReceipt` :204 / `storageFailure` :216 carry `commit.clientId`. **CORRECT** (receipt/pending identity).

### `projectDurability.ts`
- `createUserProjectStateUnit` :258, commit projection :305 use `address.clientId`. **CORRECT** (the acting client). `canRetry` at :147 is a separate defect — §4.

### `orderedCommitQueue.ts`
- `branchKey` :277 `[projectId, clientId]`. **CORRECT** — per-branch pending queue isolation is exactly clientId's live V1 job.

### `indexedDbFailureState.ts`
- Every clientId use (:54,79,127-129,140,157,169,189,206) keys drafts/outbox/failure by branch. **CORRECT** (pending/failure private).

### `cubicellStore.ts`
- :62/:65 `clientId: loaded.clientId` (from `sessionStorage` via `preferencePort`) into `address`. Consumption **CORRECT**, but this is the *trigger*: session-scoped clientId ⇒ new tab = new branch. Committed hydration must not depend on it.

### `storagePort.ts`
- clientId fields on `ProjectStorageAddress`/`Branch`/`Receipt`/`Failure`/`Checkpoint` (:7,20,32,38,46,50,59). **CORRECT** vocabulary. `ProjectStorageBranch = Pick<'clientId'|'projectId'>` is used only for pending/failure clearing — appropriate.

---

## 2. Committed-vs-pending boundary

**Authoritative COMMITTED local state any client must load:** project manifest (`projects`), authored assets (`assets`), immutable pose revisions (`poseRevisions`), the committed **working snapshot** (currently the `drafts` row at the latest committed `commitId`), local history (per user+asset), userProjectState (per user). Of these, manifest/assets/poses/userProjectState already resolve client-independently (source fallback + shared keys). The committed **working snapshot is the only committed datum trapped behind client-private storage** — and `resolveWorking` depends on it (`projectRecordHydration.ts:345`: `if (draft) return draft.working/workingPose`), so losing it resets the canvas to poster/detached-default.

**Is there a promote-to-committed step? No.** Each accepted commit writes the working snapshot straight into the client-keyed `drafts` store, atomically with the outbox add and the manifest/asset puts (`issueCommitWrites` :337-352). There is no separate committed-snapshot record; "committed" and "draft/pending" share one physical row distinguished only implicitly (commitId ∈ outbox, and absence of a `failure` field). **That conflation is the root cause** — committed work is left in a client-keyed draft, and the read path treats all drafts as private.

---

## 3. Minimal, collaboration-forward fix

**Immediate (no schema change, unblocks data loss):**
1. `indexedDbProjectStorage.ts` `issueProjectHeaderRequests` — replace the `sourceClientId !== address.clientId || !latest` guard with just `!latest`; always issue `drafts.get([projectId, sourceClientId, latest.commitId])` and return its result as `draft`.
2. `storageRecords.ts` `rawProjectHeader` — pass `sourceClientId` to `draftValue` (add a `sourceClientId` param threaded from the caller); `draftValue` validates `stored.clientId === sourceClientId` and `decoded.value.clientId === sourceClientId`. The draft's identity is the *source branch*, not the reader.

Why this preserves multi-tab pending isolation: selection is keyed strictly to the **latest committed** `commitId` (the outbox head for that branch). A foreign client's uncommitted-ahead draft has a different commitId (or bears a `failure` field) and is never selected, so private in-flight work still cannot leak or clobber. Only the shared committed snapshot becomes readable.

**Phase-2 durable end-state (schedule with Supabase schema, do NOT ship now):** stop client-keying committed data. Committed manifest/assets/working-snapshot move to client-independent stores (`projects[projectId]`, `assets[projectId, assetId]`, a `committedSnapshot[projectId]` head); `clientId` keys ONLY `drafts`(uncommitted)/`outbox`/failure. Hydration then reads committed state by `projectId` with no latest-committer guessing, and hosted stale-writer detection compares the committing clientId + revision against the shared committed head. **The minimal fix is a strict subset of this contract** ("committed state is client-independent to readers"); Phase 2 relocates the bytes but keeps the same read contract, so nothing built now is ripped out. The V1 `latest-committer-wins` source heuristic is acceptable under STORAGE.md's "one active writer per asset" and is the piece Phase 2 replaces.

---

## 4. The `canRetry` Major (`projectDurability.ts:147`) — independent root

`drain`'s failure branch sets `errorSaveState(error, unit.commitId, unit.kind === 'user-project-state')`, i.e. `canRetry = (unit.kind === 'user-project-state')`. So an **authored** drain failure gets `canRetry = false` whenever `storage.getFailure()` is null — the case where the throw came from projection/worker (`projectStorageCommitAsync`) *before* `storage.commit`, i.e. a transient, genuinely retryable error. `retry()` gates on `current.canRetry` (:166-168), so the user is left in a permanent blocked state with no retry, forcing a reload.

**Root: independent** — this is a retry-eligibility inversion (retry policy), not committed-vs-pending. But it **chains** into the Blocker: a non-retryable authored failure forces a reload, and the reload under a fresh tab/clientId then triggers §1 committed-work loss. Fix: authored drain failures must be retryable (`canRetry = true`) so `retry()`'s `!retriesStorage` branch re-drives `drain` (re-project + re-commit); the explicit `unit.kind === 'user-project-state'` third arg is the defect (the default `commitId !== null` already yields `true` for authored). Reserve `canRetry=false` only for truly terminal cases.

---

## 5. Coverage gaps (P0 tests reuse one clientId)

Missing regressions:
1. **New-clientId reopen recovers committed work** — seed ≥1 authored commit under clientId A; reopen storage + hydrate under clientId B (distinct sessionStorage clientId); assert `workbench.working` equals the committed scene (not the `resolveWorking` default) and manifest/assets present. Directly pins the Blocker.
2. **Two-tab pending isolation** — clientId A holds an uncommitted/failed draft ahead of its outbox; B's hydration surfaces only A's latest *committed* snapshot, never A's uncommitted draft; B committing does not clobber A's branch/outbox/failure.
3. **Retry after authored drain failure** — force a projection/worker (non-storage) failure on an authored commit so `storage.getFailure()` is null; assert `saveState.canRetry === true` and `retrySave()` re-drives drain to `saved`. Fails today.
4. *(bonus)* **Undo history survives same-user new tab** — pins the `history` over-keying (§6); optional for V1.

---

## 6. Quality / dead-code / cross-slice inconsistency

- **Schema ⟂ doc:** `projects`/`assets` are client-keyed though STORAGE.md's ownership table marks them Shared; client-independence is *simulated* at read time by source fallback rather than expressed in the schema.
- **Draft role conflation:** `drafts` holds committed snapshot + uncommitted/failed pending, distinguished only implicitly. This is the structural seam the fix should eventually cut.
- **Asymmetric validation:** `rawProjectHeader` threads `sourceClientId` to project/asset/history but `address.clientId` to `draftValue` (`storageRecords.ts:164`) — the direct reason the draft alone can't be read cross-client. Inconsistent and load-bearing.
- **`history` over-keying:** `[projectId, userId, assetKey, clientId]` contradicts "Private per user and asset"; silently resets undo/redo on a new tab.
- **Redundant read:** `issueProjectHeaderRequests` re-issues `projects.get([projectId, sourceClientId])` though `issueSourceRequests` already fetched `projects.get([projectId, address.clientId])`; when `source === mine` this is a duplicate get (minor inefficiency, not a bug).
- **Cross-slice:** slice 3 built the client-keyed draft/outbox/failure model (correct *for pending*). Slice 4 reused the draft as the committed hydration source without adding a client-independent committed snapshot, inheriting the conflation. The model is internally consistent for pending work and breaks precisely at the committed boundary.

---

## Plan (ordered)

1. Ship the §3 minimal read-side fix (2 edits) + regression test 5.1. Unblocks the Blocker.
2. Fix §4 `canRetry` for authored drain failures + test 5.3.
3. Add test 5.2 (two-tab isolation) as the guard that the minimal fix didn't leak pending work.
4. Schedule Phase-2 committed-snapshot store split (§3 durable end-state) with the Supabase schema; move `history` off the clientId key at the same time (§6).
