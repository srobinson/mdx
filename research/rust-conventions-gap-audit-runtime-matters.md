---
title: Runtime Matters Rust Conventions Gap Audit
type: research
tags: [rust, conventions, runtime-matters, helioy, audit]
summary: Consensus audit found 9 hard gaps and 1 soft gap remaining after PR #54's Rust conventions pass.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-26
updated: 2026-05-26
---

## Executive Summary

Two independent reviewers audited `runtime-matters` at commit `34ead90` against `/Users/alphab/.mdx/research/rust-conventions-2026.md`. The signed off artifact is `/Users/alphab/.mdx/projects/runtime-matters-rust-conv-gaps.md`: 9 hard gaps and 1 soft gap remain after PR #54.

## Project Metadata

- Language: Rust.
- Workspace: virtual Cargo workspace in `Cargo.toml:1-12`.
- Edition and MSRV: edition 2024, `rust-version = "1.90"` in `Cargo.toml:14-21`.
- Toolchain file: `rust-toolchain.toml:1-3`, currently `channel = "stable"`.
- Crates: `lilo-rm-core`, `lilo-rm-client`, `rtm-daemon`, `rtm-cli`, `rtm-store`, `rtm-platform`, `rtm-launchers`, `rtm-paths`.
- Operator surface: `justfile`. Current quality gate is documented in `PROJECT.md:331-340`.

## Architecture

`runtime-matters` is the per host substrate for littleorgans agent runtimes. The daemon owns lifecycle state and event log; the CLI talks to the daemon; the shim wraps runtime processes; launchers produce commands for named runtimes such as Claude and Codex. MAP describes the crate layout at `MAP.md:159-168`.

## Key Patterns

- Shared workspace metadata and dependencies live in the root manifest, but workspace lint policy is absent.
- Public contract crates are `lilo-rm-core` and `lilo-rm-client`; internal implementation crates use `publish = false`.
- Generated CLI and MCP surfaces have authored sources, so build time README generation was omitted from the final gap list.
- Dual public crate versioning is deliberate through `release-plz.toml:10-20`, so published crate versions not inheriting the workspace version were omitted.

## Detailed Findings

### Hard gaps

1. **No workspace lint policy.** `Cargo.toml` has no `[workspace.lints]`, and all eight member manifests lack `[lints] workspace = true`. The fix is a root lint baseline plus member opt in. See final artifact lines 23 to 33.
2. **No safe crate unsafe ban.** Six crates can enforce `unsafe_code = "forbid"`: `rtm-core`, `rtm-client`, `rtm-paths`, `rtm-launchers`, `rtm-store`, and `rtm-daemon`. See final artifact lines 35 to 43.
3. **Unsafe blocks lack `SAFETY:` comments.** Missing comments were verified in `crates/rtm-platform/src/kqueue.rs:27,33,45,80,92,98,109`, `pidfd.rs:15,20`, `process.rs:148`, and `process_exit.rs:59`. See final artifact lines 45 to 55.
4. **No doc recipe.** `justfile:93-108` has no `doc` recipe. Add `cargo doc --workspace --no-deps --all-features`, with broken intra doc links denied if practical. See final artifact lines 57 to 67.
5. **Local gate omits all features.** `justfile:8-12`, `43-44`, and `99-103` run build, test, Clippy, and Clippy fix without `--all-features`. `crates/rtm-platform/Cargo.toml:20-21` defines `test-support`. See final artifact lines 69 to 79.
6. **Five crate roots lack crate docs.** `rtm-daemon`, `rtm-launchers`, `rtm-platform`, `rtm-store`, and `rtm-cli` open without `//!` docs. `rtm-core`, `rtm-client`, and `rtm-paths` already have crate docs. See final artifact lines 81 to 91.
7. **`RuntimePathError` is hand written.** `crates/rtm-paths/src/lib.rs:128-155` manually implements `Display` and `Error`; `rtm-paths` lacks `thiserror` despite root `Cargo.toml:40`. See final artifact lines 93 to 103.
8. **`CaptureError` lacks `Error`.** `crates/rtm-core/src/capture.rs:57-66` defines `CaptureError`; `crates/rtm-core/src/capture.rs:76-82` returns it from `into_result`. Add `thiserror::Error` without changing serde shape. See final artifact lines 105 to 115.
9. **Three production `mod.rs` files remain.** User elected to migrate `crates/rtm-store/src/sqlite/mod.rs`, `crates/rtm-cli/src/mcp/mod.rs`, and `crates/rtm-cli/src/cli/mod.rs`. Test and generated `mod.rs` exceptions stay. See final artifact lines 117 to 137.

### Soft gap

1. **Toolchain tracks floating stable while MSRV is 1.90.** `rust-toolchain.toml:2` uses stable; `Cargo.toml:21` says `rust-version = "1.90"`; `PROJECT.md:339-340` says the toolchain is pinned. Either pin `channel = "1.90"` or document stable tracking and add MSRV verification. See final artifact lines 141 to 153.

### Dropped or deferred by directive

- Mutating `just check` is intentional developer experience.
- Cargo deny policy is deferred to the littleorgans monorepo migration.
- CI workflow wiring for docs and all features is deferred to monorepo migration.
- Build time README generation and dual public crate versioning were judged deliberate and documented.

## Dependencies

The audit focused on convention relevant dependencies:

- `thiserror`: already present in root `Cargo.toml:40`; should be used by `rtm-paths` and `CaptureError`.
- `tokio`, `anyhow`, `serde`, `serde_json`, `clap`, `tracing`: already inherited through `[workspace.dependencies]`.
- `libc`: used by platform and shim unsafe blocks, requiring explicit safety documentation and targeted unsafe allowances.

## Relevance to Helioy

This audit gives Nancy or another implementation agent a bounded, source backed remediation list. The most important sequencing is: add workspace lint policy first, add narrow unsafe allowances, document unsafe blocks, then update local `just` recipes and small docs or error derives.

## Open Questions

- Should `rust-toolchain.toml` pin `1.90`, or should the repo track stable with separate MSRV proof during monorepo migration?
- Should `unwrap_used` and `expect_used` land as workspace warnings plus test local allows, or as per crate production policies only?
