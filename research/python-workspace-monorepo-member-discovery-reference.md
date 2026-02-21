---
title: Python Workspace/Monorepo Member Discovery Reference
type: research
tags: [python, monorepo, workspaces, uv, poetry, hatch, pants, setuptools, pyproject-toml, import-names, package-discovery]
summary: Exact file paths, field paths, discovery algorithms, and import-name resolution for all major Python workspace/monorepo tools — for implementing a code indexing workspace member discoverer.
status: active
source: quick-research
confidence: high
created: 2026-03-21
updated: 2026-03-21
---

## Summary

Python has no single universal workspace standard. The ecosystem spans six distinct models: uv workspaces (explicit glob-based, similar to Cargo), Poetry path-dependencies (no native workspace concept), Hatch environment workspaces (env-scoped, not repo-scoped), Pants (build-graph with source roots), PDM (no native workspace support as of 2026), and setuptools/pyproject.toml (single-package, no workspace concept). Import names differ from distribution names — the mapping is: lowercase the project name, replace all runs of `-`, `.`, `_` with underscores. But that is only the default; every tool has an override mechanism.

---

## The Core Complexity: Import Name vs. Distribution Name

Before covering tools, understand this foundational issue.

### Three distinct names exist for every Python package

1. **Distribution name** (`[project] name` in pyproject.toml): used on PyPI, hyphen-friendly. E.g., `my-package`.
2. **Import name** (the directory/module on disk): used in `import` statements. Must be a valid Python identifier — underscores only, no hyphens. E.g., `my_package`.
3. **Directory name** (the actual filesystem path): usually matches the import name, but is a build-backend choice.

### Default normalization rule

Most build backends derive the import name from the distribution name by:
- Lowercasing all characters
- Replacing any run of `-`, `.`, or `_` with a single `_`

So `My-Package`, `my.package`, `my_package`, `my--package` all map to import name `my_package`.

This is **not** the PyPA name normalization spec (which normalizes to hyphens for distribution names). For import names, underscores are the canonical form.

### src-layout vs flat-layout

**Flat layout** (import package at project root):
```
project/
├── pyproject.toml
└── my_package/
    ├── __init__.py
    └── module.py
```
`import my_package` resolves to `./my_package/`.

**src-layout** (import package under `src/`):
```
project/
├── pyproject.toml
└── src/
    └── my_package/
        ├── __init__.py
        └── module.py
```
`import my_package` resolves to `./src/my_package/`. The `src/` directory is not itself importable.

**Single-module distribution** (no package directory, just a `.py` file):
```
project/
├── pyproject.toml
└── my_module.py
```
`import my_module` resolves to `./my_module.py`.

### Role of `__init__.py`

- `find_packages()` (setuptools) **requires** `__init__.py` to recognize a directory as a package.
- `find_namespace_packages()` (setuptools), uv, and most modern backends do **not** require it — they support PEP 420 implicit namespace packages.
- For a code indexer, a directory should be considered a Python package if it either contains `__init__.py` OR if the build backend config explicitly declares it.

### How to determine the import name without running the build tool

Priority order:
1. Check tool-specific override field (see per-tool sections below).
2. If no override: apply the normalization rule (lowercase, collapse `-_.` runs to `_`) to `[project] name`.
3. Verify that a matching directory exists: check `src/<import_name>/`, then `./<import_name>/`, then `./<import_name>.py`.
4. If none of those exist, the project has a non-standard layout and requires explicit tool config.

---

## Tool-by-Tool Reference

---

### 1. uv Workspaces

**Status**: First-class, actively developed. Growing quickly as of 2025-2026.

#### Workspace discovery file and fields

Root `pyproject.toml`:
```toml
[tool.uv.workspace]
members = ["packages/*", "apps/*"]      # required; list of glob patterns
exclude = ["packages/internal"]         # optional; patterns to exclude
```

Both `members` and `exclude` accept glob patterns expanded relative to the workspace root. Negation works via the `exclude` field, not via `!` prefix in `members`.

**Constraint**: every directory matched by `members` (and not excluded) MUST contain a `pyproject.toml`. Matched directories without one are an error.

The workspace root itself is implicitly a member (it has its own `[project]` section).

#### Member detection algorithm (for a code indexer)

1. Find the workspace root: the directory containing a `pyproject.toml` with a `[tool.uv.workspace]` section.
2. Expand each glob in `members` relative to that root.
3. Remove directories matched by `exclude` globs.
4. Each remaining directory is a workspace member. Read its `pyproject.toml` for `[project] name`.

#### Import name determination

uv's own build backend (`uv build`) uses:
- Default: lowercase `[project] name`, replace `-/.` with `_`. Look for `src/<name>/` first, then `./<name>/`.
- Override: `[tool.uv.build-backend] module-name` explicitly sets the import name.
- Override: `[tool.uv.build-backend] module-root` changes the search root (default: `src`; set to `""` for flat layout).

For a third-party build backend (hatchling, setuptools), those backends' own rules apply (see their sections).

#### Reference

- https://docs.astral.sh/uv/concepts/projects/workspaces/
- https://docs.astral.sh/uv/concepts/build-backend/

---

### 2. Poetry

**Status**: No native workspace concept. Single-package tool. Monorepo patterns use path dependencies.

#### "Workspace" pattern: path dependencies

Poetry has no `[tool.poetry.workspace]` or `members` field. Monorepos use path dependencies in each member's `pyproject.toml`:

```toml
[tool.poetry.dependencies]
core = {path = "../core", develop = true}
```

`develop = true` installs in editable mode. This is a dependency declaration, not a workspace discovery mechanism — there is no single file that enumerates all members.

#### What a code indexer should do for Poetry

Since there is no workspace manifest, discovery must be heuristic:
1. Find all `pyproject.toml` files in the tree.
2. For each, check `[tool.poetry]` table presence and `[project]` or `[tool.poetry] name`.
3. Path dependencies in `[tool.poetry.dependencies]` with a `path =` key point to sibling member directories.

#### Import name determination

Poetry's automatic detection: a single module or package whose name matches the normalized project name (hyphens → underscores). It checks two locations: same level as `pyproject.toml` (flat), or inside `src/` (src-layout).

Explicit override via `[tool.poetry] packages`:
```toml
[tool.poetry]
packages = [
    {include = "my_package"},
    {include = "extra_module", from = "lib"}
]
```
`include` is the **import name** (directory name to include). `from` is the subdirectory to look in (default: project root).

#### Reference

- https://python-poetry.org/docs/pyproject/
- https://github.com/python-poetry/poetry/issues/6850 (workspace support tracking issue — open as of 2026)

---

### 3. Hatch / Hatchling

**Status**: Hatch environments support workspace-style multi-package development, but this is **env-scoped**, not a repository-level workspace manifest. Hatchling is the build backend.

#### Hatch environment workspace (not a repo workspace)

`hatch.toml` or `[tool.hatch]` section in `pyproject.toml`:
```toml
[tool.hatch.envs.default]
workspace.members = ["packages/*"]
workspace.exclude = ["packages/internal"]
```

This tells Hatch to install those packages as editable dependencies into the named environment. It is per-environment configuration — not a top-level workspace membership declaration.

**For a code indexer**: this does identify the directories that contain sibling packages, but only within the context of a specific environment.

#### Hatch project discovery (multi-project mode)

Hatch itself (the dev tool, not hatchling the build backend) has a project-mode that discovers multiple projects:
```toml
# ~/.config/hatch/config.toml
mode = "project"
[dirs]
project = ["/path/to/monorepo"]
```
or explicitly:
```toml
[projects]
proj1 = "/path/to/project1"
```
This is global Hatch user config, not in the repository.

#### Import name determination (hatchling build backend)

Hatchling auto-detects src-layout and flat-layout. The `[project] name` normalized form (hyphens → underscores) is the default import name. Explicit override:
```toml
[tool.hatchling.build.targets.wheel]
packages = ["src/my_package"]
```
or namespace packages via `shared-data`, `shared-scripts`, etc.

#### Reference

- https://hatch.pypa.io/1.16/how-to/environment/workspace/
- https://hatch.pypa.io/1.9/config/hatch/

---

### 4. Pants

**Status**: Full monorepo build system. Not a packaging tool. Uses BUILD files and source roots.

#### Key concepts

Pants does not use `pyproject.toml` for target discovery. Instead:

- **BUILD files**: present in each directory with Python sources. Declare `python_sources()`, `python_library()`, `python_binary()` targets.
- **Source roots**: the directories that serve as the base for import resolution (analogous to `$PYTHONPATH` entries).

#### `pants.toml` configuration

```toml
[source]
root_patterns = [
    "/",
    "src",
    "src/python",
    "src/py",
]
```

Default `root_patterns`: `["/", "src", "src/python", "src/py", "src/java", "src/scala", "src/thrift", "src/protos", "src/protobuf"]`.

Alternative: marker files instead of patterns:
```toml
[source]
marker_filenames = ["setup.py", "pyproject.toml"]
```

A directory containing the marker file is treated as a source root.

#### Import name resolution in Pants

The source root acts as the `sys.path` entry. A file at `src/python/myapp/models.py` with source root `src/python` is importable as `myapp.models`. The import name is derived purely from the filesystem path relative to the source root — no configuration needed beyond declaring the source root itself.

#### BUILD file structure

```python
# src/python/myapp/BUILD
python_sources(name="lib")
python_binary(name="main", entry_point="main.py")
```

The directory name (`myapp`) is the import name. BUILD file `name` fields are Pants-internal target addresses, not Python import names.

#### What a code indexer should do for Pants repos

1. Read `pants.toml` `[source] root_patterns` (or `marker_filenames`).
2. Find all source roots by matching patterns against the directory tree.
3. For each source root, any subdirectory containing a `BUILD` file with `python_sources()` is a Python package.
4. Import name = relative path from source root to the package directory (slashes → dots for subpackages).

#### Reference

- https://www.pantsbuild.org/stable/docs/using-pants/key-concepts/source-roots

---

### 5. PDM

**Status**: No native workspace support as of early 2026. Workspace support is an open feature request (issue #1505 opened Nov 2022, still open).

#### Monorepo pattern in PDM

Like Poetry, PDM uses path dependencies. Local packages are added as:
```toml
[project]
dependencies = ["core @ file:///path/to/core"]
```
or via `pdm add ./packages/core`.

There is no `[tool.pdm.workspace]` or member discovery manifest.

#### What a code indexer should do for PDM repos

Same heuristic as Poetry:
1. Find all `pyproject.toml` files.
2. Check `[tool.pdm]` table presence for PDM-managed projects.
3. Parse `[project] dependencies` for `file://` or path-format entries pointing to sibling directories.

#### Import name determination

PDM uses `pdm-backend` as its build backend. It follows the same normalization rule: `[project] name` → lowercase + underscores. Explicit override:
```toml
[tool.pdm.build]
package-dir = "src"
```
This tells pdm-backend where to look for the package root (defaults to `.`).

#### Reference

- https://pdm-project.org/latest/
- https://github.com/pdm-project/pdm/issues/1505

---

### 6. setuptools (setup.py / setup.cfg / pyproject.toml)

**Status**: No workspace concept. Single-package tool. The most common build backend for legacy and many active projects.

#### Package discovery — three methods

**Explicit listing** (pyproject.toml):
```toml
[tool.setuptools]
packages = ["my_package", "my_package.submodule"]
```

**Automatic discovery with `find:`** (setup.cfg):
```ini
[options]
packages = find:

[options.packages.find]
where = src
include = my_package*
exclude = my_package.tests*
```

**Automatic discovery with `find_namespace:`** (setup.cfg):
```ini
[options]
packages = find_namespace:
```
`find_namespace:` recognizes directories without `__init__.py` (PEP 420 namespace packages).

**pyproject.toml equivalent**:
```toml
[tool.setuptools.packages.find]
where = ["src"]           # search root (default: ["."])
include = ["my_pkg*"]     # glob patterns matched against import names
exclude = ["my_pkg.tests*"]
namespaces = false        # set true to enable find_namespace behavior
```

Setuptools 61+ has **automatic discovery**: if neither `packages` nor `py-modules` is set, it auto-detects src-layout and flat-layout without configuration. Flat-layout auto-excludes reserved names (`test`, `tests`, `docs`, `doc`, `build`, `dist`, `venv`, etc.).

#### Package-directory mapping (non-standard layouts)

```toml
[tool.setuptools]
package-dir = {"" = "lib"}    # root package found in ./lib/
```

This maps the empty package name (root) to `lib/`, so `lib/my_package/` is importable as `my_package`.

#### setup.py equivalent

```python
from setuptools import find_packages, find_namespace_packages
setup(
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
```

#### Import name determination for setuptools

Import name = directory name as found by `find_packages()`. The `[project] name` is not directly used for import — it is the distribution name only. A project named `my-project` can expose a package named `totally_different_name/` with no required relationship to the distribution name.

The only way to reliably determine the import name for a setuptools project is:
1. Check `[tool.setuptools.packages.find] where` to know the search root.
2. Scan that root for directories containing `__init__.py` (or all directories if `namespaces = true`).
3. Cross-reference with `include`/`exclude` patterns.

#### Reference

- https://setuptools.pypa.io/en/latest/userguide/package_discovery.html
- https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html

---

### 7. Flit

**Status**: Single-package build backend. No workspace concept.

#### Import name determination

Flit is the simplest case:
1. Default: `[project] name` with hyphens → underscores. Flit searches `src/<name>/` then `./<name>/` then `./<name>.py`.
2. Override: `[tool.flit.module] name = "actual_import_name"` explicitly sets the import name independent of the distribution name.

#### Reference

- https://flit.pypa.io/en/latest/pyproject_toml.html

---

## Comparison Table

| Tool | Workspace Manifest | Discovery Field | Import Name Override |
|---|---|---|---|
| uv | `pyproject.toml` at root | `[tool.uv.workspace] members` (globs) | `[tool.uv.build-backend] module-name` |
| Poetry | None (path deps only) | `[tool.poetry.dependencies]` `path =` keys | `[tool.poetry] packages[].include` |
| Hatch (env) | `pyproject.toml` per env | `[tool.hatch.envs.<name>] workspace.members` | `[tool.hatchling.build.targets.wheel] packages` |
| Pants | `pants.toml` | `[source] root_patterns` + BUILD files | Not needed — filesystem relative path IS the import path |
| PDM | None (path deps only) | `[project] dependencies` `file://` paths | `[tool.pdm.build] package-dir` |
| setuptools | None | `[tool.setuptools.packages.find] where` | `[tool.setuptools] package-dir` |
| Flit | None | Auto-detect from `[project] name` | `[tool.flit.module] name` |

---

## Detection Heuristics for a Code Indexer

To detect which workspace format(s) a Python repo uses, check in this order:

1. **uv workspace root**: root `pyproject.toml` contains `[tool.uv.workspace]` with a `members` key.
   - Parse `members` globs, exclude `exclude` globs, each matched dir with `pyproject.toml` is a member.

2. **Pants**: `pants.toml` exists at repo root.
   - Read `[source] root_patterns`. Each source root directory contains packages.

3. **Poetry monorepo**: multiple `pyproject.toml` files where `[tool.poetry]` is present and siblings reference each other via `path =` dependencies.

4. **PDM monorepo**: same heuristic as Poetry but look for `[tool.pdm]` table.

5. **Hatch environment workspace**: `pyproject.toml` with `[tool.hatch.envs.*] workspace.members` — note this is per-environment, not a repo-wide workspace manifest.

6. **Plain pyproject.toml (single package)**: `[project]` table with `name` field but no workspace configuration. Single package; directory is a Python package root.

7. **setuptools single package**: `setup.py` or `setup.cfg` or `[tool.setuptools]` in `pyproject.toml`.

---

## Import Name Resolution Algorithm (for a code indexer)

For any given Python project directory with a `pyproject.toml`:

```
1. Determine build backend from [build-system] requires:
   - "hatchling" → use hatchling rules
   - "setuptools" → use setuptools rules
   - "flit_core" or "flit" → use flit rules
   - "pdm-backend" → use pdm-backend rules
   - "poetry-core" → use poetry rules
   - "uv" or "[tool.uv.build-backend]" present → use uv rules

2. Check for explicit import name override (backend-specific field).

3. If no override:
   a. Read [project] name (or [tool.poetry] name for Poetry-only configs).
   b. Normalize: lowercase, replace runs of [-._] with single underscore.
   c. This is the candidate import name.

4. Locate the package on disk:
   a. Check src/<candidate_name>/ — this is the src-layout path.
   b. Check ./<candidate_name>/ — this is the flat-layout path.
   c. Check src/<candidate_name>.py — single-module src-layout.
   d. Check ./<candidate_name>.py — single-module flat-layout.
   e. For setuptools: check [tool.setuptools.packages.find] where, scan that dir.

5. The first match is the package root. Everything within it is importable under
   <candidate_name>.
```

---

## Open Questions

- Does Hatch's `workspace.members` (environment-scoped) have any standardization plans for a repo-level workspace manifest, similar to uv?
- PDM issue #1505 is long-running. Has any community fork or plugin added workspace support?
- For repos using both uv workspaces AND a third-party build backend (e.g., hatchling), does uv's `module-name` override take precedence, or does the backend's own override apply?
- Setuptools auto-discovery in 61+: exactly which reserved directory names are excluded in flat-layout? The full list should be confirmed against source.

---

## Sources

- [uv workspaces docs](https://docs.astral.sh/uv/concepts/projects/workspaces/)
- [uv build backend docs](https://docs.astral.sh/uv/concepts/build-backend/)
- [src-layout vs flat-layout — PyPA](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
- [setuptools package discovery](https://setuptools.pypa.io/en/latest/userguide/package_discovery.html)
- [setuptools pyproject.toml config](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html)
- [Poetry pyproject.toml reference](https://python-poetry.org/docs/pyproject/)
- [Flit pyproject.toml reference](https://flit.pypa.io/en/latest/pyproject_toml.html)
- [Hatch workspace how-to](https://hatch.pypa.io/1.16/how-to/environment/workspace/)
- [Hatch config reference](https://hatch.pypa.io/1.9/config/hatch/)
- [Pants source roots](https://www.pantsbuild.org/stable/docs/using-pants/key-concepts/source-roots)
- [PDM configure project](https://pdm-project.org/latest/usage/config/)
- [Python name normalization spec](https://packaging.python.org/en/latest/specifications/name-normalization/)
- [Poetry monorepo discussion](https://github.com/python-poetry/poetry/issues/6850)
- [PDM workspace feature request](https://github.com/pdm-project/pdm/issues/1505)
