# am-store Persistence Layer Review

**Date:** 2026-03-13
**Reviewer:** database-administrator agent
**Codebase:** `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-store/`
**Files reviewed:** store.rs (1596 LOC), project.rs (349), config.rs (344), schema.rs (321), json_bridge.rs (252), error.rs (26)

---

## Summary

am-store is a single-file SQLite persistence layer for the DAE geometric memory engine. Overall, the code is thoughtfully constructed with solid WAL configuration, a defensive guard against data loss, and comprehensive test coverage. Several meaningful issues exist around dynamic SQL construction, schema versioning consistency, load-time N+1 query patterns, and error type coverage that are worth addressing before the system scales.

---

## 1. Schema Design (schema.rs)

### Table structure

Five tables: `metadata`, `episodes`, `neighborhoods`, `occurrences`, `conversation_buffer`.

The hierarchy `episode → neighborhood → occurrence` is normalized correctly. Foreign key constraints are declared and enforced (`PRAGMA foreign_keys = ON`). This is good — rusqlite disables FK enforcement by default.

### Type choices

| Column | SQLite type | Assessment |
|---|---|---|
| UUIDs (id fields) | TEXT | Correct. SQLite has no UUID type. |
| Quaternion components (w, x, y, z) | REAL (f64) | Correct. Tests confirm < 1e-10 round-trip drift. |
| `is_conscious` | INTEGER | Correct SQLite boolean idiom. |
| `timestamp` | TEXT with `DEFAULT ''` | Fragile (see below). |
| `phasor_theta` | REAL | Correct. |
| `epoch` | INTEGER | Correct. |
| `neighborhood_type` | TEXT | No CHECK constraint on allowed values. |

### Timestamp as empty string default

`timestamp TEXT NOT NULL DEFAULT ''` is a design smell. An empty string is not a valid ISO8601 value, but it is stored and compared in queries using string comparisons such as `e.timestamp = ''`. SQLite's `datetime()` comparisons only work reliably when timestamps are in `YYYY-MM-DD HH:MM:SS` form. The ISO8601 format used here (`2026-03-13T...Z`) requires the `REPLACE(REPLACE(..., 'T', ' '), 'Z', '')` transformation seen in the GC queries. A `NULL` default would be cleaner and more idiomatic for an optional value, though the current approach works correctly.

### Indexes

Three indexes exist:
- `idx_occ_word ON occurrences(word)` — covers word-based lookups
- `idx_occ_neighborhood ON occurrences(neighborhood_id)` — covers neighborhood load
- `idx_nbhd_episode ON neighborhoods(episode_id)` — covers episode load

Missing indexes:
- `episodes(is_conscious)` — filtered in multiple queries (`WHERE e.is_conscious = 0 / 1`). As the episodes table grows, every GC pass and `list_conscious_neighborhoods` call does a full table scan.
- `neighborhoods(episode_id, epoch)` — the composite eviction scoring query in `gc_to_target_size` joins neighborhoods to occurrences with an epoch filter. A composite index would help under large data sets.
- `occurrences(activation_count)` — `gc_pass` deletes `WHERE activation_count <= ?`. On large occurrence sets this is an unindexed range scan.

### No CHECK constraints

`neighborhood_type` accepts any TEXT value. A `CHECK(neighborhood_type IN ('memory', 'decision', ...))` would catch application-level bugs at the database boundary.

---

## 2. store.rs: Responsibilities

At 1596 LOC, `Store` carries six distinct concerns:

1. Connection lifecycle (`open`, `open_in_memory`, `conn`, `health_check`, `checkpoint_truncate`)
2. Full system serialization (`save_system`, `load_system` and their private helpers)
3. Targeted mutations (`increment_activation`, `mark_superseded`, `save_occurrence_positions`)
4. Conversation buffer (`append_buffer`, `drain_buffer`, `buffer_count`)
5. Inspection queries (`list_episodes`, `list_neighborhoods`, `top_words`, etc.)
6. Garbage collection (`gc_pass`, `gc_to_target_size`)

The GC methods alone (lines 654–882) are 230 LOC containing non-trivial SQL and eviction logic. Splitting into a `GcStore` trait or separate `gc.rs` module would improve navigability and testability without changing the public API. The conversation buffer is also a distinct concern that could live in `buffer.rs`.

That said, the struct boundary is clean: `Store` wraps a single `Connection` and all state is in SQLite. There is no hidden mutable state or reference counting complexity. This is not harmful at current scale but will become friction as the codebase grows.

---

## 3. Transaction Management

### What is transactional

| Operation | Transaction |
|---|---|
| `save_system` | Yes — wraps all DELETEs and INSERTs in one `unchecked_transaction` |
| `save_occurrence_positions` | Yes |
| `gc_pass` | Yes — DELETE cascade is atomic |
| `gc_to_target_size` | Yes |
| `forget_episode` | Yes |
| `forget_conscious` | Yes |
| `forget_term` | Yes |
| `backfill_empty_timestamps` | Yes |

### What is NOT transactional

- `append_buffer` + subsequent `COUNT(*)` — two separate autocommit statements. The count can be stale if another writer interleaves, though the single-connection model makes this low risk in practice.
- `drain_buffer` — `SELECT` then `DELETE` are two separate autocommit statements. If the process dies between them, the buffer is lost but not re-processed. This is an at-most-once delivery guarantee. Whether that is acceptable depends on the caller's semantics.
- `increment_activation` — single-statement, effectively atomic in SQLite's default isolation.

### `unchecked_transaction`

All transactions use `conn.unchecked_transaction()`. This is rusqlite's way of starting a transaction on a `&Connection` (not `&mut Connection`). It is safe in a single-threaded context. Since `Store` wraps a single `Connection` without interior mutability or `Arc`, concurrent access is a compile error — this is correct.

### ACID guarantees

WAL mode + `foreign_keys = ON` + explicit transactions on all multi-step writes provides strong durability. The `busy_timeout = 5000ms` prevents immediate failure under concurrent file access (e.g., two processes using the same `brain.db`). There is no process-level locking beyond SQLite's own, so two processes opening the same DB concurrently will serialize writes via WAL write lock — correct behavior.

---

## 4. Dynamic SQL Construction (SQL Injection Risk)

Two locations construct SQL strings via `format!`:

### `gc_pass` (lines 676–698)

```rust
retention_clauses.push_str(&format!(
    "\n                     AND n.epoch < {epoch_floor}"
));
retention_clauses.push_str(&format!(
    "\n                     AND (e.timestamp = ''
          OR REPLACE(REPLACE(e.timestamp, 'T', ' '), 'Z', '')
             < datetime('now', '-{retention_secs} seconds'))"
));
```

`epoch_floor` and `retention_secs` are both `u64` values computed from config (not user input). Rust's type system ensures these are numeric. No injection risk in practice, but dynamic SQL construction is a category of risk that should be noted.

### `gc_to_target_size` (lines 794–801)

```rust
let query = format!(
    "SELECT o.id, o.activation_count FROM occurrences o ...
     ORDER BY (o.activation_count - (CAST(n.epoch AS REAL) / {max_epoch_f}) * {w}) ASC",
    w = retention.recency_weight,
);
```

`max_epoch_f` is `f64` derived from a `MAX(epoch)` query. `w` (`recency_weight`) is an `f64` from config. Both are numeric and not user-controlled at runtime. Still, formatting floats directly into SQL produces strings like `1.5e2` or `inf` on edge cases. If `recency_weight` were ever `f64::INFINITY` or `f64::NAN`, the resulting SQL would be syntactically invalid (`... * inf ASC`). SQLite would return an error rather than silently corrupt data, but the error message would be opaque.

**Recommendation:** Both queries could be rewritten with bound parameters and SQLite expressions to eliminate the dynamic construction. The epoch filter `AND n.epoch < ?` accepts a parameter directly. The ORDER BY expression can use bound parameters for the recency weight.

---

## 5. Schema Versioning and Migration Strategy

### The version mismatch

`SCHEMA_VERSION` constant is `5`, but `get_schema_version` is documented (and used) with the value `5`. The constant stored in the database is also `5`. No inconsistency here. However, note that `SCHEMA_VERSION` appears as `5` in the constant but the docstring on `initialize` says "version 5" while tests reference `Some(SCHEMA_VERSION)`. This is self-consistent.

### Migration approach: column probe + ALTER TABLE

Instead of a formal migration table with versioned UP/DOWN scripts, the code uses column existence probes:

```rust
if conn.prepare("SELECT neighborhood_type FROM neighborhoods LIMIT 0").is_err() {
    conn.execute_batch("ALTER TABLE neighborhoods ADD COLUMN ...")?;
}
```

This approach works for additive migrations (ADD COLUMN) only. It cannot handle:
- Column renames
- Column type changes
- Table renames or drops
- Index additions that should be applied once
- Multi-step data transformations

The current schema has grown from roughly version 1 to 5 using only ADD COLUMN migrations plus the `backfill_empty_timestamps` one-time data fix. This is fine for the current trajectory, but the lack of a `schema_versions` migration log means it is impossible to know which migrations have already been applied to a given database without re-probing columns.

### `backfill_empty_timestamps` runs on every startup

The function early-returns when no empty timestamps exist, so the cost is one `COUNT(*)` query per startup. Not harmful, but it is an implicit migration that runs indefinitely rather than being gated on schema version.

### The `SCHEMA_VERSION` is written but never read to gate migrations

`initialize` writes `schema_version = 5` at the end, and `get_schema_version` reads it, but nothing in `initialize` reads the stored version before deciding which migrations to run. All migrations re-probe columns on every call. This is idempotent but wasteful on large databases.

---

## 6. N+1 Query Pattern in `load_system`

`load_system` loads all episodes, then for each episode calls `load_neighborhoods`, which for each neighborhood calls `load_occurrences`. This is a classic 3-level N+1:

```
1 query: SELECT all episodes
N queries: SELECT neighborhoods WHERE episode_id = ?   (one per episode)
N*M queries: SELECT occurrences WHERE neighborhood_id = ?  (one per neighborhood)
```

For a database with 50 episodes averaging 10 neighborhoods each, `load_system` issues 1 + 50 + 500 = 551 queries. At 100 episodes / 20 neighborhoods each: 1 + 100 + 2000 = 2101 queries.

Each query is a prepared statement, but the round-trip overhead and SQLite's per-statement overhead accumulate. A single JOIN query loading all three levels at once would replace this with 1 query at the cost of some in-Rust assembly of the nested structure.

The targeted update methods (`increment_activation`, `mark_superseded`, `save_occurrence_positions`) exist precisely to avoid full `load_system`/`save_system` round-trips for hot-path operations, which mitigates the impact. However, any caller that needs the full system in memory pays the N+1 cost.

---

## 7. The Conversation Buffer

`drain_buffer` is a non-atomic read-then-delete pair:

```rust
let rows = stmt.query_map(...)?.collect(...)?;
self.conn.execute_batch("DELETE FROM conversation_buffer")?;
```

If the process crashes between the SELECT and the DELETE, the buffer entries are silently lost. If the caller processes the returned rows and then crashes before completing, the entries are also gone. This is at-most-once semantics.

Wrapping both in a single transaction would not change the crash behavior (the transaction commits on `tx.commit()`, which happens before the caller processes the rows), but it would at least ensure the SELECT and DELETE are consistent with each other.

A safer pattern: read, process, then delete by ID rather than truncating the whole table. This gives at-least-once semantics if combined with idempotent processing.

---

## 8. `save_system` Full Replace Semantics

`save_system` issues `DELETE FROM occurrences; DELETE FROM neighborhoods; DELETE FROM episodes;` then re-inserts everything. This is a full replace, not an upsert. Implications:

1. **Write amplification:** every call rewrites the entire dataset regardless of what changed. For a 45MB database, every `save_system` call rewrites ~45MB of data.
2. **WAL growth:** the passive checkpoint after bulk writes flushes the WAL, but the WAL can grow to the full database size during the transaction.
3. **Fragmentation:** repeated delete-all + insert-all cycles cause significant page fragmentation, which is why VACUUM is called after GC. Consider periodic VACUUM scheduling rather than only after GC.

The targeted update methods (`increment_activation`, `mark_superseded`, `save_occurrence_positions`) exist to avoid `save_system` on hot paths. The GC tests confirm that `gc_pass` + `gc_to_target_size` are also targeted. The primary caller of `save_system` should be ingest/import operations.

---

## 9. Error Types (error.rs)

`StoreError` has two variants:
- `Sqlite(rusqlite::Error)` — wraps all SQLite/rusqlite errors
- `InvalidData(String)` — covers UUID parse failures, empty-system guard, JSON errors, path errors

Missing coverage:
- **I/O errors** for file operations in `json_bridge.rs` and `project.rs` are mapped to `InvalidData(format!(...))`. This loses the distinction between "file not found" and "permission denied" and "disk full". A dedicated `Io(std::io::Error)` variant would allow callers to handle I/O failures distinctly.
- **Migration errors** — `migrate_old_layout` in project.rs uses `tracing::warn!` and silently continues on errors rather than propagating them. A failed migration is treated as non-fatal, which is defensible (brain.db is opened fresh) but means a corrupt merge is not surfaced to the caller.
- No `std::error::Error` source chain — `StoreError` does not implement `source()`, so the underlying `rusqlite::Error` or parse error is not accessible via the standard error chain API. Adding `#[source]` support would improve debuggability in callers that use `anyhow` or similar.

---

## 10. Connection Model

Single `Connection` per `Store`. No connection pooling. This is correct for SQLite, which is not designed for multi-reader connection pools in the same process. WAL mode allows concurrent readers from different processes, but the in-process model is correctly single-connection.

`Store` is not `Send` or `Sync` (rusqlite `Connection` is `!Send`). This enforces single-thread access at compile time, eliminating data races entirely.

The `conn()` public accessor (`pub fn conn(&self) -> &Connection`) leaks the raw connection to callers. This allows callers to bypass the `Store` abstraction and issue arbitrary queries or transactions. Consider whether this accessor is necessary or can be removed.

---

## 11. SQLite Pragmas

| Pragma | Value | Assessment |
|---|---|---|
| `journal_mode` | WAL | Correct for concurrent read access |
| `foreign_keys` | ON | Correct — rusqlite default is OFF |
| `busy_timeout` | 5000ms | Reasonable — prevents immediate failure under contention |
| `wal_autocheckpoint` | 100 pages (~400KB) | Conservative — keeps WAL small at cost of more frequent checkpoints |
| `synchronous` | not set (default: FULL) | Correct for durability; could consider NORMAL for write throughput at minor durability risk |
| `cache_size` | not set | Default 2000 pages (~8MB). For read-heavy workloads, increasing this could reduce I/O. |
| `temp_store` | not set | Default is file-based. Setting `MEMORY` would speed up GC sort operations. |
| `mmap_size` | not set | Memory-mapped I/O could improve read performance for large databases. |

---

## 12. project.rs: Project Isolation Model

There is no project isolation. The design has migrated from a multi-database `projects/*.db` layout to a single `brain.db`. The `migrate_old_layout` function handles the one-time upgrade.

`BrainStore` is a thin facade over `Store` that adds:
- Directory creation
- Migration on first open
- GC trigger on open

This is a deliberate architectural simplification: one brain, one file. The `Config.data_dir` is the only isolation mechanism — different `data_dir` values point to different `brain.db` files.

The `mark_salient` method on `BrainStore` mutates a `DAESystem` passed by mutable reference and immediately saves. This creates a tight coupling where the caller must hold the system in memory and pass it to `BrainStore` — the store does not own the in-memory system. This is consistent with the design but worth noting: there is no in-memory cache in the store layer. Every load is a full database read.

---

## 13. json_bridge.rs

The JSON bridge exists to support the v0.7.2 wire format used by the JavaScript reference implementation. It is a thin wrapper: `am_core::import_json` / `am_core::export_json` do the actual serialization; `json_bridge.rs` just adds file I/O and error mapping.

The file I/O errors (`fs::read_to_string`, `fs::write`) are mapped to `InvalidData` rather than a dedicated I/O variant — as noted in the error type section.

`export_json_file` writes atomically only if `fs::write` is atomic on the target filesystem, which it is not on all platforms. A write-to-temp-then-rename pattern would be safer for export files.

---

## 14. config.rs

Configuration is entirely file + environment based. Nothing is persisted to SQLite — the `metadata` table is used only for `agent_name` and `schema_version`, not for runtime config. This is a clean separation.

`gc_enabled` defaults to `false`. GC must be explicitly enabled, which is a safe default. The 50MB `db_size_mb` default is low for a growing memory engine but appropriate for a developer tool.

The config resolution order (CWD file → env var path file → global file → defaults, then env vars override) is well-documented and tested.

`expand_tilde` does a simple `~/` prefix strip. It does not handle `~username/` or bare `~` without a trailing slash. This is acceptable for a developer tool.

---

## Severity Summary

| Issue | Severity | File |
|---|---|---|
| Dynamic SQL construction with float interpolation in GC queries | Medium | store.rs:794–801 |
| N+1 query pattern in `load_system` | Medium | store.rs:233–277 |
| `drain_buffer` non-atomic read-delete | Low-Medium | store.rs:414–423 |
| Missing index on `episodes(is_conscious)` | Low-Medium | schema.rs |
| Missing index on `occurrences(activation_count)` | Low | schema.rs |
| `StoreError` missing `Io` variant | Low | error.rs |
| `pub fn conn()` leaks raw connection | Low | store.rs:78–80 |
| No CHECK constraint on `neighborhood_type` | Low | schema.rs |
| `export_json_file` not atomic (no temp+rename) | Low | json_bridge.rs |
| Schema migrations not gated by stored version | Low | schema.rs |
| `backfill_empty_timestamps` runs every startup | Cosmetic | schema.rs |
| `SCHEMA_VERSION` constant vs stored value (`5` vs stated "5") | Cosmetic | schema.rs |

---

## Appendix: File Paths

- `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-store/src/store.rs`
- `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-store/src/schema.rs`
- `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-store/src/config.rs`
- `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-store/src/project.rs`
- `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-store/src/json_bridge.rs`
- `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-store/src/error.rs`
