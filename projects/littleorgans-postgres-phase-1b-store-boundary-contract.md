# littleorgans Postgres Phase 1.b Store Boundary Contract

Status: LOCKED 2026-06-06 — 4 MoE revalidation rounds (tx single-mechanism; im-store publishability model X; per-consumer sqlite feature routing; im-store test-gate feature)
Date: 2026-06-06
Parent plan: `/Users/alphab/.mdx/projects/littleorgans-postgres-persistence-plan.md`
Predecessor: `/Users/alphab/.mdx/projects/littleorgans-postgres-phase-1a-lilo-db-contract.md` (merged to `main` as #29, commit `d1e7754`)

## 1. Purpose And Inherited Locked Decisions

### Purpose

Phase 1.a made `lilo-db` the single internal database boundary and added the
Postgres target (`open_postgres`/`open_postgres_resolved`, `pool() -> &LiloPool`,
`DbConfig`, `TestDb`) alongside a quarantined SQLite transition surface
(`internal/db/src/transition.rs`). The not-yet-migrated stores still compile
against SQLite types through that surface.

Phase 1.b makes the **domain store crates depend on the database boundary, not on
SQLite types**. After 1.b, no store export, no cross-crate trait, and no
cross-component daemon or service signature names `SqlitePool`,
`SqliteConnection`, `sqlx::Sqlite`, or `PoolConnection<Sqlite>`. The published
`lilo-im-store` API stops exposing concrete SQLite types entirely.

This phase does **not** migrate any SQL body from the SQLite dialect to Postgres.
That is Phase 2. The private SQLite implementation inside each store stays as
transition scaffolding behind a neutral public surface.

### Inherited locked decisions (from plan Phase 0; binding on 1.b)

1. Postgres is the single target backend. SQLite may remain temporarily inside
   private modules but is not a supported final backend.
2. `lilo-im-store` is **published** and must not depend on the unpublished
   `lilo-db`. Confirmed: `lilo-im-store` is the only crate in this work set
   without `publish = false`; `lilo-session-store`, `lilo-runtime-store`,
   `lilo-identity-service`, and `lilo-db` are all `publish = false`.
3. `lilo-im-store` uses feature-gated backend support without depending on
   `lilo-db`. The target is a publishable neutral audit API, not a renamed
   `SqliteAuditSink::with_pool(SqlitePool)` with a concrete pool still in the
   published boundary (plan Phase 0 decision 8).
4. `LiloDb` may expose concrete sqlx types to internal crates during the
   Postgres-only migration; do not introduce a wider database abstraction until a
   second backend exists (plan Phase 0 decision 6).
5. The transition surface is removed in Phase 2. Every transition symbol that
   survives 1.b must be named in this contract with its Phase 2 removal owner.
6. Existing local SQLite data is disposable; no compatibility aliases for removed
   SQLite-specific names (plan Non Goals). No new test asserts a removed SQLite
   name stays removed (plan Non Goals; project feedback "no deletion-guard
   tests").

## 2. Scope Fence (state and obey)

In scope for 1.b:

- Rename and neutralize the **public, exported, and cross-component** store and
  audit surfaces so they carry no SQLite type.
- Fix `lilo-im-store` publishability: neutral default API, feature-gated SQLite
  backend, no `lilo-db` dependency.
- Route cross-component transaction work through a single neutral `lilo-db`
  transition handle so no daemon, store, or service signature names a SQLite type.
- Construct every store from `&LiloDb` rather than from a raw `SqlitePool`.

Out of scope for 1.b (defer to Phase 2 or later):

- Replacing SQLite SQL with Postgres SQL in any store body. Placeholders,
  PRAGMAs, `BEGIN IMMEDIATE`, `sqlite_master`, `rowid`, and dialect-specific
  encoding stay until Phase 2.
- Removing the `lilo-db` transition surface (`transition.rs`). It is deleted in
  Phase 2 when the last private store impl leaves SQLite.
- *Semantic* migration of CLI/doctor/admin/driver callers and integration
  fixtures (`crates/lilo`, `tests/integration`, admin protocol) — moving them to
  the Postgres path, changing SQL dialect, or changing behavior. Those are Phase
  3 and Phase 5; they are outside the 1.b acceptance `rg` scope
  (`internal/session internal/runtime internal/identity crates/lilo-im-store`).
  CAVEAT (reconciliation): because 1.b renames exported types with **no
  compatibility aliases** (`SqliteStore`->`SessionStore`,
  `*::open`->`from_db`, connection-scoped->pool-scoped tx helpers) and the
  acceptance demands the **full workspace compiles 0-failed**, these callers and
  their test files (`internal/session/driver/tests/*`, `tests/integration/**`)
  MUST be updated to follow the renames/signatures. Such mechanical
  rename/signature follows are in scope and required; only the *semantic* Phase
  3/5 migration above is deferred. A pure rename-follow in an out-of-`rg`-scope
  file is not a scope violation.
- Schema column-type changes (`uuid`, `timestamptz`, `bytea`, `owner` seam,
  JSONB). Phase 2.

The litmus test for 1.b: a SQLite type may survive **only** inside a private
`sqlite` module/file of a store crate, inside `lilo-db`'s `transition.rs`, or
inside test code. It may not appear in any export, any cross-crate trait, any
published signature, or any function that threads a value between two crates.

## 3. Target Exported Surface Per Store Crate

### `lilo-session-store` (`internal/session/store`, `publish = false`)

- Rename public store type `SqliteStore` -> `SessionStore`. Re-export
  `SessionStore` from `src/lib.rs` (replacing `SqliteStore`).
- Constructor becomes backend-neutral: `SessionStore::from_db(db: &LiloDb)`
  (today's `SqliteStore::open(&LiloDb)` already takes `&LiloDb`; rename it and
  drop any `SqlitePool`-typed constructor). No public constructor takes a
  `SqlitePool`.
- Remove `pub fn pool(&self) -> &SqlitePool` from the public surface. If the
  crate's own tests and private impl still need pool access, demote it to
  `pub(crate)` (still SQLite-typed, but private to the crate and inside the
  `sqlite` module, so not a cross-component leak).
- The cross-crate transaction methods (`insert_pending_spawn_intent_in`,
  `insert_session_in`, `resolve_spawn_intent_in`, `abort_spawn_intent_in`) stay
  `pub` (the daemon calls them) but change their connection parameter from
  `&mut SqliteConnection` to `&mut lilo_db::ImmediateTx` (section 4). Demotion is
  not an option for these; they are genuinely called from the session daemon.
- Domain types stay (`SessionDraft`, `SessionSpawnIntent`, `PendingSpawnIntent`,
  `SpawnIntentStatus`, `SpawnIntentError`, `MailWriteOutcome`) — already neutral.
- Backend impl stays in the `sqlite` module (`src/sqlite.rs` + `src/sqlite/*.rs`).
  Consider demoting `pub mod sqlite` to `mod sqlite` so the only public reach into
  it is through re-exported neutral items; the SQLite-bounded `*_with` executor
  generics and bare-`Sqlite` helpers then stop being crate-public surface.

### `lilo-runtime-store` (`internal/runtime/store`, `publish = false`)

- Keep public type name `LifecycleStore` (already neutral).
- Remove the SQLite-typed surface on it:
  - `pub fn pool(&self) -> &SqlitePool` -> removed from public API (demote to
    `pub(crate)` if internal tests need it).
  - `pub fn from_pool(pool: SqlitePool) -> Self` -> replaced by
    `LifecycleStore::from_db(db: &LiloDb)`. No public constructor takes a
    `SqlitePool`.
  - Cross-crate transaction methods (`insert_forking_in`, `update_lifecycle_in`,
    `delete_in`) stay `pub` but change their connection parameter
    `&mut SqliteConnection` -> `&mut lilo_db::ImmediateTx` (section 4).
- `StoreConfig` stays (already neutral).
- Backend impl stays in the `src/sqlite/lifecycle.rs` module; same `pub mod` ->
  `mod` consideration as the session store.

### `lilo-im-store` (`crates/lilo-im-store`, **published**)

- Public default surface carries **no** sqlx type. The neutral audit contract
  (`AuditSink`, `AuditRow`, `AuditError`) already lives in the sqlx-free
  published `lilo-im-core`; lean on it.
- The default published surface (empty features) is exactly the sqlx-free
  contract re-exported from `lilo-im-core`: `AuditSink`, `AuditRow`, `AuditError`.
  No concrete store type, no sqlx type, and no constructor at default.
- `SqliteAuditSink` -> renamed `AuditStore`: the neutral *name* for the concrete
  SQLite-backed sink. It compiles ONLY under `#[cfg(feature = "sqlite")]`,
  `impl AuditSink`, and is NOT part of the default surface. Its constructors
  (`with_pool`, ...) are `sqlite`-gated.
- `query_audit(pool: &SqlitePool, filters)` free function -> removed. It becomes a
  `sqlite`-gated method on `AuditStore` (`AuditStore::query_audit(&self, filters)`),
  so the pool is never a public parameter and the method is absent at default.
- There is no neutral default constructor. The default consumer reaches audit
  storage through the `AuditSink` trait; internal crates enable `sqlite` to obtain
  the concrete `AuditStore` (see section 5).
- `record_audit_in_tx(conn: &mut SqliteConnection, ...)` -> feature-gated
  (`sqlite`) and reached only by internal callers (identity service) that enable
  the feature. Not part of the default published surface.
- Update `Cargo.toml` `description` and `README.md` to drop `SqliteAuditSink`
  wording (both currently name it).

## 4. Cross-Component Transaction Routing

### What exists today (the atomic seam to preserve)

Both spawn paths thread **one** SQLite connection holding an open
`BEGIN IMMEDIATE` across crate boundaries so the spawn-intent insert and the
identity audit row commit atomically:

```
session daemon spawn.rs::begin_spawn_tx
  -> self.store.pool().acquire()            // PoolConnection<Sqlite>
  -> begin_immediate_tx(&mut conn, label)   // lilo-db transition (SQLite)
  -> session store insert methods (&mut conn)
  -> IdentityPort::authorize_in_tx(&mut conn, ...)   // session daemon trait
       -> IdentityClient::authorize_in_tx(&mut conn) // identity service
            -> record_audit_in_tx(&mut conn, &row)   // im-store
  -> finish_immediate_tx(&mut conn, result, label)
```

The runtime daemon (`internal/runtime/daemon/src/identity.rs::authorize_runtime_spawn`)
mirrors this exactly, acquiring from `state.store().pool()` (the `LifecycleStore`
SQLite pool) and threading `&mut conn` through the same `authorize_in_tx` chain.

This atomicity must be preserved. The connection must remain shared, because
session+identity+runtime are one physical database today.

### Target routing for 1.b

Route the shared connection through a single **neutrally named** `lilo-db`
transition handle so no crate names a `sqlx::Sqlite*` type in a cross-component
position. `lilo-db` already exports `ImmediateTx`, a neutrally named handle that
owns a `PoolConnection<Sqlite>` and `Deref`s to `SqliteConnection`. Reuse it as
the threaded handle:

1. `lilo-db` adds a transition begin helper that returns the neutral handle from
   a `LiloDb` (transition, SQLite-backed today), e.g.
   `LiloDb::begin_spawn_tx(&self, label) -> Result<ImmediateTx>` — or expose the
   equivalent on the store so the daemon, which already holds the store, does not
   reach a raw pool. The helper internally does
   `begin_immediate_pool_tx(self.sqlite_pool())`.
2. The session daemon's `begin_spawn_tx` returns `lilo_db::ImmediateTx` instead
   of `PoolConnection<Sqlite>`. It threads `&mut tx` to store methods and to
   `authorize_in_tx`. It commits with `finish_immediate_pool_tx(tx, result)`.
3. **Every store method that joins the shared transaction** changes its
   connection parameter from `&mut SqliteConnection` to `&mut lilo_db::ImmediateTx`.
   These are `pub` methods on re-exported store types, called cross-crate by the
   daemon with the shared connection (verified call sites in `spawn.rs`):

   | Store | Method | Today | 1.b |
   |---|---|---|---|
   | session | `insert_pending_spawn_intent_in` | `&mut SqliteConnection` | `&mut ImmediateTx` |
   | session | `insert_session_in` | `&mut SqliteConnection` | `&mut ImmediateTx` |
   | session | `resolve_spawn_intent_in` | `&mut SqliteConnection` | `&mut ImmediateTx` |
   | session | `abort_spawn_intent_in` | `&mut SqliteConnection` | `&mut ImmediateTx` |
   | runtime | `insert_forking_in` | `&mut SqliteConnection` | `&mut ImmediateTx` |
   | runtime | `update_lifecycle_in` | `&mut SqliteConnection` | `&mut ImmediateTx` |
   | runtime | `delete_in` | `&mut SqliteConnection` | `&mut ImmediateTx` |

   Bodies stay SQLite (Phase 2 migrates them): they execute against
   `&mut **tx`, since `ImmediateTx: DerefMut<Target = SqliteConnection>`. The
   intra-crate `*_with` executor-generic helpers (`E: Executor<Database = Sqlite>`)
   are **not** called cross-crate (verified) and stay private/transitional.

4. `IdentityPort::authorize_in_tx` (session daemon trait) and
   `IdentityClient::authorize_in_tx` (identity service) take
   `tx: &mut lilo_db::ImmediateTx` instead of `&mut SqliteConnection`. Session
   daemon and identity service both depend on `lilo-db`, so the neutral name is
   available.
5. The identity service passes `&mut **tx` (auto-derefs `ImmediateTx` ->
   `SqliteConnection`) into im-store's feature-gated `record_audit_in_tx`. The
   identity service source names no SQLite type; the only `SqliteConnection`
   token left is inside im-store's private, feature-gated `sqlite/audit.rs`.
6. The runtime daemon `authorize_runtime_spawn` performs the same swap: obtain a
   `lilo_db::ImmediateTx` from the runtime store / `LiloDb`, thread `&mut tx` to
   `authorize_in_tx`.

**Single tx mechanism (correctness, per revalidation finding).** The spawn paths
use exactly one mechanism: the pool-scoped `ImmediateTx` begun by
`begin_immediate_pool_tx` and committed by `finish_immediate_pool_tx`. Store
methods and `authorize_in_tx` only *execute* statements against `&mut **tx`; they
must never call the connection-scoped `begin_immediate_tx`/`finish_immediate_tx`
on that same handle, which (`transition.rs:176-201`) would issue a second `BEGIN`
on an already-open connection or leave `open=true` so `Drop` rolls back an
already-committed result. One begin, one finish, both pool-scoped.

This is the plan's "shared `lilo-db` transaction" option. Narrow per-store
methods are **not** sufficient here because the atomic boundary spans two bounded
contexts (session spawn-intent + identity audit); only a shared transaction
preserves it without coupling the session store to the audit sink.

Design note for revalidation: reusing the existing `ImmediateTx` avoids adding a
new alias and respects the Phase 1.a `transition.rs` rule "no replacement SQLite
aliases may be added." If revalidation prefers a bare-connection signature over
threading `ImmediateTx`, the alternative is one neutral transition alias
`pub type TxConnection = sqlx::SqliteConnection;` in `transition.rs`, used at the
same cross-component signatures. That technically adds a transition alias; its
purpose is to *erase* SQLite names from cross-component code, the opposite of the
proliferation the original rule guarded against. Recommendation: thread
`ImmediateTx`; do not add `TxConnection`.

### `begin_immediate_*` disposition (stay vs go in 1.b)

| Symbol (lilo-db `transition.rs`) | 1.b | Rationale | Removed |
|---|---|---|---|
| `ImmediateTx` | **stay** | Neutral cross-component tx handle threaded by daemons | Phase 2 |
| `begin_immediate_pool_tx` / `finish_immediate_pool_tx` | **stay** | Pool-scoped tx used by session store `mail.rs` / `spawn_intents.rs` (private impl) and by the daemon begin helper | Phase 2 |
| `begin_immediate_tx` / `finish_immediate_tx` | **stay (daemon stops calling)** | Connection-scoped; the migrated spawn paths use the pool-scoped `ImmediateTx` (`begin_immediate_pool_tx`/`finish_immediate_pool_tx`) and must NOT also call these on that handle — `transition.rs:176-201` would double-`BEGIN` or leave `open=true` so `Drop` rolls back a committed result. They remain only for any non-spawn callers; if none remain, they are unused transition code | Phase 2 |
| `open` / `open_path` | **stay** | Transition SQLite constructors still used by daemon/store setup; caller migration is Phase 3 | Phase 2/3 |
| `identity_pool` / `session_pool` / `runtime_pool` | **stay, callers reduced** | Keep as transition accessors but reduce production callers to store/sink constructors built via `from_db`; remaining callers (`crates/lilo` doctor, integration tests) are out of 1.b scope | Phase 2/3 |
| `sqlite_migrator` / `Target` / `Backing::Sqlite` | **stay (private)** | Internal transition plumbing | Phase 2 |

No transition symbol is removed in 1.b. 1.b changes who names them and how they
are typed at the boundary, not their existence.

## 5. `lilo-im-store` Publishability Strategy

Hard constraints: `lilo-im-store` is published; it must not depend on `lilo-db`;
its default published API must carry no concrete sqlx type.

Strategy:

1. **Lean on the existing neutral contract.** `lilo-im-core` (published, no sqlx)
   already defines `AuditSink`, `AuditRow`, `AuditError`. The published audit
   contract is the `AuditSink` trait; concrete backends implement it.
2. **Feature-gate backends.** Add Cargo features to `lilo-im-store`:
   - `sqlite` (transition; default for internal consumers during migration):
     compiles the current `sqlite/audit.rs` impl, `AuditStore::with_pool(SqlitePool)`,
     and the gated `record_audit_in_tx`.
   - `postgres`: NOT added in 1.b. Declared in Phase 2 when its audit SQL body
     lands; declaring an empty no-op feature now is speculative (project ethos:
     no speculative surface until a real field/impl needs it). 1.b adds only
     `sqlite`.
   - Default features: empty (no backend). A crates.io consumer building with
     defaults sees only the sqlx-free published contract — `AuditSink`,
     `AuditRow`, `AuditError` re-exported from `lilo-im-core` — and no concrete
     sqlx type. The neutral-named concrete sink `AuditStore` and its
     pool/connection constructors compile only when the `sqlite` feature is
     explicitly enabled (which internal crates do during the transition). So
     `AuditStore` is the neutral *name*, but it is `sqlite`-gated, not part of
     the default published surface.
3. **No `lilo-db` dependency.** im-store never imports `lilo-db`. The threaded
   transaction connection arrives as a sqlx type the identity service already
   holds (via `ImmediateTx` deref). im-store's gated `record_audit_in_tx` accepts
   a sqlx `SqliteConnection`/`Executor` under `#[cfg(feature = "sqlite")]`. Because
   `lilo_db::ImmediateTx: Deref<Target = SqliteConnection>`, the identity service
   passes `&mut **tx` without im-store ever seeing `lilo-db`.
4. **Identity service wiring.** `internal/identity/service` (`publish = false`)
   enables `lilo-im-store`'s `sqlite` feature for the transition. It constructs
   the audit store from `&LiloDb` internally
   (`IdentityClient::from_db(db: &LiloDb)` already exists; keep it, but build the
   sink without naming `SqlitePool` in the public method — the `db.identity_pool()`
   call stays inside the service, returning a transition `&SqlitePool` that the
   gated `AuditStore::with_pool` consumes). The published `lilo-im-store` API is
   never the thing the service's public signature exposes.

Net: a crates.io consumer depends on `lilo-im-store` (+ `lilo-im-core`) and, with
default (empty) features, uses the `AuditSink` trait (plus `AuditRow` /
`AuditError`) only — it never sees `AuditStore`, `lilo-db`, or a sqlx SQLite type.
Enabling the `sqlite` feature is what exposes the concrete `AuditStore`; internal
littleorgans crates do this during the transition. A `postgres` backend feature is
Phase 2, not declared in 1.b.

## 6. Transitional (private SQLite OK) vs Removed Now

Removed / neutralized in 1.b (cross-component, public, or published):

- `SqliteStore` public name -> `SessionStore`.
- `SqliteAuditSink` public name -> `AuditStore`.
- `SqliteStore::pool() -> &SqlitePool`, `LifecycleStore::pool() -> &SqlitePool`
  removed from public API.
- `LifecycleStore::from_pool(SqlitePool)` -> `from_db(&LiloDb)`.
- `query_audit(pool: &SqlitePool, ...)` free fn -> neutral method.
- `with_pool(SqlitePool)` / `record_audit_in_tx(&mut SqliteConnection)` ->
  feature-gated (`sqlite`), off the default published surface.
- `IdentityPort::authorize_in_tx(&mut SqliteConnection)` and
  `IdentityClient::authorize_in_tx(&mut SqliteConnection)` -> `&mut ImmediateTx`.
- `begin_spawn_tx() -> PoolConnection<Sqlite>` -> returns `ImmediateTx`.

Stays transitional in 1.b (private SQLite impl, removed in Phase 2):

- Every `internal/session/store/src/sqlite.rs` and `src/sqlite/*.rs` body
  (SQLite SQL, `&mut SqliteConnection` private helpers, `pool: SqlitePool` field,
  `sqlx::Transaction<'_, Sqlite>` private helpers in `namespaces.rs`).
- `internal/runtime/store/src/sqlite/lifecycle.rs` private body and helpers.
- `crates/lilo-im-store/src/sqlite/audit.rs` under `#[cfg(feature = "sqlite")]`.
- All of `lilo-db` `transition.rs`.
- All SQLite usage in test code (see section 7 acceptance).

## 7. Acceptance

### Gate 1: call-site + published-surface neutrality (must be zero)

Run the plan's leak check, excluding private `sqlite` impl modules/files and all
test files, over the four trees. Note `tests.rs` (inline `mod tests` files under
`src/`) must be excluded explicitly — `-g '!**/tests/**'` only excludes the
`tests/` directory and `-g '!**/*_tests.rs'` does not match `tests.rs`. This must
return **zero**:

```bash
rg "SqlitePool|SqliteConnection|sqlx::Sqlite|PoolConnection<Sqlite>" \
  internal/session internal/runtime internal/identity crates/lilo-im-store \
  -g '!**/sqlite.rs' -g '!**/sqlite/**' \
  -g '!**/tests/**' -g '!**/*_tests.rs' -g '!**/tests.rs' -g '!**/test_support.rs'
```

Zero here proves no leak survives in any cross-crate call site, daemon handler,
identity service signature, cross-crate trait file, or the published top-level
`lib.rs`. On `main` today this returns the 8 hits Gate 1 is designed to drive to
zero (`client.rs:9,65`; `im-store lib.rs:10,15`; `identity_client.rs:10,24,55`;
`spawn.rs:343`).

### Gate 2: public-item neutrality inside impl modules (must be zero)

Gate 1 excludes `**/sqlite/**`, so a re-exported `pub` item that physically lives
inside an impl module is invisible to it. This is where the largest part of the
leak lives: the seven cross-crate `*_in` transaction methods plus the
pool accessors and the published im-store fns. Gate 2 closes the hole: **no fully
`pub` item (not `pub(crate)`, not `#[cfg(feature = "sqlite")]`-gated) inside any
`sqlite` impl module may name a SQLite type**.

Single-line signatures and wrapped (multi-line) signatures both matter, so run
both finders and union the results (the single-line form catches return-type
accessors like `pool() -> &SqlitePool`; the multi-line form catches wrapped param
lists like `record_audit_in_tx(\n  conn: &mut SqliteConnection)`):

```bash
# return-type and single-line signatures
rg -n "^\s*pub (async )?(fn|struct|type|const) .*(SqlitePool|SqliteConnection|sqlx::Sqlite|PoolConnection<Sqlite>)" \
  internal/session/store/src internal/runtime/store/src crates/lilo-im-store/src
# wrapped param lists
rg -U -n --multiline-dotall \
  "pub (async )?fn [a-z_]+\s*(<[^>]*>)?\s*\([^)]*?(SqlitePool|SqliteConnection|sqlx::Sqlite|PoolConnection<Sqlite>)" \
  internal/session/store/src internal/runtime/store/src crates/lilo-im-store/src
```

Disposition for every line returned:

- `pool()` accessors -> demote to `pub(crate)` (passes Gate 2).
- `from_pool(SqlitePool)` -> replace with `from_db(&LiloDb)` (gone).
- `*_in(&mut SqliteConnection)` cross-crate tx methods -> change param to
  `&mut lilo_db::ImmediateTx` (stays `pub`, no SQLite token).
- im-store `with_pool` / `record_audit_in_tx` -> `#[cfg(feature = "sqlite")]`.

A bare `pub fn ... &SqlitePool` / `pub async fn ...(&mut SqliteConnection)` on a
re-exported store/sink type, not `pub(crate)` and not feature-gated, fails Gate 2.

### Acceptance pattern blind spot (extend the residue audit)

The plan's literal pattern `SqlitePool|SqliteConnection|sqlx::Sqlite|PoolConnection<Sqlite>`
misses **bare `Sqlite`**: `Database = Sqlite` executor bounds,
`Transaction<'_, Sqlite>` with an unqualified `Sqlite`, and `QueryBuilder::<Sqlite>`.
On `main` these appear in `events.rs:38,102,123`, every `*_with` generic bound,
and the query builders — none are in the 52 the literal pattern reports. They are
all private impl (role iii) today, but the residue audit must be honest, so run
it with the extended pattern and confirm every extra hit is private/transitional:

```bash
rg -n "SqlitePool|SqliteConnection|PoolConnection<Sqlite>|\bSqlite\b" \
  internal/session internal/runtime internal/identity crates/lilo-im-store
```

`\bSqlite\b` subsumes `sqlx::Sqlite` and catches the bare forms while not matching
inside `SqlitePool`/`SqliteConnection` (no word boundary mid-token).

### Residue audit (must be classifiable)

Run the plan's unfiltered leak check and confirm **every** remaining hit is one
of: (a) a private `sqlite` module/file of a store crate, (b) test code, or
(c) (only ever appears outside the four trees) `lilo-db` `transition.rs`. No hit
may be a cross-component production signature:

```bash
rg "SqlitePool|SqliteConnection|sqlx::Sqlite|PoolConnection<Sqlite>" \
  internal/session internal/runtime internal/identity crates/lilo-im-store
```

### Surface and publishability

- Store names exposed to callers are backend-neutral (`SessionStore`,
  `LifecycleStore`; `AuditStore` only when the `sqlite` feature is enabled).
- `lilo-im-store` default-feature (empty) build exposes the sqlx-free contract and
  no concrete sqlx type: a manual check (or `cargo public-api`) that the default
  public surface re-exports `AuditSink`, `AuditRow`, `AuditError`, names no sqlx
  type, and does not expose `AuditStore`.
- `AuditStore` is present only under `--features sqlite` and `impl AuditSink`
  there; confirm it is absent at default
  (`cargo build -p lilo-im-store` vs `cargo build -p lilo-im-store --features sqlite`).
- `lilo-im-store` does not depend on `lilo-db`:
  `! grep -q 'lilo-db' crates/lilo-im-store/Cargo.toml`.
- `cargo package --no-verify -p lilo-im-store` builds the published tarball.
  (Use `--no-verify`; a full verify-build resolves sibling `version = "0.8.0"`
  deps from crates.io, which are unpublished mid-migration — see the cm lesson on
  `cargo publish --dry-run` verify-build.)

### Tests

- Focused store tests pass. `lilo-im-store` tests import the `sqlite`-gated audit
  API, so in isolation they need the feature; the default-feature sqlx-free check
  above stays a SEPARATE step (do not merge — merging either hides `AuditStore`
  or fails to prove the sqlx-free default):
  `cargo nextest run -p lilo-session-store -p lilo-runtime-store` and
  `cargo nextest run -p lilo-im-store --features sqlite`.
  (The full `--workspace` run below compiles im-store with `sqlite` via feature
  unification, so it already covers them; this focused line is for isolated runs.)
- **Full workspace suite is 0-failed** (do not trust scoped runs or `just check`
  alone; `just check` runs no tests):

```bash
cargo nextest run --workspace --no-fail-fast
```

  This gate is mandatory and load-bearing: the Phase 1.a branch sat on 275/719
  red while scoped runs and `just check` were green (cm lesson
  `019e9c20-fef7-78e3-8f6b-883fa56d772c`). A rename of `SqliteStore` /
  `SqliteAuditSink` touches ~30 daemon and test call sites; workspace-wide blast
  radius is the norm for this change, not the exception.

- `just check && just build && just test` clean.
- If files or symbols moved: `fmm generate && fmm validate` green.

## 8. File-By-File Work Plan With Blast Radius

Ordering: neutralize producers first (stores, im-store, identity service), then
the daemon call sites that thread the connection, then sweep tests. Group by
natural coupling (project feedback: fewer broad workers, group by coupling).

### Cargo feature routing (land with Group A — required or the workspace compiles red)

Default `lilo-im-store` features are now empty (model X), so every internal
consumer that names `AuditStore`/`query_audit` must enable the `sqlite` feature
on its dependency, or the type disappears and the build goes red:

| Cargo.toml | Change |
|---|---|
| `internal/identity/service/Cargo.toml` (~line 21) | `lilo-im-store = { ..., features = ["sqlite"] }` |
| `internal/session/daemon/Cargo.toml` (~line 26) | add `features = ["sqlite"]` |
| `internal/session/app/Cargo.toml` (~line 55) | add `features = ["sqlite"]` |
| `internal/runtime/daemon/Cargo.toml` (~line 41) | add `features = ["sqlite"]` |

If `lilo-im-store` is declared in the root `[workspace.dependencies]`, set the
feature once there and let members inherit rather than repeating it. After the
edits, `cargo tree -e features -i lilo-im-store` must show every consumer
resolving the `sqlite` feature, and a default-feature `cargo build -p
lilo-im-store` must still be sqlx-free (the §7 publishability gate).

### Group A — `lilo-im-store` publishable boundary (do first; unblocks identity)

| File | Change |
|---|---|
| `crates/lilo-im-store/Cargo.toml` | Add `[features]` with `sqlite` only (no `postgres` in 1.b); default features empty (sqlx-free surface); update `description` (drop `SqliteAuditSink`). |
| `crates/lilo-im-store/src/lib.rs` | Remove `query_audit(pool: &SqlitePool)` free fn and the `use sqlx::SqlitePool`. Default re-export = `AuditSink`/`AuditRow`/`AuditError` from `lilo-im-core` (sqlx-free). Re-export `AuditStore` + `AuditFilters`/`AuditTableColumn`/`StoreError` only under `#[cfg(feature = "sqlite")]`. |
| `crates/lilo-im-store/src/sqlite.rs` | Rename re-exports; keep `sqlite` module private/feature-gated. |
| `crates/lilo-im-store/src/sqlite/audit.rs` | Rename `SqliteAuditSink` -> `AuditStore`; gate behind `#[cfg(feature = "sqlite")]`; move `query_audit` onto the sink; keep SQLite SQL body (transition). |
| `crates/lilo-im-store/README.md` | Replace `SqliteAuditSink` wording with the neutral name. |
| `crates/lilo-im-store/tests/audit.rs` | Update to neutral name; allowed to keep `SqlitePool` (test, excluded by acceptance). |

### Group B — identity service + cross-crate identity port

| File | Change | Blast radius |
|---|---|---|
| `internal/identity/service/src/client.rs` | `use lilo_im_store::SqliteAuditSink` -> `AuditStore`; `authorize_in_tx(conn: &mut SqliteConnection)` -> `(tx: &mut lilo_db::ImmediateTx)`; pass `&mut **tx` to gated `record_audit_in_tx`; drop `use sqlx::SqliteConnection`. | `IdentityClient::{new,from_db,audit_sink,authorizer}` callers (see below). |
| `internal/session/daemon/src/identity_client.rs` | `IdentityPort::authorize_in_tx(&mut SqliteConnection)` -> `(&mut lilo_db::ImmediateTx)`; impl forwards; drop `use sqlx::SqliteConnection`. | All `IdentityPort` impls incl. the test double in `tests/common/mod.rs:397`. |

### Group C — session store + session daemon spawn path

| File | Change | Blast radius |
|---|---|---|
| `internal/session/store/src/lib.rs` | Re-export `SessionStore` (was `SqliteStore`). | All `SqliteStore` importers below. |
| `internal/session/store/src/sqlite.rs` | Rename `SqliteStore` -> `SessionStore`; demote `pool()` to `pub(crate)`; keep `pool: SqlitePool` field private (transition). | — |
| `internal/session/store/src/sqlite/{spawn_intents,sessions}.rs` | `impl SqliteStore` -> `impl SessionStore`; cross-crate `*_in` methods (`insert_pending_spawn_intent_in`, `resolve_spawn_intent_in`, `abort_spawn_intent_in`, `insert_session_in`) change `conn` param to `&mut lilo_db::ImmediateTx`, bodies use `&mut **tx`. | daemon `spawn.rs` call sites. |
| `internal/session/store/src/sqlite/{mail,labels,namespaces,events,*_tests}.rs` | `impl SqliteStore` -> `impl SessionStore`; intra-crate `*_with` / bare-`Sqlite` helpers stay private (transition). | intra-crate only. |
| `internal/session/daemon/src/handler/spawn.rs` | `begin_spawn_tx() -> PoolConnection<Sqlite>` returns `ImmediateTx`; thread `&mut tx`; `LifecycleStore::from_pool(self.store.pool().clone())` -> `from_db(&self.db)`. | `complete_spawn_intent` and `authorize_in_tx` call site (line 112). |
| `internal/session/daemon/src/{store_lock,events,service,server,spawn_request}.rs`, `src/handler/state.rs`, `src/handler/spawn/tests.rs` | `SqliteStore` -> `SessionStore`; `SqliteStore::open(&db)` -> `SessionStore::from_db(&db)`; `SqliteAuditSink::with_pool(db.identity_pool())` -> neutral `AuditStore` construction via identity wiring. | 10 production + test call sites (see survey appendix). |

### Group D — runtime store + runtime daemon

| File | Change | Blast radius |
|---|---|---|
| `internal/runtime/store/src/lib.rs` | Keep `LifecycleStore` export; doc tweak. | — |
| `internal/runtime/store/src/sqlite/lifecycle.rs` | Demote `pool()` to `pub(crate)`; `from_pool(SqlitePool)` -> `from_db(&LiloDb)`; cross-crate `*_in` methods (`insert_forking_in`, `update_lifecycle_in`, `delete_in`) change `conn` param to `&mut lilo_db::ImmediateTx`, bodies use `&mut **tx`; `*_with` / query-builder helpers stay private. | `from_pool` callers: `spawn.rs:336`, `spawn_recovery.rs:342` (test); `*_in` callers in `spawn.rs`. |
| `internal/runtime/daemon/src/identity.rs` | `authorize_runtime_spawn`: obtain `ImmediateTx` from store/`LiloDb`; thread `&mut tx` to `authorize_in_tx`. No SQLite type named. | — |
| `internal/runtime/daemon/src/server/state.rs` | `#[cfg(test)]` ctor `SqliteAuditSink::with_pool(store.pool())` -> neutral; test-only. | — |

### Group E — test sweep (after producers compile)

Test files keep SQLite types (excluded by acceptance) but must follow renames
(`SqliteStore` -> `SessionStore`, `SqliteAuditSink` -> `AuditStore`) and the
`authorize_in_tx` signature change:

- `internal/session/daemon/tests/common/mod.rs` (test double `authorize_in_tx`, `SqliteStore`, `query_audit`)
- `internal/session/daemon/tests/{server_concurrency,handler/spawn_recovery}.rs`
- `internal/runtime/daemon/src/handler/tests.rs`
- `internal/identity/service/tests/factory.rs` (`authorize_in_tx`, `query_audit`)
- `internal/runtime/app/tests/integration_pass7.rs`, `internal/session/app/tests/{common/mod.rs,cli_get_test/run_resolution.rs}` (`query_audit`, `session_pool` — neutral query method or keep gated test path)

Out of 1.b scope (Phase 3/5, outside acceptance `rg`): `crates/lilo/src/cli/doctor.rs` (`session_pool`/`identity_pool`/`runtime_pool`), `crates/lilo-rm-core/src/admin.rs`, `internal/session/driver/src/conv.rs`, `tests/integration/**`.

## Appendix: Survey Evidence (leak classification)

Acceptance `rg` over `internal/session internal/runtime internal/identity
crates/lilo-im-store` on `main` @ `d1e7754`. **52 hits**, classified into four
roles (8 + 12 + 24 + 8 = 52). (The literal pattern undercounts; see the blind-spot
note in section 7 — the extended `\bSqlite\b` audit surfaces more private-impl
hits, all role iii.):

Role (i) — cross-component call sites / cross-crate traits / published `lib.rs`
(Gate 1; must reach zero) — **8 hits**:

- `crates/lilo-im-store/src/lib.rs:10,15` — `query_audit(pool: &SqlitePool)` (published free fn)
- `internal/identity/service/src/client.rs:9,65` — `IdentityClient::authorize_in_tx(&mut SqliteConnection)`
- `internal/session/daemon/src/identity_client.rs:10,24,55` — `IdentityPort::authorize_in_tx(&mut SqliteConnection)` (cross-crate trait)
- `internal/session/daemon/src/handler/spawn.rs:343` — `begin_spawn_tx() -> PoolConnection<Sqlite>`

Role (ii) — `pub`, re-exported items physically inside `sqlite` impl modules,
called cross-crate or published (Gate 2; must be neutralized, demoted to
`pub(crate)`, or feature-gated) — **12 hits**:

- `internal/runtime/store/src/sqlite/lifecycle.rs:62` — `pub fn pool(&self) -> &SqlitePool` (-> `pub(crate)`)
- `internal/runtime/store/src/sqlite/lifecycle.rs:314` — `pub fn from_pool(pool: SqlitePool)` (-> `from_db`)
- `internal/runtime/store/src/sqlite/lifecycle.rs:75,90,107` — `insert_forking_in` / `update_lifecycle_in` / `delete_in` `conn: &mut SqliteConnection` (cross-crate; -> `&mut ImmediateTx`)
- `internal/session/store/src/sqlite.rs:37` — `pub fn pool(&self) -> &SqlitePool` (-> `pub(crate)`)
- `internal/session/store/src/sqlite/sessions.rs:53` — `insert_session_in` `conn: &mut SqliteConnection` (cross-crate; -> `&mut ImmediateTx`)
- `internal/session/store/src/sqlite/spawn_intents.rs:210,229,253` — `insert_pending_spawn_intent_in` / `resolve_spawn_intent_in` / `abort_spawn_intent_in` `conn` (cross-crate; -> `&mut ImmediateTx`)
- `crates/lilo-im-store/src/sqlite/audit.rs:56` — `pub fn with_pool(pool: SqlitePool)` (published; gate under `sqlite`)
- `crates/lilo-im-store/src/sqlite/audit.rs:93` — `pub async fn record_audit_in_tx(&mut SqliteConnection)` (published; gate under `sqlite`)

Role (iii) — genuinely private impl bodies, fields, helpers, and imports inside
`sqlite` modules/files (stay transitional through Phase 2; not a leak) — **24 hits**:

- `internal/session/store/src/sqlite.rs:14,25` — `use sqlx::SqlitePool`, private `pool: SqlitePool` field
- `internal/session/store/src/sqlite/namespaces.rs:156,167` — private `sqlx::Transaction<'_, Sqlite>` helpers
- `internal/session/store/src/sqlite/labels.rs:3,33,81` — import + private `&mut SqliteConnection` helpers
- `internal/session/store/src/sqlite/spawn_intents.rs:12` — import
- `internal/session/store/src/sqlite/mail.rs:9,237,259,328,346,365,387,406,524` — import + private helpers
- `internal/session/store/src/sqlite/sessions.rs:11` — import
- `internal/runtime/store/src/sqlite/lifecycle.rs:9,53` — import, private `pool: SqlitePool` field
- `crates/lilo-im-store/src/sqlite/audit.rs:9,51,176,212` — import, private `pool: SqlitePool` field, private `&SqlitePool` query/insert helpers (feature-gated under `sqlite`)

Role (iv) — test code (excluded by Gate 1 globs) — **8 hits**:

- `crates/lilo-im-store/tests/audit.rs:12,165,168`
- `internal/runtime/app/tests/integration_pass7.rs:103`
- `internal/runtime/daemon/src/handler/tests.rs:276` (inline `tests.rs` module — excluded via `-g '!**/tests.rs'`)
- `internal/session/daemon/tests/common/mod.rs:23,399`
- `internal/session/app/tests/cli_get_test/run_resolution.rs:104`

(Session store test files such as `mail_tests.rs` and `sessions_tests.rs` reach
the pool through `store.pool()`, which does not name a SQLite type, so they are
not among the 52 hits. They still must follow the `pool()` demotion to
`pub(crate)` to keep compiling.)

Note: `internal/session/store/src/sqlite.rs` and `crates/lilo-im-store/src/sqlite.rs`
are FILES (not dirs); the acceptance excludes both via `-g '!**/sqlite.rs'` and
`-g '!**/sqlite/**'`.
