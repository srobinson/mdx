# S3 — Canvas create + update — build spec v1

Status: build-ready, tests-first.
Date: 2026-07-23
Baseline: worktree reset onto `main` @ `0905622d` (Space-CRUD #317 merged).
Model of record: cm `019f8a57` (canvas anchors on `anchor_worktree_id`, never `space_id`).
Slice source: `~/.mdx/projects/tm-s2-s6-replan-architect.md` §S3.
Governing rules: `CLAUDE.md` (refactor-BEFORE-add over 700 LOC; no function >150; DRY),
`TLDR.md` ("No production, no legacy: break freely").

**New error code needed: NO.** Every failure maps to an existing code (justified in §5).

## 0. Scope

Deliver user-Canvas **create** and **update** (rename + reparent + default change) through the same
`SpaceCrudService` facade, re-scoped to `anchor_worktree_id` per the model. CMDK stays list/switch
only (S1). Worktree-root Canvases remain service-created only; public create always makes a `user`
Canvas under an existing parent.

Out of scope: Canvas delete (S4), Worktree create/move/delete (S5/S6), cross-anchor move,
CMDK mutation surfaces.

## 1. STEP 0 — mandatory pure refactor BEFORE any Canvas code (own commit)

`space/service.py` is **698 LOC**. `CLAUDE.md` mandates refactor before adding to a file at/over the
limit. Extract, as a **behavior-preserving move** (all existing tests stay green, import graph clean,
no signature change on the public facade):

1. **`space/authz.py` (new leaf).** Move the shared guards that BOTH reads and mutations use, so the
   mutation module does not create a read→mutation back-edge:
   - `require_director(caller)` (currently `SpaceCrudService._require_director`, used by
     `reconcile_worktrees` and `director_tree` too).
   - `require_bound_space(caller)` (used by `list_canvases`/`get_canvas`/`get_worktree`/launch reads).
   - `display_name(name)` (the `SpaceCrudError("invalid_request", …)` wrapper over
     `validate_display_name`).
   - `rest_director_caller(...)` (already a module function in `service`).
   Pure functions; depend only on `models`. `SpaceCrudService` calls into `authz` (keep thin private
   method shims only if a caller count makes it cheaper; prefer direct calls).
2. **`space/space_mutations.py` (new).** Move the five Space-mutation bodies
   (`create_space`/`rename_space`/`delete_space`/`link_worktree`/`unlink_worktree`) as free async
   functions taking `(store, conn, caller, …)`, importing `authz`. `SpaceCrudService` keeps the five
   method signatures as **thin delegators** (preserves the "SpaceCrudService is the sole application
   entry point" invariant and every existing call site).

This is a deliberate refinement of the brief's single-module suggestion: `_require_director` /
`require_bound_space` are shared by reads, so they belong in a neutral `authz` leaf, not inside
`space_mutations` (which would force reads to import the mutations module). Import graph after STEP 0:
`authz` ← {`service`, `space_mutations`}; `space_mutations` ← `service`. No cycles.

Result: `service.py` drops ~90-110 LOC (five bodies + guards), giving S3 headroom so Canvas
mutations land under 700 with room for S4/S5/S6.

**STEP 0 gate:** the entire existing suite stays green with zero behavior change; extend
`space/test_reshape_structure.py` to assert the new module boundaries and that `SpaceCrudService`
still exposes the five Space-mutation methods.

## 2. New module for Canvas mutations

Canvas create/update bodies land in **`space/canvas_commands.py` (new)** as free async functions,
mirroring the `space_mutations.py` shape. `SpaceCrudService` exposes `create_canvas` / `update_canvas`
as thin delegators. This keeps `service.py` lean and matches the original module plan
(`space/canvas_commands.py`). Store primitives live in `space/store.py`.

## 3. Store contract — `space.store:SpaceStore`

| Method | Status | Shape |
|--------|--------|-------|
| `insert_user_canvas` | **exists, reserved** (only test callers today) — wire it through the service unchanged; it already inherits `anchor_worktree_id` from the parent, forces `kind='user'`, and validates the name | reuse |
| `update_canvas(canvas_id, *, owner, name?, parent_canvas_id?, default_worktree_id: Patch)` | **new** | `UPDATE canvas SET … , updated_at=now() WHERE canvas_id=%s AND owner=%s AND kind='user' RETURNING …` → `StoredCanvas \| None` (None = not found or is a protected root) |
| `list_canvases_by_anchor(anchor_worktree_id, *, owner)` | **new** | `SELECT … FROM canvas WHERE owner=%s AND anchor_worktree_id=%s` → `tuple[Canvas, …]`; used to build the mutation-response `CanvasRecord` and to run the ancestry/depth walk, independent of Space scoping |
| `canvas_ancestry(canvas_id, *, owner)` or reuse a recursive CTE | **new** | recursive-CTE walk of `parent_canvas_id` returning ordered ancestor ids + depth; the mutation-time cycle/depth authority (distinct from the read-time in-memory `_canvas_records` walk) |

`update_canvas` sets only the fields provided. The `canvas_kind_shape_ck` and `canvas_parent_fk`
constraints (mig 0030) are DB backstops: `kind='user'` in the predicate keeps roots immutable, and the
composite `canvas_parent_fk (owner, anchor_worktree_id, parent_canvas_id)` structurally forbids a
cross-anchor parent (the parent must exist under the same `anchor_worktree_id`).

Extend the repository-contract guard `space.test_service:test_store_exposes_the_service_repository_contract`
with `update_canvas` and `list_canvases_by_anchor`.

## 4. Service contract — `SpaceCrudService` (delegating to `canvas_commands`)

Both are Director-only, **owner-scoped** (canvas is anchored to a Worktree, not bound to a Space —
never call `require_bound_space` here). Advisory lock reuses the `_lock_detection` precedent
(`pg_advisory_xact_lock(hashtextextended(identity, 0))`) keyed on `(owner, anchor_worktree_id)`.

### create_canvas(caller, CreateCanvasCommand) -> CanvasRecord

```text
CreateCanvasCommand { parent_canvas_id: CanvasId; name: str; default_worktree_id: WorktreeId | None }
```
(No `space_id` — re-scoped from the original spec §5; the parent determines the anchor.)

Flow: `require_director`; load parent (`store.get_canvas`, owner-scoped) → `canvas_not_found`; take the
`(owner, parent.anchor_worktree_id)` advisory xact lock; depth guard via CTE
(`parent_depth + 1 > MAX_CANVAS_DEPTH` → `canvas_depth_exceeded`); validate `default_worktree_id` when
present is an **owner** Worktree (any owner Worktree, owner-scoped) → `worktree_not_found`; call
`store.insert_user_canvas` (inherits anchor, `display_name` validates the name); build and return the
`CanvasRecord` (see §4.3). Parent may be a `worktree_root` or a `user` Canvas (both are valid parents).

### update_canvas(caller, UpdateCanvasCommand) -> CanvasRecord

```text
UpdateCanvasCommand { canvas_id: CanvasId;
                      name: str | None;                       # present → rename
                      parent_canvas_id: CanvasId | None;      # present → reparent (no null case)
                      default_worktree_id: Patch[WorktreeId | None] }  # absent | set | clear
```

Flow: `require_director`; load Canvas (`store.get_canvas`, owner-scoped) → `canvas_not_found`; reject a
protected root via `require_user_canvas` (→ `canvas_root_locked`); take the
`(owner, canvas.anchor_worktree_id)` advisory xact lock. Then, under the lock:
- **rename:** `name` present → `display_name` validate.
- **reparent:** `parent_canvas_id` present → new parent must exist owner-scoped and share the SAME
  `anchor_worktree_id` (→ `canvas_root_mismatch` on cross-anchor); run the ancestry CTE from the new
  parent upward — if `canvas_id` appears (self or descendant becomes ancestor) → `canvas_cycle`;
  depth: `new_parent_depth + height(moved subtree) > MAX_CANVAS_DEPTH` → `canvas_depth_exceeded`.
- **default:** `Patch.present(value)` → validate owner Worktree exists (→ `worktree_not_found`);
  `Patch.present(null)` → clear.
- Persist via `store.update_canvas`; None return (root/missing under the lock) → re-resolve to
  `canvas_root_locked` / `canvas_not_found`. Return the rebuilt `CanvasRecord`.

**`Patch[T]` (new, in `space.models`).** Introduce a minimal `Patch[T] = Absent | Present(value)` so
`default_worktree_id` distinguishes omitted / set / cleared. Name and parent take plain optionals (no
meaningful null: a user Canvas always has a parent, so "clear parent" is not a valid op). `Patch` is
forward-reusable by S5/S6 `Patch[T]` needs.

### 4.3 Mutation-response `CanvasRecord`

`CanvasRecord.space_id` is response context (a Canvas appears in every Space referencing its anchor).
Mutations are owner-scoped, so **stamp the response with the owner's default Space id** (the
computed-all default always contains the anchor Worktree — always valid, always stable). Build
`depth`/`path`/`child_count` by running the existing `_canvas_records` tree walk over
`store.list_canvases_by_anchor(canvas.anchor_worktree_id)` and selecting the target id. This reuses the
read-side projection logic without Space scoping.

## 5. Error semantics — all reused, NO new code

| Code | HTTP (existing `_raise_crud_error.status_by_code`) | When |
|------|------|------|
| `forbidden` | 403 | non-Director |
| `canvas_not_found` | 404 | canvas or parent absent |
| `worktree_not_found` | 404 | bad `default_worktree_id` |
| `invalid_request` | 400 | bad name (empty / NUL / >120) |
| `canvas_root_locked` | 409 | mutate a protected root |
| `canvas_cycle` | 409 | reparent onto self/descendant |
| `canvas_depth_exceeded` | 409 | create/reparent past depth 32 |
| `canvas_root_mismatch` | 409 | **cross-anchor reparent** (new parent under a different Worktree root) |

Justification for reusing `canvas_root_mismatch` for cross-anchor reparent: it already means "Canvas
tree is detached from its root," and a cross-anchor parent is precisely a target and parent belonging
to different Worktree roots. A distinct new code would carry no distinct client action (the fix is the
same: choose a parent in the same Worktree root). REST and MCP return identical codes. No change to
`status_by_code`.

## 6. REST — `api/v1/space_routes.py`

Reuse `rest_director_caller`, `_parse_canvas_id`, `_raise_crud_error`, `response_payload`,
`require_http_origin`. Request DTOs are frozen Pydantic with camelCase aliases.

| Verb | Path | Service | Success | Body |
|------|------|---------|---------|------|
| POST | `/v1/canvases` | `create_canvas` | 201 `CanvasRecord` | `CreateCanvasRequest { parentCanvasId; name; defaultWorktreeId? }` |
| PATCH | `/v1/canvases/{canvas_id}` | `update_canvas` | 200 `CanvasRecord` | `UpdateCanvasRequest { name?; parentCanvasId?; defaultWorktreeId?: Patch }` |

Create is **not** nested under `/spaces/{id}` (canvas is anchored to a Worktree, not Space-scoped) —
the parent id in the body determines the anchor. Both routes are origin-guarded. `CanvasRecord`
(models.py) is already the REST canvas response type (see `CanvasListResponse`, `CanvasDetailResponse`),
so no new response DTO and no neutral-leaf mapper is needed.

## 7. MCP — `api/v1/space_mcp.py`

Add two tools delegating through `SpaceMcpAdapter` with the **owner-scoped Director caller**
(`director=True` path, `allowed_space_id=None`), typed `Annotated[CallToolResult,
McpToolOutput[CanvasGetResult, SpaceCrudFailure]]` (reuse the existing `CanvasGetResult { canvas:
CanvasRecord }`). Parse ids with the existing generic `_crud_id`.

| Tool | Args | Result |
|------|------|--------|
| `canvas_create` | `parent_canvas_id: str, name: str, default_worktree_id: str \| None = None` | `CanvasGetResult { canvas }` |
| `canvas_update` | `canvas_id: str, name: str \| None = None, parent_canvas_id: str \| None = None, default_worktree_id: str \| None = None` | `CanvasGetResult { canvas }` |

`CanvasRecord` lives in `space.models` (a neutral leaf both adapters already import), so **no private
cross-adapter import** is introduced — this was Space-CRUD review Minor #1 and must not recur. MCP
accepts no owner override and no raw args.

## 8. `@tm/core` transport — `www/packages/core/src/spaceTransport.ts`

Add two fetchers reusing `requestApiJson` (both return the created/updated summary). `CanvasSummary`
already exists.

```text
createCanvas(parentCanvasId, name, defaultWorktreeId?): POST /v1/canvases         -> CanvasSummary
updateCanvas(canvasId, patch): PATCH /v1/canvases/{id}                            -> CanvasSummary
```

camelCase JSON bodies (`{ parentCanvasId, name, defaultWorktreeId }`), `Content-Type: application/json`,
`encodeURIComponent` on the path id, `{ detailAware: true }` to surface typed error detail (matching
the Space-CRUD fetchers).

## 9. No new migration

The `canvas` table, `canvas_scoped_id_uq`, `canvas_parent_not_self_ck`, `canvas_kind_shape_ck`,
`canvas_parent_fk` (composite same-anchor), `canvas_anchor_worktree_fk`, `canvas_default_worktree_fk`
(deferred), `canvas_parent_lookup_ix`, and the root-pair triggers all shipped in
`0030_space_crud_reset`. **This slice adds no Alembic revision; head stays `0030`.** `migration-smoke`
must show no schema delta.

## 10. Tests-first plan (all red before impl; assert OBSERVABLE end-state)

**STEP 0 (`space/test_reshape_structure.py` + full suite):** assert the new module boundaries; assert
`SpaceCrudService` still exposes the five Space-mutation methods; the entire existing Space-CRUD +
canvas-read suite stays green with zero behavior change. Extend the repository-contract tuple with
`update_canvas` + `list_canvases_by_anchor`.

**`space/test_store.py` (canvas primitives):**
- `insert_user_canvas` inherits the parent's `anchor_worktree_id` (create under a nested parent →
  `anchor == parent.anchor`).
- `update_canvas` rename + reparent-within-anchor persist; `update_canvas` against a `worktree_root`
  returns None (kind guard).
- cross-anchor reparent at the store level raises `ForeignKeyViolation` (constraint
  `canvas_parent_fk`) — proves the DB backstop.
- `list_canvases_by_anchor` returns exactly one anchor's tree.

**`space/test_service.py` (canvas commands):**
- create under a parent inherits anchor; returns a `CanvasRecord` with correct `depth`/`path`/
  `child_count` and `space_id` = default Space.
- create at the depth-32 boundary → `canvas_depth_exceeded`, tree unchanged (observable via read).
- create: blank / NUL / 121-char name → `invalid_request`; non-Director → `forbidden`; unknown
  `default_worktree_id` → `worktree_not_found`.
- update rename → new name visible through `list_canvases` read path.
- update reparent within-anchor → new parent + recomputed `depth`/`path` visible via read.
- update reparent onto a descendant → `canvas_cycle`; cross-anchor reparent → `canvas_root_mismatch`;
  reparent/rename a root → `canvas_root_locked`.
- update reparent pushing a subtree past depth 32 → `canvas_depth_exceeded`.
- update `default_worktree_id`: set to another owner Worktree (owner-scoped, cross-anchor allowed),
  clear to null, and omit (unchanged) — three `Patch` states each asserted through a read-back.

**`api/v1/test_space_routes.py`:** POST 201 + `CanvasRecord` shape; PATCH 200; status parity
(`forbidden` 403, not-found 404, cycle/depth/root_locked/root_mismatch 409, `invalid_request` 400);
origin guard on both mutations.

**`api/v1/test_space_mcp.py`:** `canvas_create`/`canvas_update` success + `SpaceCrudFailure` envelope;
owner-scoped Director caller (`allowed_space_id is None`); MCP↔REST code parity.

**`www/packages/core/src/spaceTransport.test.ts`:** `createCanvas`/`updateCanvas` issue the exact
method + path + camelCase body and parse the response (mirror the Space-CRUD transport tests).

## 11. Gate

- Engineer + reviewers: `just check` + `just test-affected`.
- Grok local-CI (tree idle): `just check` + `just test` + `just migration-smoke` (direct proof of the
  zero-migration claim).

Bounded: STEP 0 restores `service.py` headroom; Canvas mutation bodies live in
`space/canvas_commands.py`; no new file exceeds 700 LOC and no function exceeds ~150.
