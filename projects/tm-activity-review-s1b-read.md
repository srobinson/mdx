# Activity slice 1b-read — review-driven fixes (Opus)

Branch: `feat/activity-slice-1b-read` · date 2026-07-04 · scope: `packages/activity/` only.
Roles reversed: Opus implemented the fixes for its own /code-review + /code-hygiene findings; Codex reviews the delta.

## Correctness fixes applied (one line per fix)
- `tmEvents.ts`: registered a pg `'error'` listener + error-driven reconnect loop — an unhandled `'error'` on the long-lived LISTEN client crashed the process on any connection drop (mirrors the Python `listen.py` reconnect owner).
- `tmEvents.ts`: also handle the pg `'end'` event through the same `recoverFromDisconnect` reconnect path — a server-side close that emits `'end'` without an `'error'` would otherwise silently stall delivery (the failure the reconnect was meant to prevent).
- `tmEvents.ts`: `stop()` guards `UNLISTEN` with `.catch(...)` before `end()` — a rejecting UNLISTEN on a dead connection previously skipped `end()` and leaked the socket.
- `tmEvents.ts`: `start()` now guards on a synchronous `connecting` flag — concurrent `start()` calls previously double-connected, double-dispatched, and leaked the first client.
- `tmEvents.ts`: notifications dispatched through a serialized promise queue — fire-and-forget dispatch delivered records out of arrival order when reads resolved out of order.
- `tmEvents.ts`: `onError` wrapped in `emitError` so a throwing handler can neither poison the queue nor raise an unhandled rejection.
- `tmEvents.ts`: unknown payload types explicitly ignored (parse → `undefined` → no handler); confirmed by test.
- `postgresRecords.ts`: both record queries now filter `kind = 'turn'` — meta rows were fed to the transcript parser and produced spurious records; matches the session store's own `kind='turn'` read queries (`dao_statements.py`).
- `pgContracts.ts`: added `EVENT_COLUMNS.kind` + `EVENT_KIND_TURN` const as the single owner of the filter value; shared `EVENT_KIND_TURN_FILTER` fragment reused by both queries (no duplication).

## Contract parity confirmed against merged Python on main
- `run_lifecycle_event` columns (migration `0007`) match the lifecycle reader; `event_type ∈ {run-started, run-exited}` (`run_lifecycle_contracts.py`).
- NOTIFY payload keys match the parser: `session_events {session_id, run_id, first_seq, last_seq}`, `run_lifecycle {run_id}` (`writer.py`).
- `event.raw` is harness-native `dict(record)` for both TURN and META (`ingest.build_event`); the `kind` column drives the turn/meta split, so the new filter is correct.
- Reader event/session columns match the `0001` foundation schema.

## Boundary / conventions verified
- node-postgres stays on the `./server` export subpath; the `.` barrel (`src/index.ts`) remains IO-free (untouched).
- No XState import in these adapters. Mapping via slice-1a `transcriptRecords`, consts via `server/pgContracts`, DTOs via `ports.ts` — nothing re-declared.

## Deferred (not correctness / out of scope)
- Missing index on `event.run_id` (full-run replay seq-scans the event table): requires an `api/migrations` change, outside `packages/activity/` — flag for a follow-up migration.
- Lifecycle `seq` ordering (ts-primary) + positional seq on partial writes: low/theoretical; left as chronological with deterministic event-type tiebreak.
- `run_id = $4` in the range query: harmless no-op in practice; left in place.
- `jsonCoerce.ts` coercion consolidation (hygiene): deferred to after these fixes merge, per the hygiene refactor map.

## Tests added (TDD, RED → GREEN)
- `postgresRecords.test.ts`: both record queries assert `"kind" = 'turn'`.
- `tmEvents.test.ts`: concurrent-`start` single connection; reconnect + re-LISTEN after `'error'`; reconnect after `'end'` without an error; `stop()` closes client when UNLISTEN rejects; unknown payload ignored; queue survives a throwing handler; serialization invariant (a later notification's read does not start until the earlier read completes).
- Reconnect tests use vitest fake timers (`runAllTimersAsync`) and the serialization test uses explicit promise gates — no wall-clock delays, so the suite is deterministic (verified stable over repeated runs).

## Known limitations (deliberate, for reviewer awareness)
- `start()` fails fast if the initial connect throws (caller sees the error); only an already-established connection self-heals. Established-drop recovery is the failure mode the reconnect targets.
- Reconnect uses a fixed delay (default 250 ms) with unbounded retries, matching the Python `listen.py` precedent — no exponential backoff or attempt cap.
- The crash-on-drop fix is verified by mechanism + a fake client, not driven against a real Postgres connection loss (gate is typecheck + vitest).

## Codex review round (0 blockers, 1 major, 1 minor) — both addressed
- MAJOR (accepted, fixed): `stop()` could not stop a connection still opening — `openClient` stored `this.client` only after `connect()`+`LISTEN`, so `stop()` during that window did nothing and the client went live afterward. Fix: track the in-flight open as a shared `opening` promise that `stop()` awaits, and re-check `closing` after `LISTEN` so a client finishing post-`stop()` tears itself down (UNLISTEN+end) instead of storing. The shared `opening` promise also replaces the `connecting` flag, so concurrent `start()` callers now observe the real startup result. New TDD test: "tears down a connection that finishes opening after stop()".
- MINOR (accepted, fixed): relocated IO-free contracts to `ports.ts` — `RecordSeqRange`, `SessionEventsPayload`, `RunLifecyclePayload`, `TmEventsPayload`, the dispatch types, and `TmEventsActivityReader`. They now export from the root `.` barrel. This is required, not just tidy: the shell `importGraphBoundary` test forbids external product-plane code from importing `@tm/activity/server` or any internal path, so slice-2 machine wiring can only reach these contracts via the root barrel. node-postgres client types and `TmEventsActivityListener` stay in the server adapter.
- Judgment call flagged: `ports.ts` now imports the discriminant constants from the pure, IO-free `server/pgContracts` leaf (reusing the const beats re-declaring the literal and risking drift). Acyclic, no node-postgres pulled into the root barrel. If we later want `ports` to not import from `server/`, the follow-up is relocating the pure `pgContracts` constants to a neutral module — out of scope for this slice.
- Codex contract checks (channel, notify keys, lifecycle/event columns, ingest raw+kind, kind='turn' filter, unknown-payload handling, pg confinement, no XState) all passed independently.

## Gate
`pnpm --filter @tm/activity typecheck && pnpm --filter @tm/activity test` → green (53 passed, exit 0). Cross-package `@tm/shell importGraphBoundary` → green (6 passed) after the export-surface reshape.

## Follow-up task: extract @tm/common (foundational package)
- Created `packages/common` as `@tm/common`, a FOUNDATIONAL package (not a bounded context): just `package.json`, `tsconfig.json`, `src/index.ts` (barrel), `src/primitives.ts`, `src/primitives.test.ts`. No domain/service/ports/adapters/server layering. Wired into the pnpm workspace (auto-globbed by `packages/*`, dep linked via `pnpm install`) and into `just check`/`just test`.
- Moved the 6 generic throwing coercions (`nullableString`, `optionalString`, `requiredString`, `optionalInteger`, `requiredInteger`, `timestampString`) out of `postgresRecords.ts` into `@tm/common`. Domain coercions (`workspaceId`, `runLifecycleEventType`, `launchKind`) stay in activity.
- Reconciled the duplicate: `tmEvents.ts` had its own non-throwing `optionalInteger` (INVALID_INTEGER sentinel) + `nonEmptyString` equivalent (`stringValue`). Resolved into a `@tm/common` safe family without changing behavior: throwing `requiredInteger`/`optionalInteger` (reader still throws on bad rows) plus `safeInteger` (listener never throws — returns `null` for absent, `undefined` for malformed, replacing the Symbol sentinel) and `nonEmptyString`. Both adapters import from `@tm/common`; no coercion helper remains in activity.
- Added `@tm/common` to the import-graph boundary discipline: generalized the activity-internal enforcement to a parameterized `packageInternalViolations(src, entrypoint)` and added a common-internals test; asserted `@tm/common` resolves and `@tm/common/primitives` fails closed. Only `@tm/common`'s `index.ts` is importable by other packages.
- Wrote `packages/AGENTS.md` (imported by `packages/CLAUDE.md`): documents `@tm/common` as the home for cross-cutting primitives, the CONTEXT vs FOUNDATIONAL package distinction, and the "second consumer means it belongs in @tm/common, not copied" rule.
- Gate: `just check` green (all typechecks + api ruff/mypy) AND `pnpm -r test` exit 0 — @tm/common 9, activity 53, shell 1190, desktop 49, all JS packages green.
