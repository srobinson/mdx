---
title: RM Launchers DRY Fix Implementation
type: sessions
tags: [backend, littleorgans, runtime, clippy]
summary: Deduplicated runtime launcher, protocol, serde, schema, and client response production code for the rm-launchers lane.
status: active
source: backend-engineer
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Summary

Implemented the Phase 2 `rm-launchers` DRY lane. Production code now shares nonempty JSON line parsing, argv command extraction, optional number display, string parsed serde helpers, schema description injection, typed client response extraction, and binary launcher behavior.

## API Contract

No HTTP or daemon wire contract changed.

New crate private helper module:

```rust
pub(crate) fn serialize_string<S>(value: &str, serializer: S) -> Result<S::Ok, S::Error>;
pub(crate) fn serialize_display<T, S>(value: &T, serializer: S) -> Result<S::Ok, S::Error>;
pub(crate) fn deserialize_string_parsed<'de, T, D>(deserializer: D) -> Result<T, D::Error>;
```

New runtime launcher implementation type:

```rust
pub struct BinaryLauncher;
```

`ClaudeLauncher` and `CodexLauncher` are now binary registrations backed by `BinaryLauncher`.

## Database Changes

None.

## Security Considerations

No authorization or persistence paths changed. Protocol readers still return EOF on empty reads and parse newline delimited JSON through the existing serde path.

## Performance Notes

The launcher refactor preserves binary path caching through `OnceLock`. Query and protocol behavior are unchanged. The serde display helper allocates only for the tmux address display path, which already serialized via `to_string()`.

## Verification

Passed:

- `cargo clippy -p lilo-rm-core --all-targets -- -D warnings`
- `cargo clippy -p lilo-runtime-launchers --all-targets -- -D warnings`
- `cargo clippy -p lilo-runtime-launchers --lib -- -D warnings`
- `cargo clippy -p lilo-rm-client --lib -- -D warnings`

Blocked outside lane:

- `cargo clippy -p lilo-rm-core -p lilo-rm-client -p lilo-runtime-launchers --all-targets -- -D warnings`
- `cargo clippy -p lilo-rm-client --all-targets -- -D warnings`

Both fail because `internal/runtime/daemon/src/service.rs:96` uses `.context(...)` without `anyhow::Context` in scope. That file is outside the assigned lane, and the orchestrator confirmed Lane 1 owns it.

## Open Items

None for this lane. The orchestrator confirmed the remaining `internal/runtime/daemon/src/service.rs` compile error belongs to Lane 1.
