# Transport Matters concurrent spawn failure brainstorm

## Summary

Confirmed from live code: the browser text `Failed to spawn captured run: 500` means the backend returned HTTP 500 from the `launch_failed` error path. A detected captured run bind conflict maps to HTTP 409, so a final detected `CapturedRunBindConflict` is not the observed 500. The concurrency specific failure path that fits the report is mitmdump startup readiness timeout, surfaced as `launch_failed`, with thread pool saturation explaining launch slowness and delayed unrelated `to_thread` work.

No local failing runtime log was available under `~/.transport-matters` during this investigation, so the 500 classification is code confirmed and the specific timeout cause is the strongest code path match for bulk launch pressure.

## Confirmed request path

1. `www/src/api.ts` `createCapturedRun`, lines 390 to 409, posts to `/v1/runs` with `cli`, optional `cwd`, and `oscColorReplies`. It sends no `idempotencyKey`.
2. `api/src/transport_matters/main.py` `create_app`, lines 202 to 204, mounts `run_routes.router` with prefix `/v1`.
3. `api/src/transport_matters/api/v1/run_routes.py` `create_run`, lines 405 to 427, handles `POST /v1/runs`, builds a `SpawnRun`, calls `RunManager.spawn`, and converts `RunManagerError` through `_http_error_from_manager`.
4. `api/src/transport_matters/run_manager.py` `RunManager.spawn`, lines 249 to 260, sends requests with no `idempotency_key` directly to `_spawn_new`; only keyed requests enter `_spawn_idempotency_lock`.
5. `api/src/transport_matters/run_manager.py` `RunManager._spawn_new`, lines 266 to 285, first awaits `_prepare_request`, then uses a second `asyncio.to_thread` call to spawn the PTY client.
6. `api/src/transport_matters/run_manager.py` `RunManager._prepare_request`, lines 393 to 415, calls `prepare_captured_run` inside `asyncio.to_thread` and maps `CapturedRunBindConflict` to `RunManagerError("bind_conflict")`; every other exception becomes `RunManagerError("launch_failed")`.

## Confirmed 500 root cause

A true bind conflict is not the visible 500:

1. `api/src/transport_matters/captured_run.py` `prepare_captured_run`, line 67, sets `_BIND_RETRY_ATTEMPTS = 3`; lines 210 to 266 retry proxy startup bind failures and raise `CapturedRunBindConflict` only after retry exhaustion.
2. `api/src/transport_matters/run_manager.py` `RunManager._prepare_request`, lines 410 to 415, maps `CapturedRunBindConflict` to `bind_conflict` and maps all other exceptions to `launch_failed`.
3. `api/src/transport_matters/api/v1/run_routes.py` `_RUN_MANAGER_HTTP_STATUS`, lines 60 to 70, maps `bind_conflict` to 409 and `launch_failed` to 500.
4. `api/src/transport_matters/api/v1/run_routes.py` `_http_error_from_manager`, lines 168 to 177, raises the mapped HTTP status for the `RunManagerError` code.
5. Local probe on Python 3.14.5 confirmed the mapping: `bind_conflict` returned status 409 and `launch_failed` returned status 500.

The code path that matches many concurrent launches is proxy readiness timeout:

1. `api/src/transport_matters/cli/runner.py` `start_prepared_proxy`, lines 317 to 331, spawns mitmdump and calls `wait_for_port_ready` on the proxy port.
2. `api/src/transport_matters/cli/net.py` `wait_for_port_ready`, lines 52 to 69, polls for up to five seconds.
3. `api/src/transport_matters/cli/runner.py` `_proxy_not_ready_outcome`, lines 134 to 150, returns `LaunchBindFailureOutcome` only when the log identifies a bind failure; otherwise it returns `LaunchExitOutcome` with `mitmdump did not come up within 5s.`
4. `api/src/transport_matters/captured_run.py` `_raise_prepare_outcome`, lines 290 to 293, converts non bind launch outcomes to `RuntimeError`.
5. `api/src/transport_matters/run_manager.py` `RunManager._prepare_request`, lines 414 to 415, converts that `RuntimeError` to `RunManagerError("launch_failed")`.

Conclusion: detected port races return 409 after three bind retries. The observed 500 is the generic launch failure path, with mitmdump readiness timeout under bulk start pressure as the best confirmed code path match. PTY spawn failure would also return 500 through `RunManager._spawn_new`, lines 278 to 331, but this investigation found no local log evidence pointing there.

## Retry status

There is retry, but only after a detected bind failure:

1. `api/src/transport_matters/captured_run.py` `prepare_captured_run`, lines 210 to 260, retries `start_prepared_proxy` up to three attempts and calls `handle_bind_failure` for a new port pair.
2. `api/src/transport_matters/cli/bind_failure.py` `handle_bind_failure`, lines 126 to 164, reallocates unpinned failed ports and fails fast for user pinned ports or allocator exhaustion.
3. `api/src/transport_matters/cli/test_captured_run.py` `test_prepare_captured_run_preserves_owned_session_across_retries`, lines 223 to 271, proves a first bind failure can retry with a fresh proxy port while preserving the owned session.
4. `api/src/transport_matters/cli/test_runner.py` `test_run_client_children_outcome_captures_bind_failure`, lines 333 to 359, proves `EADDRINUSE` in the mitmdump log becomes `LaunchBindFailureOutcome`.

There is no retry for non bind readiness timeout, generic mitmdump exit, or PTY spawn failure. There is also no reservation that prevents two launches from selecting the same available port before either mitmdump process binds.

The next retry layer should live at the captured run launch boundary, not in the frontend. That boundary already knows whether ports were user supplied, owns the storage and manifest lease, can classify bind versus readiness failures, and can apply backoff without duplicating launch policy in React. `RunManager` should own concurrency limits and per request admission because it is the API resource owner.

## Thread pool and launch slowness

Local runtime evidence:

1. Python is 3.14.5.
2. `os.cpu_count()` is 12.
3. Default `ThreadPoolExecutor` worker count is 16.
4. A local `asyncio.to_thread` probe with 50 blocking jobs observed `max_active_to_thread_jobs=16`, about 1.012 seconds for 50 jobs of 0.25 seconds, and an unrelated `to_thread` call delayed by about 0.711 seconds. The event loop ticker still advanced, proving queueing rather than event loop blockage.

Code evidence:

1. `api/src/transport_matters/run_manager.py` `RunManager._prepare_request`, lines 398 to 409, consumes one default executor worker for each blocking `prepare_captured_run` call.
2. `api/src/transport_matters/run_manager.py` `RunManager._spawn_new`, lines 278 to 285, consumes another default executor worker for PTY `Popen` after prepare succeeds.
3. `api/src/transport_matters/run_manager.py` `RunManager._teardown_run`, lines 548 to 553, and `RunManager._rollback_post_prepare`, lines 573 to 576, also use `asyncio.to_thread`, so cleanup can queue behind launch work when the shared executor is saturated.

Interpretation for 50 concurrent POSTs:

1. Only 16 blocking prepare or PTY jobs run at once on this machine; the rest queue in the shared default executor.
2. The event loop remains responsive, but other `to_thread` users wait behind spawn work.
3. Mitmdump processes that have already passed readiness stay alive while later queued prepare jobs start, so the process, file descriptor, and CPU pressure can still rise toward the requested 50 runs.
4. Bulk launch wall clock serializes in waves of 16, and each readiness timeout can hold an executor worker for up to five seconds.

## Per spawn latency phases inside prepare

1. `api/src/transport_matters/captured_run_context.py` `build_captured_run_context`, lines 70 to 93, resolves the launch profile, add on, mitmdump executable, client binary, working directory, and ports through `prepare_launch`.
2. `api/src/transport_matters/cli/launch_runtime.py` `prepare_launch`, lines 275 to 319, calls `require_addon`, `resolve_mitmdump_or_exit`, `resolve_client_binary`, `resolve_launch_ports`, `new_run_id`, and `resolve_storage_dir`.
3. `api/src/transport_matters/cli/launch_runtime.py` `resolve_launch_ports`, lines 154 to 185, allocates missing ports and only probes user supplied ports. It does not reserve auto allocated ports.
4. `api/src/transport_matters/cli/ports.py` `allocate_port_pair`, lines 55 to 67, opens two sockets, reads their assigned ports, closes the sockets, and returns the numbers. The free check ends before mitmdump binds.
5. `api/src/transport_matters/captured_run_context.py` `build_captured_run_context`, lines 97 to 129, plans and prepares runtime home, prepares the managed session, and materializes the add on path.
6. `api/src/transport_matters/captured_run.py` `prepare_captured_run`, lines 207 to 224, takes a per run workspace lock, persists session facts, writes the manifest, builds the invocation, spawns mitmdump, and enters readiness polling.
7. `api/src/transport_matters/cli/runner.py` `start_prepared_proxy`, lines 317 to 331, is the dominant per attempt wait because it can poll for up to five seconds.

The wall clock serialization comes from the shared default executor cap and from each blocking readiness poll occupying an executor worker. There is no process wide semaphore that shapes load before mitmdump starts.

## Shared state and race review

1. `api/src/transport_matters/run_manager.py` `RunManager.__init__`, lines 243 to 246, creates `_runs`, `_runs_by_idempotency_key`, `_spawn_idempotency_lock`, and `_teardown_lock`.
2. `api/src/transport_matters/run_manager.py` `RunManager.spawn`, lines 252 to 260, locks only keyed requests. Since the frontend sends no `idempotencyKey`, the normal canvas spawn path bypasses this lock.
3. `api/src/transport_matters/run_manager.py` `RunManager._spawn_new`, lines 266 to 312, performs the slow external side effects before mutating `_runs`; the actual `_runs` insertion has no await and is safe under the single event loop model.
4. `api/src/transport_matters/run_manager.py` `RunManager.close`, lines 387 to 391, can set `_closed` while a spawn is in prepare or PTY spawn. `_spawn_new`, lines 309 to 310, checks `_closed` again after PTY spawn and rolls back, so this is resource waste rather than a corrupt shared map.
5. There is no shared port reservation map. `api/src/transport_matters/cli/ports.py` `allocate_port_pair`, lines 55 to 67, deliberately releases the sockets before returning. This permits same process and external processes to race before mitmdump binds.
6. Leases are per spawn and are closed on rollback through `RunManager._rollback_post_prepare`, lines 573 to 576. I found no shared lease collection mutated without a guard.

Important design note: adding `idempotencyKey` from the frontend will de duplicate retried identical pane opens, but the current `_spawn_idempotency_lock` serializes all keyed spawns, even different keys. A production singleflight should lock per key and use a separate bounded concurrency semaphore for global launch pressure.

## Ranked reliability fixes

1. Add a launch admission controller in `RunManager`: an `asyncio.Semaphore` around prepare plus PTY spawn, with explicit queue metrics and a typed overload response if the queue is too deep. Start conservatively at a configurable limit below the default executor worker count, then tune with 50 run load tests.
2. Move captured run work to a dedicated executor owned by `RunManager`, so launch, PTY spawn, and teardown do not starve unrelated `asyncio.to_thread` users. Keep cleanup capacity reserved, for example one small cleanup executor or a priority path.
3. Replace probe only port allocation with a lease abstraction. Best option if mitmdump supports it: let the child bind port 0 and report the actual port through a readiness channel. If mitmdump requires a numeric port up front, add a process local `PortLeaseRegistry` that reserves allocated ports until readiness succeeds or rollback runs, then keep the existing bind retry as defense against external processes.
4. Extend retry and backoff for proxy readiness failures. Keep the current bind specific retry, and add a short bounded retry for `mitmdump did not come up within 5s.` with jitter and fresh ports when the log is empty or inconclusive. Surface final exhaustion as a typed `proxy_start_timeout`, likely 503 or 504, rather than generic `launch_failed` 500.
5. Add frontend idempotency keys for user initiated pane spawns and parse object shaped API error details. This improves retries and diagnosis, but it does not solve 50 unique concurrent launches by itself.
6. Add structured per phase timings around `build_captured_run_context`, `prepare_runtime_home`, `start_prepared_proxy`, `wait_for_port_ready`, and PTY spawn. The note above is code path evidence; production tuning needs real histograms.

## Verification run

Focused tests passed locally with Python 3.14.5:

```text
api/.venv/bin/python -m pytest \
  api/src/transport_matters/api/v1/test_run_routes_launch.py::test_post_launch_failure_returns_machine_error \
  api/src/transport_matters/cli/test_captured_run.py::test_prepare_captured_run_preserves_owned_session_across_retries \
  api/src/transport_matters/cli/test_runner.py::test_run_client_children_outcome_captures_bind_failure \
  api/src/transport_matters/cli/test_runner.py::test_handle_bind_failure_reallocates_only_named_unpinned_slot \
  api/src/transport_matters/cli/test_runner.py::test_handle_bind_failure_anonymous_failure_replaces_all_unpinned \
  api/src/transport_matters/cli/test_runner.py::test_handle_bind_failure_propagates_allocator_error
```

Result: 6 passed in 0.17 seconds, exit 0.
