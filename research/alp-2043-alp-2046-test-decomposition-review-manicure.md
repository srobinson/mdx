---
title: ALP-2043 and ALP-2046 Test Decomposition Review for Manicure
type: research
tags: [manicure, review, tests, frontend, backend, linear]
summary: ALP-2043 and ALP-2046 satisfy the requested test decompositions with no blocking regression found.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed ALP-2043 and ALP-2046 in `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`. Both issues are complete against the Linear acceptance criteria. The specified test commands pass.

## Project Metadata

- Repository: manicure worktree under Helioy.
- fmm: `.fmm.db` present. fmm reports 287 indexed files and 53,826 LOC across `api/` and `www/`.
- Frontend: React 19, TypeScript, Vite, Vitest, TanStack Query. Node >=20.19, pnpm 10.8.1.
- Backend: Python >=3.12, uv, pytest, FastAPI, mitmproxy.

## Architecture

### ALP-2043

`www/src/hooks/useExchangeStream.test.tsx` was removed and replaced by four themed suites plus support:

- `www/src/hooks/useExchangeStream.race.test.tsx`: forwarding race guard behavior.
- `www/src/hooks/useExchangeStream.validation.test.tsx`: SSE exchange validation and cache effects.
- `www/src/hooks/useExchangeStream.forwarding.test.tsx`: forwarding activity liveness.
- `www/src/hooks/useExchangeStream.pausedTokens.test.tsx`: pause and token follow up state.
- `www/src/hooks/useExchangeStream.testSupport.tsx`: EventSource mock, React Query wrapper, paused flow factory, SSE emitter.

fmm dependency graph shows the support module has four downstream test files and imports only React Query, Testing Library, React, Vitest, `uiStore`, and shared types.

### ALP-2046

`api/src/manicure/test_track_manager.py` was removed and split into provider focused suites plus support:

- `api/src/manicure/test_track_manager_anthropic.py`: Anthropic reference and fan out traces.
- `api/src/manicure/test_track_manager_codex.py`: Codex agent id and call id traces.
- `api/src/manicure/test_track_manager_core.py`: provider neutral core behavior.
- `api/src/manicure/test_track_manager_support.py`: constants and trace builders.
- `api/src/manicure/test_track_manager_lifecycle.py`: imports updated from support module.

fmm dependency graph shows the support module has four downstream test files.

## Detailed Findings

- ALP-2043 preserves the exact 26 `it(...)` test names from the deleted monolith. Verified by comparing `877f237^:www/src/hooks/useExchangeStream.test.tsx` against the replacement test files.
- ALP-2043 support ownership is centralized in `www/src/hooks/useExchangeStream.testSupport.tsx:15-35`, `:37-78`, `:80-84`, and `:86-96`.
- ALP-2043 behavior themes are readable and separated by file. The validation suite is still large at 356 LOC, but it is coherent for exchange validation and cache synchronization.
- ALP-2046 preserves the original 8 `test_*` names from the deleted monolith and adds 9 existing lifecycle tests via the glob. Verified by comparing `f393073^:api/src/manicure/test_track_manager.py` against split files.
- ALP-2046 lifecycle import was updated directly from `manicure.test_track_manager` to `manicure.test_track_manager_support` in `api/src/manicure/test_track_manager_lifecycle.py:5-13`.
- No runtime regression was found in the requested test commands.

## Dependencies

- Frontend tests depend on Vitest, React Testing Library, TanStack Query, Zustand store state.
- Backend tests depend on pytest and `manicure.ir` plus `manicure.track_manager` primitives.

## Relevance to Helioy

The split follows the Helioy preference for structural seams and focused suites. The support modules reduce shared fixture drift while keeping provider specific trace behavior readable.

## Open Questions

- Consider making `fireSSE` fail fast if the hook did not create an EventSource. Current optional chaining preserves old behavior but can hide a missing `renderHook` setup.
