# Manicure Backend API Review

**Date:** 2026-04-13
**Scope:** All files under `api/src/manicure/` (core, storage, adapters, routes, tests)
**Branch:** feat/ui-improvements (d88f8da)

## Summary

The manicure backend is a well structured FastAPI + mitmproxy system with clean separation between adapters, IR, overrides, and storage. The architecture is sound for its scope. The primary risks are concurrency: the breakpoint state machine, broadcast queue, and storage layer all use module level globals without synchronization. Secondary concerns involve incomplete error handling at API boundaries and significant test coverage gaps in integration paths.

## Architecture Overview

```
Client -> mitmproxy (ManicureAddon)
              |
              v
         ProviderAdapter (Anthropic)
              |
              v
         InternalRequest (IR) <-> OverrideStore (pipeline)
              |                         |
              v                         v
         BreakpointStateMachine    OverrideAudit
              |
              v
         DiskStorageBackend (JSONL index + per-exchange dirs)
              |
              v
         FastAPI Routes (exchanges, overrides, breakpoint, stream)
              |
              v
         SSE Broadcast -> Web UI
```

Key design decisions:
- Frozen Pydantic models for IR (immutability by default)
- Adapter pattern for provider abstraction (currently Anthropic only)
- Append only JSONL index with in memory cache for storage
- Module level singletons for breakpoint, broadcast, override store, and storage backend

## Strengths

- **IR model design**: Frozen Pydantic models with discriminated unions. Clean, type safe, serialization round trips verified by tests.
- **Adapter abstraction**: Minimal 4 method interface. AnthropicAdapter handles JSON + SSE, preserves unknown fields via `provider_extras` for forward compatibility.
- **Override pipeline**: Pure transform functions for each override type. Audit trail captures before/after with character deltas. Well tested (714 lines of tests).
- **Storage interface**: Clean ABC with 5 async methods. Easy to swap implementations. Disk backend uses append only index with in memory cache.
- **CLI diagnostics**: `doctor` command checks Python, mitmproxy, addon, web bundle, storage, and ports. Good operational tooling.
- **Test data quality**: Realistic Anthropic request fixtures, round trip adapter tests, SSE stream parsing tests.
- **REST conventions**: Consistent kebab case URLs, proper 204 on DELETE, 404 on missing resources, query param validation with Pydantic.

## Issues

### Critical

1. **breakpoint.py:36-37** - Global mutable dict `_paused` with no synchronization. Modified from both `addon.request()` and `addon.response()` async hooks. Race between `pause()` registering a flow and `release()`/`drop()` popping it.

2. **breakpoint.py:40-42** - Breakpoint mode not re-armed after pause. `armed_once` fires for the first request only, then reverts to `off`. Comment at line 64 says "re-arm for next request" but code does not match. Feature does not work as designed if user expects each request to pause.

3. **addon.py:363** - `exchange_id = flow.id` uses mitmproxy flow IDs which are not guaranteed unique across proxy restarts. Colliding IDs overwrite storage index entries.

4. **broadcast.py:29** - `contextlib.suppress(asyncio.QueueFull)` silently drops SSE events when a subscriber queue is full. No logging. Clients receive incomplete data with no indication of loss.

5. **stream.py:20-25** - SSE generator has no exception handling for non-TimeoutError exceptions. `CancelledError` on client disconnect crashes the generator without running cleanup. The `finally` block relies on garbage collection timing.

6. **exchanges.py:14-20** - `storage.read_index()` exceptions (file I/O, JSON parse) are not caught. Produces raw 500 instead of structured error response.

### Major

7. **storage/disk.py:100-101** - Exchange directory creation (`mkdir`) not protected by lock. Concurrent writes with the same exchange_id can interleave files in the same directory.

8. **storage/disk.py:103-124** - Writes 5 files sequentially with no atomicity. Process crash mid-write leaves partial exchange on disk. No write-to-temp + rename pattern.

9. **storage/__init__.py:28-29** - Global `_backend` singleton assigned without lock. Two concurrent requests hitting `get_storage()` before `init_storage()` can both create a `DiskStorageBackend`, one overwriting the other.

10. **addon.py:201-203** - Between `event.wait()` returning and `bp.get_paused().pop(flow.id)`, another coroutine can modify the paused dict. `pop()` may return `None`, losing user mutations.

11. **addon.py:360** - `curated_ir` fallback uses original `ir` when breakpoint handler did not run, but pipeline may have modified the request. Request/response artifact mismatch in storage.

12. **overrides.py:489-496** - Index adjustment for multiple sequential system_part_toggle overrides uses already adjusted indices from prior toggles, targeting wrong system parts.

13. **overrides.py:462** - `strip_thinking` removes message blocks, changing indices. Subsequent `message_text` overrides use stale block indices.

14. **overrides.py:267** - `truncate_tool_result` accepts any int including negative or zero. No validation that `max_chars > 0`.

15. **main.py:74** - CORS origins hardcoded to `localhost:3000` and `localhost:5173`. `allow_methods=["*"]` and `allow_headers=["*"]` are overly permissive. Should be configurable via settings.

16. **adapters/__init__.py:19-24** - `get_adapter()` returns `None` silently when no adapter matches. Callers must handle `None` explicitly. Crash on `adapter.inbound_request()` if no match.

17. **cli.py:306-309** - Sets `MANICURE_*` env vars in current process before `execvpe()`. Visible to other child processes. Should be isolated to the mitmdump subprocess environment.

18. **cli.py:228** - `upstream` parameter passed to mitmdump as `reverse:{upstream}` without URL validation. Malformed URLs produce cryptic mitmdump errors.

19. **stream.py:14-29** - No client disconnect detection. Server keeps connection open and sends keepalives indefinitely for disconnected clients.

20. **broadcast.py:17** - `asyncio.Queue()` defaults to unbounded (`maxsize=0`). A slow subscriber causes unbounded memory growth.

### Minor

21. **addon.py:93** - `raw.decode("utf-8", errors="replace")` silently replaces invalid bytes. Corrupted SSE payloads produce garbage statistics with no warning.

22. **addon.py:201** - No timeout on `await event.wait()` in breakpoint handler. If user never releases, request blocks indefinitely.

23. **storage/disk.py:172-179** - Directory lookup by 8-char suffix has collision probability ~1 in 4B. Returns first match from `iterdir()` on ambiguous match.

24. **config.py:33-35** - `@lru_cache` on `get_settings()` with no invalidation. Env var changes at runtime return stale settings.

25. **ir.py:99-114** - No min-length validation on `InternalRequest.messages`. Empty list passes validation but causes downstream failures.

26. **overrides.py:393-426** - DRY violation: 7 target parsing helpers follow identical pattern (check prefix, extract, parse, return None on failure).

27. **cli.py:553-558** - TOCTOU race in `_port_in_use()`. Port can be claimed between check and actual bind.

28. **cli.py:460** - `doctor` hardcodes ports 8787/8788 instead of reading configured ports from settings.

29. **exchanges.py:36-49** - Manual dict construction for response instead of Pydantic model. Inconsistent with overrides.py pattern.

30. **overrides.py:49-72** - `_compute_preview()` mutates `pf.curated_ir` and `pf.audit` in place. Side effects in a helper function.

## Test Coverage Analysis

**Well tested:**
- IR models: construction, immutability, serialization round trips (test_ir.py, 155 lines)
- Overrides: 9 override types, priority ordering, index shifting, audit aggregation (test_overrides.py, 714 lines)
- Adapter round trips: 6 realistic fixtures, thinking block regression, SSE parsing (test_anthropic.py, 339 lines)
- CLI commands: version, paths, doctor, start with mock exec (test_cli.py, 382 lines)
- Breakpoint state machine: arm/disarm, pause/release/drop (test_breakpoint.py, 149 lines)
- API routes: breakpoint, overrides, exchanges HTTP endpoints (test_breakpoint.py 282, test_overrides.py 292, test_exchanges.py 158)

**Critical gaps:**
- **No integration tests.** No test covers the full addon lifecycle: request -> parse -> override -> breakpoint -> response -> storage -> broadcast.
- **No concurrency tests.** Race conditions in breakpoint, broadcast, and storage are untested.
- **No stream endpoint tests.** `GET /stream` (SSE) has zero test coverage.
- **No error path tests.** Storage failures, malformed JSON, invalid adapter responses, disk full scenarios.
- **No adapter.matches() test.** The adapter selection logic is untested.
- **No main.py tests.** App creation, CORS, lifespan, static file serving.

**Moderate gaps:**
- Disk storage: no concurrent write tests, no corruption recovery tests, no large payload tests.
- Adapter: no malformed request JSON tests, no image/vision block tests, no cache_creation_input_tokens parsing tests.
- Exchange API: no pagination edge case tests, no filtering tests.

**Test quality observations:**
- Tests focus on behavior over implementation (good).
- `_make_ir()` factory duplicated across 4+ files. Should consolidate in conftest.py.
- test_broadcast.py uses string matching for JSON (fragile).
- test_addon_phases.py directly mutates `broadcast._subscribers` (encapsulation violation).

## Recommendations

### P0: Fix before next release

1. **Add asyncio.Lock to breakpoint state.** Protect `_paused` dict with a lock in `pause()`, `release()`, `drop()`, and `get_paused()`. This is the highest risk data race.

2. **Add bounded queue + overflow logging to broadcast.** Set `maxsize=1000` on subscriber queues. Log dropped events instead of silently suppressing.

3. **Make CORS configurable.** Move allowed origins to `Settings`. Explicitly list allowed methods and headers.

4. **Wrap storage exceptions in API layer.** Add try/except around `storage.read_index()` and `storage.read_exchange()` in exchanges.py. Return structured error responses.

5. **Add exception handling to SSE generator.** Catch `asyncio.CancelledError` and `Exception` in stream.py, ensure `unsubscribe()` runs in all paths.

### P1: Address in next sprint

6. **Atomic storage writes.** Write exchange files to a `.tmp` directory, then rename. Detect and clean up partial writes on startup.

7. **Guard storage singleton with lock.** Use `asyncio.Lock` in `get_storage()` for double checked initialization.

8. **Fix override index composition.** Track removal offsets in a single pass through `apply_overrides()` so subsequent overrides reference correct indices.

9. **Validate truncation and other override values.** Add `gt=0` constraint on truncation max_chars. Validate override targets at creation time, not application time.

10. **Add integration tests.** One test that exercises: adapter parse -> override pipeline -> breakpoint pause/release -> storage write -> exchange retrieval.

11. **Add stream endpoint tests.** Test SSE subscribe, receive events, disconnect, queue overflow behavior.

### P2: Improve when convenient

12. **Generate unique exchange IDs.** Use UUID4 instead of mitmproxy flow.id to avoid cross-session collisions.

13. **Isolate env vars.** Pass `MANICURE_*` vars through the `env` parameter of `execvpe()` instead of polluting the current process.

14. **Consolidate test fixtures.** Move `_make_ir()`, `_make_index_entry()`, and adapter fixtures to conftest.py.

15. **Add get_adapter() error handling.** Raise explicit `UnsupportedProviderError` instead of returning None.

16. **Add timeout to breakpoint wait.** Configurable via settings (e.g., 5 minutes default). Log and auto-release on timeout.

17. **DRY up override target parsing.** Replace 7 similar parser functions with a generic parser + target schema.
