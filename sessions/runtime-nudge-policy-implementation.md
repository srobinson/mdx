---
title: Runtime nudge policy implementation
type: sessions
tags: [backend, runtime, tmux, mail-protocol, ALP-2906]
summary: Implemented runtime wait and steer nudge behavior with busy classification and timeout outcomes.
status: active
source: backend-engineer
confidence: high
created: 2026-06-02
updated: 2026-06-02
---

## Summary

Implemented local batch item 2/3 for ALP-2906.

Commits:

- `a4925d5` `feat(runtime): honor nudge wait and steer modes`
- `b7877c2` `fix(runtime): classify long claude busy timers`

Key decisions:

- Runtime owns pane policy. Session continues to pass mode over the runtime port.
- `ServerState::nudge_runtime` threads `NudgeRequest.mode` and `Lifecycle.runtime` into `TmuxGateway::nudge`.
- Nudge policy lives in `internal/runtime/daemon/src/tmux_nudge.rs`.
- Busy classification lives in `internal/runtime/daemon/src/tmux_busy.rs` so the UI scrape is isolated for replacement later.
- Existing tmux payload behavior remains the single send path: literal payload, hex CR, Enter.
- Claude spinner rows require an enumerated glyph plus `… (` followed by a timer whose first character is an ASCII digit. This covers `52s`, `3m 29s`, and hour style timers while rejecting non timer parentheticals.

## API Contract

No new wire fields were added in this item. Item 1 had already added the required runtime wire contract:

```typescript
type NudgeMode = "immediate" | "wait" | "steer";

type NudgeFailureReason =
  | "headless_lifecycle"
  | "session_ended"
  | "tmux_pane_dead"
  | "agent_busy_timeout";

interface NudgeRequest {
  sessionId: string;
  content: string;
  mode: NudgeMode;
}

interface NudgeResponse {
  delivered: boolean;
  outcome:
    | { kind: "delivered" }
    | { kind: "failed"; reason: NudgeFailureReason }
    | { kind: "unsupported"; reason: NudgeFailureReason };
}
```

Runtime behavior now matches the contract:

- `immediate`: deliver using the existing copy mode guard and payload path.
- `wait`: poll until idle, then deliver. On timeout, return `delivered: false` and `failed: agent_busy_timeout` without sending the payload.
- `steer`: if busy, send one Escape, wait for idle, then deliver. If still busy at timeout, return `delivered: false` and `failed: agent_busy_timeout` without sending the payload.

## Database Changes

None.

## Security Considerations

- Session still does not scrape panes. Runtime keeps the tmux UI coupling behind the runtime boundary.
- Payload delivery continues to use literal `tmux send-keys -l`, hex CR, then Enter, preserving the existing shell metacharacter safety behavior.
- Capture or probe errors degrade to best effort delivery so a transient scrape failure does not suppress durable mail notification. `steer` skips Escape when the initial probe fails.
- Timeout paths do not send payloads, preserving the guarantee that persisted mail is not silently treated as delivered to a busy agent.

## Performance Notes

- `wait` uses a 1 second poll interval with a 2 minute cap and requires 2 consecutive idle probes.
- `steer` uses a 250 ms poll interval with a 5 second cap and requires 2 consecutive idle probes after interrupt.
- Busy probing uses `capture_pane(Some(20))` and only examines the bottom visible nonblank rows.
- File size checks remain within limits: `tmux.rs` 479 LOC, `tmux_nudge.rs` 473 LOC, `tmux_busy.rs` 161 LOC.

Verification for `a4925d5`:

- `cargo test -p lilo-runtime-daemon`
- `just check`
- `fmm generate && fmm validate`
- `just build`
- `just test`

Verification for `b7877c2`:

- `cargo test -p lilo-runtime-daemon tmux_busy`
- `cargo test -p lilo-runtime-daemon`
- `just check`
- `fmm generate && fmm validate`

All passed.

## Open Items

- Phase B peer signoff was pending after `C|2|b7877c2` was sent.
- The busy classifier remains a tmux UI scrape and should be replaced when a runtime shim or transport turn signal exists.
