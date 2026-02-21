---
title: ALP-1127 AM Chat Interface - Iter 1 Review
type: sessions
tags: [review, security, cors, am-cli, http-server]
summary: Fixed CORS origin validation vulnerability in HTTP server; 315 tests pass
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-11
updated: 2026-03-11
---

## Summary

Reviewed iteration 1 of ALP-1127 (AM Standalone Chat Interface). Three commits added:
- ALP-1131: axum HTTP server scaffold with `--http` flag
- ALP-1132: REST endpoints for all 12 AM memory tools + episodes endpoint
- ALP-1133: LLM proxy endpoint with SSE streaming via OpenRouter

Overall code quality is solid. Server architecture (bind/serve split, CancellationToken shutdown, shared state via Arc<Mutex>) is well designed. The refactoring of `ServerState` methods for reuse between MCP and HTTP handlers is clean.

## Issues Found and Fixed

### 1. CORS Origin Validation Vulnerability (http_server.rs)

**Severity:** Medium (security)

The CORS predicate used `origin.as_bytes().starts_with(b"http://localhost")` which matches `http://localhost.evil.com`. An attacker could create a page at that domain that makes cross-origin requests to the local AM server, reading and writing the user's memory.

**Fix:** Replaced with strict validation function `is_local_origin()` that requires the origin to be exactly the host, optionally followed by `:<port>` with digits only. Added 9 unit tests.

## Patterns Observed

- Worker creates `reqwest::Client` per-request in `handle_chat`. For v1 local server this is acceptable but should be addressed if request volume increases.
- `post_response_ops` (buffer, activate, salient) runs inside the async stream generator. If the client disconnects mid-stream, these ops may not execute, losing the memory record of the exchange. Acceptable for v1 but worth addressing later with a detached task.
- `do_query` does not call `save_system` (query drift is ephemeral until `activate_response` persists). `do_query_index` does persist. This asymmetry is intentional: `query_index` is a standalone operation that may not be followed by `activate_response`.

## Open Items

None. All issues within review scope were resolved.
