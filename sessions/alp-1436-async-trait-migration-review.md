---
title: ALP-1436 Async Trait Migration Review
type: sessions
tags: [review, context-matters, async, rust]
summary: Clean review of native async fn trait migration. No issues found. 177/177 tests pass.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-18
updated: 2026-03-18
---

## Summary

Reviewed the full diff for ALP-1436: migrating context-matters `ContextStore` trait from synchronous signatures with `block_in_place` wrappers to native `async fn` in trait (Rust 1.75+).

Scope: 31 files changed, ~2000 lines added, ~950 removed across 4 commits:
1. Core migration (trait + impl + all tool handlers + all tests)
2. Nextest adoption
3. Insta snapshot tests for all 9 MCP tools
4. Subprocess MCP protocol tests

## Issues Found and Fixed

None. The code is clean.

## Patterns Observed

- Mechanical migration: every `tokio::task::block_in_place(|| { Handle::current().block_on(async { ... }) })` replaced with direct async. Zero residual sync wrappers.
- `McpServer` correctly made generic over `S: ContextStore` with `Arc<S>` ownership.
- Tool handlers changed from `&CmStore` to `&impl ContextStore`, enabling test isolation without trait objects.
- `#[allow(async_fn_in_trait)]` is appropriate since the project uses static dispatch only.
- Snapshot tests use manual redaction of dynamic fields rather than insta's built-in redaction. Works but slightly verbose.
- Protocol tests spawn the binary as a subprocess with isolated `CM_DATA_DIR`. Good isolation pattern.

## Open Items

None.
