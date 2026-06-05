---
title: littleorgans Postgres Phase 1.a lilo-db contract review
type: research
tags: [littleorgans, postgres, lilo-db, persistence, spec-review]
summary: Fixture cleanup, compile transition, and LiloDb end-state contradictions were fixed; Phase 1.a contract revalidation signed off.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-06
updated: 2026-06-06
---

## Executive Summary

The Phase 1.a `lilo-db` contract aligns with the signed parent plan on Postgres as the single target backend, `LILO_DATABASE_URL`, internal `PgPool` exposure, Postgres migrations, and early fixture provisioning. Initial review found one blocker in the fixture cleanup contract, and later revalidations checked compile transition staging plus the `LiloDb` target versus transition end-state. The updated contract fixes these issues, so the revalidation outcome is signoff.

## Project Metadata

- Language: Rust workspace, edition 2024.
- Build system: Cargo workspace with Just gates.
- Navigation: fmm reported 387 indexed files and 56,985 LOC.
- Current persistence boundary: `internal/db/src/lib.rs` exports `LiloDb`, `ImmediateTx`, SQLite pool accessors, and SQLite transaction helpers.
- Reviewed documents: `/Users/alphab/.mdx/projects/littleorgans-postgres-phase-1a-lilo-db-contract.md` and linked parent plan lines for Phase 0 and Phase 1.a.

## Architecture

The current repo shape still has `LiloDb` backed by `SqlitePool` and exported helpers such as `open_path`, `identity_pool`, `session_pool`, `runtime_pool`, `begin_immediate_tx`, and `ImmediateTx` in `internal/db/src/lib.rs`. The contract proposes replacing that with a Postgres internal boundary: `LiloPool = sqlx::PgPool`, `LiloConnection = sqlx::PgConnection`, `DbConfig`, `LiloDb::open(config)`, `LiloDb::open_from_env()`, `LiloDb::pool()`, `LiloDb::acquire()`, and `LiloDb::begin()` (`littleorgans-postgres-phase-1a-lilo-db-contract.md:30-69`).

The parent plan now links the Phase 1.a contract directly (`littleorgans-postgres-persistence-plan.md:152-157`) and requires deterministic Postgres fixture provisioning before store gates depend on Postgres (`littleorgans-postgres-persistence-plan.md:161-170`).

## Key Patterns

- Backend neutral names are preserved while concrete internal types can be Postgres specific.
- The `lilo-im-store` publishable boundary remains outside `lilo-db`, consistent with the parent plan.
- Fixture provisioning is a Phase 1.a foundation, not an operations afterthought.
- Async database teardown needs an explicit async API. Rust `Drop` is a synchronous last resort, not a reliable cleanup boundary for sqlx pools and database deletion.

## Detailed Findings

### Blocker: `TestDb` cleanup cannot rely on `Drop`

The contract says `TestDb::create()` connects to an admin database, creates a unique test database, runs migrations, and returns a fixture (`littleorgans-postgres-phase-1a-lilo-db-contract.md:179-182`). It then requires dropping the fixture to close the pool and drop the test database (`littleorgans-postgres-phase-1a-lilo-db-contract.md:181-183`).

That cleanup shape is not executable as written. Closing a `PgPool` and issuing `DROP DATABASE` through sqlx are async operations. Rust `Drop` cannot await, and blocking a Tokio runtime from `Drop` is a fragile cleanup design. The contract should require an explicit async cleanup path, for example `TestDb::cleanup(self).await`, while `Drop` may only warn, record a leaked fixture name, or perform best effort synchronous metadata cleanup.

Bus reply sent:

```text
BLOCKED: `TestDb` cleanup contract is not executable as written. Lines 181-183 require dropping the fixture to close `PgPool` and drop the database, but both are async Postgres/sqlx work and Rust `Drop` cannot await. / NEED: replace with explicit async cleanup, e.g. `TestDb::cleanup(self).await`; `Drop` may only warn or mark leaks. Acceptance should require the cleanup path.
```


### Revalidation outcome after cleanup fix

The updated contract now defines `TestDb::cleanup(self).await` in the fixture API (`littleorgans-postgres-phase-1a-lilo-db-contract.md:173-178`). Required behavior now says explicit cleanup closes the pool and drops the test database, while `Drop` must not perform async cleanup and may only mark or warn about leaked databases (`littleorgans-postgres-phase-1a-lilo-db-contract.md:181-190`). Fixture acceptance now requires a cleanup test, a parallel fixture collision test, and test code that calls explicit cleanup or uses a helper that awaits cleanup (`littleorgans-postgres-phase-1a-lilo-db-contract.md:269-275`).

Verdict sent on the bus: `DONE: SIGNOFF / FINDINGS: none / RECOMMEND: none`.

### Revalidation outcome after transition scaffold fix

The latest contract and parent plan now resolve the compile transition blocker. The contract distinguishes the Postgres target API from an explicit transition surface: Phase 1.a introduces and proves the Postgres API, fixture, and service path; existing SQLite pool accessors may remain only where current stores need them to compile; no new code may use the transition surface; the handoff must list each remaining symbol and removal phase; Phase 1.b removes cross component use; Phase 2 deletes the private SQLite implementation (`littleorgans-postgres-phase-1a-lilo-db-contract.md:73-105`).

The parent plan matches that staging, requiring any remaining SQLite accessors to be marked as transition scaffolding with a removal owner in the Phase 1.a handoff, while Phase 1.b removes cross component SQLite leaks (`littleorgans-postgres-persistence-plan.md:159-200`, `littleorgans-postgres-persistence-plan.md:211-259`).

Verdict sent on the bus: `DONE: SIGNOFF / FINDINGS: none / RECOMMEND: none`.

### Revalidation outcome after LiloDb end-state clarification

The latest contract resolves the remaining `LiloDb` transition contradiction. Public Surface now says Phase 1.a exports target Postgres primitives while the single Postgres backed `LiloDb { pool: LiloPool }` struct is the Phase 2 end state after store callers stop using SQLite pool accessors (`littleorgans-postgres-phase-1a-lilo-db-contract.md:32-76`). Transition Surface now allows `LiloDb` to retain an internal SQLite backing path alongside the Postgres target path during Phase 1.a, limited to current compile blockers with no new code using that surface (`littleorgans-postgres-phase-1a-lilo-db-contract.md:78-112`). Parent plan staging matches this handoff and removal model (`littleorgans-postgres-persistence-plan.md:159-200`, `littleorgans-postgres-persistence-plan.md:211-259`).

Verdict sent on the bus: `DONE: SIGNOFF / FINDINGS: none / RECOMMEND: none`.

## Dependencies

- `sqlx` Postgres support is planned in the contract (`littleorgans-postgres-phase-1a-lilo-db-contract.md:228-237`).
- `lilo-paths::env` currently owns the LILO environment registry and does not yet include `LILO_DATABASE_URL` in the live repo.
- `lilo-db` remains unpublished internal infrastructure.

## Relevance to Helioy

The contract mostly reflects the Helioy pre-release standard: simplify the boundary first, avoid dual backend abstractions, and make acceptance prove the target backend. The required correction is small but important because unreliable fixture cleanup would make Postgres tests flaky and leave leaked local databases.

## Open Questions

- Should the fixture require a separate admin URL variable, or can it derive the admin database from `LILO_TEST_DATABASE_URL`?
- What exact helper pattern will ensure cross crate tests always await cleanup?
