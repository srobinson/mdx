# schedule-matters Phase 1 · Plan 01 — Scaffolding Implementation Plan

> **For agentic workers:** Use a task-by-task execution discipline (subagent-driven or inline).
> Steps use checkbox (`- [ ]`) syntax for tracking. Each step is one action; run the test, see it
> fail, implement, see it pass, commit.

**Goal:** Stand up the two schedule-matters crates and make them reachable from the wire envelope
and the shared database, without touching any existing behavior.

**Architecture:** Pure-additive scaffolding. `lilo-schedule-core` holds the `ScheduleRpc` control
enum and (later) the record/manifest types; `lilo-schedule-store` holds the SQLite store skeleton
over the single shared `data/lilo.db`. The wire envelope gains a third substrate variant; `LiloDb`
gains a fourth named pool accessor that returns the same shared pool as its siblings.

**Tech stack:** Rust (edition/workspace inheritance), `serde`/`serde_json`, `sqlx` (SQLite, WAL),
`cargo`, `just`. Mirrors the existing `internal/session/{core,store}` and `internal/db` patterns.

**Ground-truth anchors (verified against the live repo):**
- Workspace members + `[workspace.dependencies]`: root `Cargo.toml` (members list ends at
  `tools/xtask`; internal crates use `{ path = "…" }`, no version; `crates/*` use `version="0.8.0"`).
- Wire envelope: `internal/wire/src/lib.rs:5-8` — `LilodRpc` is
  `#[serde(tag = "substrate", content = "payload", rename_all = "lowercase")]` over
  `Session(lilo_session_core::SessionRpc)` and `Runtime(lilo_rm_core::RuntimeRpc)`.
- Core-crate template: `internal/session/core/Cargo.toml` (lib name `lilo_session_core`,
  `publish = false`, workspace inheritance, `[lints] workspace = true`).
- Single pool: `internal/db/src/lib.rs:16-18` (`LiloDb { pool: SqlitePool }`), `:58-68`
  (`identity_pool`/`session_pool`/`runtime_pool` each return `&self.pool`).
- Store open idiom: `internal/session/store/src/sqlite.rs:28-31` (`SqliteStore::open` clones
  `db.session_pool()`).

**Scope guard:** `ScheduleRpc` ships in Plan 01 with a single thin read verb so the envelope
compiles and serializes; the full §3.3 verb set is added incrementally in Plans 02–07. No store
tables and no migrations land here (that is Plan 02). No existing code path changes behavior.

---

## File structure

| File | Responsibility | Action |
|---|---|---|
| `internal/schedule/core/Cargo.toml` | crate manifest for `lilo-schedule-core` | create |
| `internal/schedule/core/src/lib.rs` | re-exports; crate root | create |
| `internal/schedule/core/src/proto/rpc.rs` | `ScheduleRpc` control enum | create |
| `internal/schedule/store/Cargo.toml` | crate manifest for `lilo-schedule-store` | create |
| `internal/schedule/store/src/lib.rs` | `ScheduleStore` skeleton | create |
| `Cargo.toml` (root) | workspace members + dependencies | modify |
| `internal/wire/Cargo.toml` | add `lilo-schedule-core` dep | modify |
| `internal/wire/src/lib.rs:5-8` | add `Schedule(ScheduleRpc)` variant + test | modify |
| `internal/db/src/lib.rs:58-68` | add `schedule_pool()` accessor + test | modify |

---

## Task 1: Create `lilo-schedule-core` with a minimal `ScheduleRpc`

**Files:**
- Create: `internal/schedule/core/Cargo.toml`
- Create: `internal/schedule/core/src/lib.rs`
- Create: `internal/schedule/core/src/proto/rpc.rs`
- Modify: root `Cargo.toml` (members + `[workspace.dependencies]`)

- [ ] **Step 1: Write the crate manifest** (mirrors `internal/session/core/Cargo.toml`)

`internal/schedule/core/Cargo.toml`:
```toml
[package]
name = "lilo-schedule-core"
version.workspace = true
edition.workspace = true
license.workspace = true
repository.workspace = true
homepage.workspace = true
authors.workspace = true
rust-version.workspace = true
publish = false

[lib]
name = "lilo_schedule_core"
path = "src/lib.rs"

[dependencies]
serde.workspace = true
serde_json.workspace = true
uuid.workspace = true

[lints]
workspace = true
```

- [ ] **Step 2: Write the failing test** for the `ScheduleRpc` shape

`internal/schedule/core/src/proto/rpc.rs`:
```rust
use serde::{Deserialize, Serialize};

/// Schedule substrate control verbs. Plan 01 ships only the thin read verb;
/// the full set (§3.3 of the spec) is added in later plans.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum ScheduleRpc {
    /// Read one applied topology unit by its durable schedule UID.
    SessionGet { schedule_session_uid: String },
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn schedule_rpc_round_trips() {
        let rpc = ScheduleRpc::SessionGet { schedule_session_uid: "ssn_01".to_string() };
        let json = serde_json::to_string(&rpc).unwrap();
        let back: ScheduleRpc = serde_json::from_str(&json).unwrap();
        assert_eq!(rpc, back);
    }
}
```

- [ ] **Step 3: Write the crate root**

`internal/schedule/core/src/lib.rs`:
```rust
mod proto;

pub use proto::rpc::ScheduleRpc;
```

`internal/schedule/core/src/proto/mod.rs`:
```rust
pub mod rpc;
```

- [ ] **Step 4: Register the crate in the workspace**

In root `Cargo.toml`, add to `[workspace] members` (after `"internal/session/app",`):
```toml
    "internal/schedule/core",
    "internal/schedule/store",
```
In root `[workspace.dependencies]` (after the `lilo-session-store` line):
```toml
lilo-schedule-core = { path = "internal/schedule/core" }
lilo-schedule-store = { path = "internal/schedule/store" }
```
(`internal/schedule/store` is created in Task 3; declaring its workspace entry now keeps the two
member edits in one place.)

- [ ] **Step 5: Run the test to verify it passes**

Run: `cargo test -p lilo-schedule-core schedule_rpc_round_trips`
Expected: PASS (1 passed). If `lilo-schedule-store` is not yet created, run with
`cargo test -p lilo-schedule-core` only — do not build the whole workspace until Task 3.

- [ ] **Step 6: Commit**

```bash
git add internal/schedule/core Cargo.toml
git commit -m "feat(schedule): scaffold lilo-schedule-core with ScheduleRpc"
```

---

## Task 2: Add the `Schedule` substrate to the wire envelope

**Files:**
- Modify: `internal/wire/Cargo.toml`
- Modify: `internal/wire/src/lib.rs:5-8`

- [ ] **Step 1: Add the dependency**

In `internal/wire/Cargo.toml` `[dependencies]`, add:
```toml
lilo-schedule-core.workspace = true
```

- [ ] **Step 2: Write the failing test** for the envelope tag

Append to `internal/wire/src/lib.rs`:
```rust
#[cfg(test)]
mod schedule_envelope_tests {
    use super::*;

    #[test]
    fn schedule_variant_tags_as_schedule() {
        let env = LilodRpc::Schedule(lilo_schedule_core::ScheduleRpc::SessionGet {
            schedule_session_uid: "ssn_01".to_string(),
        });
        let json = serde_json::to_value(&env).unwrap();
        assert_eq!(json["substrate"], "schedule");
        let back: LilodRpc = serde_json::from_value(json).unwrap();
        assert_eq!(env, back);
    }
}
```
If `serde_json` is not already a dev/normal dependency of `internal/wire`, add
`serde_json.workspace = true` under `[dev-dependencies]` in `internal/wire/Cargo.toml`.

- [ ] **Step 3: Run the test to verify it fails**

Run: `cargo test -p lilo-wire schedule_variant_tags_as_schedule`
Expected: FAIL — `no variant named Schedule found for enum LilodRpc`.

- [ ] **Step 4: Add the variant**

In `internal/wire/src/lib.rs`, extend the enum (the `rename_all = "lowercase"` attribute already
renders the new variant's tag as `"schedule"`):
```rust
pub enum LilodRpc {
    Session(lilo_session_core::SessionRpc),
    Runtime(lilo_rm_core::RuntimeRpc),
    Schedule(lilo_schedule_core::ScheduleRpc),
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cargo test -p lilo-wire schedule_variant_tags_as_schedule`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add internal/wire
git commit -m "feat(wire): add Schedule substrate to LilodRpc envelope"
```

---

## Task 3: Create `lilo-schedule-store` skeleton

**Files:**
- Create: `internal/schedule/store/Cargo.toml`
- Create: `internal/schedule/store/src/lib.rs`

- [ ] **Step 1: Write the crate manifest**

`internal/schedule/store/Cargo.toml`:
```toml
[package]
name = "lilo-schedule-store"
version.workspace = true
edition.workspace = true
license.workspace = true
repository.workspace = true
homepage.workspace = true
authors.workspace = true
rust-version.workspace = true
publish = false

[lib]
name = "lilo_schedule_store"
path = "src/lib.rs"

[dependencies]
lilo-db.workspace = true
lilo-schedule-core.workspace = true
sqlx.workspace = true

[lints]
workspace = true
```

- [ ] **Step 2: Write the failing test** for the store skeleton

`internal/schedule/store/src/lib.rs`:
```rust
use sqlx::SqlitePool;

/// SQLite-backed store for schedule topology. Plan 01 ships only the handle;
/// per-table modules and tables land in Plan 02. Mirrors `SqliteStore`
/// (`internal/session/store/src/sqlite.rs:28-31`).
#[derive(Clone)]
pub struct ScheduleStore {
    pool: SqlitePool,
}

impl ScheduleStore {
    /// Build from an explicit pool (test seam).
    pub fn from_pool(pool: SqlitePool) -> Self {
        Self { pool }
    }

    /// Borrow the underlying pool (used by per-table modules in Plan 02).
    pub fn pool(&self) -> &SqlitePool {
        &self.pool
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn schedule_store_builds_from_pool() {
        // Lazy pool: no connection or migration needed for a construction smoke test.
        let pool = SqlitePool::connect_lazy("sqlite::memory:").unwrap();
        let store = ScheduleStore::from_pool(pool);
        let _ = store.pool();
    }
}
```

- [ ] **Step 3: Run the test to verify it passes**

Run: `cargo test -p lilo-schedule-store schedule_store_builds_from_pool`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add internal/schedule/store
git commit -m "feat(schedule): scaffold lilo-schedule-store skeleton"
```

---

## Task 4: Add `LiloDb::schedule_pool()` named accessor

**Files:**
- Modify: `internal/db/src/lib.rs:58-68`

- [ ] **Step 1: Write the failing test** proving the alias shares the single pool

Append to `internal/db/src/lib.rs` (mirror however existing pool tests open a `LiloDb`; if a test
helper such as an in-memory/temp constructor exists, reuse it — match the existing pool-accessor
tests in this file):
```rust
#[cfg(test)]
mod schedule_pool_tests {
    use super::*;

    #[tokio::test]
    async fn schedule_pool_is_the_shared_pool() {
        let db = test_db().await; // same helper the session_pool/runtime_pool tests use
        assert!(std::ptr::eq(db.schedule_pool(), db.session_pool()));
        assert!(std::ptr::eq(db.schedule_pool(), db.runtime_pool()));
    }
}
```
If no `test_db()` helper exists, add the assertion to the existing accessor test that already
constructs a `LiloDb`, rather than introducing a new DB-open path.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cargo test -p lilo-db schedule_pool_is_the_shared_pool`
Expected: FAIL — `no method named schedule_pool found`.

- [ ] **Step 3: Add the accessor** next to the sibling accessors (`internal/db/src/lib.rs:58-68`)

```rust
    /// Schedule substrate pool. A named alias over the single shared pool,
    /// exactly like `session_pool`/`runtime_pool`. Keeps one `data/lilo.db`.
    pub fn schedule_pool(&self) -> &SqlitePool {
        &self.pool
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cargo test -p lilo-db schedule_pool_is_the_shared_pool`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add internal/db
git commit -m "feat(db): add schedule_pool() alias over the shared pool"
```

---

## Final gate

- [ ] **Step 1: Whole-workspace check**

Run: `cargo check --workspace`
Expected: green. Both new crates compile; the envelope and pool accessor resolve.

- [ ] **Step 2: Full test gate**

Run: `just test` (the repo's canonical gate)
Expected: all green, including the four new tests. No existing test changes behavior.

- [ ] **Step 3: Confirm purely-additive**

Run: `git diff --stat main` (or the base branch)
Expected: only the nine files in the File-structure table changed; no edits to session/runtime
behavior, only additive lines in `Cargo.toml`, `wire/src/lib.rs`, and `db/src/lib.rs`.

---

## Self-review (run before handoff)

1. **Spec coverage:** §3.1 envelope + workspace wiring ✓; §2.2 single shared pool ✓. Records,
   tables, migrations are explicitly Plan 02, not here.
2. **Placeholder scan:** the only "match the existing pattern" references point at exact file:line
   anchors (store-open idiom, pool-accessor tests) — concrete, not vague.
3. **Type consistency:** `ScheduleRpc::SessionGet { schedule_session_uid }` is named identically in
   the core crate, the wire test, and the envelope test. `ScheduleStore::from_pool`/`pool` match
   between definition and test.

## Execution handoff

Plan complete. Two execution options:
1. **Subagent-driven (recommended):** one fresh subagent per task, review between tasks.
2. **Inline:** execute the four tasks here with a checkpoint after the final gate.

On completion, Plan 02 (schedule store data model) and Plan 03 (tmux topology verbs) and Plan 04
(runtime-port rehost) unblock and may run in parallel.
