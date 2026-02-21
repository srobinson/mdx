---
title: ALP-2066 Lazy Turn Content Review for Manicure
type: research
tags: [manicure, alp-2066, code-review, lazy-turn-content]
summary: Read-only review of d7f45cb found the lazy turn-content branch coherent with one low severity stop_reason fallback deviation.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

Reviewed `/tmp/manicure-alp-2066-review` at `d7f45cb` against base `f21b0c4` for ALP-2066 and ALP-2076 verification coherence. The branch is clean, implements the lazy turn-content endpoint and frontend rendering path, removes legacy `user_prompt_preview` from API and frontend source, and includes verification evidence in the ALP-2076 commit message plus the expected Playwright snapshot artifact.

## Project Metadata

- Target: `/tmp/manicure-alp-2066-review`
- HEAD: `d7f45cb80b4ec31b4a3b6b114c521532b5246266`
- Base: `f21b0c4`
- Worktree state: clean detached worktree
- Stack: Python 3.13 / FastAPI / Pydantic v2, React 18 / TypeScript / TanStack Query / Vitest / Playwright

## Architecture

- Backend adds `GET /api/exchanges/{exchange_id}/turn-content` in `api/src/manicure/api/v1/exchanges.py:198-225`.
- Backend content extraction lives in `api/src/manicure/exchange_stats.py:25-75`.
- `IndexEntry` no longer includes `user_prompt_preview` in `api/src/manicure/storage/base.py:110-129`.
- Frontend adds `fetchTurnContent` in `www/src/api.ts:54-60`, `TurnContent` in `www/src/types.ts:69-73`, and `useTurnContent` in `www/src/hooks/useTurnContent.ts:5-11`.
- `ExchangeTurnCard` renders settled rows through lazy two-column content in `www/src/components/ExchangeTurnCard.tsx:181-195` and `:285-315`.
- Stream updates invalidate or remove `turn-content` queries in `www/src/hooks/useExchangeStream.ts:252-253` and `:276-277`.

## Detailed Findings

### Clean branch state

Command evidence:

```text
PWD=/private/tmp/manicure-alp-2066-review
BRANCH=HEAD
HEAD=d7f45cb
STATUS
```

`git status --short` returned no output. `git worktree list --porcelain` showed `/private/tmp/manicure-alp-2066-review` at `d7f45cb80b4ec31b4a3b6b114c521532b5246266` detached.

### Diff scope

`git diff --name-status f21b0c4..HEAD` reported 20 changed files: backend endpoint and extractor changes, frontend API/hook/card changes, tests, and one updated Playwright snapshot.

### Test and artifact coverage

Relevant files exist:

- `api/src/manicure/api/v1/test_exchanges_turn_content.py`
- `api/src/manicure/test_exchange_stats.py`
- `www/src/api.test.ts`
- `www/src/hooks/useTurnContent.test.tsx`
- `www/src/hooks/useExchangeStream.validation.test.tsx`
- `www/src/components/ExchangeList.test.tsx`
- `www/src/components/ExchangePreview.test.tsx`
- `www/tests/visual/exchange-list-anchored.spec.ts-snapshots/exchange-list-anchored-subagent-visual-darwin.png`

The ALP-2076 commit message states that `just check && just build && just test`, `npx playwright test`, manual smoke, index payload inspection, and cache clearing were completed. No independent full test rerun was performed during review because the task requested only fast read-only commands.

### Legacy preview removal

Command:

```bash
git grep -n -E 'user_prompt_preview|extract_user_prompt_preview|_PREVIEW_MAX_CHARS' -- api www
```

Result: no output. This supports the “no legacy preview in index payload” acceptance criterion. `~/.manicure/exchanges` was also absent during review.

### Low severity gap

`ExchangeTurnCard` drops `stopReason` when `response_text` is null. Current code in `www/src/components/ExchangeTurnCard.tsx:172-178` returns `—` for missing text and only renders `stopReason` through `ExchangePreview` when text exists. The plan expected `— · {stopReason}` for settled turns with no response text at `DOCS/superpowers/plans/2026-04-28-lazy-turn-content.md:699-707`.

Impact: low. Main lazy content, legacy field removal, tests, and verification artifacts remain coherent. This only affects an edge display state where an exchange has a response stop reason but no extractable response text.

## Dependencies

- `@tanstack/react-query` powers lazy turn-content fetching and cache invalidation.
- FastAPI and Pydantic provide the new endpoint and typed response model.
- Vitest and Playwright cover frontend behavior and visual snapshot drift.
- Pytest and mypy are the backend verification gates recorded in the ALP-2076 commit.

## Relevance to Helioy

The branch removes denormalized preview data from the exchange index and moves full prompt and response rendering behind a lazy endpoint. This keeps the list payload smaller and aligns Manicure with Helioy’s preference for explicit structured artifacts rather than lossy cached summaries.

## Open Questions

- Should the plan’s fallback `stopReason` display be treated as required before parent closure, or acceptable as a low severity follow-up?
- If future reviews require independent verification, capture command output logs as committed or attached artifacts rather than relying on commit message evidence.
