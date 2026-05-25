---
title: sm-core proto decomposition
type: sessions
tags: [backend, rust, protocol, session-matters]
summary: Split sm-core proto contracts into focused sibling modules while preserving crate::proto re-exports.
status: active
source: backend-engineer
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Summary

Implemented the decomp-squad round 2 pane 2 assignment for `crates/sm-core/src/proto.rs`.
The root `proto.rs` now declares focused sibling modules and re-exports every public protocol name so `crate::proto::*` remains stable.

New modules:

- `crates/sm-core/src/proto/bridge.rs`
- `crates/sm-core/src/proto/doctor.rs`
- `crates/sm-core/src/proto/messaging.rs`
- `crates/sm-core/src/proto/namespace.rs`
- `crates/sm-core/src/proto/rpc.rs`
- `crates/sm-core/src/proto/session.rs`
- `crates/sm-core/src/proto/spawn.rs`
- `crates/sm-core/src/proto/target.rs`
- `crates/sm-core/src/proto/tests.rs`

Commit: `0e5338e`.

## API Contract

No wire contract changes were intended. Request and response structs, enums, serde tags, defaults, and helper impls were moved by domain seam:

- spawn and list contracts
- namespace contracts
- mail and nudge contracts
- session operation contracts, including delete, label, logs, capture, and wait
- doctor contracts
- MCP bridge, shutdown, and daemon status contracts
- RPC request and response envelope contracts
- target error contract

The public `crate::proto::*` import surface is preserved by root-level `pub use` re-exports.

## Database Changes

None.

## Security Considerations

No production logic changed. The refactor kept serde defaults and tagged enum behavior intact, which preserves compatibility for daemon and CLI request decoding.

## Performance Notes

No runtime performance impact. The largest resulting file is `crates/sm-core/src/proto/tests.rs` at 146 LOC. The production modules are all smaller than 104 LOC.

Verification run:

```bash
cargo check -p sm-core
cargo test -p sm-core proto::
fmm generate && fmm validate
scripts/check-loc-limit.sh crates/sm-core/src/proto.rs crates/sm-core/src/proto/*.rs
git diff --check -- crates/sm-core/src/proto.rs crates/sm-core/src/proto/*.rs
```

Results: `cargo check` passed; 6 focused proto tests passed; FMM index validated; LOC and diff checks passed.

## Open Items

None for this pane. The round noted a possible `sm-core/src/lib.rs` collision with pane 3, but this split did not require touching `lib.rs`.
