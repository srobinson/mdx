---
title: Refactoring Decomposition Proposal for Large Files in fmm
type: research
tags: [fmm, refactoring, architecture, rust, code-quality]
summary: Concrete decomposition proposals for all 9 fmm source files exceeding 600 LOC, with line-range analysis and migration risk assessment.
status: active
source: codebase-analyst
confidence: high
created: 2026-03-16
updated: 2026-03-16
---

## Executive Summary

fmm has 9 source files exceeding 600 lines (10,380 LOC total), plus 4 test files exceeding 600 lines (8,119 LOC). The source files follow a consistent pattern: production logic + inline `#[cfg(test)] mod tests` in the same file. The largest offender is `typescript.rs` at 2,011 LOC, followed by `rust.rs` at 1,694 LOC. All parser files share the same internal structure (constructor with query compilation, extraction methods, `impl Parser` trait, inline tests), making them candidates for a uniform decomposition strategy.

This document covers source files only. Test-only files (`tests/cross_language_validation.rs`, `src/mcp/tests.rs`, `tests/fixture_validation.rs`, `tests/mcp_tools.rs`, `tests/edge_cases.rs`, `tests/glossary.rs`) are excluded. They are large but they are tests; splitting them has lower architectural value and can be done independently.

## Files Exceeding 600 Lines

| # | File | LOC | Tests LOC | Production LOC |
|---|------|-----|-----------|----------------|
| 1 | `src/parser/builtin/typescript.rs` | 2,011 | ~1,108 (L903-2011) | ~903 |
| 2 | `src/parser/builtin/rust.rs` | 1,694 | ~717 (L977-1694) | ~977 |
| 3 | `src/search.rs` | 1,614 | ~993 (L621-1614) | ~621 |
| 4 | `src/cli/mod.rs` | 985 | 0 | 985 |
| 5 | `src/db/writer.rs` | 909 | ~397 (L512-909) | ~512 |
| 6 | `src/parser/builtin/python.rs` | 898 | ~416 (L482-898) | ~482 |
| 7 | `src/manifest/private_members.rs` | 825 | ~301 (L524-825) | ~524 |
| 8 | `src/cli/search.rs` | 744 | ~345 (L399-744) | ~399 |
| 9 | `src/format/yaml_formatters.rs` | 700 | ~261 (L440-700) | ~439 |

Key observation: inline tests account for 40-60% of most files. Extracting tests alone would bring 6 of 9 files under the 600-line threshold.

---

## Proposal 1: `src/parser/builtin/typescript.rs` (2,011 LOC)

**Priority: High.** Largest file. Clear concern boundaries.

### Concern Groups

| Group | Lines | LOC | Description |
|-------|-------|-----|-------------|
| tsconfig resolution | 11-139 | 129 | `load_tsconfig_paths`, `read_tsconfig_paths`, `strip_json_comments`, `resolve_alias` |
| Struct + constructor | 141-278 | 138 | `TypeScriptParser` struct, `new()`, `new_tsx()`, `build()` with query compilation |
| Export extraction | 280-306 | 27 | `extract_exports` |
| Import extraction | 308-390 | 83 | `extract_imports`, `extract_dependencies` |
| Class method extraction | 392-493 | 102 | `extract_class_methods`, `extract_method_entry` |
| Named import extraction | 495-611 | 117 | `extract_named_imports` (named imports, re-exports, namespace imports) |
| Decorator extraction | 613-635 | 23 | `extract_decorators` |
| Nested symbol extraction | 638-780 | 143 | `extract_nested_symbols`, `is_non_trivial_declarator` (ALP-922) |
| Parser trait impl | 782-821 | 40 | `impl Parser for TypeScriptParser` |
| Parse orchestration | 823-901 | 79 | `parse_with_aliases` combining all extractors |
| Tests | 903-2011 | 1,108 | 50+ unit tests |

### Proposed Modules

```
src/parser/builtin/
  typescript/
    mod.rs              (~220 LOC) - TypeScriptParser struct, constructors, Parser trait impl, parse_with_aliases
    tsconfig.rs         (~130 LOC) - load_tsconfig_paths, read_tsconfig_paths, strip_json_comments, resolve_alias
    extract_exports.rs  (~30 LOC)  - extract_exports
    extract_imports.rs  (~200 LOC) - extract_imports, extract_dependencies, extract_named_imports
    extract_classes.rs  (~125 LOC) - extract_class_methods, extract_method_entry, extract_nested_symbols, is_non_trivial_declarator
    extract_decorators.rs (~25 LOC) - extract_decorators
    tests.rs            (~1,108 LOC) - all tests (can stay large; it is test code)
```

**Alternative (simpler, fewer files):**

```
src/parser/builtin/
  typescript/
    mod.rs              (~300 LOC) - struct, constructors, Parser impl, parse_with_aliases, extract_exports, extract_decorators
    tsconfig.rs         (~130 LOC) - path alias resolution
    extractors.rs       (~445 LOC) - extract_imports, extract_dependencies, extract_named_imports, extract_class_methods, extract_nested_symbols
    tests.rs            (~1,108 LOC) - all tests
```

### Shared Extractions

None required. All extraction methods are `impl TypeScriptParser` methods operating on `&self` and tree-sitter nodes. The struct itself stays in `mod.rs` and methods can be implemented on it from other files within the same module. The query fields are `pub(super)` accessible.

### Migration Risk: **Low**

All extraction methods take `&self` plus `source: &str` and `root_node: tree_sitter::Node`. No cross-file coupling beyond `crate::parser::{ExportEntry, Metadata, ParseResult, Parser}` and `super::query_helpers`. The `tsconfig.rs` functions are pure (no `&self`) and trivially extractable.

---

## Proposal 2: `src/parser/builtin/rust.rs` (1,694 LOC)

**Priority: High.** Same structural pattern as TypeScript parser.

### Concern Groups

| Group | Lines | LOC | Description |
|-------|-------|-----|-------------|
| Dep path normalization | 9-48 | 40 | `rust_use_path_to_dep` (free function) |
| Struct + constructor | 50-143 | 94 | `RustParser` struct, `new()` with query compilation |
| Export extraction | 145-220 | 76 | `extract_exports` |
| Impl method extraction | 222-308 | 87 | `impl_type_name`, `extract_impl_methods` (ALP-770) |
| Import extraction | 310-342 | 33 | `extract_imports`, `is_local_path` |
| Dependency extraction | 344-462 | 119 | `extract_dependencies`, `use_declaration_deps`, `extract_use_roots`, `use_declaration_root`, `leftmost_path_leaf` |
| Metadata extractors | 464-596 | 133 | `count_unsafe_blocks`, `extract_trait_impls`, `extract_lifetimes`, `count_async_functions`, `extract_derives` |
| Macro export extraction | 598-748 | 151 | `extract_macro_exports`, `attrs_contain`, `attr_item_has_name`, `check_proc_macro_attr`, `extract_first_token_in_attr`, `extract_pub_use_names`, `collect_use_names` |
| Parse orchestration | 848-957 | 110 | `parse_inner`, `is_binary_entry_point`, `impl Parser for RustParser` |
| Tests | 977-1694 | 717 | Unit tests |

### Proposed Modules

```
src/parser/builtin/
  rust/
    mod.rs              (~245 LOC) - RustParser struct, constructor, Parser impl, parse_inner, rust_use_path_to_dep
    extract_imports.rs   (~152 LOC) - extract_imports, extract_dependencies, use_declaration_deps, extract_use_roots, use_declaration_root, leftmost_path_leaf, is_local_path
    extract_exports.rs   (~314 LOC) - extract_exports, extract_impl_methods, impl_type_name, extract_macro_exports, extract_pub_use_names, collect_use_names, attrs_contain, attr_item_has_name, check_proc_macro_attr, extract_first_token_in_attr
    metadata.rs          (~133 LOC) - count_unsafe_blocks, extract_trait_impls, extract_lifetimes, count_async_functions, extract_derives
    tests.rs             (~717 LOC) - all tests
```

### Shared Extractions

`extract_field_text` is already in `super::query_helpers`. No new shared types needed.

### Migration Risk: **Low**

Same pattern as TypeScript. All methods are `impl RustParser` with no cross-file state.

---

## Proposal 3: `src/search.rs` (1,614 LOC)

**Priority: Medium.** The production code is ~621 LOC (just above threshold), but tests are ~993 LOC.

### Concern Groups

| Group | Lines | LOC | Description |
|-------|-------|-----|-------------|
| Types | 18-77 | 60 | `ExportHit`, `ImportHit`, `NamedImportHit`, `BareSearchResult`, `FileSearchResult`, `ExportHitCompact`, `SearchFilters`, `DEFAULT_SEARCH_LIMIT` |
| Bare search | 81-254 | 174 | `bare_search`, `export_match_score` |
| Filter search | 261-378 | 118 | `filter_search`, `find_export_matches` |
| Dependency graph | 385-562 | 178 | `dependency_graph`, `dependency_graph_transitive` |
| Helpers | 564-619 | 56 | `dep_targets_file`, `export_hit_from_location`, `file_entry_to_result` |
| Tests | 621-1614 | 993 | Extensive test suite |

### Proposed Modules

```
src/search/
  mod.rs                (~60 LOC)  - types, re-exports, DEFAULT_SEARCH_LIMIT
  bare_search.rs        (~174 LOC) - bare_search, export_match_score
  filter_search.rs      (~118 LOC) - filter_search, find_export_matches
  dependency_graph.rs   (~178 LOC) - dependency_graph, dependency_graph_transitive
  helpers.rs            (~56 LOC)  - dep_targets_file, export_hit_from_location, file_entry_to_result
  tests.rs              (~993 LOC) - all tests
```

### Shared Extractions

The types in `mod.rs` (`ExportHit`, `SearchFilters`, etc.) are consumed by all sub-modules. They naturally belong in `mod.rs` and would be re-exported.

### Migration Risk: **Medium**

`search.rs` has 14 exports and 1 downstream dependent (`src/cli/search.rs`). The public API surface is well-defined, but changing from a flat file to a directory module requires updating `mod.rs` re-exports to maintain backward compatibility for all callers. The `bare_search` and `filter_search` functions both use the helper functions, so `helpers.rs` needs to be `pub(crate)` visible.

---

## Proposal 4: `src/cli/mod.rs` (985 LOC)

**Priority: Medium.** The file is 985 LOC but 574 of those are the `Commands` enum definition (L58-631), which is largely declarative (clap derive macros with help text). The remaining ~411 LOC is utility functions.

### Concern Groups

| Group | Lines | LOC | Description |
|-------|-------|-----|-------------|
| Imports + Cli struct | 1-55 | 55 | Imports, `Cli` struct with global args |
| Commands enum | 58-631 | 574 | `Commands` enum with 15+ variants, each decorated with clap attributes and help text |
| Utility functions | 633-985 | 353 | `resolve_root`, `find_project_root`, `collect_files`, `file_within_line_limit`, `bytecount_newlines`, `collect_files_multi`, `resolve_root_multi`, `run()` dispatch |

### Proposed Modules

```
src/cli/
  mod.rs                (~630 LOC) - Cli struct, Commands enum (unavoidable; clap requires enum in one place), run() dispatch
  files.rs              (~200 LOC) - collect_files, collect_files_multi, file_within_line_limit, bytecount_newlines
  resolve.rs            (~100 LOC) - resolve_root, resolve_root_multi, find_project_root
```

### Shared Extractions

None. The utility functions are standalone and only called from `run()`.

### Migration Risk: **Low**

The `Commands` enum cannot be split (clap derive limitation), so it stays in `mod.rs`. Even with the enum, the file drops from 985 to ~630, which is borderline. The real value is separating the file collection/resolution logic from the CLI definition.

**Note:** If the help text on each command variant continues to grow, consider moving the long help strings to a separate `help_text.rs` module (constants or `include_str!` files). That would reduce `mod.rs` further.

---

## Proposal 5: `src/db/writer.rs` (909 LOC)

**Priority: Low.** Production code is ~512 LOC. Tests are ~397 LOC.

### Concern Groups

| Group | Lines | LOC | Description |
|-------|-------|-----|-------------|
| File mtime utilities | 16-57 | 42 | `file_mtime_rfc3339`, `is_file_up_to_date`, `load_indexed_mtimes` |
| Serialization types | 63-153 | 91 | `PreserializedRow`, `ExportRecord`, `MethodRecord`, `serialize_file_data` |
| Write operations | 164-321 | 158 | `upsert_preserialized`, `delete_all_files`, `upsert_file_data` |
| Read operations | 329-469 | 141 | `load_files_map`, `rebuild_and_write_reverse_deps`, `write_reverse_deps`, `upsert_workspace_packages`, `write_meta` |
| Helper | 495-511 | 17 | `extract_function_names` |
| Tests | 513-909 | 397 | Database integration tests |

### Proposed Modules

Extracting tests alone brings this to 512 LOC, which is well under threshold. A test extraction is sufficient:

```
src/db/
  writer.rs             (~512 LOC) - all production code (stays as-is)
  writer_tests.rs       (~397 LOC) - tests (use `#[cfg(test)] #[path = "writer_tests.rs"] mod tests;`)
```

If further splitting is desired, the serialization types and utilities could be separated, but the current production LOC does not warrant it.

### Migration Risk: **Low**

Test extraction is zero-risk. The `#[path]` attribute approach keeps tests co-located without changing any imports.

---

## Proposal 6: `src/parser/builtin/python.rs` (898 LOC)

**Priority: Low.** Production code is ~482 LOC, well under threshold.

### Concern Groups

| Group | Lines | LOC | Description |
|-------|-------|-----|-------------|
| Utility function | 8-26 | 19 | `dot_import_to_path` |
| Struct + constructor | 28-119 | 92 | `PythonParser` struct, `new()` |
| Export extraction | 121-242 | 122 | `extract_exports`, `build_definition_map`, `extract_dunder_all` |
| Import/dep extraction | 244-289 | 46 | `extract_imports`, `extract_dependencies` |
| Class method extraction | 291-406 | 116 | `extract_class_methods`, `extract_python_method_entry` |
| Decorators + Parser impl | 408-481 | 74 | `extract_decorators`, `impl Parser for PythonParser` |
| Tests | 482-898 | 416 | Unit tests |

### Proposed Modules

Test extraction alone brings this under threshold:

```
src/parser/builtin/
  python.rs             (~482 LOC) - all production code
  python/tests.rs       (~416 LOC) - tests
```

If the parser grows further, the same directory-module pattern from TypeScript/Rust applies.

### Migration Risk: **Low**

---

## Proposal 7: `src/manifest/private_members.rs` (825 LOC)

**Priority: Medium.** The file has clear language-specific blocks that map to separate modules.

### Concern Groups

| Group | Lines | LOC | Description |
|-------|-------|-----|-------------|
| Types + dispatch | 1-140 | 140 | `TopLevelFunction`, `PrivateMember`, `extract_private_members`, `extract_top_level_functions`, `find_private_method_range`, `find_top_level_function_range` |
| TypeScript extraction | 142-431 | 290 | `extract_ts_top_level`, `extract_ts_private`, `walk_ts_node`, `collect_ts_private_members`, `ts_private_method`, `ts_private_field` |
| Python extraction | 433-518 | 86 | `extract_py_private`, `walk_py_node`, `collect_py_private_members`, `is_py_private`, `extract_py_top_level` |
| Tests | 524-825 | 301 | Tests |

### Proposed Modules

```
src/manifest/
  private_members/
    mod.rs              (~140 LOC) - types (TopLevelFunction, PrivateMember), dispatch functions, find_*_range
    typescript.rs       (~290 LOC) - all extract_ts_*, walk_ts_node, collect_ts_private_members, ts_private_method, ts_private_field
    python.rs           (~86 LOC)  - all extract_py_*, walk_py_node, collect_py_private_members, is_py_private
    tests.rs            (~301 LOC) - tests
```

### Shared Extractions

`TopLevelFunction` and `PrivateMember` structs stay in `mod.rs` and are used by both `typescript.rs` and `python.rs`.

### Migration Risk: **Low**

The language-specific blocks are already cleanly separated with comment headers. The dispatch functions in `mod.rs` already route by file extension. No public API changes needed.

---

## Proposal 8: `src/cli/search.rs` (744 LOC)

**Priority: Low.** Production code is ~399 LOC. The file has 6 JSON serialization structs (L8-55) and two search paths (bare search, flag search).

### Proposed Action

Test extraction only:

```
src/cli/
  search.rs             (~399 LOC)
  search_tests.rs       (~345 LOC) - via #[path] attribute
```

No further splitting needed at 399 LOC.

### Migration Risk: **Low**

---

## Proposal 9: `src/format/yaml_formatters.rs` (700 LOC)

**Priority: Low.** Production code is ~439 LOC.

### Concern Groups

| Group | Lines | LOC | Description |
|-------|-------|-----|-------------|
| File outline formatting | 16-226 | 211 | `format_file_outline` (the largest single function at 211 LOC) |
| Lookup/search formatters | 229-438 | 210 | `format_lookup_export`, `format_dependency_graph`, `format_dependency_graph_transitive`, `format_read_symbol`, `format_class_redirect` |
| Tests | 440-700 | 261 | Tests |

### Proposed Action

Test extraction brings this to 439 LOC. However, `format_file_outline` at 211 LOC is worth noting as a candidate for future internal refactoring (breaking into sub-functions), not file splitting.

### Migration Risk: **Low**

---

## Summary: Priority Order

| Priority | File | Action | Estimated Effort |
|----------|------|--------|-----------------|
| **High** | `typescript.rs` (2,011) | Split into directory module (4-6 files) | 2-3 hours |
| **High** | `rust.rs` (1,694) | Split into directory module (4-5 files) | 2-3 hours |
| **Medium** | `search.rs` (1,614) | Split into directory module (5-6 files) | 1-2 hours |
| **Medium** | `cli/mod.rs` (985) | Extract file utilities + resolve logic | 1 hour |
| **Medium** | `private_members.rs` (825) | Split by language (TS/Python) | 1 hour |
| **Low** | `db/writer.rs` (909) | Extract tests only | 30 min |
| **Low** | `python.rs` (898) | Extract tests only | 30 min |
| **Low** | `cli/search.rs` (744) | Extract tests only | 30 min |
| **Low** | `format/yaml_formatters.rs` (700) | Extract tests only | 30 min |

## Cross-cutting Pattern: Test Extraction

A universal first pass would extract `#[cfg(test)] mod tests` from all 9 files into separate test files. This is the lowest-risk refactor and would bring 6 of 9 files under 600 LOC immediately. For files that remain over threshold after test extraction (typescript.rs, rust.rs, search.rs, cli/mod.rs, private_members.rs), the directory-module splits apply.

Two approaches for test extraction in Rust:

1. **`#[path]` attribute**: `#[cfg(test)] #[path = "writer_tests.rs"] mod tests;` in the original file. Zero impact on the module tree.
2. **Directory module**: Convert `foo.rs` to `foo/mod.rs` + `foo/tests.rs`. Slightly more structural change but cleaner for files that need multiple sub-modules anyway.

For typescript.rs, rust.rs, search.rs, and private_members.rs, the directory module approach is recommended since they benefit from production code splitting too. For the remaining files, the `#[path]` approach suffices.

## Open Questions

1. **Parser trait extension**: Would a `ParserExtractors` trait (with default methods for shared extraction patterns across TS/Rust/Python) reduce duplication? The class method extraction logic is nearly identical across all three parsers.
2. **Shared test utilities**: The test helpers (`make_entry`, `manifest_with`, `parse()` wrappers) are duplicated across test modules. A `src/test_utils.rs` module could centralize these.
3. **`cli/mod.rs` Commands enum**: At 574 LOC of declarative clap attributes, this will only grow as commands are added. Worth considering whether `include_str!` or a macro could generate help text from external files.
