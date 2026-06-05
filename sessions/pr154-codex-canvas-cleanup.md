---
title: PR 154 Codex Canvas Cleanup
type: sessions
tags: [backend, transport-matters, codex, run-manager, shared-proxy]
summary: Addressed PR 154 cleanup items for owned cursor cleanup, run list public state filtering, redundant locate avoidance, and run manager LOC refactor.
status: active
source: backend-engineer
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

## Summary

Implemented PR 154 review feedback on branch `fix/codex-canvas-first-paint`, commit `c315d35`.

Key decisions:

- Added regression tests for owned shared proxy binding cleanup when session capture is unavailable or owned cursor registration fails.
- Kept `RunManager.list()` raw state semantics unchanged and fixed public state filtering at the API route boundary.
- Threaded `ProxyRunBinding.owned_source_descriptor` into read back `SessionBinding` creation so owned runs reuse the deterministic descriptor and skip redundant transcript discovery.
- Extracted public run contracts and dataclasses into `transport_matters.run_models`, preserving existing `transport_matters.run_manager` imports through reexports and `__all__`.

## API Contract

Affected endpoint:

```typescript
type RunState = "RUNNING" | "TERMINATING" | "TERMINATED" | "EXITED" | "FAILED";

interface Run {
  runId: string;
  workspaceId: string;
  sessionId: string;
  harness: "claude" | "codex";
  state: RunState;
  endReason?: "explicit" | "idle-timeout" | "shutdown" | "deploy-restart";
  error?: string;
  createdAt: string;
}

interface ListRunsResponse {
  items: Run[];
  nextCursor: string | null;
}

interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

// GET /v1/runs?state=RUNNING&limit&cursor
// Public state filter RUNNING now matches internal STARTING and RUNNING runs.
// Returned run.state remains the curated public state, so STARTING is rendered as RUNNING.
```

Validation remains unchanged: `STARTING` is not accepted as a public state filter.

## Database Changes

None.

## Security Considerations

- No new public inputs were introduced.
- Existing state validation remains in `_validated_state()`.
- Shared proxy cleanup tests pin cleanup on owned cursor failures so stale run bindings and snapshot writers are not retained after failed registration.

## Performance Notes

- Owned exchange cursor registration now carries `source_descriptor`, avoiding redundant adapter `locate()` discovery work for owned runs.
- Deferred and non owned discovery still invokes `locate()`, preserving the canvas first paint deferred Codex path.
- `run_manager.py` is now 596 LOC. The extracted `run_models.py` seam is 197 LOC.

## Verification

- Failing before evidence for D2 and D3: with only the new tests and old production behavior, `test_list_runs_running_filter_includes_starting_runs` failed with `assert [] == ['run-1']`, and `test_exchange_cursor_sink_uses_owned_source_descriptor_without_locate` failed with `assert 1 == 0` for `adapter.locate_calls`.
- Passing targeted evidence: `uv run pytest src/transport_matters/test_run_models.py::test_run_models_imports_in_fresh_process src/transport_matters/shared_proxy/test_core.py::test_register_owned_binding_requires_session_capture_and_cleans_up src/transport_matters/shared_proxy/test_core.py::test_register_owned_binding_cursor_failure_cleans_up src/transport_matters/api/v1/test_run_routes_list_filters.py::test_list_runs_running_filter_includes_starting_runs src/transport_matters/test_addon_runtime.py::test_exchange_cursor_sink_registers_deferred_codex_session src/transport_matters/test_addon_runtime.py::test_exchange_cursor_sink_uses_owned_source_descriptor_without_locate` passed, 6 passed in 0.29s.
- `just check` passed.
- `just test` passed: desktop 29 passed, web 981 passed, API 1583 passed.

## Open Items

None for the requested PR 154 cleanup items.
