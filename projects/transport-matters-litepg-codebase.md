# Transport Matters embedded Postgres feasibility

Date: 2026-06-15
Scope: codebase coupling and migration surface only. No implementation was performed.

## Executive summary

Feasible with caveats. Transport Matters already centralizes most database access behind a Postgres URL, psycopg pools, Alembic migrations, and a small launch preflight, so replacing Docker backed external Postgres with a process owned local Postgres cluster is a bounded migration.

The clean design is a session store lease abstraction that starts or reuses a bundled real Postgres cluster under `$TRANSPORT_MATTERS_HOME`, returns a DSN, and is acquired before both transcript capture and the FastAPI app start. The biggest risk is package and platform coverage, not SQL compatibility.

## Current Postgres coupling

| Surface | Current evidence | Embedded impact |
| --- | --- | --- |
| Settings and DSN resolution | `api/src/transport_matters/config.py :: Settings`, `resolve_database_url`, `resolve_test_database_url`, `ensure_settings_scaffold` | Today the app expects `TRANSPORT_MATTERS_DATABASE_URL` or `[database] url` in `$TRANSPORT_MATTERS_HOME/settings.toml`. Embedded mode needs a resolver that can create a local lease and return its DSN when no external URL is configured. |
| Runtime pool | `api/src/transport_matters/session/pool.py :: create_pool`, `create_async_pool`, `_resolved_url`, `sqlalchemy_url` | The pool layer already accepts an explicit URL. Keep this boundary and pass the embedded DSN explicitly where possible. |
| FastAPI lifecycle | `api/src/transport_matters/main.py :: lifespan`, `_start_session_store` | The API opens the pool, applies migrations, then starts the notification listener. Embedded mode should acquire and close the local Postgres lease in the same lifecycle when the API starts standalone. |
| Proxy capture lifecycle | `api/src/transport_matters/addon_runtime.py :: load_runtime`, `load_capture_runtime`, `start_web_runtime` | `load_runtime` starts transcript capture before it starts the embedded web runtime. If local Postgres starts only inside FastAPI `lifespan`, `SessionWriter` will run too early. Acquire the store lease before `load_capture_runtime`, then hand its DSN to capture and web startup. |
| Launch preflight | `api/src/transport_matters/cli/launch_runtime.py :: preflight_session_store_or_exit`; `api/src/transport_matters/session_store_preflight.py :: check_session_store`, `session_store_setup_help` | Current launch blocks if an external store is missing or unreachable. Embedded default should convert this into platform and bootstrap validation. External DSN can remain an override. |
| Claude and Codex launch paths | `api/src/transport_matters/cli/start_cmd.py :: run_start`; `api/src/transport_matters/cli/codex_cmd.py :: run_codex`; `api/src/transport_matters/launch_environment.py :: build_launch_env` | Both commands call the same preflight and pass ambient env into mitmdump. If the parent CLI starts or resolves embedded Postgres, the generated DSN must be passed to the addon process or both processes must safely acquire the same lease. |
| Captured canvas runs | `api/src/transport_matters/run_manager.py :: RunManager._captured_request`; `api/src/transport_matters/captured_run.py :: prepare_captured_run` | Canvas spawns reject runs when the session store is unavailable. In embedded mode, this should ensure the local lease is healthy instead of requiring user supplied Postgres. |
| Migrations | `api/src/transport_matters/session/migrate.py :: apply_migrations`, `current_revision`, `alembic_config`; `api/migrations/env.py :: _database_url` | Alembic already consumes a DSN. Embedded mode must create the target application database before Alembic checks revisions, because current migration code assumes the database already exists. |
| Database maintenance CLI | `api/src/transport_matters/cli/db_cmd.py :: status`, `upgrade` | `db status` and `db upgrade` should use the same resolver. They may also need `db start`, `db stop`, or `db reset` if operators need direct control over the local cluster. |
| Doctor | `api/src/transport_matters/cli/diagnose.py :: run_doctor`, `_session_store_failure` | Doctor already checks session store config, reachability, and migration head. In embedded mode, it should report bundled binary availability, data dir, cluster status, PID, DSN target, and schema revision. |
| Test harness | `api/src/transport_matters/session/testing.py :: TestDb`; `api/src/transport_matters/session/conftest.py :: test_db`; `api/tests/integration/test_backend_launch_smoke.py :: migrated_db` | Tests currently create and drop databases through an admin URL supplied by `TRANSPORT_MATTERS_TEST_DATABASE_URL`. Embedded testing needs a session scoped local cluster that supplies the admin URL, then keeps the existing per test database isolation. |
| Packaging | `api/pyproject.toml :: project.dependencies`, `tool.hatch.build.targets.wheel.artifacts` | Adding `pgembed` as a dependency would pull platform wheels during install. The Transport Matters wheel does not need to vendor Postgres binaries directly, but release smoke tests should cover each supported platform. |
| Docker surface | `docker-compose.yml :: services.postgres`; `README.md :: Source checkout`; `QUICKSTART.md :: Provide a Postgres`; `.github/workflows/ci.yml :: backend-test`; `.github/workflows/release.yml :: build` | Compose, docs, CI services, release services, and setup text are all explicitly Docker or external Postgres oriented. They become optional external mode docs or disappear from the default path. |

## SQL feature compatibility

These features are standard PostgreSQL server features. A bundled real Postgres 17 cluster should carry them unchanged.

| Feature Transport Matters uses | Code evidence | PostgreSQL 17 evidence | Assessment |
| --- | --- | --- | --- |
| LISTEN and NOTIFY | `api/src/transport_matters/session/writer.py :: SessionWriter._commit_batch` calls `pg_notify`; `api/src/transport_matters/session/listen.py :: SessionEventListener._listen_forever` executes `LISTEN` | PostgreSQL 17 documents `NOTIFY` as sending payloads to sessions that executed `LISTEN`, and documents `pg_notify(text, text)` as the function form. See https://www.postgresql.org/docs/17/sql-notify.html and https://www.postgresql.org/docs/17/sql-listen.html | Standard. No extension needed. |
| Generated `tsvector` column | `api/migrations/versions/0001_session_store_foundation.py :: upgrade` defines `content_tsv tsvector GENERATED ALWAYS AS (...) STORED` | PostgreSQL 17 documents stored generated columns and shows `GENERATED ALWAYS AS (...) STORED`. See https://www.postgresql.org/docs/17/ddl-generated-columns.html | Standard. No extension needed. |
| GIN full text search | `api/migrations/versions/0001_session_store_foundation.py :: upgrade` creates `event_fts_gin`; `api/src/transport_matters/session/dao_statements.py :: TEXT_SEARCH_SQL` queries `content_tsv @@ websearch_to_tsquery` | PostgreSQL 17 full text docs show GIN indexes over `to_tsvector` and a stored generated `tsvector` column indexed by GIN. See https://www.postgresql.org/docs/17/textsearch-tables.html | Standard. No extension needed. |
| JSONB and JSONB GIN | `api/migrations/versions/0001_session_store_foundation.py :: upgrade` defines `source_descriptor`, `raw`, `ir`, and `ref` as `jsonb`; `api/migrations/versions/0002_event_tier1_indexes.py :: upgrade` creates `event_raw_gin`; `api/src/transport_matters/session/dao_statements.py :: IR_SEARCH_SQL` uses `ir @>` | PostgreSQL 17 documents JSONB containment, existence, and GIN operator classes. See https://www.postgresql.org/docs/17/datatype-json.html and https://www.postgresql.org/docs/17/gin.html | Standard. No extension needed. |
| Advisory locks for migration serialization | `api/src/transport_matters/session/migrate.py :: apply_migrations` uses `pg_advisory_lock` and `pg_advisory_unlock` | PostgreSQL 17 documents advisory locks as application defined locks, with session level locks held until release or session end. See https://www.postgresql.org/docs/17/explicit-locking.html | Standard. No extension needed. |
| Bytea artifacts and identity dead letters | `api/migrations/versions/0001_session_store_foundation.py :: upgrade`; `api/migrations/versions/0003_event_dead_letter.py :: upgrade` | Core PostgreSQL column types and identity columns | Standard. No extension needed. |

No active code requires PostGIS, pgvector, pgvectorscale, pg_textsearch, logical replication, superuser only extensions, or cloud provider features.

## Package fit

| Package | Current fit for Transport Matters |
| --- | --- |
| `pgembed` | Best fit among the named family. PyPI reports `pgembed` 0.2.0 with `requires-python >=3.12`, including CPython 3.14 wheels in the PyPI JSON response checked during this investigation. The project README advertises PostgreSQL 17, no admin rights, `pgembed.get_server(DATA_DIR)`, managed `initdb`, process cleanup, and direct paths to `initdb`, `pg_ctl`, `psql`, and `pg_config`. Sources: https://pypi.org/project/pgembed/ and https://github.com/Ladybug-Memory/pgembed |
| `pgserver` | Poor fit now. PyPI latest is 0.1.4 from 2024. The package targets PostgreSQL 16.2 and CPython 3.9 through 3.12, while Transport Matters requires Python 3.14 and currently runs Postgres 17. Sources: https://pypi.org/project/pgserver/ and https://github.com/orm011/pgserver |
| `pg0-embedded` | Interesting fallback, but not PG17 aligned. Current PyPI release 0.14.2 is recent and broad, but upstream documents PostgreSQL 18 bundled into the binary. It also has host dependency notes on Linux and root user constraints. Source: https://pypi.org/project/pg0-embedded/ and https://github.com/vectorize-io/pg0 |
| `pgvenv` | Poor fit for no setup. It builds PostgreSQL from source inside a virtualenv and requires a compiler toolchain, so it does not replace Docker with a simple bundled binary path. Source: https://github.com/Florents-Tselai/pgvenv |

## Proposed embedded shape

1. Add a narrow session store lease module, for example `transport_matters.session.local_postgres`, owned below `config` and above `session.pool`.
2. Model store mode in settings: default embedded, optional external URL override, data dir defaulting to `$TRANSPORT_MATTERS_HOME/postgres` or `$TRANSPORT_MATTERS_HOME/session-store`.
3. On embedded mode, call `pgembed.get_server(data_dir, cleanup_mode="stop")` or an equivalent wrapper, keep the returned server handle alive for the process lifetime, derive the app database DSN, and create the app database if absent.
4. Preserve the existing pool and migration APIs by passing a DSN into `create_async_pool`, `current_revision`, and `apply_migrations`.
5. Acquire the lease in `addon_runtime.load_runtime` before `load_capture_runtime`, because capture starts before web startup.
6. Acquire the lease in `main.lifespan` for standalone API starts, and avoid double ownership through a process local cache or explicit injected lease.
7. Make `session_store_preflight` validate that embedded Postgres can start on this platform and that the data dir is usable. Preserve external URL checks when a URL is configured.
8. Keep `TestDb` database isolation. Replace the Docker supplied admin URL with a test session embedded lease.

## Migration surface

### Code

- `api/src/transport_matters/config.py :: Settings`, `DatabaseSettings`, `resolve_database_url`, `resolve_test_database_url`: add embedded mode and data dir fields, or replace URL only resolution with a resolver that returns a lease plus DSN.
- `api/src/transport_matters/session/pool.py :: create_pool`, `create_async_pool`: keep the explicit URL path and reduce no argument resolution where long lived callers can pass a DSN.
- `api/src/transport_matters/addon_runtime.py :: load_runtime`, `load_capture_runtime`, `close_runtime`: acquire and close the embedded lease around capture and web runtimes.
- `api/src/transport_matters/main.py :: lifespan`, `_start_session_store`: acquire the embedded lease for standalone ASGI and close it after listener and pool shutdown.
- `api/src/transport_matters/session_store_preflight.py :: check_session_store`, `session_store_setup_help`: replace external Postgres instructions with embedded status and remediation, while keeping external override instructions.
- `api/src/transport_matters/cli/launch_runtime.py :: preflight_session_store_or_exit`: stop hard failing on missing external config when embedded mode is available.
- `api/src/transport_matters/run_manager.py :: RunManager._captured_request`: convert store unavailable errors to local bootstrap failures with typed machine codes.
- `api/src/transport_matters/cli/db_cmd.py :: status`, `upgrade`: use the shared resolver and consider exposing embedded cluster diagnostics.
- `api/src/transport_matters/cli/diagnose.py :: run_doctor`: report binary package availability, data dir writability, cluster running state, DSN target, migration revision, and platform support.
- `api/src/transport_matters/cli/help.py :: _CLAUDE_HELP`, `_CODEX_HELP`, `_DESKTOP_HELP`, `_DOCTOR_HELP`: update environment and doctor descriptions. `_DOCTOR_HELP` is currently stale because the code checks session store health.

### Tests and CI

- Replace the CI Postgres service in `.github/workflows/ci.yml :: backend-test` and `.github/workflows/release.yml :: build` with embedded startup once coverage is proven on Linux.
- Add platform smoke jobs for macOS and Windows before claiming Docker free install across those platforms.
- Convert `api/src/transport_matters/session/testing.py :: TestDb` to create its admin cluster through the embedded lease.
- Keep existing migration and route tests. They are useful compatibility tests against the embedded real server.
- Add a focused test for first run with no `settings.toml` and no database URL: launch should scaffold settings if still needed, start embedded Postgres, migrate, and return `GET /api/sessions` 200.
- Add a restart test against an existing data dir to prove migrations are no op and data survives app restart.
- Add a concurrent launch test against the same `$TRANSPORT_MATTERS_HOME` to prove lease locking and advisory migration serialization work together.

### Docs and packaging

- `docker-compose.yml :: services.postgres`: remove from the default path, or keep only as external mode developer fallback.
- `README.md :: Source checkout` and `QUICKSTART.md :: Provide a Postgres`: rewrite from "provide Postgres" to "Transport Matters provisions local Postgres by default" with external override notes.
- `api/src/transport_matters/settings.example.toml :: database`: stop scaffolding Docker defaults in the default path. External mode examples can remain commented.
- `api/pyproject.toml :: project.dependencies`: add the embedded package dependency and revise OS classifier claims to match the real wheel matrix.
- Release notes and installer smoke tests should mention larger downloads and platform exceptions.

## Risks and caveats

1. Platform coverage is the primary risk. `pgembed` currently fits Python 3.14 and PostgreSQL 17, but the PyPI file matrix checked here showed CPython specific wheels and uneven platform tags. Transport Matters should not claim a Docker free default on platforms not covered by tested wheels.
2. Startup order matters. The current proxy runtime starts transcript capture before the FastAPI app. A FastAPI only embedded start would leave `SessionWriter` disabled during capture.
3. Database creation is new product code. Migrations assume the target database exists. Embedded mode must create and version the app database before Alembic runs.
4. Multi process ownership needs proof. Several Transport Matters launches can share one `$TRANSPORT_MATTERS_HOME`. The embedded wrapper advertises interprocess cleanup behavior, but Transport Matters still needs its own concurrent launch regression.
5. Authentication and exposure need explicit defaults. `pgembed` initializes with trust auth and uses Unix sockets on POSIX. Windows uses TCP on localhost. That is probably acceptable for a local app, but doctor should print the exposure mode.
6. Binary size and install reliability will change. Tool install gets simpler operationally but heavier in bytes, and failures move from Docker setup to wheel resolution.
7. External Postgres may still matter for advanced users. Even pre release, keeping URL override is cheap and useful for debugging, CI fallback, and users with unsupported platforms.

## Open questions

- Which platforms does Transport Matters want to support at release: macOS arm64 only, macOS Intel, Windows, manylinux, musllinux, or all current OS independent claims?
- Should the embedded server stop when the last Transport Matters process exits, or stay resident for faster restarts?
- Should the app database be named `transport_matters`, or should embedded mode use the default `postgres` database to avoid `CREATE DATABASE` bootstrap?
- Should `transport-matters db` own explicit `start`, `stop`, `logs`, and `reset` commands, or should doctor be the only operator surface?

## Verdict

feasible-with-caveats: the codebase migration is bounded around config, lifecycle, preflight, tests, CI, and docs; the single biggest risk is embedded Postgres wheel and platform coverage for Transport Matters supported installs.
