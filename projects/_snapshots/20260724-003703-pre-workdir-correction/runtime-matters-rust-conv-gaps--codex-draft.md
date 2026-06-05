# runtime-matters Rust conventions gap draft, Codex pane B

Scope: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/runtime-matters/` at `34ead90`, audited against `/Users/alphab/.mdx/research/rust-conventions-2026.md`.

Method: validated `.fmm.db` with `fmm validate`; mapped 143 indexed files with `fmm_list_files(group_by: "subdir")`; used fmm outlines and symbol reads for source claims; read the conventions rubric, root manifests, member manifests, README, PROJECT, MAP, justfile, CI, and release config. `cargo doc --workspace --no-deps --all-features` passes locally, but is not part of the documented gate.

## Gaps

### C1. Workspace lint policy is absent

**Gap**: The workspace has no `[workspace.lints]`, and member crates do not opt in with `[lints] workspace = true`.

**Convention reference**: Workspace Manifest: use `[workspace.lints]`; every member crate should opt in with `[lints] workspace = true`. Lints and Formatting: use Clippy in CI with warnings denied.

**Evidence**: `Cargo.toml:23-56` defines shared dependencies, then `Cargo.toml:58-62` jumps to release profile settings with no `[workspace.lints]`. `crates/rtm-cli/Cargo.toml:20-45`, `crates/rtm-core/Cargo.toml:19-29`, and the other member manifests have dependency tables but no `[lints]` table. A manifest scan checked all root and member manifests and found no `[workspace.lints]` or `[lints]` table.

**Proposed fix**: Add a root `[workspace.lints]` baseline, including `unsafe_code` policy and Clippy warnings wanted by this repo, then add `[lints] workspace = true` to every crate manifest. Use narrow per crate overrides only where justified.

**Effort**: Small.

### C2. Unsafe policy is not explicit

**Gap**: The repo contains production unsafe code, but crate roots and manifests do not state which crates are allowed to use unsafe and which crates forbid it.

**Convention reference**: Unsafe: default to forbidding unsafe; only allow unsafe in crates with a clear reason. Lints and Formatting: prefer narrow allows over crate wide allows.

**Evidence**: `crates/rtm-cli/src/lib.rs:1-6`, `crates/rtm-core/src/lib.rs:1-18`, `crates/rtm-daemon/src/lib.rs:1-18`, `crates/rtm-platform/src/lib.rs:1-9`, and other crate roots have no `#![forbid(unsafe_code)]`. Unsafe is used in production code at `crates/rtm-cli/src/cli/shim.rs:151`, `crates/rtm-platform/src/kqueue.rs:27`, `crates/rtm-platform/src/pidfd.rs:15`, `crates/rtm-platform/src/process.rs:33`, `crates/rtm-platform/src/process_exit.rs:59`, and `crates/rtm-platform/src/signal.rs:28`.

**Proposed fix**: Enforce `unsafe_code = "forbid"` by default through workspace lints. Explicitly allow unsafe only in `rtm-cli` and `rtm-platform`, where signal, process, pidfd, and kqueue calls require FFI, with local lint comments or manifest overrides documenting the reason.

**Effort**: Small.

### C3. Several unsafe blocks lack `SAFETY:` comments

**Gap**: Some unsafe blocks call libc without a preceding `SAFETY:` invariant comment.

**Convention reference**: Unsafe: every unsafe block must have a `SAFETY:` comment explaining why the operation is valid here.

**Evidence**: `crates/rtm-cli/src/cli/shim.rs:149-184` shows the local style when this is done correctly. Missing examples include `crates/rtm-platform/src/kqueue.rs:27`, `crates/rtm-platform/src/kqueue.rs:33`, `crates/rtm-platform/src/kqueue.rs:45`, `crates/rtm-platform/src/kqueue.rs:80`, `crates/rtm-platform/src/kqueue.rs:92`, `crates/rtm-platform/src/kqueue.rs:98`, `crates/rtm-platform/src/kqueue.rs:109`, `crates/rtm-platform/src/pidfd.rs:15`, `crates/rtm-platform/src/pidfd.rs:20`, `crates/rtm-platform/src/process.rs:148`, and `crates/rtm-platform/src/process_exit.rs:59`.

**Proposed fix**: Add precise `SAFETY:` comments near each unsafe block, or wrap repeated libc calls in small helper functions with one documented invariant.

**Effort**: Small.

### C4. The documented gate and CI omit documentation verification

**Gap**: The normal quality gate does not run `cargo doc`, and CI does not verify docs.

**Convention reference**: Documentation: treat `cargo doc` as part of the public API surface. Build and CI: normal local proof includes `cargo doc --workspace --no-deps --all-features`; use the repo operator surface when it exists.

**Evidence**: `PROJECT.md:331-340` documents only `just check`, `just build`, `just test`, and separately mentions snapshots. `justfile:93-108` defines `fmt`, `fmt-check`, `clippy`, `clippy-fix`, `check-loc`, and `check`, but no `doc` recipe. `.github/workflows/ci.yml:23-26` and `.github/workflows/ci.yml:37-40` run `just check`, `just build`, `just test`, and platform or snapshot checks, but no docs step. Local proof: `cargo doc --workspace --no-deps --all-features` passes on 2026-05-26.

**Proposed fix**: Add a `doc` just recipe for `cargo doc --workspace --no-deps --all-features`, document it in PROJECT, and run it in CI.

**Effort**: Trivial.

### C5. `just check` mutates the workspace

**Gap**: The documented quality gate starts with a mutating `just check`, because it runs `cargo fmt` and `cargo clippy --fix --allow-dirty` rather than check only commands.

**Convention reference**: Agent Rules: run the repo's documented checks before claiming done. Testing: update authored source first, then regenerate and verify generated output. Build and CI: normal local proof uses check style commands.

**Evidence**: `PROJECT.md:331-337` makes `just check` the first normal gate command. `justfile:93-100` defines both `fmt` and `fmt-check`, and `justfile:99-103` defines both `clippy` and `clippy-fix`. `justfile:108` wires `check: fmt clippy-fix check-loc`.

**Proposed fix**: Change `check` to `fmt-check clippy check-loc`. Keep a separate `fix` recipe, for example `fix: fmt clippy-fix`, when mutation is intended.

**Effort**: Trivial.

### C6. The normal gate does not exercise all features

**Gap**: The build, Clippy, and test recipes do not use `--all-features`, even though the workspace has at least one feature.

**Convention reference**: Build and CI: normal proof includes Clippy, build, tests, and docs with `--all-features`. Dependencies: feature flags must be additive and should avoid matrices the project cannot test.

**Evidence**: `crates/rtm-platform/Cargo.toml:18-21` defines the optional `uuid` dependency and `test-support` feature. `justfile:8-12` builds with `cargo build --workspace`, `justfile:43-44` tests with `cargo nextest run --workspace`, and `justfile:99-100` runs Clippy with `cargo clippy --workspace --all-targets -- -D warnings`, all without `--all-features`. CI consumes those recipes at `.github/workflows/ci.yml:23-25` and `.github/workflows/ci.yml:37-39`.

**Proposed fix**: Add `--all-features` to the standard build, Clippy, test, and doc recipes unless there is a platform reason to split feature coverage into a named recipe and CI job.

**Effort**: Small.

### C7. Cargo deny policy is absent

**Gap**: The workspace has no Cargo deny policy or CI step for advisory, license, and dependency policy.

**Convention reference**: Build and CI: use `cargo deny` for license, advisory, and dependency policy.

**Evidence**: A root scan for `deny.toml`, `cargo-deny.yml`, or similarly named deny files returned no files. `.github/workflows/ci.yml:13-65` contains local gates and semver checks only, with no Cargo deny install or run step.

**Proposed fix**: Add `deny.toml`, a `just deny` recipe, and a CI step. Start with a permissive explicit policy if needed, then tighten it as dependency decisions settle.

**Effort**: Small.

### C8. The contributor toolchain is floating while MSRV is fixed

**Gap**: `rust-toolchain.toml` uses floating `stable`, while `[workspace.package]` declares `rust-version = "1.90"`; the project docs call the toolchain pinned.

**Convention reference**: Edition and Toolchain: pin the contributor toolchain in `rust-toolchain.toml`; set `rust-version`; the toolchain channel and `rust-version` should usually match.

**Evidence**: `rust-toolchain.toml:1-3` sets `channel = "stable"`. `Cargo.toml:14-21` sets edition 2024 and `rust-version = "1.90"`. `PROJECT.md:339-340` says the toolchain is pinned in `rust-toolchain.toml`. Local `rustc --version` resolves that stable channel to `rustc 1.95.0`, not 1.90.

**Proposed fix**: Pin `channel = "1.90"` if contributors should build against MSRV, or update PROJECT to say the repo tracks stable and add a separate MSRV check for 1.90.

**Effort**: Trivial.

### C9. Internal library crate roots lack crate level docs

**Gap**: Several library crates have no crate level `//!` documentation.

**Convention reference**: Documentation: library crates should have crate level docs; internal crates should document public items that are cross crate contracts.

**Evidence**: `crates/rtm-client/src/lib.rs:1-5`, `crates/rtm-core/src/lib.rs:1-17`, and `crates/rtm-paths/src/lib.rs:1-5` have crate level docs. `crates/rtm-cli/src/lib.rs:1-6`, `crates/rtm-daemon/src/lib.rs:1-18`, `crates/rtm-launchers/src/lib.rs:1-18`, `crates/rtm-platform/src/lib.rs:1-9`, and `crates/rtm-store/src/lib.rs:1-6` start directly with items and have no crate docs.

**Proposed fix**: Add concise `//!` docs to each internal library crate root describing its cross crate contract and warning when a crate is implementation only.

**Effort**: Small.

### C10. `rtm-paths` hand writes a library error instead of using `thiserror`

**Gap**: `RuntimePathError` manually implements `Display` and `std::error::Error` even though the workspace already standardizes on `thiserror`.

**Convention reference**: Error Handling: use `thiserror` for library and internal library crates; use source chaining through `#[from]` or `#[source]` where it preserves meaning.

**Evidence**: `Cargo.toml:40` defines `thiserror` in workspace dependencies. `crates/rtm-paths/Cargo.toml:1-15` has no dependencies section, so it does not consume `thiserror`. `crates/rtm-paths/src/lib.rs:128-155` derives only `Debug`, then hand writes `fmt::Display` and `std::error::Error` for `RuntimePathError`.

**Proposed fix**: Add `thiserror.workspace = true` to `rtm-paths` and replace the manual impls with `#[derive(Debug, thiserror::Error)]` plus explicit variant messages and `#[source]` on `CurrentExecutable`.

**Effort**: Small.

### C11. `CaptureError` is a public error return type without an Error implementation

**Gap**: `CaptureError` is returned by a public result producing method, but it does not implement `std::error::Error`.

**Convention reference**: API Design: error types should end in `Error`. Error Handling: library errors should be structured and matchable; use `thiserror` for library crates.

**Evidence**: `crates/rtm-core/src/capture.rs:57-66` defines public `CaptureError` with serde derives only. `crates/rtm-core/src/capture.rs:76-82` exposes `CaptureResponse::into_result(self) -> Result<PaneSnapshot, CaptureError>`. `crates/rtm-core/Cargo.toml:19-29` already depends on `thiserror.workspace = true`, so no new crate is needed.

**Proposed fix**: Derive `thiserror::Error` for `CaptureError` and add stable error messages per variant while preserving serde wire shape.

**Effort**: Small.

## Checked sections with no gap found

### Project shape

The repo is a virtual Cargo workspace with no root `src/` (`Cargo.toml:1-12`). Workspace packages live flat under `crates/`, and internal packages use `publish = false` (`crates/rtm-cli/Cargo.toml:1-11`, `crates/rtm-daemon/Cargo.toml:1-10`, `crates/rtm-platform/Cargo.toml:1-10`). Public crate naming and public crate versioning intentionally differ from folder names and the internal workspace version, as documented by MAP (`MAP.md:159-168`) and release-plz config (`release-plz.toml:10-20`). I do not treat that as a gap because it is an explicit local release boundary.

### Workspace dependencies

Member manifests inherit dependency versions from `[workspace.dependencies]`. Spot checks: `crates/rtm-cli/Cargo.toml:20-45`, `crates/rtm-daemon/Cargo.toml:12-29`, `crates/rtm-core/Cargo.toml:19-29`, and `crates/rtm-client/Cargo.toml:19-30`. I found no wildcard dependency versions.

### Module files and size limits

fmm reports the largest Rust source file is `crates/rtm-cli/tests/spawn_target.rs` at 574 LOC, below the local 700 line hard limit. Existing `mod.rs` files are legacy, generated, or test support: `crates/rtm-cli/src/cli/mod.rs`, `crates/rtm-cli/src/generated/mod.rs`, `crates/rtm-cli/src/mcp/mod.rs`, `crates/rtm-cli/tests/common/mod.rs`, `crates/rtm-core/tests/support/mod.rs`, and `crates/rtm-store/src/sqlite/mod.rs`. No new module churn is required for this audit.

### Public re exports

fmm outline of `crates/rtm-core/src/lib.rs` shows named re exports from public contract modules. A source scan found no public glob re exports.

### Async traits

No `async-trait` usage was found. `RuntimeLauncher` is synchronous and has real `ClaudeLauncher` and `CodexLauncher` implementations (`crates/rtm-core/src/launcher.rs:64-92`; fmm export list shows both impls). `ProcessProbe` has a real system implementation plus test fakes (`crates/rtm-daemon/src/reconcile.rs:50-76`; fmm export list shows test probes), so the trait is justified.

### Generated surfaces

Generated CLI and MCP surfaces have authored sources: MAP points to `crates/rtm-core/tools.toml` and `crates/rtm-cli/build.rs` for generation (`MAP.md:345-346`, `MAP.md:433-434`). I found no generated surface without an authored source of truth.

