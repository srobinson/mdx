---
title: Littleorgans dry fix2 session daemon app implementation
type: sessions
tags: [backend, littleorgans, rust, session-daemon, dry]
summary: Refactored duplicated production code in session daemon and app CLI lane, then verified lane clippy clean.
status: active
source: backend-engineer
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Summary

Implemented the `dry-fix` Phase 2 `session-daemon-app` lane across the assigned files only. The changes deduplicate production code in session spawn transaction setup, selector fanout error aggregation, mail count response construction, MCP mail selector scoping, optional string array parsing, and daemon unexpected response formatting for capture and logs.

Key decisions:

- Kept changes inside the assigned lane.
- Reused the existing P1 `session_tool_response_error` helper from `mcp_tools/agent.rs` without editing that file.
- Used `capture::unexpected_daemon_response` as the shared app CLI helper because the lane allowed only `capture.rs` and `logs.rs` on the app side.
- Held while `lilo-rm-core` was temporarily broken by another lane, then reran verification after the unblock ping.

## API Contract

No external API changed.

Internal helper changes:

```rust
// internal/session/daemon/src/handler/spawn.rs
async fn begin_spawn_tx(
    &self,
    label: &'static str,
    acquire_context: &'static str,
) -> Result<sqlx::pool::PoolConnection<sqlx::Sqlite>>;

// internal/session/daemon/src/handler/sessions.rs
async fn collect_target_sessions<F, Fut>(
    &self,
    selector: &Selector,
    apply: F,
) -> Result<(Vec<Session>, Vec<TargetError>)>;

// internal/session/daemon/src/handler/messaging.rs
async fn mail_count_response<F>(&self, selector: &Selector, response: F) -> Result<RpcResponse>;

// internal/session/daemon/src/mcp_tools/mail.rs
async fn mail_count_from_args(
    state: &DaemonState,
    context: &RequestContext,
    arguments: &serde_json::Value,
    request: impl FnOnce(Selector) -> SessionRpc,
) -> Result<serde_json::Value>;

// internal/session/daemon/src/mcp_tools/args.rs
fn optional_string_array<T>(
    arguments: &serde_json::Value,
    field: &str,
    entry_description: &str,
    parse: impl Fn(&str) -> Result<T>,
) -> Result<Vec<T>>;

// internal/session/app/src/cli/capture.rs
pub(super) fn unexpected_daemon_response(response: &RpcResponse) -> anyhow::Error;
```

## Database Changes

None.

## Security Considerations

- Authorization paths remain unchanged.
- Spawn intent transaction boundaries preserve the existing `BEGIN IMMEDIATE` and `finish_immediate_tx` semantics.
- Per target delete, label, mail, and nudge behavior remains unchanged.

## Performance Notes

- Selector fanout and mail count loops remain sequential with the same store and driver call behavior.
- Refactor removes repeated control flow without adding meaningful allocations beyond the existing response vectors.
- All edited files remain below the 700 line limit.

## Verification

Required clippy command:

```bash
cargo clippy -p lilo-session-daemon -p lilo-session-app --all-targets -- -D warnings
```

Result: clean, finished dev profile in 17.57s.

Line counts:

```text
427 internal/session/daemon/src/handler/spawn.rs
168 internal/session/daemon/src/handler/sessions.rs
228 internal/session/daemon/src/handler/messaging.rs
132 internal/session/daemon/src/mcp_tools/mail.rs
133 internal/session/daemon/src/mcp_tools/args.rs
 52 internal/session/app/src/cli/capture.rs
 58 internal/session/app/src/cli/logs.rs
```

Bus report sent:

```text
session-daemon-app P2: 7 files, clippy clean
```

## Open Items

None for this lane. No git operations, cargo fix, cargo fmt, or workspace rewrite were run.
