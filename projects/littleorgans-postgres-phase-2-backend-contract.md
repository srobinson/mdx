# littleorgans Postgres Phase 2 Backend Contract

Status: draft for expert revalidation
Date: 2026-06-06
Parent plan: `/Users/alphab/.mdx/projects/littleorgans-postgres-persistence-plan.md`
Predecessors: `littleorgans-postgres-phase-1a-lilo-db-contract.md`,
`littleorgans-postgres-phase-1b-store-boundary-contract.md`
Cut-over baseline: `main` @ `f235cff` (PR #30, Phase 1.b merged)

## 1. Purpose And Inherited Locked Decisions

Phase 2 replaces the private SQLite implementation behind the neutral store
boundary with Postgres, deletes the transition scaffolding, and collapses
`LiloDb` to a single `PgPool`. After Phase 2 the workspace runs on Postgres
only. No SQLite dialect, type, backing, or migration directory survives.

This is a backend cut-over, not a naming sweep. The `sqlite` module and type
*names* (`internal/session/store/src/sqlite/`, `StoreError::Sqlite`, the `sqlite`
in doctor fields) are cosmetic and stay until Phase 5. See §6.

### State Phase 2 cuts over from (verified on `main` @ `f235cff`)

- `internal/db/src/lib.rs`: `LiloDb { backing: Backing }` with
  `Backing::Postgres(LiloPool)` and `Backing::Sqlite(SqlitePool)`. The Postgres
  target API already exists: `open_postgres`, `open_postgres_resolved`, `pool()`,
  `acquire()`, `begin(label) -> LiloTransaction<'_>`, `close()`. Type aliases
  `LiloPool = PgPool`, `LiloConnection = PgConnection`,
  `LiloTransaction<'a> = sqlx::Transaction<'a, Postgres>` are declared.
  `migrator()` points at `./migrations` (Postgres dir).
- `internal/db/src/transition.rs`: the entire SQLite transition surface
  (`open`, `open_path`, `identity_pool`/`session_pool`/`runtime_pool`,
  `sqlite_pool`, `sqlite_migrator` → `./migrations-sqlite`, `ImmediateTx`,
  `begin_immediate_tx`/`finish_immediate_tx` (conn-scoped),
  `begin_immediate_pool_tx`/`finish_immediate_pool_tx` (pool-scoped)).
- `internal/db/migrations/0001_unified_schema.sql`: already Postgres dialect but
  SQLite-faithful types (TEXT ids, mostly-TEXT timestamps, `BIGINT` ints,
  `BYTEA` cursor, `to_char(now() AT TIME ZONE 'UTC', …)` namespace default,
  **no `owner` column, no JSONB**).
- `internal/db/migrations-sqlite/0001_unified_schema.sql`: quarantined SQLite
  dialect (`INTEGER`, `BLOB`, `strftime`). The live daemon runs on this via
  `Backing::Sqlite` today.
- Neutral store exports with SQLite-typed private bodies: `SessionStore`
  (`internal/session/store`), `LifecycleStore` (`internal/runtime/store`),
  `AuditStore` (`crates/lilo-im-store`, published, `#[cfg(feature = "sqlite")]`).
- Cross-component tx threads one pool-scoped `lilo_db::ImmediateTx`.
- `lilo-im-store` "model X": default features empty = sqlx-free (re-exports
  `AuditSink`/`AuditRow`/`AuditError` from published `lilo-im-core`); `sqlite`
  feature gates the concrete `AuditStore`. No `postgres` feature yet.

### Inherited locked decisions (Phase 0)

1. Postgres is the single target backend; no dual backend.
2. SQLite may live only inside private modules while migration is in flight;
   Phase 2 removes the last of it.
3. Operator DB contract is `LILO_DATABASE_URL` (over `$LILO_HOME/settings.toml`).
4. Existing local SQLite data is disposable. This allowance expires the moment
   Phase 2 ships real Postgres schema and rows (decision 11).
5. `lilo-im-store` stays publishable and must not depend on `lilo-db`.
6. `LiloDb` exposes a concrete `PgPool`; no wider DB abstraction until a second
   backend exists.
7. Migrations are Postgres migrations; the quarantined SQLite dir is deleted.
8. `lilo-im-store` uses feature-gated backend support without `lilo-db`.
9. Postgres test provisioning landed in Phase 1.a (`lilo_db::test_support::TestDb`).
10. Owner seam: every persisted session/runtime-lifecycle/identity-audit table
    carries `owner TEXT NOT NULL DEFAULT 'local'` from the first real schema; v1
    writes `'local'`, enables no RLS. RLS is a documented future seam.
11. Forward-only migrations once real Postgres data exists.

### Decisions this contract introduces (require sign-off — see §9)

- **D-ID**: ID columns stay `text` (recommended) vs become native `uuid`. §7.
- **D-OWNER-IDX**: how `owner` folds into indexes. §2.
- **D-TS**: convert RFC3339-text time columns to `timestamptz`; keep the
  spawn-intent `BIGINT` epoch columns. §2.
- **D-PAYLOAD**: no JSONB/GIN/tsvector in Phase 2. §5.
- **D-TESTGATE**: keep DB tests honestly skipped without Postgres; the existing
  CI Postgres service runs them. §8.

## 2. Schema Specification (`internal/db/migrations/0001_unified_schema.sql`)

The Postgres migration is edited in place (single forward-only file; no second
migration is added — pre-release, no real rows exist yet, decision 4). Ten
tables. Per-table column changes:

### 2.1 Time columns → `timestamptz` (D-TS)

Today these are `TEXT` holding RFC3339 (`DateTime<Utc>::to_rfc3339()` on write,
`DateTime::parse_from_rfc3339` on read). Convert to `timestamptz`:

| table | columns |
|---|---|
| `identity_audit` | `timestamp` |
| `session_sessions` | `created_at`, `started_at`, `terminated_at`, `updated_at` |
| `session_namespaces` | `created_at` |
| `messages` | `sent_at` |
| `message_deliveries` | `read_at` (nullable) |
| `session_event_cursor` | `updated_at` |
| `runtime_lifecycle` | `start_time` (nullable), `spawned_at`, `updated_at` |
| `runtime_metadata` | `updated_at` |

- Change the namespace seed insert from
  `to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')` to plain
  `now()`.
- Phase 2 is the cheapest moment for this change: after it ships, decision 11
  makes `text→timestamptz` a data-migrating `ALTER … USING`. Doing it now is
  zero-data and mechanical.
- This column-type change forces a `String`→`DateTime<Utc>` bind/decode change at
  every timestamp site. Those sites are enumerated exhaustively in §3.4; they are
  not optional follow-on work, they are part of the same atomic change.

**Exception — keep `BIGINT` epoch:** `session_spawn_intents.created_at`,
`updated_at`, `resolved_at` are `BIGINT` epoch-millis (`i64` from
`Utc::now().timestamp_millis()`), not RFC3339 text. They back a millis domain
field, are transient (row deleted on resolve), and have no cross-table time
comparison. Keep them `BIGINT`. (Flag for sign-off; converting them would churn
`SessionSpawnIntent`/`SessionDraft` domain types for no functional gain.)

### 2.2 Owner seam (decision 10, D-OWNER-IDX)

Add `owner TEXT NOT NULL DEFAULT 'local'` to exactly three tables:
`session_sessions`, `runtime_lifecycle`, `identity_audit`.

Index treatment (sign-off item): all three have surrogate-`uuid` primary keys
(`id` / `session_id`), so no *unique* index needs `owner` for v1 correctness —
ids do not collide across owners. Recommended: prepend `owner` to the
**listing** indexes so future per-owner scans are index-supported:

- `idx_session_sessions_namespace_terminated` → `(owner, namespace, terminated_at)`
- `idx_runtime_lifecycle_state` → `(owner, state)`
- `idx_identity_audit_timestamp` → `(owner, timestamp)`

RLS is **not** enabled. Document the per-owner RLS policy as a future seam in a
SQL comment. `messages.idempotency` and `session_namespaces.slug` are
owner-scoped *conceptually* but are out of decision-10 scope (only the three
named tables get `owner`); note this and do not widen scope without sign-off.

### 2.3 Already Postgres-correct (no Phase 2 change)

- Integer columns are `BIGINT` (`runtime_pid`, `shim_pid`, `exit_code`,
  `exit_signal`, `runtime_pid`, `exit_code`, `runtime_session` pid fields).
  Decode types already match (`i64` → `u32`/`i32` in `codec.rs`).
- `session_event_cursor.cursor` is `BYTEA`; the store binds `Vec<u8>`
  (`cursor.to_be_bytes().to_vec()`) and decodes `try_get::<Vec<u8>>`. No change.
- `strftime` exists only in the quarantined SQLite migration; store bodies hold
  no `strftime`. The Postgres default already uses a timestamp expression.
- `_sqlx_migrations` stays sqlx-owned (sqlx creates the Postgres variant; the
  SQLite one vanishes with `migrations-sqlite`).

### 2.4 ID columns (D-ID) — see §7 for the full fork analysis

Recommended: keep id columns `text` (36-char). If sign-off chooses native
`uuid`, apply the column-type change here and the §7 churn.

## 3. Query Migration (per store)

General rules:
- Positional `?` and numbered `?1` placeholders → Postgres `$N`. `QueryBuilder`
  `push_bind` auto-numbers under `QueryBuilder::<Postgres>`; hand-written SQL is
  converted by hand.
- `QueryBuilder::<Sqlite>` → `QueryBuilder::<Postgres>` (4 sites).
- `Executor<'e, Database = Sqlite>` → `Database = Postgres` (12 sites).
- `sqlx::Transaction<'_, Sqlite>` → `Transaction<'_, Postgres>` (events.rs ×3,
  namespaces.rs ×2).
- `BEGIN IMMEDIATE` semantics: Postgres needs no upfront write-lock acquisition;
  a plain `db.begin(label)` (`BEGIN`, READ COMMITTED) is correct. The atomicity
  and idempotency guarantees that `BEGIN IMMEDIATE` protected are preserved by
  the transaction boundary + `ON CONFLICT`/unique indexes (see mail below).
- `ON CONFLICT (...) DO UPDATE SET … = excluded.…` is already Postgres-valid and
  is **preserved verbatim** at all three sites: `labels.rs` (`(session_id, key)`),
  `lifecycle.rs` runtime_metadata (`(key)`), `events.rs` cursor (`(id)`).

### 3.1 `lilo-im-store` audit (`crates/lilo-im-store/src/sqlite/audit.rs`)

- `AUDIT_ROW_PLACEHOLDERS = "?, ?, …"` (11) → `"$1, $2, … $11"`.
- `query_audit_rows`: `QueryBuilder::<Sqlite>` → `<Postgres>`; the
  `WhereClause`/`push_bind` predicate building is dialect-neutral and unchanged.
- `ORDER BY rowid ASC` → `ORDER BY timestamp ASC, id ASC` (Postgres has no
  `rowid`; `timestamp` is the natural audit order, `id` the deterministic
  tiebreak). With `timestamp` now `timestamptz`, the sort is native temporal.
- `audit_table_columns()` uses `PRAGMA table_info(identity_audit)` returning
  name/type/notnull/pk → replace with an `information_schema.columns` query
  (`SELECT column_name, data_type, is_nullable …`) plus a `pg_index`/
  `information_schema.table_constraints` join for `primary_key`. **Verify the
  caller**: this is diagnostic (doctor/schema check); if its only consumer is a
  doctor smoke, a simpler `information_schema` query suffices. `AuditTableColumn`
  stays neutral.
- `insert_audit_row_with<E: Executor<Database = Sqlite>>` → `Postgres`.
- `SqliteRow` → `PgRow`; `SqliteConnection`/`SqlitePool`/`Sqlite` → Postgres.
- `record_audit_in_tx(conn: &mut SqliteConnection, …)` →
  `record_audit_in_tx(conn: &mut sqlx::PgConnection, …)`. im-store still imports
  no `lilo-db`; the identity service passes `&mut **tx` from its
  `&mut LiloTransaction` (which derefs to `PgConnection`).

### 3.2 Session store (`internal/session/store/src/sqlite/*.rs`)

- `mail.rs`: `?` → `$N` across all statements (insert_message 7, insert_deliveries
  4, and the read/count helpers); `QueryBuilder::<Sqlite>` (`MESSAGE_LOG_SELECT_SQL`
  keyset build, line ~194) → `<Postgres>`; two `Executor<Database = Sqlite>`
  helpers → `Postgres`. **Idempotency unchanged**: the path is SELECT-then-INSERT
  inside the tx (`message_by_idempotency` → `validate_idempotent_replay` →
  `insert_message`/`insert_deliveries`), returning `MailWriteOutcome { inserted }`.
  No `ON CONFLICT` exists; the partial unique index
  `idx_messages_sender_idempotency` is the backstop. Preserve both the SELECT-first
  logic and the partial unique index. `finish_immediate_pool_tx(tx, result)` →
  `tx.commit()` on Ok, drop-rollback on Err (§4).
- `spawn_intents.rs`: `?` → `$N` (INSERT 7 + 2 literal NULLs; status UPDATE 5;
  list 1); keep `BIGINT` epoch binds/decodes (`i64`/`Option<i64>`); four
  `Executor<Database = Sqlite>` → `Postgres`; `ImmediateTx` `*_in` params →
  `LiloTransaction` (§4); `finish_immediate_pool_tx` → commit.
- `sessions.rs`: `?` → `$N`; one `Executor<Database = Sqlite>` → `Postgres`;
  **prefix selector** `WHERE id LIKE ? || '%'` → `WHERE id LIKE $1 || '%'` (text
  id). `Selector::n`/prefix resolution and `SessionRowError::Ambiguous { prefix,
  candidates }` behavior unchanged. If D-ID = uuid, this becomes
  `WHERE id::text LIKE $1 || '%'` plus a functional index (§7).
- `events.rs`: `?` → `$N`; cursor upsert
  `INSERT … VALUES (1, $1, $2) ON CONFLICT (id) DO UPDATE …` (already ANSI);
  cursor bind stays `Vec<u8>`; three `Transaction<'_, Sqlite>` helper sigs →
  `Postgres`. State literals (`'RUNNING'`, etc.) unchanged.
- `labels.rs`: numbered `?1` → `$1`; `ON CONFLICT (session_id, key) DO UPDATE`
  preserved; `Executor<Database = Sqlite>` → `Postgres`.
- `namespaces.rs`: `?` → `$N`; two `sqlx::Transaction<'_, sqlx::Sqlite>` sigs →
  `Postgres`.

### 3.3 Runtime store (`internal/runtime/store/src/sqlite/lifecycle.rs` + `lifecycle/codec.rs`)

- `?` → `$N`: `INSERT_FORKING_SQL` (13), `UPDATE_LIFECYCLE_SQL` (12), the two
  `DELETE` statements, `record_probe_sweep` upsert (3, `ON CONFLICT (key) DO
  UPDATE` preserved).
- `QueryBuilder::<Sqlite>` → `<Postgres>` (`lifecycle_rows_query` ~327,
  `recent_lost_since` ~229). `LOWER(state) = LOWER(?)` is Postgres-valid.
  `updated_at >= ?` becomes a `DateTime<Utc>` bind once `updated_at` is
  `timestamptz` (proper temporal compare; supersedes lexicographic text).
- Two `Executor<Database = Sqlite>` → `Postgres`.
- `ImmediateTx` `*_in` params (`insert_forking_in`, `update_lifecycle_in`,
  `delete_in`) → `LiloTransaction` (§4).
- `codec.rs`: `BIGINT` decodes (`decode_u32`/`decode_i32` over `Option<i64>`)
  unchanged; text/JSON encodings unchanged; `#[derive(sqlx::FromRow)]` structs
  (`LifecycleRow`, `RecentLostRow`, `StateCountRow`) keep `session_id: String`
  under D-ID=text (switch to the typed id only under D-ID=uuid). The
  `_sqlx_migrations.version` read (`i64`) is valid against Postgres
  sqlx-migrate; the `success` predicate in the same query is not — see §3.5.

### 3.4 Timestamp bind/decode (D-TS) — every site

Converting the §2.1 columns to `timestamptz` requires replacing RFC3339-`String`
encode/decode with native `chrono::DateTime<Utc>` everywhere. sqlx with
`chrono` + `postgres` maps `timestamptz` ↔ `DateTime<Utc>` directly. Exhaustive
sites (verified on `main` @ `f235cff`):

**Binds — drop `.to_rfc3339()`, bind `DateTime<Utc>`; `Utc::now().to_rfc3339()` →
`Utc::now()`:**
- session store: `sessions.rs:268,269,292,314,352,353,357,360`;
  `mail.rs:132,173,215,252,272`; `events.rs:57,58,73,115,134`;
  `namespaces.rs:57`.
- runtime store: `lifecycle.rs:166,235` (filter binds) and the `updated_at` bind
  in `record_probe_sweep` (`:246`); `lifecycle/codec.rs:70,75` (`EncodedLifecycle`
  binds `spawned_at`/`updated_at` from `now`).
  **Not `runtime_metadata.value`:** `record_probe_sweep` (`:245-263`) binds the
  same RFC3339 string into *both* `value` and `updated_at`. `value` is a
  polymorphic `TEXT` key-value column and stays `TEXT` (§2.1 converts only
  `runtime_metadata.updated_at`); keep the `value` bind a `String`, convert only
  the `updated_at` bind to `DateTime<Utc>` (`.bind(swept_at)`).
- im-store: `audit.rs:118,197`.

**Decodes — drop `parse_timestamp`/`parse_optional_timestamp`/`parse_time` +
`try_get::<String>`/`try_get::<Option<String>>`, use `try_get::<DateTime<Utc>>`
/ `try_get::<Option<DateTime<Utc>>>`:**
- session store: `sessions.rs:442,443,444,448`; `mail.rs:285,286,422,516`;
  `namespaces.rs:124`.
- runtime store: `lifecycle/codec.rs:91,105`. **`last_probe_sweep`
  (`lifecycle.rs:265-277`) is redirected, not type-swapped:** change
  `SELECT value` + `query_scalar::<_, String>` + `parse_time(&value)` to
  `SELECT updated_at` + `query_scalar::<_, DateTime<Utc>>` so the read sources
  the `timestamptz` column directly and stops parsing the polymorphic `TEXT`
  `value`. This must land *with* the `parse_time` deletion below — otherwise
  deleting `parse_time` breaks this read.
- im-store: `audit.rs:153` (`parse_from_rfc3339`) via the `EncodedAuditRow`
  `try_into_audit_row` path.

**`#[derive(sqlx::FromRow)]` / encoded-struct time fields `String` → `DateTime`:**
- im-store `audit.rs:102` `EncodedAuditRow.timestamp: String` → `DateTime<Utc>`.
- runtime `lifecycle/codec.rs:23` `LifecycleRow.start_time: Option<String>` →
  `Option<DateTime<Utc>>`; `:40` `RecentLostRow.updated_at: String` →
  `DateTime<Utc>`; `:50` `EncodedLifecycle.start_time: Option<String>` →
  `Option<DateTime<Utc>>` (and the `now`/`spawned_at`/`updated_at` fields).

**Keyset/range comparisons** (`lifecycle.rs` `updated_at >= $N`, `audit.rs`
`timestamp >= $N`, `mail.rs` `(sent_at, message_id)` cursor) become native
temporal compares once columns and binds are `DateTime<Utc>`. This is a
correctness *improvement* over the prior lexicographic text compare; the
`(sent_at, message_id)` ordering and mail keyset behavior are preserved.

**Functional dead code to delete in Phase 2 (now unused):**
- `internal/session/store/src/sqlite/time.rs` (`parse_timestamp`,
  `parse_optional_timestamp`).
- `internal/runtime/store/src/sqlite/lifecycle/codec.rs` `parse_time` (`:199-200`).
- im-store `StoreError::Timestamp(#[from] chrono::ParseError)` variant once
  decodes no longer parse text. Removing it is functional, not cosmetic; Phase 2
  scope.

### 3.5 Boolean semantics — Postgres `BOOLEAN`, not `0`/`1`

SQLite stores booleans as `0`/`1` integers; Postgres has a real `boolean` type.
Three sites are Postgres-invalid as written:

- `runtime/store/.../lifecycle.rs:286` `migration_state`:
  `… WHERE success = 1 …` → `… WHERE success …` (`_sqlx_migrations.success` is
  `BOOLEAN`; `= 1` is a type error). The selected `version` (`BIGINT`→`i64`)
  decode is unaffected.
- `session/store/.../namespaces.rs:38` `namespace_exists`:
  `query_scalar::<_, i64>("SELECT EXISTS(…)")` + `exists != 0` →
  `query_scalar::<_, bool>(…)` returning the bool directly. Postgres `EXISTS`
  yields `boolean`; decoding it as `i64` fails.
- `session/store/.../namespaces.rs:356` `message_exists` (test helper): same
  `EXISTS`-as-`i64` + `!= 0` → `bool`.

Not boolean fixes: the `PRAGMA table_info` `notnull`/`pk` `!= 0` decodes
(`audit.rs:72,73`) vanish with the §3.1 `information_schema` replacement
(`is_nullable` text + constraint join), not a `= true` edit. `mail.rs:508
WHERE 1 = 1` (query-builder seed predicate) is valid Postgres; no change.

## 4. Transition Removal And Transaction Replacement

Delete:
- `internal/db/src/transition.rs` (whole file) and the `mod transition;` +
  `pub use transition::{…}` re-export block in `internal/db/src/lib.rs`.
- `internal/db/migrations-sqlite/` (whole dir) and `sqlite_migrator()`.
- The `Backing` enum: collapse `LiloDb` to `#[derive(Clone)] pub struct LiloDb {
  pool: LiloPool }`. `pool()` returns `&self.pool` (no panic arm); `close()`
  closes the single pool. Remove `open`, `open_path`, `identity_pool`,
  `session_pool`, `runtime_pool`, `sqlite_pool`.
- The workspace/`internal/db` sqlx `sqlite` feature, once nothing compiles
  against it.

Replace the cross-component transaction:
- The threaded handle changes from `lilo_db::ImmediateTx` (a
  `PoolConnection<Sqlite>` wrapper running `BEGIN IMMEDIATE`) to
  `lilo_db::LiloTransaction<'_>` (`sqlx::Transaction<'_, Postgres>`, already
  declared).
- Store `begin_immediate_tx(&self) -> ImmediateTx` wrappers
  (`session/store/src/sqlite.rs`, `runtime/store/src/sqlite/lifecycle.rs`) →
  return `LiloTransaction` via the held pool/`LiloDb` (`self.pool.begin()` or
  `db.begin(label)`).
- `*_in(tx: &mut ImmediateTx, …)` methods → `*_in(tx: &mut LiloTransaction<'_>,
  …)` and execute against `&mut **tx`.
- `begin_immediate_pool_tx`/`finish_immediate_pool_tx` callers (mail.rs,
  spawn_intents.rs, session daemon `handler/spawn.rs`, runtime daemon
  `identity.rs`, identity service tests, integration `session_spawn_contract.rs`)
  → `db.begin(label)` then `tx.commit().await` on success; sqlx `Transaction`
  rolls back on drop, so the `finish_immediate_pool_tx` Err arm becomes "return
  the error and drop tx". A small `commit_or_rollback(tx, result)` helper on
  `lilo-db` may replace the deleted `finish_immediate_pool_tx` to keep callers
  DRY (optional; do not re-introduce a SQLite-named helper).
- Identity audit path: `IdentityPort::authorize_in_tx` /
  `IdentityClient::authorize_in_tx` take `&mut LiloTransaction`; pass `&mut **tx`
  into im-store `record_audit_in_tx(&mut PgConnection, …)`.

`lilo-im-store` feature flip:
- `crates/lilo-im-store/Cargo.toml`: replace `sqlite = [...]` with
  `postgres = ["dep:sqlx", "sqlx/postgres", "sqlx/runtime-tokio", …]`. Default
  features stay empty (sqlx-free published surface). The acceptance invariant
  `! grep -q 'lilo-db' crates/lilo-im-store/Cargo.toml` still holds.
- `crates/lilo-im-store/src/lib.rs`: gate the concrete module on
  `#[cfg(feature = "postgres")]`. Keep the module *path* `sqlite` until Phase 5
  (cosmetic rename), or rename to a neutral path now only if sign-off folds that
  cosmetic step into Phase 2 (§6 — default is keep the name).
- Internal consumers that need the concrete store enable
  `lilo-im-store/postgres` (identity service; session/runtime daemons that build
  `AuditStore::with_pool`).

## 5. Rich Payload Types — Evaluate, Do Not Force (D-PAYLOAD)

Recommendation: **introduce no JSONB, GIN, or tsvector in Phase 2.** No
containment or full-text query exists in the codebase to justify index
maintenance. Keep `TEXT`/`BYTEA`. Document each as a future seam (SQL comment)
to revisit when a concrete query lands:

| candidate | column | current | verdict |
|---|---|---|---|
| structured config | `session_sessions.agent_config` | `TEXT` (serde_json) | stays `TEXT`; no containment query. JSONB+GIN future seam. |
| policy trace | `identity_audit.evaluation_trace` | `TEXT` (reserved, v2 policy) | stays `TEXT`; never queried. |
| message body | `messages.content` | `TEXT` | stays `TEXT`; mail list filters by context/sender/time, not content. STORED `tsvector` future seam. |
| transient payloads | `session_spawn_intents.spawn_request_json`, `session_draft_json` | `TEXT` (serde_json) | stays `TEXT`; transient, never queried by content. |

This matches the plan's "default to text/bytea unless a concrete containment or
full-text query exists."

## 6. Scope Boundary vs Phase 3 and Phase 5

**Phase 2 owns (functional cut-over):**
- Schema column types + owner seam (§2).
- All SQL dialect migration in the three store bodies + im-store (§3).
- Transition deletion + `LiloDb` collapse + tx-handle swap + im-store feature
  flip (§4).
- **All mechanical compile-follows** that transition deletion forces across the
  workspace: every `LiloDb::open`/`open_path` caller switches to
  `open_postgres_resolved()`/config-based open; every `db.pool()`/`*_pool()`
  read uses `PgPool`; every `AuditStore::with_pool(SqlitePool)` →
  `with_pool(PgPool)`; every `ImmediateTx` reference → `LiloTransaction`. This
  spans the session daemon, runtime daemon, identity service, both apps, doctor,
  and the test/integration fixtures (see §8 blast radius). They must follow in
  Phase 2 because the workspace must compile and the suite must be green at
  phase exit (full-suite-green lesson). The daemon opening Postgres instead of
  SQLite is a *required* consequence of removing `open`, not optional Phase 3
  work.

**Phase 3 owns (semantic caller migration, NOT Phase 2):**
- Integration fixtures graduating from "compiles against Postgres" to creating
  *isolated* per-test Postgres databases via `TestDb` with full coverage.
- Doctor *health semantics* and admin/driver *protocol* redesign beyond the
  mechanical pool-type follow.
- Any richer caller behavior not required merely to compile.

**Phase 5 owns (cosmetic, NOT Phase 2):**
- Module renames (`internal/**/sqlite/` → neutral; `lilo-im-store/src/sqlite/`),
  type/variant renames (`StoreError::Sqlite`, error string "sqlite error"),
  doctor response fields named `sqlite`, snapshots, README/architecture docs.

**Consequence for the Phase 2 residue gate:** the acceptance `rg` must target
**functional** tokens (`SqlitePool`, `SqliteConnection`, `sqlx::Sqlite`,
`PoolConnection<Sqlite>`, `BEGIN IMMEDIATE`, `PRAGMA`, `sqlite_master`,
`ImmediateTx`, `begin_immediate`, `migrations-sqlite`, `QueryBuilder::<Sqlite>`,
`Database = Sqlite`) → **zero** in `internal` + `crates`. A blanket
`rg -i sqlite` will still hit surviving module/type *names* and is **Phase 5's**
gate, not Phase 2's. Workers must not pull Phase 5 renames forward (scope +
merge-churn discipline); reviewers must not fail Phase 2 on cosmetic name hits.

## 7. Critical Design Fork: ID Columns `text` vs native `uuid` (D-ID)

This is on the plan's peer-consensus list and needs Stuart's call.

**Type-layer fact:** `crates/lilo-common/src/id.rs` `define_id!` derives
`#[cfg_attr(feature = "sqlx", derive(sqlx::Type), sqlx(transparent))]` over
`uuid::Uuid`. So `Type`/`Encode`/`Decode` already delegate to `Uuid` — native
`uuid` columns are drop-in at the macro layer (`bind(id)` / `try_get::<SessionId>`
just work). The macro is **not** the churn.

**Call-site fact:** every store call site bypasses the transparent impl and binds
`id.to_string()` / decodes `try_get::<String, _>("id")?.parse()`, because the
columns are `text`. ~30 bind sites + ~6 decode sites + 3 `FromRow` structs across
`sessions.rs`, `mail.rs`, `spawn_intents.rs`, `events.rs`, `labels.rs`,
`namespaces.rs`, `lifecycle.rs`/`codec.rs`. The **load-bearing dependency** is the
git-style short-prefix selector (`sessions.rs` `WHERE id LIKE ? || '%'`,
`Selector::n`, `MIN_SELECTOR_PREFIX_LEN`, `SessionRowError::Ambiguous`).

| | **text (recommended)** | **native uuid** |
|---|---|---|
| Prefix selector | `WHERE id LIKE $1 \|\| '%'` works as-is | needs `WHERE id::text LIKE $1 \|\| '%'` + a functional index `((id::text) text_pattern_ops)`; cast bypasses the PK btree |
| Call-site churn | placeholder-only (`?`→`$N`); keep `.to_string()`/`.parse()` | ~30 binds → `bind(id)`, ~6 decodes → `try_get::<SessionId>`, 3 `FromRow` String→typed id |
| Indexed prefix | add `text_pattern_ops` index on `id` if needed (perf-only at v1 scale) | functional `((id::text) text_pattern_ops)` index required |
| Storage | 36 bytes/id | 16 bytes/id |
| DB-level validation | none (text) | native uuid validation |
| typed-id spirit | Rust layer still fully typed (`SessionId` etc.) | also typed at the DB layer |

**Recommendation: keep `text`.** One-clause why: native `uuid` forces an
`id::text LIKE` cast plus a functional index for the load-bearing git-style
prefix selector and ~36 sites of bind/decode churn, for a 20-byte/row storage win
that is irrelevant at single-operator v1 scale — while the typed-id family still
enforces types in Rust regardless of column type. (If sign-off prefers `uuid`,
apply the §2.4 column change, the `id::text` prefix query, the functional index,
and the call-site churn; the macro layer needs no change.)

Perf note (either choice): under non-C collation a plain btree does not serve
`LIKE 'prefix%'`. For `text`, add `CREATE INDEX … ON session_sessions (id
text_pattern_ops)` if/when prefix lookup is hot. At v1 scale a seq scan over a
handful of sessions is acceptable, so this index is a perf affordance, not a
correctness requirement.

## 8. File-By-File Plan, Blast Radius, Slicing

### 8.1 Core (functional)

| file | change |
|---|---|
| `internal/db/src/lib.rs` | collapse `Backing`→`{ pool }`; drop transition re-exports + `mod transition`; `pool()`/`close()` single-arm |
| `internal/db/src/transition.rs` | **delete** |
| `internal/db/migrations-sqlite/` | **delete** |
| `internal/db/migrations/0001_unified_schema.sql` | timestamptz, owner seam (+listing indexes), `now()` default; id type per D-ID |
| `internal/db/Cargo.toml` + workspace `Cargo.toml` | drop sqlx `sqlite` feature |
| `internal/db/src/test_support.rs` | verify Postgres-only (already `open_postgres`); no SQLite refs |
| `internal/session/store/src/sqlite.rs` + `sqlite/{sessions,mail,spawn_intents,events,labels,namespaces}.rs` | §3.2 |
| `internal/runtime/store/src/sqlite/lifecycle.rs` + `lifecycle/codec.rs` | §3.3 |
| `crates/lilo-im-store/src/lib.rs` + `src/sqlite/audit.rs` + `Cargo.toml` | §3.1, §4 feature flip |
| `internal/identity/service/src/client.rs` | `ImmediateTx`→`LiloTransaction`; `with_pool(PgPool)`; enable `lilo-im-store/postgres` |

### 8.2 Mechanical compile-follows (required for green; see §6)

The plan's Phase 2 "Likely files" list is **not** the real blast radius —
deleting `open`/`open_path`/`ImmediateTx`/`*_pool` breaks every caller below.
Verified callers (from repo-wide grep):

- Live daemon open paths → `open_postgres_resolved()`/config open:
  `internal/session/daemon/src/{service.rs,server.rs,events.rs}`,
  `internal/session/app/src/compose.rs`,
  `internal/runtime/daemon/src/{service.rs,server/state.rs,server/runner.rs}`,
  `internal/runtime/app/src/cli/initdb.rs`, `crates/lilo/src/cli/doctor.rs`.
- `db.pool()`/`*_pool()` reads + `AuditStore::with_pool`:
  `internal/session/daemon/src/{service.rs,server.rs}`,
  `internal/identity/service/src/client.rs`, `crates/lilo/src/cli/doctor.rs`,
  plus the store constructors (`sqlite.rs`, `lifecycle.rs`).
- `ImmediateTx`/`begin_immediate_*` references:
  `internal/session/daemon/src/{handler/spawn.rs,identity_client.rs}`,
  `internal/runtime/daemon/src/identity.rs`.
- Tests that open via the transition path (flip to `TestDb`/Postgres, gated):
  `internal/session/store/src/sqlite/{sessions_tests.rs,events.rs}`,
  `internal/session/daemon/src/{service.rs,events.rs,handler/spawn/tests.rs}`,
  `internal/session/daemon/tests/{common/mod.rs,server_concurrency.rs,handler/spawn_recovery.rs}`,
  `internal/session/driver/tests/port_conformance.rs`,
  `internal/session/app/tests/{common/mod.rs,cli_get_test/run_resolution.rs}`,
  `internal/runtime/daemon/src/{test_support.rs,reconcile/tests.rs,handler/tests.rs,server/tests.rs,spawn_preflight/tests/helpers.rs}`,
  `internal/runtime/store/src/sqlite/lifecycle.rs` (test mod),
  `internal/runtime/app/tests/integration_pass7.rs`,
  `internal/identity/service/tests/factory.rs`,
  `tests/integration/src/lib.rs` (`IntegrationFixture::open`) +
  `tests/integration/tests/{db_contract,session_spawn_contract,shutdown_contract}.rs`.

This is the bulk of the work. The `lilo_db::test_support::TestDb` fixture
(Phase 1.a) is the substitute for `LiloDb::open_path(tempfile)`; the
`IntegrationFixture` switches to it. Test-time SQLite temp-path construction
disappears.

### 8.3 Test gating (D-TESTGATE)

Recommendation: **keep DB-backed tests honestly skipped without Postgres, and
broaden the DB run from `-p lilo-db` to the whole workspace.** Do not make the
default `cargo nextest run --workspace` require a live database — that would turn
the no-DB dev/lint path red and break the honest-skip design Phase 1.a
established. But the *current* gate only covers `lilo-db`, which is the gap: after
cutover the session, runtime, im-store, daemon, and integration DB tests must
also run against Postgres.

Current state (verified):
- `.github/workflows/pr.yml` step "lilo-db Postgres tests":
  `cargo nextest run -p lilo-db --run-ignored all` (after `moon ci`; the job's
  postgres service + `LILO_TEST_DATABASE_URL` env are already configured).
- `justfile` `test-db`: `cargo nextest run -p lilo-db --run-ignored all`.

Required Phase 2 change (two parts):

1. **Annotate** every new DB-requiring test (session store, runtime store,
   im-store, session/runtime daemon, `tests/integration`) with the same
   `#[ignore = "requires Postgres: set LILO_TEST_DATABASE_URL …"]` pattern
   `lilo-db` uses, so the no-DB suite (`moon ci` / plain
   `cargo nextest run --workspace`) skips them honestly. This is the direct
   countermeasure to the 1.a masking lesson (scoped-green hiding workspace-red).

2. **Broaden the runner** from one package to the workspace, and from
   `--run-ignored all` to `--run-ignored ignored-only` (run exactly the gated DB
   tests; `moon ci` already ran the no-DB suite, so re-running it under `all`
   is wasted CI time):

   `justfile`:
   ```make
   test-db:
       CARGO_TARGET_DIR={{TARGET_NEXTEST}} cargo nextest run --workspace --run-ignored ignored-only
   ```

   `.github/workflows/pr.yml` (rename the step; it inherits the same postgres
   service + `LILO_TEST_DATABASE_URL` job env):
   ```yaml
   - name: Postgres-backed DB tests (workspace)
     run: cargo nextest run --workspace --run-ignored ignored-only
   ```

This satisfies both the full-suite-green lesson (no-DB suite green by skipping)
and the orchestrator's "0-failed against Postgres" (the DB job now proves
session/runtime/im-store/daemon/integration DB tests, not just `lilo-db`).
Note the local compose host port is `55432` (justfile doc comment) while the CI
service uses `5432`; keep both, change only the package/run-ignored scope.

### 8.4 Acceptance

```bash
# functional proof against Postgres (local; CI DB job is the workspace step in §8.3)
docker compose up -d --wait postgres
# local compose maps host 55432 (justfile); the CI service uses 5432
LILO_TEST_DATABASE_URL=postgres://lilo:lilo@localhost:55432/lilo \
  cargo nextest run --workspace --no-fail-fast --run-ignored all   # 0 failed
# honest no-DB suite still green (DB tests skipped, nothing red)
cargo nextest run --workspace --no-fail-fast                       # 0 failed
just check && just build
fmm generate && fmm validate    # files moved/deleted
scripts/check-env.sh --check
```

Functional residue (must be zero in `internal` + `crates`):

```bash
rg "SqlitePool|SqliteConnection|sqlx::Sqlite|PoolConnection<Sqlite>|BEGIN IMMEDIATE|PRAGMA|sqlite_master|ImmediateTx|begin_immediate|finish_immediate|QueryBuilder::<Sqlite>|Database = Sqlite" internal crates
test ! -d internal/db/migrations-sqlite
test ! -f internal/db/src/transition.rs
! grep -q 'lilo-db' crates/lilo-im-store/Cargo.toml
```

Behavior-unchanged checks (the four named acceptance items + audit):
- Prefix selector: short-prefix resolve returns the unique session; ambiguous
  prefix errors with the candidate list (`SessionRowError::Ambiguous`).
- Mail idempotency: re-send with the same `(sender_ref, idempotency_key)` returns
  `inserted: false` and no duplicate row; a conflicting replay errors.
- Spawn intent: insert→resolve and insert→abort transitions commit/rollback
  atomically; the transient row is deleted on resolve.
- Runtime lifecycle reconcile: insert/update/delete via `LiloTransaction`
  preserve state-machine behavior; `recent_lost_since`/`list` filters unchanged.
- Audit: `record`/`record_audit_in_tx` insert; `query_audit` filters + ordering
  (now `timestamp, id`) return the expected rows.

### 8.5 Slicing recommendation

**Phase 2 is atomic; it cannot be sliced per store crate.** Three seams flip
together:

1. The transition surface (`transition.rs`, `Backing::Sqlite`, `ImmediateTx`,
   `*_pool` accessors, `migrations-sqlite`) is shared by all three stores and
   the daemons; it cannot be deleted until the last caller leaves, and
   `LiloDb` cannot be half-collapsed.
2. The cross-component tx handle (`ImmediateTx` → `LiloTransaction`) is one typed
   change spanning session store, runtime store, identity service, and both
   daemons simultaneously.
3. The daemon opens exactly one `LiloDb`. There is no half-Postgres daemon:
   Postgres-dialect store bodies (`$N`, `QueryBuilder::<Postgres>`) cannot
   execute on a `SqlitePool`, so the store-body migration, the schema change, and
   the daemon open-path flip are inseparable.

Therefore: **one atomic PR**, built in a worktree with the Postgres service up,
verified by the full `--run-ignored all` suite. Recommended internal commit
order (commits may be transiently red mid-PR; only the PR tip must be green):
(1) schema edit; (2) `lilo-db` collapse + tx helpers; (3) three store bodies +
im-store; (4) all caller/test compile-follows; (5) feature flip + test gating +
residue sweep. The only defensible smaller-review split is the "two checked
commits" compromise — (A) store-body dialect + schema + caller follows reaching
compile, (B) transition deletion + `LiloDb` collapse — but (A) is not
independently shippable or verifiable (the daemon still can't run until the
backing flips in B), so prefer the single atomic PR.

## 9. Sign-Off Items (peer consensus before implementation)

1. **D-ID** — id columns `text` (recommended) vs native `uuid` (§7).
2. **D-OWNER-IDX** — `owner` added to the three tables; folded into the listing
   indexes; no unique-index change (surrogate-uuid PKs); RLS off (§2.2).
3. **D-TS** — RFC3339-text time columns → `timestamptz`; spawn-intent `BIGINT`
   epoch columns kept (§2.1).
4. **D-PAYLOAD** — no JSONB/GIN/tsvector in Phase 2 (§5).
5. **D-TESTGATE** — DB tests stay honestly skipped (`#[ignore]`) without
   Postgres; CI + `just test-db` broaden from `-p lilo-db` to
   `--workspace --run-ignored ignored-only` so session/runtime/im-store/daemon/
   integration DB tests run against the Postgres service (§8.3).
6. **Atomic vs sliced** — confirm Phase 2 ships as one atomic PR (§8.5).

## Appendix: Survey Evidence (verified on `main` @ `f235cff`)

- Placeholders: positional `?` pervasive; numbered `?1` only in
  `session/store/src/sqlite/labels.rs`. Hand-written `?` counts: lifecycle
  INSERT 13 / UPDATE 12 / metadata 3; mail insert_message 7 / deliveries 4;
  spawn_intents INSERT 7 / UPDATE 5; audit `AUDIT_ROW_PLACEHOLDERS` 11.
- `QueryBuilder::<Sqlite>` (4): `im-store/audit.rs:179`,
  `runtime/.../lifecycle.rs:229,327`, `session/.../mail.rs:194`.
- `Executor<'e, Database = Sqlite>` (12): audit.rs:218; labels.rs:94;
  lifecycle.rs:335,352; sessions.rs:325; spawn_intents.rs:282,310,328,346;
  mail.rs:449,468.
- `sqlx::Transaction<'_, Sqlite>` sigs (5): namespaces.rs:156,167;
  events.rs:38,102,123.
- `PRAGMA table_info`: only `im-store/audit.rs:65`. `ORDER BY rowid`: only
  `im-store/audit.rs:199`. `strftime`: only `migrations-sqlite/0001…sql:48`.
- Prefix selector: `session/.../sessions.rs:167 WHERE id LIKE ? || '%'`; ambiguity
  → `SessionRowError::Ambiguous { prefix, candidates }`.
- `ON CONFLICT` (3, all Postgres-valid): labels.rs:99 `(session_id, key)`;
  lifecycle.rs:251 `(key)`; events.rs:129 `(id)`.
- Cursor: `EventCursor` (`u64`) → 8-byte BE → `Vec<u8>` → `BYTEA` (already).
- Spawn-intent timestamps: `BIGINT` epoch-millis `i64` (contrast: all other
  tables use RFC3339 `TEXT`).
- `define_id!` (`lilo-common/src/id.rs`): `sqlx(transparent)` over `uuid::Uuid`
  (native-uuid drop-in at the type layer; stores bypass it with text).
- Transition surface and Postgres target both live in `internal/db/src/`
  (`transition.rs` vs `lib.rs` + `migrations/`).
