---
title: ALP-2081 and ALP-2084 Review for context-matters
type: research
tags: [context-matters, cm-cli, review, alp-2081, alp-2084]
summary: Read-only review found ALP-2081 and ALP-2084 passing acceptance with no blocking findings.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

The context-matters worktree at `/Users/alphab/Dev/LLM/DEV/helioy/context-matters-worktrees/nancy-ALP-2054` was reviewed read only for ALP-2081 and ALP-2084. Both issues pass their stated acceptance criteria. No blocking correctness, regression, or DRY findings were found.

## Project Metadata

- Language: Rust workspace.
- Reviewed package: `cm-cli`.
- Baseline: `origin/nancy/ALP-2054` at `9f341c5161f4dde42aacd2192f65187488245505`.
- Reviewed HEAD: `626614230f6aef444ab023a434a290b83dfe2d68`.
- Branch state during review: `nancy/ALP-2054...origin/nancy/ALP-2054 [ahead 6]`.
- Structural signal: fmm index available and used for topology, outlines, symbol reads, and dependency checks.

## Architecture Context

- `crates/cm-cli/src/cli/store.rs` is a discoverable CLI stub for `cm store`. It does not open the store and does not mutate data.
- `crates/cm-cli/src/main.rs` dispatches `Commands::Store { scope, .. }` directly to `cli::store::run(scope)`, so store validation happens before any Curator guidance output.
- Scope parsing is centralized in `cm_capabilities::scope::ScopeSelector`.
- Tool and skill documentation is generated from `tools.toml` by `crates/cm-cli/build.rs` into generated MCP schemas, generated CLI help constants, and `crates/cm-cli/templates/SKILL.md`.

## Detailed Findings

### ALP-2081: PASS

Acceptance reviewed: `cm store --scope auto` must exit nonzero with clear validation, current `cwd_inferred` and exact scope selectors must preserve non-mutating Curator guidance, tests must cover removed auto selector, and `cargo test -p cm-cli` must pass.

Evidence:

- `store.rs` validates the optional scope with `ScopeSelector::parse` before printing the Curator guidance: `crates/cm-cli/src/cli/store.rs:25-28`.
- Scope parsing rejects `auto` with the message `scope='auto' has been removed; use scope='cwd_inferred'`: `crates/cm-capabilities/src/scope/types.rs:71-75`.
- `main.rs` passes the parsed `Store` scope into the store stub: `crates/cm-cli/src/main.rs:117-118`.
- Manual verification:
  - `target/debug/cm store --scope auto` exited `1` and printed `error: scope='auto' has been removed; use scope='cwd_inferred'`.
  - `target/debug/cm store --scope cwd_inferred` printed Curator guidance and exited successfully.
  - `target/debug/cm store --scope global/project:helioy` printed Curator guidance and exited successfully.
- CLI tests cover removed and current selectors:
  - `store_stub_rejects_removed_auto_scope_selector`: `crates/cm-cli/tests/cli_integration.rs:109-116`.
  - `store_stub_accepts_current_scope_selectors`: `crates/cm-cli/tests/cli_integration.rs:119-128`.
- Full requested verification passed: `cargo test -p cm-cli` completed with all unit, integration, protocol, snapshot, and doctest suites passing.

Quality assessment: implementation is small and DRY. It reuses centralized `ScopeSelector` validation rather than duplicating selector rules.

### ALP-2084: PASS

Acceptance reviewed: concrete `cwd_inferred` CLI example, generated skill and MCP docs guidance, refreshed snapshots or generated artifacts, and no public examples that recommend `scope_path` or `scope=auto`.

Evidence:

- CLI help includes a concrete cwd based browse example: `cm browse --scope cwd_inferred --cwd /path/to/repo` in `crates/cm-cli/src/cli/help_text.rs:84-90`.
- CLI test asserts that example is present and that stale flags are absent from browse help: `crates/cm-cli/tests/cli_flags.rs:105-116`.
- Source of truth docs in `tools.toml` include the MCP guidance example `cx_browse(scope: "cwd_inferred", cwd: "/path/to/repo")`: `tools.toml:47-53`.
- Generated skill docs contain the same guidance: `crates/cm-cli/templates/SKILL.md:67-73`.
- The protocol test asserts the generated skill doc contains the scope migration boundary and the concrete `cx_browse` example: `crates/cm-cli/tests/mcp_protocol/tools_list.rs:249-260`.
- Generated MCP schemas were refreshed. Each tool input schema now gets `additionalProperties: false` from `build.rs`: `crates/cm-cli/build.rs:212-216`. A generated example is visible in `crates/cm-cli/src/mcp/generated_schema/cx_browse.json:1-5`.
- `cargo test -p cm-cli` ran `build.rs`; `git status --short` was clean afterward, which supports that checked-in generated artifacts are current.
- `target/debug/cm --markdown-help | rg 'scope_path|scope=auto|cx_browse\(scope: "cwd_inferred"|--scope-path'` returned no stale public CLI markdown terms. Repository search showed stale terms only in negative guidance, persisted response schema fields, or tests, not as recommended public examples.

Quality assessment: the change keeps documentation centralized through `tools.toml` and generated artifacts. The CLI example is placed in browse specific help where it is most actionable.

## Dependencies and Regression Surface

- Critical dependency: `cm_capabilities::scope::ScopeSelector` validates all current selectors and rejects removed selectors.
- Runtime mutation risk for `cm store`: low. The store stub still performs no store I/O and only prints guidance after successful selector validation.
- Documentation drift risk: low for generated artifacts because `build.rs` writes generated schema, help, and skill files from `tools.toml`, and the test run left the worktree clean.

## Nonblocking Findings

1. `crates/cm-cli/src/cli/store.rs:23-24` still says `run` returns `Ok(())` after printing and exits 0. That is now only true for accepted selectors. Invalid `--scope auto` returns an error before printing.
2. The unit test comment at `crates/cm-cli/src/cli/store.rs:67-69` still says the stub is infallible, but `run(Some("auto"))` is intentionally fallible now.
3. `crates/cm-cli/tests/tools_integration/store.rs:61` is named `store_scope_auto_creates_scope_chain`, but the test now uses an exact scope at lines 65-72. Rename would reduce future confusion.

## Relevance to Helioy

These changes keep the Helioy context store request surface aligned around `scope` and the reserved `cwd_inferred` selector. They also prevent stale client fields from silently passing through MCP schemas, which is useful for agent workflows that depend on clear request boundaries.

## Open Questions

- None blocking. The only suggested follow up is cleanup of stale comments and the stale test name.
