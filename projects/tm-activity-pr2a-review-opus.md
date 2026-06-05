# PR-2a review — Opus family

**PR #255** · branch `feat/activity-pr2a-core-data` · scope `git diff origin/main...HEAD`
Reviewed read-only; `git status --short` pristine before and after. Protocol: high-effort `/code-review` (8 finder angles) + hygiene seam pass.

## Verdict

**issue — 1 major, 9 minor.** The pure core-data (reducer, store, transport verbs, `useEventSource`) is clean and well-tested. The one real problem is a behavior regression in a refactored existing hook, which is exactly the brief's criterion-1 risk: `useExchangeStream` now refetches the entire exchange cache on every run switch. Everything else is latent/robustness/DRY.

---

## Criteria walkthrough

### 1. Behavior preservation of the two refactored hooks — ONE regression found

**MAJOR — `useExchangeStream` (`useExchangeStream.ts`, effect gated on `connected` + `hasConnected`): spurious full `exchangesPrefix` invalidation on every run switch.**
- Mechanism: `useEventSource`'s teardown (`useEventSource.ts`, cleanup return) unconditionally calls `setConnected(false)`. On a run switch the `streamKey` (the url string) changes → cleanup commits `connected:false`, then the new source's `onopen` commits `connected:true`. The backfill effect (`if (connected && hasConnected.current) invalidateQueries({queryKey: exchangesPrefix})`) sees the false→true transition with `hasConnected.current` still latched from the previous run, and fires.
- Old behavior: the previous effect's cleanup was a bare `source.close()` that never touched `connected`; `connected` stayed `true` across a run switch, so the backfill effect never re-ran and never invalidated. **Confirmed regression, not present before this PR.**
- Impact: an extra invalidate-all-exchange-queries + refetch/flicker on every run selection. Not data loss, not a crash; self-heals. But it violates the brief's "ZERO observable behavior change" bar for the refactor, so I rank it major.
- Fix direction: don't let a `streamKey`/run change drive a false→true `connected` flip through the reconnect-backfill path — e.g. gate the invalidation on an actual disconnect (track prior run id, or reset `hasConnected` when the stream identity changes), or have `useEventSource` not emit a spurious `connected:false` on identity-change teardown.

**MINOR — `useSessionEventStream` (`dispatchGapBackfill` / `streamEpochRef`): the old `closed`-flag guard that aborted an in-flight gap backfill on unmount is not fully re-established.** The new `streamEpochRef` only bumps during a *render* where `streamIdentity` changes; a bare unmount neither re-renders nor changes identity, so `isCurrent()` stays true and a resolved backfill still calls `onEvents` / mutates `lastSeqRef` post-unmount. Harmless for the current `useReducer` consumer (no-op dispatch), but the guarantee the comment claims is not actually there.

Resume-cursor semantics (url factory reading `lastSeqRef.current` at connect), gap-backfill-over-REST trigger, seq-cursor advance ordering, native-vs-timed reconnect selection, and disabled/teardown paths are otherwise **behavior-preserved**. `connected` no longer flips to true on backfill success (old `setConnected(true)` in the success path dropped) — benign/arguably more correct since the socket may be down mid-window.

### 2. `useEventSource` itself — sound, one latent trap

- No listener leak: cleanup sets `closed`, clears `reconnectTimer`, closes source. Confirmed.
- No double-connect: `connect()` clears any pending timer and closes the prior source before opening. On the manual-reconnect path it nulls `source` after `close()`, so a closed source can't re-fire `onerror` into a second timer. Confirmed.
- Error handler present; injectable/testable (tests stub `EventSource`). Confirmed.
- **MINOR (latent) — empty resolved URL on reconnect kills the stream.** In the reconnect path `if (resolved.length === 0) return;` bails without rescheduling and with the timer already nulled → a factory `url` that transiently yields `""` leaves `connected` stuck false forever until `enabled`/`streamKey` changes. In-diff callers always yield non-empty, so latent, but a footgun for the primitive's next consumer.
- **MINOR (altitude) — the staleness guard belongs in the primitive.** `useEventSource` owns the lifecycle but gives `onMessage` no is-current signal, so `useSessionEventStream` reinvents it (`streamEpochRef` + a parallel `streamIdentity` string that drifts from `urlKey` by including `enabled` + a render-phase ref mutation). Every future cursor/async-in-`onMessage` consumer must copy the dance. Deeper fix: expose `isCurrent()` bound to the effect generation. (Also folds the minor in §1.)
- **MINOR (altitude) — `reconnectDelayMs` presence/absence overloads one nullable number to select two distinct reconnect strategies** (native recovery vs manual close-and-retry), documented only by a call-site comment; `reconnectDelayMs: 0` would silently mean a zero-delay manual loop. Prefer an explicit `reconnect: 'native' | { delayMs }` seam. Related: a factory `url` supplied without `urlKey` gets a constant `""` reopen key and never reopens, with no guard.

### 3. `activityStreamEvents.ts` pure reducer — pure and correct; both flagged items CONFIRMED

- `applyActivityStreamFrame` is a pure `(state, frame) => state`: snapshot replaces, delta upserts by `run_id` and replaces rollup, unknown types return the same reference. No side effects. Confirmed. Snapshot+delta folding and per-`run_id` keying verified against the tests.
- **CONFIRMED — `isObject` duplicates the package's own exported `isRecord`.** `core/src/isRecord.ts` exports `isRecord` (`typeof value === "object" && value !== null && !Array.isArray(value)`), barrelled in `core/src/index.ts`; the new `isObject` is a byte-equivalent predicate in the same package. DRY violation (zero-tolerance). Fix: import `isRecord`, delete the copy. **MINOR.**
- **CONFIRMED — dead branch in `runVitalsStore.ts` `toResponse`** (the `rollup === null && empty byRunId` special case): it returns exactly what the `?? emptyActivityStreamState().rollup` fallback below already produces. Dead code. **MINOR.** (This was flagged against `activityStreamEvents.ts:58` in the brief; the actual owner is `runVitalsStore.ts::toResponse`.)
- **MINOR (robustness) — `parseActivityStreamFrame` validates shape but not identity.** It accepts a `delta` whose `item` is any object, never checking `run_id`; a skewed/buggy frame `{type:"delta", item:{...no run_id...}, rollup:{partial}}` passes, and `runVitalsStore` then keys `byRunId["undefined"]` and stores a rollup whose `status_counts[...]` are `undefined` (NaN downstream). The parser's stated job is to drop bad frames. Tolerant posture is documented, but here tolerance corrupts the store rather than dropping the frame.

### 4. `useWorkspaceActivityStream.ts` — correct

Snapshot-on-connect: no cursor, no gap backfill, fresh snapshot each reconnect (`reconnectDelayMs` set, string `url`). Built on `useEventSource`. Teardown via the primitive. `enabled: enabled && workspaceId.length > 0` guards empty id. Confirmed.

### 5. `transport.ts` — mirrors the existing verbs, boundary intact

`getWorkspaceActivity` uses `requestApiJson` and `workspaceActivityStreamUrl` uses `apiUrl` exactly as `listRuns`/`getRun` do; `workspaceId` path-encoded; `owner` always sent. Wire types imported from `@tm/contract/activity` (sanctioned subpath, declared in the contract `exports`). **`@tm/core` does not import `@tm/activity`** — only `@tm/contract/activity`. Boundary confirmed.
- Note (out of scope for this data-only slice): the routes `GET /v1/workspaces/{id}/activity[/stream]` live in the `@tm/gateway`-mounted activity router; when PR-2b wires these verbs, confirm the currently-served origin actually exposes them.

### 6. `runVitalsStore.ts` — data-only, keyed by `run_id`; one cohesion nit

Zustand store, keyed by `run_id`, fed by the pure reducer, no rendering, non-persisted (correctly never touches `capturedRunStore`). Confirmed.
- **MINOR (cohesion/efficiency) — Record↔items round-trip every frame.** `toResponse`/`fromResponse` convert `byRunId` → items[] → reducer → `byRunId` on every frame (O(runs) alloc per single-run delta), and correctness depends on `Object.values` insertion order matching the reducer's append-on-upsert (no test pins it). Hold `{items, rollup}` (the reducer's own shape) as store state and expose `byRunId` as a derived selector; both helpers and the order-invariant disappear.

### 7. DRY / hygiene

Guardrails clean: largest touched source file is `transport.ts` at 512 LOC (pre-existing, additive); no file near 700, no function near 150.
- **MINOR — `MockEventSource` copy-pasted into 6 test files** (2 new this PR, in `core` and `canvas`; 4 pre-existing). The fake mocks the browser `EventSource` that core's `useEventSource` constructs → it belongs in a core test-support module (`makeMockEventSource()` + `sources` registry); canvas `testUtils.tsx` already re-exports the transport mock "with the seam it mocks" and can re-export this too. Note: `useSessionEventStream.test.tsx` already imports from `../../testUtils` yet still redeclares the mock locally.
- **MINOR — activity wire test builders duplicated.** `wireRun` / `emptyUsage` / `rollupFor` appear in `activityStreamEvents.test.ts` (core) and `runVitalsStore.test.ts` (canvas), and `emptyUsage` again in `packages/contract/src/activity/activity.test.ts`. `ActivityWireRun` is owned by `@tm/contract/activity` → a `makeActivityWireRun` fixture belongs beside the DTO. Two of these files also hand-roll zero-literals that PR-2a's new `emptyActivityRollup()` / `emptyActivityStreamState()` core exports now provide.

---

## Suggested fix order (if greenlit)
1. **[major]** Kill the run-switch `exchangesPrefix` invalidation regression.
2. **[minor]** `isObject` → `isRecord`; drop the dead `toResponse` branch.
3. **[minor]** `parseActivityStreamFrame` reject `delta` without `run_id`.
4. **[minor]** Consolidate `MockEventSource` + activity wire builders into shared test-support.
5. **[minor, design]** Fold the staleness guard + empty-url reconnect + `reconnectDelayMs` overload into `useEventSource`.

Gate: `just check` + `just test`; for the test-support consolidation run the full `pnpm --filter @tm/shell test` (targeted vitest filters miss cross-package import fixups).
