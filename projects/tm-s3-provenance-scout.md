# S3 provenance reuse map

Baseline: `feat/multi-launch` at
`7ffba78b9feeafda5799cc5d032ee2712d4f8907`.

No repository writes or gates were performed.

## 1. Workdir provenance marker

Reuse Map: `api/src/transport_matters/space/models.py::WorktreeProvenance`
is **PRESENT** with exact values `DETECTED = "detected"` and
`CREATED = "created"`.

Reuse Map: `api/src/transport_matters/space/models.py::StoredWorktree.provenance`
stores the marker on the durable entity.
`api/src/transport_matters/space/models.py::WorktreeRecord.provenance`
preserves it on the public record.

Reuse Map:
`api/migrations/versions/0030_space_crud_reset.py::_create_final_space_worktree`
persists `provenance` and constrains it to `detected` or `created`.

## 2. Workdir create path

Reuse Map:
`api/src/transport_matters/space/service.py::SpaceCrudService.reconcile_detection`
calls
`api/src/transport_matters/space/store.py::SpaceStore.upsert_worktree`,
the only production Workdir materialization path. The store insert hard codes
`provenance = 'detected'`.

Reuse Map:
`api/src/transport_matters/space/store.py::SpaceStore.ensure_worktree_root`
creates the protected root Canvas after inventory materialization.

**ABSENT:** no Workdir create method exists on `SpaceCrudService`, no REST
Workdir create route exists in `space_routes.py`, and no MCP Workdir create
tool exists in `space_mcp.py`. No production symbol sets provenance to
`created`.

The existing detection path is DB only. It runs read only Git discovery through
`space/detection.py::detect_space` and `space/detection.py::_run_git`
with `git worktree list --porcelain -z`. It performs no `git worktree add` and
no directory creation.

## 3. Workdir delete path

Reuse Map: **NONE** for a product Workdir delete symbol. There is no Workdir
delete method in `SpaceStore` or `SpaceCrudService`, no REST Workdir delete
route, and no MCP Workdir delete tool.

Reuse Map:
`api/migrations/versions/0030_space_crud_reset.py::_create_final_canvas`
already gives the Canvas anchor foreign key `ON DELETE CASCADE`.
`api/src/transport_matters/space/test_space_crud_migration.py::test_worktree_delete_cascades_root_subtree_and_membership_then_commits`
proves that a raw Workdir row delete removes its Canvas subtree and membership.

`api/src/transport_matters/space/store.py::SpaceStore.delete_space` deletes only
the named Space row. Under the current link schema, that removes membership and
leaves the Workdir row. It performs no filesystem operation and does not branch
on Workdir provenance.

Delete provenance awareness: **NO**.

## 4. Detection reconciliation

Reuse Map:
`api/src/transport_matters/space/service.py::SpaceCrudService.reconcile_detection`
flows through `SpaceStore.upsert_worktree`.

The insert assigns `detected`. On workspace identity conflict, the update
changes only `path` and `updated_at`; it does not update `provenance` or
`root_canvas_id`. Re-detection therefore preserves an existing `created`
marker and root identity.

Reuse Map:
`api/src/transport_matters/space/test_reconciliation.py::test_detection_refresh_preserves_created_provenance_and_root_identity`
directly guards this behavior.

## 5. Clean check and Workdir removal helpers

Reuse Map:
`api/src/transport_matters/harnesses/certification_minting.py::require_clean_worktree`
is **PRESENT**. It runs
`git status --porcelain --untracked-files=all`, rejects tracked or untracked
changes, then returns `git rev-parse HEAD`. Its exception type and message are
certification specific.

Reuse Map: `api/src/transport_matters/space/detection.py::_run_git` is a private
read only Git command runner used for detection. It has no clean check or
mutation policy.

**NONE:** no Git Workdir removal helper, `git worktree remove` wrapper, directory
cleanup helper for created Workdirs, dirty digest, force policy, or
provenance-aware cleanup path exists at HEAD.

## Summary

Marker: **present**.

Production setter for `created`: **absent**.

Workdir delete: **absent**.

Delete provenance-aware: **no**.
