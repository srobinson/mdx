---
title: Lazy Turn Content Backend Review for Manicure ALP-2066
type: research
tags: [manicure, backend, code-review, alp-2066, fastapi]
summary: Backend acceptance review for ALP-2066 at d7f45cb found no blocking issues.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

Reviewed the landed ALP-2066 backend branch in `/tmp/manicure-alp-2066-review` at `d7f45cb` against base `f21b0c4`. The backend acceptance scope for ALP-2068, ALP-2069, ALP-2070, and ALP-2075 is satisfied with no blocking findings.

## Project Metadata

- Language: Python 3.13
- Backend framework: FastAPI, Pydantic v2
- Worktree: `/tmp/manicure-alp-2066-review`
- Reviewed commit: `d7f45cb`
- Base commit: `f21b0c4`
- fmm status: unavailable for the detached worktree. `.fmm.db` is missing and `fmm_list_files` over the absolute worktree path returned 0 files, so inspection used targeted shell reads and ripgrep fallback.

## Architecture

The change replaces the denormalized exchange list preview with lazy content extraction:

- `api/src/manicure/exchange_stats.py` owns extractor helpers.
- `api/src/manicure/api/v1/exchanges.py` exposes `GET /api/exchanges/{id}/turn-content`.
- `api/src/manicure/storage/base.py` defines the `IndexEntry` schema without preview content.
- Exchange writers in `exchange_recorder.py` and `codex/exchange.py` now construct `IndexEntry` without `user_prompt_preview`.

## Detailed Findings

No blocking backend findings.

Acceptance evidence:

- ALP-2068: `extract_response_text` exists at `api/src/manicure/exchange_stats.py:57-75`. It joins text blocks, falls back to first tool input JSON, then falls back to non-empty thinking text wrapped in `<thinking>`.
- ALP-2069: `extract_user_prompt_text` exists at `api/src/manicure/exchange_stats.py:25-33`. It reads the last user message and returns uncapped stripped text or `None`.
- ALP-2070: `TurnContentResponse` and `GET /{exchange_id}/turn-content` exist at `api/src/manicure/api/v1/exchanges.py:198-225`. The route returns `user_text`, `response_text`, and `stop_reason`, maps missing artifacts to `NotFoundError`, and returns `response_text=None` plus `stop_reason=None` when `response_ir` is absent.
- ALP-2075: `IndexEntry` has no `user_prompt_preview` field at `api/src/manicure/storage/base.py:110-128`.
- ALP-2075: `exchange_recorder.py` imports no preview extractor at `api/src/manicure/exchange_recorder.py:13-18`, and HTTP `IndexEntry` construction omits preview kwargs at `api/src/manicure/exchange_recorder.py:239-251` and `304-315`.
- ALP-2075: `codex/exchange.py` imports no preview extractor at `api/src/manicure/codex/exchange.py:33-37`, and Codex `IndexEntry` construction omits preview kwargs at `api/src/manicure/codex/exchange.py:103-119`, `241-258`, and `530-539`.
- Production search across `api` and `www` for `user_prompt_preview`, `extract_user_prompt_preview`, and `_PREVIEW_MAX_CHARS` returned no results.

Verification run:

```bash
cd /tmp/manicure-alp-2066-review/api
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  src/manicure/test_exchange_stats.py \
  src/manicure/api/v1/test_exchanges_turn_content.py -q
```

Result: 14 passed.

## Dependencies

- FastAPI routing and dependency injection provide the endpoint surface.
- Pydantic models define response and storage contracts.
- Existing storage `read_exchange()` provides parsed IR artifacts for lazy extraction.

## Relevance to Helioy

This pattern keeps list index rows small and moves large rendered request and response content behind a lazy endpoint. It is a useful approach for other Helioy UI surfaces that need rich detail panes without denormalizing large text into primary indexes.

## Open Questions

None for the stated backend acceptance scope.
