# Activity Slice 1b Read Review

Scope: uncommitted `git diff main -- packages/activity` on `feat/activity-slice-1b-read`.

Verdict: issues. Counts: 0 blockers, 1 major, 1 minor.

## Major

1. `packages/activity/src/adapters/tmEvents.ts:TmEventsActivityListener.stop` cannot stop a connection that is still opening.

Evidence:

- `TmEventsActivityListener.stop` releases only `this.client` at lines 129-136.
- `TmEventsActivityListener.openClient` does not assign `this.client` or `this.listeners` until after both `connect()` and `LISTEN` finish at lines 149-158.
- `TmEventsActivityListener.reconnect` has the same in-flight window at lines 194-204.

Concrete failure scenario:

If shutdown, route disposal, or a test calls `stop()` while `start()` is still awaiting `client.connect()` or `client.query("LISTEN ...")`, `releaseClient()` returns `undefined`, `stop()` returns, then `openClient()` completes and stores an active client while `closing` is already true. That leaves a live `LISTEN tm_events` connection after the listener was stopped. The same race exists during reconnect if `stop()` lands while the replacement client is opening.

Fix:

Track the in-flight open operation and make stop wait for or cancel it, or assign the client/listeners before the awaits so `releaseClient()` can tear them down. Also check `this.closing` after `connect()` and after `LISTEN`; if closing became true, detach listeners, `UNLISTEN`, end the client, and do not store it. A shared `startPromise` would also make concurrent `start()` callers observe the real startup result instead of one caller returning early.

## Minor

2. Listener DTOs and range contracts are adapter-owned instead of port-owned.

Evidence:

- `packages/activity/src/adapters/postgresRecords.ts:RecordSeqRange` is declared in the Postgres adapter at lines 32-37.
- `packages/activity/src/adapters/tmEvents.ts:SessionEventsPayload`, `RunLifecyclePayload`, dispatch DTOs, and `TmEventsActivityReader` are declared in the listener adapter at lines 13-47.
- `packages/activity/src/server/index.ts` re-exports those adapter DTOs at lines 1-20.
- The brief's reuse rule says DTOs should go through `ports.ts`.

Concrete failure scenario:

Slice 2 machine wiring needs the same payload, range, and dispatch vocabulary, but the only exported definitions live behind the server adapter surface. Product-plane code either imports server types, pulling product code toward IO ownership, or re-declares equivalent DTOs and risks drift from the reader/listener contract.

Fix:

Move IO-free DTOs and source-facing interfaces to `packages/activity/src/ports.ts`: `RecordSeqRange`, `SessionEventsPayload`, `RunLifecyclePayload`, `TmEventsPayload`, dispatch types, and the reader interface. Keep node-postgres client types and `TmEventsActivityListener` in the server adapter path.

## Contract Checks

- `tm_events` channel matches Python: `api/src/transport_matters/session/listen.py:NOTIFY_CHANNEL` line 22 and `packages/activity/src/server/pgContracts.ts:TM_EVENTS_NOTIFY_CHANNEL` line 1.
- Session notify payload keys match Python writer: `api/src/transport_matters/session/writer.py:_notify_payload` lines 279-289 emits `type`, `session_id`, `run_id`, `count`, `first_seq`, `last_seq`; `packages/activity/src/adapters/tmEvents.ts:sessionEventsPayload` lines 279-292 reads the required keys and safely ignores `count`.
- Lifecycle notify payload type matches Python: `api/src/transport_matters/session/run_lifecycle_contracts.py` line 3 and `packages/activity/src/server/pgContracts.ts` line 3 both use `run_lifecycle`. The Python writer also emits `event_type` and `ts` at `writer.py:_run_lifecycle_notify_payload` lines 292-299; the TS listener ignores those and re-reads by `run_id`, which is acceptable for the current full-run lifecycle source.
- `run_lifecycle_event` read columns match the migration for the fields used by `RunLifecycleFact`: migration lines 29-42 define `run_id`, `event_type`, `ts`, `workspace_slug`, `workspace_hash`, `harness`, `launch_kind`, `exit_reason`, `exit_code`, `error`; TS reads those at `packages/activity/src/adapters/postgresRecords.ts:LIFECYCLE_BY_RUN_SQL` lines 256-276. The migration also has `space_id`, `worktree_id`, and `session_id`, which this DTO does not currently expose.
- Transcript event reader matches ingest shape: `api/src/transport_matters/session/ingest.py:build_event` lines 123-139 writes `session_id`, `seq`, `kind = turn`, `run_id`, `harness`, `ts`, and `raw`; TS selects those at `packages/activity/src/adapters/postgresRecords.ts:RECORD_SELECT_COLUMNS` lines 217-228 and filters `kind = 'turn'` at lines 206-208 and 244-253.
- Seq range query uses inclusive `[first_seq..last_seq]` plus `session_id` and `run_id` bounds at `packages/activity/src/adapters/postgresRecords.ts:RECORDS_BY_SESSION_RANGE_SQL` lines 244-254.
- Unknown payload types are ignored gracefully at `packages/activity/src/adapters/tmEvents.ts:parseTmEventsPayload` lines 271-276 and covered by `tmEvents.test.ts` lines 252-277.
- `pg` imports are confined to adapter/server test code in the scanned paths; the root package barrel does not import node-postgres. No XState import appears in the changed adapters.

## Limitations Assessment

- Fail-fast initial connect is a gap relative to the Python precedent if parity was intended. `api/src/transport_matters/session/listen.py:SessionEventListener._run` retries `_listen_forever()` after any initial or later failure with `reconnect_delay_s = 0.25` at lines 96-146. The TS listener retries after established connection loss, but `start()` throws on initial `openClient()` failure and does not schedule reconnect. This is acceptable only if the product wants startup to fail loudly when Postgres is unavailable.
- Fixed 250 ms unbounded reconnect delay is precedent-backed by `listen.py` lines 96-146.
- Crash and reconnect behavior is verified by mechanism and fakes in `packages/activity/src/adapters/tmEvents.test.ts`, not by a real Postgres listener. That is acceptable for this product-plane read slice, with one missing race test for stop during open.

## Verification

- Read-only review only. No build or typecheck run, matching code-review guidance and the frozen-tree constraint.
- Baseline `git status --short` before artifact write showed only the slice changes: `packages/activity/package.json`, six new adapter/test files, `ports.ts`, `server/index.ts`, `server/pgContracts.ts`, and `pnpm-lock.yaml`.

## @tm/common round

Verdict: clean. Counts: 0 blockers, 0 majors, 0 minors.

No new issues found in the `@tm/common` extraction round.

## Evidence

- Behavior preservation, `safeInteger`: `packages/common/src/primitives.ts:safeInteger` lines 53-57 returns `null` for absent `null` or `undefined`, the integer for integer numbers, and `undefined` for present malformed values. `packages/activity/src/adapters/tmEvents.ts:sessionEventsPayload` lines 273-288 checks `firstSeq === undefined || lastSeq === undefined` before constructing the payload, so malformed values still reject the payload. `dispatchTmEventsPayload` lines 240-263 only sees accepted payloads and uses strict `=== null` for absent bounds, so absent bounds still produce an empty record dispatch while malformed bounds are ignored before dispatch.
- Listener safety on bad payloads: `parseTmEventsPayload` lines 265-270 and `jsonRecord` lines 299-309 return `undefined` for malformed JSON, non object payloads, unknown types, and rejected payload shapes. There is no throwing coercion in the untrusted listener payload path.
- Reader throwing behavior: `packages/activity/src/adapters/postgresRecords.ts` imports the throwing trusted input primitives from `@tm/common` at lines 1-8. Event and lifecycle row mapping still uses `requiredString`, `requiredInteger`, `optionalInteger`, `optionalString`, `nullableString`, and `timestampString` at lines 109-145, so malformed database row strings, integers, and timestamps still surface as errors.
- Full migration: `rg` found no Activity definitions of `requiredString`, `optionalString`, `nullableString`, `requiredInteger`, `optionalInteger`, `timestampString`, `safeInteger`, `nonEmptyString`, or the old `INVALID_INTEGER` sentinel. The only Activity local coercions left are domain specific `workspaceId`, `runLifecycleEventType`, `launchKind`, plus JSON object parsing for the listener.
- Boundary fail closed: `www/packages/shell/src/testSupport/importGraphBoundary.test.ts` includes red cases for `@tm/common/primitives` and `@tm/common/src/primitives` at lines 41-66, and an allowed root import for `@tm/common` at lines 68-94. It also adds `packageInternalViolations(COMMON_SRC, COMMON_ENTRYPOINT)` at lines 100-102. `importGraph.ts:workspacePackageCandidate` resolves through package `exports` and returns an unresolvable `__unexported__` candidate for undeclared subpaths, so deep imports fail closed rather than resolving the on disk file.
- Foundational purity and shape: `packages/common/src/primitives.ts` has no imports and carries only `unknown` to typed primitives. `packages/common/src/index.ts` is the only public barrel. `packages/common` has no `domain`, `service`, `ports`, `adapters`, `projections`, or `server` directories. `packages/AGENTS.md` accurately documents the foundational package rule and the two coercion families.
- Scope note: `git diff main -- packages/common packages/activity/src/adapters packages/activity/package.json packages/AGENTS.md www/packages/shell justfile` omits the currently untracked `packages/common`, `packages/AGENTS.md`, and `packages/CLAUDE.md` files. I reviewed them from the live working tree via `git status --short`, `rg --files`, `find`, and direct file reads.
