---
title: 'fmm Roadmap: Symbols, body_loc, and Complexity Spec'
type: spec
tags: [fmm, roadmap, symbols, body_loc, complexity, mcp, json-contract]
summary: Adds a repo wide symbol query, body_loc, and phased complexity metrics for later fmm health work.
status: draft
source: backend-engineer
confidence: medium
repo: /Users/alphab/Dev/LLM/DEV/helioy/fmm
head: 5f8a1296d72f507a2e4bd1950001a442dc6b31fc
fmm_version: 0.3.6
created: 2026-06-17
updated: 2026-06-17
inputs:
  - ~/.mdx/projects/fmm-roadmap-spec-foundations.md
  - ~/.mdx/projects/fmm-eval-claude--brainstorm.md
---

# fmm Symbols, body_loc, and Complexity Metrics Spec

This spec covers three related capabilities:

1. `body_loc`: a stored line count for every indexed symbol with a valid line range.
2. `fmm symbols` and MCP `fmm_list_symbols`: a repo wide symbol query for long function detection and targeted architecture audits.
3. Complexity metrics: a phased parser backed metric set consumed later by `fmm health`.

`fmm health` is only a consumer. This spec does not design the health command.

## Foundation dependency

This spec inherits the canonical foundation rules from `~/.mdx/projects/fmm-roadmap-spec-foundations.md`:

- JSON output is wrapped in the approved report envelope. This spec defines only the `results` payload for symbols.
- `--json` emits the envelope directly.
- `tools.toml` remains the single source of truth for MCP schema, CLI help, and generated skill docs.
- Deterministic output is mandatory: sorted params, stable ordering, and stable tie breakers.
- The live index is regeneratable. Changing the live `exports` and `methods` tables bumps `SCHEMA_VERSION`.
- The separate snapshot database is not part of this work and must not be changed by this spec.

## Current state and gap

The evaluation note confirms the current health gap: fmm has file level LOC, symbol line ranges, visibility, kind, and signatures, but no stored symbol size or complexity metrics. The `exports` and `methods` tables already carry `start_line` and `end_line`, so `body_loc` is nearly free.

Current code shape:

- `crates/fmm-core/src/parser/types.rs` `ExportEntry`: parser result symbol shape with `start_line`, `end_line`, `signature`, `visibility`, `declaration_kind`, `parent_class`, and `relationship_kind`.
- `crates/fmm-core/src/parser/types.rs` `Metadata`: file parse output carrying `Vec<ExportEntry>`.
- `crates/fmm-core/src/extractor/mod.rs` `FileProcessor.parse_content`: extracts source text and delegates to parser registry.
- `crates/fmm-core/src/parser/builtin/symbol_metadata.rs` `export_entry_from_source` and `method_entry_from_source`: shared helpers that create symbols from tree sitter nodes.
- `crates/fmm-core/src/types.rs` `ExportRecord`, `MethodRecord`, and `serialize_file_data_inner`: stored row structs and parser to store conversion.
- `crates/fmm-store/src/schema.rs` `CREATE_SCHEMA_SQL`: live SQLite tables. `exports` and `methods` persist line ranges, signatures, visibility, and kind.
- `crates/fmm-store/src/writer.rs` `upsert_file_data` and `upsert_preserialized_with_file_id`: write export and method rows.
- `crates/fmm-store/src/reader/exports.rs` `load_exports` and `load_methods`: load symbol rows back into `Manifest`.
- `crates/fmm-core/src/manifest/file_entry.rs` `FileEntry` and `SymbolMetadata`: in memory representation used by CLI and MCP tools.
- `crates/fmm-cli/tools.toml` plus `crates/fmm-cli/build.rs` `generate_mcp_schema`, `generate_cli_help`, and `generate_skill_md`: generated tool surface.
- `crates/fmm-cli/src/mcp/mod.rs` `McpServer.handle_tool_call`: MCP dispatch table.
- `crates/fmm-cli/src/cli/mod.rs` `Commands` and `crates/fmm-cli/src/main.rs` `run_command`: CLI command registration and dispatch.

## Data model

### Core types

Add a shared metrics struct in `crates/fmm-core/src/parser/types.rs`:

```rust
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct SymbolMetrics {
    pub body_loc: Option<u32>,
    pub param_count: Option<u16>,
    pub cyclomatic_complexity: Option<u16>,
    pub nesting_depth: Option<u16>,
    pub branch_count: Option<u16>,
    pub match_arm_count: Option<u16>,
}
```

Add `pub metrics: SymbolMetrics` to `ExportEntry`. The constructors `ExportEntry::new`, `ExportEntry::method`, `ExportEntry::nested_fn`, and `ExportEntry::closure_state` compute `body_loc` once through a helper:

```rust
impl SymbolMetrics {
    pub fn from_line_range(start_line: usize, end_line: usize) -> Self {
        let body_loc = if start_line > 0 && end_line >= start_line {
            u32::try_from(end_line - start_line + 1).ok()
        } else {
            None
        };
        Self { body_loc, ..Self::default() }
    }
}
```

This avoids copying a body line calculation into every parser. Every existing parser that produces valid symbol ranges gets `body_loc` automatically.

Add `metrics: SymbolMetrics` to:

- `crates/fmm-core/src/types.rs` `ExportRecord`
- `crates/fmm-core/src/types.rs` `MethodRecord`
- `crates/fmm-core/src/manifest/file_entry.rs` `SymbolMetadata`
- `crates/fmm-store/src/memory_store/state.rs` `StoredExport`
- `crates/fmm-store/src/memory_store/state.rs` `StoredMethod`

`SymbolMetadata::from_parts` should accept metrics, or gain a sibling constructor such as `from_entry_parts`. Prefer the constructor change if the call sites are mechanical after `fmm_glossary` confirms blast radius.

### Live SQLite schema

Bump `crates/fmm-store/src/schema.rs` `SCHEMA_VERSION` from `6` to `7`.

Add nullable nonnegative metric columns to both `exports` and `methods` in `CREATE_SCHEMA_SQL`:

```sql
body_loc INTEGER CHECK (body_loc IS NULL OR body_loc >= 0),
param_count INTEGER CHECK (param_count IS NULL OR param_count >= 0),
cyclomatic_complexity INTEGER CHECK (cyclomatic_complexity IS NULL OR cyclomatic_complexity >= 0),
nesting_depth INTEGER CHECK (nesting_depth IS NULL OR nesting_depth >= 0),
branch_count INTEGER CHECK (branch_count IS NULL OR branch_count >= 0),
match_arm_count INTEGER CHECK (match_arm_count IS NULL OR match_arm_count >= 0)
```

`body_loc` is nullable because the table permits nullable line ranges. New parser rows should populate it when the symbol has a valid range.

Add only the indexes needed for likely query paths:

```sql
CREATE INDEX IF NOT EXISTS idx_exports_body_loc ON exports(body_loc);
CREATE INDEX IF NOT EXISTS idx_methods_body_loc ON methods(body_loc);
CREATE INDEX IF NOT EXISTS idx_methods_file ON methods(file_path);
```

Do not add broad composite indexes in v1. The CLI and MCP surface can query the loaded `Manifest`, and these three indexes cover future store backed filtering without over indexing writes.

### Snapshot database

No changes. The snapshot database belongs to the foundation snapshot work. If foundations lands before this spec, its live row copy code must copy the new live columns into snapshot rows in that separate spec, but this spec does not alter `.fmm-snapshots.db`.

## Extractor and parser wiring

### `body_loc`

`body_loc` is computed from the same start and end range that fmm already indexes:

- `crates/fmm-core/src/parser/builtin/symbol_metadata.rs` `export_entry_from_source`
- `crates/fmm-core/src/parser/builtin/symbol_metadata.rs` `method_entry_from_source`
- `crates/fmm-core/src/parser/builtin/query_helpers.rs` `push_export`
- Language specific code that calls `ExportEntry::new` or `ExportEntry::method`

Because the `ExportEntry` constructors compute the value, most language parsers need no dedicated `body_loc` edits.

### `param_count`

`param_count` is the first complexity adjacent metric after `body_loc` because it is cheap and stable when the parser still has the tree sitter node. It should be populated only for symbol kinds where parameters are meaningful: `fn`, `method`, and equivalent language function declarations.

Implementation shape:

- Add a setter such as `ExportEntry::with_param_count(self, value: Option<u16>) -> Self` or mutate `entry.metrics.param_count` in language metadata helpers.
- For Rust, add `param_count_for` in `crates/fmm-core/src/parser/builtin/rust/symbol_metadata.rs` and call it from `rust_entry` and `rust_method_entry` when the declaration kind is `Fn` or `Method`.
- For TypeScript and Python, follow the existing language specific `symbol_metadata.rs` files and add tests beside existing outline metadata tests.
- For other languages, leave `param_count` as `null` until each grammar has parser tests. Do not infer by parsing signature strings.

String parsing of signatures is explicitly rejected for v1 because it will be inaccurate for generics, default values, destructuring, nested types, and multiline signatures.

### Later complexity metrics

These are parser backed and language specific:

- `cyclomatic_complexity`: count decision points plus one. Branch nodes differ by grammar.
- `nesting_depth`: maximum nested control flow depth in the symbol body.
- `branch_count`: count `if`, loop, catch, conditional, and equivalent branch nodes.
- `match_arm_count`: count Rust `match` arms and equivalent switch or pattern arms where a language has them.

They should land after `body_loc` and `param_count`, language by language, with parser tests per grammar. Null means unsupported for that parser or symbol kind.

## Store wiring

Update the serialization path once and keep SQLite and memory stores aligned:

1. `crates/fmm-core/src/types.rs` `serialize_file_data_inner`: copy `ExportEntry.metrics` into `ExportRecord` and `MethodRecord`.
2. `crates/fmm-store/src/writer.rs` `upsert_file_data`: insert metric columns for direct parse writes.
3. `crates/fmm-store/src/writer.rs` `upsert_preserialized_with_file_id`: insert metric columns for batch and watch writes.
4. `crates/fmm-store/src/reader/exports.rs` `load_exports`: select metric columns and build `SymbolMetadata` with metrics.
5. `crates/fmm-store/src/reader/exports.rs` `load_methods`: same for methods, nested functions, and closure state rows.
6. `crates/fmm-store/src/memory_store/state.rs` `InnerState.ingest_row`: preserve metrics in `StoredExport` and `StoredMethod`.
7. `crates/fmm-store/src/memory_store/manifest.rs` `populate_exports` and `populate_methods`: copy metrics into manifest metadata.

Round trip tests must cover SQLite and in memory stores.

## Symbol query surface

Add a new command instead of extending `exports`. `exports` remains discovery by name. `symbols` is a structured repo wide query for density and health signals.

### CLI

Command:

```bash
fmm symbols [--kind <kind>] [--min-lines <n>] [--max-lines <n>] [--visibility <visibility>] [--directory <path>] [--limit <n>] [--offset <n>] [--sort-by <field>] [--order <asc|desc>] [--json]
```

Filters:

- `--kind`: values from `DeclarationKind::as_str`, for example `fn`, `method`, `struct`, `trait`, `impl`, `enum`, `type`, `const`, `field`, `module`, `macro`, `test`.
- `--min-lines`: inclusive lower bound on `body_loc`.
- `--max-lines`: inclusive upper bound on `body_loc`.
- `--visibility`: `public`, `crate`, `protected`, `private`, or `non_exported`.
- `--directory`: file path prefix.
- `--limit`: default 200.
- `--offset`: default 0.
- `--sort-by`: `size` default, `name`, `file`, `kind`, `visibility`, `downstream`.
- `--order`: default `desc` for `size` and `downstream`, otherwise `asc`.

Text output should be compact and deterministic:

```text
name                                      file                              lines   size  kind    visibility  downstream
RustParser.parse_inner                    crates/fmm-core/src/parser/...     154-270 117   method  private     0
```

`size` is the user facing label for `body_loc`.

### MCP

Add `fmm_list_symbols` to `crates/fmm-cli/tools.toml` so `build.rs` regenerates the MCP schema, CLI help, and skill docs.

MCP params mirror the CLI names, with `directory`, `kind`, `min_lines`, `max_lines`, `visibility`, `limit`, `offset`, `sort_by`, and `order`.

Add dispatch in `crates/fmm-cli/src/mcp/mod.rs` `McpServer.handle_tool_call`, module exports in `crates/fmm-cli/src/mcp/tools/mod.rs`, and implementation in a new `crates/fmm-cli/src/mcp/tools/symbols.rs`.

## Shared implementation seam

Create one shared query module so CLI and MCP cannot drift:

- `crates/fmm-core/src/symbols.rs` or `crates/fmm-cli/src/symbols.rs` if the result type should stay CLI local.
- Prefer core if later `fmm health` will compose the same query.

Suggested types:

```rust
pub struct SymbolQuery {
    pub directory: Option<String>,
    pub kind: Option<String>,
    pub min_lines: Option<u32>,
    pub max_lines: Option<u32>,
    pub visibility: Option<String>,
    pub limit: usize,
    pub offset: usize,
    pub sort_by: SymbolSort,
    pub order: SortOrder,
}

pub struct SymbolRow {
    pub name: String,
    pub file: String,
    pub lines: Option<ExportLines>,
    pub body_loc: Option<u32>,
    pub signature: Option<String>,
    pub visibility: Option<String>,
    pub kind: Option<String>,
    pub downstream_count: usize,
    pub relationship_kind: Option<String>,
    pub metrics: SymbolMetrics,
}
```

Collect from `Manifest.files` so CLI and MCP use the same loaded index path as existing commands. Include top level exports, methods, nested functions, and closure state. `relationship_kind` disambiguates method, nested function, and closure state rows.

`downstream_count` is file level blast radius from `Manifest.reverse_deps` for the row file. This matches existing fmm file level dependency semantics.

Stable ordering:

1. Primary requested sort.
2. File path ascending.
3. Start line ascending, missing line ranges last.
4. Symbol name ascending.

## JSON results payload

The full output is the foundation envelope. This spec defines `results` only:

```jsonc
{
  "summary": {
    "total": 417,
    "returned": 200,
    "offset": 0,
    "limit": 200
  },
  "symbols": [
    {
      "name": "RustParser.parse_inner",
      "file": "crates/fmm-core/src/parser/builtin/rust/mod.rs",
      "lines": { "start": 154, "end": 270 },
      "size": 117,
      "signature": "fn parse_inner(&mut self, source: &str, binary_crate: bool) -> Result<ParseResult>",
      "visibility": "private",
      "kind": "method",
      "relationship_kind": null,
      "downstream_count": 9,
      "metrics": {
        "body_loc": 117,
        "param_count": 2,
        "cyclomatic_complexity": null,
        "nesting_depth": null,
        "branch_count": null,
        "match_arm_count": null
      }
    }
  ]
}
```

`size` is an alias in the result payload for `metrics.body_loc`, included because the CLI and existing outline language already use size. The canonical metric remains `body_loc`.

## Traceability

| Field or surface | Source of truth |
| --- | --- |
| Symbol range | `crates/fmm-core/src/parser/types.rs` `ExportEntry` |
| Automatic `body_loc` | `crates/fmm-core/src/parser/types.rs` `SymbolMetrics::from_line_range` |
| Rust parameter count | `crates/fmm-core/src/parser/builtin/rust/symbol_metadata.rs` `rust_entry`, `rust_method_entry` |
| Shared tree sitter symbol creation | `crates/fmm-core/src/parser/builtin/symbol_metadata.rs` `export_entry_from_source`, `method_entry_from_source` |
| Parser entry point | `crates/fmm-core/src/extractor/mod.rs` `FileProcessor.parse_content` |
| Parser result conversion | `crates/fmm-core/src/types.rs` `serialize_file_data_inner` |
| Stored export row | `crates/fmm-core/src/types.rs` `ExportRecord` |
| Stored method row | `crates/fmm-core/src/types.rs` `MethodRecord` |
| SQLite schema | `crates/fmm-store/src/schema.rs` `CREATE_SCHEMA_SQL`, `SCHEMA_VERSION` |
| SQLite writes | `crates/fmm-store/src/writer.rs` `upsert_file_data`, `upsert_preserialized_with_file_id` |
| SQLite reads | `crates/fmm-store/src/reader/exports.rs` `load_exports`, `load_methods` |
| In memory store | `crates/fmm-store/src/memory_store/state.rs` `InnerState.ingest_row` |
| Manifest metadata | `crates/fmm-core/src/manifest/file_entry.rs` `SymbolMetadata`, `FileEntry` |
| CLI command enum | `crates/fmm-cli/src/cli/mod.rs` `Commands` |
| CLI dispatch | `crates/fmm-cli/src/main.rs` `run_command` |
| MCP dispatch | `crates/fmm-cli/src/mcp/mod.rs` `McpServer.handle_tool_call` |
| Tool docs and schema | `crates/fmm-cli/tools.toml`, `crates/fmm-cli/build.rs` `generate_mcp_schema`, `generate_cli_help`, `generate_skill_md` |

## Tests and verification gate

Use repo convention from the foundation spec:

```bash
just check
just test
```

Required tests:

1. Parser constructor test: `ExportEntry::new` and `ExportEntry::method` compute `body_loc` from valid line ranges and return `None` for invalid ranges.
2. Store schema test: `SCHEMA_VERSION` is bumped and new columns exist on `exports` and `methods`.
3. SQLite round trip: write a symbol with metrics through `upsert_preserialized_with_file_id`, load it with `load_manifest_from_db`, and assert metrics survive for exports and methods.
4. Memory store round trip: same assertion through `InMemoryStore`.
5. CLI symbols text: fixture with a long function returns deterministic rows sorted by `size desc` by default.
6. CLI symbols JSON: `--json` emits the foundation envelope and the `results.symbols` payload above.
7. MCP `fmm_list_symbols`: filters by `kind`, `min_lines`, `max_lines`, `visibility`, and `directory` match CLI output over the same fixture.
8. Rust `param_count`: Rust functions and impl methods populate counts; non function declarations remain null.
9. Null safety: languages without `param_count` support still emit rows with `metrics.param_count: null` and do not fail filtering by lines.

## Build order

1. Core metrics struct and `body_loc` constructor wiring.
2. Store row structs, SQLite schema bump, writer, reader, memory store, and round trip tests.
3. Shared `SymbolQuery` and `SymbolRow` collector over `Manifest`.
4. CLI `fmm symbols` text output and tests.
5. JSON payload inside the foundation envelope.
6. MCP `fmm_list_symbols` through `tools.toml`, generated schema, dispatch, and tests.
7. Rust `param_count` parser support and tests.
8. TypeScript and Python `param_count` parser support, then other languages as grammar tests are added.
9. Later complexity metrics language by language.

## Open questions

1. Should Phase 1 require `param_count` coverage for every builtin language, or may unsupported grammars return `null` until each parser has tests?
2. Should the JSON payload keep both `size` and `metrics.body_loc`, or should `size` be text only and JSON expose only `body_loc`?
3. Should `fmm symbols --kind` accept only exact enum values, or also aliases such as `function` for `fn`?
