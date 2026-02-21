---
title: Worker Review for ALP-2035 and ALP-2036
type: research
tags: [nancy, manicure, linear-review, backend, frontend, tests]
summary: ALP-2035 has an acceptance criteria mismatch; ALP-2036 satisfies fixture sharing expectations and targeted tests pass.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed completed Worker Done issues ALP-2035 and ALP-2036 in the current `nancy/ALP-2019` worktree. ALP-2036 passes acceptance and quality review. ALP-2035 improves DRY by centralizing spawn anchor projection through `assignment_index_fields()`, but it does not satisfy the issue's literal acceptance criteria because the requested `track_anchors.py` helper is absent.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`
- Branch: `nancy/ALP-2019`
- fmm: `.fmm.db` present
- Backend: Python 3.13 in `api`, `uv`, pytest
- Frontend: TypeScript, React 19, Vite, Vitest, pnpm

## Review Method

- Used fmm first: `fmm_list_files`, `fmm_search`, `fmm_file_outline`, `fmm_read_symbol`, `fmm_dependency_graph`.
- Fetched Linear issues ALP-2035 and ALP-2036 with relations.
- Inspected current worktree only. No branches pulled.
- Ran targeted backend and frontend tests.
- Added a Linear comment only where a real acceptance gap was found.

## Findings

### ALP-2035: Needs fix

Issue acceptance requires `_extract_spawn_anchor(track_assignment) -> SpawnAnchor | None` in `api/src/manicure/track_anchors.py` and replacement of the three known emit sites with that helper.

Current worktree state:

- `api/src/manicure/track_anchors.py` is absent.
- `_extract_spawn_anchor` is absent.
- Spawn anchor projection is now folded into `assignment_index_fields()` at `api/src/manicure/track_manager.py:464-475`.
- `assignment_index_fields()` is reused for both `IndexEntry` construction and emit kwargs at:
  - `api/src/manicure/codex/exchange.py:118`
  - `api/src/manicure/codex/exchange.py:148`
  - `api/src/manicure/codex/exchange.py:257`
  - `api/src/manicure/codex/exchange.py:284`
  - `api/src/manicure/exchange_recorder.py:224`
  - `api/src/manicure/exchange_recorder.py:248`
- The fourth surface has the requested divergence comment at `api/src/manicure/codex/exchange_derivation.py:421-422` and emits `updated_entry.spawn_anchor` at line 422.

Assessment:

- DRY goal is partially satisfied by reusing `assignment_index_fields()`.
- Literal acceptance is not satisfied because the required helper and file do not exist.
- This may be an intentional review change from commit `7f6372d review[ALP-2019]: fold spawn anchor extraction into existing assignment_index_fields`, but Linear acceptance was not updated.

Action taken:

- Added Linear comment `0b2f7d02-0719-458a-b689-088eaf346490` to ALP-2035 with evidence and recommended fix.

Recommended fix:

- Either restore the accepted design with `_extract_spawn_anchor()` in `api/src/manicure/track_anchors.py`, or update ALP-2035 acceptance criteria to document the intentional `assignment_index_fields()` design.

### ALP-2036: Pass

Issue acceptance requires a shared `makeEntry()` fixture for the ExchangeList row test family and `exchangeListRows.test.ts`, defaulting to `res: null`, plus a named legacy response override for component assertions that need the old response shape.

Current worktree state:

- Shared fixture lives at `www/src/components/__test-utils__/exchangeList.ts:13-34`.
- `makeEntry()` returns a minimal `IndexEntry` with `res: null` at line 29 and accepts overrides at line 32.
- `legacyClaudeRes` is exported at `www/src/components/__test-utils__/exchangeList.ts:3-11`.
- `ExchangeList.test.tsx` imports `legacyClaudeRes` and passes it for the metric assertion path at `www/src/components/ExchangeList.test.tsx:3,16`.
- fmm dependency graph shows `makeEntry` used by:
  - `www/src/components/ExchangeList.ordering.test.tsx`
  - `www/src/components/ExchangeList.test.tsx`
  - `www/src/components/ExchangeList.trackTree.test.tsx`
  - `www/src/components/exchangeListRows.test.ts`
- No evidence of scope creep into `app.test.tsx` or `useExchanges.test.ts`.

Assessment:

- Acceptance criteria satisfied.
- DRY improved through a single fixture.
- `res` divergence is explicitly handled through overrides.
- No quality or regression concern found.

## Verification

Backend targeted tests:

```bash
cd api
uv run pytest src/manicure/test_exchange_recorder_emit.py src/manicure/storage/test_disk_cache_backfill.py
```

Result: 13 passed.

Frontend targeted tests:

```bash
cd www
pnpm test -- ExchangeList.test.tsx ExchangeList.ordering.test.tsx ExchangeList.trackTree.test.tsx exchangeListRows.test.ts
```

Result: 33 test files passed, 298 tests passed.

## Open Questions

- For ALP-2035, should the source of truth be the original Linear acceptance criteria or the later review commit that folded projection into `assignment_index_fields()`?
