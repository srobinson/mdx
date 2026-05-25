---
title: ALP-2859 Composed Lilod Structural Implementation
type: sessions
tags: [backend, littleorgans, daemon, runtime, session]
summary: Implemented the structural composed lilod checkpoint with shared session and runtime RPC routing through one LILO socket.
status: active
source: backend-engineer
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Summary

Implemented the ALP-2859 W3 C1 structural checkpoint in commit `b1d28fbbec8138b2124bbe26044f4d56a68527c6`.

Key decisions:

- Added `internal/wire` with an explicit substrate envelope so composed daemon routing is deterministic.
- Added top level `lilo daemon start`, `lilo daemon stop`, and `lilo daemon status` as the sole daemon launch surface for this checkpoint.
- Built one composed `lilod` listener on `LILO_SOCKET_PATH` backed by one shared `LiloDb`, a runtime service, and a session service.
- Kept `rtm` and `sm` binaries installable while removing their daemon launch subcommands.
- Left ALP-2859 `In Progress` because two phase `session_spawn_intents` and d9 JSONL retry dedup acceptance remain open.

## API Contract

Wire envelope:

```rust
#[serde(tag = "substrate", content = "payload", rename_all = "lowercase")]
pub enum LilodRpc {
    Session(lilo_session_core::SessionRpc),
    Runtime(lilo_rm_core::RuntimeRpc),
}
```

Command surface:

- `lilo daemon start` starts composed `lilod` in the foreground using `LILO_HOME` and `LILO_SOCKET_PATH` defaults from `LiloPaths`.
- `lilo daemon stop` sends a session shutdown RPC through the composed socket and falls back to process signals if needed.
- `lilo daemon status --output json` returns `{ "pid": Option<u32>, "running": bool, "socket_exists": bool }`.
- `rtm` and `sm` clients connect to the composed socket through their existing command surfaces.

Consistent error behavior remains delegated to the existing runtime and session response contracts.

## Database Changes

No schema migration was added in this checkpoint.

Runtime, session, and identity surfaces now share the existing unified SQLite database through `LiloDb`. `LiloDb` gained clone and close support so the composed daemon can coordinate lifecycle ownership cleanly.

The existing `session_spawn_intents` table remains unused by this structural checkpoint. Two phase session spawn semantics are the next ALP-2859 implementation step.

## Security Considerations

- Peer credential extraction remains at the composed accept boundary before request dispatch.
- Session and runtime handlers keep their existing authorization and audit behavior.
- Product path env reads for deleted `RTM_*`, `SM_*`, and `AGM_*` variables were removed under the W3 grep guard.
- The runtime shim now receives `LILO_SOCKET_PATH` instead of the legacy runtime socket variable.
- Trap guarded smoke verified daemon teardown so failed smoke runs do not leave a privileged local control socket behind.

## Performance Notes

- Composed daemon startup runs runtime service setup and session service setup in process, avoiding sibling daemon process management.
- Runtime event cursor tests were adjusted to account for the composed session event watcher by comparing watcher counts relative to a baseline.
- Duplicate `Running` runtime events no longer churn session timestamps after a session is already running with the same runtime pid.

Verification passed:

- `cargo check -p lilo && cargo build -p lilo`
- `cargo test -p lilo-session-app --test cli_namespace_test`
- `cargo test -p lilo`
- `just check && just build && just test`, `553 tests run: 553 passed, 0 skipped`
- `moon ci`, `553 tests run: 553 passed, 0 skipped`
- `fmm generate && fmm validate`
- Trap guarded daemon smoke with temporary `LILO_HOME`, fake `claude`, `lilo daemon start`, `rtm version`, `sm run --detach claude`, `sm get session --json`, and `lilo daemon stop`
- Grep guards clean for removed daemon surfaces and legacy product env reads

## Open Items

- Implement two phase session spawn around `session_spawn_intents`.
- Ensure d9 JSONL append happens after Tx B commit and is retry dedup safe.
- Add or adjust startup reconcile behavior for pending intents.
- Keep ALP-2859 open until those acceptance items pass the required verification gate.
