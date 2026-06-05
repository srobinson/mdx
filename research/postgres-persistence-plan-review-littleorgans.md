---
title: littleorgans Postgres persistence plan review
type: research
tags: [littleorgans, postgres, persistence, plan-review, rust]
summary: Initial issues were resolved in the updated plan; revalidation signed off on the Postgres persistence migration plan.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-06
updated: 2026-06-06
---

## Executive Summary

The Postgres persistence plan is directionally coherent: it starts with a persistence boundary, treats Postgres as the single target backend, and calls out `lilo-im-store` publishability as a constraint. Initial review found gaps in Phase 0 decisions, working file coverage, and Phase 4 proof. The updated 2026-06-06 plan resolves those gaps, so the revalidation outcome is signoff.

## Project Metadata

- Language: Rust workspace, edition 2024, Rust 1.95.
- Build system: Cargo workspace with Just operator gates.
- Navigation: `fmm validate` passed on 2026-06-06, 387 indexed files.
- Current database stack: `sqlx` with `sqlite` and `uuid` features in `Cargo.toml:76`.
- Persistence crates reviewed: `internal/db`, `internal/session/store`, `internal/runtime/store`, `crates/lilo-im-store`.

## Architecture

Current persistence centers on `LiloDb` in `internal/db/src/lib.rs`. `LiloDb` owns a `SqlitePool` field, exposes `open`, `open_path`, and substrate pool accessors, and runs unified migrations from `internal/db/migrations` (`internal/db/src/lib.rs:17-74`). Transaction helpers encode SQLite `BEGIN IMMEDIATE` semantics (`internal/db/src/lib.rs:77-169`).

Session store still exports `SqliteStore` from the public crate root (`internal/session/store/src/lib.rs:3-12`), backed by `SqlitePool` and a test `open_temp` that creates `lilo.db` directly (`internal/session/store/src/sqlite.rs:13-48`). Runtime store exposes `LifecycleStore` from its `sqlite` module. Identity audit storage is a published crate, `crates/lilo-im-store`, and currently exports `SqliteAuditSink`, `query_audit(&SqlitePool, ...)`, and SQLite specific schema inspection (`crates/lilo-im-store/src/lib.rs:1-21`, `crates/lilo-im-store/src/sqlite/audit.rs:50-97`).

## Key Patterns

- The migration should be boundary first, backend second. The plan reflects this in Phase 1 and Phase 2.
- `lilo-im-store` is the critical exception to an internal `lilo-db` boundary because it is a publishable crate and cannot depend on unpublished `lilo-db`.
- Real acceptance must exercise a Postgres service. Generic `just check`, `just build`, and `just test` are necessary but insufficient unless the fixture path provisions Postgres.

## Detailed Findings

### 1. Phase 0 should lock all load-bearing persistence decisions

The plan correctly says no worker should start code changes before the `lilo-db` API shape is approved (`littleorgans-postgres-persistence-plan.md:125-129`). The same phase still leaves open whether stores see `PgPool` or a wrapper, where migrations live, and how `LILO_DATABASE_URL` is resolved (`littleorgans-postgres-persistence-plan.md:146-154`). It also defers the `lilo-im-store` handling options (`littleorgans-postgres-persistence-plan.md:199-206`).

Those choices shape the store APIs, test fixtures, identity audit transaction path, and publishable crate boundary. They should be Phase 0 gates, not Phase 1.b discoveries. Current code shows why: `IdentityClient::authorize_in_tx` takes `&mut SqliteConnection` and calls `record_audit_in_tx` from `lilo-im-store` (`internal/identity/service/src/client.rs:63-79`), while `record_audit_in_tx` is itself typed to `SqliteConnection` (`crates/lilo-im-store/src/sqlite/audit.rs:92-97`).

### 2. The working file set misses active protocol and test surfaces

The plan states the current scan surfaced 49 files and treats the list as planning input (`littleorgans-postgres-persistence-plan.md:43-99`). Live reads found important SQLite surfaces outside that list:

- `tests/integration/tests/db_contract.rs:5-26` asserts SQLite PRAGMAs and busy behavior directly.
- `crates/lilo-rm-core/src/admin.rs:205-215` exposes `DoctorResponse.sqlite` in a JSON contract comment that calls the field names stable.
- `crates/lilo-rm-core/src/cli_output.rs:58-70` renders a `sqlite` section.
- `internal/session/driver/src/conv.rs:205-208` derives runtime doctor health from `doctor.sqlite.pending_descriptions`.
- `crates/lilo/src/cli/doctor/runtime.rs:61-64` emits `runtime sqlite migrations pending`.

Phase 5 mentions runtime response fields named `sqlite` (`littleorgans-postgres-persistence-plan.md:380-388`), but these are protocol and generated surface inputs, not only cleanup residue. The plan should move them into the caller migration or a dedicated protocol surface workstream with acceptance for schema, snapshots, and generated docs.

### 3. Phase 4 proof is not executable enough for the target environments

Phase 4 names local native, Docker Compose, and cloud targets (`littleorgans-postgres-persistence-plan.md:333-360`), but suggested verification remains generic (`littleorgans-postgres-persistence-plan.md:362-368`) and the only live smoke is optional (`littleorgans-postgres-persistence-plan.md:370-374`). The command shown, `cargo run -p lilo -- daemon start`, enters the long-running daemon path (`crates/lilo/src/cli/daemon.rs:29-33`) and does not by itself prove readiness, doctor health, or clean shutdown.

A deterministic acceptance path should include non-optional Postgres backed tests or smokes for each environment. A practical shape is: provision database, set `LILO_DATABASE_URL`, run migrations, start daemon in a controlled background process or test harness, run `lilo doctor --output json`, then stop the daemon and assert clean teardown.


### Revalidation outcome, 2026-06-06

The updated plan resolves the prior blockers. Phase 0 now locks `LILO_DATABASE_URL`, concrete internal `PgPool` exposure, Postgres migrations, `lilo-im-store` feature-gated Postgres support without `lilo-db`, and deterministic Postgres fixture provisioning (`littleorgans-postgres-persistence-plan.md:111-148`). Phase 1.a now owns Postgres fixture and Compose or CI service setup before store gates require Postgres (`littleorgans-postgres-persistence-plan.md:156-193`). The working set now includes protocol and test surfaces such as `crates/lilo-rm-core/src/admin.rs`, `crates/lilo/src/cli/doctor/runtime.rs`, `internal/session/driver/src/conv.rs`, and `tests/integration/tests/db_contract.rs` (`littleorgans-postgres-persistence-plan.md:43-103`). Phase 3 covers admin and driver protocol field cleanup (`littleorgans-postgres-persistence-plan.md:318-360`). Phase 4 now requires deterministic local, Compose, and cloud daemon smokes, with a bounded foreground or harness change if needed (`littleorgans-postgres-persistence-plan.md:386-412`).

Verdict sent on the bus: `DONE: SIGNOFF / FINDINGS: none / RECOMMEND: none`.

## Dependencies

- `sqlx` currently uses SQLite features only from the workspace dependency (`Cargo.toml:76`). Postgres migration must add or replace the relevant features in one place.
- `lilo-db` is internal and unpublished (`internal/db/Cargo.toml:1-11`). It can own internal connection and migration policy.
- `lilo-im-store` is under `crates/` and has no `publish = false` marker (`crates/lilo-im-store/Cargo.toml:1-37`). Its public API cannot rely on internal crates.

## Relevance to Helioy

This plan is a good fit for the Helioy pre-release standard: break compatibility to simplify the system, keep generated and public surfaces authored from one source of truth, and avoid staged duplication. The main correction is to lock the irreversible API and publishability decisions before parallel work starts.

## Open Questions

- What exact Phase 1.a `lilo-db` API and fixture contract will the implementation note approve?
- Should ID columns become native Postgres `uuid` or remain text for short-prefix ergonomics?
- Which generated surfaces own the `DoctorResponse.sqlite` protocol cleanup?
- What concrete cloud smoke target will be used when valid managed Postgres credentials are available?
