# Slice 1: Identity + schema foundation Implementation Plan

**Goal:** Freeze the Spaces identity and persistence foundation without changing runtime behavior. Later slices cite the exact type names, DTO fields, table names, constraints, and session link columns from this slice.

**Architecture:** Add typed uuid4 identifiers and Pydantic DTOs in `space/models.py` (a new `space/` package mirroring the existing `session/` package). Add additive Alembic schema objects for `space`, `space_git_identity`, `space_worktree`, `canvas`, and soft nullable `session.space_id` plus `session.worktree_id` columns. Space cluster foreign keys cascade inside the cluster. Session links stay soft and nullable so history survives Space lifecycle changes.

**Tech Stack:** Python 3.14, Pydantic v2, pydantic-core custom schemas, FastAPI DTO conventions, psycopg3, Alembic, Postgres native `uuid`, pytest, repo gates `just check` and `just test`.

**Frozen contracts:** `SpaceId`, `WorktreeId`, `CanvasId`, `Space`, `SpaceGitIdentity`, `Worktree` (incl. `branch_name`, `head_oid`, `is_primary`), `Canvas`, `ResolvedWorktree`; tables `space`, `space_git_identity`, `space_worktree`, `canvas`; session columns `space_id`, `worktree_id`; indexes `session_space_ix`, `session_worktree_ix`.

**Casing contract:** these are internal domain models and serialize **snake_case**. The public `/v1/` wire is **camelCase** — Slice 3 response DTOs (`SpaceSummary`, `WorktreeSummary`, `CanvasSummary`) project these domain models through the existing camelCase alias convention (`RunViewModel`'s `serialization_alias`), mapping e.g. `Space.name→label`, `Worktree.branch_name→branch`, `Worktree.is_primary→isPrimary`, and deriving `SpaceSummary.kind ∈ {"repo","plain"}` from the presence of a `space_git_identity` row (there is **no** `kind` column).

## Task 1: Add typed Space, Worktree, and Canvas model contracts

**Files:**

- Create: `api/src/transport_matters/space/__init__.py` (empty package marker)
- Create: `api/src/transport_matters/space/models.py`
- Create: `api/src/transport_matters/space/test_models.py`

### Step 1: Create the package marker and write the failing test

Create an empty `api/src/transport_matters/space/__init__.py` so `transport_matters.space` is an importable package, mirroring `transport_matters/session/`.

Then create `api/src/transport_matters/space/test_models.py` with this complete content:

```python
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from transport_matters.space.models import (
    Canvas,
    CanvasId,
    ResolvedWorktree,
    Space,
    SpaceId,
    Worktree,
    WorktreeId,
    shortest_unambiguous_prefix,
)

FIXED_UUID = UUID("12345678-1234-4234-9234-123456789abc")


class IdEnvelope(BaseModel):
    space_id: SpaceId
    worktree_id: WorktreeId
    canvas_id: CanvasId


def test_space_ids_are_uuid4_backed_and_dump_to_bare_strings() -> None:
    generated = SpaceId.new()

    assert generated.as_uuid().version == 4

    envelope = IdEnvelope(
        space_id=SpaceId.from_uuid(FIXED_UUID),
        worktree_id=WorktreeId.from_uuid(FIXED_UUID),
        canvas_id=CanvasId.from_uuid(FIXED_UUID),
    )

    assert envelope.space_id.as_uuid() == FIXED_UUID
    assert envelope.model_dump() == {
        "space_id": "12345678-1234-4234-9234-123456789abc",
        "worktree_id": "12345678-1234-4234-9234-123456789abc",
        "canvas_id": "12345678-1234-4234-9234-123456789abc",
    }
    assert envelope.model_dump_json() == (
        '{"space_id":"12345678-1234-4234-9234-123456789abc",'
        '"worktree_id":"12345678-1234-4234-9234-123456789abc",'
        '"canvas_id":"12345678-1234-4234-9234-123456789abc"}'
    )


def test_ids_validate_from_uuid_instances_and_uuid_strings() -> None:
    envelope = IdEnvelope(
        space_id=FIXED_UUID,
        worktree_id=str(FIXED_UUID),
        canvas_id=CanvasId.from_uuid(FIXED_UUID),
    )

    assert envelope.space_id == SpaceId.from_uuid(FIXED_UUID)
    assert envelope.worktree_id == WorktreeId.from_uuid(FIXED_UUID)
    assert envelope.canvas_id == CanvasId.from_uuid(FIXED_UUID)


def test_short_prefix_helper_matches_littleorgans_floor() -> None:
    space_id = SpaceId.from_uuid(FIXED_UUID)

    assert shortest_unambiguous_prefix(str(space_id), lambda _: True) == "1234567"
    assert shortest_unambiguous_prefix(str(space_id), lambda candidate: len(candidate) == 9) == (
        "12345678-"
    )
    assert shortest_unambiguous_prefix("abc", lambda _: True) == "abc"
    assert space_id.short() == "1234567"
    assert space_id.short_with(lambda candidate: len(candidate) == 9) == "12345678-"


def test_space_worktree_canvas_models_are_frozen_pydantic_rows() -> None:
    space_id = SpaceId.from_uuid(FIXED_UUID)
    worktree_id = WorktreeId.from_uuid(UUID("aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa"))
    canvas_id = CanvasId.from_uuid(UUID("bbbbbbbb-bbbb-4bbb-9bbb-bbbbbbbbbbbb"))

    space = Space(space_id=space_id, name="Transport Matters")
    worktree = Worktree(
        worktree_id=worktree_id,
        space_id=space_id,
        path="/repo/main",
        workspace_slug="transport-matters",
        workspace_hash="hash-main",
    )
    canvas = Canvas(
        canvas_id=canvas_id,
        space_id=space_id,
        name="Main canvas",
        default_worktree_id=worktree_id,
        layout={"panes": []},
    )

    assert space.model_dump()["space_id"] == str(space_id)
    assert worktree.model_dump()["worktree_id"] == str(worktree_id)
    assert canvas.model_dump()["default_worktree_id"] == str(worktree_id)


def test_resolved_worktree_freezes_run_handoff_contract() -> None:
    resolved = ResolvedWorktree(
        space_id=SpaceId.from_uuid(FIXED_UUID),
        worktree_id=WorktreeId.from_uuid(UUID("aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa")),
        cwd="/repo/main",
        workspace_slug="transport-matters",
        workspace_hash="hash-main",
        missing=False,
        archived=False,
    )

    assert resolved.model_dump() == {
        "space_id": "12345678-1234-4234-9234-123456789abc",
        "worktree_id": "aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa",
        "cwd": "/repo/main",
        "workspace_slug": "transport-matters",
        "workspace_hash": "hash-main",
        "missing": False,
        "archived": False,
    }
```

### Step 2: Run the test and confirm the expected failure

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/space/test_models.py
```

Expected failure:

```text
ModuleNotFoundError: No module named 'transport_matters.space.models'
```

### Step 3: Add the minimal implementation

Create `api/src/transport_matters/space/models.py` with this complete content:

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic_core import core_schema

MIN_SHORT_PREFIX_LEN = 7
JsonObject = dict[str, Any]


def shortest_unambiguous_prefix(full_id: str, is_unique: Callable[[str], bool]) -> str:
    min_len = min(MIN_SHORT_PREFIX_LEN, len(full_id))
    for length in range(min_len, len(full_id) + 1):
        candidate = full_id[:length]
        if is_unique(candidate):
            return candidate
    return full_id


class _UuidId:
    __slots__ = ("_value",)

    def __init__(self, value: UUID) -> None:
        self._value = value

    @classmethod
    def new(cls) -> Self:
        return cls(uuid4())

    @classmethod
    def from_uuid(cls, value: UUID) -> Self:
        return cls(value)

    @classmethod
    def parse(cls, value: str) -> Self:
        return cls(UUID(value))

    def as_uuid(self) -> UUID:
        return self._value

    def into_uuid(self) -> UUID:
        return self._value

    def short(self, is_unique: Callable[[str], bool] | None = None) -> str:
        return shortest_unambiguous_prefix(str(self), is_unique or (lambda _: True))

    def short_with(self, is_unique: Callable[[str], bool]) -> str:
        return self.short(is_unique)

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f"{type(self).__name__}('{self}')"

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, _UuidId)
            and type(self) is type(other)
            and self._value == other._value
        )

    def __hash__(self) -> int:
        return hash((type(self), self._value))

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source: type[Any],
        _handler: Any,
    ) -> core_schema.CoreSchema:
        def validate(value: object) -> Self:
            if isinstance(value, cls):
                return value
            if isinstance(value, UUID):
                return cls.from_uuid(value)
            if isinstance(value, str):
                return cls.parse(value)
            raise ValueError(f"{cls.__name__} must be a UUID or UUID string")

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda value: str(value),
                return_schema=core_schema.str_schema(),
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _schema: core_schema.CoreSchema,
        _handler: Any,
    ) -> dict[str, Any]:
        return {"type": "string", "format": "uuid"}


class SpaceId(_UuidId):
    pass


class WorktreeId(_UuidId):
    pass


class CanvasId(_UuidId):
    pass


class Space(BaseModel):
    model_config = ConfigDict(frozen=True)

    space_id: SpaceId
    owner: str = "local"
    name: str
    archived: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SpaceGitIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)

    space_id: SpaceId
    repo_instance_key: str
    git_common_dir: str
    detected_at: datetime | None = None


class Worktree(BaseModel):
    model_config = ConfigDict(frozen=True)

    worktree_id: WorktreeId
    space_id: SpaceId
    owner: str = "local"
    path: str | None = None
    workspace_slug: str
    workspace_hash: str
    branch_name: str | None = None
    head_oid: str | None = None
    is_primary: bool = False
    missing: bool = False
    archived: bool = False
    detected_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Canvas(BaseModel):
    model_config = ConfigDict(frozen=True)

    canvas_id: CanvasId
    space_id: SpaceId
    owner: str = "local"
    name: str
    default_worktree_id: WorktreeId | None = None
    layout: JsonObject = Field(default_factory=dict)
    layout_version: int = 1
    archived: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ResolvedWorktree(BaseModel):
    model_config = ConfigDict(frozen=True)

    space_id: SpaceId
    worktree_id: WorktreeId
    cwd: str
    workspace_slug: str
    workspace_hash: str
    missing: bool
    archived: bool
```

### Step 4: Run the test and confirm the expected pass

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/space/test_models.py
```

Expected pass:

```text
5 passed
```

### Step 5: Run the slice gate

Run the repo recipes (not hand-assembled substitutes):

```bash
cd api && just check && just test
```

Expected: both exit 0. The `_UuidId.__eq__` narrows on `isinstance(other, _UuidId)` before reading `other._value`, so `mypy` (part of `just check`) is clean.

### Step 6: Commit

Run:

```bash
git add api/src/transport_matters/space/__init__.py api/src/transport_matters/space/models.py api/src/transport_matters/space/test_models.py && git commit -m "feat(spaces): add identity model contracts"
```

## Task 2: Add the Spaces foundation migration and downgrade proof

**Files:**

- Create: `api/migrations/versions/0006_spaces_foundation.py`
- Modify: `api/src/transport_matters/session/test_migrate.py`

### Step 1: Write the failing migration tests

In `api/src/transport_matters/session/test_migrate.py`, extend the existing constants near the top of the file with this complete block:

```python
_SPACES_TABLES = frozenset({"space", "space_git_identity", "space_worktree", "canvas"})
_SPACES_SESSION_COLUMNS = frozenset({"space_id", "worktree_id"})
_SPACES_SESSION_INDEXES = frozenset({"session_space_ix", "session_worktree_ix"})
_SPACES_UUID_COLUMNS = frozenset(
    {
        ("space", "space_id"),
        ("space_git_identity", "space_id"),
        ("space_worktree", "space_id"),
        ("space_worktree", "worktree_id"),
        ("canvas", "canvas_id"),
        ("canvas", "space_id"),
        ("canvas", "default_worktree_id"),
        ("session", "space_id"),
        ("session", "worktree_id"),
    }
)
_SPACES_TEXT_COLUMNS = frozenset(
    {
        ("session", "session_id"),
        ("session", "run_id"),
        ("session", "workspace_slug"),
        ("session", "workspace_hash"),
        ("space_worktree", "workspace_slug"),
        ("space_worktree", "workspace_hash"),
    }
)
_SPACE_CASCADE_FKS = frozenset(
    {
        "space_git_identity_space_fk",
        "space_worktree_space_fk",
        "canvas_space_fk",
    }
)
```

Replace `_reset_to_unmigrated` with this complete implementation:

```python
def _reset_to_unmigrated(database_url: str) -> None:
    with connect(database_url, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS canvas CASCADE")
        conn.execute("DROP TABLE IF EXISTS space_worktree CASCADE")
        conn.execute("DROP TABLE IF EXISTS space_git_identity CASCADE")
        conn.execute("DROP TABLE IF EXISTS space CASCADE")
        conn.execute("DROP TABLE IF EXISTS event_dead_letter CASCADE")
        conn.execute("DROP TABLE IF EXISTS event_artifact CASCADE")
        conn.execute("DROP TABLE IF EXISTS event CASCADE")
        conn.execute("DROP TABLE IF EXISTS artifact CASCADE")
        conn.execute("DROP TABLE IF EXISTS session CASCADE")
        conn.execute("DROP TABLE IF EXISTS alembic_version")
```

Add these complete helpers below `_session_columns`:

```python
def _tables(database_url: str) -> frozenset[str]:
    with connect(database_url, autocommit=True) as conn:
        rows = conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            """
        ).fetchall()
    return frozenset(row["table_name"] for row in rows)


def _table_columns(database_url: str, table_name: str) -> dict[str, dict[str, str | None]]:
    with connect(database_url, autocommit=True) as conn:
        rows = conn.execute(
            """
            SELECT column_name, data_type, column_default, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            """,
            (table_name,),
        ).fetchall()
    return {
        row["column_name"]: {
            "data_type": row["data_type"],
            "column_default": row["column_default"],
            "is_nullable": row["is_nullable"],
        }
        for row in rows
    }


def _indexes(database_url: str, table_name: str) -> dict[str, str]:
    with connect(database_url, autocommit=True) as conn:
        rows = conn.execute(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = %s
            """,
            (table_name,),
        ).fetchall()
    return {row["indexname"]: row["indexdef"] for row in rows}


def _foreign_key_delete_actions(database_url: str) -> dict[str, str]:
    with connect(database_url, autocommit=True) as conn:
        rows = conn.execute(
            """
            SELECT conname, confdeltype
            FROM pg_constraint
            WHERE contype = 'f'
              AND connamespace = 'public'::regnamespace
            """
        ).fetchall()
    return {row["conname"]: row["confdeltype"] for row in rows}


def _assert_spaces_foundation_present(database_url: str) -> None:
    assert _tables(database_url) >= _SPACES_TABLES

    session_columns = _table_columns(database_url, "session")
    assert set(session_columns) >= _SPACES_SESSION_COLUMNS

    for table_name, column_name in _SPACES_UUID_COLUMNS:
        column = _table_columns(database_url, table_name)[column_name]
        assert column["data_type"] == "uuid"
        if column_name in {"space_id", "worktree_id", "canvas_id"}:
            assert column["column_default"] is None

    for table_name, column_name in _SPACES_TEXT_COLUMNS:
        assert _table_columns(database_url, table_name)[column_name]["data_type"] == "text"

    session_indexes = _indexes(database_url, "session")
    assert set(session_indexes) >= _SPACES_SESSION_INDEXES
    assert "WHERE (space_id IS NOT NULL)" in session_indexes["session_space_ix"]
    assert "WHERE (worktree_id IS NOT NULL)" in session_indexes["session_worktree_ix"]

    fks = _foreign_key_delete_actions(database_url)
    for fk_name in _SPACE_CASCADE_FKS:
        assert fks[fk_name] == "c"


def _assert_spaces_foundation_absent(database_url: str) -> None:
    assert _tables(database_url).isdisjoint(_SPACES_TABLES)
    assert _session_columns(database_url).isdisjoint(_SPACES_SESSION_COLUMNS)
    session_indexes = _indexes(database_url, "session")
    assert set(session_indexes).isdisjoint(_SPACES_SESSION_INDEXES)
```

Replace `test_alembic_upgrade_and_downgrade_smoke` with this complete implementation:

```python
def test_alembic_upgrade_and_downgrade_smoke(test_db: TestDb) -> None:
    _reset_to_unmigrated(test_db.database_url)

    migrate.apply_migrations(test_db.database_url)

    assert migrate.current_revision(test_db.database_url) == migrate.migration_head()
    assert migrate.current_revision(test_db.database_url) == "0006_spaces_foundation"
    _assert_spaces_foundation_present(test_db.database_url)
    _assert_tier1_indexes_present(test_db.database_url)
    _assert_dead_letter_present(test_db.database_url)
    _assert_session_classification_present(test_db.database_url)
    _assert_session_template_provenance_present(test_db.database_url)

    command.downgrade(migrate.alembic_config(test_db.database_url), "-1")

    assert migrate.current_revision(test_db.database_url) == "0005_session_template_provenance"
    _assert_spaces_foundation_absent(test_db.database_url)
    _assert_session_template_provenance_present(test_db.database_url)
    _assert_session_classification_present(test_db.database_url)
    _assert_dead_letter_present(test_db.database_url)
    _assert_tier1_indexes_present(test_db.database_url)

    command.downgrade(migrate.alembic_config(test_db.database_url), "-1")

    assert migrate.current_revision(test_db.database_url) == "0004_session_purpose_visibility"
    _assert_session_template_provenance_absent(test_db.database_url)
    _assert_session_classification_present(test_db.database_url)
    _assert_dead_letter_present(test_db.database_url)
    _assert_tier1_indexes_present(test_db.database_url)

    command.downgrade(migrate.alembic_config(test_db.database_url), "-1")

    assert migrate.current_revision(test_db.database_url) == "0003_event_dead_letter"
    _assert_session_classification_absent(test_db.database_url)
    _assert_dead_letter_present(test_db.database_url)
    _assert_tier1_indexes_present(test_db.database_url)

    command.downgrade(migrate.alembic_config(test_db.database_url), "-1")

    assert migrate.current_revision(test_db.database_url) == "0002_event_tier1_indexes"
    assert not _dead_letter_indexes(test_db.database_url)
    _assert_tier1_indexes_present(test_db.database_url)

    migrate.apply_migrations(test_db.database_url)

    assert migrate.current_revision(test_db.database_url) == migrate.migration_head()
    assert migrate.current_revision(test_db.database_url) == "0006_spaces_foundation"
    _assert_spaces_foundation_present(test_db.database_url)
    _assert_tier1_indexes_present(test_db.database_url)
    _assert_dead_letter_present(test_db.database_url)
    _assert_session_classification_present(test_db.database_url)
    _assert_session_template_provenance_present(test_db.database_url)
```

### Step 2: Run the test and confirm the expected failure

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/session/test_migrate.py -k alembic_upgrade_and_downgrade_smoke
```

Expected failure before the migration file exists:

```text
AssertionError: assert '0005_session_template_provenance' == '0006_spaces_foundation'
```

### Step 3: Add the minimal migration implementation

Create `api/migrations/versions/0006_spaces_foundation.py` with this complete content:

```python
"""spaces foundation

Revision ID: 0006_spaces_foundation
Revises: 0005_session_template_provenance
Create Date: 2026-06-21 06:30:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "0006_spaces_foundation"
down_revision = "0005_session_template_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE space (
            space_id uuid PRIMARY KEY,
            owner text NOT NULL DEFAULT 'local',
            name text NOT NULL,
            archived boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE space_git_identity (
            space_id uuid NOT NULL,
            repo_instance_key text NOT NULL,
            git_common_dir text NOT NULL,
            detected_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (space_id, repo_instance_key),
            CONSTRAINT space_git_identity_space_fk
                FOREIGN KEY (space_id) REFERENCES space(space_id) ON DELETE CASCADE,
            CONSTRAINT space_git_identity_repo_instance_key_uq UNIQUE (repo_instance_key)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE space_worktree (
            worktree_id uuid PRIMARY KEY,
            space_id uuid NOT NULL,
            owner text NOT NULL DEFAULT 'local',
            path text,
            workspace_slug text NOT NULL,
            workspace_hash text NOT NULL,
            branch_name text,
            head_oid text,
            is_primary boolean NOT NULL DEFAULT false,
            missing boolean NOT NULL DEFAULT false,
            archived boolean NOT NULL DEFAULT false,
            detected_at timestamptz NOT NULL DEFAULT now(),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT space_worktree_space_fk
                FOREIGN KEY (space_id) REFERENCES space(space_id) ON DELETE CASCADE,
            CONSTRAINT space_worktree_workspace_uq UNIQUE (owner, workspace_slug, workspace_hash),
            CONSTRAINT space_worktree_path_uq UNIQUE (owner, path)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE canvas (
            canvas_id uuid PRIMARY KEY,
            space_id uuid NOT NULL,
            owner text NOT NULL DEFAULT 'local',
            name text NOT NULL,
            default_worktree_id uuid,
            layout jsonb NOT NULL DEFAULT '{}'::jsonb,
            layout_version integer NOT NULL DEFAULT 1,
            archived boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT canvas_space_fk
                FOREIGN KEY (space_id) REFERENCES space(space_id) ON DELETE CASCADE,
            CONSTRAINT canvas_default_worktree_fk
                FOREIGN KEY (default_worktree_id)
                REFERENCES space_worktree(worktree_id)
                ON DELETE SET NULL
        )
        """
    )
    op.execute(
        """
        ALTER TABLE "session"
            ADD COLUMN space_id uuid,
            ADD COLUMN worktree_id uuid
        """
    )
    op.execute(
        """
        CREATE INDEX session_space_ix
        ON "session" (owner, space_id, started_at DESC)
        WHERE space_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX session_worktree_ix
        ON "session" (owner, worktree_id, started_at DESC)
        WHERE worktree_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX session_worktree_ix")
    op.execute("DROP INDEX session_space_ix")
    op.execute(
        """
        ALTER TABLE "session"
            DROP COLUMN worktree_id,
            DROP COLUMN space_id
        """
    )
    op.execute("DROP TABLE canvas")
    op.execute("DROP TABLE space_worktree")
    op.execute("DROP TABLE space_git_identity")
    op.execute("DROP TABLE space")
```

### Step 4: Run the migration test and confirm the expected pass

Run:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/session/test_migrate.py -k alembic_upgrade_and_downgrade_smoke
```

Expected pass:

```text
1 passed
```

Then run the full migration module because the head revision changed:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/session/test_migrate.py
```

Expected pass:

```text
7 passed
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
git add api/migrations/versions/0006_spaces_foundation.py api/src/transport_matters/session/test_migrate.py && git commit -m "feat(spaces): add schema foundation"
```
