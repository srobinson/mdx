---
title: Worker Done review for Nancy ALP 2029 through 2039
type: research
tags: [nancy, linear, worker-review, acceptance, tests, dry]
summary: Multi-agent review found two follow-up items among ALP-2029 through ALP-2039 and confirmed the remaining issues pass acceptance and tests.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Four agents reviewed completed Worker Done issues ALP-2029 through ALP-2039 for acceptance fit, quality, DRY, and tests. Two issues need follow-up comments in Linear: ALP-2029 and ALP-2035. The remaining nine issues passed targeted review and verification.

## Project Metadata

* Worktree: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`
* fmm topology: 287 files, 54,055 LOC
* Main areas: `api/` with 177 files, `www/` with 110 files
* Review date: 2026-04-27

## Architecture

The reviewed issues cover spawn anchor modeling, track manager behavior, disk cache backfill, ExchangeList row projection, frontend fixture DRY, and documentation comments for spawn order and depth semantics.

Relevant implementation areas:

* `api/src/manicure/track_manager.py`
* `api/src/manicure/test_track_manager_lifecycle.py`
* `api/src/manicure/storage/test_disk_cache_backfill.py`
* `www/src/components/exchangeListRows.test.ts`
* `www/src/components/ExchangeList.test.tsx`
* `www/src/components/ExchangeList.ordering.test.tsx`
* `www/src/components/__test-utils__/exchangeList.ts`
* `www/src/hooks/useExchanges.test.ts`
* `www/src/hooks/useExchangeStream.validation.test.tsx`

## Detailed Findings

### Needs fix

#### ALP-2029: Add spawn anchor coverage to disk cache backfill tests

Behavior is covered and targeted tests pass, but the literal acceptance criteria named two specific tests that are not present under those names. A Linear comment was added with evidence and recommended fix.

Verification:

* `uv run pytest src/manicure/storage/test_disk_cache_backfill.py src/manicure/test_track_manager_lifecycle.py`: 15 passed
* `uv run ruff check src/manicure/storage/test_disk_cache_backfill.py src/manicure/test_track_manager_lifecycle.py src/manicure/track_manager.py`: passed

#### ALP-2035: Extract emit-track-assignment-anchors helper to remove triplicate unpacking

Current worktree does not satisfy literal acceptance. `api/src/manicure/track_anchors.py` is absent, `_extract_spawn_anchor` is absent, and projection is instead folded into `assignment_index_fields()` at `api/src/manicure/track_manager.py:464-475`. A Linear comment was added with evidence and recommended fix.

Verification:

* Backend targeted tests: 13 passed
* Frontend targeted tests: 33 files passed, 298 tests passed

### Passed

#### ALP-2030: Document spawn_order semantics across multi-response track spawns

`spawn_order` response local semantics are documented in `TrackManager.observe_response`. Reset comments and helper notes are present. No frontend ordering regression was found.

#### ALP-2031: Surface diagnostic when subagent anchor falls outside fetched window

Passed review. No accuracy, acceptance, DRY, quality, test, or regression defects found.

#### ALP-2032: Tighten anchor field optionality between IndexEntry and ExchangeTrack

Passed review. Frontend and backend tests and type checks passed.

#### ALP-2033: Document depth semantics for nested inline subagent rows

Depth semantics comment is present near `entryDepth` and `childDepth`. The comment references the current regression test name. No behavior change found.

#### ALP-2034: Replace DOM-selector assertions in ExchangeList tests with row-projection assertions

DOM index based ordering assertions are gone. Component tests keep integration scope. Projection ordering coverage exists in `exchangeListRows.test.ts`.

#### ALP-2036: Share makeEntry test fixture across ExchangeList tests

Shared `makeEntry()` fixture exists at `www/src/components/__test-utils__/exchangeList.ts:13-34`. The fixture defaults `res: null`. `legacyClaudeRes` exists and is used for expectations needing the prior response shape. No scope creep found.

#### ALP-2037: Convert test_track_manager_lifecycle.py to table-driven cases

Lifecycle tests are table driven where appropriate. All 9 scenarios are retained. Anchor assertions use nested `spawn_anchor.*`. No DRY or quality concerns found.

#### ALP-2038: Convert exchangeListRows.test.ts to table-driven cases

Row order cases are table driven with `[label, entries, expectedRowKeys]`. Minimum matrix coverage is present. Required one off cases remain outside the matrix.

#### ALP-2039: Nest spawn anchor fields as SpawnAnchor on IndexEntry

Passed review. No accuracy, acceptance, DRY, quality, test, or regression defects found.

## Verification Summary

Agents ran targeted backend and frontend checks:

* Backend pytest subsets covering disk cache backfill and track manager lifecycle: passing
* Backend ruff checks on touched files: passing
* Backend mypy on relevant source files: passing
* Frontend Vitest subsets for ExchangeList rows, ordering, hooks, and validation: 33 files passed, 298 tests passed
* Frontend typecheck: passing
* One frontend review confirmed `git status --short` clean at time of check

## Dependencies

Review used:

* fmm MCP tools for codebase orientation and structural inspection
* Linear MCP tools for issue retrieval and comments
* `uv`, `pytest`, `ruff`, and `mypy` for backend verification
* `pnpm`, Vitest, and TypeScript typecheck for frontend verification

## Relevance to Helioy

This review keeps Nancy's autonomous execution loop honest after workers mark issues done. The two follow-up findings are acceptance alignment issues rather than broad regressions, which lets the next worker focus narrowly.

## Open Questions

* Should ALP-2029 update acceptance to match current test names, or should tests be renamed to match acceptance exactly?
* Should ALP-2035 accept the existing `assignment_index_fields()` consolidation, or should it implement the requested `track_anchors.py` helper and `_extract_spawn_anchor` symbol literally?

## Related Research Notes

* `~/.mdx/research/completed-worker-review-nancy-alp-2029-2030-2037.md`
* `~/.mdx/research/worker-done-review-agent-b-nancy-alp-2031-2039.md`
* `~/.mdx/research/completed-worker-review-nancy-alp-2033-2034-2038.md`
* `~/.mdx/research/worker-review-nancy-alp-2035-2036.md`
