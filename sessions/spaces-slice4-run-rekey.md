---
title: Spaces Slice 4 Run Re-Key Implementation
type: sessions
tags: [backend, spaces, runs, sessions, shared-proxy]
summary: Run creation now resolves worktree identity and preserves space/worktree ids through managed runs, shared proxy, and session persistence.
status: active
source: backend-engineer
confidence: high
created: 2026-06-21
updated: 2026-06-21
---

## Summary

Implemented Spaces Slice 4 run re-keying on branch `spaces/slice4-run-rekey`, PR #164. The latest pushed head is `e53b9092cb23337f68c668c8724ba9456c4dd3c3`.

Key decisions:

- Public run creation now accepts `worktreeId` instead of `cwd`.
- `RunViewModel` now emits `spaceId` and `worktreeId`, and no longer exposes `workspaceId`.
- `SpawnRun`, `ManagedRun`, and `ManagedRunView` carry required space and worktree identity resolved through `SpaceStore`.
- `SpawnRun.resolved_worktree` is required, removing the previous `Path.cwd()` fallback.
- Captured run, shared proxy payload, shared proxy subprocess reconstruction, transcript cursor registration, and session writes all preserve `space_id` and `worktree_id`.
- Run route UUID parsing now uses one generic parser for required and optional space/worktree ids, bringing `run_routes.py` below the 700 line ceiling.

## API Contract

```typescript
// POST /v1/runs
interface CreateRunRequest {
  harness: "claude" | "codex";
  worktreeId: string;
  prompt?: string | null;
  runtimeTemplate?: string | null;
  bypassPermissions?: boolean;
  continuation?: {
    parentSessionId: string;
    idempotencyKey: string;
  } | null;
}

interface RunViewModel {
  runId: string;
  state: string;
  harness: string;
  spaceId: string;
  worktreeId: string;
  createdAt: string;
  updatedAt: string;
  attachedViewers: number;
  nativeSessionId?: string | null;
  sourceDescriptor?: string | null;
}

// GET /v1/runs?spaceId=<id>&worktreeId=<id>
interface ListRunsResponse {
  items: RunViewModel[];
  nextCursor: string | null;
}
```

Errors continue to use the existing machine-readable FastAPI error envelope. Missing or unknown worktree ids fail before spawn.

## Database Changes

No schema migration was needed in this slice because the active `session` table already has `space_id` and `worktree_id` columns from prior Spaces work.

Changed the session writer path so `SessionBinding`, `SessionRow`, `build_session`, and `UPSERT_SESSION_SQL` persist `space_id` and `worktree_id`. The upsert keeps existing values when a later write omits optional identity metadata.

Fix round follow-up threaded identity through `SharedProxyBindingPayload`, `binding_payload_from_binding()`, shared proxy subprocess reconstruction in `_runtime_binding_from_payload()`, and `register_session_cursor()` so a re-bound transcript cursor does not drop ids before `SessionWriter` persists the session row.

## Security Considerations

- Removed client supplied `cwd` from the public create run contract.
- Server side `SpaceStore.resolve_worktree()` now owns path resolution for run creation.
- Unknown worktree ids are rejected before `RunManager.spawn()`.
- Existing origin checks, harness validation, and proxy launch error mapping remain intact.

## Performance Notes

- Worktree resolution adds one store lookup before spawn.
- Run list filtering by `spaceId` and `worktreeId` is in process over managed runs, matching the current process resident run manager model.
- Shared proxy identity threading adds fields to the control payload but no extra subprocess round trips.
- Session writes remain a single upsert and add no extra database round trips.

## Verification

- `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres .venv/bin/python -m pytest src/transport_matters/shared_proxy/test_core.py::test_shared_proxy_payload_round_trip_persists_space_identity tests/integration/test_backend_launch_smoke.py::test_launched_backend_reads_db_from_home_not_per_run_storage src/transport_matters/api/v1/test_run_routes_list_filters.py`
- `cd api && just check && just test`
- Full API gate result after fix round: `1699 passed`.
- PR #164 is open, ready, and targets `main`.

## Open Items

- Frontend consumers still need to move any remaining run creation calls from `cwd` to `worktreeId` when their slice lands.
- Longer term persistent run storage may need indexed `space_id` and `worktree_id` filters if managed runs become durable beyond process lifetime.
