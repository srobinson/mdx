---
title: "Tier 2 bounded shared proxy pool design"
type: design
tags: [transport-matters, tier-2, shared-proxy, bounded-pool, performance]
summary: "Generalize SharedProxyManager from one shared mitmdump subprocess to K members, with K=1 as the default identity case."
status: proposed
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

# Tier 2 bounded shared proxy pool design

## Summary

The Slice 9 load harness found one shared mitmdump subprocess can carry 50 mixed runs correctly, but it reaches the CPU knee. The bounded pool is the HQ5 fallback: K shared mitmdump subprocesses, each one an unchanged instance of the current member machinery, with the API side manager becoming a router and supervisor.

Recommendation: build this as a generalization of `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager` with K=1 as the default identity case. K=1 should keep the same public contract, same control payloads, same subprocess command, same control socket path, same log path, and same register or deregister behavior. K>1 is opt in through a new setting.

Estimated implementation: about 4 engineer days, 3 PRs, and 650 changed or added LoC. Risk: medium, mostly lifecycle and race risk. The per member proxy, addon, control, core, and capture machinery stays unchanged.

## Current facts from main

* `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager` owns one `SharedProxyProcess`, one `SharedProxyControlChannel`, API side mirrors keyed by run id and listen port, one overrides cache, one monitor task, and one restart rehydrate flag.
* `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager.register` validates unique run id and listen port, starts the subprocess if needed, stores a `SharedProxyBindingPayload`, and sends `RegisterListenerRequest`.
* `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager.deregister` looks up a run, sends `DeregisterListenerRequest`, removes manager mirrors, and drops cached overrides for that run.
* `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager.set_overrides` sends `SetOverridesRequest` before committing the override cache, and restores the previous snapshot on failure.
* `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager._rehydrate_locked` replays all cached bindings, then all cached overrides, after a subprocess restart.
* `api/src/transport_matters/shared_proxy/process.py::SupervisorSharedProxyProcess` launches `python -m transport_matters.shared_proxy.subprocess` with one control socket and one log path.
* `api/src/transport_matters/shared_proxy/control.py::SharedProxyControlClient` and `api/src/transport_matters/shared_proxy/control.py::SharedProxyControlServer` already provide the full member control contract: `ping`, `register_listener`, `deregister_listener`, and `set_overrides`.
* `api/src/transport_matters/shared_proxy/subprocess.py::SharedProxySubprocess` owns `DumpMaster`, listener mode updates, accept probes, the subprocess binding table, and `SharedProxyCore`.
* `api/src/transport_matters/shared_proxy/addon.py::SharedProxyBindingTable` resolves new flows by listen port, tracks stamped flows by flow id and run id, and cleans up `active_flows` when flows complete.
* `api/src/transport_matters/shared_proxy/addon.py::SharedProxyAddon` fails closed when it cannot map a flow to a binding.
* `api/src/transport_matters/shared_proxy/core.py::SharedProxyCore` registers one run with the member's transcript tailer and snapshot writer, and unregisters only that run on teardown.
* `api/src/transport_matters/addon_runtime.py::load_shared_capture_runtime` creates the member local HTTP client, token counter, session writer, transcript tailer, and sharded commit dispatcher.
* `api/src/transport_matters/session/pool.py::create_async_pool` uses `Settings.session_pool_min_size` and `Settings.session_pool_max_size` for each pool instance.
* `api/src/transport_matters/shared_proxy/run_preparation.py::prepare_shared_captured_run` only needs a manager shaped object with `register` and `deregister`.
* `api/src/transport_matters/run_manager.py::RunManager._prepare_request` routes external web runtime launches through `prepare_shared_captured_run` and embedded launches through the older per run path.
* `api/src/transport_matters/main.py::lifespan` creates the shared proxy manager, starts it only after the session store starts, and degrades canvas run launch if shared proxy startup fails.
* `api/src/transport_matters/api/v1/exchanges.py::list_exchanges` resolves storage by run id and has no member awareness.
* `api/src/transport_matters/api/v1/stream.py::stream_run` subscribes by run id and has no member awareness.
* `api/src/transport_matters/api/v1/session_routes.py::stream_session_events` and `api/src/transport_matters/api/v1/session_routes.py::stream_session_timeline` read from Postgres and the session event hub, not from a proxy member.
* `api/tests/integration/shared_proxy_load_harness.py::LoadMetrics` records proxy CPU and the current verdict says bounded pool is recommended when one proxy saturates.

## K=1 identity feasibility

Feasible.

The safest design keeps `SharedProxyManager` as the public type. Internally, it owns a tuple of members. With `shared_proxy_pool_size=1`, the tuple has one member built from the same `runtime_dir` and `_control_socket_path` as today. The member receives the same `RegisterListenerRequest`, `DeregisterListenerRequest`, and `SetOverridesRequest` payloads that the single subprocess receives today.

Identity requirements:

* `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager.create` keeps `runtime_dir=get_settings().storage_dir / "runtime" / "shared-proxy"` for K=1.
* K=1 keeps `runtime_dir / "shared-proxy.sock"` or the existing `/tmp/tm-sp-.../s.sock` fallback from `api/src/transport_matters/shared_proxy/manager.py::_control_socket_path`.
* K=1 keeps `runtime_dir / "logs" / "shared-mitmdump.log"` through `api/src/transport_matters/shared_proxy/process.py::SupervisorSharedProxyProcess`.
* K=1 keeps `process_id`, `is_running`, `by_run_id`, and `by_listen_port` semantics. For K>1, `process_id` can return the first member for compatibility while a new `process_ids` diagnostic property exposes all pids.
* Existing tests should pass without setting the new pool size. New tests assert the K=1 child command, socket path, log path, registry maps, and rehydrate order match today's behavior.

This makes the rollout additive. The first PR can ship dark at K=1. K>1 changes only when the setting is raised.

## Component design

### SharedProxyManager as router and supervisor

`api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager` becomes the pool owner. It keeps the existing public methods:

* `start()`
* `close()`
* `supervise()`
* `register(binding)`
* `deregister(run_id)`
* `set_overrides(scope, payload)`
* `by_run_id`
* `by_listen_port`
* `process_id`
* `is_running`

New internal state:

```python
_members: tuple[_SharedProxyMember, ...]
_member_by_run_id: dict[str, _SharedProxyMember]
_member_by_listen_port: dict[int, _SharedProxyMember]
_broadcast_overrides: dict[OverrideScopeKey, OverrideSnapshotPayload]
_lock: asyncio.Lock
_monitor_task: asyncio.Task[None] | None
```

`by_run_id` remains a union of member payload maps. `by_listen_port` remains `listen_port -> run_id`, not `listen_port -> member`, so callers see the same contract. The member dimension stays internal through `_member_by_run_id` and `_member_by_listen_port`.

### Internal member object

Extract the current single subprocess behavior into a private `_SharedProxyMember` inside `manager.py`. It is a refactor of the current manager internals, not a new subprocess path.

Member fields:

```python
member_id: str
process: SharedProxyProcess
control: SharedProxyControlChannel
by_run_id: dict[str, SharedProxyBindingPayload]
by_listen_port: dict[int, str]
overrides: dict[OverrideScopeKey, OverrideSnapshotPayload]
needs_rehydrate: bool
lock: asyncio.Lock
```

Member methods mirror the current private manager behavior:

* `start()` and `supervise()` reuse the current `_ensure_started_locked`, `_wait_until_ready_locked`, and `_rehydrate_locked` logic.
* `register_payload(payload)` sends `RegisterListenerRequest` to this member only.
* `deregister_run(run_id)` sends `DeregisterListenerRequest` to this member only.
* `set_overrides(scope, payload)` sends `SetOverridesRequest` to this member only.
* `active_run_count` returns `len(by_run_id)`.

What stays unchanged:

* `api/src/transport_matters/shared_proxy/subprocess.py::SharedProxySubprocess`
* `api/src/transport_matters/shared_proxy/control.py::SharedProxyControlClient`
* `api/src/transport_matters/shared_proxy/control.py::SharedProxyControlServer`
* `api/src/transport_matters/shared_proxy/core.py::SharedProxyCore`
* `api/src/transport_matters/shared_proxy/addon.py::SharedProxyAddon`
* `api/src/transport_matters/shared_proxy/addon.py::SharedProxyBindingTable`
* `api/src/transport_matters/shared_proxy/models.py::SharedProxyBindingPayload`
* `api/src/transport_matters/shared_proxy/binding.py::ProxyRunBinding`

### Member creation

`SharedProxyManager.create` gains `pool_size: int = 1`.

For K=1, it builds the same process and control client as today.

For K>1, it builds K members with unique runtime roots:

```text
{runtime_dir}/members/0/
{runtime_dir}/members/1/
...
```

Each member receives a distinct control socket through `_control_socket_path(member_runtime_dir)` and a distinct log path:

```text
{runtime_dir}/logs/shared-mitmdump-0.log
{runtime_dir}/logs/shared-mitmdump-1.log
...
```

The subprocess argv remains unchanged because each member is still `api/src/transport_matters/shared_proxy/process.py::SupervisorSharedProxyProcess` launching `api/src/transport_matters/shared_proxy/subprocess.py::async_main`.

### Start and monitor

`SharedProxyManager.start()` starts all members. For the initial K>1 version, fail the entire shared proxy startup if any member fails before app startup completes. This matches the existing degrade model in `api/src/transport_matters/main.py::lifespan`: canvas runs are disabled rather than partially routed through a damaged pool.

`SharedProxyManager.supervise()` iterates members and calls member scoped supervise. A member failure logs with `member_id` and does not block supervising the other members. A failed rehydrate is retried by the existing monitor loop. Active runs assigned to that member remain assigned there and are not migrated.

### Register selection

Selection policy: least loaded by active run count.

Algorithm:

1. Validate global uniqueness of run id and listen port, using `_member_by_run_id` and `_member_by_listen_port`.
2. Choose the member with the smallest `active_run_count`.
3. Use member id as a stable tie breaker to make tests deterministic.
4. Add global and member mirror state before sending the control request, matching today's manager side ordering.
5. Send `RegisterListenerRequest` to the chosen member.
6. On failure, roll back global maps and member maps, then re raise.

Run placement is pinned for the run lifetime. No active run migrates between members. No listener port moves after registration.

This gives CPU headroom and isolates failures while preserving the current demux invariant: one listen port maps to one run inside exactly one member.

### Deregister routing

`SharedProxyManager.deregister(run_id)` looks up `_member_by_run_id[run_id]`, calls that member's deregister, then removes the global maps and cached run scoped overrides. This is the same behavior as `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager.deregister`, with one added lookup.

If the member has already crashed, member `deregister_run` should still call `ensure_started` before sending the control request. If restart cannot complete, preserve the manager side desired state and raise the existing `SharedProxyControlError`. `RunManager` already surfaces teardown failures through its async close path, and the monitor keeps retrying member rehydrate.

### Override routing

Current API sync only forwards shared overrides when a run id is present: `api/src/transport_matters/api/v1/overrides.py::_sync_shared_overrides` returns when `run_id is None`. For the pool:

* Run scoped override: route to the owning member from `_member_by_run_id`.
* Unknown run id: preserve today's effective API behavior by no op at the API sync layer. Direct manager calls may raise `SharedProxyRegistryError` if needed for tests.
* Non run scoped override: broadcast to all members and cache in `_broadcast_overrides`. This protects future callers and preserves K=1 semantics.

For run scoped set failures, restore the previous cached snapshot just like `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager.set_overrides` does today. For broadcast failures, use a two phase approach: send to every member, then commit the cache only if all ACK. If any member fails, restore members that already ACKed to the previous snapshot.

### Binding registry with member dimension

Manager side registry gains member dimension only in the API process:

```python
_member_by_run_id: dict[str, _SharedProxyMember]
_member_by_listen_port: dict[int, _SharedProxyMember]
```

Public properties keep their old shapes:

```python
by_run_id: Mapping[str, SharedProxyBindingPayload]
by_listen_port: Mapping[int, str]
```

Subprocess side registries stay member local. `api/src/transport_matters/shared_proxy/addon.py::SharedProxyBindingTable` is unchanged. Each member has its own port map, flow map, runtime binding map, and active flow sets.

### Per member shared core duplication

Each member subprocess calls `api/src/transport_matters/shared_proxy/core.py::load_shared_proxy_core`, which calls `api/src/transport_matters/addon_runtime.py::load_shared_capture_runtime`.

That means K members create:

* K `DumpMaster` instances.
* K `SharedProxyAddon` instances.
* K `SharedProxyBindingTable` instances.
* K `SharedProxyCore` instances.
* K `httpx.AsyncClient` instances.
* K token counters, unless `TRANSPORT_MATTERS_DISABLE_TOKEN_COUNTER=1` is set.
* K `SessionWriter` instances.
* K `TranscriptTailer` instances.
* K `ShardedCommitDispatcher` instances.
* K Postgres async pools through `api/src/transport_matters/session/pool.py::create_async_pool`.
* K process local `OverrideStore` module instances.

Correctness remains per run because a run lives on exactly one member:

* Its `ProxyRunBinding` stays in one member's `SharedProxyBindingTable`.
* Its active flows stay in that member's flow map.
* Its recent auth lives on that member's `ProxyRunBinding`.
* Its override snapshot is applied to that member's process local store.
* Its owned transcript cursor is registered in that member's `TranscriptTailer`.
* Its snapshot writer is registered in that member's `SharedTranscriptSnapshotWriter`.

No cross member sync is required for per run correctness. Cross member migration is out of scope.

Cost formula:

* DB connections: API pool plus `K * Settings.session_pool_max_size` for shared proxy members. With current default `session_pool_max_size=10`, K=2 gives 20 member connections, K=4 gives 40 member connections. The old 50 per run proxy model could create up to `50 * session_pool_max_size`, so the connection ceiling win still holds.
* Memory: `K * current shared mitmdump RSS`, plus K Python interpreters and mitmproxy masters. This is still far below 50 per run mitmdump processes.
* CPU: work is distributed by active run count. If one member reaches the CPU knee around 50 active streams, K=2 puts a 50 run canvas near 25 runs per member.

## Sizing K

Add a setting to `api/src/transport_matters/config.py::Settings`:

```python
shared_proxy_pool_size: int = Field(default=1, ge=1)
```

Add the same setting to the operator example settings file. Pass it through `api/src/transport_matters/main.py::lifespan` into `SharedProxyManager.create(pool_size=settings.shared_proxy_pool_size)`.

Rollout default: 1. This is required for K=1 identity.

Recommended opt in for the 50 run target: 2 on the current load finding. One subprocess saturated around 50 active streams, so 2 members provides CPU headroom and member crash isolation without large DB or RAM cost.

General recommendation once this is stable:

```text
K = min(ceil(target_active_runs / (member_knee_active_runs * 0.70)), max(1, cpu_count - 2), 4)
```

Where:

* `target_active_runs` starts at 50 for the canvas target.
* `member_knee_active_runs` comes from the load harness, currently about 50 for the tested host.
* `0.70` keeps a safety margin below the knee.
* `cpu_count - 2` reserves CPU for the API, UI, database client work, and agents.
* `4` is the first cap. Raise it only after measuring DB connection budget, RSS, fd count, and register churn.

For 50 target runs and a 50 run knee, the formula returns 2.

## Failure model

### Member crash

A member crash affects only runs assigned to that member. With K members and even placement, expected blast radius is about `active_runs / K`.

Existing restart logic generalizes cleanly because `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager._ensure_started_locked` and `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager._rehydrate_locked` already restart a subprocess and replay desired state. In the pool, that logic moves to `_SharedProxyMember` and replays only that member's bindings and overrides.

In flight flows on the crashed member fail. Clients retry. Other members keep proxying.

### Restart and rehydrate

On member restart:

1. Start that member's `SupervisorSharedProxyProcess`.
2. Wait for its control socket with the existing ping loop.
3. Re send only that member's `RegisterListenerRequest` payloads.
4. Re send only that member's run scoped overrides plus any broadcast overrides.
5. Mark the member healthy.

No other member is touched.

### Register during churn

The manager lock serializes global map changes. Selection counts active runs already present in member maps. For the first version, holding the manager lock through the control request is acceptable because register is a lifecycle operation and this preserves today's ordering. If register p95 becomes a problem, split this later into a reservation state plus member local locks.

### Control channel per member

Each member has one Unix socket and one control client. Socket paths must be unique. Use member runtime dirs so the existing `api/src/transport_matters/shared_proxy/manager.py::_control_socket_path` fallback remains valid.

### API restart

No change. Runs are process resident and do not survive API restart, matching the current model in `api/src/transport_matters/run_manager.py::RunManager.close` and `api/src/transport_matters/main.py::lifespan`.

## Untouched surfaces

No API route shape changes are needed.

* `api/src/transport_matters/run_manager.py::RunManager._prepare_request` can continue passing the manager object to `api/src/transport_matters/shared_proxy/run_preparation.py::prepare_shared_captured_run`.
* `api/src/transport_matters/shared_proxy/run_preparation.py::SharedCapturedRunLease` can continue calling `deregister(run_id)` because the pool manager preserves that method.
* `api/src/transport_matters/api/v1/exchanges.py::list_exchanges`, `api/src/transport_matters/api/v1/exchanges.py::get_exchange`, and related exchange reads stay member agnostic. They resolve storage from live `RunManager`, current process settings, or run manifests through `api/src/transport_matters/api/v1/run_storage.py::resolve_run_storage`.
* `api/src/transport_matters/api/v1/stream.py::stream_run` stays run id based through `broadcast.subscribe(run_id)`.
* `api/src/transport_matters/api/v1/session_routes.py::stream_session_events` and `api/src/transport_matters/api/v1/session_routes.py::stream_session_timeline` stay Postgres and session hub based.
* Frontend routing stays unchanged because run ids remain the read boundary.
* `api/src/transport_matters/shared_proxy/subprocess.py`, `api/src/transport_matters/shared_proxy/control.py`, `api/src/transport_matters/shared_proxy/core.py`, and `api/src/transport_matters/shared_proxy/addon.py` stay unchanged for the first implementation.

## Migration slices

### PR 1: K=1 identity refactor

Goal: refactor current manager internals into member shaped code while shipping with one member only.

Changes:

* Extract `_SharedProxyMember` inside `api/src/transport_matters/shared_proxy/manager.py`.
* Make `SharedProxyManager` own `tuple[_SharedProxyMember, ...]` with exactly one member.
* Preserve public properties and methods.
* Preserve process command, socket path, log path, control payload order, and rehydrate order for K=1.
* Add tests that compare default K=1 paths and behavior with today's expected contract.

Verification:

* Existing `api/src/transport_matters/shared_proxy/test_manager.py` suite.
* Existing `api/tests/integration/test_shared_proxy_subprocess.py` suite.
* `cd api && just check && just test`.

### PR 2: K>1 routing and config

Goal: enable opt in K members.

Changes:

* Add `Settings.shared_proxy_pool_size` with default 1 in `api/src/transport_matters/config.py::Settings`.
* Pass the setting in `api/src/transport_matters/main.py::lifespan`.
* Build K members in `SharedProxyManager.create`.
* Add least loaded by active run count selection.
* Add global member maps by run id and listen port.
* Route deregister and run scoped overrides to the owning member.
* Broadcast non run scoped overrides for safety.

Verification:

* Unit test K=2 placement: run 1 member 0, run 2 member 1, run 3 member 0 with deterministic tie break.
* Unit test duplicate run id and duplicate listen port reject globally across members.
* Unit test deregister routes to the original member.
* Unit test set overrides routes to the original member.
* `cd api && just check && just test`.

### PR 3: restart isolation, load harness, and operational proof

Goal: prove K>1 behavior under churn and crash.

Changes:

* Add member scoped restart integration test: start K=2, register two runs, kill member 0 subprocess, confirm member 1 traffic still works, confirm member 0 rehydrates its binding.
* Update `api/tests/integration/shared_proxy_load_harness.py` to sample all member pids and report per member CPU plus aggregate CPU.
* Add `just shared-proxy-load-test --pool-size 2` or equivalent test arguments.
* Add logs with `member_id` for register, deregister, rehydrate, restart, and control failures.

Verification:

* Existing full gate.
* `cd api && just shared-proxy-load-test --runs 50 --requests-per-run 2 --ws-echo-samples 100 --pool-limit 50 --pool-size 2`.
* Expected proof: zero failed requests, zero contamination, capture complete, per member CPU below the single member knee, and successful member restart rehydrate.

## LoE and LoC estimate

| File | Estimate | Notes |
| --- | ---: | --- |
| `api/src/transport_matters/shared_proxy/manager.py` | 300 LoC | Extract member, add pool routing, member maps, selection, broadcast overrides, process ids. Keep file under 700 LoC. |
| `api/src/transport_matters/config.py` | 5 LoC | Add `shared_proxy_pool_size`. |
| `api/settings.example.toml` or packaged settings example | 5 LoC | Document the setting. Exact path should be confirmed before edit. |
| `api/src/transport_matters/main.py` | 10 LoC | Pass pool size into manager create. |
| `api/src/transport_matters/api/v1/run_routes.py` | 0 to 5 LoC | Likely unchanged. Only update if construction moves there. |
| `api/src/transport_matters/run_manager.py` | 0 LoC | Keep manager interface stable. Avoid adding to this 684 LoC file. |
| `api/src/transport_matters/shared_proxy/subprocess.py` | 0 LoC | Reused unchanged. |
| `api/src/transport_matters/shared_proxy/control.py` | 0 LoC | Reused unchanged. |
| `api/src/transport_matters/shared_proxy/core.py` | 0 LoC | Reused unchanged. |
| `api/src/transport_matters/shared_proxy/addon.py` | 0 LoC | Reused unchanged. |
| `api/src/transport_matters/shared_proxy/models.py` | 0 LoC | No member id in control payloads. Member dimension is API side only. |
| `api/src/transport_matters/shared_proxy/test_manager.py` | 170 LoC | K=1 identity, K=2 placement, global duplicate rejection, override routing, restart unit coverage. |
| `api/tests/integration/test_shared_proxy_subprocess.py` | 90 LoC | K=2 live member restart and rehydrate proof. |
| `api/src/transport_matters/api/v1/test_main_lifespan_shared_proxy.py` | 30 LoC | Startup with configured K and degrade on failed member startup. |
| `api/tests/integration/shared_proxy_load_harness.py` | 80 LoC | Pool size argument, all pid CPU sampling, per member metrics. |
| `api/tests/integration/test_shared_proxy_load_harness_unit.py` | 25 LoC | Metrics and verdict updates. |
| Config tests if present | 20 LoC | Settings parsing and default identity. |

Total: about 650 LoC.

Effort:

* PR 1: 1.5 days.
* PR 2: 1.5 days.
* PR 3: 1 day.

Total: about 4 engineer days. A single PR is possible, but 3 PRs keep K=1 identity reviewable.

## Risk register

| Risk | Severity | Mitigation |
| --- | --- | --- |
| K=1 behavior drift | High | PR 1 ships only K=1. Assert same child argv, socket path, log path, public maps, control payload order, and existing tests. |
| Register selection under churn | Medium | Serialize manager mutations first. Count active runs after each ACK. Add concurrent register tests. Move to pending reservations only if measured register p95 regresses. |
| Restart during register | High | Roll back manager maps on control error. Add tests where process exits before ACK and after local map insert. Keep listener port unavailable until rollback completes. |
| Rehydrate only one member | Medium | Keep member desired state local. Test member 0 restart does not send member 1 bindings. |
| Control socket collision | Medium | Use member runtime dirs and existing `_control_socket_path`. K=1 keeps the old path. |
| Override broadcast rollback | Medium | Current API only forwards run scoped overrides. For future non run scoped calls, use all ACK before cache commit and restore previous snapshots on partial failure. |
| DB connection budget | Medium | Document total member pool connections as `K * session_pool_max_size`. Cap initial K at 4. Add startup log showing the computed maximum. |
| Memory budget | Medium | K processes cost K current shared subprocess RSS, not 50. Require load proof before raising default. |
| File size creep | Low | Keep new code in `manager.py` under 700 LoC. Do not add to `run_manager.py`. |
| Load harness blind spot | Medium | Update harness to sample every member pid and report per member p95, aggregate CPU, failed requests, contamination, and capture correctness. |
| Partial startup policy | Medium | First implementation requires all K members to start. Runtime crashes are supervised per member. Partial capacity can be a later feature. |

## Open questions

1. Should the stable product default ever move above 1, or should K remain an explicit operator setting until more host profiles are measured?
2. What DB connection budget should the desktop installer reserve for Postgres when K is 2 or 4?
3. Should `session_pool_max_size` remain per member, or should a future setting define total pool budget divided across members?
4. Should the API expose member health in `/health`, a diagnostics route, or only logs for now?
5. Should placement stay least active run count, or should it become least active flow count after active flow metrics are surfaced?
6. Should future non run scoped overrides be forbidden on the shared path instead of broadcast?

## Final recommendation

Build the bounded pool as a K member generalization of `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager`. Keep K=1 as the identity default. Route new runs to the least loaded member by active run count and pin them there for life. Reuse the existing subprocess, control, core, addon, binding, and run preparation machinery unchanged. Enable K=2 only after the K=1 refactor passes the full gate and the K=2 load harness proves lower per member CPU with zero contamination.
