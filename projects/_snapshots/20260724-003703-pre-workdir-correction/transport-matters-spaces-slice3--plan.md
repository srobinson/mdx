# Slice 3: `/v1/spaces` routes Implementation Plan

**Goal:** Expose Space, Worktree, and Canvas surfaces under the existing `/v1/` prefix. This slice is detect only. It must not create, checkout, prune, or remove git worktrees.

**Architecture:** Add `api/v1/space_routes.py` as the HTTP adapter over Slice 2 `SpaceStore`. Route DTOs are public wire projections named `SpaceSummary`, `WorktreeSummary`, and `CanvasSummary`. Domain models remain snake_case. Public JSON is camelCase through explicit `Field(serialization_alias=...)`, mirroring `RunViewModel`. Owner scoping applies to every route. Mutations require the existing local origin check. The app factory registers the router under `/v1`. Lifespan resolves the API process cwd into a current Space when the session store is available.

**Tech Stack:** FastAPI, Pydantic v2, explicit `serialization_alias`, psycopg3 async pool dependency via `app.state.session_pool`, Slice 2 `SpaceStore`, Slice 1 ids and models, pytest, repo gates `just check` and `just test`.

**Frozen contracts cited from Slice 1 and Slice 2:**

- `SpaceId`, `WorktreeId`, and `CanvasId` are uuid4 backed and serialize as bare strings. Route path parameters parse those bare UUID strings.
- `Space`, `SpaceGitIdentity`, `Worktree`, and `Canvas` are internal domain rows and stay snake_case.
- `Worktree` includes nullable `branch_name`, nullable `head_oid`, and `is_primary`.
- Public Worktree wire maps `branch_name` to `branch`, `head_oid` to `headOid`, and `is_primary` to `isPrimary`.
- Public Space wire maps `Space.name` to `label` and derives `SpaceSummary.kind in {"repo","plain"}` from whether `space_git_identity` exists. There is no `kind` column.
- `SpaceSummary` inlines `worktrees: WorktreeSummary[]` for `GET /v1/spaces` and `POST /v1/spaces/resolve`; Slice 6 uses this for the launcher single versus multi worktree decision.
- Route DTOs do not reintroduce `workspaceId` as a public Space identity.

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

interface ListSpacesResponse {
  items: SpaceSummary[];
  nextCursor?: string;
}

interface SpaceDetailResponse {
  space: SpaceSummary;
  worktrees: WorktreeSummary[];
  canvases: CanvasSummary[];
}

interface ResolveSpaceRequest {
  cwd: string;
  create?: boolean;
}

interface ResolveSpaceResponse {
  space: SpaceSummary;
  worktree: WorktreeSummary;
  canvases: CanvasSummary[];
}

interface PatchSpaceRequest {
  label?: string;
  archived?: boolean;
}

interface CreateCanvasRequest {
  label: string;
  defaultWorktreeId?: string;
  layout?: Record<string, unknown>;
}

interface PatchCanvasRequest {
  label?: string;
  defaultWorktreeId?: string;
  layout?: Record<string, unknown>;
  archived?: boolean;
}
```

Endpoints:

- `GET /v1/spaces?owner=&limit=&cursor=` returns `ListSpacesResponse`.
- `POST /v1/spaces/resolve` returns `ResolveSpaceResponse`. `create=false` performs lookup only and returns `404 space_not_found` if unknown.
- `GET /v1/spaces/{spaceId}` returns `SpaceDetailResponse`.
- `PATCH /v1/spaces/{spaceId}` returns `{ space: SpaceSummary }`.
- `GET /v1/spaces/{spaceId}/worktrees?refresh=` returns `{ items: WorktreeSummary[] }`. `refresh=true` re-runs detection from a known non-missing worktree path and reconciles only observed rows.
- `GET /v1/spaces/{spaceId}/canvases` returns `{ items: CanvasSummary[] }`.
- `POST /v1/spaces/{spaceId}/canvases` returns `{ canvas: CanvasSummary }`.
- `PATCH /v1/canvases/{canvasId}` returns `{ canvas: CanvasSummary }`.

## Task 1: Add route tests for resolve, list, refresh, canvases, casing, and startup resolution

**Files:**

- Create: `api/src/transport_matters/api/v1/test_space_routes.py`

### Step 1: Write the failing tests

Create `api/src/transport_matters/api/v1/test_space_routes.py` with this complete content:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from transport_matters.api.v1.session_test_support import session_client as _client
from transport_matters.config import get_settings
from transport_matters.main import create_app, lifespan
from transport_matters.session.pool import create_async_pool
from transport_matters.session.testing import TestDb
from transport_matters.space.detection import DetectedSpace, DetectedWorktree, repo_instance_key
from transport_matters.space.store import SpaceStore
from transport_matters.workspace import workspace_id

BACKEND_ORIGIN = "http://localhost:8788"


def _headers() -> dict[str, str]:
    return {"origin": BACKEND_ORIGIN, "host": "localhost:8788"}


def _worktree(
    path: Path,
    *,
    branch: str | None = None,
    head: str | None = None,
    is_primary: bool = False,
) -> DetectedWorktree:
    workspace = workspace_id(path)
    return DetectedWorktree(
        path=path.resolve(strict=False),
        workspace_slug=workspace.slug,
        workspace_hash=workspace.hash,
        branch_name=branch,
        head_oid=head,
        is_primary=is_primary,
    )


def _git_detection(root: Path, *worktrees: Path) -> DetectedSpace:
    common_dir = root / ".git"
    return DetectedSpace(
        name="repo",
        primary_path=root.resolve(strict=False),
        repo_instance_key=repo_instance_key(common_dir),
        git_common_dir=common_dir.resolve(strict=False),
        worktrees=(_worktree(root, branch="main", head="abc123", is_primary=True),)
        + tuple(_worktree(path, branch="feature", head="def456") for path in worktrees),
    )


async def test_resolve_path_returns_camel_case_summaries_and_lists(
    test_db: TestDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    linked = tmp_path / "linked"
    repo.mkdir()
    linked.mkdir()
    monkeypatch.setattr("transport_matters.space.store.detect_space", lambda cwd: _git_detection(repo))

    async with _client(test_db) as client:
        legacy = await client.get("/api/spaces")
        assert legacy.status_code == 404

        resolved = await client.post(
            "/v1/spaces/resolve",
            json={"cwd": str(repo), "create": True},
            headers=_headers(),
        )
        assert resolved.status_code == 200
        payload = resolved.json()
        space_id = payload["space"]["spaceId"]
        worktree_id = payload["worktree"]["worktreeId"]
        assert payload["space"] == {
            "spaceId": space_id,
            "label": "repo",
            "kind": "repo",
            "archived": False,
            "createdAt": payload["space"]["createdAt"],
            "updatedAt": payload["space"]["updatedAt"],
            "worktrees": [payload["worktree"]],
        }
        assert payload["worktree"]["branch"] == "main"
        assert payload["worktree"]["headOid"] == "abc123"
        assert payload["worktree"]["isPrimary"] is True
        assert payload["worktree"]["workspaceSlug"] == workspace_id(repo).slug
        assert payload["canvases"] == []
        assert "workspaceId" not in payload["worktree"]
        assert "branch_name" not in payload["worktree"]
        assert "is_primary" not in payload["worktree"]

        listed = await client.get("/v1/spaces")
        assert listed.status_code == 200
        listed_item = listed.json()["items"][0]
        assert listed_item["spaceId"] == space_id
        assert [item["worktreeId"] for item in listed_item["worktrees"]] == [worktree_id]

        detail = await client.get(f"/v1/spaces/{space_id}")
        assert detail.status_code == 200
        assert [item["worktreeId"] for item in detail.json()["worktrees"]] == [worktree_id]

        canvas = await client.post(
            f"/v1/spaces/{space_id}/canvases",
            json={"label": "Main canvas", "defaultWorktreeId": worktree_id, "layout": {"panes": []}},
            headers=_headers(),
        )
        assert canvas.status_code == 201
        canvas_payload = canvas.json()["canvas"]
        assert canvas_payload["label"] == "Main canvas"
        assert canvas_payload["defaultWorktreeId"] == worktree_id

        canvases = await client.get(f"/v1/spaces/{space_id}/canvases")
        assert canvases.status_code == 200
        assert [item["canvasId"] for item in canvases.json()["items"]] == [canvas_payload["canvasId"]]

        patched = await client.patch(
            f"/v1/canvases/{canvas_payload['canvasId']}",
            json={"label": "Renamed canvas"},
            headers=_headers(),
        )
        assert patched.status_code == 200
        assert patched.json()["canvas"]["label"] == "Renamed canvas"

        monkeypatch.setattr("transport_matters.space.store.detect_space", lambda cwd: _git_detection(repo, linked))
        refreshed = await client.get(f"/v1/spaces/{space_id}/worktrees", params={"refresh": "true"})
        assert refreshed.status_code == 200
        paths = {item["path"] for item in refreshed.json()["items"]}
        assert paths == {str(repo.resolve()), str(linked.resolve())}


async def test_resolve_plain_space_derives_plain_kind_and_create_false_is_lookup_only(
    test_db: TestDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.setattr(
        "transport_matters.space.store.detect_space",
        lambda cwd: DetectedSpace(
            name="plain",
            primary_path=plain.resolve(),
            repo_instance_key=None,
            git_common_dir=None,
            worktrees=(_worktree(plain, is_primary=True),),
        ),
    )

    async with _client(test_db) as client:
        missing = await client.post(
            "/v1/spaces/resolve",
            json={"cwd": str(plain), "create": False},
            headers=_headers(),
        )
        assert missing.status_code == 404
        assert missing.json()["detail"]["code"] == "space_not_found"

        created = await client.post(
            "/v1/spaces/resolve",
            json={"cwd": str(plain)},
            headers=_headers(),
        )
        assert created.status_code == 200
        assert created.json()["space"]["kind"] == "plain"
        space_id = created.json()["space"]["spaceId"]

        hidden = await client.get(f"/v1/spaces/{space_id}", params={"owner": "other"})
        assert hidden.status_code == 404
        assert hidden.json()["detail"]["code"] == "space_not_found"


async def test_lifespan_resolves_api_cwd_into_current_space(
    test_db: TestDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cwd = tmp_path / "api-cwd"
    cwd.mkdir()
    monkeypatch.setenv("TRANSPORT_MATTERS_DATABASE_URL", test_db.database_url)
    monkeypatch.setenv("TRANSPORT_MATTERS_CWD", str(cwd))
    monkeypatch.setattr(
        "transport_matters.space.store.detect_space",
        lambda detected_cwd: DetectedSpace(
            name="api-cwd",
            primary_path=cwd.resolve(),
            repo_instance_key=None,
            git_common_dir=None,
            worktrees=(_worktree(cwd, is_primary=True),),
        ),
    )
    get_settings.cache_clear()
    app = create_app()

    try:
        async with lifespan(app):
            pass
        async with create_async_pool(test_db.database_url, min_size=1, max_size=2) as pool:
            async with pool.connection() as conn:
                spaces = await SpaceStore(conn, storage_dir=tmp_path / "storage").list_spaces()
    finally:
        get_settings.cache_clear()

    assert [item.space.name for item in spaces] == ["api-cwd"]
```

### Step 2: Run the tests and confirm the expected failure

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_space_routes.py
```

Expected failure before the routes are implemented:

```text
assert 404 == 200
```

The first failing request is `POST /v1/spaces/resolve`.

## Task 2: Implement the `/v1/spaces` route module

**Files:**

- Create: `api/src/transport_matters/api/v1/space_routes.py`

### Step 1: Add the route implementation

Create `api/src/transport_matters/api/v1/space_routes.py` with this complete content:

```python
"""Space, Worktree, and Canvas API routes."""

from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any, Literal, NoReturn
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi import status as http_status
from pydantic import BaseModel, ConfigDict, Field

from transport_matters.api.v1.run_routes import require_http_origin
from transport_matters.api.v1.session_store import optional_session_pool
from transport_matters.space.detection import SpaceDetectionError
from transport_matters.space.models import Canvas, CanvasId, Space, SpaceId, Worktree, WorktreeId
from transport_matters.space.store import SpaceSnapshot, SpaceStore

if TYPE_CHECKING:
    from psycopg import AsyncConnection
    from psycopg.rows import DictRow
    from psycopg_pool import AsyncConnectionPool

router = APIRouter()
DEFAULT_OWNER = "local"
DEFAULT_SPACES_LIMIT = 50
MAX_SPACES_LIMIT = 100
SpaceKind = Literal["repo", "plain"]


class ApiError(BaseModel):
    code: str
    message: str
    details: object | None = None


class WorktreeSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    worktree_id: str = Field(serialization_alias="worktreeId")
    space_id: str = Field(serialization_alias="spaceId")
    path: str | None = None
    workspace_slug: str = Field(serialization_alias="workspaceSlug")
    workspace_hash: str = Field(serialization_alias="workspaceHash")
    branch: str | None = None
    head_oid: str | None = Field(default=None, serialization_alias="headOid")
    is_primary: bool = Field(serialization_alias="isPrimary")
    missing: bool
    archived: bool


class SpaceSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    space_id: str = Field(serialization_alias="spaceId")
    label: str
    kind: SpaceKind
    archived: bool
    created_at: datetime | None = Field(default=None, serialization_alias="createdAt")
    updated_at: datetime | None = Field(default=None, serialization_alias="updatedAt")
    worktrees: list[WorktreeSummary]


class CanvasSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    canvas_id: str = Field(serialization_alias="canvasId")
    space_id: str = Field(serialization_alias="spaceId")
    label: str
    default_worktree_id: str | None = Field(default=None, serialization_alias="defaultWorktreeId")
    layout: dict[str, Any] = Field(default_factory=dict)
    layout_version: int = Field(serialization_alias="layoutVersion")
    archived: bool


class ListSpacesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[SpaceSummary]
    next_cursor: str | None = Field(default=None, serialization_alias="nextCursor")


class WorktreeListResponse(BaseModel):
    items: list[WorktreeSummary]


class CanvasListResponse(BaseModel):
    items: list[CanvasSummary]


class SpaceDetailResponse(BaseModel):
    space: SpaceSummary
    worktrees: list[WorktreeSummary]
    canvases: list[CanvasSummary]


class ResolveSpaceRequest(BaseModel):
    cwd: str
    create: bool = True


class ResolveSpaceResponse(BaseModel):
    space: SpaceSummary
    worktree: WorktreeSummary
    canvases: list[CanvasSummary]


class PatchSpaceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    label: str | None = None
    archived: bool | None = None


class SpaceMutationResponse(BaseModel):
    space: SpaceSummary


class CreateCanvasRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    label: str
    default_worktree_id: str | None = Field(default=None, validation_alias="defaultWorktreeId")
    layout: dict[str, Any] = Field(default_factory=dict)


class PatchCanvasRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    label: str | None = None
    default_worktree_id: str | None = Field(default=None, validation_alias="defaultWorktreeId")
    layout: dict[str, Any] | None = None
    archived: bool | None = None


class CanvasMutationResponse(BaseModel):
    canvas: CanvasSummary


def _api_error(code: str, message: str, details: object | None = None) -> dict[str, object]:
    return ApiError(code=code, message=message, details=details).model_dump(mode="json", exclude_none=True)


def _raise_api_error(status_code: int, code: str, message: str, details: object | None = None) -> NoReturn:
    raise HTTPException(status_code=status_code, detail=_api_error(code, message, details))


def _response_payload(response: BaseModel) -> dict[str, object]:
    return response.model_dump(mode="json", by_alias=True, exclude_none=True)


async def _session_pool(request: Request) -> AsyncConnectionPool[AsyncConnection[DictRow]]:
    pool = optional_session_pool(request)
    if pool is None:
        _raise_api_error(http_status.HTTP_503_SERVICE_UNAVAILABLE, "session_store_unavailable", "session store unavailable")
    return pool


def _encode_cursor(offset: int) -> str:
    payload = json.dumps({"offset": offset}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> int:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")))
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError):
        _raise_api_error(http_status.HTTP_400_BAD_REQUEST, "invalid_cursor", "invalid cursor")
    offset = payload.get("offset")
    if not isinstance(offset, int) or offset < 0:
        _raise_api_error(http_status.HTTP_400_BAD_REQUEST, "invalid_cursor", "invalid cursor")
    return offset


def _parse_space_id(value: str) -> SpaceId:
    try:
        return SpaceId.parse(value)
    except ValueError:
        _raise_api_error(http_status.HTTP_400_BAD_REQUEST, "invalid_space_id", "space id must be a UUID")


def _parse_worktree_id(value: str | None) -> WorktreeId | None:
    if value is None:
        return None
    try:
        return WorktreeId.parse(value)
    except ValueError:
        _raise_api_error(http_status.HTTP_400_BAD_REQUEST, "invalid_worktree_id", "worktree id must be a UUID")


def _parse_canvas_id(value: str) -> CanvasId:
    try:
        return CanvasId.parse(value)
    except ValueError:
        _raise_api_error(http_status.HTTP_400_BAD_REQUEST, "invalid_canvas_id", "canvas id must be a UUID")


def _request_cwd(cwd: str) -> Path:
    path = Path(cwd).expanduser()
    if not path.is_absolute():
        _raise_api_error(http_status.HTTP_400_BAD_REQUEST, "invalid_cwd", "cwd must be absolute")
    return path


def _space_summary(snapshot: SpaceSnapshot) -> SpaceSummary:
    return SpaceSummary(
        space_id=str(snapshot.space.space_id),
        label=snapshot.space.name,
        kind="repo" if snapshot.git_identity is not None else "plain",
        archived=snapshot.space.archived,
        created_at=snapshot.space.created_at,
        updated_at=snapshot.space.updated_at,
        worktrees=[_worktree_summary(item) for item in snapshot.worktrees],
    )


def _worktree_summary(worktree: Worktree) -> WorktreeSummary:
    return WorktreeSummary(
        worktree_id=str(worktree.worktree_id),
        space_id=str(worktree.space_id),
        path=worktree.path,
        workspace_slug=worktree.workspace_slug,
        workspace_hash=worktree.workspace_hash,
        branch=worktree.branch_name,
        head_oid=worktree.head_oid,
        is_primary=worktree.is_primary,
        missing=worktree.missing,
        archived=worktree.archived,
    )


def _canvas_summary(canvas: Canvas) -> CanvasSummary:
    return CanvasSummary(
        canvas_id=str(canvas.canvas_id),
        space_id=str(canvas.space_id),
        label=canvas.name,
        default_worktree_id=str(canvas.default_worktree_id) if canvas.default_worktree_id else None,
        layout=canvas.layout,
        layout_version=canvas.layout_version,
        archived=canvas.archived,
    )


def _detail_response(snapshot: SpaceSnapshot) -> SpaceDetailResponse:
    return SpaceDetailResponse(
        space=_space_summary(snapshot),
        worktrees=[_worktree_summary(item) for item in snapshot.worktrees],
        canvases=[_canvas_summary(item) for item in snapshot.canvases],
    )


def _worktree_for_cwd(snapshot: SpaceSnapshot, cwd: Path) -> Worktree | None:
    resolved = str(cwd.resolve(strict=False))
    for worktree in snapshot.worktrees:
        if worktree.path == resolved:
            return worktree
    return None


def _refresh_path(snapshot: SpaceSnapshot) -> Path:
    for worktree in snapshot.worktrees:
        if worktree.path is not None and not worktree.missing and not worktree.archived:
            return Path(worktree.path)
    _raise_api_error(http_status.HTTP_409_CONFLICT, "space_not_refreshable", "space has no active worktree path to refresh from")


def _require_worktree_in_space(snapshot: SpaceSnapshot, worktree_id: WorktreeId | None) -> None:
    if worktree_id is None:
        return
    if any(item.worktree_id == worktree_id for item in snapshot.worktrees):
        return
    _raise_api_error(http_status.HTTP_400_BAD_REQUEST, "invalid_worktree_id", "defaultWorktreeId must belong to the target space")


async def _require_snapshot(store: SpaceStore, space_id: SpaceId, *, owner: str) -> SpaceSnapshot:
    snapshot = await store.get_space_snapshot(space_id, owner=owner)
    if snapshot is None:
        _raise_api_error(http_status.HTTP_404_NOT_FOUND, "space_not_found", "space not found")
    return snapshot


@router.get("/spaces", response_model=ListSpacesResponse)
async def list_spaces(
    pool: Any = Depends(_session_pool),
    owner: Annotated[str, Query(min_length=1)] = DEFAULT_OWNER,
    limit: Annotated[int, Query(ge=1, le=MAX_SPACES_LIMIT)] = DEFAULT_SPACES_LIMIT,
    cursor: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    offset = _decode_cursor(cursor) if cursor is not None else 0
    async with pool.connection() as conn:
        summaries = await SpaceStore(conn).list_spaces(owner=owner, limit=limit + 1, offset=offset)
    snapshots = [SpaceSnapshot(item.space, item.git_identity, item.worktrees) for item in summaries[:limit]]
    next_cursor = _encode_cursor(offset + limit) if len(summaries) > limit else None
    return _response_payload(ListSpacesResponse(items=[_space_summary(item) for item in snapshots], next_cursor=next_cursor))


@router.post("/spaces/resolve", response_model=ResolveSpaceResponse)
async def resolve_space(
    body: ResolveSpaceRequest,
    pool: Any = Depends(_session_pool),
    owner: Annotated[str, Query(min_length=1)] = DEFAULT_OWNER,
    _origin: None = Depends(require_http_origin),
) -> dict[str, object]:
    cwd = _request_cwd(body.cwd)
    try:
        async with pool.connection() as conn:
            snapshot = await SpaceStore(conn).resolve_cwd(cwd, owner=owner, create=body.create)
    except SpaceDetectionError as exc:
        _raise_api_error(http_status.HTTP_400_BAD_REQUEST, exc.code, exc.message, exc.details)
    if snapshot is None:
        _raise_api_error(http_status.HTTP_404_NOT_FOUND, "space_not_found", "space not found")
    worktree = _worktree_for_cwd(snapshot, cwd)
    if worktree is None:
        _raise_api_error(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "worktree_resolution_failed", "resolved space did not include the requested cwd")
    return _response_payload(
        ResolveSpaceResponse(
            space=_space_summary(snapshot),
            worktree=_worktree_summary(worktree),
            canvases=[_canvas_summary(item) for item in snapshot.canvases],
        )
    )


@router.get("/spaces/{space_id}", response_model=SpaceDetailResponse)
async def get_space(
    space_id: str,
    pool: Any = Depends(_session_pool),
    owner: Annotated[str, Query(min_length=1)] = DEFAULT_OWNER,
) -> dict[str, object]:
    parsed = _parse_space_id(space_id)
    async with pool.connection() as conn:
        snapshot = await _require_snapshot(SpaceStore(conn), parsed, owner=owner)
    return _response_payload(_detail_response(snapshot))


@router.patch("/spaces/{space_id}", response_model=SpaceMutationResponse)
async def patch_space(
    space_id: str,
    body: PatchSpaceRequest,
    pool: Any = Depends(_session_pool),
    owner: Annotated[str, Query(min_length=1)] = DEFAULT_OWNER,
    _origin: None = Depends(require_http_origin),
) -> dict[str, object]:
    parsed = _parse_space_id(space_id)
    async with pool.connection() as conn:
        store = SpaceStore(conn)
        updated = await store.update_space(parsed, owner=owner, name=body.label, archived=body.archived)
        if updated is None:
            _raise_api_error(http_status.HTTP_404_NOT_FOUND, "space_not_found", "space not found")
        snapshot = await _require_snapshot(store, parsed, owner=owner)
    return _response_payload(SpaceMutationResponse(space=_space_summary(snapshot)))


@router.get("/spaces/{space_id}/worktrees", response_model=WorktreeListResponse)
async def list_space_worktrees(
    space_id: str,
    pool: Any = Depends(_session_pool),
    owner: Annotated[str, Query(min_length=1)] = DEFAULT_OWNER,
    refresh: Annotated[bool, Query()] = False,
) -> dict[str, object]:
    parsed = _parse_space_id(space_id)
    try:
        async with pool.connection() as conn:
            store = SpaceStore(conn)
            snapshot = await _require_snapshot(store, parsed, owner=owner)
            if refresh:
                snapshot = await store.resolve_cwd(_refresh_path(snapshot), owner=owner, create=True)
                if snapshot is None:
                    _raise_api_error(http_status.HTTP_404_NOT_FOUND, "space_not_found", "space not found")
    except SpaceDetectionError as exc:
        _raise_api_error(http_status.HTTP_400_BAD_REQUEST, exc.code, exc.message, exc.details)
    return _response_payload(WorktreeListResponse(items=[_worktree_summary(item) for item in snapshot.worktrees]))


@router.get("/spaces/{space_id}/canvases", response_model=CanvasListResponse)
async def list_space_canvases(
    space_id: str,
    pool: Any = Depends(_session_pool),
    owner: Annotated[str, Query(min_length=1)] = DEFAULT_OWNER,
) -> dict[str, object]:
    parsed = _parse_space_id(space_id)
    async with pool.connection() as conn:
        snapshot = await _require_snapshot(SpaceStore(conn), parsed, owner=owner)
    return _response_payload(CanvasListResponse(items=[_canvas_summary(item) for item in snapshot.canvases]))


@router.post("/spaces/{space_id}/canvases", response_model=CanvasMutationResponse, status_code=http_status.HTTP_201_CREATED)
async def create_canvas(
    space_id: str,
    body: CreateCanvasRequest,
    pool: Any = Depends(_session_pool),
    owner: Annotated[str, Query(min_length=1)] = DEFAULT_OWNER,
    _origin: None = Depends(require_http_origin),
) -> dict[str, object]:
    parsed = _parse_space_id(space_id)
    default_worktree_id = _parse_worktree_id(body.default_worktree_id)
    async with pool.connection() as conn:
        store = SpaceStore(conn)
        snapshot = await _require_snapshot(store, parsed, owner=owner)
        _require_worktree_in_space(snapshot, default_worktree_id)
        canvas = await store.create_canvas(parsed, owner=owner, name=body.label, default_worktree_id=default_worktree_id, layout=body.layout)
    return _response_payload(CanvasMutationResponse(canvas=_canvas_summary(canvas)))


@router.patch("/canvases/{canvas_id}", response_model=CanvasMutationResponse)
async def patch_canvas(
    canvas_id: str,
    body: PatchCanvasRequest,
    pool: Any = Depends(_session_pool),
    owner: Annotated[str, Query(min_length=1)] = DEFAULT_OWNER,
    _origin: None = Depends(require_http_origin),
) -> dict[str, object]:
    parsed = _parse_canvas_id(canvas_id)
    default_worktree_id = _parse_worktree_id(body.default_worktree_id)
    async with pool.connection() as conn:
        store = SpaceStore(conn)
        if default_worktree_id is not None and await store.resolve_worktree(default_worktree_id, owner=owner) is None:
            _raise_api_error(http_status.HTTP_400_BAD_REQUEST, "invalid_worktree_id", "defaultWorktreeId does not resolve")
        canvas = await store.update_canvas(
            parsed,
            owner=owner,
            name=body.label,
            default_worktree_id=default_worktree_id,
            layout=body.layout,
            archived=body.archived,
        )
    if canvas is None:
        _raise_api_error(http_status.HTTP_404_NOT_FOUND, "canvas_not_found", "canvas not found")
    return _response_payload(CanvasMutationResponse(canvas=_canvas_summary(canvas)))
```

### Step 2: Run the route tests and confirm the intermediate failure

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_space_routes.py
```

Expected failure before app registration:

```text
assert 404 == 200
```

The route module exists, but the app factory has not mounted it yet.

## Task 3: Register the router and resolve the current Space during startup

**Files:**

- Modify: `api/src/transport_matters/main.py`

### Step 1: Add imports

In `api/src/transport_matters/main.py`, replace the existing `transport_matters.api.v1` import block with this complete block:

```python
from transport_matters.api.v1 import (
    exchanges,
    meta,
    run_routes,
    runtime_template_routes,
    session_routes,
    space_routes,
    stream,
)
```

Add this import near the standard library imports:

```python
from pathlib import Path
```

Add this import near the other `transport_matters` imports:

```python
from transport_matters.space.store import SpaceStore
```

### Step 2: Add current Space resolution helper

Add this complete helper below `_start_session_store`:

```python
async def _resolve_current_space(pool: AsyncConnectionPool[AsyncConnection[DictRow]]) -> None:
    settings = get_settings()
    cwd = settings.cwd or Path.cwd()
    try:
        async with pool.connection() as conn:
            await SpaceStore(conn).resolve_cwd(cwd, owner="local", create=True)
    except Exception:
        logger.exception("Failed to resolve current Space for %s", cwd)
```

### Step 3: Call the helper during lifespan

In `lifespan`, replace this block:

```python
              session_pool = await _start_session_store(app, database_url)
              session_listener = app.state.session_event_listener
              if session_pool is not None:
                  try:
                      await pending_shared_proxy_manager.start()
```

with this complete block:

```python
              session_pool = await _start_session_store(app, database_url)
              session_listener = app.state.session_event_listener
              if session_pool is not None:
                  await _resolve_current_space(session_pool)
                  try:
                      await pending_shared_proxy_manager.start()
```

### Step 4: Include the router in `create_app`

In `create_app`, add the Spaces router after the sessions router:

```python
      app.include_router(space_routes.router, prefix="/v1", tags=["spaces"])
```

The resulting router section must be:

```python
      app.include_router(api_router, prefix="/api")
      app.include_router(run_routes.router, prefix="/v1", tags=["runs"])
      app.include_router(
          exchanges.run_router,
          prefix="/v1" + exchanges.RUN_EXCHANGES_ROUTE_PREFIX,
          tags=["exchanges"],
      )
      app.include_router(meta.run_router, prefix="/v1/runs/{run_id}/meta", tags=["meta"])
      app.include_router(stream.router, prefix="/v1", tags=["stream"])
      app.include_router(session_routes.router, prefix="/v1", tags=["sessions"])
      app.include_router(space_routes.router, prefix="/v1", tags=["spaces"])
      app.include_router(
          runtime_template_routes.router,
          prefix="/v1",
          tags=["runtime-templates"],
      )
```

### Step 5: Run the route tests and confirm the expected pass

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_space_routes.py
```

Expected pass:

```text
3 passed
```

## Task 4: Run slice gates

**Files:**

- Existing files from Tasks 1 through 3

### Step 1: Run the focused route tests

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_space_routes.py src/transport_matters/space/test_store.py src/transport_matters/space/test_detection.py
```

Expected pass:

```text
all selected tests pass
```

### Step 2: Run the repo gates

Run the repo recipes, not hand assembled substitutes:

```bash
just check && just test
```

Expected pass:

```text
just check exits 0
just test exits 0
```

### Step 3: Commit

Run:

```bash
git add api/src/transport_matters/api/v1/space_routes.py api/src/transport_matters/api/v1/test_space_routes.py api/src/transport_matters/main.py && git commit -m "feat(spaces): expose space routes"
```
