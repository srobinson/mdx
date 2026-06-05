---
title: Stream SSE responses through the capture proxy (fix 60s SSE stall)
type: spec
status: synthesis-for-consensus
source: orchestrator-synthesis
inputs:
  - transport-matters-spec-streaming-claude.md
  - transport-matters-spec-streaming-codex.md
created: 2026-06-20
---

# Spec: stream SSE responses through the capture proxy, still capturing full wire bytes

This is a SYNTHESIS of the two independent MoE design specs, filed for peer-consensus
sign-off. Repo: `transport-matters` (`api/`). Design only; no code here.

## Root cause (both specs confirmed, condensed)

The addon registers only a `response` hook and never sets `flow.response.stream`, so
mitmproxy 12.2 fully BUFFERS every upstream response before delivering a byte to the
client. For `stream:true` SSE turns, Anthropic's keepalive pings are held inside
mitmproxy; during a long model-thinking turn the client sees zero bytes for ~60s, hits
its stream-idle timeout, and aborts (`200 OK content missing`), then retries identically.
Evidence: per-run mitmdump debug log shows server disconnect at exactly 60.000s after the
synthesis turn (msgs=17); fast turns (<60s) return real content; direct works; bare
mitmdump and a body-reading addon both stream 614KB fine. The differentiator is response
BUFFERING, not size. Capture works today only *because* of buffering: `extract_response`
reads `flow.response.get_text()` after the full body is present.

## Chosen design

### 1. One shared helper module (no duplication)
New `api/src/transport_matters/response_stream.py`, the single home for streaming capture.
Imports only `mitmproxy` + stdlib. Exposes:
- `install_response_tee(flow) -> None`
- `restore_streamed_response(flow) -> None`
- `clear_response_capture(flow) -> None`
- `_STREAM_BUFFER_KEY` (dedicated `flow.metadata` key). It must not collide with ANY
  `transport_matters_*` flow.metadata key — the full `flow_state.py` namespace
  (`_ADAPTER_KEY`, `_REQUEST_IR_KEY`, `_PROVISIONAL_EXCHANGE_ID_KEY`, …) plus
  `FLOW_RUN_ID_METADATA_KEY` / `FLOW_LISTEN_PORT_METADATA_KEY`. [consensus: both reviewers]

### 2. `responseheaders` hook on both addons -> `install_response_tee(flow)`
Thin delegation in both `addon.py` and `shared_proxy/addon.py`, mirroring the existing
thin `request`/`response`/`error` pattern. Demux is NOT resolved here; binding resolution
and `finish_flow` stay in `response`/`error` exactly as today.

`install_response_tee` install predicate (**SSE-OR-Codex gated** — consensus-revised):
- `flow.response` present; else return.
- Skip websocket upgrades: `flow.response.status_code == 101` or request carried
  `Upgrade: websocket`.
- POSITIVELY exclude locally-crafted responses (breakpoint-drop 400, shared-proxy 502).
  CORRECTION (Codex): mitmproxy 12.2.2 DOES fire `HttpResponseHeadersHook` for an
  inline-script-set `flow.response` (`HttpStream.state_consume_request_body`), so the hook
  runs for them too — do NOT rely on "responseheaders never fires". Exclude by a positive
  upstream-roundtrip signal: `flow.server_conn.timestamp_start is not None` (verified by
  Claude vs mitmproxy 12.2.2 — defaults None, set only once `make_server_connection` runs,
  so it is None for `Response.make` locals). This guard is NECESSARY, not redundant: a
  Codex breakpoint-drop / `_fail_http` local response still matches
  `is_codex_http_responses_flow` (which reads the request path, not the response) and would
  otherwise be teed. Cover with a test.
- Install when EITHER:
  (a) **Anthropic SSE** — reuse the adapter's exact test `"event-stream" in content_type`
      (`AnthropicAdapter.inbound_response`, `adapters/anthropic.py`), NOT a separate
      `text/event-stream` literal, to prevent gate/parser drift [Claude]; OR
  (b) **Codex** — `is_codex_http_responses_flow(flow)` is true REGARDLESS of content-type,
      because mitmproxy strips Content-Type from some streamed bodies and
      `CodexAdapter.inbound_response` parses by body shape [Codex]; without this, Codex
      `/responses` SSE stays buffered and still stalls.
  Non-SSE, non-Codex JSON stays on the existing buffered path (`restore_streamed_response`
  no-ops for it, so the persist pipeline is unchanged).
- DAG placement: the tee / restore / clear MECHANICS stay in `response_stream.py`
  (mitmproxy + stdlib only). The predicate needs `is_codex_http_responses_flow` and the
  adapter SSE test, which live below the addon layer — compute `should_stream` at the
  addon/handler layer (which may import adapters/codex) and pass it into a mechanism-only
  installer, OR import them into `response_stream.py` only if that keeps the DAG acyclic.
  Keep `response_stream.py` free of upward (server-layer) imports.

Tee closure: append each non-empty chunk to a flow-scoped `bytearray` stashed at
`flow.metadata[_STREAM_BUFFER_KEY]`, return the chunk unchanged (byte-for-byte
pass-through). End-of-body is a terminal `b""`; accumulate, never assume framing.
No size cap (product invariant: complete wire bytes). Pure sync byte ops; no I/O,
parsing, logging of chunk contents, or token counting in the tee.

### 3. Re-hydration spine (Claude's approach) — pipeline stays byte-for-byte unchanged
At the VERY TOP of `handle_response` (`addon_handlers.py`), one shared call:
`restore_streamed_response(flow)` pops the buffer and, when the response streamed
(`flow.response.raw_content is None`), sets `flow.response.raw_content = bytes(buffer)`.
This makes `flow.response.content`/`get_text()` decode normally (content-encoding aware),
so `extract_response`, `_finalize_http_provisional_exchange`, `derive_codex_http`,
`parse_response_ir`, and token-usage parsing are UNCHANGED. Token usage continues to come
from the parsed response body (message_start/message_delta), not from count_tokens.

### 4. Error-path cleanup (both reviewers)
Both addons' `error` hooks call `clear_response_capture(flow)` in a `finally` (or before
EVERY early-return guard — the `is_codex_websocket_flow` guard and the
`request_state is None or provisional_exchange_id is None` guard). NOT merely "after
provisional deletion": both error hooks early-return on those guards, which would skip the
cleanup and leak the buffer, defeating the prompt-release intent.

### 5. Hard rules
- Only `flow.response.stream` is ever set. NEVER `flow.request.stream` — the request must
  stay buffered for pipeline parse + `flow.request.set_text(...)` mutation in the request
  hook.
- Breakpoint is request-side only (`handle_breakpoint` mutates `flow.request` or sets a
  synthetic 400 in the `request` hook). No interaction with response streaming. If a
  future feature edits the RESPONSE, that flow must opt out of streaming — out of scope.

## Files touched (streaming fix)
| File | Change |
| --- | --- |
| `api/src/transport_matters/response_stream.py` | NEW: tee install + restore + clear + key (~50-80 LOC) |
| `api/src/transport_matters/addon.py` | add thin `responseheaders`; `clear_response_capture` in `error` |
| `api/src/transport_matters/shared_proxy/addon.py` | add thin `responseheaders`; `clear_response_capture` in `error` |
| `api/src/transport_matters/addon_handlers.py` | `restore_streamed_response(flow)` as first statement of `handle_response` |

Honors api/CLAUDE.md: async hooks where required (the `responseheaders` hook may be
sync — pure byte op), no new import cycle (new module imports only mitmproxy+stdlib), all
touched files <700 LOC.

## count_tokens 400 — separate PR (both agree)
`_strip_for_count` is a denylist that leaves rejected top-level fields in the body
(lead cause `metadata`; likely also `context_management`/`output_config`). Flip it to an
ALLOWLIST of count_tokens-accepted keys (`model, messages, system, tools, tool_choice`;
`thinking` only if its required beta header is present and a count test passes). Confirm
the exact rejected field via the existing `TokenCounter.count` debug log first. Ships as
its own focused change with a unit test; not bundled with the streaming PR.

## Test plan (per-area files, Codex's structure)
- `test_streaming_capture.py`: tee install / accumulate / pass-through / terminal `b""`;
  restore reconstructs full bytes + `get_text()` returns full SSE; no-install for JSON and
  for websocket upgrades; restore is a no-op when `raw_content` already present; error ->
  `clear_response_capture` releases buffer.
- Capture-path regression: provisional finalize from streamed bytes yields the same
  `response_raw`/`response_ir`/`res_stats` as the buffered path (golden compare).
- Codex HTTP `/responses` SSE: streamed bytes still drive `derive_codex_http` transport +
  turn artifacts.
- Shared-proxy: `responseheaders` resolves nothing/does not `finish_flow`; `response`
  finishes; `_STREAM_BUFFER_KEY` does not collide with run-id/listen-port keys.
- Incremental-delivery proof: tee invoked with an early ping chunk BEFORE `response` fires;
  persisted Tier-1 record contains the FULL response. Pre-fix baseline forwards zero bytes
  until completion (the regression this fixes).
- count_tokens allowlist unit (separate PR).

## Consensus record
Both `backend-engineer` reviewers (Claude + Codex MoE) conditionally signed off; all
conditions are folded in above. Resolved decisions:
- **Spine confirmed sound** (Claude, vs mitmproxy 12.2.2 source): `Message.raw_content`
  setter is unconditional; `store_streamed_bodies` defaults False so `raw_content is None`
  holds after `state_stream_response_body` and the restore guard fires; tee `event.data`
  chunks are transfer-decoded/content-encoded and `get_content`/`get_text` decode them
  content-encoding-aware, so `extract_response` is unchanged.
- **SSE-OR-Codex gate** replaces the earlier SSE-only literal: Anthropic via
  `"event-stream" in content_type` (adapter's own test), Codex via
  `is_codex_http_responses_flow` regardless of content-type.
- **count_tokens** allowlist verdict confirmed (separate PR): `_STRIP_KEYS` strips only the
  6 sampling keys and leaves `metadata`/`context_management`/`output_config`; flip to an
  allowlist after confirming the rejected field via the existing debug log.
