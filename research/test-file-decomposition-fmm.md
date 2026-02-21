---
title: Test File Decomposition Proposal for fmm
type: research
tags: [fmm, testing, refactoring, decomposition]
summary: Structured decomposition plan for 5 large test files (8,619 LOC total) into per-language and per-concern modules matching production code layout
status: active
source: codebase-analyst
confidence: high
created: 2026-03-16
updated: 2026-03-16
---

## Executive Summary

Five test files in fmm total 8,619 LOC and need decomposition to match the per-language module pattern already applied to production code under `src/parser/builtin/`. The files split cleanly: `cross_language_validation.rs` and `edge_cases.rs` are purely language-partitioned, `fixture_validation.rs` maps 1:1 to language fixtures, and `mcp_tools.rs` and `src/mcp/tests.rs` split by MCP tool concern. No ambiguous ownership was found. Shared utilities are minimal and already isolated.

## Production Module Reference

Production parsers live in `src/parser/builtin/` with one file (or directory) per language:
`c.rs`, `cpp.rs`, `csharp.rs`, `dart.rs`, `elixir.rs`, `go.rs`, `java.rs`, `kotlin.rs`, `lua.rs`, `php.rs`, `python/`, `ruby.rs`, `rust/`, `scala.rs`, `swift.rs`, `typescript/`, `zig.rs`

---

## File 1: `tests/cross_language_validation.rs` (2,757 LOC)

### Current Structure

17 language imports (lines 14-31), then test functions organized by clear section headers. Every test function validates parser accuracy against inline real-world code snippets.

| Language | Tests | Line Range | LOC |
|----------|-------|------------|-----|
| Python | `python_real_repo_httpx_simple_functions`, `python_real_repo_httpx_init_with_all`, `python_real_repo_httpx_class_with_decorators`, `python_real_repo_aliased_and_star_imports`, `python_real_repo_fastapi_decorated_exports`, `python_real_repo_dunder_all_with_decorated_models` | 33-392 | ~360 |
| Rust | `rust_real_repo_bat_style_config`, `rust_real_repo_ripgrep_style_searcher`, `rust_real_repo_visibility_filtering`, `rust_real_repo_complex_derives_and_use_groups` | 394-708 | ~315 |
| TypeScript | `typescript_real_repo_barrel_file`, `typescript_real_repo_complex_module`, `typescript_real_repo_internal_module`, `typescript_real_repo_default_and_type_exports`, `typescript_real_repo_default_export_identifier` | 710-947 | ~238 |
| Go | `go_real_repo_http_handler`, `go_real_repo_interface_pattern` | 949-1075 | ~127 |
| Java | `java_real_repo_spring_controller`, `java_real_repo_generics_and_interfaces` | 1077-1191 | ~115 |
| C++ | `cpp_real_repo_modern_patterns` | 1193-1274 | ~82 |
| C# | `csharp_real_repo_aspnet_service` | 1276-1340 | ~65 |
| Ruby | `ruby_real_repo_rails_model`, `ruby_real_repo_module_mixins` | 1342-1475 | ~134 |
| PHP | `php_real_repo_laravel_controller`, `php_real_repo_composer_package` | 1477-1653 | ~177 |
| C | `c_real_repo_linux_kernel_style_module` | 1655-1744 | ~90 |
| C (embedded) | `c_real_repo_embedded_systems_pattern` | 1746-1826 | ~81 |
| Zig | `zig_real_allocator_pattern`, `zig_real_build_zig_pattern` | 1828-2000 | ~173 |
| Lua | `lua_real_neovim_plugin_pattern`, `lua_real_love2d_game_pattern` | 2002-2132 | ~131 |
| Scala | `scala_real_akka_actor_pattern`, `scala_real_spark_job_pattern` | 2134-2278 | ~145 |
| Swift | `swift_real_ios_app_pattern`, `swift_real_swiftui_pattern` | 2280-2404 | ~125 |
| Kotlin | `kotlin_real_android_viewmodel_pattern`, `kotlin_real_ktor_server_pattern` | 2406-2532 | ~127 |
| Dart | `dart_real_flutter_widget_pattern`, `dart_real_data_layer_pattern` | 2534-2658 | ~125 |
| Elixir | `elixir_real_genserver_pattern`, `elixir_real_phoenix_context_pattern` | 2660-2757 | ~98 |

### Proposed Split

Convert to a directory module: `tests/cross_language_validation/`

| New File | Contents | Est. LOC |
|----------|----------|----------|
| `mod.rs` | (empty, just `mod` declarations) | ~20 |
| `python.rs` | 6 Python validation tests | ~370 |
| `rust.rs` | 4 Rust validation tests | ~325 |
| `typescript.rs` | 5 TypeScript validation tests | ~250 |
| `go.rs` | 2 Go validation tests | ~140 |
| `java.rs` | 2 Java validation tests | ~125 |
| `cpp.rs` | 1 C++ validation test | ~95 |
| `csharp.rs` | 1 C# validation test | ~75 |
| `ruby.rs` | 2 Ruby validation tests | ~145 |
| `php.rs` | 2 PHP validation tests | ~190 |
| `c.rs` | 2 C validation tests (kernel + embedded) | ~180 |
| `zig.rs` | 2 Zig validation tests | ~185 |
| `lua.rs` | 2 Lua validation tests | ~145 |
| `scala.rs` | 2 Scala validation tests | ~155 |
| `swift.rs` | 2 Swift validation tests | ~135 |
| `kotlin.rs` | 2 Kotlin validation tests | ~140 |
| `dart.rs` | 2 Dart validation tests | ~135 |
| `elixir.rs` | 2 Elixir validation tests | ~110 |

### Shared Utilities

None. Each test is self-contained with inline source snippets. Each file needs only its own parser import + `use fmm::parser::Parser;`.

---

## File 2: `src/mcp/tests.rs` (2,051 LOC)

### Current Structure

Unit tests for MCP server internals. Tests are organized by ALP ticket and functional area, with several helper functions that construct test manifests.

| Concern | Tests | Line Range | LOC |
|---------|-------|------------|-----|
| Server basics | `test_server_construction`, `cap_response_*` (3 tests) | 4-45 | ~42 |
| Error handling | `dependency_graph_directory_path_returns_helpful_error`, `read_symbol_empty_name_returns_helpful_error`, `file_outline_directory_path_returns_helpful_error` | 47-120 | ~74 |
| Dotted notation / reexports | `read_symbol_dotted_notation_returns_method_source`, `read_symbol_dotted_not_found_gives_helpful_error`, `is_reexport_file_detects_index_files`, `read_symbol_follows_reexport_to_concrete_definition` | 122-302 | ~181 |
| Glob matching helpers | `glob_filename_matches_*` (4 tests) | 304-328 | ~25 |
| list_files tool | `list_files_tool_no_args`, `list_files_tool_with_directory`, `list_files_tool_pagination_limit_and_offset` | 330-517 | ~188 |
| ALP-838: dependency_graph filter | `dependency_filter_manifest` helper, `dependency_graph_filter_*` (4 tests) | 518-649 | ~132 |
| ALP-803: list_files sort/order | `list_files_sort_manifest` helper, `list_files_order` helper, sort/order tests (7 tests) | 651-826 | ~176 |
| ALP-818: list_files group_by | `list_files_group_by_subdir_*` (2 tests) | 828-873 | ~46 |
| ALP-836: list_files directory="." | 3 tests | 875-933 | ~59 |
| ALP-835: group_by + directory | `group_by_directory_manifest` helper, 3 tests | 935-1046 | ~112 |
| ALP-819: list_files filter | 3 tests | 1048-1171 | ~124 |
| ALP-821: list_files sort_by=modified | `list_files_modified_manifest` helper, 4 tests | 1172-1281 | ~110 |
| ALP-778: lookup_export dotted | 3 tests | 1283-1400 | ~118 |
| ALP-779: list_exports method index | 2 tests | 1402-1523 | ~122 |
| ALP-824: list_exports truncation | 2 tests | 1525-1614 | ~90 |
| ALP-837: list_exports regex | `regex_exports_manifest` helper, 5 tests | 1616-1780 | ~165 |
| Import specifier helpers | `compute_import_specifiers_*` (7 tests) | 1782-1930 | ~149 |
| Glossary layer 2 | `glossary_layer2_filters_non_symbol_importers` | 1931-2051 | ~121 |

### Proposed Split

Convert to a directory module: `src/mcp/tests/`

| New File | Contents | Est. LOC |
|----------|----------|----------|
| `mod.rs` | `mod` declarations, shared imports (`use super::*;`, `use super::tools::*;`) | ~15 |
| `server_basics.rs` | Server construction, cap_response, error handling tests | ~120 |
| `read_symbol.rs` | Dotted notation, reexport following, empty name errors | ~185 |
| `file_outline.rs` | file_outline directory error (currently 1 test, room for growth) | ~30 |
| `list_files.rs` | All list_files tests: no_args, directory, pagination, sort/order, group_by, filter, modified, directory="." | ~815 |
| `list_exports.rs` | list_exports: pattern, pagination, method index, truncation, regex | ~380 |
| `dependency_graph.rs` | dependency_graph filter tests | ~140 |
| `lookup_export.rs` | lookup_export dotted name fallback tests | ~125 |
| `import_specifiers.rs` | compute_import_specifiers_* unit tests | ~155 |
| `glossary.rs` | glossary layer 2 filtering test | ~125 |

### Shared Utilities

Several helper functions build test manifests. These should go in `mod.rs` or a dedicated `helpers.rs`:

- No shared fixtures across groups. Each test group has its own manifest builder (e.g., `dependency_filter_manifest`, `list_files_sort_manifest`, `list_files_modified_manifest`, `group_by_directory_manifest`, `regex_exports_manifest`).
- The `list_files_order` helper (line 701) is used only within list_files tests.

The split is clean because each manifest builder is used only by its own test group.

### Alternative: Split list_files.rs further

`list_files.rs` at ~815 LOC is still large. Could further split into:
- `list_files_core.rs` (~190 LOC): basic tests, directory, pagination
- `list_files_sort.rs` (~280 LOC): sort_by, order, group_by
- `list_files_filter.rs` (~345 LOC): filter=source/tests, modified, directory="."

---

## File 3: `tests/fixture_validation.rs` (1,457 LOC)

### Current Structure

Each test parses a fixture file from `fixtures/` using `include_str!` and validates exports, imports, dependencies, and LOC. One test per language, perfectly aligned.

| Language | Test Function | Line Range | LOC |
|----------|--------------|------------|-----|
| Python | `validate_python_fixture` | 20-72 | ~53 |
| TypeScript | `validate_typescript_fixture` | 74-124 | ~51 |
| Rust | `validate_rust_fixture` | 126-192 | ~67 |
| Go | `validate_go_fixture` | 194-270 | ~77 |
| Java | `validate_java_fixture` | 272-337 | ~66 |
| C++ | `validate_cpp_fixture` | 339-409 | ~71 |
| C# | `validate_csharp_fixture` | 411-463 | ~53 |
| Ruby | `validate_ruby_fixture` | 465-527 | ~63 |
| PHP | `validate_php_fixture` | 529-587 | ~59 |
| C | `validate_c_fixture` | 589-661 | ~73 |
| Zig | `validate_zig_fixture` | 663-743 | ~81 |
| Lua | `validate_lua_fixture` | 745-812 | ~68 |
| Scala | `validate_scala_fixture` | 814-871 | ~58 |
| Swift | `validate_swift_fixture` | 873-940 | ~68 |
| Kotlin | `validate_kotlin_fixture` | 942-1022 | ~81 |
| Dart | `validate_dart_fixture` | 1024-1149 | ~126 |
| Elixir | `validate_elixir_fixture` | 1151-1262 | ~112 |
| Dart (extras) | `validate_dart_mixin_fixture`, `validate_dart_extension_fixture`, `validate_dart_factory_constructor_fixture` | 1264-1457 | ~194 |

### Proposed Split

**Recommendation: Keep as single file.**

Each test is ~60-80 LOC, self-contained, and follows an identical pattern. Splitting 17 files of ~70 LOC each creates more module boilerplate than it saves in cognitive load. The file reads linearly and alphabetically.

**If splitting is desired** (for consistency with the other test files), convert to `tests/fixture_validation/`:

| New File | Contents | Est. LOC |
|----------|----------|----------|
| `mod.rs` | Common imports (17 parser imports + `Parser` trait) | ~25 |
| One file per language (17 files) | Single `validate_*_fixture` test each | ~55-130 each |

### Shared Utilities

None. Each test uses only `include_str!` and its parser. The 17 import lines at the top are the only shared element, easily duplicated or centralized in a `mod.rs`.

---

## File 4: `tests/mcp_tools.rs` (1,223 LOC)

### Current Structure

Integration tests that call MCP tools through `McpServer::call_tool`. Uses fixture files written to a temp dir.

| Concern | Tests | Line Range | LOC |
|---------|-------|------------|-----|
| **Helpers** | `write_file`, `setup_mcp_server`, `call_tool_text`, `call_tool_expect_error` | 15-80 | ~66 |
| Manifest loading | `manifest_loads_from_db`, `export_index_consistency` | 86-116 | ~31 |
| fmm_read_symbol | `read_symbol_returns_source_lines`, `read_symbol_not_found`, `read_symbol_truncate_false_bypasses_cap`, `read_symbol_truncate_true_is_default` | 118-176 | ~59 |
| fmm_file_outline | `file_outline_returns_symbols_with_lines`, `file_outline_not_found`, `file_outline_shows_all_exports`, `file_outline_returns_symbols` | 178-257 | ~80 |
| fmm_lookup_export | `lookup_export_returns_sidecar_yaml`, `lookup_export_not_found` | 259-286 | ~28 |
| fmm_list_exports | `list_exports_by_file`, `list_exports_by_pattern`, `list_exports_all`, `list_exports_directory_filter_pattern`, `list_exports_directory_filter_all`, pagination tests (2) | 288-463 | ~176 |
| fmm_dependency_graph | `dependency_graph_upstream_and_downstream`, `dependency_graph_shows_downstream_dependents`, `dependency_graph_not_found`, `dependency_graph_depth2_*`, `dependency_graph_depth1_*` | 465-559 | ~95 |
| fmm_search (term) | `search_term_finds_exact_export`, `search_term_finds_fuzzy_exports`, `search_term_finds_file_path_matches`, `search_term_finds_import_matches`, `search_term_returns_grouped_sections`, `search_term_case_insensitive` | 561-623 | ~63 |
| fmm_search (export filter) | `search_export_fuzzy_fallback`, `search_export_exact_still_works`, `search_export_fuzzy_case_insensitive` | 625-651 | ~27 |
| fmm_search (line ranges) | 2 tests | 653-674 | ~22 |
| fmm_search (structured filters) | `search_depends_on_filter`, `search_depends_on_full_manifest_path`, `search_loc_range`, `search_imports_filter` | 676-742 | ~67 |
| fmm_search (combined) | ALP-786: 4 term+filter intersection tests, 2 regressions | 744-833 | ~90 |
| fmm_search (multi-filter AND) | ALP-823: 5 tests | 834-927 | ~94 |
| Go module resolution | `setup_go_mcp_server` helper, `go_internal_import_resolves_upstream`, `go_internal_import_resolves_downstream`, `go_stdlib_import_no_false_positive` | 929-1203 | ~85 |
| ALP-822: read_symbol class redirect | `setup_large_class_server` helper, 3 tests | 1002-1103 | ~102 |
| ALP-845: lookup_export collision | `setup_collision_server` helper, 2 tests | 1105-1185 | ~81 |
| Debug (ignored) | `debug_large_class_output` | 1206-1223 | ~18 |

### Proposed Split

Convert to `tests/mcp_tools/`:

| New File | Contents | Est. LOC |
|----------|----------|----------|
| `mod.rs` | `mod` declarations + shared helpers (`write_file`, `setup_mcp_server`, `call_tool_text`, `call_tool_expect_error`) | ~85 |
| `manifest.rs` | Manifest loading, export index consistency | ~35 |
| `read_symbol.rs` | read_symbol tests + large class redirect tests (ALP-822) | ~165 |
| `file_outline.rs` | file_outline tests | ~85 |
| `lookup_export.rs` | lookup_export + collision disclosure (ALP-845) | ~115 |
| `list_exports.rs` | list_exports + pagination tests | ~180 |
| `dependency_graph.rs` | dependency_graph + Go module resolution tests | ~185 |
| `search.rs` | All fmm_search tests (term, export filter, line ranges, structured, combined, multi-filter AND) | ~365 |

### Shared Utilities

Four functions must be shared across all submodules:

- `write_file(root, rel, content)` (line 15)
- `setup_mcp_server() -> (TempDir, McpServer)` (line 22)
- `call_tool_text(server, tool, args) -> String` (line 62)
- `call_tool_expect_error(server, tool, args) -> String` (line 68)

Two additional setup helpers are used by specific submodules only:

- `setup_go_mcp_server()` (line 937) -- moves with `dependency_graph.rs`
- `setup_large_class_server()` (line 1007) -- moves with `read_symbol.rs`
- `setup_collision_server()` (line 1110) -- moves with `lookup_export.rs`

---

## File 5: `tests/edge_cases.rs` (1,131 LOC)

### Current Structure

Parser edge case tests organized by concern (cross-language) and then by language. Tests categories like empty files, huge files, syntax errors, no exports, unicode, CRLF, whitespace-only, and comments-only, each repeated across 3+ languages.

| Concern | Languages Covered | Line Range | LOC |
|---------|-------------------|------------|-----|
| Imports | (all 17 parsers) | 1-18 | 18 |
| Empty files | TS, Python, Rust | 20-50 | ~31 |
| Huge files (10k lines) | TS, Python, Rust | 52-91 | ~40 |
| Syntax errors | TS, Python, Rust | 93-118 | ~26 |
| No exports | TS, Python, Rust | 120-144 | ~25 |
| Unicode identifiers | Python, Rust | 146-168 | ~23 |
| CRLF line endings | TS, Python, Rust | 170-215 | ~46 |
| Whitespace-only | TS, Python, Rust | 217-238 | ~22 |
| Comments-only | TS, Python, Rust | 240-267 | ~28 |
| Python decorators | Python (5 tests) | 269-331 | ~63 |
| Go edge cases | Go (4 tests) | 333-368 | ~36 |
| Java edge cases | Java (3 tests) | 370-397 | ~28 |
| C++ edge cases | C++ (4 tests) | 399-435 | ~37 |
| C# edge cases | C# (3 tests) | 437-464 | ~28 |
| Ruby edge cases | Ruby (4 tests) | 466-501 | ~36 |
| TS default exports | TS (6 tests) | 503-562 | ~60 |
| PHP edge cases | PHP (6 tests) | 564-630 | ~67 |
| C edge cases | C (6 tests) | 632-690 | ~59 |
| Zig edge cases | Zig (6 tests) | 692-752 | ~61 |
| Lua edge cases | Lua (6 tests) | 754-814 | ~61 |
| Scala edge cases | Scala (6 tests) | 816-874 | ~59 |
| Swift edge cases | Swift (5 tests) | 876-942 | ~67 |
| Kotlin edge cases | Kotlin (5 tests) | 944-1010 | ~67 |
| Dart edge cases | Dart (5 tests) | 1012-1073 | ~62 |
| Elixir edge cases | Elixir (5 tests) | 1074-1131 | ~58 |

### Proposed Split

This file has two distinct zones:

1. **Lines 20-331**: Cross-language edge cases where the same scenario (empty file, huge file, etc.) is tested across TS/Python/Rust, plus Python-specific decorator tests.
2. **Lines 333-1131**: Per-language edge case sections, each covering empty/syntax-errors/comments/CRLF/visibility for one language.

**Option A: Split by language (matches production layout)**

Convert to `tests/edge_cases/`:

| New File | Contents | Est. LOC |
|----------|----------|----------|
| `mod.rs` | Common imports | ~20 |
| `typescript.rs` | TS empty/huge/syntax/no-exports/unicode/crlf/whitespace/comments + TS default export tests | ~100 |
| `python.rs` | Python empty/huge/syntax/no-exports/unicode/crlf/whitespace/comments + decorator tests | ~115 |
| `rust.rs` | Rust empty/huge/syntax/no-exports/unicode/crlf/whitespace/comments | ~75 |
| `go.rs` | Go edge cases | ~40 |
| `java.rs` | Java edge cases | ~32 |
| `cpp.rs` | C++ edge cases | ~40 |
| `csharp.rs` | C# edge cases | ~32 |
| `ruby.rs` | Ruby edge cases | ~40 |
| `php.rs` | PHP edge cases | ~70 |
| `c.rs` | C edge cases | ~62 |
| `zig.rs` | Zig edge cases | ~64 |
| `lua.rs` | Lua edge cases | ~64 |
| `scala.rs` | Scala edge cases | ~62 |
| `swift.rs` | Swift edge cases | ~70 |
| `kotlin.rs` | Kotlin edge cases | ~70 |
| `dart.rs` | Dart edge cases | ~65 |
| `elixir.rs` | Elixir edge cases | ~60 |

This requires pulling the cross-language tests (lines 20-267) apart. For example, `typescript_empty_file` goes to `typescript.rs`, `python_empty_file` goes to `python.rs`, etc. The function names already have language prefixes, making this mechanical.

### Shared Utilities

None. Every test is self-contained.

---

## Summary Table

| File | Current LOC | Proposed Submodules | Avg LOC/Module |
|------|-------------|---------------------|----------------|
| `cross_language_validation.rs` | 2,757 | 18 language files + mod.rs | ~150 |
| `src/mcp/tests.rs` | 2,051 | 10 files (8 concern + mod + helpers) | ~205 |
| `fixture_validation.rs` | 1,457 | Keep as-is (or 18 files) | ~80 |
| `mcp_tools.rs` | 1,223 | 9 files (7 tool + mod + search) | ~140 |
| `edge_cases.rs` | 1,131 | 18 language files + mod.rs | ~60 |

## Implementation Notes

1. **Rust test module conventions**: Converting `tests/foo.rs` to `tests/foo/mod.rs` with submodules requires each submodule to be `pub mod` or `mod` in `mod.rs`. Integration test crates in Rust treat each file under `tests/` as a separate crate, so `tests/cross_language_validation/mod.rs` becomes the crate root and can `mod python;` to include `tests/cross_language_validation/python.rs`.

2. **Compilation parallelism**: Splitting integration test files means more test crates compiled in parallel, which can improve incremental compile times. Each integration test file under `tests/` becomes its own crate. Splitting tests within a file into submodules of the same crate does not increase crate count.

3. **Fixture validation**: The recommendation to keep `fixture_validation.rs` as a single file is based on its uniform structure. Every test follows an identical pattern: parse fixture, assert exports, assert imports, assert deps, assert LOC. Splitting into 17 files of ~70 LOC each adds overhead without reducing cognitive load.

4. **Priority order**: Start with `cross_language_validation.rs` (largest, clearest split points), then `edge_cases.rs` (same pattern), then `mcp_tools.rs` and `src/mcp/tests.rs` (require careful utility extraction).
