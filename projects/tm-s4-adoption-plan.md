# S4 MCP canvas adoption plan

Baseline: `ml/s4-adoption` at `9c9b06f874193b3d9669976dbc790790a495ff6c`, clean.

## Fix shape

Keep one Activity subscription. Bind it to the workspace of the Worktree selected by the already resolved Canvas identity. Recreate that subscription when the selected Worktree changes. Reuse the Activity snapshot to recover service runs that started before the client subscribed.

The required precedence is:

1. A resolved launch session workspace for an explicit session route.
2. The server projected workspace of `resolvedLaunch.worktreeId` within `resolvedLaunch.spaceId`.
3. `meta.workspaceId` only when the active selection is unscoped or exactly matches the affinity carried by meta.
4. No subscription while a selected Worktree is unresolved or mismatched.

This keeps Canvas identity policy at its current resolution call site. It does not write workspace identity into the Canvas store.

## Reuse map

| Capability | Owning file and symbol | Current precedence or contract | Planned reuse |
|---|---|---|---|
| Canvas route identity | `www/packages/canvas/src/route.ts`, `resolveCanvasLaunchIdentity` | Route fields are verified against one usable identity source. | Keep unchanged. Activity follows the resulting `resolvedLaunch`. |
| Identity source precedence | `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx`, `identity` and `resolvedLaunch` | Usable server meta wins. Otherwise the verified store identity stands. | Use `resolvedLaunch.spaceId` and `resolvedLaunch.worktreeId`. Do not add another identity resolver. |
| In place Worktree selection | `www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts`, `activateWorktree` and `initializeVerifiedCanvas` | URL replacement occurs first, then the same `resolveCanvasLaunchIdentity` policy initializes the store. | Keep unchanged. The route render caused by the store update supplies the new `resolvedLaunch`. |
| Canvas identity state | `www/packages/canvas/src/model/canvasStoreLifecycle.ts`, `initializeCanvas` | Sole store mutation owner for launch derived Space, Worktree, Canvas, and workspace hash fields. | Do not add workspace slug or full workspace id to this state. |
| Server Worktree workspace identity | `www/packages/core/src/spaceTransport.ts`, `WorktreeSummary.workspaceSlug` and `WorktreeSummary.workspaceHash` | Server projected from canonical Worktree path. | Form the selected Worktree workspace id from these fields. |
| Complete Space and Worktree inventory | `www/packages/canvas/src/launcher/useSpaces.ts`, `useSpaces`, `fetchSpaceInventory`, and `SPACES_QUERY_KEY` | One paged React Query cache. `spaceCommandDispatcher.refreshSpaces` invalidates the same owner after mutations. | Reuse this cache. Do not add a second `fetchWorktree` query or cache. |
| Workspace id assembly | None found in the frontend. Searches: `workspaceSlug`, `workspaceHash`, `workspaceIdParts`, `asWorkspaceId`, and combined slug/hash expressions under `www/packages` and `packages`. | Backend and Activity adapters assemble `slug/hash`, but no frontend builder is exported. | Assemble once beside Activity subscription resolution. Do not introduce a one caller helper. |
| Active Worktree lookup | None found. Searches: `useWorktree`, `fetchWorktree`, `worktrees.find`, `flatMap(worktrees)`, and Worktree query keys. | `useSpaces` is the existing data owner. | Resolve the Worktree inside the selected Space with one memoized lookup. |
| Activity workspace precedence | `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx`, `activityWorkspaceId` | Resolved launch session, then fixed `meta.workspaceId`, then empty. The active Worktree is absent. | Replace this expression with the precedence stated above. |
| Activity connection lifecycle | `www/packages/canvas/src/infrastructure/stream/useWorkspaceActivityStream.ts`, `useWorkspaceActivityStream`; `www/packages/core/src/useEventSource.ts`, `useEventSource` | The string URL is the stream key. A changed workspace closes the old EventSource and opens a new one. | Reuse unchanged. A Worktree switch naturally re-establishes the stream. |
| Pre-subscription race recovery | `packages/activity/src/server/activityRouter.ts`, `createActivityRouter` | Subscribes before reading, sends a persisted snapshot, then drains pending deltas. Every reconnect gets a fresh snapshot. | Reuse unchanged. A service run launched before the browser listens appears in the first selected workspace snapshot. |
| Vitals ingestion | `www/packages/canvas/src/model/runVitalsStore.ts`, `RunVitalsState.applyFrames` | Snapshot and delta frames own the current per-run vitals projection. | Keep the existing `SessionCanvasRoute.onActivityFrames` fanout. |
| Service adoption predicate | `www/packages/canvas/src/model/capturedRunAdoption.ts`, `candidateFromWire` and `CapturedRunAdoptionReconciler` | Only `launch_kind === "service"` with a supported harness and safe run id is eligible. A fresh snapshot rearms dormant candidates. | Reuse unchanged. |
| Runtime identity lookup | `www/packages/canvas/src/model/capturedRunAdoption.ts`, `CapturedRunAdoptionReconciler.attempt` and `attachableRun`; `www/packages/core/src/transport.ts`, `getRun` | Run id, harness, state, Worktree, name, agent id, and agent name are validated before adoption. | Reuse unchanged. |
| Captured run identity | `www/packages/canvas/src/model/capturedRunStore.ts`, `CapturedRunState.adoptRun` | Idempotent by managed run id. Stores service origin and runtime identity. | Reuse unchanged. |
| Pane and layout creation | `www/packages/canvas/src/model/canvasActions.ts`, `createCapturedRunActions.adoptCapturedRun`, `spawnCapturedRunPane`, `CanvasStoreActions.spawnPane`, and `insertPane` | One shared captured pane path. `insertPane` updates PaneRecord and layout in one store mutation. | Reuse unchanged. |
| User visible metadata and vitals | `www/packages/canvas/src/workbench/PaneWindow.tsx`, `PaneWindow`; `www/packages/canvas/src/workbench/chrome/RunVitalsStrip.tsx`, `RunVitalsStrip` | Subtitle resolves agent name or id. The strip resolves Activity by managed run id. | Assert these DOM outputs in the regression tests. |

## Quality map

### Second writer risk

`CanvasStoreModel.workspaceHash` is launch derived and lacks the workspace slug. Populating it from Worktree inventory would create another writer to selected identity and would still leave an incomplete Activity key. The fix must derive the subscription workspace in `SessionCanvasRoute` without mutating the store.

`activateWorktree` and the route effect both initialize Canvas state, but both already use `resolveCanvasLaunchIdentity`. No new writer or policy branch is needed.

### Duplication

CMDK creation and MCP adoption already converge at `spawnCapturedRunPane`, `CanvasStoreActions.spawnPane`, and `insertPane`. Creating another MCP pane path would duplicate pane identity and layout policy.

`useSpaces` already owns the complete Worktree inventory and its invalidation. A direct `fetchWorktree` query in the route would duplicate read and cache ownership.

### Boundary problem

`useSpaces` is stored under `launcher` although `workbench/spaceCommandDispatcher.ts` already consumes its query owner. `SessionCanvasRoute` would become another non-launcher consumer. Move this shared query owner to `www/packages/canvas/src/hooks/useSpaces.ts` before adding the route import, update all imports, and delete the old path. Move its test to `www/packages/canvas/src/hooks/useSpaces.test.tsx`. Preserve `SPACES_QUERY_KEY`, paging, stale time, and mutation invalidation exactly.

### Test structure

`www/packages/canvas/src/workbench/SessionCanvasRoute.test.tsx` is 776 lines at the baseline, above the repository limit. Refactor it before adding coverage. Move the Activity and adoption cases into `SessionCanvasRoute.activity.test.tsx` and extract shared route fixtures and the captured pane test double into `SessionCanvasRoute.testSupport.tsx` so neither suite duplicates setup.

Several existing Activity tests assert an EventSource URL or Zustand contents. Keep useful protocol coverage, but the new red tests must assert pane chrome, vitals text, agent subtitle, and one visible pane.

### Dead code

No dead adoption branch was found. The emitter, snapshot, predicate, lookup, idempotent run record, and shared pane insertion are all live and required. The production change should remove only the obsolete fixed meta fallback expression.

## Ordered plan

1. Refactor without behavior change.
   - Move the shared Space inventory query owner from `launcher/useSpaces.ts` to `hooks/useSpaces.ts`, and move its test beside it. Update `useLauncherData`, `spaceCommandDispatcher`, and affected tests. Delete the old path.
   - Split the 776 line `SessionCanvasRoute.test.tsx` by moving Activity and adoption coverage into `SessionCanvasRoute.activity.test.tsx`. Extract common setup into `SessionCanvasRoute.testSupport.tsx` rather than copying it.
   - Run the existing focused route suites after the move to prove the refactor is neutral.

2. Add and commit the red regressions before production code.
   - `adopts a service run already present in the selected Worktree snapshot and renders its pane, vitals, and agent metadata when meta names another workspace`.
     - Arrange backend meta for workspace A.
     - Arrange the active resolved Worktree in Space inventory for workspace B.
     - Arrange the first workspace B snapshot to contain a service run that already exists.
     - Return `name`, `agentId`, and `agentName` from `getRun`.
     - Assert one captured run pane, the agent subtitle, token text, and status text.
     - This fails at the baseline because the client remains on workspace A and never receives the workspace B snapshot.
   - `after a Worktree switch, adopts a service run already present in the new snapshot and renders its pane, vitals, and agent metadata`.
     - Start on Worktree A.
     - Switch through the existing URL plus verified Canvas initialization path to Worktree B.
     - Place a preexisting service run in Worktree B's first snapshot.
     - Assert the visible pane, agent subtitle, token text, status text, and a single pane instance.
     - This fails at the baseline because the Activity stream does not follow the switch.
   - Keep the tree clean before running the red command and record the expected user visible assertion failure.

3. Resolve the selected Worktree through the existing inventory.
   - In `SessionCanvasRoute`, call the shared `useSpaces` owner.
   - Find `resolvedLaunch.spaceId`, then find `resolvedLaunch.worktreeId` within that Space.
   - Build the full workspace id once from the server projected slug and hash.
   - Treat a selected Worktree that is still loading, missing, or mismatched as unresolved. Do not temporarily subscribe to unrelated meta.

4. Replace the Activity precedence at its current call site.
   - Keep `resolved.workspaceId` first for explicit launch session routes.
   - Use the resolved active Worktree workspace second.
   - Use meta only when the resolved selection is unscoped or exactly matches `meta.spaceId` and `meta.worktreeId`.
   - Otherwise pass an empty workspace id and leave the stream disabled until authoritative Worktree data arrives.
   - Do not change Canvas store shape, route parsing, activation commands, adoption predicate, captured run state, or pane creation.

5. Let existing lifecycle owners complete adoption.
   - The changed workspace id makes `useEventSource` close and reopen.
   - The new `CapturedRunAdoptionReconciler` instance consumes the first snapshot.
   - `RunVitalsState.applyFrames` receives the same snapshot.
   - `getRun` supplies agent metadata.
   - `adoptCapturedRun` creates the PaneRecord and layout through the shared path.

6. Prove the user outcome.
   - Run the focused route suite and confirm both red tests turn green.
   - Confirm each case renders one pane with agent metadata and nonempty vitals.
   - Run the repository gates from a clean commit.

## Subscription and race answers

- Follow the active Worktree's workspace with one subscription.
- Do not subscribe to several workspaces. Workspace wide service adoption would otherwise place runs from inactive Worktrees into the current Canvas.
- Re-establish the subscription on every resolved Worktree workspace change. `useEventSource` already owns teardown and reopen through its string stream key.
- A run launched before the client subscribes is recovered from the persisted Activity snapshot sent on connection. The server subscribes before reading that snapshot, so deltas that race with the read are drained after it.
- While the selected Worktree inventory is unresolved, keep Activity disabled. Opening the meta workspace temporarily could adopt a run from the wrong Worktree.

## Gate commands

Red and focused green command, from a clean commit:

```bash
pnpm --filter @tm/shell exec vitest run ../canvas/src/workbench/SessionCanvasRoute.activity.test.tsx
```

Repository gates, each from a clean tree:

```bash
just check
just test
```

Final provenance:

```bash
git status --short --branch
git rev-parse HEAD
```

## Design decision

Decisions needed: 0.

The existing product model already supplies the answer. One Canvas has one active Worktree default, service adoption writes into that Canvas, and Activity snapshots recover missed launch timing. Following the active Worktree preserves that authority. Multi-workspace subscription would violate it.
