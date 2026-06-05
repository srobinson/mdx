# Adversarial review: PR #266 (realtime-fix-live-tap-decompression)

**Reviewer:** grok (`transport-matters:general:1:2.3`)  
**PR:** https://github.com/littleorgans/transport-matters/pull/266  
**Branch:** `realtime-fix-live-tap-decompression` @ `8305ed9`  
**Tree:** pristine  
**Verdict:** **CLEAN** — 0 BLOCKER / 0 MAJOR / 0 MINOR

Root cause: mitmproxy stream-mode delivers **content-encoded** response chunks to the live tap; reframer saw zero `data:` frames → only `flow_abort` at finish → UI stuck on Thinking. Fix: per-flow streaming decompression inside the tap before `IncrementalSseFrames`.

---

## 1. Regression is real — PASS

**Test:** `test_content_encoded_real_anthropic_response_emits_live_facts`  
**Fixture:** `api/tests/fixtures/anthropic_live_response_reasoning_tool.sse` (real Anthropic SSE: thinking → tool_use → message_stop)  
**Path exercised:** `handle_response_headers(flow, observer)` → `start_http_flow(..., content_encoding=...)` → `install_response_tee(..., on_chunk=)` → `flow.response.stream(chunk)` identity return. Not a decoded shortcut.

| Encoding | WITH fix | WITHOUT decompress (scratch patch of `_observe_http_chunk`) |
|----------|----------|---------------------------------------------------------------|
| identity | GREEN — reasoning, running_tool, message_stop | GREEN |
| gzip     | GREEN | **RED** — only `flow_abort` |
| deflate  | GREEN | **RED** — only `flow_abort` |
| br       | GREEN | **RED** — only `flow_abort` |
| zstd     | GREEN | **RED** — only `flow_abort` |

Without-fix summary: **green=1 red=4** (exactly the always-Thinking shape: content facts absent, terminal-only abort).

Streaming encode uses per-record compress + flush + finish so chunk boundaries land mid-compressed-stream.

---

## 2. Decompression correctness — PASS

`_streaming_decompressor(content_encoding)`:

| Encoding | Implementation |
|----------|----------------|
| identity / absent / empty | `_identity` passthrough |
| gzip, deflate | `zlib.decompressobj(wbits=47).decompress` (gzip+zlib auto) |
| br | `brotli.Decompressor().process` |
| zstd | `zstandard.ZstdDecompressor().decompressobj().decompress` |
| unknown | returns `None` → tap skipped, one WARNING |

- Selected from `Content-Encoding` at `start_http_flow` (wired from `response.headers` in `addon_handlers`; shared by dedicated + shared proxy).
- Stateful decompressors bound once per flow (bound methods keep objects alive).
- Codex HTTP shares the seam; Codex WS `observe_codex_payload` still `decompressor=None`, reframer=False.
- Decompress error: set `decompression_failed`, log once, subsequent chunks no-op; wire forward unchanged; `finish_flow` may still emit `flow_abort`.

`brotli` / `zstandard` already in lock/venv (not new deps in this PR).

---

## 3. Frozen plane — PASS

- Decompress is tap-local only; `capture_chunk` still returns the **same** encoded `chunk`.
- Tests assert `stream(chunk) == chunk` and `restore_streamed_response` → `raw_content == b"".join(chunks)`.
- Decompress exceptions never propagate into the response path.
- `test_live_tap_preserves_complete_tier1_manifest_and_bytes` still green.
- Unknown encoding: no tap, body still captured; empty live rows.

---

## 4. Scope / sizing / DRY — PASS

- **Files:** `live_status_observer.py` (+70), `addon_handlers.py` (+content_encoding), new encoding tests + fixture. No consumer/admission/coalescing changes.
- **LOC:** observer 427 (<700); no deferred-stop/latest-wins edits.
- Reuses existing classifier + reframer; no second emit path.

---

## Verification

```
pytest test_live_status_content_encoding.py test_live_status_observer.py test_response_stream.py
  → 38 passed
pytest test_live_tap_preserves_complete_tier1_manifest_and_bytes → pass
scratch mutation without decompress → identity green, gzip/deflate/br/zstd red (4)
git status clean @ 8305ed9
```
