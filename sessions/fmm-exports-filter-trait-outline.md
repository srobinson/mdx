---
title: fmm exports filter and trait outline implementation
type: sessions
tags: [backend, fmm, cli, mcp, rust-parser]
summary: Added exports source or tests filtering with inline cfg test exclusion plus Rust trait method outline support.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary

Implemented PR#159 on branch `feat/exports-filter-outline-traits` at `ea6f616`.

Key decisions:

* `fmm exports --filter {all|source|tests}` now supports path based classification and symbol level exclusion for inline Rust test contexts.
* MCP `fmm_list_exports` exposes the same `filter` parameter and schema.
* Rust declarations inside `#[cfg(test)]` module ancestors or `mod tests` ancestors are marked as `DeclarationKind::Test`.
* Rust trait methods are extracted in the parser as `DeclarationKind::Method` members under the trait name, so existing outline rendering displays them without a renderer fork.

## API Contract

CLI:

```text
fmm exports [PATTERN] [--file <FILE>] [--dir <DIR>] [--filter <all|source|tests>] [--limit <N>] [--offset <N>] [--json]
```

MCP:

```typescript
interface FmmListExportsArgs {
  pattern?: string;
  file?: string;
  directory?: string;
  filter?: "all" | "source" | "tests";
  limit?: number;
  offset?: number;
}
```

Filter behavior:

* `all` keeps the previous behavior.
* `source` excludes files classified as tests and excludes individual symbols classified as tests.
* `tests` includes files classified as tests or individual symbols classified as tests.
* Inline Rust `#[cfg(test)]` modules and `mod tests` modules in ordinary source files are classified at the symbol level.

Outline behavior:

```text
fmm outline crates/fmm-core/src/store.rs --include-private
```

Now lists `FmmStore` members such as `load_manifest`, `update_file_fingerprint`, and `write_meta` with method signatures.

## Database Changes

No schema or migration changes.

The implementation changes parser output, so regenerated indexes include trait method entries in existing methods metadata and method index structures. Regenerated Rust indexes also mark inline test context declarations as test declarations.

## Security Considerations

No authentication or authorization changes.

Input handling remains bounded by existing clap value parsers and MCP schema enum validation for the new `filter` argument.

## Performance Notes

The filter path uses existing path classification plus manifest level export metadata. No extra source file reads are introduced for indexed export listing.

Parser extraction adds bounded ancestor and attribute checks while already walking Rust declarations.

Verification completed:

```text
cargo test -p fmm --test cli_exports exports_filter -- --nocapture
cargo test -p fmm --test mcp_tools list_exports_filter -- --nocapture
cargo test -p fmm-core rust_inline_test_module_exports_are_test_kind -- --nocapture
just check
git diff --check
```

Manual proof after regenerating the local index:

```text
rm -f .fmm.db .fmm.db-shm .fmm.db-wal
cargo run -q -p fmm -- generate --force .
cargo run -q -p fmm -- exports --dir crates/fmm-store/src --filter source | rg wal_mode_is_active
# no match

cargo run -q -p fmm -- exports --dir crates/fmm-store/src --filter tests | rg wal_mode_is_active
# lists wal_mode_is_active
```

## Open Items

No known open items for this slice.
