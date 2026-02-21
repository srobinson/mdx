---
title: Manicure frontend turn content plumbing review
type: research
tags: [manicure, frontend, code-review, alp-2066, react-query]
summary: Runtime frontend plumbing for lazy turn content meets ALP-2066 acceptance, with a low severity direct test coverage gap for useTurnContent query key and stale time.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

Reviewed `/tmp/manicure-alp-2066-review` at `d7f45cb` against base `f21b0c4` for ALP-2071, ALP-2072, and ALP-2073 frontend data plumbing. Runtime code meets the requested API, hook, and stream invalidation behavior. One low severity acceptance proof gap remains: the hook tests do not directly assert the query key or infinite stale time.

## Project Metadata

- Project: Manicure frontend
- Path reviewed: `/tmp/manicure-alp-2066-review/www`
- Base: `f21b0c4`
- Head: `d7f45cb`
- Stack: React, TypeScript, TanStack Query, Vitest
- fmm status: fmm MCP was tried first, but the detached worktree has no `.fmm.db`; direct read-only inspection was used after `fmm validate` reported no database.

## Detailed Findings

### Runtime acceptance met

- `TurnContent` exists in `www/src/types.ts:69` with `user_text`, `response_text`, and `stop_reason` fields at `www/src/types.ts:70-72`.
- `fetchTurnContent` calls `/api/exchanges/${encodeURIComponent(id)}/turn-content` at `www/src/api.ts:54-55`, throws on non-OK at `www/src/api.ts:56-58`, and returns `TurnContent` at `www/src/api.ts:59`.
- `useTurnContent` uses `queryKey: ["turn-content", id]` at `www/src/hooks/useTurnContent.ts:7`, `enabled: id.length > 0` at `www/src/hooks/useTurnContent.ts:9`, and `staleTime: Number.POSITIVE_INFINITY` at `www/src/hooks/useTurnContent.ts:10`.
- `useExchangeStream` invalidates `['turn-content', entry.id]` on exchange update at `www/src/hooks/useExchangeStream.ts:253` and removes exact `['turn-content', data.id]` on delete at `www/src/hooks/useExchangeStream.ts:277`.

### Low severity test coverage gap

The hook tests cover successful fetch and disabled empty id behavior at `www/src/hooks/useTurnContent.test.tsx:11-45`, but do not directly assert the TanStack Query key or `staleTime`. This impacts the acceptance clause that tests cover the ALP-2072 query key and stale time requirements, not the observed runtime behavior.

## Verification

Ran from `/tmp/manicure-alp-2066-review/www`:

```bash
pnpm test -- src/api.test.ts src/hooks/useTurnContent.test.tsx src/hooks/useExchangeStream.validation.test.tsx
```

Vitest reported 37 test files passed and 331 tests passed. `git status --short` remained clean after verification.

## Ship Readiness

Frontend plumbing is runtime ready. If acceptance requires direct tests for every hook option, add assertions for the `['turn-content', id]` cache key and infinite stale time before final closure.
