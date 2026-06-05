---
title: Stream SSE response passthrough implementation
type: sessions
tags: [backend, proxy, streaming, mitmproxy, transport-matters]
summary: Implemented response stream tee capture so SSE bytes pass through while remaining persistable.
status: active
source: backend-engineer
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Summary

Implemented the Transport Matters streaming fix on branch `fix/stream-sse-response-passthrough`, PR #157.

Commits:

- `5a483a1b9e310c2fe84439ff5ca6e0f8906fcb7f`: initial stream tee implementation.
- `2375ee05db98ff6b32966540ec8576f264c93626`: follow up restore fix for empty `raw_content` edge cases.

Key decisions:

- Added `transport_matters.response_stream` as the single response tee mechanism.
- Kept stream selection in `addon_handlers.handle_response_headers` so the mechanism module has no upward imports.
- Added `responseheaders` hooks to both addons.
- Restored streamed bytes at the top of `handle_response`, preserving the existing persistence and derivation pipeline.
- Changed `restore_streamed_response` so a present tee buffer always restores `flow.response.raw_content = bytes(buffer)`, including when mitmproxy exposes `raw_content == b""`.
- Cleared stream buffers on both addon error paths.
- Pinned the mitmproxy 12.2.x streaming contract in a test docstring instead of adding a full proxy loop, because a real loop would require standing up mitmproxy plus an upstream server.

## API Contract

No public REST, GraphQL, WebSocket, or persisted API contract changed.

Internal hook contract:

```python
def handle_response_headers(flow: http.HTTPFlow) -> None: ...
def install_response_tee(flow: http.HTTPFlow, *, should_stream: bool) -> None: ...
def restore_streamed_response(flow: http.HTTPFlow) -> None: ...
def clear_response_capture(flow: http.HTTPFlow) -> None: ...
```

Selection rules:

- Require `flow.response`.
- Skip response status `101`.
- Skip request `Upgrade: websocket`.
- Require `flow.server_conn.timestamp_start` to prove an upstream round trip.
- Stream Anthropic SSE when the shared Anthropic content type helper matches.
- Stream Codex HTTP `/responses` flows regardless of content type.

Restore rule:

- If `_STREAM_BUFFER_KEY` is present and `flow.response` exists, restore `flow.response.raw_content = bytes(buffer)` unconditionally.
- If no tee buffer is present, leave any existing response body untouched.

## Database Changes

None.

## Security Considerations

- The tee only appends bytes to a flow scoped `bytearray` and returns the original chunk unchanged.
- It performs no I/O, logging, parsing, token counting, or content inspection.
- Locally crafted error responses are excluded by requiring an upstream connection timestamp.
- The stream buffer metadata key is tested against existing flow metadata keys.

## Performance Notes

- SSE bytes pass through mitmproxy immediately instead of waiting for the full body.
- Capture remains in memory for the complete response by product requirement, with no size cap.
- Existing response parsing, Codex derivation, and persistence remain unchanged after restoration.

## Verification

Initial commit verification:

- `cd api && just check` passed with `EXIT=0`.
- `cd api && just test` passed, `1608 passed in 45.18s`, `EXIT=0`.
- `fmm validate` passed with all `843` files indexed and up to date, `EXIT=0`.

Follow up commit verification:

- Focused regression suite passed: `16 passed in 0.18s`.
- `cd api && just check` passed with `EXIT=0`.
- `cd api && just test` passed, `1609 passed in 44.77s`, `EXIT=0`.
- `fmm validate` passed with all `843` files indexed and up to date, `EXIT=0`.
- `git diff --check` passed.
- Branch pushed cleanly to `origin/fix/stream-sse-response-passthrough` at `2375ee05db98ff6b32966540ec8576f264c93626`.

## Open Items

- `count_tokens` request stripping remains intentionally out of scope for a separate PR.

## Coordination

- Initial bus reply sent to `transport-matters:general:1:2.1` with `done: fix/stream-sse-response-passthrough 5a483a1b9e310c2fe84439ff5ca6e0f8906fcb7f PR#157`.
- Follow up bus reply sent to `transport-matters:general:1:2.1` on topic `tm-stream-build` with `done: 2375ee05db98ff6b32966540ec8576f264c93626 tests:1 added`.
