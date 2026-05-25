# littleorgans dry-fix buildscripts

Date: 2026-05-28
Lane: buildscripts

## Files changed

- `Cargo.toml`
- `crates/lilo-build-support/Cargo.toml`
- `crates/lilo-build-support/src/lib.rs`
- `internal/runtime/app/build.rs`
- `internal/runtime/app/Cargo.toml`
- `internal/session/app/build.rs`
- `internal/session/app/Cargo.toml`
- `crates/lilo/build.rs`
- `crates/lilo/Cargo.toml`

## New crate API signatures

- `pub fn emit_cli_version(version_env: &str)`
- `pub fn package_version_with_optional_git_sha(package_version: &str) -> String`
- `pub fn emit_git_sha_env_rerun_directives()`
- `pub fn emit_git_rerun_directives()`
- `pub fn emit_rerun_if_path_exists(path: &Path)`
- `pub fn git_path(rel: &str) -> Option<PathBuf>`
- `pub fn include_git_sha() -> bool`
- `pub fn build_git_sha() -> Option<String>`
- `pub fn explicit_git_sha() -> Option<String>`
- `pub fn git_head_sha() -> Option<String>`
- `pub fn short_sha(value: &str) -> Option<String>`

## Notes

- Consolidated duplicated git SHA lookup, explicit SHA lookup, git path lookup, rerun guards, include flag parsing, and CLI version emission into `lilo-build-support`.
- Added `lilo-build-support.workspace = true` to the three consumer build dependency sections.
- `lilo-build-support` is internal and `publish = false`.
- Did not update `Cargo.lock` in the shared worktree. Verification ran in a temporary copy so Cargo could refresh its local lockfile without touching files outside the lane.

## Verification

- `cargo build -p lilo-runtime-app -p lilo-session-app -p lilo` in `/var/folders/15/l6zdb_ln4tq4slrn7c3hps7m0000gn/T/tmp.Mkrc2XUzL7/repo`: OK, finished dev profile in 26.21s.
- Helper location check: SHA helper function definitions now exist only in `crates/lilo-build-support/src/lib.rs` across the three consumer build scripts and the support crate.

## Left

- Orchestrator owns `fmm generate && fmm validate` per lane directive.
- Orchestrator owns git operations and any shared `Cargo.lock` update.
