# Space-CRUD slice — build spec v1

Status: build-ready, tests-first.
Date: 2026-07-23
Baseline: `feat/multi-launch` @ `6453364a` (S1 merged, PR#316).
Model of record: cm `019f8a57` + `~/.mdx/projects/tm-s1-reshape-proposal.md` (v3).
Slice source: `~/.mdx/projects/tm-s2-s6-replan-architect.md` §3.
Governing rule: `TLDR.md` "No production, no legacy: break freely".
Owner locks carried in: Space-CRUD is the FIRST build slice; D5 (`create_worktree` takes no
`space_id`) is locked for S5, out of scope here.

## 1. Scope

Deliver named-Space lifecycle and worktree-reference membership through the same
`SpaceCrudService` seam S1 established. Five operations: **create named Space, rename named Space,
delete named Space, add worktree reference, remove worktree reference.** Every membership read
already routes through the shipped `worktree_in_space()` SQL function; this slice writes the
junction that predicate reads and introduces **no second membership path**.

In scope:
- Store helpers, service methods (Director authz), REST routes, MCP tools, `@tm/core` fetchers.
- Typed error semantics reusing the S1 `SpaceCrudError`/`SpaceCrudFailure` contract.

Out of scope (recommend as their own later slices):
- **Switch-default** (reassign which Space is `is_default`). The `validate_default_space_membership`
  trigger already reserves the invariant (a linked Space cannot become default), but switching is a
  two-row transactional flip under `UNIQUE(owner) WHERE is_default` plus a computed-all membership
  shift and its own switcher UX. It is **not trivially free** and does not belong in the smallest
  slice.
- Default-Space rename (its name is system-managed; rejected here).
- Any worktree/canvas mutation (S3/S5/S6).

## 2. No new migration

Migration `0030_space_crud_reset` already ships every schema object this slice needs. **This slice
adds no Alembic revision; Alembic head stays `0030_space_crud_reset`.** Confirmed present in
`migrations/versions/0030_space_crud_reset.py`:

- Table `space` (`space_id`, `owner`, `name` nullable, `is_default`, timestamps) with partial unique
  index on `(owner) WHERE is_default`.
- Table `space_worktree_link(owner, space_id, worktree_id)`, both FKs `ON DELETE CASCADE`.
- Function `worktree_in_space(owner, space_id, worktree_id)` — single membership authority.
- Function + trigger `validate_named_space_worktree_link` / `space_worktree_link_named_space_check`:
  `BEFORE INSERT OR UPDATE ON space_worktree_link`, raises `SQLSTATE 23514` with
  `CONSTRAINT = 'space_worktree_link_named_space_ck'` and message "Default Space membership is
  computed and cannot be linked".
- Function + trigger `validate_default_space_membership` / `space_default_computed_membership_check`
  (reserves switch-default; unused this slice).

`migration-smoke` still runs in the gate and must show **no schema delta** from this slice.

## 3. Store contract — `space.store:SpaceStore`

> **>> SUPERSEDED (2026-07-24 space-model).** The "computed-all catch-all default Space", "workdir survives / falls back to default on named Space delete or unlink", and "shared workdir M:N across Spaces" model is **wrong**. Confirmed model: **Workdir belongs to exactly one Space**; same OS dir in multiple Spaces = **multiple Workdir entities**; Default is auto + undeletable but **not** a catch-all; **DELETE Space cascades all its workdirs** (canvases + runs); **DELETE workdir** cascades its canvases + runs; OS dir never touched. See cm *Space/Workdir/OS-dir domain model (CONFIRMED)* and `~/.mdx/projects/tm-s3-spec-v2.md`.


Add five methods, matching the existing imperative-verb convention (`ensure_default_space`,
`upsert_worktree`, `insert_user_canvas`, `worktree_in_space`). All are owner-scoped, `owner="local"`
default. All reuse `_space_from_row` for row mapping.

| Method | SQL shape | Returns |
|--------|-----------|---------|
| `create_named_space(*, owner="local", name)` | `INSERT INTO space (space_id, owner, name) VALUES (gen, owner, name) RETURNING …` (server-minted UUID, `is_default` defaults false) | `Space` |
| `rename_space(space_id, *, owner="local", name)` | `UPDATE space SET name=%s, updated_at=now() WHERE space_id AND owner AND NOT is_default RETURNING …` | `Space \| None` (None = missing or default) |
| `delete_space(space_id, *, owner="local")` | `DELETE FROM space WHERE space_id AND owner AND NOT is_default RETURNING space_id` (links cascade via FK) | `bool` (deleted?) |
| `add_worktree_link(space_id, worktree_id, *, owner="local")` | `INSERT INTO space_worktree_link (owner, space_id, worktree_id) VALUES (…) ON CONFLICT DO NOTHING` | `None` |
| `remove_worktree_link(space_id, worktree_id, *, owner="local")` | `DELETE FROM space_worktree_link WHERE owner AND space_id AND worktree_id` | `None` |

Rules baked into the store:
- **Default immutability is enforced by SQL, not re-derived in Python.** `rename_space`/`delete_space`
  carry `AND NOT is_default` in the predicate (row simply does not match), and `add_worktree_link`
  lets the shipped `space_worktree_link_named_space_check` trigger fire. The store does **not** read
  `is_default` to branch. Per orchestrator: surface a clean typed error, do not duplicate the check.
- **Idempotency** mirrors `ensure_default_space`: duplicate `add_worktree_link` is a no-op
  (`ON CONFLICT DO NOTHING`); `remove_worktree_link` of an absent link is a no-op.
- `add_worktree_link` lets `psycopg.errors.CheckViolation` (constraint
  `space_worktree_link_named_space_ck`) propagate for the service to map. It does not catch it.
- Worktree-existence and space-existence are **not** the store's job here; the service validates
  those before calling (matching how `reconcile_detection` validates before `upsert_worktree`).

Extend the repository-contract guard `space.test_service:test_store_exposes_the_service_repository_contract`
`public_operations` tuple with the five new names. This is the cheapest fail-first signal.

## 4. Service contract — `space.service:SpaceCrudService`

> **>> SUPERSEDED (2026-07-24 space-model).** The "computed-all catch-all default Space", "workdir survives / falls back to default on named Space delete or unlink", and "shared workdir M:N across Spaces" model is **wrong**. Confirmed model: **Workdir belongs to exactly one Space**; same OS dir in multiple Spaces = **multiple Workdir entities**; Default is auto + undeletable but **not** a catch-all; **DELETE Space cascades all its workdirs** (canvases + runs); **DELETE workdir** cascades its canvases + runs; OS dir never touched. See cm *Space/Workdir/OS-dir domain model (CONFIRMED)* and `~/.mdx/projects/tm-s3-spec-v2.md`.


Add five methods. All are **Director-only** and **owner-scoped across Spaces** (the `director_tree`
idiom), never the space-bound `_require_allowed_space` gate — a Director bound to Space A must be able
to create Space B.

```text
create_space(caller, name)                       -> Space
rename_space(caller, space_id, name)             -> Space
delete_space(caller, space_id)                   -> None
link_worktree(caller, space_id, worktree_id)     -> None
unlink_worktree(caller, space_id, worktree_id)   -> None
```

Authz + validation, reusing S1 seams:
- **Extract `_require_director(caller)`** from the two-line role check currently duplicated in
  `reconcile_worktrees` and `director_tree`; call it first in all five methods. (DRY: this removes
  the duplication rather than adding a sixth copy.)
- `create_space`: `_require_director`; validate name (below); `store.create_named_space`.
- `rename_space`: `_require_director`; validate name; `store.rename_space`; on `None`, disambiguate
  via `store.get_space` → `space_not_found` if missing else `space_default_locked`.
- `delete_space`: `_require_director`; `store.delete_space`; on `False`, disambiguate via
  `store.get_space` → `space_not_found` else `space_default_locked`.
- `link_worktree`: `_require_director`; assert space exists (`store.get_space` → `space_not_found`)
  and worktree exists owner-scoped (`store.get_worktree` → `worktree_not_found`); call
  `store.add_worktree_link`; catch `psycopg.errors.CheckViolation` whose
  `diag.constraint_name == "space_worktree_link_named_space_ck"` → `SpaceCrudError("space_default_locked", …)`.
- `unlink_worktree`: `_require_director`; assert space exists; `store.remove_worktree_link`
  (idempotent — removing an absent link succeeds; the worktree stays visible via computed-all).

**Name validation (DRY):** Space names follow the Canvas rule (trimmed, non-empty, ≤120 scalars).
Generalize `space.models:validate_canvas_name` into a shared `validate_display_name(value, *,
max_len=120)` and have both Canvas and Space names call it. Invalid → `SpaceCrudError("invalid_request", …)`.

**Caller construction.** Add `rest_director_caller(*, owner=DEFAULT_OWNER)` next to `rest_caller` in
`space.service`. Because Director mutations are not space-bound, make `CrudCaller.allowed_space_id`
optional (`SpaceId | None = None`) — an additive default; every existing constructor already passes a
concrete value, so blast radius is nil and `_require_allowed_space` stays correct for space-bound
reads. The new factory sets `role=CrudRole.DIRECTOR`, `surface=CrudSurface.REST`, `allowed_space_id=None`.

## 5. Error semantics

One new code; everything else reuses S1 codes.

| Code | HTTP | When |
|------|------|------|
| `space_default_locked` (NEW) | 409 | delete or rename the default Space; link a worktree into the default Space (mapped from the trigger's `space_worktree_link_named_space_ck`) |
| `forbidden` | 403 | caller is not Director |
| `space_not_found` | 404 | target Space absent |
| `worktree_not_found` | 404 | link target worktree absent |
| `invalid_request` | 400 | empty/oversize name |

Add `"space_default_locked": HTTP_409_CONFLICT` to `space_routes:_raise_crud_error.status_by_code`.
REST and MCP return identical codes and messages. `space_default_locked` mirrors the existing
`canvas_root_locked` pattern: one code covers the whole "this object's shape is system-owned"
family.

## 6. REST — `api/v1/space_routes.py`

Reuse `rest_director_caller`, `_parse_space_id`/`_parse_worktree_id`, `_raise_crud_error`,
`response_payload`, `_space_summary`, and `require_http_origin` (mutations are origin-guarded like
`resolve_space`). Request DTOs are frozen Pydantic (camelCase aliases) alongside the existing
`ResolveSpaceRequest`.

| Verb | Path | Service | Success | Body |
|------|------|---------|---------|------|
| POST | `/v1/spaces` | `create_space` | 201 `SpaceSummary` | `CreateSpaceRequest { name }` |
| PATCH | `/v1/spaces/{space_id}` | `rename_space` | 200 `SpaceSummary` | `RenameSpaceRequest { name }` |
| DELETE | `/v1/spaces/{space_id}` | `delete_space` | 204 | — |
| POST | `/v1/spaces/{space_id}/links` | `link_worktree` | 204 | `LinkWorktreeRequest { worktreeId }` |
| DELETE | `/v1/spaces/{space_id}/links/{worktree_id}` | `unlink_worktree` | 204 | — |

Create/rename return the `SpaceSummary` (client needs the minted id/name). Delete/link/unlink return
204; the client refetches via `fetchSpaces` (server authority, mirroring the S1 canvas-delete
client-reconciliation rule). All mutations drop public owner query authority exactly like the S1
CRUD routes.

## 7. MCP — `api/v1/space_mcp.py`

Add five tools in `register_space_mcp_tools`, each delegating through `SpaceMcpAdapter` to the
matching service method, each typed `Annotated[CallToolResult, McpToolOutput[Result, SpaceCrudFailure]]`.

| Tool | Args | Result |
|------|------|--------|
| `space_create` | `name: str` | `SpaceResult { space: SpaceSummary }` |
| `space_rename` | `space_id: str, name: str` | `SpaceResult { space }` |
| `space_delete` | `space_id: str` | `SpaceAck { space_id }` |
| `space_link_worktree` | `space_id: str, worktree_id: str` | `SpaceAck { space_id }` |
| `space_unlink_worktree` | `space_id: str, worktree_id: str` | `SpaceAck { space_id }` |

Reuse the `_invoke` + `mcp_tool_result` + `space_crud_failure` machinery. **Caller derivation seam:**
the S1 adapter builds a *space-bound* caller from the run's `ControlPlanePrincipal` (reads use
`caller.allowed_space_id`). Space-CRUD tools need an **owner-scoped Director caller**
(`role=DIRECTOR`, `allowed_space_id=None`, `surface=MCP`). Add a director-caller path in
`SpaceMcpAdapter` distinct from the read path. MCP accepts no owner override, no raw args.

## 8. `@tm/core` transport — `www/packages/core/src/spaceTransport.ts`

Add five fetchers reusing the shipped `requestApiJson` / `requestApiVoid` helpers from
`www/packages/core/src/transport.ts` (both already accept a `RequestInit`, so method+body+headers
come for free — **no new HTTP helper**).

```text
createSpace(name): POST /v1/spaces                                 -> SpaceSummary   (requestApiJson)
renameSpace(spaceId, name): PATCH /v1/spaces/{id}                  -> SpaceSummary   (requestApiJson)
deleteSpace(spaceId): DELETE /v1/spaces/{id}                       -> void           (requestApiVoid)
linkWorktree(spaceId, worktreeId): POST /v1/spaces/{id}/links      -> void           (requestApiVoid)
unlinkWorktree(spaceId, worktreeId): DELETE /v1/spaces/{id}/links/{wt} -> void        (requestApiVoid)
```

JSON bodies use camelCase (`{ name }`, `{ worktreeId }`) and `Content-Type: application/json`,
matching the existing `resolveSpace`/`transport.ts` POST idiom. Reuse `encodeURIComponent` on path
ids as the existing fetchers do.

## 9. Reuse map (DRY — build on shipped seams only)

| Capability | Existing owner (file:symbol) | Disposition |
|------------|------------------------------|-------------|
| Default-Space insert idiom | `space.store:SpaceStore.ensure_default_space` | Mirror for `create_named_space` |
| Membership authority | `worktree_in_space()` (mig 0030) + `SpaceStore.worktree_in_space` | Consume, never bypass |
| Link-into-default rejection | trigger `space_worktree_link_named_space_check` (mig 0030) | Catch + map, do not re-check in Python |
| Row mapping | `space.store:_space_from_row` | Reuse |
| Director gate | `space.service:SpaceCrudService.director_tree` / `reconcile_worktrees` role check | Extract `_require_director`, reuse |
| Name validation | `space.models:validate_canvas_name` | Generalize to `validate_display_name` |
| REST caller | `space.service:rest_caller` | Add sibling `rest_director_caller` |
| Error → HTTP map | `space_routes:_raise_crud_error` | Add one code |
| REST response envelope | `space_routes:response_payload` / `_space_summary` | Reuse |
| Origin guard | `origin:require_http_origin` | Reuse |
| MCP result envelope | `space_mcp:McpToolOutput` / `mcp_tool_result` / `space_crud_failure` | Reuse |
| MCP principal | `controlplane.models:ControlPlanePrincipal` | Reuse |
| Browser HTTP | `transport:requestApiJson` / `requestApiVoid` | Reuse (pass `RequestInit`) |
| Repo contract guard | `space.test_service:test_store_exposes_the_service_repository_contract` | Extend tuple |

No new migration, no new HTTP helper, no second membership predicate, no duplicated default check.

## 10. Tests-first plan

Every case below is written **red first** and must FAIL before its implementation exists. TDD per
`superpowers:test-driven-development`.

**`space/test_store.py`** (Postgres-backed, `test_db` fixture; app-path writes):
- `create_named_space` inserts a non-default named Space (`is_default False`, name set, fresh UUID).
- **Rewrite `test_default_membership_is_computed_and_named_membership_uses_links`** to drive
  membership through `add_worktree_link` / `remove_worktree_link` instead of raw `INSERT INTO
  space_worktree_link`. Assert: linked worktree appears in `list_worktrees(named)`, `worktree_in_space`
  true; after `remove_worktree_link` it is absent from the named Space but still in the default
  (computed-all) and `worktree_in_space(default)` true.
- `add_worktree_link` into the default Space raises `psycopg.errors.CheckViolation` with constraint
  `space_worktree_link_named_space_ck`.
- `add_worktree_link` twice is idempotent (one row).
- `remove_worktree_link` of an absent link is a no-op (no error).
- `delete_space(named)` returns True; its `space_worktree_link` rows are gone; worktrees + root
  canvases survive.
- `delete_space(default)` returns False; the default row survives.
- `rename_space(named)` updates the name; `rename_space(default)` returns None; default name unchanged.

**`space/test_service.py`**:
- Extend `test_store_exposes_the_service_repository_contract` with the five new store names (fails
  until the store has them).
- Each of the five service methods rejects a non-Director caller → `forbidden`.
- `link_worktree` into the default Space → `space_default_locked` (mapped from CheckViolation).
- `delete_space(default)` and `rename_space(default)` → `space_default_locked`.
- `link_worktree` with unknown worktree → `worktree_not_found`; any op on unknown space →
  `space_not_found`.
- `create_space` with empty / >120 name → `invalid_request`.
- After `create_space`, the new Space appears in `list_spaces`; `list_spaces` count crossing 1 makes
  the REST `show_switcher` true (assert at the route layer too).
- `unlink_worktree` leaves the worktree visible via the computed-all default.

**`api/v1/test_space_routes.py`**:
- Each route: correct status (201 create, 200 rename, 204 delete/link/unlink) and DTO shape.
- Error→status mapping: `space_default_locked`→409, `forbidden`→403, `space_not_found`→404,
  `worktree_not_found`→404, invalid name→400.
- Origin guard enforced on mutations.

**`api/v1/test_space_mcp.py`**:
- Each tool: success result shape + failure surfaces `SpaceCrudFailure` with the same codes as REST.
- Director caller derivation (owner-scoped, not the run's bound Space).

**`www/packages/core/src/spaceTransport.test.ts`** (mock `apiTransport`, mirror
`transport.test.ts`):
- Each fetcher issues the exact method + path + JSON body and parses the response
  (POST/PATCH/DELETE assertions, camelCase body keys).

## 11. Gate

Reference recipes verbatim; no bare `pytest`/`tsc` (`feedback_gates_are_repo_recipes`).

- **Engineer + reviewers (change-scoped):** `just check` + `just test-affected`.
- **Grok local-CI (authoritative pre-merge, tree idle):** `just check` + `just test` +
  `just migration-smoke` (the api-level `migration-smoke` recipe; it must show no schema delta since
  this slice adds no migration).

Bounded slice: no new file, and no function exceeds ~150 lines. `space/store.py` is 503 lines
(comfortable). `space/service.py` is 597 — the five service methods plus the `_require_director`
extraction and `rest_director_caller` factory could approach the 700-line limit; if it crosses,
split the Space-mutation service methods into a focused module before adding, per the refactor-first
rule (flag to engineer at build start).
```
