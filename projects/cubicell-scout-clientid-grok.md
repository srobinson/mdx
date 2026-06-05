# Cubicell scout: clientId / committed-vs-pending

Agent: `performance-audit:general:6:2.4` (grok)  
Scope: persistence stack on `docs/performance-audit` (merged slices 1–3) plus PR#106 `feat/persist-cutover` @ `4c7fff3`  
Mode: read-only on the cubicell tree; report only  
Date: 2026-07-21

## Executive answer

**Root cause:** There is no local "promote to client-independent committed" step. Every successful IDB durability unit still stores project, assets, history, and the working snapshot under **client-keyed** rows. The working recovery surface is the **client-keyed draft**. On reopen under a new `clientId` (sessionStorage), load correctly selects the latest source branch via project-scoped outbox, then **deliberately drops that branch's draft** (`indexedDbProjectStorage.ts` / `issueProjectHeaderRequests`), and hydration **never replays outbox onto the workbench**. `resolveWorking` then falls back to poster/default → committed local edits disappear.

**Recommended minimal fix:** When hydrating from a source branch, always load that source's latest completed draft as the **read-only recovery snapshot** (validate draft against `sourceClientId`, not the opener's `address.clientId`). Keep drafts/outbox/failure **writes** client-keyed. On foreign inherit, do not adopt foreign failure/retry ownership; clear or ignore foreign outbox for the new client's pending set (ops already baked into the draft snapshot). Leave schema rekey of projects/assets for a later Phase-2-aligned slice if needed; this unblocks the data-loss Blocker without ripping multi-tab pending isolation.

---

## STORAGE.md contract (invariant)

From `STORAGE.md` Local persistence (~L227–231 on `4c7fff3`):

- Multiple tabs receive a distinct `clientId`.
- **Unsynced working snapshots, outbox commits, and failure state** are keyed by client ID so one tab cannot overwrite another tab's pending branch.
- Optimistic **hosted** revisions detect stale writers (Phase 2+).

Implied boundary:

| Kind | Intended keying | V1 role |
|------|-----------------|--------|
| Pending / unsynced | `clientId` | Multi-tab isolation |
| Committed shared project content | client-independent | Any tab/session loads it |
| Hosted stale-writer | `client_id` on commits | Phase 2+ |

`clientId` is created in `preferencePort.loadCubicellPreferences` and stored only in **sessionStorage** (`cubicell.client`). New tab / browser restart ⇒ new `clientId` unless session is restored.

---

## 1. Site enumeration (clientId)

Classification:

- **CORRECT** — keys pending/unsynced work, or correctly scopes multi-tab queues/failures.
- **BUG** — client-keys data that must be shared after local durability, or drops committed recovery on clientId change.
- **AMBIGUOUS** — client-keyed today but also used as the only local head snapshot (design debt; becomes BUG at load time).

### Schema (`indexedDbSchema.ts` / `createIndexedDbProjectSchema`)

| Store / index | Key | Class |
|---------------|-----|-------|
| `projects` | `[projectId, clientId]` | **BUG / AMBIGUOUS** — committed local head is client-private |
| `assets` | `[projectId, clientId, assetId]` | **BUG / AMBIGUOUS** — same |
| `poseRevisions` | `[projectId, revisionId]` | **CORRECT** — shared immutable |
| `drafts` | `[projectId, clientId, commitId]` | **CORRECT** as pending; **BUG in role** when used as sole durable head |
| `history` | `[projectId, userId, assetKey, clientId]` | **AMBIGUOUS** — local undo is user+branch private; new client loses history on inherit |
| `outbox` + `byCommit` / `byBranchSequence` | includes `clientId` | **CORRECT** pending |
| `outbox` + `byProjectSequence` | `[projectId, sequence]` | **CORRECT** — project-wide latest branch discovery |
| `userProjectState` | `[projectId, userId]` | **CORRECT** shared workspace prefs |

### Write path (`issueCommitWrites` in `indexedDbProjectStorage.ts`)

On every local durability success, one TX puts:

- `projects`, `assets`, `history`, `drafts`, `outbox` under **writer `clientId`**
- `poseRevisions` shared
- `userProjectState` shared

There is **no second step** that copies head into client-independent keys. Local "saved" ≡ client-keyed branch tip.

### Load / source selection

| Site | Symbol | Behavior | Class |
|------|--------|----------|-------|
| `indexedDbProjectStorage.ts` | `issueSourceRequests` | Exact `[projectId, address.clientId]` project, else latest outbox row's `clientId` via `byProjectSequence` | **CORRECT** discovery |
| `indexedDbProjectStorage.ts` | `issueProjectHeaderRequests` L495–501 (`4c7fff3`; baseline ~L422) | If `sourceClientId !== address.clientId` **or** no latest: `draft: undefined` | **BUG** — drops sole working recovery |
| `memoryProjectStorage.ts` | `loadProject` / `sourceClient` | Same drop when `sourceClientId !== address.clientId` | **BUG** (mirrors IDB) |
| `storageRecords.ts` | `rawProjectHeader` → `draftValue(..., address.clientId, ...)` | Validates draft against **opener** clientId | **BUG** — would reject foreign draft even if loaded |
| `storageRecords.ts` | `projectValue` / `assetValue` / `outboxValue` / `historyValue` with `sourceClientId` | Validate stored rows for source branch | **CORRECT** for branch read |
| `indexedDbHydrationBytes.ts` | `physicalDraftBytes` | Requires `stored.clientId === sourceClientId && stored.clientId === address.clientId` | **BUG** — foreign draft bytes zeroed |
| `projectRecordHydration.ts` | `decodeDraft(..., seed.clientId)` | Rejects draft if `clientId !== seed` | **BUG** for inherit path |
| `projectRecordHydration.ts` | `resolveWorking` | Draft → working; else userState asset + poster pose; else default scene | **CORRECT** fallback; becomes data loss when draft missing |
| `projectRecordHydration.ts` | outbox decode | Outbox returned to state; **not applied** to workbench | **CORRECT** for sync bag; **implies draft is required** for recovery |

### Failure / queue / durability

| Site | Symbol | Class |
|------|--------|-------|
| `orderedCommitQueue.ts` | `ProjectCommitQueues.queueFor` / `branchKey([projectId, clientId])` | **CORRECT** per-branch pump |
| `indexedDbFailureState.ts` | draft keys, `branchKey`, `draftBranchRange` | **CORRECT** pending failure |
| `indexedDbFailureValidation.ts` | re-fingerprint with commit.clientId | **CORRECT** |
| `indexedDbUserProjectState.ts` | pending.clientId on shared row | **CORRECT** in-flight user-state isolation |
| `storagePort.ts` | `ProjectStorageAddress.clientId`, branch/failure types | Contract surface |
| `projectDurability.ts` | address.clientId on user-state units | **CORRECT** writer identity |
| `projectCommitProjection.ts` / `projectRecordProjection.ts` | stamps draft/outbox with input.clientId | **CORRECT** encode ownership |
| `cubicellStore.ts` | address from session clientId + prefs project/user | **CORRECT** wiring; **triggers BUG** on every new session |
| `preferencePort.ts` | sessionStorage `cubicell.client` | **CORRECT** for multi-tab identity; makes new-clientId reopen common |
| `localAuthoring.ts` | operations carry clientId | **CORRECT** provenance for Phase 2 |

### Domain / codecs

Draft, outbox, checkpoint codecs carry `clientId` as provenance — **CORRECT**.  
Domain `AuthoredOperation.clientId` — **CORRECT** for hosted stale-writer later.

---

## 2. Committed-vs-pending boundary (as implemented)

### What should be "committed local project state" (any client loads)

Authoritative recovery for a Project after local durability should be:

1. Latest **project manifest** + **assets** + **pose revisions** that reflect the last successful local TX.
2. Latest **working attachment + workingPose** at that TX (today encoded only in **draft**).
3. Optional: local history for undo (user-scoped; may stay branch-private).
4. Shared **userProjectState** (panel/active asset) — already client-independent.

Outbox is **not** applied on hydrate; it is a bag for future hosted sync. Therefore **draft (or an equivalent shared head snapshot) is the only working recovery**.

### What is pending / client-private

- In-flight IDB attempts (draft + failure metadata before success).
- Outbox rows not yet hosted-acked (Phase 2).
- Per-branch ordered commit queue failure state.
- userProjectState `pending` envelope.

### Local promote step today?

**None.**  
`OrderedCommitQueue.complete` → receipt → durability sets `saveState: saved`. Physical writes already happened in `issueCommitWrites` under the writer’s `clientId`. Nothing copies head to shared keys. "Local committed" remains "tip of a client branch."

That dual role of draft (pending isolation **and** durable head) is the root modeling error.

---

## 3. Minimal collaboration-forward fix

### Goal

- New `clientId` reopen recovers the same workbench as the last completed TX.
- Two live tabs still cannot clobber each other's **in-flight** branch writes.
- Phase 2 can still key pending outbox/failure by client and use hosted revision races for true multi-writer.

### Do now (minimal, no schema migration)

1. **`issueProjectHeaderRequests`** (IDB + memory twin): always resolve latest draft for `sourceClientId` + `latest.commitId` when `latest` exists. Remove the foreign-client draft drop.  
   - Keep dropping draft only when there is no completed outbox tip (empty branch).
2. **`rawProjectHeader` / `draftValue`**: validate draft with **`sourceClientId`**, not `address.clientId`.
3. **`physicalDraftBytes`**: require `stored.clientId === sourceClientId` only (drop the `=== address.clientId` conjunction).
4. **`decodeDraft` / hydrate seed**: pass `sourceClientId` for draft acceptance when inheriting; or accept draft when `draft.clientId === sourceClientId` while seed retains opener identity for **new writes**.
5. **Foreign inherit outbox policy (V1-safe, Phase-2-ready):**  
   - Load source outbox for diagnostics if needed, but set runtime `outbox` to **empty** when `sourceClientId !== address.clientId` (ops already reflected in draft snapshot). Prevents future double-submit under a new client.  
   - Same-client reopen keeps full outbox + failure restore.
6. **Failure restore:** only `restoreFailure` / retry for queues matching `address.clientId`. Foreign branch failures stay on the foreign branch (already true if queues are per clientId; verify open path does not re-home foreign failures onto the new client).
7. **First write after inherit:** continues under `address.clientId`, creating a new branch tip (projects/assets/draft/outbox rows for the new client). Multi-tab isolation of subsequent writes preserved.

### Explicit non-goals for this minimal fix

- Do not rekey `projects`/`assets` yet (larger migration; optional follow-up).
- Do not move `clientId` from sessionStorage to localStorage (would hide the bug and weaken multi-tab identity).
- Do not replay outbox onto workbench as the primary recovery (duplicates draft; harder for Phase 2).

### Optional follow-up (cleaner Phase-2 alignment)

- Shared head store: `projects`/`assets` keyed by `projectId` only (or `projectId` + content revision), updated only on local TX complete.
- Client-keyed `drafts` only for pre-complete attempts and true unsynced working forks.
- Hosted ack removes client outbox; shared head mirrors Postgres.

Minimal fix above is a subset: treat **source tip draft as readable committed recovery** without schema break.

### Why this survives Phase 2

- Writer identity remains on outbox/operations (`clientId`).
- Pending failure stays branch-scoped.
- Hosted stale-writer still uses operation `client_id` + revision, not "draft is secret forever."
- Shared recovery is "latest durable snapshot," which is what Postgres will also be.

---

## 4. Related Major (`projectDurability.ts:147` canRetry)

**Independent of the clientId / committed-pending confusion.**

- Failure: `failureSaveState(storage.getFailure()) ?? errorSaveState(error, unit.commitId, unit.kind === 'user-project-state')`.
- Authored/checkpoint projection or `prepareStorageCommit` errors leave `getFailure() === null` ⇒ `canRetry: false`.
- `retry()` already supports `!retriesStorage` → `blocked = false; drain()` re-run.
- PersistenceStatus disables RETRY SAVE; local dispatch stays gated on `failed`; refresh drops the in-memory edit.

Fix: pass `canRetry: true` whenever `unit.commitId` is set (or default `commitId !== null`), except superseded/conflict. Orthogonal PR from clientId inherit fix; both lose user work, different roots.

---

## 5. Coverage gap

P0 / cutover tests (`cubicellStore.browser.test.ts`, `cubicellStorePersistence.test.ts`, storage browser drivers) pin one `clientId` via fixture/session restore.

### Missing regressions (must add)

1. **New-clientId reopen recovers committed work**  
   - Save authored edit under client A; close.  
   - Open with client B (new session id, same projectId/userId).  
   - Expect workbench (gap/scene/digest) matches last completed TX; not poster/default.  
   - Real Chromium + memory port twins.

2. **Two-tab pending isolation**  
   - Client A and B both open same project.  
   - A writes; B writes.  
   - Assert A cannot overwrite B's in-flight/failure draft keys; queues isolated by branch.  
   - Optional: last completed project sequence wins on third open.

3. **Retry after authored drain failure without storage.getFailure**  
   - Inject projection/worker or prepare throw.  
   - Expect `canRetry: true`, RETRY SAVE re-drains, eventually `saved`, no refresh required.

4. **Foreign inherit does not steal foreign failure retry**  
   - A fails mid-commit; B opens; B is not blocked by A's failure; A's draft/failure remains under A.

5. **Same-clientId reopen keeps outbox + failure**  
   - Guards against over-fixing outbox on inherit.

---

## 6. Quality / dead code / slice inconsistency

| Issue | Notes |
|-------|-------|
| Dual role of draft | Documented as pending; implemented as durable head. Naming and STORAGE wording lag code. |
| Client-keyed projects/assets | Inconsistent with STORAGE "committed is shared." poseRevisions already shared. |
| `history` client-keyed | New session loses undo stack on inherit even after draft fix; decide if intentional. |
| Outbox loaded but not applied | Correct for sync; undocumented dependency that draft is mandatory for recovery. |
| `physicalDraftBytes` double client check | Dead for foreign path; always false when source ≠ address. |
| Baseline vs cutover | Blocker present on **both** `docs/performance-audit` and `4c7fff3`; cutover surfaces it by making IDB the only writer + session clientId. |
| canRetry Major | Independent quality bug in durability coordinator. |
| Preference cutover | `cubicell.workbench` one-time clear only — correct; not part of clientId bug. |

---

## Reuse Map

| Existing piece | Reuse |
|----------------|-------|
| `issueSourceRequests` / `sourceClient` | Keep project-sequence branch discovery |
| `byProjectSequence` index | Keep |
| Shared `poseRevisions`, `userProjectState` | Keep as model for shared head |
| `OrderedCommitQueue` per `[projectId, clientId]` | Keep for pending |
| Failure draft keying | Keep |
| Slice 2 codecs + prepare/fingerprint | Keep; only change **read validation** client argument for drafts |
| Cutover durability coordinator | Keep; separate canRetry fix |
| Browser lifecycle / store drivers | Extend with new-clientId cases |

---

## Quality Map

| Risk | Severity | Evidence |
|------|----------|----------|
| New clientId drops draft → default/poster workbench | **Blocker** | `issueProjectHeaderRequests` L495; `resolveWorking` L345–366; no outbox replay |
| draftValue/physicalDraftBytes/decodeDraft reject foreign tip | **Blocker** (same chain) | `storageRecords.ts` draftValue; `indexedDbHydrationBytes.ts` physicalDraftBytes; `decodeDraft` |
| projects/assets client-keyed with no promote | **Major** design debt | schema + `issueCommitWrites` |
| canRetry false on authored pre-storage failure | **Major** independent | `projectDurability.ts:147` |
| Tests only single clientId | **Major** gap | browser + persistence suites |
| History lost on inherit | Minor/Product | history key includes clientId |

---

## Plan

### P0 — stop data loss (minimal)

1. Load source tip draft for foreign clients (IDB + memory).
2. Validate draft against `sourceClientId` end-to-end (header, hydration bytes, decodeDraft).
3. Foreign inherit: empty runtime outbox; do not adopt foreign failure.
4. Tests: new-clientId reopen exact recovery; same-client failure retain; two-tab isolation smoke.
5. Separate tiny fix: authored canRetry default true when commitId set.

### P1 — model clarity (optional, before hosted)

1. Document in STORAGE.md: local durable tip draft is readable recovery for any client; writes remain client-keyed until hosted ack.
2. Consider shared head keys for projects/assets once multi-device requires it.
3. Decide history inheritance policy.

### P2 — hosted

1. Outbox drain to Postgres; ack removes client outbox.
2. Stale-writer via hosted revision + operation client_id.
3. Local shared head mirrors server; client draft only for true offline forks.

---

## Verdict line (for bus)

Root cause: local durable head (especially working draft) stays client-keyed with no promote, and foreign-client hydrate drops that draft without replaying outbox.  
Minimal fix: always hydrate the source branch's latest completed draft as read-only recovery (validate with sourceClientId), keep pending writes/failures client-keyed, empty outbox on foreign inherit; fix canRetry separately.
