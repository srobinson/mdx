---
title: Language dispatch blast radius analysis for fmm
type: research
tags: [fmm, architecture, language-support, dispatch, refactoring]
summary: Every file in fmm that contains language-specific branching logic, documenting the full blast radius when adding a new language.
status: active
source: codebase-analyst
confidence: high
created: 2026-03-16
updated: 2026-03-16
---

## Executive Summary

fmm has **8 distinct locations** across **6 files** where language-specific dispatch logic lives. The parser subsystem (`parser/builtin/`) already follows the per-language file pattern the user proposes. The remaining dispatch sites are scattered across the manifest, resolver, config, MCP, and DB layers. Most of these are hardcoded extension lists or match arms that silently degrade (return empty results or include false positives) when a new language is added without updating them.

## Dispatch Sites

### 1. `src/parser/mod.rs` -- `register_builtin()` (lines 186-237)

**What it dispatches:** Parser factory registration. Maps file extensions to their tree-sitter parser constructors.

**Mechanism:** Sequential `register_language!` macro calls and manual `self.register()` calls. Each call binds extension(s) to a parser struct from `parser/builtin/<lang>.rs`.

**Current languages:** TypeScript/JS (`ts`, `js`), TSX/JSX (`tsx`, `jsx`), Python (`py`), Rust (`rs`), Go (`go`), Java (`java`), C++ (`cpp`, `hpp`, `cc`, `hh`, `cxx`, `hxx`), C# (`cs`), Ruby (`rb`), PHP (`php`), C (`c`, `h`), Zig (`zig`), Lua (`lua`), Scala (`scala`, `sc`), Swift (`swift`), Kotlin (`kt`, `kts`), Dart (`dart`), Elixir (`ex`, `exs`).

**Impact of missing a case:** Hard failure. `ParserRegistry::get_parser()` returns `Err("No parser registered for extension: .xxx")`. The file is skipped during indexing. This is the **loudest** failure mode in the codebase because it produces an error.

**Architecture note:** This is the one dispatch site that *already* follows good separation. Each parser lives in its own file under `parser/builtin/<lang>.rs`. The `register_builtin` method is the only coupling point, and it is a flat registration list (no branching logic per language).

---

### 2. `src/parser/builtin/mod.rs` (lines 1-23)

**What it dispatches:** Module declarations (`pub mod python;`, `pub mod rust;`, etc.) that make each parser file visible to the crate.

**Mechanism:** Flat list of `pub mod <lang>;` declarations.

**Current languages:** All 17 language modules plus `query_helpers` and a gated `template`.

**Impact of missing a case:** Compile error. If you create `src/parser/builtin/haskell.rs` but forget to add `pub mod haskell;`, the module is invisible and `register_builtin` cannot reference it. This fails at compile time, so it is safe.

---

### 3. `src/config/mod.rs` -- `default_languages()` (lines 137-146)

**What it dispatches:** The default set of file extensions that fmm will scan during indexing. Controls which files get walked and processed.

**Mechanism:** A hardcoded array of 29 extension strings returned as a `BTreeSet<String>`.

**Current languages:** `ts`, `tsx`, `js`, `jsx`, `py`, `rs`, `go`, `java`, `cpp`, `hpp`, `cc`, `hh`, `cxx`, `hxx`, `cs`, `rb`, `php`, `c`, `h`, `zig`, `lua`, `scala`, `sc`, `swift`, `kt`, `kts`, `dart`, `ex`, `exs`.

**Impact of missing a case:** Silent omission. Files with the new extension are never walked, never parsed, never indexed. The parser exists but is never invoked. No error, no warning. The user must manually add the extension to `.fmmrc.toml` `languages` field. **This is the most dangerous silent failure** because it makes a fully implemented parser appear broken.

---

### 4. `src/manifest/private_members.rs` -- Two match dispatch sites

#### 4a. `extract_top_level_functions()` (lines 50-56)

**What it dispatches:** On-demand tree-sitter parsing to find non-exported top-level function definitions for the `fmm_file_outline(include_private: true)` feature.

**Mechanism:** `match ext.as_str()` with arms for TS/JS and Python. Default arm returns `Vec::new()`.

**Current languages:** TypeScript/JS (`ts`, `tsx`, `js`, `jsx`, `mjs`, `cjs`), Python (`py`).

**Impact of missing a case:** Silent degradation. `fmm_file_outline(include_private: true)` returns zero top-level functions for the unsupported language. The `non_exported:` section is empty. No error.

#### 4b. `extract_private_members()` (lines 115-121)

**What it dispatches:** On-demand tree-sitter parsing to find private class members (private fields, private methods) for the `fmm_file_outline(include_private: true)` feature.

**Mechanism:** `match ext.as_str()` with arms for TS/JS and Python. Default arm returns `HashMap::new()`.

**Current languages:** TypeScript/JS (`ts`, `tsx`, `js`, `jsx`, `mjs`, `cjs`), Python (`py`).

**Impact of missing a case:** Silent degradation. `fmm_file_outline(include_private: true)` shows no private members for the unsupported language. Classes appear to have only public members.

---

### 5. `src/manifest/call_site_finder.rs` -- Two match dispatch sites

#### 5a. `file_calls_method()` (lines 65-72)

**What it dispatches:** Tree-sitter verification of whether a candidate file actually contains a `something.METHOD()` call expression. Used by `fmm_glossary(precision: "call-site")` to remove false positive dependents.

**Mechanism:** `match ext.as_str()` with arms for TS/JS, Python, and Rust. Default arm returns `true` (assume it calls the method).

**Current languages:** TypeScript/JS (`ts`, `tsx`, `js`, `jsx`, `mjs`, `cjs`), Python (`py`), Rust (`rs`).

**Impact of missing a case:** Silent false positives. Files in unsupported languages are always included as callers (the `_ => true` default), inflating the `used_by` list in glossary results. Not incorrect per se (conservative), but noisy.

#### 5b. `file_bare_call_result()` (lines 197-202)

**What it dispatches:** Tree-sitter analysis for bare function call sites (non-method calls). Used by `fmm_glossary` to distinguish direct callers from namespace callers.

**Mechanism:** `match ext.as_str()` with an arm for TS/JS only. Default arm returns `DirectCaller`.

**Current languages:** TypeScript/JS (`ts`, `tsx`, `js`, `jsx`, `mjs`, `cjs`) only.

**Impact of missing a case:** Silent false positives. All files in unsupported languages are classified as direct callers, even if they only use namespace imports.

---

### 6. `src/manifest/dependency_matcher.rs` -- `strip_source_ext()` (lines 13-24)

**What it dispatches:** Extension stripping for dependency path resolution. Determines whether a trailing `.xxx` is a file extension (strip it) or part of the filename (keep it, like `runtime.exception`).

**Mechanism:** `match ext` with a hardcoded list of recognized source extensions.

**Current languages:** `ts`, `tsx`, `js`, `jsx`, `mjs`, `cjs`, `py`, `go`, `rs`, `java`, `kt`, `swift`, `dart`, `rb`, `php`, `cs`, `cpp`, `c`, `h`, `lua`, `zig`, `ex`, `exs`, `scala`, `cr` (Crystal, not even a supported parser language).

**Impact of missing a case:** Subtle dependency resolution bugs. If a new language's extension is not listed, dependency paths like `../utils/helper.newlang` will not have `.newlang` stripped, causing the resolved stem to differ from the target stem. Dependencies will silently fail to match, producing missing edges in the dependency graph.

---

### 7. `src/mcp/tools/common.rs` -- `is_reexport_file()` (lines 7-13)

**What it dispatches:** Identification of "re-export hub" files that aggregate symbols from sub-modules (`index.ts`, `__init__.py`, `mod.rs`). Used by `fmm_read_symbol` to skip re-export files and find the concrete definition.

**Mechanism:** `matches!` macro on filename.

**Current languages:** Python (`__init__.py`), TypeScript/JS (`index.ts`, `index.tsx`, `index.js`, `index.jsx`), Rust (`mod.rs`).

**Impact of missing a case:** `fmm_read_symbol` may return source from a re-export file instead of the actual definition. Mild UX degradation.

---

### 8. `src/manifest/glossary_builder.rs` -- `is_test_file()` (lines 54-70)

**What it dispatches:** Test file detection by filename convention. Supplements the configurable `test_patterns` with language-specific heuristics.

**Mechanism:** Hardcoded `ends_with` / `starts_with` checks for Go (`_test.go`) and Python (`test_*.py`, `*_test.py`) naming conventions, plus directory-based patterns (`tests/`, `test/`, `__tests__/`).

**Current languages:** Go (`_test.go`), Python (`test_*.py`, `*_test.py`).

**Impact of missing a case:** Test files for the new language may not be filtered out of source-mode glossary results. The configurable `test_patterns` in `.fmmrc.toml` can compensate, but the built-in heuristic will miss them.

---

### Near-miss: `src/resolver/mod.rs` -- `resolve_by_directory_prefix()` (lines 119-126)

**What it dispatches:** Hardcoded extension candidates for workspace package resolution.

**Current languages:** TypeScript/JS only (`.ts`, `.tsx`, `.js`, `.jsx` plus `index.ts`, `index.js`).

**Impact:** This is intentionally TS/JS-only (workspace resolution uses `oxc_resolver` which is a JS module resolver). Not a dispatch site that needs updating for non-JS languages. Noted for completeness.

### Near-miss: `src/manifest/mod.rs` -- `Manifest.add_file()` and `src/db/reader.rs` (lines 289-301, 180-196)

**What it dispatches:** TS > JS priority when two files export the same symbol name. `.ts` wins over `.js`.

**Current languages:** TypeScript/JS only.

**Impact:** This is a TS/JS-specific collision rule (compiled `.js` shadows source `.ts`). Not a dispatch site for other languages. Other languages fall through to the `else` branch which warns and overwrites.

---

## Summary Table

| # | File | Lines | Dispatch type | Languages handled | Failure mode |
|---|------|-------|---------------|-------------------|--------------|
| 1 | `src/parser/mod.rs` | 186-237 | Registration list | All 17 | **Error** (loud) |
| 2 | `src/parser/builtin/mod.rs` | 1-23 | Module declarations | All 17 | **Compile error** (loud) |
| 3 | `src/config/mod.rs` | 137-146 | Default extension set | 29 extensions | **Silent omission** |
| 4a | `src/manifest/private_members.rs` | 50-56 | Match on ext | TS/JS, Python | Silent empty results |
| 4b | `src/manifest/private_members.rs` | 115-121 | Match on ext | TS/JS, Python | Silent empty results |
| 5a | `src/manifest/call_site_finder.rs` | 65-72 | Match on ext | TS/JS, Python, Rust | Silent false positives |
| 5b | `src/manifest/call_site_finder.rs` | 197-202 | Match on ext | TS/JS only | Silent false positives |
| 6 | `src/manifest/dependency_matcher.rs` | 13-24 | Match on ext | 26 extensions | Silent broken deps |
| 7 | `src/mcp/tools/common.rs` | 7-13 | Matches on filename | Python, TS/JS, Rust | Wrong definition source |
| 8 | `src/manifest/glossary_builder.rs` | 54-70 | Filename heuristics | Go, Python | Test files leak into results |

## New Language Checklist (Current State)

To fully support a new language today, a developer must touch:

1. **Create** `src/parser/builtin/<lang>.rs` -- the parser implementation
2. **Add** `pub mod <lang>;` to `src/parser/builtin/mod.rs`
3. **Add** `register_language!` call to `src/parser/mod.rs` `register_builtin()`
4. **Add** extension(s) to `src/config/mod.rs` `default_languages()`
5. **Add** extension(s) to `src/manifest/dependency_matcher.rs` `strip_source_ext()`
6. **Optionally add** to `src/manifest/private_members.rs` (if the language has private members/top-level functions worth extracting)
7. **Optionally add** to `src/manifest/call_site_finder.rs` (if you want call-site precision for glossary)
8. **Optionally add** re-export hub filename to `src/mcp/tools/common.rs`
9. **Optionally add** test file naming conventions to `src/manifest/glossary_builder.rs`

Steps 1-5 are mandatory. Steps 6-9 are optional but affect feature completeness. Only steps 1-3 produce compile-time errors if skipped. Steps 4-5 fail silently.

## Architectural Observations

**The parser layer is well-factored.** Each language lives in its own file under `parser/builtin/`. The registration in `parser/mod.rs` is a flat list with no per-language branching logic. Adding a language is mechanical.

**The manifest layer is where the real problem lives.** `private_members.rs` and `call_site_finder.rs` contain tree-sitter query logic that is structurally identical per language but hardcoded via match arms. These are the strongest candidates for the proposed `filename.<lang>.rs` split pattern.

**`strip_source_ext` and `default_languages` are flat data, not logic.** These could be derived from the `ParserRegistry` at startup rather than being maintained as independent hardcoded lists. If `ParserRegistry` exposed its registered extensions, both sites could query it instead of maintaining parallel lists.

**`is_reexport_file` and `is_test_file` contain language conventions, not language parsers.** These are lightweight heuristics. Splitting them into per-language files would be over-engineering. A better approach: make them data-driven from a `LanguageConfig` struct that each parser provides alongside its tree-sitter grammar.

## Proposed Consolidation Strategy

The core insight: `strip_source_ext`, `default_languages`, `is_reexport_file`, and `is_test_file` are all **language metadata**, not language logic. They could be expressed as associated data on each parser registration:

```
// Conceptual, not real code
struct LanguageDescriptor {
    extensions: &[&str],
    reexport_filenames: &[&str],      // e.g. ["__init__.py"]
    test_file_patterns: &[TestPattern],
    // ...
}
```

This would reduce the "new language checklist" to:
1. Create `parser/builtin/<lang>.rs` (parser + descriptor)
2. Add `pub mod <lang>;` to `parser/builtin/mod.rs`
3. Add `register_language!` to `parser/mod.rs`

Everything else would be derived from the descriptor.

The `private_members.rs` and `call_site_finder.rs` dispatch sites are the only ones that contain substantial per-language *logic* (tree-sitter queries). These are the files where the `filename.<lang>.rs` split pattern would provide the most value.
