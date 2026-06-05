---
title: Transport Matters baseline verification launch chokepoint scout
type: projects
tags: [transport-matters, baseline, launch, concurrency, scout]
summary: Live code map for launch triggered baseline verification, background work, exclusion, quota signals, and harvest caller demands
status: active
project: transport-matters
confidence: high
created: 2026-08-23
updated: 2026-08-23
---

# Baseline verification launch chokepoint scout

I inspected clean `main` at `ea10791ce64c29e2f4fb3be0a63f1e7e7c2607b7`. The inspection was read only. I did not start the backend, launch a harness, call a provider, or read or write the live Transport Matters store.

## Reuse map

### Chokepoint

There is one shared Python hook for Canvas and MCP launches: `api/src/transport_matters/api/v1/capture_rpc_routes.py` / `prepare_capture`. The precise placement is after `_resolved_domain_request` returns and after `CaptureLeaseRegistry.prepare_capture` returns the prepared spawn specification, but before `prepare_capture` returns to the gateway. At that point:

- The request has passed workspace, name, continuation, target, access, and effort resolution.
- `CapturedRunRequest` carries the harness plus the model and effort actuation values.
- `CaptureLeaseRegistry.prepare_capture` has completed live launch preparation. Its storage directory contains the fresh compatibility facts written by `prepare_launch`.
- The gateway is still awaiting `CaptureRpcClient.prepareCapture`.
- `packages/runtime/src/service/RunManager.ts` / `RunManager.createNew` calls `ptyPort.spawn` only after that RPC returns. The provider process has not started.

The Python hook is preferable to a TypeScript hook because harvest, staleness, bundle storage, runtime template resolution, and captured turn execution already live in Python. No second hook is needed.

The ingress chains are:

| Ingress | File and symbol path | Convergence proof |
| --- | --- | --- |
| Canvas command palette | `www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts` / `useCanvasCommandHandler` calls `addCapturedRun`; `www/packages/canvas/src/model/canvasActions.ts` / `createCapturedRunActions.addCapturedRun` creates a captured run pane; `www/packages/canvas/src/infrastructure/runtime/useCapturedRunBinding.ts` / `useCapturedRunBinding` calls `CapturedRunState.ensureRun`; `www/packages/canvas/src/model/capturedRunStore.ts` / `CapturedRunState.ensureRun` calls `createCapturedRunView`; `www/packages/core/src/transport.ts` / `createCapturedRunView` posts `/v1/runs`. | Python `api/src/transport_matters/api/v1/run_proxy.py` / `RunRouteProxy.forward_http` forwards the request to the gateway. `packages/runtime/src/server/runtimeRouter.ts` / `registerRunRoutes` calls `RunManager.createWithDisposition`, then `RunManager.createNew`, then `CaptureRpcClient.prepareCapture`. |
| MCP | `api/src/transport_matters/api/v1/controlplane_mcp.py` / `_McpControlPlaneAdapter.launch` calls `ControlPlaneService.launch`; `api/src/transport_matters/controlplane/service.py` / `ControlPlaneService.launch` calls `ControlPlaneLauncher.launch`; `api/src/transport_matters/controlplane/launch_service.py` / `ControlPlaneLauncher._execute` calls `RunRouteProxy.create_run`; `api/src/transport_matters/api/v1/controlplane_gateway_runs.py` / `create_run` posts `/v1/runs` to the gateway with `launchKind=service`. | The same gateway `registerRunRoutes`, `RunManager.createNew`, `CaptureRpcClient.prepareCapture`, and Python `capture_rpc_routes.prepare_capture` chain follows. |

`RunManager.createWithDisposition` has one production caller, `registerRunRoutes`. No production caller invokes `RunManager.create` directly. The common route is complete for gateway managed runs.

The statement that CMDK and MCP are the only two ingress families is accurate if Canvas HTTP is treated as one family. The literal CMDK only statement is incomplete. Two more Canvas triggers reach the same route:

- `www/packages/canvas/src/firstrun/FirstRunScreen.tsx` / `startAccessTest` calls `createCapturedRun` directly for a diagnostic provider access test.
- `www/packages/canvas/src/model/canvasActions.ts` / `createCapturedRunActions.continueSession` creates a continuation outside the command palette. `useCapturedRunBinding` then reaches the same store and REST path.

The shared hook must therefore distinguish a real operator launch from `providerAccessApproval=diagnostic_test`. `LaunchKind.SERVICE` cannot make that distinction because MCP launches also use it. Controlled baseline harvest and startup provider access verification call `run_captured_turn` directly, so they do not recurse through the capture RPC route.

### Concrete cell identity gap

Live code does not always know a concrete launch model and effort at the chokepoint.

- `www/packages/canvas/src/launcher/commandTypes.ts` / `LauncherCommand` carries `harness`, `agentId`, name, focus behavior, and worktree. It has no model or effort fields.
- `www/packages/canvas/src/model/capturedRunStore.ts` / `CapturedRunState.ensureRun` posts no model or effort for CMDK launches.
- MCP accepts optional model and effort in `_McpControlPlaneAdapter.launch` and carries `None` when omitted.
- `capture_rpc_routes._resolve_launch_target` calls `resolve_launch_target_advisory` only when model or effort is explicit. A native default launch leaves both fields as `None`.

`None` is valid actuation because it tells the harness to choose its native default. Baseline storage still needs the concrete `EnumeratedModel.model_id` required by `assess_baseline_staleness` and `harvest_controlled_baseline`. The implementation must obtain the concrete default target from the already loaded `ResolverSnapshots` while preserving native default actuation. Treating `None` as a model key would create a cell that baseline storage cannot address.

### Background work

No generic job runner exists. There is no Celery, RQ, Dramatiq, ARQ, APScheduler, FastAPI `BackgroundTasks`, or `asyncio.TaskGroup` use in production code.

Existing mechanisms are:

| Mechanism | Evidence | Fit for launch verification |
| --- | --- | --- |
| Lifespan owned startup tasks | `api/src/transport_matters/main.py` / `lifespan` stores `harness_refresh_task` and `harness_access_verification_task` on `app.state`. `_start_harness_access_verification` creates the second task. Shutdown cancels both before closing the pool. | Reuse the ownership and shutdown pattern. The startup task bodies themselves are one shot boot work and do not accept per launch jobs. |
| Guarded startup bodies | `api/src/transport_matters/harnesses/state_refresh.py` / `run_startup_refresh` catches and logs every failure. `api/src/transport_matters/harnesses/access_verification.py` / `run_startup_verification` awaits refresh, then catches and logs verification failure. | Reuse the fail open wrapper shape. Do not call either function for launch verification because their inputs and lifecycle are startup specific. |
| Fire and forget task registry | `api/src/transport_matters/harnesses/drift_emitter.py` / `DriftEmitter.submit` creates a task, retains it in `_tasks`, never raises, and removes it on completion. `DriftEmitter._begin` rejects seen or in flight evidence IDs. `DriftEmitter.drain` uses `drain_pending` before the session pool closes. | This is the closest background pattern. Reuse its owned task set, done callback, failure containment, and drain helper. Its `DriftEvidence` API cannot run provider captures directly, so do not route verification through the drift evidence domain. |
| Wire drift task registry | `api/src/transport_matters/drift_capture.py` / `WireDriftObserver._schedule` creates and retains detection tasks. `DriftCaptureRuntime.aclose` drains the observer and emitter. | Same reusable lifecycle pattern. The observer is tied to completed exchange artifacts and is too late and too specific for a launch trigger. |
| Addon process task sets | `api/src/transport_matters/addon_runtime.py` / `_schedule_detached_run_lifecycle_event` and `api/src/transport_matters/pause_session.py` retain tasks and drain them on addon shutdown. | Wrong process and wrong owner. A backend launch verification task must survive independently of one proxy addon's event loop. |
| MCP launch ledger | `api/src/transport_matters/controlplane/launch_ledger.py` / `LaunchLedger.claim` creates one task per owner, dispatch ID, and candidate key. A follower receives the same live task. | Wrong key and response contract. Callers await the launch task, entries are process local, successful entries persist, and there is no TTL. Verification followers must return no op rather than await or replay work. |
| Runtime and Canvas create maps | `packages/runtime/src/service/RunManager.ts` / `pendingCreates` deduplicates an idempotency key and makes followers await the same promise. `www/packages/canvas/src/model/capturedRunStore.ts` / `pendingSpawns` does the same per pane key and uses `queuedCapturedRunSpawnSlots` to cap five distinct spawns. | Wrong lifetime and semantics. Both are browser or gateway memory. The Canvas limiter queues distinct launches, while verification requires same cell no op and different cell concurrency. |
| Sharded commit job queue | `api/src/transport_matters/index/commit_dispatcher.py` / `ShardedCommitDispatcher` owns bounded `asyncio.Queue` instances and worker tasks. | Wrong domain and deliberately queue based. Reusing it would violate the single flight requirement. |
| Fanout queues | `api/src/transport_matters/broadcast.py`, `api/src/transport_matters/session/listen.py` / `SessionEventHub`, and `packages/runtime/src/service/TerminalFanout.ts` carry stream notifications with backpressure and catch up behavior. | Notification transport only. They do not own provider jobs or restart safe claims. |
| Long lived service loops | `SessionEventListener.start`, `SharedProxyManager._start_monitor`, `ControlPlaneWatchEngine._ensure_feed`, and the gateway watcher in `main.lifespan` create supervised tasks with explicit close paths. | Useful lifecycle examples. Each loop owns one continuous service and is the wrong shape for independent per cell captures. |
| Shielded thread preparation | `api/src/transport_matters/capture_rpc.py` / `CaptureLeaseRegistry.prepare_capture` uses `ensure_future`, `to_thread`, and `shield` so cancelled HTTP requests cannot leak a prepared lease. | The launch awaits it, so this mechanism does not perform background work. The cancellation cleanup is reusable around synchronous capture preparation, but the existing call cannot host the seconds long A/B/A job inline. |

The implementation should reuse the established task ownership pattern and `drain_pending`. It should not add a queue or a new worker service. `harvest_controlled_baseline` is synchronous, so the task must move it off the event loop with the existing `asyncio.to_thread` pattern.

### Mutual exclusion

There is no durable TTL lease or database backed single flight helper.

| Mechanism | Scope and liveness | TTL | Fit |
| --- | --- | --- | --- |
| `api/src/transport_matters/lock.py` / `WorkspaceLock` | Nonblocking `flock` on a file descriptor. Contention raises `WorkspaceLocked`. It works across processes on one filesystem and the kernel releases it when the holder dies. | None. Process death provides liveness. A live hung holder stays locked. | Closest match. A stable per channel, executor, and cell lock directory gives one capture and immediate no ops for contenders. Different directories permit concurrent cells. The current class also owns workspace manifest naming, so reuse may require a small ownership cleanup rather than copying its `flock` block. |
| `lock.py` / `exclusive_file_lock` | Blocking `flock`, automatic release on death. | None. | Wrong contention behavior because it queues. |
| `api/src/transport_matters/session/migrate.py` / `apply_migrations` | Blocking session level `pg_advisory_lock`, then recheck. PostgreSQL releases it with the connection. | None. | Global and queued. Wrong for paid capture single flight. |
| `api/src/transport_matters/space/store_space_ops.py` / `SpaceStoreSpaceOps.lock_owner_scope`; `api/src/transport_matters/session/wire_store.py` / `commit_wire_exchange` | Blocking transaction advisory locks keyed by owner identity or a global watermark. Row mutations also use `FOR UPDATE`. PostgreSQL releases locks at transaction end or connection loss. | None. | The keyed identity pattern is relevant. No `pg_try_advisory_lock` helper exists, so current behavior queues. |
| Keyed `asyncio.Lock` uses | `api/src/transport_matters/api/v1/exchanges.py` / `_lock_for`, `api/src/transport_matters/api/v1/harnesses.py` / `refresh_harnesses`, and `api/src/transport_matters/breakpoint.py` serialize work in one event loop. | None. | Process local and blocking. A restart forgets ownership. |
| In memory single flight sets and maps | `DriftEmitter._in_flight`, `LaunchLedger._entries`, `RunManager.pendingCreates`, and Canvas `pendingSpawns`. | None. | Useful only inside one process. They do not protect billed turns across backend restarts or concurrent backend processes. |
| Capture leases | `CaptureLeaseRegistry._leases` tracks live prepared runs and `CaptureLeaseHandle.alive` checks their proxy process. | None. | Keyed by run ID, process local, and created after a capture starts. It cannot claim a baseline cell. |

`WorkspaceLock` already supplies the required no wait exclusion and death liveness. It has no elapsed time TTL. A capture timeout and `finally` release cover a live but failed worker; process death releases the file descriptor. If the implementation requires timed reclamation while the owner remains alive, no current helper supplies it.

### Quota and limit signals

There is one partial exhaustion signal and no remaining allowance signal.

- `api/src/transport_matters/provider_conditions.py` / `classify_provider_response_status` can mint `usage_limit_reached` for Anthropic only after a 429 with `x-should-retry: false`. Its comment says the rule is false negative biased and no real usage cap 429 has certified that header yet.
- The same function deliberately does not classify Codex usage exhaustion because its in band limit frame has no certified shape.
- `api/src/transport_matters/live_status_observer.py` records provider conditions. `api/src/transport_matters/controlplane/activity.py` and the Activity contract can surface `needs-you-usage-limit` for an affected run.
- `api/src/transport_matters/codex/protocol.py` allowlists a `codex.rate_limits` response tag, but no production parser, persistence owner, remaining allowance reader, or launch guard consumes it.
- `api/src/transport_matters/controlplane/launch_ledger.py` limits MCP launch requests to 120 per owner per 60 seconds by default. That protects the local control plane. It says nothing about provider weekly caps, billed turns, or remaining quota.

Searches covered `rate_limit`, `rate limits`, `quota`, `weekly`, `usage_limit_reached`, `429`, `Retry-After`, `remaining turn`, and `usage limit` across Python, TypeScript, SQL migrations, contracts, and dependency manifests. No provider weekly cap, remaining turns, or headroom signal was found.

The existing condition can prevent verification after Transport Matters has already observed exhaustion. It cannot prove that three billed turns are safe before capture. The quota guard therefore lacks a data source and must remain an explicit implementation prerequisite. Do not describe `usage_limit_reached` as a complete quota guard.

### Harvest caller contract

`api/src/transport_matters/baseline_capture.py` / `harvest_controlled_baseline` requires all of the following from its caller:

| Demand | Current CLI owner | Launch path assessment |
| --- | --- | --- |
| Harness, wire provider, concrete `EnumeratedModel`, executable path | `baseline_harvest.main` reads `harness_inventory`, projects `HarnessLaunchViewResponse`, checks launchable and authenticated state, finds the descriptor and binary, then runs `_select_model`. | The capture route already owns `ResolverSnapshots`, target resolution, provider access assessment, and the exact binary preparation. Repeating inventory projection would create a third resolver. Native default model identity is currently missing, as described above. |
| Model effort | `_enumerated_models` carries the default effort, and `--effort` replaces it only after option validation. | Must come from the existing resolver evidence for the selected model. Raw `CapturedRunRequest.effort=None` is insufficient when baseline storage needs the concrete cell. |
| Runtime template | `resolve_capture_baseline_template` reads the harness template mapping and resolves it from the current environment. | Required and valid for controlled isolation. A wheel launch can only use it if packaged runtime roots are resolvable. Failure must leave the cell unverified and the launch unaffected. |
| Fixed prompts and comparable reference plan | `ControlledPrompts` defaults to ALPHA and BRAVO. Harvest rejects prompt or runtime template changes against an existing reference. | Required. The launch must trigger the fixed controlled sample and must never use the operator's real prompt or home. |
| Writable controlled workspace and baseline output | CLI defaults to a temporary workspace and the channel baseline directory. Harvest reads the current pointer, writes an immutable bundle, validates read back, and promotes only bootstrap or exact outcomes. | Required. The operator worktree must not become the sample. The channel home remains the storage owner. |
| Session store and capture dependencies | CLI passes `default_claude_run_dependencies`. Each probe checks session store availability. | The live backend already owns `app.state.capture_registry.dependencies`. Reuse those dependencies. The helper name is misleading because the dependency set serves every captured harness. |
| Three sequential provider turns | `harvest_controlled_baseline` runs A1, B, A2 synchronously through `run_captured_turn`. | Seconds of blocking work. It must run in the existing background task and thread pattern. Any exception is a failed verification attempt, never a launch error. |
| Source revision | CLI calls `require_clean_worktree` and passes its returned HEAD to `source_commit`. `BaselineBundle.source_commit` requires exactly 40 lowercase hexadecimal characters. | This is the sharp blocker. A wheel install may have no Git checkout at `Path(__file__).resolve().parents[3]`. A dirty source checkout is rejected even though ordinary launch is valid. Removing the cleanliness call alone is insufficient because the bundle schema still requires a Git SHA. Production needs packaged revision provenance or an intentional bundle provenance change. |

The clean worktree requirement belongs to certification minting, where live checkout bytes must match a commit. Launch triggered verification runs installed product bytes. Applying `require_clean_worktree(Path(__file__).resolve().parents[3])` there would reject wheel installs, dirty checkouts, and nonrepository module layouts before the first probe.

## Quality map

### Duplication and ownership

- `baseline_harvest.main` resolves inventory, launchability, model, effort, binary, and provider. `capture_rpc_routes._resolve_launch_target` already owns launch target and access resolution for live runs. A launch implementation must reuse the resolver result and avoid copying `_enumerated_models` or `_select_model` into a new service.
- `default_claude_run_dependencies` is a generic captured run dependency bundle with a Claude specific name. The live registry getter, `CaptureLeaseRegistry.dependencies`, is the correct reuse point.
- Fire and forget task retention appears in `DriftEmitter`, `WireDriftObserver`, addon lifecycle, pause counting, watch maintenance, and other owners. Copying the create, retain, callback, drain sequence again would deepen duplication. Reuse `drain_pending` and the established owner lifecycle.
- File locking has one generic blocking helper and one workspace specific nonblocking class. Copying raw `fcntl.flock` into baseline code would violate the repository's DRY rule.

### Boundaries

- The hook belongs at the server composition edge. Lower capture and baseline modules should not import FastAPI routes or `main`. Inject the verifier from `main.lifespan` or app construction into the route or registry owner.
- Baseline capture already orchestrates captured turns, projection, comparison, and baseline storage. It should not own Canvas or MCP request models.
- The stated dependency direction `ir -> adapters -> rules -> pipeline -> storage -> breakpoint -> server` remains unaffected if the hook stays in server orchestration and calls a lower verification service. Importing server code into baseline, captured, storage, breakpoint, or IR code would reverse that direction.
- The FMM runtime cycle scan found one existing source cycle between `api/src/transport_matters/index/record_ingest.py` and `api/src/transport_matters/index/tailer.py`. It is unrelated to launch or baseline code. No cycle was found in the inspected launch and baseline chain.

### Dead code candidates

- `api/src/transport_matters/captured/run.py` / `run_captured_run_on_local_tty` has no production caller. Its only named import is `api/src/transport_matters/cli/_helpers.py`, a test helper that imports `pytest`.
- `packages/runtime/src/service/RunManager.ts` / `RunManager.create` has no production caller. Production calls `createWithDisposition`; tests still call `create`.

These candidates are grooming work. They should not expand the launch verification change unless deletion or refactoring becomes necessary for the touched boundary.

### Size guardrails

| File | Lines | Assessment |
| --- | ---: | --- |
| `packages/runtime/src/service/RunManager.ts` | 685 | Fifteen lines below the hard file limit. Do not add the feature here. |
| `api/src/transport_matters/main.py` | 645 | Keep composition wiring small. Put behavior in an existing owner or a focused module. |
| `www/packages/canvas/src/firstrun/FirstRunScreen.tsx` | 623 | No feature code is needed here. |
| `api/src/transport_matters/api/v1/capture_rpc_routes.py` | 621 | The hook can stay a small call. Move verification behavior out. |
| `api/src/transport_matters/capture_rpc.py` | 498 | Registry ownership fits lifecycle injection, but baseline policy does not belong in this file. |
| `packages/runtime/src/server/runtimeRouter.ts` | 458 | `registerRunRoutes` is already 177 lines, above the function threshold. Refactor before adding behavior there. |
| `api/src/transport_matters/captured/run.py` | 474 | `prepare_captured_run` is already 167 lines. Refactor before adding behavior there. |
| `api/src/transport_matters/baseline_capture.py` | 397 | `harvest_controlled_baseline` is 113 lines and already owns controlled capture. Extend through inputs or smaller helpers only if required. |
| `api/src/transport_matters/baseline_harvest.py` | 204 | CLI wrapper. Production launch code should not call `main`. |

No production file under the inspected roots exceeds 700 lines. The files above 700 found by the measurement pass are tests.

### Grooming recommendation

Keep the change in Python. Add one small call at `capture_rpc_routes.prepare_capture`, reuse the existing resolver and live capture dependencies, reuse the owned task lifecycle and `WorkspaceLock` liveness, and leave `RunManager` untouched. Before adding code to `prepare_captured_run` or `registerRunRoutes`, decompose those functions. Do not add a queue, a second launch resolver, copied file lock code, or a harvest subprocess wrapper.

## Plan

1. Make the existing launch resolution owner expose a concrete verification cell for native default and explicit target launches while preserving the existing native actuation values. Prove CMDK default, explicit MCP model, effort override, and rejected target behavior.
2. Introduce a focused Python verification coordinator below the API route and above baseline capture. Give it the baseline output root, fresh installed version, concrete model cell, provider, binary, runtime template resolver, live capture dependencies, task lifecycle, and quota decision as explicit inputs. Keep FastAPI and gateway types outside it.
3. Call the coordinator from `capture_rpc_routes.prepare_capture` only after launch preparation succeeds and before returning the spawn specification. Skip diagnostic access tests. Schedule without awaiting. Wrap the task so all failures log, leave the cell unverified, and never alter the response.
4. Use a stable per channel, executor, and model cell path with the existing nonblocking `WorkspaceLock` behavior. Contention returns a no op. Different paths run concurrently. Release in `finally`; process death supplies liveness. Add a timeout around the A/B/A work. Do not use blocking file locks, PostgreSQL blocking advisory locks, or a queue.
5. Reuse `assess_baseline_staleness`, but feed it the version from the launch's freshly written compatibility facts, never the stored inventory observation. Recheck after claiming the lock so a capture that just finished turns the contender into a no op.
6. Adapt the harvest caller boundary. Reuse `harvest_controlled_baseline` directly with the live registry dependencies and controlled runtime template. Replace the certification only clean checkout provenance requirement with packaged revision provenance or an intentional bundle provenance contract change. Do not call `baseline_harvest.main`.
7. Treat known `usage_limit_reached` as a skip signal. Keep the broader quota guard blocked on an explicit provider headroom source because the repository has no remaining allowance signal. Record that limitation in tests and product status rather than claiming full coverage.
8. Reuse the existing task retention and drain pattern. Close or cancel outstanding verification tasks before the session pool and other dependencies close. Do not add a runner or job queue.
9. Prove single flight with five concurrent same cell launches yielding one harvest and four no ops, different cells running concurrently, process death or timeout allowing a later claim, quota skip, all harvest failures failing open, no recursive trigger from controlled or diagnostic service turns, and notification only after the verdict lands.
10. Run focused Python tests for resolution, staleness, locking, task lifecycle, and harvest invocation. Then run the repository's named `just check` and `just test` gates and confirm the worktree after each gate.
