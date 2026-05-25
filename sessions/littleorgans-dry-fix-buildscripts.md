---
title: Littleorgans dry fix buildscripts implementation
type: sessions
tags: [backend, littleorgans, rust, buildscripts, dry]
summary: Consolidated duplicated build script git SHA logic into the internal lilo-build-support crate.
status: active
source: backend-engineer
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Summary

Implemented the `dry-fix` buildscripts lane. Added the internal `lilo-build-support` crate and rewired the runtime app, session app, and top-level `lilo` build scripts to use one shared implementation for git SHA discovery, rerun directives, include flag parsing, and CLI version emission.

Key decisions:

- Kept the support crate small, dependency free, and `publish = false`.
- Exposed low-level helpers for git path lookup, explicit SHA lookup, `HEAD` short SHA lookup, SHA truncation, rerun path guards, and include flag parsing.
- Exposed `emit_cli_version(version_env: &str)` so consumer build scripts do not duplicate package version composition.
- Verified in a temporary repository copy to avoid mutating shared-worktree files outside the assigned lane, especially `Cargo.lock`.

## API Contract

Build support crate API:

```rust
pub fn emit_cli_version(version_env: &str);
pub fn package_version_with_optional_git_sha(package_version: &str) -> String;
pub fn emit_git_sha_env_rerun_directives();
pub fn emit_git_rerun_directives();
pub fn emit_rerun_if_path_exists(path: &std::path::Path);
pub fn git_path(rel: &str) -> Option<std::path::PathBuf>;
pub fn include_git_sha() -> bool;
pub fn build_git_sha() -> Option<String>;
pub fn explicit_git_sha() -> Option<String>;
pub fn git_head_sha() -> Option<String>;
pub fn short_sha(value: &str) -> Option<String>;
```

Consumer build script usage:

```rust
lilo_build_support::emit_cli_version("RTM_CLI_VERSION");
lilo_build_support::emit_cli_version("SM_CLI_VERSION");
lilo_build_support::emit_cli_version("LILO_CLI_VERSION");
```

No HTTP or RPC API changed.

## Database Changes

None.

## Security Considerations

- Preserved environment based override order: `LILO_GIT_SHA`, then `GITHUB_SHA`, then git `HEAD`.
- Centralized SHA validation in `short_sha`, requiring seven ASCII hex characters before appending build metadata.
- No secrets are introduced or persisted.

## Performance Notes

- Removed repeated build script implementations and kept the shared crate dependency free.
- Preserved guarded `cargo:rerun-if-changed` emission so missing packed or unpacked git ref paths do not force stale build scripts.
- Line counts remain under the 700 line file limit: support crate source is 110 lines, runtime build script is 157 lines, session build script is 198 lines, and top-level `lilo` build script is 3 lines.

## Verification

- `cargo build -p lilo-runtime-app -p lilo-session-app -p lilo` passed in temporary copy `/var/folders/15/l6zdb_ln4tq4slrn7c3hps7m0000gn/T/tmp.Mkrc2XUzL7/repo`.
- Build completed in 26.21s.
- Helper location check confirmed SHA helper definitions exist only in `crates/lilo-build-support/src/lib.rs` across the support crate and three consumer build scripts.
- Bus closeout sent: `done buildscripts: 9 files, check OK`.

## Open Items

- Orchestrator owns `fmm generate && fmm validate` for the structural change.
- Orchestrator owns git operations and any shared `Cargo.lock` update.
