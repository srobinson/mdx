# Slice 5: Session backfill + empty cwd legacy Implementation Plan

**Goal:** Backfill existing session rows with first class Space identity without misclassifying legacy rows that have no cwd. Sessions with a real cwd gain `space_id` and `worktree_id`. Sessions whose cwd points at a path that no longer exists resolve to a missing worktree. Sessions with `cwd == ""` remain legacy unassigned and continue to be reachable through the retained `workspaceId` history filter.

**Architecture:** Slice 4 makes live captured runs write `session.space_id` and `session.worktree_id`. Slice 5 closes the historical gap. `session/backfill.py` owns an idempotent row scanner that asks `SpaceStore` to resolve each stored cwd. The scanner never uses process cwd as a fallback. `SpaceStore` gains a session backfill resolver that can handle missing paths and can create or reuse `space_worktree` rows with `missing = true`. Public session reads expose camelCase `spaceId`, `worktreeId`, and `legacyGroup`; existing `workspaceId` remains as a legacy history filter.

**Tech Stack:** Python 3.14, Pydantic v2, FastAPI query aliases, psycopg3, Postgres nullable uuid columns, Slice 1 `SpaceId` and `WorktreeId`, Slice 2 `SpaceStore`, pytest, repo gates `just check` and `just test`.

**Grounded symbols:** `api/src/transport_matters/session/backfill.py` owns transcript backfill orchestration. `api/src/transport_matters/session/async_dao.py` owns `AsyncSessionDao` and async session reads. `api/src/transport_matters/session/models.py` owns `SessionRow` and `SessionListRow`; Slice 4 already added nullable `space_id` and `worktree_id`. `api/src/transport_matters/session/dao_rows.py` owns session list row parsing. `api/src/transport_matters/session/dao_statements.py` owns `LIST_SESSION_VIEWS_SQL` and related SQL. `api/src/transport_matters/api/v1/session_routes.py` owns session query parameters and list filters. `api/src/transport_matters/api/v1/session_models.py` owns `SessionView`, which uses `ConfigDict(alias_generator=_to_camel)`. `api/src/transport_matters/main.py` owns `lifespan` and `app.state.session_pool`. `api/src/transport_matters/space/store.py` owns Space and Worktree persistence.

## API Contract

```typescript
interface SessionSummary {
  sessionId: string;
  owner: string;
  workspaceId: string | null;
  spaceId: string | null;
  worktreeId: string | null;
  legacyGroup: "unassigned" | null;
  cwd: string;
  harness: string | null;
  title: string | null;
  startedAt: string | null;
  updatedAt: string | null;
}

interface ListSessionsQuery {
  workspaceId?: string; // retained legacy history filter
  spaceId?: string;
  worktreeId?: string;
  limit?: number;
  cursor?: string;
}
```

**Legacy rule:** `cwd == ""` means the row predates reliable cwd capture. It is grouped as `legacyGroup: "unassigned"`, leaves `spaceId` and `worktreeId` null, and must never be assigned to whatever Space happens to be active at backfill time.

**Missing path rule:** `cwd != ""` with a path that no longer exists still represents a real historical target. Backfill creates or reuses a `space_worktree` row with `missing = true`, `branch_name = null`, `head_oid = null`, and `is_primary = false`, then writes its ids to the session row.

**Preflight schema rule:** Inspect the Slice 1 migration before implementation and verify `session.space_id`, `session.worktree_id`, `space_worktree.missing`, and the existing partial indexes are present. Do not add a Slice 5 migration for those columns or indexes. The expected action is to rely on the Slice 1 schema and avoid duplicate indexes.

## Task 1: Add the session Space backfill scanner

**Files:**

- Modify: `api/src/transport_matters/session/backfill.py`
- Modify: `api/src/transport_matters/session/dao_statements.py`
- Modify: `api/src/transport_matters/session/async_dao.py`
- Create: `api/src/transport_matters/test_session_space_backfill.py`

### Step 1: Write the failing scanner tests

Create `api/src/transport_matters/test_session_space_backfill.py` with focused tests that use a small fake DAO or the existing Postgres test fixture, whichever is already used by nearby session backfill tests. Keep the test seam at `session/backfill.py`.

```python
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import pytest

from transport_matters.session.backfill import backfill_session_spaces
from transport_matters.space.models import ResolvedWorktree, SpaceId, WorktreeId


@dataclass
class BackfillCandidate:
    session_id: str
    owner: str
    workspace_id: str | None
    cwd: str


class FakeSessionDao:
    def __init__(self, candidates: list[BackfillCandidate]) -> None:
        self.candidates = candidates
        self.updates: list[tuple[str, SpaceId, WorktreeId]] = []

    async def list_sessions_missing_space_identity(self, *, owner: str) -> list[BackfillCandidate]:
        return [candidate for candidate in self.candidates if candidate.owner == owner]

    async def update_session_space_identity(
        self,
        *,
        owner: str,
        session_id: str,
        space_id: SpaceId,
        worktree_id: WorktreeId,
    ) -> None:
        self.updates.append((session_id, space_id, worktree_id))


class FakeSpaceStore:
    def __init__(self, resolved: ResolvedWorktree) -> None:
        self.resolved = resolved
        self.cwd_calls: list[str] = []

    async def resolve_session_cwd(self, cwd: str, *, owner: str) -> ResolvedWorktree:
        self.cwd_calls.append(cwd)
        return self.resolved


def _resolved(cwd: str) -> ResolvedWorktree:
    return ResolvedWorktree(
        space_id=SpaceId.from_uuid(UUID("11111111-1111-4111-8111-111111111111")),
        worktree_id=WorktreeId.from_uuid(UUID("22222222-2222-4222-8222-222222222222")),
        cwd=cwd,
        workspace_slug="workspace",
        workspace_hash="hash1",
        missing=False,
        archived=False,
    )


@pytest.mark.asyncio
async def test_backfill_writes_space_identity_for_real_cwd(tmp_path) -> None:
    cwd = str(tmp_path)
    dao = FakeSessionDao([BackfillCandidate("s1", "local", "legacy", cwd)])
    store = FakeSpaceStore(_resolved(cwd))

    result = await backfill_session_spaces(session_dao=dao, space_store=store, owner="local")

    assert store.cwd_calls == [cwd]
    assert dao.updates == [("s1", store.resolved.space_id, store.resolved.worktree_id)]
    assert result.scanned == 1
    assert result.resolved == 1
    assert result.legacy_unassigned == 0


@pytest.mark.asyncio
async def test_backfill_leaves_empty_cwd_unassigned() -> None:
    dao = FakeSessionDao([BackfillCandidate("legacy", "local", "old-workspace", "")])
    store = FakeSpaceStore(_resolved("/should/not/be/used"))

    result = await backfill_session_spaces(session_dao=dao, space_store=store, owner="local")

    assert store.cwd_calls == []
    assert dao.updates == []
    assert result.scanned == 1
    assert result.resolved == 0
    assert result.legacy_unassigned == 1
```

### Step 2: Run the tests and confirm the expected failure

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/test_session_space_backfill.py
```

Expected first failure:

```text
ImportError: cannot import name 'backfill_session_spaces'
```

### Step 3: Implement the scanner seam

Add a typed result and an injectable scanner in `session/backfill.py`. The injection keeps the scanner easy to unit test while the production caller can pass the real DAO and `SpaceStore`.

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from transport_matters.space.models import ResolvedWorktree, SpaceId, WorktreeId


@dataclass(frozen=True, slots=True)
class SessionSpaceBackfillResult:
    scanned: int = 0
    resolved: int = 0
    missing: int = 0
    legacy_unassigned: int = 0


class SessionSpaceBackfillDao(Protocol):
    async def list_sessions_missing_space_identity(self, *, owner: str): ...

    async def update_session_space_identity(
        self,
        *,
        owner: str,
        session_id: str,
        space_id: SpaceId,
        worktree_id: WorktreeId,
    ) -> None: ...


class SessionCwdResolver(Protocol):
    async def resolve_session_cwd(self, cwd: str, *, owner: str) -> ResolvedWorktree: ...


async def backfill_session_spaces(
    *,
    session_dao: SessionSpaceBackfillDao,
    space_store: SessionCwdResolver,
    owner: str = "local",
) -> SessionSpaceBackfillResult:
    scanned = 0
    resolved_count = 0
    missing_count = 0
    legacy_unassigned = 0
    rows = await session_dao.list_sessions_missing_space_identity(owner=owner)

    for row in rows:
        scanned += 1
        cwd = row.cwd.strip()
        if not cwd:
            legacy_unassigned += 1
            continue

        resolved = await space_store.resolve_session_cwd(cwd, owner=owner)
        await session_dao.update_session_space_identity(
            owner=owner,
            session_id=row.session_id,
            space_id=resolved.space_id,
            worktree_id=resolved.worktree_id,
        )
        resolved_count += 1
        if resolved.missing:
            missing_count += 1

    return SessionSpaceBackfillResult(
        scanned=scanned,
        resolved=resolved_count,
        missing=missing_count,
        legacy_unassigned=legacy_unassigned,
    )
```

### Step 4: Add DAO methods for production rows

Add SQL in `session/dao_statements.py`:

```python
LIST_SESSIONS_MISSING_SPACE_IDENTITY_SQL = """
SELECT
  s.session_id,
  s.owner,
  s.workspace_id,
  s.cwd
FROM "session" s
WHERE s.owner = %(owner)s
  AND (s.space_id IS NULL OR s.worktree_id IS NULL)
ORDER BY s.updated_at NULLS LAST, s.session_id
"""

UPDATE_SESSION_SPACE_IDENTITY_SQL = """
UPDATE "session"
SET space_id = %(space_id)s::uuid,
    worktree_id = %(worktree_id)s::uuid
WHERE owner = %(owner)s
  AND session_id = %(session_id)s
"""
```

Add matching `AsyncSessionDao` methods. Convert `SpaceId` and `WorktreeId` to uuid strings at the adapter boundary. Do not stringify inside `session/backfill.py`.

### Step 5: Rerun the scanner tests

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/test_session_space_backfill.py
```

Expected pass. If the fake DAO shape drifts from production row objects, fix the protocol to use the production row type rather than duplicating a new type.

## Task 2: Resolve missing session cwd values through SpaceStore

**Files:**

- Modify: `api/src/transport_matters/space/store.py`
- Modify: `api/src/transport_matters/space/models.py`
- Create: `api/src/transport_matters/space/test_store_session_resolution.py`

### Step 1: Write failing SpaceStore tests

Create `api/src/transport_matters/space/test_store_session_resolution.py` with tests that use the shared `space_store` pytest fixture introduced in Slice 2. That fixture builds `SpaceStore(conn)` over a `TestDb` pooled connection; do not invent a long lived app singleton.

```python
from __future__ import annotations

from pathlib import Path

import pytest

from transport_matters.space.store import SpaceStore


@pytest.mark.asyncio
async def test_resolve_session_cwd_uses_existing_worktree_for_present_path(
    space_store: SpaceStore,
    tmp_path: Path,
) -> None:
    resolved = await space_store.resolve_session_cwd(str(tmp_path), owner="local")

    assert resolved.cwd == str(tmp_path.resolve())
    assert resolved.missing is False

    again = await space_store.resolve_session_cwd(str(tmp_path), owner="local")
    assert again.space_id == resolved.space_id
    assert again.worktree_id == resolved.worktree_id


@pytest.mark.asyncio
async def test_resolve_session_cwd_creates_missing_worktree_for_deleted_path(
    space_store: SpaceStore,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "deleted" / "project"

    resolved = await space_store.resolve_session_cwd(str(missing), owner="local")

    assert resolved.cwd == str(missing.resolve(strict=False))
    assert resolved.missing is True
    assert resolved.archived is False

    worktree = await space_store.get_worktree(resolved.worktree_id, owner="local")
    assert worktree.missing is True
    assert worktree.branch_name is None
    assert worktree.head_oid is None
    assert worktree.is_primary is False
```

### Step 2: Run the tests and confirm the expected failure

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/space/test_store_session_resolution.py
```

Expected first failure:

```text
AttributeError: 'SpaceStore' object has no attribute 'resolve_session_cwd'
```

### Step 3: Implement the resolver

Add `resolve_session_cwd()` to `SpaceStore`. Reuse Slice 2 detection for paths that exist. Add a narrow missing path helper for deleted paths.

```python
async def resolve_session_cwd(self, cwd: str, *, owner: str = "local") -> ResolvedWorktree:
    target = Path(cwd).expanduser().resolve(strict=False)
    if target.exists():
        return await self.resolve_cwd(str(target), owner=owner)
    return await self._ensure_missing_session_worktree(target, owner=owner)
```

Implementation notes:

- Canonicalize with `resolve(strict=False)` so a deleted path has stable identity.
- Do not inspect `Path.cwd()` anywhere in this flow.
- For a missing path, compute the same workspace slug and hash that the old workspace id used for that path.
- Persist `space.kind` through the existing identity model rather than adding a kind column.
- Persist `space_worktree.missing = true`, `is_primary = false`, `branch_name = null`, and `head_oid = null`.
- If a row already exists for the same canonical path and owner, return it instead of inserting a duplicate.

If `space_worktree.path` is currently nonnullable, keep the missing row path as the canonical deleted path string. Reserve `path = null` for the optional empty cwd legacy group only if the implementation chooses a legacy Worktree row. The preferred implementation for empty cwd in this slice is a DTO group with null ids.

### Step 4: Rerun SpaceStore tests

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/space/test_store_session_resolution.py
```

Expected pass.

## Task 3: Expose session Space fields and legacy grouping on public DTOs

**Files:**

- Modify: `api/src/transport_matters/session/models.py`
- Modify: `api/src/transport_matters/session/dao_rows.py`
- Modify: `api/src/transport_matters/api/v1/session_models.py`
- Modify: `api/src/transport_matters/api/v1/session_routes.py`
- Create: `api/src/transport_matters/api/v1/test_session_routes_spaces.py`

### Step 1: Write failing DTO tests

Create or extend `api/src/transport_matters/api/v1/test_session_routes_spaces.py`.

```python
from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient


def test_session_list_emits_space_ids_as_camel_case(client: TestClient, seeded_session_with_space) -> None:
    response = client.get("/v1/sessions")

    assert response.status_code == 200
    item = response.json()["sessions"][0]
    assert item["spaceId"] == "11111111-1111-4111-8111-111111111111"
    assert item["worktreeId"] == "22222222-2222-4222-8222-222222222222"
    assert "space_id" not in item
    assert "worktree_id" not in item
    assert item["legacyGroup"] is None


def test_empty_cwd_session_is_legacy_unassigned(client: TestClient, seeded_empty_cwd_session) -> None:
    response = client.get("/v1/sessions", params={"workspaceId": "legacy-workspace"})

    assert response.status_code == 200
    item = response.json()["sessions"][0]
    assert item["workspaceId"] == "legacy-workspace"
    assert item["spaceId"] is None
    assert item["worktreeId"] is None
    assert item["legacyGroup"] == "unassigned"
```

Use local fixtures instead of inventing new fixture machinery. If the current suite builds API rows directly, assert through `session_view_from_row()` and then one route smoke test.

### Step 2: Run the tests and confirm the expected failure

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_session_routes_spaces.py
```

Expected first failure:

```text
KeyError: 'spaceId'
```

or the response omits `legacyGroup`. A `SessionRow(..., space_id=...)` constructor failure is not valid in Slice 5 because Slice 4 already added `space_id` and `worktree_id` to `SessionRow`, `SessionBinding`, `SESSION_COLUMN_NAMES`, and `UPSERT_SESSION_SQL`.

### Step 3: Extend session list row parsing and public DTO models

Build on Slice 4's `SessionRow` and persistence columns. Slice 5 only adds the public `legacy_group` projection and list filters. Update `SessionListRow` in `session/models.py` if it does not already carry `space_id`, `worktree_id`, and `cwd`, then update `session/dao_rows.py` to parse those fields from list rows.

Update `SessionView` in `api/v1/session_models.py`. Do not add per-field aliases; this model already inherits `PublicSessionModel` with `ConfigDict(alias_generator=_to_camel, populate_by_name=True)`.

```python
class SessionView(PublicSessionModel):
    session_id: str
    workspace_id: str | None
    space_id: str | None
    worktree_id: str | None
    legacy_group: Literal["unassigned"] | None = None
    # existing fields stay unchanged
```

Set `legacy_group` in `session_view_from_row(row: SessionListRow)`:

```python
def _legacy_group_for_session(row: SessionListRow) -> Literal["unassigned"] | None:
    if row.cwd == "" and row.space_id is None and row.worktree_id is None:
        return "unassigned"
    return None
```

### Step 4: Rerun DTO tests

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_session_routes_spaces.py
```

Expected pass for DTO serialization and empty cwd grouping.

## Task 4: Add `spaceId` and `worktreeId` session list filters while retaining `workspaceId`

**Files:**

- Modify: `api/src/transport_matters/api/v1/session_routes.py`
- Modify: `api/src/transport_matters/session/async_dao.py`
- Modify: `api/src/transport_matters/session/dao_statements.py`
- Modify: `api/src/transport_matters/session/dao_rows.py`
- Extend: `api/src/transport_matters/api/v1/test_session_routes_spaces.py`

### Step 1: Write failing filter tests

Add route tests that seed three sessions: two in one Space across two worktrees, and one legacy empty cwd row with `workspace_id = "legacy-workspace"`.

```python
def test_session_list_filters_by_space_id(client: TestClient, seeded_space_sessions) -> None:
    response = client.get(
        "/v1/sessions",
        params={"spaceId": "11111111-1111-4111-8111-111111111111"},
    )

    assert response.status_code == 200
    assert {item["sessionId"] for item in response.json()["sessions"]} == {"s1", "s2"}


def test_session_list_filters_by_worktree_id(client: TestClient, seeded_space_sessions) -> None:
    response = client.get(
        "/v1/sessions",
        params={"worktreeId": "22222222-2222-4222-8222-222222222222"},
    )

    assert response.status_code == 200
    assert [item["sessionId"] for item in response.json()["sessions"]] == ["s1"]


def test_workspace_id_filter_still_finds_empty_cwd_legacy_sessions(
    client: TestClient,
    seeded_empty_cwd_session,
) -> None:
    response = client.get("/v1/sessions", params={"workspaceId": "legacy-workspace"})

    assert response.status_code == 200
    assert [item["sessionId"] for item in response.json()["sessions"]] == ["legacy"]
    assert response.json()["sessions"][0]["legacyGroup"] == "unassigned"
```

### Step 2: Run the tests and confirm the expected failure

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_session_routes_spaces.py
```

Expected first failure:

```text
422 Unprocessable Entity
```

or sessions are not filtered because the DAO ignores the new query fields.

### Step 3: Implement route parsing and DAO filters

In `session_routes.py`, add camelCase query aliases:

```python
space_id: UUID | None = Query(default=None, alias="spaceId"),
worktree_id: UUID | None = Query(default=None, alias="worktreeId"),
```

Pass both values into the DAO filter object or argument list. Keep `workspace_id` unchanged.

Update the cursor filter key so cursor reuse cannot cross filter scopes:

```python
def _cursor_filter_key(..., workspace_id: str | None, space_id: UUID | None, worktree_id: UUID | None) -> str:
    return json.dumps(
        {
            "workspaceId": workspace_id,
            "spaceId": str(space_id) if space_id else None,
            "worktreeId": str(worktree_id) if worktree_id else None,
        },
        sort_keys=True,
    )
```

Update `LIST_SESSION_VIEWS_SQL`:

```sql
AND (%(workspace_id)s IS NULL OR s.workspace_id = %(workspace_id)s)
AND (%(space_id)s::uuid IS NULL OR s.space_id = %(space_id)s::uuid)
AND (%(worktree_id)s::uuid IS NULL OR s.worktree_id = %(worktree_id)s::uuid)
```

Parameter rules:

- `workspace_id` remains a string because it is the legacy history key.
- `space_id` and `worktree_id` are uuid strings at the SQL adapter boundary.
- Do not coerce empty cwd rows into Space filters. They should appear only through `workspaceId` or unfiltered lists.

### Step 4: Rerun filter tests

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_session_routes_spaces.py
```

Expected pass.

## Task 5: Wire the backfill into `main.lifespan` without breaking no database mode

**Files:**

- Modify: `api/src/transport_matters/main.py`
- Modify: `api/src/transport_matters/session/backfill.py`
- Create or extend: `api/src/transport_matters/api/v1/test_session_routes.py` or a nearby lifespan test module

### Step 1: Write failing startup tests

Drive startup through the real `main.lifespan` and the existing `TestDb` settings override pattern. Do not invent settings factories or lifespan wrapper helpers.

```python
import pytest

from transport_matters.config import get_settings
from transport_matters.main import create_app, lifespan
from transport_matters.session.backfill import SessionSpaceBackfillResult
from transport_matters.session.testing import TestDb


@pytest.mark.asyncio
async def test_lifespan_runs_session_space_backfill_when_database_enabled(
    test_db: TestDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def fake_backfill(*, session_dao, space_store, owner: str = "local"):
        assert session_dao.__class__.__name__ == "AsyncSessionDao"
        assert space_store.__class__.__name__ == "SpaceStore"
        calls.append(owner)
        return SessionSpaceBackfillResult(scanned=1, resolved=1)

    monkeypatch.setenv("TRANSPORT_MATTERS_DATABASE_URL", test_db.database_url)
    monkeypatch.setattr("transport_matters.main.backfill_session_spaces", fake_backfill)
    get_settings.cache_clear()
    app = create_app()
    try:
        async with lifespan(app):
            pass
    finally:
        get_settings.cache_clear()

    assert calls == ["local"]


@pytest.mark.asyncio
async def test_lifespan_skips_session_space_backfill_without_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def fake_backfill(*args, **kwargs):
        calls.append("called")
        return SessionSpaceBackfillResult()

    monkeypatch.delenv("TRANSPORT_MATTERS_DATABASE_URL", raising=False)
    monkeypatch.setattr("transport_matters.main.backfill_session_spaces", fake_backfill)
    get_settings.cache_clear()
    app = create_app()
    try:
        async with lifespan(app):
            pass
    finally:
        get_settings.cache_clear()

    assert calls == []
```

### Step 2: Run the tests and confirm the expected failure

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_session_routes.py -k session_space_backfill
```

Expected first failure: the fake backfill is never called in database enabled startup.

### Step 3: Implement idempotent startup wiring

Add imports in `main.py`:

```python
from transport_matters.session.async_dao import AsyncSessionDao
from transport_matters.session.backfill import backfill_session_spaces
from transport_matters.space.store import SpaceStore
```

Add a helper near `_start_session_store`. This mirrors Slice 3's `_resolve_current_space(pool)` shape: open one pooled connection, construct connection-scoped stores inside that connection, and close them with the connection.

```python
async def _backfill_session_spaces(
    pool: AsyncConnectionPool[AsyncConnection[DictRow]],
) -> None:
    async with pool.connection() as conn:
        result = await backfill_session_spaces(
            session_dao=AsyncSessionDao(conn),
            space_store=SpaceStore(conn),
            owner="local",
        )
    logger.info(
        "session space backfill complete",
        extra={
            "scanned": result.scanned,
            "resolved": result.resolved,
            "missing": result.missing,
            "legacy_unassigned": result.legacy_unassigned,
        },
    )
```

Call it from `lifespan` only when `_start_session_store(...)` returns a pool:

```python
session_pool = await _start_session_store(app, settings.database_url)
if session_pool is not None:
    await _backfill_session_spaces(session_pool)
```

Keep this simple:

- No daemon.
- No scheduler.
- No retry loop beyond startup failure handling already used by `lifespan`.
- No database calls in no database mode.
- No DAO or SpaceStore app state singletons; `AsyncSessionDao` and `SpaceStore` are connection-scoped.
- Idempotence comes from the DAO query selecting only rows with missing Space identity.

### Step 4: Rerun startup tests

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_session_routes.py -k session_space_backfill
```

Expected pass.

## Task 6: Confirm Slice 1 schema, no migration

**Files:**

- Inspect only unless the preflight proves Slice 1 is missing a required object

### Step 1: Inspect migration state before editing

Run:

```bash
grep -R "space_worktree" -n api/src api/migrations migrations 2>/dev/null | head -80
grep -R "session_space_ix\|session_worktree_ix\|space_id\|worktree_id" -n api/src api/migrations migrations 2>/dev/null | head -120
```

Validate these already exist from Slice 1:

- `session.space_id uuid null`
- `session.worktree_id uuid null`
- `space_worktree.missing boolean not null default false`
- partial indexes `session_space_ix` and `session_worktree_ix`

### Step 2: Do not add duplicate migration objects

Expected action: no Slice 5 migration. Do not add plain indexes such as `idx_session_space_id` or `idx_session_worktree_id`; they duplicate the Slice 1 partial indexes. If the preflight unexpectedly fails, stop and reconcile the Slice 1 plan before implementing Slice 5.

### Step 3: Add batching note for backfill cost

Document in `session/backfill.py` or nearby comments that present-cwd backfill calls `SpaceStore.resolve_session_cwd()`, which may run git detection per unresolved session. The scanner is idempotent, but large histories should process candidates in batches to keep startup bounded.

```python
BACKFILL_BATCH_SIZE = 100
```

Use a DAO `limit` parameter for `list_sessions_missing_space_identity(...)` if existing histories can be large. Do not load the entire unresolved history into memory.

## Task 7: End to end verification

Run targeted tests first:

```bash
cd api && .venv/bin/python -m pytest \
  src/transport_matters/test_session_space_backfill.py \
  src/transport_matters/space/test_store_session_resolution.py \
  src/transport_matters/api/v1/test_session_routes_spaces.py
```

Then run repo gates:

```bash
just check && just test
```

Manual verification with a seeded database:

1. Insert or retain one historical session with `cwd` set to an existing repo path.
2. Insert or retain one historical session with `cwd` set to a deleted path.
3. Insert or retain one legacy session with `cwd = ''` and a legacy `workspace_id`.
4. Start the API.
5. Confirm logs show the backfill counts.
6. Query `/v1/sessions?spaceId=<space-id>` and verify only resolved Space sessions appear.
7. Query `/v1/sessions?worktreeId=<worktree-id>` and verify only that worktree's sessions appear.
8. Query `/v1/sessions?workspaceId=<legacy-workspace>` and verify the empty cwd row appears with `legacyGroup: "unassigned"` and null Space ids.

## Commit Plan

1. Commit scanner and DAO methods after Task 1 passes.
2. Commit SpaceStore missing path resolution after Task 2 passes.
3. Commit public DTO and route filter changes after Tasks 3 and 4 pass.
4. Commit startup wiring and migration cleanup after Tasks 5 and 6 pass.
5. Final commit only after `just check && just test` pass.

## Failure Modes to Guard Against

- Empty cwd rows accidentally inherit the current process cwd. Add assertions that the resolver is not called for `cwd == ""`.
- Missing paths create duplicate worktrees on every startup. Add an idempotence assertion around `resolve_session_cwd()`.
- Cursor tokens mix `workspaceId`, `spaceId`, and `worktreeId` scopes. Include all three in the cursor filter key.
- Snake case leaks through public session responses. Use explicit `serialization_alias` fields and route tests.
- No database mode starts making database calls. Keep startup wiring behind the existing database enabled check.
- Backfill rewrites live rows that already have ids from Slice 4. DAO selection must filter to `space_id is null or worktree_id is null`.
