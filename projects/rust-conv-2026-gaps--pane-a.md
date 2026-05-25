---
title: Rust Conventions 2026 — Gap Report (Pane A / Claude draft)
type: research
tags: [rust-conventions-2026, gap-audit, littleorgans, moe, pane-a]
summary: Audit of identity-matters, session-matters, runtime-matters, transport-matters against ~/.mdx/research/rust-conventions-2026.md. Three buckets: conformance, wiring, enforcement.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-26
updated: 2026-05-26
---

# Rust Conventions 2026 — Gap Report (Pane A)

Round 1 draft. Reviewed by Codex (pane B). Orchestrator: `session-matters:general:2:3.1`.

## Scope correction up front

**transport-matters is not a Rust project.** Verified by file listing: no `Cargo.toml` exists at any level; the codebase is Python (`api/pyproject.toml`) plus TypeScript (`desktop/package.json`, `www/package.json`). The `rust-conventions-2026` guide therefore does not apply to its current implementation, only to any future Rust subdirectory it grows. I treat this as a finding (Wiring gap W4 below), not as silence in the audit.

The audit covers three repos:

- `identity-matters` (Rust workspace, 3 crates, 0.1.1)
- `session-matters` (Rust workspace, 6 crates, 0.2.8)
- `runtime-matters` (Rust workspace, 8 crates, 0.3.1)

A `littleorgans/` sub-directory exists with its own `Cargo.toml` (resolver 3); the brief did not list it, so I exclude it from this pass but flag it as worth a follow-up (W5).

## Bucket 1 — Conformance gaps (guide says X, repo state says Y)

| # | Repo | Item | Current | Guide expects | Suggested action |
|---|---|---|---|---|---|
| C1 | **all 3** | `[workspace.lints]` | absent in every workspace root | Shared lint policy with `pedantic = "warn"`, narrow allow-list, `unsafe_code = "forbid"` (or explicit allow if FFI) | Add `[workspace.lints]` block in each root and `[lints] workspace = true` to every member `Cargo.toml`. |
| C2 | **all 3** | `#![forbid(unsafe_code)]` / `#![deny(unsafe_code)]` | 0 occurrences across all 3 repos | Default forbid; opt-in only where FFI/libc/nix is unavoidable | Add `#![forbid(unsafe_code)]` to crates with no unsafe; explicit `#![allow(unsafe_code)]` on crates that need it (rtm-platform, im-store sqlite, etc.). |
| C3 | **all 3** | `SAFETY:` comments on `unsafe { ... }` blocks | identity-matters 1/1=0%; session-matters 10/10=0%; runtime-matters ~7/18=39% | Every unsafe block must carry a `SAFETY:` comment explaining the invariant | Sweep each unsafe block and add per-block `SAFETY:` comments. Per-block count is the metric, not total. |
| C4 | **session-matters** | `rust-toolchain.toml` | **missing** (identity-matters and runtime-matters both have one pinned to `stable`) | "Pin the contributor toolchain in `rust-toolchain.toml`" | Add `rust-toolchain.toml` matching the other two repos. |
| C5 | **session-matters** | `[workspace.package].rust-version` | missing (identity-matters: 1.90, runtime-matters: 1.90) | Set MSRV in `[workspace.package]` | Add `rust-version = "1.90"` (and `authors`, `homepage` while you're there). |
| C6 | **identity-matters** | `async-trait` on `Authorizer` | `#[async_trait]` used; **zero `dyn Authorizer` / `Box<dyn Authorizer>` / `&dyn Authorizer` / `Arc<dyn Authorizer>` call-sites in the repo** | "Avoid `async-trait` unless dynamic dispatch is required" | Either (a) introduce the dyn consumer the trait was designed for (the `lilo-im-daemon` swap that CLAUDE.md anticipates), or (b) drop `async-trait` and switch to `impl Future<Output = ...> + Send` until a dyn boundary actually exists. |
| C7 | **session-matters** | `async-trait` on `SpawnDriver` | `#[async_trait]` used on `RtmdDriver` impl | Same rule | Verify `dyn SpawnDriver` is the call shape. If not, drop `async-trait`. (I did not find the dyn call-site in a quick search; B should confirm before this is filed as a hard gap. See open questions.) |
| C8 | **all 3** | `mod.rs` in non-exempt locations | identity-matters: 1 (`im-store/src/sqlite/mod.rs`). session-matters: 4 non-exempt (`sm-store/src/sqlite/mod.rs`, `sm-cli/src/cli/mod.rs`, `sm-cli/src/mcp/mod.rs`, `sm-cli/src/mcp/tools/mod.rs`). runtime-matters: 3 non-exempt (`rtm-store/src/sqlite/mod.rs`, `rtm-cli/src/cli/mod.rs`, `rtm-cli/src/mcp/mod.rs`) plus 1 exempt (`generated/mod.rs`) and 2 exempt (`tests/common/mod.rs`, `tests/support/mod.rs`). | "Prefer `foo.rs` plus `foo/` children. Avoid new `mod.rs` files." Exemptions: `tests/common/mod.rs`, generated indexes, legacy. | Migrate non-exempt `mod.rs` to `foo.rs + foo/` layout. `sm-cli/src/cli/mod.rs` and `sm-cli/src/mcp/mod.rs` are pre-release and worth fixing now. |
| C9 | **session-matters** | `Box<dyn Error>` in `build.rs` | `sm-core/build.rs` and `sm-cli/build.rs` use `Result<(), Box<dyn Error>>` | Guide says "Avoid `Box<dyn Error>` for new structured error types." Build scripts are an idiomatic exception (one-off main), but the guide does not explicitly carve this out. | Soft gap. Decide whether to formally exempt `build.rs` in the guide, or convert to `anyhow::Result<()>` for consistency. |
| C10 | **all 3** | `publish = false` on internal-only crates | not set on `sm-daemon`, `sm-driver`, `im-stub`, `rtm-daemon`, etc. | "For monorepos with public and internal crates, make publishability explicit." | Either add `publish = false` to non-published crates, or rely on `release-plz` filtering (verify each repo's `release-plz.toml` excludes them). |
| C11 | **identity-matters** | local justfile uses `cargo fmt --all` (writes) and `cargo clippy --fix --allow-dirty` (writes) inside the `check` target | `check: fmt clippy loc` — both targets mutate the working tree | Guide expects `cargo fmt --all -- --check` and `cargo clippy --workspace --all-targets --all-features -- -D warnings` as **gates**, not mutators. | Split into `check` (gates: `fmt-check`, `clippy`) and `fix` (mutators: `fmt`, `clippy-fix`). See E2 below. |
| C12 | **all 3** | `--all-features` on clippy/build/test | `just clippy` is `cargo clippy --workspace --all-targets -- -D warnings` (identity-matters drops `--all-targets`) — no `--all-features` | Guide's "normal local proof" uses `--all-features` everywhere | Add `--all-features` to clippy, build, test recipes (or document why selective). |

## Bucket 2 — Wiring gaps (guide is unreachable from the repos)

| # | Repo | Item | Current | Action |
|---|---|---|---|---|
| W1 | **parent `littleorgans/CLAUDE.md` and `TLDR.md`** | guide reference | **zero references to `rust-conventions-2026.md` anywhere in any repo** (verified with `rg`) | Add a "Rust conventions" section to parent `CLAUDE.md` (which is also `AGENTS.md`) with a one-line pointer: "When the repo is silent on a Rust convention, consult `~/.mdx/research/rust-conventions-2026.md` per its 'silent or newly scaffolded' clause." |
| W2 | each repo's `TLDR.md` (= `CLAUDE.md` symlink) | guide reference | none | Add a single bullet under "Local conventions" in each repo: `Rust style: see ~/.mdx/research/rust-conventions-2026.md when this file is silent.` |
| W3 | discoverability of `~/.mdx/research/` | local research is outside repo and not symlinkable into git | Agents running in this repo won't know it exists | Either symlink the guide into `~/Dev/LLM/DEV/helioy/littleorgans/.references/rust-conventions-2026.md`, or add the path to a top-level `REFERENCES.md` that the parent CLAUDE.md links to. |
| W4 | **transport-matters** | guide applicability | repo is Python+TS; guide says nothing about non-Rust contexts | If a Rust subdirectory is planned, add an explicit "no Rust here yet" note to `transport-matters/TLDR.md` so future agents don't apply the guide to Python by analogy. |
| W5 | inner `littleorgans/littleorgans/` workspace | out-of-scope but resolver=3 confirmed | This workspace was not part of the brief but exists | Either include in next audit pass or document its scope/purpose. |

## Bucket 3 — Enforcement gaps (guide assumes a gate the repo doesn't run)

| # | Repo | Item | Current | Action |
|---|---|---|---|---|
| E1 | **all 3** | `cargo deny` | no `deny.toml` / `cargo-deny.toml` in any repo | Guide: "Use `cargo deny` for license, advisory, and dependency policy." Add `deny.toml` with at minimum the `RUSTSEC-*` advisory checks and a license allow-list; wire into CI. |
| E2 | **all 3** | `just check` is a mutator, not a gate | identity-matters: `fmt clippy loc` where both `fmt` and `clippy` write to disk. session-matters and runtime-matters: `fmt clippy-fix check-loc` — same problem; `clippy-fix` runs `--fix --allow-dirty`. A developer running `just check` before commit will have their working tree silently rewritten. | Make `check` invoke gate-only recipes: `fmt-check`, `clippy` (no `--fix`), `check-loc`. Keep `fix` as a separate, named-mutator recipe. This is the highest-leverage enforcement fix; current state defeats the purpose of "documented verification commands." |
| E3 | **all 3** | `cargo doc` in CI | identity-matters CI: no doc step. session-matters CI: doctest only (`just test-doc`), no `cargo doc`. runtime-matters CI: no doc step (only `just test-unit` includes `--doc`). | Guide: "Treat `cargo doc` as part of the public API surface… Broken intra doc links should fail CI when practical." Add `cargo doc --workspace --no-deps --all-features` with `RUSTDOCFLAGS='-D warnings'` to every CI job. |
| E4 | **session-matters** | CI toolchain pinning | CI uses `dtolnay/rust-toolchain@stable` and the repo has no `rust-toolchain.toml` and no `rust-version`. The Rust version is fully unpinned in source control. | Pair with C4/C5: once `rust-toolchain.toml` exists, replace `@stable` in CI with `dtolnay/rust-toolchain@v1` (which respects the toolchain file). |
| E5 | **identity-matters** | CI doctest step | CI runs `just check / build / test` but `just test` is `cargo nextest run` which **does not run doctests**. There is a `test-doc` recipe but CI never calls it. | Add `- run: just test-doc` to identity-matters CI. session-matters has this; runtime-matters does not. |
| E6 | **identity-matters** | clippy in CI | `just check` calls `cargo clippy --workspace --fix --allow-dirty -- -D warnings`. In CI, `--fix --allow-dirty` mutates a fresh checkout that gets discarded — the lint gate still fires via `-D warnings`, but the fix step is a wasteful no-op in CI. Locally it's harmful (E2). | Strip `--fix --allow-dirty` from the `clippy` recipe; keep a separate `clippy-fix` for developer use. |
| E7 | **runtime-matters** | doctest in CI | `just test` runs nextest only. The `test-unit` recipe includes `cargo test --workspace --doc`, but CI calls `just test`, not `just test-unit`. | Either fold doctest into the CI step, or rename for clarity. |
| E8 | **all 3** | `cargo fmt --check` as the canonical fmt gate | identity-matters has no `fmt-check` recipe at all; session-matters and runtime-matters have `fmt-check` but `check` calls `fmt` (the mutator) instead. CI never runs `fmt-check` standalone in any repo. | Add `fmt-check` to identity-matters; replace `fmt` with `fmt-check` in every `check` recipe. |
| E9 | **all 3** | `release-plz` parity | identity-matters and runtime-matters have `release-plz.toml`. **session-matters does not** (uses `release-please` via npm, see `release-please.yml`). | Guide: "Use `release-plz` for workspace crate release automation when publishing to crates.io." Either consolidate session-matters onto `release-plz`, or amend the guide to acknowledge `release-please` is an accepted alternative for npm-tooled monorepos. |

## Adversarial findings (what B is likely to miss)

I expect Codex to focus on the obvious mechanical gaps (lints, mod.rs, async-trait declarations) and miss these:

1. **E2 — `just check` is a mutator, not a gate.** The presence of `-D warnings` in the clippy line is a red herring; the recipe runs `clippy --fix --allow-dirty -- -D warnings` first. A reviewer who runs `just check && git commit -a` ships silently-rewritten code without realising clippy auto-fixed it. The guide's "Do not bypass the documented gate unless diagnosing a failure" presumes the documented gate is a gate. Here it is not.
2. **C6 — identity-matters has no dyn `Authorizer` consumer.** The trait exists; `async-trait` is applied to it; but no caller borrows `&dyn Authorizer`, owns `Box<dyn Authorizer>`, or stores `Arc<dyn Authorizer>`. The CLAUDE.md plan to "swap in `lilo-im-daemon`" forward-justifies the trait shape, but the `async-trait` macro is paying for dynamic dispatch the codebase doesn't use yet. Strict reading: drop async-trait, use `impl Future<Output = ...> + Send`, and re-add async-trait only when the daemon actually arrives.
3. **C3 — runtime-matters per-block SAFETY coverage.** Counting total `SAFETY:` occurrences (7) against total `unsafe { ... }` blocks (18) hides which blocks are uncovered. Codex may compute "7 ≥ 1, looks good." The correct metric is per-block coverage; ~11 unsafe blocks lack their own SAFETY comment.
4. **E4 — session-matters toolchain is completely unpinned.** No `rust-toolchain.toml`, no `rust-version`, and CI uses `@stable`. Builds will silently track whatever toolchain GitHub Actions advances to. Codex may catch C4 (no toolchain file) and C5 (no rust-version) individually but miss that **together** they leave zero pinning.
5. **W4 — transport-matters is not Rust.** If Codex audits transport-matters as if it were Rust (because the brief listed it), it will hallucinate gaps that don't exist. Verify by `find -name Cargo.toml`; result is empty.

## Open questions for B

1. Does `dyn SpawnDriver` exist somewhere in session-matters? I didn't find it on a quick grep; need a second pass before C7 is filed as a hard gap rather than "verify before fixing."
2. Should `build.rs` be a formal carve-out from the `Box<dyn Error>` anti-pattern (C9)?
3. W5 — should the inner `littleorgans/littleorgans/` workspace be included in the same gap pass?

## Sign-off

Pending B's draft and reconciliation.
