---
title: Monorepo Workspace Member Discovery Across All Package Managers
type: research
tags: [monorepo, workspaces, npm, pnpm, yarn, bun, nx, turborepo, lerna, rust-impl]
summary: Exact file paths, field paths, and glob semantics for workspace member discovery across all major JS/TS monorepo tools — for implementing in Rust.
status: active
source: quick-research
confidence: high
created: 2026-03-21
updated: 2026-03-21
---

## Summary

All mainstream JS package managers use `package.json` `workspaces` (array of globs) at the repo root, with pnpm as the sole exception (`pnpm-workspace.yaml` `packages` field). Turborepo and Nx are not workspace member discovery tools — they delegate to the underlying package manager. Lerna adds its own `lerna.json` `packages` field but defaults to the package manager's workspaces. Package names always come from `package.json` `name` in each member directory.

---

## Comparison Table

| Tool | Discovery File | Field Path | Format | Negation | Notes |
|---|---|---|---|---|---|
| npm | `package.json` | `.workspaces` | `string[]` globs | No official support | Also accepts `{ packages: string[], nohoist: string[] }` object form |
| Yarn Classic (v1) | `package.json` | `.workspaces` | `string[]` globs OR `{ packages: string[] }` object | Not documented | Root must have `"private": true` |
| Yarn Berry (v2+) | `package.json` | `.workspaces` | `string[]` globs | Not documented | Identical field to Classic; `.yarnrc.yml` has no workspace-member config |
| pnpm | `pnpm-workspace.yaml` | `.packages` | YAML `string[]` globs | `!pattern` supported | Root package is always included even without explicit listing |
| Bun | `package.json` | `.workspaces` | `string[]` globs | `!pattern` supported | Full glob syntax including `!**/excluded/**` |
| Turborepo | _none_ | _none_ | — | — | Reads from the underlying package manager's config; `turbo.json` contains task config only |
| Nx | _none_ (see notes) | _none_ | — | — | Discovers via package manager workspaces + any `project.json` files; `nx.json` is task/plugin config only |
| Lerna | `lerna.json` | `.packages` | `string[]` globs | Not documented | Defaults to package manager workspaces if field absent; default value `["packages/*"]` |

---

## Per-Tool Details

### npm

- **File**: `<root>/package.json`
- **Field**: `workspaces` — two accepted forms:
  - Array: `["packages/*", "apps/*"]`
  - Object: `{ "packages": ["packages/*"], "nohoist": ["**/react"] }` (the `nohoist` key is npm-specific)
- **Glob resolution**: globs are expanded relative to the repo root; only directories that contain a `package.json` are treated as workspace members
- **Package name**: `<member-dir>/package.json` → `.name`
- **Edge cases**:
  - npm does **not** document negation support (`!patterns`), though the underlying `glob` library technically supports it
  - A path that matches but has no `package.json` is silently skipped

### Yarn Classic (v1)

- **File**: `<root>/package.json`
- **Field**: `workspaces` — same as npm; array or `{ packages, nohoist }` object
- **Requirement**: root package.json must have `"private": true`
- **Package name**: `<member-dir>/package.json` → `.name`
- **Edge cases**:
  - Nested workspaces are unsupported
  - Workspaces must be filesystem descendants of root (no `../` paths)
  - Version mismatches cause npm-registry install rather than local linking

### Yarn Berry (v2+)

- **File**: `<root>/package.json`
- **Field**: `workspaces` — same array-of-globs format as Classic
- **Differences from Classic**: None at the workspace declaration level. `.yarnrc.yml` provides no workspace-member overrides. `nmHoistingLimits` and `enableTransparentWorkspaces` in `.yarnrc.yml` affect hoisting/resolution behavior only.
- **Package name**: `<member-dir>/package.json` → `.name`
- **Edge cases**: None beyond Yarn Classic's constraints

### pnpm

- **File**: `<root>/pnpm-workspace.yaml`
- **Field**: `packages` (YAML sequence)
- **Example**:
  ```yaml
  packages:
    - 'packages/*'
    - 'apps/**'
    - '!**/test/**'
  ```
- **Negation**: explicitly supported via `!pattern` prefix
- **Package name**: `<member-dir>/package.json` → `.name`
- **Edge cases**:
  - The workspace root itself is **always** included, even when no patterns match it
  - `pnpm-workspace.yaml` also supports `catalog` and `catalogs` fields for version pinning — these are NOT workspace member declarations

### Bun

- **File**: `<root>/package.json`
- **Field**: `workspaces` — same as npm
- **Negation**: fully supported (`!**/excluded/**`, `!packages/**/test/**`)
- **Package name**: `<member-dir>/package.json` → `.name`
- **Edge cases**: Bun documents full glob syntax (double-star, negation) more explicitly than npm does; behavior is a superset of npm

### Turborepo

- **Turborepo does not own workspace discovery.** `turbo.json` contains pipeline/task configuration only.
- Turborepo reads workspace members from whichever package manager is active:
  - pnpm: reads `pnpm-workspace.yaml`
  - npm/yarn/bun: reads root `package.json` `workspaces`
- **Implementation note for Rust**: to discover Turborepo workspaces, detect presence of `turbo.json` then fall through to the package manager detection logic.

### Nx

- **Nx does not own workspace discovery.** `nx.json` configures plugins, caching, and task defaults.
- Project discovery happens via:
  1. Package manager workspaces (any of the above)
  2. Presence of `project.json` files anywhere in the tree — Nx treats any directory containing a `project.json` as a project, regardless of package manager workspace declarations
- `workspace.json` is **deprecated** (was Nx's own project registry format, now removed)
- **Implementation note for Rust**: Nx workspaces = union of (package manager workspace members) + (directories containing `project.json`). Package name from `project.json` → `.name` field, falling back to `package.json` → `.name`.

### Lerna

- **File**: `<root>/lerna.json`
- **Field**: `packages` — array of glob strings, default `["packages/*"]`
- **Example**:
  ```json
  {
    "packages": ["packages/*", "apps/*"],
    "version": "independent"
  }
  ```
- **Precedence**: When `lerna.json` has an explicit `packages` field, it takes priority over the package manager's workspace config, allowing a subset. When absent, Lerna defaults to the package manager's workspaces config.
- **Package name**: `<member-dir>/package.json` → `.name`
- **Edge cases**:
  - Lerna 5+ (nx-backed) defers dependency management entirely to the package manager; `lerna.json packages` is for task orchestration scope
  - Negation support is not officially documented

---

## Package Name Resolution

**Universal rule**: read `<member-dir>/package.json` → `.name`.

No tool in the ecosystem uses directory name, `project.json` name field, or any other source as the canonical package identity for npm/yarn/pnpm resolution. The `name` field in `package.json` is the identifier used for:
- `node_modules` symlinking
- `workspace:` protocol resolution
- Published registry identity

The only partial exception is Nx's `project.json` which has its own `.name` for Nx's task graph — but this is Nx-internal and separate from the npm package name.

---

## Detection Order (Recommended for Rust Implementation)

To detect which workspace format a repo uses, check in this order:

1. `pnpm-workspace.yaml` exists → pnpm workspace
2. Root `package.json` `.workspaces` exists → npm/yarn/bun workspace
3. `lerna.json` exists → Lerna (may also have pnpm/npm workspaces underneath)
4. Any `project.json` files in tree → Nx (layered on top of 1 or 2)
5. `turbo.json` exists → Turborepo (layered on top of 1 or 2)

Note: tools 3-5 can coexist with tools 1-2. A repo can simultaneously have `pnpm-workspace.yaml` + `turbo.json` + `nx.json`.

---

## Sources

- [npm workspaces docs](https://docs.npmjs.com/cli/v10/using-npm/workspaces)
- [pnpm-workspace.yaml reference](https://pnpm.io/pnpm-workspace_yaml)
- [Yarn Berry workspaces](https://yarnpkg.com/features/workspaces)
- [Yarn Berry manifest reference](https://yarnpkg.com/configuration/manifest)
- [Yarn Classic workspaces](https://classic.yarnpkg.com/en/docs/workspaces/)
- [Bun workspaces](https://bun.sh/docs/install/workspaces)
- [Turborepo repository structure](https://turborepo.dev/docs/crafting-your-repository/structuring-a-repository)
- [Nx project configuration reference](https://nx.dev/docs/reference/project-configuration)
- [Nx nx.json reference](https://nx.dev/docs/reference/nx-json)
- [Lerna configuration reference](https://lerna.js.org/docs/api-reference/configuration)

## Open Questions

- Does npm actually support `!negation` globs in workspaces? The npm docs are silent; the underlying `glob` package supports it but npm may filter them pre-expansion. Verify against npm source before relying on it.
- Nx `project.json` `.name` field — is it always present? What is the fallback if absent?
- Lerna: does the modern nx-backed Lerna (v6+) still honor `lerna.json packages` or has it been fully superseded by the package manager's workspaces config?
