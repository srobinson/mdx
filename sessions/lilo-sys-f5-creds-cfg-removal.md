---
title: lilo-sys F5 creds cfg removal
type: sessions
tags: [backend, littleorgans, lilo-sys, peer-creds, platform-seam]
summary: Removed production peer credential cfg from lilo-im-core by moving stream fd access behind lilo-sys; reviewer signed off.
status: complete
source: backend-engineer
confidence: high
created: 2026-06-01
updated: 2026-06-01
---

## Summary

Implemented F5 creds cfg removal on branch `refactor/lilo-sys-platform-seam` in commit `f5c209f`.

The scoped production change was limited to `crates/lilo-im-core/src/peer_creds.rs` and the public `lilo_sys::creds` wrapper. The earlier candidate filesystem sites in `namespace_resolver.rs` and `spawn_context.rs` were left untouched because they are inline test code and F6 excludes inline `#[cfg(test)]` blocks.

## API Contract

No network API changed.

Rust API change:

```rust
pub fn lilo_sys::creds::peer_cred(
    stream: &lilo_sys::ipc::IpcStream,
) -> lilo_sys::Result<lilo_sys::creds::PeerCred>;

pub async fn lilo_im_core::peer_creds::extract(
    stream: &lilo_sys::ipc::IpcStream,
) -> Result<lilo_im_core::Principal, lilo_im_core::AuthzError>;
```

The raw fd syscall primitive remains private under `lilo-sys/src/sys/*`.

## Database Changes

None.

## Security Considerations

Peer credential extraction still maps the local socket peer UID to `Principal::local(uid)`. The platform gate now stays inside `lilo-sys`; `lilo-im-core` no longer imports `std::os` traits or carries production `cfg(unix)`.

## Performance Notes

No additional allocation or I/O was added. The wrapper calls `stream.as_raw_fd()` inline and delegates to the existing platform syscall path.

## Verification

- `rg 'cfg\((unix|windows)\)|std::os' crates/lilo-im-core/src/peer_creds.rs crates/lilo-sys/src/creds.rs` returned no matches.
- `cargo test -p lilo-im-core --test peer_creds` passed, 1 test.
- `cargo test -p lilo-im-core` passed.
- `cargo test -p lilo-sys` passed.
- `moon ci` passed, 632 tests run, 632 passed, 1 leaky, 0 skipped.

## Open Items

None. Reviewer S|B signed off on 2026-06-01. No self-push per batch ledger.
