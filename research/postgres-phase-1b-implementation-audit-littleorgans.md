---
title: Postgres Phase 1.b Implementation Audit for littleorgans
type: research
tags: [littleorgans, postgres, persistence, implementation-audit, store-boundary]
summary: Phase 1.b implementation passes workspace and boundary gates; the driver and integration edits are mechanical rename follows under the corrected scope caveat.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-06
updated: 2026-06-06
---

## Executive Summary

The `feat/postgres-phase-1b` branch was audited against `main` and the Phase 1.b contract. Core behavior gates passed: workspace nextest was 719 passed, 0 failed, Gate 1 was zero, the default `lilo-im-store` surface has no sqlx dependency, and the spawn authorization transaction now uses a single pool scoped `ImmediateTx`. After the contract §2 reconciliation caveat was corrected, the driver and integration test edits are clean mechanical rename and signature follows, with no semantic Phase 3 or Phase 5 migration found.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`
- Branch: `feat/postgres-phase-1b`
- Head: `055e5d5`
- Base: `main`
- Contract: `/Users/alphab/.mdx/projects/littleorgans-postgres-phase-1b-store-boundary-contract.md`
- Indexing: fmm index present and used; branch shows 391 indexed files and 57,797 LOC

## Architecture

Phase 1.b neutralizes SQLite naming at exported and cross component store boundaries while leaving SQLite SQL bodies private and transitional. `lilo-im-store` now has empty default features and gates its concrete SQLite `AuditStore` behind `feature = "sqlite"`. Session and runtime spawn authorization share `lilo_db::ImmediateTx`, a pool owned transaction handle, across session store, runtime store, and identity audit calls.

## Detailed Findings

### Scope caveat revalidation is clean

The corrected contract §2 lines 69-82 defers semantic CLI, doctor, admin, driver, and integration migration, while explicitly allowing rename and signature follows required by no compatibility aliases and full workspace compilation. Rechecking the three previously flagged files with `git diff --unified=0 main...feat/postgres-phase-1b` found only these mechanical edits:

- `internal/session/driver/tests/port_conformance.rs:319`: `LifecycleStore::open(db)` changed to `LifecycleStore::from_db(db)`.
- `tests/integration/tests/session_spawn_contract.rs:13`: connection scoped helper imports changed to pool scoped helper imports.
- `tests/integration/tests/session_spawn_contract.rs:20`: `SqliteStore` import changed to `SessionStore`.
- `tests/integration/tests/session_spawn_contract.rs:56`, `:122-123`, `:196`, and `:229-230`: store constructors changed from `SqliteStore::open` or `LifecycleStore::open` to `SessionStore::from_db` or `LifecycleStore::from_db`.
- `tests/integration/tests/session_spawn_contract.rs:132-150` and `:160-174`: manual integration transactions changed from `session_pool().acquire()` plus `begin_immediate_tx` and `finish_immediate_tx` to `begin_immediate_pool_tx` and `finish_immediate_pool_tx`.
- `tests/integration/tests/shutdown_contract.rs:16`, `:153`, `:167`, and `:206`: `SqliteStore` and `LifecycleStore::open` calls changed to the neutral names.

A changed line scan for Postgres terms, schema terms, SQL literals, assertions, context strings, and bails returned zero hits. No SQL dialect change, test assertion change, Postgres path, doctor change, admin change, or behavior migration was found in those files. The earlier scope issue is superseded by the corrected §2 caveat.

### Workspace and focused gates passed

Commands run during the implementation audit:

```bash
cargo nextest run --workspace --no-fail-fast
```

Result: 719 tests run, 719 passed, 4 skipped, 0 failed.

```bash
cargo nextest run -p lilo-session-store -p lilo-runtime-store -p lilo-im-store
```

Result: 37 tests run, 37 passed, 0 skipped. This focused command does not run the two sqlite gated `lilo-im-store` tests because the package default surface is backend free. The full workspace run did execute and pass those tests through feature unification.

```bash
cargo nextest run -p lilo-im-store --features sqlite
```

Result: 2 tests run, 2 passed.

### Boundary gates passed with expected gated residue

Gate 1 command returned zero hits.

Gate 2 regexes return only `crates/lilo-im-store/src/sqlite/audit.rs:56` and `:92-93`, which are under the feature gated sqlite module path. This matches the contract's allowed residue.

Extended `\bSqlite\b` residue was 64 hits, all under private sqlite modules or test files:

- `crates/lilo-im-store/src/sqlite/audit.rs`
- `crates/lilo-im-store/tests/audit.rs`
- `internal/runtime/store/src/sqlite/lifecycle.rs`
- `internal/session/store/src/sqlite*.rs`
- `internal/runtime/app/tests/integration_pass7.rs`
- `internal/runtime/daemon/src/handler/tests.rs`
- `internal/session/app/tests/cli_get_test/run_resolution.rs`

### `lilo-im-store` publishability checks passed

- `cargo build -p lilo-im-store` passed with default features.
- `cargo tree -p lilo-im-store --no-default-features | rg sqlx` returned no sqlx dependency.
- `cargo tree -p lilo-im-store --features sqlite | rg sqlx` showed sqlx only under the sqlite feature.
- `crates/lilo-im-store/Cargo.toml:25` makes `sqlx` optional.
- `crates/lilo-im-store/src/lib.rs:18-24` gates the sqlite module and concrete `AuditStore` re-export behind `feature = "sqlite"`.
- `rg "lilo-db|lilo_db" crates/lilo-im-store` finds only documentation text, no Cargo dependency or code import.
- Four internal consumers enable `features = ["sqlite"]`: `internal/identity/service/Cargo.toml:21`, `internal/session/daemon/Cargo.toml:26`, `internal/session/app/Cargo.toml:55`, and `internal/runtime/daemon/Cargo.toml:41`.

### Single transaction mechanism is real

`ImmediateTx` owns a `PoolConnection<Sqlite>` and tracks open state in `internal/db/src/transition.rs:105-108`. `begin_immediate_pool_tx` begins once and returns `ImmediateTx` at `internal/db/src/transition.rs:177-181`. `finish_immediate_pool_tx` consumes the handle at `internal/db/src/transition.rs:184-201`; `ImmediateTx.drop` rolls back only if `open` remains true at `internal/db/src/transition.rs:139-143`.

Session spawn now uses that handle consistently:

- `internal/session/store/src/sqlite.rs:49-50`: `SessionStore::begin_immediate_tx` delegates to `begin_immediate_pool_tx`.
- `internal/session/daemon/src/handler/spawn.rs:103-135`: Tx A threads `&mut tx` through identity audit, pending intent insert, and runtime lifecycle insert, then finishes with `finish_immediate_pool_tx`.
- `internal/session/daemon/src/handler/spawn.rs:166-185`: Tx B threads `&mut tx` through session insert, lifecycle update, and intent resolve, then finishes with `finish_immediate_pool_tx`.
- `internal/session/daemon/src/handler/spawn.rs:239-254`: abort path threads `&mut tx` through intent abort and lifecycle delete, then finishes with `finish_immediate_pool_tx`.
- `rg` found no production import or call of the old connection scoped `begin_immediate_tx` or `finish_immediate_tx` across session, runtime, identity, integration, or im-store paths.

Runtime spawn audit also uses the same pool scoped mechanism:

- `internal/runtime/store/src/sqlite/lifecycle.rs:72-74`: `LifecycleStore::begin_immediate_tx` delegates to `begin_immediate_pool_tx`.
- `internal/runtime/daemon/src/identity.rs:41-59`: runtime spawn authorization starts one `ImmediateTx`, calls `authorize_in_tx`, then finishes with `finish_immediate_pool_tx`.

### Wiring decisions are behavior preserving

`DaemonState` now owns a `LifecycleStore` field built from the same `&LiloDb` that builds the session store: `internal/session/daemon/src/handler/state.rs:17-29` and `:42-60`. `LifecycleStore` is cloneable around a shared `SqlitePool`, so this is a second handle to the same pool rather than a second database or split ownership. The spawn path still writes through the shared `ImmediateTx`, not through independent transactions.

`ServerState::new` is async and test scoped, building identity from `config.store.db_path` before delegating to `new_with_identity`: `internal/runtime/daemon/src/server/state.rs:51-58`. Production bootstrap uses explicit identity wiring through `new_with_identity`, so this is test wiring to avoid a now private store pool. No behavior change was found beyond test construction.

### Scope fence otherwise held

No Phase 2 SQL dialect migration was found. Diff scans showed no substantive additions of Postgres placeholders, `timestamptz`, `bytea`, JSONB, owner columns, `ON CONFLICT`, `sqlite_master`, or schema rewrites. The only `postgres` additions were docs comments about the future Phase 2 feature.

`crates/lilo/src/cli/doctor.rs` and `crates/lilo-rm-core/src/admin.rs` were untouched.

## Dependencies

- `lilo-db`: owns `ImmediateTx` and transition transaction helpers.
- `lilo-im-core`: owns sqlx free `AuditSink`, `AuditRow`, and `AuditError`.
- `lilo-im-store`: exposes sqlx free defaults and feature gated sqlite `AuditStore`.
- `lilo-session-store` and `lilo-runtime-store`: now use neutral public store names and `ImmediateTx` in shared transaction methods.

## Relevance to Helioy

The branch preserves the atomic session intent plus identity audit seam while removing SQLite types from cross component signatures. The corrected scope caveat is the right reviewer contract: semantic migrations stay deferred, and compile required rename follows are accepted.

## Open Questions

None for Phase 1.b verification. The implementation is clean against the corrected contract.
