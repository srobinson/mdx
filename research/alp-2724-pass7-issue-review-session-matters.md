---
title: ALP-2724 Pass 7 Issue Review for session-matters
type: research
tags: [session-matters, linear, moe-review, cli, rust]
summary: Pass 7 cold-read review of the ALP-2724 CLI unification tree found no substantive blockers.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

ALP-2724 unifies the `sm` CLI surface around shape A resource-bucket subcommands, session CRUD nouns, declarative `sm create session`, imperative `sm run`, `sm run --force`, and per-resource help-source decomposition. Pass 7 reviewed the live Linear tree and current source for public API impact, runtime registry public surface stability, verification coverage, test isolation, snapshot workflow, and commit convention. No substantive blockers were found.

## Project Metadata

- Language: Rust, edition 2024.
- Workspace crates: `sm-paths`, `sm-core`, `sm-store`, `sm-driver`, `sm-daemon`, `sm-cli`.
- Version in workspace: `0.2.4`.
- Build system: Cargo workspace with `just` recipes.
- Indexed by fmm: `.fmm.db` present at repo root.
- Key dependencies relevant to review: `clap`, `tokio`, `toml`, `insta`, `tempfile`, `lilo-rm-core`, `lilo-rm-client`.

## Architecture

- `sm-cli` exposes the CLI parser and dispatcher as a library. `crates/sm-cli/src/lib.rs:1-5` exports `cli`, `mcp`, `tool_contracts`, `tool_docs`, and `tool_examples`; `run()` dispatches parsed `Command` variants at `crates/sm-cli/src/lib.rs:13-31`.
- CLI grammar lives in `crates/sm-cli/src/cli/cli_def.rs`. Current public parser symbols include `GetResource::Agent` and `GetResource::Agents` at lines 99-104, `DeleteResource::Agent` at lines 146-150, and `DeleteAgentArgs` at lines 152-162.
- Runtime tool contract loading lives in `crates/sm-core/src/tool_contracts.rs`. Current `contract_registry()` is public and returns `&'static ToolContractRegistry` at lines 13-18. The registry type and accessors are at lines 20-72.
- The standard verification path uses `justfile:43-44`, which runs `cargo nextest run --workspace`.
- CLI integration tests use `DaemonFixture` in `crates/sm-cli/tests/common/mod.rs`. It starts per-test runtime and session daemons with tempdir-scoped sockets, database, home, and runtime paths at lines 27-57, and cleans up in Drop via lines 118-140.

## Key Patterns

- Shape A migration intentionally changes user-facing CLI grammar, not just docs. Public `sm-cli` clap AST names will change as a side effect, but these are parser internals rather than `sm-core` protocol types.
- Runtime registry consumers should keep `contract_registry()` stable while changing only the compile-time source aggregation behind it.
- Test isolation relies on tempdir-scoped `SM_HOME`, `HOME`, `RTM_SOCKET_PATH`, `RTM_DB_PATH`, and `RTM_HOME`, so nextest parallelism is expected to be safe.

## Detailed Findings

### Public API and symbol stability

Live source exposes `sm_cli::cli` publicly through `crates/sm-cli/src/lib.rs:1`, and the `cli_def` parser structs and enums are public. Current agent-named parser items are public:

- `GetResource::Agent` and `GetResource::Agents`, `crates/sm-cli/src/cli/cli_def.rs:99-104`.
- `DeleteResource::Agent`, `crates/sm-cli/src/cli/cli_def.rs:146-150`.
- `DeleteAgentArgs`, `crates/sm-cli/src/cli/cli_def.rs:152-162`.

This means external Rust code could theoretically match these symbols. The pass did not treat that as a blocker because ALP-2724 explicitly authorizes the pre-1.0 CLI grammar break, the affected symbols are `sm-cli` parser internals, and no `sm-core` protocol/session type is implicated by the rename.

### W4b public surface impact

`contract_registry()` currently has the public signature `pub fn contract_registry() -> &'static ToolContractRegistry`, `crates/sm-core/src/tool_contracts.rs:13-18`. `ToolContractRegistry` and its public accessors are at `crates/sm-core/src/tool_contracts.rs:20-72`. ALP-2735 states this is a pure layout change with no API changes, and both proposed reconciliation options can preserve this signature. No gate-body constraint between option (a) and option (b) is needed on public signature grounds.

### Justfile test recipe completeness

`just test` runs `cargo nextest run --workspace`, `justfile:43-44`. Worker tests added under `sm-cli`, `sm-daemon`, `sm-driver`, or other workspace crates are covered by the standard gate command. No issue-body amendment is needed.

### Test isolation and concurrency

`DaemonFixture` creates a fresh tempdir and per-test runtime/session socket and DB paths, `crates/sm-cli/tests/common/mod.rs:27-57`. It sets `SM_HOME`, `HOME`, `RTM_SOCKET_PATH`, `RTM_DB_PATH`, and `RTM_HOME` for spawned daemons. Drop cleanup stops `smd` and `rtmd`, `crates/sm-cli/tests/common/mod.rs:118-140`. This supports parallel nextest execution. No `--test-threads=1` requirement was found.

### Snapshot regeneration discoverability

Snapshot tests use `insta` in `crates/sm-cli/tests/mcp_schema_snapshot_test.rs:1-18`, and `insta` is declared in `Cargo.toml:42-45`. There is no `just update-snapshots` recipe, but `cargo insta accept` is the standard workflow. This is not a substantive worker-readiness defect.

### Commit message convention

No worker body needs to restate the `nancy[ALP-XXXX]:` commit convention. It is operational convention rather than task semantics.

## Dependencies

- `clap` provides the public parser AST and help generation surface affected by W1/W2/W3/W5.
- `insta` provides snapshot assertions for MCP schema and instructions.
- `tempfile` underpins daemon fixture isolation.
- `cargo nextest` is the workspace test runner invoked by `just test`.

## Relevance to Helioy

This review confirms the ALP-2724 worker tree is ready for autonomous execution from a late-pass MoE perspective. The probe also documents a useful distinction for Helioy pre-1.0 CLI crates: public Rust parser internals can change with user-facing CLI grammar when the gate explicitly authorizes the CLI break, but protocol crates such as `sm-core` should preserve exported runtime contracts unless a worker explicitly scopes an API migration.

## Open Questions

- None blocking. Future release hardening may choose to make `sm-cli::cli` private or narrower if parser internals are not intended as a stable library API.
