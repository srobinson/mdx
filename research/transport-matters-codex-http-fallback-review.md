---
title: Transport Matters — Codex HTTP Fallback Architectural Review (Python)
type: research
tags: [transport-matters, codex, http-fallback, responses-api, capture]
summary: Maps the additive surface area required to capture Codex's HTTPS Responses fallback alongside the existing WebSocket capture path. Identifies seven concrete code changes for Slice 1, the storage protocol widening, and the seam for deferred turn-timeline parity.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-13
updated: 2026-05-13
---

# Transport Matters: Codex HTTP Fallback — Architectural Review (Python)

## Foundation

Transport Matters has two mature capture surfaces sharing one adapter contract (`ProviderAdapter` in `api/src/transport_matters/adapters/base.py`). The Anthropic path is plain HTTP and runs end-to-end through `addon.request` → `handle_http_request` → `_persist_http_provisional_exchange` → `_persist_http_exchange`. The Codex path is WebSocket and routes through `addon.websocket_*` → `handle_codex_websocket_*` → `_persist_codex_*` in `codex/exchange.py`. Both paths converge on the same storage primitives: `ExchangeArtifacts`, `IndexEntry`, and the per-exchange directory layout.

Codex 0.128.0 occasionally falls back from WS to HTTPS for the same `chatgpt.com/backend-api/codex/responses` endpoint. Today that fallback is detected as a failed handshake. The `error` and `response` hooks see `is_codex_websocket_flow(flow) is True` (path/host match) but `flow.websocket is None`, so `_persist_codex_handshake_failure` writes a stub `codex/transport-handshake` exchange instead of capturing the real HTTP request and response. The HTTP gate in `handle_http_request` at `addon_handlers.py:68` short-circuits on `path.startswith("/v1/messages")`, so the Anthropic-style flow never runs for Codex HTTP either.

The additive change is a third dispatch path: detect Codex HTTPS Responses traffic alongside the existing WS detection, route request capture through a new HTTP-aware sibling of `_persist_codex_provisional_exchange`, and reuse the Anthropic HTTP response-handling shape (final raw response only for Slice 1). The WS lifecycle stays untouched. The storage `protocol` literal widens from `"websocket"` to `"websocket" | "http"`, with `http` carrying a `null` upgrade block.

## Current state — by layer

### Codex WS path

- Matcher: `is_codex_websocket_flow(flow)` at `codex/transport.py:90-98`. Path-only check (`host == "chatgpt.com" and path == "/backend-api/codex/responses"`). It does NOT inspect `Upgrade: websocket` headers, so any flow to that endpoint matches — including the HTTP fallback request. This is the key seam.
- Adapter: `CodexAdapter` at `codex/adapter.py:16-29`. `matches()` returns `is_codex_websocket_flow(flow)`. `inbound_request` delegates to `parse_codex_request` (which parses any Codex `response.create` JSON body, not WS-specific). `inbound_response` raises `NotImplementedError`.
- Adapter dispatch: `_adapters = [CodexAdapter(), AnthropicAdapter()]` at `adapters/__init__.py:16-19`. Codex wins for the Codex host.
- Lifecycle hooks (`addon.py:60-92`):
  - `websocket_start` → `log_websocket_start` → `ensure_codex_transport_state` at `codex/transport.py:108-129` snapshots upgrade headers.
  - `websocket_message` → `handle_codex_websocket_message` at `addon_handlers.py:143-234`. Detects the initial `response.create` client frame via `is_codex_turn_start`, parses it through the adapter, runs the pipeline, persists a provisional exchange (`_persist_codex_provisional_exchange` at `codex/exchange.py:64-150`), and applies breakpoint logic.
  - `websocket_end` → `handle_codex_websocket_end` → `_finalize_codex_provisional_exchange` at `codex/exchange.py:289-437`.
  - `error` hook at `addon.py:85-91` skips Codex WS flows entirely. The HTTP fallback flow would have `is_codex_websocket_flow(flow) is True`, so today it also gets skipped here — which is correct behavior we must preserve once the new path owns its own error handling.
  - `response` hook at `addon_handlers.py:278-289` calls `_persist_codex_handshake_failure` when the flow is Codex by URL but has no `websocket` attribute. This is currently how the HTTP fallback gets persisted as a stub failure row.
- Transport state lives in `flow.metadata[CODEX_TRANSPORT_METADATA_KEY]` as a `CodexTransportState` dataclass. Tracks turn windows, message counts, provisional/finalized exchange IDs.
- Turn derivation: pure engine in `codex/derivation_engine.py` consumes `CodexTransportMessageFact` records built from `TransportArtifacts.messages`. The engine has no WS-specific code — it operates on `payload_json + direction + ts + event_type` tuples. `_codex_transport_message_facts` at `codex/exchange_derivation.py:132-154` is the adapter from `TransportArtifacts → derivation facts`. This is the seam where SSE chunks would feed in for deferred parity.
- Internal module layout (codex/):
  - `protocol.py` — pure constants, terminal/start predicates, payload helpers. Format-agnostic.
  - `request_parser.py` / `request_serializer.py` — JSON ⇄ IR for `response.create`. Already format-agnostic; reusable as-is for HTTP request capture.
  - `response_parser.py` — `parse_codex_response_payloads(payloads, ...)` consumes a `list[dict]` of server JSON events. Source format (WS frames vs SSE chunks) does not matter; the parser only needs the payload dicts.
  - `transport.py` — WS-specific (mitmproxy `WebSocketMessage`). Builds `TransportArtifacts`, `ResStats`, `InternalResponse`.
  - `derivation.py`, `derivation_engine.py`, `derivation_contract.py`, `derivation_codec.py` — pure derivation. Format-neutral.
  - `exchange.py` — persistence orchestration. WS-specific because it pulls turn windows from `CodexTransportState`.
  - `exchange_derivation.py` — derivation glue. Mostly format-neutral; depends on `TransportArtifacts.messages`.

### Anthropic HTTP path

- Matcher: `AnthropicAdapter.matches` at `adapters/anthropic.py:55-56`. Path-only (`/v1/messages`).
- Lifecycle is one HTTP request followed by one HTTP response (streaming or buffered). Entry points:
  - `addon.request` → `handle_http_request` at `addon_handlers.py:64-127`. Parses raw body via `parse_request_ir`, runs the override pipeline, persists a provisional via `_persist_http_provisional_exchange`, optionally hits the breakpoint, and writes the curated body back to the request.
  - `addon.response` → `handle_response` → `_persist_http_exchange` at `exchange_recorder.py:183-276`. Reads `flow.response.get_text()`, runs the response through the adapter (`_parse_response_ir`), and finalizes the existing provisional row.
  - `addon.error` → `_delete_http_provisional_exchange` cleans up dangling provisionals.
- Streaming handling: `_inbound_response_sse` at `adapters/anthropic.py:165-243` parses Anthropic SSE deltas into `InternalResponse`. This is Anthropic-specific (knows about `message_start`, `content_block_delta`, etc.). The shape of "buffer the full SSE body, then parse" is the reusable pattern. For Codex HTTP, mitmproxy buffers the response body before `addon.response` fires, so the same buffer-then-parse approach applies. The SSE parser itself must be Codex-specific (different event names) and is part of Slice 2.
- Generic surface to leverage:
  - `_persist_http_provisional_exchange` at `exchange_recorder.py:279-338` — request-only IndexEntry + artifacts persistence. Provider-agnostic.
  - `_persist_http_exchange` and `_finalize_http_provisional_exchange` at `exchange_recorder.py:183-276` and `365-441` — full HTTP exchange flow. Provider-agnostic — they call through the adapter.
  - `flow_state.RequestFlowState` and `capture_request_flow_state` — same metadata keys for HTTP and WS flows. Already supports the Codex case via `capture_codex_initial_request_ir`.
  - Breakpoint plumbing (`handle_breakpoint` for HTTP, `handle_websocket_breakpoint` for WS) — HTTP variant is the one to reuse for Codex HTTP.

### Storage schema

- `TransportArtifacts` at `storage/base.py:225-230`:
  ```python
  class TransportArtifacts(BaseModel):
      provider: str
      protocol: Literal["websocket"] = "websocket"
      upgrade: TransportUpgradeArtifacts
      close: TransportCloseArtifacts | None = None
      messages: list[TransportMessageArtifact] = Field(default_factory=list)
  ```
- Only production-code usage of the literal: this definition. Every other hit is in test fixtures (`storage/test_disk_*.py`, `api/v1/test_exchanges_*.py`, `codex/test_diagnostics.py`, `codex/test_repair_support.py`) which seed `"protocol": "websocket"` in dict form. The literal is purely descriptive — no branching code reads it today.
- Required widening:
  - `protocol: Literal["websocket", "http"] = "websocket"` (keep WS as default for backward compat with reads, even though the cm note says no backcompat — the literal is loaded from disk for existing exchanges, so the default avoids needing migration of historical `transport.json` files; tag this as a Pydantic-default decision, not a deprecation window).
  - `upgrade: TransportUpgradeArtifacts | None` — HTTP has no upgrade handshake. Or split into `TransportArtifacts.upgrade: TransportUpgradeArtifacts | None` and let HTTP populate request/response status without the WS-shaped upgrade dataclass. Recommend `Optional`.
  - `close: TransportCloseArtifacts | None` — already optional. HTTP can either leave it null or populate a slimmer HTTP-close variant.
  - `TransportMessageArtifact` at `storage/base.py:205-214`: `direction: Literal["client", "server"]`, `is_text`, `size_bytes`, `event_type`, `payload_text/json/base64`. These fields are protocol-agnostic. Reusable verbatim. For HTTP SSE in Slice 2, each parsed SSE chunk becomes one `TransportMessageArtifact` with `direction="server"`.
- Other shape divergence between Codex and Anthropic in storage:
  - `IndexEntry.codex_turn` at `storage/base.py:122` is Codex-only. Slice 1 HTTP exchanges can leave it `None` (matches deferred derivation work).
  - `ExchangeArtifacts.events`, `turn` at `storage/base.py:157-158` are Codex derivation outputs. Slice 1 leaves both `None`.
- Disk layout at `storage/disk_layout.py:32-44` already supports `transport.json` for any provider. No change needed.
- API surface at `api/v1/exchanges.py:120` — `ExchangeDetailResponse.transport: TransportArtifacts | None`. The widened literal flows through without code change. `build_codex_transport_diagnostics` at `codex/diagnostics.py:21-26` filters by `transport.provider == "codex"`, not protocol — also flows through without change, though some diagnostic strings reference "websocket handshake" and need protocol-aware wording (Slice 2).

### Adapter dispatch

- `get_adapter(flow)` at `adapters/__init__.py:22-32` iterates `_adapters` in order and returns the first match. Codex is first.
- Today's flow for a Codex HTTP fallback request (i.e., no Upgrade header):
  1. `addon.request` fires → `handle_http_request` → `flow.request.path.startswith("/v1/messages")` is False → early return. No adapter called, no provisional persisted.
  2. `addon.response` fires → `handle_response` → `is_codex_websocket_flow(flow) and flow.websocket is None` → True → `_persist_codex_handshake_failure`. Persists a stub IR with `model=codex/transport-handshake`.
  3. `addon.error` (if it errored) → returns early at the `is_codex_websocket_flow` guard.
- The path/host check is currently doing double duty: it identifies "this flow targets Codex" without distinguishing HTTP from WS. A new predicate `is_codex_http_responses_flow(flow)` can disambiguate by checking the absence of the `Upgrade: websocket` request header (or, post-response, the absence of `flow.websocket`).
- Slot for the new matcher: `codex/transport.py` adjacent to `is_codex_websocket_flow`. Mechanically simplest: extract a shared `_is_codex_responses_target(flow)` helper, then derive both WS and HTTP variants from it.
- Adapter registration: `CodexAdapter` already handles request parsing for `response.create` JSON, regardless of transport. The matcher needs to widen to include HTTP fallback flows (otherwise `get_adapter()` raises `UnsupportedProviderError` for them). Option A: widen `CodexAdapter.matches` to `is_codex_responses_flow(flow)` (covers both WS and HTTP). Option B: register a second adapter instance. Recommend A — same wire format, same parser, just different transport.

## Required changes — by slice

### Slice 1 (this work)

- [ ] Add `is_codex_http_responses_flow(flow)` to `api/src/transport_matters/codex/transport.py` adjacent to `is_codex_websocket_flow`.
  - **Why**: Distinguish HTTP fallback from WS upgrade at request-time so dispatch picks the right lifecycle. Detect HTTP fallback by `host == chatgpt.com and path startswith /backend-api/codex/responses and "websocket" not in flow.request.headers.get("upgrade", "").lower()`.
  - **Risk**: Codex may not send an explicit `Upgrade: websocket` header for WS in all client versions. Verify against a captured WS handshake fixture (`tests/fixtures/codex_transport_chatgpt_success.json`) before relying on this discriminator. If unreliable, fall back to `flow.request.method == "POST"` (WS handshakes are GET; HTTP fallback is POST).

- [ ] Widen `CodexAdapter.matches` in `api/src/transport_matters/codex/adapter.py` to match either WS or HTTP Codex flows.
  - **Why**: `get_adapter()` must return `CodexAdapter` for the HTTP fallback so `inbound_request` parses the `response.create` body. The existing WS matcher excludes HTTP.
  - **Risk**: Low. The request parser is already format-neutral.

- [ ] Add a Codex HTTP branch in `handle_http_request` at `api/src/transport_matters/addon_handlers.py:64`.
  - **Why**: The `/v1/messages` gate at line 68 must let Codex HTTP through. Cleanest implementation: invert the gate to `if not (flow.request.path.startswith("/v1/messages") or is_codex_http_responses_flow(flow)): return`. Everything downstream (`parse_request_ir`, `run_pipeline`, `_persist_http_provisional_exchange`, `handle_breakpoint`, `adapter.outbound_request`) is provider-agnostic and works for Codex by virtue of `CodexAdapter` already implementing the contract.
  - **Risk**: The provisional persisted via `_persist_http_provisional_exchange` will have `transport=None`. For Codex this is the additive case; the WS path still owns `transport` for WS exchanges. Confirm `ExchangeDetailResponse` and the WWW front-end handle `transport=None` for `provider=codex` (today the WS path always sets `transport`; the handshake-failure path sets transport).

- [ ] Update `handle_response` at `api/src/transport_matters/addon_handlers.py:278-289` so Codex HTTP flows route to `_persist_http_exchange`, not `_persist_codex_handshake_failure`.
  - **Why**: Currently any Codex flow without a `flow.websocket` triggers the handshake-failure stub. For HTTP fallback we want the normal HTTP finalization. Detect with `is_codex_http_responses_flow(flow)` and delegate to `_persist_http_exchange` (which finalizes the provisional row written in the request hook).
  - **Risk**: Must preserve the existing handshake-failure behavior for genuine WS upgrade failures (path matches WS, no Upgrade success, no fallback POST). The discriminator is: HTTP fallback flows had a provisional written in `request`, genuine handshake failures did not. Check `request_state is None` to disambiguate.

- [ ] Update `addon.error` at `api/src/transport_matters/addon.py:85-91` so Codex HTTP flows clean up their provisional.
  - **Why**: Today the guard at line 86 skips Codex flows entirely. The HTTP fallback now writes a provisional that must be cleaned up on error. Change to `if is_codex_websocket_flow(flow) and not is_codex_http_responses_flow(flow): return`. The remaining branch already calls `_delete_http_provisional_exchange`.
  - **Risk**: Low. The cleanup path is the same one Anthropic uses.

- [ ] Widen `TransportArtifacts.protocol` in `api/src/transport_matters/storage/base.py:227` to `Literal["websocket", "http"]` and make `upgrade: TransportUpgradeArtifacts | None`.
  - **Why**: Future Slice 2 will emit `TransportArtifacts` for HTTP Codex flows (one `TransportMessageArtifact` per SSE chunk). The schema must accept HTTP today even if Slice 1 leaves `transport=None`. Setting it up now avoids a second migration.
  - **Risk**: Any code branching on `transport.protocol == "websocket"` would break. Verified above — no production code does. Test fixtures load via `model_validate`, so unchanged fixture JSONs continue to validate against the widened union.

- [ ] Decide whether the existing `_persist_codex_handshake_failure` should still run for HTTP-fallback flows that fail before any response.
  - **Why**: An HTTP fallback POST that errors with a 4xx or 5xx is operationally interesting. Today it would write a stub `codex/transport-handshake` row. Recommend: leave `_persist_codex_handshake_failure` to its single purpose (genuine WS upgrade with `status != 101`), and let HTTP fallback errors flow through `_persist_http_exchange` like any Anthropic error. The existing `_http_error_response_stats` already captures `http_4xx/5xx` as a stop reason.
  - **Risk**: Loss of the dedicated "Codex fallback HTTP failed" diagnostic. Acceptable for Slice 1; revisit if operator feedback demands it.

### Slice 2 (deferred — full turn parity)

- [ ] Build `parse_codex_response_sse_chunks(raw_body: bytes) → list[dict]` in `api/src/transport_matters/codex/response_parser.py` (sibling to `parse_codex_response_payloads`).
  - **Why**: Codex HTTP Responses streams SSE events with the same payload shape as WS frames. Parse the buffered SSE body into the same `list[dict]` the existing parser already consumes.
- [ ] Implement `CodexAdapter.inbound_response` to detect `event-stream` content and call the SSE parser, then `parse_codex_response_payloads`. The non-stream path covers buffered JSON Responses payloads.
- [ ] Synthesize `TransportArtifacts(protocol="http", ...)` from the SSE chunks: one `TransportMessageArtifact` per chunk, `direction="server"`, `event_type=payload["type"]`. Wire this into `_persist_http_exchange` for Codex flows via a small `build_codex_http_transport_artifacts(flow, raw_response)` helper in `codex/transport.py`.
- [ ] Feed the synthesized `TransportArtifacts.messages` through `_codex_transport_message_facts` (already format-neutral) into `derive_codex_turn_replay`. The derivation engine and contract need no changes — they consume `CodexTransportMessageFact` records, not WS frames.
- [ ] Map HTTP response end → derivation close fact. `TransportCloseArtifacts` works for both protocols; for HTTP set `close_code=None`, `closed_by_client=None`, populate `client/server_message_count` from the parsed SSE chunks.
- [ ] Extend `build_codex_transport_diagnostics` at `codex/diagnostics.py` to emit HTTP-aware diagnostics. Today its strings reference "websocket upgrade" verbatim. Branch on `transport.protocol`.

## Leverage opportunities — do not reinvent

- `parse_codex_request` at `api/src/transport_matters/codex/request_parser.py:47-76` — already format-neutral. Parses the `response.create` JSON body whether it came from a WS frame or an HTTP POST body. Reuse verbatim.
- `serialize_codex_request` at `api/src/transport_matters/codex/request_serializer.py` — same. Round-trip back to wire bytes works for both transports.
- `parse_codex_response_payloads` at `api/src/transport_matters/codex/response_parser.py:29-92` — already consumes `list[dict[str, Any]]` of server payloads. Slice 2 only needs an SSE-chunk-to-dict-list pre-parser.
- `_persist_http_provisional_exchange` at `api/src/transport_matters/exchange_recorder.py:279-338` — provider-agnostic. Use directly for Codex HTTP request capture.
- `_persist_http_exchange` and `_finalize_http_provisional_exchange` at `api/src/transport_matters/exchange_recorder.py:183-441` — provider-agnostic. Use directly for Codex HTTP response capture.
- `capture_request_flow_state` at `api/src/transport_matters/flow_state.py:43-73` and the entire `RequestFlowState` dataclass — already used by both HTTP and Codex WS. No changes needed.
- `handle_breakpoint` at `api/src/transport_matters/pause_session.py` — HTTP variant. Codex HTTP can hit it identically.
- `derive_codex_turn_replay` and the derivation engine at `api/src/transport_matters/codex/derivation_engine.py` — format-agnostic. Slice 2 plugs into this seam through `_codex_transport_message_facts` at `codex/exchange_derivation.py:132-154`.
- `TransportMessageArtifact` at `api/src/transport_matters/storage/base.py:205-214` — the shape is protocol-neutral. Reusable as the SSE-chunk record type in Slice 2.
- `_http_error_response_stats` at `api/src/transport_matters/exchange_recorder.py:131-143` — generic 4xx/5xx capture. Covers Codex HTTP error responses without modification.

## Open questions

- **HTTP fallback handshake mechanics**: when Codex 0.128.0 falls back, does it send a fresh request ID or reuse the prior session/turn IDs from `client_metadata`? This matters for Slice 2 turn-index continuity but does not block Slice 1. Capture a real fallback transcript before wiring derivation.
- **Discriminator reliability**: confirm WS upgrade requests carry `Upgrade: websocket` end-to-end through mitmproxy at the `addon.request` hook. mitmproxy may strip or transform Upgrade headers in some versions. If the header is unreliable, `flow.request.method == "POST"` is a safer discriminator (WS upgrade is GET, fallback Responses is POST).
- **HTTP response shape**: does Codex's Responses HTTP path stream SSE or return a single JSON body when `stream=false`? `parse_codex_response_payloads` handles both, but `inbound_response` needs to branch on `Content-Type` in Slice 2. Anthropic adapter at `adapters/anthropic.py:135-137` is the template.
- **fmm indexing**: this review was conducted via direct `Read` because the fmm MCP server resolved the database path to `~/Dev/LLM/DEV/helioy/.fmm.db` rather than `~/Dev/LLM/DEV/helioy/transport-matters/api/.fmm.db`. The api index exists and is current (`421888` bytes, modified 2026-04-15). Worth opening an fmm config issue so subsequent reviews can use `fmm_file_outline` directly.
- **Front-end implications**: the WWW UI lives in `~/Dev/LLM/DEV/helioy/transport-matters/www/`. Slice 1 ships exchanges with `provider=codex, transport=None`. Confirm the exchange detail view degrades gracefully when `transport` is null on a Codex row (today this only happens for handshake-failure stubs, which already render).
- **Storage round-trip for the widened protocol literal**: a Pydantic `Literal["websocket", "http"]` default of `"websocket"` is the safest choice for reading legacy `transport.json` files written before the change. The cm note `feedback_no_backcompat` argues against deprecation windows, but here the default is structural (Pydantic schema literal), not a backcompat shim. Confirm with Stuart whether to keep the default or require explicit `protocol` on all writes and migrate historical files.
