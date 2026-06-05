---
title: lilo-sys Platform Seam F1 Implementation
type: sessions
tags: [backend, rust, runtime, lilo-sys, platform-seam]
summary: Implemented the F1 published lilo-sys PAL, removed the old internal runtime platform crate, and amended CI/docs hygiene.
status: active
source: backend-engineer
confidence: high
created: 2026-06-01
updated: 2026-06-01
---

## Summary

Implemented F1 of the lilo-sys platform seam on `refactor/lilo-sys-platform-seam`.

Final amended commit: `a7799764d2cc3058074b9bd6150b0a42e319a876`.

Key decisions:

- Added published crate `crates/lilo-sys` as the PAL for pure OS primitives.
- Deleted `internal/runtime/platform` and removed active `lilo-runtime-platform` references.
- Kept runtime domain behavior inside runtime code:
  - `RuntimeSignal` to signal number mapping lives in `internal/runtime/daemon/src/signal.rs`.
  - `KillOutcome` mapping lives in runtime, not in `lilo-sys`.
  - tmux behavior lives in `internal/runtime/daemon/src/tmux.rs`.
- Added `lilo_sys::signal::SignalOutcome::{Delivered, ProcessGone}` so the PAL owns ESRCH and process-gone OS knowledge without importing runtime domain types.
- Used `std::cfg_select!` for the target seam:
  - `sys/mod.rs` selects Unix, Windows, or unsupported.
  - `sys/unix/mod.rs` holds POSIX-common behavior and selects Linux, macOS, or unsupported for other Unix.
- Folded reviewer hygiene into the same amended commit:
  - Removed the stale `.moon/workspace.yml` project entry for deleted `internal/runtime/platform`.
  - Bumped `.github/workflows/pr.yml` from `dtolnay/rust-toolchain@1.90` to `@1.95` for `cfg_select!` support.
  - Updated `docs/architecture/runtime.md` to document the `lilo-sys` versus `lilo-runtime-daemon` split.

## API Contract

No HTTP or GraphQL API changed.

New Rust crate surface:

```rust
pub mod process;
pub mod process_exit;
pub mod signal;

pub use error::{Error, Result};

pub enum ProcessStartTime {
    Known(chrono::DateTime<chrono::Utc>),
    Gone,
    Unsupported,
}

pub enum SignalOutcome {
    Delivered,
    ProcessGone,
}
```

Primary functions:

```rust
lilo_sys::process::pid_alive(pid: u32) -> bool;
lilo_sys::process::start_time_probe_for_pid(pid: u32) -> lilo_sys::Result<ProcessStartTime>;
lilo_sys::process::start_time_for_pid(pid: u32) -> lilo_sys::Result<Option<DateTime<Utc>>>;

lilo_sys::process_exit::watch_process_exit(pid: u32)
    -> lilo_sys::Result<(ProcessExitWatcher, tokio::sync::oneshot::Receiver<()>)>;

lilo_sys::signal::send_signal(pid: u32, signal: i32) -> lilo_sys::Result<SignalOutcome>;
```

## Database Changes

None.

## Security Considerations

- `lilo-sys` does not depend on `lilo-rm-core` or `lilo-port`.
- Runtime domain authorization and kill semantics remain above the PAL.
- The PAL accepts primitive process ids and signal numbers only. Domain request validation stays in runtime daemon and client layers.
- Signal delivery preserves the existing process-gone distinction without leaking runtime domain enums into the published crate.

## Performance Notes

- Linux process exit watching keeps pidfd first, then falls back to polling process liveness.
- macOS process exit watching keeps the existing kqueue strategy.
- Process start time probing keeps existing retry constants and behavior.
- `cargo test -p lilo-sys` passed.
- `cargo test -p lilo-runtime-daemon -p lilo-runtime-app` passed.
- `fmm generate && fmm validate` passed with 371 indexed files.
- `just check && just build && just test` passed with 631 tests.
- Final post docs and hygiene proof: `moon ci` passed with 6 tasks completed, 1 cached, and 631 tests passed.

## Open Items

- Reviewer and orchestrator were notified with `C|F1|a7799764d2cc3058074b9bd6150b0a42e319a876|moon ci|PASS`.
- Reviewer sign-off received: `S|B|I sign off on the lilo-sys stand-up as currently filed`.
- Orchestrator was notified that reviewer sign-off was received.
- Other Unix fallback is source-shape verified through `sys/unix/mod.rs` `_ => unsupported`; only `aarch64-apple-darwin` is installed locally, so no other Unix target build was run.
