# `launch_batch` scout

## Scope and baseline

- Authority: `LAUNCH-CONTRACT.md`, then the current `NOW.md` slice.
- Source: detached `e1ca17d6c5544ff9ce70cca1d0bd4c203878e642`.
- Repository baseline: pristine before the scout.
- Mode: read only. No repository edits, database writes, captured runs, keychain access, channel home access, commits, or pull request activity.
- Count: 6 reuse hits and 7 implementation gaps.

## Reuse map

### 1. Request construction

Reuse hit:

- `api/src/transport_matters/controlplane/run_models.py::LaunchRequest` is the existing single launch wire model. A batch candidate should contain this request rather than restating its fields.
- `api/src/transport_matters/harnesses/resolver.py::LaunchOption` is the exact enumerable connection, route, model, and effort tuple.
- `api/src/transport_matters/harnesses/inventory.py::HarnessInventoryResponse` carries exact installed versions, active compatibility facts, observations, and `LaunchOption` tuples for Claude and Codex.
- `api/src/transport_matters/api/v1/controlplane_mcp.py::_McpControlPlaneAdapter._harness_inventory` and `api/src/transport_matters/api/v1/harness_launch_view.py::project_harnesses_view` expose the existing catalog authority. The full view retains the exact tuple detail.

Gap:

- `LaunchRequest` implements the current single launch subset. It lacks the contract fields `spec_version`, `connection`, `allow_unverified_target`, and `brief_id`, and it requires `harness` even when `agent` should be sufficient.
- No batch request or candidate wrapper exists.

Searches:

```text
rg -n "launch_batch|LaunchBatch|candidate_key" api packages www
rg -n "class LaunchRequest|class LaunchOption|class HarnessInventoryResponse" api/src
```

### 2. Dispatch identity minting

Reuse hit:

- `api/src/transport_matters/controlplane/service.py::ControlPlaneService.launch` owns the existing server mint when a caller omits `dispatch_id`.
- `api/src/transport_matters/controlplane/service.py::ControlPlaneService.close` demonstrates one server minted dispatch shared by a fan out.

Gap:

- Calling `ControlPlaneService.launch` N times with omitted identities mints N dispatches. A batch method must mint once and pass the shared dispatch plus one internal candidate key into the same launch authority.

Search:

```text
rg -n "dispatch_id_factory|dispatch_id =" api/src/transport_matters/controlplane
```

### 3. Ledger and replay

Reuse hit:

- `api/src/transport_matters/controlplane/launch_ledger.py::LaunchLedger.claim` owns rate limiting, intent conflict detection, single flight, replay, retained terminal outcomes, and audit retry.
- `api/src/transport_matters/controlplane/launch_service.py::ControlPlaneLauncher.launch` is the only service launch caller of that ledger.

Gap:

- `LaunchLedger._entries`, `LaunchLedger.claim`, and `LaunchLedger.release_preparation_failure` key by `(owner, dispatch_id)`.
- The ledger is process resident and stores neither `ResolutionContext` nor `FrozenLaunchSpec`.
- The contract requires durable `(owner, dispatch_id, candidate_key)` identity. Single launch must use a fixed internal candidate key.
- The durable transaction boundary and migration form remain open decisions in `LAUNCH-CONTRACT.md`. No durable launch ledger owner exists in current code.

Searches:

```text
rg -n "class LaunchLedger|_entries|release_preparation_failure" api/src
rg -n "ResolutionContext|FrozenLaunchSpec|workspace_snapshot_id" api packages www
rg -n "launch_ledger|requested_intent_digest" api/migrations api/src
```

### 4. Per item failure isolation

Reuse hit:

- `api/src/transport_matters/controlplane/service.py::ControlPlaneService.close` performs a concurrent fan out after one shared preflight.
- `api/src/transport_matters/controlplane/service.py::ControlPlaneService._close_target` converts each target failure into a receipt so one failure does not suppress siblings.
- `api/src/transport_matters/controlplane/test_launch_manage.py::test_close_fans_out_with_per_run_receipts` proves that pattern.

Gap:

- `ControlPlaneLauncher.launch` returns `LaunchResult` or raises `ControlPlaneError`.
- No launch candidate adapter converts a terminal candidate error into a batch item receipt.
- A direct `asyncio.gather` over current launch calls would raise on the first observed exception and fail to return one outcome per request.

Search:

```text
rg -n "_close_target|test_close_fans_out_with_per_run_receipts|gather" api/src/transport_matters/controlplane
rg -n "LaunchFailure|LaunchOutcome|BatchResult" api packages www
```

### 5. Compatibility advisory detail

Reuse hit:

- `api/src/transport_matters/harnesses/resolver_snapshots.py::resolver_snapshots_for_harness` assembles one explicit pinned resolver input.
- `api/src/transport_matters/harnesses/resolver.py::resolve_target` returns `ResolvedTarget`, warnings, and compatibility advisories.
- `api/src/transport_matters/harnesses/launch_target.py::resolve_launch_target_advisory` applies the current advisory launch posture.
- `api/src/transport_matters/api/v1/capture_rpc_routes.py::_resolve_launch_target` already serializes launch advisories into captured launch fields.

Gap:

- The control plane launch path does not resolve from a pinned batch context.
- `GatewayCreateRunResult` does not return resolved target or advisory facts.
- `LaunchResult` returns raw requested model and effort, but omits `spec_version`, `resolved_target`, `compatibility_release_id`, and `warnings`.
- Capture resolves each launch independently after the gateway call. That timing cannot prove every candidate used the enumerated batch catalog snapshot.

Search:

```text
rg -n "resolve_launch_target_advisory|compatibility_advisories|launch_advisories" api/src
rg -n "resolved_target|compatibility_release_id|warnings" api/src/transport_matters/controlplane
```

### 6. Result aggregation

Reuse hit:

- `api/src/transport_matters/controlplane/run_models.py::CloseResult` is the existing shared dispatch plus ordered per item receipts shape.
- `api/src/transport_matters/controlplane/prompt_models.py::PromptResult` is a second ordered fan out result.
- `api/src/transport_matters/controlplane/service.py::ControlPlaneService.close` preserves request order after deduplication and returns all receipts.

Gap:

- Neither existing receipt can represent a launch that fails before a `run_id` exists.
- A minimal batch result needs the shared dispatch and one candidate keyed terminal outcome containing either the common `LaunchResult` or a stable launch failure code and details.
- Result order and candidate key uniqueness have no current validation owner.
- Batch must retain every unique candidate key. Repeated target tuples remain separate requests.

Search:

```text
rg -n "class CloseResult|class PromptResult|class LaunchResult" api/src
rg -n "candidate.*receipt|launch.*outcome|batch.*result" api packages www
```

## Gap register

The 7 gaps counted in this scout are:

1. Batch envelope, REST verb, MCP adapter method, and MCP tool.
2. Candidate key propagation through dispatch and ledger ownership.
3. Durable `ResolutionContext` and `FrozenLaunchSpec` persistence.
4. One sealed workspace and resolver context per batch.
5. Frozen specification digest identity at the gateway and candidate safe audit identity.
6. Per candidate failure conversion and ordered aggregation.
7. Resolved target, compatibility release, and advisory result propagation.

## Contract delta

### Already specified

`LAUNCH-CONTRACT.md` already fixes these semantics:

- Every candidate uses `LaunchRequest`.
- Batch adds an internal candidate key and one sealed workspace snapshot.
- Batch execution uses the single launch semantic.
- The ledger key is `(owner, dispatch_id, candidate_key)`, with a fixed candidate key for single launch.
- The first accepted request pins `ResolutionContext`.
- Resolution freezes `FrozenLaunchSpec`.
- Gateway idempotency uses the frozen specification digest.
- Replays cannot consult current catalogs, defaults, observations, or workspace identity.
- Every client receives the common `LaunchResult`, including resolved target, compatibility release, warnings, and prompt receipt.

### Missing in code

- Public batch request, result, REST verb, MCP adapter method, and MCP tool.
- Candidate key validation and propagation.
- One batch dispatch mint.
- One sealed workspace snapshot shared across candidates.
- Durable candidate scoped ledger storage.
- `ResolutionContext` and `FrozenLaunchSpec`.
- Control plane target resolution over the catalog snapshot.
- Frozen specification digest at the gateway idempotency seam.
- Candidate safe launch audit identity.
- Per candidate error receipts.
- Resolved target and advisory result fields.

The batch wrapper can stay small only after the single launch authority accepts the contract inputs above.

## Seam audit

| Seam | Current owner | Multi item status | Evidence |
| --- | --- | --- | --- |
| Control plane verb | `api/src/transport_matters/controlplane/service.py::ControlPlaneService.launch` | Assumes one | Mints one dispatch when omitted and calls the launcher once. `ControlPlaneService.close` supplies the reusable fan out structure. |
| REST skin | `api/src/transport_matters/api/v1/controlplane_routes.py::launch` | Assumes one | Accepts one `LaunchRequest` and returns one `LaunchResult`. |
| MCP tool | `api/src/transport_matters/api/v1/controlplane_mcp.py::_McpControlPlaneAdapter.launch`, `api/src/transport_matters/api/v1/controlplane_mcp.py::launch` | Assumes one | Both are branch free single request delegators. The structure tests require public entrypoints to remain delegators. |
| Single launch | `api/src/transport_matters/controlplane/launch_service.py::ControlPlaneLauncher.launch` | Safe for distinct dispatches, unsafe for one shared batch dispatch | Per call state is local, but ledger, gateway create identity, and audit identity use dispatch alone. |
| Workspace preparation | `api/src/transport_matters/controlplane/launch_service.py::ControlPlaneLauncher._prepare` | Assumes one | Reads actor session and gateway acting context on every invocation. |
| Ledger | `api/src/transport_matters/controlplane/launch_ledger.py::LaunchLedger.claim` | Concurrency safe for its current key, candidate unaware | One `asyncio.Lock` protects process state. Key shape is `(owner, dispatch_id)`. |
| Gateway create | `api/src/transport_matters/api/v1/controlplane_gateway_runs.py::create_run`, `packages/runtime/src/service/RunManager.ts::RunManager.createWithDisposition` | Multi item safe only with distinct idempotency keys | Runtime keys by `(owner, idempotencyKey)` and rejects fingerprint drift. Python sends `dispatch_id` as the key. |
| Audit | `api/src/transport_matters/controlplane/audit.py::ControlPlaneAuditWriter.write`, `api/src/transport_matters/controlplane/action_builders.py::launch_action` | Assumes one launch per dispatch | The database constraint is unique on `(actor, verb, dispatch_id)`. Candidate launches sharing a dispatch would collapse to one audit row. |

## Evidence answers

### Hidden state under N invocations

Ports:

- `api/src/transport_matters/cli/launch_runtime.py::resolve_launch_ports` allocates a fresh pair per capture preparation.
- `api/src/transport_matters/cli/ports.py::allocate_port_pair` does not reserve ports across concurrent callers. The documented bind race is handled by the existing retry path in `api/src/transport_matters/captured/run.py::prepare_captured_run`.
- No batch port allocator is needed. Resource exhaustion remains a normal per candidate failure.

Locks:

- `api/src/transport_matters/cli/launch_runtime.py::new_run_id` mints a fresh run ID.
- `api/src/transport_matters/captured/run.py::prepare_captured_run` acquires `WorkspaceLock` under that run's storage root.
- Locks are per run, despite the class name. N candidates do not contend on one workspace lock.

Temporary and operational paths:

- `api/src/transport_matters/captured/context.py::_prepare_home_and_grant` creates runtime home under the per run storage directory.
- `api/src/transport_matters/captured/models.py::CapturedRunLease.close` releases the proxy, manifest, lock, and resource stack.
- `api/src/transport_matters/capture_rpc.py::CaptureLeaseRegistry.prepare_capture` prepares in worker threads, then registers each unique run ID on the event loop without an intervening await.
- No shared temporary candidate directory was found in the service launch path.

Snapshot:

- No launch batch workspace snapshot owner exists.
- `ControlPlaneLauncher._prepare` reads `sessions_for_runs` and `resolve_workdir_context` for every candidate. Workspace and acting context can change between calls.
- `resolver_snapshots_for_harness` supplies the reusable pinned target input, but the current control plane does not call it. Capture assembles a fresh resolver snapshot per launch.

Dispatch identity:

- `ControlPlaneService.launch` mints per call.
- `LaunchLedger`, `GatewayCreateRunRequest`, `RunManager.pendingCreates`, and control plane audit persistence all identify a launch without candidate key.
- With one shared dispatch, candidate two would replay candidate one when fingerprints match, raise an idempotency conflict when they differ, and lose its independent audit row.

### Extra work for per item failure isolation

The service needs one candidate wrapper around the existing launcher. It must:

1. Preserve the shared dispatch and candidate key.
2. Return a terminal candidate outcome for expected `ControlPlaneError` values.
3. Preserve `unknown` when gateway delivery may have occurred.
4. Allow sibling tasks to finish.
5. Keep caller cancellation separate from candidate failure.
6. Return outcomes in request order.

The wrapper should follow `ControlPlaneService._close_target`. It should not add a runner or manager.

### Snapshot once per batch

The current code has per launch assumptions:

- Actor workspace root is read inside `_prepare`.
- Workdir scope is canonicalized inside `_prepare`.
- Space and worktree acting context are resolved inside `_prepare`.
- Target resolver snapshots are assembled later inside capture.
- Gateway create receives mutable launch fields rather than a frozen specification.

Batch needs one service owned preparation phase that seals workspace identity and the eligible harness resolver inputs, then passes those immutable facts into every invocation of the same launch path. Single launch should construct the same context for one fixed candidate key. This preserves one semantic.

## Candidate identity risks

The largest immediate risk is partial candidate key propagation.

Changing only `LaunchLedger` would leave two collisions:

1. `GatewayCreateRunRequest.idempotency_key` is a UUID carrying only `dispatch_id`. `RunManager.createWithDisposition` keys by owner plus that value and guards different launch fingerprints.
2. `control_plane_action_dispatch_uq` deduplicates launch audit rows by actor, verb, and dispatch only.

The contract resolves the gateway side by requiring the `FrozenLaunchSpec` digest. The audit side still needs a candidate safe representation in the existing audit owner.

## Minimal implementation plan

1. Resolve the contract's open durable transaction and migration choice. Bind the result to the existing `LaunchLedger` owner. Do not create a parallel ledger.
2. Add red tests first:
   - one batch dispatch with two candidate keys spawns two runs;
   - replay of one candidate returns only its stored receipt;
   - intent drift for one candidate returns `dispatch_conflict`;
   - workspace and resolver inputs are read once before candidate actuation;
   - one candidate failure leaves sibling outcomes intact;
   - gateway keys use frozen specification digests;
   - audit retains every candidate;
   - advisory and resolved target fields survive REST and MCP.
3. Bring `LaunchRequest` and `LaunchResult` to the contract fields required by this slice in `run_models.py`. Add only the small batch envelope and candidate outcome models that existing result types cannot express.
4. Extend `LaunchLedger.claim` and `LaunchLedger.release_preparation_failure` with `candidate_key`. Make single launch supply a fixed internal key.
5. Move current workspace and resolver reads into one sealed launch context preparation owned by `ControlPlaneLauncher`. Single launch prepares one context. Batch prepares one and reuses it.
6. Freeze each candidate through the same `ControlPlaneLauncher` resolution and execution path. Pass the `FrozenLaunchSpec` digest to `GatewayCreateRunRequest`. Reuse the Runtime string idempotency seam.
7. Make launch audit candidate safe in the existing audit persistence owner. Preserve single launch replay behavior.
8. Add `ControlPlaneService.launch_batch` as a thin ordered fan out. Mint one dispatch, validate candidate key uniqueness, call the existing launcher per item, and convert expected errors to item receipts.
9. Add branch free REST and MCP delegators beside the existing `launch` entrypoints. Do not add a CLI command, runner, manager, or gateway topology.
10. Run the targeted gates, then the full repository gates.

Exact targeted gates:

```bash
just api test -n0 \
  src/transport_matters/controlplane/test_launch_batch.py \
  src/transport_matters/controlplane/test_launch_ledger.py \
  src/transport_matters/controlplane/test_launch_replay.py \
  src/transport_matters/controlplane/test_launch_manage.py

just api test -n0 \
  src/transport_matters/api/v1/test_controlplane_skins.py \
  src/transport_matters/api/v1/test_controlplane_action_skins.py \
  src/transport_matters/api/v1/test_controlplane_skin_structure.py \
  src/transport_matters/api/v1/test_run_proxy_controlplane.py

pnpm --filter @tm/runtime test -- \
  src/service/RunManager.idempotency.test.ts \
  src/server/runtimeRouter.test.ts

just api migration-smoke
just check
just test
```

## Adjacent `NOW.md` items

- Latent `first_prompt` double stamp in `envelope.py::_extract_launch_delivery_id`: does not block.
- Per pane versus shared gateway design: does not block.

## Conclusion

The batch orchestration itself is a small wrapper. Current single launch identity is dispatch scoped at the ledger, gateway, and audit seams, and current preparation has no shared sealed workspace or resolver context. Candidate key, frozen context, durable replay, gateway digest identity, and candidate safe audit must land in the single launch authority before the wrapper is safe.
