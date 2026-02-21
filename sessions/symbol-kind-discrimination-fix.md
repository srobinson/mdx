---
title: Symbol kind discrimination fix
type: sessions
tags: [backend, fmm, mcp, cli, rust]
summary: Implemented indexed declaration kind output for read and glossary surfaces.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented the symbol kind discrimination fix on branch `nancy/ALP-2707` in commit `904985c`.

Key decisions:

- Reused indexed declaration metadata instead of inferring kind from display shape.
- Added `Manifest::declaration_kind_for` as the single lookup path for top level exports and dotted class members.
- Added `push_kind_line` as the shared formatter for `kind:` output across read, glossary, and outline metadata paths.
- Preserved the private dotted fallback behavior by omitting `kind:` when index metadata is unavailable.
- Changed dotted field glossary output so field access is not described as method call activity.

## API Contract

This task affected CLI and MCP text and JSON contracts, not HTTP endpoints.

### Read symbol text output

`fmm_read_symbol` and `fmm read` now include a declaration kind when the resolved symbol has index metadata.

```yaml
---
symbol: McpServer.manifest
file: crates/fmm-cli/src/mcp/mod.rs
lines: [86, 86]
kind: field
---
```

Private dotted fallback symbols continue to omit `kind:` when metadata is absent.

### Read symbol JSON output

The existing response discriminator remains `kind: "source"` or `kind: "class_redirect"`. A new optional `symbol_kind` field carries declaration kind metadata.

```json
{
  "kind": "source",
  "symbol_kind": "method"
}
```

### Glossary output

Glossary sources now carry optional declaration kind metadata. Dotted fields emit field specific no caller context instead of method call wording.

```yaml
McpServer.manifest:
  kind: field
  (field; no external source callers expected)
  # 1 file import mod.rs; field access is not a method call site
```

## Database Changes

No database schema changes were made. The implementation reads existing `declaration_kind` metadata already stored in export and method metadata.

## Security Considerations

No authentication, authorization, or network surfaces changed. Input handling remains within existing symbol lookup and formatting paths. JSON output preserves the existing response discriminator, reducing compatibility risk for consumers that switch on `kind`.

## Performance Notes

The new declaration kind lookup is an in memory manifest map lookup scoped to the resolved file and symbol. No additional source file parsing or database reads were added to read or glossary formatting paths.

Verification completed:

- `git diff --check`
- `just check`
- `just test`, 1229 passed, 3 skipped
- `./target/debug/fmm validate`, all 408 files up to date
- Manual smoke checks for `McpServer.manifest` field output, `McpServer.manifest` glossary output, and `McpServer.new` method output

## Open Items

- Phase B reviewer signoff was received on bus topic `alp2707-symbol-kind`: `I sign off on the symbol-kind discrimination fix as currently filed.`
- The MCP fmm tool bridge still reports schema version mismatch in this worktree, while the local CLI index validates successfully. This was pre existing during the task.
