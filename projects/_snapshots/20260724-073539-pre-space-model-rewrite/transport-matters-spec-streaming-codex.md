---
title: Transport Matters streaming response capture for Claude and Codex
type: design
tags: [transport-matters, backend, mitmproxy, streaming, codex]
summary: Design for passing SSE responses through mitmproxy incrementally while retaining complete wire response artifacts.
status: active
source: backend-engineer
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

# Transport Matters streaming response capture for Claude and Codex

## Summary

The current addon path buffers streamed Anthropic responses in mitmproxy before any bytes reach Claude Code. The fix is to install a shared `responseheaders` streaming tee that forwards each response chunk immediately, accumulates the exact bytes in flow metadata, and lets the existing response completion path persist those bytes after mitmproxy fires `response`.

The design keeps one durable invariant: the complete provider response body still lands in Tier 1 as `response.raw`, is parsed into `response.ir.json` when possible, and can still drive Codex HTTP derivation.

## Root cause confirmation

Verified against the current tree and mitmproxy 12.2.2.

Evidence from Transport Matters code:

- `api/src/transport_matters/addon.py` `TransportMattersAddon.response` only calls `handle_response`. There is no `responseheaders` member on `TransportMattersAddon`.
- `api/src/transport_matters/shared_proxy/addon.py` `SharedProxyAddon.response` only resolves the binding, calls `handle_response`, then finishes the flow. There is no `responseheaders` member on `SharedProxyAddon`.
- `api/src/transport_matters/addon_handlers.py` `handle_response` persists only after the response body has already reached mitmproxy's full response hook.
- `api/src/transport_matters/exchange_recorder_artifacts.py` `extract_response` reads `flow.response.get_text()`, so the persistence path assumes a buffered response body.
- Repository search found no `flow.response.stream` assignment under `api/src` or `api/tests`.

Evidence from mitmproxy 12.2 API behavior:

- `Message.stream` defaults to `False`. With `False`, mitmproxy buffers the full body before forwarding.
- `Message.stream` must be set from `requestheaders` or `responseheaders`; setting it in `request` or `response` is already too late.
- `responseheaders` fires when headers are available and the body is still empty.
- When response streaming is active, `response` fires after the whole body has streamed, but mitmproxy does not retain the body in `raw_content`.
- A stream transform callable is synchronous and receives body chunks. Packet boundaries are not semantic.

The current code therefore confirms the reported failure mode: streamed SSE responses are handled only in the late `response` hook, so mitmproxy buffers them. During a long model turn, Anthropic keepalive frames are held inside mitmproxy, the client sees an idle stream, then retries.

## Existing response persistence path

Current complete path:

1. `api/src/transport_matters/addon_handlers.py` `handle_http_request` parses the request through `parse_request_ir`, runs `run_pipeline`, captures a `RequestFlowState`, and creates a provisional exchange through `persist_http_provisional_exchange`.
2. `handle_response` calls `persist_http_exchange` for normal Claude HTTP and Codex HTTP responses.
3. `api/src/transport_matters/exchange_recorder.py` `persist_http_exchange` calls `_finalize_http_provisional_exchange` when a provisional exchange exists.
4. `_finalize_http_provisional_exchange` calls `extract_response`, then `derive_codex_http`, then builds `ExchangeArtifacts` with `response_raw`, `response_ir`, optional Codex `transport`, optional Codex `events`, and optional Codex `turn`.
5. `api/src/transport_matters/storage/disk.py` `DiskStorageBackend.persist_exchange` writes the atomic exchange directory, and `DiskStorageBackend._write_exchange_files` writes `response.raw` and `response.ir.json` when present.
6. `api/src/transport_matters/storage/exchange_sink.py` `emit_to_index` hands the completed exchange to the optional sink.
7. `api/src/transport_matters/addon_runtime.py` `_make_exchange_cursor_sink` uses the persisted wire exchange to register a transcript cursor with the tailer. `_start_session_capture` wires that tailer to `SessionWriter`, which commits transcript events to Postgres.

The streaming design should preserve steps 1 through 7. Only step 4 receives response bytes from a new source when the body was streamed.

## Internal contract

```python
@dataclass(slots=True)
class ResponseBodyCapture:
    flow_id: str
    started_at: float
    streamed: bool
    body: bytearray


def maybe_install_response_stream_capture(flow: http.HTTPFlow) -> bool:
    """Install a synchronous tee for response bodies that must pass through incrementally."""


def captured_response_body(flow: http.HTTPFlow) -> bytes | None:
    """Return the accumulated streamed body, or None for a non-streamed response."""


def clear_response_stream_capture(flow: http.HTTPFlow) -> None:
    """Drop accumulator state after response or error finalization."""
```

Ownership:

- New module: `api/src/transport_matters/streaming_capture.py`.
- It must import only stdlib typing, logging, time, and `mitmproxy.http`.
- It must not import adapters, request pipeline, storage, breakpoint, server, or Codex modules.
- Both addon entry points call this one helper. No copied tee functions.

State shape:

- Store `ResponseBodyCapture` under one private metadata key on `flow.metadata`.
- The stream callable appends `bytes(chunk)` into `body` and returns the original chunk unchanged.
- The callable must never log or inspect chunk contents.
- The callable must not perform async work, storage writes, JSON parsing, token counting, or event emission.
- There is no cap in the accumulator. Transport Matters' product invariant is complete response bytes. If memory pressure becomes a concern later, the next design should tee to a spool file, not truncate.

Install predicate:

- Require `flow.response`.
- Require a `RequestFlowState` on the flow.
- Exclude successful Codex websocket upgrade flows: `is_codex_websocket_flow(flow)` and not `is_codex_http_responses_flow(flow)`.
- Prefer response header evidence: install when `content-type` contains `event-stream`.
- Allow an additional guard on `request_state.request_ir.stream` if Anthropic ever omits the event stream content type, but do not stream unrelated JSON responses by default.
- Do not install when `flow.response.stream` is already set by another addon. Log one warning and leave that flow on the old buffered path.

## Addon hook design

### `TransportMattersAddon`

Add `responseheaders`:

```python
async def responseheaders(self, flow: http.HTTPFlow) -> None:
    maybe_install_response_stream_capture(flow)
```

Keep `request`, `response`, and `error` as the durable lifecycle hooks. `responseheaders` only starts the tee. `response` remains responsible for persistence because mitmproxy fires it after the streamed body completes.

### `SharedProxyAddon`

Add `responseheaders`:

```python
async def responseheaders(self, flow: http.HTTPFlow) -> None:
    binding = self._resolve_existing_flow(flow)
    if binding is None:
        self._fail_http(flow)
        return
    maybe_install_response_stream_capture(flow)
```

Do not call `finish_flow` in `responseheaders`. The existing `SharedProxyAddon.response` and `SharedProxyAddon.error` `finally` blocks should remain the only finish points.

Why this preserves demux:

- `SharedProxyAddon.request` already calls `_resolve_new_flow` and `_stamp_flow`, placing run id and listen port metadata on the flow.
- `responseheaders` uses `_resolve_existing_flow`, the same binding path used by `response` and `error`.
- Because `finish_flow` remains in `response` and `error`, the binding table retains the flow mapping while chunks stream.
- If a flow cannot be mapped, `_fail_http` keeps the current 502 behavior.

## Persistence changes

Thread the optional captured bytes into the existing persistence path.

Recommended signatures:

```python
async def handle_response(
    flow: http.HTTPFlow,
    token_counter: TokenCountingClient | None,
    binding: ProxyRunBinding | None = None,
) -> None:
    raw_response = captured_response_body(flow)
    ...
    await persist_http_exchange(
        flow,
        request_state,
        token_counter,
        binding,
        raw_response_body=raw_response,
    )
```

```python
async def persist_http_exchange(
    flow: http.HTTPFlow,
    request_state: RequestFlowState,
    token_counter: TokenCountingClient | None,
    binding: ProxyRunBinding | None = None,
    *,
    raw_response_body: bytes | None = None,
) -> bool:
```

```python
def extract_response(
    flow: http.HTTPFlow,
    adapter: Any,
    exchange_id: str,
    *,
    raw_response_body: bytes | None = None,
) -> tuple[bytes, InternalResponse | None, ResStats | None]:
```

`extract_response` behavior:

- If `raw_response_body` is not `None`, use it exactly.
- Otherwise keep the current buffered behavior through `flow.response.get_text()`.
- Content type still comes from `flow.response.headers`.
- `parse_response_ir` remains the only response parser. `AnthropicAdapter.inbound_response` already dispatches event streams to `AnthropicAdapter._inbound_response_sse`.

`_finalize_http_provisional_exchange` should receive the same `raw_response_body` keyword and pass it to `extract_response`. The non-provisional branch should do the same.

`clear_response_stream_capture(flow)` should run in `handle_response` after persistence finishes, ideally in a `finally`, so large bytearrays are released promptly.

## Codex interactions

### Codex websocket

Do not alter the websocket path.

Relevant current symbols:

- `api/src/transport_matters/addon_handlers.py` `handle_codex_websocket_message`
- `api/src/transport_matters/addon_handlers.py` `handle_codex_websocket_end`
- `api/src/transport_matters/codex/transport.py` `record_codex_websocket_message`
- `api/src/transport_matters/codex/exchange.py` `finalize_codex_provisional_exchange`
- `api/src/transport_matters/codex/exchange_derivation.py` `rewrite_codex_provisional_exchange`

The new response body tee must not install on normal websocket upgrade flows. Those flows derive durable artifacts from websocket messages, not from an HTTP body.

### Codex HTTP or SSE

For `is_codex_http_responses_flow(flow)`, use the same HTTP response capture path as Claude.

The captured bytes feed existing Codex derivation:

- `api/src/transport_matters/exchange_recorder_artifacts.py` `derive_codex_http`
- `api/src/transport_matters/codex/transport.py` `build_codex_http_transport_artifacts`
- `api/src/transport_matters/codex/http_derivation.py` `derive_codex_http_turn`

This preserves the existing Codex provisional finalize and rewrite behavior. The only difference is that `raw_res` comes from the tee for streamed HTTP responses.

## Breakpoint interactions

Current breakpoint behavior is request side:

- `api/src/transport_matters/pause_session.py` `handle_breakpoint` pauses after request parsing and before upstream release.
- `resolve_paused_flow` decides final IR and mutation flag.
- `_release_payload` returns bytes only when the operator or override pipeline changed the outbound request.
- `handle_breakpoint` mutates `flow.request` and updates `RequestFlowState` before the upstream response exists.

Streaming response capture starts later, in `responseheaders`. That means:

- If the operator releases unchanged, the tee captures the provider's response to the original request.
- If the operator edits the request, the tee captures the provider's response to the edited request, while persistence still records original and curated request artifacts from `RequestFlowState`.
- If the operator drops the flow, `handle_breakpoint` creates a local 400 response in the request hook. There is no upstream response to stream, and the existing dropped provisional cleanup path remains correct.
- Token counting during pause remains request based through `fire_pause_count` and does not depend on response streaming.

No response editing hook exists in the current code path. If response editing is added later, it cannot share this pass through tee unchanged, because changing streamed response bytes requires a transform policy and changes the product invariant from capture only to capture plus mutation.

## Error and non streaming response interactions

Non streaming responses:

- Do not set `flow.response.stream` for ordinary JSON response bodies.
- Let `flow.response.get_text()` continue to feed `extract_response`.
- Existing HTTP error response status tagging remains in `tag_http_error_status`.

Streaming response with clean completion:

- The tee forwards chunks immediately.
- The `response` hook receives completion notification.
- `captured_response_body` supplies full bytes to persistence.

Streaming response with mitmproxy `error`:

- Keep the current `error` semantics: delete any provisional exchange and do not persist a completed `response.raw`.
- Call `clear_response_stream_capture(flow)` in both addon error paths after provisional cleanup.
- In the shared proxy addon, keep `finish_flow` in the existing `error` `finally` block.

Shared proxy generated 502:

- `_fail_http` produces a local text response when demux fails.
- Do not install the streaming tee for that generated response.

## Request mutation interaction

`handle_http_request` may mutate `flow.request` through `outbound_request_if_changed` after `run_pipeline` or after breakpoint release. The response tee is independent of that mutation.

The durable request state remains anchored in `RequestFlowState`:

- `raw_request` stores the original request body parsed by `parse_request_ir`.
- `curated_request_ir`, `audit`, and `mutated_manually` are updated by `update_request_flow_state`.
- `build_request_artifacts` persists original and curated request artifacts.

The response tee should not reread or reinterpret the request body in `responseheaders`.

## Count tokens verdict

This is a separate bug from response buffering.

Observed facts:

- The live mitmdump log has repeated `POST https://api.anthropic.com/v1/messages/count_tokens` 400 responses on 2026-06-19.
- Current captured Claude request bodies contain provider extras with `context_management`, `output_config`, and `thinking`.
- `api/src/transport_matters/adapters/anthropic.py` `AnthropicAdapter.outbound_request` restores `ir.provider_extras` verbatim into the payload used by `stamp_pipeline_tokens`.
- `api/src/transport_matters/counting.py` `_strip_for_count` removes only `max_tokens`, `stream`, sampling fields, and stop sequences.
- `api/src/transport_matters/counting.py` `relevant_auth_headers` is capable of forwarding `anthropic-beta` if present, but it cannot synthesize beta opt ins that are required by provider extra fields and missing from the original request.

Diagnosis:

- The count payload still includes fields the count endpoint rejects for the current Claude Code request shape, especially `context_management` and `output_config`.
- Some provider extras are beta gated. If the count request includes those fields without the exact required `anthropic-beta` values, Anthropic returns 400.

Recommended fix:

- Fix separately from the streaming tee to keep verification focused.
- Replace `_strip_for_count` with an allow list for fields accepted by `/v1/messages/count_tokens`, rather than growing a deny list.
- Keep `model`, `system`, `messages`, `tools`, and `tool_choice` when present.
- Include `thinking` only when the original request had the required beta header and a count endpoint test proves it is accepted.
- Strip `context_management`, `output_config`, `stream`, `max_tokens`, sampling fields, stop sequences, and metadata for count requests unless Anthropic documentation and tests prove support.
- Add a unit test that feeds a current Claude Code shaped payload with `context_management`, `output_config`, and `thinking`; assert the count request body excludes unsupported fields and that the `anthropic-beta` header policy is explicit.

This bug only leaves pipeline token counts unset. It does not explain the 60 second streamed response stall.

## Files touched

Expected implementation files:

- `api/src/transport_matters/streaming_capture.py`, new shared helper.
- `api/src/transport_matters/addon.py`, add `responseheaders` and cleanup in `error`.
- `api/src/transport_matters/shared_proxy/addon.py`, add `responseheaders` using existing demux resolution and cleanup in `error`.
- `api/src/transport_matters/addon_handlers.py`, read captured body once and pass it into persistence.
- `api/src/transport_matters/exchange_recorder.py`, thread `raw_response_body` into provisional and non provisional HTTP persistence.
- `api/src/transport_matters/exchange_recorder_artifacts.py`, let `extract_response` consume explicit response bytes.

Expected test files:

- `api/src/transport_matters/test_streaming_capture.py`, unit coverage for tee install, accumulation, cleanup, and no install for normal JSON.
- `api/src/transport_matters/test_exchange_recorder_http_provisional_finalize.py`, finalize a provisional exchange from captured streamed bytes and assert `response.raw` plus `response.ir.json` exist.
- `api/src/transport_matters/test_exchange_recorder_http_provisional_codex.py`, Codex HTTP event stream still derives transport events and turn artifacts from captured streamed bytes.
- `api/src/transport_matters/codex/test_transport_addon.py`, assert websocket flows do not install the response tee.
- `api/src/transport_matters/test_shared_proxy_streaming_capture.py`, shared proxy `responseheaders` resolves the binding without finishing the flow, then `response` finishes it.

If any listed test file would exceed 700 lines after adding coverage, split before adding tests.

## Test plan

Fast unit checks:

1. New helper test: construct an HTTP flow with event stream response headers, install the tee, invoke the stream callable with three chunks, assert each return value equals the original chunk, then assert `captured_response_body` equals concatenated bytes.
2. New helper test: construct an application JSON response and assert no stream callback is installed.
3. New helper test: construct a Codex websocket upgrade flow and assert no stream callback is installed.
4. Provisional Claude HTTP test: persist a provisional exchange, simulate a streamed SSE body through the helper, run `handle_response`, then assert `DiskStorageBackend.read_exchange` returns `response_raw` equal to the full SSE byte sequence and a parsed `response_ir` with usage.
5. Codex HTTP test: simulate `/backend-api/codex/responses` with event stream bytes and assert existing Codex HTTP derivation artifacts still exist.
6. Shared proxy unit test: after `responseheaders`, assert the binding table still resolves the flow. After `response`, assert `finish_flow` removed it.
7. Error test: install the tee, append one chunk, call addon `error`, assert the provisional exchange was deleted and the capture metadata cleared.

Integration proof:

1. Add a tiny local streaming upstream endpoint for a mitmdump harness. It should emit SSE frames with at least one gap longer than 60 seconds in wall clock only for manual proof. For CI, use short gaps and assert incremental delivery timing.
2. Run mitmdump with `TransportMattersAddon`, send a `stream: true` Claude shaped request through the proxy, and have the client read from the response iterator.
3. Assert the client receives the first SSE frame before the upstream endpoint completes the response.
4. Assert the persisted exchange's `response.raw` equals the full concatenated SSE body after completion.
5. Assert `response.ir.json` exists and includes final usage parsed by `AnthropicAdapter._inbound_response_sse`.
6. Repeat the same harness through `SharedProxyAddon` with a registered binding.

Manual road test:

1. Start Transport Matters normally.
2. Launch captured Claude Code through the proxy.
3. Run a prompt that reliably thinks for longer than 60 seconds and streams keepalive frames.
4. Confirm the Claude Code client remains attached and does not emit `200 OK (content missing)`.
5. Confirm the run directory contains complete `response.raw` and parsed `response.ir.json` for that turn.
6. Confirm the UI still receives exchange events after persistence.

Repo gates:

- `fmm validate`
- `cd api && just check`
- `cd api && just test`
- A targeted mitmproxy streaming integration test from the new test file if it is not already included in `just test`.

## Open questions

- If future provider responses are content encoded, the tee captures the bytes mitmproxy streams. The current `extract_response` fallback captures decoded text. The implementation should decide whether `response.raw` means exact streamed body bytes or decoded response body. The product wording says full wire response bytes, so the streamed path should preserve exact chunks and the non streamed path should be considered existing behavior debt.
- If memory pressure appears with very large event streams, replace the bytearray accumulator with a spool file and return bytes to persistence only at completion. Do not truncate.
