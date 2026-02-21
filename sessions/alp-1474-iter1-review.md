---
title: ALP-1474 Workspace Migration Review (Iter 1)
type: sessions
tags: [review, fmm, workspace, rust, ALP-1474]
summary: Reviewed monolith-to-workspace migration (20 commits). Found and removed 6 dead dependencies from fmm-cli. All 946 tests pass.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-18
updated: 2026-03-18
---

## Summary

Reviewed the ALP-1474 monolith-to-workspace migration of the fmm codebase. 20 commits spanning ALP-1475 through ALP-1496 restructured the single-crate project into a Cargo workspace with three crates: fmm-core (domain logic), fmm-store (persistence), and fmm-cli (CLI + MCP server). The migration introduces the FmmStore trait for backend abstraction, InMemoryStore for testing, insta snapshot tests, subprocess MCP protocol tests, and cargo-nextest for CI.

## Issues Found and Fixed

**1. Dead dependencies in fmm-cli/Cargo.toml** (fixed, committed)
- `tree-sitter`, `tree-sitter-typescript`, `tree-sitter-python`, `tree-sitter-rust`, `streaming-iterator`: Listed as runtime dependencies with a stale comment referencing ALP-1482. That issue already ran, moving the consuming modules to fmm-core. Zero imports in fmm-cli source.
- `rusqlite`: Listed as a runtime dependency but only used in integration tests (covered by `[dev-dependencies]`). No direct rusqlite imports in fmm-cli/src/.
- Fix: Removed all 6 dead dependencies. Build, clippy, and all 946 tests pass.

## Patterns Observed

- **Clean trait abstraction**: FmmStore trait is well-designed with `&self` semantics, proper error typing, and good documentation. The SqliteStore/InMemoryStore split is clean.
- **Transitional manifest_ext.rs**: Still used by CLI commands (exports, ls, deps, outline, read, lookup, search, glossary) for direct SQLite access. Not dead code. The migration to FmmStore is incomplete for CLI commands (only MCP server and watch/sidecar are migrated).
- **TS>JS collision logic correctness**: InMemoryStore's build_manifest iterates a HashMap (non-deterministic order) but the collision logic handles both orderings correctly (TS always wins regardless of iteration order).
- **Test infrastructure quality**: Good test coverage with 946 tests. Snapshot tests cover all 8 MCP tools. Subprocess protocol tests exercise the full JSON-RPC loop.
- **Release pipeline**: jsonpath fix from `$.package.version` to `$.workspace.package.version` is correct for the workspace layout.

## Open Items

None. Code is clean and pushed.
