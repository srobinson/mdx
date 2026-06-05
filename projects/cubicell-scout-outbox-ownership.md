# Cubicell scout: `outbox` / `localCommits` ownership map

Seat A of 3. Repo `/Users/alphab/Dev/LLM/DEV/helioy/cubicell`, branch `main`, read-only survey. Store names come from `src/persistence/indexedDbSchema.ts:indexedDbProjectStoreNames`; the schema (version 8) is created by `src/persistence/indexedDbSchema.ts:createIndexedDbProjectSchema`.

## 1. WRITERS

### `outbox`

- `src/persistence/indexedDbCommit.ts:issuePromoteWrites` is the only production writer. On every promote commit that carries `commit.outbox` it does `objectStore("outbox").add({...commit.outbox, digest})`. One row per authored commit, `autoIncrement` keyPath `sequence`. A second conditional `add` in the same function fires only under injected fault `"request-error"` (test fault path via `IndexedDbProjectStorageOptions.takeCommitFault`).
- The record payload is shaped upstream by `src/persistence/storageRecordPreparation.ts` using `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:encodeOutboxCommitRecord`.
- `src/persistence/memoryProjectStorage.ts:createMemoryProjectStorage` maintains a parallel in-memory `outbox` array for the memory port (test double, same `ProjectStoragePort` contract).

### `localCommits`

- `src/persistence/indexedDbCommit.ts:completeReceiptWrite` is the only production writer: `objectStore("localCommits").put({changedAssetKeys, commitId, digest, kind, originClientId, projectId, receipt})` on every completed commit. One row per commit, keyPath `[projectId, commitId]`.
- Memory twin: `src/persistence/memoryProjectStorage.ts` (`localCommits: Map`, set in its commit path).

## 2. READERS/DRAIN

### `outbox` reads

- `src/persistence/indexedDbOutbox.ts:loadIndexedDbOutbox` reads all envelopes for a branch via `outboxBranchSequenceIndex`. Exposed as `ProjectStoragePort.loadOutbox` by `src/persistence/indexedDbProjectStorage.ts:createIndexedDbProjectStorage`.
- `src/persistence/indexedDbCommit.ts:issuePromoteReads` reads a single superseded envelope via `outboxCommitIndex` when `commit.rebase` is set.
- Hydration (`src/persistence/projectRecordHydration.ts:hydrateProjectRecords` / `decodeOutbox`) accepts an `outbox` array, but every IndexedDB read path passes `outbox: []` (`src/persistence/indexedDbProjectReads.ts`, `src/persistence/storageRecordReads.ts`), so the store is not read during normal project load.

### `outbox` deletes (drain machinery, implemented)

- `src/persistence/indexedDbOutbox.ts:discardIndexedDbOutbox` cursors a branch range and deletes matching commitIds. Exposed as `ProjectStoragePort.discardOutbox`.
- `src/persistence/indexedDbCommit.ts:issuePromoteWrites` deletes `plan.supersededOutboxSequence` when a rebase replay supersedes an older envelope (replaces a row, does not shrink the queue).
- Sole production caller of `loadOutbox`/`discardOutbox`: `src/state/projectDurabilityForwardRebase.ts:ProjectDurabilityForwardRebase.sync` with `source === "outbox"`, which replays each envelope through `promoteRebasedEnvelope` and discards the remainder on rejection.
- No bulk `clear()` exists anywhere; the only full reset is the version-upgrade store recreation in `createIndexedDbProjectSchema`.

### `localCommits` reads

- `src/persistence/indexedDbCommit.ts:issuePromoteReads` gets `[projectId, commitId]` for idempotency (skip already-applied commits, see `src/persistence/promoteContract.ts`).
- `src/persistence/pendingDrafts.ts:stageIndexedDbPending` gets the same key to skip staging a draft whose commit already landed.

### `localCommits` deletes

None found. No `delete`, `clear`, or cursor removal on `localCommits` exists in `src/`. Searches run: `grep -rn '"localCommits"' src/` (6 hits, all schema/get/put), `grep -rn 'objectStore("localCommits")' src/` (3 hits: two `get`, one `put`), fmm term search `localCommits` (one test symbol). The store is an append-only idempotency ledger with no retention policy; 803 live rows is one row per commit ever made.

## 3. TRIGGER

The outbox drain trigger is a remote-commit install, not a timer or network event:

- `src/state/projectDurability.ts:ProjectDurability.installCommitted` calls `storage.installCommitted(commit)` then `this.forwardRebase.sync(storage, false, "outbox", receipt.commitId)`. That is the only `source === "outbox"` sync call in `src/`.
- It is exposed upward as `src/state/cubicellStore.ts` `installCommitted: durability.installCommitted` on the store handle.
- Nothing in the application ever calls it. All callers of `installCommitted` outside `src/state/` and `src/persistence/` are test drivers: `tests/committedStoreBrowserDriver.ts`, `tests/projectRebaseContract.ts`, `tests/projectStorageRebase.test.ts`. There is no interval, no network listener, no sign-in hook, no manual UI action wired to it.
- The other two `forwardRebase.sync` calls (`src/state/projectDurability.ts` hydrate and retry paths) use the default `source: "draft"` and drain pending drafts, never the outbox.

So the machinery is: outbox holds authored commits waiting for an authoritative remote install that would trigger rebase-and-discard. No remote ever arrives, so the queue only grows (687 rows).

## 4. FIREBASE SEAM

There is none. Searches run: `grep -rni firebase` over `src/`, `index.html`, `package.json`, `vite.config.ts`, `public/`, `pnpm-lock.yaml`, and repo-wide over `*.ts/tsx/js/html/json` excluding `node_modules` — zero hits. No `initializeApp`, `getAuth`, `signIn`, or `firestore` symbol exists in `src/`. This codebase never loads a Firebase SDK; the `firebase-heartbeat-database` and `firebaseLocalStorageDb` databases on `localhost:4174` are per-origin residue from some other app previously served on that port, not a seam of this repo. No symbol bridges Firebase to this queue.

## 5. VERDICT

`drain implemented but never invoked` for `outbox`: the full replay-and-discard path (`ProjectDurabilityForwardRebase.sync` → `discardIndexedDbOutbox`) exists and is exercised only by tests, because its sole trigger (`installCommitted`) has no production caller. For `localCommits` the stricter `no drain implemented` applies: append-only, no delete path exists anywhere.
