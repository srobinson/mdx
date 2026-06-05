# Rehydrate identity regression scout

## Scope and verdict

Reviewed branch `ml/s4-adoption` at `4e0f0e5dab326295baa5b8e206845ff8bdd4a623`, using the live evidence in `~/.mdx/projects/tm-rehydrate-identity-evidence.md` as ground truth. The shared worktree was pristine immediately before this report. No tests, builds, or gates ran under the read only contract.

Confidence: high.

Root cause: a fresh renderer has no durable Canvas identity with which to address its Canvas scoped persistence, while activity adoption reconstructs service launched MCP panes only.

## 1. Launch identity producers, divergence, and authority

### CMDK

The server inventory projection produces the selectable identity at `api/src/transport_matters/space/models.py :: WorktreeRecord.from_worktree`. `www/packages/canvas/src/launcher/workdirRows.ts :: worktreeRowActions` converts `spaceId`, `worktreeId`, and `rootCanvasId` into the Worktree selection command. `www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts :: activateWorktree` and `initializeVerifiedCanvas` write that tuple to the route and Canvas store.

At spawn time, `www/packages/canvas/src/viewers/registry.tsx :: registry`, in the `captured-run` registration, assembles the request identity from three owners:

- `spaceId` from the active Canvas store context
- `worktreeId` from the pane content reference
- `canvasId` from the active Canvas store context

`www/packages/core/src/transport.ts :: createCapturedRunView` serializes the full tuple to Gateway `POST /v1/runs`. It omits `launchKind`, whose request default is Canvas.

### MCP

There is no MCP Canvas triple producer at this head. `api/src/transport_matters/capture_rpc.py :: CaptureLeaseRegistry.resolve_control_plane_grant` recovers an authenticated Space and Worktree pair from live capture facts. `api/src/transport_matters/controlplane/launch_service.py :: ControlPlaneLauncher._prepare` freezes that pair. `api/src/transport_matters/api/v1/controlplane_gateway_runs.py :: create_run` sends the pair with `launchKind: "service"` and no `canvasId`.

The precise divergence is the launch kind and affinity contract before the shared Gateway run command:

- Canvas launch: full Space, Worktree, and Canvas tuple
- Service launch: Space and Worktree pair

Both converge on Gateway `POST /v1/runs`, then on `api/src/transport_matters/api/v1/capture_rpc_routes.py :: _resolved_domain_request`. That Python seam is the current launch authority. It rejects an incomplete Canvas tuple and delegates to `api/src/transport_matters/api/v1/launch_resolution.py :: resolve_run_canvas`. Service launches delegate to `resolve_run_worktree`. The renderer helper `www/packages/canvas/src/route.ts :: resolveCanvasLaunchIdentity` performs local candidate matching; it does not replace server authorization.

MCP success therefore proves that the server can validate the principal's Space and Worktree pair. It provides no evidence that the server reconstructed a missing Canvas UUID.

## 2. Worktree transition versus rehydrate

`www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts :: activateWorktree` runs the recovery sequence observed after switching away and back:

1. `worktreeSwitchUrl` writes the Space, Worktree, and root Canvas IDs.
2. `initializeVerifiedCanvas` resolves and installs the verified tuple.
3. `www/packages/canvas/src/model/canvasStoreLifecycle.ts :: initializeCanvas` selects the Canvas scoped cache and calls `persist.rehydrate()`.

Fresh renderer startup lacks this sequence. `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx :: SessionCanvasRoute` can use route identity, meta identity, or in memory store identity. All three are empty in the observed reload. `initializeCanvas` receives no durable Canvas ID, records the unverified state, and returns before persistence rehydrate. Its inventory fallback, `needsWorktreeInventory`, also requires Space and Worktree IDs that are already missing.

No already current Worktree early return exists at this head. `CanvasCommandDispatcher.ts :: activateWorktree` is unconditional, and `www/packages/canvas/src/launcher/workdirRows.ts :: worktreeRowActions` leaves a Worktree badged `Current` selectable. A primary click or Enter should dispatch Worktree activation and rehydrate even when the selected Canvas is unchanged.

The explicit current selection guard is `CanvasCommandDispatcher.ts :: activateSpace`. Commit `9c9b06f8` added its early return to avoid clearing a narrower verified tuple when the current Space is reselected. Selecting the current Space therefore performs no Worktree activation. The Worktree row's `advance` action also enters Agents without selecting the Worktree. Either path can look like a reselect while bypassing rehydrate. The observed no effect remains authoritative, but source evidence does not support a current Worktree guard as its cause.

## 3. Three CMDK panes fail while two MCP panes succeed

The persisted pane references are inside a Canvas scoped blob. `www/packages/canvas/src/infrastructure/persistence/canvasCacheStorage.ts :: createCanvasCacheStorage` returns no persisted item until a durable Canvas ID is known. The references remain intact yet unreachable after the identityless reload.

MCP panes have an independent reconstruction path. `www/packages/canvas/src/model/capturedRunAdoption.ts :: candidateFromWire` accepts only activity records with `launch_kind === "service"`. `CapturedRunAdoptionReconciler` looks up those service runs and calls the adoption action, which creates visible panes with their returned Worktree identity.

CMDK launches use the default `launch_kind === "canvas"`. `candidateFromWire` rejects them. Startup reconciliation can prune unavailable remembered runs, but it does not recreate a missing Canvas pane from a global run record.

The launch kind discriminator explains the exact split:

- Two MCP service panes are rebuilt from activity.
- Three CMDK Canvas panes remain only in the inaccessible Canvas cache.

Switching away and back supplies the cache key and restores all panes and layout, confirming that persistence data survived.

## 4. Commit `df052e65` and removed meta resolution

Verdict: causal contributor.

`api/src/transport_matters/api/v1/meta.py :: get_meta` previously called `_resolve_launch_worktree`, introduced by `0c6b0e58` and extended with Canvas identity by `6453364a`. Commit `df052e65` removed that helper and replaced cwd resolution with `affinity_from_launch_fields(settings.launch_fields)`. The desktop renderer has no explicit launch fields, so meta now returns null Space, Worktree, and Canvas IDs. This removed the only reload time source that could select the existing Canvas cache.

Restoring the removed implementation is unsafe. Its `SpaceCrudService.resolve_session_cwd` path used `resolve_cwd(create=True)` and could materialize missing inventory on a read. It also predates current N:1 path ownership, where one canonical path may match Worktrees in multiple Spaces.

The commit removed a required capability without a read only replacement. The deeper defect is the unresolved bootstrap cycle: Canvas identity is required to read Canvas persistence, while the fresh renderer stores no independent identity locator.

## 5. Persistence of Space and Canvas identity

The zero string observation is confirmed for serialized state properties.

`www/packages/canvas/src/infrastructure/persistence/canvasPersistOptions.ts :: partializeCanvasState` persists pane references, pane geometry, ordering, dock state, strategy settings, fit state, and expanded pane state. `www/packages/canvas/src/model/canvasStore.persistence.ts :: createCanvasStorePersistOptions` adds pane counters. Neither persists `spaceId`, `defaultWorktreeId`, `canvasId`, or `launch`.

`worktreeId` can appear inside individual captured run or terminal content references. That local field cannot recover the Space and Canvas parts of the launch tuple.

`www/packages/canvas/src/infrastructure/persistence/canvasCacheStorage.ts :: canvasCacheKey` embeds the Canvas UUID in the storage key suffix. The UUID is absent as a JSON property, and the storage adapter requires the UUID before it can calculate and read that key. `spaceId` has no equivalent persisted locator.

`canvasPersistOptions.ts :: createCanvasPersistOptions` is the symbol deciding the persisted state shape through its `partialize` callback. Its migration callback returns an empty persisted Canvas state on a storage version mismatch. A version bump would therefore discard saved panes and layout.

## Reuse map

### Resolve existing identity from cwd

- Existing read owner: `api/src/transport_matters/space/service.py :: SpaceCrudService.list_worktrees_by_path`
- Existing canonicalization owner: `api/src/transport_matters/space/identity.py :: canonical_path`
- Existing explicit Worktree validation: `SpaceCrudService.resolve_launch_worktree`
- Existing root Canvas read: `SpaceCrudService.get_canvas`
- Complete side effect free cwd to triple owner: none found

`api/src/transport_matters/cli/space_bootstrap.py :: bootstrap_cli_space` contains a reusable existing match pattern, but the complete function creates a Space and Workdir when no match exists. It is disqualified by the no seeding constraint.

Searches covered cwd resolution, canonical path lookup, Worktree lookup by path, root Canvas lookup, and prior session cwd resolution.

### Verify the triple

- Server authority: `api/src/transport_matters/api/v1/launch_resolution.py :: resolve_run_canvas`
- Client candidate matcher: `www/packages/canvas/src/route.ts :: resolveCanvasLaunchIdentity`

`resolve_run_canvas` already resolves the Worktree, reads the Canvas, checks ownership and lifecycle, verifies the Canvas anchor matches the Worktree, and creates the affinity stamp.

### Hydrate a Worktree

- Transition owner: `www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts :: activateWorktree`
- Verified store activation: `CanvasCommandDispatcher.ts :: initializeVerifiedCanvas`
- Cache selection and rehydrate: `www/packages/canvas/src/model/canvasStoreLifecycle.ts :: initializeCanvas`
- Dedicated `hydrateWorktree`, `rehydrateWorktree`, or `resolveIdentityFromCwd` owner: none found

### Invalidate Space inventory

- Query key and paged fetch: `www/packages/canvas/src/launcher/useSpaces.ts :: SPACES_QUERY_KEY` and `fetchSpaceInventory`
- Mutation refresh owner: `www/packages/canvas/src/workbench/spaceCommandDispatcher.ts :: refreshSpaces`

No second inventory invalidation owner was found.

## Minimal fix direction

Add one read only application seam for resolving an existing launch identity:

1. Canonicalize cwd.
2. Query `SpaceCrudService.list_worktrees_by_path` for the owner.
3. Return unresolved for zero matches.
4. Fail closed on multiple matching Spaces unless the caller supplies an explicit selection.
5. Resolve the selected Worktree and root Canvas through existing service reads.
6. Verify the resulting tuple through the same rules owned by `resolve_run_canvas`.

Expose that seam through one thin desktop read adapter. During initial `SessionCanvasRoute` startup, use it only when route, meta, and store lack a usable tuple. Extract the body of `CanvasCommandDispatcher.ts :: activateWorktree` into one exported activation primitive shared by CMDK selection and reload recovery so route update, identity installation, cache selection, and rehydrate remain one operation.

Keep launch execution on the existing single command surface: Gateway `POST /v1/runs`, converging at `capture_rpc_routes.py :: _resolved_domain_request`. CMDK and MCP should remain thin adapters to that seam, with their current Canvas and service affinity contracts explicit. Do not add a renderer launch endpoint, create inventory during reads, seed an empty store, or call `resolve_cwd(create=True)`.

Persisting identity inside the existing Canvas blob cannot solve bootstrap because the Canvas UUID is required to read that blob. A separate bootstrap locator would require an explicit migration and data retention design. Avoid a storage version bump for this repair because the current migration policy empties saved Canvas state.

Required regression coverage for the implementing change should begin with a real fresh renderer state: unscoped URL, null desktop meta affinity, existing inventory, and an existing Canvas cache. It should prove identity discovery, full cache rehydrate, CMDK launch, MCP launch, unchanged layout, ambiguity handling, and zero create on read operations.

## Cross-check

### Conflicts

1. The Fable report's Q5 headline says `canvasId` is not persisted anywhere. `www/packages/canvas/src/infrastructure/persistence/canvasCacheStorage.ts :: canvasCacheKey` persists the UUID in the localStorage key. The JSON payload omits the `canvasId` property, and `spaceId` has no persisted locator. The report body makes this distinction correctly, so the conflict is limited to the headline.
2. `api/src/transport_matters/controlplane/launch_service.py :: ControlPlaneLaunchService` does not exist at this head. The owner is `ControlPlaneLauncher`, specifically `_prepare`.

### Gaps

The Fable report identifies an exact producer gap that my first pass did not name: `api/src/transport_matters/cli/desktop_cmd.py :: _DESKTOP_BACKEND_STALE_ENV_KEYS` deliberately removes `LAUNCH_FIELDS`, while `api/src/transport_matters/cli/start_cmd.py` and `codex_cmd.py` use `bootstrap_cli_space_or_exit` and stamp affinity.

Both reports missed a latent tuple validation defect. `www/packages/canvas/src/route.ts :: isUsableIdentity` documents a complete tuple but requires only `spaceId` and a durable `canvasId`. A source with a null `worktreeId` can therefore mark a Canvas locally verified and later reach the server with incomplete Canvas affinity. The implementation should require all three fields before using any identity source for activation.

### Endorsed fix

Add one read only existing identity query under `api/src/transport_matters/space/service.py :: SpaceCrudService`, composed from `list_worktrees_by_path`, `resolve_launch_worktree`, and `get_canvas`, with null on zero matches and an ambiguity result on multiple matches. Expose it through `api/src/transport_matters/api/v1/meta.py :: get_meta`, then extract `www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts :: activateWorktree` into one activation primitive shared by CMDK selection and initial `SessionCanvasRoute` recovery, while hardening `route.ts :: isUsableIdentity` to require the full tuple.

The resolver remains a query with zero create operations. CMDK and MCP launch adapters remain thin clients of the single Gateway `POST /v1/runs` command and its authority seam, `api/src/transport_matters/api/v1/capture_rpc_routes.py :: _resolved_domain_request`.
