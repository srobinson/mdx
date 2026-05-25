---
title: Doctor Broken Pipe Warning Fix
type: sessions
tags: [backend, littleorgans, daemon, doctor, protocol]
summary: Silenced lilod broken pipe warnings from doctor reachability probes while preserving protocol fault propagation.
status: active
source: backend-engineer
confidence: high
created: 2026-05-30
updated: 2026-05-30
---

## Summary

Implemented commit `3096992` on branch `fix/roadtest` to treat a bare connect then disconnect as a benign daemon probe. The change keeps `lilo doctor` reachability behavior intact and avoids logging `lilod connection failed` with `Broken pipe` for a healthy daemon.

Key decisions:

- Kept the client side doctor probe unchanged.
- Added an optional JSON line reader for server side probes that returns `None` only when no bytes arrived.
- Moved peer credential extraction after request read in the composed daemon connection handler, so a bare probe exits before auth handling and before any response write.
- Left all response writes using `?`, so post request write failures and real mid protocol faults still propagate.

## API Contract

No public API or wire RPC was added.

Internal protocol helper:

```rust
pub async fn read_optional_json_line<R, T>(reader: &mut R) -> Result<Option<T>, ProtocolError>
where
    R: AsyncBufRead + Unpin,
    T: DeserializeOwned;
```

Behavior:

- `Ok(None)`: connection closed before any bytes were read.
- `Ok(Some(T))`: one JSON line decoded successfully.
- `Err(ProtocolError::Json(_))`: malformed or partial input after bytes arrived.
- `Err(ProtocolError::Io(_))`: I/O error after bytes arrived.

## Database Changes

None.

## Security Considerations

- Authz still runs before `handle_rpc` for every actual RPC request.
- Bare empty probes are not authorized because they do not carry a request and perform no action.
- Peer credential failures for real requests still return protocol mismatch responses.
- Post request write errors are not swallowed.

## Performance Notes

The new path adds no extra daemon round trips. It reads the incoming line once and avoids spawning response error work for empty probes.

Verification run:

- `cargo build -p lilo`
- `cargo test -p lilo-integration-tests --test session_spawn_contract doctor_reachability_probe_does_not_warn_on_bare_connect -- --nocapture`
- `just check`
- `cargo build -p xtask`
- `just test`: 551 tests passed

## Open Items

Reviewer noted an optional cleanup before the batch PR: reduce structural duplication between `read_json_line` and `read_optional_json_line` without losing the empty pre byte disconnect handling.
