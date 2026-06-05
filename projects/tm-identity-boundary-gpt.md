# Space identity package boundary

## Verdict

Create `@tm/space` at `packages/space`.

`@tm/space` is a TypeScript product plane context package. Space is the top level
aggregate. Worktree and Canvas identities exist inside that aggregate. The name
`@tm/identity` would hide this domain ownership and invite unrelated identifiers.
`WorkspaceId` remains the path derived capture identity owned by Activity. It is
separate from `WorktreeId`.

Browser code never imports `@tm/space`. Add `@tm/contract/space` as the wire
subpath for REST and MCP DTOs. Canvas imports that contract and its own API
adapter. Gateway imports `@tm/space` through its public barrel.

The root public authority is:

```text
@tm/space
  SpaceContextService.resolveActingContext
    verifies one complete Space, Worktree, Canvas tuple
    applies the only source precedence rule
    returns ActingContext or a typed resolution failure
```

`ActingContext` is the canonical aggregate for current selection and launch
authority:

```ts
type ActingContext = Readonly<{
  ownerId: OwnerId
  spaceId: SpaceId
  worktreeId: WorktreeId
  canvasId: CanvasId
}>
```

The actual domain value may carry verified Worktree path, workspace identity,
Canvas anchor, lifecycle state, and names required by existing consumers. Its
three identifiers are mandatory. It has no `verified` flag. Package code alone
constructs it after repository verification. A caller can hold no context or one
complete context. Incomplete and unverified states use input DTOs and typed
errors, never `ActingContext`.

## Evidence and existing seams

The design followed these searches:

* `rg` over production TypeScript and Python for the three ID declarations and
  all lower case field forms.
* `rg` over Canvas routing, persistence, CMDK, Runtime, control plane, capture,
  Session, MCP, and REST symbols.
* package manifest and import graph inspection to establish allowed planes.
* `git show df052e65^` to establish the old resolver's mutation behavior.
* `git show 068f989e` and `git show 32129cdf` to inspect both rejected fixes.
* both scout reports, both reviews, and the rehydration evidence.

No current symbol is the required owner:

| Existing symbol | Reuse | Why it cannot own the boundary |
| --- | --- | --- |
| `packages/activity/src/ids.ts:WorkspaceId` | Keep as a foreign identifier | It describes canonical path capture identity, not Space membership. |
| `api/src/transport_matters/session/affinity.py:SessionAffinityStamp` | Convert to a projection of `ActingContext` | It is complete, but it is a Session launch carrier with no selection precedence or current state authority. |
| `api/src/transport_matters/session/affinity.py:validate_affinity_group` | Preserve its all or absent rule at the compatibility boundary | It validates shape only. |
| `api/src/transport_matters/api/v1/launch_resolution.py:resolve_run_canvas` | Move its membership checks behind the Space port | It verifies one request tuple, but owns no source precedence or current selection. |
| `api/src/transport_matters/api/v1/launch_resolution.py:resolve_run_worktree` | Move its Worktree checks behind the Space port | It accepts the service pair, which is the incomplete launch shape this pass removes. |
| `www/packages/canvas/src/route.ts:CanvasLaunchContext` | Keep only as a raw route candidate until cutover | Its fields are nullable and it mixes source representation with authority. |
| `www/packages/canvas/src/route.ts:CanvasIdentitySource` | Delete after cutover | Its nullable tuple and `canvasIdVerified` permit states the domain must reject. |
| `api/src/transport_matters/controlplane/models.py:ControlPlanePrincipal` | Change to carry `ActingContext` | It currently loses Canvas and therefore cannot prove launch placement. |
| `www/packages/core/src/spaceTransport.ts` | Split and delete | Core owns no domain and currently combines domain types, wire DTOs, and browser HTTP. |
| `@tm/common` | No identity additions | It is generic foundation and may not learn Space concepts. |
| `@tm/contract` | Add the `space` wire subpath only | Contract owns serializable DTOs, not repositories, precedence, or use cases. |

The old Python resolver cannot be restored. At `df052e65^`,
`SpaceCrudService.resolve_session_cwd` called `resolve_cwd(create=True)` and
could reach `_materialize_missing_worktree`. A read or launch could therefore
seed inventory. Every new resolution path must be structurally read only.

## Canonical package shape

```text
packages/space/
  package.json
  src/
    index.ts
    domain/
      ids.ts
      actingContext.ts
      space.ts
      worktree.ts
      canvas.ts
      errors.ts
    events.ts
    service/
      SpaceContextService.ts
      SpaceCrudService.ts
    ports.ts
    adapters/
      PostgresSpaceRepository.ts
      GitWorktreeProbe.ts
    projections/
      actingContext.ts
      inventory.ts
    server/
      spaceRouter.ts
  fixtures/
    actingContextCases.ts
```

This is one Node package. Do not create a second Python domain implementation.

These parts carry real responsibility:

* `domain/ids.ts` brands `SpaceId`, `WorktreeId`, and `CanvasId`.
* `domain/actingContext.ts` makes completeness unrepresentable outside the
  package constructor.
* `domain/space.ts`, `worktree.ts`, and `canvas.ts` own membership, anchor, and
  lifecycle invariants.
* `service/SpaceContextService.ts` owns source precedence and verification.
* `service/SpaceCrudService.ts` absorbs the existing inventory mutations.
* `ports.ts` describes persistence, Git observation, ownership, and clock
  dependencies.
* `adapters/` binds the existing Postgres schema and Git probes.
* `projections/` maps domain values to contract DTOs.
* `server/spaceRouter.ts` exposes one use case surface for REST and MCP adapters.
* `fixtures/actingContextCases.ts` gives Canvas, Gateway, and Python compatibility
  tests one shared precedence table.
* `src/index.ts` is the only external entry.

`events.ts` is canonical package ceremony until a real subscriber exists. Keep
an explicit empty event map or defer the file with a documented exception.
Inventing a Space event bus during identity extraction would add an owner with
no consumer.

## Declaration inventory

### Current declarations

| File and symbol | Action |
| --- | --- |
| `packages/activity/src/ids.ts:RunId` | Stay in Activity. |
| `packages/activity/src/ids.ts:WorkspaceId` | Stay in Activity. |
| `www/packages/core/src/spaceTransport.ts:SpaceId` | Move to `packages/space/src/domain/ids.ts:SpaceId`. Delete the bare alias. |
| `www/packages/core/src/spaceTransport.ts:WorktreeId` | Move to `packages/space/src/domain/ids.ts:WorktreeId`. Delete the bare alias. |
| `www/packages/core/src/spaceTransport.ts:CanvasId` | Move to `packages/space/src/domain/ids.ts:CanvasId`. Delete the bare alias. |
| `www/packages/canvas/src/model/paneRecords.ts:CanvasId` | Delete the duplicate. Browser values come from `@tm/contract/space`. |
| `api/src/transport_matters/space/models.py:SpaceId` | Replace with a compatibility decoder for the contract during cutover, then delete. |
| `api/src/transport_matters/space/models.py:WorktreeId` | Replace with a compatibility decoder for the contract during cutover, then delete. |
| `api/src/transport_matters/space/models.py:CanvasId` | Replace with a compatibility decoder for the contract during cutover, then delete. |

`@tm/contract/space` represents identifier fields as validated UUID strings.
Brands remain inside `@tm/space`. Browser code consumes a complete
`ActingContextView` receipt and does not claim domain construction authority.

### Types and operations leaving browser Core

| Current file and symbols | Destination |
| --- | --- |
| `www/packages/core/src/spaceTransport.ts:RepoGroupKey` | `@tm/contract/space` if it remains on the wire, otherwise `@tm/space`. |
| `www/packages/core/src/spaceTransport.ts:CanvasKind` | `@tm/contract/space` wire enum plus `@tm/space` domain enum. |
| `www/packages/core/src/spaceTransport.ts:WorktreeProvenance` | Same split as `CanvasKind`. |
| `www/packages/core/src/spaceTransport.ts:WorktreeLifecycleState` | Same split as `CanvasKind`. |
| `www/packages/core/src/spaceTransport.ts:WorktreeSummary` | `@tm/contract/space`. |
| `www/packages/core/src/spaceTransport.ts:CanvasPathSegment` | `@tm/contract/space`. |
| `www/packages/core/src/spaceTransport.ts:CanvasSummary` | `@tm/contract/space`. |
| `www/packages/core/src/spaceTransport.ts:UpdateCanvasPatch` | `@tm/contract/space`. |
| `www/packages/core/src/spaceTransport.ts:SpaceSummary` | `@tm/contract/space`. |
| `www/packages/core/src/spaceTransport.ts:SpaceListResponse` | `@tm/contract/space`. |
| `www/packages/core/src/spaceTransport.ts:FetchSpacesOptions` | Canvas API adapter input. |
| `www/packages/core/src/spaceTransport.ts:fetchSpaces` | Canvas Space API adapter. |
| `www/packages/core/src/spaceTransport.ts:createSpace` | Canvas Space API adapter calling the Space service route. |
| `www/packages/core/src/spaceTransport.ts:renameSpace` | Canvas Space API adapter calling the Space service route. |
| `www/packages/core/src/spaceTransport.ts:deleteSpace` | Canvas Space API adapter calling the Space service route. |
| `www/packages/core/src/spaceTransport.ts:createWorkdir` | Canvas Space API adapter calling the Space service route. |
| `www/packages/core/src/spaceTransport.ts:deleteWorkdir` | Canvas Space API adapter calling the Space service route. |
| `www/packages/core/src/spaceTransport.ts:fetchWorktrees` | Canvas Space API adapter. |
| `www/packages/core/src/spaceTransport.ts:fetchWorktree` | Canvas Space API adapter. |
| `www/packages/core/src/spaceTransport.ts:fetchCanvases` | Canvas Space API adapter. |
| `www/packages/core/src/spaceTransport.ts:fetchCanvas` | Canvas Space API adapter. |
| `www/packages/core/src/spaceTransport.ts:createCanvas` | Canvas Space API adapter calling the Space service route. |
| `www/packages/core/src/spaceTransport.ts:updateCanvas` | Canvas Space API adapter calling the Space service route. |
| `www/packages/core/src/index.ts:export * from "./spaceTransport"` | Delete. No permanent compatibility barrel. |

## Aggregate construction and reader boundaries

The package exposes parsers for individual branded IDs only at machine input
boundaries. Those parsers do not create an aggregate.

`ActingContext` construction occurs through these readers:

1. `PostgresSpaceRepository` reads a Space, Worktree, and Canvas under one owner,
   validates membership, Worktree lifecycle, and Canvas anchor, then returns
   package records.
2. `SpaceContextService.resolveActingContext` receives whole candidate DTOs,
   asks the repository to verify each eligible candidate in precedence order,
   and constructs the aggregate.
3. Gateway REST and MCP decoders reject partial candidate groups before calling
   the service.
4. Canvas URL and persistence readers create raw `ActingContextCandidateDto`
   values. They cannot create `ActingContext`.
5. Canvas response decoding accepts the complete service issued
   `ActingContextView` receipt as one value.
6. The Python capture bridge decodes a complete context receipt during migration.
   `SessionAffinityStamp` becomes a Session projection of that receipt.

Required failures are explicit:

* `PARTIAL_CONTEXT`
* `SPACE_NOT_FOUND`
* `WORKTREE_NOT_FOUND`
* `WORKTREE_INACTIVE`
* `CANVAS_NOT_FOUND`
* `CANVAS_WORKTREE_MISMATCH`
* `OWNER_MISMATCH`
* `MALFORMED_ID`

Resolution never creates a Space, Worktree, Canvas, Git worktree, or database
row. The repository interface used by `resolveActingContext` exposes read
methods only. This interface split is the structural no seeding proof.

## One precedence rule

`SpaceContextService.resolveActingContext` receives:

```ts
type ActingContextSources = Readonly<{
  explicit: ActingContextCandidateDto | null
  url: ActingContextCandidateDto | null
  persistedReceipt: ActingContextCandidateDto | null
  metaBootstrap: ActingContextCandidateDto | null
}>
```

Each candidate is a whole tuple. Fields from different candidates are never
combined.

Space only CMDK navigation is outside `ActingContext`. It uses a Canvas owned
`navigationSpaceId`, clears the current context atomically, and cannot launch or
persist a context receipt. A Worktree row already supplies its root Canvas, and
a Canvas row supplies its default Worktree, so both acting selections are
complete explicit candidates.

The rule is:

1. An explicit user selection has highest priority. Verify it. A malformed,
   missing, inactive, foreign, or mismatched selection returns a visible error.
   No lower source may substitute for it.
2. A scoped URL is next. Verify it as a whole tuple. A partial or stale scoped
   URL returns a visible error. No lower source may substitute for it.
3. A persisted service receipt is considered only when the URL is unscoped.
   Reverify it. If it is stale, discard that cache entry and continue to meta.
4. Meta is the final bootstrap candidate for an unscoped route with no valid
   persisted receipt. Reverify it. Meta never overwrites a scoped or explicit
   choice.
5. With no verified candidate, return no active context plus the appropriate
   typed resolution state. Do not synthesize a root Canvas.

Staleness is semantic. A candidate is stale when its owner differs, any record
was deleted, its Worktree is inactive or missing, or its Canvas anchor no longer
matches the Worktree. Cache age alone neither grants nor revokes authority.

After successful explicit acting selection, Canvas installs the returned receipt,
writes the scoped URL, then records the receipt in a separate Canvas owned
bootstrap cache. Failed selection changes none of those three states.

Reload behavior follows directly:

* Reloading `/spaces/A/worktrees/B/canvases/C` verifies that URL tuple and
  reinstalls C, even when meta describes the process cwd or root Canvas.
* A stale scoped URL surfaces its failure. It cannot silently open another
  Canvas.
* An unscoped reload tries the persisted service receipt, then meta.

Non cwd selection follows the same path:

* Selecting Worktree B or its child Canvas C is explicit and therefore wins.
* Meta for cwd Worktree A cannot demote B or C.
* The selected tuple reaches launch unchanged. No later layer infers cwd or a
  root Canvas.

## Consumer migration

### Canvas route, CMDK, rehydration, and persistence

| Current consumer | After migration |
| --- | --- |
| `www/packages/canvas/src/route.ts:isUsableIdentity` | Delete. Contract decoding and `resolveActingContext` replace local completeness checks. |
| `www/packages/canvas/src/route.ts:resolveCanvasLaunchIdentity` | Delete. Precedence belongs to `SpaceContextService.resolveActingContext`. |
| `www/packages/canvas/src/route.ts:parseCanvasLaunchContext` | Stay as URL syntax parsing. Return one raw candidate or a route error. |
| `www/packages/canvas/src/route.ts:canvasSwitchUrl` | Stay as URL serialization from `ActingContextView`. |
| `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:SessionCanvasRoute` | Collect explicit, URL, persisted, and meta candidates, call one resolve endpoint, then install one receipt. |
| `www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts:activateSpace` | Enter Space navigation and clear `actingContext` atomically. It cannot create a partial context. |
| `www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts:activateWorktree` | Invoke the shared selection command for the requested Worktree and Canvas. Keep no URL first write. |
| `www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts:initializeVerifiedCanvas` | Delete. The server response is the verification result. |
| `www/packages/canvas/src/model/canvasStoreLifecycle.ts:initializeCanvas` | Accept `ActingContextView | null` atomically. Never preserve a pair while nulling Canvas. |
| `www/packages/canvas/src/model/canvasStoreLifecycle.ts:selectSpace` | Replace with installation of a resolved receipt. |
| `www/packages/canvas/src/model/canvasState.ts:CanvasStoreModel` | Replace separate identity fields with `actingContext: ActingContextView | null`; keep Space only navigation separate. |
| `www/packages/canvas/src/model/paneRecords.ts:CanvasModel` | Hold the receipt or a reference to it. Delete duplicate ID aliases. |
| `www/packages/canvas/src/model/paneRecords.ts:ViewerCanvasContext` | Expose one complete context to viewers. |
| `www/packages/canvas/src/model/paneRecords.ts:PaneContentRef` | Keep foreign Worktree references, sourced from contract types. |
| `www/packages/canvas/src/model/canvasActions.ts:createCanvasActions` | Pass complete receipts to lifecycle actions. |
| `www/packages/canvas/src/model/canvasActions.ts:createCapturedRunActions` | Pass one complete context to launch and adoption. |
| `www/packages/canvas/src/model/worktreeDefaults.ts:adoptDefaultWorktreePatch` | Stop deriving current identity. Adoption receives the resolved context. |
| `www/packages/canvas/src/infrastructure/persistence/canvasPersistOptions.ts:createCanvasPersistOptions` | Keep pane and layout persistence. Add no independent nullable identity fields. |
| `www/packages/canvas/src/model/canvasStore.persistence.ts:CANVAS_STORE_STORAGE_VERSION` | Keep unchanged if the separate receipt cache avoids a schema change. |
| `www/packages/canvas/src/infrastructure/persistence/canvasCacheStorage.ts:createCanvasCacheStorage` | Key from `actingContext.canvasId`. It remains a Canvas persistence adapter. |
| `www/packages/canvas/src/launcher/commandTypes.ts:LauncherCommand` | Carry one context candidate or receipt rather than three strings. |
| `www/packages/canvas/src/launcher/commandTypes.ts:ScopeRowInputs` | Read active IDs from the receipt and Space browse scope from launcher navigation. |
| `www/packages/canvas/src/launcher/workdirRows.ts:worktreeRowActions` | Send explicit selection as one whole candidate. |
| `www/packages/canvas/src/launcher/workdirRows.ts:buildSpaceRows` | Consume contract projections. |
| `www/packages/canvas/src/launcher/workdirRows.ts:buildWorktreeRows` | Consume contract projections and dispatch shared commands. |
| `www/packages/canvas/src/launcher/commandRows.ts:buildCanvasRows` | Send explicit Canvas selection as one whole candidate. |
| `www/packages/canvas/src/launcher/useSpaces.ts:useSpaces` | Call the Canvas Space API adapter and consume contract projections. |
| `www/packages/canvas/src/launcher/useCanvases.ts:useCanvases` | Call the Canvas Space API adapter and consume contract projections. |
| `www/packages/canvas/src/workbench/spaceCommandDispatcher.ts:dispatchSpaceMutation` | Call Space service routes through the Canvas adapter. |
| `www/packages/canvas/src/model/capturedRunStore.ts:EnsureRunOptions` | Replace optional identity fields with required `ActingContextView`. |
| `www/packages/canvas/src/model/capturedRunStore.ts:CapturedRunState.ensureRun` | Call the shared ControlPlane launch client with one complete context. |
| `www/packages/canvas/src/viewers/registry.tsx:registry` | Pass one context to `CapturedRunPane`. |
| `www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx:CapturedRunPane` | Stop assembling identity from store and pane fields. |
| `www/packages/canvas/src/infrastructure/runtime/useCapturedRunBinding.ts:UseCapturedRunBindingOptions` | Accept one context. |
| `www/packages/canvas/src/infrastructure/runtime/useCapturedRunBinding.ts:useCapturedRunBinding` | Launch and bind through the shared control plane client. |
| `www/packages/canvas/src/model/capturedRunAdoption.ts:candidateFromWire` | Compare complete contexts. Service launches can no longer omit Canvas. |
| `www/packages/canvas/src/model/capturedRunAdoption.ts:CapturedRunAdoptionReconciler` | Adopt by exact complete context. |
| `www/packages/canvas/src/workbench/CanvasWorkbench.tsx:CanvasWorkbench` | Build viewer input from the installed receipt. |
| `www/packages/core/src/transport.ts:Meta` | Return a bootstrap candidate or no candidate. It carries no precedence. |
| `www/packages/core/src/transport.ts:CreateCapturedRunOptions` | Move to the control plane contract and require complete context. |
| `www/packages/core/src/transport.ts:createCapturedRunView` | Remove from Canvas launch flow. The shared ControlPlane client owns launch. |
| `www/packages/core/src/transport.ts:RunView` | Consume a complete context projection. |
| `www/packages/core/src/transport.ts:RunFilters` | Use whole context filters where placement matters. |

### Control plane, Runtime, capture, Session, REST, and MCP

| Current consumer | After migration |
| --- | --- |
| `api/src/transport_matters/controlplane/models.py:ControlPlanePrincipal` | Carry required `ActingContext`, plus existing grant facts. |
| `api/src/transport_matters/controlplane/launch_service.py:ControlPlaneLauncher.launch` | Remain the sole launch authority for REST, MCP, Canvas, and evaluation. |
| `api/src/transport_matters/controlplane/launch_service.py:ControlPlaneLauncher._prepare` | Pass one frozen complete context. Remove pair checks and fallback. |
| `api/src/transport_matters/controlplane/run_models.py:GatewayCreateRunRequest` | Require complete context. |
| `api/src/transport_matters/controlplane/run_models.py:GatewayRunView` | Return complete context. |
| `api/src/transport_matters/api/v1/controlplane_gateway_runs.py:create_run` | Send the same complete context for every launch kind, including `service`. |
| `api/src/transport_matters/api/v1/controlplane_gateway_runs.py:list_runs` | Filter and project complete context consistently. |
| `packages/runtime/src/domain/runtimeRun.ts:RuntimeRunView` | Replace bare pair strings with a complete context contract value. |
| `packages/runtime/src/ports.ts:PrepareCaptureInput` | Require one complete context. |
| `packages/runtime/src/ports.ts:CapturedRunSpawnSpec` | Carry one complete context. |
| `packages/runtime/src/service/runManagerTypes.ts:CreateManagedRunInput` | Replace three optional fields with one required context for captured runs. |
| `packages/runtime/src/service/RunManager.ts:RunManager` | Preserve the frozen context unchanged through `register`. |
| `packages/runtime/src/server/runtimeRouter.ts:createRuntimeRouter` | Decode the complete control plane contract. |
| `packages/runtime/src/adapters/CaptureRpcClient.ts:CaptureRpcClient` | Serialize one complete context. |
| `packages/runtime/src/adapters/StubCaptureAdapter.ts:StubCaptureAdapter` | Mirror the same contract for tests. |
| `packages/runtime/src/service/runManagerSupport.ts:createRunFingerprint` | Fingerprint the complete context as one value. |
| `api/src/transport_matters/api/v1/capture_rpc_routes.py:PrepareCaptureRequest` | Replace three optional fields with one complete context DTO. |
| `api/src/transport_matters/api/v1/capture_rpc_routes.py:_resolved_domain_request` | Decode and verify the receipt through the Space compatibility port. Remove service pair mode. |
| `api/src/transport_matters/api/v1/launch_resolution.py:resolve_run_canvas` | Move verification to the Space service, then delete this owner. |
| `api/src/transport_matters/api/v1/launch_resolution.py:resolve_run_worktree` | Delete the incomplete launch mode. |
| `api/src/transport_matters/capture_rpc.py:_CaptureRunFacts` | Store complete context. |
| `api/src/transport_matters/capture_rpc.py:CaptureLeaseRegistry` | Preserve complete context through grant creation and lookup. |
| `api/src/transport_matters/capture_rpc.py:capture_spawn_spec_payload` | Serialize complete context. |
| `api/src/transport_matters/session/affinity.py:SessionAffinityStamp` | Become the Session projection and codec for `ActingContext`. |
| `api/src/transport_matters/session/affinity.py:validate_affinity_group` | Remain only at legacy decode boundaries until the old shape is gone. |
| `api/src/transport_matters/api/v1/meta.py:MetaResponse` | Expose an optional bootstrap candidate or receipt as one object. |
| `api/src/transport_matters/api/v1/meta.py:get_meta` | Read launch facts only. Cwd inference cannot establish authority. |
| `api/src/transport_matters/api/v1/space_mcp.py:SpaceMcpAdapter` | Call `@tm/space` through the Gateway service adapter. Keep MCP free of domain logic. |
| `api/src/transport_matters/api/v1/space_contracts.py:SpaceSummary` | Move its wire shape to `@tm/contract/space`; keep a temporary Python codec only. |
| `api/src/transport_matters/api/v1/space_routes.py:router` | Become a thin compatibility mount to `spaceRouter`, then retire. |
| `api/src/transport_matters/space/service.py:SpaceCrudService` | Move use cases into `@tm/space`, preserving one owner. |
| `api/src/transport_matters/space/store.py:SpaceStore` | Move behind `PostgresSpaceRepository`, preserving the schema during cutover. |
| `api/src/transport_matters/space/store_space_ops.py:SpaceStoreSpaceOps` | Move Space persistence methods into the repository adapter. |
| `api/src/transport_matters/space/store_worktree_ops.py:SpaceStoreWorktreeOps` | Move Worktree persistence methods into the repository adapter. |
| `api/src/transport_matters/space/store_canvas_ops.py:SpaceStoreCanvasOps` | Move Canvas persistence methods into the repository adapter. |
| `api/src/transport_matters/space/projection.py:SpaceSnapshot` | Move projection logic to `@tm/space`. |
| `api/src/transport_matters/space/authz.py:require_space_record` | Move owner checks into the context service and repository queries. |
| `api/src/transport_matters/space/canvas_commands.py:create_canvas` | Move Canvas creation into `SpaceCrudService`. |
| `api/src/transport_matters/space/canvas_commands.py:update_canvas` | Move Canvas updates into `SpaceCrudService`. |
| `api/src/transport_matters/cli/space_bootstrap.py:bootstrap_cli_space` | Split explicit create from read only resolution. Launch never calls create. |

The remaining direct consumers keep their own responsibility and consume one
receipt or its deliberate projection:

| Current consumer | After migration |
| --- | --- |
| `www/packages/canvas/src/launcher/CommandCenter.tsx:CommandCenter` | Read active context from the receipt and Space browse scope from navigation. |
| `www/packages/canvas/src/launcher/navigation.ts:NavFrame` | Hold an opaque navigation reference. Command execution resolves the whole candidate. |
| `www/packages/canvas/src/launcher/templateRows.ts:agentSpawnRows` | Build launch commands with a complete context. |
| `www/packages/canvas/src/model/canvasStore.ts:useCanvasStore` | Install one receipt through lifecycle actions. |
| `www/packages/canvas/src/model/spawn.ts:createCapturedRunRef` | Carry a context reference rather than a free Worktree string. |
| `www/packages/canvas/src/workbench/CanvasPaneLayer.tsx:CanvasPaneLayer` | Build viewer context from the receipt. |
| `www/packages/canvas/src/infrastructure/persistence/canvasPanePersistence.ts:PersistedCanvasState` | Keep pane mechanics. Decode Worktree foreign keys through contract readers. |
| `api/src/transport_matters/api/v1/ids.py:parse_uuid_id` | Remain a temporary Python contract reader, then retire with the bridge. |
| `api/src/transport_matters/api/v1/run_proxy.py:RunRouteProxy` | Proxy complete run context and deliberate Space or Worktree list filters. |
| `api/src/transport_matters/api/v1/session_models.py:SessionView` | Project the Session owned affinity receipt. |
| `api/src/transport_matters/api/v1/session_models.py:session_view_from_row` | Map stored affinity fields without creating authority. |
| `api/src/transport_matters/api/v1/session_routes.py:list_sessions` | Keep optional read filters as Session query criteria. |
| `api/src/transport_matters/captured_run_models.py:CapturedRunRequest` | Require one complete launch context. |
| `api/src/transport_matters/captured_run_models.py:CapturedRunSpawnSpec` | Return the same complete context. |
| `api/src/transport_matters/captured_run_models.py:CapturedRunLease` | Preserve the complete context for the lease lifetime. |
| `api/src/transport_matters/cli/start_cmd.py:run_start` | Pass a bootstrap or explicit receipt unchanged. |
| `api/src/transport_matters/controlplane/activity.py:ControlPlaneGatewayPort` | Accept and return contract context values while Activity remains a foreign reader. |
| `api/src/transport_matters/controlplane/activity.py:RunManagementPort` | Use deliberate Space or Worktree filters for management reads. |
| `api/src/transport_matters/index/adapters/base.py:SessionBinding` | Carry the Session projection of the receipt. |
| `api/src/transport_matters/index/adapters/base.py:RunContext` | Carry the Session projection of the receipt. |
| `api/src/transport_matters/run_lifecycle.py:build_run_lifecycle_event` | Project context into Activity lifecycle facts. |
| `api/src/transport_matters/addon_runtime.py:_emit_run_lifecycle_event` | Forward the bound context projection. |
| `api/src/transport_matters/addon_runtime.py:_start_session_capture` | Bind the complete Session affinity projection. |
| `api/src/transport_matters/session/models.py:SessionRow` | Persist the receipt projection as Session facts. |
| `api/src/transport_matters/session/models.py:SessionListRow` | Expose stored foreign context fields. |
| `api/src/transport_matters/session/models.py:RunLifecycleEventRow` | Keep Activity projection fields. |
| `api/src/transport_matters/session/ingest.py:build_session` | Ingest a complete affinity projection as one group. |
| `api/src/transport_matters/session/ingest.py:_binding_affinity` | Decode no partial group. |
| `api/src/transport_matters/session/dao_rows.py:session_params` | Write the complete group in one parameter map. |
| `api/src/transport_matters/session/async_dao.py:AsyncSessionDao` | Keep Session persistence and optional read filters. |
| `api/src/transport_matters/session/session_statements.py:UPSERT_SESSION_SQL` | Preserve all context columns as one write group. |
| `api/src/transport_matters/session/dao_statements.py:INSERT_RUN_LIFECYCLE_EVENT_SQL` | Preserve the deliberate Activity projection. |
| `api/src/transport_matters/shared_proxy/binding.py:ProxyRunBinding` | Carry the complete receipt. |
| `api/src/transport_matters/shared_proxy/binding.py:trusted_binding_affinity` | Return its Session projection. |
| `api/src/transport_matters/shared_proxy/addon.py:_runtime_binding_from_payload` | Decode the complete receipt. |
| `api/src/transport_matters/shared_proxy/models.py:SharedProxyBindingPayload` | Serialize the complete receipt. |
| `api/src/transport_matters/space/models.py:Space` | Move into the `@tm/space` aggregate. |
| `api/src/transport_matters/space/models.py:StoredWorktree` | Move into the `@tm/space` aggregate. |
| `api/src/transport_matters/space/models.py:ProjectedWorktree` | Move into Space projections. |
| `api/src/transport_matters/space/models.py:WorktreeRecord` | Move to domain plus contract projection. |
| `api/src/transport_matters/space/models.py:StoredCanvas` | Move into the `@tm/space` aggregate. |
| `api/src/transport_matters/space/models.py:Canvas` | Move into the `@tm/space` aggregate. |
| `api/src/transport_matters/space/models.py:CanvasRecord` | Move to domain plus contract projection. |
| `api/src/transport_matters/space/models.py:DirectorTree` | Move to Space projections. |
| `api/src/transport_matters/space/models.py:CrudCaller` | Move to Space authorization input. |
| `api/src/transport_matters/space/space_mutations.py:create_space` | Move to `SpaceCrudService`. |
| `api/src/transport_matters/space/space_mutations.py:rename_space` | Move to `SpaceCrudService`. |
| `api/src/transport_matters/space/worktree_mutations.py:create_workdir` | Move to `SpaceCrudService`. |
| `api/src/transport_matters/space/delete_mutations.py:delete_workdir` | Move to `SpaceCrudService`. |
| `api/src/transport_matters/space/delete_mutations.py:delete_space` | Move to `SpaceCrudService`. |
| `api/src/transport_matters/space/store_records.py:space_from_row` | Move into the Postgres adapter. |
| `api/src/transport_matters/space/store_records.py:worktree_from_row` | Move into the Postgres adapter. |
| `api/src/transport_matters/space/store_records.py:canvas_from_row` | Move into the Postgres adapter. |

Python capture, Session, shared proxy, and lifecycle code keep their own domains.
They consume the context receipt as a foreign value. Activity continues to own
capture history. Runtime continues to own process lifecycle. Launch continues
to own launch idempotency and normalized specifications.

CMDK and MCP then converge before capture:

```text
Canvas CMDK or MCP command
  ControlPlaneLauncher.launch
    frozen LaunchSpec with ActingContext
      Runtime
        capture prepare
          SessionAffinityStamp projection
```

There is one command surface. Canvas no longer launches through a direct
`POST /v1/runs` helper with locally assembled identity.

## Ordered shippable slices

### Slice 1: contract and declarations

Add `@tm/contract/space`. Add branded IDs to the new `@tm/space` domain. Move
wire DTOs from browser Core. Delete all three Core aliases and the duplicate
Canvas alias. Update public imports. Product behavior remains unchanged through
the existing endpoints.

Gates:

* contract round trip fixtures in TypeScript and Python
* package type checks
* `www/packages/shell/src/testSupport/importGraphBoundary.test.ts`
* dependency lint proving browser packages import only contract and common
* exact search proving one declaration per domain ID

### Slice 2: read only Space context service

Create `SpaceContextService.resolveActingContext`, the read only repository port,
Postgres adapter, typed failures, shared fixture table, and Gateway route. Bind
existing `resolve_run_canvas` checks, then make the old function delegate.
Existing launch and Canvas flows continue through compatibility adapters.

Gates:

* table tests for explicit, URL, persisted, and meta precedence
* owner, deletion, lifecycle, and Canvas anchor rejection tests
* partial candidate rejection at REST and MCP decoders
* a transaction probe proving row counts and Git worktrees do not change
* route injection tests against existing Space records

### Slice 3: atomic launch context cutover

Change `ControlPlanePrincipal`, `ControlPlaneLauncher`, Gateway request and view,
Runtime spawn input, capture prepare, lease facts, run facts, and
`SessionAffinityStamp` in one slice. Every captured launch carries Canvas.
`launchKind="service"` changes placement behavior only.

This slice is unsplittable. Any intermediate pair shaped boundary can discard
Canvas and recreate the dual authority. Land the contract producer and every
consumer in the same commit or merge queue unit.

Gates:

* focused control plane launch and idempotency suites
* Gateway request and run view contract tests
* Runtime manager and capture adapter tests
* capture RPC and Session affinity codec tests
* MCP service launch proving child Canvas preservation
* rejection tests proving no pair shaped request remains valid

### Slice 4: Canvas selection, rehydration, and CMDK convergence

Replace the nullable Canvas identity fields with one receipt. Route, persisted
receipt, meta bootstrap, and explicit commands call the shared resolver. Update
the URL and persistence only after success. Route CMDK launch through
`ControlPlaneLauncher`. Delete local precedence and direct run creation.

Gates:

* reload a full scoped URL with persisted panes and prove it remains verified
* select non cwd Worktree B while meta describes A and prove B survives
* reload a child Canvas and prove no root Canvas substitution
* stale scoped URL visible failure
* stale persisted receipt discard followed by valid meta bootstrap
* failed explicit selection leaves URL, store, and cache unchanged
* CMDK and MCP launches produce the same complete context
* a real browser rehydration probe covering service and CMDK panes

### Slice 5: Space inventory and command ownership

Move Space, Worktree, and Canvas CRUD, authorization, projection, REST, and MCP
use cases into `@tm/space`. Preserve the existing schema through the adapter.
Remove the Python business owner and the browser Core transport. The product
continues to expose the same Canvas and MCP command capabilities.

Gates:

* REST and MCP parity fixtures for every Space command
* owner scope and run aware deletion tests
* Postgres migration and transaction smoke tests
* Git worktree observation tests
* Canvas inventory and command focused suites
* no seeding proof for every read and launch endpoint

### Slice 6: compatibility removal and boundary ratchet

Delete old ID codecs, delegating resolvers, nullable tuple types, Core reexports,
and pair shaped launch fields. Add `@tm/space` to the product package import
ratchet. Update architecture documentation and dependency diagrams.

Gates:

* import graph boundary suite
* dependency lint
* exact searches proving old symbols and declarations are absent
* focused Canvas, control plane, Runtime, capture, Session, REST, and MCP suites
* one end to end reload, selection, launch, stop, and reattach scenario

No gates were run during this design pass.

## Blast radius and risk

The largest risk is the Slice 3 launch cutover. Identity crosses TypeScript
control plane and Runtime, Python capture and Session, REST, MCP, and Canvas.
A partial cutover silently loses Canvas or creates a second inference point.
The complete receipt, frozen launch specification, and atomic merge unit are
the controls.

The next risk is persistence. At current HEAD,
`www/packages/canvas/src/infrastructure/persistence/canvasPersistOptions.ts:createCanvasPersistOptions`
returns `emptyPersistedCanvasState` from `migrate`. Raising
`CANVAS_STORE_STORAGE_VERSION` therefore resets every stored Canvas pane and
layout at that release. Backward compatibility is waived, so a deliberate reset
is allowed, but it must be named in the release plan. The preferred Slice 4
shape uses a separate receipt cache and keeps the Canvas store version unchanged.

Other material risks:

* Moving persistence ownership across Node and Python can create dual writers.
  Slice 5 gives the schema one repository writer before deleting Python use
  cases.
* Branding only part of the graph creates repeated casts. Slice 1 changes all
  declarations and public imports together.
* Meta can remain cached indefinitely. Semantic revalidation makes cache age
  irrelevant and prevents cwd from overriding an explicit scope.
* Canvas cache lookup needs Canvas ID before opening the per Canvas state. The
  separate receipt cache breaks that bootstrap cycle.
* Run adoption currently treats service launches as incomplete. Slice 3 makes
  every captured run complete before Slice 4 tightens adoption.

## What not to do

* Do not restore `_resolve_launch_worktree`,
  `SpaceCrudService.resolve_session_cwd`, `resolve_cwd(create=True)`, or any
  `_materialize_missing_worktree` launch path.
* Do not seed Space inventory while resolving, reading, rehydrating, or launching.
* Do not let meta win over an explicit or scoped choice.
* Do not persist three nullable fields plus a verification boolean.
* Do not merge fields from URL, meta, persistence, or explicit selection.
* Do not infer a root Canvas when a child Canvas is absent or stale.
* Do not preserve the service pair and infer Canvas later.
* Do not import `@tm/space` from Canvas or another browser package.
* Do not place Space IDs in `@tm/common`.
* Do not leave a permanent `www/packages/core` compatibility reexport.
* Do not let Canvas call a separate run creation path.
* Do not add UI only identity precedence or validation.
* Do not bump Canvas persistence version without naming the pane and layout reset.
* Do not duplicate `SpaceCrudService`, `resolve_run_canvas`, or
  `SessionAffinityStamp`. Extract their valid rules, redirect every caller, and
  delete the old owner in the scheduled slice.

## Baseline

The reviewed baseline is branch `ml/s6-identity` at
`963fd8f89e3c4391d85adc163adc2430d371fe1c`. The only working tree difference
before this report was the permitted one line `LESSONS.md` addition. The report
does not rely on either rejected implementation commit.

## Cross-check

This section supersedes the original brand location and six-slice order.

### Risks and splittability

Both risks are real. Fable correctly identifies the client owner cutover across
`SessionCanvasRoute.tsx:SessionCanvasRoute`,
`CanvasCommandDispatcher.ts:activateWorktree`,
`canvasStoreLifecycle.ts:initializeCanvas`, and
`canvasCacheStorage.ts:createCanvasCacheStorage`. I included this cluster in
Slice 4 but underweighted it in the headline.

The launch cutover remains separate. Fable leaves
`controlplane/models.py:ControlPlanePrincipal`,
`controlplane/run_models.py:GatewayCreateRunRequest`,
`controlplane_gateway_runs.py:create_run`, and
`runtime/ports.ts:CapturedRunSpawnSpec` pair shaped. That preserves a second
completeness rule for the director. There are two cutover domains.

Neither requires a wide atomic slice. For client state, keep the legacy writer
authoritative while the new resolver runs in shadow. Add one derived receipt,
migrate every reader, then flip one owner adapter so legacy fields become
read-only projections. Delete them afterward. For launch, make every consumer
accept a complete context beside legacy fields through one compatibility
decoder, assert equality when both exist, then emit both. One small flip makes
context required; contraction removes legacy fields.

Pre-landing evidence is the shared fixture matrix, shadow decision comparisons,
an injected client divergence detector, a live browser A/B and reload probe, and
field-drop mutations at every launch hop.

### Package and precedence

Use `@tm/space` at `packages/space` plus `@tm/contract/space`.
`packages/contract/package.json:exports` already has `activity` and `runtime`
subpaths. Fable's `www/packages/spaces` context conflicts with
`docs/ARCHITECTURE.md:Product package placement` and
`packages/AGENTS.md:Context packages`. Browser packages are clients and may
import contract subpaths, never product contexts. MCP calls
`SpaceContextService.resolveActingContext` through Gateway; Canvas calls its
REST surface.

Fable found the better brand placement. Put shared branded IDs and readers in
`@tm/contract/space`, following `@tm/contract/activity`, and let `@tm/space`
import them. This supersedes the earlier domain-only brand location.

Fable's precedence is sticky explicit selection, then URL, persisted locator,
and meta last, with browser inventory promoting claims and meta allowed to fill
nonconflicting gaps. It satisfies both live behaviours if inventory includes the
child Canvas. Keep the same ranks, but require whole tuples verified by
`SpaceContextService.resolveActingContext`. Meta never fills another source.
This preserves reload and non-cwd selection and gives Canvas and MCP one rule.

### Gaps

Fable found `RunManager.ts:DEFAULT_SPACE_ID` and
`RunManager.ts:DEFAULT_WORKTREE_ID`; remove both. I found the retained director
pair and browser plane violation. Both reports missed a monotonic resolution
generation, needed so late boot cannot overwrite newer explicit selection, and
one consistent repository snapshot for Space, Worktree, and Canvas verification.

### Endorsed order

1. Contract: brands and full context DTO. Gate purity, import graph, and language fixtures.
2. Context: read-only resolver and Gateway surface. Gate precedence and zero mutation.
3. Shadow: compare new and legacy decisions. Gate the three known mismatch fixtures.
4. Client expand: add a derived receipt and migrate readers. Gate injected divergence.
5. Client flip: make the receipt authoritative. Gate live reload, A/B, child Canvas, and cache key.
6. Client contract: add locator and remove old writers. Gate old snapshot and unchanged store version.
7. Launch expand: accept and emit both shapes. Gate equality and field-drop mutations.
8. Launch flip: require context and remove pair authority and sentinels. Gate both clients end to end.
9. Ownership cleanup: move CRUD and delete old owners. Gate parity, migration smoke, and zero old symbols.

## Reconciled plan

1. **Contract.** Goal: add `@tm/contract/space` brands, `ownerId`, complete receipt, candidates, failures, and shared parity fixtures. Gate: contract purity, import graph, TypeScript and Python fixture round trips, and one TS declaration search. Works alone: yes, existing fields remain.
2. **Verification.** Goal: add `@tm/space` at `packages/space`, with read-only `SpaceContextService.verifyActingContext`, a one-snapshot repository transaction, REST and MCP adapters, and no seeding surface. Gate: fixture matrix, owner and membership failures, repeatable-read consistency, unchanged row counts and Git worktrees. Works alone: yes, additive and unused.
3. **Browser client.** Goal: retain Fable's `www/packages/spaces` only as a browser client package for pure ranking `explicit > URL > locator > meta`, URL codecs, inventory adapters, and mechanical Core moves; delete verified-dead fetchers. Meta remains `staleTime: Infinity` and is unread after acting. Gate: full frontend suite, dead-surface search, package boundary tests. Works alone: yes, Canvas still uses legacy ownership.
4. **Shadow and read expansion.** Goal: run the browser reducer in shadow, add a derived `ActingContextReceipt`, split `navigationSpaceId`, add a monotonic resolution generation, and migrate every reader while legacy writers remain sole authority. Gate: parity fixtures, expected mismatch ledger, injected late-response and field-divergence detectors, complete reader enumeration. Works alone: yes, no observable writer changes.
5. **Browser owner flip.** Goal: make the local reducer authoritative, accept explicit server-verified inventory rows without a switch round trip, verify URL and locator through `@tm/space`, project legacy fields read-only, and make failed selection atomic across URL, receipt, cache, and locator. Gate: real-browser reload, cwd A to non-cwd B, child Canvas, stale meta, late boot response, and failed-selection probes. Works alone: yes, projections support remaining legacy readers.
6. **Browser contraction and locator.** Goal: remove legacy writers and add a window-scoped `sessionStorage` locator so two windows cannot overwrite each other's fallback. Gate: two-window A/B reload, dangling locator, old Canvas snapshot, and zero legacy-writer searches. Works alone: yes. Persisted shape: one new locator record only; `CANVAS_STORE_STORAGE_VERSION` stays unchanged, so no Canvas resets.
7. **Launch expansion.** Goal: accept and dual-emit the complete receipt beside legacy fields through principal, `ControlPlaneLauncher`, Gateway, Runtime, capture, proxy, Session, lifecycle, and every checked-in Python downstream-affinity consumer; remove Runtime stub sentinels. Gate: equality assertions, affinity-consumer allowlist, field-drop mutations at every hop, CMDK and MCP parity. Works alone: yes, all consumers accept both shapes.
8. **Launch flip and contraction.** Goal: require the receipt, make both clients enter the same `ControlPlaneLauncher` path, reject pair-shaped authority, then delete legacy launch fields and compatibility decoding. Gate: legacy rejection, child-Canvas MCP launch, CMDK launch, Session persistence, stop and reattach end to end. Works alone: yes, Slice 7 has already expanded every consumer.
9. **Ownership cleanup.** Goal: move Space CRUD and projections behind `@tm/space`, delete Python business owners and Core reexports, and ratchet package imports. Gate: REST and MCP parity, migration smoke, no-seeding proof, import graph, and zero old symbols. Works alone: yes. Unsplittable: none. Reconciliation dropped my original wide client and launch slices because shadow, dual-shape expansion, and small owner flips preserve one writer at every stage.
