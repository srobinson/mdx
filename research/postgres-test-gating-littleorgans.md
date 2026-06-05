---
title: Postgres Test Gating and Migration Quarantine Audit for littleorgans
type: research
tags: [littleorgans, postgres, sqlite, lilo-db, nextest, ci, audit]
summary: Audited Phase 1.a Postgres test gating through commit a65f7e2 and confirmed the SQLite migration quarantine keeps the workspace green while Postgres tests run opt in.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-06
updated: 2026-06-06
---

## Executive Summary

The `feat/postgres-phase-1a` work now has honest Postgres test gating and a safe SQLite transition path. Commit `a65f7e2` quarantines the original SQLite migration into `internal/db/migrations-sqlite`, keeps the Postgres target in `internal/db/migrations`, and restores the full workspace suite without migrating daemon, stores, or doctor to Postgres early.

## Project Metadata

- Language: Rust 2024 workspace.
- Build and test system: Cargo, cargo-nextest, Moon CI, GitHub Actions, Just.
- Relevant crates: `lilo-db`, `lilo-paths`, `lilo`, `lilo-session-app`, `lilo-session-store`, `lilo-runtime-daemon`, `lilo-runtime-store`.
- Branch: `feat/postgres-phase-1a`.
- Audited commits: `e4a451a`, `c2797b5`, `a5ed0fe`, `57a6aae`, `a65f7e2`.
- fmm state: indexed and valid, 391 files checked by `fmm validate`.

## Architecture

`lilo-db` currently has two database paths by design:

- Postgres target path: `internal/db/src/lib.rs:64-85` defines `LiloDb::open_postgres`, and `internal/db/src/lib.rs:135-137` defines `migrator()` with `sqlx::migrate!("./migrations")`.
- SQLite transition path: `internal/db/src/transition.rs:36-38` defines `sqlite_migrator()` with `sqlx::migrate!("./migrations-sqlite")`, and `internal/db/src/transition.rs:43-72` makes `LiloDb::open/open_path` run that migrator.

The live daemon and stores remain on the SQLite transition surface. `internal/session/app/src/compose.rs:73-153` opens the composed daemon database through `LiloDb::open(&paths)` at line 80. `internal/session/store/src/sqlite.rs:30-34` uses `db.session_pool()`, and `internal/runtime/store/src/sqlite/lifecycle.rs:57-60` uses `db.runtime_pool()`. Doctor also stays SQLite: `crates/lilo/src/cli/doctor.rs:207-217` calls `LiloDb::open(paths)`, and `crates/lilo/src/cli/doctor.rs:250-270` reads SQLite PRAGMAs.

CI and local database execution remain explicit. `.github/workflows/pr.yml` provisions `postgres:17` and runs the ignored `lilo-db` Postgres tests, while `justfile:74-80` exposes `just test-db` for local opt in execution.

## Key Patterns

- Hidden test skips are not acceptable. The rejected guard returned `Ok(())`, which nextest counted as passing tests.
- Ignored DB tests are acceptable only when default package execution still runs real DB free tests and exits 0.
- Shared migration directories cannot span dialects during a live transition. `a65f7e2` makes the dialect boundary explicit with two SQLx migrators and two migration directories.
- Scope fencing is source verifiable: production callers still enter through `LiloDb::open/open_path`; only `lilo-db` tests and `internal/db/src/test_support.rs` call `open_postgres`.

## Detailed Findings

### Finding 1, e4a451a: early return guard was still masked

The no database command was green, but not loud:

- Command: `env -u LILO_DATABASE_URL -u LILO_TEST_DATABASE_URL cargo nextest run -p lilo-db`.
- Observed result: 4 tests passed, 0 skipped.
- Observed output contained no `SKIP` line or database guidance.
- Source: the former `internal/db/src/lib.rs:199-208` guard printed guidance through `eprintln!`, and the tests early returned `Ok(())`.

This contradicted the claim that the bare no database command skipped green with a loud notice. It could mask a permanently non executing DB test path in local nextest output.

### Finding 2, a5ed0fe: ignored tests were honest, but package default exited 4

Commit `a5ed0fe` fixed the masking shape by using real ignored tests, but the package default command still failed:

- `env -u LILO_DATABASE_URL -u LILO_TEST_DATABASE_URL cargo nextest run -p lilo-db` reported `0 tests run: 0 passed, 4 skipped`, then exited 4 with `error: no tests to run`.
- `env -u LILO_DATABASE_URL -u LILO_TEST_DATABASE_URL cargo nextest run -p lilo-db --run-ignored all` failed loud with the fixture guidance from `internal/db/src/test_support.rs:128-131`.
- With a random port `postgres:17` and `LILO_TEST_DATABASE_URL=postgres://lilo:lilo@localhost:<port>/lilo`, `cargo nextest run -p lilo-db --run-ignored all` passed 4/4.
- `just check` passed.

The bus finding was that `internal/db/src/lib.rs:196` made the skip honest, but the exact package default command was not a green skip because nextest returned no tests exit status 4.

### Finding 3, 57a6aae: local `lilo-db` package gating became honest

Commit `57a6aae` resolved the no tests issue by adding real DB free tests, not by suppressing nextest behavior.

Verified live:

- `internal/db/src/config.rs:60-102` covers `DbConfig::from_url`, env over settings precedence, and settings fallback.
- `internal/db/src/test_support.rs:184-242` covers `swap_database`, `database_name_of`, and unique test DB name behavior.
- `rg` found no `--no-tests`, `no-tests`, `postgres_configured`, or old skip guard in `.github`, `justfile`, or `internal/db`.
- `env -u LILO_DATABASE_URL -u LILO_TEST_DATABASE_URL -u LILO_HOME cargo nextest run -p lilo-db` exited 0 with 11 passed and 4 skipped.
- `env -u LILO_DATABASE_URL -u LILO_TEST_DATABASE_URL -u LILO_HOME cargo nextest run -p lilo-db --run-ignored all` failed loud with the expected fixture guidance.
- With a random port `postgres:17` and `LILO_TEST_DATABASE_URL=postgres://lilo:lilo@localhost:<port>/lilo`, `cargo nextest run -p lilo-db --run-ignored all` passed 15/15.
- `just check` passed, including clippy with `-D warnings`.
- `fmm validate` passed.

Bus verdict sent: `CLEAN: finding resolved, branch sound`.

### Final pass, a65f7e2: SQLite quarantine is sound

Commit `a65f7e2` corrects the wider blast radius missed in the earlier package scoped review. The prior single migration directory flip made every SQLite transition caller run Postgres SQL. The fix uses the contract quarantine option.

Verified source findings:

- `diff -u <(git show 6c267da:internal/db/migrations/0001_unified_schema.sql) internal/db/migrations-sqlite/0001_unified_schema.sql` produced no diff, so the quarantined SQLite schema is faithful to the branch base.
- `internal/db/migrations-sqlite/0001_unified_schema.sql:47-48` keeps the original SQLite default namespace seed with `strftime(...)`.
- `internal/db/migrations/0001_unified_schema.sql:47-48` keeps the Postgres target seed with `to_char(now() AT TIME ZONE 'UTC', ...)`.
- `internal/db/src/transition.rs:36-38` defines the SQLite migrator against `./migrations-sqlite`.
- `internal/db/src/transition.rs:43-72` makes `LiloDb::open/open_path` run `sqlite_migrator()`.
- `internal/db/src/lib.rs:135-137` keeps the Postgres migrator against `./migrations`.
- `internal/db/src/lib.rs:64-85` makes `LiloDb::open_postgres` run the Postgres migrator.
- `rg "migrate!|migrations-sqlite|migrations" internal/db crates internal --glob '*.rs'` found only the two intended migration macro call sites plus comments.
- `rg "open_postgres|DbConfig::resolve|LiloDb::open\(|open_path\(" crates internal tests --glob '*.rs'` showed production daemon, store, doctor, and app paths using `LiloDb::open/open_path`; `open_postgres` appears only in `internal/db` test support and tests.

Verified behavior:

- `fmm validate`: passed, 391 files indexed and current.
- `env -u LILO_DATABASE_URL -u LILO_TEST_DATABASE_URL -u LILO_HOME cargo nextest run --workspace`: exit 0, 719 passed, 4 skipped, 0 failed. Nextest also reported 2 leaky tests, but no failures.
- Random port `postgres:17` plus `LILO_TEST_DATABASE_URL=postgres://lilo:lilo@127.0.0.1:<port>/lilo just test-db`: exit 0, 15 passed, 0 skipped.
- `just check`: exit 0, including `cargo fmt --all`, workspace clippy, `cargo fmt --check`, LOC, provenance, seam, and env gate.
- Working tree remained clean after verification.

Bus verdict sent: `CLEAN: workspace 0-failed, quarantine sound`.

## Dependencies

- `sqlx::migrate!`: compile time migration embedding for both dialect directories.
- `cargo-nextest`: local and CI test runner. Its output capture and no tests exit behavior were central to the findings.
- `postgres:17`: CI service image and local opt in test database.
- `lilo-paths::Settings`: config loader used by the fixture resolver.
- `tempfile`: `lilo-db` dev dependency for DB free config tests.

## Relevance to Helioy

This audit shows why gates must cover both the narrow target crate and the full workspace when a shared substrate changes. The final design makes local behavior explicit, keeps the live SQLite transition path viable, and proves the Postgres target through an opt in database command rather than accidental workspace coupling.

## Open Questions

- Should `moon ci` eventually include a named task for `lilo-db` Postgres tests rather than relying on a separate GitHub Actions step?
- Should the two existing nextest leaky tests from the full workspace run be tracked separately from the Postgres migration work?
