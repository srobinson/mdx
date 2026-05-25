---
title: Runtime Port WS4 C1 Authz Gate
type: sessions
tags: [backend, littleorgans, authz, session, runtime-port]
summary: Added the exhaustive SessionRpc authorization classifier and door gate for WS4 C1.
status: active
source: backend-engineer
confidence: high
created: 2026-05-29
updated: 2026-05-29
---

## Summary

Implemented WS4 Card C1 on branch `feat/runtime-port-authz-audit` in commit `52f85e3023cc868f2ef145bd700c56c2b4fad80b`.

Key decisions:

- Added `internal/session/daemon/src/handler/authz.rs` with an exhaustive `authz_plan(&SessionRpc) -> AuthzPlan` match and no wildcard arm.
- Added the door gate in `handle_direct` before existing dispatch.
- Kept downstream authorization unchanged for verbs that already resolve their resource before authorizing.
- Added a small generated surface guard fallback so scoped nextest can run `xtask codegen --check` when `CARGO_BIN_EXE_xtask` is not set.

## API Contract

```rust
pub(crate) enum AuthzPlan {
    AtDoor { action: Action },
    Downstream,
}

pub(crate) fn authz_plan(rpc: &SessionRpc) -> AuthzPlan;
```

Door authorized verbs:

- `List`, `NamespaceList`: `Action::List`
- `NamespaceGet`, `Wait`: `Action::Read`
- `MailCheck`, `MailStopCheck`: `Action::MailRead`
- `NamespaceCreate`: `Action::Kill`

All door checks use `ResourceSpec::default()`. Downstream verbs remain `Spawn`, `NamespaceDelete`, `Delete`, `MailSend`, `MailRead`, `Nudge`, `Label`, `Logs`, `Capture`, `Doctor`, `McpBridge`, and `Shutdown`.

## Database Changes

No schema changes and no migrations.

Runtime behavior now writes denied identity audit rows for the 7 previously ungated verbs when authorization fails at the session door.

## Security Considerations

The session RPC door now rejects unknown or non-local principals before read or namespace create handlers execute. The exhaustive match means adding a future `SessionRpc` variant fails to compile until its authorization boundary is declared.

`NamespaceCreate` intentionally uses `Action::Kill` to match the locked WS4 plan and the existing `NamespaceDelete` action vocabulary.

## Performance Notes

The new door check adds one identity authorization call only for the 7 coarse door-gated verbs. No extra store reads are introduced before authorization.

Verification:

- `cargo test -p lilo-session-daemon authz -- --nocapture`: passed 3 selected tests.
- `just check && just build && just test`: passed, 158 nextest tests.
- `fmm generate && fmm validate`: passed after adding the new files.

## Open Items

- WS4 C2 still needs the spawn lifecycle self-RPC calls moved to `RuntimePort`.
- WS4 C3 still needs cleanup and doc truth-up by the orchestrator.
- Namespace action vocabulary cleanup remains carried forward.
