---
title: Session Matters CLI Get Test Decomposition
type: sessions
tags: [backend, rust, refactor, session-matters, tests]
summary: Split sm-cli cli_get_test into focused scenario modules while preserving helper and test re-exports.
status: active
source: backend-engineer
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Summary

Implemented the Round 2 `decomp-squad` mail directive for `crates/sm-cli/tests/cli_get_test.rs`. The original 572 line integration test file now acts as a 48 line module facade. Scenario code was split into six focused sibling modules under `crates/sm-cli/tests/cli_get_test/`:

- `help.rs`: CLI help surface tests for `get`, `create`, and `run`
- `create_session.rs`: create session behavior and create/run record parity
- `agent_config.rs`: agent config path canonicalization and missing config diagnostics
- `session_read.rs`: get session list/single reads, removed get forms, and capture id validation
- `run_resolution.rs`: run directory canonicalization and rejected/unknown argument cases
- `helpers.rs`: shared command assertions, JSON loading, stdout/stderr helpers, table assertions, and canonical path rendering

The root test file re-exports every moved test and helper at crate visibility so intra-test imports from the previous surface keep compiling.

Commit: `0100ce3 refactor(sm-cli): split cli_get_test into scenario modules`.

## API Contract

No runtime API contract changed. This was a test-only decomposition. The covered CLI surfaces remain unchanged:

- `sm get session|sessions`
- `sm get namespace|namespaces`
- `sm create session`
- `sm run`
- `sm capture <id>`

## Database Changes

None.

## Security Considerations

No auth, authorization, or persistence behavior changed. The test split preserves existing assertions around namespace errors, argument rejection, and canonical path handling.

## Performance Notes

No runtime performance impact. File sizes after the split:

- `cli_get_test.rs`: 48 LOC
- `cli_get_test/agent_config.rs`: 98 LOC
- `cli_get_test/create_session.rs`: 98 LOC
- `cli_get_test/help.rs`: 87 LOC
- `cli_get_test/helpers.rs`: 54 LOC
- `cli_get_test/run_resolution.rs`: 85 LOC
- `cli_get_test/session_read.rs`: 161 LOC

Maximum LOC after split: 161.

Verification run:

- `cargo test -p sm-cli --test cli_get_test`
- `fmm generate && fmm validate`
- `git diff --check -- crates/sm-cli/tests/cli_get_test.rs crates/sm-cli/tests/cli_get_test`

## Open Items

The shared `decomp-squad` worktree had peer owned changes in `crates/sm-core/src/selector.rs` after this commit. Those paths were intentionally not staged or modified by this pane. Final integration testing remains owned by the orchestrator per the squad directive.
