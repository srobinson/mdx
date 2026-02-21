---
title: ALP-2054 core semantics review for context-matters
type: research
tags: [context-matters, alp-2054, review, scope-selector]
summary: Read only review of ScopeSelector, cwd_inferred resolution, write policy, persistence identity, and MCP docs alignment found no blocking issues.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

Lane A reviewed the ALP-2054 core semantics across `cm-core`, `cm-capabilities`, `cm-store`, and MCP request documentation. No blocking correctness, quality, cleanliness, or DRY issues were found in the inspected lane.

## Project Metadata

- Language: Rust workspace, plus generated MCP JSON schemas and CLI help.
- Workspace areas reviewed: `crates/cm-core`, `crates/cm-capabilities`, `crates/cm-store`, `crates/cm-cli/src/mcp`, `tools.toml`.
- fmm status: `fmm validate` passed with 324 indexed files.

## Architecture

- Durable identity remains in `cm-core`: `Entry.scope_path` and `NewEntry.scope_path` are exact `ScopePath` values in `crates/cm-core/src/types/entry.rs:128` and `crates/cm-core/src/types/entry.rs:169`.
- Store APIs still accept exact `ScopePath` values for persistence and queries, including `create_entry`, `resolve_context`, `search`, `browse`, and `export` in `crates/cm-core/src/store.rs:65`, `crates/cm-core/src/store.rs:99`, `crates/cm-core/src/store.rs:120`, `crates/cm-core/src/store.rs:131`, and `crates/cm-core/src/store.rs:253`.
- `cm-core` and `cm-store` had no diff in `main...HEAD`, so the migration remains contained in capability and adapter layers.

## Key Patterns

- Public scope selection is centralized in `ScopeSelector`, with exact path and `cwd_inferred` variants only: `crates/cm-capabilities/src/scope/types.rs:9`.
- `auto` is rejected at parse time with replacement guidance: `crates/cm-capabilities/src/scope/types.rs:71`.
- `cwd` can only be attached to `cwd_inferred`; exact path plus `cwd` is rejected: `crates/cm-capabilities/src/scope/types.rs:33`.
- `cwd_inferred` resolution uses git metadata and normalizes linked worktrees to the source repository root when the common git directory is the source `.git`: `crates/cm-capabilities/src/scope/resolution.rs:211`, `crates/cm-capabilities/src/scope/resolution.rs:232`.
- Read policy accepts any resolved scope path. Write policy requires high confidence and one unique top candidate: `crates/cm-capabilities/src/scope/types.rs:174`, `crates/cm-capabilities/src/scope/types.rs:183`, `crates/cm-capabilities/src/scope/types.rs:194`.

## Detailed Findings

### No blocking findings

No severity findings were identified for lane A.

### Acceptance validation

- ScopePath remains durable identity. Evidence: `Entry.scope_path`, `NewEntry.scope_path`, `EntryFilter.scope_path`, and store trait methods still use `ScopePath` in `crates/cm-core/src/types/entry.rs:128`, `crates/cm-core/src/types/entry.rs:169`, `crates/cm-core/src/types/browse.rs:87`, and `crates/cm-core/src/store.rs:101`.
- Writes with `cwd_inferred` require one unique high confidence scope. Evidence: `store` and `deposit` call `resolve_scope_selection` then `write_scope_path` before `ensure_scope_chain`: `crates/cm-capabilities/src/store.rs:105`, `crates/cm-capabilities/src/store.rs:109`, `crates/cm-capabilities/src/store.rs:123`, `crates/cm-capabilities/src/deposit.rs:142`, `crates/cm-capabilities/src/deposit.rs:146`, `crates/cm-capabilities/src/deposit.rs:152`. The strict policy lives in `crates/cm-capabilities/src/scope/types.rs:194`.
- Rejected inferred writes create no entries or scope rows. Evidence: store tests assert zero entries and unchanged scope counts for low confidence and ambiguous inferred writes at `crates/cm-capabilities/tests/store_tests.rs:217` and `crates/cm-capabilities/tests/store_tests.rs:237`. Deposit tests cover medium confidence, ambiguity, and empty cwd at `crates/cm-capabilities/tests/deposit_tests.rs:96`, `crates/cm-capabilities/tests/deposit_tests.rs:120`, and `crates/cm-capabilities/tests/deposit_tests.rs:145`.
- No public `auto` request path remains in core capability parsing. Evidence: `ScopeSelector::from_str` rejects `auto` at `crates/cm-capabilities/src/scope/types.rs:71`.
- No migrated MCP request schema exposes `scope_path` or `scope_mode` as input fields. Evidence: generated schema inspection showed migrated inputs only expose `scope`; output schemas retain `scope_path` and `scope_mode` only for persisted data and resolution metadata.
- MCP help docs are aligned. Evidence: `tools.toml:47` documents public request inputs as `scope` only, `tools.toml:49` documents `cwd_inferred`, and `tools.toml:51` documents rejection of `scope_path`, `scope_mode`, and `scope="auto"`. CLI help generated from that contract shows `--scope` and `cwd_inferred` for browse and store.

## Dependencies

- `git` CLI is used by `SystemCwdEnvironment` for cwd normalization in `crates/cm-capabilities/src/scope/resolution.rs:211`.
- `cm-store` remains the SQLite persistence adapter and continues to persist exact `scope_path` text through existing schema and store methods.

## Verification Commands

All commands were run from `/Users/alphab/Dev/LLM/DEV/helioy/context-matters-worktrees/nancy-ALP-2054`.

- `fmm validate`: passed.
- `cargo fmt --all -- --check`: passed.
- `cargo clippy --workspace --all-targets -- -D warnings`: passed.
- `cargo nextest run -p cm-core`: 89 passed.
- `cargo nextest run -p cm-capabilities`: 286 passed.
- `cargo nextest run -p cm-cli`: 129 passed.
- `cargo nextest run -p cm-store`: 113 passed.
- `cargo test --workspace --doc`: passed, one ignored doctest and one passing doctest.
- `cargo run -q -p cm-cli -- browse --help | rg -n 'scope|cwd_inferred|scope_path|scope_mode|auto'`: showed `--scope` and `cwd_inferred`, no removed request fields.
- `cargo run -q -p cm-cli -- store --help | rg -n 'scope|cwd_inferred|scope_path|scope_mode|auto'`: showed `--scope` and `cwd_inferred`, no removed request fields.

Note: I did not run `just check` because this repository defines it as a mutating command: `cargo fmt --all` plus `cargo clippy --fix --allow-dirty`. I ran the read only equivalents instead.

## Relevance to Helioy

The migration supports Helioy worktree based agent operation by resolving `cwd_inferred` through source repo git metadata rather than transient worktree names. This matches the intended context store behavior for Nancy worktrees.

## Open Questions

- None for lane A.
