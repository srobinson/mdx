---
title: Notify Wait Timeout Implementation
type: sessions
tags: [backend, littleorgans, mail, runtime]
summary: Added a caller supplied timeout for mail send notify wait and propagated it through session and runtime.
status: active
source: backend-engineer
confidence: high
created: 2026-06-04
updated: 2026-06-04
---

## Summary

Implemented `lilo mail send --notify wait --timeout <secs>` and MCP `mail_send.timeout` on branch `feat/notify-timeout` in amended commit `d326557`.
The timeout is accepted in seconds at the public surface, converted once through the shared core helper `mail_timeout_seconds_to_ms`, and forwarded as milliseconds to runtime nudge wait handling. Default notify wait behavior is unchanged when no timeout is provided.

The Phase B reviewer found duplicated seconds to milliseconds conversion between CLI and MCP edges. The final commit extracts that conversion into core, reuses it from both edges, and unit tests the normal and overflow cases.

## API Contract

### CLI

```typescript
// lilo mail send <recipient> <message> --notify wait --timeout <secs>
interface MailSendCliOptions {
  notify?: "none" | "wait" | "steer";
  timeout?: number; // seconds, integer, minimum 1, requires notify="wait"
}
```

### MCP

```typescript
interface MailSendToolRequest {
  recipient: string;
  body: string;
  notify?: "none" | "wait" | "steer";
  timeout?: number; // seconds, integer, minimum 1, requires notify="wait"
}
```

### Session RPC

```typescript
interface MailSendRequest {
  recipient: string;
  body: string;
  notify?: "none" | "wait" | "steer";
  timeout_ms?: number; // milliseconds, requires notify="wait"
}
```

### Runtime RPC

```typescript
interface NudgeRequest {
  session_id: string;
  mode: "immediate" | "wait" | "steer";
  body?: string;
  timeout_ms?: number; // applies only to wait mode
}
```

Runtime protocol is now `0.7` and advertises `RuntimeCapability::NudgeWaitTimeout` as `nudge_wait_timeout`.

## Database Changes

None. No schema, migration, or index changes were required.

## Security Considerations

Input validation exists at each boundary:

- Clap enforces integer seconds and minimum value `1` for the CLI flag.
- MCP schema advertises integer seconds with minimum value `1`.
- Shared session validation rejects timeout values unless notify mode is `wait`.
- Shared core conversion rejects seconds to milliseconds overflow with a stable `SmError`.
- The session handler revalidates before forwarding runtime work.
- Notify delivery remains best effort after mail persistence, so runtime notify failures do not roll back stored mail.

## Performance Notes

The implementation reuses the existing tmux nudge wait loop. Runtime creates a derived `NudgeTiming` with the caller supplied timeout only for wait mode. No new polling path, queue, or database access was added.

Verified gates:

- `CARGO_TARGET_DIR=target/lilo cargo test -p lilo-session-core mail_timeout_seconds_to_ms`, 2 tests passed.
- `just check && just build && just test`, 641 tests passed.
- `fmm generate && fmm validate`, 384 files indexed and up to date.
- `git diff --check`, clean.
- `find . -name '*.snap.new' -print`, clean.

## Open Items

Phase B reviewer signoff is pending after bus message `C d326557` was sent to the code reviewer and orchestrator.
