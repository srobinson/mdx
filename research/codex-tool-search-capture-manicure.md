---
title: Codex Tool Search Capture Behavior in Manicure
type: research
tags: [manicure, codex, tool-search, tool-results, capture]
summary: Codex tool_search capture broke because the continuation request carried tool_search_output, which Manicure parsed as UnknownBlock and then refused to serialize.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-26
updated: 2026-04-26
---

## Executive Summary

Manicure captures normal Codex tool results when they travel back through `response.create.input` as `function_call_output` or `custom_tool_call_output`. The `tool_search` case uses the same continuation boundary, but with a different input item type: `tool_search_output`.

The specific `fmm` example at `/Users/alphab/.manicure/workspaces/dev-helioy-helioy-bus/ee57b03d/20260426T062000Z-c5214a36` captured the first model response through `tool_search_call`. The actual continuation existed at 2026-04-26 13:20:06 local time, but Manicure failed while persisting that second `response.create`: `Codex serializer cannot safely emit message with blocks: unknown`.

## Project Metadata

- Project: `manicure`
- Purpose: provider neutral context control plane for coding agents, with Claude reverse proxy and Codex HTTPS proxy support.
- Backend: Python 3.12 plus, FastAPI, Pydantic v2, mitmproxy, Typer.
- Frontend: React 19, Vite 8, Tailwind v4.
- Build and tests: `uv`, `pytest`, `ruff`, `mypy`, `just`.
- fmm status: repo root has `.fmm.db`, so this worktree is indexed for structural navigation.

## Architecture

Codex capture flows through an explicit HTTPS proxy to `chatgpt.com/backend-api/codex/responses`. Manicure persists request raw bytes, request IR, curated request, transport diagnostics, derived websocket events, turn summaries, and response IR under `~/.manicure/workspaces/{slug}/{hash}/...`.

Relevant backend modules:

- `api/src/manicure/codex/request_parser.py`: parses outbound Codex `response.create` payloads into `InternalRequest`.
- `api/src/manicure/codex/response_parser.py`: parses server websocket output items into `InternalResponse`.
- `api/src/manicure/codex/protocol.py`: identifies Codex event types, tool call items, and tool output items.
- `api/src/manicure/codex/exchange.py`: persists provisional and finalized Codex exchange artifacts.
- `api/src/manicure/codex/derivation_engine.py`: derives turn events from websocket frames.

## Key Patterns

Normal Codex tool results are request input items. `request_parser._parse_input` dispatches `function_call_output`, `custom_tool_call_output`, and now `tool_search_output` into `_parse_function_call_output`, which returns a user message containing `ToolResultBlock` (`api/src/manicure/codex/request_parser.py:126`, `api/src/manicure/codex/request_parser.py:275`).

Codex `tool_search` is a client executed deferred tool. The server emits `response.output_item.done` with item type `tool_search_call`, arguments, call id, and `execution: client`. The local client then sends a continuation request containing `tool_search_output` with the discovered namespace tools.

## Detailed Findings

The user's cited workspace contains the expected first half. `transport.json` for `20260426T062000Z-c5214a36` has `response.output_item.done` with item type `tool_search_call`, query `fmm structural code navigation list files file outline lookup export glossary read symbol validate`, `limit: 12`, call id `call_AdERbiyqeWaztghLERnRVrFl`, and `execution: client`.

The same exchange's `response.ir.json` preserved that item as an `unknown` raw block before this session's fix. The persisted response also includes `provider_extras.output_item_meta` for `tool_search_call`, so raw metadata survived, but typed response content and tool call stats did not treat it as a tool call.

Searches under `/Users/alphab/.manicure/workspaces/dev-helioy-helioy-bus` found zero occurrences of `Yes. `fmm` MCP is available`, `indexed search across files, exports, imports, and named import call sites`, `mcp__fmm__.fmm_list_files`, and `Found 8 tools`. That confirms those strings were not persisted in this workspace's request, response, or transport artifacts.

The continuation was visible in Codex's own session log at `/Users/alphab/.codex/sessions/2026/04/26/rollout-2026-04-26T12-58-49-019dc85e-80ff-71c0-8946-f24a24adf789.jsonl`. Line 147 records `response_item` type `tool_search_output` with `mcp__fmm__`; lines 148 and 149 record the final assistant answer.

The proxy log confirmed the Manicure failure path. At 2026-04-26 13:20:06 local time, `logs/mitmdump.log` reported `Addon error: Codex serializer cannot safely emit message with blocks: unknown` from `request_serializer._serialize_message`. The second `response.create` was parsed with an `UnknownBlock` because `tool_search_output` was not listed as a known input item type.

## Code Change Made

This session fixed the response side and the continuation request side:

- Added `tool_search_call` to `CODEX_TOOL_CALL_ITEM_TYPES` in `api/src/manicure/codex/protocol.py:32`.
- Added `tool_search_output` to `CODEX_TOOL_OUTPUT_ITEM_TYPES` in `api/src/manicure/codex/protocol.py:35`.
- Mapped nameless `tool_search_call` output items to a `ToolUseBlock` named `tool_search` in `api/src/manicure/codex/response_parser.py:224`.
- Parsed `tool_search_output` as a `ToolResultBlock` and preserved its `tools`, `status`, and `execution` metadata in `api/src/manicure/codex/request_parser.py:130` and `api/src/manicure/codex/request_parser.py:286`.
- Stopped duplicating standard `tool_search_output` frames into request level `provider_extras.input_item_raw`; known fields now remain on the typed `ToolResultBlock`, while unknown extra fields still preserve raw for replay safety in `api/src/manicure/codex/request_parser.py:145`.
- Made the UI expansion path visible by rendering `tool_search_output.tools` as JSON text inside `ToolResultBlock.content`. The React row renders `tool_result` from `block.content` (`www/src/components/editor/BlockRow.tsx:138`), so keeping the tools only in `provider_data` produced a blank expanded panel even though the size label counted hidden metadata.
- Serialized `tool_search_output` back to Codex wire shape in `api/src/manicure/codex/request_serializer.py:195`.
- Taught preserved raw reconciliation about `tool_search_output` in `api/src/manicure/codex/preserved_raw.py:67`, `api/src/manicure/codex/preserved_raw.py:80`, and `api/src/manicure/codex/preserved_raw.py:140`.
- Extended `api/src/manicure/codex/test_transport.py:148` coverage so `tool_search_call` parses as `tool_use` with id, name, and arguments.
- Added adapter round trip coverage for `tool_search_output` in `api/src/manicure/adapters/test_codex.py:262`, including visible tool result content and no request level raw duplication.
- Added a websocket lifecycle regression for the exact missing boundary: first turn emits `tool_search_call`, second request carries `tool_search_output`, and final answer persists in `api/src/manicure/codex/test_transport_turns.py:640`.

Verification:

- `uv run --project api ruff check api/src/manicure/codex/protocol.py api/src/manicure/codex/response_parser.py api/src/manicure/codex/request_parser.py api/src/manicure/codex/request_serializer.py api/src/manicure/codex/preserved_raw.py api/src/manicure/adapters/test_codex.py api/src/manicure/codex/test_transport.py api/src/manicure/codex/test_transport_turns.py`
- `uv run --project api pytest api/src/manicure/adapters/test_codex.py api/src/manicure/codex/test_transport.py api/src/manicure/codex/test_transport_turns.py -q`

Result: all ruff checks passed and 32 tests passed.

The same finding was deposited to context matters under `global/project:helioy/repo:manicure` for future recall.

## Dependencies

Critical dependencies involved in this path:

- `mitmproxy`: websocket interception and artifact capture.
- `pydantic`: frozen IR model validation and serialization.
- `FastAPI`: local API and UI serving.
- `pytest`: focused regression coverage.

## Relevance to Helioy

This matters for Helioy because `tool_search` is the discovery path for deferred MCP tools such as fmm, context matters, Linear, and Helioy bus tools. A capture layer that only watches `function_call_output` will correctly capture ordinary tool results but will under explain deferred tool discovery, where the observable result is a changed tool surface.

The important architectural lesson is that deferred tool discovery has two distinct wire items: `tool_search_call` in server output and `tool_search_output` in the next client input. Both must be mapped for complete capture.

A second UI lesson is that typed capture and visible display are separate concerns. The screenshot at `/Users/alphab/Desktop/Screenshot 2569-04-26 at 14.13.47.png` showed a `TOOL_RESULT` row with a nonzero character count but an empty expanded body. That happened because the row displays `ToolResultBlock.content`, while the parser had placed the discovered `tools` array only in `provider_data`. The parser now writes a formatted JSON text block for `tool_search_output.tools`, so the expanded tool result body shows the discovery payload.

## Open Questions

- Should Manicure add typed mappings for other builtin call and output pairs, especially `web_search_call` and any image generation output forms?
- Should Manicure synthesize a human readable discovery result from newly introduced namespace tools, for example `tool_search loaded mcp__fmm__ with 8 tools`?
- Should the UI distinguish normal tool results from deferred tool discovery to avoid implying a missing `function_call_output` where none exists?
