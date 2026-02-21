---
title: Manicure Exchange API Quality Fixes
type: sessions
tags: [backend, manicure, api, quality]
summary: Addressed verified exchange API quality findings around list error typing and lazy recount lock lifetime.
status: active
source: backend-engineer
confidence: high
created: 2026-04-25
updated: 2026-04-25
---

## Summary

Verified the reported code quality findings against current head `cc823e9`. Addressed the valid items and left token persist suppression unchanged by request.

Implemented changes:

- `list_exchanges()` now raises `HTTPException(500)` from the caught storage exception instead of returning `JSONResponse` from a handler typed as `list[IndexEntry]`.
- Removed the `# type: ignore[return-value]` escape from `api/src/manicure/api/v1/exchanges.py`.
- Replaced the strong per-exchange lazy recount lock dict with `WeakValueDictionary[str, asyncio.Lock]`, so locks are retained while in use and released afterward.
- Added `test_lazy_recount_lock_is_released_after_request` to guard against lock accumulation.

## API Contract

No response shape changed for list failures. `/api/exchanges` still returns HTTP 500 with `{"detail": "Failed to read exchange index"}` when storage index reads fail.

No change to `/api/exchanges/{exchange_id}/pipeline_tokens` token persist suppression. Computed token counts are still returned even if cache persistence fails.

## Database Changes

No database or storage schema changes.

## Security Considerations

The list endpoint now uses FastAPI exception handling instead of returning a raw response from a typed route, preserving clearer API boundary semantics and exception chaining.

## Performance Notes

The lazy recount lock map is now bounded by live references. Concurrent recounts for the same exchange still share the same lock while requests are in flight, and completed recounts no longer leave permanent lock entries.

Verification:

- RED verified first: the new lock release regression failed with the strong dict because `ex-pipe` remained in `_compute_locks` after request completion.
- Targeted checks passed: lock release regression, concurrent caller lock sharing, list storage failure response, and no `type: ignore[return-value]` grep.
- Full backend verification passed: `ruff format --check`, `ruff check`, `mypy`, and `pytest` with 708 tests.

## Open Items

Sidecar read logging was verified to already use `exc_info=True`, so no change was made.

The pipeline token persist failure behavior remains intentional and unchanged per user request.
