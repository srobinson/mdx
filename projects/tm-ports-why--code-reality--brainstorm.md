# Transport Matters desktop ports, code reality brainstorm

Date: 2026-06-23  
Repo: `transport-matters` at `e3aaecf12905`  
Mode: read only code analysis, no code writes

## 1. Does the premise hold in code?

Partly. The observed failure is real, but the deeper problem is that `desktop` treats a channel as a fixed socket address while the canvas run system already treats ports as per run allocation details.

Facts:

- `api/src/transport_matters/channel-specs.json` gives `stable` fixed `proxyPort` `8787` and `webPort` `8788`, and `preview` fixed `8797` and `8798`.
- `api/src/transport_matters/channel.py:ChannelSpec` makes proxy and web ports first class channel fields.
- `api/src/transport_matters/cli/desktop_cmd.py:_resolve_backend_ports` uses `ChannelSpec.proxy_port` and `ChannelSpec.web_port` unless a test or caller injects an allocator. Normal `transport-matters desktop` does not inject one.
- `api/src/transport_matters/cli/__init__.py:desktop` exposes `--web-port`, but not `--proxy-port`, then dispatches to `run_desktop_detached` by default.
- `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached` writes `DesktopRuntimeRecord` with the actual pid, proxy port, web port, and log path. That record already supports actual runtime ports.
- `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record` validates live records, but desktop launch does not consult it before fixed port checks.
- Live local evidence matches the code path: `~/.transport-matters/runtime/desktop.json` records stable pid `86546`, proxy `8787`, web `8788`; `http://127.0.0.1:8788/health` returns ok.

The canvas path is different:

- `api/src/transport_matters/run_models.py:SpawnRun` defaults `proxy_port=None`, `web_port=None`, and `web_runtime=external`.
- `api/src/transport_matters/api/v1/run_routes.py:_spawn_request` does not set proxy or web ports for canvas spawned runs.
- `api/src/transport_matters/run_manager.py:RunManager._captured_request` forwards those `None` ports into `CapturedRunRequest`.
- `api/src/transport_matters/run_manager.py:RunManager._prepare_request` routes external runtime runs to `prepare_shared_captured_run` and never falls back to per run mitmdump when the shared proxy is unavailable.
- `api/src/transport_matters/captured_run_context.py:build_captured_run_context` calls `prepare_launch` with `use_channel_defaults=False` from both `prepare_captured_run` and `prepare_shared_captured_run`.
- `api/src/transport_matters/cli/launch_runtime.py:resolve_launch_ports` dynamically calls `allocate_port_pair` when `use_channel_defaults=False`. For external web runtime, it returns a dynamic proxy port and no web port.
- `api/src/transport_matters/shared_proxy/run_preparation.py:_binding_from_context` registers that dynamic proxy port as the run's `listen_port`.
- `api/src/transport_matters/shared_proxy/subprocess.py:SharedProxySubprocess.register_listener` applies a new mitmproxy mode for that listener and waits for TCP readiness.

So yes, there is already a dynamic per run port model in the same product. The fixed desktop channel port model is inconsistent with the canvas run model. The inconsistency is not only theoretical: the desktop backend exists to host the canvas that launches dynamic per run listeners.

Important nuance: standalone terminal launches still use channel defaults today.

- `api/src/transport_matters/captured_run.py:run_captured_run_on_local_tty` calls `build_captured_run_context` with `use_channel_defaults=True`.
- `api/src/transport_matters/cli/codex_cmd.py:run_codex` calls `prepare_launch` with the default channel behavior.
- `api/src/transport_matters/cli/launch_runtime.py:resolve_launch_ports` treats active channel defaults as pinned when channel defaults are enabled.

That means the current code has at least two port models:

1. Canvas runs: dynamic per run proxy listener, no per run web UI.
2. Desktop and standalone channel launches: fixed channel proxy and web ports, unless explicit flags or injected tests override them.

## 2. Does anything need stable ports across restarts?

No durable product identity in the inspected code requires a stable port across restarts.

The things that look like they might need stability do not actually need the port itself:

- Persisted live record: `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord` stores actual ports. It can store dynamic ports without schema change.
- Channel management: `api/src/transport_matters/cli/channel_cmd.py:list_channels`, `_desktop_pid`, and `stop` already resolve live state through the runtime record. The list display currently prints spec ports, but it can print actual live record ports instead.
- Electron identity: `desktop/src/main.ts:applyChannelIdentity` and `desktop/src/env.ts:resolveDesktopChannelSpec` use app name, app id, user data, dock icon, and badge. They do not need a fixed port.
- Hosted Electron launched by Python: `api/src/transport_matters/cli/desktop_cmd.py:build_backend_started_event` passes a concrete `routeUrl` built from the actual web port. `desktop/src/main.ts:registerDesktopLifecycleFromEnv` chooses hosted lifecycle when that route URL is present.
- Window URL building: `desktop/src/window.ts:rendererUrlForPort` accepts any web port.

Stability is currently a convenience and a discovery shortcut, not a product invariant. The hard consumers are hard because the current model made ports part of the channel contract, not because the rest of the architecture needs that contract.

Blast radius from literal port references, excluding generated desktop dist and bundled web assets:

- 40 files contain `8787`, `8788`, `8797`, or `8798`.
- 9 source or tool files carry runtime or developer tooling assumptions: `channel-specs.json`, `config.py`, `desktop/src/main.ts`, `desktop/src/window.ts`, `www/vite.config.ts`, `api/justfile`, `scripts/local-dev-mode.sh`, `cli/_helpers.py`, and `cli/bind_failure.py`.
- 25 test files assert or fixture those assumptions.
- 5 doc or example files document the assumptions: `README`, `api/README`, `docs/CHANNELS.md`, `api/.env.example`, `settings.example.toml`, and install text.
- `api/uv.lock` also matched and should be ignored for port model decisions.

Hard consumers to treat deliberately:

- `api/src/transport_matters/cli/desktop_cmd.py:_resolve_backend_ports` is the runtime decision point for desktop.
- `desktop/src/main.ts:resolveBackendStartupOptions` is the direct Electron owned backend path when no Python hosted route is supplied.
- `www/vite.config.ts:server.proxy` assumes the API is at `8788` during web dev.
- Tests such as `api/src/transport_matters/cli/test_desktop.py:test_desktop_channel_default_port_in_use_fails_fast` and `api/src/transport_matters/cli/test_start.py:test_start_channel_default_port_in_use_fails_fast` make fixed channel ports an asserted behavior.

Soft consumers:

- Docs and installer hints that tell humans to expect `8787` and `8788`.
- Local dev scripts that can be made explicit opt ins to fixed ports.
- Browser bookmarks to `127.0.0.1:8788`, if anyone has them. That is convenience, not stored product identity.

## 3. Options and trade offs

### Option A: detect live channel and attach, keep fixed ports

Behavior:

- Before port checks, use `read_live_desktop_record` for the active channel home.
- If the record is live and health responds, open hosted Electron against that record's web port.
- If no live record exists, keep fixed channel ports and fail on conflicts.

Pros:

- Smallest patch to the current documented model.
- Avoids starting a second backend for the same stable channel.
- Uses existing live record and hosted Electron route seams.

Cons:

- Keeps fixed socket address as channel identity.
- Leaves unrelated listeners on `8788` as false blockers.
- Leaves desktop inconsistent with dynamic canvas run listeners.
- Does not answer the owner's root question.

### Option B: dynamic desktop ports by default, attach to live channel first

Behavior:

- Treat channels as state and identity boundaries: home, DB, Electron identity, badge.
- Treat desktop ports as runtime allocation details.
- On `transport-matters desktop`, first check the channel's live `DesktopRuntimeRecord`.
- If live and healthy, open a hosted Electron window using the record's actual web port.
- If no live backend exists, allocate a fresh proxy and web pair, start the backend, write the actual ports into `DesktopRuntimeRecord`, and open the hosted route.
- Keep `--web-port` as an explicit pin for diagnostics or local dev. Either expose `--proxy-port` on `desktop` or make proxy dynamic whenever only web is pinned.

Pros:

- Makes desktop consistent with the RunManager and shared proxy model.
- Removes the common false blocker from unrelated processes on `8788`.
- Keeps stable and preview meaningful without binding them to socket numbers.
- Existing hosted route and runtime record seams already carry actual ports.

Cons:

- More tests and docs change because fixed ports are currently asserted.
- Direct Electron self start needs a matching allocation path or a deliberate decision to require Python hosted launch.
- Web dev proxy needs an explicit API target or a dev command that exports the chosen port.

### Option C: dynamic fallback only after fixed port conflict

Behavior:

- Try the channel fixed ports first.
- If busy, allocate free ports and continue.

Pros:

- Smaller than full model change.
- Avoids some failures.

Cons:

- Worst semantic shape. It keeps fixed ports as the supposed identity but silently violates that identity under pressure.
- If the busy port belongs to a live stable backend, this can start a second stable backend sharing home, DB, and Electron identity unless live attach happens first.
- Leaves channel list, docs, and dev proxy with unclear truth.

## 4. Recommendation

Choose Option B, with the live record preflight from Option A.

One line: `desktop` should allocate backend ports dynamically by default, but should attach to an already live channel record instead of starting a second backend for the same channel.

Why:

- The product already has dynamic per run listener allocation in `RunManager`, `prepare_shared_captured_run`, and `SharedProxySubprocess.register_listener`.
- A channel is already more than a port pair. It owns home, database, Electron identity, user data, dock identity, and badge.
- `DesktopRuntimeRecord` already stores actual ports. That is the right discovery seam for a resident backend.
- The hosted Electron path already accepts an actual route URL from Python.
- No inspected durable identity depends on `8788` surviving restart.

Smallest coherent implementation shape:

1. Add a desktop live channel preflight before backend allocation.
   - Anchor: `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record`.
   - Anchor: `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached`.
   - Anchor: `api/src/transport_matters/cli/desktop_cmd.py:build_backend_started_event`.
   - If live and healthy, open the hosted Electron route built from the requested workdir and `record.web_port`.

2. Make desktop default port resolution allocate, not read channel fixed ports.
   - Anchor: `api/src/transport_matters/cli/desktop_cmd.py:_resolve_backend_ports`.
   - Anchor: `api/src/transport_matters/cli/ports.py:allocate_port_pair`.
   - Keep pinned behavior only when the user supplies a port.

3. Change channel display from committed ports to live ports.
   - Anchor: `api/src/transport_matters/cli/channel_cmd.py:list_channels`.
   - Anchor: `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord`.
   - Stopped channels can show no live port or a configured preferred port if that field survives as a hint.

4. Decide direct Electron self start explicitly.
   - Anchor: `desktop/src/main.ts:resolveBackendStartupOptions`.
   - Anchor: `desktop/src/backendProcess.ts:buildBackendLaunch`.
   - Either allocate in Electron before spawning `_desktop-backend`, or make packaged app launch through the Python hosted route path. Do not keep a separate fixed port model here long term.

5. Update tests and docs as contract changes, not as afterthoughts.
   - Replace `test_desktop_channel_default_port_in_use_fails_fast` with dynamic allocation, live attach, stale record, and unrelated listener cases.
   - Keep fixed port assertions only for explicit pinned flags and standalone channel launches if those remain intentionally fixed.

## 5. What I would not do

- Do not only patch the error message. The failure is a model mismatch, not just poor wording.
- Do not silently start another stable backend on a free port while a stable live record exists.
- Do not adopt an arbitrary process on `8788`. Attach only when the channel runtime record is live and the backend is healthy.
- Do not delete channels. Delete fixed ports from the channel identity, not the channel concept.
- Do not keep dynamic allocation as an exceptional fallback after a fixed port failure. Make allocation the default for desktop if that is the chosen model.
- Do not preserve `8787` and `8788` in docs as guaranteed desktop addresses once runtime records become authoritative.

## Verification

Commands run:

```bash
git status --short
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  src/transport_matters/cli/test_desktop.py::test_desktop_channel_default_port_in_use_fails_fast \
  src/transport_matters/cli/test_captured_run.py::test_prepare_captured_run_retries_proxy_start_timeout_with_fresh_ports \
  src/transport_matters/shared_proxy/test_run_preparation.py::test_prepare_shared_captured_run_registers_binding_and_lease_deregisters \
  src/transport_matters/test_run_manager_shared_proxy.py::test_run_manager_routes_external_runs_to_shared_preparation
```

Observed result: 4 passed in 0.05s.
