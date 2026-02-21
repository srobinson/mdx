---
title: Scope selector migration architecture review for context-matters
type: research
tags: [context-matters, scope-selector, architecture-review, mcp, cm-web]
summary: Review of the proposed breaking migration from public scope_path inputs to public scope with cwd_inferred across cm-core, cm-capabilities, cm-cli, and cm-web.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

The proposed migration is architecturally sound if `ScopeSelector` and git cwd normalization live in `cm-capabilities`, while `cm-core` keeps durable `ScopePath` domain and store contracts unchanged. Approval should be conditional because the current spec does not fully define unknown field rejection, web write DTO migration, `scope_mode` removal, and confidence rules for write side `cwd_inferred`.

## Project Metadata

- Language: Rust 2024 workspace plus TypeScript React frontend.
- Workspace crates: `cm-core`, `cm-store`, `cm-capabilities`, `cm-cli`, `cm-web`.
- Build system: Cargo workspace with `just check`, `just build`, `just test`, `just fmt`.
- Public tool documentation source: `tools.toml`, generated into MCP schema, CLI help, and skill template.
- fmm status: Indexed. fmm reports 320 indexed files and 39,793 LOC.

## Architecture

### Current boundaries

- `crates/cm-core` owns durable domain types and storage contracts. `ScopePath`, `Scope`, `NewEntry.scope_path`, `EntryFilter.scope_path`, and `ContextStore` methods are exact path based.
- `crates/cm-store` implements the exact path persistence model through SQLite. No selector semantics belong here.
- `crates/cm-capabilities` owns user intent translation, validation, scope chain creation, projection, and capability behavior. Existing browse resolution already lives under `cm-capabilities/src/scope`.
- `crates/cm-cli` is an adapter for CLI and MCP transport. It should parse public wire inputs, reject removed fields, then delegate typed requests to `cm-capabilities`.
- `crates/cm-web` has backend API DTOs plus frontend request types. It currently exposes `scope_path` in browse, search, export, and frontend URL state.

### Correct target layering

The spec's central boundary is correct: add `ScopeSelector` in `cm-capabilities`, not `cm-core`. Public `scope` strings should be parsed at adapter or capability boundary into a typed selector. After resolution, downstream store calls should receive exact `ScopePath` values. This preserves persistence invariants and avoids leaking cwd or git behavior into the domain/store layer.

Recommended shape:

```rust
pub enum ScopeSelector {
    Path(ScopePath),
    CwdInferred { cwd: Option<PathBuf> },
}
```

A shared resolver should live in `cm-capabilities/src/scope`, with capability specific policy layered above it:

- Browse: omitted scope defaults to `cwd_inferred`; ambiguity can be reported as resolution metadata if a deterministic result is still chosen.
- Recall: omitted scope defaults to `global`; `cwd_inferred` resolves before search or ancestor walk.
- Store and deposit: omitted scope defaults to `global`; `cwd_inferred` must pass strict confidence and ambiguity checks before creating scopes or entries.
- Export: omitted scope exports all; `cwd_inferred` resolves to an exact filter.

## Key Patterns

- Keep exact identity separate from unresolved selector intent. `ScopePath` is durable data; `ScopeSelector` is request interpretation.
- Keep transport compatibility decisions out of `cm-core`. MCP schema, CLI flags, query parameters, and frontend URL state belong in adapters.
- Generate public artifacts from `tools.toml`. Public schema removal is not complete until generated schema, help text, skill template, snapshots, and protocol fixtures are refreshed.
- For a breaking migration, schema removal is insufficient. Serde and web query extraction must explicitly reject removed public fields.

## Detailed Findings

### Approval status

Changes requested.

The high level design is correct, but the plan needs sharper issue and spec edits before implementation. The gaps are boundary and contract issues, not objections to the migration.

### Critical issues

1. Unknown field rejection is underspecified.

   Removing `scope_path` from MCP structs and generated schema will not necessarily make calls fail validation. Serde normally ignores unknown fields unless request structs opt into unknown field denial. Web query extraction also tends to ignore unknown query parameters. The acceptance criterion says calls with `scope_path` must fail validation, so each public request surface needs explicit rejection.

   Recommended spec edit: require `#[serde(deny_unknown_fields)]` on migrated MCP parameter structs where practical, or explicit preflight checks in `parse_params`. For cm-web query routes, parse raw query keys or keep a temporary `scope_path` field only to return a validation error. Add tests that pass both `scope` and `scope_path`, and `scope_path` alone, expecting validation errors.

2. `scope_mode` is obsolete under `cwd_inferred` but not explicitly removed.

   The current browse path exposes `scope_mode`, even though only `resolved` exists. The migration replaces public selector semantics with `scope: "cwd_inferred"`. Leaving `scope_mode` as a public input preserves old smart scope vocabulary and weakens the public contract.

   Recommended spec edit: state whether `scope_mode` is removed. I recommend removing it from MCP, CLI, web API, frontend request types, docs, and snapshots. Keep only response metadata fields such as `scope_mode` if existing output consumers depend on them, or rename later in a separate output cleanup.

3. Web write surfaces are not fully covered.

   The spec says `/api/entries` should use `scope` only, but the current create and merge paths accept core `NewEntry`, which contains `scope_path`. Frontend generated persisted models may retain `scope_path`, but create and merge bodies are request surfaces, not persisted output only.

   Recommended spec edit: add dedicated web request DTOs for create and merge that accept `scope`, resolve exact paths in `cm-web` through `cm-capabilities`, then construct `cm_core::NewEntry`. Do not expose `scope_path` in create or merge request bodies after the migration. Clarify update behavior if scope changes are ever supported.

4. Write confidence policy needs a precise contract.

   The spec says writes should reject ambiguous or low confidence inference, but does not define the threshold. The current resolver can produce medium confidence with ambiguity when multiple scopes share the top score. Without an exact policy, implementations and tests may drift.

   Recommended spec edit: define strict write acceptance as a unique top candidate with confidence at least medium, or require high confidence only. If medium is allowed, require no tied top candidate and include the resolved exact scope in the ack. Reject no cwd, no candidate, low confidence, and tied top score.

5. Scope selector parsing should be typed before capability logic.

   The current browse request carries raw `Option<String>` plus `Option<ScopePath>`. The migration should not repeat that duality across read and write capabilities.

   Recommended spec edit: each capability request should carry either `Option<ScopeSelector>` or a small public input type that is normalized immediately to `ScopeSelector`. Do not keep `scope_path` aliases on `StoreRequest`, `DepositRequest`, `ExportRequest`, or browse request types. This is the cleanest way to ensure public `scope_path` does not survive in capability APIs.

### Missing decisions

- Whether `cwd` remains a public supplemental input. The worktree rule references explicit `cwd`, so keep it if agents need deterministic tests and remote execution. Document that `cwd` is not a selector and only applies when `scope` is `cwd_inferred`.
- Whether `cwd_inferred` is accepted by all user facing CLI commands or only MCP and web agent APIs. The spec mentions MCP and web; CLI generated help will also change through `tools.toml`. Make CLI behavior explicit.
- Whether output fields named `scope_path` remain in returned persisted entities and mutation details. Keeping them is consistent with the spec, but state this clearly to prevent accidental output churn.
- Whether browse ambiguity is acceptable for read operations. Current browse can return a medium confidence result with ambiguity metadata. If read ambiguity should not be fatal, say so explicitly.
- Whether export filtering is exact only or subtree based. Current export gathers scopes by prefix for the metadata snapshot while entry export is store defined. The spec should state exact entry scope versus subtree export behavior.
- Whether `cx_get`, `cx_stats`, `cx_update`, and `cx_forget` are intentionally out of scope because they do not select by scope. Add one sentence to avoid unnecessary edits.

## Recommended Linear and Spec Edits

### ALP-2055 Add ScopeSelector capability type

Add acceptance details:

- Define `ScopeSelector` and `ResolvedScopeSelection` in `cm-capabilities/src/scope`.
- Public string parser accepts exact `ScopePath` strings and reserved `cwd_inferred` only.
- Remove legacy `auto` from public inputs. If kept internally for tests, it must not appear in generated public docs.
- Add separate policy helpers for read permissiveness and write strictness.

### ALP-2056 Normalize cwd through git worktree metadata

Add acceptance details:

- Implement cwd normalization in `cm-capabilities`, not `cm-core` or `cm-store`.
- Prefer a small internal abstraction around git detection so tests can cover linked worktrees without shelling out to real repos for every case.
- Test normal repo, linked worktree, non git cwd fallback, missing cwd fallback, and invalid empty cwd.
- Document that explicit `cwd` only applies to `scope: "cwd_inferred"`.

### ALP-2057 Refactor browse resolution around ScopeSelector

Add acceptance details:

- Replace `BrowseScopeInput` and raw `BrowseRequest.scope`/`scope_path` duality with `ScopeSelector`.
- Change default browse scope from `auto` to `cwd_inferred` in behavior, docs, advisories, and tests.
- Remove public `scope_mode` input unless a concrete second mode is added.
- Keep resolution metadata output for `cwd_inferred`.

### ALP-2058 Apply ScopeSelector to read capabilities

Add acceptance details:

- `RecallRequest` should accept `Option<ScopeSelector>` or an already resolved exact `ScopePath` plus selector metadata, not raw public strings in multiple places.
- `cx_recall`, `/api/agent/recall`, `/api/entries/recall`, and `/api/entries/search` should accept `scope` and reject `scope_path`.
- Omitted recall scope remains `global`.
- `cx_get` and stats are explicitly unchanged because they do not select scope.

### ALP-2059 Apply ScopeSelector to write capabilities

Add acceptance details:

- `StoreRequest` and `DepositRequest` expose `scope`, not `scope_path`, and remove serde alias compatibility.
- For `cwd_inferred`, resolve before `ensure_scope_chain`.
- Apply strict write policy before any mutation.
- Acks show the resolved exact scope.
- Web create and merge request DTOs are covered here or in ALP-2061.

### ALP-2060 Replace MCP tool inputs with scope

Add acceptance details:

- Update `tools.toml` parameter names and examples from `scope_path` and `auto` to `scope` and `cwd_inferred`.
- Remove `scope_path` from MCP schemas for browse, store, deposit, export, recall, and any affected fixtures.
- Add unknown field rejection for migrated MCP params so `scope_path` fails validation.
- Remove public `scope_mode` from MCP input schemas if the spec accepts that decision.

### ALP-2061 Migrate cm-web request surfaces to scope

Add acceptance details:

- Backend query DTOs: `/api/agent/browse`, `/api/entries`, `/api/entries/search`, `/api/agent/recall`, `/api/entries/recall`, `/api/export` use `scope` and reject `scope_path`.
- Frontend request types and API client use `scope`, not `scope_path`.
- Feed URL state migrates to `scope`; old `scope_path` URL params either fail visibly or are intentionally translated with a documented one release bridge. The current spec says fail, so tests should assert failure on API routes.
- Create and merge request bodies must not expose `scope_path` if `/api/entries` is treated as a public request surface.

### ALP-2062 Refresh generated public artifacts

Add acceptance details:

- Regenerate MCP schema JSON, CLI generated help, skill template, snapshots, protocol fixtures, and generated TypeScript models.
- Verify no generated public input schema contains `scope_path`.
- Verify persisted entity outputs may still contain `scope_path` where they represent stored exact identity.

### ALP-2063 Add vertical scope migration tests

Add test matrix:

- MCP browse default uses `cwd_inferred` and includes resolution metadata.
- MCP recall omitted scope uses `global`.
- MCP store and deposit omitted scope use `global`.
- MCP store and deposit `cwd_inferred` reject ambiguous and low confidence inference.
- MCP and web reject `scope_path` on migrated public request surfaces.
- Linked git worktree cwd resolves to source repo identity.
- Web feed browse, search, export, create, and merge use `scope`.

### ALP-2064 Publish scope migration documentation

Add migration guide requirements:

- Before and after examples for every public tool and web route.
- State that `auto` is replaced by `cwd_inferred`.
- State that `scope_path` remains a persisted output field but is no longer a public request input.
- State how linked git worktrees are normalized.

### ALP-2065 Run final scope migration verification

Add verification commands:

- `rg "scope_path" tools.toml crates/cm-cli/src/mcp crates/cm-web/src crates/cm-web/frontend/src` with expected remaining output limited to persisted output models, internal core/store exact path fields, and explicit rejection tests.
- `just check`.
- `just test`.
- Snapshot review for MCP schemas and cm-web API request types.

## Dependencies

- `cm-core` should remain dependency free from git and cwd concerns.
- `cm-capabilities` may need a small git detection dependency or process wrapper. Keep it behind scope resolution, with test seams.
- `cm-cli` and `cm-web` depend on `cm-capabilities` and should not duplicate selector resolution logic beyond parsing and public field rejection.

## Relevance to Helioy

This migration strengthens context-matters as Helioy's primary memory by making scope selection easier for agents while preserving exact durable scope identity. The linked worktree rule is important for Nancy and Codex workflows because agents often operate from ephemeral worktree names that should not become memory namespaces.

## Open Questions

- Should write `cwd_inferred` require high confidence only, or accept unique medium confidence?
- Should public `scope_mode` be removed now or treated as deprecated output metadata only?
- Should frontend old `scope_path` URL state fail immediately, or should the UI translate it for one release while APIs reject it?
- Should export by exact scope include descendant entries, or only the exact scope entries with subtree scope metadata?
