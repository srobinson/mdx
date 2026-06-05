---
title: lilo-sys creds seam implementation
type: sessions
tags: [backend, rust, littleorgans, lilo-sys, creds]
summary: Moved raw OS credential primitives into lilo-sys while keeping Principal mapping in lilo-im-core.
status: active
source: backend-engineer
confidence: high
created: 2026-06-01
updated: 2026-06-01
---

## Summary

Implemented F2 of the lilo-sys platform seam batch on branch `refactor/lilo-sys-platform-seam`.

Commit: `cd062830830b67eae0f5265f882f258b6a9ad268`.

Key decisions:

- Added `lilo_sys::creds::PeerCred` as raw OS credential data: `uid`, `gid`, and optional `pid`.
- Added `lilo_sys::creds::peer_cred(fd)` and `lilo_sys::creds::current_uid()`.
- Kept `Principal` and raw UID to `Principal::local` mapping in `lilo-im-core`.
- Moved Linux `SO_PEERCRED` and macOS `getpeereid` behind the existing `sys/unix/{linux,macos}.rs` `cfg_select!` seam.
- Replaced direct daemon and identity test `nix::unistd::getuid()` calls with `lilo_sys::creds::current_uid()`.
- Removed production `nix` usage from `lilo-im-core` and `lilo-runtime-daemon`; `lilo-session-daemon` keeps `nix` as a dev dependency for existing signal tests.
- Added platform-independent coverage for the unsupported peer credential error after reviewer feedback.

## API Contract

No HTTP or RPC endpoint contract changed.

Rust crate surface added:

```rust
pub struct PeerCred {
    pub uid: u32,
    pub gid: u32,
    pub pid: Option<u32>,
}

pub fn current_uid() -> u32;
pub fn peer_cred(fd: libc::c_int) -> lilo_sys::Result<PeerCred>;
```

Domain boundary:

- `lilo-sys` returns raw OS credentials only.
- `lilo-im-core` maps raw UID values to `Principal::local`.
- Local principal meaning does not move into `lilo-sys`.

## Database Changes

None.

## Security Considerations

- The privileged boundary is narrower: raw OS credential extraction now lives in the platform abstraction layer.
- Identity domain interpretation remains in `lilo-im-core`, so the system avoids mixing OS primitives with authorization semantics.
- Direct local UID lookup is centralized in `lilo_sys::creds::current_uid()`.
- Existing socket peer credential integration coverage still verifies accepted Unix sockets map to the local principal.
- `lilo-sys` now has platform-independent unsupported peer credential error coverage.

## Performance Notes

- Credential extraction remains synchronous and uses the platform syscall directly.
- No new database queries or background tasks were added.
- The implementation removes duplicated UID call sites and adds no extra allocation on the happy path beyond existing error formatting.

## Verification

Commands run:

```bash
cargo check -p lilo-sys -p lilo-im-core -p lilo-runtime-daemon -p lilo-session-daemon
cargo test -p lilo-sys -p lilo-im-core -p lilo-runtime-daemon -p lilo-session-daemon
cargo clippy -p lilo-sys -p lilo-im-core -p lilo-runtime-daemon -p lilo-session-daemon --all-targets -- -D warnings
cargo test -p lilo-im-core --test peer_creds
cargo test -p lilo-sys
fmm generate && fmm validate
git diff --check
rg -n 'nix::unistd::getuid' internal/runtime/daemon/src internal/session/daemon/src crates/lilo-im-core
moon ci
```

Result:

- `moon ci` passed after the reviewer fix.
- Nextest summary: 631 tests run, 631 passed, 0 skipped.
- `cargo test -p lilo-sys` passed with `error::tests::unsupported_peer_cred_error_is_descriptive` included.
- `fmm validate` passed with 372 indexed files up to date.
- Direct `nix::unistd::getuid` search returned no matches in the requested roots.

## Open Items

- Reviewer re-gate is pending for commit `cd062830830b67eae0f5265f882f258b6a9ad268`.
- Linux `SO_PEERCRED` code was added but not locally cross compiled because the installed Rust target is `aarch64-apple-darwin` only. macOS `getpeereid` path was compiled and exercised locally.
