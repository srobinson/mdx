## Reuse Map
- Reuse
  - Capability: isolate the lifespan DB. Existing owner: `api/src/transport_matters/session/testing.py:TestDb`. It is the only DB creation mechanism found. It creates a `tm_test_...` database, migrates it through `TestDb.migrate`, and drops it through `TestDb.drop`.
  - Capability: open an app client against an already isolated session store. Existing owner: `api/src/transport_matters/api/v1/session_test_support.py:session_client`. It builds a pool from `TestDb.database_url`, opens it, installs it on `app.state.session_pool`, and uses `ASGITransport`. This is useful for route tests, but it bypasses `api/src/transport_matters/main.py:lifespan`, so it cannot prove the runtime lifespan path.
  - Capability: runtime session store start seam. Existing owner: `api/src/transport_matters/main.py:lifespan` calls `api/src/transport_matters/config.py:resolve_database_url`, then passes that resolved string to `api/src/transport_matters/main.py:_start_session_store`. `_start_session_store` is the exact seam where the runtime store opens: it calls `api/src/transport_matters/session/pool.py:create_async_pool`, opens the pool, applies migrations, starts `SessionEventListener`, then assigns `app.state.session_pool`.
  - Capability: channel DB rewriting. Existing owner: `api/src/transport_matters/config.py:resolve_database_url`. It rewrites the configured URL database path to `transport_matters` or the active channel DB from `transport_matters.channel:resolve_channel_spec`. `api/src/transport_matters/config.py:resolve_test_database_url` returns the configured test URL without rewriting. Confirming probe: `Settings(database_url='postgresql://tm:tm@localhost:55432/tm_test_pid_deadbeef')` resolves through runtime config to `postgresql://tm:tm@localhost:55432/transport_matters`, while test config returns the original `tm_test_pid_deadbeef` URL.
  - Capability: route dependency access to the runtime pool. Existing owner: `api/src/transport_matters/api/v1/session_store.py:optional_session_pool` and `api/src/transport_matters/api/v1/session_store.py:require_session_pool`. These only read `app.state.session_pool`; they do not open or resolve databases.
  - Capability: SpaceStore on the runtime pool. Existing owner: `api/src/transport_matters/main.py:_resolve_current_space`, `api/src/transport_matters/main.py:_backfill_session_spaces`, and `api/src/transport_matters/space/store.py:SpaceStore`. Lifespan writes space rows through the same runtime pool after session store startup.
  - Searches ran: `fmm_list_files` under `api/src/transport_matters`; `fmm_file_outline` for `api/conftest.py`, `session/testing.py`, `session/pool.py`, `main.py`, `config.py`, `api/v1/session_test_support.py`, `api/v1/session_store.py`, and `space/store.py`; `fmm_read_symbol` for `TestDb`, `resolve_database_url`, `resolve_test_database_url`, `database_url_with_database_name`, `create_async_pool`, `_resolved_url`, `lifespan`, `_start_session_store`, `_resolve_current_space`, `_backfill_session_spaces`, `session_client`, `optional_session_pool`, and `require_session_pool`; `rg "resolve_database_url|DATABASE_URL|lifespan|TestClient\(create_app|app.state.session_pool|SpaceStore\(|create_async_pool"`.
- Existing infra
  - `api/conftest.py:test_db`, `api/src/transport_matters/api/v1/conftest.py:test_db`, and `api/src/transport_matters/session/conftest.py:test_db` already wrap `TestDb` for pytest. These wrappers should be consolidated or clearly scoped, but they are built on the correct creation primitive.
  - `api/conftest.py:_isolate_transport_matters_home` already points `TRANSPORT_MATTERS_HOME` at a temp home so tests avoid the developer settings file. This helps settings isolation, but it does not protect the runtime DB when `TRANSPORT_MATTERS_DATABASE_URL` is inherited or set in a test.
  - `api/conftest.py:_scrub_inherited_session_env` removes most inherited `TRANSPORT_MATTERS_*` values, but deliberately preserves `env_keys.DATABASE_URL`, `env_keys.TEST_DATABASE_URL`, and `env_keys.DOCKER_PG_PORT`. That is currently unsafe for app lifespan tests because runtime resolution consumes `DATABASE_URL` and rewrites it to the channel DB.
  - `api/justfile:test` and `api/justfile:ci` are the real API test gates. `api/justfile` exports `TRANSPORT_MATTERS_TEST_DATABASE_URL` by default for local Docker Postgres; it does not export `TRANSPORT_MATTERS_DATABASE_URL`.
  - Searches ran: `rg "TestDb.create\(|create_test_db\(|session_client\(|test_db.database_url"`; `rg "TRANSPORT_MATTERS_TEST_DATABASE_URL|pytest" api/justfile api/pyproject.toml`; `fmm_dependency_graph` for `session/testing.py`, `session/pool.py`, `main.py`, and `api/v1/session_test_support.py`.
- Similar checked-and-rejected
  - Schema and table enumeration exist in `api/src/transport_matters/session/test_migrate.py:_SPACES_TABLES`, `_SPACES_UUID_COLUMNS`, `_SPACES_TEXT_COLUMNS`, `_reset_to_unmigrated`, `_tables`, `_table_columns`, and migration assertion helpers. These are migration contract tests, not DB isolation infrastructure. Do not reuse them for cleanup, isolation, or guard logic.
  - Destructive table drops in `api/src/transport_matters/session/test_migrate.py:_reset_to_unmigrated` are for simulating old schemas inside a `TestDb` database. They are not a general reset mechanism.
  - Searches ran: `rg "DROP TABLE|TRUNCATE|information_schema|pg_tables|table_name|TABLES|DELETE FROM"` under `session`, `api/conftest.py`, and `api/v1/test_*.py`.
- None-found
  - Pytest guard: none found in production runtime. No existing symbol hard-fails if pytest starts the runtime store against a non `tm_test_` database.
  - Detecting pytest at runtime: none found in production code. Searches found pytest imports and fixtures, but no reusable runtime symbol such as `is_pytest`, `PYTEST_CURRENT_TEST`, or a pytest mode helper.
  - Canonical lifespan app fixture: none found. Existing `session_client` bypasses `lifespan`; current lifespan tests each set env or monkeypatch runtime resolution by hand.
  - DB-name extraction guard helper: none found. Existing URL helpers are `config.database_url_with_database_name` and `session.testing.database_url_for`, which construct or rewrite URLs; they do not validate that a resolved runtime URL targets a test database.
  - Searches ran: `rg "PYTEST_CURRENT_TEST|pytest|PYTEST|is_pytest|under pytest|PYTEST_"`; `rg "guard|fail.*pytest|non-test|tm_test|operator|production|database.*pytest|pytest.*database|database.*test"`; `rg "database_url_for|urlsplit|urlparse|dbname|datname"`.

## Quality Map
- Duplication or parallel DB-isolation wiring across tests
  - Duplicate DB fixture wrappers to consolidate: `api/conftest.py:test_db`, `api/src/transport_matters/api/v1/conftest.py:test_db`, `api/src/transport_matters/api/v1/session_test_support.py:create_test_db`, and `api/src/transport_matters/session/conftest.py:test_db` all wrap `TestDb.create` plus `drop` with small variations.
  - Direct pool seeding is repeated in `api/src/transport_matters/api/v1/test_session_routes.py:test_session_routes_are_owner_scoped_and_expose_native_payload`, `test_session_event_routes_reveal_native_payload_for_meta_records`, `test_session_list_filters_internal_sessions_and_locks_cursor`, `test_session_timeline_is_owner_scoped_paginated_and_omits_raw`, `test_session_event_stream_backlog_then_live_dedups_race`, `test_session_event_stream_catches_up_after_listener_reconnect_gap`, `test_session_timeline_stream_emits_live_item_with_stable_id`, `test_session_timeline_stream_reemits_enriched_prior_item`, and `test_session_timeline_stream_is_owner_scoped`.
  - Direct pool seeding is also repeated in `api/src/transport_matters/api/v1/test_session_resource_content.py:_seed_resource_session`, `api/src/transport_matters/api/v1/test_session_routes_spaces.py:_seed_space_sessions`, `api/src/transport_matters/api/v1/test_session_routes_spaces.py:_seed_empty_cwd_session`, `api/src/transport_matters/api/v1/test_session_routes_spaces.py:test_subdirectory_session_backfills_to_containing_worktree_filter`, and `api/src/transport_matters/api/v1/test_run_routes.py:_seed_continuation_parent`.
  - Lifespan DB wiring is duplicated and inconsistent in `api/src/transport_matters/api/v1/test_session_routes.py:test_app_lifespan_releases_session_listener_connection`, `test_lifespan_runs_session_space_backfill_when_database_enabled`, `test_lifespan_listener_start_failure_keeps_routes_unavailable`, and `test_lifespan_fails_fast_on_migration_failure`. Each sets `TRANSPORT_MATTERS_DATABASE_URL` to `TestDb.database_url`, which looks isolated but is rewritten by `resolve_database_url`.
  - `api/src/transport_matters/api/v1/test_space_routes.py:test_lifespan_resolves_api_cwd_into_current_space` and `api/src/transport_matters/api/v1/test_run_routes.py:test_post_continuation_threads_lineage_context_and_idempotency` avoid the rewrite by monkeypatching `transport_matters.main.resolve_database_url`. This is safer, but it is a second parallel pattern.
  - `api/src/transport_matters/api/v1/test_run_routes.py:test_post_continuation_returns_not_found_for_foreign_parent` seeds `TestDb`, sets `env_keys.DATABASE_URL` to `TestDb.database_url`, uses `test_run_routes.py:_client`, and does not patch `resolve_database_url`. This is a current leak path on the lifespan route.
  - App tests that use `TestClient(create_app())` as a context manager start lifespan and are exposed to inherited `TRANSPORT_MATTERS_DATABASE_URL` because `api/conftest.py:_scrub_inherited_session_env` preserves it. Affected helpers and import users: `api/src/transport_matters/api/v1/test_run_routes.py:_client`, used by `test_run_routes.py`, `test_run_routes_launch.py`, `test_run_routes_list_filters.py`, and `test_run_routes_terminal.py`; `api/src/transport_matters/api/v1/test_terminal.py:_client`; `api/src/transport_matters/api/v1/test_local_file_routes.py:_client`.
  - `ASGITransport` route clients in `api/conftest.py:client`, `api/src/transport_matters/api/v1/conftest.py:client`, `api/src/transport_matters/api/v1/test_breakpoint.py:client`, `test_meta.py:client`, `test_overrides.py:client`, `test_overrides_shared_proxy.py:app_client`, and `test_exchanges_live_run_storage.py:test_live_run_reads_exchange_written_by_distinct_storage_backend` create apps without explicitly entering lifespan. They are lower risk for runtime DB startup, but they still use ad hoc app construction.
  - Leak verdict: yes, tests currently can leak to the operator DB on the lifespan path. Static proof: `resolve_database_url` rewrites `TestDb.database_url` to the channel DB; `lifespan` uses that resolver; `_start_session_store` opens the rewritten URL. Direct leak tests are the four `test_session_routes.py` lifespan tests that set `TRANSPORT_MATTERS_DATABASE_URL` to `TestDb.database_url` without patching resolution, plus `test_run_routes.py:test_post_continuation_returns_not_found_for_foreign_parent`. Conditional inherited leak risk applies to all `TestClient(create_app())` context tests when pytest runs inside an environment that exports the live launcher `TRANSPORT_MATTERS_DATABASE_URL`.
- Boundary or design issue
  - `api/conftest.py:_scrub_inherited_session_env` treats `env_keys.DATABASE_URL` as test infrastructure, but runtime app startup also treats it as operator session store configuration. That collapses two concepts: admin or test source DB versus runtime session store DB.
  - `api/src/transport_matters/config.py:resolve_database_url` is correct for product channel isolation, but unsafe as a way to inject per-test DBs through `TRANSPORT_MATTERS_DATABASE_URL`.
  - `api/src/transport_matters/api/v1/session_test_support.py:session_client` mutates `app.state.session_pool` directly. That is useful for route tests, but it means most session route coverage does not exercise the real `lifespan` pool creation path.
  - A guard placed in `api/src/transport_matters/session/pool.py:create_async_pool` would also affect legitimate direct `TestDb.database_url` pools used by session and route seeding. A guard placed at `api/src/transport_matters/main.py:_start_session_store` targets the runtime store startup seam more narrowly.
- Dead code
  - None found in the audited area. `api/src/transport_matters/api/v1/session_test_support.py:create_test_db` is used by `api/v1/conftest.py:test_db`; `session_client` is used by `test_session_routes.py`, `test_session_routes_spaces.py`, `test_session_resource_content.py`, and `test_space_routes.py`.
  - Searches ran: `rg "session_test_support|session_client|create_test_db"`; `fmm_dependency_graph` for `api/v1/session_test_support.py`.
- Grooming recommendation (refactor first|during|defer + reason)
  - Refactor during. The fix should introduce or choose one canonical lifespan isolation helper before converting the leaking tests, because adding a guard first will expose the current duplicated env wiring immediately. Avoid broad cleanup of all direct pool seeding in the same slice; that can defer unless it blocks the guard tests. The critical consolidation is the lifespan DB path, not every route seed helper.

## Plan
- Decision needed (or none)
  - Decision needed: guard seam. Evidence points to `api/src/transport_matters/main.py:_start_session_store`, because it is the runtime session-store opening seam and receives the exact resolved URL that will be opened. This avoids interfering with direct `TestDb.database_url` pools used for test data seeding through `create_async_pool`.
  - Decision needed: pytest detection owner. No existing owner was found. The smallest owner should be a production importable helper near the runtime guard, not a pytest fixture, because the guard must run inside the app process started by tests.
- Proposed steps bound to the Reuse Map
  - Step 1: Build the canonical lifespan isolation path on `TestDb`. Do not introduce a second DB creation mechanism, a reset list, or schema enumeration. The helper should make app lifespan open `TestDb.database_url` without passing it through `resolve_database_url` channel rewriting.
  - Step 2: Convert the named leaking lifespan tests to the canonical helper. Remove per-test `TRANSPORT_MATTERS_DATABASE_URL = test_db.database_url` wiring from the runtime lifespan path. Keep direct `create_async_pool(test_db.database_url, ...)` seeding only where it seeds data outside app startup.
  - Step 3: Convert `api/src/transport_matters/api/v1/test_run_routes.py:test_post_continuation_returns_not_found_for_foreign_parent` to the same helper or to the existing patched resolver pattern used by `test_post_continuation_threads_lineage_context_and_idempotency` until the helper exists.
  - Step 4: Add the pytest runtime guard at `_start_session_store`. Under pytest, reject any runtime session-store URL whose database name is not a `tm_test_...` database. The guard should inspect the resolved URL string and fail before `create_async_pool`, `apply_migrations`, `SessionEventListener`, `_resolve_current_space`, or `_backfill_session_spaces` can touch the operator DB.
  - Step 5: Tighten env scrubbing so inherited `TRANSPORT_MATTERS_DATABASE_URL` from a live launcher cannot reach lifespan tests by default. Preserve `TRANSPORT_MATTERS_TEST_DATABASE_URL` for `TestDb.create`; do not preserve runtime `TRANSPORT_MATTERS_DATABASE_URL` unless a test explicitly opts in.
  - Step 6: Keep migration schema enumeration confined to `api/src/transport_matters/session/test_migrate.py`. The isolation fix should use database identity from the URL and `TestDb` ownership, never a hand-maintained table list.
- Tests and gates (the repo's real commands)
  - Focused config proof: `cd api && just test src/transport_matters/test_channel.py`.
  - Focused lifespan regression set: `cd api && just test src/transport_matters/api/v1/test_session_routes.py src/transport_matters/api/v1/test_run_routes.py src/transport_matters/api/v1/test_space_routes.py src/transport_matters/api/v1/test_main_lifespan_shared_proxy.py`.
  - Focused helper and route set: `cd api && just test src/transport_matters/api/v1/test_session_resource_content.py src/transport_matters/api/v1/test_session_routes_spaces.py`.
  - API gate: `cd api && just ci`.
  - If the follow-on changes shared app test helpers used outside API v1, run `just test` from the repo root after the API gate.

## Desktop focus + speed blast radius

### Desktop versus CLI map

Verdict: desktop focus does not materially narrow the test DB isolation slice. The leak sits on the FastAPI lifespan runtime DB opener used by the desktop backend, while the session store and space tables are shared infrastructure across desktop backend startup and detached CLI launch preflight. The `/spaces` HTTP routes are desktop backend routes over the shared `SpaceStore`; detached `claude` and `codex` launches do not call those HTTP routes directly, but they validate and write against the same configured session store.

Shared DB path anchors:
- `api/src/transport_matters/session/testing.py:TestDb` is the only normal per test database creation primitive.
- `api/src/transport_matters/session/pool.py:create_async_pool` is the shared pool opener used by route tests, session tests, lifespan, and seed helpers.
- `api/src/transport_matters/config.py:resolve_database_url` is the runtime resolver that rewrites a configured URL to the active channel database.
- `api/src/transport_matters/main.py:lifespan` calls `api/src/transport_matters/main.py:_start_session_store`, then `api/src/transport_matters/main.py:_resolve_current_space`, then `api/src/transport_matters/main.py:_backfill_session_spaces`.
- `api/src/transport_matters/session_store_preflight.py:check_session_store` is shared by `api/src/transport_matters/cli/launch_runtime.py:preflight_session_store_or_exit`.
- `api/src/transport_matters/cli/start_cmd.py:run_start`, `api/src/transport_matters/cli/codex_cmd.py:run_codex`, and `api/src/transport_matters/cli/desktop_cmd.py:serve_desktop_backend` all call that preflight path.
- `api/src/transport_matters/cli/desktop_cmd.py:serve_desktop_backend` then serves `api/src/transport_matters/main.py:create_app`, so desktop backend startup enters the same FastAPI lifespan leak path.

Desktop relevant code path anchors:
- `api/src/transport_matters/main.py:create_app` includes the `/v1/runs`, session, and `/v1/spaces` routers.
- `api/src/transport_matters/api/v1/run_routes.py:create_run_manager` installs the server managed `RunManager` used by canvas runs.
- `api/src/transport_matters/api/v1/run_routes.py:create_run` resolves a worktree, builds launch fields, and calls `api/src/transport_matters/run_manager.py:RunManager.spawn`.
- `api/src/transport_matters/api/v1/run_routes.py:run_terminal_socket` and `api/src/transport_matters/api/v1/run_routes.py:bridge_attached_run_terminal` attach the canvas terminal websocket.
- `api/src/transport_matters/run_manager.py:RunManager.spawn` enters `api/src/transport_matters/run_manager.py:RunManager._prepare_request`, which calls the captured run preparation path.
- `api/src/transport_matters/captured_run.py:prepare_captured_run` and `api/src/transport_matters/captured_run_context.py:build_captured_run_context` are shared capture infrastructure, but the `RunManager` use is desktop relevant.
- `api/src/transport_matters/api/v1/run_routes.py:_resolved_worktree` and `api/src/transport_matters/api/v1/run_routes.py:_launch_fields` read the runtime session pool during desktop run creation.
- `api/src/transport_matters/api/v1/space_routes.py:resolve_space`, `api/src/transport_matters/api/v1/space_routes.py:list_spaces`, `api/src/transport_matters/api/v1/space_routes.py:create_canvas`, and `api/src/transport_matters/api/v1/space_routes.py:patch_canvas` are desktop backend routes over the shared `SpaceStore` pool.
- `api/src/transport_matters/api/v1/session_routes.py:list_sessions`, `api/src/transport_matters/api/v1/session_routes.py:get_session_timeline`, and `api/src/transport_matters/api/v1/session_routes.py:stream_session_timeline` are desktop read surfaces over the same store.

Confirmed desktop relevant leak tests:
- `api/src/transport_matters/api/v1/test_session_routes.py:test_app_lifespan_releases_session_listener_connection` sets runtime `TRANSPORT_MATTERS_DATABASE_URL` to `TestDb.database_url`, then enters `main.lifespan`.
- `api/src/transport_matters/api/v1/test_session_routes.py:test_lifespan_runs_session_space_backfill_when_database_enabled` follows the same runtime env to lifespan and backfill path.
- `api/src/transport_matters/api/v1/test_session_routes.py:test_lifespan_listener_start_failure_keeps_routes_unavailable` follows the same runtime env to lifespan and listener startup.
- `api/src/transport_matters/api/v1/test_session_routes.py:test_lifespan_fails_fast_on_migration_failure` follows the same runtime env to lifespan migration.
- `api/src/transport_matters/api/v1/test_run_routes.py:test_post_continuation_returns_not_found_for_foreign_parent` sets runtime `env_keys.DATABASE_URL` to `TestDb.database_url`, creates a context managed `TestClient`, and does not patch `transport_matters.main.resolve_database_url`.

Desktop relevant but already safer or direct pool seeded:
- `api/src/transport_matters/api/v1/test_run_routes.py:test_post_continuation_threads_lineage_context_and_idempotency` covers the same continuation launch path and patches `transport_matters.main.resolve_database_url` to the `TestDb` URL.
- `api/src/transport_matters/api/v1/test_space_routes.py:test_lifespan_resolves_api_cwd_into_current_space` covers the lifespan current space path and patches `transport_matters.main.resolve_database_url`.
- `api/src/transport_matters/api/v1/test_session_routes.py`, `api/src/transport_matters/api/v1/test_session_routes_spaces.py`, `api/src/transport_matters/api/v1/test_session_resource_content.py`, and `api/src/transport_matters/api/v1/test_space_routes.py` seed or read the same session and space store used by the desktop backend.
- `api/src/transport_matters/space/test_store.py` and `api/src/transport_matters/space/test_store_session_resolution.py` cover `SpaceStore`, which is shared by lifespan, run routes, and `/spaces` routes.
- `api/src/transport_matters/session/test_foundation.py`, `api/src/transport_matters/session/test_ingest.py`, `api/src/transport_matters/session/test_listen.py`, `api/src/transport_matters/session/test_migrate.py`, `api/src/transport_matters/session/test_subagents.py`, and `api/src/transport_matters/session/test_capture_without_web.py` cover the shared session store substrate. Desktop depends on this substrate even when the test is not a canvas route test.
- `api/src/transport_matters/shared_proxy/test_core.py:test_shared_proxy_payload_round_trip_persists_space_identity` covers shared proxy persistence of space identity, which is desktop relevant through `main.lifespan` shared proxy startup and canvas runs.
- `api/tests/integration/test_backend_launch_smoke.py:test_launched_backend_reads_db_from_home_not_per_run_storage` covers backend DB resolution and is desktop backend relevant.

CLI launch only bucket for this slice:
- `api/src/transport_matters/captured_run.py:run_captured_run_on_local_tty` is the detached local terminal capture path.
- `api/src/transport_matters/cli/start_cmd.py:run_start` is detached `transport-matters claude`.
- `api/src/transport_matters/cli/codex_cmd.py:run_codex` is detached `transport-matters codex`.
- `api/src/transport_matters/cli/test_channel_cmd.py:test_channel_ensure_db_creates_migrates_and_is_idempotent`, `api/src/transport_matters/cli/test_db_cmd.py:test_db_status_reports_up_to_date`, `api/src/transport_matters/cli/test_db_cmd.py:test_db_upgrade_brings_unmigrated_db_to_head`, and `api/src/transport_matters/cli/test_launch_preflight.py:test_channel_ensure_db_makes_launch_preflight_pass` are CLI command or launch preflight tests. They contribute DB creation cost, but they are not canvas or `/runs` route coverage.

### Speed blast radius

Static count method: parsed `api/src` and `api/tests` test files, followed fixture dependencies into `test_db`, `space_store`, `dao`, `fresh_db`, `temporary_channel_database`, and `migrated_db`, and multiplied literal `pytest.mark.parametrize` cases. Search checks also covered `TestDb.create`, `def test_db`, `session_client(`, `create_async_pool(test_db.database_url)`, `async_connect(test_db.database_url)`, and direct `TestDb(...)` construction.

Search evidence:
- `TestDb.create` appears in 5 creator/helper sites: `api/conftest.py:test_db`, `api/src/transport_matters/session/conftest.py:test_db`, `api/src/transport_matters/api/v1/session_test_support.py:create_test_db`, `api/src/transport_matters/cli/test_db_cmd.py:fresh_db`, and `api/tests/integration/test_backend_launch_smoke.py:migrated_db`.
- Direct `TestDb(...)` construction appears in `api/src/transport_matters/cli/conftest.py:temporary_channel_database`, which manually creates a channel database and wraps it in `TestDb` for cleanup.
- `def test_db` fixtures appear in 3 files: `api/conftest.py:test_db`, `api/src/transport_matters/session/conftest.py:test_db`, and `api/src/transport_matters/api/v1/conftest.py:test_db`.
- `session_client(` appears as the helper `api/src/transport_matters/api/v1/session_test_support.py:session_client` plus 10 use sites in `api/src/transport_matters/api/v1/test_session_resource_content.py`.
- `create_async_pool(test_db.database_url)` appears 33 times across 12 files.
- `async_connect(test_db.database_url)` appears 13 times across 4 files.
- `psycopg.connect(test_db.database_url)` or `connect(test_db.database_url)` appears 16 times across 6 files.

DB hit count by file:

| File | DB test functions | Parameterized items | Approx DB creates |
| --- | ---: | ---: | ---: |
| `api/src/transport_matters/api/v1/test_run_routes.py` | 2 | 2 | 2 |
| `api/src/transport_matters/api/v1/test_session_resource_content.py` | 10 | 13 | 13 |
| `api/src/transport_matters/api/v1/test_session_routes.py` | 13 | 13 | 13 |
| `api/src/transport_matters/api/v1/test_session_routes_spaces.py` | 6 | 6 | 6 |
| `api/src/transport_matters/api/v1/test_space_routes.py` | 5 | 5 | 5 |
| `api/src/transport_matters/cli/test_channel_cmd.py` | 1 | 1 | 1 |
| `api/src/transport_matters/cli/test_db_cmd.py` | 2 | 2 | 2 |
| `api/src/transport_matters/cli/test_launch_preflight.py` | 1 | 1 | 1 |
| `api/src/transport_matters/session/test_capture_without_web.py` | 1 | 1 | 1 |
| `api/src/transport_matters/session/test_foundation.py` | 19 | 19 | 19 |
| `api/src/transport_matters/session/test_ingest.py` | 8 | 8 | 8 |
| `api/src/transport_matters/session/test_listen.py` | 2 | 2 | 2 |
| `api/src/transport_matters/session/test_migrate.py` | 6 | 6 | 6 |
| `api/src/transport_matters/session/test_subagents.py` | 1 | 1 | 1 |
| `api/src/transport_matters/shared_proxy/test_core.py` | 1 | 1 | 1 |
| `api/src/transport_matters/space/test_store.py` | 5 | 5 | 5 |
| `api/src/transport_matters/space/test_store_session_resolution.py` | 2 | 2 | 2 |
| `api/tests/integration/test_backend_launch_smoke.py` | 1 | 1 | 1 |
| **Total** | **86** | **89** | **89** |

Desktop relevant or shared backend substrate accounts for 15 of the 18 DB hitting files, 82 of the 86 DB hitting test functions, and about 85 of the 89 DB creations. CLI command only coverage accounts for 3 files, 4 functions, and 4 creations.

Conclusion: per test DB creation cost is a real blast radius in `cd api && just test`. A template clone optimization would help the desktop relevant suite too, because the large majority of DB creations sit in shared session, space, and backend route tests rather than CLI command only tests.

