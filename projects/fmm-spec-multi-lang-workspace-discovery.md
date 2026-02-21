---
title: "fmm: Multi-Language Workspace Discovery and Import Resolution"
project: fmm
created: 2026-03-21
status: draft
---

# Multi-Language Workspace Discovery and Import Resolution

## Problem

fmm's workspace discovery (`resolver/workspace.rs`) and import resolution (`resolver/mod.rs`, `manifest/dependency_matcher.rs`) are hardcoded to JS/TS. In multi-language repos (e.g., context-matters: Rust + TS), dependency graph features (`fmm_dependency_graph`, `fmm_search --depends_on`) produce incomplete results for non-JS languages.

## Architecture

Two new traits replace the monolithic implementations:

### WorkspaceDiscoverer trait

```rust
pub trait WorkspaceDiscoverer: Send + Sync {
    fn detect(&self, repo_root: &Path) -> bool;
    fn discover(&self, repo_root: &Path) -> WorkspaceInfo;
}
```

Top-level `discover()` runs ALL applicable discoverers and merges results. A Rust+TS repo fires both Cargo and npm discoverers.

### ImportResolver trait

```rust
pub trait ImportResolver: Send + Sync {
    fn resolve(&self, importer: &Path, specifier: &str) -> Option<PathBuf>;
}
```

`build_reverse_deps` dispatches to the correct resolver based on source file language.

## Ecosystem Reference

### JS/TS (existing, needs edge case fixes)

**Workspace discovery:**
- pnpm: `pnpm-workspace.yaml` `.packages[]` (YAML string array, supports `!negation`)
- npm/yarn/bun: `package.json` `.workspaces[]` (string array) or `.workspaces.packages[]` (object form)
- Lerna: `lerna.json` `.packages[]` (default `["packages/*"]`), lower priority than package manager
- Turborepo: delegates to package manager (no own member list)
- Nx: package manager + any directory containing `project.json`
- Package name: always `<member>/package.json` `.name`

**Detection order:** pnpm-workspace.yaml > package.json workspaces > lerna.json

**Import resolution:** oxc_resolver (existing CrossPackageResolver). Already handles tsconfig paths, workspace aliases, Node resolution algorithm.

**Gap in current code:** Only handles pnpm + npm array form. Missing: `workspaces.packages` object form (used with nohoist).

### Rust

**Workspace discovery:**
- File: root `Cargo.toml` `[workspace]` section
- Members: `members` field (glob patterns relative to root)
- Exclusions: `exclude` field (exact paths)
- Validation: each matched directory must contain `Cargo.toml` with `[package]`
- Virtual workspaces have no `[package]` section at root
- Crate name: `[package] name` with `-` replaced by `_`. Override: `[lib] name`.

**Import resolution (cross-crate):**
1. Parse each member's `[dependencies]` for `path = "..."` entries
2. Handle `workspace = true` by looking up `[workspace.dependencies]` in root
3. Handle renamed deps: `[dependencies] alias = { package = "real-name", path = "..." }`
4. Map `use alias::x::y` to resolved member's `src/x/y.rs` or `src/x/y/mod.rs`

**Import resolution (intra-crate):**
- `crate::x::y` resolves to `src/x/y.rs` or `src/x/y/mod.rs`
- `super::x` resolves relative to parent module
- `#[path = "..."]` attribute overrides (out of scope for initial impl)

**Module resolution algorithm:**
```
crate::a::b::c
  → src/a/b/c.rs       (file)
  → src/a/b/c/mod.rs   (directory module)
```

### Go

**Workspace discovery:**
- File: `go.work` at repo root
- Members: `use` directives (relative paths to module directories)
- Each member has `go.mod` with `module` directive declaring its import path
- Discovery: walk up from CWD to find `go.work`; fallback to single `go.mod`

**Import resolution:**
1. Collect workspace modules: `{module_path, local_dir}` from go.work use + go.mod module
2. Longest-prefix match import path against workspace module paths
3. `import "example.com/mod/pkg/foo"` with module `example.com/mod` at `./mod/` resolves to `./mod/pkg/foo/`
4. Standard library: no `.` in first path element (e.g., `fmt`, `net/http`)
5. Package name parsed from source files (`package foo` clause), may differ from directory name

### Python

**Workspace discovery:**
- uv: `pyproject.toml` `[tool.uv.workspace] members` (globs) -- only true workspace system
- Poetry/PDM: no native workspaces; path dependencies in each member's pyproject.toml
- Pants: `pants.toml` `[source] root_patterns` + BUILD files
- Hatch: per-environment `[tool.hatch.envs.<name>] workspace.members`
- Package name: complex. Distribution name != import name != directory name.
  - Normalize: lowercase, replace runs of `[-._]` with single `_`
  - Check `src/<name>/` (src-layout) then `./<name>/` (flat-layout)
  - Build backend can override import name

**Import resolution:**
- Import name determination requires checking build backend config
- src-layout vs flat-layout detection
- `__init__.py` presence (required by setuptools find_packages, optional for modern backends)
- Dotted imports already partially handled by existing `dotted_dep_matches`

## Phasing

### Phase 1: Trait extraction and refactor
- Define `WorkspaceDiscoverer` trait
- Extract existing pnpm/npm code into `JsWorkspaceDiscoverer`
- Define `ImportResolver` trait
- Extract `CrossPackageResolver` into `JsImportResolver`
- Merge logic: `discover()` runs all detected discoverers, merges `WorkspaceInfo`
- Language-aware dispatch in `build_reverse_deps`

### Phase 2: Rust support
- `CargoWorkspaceDiscoverer`: parse Cargo.toml members/exclude, resolve globs, read crate names
- `RustImportResolver`: parse [dependencies] path entries, resolve cross-crate + intra-crate module paths

### Phase 3: Go support
- `GoWorkspaceDiscoverer`: parse go.work use directives + go.mod module paths
- `GoImportResolver`: longest-prefix module matching + directory mapping

### Phase 4: Python support
- `PythonWorkspaceDiscoverer`: uv workspaces as primary target
- Basic Python import name resolution (distribution name normalization + layout detection)

### Phase 5: JS/TS edge cases
- Handle `workspaces.packages` object form
- Lerna `lerna.json` fallback

## Files Affected

| File | Change |
|------|--------|
| `crates/fmm-core/src/resolver/workspace.rs` | Extract trait, refactor, add implementations |
| `crates/fmm-core/src/resolver/mod.rs` | Extract ImportResolver trait, add Rust/Go resolvers |
| `crates/fmm-core/src/manifest/dependency_matcher.rs` | Language-aware dispatch in build_reverse_deps |
| `crates/fmm-store/src/writer.rs` | Pass language info through rebuild_and_write_reverse_deps |

## Research documents
- `~/.mdx/research/monorepo-workspace-discovery-all-package-managers.md`
- `~/.mdx/research/cargo-workspace-member-discovery-rust-reference.md`
- `~/.mdx/research/python-workspace-monorepo-member-discovery-reference.md`
- `~/.mdx/research/go-workspace-module-import-resolution-reference.md`
