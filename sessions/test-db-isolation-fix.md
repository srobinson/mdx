---
title: Test DB Isolation Fix
type: sessions
tags: [backend, testing, database, spaces]
summary: Added canonical pytest database isolation so runtime and CLI database tests cannot reach the operator database.
status: active
source: backend-engineer
confidence: high
created: 2026-06-22
updated: 2026-06-22
---

## Summary

Implemented PR #167 on branch `fix/test-db-isolation`. Initial implementation landed at `e90f92a`; CI follow up landed at `36235efc3bb7c4a3c0a434245c3d9bdc97642fce`.

The fix prevents pytest app lifespan and CLI database tests from reaching the operator database. Root cause was that tests set `TRANSPORT_MATTERS_DATABASE_URL` to `TestDb.database_url`, but runtime `resolve_database_url()` rewrites the database name to the active channel database, such as `transport_matters`. The CI failure exposed the same duplicated path in `db status`, which resolved to `localhost:5432/transport_matters` and reported migration pending.

The final design uses one canonical `TestDb` mechanism:

* `isolated_runtime_database_url` patches both app lifespan and CLI db command database resolution to the current `TestDb` database.
* CLI db command tests use the shared global `test_db` fixture instead of a local duplicate fixture.
* `TestDb.reset_to_unmigrated()` centralizes migration table cleanup for CLI and migration tests.
* The old private migration test reset helper was removed.

## API Contract

No public API contract changed. This was a test isolation and regression guard change only.

## Database Changes

No migrations or schema changes. Test behavior now requires runtime database URLs under pytest to target `tm_test_*` databases. `TRANSPORT_MATTERS_DATABASE_URL` is no longer preserved from the parent environment by the pytest env scrubber. `TRANSPORT_MATTERS_TEST_DATABASE_URL` remains the test DB admin URL.

`TestDb.reset_to_unmigrated()` drops all known migrated tables, including Spaces tables, to simulate an unmigrated database without copying table lists across tests.

## Security Considerations

Added defense in depth for local and CI tests:

* `isolated_runtime_database_url` routes app lifespan and CLI database resolution to the current isolated `TestDb` database.
* `_guard_runtime_session_store_database` fails fast before `_start_session_store()` can connect to a non `tm_test_*` database under pytest.
* Assertion messages redact credentials from database URLs.
* Regression coverage proves the old channel rewrite path is rejected before a connection is opened.
* CLI db command tests no longer depend on or touch the operator database.

## Performance Notes

No runtime performance impact. The guard and resolver patching are pytest only. The shared reset helper uses direct table drops against isolated test databases.

## Open Items

Backfill grouping quirk was diagnosed but not fixed in this PR. It is real: `backfill_session_spaces()` resolves only `cwd`, so when a worktree path has been deleted, `SpaceStore.resolve_session_cwd()` has no repo identity and creates a path named plain Space. Recommended follow up: persist or use launch time repo identity, then attach missing worktrees under the existing repo Space instead of a path derived plain Space.

## Verification

Completed on 2026-06-22 after commit `36235efc3bb7c4a3c0a434245c3d9bdc97642fce`:

* `git diff --check`
* `cd api && just check`
* `cd api && just test`
* Focused CLI and migration coverage before the full gate: `cd api && just test src/transport_matters/cli/test_db_cmd.py src/transport_matters/session/test_migrate.py::test_current_revision_none_on_unmigrated_db src/transport_matters/session/test_migrate.py::test_apply_migrations_brings_unmigrated_db_to_head`
* Full backend result: `1712 passed in 56.10s`
* Branch pushed: `fix/test-db-isolation`
* Bus reply sent to `transport-matters:general:orchestrator`: `done: 36235efc3bb7c4a3c0a434245c3d9bdc97642fce backend test green`
