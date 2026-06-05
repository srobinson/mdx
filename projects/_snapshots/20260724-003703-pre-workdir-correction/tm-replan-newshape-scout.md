# Transport Matters multilaunch replan seam inventory

Scope: read only inventory of `feat/multi-launch` at
`d7bfb9acbbb2bc193541fd8a18c2db73d07079b8`.

The tracked tree was clean when inspected. The active migration chain ends at
`0030_space_crud_reset`. Migration `0031_runtime_claim_and_session_affinity`
exists only on `archive/s2-claims`, so none of its tables or columns are current
tree facts.

## 1. Session creation and affinity stamp path

### Current session columns

| Requested stamp field | Current session column | Current source |
| --- | --- | --- |
| `space_id` | Yes, `text` | `0006_spaces_foundation.upgrade` adds `uuid`; `0030_space_crud_reset.upgrade` casts it to `text` |
| `worktree_id` | Yes, `uuid` | `0006_spaces_foundation.upgrade` |
| `canvas_id` | No | Absent from the active migration chain and session model |
| `parent_canvas_id` | No | Absent from the active migration chain and session model |
| `canvas_name` | No | Absent from the active migration chain and session model |
| `canvas_path` | No | Absent from the active migration chain and session model |
| `worktree_path` | No | Absent from the active migration chain and session model |
| `worktree_branch_name` | No | Absent from the active migration chain and session model |

Current model authority is
`api/src/transport_matters/session/models.py::SessionRow`. It carries only
`space_id` and `worktree_id` from this stamp set.

### Production session insert path

The live transcript path is:

```text
addon_runtime._start_session_capture.submit_events
  -> session.ingest.build_event_batch
  -> session.ingest.build_session
  -> session.writer.SessionWriter.submit
  -> session.writer.SessionWriter._commit_batch
  -> session.async_dao.AsyncSessionDao.upsert_session
  -> session.dao_statements.UPSERT_SESSION_SQL
```

`build_session` copies `space_id` and `worktree_id` from
`index.adapters.base.SessionBinding`. The DAO parameter map comes from
`session.dao_rows.session_params`.

Current upsert behavior is not write once. `UPSERT_SESSION_SQL` prefers a later
non null incoming value:

```sql
space_id = COALESCE(EXCLUDED.space_id, "session".space_id)
worktree_id = COALESCE(EXCLUDED.worktree_id, "session".worktree_id)
```

A true write once stamp must prefer the stored value, or perform a guarded
group update. The full stamp also needs one atomic policy so a later ingest
cannot combine values from different launch snapshots.

### Where launch identity currently goes

The launch stack resolves more identity than the session insert receives:

| Seam | Current behavior |
| --- | --- |
| `packages/runtime/src/server/runtimeRouter.ts::registerRunRoutes` | Accepts `spaceId` and `worktreeId`; accepts no `canvasId` |
| `packages/runtime/src/service/RunManager.ts::RunManager.createNew` | Sends space and worktree identity to capture prepare |
| `api/src/transport_matters/api/v1/capture_rpc_routes.py::PrepareCaptureRequest` | Accepts space and worktree identity; accepts no canvas identity |
| `api/src/transport_matters/api/v1/capture_rpc_routes.py::_resolved_domain_request` | Resolves and validates the launch Worktree |
| `api/src/transport_matters/capture_rpc.py::_CaptureRunFacts` | Retains space and worktree identity for run lifecycle emission |
| `api/src/transport_matters/run_lifecycle.py::build_run_lifecycle_event` | Writes space and worktree identity to `run_lifecycle_event` |
| `packages/runtime/src/service/RunManager.ts::RunManager.register` | Writes resolved space and worktree identity to `RuntimeRunView` |
| `api/src/transport_matters/api/v1/meta.py::_resolve_launch_worktree` | Returns the default space, worktree, and protected root Canvas to the client |

The handoff into transcript session creation loses that identity:

| Seam | Gap |
| --- | --- |
| `api/src/transport_matters/index/adapters/base.py::RunContext` | Has no space, worktree, or Canvas fields |
| `api/src/transport_matters/addon_runtime.py::_launch_run_context` | Builds `RunContext` without launch affinity |
| `api/src/transport_matters/index/adapters/claude.py::ClaudeAdapter.bind` | Cannot copy identity that `RunContext` does not carry |
| `api/src/transport_matters/index/adapters/codex.py::CodexAdapter.bind` | Same gap |
| `api/src/transport_matters/index/adapters/base.py::SessionBinding` | Supports space and worktree only; no Canvas stamp |

Key answer: launch space and Worktree identity is present in runtime views and
run lifecycle rows. It is not threaded through the live
launch to `SessionRow` path. Canvas identity has no session field or launch
request field. Current production session affinity is supplied after session
creation by startup backfill.

The narrow insertion seam for the new stamp is the trusted capture resolution
to `RunContext` and `SessionBinding` handoff, followed by `SessionRow` and
`UPSERT_SESSION_SQL`. Names and paths must come from the server resolved Canvas
and Worktree snapshot, rather than untrusted request strings.

## 2. `backfill_session_spaces`

`api/src/transport_matters/session/backfill.py::backfill_session_spaces` does
the following:

1. Calls
   `AsyncSessionDao.list_sessions_missing_space_identity`.
2. Reads the recorded `session.cwd`.
3. Calls `SpaceCrudService.resolve_session_cwd`.
4. Calls `AsyncSessionDao.update_session_space_identity` with the resolved
   `space_id` and `worktree_id`.

`SpaceCrudService.resolve_session_cwd` uses
`SpaceCrudService.resolve_cwd` for a present path. That path calls
`space.detection.detect_space`, reconciles detected Worktrees through
`SpaceCrudService.reconcile_detection`, and selects the containing Worktree.
A missing recorded path is materialized through
`SpaceCrudService._materialize_missing_worktree`.

The resolver returns `ResolvedWorktree.root_canvas_id`, but the backfill ignores
it. Current `canvas_id` is therefore effectively null because the session
column does not exist.

The DAO methods and SQL are:

| Purpose | DAO symbol | SQL symbol |
| --- | --- | --- |
| Find candidates | `AsyncSessionDao.list_sessions_missing_space_identity` | `LIST_SESSIONS_MISSING_SPACE_IDENTITY_SQL` |
| Write identity | `AsyncSessionDao.update_session_space_identity` | `UPDATE_SESSION_SPACE_IDENTITY_SQL` |

Startup calls `main._backfill_session_spaces` from
`main._start_session_backed_services`, after `main._resolve_current_space`.

The backfill can remain unchanged if every new launch writes both existing
identity fields before its first session upsert. Its candidate query selects a
row when either field is null, and its update sets both fields directly.

## 3. In process run stop seam

### Current ownership topology

The current FastAPI process has no `RunManager` on `app.state`.
`api/v1/test_exchanges_live_run_storage.py::test_gateway_owned_run_resolves_exchanges_and_meta_via_manifest`
asserts this cutover explicitly.

The Node Gateway owns
`packages/runtime/src/service/RunManager.ts::RunManager`. FastAPI stores the
Gateway proxy mount as `app.state.run_proxy_mount` in
`main.create_app`.

### What RunManager exposes

| Capability | Symbol | Detail |
| --- | --- | --- |
| List | `RunManager.list` | Owner scoped, with optional state, `spaceId`, and `worktreeId` filters |
| Stop one | `RunManager.terminate` | Stops by run ID and owner through the shared settle path |
| Stop all on shutdown | `RunManager.close` | Terminates every process resident managed run |
| HTTP list | `runtimeRouter.registerRunRoutes`, `GET /v1/runs` | Exposes the same space and Worktree filters |
| HTTP stop | `runtimeRouter.registerRunRoutes`, `POST /v1/runs/:runId/terminate` | Calls `RunManager.terminate` |
| Python stop adapter | `RunRouteProxy.terminate_run` | Typed request to the Gateway stop endpoint |

`domain/runtimeRun.ts::RuntimeRunView` stores `spaceId` and `worktreeId`.
`RunManager.register` fills them from the capture response, with the request as
fallback. A managed run has no `canvasId`, so the current runtime cannot list
or stop the runs bound to one exact Canvas.

`RunRouteProxy` also lacks a typed list method. Python hard delete code can
terminate a known run ID, but cannot currently request the affinity filtered
inventory through the typed port.

### Minimal best effort delete stop

For Worktree and Space deletion, the Gateway already has the necessary
identity and filter behavior:

1. List process resident runs by owner plus `worktreeId` or `spaceId`.
2. Call `RunManager.terminate` for each returned run.
3. Record or log failures, then continue the hard delete as specified.

The Python service boundary needs a typed list operation on `RunRouteProxy`, or
an equivalent run management port, before it can drive this sequence without
reaching into raw HTTP.

Exact Canvas stopping needs one additional identity seam. Add trusted
`canvasId` to managed run creation and `RuntimeRunView`, or maintain an
equivalent process resident binding index. Mapping a Canvas to its anchor
Worktree and stopping every Worktree run would stop unrelated sibling Canvas
runs.

Plain terminals are owned by
`packages/runtime/src/service/PlainTerminalSessions.ts::PlainTerminalSessions`,
outside `RunManager`, and carry no space, Worktree, or Canvas inventory in the
current tree.

## 4. Org delete cascades and session independence

### Active `0030` foreign keys

| Constraint | Relationship | Delete action |
| --- | --- | --- |
| `space_worktree_link_space_fk` | Space to membership link | `CASCADE` |
| `space_worktree_link_worktree_fk` | Worktree to membership link | `CASCADE` |
| `canvas_parent_fk` | Canvas parent to child Canvas | `CASCADE` |
| `canvas_anchor_worktree_fk` | Worktree to anchored Canvas | `CASCADE` |
| `canvas_default_worktree_fk` | Worktree to Canvas default selector | `NO ACTION`, deferred |
| `space_worktree_root_canvas_fk` | Protected root Canvas to Worktree | `NO ACTION`, deferred |

Migration authority is
`0030_space_crud_reset.upgrade`,
`0030_space_crud_reset._create_final_space_worktree`, and
`0030_space_crud_reset._create_final_canvas`.

Observed delete semantics are covered by:

| Delete | Current result | Regression symbol |
| --- | --- | --- |
| User Canvas | Descendant Canvas rows cascade | `0030_space_crud_reset._create_final_canvas`, constraint `canvas_parent_fk` |
| Protected root Canvas alone | Commit is rejected | `test_space_crud_migration.test_lone_root_delete_is_rejected_when_the_transaction_commits` |
| Worktree | Root Canvas, Canvas descendants, and membership links cascade | `test_space_crud_migration.test_worktree_delete_cascades_root_subtree_and_membership_then_commits` |
| Named Space | Membership links cascade; Worktrees and Canvases remain | `test_space_crud_migration.test_space_delete_cascades_membership_without_deleting_worktree` |

The current product surface has hard delete for named Spaces through
`SpaceCrudService.delete_space` and `SpaceStore.delete_space`. Canvas and
Worktree delete endpoints do not exist yet.

### Session stamp foreign keys

`0006_spaces_foundation.upgrade` adds `session.space_id` and
`session.worktree_id` without references. `0030_space_crud_reset.upgrade`
changes the `space_id` type without adding a reference.

The session affinity fields are therefore independent of Space, Worktree, and
Canvas rows. Org deletion cannot cascade into sessions and cannot be blocked by
session affinity. The session table does have a separate lineage self reference
through `parent_session_id`; that does not connect sessions to the org schema.

Run lifecycle space and Worktree fields are also free of org foreign keys.

## 5. S5 Worktree create and move

### Existing primitives

| Capability | Current symbol | Status |
| --- | --- | --- |
| Classify a path | `space.detection.classify_git_membership` | Present |
| Observe Git Worktrees | `space.detection.detect_space` and `space.detection._git_space` | Present, read only |
| Execute Git observation | `space.detection._run_git` | Private helper used for `git worktree list --porcelain -z` |
| Reconcile detection | `SpaceCrudService.reconcile_detection` | Present |
| Insert or refresh detected Worktree | `SpaceStore.upsert_worktree` | Present, always inserts `provenance='detected'` |
| Create protected root | `SpaceStore.ensure_worktree_root` | Present |
| Link named Space membership | `SpaceStore.add_worktree_link` | Present |
| Worktree create or move Git port | None | Missing |
| Worktree create or move REST and MCP command | None | Missing |

The schema and models already contain
`WorktreeProvenance.CREATED` and the `creating`, `active`, and `deleting`
lifecycle values. No current production command writes a created Worktree.

`SpaceStore.upsert_worktree` conflicts on owner plus workspace slug and hash.
Because workspace identity is path derived, a move cannot safely round trip
through the current detected insert path. It could mint a new Worktree ID and
root Canvas. An explicit move must update the existing row by Worktree ID and
preserve `worktree_id`, `root_canvas_id`, and `provenance`.

### Claim free create and move touch set

1. Add a neutral Git Worktree port with fixed argument create and move
   operations. Share its process runner with detection rather than duplicating
   Git execution policy.
2. Add command models to `space/models.py` and orchestration methods to
   `SpaceCrudService`.
3. Refactor `SpaceStore.upsert_worktree` into a shared materialization primitive
   that accepts the creation provenance for new rows while preserving
   provenance and root identity on refresh.
4. Add an identity preserving store update for move. It must update canonical
   path, workspace slug, and workspace hash for the same Worktree row.
5. Reuse `SpaceStore.ensure_worktree_root` and named Space membership methods.
6. Add REST routes in `api/v1/space_routes.py` and parity tools in
   `api/v1/space_mcp.py`.
7. Add unit tests for Git argument construction and failure mapping, database
   tests for stable Worktree and root Canvas identity, and REST plus MCP parity
   tests.

The active schema already holds provenance and stable identities, so a simple
create and move slice does not inherently require claim or lease tables.

`api/src/transport_matters/space/store.py` is currently 693 lines. The project
limit requires extraction before adding nontrivial store code.

## Top risks

1. Session creation drops trusted launch affinity even though capture and
   runtime already resolved space and Worktree identity.
2. Current session upsert prefers later incoming non null values, so it does
   not enforce write once semantics.
3. Canvas affinity is absent from the session schema, launch request, and
   runtime inventory.
4. FastAPI cannot list managed runs through its typed Gateway proxy, and there
   is no Python `app.state.run_manager`.
5. Worktree move cannot reuse the current path derived upsert without risking a
   new Worktree ID and protected root Canvas.
6. The store module is seven lines below the hard file size limit and must be
   decomposed before S5 implementation.
