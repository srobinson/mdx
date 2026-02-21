---
title: ALP-2040 through ALP-2047 completion review for Manicure
type: research
tags: [manicure, linear-review, testing, refactor, frontend, backend]
summary: ALP-2040, 2041, 2042, 2043, 2044, and 2046 are complete; ALP-2045 is functionally complete with visual verification unresolved; ALP-2047 is risky due duplicated row projection assertions.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed ALP-2040 through ALP-2047 in `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019` using four parallel explorer agents plus local verification. Six issues are complete. ALP-2045 is structurally correct but `pnpm --dir www test:visual` is not green locally. ALP-2047 passes tests but misses the DRY intent of the spec by duplicating row projection assertions in component tests.

## Project Metadata

- Project: Manicure, provider-neutral context control plane for Claude Code and Codex traffic.
- Worktree branch: `nancy/ALP-2019`.
- fmm status: `.fmm.db` present in the worktree.
- Backend: Python 3.12 plus, FastAPI, mitmproxy, pytest, uv, ruff, mypy.
- Frontend: React 19, Vite 8, TypeScript strict, Tailwind 4, Vitest, Playwright, Biome, pnpm 10.
- Topology from fmm: 290 indexed files, 55,897 LOC. `api/` has 179 files and 37,306 LOC. `www/` has 111 files and 18,591 LOC.

## Architecture

The reviewed issues are refactor and test decomposition tasks across the backend Codex transport and repair suites, backend track manager suites, frontend SamplingSection, frontend SSE hook tests, visual fixtures, and ExchangeList tests.

Key seams observed:

- SamplingSection now coordinates extracted hooks and row components.
- Codex transport turn tests are grouped by lifecycle behavior.
- Codex repair tests are grouped by artifact phase.
- useExchangeStream tests share EventSource and React Query setup.
- Track manager tests separate Anthropic, Codex, core, and lifecycle behavior.
- Visual fixtures are split by fixture family behind a stable barrel.
- ExchangeList tests are split, but ordering tests still duplicate projection layer checks.

## Key Patterns

- Good support module pattern: shared builders and fixtures have one owner, then focused suites import only what they need.
- Good frontend coordinator pattern: `SamplingSection` now composes hooks and rows instead of carrying all local state and markup.
- Risk pattern: component tests should not reassert exact pure projection output if a projection helper has its own direct tests.

## Detailed Findings

### ALP-2040: Decompose SamplingSection by override seams

Verdict: complete, low risk.

Evidence:

- `www/src/components/editor/SamplingSection.tsx:44-136` is now a 93 LOC coordinator.
- Sampling override behavior moved to `www/src/components/editor/useSamplingOverrides.ts:25-127`.
- Thinking, budget, display, and effort behavior moved to `www/src/components/editor/useThinkingOverrides.ts:28-182`.
- Row markup moved to `www/src/components/editor/SamplingRows.tsx:100-472`.
- Props contract remains stable in `SamplingSection.tsx:29-42`.

Quality notes:

- The requested behavior logic isolation happened before markup extraction.
- `SamplingRows.tsx` is 472 LOC, but mostly markup. Splitting by row can wait until it changes again.

### ALP-2041: Decompose Codex transport turn tests by lifecycle

Verdict: complete.

Evidence:

- Completion cases: `api/src/manicure/codex/test_transport_turn_completion.py`.
- Close and interrupted cases: `api/src/manicure/codex/test_transport_turn_close.py`.
- Derivation, tool result, and tool search cases: `api/src/manicure/codex/test_transport_turn_derivation.py`.
- Pause and stale state cases: `api/src/manicure/codex/test_transport_turn_pause.py`.
- The old `api/src/manicure/codex/test_transport_turns.py` monolith is absent.
- Agent AST preservation check found no missing, added, or changed function bodies versus the parent monolith.

### ALP-2042: Decompose SamplingSection tests by behavior family

Verdict: complete.

Evidence:

- Split files exist: `SamplingSection.render.test.tsx`, `SamplingSection.commits.test.tsx`, `SamplingSection.reset.test.tsx`, `SamplingSection.thinking.test.tsx`, and `SamplingSection.providerExtras.test.tsx`.
- Shared support lives at `www/src/components/editor/SamplingSection.testSupport.tsx:17-60`.
- The old monolith had 52 tests. The split suites preserve 52 tests.

Process note:

- `pnpm --dir www test -- SamplingSection.test.tsx` passes but the named file no longer exists, so Vitest runs the broader matching suite. Future issue text should use `SamplingSection`.

### ALP-2043: Decompose useExchangeStream tests by SSE behavior

Verdict: complete.

Evidence:

- Shared setup: `www/src/hooks/useExchangeStream.testSupport.tsx:15-96`.
- Race guard tests: `www/src/hooks/useExchangeStream.race.test.tsx:7-101`.
- Forwarding tests: `www/src/hooks/useExchangeStream.forwarding.test.tsx:7-50`.
- Paused token follow up tests: `www/src/hooks/useExchangeStream.pausedTokens.test.tsx:7-116`.
- Validation and cache behavior tests: `www/src/hooks/useExchangeStream.validation.test.tsx:8-356`.
- The original 26 `it(...)` cases are preserved by name.

Minor risk:

- `fireSSE` at `www/src/hooks/useExchangeStream.testSupport.tsx:80-84` silently no ops if no EventSource instance or handler exists. This preserves old behavior, but fail fast would make future tests safer.

### ALP-2044: Decompose Codex repair tests by artifact phase

Verdict: complete.

Evidence:

- Shared builders: `api/src/manicure/codex/test_repair_support.py:30-150`.
- Rebuild cases: `api/src/manicure/codex/test_repair_rebuild.py`.
- Migration cases: `api/src/manicure/codex/test_repair_migration.py`.
- Diagnostics cases: `api/src/manicure/codex/test_repair_diagnostics.py`.
- Safety cases: `api/src/manicure/codex/test_repair_safety.py`.
- The old `api/src/manicure/codex/test_repair.py` monolith is absent.
- Agent AST preservation check found no missing, added, or changed function bodies versus the parent monolith.

### ALP-2045: Decompose visual fixtures by fixture family

Verdict: functionally complete, verification unresolved.

Evidence:

- Barrel remains at `www/tests/visual/fixtures.ts:1-5`.
- Existing specs still import from the barrel:
  - `www/tests/visual/exchange-detail-header.spec.ts:2`.
  - `www/tests/visual/exchange-detail-timeline.spec.ts:2`.
  - `www/tests/visual/exchange-detail-transport.spec.ts:2-6`.
  - `www/tests/visual/paused-header.spec.ts:2`.
  - `www/tests/visual/top-bar.spec.ts:2`.
- Fixture ownership is clear:
  - Time: `www/tests/visual/fixtures/time.ts:1-7`.
  - Paused flow: `www/tests/visual/fixtures/pausedFlow.ts:1-43`.
  - Exchanges: `www/tests/visual/fixtures/exchanges.ts:1-130`.
  - Details: `www/tests/visual/fixtures/details.ts:1-404`.
  - Setup: `www/tests/visual/fixtures/setup.ts:1-114`.
- Guard test: `www/src/visualFixtures.test.ts:12-19`.

Verification concern:

- My local `pnpm --dir www test:visual` run started the Playwright web server, ran 12 tests, and failed 8 snapshot comparisons. The failed snapshots were `paused-*`, `exchange-detail-transport-*`, and `topbar-*`, with diff ratios around 0.02 to 0.06. This may be environment or stale snapshot related, but the requested final verification target is not green locally.

### ALP-2046: Decompose track manager tests by provider trace

Verdict: complete.

Evidence:

- Shared constants and trace builders: `api/src/manicure/test_track_manager_support.py:21-80`.
- Anthropic focused tests: `api/src/manicure/test_track_manager_anthropic.py:15-249`.
- Codex focused tests: `api/src/manicure/test_track_manager_codex.py:18-280`.
- Provider neutral tests: `api/src/manicure/test_track_manager_core.py:14-113`.
- Lifecycle imports updated to `manicure.test_track_manager_support` in `api/src/manicure/test_track_manager_lifecycle.py:5-13`.
- The old 8 monolith tests are preserved by name. The glob also includes 9 lifecycle tests.

### ALP-2047: Decompose ExchangeList tests by row behavior

Verdict: risky. Functional split exists and tests pass, but the DRY acceptance is not fully met.

Evidence of completion:

- Shared helper: `www/src/components/__test-utils__/exchangeList.ts:3-32`.
- Track tree tests: `www/src/components/ExchangeList.trackTree.test.tsx:7-273`.
- Ordering tests: `www/src/components/ExchangeList.ordering.test.tsx:6-424`.
- Remaining component tests: `www/src/components/ExchangeList.test.tsx:6-373`.

Risk:

- `ExchangeList.ordering.test.tsx` asserts exact rendered row order with `rowOrder()` at `www/src/components/ExchangeList.ordering.test.tsx:7-10`.
- Claude anchored ordering in `ExchangeList.ordering.test.tsx:12-65` duplicates `www/src/components/exchangeListRows.test.ts:23-87`.
- Codex anchored ordering in `ExchangeList.ordering.test.tsx:67-128` duplicates `www/src/components/exchangeListRows.test.ts:89-142`.
- Collapsed anchored child behavior in `ExchangeList.ordering.test.tsx:277-325` duplicates `www/src/components/exchangeListRows.test.ts:144-174`.

Recommended fix:

- Reduce `ExchangeList.ordering.test.tsx` to component integration checks such as visible rendering, selected state, click behavior, and collapse integration.
- Leave exact full row projection arrays to `exchangeListRows.test.ts`.

## Verification Commands

Passed:

- `pnpm --dir www test -- SamplingSection`: 33 files, 293 tests.
- `pnpm --dir www test -- SamplingSection.test.tsx`: 33 files, 293 tests.
- `pnpm --dir www test -- useExchangeStream ExchangeList visualFixtures`: 33 files, 293 tests.
- `pnpm --dir www typecheck`.
- `pnpm --dir www lint`.
- `uv run --project api pytest api/src/manicure/codex`: 96 passed.
- `uv run --project api pytest api/src/manicure/test_track_manager*.py`: 17 passed.
- `uv run --project api ruff check api/src/manicure/codex api/src/manicure/test_track_manager_*.py api/src/manicure/test_track_manager_support.py`.

Failed or unresolved:

- `pnpm --dir www test:visual`: 8 failed, 4 passed in my local run due snapshot diffs. A subagent run saw connection refused, which also leaves visual verification unresolved.

## Dependencies

Relevant dependencies for this review:

- Frontend: React, TanStack Query, Zustand, Vitest, Testing Library, Playwright, Biome, TypeScript.
- Backend: pytest, pytest asyncio, FastAPI, mitmproxy, Pydantic, uv, ruff.
- fmm was used for structural topology, file outlines, symbol reads, and impact checks.

## Relevance to Helioy

This work improves Manicure maintainability by moving large behavior suites and UI components toward smaller, owned seams. The strongest reusable pattern for Helioy is the support module plus focused suite split. The main caution is ALP-2047: when a pure projection helper has direct tests, component suites should verify integration behavior rather than repeat full projection tables.

## Open Questions

1. Are the local visual snapshots expected to pass on this machine without updating snapshots? Current local run says no.
2. Should ALP-2047 be sent back for a small DRY cleanup before marking accepted?
3. Should `fireSSE` become fail fast in a follow up to catch miswired EventSource tests earlier?
