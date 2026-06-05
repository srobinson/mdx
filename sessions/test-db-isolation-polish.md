---
title: Test DB Isolation Polish
type: sessions
tags: [backend, testing, database-isolation, session-store]
summary: Hardened pytest database isolation after PR 168 and updated PR 169 with a DRY template prefix fix.
status: active
source: backend-engineer
confidence: high
created: 2026-06-23
updated: 2026-06-23
---

## Summary

Implemented the five PR 168 follow up minors on `fix/test-db-isolation-polish` and opened PR #169. Review minors then replaced the remaining duplicated `tm_test_template_` builder string with `TEMPLATE_DB_PREFIX` and extracted `_as_utc()` for shared UTC normalization. The main decision was to make the async pool seam the enforcement point for pytest database safety, then keep TestDb as the sole database creator and cleanup owner.

## API Contract

No public API contract changes.

Internal test and configuration contract changes:

```python
create_async_pool(database_url: str | None = None, *, min_size: int | None = None, max_size: int | None = None)
```

Under pytest, `create_async_pool()` resolves the effective database URL before opening a pool and rejects database names that do not start with `tm_test_`.

```python
TestDb.drop_stale_templates(admin_url: str | None = None, *, min_age: timedelta = STALE_TEMPLATE_MIN_AGE) -> list[str]
```

Drops inactive, old TestDb template databases. The session fixture calls it only with an explicit allow listed test database URL.

## Database Changes

No application schema migration.

Test database behavior changed:

1. `TestDb.ensure_template()` builds template names from `TEMPLATE_DB_PREFIX` and stores JSON metadata in the database comment for template ownership and creation time.
2. Session start cleanup drops stale `tm_test_template_` databases only when old, inactive, and not owned by a live local process.
3. `TestDb.create()` now drops a clone database if template cloning partially succeeds and then raises.
4. Template name matching uses literal prefix comparison rather than SQL `LIKE`, so underscores are not wildcards.

## Security Considerations

The pytest operator database leak is closed at the shared async pool seam. Runtime code paths that call `create_async_pool()` cannot bypass the guard by omitting an explicit URL.

The session fixture scrubs inherited Transport Matters runtime environment before stale template cleanup and only sweeps when `TRANSPORT_MATTERS_TEST_DATABASE_URL` is present. It does not resolve `Settings.load()` at session scope, which avoids reading the operator config home before function scoped isolation.

## Performance Notes

The template clone path remains fast. The new stale sweep performs one `pg_database` query at pytest session start and only attempts drops for old inactive templates. Full `cd api && just ci` passed with 1717 tests in 50.86 seconds for the pytest phase.

## Open Items

No known blockers. Stale templates created before metadata support can still be reaped through the `pg_stat_file` fallback when the Postgres role allows it. If that fallback is denied, cleanup safely skips and logs at debug level.

## Verification

1. `cd api && just test src/transport_matters/session/test_pool.py src/transport_matters/session/test_testing.py src/transport_matters/test_config.py`, 27 passed.
2. `cd api && env -u TRANSPORT_MATTERS_TEST_DATABASE_URL -u TRANSPORT_MATTERS_HOME TRANSPORT_MATTERS_DATABASE_URL='postgresql://tm:tm@127.0.0.1:1/prod' uv run python -m pytest src/transport_matters/test_config.py::test_settings_default_app_name_uses_transport_matters -q`, 1 passed.
3. `cd api && just ci`, green. Ruff format check, Ruff lint, mypy, migration smoke, and 1717 pytest tests passed.
4. Self code review and code hygiene checks found session fixture and SQL prefix issues; both were fixed before PR creation.
5. DRY follow up: `cd api && just test src/transport_matters/session/test_testing.py`, 4 passed. Amended and force pushed commit `ef1fe01` to PR #169 with both DRY fixes.
6. Final tree check: branch `fix/test-db-isolation-polish` is clean and tracks `origin/fix/test-db-isolation-polish`.
