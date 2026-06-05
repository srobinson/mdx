# S1 Affinity Stamp Spec Confirmation

Status: awaiting approval. No repository code has been written.

Sources:

- `~/.mdx/projects/tm-replan-newshape-architect.md`, S1
- Context Matters model of record `019f8a57-c947-7411-8944-be6d9ebfce0f`
- Live tree at `d7bfb9acbbb2bc193541fd8a18c2db73d07079b8`

## (a) Base verification

I ran `git fetch --prune origin`.

| Fact | Value |
| --- | --- |
| Local HEAD | `d7bfb9acbbb2bc193541fd8a18c2db73d07079b8` |
| `origin/main` | `d7bfb9acbbb2bc193541fd8a18c2db73d07079b8` |
| `HEAD...origin/main` | `0 0` |
| Merge base | `d7bfb9acbbb2bc193541fd8a18c2db73d07079b8` |
| Alembic head | `0030_space_crud_reset` |
| Tracked and untracked worktree status | clean |

The branch is based exactly on latest fetched `origin/main`. Fetch pruned the
deleted `origin/feat/multi-launch` remote tracking ref.

## (b) Session column contract

Fresh migration:
`0031_session_affinity_stamp`, down revision `0030_space_crud_reset`.

No migration data backfill. The runtime backfill owns historical rows.

### New columns

| Name | PostgreSQL type | Nullable |
| --- | --- | --- |
| `canvas_id` | `uuid` | yes |
| `parent_canvas_id` | `uuid` | yes |
| `canvas_name` | `text` | yes |
| `canvas_path` | `text` | yes |
| `worktree_path` | `text` | yes |
| `worktree_branch_name` | `text` | yes |

All six columns are bare and have no foreign keys. Hard deletion can leave the
snapshot intact.

### Complete eight column group

The new columns join the existing nullable columns:

| Name | PostgreSQL type | Nullable |
| --- | --- | --- |
| `space_id` | `text` | yes |
| `worktree_id` | `uuid` | yes |
| `canvas_id` | `uuid` | yes |
| `parent_canvas_id` | `uuid` | yes |
| `canvas_name` | `text` | yes |
| `canvas_path` | `text` | yes |
| `worktree_path` | `text` | yes |
| `worktree_branch_name` | `text` | yes |

The database columns are nullable because a session can have no affinity
snapshot. Within a present snapshot, `parent_canvas_id` can be null for a
Worktree root Canvas and `worktree_branch_name` can be null for a plain
directory, detached HEAD, missing checkout, or unavailable Git observation.
The other six values are required.

Incoming session writes will accept exactly two states:

1. No snapshot: all eight values are null.
2. Full snapshot: `space_id`, `worktree_id`, `canvas_id`, `canvas_name`,
   `canvas_path`, and `worktree_path` are present. The two legitimately nullable
   fields may be null.

The write boundary will reject a partial group before SQL execution. This
validation belongs on the upsert input path, rather than `SessionRow` database
read validation, so historical rows that currently contain only
`space_id` and `worktree_id` remain readable until runtime backfill repairs them.

## (c) Exact atomic group, write once upsert

`canvas_id` is the group presence sentinel. The application validation above
guarantees that an incoming non-null `canvas_id` carries the full required
snapshot.

This is the exact `UPSERT_SESSION_SQL` shape I will use. Existing non-affinity
assignments remain unchanged. Every affinity assignment uses the same guard.

```sql
INSERT INTO "session" (
    session_id, provider, harness, run_id, cwd, workspace_slug, workspace_hash,
    space_id, worktree_id, canvas_id, parent_canvas_id, canvas_name, canvas_path,
    worktree_path, worktree_branch_name, native_session_id, minted,
    source_descriptor, home_dir, template_provenance, owner, session_purpose,
    session_visibility, status, title, parent_session_id, forked_at_seq, started_at
) VALUES (
    %(session_id)s, %(provider)s, %(harness)s, %(run_id)s, %(cwd)s,
    %(workspace_slug)s, %(workspace_hash)s, %(space_id)s, %(worktree_id)s,
    %(canvas_id)s, %(parent_canvas_id)s, %(canvas_name)s, %(canvas_path)s,
    %(worktree_path)s, %(worktree_branch_name)s, %(native_session_id)s,
    %(minted)s, %(source_descriptor)s, %(home_dir)s, %(template_provenance)s,
    %(owner)s, %(session_purpose)s, %(session_visibility)s, %(status)s,
    %(title)s, %(parent_session_id)s, %(forked_at_seq)s, %(started_at)s
)
ON CONFLICT (session_id) DO UPDATE SET
    provider = EXCLUDED.provider,
    harness = COALESCE("session".harness, EXCLUDED.harness),
    run_id = EXCLUDED.run_id,
    cwd = COALESCE(NULLIF("session".cwd, ''), EXCLUDED.cwd),
    workspace_slug = EXCLUDED.workspace_slug,
    workspace_hash = EXCLUDED.workspace_hash,
    space_id = CASE
        WHEN "session".canvas_id IS NULL AND EXCLUDED.canvas_id IS NOT NULL
        THEN EXCLUDED.space_id
        ELSE "session".space_id
    END,
    worktree_id = CASE
        WHEN "session".canvas_id IS NULL AND EXCLUDED.canvas_id IS NOT NULL
        THEN EXCLUDED.worktree_id
        ELSE "session".worktree_id
    END,
    canvas_id = CASE
        WHEN "session".canvas_id IS NULL AND EXCLUDED.canvas_id IS NOT NULL
        THEN EXCLUDED.canvas_id
        ELSE "session".canvas_id
    END,
    parent_canvas_id = CASE
        WHEN "session".canvas_id IS NULL AND EXCLUDED.canvas_id IS NOT NULL
        THEN EXCLUDED.parent_canvas_id
        ELSE "session".parent_canvas_id
    END,
    canvas_name = CASE
        WHEN "session".canvas_id IS NULL AND EXCLUDED.canvas_id IS NOT NULL
        THEN EXCLUDED.canvas_name
        ELSE "session".canvas_name
    END,
    canvas_path = CASE
        WHEN "session".canvas_id IS NULL AND EXCLUDED.canvas_id IS NOT NULL
        THEN EXCLUDED.canvas_path
        ELSE "session".canvas_path
    END,
    worktree_path = CASE
        WHEN "session".canvas_id IS NULL AND EXCLUDED.canvas_id IS NOT NULL
        THEN EXCLUDED.worktree_path
        ELSE "session".worktree_path
    END,
    worktree_branch_name = CASE
        WHEN "session".canvas_id IS NULL AND EXCLUDED.canvas_id IS NOT NULL
        THEN EXCLUDED.worktree_branch_name
        ELSE "session".worktree_branch_name
    END,
    native_session_id = COALESCE("session".native_session_id, EXCLUDED.native_session_id),
    minted = "session".minted OR EXCLUDED.minted,
    source_descriptor = COALESCE("session".source_descriptor, EXCLUDED.source_descriptor),
    home_dir = COALESCE("session".home_dir, EXCLUDED.home_dir),
    template_provenance = COALESCE(
        "session".template_provenance,
        EXCLUDED.template_provenance
    ),
    owner = EXCLUDED.owner,
    session_purpose = COALESCE("session".session_purpose, EXCLUDED.session_purpose),
    session_visibility = COALESCE(
        "session".session_visibility,
        EXCLUDED.session_visibility
    ),
    status = EXCLUDED.status,
    title = COALESCE(EXCLUDED.title, "session".title),
    parent_session_id = COALESCE(
        "session".parent_session_id,
        EXCLUDED.parent_session_id
    ),
    forked_at_seq = COALESCE("session".forked_at_seq, EXCLUDED.forked_at_seq),
    updated_at = now()
RETURNING {SESSION_COLUMNS}
```

Properties:

- Insert stores a validated whole snapshot or eight nulls.
- The first full snapshot can fill a legacy or initially unstamped row.
- Once stored `canvas_id` is present, all eight `ELSE` branches select the
  stored values. Reingest cannot alter any stored affinity bytes, including a
  null parent or branch.
- A legacy row with only `space_id` and `worktree_id` is replaced by one full
  snapshot as a single SQL statement. No values survive from the partial group.
- PostgreSQL serializes conflicting row updates. Concurrent first writers
  cannot mix snapshots.
- Non-affinity fields retain current reingest behavior. `updated_at` can change;
  the eight affinity values remain byte unchanged.

### Runtime backfill SQL

Backfill remains a separate fill missing operation. Its candidate sentinel is
`canvas_id`, because the two nullable snapshot fields cannot indicate presence.

```sql
SELECT
    s.session_id,
    s.owner,
    s.workspace_slug || '/' || s.workspace_hash AS workspace_id,
    s.cwd
FROM "session" AS s
WHERE s.owner = %(owner)s
  AND s.canvas_id IS NULL
ORDER BY
    CASE WHEN NULLIF(btrim(s.cwd), '') IS NULL THEN 1 ELSE 0 END,
    s.updated_at NULLS LAST,
    s.session_id
LIMIT %(limit)s
```

The update writes the same full group and retains a database guard:

```sql
UPDATE "session"
SET space_id = %(space_id)s::text,
    worktree_id = %(worktree_id)s::uuid,
    canvas_id = %(canvas_id)s::uuid,
    parent_canvas_id = %(parent_canvas_id)s::uuid,
    canvas_name = %(canvas_name)s::text,
    canvas_path = %(canvas_path)s::text,
    worktree_path = %(worktree_path)s::text,
    worktree_branch_name = %(worktree_branch_name)s::text,
    updated_at = now()
WHERE owner = %(owner)s
  AND session_id = %(session_id)s
  AND canvas_id IS NULL
```

The final predicate closes the select to update race. A present snapshot always
wins.

## (d) Identity field set and server resolution

### Exact `RunContext` field set

Add:

```python
space_id: SpaceId | None = None
worktree_id: WorktreeId | None = None
canvas_id: CanvasId | None = None
parent_canvas_id: CanvasId | None = None
canvas_name: str | None = None
canvas_path: str | None = None
worktree_path: str | None = None
worktree_branch_name: str | None = None
```

### Exact `SessionBinding` field set

`SessionBinding` already has `space_id` and `worktree_id`. Its complete affinity
field set becomes:

```python
space_id: SpaceId | None = None
worktree_id: WorktreeId | None = None
canvas_id: CanvasId | None = None
parent_canvas_id: CanvasId | None = None
canvas_name: str | None = None
canvas_path: str | None = None
worktree_path: str | None = None
worktree_branch_name: str | None = None
```

`ClaudeAdapter.bind` and `CodexAdapter.bind` copy all eight values from
`RunContext` to `SessionBinding`. `build_session` then copies all eight to
`SessionRow`.

For a launch without a Canvas snapshot, `RunContext` and `SessionBinding` carry
eight nulls even if general run lifecycle facts know a Space or Worktree. This
keeps session affinity atomic.

### Server resolution symbol

Add one launch authority:

```python
api/v1/launch_resolution.py::resolve_run_affinity
```

It resolves one snapshot under one database connection:

1. Call `SpaceCrudService.resolve_launch_worktree` with the requested
   `worktree_id`, owner, and optional selected `space_id`.
2. Require the execution Worktree to be a member of the resolved Space, then
   apply the existing active and missing launch checks.
3. Call `SpaceCrudService.get_canvas` with
   `rest_caller(resolved.space_id, owner=owner)` and the requested `canvas_id`.
   This is the existing authoritative Canvas name and path projection.
4. Build the full snapshot from those returned records.

The Canvas anchor does not have to equal the execution Worktree. The model of
record permits pane execution placement in another Worktree. `get_canvas`
validates that the Canvas anchor is visible in the selected Space. The
membership correction below makes `resolve_launch_worktree` validate the
execution Worktree in that Space.

Snapshot sources:

| Field | Server source |
| --- | --- |
| `space_id` | `ResolvedWorktree.space_id` |
| `worktree_id` | `ResolvedWorktree.worktree_id` |
| `canvas_id` | `CanvasRecord.canvas_id` |
| `parent_canvas_id` | `CanvasRecord.parent_canvas_id` |
| `canvas_name` | `CanvasRecord.name` |
| `canvas_path` | canonical JSON text of `CanvasRecord.path` |
| `worktree_path` | `ResolvedWorktree.cwd` |
| `worktree_branch_name` | `ResolvedWorktree.branch_name` |

Caller supplied names, paths, branches, and snapshot launch fields are ignored.
The trusted snapshot is injected after continuation, runtime home, and caller
launch field merges.

### `canvas_path` resolution

The active Canvas domain already represents a path as:

```python
CanvasRecord.path: tuple[CanvasPathSegment, ...]
CanvasPathSegment { canvas_id, name, kind }
```

The REST and TypeScript representation is the corresponding JSON array:

```json
[
  {"canvasId":"<uuid>","name":"main","kind":"worktree_root"},
  {"canvasId":"<uuid>","name":"S1","kind":"user"}
]
```

Recommendation: store the compact, deterministic JSON serialization of that
existing array in the required `canvas_path text` column. Use aliases and JSON
mode, preserve segment order, use UTF-8, and use compact separators. This
mirrors `CanvasRecord.path` exactly. It avoids the lossy UI only rendering
`segment.name` values joined by `" / "`.

Rationale: the domain path contains identity, name, and kind per segment. A
joined display string would discard identity and kind and would require a new
escaping convention. The S1 architect explicitly fixes the database column as
`text`, so canonical JSON text preserves the existing representation without
changing the migration type.

### Worktree branch resolution

The live tree has no symbol named `detect_worktree_branch`. The existing branch
observation pipeline is:

```text
space/detection.py::_git_space
  -> git worktree list --porcelain -z
  -> _worktree_from_record
  -> _branch_from_record
  -> DetectedWorktree.branch_name
  -> space/projection.py::project_worktree
  -> ProjectedWorktree.branch_name
```

`_branch_from_record` removes `refs/heads/`. Detached, plain, missing, or
unobserved Worktrees yield null.

The value is currently lost in
`space/models.py::ResolvedWorktree.from_worktree`, which copies no
`branch_name`.

Recommendation: add `branch_name: str | None` to `ResolvedWorktree` and copy
`ProjectedWorktree.branch_name` in `from_worktree`.

Rationale: the observation already exists and is projected by the Space domain.
Threading it through the launch result is the smallest change and is directly
required by S1's frozen `worktree_branch_name` snapshot. Adding a second Git
branch detector would duplicate policy and could disagree with the Space
projection.

## (e) Reconciliation deltas

### 1. Canvas pane launch currently drops Canvas and Space

This gap is on the real browser Canvas pane path:

```text
CanvasStore.canvasId and CanvasStore.spaceId
  -> CanvasWorkbench
  -> CanvasPaneLayer
  -> ViewerCanvasContext
  -> viewers/registry.tsx
  -> CapturedRunPane
  -> useCapturedRunBinding
  -> capturedRunStore.ensureRun
  -> @tm/core createCapturedRunView
  -> POST /v1/runs
```

Current facts:

- `CanvasPaneLayer` receives `canvasId`.
- `CanvasStore` also owns `spaceId`.
- `ViewerCanvasContext` exposes `id` but omits `spaceId`.
- The captured run registry passes only `worktreeId`, agent, name, and
  continuation.
- `@tm/core::createCapturedRunView` sends `worktreeId` and no Canvas or Space.
- The runtime route can parse `spaceId`, but this browser caller never sends it.
- No runtime request type currently has `canvasId`.

Recommendation: forward `canvasId` and `spaceId` explicitly through this chain.
Add `spaceId` to `ViewerCanvasContext`; pass both values as typed props and
options through `CapturedRunPane`, `useCapturedRunBinding`,
`EnsureRunOptions`, and `CreateCapturedRunOptions`; then include both in
`POST /v1/runs`.

Rationale: the durable Canvas pane already has a server verified identity tuple
from `resolveCanvasLaunchIdentity`. Explicit forwarding preserves that selected
Space and Canvas. Reading global store state deep in the terminal component
would hide the dependency.

### 2. Runtime and capture request plumbing is wider than the architect list

Add `canvasId` through:

- `packages/runtime/src/server/runtimeRouter.ts::CreateRunBody`
- `packages/runtime/src/server/runtimeRouter.ts::registerRunRoutes`
- `packages/runtime/src/service/runManagerTypes.ts::CreateManagedRunInput`
- `packages/runtime/src/service/runManagerSupport.ts::createRunFingerprint`
- `packages/runtime/src/service/RunManager.ts::RunManager.createNew`
- `packages/runtime/src/ports.ts::PrepareCaptureInput`
- `packages/runtime/src/adapters/CaptureRpcClient.ts::prepareCaptureBody`
- `api/v1/capture_rpc_routes.py::PrepareCaptureRequest`
- `captured_run_models.py::CapturedRunRequest`

`canvasId` must join the idempotency fingerprint. Reusing an idempotency key for
a different Canvas must report a conflict rather than return a run created in
another Canvas.

The capture response and `RuntimeRunView` do not gain `canvasId` in S1. That is
the separate S4a contract.

### 3. Explicit Space launch resolution omits Worktree membership

`SpaceCrudService.resolve_launch_worktree` validates membership when
`space_id` is omitted and it chooses the default Space. When an explicit
`space_id` is supplied, it currently checks only that the Space exists, then
projects any owner scoped Worktree into that Space. This bypasses
`worktree_in_space`, the model of record's membership authority.

Recommendation: fix `resolve_launch_worktree` so both branches call
`_require_worktree_in_space` before projection. Cover the explicit Space case
inside the launch stamp test.

Rationale: a trusted S1 snapshot cannot claim a Space and execution Worktree
pair that has no membership row. Fixing the shared resolver also keeps current
Worktree launch and new affinity launch behavior aligned.

### 4. Trusted resolution must override a supplied directory

Current `_resolved_domain_request` resolves a Worktree only when
`directory is None`. A caller that supplies both a directory and IDs bypasses
Worktree resolution.

Recommendation: when `canvasId` is present, require `worktreeId` and call
`resolve_run_affinity` regardless of whether `directory` was supplied. Replace
the directory, Space, and Worktree with the resolved values before preparing
the run.

Rationale: S1 promises a server resolved snapshot. Request strings cannot remain
an alternate authority.

### 5. Affinity launch carrier must be reserved and typed

The captured provider invocation already serializes `launch_fields` through the
environment. Use one reserved nested field for the full snapshot, with a codec
owned by a neutral session affinity module. Before provider invocation, remove
any caller supplied value for that key, then write the trusted snapshot or
write no key.

Recommended new neutral owner:

```text
session/affinity.py
  SessionAffinityStamp
  validate_affinity_group
  serialize_canvas_path
  affinity_launch_fields
  affinity_from_launch_fields
```

Rationale: this keeps atomic validation, path serialization, and carrier
parsing single sourced across launch, addon, adapters, DAO, and backfill.

### 6. Proxy binding and shared proxy payload omit the snapshot

`ProxyRunBinding` currently defines only `space_id` and `worktree_id`.
`build_proxy_run_binding` does not populate even those two from settings.

Add the six remaining fields to:

- `shared_proxy/binding.py::ProxyRunBinding`
- `shared_proxy/models.py::SharedProxyBindingPayload`
- `shared_proxy/models.py::binding_payload_from_binding`
- `shared_proxy/addon.py::_runtime_binding_from_payload`

Populate the complete group in
`addon_runtime.py::build_proxy_run_binding` through the reserved affinity
codec. `_launch_run_context` copies the full group into `RunContext`.

General run lifecycle `space_id` and `worktree_id` remain usable when no
session affinity snapshot exists. The codec returns no session stamp unless
`canvas_id` is present and the group validates.

### 7. Owned cursor registration currently mixes arbitrary launch fields

`register_owned_cursor` currently applies `binding.launch_fields` directly to
`SessionBinding.model_copy`, then overlays `space_id` and `worktree_id`.

Recommendation: continue applying unrelated supported launch fields, but source
the eight affinity fields only from the validated `RunContext` copied by the
adapter. Exclude the reserved affinity key from arbitrary model updates.

Rationale: this preserves one trusted path and prevents caller launch metadata
from forging or partially replacing a session stamp.

### 8. Session read and write map

Add all eight columns through:

- `session/models.py::SessionRow`
- `session/ingest.py::build_session`
- `session/dao_rows.py::session_params`
- `session/dao_statements.py::SESSION_COLUMN_NAMES`
- `session/dao_statements.py::UPSERT_SESSION_SQL`
- `session/async_dao.py::AsyncSessionDao.upsert_session`

Use the neutral affinity validator on the upsert input. Database row decoding
must continue to accept legacy partial rows.

### 9. Backfill needs a Canvas lookup and branch threading

`backfill_session_spaces` currently receives `ResolvedWorktree.root_canvas_id`
and discards it. `ResolvedWorktree` also lacks the observed branch.

Recommendation:

1. Resolve the session cwd with
   `SpaceCrudService.resolve_session_cwd`.
2. Resolve the returned root Canvas through
   `SpaceCrudService.get_canvas(rest_caller(resolved.space_id), resolved.root_canvas_id)`.
3. Build the same canonical affinity snapshot used by launch resolution.
4. Update all eight columns under `WHERE canvas_id IS NULL`.

Rationale: historical sessions did not launch from a user Canvas, so the
resolved Worktree root is the honest Canvas snapshot. Reusing
`SpaceCrudService.get_canvas` provides the authoritative name and segment path.

### 10. Exact non-null and null behavior after S1

| Launch path | `canvas_id` at session ingest |
| --- | --- |
| Verified browser Canvas pane | non-null selected Canvas |
| Browser Canvas state with no durable verified `canvasId` | null full group |
| Control plane service launch | null full group |
| Direct local CLI `transport-matters claude` or `codex` | null full group |
| RPC caller with valid identity tuple | non-null resolved Canvas |
| Raw Runtime or capture RPC caller that omits `canvasId` | null full group |
| Backfilled resolvable row | non-null Worktree root Canvas |
| Unresolvable historical row | remains null |

The Canvas pane gap is a dropped identity, so S1 fixes it. Service and direct
CLI launches genuinely have no selected Canvas in their current contracts.
They remain unstamped at initial ingest and are eligible for root Canvas
backfill. S1 does not block those launches.

### 11. `parent_canvas_id` decision

The S1 body includes `parent_canvas_id`, while the architect's open decisions
still ask whether to stamp it now.

Recommendation: stamp it now.

Rationale: the field is already present on `CanvasRecord`, costs no additional
lookup, and belongs to the same immutable snapshot. Deferring it would either
create another migration and threading pass or leave the new column
systematically null for user Canvases. Approval of this confirmation should
lock the architect's `stamp-now` option.

### 12. File size threshold

Current relevant sizes:

| File | Lines |
| --- | ---: |
| `session/writer.py` | 682 |
| `session/dao_statements.py` | 677 |
| `packages/runtime/src/service/RunManager.ts` | 664 |

No relevant file is over 700 now. The new tests belong in
`test_session_affinity_stamp.py`, so `session/writer.py` needs no production
growth. `RunManager.ts` needs only the request forwarding line and remains
below the limit.

`dao_statements.py` has 23 lines of headroom and the exact SQL above will cross
700.

Recommendation: perform a narrow S1 Step 0 extraction of the session row SQL
constants into a focused module before adding the new query. Do not duplicate
constants. Keep `dao_statements.py` as the import facade if existing imports
require it.

Rationale: the repository rule makes 700 a hard threshold. The architect's
Step 0 assessment predates the live file count and cannot be followed without
crossing the limit.

## Tests first

After approval, write exactly the six architect tests before implementation:

1. `test_launch_stamps_canvas_identity_on_first_session`
2. `test_stamp_is_write_once_across_reingest`
3. `test_stamp_group_is_atomic_never_mixed`
4. `test_snapshot_survives_hard_delete_as_tombstone`
5. `test_backfill_fills_missing_canvas_only`
6. `test_session_stamp_migration`

Capture red evidence at base
`d7bfb9acbbb2bc193541fd8a18c2db73d07079b8`, implement S1 only, then run
`just check` and `just test-affected`.

## Approval locks requested

Approval of this document locks:

1. `canvas_path` as canonical JSON text mirroring
   `CanvasRecord.path: CanvasPathSegment[]`.
2. `ResolvedWorktree.branch_name` threading as part of S1, sourced from the
   existing Space Git observation pipeline.
3. Explicit Canvas and Space forwarding on durable browser Canvas pane
   launches.
4. Explicit Space launches validate the execution Worktree through
   `worktree_in_space`.
5. Null initial affinity for service, direct CLI, and any caller without a
   verified Canvas, followed by existing runtime backfill where resolvable.
6. `parent_canvas_id` stamped now.
7. The narrow session SQL extraction required to stay below 700 lines.

Implementation remains paused pending approval.
