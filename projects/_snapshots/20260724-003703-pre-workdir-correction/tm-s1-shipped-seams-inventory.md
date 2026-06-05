# S1 shipped seams inventory

Date: 2026-07-23  
Branch: `feat/multi-launch` @ `6453364a` (S1 merge, PR #316)  
Sources: cm `019f8a57-c947-7411-8944-be6d9ebfce0f` (MODEL OF RECORD), `~/.mdx/projects/tm-s1-reshape-proposal.md` v3, live code under this worktree.  
Scope: read-only inventory of what S1 actually shipped, so S2–S6 re-plan rides real symbols.

Verdict key:

- **LIVE**: schema/symbol exists and is wired into the active path (service, SQL authority, REST/MCP consumer, or proven by store tests as the production write path).
- **SCHEMA-ONLY / RESERVED**: durable substrate is present; application mutation surface for a later Space-CRUD (or Canvas-CRUD) slice is absent.
- **SERVICE-ONLY**: implemented on `SpaceCrudService` but not exposed by REST/MCP.

---

## Summary

| # | Reshape concept | Status | Primary symbol(s) | File(s) |
|---|-----------------|--------|------------------|---------|
| 1 | `space` table + `space_worktree_link` junction | **LIVE** schema | migration `0030_space_crud_reset` | `api/migrations/versions/0030_space_crud_reset.py` |
| 2 | `worktree_in_space` membership authority | **LIVE** | SQL `worktree_in_space(owner, space_id, worktree_id)`; `SpaceStore.worktree_in_space`; `SpaceCrudService._require_worktree_in_space` | migration; `space/store.py`; `space/service.py` |
| 3 | `reconcile_detection` write boundary (no membership writes) | **LIVE** | `SpaceCrudService.reconcile_detection` | `space/service.py` |
| 4 | Projection module / Stored vs Projected | **LIVE** | `StoredWorktree`, `ProjectedWorktree`, `WorktreeRecord`, `SpaceSnapshot`, `project_worktree`, `assemble_space_snapshot` | `space/models.py`, `space/projection.py` |
| 5 | `repo_group_key` filesystem classifier | **LIVE** | `classify_git_membership`, `ClassifiedMembership.repo_group_key`, `detect_space` | `space/detection.py` |
| 6 | `canvas.anchor_worktree_id` + anchored FK constraints | **LIVE** | `StoredCanvas.anchor_worktree_id`; migration canvas FKs + root-pair triggers | `space/models.py`; migration |
| 7 | `SpaceCrudService` read + reconcile methods | **LIVE** | `list_worktrees`, `get_worktree`, `get_space_snapshot`, `reconcile_worktrees`, `list_spaces`, `list_canvases`, … | `space/service.py` |
| 8 | REST + MCP + `@tm/core` DTOs | **LIVE** (read adapters) | `space_routes`, `register_space_mcp_tools`, `spaceTransport` | `api/v1/space_routes.py`, `api/v1/space_mcp.py`, `www/packages/core/src/spaceTransport.ts` |
| 9 | Default Space computed-all membership | **LIVE** | `SpaceStore.ensure_default_space` before worktree upsert in reconcile | `space/store.py`, `space/service.py` |

**Totals:** 9 reshape concepts inventoried → **9 LIVE** at substrate/read/reconcile layer.  
**Space-mutation application surface:** **0 LIVE** (all RESERVED).  
**Junction write application path:** **0 LIVE** (schema + predicate only; tests insert links via raw SQL).

---

## 1. `space` table + `space_worktree_link` junction

**Status: LIVE schema (S1)**

Migration `0030_space_crud_reset` (`revision = "0030_space_crud_reset"`) rebuilds:

```text
space {
  space_id uuid PK
  owner text NOT NULL DEFAULT 'local'
  name text nullable
  is_default boolean NOT NULL DEFAULT false
  created_at / updated_at
  UNIQUE (owner, space_id)
  UNIQUE INDEX space_default_owner_uq ON (owner) WHERE is_default
}

space_worktree_link {
  owner, space_id, worktree_id  PK
  FK (owner, space_id) -> space ON DELETE CASCADE
  FK (owner, worktree_id) -> space_worktree ON DELETE CASCADE
}
```

Also creates final `space_worktree` without the four runtime columns (`branch_name`, `head_oid`, `is_primary`, `missing`) and without `space_id` on the worktree row. Drops legacy `space_git_identity`.

Triggers:

- `validate_named_space_worktree_link` — blocks linking into a default Space.
- `validate_default_space_membership` — blocks promoting a linked Space to default while links exist.

**Application writes to `space`:** only `SpaceStore.ensure_default_space` (idempotent default insert).  
**Application writes to `space_worktree_link`:** none (see § Reserved).

---

## 2. `worktree_in_space` predicate (single membership authority)

**Status: LIVE**

### SQL authority (source of truth)

```sql
worktree_in_space(scope_owner, scope_space_id, scope_worktree_id)
  → true when space.is_default
  → else link exists in space_worktree_link
```

Created in migration `_create_membership_predicate()`.

### Python mirror / consumer

| Layer | Symbol | Role |
|-------|--------|------|
| Store | `SpaceStore.worktree_in_space` | Executes SQL function |
| Inventory SQL | `_SPACE_INVENTORY_SELECT_SQL` | Filters worktrees + canvases via `worktree_in_space(...)` |
| List SQL | `list_worktrees`, `list_canvases` | Same predicate |
| Service | `SpaceCrudService._require_worktree_in_space` | Authz gate for get_canvas / get_worktree / launch / workspace caller |

Every Space-scoped read and placement check that ships today goes through this predicate (or the store methods that embed it). There is no second membership check.

---

## 3. `reconcile_detection` write boundary

**Status: LIVE; membership-safe**

`SpaceCrudService.reconcile_detection` (`space/service.py`):

1. `_lock_detection` — `pg_advisory_xact_lock` on owner+repo identity
2. `ensure_default_space`
3. For each detected worktree: `upsert_worktree` then `ensure_worktree_root`
4. Return projected snapshot

**Does not** INSERT/UPDATE/DELETE `space_worktree_link`.  
**Does not** reassign organizational Space membership.  
`upsert_worktree` only touches durable path identity (`path`, workspace slug/hash) on conflict.

Proof tests in `space/test_store.py`:

- `test_reconcile_creates_one_default_space_without_membership_links` → links count 0
- `test_plain_to_git_projection_and_reconcile_preserve_organizational_state` → durable rows byte-identical across plain→git

Director-scoped refresh: `reconcile_worktrees` re-resolves existing paths via `resolve_cwd(..., create=True)` then re-snapshots; still no junction writes.

Retired: `mark_missing_worktrees`, Space-keyed git identity claims, `space_git_identity` table (asserted gone in `test_space_crud_migration.py`).

---

## 4. Projection module

**Status: LIVE**

| Type / fn | File | Notes |
|-----------|------|-------|
| `StoredWorktree` | `space/models.py` | Durable path + lifecycle only; no membership, no git facts |
| `ProjectedWorktree(StoredWorktree)` | `space/models.py` | Adds `space_id`, `repo_group_key`, branch/HEAD/primary/missing |
| `WorktreeRecord` | `space/models.py` | Wire DTO (`from_worktree`), camelCase aliases |
| `StoredCanvas` / `Canvas` | `space/models.py` | Canvas adds response `space_id` context |
| `CanvasRecord` | `space/models.py` | Path segments + depth + childCount |
| `SpaceSnapshot` | `space/projection.py` | `space` + projected worktrees + contextualized canvases |
| `project_worktree` | `space/projection.py` | Pure merge of stored row + detection observation |
| `assemble_space_snapshot` | `space/projection.py` | Pure assembly |
| `observations_by_path` | `space/projection.py` | Rank git over path observations |

`store.py` returns only `StoredWorktree` / `StoredCanvas`. Runtime facts never re-enter persistence through projection.

---

## 5. `repo_group_key` runtime classifier

**Status: LIVE**

`space/detection.py`:

| Symbol | Role |
|--------|------|
| `GitMembership` | `git` / `plain` / `inconclusive` |
| `classify_git_membership` | Ancestor walk for `.git` dir or `gitdir` file; resolves `commondir`; permission/malformed/broken → inconclusive |
| `ClassifiedMembership.repo_group_key` | `git:{sha256(common_dir)}` or `path:{sha256(path)}` or `None` |
| `detect_space` | Stage-1 classify; stage-2 enrich via `git worktree list --porcelain -z` when git |
| `repo_instance_key` | sha256 of canonical git common dir |

Invariant held in code: porcelain failure does not demote a proven git classification to plain; falls back to a single path worktree still carrying the git group key.

Display consumers: `WorktreeRecord.repo_group_key` → REST/MCP/TS `repoGroupKey`. CMDK grouping in `www/packages/canvas/src/launcher/workdirRows.ts` uses `repoGroupKey` for display only.

---

## 6. `canvas.anchor_worktree_id` + anchored constraints

**Status: LIVE**

Schema (`_create_final_canvas` + root pair):

- `canvas.anchor_worktree_id NOT NULL`
- `UNIQUE (owner, anchor_worktree_id, canvas_id)`
- Parent FK `(owner, anchor_worktree_id, parent_canvas_id)` → canvas, `ON DELETE CASCADE`
- Anchor FK `(owner, anchor_worktree_id)` → `space_worktree`, `ON DELETE CASCADE`
- Default worktree FK deferred `NO ACTION`
- Worktree root FK `(owner, worktree_id, root_canvas_id)` → canvas, deferred `NO ACTION`
- Deferred pair triggers `validate_space_worktree_root_pair` on both tables

Model: `StoredCanvas.anchor_worktree_id`; records surface as `anchorWorktreeId`.  
Canvas Space visibility is computed: inventory joins canvases where `worktree_in_space(owner, space_id, c.anchor_worktree_id)`.

No `canvas.space_id` column.

---

## 7. `SpaceCrudService` read methods

**Status: LIVE** for the S1 read + reconcile surface.

| Method | Status | Notes |
|--------|--------|-------|
| `list_spaces` | LIVE | Owner inventories → projected snapshots |
| `count_spaces` | LIVE | Switcher threshold |
| `get_space_snapshot` | LIVE | `_require_space` + project |
| `list_worktrees` | LIVE | → `WorktreeRecord` |
| `get_worktree` | LIVE | Membership-gated |
| `list_canvases` / `get_canvas` | LIVE | Anchor membership-gated |
| `reconcile_worktrees` | LIVE | Director role required |
| `reconcile_detection` / `resolve_cwd` / `resolve_session_cwd` | LIVE | Materialization path |
| `resolve_launch_worktree` / `resolve_workspace_caller` | LIVE | Placement uses `worktree_in_space` |
| `director_tree` | **SERVICE-ONLY** | Builds `DirectorTree` from list_spaces; **no REST/MCP route** |
| `require_user_canvas` | **SERVICE-ONLY** | Root-lock helper for future mutations |

Store repository contract asserted by `test_store_exposes_the_service_repository_contract`:  
`ensure_default_space`, `ensure_worktree_root`, `insert_user_canvas`, `list_canvases`, `list_worktrees`, `worktree_in_space`, `upsert_worktree`.

---

## 8. REST + MCP + `@tm/core` transport

**Status: LIVE read adapters**

### REST (`api/v1/space_routes.py`, mounted at `/v1`)

| Route | Backing service |
|-------|-----------------|
| `GET /spaces` | `list_spaces` + `count_spaces` → `showSwitcher` |
| `POST /spaces/resolve` | `resolve_cwd` (origin-gated) |
| `GET /spaces/{id}` | `get_space_snapshot` + `list_canvases` |
| `GET /spaces/{id}/worktrees` | `list_worktrees` |
| `POST /spaces/{id}/worktrees/reconcile` | `reconcile_worktrees` (origin-gated) |
| `GET /worktrees/{id}` | `get_worktree` |
| `GET /spaces/{id}/canvases` | `list_canvases` |
| `GET /canvases/{id}` | `get_canvas` |

No REST for create/rename/delete Space, link add/remove, or Canvas write.

### MCP (`api/v1/space_mcp.py`, registered from `controlplane_mcp.py`)

| Tool | Backing |
|------|---------|
| `canvas_list` / `canvas_get` | `list_canvases` / `get_canvas` via workspace principal |
| `worktree_list` / `worktree_get` | `list_worktrees` / `get_worktree` |

No MCP Space list/detail, no reconcile, no mutations. Principal resolves via `resolve_workspace_caller` → default Space + membership check.

### `@tm/core` (`www/packages/core/src/spaceTransport.ts`)

DTOs match Python wire records:

- `WorktreeSummary` including `repoGroupKey`, lifecycle, branch/HEAD/primary/missing
- `CanvasSummary` including `anchorWorktreeId`
- `SpaceSummary` / `SpaceListResponse` with `showSwitcher`
- Fetchers: `fetchSpaces`, `fetchWorktrees`, `fetchWorktree`, `fetchCanvases`, `fetchCanvas`

Contract test: `spaceTransport.contract.test.ts` locks `repoGroupKey` type.

---

## 9. Default Space computed-all membership

**Status: LIVE**

Ordering inside `reconcile_detection` (transaction):

```text
ensure_default_space(owner)  →  upsert_worktree(...) × N  →  ensure_worktree_root(...)
```

`ensure_default_space`:

```sql
INSERT INTO space (...) VALUES (..., is_default=true)
ON CONFLICT (owner) WHERE is_default DO NOTHING
```

Default membership is never materialized as links. New worktrees appear under the default Space solely because `worktree_in_space` returns true when `is_default`. Proven by store tests (links remain 0 after multi-worktree reconcile).

---

## Reserved: Space mutation / junction write paths

These are the proposal’s “later Space CRUD slice.” Schema and predicate are ready; **application seams do not exist**.

| Future mutation | Schema ready? | App symbol today | Status |
|-----------------|---------------|-----------------|--------|
| Create named Space | `space` table | none | **RESERVED** — tests use raw `INSERT INTO space` |
| Rename Space | `name` col | none | **RESERVED** |
| Switch default | `is_default` + triggers | none (only auto-default insert) | **RESERVED** |
| Delete Space | CASCADE on links | none | **RESERVED** |
| Add worktree to named Space | `space_worktree_link` + named-space trigger | none | **RESERVED** |
| Remove worktree from named Space | junction PK | none | **RESERVED** |
| Store helpers `add_link` / `remove_link` / `create_space` | n/a | **absent from `SpaceStore`** | **RESERVED** |
| REST/MCP mutation routes | n/a | absent | **RESERVED** |

**Only production Space write:** `SpaceStore.ensure_default_space`.  
**Only production organizational Worktree writes:** `upsert_worktree`, `ensure_worktree_root`.  
**Canvas user-tree insert:** `SpaceStore.insert_user_canvas` exists and is unit-tested, but is **not** exposed on `SpaceCrudService` public methods or REST/MCP. Treat as **store-level foundation / RESERVED for Canvas CRUD**, not S1 Space-CRUD.

Named-membership behavior is proven read-side only: `test_default_membership_is_computed_and_named_membership_uses_links` inserts links via raw SQL, then asserts `list_worktrees` / `list_canvases` / `worktree_in_space`.

---

## Adjacent LIVE seams (not in the 9-item brief, useful for re-plan)

| Seam | Symbol | File | Note |
|------|--------|------|------|
| Canonical path identity | `canonical_path` | `space/identity.py` | Single path normalizer (reshape structure test enforces) |
| Session stamp type | `session.space_id` / `run_lifecycle_event.space_id` → **text** | migration 0030 | FK-free durable stamps; UUID string of Space |
| Startup materialize | `SpaceCrudService.resolve_cwd` from main | `main.py` | Creates default Space on API boot cwd |
| Session backfill | `resolve_session_cwd` | `session/backfill.py`, `api/v1/meta.py` | Present-cwd resolution |
| Director presentation model | `DirectorSpaceNode`, `DirectorTree` | `models.py` + `director_tree()` | Service only; UI switcher uses REST list + `showSwitcher` |
| CrudCaller / role / surface | `CrudCaller`, `CrudRole`, `CrudSurface` | `models.py` | REST director-local; MCP principal-bound |

---

## Gaps / re-plan watchouts (aspirational proposal vs shipped)

1. **Named Space CRUD** is entirely open: no service methods, no routes, no store link helpers. Re-plan must add a dedicated Space-CRUD slice that **only** mutates through `worktree_in_space` consumers already in place.
2. **`director_tree` is not HTTP-exported.** Browser uses `GET /v1/spaces` + per-space worktrees/canvases. Do not plan against a missing `/director` route unless you add it.
3. **MCP surface is narrower than REST** (no spaces list, no reconcile, no resolve). Control-plane agents see worktrees/canvases only inside the principal’s resolved Space.
4. **`insert_user_canvas` is store-private** relative to service/API. Canvas tree mutations for CMDK/MCP are not S1-complete if the re-plan expected full Canvas CRUD over the wire.
5. **Runtime columns are gone from SQL**; any pre-reshape code or docs still speaking of persisted `branch_name` / `is_primary` / worktree-owned `space_id` is stale.
6. **M4 is dissolved in code**: plain→git only changes projected `repo_group_key`; organizational rows stay put (test-backed).

---

## File map (production S1 reshape surface)

```text
api/migrations/versions/0030_space_crud_reset.py
api/src/transport_matters/space/
  detection.py      # classifier + detect_space
  identity.py       # canonical_path
  models.py         # Stored*/Projected*/Records/Director*
  projection.py     # SpaceSnapshot assembly
  store.py          # SpaceStore persistence
  service.py        # SpaceCrudService authority
  testing.py        # test helpers
api/src/transport_matters/api/v1/
  space_routes.py   # REST
  space_mcp.py      # MCP tools
www/packages/core/src/spaceTransport.ts
```

---

## One-line for orchestrator

**9/9 reshape concepts LIVE at substrate+read+reconcile; 0 Space-mutation app paths (junction add/remove, named create/rename/delete all RESERVED); inventory at `~/.mdx/projects/tm-s1-shipped-seams-inventory.md`.**
