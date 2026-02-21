---
title: ALP-2707 read_symbol module declaration contract
type: sessions
tags: [backend, fmm, alp-2707, read-symbol, rust]
summary: Locked the read_symbol contract for Rust mod declarations through CLI and MCP regression coverage plus generated docs.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented and pushed commit `953c451` on `nancy/ALP-2707` with subject `test: lock read_symbol module declaration kind`.

The work preserves existing behavior: bare Rust module names return the `mod foo;` declaration with `kind: module`. They do not follow into `foo.rs` or `foo/mod.rs`.

Key decisions:

- Chose contract preservation, not resolver behavior changes.
- Kept canonical kind value `module`, matching `DeclarationKind::Module`.
- Framed the changelog under tests, not bug fixes, because behavior was already correct.
- Added both direct MCP manifest coverage and generated-index CLI coverage.

## API Contract

Tool contract for `fmm_read_symbol` and CLI `fmm read`:

```typescript
interface ReadSymbolModuleDeclarationContract {
  name: string; // bare Rust module name, for example public_api or internal_api
  output: {
    symbol: string;
    file: string;
    lines: [number, number];
    kind: "module";
    source: string; // the mod declaration line
  };
}
```

Positive contract:

- `pub mod public_api;` emits `kind: module` and returns the declaration line.
- `mod internal_api;` emits `kind: module` and returns the declaration line.
- Backing files are not followed.

Negative contract:

- `pub fn build()` emits `kind: fn`, not `kind: module`.

## Database Changes

None.

No schema, migration, index, or storage changes were made. The implementation relies on existing parser metadata and manifest declaration kind plumbing.

## Security Considerations

No new input surface or execution path was introduced.

The change adds regression tests and documentation only. Existing `read_symbol` resolution semantics remain unchanged, which avoids a new implicit file traversal behavior for Rust modules.

## Performance Notes

No runtime performance impact is expected.

Verification completed:

- `just check`: green.
- `just test`: green, `1234 passed, 3 skipped`; doctests OK.
- `git diff --check`: clean.
- No `.snap.new` files found.

## Open Items

- Workflow lesson for future bus Phase B reviews: commit before requesting Phase B review so the reviewer can validate a stable SHA through `git show <sha>`.
- No follow-up code work is required for this module declaration contract.
