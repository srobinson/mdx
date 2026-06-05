---
title: Postgres Phase 2 Contract Audit For littleorgans
type: research
tags: [littleorgans, postgres, sqlx, persistence, contract-audit]
summary: Phase 2's atomic Postgres cutover contract is sound after the runtime_metadata timestamp ambiguity was corrected.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-06
updated: 2026-06-06
---

## Executive Summary

The Phase 2 backend contract correctly frames the Postgres cutover as an atomic store, transaction, and daemon opening change. Initial audit blockers were reconciled in the live contract, including timestamp bind/decode coverage, Postgres boolean rewrites, workspace ignored DB test coverage, and the `runtime_metadata.value` versus `updated_at` distinction.

Final bus reply to `littleorgans:general:5:2.1` on topic `pg2-spec`: `SIGNOFF: contract sound, ready to implement`.


## Final Lock Pass Update

A revised contract was re-read live after the first audit. The original three bus-reported gaps were closed: §3.4 enumerates timestamp bind/decode sites, §3.5 covers Postgres boolean rewrites for `_sqlx_migrations.success` and `EXISTS`, and §8.3 broadens ignored DB tests to workspace `--run-ignored ignored-only`.

A later pass found one remaining D-TS ambiguity around `runtime_metadata.value` versus `runtime_metadata.updated_at`. The final live contract now fixes it: `record_probe_sweep` keeps `value` as a `TEXT`/`String` bind, converts only `updated_at` to `DateTime<Utc>`, and redirects `last_probe_sweep` from `SELECT value` plus parse to `SELECT updated_at` plus `query_scalar::<_, DateTime<Utc>>`. Final verdict: contract sound, ready to implement.

## Project Metadata

- Language: Rust workspace, edition 2024, rust version 1.95 (`Cargo.toml:31-38`).
- Build and test: Cargo plus Moon CI, operator surface via `just` (`README.md` development section, `justfile:188-198`).
- Database stack: `sqlx 0.8.3` with `chrono`, `migrate`, `postgres`, `runtime-tokio`, `sqlite`, and `uuid` features during transition (`Cargo.toml:76`).
- Primary Postgres boundary: `internal/db` exports `LiloPool = sqlx::PgPool`, `LiloConnection = sqlx::PgConnection`, and `LiloTransaction<'a> = sqlx::Transaction<'a, Postgres>` (`internal/db/src/lib.rs:32-36`).
- Current cutover baseline: `main` at `f235cff`; `fmm validate` reported all 391 indexed files current.

## Architecture

The persistence surface is split by bounded context:

- `internal/db`: shared database boundary. Current code has the Postgres target API plus a private SQLite transition path (`internal/db/src/lib.rs:23-36`, `internal/db/src/transition.rs:41-201`).
- `internal/session/store`: session records, labels, namespaces, mail, event cursor, and spawn intents. Public names are neutral, but private module paths and SQL bodies remain SQLite-shaped (`internal/session/store/src/sqlite/*.rs`).
- `internal/runtime/store`: lifecycle and runtime metadata in `LifecycleStore` (`internal/runtime/store/src/sqlite/lifecycle.rs:48-324`).
- `crates/lilo-im-store`: published audit store with default sqlx-free surface and feature-gated concrete store (`crates/lilo-im-store/Cargo.toml:30-35`, `src/sqlite/audit.rs:49-97`).
- `internal/identity/service`: composes audit authorization and threads the shared transaction (`internal/identity/service/src/client.rs`).

Phase 2 deletes `internal/db/src/transition.rs`, removes `internal/db/migrations-sqlite/`, changes private store bodies to Postgres, and replaces `ImmediateTx` with `LiloTransaction<'_>` across daemon and store seams.

## Key Patterns

- Typed ids remain Rust-owned through `define_id!`, which wraps `uuid::Uuid`, derives serde transparent, and conditionally derives `sqlx::Type` (`crates/lilo-common/src/id.rs:22-38`).
- Short id UX is implemented as text prefix matching in session store: `WHERE id LIKE ? || '%'`, followed by ambiguity reporting (`internal/session/store/src/sqlite/sessions.rs:162-181`).
- Current time storage is RFC3339 text. Helpers parse string timestamps from rows (`internal/session/store/src/sqlite/time.rs:3-13`), while stores call `to_rfc3339()` before binding.
- Current SQLite transition transactions use one pool-scoped `ImmediateTx` for shared spawn work (`internal/db/src/transition.rs:105-201`).

## Detailed Findings

### D-ID: text ids are sound

Verdict: sound.

Evidence:

- The typed-id macro delegates to `uuid::Uuid` and already supports native sqlx typing when the feature is enabled (`crates/lilo-common/src/id.rs:22-38`).
- Actual stores bypass typed sqlx binding today by writing and reading strings (`internal/session/store/src/sqlite/sessions.rs:334`, `428`; `internal/session/store/src/sqlite/mail.rs:246`, `281`; `internal/runtime/store/src/sqlite/lifecycle/codec.rs:64`, `85`).
- The load-bearing prefix selector is a text operation (`internal/session/store/src/sqlite/sessions.rs:162-181`).

Keeping `text` avoids `id::text LIKE` casts and a functional prefix index. Native `uuid` would add DB-level validation and smaller storage, but no correctness requirement justifies that churn for single-operator v1.

### D-OWNER-IDX: uniqueness is safe, state listing index needs a nuance

Verdict: mostly sound, with one index caveat.

Evidence:

- The current migration has surrogate primary keys for `identity_audit.id`, `session_sessions.id`, and `runtime_lifecycle.session_id` (`internal/db/migrations/0001_unified_schema.sql:1-3`, `18-19`, `115-116`). Owner does not need to enter those unique keys for v1 correctness.
- The proposed owner seam covers the three decision-10 tables and does not widen messages or namespaces (`littleorgans-postgres-phase-2-backend-contract.md:115-132`).
- Runtime list filtering uses `LOWER(state) = LOWER($)` (`internal/runtime/store/src/sqlite/lifecycle.rs:157-160`). A plain `(owner, state)` index, proposed at contract lines 125-127, will not support that predicate. Either make the state filter exact-case or use a functional index such as `(owner, lower(state))` if the contract promises index-supported owner scans.

### D-TS: direction is sound, implementation plan is incomplete

Verdict: blocking issue.

The schema decision to convert RFC3339 text columns to `timestamptz` is right (`littleorgans-postgres-phase-2-backend-contract.md:85-113`). The query migration section under-specifies required code rewrites. Current code binds and decodes timestamps as `String`, which is unsafe once columns become native timestamps.

Representative required rewrites:

- `session_sessions` writes use `to_rfc3339()` for `created_at`, `started_at`, `terminated_at`, and `updated_at` (`internal/session/store/src/sqlite/sessions.rs:268-269`, `292`, `314`, `352-360`). Reads use `try_get::<String>` plus RFC3339 parsing (`internal/session/store/src/sqlite/sessions.rs:442-448`).
- `messages` and `message_deliveries` bind and decode `sent_at` and `read_at` as RFC3339 strings (`internal/session/store/src/sqlite/mail.rs:132`, `173`, `215-219`, `252`, `272`, `285-286`, `516`).
- Runtime lifecycle binds `updated_since`, `recent_lost_since`, and metadata timestamps as strings (`internal/runtime/store/src/sqlite/lifecycle.rs:166`, `235`, `246`). Its row codec models `start_time`, `updated_at`, and encoded `now` as `String` (`internal/runtime/store/src/sqlite/lifecycle/codec.rs:23`, `40`, `50`, `55`, `70`, `75`, `91`, `105`, `199-200`).
- Audit rows encode and decode `timestamp` as a string and filter `since` as `since.to_rfc3339()` (`crates/lilo-im-store/src/sqlite/audit.rs:118`, `137`, `153`, `197`).
- Namespaces bind and decode `created_at` as text (`internal/session/store/src/sqlite/namespaces.rs:57`, `124`).
- Event application writes `started_at`, `terminated_at`, `updated_at`, and cursor `updated_at` as RFC3339 text (`internal/session/store/src/sqlite/events.rs:57-58`, `73-86`, `115`, `134`).

The contract should require `DateTime<Utc>` or `Option<DateTime<Utc>>` binds and row decodes for all `timestamptz` columns, while leaving spawn-intent epoch millis as `BIGINT`.

### Additional Postgres query gaps

Verdict: blocking if left out of the Phase 2 plan.

Two current SQLite idioms will not survive a Postgres backend:

- `namespace_exists` decodes `SELECT EXISTS(...)` as `i64` and compares `exists != 0` (`internal/session/store/src/sqlite/namespaces.rs:38-44`). Postgres returns `bool` for `EXISTS`.
- `migration_state` queries `_sqlx_migrations` with `WHERE success = 1` (`internal/runtime/store/src/sqlite/lifecycle.rs:282-288`). Postgres sqlx migrations use boolean `success`, so the predicate should become `success = TRUE` or simply `success`.

The contract mentions `_sqlx_migrations.version` but not the boolean predicate (`littleorgans-postgres-phase-2-backend-contract.md:233-237`).

### D-PAYLOAD: keeping text and bytea is sound

Verdict: sound.

No current query requires JSON containment, GIN, or full-text search:

- Audit query filters principal, action, and since, then orders rows (`crates/lilo-im-store/src/sqlite/audit.rs:175-203`).
- Mail log query filters context, participant ids, recipient ids, system intent, and keyset time/id, not content text (`internal/session/store/src/sqlite/mail.rs:179-227`).
- Spawn intent JSON blobs are written and read as transient payloads (`internal/session/store/src/sqlite/spawn_intents.rs:284-299`, `364-374`).
- The event cursor is already `BYTEA` in the Postgres migration (`internal/db/migrations/0001_unified_schema.sql:94-98`).

### D-TESTGATE: not airtight until CI changes

Verdict: blocking issue.

The contract recommends marking Postgres-backed store, daemon, and integration tests ignored locally while CI runs them with `--run-ignored all` (`littleorgans-postgres-phase-2-backend-contract.md:439-452`). Current CI and `just test-db` only run ignored tests for `lilo-db`:

- `.github/workflows/pr.yml:89-93` runs `cargo nextest run -p lilo-db --run-ignored all`.
- `justfile:74-80` does the same for local `just test-db`.

If Phase 2 marks store, daemon, or integration tests ignored without changing those gates, they will be silently skipped in CI. The contract should list `.github/workflows/pr.yml` and `justfile` changes, with a workspace-wide ignored DB test command or explicit package list.

### Atomic vs sliced: atomic recommendation is sound

Verdict: sound, with two missing blast-radius entries.

The atomic argument holds because Postgres SQL bodies cannot run against `SqlitePool`, `LiloDb` cannot be half-collapsed, and `ImmediateTx` to `LiloTransaction` crosses session, runtime, identity, and daemon seams (`littleorgans-postgres-phase-2-backend-contract.md:489-515`). Deleting `transition.rs` has broad caller impact.

The draft blast-radius list is mostly accurate, but exact search also finds two runtime app test callers not named in the list:

- `internal/runtime/app/tests/integration_pass4.rs:76`
- `internal/runtime/app/tests/common/lifecycle.rs:29`

### ON CONFLICT and transaction semantics

Verdict: sound with normal rewrite care.

- `ON CONFLICT` sites are Postgres-valid and should be preserved: session labels (`internal/session/store/src/sqlite/labels.rs:99`), session event cursor (`internal/session/store/src/sqlite/events.rs:127-134`), and runtime metadata (`internal/runtime/store/src/sqlite/lifecycle.rs:247-254`).
- Mail idempotency has no `ON CONFLICT`. It uses SELECT-first replay validation inside a transaction plus the partial unique index on `(sender_ref, idempotency_key)` (`internal/session/store/src/sqlite/mail.rs:63-82`, `327-384`; migration lines `60-62`). That remains sound under a Postgres transaction.
- `BEGIN IMMEDIATE` removal is sound. Postgres `BEGIN` with `READ COMMITTED` preserves atomicity for these writes because uniqueness and transaction boundaries carry the guarantees. A neutral commit helper may keep callers DRY, but it must not reintroduce SQLite naming.

### Migration directory claim

Verdict: verified.

- `internal/db/migrations/0001_unified_schema.sql` exists and is Postgres-shaped with `BYTEA`, `BIGINT`, and `to_char(now() AT TIME ZONE 'UTC', ...)` (`internal/db/migrations/0001_unified_schema.sql:47-48`, `94-98`).
- `internal/db/migrations-sqlite/0001_unified_schema.sql` also exists and is the quarantined transition directory to delete in Phase 2.

## Dependencies

Critical dependencies for this audit:

- `sqlx`: database pool, migrations, dynamic queries, and typed row decode.
- `chrono`: timestamp domain types and `DateTime<Utc>`.
- `uuid`: typed id inner representation.
- `lilo-db`: shared Postgres boundary and temporary SQLite transition surface.
- `lilo-im-store` and `lilo-im-core`: published audit storage and sqlx-free audit contract.
- `cargo-nextest`, Moon, and `just`: local and CI verification paths.

## Relevance to Helioy

The main Helioy lesson is contract precision around type migrations. A schema-level decision such as `text` to `timestamptz` is not complete unless the contract enumerates bind types, decode types, and test gates that force those paths to run. The CI gap also repeats a common migration failure mode: ignored tests are acceptable only when the DB job proves they run.

## Verification Performed

- `fmm validate` succeeded for 391 indexed files.
- `fmm_list_files(group_by: "subdir")` confirmed repo topology: 391 files, 57,797 LOC.
- Targeted `rg` searches verified `ON CONFLICT`, `QueryBuilder::<Sqlite>`, `Database = Sqlite`, `to_rfc3339()`, `SELECT EXISTS`, `success = 1`, transition callers, and CI ignored-test commands.
- No code changes were made to the target repository.

## Open Questions

- Should Phase 2 keep runtime state filtering case-insensitive, or can it normalize to exact-case and use a simpler `(owner, state)` index?
- Should `just test-db` become workspace-wide during Phase 2, or should it run a curated package list to keep local DB verification faster?
- Should doctor replace SQLite PRAGMA checks with Postgres catalog checks in Phase 2, or should it degrade those fields while Phase 3 owns richer health semantics?

## Final Signoff Evidence

- Live contract §3.4 now explicitly distinguishes `runtime_metadata.value` from `runtime_metadata.updated_at` and redirects `last_probe_sweep` to read `updated_at`.
- `fmm validate` passed: all 391 indexed files current.
- Targeted source checks covered `internal/runtime/store/src/sqlite/lifecycle.rs:245-278`, `internal/session/store/src/sqlite/labels.rs:80-107`, and timestamp idiom searches across session, runtime, and im-store.
- Bus reply sent: `SIGNOFF: contract sound, ready to implement`.
