---
title: Go Workspace and Module Import Resolution Reference
type: research
tags: [go, modules, workspace, go.work, go.mod, import-resolution, indexing]
summary: Precise reference for go.work/go.mod file formats and the exact algorithms for resolving Go import paths to filesystem directories, including workspace-mode cross-module resolution.
status: active
source: quick-research
confidence: high
created: 2026-03-21
updated: 2026-03-21
---

## Summary

Go import resolution is a two-phase operation: (1) map an import path to a module using longest-prefix matching against the build list, (2) strip the module path prefix from the import path and treat the remainder as a relative directory path within the module root. In workspace mode (go.work), local modules registered via `use` directives become primary candidates before external module lookup.

---

## Details

### 1. go.work File Format (Go 1.18+)

A UTF-8, line-oriented text file placed at the workspace root. Blocks of adjacent same-keyword lines can be parenthesized.

```
go 1.23.0

toolchain go1.21.0   // optional

use ./my/first/thing
use (
    ./my/second/thing
    ../sibling-module
)

replace example.com/bad v1.4.5 => example.com/good v1.4.5
replace example.com/local => ./local/override
```

**`use` directive**

- Registers a directory as a workspace module (a "main module" for MVS purposes).
- The path is **relative to the go.work file's directory**, or absolute.
- Does NOT recurse — subdirectories with their own `go.mod` must each have their own `use` entry.
- The module path identity comes from the `module` line in that directory's `go.mod`.

**`replace` directive in go.work**

- Syntax identical to `go.mod` replace (see below).
- A wildcard replace (`module/path =>`) in `go.work` overrides any version-specific replace in any workspace module's `go.mod`.
- Priority: go.work replace > go.mod replace.

**Discovery algorithm for go.work**

```
if GOWORK == "off"  → single-module mode
if GOWORK == <path> → use that file
if GOWORK unset     → walk CWD → parent → parent... until go.work found
                      if none found → single module containing CWD
```

Check active workspace: `go env GOWORK`

---

### 2. go.mod File Format

UTF-8, line-oriented. Must contain exactly one `module` directive.

```
module github.com/user/project

go 1.23.0

require (
    golang.org/x/net  v0.20.0
    github.com/foo/bar v2.1.0+incompatible
    github.com/baz/qux v1.5.0  // indirect
)

replace github.com/baz/qux v1.5.0 => ./local/qux
replace github.com/baz/qux        => ../other-qux
```

**`module` directive**

Declares the module's canonical import path prefix. All packages within this module have import paths of the form `<module-path>/<relative-dir>`.

**`require` directive**

- Declares minimum required version (Minimum Version Selection).
- `// indirect` = no package from that module is directly imported by the main module (but is needed transitively). At go 1.17+ all transitive deps appear here.

**`replace` directive**

```
ModulePath [Version] => FilePath           // local disk replacement
ModulePath [Version] => ModulePath Version // different remote module
```

- If version omitted on left: replaces all versions.
- Local paths must start with `./` or `../`.
- `replace` in go.mod only takes effect when that module is the **main module** (i.e., the one being built directly). Replace directives in dependencies are ignored.

**go.mod discovery**

Walk CWD upward through parent directories until `go.mod` found. That directory is the module root.

---

### 3. Import Resolution Algorithm

Given `import "github.com/user/project/internal/handler"`:

#### Phase 1: Map import path to a module

Build the **build list** (all modules in the transitive dependency graph). For workspace mode, the build list includes all `use`-registered modules as roots.

Find the module whose path is the **longest prefix** of the import path:

```
"github.com/user/project/internal/handler"
  → try: "github.com/user/project/internal/handler"  (no such module)
  → try: "github.com/user/project/internal"           (no such module)
  → try: "github.com/user/project"                    ✓ found in build list
```

Validation: the matched module must contain at least one `.go` file in the corresponding subdirectory. Build constraints (GOOS/GOARCH) are NOT applied for this check.

Exactly one module must match. Zero or two+ = error.

#### Phase 2: Map module path to filesystem directory

```
module root dir = directory containing go.mod
relative subpath = import_path[len(module_path)+1:]   // strip prefix + slash

package dir = module_root / relative_subpath
```

Example:
```
module path:   github.com/user/project        (go.mod in /home/dev/project/)
import path:   github.com/user/project/internal/handler
relative path: internal/handler
resolved dir:  /home/dev/project/internal/handler
```

The package is all `.go` files in that directory (excluding `_test.go` for production builds).

#### Standard library

Import paths with no dot in the first path element are stdlib:
```
"fmt", "net/http", "os/exec"  → $GOROOT/src/<path>
```

No module lookup is performed for stdlib packages.

#### Workspace cross-module resolution

When go.work is present:

1. Collect all modules from `use` directives (each has its own module path from its go.mod).
2. Treat these as main modules in MVS.
3. When resolving an import, check `use`-registered local modules first.
4. If the import path prefix matches a `use` module's declared path, resolve directly to the local directory — no network fetch.

Example:
```
go.work:
  use ./moduleA    # module path: example.com/moduleA, dir: /ws/moduleA
  use ./moduleB    # module path: example.com/moduleB, dir: /ws/moduleB

import "example.com/moduleA/pkg/foo"
  → module "example.com/moduleA" is a workspace module
  → module root = /ws/moduleA
  → package dir = /ws/moduleA/pkg/foo
```

If an import matches a workspace module's path, that workspace module wins even if an external module with the same path exists.

---

### 4. `internal/` Package Visibility

The rule: a package at `a/b/c/internal/d/e/f` can only be imported by code in the directory tree rooted at `a/b/c`.

```
mymod/
├── go.mod          # module example.com/mymod
├── cmd/
│   └── main.go     # CAN import example.com/mymod/internal/...
└── internal/
    └── config/
        └── config.go
```

An external module importing `example.com/mymod/internal/config` will get a compile error.

The boundary is the parent directory of the `internal` component. Any `internal` anywhere in the path triggers this restriction.

---

### 5. Package Name vs. Directory Name

**The import path always maps to a directory. The package name is declared inside source files.**

They do not have to match. Convention strongly recommends they do.

```go
// File: /ws/mymod/transport/http.go
package httpx   // package name: httpx, directory: transport
```

Callers import via the directory path:
```go
import "example.com/mymod/transport"  // import path uses directory name
// but refer to symbols as:
httpx.NewServer()                      // package name from source
```

**How to determine a directory's package name reliably:**

Read the `package` clause from any non-test `.go` file in the directory. All non-test `.go` files in one directory MUST declare the same package name (exception: `_test.go` files may use `pkgname_test`).

Do not derive the package name from the directory name. Parse the source.

**Exceptions with consistent package names:**

| Pattern | Example | Notes |
|---|---|---|
| `main` | `cmd/server/main.go` | Executable; import path irrelevant to callers |
| `foo_test` | `handler_test.go` in `handler/` | External test package, compiled separately |
| `doc` packages | `doc.go` with `package pkg` | Sometimes the dir is named differently |

---

### 6. Multi-file Packages

All `.go` files in a directory belong to the same package (they share the same `package` declaration). Exception: files ending in `_test.go` may use either the package name or `<pkgname>_test`.

`_test.go` semantics:
- Excluded from normal builds; included only when `go test` runs.
- If `package foo_test`: compiled as a separate external test binary, imports `foo` as any external package would.
- If `package foo`: compiled together with the package (white-box tests).
- For indexing purposes: treat `_test.go` files as belonging to the package but conditionally excluded from non-test analysis.

---

### 7. Resolution Algorithm Summary (for a code indexer)

```
function resolve_import(import_path, workspace_root):

  // 1. Stdlib check
  if not "." in first_path_element(import_path):
    return GOROOT + "/src/" + import_path

  // 2. Load workspace modules (if go.work present)
  workspace_modules = []
  if go_work = find_go_work(workspace_root):
    for each "use" dir in go_work:
      mod_path = read_module_directive(dir + "/go.mod")
      workspace_modules.append({path: mod_path, root: abs(dir)})

  // 3. Longest-prefix match against workspace modules
  best = longest_prefix_match(import_path, workspace_modules)
  if best:
    rel = import_path[len(best.path)+1:]
    return best.root + "/" + rel

  // 4. Longest-prefix match against go.mod requires + replaces
  // (for each required module: check if replace points to local path)
  for mod in build_list(main_go_mod):
    if is_prefix(mod.path, import_path):
      if mod has local replace:
        rel = import_path[len(mod.path)+1:]
        return replace_local_path + "/" + rel
      else:
        return module_cache_path(mod) + "/" + rel

  // 5. Not found locally → requires network fetch
  return EXTERNAL
```

**Package name lookup** (after resolving directory):
```
function package_name(dir):
  for file in dir/*.go where not ends_with("_test.go"):
    parse package clause → return first found name
  return null  // no Go files = not a package
```

---

## Sources

- [Go Modules Reference (go.mod)](https://go.dev/ref/mod)
- [Go Modules Reference: Workspaces section](https://go.dev/ref/mod#workspaces)
- [Package Names blog post](https://go.dev/blog/package-names)
- [How to Write Go Code](https://go.dev/doc/code)
- [Go Language Spec: Import declarations](https://go.dev/ref/spec#Import_declarations)
- [internal package visibility docs](https://pkg.go.dev/cmd/go#hdr-Internal_Directories)
- [Go Wiki: Modules](https://go.dev/wiki/Modules)

## Open Questions

- Symlink handling: the go command documentation does not explicitly describe behavior when `use` paths or module roots involve symlinks. Worth testing empirically.
- `vendor/` directories: when a module uses `go mod vendor`, package resolution for dependencies uses `vendor/` instead of module cache. A full indexer may need to handle this path.
- Build tag filtering: the resolution algorithm above does not apply build constraints. A complete indexer needs a second pass to filter files by GOOS/GOARCH/build tags.
