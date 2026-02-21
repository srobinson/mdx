---
title: Stale Linear File References After ExchangeList Test Decomposition
type: research
tags: [linear, nancy, alp-2019, tests, exchangelist]
summary: Reviewed ALP-2038, ALP-2034, and ALP-2036 for stale ExchangeList test and fixture references after ALP-2047 and ALP-2045.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed three pre-decomposition Linear issues against the local Nancy worktree. Two issues had concrete stale references and were updated in Linear. No code was modified.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`
- fmm topology: 287 indexed files, 53,830 LOC
- Main areas: `api/` with 177 files, `www/` with 110 files
- Relevant frontend test paths verified under `www/src/components/`

## Architecture

Current ExchangeList test family:

- `www/src/components/ExchangeList.test.tsx`: component row behavior
- `www/src/components/ExchangeList.ordering.test.tsx`: anchored ordering behavior
- `www/src/components/ExchangeList.trackTree.test.tsx`: track tree behavior
- `www/src/components/exchangeListRows.test.ts`: pure projection coverage
- `www/src/components/__test-utils__/exchangeList.ts`: shared `makeEntry` helper

`makeEntry` is exported from `www/src/components/__test-utils__/exchangeList.ts` and imported by all four ExchangeList related test files.

## Detailed Findings

### ALP-2038

Issue description referenced fan-out tie-breaking at `exchangeListRows.test.ts:246-317`. Current verified range is `exchangeListRows.test.ts:224-295`, covering both fan-out sibling ordering cases.

Linear update performed: yes. Replaced only the stale line range.

### ALP-2034

Referenced files still exist:

- `www/src/components/ExchangeList.test.tsx`
- `www/src/components/exchangeListRows.test.ts`

No comments were present. No concrete stale decomposed or renamed file reference found.

Linear update performed: no.

### ALP-2036

Issue description referenced planned helper path `www/src/components/__test-utils__/makeEntry.ts`, but current helper path is `www/src/components/__test-utils__/exchangeList.ts`.

The description also framed scope as two files. Current scope is the ExchangeList test family plus `exchangeListRows.test.ts`:

- `www/src/components/ExchangeList*.test.tsx`
- `www/src/components/exchangeListRows.test.ts`
- `www/src/components/__test-utils__/exchangeList.ts`

Linear update performed: yes. Replaced stale helper path and narrowed wording to the current file family.

## Dependencies

Relevant fmm verified dependency facts:

- `ExchangeList.test.tsx`, `ExchangeList.ordering.test.tsx`, and `ExchangeList.trackTree.test.tsx` depend on `./ExchangeList` and `./__test-utils__/exchangeList`.
- `exchangeListRows.test.ts` imports `makeEntry` from `./__test-utils__/exchangeList`.
- `__test-utils__/exchangeList.ts` exports `makeEntry`.

## Relevance to Helioy

This validates Linear issue hygiene after decomposition work. It also confirms that future Nancy ExchangeList test references should use the file family phrase `www/src/components/ExchangeList*.test.tsx` when the behavior is not owned by one specific decomposed test file.

## Open Questions

- None for the requested issue set.
