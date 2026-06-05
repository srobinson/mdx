# cubicell outbox history archaeology

Repo: `/Users/alphab/Dev/LLM/DEV/helioy/cubicell`  
Branch surveyed: `main` (read-only; no checkout)  
Date: 2026-08-04  
Question: was the outbox drain ever wired, and if so when did it stop?

## 1. When the outbox appeared

`git log -S"outbox" --oneline --all` (oldest first):

| SHA | Subject |
|-----|---------|
| `2aa93627` | feat(persistence): cut over to committed IndexedDB storage (#107) |
| `ad5c6f60` | feat(persistence): hydrate committed projects before client drafts (#108) |
| `ee484e07` | feat(persistence): forward rebase stale commits (#109) |
| `c51e9767` | docs(storage): refresh persistence and scene docs to shipped state (#114) |
| … later docs/perf/schema touchups | |

**Introduction commit:** `2aa93627fc1f47480f6eb42e375fba4076cea8cf`  
**Subject (quoted):** `feat(persistence): cut over to committed IndexedDB storage (#107)`  
**Date:** 2026-07-22

That commit created the IndexedDB schema with an `outbox` object store on `cubicell.projects` (then schema v3; main is now v8), plus promote path that **appends** an outbox row on every authored promote (`src/persistence/indexedDbCommit.ts` `issuePromoteWrites`: `outbox.add` when `commit.outbox` is set).

STORAGE.md (introduced in the same commit) defines the outbox purpose as carrying **pending hosted commits**:

> "A durable operation outbox carries pending hosted commits."

and documents a future worker:

```text
read oldest pending commit
  -> send commit with expected revisions
  -> acknowledge and remove from outbox
  -> continue in local order
```

while stating in the same edition that the worker did not exist yet:

> "The remaining gaps are hosted concerns: no Supabase schema, synchronization worker, … The local outbox is durable …"

Main still says the same gap (STORAGE.md ~L96–98).

## 2. Was a drain / flush / push / sync worker ever present?

Searched across **all refs** with `git log --all -S"<symbol>"` for:

`drainOutbox`, `flushOutbox`, `syncOutbox`, `processOutbox`, `outboxWorker`, `uploadOutbox`, `hostedSync`, `syncWorker`, `pushCommits`, `ackOutbox`, `acknowledgeOutbox`, `removeFromOutbox`, `firebase`, `firebase-heartbeat`, `firebaseLocalStorage`

**Every hit count: 0.** No commit ever added those symbols. No delete-diff shows a removed sync/outbox worker implementation.

What *does* exist (and must not be confused with hosted drain):

| Symbol | Role |
|--------|------|
| `ProjectDurability.drain` / `drainQueue` (`src/state/projectDurability.ts`) | Local save-queue drain: promotes durability units to IndexedDB. Does **not** remove outbox rows after success. |
| `outbox.delete(plan.supersededOutboxSequence)` (`indexedDbCommit.ts`) | Only on **forward-rebase supersede** of a reminted envelope. |
| `discardPending` | Clears a client branch (including its outbox) on explicit discard. |

Normal successful promote path: **append outbox, keep it.** That matches the design: local durability marks `saved`; hosted ack would remove the row. Hosted ack never shipped.

**Removed/disabled commit:** none. Nothing to remove.

## 3. Firebase / hosted sync gate on main

- `git log --all -S"firebase"` / `Firebase` / heartbeat DB names: **empty**.
- `package.json` dependencies: no `firebase`, no `@supabase/*`.
- `src/**`: no Firebase or Supabase client imports; no `import.meta.env` / `VITE_` consumption for sync.
- `.env` holds Supabase project URL/JWKS comments and values (planned host per STORAGE.md). That is configuration for a layer that was never coded, not an off switch for running code.
- **Gate:** none. There is no `path:symbol` feature flag, env var, or build condition that toggles outbox upload, because no uploader exists.

Observed origin DBs named `firebase-heartbeat-database` / `firebaseLocalStorageDb` are **not produced by this repository's history**.

## 4. Unmerged local branches

Compared to `main` with `git log main..<branch> -S"outbox"` and the drain/sync symbols above:

| Branch | Outbox-only commits vs main | Drain/sync worker |
|--------|-----------------------------|-------------------|
| `feat/llm-control` | none | none |
| `spike/shape-shader` | none | none |
| `feat/turn-rotate-selection` | none | none |
| `experiment/spinor-relative-phase` | none | none |
| `feat/typography-domain` | none | none |

(Brief's "six local branches" = `main` + these five. No checkout performed.)

## 5. Why 687 outbox rows is expected under current code

Against one asset with `committedRevision=289` and 803 `localCommits`: every successful authored promote appends an outbox envelope and never host-acks it. Local commits (including checkpoints) grow faster than authored outbox rows; checkpoints intentionally skip the outbox (STORAGE.md). Growth without a consumer is the designed pre-hosted shape, not evidence of a broken former drain.

## VERDICT

**`never implemented`**

Local outbox **write path** has been live since `2aa93627` (`feat(persistence): cut over to committed IndexedDB storage (#107)`). The **hosted synchronization worker that drains the outbox** was specified in STORAGE.md from that same commit onward and has never been implemented on any branch, never gated off, and never removed.

