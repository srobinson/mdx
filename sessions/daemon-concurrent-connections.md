---
title: Daemon Concurrent Connections
type: sessions
tags: [backend, littleorgans, mail, daemon, sqlite]
summary: Fixed the session daemon mail tail deadlock with concurrent connection handling and immediate write transactions.
status: active
source: backend-engineer
confidence: high
created: 2026-06-04
updated: 2026-06-04
---

## Summary

Implemented item 1 of `mailbugs-signoff` on branch `fix/mail-observability-bugs`.
Commit: `2e90bbe fix(session): serve daemon connections concurrently`.

Key decisions:

- `server.rs` now accepts connections concurrently instead of awaiting each handler in the accept loop.
- Connection tasks are managed by `JoinSet`, completed tasks are reaped, per connection errors are logged, and shutdown aborts then drains remaining tasks.
- Shutdown is signaled only after `write_response` completes, preserving the client acknowledgement before daemon cleanup.
- Mail tail follow subscribes before querying, closing the append lost wakeup window.
- Mail write paths that require read then write atomicity now use `BEGIN IMMEDIATE` through `lilo_db::ImmediateTx`.
- Existing partial unique index `idx_messages_sender_idempotency` remains the defense in depth idempotency guard.

## API Contract

No public API shape changed.

Relevant existing RPCs exercised by tests:

```typescript
// Mail tail follow blocks until matching append or timeout.
interface MailTailRequest {
  filter: MailLogFilter;
  after?: MailLogCursor;
  follow: boolean;
  waitMs?: number;
}

// Mail send remains unchanged.
interface MailSendRequest {
  to: Selector;
  content: string;
  notify?: NotifyMode;
  timeoutMs?: number;
  contextId: string;
  intent: MailIntent;
  idempotencyKey?: string;
}
```

## Database Changes

No new migration was required.

The schema already contains:

```sql
CREATE UNIQUE INDEX idx_messages_sender_idempotency
    ON messages(sender_ref, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
```

Runtime write discipline changed:

- `insert_mail_for_recipients_with_outcome` now starts with `BEGIN IMMEDIATE`.
- Non peek `read_unread_mail` now starts with `BEGIN IMMEDIATE` before fetch then mark read.
- Top level spawn intent insert, resolve, and abort now start with `BEGIN IMMEDIATE`.
- Existing `_in` variants remain unchanged to avoid nested transactions inside caller owned transactions.

`ImmediateTx` rolls back on explicit error and queues rollback on drop, so aborted task futures do not leave partial commits.

## Security Considerations

- No authorization surface changed.
- Per connection errors no longer stop the daemon, reducing malformed client denial of service risk.
- Shutdown still uses the existing handler authorization path.
- Idempotency is now protected by both immediate writer serialization and the existing unique index.

## Performance Notes

- Long poll mail tail requests no longer block the accept loop.
- Reads still run concurrently under WAL.
- `BEGIN IMMEDIATE` serializes only write transactions that need atomic read then write behavior.
- Connection task completion is reaped during serving to avoid accumulated finished task handles.

## Verification

Focused proof:

- `cargo test -p lilo-session-daemon` passed.
- `cargo test -p lilo-session-store` passed.

Full proof:

- `just check && just build && just test` passed.
- Nextest summary: 650 tests run, 650 passed.
- `fmm generate && fmm validate` passed with 385 indexed files.

Regression coverage added:

- Follow tail plus concurrent mail send through the real daemon accept loop.
- Malformed request survival followed by a successful request.
- Shutdown acknowledgement before daemon exit.
- Concurrent idempotent mail sends collapse to one message and two deliveries.

## Open Items

- Reviewer audit pending for commit `2e90bbe`.
- Public session daemon socket framing still remains as previously implemented. The new regression uses raw `SessionRpc` framing to match current `server.rs` behavior.
