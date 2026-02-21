---
title: ALP-2048 ExchangeList Ordering Test Scope Review
type: research
tags: [manicure, alp-2048, frontend, tests, review]
summary: ALP-2048 trims ExchangeList component ordering tests away from full projection arrays while preserving integration coverage.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

ALP-2048 is complete. The implementation removes exact full row projection array assertions from `ExchangeList.ordering.test.tsx` and keeps component integration checks for rendered track headers, selected state, click behavior, relative rendered placement, and collapse behavior.

No correctness, regression, quality, or DRY blockers were found. The pure projection contract remains owned by `exchangeListRows.test.ts`.

## Project Metadata

- Project: `manicure`
- Area: `www/src/components`
- Language: TypeScript, React 19
- Test stack: Vitest, Testing Library, jsdom
- Build system: pnpm, Vite, TypeScript project references
- Node requirement: `>=20.19.0`
- fmm: `.fmm.db` present in the worktree

## Architecture

`ExchangeList.tsx` renders rows produced by `projectAnchoredRows`:

- `ExchangeList.tsx:154-162` builds the exchange track tree and projects rows.
- `ExchangeList.tsx:164-173` virtualizes the projected rows.
- `ExchangeList.tsx:201-231` renders either `TrackHeader` or `ExchangeTurnCard` using the row metadata.

The test split now matches the architectural boundary:

- `exchangeListRows.test.ts` owns exact projection correctness for row keys and ordering.
- `ExchangeList.ordering.test.tsx` owns rendered integration behavior that depends on `ExchangeList`, `TrackHeader`, and `ExchangeTurnCard` working together.

## Detailed Findings

### Acceptance criteria

1. `ExchangeList.ordering.test.tsx` no longer asserts full exact row projection arrays.
   - Verified no `toEqual`, `rowOrder`, `getAllByTestId`, or row array mapping remains in `www/src/components/ExchangeList.ordering.test.tsx`.
   - The old exact array helper was replaced with `rowIndex(testId)` at `ExchangeList.ordering.test.tsx:7-10`.

2. Component tests keep useful integration checks.
   - Claude track renders, selected row state is exercised, and the child track header is asserted between continuation and spawn rows at `ExchangeList.ordering.test.tsx:59-68`.
   - Codex track renders model text, click selection is exercised, and the track header is asserted between continuation and spawn rows at `ExchangeList.ordering.test.tsx:126-136`.
   - Grandchild nesting checks rendered depth and relative placement at `ExchangeList.ordering.test.tsx:183-189`.
   - Fan out sibling ordering keeps a relative rendered ordering check without asserting the whole projection array at `ExchangeList.ordering.test.tsx:231-236`.
   - Collapse integration remains covered at `ExchangeList.ordering.test.tsx:323-328`.
   - Track header parent focus behavior remains covered at `ExchangeList.ordering.test.tsx:377-378` and `ExchangeList.ordering.test.tsx:425-426`.

3. `exchangeListRows.test.ts` remains the projection owner.
   - Claude exact projection remains at `exchangeListRows.test.ts:79-86`.
   - Codex exact projection remains at `exchangeListRows.test.ts:135-141`.
   - Collapse projection remains at `exchangeListRows.test.ts:172-173`.
   - Spawn anchor placement remains at `exchangeListRows.test.ts:215-221`.
   - Fan out and tie breaking remain at `exchangeListRows.test.ts:224-295`.
   - Grandchild projection remains at `exchangeListRows.test.ts:335-343`.
   - Anchor outside fetched window remains at `exchangeListRows.test.ts:381-401`.

### Code quality and DRY

The change is scoped to one test file and removes duplicate full projection assertions. The remaining relative `data-index` checks are appropriate component level assertions because they verify what the rendered list exposes without duplicating the full `projectAnchoredRows` contract.

No production code changed. No new abstraction was added.

### Regression risk

Regression risk is low. The tests now fail for integration issues such as missing headers, broken click behavior, selected state regressions, collapse rendering regressions, and rendered relative placement regressions. Exact row projection regressions continue to fail in `exchangeListRows.test.ts`.

## Verification

Commands run from `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`:

```bash
pnpm --dir www test -- ExchangeList
```

Result: 33 test files passed, 293 tests passed.

```bash
pnpm --dir www typecheck
```

Result: passed.

```bash
pnpm --dir www lint
```

Result: passed, 117 files checked.

## Dependencies

Relevant dependencies:

- `@testing-library/react`: renders `ExchangeList` and queries DOM behavior.
- `vitest`: test runner and mocks.
- `@tanstack/react-virtual`: row virtualization used by `ExchangeList`.
- `zustand`: collapse state store used during collapse integration tests.

## Relevance to Helioy

This is a good cleanup pattern for Helioy UI tests: pure projection or transformation helpers own exact structural arrays, while component tests assert rendered behavior and user level integration.

## Open Questions

None for ALP-2048. Linear status is `Worker Done`, not final completed, so it can be advanced after review if that is the workflow.
