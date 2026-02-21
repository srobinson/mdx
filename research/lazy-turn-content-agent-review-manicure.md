---
title: Lazy Turn Content Agent Review for Manicure
type: research
tags: [manicure, linear, code-review, frontend, backend, react-query]
summary: Agent review of ALP-2066 found the lazy turn-content feature ready with two low severity caveats.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

ALP-2066 landed on branch `nancy/ALP-2066` at `d7f45cb`, reviewed against base `f21b0c4` in `/tmp/manicure-alp-2066-review`. The implementation satisfies the core architecture: turn content is lazy fetched per card, `user_prompt_preview` is removed from the index model and call sites, and the Exchange card renders side by side request and response columns.

No blocking findings were found. Two low severity caveats remain: a missing stop reason fallback when `response_text` is null, and missing direct test assertions for `useTurnContent` query options despite correct runtime code.

## Project Metadata

- Project: `manicure`
- Repo area: FastAPI backend under `api/`, React frontend under `www/`
- Backend: Python 3.12 plus FastAPI, Pydantic, uv, pytest, mypy
- Frontend: React 19, TypeScript, TanStack Query, pnpm 10.8.1, Vitest, Playwright
- Build and test entry points: root `justfile`, `api/pyproject.toml`, `www/package.json`
- fmm status: top level checkout has `.fmm.db`, but the detached review worktree did not. fmm returned no indexed files for the review target, so review fell back to targeted read only shell inspection after attempting fmm first.

## Architecture

The lazy path centers on a new backend endpoint and a small frontend query boundary.

- Backend extractors live in `api/src/manicure/exchange_stats.py`.
  - `extract_user_prompt_text` returns uncapped last user text from request IR.
  - `extract_response_text` returns assistant text from response IR, preferring text blocks, then tool input JSON, then thinking XML.
- Endpoint lives in `api/src/manicure/api/v1/exchanges.py`.
  - `TurnContentResponse` exposes `user_text`, `response_text`, and `stop_reason`.
  - `GET /api/exchanges/{id}/turn-content` reads stored exchange artifacts and derives text from parsed IRs.
- Frontend API and type boundary lives in `www/src/api.ts` and `www/src/types.ts`.
  - `TurnContent` mirrors the endpoint shape.
  - `fetchTurnContent` fetches `/api/exchanges/${encodeURIComponent(id)}/turn-content`.
- React Query hook lives in `www/src/hooks/useTurnContent.ts`.
  - Query key: `['turn-content', id]`.
  - Disabled for empty ids.
  - Infinite stale time with stream invalidation for coherence.
- Card render lives in `www/src/components/ExchangeTurnCard.tsx`.
  - Settled rows call `useTurnContent` through `SettledTurnContentPreview`.
  - The middle row is a two column grid: user text left, response text right.
  - Pending rows keep token activity visuals and skip the lazy content hook.

## Key Patterns

- Keep list index payloads slim. Rich text now stays in artifacts and is loaded per visible card instead of denormalized into every `IndexEntry`.
- Preserve stream driven cache coherence. `useExchangeStream` invalidates `['turn-content', id]` on exchange updates and removes it on deletes.
- Use narrow extraction helpers rather than leaking IR shape to React. The frontend receives display text and can reuse existing `ExchangePreview` classification.
- Keep virtualized row dimensions explicit. `ExchangeList` row height and card `min-h` tokens were both moved to 250px.

## Detailed Findings

### Backend acceptance

No backend blockers.

- `api/src/manicure/exchange_stats.py:25-33`: `extract_user_prompt_text` is present, uncapped, strips outer whitespace, and returns `None` for empty text.
- `api/src/manicure/exchange_stats.py:57-75`: `extract_response_text` joins non empty text blocks, falls back to `json.dumps(block.input)` for tool use, then falls back to `<thinking>...</thinking>`.
- `api/src/manicure/api/v1/exchanges.py:198-225`: `TurnContentResponse` and `get_turn_content` implement the endpoint shape.
- `api/src/manicure/api/v1/exchanges.py:209-212`: missing exchange artifacts are converted to `NotFoundError`.
- `api/src/manicure/api/v1/exchanges.py:214-225`: in flight exchanges return null response fields.
- `api/src/manicure/storage/base.py:110-129`: `IndexEntry` no longer contains `user_prompt_preview`.
- Source grep for `user_prompt_preview|extract_user_prompt_preview|_PREVIEW_MAX_CHARS` under `api` and `www` returned no source matches.

### Frontend data plumbing

Runtime plumbing is correct.

- `www/src/types.ts:69-73`: `TurnContent` has `user_text`, `response_text`, and `stop_reason`.
- `www/src/api.ts:54-59`: `fetchTurnContent` encodes ids, calls the `/api` route, and throws on non OK responses.
- `www/src/hooks/useTurnContent.ts:5-11`: hook uses the accepted query key, fetcher, empty id disabling, and infinite stale time.
- `www/src/hooks/useExchangeStream.ts:252-253`: exchange update invalidates both detail and turn content.
- `www/src/hooks/useExchangeStream.ts:276-277`: delete removes both detail and turn content queries with exact matching.

Low caveat: `www/src/hooks/useTurnContent.test.tsx:11-45` covers fetch and empty id disabling, but does not directly assert `queryKey: ['turn-content', id]` or `staleTime: Number.POSITIVE_INFINITY`.

### UI and visual acceptance

No UI blockers.

- `www/src/components/ExchangeTurnCard.tsx:181-195`: `SettledTurnContentPreview` renders a two column grid from lazy query data.
- `www/src/components/ExchangeTurnCard.tsx:185-193`: user text is left, response text is right, and `stop_reason` is passed to the response column when response text exists.
- `www/src/components/ExchangeTurnCard.tsx:172-178`: loading renders `…`; missing text falls back to `—`.
- `www/src/components/ExchangeTurnCard.tsx:233-254`: card min height tokens are 250px and grid rows are `58px_140px_48px`.
- `www/src/components/ExchangeList.tsx:24-25`: virtual exchange row height is 250.
- `www/src/components/ExchangePreview.tsx:17`, `:76`, `:88`: preview max lines, mono cap, and line clamp are updated to 5 lines and 100px.
- `www/src/components/ExchangeList.test.tsx:574-619`: tests cover lazy prompt and response columns, loading placeholders, and pending cards skipping the hook.
- `www/tests/visual/exchange-list-anchored.spec.ts-snapshots/exchange-list-anchored-subagent-visual-darwin.png`: visual snapshot updated.

Low caveat: `TurnContentValue` currently ignores `stopReason` when `text` is null. If the endpoint returns `response_text: null` with `stop_reason: 'end_turn'`, the response column shows only `—` rather than `— · end_turn`. This is narrow and not a blocker for the main happy path.

## Verification

Reviewer executed targeted checks during review:

- `cd api && uv run pytest src/manicure/test_exchange_stats.py src/manicure/api/v1/test_exchanges_turn_content.py -q`
  - Result: 14 passed.
- `cd www && pnpm install --frozen-lockfile`
  - Installed dependencies only in detached review worktree.
- `cd www && pnpm typecheck`
  - Result: passed.
- `cd www && pnpm exec vitest run src/api.test.ts src/hooks/useTurnContent.test.tsx src/hooks/useExchangeStream.validation.test.tsx src/components/ExchangePreview.test.tsx src/components/ExchangeList.test.tsx`
  - Result: 5 files passed, 49 tests passed.

The landed verification commit `d7f45cb` also records prior full verification: `just check && just build && just test`, `npx playwright test`, snapshot acceptance, manual smoke, index payload check, and clearing `~/.manicure/exchanges`.

## Dependencies

Critical dependencies touched by this work:

- FastAPI and Pydantic for endpoint and response model.
- TanStack Query for lazy card query and cache invalidation.
- React and TypeScript for card render and types.
- Vitest and Testing Library for hook and component tests.
- Playwright for visual snapshot coverage.

## Relevance to Helioy

This is a clean Helioy pattern for slimming high cardinality index payloads: keep index rows small, lazy fetch rich per item content from canonical artifacts, and rely on stream invalidation for freshness. The same pattern applies to other inspectors that need full artifact detail without making the main list cold start expensive.

## Open Questions

- Should `TurnContentValue` display `stopReason` alongside `—` when response text is null but stop reason exists?
- Should `useTurnContent.test.tsx` directly assert the query key and stale time, or is runtime evidence plus stream invalidation coverage sufficient?
