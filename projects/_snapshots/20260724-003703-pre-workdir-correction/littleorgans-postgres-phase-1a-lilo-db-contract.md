# littleorgans Postgres Phase 1.a `lilo-db` Contract

Status: draft for expert revalidation  
Date: 2026-06-06  
Parent plan: `/Users/alphab/.mdx/projects/littleorgans-postgres-persistence-plan.md`

## Purpose

Phase 1.a creates the internal database boundary that every later store and
caller migration uses. The objective is to introduce the Postgres `lilo-db`
target contract, fixture path, and service path without forcing every current
SQLite typed store to migrate in the same slice.

This phase does not migrate every store query. It creates the Postgres
connection, migration, transaction, fixture, and local service foundation that
later phases depend on. Existing SQLite store wiring may remain only as explicit
transition scaffolding until Phase 1.b removes the cross component leaks.

## Locked Decisions

1. Postgres is the single target backend.
2. `LILO_DATABASE_URL` is the operator database contract.
3. Existing local SQLite data is disposable.
4. `LiloDb` may expose concrete Postgres sqlx types to internal crates during
   this Postgres only migration.
5. API names stay backend neutral even when the current type aliases resolve to
   Postgres.
6. `lilo-im-store` remains publishable and cannot depend on `lilo-db`.
7. Test database provisioning lands in Phase 1.a, before any store gate requires
   Postgres tests.

## Public Surface

`internal/db/src/lib.rs` should export the target database primitives in Phase
1.a. The single Postgres backed `LiloDb` struct is the Phase 2 end state after
store callers stop using SQLite pool accessors.

```rust
pub type LiloPool = sqlx::PgPool;
pub type LiloConnection = sqlx::PgConnection;
pub type LiloTransaction<'a> = sqlx::Transaction<'a, sqlx::Postgres>;

pub struct DbConfig {
    pub database_url: String,
    pub max_connections: u32,
    pub connect_timeout: Duration,
}

impl DbConfig {
    pub fn from_env() -> Result<Self>;
    pub fn from_url(database_url: impl Into<String>) -> Self;
}

impl LiloDb {
    pub async fn open_postgres(config: DbConfig) -> Result<Self>;
    pub async fn open_postgres_from_env() -> Result<Self>;
    pub fn pool(&self) -> &LiloPool;
    pub async fn acquire(&self) -> Result<sqlx::pool::PoolConnection<sqlx::Postgres>>;
    pub async fn begin(&self, label: &str) -> Result<LiloTransaction<'_>>;
    pub async fn close(&self);
}
```

The exact names may change during implementation if the repo already has a
better local pattern. The shape should remain the same: one handle, one pool
accessor, one env based Postgres open path, one explicit config based Postgres
open path, and one transaction entry point. Phase 1.a must not reuse the current
`open(&LiloPaths)` name for a different signature because Rust cannot overload
inherent methods.

Phase 2 end state:

```rust
#[derive(Clone)]
pub struct LiloDb {
    pool: LiloPool,
}
```

## Transition Surface

Phase 1.a must not claim both of these at once:

- flip current `LiloDb` store callers from SQLite to `PgPool`;
- avoid store migration in Phase 1.a.

Those conflict because current stores are still `SqlitePool` and
`SqliteConnection` typed. The approved transition is:

1. Phase 1.a introduces and proves the Postgres target API, fixture, and service
   path.
2. `LiloDb` may retain an internal SQLite backing path alongside the Postgres
   target path while current stores still need SQLite pool accessors to compile.
   This can be an extra private field, an enum, or the existing `open_path`
   construction kept as scaffolding.
3. No new code may use the transition surface.
4. The Phase 1.a handoff must list every remaining transition symbol and its
   owning removal phase.
5. Phase 1.b removes cross component use of the transition surface while store
   APIs become backend neutral.
6. Phase 2 deletes the private SQLite implementation.

Allowed transition symbols are limited to the current compile blockers:

```rust
LiloDb::open_path(...)
LiloDb::open(&LiloPaths)
LiloDb::from_pool(SqlitePool)
LiloDb::identity_pool()
LiloDb::session_pool()
LiloDb::runtime_pool()
begin_immediate_tx(...)
finish_immediate_tx(...)
begin_immediate_pool_tx(...)
finish_immediate_pool_tx(...)
ImmediateTx
```

They should be annotated or isolated so readers cannot confuse them with the
target API. Do not add replacement SQLite aliases.

## Target Removed Surface

The target API removes these SQLite shaped database APIs:

```rust
LiloDb::open_path(...)
LiloDb::open(&LiloPaths)
LiloDb::from_pool(SqlitePool)
LiloDb::identity_pool()
LiloDb::session_pool()
LiloDb::runtime_pool()
begin_immediate_tx(...)
finish_immediate_tx(...)
begin_immediate_pool_tx(...)
finish_immediate_pool_tx(...)
ImmediateTx
```

Transaction helpers named after SQLite locking behavior should be removed in
the store migration phase, not Phase 1.a. Current store and daemon callers still
depend on the SQLite typed helpers while query migration is deferred. They may
remain only under the transition rules above.

## Environment Contract

Add `LILO_DATABASE_URL` to `lilo_paths::env`.

Rules:

- Empty values are treated as unset.
- `LiloDb::open_postgres_from_env()` fails with a clear operator error when the
  variable is absent.
- `LILO_HOME` no longer implies a database path for normal runtime setup.
- `LILO_DB_PATH` remains absent.
- `scripts/check-env.sh --check` must pass.

Suggested helper:

```rust
pub const LILO_DATABASE_URL: &str = "LILO_DATABASE_URL";

pub fn database_url() -> Option<String> {
    non_empty_env(LILO_DATABASE_URL).map(|value| value.to_string_lossy().into_owned())
}
```

The helper can be private or public based on current `lilo-paths` conventions.

## Connection And Migration Contract

`LiloDb::open_postgres(config)` owns:

1. Parsing the Postgres URL through sqlx.
2. Creating a `PgPool` with a bounded connection count.
3. Running Postgres migrations.
4. Returning a ready `LiloDb`.

Required behavior:

- Connection errors include enough context to identify the failed database URL
  host or database name without leaking passwords.
- Migration errors identify that Postgres migration failed.
- No caller outside `lilo-db` runs migrations directly.
- Pool access is shared through `LiloDb::pool()`.

Migration layout:

- `internal/db/migrations/` becomes the Postgres migration directory.
- The first migration keeps the unified schema intent.
- SQLite migration SQL is deleted, moved, or temporarily quarantined so workers
  cannot treat it as the final backend.

## Transaction Contract

SQLite immediate transaction helpers are replaced by neutral helpers.

Rules:

- Transaction names must not mention SQLite or immediate locking.
- Store code should use sqlx transaction semantics for Postgres.
- Rollback on dropped transactions should use sqlx behavior instead of manual
  `ROLLBACK` strings.
- Cross store operations should either receive a `&mut LiloTransaction<'_>` or
  use a narrow method on the owning store.

Phase 1.a only needs the shared transaction entry point. Later store phases can
decide which methods receive transactions.

## Test Fixture Contract

Postgres test isolation is part of Phase 1.a.

Add a test fixture module in `lilo-db`, behind `#[cfg(any(test, feature =
"test-support"))]` if cross crate tests need it:

```rust
pub struct TestDb {
    db: LiloDb,
    database_url: String,
    admin_url: String,
    database_name: String,
    cleaned: bool,
}

impl TestDb {
    pub async fn create() -> Result<Self>;
    pub fn db(&self) -> &LiloDb;
    pub fn database_url(&self) -> &str;
    pub async fn cleanup(self) -> Result<()>;
}
```

Required behavior:

- `TestDb::create()` connects to an admin database, creates a unique test
  database, runs migrations through the Postgres open path, and returns the
  fixture.
- `TestDb::cleanup(self).await` closes the pool and drops the test database.
- `Drop` must not perform async cleanup. It may mark or warn about leaked test
  databases so they are easy to clean manually.
- Test database names use a short stable prefix plus random or UUID entropy.
- Parallel tests must not collide.
- A leaked fixture should be easy to identify by database name.

Environment:

- The fixture reads an admin URL from a test only variable if needed.
- Candidate: `LILO_TEST_DATABASE_URL`.
- The normal application contract remains `LILO_DATABASE_URL`.

The final variable name must be added to the env registry before use.

## Local Service Contract

Add a repo local Postgres service path in Phase 1.a.

Preferred shape:

```yaml
services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_USER: lilo
      POSTGRES_PASSWORD: lilo
      POSTGRES_DB: lilo
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lilo -d lilo"]
      interval: 2s
      timeout: 2s
      retries: 30
```

The implementation can choose a non default host port if `5432` conflicts. The
documented URL must match the committed service.

Required local URL example:

```text
postgres://lilo:lilo@localhost:5432/lilo
```

## Workspace Dependency Changes

Required direction:

- Add sqlx `postgres` support.
- Remove sqlx `sqlite` support once SQLite code no longer compiles against it.
- Keep `chrono`, `migrate`, `runtime-tokio`, and `uuid`.
- Avoid adding a new database abstraction crate.

`lilo-db` remains unpublished internal infrastructure.

## Phase 1.a Work Items

1. Add `LILO_DATABASE_URL` and test database env names to the env registry.
2. Change workspace sqlx features to include Postgres.
3. Add the Postgres `LiloDb` target path backed by a `PgPool`.
4. Add config and env based open paths for Postgres.
5. Replace SQLite migrations with Postgres migrations.
6. Add the Postgres test fixture.
7. Add the local Postgres service path.
8. Update `lilo-db` unit tests from PRAGMA and `sqlite_master` checks to
   Postgres schema and connection checks.
9. Keep callers compiling through the explicit transition surface, without
   spreading store migration work into Phase 1.a.

## Phase 1.a Acceptance

Required checks:

```bash
fmm validate
scripts/check-env.sh --check
docker compose up -d --wait postgres
cargo test -p lilo-db
just check
```

Fixture acceptance:

- One test proves `TestDb::cleanup(self).await` drops the created database.
- One test proves multiple fixtures can run in parallel without database name
  collision.
- Test code must call explicit cleanup or use a helper that awaits cleanup.

Required searches:

```bash
rg "open_path|open\\([^)]*LiloPaths|identity_pool|session_pool|runtime_pool|from_pool|begin_immediate|finish_immediate|ImmediateTx" internal/db
rg "SqlitePool|SqliteConnection|sqlx::Sqlite|PoolConnection<Sqlite>" internal/db
rg "LILO_DATABASE_URL|LILO_TEST_DATABASE_URL" crates/lilo-paths/src/env.rs
```

Expected result:

- The transition symbol and SQLite searches return only approved transition
  scaffolding listed in the Phase 1.a handoff.
- The env names are registered exactly once.
- `cargo test -p lilo-db` proves migration and fixture behavior against
  Postgres.

## Handoff To Phase 1.b

Phase 1.b starts only after this contract is implemented or consciously revised.

The handoff artifact should state:

- The final exported `lilo-db` API.
- The Postgres URL used for local verification.
- The test fixture API.
- Any temporary SQLite transition scaffolding that still exists, with owner and
  removal phase.
- Whether SQLite transition constructors still share the same sqlx migration
  directory as the Postgres target path. If so, they are compile scaffolding
  once the directory flips to Postgres, and any store test still exercising them
  is expected red until the owning store migration removes that dependency.
- The exact command output for the Phase 1.a acceptance checks.
