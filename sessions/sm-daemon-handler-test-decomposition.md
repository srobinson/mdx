---
title: sm-daemon handler integration test decomposition
type: sessions
tags: [backend, rust, tests, session-matters]
summary: Split sm-daemon handler integration tests into focused modules while preserving crate-local re-exports.
status: active
source: backend-engineer
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Summary

Implemented the decomp-squad pane 2 assignment for `crates/sm-daemon/tests/handler.rs`.
The root integration test file now only wires `common`, declares focused module files with explicit `#[path]` attributes, and re-exports each module crate-locally to preserve the split helper and test surface.

New modules:

- `crates/sm-daemon/tests/handler/agent_config.rs`
- `crates/sm-daemon/tests/handler/lifecycle.rs`
- `crates/sm-daemon/tests/handler/logs_doctor.rs`
- `crates/sm-daemon/tests/handler/spawn_launch.rs`
- `crates/sm-daemon/tests/handler/spawn_namespace.rs`

Commit: `032b1ed`.

## API Contract

Not applicable. This was a test-only refactor with no runtime API, CLI, MCP, or wire contract changes.

The crate-local test import surface is intentionally preserved through `pub(crate) use` re-exports from `tests/handler.rs`.

## Database Changes

None.

## Security Considerations

No production behavior changed. Existing tests around spawn environment handling, namespace validation, logs, wait, doctor, and deletion behavior were moved without semantic changes.

## Performance Notes

No runtime performance impact. Test decomposition reduced the largest edited file from 689 LOC to a 23 LOC root plus modules, with max new module LOC of 186.

Verification run:

```bash
cargo test -p sm-daemon --test handler
fmm generate && fmm validate
scripts/check-loc-limit.sh crates/sm-daemon/tests/handler.rs crates/sm-daemon/tests/handler/*.rs
git diff --check -- crates/sm-daemon/tests/handler.rs crates/sm-daemon/tests/handler/*.rs
```

Results: 15 handler tests passed; FMM index validated; LOC and diff checks passed.

## Open Items

Other decomp-squad panes owned concurrent changes in `crates/sm-daemon/src/mcp_tools.rs`, `crates/sm-cli/tests/mcp_protocol_test.rs`, and `crates/sm-core/src/tool_contracts.rs`. Those files were left untouched by this pane.
