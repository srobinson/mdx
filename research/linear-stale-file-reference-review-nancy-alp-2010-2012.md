---
title: Linear stale file reference review for Nancy ALP-2010 to ALP-2012
type: research
tags: [nancy, linear, review, file-references]
summary: ALP-2010, ALP-2011, and ALP-2012 contain no stale file references after the decompose phase.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed Linear issues ALP-2010, ALP-2011, and ALP-2012 for stale file references after the decompose phase. All referenced source paths still exist in the ALP-2019 Nancy worktree, so no Linear updates were required.

## Project Metadata

- Project: Nancy, Helioy worktree `manicure-worktrees/nancy-ALP-2019`
- Topology from fmm: 287 indexed files, 53,843 LOC
- Major areas: `api/` with 177 files, `www/` with 110 files
- fmm index available and used as primary structural context

## Detailed Findings

### ALP-2010

Referenced paths:

- `api/src/manicure/exchange_recorder.py`
- `api/src/manicure/codex/exchange.py`

Validation:

- fmm found both files.
- Filesystem existence check confirmed both paths exist.
- Referenced symbols are still present: `_emit_exchange_deleted` and `_persist_http_exchange` in `api/src/manicure/exchange_recorder.py`; `_delete_codex_provisional_exchange` in `api/src/manicure/codex/exchange.py`.

Outcome: no stale references. No Linear update made.

### ALP-2011

Referenced paths:

- `api/src/manicure/addon_handlers.py`
- `api/src/manicure/flow_state.py`

Validation:

- fmm found both files.
- Filesystem existence check confirmed both paths exist.
- Referenced symbols are still present: `handle_http_request` in `api/src/manicure/addon_handlers.py`; `update_request_flow_state` in `api/src/manicure/flow_state.py`.

Outcome: no stale references. No Linear update made.

### ALP-2012

Referenced path:

- `api/src/manicure/exchange_recorder.py`

Validation:

- fmm found the file.
- Filesystem existence check confirmed the path exists.
- Referenced symbol `_persist_http_exchange` is still present.

Outcome: no stale references. No Linear update made.

## Open Questions

None for this scope.
