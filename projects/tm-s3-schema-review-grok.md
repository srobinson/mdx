# S3-schema PR1 Review — Grok (large-context MoE)

- **Range**: `57d1f087..1962bf82` on `ml/s3-schema` (HEAD `1962bf82`)
- **Date**: 2026-07-24
- **Reviewer**: `multi-launch:general:1:3.3` (grok)
- **Lens**: completeness + edge cases + test rigor + over-engineering; whole-surface sweep
- **Mode**: READ-ONLY (no repo writes, no gates)
- **Tree**: pristine at review tip (`git status` clean; tip is ancestor-reachable from range end)
- **cm authority**:
  - `019f918b-c4e0-7633-bfec-d7a86466fe28` Space/Workdir/OS-dir domain (CONFIRMED)
  - `019f91b3-6e12-73d1-86ae-83dc55e66dcd` S3 refinements (0..N equal spaces, UNIQUE(space_id, path), no default lock)
  - `019f92cc-0df9-7b42-8c79-c941e06e1c2b` S3 slice map (schema vs delete vs S3b)

## Verdict

**approve** — N:1 ownership reshape is complete and coherent. The M:N surface is gone from the active product path, edge cases are enforced in schema + service + REST, retired contracts are deleted rather than skipped, and no coordinator/finalization/computed-membership machinery was reintroduced. Product delete REST/MCP is intentionally absent (S3-delete cut); backend deletability is proven at the schema/cascade layer.

| Severity | Count | Summary |
|----------|------:|---------|
| blocker | 0 | — |
| major | 0 | — |
| minor | 3 | bootstrap path scan vs `list_worktrees_by_path`; dead path helper; wire `path` optionality lag |
| nit | 2 | vestigial `path or fallback`; slice-map delete/CMDK residual deferred |

## Builder-trust verdict

**trust: high**

| Axis | Score | Notes |
|------|-------|-------|
| Craftsmanship | high | Net −3k LOC of M:N/default/backfill ceremony; modules stay under 700; `worktree_mutations` mirrors `space_mutations`; one `SpaceCrudService` authority |
| Test rigor | high | Edge cases assert persisted rows / typed codes / HTTP status; retired M:N tests deleted (not skipped); REST absence test for resolve/link/delete |
| Spec + reuse fidelity | high | Matches cm 019f91b3 uniqueness and 0..N spaces; migration 0032 is a reshape reset (no backcompat theater); reuses canvas anchor/parent/root-pair constraints |
| Shortcuts | low residual | Product delete surfaces cut to S3-delete with explicit 405 coverage; CLI bootstrap is client-composed (approach A) without backend default composite |

Codex built a clean reshape, not a parallel compatibility layer.

## Lens checklist

| Check | Result |
|-------|--------|
| Entire M:N surface gone (store/service/REST/MCP/TS/allowlist/tests) | **PASS** — active refs only: migration downgrade history, `test_migrate` DROP cleanup, harness `connection.is_default` (unrelated domain), negative assertions in `test_space_crud_migration` |
| `space_worktree_link` / `worktree_in_space` / link-unlink / `DEFAULT_SPACE_LINK_CONSTRAINT` / `space_default_locked` | **PASS** — absent from production space/api/www; MCP skins list create/list/get/rename only |
| `is_default` / `space_default_owner_uq` / `ensure_default_space` / `require_default_space` | **PASS** — dropped from space table + models; `SpaceSummary` has no default flag; startup `_resolve_current_space` / backfill removed from `main.py` |
| Same path same space = conflict | **PASS** — `space_worktree_space_path_uq` + `worktree_mutations.create_workdir` → `SpaceCrudError("conflict")`; tests at migration/store/service/REST |
| Same path two spaces = two rows | **PASS** — schema + store/service/REST tests; CLI multi-match → `conflict` |
| Zero spaces valid | **PASS** — `test_zero_spaces_is_a_valid_store_state`, `test_zero_spaces_is_valid` (delete last row) |
| Every space renamable/deletable at backend | **PASS** — no undeletable marker; rename service/REST; SQL delete of any space cascades owned worktrees+canvases; REST `DELETE /spaces/{id}` returns 405 (product delete deferred) |
| Retired tests deleted not skipped | **PASS** — no `pytest.mark.skip/xfail` in space/space route suites; large test deletions |
| New tests assert observable end-state | **PASS** — conflict codes, distinct ids, inventory membership, affinity stamp survival, MCP bound tuple |
| No coordinator/finalization/computed-membership reimport | **PASS** |
| No duplicate helper/type/table machinery | **PASS** with minor unused path helper (m1/m2) |

## M:N excision evidence

| Symbol / object | Active status |
|-----------------|---------------|
| Table `space_worktree_link` | Dropped in `0032_space_worktree_ownership.upgrade`; recreated only on downgrade |
| `worktree_in_space` / named-link / default-membership functions | Dropped on upgrade; migration test asserts `functions == set()` |
| `SpaceStore*Ops.add/remove_worktree_link`, `worktree_in_space` | Gone |
| `space_mutations.link/unlink`, `DEFAULT_SPACE_LINK_CONSTRAINT` | Gone (`space_mutations.py` is create/rename only) |
| REST `POST/DELETE .../links`, `POST /spaces/resolve` | Absent; `test_retired_resolve_link_and_delete_routes_are_absent` |
| MCP `space_link_worktree` / `space_unlink_worktree` / `space_delete` | Removed from adapter + registration; skins allowlist has `worktree_create`/`space_list`/`space_get`/`space_create`/`space_rename` |
| TS `linkWorktree` / `unlinkWorktree` / `isDefault` | Removed; `createWorkdir` + `showSwitcher` remain |
| Session space backfill / `resolve_cwd` / `resolve_session_cwd` | Deleted with tests |

## Schema reshape (correct)

`api/migrations/versions/0032_space_worktree_ownership.py`:

- `space`: `space_id`, `owner`, **required** `name`, timestamps — no `is_default`
- `space_worktree`: required `space_id`, `canonical_os_path`, `UNIQUE(space_id, canonical_os_path)`, owner-safe FK `ON DELETE CASCADE`
- Path exposed as `canonical_os_path AS path` in store SQL (`store_worktree_ops._WORKTREE_COLUMNS`)
- Canvas anchor/parent/root-pair validation preserved
- Inventory joins via `w.space_id = s.space_id` (`store_space_ops._SPACE_INVENTORY_SELECT_SQL`)

## Edge-case + ownership paths

| Path | Behavior | Covered by |
|------|----------|------------|
| Strict create | no upsert; UniqueViolation → `conflict` | `worktree_mutations.create_workdir`, service/REST/store tests |
| Detection refresh | updates only **existing** owned rows; does not auto-insert siblings | `service.reconcile_detection` + `test_detection_refresh_updates_only_rows_owned_by_the_explicit_space` |
| Launch resolve | owned `worktree_id`; optional `space_id` mismatch → `space_mismatch` | `resolve_launch_worktree`, launch_resolution, service test |
| MCP binding | principal `space_id`/`worktree_id` → `CrudCaller.allowed_*` | `space_mcp._invoke`, `test_mcp_caller_carries_the_live_owned_tuple`, bound list/get tests |
| CLI bootstrap | empty → `create_space` then `create_workdir`; one match reuse; multi-match conflict | `cli/space_bootstrap.py` + `test_space_bootstrap.py` |
| IR survival | raw `DELETE FROM space` leaves session affinity columns | `test_inventory_delete_does_not_erase_session_affinity_stamp` |

## Over-engineering hunt

Absent (good):

- Deletion coordinator / finalization barrier / `run_capture_state`
- Computed default membership / catch-all default Space
- Parallel M:N compatibility path
- Startup auto-resolve / session space backfill

Acceptable lean additions:

- `worktree_mutations.create_workdir` (mutation boundary parity with spaces)
- Migration reshape via drop/recreate (matches cm "no migration ceremony")

## Minors

### m1 — CLI bootstrap path match should use owned path index

- **File/symbol**: `cli/space_bootstrap.bootstrap_cli_space` vs `SpaceStoreWorktreeOps.list_worktrees_by_path`
- **Issue**: bootstrap builds matches by `list_spaces(limit=10_000)` then projects every worktree (detection fan-out). A dedicated `list_worktrees_by_path` already exists on the store and is the correct N:1 multi-row lookup.
- **Risk**: pagination ceiling + unnecessary detection cost; theoretically can miss a match beyond the list window and invent a second Space for the same path (later launches then hit multi-match conflict).
- **Suggestion**: query `list_worktrees_by_path(target)` (or equivalent store SQL) inside the existing transaction; keep conflict-on-len>1 semantics.

### m2 — `list_worktrees_by_path` is dead production code

- **File/symbol**: `SpaceStoreWorktreeOps.list_worktree_by_path` (defined; no non-test caller)
- **Issue**: helper added for the multi-Space same-path world but unused; bootstrap reimplements a weaker form.
- **Suggestion**: wire m1 and keep one path; do not leave an orphan store API.

### m3 — Public Worktree path still optional after storage made it required

- **File/symbol**: `models.StoredWorktree.path: str` vs `models.WorktreeRecord.path: str | None` and `www/.../spaceTransport.ts` `path: string | null`
- **Issue**: storage and inventory always require `canonical_os_path`; wire types still advertise null. `ResolvedWorktree.from_worktree` still uses `worktree.path or fallback_cwd`.
- **Suggestion**: tighten record/TS to required `string` (or document a real null case if one remains).

## Nits

### n1 — Product delete surfaces deferred (intentional)

- REST/MCP `delete_space` / workdir delete removed; `test_retired_resolve_link_and_delete_routes_are_absent` expects 405 on `DELETE /v1/spaces/{id}`.
- Aligns with S3-delete slice in cm `019f92cc`, not a half-removed stub (link/unlink/default also gone). Cascade correctness is already tested at SQL.

### n2 — Slice-map CMDK "create-only until >1 Space" not expanded here

- Frontend removes `isDefault` and keeps `showSwitcher` gating in `useSpaces`.
- No new CMDK create-space command in this range; acceptable if UI progressive disclosure tracks a later desktop slice, but full slice-map text still mentions it under S3-schema.

## What this PR gets right

1. **Honest ownership**: every `StoredWorktree` carries `space_id`; inventory and canvas projection join through ownership; launch/MCP/canvas guards reject cross-space ids.
2. **Strict create**: user/service create does not upsert; only `reconcile_worktree` updates slug/hash on conflict for already-owned rows.
3. **Bootstrap composition**: detached CLI creates space then workdir client-side; server no longer auto-seeds a default Space on startup.
4. **Test posture**: large negative surface deleted; positive tests focus on durable uniqueness, multi-space rows, zero-space state, and live caller binding.
5. **IR boundary**: inventory delete does not touch session affinity stamps (S1 preserved).

## Residual for S3-delete (not blocking schema)

- Service/REST/MCP delete_space / delete_workdir
- Clear foreign `canvas.default_worktree_id` before worktree delete (`ON DELETE NO ACTION` remains)
- Provenance-keyed detected de-inventory + run stop

These are the next slice by design; this PR correctly stops at N:1 inventory + create/list/rename.

## Counts for bus

`review: approve 0b/0M/3m/2n trust:high ~/.mdx/projects/tm-s3-schema-review-grok.md`
