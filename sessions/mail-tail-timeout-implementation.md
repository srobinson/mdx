---
title: Mail Tail Timeout Implementation
type: sessions
tags: [backend, cli, mcp, mail, observability]
summary: Replaced mail tail once semantics with timeout semantics across CLI and MCP surfaces.
status: active
source: backend-engineer
confidence: high
created: 2026-06-04
updated: 2026-06-04
---

## Summary

Implemented amended commit `a927ec5` on branch `feat/mail-observability` to replace `mail tail` once vocabulary with timeout vocabulary across CLI and MCP surfaces.

CLI semantics:

- No `--timeout`: follow forever with no daemon deadline. The CLI loop owns long running follow behavior.
- `--timeout 0`: single fetch with no `tokio::time::timeout` wrapper.
- `--timeout N` where `N > 0`: follow with one wall clock client deadline, wrapping each in flight tail request with the remaining budget.
- JSON output remains single shot. `--output json --timeout N` is deadline bounded and emits an empty `MailTail` response if the deadline elapses before mail arrives.

MCP semantics:

- `timeout` omitted: snapshot only.
- `timeout: 0`: snapshot only.
- `timeout: N` where `N > 0`: one bounded follow request.

The old MCP `once` parameter was removed. The daemon now accepts `MailTailRequest.wait_ms` so MCP can bound a single RPC without reusing CLI follow forever semantics.

## API Contract

CLI contract:

```text
lilo mail tail [--context-id <id>] [--selector <selector>] [--recipient <selector>] [--include-system] [--timeout <secs>]
```

Removed CLI contract:

```text
lilo mail tail --once
```

Removal is proven by the diff plus green suite. No standing deletion guard test remains.

MCP `mail_tail` input contract:

```json
{
  "context_id": "review-thread",
  "selector": "role:reviewer",
  "recipient": "role:engineer",
  "include_system": false,
  "namespace": "default",
  "all_namespaces": false,
  "timeout": 1
}
```

`timeout` is optional. Omitted or zero returns a snapshot. Positive values bound one follow request.

Internal RPC contract:

```rust
pub struct MailTailRequest {
    pub filter: MailLogFilter,
    pub after: Option<MailLogCursor>,
    pub follow: bool,
    pub wait_ms: Option<u64>,
}
```

CLI passes `wait_ms: None`. MCP passes `Some(timeout * 1000)` only for positive timeouts.

## Database Changes

None.

## Security Considerations

No authorization or persistence path changed. Tail requests still go through the existing daemon RPC and operator observation authorization. The new daemon deadline only bounds waiting on mail append events.

## Performance Notes

The CLI computes one `Instant` deadline and uses remaining budget for each request, so a steady stream cannot extend the requested wall clock budget. The daemon computes one `sleep_until` deadline before the MCP append loop, so non matching append events cannot reset the timeout.

## Verification

- `cargo test -p lilo-session-app --lib cli::cli_def::tests::mail_tail_timeout_flag_maps_values -- --nocapture`
- `cargo test -p lilo-session-app --test cli_help_surface_test mail_help_matches_protocol_v1_surface -- --nocapture`
- `cargo test -p lilo-session-app --test mcp_protocol_test mail::tools_call_can_send_read_check_mail_and_nudge -- --nocapture`
- `cargo test -p lilo-session-app -- --nocapture`
- `cargo run -q -p lilo -- mail tail --help`
- `just codegen`
- `just build`
- `INSTA_UPDATE=always cargo test -p lilo-session-app --test mcp_schema_snapshot_test -- --nocapture`
- `just check && just build && just test` with 562 tests passed
- `fmm generate && fmm validate`

## Open Items

Reviewer Phase B re-review is pending on bus topic `mail-obs-signoff` for amended commit `a927ec5`.
