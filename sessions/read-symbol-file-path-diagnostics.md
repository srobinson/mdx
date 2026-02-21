---
title: read_symbol file path diagnostics
type: sessions
tags: [backend, fmm, cli, mcp, diagnostics]
summary: Implemented read_symbol guidance for file path inputs that were previously parsed as Class.method lookups.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented and pushed `2cf44d8 fix(cli): clarify read_symbol file path diagnostics` on `origin/nancy/ALP-2707`.

The fix changes `read_symbol` resolution so dotted file names such as `crates/fmm-cli/src/read_symbol.rs` and `.fmmrc.toml` no longer fall through to misleading `Class.method` errors. The resolver now keeps the method index fast path first, then detects file path suffixes before class lookup.

## API Contract

No HTTP API changed.

CLI behavior:

```text
fmm read <path-with-known-extension>
```

returns guidance in this shape:

```text
'<name>' looks like a file path, not a Class.method symbol. Use fmm outline <name> to inspect an indexed source file, or pass a symbol name without a file extension.
```

MCP behavior:

```typescript
interface ReadSymbolRequest {
  name: string;
  truncate?: boolean;
  line_numbers?: boolean;
}
```

For file path style names, the MCP error text now points to `fmm_file_outline(file: "<name>")`.

Supported detection uses registered parser source extensions from `ParserRegistry::with_builtins().source_extensions()` plus `toml` for config file paths.

## Database Changes

None. This is resolver and diagnostic behavior only.

## Security Considerations

Input is still treated as an opaque symbol name. The change only classifies known file suffixes before attempting class lookup. No filesystem reads or path traversal behavior were added to the diagnostic branch.

## Performance Notes

The extension set is cached in a `LazyLock<HashSet<String>>`. Runtime work per dotted lookup is a path extension parse plus hash lookup after the method index fast path.

Verification completed:

```text
cargo fmt --all
just check
just test
./target/debug/fmm read crates/fmm-cli/src/read_symbol.rs
./target/debug/fmm read .fmmrc.toml
./target/debug/fmm read ReadSymbolResult.format_text --line-numbers
./target/debug/fmm validate
```

`just test` result: `1238 tests run: 1238 passed, 3 skipped`.

## Open Items

None for this scope. Auto routing `fmm read <file>` to file outline remains out of scope.
