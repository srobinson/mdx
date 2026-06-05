---
title: Postgres Phase 1.b Store Boundary Contract Audit for littleorgans
type: research
tags: [littleorgans, postgres, persistence, audit, store-boundary]
summary: Final lock pass confirms tx, publishability, and Cargo routing are coherent, with one remaining focused test gate feature mismatch.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-06
updated: 2026-06-06
---

## Executive Summary

The Phase 1.b store boundary draft was audited against `main` at `d1e7754`. The latest live pass confirms that section 4 resolves the transaction defect with a single pool scoped `ImmediateTx` mechanism, sections 3, 5, and 7 consistently model empty default features with sqlite gated `AuditStore`, and section 8 now includes Cargo feature routing for internal consumers. One focused test gate mismatch remains: the `lilo-im-store` tests use sqlite gated audit store symbols, but the focused store test command still invokes that package without `--features sqlite`.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`
- Branch and commit: `main` at `d1e7754`
- Indexing: `.fmm.db` and `.fmmrc.toml` are present; fmm reported 391 indexed files and 57,748 LOC
- Primary stack: Rust workspace, Cargo, Moon, Just, sqlx
- Audit inputs:
  - Contract: `/Users/alphab/.mdx/projects/littleorgans-postgres-phase-1b-store-boundary-contract.md`
  - Parent plan: `/Users/alphab/.mdx/projects/littleorgans-postgres-persistence-plan.md`

## Architecture Context

The current persistence boundary still has SQLite implementation types in store internals. `lilo-db` owns transition helpers and exposes `ImmediateTx`, `begin_immediate_tx`, `finish_immediate_tx`, `begin_immediate_pool_tx`, and `finish_immediate_pool_tx` from `internal/db/src/transition.rs`.

The session spawn path currently opens one SQLite pool connection from `SqliteStore::pool()`, starts `BEGIN IMMEDIATE`, threads that borrowed connection across session store, runtime store, and identity audit, then commits or rolls back through the connection scoped helper. The runtime authorization path mirrors this for runtime spawn audit.

## Detailed Findings

### Final lock pass: transaction, default surface, and Cargo routing fixed; focused test gate mismatch remains

Live reread of the revised contract confirmed the transaction finding remains fixed:

- Section 4 states that spawn paths use exactly one mechanism: `ImmediateTx` begun by `begin_immediate_pool_tx` and committed by `finish_immediate_pool_tx`: contract lines 223 to 230.
- The disposition table says daemon paths stop calling `begin_immediate_tx` and `finish_immediate_tx` on `ImmediateTx`: contract lines 249 to 253.
- This matches the actual transition code: `ImmediateTx` owns `PoolConnection<Sqlite>` and `open: bool` at `internal/db/src/transition.rs:105-108`; `begin_immediate_pool_tx` begins once at lines 177 to 181; `finish_immediate_pool_tx` consumes the handle at lines 184 to 201; `ImmediateTx.drop` rolls back only if `open` remains true at lines 139 to 143.

The default published surface is now coherent:

- Section 3 says default features expose only `AuditSink`, `AuditRow`, and `AuditError`, with no concrete store type and no constructor: contract lines 125 to 140.
- Section 5 repeats that default features are empty, `AuditStore` is sqlite gated, and default consumers never see `AuditStore`, `lilo-db`, or SQLite types: contract lines 279 to 307.
- Section 7 accepts the same shape: `AuditStore` appears only with `--features sqlite` and is absent at default: contract lines 425 to 433.
- Section 8 aligns `crates/lilo-im-store/src/lib.rs` with default core re-exports and sqlite gated `AuditStore` re-exports: contract lines 471 to 474.

That Cargo routing gap is now fixed in the contract:

- Section 8 adds a required Cargo feature routing subsection for the four consumers: `internal/identity/service`, `internal/session/daemon`, `internal/session/app`, and `internal/runtime/daemon`: contract lines 467 to 484.
- The subsection includes root workspace dependency inheritance and a `cargo tree -e features -i lilo-im-store` verification command, while preserving the default `cargo build -p lilo-im-store` publishability check.

A smaller but still blocking gate mismatch remains. The acceptance command at contract lines 441 to 444 still runs `cargo nextest run -p lilo-im-store` without `--features sqlite`. The crate's integration tests currently import and exercise sqlite gated items: `AuditFilters`, `AuditTableColumn`, `SqliteAuditSink`, and `query_audit` at `crates/lilo-im-store/tests/audit.rs:10`, with uses at lines 17, 49, 74, 91, 137, 150 to 152, 228, 235, 248, and 254. Once `AuditStore` and query helpers are hidden at default, that focused package test gate compiles red unless the gate enables sqlite, for example with a separate `cargo nextest run -p lilo-im-store --features sqlite` plus the default surface build check.

### Blocking issue: section 4 has a transaction helper contradiction

The contract's target routing says the daemon should obtain `lilo_db::ImmediateTx` and finish it with `finish_immediate_pool_tx`:

- Contract section 4, lines 178 to 186: proposed helper uses `begin_immediate_pool_tx`, `begin_spawn_tx` returns `ImmediateTx`, and commit goes through `finish_immediate_pool_tx`.

The later disposition table contradicts that by saying daemons keep using the connection scoped helpers through `&mut *immediate_tx`:

- Contract section 4, lines 237 to 242: `begin_immediate_tx` and `finish_immediate_tx` stay, with daemons using them via `&mut *immediate_tx`.

That is unsafe for the actual code model:

- `ImmediateTx` owns `PoolConnection<Sqlite>` and tracks transaction state with `open: bool`: `internal/db/src/transition.rs:104-108`.
- `begin_immediate_pool_tx` already acquires the connection, executes `BEGIN IMMEDIATE`, and returns `ImmediateTx { open: true }`: `internal/db/src/transition.rs:176-181`.
- `finish_immediate_pool_tx` consumes `ImmediateTx` and flips `open` false through `commit()` or `rollback()`: `internal/db/src/transition.rs:110-121` and `184-201`.
- `finish_immediate_tx` commits a borrowed `SqliteConnection` but cannot flip `ImmediateTx.open`: `internal/db/src/transition.rs:155-174`.
- `Drop` rolls back when `open` remains true: `internal/db/src/transition.rs:138-143`.

If a caller follows the table literally, it either calls `begin_immediate_tx(&mut *tx, ...)` after `begin_immediate_pool_tx`, which attempts a nested `BEGIN IMMEDIATE`, or it commits with `finish_immediate_tx(&mut *tx, ...)` and leaves `ImmediateTx.open` true for `Drop`. The contract should pick one model: pool scoped `ImmediateTx` is begun once and finished once by `finish_immediate_pool_tx`; connection scoped helpers remain only for legacy call sites that still own a raw borrowed `SqliteConnection`.

### Survey accuracy checks passed

Commands run against `main`:

```bash
rg -n "SqlitePool|SqliteConnection|sqlx::Sqlite|PoolConnection<Sqlite>" \
  internal/session internal/runtime internal/identity crates/lilo-im-store
```

Result: 52 hits, matching contract appendix lines 498 to 500.

Gate 1 command from contract section 7 returned exactly 8 hits:

- `internal/identity/service/src/client.rs:9,65`
- `crates/lilo-im-store/src/lib.rs:10,15`
- `internal/session/daemon/src/identity_client.rs:10,24,55`
- `internal/session/daemon/src/handler/spawn.rs:343`

These match contract lines 504 to 510.

The extended audit with bare `\bSqlite\b` returned 82 hits. The additional production file outside the literal set was `internal/session/store/src/sqlite/events.rs`, consistent with the contract's blind spot note at lines 374 to 390.

### Existing neutral identity core claim passed

`lilo-im-core` is sqlx free:

```bash
rg -n "sqlx|Sqlite|PgPool|PoolConnection" crates/lilo-im-core
```

Result: zero hits.

The neutral audit contract exists:

- `AuditRow`: `crates/lilo-im-core/src/audit.rs:40-52`
- `AuditSink`: `crates/lilo-im-core/src/audit.rs:83-88`
- `AuditError` export: `crates/lilo-im-core/src/lib.rs:11`
- `AuditError` definition: `crates/lilo-im-core/src/error.rs:31`

Minor wording note: the contract calls `AuditSink/AuditRow/AuditError` a trait family at line 126. Only `AuditSink` is a trait. The claim remains architecturally correct.

### Existing ImmediateTx claim passed

`lilo-db::ImmediateTx` exists and derefs to `SqliteConnection`:

- `ImmediateTx` struct: `internal/db/src/transition.rs:104-108`
- `Deref<Target = SqliteConnection>`: `internal/db/src/transition.rs:124-130`
- `DerefMut`: `internal/db/src/transition.rs:132-136`
- Re-export from `lilo-db`: `internal/db/src/lib.rs:26`

### Cross component method inventory matched the contract

The seven cross component store methods named in the contract are real and currently take `&mut SqliteConnection`:

- Session store:
  - `insert_pending_spawn_intent_in`: `internal/session/store/src/sqlite/spawn_intents.rs:208-214`
  - `resolve_spawn_intent_in`: `internal/session/store/src/sqlite/spawn_intents.rs:227-233`
  - `abort_spawn_intent_in`: `internal/session/store/src/sqlite/spawn_intents.rs:251-258`
  - `insert_session_in`: `internal/session/store/src/sqlite/sessions.rs:51-60`
- Runtime store:
  - `insert_forking_in`: `internal/runtime/store/src/sqlite/lifecycle.rs:73-82`
  - `update_lifecycle_in`: `internal/runtime/store/src/sqlite/lifecycle.rs:88-94`
  - `delete_in`: `internal/runtime/store/src/sqlite/lifecycle.rs:105-116`

The session daemon calls them from `internal/session/daemon/src/handler/spawn.rs:123-138`, `175-191`, and `251-263`.

### Publishability checks passed for current claims

`lilo-im-store` is publishable because it lacks `publish = false`, while the internal crates are explicitly private:

- `crates/lilo-im-store/Cargo.toml:1-17`
- `internal/db/Cargo.toml:11`
- `internal/identity/service/Cargo.toml:11`
- `internal/runtime/store/Cargo.toml:10`
- `internal/session/store/Cargo.toml:10`

`lilo-im-store` currently does not depend on `lilo-db`:

```bash
rg -n "lilo-db|lilo_db" crates/lilo-im-store
```

Result: zero hits.

Open design caution: the draft should make the default feature shape explicit. If `AuditStore` is only the SQLite concrete type behind `feature = "sqlite"`, a default feature build exposes only the trait and helper types, not a usable concrete audit store. If that is intended for Phase 1.b, say so directly. If default builds must expose a usable `AuditStore`, the contract needs a concrete backend neutral constructor that does not require a Phase 2 Postgres body.

## Dependencies

Critical dependencies in the audited surface:

- `sqlx`: current transition SQLite implementation and future Postgres boundary.
- `lilo-db`: internal database boundary and transition transaction helpers.
- `lilo-im-core`: published sqlx free identity and audit core API.
- `lilo-im-store`: published audit storage crate requiring careful feature gating.
- `lilo-session-store` and `lilo-runtime-store`: internal store crates whose cross component transaction signatures must stop naming SQLite.

## Relevance to Helioy

The finding protects the atomic seam between session intent, runtime lifecycle, and identity audit. The migration should not trade a naming cleanup for transaction ambiguity. Keep the invariant simple: one begin owner and one finish owner for the shared transaction handle.

## Open Questions

- Should the focused `lilo-im-store` acceptance command become a separate sqlite feature test command, or should only specific sqlite backend tests be gated?
- Should the default surface check use `cargo build -p lilo-im-store` plus a public API check before the sqlite feature test to prove both surfaces independently?
