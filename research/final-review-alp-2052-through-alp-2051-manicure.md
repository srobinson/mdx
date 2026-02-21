---
title: Final review for ALP-2052 through ALP-2051 in Manicure
type: research
tags: [manicure, alp-2019, exchange-list, codex, frontend, review]
summary: Final review found the ALP-2052 through ALP-2051 commits satisfy their stated acceptance criteria, with focused tests and visual coverage passing.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

The ALP-2052, ALP-2049, ALP-2050, and ALP-2051 commits are clean on review. They preserve decomposed coverage, wire paused subagent stubs into production ExchangeList state, make orphan anchor behavior operator visible, and add visual coverage for anchored subagent rows.

No blocking issues were found.

## Project Metadata

- Project: Manicure
- Branch: `nancy/ALP-2019`
- Review range: `5f960a0..ffbb0ed`
- Frontend: React 19, TypeScript, Vite, TanStack Query, TanStack Virtual, Zustand, Vitest, Playwright
- Backend: Python 3.13 in local verification, FastAPI, Pydantic, mitmproxy, pytest, uv
- fmm: `.fmm.db` is present at repo root, and fmm indexed 288 files with 54,626 LOC.

## Architecture

### ALP-2049 pending subagent stubs

Paused subagent track metadata now flows from backend pause state into the frontend track tree.

- Backend pause state carries `spawn_anchor` on `PausedFlow` in `api/src/manicure/breakpoint.py:25` and `api/src/manicure/breakpoint.py:91`.
- Pause SSE payloads include nested `spawn_anchor` from `_flow_track_fields` and `_paused_event_payload` in `api/src/manicure/pause_session.py:111` and `api/src/manicure/pause_session.py:154`.
- Refresh hydration includes `spawn_anchor` through `PausedFlowDetail` in `api/src/manicure/api/v1/breakpoint_routes.py`.
- Frontend SSE parsing stores `spawn_anchor` on `PausedFlow` in `www/src/hooks/useExchangeStream.ts:180`.
- `App` derives a production `ExchangeTrackStub` from `pausedFlow` in `www/src/app.tsx:82`.
- `useExchanges` accepts stubs and merges them into `buildExchangeTrackTree` in `www/src/hooks/useExchanges.ts:59` and `www/src/hooks/useExchanges.ts:167`.

This satisfies the requirement that pending child track headers appear before the first child exchange when spawn metadata is known.

### ALP-2050 orphan anchor visibility

The chosen product behavior is visible but low noise.

- `projectTrack` already identifies child tracks whose `track_spawn_exchange_id` is outside the fetched parent exchange window and carries `OrphanAnchorMeta` forward in `www/src/components/exchangeListRows.ts:32`.
- `ExchangeList` passes `row.meta` into `TrackHeader` in `www/src/components/ExchangeList.tsx:134`.
- `TrackHeader` renders `anchor outside view` with a title containing the missing anchor id in `www/src/components/TrackHeader.tsx:39`.

This keeps the existing diagnostic console warning and adds operator visible state only on the affected track header.

### ALP-2051 visual coverage

Visual fixtures now include a parent exchange, spawned child track, and nested `spawn_anchor` data.

- `mockAnchoredExchanges` is defined in `www/tests/visual/fixtures/exchanges.ts:140`.
- Fixture validation asserts required anchored fields in `www/src/visualFixtures.test.ts`.
- Playwright visual coverage verifies child track placement between post and spawn parent rows in `www/tests/visual/exchange-list-anchored.spec.ts`.
- Snapshot was added at `www/tests/visual/exchange-list-anchored.spec.ts-snapshots/exchange-list-anchored-subagent-visual-darwin.png`.

### ALP-2052 coverage audit

The branch includes `DOCS/ALP-2019-coverage-audit.md`, which documents the decomposition audit baseline, scopes checked, retained assertions, and the one restored ExchangeList row ordering gap. The restored row order assertions live in `www/src/components/ExchangeList.ordering.test.tsx`.

## Key Patterns

- Backend pause metadata is single source of truth. The frontend does not infer pending subagent anchors from labels or timing.
- Stubs are merged before exchanges in `buildExchangeTrackTree`, then concrete exchanges upgrade pending tracks from `pending` to `live`.
- Anchor adoption only overwrites non null nested fields, which prevents stale null data from erasing known anchor metadata.
- Orphan anchors are projected as row metadata rather than mutating track shape, keeping display concerns local to row projection and `TrackHeader`.

## Detailed Findings

### Acceptance criteria review

- ALP-2052: Satisfied. The audit doc exists, no intentional high value coverage removals are claimed, and the restored row order assertions cover the documented gap.
- ALP-2049: Satisfied. The pending stub path is wired through production `App` state, not only direct `ExchangeList` props.
- ALP-2050: Satisfied. Product behavior is explicit and visible via a small track header label for orphan anchors.
- ALP-2051: Satisfied. Anchored visual fixtures and a Playwright visual spec are present and verified.

### No blockers found

The reviewed code is internally consistent across backend payload generation, frontend parsing, state projection, row projection, and tests. No target code changes were made during review.

## Verification

Commands run from `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`:

```bash
cd api && uv run pytest src/manicure/api/v1/test_breakpoint.py src/manicure/test_addon_phases.py -q
# 55 passed

cd api && uv run pytest src/manicure/test_track_manager_*.py src/manicure/codex/test_transport_turn_*.py src/manicure/codex/test_repair_*.py -q
# 36 passed

cd api && uv run ruff check src/manicure/api/v1/breakpoint_routes.py src/manicure/api/v1/test_breakpoint.py src/manicure/breakpoint.py src/manicure/pause_session.py src/manicure/test_addon_phases.py
# All checks passed

cd www && pnpm vitest run src/app.test.tsx src/components/ExchangeList.ordering.test.tsx src/hooks/useExchangeStream.pausedTokens.test.tsx src/visualFixtures.test.ts
# 4 files passed, 23 tests passed

cd www && pnpm vitest run src/components/editor/SamplingSection.*.test.tsx src/hooks/useExchangeStream.*.test.tsx src/components/ExchangeList*.test.tsx
# 12 files passed, 102 tests passed

cd www && pnpm typecheck
# passed

cd www && pnpm lint -- src/app.tsx src/app.test.tsx src/components/ExchangeList.tsx src/components/ExchangeList.ordering.test.tsx src/components/TrackHeader.tsx src/hooks/useExchangeStream.ts src/hooks/useExchangeStream.pausedTokens.test.tsx src/hooks/useExchanges.ts src/types.ts src/visualFixtures.test.ts tests/visual/exchange-list-anchored.spec.ts tests/visual/fixtures/exchanges.ts tests/visual/fixtures/setup.ts
# passed

cd www && pnpm playwright test --project=visual tests/visual/exchange-list-anchored.spec.ts
# 1 passed
```

Final `git status --short` was clean.

## Dependencies

- TanStack Query supplies exchange query cache and SSE driven updates.
- TanStack Virtual renders ExchangeList rows with fixed row height estimates.
- Zustand stores UI state including `pausedFlow`, `selectedId`, and collapsed track state.
- FastAPI and Pydantic carry paused flow detail payloads.
- mitmproxy provides the live flow state used to resolve track assignments.

## Relevance to Helioy

This work strengthens Manicure as an observable control plane for multi agent traffic. The important pattern for Helioy is explicit metadata propagation: spawn anchors are captured once, carried as structured state, and rendered without heuristic reconstruction in the UI.

## Open Questions

None for this review. If product direction changes later, the only likely follow up is visual treatment of orphan anchor labels under very narrow sidebars or unusually long agent names.
