# Slice 5 review (claude family) — PR #267 `realtime-slice5-empty-at-spawn`

**Verdict: clean.** No blocking, major, or minor findings. All CI gates green on the PR head (backend lint/test/package, frontend, desktop, e2e, product-plane). Main working tree verified pristine before and after review; all experiments ran in a scratchpad clone against the local test Postgres (55432).

## 1. Owner-scope leak — proven closed

Predicate: `COALESCE(s.owner, l.owner) = $3` over `LEFT JOIN session`.

- A lifecycle-only run for owner A cannot surface for owner B: join miss yields `s.owner = NULL`, `COALESCE` falls to `l.owner`, which is `NOT NULL DEFAULT 'local'` post-0010 (harness DDL matches), so equality is strict. No `NULL = NULL` vector. `session.owner` is itself `NOT NULL` (migration 0001), so the fallback fires only on a true join miss, never on a null-owner session.
- The live NOTIFY path cannot bypass the gate: `WorkspaceActivityProjections` admission only schedules `refreshOwnerWorkspace` → `listWorkspaceActivity` → the same owner-scoped SQL. The `payload.owner` check in `activeOwnerWorkspaceMatches` is a fan-out optimization, not the gate. `tmEvents.runPayloadIdentity` already parsed `owner`; the payload now carries it (writer change verified).
- Mutation checks (scratchpad clone, real Postgres; CI runs these — `ci.yml` sets `TRANSPORT_MATTERS_TEST_DATABASE_URL` with a pg service):
  - **Predicate dropped** (`COALESCE(...) = $3` → `$3 = $3`): 4 tests fail, including `surfaces a lifecycle-only run as starting and keeps it owner scoped` and `uses the session owner once the first session exists`. Red test is real.
  - **Predicate weakened** to `l.owner = $3`: 2 tests fail (`uses the session owner once the first session exists` + the SQL-shape unit test). Session-owner authority is pinned.
  - Baseline: 249/249 pass.

## 2. LEFT JOIN correctness

- One row per run is structural: `GROUP BY run_id`; every aggregate is `max`/`bool_or` (duplication-idempotent), exit fields `FILTER (WHERE run-exited)`. The multi-lifecycle × multi-session cardinality test passes and asserts exactly one summary with correct exit fields.
- `PRIMARY_SESSION_FILTER` is vacuously true on null-session rows: `s.parent_session_id` is NULL, the correlated `NOT EXISTS` equality never matches. Confirmed analytically and empirically (lifecycle-only run surfaces in the baseline test; it could not if the filter rejected null rows).
- **Mutation: LEFT JOIN → INNER JOIN**: 4 tests fail, including `re-lists a lifecycle-only starting run after a dropped NOTIFY` and `returns exactly one run before and after its first session row`. Red tests are real.

## 3. Migration 0010

- Correct next number (`0009_run_live_status` → `0010_run_lifecycle_owner`), style matches 0009 (imports app contract constants, f-string DDL). New-column-only, `text NOT NULL DEFAULT 'local'`, zero data loss; downgrade drops the column only. `test_run_lifecycle_owner_migration_backfills_and_downgrades` inserts a pre-0010 legacy row, upgrades, asserts backfill `'local'`, downgrades, asserts the row survives. `_assert_run_lifecycle_event_present(with_owner=...)` pins the exact column shape (`'local'::text`, `is_nullable NO`) and its absence at 0009 and below through the full downgrade ladder.
- Two-sided pg-contracts pin exists: `runLifecycleEventOwnerColumn` in `pg-contracts.json`, asserted by `test_activity_pg_contracts.py` (Python side) and `pgContracts.test.ts` (TS side).
- Notify payload owner: exact-dict-equality asserts in `test_run_lifecycle_writer.py` (`"owner": "owner-a"` and default `"local"`) would fail if the payload key were dropped.

## 4. Starting reachable, no double count

- `runActivityMachine` initial state is `starting`; a lifecycle-only run materializes there. Integration test asserts `{ runId, status: "starting" }` for owner A and `[]` for owner B against real Postgres.
- No double count: `returns exactly one run before and after its first session row` inserts the first session row after the lifecycle-only phase and asserts length 1 both sides; killed by the INNER JOIN mutation, so it is load-bearing.
- Reconnect relist (spec's slice-4 dependency): `re-lists a lifecycle-only starting run after a dropped NOTIFY` drives `onConnected` and asserts the `starting` delta; also killed by the INNER JOIN mutation.
- Spec §6.1 conformance: owner stays a single-tenant forward-compat constant (`DEFAULT_ACTIVITY_OWNER = "local"`) threaded by default at `build_run_lifecycle_event`; call sites (`addon_runtime.py`, `capture_rpc.py`) intentionally unchanged, exactly as the locked resolution specifies.

## 5. Scope / DRY / sizing

- 17 files, all named by the spec's slice 5 row (migration, Python row/builder/writer/contracts + tests, pg-contracts.json, TS SQL + contracts + harness + tests). No unrelated change; `SessionRow.owner` literal → `DEFAULT_ACTIVITY_OWNER` is an in-scope DRY consolidation.
- Largest touched files: `test_migrate.py` 643, `dao_statements.py` 600, `postgresRecords.ts` 561. Nothing over 700.

## Observation (non-blocking, no action needed)

Owner is per lifecycle event row, not per run, with uniqueness on `(run_id, event_type)`. If a future multi-owner caller ever threaded different owners to a run's start and exit events, the group would split across owners (A sees a never-exiting run, B sees an exit without a start). Unreachable today (every call site uses the default) and spec-conformant (§6.1 locks owner-at-emit); worth remembering when owner becomes a real input.
