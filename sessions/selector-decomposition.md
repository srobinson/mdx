---
title: Selector Module Decomposition
type: sessions
tags: [backend, rust, sm-core, selector, refactor]
summary: Split sm-core selector into focused sibling modules while preserving sm_core::selector public re-exports.
status: active
source: backend-engineer
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Summary

Implemented commit `72c0780` on branch `decomp-squad`. The `crates/sm-core/src/selector.rs` file now acts as a 10 line module hub. Selector logic moved into five focused siblings under `crates/sm-core/src/selector/`: `types`, `parser`, `display`, `scope`, and `tests`. The hub re-exports `Selector`, `LabelOp`, `NamespaceScope`, and `SELECTOR_GRAMMAR_HINT` so `sm_core::selector::*` consumers continue to compile unchanged.

## API Contract

No runtime API contract changed. Public selector imports are preserved through the root selector module re-exports.

## Database Changes

None.

## Security Considerations

Selector validation behavior is unchanged. Existing namespace conflict and legacy workspace selector rejection coverage was preserved in the moved selector tests.

## Performance Notes

No production performance impact. Targeted verification passed:

- `cargo check -p sm-core`
- `cargo test -p sm-core selector::`

## Open Items

Other pane work was present in `crates/sm-core/src/proto.rs` and `crates/sm-core/src/proto/` after this task. This pane staged and committed only the owned selector paths.
