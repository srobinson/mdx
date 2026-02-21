---
title: Linear stale reference review for Nancy ALP 2007 to 2009
type: research
tags: [nancy, linear, review, stale-references]
summary: ALP-2007 through ALP-2009 were checked for stale file references after decomposition, with no Linear updates required.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed Linear issues ALP-2007, ALP-2008, and ALP-2009 for stale file references after the test decomposition phase. All referenced files still exist in the current worktree, and referenced symbols were confirmed by fmm outlines where applicable.

## Project Metadata

- Repository: `nancy-ALP-2019`
- Indexed topology from fmm: 287 files, 53,843 LOC
- Main areas: `api/` and `www/`
- Review type: Linear description file reference validation only

## Architecture Context

The reviewed issues target HTTP provisional exchange flow code in the API layer:

- Flow state: `api/src/manicure/flow_state.py`
- HTTP handlers: `api/src/manicure/addon_handlers.py`
- Exchange persistence: `api/src/manicure/exchange_recorder.py`
- Codex reference implementation: `api/src/manicure/codex/exchange.py`
- Storage interface: `api/src/manicure/storage/base.py`

## Detailed Findings

### ALP-2007

Checked references:

- `api/src/manicure/flow_state.py`: exists. fmm confirms `RequestFlowState` and `update_request_flow_state`.
- `api/src/manicure/addon_handlers.py`: exists. fmm confirms `handle_http_request` and `handle_response`.
- `api/src/manicure/exchange_recorder.py`: exists. fmm confirms `_persist_http_exchange`.
- `api/src/manicure/pause_session.py`: exists by filesystem check.

Result: no stale references. No Linear update made.

### ALP-2008

Checked references:

- `api/src/manicure/exchange_recorder.py`: exists. fmm confirms `_persist_http_exchange` location for nearby helper placement.
- `api/src/manicure/codex/exchange.py`: exists. fmm confirms `_persist_codex_provisional_exchange`.
- `api/CLAUDE.md`: exists by filesystem check.

Result: no stale references. No Linear update made.

### ALP-2009

Checked references:

- `api/src/manicure/exchange_recorder.py`: exists.
- `api/src/manicure/codex/exchange.py`: exists. fmm confirms `_finalize_codex_provisional_exchange`.
- `api/src/manicure/storage/base.py`: exists. fmm confirms `StorageBackend.read_index_entry`.

Result: no stale references. No Linear update made.

## Dependencies

Validation used fmm for indexed source files and direct filesystem existence checks for documentation files not represented as source symbols.

## Relevance to Helioy

This review confirms the first backend slice of the HTTP provisional exchange work can proceed without stale file path remediation from the decomposition phase.

## Open Questions

None for this scope.
