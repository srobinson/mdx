# S3 schema GPT review

Range: `57d1f087..1962bf82`  
Branch and head: `ml/s3-schema` at `1962bf82484066460f06eaa89b95960229e6f803`  
Verdict: **CHANGES REQUESTED**  
Counts: **1 Blocker, 1 Major, 1 Minor**  
Builder trust: **LOW until the launch authority chain is repaired**

## Blocker

### B1. A service launch can promote client supplied owner and Space identity into MCP authority

`api/src/transport_matters/api/v1/run_proxy.py::create_run` forwards the trusted origin request body and query unchanged. `packages/runtime/src/server/runtimeRouter.ts::registerRunRoutes` accepts `owner` from the query and `spaceId`, `worktreeId`, and `canvasId` from the body, then `packages/runtime/src/service/RunManager.ts::createNew` forwards those values to capture.

`api/src/transport_matters/api/v1/capture_rpc_routes.py::_resolved_domain_request` validates the tuple when `canvas_id` is present, or resolves `worktree_id` when `directory` is absent. A `launchKind: "service"` request with an explicit directory and supplied `spaceId` or `worktreeId` bypasses both branches. `api/src/transport_matters/capture_rpc.py::CaptureLeaseRegistry.prepare_capture` stores those unverified values in `_CaptureRunFacts`; `CaptureLeaseRegistry.resolve_control_plane_grant` copies them into `ControlPlanePrincipal`; `api/src/transport_matters/api/v1/space_mcp.py::SpaceMcpAdapter._invoke` promotes them to `CrudCaller.allowed_space_id` and `allowed_worktree_id`.

Impact: a client can launch an observer grant with a selected owner and Space tuple, then read inventory outside the run's actual Workdir. Supplying only `spaceId` grants Space wide list access because list operations require the bound Space and do not require the bound Workdir.

Required closure:

1. Resolve every supplied affinity tuple through the owner scoped Space store, including service launches with an explicit directory.
2. Require a coherent pair and verify that the canonical launch directory belongs to the resolved Workdir.
3. Derive owner from a trusted server boundary.
4. Store only the resolved tuple in `_CaptureRunFacts`.
5. Add a hostile end to end test from `POST /v1/runs` through the live grant resolver and MCP caller.

## Major

### M1. Control plane child launches drop the live owned tuple

`api/src/transport_matters/controlplane/launch_service.py::ControlPlaneLaunchService._execute` creates `GatewayCreateRunRequest` with `workdir`, `workspace_root`, and `workspace_id`, while omitting `space_id` and `worktree_id`. `api/src/transport_matters/controlplane/run_models.py::GatewayCreateRunRequest` has no fields for that tuple, and `api/src/transport_matters/api/v1/controlplane_gateway_runs.py::create_run` cannot serialize it.

The child capture therefore records null Space identity. `SpaceMcpAdapter._invoke` constructs a caller with both allowed IDs null, so observer child runs fail `worktree_list`, `canvas_list`, `worktree_get`, and `canvas_get` at the new owned identity guards. This is a regression from replacing workspace or default inference with explicit ownership.

Required closure: extend the typed launch request and gateway serializer to carry a server verified Space and Workdir tuple. If a child may target a different Workdir, make that ID explicit and validate it against the parent's owned Space. Do not restore path or workspace inference.

## Minor

### m1. Detached CLI bootstrap scans projected inventory instead of using the exact path lookup added in this range

`api/src/transport_matters/cli/space_bootstrap.py::bootstrap_cli_space` calls `SpaceCrudService.list_spaces(limit=10_000)`, flattens every projected Workdir, and repeats canonical path matching in Python. `api/src/transport_matters/space/service.py::SpaceCrudService.list_spaces` performs filesystem detection for every inventoried Workdir. The same range adds the owner scoped exact query `api/src/transport_matters/space/store_worktree_ops.py::SpaceStoreWorktreeOps.list_worktrees_by_path`, but no production caller uses it.

Impact: each detached launch is proportional to all inventoried paths, can touch unrelated disks, and treats a matching Workdir after the 10,000 Space cap as absent.

Required closure: expose the exact owner and canonical path lookup through `SpaceCrudService` and use it in the client composition helper.

## Verified contracts

- Active production code contains none of `ensure_default_space`, `require_default_space`, `_default_caller`, `_resolve_current_space`, `resolve_cwd`, `resolve_session_cwd`, or `resolve_workspace_caller`.
- `POST /v1/spaces/resolve` and the link and unlink routes are absent.
- Detached CLI bootstrap composes `create_space` then strict `create_workdir`; `/api/meta` reads the explicit launch affinity.
- Migration 0032 makes `space_worktree.space_id` required, enforces `UNIQUE(space_id, canonical_os_path)`, and removes active computed membership.
- `SpaceStoreWorktreeOps.create_workdir` inserts without conflict update. `worktree_mutations.create_workdir` translates the named uniqueness violation to typed `conflict`.
- `SpaceStoreWorktreeOps.reconcile_worktree` is the only conflict update and preserves Workdir ID, root Canvas ID, and provenance.
- `resolve_worktree_caller`, `resolve_canvas_caller`, and `canvas_commands._canvas_record` derive Space identity from stored Workdir ownership.
- Every changed file is below 700 lines.

## Builder trust

- Craftsmanship: strong schema constraints, owner scoped queries, mutation modules, and shared service facade.
- Test rigor: focused store, service, REST, MCP, migration, and CLI tests exist. The trust tests inject a principal or call capture directly, so they do not exercise the client to grant authority chain that contains B1. No test covers tuple propagation through a control plane child launch.
- Spec and reuse fidelity: N:1 ownership and strict create are faithful. Launch authority and child propagation are incomplete. The CLI scan bypasses the exact lookup introduced beside it.
- Shortcuts: the manual principal tests and full inventory bootstrap conceal boundary behavior.

No repository gates were run, per review instructions.
