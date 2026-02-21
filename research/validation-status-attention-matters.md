---
title: attention-matters validation status
type: research
tags: [attention-matters, rust, validation, testing, ci, evaluation]
summary: attention-matters has strong Rust test and CI gates, but lacks a checked in semantic retrieval evaluation harness and does not gate the chat frontend.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-26
updated: 2026-04-26
---

## Executive Summary

attention-matters is a Rust workspace with extensive unit, integration, property, CLI, MCP protocol, snapshot, shutdown, coverage, audit, and benchmark gates. The active repo does not contain the previously remembered autoresearch eval harness source, gold standard, or eval scripts outside ignored `target/` artifacts, so semantic retrieval quality is not currently reproducible from tracked files.

## Project Metadata

- Language: Rust 2024 workspace, resolver 3, crates `am-core`, `am-store`, `am-cli`; see `Cargo.toml:1-7` and `Cargo.toml:9-12`.
- Core deps: `rand`, `rusqlite` bundled SQLite, `uuid`, `regex`, `serde`, `clap`, `tokio`, `axum`, `reqwest`; see `Cargo.toml:14-36`.
- Dev tooling: `nextest`, `rustfmt`, `clippy`, `cargo-audit`, `cargo-llvm-cov`, Criterion, proptest, insta; see `justfile:13-51`, `crates/am-core/Cargo.toml:15-22`, `crates/am-cli/Cargo.toml:43-47`.
- Frontend: tracked Next app in `chat/` with `lint`, `typecheck`, and `check` scripts, but not wired into root `justfile` or CI; see `chat/package.json:5-12`.
- fmm signal: `.fmm.db` exists in repo root and fmm indexed 100 files, 28,458 LOC.

## Architecture

Validation spans three layers:

1. Rust workspace checks: root `justfile` defines build, test, fmt, clippy, coverage, audit, bench, and bench gate commands at `justfile:4-51`.
2. CI checks: GitHub Actions runs `cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets -- -D warnings`, `cargo nextest run --workspace`, doctests, and `cargo audit`; see `.github/workflows/ci.yml:32-49`.
3. PR performance gate: CI benchmarks base and PR with Criterion, then compares with `scripts/bench-gate.sh --compare`; see `.github/workflows/ci.yml:51-77`.

## Key Patterns

- Broad Rust test surface: fmm found 467 tracked `#[test]` style attrs and 10 tracked insta snapshots.
- Protocol tests are black box over the `am serve` stdio JSON-RPC process. Key helper and test range is `crates/am-cli/tests/mcp_protocol_test.rs:13-636`.
- CLI tests use `assert_cmd` plus temp data dirs to isolate state. Coverage includes ingest, query, import/export, sync, GC, forget, and config path failures at `crates/am-cli/tests/cli.rs:8-860`.
- Store tests directly stress SQLite persistence, GC, incremental writes, checkpointing, buffer atomicity, and forget operations at `crates/am-store/src/store/tests.rs:33-985`.
- Property tests cover quaternion invariants through `proptest!` at `crates/am-core/tests/proptest.rs:58`.
- Benchmark gate has a first-run escape hatch: if no baseline is present under `target/criterion`, it exits success and skips comparison; see `scripts/bench-gate.sh:42-55`.

## Detailed Findings

### Current test setup

- Root test command: `just test` runs `cargo nextest run --workspace` and `cargo test --workspace --doc`; see `justfile:13-15` and `README.md:119-122`.
- CI mirrors this with nextest and doctests at `.github/workflows/ci.yml:38-44`.
- Key documented tests: proptest, MCP protocol, and shutdown are called out in `PROJECT.md:389-391`.
- am-core external tests cover ingest/query, conscious memory flow, multi episode recall, drift movement, serde roundtrip, repeated activation, and empty query behavior at `crates/am-core/tests/integration.rs:46-298`.
- am-cli snapshots cover MCP tool result contracts in `crates/am-cli/src/server/server_tests.rs:957-1191` and snapshot files under `crates/am-cli/src/server/snapshots/`.

### Current quality gates

Likely commands to run locally:

```sh
just fmt
cargo fmt --all -- --check
just clippy
cargo clippy --workspace --all-targets -- -D warnings
just test
just coverage
just audit
just bench-gate
```

Notes:

- `just check` currently runs `fmt` then `clippy`, but `clippy` uses `--fix --allow-dirty`; see `justfile:20-23`. That is unsafe as a validation only command because it can modify files.
- CI uses non-mutating format and clippy commands, which are safer for gates; see `.github/workflows/ci.yml:32-36`.
- Coverage is available but not in CI. Commands are defined at `justfile:37-48`.
- Audit is available locally and in CI at `justfile:50-51` and `.github/workflows/ci.yml:46-49`.

### Current eval setup

- No tracked `eval.sh`, `gold_standard.json`, `program.md`, `am-autoresearch` crate, or eval source was found via `git ls-files`.
- Only ignored build artifacts named `am-eval` exist under `target/`, which are not reproducible validation assets.
- This conflicts with prior memory that an autoresearch harness existed. Current tracked repository state does not validate that memory.
- Retrieval behavior is tested functionally through CLI, protocol, and server tests, but there is no checked in quality metric such as nDCG@10, MRR, recall@k, fixed corpus, or gold labels.

### Docs and repo hygiene

- README gives user facing install, MCP, CLI, architecture, math, and development commands at `README.md:33-123`.
- PROJECT.md contains deeper architecture, sync behavior, GC behavior, npm distribution, commands, and known issues at `PROJECT.md:21-40`, `PROJECT.md:296-331`, `PROJECT.md:336-391`, and `PROJECT.md:395-405`.
- `docs.llm/CODE_REVIEW_2026-03-21.md:6` says 418 tests passing as of March 21, 2026. Current tracked source has more test attrs, so this document is useful history but stale as status evidence.
- Repo root `.gitignore` ignores fmm DB, target, Nancy, npm generated binary, and chat build artifacts at `.gitignore:1-17`.
- Chat frontend has its own `check` script at `chat/package.json:5-12`, but root CI does not run it.

## Dependencies

Critical validation dependencies:

- `assert_cmd`, `predicates`, `tempfile` for CLI tests, `crates/am-cli/Cargo.toml:43-47`.
- `insta` for JSON snapshot contracts, `crates/am-cli/Cargo.toml:45`.
- `proptest` for property tests, `crates/am-core/Cargo.toml:18`.
- `criterion` for `am-core` and `am-store` benches, `crates/am-core/Cargo.toml:17-22`, `crates/am-store/Cargo.toml:18-26`.
- `critcmp` is required by the benchmark gate, `scripts/bench-gate.sh:13-14` and `scripts/bench-gate.sh:28-31`.

## Risks and Missing Validation

1. Retrieval quality is not measured by a checked in evaluation harness.
2. `just check` is mutating because it delegates to clippy `--fix --allow-dirty`; use CI commands for read only validation.
3. Benchmark gate can pass without a comparison baseline on first run, by design, at `scripts/bench-gate.sh:52-55`.
4. Coverage exists locally but is not enforced in CI.
5. Chat frontend checks are defined but not included in root justfile or CI.
6. Docs include stale test counts from March 21, 2026.
7. Release build matrix builds `am-cli` only and package publish path is tested indirectly, not through an install smoke test in CI; see `.github/workflows/release.yml:94-107` and `.github/workflows/release.yml:150-164`.

## Relevance to Helioy

attention-matters already has strong structural validation for MCP memory behavior. The largest Helioy gap is semantic quality validation: Helioy needs reproducible memory retrieval scoring before treating this as a dependable organizational identity or memory substrate.

## Next Focus Areas

1. Restore or recreate a tracked semantic eval harness with fixed corpus, gold labels, and nDCG@10 or MRR.
2. Add a non-mutating `just validate` that mirrors CI exactly: fmt check, clippy, nextest, doctests, audit.
3. Wire `chat` validation into CI with `npm ci && npm run check` under `chat/`.
4. Add a release smoke test that installs the packaged npm wrapper and runs `am --help` plus `am serve` handshake.
5. Decide whether coverage thresholds matter, then gate `cargo llvm-cov nextest --workspace` if they do.

## Open Questions

- Was the autoresearch harness intentionally removed, never committed, or only built locally under `target/`?
- Should performance gating include `am-store` `save_system` benchmark, not only `am-core` drift?
- Should root `just check` be changed to read only validation semantics, with a separate `just fix` for mutating clippy fixes?
