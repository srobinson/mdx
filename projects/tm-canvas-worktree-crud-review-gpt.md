# Canvas and Worktree CRUD peer review

Date: 2026-07-22

## Scope and evidence

This review covers `tm-canvas-worktree-crud-scout.md` and
`tm-canvas-worktree-crud-decision-surface.md` against `feat/multi-launch` at
`b094e80d69ad7d57c5bba0ff8f4d71a986a837f2`.

The commit matches the requested baseline. Tracked files were clean before review. The
preexisting untracked `.serena/` directory was present before review and remained untouched.
This was a static, read only review. No tests ran and no repository files changed.

## Verdict

The shared `SpaceCrudService` direction is sound. The plan is not buildable under the locked
subtree and cascade stop semantics yet. Current code has no server owned Canvas to run edge,
pane membership lives in browser storage, and pane close deliberately leaves service adopted
runs alive. A server delete therefore cannot enumerate the resources it promises to stop or
prove that sibling Canvases remain unaffected.

I sign off conditional on:

1. Add server owned Canvas tree and run ownership or affinity contracts before Canvas delete.
2. Define a persisted Worktree lifecycle lease that covers pending capture, registered runs,
   and plain terminals before Worktree delete.
3. Specify the idempotent delete state machine for partial termination, retry, database commit,
   and client reconciliation.
4. Correct the reuse map and PR slices to include the existing close, capture lease, dirty
   status, and terminal seams named below.

## Findings

### 1. Blocker: subtree deletion has no authoritative membership

`api/src/transport_matters/space/models.py::Canvas` stores durable Canvas identity, default
Worktree, and an opaque layout. `www/packages/canvas/src/model/paneRecords.ts::CanvasModel`
stores panes in the active browser model, and
`www/packages/canvas/src/infrastructure/persistence/canvasCacheStorage.ts::createCanvasCacheStorage`
persists that model in local storage. No browser path synchronizes pane membership into the
server `layout` field.

`packages/runtime/src/service/runManagerTypes.ts::CreateManagedRunInput` and
`packages/runtime/src/domain/runtimeRun.ts::RuntimeRunView` carry Space and Worktree identity,
with no Canvas identity. `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx::createCapturedRunAdoptionReconciler`
adopts a service run into whichever Canvas store is active. This does not establish durable
ownership.

The proposed pane close reuse also differs from the live contract.
`www/packages/canvas/src/model/capturedRunLifecycle.ts::capturedRunLifecyclePolicy` delegates to
`www/packages/canvas/src/model/capturedRunStore.ts::stopRun`. That method terminates only a
Canvas originated run. It removes a service adopted run from local state and leaves the process
alive. A run can also be presented from another Canvas cache or another browser. Terminating it
while deleting one Canvas would affect that sibling presentation, contrary to the locked rule
that siblings remain untouched.

The minimum contract required before PR 3 is:

- `parent_canvas_id` on the durable Canvas row.
- One exclusive owning Canvas identity on every managed run that Canvas deletion may stop.
- A separate presentation binding if one run may appear in several Canvases. Deleting a binding
  removes that pane. Deleting the owning Canvas stops the run. A sibling binding cannot silently
  change ownership.
- Optional Canvas affinity threaded through the one launch request, frozen launch facts, capture
  request, runtime view, and batch candidate. Ad hoc launch and `launch_batch` then use the same
  field and service.
- An explicit rule for unassigned service runs. They remain outside any Canvas subtree until a
  service operation assigns ownership.

Plain terminal panes need the same ownership decision.
`packages/runtime/src/service/PlainTerminalSessions.ts::PlainTerminalSessions` describes them as
socket scoped shells with no owner or REST surface. A server Canvas delete cannot enumerate or
close them. Either promote them into Canvas and Worktree scoped managed resources, or exclude
them from the cascade contract explicitly. The current locked wording includes panes, so the
first option is coherent.

### 2. Blocker: the Worktree lifecycle gate misses the critical race window

`api/src/transport_matters/api/v1/launch_resolution.py::resolve_run_worktree` reads availability
and releases its database connection before capture preparation. In
`packages/runtime/src/service/RunManager.ts::createNew`, capture preparation and PTY spawn happen
before `RunManager.register`. `RunManager.list` sees only the registered map. Its
`pendingCreates` map has no Worktree inventory surface.

`api/src/transport_matters/capture_rpc.py::CaptureLeaseRegistry` is an existing, omitted seam.
After preparation, its `_facts` records owner, Space, and Worktree for every live capture lease.
It still cannot close the earlier window between Worktree resolution and lease registration.
`PlainTerminalSessions` bypasses capture registration altogether.

A delete check based on `RunManager.list` can therefore observe no run after launch has passed
availability validation. It can also miss a live plain shell whose current directory is the
target Worktree.

The service needs a persisted Worktree lifecycle authority shared across Python and the Node
runtime:

1. A launch transaction acquires a Worktree lease only while the Worktree state is `active`.
   The lease exists before filesystem preparation and remains owned through pending creation,
   registered execution, termination, and capture release.
2. Plain terminal open acquires the same class of lease with its Canvas and Worktree identity.
3. Delete atomically changes the Worktree from `active` to `deleting` only when policy permits.
   That transition blocks every later lease before any Git operation.
4. Existing leases either block delete or are stopped and awaited according to one explicit
   policy. A `TERMINATING` resource remains a lease holder until cleanup finishes.
5. Deletion checks dirtiness only after managed writers are quiescent. It checks again immediately
   before Git removal while the lifecycle state still blocks new managed writers.

`api/src/transport_matters/harnesses/certification_minting.py::require_clean_worktree` already
runs `git status --porcelain --untracked-files=all`. Refactor its Git observation into a neutral,
structured status port used by certification and Worktree deletion. Deletion needs separate
tracked and untracked facts plus a digest for confirmation, so directly importing the
certification policy would be the wrong dependency.

Force confirmation must bind owner, Worktree ID, canonical path, HEAD, exact dirty snapshot,
operation, and expiry. If any bound fact changes, the service requires a new confirmation. A raw
`force=true` boolean cannot prove that the caller confirmed the bytes being discarded.

### 3. Major: the Canvas tree migration and cycle rules are absent

The decision artifacts predate the locked tree decision. They contain no `parent_canvas_id`
schema, create or update field, traversal contract, or migration slice.

A safe additive migration after
`api/migrations/versions/0029_native_connection_origin.py` should:

- Add nullable `parent_canvas_id`. Existing rows become roots, so no data rewrite or inferred
  backfill is required.
- Add an index on `(owner, space_id, parent_canvas_id)` for subtree reads.
- Add `CHECK (parent_canvas_id IS NULL OR parent_canvas_id <> canvas_id)`.
- Enforce parent scope in the database with a composite self reference over owner, Space, and
  Canvas identity, or an equivalent constraint. A plain self foreign key permits a cross Space
  parent.
- Define delete behavior deliberately. `ON DELETE CASCADE` gives atomic metadata subtree
  removal, while the service must still stop resources first. `RESTRICT` requires explicit
  leaf first deletion. Either choice must have a test that direct persistence cannot create an
  orphan.
- Extend migration convergence tests in
  `api/src/transport_matters/session/test_migrate.py` and keep the revision identifier within the
  schema limit.

A foreign key cannot prevent an ancestor loop. Create, reparent, and subtree delete must
serialize on the target `(owner, space_id)`, through a database advisory lock or equivalent.
Reparent then performs a recursive ancestor query while that serialization is held. Traversal
must carry a visited set and a fixed depth ceiling, and fail closed on a repeated ID or exceeded
depth. This protects reads and deletion even if corrupt rows enter through an administrative
path. The same transaction validates that the parent is present, active, and in scope.

Without serialization, concurrent `A -> B` and `B -> A` updates can each pass an independent
cycle check and commit a two node loop.

### 4. Major: runtime stop is reusable server side, with different route semantics

The live stop route is `POST /v1/runs/{runId}/terminate`, implemented by
`packages/runtime/src/server/runtimeRouter.ts::registerRunRoutes` and proxied by
`api/src/transport_matters/api/v1/run_proxy.py::RunRouteProxy.terminate_run`. The browser helper
`www/packages/core/src/transport.ts::terminateRun` uses that POST route. There is no live
`DELETE /runs/{id}` path.

There is already a server side bulk close primitive.
`api/src/transport_matters/controlplane/service.py::ControlPlaneService.close` normalizes run IDs,
scopes them, fans out through
`api/src/transport_matters/controlplane/activity.py::RunManagementPort.terminate_run`, and returns
per run `closed`, `failed`, or `unknown` receipts under one dispatch. Both
`api/src/transport_matters/api/v1/controlplane_routes.py::close` and
`api/src/transport_matters/api/v1/controlplane_mcp.py::_McpControlPlaneAdapter.close` delegate to
that service. This is the strongest existing twin client and bulk stop precedent.

Canvas deletion should extract or reuse that close coordinator. A second bulk termination loop
inside `SpaceCrudService` would violate the project DRY rule. The existing close path still needs
Canvas ownership input and the lifecycle freeze from finding 1.

Runtime termination and Postgres deletion cannot form one transaction. The plan needs an
idempotent state machine:

1. In one database transaction, lock and freeze the exact subtree and its owned resources, mark
   the subtree `deleting`, and reject create, reparent, adoption, and launch into it.
2. Outside that transaction, stop the frozen run set through the shared close coordinator and
   await all receipts.
3. If any receipt is `failed` or `unknown`, retain the `deleting` state and Canvas rows. Return the
   complete receipt. A retry operates on the same frozen operation and never stops a newly
   discovered sibling resource.
4. After every owned resource is terminal, delete the subtree and update durable cross
   references in one transaction. Commit a mutation record and notification with the same
   operation ID.
5. Browser clients remove local cache and pane bindings on notification. Because notifications
   can be missed, Canvas open and list reconciliation must also purge local state for a missing
   or deleted server Canvas.

Successful stops cannot be rolled back after a later failure. The receipt and retry contract must
say so. Holding a database transaction open during process termination would create long locks
and still would not add atomicity.

### 5. Major: twin client scope is sound, but its trust and confirmation contracts need one owner

The proposed direction matches the existing control plane precedent:

```text
CMDK -> REST adapter -> SpaceCrudService
MCP  -> MCP adapter  -> SpaceCrudService
```

Current Space routes accept `owner` as a query value. MCP obtains owner and workspace from
`api/src/transport_matters/controlplane/models.py::ControlPlanePrincipal`. CRUD mutations must
construct trusted caller context in each adapter. The REST adapter should derive local owner from
configured policy and origin, rather than forwarding an arbitrary query value into the service.
The MCP adapter should pass the resolved principal. The service owns target scope, authorization,
policy, confirmation, receipts, audit, and event emission.

Destructive operations should use the same prepare and execute command on both surfaces. Prepare
returns a server minted confirmation token bound to the exact subtree or dirty Worktree snapshot.
CMDK renders that receipt. MCP returns it as structured data. Execute consumes it through the same
service. This keeps confirmation semantics identical without moving safety into the browser.

The PR plan also needs reconciliation with the locked v1 decisions. Its current matrix still
marks Canvas delete and Worktree delete as policy gated, Worktree update as deferred, and the
Canvas tree as absent. A builder cannot infer the approved Worktree update subset, parent mutation
surface, or Canvas run ownership from that text. Update the decision artifact before implementation
so each PR has stable inputs.

## Reuse map disposition corrections

All fourteen named reuse entries resolve to real code at the pinned commit. The following
dispositions need correction:

| Area | Corrected disposition |
| --- | --- |
| Runtime filter and terminate | Refactor across `RunManager.list`, `CaptureLeaseRegistry`, `RunManagementPort`, `ControlPlaneService.close`, `RunRouteProxy.terminate_run`, and `PlainTerminalSessions`. `RunManager` alone is incomplete. |
| Dirty Worktree preflight | Refactor `require_clean_worktree` into a neutral structured Git status port. This capability is partial, rather than wholly missing. |
| Canvas delete | Split into tree persistence, exclusive run ownership, presentation bindings, deletion coordination, and client reconciliation. One server primitive cannot own browser local storage. |
| Cross reference cleanup | Server transactions own durable rows. Clients own local cache removal. A durable version or tombstone plus reconnect reconciliation joins the two. |
| Bulk run stop | Reuse or extract `ControlPlaneService.close` and its receipt types. Do not add a parallel fanout implementation. |

The stated count of twelve missing primitives should change after this decomposition. Several are
existing seams that need promotion, while Canvas deletion expands into distinct authorities.

The file size claims in the scout were also verified. The named files and functions match the
reported sizes at this commit, so the proposed extraction work remains required before adding code.

## Slice corrections

The current five PR sequence can remain, with these contract changes:

1. PR 1 adds `SpaceCrudService`, typed callers, read parity, `parent_canvas_id`, tree reads, and
   the neutral Git status and lifecycle port contracts.
2. PR 2 migrates visible Canvas identity, implements parent create and reparent with cycle
   serialization, and threads optional owning Canvas affinity through the one launch contract.
3. PR 3 implements the Canvas deletion state machine, shared close coordinator, exclusive
   membership freeze, durable mutation notification, and reconnect reconciliation.
4. PR 4 implements Git Worktree create and the explicitly approved update subset through the
   neutral Git adapter.
5. PR 5 implements the persisted Worktree lease, RunManager and capture registry integration,
   plain terminal integration, dirty confirmation, Git removal, and recovery receipts.

This shape preserves ad hoc launch and batch evolution. A batch candidate carries the same
optional Canvas affinity as a single launch. No batch specific Canvas service or adoption loop is
needed later.

## Required proof before implementation sign off

- Concurrent reparent tests for self parent, ancestor loop, two writer cycle, depth bound, and
  cross Space parent.
- Subtree delete tests proving siblings and ancestors are unchanged.
- Canvas delete tests for Canvas originated runs, service assigned runs, plain terminals, shared
  presentation bindings, failed stop, unknown stop, retry, and disconnected client cache.
- Worktree delete tests for launch before gate, launch after gate, pending capture, registered run,
  terminating run, plain terminal, dirty tracked files, untracked files, changed confirmation
  snapshot, primary checkout, and Git success with database failure.
- REST and MCP contract fixtures proving identical results, error codes, confirmation tokens,
  authorization scope, receipts, and audit facts.
- Launch and batch contract tests proving Canvas affinity reaches frozen facts and runtime views
  through one service path.
- Repository gates from the project recipes: `just check` and `just test-affected` for every slice.

