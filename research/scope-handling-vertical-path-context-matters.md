---
title: Scope Handling Vertical Path in context-matters
type: research
tags: [context-matters, cm-capabilities, cm-core, scope, refactor]
summary: cm-capabilities has split scope request semantics across typed ScopePath, string scope, and cwd based inference, while cm-core remains cleanly centered on ScopePath.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

Scope handling is vertically split. `cm-core` has a single validated `ScopePath` domain type and store APIs that consume either `ScopePath` or `Option<ScopePath>`. `cm-capabilities` adds request layer compatibility around this, with `BrowseRequest` carrying both `scope` and `scope_path`, while write capabilities use only `scope_path` strings and recall uses an optional typed `ScopePath`.

The clean refactor seam is a new request layer `ScopeSelector` in `cm-capabilities`, plus a small resolver that emits the existing `ScopePath` or scope resolution metadata. `cm-core` should stay focused on validated paths and store filters, not cwd inference.

## Project Metadata

- Language: Rust 2024 workspace
- Packages in scope: `crates/cm-core`, `crates/cm-capabilities`
- Core dependencies: `serde`, `serde_json`, `uuid`, `chrono`, `ts-rs`, `thiserror`, `blake3`
- Capability dependencies: `cm-core`, `serde`, `serde_json`, `uuid`, `chrono`, `ts-rs`
- Indexed by fmm: yes, 320 Rust or generated files total. In scope: `cm-capabilities` has 89 files and 13,964 LOC. `cm-core` has 16 files and 2,225 LOC.

## Architecture

### `cm-core`: domain path and store contracts

Relevant files and symbols:

- `crates/cm-core/src/types/scope.rs`
  - `ScopePath`
  - `ScopePath::parse`
  - `ScopePath::validate`
  - `ScopePath::global`
  - `ScopePath::ancestors`
  - `ScopePath::leaf_kind`
  - `ScopePath::depth`
  - `ScopeKind`
  - `Scope`
  - `NewScope`
- `crates/cm-core/src/types/browse.rs`
  - `EntryFilter.scope_path: Option<ScopePath>`
- `crates/cm-core/src/types/entry.rs`
  - `NewEntry.scope_path: ScopePath`
- `crates/cm-core/src/store.rs`
  - `ContextStore::resolve_context`
  - `ContextStore::search`
  - `ContextStore::browse`
  - `ContextStore::create_scope`
  - `ContextStore::get_scope`
  - `ContextStore::list_scopes`
  - `ContextStore::export`
- `crates/cm-core/src/query/builder.rs`
  - `QueryBuilder.scope`
  - `QueryBuilder.get_scope_path`

`ScopePath` enforces the domain invariant: paths start at `global`, ordered segments use known `ScopeKind`s, identifiers are lower case style identifiers, and path length is capped. `ancestors` returns the target scope first, then parent scopes up to `global`. Store interfaces do not know about `cwd`, `auto`, or request compatibility. They accept validated paths.

### `cm-capabilities`: request normalization and capability behavior

Relevant files and symbols:

- `crates/cm-capabilities/src/browse.rs`
  - `BrowseRequest`
  - `browse`
  - `DEFAULT_BROWSE_SCOPE`
  - `BROWSE_SCOPE_DEFAULT_ADVISORY`
- `crates/cm-capabilities/src/scope/types.rs`
  - `BrowseScopeInput`
  - `BrowseScopeMode`
  - `ScopeResolution`
  - `ScopeResolutionCandidate`
  - `ScopeResolutionConfidence`
  - `ResolvedBrowseScope`
- `crates/cm-capabilities/src/scope/resolution.rs`
  - `resolve_browse_scope`
  - `normalize_browse_scope`
  - `resolve_auto_scope`
- `crates/cm-capabilities/src/scope/chain.rs`
  - `ensure_scope_chain`
  - `ensure_scope_chain_with_status`
- `crates/cm-capabilities/src/recall/types.rs`
  - `RecallRequest`
  - `DEFAULT_RECALL_SCOPE`
  - `RECALL_SCOPE_DEFAULT_ADVISORY`
- `crates/cm-capabilities/src/recall.rs`
  - `recall`
  - `scope_chain_and_hits`
- `crates/cm-capabilities/src/recall/routing.rs`
  - `route_search`
  - `route_without_query`
  - `recall_candidates_without_query`
- `crates/cm-capabilities/src/store.rs`
  - `StoreRequest`
  - `store`
- `crates/cm-capabilities/src/deposit.rs`
  - `DepositRequest`
  - `deposit`
- `crates/cm-capabilities/src/export.rs`
  - `ExportRequest`
  - `export`

Current vertical flow:

1. Read request enters a capability request struct.
2. Capability code normalizes scope input into `ScopePath` or no filter.
3. Capability calls `ContextStore` with `ScopePath`, `Option<&ScopePath>`, or `EntryFilter.scope_path`.
4. Store owns persistence and exact filtering or ancestor walking, depending on method.

Browse is the only capability with inferred scope. `BrowseRequest` has both `scope: Option<String>` and `scope_path: Option<ScopePath>`, plus `cwd`, `scope_mode`, and `include_resolution`. `browse` defaults omitted scope to `scope='auto'`, fills missing cwd from process cwd, resolves auto through `resolve_browse_scope`, then passes an exact `EntryFilter.scope_path` to the store.

Recall uses `RecallRequest.scope: Option<ScopePath>`. `recall` defaults missing scope to `ScopePath::global`, then routes to `search`, `resolve_context`, or a browse fallback. Search and context resolution use ancestor semantics through store methods. There is no cwd inference path for recall in `cm-capabilities`.

Writes use explicit strings. `StoreRequest.scope_path` defaults to `global` and has a serde alias `scope`. `DepositRequest.scope_path` is required. Both parse with `ScopePath::parse`, then call `ensure_scope_chain` or `ensure_scope_chain_with_status` before creating entries. This is the write side equivalent of scope resolution: explicit paths can create missing scope rows.

Export uses `ExportRequest.scope_path: Option<String>`, parses on demand, and calls `ContextStore::export(scope_path.as_ref())`.

## Key Patterns

- `cm-core` is correctly pure: it validates and transports `ScopePath`, but does not infer from working directories.
- `cm-capabilities` is the compatibility and policy layer. Defaults, aliases, cwd inference, advisories, and resolution metadata belong there.
- Read semantics are inconsistent by capability:
  - browse without scope means infer current local scope and then exact filter that scope.
  - recall without scope means `global` and ancestor walk from global, effectively global only.
  - export without scope means all active entries.
- Write semantics are explicit path only, with auto creation of missing scope chain.
- The existing internal `BrowseScopeInput` is already close to the desired shape, but is browse specific and represents `Auto` rather than explicit cwd inference.

## Detailed Findings

### Request structs carry inconsistent scope shapes

Current request scope fields:

- `BrowseRequest` in `crates/cm-capabilities/src/browse.rs`: `scope: Option<String>`, `scope_path: Option<ScopePath>`, `scope_mode: BrowseScopeMode`, `cwd: Option<PathBuf>`, `include_resolution: Option<bool>`.
- `RecallRequest` in `crates/cm-capabilities/src/recall/types.rs`: `scope: Option<ScopePath>`.
- `StoreRequest` in `crates/cm-capabilities/src/store.rs`: `scope_path: String`, default `global`, alias `scope`.
- `DepositRequest` in `crates/cm-capabilities/src/deposit.rs`: `scope_path: String`.
- `ExportRequest` in `crates/cm-capabilities/src/export.rs`: `scope_path: Option<String>`.
- `GetRequest`, `UpdateRequest`, `ForgetRequest`, and `StatsRequest` do not scope their operation at request level.

The dual `scope` and `scope_path` structure exists only in browse. `normalize_browse_scope` accepts equivalent duplicates, rejects `scope='auto'` with `scope_path`, and rejects conflicts. This creates request layer complexity and forces formatters to reconstruct what the user meant.

### Scope resolution is browse specific but reusable in concept

`resolve_browse_scope` takes `&BrowseRequest`, not a neutral scope request. It returns `ResolvedBrowseScope` containing `Option<ScopePath>` and optional `ScopeResolution` metadata.

`resolve_auto_scope` lists all scopes via `ContextStore::list_scopes(None)`, scores candidates against cwd basename and parent basename, and falls back to `global` when no local scope matches. This behavior is read side inference, not a core domain concern.

Recommendation: detach resolution from `BrowseRequest` so it accepts a `ScopeSelector` plus resolution options. Browse should be a caller, not the owner of scope selection semantics.

### `ScopePath` should remain the only core scope identity

`ScopePath` is simple and valuable. It is serialized as a string, implements parse and validation, exposes ancestors, and is used by `EntryFilter`, `NewEntry`, `NewScope`, and `ContextStore` methods.

Do not move `Path` versus `CwdInferred` into `cm-core` unless store level operations need to understand inference. Today they do not. A selector is a request concern, not a persistence concern.

### Read capabilities use three different scope meanings

- Browse exact filters after normalization through `EntryFilter.scope_path`.
- Recall with query calls `ContextStore::search(query, scope, limit)`, where scope means exact scope or ancestors according to store contract.
- Recall without query calls `ContextStore::resolve_context(scope_path, kinds, limit)` for ancestor walk.
- Recall fallback can browse with no scope if request scope were `None`, but `recall` currently defaults to global before routing, so this fallback path is mostly defensive.
- Export uses optional scope filter and leaves filtering to store export.

A unified selector should not hide these semantic differences. It should only normalize input to a resolved `Option<ScopePath>` plus metadata. Each capability still decides exact filter, ancestor walk, or all entries.

### Write capabilities are explicit and should probably stay explicit initially

`store` and `deposit` parse `scope_path`, then call `ensure_scope_chain` before creating entries. This is safe because the target path is explicit. Supporting cwd inferred writes would create surprising writes to inferred scopes. If added, it should be explicit as `ScopeSelector::CwdInferred` and probably gated per capability.

For this refactor, prefer `ScopeSelector` in request structs but allow each capability to choose defaults:

- store default: `ScopeSelector::Path(ScopePath::global())`
- deposit default, if one is desired: `ScopeSelector::Path(ScopePath::global())`; current API requires a string through MCP defaulting elsewhere
- browse default: `ScopeSelector::CwdInferred { cwd: None }`
- recall default: `ScopeSelector::Path(ScopePath::global())`
- export default: no selector, because `None` means all entries, not global

### Tests already cover the important compatibility points

Relevant test files:

- `crates/cm-core/tests/types_test.rs`: `ScopePath` parse, reject, serde, `EntryFilter.scope_path` default.
- `crates/cm-core/src/query/builder_tests.rs`: `QueryBuilder.scope` and `get_scope_path`.
- `crates/cm-capabilities/tests/browse_scope/auto_resolution.rs`: cwd based browse resolution, repo/project matching, ambiguous candidates, fallback to global, process cwd default.
- `crates/cm-capabilities/tests/browse_scope/explicit.rs`: explicit browse scope, matching `scope` plus `scope_path`, and conflict rejection.
- `crates/cm-capabilities/tests/browse_scope/filters_and_pagination.rs`: resolved scope combined with filters, pagination, and sort.
- `crates/cm-capabilities/tests/browse/filters.rs`: `scope_path` exact filtering.
- `crates/cm-capabilities/tests/browse/responses.rs`: browse default advisory and scope metadata.
- `crates/cm-capabilities/tests/recall_scope_order_tests.rs`: recall scope ancestor ordering and default advisory.
- `crates/cm-capabilities/tests/recall_trace_tests.rs`: scope chain and hit counts.
- `crates/cm-capabilities/tests/store_tests.rs`: store request default scope, explicit scope path, and scope chain creation.

Tests to change for `ScopeSelector`:

- Update browse explicit tests to construct `ScopeSelector::Path` and `ScopeSelector::CwdInferred` rather than dual fields.
- Keep compatibility tests at CLI or MCP layer if legacy JSON still accepts `scope_path` during a transition.
- Add neutral resolver unit tests for selector parsing and defaults, separate from browse behavior.
- Preserve existing browse auto resolution fixtures, since they validate scoring and signals.
- Add write tests that `StoreRequest` with `ScopeSelector::Path` still creates missing chains and that cwd inferred writes are rejected or intentionally supported.

## Recommended `ScopeSelector` Refactor

Introduce in `crates/cm-capabilities/src/scope/types.rs`:

```rust
pub enum ScopeSelector {
    Path(ScopePath),
    CwdInferred { cwd: Option<PathBuf> },
}
```

If request serde needs a compact string form, support:

- `
- `"auto"` maps to `ScopeSelector::CwdInferred { cwd: None }`.
- Any valid scope path string maps to `ScopeSelector::Path`.
- Structured input can map `{ "type": "cwd_inferred", "cwd": "..." }` or `{ "type": "path", "path": "global/..." }`.

Recommended support types:

```rust
pub struct ScopeSelectionOptions {
    pub mode: BrowseScopeMode,
    pub include_resolution: Option<bool>,
}

pub struct ResolvedScopeSelection {
    pub scope_path: Option<ScopePath>,
    pub resolution: Option<ScopeResolution>,
    pub requested_scope: Option<String>,
}
```

Replace `BrowseScopeInput` with `ScopeSelector` or make it a private compatibility adapter during migration. Rename `resolve_browse_scope` to `resolve_scope_selector` and make it accept `&ScopeSelector` rather than `&BrowseRequest`.

Recommended request shapes:

```rust
pub struct BrowseRequest {
    pub scope: Option<ScopeSelector>,
    pub scope_mode: BrowseScopeMode,
    pub include_resolution: Option<bool>,
    pub kind: Option<EntryKind>,
    pub tag: Option<String>,
    pub created_by: Option<String>,
    pub include_superseded: bool,
    pub sort: BrowseSort,
    pub limit: Option<u32>,
    pub cursor: Option<String>,
}
```

```rust
pub struct RecallRequest {
    pub query: Option<String>,
    pub scope: Option<ScopeSelector>,
    pub kinds: Vec<EntryKind>,
    pub tags: Vec<String>,
    pub limit: u32,
    pub max_tokens: Option<u32>,
}
```

For recall, resolve only `Path` at first and reject `CwdInferred` unless product behavior explicitly wants inferred recall. The current contract defaults to global and tests depend on that.

```rust
pub struct StoreRequest {
    pub title: String,
    pub body: String,
    pub kind: String,
    pub scope: ScopeSelector,
    pub created_by: String,
    pub meta: MetaInput,
    pub supersedes: Option<String>,
}
```

For store and deposit, prefer accepting only `ScopeSelector::Path` in capability code initially. This removes dual names without silently introducing inferred writes.

Migration strategy:

1. Add `ScopeSelector` and neutral resolver in `cm-capabilities/src/scope`.
2. Convert `BrowseRequest` internally first. Preserve external `scope_path` compatibility at adapter boundaries outside this analysis scope.
3. Convert `StoreRequest` and `DepositRequest` to use selector or provide helper constructors that produce `ScopeSelector::Path`.
4. Convert `RecallRequest` only after deciding whether cwd inferred recall is desired.
5. Delete `normalize_browse_scope` once no request struct carries both fields.
6. Keep `cm-core` unchanged unless generated TypeScript or adapter serialization requires a reusable domain enum. Even then, keep cwd inference out of store traits.

## Dependencies

`cm-capabilities` depends on `cm-core` for all domain types and store traits. `cm-core` has no dependency back to `cm-capabilities`, which is the right direction for this refactor. The new selector should live in `cm-capabilities` to preserve that dependency boundary.

## Relevance to Helioy

This refactor should make scope behavior easier for agents to reason about. A single selector reduces tool schema ambiguity and makes cwd inferred scope explicit without weakening the core `ScopePath` invariant.

## Open Questions

- Should recall support `CwdInferred`, or should it stay default global until a product decision is made?
- Should writes ever support cwd inferred scope, or should writes require an explicit `Path` forever?
- Should legacy `scope_path` remain as serde alias on capability requests, or should compatibility live only in CLI and MCP adapters?
- Should export accept a selector, or should it keep `Option<ScopePath>` semantics because `None` means full export?
