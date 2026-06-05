# littleorgans Postgres Phase 5 Cleanup & Naming Contract

Status: LOCKED (Stuart sign-off 2026-06-07: D1 accepted, D2 = rename + protocol bump, D4 adopted)
Date: 2026-06-07
Author: codebase-analyst (warroom pane `5:3.1`)
Scope: remove SQLite-shaped residue after the Postgres backend cutover is green
Predecessors (same dir):
`littleorgans-postgres-persistence-plan.md` (Phase 5 §444-472),
`littleorgans-postgres-phase-1a-lilo-db-contract.md`,
`littleorgans-postgres-phase-1b-store-boundary-contract.md`,
`littleorgans-postgres-phase-2-backend-contract.md`
Verified against `main` @ `38ca97e` (Phase 2 backend cutover merged, PR #31).

---

## 1. Purpose And Inherited Locked Decisions

### Purpose

Phase 2 cut the functional backend over to Postgres. The SQLite *engine* is gone:
`transition.rs` and `migrations-sqlite` deleted, every store on `PgPool` /
`LiloTransaction`, all dialect SQL migrated, the Phase 2 functional residue gate
at zero. What remains is **purely cosmetic plus a small pocket of dead config**:
module/dir names, error-variant names, one wire-protocol field, doctor output
shape, snapshots, and docs that still say `sqlite`.

Phase 5 finishes the migration by making the source tree *say* what it now *is*:
one Postgres backend behind a backend-neutral store boundary. This is the
"Cleanup AND Naming" phase. It is mostly renames with **no behavior change**,
with two deliberate exceptions that are the "cleanup" half (dead `db_path`
removal §2-E and the now-empty doctor pragma shape §4), both called out for
sign-off.

### Inherited locked decisions (binding on Phase 5)

From plan Phase 0 and the Phase 2 §6 scope boundary:

1. Postgres is the single target backend. No dual-backend abstraction is
   introduced (plan decision 6: no wider DB abstraction until a second backend
   exists). Phase 5 must **not** add a backend-selection trait or feature fork.
2. The public store boundary is already neutral and frozen by 1.b:
   `SessionStore`, `LifecycleStore`, `AuditStore`, `StoreError`. Phase 5 does not
   change these exported names; it cleans the **private impl** behind them.
3. `lilo-im-store` stays publishable and must not depend on `lilo-db`. Its
   boundary is already neutral (`StoreError::Database(#[from] sqlx::Error)`,
   shipped in Phase 2). This is the **in-tree precedent** for every other
   `Sqlite`→? naming choice in this contract (§3).
4. Phase 2 §6 explicitly assigned to **Phase 5**: "Module renames
   (`internal/**/sqlite/` → neutral; `lilo-im-store/src/sqlite/`),
   type/variant renames (`StoreError::Sqlite`, error string "sqlite error"),
   doctor response fields named `sqlite`, snapshots, README/architecture docs."
5. No compatibility aliases for removed names (plan non-goal). No deletion-guard
   tests (plan non-goal: "No new tests that assert removed SQLite names stay
   removed"). Deletion is proven by the diff + green suite + the gate.
6. No DB file lives under `~/.lilo/` — the root `CLAUDE.md` states "no database
   file lives under the tree" and "`LILO_DB_PATH` does not exist". This makes the
   surviving `lilo-paths::db_path()` → `data/lilo.db` chain **dead and wrong**,
   not cosmetic (§2-E).

### The exact rg gate set (acceptance authority)

The plan's Phase 5 acceptance gate, run over the five trees:

```bash
rg "Sqlite|sqlite|SQLite|lilo\.db|PRAGMA|BEGIN IMMEDIATE|sqlite_master" \
   internal crates tests docs README.md
```

**Gate-completeness defect (must fix the gate, see §4 + §7-D4):** this pattern is
case-sensitive on `PRAGMA`, so it **misses** the doctor's `DbPragmas` struct and
its `pragmas:` fields (`journal_mode`, `busy_timeout`, `synchronous`) — real
SQLite-shaped residue that doctor.rs:251 itself defers to "a later phase". Phase
5 must extend the gate to catch it (recommended below). A gate that the residue
can hide from is a falsifiability gap, not an acceptance.

Recommended extended gate (use this as the binding gate):

```bash
rg -i "sqlite|lilo\.db|\bpragma|DbPragmas|begin immediate|sqlite_master|rusqlite" \
   internal crates tests docs README.md
```

Gate scope is exactly `internal crates tests docs README.md`. Out-of-scope
trees (`NOTES/`, root `CHANGELOG.md`, `~/.mdx`, git history, cm) are the
legitimate historical homes and are **not** scanned (§6).

---

## 2. Full Classified Survey

68 hits in the literal gate across ~40 files (verified @ `38ca97e`). Every hit
is classified into one of eight buckets: rename target, dead-code removal, or
allowlist. Buckets A/B/C/D/G are renames; E is removal; F is the gate-blind
doctor residue; H is the allowlist.

### Bucket A — Private impl module renames (`sqlite` → `postgres`, locked §3/D1)

Each store crate has a module-root file `sqlite.rs` **and** a `sqlite/` dir; both
move. External (cross-crate) blast radius is exactly **one line**
(identity client.rs:7); everything else is the crate's own `pub mod`/`pub use`.

| File / dir | Hit(s) | Action |
|---|---|---|
| `internal/session/store/src/sqlite.rs` + `sqlite/` (events, labels, mail, mail_tests, namespaces, sessions, sessions_tests, spawn_intents, test_support) | dir move | rename `sqlite.rs`+`sqlite/` → `postgres.rs`+`postgres/` |
| `internal/session/store/src/lib.rs` | :3 `pub mod sqlite;`, :9 `pub use sqlite::{` | update mod + re-export path |
| `internal/runtime/store/src/sqlite.rs` + `sqlite/` (lifecycle.rs, lifecycle/codec.rs, lifecycle/tests.rs) | dir move | rename `sqlite.rs`+`sqlite/` → `postgres.rs`+`postgres/` |
| `internal/runtime/store/src/lib.rs` | :3 doc "Durable `SQLite` lifecycle state", :10 `pub mod sqlite;`, :13 `pub use sqlite::LifecycleStore;` | rewrite doc + mod + re-export |
| `crates/lilo-im-store/src/sqlite/audit.rs` + `sqlite/` | dir move | rename `sqlite/` → `postgres/` |
| `crates/lilo-im-store/src/lib.rs` | :17-19 transition comment, :20 `pub mod sqlite;`, :25 `pub use sqlite::{AuditFilters, AuditStore, AuditTableColumn, StoreError};` | drop comment, update mod + re-export |
| `internal/identity/service/src/client.rs` | :7 `use lilo_im_store::sqlite::record_audit_in_tx;` | **only cross-crate importer** — update path |

No intra-crate `crate::sqlite::` / `super::sqlite` references exist (verified), so
the dir move plus the `pub mod`/`pub use` edits are the whole change per crate.

### Bucket B — Error-variant renames (`Sqlite` → `Database`, §3)

`sqlx::Error` is backend-agnostic; im-store already names this wrapper
`Database`. Session store's four sibling row-error enums must match.

| File:line | Hit | Rename to |
|---|---|---|
| `internal/session/store/src/sqlite/namespaces.rs:22` | `Sqlite(#[from] sqlx::Error)` | `Database(#[from] sqlx::Error)` |
| `internal/session/store/src/sqlite/sessions.rs:20` | `Sqlite(#[from] sqlx::Error)` | `Database(...)` |
| `internal/session/store/src/sqlite/mail.rs:16` | `Sqlite(#[from] sqlx::Error)` | `Database(...)` |
| `internal/session/store/src/sqlite/mail.rs:71` | `MailRowError::Sqlite(error)` | `MailRowError::Database(error)` |
| `internal/session/store/src/sqlite/spawn_intents.rs:19` | `Sqlite(#[from] sqlx::Error)` | `Database(...)` |

`crates/lilo-im-store/src/sqlite/audit.rs:20` `StoreError::Database` — **already
correct, no change** (precedent source).

### Bucket C — Protocol/doctor field rename (`sqlite: MigrationState` → `migrations`) [LOCKED: D2 = rename + bump]

One serde field on the rtmd `DoctorResponse` (`lilo-rm-core`), consumed across
five crates. Renaming the definition breaks every consumer simultaneously →
**atomic slice** (§8). It is a wire-protocol JSON key; pre-release + smd↔rtmd in
lockstep make it safe. **Stuart locked D2 = rename + bump** (2026-06-07): rename
the field **and** bump `RUNTIME_PROTOCOL_VERSION` 0.7→0.8 (version.rs:8) as paired
hard steps. Bucket C is **unblocked**.

| File:line | Role |
|---|---|
| `crates/lilo-rm-core/src/admin.rs:214` | **canonical def** `pub sqlite: MigrationState,` on `DoctorResponse` |
| `crates/lilo-rm-core/src/cli_output.rs:58,62,63,64,66,70` | human render of the field |
| `crates/lilo/src/cli/doctor/runtime.rs:61,63,64,132,212,232` | reads `.sqlite.pending_descriptions` + test |
| `internal/session/daemon/src/polish.rs:209,211,212` | reads `.sqlite.pending_descriptions` (drift check) |
| `internal/session/driver/src/conv.rs:207,363` | reads + re-constructs `sqlite: MigrationState` |
| `internal/runtime/daemon/src/doctor.rs:21` | constructs `sqlite: state.store().migration_state()...` |
| `crates/lilo-rm-core/tests/support/mod.rs:53` | test constructor |
| `crates/lilo-rm-client/tests/typed_helpers.rs:265` | test constructor |
| `internal/session/daemon/tests/common/mod.rs:447` | test constructor |
| `internal/session/app/tests/runtime_contract_snapshot_test.rs:117` | test constructor |
| `crates/lilo-rm-core/README.md:45` | documents `sqlite.applied` / `.total` / `.applied_descriptions` / `.pending_descriptions` |

### Bucket D — Snapshot regeneration (insta + mcp)

These regenerate automatically once Buckets C/F/G land; they are listed so the
regen step is verifiable, not hand-edited (generated-surface rule).

| File:line | Source of the hit |
|---|---|
| `crates/lilo-rm-core/tests/snapshots/serde_snapshots__runtime_response_json_shapes_are_stable.snap:265` | `"sqlite": {` ← Bucket C |
| `internal/runtime/app/tests/snapshots/surface_snapshots__doctor_json_response_is_stable.snap:51` | `"sqlite": {` ← Bucket C |
| `internal/runtime/app/tests/snapshots/surface_snapshots__doctor_output_is_stable.snap:12` | human `sqlite` ← Bucket C |
| `internal/runtime/app/tests/snapshots/surface_snapshots__session_facing_cli_json_outputs_are_stable.snap:63` | `"sqlite": {` ← Bucket C |
| `internal/session/app/tests/snapshots/runtime_contract_snapshot_test__rtmd_payload_json_shapes_are_snapshotted.snap:75` | `"sqlite": {` ← Bucket C |
| `crates/lilo-im-core/tests/snapshots/core_snapshots__authz_error_display.snap:7` | `audit sink failed: sqlite unavailable` ← test string in `core_snapshots.rs:13` (Bucket G) |

### Bucket E — Dead `db_path` / `lilo.db` / `StoreConfig` removal (NOT rename) [SIGN-OFF §9 D3, behavior-affecting]

**Verified dead:** the runtime store is built by `LifecycleStore::from_db(&LiloDb)`
(`internal/runtime/store/src/sqlite/lifecycle.rs:54`) from an already-open
`PgPool`; the pool is opened via `LiloDb::open_postgres_resolved()`
(`internal/db/src/lib.rs:65-67`) from `LILO_DATABASE_URL`/settings. `db_path` is
**set but never opens a database**. Its **only live read** is
`DaemonConfig::data_dir()` (`server/config.rs:81-86`) taking `db_path.parent()` to
locate the event-log dir — a derivation that must be replaced with a real
data-root, not preserved.

**Removal is behavior-safe (verified):** `data_dir()` returns
`db_path.parent()`, and `db_path = LiloPaths::db_path() = data_root().join("lilo.db")`,
so `data_dir()` is exactly `data_root()` today. Its sole consumer is
`EventLog::open(config.data_dir())` (`internal/runtime/daemon/src/server/state.rs:67`)
plus a test harness (`integration_events_cursor.rs:343`). Carrying an explicit
`data_root` field on `DaemonConfig` (set to `paths.data_root()` in prod, and to
the former `db_path.parent()` in each test fixture) yields a **path-identical**
event-log dir. The `map_or_else(|| self.log_root.clone(), ...)` fallback never
fired (the path always had a parent), so dropping it changes nothing. This is a
removal of dead code plus a path-preserving derivation swap, not a behavior
change.

| File:line | Hit | Action |
|---|---|---|
| `crates/lilo-paths/src/lilo.rs:104` | `db_path()` → `data_root().join("lilo.db")` | **remove** `db_path()` method |
| `crates/lilo-paths/src/lilo.rs:218,314` | default + assertion in tests | remove (test of removed method) |
| `internal/runtime/store/src/config.rs:8,14` | `StoreConfig { db_path }` + `from_env` | remove field; if `StoreConfig` becomes empty, **delete the struct** and its uses |
| `internal/runtime/daemon/src/server/config.rs:34` | `db_path: paths.db_path()` | remove |
| `internal/runtime/daemon/src/server/config.rs:56` | `db_path: PathBuf::from("/tmp/rtm.db")` (test fixture; not in gate but same dead field) | remove |
| `internal/runtime/daemon/src/server/config.rs:81-86` | **the only LIVE read** — `data_dir()` from `db_path.parent()` | replace with explicit data-root (`paths.data_root()` carried on `DaemonConfig`); path-identical (see behavior-safety note above) |
| `tests/integration/src/lib.rs:60-67` | `runtime_config()` builds `DaemonConfig { store: StoreConfig { db_path: paths.db_path() } }` | remove `store`/`db_path`; set the new `data_root` field to the test's data root |
| `crates/lilo-rm-client/tests/common/daemon.rs:45` | `db_path: tempdir...join("rtm.sqlite")` | remove |
| `internal/runtime/daemon/src/reconcile/tests.rs:307` | `db_path: root.join("rtm-test.sqlite")` | remove |
| `internal/runtime/daemon/src/spawn_preflight/tests/helpers.rs:81` | `db_path: temp.join("rtm.sqlite")` | remove |
| `internal/runtime/daemon/src/server/tests.rs:177` | `db_path: temp.path().join("rtm.sqlite")` | remove |
| `internal/runtime/daemon/src/handler/tests.rs:176`, `test_support.rs:24` | `db_path: paths.db_path()` | remove (coupled to method removal) |

Removing `db_path` is genuinely the "cleanup" half of Phase 5 and changes the
data-dir derivation (behavior-safe per the note above). It is in scope (plan:
"remove SQLite-shaped residue") but touches code shape, so it is a sign-off item.
**DRY note:** decide the data-root seam once on `DaemonConfig` so every fixture
that currently hand-sets `db_path` (the seven listed above, including the
`tests/integration` and `server/config.rs:56` fixtures) stops constructing a
path. **Completeness:** the removal must cover BOTH the integration fixture
(`tests/integration/src/lib.rs:60-67`) and the live `data_dir()` read
(`server/config.rs:81-86`); neither is optional, or the workspace will not
compile after `db_path()` is deleted.

### Bucket F — Doctor `DatabaseHealth` SQLite-shaped output (gate-BLIND) [SIGN-OFF §9 D3]

All in `crates/lilo/src/cli/doctor.rs`. doctor.rs:251 comment: "Renaming this
struct and the doctor's `pragmas:` line is a later phase." Against Postgres the
pragma probe is a vestigial `SELECT 1` returning `DbPragmas::default()` — the
fields are **always empty**, so the doctor reports dead SQLite shape.

| Line(s) | Hit | Note |
|---|---|---|
| `:194` | `path: String` on `DatabaseHealth` | db **file** path; meaningless for Postgres (no file). Caught by gate via `:208`/`:435`/`:466`. |
| `:208` | `let path = paths.db_path();` | breaks when `db_path()` removed (Bucket E) — couple these slices |
| `:435,466` | `path: "/tmp/lilo.db"` test fixtures | matches gate (`lilo.db`) |
| `:243-247` | `struct DbPragmas { journal_mode, busy_timeout, synchronous }` | **gate-blind** (lowercase) — always-empty SQLite shape |
| `:87,93-95,197,211,212,222,230,238,249,251,364,437,468` | `DbPragmas` / `pragmas:` field + render + tests | gate-blind |

### Bucket G — Docs / comments / test-string sweep

| File:line | Hit | Action |
|---|---|---|
| `docs/architecture/runtime.md:66,113,160` | "SQLite lifecycle state", "rows in SQLite", "Internal SQLite lifecycle store" | rewrite → Postgres |
| `docs/architecture/session.md:76,129,131,190` | "SQLite session state", "owns SQLite persistence", "rusqlite boundary", "Internal SQLite store" | rewrite → Postgres (the `Phase 4`/`Phase 7` refs are monorepo-migration phases, keep numbering but fix the SQLite claim) |
| `internal/session/app/README.md:24`, `internal/session/app/src/tool_docs.rs:31` | `~/.lilo/data/lilo.db` in operator + MCP tool docs | remove the DB-file mention (no file exists); tool_docs change → **regen the mcp snapshot** |
| `internal/db/src/lib.rs:122` | doc comment "The `SQLite` ..." | rewrite |
| `internal/db/migrations/0001_unified_schema.sql:11` | "replaces the SQLite implicit rowid" | rewrite comment without SQLite contrast |
| `crates/lilo-im-store/src/sqlite/audit.rs:218` | "Postgres has no SQLite rowid" | rewrite comment |
| `crates/lilo-im-core/tests/core_snapshots.rs:13` | test string `"sqlite unavailable"` | → `"database unavailable"` (+ regen snap, Bucket D) |
| `internal/runtime/app/tests/integration_pass7.rs:39` | `assert!(doctor.contains("sqlite"))` | update assertion to the new field name (`migrations`) |
| `internal/runtime/app/tests/integration_pass4.rs:19` | `fn pass4_restart_reconciles_sqlite_lifecycles()` | rename test fn (drop `sqlite`) |

### Bucket H — Allowlist (legitimate historical, keep) — §6

Within the gate scope, the allowlist is **currently empty**: no in-scope file
holds a legitimate historical SQLite note today (every in-scope hit is either
residue to rename or dead code to remove). See §6 for the reserved members and
the out-of-scope historical homes.

---

## 3. Naming Convention Decision (LOCKED — Stuart 2026-06-07, D1)

The question is only about **private impl** names (the public boundary is
neutral and frozen). The fork was: ex-`sqlite` impl modules/types → `postgres`-named
(honest, single backend) vs neutral. **Stuart locked the split below.**

### LOCKED convention: split by what the thing *is*

**Name impl modules after the backend; name backend-agnostic surfaces after
their domain concept.** Concretely:

1. **Impl module dirs/files → `postgres`** (`internal/session/store/src/sqlite/`
   → `.../postgres/`, same for runtime store and `lilo-im-store`).
   Rationale: their bodies contain Postgres-dialect SQL (`ON CONFLICT`,
   `timestamptz`, `$1` placeholders, `RETURNING`). The plan commits to Postgres
   as the sole backend with no speculative abstraction (decision 6), so the
   module *is* Postgres. This mirrors `sqlx::postgres` and reads honestly. A
   neutral dir name (`db`/`backend`/`store`) is ambiguous: `db` collides with the
   `lilo-db` boundary vocabulary, and `store` is redundant inside `*-store`
   crates.

2. **Backend-agnostic surfaces → neutral domain name**, matching the existing
   in-tree precedent:
   - Error variant `Sqlite(#[from] sqlx::Error)` → **`Database`** (wraps the
     agnostic `sqlx::Error`; im-store already chose `Database` in Phase 2 — Phase
     5 must not introduce a *second*, conflicting label).
   - Doctor protocol field `sqlite: MigrationState` → **`migrations`** (the value
     is a `MigrationState`; name it after the value).

The unifying principle — *name each thing after what it is* — makes the split
non-arbitrary: a module of Postgres SQL is `postgres`; an error wrapping
`sqlx::Error` is `Database`; a field holding `MigrationState` is `migrations`.
Naming the agnostic surfaces `Postgres` would be exactly as arbitrary as `Sqlite`
was, and would fork the convention away from the shipped `StoreError::Database`.

### Alternative considered and rejected

Fully neutral for the modules too (`sqlite/` → `db/` or `backend/`). Pro: never
re-encodes a backend name, so the names never lie if a second backend ever lands.
Con: contradicts the plan's "no speculative abstraction" stance, and every
neutral module name is ambiguous against `lilo-db`/`*-store`. Cost is identical
(both are mechanical renames). **Rejected by Stuart (2026-06-07): D1 = `postgres`
for impl modules.**

---

## 4. Protocol / Doctor Field Renames + Snapshot-Regen Plan

### Field renames

- **rtmd `DoctorResponse.sqlite` → `migrations`** (Bucket C). This **crosses the
  runtime protocol** (confirmed): the field is defined on `DoctorResponse`
  (`crates/lilo-rm-core/src/admin.rs:210-214`) and carried on the wire by
  `proto.rs:217-219 DoctorPayload { doctor: DoctorResponse }` →
  `RuntimeResponse::Doctor(DoctorPayload)` (`crates/lilo-rm-core/src/proto.rs`,
  the `#[serde(tag="type", content="payload")]` response enum). Because smd↔rtmd
  compat is gated on the protocol **minor** (root `CLAUDE.md`: "smd requires rtmd
  at the compatible minor"), this rename **REQUIRES a `RUNTIME_PROTOCOL_VERSION`
  bump as a hard step** — `crates/lilo-rm-core/src/version.rs:8` is currently
  `"0.7"` and must move to the next minor (e.g. `"0.8"`). It is safe to do
  (pre-release, zero external users, smd+rtmd ship in lockstep from the
  monorepo), but the bump is non-optional and paired with the rename.
  **LOCKED (Stuart, 2026-06-07): D2 = rename + bump.** The field rename and the
  `RUNTIME_PROTOCOL_VERSION` 0.7→0.8 bump (version.rs:8) are paired hard steps in
  the Bucket C atomic slice. Bucket C is unblocked.
- **doctor `DatabaseHealth` shape** (Bucket F): the `path` (db file) and
  `DbPragmas { journal_mode, busy_timeout, synchronous }` fields are now
  dead/always-empty SQLite shape. Two options (**Sign-Off Item D3**):
  - *Minimal rename:* keep the shape, rename the struct/field (least churn, but
    keeps always-empty SQLite-named fields in the JSON — dishonest output).
  - *Recommended minimal redesign:* drop `DbPragmas` (always default), replace
    `path: String` (file) with a Postgres-appropriate neutral label (e.g. a
    redacted `target`/host or simply rely on `status`). This is the honest
    Phase-5 cleanup and removes the gate-blind residue at the source. It nudges
    the Phase 3/Phase 5 seam (doctor *semantics*), so it needs explicit sign-off;
    if rejected, fall back to minimal rename + extend the gate to police it.

### Snapshot-regen plan (no hand-editing — generated-surface rule)

1. Land the code renames (Buckets C/F/G).
2. Regenerate insta snapshots: `cargo insta test --review` then accept, or
   `INSTA_UPDATE=always cargo nextest run -p lilo-rm-core -p lilo-runtime-app
   -p lilo-session-app -p lilo-im-core` followed by `cargo insta accept`. The six
   `.snap` files in Bucket D are the expected diffs.
3. Regenerate the **mcp tool-docs snapshot** affected by `tool_docs.rs:31`
   (`runtime_contract_snapshot_test` / session-app surface snapshots) the same
   way; do not edit `.snap` by hand.
4. Commit the regenerated snapshots in the same slice as their source rename so
   the suite is green at slice exit.

---

## 5. Docs / README / Architecture Sweep

Bucket G covers it. Summary:

- `docs/architecture/{runtime,session}.md`: replace every "SQLite" persistence
  claim with Postgres; remove the "rusqlite boundary" phrase. Keep the
  monorepo-migration `Phase N` numbering (that is a different axis from these
  Postgres phases) — only the backend noun is wrong.
- `docs/{provenance,reference}/`: clean (no hits).
- Root `README.md`: clean (no hits) — no action.
- Per-component READMEs: `internal/session/app/README.md` (drop `lilo.db` file
  mention), `crates/lilo-rm-core/README.md` (rename the documented `sqlite.*`
  field paths to `migrations.*` alongside Bucket C).
- In-code doc comments + the migration-file comment: rewrite to drop the SQLite
  contrast (`internal/db/src/lib.rs`, `internal/runtime/store/src/lib.rs`,
  `0001_unified_schema.sql`, `lilo-im-store audit.rs`).

---

## 6. Approved-Historical-Notes Allowlist

The gate must reach **zero** in `internal crates tests README.md`. For `docs/`
the target is also zero today. The allowlist exists so the gate is not fooled by
*legitimate* migration history, but that history lives almost entirely
**outside** the gate scope and is therefore exempt by construction:

Out-of-scope historical homes (gate does not scan — keep as-is):

- **git history** (the cutover diff is the record).
- **root `CHANGELOG.md`** — not in `internal/crates/tests/docs/README.md`; the
  git-cliff Postgres-cutover entry ("cut over from SQLite to Postgres") lives
  here safely.
- **`NOTES/`** design docs: `v1-v2-strategy.md`, `transport-integration.md`
  (transport's *own separate* SQLite index under `~/.lilo/capture/` — a different,
  legitimately-SQLite component, must not be "fixed"), `typed-ids-and-v4-prefix.md`,
  `openprose-reactor-primitives.md`.
- **`~/.mdx/projects/littleorgans-postgres-*`**: this plan + the 1.a/1.b/2/5
  contracts.
- **cm decision/lesson ids** (provenance): Phase 2 landing lesson
  `019e9f12-5efb-7f32-a0a0-ce437b8c498f`; release decision
  `019e939c-c190-7423-b63a-acb85cab7069`; MoE-warroom-consensus
  `019e5dbb-53e6-7ae3-b842-cfaba18fe690`.

Reserved in-scope allowlist members (currently none exist; bless only if they
land):

- `crates/*/CHANGELOG.md` — per-crate git-cliff entries describing the cutover
  may legitimately say "SQLite". Currently clean (verified). If a cutover entry
  lands before Phase 5 closes, add the specific changelog path to the gate's
  allowlist (e.g. `--glob '!crates/*/CHANGELOG.md'`).
- An optional `docs/adr/NNNN-postgres-migration.md` if the team chooses to record
  the migration as an ADR. If created, it is the single in-scope file allowed to
  say "SQLite", and it must be the only allowlist entry.

**`NOTES/typed-ids-and-v4-prefix.md:136,139` housekeeping:** that note cites
`internal/runtime/store/src/sqlite/lifecycle.rs:159` and
`internal/session/store/src/sqlite/mail.rs:221,486` by path. The Bucket A module
rename makes those path references stale. NOTES/ is out of gate scope, so this is
optional, but update the two path citations when the modules move to keep the
note navigable.

---

## 7. Acceptance

All must hold at phase exit. Run the **extended** gate (§1) as the binding one.

### A. Residue gate → zero (or allowlist-only)

```bash
# binding extended gate (catches DbPragmas the literal gate misses)
rg -i "sqlite|lilo\.db|\bpragma|DbPragmas|begin immediate|sqlite_master|rusqlite" \
   internal crates tests docs README.md
# expected: no output, OR only an explicitly-allowlisted CHANGELOG/ADR path (§6)

# the plan's literal gate must also be zero/allowlist-only
rg "Sqlite|sqlite|SQLite|lilo\.db|PRAGMA|BEGIN IMMEDIATE|sqlite_master" \
   internal crates tests docs README.md
```

### B. fmm navigation refreshed (files/symbols moved)

```bash
fmm generate && fmm validate   # green; index reflects renamed modules
```

### C. Full suite green, both DB modes

```bash
# functional proof against Postgres (compose up; host port per justfile)
docker compose up -d postgres
cargo nextest run --workspace --run-ignored ignored-only   # 0 failed (DB tests)
# honest no-DB run: DB-gated tests skip, nothing red
cargo nextest run --workspace                               # 0 failed
```

### D. Operator gates

```bash
just check && just build
```

### E. Concrete contract proof (verify the user-visible surface directly)

```bash
# rtmd doctor JSON key is `migrations`, not `sqlite`
LILO_DATABASE_URL=postgres://... cargo run -p lilo -- doctor --json | rg '"migrations"'
LILO_DATABASE_URL=postgres://... cargo run -p lilo -- doctor --json | rg -v '"sqlite"'
# doctor no longer prints SQLite pragma shape (if D3 redesign accepted)
```

### Anti-requirements (plan non-goals)

- No new test asserting a removed `sqlite` name stays removed (deletion proven by
  diff + green suite + gate).
- No compatibility alias / re-export for any renamed module, type, variant, or
  field.

---

## 8. File-By-File Plan, Blast Radius, Slicing

### Blast radius summary

- **Module renames (A):** ripple only through each crate's own `lib.rs` re-exports
  plus **one** cross-crate import (`identity/service/client.rs:7`). No intra-crate
  `crate::sqlite::` references. Smallest blast radius of the lot.
- **Error variants (B):** contained to `internal/session/store` + any matcher on
  the variant (only `mail.rs:71` in-crate). Contained.
- **Protocol field (C):** widest — one def in `lilo-rm-core` fans out to 5 crates
  + 4 test constructors + 6 snapshots + 1 README. Renaming the def is a
  compile-break for all consumers → **must be atomic**.
- **Dead db_path (E):** `lilo-paths` def → runtime store config → runtime daemon
  config + `data_dir()` derivation + 6 test fixtures + doctor.rs:208. Removing
  the method is a compile-break for all callers → atomic within this cluster.
- **Doctor (F):** contained to `crates/lilo` doctor.rs + its snapshots, but
  coupled to E via `doctor.rs:208`.

### Recommended slicing — sliceable per crate, with two forced-atomic clusters

Phase 5 is **mostly sliceable per crate** because module renames are crate-local.
Two clusters are forced atomic by shared definitions (C; E). Recommended order:

1. **Slice 1 — session store** (A session + B): rename `sqlite.rs`/`sqlite/` →
   `postgres/`, fix `lib.rs` re-exports, rename the four `Sqlite`→`Database`
   variants. Self-contained in `internal/session/store` + its tests.
2. **Slice 2 — runtime store** (A runtime): rename module, fix `lib.rs` +
   doc comment; rename `integration_pass4` test fn (G). Self-contained.
3. **Slice 3 — im-store + identity** (A im-store): rename module, fix `lib.rs`
   re-export + drop transition comment, update `identity/service/client.rs:7`.
4. **Slice 4 — doctor protocol field + doctor cleanup** (C + E + F + docs/README
   for these): atomic. Rename `DoctorResponse.sqlite` → `migrations` across all
   consumers; remove dead `db_path`/`StoreConfig` and rework `data_dir()`; redesign
   `DatabaseHealth`/`DbPragmas` (per D3); regen all doctor/serde/surface snapshots
   **once** here. Bundling C+E+F means the doctor snapshots regenerate a single
   time instead of twice.
5. **Slice 5 — docs + comments sweep + final gate** (remaining G): architecture
   docs, in-code doc comments, migration-file comment, README field-path doc;
   run the binding gate + `fmm generate && fmm validate` + full suite as the
   close-out proof.

Each of slices 1-3 is an independent PR-sized change; 4 is the one large atomic
change; 5 is the verification close-out. **Alternative:** a single atomic PR is
also defensible given the pre-release status and small total size, and it regens
every snapshot exactly once — but it loses per-crate reviewability. Recommend the
5-slice sequence unless the orchestrator prefers one PR to minimize snapshot
churn.

### Why not fully atomic-everything

The module renames (1-3) have near-zero cross-crate blast radius and benefit from
small, independent review. Forcing them into Slice 4 would bloat one PR with
unrelated mechanical moves. Keep them separate; reserve atomicity for the surfaces
that genuinely share a definition.

---

## 9. Sign-Off Items (resolved — Stuart 2026-06-07)

- **D1 — impl module naming: LOCKED = `postgres`.** Bucket A impl module
  dirs/files (`sqlite/` → `postgres/`) take the backend name; agnostic surfaces
  stay neutral (`StoreError::…::Database`, doctor field `migrations`). The naming
  split in §3 is the binding convention.
- **D2 — protocol field rename: LOCKED = rename + bump.** `DoctorResponse.sqlite`
  → `migrations` (admin.rs:214 def, carried via `proto.rs DoctorPayload` /
  `RuntimeResponse::Doctor`) **paired with** a `RUNTIME_PROTOCOL_VERSION` minor
  bump `0.7` → `0.8` (version.rs:8). Both are hard steps in the Bucket C atomic
  slice. Bucket C is unblocked.
- **D4 — gate completeness: LOCKED = extended case-insensitive gate.** The
  binding gate is the §1/§7-A extended pattern (`-i`, incl. `DbPragmas`,
  `rusqlite`, `\bpragma`), so the doctor residue cannot hide from acceptance.
- **D3 — doctor `DatabaseHealth` shape: implementer's choice within the lock
  (non-blocking).** Not separately adjudicated by Stuart; contained entirely to
  the doctor slice (Slice 4) and to doctor output, so it does not gate the lock.
  Standing recommendation: **redesign** — drop the always-empty `DbPragmas` and
  the file-path `path` field rather than ship empty SQLite-shaped output. Fallback
  if the redesign expands scope: minimal rename, with the D4 extended gate
  policing the residue. Either way the field names leave the gate clean.
- **Behavior note:** Buckets E (dead `db_path` removal + `data_dir()` rework,
  proven path-identical in §2-E) and the D3 doctor cleanup are the only
  behavior-touching items; everything else is a pure rename. Both are the
  "Cleanup" half of Phase 5 and the residue is dead/dishonest, not load-bearing.

---

## Appendix: Survey Evidence (verified @ `38ca97e`)

- Gate hit count (literal gate, `internal crates tests docs README.md`): **68**
  across ~40 files.
- Gate-blind residue (lowercase `pragmas`/`DbPragmas`, `crates/lilo/src/cli/doctor.rs`):
  ~18 additional sites, deferred by the in-code comment at doctor.rs:251.
- `db_path` liveness: dead. Pool opened via `LiloDb::open_postgres_resolved()`
  (`internal/db/src/lib.rs:65`); store built via `LifecycleStore::from_db(&LiloDb)`
  (`internal/runtime/store/src/sqlite/lifecycle.rs:54`); only live `db_path` read
  is `data_dir()` parent-derivation (`server/config.rs:83`).
- im-store error wrapper already neutral (`StoreError::Database`,
  `crates/lilo-im-store/src/sqlite/audit.rs:20`) — the convention precedent.
- Module-rename cross-crate blast radius: one line
  (`internal/identity/service/src/client.rs:7`); no intra-crate `crate::sqlite::`.
- Out-of-scope trees (`NOTES/`, root `CHANGELOG.md`, per-crate CHANGELOGs)
  currently clean of new-residue except legitimate `NOTES/` design history (§6).
