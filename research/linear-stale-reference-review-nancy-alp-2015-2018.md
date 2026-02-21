---
title: Linear stale reference review for Nancy ALP 2015, 2016, and 2018
type: research
tags: [nancy, linear, stale-references, review]
summary: Reviewed three Linear issues after test and fixture decomposition, then updated stale references in place.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed ALP-2015, ALP-2016, and ALP-2018 for file references made stale by the decompose phase. Linear descriptions were updated in place where references no longer pointed at the current source of truth.

## Project Metadata

- Project: Nancy worktree at `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`
- Topology from fmm: `api/` has 177 files and `www/` has 110 files
- Scope: Linear issue descriptions only
- Code changes: none

## Architecture Context

Relevant frontend files remain under `www/src/components` and `www/src/hooks`. Visual fixtures were decomposed into family files under `www/tests/visual/fixtures/` while `www/tests/visual/fixtures.ts` remains a barrel export.

## Detailed Findings

### ALP-2015

Updated stale visual fixture references:

- `www/tests/visual/fixtures.ts` became `www/tests/visual/fixtures/exchanges.ts` for `mockExchanges`, `mockCodexTimelineOpenId`, and `mockCodexTransportDiagnosticId`.
- Added `www/tests/visual/fixtures/details.ts` for the `mockExchangeDetails` detail payload location.

Verified via fmm and filesystem inspection:

- `www/tests/visual/fixtures/exchanges.ts` exports `mockExchanges`, `mockCodexTimelineOpenId`, and `mockCodexTransportDiagnosticId`.
- `www/tests/visual/fixtures/details.ts` exports `mockExchangeDetails`.

### ALP-2016

Updated stale test and fixture references:

- `ExchangeList.test.tsx:604` became `www/src/components/ExchangeList.test.tsx:337` for the open Codex WAITING assertion.
- `www/tests/visual/fixtures.ts` became `www/tests/visual/fixtures/exchanges.ts` for Option B fixture edits and reference patterns.

Verified current files:

- `www/src/components/ExchangeList.test.tsx` still owns the observable row behavior tests relevant to the waiting gate.
- `www/tests/visual/fixtures/exchanges.ts` owns the `mockExchanges` shape after fixture decomposition.

### ALP-2018

Updated stale hook reference:

- `useExchangeStream.ts:231` became `www/src/hooks/useExchangeStream.ts:238` for the exchange detail invalidation call.

No decomposed file path replacements were needed for `ExchangeDetail.tsx` or `ExchangeDetail.test.tsx`.

## Dependencies

- fmm MCP tools for file topology and symbol oriented lookup
- Linear MCP tools for issue retrieval and in place description updates
- Filesystem inspection for existence and exact line validation

## Relevance to Helioy

This confirms the decompose phase left useful barrel files in place, but issue descriptions should reference the decomposed source files when they instruct workers to edit fixture content.

## Open Questions

None. No unresolved references remained in the scoped issues.
