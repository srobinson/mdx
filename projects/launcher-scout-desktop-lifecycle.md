# Desktop launcher lifecycle scout

## Reuse Map

### Command and process map

1. CLI entry: `api/src/transport_matters/cli/__init__.py::desktop` defines `transport-matters desktop`. It activates the channel, dispatches to `api/src/transport_matters/cli/desktop_cmd.py::run_desktop_launch` for `--foreground`, and dispatches to `api/src/transport_matters/cli/desktop_cmd.py::run_desktop_detached` for the default detached mode.

2. Shared launch planning: `api/src/transport_matters/cli/desktop_cmd.py::prepare_desktop_launch` builds the common `DesktopLaunchPlan`. `api/src/transport_matters/cli/desktop_cmd.py::_build_desktop_backend_command` creates the internal `transport-matters _desktop-backend` command. `api/src/transport_matters/cli/desktop_cmd.py::_build_desktop_backend_env` sets cwd, storage dir, proxy port, web port, and channel while stripping stale run specific env.

3. Foreground mode: `api/src/transport_matters/cli/desktop_cmd.py::run_desktop_launch` runs the FastAPI backend in the caller's Python process through `api/src/transport_matters/cli/desktop_cmd.py::serve_desktop_backend`. That server path creates a `uvicorn.Server` for `api/src/transport_matters/main.py::create_app`, starts it on a thread only when an `on_backend_ready` hook is needed, launches the Electron viewer through `api/src/transport_matters/cli/desktop_cmd.py::spawn_detached_electron`, then joins the server thread. The Electron viewer is a detached child. The foreground path does not write a `DesktopRuntimeRecord`, so `channel list` has no foreground backend pid to show or stop.

4. Detached mode: `api/src/transport_matters/cli/desktop_cmd.py::run_desktop_detached` starts the same internal `_desktop-backend` command as a new session, redirects stdout and stderr to `api/src/transport_matters/desktop_runtime.py::desktop_log_path`, writes `api/src/transport_matters/desktop_runtime.py::DesktopRuntimeRecord` through `api/src/transport_matters/desktop_runtime.py::write_desktop_record`, waits for readiness with `api/src/transport_matters/cli/desktop_cmd.py::_wait_for_detached_backend_or_exit`, launches the Electron viewer through `spawn_detached_electron`, and returns. The backing server is the child process running `api/src/transport_matters/cli/desktop_cmd.py::run_desktop_backend_server`, which calls `serve_desktop_backend`.

5. Electron app path: `desktop/src/main.ts::registerDesktopLifecycleFromEnv` is the Electron entry seam. When `TRANSPORT_MATTERS_DESKTOP_ROUTE_URL` is present, it uses `desktop/src/main.ts::registerHostedDesktopLifecycle`. That hosted path opens a window for the Python supplied backend and does not own the backend child. When the route URL is absent, it uses `desktop/src/main.ts::registerAppLifecycle`, which owns a backend child through `desktop/src/backendProcess.ts::launchBackendProcess` and stops it on app quit through `desktop/src/main.ts::bindBackendQuitCleanup`.

6. Shared proxy process: the desktop backend starts the FastAPI app, and `api/src/transport_matters/main.py::lifespan` creates a `SharedProxyManager` when the session store is available. `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager.start` starts it, and `api/src/transport_matters/shared_proxy/process.py::SupervisorSharedProxyProcess.start` spawns the shared mitmdump subprocess and writes its pid record. `main.py::lifespan`, `SharedProxyManager.close`, and `SupervisorSharedProxyProcess.terminate` already own shared proxy teardown.

7. Log tail: `api/src/transport_matters/cli/tail_cmd.py::run_tail` is a separate command. It reads `desktop_log_path`, follows appended bytes when requested, and exits only on `KeyboardInterrupt`. `transport-matters desktop` does not start this tail command. In foreground mode, the visible log stream is the uvicorn server output in the caller's terminal.

### Channel and runtime registry ownership

1. A channel is static environment identity, not the process registry. `api/src/transport_matters/channel.py::ChannelSpec` carries channel id, home, database name, default proxy and web ports, and Electron identity. `api/src/transport_matters/channel.py::_channel_specs` loads committed channel specs, and `api/src/transport_matters/channel.py::activate_channel` writes the selected channel to the process env and clears settings cache.

2. The detached desktop registry is the runtime record under the channel storage root. `api/src/transport_matters/desktop_runtime.py::DesktopRuntimeRecord` owns pid, proxy port, web port, cwd, storage dir, log path, version, and instance. `api/src/transport_matters/desktop_runtime.py::desktop_record_path`, `write_desktop_record`, and `discover_desktop_runtime` are the registry read and write seams.

3. `transport-matters channel list` sees a pid through `api/src/transport_matters/cli/channel_cmd.py::list_channels`, `api/src/transport_matters/cli/channel_cmd.py::_desktop_columns`, and `api/src/transport_matters/cli/channel_cmd.py::_desktop_status`. That path calls `discover_desktop_runtime` and prints a pid only when the runtime status is live.

4. `transport-matters channel stop` already has the stop path. `api/src/transport_matters/cli/channel_cmd.py::stop` resolves the channel record path and calls `api/src/transport_matters/desktop_runtime.py::stop_desktop_record`.

### Existing teardown machinery to reuse

1. `api/src/transport_matters/desktop_runtime.py::stop_desktop_record` is the direct reusable detached backend kill path. It reads the runtime record, sends SIGTERM, polls, escalates to SIGKILL after timeout, and unlinks the record.

2. `api/src/transport_matters/cli/desktop_recovery.py::prepare_desktop_runtime_for_launch_or_exit` already centralizes prelaunch recovery. It detects live, stale, wedged, not serving, and unhealthy runtime states through `discover_desktop_runtime`. `api/src/transport_matters/cli/desktop_recovery.py::recover_desktop_runtime_or_exit` and `force_restart_desktop_runtime_or_exit` both converge on `_stop_record_or_exit`, which reuses `stop_desktop_record`.

3. Electron has a separate backend child cleanup seam in direct mode. `desktop/src/main.ts::bindBackendQuitCleanup` stops the Electron launched backend child on `before-quit` through `desktop/src/backendProcess.ts::stopBackendProcess`. This is useful as a pattern for app owned cleanup, but it does not currently run for Python hosted desktop launches.

4. The hosted Electron path already detects backend loss in the other direction. `desktop/src/main.ts::registerHostedDesktopLifecycle` installs `desktop/src/hostedLiveness.ts::registerHostedBackendLivenessPoll`, which quits the app after repeated backend health failures. This is why backend shutdown can close the desktop, but window close does not close the backend.

5. Canvas managed runs have a mature teardown path. `api/src/transport_matters/run_manager.py::RunManager.terminate` and `RunManager.close` converge on `RunManager._teardown_run`, which closes attachments, terminates PTY resources, and closes the captured run lease. `api/src/transport_matters/shared_proxy/run_preparation.py::SharedCapturedRunLease.aclose` deregisters shared proxy bindings. `api/src/transport_matters/api/v1/run_routes.py::terminate_run` exposes the current HTTP stop surface for captured pane runs. Reuse the teardown pattern and shared proxy cleanup ownership, not the RunManager object for standalone desktop backend lifecycle.

### Desktop window close observability today

1. The Electron child observes window close in `desktop/src/main.ts::bindHostedWindowLifecycle` through Electron's `window-all-closed` event. In hosted mode, `registerHostedDesktopLifecycle` passes `quitOnWindowAllClosed: true`, so closing the only hosted window quits the Electron app on every platform.

2. The Python launcher does not observe that window close. `api/src/transport_matters/cli/desktop_cmd.py::spawn_detached_electron` calls `subprocess.Popen` with `start_new_session=True` and returns no process handle. `run_desktop_launch` and `run_desktop_detached` do not wait on the Electron child, do not set up IPC, and do not watch an Electron pid.

3. In default detached mode the Python launcher exits after spawning Electron, so no parent remains to observe Electron exit. In foreground mode the Python process stays alive serving uvicorn, but it has already discarded the Electron child handle. Closing the window cannot set `server.should_exit` today.

4. There is no `atexit` handler in the inspected desktop launcher files. Signal handling is local: `api/src/transport_matters/cli/desktop_cmd.py::serve_desktop_backend` catches `KeyboardInterrupt` and sets `server.should_exit`; `api/src/transport_matters/cli/tail_cmd.py::run_tail` catches `KeyboardInterrupt` and returns. `desktop_runtime.py::stop_desktop_record` uses SIGTERM and SIGKILL for recorded backend pid cleanup.

## Quality Map

1. Primary gap: the lifecycle edge from Electron window close back to the Python hosted backend is missing. The reverse edge already exists through hosted backend liveness polling.

2. Do not add another process registry. The existing source of truth for detached desktop backends is `DesktopRuntimeRecord` plus `discover_desktop_runtime` plus `stop_desktop_record`. `channel list`, `channel status`, `channel stop`, desktop recovery, and Electron discovery all already depend on that record contract.

3. Avoid a third backend launch implementation. The code already has two backend command builders: `api/src/transport_matters/cli/desktop_cmd.py::_build_desktop_backend_command` and `desktop/src/backendProcess.ts::buildBackendLaunch`. Any fix that needs backend process launch details should route through these owners or consolidate them, not copy their command construction.

4. File size risk is immediate. `api/src/transport_matters/cli/desktop_cmd.py` is 697 LOC, just under the 700 LOC hard limit. `api/src/transport_matters/desktop_runtime.py` and `desktop/src/main.ts` are both 655 LOC. A lifecycle fix should keep `desktop_cmd.py` as a thin dispatch surface and move new orchestration into a small owned module or an existing smaller owner such as `api/src/transport_matters/cli/desktop_recovery.py` when the behavior is purely record recovery.

5. RunManager is adjacent but not the standalone desktop owner. `RunManager._teardown_run` is the right pattern for one public stop path that closes all owned resources exactly once. The standalone desktop backend should reuse the same discipline and shared proxy close ownership, while keeping general agent lifecycle policy out of Transport Matters.

6. Tail behavior is independent. `tail_cmd.run_tail` follows the log file without consulting `DesktopRuntimeRecord` after startup. If the product wants a foreground or detached log tail to exit when the backend exits, it should reuse `discover_desktop_runtime` or pid liveness from `desktop_runtime.py` rather than inventing a second stop signal.

## Plan

1. DESIGN DECISION: choose the window close signal contract. The open choice is whether Electron should call a backend stop contract on `window-all-closed`, whether the Python foreground launcher should retain and wait on the Electron child process, or whether both modes should converge on a single `DesktopRuntimeRecord` mediated shutdown path. Detached mode cannot rely on a Python parent wait because `run_desktop_detached` exits.

2. DESIGN DECISION: decide whether foreground mode should also write a temporary `DesktopRuntimeRecord`. If yes, the same Electron close action can call the existing `stop_desktop_record` path and `channel list` can show the foreground pid. If no, foreground needs a separate child watcher or IPC path that sets `server.should_exit` without a runtime record.

3. Add tests first around the current seams. Python focused tests should cover `api/src/transport_matters/cli/desktop_cmd.py::run_desktop_launch`, `run_desktop_detached`, and `api/src/transport_matters/desktop_runtime.py::stop_desktop_record`. Electron tests should cover `desktop/src/main.ts::registerHostedDesktopLifecycle` and `bindHostedWindowLifecycle`. Tail tests should extend `api/src/transport_matters/cli/tail_cmd.py::run_tail` only if tail auto exit becomes part of the chosen scope.

4. Implement one reusable backend stop primitive. Prefer a small wrapper that resolves the active channel storage root and calls `stop_desktop_record`. Reuse it from `channel_cmd.stop`, desktop recovery, and any new Electron initiated shutdown. Keep kill semantics in `desktop_runtime.py`.

5. Wire hosted Electron close to the chosen stop primitive. The likely reuse seam is `desktop/src/main.ts::bindHostedWindowLifecycle`, because it already centralizes `window-all-closed`. The implementation should not duplicate `bindBackendQuitCleanup`; it should parameterize hosted shutdown behavior so Python hosted mode can stop its recorded backend and direct Electron mode can keep its existing child cleanup.

6. For foreground mode, use the decision from step 2. If the shared record path is chosen, make `run_desktop_launch` register the current backend pid and ensure `serve_desktop_backend` unlinks the record on normal exit and `KeyboardInterrupt`. If a child watcher is chosen, change `spawn_detached_electron` or a sibling launch helper to return a process handle and have `serve_desktop_backend` stop the server when that process exits.

7. Keep shared proxy teardown under the FastAPI lifespan. Do not terminate shared proxy directly from the launcher. Once the desktop backend exits, `main.py::lifespan`, `SharedProxyManager.close`, and `SupervisorSharedProxyProcess.terminate` already own that cleanup.

8. Verification gates for the implementation should include focused API tests for desktop launch, record stop, and tail behavior; Electron tests for hosted window close; then the repo native gates requested by the implementer. No verification was run for this scout beyond read only structural inspection.
