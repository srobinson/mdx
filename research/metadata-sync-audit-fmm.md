---
title: "fmm Metadata Sync Audit: User-Facing Text vs Implementation"
type: research
tags: [fmm, audit, documentation, mcp, cli, language-support]
summary: "Comprehensive audit of all user-facing text in fmm against actual implementation. Found 14 discrepancies across MCP descriptions, CLI help, SKILL.md, and internal comments."
status: active
source: codebase-analyst
confidence: high
created: 2026-03-18
updated: 2026-03-18
---

## Executive Summary

fmm's user-facing metadata has drifted from the implementation across three axes: language support claims, MCP tool count, and internal doc comments. The most impactful gap is the `fmm_file_outline` description which says `include_private` supports "TypeScript, JavaScript, Python" when Rust is fully supported via `RsPrivateMemberExtractor`. A total of **14 discrepancies** were found; 4 are high severity (actively misleading agents/users), 6 are medium, and 4 are low.

## Discrepancies

### 1. HIGH: `fmm_file_outline` MCP description omits Rust from `include_private` support

**Source of truth:** `crates/fmm-cli/tools.toml` lines 304, 318 (propagates to generated_schema.rs, SKILL.md)

**Currently says:**
- Tool description: `"Supported: TypeScript, JavaScript, Python."`
- `include_private` param: `"Supported: TypeScript, JavaScript, Python."`

**Should say:** `"Supported: TypeScript, JavaScript, Python, Rust."`

**Evidence:** `crates/fmm-core/src/manifest/private_members/mod.rs` lines 80-86 registers three extractors:
- `TsPrivateMemberExtractor` (TypeScript/JavaScript)
- `PyPrivateMemberExtractor` (Python)
- `RsPrivateMemberExtractor` (Rust)

All three implement `PrivateMemberExtractor` with `extract_top_level_functions()` and `extract_private_members()`. Rust support is complete (194 LOC implementation at `private_members/rust.rs`).

**Affected files (all generated from tools.toml):**
- `crates/fmm-cli/tools.toml:304` (mcp_description)
- `crates/fmm-cli/tools.toml:318` (include_private mcp_description)
- `crates/fmm-cli/src/mcp/generated_schema.rs:108` (generated)
- `crates/fmm-cli/src/mcp/generated_schema.rs:118` (generated)
- `crates/fmm-cli/templates/SKILL.md:267` (generated)

**Severity: HIGH** — agents reading the MCP tool description will skip `include_private: true` on Rust files, missing private members and non-exported functions.

---

### 2. HIGH: CLI help text says "9 tools", actual count is 8

**Currently says:** `"Start MCP server (9 tools for LLM navigation)"` and `"The MCP config enables 9 tools"`

**Actual count:** 8 tools registered in `generated_schema.rs` and dispatched in `mcp/mod.rs`:
1. `fmm_lookup_export`
2. `fmm_list_exports`
3. `fmm_dependency_graph`
4. `fmm_read_symbol`
5. `fmm_file_outline`
6. `fmm_search`
7. `fmm_list_files`
8. `fmm_glossary`

**Note:** The README correctly says "8 tools" (line 76 and 84). The discrepancy is CLI-only.

**Affected files:**
- `crates/fmm-cli/src/cli/help_text.rs:23` — `"Start MCP server (9 tools for LLM navigation)"`
- `crates/fmm-cli/src/cli/help_text.rs:48` — same string, repeated in long help
- `crates/fmm-cli/src/cli/mod.rs:240` — `"The MCP config enables 9 tools"`
- `crates/fmm-cli/src/cli/mod.rs:584` — `"Start MCP server — 9 tools for LLM code navigation"`
- `crates/fmm-cli/src/cli/mod.rs:587` — `"Exposes 9 tools that LLM agents..."`

**Severity: HIGH** — users may think a tool is missing from their setup. The `fmm mcp --help` long_about correctly lists 8 tools by name (lines 592-599), contradicting its own short description.

---

### 3. HIGH: `fmm generate` help text lists only 9 of 18 languages

**File:** `crates/fmm-cli/src/cli/mod.rs:90`

**Currently says:** `"Supports: TypeScript, JavaScript, Python, Rust, Go, Java, C++, C#, Ruby."`

**Missing 9 languages:** PHP, C, Swift, Kotlin, Dart, Elixir, Lua, Scala, Zig

All 18 languages are registered in `ParserRegistry::register_builtin()` (`crates/fmm-core/src/parser/mod.rs:246-277`). All have working parsers confirmed by tests.

**Severity: HIGH** — users with PHP, Kotlin, Swift, Dart, etc. codebases will not try fmm, thinking it is unsupported.

---

### 4. HIGH: CLI `--help` Languages section lists only 9 of 18

**File:** `crates/fmm-cli/src/cli/help_text.rs:73`

**Currently says:** `"TypeScript · JavaScript · Python · Rust · Go · Java · C++ · C# · Ruby"`

**Missing:** Same 9 languages as #3 above.

**Severity: HIGH** — this is the primary `fmm --help` output. Same impact as #3.

---

### 5. MEDIUM: `fmm_read_symbol` examples use `.ts` exclusively

**Source:** `crates/fmm-cli/tools.toml:277-285` (propagates to generated_schema.rs, generated_help.rs, SKILL.md)

**Currently says:**
- MCP param description: `"path/to/file.ts:helperFn to read a non-exported top-level function"`
- CLI about: `"path/to/file.ts:helperFn notation"`
- CLI help: `"path/to/file.ts:fn for a non-exported function"`

**Should say:** `"path/to/file.ext:helperFn"` or use a language-neutral example like `"path/to/file:helperFn"`. The colon notation works for any language with a `PrivateMemberExtractor` (TS, JS, Python, Rust). Agents working on Rust or Python files see `.ts`-only examples and may not realize the feature is available.

**Severity: MEDIUM** — not incorrect (`.ts` is a valid example), but incomplete and subtly steers agents toward TS-only usage.

---

### 6. MEDIUM: Internal doc comment "TS/JS only" on `function_names` field is stale

**File:** `crates/fmm-core/src/manifest/mod.rs:47`

**Currently says:** `"Names of exported module-level function declarations (TS/JS only)."`

**Actual:** Python parser (`python/mod.rs:401-484`) and Rust parser (`rust/metadata.rs:144`, `rust/mod.rs:181-246`) both populate `function_names` via `extract_function_names()`. Confirmed by tests (`python/tests.rs:591-645`, `rust/tests.rs:906-959`).

**Should say:** `"Names of exported module-level function declarations (TS/JS, Python, Rust)."`

**Severity: MEDIUM** — internal code comment, but a developer extending the system would wrongly assume this field is unavailable for Rust/Python.

---

### 7. MEDIUM: Internal doc comment "TS/JS only" on `named_imports` field (manifest) is stale

**File:** `crates/fmm-core/src/manifest/mod.rs:52`

**Currently says:** `"Named imports per source module (TS/JS only)."`

**Actual:** Rust parser populates `named_imports` and `namespace_imports` (`rust/extract_imports.rs:169-175`, `rust/mod.rs:176,261-262`). Python parser does the same (`python/mod.rs:287-292,449-501`). Both have extensive test coverage.

**Should say:** `"Named imports per source module (TS/JS, Python, Rust)."`

**Severity: MEDIUM** — same reasoning as #6.

---

### 8. MEDIUM: Internal doc comment "TS/JS only" on `named_imports` field (parser types) is stale

**File:** `crates/fmm-core/src/parser/mod.rs:145`

**Currently says:** `"Named imports per source module (TS/JS only)."`

**Same fix as #7.** This is the `Metadata` struct in the parser module; manifest's `FileEntry` has the same stale comment.

**Severity: MEDIUM** — internal, but misleading for contributors.

---

### 9. MEDIUM: `fmm_dependency_graph` test file examples are TS-centric

**Source:** `crates/fmm-cli/tools.toml:271`

**Currently says:** `"'source': exclude test files (*.spec.ts, *.test.ts, /test/, etc.)"`

This is not wrong since it lists other patterns too, but the emphasis on `.spec.ts` and `.test.ts` obscures that Rust (`_test.rs`), Go (`_test.go`), Python (`test_*.py`), and other language-specific patterns are also supported. The `fmm_list_files` description (line 437) does better, mentioning `_test.go` alongside `.spec.ts`.

**Severity: MEDIUM** — incomplete, could cause agents to assume test detection is JS-only.

---

### 10. MEDIUM: SKILL.md workflow examples are entirely TypeScript-centric

**Source:** `crates/fmm-cli/tools.toml` skill section (lines 1-191)

All workflow examples reference TypeScript paths and patterns:
- `fmm_file_outline(file: "src/foo.ts")` (line 31, 83)
- `fmm_read_symbol("src/foo.ts:helperFn")` (line 40)
- `fmm_dependency_graph(file: "src/injector.ts")` (line 51, 173)
- `fmm_search(depends_on: "src/core/injector.ts")` (line 121)

While a `.ts` example works for illustration, agents working on Rust/Python/Go codebases receive a skill document with zero examples in their language.

**Severity: MEDIUM** — does not prevent functionality, but the complete absence of non-TS examples reinforces a TS-centric mental model.

---

### 11. LOW: `fmm_read_symbol` description says "function, class, type, component"

**Source:** `crates/fmm-cli/tools.toml:284` (mcp_description for `name` param)

**Currently says:** `"Exact export name to read (function, class, type, component)"`

For Rust, the valid export types include `struct`, `enum`, `trait`, `impl`, `mod`, and `macro`. The term "component" is React-specific. This is not incorrect (it is an illustrative list), but a Rust developer might wonder if their `pub struct` is findable.

**Severity: LOW** — illustrative, not exhaustive. No functional impact.

---

### 12. LOW: `fmm_lookup_export` description says "function, class, type, variable, component"

**Source:** `crates/fmm-cli/tools.toml:203`

Same issue as #11. Rust-specific terms (struct, enum, trait, impl) are absent from the illustrative list.

**Severity: LOW** — same reasoning as #11.

---

### 13. LOW: `fmm mcp --help` long_about lists 8 tools but short help says 9

**File:** `crates/fmm-cli/src/cli/mod.rs:584-599`

The `/// Start MCP server — 9 tools for LLM code navigation` doc comment and `long_about` text both say "9 tools", but the tool list in `after_long_help` (lines 592-599) correctly enumerates exactly 8 tools. These are on the same command definition, contradicting each other within the same `--help` output.

**Severity: LOW** — confusing but the enumerated list is authoritative.

---

### 14. LOW: Call-site finder claims "all supported languages" in fallback docs

**File:** `crates/fmm-core/src/manifest/call_site_finder/mod.rs:79`

**Currently says:** `"a valid identifier in all supported languages"`

Call-site verification is only implemented for TypeScript, Python, and Rust (verifiers at line 64-69). Other languages get the fallback path (included as true, no false negatives). This is technically correct but could confuse a developer reading the code who assumes "all supported languages" means 18.

**Severity: LOW** — internal doc, fallback semantics are safe.

---

## Language Support Feature Matrix

Based on implementation analysis, here is the actual feature matrix across the three tiers:

| Feature | TypeScript/JS | Python | Rust | Go + 14 others |
|---------|:---:|:---:|:---:|:---:|
| Exports (indexed) | Yes | Yes | Yes | Yes |
| Imports (indexed) | Yes | Yes | Yes | Yes |
| Dependencies (indexed) | Yes | Yes | Yes | Yes |
| LOC (indexed) | Yes | Yes | Yes | Yes |
| Named imports | Yes | Yes | Yes | No |
| Namespace imports | Yes | Yes | Yes | No |
| Function names | Yes | Yes | Yes | No |
| Private members (include_private) | Yes | Yes | Yes | No |
| Top-level functions (include_private) | Yes | Yes | Yes | No |
| Call-site verification | Yes | Yes | Yes | No (fallback: included) |
| Methods index | Yes | Yes | Yes | Yes* |

*Methods index depends on parser emitting `ExportEntry::method()`. Check per-language.

## Recommended Fix Approach

All high-severity items trace to **`crates/fmm-cli/tools.toml`** as the single source of truth. The build system generates `generated_schema.rs`, `generated_help.rs`, and `templates/SKILL.md` from this file. Fixing `tools.toml` and re-running `cargo build` propagates corrections to all three generated outputs.

For the CLI help text (`help_text.rs` and `mod.rs`), these are hand-maintained and require manual edits.

**Priority order:**
1. Fix tool count: "9 tools" to "8 tools" in `help_text.rs` and `mod.rs` (5 locations)
2. Fix `include_private` language list in `tools.toml` (2 locations): add "Rust"
3. Fix `fmm generate` language list in `mod.rs:90`: add all 18 languages
4. Fix `--help` Languages line in `help_text.rs:73`: add all 18 languages
5. Fix "TS/JS only" comments in `manifest/mod.rs` and `parser/mod.rs` (3 locations)
6. Consider adding polyglot examples to SKILL.md workflow section

## Open Questions

1. Should the language lists in help text be auto-generated from the `ParserRegistry` descriptors rather than maintained by hand? This would prevent future drift when new languages are added.
2. The `include_private` language list will grow as new `PrivateMemberExtractor` implementations are added. Should the description use a dynamic phrasing like "Supported for languages with tree-sitter extractors" instead of enumerating?
3. Should the SKILL.md examples include at least one Rust and one Python example alongside TS to signal polyglot support?
