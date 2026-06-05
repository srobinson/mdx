---
title: PR 155 Follow-up API Test Cleanup
type: sessions
tags: [backend, api, tests, runs, yolo-toggle]
summary: Split oversized run test modules and addressed API-side bypass-permissions review nits in PR #156.
status: active
source: backend-engineer
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

## Summary

Implemented the API-owned follow-up fixes from the PR #155 bypass-permissions review on branch `test/pr155-followups`, committed as `32d7019`, pushed, and opened PR #156.

Key decisions:

- Kept existing shared test helpers in `api/src/transport_matters/test_run_manager.py` to avoid duplicating fixtures.
- Split lifecycle and terminal behavior into focused sibling test modules.
- Preserved all existing test coverage and added one owned Codex captured-run ordering regression.

## API Contract

No runtime API contract changed in this follow-up. The existing `POST /v1/runs` `bypassPermissions` field remains unchanged.

Relevant test coverage now lives in:

- `api/src/transport_matters/api/v1/test_run_routes.py` for core HTTP run routes and spawn request mapping.
- `api/src/transport_matters/api/v1/test_run_routes_terminal.py` for websocket terminal route behavior.

## Database Changes

None.

## Security Considerations

The bypass flag remains a strict boolean carrier with fixed argv constants. This follow-up tightened resource cleanup in captured-run tests by leasing through `contextlib.ExitStack`, preventing a latent lease leak if a second captured-run preparation fails.

Added captured-path coverage for owned Codex sessions proving `--yolo` is inserted before `resume` in the real prepared argv.

## Performance Notes

No production performance changes. Test module sizes after the split:

- `api/src/transport_matters/test_run_manager.py`: 470 LOC
- `api/src/transport_matters/test_run_manager_lifecycle.py`: 294 LOC
- `api/src/transport_matters/api/v1/test_run_routes.py`: 635 LOC
- `api/src/transport_matters/api/v1/test_run_routes_terminal.py`: 114 LOC

Verification:

```text
cd /Users/alphab/Dev/LLM/DEV/helioy/transport-matters/api && just check && just test
All checks passed!
Success: no issues found in 405 source files
1590 passed in 47.54s
```

## Open Items

None for the API-owned PR #155 follow-up scope. The review file also included two non-blocking frontend/design notes that were outside this API-only task.
