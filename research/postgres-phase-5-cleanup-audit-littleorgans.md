---
title: Postgres Phase 5 Cleanup Audit for littleorgans
type: research
tags: [littleorgans, postgres, cleanup, runtime-protocol, doctor, db-path, audit]
summary: Final implementation audit verified the Phase 5 cleanup claims, but found an unrelated local scheduler lock file committed on the branch.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Executive Summary

`feat/postgres-phase-5` implements the locked Phase 5 Postgres cosmetic cleanup over six commits. The core cleanup claims verified cleanly: the extended SQLite gate is zero, implementation modules use `postgres`, neutral surfaces use `Database` or `migrations`, the runtime doctor wire rename is paired with protocol `0.8`, dead `StoreConfig` and `db_path` are gone, and the top level doctor database probe is reduced to `{status,error}`.

The only substantive issue found in the final branch diff is unrelated diff contamination: `.claude/scheduled_tasks.lock:1` commits a local scheduler lock containing a session id, PID, process start time, and acquisition timestamp. Remove that file before merge. After removal, the Phase 5 code claims are sound.

## Project Metadata

- Language: Rust, workspace edition 2024.
- Branch audited: `feat/postgres-phase-5`.
- Merge base: `main` at `38ca97e`.
- Diff scope: 6 commits, 64 files, 127 insertions, 229 deletions.
- Workspace version: `0.8.0`.
- fmm coverage on audited tree: 388 indexed files, 58,309 LOC. Buckets: `internal/` 298 files, `crates/` 85 files, `tests/` 4 files, `tools/` 1 file.
- Build system: Cargo plus root `just` targets and Moon CI.
- Critical dependencies: `sqlx` with Postgres, `tokio`, `serde`, `serde_json`, `insta`, `thiserror`, `anyhow`, `uuid`.

## Architecture

- `crates/lilo-rm-core` owns runtime protocol types, including `DoctorResponse`, `DoctorPayload`, `RuntimeResponse`, `VersionInfo`, and `RUNTIME_PROTOCOL_VERSION`.
- `crates/lilo-rm-client` owns typed runtime client helpers and protocol version expectations.
- `internal/runtime/daemon` builds `DaemonConfig`, runtime state, and daemon doctor payloads.
- `internal/runtime/store`, `internal/session/store`, and `crates/lilo-im-store` own concrete Postgres store implementations behind narrow APIs.
- `crates/lilo` owns top level `lilo doctor` output and the database health probe.
- `internal/db` is the actual Postgres open and migration path. Runtime store code receives an already opened `LiloDb` or `PgPool`, so removed `db_path` state was not used to open the database.

## Key Patterns

- Wire shape changes require a protocol version bump. `DoctorResponse.migrations` travels through `DoctorPayload` into `RuntimeResponse::Doctor`, so the `sqlite` to `migrations` rename is correctly paired with `RUNTIME_PROTOCOL_VERSION = "0.8"`.
- Concrete implementation modules now use backend names, while public surfaces remain neutral. Examples: `postgres.rs` and `postgres/` modules, `StoreError::Database`, `MailRowError::Database`, and `DoctorResponse.migrations`.
- Dead path removal is behavior preserving because the previous live read was `db_path.parent()`. Since old `db_path()` was `data_root().join("lilo.db")`, the replacement `data_root` is path identical for real config and the updated fixtures.
- Gate design must search both names and semantic residue. The final gate includes lowercase `pragma`, `DbPragmas`, `rusqlite`, `lilo.db`, and engine names with `-i`, which catches doctor residue that the original case sensitive gate missed.

## Detailed Findings

### Diff scope and issue

`git log --oneline main..feat/postgres-phase-5` shows the expected six commits:

- `351146c` store implementation module rename.
- `2d4df1d` `StoreError::Sqlite` to `Database`.
- `0d8a5e0` runtime doctor protocol rename plus protocol bump.
- `447e067` dead `db_path` and doctor health cleanup.
- `ca761f4` docs, comments, and fixture naming sweep.
- `f5fa293` real daemon protocol assertion follow up.

The branch also adds `.claude/scheduled_tasks.lock`, which is outside the Phase 5 contract. Line 1 contains local process state:

- `.claude/scheduled_tasks.lock:1`: JSON with `sessionId`, `pid`, `procStart`, and `acquiredAt`.

This should be removed from the branch before merge.

### Claim 1: extended zero SQLite gate passed

Command reproduced over `internal`, `crates`, `tests`, `docs`, and `README.md`:

```bash
rg -n -i "sqlite|lilo\.db|\bpragma|DbPragmas|begin immediate|sqlite_master|rusqlite" internal crates tests docs README.md
```

Result: exit status `1`, no matches. The older case sensitive gate also returned no matches:

```bash
rg -n "Sqlite|sqlite|SQLite|lilo\.db|PRAGMA|BEGIN IMMEDIATE|sqlite_master" internal crates tests docs README.md
```

Result: exit status `1`, no matches. `find internal crates tests docs -path '*sqlite*'` also returned no paths.

### Claim 2: D1 naming is consistent

Implementation modules were renamed to `postgres` and neutral surfaces stayed neutral:

- `internal/session/store/src/lib.rs:3` declares `pub mod postgres`; `:9-11` reexports from `postgres`.
- `internal/runtime/store/src/lib.rs:3` documents durable Postgres lifecycle state; `:8` declares `pub mod postgres`; `:11` reexports `LifecycleStore`.
- `crates/lilo-im-store/src/lib.rs:17-23` exposes the concrete backend under the `postgres` feature and reexports `StoreError` from `postgres`.
- `internal/identity/service/src/client.rs:7` imports `lilo_im_store::postgres::record_audit_in_tx`.
- `internal/session/store/src/postgres/mail.rs:14-29` defines `MailRowError` with `Database(#[from] sqlx::Error)` at `:16`.
- `internal/session/store/src/postgres/namespaces.rs:20-33`, `sessions.rs:17-40`, and `spawn_intents.rs:16-34` use `Database` row error variants.
- `crates/lilo-im-store/src/postgres/audit.rs:20-29` defines `StoreError::Database`.

fmm dependency graphs for the three store crate roots show local dependencies on `postgres` modules only.

### Claim 3: D2 protocol rename and version bump are complete

The canonical runtime doctor payload was renamed and the protocol version was bumped:

- `crates/lilo-rm-core/src/admin.rs:210-227` defines `DoctorResponse`; line `214` is `pub migrations: MigrationState`.
- `crates/lilo-rm-core/src/proto.rs:217-219` wraps it in `DoctorPayload`.
- `crates/lilo-rm-core/src/proto.rs:260-280` carries `RuntimeResponse::Doctor(DoctorPayload)`.
- `crates/lilo-rm-core/src/version.rs:8` sets `RUNTIME_PROTOCOL_VERSION` to `"0.8"`.
- `crates/lilo-rm-core/src/version.rs:144-155` updates the version unit assertion to `0.8`.
- `crates/lilo-rm-client/tests/integration_typed_helpers.rs:12` updates the real daemon helper assertion to `0.8`.
- `crates/lilo-rm-client/tests/typed_helpers.rs:265` constructs `DoctorResponse { migrations: ... }`.
- `crates/lilo-rm-core/tests/support/mod.rs:53` constructs `DoctorResponse { migrations: ... }`.
- `crates/lilo-rm-core/tests/snapshots/serde_snapshots__runtime_response_json_shapes_are_stable.snap:264` uses the JSON key `migrations` and protocol `0.8`.
- Runtime app and session app snapshots also changed from `sqlite` to `migrations` and from protocol `0.7` to `0.8`.

No `sqlite` or `Sqlite` wire residue remains under the scoped gate paths.

### Claim 4: Bucket E dead path removal is behavior preserving

`StoreConfig` and `db_path` residue is gone:

```bash
rg -n "\bdb_path\b|StoreConfig" internal crates tests docs README.md
```

Result: exit status `1`, no matches.

Relevant code now carries `data_root` directly:

- `crates/lilo-paths/src/lilo.rs:95-109` no longer defines `db_path()` and still defines `data_root()` consumers such as `events_log_path()`.
- `internal/runtime/store/src/config.rs` is deleted.
- `internal/runtime/store/src/lib.rs:8-11` no longer exports `StoreConfig`; it exports `postgres::LifecycleStore`.
- `internal/runtime/daemon/src/server/config.rs:10-18` defines `DaemonConfig` with `data_root: PathBuf`.
- `internal/runtime/daemon/src/server/config.rs:27-37` sets `data_root: paths.data_root()` in `from_lilo_paths()`.
- `internal/runtime/daemon/src/server/config.rs:45-57` updates the test fixture from old `/tmp/rtm.db` parent behavior to `data_root: /tmp`.
- `internal/runtime/daemon/src/server/config.rs:76-78` returns `self.data_root.clone()` from `data_dir()`.
- `tests/integration/src/lib.rs:59-73` updates the integration fixture to `data_root: paths.data_root()`.
- Other test constructors now use the old parent directory directly: `crates/lilo-rm-client/tests/common/daemon.rs:42`, `internal/runtime/daemon/src/reconcile/tests.rs:306`, `spawn_preflight/tests/helpers.rs:81`, `server/tests.rs:184`, `handler/tests.rs:176`, and `test_support.rs:24`.

The old path equation was `paths.db_path().parent() == paths.data_root()`, because `db_path()` was `data_root().join("lilo.db")`. The new code preserves that effective directory without keeping the dead database file concept alive.

### Claim 5: D3 doctor `DatabaseHealth` redesign is sound

The top level doctor database health no longer exposes file path or PRAGMA shaped data:

- `crates/lilo/src/cli/doctor.rs:189-192` defines `DatabaseHealth { status, error }`.
- `crates/lilo/src/cli/doctor.rs:200-208` opens Postgres through `LiloDb::open_postgres_resolved()` and maps failures into `error`.
- `crates/lilo/src/cli/doctor.rs:211-217` probes the pool with `SELECT 1`.
- `crates/lilo/src/cli/doctor.rs:219-228` constructs `{status,error}` through `probe()` and `error_probe()`.
- `crates/lilo/src/cli/doctor.rs:76-101` human output renders `db: {status}` with no path or pragma section.
- `crates/lilo/src/cli/doctor.rs:299-335` tests the backend probe shape against a real test database.

The extended gate confirms `DbPragmas`, lowercase `pragmas`, and `pragma` residue are gone under scoped paths.

## Dependencies

- `sqlx`: Postgres pool, migrations, and query execution.
- `serde` and `serde_json`: runtime protocol shape and snapshot serialization.
- `insta`: protocol, CLI, and surface snapshots.
- `lilo-paths`: authoritative runtime path registry. The deleted `db_path()` lived here.
- `lilo-db`: actual database open path and migrations.
- `lilo-rm-core`: runtime wire protocol and version contract.
- `lilo-rm-client`: typed helper assertions and protocol consumers.

## Verification Performed

Structural and diff checks:

- `fmm_list_files(group_by="subdir")`: confirmed indexed topology on the audited tree.
- `fmm_file_outline` and `fmm_read_symbol`: inspected `DoctorResponse`, `DoctorPayload`, `RuntimeResponse`, `RUNTIME_PROTOCOL_VERSION`, `DaemonConfig`, `DatabaseHealth`, and `runtime_config` without bulk reading large files.
- `fmm_glossary`: checked `DoctorResponse`, `StoreConfig`, `DatabaseHealth`, `StoreError`, `MailRowError`, and `RUNTIME_PROTOCOL_VERSION` impact.
- `git status --short --branch`: branch `feat/postgres-phase-5`, clean worktree.
- `git log --oneline main..feat/postgres-phase-5`: six expected commits.
- `git diff --stat main...feat/postgres-phase-5`: 64 files, 127 insertions, 229 deletions.
- Extended gate: no matches, exit status `1`.
- `rg -n "\bdb_path\b|StoreConfig" internal crates tests docs README.md`: no matches, exit status `1`.
- `find internal crates tests docs -path '*sqlite*'`: no output.
- `git diff --check main...feat/postgres-phase-5`: passed.

Targeted tests:

- `cargo test -p lilo-rm-core version::tests::protocol_version_advertises_v08_nudge_wait_timeout_contract --lib`: passed, 1 test.
- `cargo test -p lilo-rm-core --test serde_snapshots runtime_response_json_shapes_are_stable`: passed, 1 test.
- `cargo test -p lilo doctor::tests::render_json_includes_runtime_detail_section`: passed, 1 test.
- `cargo test -p lilo-rm-client --test typed_helpers`: passed, 37 tests.

No Postgres integration gate was run locally. The peer mail stated CI runs the authoritative gate and warned that local DB gate execution needs `LILO_DATABASE_DOCKER_PORT` because `:55432` is occupied by `transport-matters`.

## Relevance to Helioy

This audit reinforces two Helioy cleanup rules. First, protocol shape changes need explicit version evidence, not only green snapshots. Second, name cleanup gates catch string residue, but branch hygiene still requires reviewing the full diff for unrelated local artifacts such as scheduler locks.

## Open Questions

1. Should `.claude/scheduled_tasks.lock` be added to ignore rules or excluded by an existing local config? The branch should remove it regardless.
2. Should CI add a general guard for `.claude/*.lock` or other local runtime lock files?
