# Transport Matters instance discovery spec

Date: 2026-06-23
Status: active spec
Scope: discovery seam, idempotent `desktop` launch, and dev proxy cleanup

## Summary

`transport-matters desktop` must become an idempotent channel operation. The launch command must first discover whether the requested channel already has a healthy desktop backend. If it does, the command opens a viewer onto that backend. If the record is stale, it recovers silently. If the pid is alive but the health URL refuses connections after debounce, it announces recovery and starts fresh. If the health URL times out after debounce, it refuses without killing the pid. If the fixed channel port is held by a non Transport Matters process, it refuses with a precise conflict.

Dynamic control plane ports remain deferred. The discovery seam must still store actual runtime ports so a later additive instance mode can use dynamic ports without changing the channel contract.

## Decisions

1. Keep fixed channel ports for `stable` and `preview` now.
   - `stable` and `preview` still derive default `proxyPort` and `webPort` from `api/src/transport_matters/channel-specs.json:channels`.
   - The channel identity remains `homeDir`, `databaseName`, `proxyPort`, `webPort`, Electron identity, user data, and badge, as modeled by `api/src/transport_matters/channel.py:ChannelSpec` and `desktop/src/env.ts:DesktopChannelSpec`.
2. Build discovery now.
   - The durable source is the existing desktop runtime record generalized from `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord`.
   - The bootstrap query surface is CLI JSON, because HTTP cannot be the first lookup when the caller does not know the port.
   - Add an HTTP echo after bootstrap so clients that already reached the backend can confirm the same runtime facts.
3. First consumer is idempotent desktop launch.
   - `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached` consults discovery before `api/src/transport_matters/cli/desktop_cmd.py:prepare_desktop_launch` performs port checks.
4. Defer dynamic instance launch.
   - Add an `instance` field now, with default value `channel`, so future `--instance` or director spawned instances can be additive.
   - Do not call `api/src/transport_matters/cli/ports.py:allocate_port_pair` for normal channel desktop starts in this slice.

## Existing facts to preserve

| Fact | Existing anchor |
| --- | --- |
| Channel defaults are fixed today | `api/src/transport_matters/channel.py:ChannelSpec.proxy_port`, `api/src/transport_matters/channel.py:ChannelSpec.web_port`, `api/src/transport_matters/channel-specs.json:channels` |
| Detached launch writes a runtime record | `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached`, `api/src/transport_matters/cli/desktop_runtime.py:write_desktop_record` |
| Record already stores actual ports | `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord.proxy_port`, `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord.web_port` |
| Live record validation already checks PID liveness | `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record`, `api/src/transport_matters/cli/desktop_runtime.py:is_pid_alive` |
| Channel list and stop already read the record | `api/src/transport_matters/cli/channel_cmd.py:list_channels`, `api/src/transport_matters/cli/channel_cmd.py:_desktop_pid`, `api/src/transport_matters/cli/channel_cmd.py:stop` |
| Hosted Electron already accepts a concrete route | `api/src/transport_matters/cli/desktop_cmd.py:build_backend_started_event`, `api/src/transport_matters/cli/desktop_cmd.py:spawn_detached_electron`, `desktop/src/main.ts:registerHostedDesktopLifecycle` |
| Electron can build a route for any web port | `desktop/src/window.ts:rendererUrlForPort` |
| HTTP health exists in the backend | `api/src/transport_matters/main.py:create_app`, `/health` route inside `create_app` |
| Electron health probing exists | `desktop/src/backendHealth.ts:backendHealthUrl`, `desktop/src/backendHealth.ts:isBackendHealthy`, `desktop/src/backendHealth.ts:waitForBackendHealth` |
| Existing metadata resolves cwd and channel after a client already has an address | `api/src/transport_matters/api/v1/meta.py:MetaResponse`, `api/src/transport_matters/api/v1/meta.py:get_meta`, `api/src/transport_matters/api/v1/meta.py:_build_meta_response` |
| Built `www` is same origin | `api/src/transport_matters/main.py:SpaStaticFiles`, `api/src/transport_matters/main.py:create_app`, `www/src/api.ts:apiUrl`, `www/src/api.ts:fetchMeta` |
| Vite dev proxy is the fixed port consumer | `www/vite.config.ts:server.proxy` |
| Run ports are already dynamic under the run tier | `api/src/transport_matters/run_manager.py:RunManager._prepare_request`, `api/src/transport_matters/run_manager.py:RunManager._captured_request`, `api/src/transport_matters/run_models.py:ManagedRunView.proxy_port`, `api/src/transport_matters/run_models.py:ManagedRunView.web_port` |

## Discovery surface contract

### Source of truth

Keep the file backed record as the source of truth because discovery must work before HTTP is reachable.

Existing source:

```text
api/src/transport_matters/cli/desktop_runtime.py:desktop_record_path
api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord
api/src/transport_matters/cli/desktop_runtime.py:write_desktop_record
api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record
```

New model, because the current record is enough for stop and list, but not enough for director bootstrap, health, versioning, or future instances:

```typescript
type DesktopRuntimeState =
  | "absent"
  | "live"
  | "stale"
  | "unhealthy"
  | "not-serving"
  | "wedged";
type DesktopRuntimeInstance = "channel" | string;

interface DesktopRuntimeStatus {
  schemaVersion: 2;
  state: DesktopRuntimeState;
  channel: string;
  instance: DesktopRuntimeInstance;
  pid: number | null;
  proxyPort: number | null;
  webPort: number | null;
  apiBaseUrl: string | null;
  healthUrl: string | null;
  defaultRouteUrl: string | null;
  cwd: string | null;
  storageDir: string;
  recordPath: string;
  logPath: string | null;
  startedAt: string | null;
  version: string | null;
  reason?: string;
}

interface DesktopRuntimeStatusResponse {
  runtime: DesktopRuntimeStatus;
}
```

Field bindings:

| Field | Binding |
| --- | --- |
| `schemaVersion` | new, because `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord.schema_version` currently describes only the persisted record |
| `state` | new, because `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record` returns record or none, without an addressable state |
| `channel` | `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord.channel` |
| `instance` | new, because channel singleton must remain the default while future dynamic instances need an additive key |
| `pid` | `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord.pid` |
| `proxyPort` | `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord.proxy_port` |
| `webPort` | `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord.web_port` |
| `apiBaseUrl` | derived from `api/src/transport_matters/cli/net.py:loopback_http_url` and `webPort` |
| `healthUrl` | derived from `api/src/transport_matters/cli/net.py:loopback_http_url` and `/health`, matching `desktop/src/backendHealth.ts:backendHealthUrl` |
| `defaultRouteUrl` | derived with `api/src/transport_matters/cli/desktop_cmd.py:build_backend_started_event` using the requested route |
| `cwd` | new persisted field, because `api/src/transport_matters/cli/desktop_cmd.py:build_backend_started_event` derives workspace routing from cwd, while `DesktopRuntimeRecord` does not store it |
| `storageDir` | `api/src/transport_matters/cli/desktop_runtime.py:desktop_record_path` parent, plus launch storage from `api/src/transport_matters/cli/desktop_cmd.py:prepare_desktop_launch` |
| `recordPath` | `api/src/transport_matters/cli/desktop_runtime.py:desktop_record_path` |
| `logPath` | `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord.log_path` |
| `startedAt` | `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord.started_at` |
| `version` | new, because the record does not expose the package version imported by `api/src/transport_matters/cli/desktop_cmd.py` |
| `reason` | new, because stale, invalid, and unhealthy records need machine readable diagnostics |

### Functions

Add these to `api/src/transport_matters/cli/desktop_runtime.py`, because the existing record helpers already own runtime record parsing and cleanup:

```typescript
// Python shape, expressed as a typed contract.
function discover_desktop_runtime(input: {
  channel: string;
  storageDir: string;
  route: "canvas" | "canvas-lab";
  cwd: string;
  healthTimeoutMs?: number; // legacy compatibility
  livenessPolicy?: {
    attempts?: number; // default 3
    perProbeTimeoutS?: number; // default 2.0
    backoffS?: number; // default 0.2
  };
}): DesktopRuntimeStatus;

function desktop_runtime_status_to_json(status: DesktopRuntimeStatus): DesktopRuntimeStatusResponse;
```

Implementation notes:

1. Use `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record` as the low level reader.
2. Probe `GET /health` through `api/src/transport_matters/desktop_runtime.py:probe_desktop_liveness`, not a single TCP connect.
3. Debounce liveness with multiple attempts. Defaults are three attempts, two seconds per probe, and a short backoff. The policy is injectable for tests and future operators.
4. Preserve the distinction between refused and timeout. Refused means the recorded pid is not serving the health URL. Timeout means something is listening but slow, busy, or wedged.
5. Optionally request `GET /api/meta` when the backend is reachable and read `api/src/transport_matters/api/v1/meta.py:MetaResponse.channel` to verify the reported channel matches the requested channel. A mismatch returns `unhealthy` with `reason: "channel_mismatch"`.
6. Do not trust stored URLs. Compute `apiBaseUrl`, `healthUrl`, and `defaultRouteUrl` from ports and route helpers.
7. Keep invalid JSON and wrong schema as `absent` for legacy compatibility in the low level reader, but the new status helper should return `stale` with a reason before cleanup when it can safely identify a stale record.

### CLI surface

Add a shipped query surface under channel commands:

```typescript
// transport-matters channel status [channel] --json
interface ChannelStatusJsonResponse {
  runtime: DesktopRuntimeStatus;
}
```

Bindings:

| Capability | Binding |
| --- | --- |
| Resolve channel | `api/src/transport_matters/cli/channel_cmd.py:_resolve_channel_or_exit`, `api/src/transport_matters/channel.py:resolve_channel_spec` |
| Resolve channel storage | `api/src/transport_matters/storage_roots.py:default_storage_root`, as already used by `api/src/transport_matters/cli/channel_cmd.py:_desktop_pid` and `api/src/transport_matters/cli/channel_cmd.py:stop` |
| Read status | new, calls `api/src/transport_matters/cli/desktop_runtime.py:discover_desktop_runtime` |
| Human list remains | `api/src/transport_matters/cli/channel_cmd.py:list_channels` |

`channel list` should keep human output, but it should print live ports from `DesktopRuntimeStatus.proxyPort` and `DesktopRuntimeStatus.webPort` when state is `live`. Configured ports remain displayed only when no live record exists.

### HTTP surface

Add a sibling runtime endpoint rather than overloading `/api/meta`:

```typescript
// GET /v1/desktop-runtime
interface GetDesktopRuntimeResponse {
  runtime: DesktopRuntimeStatus;
}
```

This endpoint is new, because `api/src/transport_matters/api/v1/meta.py:MetaResponse` describes the reached backend cwd, workspace, run id, channel, badge, and harnesses, but it does not bootstrap or enumerate the runtime address. The HTTP endpoint uses the same serializer as the CLI. It exists for confirmation and in app clients after they already reached the backend.

Recommended placement:

| Capability | Binding |
| --- | --- |
| Router include | `api/src/transport_matters/main.py:create_app` |
| Current settings | `api/src/transport_matters/config.py:get_settings` via `api/src/transport_matters/api/v1/meta.py:get_meta` pattern |
| Channel metadata | `api/src/transport_matters/channel.py:resolve_channel_spec` |
| Response model style | `api/src/transport_matters/api/v1/meta.py:MetaResponse` |

## Writer lifecycle

`api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached` remains the writer for detached Python launched desktop backends.

1. Resolve channel through `transport_matters.channel:activate_channel`.
2. Run discovery before preparing the launch.
3. If no reusable runtime exists, call `api/src/transport_matters/cli/desktop_cmd.py:prepare_desktop_launch`.
4. Spawn `_desktop-backend` with `api/src/transport_matters/cli/desktop_cmd.py:_build_desktop_backend_command`.
5. Persist record immediately after spawn through `api/src/transport_matters/cli/desktop_runtime.py:write_desktop_record`.
6. Wait for readiness through `api/src/transport_matters/cli/desktop_cmd.py:_wait_for_detached_backend_or_exit` and `api/src/transport_matters/cli/net.py:wait_for_port_ready`.
7. Open Electron through `api/src/transport_matters/cli/desktop_cmd.py:spawn_detached_electron`.

Schema change to `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord`:

```typescript
interface PersistedDesktopRuntimeRecordV2 {
  schemaVersion: 2;
  channel: string;
  instance: "channel";
  pid: number;
  proxyPort: number;
  webPort: number;
  cwd: string;
  storageDir: string;
  logPath: string;
  startedAt: string;
  version: string;
}
```

Backward compatibility for v1 records is only operational compatibility for local stale files. External compatibility is not required pre release. Parse v1 records so existing running stable and preview instances can be discovered once during rollout.

## Idempotent `desktop` behavior

### State machine

```text
requested channel + storage dir
  -> discover runtime
    -> live and healthy: attach viewer
    -> stale: cleanup record, then start
    -> not-serving: announce refused health URL, recover recorded process, then start
    -> wedged: refuse; do not terminate the recorded pid
    -> unhealthy: refuse unless the user explicitly force restarts
    -> absent: start
  -> during start, fixed channel port held by non TM process: refuse
```

### Branch contracts

| Branch | Behavior | Anchors |
| --- | --- | --- |
| live and healthy | Build a route event with `record.webPort`, then call hosted Electron. Do not spawn `_desktop-backend`. | `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record`, `api/src/transport_matters/cli/desktop_cmd.py:build_backend_started_event`, `api/src/transport_matters/cli/desktop_cmd.py:spawn_detached_electron` |
| stale | Unlink stale record and run the normal start path. This is the only silent auto recovery. | `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record`, `api/src/transport_matters/cli/desktop_runtime.py:stop_desktop_record`, `api/src/transport_matters/cli/desktop_cmd.py:prepare_desktop_launch` |
| not-serving | Announce channel, pid, and health URL, stop the recorded process, unlink, then start. Refused connections mean no backend is serving the recorded URL. | `api/src/transport_matters/cli/desktop_recovery.py:recover_desktop_runtime_or_exit`, `api/src/transport_matters/cli/desktop_runtime.py:stop_desktop_record` |
| wedged | Refuse without sending a signal. Error text must name channel, pid, URL, `transport-matters desktop --force-restart`, and `transport-matters doctor`. | `api/src/transport_matters/cli/desktop_recovery.py:refuse_desktop_runtime_or_exit` |
| unhealthy | Refuse without sending a signal unless explicit force restart is requested. | `api/src/transport_matters/cli/desktop_recovery.py:refuse_desktop_runtime_or_exit` |
| force restart | The explicit user authorized path. Terminate the recorded pid with SIGTERM, escalate to SIGKILL through `stop_desktop_record` if needed, unlink, then start. | `transport-matters desktop --force-restart`, `api/src/transport_matters/cli/desktop_recovery.py:force_restart_desktop_runtime_or_exit` |
| absent | Start normally with channel defaults. | `api/src/transport_matters/cli/desktop_cmd.py:prepare_desktop_launch`, `api/src/transport_matters/cli/desktop_cmd.py:_resolve_backend_ports` |
| non TM listener | Use the existing pinned port refusal. | `api/src/transport_matters/cli/net.py:port_in_use`, `api/src/transport_matters/cli/net.py:raise_port_in_use` |

Healthy means:

1. Record parses and channel matches.
2. PID is alive according to `api/src/transport_matters/cli/desktop_runtime.py:is_pid_alive`.
3. `GET /health` succeeds after the debounced liveness policy.
4. If `/api/meta` is reachable, `api/src/transport_matters/api/v1/meta.py:MetaResponse.channel` matches the requested channel.

Liveness policy:

1. A single probe never changes state.
2. Only an all-refused debounce becomes `state: "not-serving"` with `reason: "health_probe_refused"`.
3. Timeout after debounce becomes `state: "wedged"` with `reason: "health_probe_timeout"`.
4. Any timeout in a failed debounce dominates refused or generic failure because killing a slow but listening backend is unsafe.
5. Mixed non-timeout failures are ambiguous and must refuse without killing the pid.
6. Transient timeout followed by a healthy probe is live and must not kill or restart the backend.

The attach event reuses `api/src/transport_matters/cli/desktop_cmd.py:build_backend_started_event` so workspace routing remains identical to a fresh launch. The only difference is that `webPort` comes from `DesktopRuntimeStatus.webPort` rather than `DesktopLaunchPlan.web_port`.

### Error format

CLI errors keep the current Typer style. For machine surfaces, use the existing API error shape:

```typescript
interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}
```

New HTTP error codes:

| Code | Meaning |
| --- | --- |
| `desktop_runtime_unavailable` | Status could not be read due to a filesystem permission error |
| `desktop_runtime_invalid` | Record schema is invalid and could not be normalized |

Normal absent, stale, not-serving, wedged, and unhealthy states return HTTP 200 with `runtime.state`; they are discovery facts, not transport failures.

## Consumer migration

### CLI and director

The director consumes `transport-matters channel status <channel> --json` first. This is the bootstrap surface for MCP or CLI adapters because it does not require the director to know an HTTP port.

The human `transport-matters desktop` command consumes the same helper through `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached`.

### Electron

Normal Python launched desktop keeps using `TRANSPORT_MATTERS_DESKTOP_ROUTE_URL` set by `api/src/transport_matters/cli/desktop_cmd.py:spawn_detached_electron`. `desktop/src/main.ts:registerDesktopLifecycleFromEnv` already chooses hosted mode when `desktop/src/env.ts:ENV.DESKTOP_ROUTE_URL` is present.

Soft migration for direct Electron startup:

1. Change `desktop/src/main.ts:resolveBackendStartupOptions` to prefer discovered runtime status for the selected channel before falling back to `desktop/src/env.ts:DesktopChannelSpec.proxyPort` and `desktop/src/env.ts:DesktopChannelSpec.webPort`.
2. Keep explicit `desktop/src/env.ts:ENV.PROXY_PORT` and `desktop/src/env.ts:ENV.WEB_PORT` as operator pins.
3. Keep `desktop/src/window.ts:rendererUrlForPort` as the URL constructor.
4. Keep `desktop/src/window.ts:DEFAULT_WEB_PORT` only as a test and last resort fallback.

The TypeScript status reader is new, because no current desktop symbol reads the Python runtime record. If this adds too much duplication, direct Electron startup can shell out to `transport-matters channel status --json` and parse the shared CLI schema.

### Web app

Shipped `www` needs no discovery. It remains same origin:

| Behavior | Anchor |
| --- | --- |
| Backend serves built SPA | `api/src/transport_matters/main.py:SpaStaticFiles`, `api/src/transport_matters/main.py:create_app` |
| Browser API calls are relative | `www/src/api.ts:apiUrl`, `www/src/api.ts:fetchMeta` |

Retire the dev only fixed proxy in `www/vite.config.ts:server.proxy`.

New dev contract:

```text
TRANSPORT_MATTERS_DEV_API_BASE_URL=http://127.0.0.1:8788 pnpm dev
```

`www/vite.config.ts:server.proxy` reads `TRANSPORT_MATTERS_DEV_API_BASE_URL`; if absent, it can retain `http://localhost:8788` for one release as a warning fallback, then the fallback is removed. A dev wrapper can run `transport-matters channel status stable --json`, extract `runtime.apiBaseUrl`, export the env var, then launch Vite.

## Reuse map

| Existing seam | Use |
| --- | --- |
| `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord` | Extend to v2 record fields |
| `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record` | Low level compatibility reader inside the new discovery helper |
| `api/src/transport_matters/cli/desktop_runtime.py:write_desktop_record` | Persist v2 records atomically |
| `api/src/transport_matters/cli/desktop_runtime.py:stop_desktop_record` | Recover stale records, announced not-serving records, and explicit force restarts |
| `api/src/transport_matters/cli/net.py:port_in_use` | Keep non TM listener detection |
| `api/src/transport_matters/cli/net.py:raise_port_in_use` | Keep pinned port refusal for real conflicts |
| `api/src/transport_matters/cli/net.py:wait_for_port_ready` | CLI startup readiness check |
| `api/src/transport_matters/cli/desktop_cmd.py:build_backend_started_event` | Build attach route without duplicating route query logic |
| `api/src/transport_matters/cli/desktop_cmd.py:spawn_detached_electron` | Open a hosted viewer for existing backend |
| `api/src/transport_matters/cli/ports.py:allocate_port_pair` | Do not use for normal channel desktop now. Reserve for future additive instance launch |
| `api/src/transport_matters/run_manager.py:RunManager` | Reuse the pattern, not the class. It is process resident and scoped to managed runs |

## Forward compatibility for dynamic instances

The discovery seam generalizes from per channel record to instance registry without changing channel launch behavior.

Current record path:

```text
{channelHome}/runtime/desktop.json
```

Forward compatible registry path:

```text
{channelHome}/runtime/instances/{instance}.json
```

Compatibility rule:

1. `desktop.json` remains the channel singleton alias.
2. `instances/channel.json` can mirror or replace it in a later migration.
3. Future `transport-matters desktop --instance <id>` writes `instances/<id>.json` with `instance: <id>` and may use `api/src/transport_matters/cli/ports.py:allocate_port_pair`.
4. Existing `stable` and `preview` commands keep resolving `instance: "channel"` unless the caller opts into instance mode.

This lets the future director enumerate instances with one query while preserving the stable channel contract for humans.

## Tests

### New or changed tests

| Test area | Required coverage |
| --- | --- |
| `api/src/transport_matters/cli/test_desktop_runtime.py` | v2 record write and read, v1 compatibility, invalid schema status, stale cleanup, failed, refused, timeout, and live health classifications |
| `api/src/transport_matters/cli/test_channel_cmd.py` | `channel status --json` returns typed absent and live payloads, `channel list` prints live record ports when present |
| `api/src/transport_matters/cli/test_desktop.py` and `api/src/transport_matters/cli/test_desktop_idempotent.py` | live healthy record attaches without spawning backend, stale record starts normally, refused health recovers with an announcement, transient timeout retries then attaches, persistent timeout refuses without a signal, `--force-restart` kills then restarts, non TM listener still exits through pinned port refusal |
| `desktop/src/main.test.ts` | direct startup prefers discovered port or route, hosted lifecycle still opens Python supplied route without backend startup |
| `desktop/src/window.test.ts` | `rendererUrlForPort` remains the only URL constructor for runtime ports |
| `www/src/api.test.ts` or Vite config test | dev proxy reads `TRANSPORT_MATTERS_DEV_API_BASE_URL` |
| `api/src/transport_matters/api/v1/test_desktop_runtime.py` | HTTP endpoint returns `GetDesktopRuntimeResponse`, absent and live states are HTTP 200, filesystem errors map to `ApiError` |

### Canonical gates

The repo root gates are the justfile recipes, verbatim:

```text
check:
    cd "{{desktop_dir}}" && just check
    cd "{{www_dir}}" && just check
    cd "{{api_dir}}" && just check
```

```text
test:
    cd "{{desktop_dir}}" && just test
    cd "{{www_dir}}" && just test
    cd "{{api_dir}}" && just test
```

Final verification for the full slice is:

```bash
just check
just test
```

Focused inner loops are allowed while building, but they do not replace the root gates.

## Slice plan

### Slice 1: Discovery seam

Deliverables:

1. Extend `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord` to v2.
2. Add `api/src/transport_matters/cli/desktop_runtime.py:discover_desktop_runtime` as the single status helper.
3. Add `transport-matters channel status [channel] --json` in `api/src/transport_matters/cli/channel_cmd.py`.
4. Add `GET /v1/desktop-runtime` using the same response model.
5. Update `api/src/transport_matters/cli/channel_cmd.py:list_channels` to prefer live ports.

Independent value: director and humans can query the current runtime without starting anything.

### Slice 2: Idempotent desktop launch

Deliverables:

1. Change `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached` to call `api/src/transport_matters/cli/desktop_runtime.py:discover_desktop_runtime` first.
2. Live healthy status opens hosted Electron through `api/src/transport_matters/cli/desktop_cmd.py:spawn_detached_electron`.
3. Stale statuses recover before start.
4. Refused health recovers only with an explicit warning.
5. Timeout and unhealthy statuses refuse without a signal unless `--force-restart` is set.
6. Non TM port conflicts still flow through `api/src/transport_matters/cli/net.py:raise_port_in_use`.

Independent value: rerunning `transport-matters desktop` attaches to the existing channel backend instead of failing on its own port.

### Slice 3: Consumer cleanup

Deliverables:

1. Change `desktop/src/main.ts:resolveBackendStartupOptions` so direct Electron startup prefers discovered runtime status.
2. Keep `desktop/src/main.ts:registerDesktopLifecycleFromEnv` hosted route behavior unchanged.
3. Change `www/vite.config.ts:server.proxy` to read `TRANSPORT_MATTERS_DEV_API_BASE_URL`.
4. Add or update a dev wrapper to export that env var from `transport-matters channel status --json`.

Independent value: fixed `8788` becomes a channel default, not a dev client constant.

## Non goals

- No dynamic default ports for `stable` or `preview`.
- No free port fallback when a non TM process owns the channel port.
- No general N channel model.
- No reuse of `api/src/transport_matters/run_manager.py:RunManager` as the desktop registry.
- No UI only discovery logic.
