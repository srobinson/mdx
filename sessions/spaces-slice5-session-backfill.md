---
title: Spaces Slice 5 Session Backfill
type: sessions
tags: [backend, spaces, sessions, api]
summary: Implemented session Space identity backfill and /v1/sessions Space filters.
status: active
source: backend-engineer
confidence: high
created: 2026-06-21
updated: 2026-06-21
---

## Summary

Implemented Slice 5 session Space backfill on branch `spaces/slice5-session-backfill` in PR #165.

Key decisions:

- Reused the existing `session.space_id`, `session.worktree_id`, `space`, and `space_worktree` schema from the Spaces foundation migration.
- Added a bounded startup backfill that uses a pooled session store connection and conn scoped `AsyncSessionDao` plus `SpaceStore` instances.
- Resolved present cwd values through `SpaceStore.resolve_cwd()` so backfilled sessions share the same Space identity path as new captured runs.
- Fixed PR #165 review round at `a70736dd1a94092e1a65107b558247fa129c3198`: subdirectory cwd values now resolve to the containing worktree root, not the primary worktree fallback.
- Treated deleted cwd values as missing worktrees with stable workspace slug and hash identity.
- Left empty cwd legacy sessions intentionally unassigned and surfaced `legacyGroup: "unassigned"` in the API response.

## API Contract

```typescript
interface SessionView {
  sessionId: string;
  workspaceId: string;
  spaceId: string | null;
  worktreeId: string | null;
  legacyGroup: "unassigned" | null;
  title: string | null;
  status: string;
  provider: string;
  harness: string;
  createdAt: string;
  lastActivityAt: string;
  purpose: string;
  visibility: string;
  lineage: SessionLineage;
  turnCount: number;
  inheritedTurnCount: number;
  lastMessagePreview: string | null;
}

interface ListSessionsRequestQuery {
  workspaceId?: string;
  spaceId?: string;
  worktreeId?: string;
  purpose?: string;
  visibility?: string;
  includeInternal?: boolean;
  limit?: number;
  cursor?: string;
}

interface ListSessionsResponse {
  items: SessionView[];
  nextCursor: string | null;
}

interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}
```

Endpoint changes:

- `GET /v1/sessions?spaceId=<uuid>` filters sessions by `session.space_id`.
- `GET /v1/sessions?worktreeId=<uuid>` filters sessions by `session.worktree_id`.
- `workspaceId` remains supported for legacy workspace slug or hash filters.
- Cursor filter keys include `spaceId` and `worktreeId` to prevent cross filter cursor reuse.

## Database Changes

No new migration was required.

Existing schema used by this slice:

- `session.space_id`
- `session.worktree_id`
- `space_worktree.missing`
- partial indexes on `session.space_id` and `session.worktree_id`

New DAO methods:

- `AsyncSessionDao.list_sessions_missing_space_identity(owner, limit)`
- `AsyncSessionDao.update_session_space_identity(owner, session_id, space_id, worktree_id)`

Backfill behavior:

- Scans rows where either identity column is null.
- Orders non empty cwd rows before empty cwd legacy rows.
- Processes bounded batches with `BACKFILL_BATCH_SIZE = 100`.
- Creates or reuses missing worktree rows for deleted cwd values.
- Skips resolver calls for empty cwd rows.
- Uses a shared `ResolvedWorktree.from_worktree()` builder for run handoff values.

## Security Considerations

- All database writes use parameterized SQL through psycopg bindings.
- Owner scoping is preserved on session reads, backfill scans, and Space store writes.
- The new API filters are typed UUID query parameters through FastAPI.
- The backfill does not expose raw transcript or wire payloads.
- Startup backfill failures are logged and do not change the existing database degradation behavior.

## Performance Notes

- The backfill uses bounded batches to avoid loading large session histories into memory.
- Present path filesystem checks and resolution run off the event loop.
- Existing partial indexes support `spaceId` and `worktreeId` filters.
- Worktree selection uses a longest containing root match, so nested cwd values under linked worktrees do not leak into primary worktree filters.
- Full gate passed on 2026-06-21 after the fix round: `cd api && just check && just test`, with `1711 passed`.

## Open Items

- Empty cwd legacy rows remain unassigned by design. A later product slice can add a dedicated legacy grouping or cleanup workflow if needed.
- The backfill runs at startup. If session history becomes very large, move it behind an explicit maintenance command or progress tracked job.
