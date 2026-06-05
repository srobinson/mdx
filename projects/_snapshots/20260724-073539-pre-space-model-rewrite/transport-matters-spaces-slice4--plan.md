# Slice 4: Run path re-key + ResolvedWorktree + drop workspaceId Implementation Plan

**Goal:** Make every managed run carry first class Space identity. Public run creation moves from `cwd` to `worktreeId`; any internal CLI launch path must resolve cwd to `ResolvedWorktree` through `SpaceStore` before calling `RunManager.spawn`. `SpawnRun`, `ManagedRun`, and `ManagedRunView` carry `space_id` and `worktree_id` from `ResolvedWorktree`. Public `RunViewModel` drops `workspaceId` and emits `spaceId` plus `worktreeId`. The session writer path persists those ids onto `session.space_id` and `session.worktree_id`.

**Architecture:** `space.store.SpaceStore.resolve_worktree()` is the API route boundary for public run creation. `RunManager` receives a required `ResolvedWorktree`, validates the resolved cwd internally, and preserves cwd as implementation detail. There is no `Path.cwd()` fallback in `RunManager`. The run list filter grows `space_id` and `worktree_id`. Transcript ingestion propagates the same ids through `SessionBinding` and `SessionRow`, so `SessionWriter._commit_batch()` persists them via the existing `AsyncSessionDao.upsert_session()` path.

**Tech Stack:** Python 3.14, Pydantic v2, FastAPI, dataclasses, psycopg3, Slice 1 `SpaceId` and `WorktreeId`, Slice 2 `ResolvedWorktree` and `SpaceStore`, pytest, repo gates `just check` and `just test`.

**Grounded symbols:** `api/src/transport_matters/run_models.py` owns `SpawnRun`, `RunFilters`, `ManagedRunView`, and `ManagedRun`. `api/src/transport_matters/run_manager.py` owns `RunManager.list`, `_prepare_request`, `_captured_request`, and `_resolve_cwd`. `api/src/transport_matters/api/v1/run_routes.py` owns `CreateRunRequest`, `RunViewModel`, `_spawn_request`, `_launch_fields`, `run_view_model`, and list filters. `api/src/transport_matters/shared_proxy/binding.py` owns `ProxyRunBinding`. `api/src/transport_matters/addon_runtime.py` owns `_make_exchange_cursor_sink`, the captured-run `SessionBinding` construction seam. `api/src/transport_matters/index/adapters/base.py` owns `SessionBinding`. `api/src/transport_matters/session/ingest.py` owns `build_session`. `api/src/transport_matters/session/writer.py` owns `SessionWriter._commit_batch`. `api/src/transport_matters/session/models.py`, `dao_statements.py`, and `dao_rows.py` own persisted session columns.

## API Contract

```typescript
interface CreateRunRequest {
  harness: "claude" | "codex" | string;
  worktreeId: string;
  terminal?: { cols: number; rows: number };
  oscColorReplies?: boolean;
  continueFromSessionId?: string;
  idempotencyKey?: string;
  runtimeTemplate?: string;
  bypassPermissions?: boolean;
}

interface RunViewModel {
  runId: string;
  spaceId: string;
  worktreeId: string;
  sessionId: string;
  harness: string;
  state: "RUNNING" | "TERMINATING" | "TERMINATED" | "EXITED" | "FAILED";
  endReason?: "explicit" | "idle-timeout" | "shutdown" | "deploy-restart";
  error?: string;
  createdAt: string;
}

interface ListRunsQuery {
  state?: string;
  spaceId?: string;
  worktreeId?: string;
  limit?: number;
  cursor?: string;
}
```

## Task 1: Extend run domain models with resolved Space identity

**Files:**

- Modify: `api/src/transport_matters/run_models.py`
- Modify: `api/src/transport_matters/run_manager.py`
- Create: `api/src/transport_matters/test_run_manager_spaces.py`

### Step 1: Write the failing model tests

Create `api/src/transport_matters/test_run_manager_spaces.py` with this complete content:

```python
from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from transport_matters.captured_run import CLAUDE_HARNESS_NAME
from transport_matters.run_manager import RunFilters, SpawnRun
from transport_matters.space.models import ResolvedWorktree, SpaceId, WorktreeId
from transport_matters.test_run_manager import PreparedRunHarness, PtyHarness, make_manager, patch_pty_teardown


def _resolved(tmp_path: Path) -> ResolvedWorktree:
    return ResolvedWorktree(
        space_id=SpaceId.from_uuid(UUID("11111111-1111-4111-8111-111111111111")),
        worktree_id=WorktreeId.from_uuid(UUID("22222222-2222-4222-8222-222222222222")),
        cwd=str(tmp_path),
        workspace_slug="workspace",
        workspace_hash="hash1",
        missing=False,
        archived=False,
    )


@pytest.mark.asyncio
async def test_run_manager_threads_resolved_worktree_into_run_view(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pty = PtyHarness()
    patch_pty_teardown(monkeypatch, pty)
    prepared = PreparedRunHarness(tmp_path)
    manager = make_manager(tmp_path, pty, prepared, shared_proxy_manager=object())
    resolved = _resolved(tmp_path)

    run = await manager.spawn(
        SpawnRun(harness=CLAUDE_HARNESS_NAME, resolved_worktree=resolved, start_on_attach=False)
    )
    view = run.view()

    assert run.cwd == tmp_path.resolve()
    assert run.space_id == resolved.space_id
    assert run.worktree_id == resolved.worktree_id
    assert view.space_id == resolved.space_id
    assert view.worktree_id == resolved.worktree_id
    assert view.cwd == tmp_path.resolve()


@pytest.mark.asyncio
async def test_run_manager_filters_by_space_and_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pty = PtyHarness()
    patch_pty_teardown(monkeypatch, pty)
    prepared = PreparedRunHarness(tmp_path)
    manager = make_manager(tmp_path, pty, prepared, shared_proxy_manager=object())
    resolved = _resolved(tmp_path)
    other = resolved.model_copy(
        update={"worktree_id": WorktreeId.from_uuid(UUID("33333333-3333-4333-8333-333333333333"))}
    )

    first = await manager.spawn(SpawnRun(harness=CLAUDE_HARNESS_NAME, resolved_worktree=resolved))
    await manager.spawn(SpawnRun(harness=CLAUDE_HARNESS_NAME, resolved_worktree=other))

    assert [item.run_id for item in manager.list(RunFilters(space_id=resolved.space_id))] == [
        first.run_id,
        next(item.run_id for item in manager.list() if item.run_id != first.run_id),
    ]
    assert [item.run_id for item in manager.list(RunFilters(worktree_id=resolved.worktree_id))] == [
        first.run_id
    ]
```

### Step 2: Run the tests and confirm the expected failure

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/test_run_manager_spaces.py
```

Expected failure:

```text
TypeError: SpawnRun.__init__() got an unexpected keyword argument 'resolved_worktree'
```

### Step 3: Add the minimal model fields

In `api/src/transport_matters/run_models.py`, add this import:

```python
from transport_matters.space.models import ResolvedWorktree, SpaceId, WorktreeId
```

Update `SpawnRun` so resolved identity is required. Keep `cwd` only if an older caller still supplies it for validation during the same edit, then delete that fallback before the task is complete:

```python
    resolved_worktree: ResolvedWorktree
```

Every `RunManager.spawn(SpawnRun(...))` call site must pass `resolved_worktree`. A caller that starts from cwd must first call `SpaceStore.resolve_cwd(..., create=True)` or equivalent and select the intended `ResolvedWorktree`; `RunManager` must not infer identity from `Path.cwd()`.

Update `RunFilters` with these complete additional fields after `cwd`:

```python
    space_id: SpaceId | None = None
    worktree_id: WorktreeId | None = None
```

Update `ManagedRunView` with these complete additional fields after `cwd`:

```python
    space_id: SpaceId
    worktree_id: WorktreeId
```

Update `ManagedRun` with these complete additional fields after `cwd`:

```python
    space_id: SpaceId
    worktree_id: WorktreeId
```

In `ManagedRun.view`, add these complete arguments after `cwd=self.cwd`:

```python
            space_id=self.space_id,
            worktree_id=self.worktree_id,
```

### Step 4: Thread resolved identity through `RunManager`

In `api/src/transport_matters/run_manager.py`, update `_ValidatedSpawnRun` to carry `space_id` and `worktree_id` wherever the local `_ValidatedSpawnRun` dataclass is defined:

```python
@dataclass(frozen=True)
class _ValidatedSpawnRun:
    request: SpawnRun
    cwd: Path
    upstream: str | None
    space_id: SpaceId
    worktree_id: WorktreeId
```

Add the `SpaceId` and `WorktreeId` import from `transport_matters.space.models` if needed.

Replace `RunManager.list` with this complete implementation:

```python
    def list(self, filters: RunFilters | None = None) -> list[ManagedRunView]:
        runs = tuple(self._runs.values())
        if filters is not None:
            if filters.harness is not None:
                runs = tuple(run for run in runs if run.harness == filters.harness)
            if filters.cwd is not None:
                runs = tuple(run for run in runs if run.cwd == filters.cwd)
            if filters.space_id is not None:
                runs = tuple(run for run in runs if run.space_id == filters.space_id)
            if filters.worktree_id is not None:
                runs = tuple(run for run in runs if run.worktree_id == filters.worktree_id)
            if filters.states is not None:
                runs = tuple(run for run in runs if run.state in filters.states)
        return [run.view() for run in runs]
```

Replace `_resolve_cwd` with this complete implementation:

```python
    def _resolve_cwd(self, request: SpawnRun) -> Path:
        working_dir = Path(request.resolved_worktree.cwd).expanduser()
        if not working_dir.is_absolute():
            raise RunManagerError("invalid_cwd", "cwd must be an absolute path")
        if not working_dir.exists():
            raise RunManagerError("invalid_cwd", f"cwd does not exist: {working_dir}")
        if not working_dir.is_dir():
            raise RunManagerError("invalid_cwd", f"cwd is not a directory: {working_dir}")
        return working_dir.resolve()
```

In `_validate_spawn_request`, change the call from `self._resolve_cwd(request.cwd)` to `self._resolve_cwd(request)` and set the validated ids directly from the required `request.resolved_worktree`.

Use this exact assignment inside `_validate_spawn_request` before returning `_ValidatedSpawnRun`:

```python
        resolved = request.resolved_worktree
        space_id = resolved.space_id
        worktree_id = resolved.worktree_id
```

In `_spawn_new_admitted`, add these arguments when constructing `ManagedRun`:

```python
            space_id=validated.space_id,
            worktree_id=validated.worktree_id,
```

### Step 5: Run the tests and confirm the expected pass

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/test_run_manager_spaces.py
```

Expected pass:

```text
2 passed
```

### Step 6: Commit

Run:

```bash
git add api/src/transport_matters/run_models.py api/src/transport_matters/run_manager.py api/src/transport_matters/test_run_manager_spaces.py && git commit -m "feat(spaces): thread run worktree identity"
```

## Task 2: Replace public run creation `cwd` with `worktreeId` and drop `workspaceId`

**Files:**

- Modify: `api/src/transport_matters/api/v1/run_routes.py`
- Modify: `api/src/transport_matters/api/v1/test_run_routes.py`
- Modify: `api/src/transport_matters/api/v1/test_run_routes_list_filters.py`

### Step 1: Write failing route tests

In `api/src/transport_matters/api/v1/test_run_routes.py`, add this complete test:

```python
from uuid import UUID

from transport_matters.space.models import ResolvedWorktree, SpaceId, WorktreeId


def test_post_run_resolves_worktree_id_and_serializes_space_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    harness = ManagedRunHarness(tmp_path, monkeypatch)
    space_id = SpaceId.from_uuid(UUID("11111111-1111-4111-8111-111111111111"))
    worktree_id = WorktreeId.from_uuid(UUID("22222222-2222-4222-8222-222222222222"))
    resolved = ResolvedWorktree(
        space_id=space_id,
        worktree_id=worktree_id,
        cwd=str(tmp_path),
        workspace_slug="workspace",
        workspace_hash="hash1",
        missing=False,
        archived=False,
    )

    class Store:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def resolve_worktree(self, requested: WorktreeId, *, owner: str = "local") -> ResolvedWorktree | None:
            assert requested == worktree_id
            assert owner == "local"
            return resolved

    monkeypatch.setattr("transport_matters.api.v1.run_routes.SpaceStore", Store)
    client = _client(monkeypatch, tmp_path)

    with client:
        response = client.post(
            "/v1/runs",
            json={"harness": "claude", "worktreeId": str(worktree_id)},
            headers=_http_headers(BACKEND_ORIGIN),
        )

    assert response.status_code == 201
    run = response.json()["run"]
    assert set(run) == {"runId", "spaceId", "worktreeId", "sessionId", "harness", "state", "createdAt"}
    assert run["spaceId"] == str(space_id)
    assert run["worktreeId"] == str(worktree_id)
    assert "workspaceId" not in run
    spawned = harness.manager.get(run["runId"])
    assert spawned.space_id == space_id
    assert spawned.worktree_id == worktree_id
```

Update every existing `workspaceId` assertion in `api/src/transport_matters/api/v1/test_run_routes.py`: the sites currently at 78, 97, and 160 all move from `workspaceId` to `spaceId` plus `worktreeId`. In `test_post_get_attach_detach_and_terminate`, also change the create JSON from `cwd` to `worktreeId` by using the store stub above. Keep the old invalid cwd test by renaming it to prove `worktreeId` is required on public routes.

Add this complete test in `api/src/transport_matters/api/v1/test_run_routes_list_filters.py`. It uses the real `manager.spawn(SpawnRun(resolved_worktree=...))` seam and does not invent `_spawn_test_view`:

```python
import asyncio
from uuid import UUID

from transport_matters.captured_run import CLAUDE_HARNESS_NAME
from transport_matters.run_manager import SpawnRun
from transport_matters.space.models import ResolvedWorktree, SpaceId, WorktreeId


def _resolved(tmp_path: Path, *, space_id: SpaceId, worktree_id: WorktreeId) -> ResolvedWorktree:
    return ResolvedWorktree(
        space_id=space_id,
        worktree_id=worktree_id,
        cwd=str(tmp_path),
        workspace_slug="workspace",
        workspace_hash="hash1",
        missing=False,
        archived=False,
    )


def test_list_runs_filters_by_space_and_worktree(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    harness = ManagedRunHarness(tmp_path, monkeypatch)
    first_space = SpaceId.from_uuid(UUID("11111111-1111-4111-8111-111111111111"))
    second_space = SpaceId.from_uuid(UUID("33333333-3333-4333-8333-333333333333"))
    first_worktree = WorktreeId.from_uuid(UUID("22222222-2222-4222-8222-222222222222"))
    second_worktree = WorktreeId.from_uuid(UUID("44444444-4444-4444-8444-444444444444"))
    first = asyncio.run(
        harness.manager.spawn(
            SpawnRun(
                harness=CLAUDE_HARNESS_NAME,
                resolved_worktree=_resolved(tmp_path, space_id=first_space, worktree_id=first_worktree),
            )
        )
    )
    asyncio.run(
        harness.manager.spawn(
            SpawnRun(
                harness=CLAUDE_HARNESS_NAME,
                resolved_worktree=_resolved(tmp_path, space_id=second_space, worktree_id=second_worktree),
            )
        )
    )
    client = _client(monkeypatch, tmp_path)

    with client:
        by_space = client.get(
            "/v1/runs",
            params={"spaceId": str(first_space)},
            headers=_http_headers(BACKEND_ORIGIN),
        ).json()
        by_worktree = client.get(
            "/v1/runs",
            params={"worktreeId": str(first_worktree)},
            headers=_http_headers(BACKEND_ORIGIN),
        ).json()

    assert [item["runId"] for item in by_space["items"]] == [first.run_id]
    assert [item["runId"] for item in by_worktree["items"]] == [first.run_id]
```

### Step 2: Run the tests and confirm the expected failure

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_run_routes.py src/transport_matters/api/v1/test_run_routes_list_filters.py
```

Expected failures:

```text
AssertionError: assert 'workspaceId' not in run
```

and, before route wiring, `worktreeId` is ignored or rejected.

### Step 3: Update the route request and response models

In `api/src/transport_matters/api/v1/run_routes.py`, add imports:

```python
from transport_matters.space.models import SpaceId, WorktreeId
from transport_matters.space.store import SpaceStore
```

Replace `CreateRunRequest.cwd` with this field:

```python
    worktree_id: str | None = Field(default=None, alias="worktreeId")
```

Keep internal helpers that accept `cwd` for non-public CLI code out of this public request model.

Replace `RunViewModel` with this complete class:

```python
class RunViewModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    run_id: str = Field(serialization_alias="runId")
    space_id: str = Field(serialization_alias="spaceId")
    worktree_id: str = Field(serialization_alias="worktreeId")
    session_id: str = Field(serialization_alias="sessionId")
    harness: CapturedRunHarness
    state: PublicRunState
    end_reason: Literal["explicit", "idle-timeout", "shutdown", "deploy-restart"] | None = Field(
        default=None, serialization_alias="endReason"
    )
    error: str | None = None
    created_at: str = Field(serialization_alias="createdAt")
```

Add this helper:

```python
def _parse_worktree_id(value: str | None) -> WorktreeId:
    if value is None or value == "":
        _raise_api_error(http_status.HTTP_400_BAD_REQUEST, "worktree_required", "worktreeId is required")
    try:
        return WorktreeId.parse(value)
    except ValueError:
        _raise_api_error(http_status.HTTP_400_BAD_REQUEST, "invalid_worktree_id", "worktreeId must be a UUID")
```

Add this async helper:

```python
async def _resolved_worktree(body: CreateRunRequest, *, request: Request, owner: str) -> ResolvedWorktree:
    worktree_id = _parse_worktree_id(body.worktree_id)
    pool = optional_session_pool(request)
    if pool is None:
        _raise_api_error(http_status.HTTP_503_SERVICE_UNAVAILABLE, "session_store_unavailable", "session store unavailable")
    async with pool.connection() as conn:
        resolved = await SpaceStore(conn).resolve_worktree(worktree_id, owner=owner)
    if resolved is None:
        _raise_api_error(http_status.HTTP_404_NOT_FOUND, "worktree_not_found", "worktree not found")
    if resolved.missing or resolved.archived:
        _raise_api_error(http_status.HTTP_409_CONFLICT, "worktree_unavailable", "worktree is missing or archived")
    return resolved
```

Update `_spawn_request` to accept `resolved_worktree: ResolvedWorktree` and pass it into `SpawnRun`:

```python
def _spawn_request(
    body: CreateRunRequest,
    settings: Settings,
    *,
    resolved_worktree: ResolvedWorktree,
    launch_fields: dict[str, object] | None = None,
    runtime_template: RuntimeTemplateRef | None = None,
) -> SpawnRun:
    terminal = body.terminal or TerminalSizeModel()
    harness = _validated_harness(body.harness)
    return SpawnRun(
        harness=harness,
        resolved_worktree=resolved_worktree,
        cols=terminal.cols,
        rows=terminal.rows,
        passthrough=(),
        home_dir=settings.agent_home_dir,
        debug=settings.debug,
        osc_color_replies=body.osc_color_replies,
        runtime_template=runtime_template,
        launch_fields=launch_fields or {},
        idempotency_key=body.idempotency_key,
        start_on_attach=True,
        defer_session_ownership=harness == CODEX_HARNESS_NAME,
        bypass_permissions=body.bypass_permissions,
    )
```

Update `create_run` so it resolves worktree before building `SpawnRun`:

```python
        resolved = await _resolved_worktree(body, request=request, owner=owner)
        spawn_request = _spawn_request(
            body,
            get_settings(),
            resolved_worktree=resolved,
            runtime_template=runtime_template,
        )
```

Replace `_cursor_filter_key` with this complete helper:

```python
def _cursor_filter_key(
    state: str | None, space_id: str | None, worktree_id: str | None
) -> dict[str, str | None]:
    return {"state": state, "spaceId": space_id, "worktreeId": worktree_id}
```

Update `list_runs` signature to accept `spaceId` and `worktreeId`, parse them into ids, and pass them into `RunFilters`:

```python
    space_id: str | None = Query(default=None, alias="spaceId"),
    worktree_id: str | None = Query(default=None, alias="worktreeId"),
```

When constructing `RunFilters`, include:

```python
        space_id=SpaceId.parse(space_id) if space_id else None,
        worktree_id=WorktreeId.parse(worktree_id) if worktree_id else None,
```

Replace `run_view_model` with this complete implementation:

```python
def run_view_model(view: ManagedRunView) -> RunViewModel:
    if view.space_id is None or view.worktree_id is None:
        raise RuntimeError("managed run view is missing resolved Space identity")
    end_reason = view.end_reason if view.end_reason in _END_REASONS else None
    return RunViewModel(
        run_id=view.run_id,
        space_id=str(view.space_id),
        worktree_id=str(view.worktree_id),
        session_id=_session_id_for_view(view),
        harness=view.harness,
        state=_curated_state(view.state),
        end_reason=cast(
            'Literal["explicit", "idle-timeout", "shutdown", "deploy-restart"] | None',
            end_reason,
        ),
        error=view.error,
        created_at=view.created_at.isoformat(),
    )
```

Delete `_workspace_id_for_view` after the tests no longer reference it.

### Step 4: Run route tests and confirm the expected pass

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_run_routes.py src/transport_matters/api/v1/test_run_routes_list_filters.py
```

Expected pass:

```text
all selected tests pass
```

### Step 5: Commit

Run:

```bash
git add api/src/transport_matters/api/v1/run_routes.py api/src/transport_matters/api/v1/test_run_routes.py api/src/transport_matters/api/v1/test_run_routes_list_filters.py && git commit -m "feat(spaces): expose run space identity"
```

## Task 3: Persist resolved identity through the session writer path

**Files:**

- Modify: `api/src/transport_matters/index/adapters/base.py`
- Modify: `api/src/transport_matters/session/ingest.py`
- Modify: `api/src/transport_matters/session/models.py`
- Modify: `api/src/transport_matters/session/dao_statements.py`
- Modify: `api/src/transport_matters/session/dao_rows.py`
- Modify: `api/src/transport_matters/shared_proxy/binding.py`
- Modify: `api/src/transport_matters/addon_runtime.py`
- Modify: `api/src/transport_matters/session/test_foundation.py`
- Modify: `api/src/transport_matters/session/writer.py`

### Step 1: Write failing persistence tests

In `api/src/transport_matters/session/test_foundation.py`, add this complete test:

```python
from uuid import UUID

from transport_matters.space.models import SpaceId, WorktreeId


def test_session_upsert_persists_space_and_worktree_ids(dao: SessionDao) -> None:
    space_id = SpaceId.from_uuid(UUID("11111111-1111-4111-8111-111111111111"))
    worktree_id = WorktreeId.from_uuid(UUID("22222222-2222-4222-8222-222222222222"))
    row = dao.upsert_session(
        root_session("space-session").model_copy(
            update={"space_id": space_id, "worktree_id": worktree_id}
        )
    )

    fetched = dao.get_session("space-session")

    assert row.space_id == space_id
    assert row.worktree_id == worktree_id
    assert fetched is not None
    assert fetched.space_id == space_id
    assert fetched.worktree_id == worktree_id
```

In `api/src/transport_matters/session/test_ingest.py`, add this complete test:

```python
from uuid import UUID

from transport_matters.index.adapters.base import SessionBinding
from transport_matters.session.ingest import build_session
from transport_matters.space.models import SpaceId, WorktreeId


def test_build_session_threads_space_identity_from_binding() -> None:
    binding = SessionBinding(
        session_id="s1",
        provider="anthropic",
        run_id="run1",
        cwd="/workspace",
        workspace_slug="workspace",
        workspace_hash="hash1",
        started_at="2026-06-06T00:00:00+00:00",
        space_id=SpaceId.from_uuid(UUID("11111111-1111-4111-8111-111111111111")),
        worktree_id=WorktreeId.from_uuid(UUID("22222222-2222-4222-8222-222222222222")),
    )

    session = build_session(binding)

    assert session.space_id == binding.space_id
    assert session.worktree_id == binding.worktree_id
```

### Step 2: Run tests and confirm the expected failure

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/session/test_foundation.py -k space_and_worktree src/transport_matters/session/test_ingest.py -k space_identity
```

Expected failure:

```text
ValueError: "SessionRow" object has no field "space_id"
```

or `SessionBinding` rejects `space_id`.

### Step 3: Add id fields to binding and session rows

In `api/src/transport_matters/index/adapters/base.py`, import ids:

```python
from transport_matters.space.models import SpaceId, WorktreeId
```

Add fields to `SessionBinding` after `workspace_hash`:

```python
    space_id: SpaceId | None = None
    worktree_id: WorktreeId | None = None
```

In `api/src/transport_matters/session/models.py`, import ids and add fields to `SessionRow` after `workspace_hash`:

```python
    space_id: SpaceId | None = None
    worktree_id: WorktreeId | None = None
```

In `api/src/transport_matters/session/ingest.py`, add these arguments to `build_session` after `workspace_hash`:

```python
        space_id=binding.space_id,
        worktree_id=binding.worktree_id,
```

### Step 4: Wire DAO columns

In `api/src/transport_matters/session/dao_statements.py`, add `space_id` and `worktree_id` to `SESSION_COLUMN_NAMES` immediately after `workspace_hash`.

In `UPSERT_SESSION_SQL`, add the two insert columns after `workspace_hash`, add the two values after `%(workspace_hash)s`, and add these conflict updates after `workspace_hash = EXCLUDED.workspace_hash`:

```sql
    space_id = COALESCE(EXCLUDED.space_id, "session".space_id),
    worktree_id = COALESCE(EXCLUDED.worktree_id, "session".worktree_id),
```

In `api/src/transport_matters/session/dao_rows.py`, `session_params()` already dumps model fields. Keep that single source of truth. Do not hand-build UUID values there.

### Step 5: Bind resolved identity into the captured-run SessionBinding path

The captured-run binding construction seam is `addon_runtime._make_exchange_cursor_sink(...).register(...)`, where the code builds `session_binding = SessionBinding(...)` from the run-scoped `ProxyRunBinding` returned by `binding_for_run_id(entry.run_id)`. `SessionWriter._commit_batch()` only commits the resulting `EventBatch.session`, so the identity must be present before `register_session_cursor(...)` builds batches.

Add `space_id: SpaceId | None` and `worktree_id: WorktreeId | None` to `ProxyRunBinding`, and populate those fields from the `ManagedRun` when registering the run with the shared proxy. The complete binding construction edit is:

```python
session_binding = SessionBinding(
    session_id=_wire_session_id(entry.run_id, request.provider, native_session_id),
    provider=request.provider,
    run_id=entry.run_id,
    cwd=str(binding.working_dir),
    workspace_slug=workspace.slug,
    workspace_hash=workspace.hash,
    space_id=binding.space_id,
    worktree_id=binding.worktree_id,
    started_at=entry.ts.isoformat(),
    harness=harness,
    native_session_id=native_session_id,
    minted=request.provider in _DIRECT_MINT_PROVIDERS,
    source_descriptor=binding.owned_source_descriptor,
    template_provenance=_template_provenance(binding),
    parent_session_id=_string_launch_field(binding, "parent_session_id"),
    title=_string_launch_field(binding, "title"),
    home_dir=home_dir,
)
```

Do not leave a cwd-only compatibility branch. The invariant for Slice 4 is: every `RunManager` run carries `space_id` and `worktree_id`, and every captured-run `SessionBinding` sourced from a managed run receives those same ids.

### Step 6: Run persistence tests and confirm the expected pass

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/session/test_foundation.py -k space_and_worktree src/transport_matters/session/test_ingest.py -k space_identity
```

Expected pass:

```text
2 passed
```

### Step 7: Run slice gates

Run:

```bash
just check && just test
```

Expected pass:

```text
just check exits 0
just test exits 0
```

### Step 8: Commit

Run:

```bash
git add api/src/transport_matters/index/adapters/base.py api/src/transport_matters/session/ingest.py api/src/transport_matters/session/models.py api/src/transport_matters/session/dao_statements.py api/src/transport_matters/session/dao_rows.py api/src/transport_matters/session/test_foundation.py api/src/transport_matters/session/test_ingest.py api/src/transport_matters/session/writer.py && git commit -m "feat(spaces): persist run session identity"
```
