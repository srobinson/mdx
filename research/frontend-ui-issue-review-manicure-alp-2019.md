---
title: Frontend UI Issue Review for Manicure ALP-2019
type: research
tags: [manicure, linear-review, frontend, exchange-list, subagents]
summary: ALP-2019 frontend issues are mostly actionable, but ALP-2039 needs added live stream scope and the ordering graph should be tightened before Nancy execution.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

The ALP-2019 frontend issue set is close to ready for Nancy, with clear separation between projection behavior, type contract cleanup, fixture cleanup, and test refactors. The main blocker is ALP-2039 scope clarity: nesting `spawn_anchor` affects the live SSE frontend path in `useExchangeStream`, not only `types` and `useExchanges`.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`
- fmm: `.fmm.db` exists and `fmm validate` passed in the worktree. MCP fmm initially resolved an older repository view, so worktree fmm CLI was used for structural inspection.
- Frontend: React 19, Vite 8, TypeScript 5.9, Vitest 4, TanStack Query and Virtual, pnpm 10.
- Relevant scripts: `www/package.json` has `test`, `typecheck`, `lint`, `build`, and `ci`.

## Architecture

- `www/src/hooks/useExchanges.ts` exports `buildExchangeTrackTree`, which groups `IndexEntry` rows and `ExchangeTrackStub` stubs into flat runtime `ExchangeTrack` nodes with child lists.
- `www/src/components/exchangeListRows.ts` exports `projectAnchoredRows`, which projects the tree into virtual list rows and places child tracks at `track_spawn_exchange_id` anchors.
- `www/src/components/ExchangeList.tsx` renders projected rows with TanStack Virtual and owns collapse interaction through `collapsedTrackIds`.
- `www/src/hooks/useExchangeStream.ts` parses live SSE exchange events into `IndexEntry`; it currently preserves flat spawn anchor fields.
- `www/src/types.ts` mirrors the wire shapes and the runtime `ExchangeTrack` shape.

## Key Patterns

- Runtime `ExchangeTrack` is intentionally flat for anchor fields even when wire shapes change.
- Projection tests in `exchangeListRows.test.ts` are the right home for ordering assertions.
- Component tests in `ExchangeList.test.tsx` should retain integration concerns such as virtualizer mount and collapse behavior.
- Worktree fmm CLI can be more reliable than MCP fmm when MCP is attached to another checkout.

## Detailed Findings

### Overall readiness

Ready with changes. ALP-2031, ALP-2033, ALP-2034, ALP-2036, and ALP-2038 are implementable as written with minor wording fixes. ALP-2032 is correctly blocked by ALP-2039. ALP-2039 needs scope correction before execution because live stream parsing is missing from the frontend section.

### ALP-2031

- Clear behavior target: orphan anchored tracks should remain visible, but should carry diagnostics.
- Clarify that `meta` belongs on `ExchangeListRow` track rows, not on `ExchangeTrack`.
- Clarify that row metadata is emitted regardless of `import.meta.env.DEV`; only `console.warn` is DEV gated.
- The current description conflicts with itself by saying tests should not spy on logs while also requiring warn assertion. Use one narrow warn spy test, or explicitly say warning behavior is covered by implementation review only.
- Ensure no anchor at all remains a legacy fallback with no orphan warning.

### ALP-2032

- Correctly blocked by ALP-2039.
- Needs exact semantics for conflicting non null anchors. If the policy is last non null write wins, then a later non null source must overwrite an existing non null value.
- Add two arrival order tests in `useExchanges.test.ts`, and consider a third conflicting non null case if the overwrite policy is intentional.

### ALP-2033

- Actionable and low risk.
- Can stay separate, but it is tiny and touches the same symbol as ALP-2031. Merge into ALP-2031 if reducing Nancy overhead matters more than preserving strict issue purity.

### ALP-2034

- Sound direction. Ordering assertions already exist in `exchangeListRows.test.ts`, so this issue should mostly remove duplicate DOM order tests from `ExchangeList.test.tsx`.
- Keep collapse interactivity in the component test. It exercises `ExchangeList`, `TrackHeader`, and UI store behavior that projection tests cannot cover.
- Avoid replacing component DOM tests with direct calls to `projectAnchoredRows` inside `ExchangeList.test.tsx`; that would duplicate the projection test layer.

### ALP-2036

- Ready. The two local `makeEntry` fixtures differ on `res`, so a shared minimal fixture with overrides is justified.
- Keep the scope limited to `ExchangeList.test.tsx` and `exchangeListRows.test.ts` as the issue states. `useExchanges.test.ts` and `app.test.tsx` can remain independent unless a later issue explicitly expands scope.

### ALP-2038

- Useful, but the current matrix instruction may not reach the line reduction target if each case still carries full entry objects.
- Add a small scenario builder or tuple format to make provider, anchor, nesting, and expected order explicit.
- Keep orphan diagnostics, collapse behavior, depth checks, and turn sequence checks as one offs if they do not fit the row order matrix.

### ALP-2039

- Blocker before execution: add `www/src/hooks/useExchangeStream.ts` and `www/src/hooks/useExchangeStream.test.tsx` to the frontend scope. Live SSE events currently parse flat spawn anchor fields into `IndexEntry`; nesting the wire contract without updating this path will break live anchored rows.
- Cross cutting scope is broad. If assigned to a frontend agent, split the backend schema and emitter work from the frontend mirror work. If kept as one issue, assign to a full stack agent.
- Backend references should include the Codex provisional rewrite path in `api/src/manicure/codex/exchange_derivation.py`, because it emits `updated_entry` anchor fields back to the live stream.
- Existing frontend tests that use flat fields include `useExchanges.test.ts`, `useExchangeStream.test.tsx`, `ExchangeList.test.tsx`, and `exchangeListRows.test.ts`; fixture migration must cover all affected tests, even if the shared fixture only covers two files.

## Dependency Recommendations

Hard dependencies:

1. ALP-2036 before ALP-2039.
2. ALP-2039 before ALP-2032.
3. ALP-2039 before ALP-2035, as already captured outside this frontend review.

Recommended execution order:

1. ALP-2036.
2. ALP-2034.
3. ALP-2038.
4. ALP-2039, after adding live stream scope.
5. ALP-2031, or merge ALP-2033 into it and do both here.
6. ALP-2032.

ALP-2033 can run anytime after the row builder shape is stable.

## Dependencies

- `@tanstack/react-query`: fetch and live stream cache integration.
- `@tanstack/react-virtual`: virtual row mount behavior in `ExchangeList`.
- Vitest and Testing Library: projection and component tests.
- Pydantic backend models: source of the wire shape mirrored by `www/src/types.ts`.

## Relevance to Helioy

Manicure is the Helioy operator view for multi agent traffic. These issues protect causal readability for Claude Agent and Codex `spawn_agent` flows, especially nested subagent execution and collapsed subtree behavior.

## Open Questions

- Should sibling spawn chronology be documented in display direction, where higher `track_spawn_order` currently appears above lower order in newest first list rendering?
- Should ALP-2039 be split by role, or kept as a full stack contract change?
- Should ALP-2031 also diagnose missing parent tracks, or stay limited to missing anchor exchanges?
