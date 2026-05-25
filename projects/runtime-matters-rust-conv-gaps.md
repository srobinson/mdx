---
title: runtime-matters vs rust-conventions-2026 — agreed gap list
audited_against: /Users/alphab/.mdx/research/rust-conventions-2026.md
repo: /Users/alphab/Dev/LLM/DEV/helioy/littleorgans/runtime-matters
baseline_commit: 34ead90
date: 2026-05-26
status: orchestrator-merged, awaiting clean sign-off
reviewers:
  - pane A (claude): runtime-matters:helioy-tools:codebase-analyst:3:4.1
  - pane B (codex):  runtime-matters:helioy-tools:codebase-analyst:3:4.2
---

# Remaining work to align runtime-matters with rust-conventions-2026

## Scope

This is the merged consensus of two independent audits. Items below are residual gaps PR #54 did not close. **CI workflow changes are out of scope** — runtime-matters will migrate into the `littleorgans` monorepo before its CI is reshaped, so any change here scoped to `.github/workflows/*` is deferred to that migration. The same conventions still get enforced; the justfile-level changes land now, the CI wiring lands at monorepo cut.

Two items from the original drafts were withdrawn by mutual agreement (build-time README write in `rtm-cli/build.rs`; published-crate version not inheriting workspace version — both judged deliberate and documented). Two items were dropped per user directive (mutating `just check` is the desired developer experience; `cargo deny` is deferred to monorepo migration).

## Hard gaps (9)

### C1. No `[workspace.lints]` policy

**Gap**: Root `Cargo.toml` has no `[workspace.lints]`. No member carries `[lints] workspace = true`. The rubric's baseline (`unsafe_code = "forbid"`, `pedantic = "warn"`, allow-list for `module_name_repetitions`, `missing_errors_doc`, `missing_panics_doc`, `must_use_candidate`) is unenforced. Production-targeted lints (`unwrap_used`, `expect_used`) for `rtm-daemon` and `rtm-cli` are missing.

**Convention**: Workspace Manifest; Lints and Formatting.

**Evidence**: `Cargo.toml` (no `[workspace.lints]` block). All eight member manifests: no `[lints]` table.

**Fix**: Add `[workspace.lints.rust]` and `[workspace.lints.clippy]` baselines to root `Cargo.toml`. Add `[lints] workspace = true` to every member manifest. Include `unwrap_used = "warn"` and `expect_used = "warn"` (production-targeted via per-crate overrides on `rtm-daemon` and `rtm-cli`; allow in test modules narrowly).

**Effort**: small.

### C2. No `forbid(unsafe_code)` on safe crates

**Gap**: Six crates (`rtm-core`, `rtm-client`, `rtm-paths`, `rtm-launchers`, `rtm-store`, `rtm-daemon`) contain zero unsafe code and could enforce `#![forbid(unsafe_code)]`.

**Convention**: Unsafe — default to forbidding unsafe.

**Fix**: Subsumed by C1's workspace-level `unsafe_code = "forbid"`. `rtm-platform` and `rtm-cli/src/cli/shim.rs` use narrow `#[allow(unsafe_code)]` at the smallest scope.

**Effort**: trivial after C1.

### C3. Many unsafe blocks lack `SAFETY:` comments

**Gap**: ~11 unsafe blocks in `rtm-platform` call libc without a preceding `SAFETY:` invariant comment. Only `signal.rs:26` and the three blocks in `rtm-cli/src/cli/shim.rs` (150, 168, 183) currently follow the rubric.

**Convention**: Unsafe — every unsafe block must have a `SAFETY:` comment.

**Evidence**: `crates/rtm-platform/src/kqueue.rs:27,33,45,80,92,98,109`; `crates/rtm-platform/src/pidfd.rs:15,20`; `crates/rtm-platform/src/process.rs:148`; `crates/rtm-platform/src/process_exit.rs:59`.

**Fix**: Add precise `SAFETY:` comments at each block, or wrap repeated libc calls in small helpers with one documented invariant.

**Effort**: small.

### C4. No `cargo doc` recipe in the gate

**Gap**: `justfile` has no `doc` recipe. Public crates (`lilo-rm-core`, `lilo-rm-client`) can silently regress on broken intra-doc links or doc-test failures.

**Convention**: Documentation; Build and CI.

**Evidence**: `justfile:93-108` — fmt, fmt-check, clippy, clippy-fix, check-loc, check; no `doc`.

**Fix**: Add `doc: cargo doc --workspace --no-deps --all-features` to `justfile`, ideally with `RUSTDOCFLAGS="-D rustdoc::broken-intra-doc-links"`. CI wiring deferred to monorepo migration.

**Effort**: trivial.

### C6. Local gate recipes omit `--all-features`

**Gap**: `justfile` recipes for `build`, `test`, and `clippy`/`clippy-fix` run without `--all-features`. `rtm-platform` has a `test-support` feature exercised only via dev-deps; default gate never checks it in isolation across all consumers.

**Convention**: Build and CI.

**Evidence**: `justfile:8-12` (`build`), `justfile:43-44` (`test`), `justfile:99-103` (`clippy`/`clippy-fix`). `crates/rtm-platform/Cargo.toml:20-21` defines `test-support = ["uuid"]`.

**Fix**: Add `--all-features` to `justfile` `build`, `clippy`, `clippy-fix`, `test`, and the new `doc` recipe (C4). Verify the build stays green. CI wiring deferred to monorepo migration.

**Effort**: small (verify gate stays green is the bulk of the work).

### C9. Five `lib.rs` files lack crate-level `//!` docs

**Gap**: `rtm-daemon`, `rtm-launchers`, `rtm-platform`, `rtm-store`, `rtm-cli` have no `//!` headers. `rtm-core`, `rtm-client`, `rtm-paths` are compliant.

**Convention**: Documentation — library crates should have crate-level docs.

**Evidence**: Each named `lib.rs` opens directly with `mod` / `pub mod` / `cfg_attr`.

**Fix**: Add 2-4 line `//!` to each, sourced from `PROJECT.md` / `MAP.md`.

**Effort**: small.

### C10. `rtm-paths::RuntimePathError` is hand-written

**Gap**: `RuntimePathError` implements `Display` and `std::error::Error` manually despite the workspace standardizing on `thiserror`.

**Convention**: Error Handling — use `thiserror` for library crates.

**Evidence**: `crates/rtm-paths/src/lib.rs:128-155` (manual impls). `crates/rtm-paths/Cargo.toml` has no `thiserror` dep. Root `Cargo.toml:40` defines `thiserror` in `[workspace.dependencies]`.

**Fix**: Add `thiserror.workspace = true` to `rtm-paths/Cargo.toml`. Replace manual impls with `#[derive(thiserror::Error)]` plus `#[error("...")]` per variant and `#[source]` on `CurrentExecutable`.

**Effort**: small.

### C11. `CaptureError` is returned as `Result::Err` but does not implement `Error`

**Gap**: `CaptureError` is returned from `CaptureResponse::into_result()` but only derives serde traits; no `std::error::Error` impl.

**Convention**: Error Handling — library errors should be structured and matchable.

**Evidence**: `crates/rtm-core/src/capture.rs:57-66` (definition); `crates/rtm-core/src/capture.rs:76-82` (`into_result`). `crates/rtm-core/Cargo.toml:19-29` already depends on `thiserror`.

**Fix**: Add `#[derive(thiserror::Error)]` to `CaptureError`. Stable variant messages via `#[error("...")]`. Preserve serde wire shape — `thiserror::Error` does not interfere with existing `Serialize`/`Deserialize` derives.

**Effort**: small.

### G6. Three production `mod.rs` files survive PR #54

**Gap**: Three production module indexes remain in the legacy `mod.rs` form. The rubric prefers `foo.rs` + `foo/` for new modules; existing `mod.rs` may stay when "churn is not worth it", but the user has elected to migrate.

**Convention**: Modules and Files.

**Evidence**:
- `crates/rtm-store/src/sqlite/mod.rs`
- `crates/rtm-cli/src/mcp/mod.rs`
- `crates/rtm-cli/src/cli/mod.rs`

The three `mod.rs` files that match a rubric exception stay: `crates/rtm-core/tests/support/mod.rs`, `crates/rtm-cli/tests/common/mod.rs`, `crates/rtm-cli/src/generated/mod.rs` (build-script-generated).

**Fix**: `git mv` each:
- `crates/rtm-store/src/sqlite/mod.rs` → `crates/rtm-store/src/sqlite.rs`
- `crates/rtm-cli/src/mcp/mod.rs` → `crates/rtm-cli/src/mcp.rs`
- `crates/rtm-cli/src/cli/mod.rs` → `crates/rtm-cli/src/cli.rs`

Parent declarations (`pub mod sqlite;` etc.) stay unchanged.

**Effort**: small (three mechanical moves).

## Soft gap (1)

### C8. Toolchain channel `stable` vs `rust-version = "1.90"`

**Gap**: `rust-toolchain.toml` pins `channel = "stable"` while `[workspace.package]` declares `rust-version = "1.90"`. The local `rustc` resolves to `1.95.0`, contradicting the MSRV contract advertised to crates.io consumers of `lilo-rm-core` / `lilo-rm-client`.

**Convention**: Edition and Toolchain — toolchain channel and `rust-version` should usually match.

**Evidence**: `rust-toolchain.toml:2` (`channel = "stable"`); `Cargo.toml:21` (`rust-version = "1.90"`); `PROJECT.md:339-340` describes the toolchain as pinned.

**Fix (choose one)**:
- Pin `channel = "1.90"` and add `rust-src` to `components` (rubric recommends `["clippy", "rustfmt", "rust-src"]`).
- Or update `PROJECT.md` to say the repo tracks stable, and add a separate MSRV-verification step (e.g. `cargo msrv verify` or a 1.90 build matrix entry) deferred to monorepo migration.

**Effort**: trivial.

## Out of scope (handled at littleorgans monorepo migration)

- Wiring `just doc`, `--all-features`-flavored recipes, or `cargo deny` into `.github/workflows/*`.
- `cargo deny` / `deny.toml` policy itself (deferred whole-hog).
- Repo-mutating `build.rs` README write (deliberate; authored source exists).
- Published-crate version pinning vs workspace version (deliberate dual-release boundary).
- Mutating `just check` (`fmt` + `clippy-fix`) — desired developer experience.

## Sign-off

Both reviewers fetch this file fresh (do not work from memory) and respond with one of:
- `I sign off on /Users/alphab/.mdx/projects/runtime-matters-rust-conv-gaps.md as currently filed`
- `I sign off conditional on the following changes:` + numbered list
