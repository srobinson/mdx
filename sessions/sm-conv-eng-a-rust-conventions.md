---
title: sm-conv warroom eng-a — sm-paths/sm-core rust-conventions alignment
type: sessions
tags: [backend, rust, session-matters, warroom, rust-conventions, sm-paths, sm-core, thiserror, forbid-unsafe]
summary: Aligned sm-paths and sm-core with strict Rust conventions (#![forbid(unsafe_code)] + thiserror derive). Refactored sm-paths to use an SmPathsEnv builder so tests inject env values instead of mutating process env.
status: active
source: backend-engineer
confidence: high
created: 2026-05-26
updated: 2026-05-26
---

## Summary

Acting as `eng-a` in the `sm-conv` warroom, executed zone-scoped refactor of `crates/sm-paths` and `crates/sm-core` to align with `/Users/alphab/.mdx/research/rust-conventions-2026.md`. Reference implementation: runtime-matters commit `dad5f09` ("refactor: align with strict rust conventions").

Final commit: `e4af5dd` on branch `worktree-rust-conv`.

Key decisions:
- Added `#![forbid(unsafe_code)]` to both crate roots.
- Converted `SmPathsError` from manual `fmt::Display` + `Error` impls to `#[derive(thiserror::Error)]`.
- **Scope expansion**: introduced `SmPathsEnv` builder + `SmPaths::resolve` / `SmEndpoint::resolve` / `rtmd_socket_path_from` because the original tests used `unsafe { env::set_var() }` (Rust 2024 makes env mutation unsafe). `forbid(unsafe_code)` cannot be downgraded by `#[allow]`, so the test helper would have failed to compile. Mirrored runtime-matters' `RuntimePathEnv` pattern.

## API Contract (zone-additive only)

New public APIs in `sm-paths` (re-exported through `sm-core::paths`):

```rust
pub struct SmPathsEnv { /* fields hidden */ }

impl SmPathsEnv {
    pub fn from_process() -> Self;       // snapshots live process env
    pub fn new() -> Self;                 // empty; same as Default
    pub fn sm_home(self, value: impl Into<OsString>) -> Self;       // builder
    pub fn sm_db_path(self, value: impl Into<OsString>) -> Self;
    pub fn sm_log_path(self, value: impl Into<OsString>) -> Self;
    pub fn sm_socket_path(self, value: impl Into<OsString>) -> Self;
    pub fn rtm_socket_path(self, value: impl Into<OsString>) -> Self;
    pub fn xdg_runtime_dir(self, value: impl Into<OsString>) -> Self;
    pub fn home(self, value: impl Into<OsString>) -> Self;
}

impl SmPaths {
    pub fn resolve(env: &SmPathsEnv) -> Result<Self, SmPathsError>;
}

impl SmEndpoint {
    pub fn resolve(env: &SmPathsEnv) -> Result<Self, SmPathsError>;
}

pub fn rtmd_socket_path_from(env: &SmPathsEnv) -> PathBuf;
```

Existing APIs unchanged: `SmPaths::from_env`, `SmEndpoint::from_env`, `rtmd_socket_path()` (now thin wrappers over `SmPathsEnv::from_process()`).

New env-name constants exposed: `SM_HOME`, `SM_DB_PATH`, `SM_LOG_PATH`, `SM_SOCKET_PATH`, `RTM_SOCKET_PATH`, `XDG_RUNTIME_DIR`, `HOME`.

## Database Changes

None.

## Security Considerations

- `#![forbid(unsafe_code)]` is now a crate-level guarantee for sm-paths and sm-core. Future contributions to either crate cannot introduce `unsafe` blocks without lifting the forbid attribute (which would be visible in code review).
- Test isolation improved: tests no longer mutate process env via `unsafe { env::set_var }`. This eliminates a real safety hazard in Rust 2024 where concurrent env reads/writes are undefined behavior. Tests now rely on pure-data env injection.

## Performance Notes

No runtime hot-path changes. Resolver functions add one extra function call hop (the `from_env` wrapper) which the compiler will inline.

## Verification

- `cargo clippy -p sm-paths -p sm-core --all-targets --all-features -- -D warnings` → clean.
- `cargo test -p sm-paths -p sm-core --all-features` → 11 sm-paths tests + 40 sm-core tests pass.
- `cargo check -p sm-store -p sm-driver -p sm-daemon -p sm-cli --all-features` → clean (no breakage to downstream zones).

## Open Items

- `Cargo.lock` was modified (added `thiserror` to sm-paths' direct deps) but left unstaged per the warroom zone-discipline rule. The orchestrator or a workspace-scope agent should roll Cargo.lock forward.
- First commit attempt (2370d37) was clobbered by a racing agent in the shared worktree that staged MAP.md + TLDR.md from a codebase-map run. Recovered via `git reset --soft HEAD~1` + restage. Lesson captured to cm at `global/project:helioy/project:littleorgans` (id `019e63db-803b-7df0-ae1d-6cfef94de289`).
- Existing manual `fmt::Display` impls on state enums in sm-core (`RuntimeKind`, `SessionState`, `Selector`, `MailStatus`, `Namespace`) were left untouched per directive — these are state formatters, not errors.

## Reply

Sent to `session-matters:general:2:3.1` on topic `sm-conv-eng-a`:
> done: e4af5dd — also introduced `SmPathsEnv` builder + `resolve`/`rtmd_socket_path_from` so tests inject env values instead of `unsafe { env::set_var }` ... Note: Cargo.lock updated (thiserror added to sm-paths) but left unstaged per zone discipline; first commit attempt at 2370d37 was clobbered by a racing agent that staged MAP.md+TLDR.md in the shared worktree — soft-reset and recommitted clean as e4af5dd.
