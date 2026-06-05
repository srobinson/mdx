---
title: Test-DB isolation + prod-DB guard — industry standard for FastAPI + async-psycopg + Postgres
type: research
tags: [transport-matters, testing, database-isolation, fastapi, psycopg, pytest, lifespan]
summary: Keep TestDb as the per-test ephemeral create/drop DB; wire the lifespan to it through an injectable settings/config seam (FastAPI's get_settings + dependency_overrides analogue for lifespan-built pools), never by monkeypatching resolve_database_url; add a fail-fast guard at _start_session_store that rejects any non-tm_test_ DB name under pytest.
status: active
source: quick-research
confidence: high
created: 2026-06-22
updated: 2026-06-22
---

# Test-DB Isolation + Prod-DB Guard: Industry Standard for Our Stack

Stack under test: FastAPI, raw **psycopg 3 async pool** (not SQLAlchemy ORM), Postgres, app run **in-process** (TestClient / async lifespan). Pool is built **inside** `main.py:lifespan` → `_start_session_store` → `session/pool.py:create_async_pool`, stored on `app.state.session_pool`. URL comes from `config.py:resolve_database_url`, which **rewrites the DB name** to the channel DB. Per-test isolated migrated DB already exists via `session/testing.py:TestDb` (create / migrate / drop).

---

## (a) Recommendation for OUR stack (the single approach to adopt)

**Keep `TestDb` as the only DB creator** — ephemeral create-migrate-drop per test (or per xdist-worker), which is the correct standard for a stack that owns its own connection pool and whose business logic commits. **Do not adopt SQLAlchemy-style transaction-rollback-per-test**: it is the speed-optimal standard *for ORM session-injection stacks*, but it requires every code path to share one rollback-bound connection and to never `COMMIT` — neither holds for a lifespan-owned psycopg pool. **Wire the lifespan to the test DB through an injectable settings/config seam**, the lifespan-equivalent of FastAPI's canonical `get_settings` + `app.dependency_overrides` pattern, so a test supplies `TestDb.database_url` *verbatim* and the lifespan opens it **without** passing through `resolve_database_url` channel rewriting. **Do not monkeypatch `resolve_database_url`** — the rewrite-on-read behavior is the root cause of the leak, and the standard fix is a real config seam, not patching a private function. Finally, **add a fail-fast guard at `_start_session_store`** that, when running under pytest, refuses any resolved DB whose name is not a `tm_test_…` database (Rails `protected_environments` / Django `test_`-prefix pattern), inspecting the URL DB name only — never enumerating tables.

---

## (b) Industry standard per question, with sources

### Q1 — Test-DB strategy (ephemeral create/drop vs transaction-rollback vs containers)

Three established patterns:

| Pattern | What it is | Standard when | Cost / risk |
|---|---|---|---|
| **Transaction-rollback per test** | Open one connection, `BEGIN` (+ savepoints via `SAVEPOINT`/event listener), run test, `ROLLBACK`. | ORM stacks that inject a single `Session`/connection (SQLAlchemy, SQLModel). Fastest: savepoints reuse one connection. | **Breaks if app code `COMMIT`s** or opens its own pool/connection. Requires the app to receive the test's connection — incompatible with a lifespan that builds its own pool. |
| **Ephemeral create/drop DB** (per session, per worker, or per test) | Create a fresh DB (often `CREATE DATABASE … TEMPLATE`), migrate, run, drop. | Stacks where the app owns connections, or where code commits. `pytest-postgresql` does exactly this: template DB once per session, clone per test, "terminates leftover connections and drops the test database to ensure isolation," and **handles xdist** worker naming. | Slower per test (DB create/clone), but fully isolated and commit-safe. |
| **Testcontainers** | Spin a disposable Postgres container (per session or per xdist worker). | CI that wants prod-parity Postgres with zero host setup; per-worker container = clean parallel isolation. | Container start latency; Docker dependency. |

For **pytest-xdist**, the converged rule across sources is **one DB (or schema) per worker**, keyed off `PYTEST_XDIST_WORKER`; do not share a DB across workers. The SQLAlchemy maintainer's recommendation is per-worker DB + per-test rollback *for ORM stacks*; for non-ORM/pool-owning stacks the per-worker ephemeral-DB half is what transfers.

**Verdict for us:** `TestDb` (ephemeral create/migrate/drop) is already the industry-correct primitive for a psycopg-pool stack with committing code. Rollback-per-test is explicitly **not** applicable. Keep `TestDb`; if/when xdist is enabled, key the DB name on `PYTEST_XDIST_WORKER` (TestDb already namespaces by pid).

Sources:
- FastAPI "Testing a Database" → defers to SQLModel testing tutorial (separate test DB + dependency override): https://fastapi.tiangolo.com/how-to/testing-database/ and https://sqlmodel.tiangolo.com/tutorial/fastapi/tests/
- `pytest-postgresql` (template-clone, drop-per-test, xdist handling, psycopg 3): https://pypi.org/project/pytest-postgresql/
- Testcontainers for Python (disposable per-worker Postgres): https://testcontainers.com/guides/getting-started-with-testcontainers-for-python/
- SQLAlchemy Discussion #13109 — parallelizing FastAPI+Postgres+pytest, per-worker DB + rollback trade-offs, `PYTEST_XDIST_WORKER`: https://github.com/sqlalchemy/sqlalchemy/discussions/13109

### Q2 — Wiring the app to the test DB (the FastAPI-canonical mechanism)

The canonical FastAPI mechanism is **`app.dependency_overrides`**: "you put as a key the original dependency (a function), and as the value, your dependency override … FastAPI will call that override instead." The officially documented way to swap *configuration* (including a DB URL) is to expose settings through a **`get_settings` dependency** (`@lru_cache def get_settings(): return Settings()`) and in tests do `app.dependency_overrides[get_settings] = get_settings_override`. This is the FastAPI-blessed alternative to monkeypatching.

**Critical sub-question — exercising the REAL lifespan against the test DB without monkeypatching a private function.** `dependency_overrides` is request-time only; **FastAPI's DI does not natively reach `lifespan`** (confirmed in Discussion #11742). The established patterns, in order of cleanliness:

1. **Injectable settings / app-factory parameterization (the standard).** The lifespan reads its DB URL from an injectable `Settings` (or provider) held on the app, set at construction: `create_app(settings=...)` or `app.state.settings`. A test constructs the app with test settings carrying `TestDb.database_url`. The lifespan opens *that* URL directly. This is the lifespan analogue of `dependency_overrides[get_settings]` — a real seam, no patching.
2. **Lifespan reads `app.dependency_overrides` itself** (community workaround from #11742): `get = app.dependency_overrides.get(get_db_url) or get_db_url`. Works only for dependencies with no transitive deps; it leans on a request-time facility from startup, so it is weaker than (1).
3. **Monkeypatching internals / env var** — what we do today (set `TRANSPORT_MATTERS_DATABASE_URL`, or patch `transport_matters.main.resolve_database_url`). The env-var route is actively unsafe here because `resolve_database_url` rewrites the name back to the channel DB; the monkeypatch route is the anti-pattern the settings seam exists to replace.

Sources:
- FastAPI "Testing Dependencies — Overrides" (`app.dependency_overrides`): https://fastapi.tiangolo.com/advanced/testing-dependencies/
- FastAPI "Settings and Environment Variables" — `get_settings` + `dependency_overrides[get_settings]` for tests: https://fastapi.tiangolo.com/advanced/settings/
- FastAPI Discussion #11742 "Dependencies in lifespan" — DI does not natively reach lifespan; community `dependency_overrides.get(...)` pattern: https://github.com/fastapi/fastapi/discussions/11742
- FastAPI "Lifespan Events": https://fastapi.tiangolo.com/advanced/events/

### Q3 — The prod-DB guard (fail-fast if a test would hit a non-test DB)

Two industry archetypes, both fail-fast:

- **Naming-convention guard (Django).** The test runner takes the configured DB name and **prepends `test_`**, creating/using only that DB, so tests structurally cannot use the production DB. Standard placement: framework/app config. https://docs.djangoproject.com/en/5.0/topics/testing/overview/
- **Environment/identity guard (Rails `protected_environments`).** Rails stores the environment in `ar_internal_metadata` and **raises before destructive operations** if the target DB belongs to a protected environment; `rails_db_guard` raises on connecting to a protected DB from another environment. Standard placement: app/config layer, enforced at connect/migrate time. https://www.bigbinary.com/blog/rails-5-prevents-destructive-action-on-production-db and https://github.com/betterdoc-org/rails_db_guard
- **Access-gating guard (pytest-django).** "By default your tests will fail if they try to access the database" unless explicitly marked (`@pytest.mark.django_db`), via `django_db_blocker`. Standard placement: test fixture/plugin. https://pytest-django.readthedocs.io/en/latest/database.html

**Where the industry puts it:** when tests run the framework **out-of-process**, a pytest fixture assertion suffices. When tests run the app **in-process** (our case — the real `lifespan` builds the pool inside the pytest process), the load-bearing guard must live at the **app/startup layer** (Rails model), because an env-var leak reaches the lifespan regardless of any fixture. A fixture-level assertion is a useful belt-and-suspenders second line, not the primary guard.

---

## (c) Map onto our seams (TestDb stays the creator; no table enumeration)

1. **Creator — unchanged.** `session/testing.py:TestDb` remains the *only* DB creation/migration/drop mechanism. No second creator, no reset list, no schema/table enumeration (keep that confined to `session/test_migrate.py`). Q1 says this is already correct.

2. **Wiring seam — add an injectable session-store URL to the lifespan (Q2 pattern #1).** Introduce a settings/config field the lifespan uses *verbatim* for the session store, e.g. `Settings.session_store_url` (or a `session_store_url_override`). Change `main.py:lifespan`/`_start_session_store` to take the URL from that injectable settings value held on `app.state`, applying `resolve_database_url` channel rewriting **only** when the override is absent (production path unchanged). Canonical lifespan fixture outline:

   ```python
   @pytest.fixture
   def lifespan_app(test_db):                      # test_db: TestDb (existing primitive)
       settings = build_test_settings(             # injectable settings, not env, not patch
           session_store_url=test_db.database_url, # used verbatim, NOT channel-rewritten
       )
       app = create_app(settings=settings)         # app-factory parameterization
       with TestClient(app) as client:             # enters REAL lifespan → opens TestDb DB
           yield client
   ```

   This replaces the duplicated, leaky per-test `TRANSPORT_MATTERS_DATABASE_URL = test_db.database_url` wiring (the four `test_session_routes.py` lifespan tests + `test_run_routes.py:test_post_continuation_returns_not_found_for_foreign_parent`) **and** the parallel monkeypatch-`resolve_database_url` pattern, collapsing both into one canonical seam. Existing `session_test_support.py:session_client` (mutates `app.state.session_pool` directly, bypassing lifespan) stays only for pure route/data tests where exercising the real lifespan is not the point.

3. **Guard seam — `main.py:_start_session_store`, gated on pytest, URL-name only.** Before `create_async_pool`, when under pytest (detect via the `PYTEST_CURRENT_TEST` env var that pytest sets per test), extract the DB name from the *resolved* URL (`urllib.parse.urlsplit` → path basename) and **fail-fast unless it matches the `tm_test_` ownership prefix** that `TestDb` creates. This is the Rails-style app-layer guard at the exact runtime-store-open seam (narrower than `create_async_pool`, which also serves legitimate direct `TestDb.database_url` data-seeding pools). It validates *identity from the URL*, never tables.

   ```python
   # inside _start_session_store, before create_async_pool(resolved_url, ...)
   if os.environ.get("PYTEST_CURRENT_TEST"):
       dbname = urlsplit(resolved_url).path.lstrip("/")
       if not dbname.startswith(TEST_DB_PREFIX):   # "tm_test_"
           raise RuntimeError(
               f"refusing to open non-test session store {dbname!r} under pytest")
   ```

4. **Env hygiene — `api/conftest.py:_scrub_inherited_session_env`.** Stop preserving runtime `TRANSPORT_MATTERS_DATABASE_URL` by default (it currently survives scrubbing and can reach lifespan tests from a live launcher). Keep preserving `TRANSPORT_MATTERS_TEST_DATABASE_URL` (TestDb's source) and `DOCKER_PG_PORT`. This removes the inherited-leak class; the startup guard (3) is the backstop if anything slips through.

Gates (repo recipes, verbatim — per scout): focused config proof `cd api && just test src/transport_matters/test_channel.py`; lifespan regression `cd api && just test src/transport_matters/api/v1/test_session_routes.py src/transport_matters/api/v1/test_run_routes.py src/transport_matters/api/v1/test_space_routes.py src/transport_matters/api/v1/test_main_lifespan_shared_proxy.py`; API gate `cd api && just ci`.

---

## (d) Does the standard imply our pattern should change vs be monkeypatched?

**Yes — change the seam, do not monkeypatch.** The `app.state` + DI pattern itself is *correct and idiomatic* (FastAPI builds pools in lifespan and exposes them on `app.state`; routes read via `require_session_pool`/`optional_session_pool` — keep all of it). The defect is narrower: the lifespan's **DB-URL source is a global resolver (`resolve_database_url`) that rewrites the name**, so the only ways to redirect it today are an env var (silently rewritten → leak) or monkeypatching a private function (the anti-pattern). The industry standard (FastAPI `get_settings` + override; lifespan parameterized by injectable settings) says the URL should come from an **injectable config seam** the test controls. So: **keep `app.state` + DI and `TestDb`; replace env/monkeypatch wiring with an injectable session-store-URL setting; add the app-layer startup guard.** Monkeypatching `resolve_database_url` should be retired, not standardized.

---

## Sources
- FastAPI — Testing a Database: https://fastapi.tiangolo.com/how-to/testing-database/
- FastAPI — Testing Dependencies with Overrides: https://fastapi.tiangolo.com/advanced/testing-dependencies/
- FastAPI — Settings and Environment Variables (get_settings + override): https://fastapi.tiangolo.com/advanced/settings/
- FastAPI — Lifespan Events: https://fastapi.tiangolo.com/advanced/events/
- FastAPI — Discussion #11742, Dependencies in lifespan: https://github.com/fastapi/fastapi/discussions/11742
- SQLModel — Test Applications with FastAPI and SQLModel: https://sqlmodel.tiangolo.com/tutorial/fastapi/tests/
- SQLAlchemy — Discussion #13109, parallelizing FastAPI+Postgres+pytest: https://github.com/sqlalchemy/sqlalchemy/discussions/13109
- pytest-postgresql (PyPI): https://pypi.org/project/pytest-postgresql/
- Testcontainers for Python: https://testcontainers.com/guides/getting-started-with-testcontainers-for-python/
- Django — Writing and running tests (test_ prefix): https://docs.djangoproject.com/en/5.0/topics/testing/overview/
- Rails 5 protected production DB: https://www.bigbinary.com/blog/rails-5-prevents-destructive-action-on-production-db
- rails_db_guard: https://github.com/betterdoc-org/rails_db_guard
- pytest-django — Database access guard: https://pytest-django.readthedocs.io/en/latest/database.html

## Speed (fast per-test isolation)

**Concern confirmed.** `session/testing.py:TestDb.create` runs `CREATE DATABASE` (empty) then `migrate()` → `upgrade_to_head(database_url)` on **every** create, so each per-test DB re-runs the full Alembic chain from scratch. At suite scale this is the dominant cost: Alembic spins up its runner and applies every revision as DDL inside transactions on a cold DB, which is on the order of **hundreds of ms to seconds per test**.

### Recommended fast mechanism (keeps TestDb as the sole creator, no table list)

**The template-database pattern.** Migrate a schema-complete **template database once per test session (per xdist worker)**, then for each test do `CREATE DATABASE <clone> TEMPLATE <template>` — Postgres physically copies the schema at the storage layer instead of re-running migrations, and the per-test DB is dropped after. This is the converged industry standard for non-ORM/pool-owning Postgres stacks and is exactly what `pytest-postgresql` ships: *"The process fixture pre-populates the database once per session into a template database. The client fixture then clones this template for each test, which significantly speeds up your tests,"* then *"terminates leftover connections and drops the test database to ensure isolation,"* with per-worker databases under xdist.

**Postgres clone semantics (source-grounded):**
- `CREATE DATABASE` *"actually works by copying an existing database"* — a physical copy of the template, no migration replay.
- **Limitation that shapes the design:** *"no other sessions can be connected to the template database while it is being copied. CREATE DATABASE will fail if any other connection exists when it starts."* So the template must be idle during a clone. This is naturally satisfied (the template is only ever connected during its one-time build) and is the reason to use **one template per xdist worker** rather than one shared template: shared, the per-test `CREATE DATABASE ... TEMPLATE` calls across workers contend on the connection lockout; per-worker templates eliminate that contention.
- **STRATEGY:** default `WAL_LOG` is *"the most efficient strategy in cases where the template database is small"* (our case — a handful of session-store tables), so the default needs no tuning; `FILE_COPY` only wins for large templates. No change required.
- Caveat: clone does **not** copy database-level GRANTs (irrelevant here — same role owns template and clones).

**Rough cost:** template clone of a small schema is **single-to-tens of ms** ("test databases created in milliseconds instead of seconds"); the migration runs **once** per session/worker instead of once per test. `pgdbtemplate` reports template cloning ~1.5x faster end-to-end with 17% less memory and clean scaling to hundreds of test DBs versus migrate-per-test. Net: the O(tests) Alembic cost collapses to O(workers).

### Concrete shape — what `TestDb` gains (no second creator, no table enumeration)

`TestDb` stays the **only** DB creation/migration/drop owner. Two additive changes, both inside it:

1. **Session-scoped template builder** — a memoized classmethod (e.g. `TestDb.ensure_template()`) that, once per process/worker, creates one `tm_test_template_{worker}_<hash>` DB via the existing `connect(admin_url, autocommit=True)` + `CREATE DATABASE` seam and runs `upgrade_to_head` on it **once**. `upgrade_to_head` opens and closes its own connection, so the template is left idle and clonable. Key the template name on `PYTEST_XDIST_WORKER` (falls back to a single value off-xdist), resolving the prior Open Question about pid-namespacing composing with xdist.
2. **`TestDb.create` fast path** — replace the empty-`CREATE DATABASE` + `migrate()` body with `CREATE DATABASE <name> TEMPLATE <template>` against the worker's template, skipping per-test migration. Same `admin_url`/autocommit seam, same `tm_test_...` clone naming, same `drop()` (which already runs `pg_terminate_backend` then `DROP DATABASE` — exactly the leftover-connection cleanup the pattern requires). `migrate()` and `drop()` are otherwise unchanged; `migrate()` is reused by the template builder.

### Does the fast path change the prior wiring/guard design? No.

The Q2 injectable-settings wiring and the Q3 `_start_session_store` guard are **untouched**. Tests still hand the lifespan `test_db.database_url` verbatim; the guard still inspects only the resolved URL's DB name for the `tm_test_` ownership prefix — clones (`tm_test_…`) and templates (`tm_test_template_…`) both pass, never the operator DB, and the guard still enumerates no tables. The change is confined to *how a per-test DB acquires its schema* (clone vs migrate) plus a one-time template builder, both inside `TestDb`. No second DB creator, no reset/truncate list, no schema enumeration.

### Alternatives — when they win (honest assessment for our constraints)

| Approach | Verdict for our stack |
|---|---|
| **Worker-scoped single migrated DB + clean between tests** | **Rejected.** Cleanup is either `TRUNCATE`/`DELETE` per table (**requires a table list** — violates the no-enumeration constraint) or transaction-`ROLLBACK` per test (**incompatible** with a lifespan-owned psycopg pool whose code `COMMIT`s, per Q1). Neither is open to us. |
| **Schema-per-test** (`CREATE SCHEMA` in one DB) | **Rejected.** Marginally cheaper than a DB clone but invasive: Alembic/our migrations target a database, so it needs `search_path` juggling and per-schema object creation (effectively re-migrating), and it abandons TestDb's DB-per-test model. |
| **Pool reuse / Testcontainers** | **Orthogonal.** Pool reuse is not an isolation mechanism; Testcontainers still pays the migration cost once per container (same as the template) and does not address per-test migration. |

**Bottom line:** extend `TestDb` with a session/worker-scoped migrated **template** plus a per-test `CREATE DATABASE … TEMPLATE` clone. Prior wiring and guard design stand.

### Speed sources
- PostgreSQL — Template Databases (clone semantics, no-connection limitation): https://www.postgresql.org/docs/current/manage-ag-templatedbs.html
- PostgreSQL — CREATE DATABASE (TEMPLATE, WAL_LOG vs FILE_COPY STRATEGY): https://www.postgresql.org/docs/current/sql-createdatabase.html
- pytest-postgresql (migrate template once per session, clone per test, drop + terminate connections, xdist per-worker DBs): https://pypi.org/project/pytest-postgresql/
- boringSQL — Instant database clones (template clone in ms not seconds): https://boringsql.com/posts/instant-database-clones/
- pgdbtemplate — fast Postgres test databases via templates (1.5x faster, scales to hundreds of test DBs): https://dev.to/andrei-polukhin/pgdbtemplate-fast-postgresql-test-databases-in-go-using-templates-138n

## Open Questions
- Exact name/shape of the injectable settings field (`session_store_url` vs `session_store_url_override`) is an implementation choice for the builder; this research fixes the *mechanism* (injectable settings, not patch), not the field name.
- Template lifecycle teardown: dropping the per-worker template at session end is optional hygiene (an idle `tm_test_template_…` DB is harmless and the guard ignores it); decide whether to drop on session-finish or leave for the next run to reuse.
