# littleorgans Postgres Persistence Plan

Status: expert reviewed plan  
Date: 2026-06-06  
Scope: littleorgans v1 persistence boundary cleanup and Postgres migration

## Goal

Move littleorgans from SQLite-shaped persistence to a clean persistence boundary
that can run on Postgres for local native, Docker Compose, and cloud managed
deployments.

The plan treats Postgres as the target backend. It does not preserve SQLite as a
long-term supported backend. The repo is pre-release, so breaking changes are
allowed when they simplify the design.

## Problem Statement

The current database implementation leaks through the application boundary:

- `lilo-db` exposes `sqlx::SqlitePool` directly.
- Session exports `SqliteStore`.
- Identity exports `SqliteAuditSink`.
- Cross-component paths pass `SqliteConnection`, `PoolConnection<Sqlite>`, and
  `sqlx::Sqlite`.
- Transaction semantics name SQLite behavior, including `BEGIN IMMEDIATE`, WAL,
  and PRAGMAs.
- Tests construct temp SQLite paths and `lilo.db` paths directly.
- Doctor, docs, snapshots, and protocol surfaces say `sqlite`.

The migration should fix the design boundary first. Postgres then becomes a
backend migration rather than a broad SQLite naming sweep.

## Non Goals

- No dual SQLite plus Postgres production backend.
- No automatic migration from existing local `~/.lilo/data/lilo.db` rows.
- No v2 distributed persistence, multi-host topology, etcd, or sagas.
- No compatibility aliases for removed SQLite-specific env vars, flags, or
  code paths.
- No new tests that assert removed SQLite names stay removed.

## Working File Set

The initial deduped SQLite/path/test coupling scan surfaced 49 files. Expert
review added four active protocol and test surfaces, so the working set is 53
files:

```text
crates/lilo-common/src/id.rs
crates/lilo-im-store/src/lib.rs
crates/lilo-im-store/src/sqlite/audit.rs
crates/lilo-im-store/tests/audit.rs
crates/lilo-paths/src/lilo.rs
crates/lilo-rm-core/src/admin.rs
crates/lilo/src/cli/doctor.rs
crates/lilo/src/cli/doctor/runtime.rs
internal/db/migrations/0001_unified_schema.sql
internal/db/src/lib.rs
internal/identity/service/src/client.rs
internal/runtime/app/src/cli/initdb.rs
internal/runtime/app/tests/common/harness.rs
internal/runtime/app/tests/common/lifecycle.rs
internal/runtime/app/tests/critical_scenarios.rs
internal/runtime/app/tests/integration_events_cursor.rs
internal/runtime/app/tests/integration_pass4.rs
internal/runtime/app/tests/integration_pass7.rs
internal/runtime/daemon/src/handler/tests.rs
internal/runtime/daemon/src/identity.rs
internal/runtime/daemon/src/reconcile/tests.rs
internal/runtime/daemon/src/server/config.rs
internal/runtime/daemon/src/server/runner.rs
internal/runtime/daemon/src/server/tests.rs
internal/runtime/daemon/src/service.rs
internal/runtime/daemon/src/spawn_preflight/tests/helpers.rs
internal/runtime/daemon/src/test_support.rs
internal/runtime/store/src/config.rs
internal/runtime/store/src/lib.rs
internal/runtime/store/src/sqlite/lifecycle.rs
internal/runtime/store/src/sqlite/lifecycle/codec.rs
internal/runtime/store/src/sqlite/lifecycle/tests.rs
internal/session/app/src/tool_docs.rs
internal/session/app/tests/cli_get_test/run_resolution.rs
internal/session/app/tests/common/mod.rs
internal/session/daemon/src/handler/spawn.rs
internal/session/daemon/src/identity_client.rs
internal/session/daemon/tests/common/mod.rs
internal/session/driver/src/conv.rs
internal/session/store/src/lib.rs
internal/session/store/src/sqlite.rs
internal/session/store/src/sqlite/events.rs
internal/session/store/src/sqlite/labels.rs
internal/session/store/src/sqlite/mail_tests.rs
internal/session/store/src/sqlite/mail.rs
internal/session/store/src/sqlite/namespaces.rs
internal/session/store/src/sqlite/sessions_tests.rs
internal/session/store/src/sqlite/sessions.rs
internal/session/store/src/sqlite/spawn_intents.rs
tests/integration/src/lib.rs
tests/integration/tests/db_contract.rs
tests/integration/tests/session_spawn_contract.rs
tests/integration/tests/shutdown_contract.rs
```

This list is a planning input, not a promise that every file must be edited.

## Phase 0: Lock Decisions And Baseline

Purpose: prevent parallel workers from designing different persistence systems.

Decisions to lock:

1. Postgres is the single target backend.
2. SQLite may remain temporarily inside private modules while migration is in
   flight, but it is not a supported final backend.
3. The operator database contract is `LILO_DATABASE_URL`.
4. Existing local SQLite data is disposable for this pre-release migration.
5. `lilo-im-store` remains publishable. It must not depend on internal
   unpublished crates such as `lilo-db`.
6. `LiloDb` may expose a concrete `PgPool` internally during the Postgres-only
   migration. Do not introduce a wider database abstraction until there is a
   second supported backend.
7. Migrations become Postgres migrations. Any SQLite migration files that remain
   during the transition are private compile scaffolding and must be deleted
   before final cleanup.
8. `lilo-im-store` uses feature-gated backend support without depending on
   `lilo-db`. The target shape is a publishable neutral audit API with Postgres
   support, not only a renamed `SqliteAuditSink::with_pool(SqlitePool)`.
9. Postgres test database provisioning is part of Phase 1.a, not a later ops
   task. Store and integration gates cannot require Postgres until fixtures can
   create isolated databases deterministically.
10. Owner seam. Every persisted table carries `owner TEXT NOT NULL DEFAULT
    'local'` from the first Postgres schema. v1 writes `'local'` everywhere,
    enables no RLS, and adds no multi-tenant logic; the column plus a per-owner
    RLS seam is a hosting-ready schema affordance, explicitly not v2
    multi-tenancy behavior. Locked now because it is one column today and a
    painful data backfill once Phase 2 ships real schema and rows. (borrowed
    from transport-matters session-store, 2026-06-06)
11. Forward-only migrations. Once real Postgres data exists, migrations are
    additive only: no drop-and-rebuild. The pre-release "local data is
    disposable" allowance (decision 4) applies only while no real Postgres data
    exists; this decision closes that door at the right moment.

Baseline commands:

```bash
fmm validate
just check
just build
just test
```

Exit criteria:

- A short implementation decision note exists.
- The current gate status is known.
- The `LILO_DATABASE_URL`, `PgPool`, migration layout, `lilo-im-store`, and test
  fixture decisions above are accepted.
- No worker starts code changes before the `lilo-db` API shape is approved.

## Phase 1: Persistence Boundary

### Phase 1.a: `lilo-db`

Purpose: make `lilo-db` the single internal database boundary.

Detailed contract:
`/Users/alphab/.mdx/projects/littleorgans-postgres-phase-1a-lilo-db-contract.md`

Expected design:

- `LiloDb` remains the central internal handle.
- `LiloDb` owns connection creation, migrations, pool lifecycle, and shutdown.
- `lilo-db` exposes backend-neutral transaction helpers.
- Public helper names stop encoding SQLite transaction behavior.
- Test fixture creation moves behind `lilo-db`.
- `lilo-db` owns deterministic Postgres test provisioning: create database, run
  migrations, return a fixture handle, and drop the database on cleanup.
- Local Compose or CI service provisioning exists early enough for Postgres
  tests to run before store migration gates require them.
- Normal application setup no longer builds database paths outside `lilo-db`.
- Existing SQLite pool accessors may remain only as explicit transition
  scaffolding while current stores still compile against SQLite types. Phase 1.a
  handoff must list every remaining transition symbol and the phase that removes
  it.

Likely files:

```text
Cargo.toml
internal/db/Cargo.toml
internal/db/src/lib.rs
internal/db/migrations/0001_unified_schema.sql
docker-compose.yml
crates/lilo-paths/src/env.rs
crates/lilo-paths/src/lilo.rs
internal/runtime/store/src/config.rs
internal/runtime/app/src/cli/initdb.rs
tests/integration/tests/db_contract.rs
```

Acceptance:

- No application code imports `SqlitePool` from `lilo-db`.
- No application code calls `LiloDb::open_path` for normal runtime setup.
- Test helpers can create an isolated database through one `lilo-db` fixture.
- A local Postgres service can be started through the documented Compose path or
  an equivalent repo-local service command.
- CI or local gate documentation identifies the Postgres service requirement.
- Any remaining SQLite accessors in `lilo-db` are marked as transition
  scaffolding and have a removal owner in the Phase 1.a handoff.
- `scripts/check-env.sh --check` passes after any new env var is added to the
  registry and docs.

Suggested verification:

```bash
cargo test -p lilo-db
just check
```

### Phase 1.b: Store Boundary

Purpose: make domain stores depend on the database boundary, not SQLite types.

Expected design:

- `lilo-session-store` exports `SessionStore`, not `SqliteStore`.
- `lilo-runtime-store` keeps `LifecycleStore`, but no exported or cross-component
  signatures mention `SqliteConnection`, `SqlitePool`, or `sqlx::Sqlite`.
- `lilo-im-store` exports a neutral audit store or sink name. Because it is
  publishable, it cannot depend on unpublished `lilo-db`.
- Backend-specific modules are private implementation details.
- Cross-component transaction work goes through a shared `lilo-db` transaction
  or through narrow store methods.

Special constraint:

`lilo-im-store` is published. Its boundary needs special handling. Options:

1. Chosen path: give it feature-gated Postgres support without depending on
   `lilo-db`.
2. Keep the public audit API backend-neutral. Do not merely rename
   `SqliteAuditSink::with_pool(SqlitePool)` while leaving a concrete pool type
   in the published boundary.
3. Identity service wiring may use `LiloDb` internally, but the publishable
   crate API must remain usable without an internal crate dependency.

Likely files:

```text
crates/lilo-im-store/src/lib.rs
crates/lilo-im-store/src/sqlite/audit.rs
internal/identity/service/src/client.rs
internal/runtime/store/src/lib.rs
internal/runtime/store/src/sqlite/lifecycle.rs
internal/session/store/src/lib.rs
internal/session/store/src/sqlite.rs
internal/session/store/src/sqlite/*.rs
internal/session/daemon/src/handler/spawn.rs
internal/session/daemon/src/identity_client.rs
```

Acceptance:

- `rg "SqlitePool|SqliteConnection|sqlx::Sqlite|PoolConnection<Sqlite>" internal/session internal/runtime internal/identity crates/lilo-im-store` shows no cross-component API leaks.
- Store names exposed to callers are backend-neutral.
- Existing SQLite implementation, if still present, is private and transitional.
- Focused store tests pass.
- Published `lilo-im-store` APIs no longer require SQLite concrete types.

Suggested verification:

```bash
cargo test -p lilo-session-store
cargo test -p lilo-runtime-store
cargo test -p lilo-im-store
just check
```

## Phase 2: Postgres Backend

Purpose: replace the private SQLite implementation with Postgres.

Schema changes:

- ID columns become `uuid` or remain `text` by explicit decision. Prefer `uuid`
  unless short-prefix behavior forces too much churn.
- Timestamp text columns become `timestamptz` where the domain uses time values.
- Cursor blobs become `bytea`.
- SQLite `strftime` initialization becomes a Postgres timestamp expression.
- `_sqlx_migrations` remains sqlx-owned.
- Owner seam (decision 10): add `owner TEXT NOT NULL DEFAULT 'local'` to the
  session, runtime lifecycle, and identity audit tables, and fold `owner` into
  the relevant unique indexes. RLS is a documented future seam, not enabled in
  v1.
- Evaluate, do not force, Postgres-rich payload types: JSONB + GIN for
  structured columns that are queried (candidates: `agent_config`,
  `evaluation_trace`) and a STORED generated `tsvector` column where content is
  searched (candidate: `messages.content`). Default to `text`/`bytea` unless a
  concrete containment or full-text query exists. (borrowed from
  transport-matters session-store)

Query changes:

- Replace SQLite placeholders with Postgres placeholders where needed.
- Replace SQLite PRAGMAs and `sqlite_master` introspection.
- Replace `BEGIN IMMEDIATE` with Postgres transaction semantics.
- Preserve idempotency and conflict behavior with Postgres `ON CONFLICT`.
- Fix prefix selector lookup. If IDs are native `uuid`, use `id::text LIKE $1`
  or an equivalent indexed strategy.

Likely files:

```text
internal/db/src/lib.rs
internal/db/migrations/0001_unified_schema.sql
internal/session/store/src/sqlite/*.rs
internal/runtime/store/src/sqlite/lifecycle.rs
internal/runtime/store/src/sqlite/lifecycle/codec.rs
crates/lilo-im-store/src/sqlite/audit.rs
crates/lilo-common/src/id.rs
```

Acceptance:

- Postgres-backed unit tests pass for session, runtime, and identity stores.
- Prefix selector behavior is unchanged at the user level.
- Mail idempotency behavior is unchanged.
- Spawn intent transaction behavior is unchanged.
- Runtime lifecycle reconcile behavior is unchanged.

Suggested verification:

```bash
docker compose up -d postgres
cargo test -p lilo-db
cargo test -p lilo-session-store
cargo test -p lilo-runtime-store
cargo test -p lilo-im-store
```

## Phase 3: Caller Migration

Purpose: migrate the remaining application, daemon, doctor, and integration
callers to the new boundary.

Work groups:

1. Session daemon and session app.
2. Runtime daemon and runtime app.
3. Identity service and audit wiring.
4. Integration fixtures.
5. Doctor, admin protocol, and human output.

Likely files:

```text
internal/session/daemon/**
internal/session/app/**
internal/runtime/daemon/**
internal/runtime/app/**
internal/identity/service/**
tests/integration/**
crates/lilo/src/cli/doctor.rs
crates/lilo/src/cli/doctor/runtime.rs
crates/lilo-rm-core/src/admin.rs
internal/session/driver/src/conv.rs
```

Acceptance:

- No direct application caller opens `lilo.db`.
- No direct application caller creates a temp SQLite database.
- Integration tests create isolated Postgres databases through the shared
  fixture.
- Doctor reports backend-neutral database health or Postgres health.
- Admin and driver protocol surfaces no longer expose `sqlite` field names for
  active database health.

Suggested verification:

```bash
docker compose up -d postgres
cargo test -p lilo-session-daemon
cargo test -p lilo-runtime-daemon
cargo test -p lilo-runtime-app
cargo test -p lilo-session-app
cargo test -p lilo-integration-tests
```

## Phase 4: Local, Compose, Cloud

Purpose: make the Postgres backend usable in the three target environments.

Local native:

- Document installing or running local Postgres.
- `LILO_DATABASE_URL` points at a local database.
- Test fixture can create and drop isolated test databases.

Docker Compose:

- Add a Compose file or documented service snippet for Postgres.
- Use health checks.
- Provide a local URL example.
- Make the Compose service the same path used by developer and CI Postgres
  verification unless CI has a stronger native service primitive.

Cloud:

- Support standard Postgres URLs.
- Document TLS expectations if required.
- Avoid baking provider-specific behavior into the core.

Acceptance:

- Fresh local native setup can run migrations and perform a deterministic daemon
  smoke.
- Compose setup can run migrations and perform the same deterministic daemon
  smoke.
- Cloud managed URL can run migrations and perform the same deterministic daemon
  smoke, assuming network access and valid credentials.

Suggested verification:

```bash
docker compose up -d postgres
just check
just build
just test
```

Required smoke shape:

```bash
LILO_DATABASE_URL=postgres://... cargo run -p lilo -- doctor
LILO_DATABASE_URL=postgres://... cargo run -p lilo -- daemon start --foreground
```

If the daemon command cannot run in the foreground today, Phase 4 includes the
small CLI or harness change needed to make the smoke bounded and deterministic.

## Phase 5: Cleanup And Naming

Purpose: remove SQLite-shaped residue after the backend migration is green.

Cleanup targets:

- Module names.
- Type names.
- Error messages.
- Doctor output.
- Runtime response fields named `sqlite`.
- Snapshot files.
- README and architecture docs.

Acceptance:

- `rg "Sqlite|sqlite|SQLite|lilo.db|PRAGMA|BEGIN IMMEDIATE|sqlite_master" internal crates tests docs README.md` returns only approved historical notes or no hits.
- `fmm generate && fmm validate` is green if files or symbols moved.
- Full repo gate is green.

Required final proof:

```bash
just check
just build
just test
fmm generate
fmm validate
```

## Warroom Execution Model

Use a warroom only after Phase 0 decisions are locked and Phase 1.a has a single
approved `lilo-db` contract. Do not let multiple agents independently invent
the database boundary.

Recommended split:

1. `lilo-db` owner: connection, migration, transaction, fixture API.
2. Session store owner: `lilo-session-store` and session daemon use sites.
3. Runtime store owner: `lilo-runtime-store` and runtime daemon use sites.
4. Identity owner: `lilo-im-store` publishable boundary and identity service.
5. Test and surface owner: integration fixtures, doctor, docs, snapshots, CI.

Use peer consensus on:

- Phase 1.a API shape.
- The ID column type decision.
- The `owner` column type and its inclusion in unique indexes (decision 10).
- Any later change to the chosen `lilo-im-store` publishability decision.
- Any later change to the chosen Postgres test fixture strategy.

## Risks

1. `lilo-im-store` publishability can be broken by a naive dependency on
   `lilo-db`.
2. Prefix selectors may become inefficient or awkward if IDs move to native
   Postgres `uuid`.
3. Transaction behavior can drift when replacing `BEGIN IMMEDIATE`.
4. Tests can become slow or flaky if each test uses an external database without
   cheap isolation.
5. A dual-backend compromise would recreate the current leak with more code.
6. If Postgres fixtures and service provisioning land after store conversion,
   acceptance gates become un-runnable and workers will optimize for compile
   progress over proof.

## Recommended Next Step

Run a two-pane peer consensus review on the Phase 1.a `lilo-db` contract, then
apply any required edits before implementation spreads to store crates.
