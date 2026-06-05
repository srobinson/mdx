---
title: Transport Matters Q2 provider API forward compatibility verification
type: research
tags: [transport-matters, architecture, provider-api, mitmproxy, pydantic, codex, anthropic]
summary: Q2 is mostly confirmed, with a correction that Anthropic nested field loss is broader than the draft stated.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Executive Summary

The Q2 split verdict is confirmed: responses are not modified on the live path, while requests are normally serialized back from the internal IR even when no user edit occurred. One correction matters: the Anthropic loss surface is broader than the draft names. Extra fields are also lost on message objects, text blocks, and Anthropic tool result blocks, even though `ToolResultBlock` has an IR `provider_data` field.

Recommended shape: add a no mutation fast path when `curated_ir == ir`, then add structural raw overlay for Anthropic edited paths. Explicit overflow fields are still useful for surfaced fields, but `extra="allow"` alone would not fix this because the adapters build IR by cherry picking keys.

## Project Metadata

- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
- fmm status: `fmm validate` passed for 352 indexed files.
- Backend: Python package under `api/`, Python `>=3.12`, FastAPI, Pydantic, HTTPX, mitmproxy, Typer. See `api/pyproject.toml`.
- Frontend: `www/` React application, not needed for this Q2 verification.
- Relevant topology from fmm: `api/` 205 files and 42,287 LOC, `www/` 133 files and 20,181 LOC, `desktop/` 14 files and 1,588 LOC.

## Architecture Relevant to Q2

- `addon_handlers.py` is the live mitmproxy request and response coordinator. It parses requests, runs the override pipeline, captures flow state, optionally pauses at a breakpoint, and writes the outbound request body.
- Provider adapters translate provider wire payloads to `InternalRequest` and back. Anthropic is in `api/src/transport_matters/adapters/anthropic.py`; Codex request parsing and serialization are split across `api/src/transport_matters/codex/request_parser.py`, `request_serializer.py`, and `preserved_raw.py`.
- The IR is in `api/src/transport_matters/ir.py`. Models are frozen Pydantic models with explicit fields and a few explicit catch all fields such as `provider_extras` and `provider_data`.

## Detailed Findings

### 1. Split verdict confirmed: responses pass through, requests serialize on normal path

Responses are only recorded on the live response path. `handle_response` dispatches to persistence helpers and never assigns to `flow.response` or response body fields (`api/src/transport_matters/addon_handlers.py:286-303`). `_persist_http_exchange` reads the response text and persists derived artifacts (`api/src/transport_matters/exchange_recorder.py:237-242`, `303-314`). That recorded copy may be parsed or normalized, but the live client response is not rewritten by this handler.

HTTP requests are serialized from IR on the normal non paused path. `handle_http_request` applies the pipeline, captures state, and then calls `flow.request.set_text(adapter.outbound_request(curated_ir).decode())` (`api/src/transport_matters/addon_handlers.py:94-110`, `121-135`). This covers Anthropic `/v1/messages` and Codex HTTPS fallback requests because the handler admits either `/v1/messages` or `codex_http` (`api/src/transport_matters/addon_handlers.py:70-72`), while `is_codex_http_responses_flow` identifies Codex fallback POSTs on the Codex responses path (`api/src/transport_matters/codex/transport.py:116-130`).

Codex WebSocket initial request frames are also serialized from IR on the normal path. `handle_codex_websocket_message` captures the initial frame, builds IR, runs the same pipeline, and assigns `message.content = adapter.outbound_request(curated_ir)` (`api/src/transport_matters/addon_handlers.py:199-220`, `233-242`).

Breakpoint release follows the same pattern unless an explicit raw `release_payload` was supplied. `_release_payload` returns `pf.release_payload` if present, else `adapter.outbound_request(final_ir)` (`api/src/transport_matters/pause_session.py:73-80`). The HTTP and WebSocket breakpoint release sites then write that payload to the request body or message content (`api/src/transport_matters/pause_session.py:243-250`, `317-325`).

### 2. Top level extras survive, but nested Anthropic loss is broader than stated

Top level provider request keys survive for both providers:

- Anthropic captures keys outside `_MAPPED_REQUEST_KEYS` into `provider_extras` (`api/src/transport_matters/adapters/anthropic.py:71-73`) and restores them with `data.update(ir.provider_extras)` (`api/src/transport_matters/adapters/anthropic.py:128-131`).
- Codex does the same for top level keys (`api/src/transport_matters/codex/request_parser.py:60-64`) and starts serialization from those extras (`api/src/transport_matters/codex/request_serializer.py:33-37`).

The draft is correct that `Message`, `ToolUseBlock`, `SamplingParams`, and `ImageBlock` lack overflow fields in the IR (`api/src/transport_matters/ir.py:26-32`, `53-57`, `100-114`). It is also correct that system parts, tools, and thinking blocks have explicit provider data and Anthropic restores those fields (`api/src/transport_matters/ir.py:80-97`, `45-50`; `api/src/transport_matters/adapters/anthropic.py:267-288`, `297-319`, `368-376`, `417-425`).

Correction: the Anthropic nested loss surface also includes `TextBlock`, message object extras, and tool result extras. Anthropic parses a message into `Message(role=item["role"], content=blocks)` with no message level catch all (`api/src/transport_matters/adapters/anthropic.py:324-338`), then serializes only `role` and `content` (`api/src/transport_matters/adapters/anthropic.py:381-386`). Text blocks serialize only `type` and `text` (`api/src/transport_matters/adapters/anthropic.py:345-346`, `393-394`). Anthropic tool results parse only `tool_use_id`, `content`, and `is_error` (`api/src/transport_matters/adapters/anthropic.py:349-367`), then serialize only those fields (`api/src/transport_matters/adapters/anthropic.py:402-416`). This drops unknown tool result siblings despite `ToolResultBlock.provider_data` existing in the IR (`api/src/transport_matters/ir.py:35-42`).

The adapter cherry picking point is confirmed. The adapters construct models by selecting specific keys, not by validating raw provider dicts wholesale. For example, Anthropic `_parse_content_block` chooses known fields per block type (`api/src/transport_matters/adapters/anthropic.py:340-379`), and `_parse_sampling` selects only `max_tokens`, `temperature`, `top_p`, `top_k`, and `stop_sequences` (`api/src/transport_matters/adapters/anthropic.py:469-477`). Codex parsing likewise selects known keys in `_parse_sampling` (`api/src/transport_matters/codex/request_parser.py:391-414`) and the content parsers (`api/src/transport_matters/codex/request_parser.py:206-258`, `261-318`). Therefore the default Pydantic extra policy is mostly moot except where code explicitly carries extras through `provider_extras`, `provider_data`, `UnknownBlock.raw`, or Codex preserved raw overlays.

Codex is better protected on edited paths because it already has structural raw overlay. It marks message items for raw preservation when message level or content extras are seen (`api/src/transport_matters/codex/request_parser.py:117-124`, `154-179`, `220-229`, `247-258`). Serialization reconciles those raw items back onto emitted payloads (`api/src/transport_matters/codex/request_serializer.py:81-113`; `api/src/transport_matters/codex/preserved_raw.py:33-61`, `197-251`).

### 3. Raw body passthrough is cheap if it means no body assignment when IR is unchanged

The equality guard is implementable cheaply. The code already relies on Pydantic model equality to detect structural sameness: `_persistable_curated_ir` returns `None` when `curated_ir == original_ir` (`api/src/transport_matters/exchange_recorder.py:72-82`), and breakpoint release decides manual mutation with `pf.mutated_ir != pf.curated_ir` (`api/src/transport_matters/pause_session.py:48-70`). A local smoke script also confirmed that frozen IR model copies and model dump plus validate round trips compare equal.

The safe passthrough implementation is to avoid body mutation when `curated_ir == ir`:

- HTTP: skip `flow.request.set_text(...)` at `api/src/transport_matters/addon_handlers.py:135`.
- Codex WebSocket: skip `message.content = ...` at `api/src/transport_matters/addon_handlers.py:242`.

This avoids content length and content encoding traps because mitmproxy keeps the original body and frame untouched. Reinjecting captured bytes is less safe because `parse_request_ir` currently captures `raw` from `flow.request.get_text().encode()`, not from a byte exact body field (`api/src/transport_matters/request_pipeline.py:22-33`). If a future client sends compressed or charset sensitive JSON, that `raw` value is not a reliable byte faithful passthrough source.

Storage and token accounting need small follow through changes if raw passthrough lands. `_curated_request_raw` currently serializes `curated_ir` and compares bytes with `original_raw` (`api/src/transport_matters/exchange_recorder.py:62-69`). Because serializers canonicalize JSON with sorted keys (`api/src/transport_matters/adapters/anthropic.py:131`; `api/src/transport_matters/codex/request_serializer.py:72`), storage can record a curated raw difference even when the IR is unchanged. The persistence layer should prefer the same structural equality test used by `_persistable_curated_ir` before serializing a curated raw artifact.

Token counting also serializes IR instead of using the original raw request. `stamp_pipeline_tokens` passes `adapter.outbound_request(original_ir)` and `adapter.outbound_request(curated_ir)` to `count_before_after` (`api/src/transport_matters/exchange_stats.py:142-156`). The counter strips sampling fields before posting to `/v1/messages/count_tokens` (`api/src/transport_matters/counting.py:119-131`) and forwards the filtered auth plus Anthropic version and beta headers (`api/src/transport_matters/counting.py:31-38`, `105-116`). Raw passthrough will protect the live request, but token counts may still be computed from a normalized or lossy IR payload unless this path switches to the original raw payload for the before side and omits the after side when IR is equal.

### 4. Raw overlay is better than overflow for wire fidelity, but both are needed

Raw body passthrough is the highest leverage fix because it makes unmodified traffic byte faithful and provider compatible even when the IR is lossy. It should be the keystone.

For edited requests, a blanket item raw overlay is stronger than adding `provider_data` to every modeled struct. Codex proves the pattern: preserve the original raw input item, then overlay the edited known fields back into it. That retains unknown siblings around the edited field. Anthropic should copy this at the message and content block level.

Explicit overflow fields are still useful where fields are surfaced, diffed, transformed, or shared across providers. But Pydantic `extra="allow"` on IR models would not solve the current adapter behavior by itself, because the adapters are not validating raw dicts into those models. They are constructing models from selected values.

## Verification

Commands run:

```bash
fmm validate
```

Result: all 352 files indexed and up to date.

```bash
uv run --project api python - <<'PY'
# Smoke checked Pydantic equality, Anthropic nested loss, Codex overlay preservation.
PY
```

Result highlights: equality true for IR model copy and dump plus validate; Anthropic top level, system, tool, and thinking extras preserved; Anthropic message, text, image, tool result, and tool use extras dropped; Codex top level and preserved raw message content extras kept.

```bash
PYTHONPATH=src uv run pytest -q \
  src/transport_matters/adapters/test_anthropic.py \
  src/transport_matters/adapters/test_codex.py \
  src/transport_matters/test_ir.py \
  src/transport_matters/test_request_pipeline.py \
  src/transport_matters/test_counting.py
```

Result: 68 passed in 0.54s. A prior root level pytest attempt without `PYTHONPATH=src` failed to import `transport_matters`; rerunning from `api/` with `PYTHONPATH=src` passed.

```bash
git status --short
```

Result: clean worktree before writing this external research artifact.

## Relevance to Helioy

This confirms a general Helioy pattern: preserve raw external protocol payloads until a user or rule actually edits them. Use canonical IR for inspection and controlled edits, but do not make lossless forwarding depend on the IR being fully modeled.

## Open Questions

- Should the raw passthrough guard live in `addon_handlers.py`, or should adapters expose an explicit `outbound_request_or_original` style helper so storage, counting, and breakpoint release share one decision point?
- For Anthropic edited paths, should raw overlay preserve whole message objects, individual content blocks, or both?
- Should token counts optimize for exact live wire bytes or for normalized semantic payloads accepted by `count_tokens`?
