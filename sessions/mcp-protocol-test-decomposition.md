---
title: MCP Protocol Test Decomposition
type: sessions
tags: [backend, rust, sm-cli, tests, refactor]
summary: Split sm-cli MCP protocol integration tests into natural protocol modules while preserving root re-exports.
status: active
source: backend-engineer
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Summary

Implemented commit `de20d1a` on branch `decomp-squad`. The `crates/sm-cli/tests/mcp_protocol_test.rs` integration test now acts as a 44 line module hub. Test logic moved into seven explicit sibling modules under `crates/sm-cli/tests/mcp_protocol_test/`: lifecycle, configuration and namespaces, handshake, helpers, mail, schema, and selectors. Root re-exports preserve helper and test symbol access from the original test module surface.

## API Contract

No runtime API contract changed. This was a test-only refactor of the MCP protocol integration test layout.

## Database Changes

None.

## Security Considerations

The refactor preserves existing audit assertions for spawn, read, doctor, kill, mail, and nudge authorization paths. No authentication, authorization, or input validation code changed.

## Performance Notes

No production performance impact. Targeted verification ran with `cargo test -p sm-cli --test mcp_protocol_test`, which passed all 8 tests.

## Open Items

Other panes had unowned unstaged changes in `crates/sm-daemon/src/handler.rs` and `crates/sm-daemon/src/handler/` after this work. This pane staged and committed only the owned `sm-cli` test paths.
