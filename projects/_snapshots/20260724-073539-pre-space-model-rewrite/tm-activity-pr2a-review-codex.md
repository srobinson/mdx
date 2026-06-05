# PR #255 Codex review

Verdict: issue

Head: `ffb616572b5c4fa1fee5e7a7240aefcadbfe77af`

Base: `87fab5d8fe5fd23fddaf3cfd27430410d0a49f10`

Scope: `git diff origin/main...HEAD`

## Findings

### 1. Major, confidence 100: an in flight session gap backfill still dispatches after unmount

`www/packages/canvas/src/infrastructure/stream/useSessionEventStream.ts:27` says the stream epoch invalidates work after a session switch, disable, or unmount. The epoch only changes during a render whose identity differs at lines 30 to 35. Unmount performs no render, so the `isCurrent` closure created at lines 53 to 60 remains true after `useEventSource` closes the socket. When the pending REST request resolves, both completion paths at lines 96 to 103 call the retired `onEvents` callback.

This regresses the baseline lifecycle. In `origin/main`, the product hook owned `closed`, set it during cleanup, and checked it immediately after the awaited backfill before dispatching.

A read only deferred response harness reproduced the regression:

```json
{"callbackCallsAfterUnmount":1,"deliveredSeqs":[0,1,2],"sourceCloseCalls":1}
```

Closing a transcript pane while a gap request is pending can therefore deliver stale events into the retired `TranscriptChatPane` reducer. The existing backfill test at `www/packages/canvas/src/infrastructure/stream/useSessionEventStream.test.tsx:82` awaits success but never unmounts before resolving, so it does not protect the teardown contract.

Increment a committed generation during the stream identity effect cleanup, including unmount, and add a deferred backfill regression that proves `onEvents` remains untouched after unmount. Avoid mutating the generation ref during render, since abandoned concurrent renders should not invalidate the committed stream.

### 2. Minor, confidence 95: a stream identity change is now treated as an exchange reconnect

`www/packages/core/src/useEventSource.ts:110` sets `connected` false whenever a URL identity is replaced. `useExchangeStream` keeps `hasConnected` across that replacement at `www/packages/inspector/src/hooks/useExchangeStream.ts:59`. The first open for the new run or base URL consequently enters the reconnect branch and invalidates the broad `exchangesPrefix` at lines 62 to 64.

The baseline hook closed and replaced its `EventSource` on a direct `runId` or `baseUrl` change without forcing `connected` false. Its first open for the replacement therefore did not perform reconnect backfill. A read only rerender harness confirmed the branch now adds one invalidation:

```json
{"afterFirstOpen":0,"afterSwitchBeforeOpen":0,"afterSecondOpen":1,"urls":["/v1/runs/run-a/stream","/v1/runs/run-b/stream"],"closes":[1,0]}
```

This creates an observable connected state transition and a redundant exchange list fetch during an identity switch. Preserve the prior distinction between reconnecting the same stream and opening a different stream identity. Add a rerender test covering direct `runId` and `baseUrl` replacement.

### 3. Minor, confidence 100: activity parsing duplicates the existing record guard

`www/packages/core/src/activityStreamEvents.ts:103` adds `isObject`, which is functionally identical to the exported `isRecord` at `www/packages/core/src/isRecord.ts:1`. Both live in `@tm/core`. This is the exact helper duplication prohibited by the repository guidance.

Import and reuse `isRecord` in `activityStreamEvents.ts`.

## Requested confirmations

The `isRecord` versus `isObject` duplication is confirmed as finding 3.

The `rollup === null` branch at `www/packages/canvas/src/model/runVitalsStore.ts:58` is not a defect. The store's public transitions preserve the paired state: initial and cleared state are empty with a null rollup, while every applied snapshot or delta supplies a rollup. The fallback at line 63 only handles a state that external `setState` code would have to make inconsistent. No production path in this slice creates that state.

The activity reducer is pure. Snapshot replaces the view, delta upserts by `run_id`, and unknown frames preserve reference identity. `useWorkspaceActivityStream` is snapshot on connect with no cursor or REST backfill. The transport methods use GET, encode the workspace id, and import wire types from `@tm/contract/activity`. No `@tm/core` import of `@tm/activity` exists. The vitals store is data only and delegates frame folding to the reducer.

## Verification

* Focused stream and data suites: 11 files passed, 82 tests passed.
* Full `@tm/shell` Vitest suite: 160 files passed, 1,181 tests passed.
* No emit TypeScript checks for core, canvas application and tests, inspector application and tests: all five commands exited 0.
* Scoped Biome check: 13 changed TypeScript files checked, no fixes applied.
* `git diff --check origin/main...HEAD`: clean.
* `git status --short`: empty before this report was written. The report is outside the worktree.
