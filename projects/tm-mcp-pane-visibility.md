# MCP launch and pane visibility archaeology

Baseline: `ml/s3-cmdk` at `699fb5786091ae5da1c86c688baa7ec714662084`.

## Finding

There is no commit that split CMDK and MCP away from the shared captured run launch entrypoint. The invariant still holds at the capture seam. Both paths reach `api/src/transport_matters/captured_run.py`, `prepare_captured_run`, through the same runtime create route and capture registry.

The browser sequencing differs. CMDK creates a captured run pane before posting the run. MCP posts the run first, then the existing activity adoption path must create the captured run pane. No history commit changed MCP from the CMDK browser command because MCP never invoked that browser command. The visibility regression is a failure to complete the documented activity adoption path.

At the pinned head, the lifecycle event reaches the backend. The browser loses it at the workspace subscription boundary. `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx`, `SessionCanvasRoute`, derives `activityWorkspaceId` from a resolved launch session or `meta.workspaceId`. A desktop Canvas normally has no resolved launch session, so it uses `meta.workspaceId`. `api/src/transport_matters/api/v1/meta.py`, `get_meta`, derives that value from the API process launch cwd, which remains fixed for the process lifetime.

Worktree selection changes the Canvas store and URL in place. It does not change backend meta. When the active Worktree workspace differs from the API launch workspace, the Activity client remains subscribed to the old workspace. `SessionCanvasRoute.onActivityFrames` therefore never receives the service run lifecycle row. The adoption predicate, run lookup, PaneRecord creation, and layout insertion are never reached.

## 1. Shared entrypoint

The authoritative shared symbol is `api/src/transport_matters/captured_run.py`, `prepare_captured_run`.

Both launch paths converge before it:

1. `packages/runtime/src/server/runtimeRouter.ts`, `registerRunRoutes`, accepts `POST /v1/runs`.
2. `packages/runtime/src/service/RunManager.ts`, `RunManager.createWithDisposition`, calls `RunManager.createNew`.
3. `RunManager.createNew` calls `packages/runtime/src/adapters/CaptureRpcClient.ts`, `CaptureRpcClient.prepareCapture`.
4. `api/src/transport_matters/api/v1/capture_rpc_routes.py`, `prepare_capture`, calls `CaptureLeaseRegistry.prepare_capture`.
5. `api/src/transport_matters/capture_rpc.py`, `CaptureLeaseRegistry._prepare_with_dependencies`, calls `prepare_captured_run`.

`CONTROLPLANE.md` already described MCP `launch` as using “the same `prepare_captured_run()` seam the UI uses” before MCP launch implementation landed.

## 2. Commit archaeology

No single culprit commit exists.

The shared seam originated in:

- SHA: `78cc7606e29aa6c52cca994369b5b81a720fa734`
- Date: `2026-06-09T07:15:36+07:00`
- Subject: `feat: extract captured run seam (#61)`
- Change: created `captured_run.py` and `prepare_captured_run` as reusable captured run preparation.

MCP launch first appeared in:

- SHA: `4b2d472833f9beebc511c651dcf9e953c51dfaec`
- Date: `2026-07-12T16:24:36+07:00`
- Subject: `feat(controlplane): S6a launch + manage verbs (backend) (#281)`
- Change: added `_McpControlPlaneAdapter.launch`, `ControlPlaneService.launch`, `ControlPlaneLauncher`, gateway `POST /v1/runs`, service launch identity, and `RunManager.createWithDisposition`.
- Result: MCP entered the existing runtime create route and still reached `prepare_captured_run`. It did not introduce a bypass around captured run preparation.

Canvas hydration for those already created service runs followed in:

- SHA: `e05373b6a4f5a101f1f4da95d499682e6bc8ee11`
- Date: `2026-07-12T18:00:59+07:00`
- Subject: `feat(controlplane): S6b canvas adoption reconciler (#283)`
- Change: added `CapturedRunAdoptionReconciler`, `CapturedRunState.adoptRun`, `CanvasStoreActions.adoptCapturedRun`, and the shared `spawnCapturedRunPane` helper. `SessionCanvasRoute` wired service activity frames into adoption.
- Result: CMDK creation and MCP adoption both create the same captured run pane shape through `spawnCapturedRunPane`.

`git log --follow`, `git log -Sprepare_captured_run`, `git log -ScreateWithDisposition`, and the three commit diffs show no later removal of either launch path from the shared capture seam.

## 3. Deliberate or incidental

The commit history contains no launch entrypoint split to classify.

The different browser sequencing was deliberate and explicit:

- `4b2d4728` names service launch and threads it through the common runtime and capture path.
- `e05373b6` names canvas adoption and adds the post launch pane hydration path.

Neither commit message states a reason for bypassing `prepare_captured_run`, and neither commit performs such a bypass.

## 4. Current MCP path and the missing canvas step

The current MCP launch chain is:

1. `api/src/transport_matters/api/v1/controlplane_mcp.py`, MCP `launch`
2. `_McpControlPlaneAdapter.launch`
3. `api/src/transport_matters/controlplane/service.py`, `ControlPlaneService.launch`
4. `api/src/transport_matters/controlplane/launch_service.py`, `ControlPlaneLauncher.launch`
5. `ControlPlaneLauncher._prepare_and_execute`
6. `ControlPlaneLauncher._execute`
7. `ControlPlaneGatewayPort.create_run`, implemented by `api/src/transport_matters/api/v1/controlplane_gateway_runs.py`, `create_run`
8. `POST /v1/runs`
9. `packages/runtime/src/server/runtimeRouter.ts`, `registerRunRoutes`
10. `packages/runtime/src/service/RunManager.ts`, `RunManager.createWithDisposition`
11. `RunManager.createNew`
12. `packages/runtime/src/adapters/CaptureRpcClient.ts`, `CaptureRpcClient.prepareCapture`
13. `POST /v1/capture/prepare`
14. `api/src/transport_matters/api/v1/capture_rpc_routes.py`, `prepare_capture`
15. `api/src/transport_matters/capture_rpc.py`, `CaptureLeaseRegistry.prepare_capture`
16. `CaptureLeaseRegistry._prepare_with_dependencies`
17. `api/src/transport_matters/captured_run.py`, `prepare_captured_run`

The current CMDK run chain joins the same server chain:

1. `www/packages/canvas/src/launcher/templateRows.ts`, `spawnCommand`
2. `www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts`, `useCanvasCommandHandler`
3. `www/packages/canvas/src/model/canvasActions.ts`, `createCapturedRunActions.addCapturedRun`
4. `spawnCapturedRunPane`
5. `CanvasStoreActions.spawnPane`
6. `insertPane`
7. `CapturedRunPane`
8. `useCapturedRunBinding`
9. `CapturedRunState.ensureRun`
10. `www/packages/core/src/transport.ts`, `createCapturedRunView`
11. `POST /v1/runs`, then the shared server chain above

MCP does not execute the browser precreation step `useCanvasCommandHandler` to `addCapturedRun`. It never did. The intended equivalent pane registration after an MCP run starts is:

1. `SessionCanvasRoute.onActivityFrames`
2. `CapturedRunAdoptionReconciler.applyFrames`
3. `candidateFromWire`
4. `CapturedRunAdoptionReconciler.attempt`
5. `CanvasStoreActions.adoptCapturedRun`
6. `spawnCapturedRunPane`
7. `CanvasStoreActions.spawnPane`
8. `insertPane`

The invisible MCP runs identify the Activity subscription boundary as the missing execution. The lifecycle row never reaches `SessionCanvasRoute.onActivityFrames`, so the remaining adoption chain has no candidate to process.

## 5. Captured run registration, Native, and vitals

No split commit explains a run failing to register as captured because no split commit exists.

`CaptureLeaseRegistry.prepare_capture` registers every successfully prepared run in `_leases` and `_facts` immediately after `prepare_captured_run` returns. It then calls `CaptureLeaseRegistry._emit_lifecycle`. That emission is best effort through `emit_run_lifecycle_best_effort`, so a captured run can remain registered even when its activity row or vitals never reaches the browser.

`www/packages/canvas/src/workbench/PaneWindow.tsx`, `PaneWindow`, only renders the run subtitle and `RunVitalsStrip` when `pane.contentRef.kind === "captured-run"`. Its `Native` text is the fallback for a captured run with no `agentName` or `agentId`. `Native` therefore describes catalog identity, not capture status.

The Native pane with no vitals is consistent with a captured run whose lifecycle activity is absent from the canvas stream. The same missing activity prevents `CapturedRunAdoptionReconciler` from seeing MCP service runs. The history does not tie that activity failure to a launch entrypoint split.

## 6. Adoption end to end

### Emitter

Both CMDK and MCP reach the same lifecycle emitter:

1. `api/src/transport_matters/capture_rpc.py`, `CaptureLeaseRegistry.prepare_capture`, registers `_leases` and `_facts`.
2. `CaptureLeaseRegistry.prepare_capture` calls `CaptureLeaseRegistry._emit_lifecycle`.
3. `api/src/transport_matters/run_lifecycle.py`, `build_run_lifecycle_event`, builds the `run-started` row with workspace, owner, harness, launch kind, name, and agent id.
4. `emit_run_lifecycle_best_effort` calls the emitter bound by `api/src/transport_matters/main.py`, `lifespan`.
5. `api/src/transport_matters/session/writer.py`, `SessionWriter.submit_run_lifecycle_event`, persists the row.

MCP supplies `launchKind: "service"` through `api/src/transport_matters/api/v1/controlplane_gateway_runs.py`, `create_run`. CMDK leaves the runtime default as `canvas`.

### Activity client

1. `packages/activity/src/adapters/postgresRecords.ts`, `PostgresActivityReader.runsForWorkspace`, queries lifecycle rows by the exact workspace slug, workspace hash, and owner.
2. `packages/activity/src/server/activityRouter.ts`, `createActivityRouter`, subscribes first and then sends a persisted snapshot, so subscription timing does not lose the run.
3. `www/packages/canvas/src/infrastructure/stream/useWorkspaceActivityStream.ts`, `useWorkspaceActivityStream`, opens `/v1/workspaces/{workspaceId}/activity/stream`.
4. `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx`, `SessionCanvasRoute.onActivityFrames`, sends every received frame to `RunVitalsState.applyFrames` and `CapturedRunAdoptionReconciler.applyFrames`.

### Predicate and run lookup

1. `www/packages/canvas/src/model/capturedRunAdoption.ts`, `candidateFromWire`, accepts only `launch_kind === "service"`, a supported harness, and a safe run id.
2. `CapturedRunAdoptionReconciler.attempt` calls `www/packages/core/src/transport.ts`, `getRun`.
3. `capturedRunAdoption.ts`, `attachableRun`, validates run id, harness, attachable state, Worktree id, and nullable identity fields.

### PaneRecord and layout insertion

1. `SessionCanvasRoute.createCapturedRunAdoptionReconciler` calls `CanvasStoreActions.adoptCapturedRun`.
2. `www/packages/canvas/src/model/canvasActions.ts`, `createCapturedRunActions.adoptCapturedRun`, calls `CapturedRunState.adoptRun`.
3. `createCapturedRunActions.adoptCapturedRun` calls the shared `spawnCapturedRunPane`.
4. `CanvasStoreActions.spawnPane` calls `insertPane`.
5. `canvasActions.ts`, `insertPane`, creates the PaneRecord with `createPaneRecord` and returns both the updated `panes` map and the updated layout from one Zustand mutation.

## 7. Exact stop point and failing condition

The MCP run stops at the Activity client scope. Event emission and persistence occur. The browser requests a different workspace, so the lifecycle row is excluded by `PostgresActivityReader.runsForWorkspace`.

The concrete failing condition is:

```text
active Worktree workspaceSlug/workspaceHash
!=
SessionCanvasRoute activityWorkspaceId from meta.workspaceId
```

The state split is visible in these symbols:

- `www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts`, `activateWorktree`, changes the URL and calls `initializeVerifiedCanvas`.
- `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx`, `storeIdentity` and `resolvedLaunch`, follow the selected Worktree.
- `SessionCanvasRoute.activityWorkspaceId` ignores `storeWorktreeId` and `resolvedLaunch`.
- `www/packages/core/src/useMeta.ts`, `useMeta`, caches backend meta indefinitely because the backend cwd is fixed.
- `api/src/transport_matters/api/v1/meta.py`, `get_meta`, computes `workspace_id` from that fixed cwd.

The causal SHAs are:

- `350e50c1f04c75075dcb36009df9aacdfd8d151c`, `feat(canvas): always-on per-pane vitals strip (slice 4 PR-2b) (#256)`, introduced `activityWorkspaceId = resolved?.workspaceId ?? meta?.workspaceId ?? ""`.
- `e05373b6a4f5a101f1f4da95d499682e6bc8ee11`, `feat(controlplane): S6b canvas adoption reconciler (#283)`, connected service adoption to that Activity stream.
- `6453364a4ae15711a6cb01f6db71bca98a7259ee`, `feat: add Canvas and Worktree CRUD foundation (#316)`, added server projected `workspaceSlug` and `workspaceHash` to `WorktreeSummary`.
- `8e240663c83c80492f1fb3a1d0158fb63d23777b`, `feat(canvas): add Space command management`, added in place Worktree activation.
- `699fb5786091ae5da1c86c688baa7ec714662084`, `feat(canvas): sticky launch identity and CMDK reachability from empty DB`, made the selected Canvas identity sticky while leaving Activity subscription identity on resolved session or meta.

`8e240663` exposed the latent mismatch. `699fb578` preserved the selected identity correctly for Canvas launch while the Activity stream continued to use the fixed backend launch workspace.

## 8. Which launch paths work

Service adoption works when the service run lifecycle workspace equals `SessionCanvasRoute.activityWorkspaceId`. This includes MCP launches scoped to the desktop API launch workspace and launch session routes whose `resolved.workspaceId` matches the service run. `SessionCanvasRoute` then receives the snapshot, `candidateFromWire` accepts `launch_kind === "service"`, `getRun` returns the runtime identity, and `insertPane` creates the PaneRecord and layout node.

CMDK launches do not use adoption. `CanvasCommandDispatcher.useCanvasCommandHandler` calls `createCapturedRunActions.addCapturedRun`, which creates the PaneRecord and layout before `POST /v1/runs`. The adoption predicate deliberately rejects CMDK lifecycle rows because their launch kind is `canvas`.

CMDK vitals still depend on the same workspace equality. A CMDK pane can exist with an empty strip when its run belongs to a selected Worktree whose workspace differs from `activityWorkspaceId`.

## 9. Native label, agent metadata, and empty vitals

`www/packages/canvas/src/workbench/PaneWindow.tsx`, `PaneWindow`, renders `Native` when no agent name or agent id is present in the captured run record or pane ref. SHA `e874c30ff70c631aeb00b55ff8ef672c164af122`, `feat: surface managed agent runtimes (#286)`, introduced that fallback.

`www/packages/canvas/src/workbench/chrome/RunVitalsStrip.tsx`, `RunVitalsStrip`, reads the managed run id from `CapturedRunState` and then looks up Activity data in `RunVitalsState.byRunId`. An empty mounted strip means no Activity item exists for that run id in the current client store. That observation directly supports the wrong workspace subscription condition because vitals and service adoption consume the same `onActivityFrames` callback.

Missing agent metadata is additional support only when the MCP launch specified an agent. Service adoption copies `name`, `agentId`, and `agentName` from `getRun`. If no agent was requested, `Native` is the expected label and does not independently prove an adoption failure.

## 10. Smallest recommended change

Bind `SessionCanvasRoute.activityWorkspaceId` to the active Worktree's server projected workspace identity. `www/packages/core/src/spaceTransport.ts`, `WorktreeSummary`, already carries `workspaceSlug` and `workspaceHash`. Resolve the selected `storeWorktreeId` from the existing Space inventory, form the full workspace id from those fields, and use it ahead of `meta.workspaceId`. Keep `resolved.workspaceId` for explicit launch session routes and retain meta only as the no selected Worktree fallback.

The stream and `CapturedRunAdoptionReconciler` already recreate when `activityWorkspaceId` changes. No emitter, predicate, run lookup, pane insertion, or layout change is required.
