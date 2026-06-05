# Transport Matters real restart spec

Status: implementation ready. Verified against `feat/desktop-detach` HEAD `d1c152f` on 2026-06-20 for PR #160.

## Goal

Make `just channel-restart preview` mean a real restart: stop the old detached channel backend, free the channel ports, prepare the database, then start a fresh desktop instance. When the old backend dies, its hosted Electron window should close itself instead of sitting on a load failure screen.


## Current seams

Detached launch already records the backend process. `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached` calls `activate_channel`, builds a `DesktopLaunchPlan`, starts `plan.command` with `subprocess.Popen`, redirects stdout and stderr to `desktop.log`, passes `start_new_session=True`, writes `DesktopRuntimeRecord`, waits for readiness, then spawns Electron. `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord`, `desktop_record_path`, `desktop_log_path`, `read_live_desktop_record`, and `is_pid_alive` are the owned record seam.

Channel management already has the right command group. `api/src/transport_matters/cli/channel_cmd.py:channel_app` owns `list`, `ensure_db`, and `promote`. `channel_cmd.py:_desktop_pid` reads the runtime record for `list`. Channel argument resolution for read only commands should mirror `api/src/transport_matters/cli/tail_cmd.py:_resolve_channel_or_exit`, which calls `transport_matters.channel:resolve_channel_spec` and therefore honors the explicit argument, then `TRANSPORT_MATTERS_CHANNEL`, then `stable`.

The cheapest backend liveness endpoint already exists. `api/src/transport_matters/main.py:create_app` registers `GET /health` and returns only `{"status": "ok"}`. `desktop/src/backendHealth.ts:backendHealthUrl` already points to that route, and `desktop/src/backendHealth.ts:waitForBackendHealth` uses it for startup readiness.

Hosted Electron is isolated from backend startup. `desktop/src/main.ts:registerDesktopLifecycleFromEnv` enters `registerHostedDesktopLifecycle` when Python supplies `DESKTOP_ROUTE_URL`. `desktop/src/main.ts:registerHostedDesktopLifecycle` creates the hosted window and delegates app activation to `bindHostedWindowLifecycle`. Initial load failures are already handled by `desktop/src/window.ts:registerHostedWindowPolicy`, which calls `desktop/src/window.ts:showHostedLoadFailure` on main frame `did-fail-load`.

## Contract

### `transport-matters channel stop [channel]`

Add `stop` beside `list`, `ensure-db`, and `promote` in `api/src/transport_matters/cli/channel_cmd.py:channel_app`.

Resolution: use `resolve_channel_spec`, not `activate_channel`, so stop is a channel lookup with no environment mutation and no database work. Unknown channels should reuse the list hint shape from `tail_cmd.py:_resolve_channel_or_exit`.

Record path: compute `default_storage_root(spec.id).expanduser().resolve()`, then `desktop_record_path(storage_root)`. This targets the normal channel scoped record. Explicit `--storage-dir` launches remain outside channel stop, matching the accepted edge in the detach spec.

Runtime helper: put the kill logic in `api/src/transport_matters/cli/desktop_runtime.py`, not inside Typer code. Suggested export: `stop_desktop_record(record_path, *, timeout_s=3.0, poll_s=0.1, pid_alive=is_pid_alive, kill=os.kill, sleep=time.sleep) -> StopDesktopResult`. Keep `channel_cmd.py:stop` as I/O only: resolve channel, call helper, print one concise result, map unrecoverable permission or OS errors to exit code 1.

Result shape: use a tiny frozen dataclass or enum plus pid field, with statuses for `nothing` and `stopped`. The helper should own record unlinking, signal escalation, and stale cleanup. The Typer layer should own channel labels and printed text. Tests can inject `pid_alive`, `kill`, and `sleep`, so SIGTERM, timeout, SIGKILL fallback, and ProcessLookupError races stay headless and deterministic.

Idempotency: missing record, malformed record, and dead PID are success. Dead PID cleanup should unlink the stale record. Successful stop should also unlink the record. Output examples: `nothing running for preview` and `stopped preview desktop pid 12345`.

Kill mechanism: send `SIGTERM` to the recorded PID, poll until `is_pid_alive(pid)` is false, then send `SIGKILL` to the same PID after the bounded timeout. Use PID, not process group. `start_new_session=True` in `desktop_cmd.py:run_desktop_detached` detaches the backend from the launcher terminal; the recorded process is the backend owner and uvicorn runs inside it. Process group kill is broader and can hit future child sessions. This stop command is one kill plus cleanup, with no supervisor behavior.

### `just channel-restart`

Change `justfile:channel-restart` by inserting:

```just
uv run --project "{{api_dir}}" transport-matters channel stop {{channel}}
```

after the web and desktop build steps and before `transport-matters channel ensure-db {{channel}}`. Restart then becomes build, stop, ensure database, launch. The second launch should see free ports for preview `8797` and `8798`.

### Hosted Electron auto close

Add a liveness poll for the hosted route path in `desktop/src/main.ts:registerHostedDesktopLifecycle`. Reuse `desktop/src/backendHealth.ts:backendHealthUrl` and factor `desktop/src/backendHealth.ts:isBackendHealthy` so startup readiness and hosted liveness share one probe implementation. Give each probe a real timeout, for example 750 ms, by creating an `AbortController`, arming a timeout that aborts the probe, and clearing that timeout when the probe settles.

Start polling only after the first successful hosted load, for example from a `did-finish-load` hook on the created window. That keeps the current initial load failure contract owned by `window.ts:registerHostedWindowPolicy` and `showHostedLoadFailure`. If the backend is absent before the first page load, show the existing load failure dialog. If the backend disappears after a successful load, close the window.

Derive the health target from `options.routeUrl`, not from process env, so tests and future launchers can pass any hosted URL through one contract. A small helper can parse the route URL, extract the web port, and pass it to `backendHealthUrl`. If parsing fails, skip the auto close poll and let the existing load policy report the bad route.

Self schedule probes with `setTimeout` after each probe settles, not with a fixed `setInterval`. Wait 1000 ms between settled probes, close after 3 consecutive failed probes, and clear the pending timeout on `closed`. The close action is `window.close()`, not a navigation and not a dialog. Non overlapping probes keep the failure count reliable when a half dead backend stalls fetches, while the debounce lets a transient blip recover.

## Traceability

- Channel resolution -> `api/src/transport_matters/channel.py:resolve_channel_spec`; `api/src/transport_matters/cli/tail_cmd.py:_resolve_channel_or_exit`.
- Stop command registration -> `api/src/transport_matters/cli/channel_cmd.py:channel_app`.
- Storage root resolution -> `api/src/transport_matters/storage_roots.py:default_storage_root`.
- Runtime record read and cleanup -> `api/src/transport_matters/cli/desktop_runtime.py:desktop_record_path`; `read_live_desktop_record`; `is_pid_alive`.
- Graceful kill helper -> `api/src/transport_matters/cli/desktop_runtime.py:stop_desktop_record`.
- Detached backend PID source -> `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached`.
- Restart recipe -> `justfile:channel-restart`.
- Liveness endpoint and probe -> `api/src/transport_matters/main.py:create_app`; `desktop/src/backendHealth.ts:backendHealthUrl`; `desktop/src/backendHealth.ts:isBackendHealthy`.
- Hosted close -> `desktop/src/main.ts:registerHostedDesktopLifecycle`; `desktop/src/window.ts:registerHostedWindowPolicy`; `showHostedLoadFailure`.
- Operator docs -> `README.md`; `docs/CHANNELS.md`; `api/src/transport_matters/cli/help.py:_DESKTOP_HELP`.

## Slice plan and gates

Slice 1: Python stop plus restart wiring. Add `channel stop`, the runtime kill helper, stale record tests, CLI tests for no record, dead PID, SIGTERM success, SIGKILL fallback, permission failure, and `justfile:channel-restart` wiring. Update README, Channels docs, and CLI help so they point to `transport-matters channel stop [channel]` instead of manual `kill <PID>`. Gates: root `just check`; root `just test`; `cd api && just ci`. Live smoke: run `just channel-restart preview` twice in a row. The second run must have no `web UI port 8798 is already in use` error, and `transport-matters channel list` must show a new preview PID.

Slice 2: Electron hosted liveness close. Add the shared health probe, wire `registerHostedDesktopLifecycle`, and extend `desktop/src/main.test.ts:it opens a Python supplied hosted route without backend startup` or add adjacent tests proving no poll before first successful load, debounce across transient failures, and `window.close()` after 3 failures. Gates: root `just check`; root `just test`; `cd desktop && just check`; `cd desktop && just package-smoke`; repeat the live smoke and verify the old preview window closes after the first restart stops its backend.
