# Transport Matters port audit mechanics

Date: 2026-06-24  
Tree: `transport-matters` HEAD `7aaba75`  
Scope: read only source audit. Codebase writes were not made.

## Executive summary

The current reclaim behavior is split. Detached CLI launch has the only integrated discovery and recovery path, and `just channel-restart` has an explicit stop then start precedent. Foreground CLI launch, the hidden backend command, and direct Electron backend launch still fall through to the raw fixed port check, so they can report `web UI port 8788 is already in use` instead of reclaiming the channel port.

The detached path also still treats a healthy same channel runtime as attach, not restart. If the product contract is "relaunch reclaims the fixed port", the live branch, foreground branch, and direct Electron branch need to share one relaunch preflight that stops the recorded channel runtime before `_resolve_backend_ports` runs.

## Entry path map

| Launch path | Entrypoint | Discovery preflight | Reclaim or attach behavior | Raw fixed port check |
|---|---|---|---|---|
| CLI `desktop --foreground` | `api/src/transport_matters/cli/__init__.py:desktop` to `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_launch` | None | None. `--force-restart` is rejected in the CLI split. | `prepare_desktop_launch` calls `_resolve_backend_ports`, which calls `port_in_use` and `raise_port_in_use`. |
| CLI `desktop` detached | `api/src/transport_matters/cli/__init__.py:desktop` to `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached` | Yes. `discover_desktop_runtime` runs before `prepare_desktop_launch`. | `live` attaches a viewer. `stale` and `not-serving` recover through `recover_desktop_runtime_or_exit`. `wedged` and `unhealthy` refuse through `refuse_desktop_runtime_or_exit`. `--force-restart` stops any non absent recorded runtime. | After recovery or absent discovery, `prepare_desktop_launch` still runs `_resolve_backend_ports`. Non recorded listeners still produce raw port errors. |
| Hidden backend command | `api/src/transport_matters/cli/__init__.py:desktop_backend` to `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_backend_server` | None | None. This path is a child server entrypoint. | `run_desktop_backend_server` calls `prepare_desktop_launch`, which calls `_resolve_backend_ports`. |
| Electron hosted viewer | `api/src/transport_matters/cli/desktop_cmd.py:spawn_detached_electron` sets `TRANSPORT_MATTERS_DESKTOP_ROUTE_URL`; `desktop/src/main.ts:registerDesktopLifecycleFromEnv` calls `registerHostedDesktopLifecycle` | None in Electron. The backend has already been handled by the CLI parent. | Viewer only. It opens the supplied route and polls backend liveness. | None in Electron. |
| Electron direct app launch | `desktop/src/main.ts:registerDesktopLifecycleFromEnv` to `registerAppLifecycle` | Partial. `resolveRuntimeStatus` calls `readDesktopRuntimeStatus`, which shells to `transport-matters channel status <channel> --json`. | If status is `live`, it attaches through `registerHostedDesktopLifecycle`. Otherwise it spawns `_desktop-backend` through `startBackendAndCreateWindow`. It does not call the recovery helpers. | The spawned `_desktop-backend` child runs `run_desktop_backend_server`, so occupied fixed ports fail through `_resolve_backend_ports`. |
| `just channel-restart` | root `justfile:channel-restart` | Explicit stop before launch, not discovery in the justfile itself. | Runs `transport-matters channel stop <channel>`, then `channel ensure-db`, then `transport-matters desktop --channel <channel>`. | After the stop, normal detached launch still runs `_resolve_backend_ports`. Non recorded listeners still produce raw port errors. |

## Shared mechanics

### Ports

Ports are channel spec fields. `api/src/transport_matters/channel.py:ChannelSpec` has `proxy_port` and `web_port`. The packaged specs in `api/src/transport_matters/channel-specs.json` define stable as proxy `8787`, web `8788`, and preview as proxy `8797`, web `8798`.

`api/src/transport_matters/cli/desktop_cmd.py:_resolve_backend_ports` chooses explicit CLI ports first, otherwise the channel spec ports, then probes both through `api/src/transport_matters/cli/net.py:port_in_use`. A positive probe exits through `api/src/transport_matters/cli/net.py:raise_port_in_use` with the current fixed port error.

### Runtime record

The runtime record is stored under the resolved storage root: `api/src/transport_matters/desktop_runtime.py:desktop_record_path` returns `storage_dir / runtime / desktop.json`. The log path is adjacent through `desktop_log_path`.

By default, storage is channel keyed. `api/src/transport_matters/storage_roots.py:default_storage_root` returns the active channel home unless `TRANSPORT_MATTERS_HOME` overrides it. Stable uses `.transport-matters`; preview uses `.transport-matters-preview` from `channel-specs.json`.

The record schema is `api/src/transport_matters/desktop_runtime.py:DesktopRuntimeRecord`. It stores channel, pid, proxy port, web port, cwd, storage dir, version, and `instance`. The default instance is `api/src/transport_matters/desktop_runtime.py:_DEFAULT_INSTANCE`, currently `channel`.

Detached launch is the only production path in this audit that writes this record. `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached` writes it before waiting for the backend. `run_desktop_launch`, `run_desktop_backend_server`, and Electron `startBackendAndCreateWindow` do not write a record themselves.

### Work directory

`--work-dir` is data and UI context, not channel identity. `api/src/transport_matters/cli/desktop_cmd.py:_resolve_work_dir` validates it. `api/src/transport_matters/desktop_event.py:build_backend_started_event` uses it to derive the workspace owner query and route URL. It does not choose the channel, port, or default record path.

An explicit `--storage-dir` can override the default channel home. In that case the record path follows the override, and `discover_desktop_runtime` treats a record whose stored channel differs from the requested channel as `unhealthy`.

## Relaunch behavior matrix

Assumptions for the matrix:

1. "Healthy same channel" means a valid channel record exists, the recorded pid is alive, `/health` is live, and `/api/meta` is either the same channel or unavailable.
2. "Stale or dead" means the record exists but the pid is dead, or the recorded process refuses health connections. Current code classifies timeout, failed health, and channel mismatch as `wedged` or `unhealthy`, not ordinary stale.
3. "Non TM process" means the fixed port has a listener without a usable Transport Matters runtime record for that channel.

| Launch path | Fixed port free | Healthy same channel instance holds the port | Stale or dead recorded instance | Non TM process holds the port |
|---|---|---|---|---|
| Foreground CLI | Starts the backend in the foreground and launches Electron. No runtime record is written. | Fails with raw `raise_port_in_use` because the path never calls `discover_desktop_runtime`. This is the foreground gap. | Ignores the record. If the port is free, it starts and leaves record ownership unchanged. If the port is still occupied, it raw errors. | Raw `raise_port_in_use`. No reclaim attempt. |
| Detached CLI | `discover_desktop_runtime` returns absent, then `prepare_desktop_launch` starts a detached `_desktop-backend`, writes the record, waits for readiness, and launches Electron. | Attaches a viewer through `_attach_existing_desktop`. With `--force-restart`, it kills the recorded pid through `force_restart_desktop_runtime_or_exit`, then starts fresh. | Dead pid becomes `stale`; discovery unlinks the record and recovery continues to start. Refused health becomes `not-serving`; recovery stops the recorded pid, then starts fresh. Timeout, failed health, or channel mismatch refuses unless `--force-restart` is set. | If there is no usable channel record, discovery is absent and `_resolve_backend_ports` raw errors. If a record exists but probes as `unhealthy`, the path refuses rather than killing. |
| Electron direct app relaunch | If no live record exists, `resolveBackendStartupOptions` uses channel spec ports and `startBackendAndCreateWindow` spawns `_desktop-backend`. No record is written in this Electron owned path. | If a valid detached record exists, `liveRuntimeRouteUrl` attaches through `registerHostedDesktopLifecycle`. If the existing backend has no record, Electron sees absent status, spawns a child, and the child raw errors on the occupied port. | Dead pid status unlinks the record in discovery, then Electron spawns a child if the port is free. Refused, wedged, or unhealthy statuses do not run recovery; Electron still spawns a child, so the old pid is not killed. If the port remains bound, the child raw errors. | Status is absent, so Electron spawns a child and the child raw errors. No reclaim attempt. |
| `just channel-restart` | Builds UI and desktop, `channel stop` reports nothing running, `ensure-db` runs, detached CLI starts. | `channel stop` kills the pid from the channel record through `stop_desktop_record`, then detached CLI starts fresh. This is the existing stop then restart precedent. | `channel stop` unlinks a dead record or kills the recorded pid. Detached CLI then starts if the port is free. | `channel stop` has no record to stop, so it reports nothing running. Detached CLI then raw errors on the occupied port. |

## Channel restart precedent

The root `justfile:channel-restart` does four things in order:

1. Builds `www` and `desktop`.
2. Runs `transport-matters channel stop <channel>`.
3. Runs `transport-matters channel ensure-db <channel>`.
4. Runs `TRANSPORT_MATTERS_CHANNEL=<channel> transport-matters desktop --channel <channel> ...`.

`api/src/transport_matters/cli/channel_cmd.py:stop` computes `desktop_record_path(default_storage_root(spec.id))` and calls `api/src/transport_matters/desktop_runtime.py:stop_desktop_record`. That stop primitive reads the record, checks the pid, sends `SIGTERM`, waits, escalates to `SIGKILL`, and unlinks the record. It does not inspect the port owner. If there is no readable record, it cannot reclaim a non TM process.

There are no sibling root just recipes named `channel-start`, `channel-stop`, or `channel-status`; the sibling operations are CLI subcommands under `transport-matters channel`: `list`, `status`, `stop`, `ensure-db`, and `promote`.

## Electron mechanics

`desktop/src/main.ts` has no `app.requestSingleInstanceLock` or `second-instance` handler in the current tree. Multiple Electron launches are therefore handled by runtime discovery, not by Electron single instance arbitration.

There are two Electron modes:

1. Hosted viewer mode. `spawn_detached_electron` sets `TRANSPORT_MATTERS_DESKTOP_ROUTE_URL`. `registerDesktopLifecycleFromEnv` then calls `registerHostedDesktopLifecycle`, which opens that route and polls health. It does not spawn or reclaim a backend.
2. Direct app mode. With no route URL, `registerAppLifecycle` runs. It calls `resolveRuntimeStatus`. If the status is live, it opens a hosted window. Otherwise it calls `startBackendAndCreateWindow`, which spawns `transport-matters _desktop-backend` through `desktop/src/backendProcess.ts:launchBackendProcess` and waits for health.

The direct app stops only the backend child it spawned in the current Electron process. `desktop/src/main.ts:bindBackendQuitCleanup` calls `desktop/src/backendProcess.ts:stopBackendProcess` on `before-quit`. It does not stop a previously recorded runtime, and the child backend path does not write a runtime record.

## Exact gaps

1. Foreground CLI gap: `api/src/transport_matters/cli/__init__.py:desktop` dispatches `--foreground` directly to `run_desktop_launch`; `run_desktop_launch` calls `prepare_desktop_launch`; `prepare_desktop_launch` calls `_resolve_backend_ports`. No discovery or recovery occurs before the raw port check.
2. Detached live gap if relaunch means restart: `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached` treats `live` as attach. This is correct for idempotent attach semantics, but not for a relaunch contract that kills and restarts the channel backend.
3. Refuse versus reclaim branch: `run_desktop_detached` sends `stale` and `not-serving` to `recover_desktop_runtime_or_exit`, but sends `wedged` and `unhealthy` to `refuse_desktop_runtime_or_exit`. The classification is in `api/src/transport_matters/desktop_runtime.py:_status_for_probe_result` and in the channel mismatch checks inside `discover_desktop_runtime`.
4. Direct Electron gap: `desktop/src/main.ts:registerAppLifecycle` observes runtime status but does not call the Python recovery helpers. It spawns `_desktop-backend` for every non live status. The spawned child then raw errors if the fixed port is still occupied.
5. Record ownership gap: Electron direct backend launch and foreground launch do not write `DesktopRuntimeRecord`. A later relaunch cannot discover those processes as healthy same channel runtimes through `channel status`.
6. Non TM process gap: all existing stop and recovery helpers are record based. `stop_desktop_record` can kill a recorded pid, but no current code maps an occupied port back to an arbitrary process and decides to kill it.

## What would change to make every relaunch reclaim

1. Define one shared relaunch preflight in Python, before `_resolve_backend_ports`. It should take channel spec, storage root, route, cwd, and a policy: attach, reclaim recorded runtime, or refuse unknown owner.
2. Use that preflight from `run_desktop_launch` and `run_desktop_detached`. If owner direction is relaunch equals reclaim, the `live` branch should stop the recorded pid instead of attaching for the launch command. Attach can remain a distinct behavior if wanted.
3. Route direct Electron backend startup through the same Python relaunch path, or make Electron call a CLI command that performs record based stop before spawning the backend. Also make the Electron owned backend path write a runtime record, or avoid Electron owned backend launch and always use the CLI detached parent as the owner.
4. Keep `_desktop-backend` as a server child entrypoint, not the owner of reclaim policy. The parent launch path should reclaim before starting the child.
5. Decide the non TM policy explicitly. Existing code can reclaim recorded Transport Matters runtimes only. Killing arbitrary port owners would require a new port owner inspection seam, clear operator messaging, and safety boundaries. If non TM should not be killed, replace the raw `raise_port_in_use` with a typed "unowned fixed port" refusal after relaunch preflight.
6. Update `just channel-restart` only if the desired behavior exceeds record based stop. Today it is the clean precedent for record based reclaim: stop by channel record, ensure database, then launch detached.

## Verification performed

1. fmm topology confirmed the indexed project shape: `api`, `www`, and `desktop`.
2. fmm outlines and symbol reads were used for the launch, discovery, recovery, record, and Electron symbols cited above.
3. Direct justfile inspection confirmed `channel-restart` and absence of sibling root channel recipes.
4. Direct source search confirmed no Electron `requestSingleInstanceLock` or `second-instance` handler.
5. `git status --short` was clean before writing this report.
