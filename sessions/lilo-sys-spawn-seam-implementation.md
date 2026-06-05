---
title: lilo-sys Spawn Seam Implementation
type: sessions
tags: [backend, rust, lilo-sys, runtime, shim, platform-seam]
summary: Moved shim Unix spawn primitives into lilo-sys while preserving runtime termination policy.
status: active
source: backend-engineer
confidence: high
created: 2026-06-01
updated: 2026-06-01
---

## Summary

Implemented F4 of the lilo-sys platform seam batch in commit `84b67eb` on branch `refactor/lilo-sys-platform-seam`.

The change moves shim owned Unix spawn primitives into `lilo-sys`:

- Process image replacement through `lilo_sys::process::exec_replace`.
- Exit status signal extraction through `lilo_sys::process::exit_signal`.
- Child user interrupt reset before exec through `lilo_sys::process::reset_child_user_interrupts_before_exec`.
- Synchronous signal disposition installation through `lilo_sys::signal::install_disposition`.

`internal/runtime/app/src/cli/shim.rs` keeps the 5 second SIGTERM grace window, polling cadence, atomic flag behavior, and SIGKILL escalation policy. Runtime signal sends remain routed through `lilo_runtime_daemon::signal::send_signal(RuntimeSignal::Term/Kill)`, preserving the F1 boundary where RuntimeSignal mapping stays in runtime.

## API Contract

Rust surface added to `lilo-sys`:

```rust
pub fn reset_child_user_interrupts_before_exec(command: &mut Command);
pub fn exec_replace(command: &mut Command) -> std::io::Error;
pub fn exit_signal(status: ExitStatus) -> Option<i32>;

pub enum Signal {
    Interrupt,
    Quit,
    Terminate,
}

pub enum SignalDisposition {
    Default,
    Ignore,
    Handler(extern "C" fn(i32)),
}

pub fn install_disposition(
    signal: Signal,
    disposition: SignalDisposition,
) -> std::io::Result<()>;
```

The existing raw process signal delivery API remains unchanged:

```rust
pub fn send_signal(pid: u32, signal: i32) -> Result<SignalOutcome>;
```

## Database Changes

None.

## Security Considerations

The shim no longer imports production `std::os::unix::process` extensions or raw `libc::signal` and `libc::SIG*` identifiers. OS specific signal disposition and exec behavior are centralized behind `lilo-sys`.

The pre exec child closure captures no Rust state and only resets SIGINT and SIGQUIT to default disposition through a raw helper. The shim SIGTERM handler still only flips an atomic flag.

## Performance Notes

No runtime allocation or polling behavior changed. The termination loop still uses the existing 100 ms poll and exact 5 second grace window before best effort SIGKILL escalation.

## Verification

Commands run before commit:

```text
cargo test -p lilo-sys
cargo test -p lilo-runtime-app
cargo clippy -p lilo-sys -p lilo-runtime-app --all-targets -- -D warnings
fmm generate && fmm validate
moon ci
```

Results:

```text
cargo test -p lilo-sys: passed, 3 unit tests plus 1 integration test.
cargo test -p lilo-runtime-app: passed, including all 4 shim tests.
cargo clippy focused run: passed.
non-test shim forbidden identifier check: passed.
fmm generate && fmm validate: passed, 373 files indexed and current.
moon ci: passed, 632 tests run, 632 passed, 0 skipped.
```

Commit proof:

```text
84b67eb refactor: move shim spawn primitives into lilo-sys
7 files changed, 160 insertions, 45 deletions
```

Only intended files were committed. `CLAUDE.md` was not staged or committed.

## Signoff

Reviewer `littleorgans:helioy-tools:backend-engineer:9:6.1` sent `S|B|I sign off on the spawn seam as currently filed` after reviewing commit `84b67eb`. Orchestrator `littleorgans:general:9:4.1` was notified that F4 is complete locally. No push was performed.

## Open Items

None for F4. Awaiting the next batch item or orchestrator directive.
