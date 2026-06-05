# Canvas entity today (as-built dig)

Date: 2026-07-22  
Checkout: `feat/multi-launch` @ `b094e80d`  
Method: code reads (`rg` + file reads). fmm index absent in this worktree (no `.fmm.db`).  
No design. No edits.

---

## 1. SERVER MODEL

Source: `space.models`

### `space.models.Canvas`

Frozen Pydantic model (`ConfigDict(frozen=True)`). Identity hash on `canvas_id`.

| Field | Type | Default |
| --- | --- | --- |
| `canvas_id` | `CanvasId` (`_UuidId`) | required |
| `space_id` | `SpaceId` (`_UuidId`) | required |
| `owner` | `str` | `"local"` |
| `name` | `str` | required |
| `default_worktree_id` | `WorktreeId \| None` | `None` |
| `layout` | `JsonObject` (`dict[str, Any]`) | `Field(default_factory=dict)` |
| `layout_version` | `int` | `1` |
| `archived` | `bool` | `False` |
| `created_at` | `datetime \| None` | `None` |
| `updated_at` | `datetime \| None` | `None` |

**No** `parent_canvas_id` (or any tree/parent field) on the model.

### Container: `space.models.Space`

| Field | Type | Default |
| --- | --- | --- |
| `space_id` | `SpaceId` | required |
| `owner` | `str` | `"local"` |
| `name` | `str` | required |
| `archived` | `bool` | `False` |
| `created_at` | `datetime \| None` | `None` |
| `updated_at` | `datetime \| None` | `None` |

### Sibling: `space.models.Worktree`

| Field | Type | Default |
| --- | --- | --- |
| `worktree_id` | `WorktreeId` | required |
| `space_id` | `SpaceId` | required |
| `owner` | `str` | `"local"` |
| `path` | `str \| None` | `None` |
| `workspace_slug` | `str` | required |
| `workspace_hash` | `str` | required |
| `branch_name` | `str \| None` | `None` |
| `head_oid` | `str \| None` | `None` |
| `is_primary` | `bool` | `False` |
| `missing` | `bool` | `False` |
| `archived` | `bool` | `False` |
| `detected_at` | `datetime \| None` | `None` |
| `created_at` | `datetime \| None` | `None` |
| `updated_at` | `datetime \| None` | `None` |

ID wrappers: `SpaceId`, `WorktreeId`, `CanvasId` each subclass `space.models._UuidId`.

---

## 2. PERSISTENCE

### Table: `canvas`

Created only by Alembic `0006_spaces_foundation` (`revision = "0006_spaces_foundation"`).  
No later migration alters `canvas` (searched `ALTER TABLE canvas` / further `CREATE TABLE canvas`: none).

| Column | SQL type | Nullability | Default |
| --- | --- | --- | --- |
| `canvas_id` | `uuid` | NOT NULL, **PRIMARY KEY** | — |
| `space_id` | `uuid` | NOT NULL | — |
| `owner` | `text` | NOT NULL | `'local'` |
| `name` | `text` | NOT NULL | — |
| `default_worktree_id` | `uuid` | **nullable** | — |
| `layout` | `jsonb` | NOT NULL | `'{}'::jsonb` |
| `layout_version` | `integer` | NOT NULL | `1` |
| `archived` | `boolean` | NOT NULL | `false` |
| `created_at` | `timestamptz` | NOT NULL | `now()` |
| `updated_at` | `timestamptz` | NOT NULL | `now()` |

### Foreign keys

| Constraint | Definition | ON DELETE |
| --- | --- | --- |
| `canvas_space_fk` | `space_id` → `space(space_id)` | **CASCADE** |
| `canvas_default_worktree_fk` | `default_worktree_id` → `space_worktree(worktree_id)` | **SET NULL** |

Confirmed by migration SQL and by `session.test_migrate` invariants: `_SPACE_CASCADE_FKS` includes `canvas_space_fk`; `_SPACE_SET_NULL_FKS` = `{canvas_default_worktree_fk}`.

### Indexes on `canvas`

None beyond the primary key. No secondary index on `(space_id, owner)`, name, or archived.

### Server layout jsonb bag

- Column: **`layout`** (`jsonb NOT NULL DEFAULT '{}'::jsonb`)
- Model type: `JsonObject = dict[str, Any]` with comment that Any is for arbitrary jsonb layout payloads
- Store insert: `json.dumps(layout or {})`; update: full replace when provided (`COALESCE(%(layout)s::jsonb, layout)`)
- **No enforced shape** in DB or model: empty object by default; product pane layout does **not** sync here today (client owns panes in localStorage)

### Sibling tables (same migration)

- `space` (PK `space_id`)
- `space_git_identity` (FK → `space` CASCADE)
- `space_worktree` (PK `worktree_id`, FK → `space` CASCADE; unique `(owner, workspace_slug, workspace_hash)`, unique `(owner, path)`)

### Session columns added same migration

`session.space_id uuid` and `session.worktree_id uuid` (nullable, **no FK**), plus partial indexes `session_space_ix`, `session_worktree_ix`. **No** `session.canvas_id`.

### Current Alembic head

Linear chain ends at **`0029_native_connection_origin`** (`down_revision = "0028_wire_request_kind"`).  
Canvas-creating revision: **`0006_spaces_foundation`** only.

---

## 3. STORE API

Owner: `space.store.SpaceStore` (+ mapper `space.store._canvas_from_row`).

| Op | Exists? | Symbol |
| --- | --- | --- |
| List | yes | `SpaceStore.list_canvases` — by `space_id` + `owner`, order `updated_at DESC, name, canvas_id` |
| Create | yes | `SpaceStore.create_canvas` — mints `CanvasId.new()`, inserts name / optional `default_worktree_id` / layout |
| Update | yes | `SpaceStore.update_canvas` — COALESCE patch of `name`, `default_worktree_id`, `layout`, `archived`; bumps `updated_at` |
| Get one | **no** store method | Route-local only: `space_routes._require_canvas_space_id` runs `SELECT space_id FROM canvas WHERE canvas_id=… AND owner=…` for patch authz |
| Delete | **no** | No `delete_canvas` / hard-delete / archive-only dedicated delete path on the store |

Also loads canvases into snapshots via `list_canvases` (e.g. space snapshot assembly around the store).

REST skins (not store, for orientation): `space_routes.list_space_canvases`, `create_canvas`, `patch_canvas`. No REST get-one or delete.

---

## 4. RELATIONSHIPS AS-BUILT

| Edge | Cardinality | Mechanism |
| --- | --- | --- |
| Space → Canvas | **1:N** | `canvas.space_id` FK `canvas_space_fk` **ON DELETE CASCADE** |
| Space → Worktree | **1:N** | `space_worktree.space_id` FK `space_worktree_space_fk` **ON DELETE CASCADE** |
| Canvas → default Worktree | **N:0..1** | `canvas.default_worktree_id` FK `canvas_default_worktree_fk` **ON DELETE SET NULL** (nullable) |
| Canvas → parent Canvas | **absent** | No `parent_canvas_id` column, model field, store arg, or REST field |

**Confirmed:** `parent_canvas_id` does not appear in `api/` or `www/` production sources (only `canvas_id` as the Canvas PK / client key).

**Not enforced by FK:** default Worktree belonging to the same Space as the Canvas (route validates via `space_routes._require_worktree_in_space` on create/patch; DB does not).

**No server edge:** Canvas → panes, Canvas → runs, Session → Canvas.

---

## 5. CLIENT SHAPE

### `paneRecords.CanvasModel`

Source: `www/packages/canvas/src/model/paneRecords.ts::CanvasModel`

| Field | Type |
| --- | --- |
| `canvasId` | `CanvasId` (`string`) |
| `owner` | `"local"` (literal) |
| `spaceId` | `SpaceId \| null` |
| `workspaceHash` | `string \| null` |
| `defaultWorktreeId` | `WorktreeId \| null` |
| `cwd` | `string \| null` |
| `launch` | `CanvasLaunchContext` |
| `layout` | `EngineLayoutState` |
| `panes` | `Record<PaneId, PaneRecord>` |

### `paneRecords.PaneRecord`

| Field | Type |
| --- | --- |
| `paneId` | `PaneId` |
| `viewerId` | `ViewerId` |
| `title` | `string` |
| `contentRef` | `CanvasPaneRef` |
| `chromeState` | `PaneChromeState` |
| `createdAt` | `string` |
| `lastFocusedAt` | `string \| null` |

`CanvasPaneRef` union includes session-picker, dev-blank, session/subagent timelines, resource, provider-exchange, terminal (`worktreeId` required), captured-run (`worktreeId` + `runKey` required). **No canvas parent/tree field on panes.**

### Store extension: `canvasState.CanvasStoreModel`

Extends `CanvasModel` with: `activeStrategyId`, `bounds`, `fitToContent`, `params`, `framing`, `expandedPaneId`, `paneFlyIntent`, `docked`, `paneCounters`.

### localStorage key / version

| Item | Value | Symbol |
| --- | --- | --- |
| Base key registry | `"transport-matters-canvas"` | `CANVAS_STORAGE_KEYS.canvasStore` in `storageKeys` |
| Per-canvas key | `` `transport-matters-canvas:${canvasId}` `` | `canvasCacheStorage.canvasCacheKey` |
| Legacy bare key | `"transport-matters-canvas"` | `LEGACY_CANVAS_CACHE_KEY` (one-time import into per-canvas key) |
| Persist version | **`1`** | `canvasStore.persistence.CANVAS_STORE_STORAGE_VERSION` |
| Storage factory | namespaces zustand by live `getCanvasId()` | `createCanvasCacheStorage` |

Visible canvas identity can be synthetic (`route.defaultCanvasId`: explicit `canvas_id` query, else `space:<spaceId>`, else workspace hash / `direct-local`) — client keys are strings, not necessarily server UUIDs.

---

## 6. TRANSCRIPT / SESSION RECORD

### Table: `"session"`

Foundation: `0001_session_store` (+ later columns). Spaces identity: `0006_spaces_foundation` adds **`space_id`**, **`worktree_id`** only.

### Writer column set: `session.dao_statements.SESSION_COLUMN_NAMES`

```text
session_id, provider, harness, run_id, cwd, workspace_slug, workspace_hash,
space_id, worktree_id, native_session_id, minted, source_descriptor, home_dir,
template_provenance, owner, session_purpose, session_visibility, status, title,
parent_session_id, forked_at_seq, started_at, created_at, updated_at
```

**Confirmed: no `canvas_id`, no `parent_canvas_id` on session.**  
Upsert SQL (`UPSERT_SESSION_SQL`) coalesces `space_id` / `worktree_id` only for space identity.

### Related lifecycle (also no canvas FK)

`run_lifecycle_event` carries `space_id`, `worktree_id`, and `launch_kind` (enum includes string value `"canvas"` as a launch kind, not a Canvas entity id).

### Where a durable stamp would land

- Table: **`"session"`**
- Natural columns: new `canvas_id` and/or `parent_canvas_id` (neither exists)
- Migration would be **after current head** `0029_native_connection_origin`
- Session space/worktree today are **indexes without FKs** (`session_space_ix`, `session_worktree_ix`); any canvas stamp would need an explicit FK policy decision

---

## WHAT'S ABSENT (CRUD + tree + durable stamp must add)

**Absent today:** store/REST **get-by-id** and **delete**; any **canvas tree** (`parent_canvas_id` or equivalent); **session/transcript `canvas_id` (and parent) stamp**; secondary canvas indexes; DB-enforced same-Space default worktree; server↔client layout authority for panes (client localStorage is the live pane bag; server `layout` jsonb is an unconstrained bag).
