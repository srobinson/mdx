# PR #255 review (Fable) — feat/activity-pr2a-core-data

## BOUNDED DELTA @ f4ad582 (fixtures → `@tm/contract/activity/testing`): CLEAN

The non-blocking note below is resolved: fixtures moved off the production barrels onto a new `./activity/testing` subpath. `isContractSubpathExports` was minimally extended, not relaxed — context keys still must equal `./src/<ctx>/index.ts`; the only new sanctioned shape is `./<ctx>/testing` → `./src/<ctx>/testing.ts`; no wildcards, no root barrel, everything else still fails. Verified by verbose run: "treats a browser @tm/activity import target as forbidden", "fails closed for deep package imports", "enforces zero external imports into contract internals", and the exports-shape test all pass; shell + contract suites green; tree pristine. Bundled hook edits (identity string consolidation, explicit streamKey binding, comment char) are cosmetic dep-hygiene with no behavior delta.

## DELTA RE-VERIFY @ e9f8ac4 (correction round ffb6165 → e9f8ac4): CLEAN, merge-ready

- **Major A (unmount vs in-flight gap backfill) — FIXED, test genuine.** `useSessionEventStream.ts::streamEpochRef` now bumps in a dedicated effect **cleanup** keyed on `[baseUrl, enabled, owner, sessionId]`, so identity change, disable, AND unmount all invalidate in-flight backfills; the render-phase bump is gone and the false comment corrected. New test "does not dispatch an in-flight gap backfill after unmount" holds the `listSessionEvents` promise open, unmounts, resolves, and asserts `onEvents` untouched — on ffb6165 the resolution would dispatch (epoch never bumped on unmount), so it fails without the fix. Not a tautology.
- **Major B (spurious `exchangesPrefix` invalidation on run switch, Opus) — FIXED, test genuine, and confirmed a true refactor regression:** pre-refactor cleanup never flipped `connected` false on run switch, `useEventSource`'s teardown does, which armed the stale `hasConnected` latch. Fix resets the latch on `streamIdentity` change and skips latching that pass (`useExchangeStream.ts`). New `useExchangeStream.identity.test.tsx` asserts no invalidation on runId switch AND still-invalidates on same-run reconnect (guards against overcorrection). Fails without the fix on ffb6165.
- **Minors — all applied:** `isObject` → shared `isRecord`; dead `toResponse` branch removed; `parseActivityStreamFrame` rejects deltas lacking a non-empty string `run_id` (+test); `DEFAULT_ACTIVITY_OWNER` + `emptyStatusCounts()` + `emptyActivityUsageTotals()` hoisted to `@tm/contract/activity` with both planes importing from there (contract still has no `dependencies` field; AGENTS.md charter clause widened to sanction pure dep-free enum derivations); inert biome-ignore deleted; empty factory URL now reschedules reconnect instead of killing the stream (+test); `MockEventSource` consolidated into `@tm/core/testing` and re-exported through canvas `testUtils` (correct test-support surface). Router's remaining `emptyUsage` is the **domain** camelCase shape from `../domain/usage`, not a duplicate of the wire helper — clean.
- **Gates observed by me @ e9f8ac4:** `just check` exit 0; `@tm/shell` 1186 passed (up 5 = the new regression tests), `@tm/contract` 4 passed, `@tm/activity` 129 passed / 9 pre-existing skips. Pre-existing hook test files remain green. Tree pristine.
- **One non-blocking note for a future doc touch:** `makeActivityWireRun`/`makeActivityRollup` fixture builders ship in contract's **production** barrel (and core re-exports them from `activityStreamEvents.ts`), while the updated AGENTS.md clause sanctions only "pure derivations of those enums" — pure, dep-free, tree-shakable, so fine in substance, but the charter sentence should name fixtures (or they should move behind a testing surface) so the next reviewer doesn't re-litigate. No code change requested.

---

# Original review @ ffb6165 (historical)

Scope: `git diff origin/main...HEAD` (15 files, +1172/−91). Gates run by me, observed green: `just check` exit 0; full `pnpm --filter @tm/shell test` exit 0 (160 files, 1181 tests). `git status --short` pristine before and after. Both refactored hooks keep their pre-existing test files byte-untouched (`useSessionEventStream.test.tsx`; all six `useExchangeStream.*` test files) — the regression net is intact and passing.

**Verdict: issue — 1 Major (teardown behavior regression in the highest-risk zone), 4 Minors, 1 note.** Everything else on the brief's checklist verified clean (§ Checklist).

---

## Findings (ranked)

### F1 — MAJOR, CONFIRMED: unmount no longer cancels an in-flight gap backfill

`www/packages/canvas/src/infrastructure/stream/useSessionEventStream.ts` — `streamEpochRef` / `DispatchContext.isCurrent`.

Old code guarded every dispatch with the effect-closure `closed` flag, set in the effect cleanup — which runs on **both** identity change and **unmount**. The refactor replaced it with a render-epoch guard: `streamEpochRef.current` bumps only when a render observes a changed `streamIdentity` (`sessionId\0owner\0baseUrl\0enabled`). Unmount triggers no render, so the epoch never bumps; `useEventSource`'s internal `closed` flag protects only its own source callbacks, not the hook's detached backfill promise.

**Failure scenario:** live event arrives with a seq gap → `dispatchGapBackfill` issues `listSessionEvents(...)` → user closes the pane (unmount) while the request is in flight → promise resolves, `isCurrent()` still true → `context.onEventsRef.current(events)` fires **after unmount**, delivering a batch of session events into the consumer's reducer/store for a dead viewer (plus a write to the unmounted tree's `lastSeqRef`). Old code provably dropped this (`if (closed) return` on both success and catch paths).

The in-code comment claims the opposite: "in-flight gap backfills can drop results after a session switch / disable / **unmount**" — the unmount claim is factually wrong. No test covers unmount-during-backfill (the one backfill test asserts the happy path).

**Fix shape (small):** bump the epoch on unmount — e.g. `useEffect(() => () => { streamEpochRef.current += 1; }, [])` in the hook — or fold a `mountedRef` into `isCurrent`. Add the missing test: resolve the backfill after unmount, assert `onEvents` not called (it fails before the fix — observable end-state lesson).

### F2 — MINOR, PLAUSIBLE (removed behavior, unacknowledged): backfill success no longer forces `connected = true`

Same file, old `dispatchGapBackfill` success path called `setConnected(true)`; the refactor drops it — `connected` is now owned exclusively by `useEventSource` (`onopen`/`onerror`). Observable delta: source errors while a backfill is in flight → old code flipped `connected` back to `true` on backfill success (stream actually down); new code keeps `false` until the next `onopen`. Almost certainly an improvement, but this slice's mandate was zero observable change and neither the commit message nor a comment acknowledges it. Disposition: builder confirms intentional and states it in the PR body (or restores it, which I would not recommend).

### F3 — MINOR, CONFIRMED (reuse): `isObject` re-implements barrel-exported `isRecord`

`www/packages/core/src/activityStreamEvents.ts::isObject` duplicates `www/packages/core/src/isRecord.ts::isRecord` (identical semantics, same package, already exported via `core/src/index.ts`). One-line import swap, delete the private helper. (Opus flag: CONFIRMED.)

### F4 — MINOR, CONFIRMED (reuse/drift across the plane seam): `DEFAULT_ACTIVITY_OWNER` and status-counts zeroing duplicated

- `DEFAULT_ACTIVITY_OWNER = "local"` now declared in both `www/packages/core/src/transport.ts` and `packages/activity/src/server/activityRouter.ts`.
- `Object.fromEntries(activityStatuses.map((status) => [status, 0]))` zeroing appears verbatim in `core/src/activityStreamEvents.ts::emptyActivityRollup` and `activityRouter.ts` rollup construction.

Drift cost: wire default owner or `activityStatuses` membership changes on one side silently diverge server vs browser counts. The owner const fits `packages/AGENTS.md`'s contract clause ("optional status enums as `as const` values") — hoist to `@tm/contract/activity`, both sides already import that subpath. The zeroing helper is a runtime function, beyond the clause's literal allowance — either widen the clause (pure, dep-free derivations of the enums) and hoist an `emptyStatusCounts()`, or accept the duplication knowingly; orchestrator/Stuart call on the clause.

### F5 — MINOR, CONFIRMED (conventions): inert biome suppression in the new primitive

`www/packages/core/src/useEventSource.ts` carries `// biome-ignore lint/correctness/useExhaustiveDependencies: …` on the connect effect, but biome reports the suppression itself as unused — the rule never fires on that deps array (and `www/packages/core` is not biome-linted by any gate at all; only shell + product plane are). Dead, misleading comment; delete it.

### N1 — note (simplification, no action required): double validation + store round-trip

`applyActivityStreamFrame` takes the widened `ActivityStreamFrame | { type: string }` and re-checks `items`/`item`/`rollup` even though `parseActivityStreamFrame` is the only production gate — ~8 unreachable defensive lines plus two `as Extract<…>` casts; narrowing the signature would drop both (opus's `rollup == null` branch flag: real code, unreachable in production — smell, not a bug). `runVitalsStore` round-trips map→array→map per frame batch; O(n) per delta but n is per-workspace run count and the round-trip buys reuse of the shared pure fold — acceptable as written.

---

## Checklist (brief items verified clean)

1. **Behavior preservation:** reconnect timing preserved (session: close + 1s timer + fresh cursor URL via factory re-invocation, matching old `RECONNECT_DELAY_MS` flow; exchange: no close, native EventSource recovery, matching old no-close semantics). Cursor resume: `lastSeqRef` still seeded from `highestSeq`, updated on dispatch/backfill, stamped per (re)connect via the `url` factory. Gap-backfill trigger unchanged (`seq > prev + 1` → REST range fetch → merged dispatch; catch path unchanged). Reopen identity equivalent to old effect deps (session `urlKey` = sessionId/owner/baseUrl + `enabled` dep; exchange string URL = runId/baseUrl). Exceptions are exactly F1/F2.
2. **useEventSource:** no listener leak (single source, cleanup closes and clears timer; handlers attached per-instance); no double-connect (connect() clears pending timer and closes any prior source first); `onError` hook present; testable (jsdom EventSource stub drives the shipped tests); no source left open on teardown or reopen. Empty-URL early return is only reachable in the disabled exchange case where `enabled` is already false.
3. **activityStreamEvents:** genuinely pure `(state, frame) → state`, no side effects, per-`run_id` upsert, snapshot replaces wholesale (prunes vanished runs), unknown frame types no-op. Tests cover snapshot/delta/append/unknown/malformed.
4. **useWorkspaceActivityStream:** snapshot-on-connect confirmed — string URL (no factory), no cursor, no backfill, reconnectDelayMs 1s; teardown inherited from useEventSource; `enabled && workspaceId.length > 0` gate; malformed payloads dropped pre-dispatch.
5. **transport:** `getWorkspaceActivity` mirrors `listRuns` (`requestApiJson`, plain `Error`); `workspaceActivityStreamUrl` uses `apiUrl` + `URLSearchParams`; `encodeURIComponent(workspaceId)` present (slashful ids); wire types from `@tm/contract/activity` only; no `@tm/activity` anywhere under `www/` (comments only). depLint allowlist already permitted core→contract on main; canvas correctly consumes via core re-exports, no direct contract dep.
6. **runVitalsStore:** keyed by `run_id`, fed exclusively by the pure fold, data-only (zustand, no rendering), non-persisted, snapshot re-seeds after reconnect (tested).
7. **Hygiene:** all files well under guardrails (largest changed: `transport.ts` 512); barrel ordering alphabetical; JSDoc matches neighbors; no dead code beyond F5's comment.

## Findings JSON

```json
[
  {"file": "www/packages/canvas/src/infrastructure/stream/useSessionEventStream.ts", "line": 27, "summary": "Unmount no longer cancels in-flight gap backfill: render-epoch guard replaces the old effect-closure closed flag but never bumps on unmount, so onEvents fires after the pane is gone", "failure_scenario": "seq-gap event triggers listSessionEvents; pane closes mid-request; promise resolves with isCurrent() still true and dispatches the event batch into the consumer's store for an unmounted viewer (old code dropped it via closed=true)", "verdict": "CONFIRMED"},
  {"file": "www/packages/canvas/src/infrastructure/stream/useSessionEventStream.ts", "line": 92, "summary": "Removed setConnected(true) on gap-backfill success is an unacknowledged observable behavior change in a zero-change slice", "failure_scenario": "source errors while backfill in flight: old UI flipped connected back to true on backfill success, new stays false until next onopen; likely an improvement but unstated in commit/PR", "verdict": "PLAUSIBLE"},
  {"file": "www/packages/core/src/activityStreamEvents.ts", "line": 103, "summary": "Private isObject duplicates barrel-exported core isRecord with identical semantics", "failure_scenario": "two names for one predicate in the same package; next contributor imports one or the other and the pair drifts", "verdict": "CONFIRMED"},
  {"file": "www/packages/core/src/transport.ts", "line": 479, "summary": "DEFAULT_ACTIVITY_OWNER and activityStatuses zeroing duplicated across browser core and server activityRouter", "failure_scenario": "wire owner default or status membership changes on one plane only; server counts a status the browser never zero-seeds (or owners diverge) with no compile error", "verdict": "CONFIRMED"},
  {"file": "www/packages/core/src/useEventSource.ts", "line": 62, "summary": "biome-ignore useExhaustiveDependencies suppression is inert (rule never fires; core is not biome-linted) and misleads readers", "failure_scenario": "future reader assumes an exhaustive-deps violation exists and preserves or propagates the suppression; biome reports suppressions/unused if core ever gains a lint gate", "verdict": "CONFIRMED"}
]
```
