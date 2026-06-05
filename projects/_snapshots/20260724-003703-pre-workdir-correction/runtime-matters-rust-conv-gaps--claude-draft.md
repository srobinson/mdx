---
title: runtime-matters vs rust-conventions-2026 — Claude (pane A) gap draft
author: pane A (claude runtime)
audited_against: /Users/alphab/.mdx/research/rust-conventions-2026.md
repo: /Users/alphab/Dev/LLM/DEV/helioy/littleorgans/runtime-matters @ 34ead90
date: 2026-05-26
status: independent draft, pre-debate
---

# Gaps in runtime-matters against rust-conventions-2026

Audit assumes PR #54 (`34ead90`) just landed and applied a first strict-conventions pass. Items below are residual gaps that PR #54 did not close. Each item is anchored to one or more rubric sections.

---

## G1. Workspace has no `[workspace.lints]` and no member opts in

**Gap**: The root `Cargo.toml` declares `[workspace]`, `[workspace.package]`, and `[workspace.dependencies]` but no `[workspace.lints]`. No member `Cargo.toml` carries `[lints] workspace = true`. The rubric's required baseline (`unsafe_code = "forbid"`, `pedantic = "warn"`, plus the allow-list for `module_name_repetitions`, `missing_errors_doc`, `missing_panics_doc`, `must_use_candidate`) is unenforced. CI gets `-D warnings` from the justfile invocation only; there is no compiled-in policy.

**Convention reference**: "Lints and Formatting — A practical baseline … `[workspace.lints.rust] unsafe_code = "forbid"` …"; "Every member crate should opt in with `[lints] workspace = true`"; "Anti Patterns — Avoid public glob re-exports" et al. enforced via clippy pedantic.

**Evidence**:
- `Cargo.toml:1-92` — no `[workspace.lints]` block.
- `crates/rtm-core/Cargo.toml`, `crates/rtm-client/Cargo.toml`, `crates/rtm-daemon/Cargo.toml`, `crates/rtm-cli/Cargo.toml`, `crates/rtm-paths/Cargo.toml`, `crates/rtm-platform/Cargo.toml`, `crates/rtm-launchers/Cargo.toml`, `crates/rtm-store/Cargo.toml` — none carry `[lints]`.

**Proposed fix**: Add the rubric baseline `[workspace.lints.rust]` and `[workspace.lints.clippy]` blocks to `Cargo.toml`. Add `[lints] workspace = true` to every member manifest. Where a crate needs unsafe (rtm-platform, rtm-cli/shim.rs), use targeted `#[allow(unsafe_code)]` at the smallest scope, not crate-wide.

**Effort**: small.

---

## G2. No `unsafe_code = "forbid"` policy on safe crates

**Gap**: Five crates have zero unsafe and could forbid it: `rtm-core`, `rtm-client`, `rtm-paths`, `rtm-launchers`, `rtm-store`, `rtm-daemon`. Currently no crate declares `#![forbid(unsafe_code)]` (`grep -rn forbid\\(unsafe_code\\) crates --include="*.rs"` returns empty). PR #54 didn't add this guard.

**Convention reference**: "Unsafe — Default to forbidding unsafe: `#![forbid(unsafe_code)]`. Only allow unsafe in crates that have a clear reason."

**Evidence**:
- `crates/rtm-platform/src/{kqueue,process,signal,pidfd,process_exit}.rs` — only files with `unsafe` outside `rtm-cli/src/cli/shim.rs`. SAFETY comments are correct (verified at `process.rs:31,63,84`, `signal.rs:26`, `shim.rs:150,168,183`).
- `crates/rtm-cli/src/cli/shim.rs:151,170,184` — three legitimate `unsafe libc::*` blocks, properly documented.

**Proposed fix**: Subsumed by G1 (workspace `unsafe_code = "forbid"`). `rtm-platform` and `rtm-cli/src/cli/shim.rs` add narrow `#[allow(unsafe_code)]` on the modules / functions that contain the calls.

**Effort**: trivial once G1 lands.

---

## G3. No `cargo doc` step in the documented gate

**Gap**: The rubric's "normal local proof" closes with `cargo doc --workspace --no-deps --all-features`. Neither `justfile` nor any `.github/workflows/*.yml` runs `cargo doc` in any form. Public crates `lilo-rm-core` and `lilo-rm-client` can regress on broken intra-doc links, doc-test compile failures, or missing-docs without any signal.

**Convention reference**: "Documentation — Treat `cargo doc` as part of the public API surface. Run `cargo doc --workspace --no-deps`. Broken intra doc links should fail CI when practical." "Build and CI — The normal local proof should include … `cargo doc --workspace --no-deps --all-features`."

**Evidence**:
- `justfile:1-109` — no `doc` recipe.
- `.github/workflows/ci.yml` — `local-gate` and `ubuntu-runtime-gate` run `check`, `build`, `test`, `insta-test`, `linux-target-check`. No doc step.

**Proposed fix**: Add `doc: cargo doc --workspace --no-deps --all-features` to `justfile`, optionally with `RUSTDOCFLAGS="-D rustdoc::broken-intra-doc-links"`. Wire `just doc` into both CI jobs.

**Effort**: trivial.

---

## G4. `just check` is mutating and short of the rubric gate

**Gap**: CI invokes `just check` (`justfile:108: check: fmt clippy-fix check-loc`). `fmt` runs `cargo fmt --all` (write mode) and `clippy-fix` runs `cargo clippy --workspace --fix --allow-dirty -- -D warnings`. A CI run that auto-rewrites source on every push hides actual format/clippy regressions: any fixable diff is silently absorbed, only unfixable warnings surface. The rubric is explicit on the CI gate being read-only.

**Convention reference**: "Build and CI — The normal local proof should include `cargo fmt --all -- --check` and `cargo clippy --workspace --all-targets --all-features -- -D warnings`."

**Evidence**:
- `justfile:93-103` — `fmt` writes, `fmt-check` exists as a read-only target but is unused by `check`. `clippy-fix` uses `--fix --allow-dirty`; `clippy` exists as a read-only target but is unused by `check`.
- `.github/workflows/ci.yml:14,28` — both jobs call `just check`, not `just fmt-check` + `just clippy`.

**Proposed fix**: Redefine `check: fmt-check clippy check-loc`. Keep `fmt` and `clippy-fix` as developer-side convenience targets but never wire them into CI.

**Effort**: trivial.

---

## G5. Gate commands omit `--all-features`

**Gap**: The rubric's gate runs every step with `--all-features`. The local proof equivalents in `justfile` do not: `build` is `cargo build --workspace`, `test` is `cargo nextest run --workspace`, `clippy` is `cargo clippy --workspace --all-targets -- -D warnings`. `rtm-platform` declares a `test-support` feature (`crates/rtm-platform/Cargo.toml:20-21`) that is consumed only as a dev-dependency feature; the default gate never exercises `cargo check` against the feature in isolation across all consumers.

**Convention reference**: "Build and CI — The normal local proof should include `cargo build --workspace --all-features`, `cargo test --workspace --all-features`, `cargo clippy --workspace --all-targets --all-features -- -D warnings`."

**Evidence**:
- `justfile:8-9, 43-44, 99-100`.
- `crates/rtm-platform/Cargo.toml:20-21` — `[features] test-support = ["uuid"]`.

**Proposed fix**: Either add `--all-features` uniformly, or document the deliberate choice (e.g. `test-support` is dev-only and exercised via `rtm-daemon`/`rtm-cli` dev-deps). Recommended: add `--all-features` and confirm the build stays green; revisit if a feature genuinely conflicts.

**Effort**: trivial (the change itself) plus small (verify it stays green).

---

## G6. Three production `mod.rs` files survive PR #54

**Gap**: PR #54 was a strict-conventions pass, but three production `mod.rs` files remain. The rubric's exception list covers `tests/common/mod.rs` and generated indexes; these three are neither.

**Convention reference**: "Modules and Files — For new modules, prefer `foo.rs` plus `foo/` children. Avoid new `mod.rs` files. Accept existing `mod.rs` in old code when churn is not worth it. Reasonable `mod.rs` exceptions: `tests/common/mod.rs`, generated module indexes, legacy areas outside the change scope."

**Evidence**:
- `crates/rtm-store/src/sqlite/mod.rs` — production module index.
- `crates/rtm-cli/src/mcp/mod.rs` — production module index.
- `crates/rtm-cli/src/cli/mod.rs` — production module index.

The three `mod.rs` files that DO match an exception are correctly kept: `crates/rtm-core/tests/support/mod.rs`, `crates/rtm-cli/tests/common/mod.rs`, `crates/rtm-cli/src/generated/mod.rs` (the build.rs writes this one — generated index).

**Proposed fix**: Rename to the canonical 2024 form: `sqlite/mod.rs` → `sqlite.rs` + `sqlite/`; `mcp/mod.rs` → `mcp.rs` + `mcp/`; `cli/mod.rs` → `cli.rs` + `cli/`. Update parent declarations (`pub mod sqlite;` etc. stay the same; only files move).

**Effort**: small (three mechanical moves; preserve git history with `git mv`).

**Optional**: If the team agrees the rubric's "churn is not worth it" carve-out applies, document the decision in `PROJECT.md` and close G6. The decision is defensible — these are not new modules.

---

## G7. No `cargo deny` configuration

**Gap**: No `deny.toml`. License, advisory, and dependency policy is unenforced. With v0.7.1 of `lilo-rm-core` and `lilo-rm-client` publishing to crates.io, license/advisory drift is a real risk.

**Convention reference**: "Build and CI — Use `cargo deny` for license, advisory, and dependency policy."

**Evidence**: `ls deny.toml` → absent. No `cargo deny` step in `.github/workflows/ci.yml`.

**Proposed fix**: Add `deny.toml` (start from `cargo deny init`), restrict licenses to the allowlist that covers current deps, enable `[advisories] vulnerability = "deny"`. Add a `just deny` recipe and a `cargo deny check` step to CI.

**Effort**: small.

---

## G8. Missing crate-level docs on five crates

**Gap**: Five crates lack `//!` headers at the top of `lib.rs`. The rubric calls out crate-level docs for libraries and cross-crate contracts.

**Convention reference**: "Documentation — Library crates should have crate level docs. … For internal crates, document public items that are cross crate contracts."

**Evidence** (each crate's `lib.rs` starts directly with `mod` / `pub mod` declarations, no leading `//!`):
- `crates/rtm-daemon/src/lib.rs:1` — starts `mod backend;`.
- `crates/rtm-launchers/src/lib.rs:1` — starts `mod claude;`.
- `crates/rtm-platform/src/lib.rs:1` — starts `#[cfg(target_os = "macos")]`.
- `crates/rtm-store/src/lib.rs:1` — starts `pub mod config;`.
- `crates/rtm-cli/src/lib.rs:1` — starts `pub mod cli;`.

`rtm-core`, `rtm-client`, and `rtm-paths` correctly carry `//!` headers.

**Proposed fix**: Add a 2-4 line `//!` header to each of the five `lib.rs` files. Content per crate already exists in `PROJECT.md` and `MAP.md`; lift the one-liner that describes the crate's responsibility.

**Effort**: small.

---

## G9. Toolchain channel = "stable" diverges from `rust-version = "1.90"`

**Gap**: `rust-toolchain.toml` pins `channel = "stable"` while `[workspace.package]` declares `rust-version = "1.90"`. The rubric notes they should "usually match" — a floating `stable` will silently raise the effective compiler past 1.90 over time, breaking the contract `rust-version` advertises to downstream consumers of `lilo-rm-core` and `lilo-rm-client`.

**Convention reference**: "Edition and Toolchain — Pin the contributor toolchain in `rust-toolchain.toml`. Set `rust-version` in `[workspace.package]`. The toolchain channel and `rust-version` should usually match."

**Evidence**:
- `rust-toolchain.toml:2` — `channel = "stable"`.
- `Cargo.toml:21` — `rust-version = "1.90"`.

**Proposed fix**: Pin `channel = "1.90"` (or whatever version CI verifies on). Optionally add `rust-src` to `components` (rubric's recommended set is `["clippy", "rustfmt", "rust-src"]`; currently `["rustfmt", "clippy"]`).

**Effort**: trivial.

**Soft**: defensible if there is a documented reason to track stable. PR #54 didn't address it.

---

## G10. `build.rs` writes to repo-root `README.md` during cargo build

**Gap**: `crates/rtm-cli/build.rs:23-28, 105-114` writes generated content into `<repo-root>/README.md` between markers `<!-- rtm-admin-tools:start -->` … `<!-- rtm-admin-tools:end -->` during `cargo build`. It also creates `crates/rtm-cli/templates/SKILL.md`. The rubric calls out "Avoid generated docs or schemas without an authored source of truth" — here the authored source (`tool_contracts` in `lilo-rm-core`) exists, but the write happens at build time, not via an explicit code-gen invocation. Side effects:
- `cargo build` against a read-only checkout fails.
- A dirty git state after `cargo build` is the normal expected state when the registry changes, but a clean build with no convention work also touches files outside the build target directory.
- Downstream consumers building `lilo-rm-core` via crates.io never invoke this `build.rs`; only this repo's build path mutates files.

**Convention reference**: "Anti Patterns — Avoid generated docs or schemas without an authored source of truth." (The source exists, so the pattern is partially compliant.) Also: "Modules and Files — When changing generated surfaces, update the authored source first, then regenerate and verify the generated output."

**Evidence**:
- `crates/rtm-cli/build.rs:23-28` — `write_readme(repo_root, registry)`.
- `crates/rtm-cli/build.rs:105-114` — opens `repo_root.join("README.md")`, replaces a section by marker, writes back.

**Proposed fix**: Move README regeneration out of `build.rs` into an explicit `just regen-docs` (or `xtask`) target. Keep the marker-replacement logic, but invoke it from `just regen-docs` and check the result is committed via a CI diff check. `build.rs` retains the version stamping and `OUT_DIR`-target generated source writes only.

**Effort**: medium.

**Soft**: this is an established pattern in the repo. Reasonable to defer if the convergence list keeps scope tight.

---

## G11. Published crates do not inherit `version` from workspace

**Gap**: `lilo-rm-core` (`crates/rtm-core/Cargo.toml:5`) and `lilo-rm-client` (`crates/rtm-client/Cargo.toml:5`) declare `version = "0.7.1"` explicitly while `[workspace.package].version = "0.3.1"` (`Cargo.toml:15`). Two release stacks coexist: `release-plz` for `lilo-rm-*` (per-crate cadence) and `release-please` for the workspace meta-version. Reasonable for independent release cadence, but the rubric assumes a single shared version.

**Convention reference**: "Workspace Manifest — Member manifests should inherit shared fields: `version.workspace = true`."

**Evidence**:
- `Cargo.toml:14-22` — `[workspace.package] version = "0.3.1"`.
- `crates/rtm-core/Cargo.toml:5` — `version = "0.7.1"`.
- `crates/rtm-client/Cargo.toml:5` — `version = "0.7.1"`.
- `release-plz.toml` — `lilo-rm-core` and `lilo-rm-client` released together via `version_group = "rm-contract"`.

**Proposed fix**: Document the dual-release decision in `PROJECT.md` (and ideally in a header comment in the workspace `Cargo.toml`) so future readers don't try to "fix" the deviation. Optionally: split the published contract crates into their own workspace under `crates/contract/` and put the internal crates under a workspace with a single inherited version.

**Effort**: trivial (document only) or large (workspace split).

**Soft**: deliberate. List for visibility; not a hard violation if documented.

---

## G12. No production-targeted clippy lints beyond pedantic baseline

**Gap**: The rubric calls out useful clippy lints that aren't on the baseline pedantic warn set: `needless_pass_by_value`, `return_self_not_must_use`, `unnested_or_patterns`, `unwrap_used` for production crates, `expect_used` where panics are unacceptable. Currently the repo has no lint policy at all (see G1), so these are also missing. Worth listing separately because the team may choose to enable some of these even if they reject pedantic-as-default.

**Convention reference**: "Lints and Formatting — Useful individual Clippy lints: `needless_pass_by_value`, `return_self_not_must_use`, `unnested_or_patterns`, `unwrap_used` for production crates, `expect_used` where panics are unacceptable."

**Evidence**: subsumed by G1.

**Proposed fix**: When implementing G1, also add at least `unwrap_used = "warn"` and `expect_used = "warn"` for `rtm-daemon` and `rtm-cli` (production crates with the user-facing surface). Suppress narrowly in tests via `#[cfg_attr(test, allow(clippy::unwrap_used))]` or test-local `#[allow]`.

**Effort**: small.

---

## Sections checked and confirmed compliant

- **Async traits**: no `async-trait` or `async_trait` anywhere in source or `Cargo.toml`. Native trait futures used. ✓ ("Async" section of rubric)
- **Glob re-exports**: no `pub use ...::*` in any `lib.rs` (verified across all eight crates). ✓ ("Modules and Files" section)
- **Box<dyn Error>**: zero occurrences across all source files. ✓ ("Error Handling" section)
- **Error type naming**: `ErrorCode`, `ProtocolError`, `RuntimeKindParseError`, `ClientError`, `LauncherError`, `IsolationPolicyParseError`, `CaptureError`, `RuntimePathError` all end in `Error` per convention. ✓ ("API Design" section)
- **Workspace dependency inheritance**: every dep in every member uses `.workspace = true` (no version drift, no wildcard deps). ✓ ("Workspace Manifest" section)
- **Resolver 3 + edition 2024**: `Cargo.toml:12` `resolver = "3"`, `Cargo.toml:16` `edition = "2024"`. ✓ ("Edition and Toolchain" section)
- **thiserror in libs, anyhow in apps**: `lilo-rm-core` uses `thiserror`, `rtm-daemon` and `rtm-cli` use `anyhow` for binary orchestration. ✓ ("Error Handling" section)
- **tokio runtime**: tokio is the only async runtime in `Cargo.toml`. ✓ ("Async" section)
- **tracing**: in use across `rtm-daemon` and `rtm-cli`. ✓ ("Logging" section)
- **clap derive**: used in `rtm-cli`. ✓ ("Dependencies" section)
- **File LOC cap**: `scripts/check-loc-limit.sh` enforces 700 LOC across `.rs` and `.toml` files; largest file is `crates/rtm-cli/tests/spawn_target.rs` at 574 LOC. ✓ ("Modules and Files" section)
- **SAFETY comments**: all six `unsafe` blocks across the repo carry SAFETY: comments explaining the invariant. ✓ ("Unsafe" section)
- **`publish = false` on internal crates**: `rtm-daemon`, `rtm-cli`, `rtm-paths`, `rtm-platform`, `rtm-launchers`, `rtm-store` all declare `publish = false`. ✓
- **Release profile**: `Cargo.toml:58-62` has `codegen-units = 1`, `lto = true`, `strip = true`. ✓ ("Performance and Build Hygiene" section)
- **Arc<Mutex>**: a single occurrence in `crates/rtm-daemon/src/runtime_kill.rs:157` inside a `FakeKillTarget` test double. Not used as architecture. ✓

---

## Summary table

| ID  | Title                                       | Effort   | Soft? |
|-----|---------------------------------------------|----------|-------|
| G1  | No `[workspace.lints]` policy               | small    |       |
| G2  | No `forbid(unsafe_code)` on safe crates     | trivial  |       |
| G3  | No `cargo doc` in the gate                  | trivial  |       |
| G4  | `just check` is mutating                    | trivial  |       |
| G5  | Gate commands omit `--all-features`         | trivial  | ⚠     |
| G6  | Three production `mod.rs` files survive     | small    | ⚠     |
| G7  | No `cargo deny` configuration               | small    |       |
| G8  | Missing crate-level docs on five crates     | small    |       |
| G9  | Toolchain channel `stable` vs `1.90`        | trivial  | ⚠     |
| G10 | `build.rs` writes to repo-root `README.md`  | medium   | ⚠     |
| G11 | Published crates' version not inherited     | trivial† | ⚠     |
| G12 | Missing production-targeted clippy lints    | small    |       |

† G11 effort is trivial if "document the deviation" is accepted; large if workspace split is chosen.

## Open questions for pane B

- G6: does the team's "churn is not worth it" carve-out apply to the three production `mod.rs` files? PR #54 chose not to migrate them.
- G10: keep the build-time README write or move to an explicit codegen target?
- G11: document the dual-release stack or refactor the workspace shape?
