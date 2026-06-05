# Test-DB Isolation + Speed + Guard — Implementation Plan (LOCKED)

> Engineer: build EXACTLY this. The design is locked by a scout + research pass (do not redesign or re-litigate the mechanism). Full evidence and sources:
> - Scout (codebase map, seams, leak set, blast radius): `~/.mdx/projects/transport-matters-scout-test-db-isolation.md`
> - Research (industry standard + sources, speed): `~/.mdx/projects/transport-matters-research-test-db-isolation.md`
> Cite **file+symbol**, never line numbers.

**Goal:** pytest can NEVER touch the operator DB; lifespan tests run against an isolated migrated DB through a real config seam (no monkeypatch); per-test DB creation is fast (template clone, not per-test migration).

**Branch:** `fix/pytest-session-store-isolation` (the old `fix/test-db-isolation` is the dead PR#167 — do not reuse it).

## Hard constraints (non-negotiable)
- `session/testing.py:TestDb` is the ONLY DB create/migrate/drop mechanism. Do NOT add a second creator, a reset/truncate list, or ANY table/schema enumeration. (PR#167 was killed for a hand-maintained `_MIGRATED_TABLES` tuple — do not repeat.)
- Do NOT monkeypatch `config.py:resolve_database_url`. Retire that test pattern. Wiring is a real injectable settings seam.
- The guard inspects ONLY the resolved URL's DB name — never tables.
- Gate on repo recipes VERBATIM: `cd api && just test <paths>` and `cd api && just ci`. Never bare `pytest`/`tsc`.
- Keep file/function sizes within repo norms; if you touch a file near the limit, refactor before adding.

## Reuse Map (bind to these; reinventing any of these is a defect)
- DB create/migrate/drop → `session/testing.py:TestDb` (extend in place).
- Pool open → `session/pool.py:create_async_pool`, `connect`.
- Runtime store open seam (guard + URL source live here) → `main.py:_start_session_store`, called by `main.py:lifespan`.
- URL resolver → `config.py:resolve_database_url` (rewrites name to channel DB) vs `config.py:resolve_test_database_url` (no rewrite). Reuse `config.py:database_url_with_database_name` / `session.testing:database_url_for` for any URL work.
- Pool dependency getters (unchanged) → `api/v1/session_store.py:require_session_pool` / `optional_session_pool`.
- App-client-with-store helper that bypasses lifespan (KEEP for pure route/data tests) → `api/v1/session_test_support.py:session_client`.
- Env scrub → `conftest.py:_scrub_inherited_session_env` + `_PRESERVED_PREFIX_KEYS`.

## Design (5 parts — all locked)

### 1. Guard at `_start_session_store` (app-layer, pytest-gated, URL-name only)
In `main.py:_start_session_store`, BEFORE `create_async_pool(...)`: if `os.environ.get("PYTEST_CURRENT_TEST")`, extract the DB name from the resolved URL (`urlsplit(url).path.lstrip("/")`) and `raise RuntimeError(...)` unless it starts with the test prefix. Define a shared `TEST_DB_PREFIX = "tm_test_"` constant and reuse it in BOTH the guard and `TestDb` naming (DRY — do not hardcode the literal twice). Covers clones (`tm_test_…`) and templates (`tm_test_template_…`); never the operator DB.

### 2. Injectable settings seam (replaces env-var + monkeypatch wiring)
Add an optional session-store-URL override to `Settings` (e.g. `session_store_url: str | None`). In the lifespan URL source: `url = settings.session_store_url or resolve_database_url(settings)` — when the override is set it is used VERBATIM (no channel rewrite); when absent, production behaviour is unchanged. Make `create_app(settings: Settings | None = None)` accept injected settings, stash on `app.state.settings`, and have lifespan read from there (fall back to `get_settings()`). Confirm the exact current `create_app`/`lifespan` settings flow first and follow it.

### 3. Canonical lifespan fixture (one seam, no monkeypatch)
Add ONE fixture in `api/conftest.py` (e.g. `lifespan_client(test_db)`) that builds `create_app(settings=<settings with session_store_url=test_db.database_url>)` and enters the REAL lifespan (`TestClient(app)` / `async with lifespan(app)`), yielding the client. This replaces every per-test `TRANSPORT_MATTERS_DATABASE_URL = test_db.database_url` AND every `monkeypatch.setattr(...resolve_database_url...)`.

### 4. TestDb template-clone (speed; additive, inside TestDb only)
- `TestDb.ensure_template(cls, admin_url)` — memoized once per process/worker: create `tm_test_template_{worker}_{hash}` via the existing `connect(admin_url, autocommit=True)` + `CREATE DATABASE` seam, run `upgrade_to_head` ONCE. Key the worker on `os.environ.get("PYTEST_XDIST_WORKER", "gw-main")`. `upgrade_to_head` opens/closes its own connection so the template is left idle and clonable.
- `TestDb.create` fast path — replace the empty `CREATE DATABASE` + `migrate()` body with `CREATE DATABASE <clone> TEMPLATE <template>` against the worker template; keep `tm_test_…` clone naming. `migrate()` (reused by the builder) and `drop()` stay unchanged.
- No second creator, no table list. Default `WAL_LOG` strategy needs no tuning (small schema).

### 5. Env hygiene
In `conftest.py:_scrub_inherited_session_env`, REMOVE `env_keys.DATABASE_URL` from `_PRESERVED_PREFIX_KEYS`. Keep `TEST_DATABASE_URL`, `DOCKER_PG_PORT`, `HOME`. Closes the inherited-launcher-env leak; the guard is the backstop.

### Consolidation (in scope) / Deferred
- IN SCOPE: convert the 5 named leakers + the 2 safer monkeypatch tests onto the canonical fixture; consolidate the 3 duplicate `test_db` wrappers (`api/conftest.py`, `api/v1/conftest.py`, `session/conftest.py`) onto one path (promote to root; remove dupes; reconcile any variation).
- DEFERRED (do NOT do here): the 33-site direct `create_async_pool(test_db.database_url)` seed-helper dedup.

## Build order (guard-first TDD; commit per coherent step)
1. Add `TEST_DB_PREFIX` + the guard in `_start_session_store`. Run the lifespan regression set → the 5 named leakers go RED (guard trips = leak proven). This is the diagnostic.
2. Add the injectable settings seam (Settings field + `create_app(settings=)` + lifespan URL source) and the canonical `lifespan_client` fixture.
3. Convert the 5 leakers + 2 monkeypatch tests to the fixture → lifespan set GREEN. Remove the retired env/monkeypatch wiring.
4. Env hygiene: drop `DATABASE_URL` from preserved keys → full suite green.
5. TestDb template-clone (`ensure_template` + `create` fast path) → suite green AND visibly faster.
6. Consolidate the 3 `test_db` wrappers → green.
7. Self-run `$code-review` and `$code-hygiene` on the diff; fix findings.

## Files (expected touch set)
- `session/testing.py` (template + create fast path; `TEST_DB_PREFIX` may live here)
- `config.py` (Settings `session_store_url` field; possibly the prefix constant)
- `main.py` (`create_app` settings injection; lifespan URL source; guard in `_start_session_store`)
- `api/conftest.py` (canonical `lifespan_client` fixture; `_scrub_inherited_session_env`; consolidated `test_db`)
- `api/v1/conftest.py`, `session/conftest.py` (remove duplicate `test_db`)
- the 5 leaker tests + 2 monkeypatch tests (convert to the fixture)

## Tests / gates (repo recipes, verbatim)
- Lifespan regression: `cd api && just test src/transport_matters/api/v1/test_session_routes.py src/transport_matters/api/v1/test_run_routes.py src/transport_matters/api/v1/test_space_routes.py src/transport_matters/api/v1/test_main_lifespan_shared_proxy.py`
- Config proof: `cd api && just test src/transport_matters/test_channel.py`
- Full API gate: `cd api && just ci`

## Done line (to the orchestrator, one sentence)
`done: fix/pytest-session-store-isolation <sha> PR#<n>` — after `$code-review` + `$code-hygiene` self-pass and lifespan-set + `just ci` green; or `blocked: <one sentence>`.
