---
title: Test DB Isolation Implementation
type: sessions
tags: [backend, testing, database, isolation]
summary: Implemented pytest session store DB isolation guard, injected settings seam, TestDb template clone, and CLI channel DB test isolation.
status: active
source: backend-engineer
confidence: high
created: 2026-06-22
updated: 2026-06-23
---

## Summary

Implemented the pytest session store database isolation slice on branch `fix/pytest-session-store-isolation` and opened PR #168. The change prevents lifespan tests from silently opening the developer runtime database, routes app lifespan tests through explicit settings injection, speeds isolated database creation with a migrated template clone, and consolidates duplicate test database fixtures.

Follow up on 2026-06-23 fixed the CI-only CLI DB status failure. The root cause was that `db status` resolves runtime URLs through the active channel database name, so the test still depended on the operator or CI channel database. CLI DB tests now point channel resolution at explicit `tm_test_*` databases through shared CLI fixtures.

## API Contract

No public API endpoints changed. The internal test contract now has one canonical lifespan client fixture:

```python
with lifespan_client(test_db) as client:
    ...
```

The application construction seam is:

```python
settings = get_settings().with_session_store_url(test_db.database_url)
app = create_app(settings=settings)
```

The CLI test contract now has one channel database helper:

```python
point_cli_at_channel_database(test_db, home=tmp_path)
```

## Database Changes

No production schema migration was added. Test database creation now clones from a migrated `tm_test_template_*` database per worker and drops cached templates at pytest session teardown. Pytest guarded app lifespan rejects session store URLs whose database name does not begin with `tm_test_`.

CLI channel database tests now use `tm_test_channel_*` names. `db status` is verified against a migrated test channel database, and `db upgrade` is verified against an explicitly created empty test channel database.

## Security Considerations

The guard adds defense in depth for destructive tests by failing before a session store pool opens against a non test database. The injected session store URL is a private `Settings` attribute so ambient `TRANSPORT_MATTERS_SESSION_STORE_URL` cannot override runtime channel database resolution.

The CLI fix keeps the inherited `TRANSPORT_MATTERS_DATABASE_URL` scrub closed. Tests set their own database URL and channel spec explicitly instead of relying on operator state.

## Performance Notes

Cloning from a migrated template reduced full API test runtime from the direct migration path while preserving isolation. Final verification on the follow up passed `cd api && just ci`, including ruff format check, ruff check, mypy, migration smoke, and 1711 pytest tests.

## Open Items

No known follow up is required for this slice. Future app lifespan tests should use `api/conftest.py:test_db` and `api/conftest.py:lifespan_client`. Future CLI channel database tests should use `api/src/transport_matters/cli/conftest.py:point_cli_at_channel_database`.
