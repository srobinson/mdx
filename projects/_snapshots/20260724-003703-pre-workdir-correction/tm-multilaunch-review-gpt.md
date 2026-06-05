# `launch_batch` v1 design review

Date: 2026-07-21  
Reviewer: Codex, generalist lens  
Baseline: `feat/multi-launch` at `8c51797e01ef3880bb76517bafbe620766cbffe7`  
Repository state before review: clean

## Verdict

Choose the minimal hybrid.

The server should own an opaque `canvas_id` affinity on each launch. The client should
continue to own pane creation, layout, and per canvas local persistence. This preserves
the existing canvas implementation while giving MCP and browser callers the same
placement contract.

Option A cannot satisfy the draft's own three axis model. `adoptCapturedRun` operates on
the active Zustand canvas and accepts no target canvas. A director launch has no browser
caller available to perform the adoption. Split placement across canvases therefore
requires new routing even under A.

The largest loss from deferring server affinity is the authoritative run to canvas edge.
Without it, another client cannot observe or reconstruct a director's placement intent.

## Code grounding

| Draft claim | Result | Evidence and consequence |
| --- | --- | --- |
| Run creation has no canvas field | Confirmed | `CreateManagedRunInput` has `spaceId` and `worktreeId`, then `ManagedRunFilters` filters only those fields (`packages/runtime/src/service/runManagerTypes.ts:9-57`). `CapturedRunRequest` also has space and worktree fields with no canvas (`api/src/transport_matters/captured_run_models.py:68-100`). `RuntimeRunView` has no canvas (`packages/runtime/src/domain/runtimeRun.ts:10-23`). |
| Client placement reuses `addCapturedRun` and `adoptCapturedRun` | Confirmed with a material limit | Both methods mutate the current canvas store and accept no `canvasId` (`www/packages/canvas/src/model/canvasState.ts:43-59`, `canvasActions.ts:129-163`). The current adoption reconciler sees service runs, looks up a worktree, then adopts into `useCanvasStore.getState()`, which is the active canvas (`capturedRunAdoption.ts:196-220`, `SessionCanvasRoute.tsx:194-206`). The claim that A can adopt candidate i directly into canvas X is false with the current seam. |
| One runtime HOME per run | Confirmed | `_prepare_home_and_grant` places the home under `prepared.resolved_storage / "runtime-home"`, and the storage root is run specific (`api/src/transport_matters/captured_run_context.py:260-306`). Reusing single launch yields one HOME per successful candidate. |
| `LaunchLedger.claim` and gateway idempotency are reusable | Confirmed but incomplete | The Python ledger currently keys `(owner, dispatch_id)` and is explicitly process resident (`launch_ledger.py:1,67-100`). `ControlPlaneLauncher` sends that dispatch as `GatewayCreateRunRequest.idempotency_key` (`launch_service.py:224-240`). Node keys `(owner, idempotencyKey)` and retains it for the process lifetime (`runManagerTypes.ts:37-38`, `RunManager.ts:158-189`). Candidate identity must reach both boundaries. |
| Space, Worktree, and Canvas are server models | Confirmed | `Space`, `Worktree`, and `Canvas` are separate Space scoped records. Canvas has an optional default worktree and a layout bag (`api/src/transport_matters/space/models.py:121-175`). Pane membership remains in `CanvasModel.panes` on the client (`www/packages/canvas/src/model/paneRecords.ts:53-67`). |

Two additional grounding corrections are required:

1. Candidate identity must cross the audit boundary. Current launch audit rows are unique
   on `(actor, verb, dispatch_id)` (`api/migrations/versions/0016_action_dispatch_idempotency.py:21-39`).
   Each reused item launch writes verb `launch` with the outer dispatch
   (`action_builders.py:51-81`). N items under one dispatch would collapse to the first
   durable audit row. Prefer one `launch_batch` action with ordered candidate outcomes.
   If item audit rows remain, their durable identity must include `candidate_key`.
2. The governing contract requires a durable launch ledger and replay across service
   restart (`LAUNCH-CONTRACT.md:100-128,444-449`). The reusable ledger and gateway maps are
   process resident. The draft must either add durable batch claim and replay to L0 or
   record an explicit contract deviation. Calling the current reuse contract complete is
   inaccurate.

## Canvas decision

### Option A: client placement only

Benefits:

* Small server change.
* Same browser profile reload already restores canvas pane records from per canvas
  localStorage. The separate captured run store preserves `runKey` to `runId` bindings.
* Server layout ownership remains out of scope.

Costs:

* The existing seam targets only the active canvas.
* MCP directors cannot express an enforceable canvas destination.
* A second browser profile sees no placement record.
* Activity reconciliation adopts every service run into whichever canvas is active.
* Server list, filter, lifecycle, audit, and future hierarchy surfaces cannot recover the
  placement intent.

### Option B: server canvas ownership

Benefits:

* Durable, queryable placement and direct support for list or close by canvas.
* Multi client and director views can converge.
* Client reconciliation can route by explicit affinity.

Costs:

* Full server ownership of pane membership or layout would duplicate the current client
  aggregate and expand L0 into the parallel canvas layering track.
* Adding `canvas_id` only to `RuntimeRunView` and `ManagedRunFilters` would still be
  process resident. That version of B does not meet the durability claim.

### Minimal hybrid: recommended

Thread `canvas_id` as launch affinity without moving pane layout to the server:

1. Resolve and validate the requested canvas against owner and Space before claim.
2. Include `canvas_id` in normalized intent, the durable launch fact, audit outcome,
   receipt, gateway and capture contracts, runtime view, and activity fact.
3. Add an optional runtime filter by `canvas_id`. The public query can follow later, but
   preserving the fact now avoids a second contract migration.
4. Make client reconciliation target aware. An inactive target canvas needs a storage
   operation against that canvas's namespaced cache. Switching the active Zustand store
   for each receipt is unsafe.
5. Keep pane ids, geometry, dock state, and canvas layout client owned. Canvas hierarchy
   remains a separate relation between Canvas records.

This hybrid records intent once and renders it locally. It supports optimistic shells in
the palette and later adoption when the launch came from MCP.

## Answers to the five questions

### 1. Durability and reload

Option A survives a page reload only in the same browser profile because both pane refs
and captured run bindings are local persistence. A second profile has neither record.
An API restart ends the process resident runs, so old pane refs become stale and are
pruned. The durable session may remain, but its launch has no canvas grouping fact.

The hybrid preserves grouping as launch history and allows any client to reconstruct
placement while the run exists. Durable run survival is a separate future concern.

### 2. Multiple clients and director drill

A second viewer cannot discover the group under A. Roster and Activity expose flat runs,
and the director cannot inspect client localStorage. A hierarchy can be deferred, but the
leaf affinity needed to populate that hierarchy cannot.

### 3. Query, filter, and lifecycle

Without `canvas_id`, the server cannot list or close runs in canvas X. Batch lifecycle and
canvas lifecycle are distinct. `dispatch_id` plus `candidate_key` identifies the launch
experiment. `canvas_id` identifies placement. L1 profiles and L2 eval depend primarily on
the former, while director drill and canvas scoped management depend on the latter.

v1 does not need every query route. It does need both facts recorded accurately.

### 4. Cost of deferring

Adding a nullable field later is mechanically additive. The semantic migration is more
expensive:

* Existing service launches have no target to backfill.
* Current adoption assigns service runs to the active canvas, which may differ from the
  caller's intent.
* Saved profiles would contain a `canvas_ref` that the service did not honor.
* Client code would have established local placement as authority and would need conflict
  rules when server affinity arrives.

The repository has no external users, which reduces data migration cost. It does not
remove the contract and trust boundary rework.

### 5. Launch contract fidelity

The current `LAUNCH-CONTRACT.md` does not define canvas affinity, so A could satisfy that
document only if canvas placement were excluded from L0. The draft and the recorded product
decision make canvas a launch argument for both clients. Under that scope, A fails the twin
client invariant and the claimed candidate shape.

Amend the launch contract before implementation. Add canvas affinity and clarify the
runtime selected workspace isolation policy. The contract should also acknowledge the
current process resident replay gap or close it.

## Secondary design review

### Three axes

Prompt, workspace isolation, and canvas placement are sound as orchestration policy axes.
The current Worktree axis conflates two decisions:

* source selection: which existing worktree or workdir
* isolation policy: live shared workspace or an isolated copy from one sealed snapshot

`Worktree` is an existing identity record. No isolated copy or workspace snapshot runtime
exists. Model, effort, harness, agent, connection, and grant remain candidate target fields
outside these three policy axes. Rename the section accordingly and model source plus
isolation separately.

### Profile shape

The principle of one declarative shape for ad hoc and saved profiles is sound. The shown
candidate is not yet that shape. It omits fields owned by `LaunchRequest`, including harness,
agent, connection, name, grant, and unverified target policy. It also mixes reusable intent
with execution identity such as resolved worktree and canvas ids.

Keep two typed layers:

1. `LaunchProfileDefinition`: defaults, candidate overrides, stable workspace and canvas
   selectors, isolation policy, and prompt inheritance.
2. `LaunchBatchInvocation`: inline or saved profile reference, caller context, dispatch,
   resolved workspace facts, and server minted candidate keys.

Prompt inheritance needs three states: inherit shared prompt, supply candidate prompt, or
launch interactively with no prompt. An optional string cannot express all three safely
once a shared prompt exists.

This separation keeps saved profiles portable and still projects every candidate into the
single launch authority.

### L0, L1, L2, and canvas layering

The layering is viable with two corrections:

* L0 must record both experiment identity and canvas affinity. It can defer canvas
  hierarchy and all server layout ownership.
* L0 must expose workspace isolation as an explicit policy. `isolated_copy` may remain
  unavailable until snapshot sealing exists, but the contract must not claim eval
  reproducibility from live workdirs.

With those corrections, L1 can persist the declarative profile and L2 can add snapshot
materialization, evaluation artifacts, and comparison. Canvas hierarchy can evolve in
parallel because affinity refers to an opaque canvas identity rather than a hierarchy
position.

## Sign off

I sign off conditional on:

1. Adopt the minimal hybrid and carry validated `canvas_id` affinity through durable
   launch facts, receipts, activity, and target aware client adoption.
2. Carry candidate identity through ledger, gateway, delivery, and audit, with one durable
   ordered batch action or candidate scoped audit identity. Resolve or explicitly record
   the process restart replay gap.
3. Separate declarative profile definition from invocation, split workspace source from
   isolation policy, and define prompt inheritance as a three state value before freezing
   the L0 schema.
