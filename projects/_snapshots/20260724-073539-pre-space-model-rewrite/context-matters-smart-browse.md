---
title: context-matters smart browse
type: projects
tags: [context-matters, cx-browse, scope, inference, mcp, implementation]
summary: Implementation spec for the first pass of smart local scope resolution in cx_browse.
status: draft
project: context-matters
confidence: high
created: 2026-04-20
updated: 2026-04-20
related: [context-matters-browse-inferred-scope-spec, context-matters-search-spec]
---

# context-matters smart browse

## Purpose

`cx_browse` should be useful when an agent asks, "what is here?"

Today, when the caller omits `scope_path`, browse returns the newest matching entries across the whole store. That is mechanically correct, but it is operationally wrong inside the Helioy ecosystem. An agent working in `context-matters` expects browse to begin from the local repo scope. The current default makes unrelated recent work more visible than the nearby context.

The first pass should fix the common case without solving every scope modeling problem. It should infer one existing local scope from the current working directory, expose the inference, and preserve exact explicit scope behavior.

## Decision

Ship smart browse as an additive capability layer change.

The first pass supports:

- `scope = "auto"`
- `scope_mode = "resolved"`
- optional `cwd`
- one resolved existing scope
- resolution metadata in the response
- exact explicit scope behavior through existing `scope_path`

The first pass does not support stack browsing, ancestor browsing, alias config, recent write affinity, session affinity, or schema changes.

## Current State

The store already has the inventory primitive needed for this work. `ContextStore::list_scopes` exists in `crates/cm-core/src/store.rs`, and `CmStore::do_list_scopes` is implemented in `crates/cm-store/src/sqlite/scope.rs`.

The exact browse query should stay as it is. `crates/cm-store/src/sqlite/query.rs` builds `EntryFilter.scope_path` as an exact `scope_path = ?` predicate. Smart browse should resolve a scope before this filter is built. It should not change store browse semantics.

The public MCP and HTTP surfaces still expose `scope_path`. The omission of `scope_path` currently means global browse. `tools.toml` also documents that omission as browsing across all scopes. That contract needs a careful transition.

The current projection layer splits responsibility:

- YAML browse formatting receives both `BrowseResult` and `BrowseRequest`.
- Web browse projection receives only `BrowseResult`.

Resolution metadata must therefore live on `BrowseResult`, not only on the request, if both projections are expected to expose the same truth.

## Compatibility Contract

Existing callers must keep working.

`scope_path` remains supported and means exact scope filtering. If `scope_path` is supplied, no inference runs.

The new `scope` field is additive. It accepts either `"auto"` or an explicit scope path. For this first pass, `scope` and `scope_path` must not conflict.

Recommended validation:

- `scope_path` only: exact browse
- `scope = "auto"` only: smart resolved browse
- `scope = "<scope path>"` only: exact browse
- both `scope_path` and matching explicit `scope`: exact browse
- both `scope_path` and `scope = "auto"`: validation error
- both `scope_path` and different explicit `scope`: validation error

This keeps behavior inspectable. Silent precedence would create a debugging trap.

## Request Shape

MCP, CLI, and web should converge on the same conceptual request.

```json
{
  "scope": "auto",
  "scope_mode": "resolved",
  "cwd": "/Users/alphab/Dev/LLM/DEV/helioy/context-matters",
  "include_resolution": true,
  "limit": 20,
  "kind": "decision",
  "tag": "architecture"
}
```

### Fields

`scope`

Preferred new field. Defaults to `"auto"` for MCP agent browse. Accepts `"auto"` or a valid `ScopePath` string.

`scope_path`

Backward compatible exact scope field. Keep it as an alias for explicit exact scope. Do not remove it in this pass.

`scope_mode`

Only `"resolved"` is implemented in the first pass. Unknown modes should return a validation error. `"stack"` can remain reserved.

`cwd`

Optional override for transports that cannot trust process cwd. MCP should default this from `std::env::current_dir()` when the request asks for auto scope and no `cwd` is supplied. HTTP callers should send it explicitly if they want auto behavior tied to a filesystem location.

`include_resolution`

Defaults to `true` when `scope = "auto"`. When false, resolution may be omitted from the projected response, but `BrowseResult` should still carry it internally.

## Response Shape

Resolution metadata should sit beside the existing header in the structured JSON view.

```json
{
  "header": {
    "sort_used": "updated_at desc",
    "total": 39,
    "returned": 20,
    "scope": "global/project:helioy/repo:context-matters",
    "kinds_histogram": {},
    "tags_histogram": {}
  },
  "resolution": {
    "requested_scope": "auto",
    "resolved_scope": "global/project:helioy/repo:context-matters",
    "scope_mode": "resolved",
    "confidence": "high",
    "candidates": [
      {
        "scope": "global/project:helioy/repo:context-matters",
        "score": 230,
        "matched": ["repo", "project", "specificity"]
      },
      {
        "scope": "global/project:helioy",
        "score": 120,
        "matched": ["project"]
      },
      {
        "scope": "global",
        "score": 0,
        "matched": ["fallback"]
      }
    ],
    "signals": [
      "cwd basename matched repo scope segment: context-matters",
      "cwd parent basename matched project scope segment: helioy"
    ]
  },
  "entries": [],
  "next_cursor": null,
  "has_more": false
}
```

The YAML formatter can render the same information compactly:

```yaml
---
query: scope=auto
sort: updated_at desc
total: 39
returned: 20
scope: global/project:helioy/repo:context-matters
resolution:
  requested_scope: auto
  resolved_scope: global/project:helioy/repo:context-matters
  scope_mode: resolved
  confidence: high
  signals:
    - cwd repo basename matched existing repo scope
    - cwd parent basename matched existing project scope
entries:
  ...
```

Candidate details can be present in JSON while the YAML view stays compact. If YAML size becomes an issue, render only the top candidate plus signals.

## Resolver Model

Add a resolver in `crates/cm-capabilities/src/scope.rs`. The resolver is part of the capability layer because it combines caller intent, process context, and store inventory. The store should remain a mechanical persistence boundary.

Suggested types:

```rust
pub enum BrowseScopeInput {
    Auto,
    Exact(ScopePath),
}

pub enum BrowseScopeMode {
    Resolved,
}

pub enum ScopeResolutionConfidence {
    High,
    Medium,
    Low,
    VeryLow,
}

pub struct ScopeResolution {
    pub requested_scope: String,
    pub resolved_scope: ScopePath,
    pub scope_mode: BrowseScopeMode,
    pub confidence: ScopeResolutionConfidence,
    pub candidates: Vec<ScopeResolutionCandidate>,
    pub signals: Vec<String>,
}

pub struct ScopeResolutionCandidate {
    pub scope: ScopePath,
    pub score: i32,
    pub matched: Vec<String>,
}
```

These types can stay in `cm-capabilities` for the first pass. Move them to `cm-core` only when search or another crate reuses the same contract.

## Resolver Algorithm

The first pass should be deterministic and conservative.

Inputs:

- all existing scopes from `store.list_scopes(None)`
- `cwd`, either request supplied or process supplied
- explicit scope input, if supplied

Derived signals:

- repo name from cwd basename
- project name from cwd parent basename
- ancestor names from cwd, used as weak project candidates

Candidate construction:

- candidates come only from existing scopes
- always include `global` if it exists
- include repo scopes whose `repo:<id>` segment equals the cwd basename
- include project scopes whose `project:<id>` segment equals a cwd ancestor
- include parent project scope for a matching repo scope

Scoring:

```text
repo segment equals cwd basename                 +200
project segment equals cwd parent basename       +100
project segment appears anywhere in cwd          +60
scope is repo                                    +30
scope is project                                 +10
scope is global                                  +0
```

Tie breakers:

1. higher score
2. deeper scope
3. lexical path order

Confidence:

- `high`: top score is at least 200 and no other repo candidate has the same score
- `medium`: top score is at least 100
- `low`: top score is above 0
- `very_low`: only global resolved

This model handles the current cleaned tree well. From `/Users/alphab/Dev/LLM/DEV/helioy/context-matters`, the resolver should pick `global/project:helioy/repo:context-matters` with high confidence.

## Fallback Behavior

If auto scope cannot resolve from cwd, browse `global` only if that scope exists.

If the store has no `global` scope, return a validation or internal error that says no candidate scope could be resolved. The current system creates `global`, so this should be rare.

If `cwd` is absent and the transport cannot provide process cwd, the resolver should fall back to `global` with `very_low` confidence and a clear signal:

```text
no cwd supplied; using global fallback
```

## Implementation Plan

### 1. Capability request and result

File: `crates/cm-capabilities/src/browse.rs`

Extend `BrowseRequest` with:

- `scope: Option<String>` or a typed `BrowseScopeInput`
- `scope_mode: BrowseScopeMode`
- `cwd: Option<PathBuf>` or `Option<String>`
- `include_resolution: bool`

Keep `scope_path: Option<ScopePath>` for compatibility. Existing struct literals must continue to compile through `Default`.

Extend `BrowseResult` with:

- `resolution: Option<ScopeResolution>`

Update `browse()`:

1. normalize scope input
2. validate conflicts between `scope` and `scope_path`
3. resolve auto scope when requested
4. build the existing `EntryFilter` with the effective exact scope
5. call `store.browse(filter)` unchanged
6. fetch relation counts unchanged
7. return entries plus resolution metadata

### 2. Resolver

File: `crates/cm-capabilities/src/scope.rs`

Add:

- `resolve_browse_scope(store, request) -> Result<ResolvedBrowseScope, CmError>`
- helper functions for parsing scope segments
- deterministic candidate scoring
- unit tests for scoring without SQLite, if practical

The resolver should call only `store.list_scopes(None)`. It should not query entries, stats, or mutation history in the first pass.

### 3. MCP tool

File: `crates/cm-cli/src/mcp/tools/browse.rs`

Extend `CxBrowseParams`:

- `scope: Option<String>`
- `scope_mode: Option<String>`
- `cwd: Option<String>`
- `include_resolution: Option<bool>`

When `scope = "auto"` and `cwd` is absent, set `cwd` from `std::env::current_dir()`.

Continue accepting `scope_path`. Validate conflicts before constructing `BrowseRequest`, or let the capability return a clear validation error.

### 4. Tool contract

File: `tools.toml`

Update `cx_browse` description. The description should say browse is locally scoped by default through inferred scope resolution when possible.

Add parameters:

- `scope`
- `scope_mode`
- `cwd`
- `include_resolution`

Keep `scope_path`, but mark it as the compatibility exact scope field.

Update `output_schema` to include optional top level `resolution`.

Regenerate:

- `crates/cm-cli/src/mcp/generated_schema.rs`
- `crates/cm-cli/src/cli/generated_help.rs`
- `crates/cm-cli/templates/SKILL.md`

`crates/cm-cli/build.rs` should not need logic changes for this pass.

### 5. Web API

File: `crates/cm-web/src/api/agent.rs`

Extend `BrowseQuery` with:

- `scope`
- `scope_mode`
- `cwd`
- `include_resolution`

`execute_browse` is shared by `/api/agent/browse` and `/api/entries`, so this one parser change covers both routes. Keep `scope_path` parsing for compatibility.

File: `crates/cm-web/src/api/entries.rs`

No separate parsing change should be needed because it delegates to `agent::execute_browse`.

### 6. Web client

File: `crates/cm-web/frontend/src/api/client.ts`

Extend `BrowseParams` and `AgentBrowseParams` with:

- `scope?: string`
- `scope_mode?: "resolved"`
- `cwd?: string`
- `include_resolution?: boolean`

Include those fields in the query serializer for `entries.browse` and `agent.browse`.

Generated TypeScript response files should be regenerated from ts-rs after `WebBrowseView` changes.

### 7. Projections

File: `crates/cm-capabilities/src/projection/web_view.rs`

Add web structs:

- `WebScopeResolution`
- `WebScopeResolutionCandidate`

Add `resolution: Option<WebScopeResolution>` to `WebBrowseView`.

Update `project_web_browse_at` to project from `BrowseResult.resolution`.

File: `crates/cm-capabilities/src/projection/browse_view.rs`

Update `format_browse_view_at`:

- show `query: scope=auto` when auto scope was requested
- render compact `resolution` metadata when present
- keep existing hoisting and row comments unchanged

Update `reconstruct_query()` so it understands `scope`, `scope_mode`, and `include_resolution` without losing existing filters.

## Test Plan

### Capability tests

File: `crates/cm-capabilities/tests/browse_tests.rs`

Add:

- explicit `scope_path` still filters exactly
- explicit `scope` path behaves like `scope_path`
- conflicting `scope` and `scope_path` returns validation error
- `scope = auto` with cwd `/tmp/helioy/context-matters` resolves `global/project:helioy/repo:context-matters`
- `scope = auto` with project cwd resolves project scope when no repo scope exists
- `scope = auto` with no useful match falls back to `global` with `very_low` confidence
- auto browse still respects `kind`, `tag`, `created_by`, `include_superseded`, `limit`, and cursor

### Projection tests

File: `crates/cm-capabilities/tests/browse_format_tests.rs`

Update existing `BrowseResult` fixtures with `resolution: None`.

Add a focused test for auto resolution rendering:

- `query: scope=auto`
- `resolution.resolved_scope`
- `resolution.confidence`
- at least one signal

Update snapshot `crates/cm-capabilities/tests/snapshots/browse_view_session_log.txt` only if the default no resolution shape changes. Prefer keeping that golden unchanged by making `resolution` absent in legacy fixtures.

File: `crates/cm-capabilities/tests/web_view_tests.rs`

Add a web projection test that `WebBrowseView.resolution` appears when `BrowseResult.resolution` is present and is omitted when absent.

### Web parity tests

File: `crates/cm-web/tests/parity.rs`

Update `capability_browse` expected fixture construction with new default fields.

Add:

- `/api/agent/browse?scope=auto&cwd=/tmp/helioy/context-matters` matches capability layer
- `/api/entries?scope=auto&cwd=/tmp/helioy/context-matters` matches the same projection

### MCP tests

Files:

- `crates/cm-cli/tests/tools_integration.rs`
- `crates/cm-cli/tests/response_wire_tests.rs`
- `crates/cm-cli/tests/payload_size_test.rs`
- `crates/cm-cli/tests/snapshot_tests.rs`

Add or update coverage so `cx_browse` accepts `scope`, `scope_mode`, `cwd`, and `include_resolution`. Ensure the dual response JSON contains `resolution` when auto scope is used.

### Store tests

No store behavior should change.

Run existing store tests as regression coverage:

- `crates/cm-store/tests/store_query.rs`
- `crates/cm-store/tests/store_schema.rs`

## Verification Commands

Run focused tests first:

```sh
cargo test -p cm-capabilities browse
cargo test -p cm-web parity
cargo test -p cm-cli tools_integration response_wire
```

Then run the workspace checks:

```sh
just fmt
just test
just check
```

If generated files changed:

```sh
cargo build -p cm-cli
cargo build -p cm-web
```

Use `cx_stats` and a live `cx_browse(scope="auto")` call against the real local store as a final manual smoke test.

## Acceptance Criteria

`cx_browse` with no explicit scope in an MCP repo session should return entries from the local repo scope when that scope exists.

`cx_browse(scope="auto", cwd="/Users/alphab/Dev/LLM/DEV/helioy/context-matters")` should resolve to `global/project:helioy/repo:context-matters` with high confidence.

The response should disclose the requested scope, resolved scope, confidence, candidates, and signals.

Explicit `scope_path` callers should see the same result set as before this change.

The SQLite browse implementation should remain exact and unchanged.

The web API and MCP tool should expose the same response model.

## Deferred Work

Stack browsing should wait for a separate pagination design. Merging repo and project results affects ordering, total count, cursor shape, and row grouping. That is larger than this first pass.

Alias config should wait until there is a concrete source of truth for local project aliases.

Session affinity should wait until the system has an explicit current session scope. Inferring session from recent writes is too sticky for the first pass.

Scope modeling guidance should be written separately. Smart browse can improve default locality, but it should not hide the need for better scope hygiene over time.

