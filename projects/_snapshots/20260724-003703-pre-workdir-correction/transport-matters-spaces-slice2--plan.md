# Slice 2: Detection + Space store Implementation Plan

**Goal:** Detect a Space from a target cwd, persist Slice 1 Space rows, reconcile observed Worktrees, resolve a Worktree for later run handoff, and write the tier 1 Space cache. No HTTP routes in this slice.

**Architecture:** `space/detection.py` owns subprocess argv git probes and returns a domain neutral detection result. `space/store.py` owns Postgres writes over the Slice 1 tables using the same async psycopg connection pattern as `AsyncSessionDao` and `SessionWriter`. Plain directories produce a single Worktree Space with no `space_git_identity` row. Git repositories group by `repo_instance_key = sha256(resolved git_common_dir)`. Git versus plain is derived from the presence of a `space_git_identity` row. There is no `kind` column.

**Tech Stack:** Python 3.14, dataclasses, Pydantic v2 Slice 1 models, psycopg3 async connections, Postgres native `uuid`, subprocess argv git probes, pytest, repo gates `just check` and `just test`.

**Frozen contracts cited from Slice 1:**

- `api/src/transport_matters/space/models.py` owns `SpaceId`, `WorktreeId`, and `CanvasId`: uuid4 backed, bare string JSON, `.short()` display helper.
- `Space`, `SpaceGitIdentity`, `Worktree`, `Canvas`, and `ResolvedWorktree` are frozen Pydantic domain rows and serialize snake_case.
- `SpaceGitIdentity` is `{space_id, repo_instance_key, git_common_dir, detected_at}`.
- `Worktree` includes `worktree_id`, `space_id`, `owner`, `path`, `workspace_slug`, `workspace_hash`, nullable `branch_name`, nullable `head_oid`, `is_primary`, `missing`, and `archived`.
- Tables are `space`, `space_git_identity`, `space_worktree`, and `canvas`. `space_git_identity.repo_instance_key` is unique. `space_worktree` has `UNIQUE(owner, workspace_slug, workspace_hash)` and `UNIQUE(owner, path)`. `session.space_id` and `session.worktree_id` are nullable.
- Reuse `transport_matters.workspace.workspace_id(cwd)` for every Worktree path. Do not re-key WorkspaceId.
- Git Space `name` is derived from the primary worktree path, not from the cwd that triggered detection, so linked-worktree detection cannot make labels order dependent.
- `git worktree list --porcelain -z` is the source for per-worktree branch and HEAD data. Detection must not fan out to `git branch` and `git rev-parse` once per worktree.

**Internal contract:**

```python
@dataclass(frozen=True)
class DetectedWorktree:
    path: Path
    workspace_slug: str
    workspace_hash: str
    branch_name: str | None
    head_oid: str | None
    is_primary: bool
    missing: bool = False

@dataclass(frozen=True)
class DetectedSpace:
    name: str
    primary_path: Path
    repo_instance_key: str | None
    git_common_dir: Path | None
    worktrees: tuple[DetectedWorktree, ...]

class SpaceStore:
    async def upsert_detection(self, detection: DetectedSpace, *, owner: str = "local") -> SpaceSnapshot: ...
    async def resolve_cwd(self, cwd: Path | str, *, owner: str = "local", create: bool = True) -> SpaceSnapshot | None: ...
    async def resolve_worktree(self, worktree_id: WorktreeId, *, owner: str = "local") -> ResolvedWorktree | None: ...
```

## Task 1: Add git and plain directory detection

**Files:**

- Create: `api/src/transport_matters/space/detection.py`
- Create: `api/src/transport_matters/space/test_detection.py`

### Step 1: Write the failing tests

Create `api/src/transport_matters/space/test_detection.py` with this complete content:

```python
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from transport_matters.space.detection import SpaceDetectionError, detect_space, repo_instance_key
from transport_matters.workspace import workspace_id


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _init_repo(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test User")
    (path / "README.md").write_text("root\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "initial")
    return path


def test_plain_directory_detects_single_primary_degenerate_worktree(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()

    detected = detect_space(plain)
    expected_workspace = workspace_id(plain)

    assert detected.name == "plain"
    assert detected.primary_path == plain.resolve()
    assert detected.repo_instance_key is None
    assert detected.git_common_dir is None
    assert len(detected.worktrees) == 1
    worktree = detected.worktrees[0]
    assert worktree.path == plain.resolve()
    assert worktree.workspace_slug == expected_workspace.slug
    assert worktree.workspace_hash == expected_workspace.hash
    assert worktree.branch_name is None
    assert worktree.head_oid is None
    assert worktree.is_primary is True
    assert worktree.missing is False


def test_git_repository_detects_all_worktrees_with_branch_head_and_primary(
    tmp_path: Path,
) -> None:
    repo = _init_repo(tmp_path / "repo")
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", "-b", "feature", str(linked), "HEAD")

    detected = detect_space(repo)
    common_dir = (repo / ".git").resolve()

    assert detected.repo_instance_key == repo_instance_key(common_dir)
    assert detected.git_common_dir == common_dir
    paths = {item.path for item in detected.worktrees}
    assert paths == {repo.resolve(), linked.resolve()}
    by_path = {item.path: item for item in detected.worktrees}
    assert by_path[repo.resolve()].branch_name == "main"
    assert by_path[linked.resolve()].branch_name == "feature"
    assert by_path[repo.resolve()].head_oid == by_path[linked.resolve()].head_oid
    assert by_path[repo.resolve()].is_primary is True
    assert by_path[linked.resolve()].is_primary is False


def test_relative_git_common_dir_is_resolved_against_target_cwd_not_process_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path / "repo")
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)

    detected = detect_space(repo)

    assert Path.cwd() == other
    assert detected.git_common_dir == (repo / ".git").resolve()
    assert detected.repo_instance_key == repo_instance_key(repo / ".git")
    assert detected.worktrees[0].is_primary is True


def test_missing_path_is_a_structured_detection_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    with pytest.raises(SpaceDetectionError) as exc_info:
        detect_space(missing)

    assert exc_info.value.code == "missing_path"
    assert exc_info.value.details == {"cwd": str(missing)}


def test_git_unavailable_is_a_structured_detection_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()

    def raise_missing(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", raise_missing)

    with pytest.raises(SpaceDetectionError) as exc_info:
        detect_space(plain)

    assert exc_info.value.code == "git_unavailable"


def test_git_timeout_is_a_structured_detection_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()

    def raise_timeout(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(["git"], timeout=0.01)

    monkeypatch.setattr(subprocess, "run", raise_timeout)

    with pytest.raises(SpaceDetectionError) as exc_info:
        detect_space(plain, timeout_s=0.01)

    assert exc_info.value.code == "git_timeout"
```

### Step 2: Run the tests and confirm the expected failure

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/space/test_detection.py
```

Expected failure:

```text
ModuleNotFoundError: No module named 'transport_matters.space.detection'
```

### Step 3: Add the minimal implementation

Create `api/src/transport_matters/space/detection.py` with this complete content:

```python
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from transport_matters.workspace import workspace_id

GIT_TIMEOUT_S = 2.0


@dataclass(frozen=True)
class SpaceDetectionError(RuntimeError):
    code: str
    message: str
    details: dict[str, object]

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class DetectedWorktree:
    path: Path
    workspace_slug: str
    workspace_hash: str
    branch_name: str | None
    head_oid: str | None
    is_primary: bool
    missing: bool = False


@dataclass(frozen=True)
class DetectedSpace:
    name: str
    primary_path: Path
    repo_instance_key: str | None
    git_common_dir: Path | None
    worktrees: tuple[DetectedWorktree, ...]


def repo_instance_key(git_common_dir: Path) -> str:
    resolved = git_common_dir.expanduser().resolve(strict=False)
    return sha256(resolved.as_posix().encode("utf-8")).hexdigest()


def detect_space(cwd: Path | str, *, timeout_s: float = GIT_TIMEOUT_S) -> DetectedSpace:
    target = Path(cwd).expanduser()
    if not target.exists():
        raise SpaceDetectionError("missing_path", f"cwd does not exist: {target}", {"cwd": str(target)})
    if not target.is_dir():
        raise SpaceDetectionError("invalid_cwd", f"cwd is not a directory: {target}", {"cwd": str(target)})
    resolved_target = target.resolve()
    probe = _run_git(
        resolved_target,
        (
            "rev-parse",
            "--is-inside-work-tree",
            "--show-toplevel",
            "--git-common-dir",
            "--git-dir",
        ),
        timeout_s=timeout_s,
        allow_failure=True,
    )
    if probe.returncode != 0:
        return _plain_space(resolved_target)
    lines = probe.stdout.splitlines()
    if len(lines) < 4 or lines[0].strip() != "true":
        return _plain_space(resolved_target)

    toplevel = _resolve_git_path(lines[1], base=resolved_target)
    common_dir = _resolve_git_path(lines[2], base=resolved_target)
    worktrees = _detect_git_worktrees(toplevel, common_dir=common_dir, timeout_s=timeout_s)
    primary_path = _primary_path_from_worktrees(worktrees) or toplevel
    return DetectedSpace(
        name=primary_path.name,
        primary_path=primary_path,
        repo_instance_key=repo_instance_key(common_dir),
        git_common_dir=common_dir,
        worktrees=worktrees or (_worktree_from_path(toplevel, primary_path=toplevel, branch_name=None, head_oid=None),),
    )


def _plain_space(cwd: Path) -> DetectedSpace:
    workspace = workspace_id(cwd)
    return DetectedSpace(
        name=cwd.name,
        primary_path=cwd,
        repo_instance_key=None,
        git_common_dir=None,
        worktrees=(
            DetectedWorktree(
                path=cwd,
                workspace_slug=workspace.slug,
                workspace_hash=workspace.hash,
                branch_name=None,
                head_oid=None,
                is_primary=True,
            ),
        ),
    )


def _detect_git_worktrees(
    toplevel: Path, *, common_dir: Path, timeout_s: float
) -> tuple[DetectedWorktree, ...]:
    result = _run_git(
        toplevel,
        ("worktree", "list", "--porcelain", "-z"),
        timeout_s=timeout_s,
        allow_failure=False,
    )
    records = _parse_porcelain_z(result.stdout)
    primary_path = _primary_worktree_path(records, common_dir=common_dir) or toplevel
    worktrees: list[DetectedWorktree] = []
    for record in records:
        raw_path = record.get("worktree")
        if raw_path is None:
            continue
        path = Path(raw_path).expanduser().resolve(strict=False)
        worktrees.append(
            _worktree_from_path(
                path,
                primary_path=primary_path,
                branch_name=_branch_from_record(record),
                head_oid=record.get("HEAD"),
                missing=not path.exists(),
            )
        )
    return tuple(worktrees)


def _worktree_from_path(
    path: Path,
    *,
    primary_path: Path,
    branch_name: str | None,
    head_oid: str | None,
    missing: bool = False,
) -> DetectedWorktree:
    workspace = workspace_id(path)
    return DetectedWorktree(
        path=path,
        workspace_slug=workspace.slug,
        workspace_hash=workspace.hash,
        branch_name=branch_name,
        head_oid=head_oid,
        is_primary=path == primary_path,
        missing=missing,
    )


def _run_git(
    cwd: Path,
    args: tuple[str, ...],
    *,
    timeout_s: float,
    allow_failure: bool,
) -> subprocess.CompletedProcess[str]:
    argv = ["git", *args]
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_s,
        )
    except FileNotFoundError as exc:
        raise SpaceDetectionError(
            "git_unavailable",
            "git executable is unavailable",
            {"cwd": str(cwd), "argv": argv},
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise SpaceDetectionError(
            "git_timeout",
            "git probe timed out",
            {"cwd": str(cwd), "argv": argv, "timeout_s": timeout_s},
        ) from exc
    if result.returncode != 0 and not allow_failure:
        raise SpaceDetectionError(
            "git_probe_failed",
            result.stderr.strip() or "git probe failed",
            {"cwd": str(cwd), "argv": argv, "returncode": result.returncode},
        )
    return result


def _resolve_git_path(value: str, *, base: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve(strict=False)


def _parse_porcelain_z(output: str) -> tuple[dict[str, str], ...]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for item in output.split("\0"):
        if item == "":
            if current:
                records.append(current)
                current = {}
            continue
        key, separator, value = item.partition(" ")
        current[key] = value if separator else ""
    if current:
        records.append(current)
    return tuple(records)


def _primary_worktree_path(records: tuple[dict[str, str], ...], *, common_dir: Path) -> Path | None:
    # For a normal repository, the primary Worktree is the record whose .git
    # directory is the common dir. Linked worktrees have .git under the common
    # dir's worktrees/ subdirectory. Bare repositories have a "bare" record and
    # no working tree, so the first non-bare path is used by callers as fallback.
    for record in records:
        raw_path = record.get("worktree")
        if raw_path is None or "bare" in record:
            continue
        path = Path(raw_path).expanduser().resolve(strict=False)
        if (path / ".git").resolve(strict=False) == common_dir:
            return path
    for record in records:
        raw_path = record.get("worktree")
        if raw_path is not None and "bare" not in record:
            return Path(raw_path).expanduser().resolve(strict=False)
    return None


def _primary_path_from_worktrees(worktrees: tuple[DetectedWorktree, ...]) -> Path | None:
    for worktree in worktrees:
        if worktree.is_primary:
            return worktree.path
    return None


def _branch_from_record(record: dict[str, Any]) -> str | None:
    raw = record.get("branch")
    if not isinstance(raw, str) or not raw:
        return None
    return raw.removeprefix("refs/heads/")
```

### Step 4: Run the tests and confirm the expected pass

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/space/test_detection.py
```

Expected pass:

```text
6 passed
```

### Step 5: Commit

Run:

```bash
git add api/src/transport_matters/space/detection.py api/src/transport_matters/space/test_detection.py && git commit -m "feat(spaces): detect git and plain spaces"
```

## Task 2: Add the async Space store and tier 1 cache

**Files:**

- Create: `api/src/transport_matters/space/store.py`
- Create: `api/src/transport_matters/space/test_store.py`
- Modify: `api/conftest.py` for the shared `space_store` fixture if cross-module fixture visibility is needed by later slices.

### Step 1: Write the failing store tests

Create `api/src/transport_matters/space/test_store.py` with this complete content:

```python
from __future__ import annotations

import json
from pathlib import Path

from transport_matters.space.detection import DetectedSpace, DetectedWorktree, repo_instance_key
from transport_matters.space.store import SpaceStore
from transport_matters.session.pool import create_async_pool
from transport_matters.session.testing import TestDb
from transport_matters.workspace import workspace_id


def _detected_worktree(
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
    detected_worktrees = [_detected_worktree(root, branch="main", head="abc123", is_primary=True)]
    detected_worktrees.extend(
        _detected_worktree(path, branch=f"feature-{index}", head="abc123")
        for index, path in enumerate(worktrees, start=1)
    )
    return DetectedSpace(
        name="repo",
        primary_path=root.resolve(strict=False),
        repo_instance_key=repo_instance_key(common_dir),
        git_common_dir=common_dir.resolve(strict=False),
        worktrees=tuple(detected_worktrees),
    )


async def test_store_mints_git_space_reuses_identity_reconciles_and_writes_cache(
    test_db: TestDb,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    linked = tmp_path / "linked"
    repo.mkdir()
    linked.mkdir()
    storage = tmp_path / "storage"

    async with create_async_pool(test_db.database_url, min_size=1, max_size=2) as pool:
        async with pool.connection() as conn:
            store = SpaceStore(conn, storage_dir=storage)
            first = await store.upsert_detection(_git_detection(repo, linked))
            second = await store.upsert_detection(_git_detection(repo))
            resolved = await store.resolve_worktree(first.worktrees[0].worktree_id)
            fetched_worktree = await store.get_worktree(first.worktrees[0].worktree_id)

    assert second.space.space_id == first.space.space_id
    assert second.git_identity is not None
    assert second.git_identity.repo_instance_key == repo_instance_key(repo / ".git")
    assert second.git_identity.space_id == first.space.space_id
    by_path = {item.path: item for item in second.worktrees}
    assert by_path[str(repo.resolve())].is_primary is True
    assert by_path[str(repo.resolve())].branch_name == "main"
    assert by_path[str(repo.resolve())].head_oid == "abc123"
    assert by_path[str(linked.resolve())].missing is True
    assert resolved is not None
    assert fetched_worktree is not None
    assert fetched_worktree.worktree_id == first.worktrees[0].worktree_id
    assert resolved.space_id == first.space.space_id
    assert resolved.worktree_id == first.worktrees[0].worktree_id
    assert resolved.cwd == str(repo.resolve())

    cache_root = storage / "spaces" / str(first.space.space_id)
    assert json.loads((cache_root / "space.json").read_text(encoding="utf-8"))["space_id"] == str(
        first.space.space_id
    )
    cached_worktrees = json.loads((cache_root / "worktrees.json").read_text(encoding="utf-8"))
    assert {item["path"] for item in cached_worktrees} == {str(repo.resolve()), str(linked.resolve())}
    assert [item for item in cached_worktrees if item["is_primary"]] == [
        next(item for item in cached_worktrees if item["path"] == str(repo.resolve()))
    ]


async def test_plain_directory_uses_no_git_identity_row(test_db: TestDb, tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    detection = DetectedSpace(
        name="plain",
        primary_path=plain.resolve(),
        repo_instance_key=None,
        git_common_dir=None,
        worktrees=(_detected_worktree(plain, is_primary=True),),
    )

    async with create_async_pool(test_db.database_url, min_size=1, max_size=2) as pool:
        async with pool.connection() as conn:
            snapshot = await SpaceStore(conn, storage_dir=tmp_path / "storage").upsert_detection(detection)
            identity_count = (
                await conn.execute("SELECT count(*) FROM space_git_identity")
            ).fetchone()["count"]

    assert snapshot.git_identity is None
    assert identity_count == 0
    assert snapshot.worktrees[0].path == str(plain.resolve())
    assert snapshot.worktrees[0].is_primary is True


async def test_resolve_cwd_can_lookup_without_create(test_db: TestDb, tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()

    async with create_async_pool(test_db.database_url, min_size=1, max_size=2) as pool:
        async with pool.connection() as conn:
            store = SpaceStore(conn, storage_dir=tmp_path / "storage")
            assert await store.resolve_cwd(plain, create=False) is None
            created = await store.resolve_cwd(plain, create=True)
            found = await store.resolve_cwd(plain, create=False)

    assert created is not None
    assert found is not None
    assert found.space.space_id == created.space.space_id
    assert found.worktrees[0].worktree_id == created.worktrees[0].worktree_id


async def test_canvas_methods_are_owner_scoped(test_db: TestDb, tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()

    async with create_async_pool(test_db.database_url, min_size=1, max_size=2) as pool:
        async with pool.connection() as conn:
            store = SpaceStore(conn, storage_dir=tmp_path / "storage")
            snapshot = await store.resolve_cwd(plain, create=True)
            assert snapshot is not None
            canvas = await store.create_canvas(
                snapshot.space.space_id,
                owner="local",
                name="Main canvas",
                default_worktree_id=snapshot.worktrees[0].worktree_id,
                layout={"panes": []},
            )
            hidden = await store.get_space_snapshot(snapshot.space.space_id, owner="other")
            canvases = await store.list_canvases(snapshot.space.space_id, owner="local")
            updated = await store.update_canvas(canvas.canvas_id, owner="local", name="Renamed")

    assert hidden is None
    assert [item.canvas_id for item in canvases] == [canvas.canvas_id]
    assert updated is not None
    assert updated.name == "Renamed"
```

Add this shared fixture to `api/conftest.py` so later slice tests can request `space_store` from any module:

```python
from collections.abc import AsyncIterator

import pytest

from transport_matters.session.pool import create_async_pool
from transport_matters.session.testing import TestDb
from transport_matters.space.store import SpaceStore


@pytest.fixture
async def space_store() -> AsyncIterator[SpaceStore]:
    test_db = TestDb.create()
    try:
        test_db.migrate()
        async with create_async_pool(test_db.database_url, min_size=1, max_size=1) as pool:
            async with pool.connection() as conn:
                yield SpaceStore(conn)
    finally:
        test_db.drop()
```

### Step 2: Run the tests and confirm the expected failure

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/space/test_store.py
```

Expected failure:

```text
ModuleNotFoundError: No module named 'transport_matters.space.store'
```

### Step 3: Add the minimal store implementation

Create `api/src/transport_matters/space/store.py` with this complete content:

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from transport_matters.config import get_settings
from transport_matters.space.detection import DetectedSpace, detect_space
from transport_matters.space.models import (
    Canvas,
    CanvasId,
    ResolvedWorktree,
    Space,
    SpaceGitIdentity,
    SpaceId,
    Worktree,
    WorktreeId,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from psycopg import AsyncConnection
    from psycopg.rows import DictRow


@dataclass(frozen=True)
class SpaceSummary:
    space: Space
    git_identity: SpaceGitIdentity | None
    worktrees: tuple[Worktree, ...]


@dataclass(frozen=True)
class SpaceSnapshot:
    space: Space
    git_identity: SpaceGitIdentity | None
    worktrees: tuple[Worktree, ...]
    canvases: tuple[Canvas, ...] = ()


class SpaceStore:
    def __init__(self, conn: AsyncConnection[DictRow], *, storage_dir: Path | None = None) -> None:
        self._conn = conn
        self._storage_dir = storage_dir or get_settings().storage_dir

    async def resolve_cwd(
        self,
        cwd: Path | str,
        *,
        owner: str = "local",
        create: bool = True,
    ) -> SpaceSnapshot | None:
        detection = detect_space(Path(cwd))
        if create:
            return await self.upsert_detection(detection, owner=owner)
        return await self._find_detection(detection, owner=owner)

    async def upsert_detection(self, detection: DetectedSpace, *, owner: str = "local") -> SpaceSnapshot:
        space = await self._lookup_space_for_detection(detection, owner=owner)
        if space is None:
            space = await self._insert_space(owner=owner, name=detection.name)
        if detection.repo_instance_key is not None and detection.git_common_dir is not None:
            await self._upsert_git_identity(space.space_id, detection)
        seen_paths: list[str] = []
        for detected in detection.worktrees:
            seen_paths.append(str(detected.path))
            await self._upsert_worktree(space.space_id, detected, owner=owner)
        if detection.repo_instance_key is not None:
            await self._mark_missing_worktrees(space.space_id, owner=owner, active_paths=seen_paths)
        snapshot = await self.get_space_snapshot(space.space_id, owner=owner)
        if snapshot is None:
            raise RuntimeError("space disappeared after upsert")
        self._write_cache(snapshot)
        return snapshot

    async def list_spaces(self, *, owner: str = "local", limit: int = 50, offset: int = 0) -> list[SpaceSummary]:
        rows = (
            await self._conn.execute(
                """
                SELECT s.space_id, s.owner, s.name, s.archived, s.created_at, s.updated_at,
                       gi.repo_instance_key, gi.git_common_dir, gi.detected_at
                FROM space AS s
                LEFT JOIN space_git_identity AS gi ON gi.space_id = s.space_id
                WHERE s.owner = %(owner)s
                ORDER BY s.updated_at DESC, s.name, s.space_id
                LIMIT %(limit)s OFFSET %(offset)s
                """,
                {"owner": owner, "limit": limit, "offset": offset},
            )
        ).fetchall()
        summaries: list[SpaceSummary] = []
        for row in rows:
            space = _space_from_row(row)
            worktrees = tuple(await self.list_worktrees(space.space_id, owner=owner))
            summaries.append(SpaceSummary(space, _identity_from_row(row), worktrees))
        return summaries

    async def get_space_snapshot(self, space_id: SpaceId, *, owner: str = "local") -> SpaceSnapshot | None:
        row = (
            await self._conn.execute(
                """
                SELECT s.space_id, s.owner, s.name, s.archived, s.created_at, s.updated_at,
                       gi.repo_instance_key, gi.git_common_dir, gi.detected_at
                FROM space AS s
                LEFT JOIN space_git_identity AS gi ON gi.space_id = s.space_id
                WHERE s.space_id = %(space_id)s AND s.owner = %(owner)s
                """,
                {"space_id": space_id.into_uuid(), "owner": owner},
            )
        ).fetchone()
        if row is None:
            return None
        return SpaceSnapshot(
            space=_space_from_row(row),
            git_identity=_identity_from_row(row),
            worktrees=tuple(await self.list_worktrees(space_id, owner=owner)),
            canvases=tuple(await self.list_canvases(space_id, owner=owner)),
        )

    async def update_space(
        self,
        space_id: SpaceId,
        *,
        owner: str = "local",
        name: str | None = None,
        archived: bool | None = None,
    ) -> Space | None:
        row = (
            await self._conn.execute(
                """
                UPDATE space
                SET name = COALESCE(%(name)s, name),
                    archived = COALESCE(%(archived)s, archived),
                    updated_at = now()
                WHERE space_id = %(space_id)s AND owner = %(owner)s
                RETURNING space_id, owner, name, archived, created_at, updated_at
                """,
                {"space_id": space_id.into_uuid(), "owner": owner, "name": name, "archived": archived},
            )
        ).fetchone()
        return _space_from_row(row) if row is not None else None

    async def list_worktrees(self, space_id: SpaceId, *, owner: str = "local") -> list[Worktree]:
        rows = (
            await self._conn.execute(
                """
                SELECT worktree_id, space_id, owner, path, workspace_slug, workspace_hash,
                       branch_name, head_oid, is_primary, missing, archived,
                       detected_at, created_at, updated_at
                FROM space_worktree
                WHERE space_id = %(space_id)s AND owner = %(owner)s
                ORDER BY is_primary DESC, missing, path NULLS LAST, workspace_slug, workspace_hash
                """,
                {"space_id": space_id.into_uuid(), "owner": owner},
            )
        ).fetchall()
        return [_worktree_from_row(row) for row in rows]

    async def get_worktree(self, worktree_id: WorktreeId, *, owner: str = "local") -> Worktree | None:
        row = (
            await self._conn.execute(
                """
                SELECT worktree_id, space_id, owner, path, workspace_slug, workspace_hash,
                       branch_name, head_oid, is_primary, missing, archived,
                       detected_at, created_at, updated_at
                FROM space_worktree
                WHERE worktree_id = %(worktree_id)s AND owner = %(owner)s
                """,
                {"worktree_id": worktree_id.into_uuid(), "owner": owner},
            )
        ).fetchone()
        return _worktree_from_row(row) if row is not None else None

    async def resolve_worktree(self, worktree_id: WorktreeId, *, owner: str = "local") -> ResolvedWorktree | None:
        worktree = await self.get_worktree(worktree_id, owner=owner)
        if worktree is None or worktree.path is None:
            return None
        return ResolvedWorktree(
            space_id=worktree.space_id,
            worktree_id=worktree.worktree_id,
            cwd=worktree.path,
            workspace_slug=worktree.workspace_slug,
            workspace_hash=worktree.workspace_hash,
            missing=worktree.missing,
            archived=worktree.archived,
        )

    async def list_canvases(self, space_id: SpaceId, *, owner: str = "local") -> list[Canvas]:
        rows = (
            await self._conn.execute(
                """
                SELECT canvas_id, space_id, owner, name, default_worktree_id, layout,
                       layout_version, archived, created_at, updated_at
                FROM canvas
                WHERE space_id = %(space_id)s AND owner = %(owner)s
                ORDER BY updated_at DESC, name, canvas_id
                """,
                {"space_id": space_id.into_uuid(), "owner": owner},
            )
        ).fetchall()
        return [_canvas_from_row(row) for row in rows]

    async def create_canvas(
        self,
        space_id: SpaceId,
        *,
        owner: str = "local",
        name: str,
        default_worktree_id: WorktreeId | None = None,
        layout: dict[str, Any] | None = None,
    ) -> Canvas:
        canvas_id = CanvasId.new()
        row = (
            await self._conn.execute(
                """
                INSERT INTO canvas (canvas_id, space_id, owner, name, default_worktree_id, layout)
                VALUES (%(canvas_id)s, %(space_id)s, %(owner)s, %(name)s, %(default_worktree_id)s, %(layout)s::jsonb)
                RETURNING canvas_id, space_id, owner, name, default_worktree_id, layout,
                          layout_version, archived, created_at, updated_at
                """,
                {
                    "canvas_id": canvas_id.into_uuid(),
                    "space_id": space_id.into_uuid(),
                    "owner": owner,
                    "name": name,
                    "default_worktree_id": _uuid_or_none(default_worktree_id),
                    "layout": json.dumps(layout or {}),
                },
            )
        ).fetchone()
        return _canvas_from_row(row)

    async def update_canvas(
        self,
        canvas_id: CanvasId,
        *,
        owner: str = "local",
        name: str | None = None,
        default_worktree_id: WorktreeId | None = None,
        layout: dict[str, Any] | None = None,
        archived: bool | None = None,
    ) -> Canvas | None:
        row = (
            await self._conn.execute(
                """
                UPDATE canvas
                SET name = COALESCE(%(name)s, name),
                    default_worktree_id = COALESCE(%(default_worktree_id)s, default_worktree_id),
                    layout = COALESCE(%(layout)s::jsonb, layout),
                    archived = COALESCE(%(archived)s, archived),
                    updated_at = now()
                WHERE canvas_id = %(canvas_id)s AND owner = %(owner)s
                RETURNING canvas_id, space_id, owner, name, default_worktree_id, layout,
                          layout_version, archived, created_at, updated_at
                """,
                {
                    "canvas_id": canvas_id.into_uuid(),
                    "owner": owner,
                    "name": name,
                    "default_worktree_id": _uuid_or_none(default_worktree_id),
                    "layout": json.dumps(layout) if layout is not None else None,
                    "archived": archived,
                },
            )
        ).fetchone()
        return _canvas_from_row(row) if row is not None else None

    async def _find_detection(self, detection: DetectedSpace, *, owner: str) -> SpaceSnapshot | None:
        space = await self._lookup_space_for_detection(detection, owner=owner)
        if space is None:
            return None
        return await self.get_space_snapshot(space.space_id, owner=owner)

    async def _lookup_space_for_detection(self, detection: DetectedSpace, *, owner: str) -> Space | None:
        if detection.repo_instance_key is not None:
            row = (
                await self._conn.execute(
                    """
                    SELECT s.space_id, s.owner, s.name, s.archived, s.created_at, s.updated_at
                    FROM space AS s
                    JOIN space_git_identity AS gi ON gi.space_id = s.space_id
                    WHERE gi.repo_instance_key = %(repo_instance_key)s AND s.owner = %(owner)s
                    """,
                    {"repo_instance_key": detection.repo_instance_key, "owner": owner},
                )
            ).fetchone()
            return _space_from_row(row) if row is not None else None
        first = detection.worktrees[0]
        row = (
            await self._conn.execute(
                """
                SELECT s.space_id, s.owner, s.name, s.archived, s.created_at, s.updated_at
                FROM space AS s
                JOIN space_worktree AS w ON w.space_id = s.space_id
                WHERE s.owner = %(owner)s
                  AND w.owner = %(owner)s
                  AND w.workspace_slug = %(workspace_slug)s
                  AND w.workspace_hash = %(workspace_hash)s
                """,
                {"owner": owner, "workspace_slug": first.workspace_slug, "workspace_hash": first.workspace_hash},
            )
        ).fetchone()
        return _space_from_row(row) if row is not None else None

    async def _insert_space(self, *, owner: str, name: str) -> Space:
        space_id = SpaceId.new()
        row = (
            await self._conn.execute(
                """
                INSERT INTO space (space_id, owner, name)
                VALUES (%(space_id)s, %(owner)s, %(name)s)
                RETURNING space_id, owner, name, archived, created_at, updated_at
                """,
                {"space_id": space_id.into_uuid(), "owner": owner, "name": name},
            )
        ).fetchone()
        return _space_from_row(row)

    async def _upsert_git_identity(self, space_id: SpaceId, detection: DetectedSpace) -> None:
        await self._conn.execute(
            """
            INSERT INTO space_git_identity (space_id, repo_instance_key, git_common_dir)
            VALUES (%(space_id)s, %(repo_instance_key)s, %(git_common_dir)s)
            ON CONFLICT (repo_instance_key) DO UPDATE SET
                space_id = EXCLUDED.space_id,
                git_common_dir = EXCLUDED.git_common_dir,
                detected_at = now()
            """,
            {
                "space_id": space_id.into_uuid(),
                "repo_instance_key": detection.repo_instance_key,
                "git_common_dir": str(detection.git_common_dir),
            },
        )

    async def _upsert_worktree(self, space_id: SpaceId, detected: Any, *, owner: str) -> Worktree:
        row = (
            await self._conn.execute(
                """
                INSERT INTO space_worktree (
                    worktree_id, space_id, owner, path, workspace_slug, workspace_hash,
                    branch_name, head_oid, is_primary, missing, archived
                ) VALUES (
                    %(worktree_id)s, %(space_id)s, %(owner)s, %(path)s, %(workspace_slug)s,
                    %(workspace_hash)s, %(branch_name)s, %(head_oid)s, %(is_primary)s, %(missing)s, false
                )
                ON CONFLICT (owner, workspace_slug, workspace_hash) DO UPDATE SET
                    space_id = EXCLUDED.space_id,
                    path = EXCLUDED.path,
                    branch_name = EXCLUDED.branch_name,
                    head_oid = EXCLUDED.head_oid,
                    is_primary = EXCLUDED.is_primary,
                    missing = EXCLUDED.missing,
                    archived = false,
                    detected_at = now(),
                    updated_at = now()
                RETURNING worktree_id, space_id, owner, path, workspace_slug, workspace_hash,
                          branch_name, head_oid, is_primary, missing, archived,
                          detected_at, created_at, updated_at
                """,
                {
                    "worktree_id": WorktreeId.new().into_uuid(),
                    "space_id": space_id.into_uuid(),
                    "owner": owner,
                    "path": str(detected.path),
                    "workspace_slug": detected.workspace_slug,
                    "workspace_hash": detected.workspace_hash,
                    "branch_name": detected.branch_name,
                    "head_oid": detected.head_oid,
                    "is_primary": detected.is_primary,
                    "missing": detected.missing,
                },
            )
        ).fetchone()
        return _worktree_from_row(row)

    async def _mark_missing_worktrees(self, space_id: SpaceId, *, owner: str, active_paths: Sequence[str]) -> None:
        await self._conn.execute(
            """
            UPDATE space_worktree
            SET missing = true, is_primary = false, updated_at = now()
            WHERE space_id = %(space_id)s
              AND owner = %(owner)s
              AND path IS NOT NULL
              AND NOT (path = ANY(%(active_paths)s::text[]))
            """,
            {"space_id": space_id.into_uuid(), "owner": owner, "active_paths": list(active_paths)},
        )

    def _write_cache(self, snapshot: SpaceSnapshot) -> None:
        root = self._storage_dir / "spaces" / str(snapshot.space.space_id)
        _atomic_json(root / "space.json", _space_cache_payload(snapshot))
        _atomic_json(root / "worktrees.json", [item.model_dump(mode="json") for item in snapshot.worktrees])


def _space_from_row(row: Mapping[str, Any]) -> Space:
    return Space(
        space_id=SpaceId.from_uuid(row["space_id"]),
        owner=row["owner"],
        name=row["name"],
        archived=row["archived"],
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _identity_from_row(row: Mapping[str, Any]) -> SpaceGitIdentity | None:
    if row.get("repo_instance_key") is None:
        return None
    return SpaceGitIdentity(
        space_id=SpaceId.from_uuid(row["space_id"]),
        repo_instance_key=row["repo_instance_key"],
        git_common_dir=row["git_common_dir"],
        detected_at=row.get("detected_at"),
    )


def _worktree_from_row(row: Mapping[str, Any]) -> Worktree:
    return Worktree(
        worktree_id=WorktreeId.from_uuid(row["worktree_id"]),
        space_id=SpaceId.from_uuid(row["space_id"]),
        owner=row["owner"],
        path=row["path"],
        workspace_slug=row["workspace_slug"],
        workspace_hash=row["workspace_hash"],
        branch_name=row["branch_name"],
        head_oid=row["head_oid"],
        is_primary=row["is_primary"],
        missing=row["missing"],
        archived=row["archived"],
        detected_at=row.get("detected_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _canvas_from_row(row: Mapping[str, Any]) -> Canvas:
    return Canvas(
        canvas_id=CanvasId.from_uuid(row["canvas_id"]),
        space_id=SpaceId.from_uuid(row["space_id"]),
        owner=row["owner"],
        name=row["name"],
        default_worktree_id=(
            WorktreeId.from_uuid(row["default_worktree_id"])
            if row["default_worktree_id"] is not None
            else None
        ),
        layout=row["layout"] or {},
        layout_version=row["layout_version"],
        archived=row["archived"],
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _uuid_or_none(value: WorktreeId | None) -> object | None:
    return value.into_uuid() if value is not None else None


def _space_cache_payload(snapshot: SpaceSnapshot) -> dict[str, object]:
    payload = snapshot.space.model_dump(mode="json")
    payload["git_identity"] = (
        snapshot.git_identity.model_dump(mode="json") if snapshot.git_identity is not None else None
    )
    return payload


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)
```

### Step 4: Run the store tests and confirm the expected pass

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/space/test_store.py
```

Expected pass:

```text
4 passed
```

### Step 5: Run the slice gates

Run the repo recipes, not hand assembled substitutes:

```bash
just check && just test
```

Expected pass:

```text
just check exits 0
just test exits 0
```

### Step 6: Commit

Run:

```bash
git add api/src/transport_matters/space/store.py api/src/transport_matters/space/test_store.py && git commit -m "feat(spaces): persist detected spaces"
```
