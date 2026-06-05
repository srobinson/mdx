# Multilaunch re-plan — new-shape slice map (claim-free)

Architect: opus, multilaunch warroom. Owner-facing re-plan after the S2
claim/lease/reconciler machinery was **cut**. No claims, leases, coordinators,
or fencing appear anywhere below by design; §"Design smells avoided" records
where the old shape would have tempted them.

**Ground truth**
- Model of record: cm `019f8a57-c947-7411-8944-be6d9ebfce0f` (durable Space
  M:N Worktree, Canvas anchored on `anchor_worktree_id`, `worktree_in_space`
  single membership authority, named Spaces = view filters).
- Delete ruling: cm `019f8e91-63dc-7871-b045-7eb227168abc` (HARD DELETE, drop
  rows + best-effort stop live runs, no guard/force/agent-confirm).
- Seam inventory: `~/.mdx/projects/tm-replan-newshape-scout.md` (gpt,
  `@d7bfb9ac`); cross-ref `~/.mdx/projects/tm-replan-newshape-scout-grok-partial.md`.
- Tree fact: active migration chain ends at `0030_space_crud_reset`;
  `0031` is archive-only. Session stamp today = `space_id` + `worktree_id`
  only. Sessions are **FK-free** to the org schema (delete never cascades to or
  blocks on sessions).

---

## The shape in one paragraph

Two independent tracks share exactly one seam. **Track H (history):** the
affinity stamp becomes a plain write-once record so a session remembers which
space/worktree/canvas it ran in, storing both live `*_id` references and a
frozen `*_name`/`*_path` snapshot that survives hard delete as the tombstone.
**Track D (delete):** hard delete drops org rows (schema cascade) and makes a
best-effort in-process stop of live runs bound to the target. The only coupling
is the launch request field `canvasId`: Track H writes it to the session stamp,
Track D (canvas-exact stop only) writes it to the run view. Everything else in
the two tracks is disjoint. `worktree`/`space` deletes need **no** `canvasId`
because their runs are already attributable by `worktreeId`/`spaceId` filters
that `RunManager.list` exposes today.

---

## Dependency graph

```
S1  Affinity stamp (write-once)         [Track H]  — establishes canvasId request plumbing
        │  (shares: canvasId on launch request, server-resolved)
        ▼
S2  Typed run-inventory port            [Track D substrate]  — RunRouteProxy typed list
        ├────────────► S3  Worktree delete + Space-delete stop  (attributable by worktreeId/spaceId; NO canvasId)
        │
        ▼
S4a canvasId on runs (RuntimeRunView)   [Track D]  — thin enablement
        ▼
S4b Canvas delete (canvas-exact stop)   [Track D]  — needs canvasId to avoid killing sibling-canvas runs

S5  Worktree create / move              [orthogonal git port]  — no dep on stamp or run-stop
```

**Load-bearing dependency (as the brief flagged):** canvas-exact stop depends on
`canvasId` reaching both the launch request (S1) and the run view (S4a). Nothing
else in the graph blocks on it. `worktree`/`space` delete are attributable
**today** and gate only on the typed inventory port (S2).

**Shared STEP-0:** `space/store.py` is at **693 lines** (`SpaceStore`). Any slice
that adds a nontrivial store method (S3 worktree/canvas delete, S5 create/move)
must extract first. Whichever of S3/S4b/S5 lands first pays the STEP-0 cost once;
the stamp slice (S1) touches `session/` not `space/store.py`, so it is exempt.

---

## Recommended sequence + rationale

1. **S1 Affinity stamp** first. Highest standalone product value (history +
   delete tombstone), purely additive, carries **zero** cross-plane run-stop
   risk, and it is the single identity entry point: it locks the trusted
   `canvasId` server-resolution contract that S4a later reuses. Locking the
   identity contract on the safe slice de-risks everything downstream.
2. **S2 typed inventory port** next: small, unblocks all three deletes.
3. **S3 worktree + space delete** before canvas delete: they are attributable
   now, need no `canvasId`, and exercise the delete+stop pattern on the simpler
   cascades first.
4. **S4a canvasId on runs → S4b canvas delete** once the pattern is proven.
5. **S5 create/move** any time (orthogonal); slot it wherever capacity allows.

This ordering answers the brief's two open questions with a recommendation but
both remain Stuart's call — see §Open decisions.

---

## S1 — Affinity stamp (write-once) · Track H · FOUNDATION

**Scope.** Make the session affinity stamp a plain write-once record carrying
both references and a server-resolved snapshot; thread launch identity from the
trusted capture resolution into session creation; fix the upsert to write-once
with atomic-group semantics. No run-stop, no delete. Claim-free by construction
(a plain `WHERE`-guarded upsert, not a coordinator).

**New session columns (fresh migration, no-legacy drop/recreate, no backfill
migration):** `canvas_id`, `parent_canvas_id`, `canvas_name`, `canvas_path`,
`worktree_path`, `worktree_branch_name`. `space_id`/`worktree_id` already exist.
Snapshot columns are frozen text; `*_id` columns are bare (FK-free, matching the
existing stamp columns) so hard delete leaves them dangling by design.

**Atomic-group + write-once rule.** Replace the current
`space_id = COALESCE(EXCLUDED.space_id, "session".space_id)` first-non-null
merge (`session/dao_statements.py::UPSERT_SESSION_SQL`) with a stamp that is
written once from one launch snapshot and never re-mixed: on insert, take the
whole group from the incoming snapshot or none of it; on conflict, prefer the
**stored** value for every stamp column (a later ingest leaves a present stamp
untouched). No cross-snapshot mixing: the six-plus-two columns move as one unit.

**Backfill.** `session/backfill.py::backfill_session_spaces` stays fill-missing
-only. Extend it to also fill `canvas_id` (+ snapshot) from the resolver's
already-returned `ResolvedWorktree.root_canvas_id` — it is discarded today. Its
candidate query (`AsyncSessionDao.list_sessions_missing_space_identity`) and its
plain `SET` update (`UPDATE_SESSION_SPACE_IDENTITY_SQL`) already only touch
missing-identity rows; keep that invariant so backfill can never overwrite a
present stamp.

**Seams (file+symbol).**
- Launch request: add trusted `canvasId` to
  `packages/runtime/src/server/runtimeRouter.ts::registerRunRoutes`,
  `packages/runtime/src/service/RunManager.ts::RunManager.createNew`,
  `api/v1/capture_rpc_routes.py::PrepareCaptureRequest`, and
  `captured_run_models.py::CapturedRunRequest`. Resolve/validate against the
  Canvas the same way `capture_rpc_routes.py::_resolved_domain_request` /
  `api/v1/launch_resolution.py::resolve_run_worktree` resolve the Worktree.
  Names/paths come from the **server-resolved** Canvas/Worktree snapshot, never
  from request strings.
- Identity handoff (the drop the scout found): add space/worktree/canvas +
  snapshot fields to `index/adapters/base.py::RunContext` and
  `index/adapters/base.py::SessionBinding`; populate in
  `addon_runtime.py::_launch_run_context` and
  `addon_runtime.py::build_proxy_run_binding` (which omits them today); copy
  through `index/adapters/claude.py::ClaudeAdapter.bind` and
  `index/adapters/codex.py::CodexAdapter.bind`.
- Row + write: `session/models.py::SessionRow`, `session/ingest.py::build_session`,
  `session/dao_rows.py::session_params`, `session/dao_statements.py`
  (`SESSION_COLUMN_NAMES`, `UPSERT_SESSION_SQL`),
  `session/async_dao.py::AsyncSessionDao.upsert_session`.

**Tests-first (each asserts an observable end-state that FAILS at `d7bfb9ac`).**
- `test_session_affinity_stamp.py::test_launch_stamps_canvas_identity_on_first_session`
  (new, alongside `session/writer.py`): a captured launch resolves to a Canvas,
  the created `session` row carries `canvas_id` + `canvas_name`/`canvas_path`
  snapshot. FAILS now: columns and threading absent.
- `…::test_stamp_is_write_once_across_reingest`: second ingest with a **different**
  snapshot leaves the row byte-unchanged (stored value wins). FAILS now: COALESCE
  prefers later non-null.
- `…::test_stamp_group_is_atomic_never_mixed`: an ingest carrying a partial/mixed
  snapshot cannot land some columns from one snapshot and some from another. FAILS
  now: per-column COALESCE allows mixing.
- `…::test_snapshot_survives_hard_delete_as_tombstone`: delete the Canvas row,
  the session still reads its frozen `canvas_name`/`canvas_path`. FAILS now: no
  snapshot columns.
- `session/test_backfill*.py::test_backfill_fills_missing_canvas_only`: backfill
  sets `canvas_id` on a null-canvas row and does **not** rewrite a present one.
  FAILS now: canvas ignored.
- Migration test (home: `test_space_crud_migration.py` sibling, new
  `test_session_stamp_migration.py`): new columns exist with correct nullability.

**Migration.** One fresh migration adding the six columns. No data backfill in
the migration (runtime backfill handles historical rows).

**STEP-0.** None (session-side only; `space/store.py` untouched).

---

## S2 — Typed run-inventory port · Track D substrate

**Scope.** Give the Python service boundary a typed way to enumerate live
managed runs by owner + `spaceId`/`worktreeId`, so hard-delete code can drive
best-effort stop without reaching into raw HTTP. Reuses the filters
`RunManager.list` already exposes. No `canvasId` yet.

**Seams.**
- Add a typed list method to `RunRouteProxy` (Python) mirroring
  `runtimeRouter.ts` `GET /v1/runs` with `owner` + optional `spaceId`/`worktreeId`.
- Consume `RunManager.list(filters: ManagedRunFilters)` and
  `RunManager.terminate(runId, owner, reason)` unchanged.

**Tests-first.**
- `test_run_route_proxy.py::test_typed_list_returns_runs_filtered_by_worktree`
  (new): the proxy returns only runs matching `worktreeId`. FAILS now: no typed
  list method exists (Python can stop a known id but cannot list).
- `…::test_typed_list_filters_by_space`. FAILS now.

**Migration.** None. **STEP-0.** None (runtime/proxy, not `space/store.py`).

---

## S3 — Worktree delete + Space-delete stop · Track D

**Scope.** Hard-delete a worktree (cascade root canvas + descendants +
membership); upgrade the existing space delete to also best-effort-stop live
runs. Both are attributable by `worktreeId`/`spaceId` **today** — no `canvasId`.

**Delete semantics (from `0030` FKs, scout §4).**
- Worktree delete cascades `canvas_anchor_worktree_fk` (root + subtree) and
  `space_worktree_link_worktree_fk` (membership). The `space_worktree_root_canvas_fk`
  is `NO ACTION` deferrable, so the delete must run in the right statement order
  (or rely on deferral) — cover with a commit-level test.
- Space delete cascades membership only (worktrees/canvases survive) — endpoint
  `SpaceStore.delete_space` exists; add the best-effort stop-by-`spaceId` step.

**Best-effort stop.** After (or around) the row drop: typed-list by
`worktreeId`/`spaceId` (S2) → `RunManager.terminate` each → record/log failures,
continue. No guard, no force (delete ruling).

**Seams.** New `SpaceStore.delete_worktree` + `SpaceCrudService` orchestration +
`api/v1/space_routes.py` route + `api/v1/space_mcp.py` parity; existing
`SpaceStore.delete_space`/`SpaceCrudService.delete_space` gain the stop step.

**Tests-first.**
- `test_space_crud_migration.py::test_worktree_delete_cascades_root_subtree_and_membership_then_commits`
  already exists (green) — reuse as the cascade guardrail; add the product-path
  service/route test `test_worktree_delete_endpoint_drops_rows_and_stops_runs`
  (new) asserting the row is gone **and** a live worktree-bound run received
  terminate. FAILS now: no endpoint.
- `test_space_delete_stops_live_runs` (new): space delete terminates
  space-bound runs while leaving worktrees/canvases. FAILS now: stop step absent.

**Migration.** None (schema cascades already in `0030`). **STEP-0.** Yes —
`delete_worktree` is a nontrivial `space/store.py` addition; extract before
adding (this is the first slice to trip 700 if it lands before S4b/S5).

---

## S4a — canvasId on runs · Track D

**Scope.** Thread the trusted `canvasId` (resolved in S1) onto the run view so
runs are attributable to an exact Canvas. Enablement only; no delete.

**Seams.** `domain/runtimeRun.ts::RuntimeRunView` gains `canvasId`;
`RunManager.createNew`/`RunManager.register` fill it from the capture response;
`RunManager.list` gains a `canvasId` filter; the S2 typed proxy gains the
`canvasId` param.

**Tests-first.**
- `RunManager.test.ts::registers_and_lists_runs_by_canvas_id` (home:
  `packages/runtime` vitest): a run created with `canvasId` is returned by
  `list({ owner, canvasId })` and excluded for a sibling canvas. FAILS now:
  `RuntimeRunView` has no `canvasId`.

**Migration.** None. **STEP-0.** None.

---

## S4b — Canvas delete (canvas-exact stop) · Track D

**Scope.** Hard-delete a user Canvas (cascade descendants), best-effort-stop
**only** that canvas's runs (via S4a `canvasId`), and reject a lone
protected-root-canvas delete (it must go via worktree delete).

**Delete semantics.** `canvas_parent_fk` cascades descendants. Lone protected
root delete is rejected by the deferred `space_worktree_root_canvas_fk`
(`test_space_crud_migration.py::test_lone_root_delete_is_rejected_when_the_transaction_commits`);
the canvas-delete command must reject it **before** commit with a clear error,
not surface a raw constraint violation.

**Best-effort stop.** typed-list by `canvasId` (S4a) → terminate each. Using
`worktreeId` here would kill sibling-canvas runs on the same anchor — the exact
reason S4a precedes S4b.

**Seams.** New `SpaceStore.delete_canvas` + `SpaceCrudService` orchestration +
`api/v1/space_routes.py` route + `api/v1/space_mcp.py` parity.

**Tests-first.**
- `test_canvas_delete_endpoint_drops_subtree_and_stops_only_this_canvas` (new):
  descendants gone, a sibling-canvas run on the same worktree is **not**
  terminated. FAILS now: no endpoint, no `canvasId` filter.
- `test_lone_protected_root_delete_is_rejected_at_command` (new): the command
  rejects with a domain error, not a DB constraint leak. FAILS now: no command.

**Migration.** None. **STEP-0.** Yes if not already paid by S3/S5.

---

## S5 — Worktree create / move · orthogonal git port

**Scope.** Greenfield claim-free git orchestration: create a new linked worktree
checkout, and identity-preserving move. No dependency on the stamp or run-stop
tracks.

**Seams (scout §5).**
- New neutral git port (`worktree add` / `worktree move`), sharing the process
  runner with `space/detection.py::_run_git` rather than duplicating git policy.
- Refactor `SpaceStore.upsert_worktree` into a shared materialization primitive
  that accepts `provenance='created'` for new rows while preserving provenance +
  `root_canvas_id` on refresh.
- **Identity-preserving move:** a new store update that mutates canonical path +
  `workspace_slug`/`workspace_hash` for the **same** `worktree_id`. The current
  path-derived `upsert_worktree` would mint a new id + root canvas on a move —
  the primary risk to guard.
- Command models on `space/models.py`, orchestration on `SpaceCrudService`,
  routes on `api/v1/space_routes.py`, parity on `api/v1/space_mcp.py`.

**Tests-first.**
- `test_worktree_move_preserves_identity` (new): after move,
  `worktree_id`/`root_canvas_id`/`provenance` are unchanged and only path/slug/
  hash differ. FAILS now: no move path (upsert would re-mint).
- `test_worktree_create_writes_created_provenance_and_root` (new). FAILS now:
  no create command (provenance enum is schema-only).
- Git-port unit tests for argument construction + failure mapping (no live git).

**Migration.** None (provenance + lifecycle states exist in `0030`).
**STEP-0.** Yes — `space/store.py` at 693; extract before the create/move store
methods.

---

## Open decisions for Stuart

1. **Canvas-exact stop vs stop-free canvas delete (headline).** Recommended:
   sequence S4a (`canvasId` on runs) **before** S4b so canvas delete stops only
   its own runs. Alternative: ship S4b earlier with **no** run-stop (drop rows
   only) and add canvas-exact stop later — acceptable under the best-effort
   ruling, but a live canvas run would keep running after its canvas row is gone
   until API restart. Stopping by anchor-`worktreeId` instead is **rejected** on
   my lens: it kills sibling-canvas runs. Pick: S4a-then-S4b (recommended) /
   S4b-stop-free-now / accept-sibling-kill.
2. **S3 (worktree+space delete) before or after S1 (stamp)?** They are fully
   independent (S3 needs only S2). If delete UX is the nearer product need, S3
   can lead and S1 follow. Recommended S1-first only because it is the safer
   contract-locking foundation, not because S3 blocks on it.
3. **Does the affinity stamp need `parent_canvas_id` in the write path now, or
   snapshot-only?** The model lists it as a reference; S1 as written stamps it,
   but if no read surface consumes canvas lineage yet it could be deferred to
   keep the stamp minimal. Pick: stamp-now / defer-lineage.
4. **Space-delete stop: fold into S3 or its own micro-slice?** Recommended fold
   into S3 (same pattern, same typed port). Flag only if you want it isolated.

---

## Design smells avoided (claim-free audit)

- **S1 upsert:** the write-once guarantee is a `WHERE`-guarded / prefer-stored
  upsert, **not** a lease or a coordinator. No advisory locks needed for a
  write-once stamp — first writer wins, later writers are no-ops.
- **Track D stop:** best-effort `list` + `terminate` loop over process-resident
  runs. **No** RunTerminationCoordinator, **no** fencing generation, **no** claim
  reconciler. Process-resident-only + API-restart-loses-runs is an accepted
  product fact, not a gap to paper over with a durable claim table.
- **S5 create/move:** transactional DB + git subprocess + the in-schema
  `lifecycle_state` (`creating`/`active`/`deleting`) is the only guard. If a
  slice starts wanting a claim to serialize create/move, that is the design
  smell — the schema `lifecycle_state` plus a plain row lock is sufficient;
  escalate to me before building any coordinator.

---

## Slice count

**6 slices** (S1 stamp, S2 inventory port, S3 worktree+space delete, S4a
canvasId-on-runs, S4b canvas delete, S5 create/move), plus one shared STEP-0
`space/store.py` extraction paid by whichever of S3/S4b/S5 lands first.
Top open decision: **canvas-exact-stop ordering (S4a before S4b) vs stop-free
canvas delete now.**
