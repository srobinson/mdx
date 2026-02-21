---
title: Completed Worker Review for Nancy ALP-2029, ALP-2030, and ALP-2037
type: research
tags: [nancy, manicure, linear-review, backend, tests, spawn-anchor]
summary: Review Agent A found one acceptance naming gap in ALP-2029 and clean results for ALP-2030 and ALP-2037.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed three completed Worker Done issues in `nancy/ALP-2019` without pulling branches. ALP-2030 and ALP-2037 satisfy their implementation and test acceptance criteria. ALP-2029 covers the requested behavior, but misses the pinned accepted test names and only asserts the `spawn_anchor` field rather than full entry equality.

## Project Metadata

- Project: `manicure`
- Worktree: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`
- Branch: `nancy/ALP-2019`
- Backend: Python 3.12 plus, FastAPI, Pydantic, pytest, pytest asyncio, ruff
- Relevant commits: `224ccce` ALP-2030, `c0c5593` ALP-2029, `6c79950` review split for ALP-2029, `ad290df` ALP-2037

## Architecture

- `api/src/manicure/track_manager.py` owns track assignment and spawn anchor production.
- `api/src/manicure/storage/test_disk_cache_backfill.py` covers disk index reload behavior.
- `api/src/manicure/test_track_manager_lifecycle.py` covers lifecycle routing, spawn closure, and spawn anchor preservation.
- `www/src/hooks/useExchanges.ts` projects nested `spawn_anchor` data into flat runtime track ordering fields through `adoptAnchor`.

## Detailed Findings

### ALP-2029: Add spawn anchor coverage to disk cache backfill tests

Status: Needs fix.

Evidence:
- Acceptance requires test functions named `test_disk_cache_backfill_preserves_spawn_anchor` and `test_disk_cache_backfill_handles_null_spawn_anchor`.
- Current tests are `TestSpawnAnchorRoundTrip::test_preserves_populated_spawn_anchor` and `TestSpawnAnchorRoundTrip::test_preserves_null_spawn_anchor` at `api/src/manicure/storage/test_disk_cache_backfill.py:191` and `api/src/manicure/storage/test_disk_cache_backfill.py:217`.
- The tests use nested `SpawnAnchor`, evict `storage._index_cache`, reload via `read_index_entry`, and verify populated and null `spawn_anchor` behavior.
- The populated test asserts `reloaded.spawn_anchor == original_anchor`; the acceptance says round trip equals original, so full entry equality would better match the contract.

Action taken:
- Added Linear comment `974523b1-02f9-4d09-b0fb-53057e6a83f2` with evidence and recommended fix.

### ALP-2030: Document spawn_order semantics across multi-response track spawns

Status: Pass.

Evidence:
- `TrackManager.observe_response` docstring explains response scoped `spawn_order` and cross response chronology through `track_spawn_exchange_id` plus parent exchange ordering at `api/src/manicure/track_manager.py:132`.
- Inline comment near `spawn_order = 0` states this is a response local sibling ordinal at `api/src/manicure/track_manager.py:145`.
- `_register_anthropic_spawn` and `_register_codex_spawn` both include the requested one line ordinal scope note at `api/src/manicure/track_manager.py:212` and `api/src/manicure/track_manager.py:247`.
- Inspection of `www/src/hooks/useExchanges.ts:41` found `adoptAnchor` preserves non null nested anchor fields and ordering falls back to timestamps then insertion order. No regression test was required because no cross response sibling misordering was observed in this review.

### ALP-2037: Convert test_track_manager_lifecycle.py to table-driven cases

Status: Pass.

Evidence:
- Late tool result scenarios are parametrized under `test_late_tool_result_for_closed_subagent_routes_to_parent` with two retained case ids at `api/src/manicure/test_track_manager_lifecycle.py:149`.
- Spawn anchor scenarios are represented by `ANCHOR_CASES` and `test_track_manager_spawn_anchor_cases` with five retained case ids at `api/src/manicure/test_track_manager_lifecycle.py:461` and `api/src/manicure/test_track_manager_lifecycle.py:551`.
- Two standalone lifecycle tests remain one offs where table conversion would reduce clarity: `test_codex_agent_kill_closes_targeted_subagent_track` and `test_codex_resolved_spawn_result_does_not_reopen_closed_track`.
- Total scenario count remains 9: 2 late tool result cases, 2 standalone Codex lifecycle tests, and 5 spawn anchor cases.
- Anchor assertions read nested `assignment.spawn_anchor.*` at `api/src/manicure/test_track_manager_lifecycle.py:566` through `api/src/manicure/test_track_manager_lifecycle.py:574`.

## Verification

Commands run from `api/`:

```bash
uv run pytest src/manicure/storage/test_disk_cache_backfill.py src/manicure/test_track_manager_lifecycle.py
uv run ruff check src/manicure/storage/test_disk_cache_backfill.py src/manicure/test_track_manager_lifecycle.py src/manicure/track_manager.py
```

Results:
- `15 passed in 0.08s`
- `All checks passed!`

## Dependencies

- `pytest` and `pytest-asyncio` provide backend test execution.
- `ruff` validates lint and style for touched backend files.
- `manicure.storage.base.SpawnAnchor` is the nested anchor data model used by tests and runtime assignments.

## Open Questions

- I did not verify PR description text for ALP-2037 because this review was limited to the current worktree and Linear issues. The code itself exposes the retained 9 scenario count in pytest collection output.
