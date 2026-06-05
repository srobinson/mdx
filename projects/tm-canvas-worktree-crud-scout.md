# Canvas and Worktree CRUD foundation scout

Date: 2026-07-22

## Scope and baseline

This is a read only audit and implementation plan for full CRUD on `space.models.Canvas` and `space.models.Worktree` across CMDK and MCP.

The checkout was verified before review:

- Branch: `feat/multi-launch`
- Head: `b094e80d69ad7d57c5bba0ff8f4d71a986a837f2`
- Tracked tree: clean
- Existing untracked state: `.serena/`

The governing sources were:

- `LAUNCH-CONTRACT.md`
- `/Users/alphab/.mdx/projects/tm-multilaunch-canvas-relationship.md`
- Current source at the verified head
- Relevant git history and Context Matters records

The code review and code hygiene review methods were applied after the scope was read. No production code, tests, or repository documents were changed. No tests were run because this task authorizes an external report only.

## Executive verdict

The foundation is ready for a shared CRUD application layer, but it is not ready for independent CMDK and MCP implementations.

Four constraints govern the design:

1. Durable Canvas records use UUIDs. The visible Canvas uses synthetic identities such as `space:<spaceId>`, workspace hashes, and `direct-local`.
2. Canvas layout has two potential authorities: Postgres and browser local storage. The browser does not consume the server Canvas API.
3. Safe Worktree deletion has no owner. The required Git, runtime, database, and launch concurrency checks span existing boundaries.
4. REST and MCP have different trust inputs. REST currently accepts an owner query value. MCP derives an owner and workspace from its bearer principal.

Both surfaces should call one Python application service. That service should own policy, validation, lifecycle coordination, receipts, and error semantics. REST, MCP, and CMDK should remain adapters.

## Search record

The audit searched production code, tests, migrations, and history for the entity models, routes, stores, transport contracts, launcher commands, MCP tools, Git operations, runtime filters, and deletion statements.

Representative searches:

```text
rg "create_canvas|list_canvases|update_canvas|delete_canvas|get_canvas" api/src/transport_matters
rg "create_worktree|update_worktree|delete_worktree|archive_worktree" api packages www
rg "git worktree (add|remove|move|prune)" api packages www
rg "DELETE FROM canvas|DELETE FROM space_worktree|SET archived" api
rg "select-worktree|create.*canvas|rename.*canvas|delete.*canvas" www/packages/canvas
rg "@mcp.tool|create_control_plane_mcp" api/src/transport_matters/api/v1
```

Results:

- Canvas production ownership includes list, create, and update. Individual get and delete primitives are absent.
- Worktree production ownership includes detection, reconciliation, get, resolve, and list. User initiated create, update, archive, and delete primitives are absent.
- Production code has no `git worktree add`, `remove`, `move`, or `prune` operation.
- CMDK supports Worktree selection and local Canvas view commands. It has no entity CRUD commands.
- MCP has no Space, Canvas, or Worktree tools.
- Database code has no public Canvas or Worktree deletion statement.

## Current ownership by entity and operation

### Canvas

| Operation | Current owner | CMDK | MCP | Gap |
|---|---|---|---|---|
| Create | `SpaceStore.create_canvas`, exposed by `space_routes.create_canvas` | None | None | No shared service, browser client, or mutation workflow |
| Read | `SpaceStore.list_canvases`, exposed by `space_routes.list_space_canvases` | None | None | List only. Individual get is absent |
| Update | `SpaceStore.update_canvas`, exposed by `space_routes.patch_canvas` | None | None | Route owns validation. Explicit null cannot clear the default Worktree |
| Delete | None | None | None | Archive and hard delete semantics are undefined |

Current related owners:

- `space.models.Canvas` owns the durable UUID model.
- `canvasStoreLifecycle.initializeCanvas` and `canvasCacheStorage.createCanvasCacheStorage` own visible pane and layout persistence in the browser.
- `route.defaultCanvasId` owns the synthetic default Canvas identity.
- `canvasActions.clearCanvas` clears local panes. It is not a durable Canvas delete operation.

### Worktree

| Operation | Current owner | CMDK | MCP | Gap |
|---|---|---|---|---|
| Create | `SpaceStore._upsert_worktree`, invoked by detection only | None | None | No user operation or `git worktree add` adapter |
| Read | `SpaceStore.get_worktree`, `list_worktrees`, and `resolve_worktree`; REST list route; browser `fetchWorktrees` | List and select | None | Browser caller is test only. DTOs drift from the server |
| Update | `SpaceStore._upsert_worktree` reconciles detected facts | None | None | No user mutation. Rename, move, label, and archive meanings are undefined |
| Delete | None | None | None | No Git removal, dirty check, runtime guard, or durable cleanup command |

Current related owners:

- `space.detection.detect_space` owns Git observation through `git worktree list`.
- `launch_resolution.resolve_run_worktree` owns launch availability checks for missing and archived Worktrees.
- `RunManager.list` and the runtime router can filter registered runs by Worktree ID.
- No service spans Git mutation, runtime inventory, launch exclusion, and Postgres reconciliation.

## Surface gap map

| Entity operation | REST today | CMDK today | MCP today |
|---|---|---|---|
| Canvas create | Partial | Missing | Missing |
| Canvas read list | Present | Missing | Missing |
| Canvas read one | Missing | Missing | Missing |
| Canvas update | Partial | Missing | Missing |
| Canvas delete | Missing | Missing | Missing |
| Worktree create | Missing | Missing | Missing |
| Worktree read list | Present | Present | Missing |
| Worktree read one | Store only | Missing | Missing |
| Worktree update | Missing | Missing | Missing |
| Worktree delete | Missing | Missing | Missing |

`refresh=true` on the Worktree list route also performs detection writes. A future MCP observation should not inherit that hidden mutation without an explicit contract.

## Reuse map

Fourteen existing seams should be reused or promoted:

1. `space.models` for IDs and durable domain rows.
2. Migration constraints for Space, Worktree, Canvas, and default Worktree references.
3. `space.detection` for Git observation and canonical identity inputs.
4. `SpaceStore.get_worktree`, `list_worktrees`, and `resolve_worktree` for current Worktree reads.
5. `SpaceStore.list_canvases`, `create_canvas`, and `update_canvas` for current Canvas persistence behavior.
6. `space_routes` DTO projections, same Space validation, and same origin checks as inputs to extraction.
7. `@tm/core` request handling and existing Space and Worktree read contracts.
8. React Query and `useSpaces` as the query and invalidation integration point.
9. Launcher command grammar, row builders, and `CanvasCommandDispatcher` for CMDK adaptation.
10. Canvas route identity, cache lifecycle, and cache storage for an explicit UUID migration.
11. Pane Worktree identity and captured run ownership policies for local placement cleanup.
12. Runtime Worktree filtering and termination operations behind a dedicated inventory port.
13. Control plane principal resolution, Director authorization, structured errors, and audit conventions.
14. MCP authentication, adapter delegation, tool registration, and result envelopes.

These are reuse seams, not complete CRUD primitives. Several require extraction so that new callers share policy rather than copy route behavior.

## Missing primitive map

Twelve primitives are missing:

1. A neutral `SpaceCrudService` with typed caller context, commands, results, receipts, and stable errors.
2. An owner scoped Canvas get by ID repository operation that replaces route local SQL.
3. Browser Canvas DTOs, queries, mutations, and selection based on server UUIDs.
4. Canvas patch field presence semantics plus an explicit layout authority and version policy.
5. Canvas deletion with cache invalidation, pane handling, run policy, and fallback navigation.
6. A Git Worktree create adapter and command.
7. A defined Worktree update operation and command.
8. A safe Worktree deletion preflight and operation.
9. An atomic server side launch gate or lease that covers pending and registered runs by Worktree.
10. Cross reference cleanup for Canvas defaults, sessions, pane caches, and query state.
11. CMDK CRUD commands, rows, confirmation, progress, error, and receipt feedback for both entities.
12. MCP CRUD tools and schemas for both entities, implemented through the shared service.

## Quality map

### Authority and boundary findings

1. `space.models.Canvas`, `route.defaultCanvasId`, `canvasStoreLifecycle.initializeCanvas`
   
   Durable UUIDs and visible local Canvas IDs are separate authorities. A server deletion or archive has no effect on the rendered Canvas or its local cache. A malformed or foreign URL Canvas ID can create a durable local storage namespace without server validation.

2. `SpaceStore.create_canvas`, `SpaceStore.update_canvas`, `space_routes._require_worktree_in_space`
   
   Store mutations do not own same Space validation. The database foreign keys also do not guarantee that a default Worktree belongs to the Canvas Space or owner. A direct MCP store caller could bypass the current route invariant.

3. `space_routes`, `ControlPlaneMcpAuthApp`, `_McpControlPlaneAdapter`
   
   REST accepts a caller supplied owner query value. MCP derives authority from a bearer principal. The shared service needs typed caller context and must derive allowed owner and Space scope from each trusted adapter.

4. `ResolveSpaceRequest`, `space_routes.resolve_space`, `space.detection.detect_space`
   
   CWD resolution accepts any absolute path accessible to the process and returns discovered Worktree paths. An equivalent MCP tool would expose filesystem enumeration unless it is constrained to the principal workspace or an approved Space.

5. `ControlPlanePrincipal`, `ControlPlaneService`
   
   MCP identity contains owner and workspace context, but no direct Space authority. Human policy must define whether a Director can mutate every Space owned by the principal or only the Space resolved from its workspace.

### Canvas correctness findings

6. `PatchCanvasRequest`, `SpaceStore.update_canvas`
   
   Omitted `defaultWorktreeId` and explicit null both become `None`. SQL `COALESCE` preserves the existing value, so the API cannot clear it. Patch commands need field presence tracking or a sentinel.

7. `space_routes._require_worktree_in_space`, `launch_resolution.resolve_run_worktree`
   
   Canvas default validation checks membership but accepts missing and archived Worktrees. The resulting Canvas can save successfully and fail on every launch.

8. `space.models.Canvas.layout_version`, `SpaceStore.update_canvas`
   
   Layout replacement neither checks nor advances `layout_version`. If this field represents concurrency, multi writer updates can overwrite silently. If it represents a schema format, its name and contract should say so.

9. `canvasActions.clearCanvas`, `capturedRunStore.stopRun`
   
   Local Clear Canvas has mixed run behavior. Canvas owned runs are terminated through fire and forget requests. Adopted service runs are forgotten without termination. This behavior cannot serve as server Canvas delete without an explicit policy and aggregated receipt.

10. `route.worktreeSwitchUrl`, `LauncherCommand`, `workdirRows`
    
    Selecting a Worktree deletes an explicit `canvas_id` from the URL and returns to the synthetic Space Canvas. It cannot update a durable Canvas default Worktree.

### Worktree lifecycle findings

11. `SpaceStore._upsert_worktree`
    
    Detection sets `archived = false` on every matched Worktree. A user archive would be reversed by refresh unless user intent is represented separately from detected facts.

12. `launch_resolution.resolve_run_worktree`, `RunManager.createNew`, `RunManager.list`
    
    Launch releases its database check before capture preparation, PTY spawn, and registration. A delete can observe no run after launch has already passed availability validation. Pending creates are absent from runtime filters.

13. `ManagedRunFilters`, `RunManager.list`, `transport.listRuns`
    
    Exact state filtering cannot answer whether any run is pending, running, or terminating in one atomic operation. Browser `listRuns` also discards pagination after the first fifty results. Worktree deletion safety belongs server side behind a dedicated atomic operation.

14. `0006_spaces_foundation.upgrade`
    
    Session Space and Worktree IDs have indexes without foreign keys. Hard deletion can leave durable session references that no longer resolve.

15. `SpaceStore._claim_git_space`, `SpaceStore._lookup_space_for_detection`
    
    Repository identity is globally unique while lookup is owner scoped. Resolving the same repository under a second owner can lose the identity claim and then fail to find the winner.

16. `RunManager.DEFAULT_SPACE_ID`, `RunManager.DEFAULT_WORKTREE_ID`, `RuntimeRunView`
    
    Production runtime views can expose stub Space and Worktree identities. They have no Canvas identity. CRUD safety must reject unresolved identity instead of treating fixture values as durable references.

### Read model, dead projection, and performance findings

17. `space_routes.WorktreeSummary`, `transport.WorktreeSummary`, `workdirRows`
    
    Backend Worktree path is nullable and the response includes archived state. TypeScript requires a path and omits archived state. Archived records remain selectable while launch later rejects them.

18. `SpaceStore.list_spaces`
    
    A page of Spaces performs one Space query and one Worktree query per Space. CRUD invalidation and CMDK refresh will amplify this linear database access.

19. `SpaceStore._write_cache`, `SpaceStore.update_space`
    
    The filesystem Space cache has no production reader. Detection writes it, while later Space mutations do not refresh it and Canvas state is absent. It is a stale parallel projection unless retained as documented diagnostic output.

20. `space.testing`, `test_store._detected_worktree`, `test_space_routes._worktree`
    
    Space tests duplicate detected Worktree and Git detection builders with different defaults. CRUD tests should promote shared parameterized builders into `space.testing`.

### Size and decomposition findings

The following current files constrain implementation placement:

| File or symbol | Current size | Required response |
|---|---:|---|
| `SessionCanvasRoute.test.tsx` | 707 lines | Refactor before adding any test code |
| `test_controlplane_skins.py` | 695 lines | Put CRUD adapter tests in focused files |
| `RunManager.ts` | 664 lines | Add an inventory port outside this file |
| `runtimeRouter.test.ts` | 656 lines | Put Worktree lifecycle tests in focused files |
| `space/store.py` | 627 lines | Split persistence ownership before material growth |
| `canvasActions.ts` | 554 lines | Keep entity deletion orchestration outside this file |
| `core/transport.ts` | 525 lines | Split Space and Canvas transport before full CRUD |
| `controlplane_mcp.py` | 515 lines | Extract focused tool registration before adding CRUD tools |
| `runtimeRouter.registerRunRoutes` | 158 lines | Refactor before adding another route responsibility |
| `useCommandCenter` | 143 lines | Add focused hooks rather than CRUD branches here |

`SpaceStore`, `RunManager`, and MCP registration have limited growth room. New services, ports, transports, tool registrars, and focused test files should preserve the project limits.

## Human decisions

### Decision 1: v1 operation and surface matrix

Approve the exact v1 matrix before implementation:

| Operation | CMDK candidate | MCP candidate | Scope question |
|---|---|---|---|
| Canvas create | Yes | Yes | Metadata only, or create plus layout hydration? |
| Canvas read list and one | Yes | Yes | Include archived records by default? |
| Canvas update | Yes | Yes | Name and default Worktree only, or layout too? |
| Canvas delete | Pending policy | Pending policy | Archive, local layout removal, and run handling need a decision |
| Worktree create | Yes | Yes | Must this execute `git worktree add`? |
| Worktree read list and one | Yes | Yes | Can MCP see the full owner inventory or only its Space? |
| Worktree update | Pending definition | Pending definition | Rename label, move path, archive, branch change, or a selected subset? |
| Worktree delete | Pending policy | Pending policy | Dirty state, primary checkout, runs, sessions, and force need decisions |

The minimum coherent v1 includes read parity on both surfaces and all mutations through the shared service. Layout mutation and destructive Worktree operations can be held until their policies are approved.

### Decision 2: delete semantics

This is the highest risk human decision.

Canvas questions:

- Does delete archive metadata, remove browser cache and panes, or perform both?
- Do Canvas owned runs continue, terminate, or detach?
- What happens to adopted service runs?
- What is the fallback route after deleting the active Canvas?
- Are durable sessions or run history linked to a deleted Canvas in the future?

Worktree questions:

- Does delete archive an inventory row or execute `git worktree remove`?
- Are dirty and untracked files always blocking?
- Is force supported in v1?
- Is the primary checkout protected unconditionally?
- Do live, pending, and terminating runs block, terminate, or detach?
- Are session references retained, cleared, or tombstoned?
- What state is recorded if Git removal succeeds but database reconciliation fails?

No frontend preflight can make Worktree removal safe. The service needs a server side lifecycle gate that blocks new launches, observes pending and registered runs, performs the chosen Git operation, and returns a structured receipt.

### Decision 3: shared twin client service path

Approve one shared Python application service as the authority for both skins:

```text
CMDK -> browser transport -> REST adapter -> SpaceCrudService
MCP  -> authenticated tool adapter       -> SpaceCrudService
                                      -> repositories
                                      -> Git worktree port
                                      -> run inventory and launch gate port
                                      -> audit and event ports
```

The service should accept typed trusted caller context. REST derives local authority through its origin and configured owner policy. MCP derives authority from its bearer principal. The service resolves targets, enforces same Space rules, coordinates lifecycle operations, and emits the same typed results and errors for both adapters.

Direct `SpaceStore` calls from MCP, duplicated route validation, and browser owned deletion safety should be excluded by structure and tests.

## PR sized implementation plan

### PR 1: shared service and read parity

Purpose: establish the authority before adding mutation surfaces.

- Add a focused CRUD application service with typed caller context, commands, results, receipts, and errors.
- Add owner scoped individual Canvas and Worktree reads.
- Move route local Canvas SQL and same Space validation behind the service.
- Define archived list policy and align browser DTOs with nullable path and lifecycle state.
- Split Space and Canvas browser transport from the crowded general transport module.
- Split focused Space tool registration from `controlplane_mcp.py`.
- Add CMDK list and select for durable Canvases plus complete Worktree query state, retry, and errors.
- Add MCP read tools with Director and Observer policy tests.

Verification:

- Focused service tests for owner, Space, archived, missing, and nullable path behavior.
- REST and MCP parity tests for results and error codes.
- CMDK tests for loading, empty, error, retry, archived, and selection behavior.
- `just check`
- `just test-affected`

### PR 2: Canvas create and update convergence

Purpose: connect server Canvas identity to the visible application.

- Add create and update commands through the shared service.
- Make named Canvas URLs, active state, and local cache keys use the durable UUID.
- Define migration or fallback behavior for current synthetic cache keys.
- Fix omitted versus explicit null patch semantics.
- Reject missing and archived default Worktrees.
- Apply input limits for labels and layout payloads.
- Implement the approved layout authority and version policy, or explicitly exclude layout mutation from v1.
- Add CMDK and MCP commands using the same result and error contracts.

Verification:

- Explicit null clear and omitted field preservation tests.
- Same Space, foreign Space, missing, archived, and concurrent update tests.
- Browser cache identity migration and hydration tests.
- Surface parity tests.
- `just check`
- `just test-affected`

### PR 3: Canvas delete

Purpose: implement the approved Canvas delete policy end to end.

- Add an archive or delete command with a structured receipt.
- Coordinate active route fallback, query invalidation, local cache, pane bindings, and run behavior.
- Preserve or remove server layout according to the approved authority.
- Keep local Clear Canvas behavior separate unless its ownership policy becomes identical.
- Emit an event so other clients invalidate stale Canvas state.

Verification:

- Active and inactive Canvas deletion tests.
- Owned and adopted run policy tests.
- Failed termination, partial cleanup, retry, and idempotency tests.
- Cross client invalidation test.
- `just check`
- `just test-affected`

### PR 4: Worktree create and approved update operations

Purpose: add safe Git mutation without placing subprocess behavior in persistence.

- Extract a reusable Git Worktree adapter from detection conventions.
- Implement `git worktree add` and the approved update subset.
- Validate path scope, collisions, branch state, target Space, and caller authority.
- Reconcile detection once after success and return the resulting durable Worktree.
- Preserve user archive intent separately from detected facts.
- Add CMDK and MCP commands through the shared service.

Verification:

- Temporary Git repository integration tests for add, collision, duplicate, branch, path, and subprocess failure.
- Reconciliation and idempotency tests.
- Surface parity tests.
- `just check`
- `just test-affected`

### PR 5: Worktree delete lifecycle

Purpose: implement destructive behavior only after policy approval.

- Introduce a Worktree lifecycle state or lease that blocks new launches.
- Add a small run inventory port that answers live, pending, and terminating status atomically.
- Enforce primary checkout, dirty state, untracked file, and force policy.
- Apply the chosen run termination or conflict behavior.
- Execute the Git removal through the adapter.
- Reconcile durable state, Canvas defaults, session references, cache state, and query state.
- Return a structured receipt for every completed, skipped, or failed phase.
- Add CMDK confirmation and MCP confirmation or explicit force token behavior.

Verification:

- Dirty, untracked, primary checkout, active run, pending launch, terminating run, and force tests.
- Launch and delete concurrency test.
- Git success with database failure recovery test.
- Retry and idempotency tests.
- Surface parity tests.
- `just check`
- `just test-affected`

## Completion criteria for implementation

The implementation is complete when:

- CMDK and MCP call one application service for every approved operation.
- Canvas identity and layout authority are explicit and tested.
- Worktree deletion cannot race a launch or overlook active work.
- Browser and MCP authorization produce the same allowed target set under their approved policies.
- Archive, delete, missing, and default Worktree semantics are consistent across persistence, launcher state, and launch resolution.
- Each slice passes `just check` and `just test-affected`.
- Relevant files remain within the repository size and function limits.

## Audit verification

The report reflects the verified head and current source. The repository remained unchanged during the audit. The pre-existing untracked `.serena/` directory remained untouched.
