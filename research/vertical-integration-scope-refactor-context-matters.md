---
title: Vertical Integration Findings for context-matters Browse Scope Refactor
type: research
tags: [context-matters, cm-web, scope-refactor, typescript, parity-tests]
summary: cm-web, generated TS bindings, parity tests, and docs still expose browse scope_path in several user-facing paths that need migration or compatibility coverage.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

The browse scope refactor has visible integration points beyond the core capability crates. cm-web backend and frontend currently treat `scope_path` as a public exact browse filter, while smart browse already exists through `scope=auto` plus `cwd`. Removing public `scope_path` and introducing `scope="cwd_inferred"` requires adapter, URL state, docs, generated schema, and parity test updates.

## Project Metadata

- Language and frameworks: Rust workspace, Axum backend, React 19 plus Vite frontend.
- Type generation: `ts-rs` exports Rust DTOs into `crates/cm-web/frontend/src/api/generated/`.
- Frontend checks: `crates/cm-web/frontend/package.json` scripts `check`, `typecheck`, and `build`.
- Type regeneration: `just gen-types` runs `cargo test -p cm-core export_bindings_` and `cargo test -p cm-capabilities export_bindings_`.
- Distribution docs: npm package wrappers live under `npm/context-matters` and `npm/@context-matters/cli`.

## Architecture

### cm-web backend

- `crates/cm-web/src/api/agent.rs`
  - `BrowseQuery` accepts `scope`, `scope_path`, `scope_mode`, `cwd`, `include_resolution`, and filters.
  - `execute_browse` validates query fields, parses `scope_path` with `ScopePath::parse`, parses `scope_mode`, converts `cwd`, then builds `cm_capabilities::browse::BrowseRequest`.
  - `project_executed_browse` maps the capability result to `WebBrowseView`.
  - `browse_handler` serves `/api/agent/browse`.
- `crates/cm-web/src/api/entries.rs`
  - `browse` reuses `agent::execute_browse`, so `/api/entries` and `/api/agent/browse` share browse behavior.
  - `search` still accepts `scope_path` for `/api/entries/search`, separate from browse.
  - `recall` goes through recall query parsing and uses `scope`, not `scope_path`.
- `crates/cm-web/src/api/export.rs`
  - `ExportQuery` accepts `scope_path` for JSON export filtering. This is not the public browse API and should not be removed unless export semantics are also changing.
- `crates/cm-web/src/main.rs`
  - Serves `/api` plus embedded frontend assets. No scope logic.

### cm-web frontend

- `crates/cm-web/frontend/src/api/client.ts`
  - `BrowseParams` and `AgentBrowseParams` expose `scope`, `scope_path`, `scope_mode`, `cwd`, and `include_resolution`.
  - `api.entries.browse` and `api.agent.browse` serialize `scope_path` into query parameters.
  - `api.entries.search` serializes `scope_path` for search.
  - `api.export` serializes `scope_path` for export.
- `crates/cm-web/frontend/src/api/hooks.ts`
  - `queryKeys.entries.browse` and `queryKeys.agent.browse` key directly on params objects, so any rename changes cache identity.
  - `useEntries` and `useAgentBrowse` pass params through without normalization.
- `crates/cm-web/frontend/src/routes/feed/search.ts`
  - `FeedSearch` validates `scope_path` from URL query state.
- `crates/cm-web/frontend/src/routes/feed/FeedPage.tsx`
  - Reads `scope_path` from route search.
  - Passes it to `useEntries` for curate mode and to `FilterBar` as a filter value.
- `crates/cm-web/frontend/src/components/BrowsePane.tsx`
  - Local state variable `scope` is sent as `scope_path` to `useAgentBrowse`.
  - `FilterBar` updates are interpreted through `scope_path`.
- `crates/cm-web/frontend/src/components/FilterBar.tsx`
  - `FilterState` has `scope_path`.
  - Facet key and chips are `scope_path` backed, using stats scope tree values as exact filter choices.
- `crates/cm-web/frontend/src/routes/index.tsx`, `crates/cm-web/frontend/src/components/ScopeTree.tsx`, `crates/cm-web/frontend/src/components/QualityAlerts.tsx`
  - Route links write `scope_path` search params for feed navigation.
- Entry write and edit surfaces still need exact entry scopes:
  - `crates/cm-web/frontend/src/components/NewEntryEditor.tsx`
  - `crates/cm-web/frontend/src/components/EntryEditor.tsx`
  - `crates/cm-web/frontend/src/components/MergePanel.tsx`

### Generated TypeScript bindings

- Generated files live in `crates/cm-web/frontend/src/api/generated/` and are intentionally excluded from Biome edits by `crates/cm-web/frontend/biome.json`.
- Relevant generated files:
  - `ScopePath.ts`: aliases Rust `ScopePath` to `string` and documents invariants.
  - `Entry.ts`, `NewEntry.ts`, `UpdateEntry.ts`, `Scope.ts`, `NewScope.ts`, `EntryFilter.ts`: still need exact `scope_path` for storage and mutations.
  - `WebBrowseView.ts`, `WebBrowseHeader.ts`, `WebBrowseRow.ts`: browser projection surface.
  - `WebScopeResolution.ts`, `WebScopeResolutionCandidate.ts`: smart browse inference metadata.
- `client.ts` wraps generated browse view types because ts-rs maps some numeric fields differently from JSON parse behavior.

### Parity tests

- `crates/cm-web/tests/parity/browse.rs`
  - `browse_basic_parity`: `/api/agent/browse` equals capability projection.
  - `browse_with_filters_parity`: kind filter parity.
  - `browse_agent_sort_matches_entries_parity`: `/api/agent/browse` and `/api/entries` sort parity.
  - `browse_agent_auto_scope_parity`: `scope=auto&cwd=...` resolves repo scope and returns resolution.
  - `browse_entries_auto_scope_parity`: same behavior through `/api/entries`.
  - `browse_scope_path_exact_parity`: currently pins public `scope_path` exact browse behavior and absence of resolution.
- `crates/cm-web/tests/parity/pagination.rs`
  - `browse_pagination_parity`: exact `scope_path` pagination parity.
  - `browse_auto_scope_pagination_parity`: auto scope pagination parity.
- `crates/cm-web/tests/parity/support.rs`
  - `seed_entries` creates global, project, and repo scoped fixtures including `global/project:helioy/repo:context-matters`.
  - `capability_browse` builds expected `WebBrowseView` by running the capability layer and projecting through `project_web_browse`.
- `crates/cm-web/tests/parity/headers.rs`
  - Pins required `WebBrowseView` header fields but does not pin scope resolution fields.
- `crates/cm-web/tests/parity/recall.rs`
  - Recall uses `scope`, not browse `scope_path`.

### Docs and npm surfaces

- `README.md`
  - Still says three crates, while the workspace now includes cm-capabilities and cm-web. No smart browse details.
- `PROJECT.md`
  - Documents five crates, cm-web, npm wrapper, plugin integration, and content hashing with `scope_path`.
- `TLDR.md`
  - Documents five crates, web commands, and npm/plugin integration. No parameter level smart browse guidance.
- `CHANGELOG.md`
  - Mentions smart browse local scope inference and cm-web introduction.
- `tools.toml`
  - Primary public docs for MCP and generated CLI/plugin docs.
  - `cx_browse` currently says it defaults to inferred local scope when `scope_path` is omitted.
  - `cx_browse` params include both `scope` and compatibility `scope_path`.
- `crates/cm-cli/templates/SKILL.md`
  - Generated skill docs still include examples with `scope_path` for `cx_browse` and `cx_export`.
- `npm/context-matters/package.json`, `npm/@context-matters/cli/package.json`, `npm/context-matters/scripts/install.js`
  - Distribution only. No browse parameter docs beyond package description.

## Key Patterns

- Adapter parity is enforced by routing both `/api/agent/browse` and `/api/entries` through `agent::execute_browse` and comparing HTTP JSON against direct capability projection.
- The frontend currently uses exact scope paths as navigable UI state and facet values. This is broader than the MCP public tool surface.
- The same string name `scope_path` means different things across layers: exact browse filter, entry storage field, export filter, mutation diff key, and display metadata.

## Risks for Removing Public Browse `scope_path`

1. **Conflating browse API removal with storage model removal**
   - Entry creation, update, merge, scope tree, export, and display still require exact `scope_path`.
   - Only public browse filter semantics should change unless the storage model is in scope.

2. **Breaking cm-web route URLs**
   - `/feed?scope_path=...` is used by feed validation, scope tree links, quality alerts, filters, and browse pane state.
   - Removing it without migration will break existing links and selected scope views.

3. **Breaking exact scope curation workflows**
   - The current UI scope facet is an exact scope selector backed by stats scope tree values.
   - If exact browse is no longer public, the UI needs an explicit replacement concept: exact internal filter, inferred cwd filter, or no scope facet.

4. **Ambiguous new `scope="cwd_inferred"` semantics**
   - Existing smart browse uses `scope="auto"` and `cwd`.
   - Introducing `cwd_inferred` needs clear behavior for omitted `cwd`, explicit `cwd`, `include_resolution`, and pagination cursor reuse.

5. **Compatibility drift between `/api/agent/browse` and `/api/entries`**
   - Both currently share one backend path. Keep that shared execution path or add parity tests for both endpoints after the parameter change.

6. **Generated schema and docs drift**
   - `tools.toml` drives MCP schema, CLI help, and skill docs. If public `scope_path` is removed from MCP but not regenerated, clients will still see stale parameters.

7. **Cache key churn in React Query**
   - `queryKeys` include raw params. A rename from `scope_path` to `scope` or a default to `cwd_inferred` changes cache identity and pagination behavior.

8. **Exact pagination behavior may regress**
   - Existing tests cover exact `scope_path` pagination and auto scope pagination separately. The new mode must preserve stable cursors after scope inference.

## Test Coverage Needed

### Backend and parity

- Replace `browse_scope_path_exact_parity` with tests that match the intended compatibility stance:
  - If `scope_path` is rejected publicly, assert a structured 400 on `/api/agent/browse?scope_path=...` and `/api/entries?scope_path=...`.
  - If accepted as deprecated compatibility, assert it remains exact and emits no resolution.
- Add `/api/agent/browse?scope=cwd_inferred&cwd=...` parity against the capability request shape.
- Add `/api/entries?scope=cwd_inferred&cwd=...` parity to preserve alias behavior.
- Add pagination parity for `scope=cwd_inferred` with cursor reuse.
- Add validation tests for conflicts: `scope=cwd_inferred` plus `scope_path`, invalid `cwd`, omitted `cwd` if unsupported, and unknown `scope` values.
- Add resolution shape assertions for `WebScopeResolution`: `requested_scope`, `resolved_scope`, `scope_mode`, `confidence`, `candidates`, and `signals`.

### Frontend

- Typecheck after updating `BrowseParams`, `AgentBrowseParams`, `FeedSearch`, `FilterState`, `FeedPage`, `BrowsePane`, and route links.
- Add component or route tests if available for:
  - Existing `/feed?scope_path=...` links if migration is supported.
  - New URL param shape for inferred browsing.
  - Filter chip labels and clear all behavior after renaming.
- Verify React Query pagination still appends pages with the new params and resets when scope mode changes.

### Generated bindings and docs

- Run `just gen-types` after Rust DTO changes.
- Run the tool docs generation path that validates `tools.toml` into MCP schema, CLI help, and skill docs.
- Check generated `crates/cm-cli/src/mcp/generated_schema/cx_browse.json` no longer advertises removed public params.
- Update examples in `README.md`, `PROJECT.md`, `TLDR.md`, `tools.toml`, and `crates/cm-cli/templates/SKILL.md` while leaving `scope_path` examples for store and export if those APIs remain exact.

### Distribution

- npm package metadata has no parameter level docs, but release artifacts should include regenerated binaries and embedded frontend assets.
- Smoke test `npx context-matters serve` only after release packaging changes, not for the source refactor itself.

## Open Questions

- Does “removing public scope_path” apply only to `cx_browse` and web browse endpoints, or also `/api/entries/search`, export, and frontend URL state?
- Should cm-web keep an internal exact scope filter for curation while MCP hides `scope_path`?
- Should `scope="cwd_inferred"` replace `scope="auto"`, alias it, or coexist with different semantics?
- What should happen when no cwd is supplied: infer from server process cwd, use global, or reject?
