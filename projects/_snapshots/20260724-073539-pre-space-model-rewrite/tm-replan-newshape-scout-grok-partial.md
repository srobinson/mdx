> Complete scout dump from multi-launch:general:1:2.5 (grok) before stand-down. Same content as tm-replan-newshape-scout.md @ d7bfb9ac. Cross-ref only — gpt %67 owns further scout/dev.

# TM re-plan newshape scout

Tree: `feat/multi-launch` @ `d7bfb9ac` (S3/main; post Space-CRUD #317 + Canvas #318).  
Role: read-only seam inventory for plain write-once affinity stamp + simple deletes.  
S2 claim/lease/reconciler: **absent** (no `0031`, no claim tables).

---

## 1. Session creation / affinity stamp write path

### Columns that exist today

| Column | Present? | Source |
|---|---|---|
| `session.space_id` | YES (text after 0030 cast) | 0006 ADD uuid → 0030 `ALTER … TYPE text` |
| `session.worktree_id` | YES (uuid) | 0006 bare ADD |
| `canvas_id` | **NO** | — |
| `parent_canvas_id` | **NO** | — |
| `canvas_name` | **NO** | — |
| `canvas_path` | **NO** | — |
| `worktree_path` | **NO** | — |
| `worktree_branch_name` | **NO** | — |

**Migration 0031 does not exist on this tree.** Latest space-related migration is `0030_space_crud_reset.py`. The 8-column affinity stamp set from archived S2 is **not** shipped here.

Model: `SessionRow` / `SessionBinding` only carry `space_id` + `worktree_id`  
(`session/models.py:103-104`, `index/adapters/base.py:66-67`).

### Write path (production)

```
transcript/wire → EventBatch.session (SessionRow)
  → SessionWriter._commit_batch
  → AsyncSessionDao.upsert_session
  → UPSERT_SESSION_SQL
```

| Seam | Symbol | File |
|---|---|---|
| Build row from binding | `build_session` / `build_event_batch` | `session/ingest.py:69-115` |
| Writer commit | `SessionWriter._commit_batch` | `session/writer.py:396-402` |
| DAO | `AsyncSessionDao.upsert_session` | `session/async_dao.py:90-94` |
| SQL | `UPSERT_SESSION_SQL` | `session/dao_statements.py:101-137` |

Upsert semantics for identity: **first non-null wins** via  
`space_id = COALESCE(EXCLUDED.space_id, "session".space_id)` (same for `worktree_id`).  
Null later writes never clear a stamp; first null leaves room for a later non-null.

### Does launch identity flow into session create?

**Mostly no for session rows. Partial for run lifecycle.**

| Path | space/worktree threaded? | Evidence |
|---|---|---|
| Capture prepare accepts ids | YES on request | `CapturedRunRequest.space_id/worktree_id` (`captured_run_models.py:92-93`); routes resolve via `resolve_run_worktree` (`api/v1/capture_rpc_routes.py:307-318`, `api/v1/launch_resolution.py:30-72`) |
| CaptureLeaseRegistry facts | YES for lifecycle only | `_CaptureRunFacts.space_id/worktree_id` (`capture_rpc.py:123-124, 184-191`); `_emit_lifecycle` → `run_lifecycle_event` (`capture_rpc.py:382-383`) |
| ProxyRunBinding at prepare | **NO** | `build_proxy_run_binding` omits both (`addon_runtime.py:284-301`) |
| Live SessionBinding from wire | fields exist, usually **null** | `addon_runtime._make_exchange_cursor_sink` copies `binding.space_id/worktree_id` (`addon_runtime.py:232-233`) but builder never sets them |
| Historical run-dir replay | **NO** | `session/backfill._binding` omits space/worktree (`backfill.py:253-276`) |
| Startup backfill | YES (post-create) | `backfill_session_spaces` (see §2) |
| Meta default spawn target | YES (UI only) | `GET /v1/meta` → `resolve_session_cwd` returns space + worktree + **root canvas** (`api/v1/meta.py:132-167`) — not written to `session` |

**Answer to key question:** canvas/worktree/space identity is **resolved at launch surfaces** (meta, capture prepare, RunManager create filters) and stamped on **run_lifecycle_event**, but the **session create path does not currently receive a write-once affinity stamp from launch**. Session rows rely on:

1. optional null → later COALESCE fill if a future binding ever carries ids, and  
2. **startup backfill** from recorded `cwd`.

Canvas identity is never a session column and never written by backfill.

---

## 2. `backfill_session_spaces`

| Item | Detail |
|---|---|
| Function | `backfill_session_spaces` — `session/backfill.py:71-134` |
| Resolver | `SessionCwdResolver.resolve_session_cwd` → `SpaceCrudService.resolve_session_cwd` (`space/service.py:98-107`) |
| Resolution | present cwd → git detection / `resolve_cwd(create=True)` → containing worktree; missing path → `_materialize_missing_worktree` |
| Writes | `space_id` + `worktree_id` only via `update_session_space_identity` |
| **canvas_id** | **not written** (no column). Resolver returns `ResolvedWorktree.root_canvas_id` but backfill ignores it |
| DAO list | `AsyncSessionDao.list_sessions_missing_space_identity` → `LIST_SESSIONS_MISSING_SPACE_IDENTITY_SQL` (null space **or** null worktree) |
| DAO update | `AsyncSessionDao.update_session_space_identity` → `UPDATE_SESSION_SPACE_IDENTITY_SQL` (`dao_statements.py:210-217`) |
| Call site | `main._backfill_session_spaces` (`main.py:238-258`) invoked from `_start_session_backed_services` after `_resolve_current_space` (`main.py:368-369`) |
| Owner | hardcoded `"local"` |

Note: update is a plain SET (not COALESCE). Safe for missing-identity rows only; would overwrite if ever called on already-stamped sessions.

---

## 3. RunManager stop-in-process seam

| Surface | Detail |
|---|---|
| Manager | `packages/runtime/src/service/RunManager.ts` |
| List + filter | `list(filters: ManagedRunFilters)` — filters `owner` (required), optional `state`, **`spaceId`**, **`worktreeId`** (`RunManager.ts:286-293`) |
| Stop one | **`terminate(runId, owner, reason="explicit"\|"shutdown")`** (`RunManager.ts:401-408`) → `settleRun` → SIGTERM then SIGKILL |
| Stop all | `close()` terminates every run with reason `shutdown` (`RunManager.ts:411-418`) |
| HTTP | `POST /v1/runs/:runId/terminate?owner=` (`packages/runtime/src/server/runtimeRouter.ts` ~188) |
| Create identity | create accepts `spaceId` / `worktreeId`; view stores them (`runtimeRun.ts:12-13`). **No `canvasId` on RuntimeRunView** |
| Filter by canvas | **none** — must map canvas → worktree(s) externally, then `list({ owner, worktreeId })` + `terminate` each |

**Best-effort delete recipe (in-process):**

```
// canvas delete: resolve anchor_worktree_id (or descendants' worktrees), then:
const runs = manager.list({ owner, worktreeId })
await Promise.all(runs.map(r => manager.terminate(r.runId, owner, "explicit")))

// worktree delete: same with that worktreeId
// space delete: manager.list({ owner, spaceId }) then terminate each
```

Caveats:

- Process-resident only; API restart loses run map (already product fact).  
- CLI / non-RunManager launches are invisible here (CaptureLeaseRegistry / dedicated proxy).  
- `list` is exact id match; no hierarchy walk.  
- No bulk terminate-by-filter API; caller must loop.

---

## 4. DELETE cascade (org schema) + sessions FK-free

### Active FKs (0030 final schema)

| FK | Parent → child | ON DELETE |
|---|---|---|
| `space_worktree_link_space_fk` | space → link | **CASCADE** |
| `space_worktree_link_worktree_fk` | space_worktree → link | **CASCADE** |
| `canvas_parent_fk` | canvas → child canvas | **CASCADE** |
| `canvas_anchor_worktree_fk` | space_worktree → canvas | **CASCADE** |
| `canvas_default_worktree_fk` | space_worktree → canvas.default_worktree_id | **NO ACTION** (deferrable) |
| `space_worktree_root_canvas_fk` | canvas → worktree.root_canvas_id | **NO ACTION** (deferrable) |

Evidence: `api/migrations/versions/0030_space_crud_reset.py` (link FKs ~54-59; canvas FKs ~320-331; root pair ~65-70).  
Tests: `test_space_delete_cascades_membership_without_deleting_worktree` (links die, worktree+canvas stay); worktree DELETE cascades canvases+links (`test_space_crud_migration.py` ~426-439).

### Delete application surface

| Entity | API / store | Cascades org rows? |
|---|---|---|
| **Space** | `DELETE /v1/spaces/{id}` → `SpaceStore.delete_space` | Links CASCADE; **worktrees and canvases survive** |
| **Worktree link** | `DELETE /v1/spaces/{id}/links/{worktreeId}` | Link row only |
| **Canvas** | create/update only — **no delete endpoint** | SQL DELETE of parent cascades children; no product path |
| **Worktree** | **no delete endpoint** | SQL DELETE of worktree cascades canvases + links (root_canvas NO ACTION needs careful order / deferral) |

### Sessions FK-free (reconfirm)

| Artifact | FK to org? |
|---|---|
| `session.space_id` / `session.worktree_id` | **No FK** — 0006 bare ADD; 0030 type cast only |
| `run_lifecycle_event.space_id` / `worktree_id` | **No FK** |
| Org DELETE | Does not touch `session` or `run_lifecycle_event` |

Deleting space/worktree/canvas **cannot cascade or block** on sessions. Stamps go dangling. Fits write-once stamp + simple delete model.

---

## 5. S5 worktree create / move (claim-free)

### What exists

| Capability | Location | Notes |
|---|---|---|
| Detect existing git worktrees | `space/detection.py` — `classify_git_membership`, `_git_space`, `_run_git(["worktree","list","--porcelain","-z"])` | Read-only observation |
| Upsert detected worktree + root canvas | `SpaceStore.upsert_worktree` + `ensure_worktree_root` via `reconcile_detection` / `resolve_cwd` | `provenance` enum: `detected` \| `created` |
| Lifecycle states on row | `creating` / `active` / `deleting` | Schema ready; no create/move orchestration shipped |
| Link / unlink named space membership | `add_worktree_link` / `remove_worktree_link` | Membership only, not filesystem |
| Reconcile refresh | `SpaceCrudService.reconcile_worktrees` | re-`resolve_cwd` on known paths |

### What does **not** exist

- No `git worktree add` helper / port  
- No `git worktree move` / path-relocate helper  
- No service method to create a new linked worktree checkout  
- No worktree delete / move API  
- No claim/lease tables (S2 cut)

### Claim-free create/move would touch

1. **New git port** (or thin wrapper around `detection._run_git`): `worktree add`, optional `worktree move` / `remove`.  
2. **Store**: insert `space_worktree` with `provenance='created'`, `lifecycle_state='creating'→'active'`, path uniqueness; `ensure_worktree_root` for root canvas pair (deferred FK).  
3. **Link**: optional `space_worktree_link` for non-default spaces.  
4. **Move**: update `space_worktree.path` + re-identity `workspace_slug/hash` if path-derived identity changes (blast radius: unique indexes on path and workspace).  
5. **No claim layer** — just transactional DB + git subprocess; lifecycle_state is the only in-schema guard.  
6. **STEP 0:** `space/store.py` is **693 lines** — any non-trivial addition requires extract-first (700-line hard limit).

---

## Top risks (architect feed)

1. **Stamp gap at session create:** launch resolves space/worktree but `build_proxy_run_binding` drops them; session rows stay null until backfill. Write-once stamp needs an intentional seam (prepare → binding → `SessionBinding` / first upsert), not only backfill.  
2. **Canvas affinity is greenfield:** no columns, no backfill, no RunManager filter. If product needs canvas-scoped history/delete, schema + stamp path are new work.  
3. **Delete asymmetry:** space delete is soft on inventory (links only); canvas/worktree product deletes do not exist; SQL cascades are partial and `NO ACTION` root-pair FKs need ordered deletes. In-process run stop must be layered on, not assumed from FK.  
4. **Run stop incomplete for non-canvas launches:** RunManager only sees Runtime-managed runs; CLI capture path needs CaptureLeaseRegistry / proxy release for best-effort stop.  
5. **S5 create/move is greenfield git orchestration** on a near-limit `store.py` (693). Detection is read-only; `provenance=created` is schema-only.

---

## Quick citation index

| Topic | Cite |
|---|---|
| Session columns | `dao_statements.SESSION_COLUMN_NAMES`, `UPSERT_SESSION_SQL` |
| Mig 0006/0030 | `0006_spaces_foundation.py:86-88`, `0030_space_crud_reset.py:39-40,49-72,268-334` |
| Binding fields | `SessionBinding` space/worktree; no canvas |
| Launch resolve | `resolve_run_worktree`, `capture_rpc_routes._resolved_domain_request` |
| Binding builder gap | `addon_runtime.build_proxy_run_binding` |
| Backfill | `backfill_session_spaces`, `main._backfill_session_spaces` |
| Run stop | `RunManager.terminate`, `RunManager.list` |
| Cascades | 0030 FKs; `test_space_crud_migration` cascade tests |
| Sessions FK-free | 0006 ADD without REFERENCES; 0030 cast only |
| Git detect only | `detection._run_git`, `worktree list --porcelain` |
