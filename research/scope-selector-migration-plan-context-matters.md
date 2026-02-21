---
title: Scope selector migration plan for context-matters
type: research
tags: [context-matters, scope, mcp, linear, worktree]
summary: Full breaking migration plan for public scope selection using `scope` and reserved value `cwd_inferred`.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

context-matters should use one public request parameter, `scope`, for all agent and user request surfaces. `scope_path` should remain only as an internal exact `ScopePath` field for stored data, filters, and store traits.

The migration is intentionally breaking: public `scope_path` request inputs should be rejected. The reserved value for inferred scope selection is `cwd_inferred`, with git worktree aware normalization so Nancy worktrees resolve to the source repository identity.

## Project Metadata

- Language: Rust 2024 workspace with TypeScript frontend.
- Workspace crates: `cm-core`, `cm-store`, `cm-capabilities`, `cm-cli`, `cm-web`.
- Public contract root: `tools.toml` generates MCP schemas, CLI help, and skill docs.
- Verification commands: `just check`, `just test`.
- fmm index: `.fmm.db` exists at repo root.

## Architecture

The right boundary is:

- `cm-core`: keeps durable exact paths through `ScopePath`, `EntryFilter.scope_path`, `NewEntry.scope_path`, and `ContextStore` methods.
- `cm-capabilities`: owns unresolved request scope selection and cwd inference.
- `cm-cli`: maps MCP and CLI request inputs into capability request structs.
- `cm-web`: maps HTTP query params and frontend URL state into capability request structs.

The planned unresolved selector is:

```rust
pub enum ScopeSelector {
    Path(ScopePath),
    CwdInferred { cwd: Option<PathBuf> },
}
```

Resolved capability paths still use exact `ScopePath` before calling store methods.

## Key Patterns

- Public request input should use `scope` only.
- Internal exact identity should use `ScopePath` and field name `scope_path` where data is already resolved.
- `cwd_inferred` should infer from git source repo identity, not transient linked worktree names.
- Writes may accept explicit `cwd_inferred`, but must reject ambiguous or low confidence inference before any write.

## Detailed Findings

### Worktree inference

Git can distinguish the current worktree from the source repository. In a linked worktree, `git rev-parse --show-toplevel` returns the linked worktree path, while `git rev-parse --path-format=absolute --git-common-dir` points at the source repository `.git` directory. When the common dir basename is `.git`, its parent is the source repo root.

For a cwd under `context-matters-worktrees/nancy-ALP-1768`, inference should use repo basename `context-matters`, not `nancy-ALP-1768`.

### Vertical integration paths

Research artifacts produced by explorer agents:

- `~/.mdx/research/scope-handling-vertical-path-context-matters.md`
- `~/.mdx/research/cm-cli-scope-surface-refactor-context-matters.md`
- `~/.mdx/research/vertical-integration-scope-refactor-context-matters.md`

Key files and symbols identified:

- `crates/cm-capabilities/src/scope/types.rs`: `BrowseScopeInput`, `ScopeResolution`, `ResolvedBrowseScope`.
- `crates/cm-capabilities/src/scope/resolution.rs`: `resolve_browse_scope`, `normalize_browse_scope`, `resolve_auto_scope`.
- `crates/cm-capabilities/src/browse.rs`: `BrowseRequest`, `browse`.
- `crates/cm-capabilities/src/recall/types.rs`: `RecallRequest`.
- `crates/cm-capabilities/src/store.rs`: `StoreRequest`, `store`.
- `crates/cm-capabilities/src/deposit.rs`: `DepositRequest`, `deposit`.
- `crates/cm-capabilities/src/export.rs`: `ExportRequest`, `export`.
- `crates/cm-cli/src/mcp/tools/*.rs`: MCP parameter parsing.
- `tools.toml`: public MCP contract and generated documentation source.
- `crates/cm-web/src/api/agent.rs`: `BrowseQuery`, `execute_browse`.
- `crates/cm-web/frontend/src/api/client.ts`: frontend request parameter types.
- `crates/cm-web/frontend/src/routes/feed/search.ts`: URL state currently uses `scope_path`.

### Spec

A concise implementation spec was written to:

`~/.mdx/projects/context-matters-spec-scope-selector-migration.md`

Main decisions:

- Public `scope` only.
- Reserved value `cwd_inferred`.
- No public `scope_path` legacy alias.
- Keep `ScopePath` internal and exact.
- `cx_browse` omitted scope defaults to `cwd_inferred`.
- `cx_recall` omitted scope defaults to `global`.
- `cx_store` and `cx_deposit` omitted scope default to `global`.
- `cx_export` omitted scope exports all active entries.

## Linear Issues

Parent issue:

- `ALP-2054`: Unify scope selector semantics across context-matters

Subissues:

- `ALP-2055`: Add ScopeSelector capability type
- `ALP-2056`: Normalize cwd through git worktree metadata
- `ALP-2057`: Refactor browse resolution around ScopeSelector
- `ALP-2058`: Apply ScopeSelector to read capabilities
- `ALP-2059`: Apply ScopeSelector to write capabilities
- `ALP-2060`: Replace MCP tool inputs with scope
- `ALP-2061`: Migrate cm-web request surfaces to scope
- `ALP-2062`: Refresh generated public artifacts
- `ALP-2063`: Add vertical scope migration tests
- `ALP-2064`: Publish scope migration documentation
- `ALP-2065`: Run final scope migration verification

## Dependencies

Critical dependencies and what they provide:

- `serde`: request deserialization and public parameter parsing.
- `cm_core::ScopePath`: canonical exact path validation and serialization.
- `ContextStore::list_scopes`: required for cwd inferred candidate scoring.
- Git CLI or equivalent repository metadata access: required for worktree source root normalization.
- `tools.toml` build generation: keeps MCP schemas, CLI help, and skill docs aligned.

## Relevance to Helioy

This migration directly affects agent memory placement across Helioy. It removes a class of accidental global writes and makes Nancy worktrees resolve to the intended source repository scope.

## Open Questions

- The exact confidence threshold for inferred writes should be decided during `ALP-2059`. Recommendation: require a unique high confidence top candidate.
- Git detection can initially use the git CLI for simplicity. A later hardening pass could replace this with a Rust git library if process spawning becomes a concern.
