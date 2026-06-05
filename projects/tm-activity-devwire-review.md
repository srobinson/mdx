# Review — PR #229 `feat/activity-gateway-dev-wiring`

- Scope: +404/-17, 5 files (`packages/activity/src/gatewayDeps.ts`, `packages/activity/src/gatewayDeps.test.ts`, `packages/activity/src/index.ts`, `packages/gateway/src/main.ts`, `packages/gateway/src/main.test.ts`).
- Head reviewed: `ff25641` on `feat/activity-gateway-dev-wiring`; working tree verified pristine before and after.
- Gate: `@tm/activity` typecheck clean + 128 passed / 9 skipped; `@tm/gateway` typecheck clean + 12 passed. Green.
- Verdict: **1 major, 1 minor.** Lifecycle, boundary, fallback, and no-`pg`-in-gateway all otherwise correct.

---

## MAJOR

### M1 — `pg.Pool` created without an `'error'` listener; an idle-connection failure crashes the gateway
- File + symbol: `packages/activity/src/gatewayDeps.ts` → `createActivityGatewayDeps` (the `new pg.Pool({ connectionString })` construction).
- Defect: the pool is created and handed to `PostgresActivityReader` (used only via `.query`), but no `pool.on("error", ...)` handler is ever attached — grep confirms the only `.on("error")` sites are `TmEventsActivityListener` (its `Client`) and the SSE `reply.raw`, never the pool.
- Failure scenario: gateway boots with `TRANSPORT_MATTERS_DATABASE_URL` set and serves for a while. An **idle** pooled connection's backend dies — postgres failover/restart, `pg_terminate_backend`, a cloud provider idle-connection cull, or a network partition. node-postgres re-emits that error as an `'error'` event on the `Pool`. With no listener attached, Node treats it as an unhandled `'error'` emitter event and terminates the process. The gateway crashes on a routine infra event that the pool would otherwise absorb by discarding and replacing the dead client.
- Why tests miss it: both unit tests mock `pg.Pool.prototype.end` and never drive a live idle-client error, so the crash path is unexercised.
- Asymmetry worth noting: the sibling `TmEventsActivityListener` deliberately attaches `client.on("error", ...)` plus a full reconnect loop (`packages/activity/src/adapters/tmEvents.ts`, `openClient`/`recoverFromDisconnect`). The listener connection is resilient; the reader pool is not. The factory owns both and should give both the same resilience.
- Suggested fix: in the factory, attach `pool.on("error", ...)` routing to the existing `ActivityTelemetry`/logger (a swallow-and-log is enough; the pool self-heals the connection). Keeps the crash off the process while surfacing the event through the same doctor telemetry the rest of Activity uses.

---

## MINOR

### m1 — Cross-package duplication of the error-aggregating sequential-close primitive
- File + symbol: `packages/activity/src/gatewayDeps.ts` → `closeResources` and `packages/gateway/src/main.ts` → `closeGatewayResources` / `captureClose`.
- Defect: both implement the identical primitive — run a sequence of async close thunks, collect thrown errors, then `if (errors.length === 1) throw errors[0]; if (errors.length > 1) throw new AggregateError(errors, ...)`. The tail is byte-identical modulo the message string; only the shape differs (array-of-thunks vs two explicit `captureClose` calls).
- Cost / rule: this is a domain-free cross-cutting primitive now needed by two packages. `packages/AGENTS.md` (`@tm/common is the home for cross-cutting primitives`): "The moment a primitive is needed by a second package it belongs in `@tm/common`, not copied. Duplication across packages is a defect." Also user `~/.claude/CLAUDE.md` DRY ("zero tolerance"). Two copies must be kept in sync; a future change to close/aggregation semantics has to be made twice.
- Suggested fix: extract e.g. `closeAll(thunks: readonly (() => Promise<unknown> | undefined)[]): Promise<void>` into `@tm/common` and call it from both the factory `close()` and `closeGatewayResources`.

---

## Nit / hardening (no current trigger — informational)

### n1 — Pool/listener constructed before the only cleanup guard
- File + symbol: `packages/activity/src/gatewayDeps.ts` → `createActivityGatewayDeps` (construction block preceding the `try { await listener.start() }`).
- Observation: `close()` is only invoked if `listener.start()` throws. The `pool`, `projections` (which registers an ingestion subscription in its constructor), and `listener` are all built *before* the `try`. If any constructor in that window ever threw, the pool would be built but never closed → connection leak.
- Current status: **not triggerable today.** All constructors there are field assignments; `WorkspaceActivityProjections` only adds a listener to a `Set`, and `ingestion.handlers()` returns an object literal. `new pg.Pool` does not connect eagerly and does not validate the connection string at construction. So no live leak.
- Directly answers the brief's "any path where the pool/listener leaks (built but never closed)?": the guarded path (listener startup failure) is handled correctly and releases everything in reverse-construction order; this construction window is the only structurally-unguarded region and is inert today. Optional hardening: wrap construction+start in one try that runs `close()` on any failure, so a future throwing constructor cannot leak.

---

## Verified clean (evidence for the weighted brief points)

1. **Resource lifecycle (highest).** Factory `close()` runs `listener.stop → projections.stop → ingestion.stop → pool.end` — exact reverse of construction (`pool → … → projections → listener`). Idempotent via a `closed` flag (double-close test passes). Startup-failure path inside the factory calls `close()` and re-throws (wrapping in `AggregateError` only if close itself throws). `TmEventsActivityListener.stop()` is a safe no-op when `start()` failed (client never assigned, `releaseClient` returns undefined, early return), so cleanup after a failed start does not throw or leak. Gateway side: `closeGatewayResources` closes `app` then `activityDeps` (correct order; test asserts `["app.close","activity.close"]`), invoked on both SIGINT/SIGTERM (`installShutdownHandlers`, guarded by `shuttingDown`) and startup failure (`closeAfterStartupFailure`).
2. **Boundary preserved.** `packages/activity/src/index.ts` exports only `createActivityGatewayDeps` + `ActivityGatewayDeps`/`ActivityGatewayDepsConfig` types. `ActivityIngestion`, `WorkspaceActivityProjections`, `PostgresActivityReader`, `TmEventsActivityListener` remain unexported. `packages/gateway/src/main.ts` imports only from the `@tm/activity` barrel (no deep imports). The test file's relative imports of internals are intra-package (for spying), not a boundary crossing.
3. **Graceful fallback.** `resolveActivityDeps`: absent/empty `TRANSPORT_MATTERS_DATABASE_URL` → `runtime.warn("… is not set; gateway serving health only")` and returns undefined → `buildGateway` mounts no activity (health-only, bootable). Present → factory builds deps → mounted under `/v1` (`ACTIVITY_CONTEXT_PREFIX` in `app.ts`; end-to-end `/v1/.../activity` inject proven in the untouched `app.test.ts`). Health-only test asserts the warning and that the factory is not called.
4. **No `pg` in gateway.** `packages/gateway/package.json` deps: `@tm/activity`, `@tm/common`, `fastify` only. The pool lives entirely inside the factory in `@tm/activity`.
5. **Regression.** Diff touches exactly the 5 listed files; nothing under `www/`, `canvas/`, `docs/`, or `pgContracts`. `run_lifecycle` contracts untouched.
6. **Tests exercise.** `close()` releases + idempotent (double-`close` order assertion) and startup-failure cleanup: yes. Health-only fallback + warning: yes. Activity-mounts-with-injected-deps: process→build wiring proven in `main.test.ts`; the actual `/v1` HTTP mount via `app.inject()` proven at the app layer in `app.test.ts` (correct layer split, not a gap). A `pg` smoke suite is present and `skipIf`-gated on `TRANSPORT_MATTERS_TEST_DATABASE_URL`.

---

# Re-verification — delta `ff25641..3aac580` (`3aac580 fix(activity): handle gateway dependency review`)

Scope: engineer's fix commit only. Tree verified pristine at `3aac580` before and after. Gate re-run green: `@tm/common`/`@tm/activity`/`@tm/gateway` typecheck clean; tests `@tm/common` 12, `@tm/activity` 129 passed / 9 skipped (+1 new idle-pool-error test), `@tm/gateway` 12.

## M1 (MAJOR) — CLOSED
- `packages/activity/src/gatewayDeps.ts` → `createActivityGatewayDeps` now attaches `pool.on("error", (error) => { if (closed) return; telemetry.poolIdleClientError(error); })` immediately after pool creation. An idle-client `'error'` now has a listener, so Node no longer treats it as unhandled → no process crash.
- Coexists cleanly with `close()`: the `let closed` flag was hoisted above the handler and is shared with `close()` (which sets `closed = true` before tearing down). So pool `'error'` events during and after shutdown are suppressed (no double-handling, no log noise during `pool.end()`), while a genuine `pool.end()` rejection still propagates through `closeAll` to the caller (not swallowed).
- New telemetry method `ActivityTelemetry.poolIdleClientError` routes to the same `logger.warn` surface as the other doctor telemetry; `ActivityTelemetry` remains unexported from the activity barrel.
- Test `handles idle pool errors without crashing the process` proves: the `error` listener is registered; `pool.emit("error", ...)` does not throw and calls `poolIdleClientError`; after `close()`, a further emit neither throws nor re-invokes telemetry (the `closed` guard). No remaining unhandled pool/resource error path.

## m1 (MINOR, DRY) — CLOSED
- `packages/common/src/closeAll.ts` is the single home for the error-aggregating sequential-close primitive (`closeAll(resources, aggregateMessage?)`), exported from the `@tm/common` barrel with its `CloseResource` type. Own unit suite `closeAll.test.ts` covers order, single-error rethrow, and multi-error `AggregateError`.
- Both consumers now call it: `gatewayDeps.ts` `close()` → `closeAll([...], "failed to close Activity resources")`; `main.ts` `closeGatewayResources` → `closeAll([...], "failed to close gateway resources")`.
- The two parallel copies are gone: `closeResources` (activity) is deleted entirely; `captureClose` (gateway) is deleted; `closeGatewayResources` remains only as a one-line domain composition (orders `app` before `activityDeps`) delegating aggregation to `closeAll` — no re-implementation.

## Regression — intact
- Boundary: activity barrel unchanged; `ActivityIngestion`/`WorkspaceActivityProjections`/`PostgresActivityReader`/`TmEventsActivityListener`/`ActivityTelemetry` still unexported.
- Graceful health-only fallback: `resolveActivityDeps` not in the delta (untouched).
- `run_lifecycle` pgContracts: not in the delta (untouched). Delta touches only `gatewayDeps.ts(+test)`, `telemetry.ts`, `common/closeAll.ts(+test)`, `common/index.ts`, `gateway/main.ts`.

## New nit (introduced by the fix) — n2, cosmetic, non-blocking
- Indent inconsistency: the new `packages/common/src/closeAll.ts` (12 tab-indented lines), `closeAll.test.ts` (52), and the reworked `packages/common/src/index.ts` export block (8) use **tab** indentation, while the sibling `packages/common/src/primitives.ts` (2-space) and the entire `packages/*` Node tree are **2-space**.
- No gate catches it: lefthook's biome lint globs `www/**` only, so `packages/*` is not biome-governed; typecheck/tests are indent-agnostic. It will persist and drift silently.
- Rule: user `~/.claude/CLAUDE.md` "Consistency: does it match the surrounding conventions". Fix: normalize the three files to 2-space (or, better, add a biome config covering `packages/*` so this can't recur).

