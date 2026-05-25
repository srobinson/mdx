---
title: fmm MCP Tool Error Semantics
type: research
tags: [fmm, mcp, errors, rust, helioy]
summary: fmm MCP tool failures use a flat ERROR text envelope, but many messages are specific and recovery oriented.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Executive Summary

The claim that every fmm MCP tool failure returns a generic error is false as worded. Tool failures do share a flat text envelope prefixed with `ERROR:`, but the message body often contains specific diagnostics, recovery commands, and in `fmm_read_symbol` member suggestions.

## Project Metadata

- Language: Rust, edition 2024.
- Build system: Cargo workspace at `fmm/Cargo.toml`.
- Crates: `fmm` CLI and MCP server, `fmm-core` parser and search logic, `fmm-store` SQLite persistence.
- Package: CLI crate is named `fmm` in `crates/fmm-cli/Cargo.toml`.
- Critical dependencies: `serde`, `serde_json`, `clap`, `rusqlite`, `thiserror`, `anyhow`, `regex`, `glob`, and tree sitter parser crates.
- Index status: `.fmm.db` exists at repo root. `fmm validate` reported all 410 files indexed and current on 2026-05-28.

## Architecture

The MCP server lives in `crates/fmm-cli/src/mcp/mod.rs`. It handles JSON RPC framing, reloads the SQLite backed manifest before `tools/call`, dispatches tool names to `crates/fmm-cli/src/mcp/tools/*`, then wraps tool output as MCP text content.

Key paths:

- JSON RPC structures and dispatch: `crates/fmm-cli/src/mcp/mod.rs:49-74`, `231-364`.
- Tool argument structs: `crates/fmm-cli/src/mcp/args.rs:4-87`.
- Shared MCP diagnostics: `crates/fmm-cli/src/mcp/tools/common.rs:80-106`.
- `fmm_read_symbol` guidance: `crates/fmm-cli/src/read_symbol.rs:43-180` and `crates/fmm-cli/src/read_symbol/member_error.rs:60-106`.
- Tests for MCP tool errors: `crates/fmm-cli/src/mcp/tests/tool_errors.rs:6-39`, `crates/fmm-cli/src/mcp/tests/read_symbol.rs:230-267`, and `crates/fmm-cli/tests/mcp_protocol.rs:209-237`.

## Key Patterns

### Flat tool envelope

Tool handler errors are converted to successful JSON RPC results containing text that starts with `ERROR:`. `isError` is intentionally omitted.

```rust
352 // WORKAROUND: Claude Code cancels all sibling parallel MCP tool calls when
353 // any tool returns isError:true
357 Err(e) => Ok(json!({
358     "content": [{
359         "type": "text",
360         "text": format!("ERROR: {}", e)
361     }]
362 }))
```

Source: `crates/fmm-cli/src/mcp/mod.rs:352-362`.

### Protocol errors remain JSON RPC errors

JSON parse and protocol failures use `JsonRpcError` with code, message, and optional data.

- `JsonRpcError` fields: `crates/fmm-cli/src/mcp/mod.rs:69-74`.
- Parse error code `-32700`: `crates/fmm-cli/src/mcp/mod.rs:187-200`.
- Unknown method code `-32601`: `crates/fmm-cli/src/mcp/mod.rs:240-244`.
- Missing params or tool name code `-32602`: `crates/fmm-cli/src/mcp/mod.rs:281-295`.

### Guidance is pushed into message content

The design moves user facing recovery guidance into the string returned by each tool handler. This means client level structure is minimal, but text quality can be high.

## Detailed Findings

### 1. What a failed call returns

There are two relevant paths.

Protocol level failures return `JsonRpcResponse { result: None, error: Some(JsonRpcError { ... }) }` through `handle_request` at `crates/fmm-cli/src/mcp/mod.rs:247-260`.

Tool handler failures return a JSON RPC success result with MCP text content. The dispatcher matches the tool at `crates/fmm-cli/src/mcp/mod.rs:311-327`. Any tool `Err(e)` becomes a text block with `ERROR: {e}` at `crates/fmm-cli/src/mcp/mod.rs:357-362`.

Manifest load failures use the same text content path. `require_manifest` returns the stored load error or `No index found. Run 'fmm generate' first.` at `crates/fmm-cli/src/mcp/mod.rs:169-175`, and `handle_tool_call` wraps that message as `ERROR:` at `crates/fmm-cli/src/mcp/mod.rs:299-308`.

Store and core errors are not fully structured at the MCP tool result layer, but their display text can be specific:

- `StoreError::NoIndex` says to run `fmm generate`: `crates/fmm-store/src/error.rs:12-21`.
- `FmmError` variants include file, export, config, parse, resolve, and store categories: `crates/fmm-core/src/error.rs:10-34`.
- `McpServer::with_root`, `from_store`, and `reload` keep load failures as `e.to_string()`: `crates/fmm-cli/src/mcp/mod.rs:115-125`, `135-146`, `148-161`.

### 2. Generic versus structured message content

The envelope is generic. The content is often specific.

Specific examples:

- Directory passed where a file is required: `validate_not_directory` returns guidance that points to `fmm_list_files(directory: ...)` at `crates/fmm-cli/src/mcp/tools/common.rs:80-98`.
- Missing file in index: `missing_file_diagnostic` distinguishes an existing unindexed file from a missing path at `crates/fmm-cli/src/mcp/tools/common.rs:100-106`.
- Invalid `fmm_list_files` values enumerate allowed values for `sort_by`, `order`, `group_by`, and `filter` at `crates/fmm-cli/src/mcp/tools/list_files.rs:43-67`.
- Empty `fmm_glossary` pattern explains why a pattern is required and gives examples at `crates/fmm-cli/src/mcp/tools/glossary.rs:15-21`.
- `fmm_read_symbol` uses MCP specific guidance for file path input, empty symbol names, missing symbols, ambiguous symbols, unknown classes, and missing members at `crates/fmm-cli/src/read_symbol.rs:49-180`.

Thin examples:

- `fmm_lookup_export` miss returns only `Export '<name>' not found`: `crates/fmm-cli/src/mcp/tools/lookup.rs:25-26`.
- All tool handlers parse arguments with `serde_json::from_value(...).map_err(|e| format!("Invalid arguments: {e}"))`, for example `crates/fmm-cli/src/mcp/tools/read.rs:13-14` and `crates/fmm-cli/src/mcp/tools/list_files.rs:20-21`.
- `fmm_dependency_cycles` maps one computation error through `e.to_string()`: `crates/fmm-cli/src/mcp/tools/cycles.rs:29-35`.

### 3. Special cased human readable errors

Yes. `fmm_read_symbol` has the richest subsystem.

- File path mistaken for symbol: `crates/fmm-cli/src/read_symbol.rs:49-60`.
- Empty symbol: `crates/fmm-cli/src/read_symbol.rs:62-71`.
- Missing export with next tools: `crates/fmm-cli/src/read_symbol.rs:99-110`.
- Ambiguous export with file qualified examples: `crates/fmm-cli/src/read_symbol.rs:112-141`.
- Unknown class and missing member recovery: `crates/fmm-cli/src/read_symbol.rs:86-97`, `143-180`.
- Member catalog and suggestion output: `crates/fmm-cli/src/read_symbol/member_error.rs:73-106`.
- Suggestion matching uses substring and Levenshtein threshold logic: `crates/fmm-cli/src/read_symbol/member_error.rs:322-365`.

This already matches the intended ergonomics of recovery oriented MCP errors. The gap is consistency across tools, especially `fmm_lookup_export` and generic argument deserialization failures.

### 4. MCP tests assert message content

Tests assert both the `ERROR:` envelope and useful content.

- `assert_error` checks only the prefix: `crates/fmm-cli/src/mcp/tests/support.rs:86-88`.
- The tool error tests also assert content contains `fmm_list_files` or `fmm_list_exports`: `crates/fmm-cli/src/mcp/tests/tool_errors.rs:6-39`.
- `fmm_read_symbol` tests assert `fmm_file_outline` guidance and exact file path guidance: `crates/fmm-cli/src/mcp/tests/read_symbol.rs:230-267`.
- Protocol tests assert JSON RPC error code and that unknown method text names the method: `crates/fmm-cli/tests/mcp_protocol.rs:209-237`.
- Snapshot coverage includes `fmm_lookup_export` miss and `fmm_read_symbol` miss outputs under `crates/fmm-cli/src/mcp/snapshots/`.

There is no current `isError` assertion because the server deliberately avoids returning that flag for tool failures.

## Dependencies

- `serde` and `serde_json`: JSON RPC and MCP request handling.
- `fmm-core`: manifest format, search, dependency graph, outlines, symbol resolution, and display formatting.
- `fmm-store`: SQLite backed manifest loading and persistence errors.
- `rusqlite`: SQLite database access.
- `thiserror` and `anyhow`: error types and propagation.
- `regex` and `glob`: user supplied pattern handling for export and file listing tools.

## Relevance to Helioy

Helioy agents rely on fmm as the first structural navigation layer. This investigation shows fmm already invests in agent recovery guidance, especially for `fmm_read_symbol`; future work should normalize error quality across tools rather than import another repository pattern wholesale.

Suggested follow up work:

1. Upgrade `fmm_lookup_export` miss to suggest `fmm_list_exports` or `fmm_search`, mirroring `fmm_read_symbol`.
2. Wrap serde argument failures with per tool field guidance where practical.
3. Decide whether a structured MCP error metadata channel is worth adding after the Claude Code `isError` workaround is no longer needed.

## Verification

Commands run from `/Users/alphab/Dev/LLM/DEV/helioy/fmm` on 2026-05-28:

```bash
fmm validate
cargo test -p fmm mcp::tests::tool_errors --quiet
cargo test -p fmm --test mcp_protocol mcp_protocol_unknown_method --quiet
cargo test -p fmm mcp::tests::read_symbol::read_symbol_file_path_name_gives_file_outline_guidance --quiet
```

Results:

- `fmm validate`: all 410 files indexed and up to date.
- `mcp::tests::tool_errors`: 3 passed.
- `mcp_protocol_unknown_method`: 1 passed.
- `read_symbol_file_path_name_gives_file_outline_guidance`: 1 passed.

## Open Questions

- Should MCP tool errors remain text only until the client cancellation issue is resolved?
- Should each tool own its own argument validation instead of relying on raw serde messages?
