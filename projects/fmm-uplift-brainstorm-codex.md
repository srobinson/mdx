# fmm uplift brainstorm, Codex pass

Validated against fmm 0.2.9 source, plus live CLI runs on fmm, context-matters, and littleorgans. fmm and context-matters validated clean. littleorgans exposed a useful freshness gap: 35 stale or missing files.

## Top 5 wins

### 1. Add `signature` to `fmm_file_outline`

**Problem.** Outline is excellent for location, weak for decision making. Real output for `crates/cm-cli/tests/mcp_protocol/tool_calls.rs` shows only names plus `[start, end]`, so an agent cannot distinguish fixture helpers, async tests, generic methods, or return shapes without reading source. The formatter currently emits only name, line range, size, and member counts (`crates/fmm-core/src/format/yaml_formatters.rs:100-146`). The indexed export model has name and lines only (`crates/fmm-core/src/parser/types.rs:49-63`).

**Proposed change.** Add an optional `signature` string to `ExportEntry` and method records, populated from the same tree-sitter node slice already found during export extraction. Render it in outline, for example `protocol_store_and_recall_roundtrip(): [539, 634] # 96 lines` or Rust `pub fn new() -> Result<Self>`.

**Expected payoff.** Avoids many follow-up `fmm_read_symbol` calls. The example complaint is solved directly.

**Rough cost.** Storage: one short string per export or method. For fmm's 399 files and 57k LOC, likely low single digit MB. Query latency: no extra join if carried with export rows. Indexing: substring slice per exported symbol.

**Risk.** Multi-language signatures vary. Start with Rust, TS, Python, JS, then fall back to current output.

### 2. Surface custom fields or retire most of them

**Problem.** Parsers compute rich custom fields, but the durable schema stores only `function_names` (`crates/fmm-store/src/schema.rs:95-110`). Rust computes `unsafe_blocks`, `derives`, `trait_impls`, `lifetimes`, and `async_functions` (`crates/fmm-core/src/parser/builtin/rust/mod.rs:183-253`), yet `ParseResult.metadata` discards all but fields copied to `function_names` during write (`crates/fmm-store/src/writer.rs:124-162`). The README promises custom fields, but agents cannot query most of them.

**Proposed change.** Pick one: persist a compact `custom_fields` JSON column on `files`, or remove non-consumed custom field claims from user facing docs. If persisted, expose it in `fmm_file_outline` and `fmm_search --custom key=value` only when requested.

**Expected payoff.** Rust trait impls, decorators, annotations, and unsafe counts become real navigation signals. If removed, the product becomes simpler and more honest.

**Rough cost.** JSON column only for files with data. Query latency unchanged unless requested. Indexing already pays extraction cost.

**Risk.** A generic custom field surface can become junk drawer. Keep it file scoped, opt in, and documented per language.

### 3. Add `why` edges to dependency graph

**Problem.** `fmm deps crates/fmm-core/src/manifest/mod.rs` produced 60 downstream paths, but not the exact import or symbol that caused each edge. Agents still grep to answer “why does this depend on me?” The schema stores dependency paths and reverse deps, but reverse edges store only target and source (`crates/fmm-store/src/schema.rs:146-152`). Named imports exist on `FileEntry` (`crates/fmm-core/src/manifest/file_entry.rs:36-43`) and `Metadata` (`crates/fmm-core/src/parser/types.rs:127-136`).

**Proposed change.** Add an optional `explain: true` mode to `fmm_dependency_graph` that annotates each downstream edge with matched import specifier and named imports when available.

**Expected payoff.** Turns blast radius from a path list into an action plan.

**Rough cost.** No default cost. Explain mode performs per-edge lookup against already loaded `named_imports` and dependency metadata. For large closures, cap and paginate.

**Risk.** Import resolution can be ambiguous. Label entries `resolved_from` and `specifier` rather than pretending perfect semantic resolution.

### 4. Add a single planning query: `fmm_context_pack`

**Problem.** For unfamiliar modules, an agent usually calls `fmm_list_files`, `fmm_file_outline`, `fmm_dependency_graph`, and maybe `fmm_glossary`. The tool surface is good, but the common workflow is still multi call. `McpServer.handle_tool_call` dispatches isolated tools only (`crates/fmm-cli/src/mcp/mod.rs:306-321`).

**Proposed change.** Add one MCP only tool that returns a budgeted pack for a file or directory: local topology, top exports, outline, direct deps, top downstream dependents, tests if detected, and freshness status.

**Expected payoff.** Better first response for LLM agents with fewer round trips and less prompt thrash.

**Rough cost.** Query cost equals existing calls, but amortized in one server path. No schema cost. Add a strict token budget and section caps.

**Risk.** Could become another dashboard. Keep it read only, opinionated, and compositional over existing functions.

### 5. Make freshness visible in every structural answer

**Problem.** fmm and context-matters validated clean, but littleorgans had 35 stale or missing files. Normal `fmm ls` still returned indexed results without warning. Agents can unknowingly navigate stale state.

**Proposed change.** Add a cheap index freshness bit to `status`, `ls`, and MCP tool responses when stale files are known. Store a last validation summary or run bounded mtime checks for touched paths.

**Expected payoff.** Prevents false confidence, especially in active worktrees.

**Rough cost.** Full validation can be expensive, so do not run it on every query. Use per requested path mtime checks or cached validation metadata.

**Risk.** Freshness checks can silently become latency tax. Make deep validation explicit, cheap warnings default.

## Secondary ideas

Add result pagination to `fmm_glossary`; large named import output can swamp the useful part, as `ContextStore` did in context-matters. Add `sort_by=downstream|loc|modified` to glossary definitions and consumers. Add `tests_for` links by matching test file paths and imports, so dependency graph can answer coverage directly. Add `language` and parser maturity to `fmm_list_files` rows. Add `kind` to outline rows, such as function, struct, trait, test, const. Add re-export chain depth to lookup and read, not just dereferenced origin. Add JSON schemas for every CLI JSON response and snapshot them. Add `direct_only` to search depends-on to avoid the current mental split between search and deps. Add output presets: `brief`, `normal`, `agent`. Add a `stale` filter to list files.

## Dead weight / simplification candidates

The non persisted custom fields are the biggest simplification candidate if Stuart does not want to expose them. They create tests and parser work without user value. The separate CLI and MCP command implementations also look duplicative at the behavior boundary; keep separate argument shells, but drive both from shared query structs. The `external` list in dependency graph includes internal crate style strings such as `crate::parser`, which blurs package deps and unresolved local deps in agent output.

## Open questions

Should fmm optimize for terse YAML first or richer JSON first? Should signature extraction become schema backed, or should outline compute it on demand from source for zero index bloat? Does Stuart want custom fields to become first class product surface, or were they parser validation scaffolding? Should freshness be strict by default in MCP, or merely warned?

## Performance ledger

| Rank | Proposal | Storage delta | Query delta | Index delta | Risk |
|---:|---|---:|---:|---:|---|
| 1 | Outline signatures | Short string per symbol | none if indexed | substring per symbol | Language inconsistency |
| 2 | Custom fields surface | sparse JSON per file | none unless requested | already paid | Junk drawer |
| 3 | Dependency `why` edges | none default | per edge lookup in explain mode | none | Ambiguous imports |
| 4 | `fmm_context_pack` | none | sum of existing queries | none | Dashboard creep |
| 5 | Freshness warnings | optional cached summary | bounded mtime checks | none | Latency creep |
