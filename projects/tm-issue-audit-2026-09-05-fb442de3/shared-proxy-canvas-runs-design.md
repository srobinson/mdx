# Canvas runs on the shared proxy

Roadmap item 4 from the 2026-09-05 CPU incident. Stuart owns the what: 100 concurrent agents on one machine, and overrides that reach canvas runs. This note is the how, for partner agreement before code.

## Today

`CaptureLeaseRegistry.prepare_capture` runs `prepare_captured_run` in a thread. That builds the run context, takes the workspace lock, persists owned session facts, then `_start_captured_attempts` starts one mitmdump per run under a `ProcessSupervisor`, retrying ports on bind failure or readiness timeout. The lease's `close` terminates that supervisor. The gateway spawns only the client from the spawn spec.

The channel backend already starts one `SharedProxyManager` (`main.py`), a Tier 2 mitmdump subprocess with a control socket that registers reverse listeners per run (`reverse:<upstream>@127.0.0.1:<port>`), demuxes flows by listen port to a `ProxyRunBinding`, runs the same capture handlers as the per-run addon (`shared_proxy/addon.py` wraps `addon_handlers`), and owns transcript cursors per binding (`core.register_binding`). It rehydrates bindings and overrides when the subprocess restarts. Nothing registers runs with it since the Python run manager was deleted in the gateway migration (#234), so it carries no runs and `_sync_shared_overrides` has nothing to sync to.

## Change

One new module, `shared_proxy/run_preparation.py`, revived from #137 on today's context API:

    async def prepare_shared_captured_run(request, *, shared_proxy, dependencies, control_plane_grants)
        -> tuple[CapturedRunSpawnSpec, SharedCapturedRunLease]

1. `build_captured_run_context` in a thread, exactly as `prepare_captured_run` does, then `_acquire_captured_run_resources` (workspace lock, owned session facts).
2. Port attempts reuse `_next_attempt_ports` and `_CAPTURE_ATTEMPTS`: write the manifest for the attempt, build the invocation with `web_port=None`, build the binding, `await shared_proxy.register(binding)`. A `SharedProxyRegistryError` or a `duplicate_listen_port` control error is a bind failure and moves to the next port; `listener_ready_timeout` and the control timeouts map to `CapturedRunProxyStartTimeout` as in June.
3. The binding is `ProxyRunBinding(run_id, harness, working_dir, DiskStorageBackend(storage), listen_port=proxy_port, upstream, agent_home_dir=descriptor_home(ctx), owned native id and descriptor from the managed session, space and worktree from the request, storage_root, launch_fields (request plus runtime home plan), default_client_passthrough, breakpoint_skip_models)`. Owned session metadata is required, as in June.
4. The spawn spec is the same shape the gateway consumes today: `web_port=None`, `proxy_port` is the listener, `mitmdump_log` is the shared proxy's log (`process.log_path`). The identity seed resolves with `web_port=None`.
5. `SharedCapturedRunLease.alive()` is `shared_proxy.is_running and run_id in shared_proxy.by_run_id`. `aclose()` deregisters then releases resources; `close()` releases resources only and is the thread fallback.

Registry:

- `CaptureLeaseRegistry(..., shared_proxy: SharedProxyManager | None)`, threaded from `create_capture_registry` and `main.py` (`app.state.shared_proxy_manager`, `None` when the shared proxy failed to start).
- `prepare_capture` takes the shared path when the manager is present, otherwise the existing per-run path with one warning naming the fallback. Per-run stays for the CLI's embedded launches and for the degraded case.
- `CaptureLeaseHandle` gains `async aclose()`; `release_capture` and `_close_abandoned_prepare` use it. The per-run lease's `aclose` is `to_thread(close)`.

Nothing changes in the gateway, the addon handlers, the manager, the subprocess, or the override sync. Overrides for canvas runs start reaching the proxy because `manager.by_run_id` now contains them.

## Out of scope, stated

Breakpoints. Arm, pause and release are process-local (`breakpoint.py`, `pause_session.py`) and the control channel carries only ping, register, deregister and set_overrides. They did not reach per-run proxies before this change and do not reach the shared proxy after it. A follow-up slice adds breakpoint control messages.

## Proof

- Tests: revive the four June tests against a fake manager; registry tests for path selection, fallback, release deregistering, health following the manager; the existing `test_manager.py`, `test_process.py` and `test_subprocess.py` cover the subprocess.
- Road test: restart preview on the branch, launch four agents, expect no mitmdump per run, one shared mitmdump, listener ports registered in `by_run_id`, an override set in the inspector visible in the shared proxy's store, and live status and transcript rows for every run.
- Scale: `just shared-proxy-load-test --runs 100` from `api/`, the opt-in Tier 2 harness that already exists.

## Expected footprint per run after

The harness process only. Postgres connections per run: zero from the proxy side, the shared subprocess holds one writer pool.
