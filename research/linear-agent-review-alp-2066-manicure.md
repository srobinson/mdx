---
title: Linear Agent Review for ALP-2066 Lazy Turn Content
type: research
tags: [linear, agent-review, manicure, turn-content]
summary: Reviewed ALP-2066 sub-issues against current manicure code and patched stale Linear descriptions.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

Ran the Agent Review Step for ALP-2066, covering ALP-2068 through ALP-2076. The plan is structurally sound, but several sub-issue descriptions had stale implementation guidance around React Query tests, card height counts, preview removal call sites, Playwright snapshot paths, and local smoke commands. Linear has been updated in place for the affected issues.

## Project Metadata

- Project: manicure
- Repository signal: `.fmm.db` present
- Layout: `api/` Python FastAPI backend, `www/` React TypeScript frontend
- Backend: Python >=3.12, FastAPI, Pydantic v2, uv, pytest, mypy
- Frontend: React 19, TypeScript, Vite 8, TanStack React Query v5, pnpm, Vitest, Playwright
- API mount: `/api`, confirmed in `api/src/manicure/main.py` and `api/src/manicure/api/v1/router.py`

## Architecture

ALP-2066 replaces the denormalized `IndexEntry.user_prompt_preview` path with lazy per-card content retrieval.

Relevant current structure:

- Backend exchange helpers: `api/src/manicure/exchange_stats.py`
- Backend exchange routes: `api/src/manicure/api/v1/exchanges.py`
- Backend storage model: `api/src/manicure/storage/base.py`
- Claude persistence call sites: `api/src/manicure/exchange_recorder.py`
- Codex persistence call sites: `api/src/manicure/codex/exchange.py`
- Frontend API client: `www/src/api.ts`
- Frontend types: `www/src/types.ts`
- Exchange stream hook: `www/src/hooks/useExchangeStream.ts`
- Exchange list and card: `www/src/components/ExchangeList.tsx`, `www/src/components/ExchangeTurnCard.tsx`
- Preview rendering: `www/src/components/ExchangePreview.tsx`

## Key Patterns

- Current frontend API functions use `/api/exchanges/...`, not `/api/v1/...`.
- Current React Query hooks use object form `useQuery` and `Number.POSITIVE_INFINITY` for infinite stale time.
- Hook render tests already use `renderHook` with `QueryClientProvider` in `www/src/hooks/useExchangeStream.testSupport.tsx`.
- Playwright snapshots live under `www/tests/visual/*.spec.ts-snapshots/*`, not a shared `__snapshots__` folder.
- Root `just dev` requires a client argument. For Anthropic smoke use `just dev claude`.

## Detailed Findings

### Updated in Linear

- ALP-2068: added missing `import json` guidance for `extract_response_text`.
- ALP-2072: replaced stale “first renderHook pattern” guidance with the existing `useExchangeStream.testSupport.tsx` pattern, switched test path to `.test.tsx` when JSX is used, and specified `Number.POSITIVE_INFINITY`.
- ALP-2073: added explicit test guidance for invalidating `["turn-content", id]` on exchange updates and exact removal on deletes.
- ALP-2074: corrected `min-h-[196px]` guidance. Current code has four lines but five class tokens, with one line containing two tokens. Added `line-clamp-5` and updated both JSON line count assertions in `ExchangePreview.test.tsx`.
- ALP-2075: corrected `api/src/manicure/codex/exchange.py` from four preview kwargs to three, and added remaining frontend legacy references in `ExchangeTurnCard.tsx` and `ExchangeList.test.tsx`.
- ALP-2076: corrected frontend typecheck to `pnpm typecheck` or `npx tsc -b --noEmit`, snapshot path layout, `just dev claude`, Anthropic proxy port `8787`, and API port `8788`.

### No update needed

- ALP-2069: current. `extract_user_prompt_preview` and `_flatten_user_text` are still present and valid in `api/src/manicure/exchange_stats.py`.
- ALP-2070: current. `api/src/manicure/api/v1/test_exchanges_turn_content.py` is a create path, not a stale existing path.
- ALP-2071: current. `www/src/api.ts` and `www/src/types.ts` match the described client/type addition pattern.

### Verified references

- `IndexEntry.user_prompt_preview` exists in backend and frontend before implementation: `api/src/manicure/storage/base.py`, `www/src/types.ts`.
- Existing preview extractor and cap exist: `api/src/manicure/exchange_stats.py`.
- Existing backend preview call sites are in `api/src/manicure/exchange_recorder.py` and `api/src/manicure/codex/exchange.py`.
- Existing frontend preview rendering is in `www/src/components/ExchangeTurnCard.tsx`.
- Existing stream invalidation points are in `www/src/hooks/useExchangeStream.ts`.
- Current card height is 196 in `www/src/components/ExchangeList.tsx` and `www/src/components/ExchangeTurnCard.tsx`.

## Dependencies

Critical dependencies for this work:

- FastAPI and Pydantic for the new `GET /api/exchanges/{id}/turn-content` endpoint and response model.
- TanStack React Query for `fetchTurnContent`, `useTurnContent`, cache invalidation, and delete cleanup.
- Vitest and Testing Library for hook/component tests.
- Playwright visual project for Exchange list snapshot updates.

## Relevance to Helioy

This review keeps Nancy-ready Linear work accurate before autonomous execution. The corrections reduce worker friction by aligning issue descriptions with current manicure structure, avoiding stale line references, and making verification commands executable in the current repo.

## Open Questions

- None blocking. ALP-2070 test file is intentionally new.
- ALP-2076 should still be treated as the final integration gate after all implementation subtasks land.
