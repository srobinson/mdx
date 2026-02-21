# context-matters scope selector migration spec

Created: 2026-04-28
Updated: 2026-04-28
Status: reviewed, changes folded in
Project: context-matters
Parent issue: ALP-2054

## Decision

Make `scope` the only public request parameter for selecting context scope. Remove public `scope_path` request parameters as a breaking change. Keep `ScopePath` as the internal durable identity for stored entries, exact filters, exported rows, and scope tree rows.

Reserved value: `cwd_inferred`.

Public examples:

```json
{ "scope": "global/project:helioy/repo:manicure" }
```

```json
{ "scope": "cwd_inferred" }
```

Do not preserve `scope_path` as a legacy public alias. Calls that pass `scope_path` to migrated MCP, CLI, or cm-web request surfaces must fail validation. Removing it from generated schemas is not sufficient because serde and query parsing can ignore unknown fields unless rejection is explicit.

## Compatibility boundary

Public request inputs use `scope` only.

Internal and persisted exact path fields may remain named `scope_path`, including:

- `cm_core::Scope.path`
- `cm_core::NewEntry.scope_path`
- `cm_core::EntryFilter.scope_path`
- stored entries and exported rows
- output DTOs that represent persisted exact data
- explicit rejection tests and historical changelog text

## Public request surfaces in scope

The breaking migration applies to:

- MCP tools: `cx_browse`, `cx_recall`, `cx_store`, `cx_deposit`, `cx_export`.
- CLI flags generated from the public contract, including removal of `--scope-path`.
- cm-web user and agent request surfaces, including browse, search, export, create, and merge request bodies.
- frontend query serialization and feed URL state.

Unchanged tools: `cx_get`, `cx_stats`, `cx_update`, and `cx_forget` do not select by scope and are not part of this rename except for scans proving they do not expose public `scope_path` inputs.

## Removed public vocabulary

- `scope_path` is removed from public request inputs.
- `auto` is removed as a public inference selector.
- `scope_mode` is removed from public inputs. If retained, it may appear only in response metadata.

## `cwd` parameter

`cwd` remains a supplemental public input only when `scope` is `cwd_inferred`.

Validation rules:

- `cwd` must be omitted or non empty.
- Supplying `cwd` with an exact path scope is invalid.
- Omitted `cwd` means use process cwd.

## Worktree rule

`cwd_inferred` must infer from source repository identity rather than transient worktree directory name.

Resolution normalizes cwd through git when possible:

1. Start with explicit `cwd` if supplied, otherwise process cwd.
2. Find the nearest git repository with `git rev-parse --show-toplevel` or an equivalent testable helper.
3. Detect linked worktrees by comparing absolute `git rev-parse --git-dir` and `git rev-parse --git-common-dir`.
4. If the common dir basename is `.git`, treat its parent directory as the source repo root.
5. Use the source repo root basename as the repo signal and its parent basename as the project signal.
6. If git detection fails, fall back to the existing cwd basename behavior.

A temp fixture should use a source repo name that differs from the worktree directory name. For example, a cwd under:

`/tmp/context-matters-worktrees/nancy-ALP-1768`

should infer repo `context-matters`, not repo `nancy-ALP-1768`, when the common git dir is:

`/tmp/context-matters/.git`

## Internal model

Add a single unresolved selector in `cm-capabilities`, not `cm-core`:

```rust
pub enum ScopeSelector {
    Path(ScopePath),
    CwdInferred { cwd: Option<PathBuf> },
}
```

Use resolved exact paths after selection:

```rust
pub struct ResolvedScopeSelection {
    pub scope_path: Option<ScopePath>,
    pub resolution: Option<ScopeResolution>,
    pub requested_scope: String,
}
```

Capability request structs should carry `Option<ScopeSelector>` or a normalized `ScopeSelector`. They should not carry both `scope` and `scope_path`.

`cm-core` remains unchanged. It continues to own:

- `ScopePath`
- `Scope`
- `NewEntry.scope_path`
- `EntryFilter.scope_path`
- `ContextStore` methods that accept exact paths

## Tool behavior

### cx_browse

- Accept `scope` only.
- `scope` may be an exact path or `cwd_inferred`.
- Omitted `scope` defaults to `cwd_inferred`.
- Return resolution metadata for `cwd_inferred`.
- Reject `scope_path`, `auto`, and `scope_mode` inputs.

### cx_recall

- Accept `scope` only.
- `scope` may be an exact path or `cwd_inferred`.
- Omitted `scope` defaults to `global`.
- Resolve `cwd_inferred` before search or ancestor walk.
- Reject `scope_path` and `auto`.

### cx_store

- Accept `scope` only.
- `scope` may be an exact path or explicit `cwd_inferred`.
- Omitted `scope` defaults to `global`.
- For `cwd_inferred`, resolve before `ensure_scope_chain`.
- Inferred writes require one unique high confidence candidate.
- Reject no candidate, low or medium confidence, tied top candidates, empty cwd, and failed inference that cannot fall back clearly.
- Rejected inferred writes must create no entries and no scope chain rows.
- Acknowledgements print the resolved exact scope.
- Reject `scope_path` and `auto`.

### cx_deposit

Same as `cx_store`.

### cx_export

- Accept `scope` only.
- Exact path filters export by exact scope, matching current export semantics.
- Omitted `scope` exports all active entries.
- `cwd_inferred` filters to the resolved exact scope.
- Reject `scope_path` and `auto`.

## Web behavior

- `/api/agent/browse` and `/api/entries` use `scope` only.
- `/api/entries/search` uses `scope` only.
- `/api/export` uses `scope` only.
- Create and merge request bodies use dedicated cm-web request DTOs with `scope`, not `cm_core::NewEntry` directly as a public request body.
- Exact UI scope filter values pass exact scope path strings through `scope`.
- Persisted entity models and response DTOs may retain `scope_path` where they represent stored exact data.
- Feed URL state migrates from `scope_path` to `scope`. Old `scope_path` feed URLs should be migrated client side when possible; if both are present, `scope` wins and `scope_path` is removed from the next serialized URL.

## Strict rejection implementation

MCP request parsing must explicitly reject removed public fields. Acceptable approaches:

- `#[serde(deny_unknown_fields)]` on migrated parameter structs where practical.
- Manual preflight validation against raw JSON keys before serde parsing.

cm-web query and JSON body parsing must explicitly reject removed public fields. Acceptable approaches:

- Parse raw query keys before typed extraction.
- Keep temporary rejection only fields solely to return a validation error.

Required rejected cases:

- `scope_path` alone.
- `scope` with `scope_path`.
- `auto` as a scope value.
- `scope_mode` as an input.
- `cwd` with an exact path scope.

## Generated public docs

Update `tools.toml` as the source of truth, then regenerate:

- MCP schema JSON
- CLI generated help
- skill template
- snapshots and protocol fixtures
- generated TypeScript where affected

Public docs show only `scope`. They call `cwd_inferred` the reserved value for cwd based resolution. They explain that `scope_path` remains visible only as stored exact output data.

## Tests

Required coverage:

- MCP schema scan proving migrated input schemas expose `scope`, never `scope_path`.
- MCP `tools/call` rejection tests for `scope_path` on `cx_browse`, `cx_recall`, `cx_store`, `cx_deposit`, and `cx_export`.
- CLI help tests proving `--scope` and `cwd_inferred` examples.
- CLI regression proving `--scope-path` is removed or rejected.
- cm-web backend parity for browse, search, and export with exact `scope` and `scope=cwd_inferred`.
- cm-web rejection tests for public `scope_path` request inputs.
- Frontend query serialization tests proving client APIs send `scope`, not `scope_path`.
- Feed URL migration tests for old `scope_path` URLs.
- Linked worktree fixture built from a temp source repo plus `git worktree add`.
- Store and deposit rejection tests proving failed inferred writes create no entries and no scope rows.

## Acceptance criteria

- No public MCP tool input schema exposes `scope_path`, `scope_mode`, or `auto` as the inference selector.
- No cm-web user or agent request type exposes `scope_path` as a request parameter or request body field.
- CLI public flags use `--scope`; `--scope-path` is removed or rejected.
- `ScopePath` remains in domain and persistence types.
- `scope: "cwd_inferred"` resolves linked git worktrees to their source repo root identity.
- Write tools using `cwd_inferred` require one unique high confidence candidate and reject before mutation otherwise.
- Calls with `scope_path` fail validation on migrated public request surfaces.
- All generated docs and snapshots are updated.
- `just check`, `just test`, and doc tests pass.
- Final verification includes a clean diff check after commands that may rewrite files.

## Research inputs

- `~/.mdx/research/scope-handling-vertical-path-context-matters.md`
- `~/.mdx/research/cm-cli-scope-surface-refactor-context-matters.md`
- `~/.mdx/research/vertical-integration-scope-refactor-context-matters.md`
- `~/.mdx/research/scope-selector-migration-architecture-review-context-matters.md`
- `~/.mdx/research/coverage-review-scope-selector-migration-context-matters.md`
