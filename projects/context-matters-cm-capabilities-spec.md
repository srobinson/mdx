---
title: "cm-capabilities: Shared Application Layer for context-matters"
category: projects
status: draft
created: 2026-03-20
tags: [context-matters, architecture, refactor, cm-capabilities, web-mcp-parity]
---

# cm-capabilities: Shared Application Layer

## Problem Statement

Application semantics for recall, browse, and stats live inside `cm-cli/src/shared.rs` and the MCP tool handlers. `cm-web` imports from `cm-cli::shared` to reuse this logic, creating an asymmetric dependency where the HTTP adapter depends on the MCP adapter crate.

The recall code path is duplicated across two sites:
- `crates/cm-cli/src/mcp/tools/recall.rs` (MCP tool handler)
- `crates/cm-web/src/api/entries.rs:recall()` (HTTP handler, line 166)

Both call the same shared helpers (`recall_candidates_without_query`, `entry_to_recall_json`, `estimate_tokens`) but each manages its own parameter parsing, routing logic, post-filtering, and token budget tracking. Parity drifts as features are added to one adapter but not the other.

**Current dependency chain:**
```
cm-core  (types + ContextStore trait)
  |
cm-store (SQLite adapter)
  |
cm-cli   (MCP server + CLI + shared.rs)
  |
cm-web   (HTTP adapter, imports cm-cli::shared)
```

`cm-web -> cm-cli` is the problematic edge. Shared capability code should not live inside an adapter crate.

## Target Architecture

```
cm-core         (types + ContextStore trait, zero I/O)
  |
cm-store        (SQLite adapter)
  |
cm-capabilities (RecallCapability, BrowseCapability, StatsCapability)
  |
cm-cli          cm-web          future-cli
(MCP adapter)   (HTTP adapter)
```

Each adapter becomes a thin translation layer: parse protocol input, call capability, project domain result into protocol output.

## cm-capabilities Crate Design

### Cargo.toml

```toml
[package]
name = "cm-capabilities"
edition = "2024"

[dependencies]
cm-core = { workspace = true }
serde = { workspace = true }
serde_json = { workspace = true }
uuid = { workspace = true }
chrono = { workspace = true }
```

No dependency on cm-store, cm-cli, or cm-web. Operates purely against the `ContextStore` trait.

### Module Layout

```
crates/cm-capabilities/src/
  lib.rs          -- pub mod declarations, re-exports
  recall.rs       -- RecallCapability
  browse.rs       -- BrowseCapability
  stats.rs        -- StatsCapability
  projection.rs   -- Transport-neutral agent view structs + mappers
  validation.rs   -- Input validation (clamp_limit, check_input_size, parse_confidence)
  scope.rs        -- Scope chain helpers (ensure_scope_chain)
  error.rs        -- Error conversion (cm_err_to_string for MCP, kept as utility)
  constants.rs    -- Shared constants (MAX_LIMIT, DEFAULT_LIMIT, SNIPPET_LENGTH, etc.)
```

### Constants (from `cm-cli/src/shared.rs`)

```rust
// constants.rs
pub const MAX_INPUT_BYTES: usize = 1_048_576;  // line 14 in shared.rs
pub const MAX_BATCH_IDS: usize = 100;           // line 17
pub const DEFAULT_LIMIT: u32 = 20;              // line 20
pub const MAX_LIMIT: u32 = 200;                 // line 23
pub const SNIPPET_LENGTH: usize = 200;          // line 26
```

### Validation (from `cm-cli/src/shared.rs`)

```rust
// validation.rs
pub fn check_input_size(value: &str, field: &str) -> Result<(), String>;  // line 80
pub fn clamp_limit(limit: Option<u32>) -> u32;                           // line 88
pub fn parse_confidence(s: &str) -> Result<Confidence, String>;          // line 123
```

### Projection (from `cm-cli/src/shared.rs`)

```rust
// projection.rs
pub fn snippet(body: &str, max_bytes: usize) -> String;            // line 99
pub fn estimate_tokens(text: &str) -> u32;                         // line 111

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RecallEntryView { /* fields matching MCP recall entry shape */ }

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BrowseEntryView { /* fields matching MCP browse entry shape */ }

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct FullEntryView { /* fields matching cx_get full entry shape */ }

pub fn project_recall_entry(entry: &Entry) -> RecallEntryView;
pub fn project_browse_entry(entry: &Entry) -> BrowseEntryView;
pub fn project_full_entry(entry: &Entry) -> FullEntryView;
pub fn entry_has_any_tag(entry: &Entry, tags: &[String]) -> bool; // line 213
```

These are typed view models, not raw `serde_json::Value`. The capability layer owns the
agent-view projection shape, while each adapter owns its envelope and serialization.

### Scope Helpers (from `cm-cli/src/shared.rs`)

```rust
// scope.rs
pub async fn ensure_scope_chain(
    store: &impl ContextStore,
    path: &ScopePath,
    ctx: &WriteContext,
) -> Result<(), String>;  // line 294
```

### Error Conversion (from `cm-cli/src/shared.rs`)

```rust
// error.rs
pub fn cm_err_to_string(e: CmError) -> String;  // line 31
```

This stays as a utility for MCP-style string error responses. Web uses its own `ApiError` HTTP status mapping.

---

## RecallCapability

The most duplicated code path. Currently implemented in two places with identical routing logic.

### Input Type

```rust
// recall.rs
pub struct RecallRequest {
    pub query: Option<String>,
    pub scope: Option<ScopePath>,
    pub kinds: Vec<EntryKind>,
    pub tags: Vec<String>,
    pub limit: u32,           // already clamped by caller or clamped here
    pub max_tokens: Option<u32>,
}
```

### Output Type

```rust
pub struct RecallResult {
    pub entries: Vec<Entry>,
    pub scope_chain: Vec<ScopePath>,
    pub token_estimate: u32,
    pub routing: RecallRouting,     // trace metadata
    pub candidates_before_filter: usize,  // trace metadata
}

/// Which code path was taken. Aids debugging and parity verification.
pub enum RecallRouting {
    Search,              // query was set, used store.search()
    TagScopeWalk,        // no query, tags present, used recall_candidates_without_query()
    ScopeResolve,        // no query, scope set, used store.resolve_context()
    BrowseFallback,      // no query, no scope, no tags, used store.browse()
}
```

### Core Function

```rust
pub async fn recall(
    store: &impl ContextStore,
    request: RecallRequest,
) -> Result<RecallResult, CmError>
```

**Routing logic** (mirrors `cm-cli/src/mcp/tools/recall.rs` lines 72-114):

1. If `request.query` is set: call `store.search(query, scope, fetch_limit)`. Route: `Search`.
2. If no query but `request.tags` is non-empty: call `recall_candidates_without_query(store, scope, kinds, tags, limit)`. Route: `TagScopeWalk`.
3. If no query, no tags, but `request.scope` is set: call `store.resolve_context(scope, kinds, fetch_limit)`. Route: `ScopeResolve`.
4. Fallback: call `store.browse(filter)`. Route: `BrowseFallback`.

**Post-filtering** (lines 119-136 in recall.rs):
- Kind filter applied to search results (resolve_context handles kinds internally).
- Tag filter applied to all results via `entry_has_any_tag()`.
- Entries truncated to `limit` after filtering.

**Fetch-size compensation** (lines 65-70 in recall.rs):
- When post-filtering is active (kinds OR tags present), fetch `limit * 3` capped at `MAX_LIMIT`.

**Token budget** (lines 147-164 in recall.rs):
- If `max_tokens` is set, iterate entries and accumulate `estimate_tokens()` per entry.
- Stop adding entries when budget would be exceeded (always include first entry).

**Scope chain** (lines 142-145 in recall.rs):
- If scope is set, extract ancestor chain via `scope.ancestors()`.
- Return empty vec for unscoped queries.

### recall_candidates_without_query (from shared.rs line 224)

Moves into this module as a private helper:

```rust
async fn recall_candidates_without_query(
    store: &impl ContextStore,
    scope_path: Option<&ScopePath>,
    kind_filters: &[EntryKind],
    tags: &[String],
    limit: u32,
) -> Result<Vec<Entry>, CmError>
```

Algorithm: walks scope ancestors from specific to general, pages through `store.browse()` at each level, post-filters by kinds and tags, accumulates until limit reached.

---

## BrowseCapability

Less duplication than recall. MCP `cx_browse` and web `browse()` both call `store.browse(filter)` directly. The value of extracting this is consistency in filter construction and future sort/filter extensions.

### Input Type

```rust
// browse.rs
pub struct BrowseRequest {
    pub scope_path: Option<ScopePath>,
    pub kind: Option<EntryKind>,
    pub tag: Option<String>,
    pub created_by: Option<String>,
    pub include_superseded: bool,
    pub sort: BrowseSort,          // cm_core::BrowseSort
    pub limit: u32,
    pub cursor: Option<String>,
}
```

### Output Type

```rust
pub struct BrowseResult {
    pub entries: Vec<Entry>,
    pub total: u64,
    pub next_cursor: Option<String>,
}
```

### Core Function

```rust
pub async fn browse(
    store: &impl ContextStore,
    request: BrowseRequest,
) -> Result<BrowseResult, CmError>
```

Constructs `EntryFilter` from `BrowseRequest`, calls `store.browse(filter)`, returns domain result. Adapters wrap the result in their own envelopes. Agent-parity adapters can map entries through `BrowseEntryView`; curate-mode web endpoints can continue returning full `Entry` values.

---

## StatsCapability

MCP `cx_stats` and web `get_stats` diverge significantly. MCP returns base stats + scope tree. Web adds 5 supplementary raw SQL queries (entries_today, entries_this_week, active_agents, scope_tree, quality snapshot). The supplementary queries are web-only read model concerns.

### Design Decision

The capability covers only what the ContextStore trait exposes:

```rust
// stats.rs
pub struct StatsRequest {
    pub tag_sort: TagSort,
}

pub enum TagSort {
    Name,
    Count,
}

pub struct StatsResult {
    pub stats: StoreStats,       // from store.stats()
    pub scope_tree: Vec<ScopeTreeNode>,  // from store.list_scopes() + entry counts
}

pub struct ScopeTreeNode {
    pub path: ScopePath,
    pub kind: ScopeKind,
    pub label: String,
    pub entry_count: u64,
}
```

```rust
pub async fn stats(
    store: &impl ContextStore,
    request: StatsRequest,
) -> Result<StatsResult, CmError>
```

Calls `store.stats()` and `store.list_scopes(None)`. Joins scope paths with `entries_by_scope` counts. Sorts tags by name or count per request.

**Web supplementary queries** (DashboardStats fields: entries_today, entries_this_week, active_agents, quality) stay in `cm-web/src/api/stats.rs` as web-only read model. They use `read_pool` directly with raw SQL. These are UI dashboard concerns, not agent capabilities.

---

## Web Mode Design

### Three Modes

1. **Curate** (default): Existing rich web experience. Full entries, relations, mutations, merge, sort, dashboard stats. Endpoints unchanged at `/api/entries`, `/api/stats`, etc.

2. **Recall** (agent parity): New endpoint calling `RecallCapability::recall()`. Returns the exact same entries an MCP agent would see, plus trace metadata for observability.

3. **Browse** (agent parity): New endpoint calling `BrowseCapability::browse()`. Returns the exact same entries, plus cursor and filter diagnostics.

### Endpoint Ownership

- Canonical recall parity endpoint: `GET /api/agent/recall`
- Canonical browse parity endpoint: `GET /api/agent/browse`
- Compatibility alias: `GET /api/entries/recall`

`/api/entries/recall` is not a second recall implementation. During migration it becomes a
compatibility alias backed by the same `RecallCapability` path as `/api/agent/recall`, but
without the web-only `_trace` object. This preserves current clients while making
`/api/agent/recall` the canonical admin surface for agent observability.

### New Endpoints

#### `GET /api/agent/recall`

Query parameters (identical to MCP `cx_recall`):
- `query` (optional): FTS5 search term
- `scope` (optional): Scope path for ancestor walk
- `kinds` (repeatable): Kind filters (OR semantics)
- `tags` (repeatable): Tag filters (OR semantics)
- `limit` (optional): Max results [1, 200], default 20
- `max_tokens` (optional): Token budget

Response:
```json
{
  "results": [
    {
      "id": "uuid",
      "scope_path": "global/project:helioy",
      "kind": "fact",
      "title": "...",
      "snippet": "...",
      "created_by": "agent:claude-code",
      "updated_at": "2026-03-20T...",
      "tags": ["tag1"],
      "confidence": "high"
    }
  ],
  "returned": 5,
  "scope_chain": ["global", "global/project:helioy"],
  "token_estimate": 500,
  "_trace": {
    "routing": "search",
    "candidates_before_filter": 12,
    "fetch_limit_used": 60,
    "post_filters_applied": ["kinds", "tags"],
    "token_budget_exhausted": false
  }
}
```

The `results` array uses the shared `RecallEntryView` projection, identical in shape to MCP output. The `_trace` object is web-only diagnostic metadata. The parity contract is semantic, not byte-level: after parsing JSON and dropping `_trace`, the shared response fields (`results`, `returned`, `scope_chain`, `token_estimate`) must match `cx_recall`.

#### `GET /api/agent/browse`

Query parameters (identical to MCP `cx_browse`):
- `scope_path` (optional): Exact scope filter
- `kind` (optional): Kind filter
- `tag` (optional): Tag filter
- `created_by` (optional): Creator filter
- `include_superseded` (optional): Include deleted entries
- `limit` (optional): Results per page [1, 200], default 20
- `cursor` (optional): Pagination cursor

Response:
```json
{
  "entries": [
    {
      "id": "uuid",
      "scope_path": "global/project:helioy",
      "kind": "fact",
      "title": "...",
      "snippet": "...",
      "created_by": "agent:claude-code",
      "created_at": "2026-03-20T...",
      "updated_at": "2026-03-20T...",
      "superseded_by": null,
      "tags": ["tag1"]
    }
  ],
  "total": 47,
  "next_cursor": "cursor_or_null",
  "has_more": true,
  "_trace": {
    "filter_set": {
      "scope_path": "global/project:helioy",
      "kind": null,
      "tag": null,
      "include_superseded": false
    },
    "sort": "recent"
  }
}
```

The `entries` array uses the shared `BrowseEntryView` projection. `_trace` is diagnostic only. Note: MCP browse does not expose sort. Agent parity endpoints default to `BrowseSort::Recent` (matching MCP behavior) and do not accept a sort parameter. Parity is semantic: after parsing JSON and dropping `_trace`, the shared response fields (`entries`, `total`, `next_cursor`, `has_more`) must match `cx_browse`.

---

## Migration Strategy

### Phase 1: Create cm-capabilities, extract RecallCapability

1. Create `crates/cm-capabilities/` with Cargo.toml depending on `cm-core` plus shared serialization utilities only. No dependency on `cm-store`, `cm-cli`, or `cm-web`.
2. Move constants, validation, typed projection structs/mappers, and scope helpers from `cm-cli/src/shared.rs` into cm-capabilities modules.
3. Implement `RecallCapability::recall()` by extracting routing logic from `cm-cli/src/mcp/tools/recall.rs` (lines 40-179).
4. Add cm-capabilities as dependency to cm-cli. Rewire `cx_recall` to call `RecallCapability::recall()`, then map entries through `project_recall_entry()`.
5. `cm-cli/src/shared.rs` becomes a thin re-export of cm-capabilities items for backward compatibility during migration.
6. Add capability-level tests for recall routing, post-filtering, and token budget behavior using the same fixture data as current MCP tests.
7. Run `just check && just test`. All existing MCP tests must pass unchanged.

### Phase 2: Extract BrowseCapability

1. Implement `BrowseCapability::browse()` in cm-capabilities.
2. Rewire `cx_browse` in cm-cli.
3. Add capability-level tests for browse filter construction and pagination semantics.
4. Run `just check && just test`.

### Phase 3: Add agent parity web endpoints

1. Add cm-capabilities as dependency to cm-web.
2. Implement `GET /api/agent/recall` calling `RecallCapability::recall()`, mapping entries via `project_recall_entry()`, adding `_trace`.
3. Implement `GET /api/agent/browse` calling `BrowseCapability::browse()`, mapping entries via `project_browse_entry()`, adding `_trace`.
4. Rewire `GET /api/entries/recall` as a compatibility alias to the same `RecallCapability` path, without `_trace`.
5. Keep `GET /api/entries` as the curate-mode browse surface. It is not an alias of `GET /api/agent/browse`.
6. Add web parity contract tests that compare parsed JSON from `/api/agent/recall` and `/api/agent/browse` against `cx_recall` and `cx_browse` for the same fixture store, ignoring `_trace`.
7. Add compatibility tests ensuring `/api/entries/recall` matches the shared parity fields returned by `/api/agent/recall`.
8. Run `just check && just test`.

### Phase 4: Rewire cm-web, remove cm-cli dependency

1. Replace `cm-web`'s import of `cm_cli::shared::*` with `cm_capabilities::*`.
2. Ensure both the canonical `/api/agent/recall` endpoint and the compatibility `/api/entries/recall` alias call the same `RecallCapability` implementation.
3. Remove `cm-cli` from `cm-web/Cargo.toml`.
4. Run `just check && just test`.

### Phase 5: Clean up cm-cli/src/shared.rs

1. Remove functions that have moved to cm-capabilities.
2. Keep only cm-cli-specific helpers (if any remain).
3. If shared.rs is empty, delete it.
4. Run `just check && just test`.

---

## Success Criteria

1. `cm-web/Cargo.toml` does not depend on `cm-cli`.
2. Parsed JSON from `GET /api/agent/recall` matches `cx_recall` on the shared response fields (`results`, `returned`, `scope_chain`, `token_estimate`) when called with the same fixture data and parameters.
3. Parsed JSON from `GET /api/agent/browse` matches `cx_browse` on the shared response fields (`entries`, `total`, `next_cursor`, `has_more`) when called with the same fixture data and parameters.
4. `GET /api/entries/recall` is a compatibility alias to the same `RecallCapability`-backed implementation until frontend migration is complete.
5. MCP tool `cx_recall` calls `RecallCapability::recall()` internally.
6. MCP tool `cx_browse` calls `BrowseCapability::browse()` internally.
7. New capability and web parity contract tests pass, along with the existing suite: `just check && just test`.
8. No new workspace crate dependencies beyond `cm-core` are introduced for `cm-capabilities`; standard serialization utilities are allowed.
9. Existing curate-mode web endpoints (`/api/entries`, `/api/stats`) remain unchanged in behavior.

## Out of Scope

- **ContextStore trait changes.** cm-core stays pure. No new trait methods.
- **Dashboard stats refactor.** Web supplementary queries (entries_today, active_agents, quality) stay in cm-web as web-only read model.
- **cx_store, cx_update, cx_forget, cx_get, cx_deposit, cx_export.** These MCP tools have minimal or no web duplication. Extract them later if needed.
- **Frontend changes.** This spec covers backend crate architecture only. Frontend mode switching (curate/recall/browse tabs) is a separate UI spec.
- **Sort in MCP browse.** MCP `cx_browse` does not expose sort today. Agent parity endpoints match this behavior. Adding sort to MCP is a separate decision.
- **Performance optimization.** The refactor preserves existing query patterns and connection pool usage.
- **New entry kinds, scope kinds, or relation kinds.** Type system changes are orthogonal.
