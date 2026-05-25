---
title: Rust Conventions Alignment Review for session-matters
type: research
tags: [rust, session-matters, code-review, cargo, conventions, helioy]
summary: Conditional MoE signoff found three required fixes before the rust conventions branch should merge.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-26
updated: 2026-05-26
---

## Executive Summary

The `worktree-rust-conv` branch aligns `session-matters` with the 2026 Rust conventions guide and the `runtime-matters` reference commit `dad5f09`. The branch is structurally sound and passes the local gate, but MoE review reached conditional signoff on three fixes: hoist duplicated `lilo-im-*` dependency versions, add per-block `// SAFETY:` comments around unsafe environment mutation, and correct stale MAP.md and TLDR.md contract statements.

## Project Metadata

- Language: Rust, edition 2024.
- Workspace: Cargo resolver 3, six member crates under `crates/`.
- Toolchain: `rust-toolchain.toml` pins Rust `1.95` with `clippy`, `rustfmt`, and `rust-src`.
- Build system: Cargo plus `justfile`; review used direct Cargo gates from the brief.
- fmm: `.fmm.db` exists and `fmm validate` passed with 110 indexed files.
- Branch under review: `worktree-rust-conv`, `HEAD=9dfa1e8e1f80f033ae7840042da28ea75894d419`, 6 commits ahead of `main`.

## Architecture

`session-matters` is the Helioy session control plane. The `sm-cli` crate exposes the `sm` binary and embedded MCP server; `sm-daemon` owns `smd`, RPC dispatch, authorization, lifecycle, reconciliation, and MCP tools; `sm-store` owns SQLite persistence; `sm-driver` adapts to runtime-matters; `sm-core` owns shared protocol and domain types; `sm-paths` centralizes socket, database, log, and namespace binding path resolution.

The branch follows the intended Rust shape:

- `Cargo.toml:12-19` defines shared workspace package metadata, including `homepage`, `authors`, and `rust-version`.
- `Cargo.toml:50-57` defines shared Clippy policy matching `runtime-matters` dad5f09.
- Every member crate opts into `[lints] workspace = true`.
- Production `src/**/mod.rs` files were migrated to sibling files. Remaining `mod.rs` files are `tests/common/mod.rs`, an accepted convention exception.
- Crate roots forbid unsafe with `#![forbid(unsafe_code)]`, except `sm-cli` uses `#![cfg_attr(not(test), forbid(unsafe_code))]` at `crates/sm-cli/src/lib.rs:1` because tests still mutate process env under Rust 2024.

## Key Patterns

- `sm-paths` now uses `SmPathsEnv` plus `resolve` functions so path logic can be tested without mutating process environment. See `crates/sm-paths/src/lib.rs:109-183` and `rtmd_socket_path_from` at `crates/sm-paths/src/lib.rs:197-204`.
- Error types use `thiserror::Error`; `SmPathsError` was converted at `crates/sm-paths/src/lib.rs:185-189`.
- The branch avoids compatibility shims and old module paths, which fits the pre-release no-backward-compatibility policy.

## Detailed Findings

### Conditional item 1: Hoist duplicated `lilo-im-*` dependencies

The conventions guide says to use `[workspace.dependencies]` for shared dependencies and avoid repeated versions in member manifests. Current branch leaves duplicated raw versions:

- `crates/sm-daemon/Cargo.toml:14-16` declares `lilo-im-core`, `lilo-im-store`, and `lilo-im-stub` with raw `"0.1"` versions.
- `crates/sm-cli/Cargo.toml:42-43` repeats `lilo-im-core` and `lilo-im-store` as dev dependencies.
- The root already hoists the analogous runtime dependencies, `lilo-rm-client` and `lilo-rm-core`, at `Cargo.toml:34-35`.

Fix: add all three `lilo-im-*` crates to root `[workspace.dependencies]` and convert member manifests to `*.workspace = true`.

### Conditional item 2: Add per-block `// SAFETY:` comments

The conventions guide requires every unsafe block to have a `SAFETY:` comment explaining the invariant. The branch has function-level comments but lacks block-level `SAFETY:` comments at the actual unsafe sites:

- `crates/sm-cli/src/cli/run.rs:258-261`, env mutation for isolated namespace tests.
- `crates/sm-cli/src/cli/run.rs:269-273`, env restore helper.
- `crates/sm-daemon/tests/handler.rs:293-314`, `HOME` env mutation and restore in test guard.

Fix: add a `// SAFETY:` comment directly before each unsafe block or unsafe expression, matching the style used in `runtime-matters/crates/rtm-cli/src/cli/shim.rs`.

### Conditional item 3: Correct stale MAP.md and TLDR.md statements

The new docs are valuable but include stale contract details that conflict with current code.

Required corrections:

- `MAP.md:5` has stale fmm LOC numbers. Current fmm reported 110 files, 17,866 LOC, with 85 source files and 25 test files.
- `MAP.md:15` and `MAP.md:134` say the smd socket is `~/.sm/socket`; code and README use `~/.sm/sock`. The code path is `SmEndpoint::resolve` at `crates/sm-paths/src/lib.rs:72-75`; README states `~/.sm/sock` at `README.md:26`.
- `MAP.md:187` lists stale env var names. Actual constants are `SM_DB_PATH`, `SM_LOG_PATH`, `SM_SOCKET_PATH`, and `RTM_SOCKET_PATH` at `crates/sm-paths/src/lib.rs:14-18`.
- `MAP.md:331` and `MAP.md:365` say `sm config set-context` writes `${SM_HOME}/.namespace`. Actual write path is `paths.namespace_binding()` in `crates/sm-cli/src/cli/config.rs:51-54`, and `SmPaths::namespace_binding` returns `self.dir.join("namespace")` at `crates/sm-paths/src/lib.rs:45-48`.
- `TLDR.md:20-22` says a `.sm/namespace` marker scopes CLI and MCP reads by directory walk. Current code explicitly ignores workspace markers in tests at `crates/sm-cli/src/cli/namespace_resolver.rs:204-230`, and MAP.md already says the marker is ignored at `MAP.md:368`.

This is substantive because `TLDR.md` is symlinked as `AGENTS.md` and `CLAUDE.md`, so stale namespace guidance becomes agent prompt context.

## Verification

Commands run in the worktree:

```bash
pwd
git status --short --branch
git rev-list --count main..HEAD
fmm validate
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features --no-run
cargo doc --workspace --no-deps --all-features
cargo clippy --workspace --all-targets --all-features -- -W clippy::pedantic -A clippy::module_name_repetitions -A clippy::missing_errors_doc -A clippy::missing_panics_doc -A clippy::must_use_candidate
cargo test --workspace --all-features
```

All verification commands passed.

## Dependencies

Critical dependencies relevant to this review:

- `thiserror`: used for structured library errors, including `SmPathsError`.
- `lilo-rm-core` and `lilo-rm-client`: already hoisted workspace dependencies for runtime-matters contracts.
- `lilo-im-core`, `lilo-im-store`, `lilo-im-stub`: identity-matters dependencies that should be hoisted to workspace dependencies.
- `rusqlite`, `tokio`, `serde`, `serde_json`, `uuid`, `clap`: core persistence, async, serialization, IDs, and CLI surface dependencies.

## Relevance to Helioy

The branch improves `session-matters` readiness for littleorgans monorepo migration by aligning with strict Rust workspace conventions. The main remaining Helioy risk is documentation drift in `TLDR.md`, because that file doubles as agent prompt context through symlinked `AGENTS.md` and `CLAUDE.md`.

## Open Questions

- Should the `sm-cli` test unsafe env mutation be refactored later to avoid `cfg_attr(not(test), forbid(unsafe_code))`, or is the current guarded test pattern acceptable for now?
- Should MAP.md LOC counts be regenerated by script to prevent future stale manual counts?
