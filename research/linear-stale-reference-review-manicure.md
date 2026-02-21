---
title: Linear stale reference review for manicure ALP-2006 through ALP-2018
type: research
tags: [linear, manicure, stale-references, agent-review, fmm]
summary: Reviewed ALP-2006 through ALP-2018 for stale code references after refactoring and updated affected Linear issues in place.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

A parallel Agent Review Step checked the ALP-2006 optimistic HTTP exchange card issue set for stale file, symbol, test, fixture, and snapshot references. The review found real stale references in storage field naming, frontend Codex status values, visual spec references, brittle line references, and file size notes. A follow up verification pass corrected one over broad agent edit: planned helper names such as `_persist_http_provisional_exchange` and `_finalize_http_provisional_exchange` are valid issue deliverables and were preserved as planned helpers rather than treated as stale current code.

## Project Metadata

- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/manicure`
- fmm index: available and used
- Topology from fmm: 288 indexed files, 54,626 LOC
- Backend: `api/`, 177 files, 36,320 LOC
- Frontend: `www/`, 111 files, 18,306 LOC
- Linear parent reviewed: `ALP-2006`
- Linear children reviewed: `ALP-2007` through `ALP-2018`

## Architecture

Relevant current symbols and files verified:

- HTTP request entry point: `api/src/manicure/addon_handlers.py::handle_http_request`
- HTTP response entry point: `api/src/manicure/addon_handlers.py::handle_response`
- Current HTTP persistence helper: `api/src/manicure/exchange_recorder.py::_persist_http_exchange`
- Planned HTTP provisional helpers remain Linear deliverables: `_persist_http_provisional_exchange`, `_finalize_http_provisional_exchange`, `_delete_http_provisional_exchange`
- Storage index model: `api/src/manicure/storage/base.py::IndexEntry`, lines 110 to 121, uses field `pipeline`, not `pipeline_stats`
- Frontend index model: `www/src/types.ts::IndexEntry`, lines 50 to 64, uses field `pipeline`, not `pipeline_stats`
- SSE stream endpoint: `api/src/manicure/api/v1/stream.py::stream_exchanges`, lines 17 to 39
- Index endpoint: `api/src/manicure/api/v1/exchanges.py::list_exchanges`, lines 123 to 144
- List card component: `www/src/components/ExchangeTurnCard.tsx::ExchangeTurnCard`
- List status helper: `www/src/components/ExchangeTurnCard.tsx::statusDisplay`, lines 94 to 111
- Detail component: `www/src/components/ExchangeDetail.tsx::ExchangeDetail`

## Key Patterns

- Prefer stable file and symbol references in Linear descriptions. Replace line references with `path::symbol` where possible.
- Distinguish current code symbols from planned deliverables. A missing symbol is not stale when the issue is explicitly scoped to add that symbol.
- Treat storage and wire fields as contract names. Current `IndexEntry` uses `pipeline`; `pipeline_stats` is acceptable only as an internal variable or conceptual description.
- For frontend Codex turn state, the real terminal status union uses `interrupted`; UI copy renders that as `STOPPED`.

## Detailed Findings

### Issues updated by review agents

- `ALP-2008`: Storage acceptance changed from `pipeline_stats` to `pipeline`.
- `ALP-2009`: Finalize update dict changed from `pipeline_stats` to `pipeline`; acceptance changed to `IndexEntry.pipeline`.
- `ALP-2015`: Codex terminal status set changed from `completed | failed | stopped` to `completed | failed | interrupted`.
- `ALP-2016`: Visual spec scope updated because `www/tests/visual/exchange-list-anchored.spec.ts` exists. Current visual specs were listed explicitly.
- `ALP-2018`: Removed stale line reference to `www/src/hooks/useExchangeStream.ts:238`; kept the file reference.

### Additional coordinator corrections after agent review

- `ALP-2006`: Updated parent contract to use `IndexEntry.pipeline` and JSON equivalent `req_stats`, matching the child issues and current model names.
- `ALP-2008`: Updated the behavior section to persist `pipeline = build_pipeline_stats(audit)`.
- `ALP-2014`: Updated case 1 to assert `pipeline` from audit. Restored planned helper references in fallback cases 10 and 11 because `_persist_http_provisional_exchange` and `_finalize_http_provisional_exchange` are planned issue deliverables, not stale current code references. Kept the stable Codex test symbol reference and current `test_addon_phases.py` size note.
- `ALP-2016`: Replaced the brittle `www/src/components/ExchangeList.test.tsx:337` reference with the test name `renders an open Codex row from semantic turn state without response stats`.
- `ALP-2017`: Updated index assertions to use `pipeline`. Preserved planned helper references while anchoring them through current entry points `handle_http_request` and `handle_response`.

### Issues needing no stale reference updates

- `ALP-2007`: `api/src/manicure/flow_state.py`, `RequestFlowState`, and `update_request_flow_state` references remain valid.
- `ALP-2010`: `api/src/manicure/exchange_recorder.py`, `_emit_exchange_deleted`, and Codex delete reference remain valid.
- `ALP-2011`: `handle_http_request`, `capture_request_flow_state`, `_should_skip_breakpoint`, `handle_breakpoint`, and `update_request_flow_state` references remain valid.
- `ALP-2012`: `_persist_http_exchange` and `stamp_pipeline_tokens` references remain valid. Planned helper references are valid deliverables.
- `ALP-2013`: `handle_breakpoint`, `ManicureAddon`, `get_request_flow_state`, `is_codex_websocket_flow`, and referenced Codex tests remain valid.

### Snapshot and fixture status

- `exchange-detail-timeline-open-codex-visual-darwin.png` exists under the timeline spec snapshots.
- `exchange-detail-transport-diagnostics-visual-darwin.png` exists under the transport spec snapshots.
- `mockCodexTimelineOpenId` and `mockCodexTransportDiagnosticId` still satisfy the IndexEntry level provisional gate because their list shape has `res: null` and no `codex_turn`.
- These Darwin snapshots remain platform specific but not stale.

## Dependencies

- Linear MCP: used to fetch and update ALP-2006 through ALP-2018.
- fmm MCP: used for topology, outlines, and symbol verification before any direct inspection.
- `rg` and `sed`: used after fmm for exact test text checks and line reference replacement.

## Relevance to Helioy

This keeps Nancy executable work aligned with the current manicure codebase. The main operational lesson is to flag missing current symbols only after classifying whether they are existing references or planned deliverables.

## Open Questions

None for stale reference cleanup. Implementation sequencing and product design were intentionally out of scope.
