---
title: fmm tool surface road-test
date: 2026-05-22
workspace: runtime-matters
head: 70f7ed6
indexed: 132 files / 18,731 LOC (Rust)
tester: claude-code (opus-4-7)
---

# fmm tool surface road-test

Exercised every `fmm_*` MCP tool exposed by `helioy-tools:fmm` against the
`runtime-matters` workspace. The goal was to surface sharp edges, schema/UX
inconsistencies, and bugs across the surface, not to evaluate any specific
feature in depth.

## Scope

Tools exercised:

- `fmm_read_symbol`
- `fmm_lookup_export`
- `fmm_list_exports`
- `fmm_list_files`
- `fmm_file_outline`
- `fmm_search`
- `fmm_glossary`
- `fmm_dependency_graph`
- `fmm_dependency_cycles`

For each tool: nominal inputs, edge inputs, error inputs, and at least one
combination with a sibling tool.

---

## Tools that mostly work cleanly

### `fmm_file_outline`

Best tool in the suite. Returns YAML with `lines`, `size`, `signature`,
`visibility`, `kind`, and member breakdown. Excellent first-touch for any
file. `include_private: true` correctly surfaces non-exported top-level
declarations and trait impls inline.

### `fmm_lookup_export`

Exact lookup plus an ambiguity affordance: on collisions it returns one
candidate and a `⚠ N additional definition(s) found` annotation pointing to
`fmm_glossary`. Returns sibling `impl Foo` ranges alongside the struct
declaration, which saves a follow-up call.

### `fmm_list_exports`

Substring vs regex auto-detection works: `spawn` is treated as substring,
`^Server` and `Request$` activate regex mode. `directory:` scope filter is
clean. Invalid regex returns a clear parse error including the offending
position.

### `fmm_search`

Four labeled sections (EXPORTS / FILES / IMPORTS / NAMED IMPORTS) is a great
affordance for a universal-search tool. `min_loc` / `max_loc` combinators
work and compose with other filters. `term:` and `imports:` both useful.

---

## Findings worth filing

### 1. HIGH — `fmm_file_outline` truncation hint references a nonexistent param

Truncated output ends with:

```
[Truncated — showing 378/443 lines. Use truncate: false to get the full source.]
```

But the `fmm_file_outline` schema has **no `truncate` parameter**. Users
copying the suggestion will get an `InputValidationError`. Either add the
parameter or change the hint to point at a real escape hatch (e.g.
"narrow to a single symbol with `fmm_read_symbol`" or
"set `include_private: false`").

**Reproduction:** call `fmm_file_outline(file: "crates/rtm-daemon/src/reconcile.rs", include_private: true)`.

### 2. HIGH — Rust intra-crate dependency edges are incomplete

`fmm_dependency_graph` on `crates/rtm-core/src/proto.rs` returned:

```yaml
external: [admin, capture, chrono, cli_output, error, isolation, launcher,
           mcp, proto, serde, spawn_context, std, tokio, types, uuid, version]
```

The `external` list mixes **internal crate modules** (`admin`, `capture`,
`error`, `mcp`, `proto`, `types`, `version`) with actual external crates
(`chrono`, `serde`, `std`, `tokio`, `uuid`). The parser appears to treat
`use crate::admin::X` and `use chrono::X` identically.

Downstream symptoms:

- `fmm_search(depends_on: "crates/rtm-core/src/proto.rs")` reports
  `0 files depend on ... (transitive)`. This is wrong: both `rtm-daemon` and
  `rtm-cli` consume `proto::*`.
- `fmm_dependency_graph(file: proto.rs, depth: -1)` returns empty.
- `fmm_dependency_cycles` returned an empty cycle list for every variation
  tried (runtime, all, scoped to a specific file). Could be genuine, but
  given the broken edges above, more likely the Rust mod graph is too sparse
  to detect SCCs.

By contrast, `fmm_dependency_graph` on `crates/rtm-daemon/src/server/state.rs`
*did* populate `local_deps` correctly. So the resolver works for direct
single-file imports but breaks when a path is reached through a
`mod foo; pub use foo::*;` re-export chain. That inconsistency is itself a
bug — users cannot tell from the tool's output whether `0 dependents` means
"truly zero" or "the resolver couldn't follow the edges."

Blast-radius analysis on Rust files is unreliable until this is fixed.

### 3. MED — `fmm_list_files` `pattern` does not behave like a shell glob

`pattern: "*preflight*"` on `crates/rtm-daemon/src/` returned 0 files.

But `fmm_search(term: "spawn_preflight")` confirms two files exist:

```
crates/rtm-daemon/src/spawn_preflight.rs
crates/rtm-daemon/src/spawn_preflight/tests.rs
```

Docs say: "Glob pattern to filter by filename (e.g. `*.py`, `*.rs`,
`test_*`)" — which implies shell-glob semantics. Either the matcher only
handles certain glob shapes (trailing `*` only?) or it's anchored against
something other than the basename. Either way, fix the docs or fix the
matcher.

### 4. MED — `Type.field` is silently conflated with `Type.method`

Observed across multiple tools:

- `fmm_read_symbol(name: "ServerState.spawn")` returns the **field
  declaration** (`spawn: SpawnCoordinator,` at line 31) with no `kind`
  annotation distinguishing field from method.
- `fmm_glossary(pattern: "ServerState.spawn")` returns `(no external source
  callers)` — technically correct under named-import semantics, but
  misleading: it suggests "this method exists but is unused" when the truth
  is "this is a field, not a method."
- `fmm_file_outline` correctly tags `kind: field` vs `kind: method`. The
  other tools should adopt the same discrimination so dotted-name callers
  know what they're looking at.

### 5. LOW — `Type::method` (Rust syntax) error message is misleading

```
fmm_read_symbol(name: "ServerState::new")
  → ERROR: Ambiguous name 'ServerState::new'. For file:symbol notation, the
    file path must contain '/' or '.' (e.g. 'src/helpers.ts:myFn').
```

The user wasn't using file:symbol notation; they used Rust's `::` path
syntax. The tool should detect `::` specifically and suggest the supported
`Type.method` dotted form.

### 6. LOW — Bare module name resolves to `mod foo;` declaration

`fmm_read_symbol(name: "reconcile")` returned `mod reconcile;` at
`lib.rs:10`. Technically valid (module declarations are exports) but low
signal: the user almost certainly wants the module's contents. Either tag
it `kind: module_decl` or auto-follow to the single backing file when one
exists.

### 7. LOW — File-path-as-name strips `.rs` as a method extension

`fmm_read_symbol(name: "crates/rtm-cli/src/cli/spawn.rs")` →
`ERROR: Method 'crates/rtm-cli/src/cli/spawn.rs' not found. Class
'crates/rtm-cli/src/cli/spawn' is not a known export.`

The `.rs` was parsed as a `Class.method` extension. Minor, but the message
implies the user was trying to call a method on a class — they were just
typo'ing a file path. Could short-circuit when input ends in a known source
extension.

### 8. NOTE — `fmm_glossary` fuzzy fallback can surprise

`pattern: "LifecycleStore.insert"` matched `LifecycleStore.insert_forking`.
Reasonable fuzzy aid, but worth documenting that dotted patterns also
accept prefix-fuzzy matching, not just exact match. Currently the docs
only describe Layer 2 / Layer 3 semantics, not the substring fallback.

### 9. NOTE — Rust `#[cfg(test)] mod tests` not detected by `filter: tests`

`fmm_list_files(directory: "crates/rtm-daemon/src/", filter: "tests")`
returned 0 files, despite virtually every source file in that tree having
a `#[cfg(test)] mod tests` block at the bottom. Reasonable scope limit
(the filter is path-based per the docs), but worth a Rust-specific docs
note — Rust users will be confused when the filter "misses" their unit
tests.

---

## Summary by severity

| # | Severity | Tool                       | Issue                                                                  |
|---|----------|----------------------------|------------------------------------------------------------------------|
| 1 | HIGH     | `fmm_file_outline`         | Truncation hint references nonexistent `truncate` param                |
| 2 | HIGH     | `fmm_dependency_graph` / `_cycles` / `_search depends_on` | Rust intra-crate edges through `mod`/`pub use` chains are not followed; internal modules appear in `external` list |
| 3 | MED      | `fmm_list_files`           | `pattern` does not behave like shell glob                              |
| 4 | MED      | `fmm_read_symbol`, `fmm_glossary` | `Type.field` silently conflated with `Type.method`, no `kind` flag |
| 5 | LOW      | `fmm_read_symbol`          | `Type::method` (Rust syntax) error message is wrong                    |
| 6 | LOW      | `fmm_read_symbol`          | Bare module name resolves to `mod foo;` declaration, not contents      |
| 7 | LOW      | `fmm_read_symbol`          | File-path-as-name parses `.rs` as a method extension                   |
| 8 | NOTE     | `fmm_glossary`             | Dotted-pattern fuzzy fallback undocumented                             |
| 9 | NOTE     | `fmm_list_files`           | `filter: tests` misses Rust `#[cfg(test)]` modules                     |

## Recommended next steps

1. Fix the `fmm_file_outline` truncation hint (1) — trivial, high-visibility.
2. Triage the Rust dependency-graph completeness gap (2) — the most
   load-bearing issue for impact analysis on Rust codebases. Until fixed,
   `depends_on` and `_cycles` should carry a "results may be incomplete for
   Rust" caveat.
3. Either harmonise the `pattern` matcher to real shell glob (3) or rewrite
   the docs and add `pattern_examples_that_dont_work`.
4. Add a `kind` field to dotted-name results in `fmm_read_symbol` and
   `fmm_glossary` (4) so `Type.field` lookups don't masquerade as method
   lookups.
5. Tighten parser error messages on `::` (5) and `.rs` (7) — both are 5-line
   fixes that meaningfully improve discoverability.
