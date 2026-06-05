---
title: Space Routes Implementation
type: sessions
tags: [backend, transport-matters, spaces, api]
summary: Implemented detect-only /v1/spaces routes, DTO projections, startup Space resolution, and PR review fixes.
status: active
source: backend-engineer
confidence: high
created: 2026-06-21
updated: 2026-06-21
---

## Summary

Implemented Slice 3 of Spaces on branch `spaces/slice3-spaces-routes`, PR #163. Initial commit `e09d738` added detect-only Space, Worktree, and Canvas HTTP surfaces under `/v1`, wired the router into the FastAPI app, and resolved the API process cwd into a current Space during lifespan startup when the session store is available.

Follow-up commit `8a8f5be` addressed PR review findings: `PATCH /v1/canvases/{canvasId}` now validates `defaultWorktreeId` against the owning canvas Space instead of accepting any owner-visible worktree, and cursor decoding now rejects non-object JSON as `400 invalid_cursor`.

Key live-reality reconciliation: the current v1 response convention mirrors `RunViewModel` by returning `model_dump(mode="json", by_alias=True, exclude_none=True)` without FastAPI `response_model` decorators. Keeping `response_model` with alias-dumped dicts caused FastAPI response validation to expect snake_case names because `serialization_alias` is output-only, so the new routes follow the existing alias-dump pattern.

## API Contract

```typescript
interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

interface SpaceSummary {
  spaceId: string;
  label: string;
  kind: "repo" | "plain";
  archived: boolean;
  createdAt?: string;
  updatedAt?: string;
  worktrees: WorktreeSummary[];
}

interface WorktreeSummary {
  worktreeId: string;
  spaceId: string;
  path?: string;
  workspaceSlug: string;
  workspaceHash: string;
  branch?: string;
  headOid?: string;
  isPrimary: boolean;
  missing: boolean;
  archived: boolean;
}

interface CanvasSummary {
  canvasId: string;
  spaceId: string;
  label: string;
  defaultWorktreeId?: string;
  layout: Record<string, unknown>;
  layoutVersion: number;
  archived: boolean;
}
```

Endpoints implemented:

- `GET /v1/spaces?owner=&limit=&cursor=` returns `{ items, nextCursor? }`.
- `POST /v1/spaces/resolve` returns `{ space, worktree, canvases }` and supports lookup-only `create=false`.
- `GET /v1/spaces/{spaceId}` returns `{ space, worktrees, canvases }`.
- `PATCH /v1/spaces/{spaceId}` returns `{ space }`.
- `GET /v1/spaces/{spaceId}/worktrees?refresh=` returns `{ items }` and refreshes from a known active worktree path only.
- `GET /v1/spaces/{spaceId}/canvases` returns `{ items }`.
- `POST /v1/spaces/{spaceId}/canvases` returns `{ canvas }`.
- `PATCH /v1/canvases/{canvasId}` returns `{ canvas }`.

## Database Changes

No schema migration was added. The routes use the existing Slice 1 and Slice 2 `space`, `space_git_identity`, `worktree`, and `canvas` tables through `SpaceStore`.

The review fix added a narrow parameterized `SELECT space_id FROM canvas WHERE canvas_id = %(canvas_id)s AND owner = %(owner)s` helper in `space_routes.py` so the canvas owning Space can be loaded before validating patched default worktrees.

## Security Considerations

- All routes are owner scoped with default owner `local`.
- Mutating routes require the existing local HTTP origin check via `require_http_origin`.
- Route path ids are parsed through typed UUID id wrappers and return machine readable errors for invalid ids.
- Cwd resolution rejects relative paths before detection.
- `POST /v1/spaces/{spaceId}/canvases` and `PATCH /v1/canvases/{canvasId}` both reject a `defaultWorktreeId` that is not part of the target canvas Space with `400 invalid_worktree_id`.
- Refresh is detect-only: it re-runs detection from an existing active worktree path and does not create, checkout, prune, or remove git worktrees.

## Performance Notes

- List pagination uses offset cursors with `limit + 1` lookahead.
- Cursor decoding now validates the decoded JSON shape before reading `offset`, avoiding a non-dict exception path.
- DTO projection is in-process over `SpaceStore` snapshots.
- No new query path introduces string-concatenated SQL. Database access uses parameterized queries.

Verification completed:

- `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=${TRANSPORT_MATTERS_TEST_DATABASE_URL:-postgresql://tm:tm@localhost:55432/postgres} .venv/bin/python -m pytest src/transport_matters/api/v1/test_space_routes.py` at initial delivery: 3 passed.
- `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=${TRANSPORT_MATTERS_TEST_DATABASE_URL:-postgresql://tm:tm@localhost:55432/postgres} .venv/bin/python -m pytest src/transport_matters/api/v1/test_space_routes.py src/transport_matters/space/test_store.py src/transport_matters/space/test_detection.py` at initial delivery: 16 passed.
- `cd api && just check && just test` at initial delivery: check clean, 1690 passed.
- Review fix targeted regression run: `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=${TRANSPORT_MATTERS_TEST_DATABASE_URL:-postgresql://tm:tm@localhost:55432/postgres} .venv/bin/python -m pytest src/transport_matters/api/v1/test_space_routes.py` returned 5 passed.
- Review fix full gate: `cd api && just check && just test` returned ruff format unchanged, ruff check clean, mypy clean, and 1692 passed.

## Open Items

- OpenAPI typed response models remain deferred because the current v1 alias-dumped response pattern conflicts with `response_model` validation when DTOs use output-only `serialization_alias`.
- Worktree create, checkout, prune, and remove remain intentionally out of scope for this detect-only slice.
