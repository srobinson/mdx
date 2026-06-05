---
title: Streaming pass-through for the mitmproxy capture addon (fix 60s SSE stall)
type: spec
status: draft
source: backend-engineer
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

# Spec: stream the proxied response through to the client while still capturing the full wire bytes

## 0. Scope and intent

Design only. No code in this document. Repo: `transport-matters` (`api/`).

The capture proxy fully buffers every upstream response before delivering a single
byte to the agent. For `stream:true` SSE responses this breaks streaming and, on
slow model-thinking turns, trips the client's ~60s stream-idle timeout. This spec
specifies a streaming-tee design that forwards the response to the client in real
time while still capturing the **complete** response bytes for the Tier-1 wire
record and extracting token usage, in **both** addon entry points, without breaking
the armed-breakpoint path, Codex websocket/HTTP transport, error/non-streaming
responses, or the shared-proxy demux mapping.

It also diagnoses the secondary `count_tokens` 400-on-every-turn bug and gives a
verdict on where to fix it.

---

## 1. Root-cause confirmation

Verified against the code and the installed mitmproxy.

### 1.1 The proxy never streams responses

- `TransportMattersAddon` (`addon.py`) registers hooks `request`, `response`, `error`,
  `websocket_*`, `done`, `load`. It registers **no** `responseheaders` hook and never
  assigns `flow.response.stream`.
- `SharedProxyAddon` (`shared_proxy/addon.py`) is the same: `request`, `response`,
  `error`, `websocket_*`; no `responseheaders`, no `flow.response.stream`.
- mitmproxy's `Message.stream` defaults to `False`. From the installed
  `mitmproxy/http.py` (`Message.stream`, mitmproxy 12.2):
  > "If `False`, mitmproxy will buffer the entire body before forwarding it to the
  > destination. … This attribute must be set in the `requestheaders` or
  > `responseheaders` hook. Setting it in `request` or `response` is already too
  > late, mitmproxy has buffered the message body already."

Therefore every upstream response is fully buffered before mitmproxy delivers it to
the agent and before the addon's `response` hook fires.

### 1.2 Why this manifests as a 60s stall on slow turns

For a `stream:true` SSE turn, Anthropic holds the connection open and emits SSE
keepalive pings while the model thinks, then streams content. Because mitmproxy
buffers, **none** of those bytes (pings included) reach Claude Code until the whole
response is buffered. During a long synthesis turn the client sees zero bytes, its
~60s stream-idle timeout fires, the connection is treated as `200 OK (content
missing)`, it retries, and the identical 60s stall repeats. This matches the
reported evidence: server disconnect at exactly 60.000s after the synthesis turn,
fast turns (<60s) returning real content, direct (no-proxy) working, and a bare
mitmdump or a body-reading addon streaming fine. The differentiator is response
**buffering**, not body size.

### 1.3 Capture still works today — only delivery timing is broken

The capture path is correct precisely *because* of the buffering: by the time
`response` fires, the full body is present, so `extract_response`
(`exchange_recorder_artifacts.py`) reads `flow.response.get_text()` and gets the
complete SSE. The fix must preserve that completeness while removing the buffering
delay. Concretely: once we stream, `flow.response.get_text()` is no longer usable in
the `response` hook (the body was streamed, not retained), so the captured bytes must
be reconstructed from the tee.

### 1.4 The response-capture / persist path (what must keep working)

- `addon.response` → `handle_response` (`addon_handlers.py`). Branches:
  Codex-HTTP-responses flow → `persist_http_exchange`; Codex websocket handshake
  failure (`flow.websocket is None`) → `persist_codex_handshake_failure`; otherwise
  → `persist_http_exchange`.
- `persist_http_exchange` (`exchange_recorder.py`): for Claude's primary path the
  request hook already wrote a **provisional** exchange, so this delegates to
  `_finalize_http_provisional_exchange`, which calls `extract_response` to get
  `raw_res`/`res_ir`/`res_stats`, derives Codex HTTP transport via
  `derive_codex_http`, builds `ExchangeArtifacts(response_raw=…, response_ir=…)`,
  persists Tier-1, then fires the post-persist sinks `emit_to_index` and
  `emit_exchange`. (Note the in-code comment on `_finalize_http_provisional_exchange`:
  "Streaming, Claude's primary path, finalizes here … The response is only available
  now.")
- `extract_response` → `flow.response.get_text()` → `flow.response.content` decoding.
  This is the single chokepoint that depends on the full body being present in
  `flow.response`.
- Response token usage is taken from the parsed response body
  (`parse_response_ir` → `res_stats`), i.e. the `message_start` / `message_delta`
  usage in the SSE — **not** from `count_tokens`. So full-byte capture is sufficient
  for usage; the `count_tokens` enrichment (§5) is a separate request-side concern.

---

## 2. Design: stream the response through a shared capture tee

### 2.1 mitmproxy 12.2 streaming API (the exact mechanism)

`Message.stream: Callable[[bytes], Iterable[bytes] | bytes] | bool`.

- Set it in the **`responseheaders`** hook (after headers, before body). Setting it in
  `response` is too late.
- A callable acts as a transformation **tee**: mitmproxy calls it for each body chunk;
  the return value is what is forwarded to the client. Returning the chunk unchanged
  passes the body through byte-for-byte. mitmproxy signals end-of-body with a final
  empty `b""` chunk. Packet boundaries are not guaranteed, so the tee must accumulate,
  not assume framing.
- After a streamed response, `flow.response.raw_content` is `None` in the `response`
  hook (the body was streamed, not stored); `content` / `get_text()` would raise or
  return nothing. `raw_content` is the raw (transfer-decoded, still
  content-encoded) body — exactly what the tee chunks are.

### 2.2 The shared helper (one module, called by both addons)

New module `api/src/transport_matters/response_stream.py` (small, cohesive, the single
home for streaming capture — no second copy). It exposes two public functions:

**`install_response_tee(flow) -> None`** — called from each addon's `responseheaders`
hook.
- Guard out flows that must not be body-streamed:
  - no `flow.response` → return (defensive);
  - websocket upgrade: `flow.response.status_code == 101` or the request carried
    `Upgrade: websocket` → return (the body is websocket frames, delivered via the
    `websocket_*` hooks, not an HTTP body). This is a provider-agnostic HTTP-level
    guard; using `codex.transport.is_codex_websocket_flow` would also work but adds a
    dependency — prefer the status/header check.
  - Locally-crafted responses (breakpoint-drop 400, shared-proxy 502) never reach
    `responseheaders` because they are set in the `request` hook and short-circuit the
    upstream request, so no extra guard is needed for them.
- Allocate a per-flow `bytearray` and stash it on `flow.metadata[_STREAM_BUFFER_KEY]`
  (flow-scoped, auto-released with the flow — no global dict, no manual cleanup, no
  fd/lifecycle leak).
- Assign a tee closure to `flow.response.stream` that appends each non-empty chunk to
  that buffer and returns the chunk unchanged (pass-through). The closure captures the
  same `bytearray` object that lives in `flow.metadata`, so the `response` hook can
  retrieve the accumulated bytes.

**`restore_streamed_response(flow) -> None`** — called once at the very top of
`handle_response` (`addon_handlers.py`), i.e. a **single** shared call site that
covers both addons.
- Pop `flow.metadata[_STREAM_BUFFER_KEY]`. If present and `flow.response is not None`
  and `flow.response.raw_content is None` (streamed), set
  `flow.response.raw_content = bytes(buffer)`.
- Re-injecting the captured raw bytes makes `flow.response.content` /
  `get_text()` decode normally (content-encoding aware), so **`extract_response`,
  `derive_codex_http`, `parse_response_ir`, and every downstream consumer stay
  unchanged**. This is the key to a minimal, DRY change: the streaming concern is
  fully contained in `response_stream.py`; the rest of the pipeline sees the same
  `flow.response` it always did.

### 2.3 Where the full-byte accumulation happens

In the tee closure, under the streaming path, into the `flow.metadata`-held
`bytearray`. The `response` hook reconstitutes `flow.response.raw_content` from it
before any capture logic runs. This satisfies the product invariant that the **full
wire response bytes** are captured, now decoupled from delivery timing.

### 2.4 What moves where

- The current `response`-hook capture logic does **not** move. It stays in
  `handle_response` / `persist_http_exchange` / `_finalize_http_provisional_exchange`.
  The only addition is the one `restore_streamed_response(flow)` call at the top of
  `handle_response`, which re-hydrates `flow.response` so the existing logic is a
  no-op-different.
- The new work is the `responseheaders` hook (install the tee) plus the helper module.

### 2.5 DRY and the addon entry points

Both addon classes gain a thin `responseheaders(self, flow)` method that calls
`install_response_tee(flow)` — mirroring the existing pattern where `request` /
`response` / `error` are thin delegations to `addon_handlers`. All real logic lives in
the one `response_stream.py` module; there is exactly one tee implementation and one
restore implementation. No second copy in the shared proxy.

```
# addon.py  (TransportMattersAddon)
def responseheaders(self, flow): install_response_tee(flow)

# shared_proxy/addon.py  (SharedProxyAddon)
def responseheaders(self, flow): install_response_tee(flow)
```

`responseheaders` does **not** need binding/demux resolution — the tee is
binding-agnostic byte buffering. Binding resolution and `finish_flow` stay in the
`response` / `error` hooks exactly as today.

### 2.6 Stream everything (uniform), not only SSE

Install the tee on every real upstream HTTP response (after the websocket/local
guards). The tee is a transparent buffer, so non-streaming JSON responses are
captured identically with negligible overhead and forwarded incrementally. This avoids
content-type sniffing and a second code path. The only excluded flows are websocket
upgrades and locally-crafted responses (handled by the guards / by `responseheaders`
not firing).

---

## 3. Interaction analysis (the four hazards in the brief)

### 3.1 Armed breakpoint (request-side; no conflict)

The breakpoint pauses the next **outbound request** and the operator edits the
**request** body: `handle_breakpoint` (`pause_session.py`) runs inside the `request`
hook and mutates `flow.request` (`flow.request.set_text(...)`), or, on drop, sets a
synthetic `flow.response = Response.make(400, …)` in the request hook. (Note: the brief
says "operator edits the response"; the current breakpoint is request-side only —
confirmed in `handle_breakpoint`. Flagging the wording so the orchestrator can
reconcile, but it does not change the design.)

Consequences for streaming:
- Pause/edit happens entirely before any response exists. When the (possibly edited)
  request is finally released upstream, the response arrives later and the tee captures
  it normally. Streaming the response does not interact with request mutation.
- Drop path: the synthetic 400 is set in the `request` hook → mitmproxy skips the
  upstream request → `responseheaders` does **not** fire → no tee installed → the
  crafted body is delivered directly. Safe.
- Forward-compat note: if a future feature lets the operator edit the **response**, that
  flow must opt out of streaming (buffer fully) so the edit can be applied before
  forwarding. The helper should keep a single "force-buffer this flow" escape hatch in
  mind, but it is out of scope here.

Hard rule: only `flow.response.stream` is set. **Never** set `flow.request.stream` —
the request must stay buffered so the pipeline can parse and mutate it.

### 3.2 Codex websocket and Codex HTTP transport

- Codex **websocket** flows deliver their payload through `websocket_message` /
  `websocket_end`, not an HTTP response body. The `responseheaders` guard
  (status 101 / `Upgrade: websocket`) skips them, so the tee never touches the
  handshake. `handle_codex_websocket_*` are unchanged.
- Codex **HTTP** `/responses` SSE flows (`is_codex_http_responses_flow`) go through the
  ordinary HTTP `response` hook → the tee applies, the body is captured and streamed,
  and `restore_streamed_response` re-hydrates `flow.response` before
  `persist_http_exchange` runs the codex-http branch (`extract_response` +
  `derive_codex_http`). Unchanged behavior, now incremental delivery.
- Codex websocket handshake failure (`flow.websocket is None` in `response`): no
  buffer was installed (guarded), `restore_streamed_response` is a no-op,
  `persist_codex_handshake_failure` runs unchanged.

### 3.3 Non-streaming and error responses

- Non-streaming JSON: tee accumulates the whole body, restore re-hydrates, capture
  unchanged.
- Real upstream errors (429/500/etc.): they arrive from the server, so
  `responseheaders` fires, the tee captures and forwards them, and
  `tag_http_error_status` (inside `extract_response`) tags them as today. Bodies are
  small; streaming is trivial.
- Locally-crafted responses (`SharedProxyAddon._fail_http` 502, breakpoint-drop 400):
  set in the `request`/resolve path, never trigger `responseheaders`. No tee. Safe.

### 3.4 Shared-proxy demux (flow → binding mapping)

Demux resolution (`_resolve_new_flow` / `_resolve_existing_flow`, `_flow_listen_port`,
`_stamp_flow`, `finish_flow`) lives in the `request` / `response` / `error` hooks and
is keyed off `flow.metadata` run-id/listen-port and `flow.id`. `responseheaders` does
not resolve a binding and does not call `finish_flow`; it only stashes a buffer under a
**new, dedicated** metadata key (`_STREAM_BUFFER_KEY`) that does not collide with
`FLOW_RUN_ID_METADATA_KEY` / `FLOW_LISTEN_PORT_METADATA_KEY`. The existing `response`
hook still resolves the binding and calls `finish_flow` in its `finally`. No change to
the demux flow.

### 3.5 Request-mutation interaction (explicit)

`handle_http_request` already does `flow.request.set_text(outbound.decode())` in the
`request` hook, which requires the request body to be buffered. We leave the request
fully buffered (no `flow.request.stream`). Setting `flow.response.stream` in
`responseheaders` is independent of request handling and of the request mutation that
already happened earlier in the flow lifecycle. No conflict.

---

## 4. Files touched (streaming fix)

| File | Change |
| --- | --- |
| `api/src/transport_matters/response_stream.py` | **New.** `install_response_tee`, `restore_streamed_response`, `_STREAM_BUFFER_KEY`. ~40–70 LOC. The single home for streaming capture. |
| `api/src/transport_matters/addon.py` | Add thin `responseheaders` → `install_response_tee`. |
| `api/src/transport_matters/shared_proxy/addon.py` | Add thin `responseheaders` → `install_response_tee`. |
| `api/src/transport_matters/addon_handlers.py` | `handle_response`: call `restore_streamed_response(flow)` as the first statement (single shared site for both addons). |

Import DAG: `response_stream.py` imports only `mitmproxy` (and stdlib). It sits at the
addon/handler layer; `addon_handlers` and both addons import it. No new cycle, honors
`ir → adapters → rules → pipeline → storage → breakpoint → server`. All touched files
stay well under 700 LOC (`addon.py` 107, `shared_proxy/addon.py` 344,
`addon_handlers.py` 322; the new module is small). Async-I/O convention is respected:
the tee and restore are pure byte operations (sync); the `responseheaders` hook may be
sync. No new blocking I/O on the hook path.

---

## 5. Secondary bug: `count_tokens` enrichment returns 400 on every turn

### 5.1 Mechanism in code

The addon's request-side token enrichment posts a stripped copy of the request to
`/v1/messages/count_tokens` (`TokenCounter.count`, `counting.py`). On any non-200 it
logs at debug (`count_tokens %d: %s` with `response.text[:200]`) and returns `None`, so
the enrichment silently degrades — every turn loses the before/after input-token count
(`stamp_pipeline_tokens` / `stamped_pipeline_stats`). Response **usage** is unaffected
(it comes from the parsed response body, §1.3), so this is an enrichment-accuracy bug,
not a capture or streaming bug.

### 5.2 Diagnosis (lead hypothesis: unstripped fields)

`_strip_for_count` (`counting.py`) is a **denylist**: it removes only
`max_tokens, stream, temperature, top_p, top_k, stop_sequences`. The `count_tokens`
endpoint accepts the Messages body shape minus sampling fields
(`model, messages, system, tools, tool_choice, thinking`, plus betas like
`mcp_servers`) and **strict-validates** the top-level object. Claude Code's
`/v1/messages` body carries extra top-level fields that `count_tokens` does not accept
— most likely `metadata` (Claude Code always sends it), and potentially others
(`service_tier`, etc.). A denylist that strips six sampling keys leaves `metadata` in
place, and `count_tokens` rejects the unexpected field with
`400 invalid_request_error` ("Extra inputs are not permitted").

The "missing beta header" alternative is unlikely to be the cause: `anthropic-beta`
is in `_AUTH_HEADER_KEYS` and is forwarded on the count request (so the OAuth
`oauth-2025-04-20` beta that Claude Code uses is preserved), and the request body's
real system prompt is forwarded intact. OAuth/beta mismatches surface as 401/403, not a
consistent 400. The 400-every-turn shape points at body validation, i.e. unstripped
fields.

### 5.3 Robust fix (recommended)

Invert `_strip_for_count` from a denylist to an **allowlist** of `count_tokens`-accepted
top-level keys (`model, messages, system, tools, tool_choice, thinking`, plus any
beta-gated keys the endpoint accepts such as `mcp_servers`), dropping everything else.
This eliminates `metadata` and is resilient to future Claude Code additions, instead of
chasing one new rejected field at a time. The cache-key benefit of stripping volatile
sampling fields is preserved (they are not on the allowlist).

### 5.4 Confirmation step (do this before finalizing the fix)

The exact rejected field is already captured by the existing debug log line in
`TokenCounter.count` (`response.text[:200]`). Run one real Claude Code turn through the
proxy with that logger at DEBUG and read the 400 body; it will name the offending
field (expected: `metadata`). This turns the lead hypothesis into a verified one and
guards against a second unexpected field.

### 5.5 Verdict: fix separately

Fix the `count_tokens` allowlist in its **own** small change, not bundled with the
streaming fix:
- It is orthogonal (request-side enrichment vs response-side delivery), touches a
  different file (`counting.py`), and has a different risk profile.
- Keeping the streaming PR focused on the SSE-stall fix keeps its review tight
  (contract/persistence-adjacent change deserves an undiluted diff).
- The allowlist change is self-contained and ships with a focused unit test
  (§6.6). It can land before or after the streaming fix.

---

## 6. Test plan

### 6.1 Tee unit (capture completeness)
Build a fake `HTTPFlow` with a `stream:true`-style SSE response. Call
`install_response_tee`, drive the tee with several chunks plus the terminal `b""`,
assert each call returns its input unchanged (pass-through), then call
`restore_streamed_response` and assert `flow.response.raw_content` equals the
concatenation of all chunks and `flow.response.get_text()` returns the full SSE.

### 6.2 Tee unit (guards)
- 101 / `Upgrade: websocket` response → `install_response_tee` installs no tee and sets
  no buffer.
- `flow.response is None` → no error, no buffer.
- A response with content already present and `raw_content` not `None` (non-streamed) →
  `restore_streamed_response` is a no-op and does not clobber the body.

### 6.3 Capture-path regression
With the tee + restore in place, assert `extract_response` and
`_finalize_http_provisional_exchange` produce the same `response_raw` / `response_ir` /
`res_stats` for a representative captured SSE as the buffered path does today (golden
compare against an existing fixture).

### 6.4 Incremental-delivery / 60s-stall proof (integration)
Drive a streaming upstream that emits an SSE keepalive ping at T+0 and the first content
event only after a long delay (> the client idle timeout, simulated/compressed in the
test harness). Assert the tee is invoked with the ping chunk **before** the `response`
hook fires (i.e. bytes are forwarded incrementally), and that the persisted Tier-1 wire
record contains the **full** response. The pre-fix baseline (no `responseheaders` hook)
must show zero bytes forwarded until the body completes — the regression this fixes.

### 6.5 Interaction regressions
- Breakpoint armed → pause/edit request → release → response streamed and captured;
  breakpoint drop → synthetic 400 delivered, no tee, provisional deleted.
- Codex websocket flow → no tee installed; `handle_codex_websocket_*` unchanged.
- Codex HTTP `/responses` SSE → streamed, captured, `derive_codex_http` unchanged.
- Shared-proxy: demux mapping and `finish_flow` still run in `response`/`error`; the
  `_STREAM_BUFFER_KEY` metadata does not collide with run-id/listen-port keys.
- Real 429/500 upstream error → streamed, tagged by `tag_http_error_status`.

### 6.6 count_tokens allowlist unit
Feed a Claude-Code-shaped payload (including `metadata`) through `_strip_for_count`;
assert `metadata` (and any non-allowlisted key) is removed and the allowlisted keys
survive. Add a `TokenCounter.count` test asserting a 200 with the allowlisted body and
that a previously-rejecting payload now posts a clean body.

---

## 7. Summary of the change

1. Add a `responseheaders` hook to both addons that installs a transparent
   streaming tee via one shared helper (`response_stream.py`); the tee forwards each
   chunk to the client immediately and accumulates the full raw body in flow-scoped
   metadata.
2. At the top of the shared `handle_response`, re-hydrate `flow.response.raw_content`
   from the accumulated buffer so all existing capture/persist logic
   (`extract_response`, `_finalize_http_provisional_exchange`, `derive_codex_http`,
   token-usage parsing) works unchanged.
3. Guards exclude websocket upgrades and locally-crafted responses; the request stays
   buffered; demux, breakpoint, Codex, and error paths are untouched.
4. Separately, fix `count_tokens` by switching `_strip_for_count` to an allowlist
   (lead cause: unstripped `metadata`), after confirming the rejected field via the
   existing debug log.

This restores real-time SSE delivery (killing the 60s idle-timeout stall) while
preserving the product invariant that the complete wire response bytes are captured,
with one streaming-capture helper shared by both addon entry points and zero
duplication.
