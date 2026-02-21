---
title: MountSpec Parser Exposure
type: sessions
tags: [backend, runtime-matters, rtm-core, mount-spec]
summary: Exposed the runtime-matters MountSpec CLI parser through rtm-core with typed errors and tests.
status: active
source: backend-engineer
confidence: high
created: 2026-05-24
updated: 2026-05-24
---

## Summary

Implemented item 1 of the local batch on branch `refactor/expose-mount-parser`.
Commit: `c395585221bdf66339233935699a9ca91ef10de2`.

Key decisions:

- Added `impl FromStr for MountSpec` in `crates/rtm-core/src/types/spawn.rs`.
- Added public `MountSpecParseError` with `Debug`, `Display`, `std::error::Error`, `Send`, `Sync`, and `'static` compatible shape.
- Added public `expand_mount_source` in `rtm-core` and re-exported it through `rtm_core::types` and crate root.
- Preserved current `rtm-cli` parser behavior exactly, including `~foo` expansion to `$HOME/foo` and 4+ colon overflow reporting as unknown access mode.
- Did not modify `rtm-cli`, Cargo versions, or changelog release headers.

## API Contract

```rust
impl std::str::FromStr for MountSpec {
    type Err = MountSpecParseError;
}

pub enum MountSpecParseError {
    MissingSeparator,
    EmptySource,
    EmptyTarget,
    UnknownMode { mode: String },
    MissingHome,
}

pub fn expand_mount_source(source: &str) -> Result<PathBuf, MountSpecParseError>;
```

Accepted mount syntax:

- `HOST:CONTAINER` defaults to read only.
- `HOST:CONTAINER:ro` sets `read_only = true`.
- `HOST:CONTAINER:rw` sets `read_only = false`.
- Host source values beginning with `~` expand against `$HOME` on the host side.
- Container target values are lexical and are not tilde expanded.

Rejected mount syntax:

- Missing `:` between host source and container target.
- Empty host source.
- Empty container target.
- Unknown access mode.
- 4+ colon parts, reported via the same unknown access mode path as the previous CLI parser.

## Database Changes

None.

## Security Considerations

- Parser remains lexical and does not canonicalize or validate filesystem existence, preserving the current boundary between CLI parsing and daemon or Docker preflight.
- Only the host source is tilde expanded. Container target values remain unmodified to avoid host path leakage into container namespace semantics.
- Error values are typed for callers and machine handling while preserving user facing message text.

## Performance Notes

- Parser is allocation-light and linear in the input string length.
- No runtime daemon path changed.
- `crates/rtm-core/src/types/spawn.rs` remains under the 700 LOC threshold at 413 lines after tests.

Verification:

- `cargo test -p lilo-rm-core` passed.
- `cargo build -p lilo-rm-cli` was attempted and failed because no such workspace package exists.
- `cargo metadata --no-deps --format-version 1` confirmed the CLI package is `rtm-cli`.
- `cargo build -p rtm-cli` passed.
- `fmm generate && fmm validate` passed.

## Open Items

- Item 2 should rewire `rtm-cli` `--mount` parsing to delegate to `MountSpec::from_str` and delete the private CLI parser helpers.
- Session matters consumption remains separate cross repo work after the `lilo-rm-core` release path is available.
