---
title: Stale Linear File References After ALP 2019 Test Decomposition
type: research
tags: [linear, manicure, nancy, tests, stale-references, alp-2019]
summary: Parallel review found and updated stale Linear references in ALP-2028, ALP-2039, ALP-2038, ALP-2036, and ALP-2037 after ALP-2041 through ALP-2047 decomposition.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed the requested pre-decomposition Linear issues against the current `nancy-ALP-2019` worktree. Five issues contained stale or too narrow file references after decomposition and were updated directly in Linear. No code was changed.

## Project Metadata

- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`
- fmm topology: 287 indexed files, 53,830 LOC
- Main areas: `api/` with 177 files, `www/` with 110 files
- Review scope: ALP-2032, ALP-2028, ALP-2031, ALP-2029, ALP-2038, ALP-2034, ALP-2037, ALP-2035, ALP-2030, ALP-2039, ALP-2036, ALP-2033
- Decomposition context: ALP-2041 through ALP-2047

## Architecture

Current decomposed test families relevant to the review:

- `api/src/manicure/test_track_manager_{core,lifecycle,anthropic,codex,support}.py`
- `api/src/manicure/codex/test_transport_turn_{close,completion,derivation,pause}.py`
- `api/src/manicure/codex/test_repair_{diagnostics,migration,rebuild,safety,support}.py`
- `www/src/hooks/useExchangeStream.{forwarding,pausedTokens,race,validation}.test.tsx`
- `www/src/components/ExchangeList.test.tsx`
- `www/src/components/ExchangeList.ordering.test.tsx`
- `www/src/components/ExchangeList.trackTree.test.tsx`
- `www/src/components/exchangeListRows.test.ts`
- `www/src/components/__test-utils__/exchangeList.ts`
- `www/src/components/editor/SamplingSection.*.test.tsx`
- `www/tests/visual/fixtures/` plus retained barrel `www/tests/visual/fixtures.ts`

## Detailed Findings

| Issue | Result | Linear update |
| --- | --- | --- |
| ALP-2032 | No stale decomposed file reference found. Referenced files still exist. | None |
| ALP-2028 | A comment referenced stale pytest node ids under `src/manicure/test_track_manager.py`. The named Codex tests now live in `src/manicure/test_track_manager_codex.py`. | Updated comment `97a65d41-4581-4a1e-b8cf-5964ba71215e`, replacing both stale node ids with `src/manicure/test_track_manager_codex.py::...`. |
| ALP-2031 | No stale decomposed file reference found. `www/src/components/exchangeListRows.ts` still exists. | None |
| ALP-2029 | No stale decomposed file reference found. `api/src/manicure/storage/test_disk_cache_backfill.py` still exists. | None |
| ALP-2038 | Referenced stale line range `exchangeListRows.test.ts:246-317`. The file still exists, but current fan-out cases are at `224-295`. | Updated issue description to `exchangeListRows.test.ts:224-295`. |
| ALP-2034 | No stale reference found. `www/src/components/ExchangeList.test.tsx` and `www/src/components/exchangeListRows.test.ts` still exist. | None |
| ALP-2037 | Reference section pointed only at `api/src/manicure/test_track_manager_lifecycle.py`, which is too narrow after ALP-2046. | Updated description line to `File family: api/src/manicure/test_track_manager_{core,lifecycle,anthropic,codex,support}.py`. |
| ALP-2035 | No stale test decomposition reference found. `track_anchors.py` is absent, but it is a proposed helper path in the canceled issue, not a stale decomposed file. | None |
| ALP-2030 | No stale decomposed file reference found. | None |
| ALP-2039 | Description referenced removed `www/src/hooks/useExchangeStream.test.tsx` twice. Current spawn anchor coverage is in `www/src/hooks/useExchangeStream.validation.test.tsx`. | Updated both occurrences to `www/src/hooks/useExchangeStream.validation.test.tsx`. |
| ALP-2036 | Referenced stale helper path `www/src/components/__test-utils__/makeEntry.ts` and framed scope as two files. Current helper is `www/src/components/__test-utils__/exchangeList.ts`, used across the ExchangeList test family. | Updated issue description to use `www/src/components/__test-utils__/exchangeList.ts`, `www/src/components/ExchangeList*.test.tsx`, and `www/src/components/exchangeListRows.test.ts`. |
| ALP-2033 | No stale decomposed file reference found. | None |

## Key Patterns

- Replace old monolithic test file references with file-family phrases when ownership now spans multiple decomposed files.
- Keep specific file paths when behavior ownership is clear, such as `useExchangeStream.validation.test.tsx` for validation and history cache coverage.
- Avoid fragile line ranges in Linear where possible. One stale line range was updated because it already existed in the issue and the replacement was concrete.

## Verification Notes

- fmm was used first for repo topology and current decomposed test layout.
- Agents verified current path existence locally before changing Linear.
- Linear issue descriptions and comments were updated only when the stale reference was concrete.
- SamplingSection and visual fixture sweep found no concrete stale references in the requested issue set.

## Relevance to Helioy

This keeps Nancy Linear work items aligned with the decomposed test layout and reduces the chance that future autonomous agents work from pre-decomposition paths.

## Open Questions

- ALP-2037 title still names `test_track_manager_lifecycle.py`. It was not changed because the requested review focused on references in issue text, and the description now contains the correct file-family reference.
