---
title: RuntimePort Spawn Lifecycle C2
type: sessions
tags: [backend, littleorgans, runtime-port, session]
summary: WS4 C2 moved session spawn lifecycle paths off RuntimeRpc handle_rpc and proved composed spawn audit de-dup.
status: active
source: backend-engineer
confidence: high
created: 2026-05-29
updated: 2026-05-29
---

## Summary

Implemented WS4 C2 in `runtime-port-authz-audit` and amended the C2 commit to `3aa84124cdd823f04e34a05d37317aba6355dad4`.

Session spawn now calls `RuntimePort::spawn` directly. Pending spawn recovery kill calls `RuntimePort::terminate`. Pending spawn status reconciliation calls `RuntimePort::status` with `StatusFilter::for_session`.

`SpawnedProcess` now carries the full runtime `Lifecycle`, so session completion can use the lifecycle returned by either runtime adapter without an extra status fetch. The shared conversion path preserves lifecycle data for both in-process and rtmd adapters.

A reviewer DRY follow-up added `StatusFilter::for_session(session_id)` next to `StatusFilter::empty()` in `lilo-rm-core`. Both `internal/session/driver/src/conv.rs::status_session` and the spawn reconcile path now use this constructor, so the single-session status filter shape has one source of truth.

## API Contract

No public HTTP API was introduced or changed.

Internal port contract changes:

```rust
pub struct SpawnedProcess {
    pub lifecycle: Lifecycle,
    pub runtime_pid: u32,
    pub log_dir: Option<PathBuf>,
    pub stdout_path: Option<PathBuf>,
    pub stderr_path: Option<PathBuf>,
    pub tmux_pane: Option<String>,
}
```

Shared status filter construction:

```rust
impl StatusFilter {
    pub const fn for_session(session_id: Uuid) -> Self;
}
```

Session spawn lifecycle handling now depends on these `RuntimePort` calls:

```rust
runtime.spawn(&session_id, &launch)
runtime.terminate(&session_id, "SIGTERM", Duration::from_secs(5))
runtime.status(StatusFilter::for_session(session_id))
```

## Database Changes

No schema changes and no migrations.

The composed spawn audit behavior changed from two `Action::Spawn` allow rows to one session door audit row. Existing MCP protocol tests were updated to expect one spawn audit row per composed spawn.

## Security Considerations

Authorization remains at the session door from WS4 C1. This change removes duplicate downstream runtime RPC audit for composed spawn while retaining one allow audit row tied to the session resource.

The regression test `composed_spawn_writes_one_session_door_audit_row` proves a composed in-process spawn writes exactly one allowed `Action::Spawn` row for the local principal and spawned session.

## Performance Notes

Session completion no longer performs a status refetch after spawn. The runtime lifecycle returned by `RuntimePort::spawn` is passed directly into session completion.

Verification passed:

```text
fmm generate && fmm validate && just check && just build && just test
537 tests passed, 0 skipped
```

Targeted proof also passed before the amend for lifecycle mapping and de-dup regression:

```text
cargo test -p lilo-session-driver spawn -- --nocapture
cargo test -p lilo-session-daemon spawn -- --nocapture
cargo test -p lilo-session-app tools_call_can_run_list_get_and_delete_agent --test mcp_protocol_test -- --nocapture
cargo test -p lilo-session-app tools_call_can_send_read_check_mail_and_nudge --test mcp_protocol_test -- --nocapture
```

## Open Items

`spawn.rs` still appends the committed session event through `runtime_service.append_event`. The three WS4 C2 RuntimeRpc `handle_rpc` round trips were removed. The append path remains because `RuntimePort` has no event append method and session backed event ordering still depends on this write.
