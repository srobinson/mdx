---
title: Linear stale implementation references in manicure ALP-2007 through ALP-2013
type: research
tags: [linear, manicure, backend, references]
summary: Reviewed ALP-2007 through ALP-2013 against the current manicure backend and updated stale IndexEntry pipeline field references.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed Linear issues ALP-2007 through ALP-2013 for stale backend file, symbol, hook, and helper references after refactoring. All referenced backend files and existing helper symbols still exist, except two stale references to a storage field named `pipeline_stats`; the current `IndexEntry` field is `pipeline`.

## Project Metadata

- Project: manicure
- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/manicure`
- Structure: `api/` Python backend and `www/` frontend
- fmm status: indexed, 288 files and 54,626 LOC

## Architecture References Verified

- `api/src/manicure/flow_state.py`: `RequestFlowState`, `capture_request_flow_state`, `get_request_flow_state`, `update_request_flow_state`
- `api/src/manicure/addon_handlers.py`: `handle_http_request`, `handle_response`, `_should_skip_breakpoint`
- `api/src/manicure/exchange_recorder.py`: `_persist_http_exchange`, `_persist_track_assignment`, `_emit_exchange_deleted`, `emit_exchange`
- `api/src/manicure/pause_session.py`: `handle_breakpoint`
- `api/src/manicure/addon.py`: `ManicureAddon` currently has no `error` hook
- `api/src/manicure/codex/exchange.py`: `_persist_codex_provisional_exchange`, `_finalize_codex_provisional_exchange`, `_delete_codex_provisional_exchange`
- `api/src/manicure/codex/transport.py`: `is_codex_websocket_flow`
- `api/src/manicure/storage/base.py`: `StorageBackend.read_index_entry`, `IndexEntry.pipeline`

## Detailed Findings

### Linear updates applied

- ALP-2008: changed acceptance reference from storage record field `pipeline_stats` to `pipeline`.
- ALP-2009: changed `existing_entry.model_copy(update={"res": res_stats, "pipeline_stats": stamped_pipeline_stats})` to use `"pipeline"`; changed acceptance from `pipeline_stats` to `IndexEntry.pipeline`.

### Evidence

- `IndexEntry` defines `pipeline: PipelineStats | None = None` in `api/src/manicure/storage/base.py`.
- `_persist_http_exchange` creates `IndexEntry(..., pipeline=pipeline_stats, ...)` in `api/src/manicure/exchange_recorder.py`.
- `_finalize_codex_provisional_exchange` updates existing entries with `"pipeline": pipeline_stats` in `api/src/manicure/codex/exchange.py`.
- `emit_exchange` broadcasts the SSE payload field as `pipeline`, while accepting a local parameter named `pipeline_stats` in `api/src/manicure/exchange_recorder.py`.

## Open Questions

None for the requested stale reference pass. Planned symbols such as `_persist_http_provisional_exchange`, `_finalize_http_provisional_exchange`, `_delete_http_provisional_exchange`, `provisional_exchange_id`, and `dropped` are absent because these issues are still implementation tasks, not because their references are stale.
