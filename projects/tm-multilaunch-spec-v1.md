# `launch_batch` v1 implementation specification

Status: implementation ready for architect review  
Date: 2026-07-21  
Governing authority: `LAUNCH-CONTRACT.md`  
Repository baseline: `feat/multi-launch` at `8c51797e01ef3880bb76517bafbe620766cbffe7`

## 1. Outcome

`launch_batch` accepts one inline, placement free launch profile plus an invocation time
Canvas placement vector. The server validates the complete batch, mints every candidate
key, records durable claims, then fans candidates through the existing single item launch
authority. Candidate failures are isolated. Results retain request order.

The three independent candidate axes are:

1. prompt strategy
2. Worktree selection
3. Canvas placement

Model and effort remain target fields on each candidate.

The resolved candidate is the profile item plus its invocation placement. Canvas placement
is never stored in the durable profile definition.

The batch unit is `(owner, dispatch_id)`. The item unit is
`(owner, dispatch_id, candidate_key)`. Canvas identity does not define a batch.

## 2. Locked boundaries

1. Every item enters `ControlPlaneLauncher.launch`. There is no batch resolver, capture
   path, or `RunManager` fanout.
2. Candidate keys are deterministic server UUIDs derived before fanout. Clients cannot
   submit them.
3. Gateway idempotency is candidate scoped before any candidate task starts.
4. The browser performs one control plane batch request. It never loops over `/v1/runs`.
5. Each item reuses
   `api/src/transport_matters/captured_run_context.py:_prepare_home_and_grant`, so each run
   retains its own operational HOME.
6. `canvas_id` is immutable launch affinity. Clients continue to own pane records, layout,
   focus, dock state, and Canvas lifecycle.
7. No `ManagedRunFilters.canvasId` is added in v1. Activity is the durable reconstruction
   path.
8. Durable profile persistence is L1. v1 freezes the placement free profile shape but only
   accepts it inline.
9. Evaluation artifacts and comparison are L2.

## 3. Contract delta

### 3.1 Accepted v1 deviation: workspace snapshot

The governing contract says a batch adds one sealed workspace snapshot. The repository has
no workspace sealer, immutable snapshot record, or isolated materializer. A synthetic
snapshot ID would assert an isolation guarantee that does not exist.

Foundation v1 therefore makes this explicit deviation:

* `workspace_snapshot_id` is always `null`.
* Each candidate runs in a current, registered `Worktree` selected by `worktree_ref`.
* `shared` mode uses one live Worktree for all candidates.
* `per_candidate` mode requires distinct, pre-existing Worktree IDs.
* v1 receipts and UI must say `workspace_basis: "live_worktree"`.
* v1 batches are unsuitable for fair evaluation claims.
* L2 is blocked until one real snapshot is sealed once and every candidate receives an
  isolated writable materialization from it.

Before foundation v1 merges, the `LAUNCH-CONTRACT.md:launch_batch request` paragraph must
qualify its snapshot sentence by version. No implementation may emit a non-null snapshot
ID until real sealing and materialization exist.

### 3.2 Closed contract gap: durable replay

The current `api/src/transport_matters/controlplane/launch_ledger.py:LaunchLedger` is
process resident and keyed by `(owner, dispatch_id)`. v1 replaces launch truth with a
Postgres backed item ledger keyed by `(owner, dispatch_id, candidate_key)`. A process map
remains only a local single flight accelerator.

The accepted replay rules are:

* same key and same normalized item digest returns the frozen result or frozen failure
* same key and a different digest returns `dispatch_conflict`
* a terminal item never calls the gateway again
* an item interrupted by process loss is sealed as terminal `unknown` with public code
  `busy_gateway`; the same dispatch cannot spawn a second process
* the caller uses a new dispatch ID to retry an interrupted item
* a terminal result can be replayed after its process resident run has ended; the receipt
  describes the sealed creation outcome, while `getRun` reports current attachability

The item leader holds a Postgres advisory lock derived from the full item key until the
terminal row and pending audit payload are durable. A second API process cannot actuate the
same item. A competing process waits for the terminal row. If the lock becomes acquirable
while the row is nonterminal and no local task owns it, the new holder seals the interrupted
failure and does not call the gateway.

This closes batch replay and second process prevention. It does not claim that the current
repository has implemented every broader `FrozenLaunchSpec` and pinned catalog requirement
in `LAUNCH-CONTRACT.md`.

### 3.3 Canvas affinity

`canvas_id` enters the frozen create facts for a run and is projected through Activity. It
does not enter `LaunchProfileDefinition`. The same profile may be invoked into different
Canvases without mutation.

Only a real `api/src/transport_matters/space/models.py:CanvasId` UUID is accepted. Client
cache keys such as `space:<space_id>` and `direct-local` are presentation keys. Server
affinity accepts Canvas UUIDs only. A null placement means deliberately unplaced.

The server validates every non-null Canvas before fanout:

* Canvas exists
* Canvas owner equals caller owner
* Canvas belongs to `profile.space_id`
* Canvas is not archived

The affinity is immutable for the run. Moving a pane between Canvases remains a client
operation and does not rewrite launch history.

### 3.4 Canvas filter decision

Do not add `packages/runtime/src/service/runManagerTypes.ts:ManagedRunFilters.canvasId` in
v1.

`ManagedRunFilters` only filters the process resident `/runs` registry. It cannot restore
affinity after a browser reconnect and it does not serve MCP roster reconstruction. The
existing Activity stream sends a workspace snapshot on connection. Persisting `canvas_id`
in `run_lifecycle_event`, projecting it through `ActivityWireRun`, and filtering in
`capturedRunAdoption.candidateFromWire` gives each Canvas route the required drill flow.

A filter can be added later if server side list or stop by Canvas becomes a measured need.
The Canvas layering track owns that future work. Batch v1 excludes it.

### 3.5 Failure contract addition

| Code | Meaning |
| --- | --- |
| `busy_gateway` | Gateway unavailable, saturated, or left with an unknown outcome. The receipt is terminal for the accepted dispatch. |

## 4. Typed shapes

All new public Pydantic models use `ConfigDict(frozen=True, extra="forbid")`. Public
TypeScript decoders reject unknown authority fields. JSON names stay snake case on Python
control plane surfaces and camel case on the Python to Node gateway surface.

### 4.1 Shared item fields

Add these shapes in `api/src/transport_matters/controlplane/run_models.py`:

```text
LaunchTargetIntent {
  harness: "claude" | "codex"
  model: string | null
  effort: string | null
  agent: string | null
  name: string | null
  grant: "none" | "observer" | "director"
}

LaunchItemIntent extends LaunchTargetIntent {
  workdir: string
  first_prompt: string | null
}

LaunchRequest extends LaunchItemIntent {
  dispatch_id: UUID | null
}
```

`LaunchRequest` remains the single launch public input. Refactoring it through the two base
models removes duplicate launch fields from the batch profile model.

### 4.2 Three state prompt

```text
LaunchPromptSpec {
  mode: "inherit" | "interactive" | "text"
  text: string | null
}
```

Validation:

* `inherit` requires `text=null` and resolves to `shared_first_prompt`
* `interactive` requires `text=null` and resolves to no startup prompt
* `text` requires nonblank text after outer whitespace validation and preserves the exact
  accepted string for delivery

This model avoids a schema union and preserves the difference between omitted inheritance
and an explicit prompt free launch.

### 4.3 Placement free profile definition

```text
WorktreeMode = "shared" | "per_candidate"

LaunchProfileItem extends LaunchTargetIntent {
  prompt: LaunchPromptSpec
  worktree_ref: WorktreeId | null
}

LaunchProfileDefinition {
  spec_version: 1
  space_id: SpaceId
  worktree_mode: WorktreeMode
  default_worktree_ref: WorktreeId
  shared_first_prompt: string | null
  candidates: tuple[LaunchProfileItem, 1..16]
}
```

Profile validation:

* `default_worktree_ref` exists, belongs to `space_id` and owner, and is launchable
* `shared` requires every item `worktree_ref=null`
* `per_candidate` requires every item `worktree_ref` and requires those IDs to be distinct
* every selected Worktree has a path and is neither missing nor archived
* no profile field contains `canvas_id`, `canvas_ref`, `dispatch_id`, `candidate_key`, owner,
  actor, or workspace identity

`LaunchProfileDefinition` is the future L1 persisted payload. Persistence adds only profile
identity, name, owner, and revision around this definition.

### 4.4 Invocation and result

```text
LaunchBatchRequest {
  spec_version: 1
  dispatch_id: UUID | null
  profile: LaunchProfileDefinition
  placements: tuple[CanvasId | null, same length as profile.candidates]
}

LaunchBatchOutcome {
  candidate_index: integer >= 0
  candidate_key: UUID
  canvas_id: CanvasId | null
  result: LaunchResult | null
  failure: ControlPlaneFailure | null
}

LaunchBatchResult {
  spec_version: 1
  dispatch_id: UUID
  workspace_snapshot_id: null
  workspace_basis: "live_worktree"
  outcomes: tuple[LaunchBatchOutcome, same request order]
}
```

Exactly one of `result` and `failure` is non-null. A provider model rejection remains a
successful `LaunchResult` with `first_prompt.status="failed"`, matching single launch.
Operational and policy errors become the existing
`controlplane.errors.ControlPlaneFailure` envelope for that item.

The server rejects the entire batch before fanout when the outer shape, length relation,
Space, Worktree, or Canvas preflight is invalid. After fanout begins, candidate failures are
isolated into outcomes.

Extend `api/src/transport_matters/controlplane/errors.py:ControlPlaneErrorCode` with
`dispatch_conflict`. Durable claim digest mismatches use that governing contract code.
Shape and field validation keeps `invalid_request`.

### 4.5 Internal caller and identity

Add these internal immutable dataclasses in
`api/src/transport_matters/controlplane/run_models.py`:

```text
LaunchActorContext {
  actor: string
  owner: string
  source_space_id: SpaceId
  bypass_permissions: bool
}

LaunchCallerContext {
  actor: string
  owner: string
  space_id: SpaceId
  worktree_id: WorktreeId
  workspace_id: string
  workspace_root: string
  bypass_permissions: bool
}

LaunchInvocationIdentity {
  dispatch_id: UUID
  candidate_key: UUID
  gateway_idempotency_key: UUID
}
```

`ControlPlanePrincipal` remains the authenticated agent authority. Agent REST and MCP call
`require_director` before resolving an actor session to `LaunchActorContext`. Batch
preflight combines that actor context with each selected Worktree to create one
`LaunchCallerContext` per item. Single launch resolves one item context from the actor's
current workspace. The same origin operator adapter constructs both contexts from server
resolved Space and Worktree facts. The browser cannot supply any context field.

This split is required for sibling Worktrees. The current
`api/src/transport_matters/controlplane/launch_service.py:ControlPlaneLauncher._prepare`
scopes every target under the actor session cwd. A sibling Worktree is outside that path.
The refactor replaces that path assumption with a `SpaceStore` validated Worktree root.
`ControlPlaneLauncher` still calls `scoped_launch_workdir` against the selected Worktree
root, so an item cannot escape its chosen checkout.

Generalize the owner and workspace read parameters used by
`api/src/transport_matters/controlplane/delivery_proof.py:DeliveryProofPort` and
`api/src/transport_matters/controlplane/read_store.py:ControlPlaneReadStore.wire_delivery_claims`
to a structural `ControlPlaneReadScope { owner, workspace_id }`. Both
`ControlPlanePrincipal` and `LaunchCallerContext` satisfy it. This lets the trusted operator
retain startup prompt proof without fabricating an agent principal.

Candidate identity rules:

* `SINGLE_LAUNCH_CANDIDATE_KEY` is one named fixed UUID
* batch candidate key is UUIDv5 of the server batch dispatch ID and zero based ordinal
* gateway key is UUIDv5 of dispatch ID and candidate key
* all keys are computed for all candidates before the first candidate task is created
* owner scopes the durable and gateway keys, so owner is not client controlled

Add `api/src/transport_matters/controlplane/launch_caller.py` with the shared authority
adapters:

```text
actor_context_for_principal(principal, reads, space_store) -> LaunchActorContext
caller_context_for_worktree(actor, resolved_worktree) -> LaunchCallerContext
```

The first helper reads the actor session cwd, resolves its Space, and proves the profile
source Space matches. The second derives `workspace_id` from the selected Worktree's stored
slug and hash and carries its canonical path as `workspace_root`.

`ControlPlaneLauncher.launch` becomes the one item interface:

```text
launch(
  caller: LaunchCallerContext,
  item: LaunchItemIntent,
  identity: LaunchInvocationIdentity,
) -> LaunchResult
```

Single launch adapts `LaunchRequest` to `LaunchItemIntent`, supplies the fixed candidate key,
and derives its gateway key. Batch materializes one `LaunchItemIntent` per profile item and
supplies the server candidate identity. No batch caller invokes `_prepare` or `_execute`
directly.

### 4.6 Batch service port

Add `api/src/transport_matters/controlplane/launch_batch_service.py`:

```text
LaunchBatchService.launch_batch(
  caller: LaunchActorContext,
  request: LaunchBatchRequest,
) -> LaunchBatchResult
```

Constructor ports:

```text
LaunchBatchService(
  launcher: ControlPlaneLauncher,
  space_store_factory: SpaceStoreFactory,
  ledger: DurableLaunchStore,
  dispatch_id_factory: Callable[[], UUID],
  concurrency: int = 5,
)
```

`MAX_LAUNCH_BATCH_CANDIDATES` is 16. The concurrency of 5 matches the current guarded Canvas
spawn concurrency in
`www/packages/canvas/src/model/capturedRunStore.ts:CAPTURED_RUN_SPAWN_CONCURRENCY` while
moving batch authority to the server. Rate limiting remains owner scoped through the item
launcher.

The service sequence is exact:

1. mint or accept the outer dispatch ID
2. canonicalize and digest the placement free profile plus invocation placements
3. claim or replay the batch header
4. load one `SpaceStore.get_space_snapshot`
5. verify `caller.source_space_id == profile.space_id`
6. validate every Worktree and Canvas from that snapshot
7. derive every per-item caller context, candidate key, and gateway key
8. create all durable item claims
9. fan item calls under one semaphore
10. convert `ControlPlaneError` to item failures
11. freeze ordered batch outcomes

No candidate starts unless steps 1 through 8 succeed for the full batch.

### 4.7 Gateway and run affinity fields

Extend these exact interfaces:

```text
GatewayCreateRunRequest {
  candidate_key: UUID
  canvas_id: CanvasId | null
  ...existing fields
}

GatewayRunView {
  canvas_id: CanvasId | null
  ...existing fields
}

LaunchResult {
  canvas_id: CanvasId | null
  ...existing fields
}

CreateManagedRunInput {
  candidateKey: string
  canvasId?: string
  ...existing fields
}

RuntimeRunView {
  canvasId: string | null
  ...existing fields
}
```

`runManagerSupport.createRunFingerprint` includes `candidateKey` and `canvasId`. A replay
with the same gateway key but different affinity conflicts before process creation.

Thread `canvasId` through:

```text
CreateManagedRunInput
-> RunManager.createWithDisposition
-> PrepareCaptureInput
-> CaptureRpcClient.prepareCaptureBody
-> PrepareCaptureRequest.to_domain
-> CapturedRunRequest
-> CaptureLeaseRegistry.prepare_capture
-> _CaptureRunFacts
-> build_run_lifecycle_event
-> RunLifecycleEventRow
```

`candidateKey` reaches the gateway input and fingerprint. The durable Python item row binds
`candidate_key`, `gateway_idempotency_key`, and `delivery_id`. This is the delivery identity
chain. Startup prompt delivery keeps the existing delivery proof behavior.

### 4.8 Audit identity

Extend `api/src/transport_matters/controlplane/audit.py:ControlPlaneAction` with
`candidate_key: UUID | None = None`. `launch_action` and `launch_failure_action` require the
item candidate key. Other verbs retain null.

Migration `0030_launch_batch_v1` replaces the current action uniqueness with null safe
uniqueness on:

```text
(actor, verb, dispatch_id, candidate_key)
```

Existing null candidate rows remain unique under the old semantics. Batch item launch rows
share dispatch ID and differ by candidate key. `ControlPlaneAuditSink.find` accepts
`candidate_key`, and SQL comparisons are null safe. Replays write zero duplicate action
rows.

## 5. Durable storage

Migration revision `0030_launch_batch_v1` stays below the repository 32 character revision
limit and follows `0029_native_connection_origin`.

### 5.1 Batch table

`control_plane_launch_batch`:

```text
owner text
dispatch_id uuid
request_digest bytea
candidate_count integer
workspace_snapshot_id uuid null
workspace_basis text = "live_worktree"
state text = "accepted" | "completed" | "failed"
result jsonb null
created_at timestamptz
updated_at timestamptz
PRIMARY KEY (owner, dispatch_id)
```

The result JSON is validated back through `LaunchBatchResult` on read. It preserves the
ordered, frozen replay receipt. Mutable current run state stays on Activity and `getRun`.

### 5.2 Item table

`control_plane_launch_item`:

```text
owner text
dispatch_id uuid
candidate_key uuid
candidate_index integer
item_digest bytea
gateway_idempotency_key uuid
canvas_id uuid null
delivery_id uuid null
state text = "accepted" | "started" | "completed" | "failed" | "unknown"
result jsonb null
failure jsonb null
audit_action jsonb null
audit_written boolean
created_at timestamptz
updated_at timestamptz
PRIMARY KEY (owner, dispatch_id, candidate_key)
UNIQUE (owner, dispatch_id, candidate_index)
FOREIGN KEY (owner, dispatch_id) REFERENCES control_plane_launch_batch
```

Single launch also uses this item table. Its batch header is a one item internal header so
the persistence and replay implementation has one path. The public single result remains
`LaunchResult`.

The table does not foreign key `canvas_id` to `canvas`. Launch history survives Canvas
deletion. Create time validation supplies integrity.

### 5.3 Item state transaction rules

* `accepted` is committed before preparation.
* `started` is committed immediately before gateway create and is never reverted.
* `completed`, `failed`, or `unknown` stores exactly one result or failure.
* The frozen audit action is stored in the same transaction as the terminal item.
* `audit_written` changes only after `ControlPlaneAuditWriter.write` succeeds.
* Replay retries the stored audit action before returning a receipt when audit is pending.
* An interruption from either `accepted` or `started` becomes `unknown`. No automatic spawn
  retry occurs under the same item key.

## 6. Canvas persistence and reconstruction

### 6.1 Server lifecycle migration

The same migration adds nullable `canvas_id uuid` to `run_lifecycle_event`. There is no
foreign key and no backfill guess. Existing lifecycle rows remain null. Extend:

* `api/src/transport_matters/session/models.py:RunLifecycleEventRow`
* `api/src/transport_matters/session/dao_statements.py:RUN_LIFECYCLE_EVENT_COLUMN_NAMES`
* `api/src/transport_matters/session/dao_rows.py:run_lifecycle_event_params`
* `packages/activity/src/adapters/postgresSchema.ts:RUN_LIFECYCLE_EVENT_COLUMNS`
* `packages/activity/src/adapters/postgresRecords.ts:runLifecycleFactFromRow`
* `packages/activity/src/adapters/postgresRecords.ts:runLifecycleSummaryFromRow`
* `packages/activity/src/adapters/postgresRecords.ts:RUNS_BY_WORKSPACE_SQL`
* `packages/contract/src/activity/wire.ts:ActivityWireRun`
* `packages/activity/src/server/activityRouter.ts:runToWire`
* `api/src/transport_matters/controlplane/activity.py:GatewayActivityRun`
* `api/src/transport_matters/controlplane/observe_models.py:RosterItem`
* `api/src/transport_matters/controlplane/roster_projection.py:project_roster`

Activity wire uses `canvas_id: string | null`. MCP roster gains the same nullable field.

### 6.2 Client storage version

Add `canvasId?: string` to
`www/packages/canvas/src/model/capturedRunStore.ts:CapturedRunRecord`. Bump
`CAPTURED_RUN_STORAGE_VERSION` from 7 to 8.

The v8 migration is a per record sanitizer:

* retain every valid v7 run record unchanged with absent `canvasId`
* retain a valid UUID `canvasId`
* remove only malformed `canvasId` fields
* remove only malformed run records
* preserve every valid sibling record and all launch settings

Tests must start with mixed valid and malformed records. They must prove one malformed or
dangling affinity never returns `{ runs: {} }` and never resets Canvas panes.

Do not bump
`www/packages/canvas/src/model/canvasStore.persistence.ts:CANVAS_STORE_STORAGE_VERSION`.
Pane record shape does not change. Its shared
`www/packages/canvas/src/infrastructure/persistence/canvasPersistOptions.ts:createCanvasPersistOptions`
migration currently returns an empty persisted Canvas for every version change, so an
unnecessary bump would erase pane layout. If a later slice changes pane schema, it must
first replace that blanket reset with a version aware, per record migration using
`www/packages/canvas/src/infrastructure/persistence/canvasPanePersistence.ts:readContentRefs`
behavior.

### 6.3 Rehydrate and dangling IDs

`www/packages/canvas/src/model/capturedRunAdoption.ts:CapturedRunAdoptionReconciler`
receives the active real Canvas UUID. Its `candidateFromWire` accepts a service run only
when `item.canvas_id` equals that UUID. Null affinity and a different Canvas are skipped.

`www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:snapshotCapturedRunPruneCandidates`
includes only records whose `canvasId` equals the active real Canvas UUID, plus legacy
records with no affinity that already have a pane in this Canvas. Records for another
Canvas are not treated as stale.

When the current Space snapshot no longer contains a persisted record's Canvas UUID,
rehydration skips that record for pane restoration and may prune that one run binding after
the normal bounded run lookup. It must retain all siblings. A missing Canvas never causes a
store wide wipe.

Add `www/packages/core/src/transport.ts:fetchCanvases` over the existing
`api/src/transport_matters/api/v1/space_routes.py:list_space_canvases` route. Fetch the
inventory only when the route has a real Space ID and remembered affinity records. A failed
inventory request retains every record and defers pruning. A successful inventory may drop
one confirmed dangling binding while preserving all siblings and every pane cache.

`www/packages/canvas/src/model/capturedRunStore.ts:adoptRun` records the server affinity. An
existing record with a different non-null affinity is not moved. The Activity fact wins and
the conflicting local record is reported to diagnostics.

Activity supplies multi-client reconstruction:

1. a Canvas route connects to its existing workspace Activity stream
2. the snapshot contains service runs and nullable `canvas_id`
3. the reconciler selects only its Canvas
4. `getRun` verifies current attachability and returns `RuntimeRunView.canvasId`
5. `canvasActions.adoptCapturedRun` creates the local pane

This avoids a target Canvas mutation API and avoids writing panes into the server
`Canvas.layout` JSON.

## 7. Reuse map

| Concern | Existing owner `file:symbol` | Decision |
| --- | --- | --- |
| Governing launch semantics | `LAUNCH-CONTRACT.md:Public request through verification` | Reuse, with the explicit live Worktree v1 delta in section 3.1. |
| Single request and receipt | `api/src/transport_matters/controlplane/run_models.py:LaunchRequest`, `LaunchResult` | Refactor shared fields, preserve single public shape, embed result in each batch outcome. |
| Structured failures | `api/src/transport_matters/controlplane/errors.py:ControlPlaneFailure`, `control_plane_failure` | Reuse unchanged per failed candidate. |
| Item authority | `api/src/transport_matters/controlplane/launch_service.py:ControlPlaneLauncher.launch` | Reuse for every candidate after caller and identity refactor. |
| Normalized intent | `api/src/transport_matters/controlplane/launch_service.py:_NormalizedLaunchRequest`, `_normalize_launch_request`, `_intent_fingerprint` | Reuse. Add candidate affinity to normalized item digest. |
| Item replay | `api/src/transport_matters/controlplane/launch_ledger.py:LaunchLedger`, `LaunchLedgerEntry` | Deviate. Replace durable truth with `DurableLaunchStore`; retain a small process task map only. |
| Failure isolation pattern | `api/src/transport_matters/controlplane/service.py:ControlPlaneService.close`, `_close_target` | Reuse ordered per target outcome and concurrent isolation pattern. |
| Service facade | `api/src/transport_matters/controlplane/service.py:ControlPlaneService.launch` | Reuse. Add thin `launch_batch` delegation and keep the file below 700 lines. |
| Item audit builders | `api/src/transport_matters/controlplane/action_builders.py:launch_action`, `launch_failure_action` | Reuse with required candidate key. |
| Audit persistence | `api/src/transport_matters/controlplane/audit.py:ControlPlaneAction`, `ControlPlaneAuditWriter` | Extend with candidate scoped null safe uniqueness. |
| Worktree and Canvas ownership | `api/src/transport_matters/space/store.py:SpaceStore.get_space_snapshot`, `resolve_worktree` | Reuse one owner scoped snapshot for full batch preflight. |
| Worktree and Canvas types | `api/src/transport_matters/space/models.py:SpaceId`, `WorktreeId`, `CanvasId`, `Canvas` | Reuse. Do not introduce parallel ID aliases. |
| Canvas inventory | `api/src/transport_matters/api/v1/space_routes.py:list_space_canvases` | Reuse for data safe client affinity rehydration. |
| Existing launch target lookup | `api/src/transport_matters/api/v1/launch_resolution.py:resolve_run_worktree` | Extract its store level validation so single and batch adapters share it. |
| Gateway request | `api/src/transport_matters/controlplane/run_models.py:GatewayCreateRunRequest` | Extend with candidate key and Canvas affinity. |
| Python gateway adapter | `api/src/transport_matters/api/v1/run_proxy.py:RunRouteProxy.create_run` | Reuse, project the two new fields. |
| Runtime create | `packages/runtime/src/service/RunManager.ts:RunManager.createWithDisposition` | Reuse. No batch method. Keep additions small enough to preserve the 700 line limit. |
| Runtime idempotency | `packages/runtime/src/service/runManagerSupport.ts:createRunFingerprint` | Reuse and include candidate key plus Canvas affinity. |
| Runtime create types | `packages/runtime/src/service/runManagerTypes.ts:CreateManagedRunInput`, `ManagedRunFilters` | Extend create input. Deliberately leave filters unchanged. |
| Runtime view | `packages/runtime/src/domain/runtimeRun.ts:RuntimeRunView` | Extend with nullable `canvasId`. |
| Capture port | `packages/runtime/src/ports.ts:PrepareCaptureInput`, `CapturedRunSpawnSpec` | Extend Canvas affinity through prepare and read back. |
| Capture client | `packages/runtime/src/adapters/CaptureRpcClient.ts:prepareCaptureBody` | Reuse and project `canvasId`. |
| Python capture request | `api/src/transport_matters/api/v1/capture_rpc_routes.py:PrepareCaptureRequest`, `to_domain` | Extend and validate nullable Canvas UUID. |
| Capture domain | `api/src/transport_matters/captured_run_models.py:CapturedRunRequest` | Extend with `canvas_id`. |
| Capture facts | `api/src/transport_matters/capture_rpc.py:_CaptureRunFacts`, `CaptureLeaseRegistry.prepare_capture` | Extend so started and exited lifecycle events agree. |
| Operational HOME | `api/src/transport_matters/captured_run_context.py:_prepare_home_and_grant` | Reuse unchanged once per candidate. |
| Lifecycle event | `api/src/transport_matters/run_lifecycle.py:build_run_lifecycle_event` | Extend with immutable Canvas affinity. |
| Lifecycle storage | `api/src/transport_matters/session/models.py:RunLifecycleEventRow`, `session/dao_statements.py:RUN_LIFECYCLE_EVENT_COLUMN_NAMES` | Extend nullable, without Canvas foreign key. |
| Activity projection | `packages/activity/src/adapters/postgresRecords.ts:runLifecycleFactFromRow`, `runLifecycleSummaryFromRow`, `RUNS_BY_WORKSPACE_SQL` | Extend Canvas fact into snapshot and updates. |
| Activity wire | `packages/contract/src/activity/wire.ts:ActivityWireRun`, `packages/activity/src/server/activityRouter.ts:runToWire` | Extend nullable `canvas_id`. |
| Roster | `api/src/transport_matters/controlplane/activity.py:GatewayActivityRun`, `controlplane/observe_models.py:RosterItem` | Extend Canvas affinity for MCP observability. |
| Agent REST skin | `api/src/transport_matters/api/v1/controlplane_routes.py:launch` | Add adjacent `launch_batch`, argument shaping only. |
| MCP skin | `api/src/transport_matters/api/v1/controlplane_mcp.py:_McpControlPlaneAdapter.launch`, `create_control_plane_mcp` | Add one shared schema tool, no fanout. |
| Browser origin trust | `api/src/transport_matters/api/v1/origin.py:require_http_origin` | Reuse for a server resolved operator adapter. |
| Browser transport | `www/packages/core/src/transport.ts:createCapturedRunView` | Add sibling `launchCapturedRunBatch`; never loop through the single create function. |
| Palette command | `www/packages/canvas/src/launcher/templateRows.ts:spawnCommand`, `launcher/commandTypes.ts:LauncherCommand` | Reuse row grammar, add one batch commit command. |
| Palette dispatch | `www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts:useCanvasCommandHandler` | Reuse, call one batch transport. |
| Activity adoption | `www/packages/canvas/src/model/capturedRunAdoption.ts:CapturedRunAdoptionReconciler`, `candidateFromWire`, `attachableRun` | Reuse with Canvas match and runtime Canvas verification. |
| Pane adoption | `www/packages/canvas/src/model/canvasActions.ts:adoptCapturedRun` | Reuse only for the active Canvas selected by Activity. No target cache API. |
| Run binding persistence | `www/packages/canvas/src/model/capturedRunStore.ts:CapturedRunRecord`, `adoptRun` | Extend with Canvas UUID and migrate version 7 to 8 per record. |
| Pane persistence | `www/packages/canvas/src/infrastructure/persistence/canvasPersistOptions.ts:createCanvasPersistOptions` | Do not bump its version. Its blanket reset is a known data loss hazard. |

## 8. Ordered PR sized slices

Every slice starts with the named failing tests. Every slice ends with the same repository
gates from the worktree root:

```text
just check
just test-affected
```

### Slice 1: durable item identity and restart replay

Deliverables:

* migration `0030_launch_batch_v1` creates batch and item tables, extends audit uniqueness,
  and adds lifecycle `canvas_id`
* `controlplane.launch_store.DurableLaunchStore` with claim, terminal write, audit retry,
  batch receipt, and advisory lock behavior
* `LaunchInvocationIdentity`, fixed single key, deterministic batch key helper, and gateway
  key helper
* `controlplane.errors.ControlPlaneErrorCode` gains `dispatch_conflict`
* single launch moves from process truth in `LaunchLedger` to the durable item store
* `main._start_session_store` injects one shared store into `ControlPlaneService`

Exact interfaces:

```text
DurableLaunchStore.claim_batch(owner, dispatch_id, request_digest, count)
DurableLaunchStore.claim_item(owner, identity, item_digest, candidate_index, canvas_id)
DurableLaunchStore.mark_started(claim)
DurableLaunchStore.finish(claim, result_or_failure, audit_action)
DurableLaunchStore.mark_audit_written(claim)
DurableLaunchStore.freeze_batch(owner, dispatch_id, result)
```

Failing tests first:

* `session/test_launch_batch_migration.py:test_launch_tables_roundtrip_without_row_loss`
* `controlplane/test_launch_store.py:test_item_key_is_owner_dispatch_candidate`
* `controlplane/test_launch_store.py:test_changed_item_digest_conflicts_before_gateway`
* `controlplane/test_launch_store.py:test_restart_replays_terminal_result_without_gateway`
* `controlplane/test_launch_store.py:test_restart_seals_interrupted_item_unknown_without_spawn`
* `controlplane/test_launch_replay.py:test_single_launch_uses_fixed_candidate_key_durably`
* `session/test_control_plane_actions_migration.py:test_candidate_scoped_launch_actions_coexist`

Proof beyond status codes: assert run IDs, gateway create count, audit row count, persisted
candidate keys, and byte stable replay JSON.

Gates:

```text
just check
just test-affected
```

### Slice 2: item authority and candidate chain

Deliverables:

* `LaunchTargetIntent`, `LaunchItemIntent`, `LaunchActorContext`, `LaunchCallerContext`
* `launch_caller.actor_context_for_principal` and `caller_context_for_worktree`
* `ControlPlaneLauncher.launch(caller, item, identity)`
* sibling Worktree authority comes from a `SpaceStore` validated per-item caller context
* candidate key in item audit and gateway request
* gateway idempotency derived from dispatch and candidate
* delivery ID persisted beside candidate before create
* single REST and MCP receipts remain identical

Exact interface changes:

```text
ControlPlaneLauncher.launch(LaunchCallerContext, LaunchItemIntent, LaunchInvocationIdentity)
GatewayCreateRunRequest.candidate_key
ControlPlaneAction.candidate_key
ControlPlaneAuditSink.find(actor, verb, dispatch_id, candidate_key)
DeliveryProofPort.subscribe(ControlPlaneReadScope, delivery_id)
actor_context_for_principal(principal, reads, space_store)
caller_context_for_worktree(actor, resolved_worktree)
```

Failing tests first:

* `controlplane/test_launch_service.py:test_candidate_identity_reaches_gateway_delivery_and_audit`
* `controlplane/test_launch_service.py:test_sibling_worktree_uses_validated_target_scope`
* `controlplane/test_launch_service.py:test_target_scope_cannot_escape_selected_worktree`
* `controlplane/test_launch_replay.py:test_two_candidates_under_one_dispatch_create_two_runs`
* `controlplane/test_launch_replay.py:test_candidate_replay_creates_no_run_and_no_audit`
* `api/v1/test_run_proxy_controlplane.py:test_create_projects_candidate_key`
* `packages/runtime/src/service/RunManager.idempotency.test.ts:two_candidate_keys_create_two_runs_and_each_replays`
* `api/v1/test_controlplane_action_skins.py:test_single_launch_receipt_survives_caller_context_refactor`

Gates:

```text
just check
just test-affected
```

### Slice 3: Canvas affinity through create, lifecycle, Activity, and persistence

Risk note: slice 3 is the heaviest cross-language slice and needs the closest interface and
migration review.

Deliverables:

* nullable Canvas field through every interface in section 4.7
* candidate and Canvas included in runtime create fingerprint
* lifecycle migration read and write support
* Activity and roster projection
* `CapturedRunRecord.canvasId`, storage version 8 migration, and Canvas scoped adoption
* `core.transport.fetchCanvases` for confirmed dangling affinity checks
* no `ManagedRunFilters` change

Exact interface changes:

```text
GatewayCreateRunRequest.canvas_id
CreateManagedRunInput.canvasId
RuntimeRunView.canvasId
PrepareCaptureInput.canvasId
PrepareCaptureRequest.canvas_id
CapturedRunRequest.canvas_id
RunLifecycleEventRow.canvas_id
ActivityWireRun.canvas_id
GatewayActivityRun.canvas_id
RosterItem.canvas_id
CapturedRunRecord.canvasId
```

Failing tests first:

* `api/v1/test_run_proxy_controlplane.py:test_create_projects_canvas_affinity`
* `packages/runtime/src/service/RunManager.idempotency.test.ts:same_key_changed_canvas_conflicts_before_capture`
* `api/v1/test_control_plane_capture_request.py:test_canvas_id_reaches_captured_run_request`
* `test_capture_rpc.py:test_started_and_exited_lifecycle_keep_canvas_id`
* `session/test_migration_roundtrip.py:test_canvas_affinity_column_roundtrip_preserves_legacy_rows`
* `packages/activity/src/adapters/postgresRecords.integration.test.ts:activity_snapshot_projects_canvas_id`
* `api/v1/test_controlplane_skins.py:test_roster_projects_canvas_id`
* `www/packages/canvas/src/model/capturedRunStore.test.ts:migration_v8_preserves_valid_siblings_and_strips_only_bad_affinity`
* `www/packages/canvas/src/model/capturedRunAdoption.test.ts:adopts_only_matching_canvas_affinity`
* `www/packages/canvas/src/workbench/SessionCanvasRoute.test.ts:rehydrate_skips_dangling_canvas_without_store_wipe`
* `www/packages/canvas/src/workbench/SessionCanvasRoute.test.ts:canvas_inventory_failure_preserves_every_binding`

Data loss gate: fixture one valid v7 run, one malformed v8 run, one dangling Canvas ID, two
valid pane refs, and a layout. Verify only invalid records are skipped and the layout bytes
remain present.

Gates:

```text
just check
just test-affected
```

### Slice 4: batch semantic core

Deliverables:

* profile, prompt, placement, outcome, and result models from section 4
* `launch_batch_service.LaunchBatchService`
* full Space, Worktree, and Canvas preflight before fanout
* deterministic candidate minting before fanout
* bounded parallel item execution with ordered outcomes
* durable ordered batch replay
* explicit null snapshot and live Worktree receipt fields
* thin `ControlPlaneService.launch_batch` delegation, with `service.py` kept below 700 lines

Failing tests first:

* `controlplane/test_launch_batch_models.py:test_profile_has_no_placement_or_authority_fields`
* `controlplane/test_launch_batch_models.py:test_prompt_inherit_interactive_and_text_are_distinct`
* `controlplane/test_launch_batch_models.py:test_worktree_modes_reject_ambiguous_refs`
* `controlplane/test_launch_batch.py:test_preflight_validates_all_resources_before_any_start`
* `controlplane/test_launch_batch.py:test_batch_mints_all_keys_before_fanout`
* `controlplane/test_launch_batch.py:test_batch_fans_every_candidate_through_single_authority`
* `controlplane/test_launch_batch.py:test_one_failure_does_not_cancel_siblings`
* `controlplane/test_launch_batch.py:test_completion_order_does_not_change_result_order`
* `controlplane/test_launch_batch.py:test_batch_replay_is_byte_stable_and_creates_nothing`
* `controlplane/test_launch_batch.py:test_workspace_snapshot_is_explicitly_null_live_worktree`

Gates:

```text
just check
just test-affected
```

### Slice 5: agent REST and MCP skins

Deliverables:

* `POST /v1/controlplane/launch-batch`
* `_McpControlPlaneAdapter.launch_batch`
* `launch_batch` MCP tool registration
* shared request and result schemas
* director enforcement before `LaunchActorContext` creation
* no adapter fanout

Exact interfaces:

```text
controlplane_routes.launch_batch(request: LaunchBatchRequest, principal, service)
_McpControlPlaneAdapter.launch_batch(scope_bearer, request: LaunchBatchRequest)
ControlPlaneService.launch_batch(caller: LaunchActorContext, request)
```

Failing tests first:

* `api/v1/test_controlplane_action_skins.py:test_launch_batch_rest_and_mcp_are_identical`
* `api/v1/test_controlplane_action_skins.py:test_launch_batch_requires_director`
* `api/v1/test_controlplane_mcp_inventory.py:test_launch_batch_schema_has_no_candidate_key_input`
* `api/v1/test_controlplane_mcp_inventory.py:test_launch_batch_result_has_no_top_level_schema_combinator`
* `api/v1/test_controlplane_skins.py:test_batch_malformed_profile_has_shared_failure_envelope`

Gates:

```text
just check
just test-affected
```

### Slice 6: trusted browser adapter and one batch transport

Deliverables:

* origin checked operator batch route in a focused route module
* server resolution of owner, Space, Worktrees, workspace root, and actor label
* rejection of browser owner, workspace identity, actor, candidate key, and synthetic Canvas
  cache IDs
* `core.transport.launchCapturedRunBatch`
* one request from Canvas, with no calls to `createCapturedRunView`

The operator actor is the stable audit label `canvas-operator`. It grants no run bearer and
does not fabricate `ControlPlanePrincipal`. `require_http_origin` authenticates the local
browser boundary. `SpaceStore` supplies launch scope.

Failing tests first:

* `api/v1/test_operator_launch_batch.py:test_same_origin_operator_enters_shared_batch_service`
* `api/v1/test_operator_launch_batch.py:test_cross_origin_is_rejected_before_service`
* `api/v1/test_operator_launch_batch.py:test_browser_authority_fields_are_rejected`
* `api/v1/test_operator_launch_batch.py:test_synthetic_canvas_cache_key_is_rejected`
* `www/packages/core/src/transport.test.ts:launchCapturedRunBatch_posts_once_and_decodes_shared_receipt`

Gates:

```text
just check
just test-affected
```

### Slice 7: Cmd K batch composer and Activity placement

Deliverables:

* candidate selection through existing `run-stay` interactions
* one `Launch N` commit row
* shared prompt plus item prompt mode editing
* Worktree mode and item Worktree selection
* invocation time Canvas placement, never stored in the profile definition
* one batch command through `useCanvasCommandHandler`
* one visible result row per candidate
* successful runs adopted by matching Canvas Activity, failed siblings remain visible
* no direct `/v1/runs` loop

For an active synthetic Canvas cache key, the composer exposes placement as `Unplaced` and
does not submit that key. A real server Canvas UUID is required for durable affinity. The
parallel Canvas identity track may later replace synthetic defaults with durable Canvas
records.

Failing tests first:

* `www/packages/canvas/src/launcher/templateRows.test.ts:batch_selection_uses_run_stay_and_one_commit`
* `www/packages/canvas/src/workbench/CanvasCommandDispatcher.test.ts:batch_command_posts_once`
* `www/packages/canvas/src/workbench/CanvasCommandDispatcher.test.ts:batch_never_calls_createCapturedRunView`
* `www/packages/canvas/src/workbench/CanvasCommandDispatcher.test.ts:placement_is_invocation_only`
* `www/packages/canvas/src/workbench/SessionCanvasRoute.test.ts:activity_places_success_only_in_matching_canvas`
* `www/packages/canvas/src/workbench/SessionCanvasRoute.test.ts:fresh_client_reconstructs_affinity_from_snapshot`
* `www/packages/canvas/src/launcher/LauncherPalette.test.ts:failed_candidate_remains_visible_beside_successes`

Gates:

```text
just check
just test-affected
```

## 9. Cross slice acceptance proof

The feature is not complete until all of these are demonstrated together:

1. Launch three candidates under one dispatch. The response contains three distinct
   candidate keys and three distinct run IDs.
2. Replay the exact request before restart. It performs zero new gateway creates and zero
   new audits.
3. Restart the API and replay. It returns the same ordered receipt and creates nothing.
4. Interrupt one accepted item at process loss. Replay returns terminal unknown and creates
   nothing. A new dispatch can launch it.
5. Change one item under the same dispatch and key. It fails before gateway create.
6. Place candidates into two real Canvas UUIDs. Two browser clients reconstruct only their
   matching runs from Activity snapshots.
7. Delete one Canvas, reload another, and prove the dangling record is skipped without
   wiping sibling runs or pane layout.
8. Launch with a startup prompt. Candidate key, gateway key, delivery ID, and audit row are
   correlated in durable records without storing prompt text in keys or digests.
9. Launch without a prompt. The run remains interactive and has no delivery ID.
10. Inspect each run directory and prove each candidate owns a distinct operational HOME.
11. Capture the browser network trace and prove one batch POST and zero `/v1/runs` candidate
    POSTs.

## 10. Open risks

### Snapshot and evaluation

Live Worktrees can drift during a batch and shared Worktrees permit candidates to interfere.
The receipt is honest about this. No evaluation label, score, or fairness claim may build on
foundation v1.

### Existing launch contract debt

Durable candidate claims do not by themselves implement the complete frozen resolution
context described by `LAUNCH-CONTRACT.md`. Catalog pinning and immutable launch actuation
remain separate contract work. The item store must be shaped so those fields can move from
JSON into typed durable records without changing its identity key.

### Gateway process lifetime

`RunManager` idempotency and runs are process resident. Durable Python claims prevent a
second spawn after API restart, but cannot resurrect a run after gateway restart. Replayed
receipts remain creation facts. Current attachability comes from `getRun` and Activity.

### Synthetic default Canvas identity

The current client can key a default Canvas as `space:<space_id>` without a matching server
`Canvas` row. v1 refuses to forge affinity from that key. Those launches are unplaced until
the Canvas identity track gives every default view a real `CanvasId`.

### Activity timing

The batch receipt can arrive before the lifecycle event reaches Activity. The composer must
show receipt state immediately and let the existing bounded reconciler create panes when the
Activity fact arrives. It must not add a second direct adoption authority to hide latency.

### Audit migration

The uniqueness migration touches a live audit table. Migration tests must cover null and
candidate values, rollback, duplicate prevention, and concurrent writers. The migration
must preserve every existing action row.

### Local persistence

Captured run bindings are global localStorage while pane caches are per Canvas. Affinity
filtering must never treat a record for another Canvas as stale. A storage version error must
degrade per record. Returning an empty state is data loss.

### File size thresholds

`controlplane/service.py` is 666 lines and `RunManager.ts` is 664 lines at this baseline.
Keep batch behavior in new focused modules. If required wiring would push either file over
700 lines, extract the existing create or launch composition first, then add the field.

## 11. Explicit non-goals

* pre-migration replay is a flag-day boundary: runs launched before
  `0030_launch_batch_v1` and the accompanying captured-run storage v8 rollout have no
  durable candidate identity and are not replayable
* saved profile CRUD
* profile scheduling
* real workspace snapshot sealing or materialization
* evaluation rubric, judge, score, or comparison UI
* server pane membership or layout ownership
* Canvas hierarchy or drill navigation
* `ManagedRunFilters.canvasId`
* stop by Canvas
* batch logic in Node runtime
* browser candidate fanout
* backward compatibility adapters for rejected authority fields
