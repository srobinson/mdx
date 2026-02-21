---
title: Linear stale reference review for Nancy ALP 2013, 2014, and 2017
type: research
tags: [nancy, linear, stale-references, codex-transport, fmm]
summary: Reviewed three Nancy Linear issues after test decomposition and updated stale Codex transport test references in place.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed ALP-2013, ALP-2014, and ALP-2017 for stale file references after the test decomposition phase. ALP-2013 and ALP-2014 contained stale references to the former monolithic Codex transport test file. Linear descriptions were updated in place with current file paths.

## Project Metadata

- Project: Nancy worktree at `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`
- Languages: Python backend under `api/`, TypeScript frontend under `www/`
- Structural index: `.fmm.db` present in the worktree
- Review date: 2026-04-27

## Architecture

fmm reports 287 indexed files, with 177 files under `api/` and 110 files under `www/`. The relevant decomposition moved Codex transport tests from the former `api/src/manicure/test_codex_transport.py` location into `api/src/manicure/codex/test_transport_*.py` files.

## Detailed Findings

### ALP-2013

Updated stale Codex reference paths:

- `api/src/manicure/test_codex_transport.py` for `test_addon_websocket_end_cancellation_restores_provisional_exchange` now points to `api/src/manicure/codex/test_transport_lifecycle.py`.
- `api/src/manicure/test_codex_transport.py` for `test_addon_websocket_message_drops_initial_frame_when_user_drops` now points to `api/src/manicure/codex/test_transport_addon.py`.

Verified current symbols with fmm:

- `test_addon_websocket_end_cancellation_restores_provisional_exchange`: `api/src/manicure/codex/test_transport_lifecycle.py`, lines 229 to 277.
- `test_addon_websocket_message_drops_initial_frame_when_user_drops`: `api/src/manicure/codex/test_transport_addon.py`, lines 385 to 409.

### ALP-2014

Updated stale Codex transport references:

- General Codex coverage reference now points to `api/src/manicure/codex/test_transport_addon.py` and `api/src/manicure/codex/test_transport_lifecycle.py`.
- Canonical emit and SSE capture pattern now points to `api/src/manicure/codex/test_transport_addon.py:119-155`.
- `mitmproxy.test.tflow()` import reference now points to `api/src/manicure/codex/test_transport_support.py`.
- Codex parity reference now points to `api/src/manicure/codex/test_transport_addon.py` and `api/src/manicure/codex/test_transport_lifecycle.py`.

Verified current symbols with fmm:

- `test_addon_websocket_message_persists_provisional_codex_exchange`: `api/src/manicure/codex/test_transport_addon.py`, lines 119 to 155.
- `tflow` named import from `mitmproxy.test`: `api/src/manicure/codex/test_transport_support.py`.

### ALP-2017

No stale file references found. Existing referenced files remain valid:

- `api/src/manicure/api/v1/stream.py`
- `api/src/manicure/api/v1/test_exchanges_list.py`

The optional sibling `api/src/manicure/api/v1/test_exchanges_recovery.py` is an intended new test target, so absence in the worktree is not treated as stale.

## Dependencies

Relevant current files:

- `api/src/manicure/codex/test_transport_addon.py`
- `api/src/manicure/codex/test_transport_lifecycle.py`
- `api/src/manicure/codex/test_transport_support.py`
- `api/src/manicure/test_addon_phases.py`
- `api/src/manicure/api/v1/test_breakpoint.py`
- `api/src/manicure/storage/test_disk.py`

## Relevance to Helioy

This review confirms that post decomposition Linear work remains executable by Nancy agents without stale test file paths. It also reinforces the Helioy preference for stable file and symbol references in Linear issue descriptions.

## Open Questions

None. No unresolved stale references remain for the reviewed scope.
