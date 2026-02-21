---
title: Completed Worker Review for Nancy ALP 2033, 2034, and 2038
type: research
tags: [nancy, manicure, linear-review, frontend-tests, exchange-list]
summary: Review of three completed ExchangeList row projection issues found acceptance criteria met with tests and typecheck passing.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed ALP-2033, ALP-2034, and ALP-2038 in the current `nancy/ALP-2019` worktree. All three issues pass review: acceptance criteria are satisfied, the test boundary is cleaner, and no quality, DRY, or regression concerns were found.

## Project Metadata

- Project: `manicure`
- Area: frontend ExchangeList row projection and tests
- Language: TypeScript, React
- Test runner: Vitest
- Package manager: pnpm 10.8.1
- Relevant files:
  - `www/src/components/exchangeListRows.ts`
  - `www/src/components/exchangeListRows.test.ts`
  - `www/src/components/ExchangeList.ordering.test.tsx`
  - `www/src/components/ExchangeList.test.tsx`

## Architecture

`ExchangeList.tsx` builds or receives an `ExchangeTrack[]`, projects it through `projectAnchoredRows`, then renders virtualized track and exchange rows. Pure ordering, depth, collapse, orphan, and stable key behavior is isolated in `exchangeListRows.test.ts`. Component tests keep integration coverage in `ExchangeList.ordering.test.tsx` and `ExchangeList.test.tsx` without asserting virtualizer row indexes.

## Detailed Findings

### ALP-2033: Document depth semantics for nested inline subagent rows

Status: Pass.

Evidence:

- `www/src/components/exchangeListRows.ts:51-58` documents why exchange rows use `entryDepth` while child track headers use `childDepth`.
- The comment references the current depth regression case name after ALP-2038 renamed the old grandchild ordering test.
- No behavior changed in the projection function.
- `www/src/components/exchangeListRows.test.ts:379-392` verifies nested depth semantics directly.

Assessment: The issue asked for a short local explanation near the depth assignment and no behavior change. Current implementation satisfies that and avoids stale test name references.

### ALP-2034: Replace DOM selector assertions in ExchangeList tests with row projection assertions

Status: Pass.

Evidence:

- `fmm_search` found no `rowIndex` helper and no `data-index` assertions in the current indexed code.
- `www/src/components/ExchangeList.ordering.test.tsx` keeps rendered integration checks for selected row state, subagent headers, collapse behavior, orphan rendering, and parent focus clicks.
- Pure ordering coverage lives in `www/src/components/exchangeListRows.test.ts`, especially the row order matrix and sibling ordering cases.

Assessment: The component layer no longer duplicates projection ordering through virtualizer DOM internals. The remaining tests match the intended integration boundary.

### ALP-2038: Convert exchangeListRows.test.ts to table driven cases

Status: Pass.

Evidence:

- `www/src/components/exchangeListRows.test.ts:8-18` defines the tuple style scenario type: `[label, entries, expectedRowKeys]`.
- `www/src/components/exchangeListRows.test.ts:137-239` contains the table driven matrix.
- Matrix coverage includes Claude placement, Codex placement, multi anchor parent, one level nest, two level nest, and pending stub at anchor.
- The single loop at `www/src/components/exchangeListRows.test.ts:242-246` builds the track tree and asserts projected row keys.
- One off cases remain separate for sibling tie breaking, collapse behavior, orphan diagnostics, legacy fallback, chronological order, turn sequences, depth semantics, and stable keys.

Assessment: The refactor reduces repetition while preserving the explicit behavioral cases requested by the issue. Helper functions improve DRY without adding speculative abstraction.

## Verification

Commands run from `www/`:

```bash
pnpm test -- exchangeListRows.test.ts ExchangeList.ordering.test.tsx ExchangeList.test.tsx
pnpm typecheck
```

Results:

- Vitest: 33 test files passed, 298 tests passed.
- TypeScript: `tsc -b --noEmit` passed.
- `git status --short` remained clean.

## Dependencies

- `@testing-library/react`: component rendering assertions.
- `vitest`: unit and component test runner.
- `@tanstack/react-virtual`: virtualized row rendering in `ExchangeList.tsx`; tests now avoid depending on its DOM index details.

## Relevance to Helioy

This review confirms the ExchangeList row projection boundary is now explicit: algorithmic ordering belongs in `exchangeListRows.test.ts`, while component tests cover rendered integration behavior. That boundary reduces future review noise and makes the subagent spawn anchor work easier to evolve.

## Open Questions

None.
