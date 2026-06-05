# S1 review + authoritative full gate (Grok)

Date: 2026-07-22  
PR: #316  
Branch / SHA: `feat/multi-launch` @ `25f20382f860d4371256319192bb295544b203f3`  
Authority: `~/.mdx/projects/tm-canvas-worktree-crud-spec-v1.md` §15 Slice 1 + contract invariants  
Role: read-only review; authoritative local pre-merge gate  
Tree after review: tracked clean (`?? .serena/` only)

## Gate results (authoritative)

Environment note: Docker Desktop was unavailable (`docker.sock` missing). Default `localhost:55432` refused connections. Authoritative re-run used Homebrew PostgreSQL 18 on `127.0.0.1:5432` with role `tm` and:

`TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@127.0.0.1:5432/postgres`

| Gate | Result | Counts |
| --- | --- | --- |
| `just check` | **pass** (exit 0) | desktop typecheck + 102 tests; shell format/lint/typecheck; product packages typecheck; api ruff + mypy 670 files |
| `just test` | **pass** (exit 0) | JS packages all green (desktop 102; shell aggregate 1249; common 24; contract 8; activity 322; runtime 190 + 2 skipped; gateway 21). API: **3342 passed, 11 skipped, 0 failed** in 38.66s |
| `just migration-smoke` (`api/justfile` → `session/test_migrate.py`) | **pass** | **9 passed** in 2.65s |

First `just test` attempt against :55432 failed with 266 connection ERRORs + 5 FAILED (all DB-admin path). That run is **not** the authority. After Postgres was available, full re-run is green.

Remote Blacksmith backend·test reported green on this SHA; local full gate agrees.

## Slice 1 scope check (spec §15)

| Deliverable | Status |
| --- | --- |
| `SpaceCrudService` | Present: `space.service.SpaceCrudService` |
| Migration 0030 | `0030_space_crud_reset`, `down_revision = 0029_native_connection_origin`, is head |
| Final Canvas / Worktree records | `kind`, `parent_canvas_id`, `root_canvas_id`, `provenance`, lifecycle fields; drop layout/archive |
| Virtual Director projection | `SpaceCrudService.director_tree` + test; no director canvas row |
| Tree reads | `list_canvases` / `get_canvas` with path, depth, child_count, cycle/depth guards |
| Detection reconciliation | `reconcile_detection` → upsert + `_ensure_worktree_root` in one transaction + advisory lock |
| Idempotent protected root | `_ensure_worktree_root` ON CONFLICT + concurrent tests |
| Trusted REST + MCP callers | REST via `rest_caller` / DEFAULT_OWNER local; MCP via `resolve_workspace_caller` + principal workspace |
| CMDK list and switch | `useCanvases` + `buildCanvasRows` / `select-canvas` by durable UUID |

Out of S1 (correctly absent): user create/update/delete MCP mutations, runtime claims, Git create, Worktree delete.

## Coherence review (whole-diff)

### Single `SpaceCrudService` path

Production write/reconcile/read entry points observed:

- `space_routes` → `SpaceCrudService` only (list/get/resolve; no parallel create/patch REST)
- `space_mcp.register_space_mcp_tools` → shared service
- `launch_resolution.resolve_run_worktree` → `SpaceCrudService.resolve_launch_worktree`
- `main` lifespan / session backfill / meta → service

No second application service. Repository primitives remain on `SpaceStore` and are reached through the service for detection (`_upsert_worktree`, `_ensure_worktree_root`). Acceptable internal split for S1.

### No backfill / compat / dual-write

Migration **DROP + recreate** of `canvas` and `space_worktree`. Spec allows reset; no data migration, no dual-write, no `layout_version` bridge. Browser: `defaultCanvasId` is UUID-only (`route.defaultCanvasId`); no `space:` synthetic canvas cache keys for durable identity. Storage version remains 1 with null canvasId disabling persist until UUID present. Matches “no production users” reset policy.

### Migration 0030 head off 0029

Verified in `0030_space_crud_reset.py` and `test_space_crud_reset_is_the_migration_head`. Deferred circular FK:

`space_worktree_root_canvas_fk` → `(owner, space_id, root_canvas_id)` REFERENCES `canvas` **ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED**.

Canvas shape CHECK: `worktree_root` requires null parent + nonnull default worktree; `user` requires parent. Parent scoped FK same owner+space. Unique `root_canvas_id`. Provenance CHECK. Tests cover immediate root restrict, one root per worktree, drop of legacy columns.

### worktree_root + ≥1-canvas invariant

- Every upserted worktree gets `root_canvas_id` + `_ensure_worktree_root` before commit.
- Root kind is protected at service layer via `require_user_canvas` (mutations later).
- Protected root **is** the ≥1 canvas; zero user children allowed (spec).
- Concurrent detection test asserts single valid root pair.

### CMDK / MCP contracts

- CMDK: list + switch only; no CRUD mutation commands in this slice.
- MCP: `canvas_list`, `canvas_get`, `worktree_list`, `worktree_get` only; workspace-scoped caller; cross-space rejected (`space_mismatch`).

## Code hygiene (new surface)

| File | LOC | Note |
| --- | --- | --- |
| `space/service.py` | 428 | Under limit; clear facade |
| `space/store.py` | 585 | Under limit; still large but reduced vs pre-S1 growth risk |
| `space/models.py` | 321 | Clean vocabulary |
| `api/v1/space_mcp.py` | 227 | Focused extraction (good) |
| `api/v1/space_routes.py` | 351 | Read adapter |
| `controlplane_mcp.py` | 499 | Registers space tools; under 700 |
| `spaceTransport.ts` | 100 | Split from crowded transport (good) |
| `commandRows.ts` | 439 | Canvas rows added; OK |
| `useCommandCenter.ts` | 357 | Hooks stay focused |

No new file over 700. Duplication of Space/Worktree/Canvas DTOs between Python records and TS `spaceTransport` is intentional contract mirroring, not parallel logic.

## Findings

### Blockers

None for Slice 1 merge relative to §15 and full green gate.

### Suggestions (non-blocking)

1. **Private store methods called from service** (`_upsert_worktree`, `_ensure_worktree_root`, `_claim_git_space`, test use of `_insert_user_canvas`). Prefer a thin public repository API before S3/S5 so tests and service do not reach underscore methods.
2. **`director_tree` is service-only** in S1 (no REST/MCP tool). Spec lists “virtual Director projection” as S1 deliverable; behavior is tested, but product surfaces still compose roots via space/canvas list. Fine if intentional; expose later if CMDK/MCP need the aggregation.
3. **Launch gate does not yet consult `lifecycle_state`** (`resolve_run_worktree` checks `missing` only). Correct for S1; S2/S6 must refuse `deleting` / non-active before Git delete lands.
4. **`canvas_default_worktree_fk ON DELETE SET NULL` vs root CHECK** requiring nonnull default: safe while Worktree delete is absent; S6 finalization order must not SET NULL a root’s default.

### Nits

- `SpaceCrudService.list_spaces` still accepts raw `owner` without `CrudCaller` (REST hardcodes DEFAULT_OWNER). Consistent with local REST trust model; keep MCP on principal-derived caller only.
- Test-only depth walk uses private `_insert_user_canvas` until S3 owns public create.

## Builder trust (codex engineer)

**High trust.** Slice is coherent end-to-end: reset migration, single service authority, provenance-preserving detection upsert, deferred root FK, focused MCP module, UUID-only client identity, and tests that match the S1 list (reset, roots, concurrency, parity, director virtual). Gate green under full `just check` / `just test` / migration-smoke. No parallel CRUD path or silent compat layer found.

## Verdict

**review: clean**  
**gate: check pass · test 3342 passed / 0 failed (API) + JS packages green · migration-smoke 9 passed**
