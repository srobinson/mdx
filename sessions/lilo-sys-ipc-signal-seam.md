---
title: lilo-sys IPC and shutdown signal seam
type: sessions
tags: [backend, littleorgans, lilo-sys, ipc, signal]
summary: Implemented the F3 production IPC and shutdown signal seam through lilo-sys.
status: active
source: backend-engineer
confidence: high
created: 2026-06-01
updated: 2026-06-01
---

## Summary

Implemented F3 on branch `refactor/lilo-sys-platform-seam` in commit `3a3d901`.

The change centralizes production Unix IPC and shutdown signal handling in `crates/lilo-sys`, then reroutes the agreed eight production callers:

- `crates/lilo-rm-client/src/lib.rs`
- `crates/lilo-im-core/src/peer_creds.rs`
- `internal/session/daemon/src/socket.rs`
- `internal/session/daemon/src/server.rs`
- `internal/runtime/daemon/src/shim_socket.rs`
- `internal/runtime/daemon/src/handler.rs`
- `internal/runtime/daemon/src/server/runner.rs`
- `internal/session/app/src/compose.rs`

`crates/lilo/src/cli/doctor.rs` was confirmed test only for raw Unix IPC and left unchanged.

Key decisions:

- Use newtype wrappers rather than type aliases so production callers no longer expose `tokio::net::UnixStream`, `tokio::net::UnixListener`, or `std::os::unix::net::UnixStream`.
- Keep path resolution in existing callers. `lilo_sys::ipc` accepts paths only.
- Preserve socket behavior: create parent directory, remove stale socket ignoring `NotFound`, bind, no chmod.
- Preserve shutdown behavior: `on_shutdown` resolves on either SIGINT or SIGTERM.
- Delete the old `internal/runtime/daemon/src/socket.rs` helper path after all production callers moved to `lilo_sys::ipc`.

## API Contract

No HTTP or RPC endpoint contract changed.

New Rust surface:

```rust
pub mod lilo_sys::ipc {
    pub struct IpcListener;
    pub struct IpcStream;
    pub struct BlockingIpcStream;

    pub fn bind(path: impl AsRef<Path>) -> std::io::Result<IpcListener>;
    pub async fn connect(path: impl AsRef<Path>) -> std::io::Result<IpcStream>;
    pub fn connect_blocking(path: impl AsRef<Path>) -> std::io::Result<BlockingIpcStream>;
    pub fn remove_socket_file(path: impl AsRef<Path>) -> std::io::Result<()>;
}

pub mod lilo_sys::signal {
    pub fn on_shutdown() -> std::io::Result<impl Future<Output = ()> + Send>;
}
```

`IpcStream` supports async read and write, split halves, and `AsRawFd` for the F2 credential primitive. `BlockingIpcStream` supports `Read` and `Write` for shim blocking paths.

## Database Changes

No database schema or migrations changed.

## Security Considerations

- Peer credential extraction remains raw fd based through `lilo_sys::creds::peer_cred`.
- `lilo_im_core::peer_creds::extract` now accepts an `AsRawFd` input instead of a tokio Unix stream, avoiding a tokio IPC type dependency in identity mapping.
- Socket file permissions are not changed. The seam preserves existing default platform bind behavior.
- Auth, request handling, response serialization, and daemon lifecycle logic remained in the owning runtime and session layers.

## Performance Notes

- IPC wrappers delegate directly to tokio Unix socket and std blocking Unix socket primitives on Unix.
- No additional runtime allocation is added on IPC hot paths beyond the existing split handling.
- The shutdown signal future is created once and pinned outside daemon select loops.

## Verification

Completed before sending `C|F3|3a3d901` to the reviewer:

- `cargo check -p lilo-sys -p lilo-im-core -p lilo-rm-client -p lilo-runtime-daemon -p lilo-session-daemon -p lilo-session-app`, green
- `cargo test -p lilo-sys -p lilo-im-core -p lilo-rm-client`, green
- `cargo clippy -p lilo-runtime-daemon -p lilo-session-app --all-targets -- -D warnings`, green
- `cargo nextest run compose_shutdown_paths_stop_tasks_before_db_pool`, green
- `fmm generate && fmm validate`, green, 373 files indexed
- Eight file leak scan for `tokio::net::Unix|std::os::unix::net|tokio::signal::unix`, empty
- `moon ci`, green, 631 tests run, 631 passed, 0 skipped
- `git show --stat HEAD`, verified no `CLAUDE.md`

## Open Items

- Reviewer `S|B` is pending for commit `3a3d901`.
- F5 must implement production only seam lint. Inline `#[cfg(test)]` raw Unix in `crates/lilo/src/cli/doctor.rs` is intentionally out of F3 scope.
