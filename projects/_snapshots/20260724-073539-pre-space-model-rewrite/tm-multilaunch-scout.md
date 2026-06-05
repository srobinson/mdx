# `launch_batch` scout and slice plan

Date: 2026-07-20

Checkout: `/Users/alphab/Dev/LLM/DEV/helioy/tm-multilaunch`

Branch and head: `feat/multi-launch` at `8c51797e01ef`

Governing authority: `LAUNCH-CONTRACT.md`

## Verdict

The item authority is reusable. `ControlPlaneLauncher.launch` already owns director policy, request normalization, item replay, scoped workdir preparation, gateway create, prompt proof, provider rejection receipts, and audit persistence.

A batch cannot call that method N times under one dispatch yet. The Python launch ledger keys by `(owner, dispatch_id)`, and the Node runtime keys create idempotency by `(owner, idempotency_key)` where the control plane currently sends `dispatch_id`. Equal candidates would collapse onto one run. Different candidates would produce an idempotency conflict.

The client paths also diverge above the gateway. MCP enters `ControlPlaneService.launch` and `ControlPlaneLauncher.launch`. The Cmd K palette posts directly to `/v1/runs` through the canvas run store. It joins the MCP path only at `RunManager`, below control plane normalization, ledger, audit, and receipts.

There is no code implementation of `launch_batch`, `candidate_key`, or `WorkspaceSnapshot`. These are contract and plan concepts only.

## Exact single launch signature

`api/src/transport_matters/controlplane/launch_service.py::ControlPlaneLauncher.launch`

```python
async def launch(
    self,
    principal: ControlPlanePrincipal,
    workdir: str,
    harness: LaunchHarness,
    *,
    model: str | None = None,
    effort: str | None = None,
    agent: str | None = None,
    name: str | None = None,
    first_prompt: str | None = None,
    grant: ControlPlaneGrantOption = ControlPlaneGrantOption.NONE,
    dispatch_id: UUID,
) -> LaunchResult
```

`api/src/transport_matters/controlplane/service.py::ControlPlaneService.launch` is the public application facade. It mints `dispatch_id` when omitted, then delegates to the launcher.

## Reuse map

| Capability | Existing file and symbol | Batch use |
| --- | --- | --- |
| Public item request and receipt | `api/src/transport_matters/controlplane/run_models.py::LaunchRequest`, `LaunchResult` | Reuse one request per candidate and embed the existing receipt in each candidate outcome. |
| Application facade and dispatch minting | `api/src/transport_matters/controlplane/service.py::ControlPlaneService.launch`, `_dispatch_id_factory`, `_launcher` | Add a thin `launch_batch` delegation. Keep orchestration out of this 666 line file. |
| Single item authority | `api/src/transport_matters/controlplane/launch_service.py::ControlPlaneLauncher.launch` | Every candidate must call this method after candidate identity is added. |
| Canonical item intent | `api/src/transport_matters/controlplane/launch_service.py::_NormalizedLaunchRequest`, `_normalize_launch_request`, `_intent_fingerprint` | Reuse unchanged for each candidate. Batch identity must never replace item identity. |
| Item single flight and replay | `api/src/transport_matters/controlplane/launch_ledger.py::LaunchLedger.claim`, `LaunchLedgerEntry` | Extend the key to `(owner, dispatch_id, candidate_key)`. Single launch uses one fixed internal key. |
| Failure isolation precedent | `api/src/transport_matters/controlplane/service.py::ControlPlaneService.close`, `_close_target` | Reuse the per target receipt pattern and concurrent gather shape. Batch must catch candidate failures into outcomes. |
| Gateway request projection | `api/src/transport_matters/controlplane/run_models.py::GatewayCreateRunRequest`, `api/src/transport_matters/controlplane/launch_service.py::ControlPlaneLauncher._execute` | Supply a candidate scoped gateway idempotency value. Preserve every other item field. |
| Python to gateway adapter | `api/src/transport_matters/api/v1/run_proxy.py::RunRouteProxy.create_run` | Reuse unchanged once the request carries a unique idempotency value per candidate. |
| Runtime create idempotency | `packages/runtime/src/service/RunManager.ts::RunManager.createWithDisposition`, `packages/runtime/src/service/runManagerSupport.ts::createRunFingerprint` | Reuse unchanged. Its current composite key proves candidate identity must reach this boundary. |
| Model, effort, and connection authority | `api/src/transport_matters/api/v1/capture_rpc_routes.py::_resolve_launch_target`, `api/src/transport_matters/harnesses/launch_target.py::resolve_launch_target_advisory`, `api/src/transport_matters/harnesses/resolver_snapshots.py::resolver_snapshots_for_harness` | Reuse per candidate through the existing item path. No batch resolver is needed. |
| REST launch skin | `api/src/transport_matters/api/v1/controlplane_routes.py::launch` | Add one thin `/launch-batch` sibling that delegates to the same application service. |
| MCP launch skin | `api/src/transport_matters/api/v1/controlplane_mcp.py::_McpControlPlaneAdapter.launch`, `create_control_plane_mcp` local tool `launch` | Add `LaunchBatchToolResult`, adapter delegation, and registered `launch_batch` tool. |
| Palette command entry | `www/packages/canvas/src/launcher/templateRows.ts::spawnCommand`, `www/packages/canvas/src/launcher/commandTypes.ts::LauncherCommand`, `www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts::useCanvasCommandHandler` | Reuse the command grammar and dispatcher. Add batch candidate selection and one commit command. |
| Palette run create path | `www/packages/canvas/src/model/capturedRunStore.ts::CapturedRunState.ensureRun`, `www/packages/core/src/transport.ts::createCapturedRunView` | Current direct single spawn path. Do not put a second batch loop here. Add one batch transport call to the control plane adapter. |
| Service run adoption | `www/packages/canvas/src/model/capturedRunAdoption.ts::CapturedRunAdoptionReconciler`, `www/packages/canvas/src/model/canvasActions.ts::adoptCapturedRun` | Reuse to attach successful service launched runs to panes. Avoid a second adoption mechanism. |

Reuse count: 15 seams.

## Missing substrate and searches

| Capability | Finding | Search evidence |
| --- | --- | --- |
| Batch scaffolding | None found in runtime code. | `rg 'launch_batch|LaunchBatch|launchBatch'` found only `LAUNCH-CONTRACT.md`, `NOW.md`, and `RUNTIME-SURFACING-PLAN.md`. `rg 'LaunchBatchRequest|LaunchBatchResult|batch launch|batch_launch' api www packages desktop` returned no matches. |
| Candidate key minting | None found in launch code. | `rg 'candidate_key|candidateKey'` found only `LAUNCH-CONTRACT.md` and `NOW.md`. Activity's unrelated wire candidate vocabulary is outside launch identity. |
| Sealed workspace snapshot | None found. | `rg 'WorkspaceSnapshot|workspace_snapshot|sealed workspace|seal.*workspace'` found only contract and plan references. The harness certification snapshot code is unrelated executor evidence. |

Missing capability count: 3.

## Current client paths

### MCP

`create_control_plane_mcp` tool `launch`
→ `_McpControlPlaneAdapter.launch`
→ `ControlPlaneService.launch`
→ `ControlPlaneLauncher.launch`
→ `RunRouteProxy.create_run`
→ `createRuntimeRouter`
→ `RunManager.createWithDisposition`

### Cmd K palette

`templateRows.spawnCommand`
→ `useCanvasCommandHandler`
→ `CanvasStoreActions.addCapturedRun`
→ `CapturedRunState.ensureRun`
→ `createCapturedRunView`
→ `POST /v1/runs`
→ `create_run_proxy_mount`
→ `createRuntimeRouter`
→ `RunManager.createWithDisposition`

The paths converge at the runtime gateway. The batch work must converge them at one batch application service.

## PR sized slice plan

### PR 1: batch semantic core

Scope:

1. Add `LaunchBatchRequest`, `LaunchBatchOutcome`, and `LaunchBatchResult` beside the existing item models in `run_models.py`. Each candidate remains a `LaunchRequest`. The outer request owns one optional dispatch id. Candidate dispatch ids are rejected.
2. Add a focused `launch_batch_service.py` so `ControlPlaneService` remains below its 700 line limit. The batch service receives the existing `ControlPlaneLauncher` as its item port.
3. Mint deterministic internal candidate UUIDs from the server owned batch dispatch and candidate ordinal. Clients never submit them. Repeated targets at different ordinals receive different keys. Replay derives the same keys.
4. Extend `LaunchLedger.claim` and `release_preparation_failure` to key by `(owner, dispatch_id, candidate_key)`. Give single launch one named fixed internal key.
5. Thread `candidate_key` into `ControlPlaneLauncher.launch`. Use a candidate scoped UUID for `GatewayCreateRunRequest.idempotency_key` during batch. Keep the current dispatch value for single launch.
6. Fan candidates with a server owned concurrency bound. Convert `ControlPlaneError` per candidate into a structured failure outcome. Preserve provider rejection as a normal `LaunchResult` whose `first_prompt.status` is `failed`.
7. Return outcomes in request order regardless of completion order.

KISS boundary: no resolver, capture, launch profile, or RunManager batch implementation. Those layers continue to see one launch at a time.

### PR 2: agent facing skins

Scope:

1. Add `POST /v1/controlplane/launch-batch` beside `controlplane_routes.launch`.
2. Add `launch_batch` to `_McpControlPlaneAdapter` and `create_control_plane_mcp`.
3. Keep both adapters as argument shapers only. All fanout stays in the batch service.
4. Extend the existing shared skin and MCP schema tests.

### PR 3: trusted Canvas adapter and browser transport

The palette has no agent bearer and currently bypasses `ControlPlaneService`. Resolve this trust boundary explicitly.

Scope:

1. Add an origin checked operator adapter that constructs a typed launch caller context from server resolved workspace facts. Do not forge an agent grant or expose a run bearer to the browser.
2. Refactor the launcher input from agent specific principal facts to one typed caller context only where required. The MCP facade still enforces `require_director` before constructing that context.
3. Delegate the operator batch endpoint to the same batch application service used by MCP.
4. Add one `launchCapturedRunBatch` transport in `@tm/core`. It performs one request and returns the shared batch receipt.
5. Reuse `CapturedRunAdoptionReconciler` for successful service runs.

Security gate: same origin validation establishes browser origin, while server resolved workspace and owner establish launch scope. Browser supplied owner, workspace identity, actor identity, and candidate keys are rejected.

### PR 4: Cmd K batch composer

Scope:

1. Reuse the existing Agents scope rows and launch catalog data.
2. Add local candidate selection with `run-stay` interactions and one `Launch N` commit row.
3. Dispatch one batch command through `useCanvasCommandHandler` and the new core transport.
4. Render one result row per candidate. A failed candidate remains visible while successful siblings appear through service run adoption.
5. Keep `CapturedRunState.ensureRun` for legacy single palette spawn until single palette convergence is scheduled. Never call it N times to simulate batch.

Foundation plan count: 4 PRs.

## Failing test design

All named tests fail before the corresponding slice because the models, service method, tool, transport, and palette command do not exist.

### 1. N candidates call the single authority N times

New `api/src/transport_matters/controlplane/test_launch_batch.py::test_batch_fans_every_candidate_through_single_launch_authority`:

- Supply three `LaunchRequest` candidates.
- Inject a recording single launch port.
- Assert three calls to `ControlPlaneLauncher.launch` semantics.
- Assert one shared dispatch id, three distinct server candidate keys, preserved request order, and three receipts.
- Assert no direct call from the batch service to gateway, resolver, or capture.

### 2. Per item isolation, including provider rejection

New `test_launch_batch.py::test_batch_retains_provider_rejection_and_launches_siblings`:

- Candidate A returns a submitted receipt.
- Candidate B returns `LaunchResult` with `first_prompt.status == "failed"` and reason `model_rejected`.
- Candidate C returns a submitted receipt.
- Assert all three outcomes are present and B does not cancel A or C.

New `test_launch_batch.py::test_batch_captures_one_control_plane_failure_without_cancelling_siblings`:

- Make one item raise `ControlPlaneError` from target or gateway preparation.
- Assert one structured failure and successful receipts for the other candidates.

### 3. Idempotency uses owner, dispatch, and candidate

Extend `api/src/transport_matters/controlplane/test_launch_replay.py` with `test_batch_replay_keys_items_by_owner_dispatch_and_candidate`:

- Launch two candidates under one dispatch.
- Assert two gateway creates and two distinct gateway idempotency values.
- Replay the identical batch.
- Assert byte identical candidate outcomes, zero extra creates, and zero extra audits.
- Reuse one derived candidate key with changed item intent and assert `dispatch_conflict` for that item.
- Repeat the same dispatch under another owner and assert independent runs.

Extend `packages/runtime/src/service/RunManager.idempotency.test.ts` with a cross component fixture proving two candidate scoped keys create two runs while replaying either key creates none.

### 4. REST and MCP reach the same service

Extend `api/src/transport_matters/api/v1/test_controlplane_action_skins.py` with `test_launch_batch_receipts_are_identical_across_agent_skins`:

- Call REST and MCP with the same payload.
- Assert identical JSON receipts.
- Assert `FakeService.launch_batch` received the same typed request from both skins.

Extend `test_mcp_tool_schemas_are_the_agent_contract`:

- Assert `launch_batch` exists.
- Assert its output schema remains a combinator free top level object.
- Assert candidate keys appear only in output.

### 5. Cmd K reaches the same batch service

Add a core transport test and a Canvas workbench test:

- Select two candidate rows and commit once.
- Assert one operator batch request.
- Assert zero calls to `createCapturedRunView` for those candidates.
- Assert one failed outcome remains visible.
- Assert successful service runs are adopted exactly once through `CapturedRunAdoptionReconciler`.

Required test group count: 5. Snapshot adds one conditional group below.

## Biggest blast radius risk

Candidate identity can be lost between the Python ledger and Node runtime.

Current keys:

- Python: `LaunchLedger._entries[(owner, dispatch_id)]`
- Node: `RunManager.pendingCreates[(owner, idempotency_key)]`
- Current control plane projection: `idempotency_key = dispatch_id`

A naive gather around `ControlPlaneLauncher.launch` therefore produces one of two wrong outcomes:

1. Equal candidates return the same run.
2. Different candidates conflict before the second run starts.

Client minted per candidate dispatch ids would break the governing replay contract. Candidate identity must be server owned and must cross both keys before any batch fanout ships. Tests must assert run ids, create counts, and audit counts, since a superficially successful N item receipt could still contain one repeated run.

The second risk is trust duplication. Adding a new `/v1/runs/batch` loop for the palette would preserve the current bypass and create a second batch semantic. The operator adapter must enter the shared batch service.

## Open decision for Stuart

The contract says `launch_batch` adds one sealed workspace snapshot and optional evaluation artifacts. The current repository has none of the snapshot or evaluation substrate.

### Option A: contract complete batch v1

Build one real `WorkspaceSnapshot`, seal it once, and give every candidate an isolated writable workspace derived from it. Defer rubric, judge, labels, and comparative views, but include the actual snapshot identity and isolation guarantee.

This adds a fifth PR with snapshot records, Git and non Git sealing, isolated workspace creation, cleanup, failure semantics, and one snapshot per batch tests. It moves v1 into the S4 execution layer described by `RUNTIME-SURFACING-PLAN.md`.

Conditional test: `test_batch_seals_one_snapshot_and_threads_it_to_every_candidate` asserts one sealer call, one snapshot id, isolated candidate roots, and zero starts when sealing fails.

### Option B: thin batch verb foundation

Ship candidate identity, item fanout, isolation of failures, receipts, MCP, and palette access over the current workdir. Defer workspace snapshots and all evaluation artifacts.

This keeps the batch verb small. It requires a narrow contract clarification before merge because the current `LAUNCH-CONTRACT.md` sentence assigns a snapshot to `launch_batch` without qualification.

### Avoid the middle state

A snapshot id or digest without isolated candidate workspaces creates a false trust signal. Either provide a real shared starting state or state that the foundation runs against the live workdir.

Decision requested: choose contract complete snapshot isolation for v1, or authorize the thin foundation plus the contract clarification. Evaluation artifacts above snapshot identity can remain deferred in both cases.

## Verification evidence

- `LAUNCH-CONTRACT.md` was read before code mapping.
- Branch and head verified as `feat/multi-launch` at `8c51797e01ef`.
- Tracked tree was clean before the scout and after targeted checks.
- Targeted Python proof passed: 2 tests covering item replay and identical REST or MCP single launch receipts.
- Targeted browser proof passed under the shell Vitest project: 34 tests covering Cmd K spawn and `CapturedRunStore` idempotency.
- An initial direct Vitest run omitted the shell project configuration and failed on missing `localStorage`. The correctly configured rerun passed. This was a runner invocation issue, not a product failure.

## Counts and reuse verdict

- Reuse seams: 15
- Missing batch primitives: 3
- Foundation PRs: 4
- Required failing test groups: 5
- Conditional snapshot PR and test group: 1

Key reuse verdict: strong item reuse, unsafe direct fanout until server candidate identity reaches both the Python ledger and Node gateway idempotency key; the palette also needs a trusted adapter into the shared service.
