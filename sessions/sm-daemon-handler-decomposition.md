---
title: sm-daemon handler decomposition
type: sessions
tags: [backend, rust, sm-daemon, refactor]
summary: Split sm-daemon handler.rs into focused handler submodules while preserving crate::handler public imports.
status: active
source: backend-engineer
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Summary

Decomposed `crates/sm-daemon/src/handler.rs` from a 674 line monolith into a root module plus six focused submodules:

- `handler/dispatch.rs` for RPC dispatch and shutdown response handling.
- `handler/messaging.rs` for mail and nudge flows.
- `handler/sessions.rs` for list, capture, delete, and label flows.
- `handler/spawn.rs` for spawn lifecycle and launch construction.
- `handler/state.rs` for `DaemonState` and `HandlerResult`.
- `handler/target.rs` for selector resolution, session requirements, and target error shaping.

The root `handler.rs` now re-exports `DaemonState` and `HandlerResult`, preserving `crate::handler::DaemonState`, `crate::handler::HandlerResult`, and `crate::handler::*` consumers.

Commit: `825484d refactor(sm-daemon): split handler into request modules (decomposition)`.

## API Contract

No external API contract changed. The Rust public module contract is preserved:

```rust
pub use state::{DaemonState, HandlerResult};
```

Existing downstream imports continue to compile unchanged.

## Database Changes

No schema, migration, or index changes.

## Security Considerations

Authorization call sites remain attached to their original operations:

- Spawn uses `Action::Spawn` with `spawn_resource`.
- Capture uses `Action::Read` with `session_resource`.
- Delete uses `Action::Kill` with `session_resource`.
- Mail send and read use `Action::MailSend` and `Action::MailRead`.
- Nudge uses `Action::Nudge`.
- Label uses `Action::Link`.
- Shutdown uses `Action::Daemon`.

The refactor moved code only. It did not widen method visibility beyond sibling module needs, except existing `pub(crate)` methods remained `pub(crate)` for existing crate consumers.

## Performance Notes

No runtime behavior or query shape changed. Verification completed with:

```bash
rustfmt --edition 2024 crates/sm-daemon/src/handler.rs crates/sm-daemon/src/handler/*.rs
cargo check -p sm-daemon
cargo test -p sm-daemon --lib
fmm generate && fmm validate
```

Largest resulting handler file: `crates/sm-daemon/src/handler/messaging.rs` at 212 LOC.

## Open Items

None for this decomposition. The squad level integration owner should run any broader integration tests after peer panes land their changes.
