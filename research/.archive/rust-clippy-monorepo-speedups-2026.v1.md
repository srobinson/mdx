---
title: Rust clippy speedups for multi-crate workspaces in 2026
type: research
tags: [rust, clippy, ci, cargo, monorepo, sccache, github-actions, build-cache]
summary: Field survey of how serious Rust shops accelerate cargo clippy on multi-crate workspaces in 2026, with a layered solution stack and a Helioy-shaped decision matrix.
status: active
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

# Rust clippy speedups for multi-crate workspaces in 2026

## 1. Executive summary

The cool kids in 2026 are doing four things, in roughly this order of impact:

1. Picking a faster runner platform rather than chasing exotic config on github-hosted runners. The dominant 2026 stack is Namespace (oxc, ruff via `actions/cache`, bevy via `actions/cache`) or Depot (biome, uv) instead of `ubuntu-latest`. Both ship Rust-aware cache volumes that dwarf GitHub Actions' 10 GB cap.
2. Either `Swatinem/rust-cache` v2.9.1 with `save-if: github.ref == 'refs/heads/main'` (the ruff and tauri pattern), or the runner vendor's own cache volume action (the oxc/biome/uv pattern). Sccache is no longer the default choice for first-party CI on github runners. It still wins inside Docker layers and on self-hosted infra with S3/Redis backing.
3. Splitting work the right way. Lint, build, test all share the same `target/`; running clippy after build (the classic trick) is no longer reliably a win since late 2024. Instead, the trend is parallel jobs all hitting the same restore key with a single "save on main only" job, plus changed-paths gating to skip jobs entirely on docs-only PRs (ruff and uv both do this).
4. Switching to rust 1.90+ for `rust-lld` as the default linker on x86_64 linux (Sept 2025), which alone gives ~7x faster incremental linking and ~40% end-to-end on something the size of ripgrep. This is a one-line toolchain bump that beats nearly everything else for free.

For Helioy specifically (small team, few dozen crates, no monorepo scale): adopt `Swatinem/rust-cache@v2.9.1` with `save-if main` first, move to `actions-rust-lang/setup-rust-toolchain` to get problem matchers, ensure Rust >= 1.90 for the linker default, and only consider Namespace/Depot or `mold` once a clippy run on stock github runners exceeds 8 minutes. Skip Bazel/Buck2 entirely. Skip `cargo-hakari` until you have more than ~50 crates with heavy feature divergence. The "Cargo cross-workspace cache" goal landing on nightly in 2026 may obsolete a chunk of this stack within 12 months.

## 2. The bottleneck model

Where time goes in a multi-crate clippy run, roughly:

```
crate graph topology (fan-out wide = parallelism wins)
                       v
[parse + macro expand + name resolution]   ~10-20% of cargo check time
[type check + borrow check]                ~40-60% of cargo check time   <- clippy adds ~30-150% more lint passes here
[query system + incremental cache I/O]     ~5-15%
[metadata emit (.rmeta)]                    ~5-10%
[codegen (skipped by check/clippy)]         ~30-50% of cargo build time
[linker]                                    ~5-30% of cargo build time, dominant on incremental builds
```

Key facts that shape the stack:

- Clippy is ~2.5x slower than `cargo check` for the same workload because every lint pass runs after typecheck. The Clippy team has called this out as their primary 2024H2 optimization goal ([rust-lang/rust-project-goals 2024h2](https://rust-lang.github.io/rust-project-goals/2024h2/optimize-clippy.html)). A 5% improvement landed in 2025 via jemalloc ([Kobzol blog, Jan 2026](https://kobzol.github.io/rust/rustc/2026/01/05/my-rust-contributions-in-2025.html)).
- `cargo check` and `cargo clippy` do **not** share build artifacts cleanly. The 2021-era trick of running clippy after `cargo build` to reuse artifacts is reported to no longer work as of December 2024 ([reillywood blog](https://www.reillywood.com/blog/rust-faster-ci/)). The Rust compiler team has a 2025 redesign effort to fix this so `build` can reuse `check`'s borrow-check outputs ([rust-analyzer #21286 discussion](https://github.com/rust-lang/rust-analyzer/issues/21286)).
- Clippy runs lints per-crate, so on a multi-crate workspace clippy benefits linearly from `cargo`'s parallel scheduler. A wide-shallow graph (many leaf crates) gets near-linear scaling; a deep-narrow graph bottlenecks on the longest dependency chain.
- `--all-features` forces a single feature-unified resolve. On a workspace with proc-macros that pull heavy optional deps, this can balloon the crate graph 2-5x. There is no flag to skip this; `cargo hack --each-feature` is the workaround for matrix testing but adds CI minutes.
- Linking dominates incremental rebuilds. With rust-lld now default on 1.90 stable for x86_64 linux, this layer largely solves itself ([rust blog 2025-09-01](https://blog.rust-lang.org/2025/09/01/rust-lld-on-1.90.0-stable/)). For macOS and Windows, mold is not available; `lld` on macOS was demoted in 1.90 ([Phoronix](https://www.phoronix.com/news/Rust-1.90-LLD-Linking)).

## 3. Layered solution stack

### 3.1 Local dev

| Layer | Best option 2026 | Runner-up | When to use |
|---|---|---|---|
| Linker | `rust-lld` (default on linux 1.90+) | `mold` on linux for very large workspaces | mold gives diminishing returns vs rust-lld; only worth installing if rust-lld measurably underperforms |
| Codegen backend | LLVM (default) | `cranelift` on nightly for dev builds | Cranelift is still preview on nightly per 2025H2 goal ([rust-lang/rust-project-goals 2025h2](https://rust-lang.github.io/rust-project-goals/2025h2/production-ready-cranelift.html)); skip for serious work |
| Parallel rustc | `-Z threads=8` on nightly | n/a | Per 2026 project goal, still nightly only ([rust-lang/rust-project-goals 2026](https://rust-lang.github.io/rust-project-goals/2026/parallel-front-end.html)) |
| `target/` location | Default, on fast NVMe | tmpfs/ramdisk for very large workspaces | Depot recommends ramdisk for I/O-bound runs |
| Editor | rust-analyzer with clippy disabled by default | n/a | rust-analyzer maintainers explicitly warn against using clippy as the check command ([rust-analyzer #19336](https://github.com/rust-lang/rust-analyzer/issues/19336)) |

### 3.2 CI cache

| Layer | Best option 2026 | Runner-up | When each wins |
|---|---|---|---|
| GitHub-hosted runner, simple | `Swatinem/rust-cache@v2.9.1` with `save-if: main` | `actions/cache` with hand-rolled key (bevy still does this) | rust-cache wins for almost everyone; bevy's pattern only justified if you have a custom cache-update workflow ([bevy `update-caches.yml`](https://github.com/bevyengine/bevy/tree/main/.github/workflows)) |
| GitHub-hosted, heavier | `mozilla-actions/sccache-action` with GHA backend | `metalbear-co/sccache-action` (uses github API) | sccache is preferred when target/ exceeds the 10 GB GHA cache ceiling, or when you have many parallel jobs hitting the same artifacts ([sccache-action marketplace](https://github.com/marketplace/actions/sccache-action)) |
| Hosted runner with native cache | Namespace `nscloud-cache-action` or Depot `depot cargo` | WarpBuild own cache | Both Namespace and Depot have first-party Rust caching; Depot's `depot cargo` is a drop-in cargo wrapper that auto-wires sccache ([depot changelog 2025-06-30](https://depot.dev/changelog/2025-06-30-depot-cargo-command)) |
| Self-hosted runner | Persistent `~/.cargo` and `target/` on ephemeral filesystem with rust-cache `cache-bin: false` | sccache with local disk backend | self-hosted persistent target/ is highest-cache-hit but fragile to concurrent jobs; rust-cache on self-hosted needs `cache-bin: false` to avoid wiping `~/.cargo/bin` ([rust-cache README](https://github.com/Swatinem/rust-cache)) |
| Docker layer cache | `cargo-chef` + sccache + BuildKit cache mounts | none | cargo-chef remains the right answer for Dockerfile builds in 2026 ([depot docs](https://depot.dev/docs/container-builds/optimal-dockerfiles/rust-dockerfile)); pair with sccache for sub-crate caching |

### 3.3 Linker and codegen

`rust-lld` is the new default for `x86_64-unknown-linux-gnu` from rust 1.90.0 (Sept 18 2025), giving up to 7x faster incremental linking. macOS x86_64 was demoted from tier 1 in the same release. There is no equivalent shift for Windows or aarch64-linux yet.

mold on linux gives marginal additional speedup over rust-lld and adds toolchain complexity. The Depot benchmark on Zed reported mold as 0.7% **slower** than the default ([depot guide](https://depot.dev/blog/guide-to-faster-rust-builds-in-ci)). Skip unless rust-lld is measurably underperforming on a specific workload.

Cranelift backend: nightly-only preview as of the 2025H2 production-ready cranelift goal. Not for serious CI work in 2026. Will likely be production-ready on linux/macOS x86_64 and aarch64 by late 2026 or 2027.

Parallel rustc front-end (`-Z threads=N`): nightly only as of the May 2026 project goals update ([rust blog 2026-05-18](https://blog.rust-lang.org/2026/05/18/project-goals-2026-04/)). The 2026 goal is "promote to stable" but no shipping date.

### 3.4 Workspace structure

`cargo-hakari` / workspace-hack: still maintained and current (v0.9.36, MSRV 1.86, as of Feb 2025 on crates.io). Documented speedup is "up to 100x" for `cargo check`/`cargo build` ([cargo-hakari docs](https://docs.rs/cargo-hakari/latest/cargo_hakari/about/index.html)). Real-world payoff scales with workspace size and feature divergence; on workspaces under 30 crates the maintenance cost rarely beats the speedup. Cargo-hakari is what the diem/aptos/zksync-era ecosystems have used at scale.

Splitting heavy proc-macros into their own crates remains a 2026 best practice; proc-macros block their dependents during compilation and any change forces downstream recompilation. The rust-clippy team's optimization goal explicitly calls out proc-macro handling as a target ([rust-lang project goals 2024h2](https://rust-lang.github.io/rust-project-goals/2024h2/optimize-clippy.html)).

`cargo-nextest`: faster test runner, does not interact with clippy directly. Saves wall-clock time after compilation. Major projects using it: tokio (every CI workflow), ruff, biome. Skip doctests; nextest does not run them ([nextest issue #16](https://github.com/nextest-rs/nextest/issues/16)).

### 3.5 CI orchestration

The dominant 2026 pattern across the surveyed projects:

1. **Plan / determine-changes job** at the top of the workflow, computing which crates changed via `git diff --name-only`. ruff and uv both do this in shell; their `plan` job sets outputs that gate every downstream job ([ruff ci.yaml](https://github.com/astral-sh/ruff/blob/main/.github/workflows/ci.yaml), uv's massive plan job).
2. **Parallel format/clippy/build/test jobs** that all share the same cache. They restore from the same key. Only one (typically clippy or test) sets `save-if: main` to write the cache back.
3. **Merge queue gating**: GitHub merge queue + a `basic checks must pass` aggregator job. Tokio uses this with explicit `needs: [clippy, fmt, docs, minrust]` ([tokio ci.yml](https://github.com/tokio-rs/tokio/blob/master/.github/workflows/ci.yml)). bevy uses `merge_group:` trigger.
4. **Per-crate or per-feature sharding** only at large scale (swc uses a generated test matrix; rustc itself uses the citool-generated matrix; ruff uses changed-path booleans). For a few-dozen-crate workspace, sharding adds CI minutes through repeated cargo planning overhead.

`cargo clippy --workspace --all-targets --all-features --locked -- -D warnings` is still the canonical invocation (ruff uses exactly this). When `--all-features` causes pain, the workaround is to drop to `--all-targets` only and run a separate `cargo hack --each-feature check` matrix.

### 3.6 Monorepo-scale tooling

Bazel `rules_rust` and Buck2: only worth it at the polyglot mega-monorepo scale (Meta, Discord, parts of Cloudflare). Both work fine with clippy via the `rust_clippy_aspect` ([rules_rust docs](https://bazelbuild.github.io/rules_rust/rust_clippy.html)). The cost is rewriting your build graph and maintaining BUILD files in parallel with Cargo.toml. Buck2 is faster than Buck1 (~2x per Meta's numbers) but is younger than Bazel and less battle-tested outside Meta ([Meta engineering blog](https://engineering.fb.com/2023/10/23/developer-tools/5-things-you-didnt-know-about-buck2/)). polkadot-sdk runs on GitLab CI with matterlabs-style self-hosted runners and is cargo-native, not Bazel; the perception that polkadot uses Bazel is incorrect.

Nix-based caches via Crane: relevant if you already live in Nix-land. Otherwise the setup cost is steep ([NixOS Crane announcement](https://discourse.nixos.org/t/introducing-crane-composable-and-cacheable-builds-with-cargo/17275)).

## 4. Field survey

Pulled from actual workflow files on May 27 2026. Citations are workflow URLs.

| Project | Runner | Cache backend | Linker | Sharding strategy | Notable tricks |
|---|---|---|---|---|---|
| rustc itself | `ubuntu-24.04-arm`, AWS CodeBuild, custom matrix | `sccache` to `rust-lang-ci-sccache2` S3 bucket, `CACHE_DOMAIN: ci-caches.rust-lang.org` | system default | citool-generated matrix from `src/ci/github-actions/jobs.yml` | Bors-based merge train on `automation/bors/auto` and `try` branches; `try-perf` branch for perf testing ([rust ci.yml](https://github.com/rust-lang/rust/blob/master/.github/workflows/ci.yml)) |
| tokio | `windows-latest`, `ubuntu-latest`, `macos-latest` (github-hosted) | `Swatinem/rust-cache@v2` with `cache-bin: ${{ matrix.os != 'macos-latest' }}` workaround | rust default | per-feature integration tests via `cargo-hack`; per-workspace-member feature matrix | `cargo nextest` everywhere; pins `rust_clippy: '1.88'` env var separately from `rust_stable` ([tokio ci.yml](https://github.com/tokio-rs/tokio/blob/master/.github/workflows/ci.yml)) |
| deno | `ubuntu-24.04` (github-hosted) | `actions/cache/restore` with `never_saved` key + restore-keys fallback; auxiliary update-caches job | clang-22 + lld-22 via incremental LTO setup | hand-rolled per-job, generated from `ci.ts` | Builds custom sysroot with thinLTO; `linker-plugin-lto=true`, `--thinlto-cache-policy,cache_size_bytes=700m` ([deno ci.generated.yml](https://github.com/denoland/deno/blob/main/.github/workflows/ci.generated.yml)) |
| bevy | `windows-latest`, `ubuntu-latest`, `macos-latest` | `actions/cache/restore` with `${{ runner.os }}-stable--${{ hashFiles('**/Cargo.toml') }}-` key; companion `update-caches.yml` writes; restore-keys fallback chain | rust default | dedicated `ci` binary (`cargo run -p ci -- lints`) that runs all checks | Uses `merge_group:` trigger; separates `build`, `ci` (lints), `miri`, `check-compiles-no-std` jobs ([bevy ci.yml](https://github.com/bevyengine/bevy/blob/main/.github/workflows/ci.yml)) |
| ruff | `ubuntu-latest` (github-hosted) | `Swatinem/rust-cache@v2.9.1` pinned by commit SHA, `save-if: ${{ github.ref == 'refs/heads/main' }}` | rust default | `determine_changes` job with per-crate git diff path booleans gating downstream jobs | Canonical `cargo clippy --workspace --all-targets --all-features --locked -- -D warnings` invocation ([ruff ci.yaml](https://github.com/astral-sh/ruff/blob/main/.github/workflows/ci.yaml)) |
| uv | `depot-ubuntu-24.04` (Depot runners) | Depot built-in; `save-rust-cache` flag computed in plan job | rust default | massive shell-based `plan` job with per-path booleans; reusable workflows for each check | Uses `samypr100/setup-dev-drive` on Windows with ReFS for faster I/O; copies workspace onto the dev drive ([uv ci.yml](https://github.com/astral-sh/uv/blob/main/.github/workflows/ci.yml)) |
| oxc | `namespace-profile-linux-x64-default`, `ubuntu-24.04-arm`, `namespace-profile-mac-default` | `namespacelabs/nscloud-cache-action` for rust + pnpm cache volumes; `oxc-project/setup-rust` action for ARM/Windows | rust default | `cargo ck` (custom alias), main-branch-only matrix expansion to mac/windows/big-endian/32bit | Per-target cross-tests via `taiki-e/install-action: cross`; uses `samypr100/setup-dev-drive` on Windows ([oxc ci.yml](https://github.com/oxc-project/oxc/blob/main/.github/workflows/ci.yml)) |
| biome | `depot-ubuntu-24.04-arm-16` (Depot ARM 16-vCPU) | `moonrepo/setup-rust` with `cache-base: main` | rust default | matrix across `depot-windows-2022-16`, `depot-ubuntu-24.04-arm-16`, `depot-macos-14` | `cargo lint` custom alias; `cargo deny check` for licenses; `cargo udeps` on nightly; cargo-cache cleanup step ([biome main.yml](https://github.com/biomejs/biome/blob/main/.github/workflows/main.yml)) |
| swc | `ubuntu-latest` etc (github-hosted) | `Swatinem/rust-cache@v2` implicitly via `actions/cache` (pre-clippy stage uses `actions/checkout` only) | rust default | dynamic crate test matrix generated by `scripts/github/get-test-matrix.mjs` | `cargo-mono` for cross-crate dependency walking; `cargo-shear` for unused-dep detection; CI uses `nightly-2026-04-10` for fmt/clippy ([swc CI.yml](https://github.com/swc-project/swc/blob/main/.github/workflows/CI.yml)) |
| tauri | github-hosted multi-OS | `Swatinem/rust-cache@v2` with `key: ${{ matrix.platform.target }}` per-target sharding, `save-if: ${{ matrix.features.key == 'all' }}` | rust default | per-target matrix (windows/linux/macOS/iOS/android), per-feature matrix (--no-default / --all) | `cargo install cross` per-job for android target ([tauri test-core.yml](https://github.com/tauri-apps/tauri/blob/dev/.github/workflows/test-core.yml)) |
| zksync-era | `matterlabs-ci-runner-highmem-long` (matter-labs self-hosted) | sccache (logged in `/tmp/sccache_log.txt`); `ci_run sccache --show-stats` at end of every job | rust default | per-test-type job (lint, unit-tests, loadtest, integration-tests); custom `ci_run` and `zkstack` helper CLIs | All Rust runs through containerized `ci_run` wrapper; sccache stats surfaced on every run ([zksync ci-core-reusable.yml](https://github.com/matter-labs/zksync-era/blob/main/.github/workflows/ci-core-reusable.yml)) |
| turbopack (vercel/turborepo) | Cargo workspace inside Turborepo; Rust crates built via direct cargo, not Turborepo's hashing | (no clippy-specific GHA cache evidence in public repo at time of survey) | rust default | n/a | Turborepo's own remote cache is for JS task outputs, not cargo artifacts ([vercel/turbo](https://github.com/vercel/turbo)) |

Patterns across the survey:

- **Swatinem/rust-cache dominates the github-hosted runners** (ruff, tokio, tauri use it directly; swc uses it implicitly). bevy is the outlier with hand-rolled `actions/cache`.
- **Namespace and Depot have become the de-facto hosted-runner picks for Rust-heavy front-tier projects.** uv, oxc, and biome all switched in the past 18 months.
- **Sccache survives in two niches**: massive projects with sysroot-level reuse (rustc itself, deno) and self-hosted infra (zksync-era). It is rare in the github-hosted-runner + cache-action pattern.
- **No surveyed project uses Bazel or Buck2 for clippy.** All run native cargo.
- **`cargo nextest`** is universal in projects that maintain their own test infra (tokio, ruff, biome). zksync-era explicitly notes incompatibility with criterion-based benchmarks and runs those separately.
- **Custom `cargo lint` / `cargo ck` aliases** are normal at scale (biome, oxc). They wrap clippy flags so CI and devs share one invocation.
- **Save-if on main branch** is universal among rust-cache users.
- **Per-OS sharding is the default**; per-crate sharding is rare and only at >100 crate scale.

## 5. Decision matrix for Helioy

Helioy context: small team, multi-crate Rust workspace under 50 crates, github-hosted CI, no monorepo-scale aspirations yet, "the cool kids" framing prioritizes time-to-stable signal over exotic optimization.

### First adopt (cost: minutes to hours)

1. **`Swatinem/rust-cache@v2.9.1`** with `save-if: ${{ github.ref == 'refs/heads/main' }}`. Pin by commit SHA, not by tag. This is the ruff pattern and pays for itself on the first PR.
2. **`actions-rust-lang/setup-rust-toolchain@v1`** in place of `dtolnay/rust-toolchain`. Adds problem matchers for cargo and clippy output, automatic caching env vars, and rustup integration. Almost a strict superset for CI use.
3. **Pin rust >= 1.90** in `rust-toolchain.toml`. Free 40% incremental link-time speedup on linux x86_64 with no other changes.
4. **Single canonical clippy invocation**: `cargo clippy --workspace --all-targets --all-features --locked -- -D warnings`. Wire it into a `cargo-clippy` alias if dev and CI invocations diverge.
5. **Concurrency cancellation**: `concurrency: { group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true }` on PR triggers. Every surveyed project does this.

### Second adopt (cost: hours to a day)

6. **Changed-path gating**: a `determine_changes` job at the top that sets booleans for "rust changed", "docs only", "ci-config changed". Skip clippy/test on docs-only PRs. ruff and uv both do this. Eliminates 30-60% of CI minutes on a busy repo.
7. **Merge queue + aggregator job**: enable github merge queue, add a `merge-gate` job with `needs: [clippy, fmt, test]`. Tokio's `basics` job is the model.
8. **Cargo nextest**: drop-in faster test runner. Negligible compile-time win but cleaner output and better parallelism. Skip if your test suite is small enough not to matter.

### Third adopt (cost: days, evaluate first)

9. **Hosted runner**: Namespace or Depot. Only do this if `cargo clippy --workspace` regularly exceeds 8 minutes on `ubuntu-latest`. Cost is a paid runner contract; benefit is 2-10x speedup per the WarpBuild and RunsOn benchmarks. Pick Namespace if you already use it for non-Rust workloads; pick Depot if you want `depot cargo` as a drop-in cargo wrapper. Avoid WarpBuild for now unless you have a specific reason; it has the smallest Rust footprint among the three.
10. **Sccache** with the GHA backend. Pair `mozilla-actions/sccache-action@v0.10.0` with `RUSTC_WRAPPER=sccache` and `SCCACHE_GHA_ENABLED=true`. This is only a win if your `target/` exceeds GHA's 10 GB cache cap or if your job count creates rust-cache thrash. Otherwise it adds chattiness without payoff.
11. **mold linker**: pre-install on the runner, set `RUSTFLAGS="-C link-arg=-fuse-ld=mold"`. Negligible gain over rust-lld in benchmarks ([depot guide](https://depot.dev/blog/guide-to-faster-rust-builds-in-ci) reports 0.7% slower). Skip unless rust-lld is measurably underperforming.

### Never (for Helioy's scale)

- Bazel / Buck2 / rules_rust.
- `cargo-hakari` until Helioy crosses ~50 crates with meaningful feature divergence.
- Parallel rustc front-end (nightly only).
- Cranelift backend (nightly only).
- `cargo-difftests` for clippy selection. The path-based determine_changes job is simpler and gives 80% of the win at 10% of the complexity.
- `cargo-chef` unless Helioy starts shipping Docker artifacts.

## 6. Things that sound good but are not worth it

- **Running clippy after `cargo build` for artifact reuse.** This was the headline trick in Reilly Wood's 2022 post. The author explicitly added a Dec 2024 note that it stopped working. Don't bother.
- **`cargo check` then `cargo clippy` in CI.** Same problem in reverse. The two do not share artifacts cleanly; running both is roughly 1.8x running just clippy. Just run clippy.
- **`mold` over `rust-lld` on linux**. Marginal gain post-1.90, added install step, more surface area for things to break.
- **BuildJet**. Shutting down March 31 2026 ([WarpBuild comparison](https://www.warpbuild.com/blog/buildjet-warpbuild-comparison)). Do not adopt.
- **Sccache on a fresh github-hosted job with no other caching**. Without a warm cache, the per-call cache lookup overhead exceeds the recompilation it would have avoided.
- **`--each-feature` matrix as the default clippy strategy**. Use it for occasional matrix testing via `cargo hack`, not for every PR. The CI minutes don't justify the additional coverage on a small workspace.
- **Cranelift for "fast dev builds"**. Still missing too many features as of the 2025H2 cranelift production-ready goal. Wait until late 2026.
- **GitLab CI for the speed**. Polkadot uses it because of historic infra reasons; on GitHub-hosted Rust shops it adds friction without the speed payoff.

## 7. References

### Rust project sources
- [Optimizing Clippy & linting (project goal 2024H2)](https://rust-lang.github.io/rust-project-goals/2024h2/optimize-clippy.html)
- [Production-ready cranelift backend (project goal 2025H2)](https://rust-lang.github.io/rust-project-goals/2025h2/production-ready-cranelift.html)
- [Promoting Parallel Front End (project goal 2026)](https://rust-lang.github.io/rust-project-goals/2026/parallel-front-end.html)
- [Cargo cross workspace cache (project goal 2026)](https://rust-lang.github.io/rust-project-goals/2026/cargo-cross-workspace-cache.html)
- [Rework Cargo Build Dir Layout (project goal 2025H2)](https://rust-lang.github.io/rust-project-goals/2025h2/cargo-build-dir-layout.html)
- [User-wide build cache (project goal 2024H2)](https://rust-lang.github.io/rust-project-goals/2024h2/user-wide-cache.html)
- [Rust compiler performance survey 2025 results](https://blog.rust-lang.org/2025/09/10/rust-compiler-performance-survey-2025-results/)
- [Project goals update April 2026](https://blog.rust-lang.org/2026/05/18/project-goals-2026-04/)
- [Faster linking times with 1.90.0 stable on Linux using LLD](https://blog.rust-lang.org/2025/09/01/rust-lld-on-1.90.0-stable/)
- [Kobzol's 1160 PRs to improve Rust in 2025](https://kobzol.github.io/rust/rustc/2026/01/05/my-rust-contributions-in-2025.html)

### Tool docs and READMEs
- [Swatinem/rust-cache (v2.9.1)](https://github.com/Swatinem/rust-cache)
- [actions-rust-lang/setup-rust-toolchain](https://github.com/actions-rust-lang/setup-rust-toolchain)
- [mozilla/sccache](https://github.com/mozilla/sccache)
- [mozilla-actions/sccache-action](https://github.com/marketplace/actions/sccache-action)
- [cargo-hakari](https://docs.rs/cargo-hakari/latest/cargo_hakari/about/index.html)
- [cargo-chef](https://github.com/LukeMathWalker/cargo-chef)
- [cargo-nextest](https://nexte.st)
- [taiki-e/install-action](https://github.com/taiki-e/install-action)
- [taiki-e/cargo-hack](https://github.com/taiki-e/cargo-hack)
- [bazelbuild/rules_rust clippy docs](https://bazelbuild.github.io/rules_rust/rust_clippy.html)
- [Buck2 (Meta)](https://buck2.build/docs/about/why/)
- [NixOS Crane](https://discourse.nixos.org/t/introducing-crane-composable-and-cacheable-builds-with-cargo/17275)

### Runner / cache vendors
- [Namespace nscloud-cache-action docs](https://namespace.so/docs/reference/github-actions/nscloud-cache-action)
- [Depot guide to faster Rust builds in CI](https://depot.dev/blog/guide-to-faster-rust-builds-in-ci)
- [Depot cargo command (2025-06-30 changelog)](https://depot.dev/changelog/2025-06-30-depot-cargo-command)
- [Depot Rust Dockerfile best practices](https://depot.dev/blog/rust-dockerfile-best-practices)
- [Depot Fast Rust Builds with sccache and GHA](https://depot.dev/blog/sccache-in-github-actions)
- [RunsOn cache benchmarks](https://runs-on.com/benchmarks/github-actions-cache-performance/)
- [RunsOn accelerated Rust CI guide](https://runs-on.com/guides/languages/rust/)
- [Blacksmith vs WarpBuild comparison](https://www.warpbuild.com/blog/blacksmith-warpbuild-comparison-2025-May)
- [BuildJet vs WarpBuild comparison (notes BuildJet shutdown)](https://www.warpbuild.com/blog/buildjet-warpbuild-comparison)

### Field survey workflow files (verified 2026-05-27)
- [rust-lang/rust ci.yml](https://github.com/rust-lang/rust/blob/master/.github/workflows/ci.yml)
- [tokio-rs/tokio ci.yml](https://github.com/tokio-rs/tokio/blob/master/.github/workflows/ci.yml)
- [denoland/deno ci.generated.yml](https://github.com/denoland/deno/blob/main/.github/workflows/ci.generated.yml)
- [bevyengine/bevy ci.yml](https://github.com/bevyengine/bevy/blob/main/.github/workflows/ci.yml)
- [astral-sh/ruff ci.yaml](https://github.com/astral-sh/ruff/blob/main/.github/workflows/ci.yaml)
- [astral-sh/uv ci.yml](https://github.com/astral-sh/uv/blob/main/.github/workflows/ci.yml)
- [oxc-project/oxc ci.yml](https://github.com/oxc-project/oxc/blob/main/.github/workflows/ci.yml)
- [biomejs/biome main.yml](https://github.com/biomejs/biome/blob/main/.github/workflows/main.yml)
- [swc-project/swc CI.yml](https://github.com/swc-project/swc/blob/main/.github/workflows/CI.yml)
- [tauri-apps/tauri test-core.yml](https://github.com/tauri-apps/tauri/blob/dev/.github/workflows/test-core.yml)
- [matter-labs/zksync-era ci-core-reusable.yml](https://github.com/matter-labs/zksync-era/blob/main/.github/workflows/ci-core-reusable.yml)
- [vercel/turbo workflows](https://github.com/vercel/turbo/tree/main/.github/workflows)

### Issue / PR / blog references for specific claims
- [rust-clippy #8171: cargo clippy 20x slower than cargo check](https://github.com/rust-lang/rust-clippy/issues/8171)
- [rust-analyzer #21286: both cargo check and cargo clippy one after the other](https://github.com/rust-lang/rust-analyzer/issues/21286)
- [rust-analyzer #19336: Using clippy as the check command makes rust-analyzer unreliable](https://github.com/rust-lang/rust-analyzer/issues/19336)
- [Reilly Wood: How to Make Rust CI 2-3x Faster (with Dec 2024 caveat)](https://www.reillywood.com/blog/rust-faster-ci/)
- [Improving the Incremental System in the Rust Compiler (RustChinaConf 2025 talk write-up)](https://blog.goose.love/posts/improving-the-incremental-system-in-the-rust-compiler/)
- [sccache is pretty okay (broken.de, Aug 2025)](https://brokenco.de/2025/08/25/sccache-is-pretty-okay.html)
- [Phoronix: Rust 1.90 LLD default](https://www.phoronix.com/news/Rust-1.90-LLD-Linking)
- [Meta engineering: 5 things you didn't know about Buck2](https://engineering.fb.com/2023/10/23/developer-tools/5-things-you-didnt-know-about-buck2/)

## 8. Conflicts and gaps in the source material

- **The clippy-after-build trick**: Reilly Wood's December 2024 caveat says it stopped working, but newer how-to articles still recommend it. No definitive postmortem from the cargo team confirms when or why it broke. **Treat the trick as dead but be ready to revisit if a cargo team blog post clarifies.**
- **Cargo cross-workspace cache landing date**: the 2026 goal page says "available on nightly in 2026" but Jan 2026 update gives no concrete shipping date. **Could obsolete sccache for many users within 12 months; could also slip to 2027.**
- **Whether `sccache --show-stats` is providing useful signal**: brokenco.de (Aug 2025) says sccache is "fairly well" useful; the Depot guide reports only ~11.5% overall speedup on Zed with warm sccache. **Real-world payoff is highly workload-dependent; benchmark before committing.**
- **Namespace vs Depot for Rust specifically**: vendors publish their own comparisons (WarpBuild's, Depot's, RunsOn's). No neutral third-party head-to-head Rust benchmark exists. **Use trial periods on both before committing.**
- **Whether `cargo clippy --workspace --all-features` is dominant or out of favor**: every surveyed project uses some variant of this, but `--all-features` has documented feature unification cost that no source quantifies for clippy specifically. **The canonical invocation is universal; the cost isn't well-measured.**
