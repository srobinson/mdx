---
title: Postgres Phase 2 Cutover And Flake Fix Verification For littleorgans
type: research
tags: [littleorgans, postgres, phase-2, verification, waitwatchers, flaky-test]
summary: The Phase 2 cutover and WaitWatchers flake fix are sound after commit 4cf6f1d preserved the satisfying waiter count in the RPC response.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Executive Summary

Final adversarial pass on `feat/postgres-phase-2` found the Postgres cutover aligned with the locked contract: schema, owner seam, text ids, timestamp conversion, transaction replacement, test gating, and SQLite transition removal all checked out in focused inspection. The previously reported `WaitWatchers` response race is fixed in `4cf6f1d`: the RPC now returns the event waiter count that satisfied the daemon-side wait instead of re-reading it.

The final bus verdict was `SIGNOFF: cutover + flake-fix sound, branch ready`.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`
- Branch: `feat/postgres-phase-2`
- HEAD: `4cf6f1d8ecf48ffd35b7338b2e3762ffec06b84a`
- Compared against: `main`
- fmm status: valid, 389 indexed files
- Contract: `/Users/alphab/.mdx/projects/littleorgans-postgres-phase-2-backend-contract.md`
- Local Postgres used for spot check: `postgres://lilo:lilo@localhost:55433/lilo`

## Architecture

Phase 2 collapses the persistence boundary onto one Postgres pool:

- `internal/db/src/lib.rs:25-35` defines `LiloPool = PgPool`, `LiloConnection = PgConnection`, `LiloTransaction<'a> = Transaction<'a, Postgres>`, and `LiloDb { pool }`.
- `internal/db/src/lib.rs:42-61` opens Postgres, runs the single migration, and returns the unified pool.
- `internal/db/src/lib.rs:103-120` provides `commit_or_rollback`, replacing the old SQLite immediate transaction helper.
- `internal/db/migrations/0001_unified_schema.sql:9-153` defines the Postgres schema with `TIMESTAMPTZ`, `owner TEXT NOT NULL DEFAULT 'local'` on the three scoped tables, text ids, `runtime_metadata.value TEXT`, and `runtime_metadata.updated_at TIMESTAMPTZ`.

The event flake fix adds a runtime RPC path:

- `crates/lilo-rm-core/src/proto.rs:112-118` adds `RuntimeRpc::WaitWatchers`.
- `internal/runtime/daemon/src/identity.rs:86-89` authorizes it as `Action::Read`.
- `internal/runtime/daemon/src/event_log.rs:229-250` waits on a `Notify` backed event waiter signal.
- `internal/runtime/daemon/src/server/state.rs:271-282` now returns the satisfying event waiter observation in `WatcherCounts.event_waiters`.
- `internal/runtime/app/tests/common/wait.rs:160-185` uses that RPC instead of client side polling.

## Key Patterns

- The cutover keeps module paths named `sqlite` for now but changes the bodies to Postgres. `crates/lilo-im-store/src/lib.rs:17-20` documents this as a planned cosmetic rename, not a backend feature.
- The owner seam is default driven. Insert paths omit owner, relying on `DEFAULT 'local'`, which matches the v1 contract and avoids widening APIs prematurely.
- The deterministic waiter direction is correct: move synchronization inside the daemon and preserve the satisfying observation in the response rather than sampling a transient counter through repeated RPC calls.

## Detailed Findings

### 1. Cutover contract checks passed in focused inspection

Evidence:

- Branch has six commits, with `4cf6f1d` fixing the final WaitWatchers response race.
- `fmm validate` passed for 389 files.
- Functional SQLite residue command returned no matches:
  `rg "SqlitePool|SqliteConnection|sqlx::Sqlite|PoolConnection<Sqlite>|BEGIN IMMEDIATE|PRAGMA|sqlite_master|ImmediateTx|begin_immediate|finish_immediate|QueryBuilder::<Sqlite>|Database = Sqlite" internal crates`.
- `internal/db/migrations-sqlite/` and `internal/db/src/transition.rs` are deleted.
- `crates/lilo-im-store/Cargo.toml` has no `lilo-db` dependency and exposes `postgres = ["dep:sqlx"]`.
- `justfile:74-82` and `.github/workflows/pr.yml:89-94` now run workspace ignored-only DB tests.

Schema checks:

- `identity_audit` has text primary key, `seq BIGINT GENERATED ALWAYS AS IDENTITY`, owner default, and `timestamp TIMESTAMPTZ`: `internal/db/migrations/0001_unified_schema.sql:9-27`.
- `session_sessions` keeps text id and has owner plus timestamp columns: `internal/db/migrations/0001_unified_schema.sql:30-53`.
- `runtime_lifecycle` has text session id, owner, and timestamp columns: `internal/db/migrations/0001_unified_schema.sql:130-148`.
- `runtime_metadata.value` stays `TEXT`, while `updated_at` is `TIMESTAMPTZ`: `internal/db/migrations/0001_unified_schema.sql:150-153`.

Timestamp and boolean checks:

- Session rows decode `created_at`, `started_at`, `terminated_at`, and `updated_at` as `DateTime<Utc>` in `internal/session/store/src/sqlite/sessions.rs:439-443`.
- Mail binds and decodes `sent_at` and `read_at` as `DateTime<Utc>` in `internal/session/store/src/sqlite/mail.rs:153-154`, `:274`, and `:307-308`.
- `namespace_exists` uses `query_scalar::<_, bool>` in `internal/session/store/src/sqlite/namespaces.rs:36-43`; the test helper does the same at `:364-376`.
- `_sqlx_migrations.success` is queried as a boolean predicate in `internal/runtime/store/src/sqlite/lifecycle.rs:281-287`.
- `record_probe_sweep` keeps `runtime_metadata.value` as an RFC3339 string and binds only `updated_at` as `DateTime<Utc>` in `internal/runtime/store/src/sqlite/lifecycle.rs:245-258`; `last_probe_sweep` reads `updated_at` directly at `:264-277`.

Behavior seams checked:

- Prefix selector still uses text `LIKE $1 || '%'` and ambiguity reporting in `internal/session/store/src/sqlite/sessions.rs:163-182`.
- Mail idempotency preserves SELECT then INSERT, with a Postgres unique violation retry in `internal/session/store/src/sqlite/mail.rs:61-76`; unique violation detection is scoped to `idx_messages_sender_idempotency` at `:548-552`.
- Spawn-intent insert, resolve, and abort all use Postgres transactions and `commit_or_rollback` in `internal/session/store/src/sqlite/spawn_intents.rs:197-247`.
- Lifecycle transaction seams use `LiloTransaction` and Postgres executors in `internal/runtime/store/src/sqlite/lifecycle.rs:81-124`, `:326-358`.

### 2. WaitWatchers response race is fixed

The prior issue was narrow: `ServerState::wait_for_event_waiters` waited for `EventLog::wait_for_min_waiters`, then discarded that count and re-snapshotted through `watcher_counts()`. A short waiter could unregister between those operations.

Live fix in `4cf6f1d`:

- `internal/runtime/daemon/src/server/state.rs:276` stores `let event_waiters = self.events.wait_for_min_event_waiters(min, timeout).await;`.
- `internal/runtime/daemon/src/server/state.rs:277-281` constructs `WatcherCounts` directly and sets `event_waiters` to the stored satisfying observation.
- There is no remaining `watcher_counts()` call on the `WaitWatchers` path.
- The comment at `internal/runtime/daemon/src/server/state.rs:263-270` now documents why the satisfying observation must be preserved.

The daemon-side waiter primitive remains sound:

- It arms the notification before reading the count: `internal/runtime/daemon/src/event_log.rs:232-237`.
- It returns the count once `count >= min`: `internal/runtime/daemon/src/event_log.rs:237-240`.
- `EventWaiterGuard` notifies on both increment and decrement: `internal/runtime/daemon/src/event_log.rs:267-278`.

This closes the response race I reported in the previous pass.

### 3. Validation performed

Commands and results:

```bash
git show --unified=40 4cf6f1d -- internal/runtime/daemon/src/server/state.rs
fmm validate
CARGO_TARGET_DIR=target/nextest cargo build -p lilo -p lilo-runtime-app
LILO_TEST_DATABASE_URL=postgres://lilo:lilo@localhost:55433/lilo \
CARGO_TARGET_DIR=target/nextest \
cargo nextest run -p lilo-runtime-app \
  --test integration_events_cursor \
  timed_out_long_poll_releases_waiter \
  --run-ignored ignored-only
```

Results:

- `git show` confirmed the live fix returns the observed count and no longer re-snapshots `event_waiters`.
- `fmm validate` passed for 389 files.
- Build passed.
- Targeted Postgres ignored test passed, 1 passed and 13 skipped.

## Dependencies

Critical dependencies in the changed paths:

- `sqlx` with Postgres, chrono, migrate, runtime tokio, and uuid workspace features.
- `chrono::DateTime<Utc>` for native `TIMESTAMPTZ` binds and decodes.
- `tokio::sync::Notify` for daemon side waiter synchronization.

## Relevance to Helioy

This branch now follows the broader Helioy lesson: put synchronization at the producer of the transient state, then return the exact observed state that satisfied the wait. That avoids turning a deterministic daemon-side wait back into a client-visible sampling race.

## Open Questions

- Should `WaitWatchers` remain in the public `RuntimeRpc` enum after test hardening, or should it be gated as a test/debug contract only?
- Should the legacy module path and error variant names containing `sqlite` be renamed in the next cosmetic phase, or left until the planned Phase 5 rename?

## Bus Replies Sent

Earlier issue reply sent to `littleorgans:general:5:2.1` on topic `pg2-verify`:

`ISSUES: internal/runtime/daemon/src/server/state.rs:271 — WaitWatchers discards the event_waiters count that satisfied EventLog::wait_for_min_waiters and re-snapshots via watcher_counts(), so a short waiter can drop before the response and the deterministic helper still has a response race; return the observed count in WatcherCounts.event_waiters.`

Final reply sent after `4cf6f1d` live re-read and targeted proof:

`SIGNOFF: cutover + flake-fix sound, branch ready`
