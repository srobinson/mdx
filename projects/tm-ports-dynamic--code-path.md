# TM ports dynamic: code path

Status: read-only design, verified against `transport-matters` main at `e3aaecf` on 2026-06-23.

## Executive summary

Dynamic ports are feasible if the channel record becomes the addressability contract. The minimal path is dynamic-with-record-discovery: keep channel identity stable, allocate ports at process start, persist the chosen ports in a durable per-channel record, and make every external client discover the live address before it tries HTTP.

The blocker is not allocation. The blocker is that `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record` is internal plumbing today, while the director, direct Electron startup, and dev tooling still depend on fixed constants or already knowing the backend URL.

## Discovery seam

### Source of truth

Use the existing desktop runtime record as the source of truth:

- `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord` already stores `channel`, `pid`, `proxy_port`, `web_port`, `log_path`, and `started_at`.
- `api/src/transport_matters/cli/desktop_runtime.py:desktop_record_path` gives a deterministic record path under the channel home.
- `api/src/transport_matters/cli/desktop_runtime.py:write_desktop_record` already persists the selected ports atomically.
- `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record` already validates pid liveness and removes stale records.

The well-known address becomes the record location, not the TCP port. The record path is derived from the channel home. The channel id, database identity, app identity, and storage root stay stable.

### Minimal mechanism

Add a small discovery model in `api/src/transport_matters/cli/desktop_runtime.py`, for example `DesktopRuntimeStatus` plus `discover_desktop_runtime(...)`:

```text
state: absent | live | stale | unhealthy
channel
pid
proxyPort
webPort
apiBaseUrl: http://127.0.0.1:{webPort}
rendererUrl: http://127.0.0.1:{webPort}/canvas
recordPath
logPath
startedAt
```

`read_live_desktop_record` can remain the low-level primitive. The new status helper should layer on top and add optional backend health. A live pid with a dead backend should return `unhealthy`, not pretend discovery succeeded.

Expose that status in a shipped, process-external surface before flipping consumers:

1. CLI bootstrap: `transport-matters channel status <channel> --json` or `transport-matters desktop status --json`.
2. Director bootstrap: consume the same helper or the CLI JSON output.
3. HTTP echo: extend `api/src/transport_matters/api/v1/meta.py:MetaResponse`, or add a sibling runtime endpoint, to echo the runtime base URL once a client has already reached the backend.

The CLI or record-based surface is required. `/api/meta` is useful confirmation after connection, but cannot bootstrap dynamic discovery because a client must already know the port to call it.

## Consumer switch plan

| Consumer | Current coupling | Hard or soft | Can discover? | Required change |
| --- | --- | --- | --- | --- |
| `desktop/src/main.ts:resolveBackendStartupOptions` | Reads `ENV.PROXY_PORT` and `ENV.WEB_PORT`, otherwise falls back to `DesktopChannelSpec.proxyPort` and `DesktopChannelSpec.webPort`. | HARD | Yes, if the launcher passes a discovered route URL, or if Electron learns the record schema. | Prefer a discovered `DESKTOP_ROUTE_URL` or `DesktopRuntimeStatus` over channel constants. Keep explicit env ports as operator pins. Direct packaged Electron needs either a TS record reader or a Python CLI status child. |
| `desktop/src/window.ts:DEFAULT_WEB_PORT` | Fixed fallback is `8788`. | HARD for direct startup, SOFT once hosted launch is the only supported path. | Partly. `rendererUrlForPort` already accepts any port. | Demote `DEFAULT_WEB_PORT` to test or fallback only. Treat `rendererUrlForPort` as the dynamic primitive and require callers to pass the discovered `webPort` or route URL. |
| `www/vite.config.ts:server.proxy` | Dev server proxies `/api` to `http://localhost:8788`. | SOFT | No runtime discovery, because Vite proxy config is evaluated at dev server startup. | Read a dev env var such as `TRANSPORT_MATTERS_DEV_API_BASE_URL`, or use a dev wrapper that reads the runtime record before starting Vite. Shipped builds do not need this because the SPA uses relative `/api` against the backend origin. |
| `api/src/transport_matters/channel.py:ChannelSpec` | Treats `proxy_port` and `web_port` as required channel fields. | HARD | No. This is configuration, not runtime observation. | Keep channel identity fields, but rename ports to preferred defaults or remove them from runtime identity. Explicit user pins can still flow through launch options. |
| `api/src/transport_matters/cli/channel_cmd.py:list_channels` | Prints configured ports and only uses the live record for pid. | HARD for discovery UX, SOFT for table formatting. | Yes. It already imports the desktop runtime record path. | Print live `record.proxy_port` and `record.web_port` when a record is live. Add JSON status so the director does not scrape table text. |
| `api/src/transport_matters/config.py:Settings` | Defaults `proxy_port=8787` and `web_port=8788`. | HARD as backend fallback, SOFT as desktop source of truth. | No. Settings should receive runtime facts, not discover them. | Keep defaults for direct dev, tests, and explicit fallback. Dynamic desktop launch should inject selected ports through env or settings before backend startup. |
| Director, MCP, and external CLI clients | Need an address before any HTTP request. No current shipped discovery surface exists. | HARD | Only after the new status helper or CLI JSON exists. | Consume `DesktopRuntimeStatus` first, then call `/api/meta`, `/v1/runs`, or other HTTP APIs using the discovered `apiBaseUrl`. |

## Reuse from canvas `RunManager`

Yes, the product already has the dynamic allocation pattern. It lives in the captured run path, not the channel path.

Relevant working pieces:

- `api/src/transport_matters/cli/ports.py:allocate_port_pair` allocates two free loopback ports as a pair.
- `api/src/transport_matters/cli/launch_runtime.py:resolve_launch_ports` can allocate dynamically when `use_channel_defaults=False`.
- `api/src/transport_matters/shared_proxy/run_preparation.py:prepare_shared_captured_run` calls captured run setup with `use_channel_defaults=False`.
- `api/src/transport_matters/shared_proxy/run_preparation.py:_finish_shared_preparation` writes manifests, registers bindings, and returns the selected proxy and web ports in `CapturedRunSpawnSpec`.
- `api/src/transport_matters/run_manager.py:RunManager._prepare_request` routes external web runtime runs through shared preparation.
- `api/src/transport_matters/run_models.py:ManagedRun.view` includes `proxy_port` and `web_port` in the internal managed run view.

Adopt this as the channel launch pattern:

1. Allocate with `allocate_port_pair`.
2. Start backend with those selected ports.
3. Persist the selected ports before handing control to clients.
4. Expose a discovery view for the owner process.
5. Release any ownership or record on shutdown.

Do not reuse `RunManager` wholesale as the channel registry. It is process-resident and scoped to managed runs. The desktop channel needs a durable per-channel record that survives outside one backend process.

## The `www/vite` dev proxy problem

`www/vite.config.ts:server.proxy` is the one static proxy that cannot discover a runtime port after startup. That makes it a real blocker for dev ergonomics, but not a shipped product blocker.

Why it is dev-only:

- The built SPA is emitted into `api/src/transport_matters/www` and is served by the backend origin.
- `www/src/api.ts:apiUrl` returns relative paths when no `baseUrl` is supplied.
- `www/src/api.ts:fetchMeta` calls `/api/meta` relative to the current origin.
- Therefore a packaged Electron window opened to `http://127.0.0.1:{webPort}/canvas` does not need Vite or a fixed backend port.

Best dev answer:

1. Add an env-driven Vite proxy target, for example `TRANSPORT_MATTERS_DEV_API_BASE_URL=http://127.0.0.1:{webPort}`.
2. Add a tiny dev wrapper that calls the new discovery CLI, exports the env var, then starts `pnpm dev`.
3. Keep browser code relative. Avoid baking runtime discovery into the SPA for this case.

Alternatives:

- A runtime meta fetch cannot solve the bootstrap case because the browser has no backend origin until the proxy knows where to send `/api`.
- A stable loopback forwarder would hide dynamic ports behind another fixed port. That adds another process and recreates the fixed address contract under a different name.

## Blast radius

Focused files for the dynamic channel path: 16 files, about 4,617 LOC.

Core implementation files:

- `api/src/transport_matters/cli/desktop_runtime.py`
- `api/src/transport_matters/cli/desktop_cmd.py`
- `api/src/transport_matters/cli/channel_cmd.py`
- `api/src/transport_matters/channel.py`
- `api/src/transport_matters/config.py`
- `api/src/transport_matters/api/v1/meta.py`
- `api/src/transport_matters/cli/launch_runtime.py`
- `api/src/transport_matters/cli/ports.py`
- `api/src/transport_matters/shared_proxy/run_preparation.py`
- `api/src/transport_matters/run_manager.py`
- `desktop/src/main.ts`
- `desktop/src/backendProcess.ts`
- `desktop/src/window.ts`
- `desktop/src/env.ts`
- `www/vite.config.ts`
- `www/src/api.ts`

Port-related references are broader: 41 source or tool files with 394 matches when scanning `8787`, `8788`, `proxyPort`, `webPort`, `proxy_port`, and `web_port`, excluding tests and vendored build output. Much of that is captured-run plumbing that already supports dynamic ports.

Expected first implementation slice: 5 to 8 production files plus tests. The highest confidence slice can stay mostly in Python and avoid flipping the TypeScript direct-start path immediately.

## Minimal first slice

Goal: ship discovery safely before making ports dynamic by default everywhere.

1. Add `DesktopRuntimeStatus` and `discover_desktop_runtime(...)` in `api/src/transport_matters/cli/desktop_runtime.py`.
   - Build from `read_live_desktop_record`.
   - Include `apiBaseUrl` and `rendererUrl`.
   - Distinguish absent, live, stale, and unhealthy.
2. Add a JSON status command in `api/src/transport_matters/cli/channel_cmd.py`, or in the desktop command family.
   - Use the status helper.
   - Keep table output human-friendly.
   - Make JSON the director contract.
3. Make `api/src/transport_matters/cli/desktop_cmd.py` idempotent.
   - Live and healthy record opens a hosted Electron window using the discovered URL.
   - Stale or unhealthy record starts normally.
   - Unrelated listener still reports the precise bind failure.
4. Change the desktop launch default to allocate dynamic ports only inside the CLI path.
   - Reuse `api/src/transport_matters/cli/ports.py:allocate_port_pair`.
   - Preserve explicit `--proxy-port` and `--web-port` pins.
   - Persist the actual ports through `write_desktop_record` before clients attach.
5. Update `api/src/transport_matters/cli/channel_cmd.py:list_channels` to report live ports from the record.
6. Add tests around live record attach, stale record cleanup, JSON status, dynamic default allocation, and explicit pin behavior.

Second slice:

1. Switch `desktop/src/main.ts:resolveBackendStartupOptions` to prefer discovered status or an injected route URL over `DesktopChannelSpec` ports.
2. Demote `desktop/src/window.ts:DEFAULT_WEB_PORT` to fallback only.
3. Make `www/vite.config.ts:server.proxy` read an env-provided target and add a dev wrapper.
4. Decide whether `api/src/transport_matters/channel.py:ChannelSpec` ports become named defaults or disappear from runtime identity.

## Feasibility verdict

Feasible. The codebase already has dynamic port allocation and per-run recording through the canvas run path. The channel path needs one missing abstraction: a shipped discovery surface based on `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record`.

## Verification

Read-only verification used:

- `mcp__fmm.fmm_list_files` for repository topology.
- `mcp__fmm.fmm_read_symbol` for `DesktopRuntimeRecord`, `desktop_record_path`, `read_live_desktop_record`, `write_desktop_record`, `resolveBackendStartupOptions`, `DEFAULT_WEB_PORT`, `rendererUrlForPort`, `ChannelSpec`, `list_channels`, `Settings`, `MetaResponse`, `resolve_launch_ports`, `allocate_port_pair`, `prepare_shared_captured_run`, `_finish_shared_preparation`, `RunManager._prepare_request`, `RunManager._captured_request`, `ManagedRun.view`, `apiUrl`, and `fetchMeta`.
- `mcp__fmm.fmm_dependency_graph` for `desktop_runtime.py` and `channel.py` direct source dependents.
- `rg` and LOC counts for the blast radius summary.
