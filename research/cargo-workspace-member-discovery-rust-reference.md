---
title: Cargo Workspace Member Discovery and Rust Module Resolution
type: research
tags: [rust, cargo, workspace, module-resolution, crate-names, cross-crate-imports]
summary: Precise reference for implementing a workspace member discoverer in a code indexing tool, covering Cargo.toml workspace fields, member discovery algorithm, package/crate name resolution, Rust module path rules, and cross-crate import resolution.
status: active
source: quick-research
confidence: high
created: 2026-03-21
updated: 2026-03-21
---

## Summary

Cargo workspace discovery follows a deterministic three-phase algorithm: expand `members` globs, auto-collect path dependencies, filter by `exclude`. Package names use hyphens but crate names (what you write in `use` statements) always use underscores. Rust module resolution maps `crate::x::y` to `src/x/y.rs` or `src/x/y/mod.rs` with `#[path]` as an escape hatch.

---

## 1. Cargo.toml `[workspace]` Section

### `members` field

```toml
[workspace]
members = [
    "member1",            # exact path
    "path/to/member2",    # exact nested path
    "crates/*",           # glob: all direct subdirs of crates/
    "crates/**",          # NOT standard - Cargo uses glob crate, not **
]
```

- Values are **relative paths** from the workspace root directory.
- Glob expansion uses the [`glob` crate](https://docs.rs/glob/0.3.0/glob/struct.Pattern.html) (`*`, `?`, `[abc]`). No `**` recursive glob is documented as supported in `members`.
- Each expanded path must contain a `Cargo.toml` with a `[package]` section to be a valid member.

### `exclude` field

```toml
[workspace]
members = ["crates/*"]
exclude = ["crates/experimental", "path/to/other"]
```

- Takes exact paths (not globs per documentation, though implementations may vary).
- Paths matching `exclude` are silently skipped during member resolution.
- Useful for path dependencies that live inside the workspace tree but should not be members.

### `default-members` field

```toml
[workspace]
members = ["crates/foo", "crates/bar", "crates/baz"]
default-members = ["crates/foo"]
```

- Controls which packages are built/tested when running `cargo build` from the workspace root without `-p` or `--workspace`.
- Uses the same glob expansion logic as `members`.
- Must be a subset of `members` (validated at workspace construction time).
- **Default behavior when unset:**
  - Virtual workspace: all `members`
  - Non-virtual workspace: the root package only

### Virtual vs. Non-Virtual Workspaces

| Feature | Non-Virtual | Virtual |
|---|---|---|
| Root `Cargo.toml` has `[package]`? | Yes | No |
| `resolver` field | Inferred from `package.edition` | **Must be set explicitly** |
| Default build target | Root package | All members |
| Use case | Repo with one primary crate + helpers | Monorepo with no primary crate |

Non-virtual example:
```toml
[workspace]   # coexists with [package]

[package]
name = "my-app"
version = "0.1.0"
```

Virtual example:
```toml
[workspace]
members = ["crates/foo", "crates/bar"]
resolver = "3"   # required - no [package] to infer from
```

---

## 2. Member Discovery Algorithm

### Phase 1: Explicit `members` glob expansion

```
for pattern in workspace.members:
    paths = glob::glob(workspace_root / pattern)
    for path in paths:
        if (path / "Cargo.toml").exists() AND path NOT in exclude:
            add path to members
```

### Phase 2: Path dependency auto-discovery (when `members` is absent)

When `workspace.members` is not specified, Cargo calls `find_path_deps()`:

```
queue = [workspace_root]
visited = {}
while queue not empty:
    manifest_dir = queue.pop()
    read Cargo.toml at manifest_dir
    for each path dependency in [dependencies], [dev-dependencies], [build-dependencies]:
        resolved_path = manifest_dir / dep.path
        if resolved_path not in visited AND resolved_path under workspace_root:
            if resolved_path not in workspace.exclude:
                add resolved_path to members
                queue.push(resolved_path)   # recurse
            visited.add(resolved_path)
```

**Note:** Even when `members` IS specified, all path dependencies residing within the workspace directory are automatically included as members regardless of whether they appear in `members`. This is a Cargo invariant, not a user choice.

### Phase 3: Validation

Each discovered member must have:
- A `Cargo.toml` file
- A `[package]` section with at minimum a `name` field

### Workspace Root Finding (for subdirectory invocations)

Cargo walks up the directory tree from the current working directory. At each level it checks `Cargo.toml` for a `[workspace]` definition. The first workspace root found wins. This produces the key constraint:

**Nested workspaces are not supported.** A package cannot belong to multiple workspace roots. Each `Cargo.toml` can declare `package.workspace = "/path/to/ws/root"` to override the automatic upward search, but the target must be a single workspace root.

---

## 3. Package Name Resolution

### `[package] name` is the source of truth

```toml
# crates/cm-core/Cargo.toml
[package]
name = "cm-core"   # package name (used by Cargo, crates.io, [dependencies])
```

### Hyphen-to-underscore conversion

Cargo transparently converts hyphens to underscores for the **crate name** (what `rustc` sees):

| Package name (Cargo.toml) | Crate name (Rust code) |
|---|---|
| `cm-core` | `cm_core` |
| `hello-world` | `hello_world` |
| `my_lib` | `my_lib` (unchanged) |

This is controlled by the `[lib]` target: if `[lib] name` is not set, Cargo uses the package name with `-` → `_`.

Override via explicit `[lib]` section:
```toml
[lib]
name = "custom_name"   # overrides package-name-derived default
path = "src/lib.rs"
```

### Directory name vs. crate name

Directory name has no bearing on the crate name. Only `[package] name` (and optionally `[lib] name`) matters.

```
crates/cm-core/          # directory name is "cm-core"
  Cargo.toml             # [package] name = "cm-core"
  src/lib.rs             # the lib target

# In Rust code:
use cm_core::some_module;   # underscore, NOT hyphen
```

---

## 4. Rust Module Resolution Rules

### Root of a crate

- Library crate root: `src/lib.rs` (default), overridable via `[lib] path`
- Binary crate root: `src/main.rs` (default), or `src/bin/<name>.rs`

### `mod` declaration resolution

Given `mod foo;` in a source file:

| Source file | `mod foo;` resolves to |
|---|---|
| `src/lib.rs` (mod-rs style) | `src/foo.rs` OR `src/foo/mod.rs` |
| `src/bar.rs` (non-mod-rs) | `src/bar/foo.rs` OR `src/bar/foo/mod.rs` |
| `src/bar/mod.rs` (mod-rs style) | `src/bar/foo.rs` OR `src/bar/foo/mod.rs` |

**Rule:** A "mod-rs file" (any file named `mod.rs`, `lib.rs`, or `main.rs`) anchors submodule resolution to its directory. A non-mod-rs file (e.g., `bar.rs`) creates a virtual directory named `bar/` for its children.

**Cannot mix** `foo.rs` and `foo/mod.rs` for the same module — that is a compile error.

### Path semantics

| Rust path | Meaning |
|---|---|
| `crate::x::y` | Absolute path from crate root |
| `super::x` | Parent module's child `x` |
| `self::x` | Current module's child `x` |
| `::std::...` | External crate (global namespace) |

`crate::x::y` resolves as:
```
src/x.rs or src/x/mod.rs     → defines module x
src/x/y.rs or src/x/y/mod.rs → defines module y within x
```

### `#[path]` attribute

Overrides the default file-system lookup. Path is relative to the current source file's directory.

```rust
#[path = "platform/unix.rs"]
mod platform;
```

For modules inside inline blocks (`mod foo { ... }`), resolution depends on whether the containing file is mod-rs or not:

- **In mod-rs file** (`lib.rs`, `main.rs`, `mod.rs`): path is relative to that file's directory, treating inline module names as subdirectories.
- **In non-mod-rs file** (`bar.rs`): same as above, but the file's name creates an implicit directory prefix.

```rust
// src/a/b.rs (non-mod-rs)
mod inline {
    #[path = "other.rs"]
    mod inner;  // resolves to src/a/b/inline/other.rs
}
```

### Edition differences

The file-naming convention (`foo.rs` vs `foo/mod.rs`) has been available since Rust 1.30 and is consistent across editions 2015, 2018, 2021, and 2024. The `mod.rs` style is legacy but still valid. The only edition-relevant module change was path imports (`use` in 2018+ does not require `extern crate`), not file resolution.

---

## 5. Cross-Crate Imports

### Resolving `use other_crate::thing`

1. `other_crate` (with hyphens converted to underscores) is looked up in the current package's `[dependencies]` (or `[dev-dependencies]`/`[build-dependencies]`).
2. The dependency entry provides either:
   - A registry version (crates.io or other registry)
   - A `path = "..."` pointing to a local directory
   - A `git` URL

### Path dependencies in workspace context

```toml
# In crates/my-app/Cargo.toml
[dependencies]
cm-core = { path = "../cm-core" }
```

The `path` is relative to the **consuming crate's** `Cargo.toml` directory, not the workspace root.

To resolve `use cm_core::foo` to a workspace member directory:
1. Look up the dependency by name (`cm-core`) in `[dependencies]`.
2. Read the `path` value (`"../cm-core"`).
3. Resolve relative to the consuming crate's directory: `crates/my-app/../cm-core` → `crates/cm-core`.
4. That directory contains the member crate's `src/lib.rs`, which is the module resolution root.

### Renamed dependencies (`package` key)

```toml
[dependencies]
my_alias = { path = "../some-lib", package = "some-lib" }
# OR for registry:
my_alias = { version = "1.0", package = "actual-crate-name" }
```

- `package` = the actual crate name (as in the dependency's `[package] name`).
- The key (`my_alias`) = what you write in `use my_alias::...` Rust code.
- Cargo still does the hyphen → underscore conversion on the key: `my-alias` in Cargo.toml becomes `my_alias` in Rust.

**For a code indexer:** when resolving `use foo::bar`, the lookup key is `foo` (as underscored identifier), which must be matched against the **key names** (not `package` values) in `[dependencies]`, after applying underscore normalization.

### Workspace dependency inheritance

```toml
# Workspace root Cargo.toml
[workspace.dependencies]
cm-core = { path = "crates/cm-core", version = "0.1.0" }

# Member Cargo.toml
[dependencies]
cm-core.workspace = true
```

When resolving a `workspace = true` dependency, look up the dep by name in `[workspace.dependencies]` in the workspace root, then follow that entry's `path` (relative to **workspace root**).

---

## Resolution Algorithm for a Code Indexer

### Step 1: Build workspace member map

```
ws_root = find workspace root (walk up to Cargo.toml with [workspace])
members = {}

for pattern in workspace.members:
    for dir in glob(ws_root / pattern):
        if (dir / "Cargo.toml").exists():
            manifest = parse(dir / "Cargo.toml")
            pkg_name = manifest.package.name
            crate_name = pkg_name.replace("-", "_")
            lib_name = manifest.lib.name ?? crate_name
            lib_path = manifest.lib.path ?? (dir / "src/lib.rs")
            members[crate_name] = {
                dir: dir,
                pkg_name: pkg_name,
                lib_root: lib_path,
            }
```

### Step 2: Resolve `use <crate>::<path>` to source file

```
fn resolve_use(consuming_manifest_dir, crate_ident, module_path):
    // 1. Find the dependency entry
    manifest = parse(consuming_manifest_dir / "Cargo.toml")
    dep_key = crate_ident.replace("_", "-") OR crate_ident  // try both
    dep = manifest.dependencies[dep_key]
    if dep is None:
        dep = manifest.dependencies.find_by(underscore_normalize(key) == crate_ident)

    // 2. Get the actual package name (handle 'package' rename)
    actual_pkg = dep.package ?? dep_key
    actual_crate = actual_pkg.replace("-", "_")

    // 3. Find the workspace member
    member = members[actual_crate]

    // 4. Resolve module path within member
    return resolve_module_path(member.lib_root, module_path)

fn resolve_module_path(lib_root, segments):
    // segments = ["x", "y"] for crate::x::y
    current_dir = lib_root.parent()   // e.g., src/
    for (i, seg) in segments.enumerate():
        // Try file-as-module first (modern style)
        candidate_file = current_dir / (seg + ".rs")
        candidate_mod  = current_dir / seg / "mod.rs"
        if candidate_file.exists():
            if i == segments.len() - 1: return candidate_file
            current_dir = current_dir / seg   // descend for next segment
        elif candidate_mod.exists():
            if i == segments.len() - 1: return candidate_mod
            current_dir = current_dir / seg
        else:
            return None  // not found; may be inline module or #[path]
```

---

## Sources

- [Cargo Workspaces Reference](https://doc.rust-lang.org/cargo/reference/workspaces.html)
- [Cargo Specifying Dependencies](https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html)
- [Cargo Targets Reference](https://doc.rust-lang.org/cargo/reference/cargo-targets.html)
- [Cargo Manifest Reference](https://doc.rust-lang.org/cargo/reference/manifest.html)
- [Rust Reference: Modules](https://doc.rust-lang.org/reference/items/modules.html)
- [DeepWiki: Cargo Workspaces Implementation](https://deepwiki.com/rust-lang/cargo/2.2-workspaces)
- [RFC 940: Hyphens Considered Harmful](https://rust-lang.github.io/rfcs/0940-hyphens-considered-harmful.html)
- [GitHub Issue: Nested Workspaces](https://github.com/rust-lang/cargo/issues/5042)

---

## Open Questions

- Does `glob::glob` in Cargo's `members` support `**` (recursive) patterns? The docs only show `*`. Worth verifying against Cargo source.
- `#[path]` combined with `cfg` attributes creates conditional module resolution that no static indexer can fully resolve without evaluating feature flags and cfg conditions.
- Proc-macro crates declare `crate-type = ["proc-macro"]` in `[lib]` — they are workspace members but their resolution as imports is different (they export derive macros, not modules). An indexer needs to handle this case separately.
- `[patch]` and `[replace]` in workspace manifests can redirect a dependency to a different path — an advanced case for dependency resolution.
