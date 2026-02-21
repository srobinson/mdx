---
title: "Codex CLI: WS-to-HTTP Fallback Mechanism"
type: research
tags: [codex, websocket, http-fallback, transport-matters, openai, responses-api, mitmproxy]
summary: Codex CLI runs both a WebSocket Responses transport and an HTTPS Responses transport against the same path `/backend-api/codex/responses`; on WS connect or stream failure it consumes the `stream_max_retries` budget then atomically flips a session-scoped `disable_websockets` flag and replays the turn over HTTPS POST + SSE.
status: active
confidence: high
created: 2026-05-13
updated: 2026-05-13
---

# Codex CLI: WS-to-HTTP Fallback Mechanism

Source tree inspected: `openai/codex` at `main` (shallow clone, 2026-05-13). All file:line citations are against that snapshot.

## Trigger conditions

Codex falls back from WebSockets to HTTPS at the end of a turn's retry loop, not on first error. The chain:

1. A turn calls `try_run_sampling_request` from `codex-rs/core/src/session/turn.rs:1059`. Errors classified as retryable (transport timeouts, network errors, stream disconnects, WS close frames) re-enter the loop.
2. Retries are bounded by `provider.info().stream_max_retries()` (default surfaced by issues is 5; the test fixture uses 2).
3. When `retries >= max_retries` the loop calls `client_session.try_switch_fallback_transport(...)` (`turn.rs:1095`). If that returns `true`, it emits the user-visible warning:

   ```rust
   // codex-rs/core/src/session/turn.rs:1102-1106
   sess.send_event(
       &turn_context,
       EventMsg::Warning(WarningEvent {
           message: format!("Falling back from WebSockets to HTTPS transport. {err:#}"),
       }),
   )
   ```

   then resets `retries = 0` and re-enters the loop, which now uses HTTPS because the session flag changed.

4. The transport flip lives in `force_http_fallback` at `codex-rs/core/src/client.rs:405-424`:

   ```rust
   pub(crate) fn force_http_fallback(&self, ...) -> bool {
       let websocket_enabled = self.responses_websocket_enabled();
       let activated =
           websocket_enabled && !self.state.disable_websockets.swap(true, Ordering::Relaxed);
       if activated {
           warn!("falling back to HTTP");
           session_telemetry.counter(
               "codex.transport.fallback_to_http",
               1,
               &[("from_wire_api", "responses_websocket")],
           );
       }
       self.store_cached_websocket_session(WebsocketSession::default());
       activated
   }
   ```

   `disable_websockets` is an `AtomicBool` (`client.rs:179`). Once set, `responses_websocket_enabled()` (`client.rs:771-779`) returns `false` for the rest of the session and every subsequent turn routes via HTTPS.

5. Triggering categories observed in source plus user reports:
   - **WS upgrade refused at handshake** (HTTP 426 Upgrade Required from the upstream). Demonstrated by the integration test `websocket_fallback_switches_to_http_on_upgrade_required_connect` in `codex-rs/core/tests/suite/websocket_fallback.rs:28-77`. In this case the startup prewarm sees 426, immediately flips fallback, and the first turn goes straight to HTTP.
   - **WS upgrade succeeds, server closes with 1008 Policy mid-stream.** Issue [#13041](https://github.com/openai/codex/issues/13041): repeated reconnect 1/5 to 5/5, then fallback.
   - **Connect timeout / network unreachable** (e.g. proxy environments, mainland China). PR [#19821](https://github.com/openai/codex/issues/19821) proposes a `should_fallback_to_http_after_websocket_connect_error` shortcut so `TransportError::Timeout` and `TransportError::Network(_)` skip the full retry budget; as of `main` that shortcut is still proposed, not merged, so today every connect failure burns through `stream_max_retries` first.
   - **Stream disconnect mid-response** (broken pipe, idle timeout). Reported in issues [#15014](https://github.com/openai/codex/issues/15014), [#19330](https://github.com/openai/codex/issues/19330), [#19643](https://github.com/openai/codex/issues/19643).

The fallback is **one-way for the session**. There is no re-promotion back to WS after a successful HTTP turn (verified by tracing `disable_websockets`: only `swap(true)` exists; no path resets it to false within a session).

## Endpoint signatures

Both transports live at the same base URL and the same path component, distinguished only by scheme and HTTP method.

Base URL constant: `CHATGPT_CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"` (`codex-rs/model-provider-info/src/lib.rs:37`). For API-key auth users it is `https://api.openai.com/v1` (`model-provider-info/src/lib.rs:243`).

### WebSocket endpoint

- URL: scheme `wss://`, host `chatgpt.com`, path `/backend-api/codex/responses` (constructed by `Provider::websocket_url_for_path("responses")` at `codex-rs/codex-api/src/provider.rs:92-103`, which simply swaps `https` to `wss`).
- Method on the initial HTTP request: `GET` with standard RFC 6455 upgrade headers (`Upgrade: websocket`, `Connection: Upgrade`, `Sec-WebSocket-Key`, `Sec-WebSocket-Version: 13`). Built via tungstenite's `into_client_request` at `codex-rs/codex-api/src/endpoint/responses_websocket.rs:392-396`.
- Codex-specific upgrade headers: `OpenAI-Beta: responses_websockets=2026-02-06` (`client.rs:146`), `Authorization` or `ChatGPT-Account-Id`, plus `session_id`/`session-id`/`thread_id`/`thread-id` from `build_session_headers` at `codex-rs/codex-api/src/requests/headers.rs:9-14`.
- Server response headers used by client: `x-reasoning-included`, `x-models-etag`, `openai-model`, `x-codex-turn-state` (`responses_websocket.rs:434-456`).
- Compression: permessage-deflate negotiated on the WS extension (`responses_websocket.rs:457-465`).
- Startup prewarm: opportunistic, fired before the first turn from `preconnect_websocket` at `client.rs:1065-1106`. A capture tool will see a WS upgrade attempt with no immediate user-visible turn following it.

### HTTPS Responses endpoint

- URL: `https://chatgpt.com/backend-api/codex/responses` (same host, same path).
- Method: `POST`. Path returned by `ResponsesClient::path() -> "responses"` at `codex-rs/codex-api/src/endpoint/responses.rs:103`.
- Request headers: `Accept: text/event-stream` (`responses.rs:139-142`), `x-client-request-id` set to `thread_id` (`responses.rs:91-92`), the same `session_id`/`session-id`/`thread_id`/`thread-id` pair from `build_session_headers`, optional `x-openai-subagent`, and the same `Authorization` / `ChatGPT-Account-Id` auth.
- Body: `application/json` (Reqwest default for JSON body). Optional request compression `Zstd` via `RequestCompression::Zstd` (`responses.rs:124-128`).
- Response: SSE (`Content-Type: text/event-stream`), parsed by `spawn_response_stream` (`responses.rs:146-149`).

### How a capture tool can distinguish them on the wire

A proxy sees both as TLS to the same host:port. The discriminator is the request method and the `Upgrade` header on the initial HTTP exchange. The Python matcher in `transport-matters/api/src/transport_matters/codex/transport.py:43,90-98` already keys on `host == "chatgpt.com"` and `path == "/backend-api/codex/responses"`. For HTTP fallback, the same path + host + scheme matches but with `flow.request.method == "POST"` and no `Upgrade: websocket` request header. Recommendation: add a parallel `is_codex_http_flow` predicate that matches the same host/path with `method == "POST"` and routes the flow to an HTTP-aware capture path.

## Request / response shape

The WS and HTTP request bodies are near-identical OpenAI Responses API payloads. They share the same `ResponsesApiRequest` Rust struct.

### HTTP body

`ResponsesApiRequest` at `codex-rs/codex-api/src/common.rs:170-184`:

```rust
pub struct ResponsesApiRequest {
    pub model: String,
    pub instructions: String,
    pub input: Vec<ResponseItem>,
    pub tools: Vec<serde_json::Value>,
    pub tool_choice: String,
    pub parallel_tool_calls: bool,
    pub reasoning: Option<Reasoning>,
    pub store: bool,
    pub stream: bool,
    pub include: Vec<String>,
    pub service_tier: Option<String>,
    pub prompt_cache_key: Option<String>,
    pub text: Option<TextControls>,
    pub client_metadata: Option<HashMap<String, String>>,
}
```

### WS frame envelope

WS messages add a discriminator wrapper. `ResponsesWsRequest` at `common.rs:272-279`:

```rust
#[serde(tag = "type")]
pub enum ResponsesWsRequest {
    #[serde(rename = "response.create")]
    ResponseCreate(ResponseCreateWsRequest),
    #[serde(rename = "response.processed")]
    ResponseProcessed(ResponseProcessedWsRequest),
}
```

`ResponseCreateWsRequest` is `ResponsesApiRequest` plus two optional fields, `previous_response_id` and `generate` (prewarm uses `generate: false`). The conversion is at `common.rs:194-216`.

`ResponseProcessed` is a tiny ack: `{ "type": "response.processed", "response_id": "<id>" }` (`common.rs:241-244` and `responses_websocket.rs:220`). It is sent from client back to server after the client finishes consuming a `response.created`. A capture tool will see these even when no new user turn is in progress.

### Response shape

Both transports surface the same `ResponseEvent` stream internally. On the wire:
- HTTP: SSE frames with `data: { ... }` lines. Standard OpenAI Responses SSE event names (`response.created`, `response.output_item.added`, `response.completed`, etc.).
- WS: binary or text frames carrying the same JSON event objects, framed by tungstenite, deflate-compressed. There is no extra envelope around each event.

So the per-event JSON content is the same. The differences a capture tool must handle:
1. HTTP needs SSE parsing (`data: \n\n` chunks) instead of WS frame boundaries.
2. HTTP has no client-to-server frames after the initial POST. The model's response is the full SSE response body.
3. HTTP carries no `response.processed` ack.

## Streaming mechanism

Pure SSE over chunked HTTPS. `Accept: text/event-stream`, response is `text/event-stream`, `spawn_response_stream` consumes the body line-by-line. There is no polling and no chunked-JSON variant. The stream idle timeout is provider-configured (`stream_idle_timeout` field on `Provider`). A capture proxy must keep the connection open as a streamed response, not buffer the whole body, or it will deadlock mid-turn.

## Session continuity

Codex stitches the WS and HTTP halves of a fallback into one logical turn at the client. Evidence:

1. The same `session_id` and `thread_id` are sent on every request via `build_session_headers` (`requests/headers.rs:5-15`), and they originate from `state.session_id` and `state.thread_id` on `ModelClient` (`client.rs`). These are session-lifetime fields, unchanged by transport flip.
2. The `x-client-request-id` header is set to `thread_id` on the HTTP path (`responses.rs:91-92`).
3. After fallback, `force_http_fallback` clears the cached WS session (`client.rs:421-422`) but leaves session/thread IDs untouched, and the turn retry loop in `turn.rs:1108-1110` resets `retries = 0` and re-issues the same prompt via the HTTPS path.
4. The HTTP request body carries the full conversation context (the `input: Vec<ResponseItem>` array contains the entire conversation history rebuilt by `build_prompt`), so there is no protocol-level "resume from where WS left off". The HTTP request restarts the turn from the prompt.

Capture-tool implications:
- A WS turn that fell back to HTTP will produce two flows with the same `session_id`/`thread_id`/`x-client-request-id` on chatgpt.com. Stitching them into one exchange is therefore feasible by joining on those headers.
- The HTTP request will contain the full prompt input including any partial output the WS turn already streamed back (Codex re-includes assistant items that completed before the disconnect via the prompt rebuild). This means the HTTP request's `input` is a superset of the WS request's, not an "increment".
- A new conversation_id is not minted on fallback; the WS prewarm/turn `session_id` carries through.

## Configuration

There is one provider-level flag.

- `supports_websockets: bool` on `ModelProviderInfo` (`model-provider-info/src/lib.rs:135`). Default for the built-in OpenAI provider is `true` (`lib.rs:351`); default for Bedrock and OSS providers is `false` (`lib.rs:381`, `lib.rs:512`).
- In `~/.codex/config.toml` it is set on a `[model_providers.<name>]` block:

  ```toml
  [model_providers.your_provider]
  wire_api = "responses"
  supports_websockets = false
  ```

- **Catch**: the built-in `openai` provider definition appears immutable. Issue [#13103](https://github.com/openai/codex/issues/13103) reports that setting `supports_websockets = false` in `config.toml` does not override the built-in `openai` provider; the WS attempt still fires. Workaround in the wild is to define a custom provider with `wire_api = "responses"`, `supports_websockets = false`, and point Codex at it.
- There is no `disable_websockets`, `force_http`, `transport`, or equivalent top-level config flag in `model_provider_info.rs`. The Atomic-Bool `disable_websockets` on `ModelClient` is runtime-only and not user-controllable.
- `stream_max_retries`, `websocket_connect_timeout_ms`, and `stream_idle_timeout_ms` (`lib.rs:106-128`) tune how long Codex waits before falling back but do not bypass WS.

**Recommendation for transport-matters**: For controlled capture testing, point Codex at a custom provider whose `supports_websockets = false`. That eliminates the WS path entirely and makes the HTTPS POST the only thing on the wire. For production captures where the user is on the default `openai` provider and WS is the primary path with HTTP being the fallback, instrument both paths.

## Sources

File:line references (openai/codex `main` snapshot 2026-05-13):

- `codex-rs/core/src/session/turn.rs:1059` — `try_run_sampling_request` retry loop entry.
- `codex-rs/core/src/session/turn.rs:1093-1110` — fallback gate, warning emission, retry reset.
- `codex-rs/core/src/client.rs:146` — beta header constant `responses_websockets=2026-02-06`.
- `codex-rs/core/src/client.rs:147-148` — `RESPONSES_ENDPOINT = "/responses"`, `RESPONSES_COMPACT_ENDPOINT = "/responses/compact"`.
- `codex-rs/core/src/client.rs:179` — `disable_websockets: AtomicBool` state.
- `codex-rs/core/src/client.rs:405-424` — `force_http_fallback`, the atomic flip.
- `codex-rs/core/src/client.rs:771-779` — `responses_websocket_enabled` gate.
- `codex-rs/core/src/client.rs:801-863` — `connect_websocket` and connect timeout handling.
- `codex-rs/core/src/client.rs:1065-1106` — `preconnect_websocket` (startup prewarm).
- `codex-rs/codex-api/src/provider.rs:92-103` — `websocket_url_for_path` scheme swap.
- `codex-rs/codex-api/src/endpoint/responses.rs:102-150` — HTTP path, body, SSE accept header.
- `codex-rs/codex-api/src/endpoint/responses_websocket.rs:347-358` — `connect` resolves to `websocket_url_for_path("responses")`.
- `codex-rs/codex-api/src/endpoint/responses_websocket.rs:385-465` — `connect_websocket` handshake and header parsing.
- `codex-rs/codex-api/src/common.rs:170-184` — `ResponsesApiRequest` (HTTP body).
- `codex-rs/codex-api/src/common.rs:194-244` — `ResponseCreateWsRequest`, `ResponseProcessedWsRequest`.
- `codex-rs/codex-api/src/common.rs:272-279` — `ResponsesWsRequest` enum envelope.
- `codex-rs/codex-api/src/requests/headers.rs:5-15` — `build_session_headers`.
- `codex-rs/model-provider-info/src/lib.rs:37` — `CHATGPT_CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"`.
- `codex-rs/model-provider-info/src/lib.rs:106-135` — provider fields including `wire_api`, `stream_max_retries`, `websocket_connect_timeout_ms`, `supports_websockets`.
- `codex-rs/model-provider-info/src/lib.rs:318-352` — default `openai` provider (`supports_websockets: true`).
- `codex-rs/core/tests/suite/websocket_fallback.rs:28-122` — fallback integration tests, two scenarios.

GitHub issues / PRs:

- [#13041](https://github.com/openai/codex/issues/13041) — WS 1008 Policy close then HTTPS fallback (canonical reproduction).
- [#13103](https://github.com/openai/codex/issues/13103) — `supports_websockets = false` does not override the built-in openai provider.
- [#13169](https://github.com/openai/codex/issues/13169), [#13143](https://github.com/openai/codex/issues/13143), [#12273](https://github.com/openai/codex/issues/12273), [#15014](https://github.com/openai/codex/issues/15014), [#15488](https://github.com/openai/codex/issues/15488), [#19330](https://github.com/openai/codex/issues/19330), [#19643](https://github.com/openai/codex/issues/19643) — observed fallback warnings in the wild.
- [#19821](https://github.com/openai/codex/issues/19821) — proposed fast-path fallback on `TransportError::Timeout` / `TransportError::Network`. Not merged at snapshot time.
- [PR #10698](https://github.com/openai/codex/pull/10698) — origin of the WS prewarm path.

Transport-matters existing reference:

- `~/Dev/LLM/DEV/helioy/transport-matters/api/src/transport_matters/codex/transport.py:42-98` — current matcher keys on host + path, only triggers on WS flows.

## Open questions

1. **Cookie / `ChatGPT-Account-Id` propagation across fallback.** Source treats them as same-session, but I did not verify by running Codex. A capture tool should confirm that the same set-cookie values flow into the HTTPS POST.
2. **Server-Sent `response.processed` equivalent on HTTP.** Confirmed absent from the HTTP path. Worth checking whether the server expects any client-to-server ack on HTTP and how that affects upstream state (probably not, since HTTP is request/response, but worth one wire capture).
3. **`x-codex-turn-state` header on the HTTP path.** Present in WS upgrade responses (`responses_websocket.rs:447-454`); the HTTP path does not appear to read it. Confirm by capture whether it shows up on the HTTP request as a passthrough hint.
4. **Whether image-generation turns use a different path.** Issue #19643 reports image generation specifically triggers the fallback. The path appears identical, but image input is encoded inside the `input` array; worth a one-off capture to confirm there is no `/images/responses` or similar sub-path.
5. **`x-openai-subagent` header semantics.** Sent on HTTP for sub-agent paths (`responses.rs:93`). It is unclear whether this header ever appears on the WS handshake; if not, it is an extra channel-discriminator a capture tool can use.

## Actionable takeaways for transport-matters

1. **Add an HTTP-flow matcher mirroring the WS one.** Match `host == "chatgpt.com"` + `path == "/backend-api/codex/responses"` + `method == "POST"`. Capture as a streaming SSE response.
2. **Stitch by `session_id` header (or `thread_id` / `x-client-request-id`).** All three identify the same logical Codex session across the WS-to-HTTP transition. The session-id is in both the WS upgrade request headers and the HTTPS POST headers.
3. **Recommend the config-only path first.** For users who only want HTTPS captures, document the custom-provider workaround with `supports_websockets = false` and `wire_api = "responses"`. Note that overriding the built-in `openai` provider does not work (per issue #13103); a new named provider is required.
4. **Recognize the prewarm flow.** A WS upgrade attempt with no subsequent client-to-server frames before close is the startup prewarm and not a real turn. Avoid raising it as an "incomplete turn" in capture diagnostics.
5. **Expect a content-superset relationship on fallback.** The HTTPS POST body's `input` array is the same conversation seed as the WS turn would have used, not a delta. A stitched view should prefer the HTTPS request body as the canonical prompt and surface the WS frames only as partial output that did not complete.
