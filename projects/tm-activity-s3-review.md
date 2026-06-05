# Activity Slice 3 read surface — review (PR #228 `feat/activity-slice-3-read`)

Reviewer: `transport-matters:general:1:2.2` · xhigh recall · read-only
Scope: `git diff main...HEAD` (a419629), +685/-13, 17 files. Tree verified pristine before and after.
Gates observed green: `@tm/activity` test (120 passed / 8 skipped), `@tm/gateway` test (8 passed),
`@tm/activity` + `@tm/gateway` typecheck clean, shell `importGraphBoundary` (9 passed).

Verdict: **2 major, 2 minor.** No blockers to the owner-auth or SQL contract; the two majors are on
the SSE stream's delta delivery and process resilience.

---

## MAJOR 1 — SSE snapshot is captured before the subscription is registered; deltas emitted during snapshot materialization are lost (brief priority #2)

- File/symbol: `packages/activity/src/server/activityRouter.ts` › `createActivityRouter` (stream route handler)
  and `packages/activity/src/projections/workspaceActivity.ts` › `WorkspaceActivityProjections.listWorkspaceActivity` / `run`.
- Mechanism: the stream handler awaits `deps.reader.listWorkspaceActivity(workspaceId, owner)` to build the
  snapshot, writes the `snapshot` frame, and only THEN calls `subscribeWorkspaceActivity`. But
  `listWorkspaceActivity` itself materializes every run and subscribes each actor
  (`run()` → `actor.subscribe(...)`) inside `await Promise.all(summaries.map(run))`. While a later run awaits
  materialize, an earlier already-subscribed actor can advance and fire `store()` → `emit()`. At that moment no
  workspace listener is registered yet (the router subscribes afterward), so the emit reaches nobody. The
  snapshot returned to the router is the per-run projection captured at each `run()` call
  (`listWorkspaceActivity` returns the `projections` array), i.e. the pre-advance value.
- Failure scenario: run A materializes and subscribes; run B's materialize yields the event loop; an ingestion
  event advances run A to a terminal state (`run-exited`), emitting a delta that is dropped (no listener). The
  snapshot frame carries run A's stale pre-exit status. The router then subscribes; run A emits no further
  delta (terminal). The connected client shows run A's status permanently wrong for the life of the stream.
- Trigger is timing-dependent (an ingestion event must land during connect-time materialization), so PLAUSIBLE
  rather than deterministic; the ordering itself is the defect. Correct shape: subscribe first (or build the
  snapshot from the post-subscribe cache) so no emit falls in the gap, then de-dup. Note also the snapshot is
  built from the returned `items` rather than `projections.current(workspaceId)`, which would already be fresher.

## MAJOR 2 — Hijacked SSE socket has no `error` handler; a keepalive/delta write racing client disconnect can throw unhandled and crash the gateway process

- File/symbol: `packages/activity/src/server/activityRouter.ts` › `createActivityRouter` (stream route: the
  `setInterval` keepalive `reply.raw.write(": keepalive\n\n")` and `writeFrame(reply.raw, ...)` in the
  subscription callback).
- Mechanism: after `reply.hijack()` the handler owns the raw socket but never registers
  `reply.raw.on("error", ...)`. `cleanup` clears the interval and unsubscribes only on the `close` event. There
  is a window where the client disconnects, the socket breaks (EPIPE/ECONNRESET), a keepalive tick or a delta
  callback writes to it before `close` propagates, and `stream.write()` with no callback emits an `error` event
  on the socket. An unhandled socket `error` surfaces as an `uncaughtException`, which takes down the whole
  Fastify process and every other live stream with it.
- Failure scenario: a client aborts mid-stream; the 15s keepalive (or a concurrently-arriving delta) fires
  against the half-closed socket before the `close` listener runs → unhandled `error` → gateway crash.
- Trigger is a disconnect/write race so PLAUSIBLE, but the blast radius (shared gateway process) is why this is
  major. Remedy: attach an `error` handler on `reply.raw` that routes to `cleanup`, and/or guard writes on
  `reply.raw.writableEnded`/`destroyed`.

## MINOR 3 — Runs started after connect never surface on an open stream (owner-scope side effect + no re-materialization)

- File/symbol: `packages/activity/src/projections/workspaceActivity.ts` › `subscribeWorkspaceActivity`
  (the `scopedListener` gate against `ownerRuns`) and `listWorkspaceActivity` (which freezes `ownerRuns` and is
  the only path that materializes runs).
- Mechanism: `ownerRuns[owner,workspace]` is the set of run ids returned by the connect-time owner-scoped list
  query. The scoped listener drops any delta whose `runId` is not in that frozen set. Independently, a run
  created after connect is never materialized on this connection (only `listWorkspaceActivity`/`run` materialize
  and subscribe actors), so it would not emit at all. Either way, a newly-started run for the same owner does
  not appear on an already-open stream; the client must reconnect to see it.
- Cost: for a live "workspace activity" stream this is a functional gap. It reads as intended for a slice-3
  "runs known at connect" model, and the frozen set is a sound owner-gate (see Verified below — it prevents
  cross-owner leakage), but the new-run-invisibility behavior should be explicit in the contract/tests rather
  than incidental. Flagging so the contract owner can confirm it is in scope for slice 3.

## MINOR 4 — `rollup` round-trips usage wire → domain → wire on every delta

- File/symbol: `packages/activity/src/server/activityRouter.ts` › `rollup` / `usageFromWire` / `deltaFrame`.
- Mechanism: `deltaFrame` maps every current projection through `runToWire` and hands the wire items to
  `rollup`, which then converts each item's `total_usage` back to domain via `usageFromWire`, sums with
  `addUsage`, and converts once more via `usageToWire`. `usageFromWire` exists solely to undo a conversion the
  same function just performed. Per delta this is O(n) double conversion over all runs.
- Cost: wasted work and an extra converter to maintain. Simpler: accumulate over the domain `RunActivityProjection.totalUsage`
  values (already `UsageTotals`) and call `usageToWire` once for the rollup, dropping `usageFromWire`.

---

## Verified clean (traced, not assumed)

- **Owner auth enforced on both routes (brief #1).** `GET .../activity` and `.../activity/stream` both call
  `ownerFromQuery`; owner flows into `runsForWorkspace(..., owner)` → `RUNS_BY_WORKSPACE_SQL` `WHERE ... AND "s"."owner" = $3`.
  The `session` table has a real, populated `owner` column (migration `0001_session_store_foundation.py`
  `session_owner_ix ON "session" (owner, ...)`; `dao_statements.py` session INSERT lists `owner`; Python DAO is
  owner-scoped throughout), so the SQL gate is live, not a no-op. Owner is self-asserted via query param and
  defaults to `local` when omitted (empty string is rejected, 400) — this matches the blessed dialect and the
  Python `DEFAULT_OWNER`, so it is by design, not a defect.
- **No cross-owner leak on the shared stream.** `workspaceListeners` is workspace-global, but each owner's
  `scopedListener` forwards only run ids in that owner's SQL-gated `ownerRuns` set, so owner B's stream cannot
  receive owner A's run deltas.
- **Subscription lifecycle (brief #3).** `cleanup` is idempotent (`cleanedUp` guard), clears the keepalive
  interval, and unsubscribes; the trailing `if (cleanedUp) subscription.unsubscribe()` covers a close that
  races subscribe assignment. No subscriber/timer leak on normal close (the resilience gap is Major 2, a
  different failure mode).
- **Dialect conformance (brief #4).** `data:`-only frames (`writeFrame`), `: keepalive\n\n` comment every
  `ACTIVITY_STREAM_KEEPALIVE_MS = 15_000`, owner via query param, resume = `snapshot` then `delta` frames;
  tests assert no `event:`/`id:` lines. Conforms.
- **Boundary (brief #5).** Barrel exports only `createActivityRouter` + its three deps types; `ActivityIngestion`
  and `WorkspaceActivityProjections` stay unexported. Gateway imports `@tm/activity` via the bare barrel
  (resolves to the entrypoint), so `packageInternalViolations(ACTIVITY_SRC, ...)` stays green; `GATEWAY_SRC`
  assertion intact; boundary suite passes.
- **DRY/types (brief #6).** Reuses `RunActivityProjection`, `UsageTotals`, `addUsage`, `emptyUsage`,
  `ActivityStatus`/`activityStatuses`, `asWorkspaceId`; no parallel type definitions. `WorkspaceRunsSource`
  signature widened to `(workspaceId, owner)` and all callers/tests updated in lockstep.
- **§5.3 fields (brief #7).** `initial_prompt`, `last_message`, `context_tokens`, `since_ts`, `status` present
  on `ActivityWireRun` alongside harness/launch_kind/run_id/total_usage/exit_reason; raw bytes omitted.
- **Frozen contract (brief #8).** `pgContracts.ts` `run_lifecycle` block untouched; the only pgContracts change
  is adding `owner` to `SESSION_COLUMNS`, aligning the TS contract with the existing DB column. `www/` is
  untouched entirely (no boundary-test edit was even needed).
- **Test coverage (brief #9).** Exercises auth-denial (empty owner → 400 on both routes), keepalive framing,
  snapshot→data-only-delta ordering, and unsubscribe-on-close via `app.inject()` / real `fetch` + abort.

---

# Round 2 — re-verify of pushed fixes (commit `0ec74e7`, diff `a419629..HEAD`)

Tree verified pristine before and after; read-only. Delta touches 6 files
(`workspaceActivity.ts/.test.ts`, `activityRouter.ts/.test.ts`, `activityIngestion.ts`,
`gateway/app.test.ts`); `pgContracts.ts`, both barrels (`activity/index.ts`, `gateway/index.ts`),
and `www/` are untouched. Gates green: `@tm/activity` test 123 passed / 8 skipped (+3 new tests),
`@tm/gateway` test 8 passed, both typecheck clean, shell `importGraphBoundary` 9 passed.

Verdict: **all 4 findings closed. 2 new minor observations in the added live-refresh path.**

## MAJOR 1 — CLOSED
`createActivityRouter` stream route now subscribes BEFORE reading the snapshot. The subscription
callback buffers into `pending` while `snapshotSent === false`; the snapshot is built from
`deps.reader.currentWorkspaceActivity(...)` (the post-materialization cache), not the pre-advance
`listWorkspaceActivity` return. After the snapshot frame is written, `snapshotSent` flips and buffered
deltas flush, each de-duped against the snapshot via `sameRunActivityProjection`. Traced: the original
terminal-during-materialization loss is gone — that emit is buffered AND reflected in the cache the
snapshot reads from, so it is neither lost nor double-sent. Steps between the cache read and
`snapshotSent = true` are synchronous (no await), so no emit slips the gap. A `try/catch` around the
list unsubscribes on failure (no leak). Note: the router-level test (`FakeActivityBackend` whose
`currentWorkspaceActivity` always returns fresh items) would pass even without buffering, so it proves
the de-dup path more than the lost-delta close; the lost-delta close rests on the projection-layer
mechanism (cache-backed snapshot), which is sound. Not a defect, a test-strength note.

## MAJOR 2 — CLOSED
`reply.raw.on("error", cleanup)` is registered (before `writeHead`), and every write goes through
`safeWrite`, which returns early on `destroyed`/`writableEnded` and wraps `write` in try/catch,
calling `response.destroy()` on throw. Keepalive and delta writes both route through it. An error
event now lands on a listener (no `uncaughtException`), and a write racing disconnect is guarded.
The error handler is in place before the first write (snapshot) and before the keepalive interval
starts. No remaining unhandled-throw path on disconnect.

## MINOR 3 — CLOSED (highest-risk path, authorization traced)
Live pickup: `ActivityIngestion.markReconcileNeeded` now fires `reconcileListeners` for every NOTIFY
(before the un-materialized early-return, so brand-new runs count). `WorkspaceActivityProjections`
subscribes in its constructor and, on any reconcile, calls `refreshSubscribedWorkspaces` →
`refreshOwnerWorkspace` → `listWorkspaceActivity(workspaceId, owner)`, which re-runs the owner-scoped
SQL (`runsForWorkspace` → `WHERE "s"."owner" = $3`), rebuilds `ownerRuns`, and materializes the new
runs so they emit live. **Authorization is the owner-gated source, not a trusted event field** — the
NOTIFY carries only a runId (a trigger); the run is admitted only if the per-owner SQL returns it.
Cross-owner trace: a run started for owner B triggers a refresh for every active owner-workspace, but
owner A's refresh runs `listWorkspaceActivity(ws, A)` whose SQL excludes B's run, so B's runId never
enters `ownerRuns[A,ws]`; A's `scopedListener` and `currentWorkspaceActivity` both filter on that set,
so B's run cannot reach A's stream or snapshot even though it sits in the workspace-global cache.
Both required tests exist and genuinely assert: (a) "picks up a run started after stream subscription
through the owner-scoped source" adds the run only to the owner's source, fires reconcile, and asserts
the delta + `currentWorkspaceActivity`; (b) "does not leak a later owner B run onto owner A's open
workspace stream" adds the run only to owner B's source and asserts owner A sees zero deltas and empty
current while owner B sees it. `FakeRuns` is keyed by (owner, workspace), correctly modeling the gate.

## MINOR 4 — CLOSED
`usageFromWire` is deleted; `rollup` now takes `readonly RunActivityProjection[]` and sums
`item.totalUsage` / `item.contextTokens` directly, with a single `usageToWire` at the end.
`activityResponse` and `deltaFrame` pass domain projections to `rollup`. No round-trip remains.

## New minor observations (introduced by the round-2 refresh mechanism)

### N1 (minor, efficiency) — every NOTIFY refreshes every active stream, cross-workspace
`refreshSubscribedWorkspaces` iterates ALL `activeOwnerWorkspaces` and ignores the reconcile's runId,
so a NOTIFY for any run in any workspace triggers a full owner-scoped re-list + re-materialize for
every open stream, including unrelated workspaces. In-flight refreshes are deduped (`refreshes` map),
but load is still O(active_streams) SQL re-lists per NOTIFY system-wide. Partly inherent: a brand-new
runId cannot be mapped to a workspace/owner without querying, so some broad refresh is unavoidable for
discovery. Flagging the amplification as a scaling concern, not a correctness defect.

### N2 (minor, robustness) — refresh promise is voided with no rejection handler
`refreshSubscribedWorkspaces` does `void this.refreshOwnerWorkspace(key)`, and `refreshOwnerWorkspace`
chains `.then().finally()` with no `.catch()`. If `listWorkspaceActivity` rejects during a live refresh
(transient store error), the rejection is unhandled — a Node `unhandledRejection` (warning today, a
hard crash under `--unhandled-rejections=strict`). A `.catch` that logs/telemeters and clears the
`refreshes` entry would contain it. `WorkspaceActivityProjections.stop()` was added and unsubscribes the
reconcile listener, but nothing observed wires `stop()` into a shutdown path yet (out of this slice's
scope; noting for the lifecycle owner).

## Regressions checked — none
SSE dialect intact (`data:` frames + `: keepalive\n\n`, `safeWrite` preserves format, snapshot/delta
shapes unchanged). Barrels untouched (`activity/index.ts`, `gateway/index.ts` unchanged; new symbols
`sameRunActivityProjection`, `ActivityIngestionSubscription` are intra-package imports, not barrel
exports); internals still unexported; boundary suite green. `pgContracts.ts` `run_lifecycle` untouched.

## Round 3 — targeted confirm of N1 & N2 fixes (commit `7eef54a`, diff `0ec74e7..HEAD`)

Tree pristine before/after; read-only. Delta: Python writer + tmEvents parser + ports + projections +
router (+ tests). `pgContracts.ts`, both barrels, and `www/` untouched. Gates green: `@tm/activity`
126 passed / 8 skipped (+3 new tests), `@tm/gateway` 8 passed, both typecheck clean, boundary 9 passed,
Python payload-contract tests (`test_writer_notify_payload_is_small_session_range_handle`,
`test_run_lifecycle_notify_payload_uses_shared_contract`) pass on the repo venv (3.14.5).

### N1 — CLOSED (refresh now scoped by workspace/owner)
The NOTIFY payload was widened end to end so the refresh can route: `writer.py` `_notify_payload` adds
`owner`/`workspace_slug`/`workspace_hash` (session_events) and `_run_lifecycle_notify_payload` adds
`workspace_slug`/`workspace_hash`; `tmEvents.ts` parses them into `SessionEventsPayload`/
`RunLifecyclePayload` (`owner?`, `workspaceId?` optional in `ports.ts`); `onReconcile` and
`ActivityIngestion.markReconcileNeeded` now forward the whole payload. `refreshSubscribedWorkspaces`
skips any active owner-workspace where `activeOwnerWorkspaceMatches` is false: a session_events NOTIFY
(carries both workspaceId and owner) refreshes only the matching (workspace, owner) stream; a
run_lifecycle NOTIFY (workspace only) refreshes that workspace's owners; a bare runId or absent metadata
falls through to refresh-all. Correct failure mode: undefined metadata OVER-refreshes (never misses a
live pickup), and authorization still runs inside `listWorkspaceActivity`'s owner-scoped SQL, so the
scoping decision cannot create a cross-owner leak. First event of a brand-new run carries the routing
metadata (the session row has owner/workspace), so live pickup is not lost. Test "refreshes only the
owner and workspace named by the NOTIFY payload" asserts exactly one scoped `runsForWorkspace` call and
no refresh of the unrelated workspace. Payload-size guard (<8000 bytes, no raw/ir) still asserted.

### N2 — CLOSED (refresh rejection handled, cannot become unhandled)
`refreshOwnerWorkspace` now chains `.catch((error) => this.emitRefreshError(key, error))` before
`.finally`, so the stored `refresh` promise resolves rather than rejects — no unhandled rejection path.
`emitRefreshError` fans out to per-stream `errorListeners` (each wrapped in try/catch so a faulty
subscriber cannot re-open the hole) and no-ops if the active entry was already removed. The router wires
`handleRefreshError` as the new 4th `subscribeWorkspaceActivity` arg: it records the error, runs
`cleanup` (clears keepalive, unsubscribes), and `reply.raw.destroy()` if already hijacked; a refresh
error that fires during the initial list is re-thrown after the await (`if (refreshError !== undefined)
throw refreshError`) into the existing unsubscribe+500 path. Tests: projection-layer "routes live
refresh failures to the subscriber without unhandled rejection" registers a `process.on(
"unhandledRejection")` probe, forces a store failure, and asserts the error reaches the subscriber with
`unhandled === []`; router-layer "cleans up the stream when a live refresh reports an error" asserts the
stream unsubscribes on `emitRefreshError`.

### Regressions — none
Owner gate intact (matches() only gates WHETHER to refresh; the owner-scoped SQL remains the
authorization; round-2 cross-owner no-leak test still present and green). SSE dialect unchanged
(`safeWrite`/`data:`/keepalive untouched). Boundary green; new symbol
`WorkspaceActivityRefreshErrorListener` and widened `TmEventsPayload` are intra-package/existing-barrel,
no new public surface. `pgContracts.ts` `run_lifecycle` untouched (the widened NOTIFY payload lives in
`ports.ts` as backward-compatible optional fields, not the frozen table contract).

Round-3 verdict: **clean — both N1 and N2 closed, no regressions.**
