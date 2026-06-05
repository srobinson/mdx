# Review: PR 42 feat/fix-db-config at 5b25291

Verdict: Clean.

## Scope

Reviewed `origin/feat/fix-db-config` at `5b25291` against the prior review findings from `88ab3a0`.

Prior open items:

1. Blocker: test home isolation ran too late for collection imports.
2. Blocker: unreachable configured database crashed backend startup instead of degrading.
3. Minor: `run_codex` crossed the project function size threshold.
4. Minor: stale `HOME_DIR` wording remained after the agent home rename.

All four are resolved in `5b25291`.

## Resolution verification

### Prior blocker 1 resolved: import side effects removed

`api/src/transport_matters/main.py` no longer constructs the FastAPI app at module import. It exposes lazy app creation through `__getattr__`, so importing `transport_matters.main` does not read settings or construct the app.

Poisoned home import probe:

```bash
cd api
tmp=$(mktemp -d)
mkdir -p "$tmp/.transport-matters"
printf '[database\n' > "$tmp/.transport-matters/settings.toml"
env -u TRANSPORT_MATTERS_HOME -u TRANSPORT_MATTERS_DATABASE_URL \
  -u TRANSPORT_MATTERS_TEST_DATABASE_URL HOME="$tmp" \
  .venv/bin/python - <<'PY'
import transport_matters.main as main
print('MAIN_IMPORT_OK', hasattr(main, '__dict__'))
import conftest
print('CONFTEST_IMPORT_OK')
PY
```

Observed result: import completed without reading the malformed real home config. The probe exited 0 and printed `CONFTEST_IMPORT_OK`.

### Prior blocker 2 resolved: unreachable database degrades

`api/src/transport_matters/main.py` now separates migration failures from reachability failures. `MigrationError` still fails fast. Other failures during the migration check close the pool and return degraded session store state.

Unreachable database probe:

```bash
cd api
TRANSPORT_MATTERS_HOME=$(mktemp -d) \
TRANSPORT_MATTERS_DATABASE_URL=postgresql://u:p@127.0.0.1:1/none \
.venv/bin/python - <<'PY'
import asyncio
from httpx import ASGITransport, AsyncClient
from transport_matters.main import create_app

async def main():
    app = create_app()
    async with app.router.lifespan_context(app):
        print('LIFESPAN_OK', True)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get('/api/sessions')
            print('STATUS', response.status_code)
            print('BODY', response.text)

asyncio.run(main())
PY
```

Observed result: startup did not crash, the probe logged `Session store unreachable during migration check`, then printed `LIFESPAN_OK True`, `STATUS 503`, and `BODY {"detail":"session store unavailable"}`. The probe exited 0.

### Prior minor 1 resolved: function size threshold

`run_codex` was split with `_resolve_codex_addons_and_ca`. AST measurement over changed Python files found no functions above 150 lines.

Observed result: `LONG_COUNT 0`.

### Prior minor 2 resolved: stale rename wording

`api/src/transport_matters/cli/test_start_mint.py` now uses `AGENT_HOME_DIR` wording. A stale sweep found only intentional internal helper naming and legitimate `--agent-home-dir` references.

## Tests

Focused regression gate:

```bash
cd api
TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres \
env -u TRANSPORT_MATTERS_DATABASE_URL -u TRANSPORT_MATTERS_HOME \
uv run python -m pytest \
  src/transport_matters/api/v1/test_session_routes.py::test_lifespan_degrades_when_database_unreachable \
  src/transport_matters/api/v1/test_session_routes.py::test_main_app_is_built_lazily_not_at_import \
  src/transport_matters/api/v1/test_session_routes.py::test_lifespan_fails_fast_on_migration_failure \
  src/transport_matters/cli/test_launch_preflight.py
```

Observed result: exit 0, `7 passed in 0.21s`.

Bare test with docker default and no database env:

```bash
env -u TRANSPORT_MATTERS_TEST_DATABASE_URL -u TRANSPORT_MATTERS_DATABASE_URL -u TRANSPORT_MATTERS_HOME just test
```

Observed result: exit 0, `1177 passed in 14.89s`.

Full bare CI gate with docker default and no database env:

```bash
env -u TRANSPORT_MATTERS_TEST_DATABASE_URL -u TRANSPORT_MATTERS_DATABASE_URL -u TRANSPORT_MATTERS_HOME just ci
```

Observed result: exit 0. Ruff format check passed, ruff check passed, mypy passed, and pytest reported `1177 passed in 14.31s`.

## Additional verification retained from earlier review

Wheel packaging probe passed earlier in this review: `uv build --out-dir /tmp/...` then `unzip -l` showed `transport_matters/settings.example.toml` and `migrations/versions/0001_session_store_foundation.py` in the wheel.

## Findings

No open findings.
