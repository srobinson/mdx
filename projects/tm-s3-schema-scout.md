# S3 Schema Scout

Scope: `feat/multi-launch` at `57d1f087594777c7d07d97105a539616d7463ee5`. The repository tree was pristine before inspection. This was a read only scout. No gates ran.

## Reuse Map

### 1. Current schema

`api/migrations/versions/0030_space_crud_reset.py::upgrade` is the current Space, Worktree, and Canvas authority. `api/migrations/versions/0031_session_affinity_stamp.py::upgrade` only adds session affinity columns, so no later migration changes this inventory model.

Current `space` objects:

- Table `space`: `space_id` primary key, `owner`, nullable `name`, `is_default`, timestamps, and `space_owner_id_uq UNIQUE(owner, space_id)`.
- Index `space_default_owner_uq`: partial `UNIQUE(owner) WHERE is_default`.
- The default marker is enforced and consumed across `Space`, `space_from_row`, `SpaceSummary`, `space_summary`, `SpaceStoreSpaceOps.ensure_default_space`, `SpaceStoreSpaceOps.rename_space`, `SpaceStoreSpaceOps.delete_space`, `SpaceCrudService.reconcile_detection`, `SpaceCrudService._default_caller`, `require_default_space`, and `canvas_commands._canvas_record`.

Current `space_worktree` objects:

- Table `space_worktree` has no `space_id`. Its persistent path field is `path`.
- `space_worktree_workspace_uq UNIQUE(owner, workspace_slug, workspace_hash)`.
- `space_worktree_owner_id_uq UNIQUE(owner, worktree_id)`.
- `space_worktree_path_uq UNIQUE(owner, path)`.
- `space_worktree_root_canvas_uq UNIQUE(root_canvas_id)`.
- `space_worktree_provenance_ck`, `space_worktree_lifecycle_state_ck`, and `space_worktree_lifecycle_generation_ck`.
- `space_worktree_root_canvas_fk` is a deferred owner, worktree, root Canvas tuple reference.

Current M:N objects:

- Table `space_worktree_link`.
- Primary key `(owner, space_id, worktree_id)`.
- `space_worktree_link_space_fk` to `space(owner, space_id) ON DELETE CASCADE`.
- `space_worktree_link_worktree_fk` to `space_worktree(owner, worktree_id) ON DELETE CASCADE`.
- Function `worktree_in_space(text, uuid, uuid)`. It gives every owner Worktree computed membership in the default Space, while named Spaces use `space_worktree_link`.
- Function `validate_named_space_worktree_link` and trigger `space_worktree_link_named_space_check`.
- Function `validate_default_space_membership` and trigger `space_default_computed_membership_check`.
- Constraint names `space_worktree_link_named_space_ck` and `space_default_computed_membership_ck`.

Canvas containment already has reusable N:1 structure:

- `canvas_anchor_worktree_fk` cascades an anchored Canvas tree when its Worktree row is deleted.
- `canvas_parent_fk` cascades Canvas descendants.
- `canvas_default_worktree_fk` is deferred and uses `ON DELETE NO ACTION`. S3 delete must clear foreign default references before deleting the target Worktree.
- `validate_space_worktree_root_pair`, `space_worktree_root_pair_check`, and `canvas_worktree_root_pair_check` protect the Worktree root pair and should remain.

S3 schema reshape:

- Remove `space.is_default`, `space_default_owner_uq`, and every backend default lock or computed default path. Backend cardinality becomes 0..N equal, deletable Spaces.
- Add required Worktree ownership through `space_worktree.space_id` and an owner safe foreign key to `space`.
- Replace `space_worktree_workspace_uq` and `space_worktree_path_uq` with `UNIQUE(space_id, canonical_os_path)`. The storage query can expose `canonical_os_path AS path` so the public `StoredWorktree.path` and `WorktreeRecord.path` contracts do not need a second path concept.
- Drop `space_worktree_link`, `worktree_in_space`, both M:N validation functions, both M:N triggers, and their constraint names.
- Rewrite Space inventory, Worktree list, and Canvas list joins to use `space_worktree.space_id`.

### 2. M:N surface to delete

Store:

- `api/src/transport_matters/space/store_space_ops.py::_SPACE_INVENTORY_SELECT_SQL` uses `worktree_in_space` for both Worktrees and Canvases. Replace it with direct `w.space_id = s.space_id` ownership and a Canvas join through the anchor Worktree.
- `SpaceStoreSpaceOps.add_worktree_link`.
- `SpaceStoreSpaceOps.remove_worktree_link`.
- `SpaceStoreWorktreeOps.worktree_in_space`.
- `SpaceStoreWorktreeOps.list_worktrees` uses the predicate and must become a direct ownership query.
- `SpaceStoreCanvasOps.list_canvases` uses the predicate and must join through the owning Worktree.
- `SpaceStore` exposes all of these through its mixins even though the facade declares no duplicate methods.

Service:

- `space_mutations.DEFAULT_SPACE_LINK_CONSTRAINT`.
- `space_mutations.link_worktree`.
- `space_mutations.unlink_worktree`.
- `SpaceCrudService.link_worktree`.
- `SpaceCrudService.unlink_worktree`.
- `SpaceCrudService._require_worktree_in_space` is reusable only as an ownership guard backed by the Worktree row. Its SQL predicate dependency must disappear.
- Default selection dependencies to remove with the M:N model: `SpaceStoreSpaceOps.ensure_default_space`, `authz.require_default_space`, and `SpaceCrudService._default_caller`.

REST:

- `space_routes.LinkWorktreeRequest`.
- `space_routes.link_worktree`, `POST /spaces/{space_id}/links`.
- `space_routes.unlink_worktree`, `DELETE /spaces/{space_id}/links/{worktree_id}`.
- The `space_default_locked` mapping in `space_routes._raise_crud_error` becomes stale once all Spaces are equal.

MCP:

- `SpaceMcpAdapter.space_link_worktree`.
- `SpaceMcpAdapter.space_unlink_worktree`.
- `_space_link_worktree`.
- `_space_unlink_worktree`.
- Nested registration tools `register_space_mcp_tools.space_link_worktree` and `register_space_mcp_tools.space_unlink_worktree`.
- Tool names `space_link_worktree` and `space_unlink_worktree` in the MCP skin allowlist.

Shared TypeScript client:

- `www/packages/core/src/spaceTransport.ts::linkWorktree`.
- `www/packages/core/src/spaceTransport.ts::unlinkWorktree`.

Tests that directly encode links or computed membership:

- `space/test_store.py::test_reconcile_creates_one_default_space_without_membership_links`.
- `space/test_store.py::test_default_membership_is_computed_and_named_membership_uses_links`.
- `space/test_store.py::test_default_space_rejects_explicit_worktree_links`.
- `space/test_store.py::test_worktree_link_writes_are_idempotent`.
- `space/test_store.py::test_delete_named_space_cascades_only_membership_links`.
- `space/test_service.py::test_store_exposes_the_service_repository_contract`.
- `space/test_service.py::test_every_space_mutation_requires_director_authority`.
- `space/test_service.py::test_space_mutation_failures_are_typed`.
- `space/test_service.py::test_space_lifecycle_is_visible_through_existing_read_paths`.
- `space/test_service.py::test_link_worktree_maps_a_concurrent_space_delete`.
- `space/test_service.py::test_launch_resolution_consumes_canonical_membership_predicate`.
- `space/test_service.py::test_launch_resolution_preserves_explicit_named_space_context`.
- `space/test_service.py::test_reconcile_preserves_named_membership_until_an_explicit_link`.
- `space/test_space_crud_migration.py::_insert_root_pair`.
- `space/test_space_crud_migration.py::assert_space_crud_schema_present`.
- `space/test_space_crud_migration.py::test_owner_cannot_have_two_default_spaces`.
- `space/test_space_crud_migration.py::test_default_space_membership_cannot_be_materialized`.
- `space/test_space_crud_migration.py::test_canvas_tree_constraints_and_lookup_index_match_the_final_schema`.
- `space/test_space_crud_migration.py::test_worktree_delete_cascades_root_subtree_and_membership_then_commits`.
- `space/test_space_crud_migration.py::test_space_delete_cascades_membership_without_deleting_worktree`.
- `api/v1/test_space_routes.py::test_space_crud_routes_close_the_write_to_read_feedback_loop`.
- `api/v1/test_space_routes.py::test_space_crud_routes_share_typed_error_statuses`.
- `api/v1/test_space_routes.py::test_every_space_crud_mutation_requires_a_trusted_origin`.
- `api/v1/test_space_mcp.py::test_space_mcp_mutations_use_an_owner_scoped_director_caller`.
- `api/v1/test_space_mcp.py::test_space_mcp_failures_match_the_rest_error_contract`.
- `api/v1/test_controlplane_action_skins.py` tool allowlist assertion.
- `space/test_reshape_structure.py::test_space_mutation_boundaries_keep_the_service_facade`.
- `www/packages/core/src/spaceTransport.test.ts` link and unlink transport cases and the mutation failure table.

These tests should be deleted when they assert the retired contract. Tests that also cover authorization, typed failures, route origin checks, or root Canvas cascades should be rewritten around create, rename, direct ownership, and the new delete contract.

### 3. Current CRUD state

Space create:

- Store: `SpaceStoreSpaceOps.create_named_space`.
- Service: `SpaceCrudService.create_space` delegates to `space_mutations.create_space`.
- REST: `space_routes.create_space`, `POST /spaces`.
- MCP: `SpaceMcpAdapter.space_create`, `_space_create`, and `register_space_mcp_tools.space_create`.
- TypeScript: `spaceTransport.createSpace`.

Space list and read:

- Store: `list_spaces`, `count_spaces`, `get_space`, `get_space_inventory`, and `list_space_inventories`.
- Service: `list_spaces`, `count_spaces`, and `get_space_snapshot`.
- REST: `list_spaces`, `GET /spaces`; `get_space`, `GET /spaces/{space_id}`.
- MCP: `space_list` and `space_get` are ABSENT. MCP only receives a Space projection as the result of create or rename.
- REST returns `showSwitcher = count_spaces(owner) > 1`.

Space rename:

- Store: `rename_space`, currently rejects the default row with `NOT is_default`.
- Service: `SpaceCrudService.rename_space` delegates to `space_mutations.rename_space`.
- REST: `space_routes.rename_space`, `PATCH /spaces/{space_id}`.
- MCP: `SpaceMcpAdapter.space_rename`, `_space_rename`, and `register_space_mcp_tools.space_rename`.

Space delete today:

- Store: `SpaceStoreSpaceOps.delete_space` executes one owner scoped `DELETE FROM space ... AND NOT is_default`.
- Service: `SpaceCrudService.delete_space` delegates to `space_mutations.delete_space`.
- REST: `space_routes.delete_space`, `DELETE /spaces/{space_id}`.
- MCP: `SpaceMcpAdapter.space_delete`, `_space_delete`, and `register_space_mcp_tools.space_delete`.
- It is row only application behavior. Because Worktrees are M:N peers rather than children, the database cascades only `space_worktree_link` rows. Worktree and Canvas rows survive. It performs no run inventory or termination.

Workdir CRUD:

- `create_workdir`, `delete_workdir`, `worktree_create`, and `worktree_delete` are ABSENT from store, service, REST, MCP, and TypeScript transport.
- Current materialization is detection driven through `SpaceStoreWorktreeOps.upsert_worktree`, `SpaceCrudService.reconcile_detection`, `SpaceCrudService.resolve_cwd`, and `POST /spaces/resolve`.
- `reconcile_detection` silently calls `ensure_default_space`, then globally upserts by `(owner, workspace_slug, workspace_hash)`.
- `main._resolve_current_space` and `meta._resolve_launch_worktree` invoke cwd based materialization. This is a backend bootstrap composite and conflicts with client composed `create_space`, then `create_workdir`.

### 4. Frontend CMDK and active Space state

Palette location:

- `www/packages/canvas/src/launcher/CommandCenter.tsx::CommandCenter` owns the Ark Combobox for the command center.
- `useCommandCenter`, `useLauncherData`, `useLauncherRows`, `buildScopeRows`, and `CanvasCommandDispatcher.useCanvasCommandHandler` own state, queries, row grammar, and command dispatch.

Current Space and Workdir behavior:

- `useSpaces` uses React Query key `["spaces"]` and `spaceTransport.fetchSpaces`.
- `useSpaces` returns only `SpaceSummary[]`. It returns an empty array whenever REST `showSwitcher` is false, so the sole Space is hidden entirely.
- `buildSpaceRows` lists Space rows in the Workdir scope. A one Worktree Space executes `select-worktree`; a multi Worktree Space descends to `buildWorktreeRows`.
- `CanvasCommandDispatcher` handles `select-worktree` by replacing the route tuple and reinitializing the Canvas store.
- There is no `select-space`, `create-space`, `rename-space`, or `delete-space` `LauncherCommand`.

Current Canvas behavior:

- `useCanvases` uses React Query key `["canvases", spaceId]` and `spaceTransport.fetchCanvases`.
- `buildCanvasRows` lists the active Space's Canvas tree and emits `select-canvas`.
- `CanvasCommandDispatcher` handles `select-canvas` through `canvasSwitchUrl` and `initializeVerifiedCanvas`.
- CMDK has Canvas list and switch only. It has no Canvas create, rename, or delete rows.
- `spaceTransport.createCanvas` and `spaceTransport.updateCanvas` exist, but CMDK does not use them. Canvas delete is ABSENT from the current backend and TypeScript transport.

Current frontend Space state:

- There is no dedicated Space store.
- React Query owns the Space inventory list.
- `useCanvasStore` owns the active route context: `spaceId`, `canvasId`, `defaultWorktreeId`, and `launch`.
- Space and Canvas switching currently update URL state, then call `initializeCanvas`.
- An empty Space has no Worktree root Canvas, so active Space selection must support `spaceId` with null `canvasId` and null `defaultWorktreeId`. Reusing `useCanvasStore.spaceId` avoids a second active Space authority, but it requires a direct `select-space` action rather than routing every selection through a verified Canvas tuple.

Progressive disclosure target:

- Always expose `Create new space`.
- While owner count is 0 or 1, hide the Space name, list, switch, rename, and delete controls.
- Once owner count is greater than 1, expose list, switch, rename, and delete.
- Keep last Space delete prevention in CMDK only. REST, MCP, service, store, and schema must permit zero Spaces.
- `useSpaces` must return the full response or a structured result containing items, count or `showSwitcher`, status, and refetch. It cannot keep discarding the sole item because the create row and client composed bootstrap need the real inventory state.

### 5. REST and MCP parity structure

Shared application authority:

- Both adapters instantiate `SpaceCrudService` with one database connection.
- Store and mutation logic belongs behind `SpaceCrudService`. New adapter methods should remain parsing and serialization shells.
- `space_contracts.SpaceSummary`, `space_contracts.space_summary`, `WorktreeRecord`, and `CanvasRecord` are shared serialized authorities.

REST path:

- `space_routes` parses IDs and request models, builds `rest_director_caller` or `rest_caller`, calls `SpaceCrudService`, maps `SpaceCrudError` through `_raise_crud_error`, and serializes through `response_payload`.

MCP path:

- `SpaceMcpAdapter._invoke` resolves the principal, opens the pool connection, builds `SpaceCrudService`, constructs a Director caller or calls `resolve_workspace_caller`, maps `SpaceCrudError` to `SpaceCrudFailure`, and serializes through `mcp_tool_result`.
- Private MCP helpers call the same service methods as REST and wrap shared records in typed result models.

N:1 parity issue:

- `SpaceCrudService.resolve_workspace_caller` currently calls `find_worktree_by_workspace(owner, workspace_slug, workspace_hash)`.
- `find_worktree_by_workspace` and `find_worktree_by_path` are globally owner scoped. Both become ambiguous when the same OS directory has separate Workdir rows in multiple Spaces.
- `CaptureFacts` already stores `space_id` and `worktree_id`, but `ControlPlanePrincipal` exposes only `workspace_id`. The clean reuse is to thread the live capture's owned `space_id` and `worktree_id` into `ControlPlanePrincipal` and `CrudCaller`, then bind MCP reads to that tuple. Adding another workspace based inference would recreate the deleted computed membership model.

## Quality Map

Required replacement coverage:

- Migration shape: no link table, no default marker, Worktree owns `space_id`, owner safe cascade FK, and exact path uniqueness.
- Same canonical path in the same Space conflicts.
- Same canonical path in two Spaces creates two Worktree rows with distinct IDs.
- Zero Spaces is valid. Every Space row can be renamed and deleted at the backend.
- Space inventory, Worktree list, Canvas list, launch resolution, and MCP caller resolution all use direct ownership.
- Deleting a Worktree cascades its anchored Canvas tree after clearing foreign `default_worktree_id` references.
- Deleting a Space cascades its Worktrees and Canvases.
- Session, wire, transcript IR, and FK free affinity stamps survive inventory deletion.
- REST and MCP expose the same typed success and error contracts through `SpaceCrudService`.
- CMDK always shows create. It exposes list, switch, rename, and delete only when Space count exceeds one.
- Client bootstrap is two calls. Create a Space, then create its Workdir with that `space_id`.

Existing reusable guards:

- `test_reshape_structure.py::test_space_mutation_boundaries_keep_the_service_facade` protects one service authority.
- `test_reshape_structure.py::test_space_neutral_seams_import_in_fresh_interpreters` protects neutral module imports.
- `test_private_import_boundary.py` protects public module boundaries.
- `space/test_space_crud_migration.py` already exercises deferred root pair integrity and Canvas cascade mechanics.
- `api/v1/test_space_routes.py` and `api/v1/test_space_mcp.py` already provide parity shaped fixtures and typed error assertions.
- `www/packages/core/src/spaceTransport.contract.test.ts` and `spaceTransport.test.ts` protect shared transport shape.
- `launcher/commandRows.test.ts`, `useSpaces.test.tsx`, `useCommandCenter.test.tsx`, and `CanvasCommandDispatcher` tests are the natural CMDK contract points.

Structural risks:

- `SpaceCrudService` is 596 lines, `space_routes.py` is 564, and `space_mcp.py` is 499. New Workdir mutation logic should use a focused mutation module rather than pushing these files toward the 700 line limit.
- `resolve_cwd`, `resolve_session_cwd`, `_default_caller`, `resolve_canvas_caller`, `resolve_worktree_caller`, `resolve_workspace_caller`, and `canvas_commands._canvas_record` all embed default or cwd only inference. Leaving any one unchanged creates incorrect cross Space selection.
- `POST /spaces/resolve` and `main._resolve_current_space` currently perform implicit backend bootstrap. They must not remain as a parallel composite beside explicit `create_space`, then `create_workdir`.
- The current REST list response has pagination plus a transactionally consistent owner count. Preserve that snapshot behavior while removing `isDefault`.

## Plan

### Internal PR 1: S3 schema backend

1. Author the Alembic reshape:
   - Drop the M:N table, functions, triggers, constraints, and default marker.
   - Add `space_worktree.space_id`.
   - Add the owner safe Space foreign key with `ON DELETE CASCADE`.
   - Replace owner global path and workspace uniqueness with `UNIQUE(space_id, canonical_os_path)`.
   - Preserve Canvas anchor, parent, and root pair constraints.
2. Move ownership into shared models:
   - Add `space_id` to `StoredWorktree`.
   - Let `ProjectedWorktree`, `WorktreeRecord`, `ResolvedWorktree`, and row decoders reuse that stored authority.
3. Use the STEP 0 modules as intended:
   - `store_space_ops.py`: Space create, rename, list, count, get, and direct inventory aggregation. Delete default and link methods.
   - `store_worktree_ops.py`: strict `create_workdir(space_id, detected, owner)`, direct ownership reads, scoped path and workspace lookup, detection refresh, and protected root creation.
   - `store_canvas_ops.py`: direct Canvas list through anchor Worktree ownership.
   - `store_records.py`: decode `space_id` once.
   - `store.py`: remain the stable facade only.
4. Remove `link_worktree`, `unlink_worktree`, link request models, REST routes, MCP tools, TypeScript clients, allowlist entries, and tests.
5. Remove the old `delete_space` store, service, REST, MCP, and TypeScript surface in this PR. Do not leave the link only behavior under the same command name.
6. Keep create, list, get, and rename on the shared service. Add missing MCP list and get parity.
7. Replace default inference with explicit or owned identity:
   - Reconciliation and create Workdir take `space_id`.
   - Worktree and Canvas records derive Space from their owning Worktree.
   - MCP caller binding consumes live capture `space_id` and `worktree_id`.
   - Remove implicit default creation from `main._resolve_current_space`, `resolve_cwd`, and `/spaces/resolve`, or reshape them into explicit Space scoped operations with no service composite.
8. Keep strict create behavior: same path in the same Space returns typed `conflict`; the same path in another Space creates another row. Detection refresh may update an existing owned row, but the user facing create primitive must not upsert.

### Internal PR 2: S3 delete backend

1. Add new `delete_workdir` and `delete_space` mutations as one complete behavior:
   - Reuse `RunManagementPort.list_runs` and `RunManagementPort.terminate_run`.
   - Filter by the exact target `worktree_id` or `space_id`.
   - Attempt every run stop and continue after individual failures.
   - Clear foreign `canvas.default_worktree_id` references when deleting a Worktree.
   - Delete the inventory row only after stop attempts. Let the N:1 foreign keys cascade owned inventory.
   - Never touch the detected OS directory.
2. Put row deletion in the owning STEP 0 modules:
   - `SpaceStoreWorktreeOps.delete_workdir`.
   - `SpaceStoreSpaceOps.delete_space`.
   - Keep run coordination in a service mutation module, not in SQL store methods.
3. Restore delete commands together across service, REST, MCP, and TypeScript transport.
4. Prove session, wire, transcript IR, and affinity stamps remain after inventory cascade.

This boundary leaves no interval where `delete_space` retains the old meaning. PR 1 has no delete command. PR 2 introduces the new run aware cascade command atomically.

### Internal PR 3: S3 CMDK

1. Keep this separate from schema and delete. It consumes stable backend contracts and avoids coupling migration review to interaction state.
2. Change `useSpaces` to preserve full inventory and disclosure state.
3. Add `create-space`, `select-space`, `rename-space`, and `delete-space` command rows and dispatcher paths.
4. Always show `Create new space`. Show list, switch, rename, and delete only when owner count exceeds one.
5. Reuse `useCanvasStore.spaceId` as the active Space authority. Add a direct selection action that supports an empty Space with null Canvas and Worktree.
6. In the zero Space bootstrap, compose `createSpace`, then `createWorkdir(spaceId, path)`. Do not add a backend composite.
7. Keep Canvas list and switch behavior unchanged. Canvas create, rename, and delete belong to their Canvas CRUD slice.

Recommended count: three internal PRs, in order: schema backend, delete backend, CMDK.

Decision needed: the newest S3 brief and slice map place inventory only `create_workdir(space_id)` in Internal PR 1, while `~/.mdx/projects/tm-s3-spec-v2.md` reserves `create_workdir` for the later disk provisioning slice. Resolve the name and placement before build. Recommendation: include a detected, no disk mutation Workdir create in PR 1, reserve git worktree provisioning for the later created provenance slice, and source MCP active Space binding from live `CaptureFacts.space_id` and `CaptureFacts.worktree_id`.
