---
title: Rust Language Support Gap Analysis for fmm
type: research
tags: [fmm, rust, parser, gap-analysis, tree-sitter]
summary: Comprehensive analysis of fmm's Rust parser capabilities vs TypeScript parity, with prioritized gaps
status: active
source: codebase-analyst
confidence: high
created: 2026-03-16
updated: 2026-03-16
---

## Executive Summary

fmm's Rust parser (`src/parser/builtin/rust.rs`, 1,694 LOC) is the second largest language parser after TypeScript (2,011 LOC) and has strong foundational coverage. It extracts exports, imports, dependencies, impl methods, trait impls, derives, lifetimes, unsafe blocks, async function counts, macros, and `pub use` re-exports. The primary gaps fall into two categories: (1) on-demand tree-sitter features that only support TS/JS/Python today, and (2) Rust-specific language features that lack extraction or indexing.

## Current Rust Capabilities

### Exports (lines 68-96 of rust.rs)
Extracted via tree-sitter queries anchored to `source_file`:
- `pub fn` (top-level only, impl block methods handled separately)
- `pub struct`, `pub enum`, `pub trait`
- `pub type` aliases
- `pub const`, `pub static`
- `pub mod` declarations

Visibility filtering is correct: `pub(crate)` and `pub(super)` are excluded from exports. Binary crate detection (`main.rs`, `src/bin/*.rs`) switches to all-item queries that ignore visibility.

### Impl Block Methods (lines 230-308, ALP-770)
- Public methods on exported types are indexed with `parent_class` set
- Supports generic types: `impl<T> Wrapper<T>` resolves to `Wrapper`
- Trait impl methods with `pub` visibility are also captured
- Methods on non-exported types are correctly excluded

### Imports (lines 310-342)
- Extracts root crate name from `use` declarations (e.g., `use tokio::runtime::Runtime` -> `tokio`)
- Handles `extern crate` declarations
- Filters out `self`, `crate`, `super` from imports list
- Includes std/core/alloc as imports

### Dependencies (lines 348-462)
- Converts `crate::` paths to `crate::module` format
- Converts `super::` paths to `../module` format using `rust_use_path_to_dep()`
- Handles `scoped_use_list` (`crate::parser::{builtin, search}`)
- Handles `use_wildcard` (`crate::parser::*`)
- External crate imports are correctly excluded from deps

### Custom Fields (lines 848-946)
| Field | Extraction Method | Notes |
|-------|------------------|-------|
| `unsafe_blocks` | Count of `(unsafe_block)` nodes | Simple count, no context |
| `derives` | Parses `#[derive(...)]` attribute arguments | Deduped, sorted |
| `trait_impls` | Matches `impl Trait for Type` | Handles scoped traits (`std::fmt::Display` -> `Display`) |
| `lifetimes` | All `(lifetime)` nodes | Filters `'_` anonymous lifetime |
| `async_functions` | Counts `function_modifiers` containing "async" | Simple count |

### Macros (lines 598-748, ALP-775)
- `#[macro_export] macro_rules!` -> exported as `name!`
- `#[proc_macro_derive(Name)]` -> exported as `Name`
- `#[proc_macro_attribute]` and `#[proc_macro]` -> exported as function name
- Handles multiple preceding attributes correctly

### pub use Re-exports (lines 750-845)
- Simple path: `pub use crate::runtime::Runtime` -> exports `Runtime`
- Aliased: `pub use crate::X as Alias` -> exports `Alias`
- Grouped: `pub use crate::task::{JoinHandle, LocalSet}` -> exports both
- Wildcard `pub use crate::prelude::*` correctly emits no exports

### Test Coverage
- 37 unit tests in `rust.rs` (lines 977-1694)
- 4 integration tests in `cross_language_validation.rs` (bat-style config, ripgrep-style searcher, visibility filtering, complex derives/use groups)
- 1 fixture validation test against `fixtures/sample.rs`
- Good coverage of edge cases: visibility modifiers, generic impls, binary vs library crates, grouped use, wildcard use, proc macros

## TypeScript Parity Gaps

These are features the TypeScript parser has that the Rust parser lacks.

### 1. Named Import Tracking (ALP-881) -- HIGH IMPACT

**TypeScript**: Populates `Metadata.named_imports` and `Metadata.namespace_imports`. This enables fmm_glossary Layer 2 (named-import-filtered `used_by`) and Layer 3 (call-site precision).

**Rust**: Does not populate `named_imports` or `namespace_imports`. The `parse_inner` method constructs `Metadata` with `..Default::default()` which leaves these fields empty (line 942).

**Impact**: `fmm_glossary` and `fmm_lookup_export` cannot trace Rust symbol usage across files. This is the single largest functional gap because it blocks the entire symbol-level impact analysis workflow for Rust codebases.

**What's needed**: Extract `use crate::module::SymbolName` patterns to populate `named_imports` with the mapping `"crate::module" -> ["SymbolName"]`. Also handle `use crate::module::*` as namespace imports.

### 2. function_names Custom Field (ALP-863) -- MEDIUM IMPACT

**TypeScript**: Emits `function_names` in `custom_fields`, listing confirmed function declaration names. The manifest uses this to build `function_index` for call-site precision in `fmm_glossary`.

**Rust**: Does not emit `function_names`. All exported functions, struct methods, and standalone functions are absent from the function index.

**Impact**: `fmm_glossary` Layer 3 call-site precision cannot work for Rust files.

### 3. On-Demand Private Member Extraction -- MEDIUM IMPACT

**TypeScript/Python**: `extract_private_members()` in `src/manifest/private_members.rs` (line 116) handles `.ts/.tsx/.js/.jsx/.mjs/.cjs` and `.py` files. Returns private class methods with line ranges.

**Rust**: Returns `HashMap::new()` for `.rs` files (line 120, default match arm).

**Impact**: `fmm_file_outline(include_private: true)` silently returns no private members for Rust files. The `fmm_read_symbol("ClassName.method")` path for private methods also fails silently via `find_private_method_range()`.

**What's needed**: Implement `extract_rs_private()` that walks `impl` blocks for a given type and returns non-pub methods.

### 4. On-Demand Non-Exported Function Extraction -- MEDIUM IMPACT

**TypeScript/Python**: `extract_top_level_functions()` in `src/manifest/private_members.rs` (line 51) returns non-exported top-level functions for TS/JS/Python.

**Rust**: Returns `Vec::new()` for `.rs` files (line 55, default match arm).

**Impact**: `fmm_file_outline(include_private: true)` shows no `non_exported:` section for Rust. The `fmm_read_symbol("path/to/file.rs:helperFn")` path for reading non-exported functions also fails silently.

**What's needed**: Implement `extract_rs_top_level()` that returns all non-pub `fn` items at module scope.

### 5. Nested Symbol Extraction (ALP-922) -- LOW IMPACT

**TypeScript**: `extract_nested_symbols()` finds depth-1 function declarations and closure-state variables inside function bodies. These appear with `kind: "nested-fn"` or `kind: "closure-state"` in exports.

**Rust**: No equivalent. Rust's nested function pattern (functions defined inside other functions) is less common than in JS/TS, but it exists. Closures assigned to variables (`let handler = |x| { ... }`) are also relevant.

**Impact**: Low for most Rust codebases. Nested functions in Rust are uncommon compared to JS.

### 6. tsconfig Path Alias Resolution (ALP-794/925) -- NOT APPLICABLE

TypeScript's `parse_file()` resolves tsconfig path aliases for dependency classification. Rust has no equivalent concept (Cargo handles all path resolution). This is not a gap.

## Rust-Specific Gaps

Features unique to Rust that should be extracted but currently are not.

### 1. cfg/cfg_attr Conditional Compilation -- MEDIUM VALUE

`#[cfg(feature = "...")]`, `#[cfg(target_os = "...")]`, `#[cfg_attr(...)]` are pervasive in Rust. Currently no extraction.

**Value**: Knowing which features gate which exports would let fmm users understand conditional API surfaces. Could be stored as a custom field `"cfg_gates"` mapping export names to their conditions.

### 2. Associated Types in Trait Definitions -- LOW VALUE

```rust
pub trait Iterator {
    type Item;
    fn next(&mut self) -> Option<Self::Item>;
}
```

Associated types are not extracted as separate symbols. They are part of the trait definition but invisible in fmm output.

### 3. Trait Method Signatures (without impl) -- LOW VALUE

Trait definitions declare method signatures, but only `impl` block methods get extracted as `ExportEntry` items with `parent_class`. The trait's own method declarations (which define the interface contract) are not captured.

### 4. Const Generics -- LOW VALUE

`pub struct Array<const N: usize>` -- const generic parameters are not extracted or noted.

### 5. Where Clauses -- LOW VALUE

Complex trait bounds (`where T: Serialize + Clone`) are not captured. These are important for understanding API contracts but low value for structural indexing.

### 6. Feature-Gated Dependencies -- MEDIUM VALUE

`Cargo.toml` is not parsed. Knowing which crates are optional (behind feature flags) vs required would enrich the dependency picture. This is a separate concern from the parser itself but relevant to Rust support completeness.

## Priority Recommendations

### P0: Named Import Tracking for Rust

**Why first**: This unblocks the entire fmm_glossary/fmm_lookup_export workflow for Rust. Without it, fmm can index Rust files but cannot answer "who uses this symbol?" which is the core value proposition.

**Implementation sketch**:
- In `extract_imports` or a new `extract_named_imports` method, capture the full `use` path and the imported symbol name
- `use crate::parser::Parser` -> `named_imports["crate::parser"] = ["Parser"]`
- `use anyhow::{Context, Result}` -> `named_imports["anyhow"] = ["Context", "Result"]`
- `use crate::config::*` -> `namespace_imports.push("crate::config")`
- Wire into `Metadata.named_imports` and `Metadata.namespace_imports`

**Estimated effort**: Medium. The use-path parsing infrastructure already exists in `extract_use_roots` and `use_declaration_deps`. The main work is restructuring to capture both the module path and the specific imported names.

### P1: On-Demand Private/Non-Exported Extraction for Rust

**Why second**: Enables `fmm_file_outline(include_private: true)` and `fmm_read_symbol("path/to/file.rs:helperFn")` for Rust. These are the primary navigation tools during code review.

**Implementation sketch**:
- Add `extract_rs_private()` in `private_members.rs` that parses `.rs` files with tree-sitter-rust
- Walk `impl` blocks, collect non-pub `fn` items
- Add `extract_rs_top_level()` that collects non-pub top-level `fn` items
- Add `.rs` match arms in `extract_private_members()` and `extract_top_level_functions()`

**Estimated effort**: Medium. The TypeScript implementation in `private_members.rs` is a good template.

### P2: function_names Custom Field

**Why third**: Enables Layer 3 call-site precision in fmm_glossary for Rust. Requires P0 (named imports) to be useful.

**Implementation sketch**: In `parse_inner`, collect names of all `pub fn` exports (both top-level and impl methods) and emit as `function_names` in custom_fields.

**Estimated effort**: Small. The data is already available from the export extraction pass.

### P3: cfg Conditional Compilation Extraction

**Why later**: Useful for understanding feature-gated APIs but not blocking any core fmm workflow.

**Implementation sketch**: Add a tree-sitter query for `(attribute_item (attribute (identifier) @name) @attr)` where name is "cfg" or "cfg_attr". Extract the condition text and associate with the next sibling item.

**Estimated effort**: Medium. The attribute-sibling association pattern already exists in `extract_macro_exports()`.

## File Reference

| File | LOC | Role |
|------|-----|------|
| `src/parser/builtin/rust.rs` | 1,694 | Rust parser (tree-sitter queries + extraction) |
| `src/parser/builtin/typescript.rs` | 2,011 | TypeScript parser (reference implementation) |
| `src/parser/mod.rs` | ~130 | `ExportEntry`, `Metadata`, `ParseResult`, `Parser` trait |
| `src/manifest/private_members.rs` | 825 | On-demand private member extraction (TS/JS/Python only) |
| `src/extractor/mod.rs` | 90 | `FileProcessor` and `ParserCache` |
| `fixtures/sample.rs` | 60 | Rust test fixture |
| `tests/cross_language_validation.rs` | 2,757 | Integration tests (4 Rust-specific tests) |
| `tests/fixture_validation.rs` | 1,457 | Fixture validation (1 Rust test) |
