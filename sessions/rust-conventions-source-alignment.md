---
title: Runtime Matters Rust Conventions Source Alignment
type: sessions
tags: [backend, rust, runtime-matters, conventions]
summary: Implemented the source side of the runtime-matters Rust conventions alignment and verified the full workspace gates.
status: active
source: backend-engineer
confidence: high
created: 2026-05-26
updated: 2026-05-26
---

## Summary

Implemented pane B source work for the `rust-conv-impl` warroom in `runtime-matters`.

Key changes:

- Added `#![forbid(unsafe_code)]` to safe crates: `rtm-core`, `lilo-rm-client`, `rtm-paths`, `rtm-launchers`, `rtm-store`, and `rtm-daemon`.
- Added crate docs to `rtm-cli`, `rtm-daemon`, `rtm-launchers`, `rtm-platform`, and `rtm-store`.
- Added precise `SAFETY:` comments to the requested `rtm-platform` unsafe blocks.
- Converted `rtm-paths::RuntimePathError` to `thiserror::Error` while preserving source chaining for current executable lookup failures.
- Converted `rtm-core::CaptureError` to `thiserror::Error` while preserving serde derives and wire shape.
- Renamed legacy production `mod.rs` files to `sqlite.rs`, `mcp.rs`, and `cli.rs` with `git mv`.
- Resolved clippy fallout from the new lint policy in source only: production unwrap and expect sites in `rtm-daemon` and `rtm-cli/build.rs` were removed, while test, bench, and example targets received explicit test scope allows for `expect_used` and `unwrap_used`.

## API Contract

No REST, RPC, or JSON wire contracts changed.

The `CaptureError` serde attributes were preserved, so the existing `capture_error_json_names_are_stable` snapshot remains valid.

## Database Changes

No schema, migration, or query changes.

## Security Considerations

- Safe crates now forbid unsafe code at crate level.
- Existing unsafe code remains isolated in `rtm-platform` and `rtm-cli` shim logic, with concrete `SAFETY:` invariants at each requested libc call site.
- JSON RPC serialization fallback now avoids `expect` while returning a structured internal error frame if serialization ever fails.
- Test only lint allows are isolated to test, bench, example, or `cfg(test)` contexts. Normal library targets still enforce the production lint policy.

## Performance Notes

No runtime performance impact expected. Changes are compile time lints, documentation, error derives, module path moves, and equivalent control flow around rare error paths.

## Verification

Passed:

```bash
fmm generate --force && fmm validate
cargo build --workspace --all-features
cargo test --workspace --all-features
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo fmt --all -- --check
git diff --check
```

The final `fmm validate` reported all 143 indexed files up to date.

## Open Items

- No source blockers remain for pane B.
- `Cargo.toml`, `justfile`, `rust-toolchain.toml`, and `Cargo.lock` changes were owned by the parallel pane and were not edited by pane B.
