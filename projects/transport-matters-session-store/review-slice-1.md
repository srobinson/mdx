# Session Store — Slice 1 Review (Postgres foundation + DAO boundary)

Reviewer: backend-engineer/claude (build reviewer, pane 3.2). One adversarial pass.
PR #34, branch `feat/session-1-pg-foundation` @ fa227b9, against `main` @ d8b944a.
Spec: `spec-session-store.md` (round-2; the 6 prior findings are RESOLVED in the
design and were verified against the build, not relitigated).

Surface reviewed (18 files, +1302/-2): Alembic env + `0001` migration, `session/`
package (`pool.py`, `models.py`, `dao.py`, `artifacts.py`, `testing.py`,
`test_foundation.py`, `__init__.py`), `session_config.py`, `config.py`/`env_keys.py`
wiring, `docker-compose.yml`, `pyproject.toml` deps.

Verdict: **1 blocker, 1 major, 5 minor/nit.** The schema, DAO boundary, upsert
semantics, and test harness are correct and well built; the blocker is a CI-infra
gap (the new tests hard-require Postgres but CI has no Postgres service), and the
major is unverified by-value-artifact decode code shipped a slice early.

Local verification I ran (Postgres 17.10 on `tm:tm@localhost:55432`, the dev's
remapped compose port):
- `ruff format --check` clean; `ruff check` clean; `mypy src/` clean (297 files).
- Full suite: **1225 passed, 0 skipped**.
- `session/test_foundation.py`: **6 passed** against real Postgres.
- Same 6 with the DEFAULT DSN (no reachable PG, the CI condition): **6 errors**, not
  skipped — confirming the tests cannot silently pass without a real database.

---

## 1. BLOCKER — CI has no Postgres service; the session tests hard-require one, so this PR reds GitHub CI

The session tests open a real connection with no skip-guard
(`session/test_foundation.py` fixtures -> `TestDb.create()` -> `connect(admin_url)`
in `session/testing.py:create`). This is the RIGHT call for the "must not silently
skip" requirement, but it makes Postgres a hard precondition of the default `pytest`
run. GitHub CI does not provide one:

- `.github/workflows/ci.yml:40-62` `backend-test` runs `uv run pytest --cov=...`
  with NO `services:` block and no Postgres anywhere in `.github/`.
- `.github/workflows/release.yml:105` runs the same `pytest` with the same gap.
- `ci.yml:116-118` `package` job `needs: [backend-test]`, so the release-chain proof
  also stops.

Proven: with the default DSN (unreachable tm Postgres, exactly the CI condition) all
6 tests ERROR (`psycopg.OperationalError: connection ... port 5432 failed`), they do
not skip. So merging this turns `backend-test` red.

`cd api && just ci` passes LOCALLY only because a tm Postgres is reachable. The
orchestrator's two-part question resolves as: `just ci` green locally with PG; RED in
GitHub CI as configured.

Required correction: add a `postgres:17` service to `ci.yml` `backend-test` (and the
`release.yml` test step) with a health-check and a `TRANSPORT_MATTERS_TEST_ADMIN_DATABASE_URL`
(or `DATABASE_URL`) env pointing the test admin connection at it. Do NOT resolve this
by gating the tests behind a skip — that reintroduces the silent-skip the brief
explicitly warns against. The service is the correct fix; it is a CI-config addition,
small, but it must land with (or immediately ahead of) this PR or CI breaks on merge.

## 2. MAJOR — the by-value inline-artifact decode path ships in slice 1 with zero call sites and zero tests

`session/artifacts.py` ships `inline_artifacts_from_ir`, `inline_artifacts_from_parts`,
`inline_artifact_from_image`, `_decode_base64_source`, `_decode_data_url`,
`_source_ref` (~55 LOC). Nothing in this slice calls them (the ingest path that
consumes them is a later slice) and no test exercises them — `test_foundation.py`
imports only `artifact_hash`. This is precisely the security-relevant by-value capture
that round-1 finding 6 hardened (claude inline base64 + codex `data:` URL), now
shipped unverified. The decode has real edge cases: `base64.b64decode(validate=True)`
-> `binascii.Error`/`ValueError` -> `None` (good defensive skip, but untested), and
`data:` URL header parsing (`;base64` gate, `removeprefix("data:")`, media-type split).
I read it and it looks correct, but "looks correct + untested + already in the tree"
is how a subtle decode bug survives to the ingest slice.

`artifact_hash` itself IS used (by the DAO) and IS tested — keep it. For the decode
functions, either (a) add pure-function unit tests now (they need no Postgres: one
claude `{"data":...,"media_type":...}` source, one codex `{"image_url":"data:...;base64,..."}`
source, one bad-base64 -> `None`), or (b) move the decode into the slice that calls
it. As-is it is unverified surface area.

## 3. MINOR — `session/testing.py` ships in the production wheel

The wheel exclude is `**/test_*.py` + `conftest.py` (`pyproject.toml`
`[tool.hatch.build.targets.wheel]`). `testing.py` does not match `test_*` so the
`TestDb` harness ships in the distributed package, and it pulls a top-level `alembic`
import into "production" code. It is self-consistent (alembic is now a runtime dep,
and `migrations_dir()` handles both source-tree and installed-wheel layouts), so this
is not a breakage. But test-support code in the shipped wheel is a cleanliness gap.
Confirm intentional (a deliberately-public `.testing` utility) or exclude it.
Note: `testing.py` is also treated as PRODUCTION by the privacy-import lint
(`is_test()` matches `_support.py`/`test_`/`fixtures`/`conftest`, not `testing.py`) —
it passes today (only public imports) but the classification is worth knowing.

## 4. MINOR — default DSN port is decoupled from the compose port var

`session_config.DEFAULT_DATABASE_URL` / `DEFAULT_TEST_ADMIN_DATABASE_URL` hardcode
`:5432`, but `docker-compose.yml` parameterizes the host port as
`${TRANSPORT_MATTERS_POSTGRES_PORT:-5432}`. A dev who must remap (5432 already taken —
observed live on this machine: another Postgres held 5432, the tm container was on
55432) has to ALSO hand-set `TRANSPORT_MATTERS_DATABASE_URL` and the test-admin env,
or every session test errors with a confusing "server closed the connection". Worth a
README/`doctor` note, or derive the default port from the same env var so compose and
the app agree.

## 5. NIT — `script.py.mako` scaffolds a reversible `downgrade()` while policy is forward-only

`0001` correctly enforces the durable-store policy with
`downgrade(): raise RuntimeError("session store migrations are forward only")`, but
the generator template (`migrations/script.py.mako`) scaffolds `downgrade(): pass` for
future revisions, which reads as silently reversible. Scaffold a `raise` to keep new
migrations consistent with the forward-only stance (§8).

## 6. NIT — eval/learn reads don't filter `kind='turn'` as §2.1 states

`_IR_SEARCH_SQL` and `_TEXT_SEARCH_SQL` (`dao.py`) omit `WHERE kind='turn'`. Harmless
today: meta rows have `ir IS NULL` (so `ir @>` never matches) and `search_text` NULL
(so `content_tsv` is empty and never matches). But §2.1 specifies the filter, and the
implicit reliance on NULL semantics breaks if a meta row ever gains `ir`/`search_text`.
Add the explicit `kind='turn'` predicate to match the spec and be robust.

## 7. NIT — pool lifecycle is untested

`create_pool`/`create_async_pool` (correct `open=False` psycopg3 idiom) and
`transaction`/`async_transaction` have no open/close test. They are thin wrappers, but
the `open=False` -> `await pool.open()` lifecycle is the easy-to-break seam the writer
slice will depend on. An optional smoke test (open pool, run `SELECT 1`, close) would
de-risk the next slice.

---

## What is correct (positively justified, not "none found")

- **Migration is a faithful 1:1 of spec §2 DDL.** Verified every column/type/constraint/
  index in `0001_session_store_foundation.py`: event PK `(session_id, seq)` (finding 1),
  `session_native_uq (owner, run_id, provider, native_session_id) WHERE native_session_id
  IS NOT NULL` (finding 5 owner dim present), `content_tsv` GENERATED ALWAYS ... STORED
  with `to_tsvector('english', coalesce(...))`, both GINs (`event_ir_gin`, `event_fts_gin`),
  `session_fork_ck ((parent IS NULL) = (forked_at_seq IS NULL))`, `event_kind_ck`, FK
  cascades (event->session, event_artifact composite FK->event), artifact `bytea` + `hash`
  PK dedup. Forward-only: no schema_meta drop-rebuild gate ported (Alembic version table
  replaces it, §8); `downgrade()` raises. Raw `op.execute` DDL (not `op.create_table`) is
  the right choice here — 1:1 with the reviewed spec for PG-specific generated/partial/GIN
  features; `target_metadata=None` (no autogenerate) is consistent with hand-authored.
- **DAO boundary is clean.** Methods return frozen Pydantic rows (`SessionRow`/`EventRow`/
  `ArtifactRow`/`EventArtifactRow`); no psycopg `Connection`/`Cursor`/`DictRow` leaks past
  the public surface (the injected connection in the constructor is the standard DAO seam,
  mirrors `index/db.py`). All SQL is parameterized via `%(name)s` (no value-level f-string
  interpolation — the f-strings only splice constant column lists); the harness uses
  `psycopg.sql.Identifier` for the dynamic DB name. `INSERT ... ON CONFLICT (hash) DO
  NOTHING RETURNING` is correctly handled with the fetch-existing fallback (the classic
  "DO NOTHING returns no row" trap is avoided).
- **Upsert semantics match spec §3.3.** `cli`/`native_session_id`/`source_descriptor`/
  `home_dir` use `COALESCE(session.col, EXCLUDED.col)` (launch-authoritative facts never
  clobbered to NULL), `minted = session.minted OR EXCLUDED.minted`, `owner`/`status`
  last-writer-wins (import re-owning), lineage COALESCEd. The independent lineage COALESCE
  cannot break `session_fork_ck` for any well-formed row; the DB check is the backstop and
  the test proves it fires.
- **Test harness is sound and safe.** Unique DB `tm_test_{pid}_{uuid4().hex}` (parallel-safe);
  CREATE/DROP DATABASE on an autocommit admin connection to the `postgres` maintenance DB
  (cannot run in a txn — handled); `pg_terminate_backend` before DROP; drop-on-failure in
  `create()` plus the fixture finalizer's `drop()`; never targets the dev `transport_matters`
  DB. `autocommit=True` for the multi-violation constraint tests is a deliberate, correct
  choice — it avoids aborted-transaction poisoning across the `pytest.raises` blocks.
- **Tests prove the invariants, not just "tables exist":** round-trip equality
  (session+event+artifact+link), native_uq fires on the 4th duplicate while 3 differing-key
  rows coexist, `CheckViolation` (fork pairing) + `ForeignKeyViolation` (missing parent),
  GIN `@>` containment match, generated-tsvector `websearch_to_tsquery` ranking, and the
  async DAO round-trip.
- **Repo invariants respected:** import DAG (`session/` -> `ir`/`config`/`session_config`/
  capture deps; no `storage -> session` back-edge); privacy boundary clean (no cross-module
  `_`-name imports); builtins-only typing with every `Any` commented; Pydantic v2 frozen
  models with `use_enum_values`; LOC within budget (largest new file `dao.py` 326 < 700);
  no em dashes. mypy/ruff clean.

---

## Final verification

- Finding 1 (CI Postgres service): OPEN — blocker, fix is CI config.
- Finding 2 (untested inline-artifact decode): OPEN — major.
- Findings 3-7: OPEN — minor/nit, non-blocking.
- Schema / DAO / upsert / harness / tests / invariants: VERIFIED CORRECT.

---

# settings.toml config layer (delta review)

Delta: PR #34 `fa227b9..46ff547` ("feat(config): add settings toml database layer").
Contract: `littleorgans-settings-config-contract.md` (authored for Rust `lilo`;
translated to TM/Python). This delta also closes slice-1 finding 4 (compose port
decoupling) and the spirit of finding 1's silent-default concern.

Verdict: **strong, 0 blocker / 0 major in the delta itself; 3 minor/nit, plus 1
carryover.** Every contract checkpoint is met and the resolution fails loud at
resolution time with actionable guidance. Verified locally against the docker-compose
Postgres (55432): `cd api && just ci` GREEN (ruff + mypy clean, **1231 passed, 0
skipped** = slice-1's 1225 + 6 new config tests); the 12 `test_config.py` tests pass
with NO database env set (hermetic); `rg` confirms the silent default DSN is gone.

## s1. NIT — `config.py` imports/re-exports `DATABASE_URL`/`TEST_DATABASE_URL` it never uses

`config.py` imports `DATABASE_URL, TEST_DATABASE_URL` from `env_keys` and lists them in
`__all__`, but the logic uses neither (the guidance strings hardcode the literal
`"TRANSPORT_MATTERS_DATABASE_URL"`, which is explicitly sanctioned by `env_keys.py`'s
"display copy keeps literals" convention). So the two constants are imported solely to
be re-exported, unused in the module, mildly muddying the env-keys single source.
Either drop the imports + `__all__` entries, or consume the constants. Low priority.

## s2. NIT — the `extra="forbid"` ValidationError branch of `load_toml_settings` is untested

`load_toml_settings` catches `tomllib.TOMLDecodeError` AND `ValidationError`, both
mapped to `SettingsFileError`, and `DatabaseSettings`/`TomlSettings` use
`extra="forbid"` (good: a typo'd `[databse]` table or `urll` key fails loud, not
silently to defaults). But `test_malformed_settings_toml_errors` only exercises the
syntax (TOMLDecodeError) arm; the unknown-key -> ValidationError -> SettingsFileError
arm has no test. Cheap to add (`[database]\nbogus = 1` -> `SettingsFileError`). The
forbid config plus the syntax test is decent coverage, but the second except-arm is a
real untested path.

## s3. NIT — `Settings` carries three overlapping DB fields

`database_url` (env scalar), `test_database_url` (env scalar), and `database` (nested
toml model) coexist, so `settings.database_url` is the ENV value while
`settings.database.url` is the TOML value. The `resolve_*` functions encapsulate the
precedence correctly and are the intended call surface, but the raw fields read
ambiguously. A one-line field docstring (env-override vs toml-source) would prevent a
future caller from reading `settings.database.url` directly and bypassing the env
layer.

## s4. CARRYOVER — the CI-Postgres blocker (finding 1) is NOT resolved by this delta

The delta makes the DB config loud and env-overridable, which is exactly what a CI
`services: postgres` + `env: TRANSPORT_MATTERS_TEST_DATABASE_URL` block would consume,
so the fix is now even more mechanical. But GitHub CI `backend-test` still runs
`uv run pytest` with no Postgres service and no DB env, so the 6 `session/` foundation
tests still ERROR in CI (now with `MissingDatabaseConfigError` + guidance instead of a
raw connection refusal, a clearer message but still a hard failure, not a skip). The 6
new `test_config.py` tests are hermetic and pass in CI. Blocker stands, narrowed to the
session foundation tests.

## What is correct (positively justified)

- **Silent default deleted, fails loud:** `session_config.py` removed; `database_url`
  default dropped (`str | None = None`); `rg` over `api/src` finds no `localhost:5432`,
  `DEFAULT_DATABASE_URL`, `session_config`, or `TEST_ADMIN_DATABASE_URL`. Resolution
  raises `MissingDatabaseConfigError` naming the env var + `~/.transport-matters/settings.toml`
  + "copy settings.example.toml". The raise is at RESOLUTION (`resolve_database_url`/
  `resolve_test_database_url`), not at `Settings.load()`, so the broad app/test surface
  that never touches the DB is unaffected (1225 unrelated tests still green).
- **Precedence env-over-toml, correct and tested:** `resolve_database_url` =
  `database_url(env) ?? database.url(toml) ?? raise`; `resolve_test_database_url` =
  `test_database_url(env) ?? database_url(env) ?? database.test_url(toml) ?? database.url(toml)
  ?? raise` — exactly the contract chain. Proven by `test_database_url_resolves_env_over_toml`
  and `test_test_database_url_falls_back_through_env_and_toml`.
- **No duplicated env reads:** slice-1's dual read (testing.py direct `os.environ` +
  pydantic Settings) is unified — `testing.py` now calls
  `resolve_test_database_url(Settings.load())`; the env read flows through the pydantic
  Settings fields only. `migrations/env.py` also routed through the loud resolver.
- **tomllib + Pydantic only:** no new dependency added; `tomllib` (stdlib, already used
  in `cli/home_seed.py`); Pydantic `BaseModel` with `extra="forbid"`. No
  figment/config/dynaconf.
- **File location + load semantics:** `settings.example.toml` committed at REPO ROOT
  (not `api/`); live file = `storage_dir/settings.toml` = `~/.transport-matters/settings.toml`,
  honoring a `TRANSPORT_MATTERS_STORAGE_DIR` override; missing file -> defaults,
  malformed -> `SettingsFileError`. Both proven.
- **Hermetic tests, env-first:** all 6 new tests use `tmp_path` + `monkeypatch`; pass
  with NO DB env (12/12 `test_config.py` green with both vars unset); never read the
  dev's real home (`load_from` takes an explicit path; the connect test overrides
  `STORAGE_DIR` to `tmp_path`). The three required tests are present:
  malformed-errors, missing-yields-defaults, and the loud-error-no-connect path
  (`test_session_connect_error_does_not_attempt_connection` monkeypatches
  `Connection.connect` and asserts it is never called).
- **Compose + port alignment:** `TRANSPORT_MATTERS_POSTGRES_PORT` ->
  `TRANSPORT_MATTERS_DOCKER_PG_PORT` (default 55432) with a `127.0.0.1:` loopback bind
  (security improvement over slice-1's all-interfaces bind); `DOCKER_PG_PORT` and
  `TEST_DATABASE_URL` registered in `env_keys.py` (single source); `.env.example` and
  `settings.example.toml` aligned to 55432.
- **Minimal scope:** only `[database] url`/`test_url` flow through toml; proxy/web
  ports, storage_dir, cli/run_id/etc stay pure env. `.env` loading removed cleanly
  (justfile `install` no longer copies `.env`; `.env.example` reframed as a shell-export
  reference).
- **DAG / privacy / LOC:** `config.py` imports only stdlib + pydantic + env_keys +
  storage_roots (no session import; `pool -> config` is one-way, no cycle); `_resolved_url`
  is module-private in `pool.py`; `config.py` ~190 LOC < 700; mypy + ruff clean on 297
  files. Dead `resolve_database_url`/`DEFAULT_*` re-exports removed from `session/__init__`.

## settings.toml final verification

- Silent default DSN deleted + loud guided failure: VERIFIED (rg clean; resolver raises;
  no-connect test green).
- Precedence / no-dup-env / tomllib+Pydantic / example-at-root / hermetic 3 tests /
  compose rename + 55432 / minimal scope / DAG-LOC-privacy-DRY: VERIFIED.
- `just ci` against docker-compose Postgres: GREEN (1231 passed, 0 skipped).
- Delta findings s1-s3: minor/nit, non-blocking. s4: the slice-1 CI-Postgres blocker
  persists (unchanged by this delta).

---

# Round-2 verification (PR #34 @ af2afc4)

Verification pass over `46ff547..af2afc4` ("fix(session): clear postgres foundation
review"). One line per open finding:

- Finding 1 (BLOCKER, CI Postgres service): RESOLVED. A `postgres:17` service +
  `TRANSPORT_MATTERS_TEST_DATABASE_URL` env are added to `ci.yml` `backend-test` AND
  `release.yml` `build`; both pytest steps run against it (verified in the yaml, with
  health-check on the `postgres` maintenance DB tm connects to). Actions now runs the
  session tests for real instead of erroring.
- Finding 2 (MAJOR, untested inline-artifact decode): RESOLVED. `artifacts.py` KEPT;
  new `session/test_artifacts.py` covers claude base64 `source.data`, codex `data:` URL
  `source.image_url`, and the invalid-base64 -> skip path (pure, no DB).
- Finding 3 (testing.py ships in wheel): RESOLVED. `pyproject.toml` wheel `exclude` now
  lists `src/transport_matters/session/testing.py`.
- Finding 4 (default DSN port decoupled from compose): RESOLVED earlier in the
  settings.toml delta (`DOCKER_PG_PORT` rename + 55432 alignment).
- Finding 5 (mako scaffolds reversible downgrade): RESOLVED. `script.py.mako`
  `downgrade()` now scaffolds `raise RuntimeError("session store migrations are forward
  only")`.
- Finding 6 (eval/learn reads miss `kind='turn'`): RESOLVED. `_IR_SEARCH_SQL` and
  `_TEXT_SEARCH_SQL` now filter `kind = 'turn'`, and the GIN/FTS tests were strengthened
  with a `kind='meta'` row carrying a matching `ir`/`search_text` to prove the explicit
  filter excludes it (no longer relying on NULL semantics).
- Finding 7 (pool lifecycle untested): RESOLVED. `test_sync_pool_and_transaction_lifecycle`
  and `test_async_pool_and_transaction_lifecycle` exercise `create_pool`/`create_async_pool`
  open -> connection+transaction -> close.
- Nit s1 (config re-exports unused env-key consts): RESOLVED. The `DATABASE_URL`/
  `TEST_DATABASE_URL` imports + `__all__` entries are removed.
- Nit s2 (`extra="forbid"` ValidationError arm untested): RESOLVED.
  `test_invalid_settings_toml_extra_keys_error` proves an unknown `[database]` key ->
  `SettingsFileError`.
- Nit s3 (three overlapping DB fields read ambiguously): RESOLVED. Each field now carries
  a `description` distinguishing env-override vs toml-source and pointing at `resolve_*`.

Verified locally: `cd api && just ci` GREEN @ af2afc4 vs docker-compose Postgres (55432):
ruff + mypy clean, **1237 passed, 0 skipped** (1231 + 3 artifacts + 2 pool + 1 extra-keys).

RESIDUAL: none open. Two nits I'd note as informational, not blocking: the CI service
binds host `5432:5432` (the workflow's own choice; fine on a clean runner) while local dev
uses the 55432 loopback bind, and the CI sets only `TEST_DATABASE_URL` (sufficient, since
no test resolves the operator `DATABASE_URL` without an explicit arg). Neither blocks.

## SIGN-OFF

All blocker, major, minor, and nit findings from the slice-1 and settings.toml reviews are
RESOLVED and verified (CI workflow yaml + a green `just ci` against real Postgres). Slice 1
(Postgres foundation, DAO boundary, settings.toml config layer) is APPROVED to merge.
