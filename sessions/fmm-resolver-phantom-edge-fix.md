---
title: fmm resolver phantom edge fix
type: sessions
tags: [backend, fmm, rust, dependency-graph, resolver]
summary: Fixed Rust crate imports with relative manifest keys falling through to generic basename dependency matching.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary

Implemented the Slice Build Loop fix for the fmm resolver phantom cross crate edge.

Root cause: `build_dependency_edges` already intended to skip generic dependency matching for Rust workspace `crate::` imports, but `is_cargo_workspace_source` compared a relative manifest key against absolute Cargo package directories. That returned false, so `crate::dupes` from `crates/fmm-core/src/format/search_formatters.rs` fell through to generic basename matching and incorrectly matched `crates/fmm-cli/src/cli/commands/dupes.rs`.

Fix: `is_cargo_workspace_source` now reuses the Rust path helper that recognizes relative manifest keys beneath Cargo package directories. The helper was widened to `pub(crate)` and reexported through `resolver`, avoiding duplicate path comparison logic.

PR: https://github.com/srobinson/fmm/pull/166
Commit: `0e37385`

## API Contract

No public API or CLI contract changed.

## Database Changes

No schema or migration changes. The generated fmm graph now omits the phantom core to cli edge after regeneration.

## Security Considerations

No authentication, authorization, or external input boundary changes. The fix narrows dependency edge construction, which reduces misleading graph output without expanding trust boundaries.

## Performance Notes

The added check is a small path component comparison inside existing workspace source detection. It reuses the existing helper and does not add additional filesystem scans beyond the existing `Cargo.toml` existence check.

Verification performed:

- `cargo run -q -p fmm -- generate`
- `cargo run -q -p fmm -- cycles --filter source --explain`, now showing only `crates/fmm-core/src/resolver/deno.rs <-> crates/fmm-core/src/resolver/workspace.rs`
- `cargo test -q -p fmm-core dependency_matcher`, 25 passed
- `just check`, clean

## Open Items

The remaining genuine cycle between `resolver/deno.rs` and `resolver/workspace.rs` is unchanged and outside this slice.
