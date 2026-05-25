---
title: Tool contracts decomposition
type: sessions
tags: [backend, rust, sm-core, tool-contracts, decomposition]
summary: Split sm-core tool contracts into focused modules while preserving root exports.
status: active
source: backend-engineer
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Summary

Split `crates/sm-core/src/tool_contracts.rs` into six natural sibling modules under `crates/sm-core/src/tool_contracts/`:

- `contract.rs` for shared content and tool contract models
- `metadata.rs` for CLI and artifact render metadata
- `params.rs` for parameter contracts, shapes, and namespace scope parameters
- `raw.rs` for TOML input structs and JSON parsing helpers
- `registry.rs` for bundled registry loading, ordering, and duplicate validation
- `render.rs` for selector grammar rendering and Rust constant naming

The root `tool_contracts.rs` now declares modules, re-exports the public surface, and retains the existing focused tests. Commit: `2d1ec3b`.

## API Contract

No HTTP or GraphQL API changed.

Rust module contract preserved:

```rust
pub use contract::{SharedContent, SkillConfig, SelectorGrammar, ToolContract};
pub use metadata::{ArtifactRenderMetadata, CliMetadata};
pub use params::ToolParamContract;
pub use registry::{contract_registry, ToolContractRegistry};
pub use render::{render_selector_grammar_block, rust_const_name};
```

Downstream callers can continue using `sm_core::tool_contracts::*`.

## Database Changes

None.

## Security Considerations

No authorization, authentication, or boundary behavior changed. Parsing and validation behavior moved unchanged into focused modules.

## Performance Notes

Runtime behavior is unchanged. Registry initialization still uses `OnceLock`, bundled tool source concatenation, deterministic ordering, and duplicate render name validation.

Verification:

```bash
rustfmt --edition 2024 crates/sm-core/src/tool_contracts.rs crates/sm-core/src/tool_contracts/*.rs
cargo check -p sm-core
cargo test -p sm-core tool_contracts
```

Both cargo commands passed after the commit.

## Open Items

The shared worktree still contained other panes' unstaged changes in `crates/sm-cli/tests/mcp_protocol_test.rs`, `crates/sm-daemon/src/handler.rs`, and `crates/sm-daemon/src/mcp_tools.rs`. Those were not touched or staged by this work.
