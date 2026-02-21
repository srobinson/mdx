---
title: Stale Linear File References After Track Manager Test Decomposition
type: research
tags: [nancy, linear, tests, track-manager, alp-2046]
summary: ALP-2037 had one stale monolithic track manager test reference and was updated to the current decomposed file family; ALP-2035 required no update.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed ALP-2037 and ALP-2035 for stale file references after ALP-2046 decomposed track manager tests by provider trace. ALP-2037 referenced the old monolithic lifecycle test file in its Reference section, while the repo now uses a track manager test family. ALP-2035 references production helper paths and had no concrete stale reference caused by the test decomposition.

## Project Metadata

- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`
- fmm index: available. Topology reported 287 indexed files and 53,830 LOC across `api/` and `www/`.
- Relevant language: Python under `api/src/manicure`.

## Architecture

Track manager tests now live in a provider oriented file family:

- `api/src/manicure/test_track_manager_core.py`
- `api/src/manicure/test_track_manager_lifecycle.py`
- `api/src/manicure/test_track_manager_anthropic.py`
- `api/src/manicure/test_track_manager_codex.py`
- `api/src/manicure/test_track_manager_support.py`

`git show --name-status f393073` confirms ALP-2046 added the core, anthropic, codex, and support files while modifying the lifecycle file.

## Detailed Findings

| Issue | Finding | Verification | Linear update |
| --- | --- | --- | --- |
| ALP-2037 | Description Reference section used `File: api/src/manicure/test_track_manager_lifecycle.py`, which is now too narrow after ALP-2046 decomposition. | fmm outlines show current tests across lifecycle, core, anthropic, codex, and support files. | Updated description line to `File family: api/src/manicure/test_track_manager_{core,lifecycle,anthropic,codex,support}.py`. |
| ALP-2035 | No stale track manager test file reference. Description references production files: `codex/exchange.py`, `exchange_recorder.py`, `codex/exchange_derivation.py`, and intended new `track_anchors.py`. | Current repo contains the three production files. `track_anchors.py` is not present, but it is a proposed new helper path in the canceled issue, not a stale test decomposition reference. | No update. |

## Dependencies

- fmm MCP for topology and file outlines.
- Linear MCP for issue descriptions and update.
- Local git and `find` for confirming ALP-2046 file additions and current path existence.

## Relevance to Helioy

This keeps Linear planning references aligned with the decomposed Nancy test layout, reducing risk that future agents operate against pre-decomposition assumptions.

## Open Questions

- ALP-2037 title still names `test_track_manager_lifecycle.py`. I did not change it because the requested workflow focused on description and comments, and the smallest concrete stale reference was in the Reference section.
