# Transport Matters port allocation scout

Scope: `transport-matters` at `main` `e3aaecf12905fd16d2ff142d350c49a3420932ad` on 2026-06-23.

Live evidence: `~/.transport-matters/runtime/desktop.json` records stable pid `86546`, proxy port `8787`, and web port `8788`. `ps` shows that pid running `transport-matters _desktop-backend ... --web-port 8788 --proxy-port 8787 --channel stable`. `curl http://127.0.0.1:8788/health` returns `{"status":"ok"}`. A fresh `transport-matters desktop` exits `2` with `web UI port 8788 is already in use`.

## Reuse Map

### Existing helpers

- `api/src/transport_matters/cli/net.py:port_in_use` probes loopback with `connect_ex`; this is the right reusable listener check.
- `api/src/transport_matters/cli/net.py:raise_port_in_use` owns the current standardized pinned port error.
- `api/src/transport_matters/cli/net.py:wait_for_port_ready` is the existing readiness probe used after backend launch.
- `api/src/transport_matters/cli/ports.py:allocate_port_pair` allocates a distinct free proxy and web pair.
- `api/src/transport_matters/cli/launch_runtime.py:resolve_launch_ports` centralizes normal agent launch port resolution and marks channel defaults as pinned.
- `api/src/transport_matters/cli/runner.py:run_client_with_retry` and `api/src/transport_matters/cli/bind_failure.py:handle_bind_failure` provide the retry loop for unpinned agent launch ports.
- `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record` reads and validates the per channel detached desktop pid record.
- `api/src/transport_matters/cli/channel_cmd.py:list_channels`, `api/src/transport_matters/cli/channel_cmd.py:_desktop_pid`, and `api/src/transport_matters/cli/channel_cmd.py:stop` already use the desktop record for list and stop behavior.

### Desktop path

- `api/src/transport_matters/cli/__init__.py:desktop` activates the channel and dispatches to `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached` unless `--foreground` is set.
- `api/src/transport_matters/cli/__init__.py:desktop` exposes `--web-port`, `--work-dir`, `--storage-dir`, `--channel`, and `--foreground`. It does not expose `--proxy-port`.
- `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached` activates the channel, calls `prepare_desktop_launch`, spawns `_desktop-backend`, writes a `DesktopRuntimeRecord`, waits for the web port, then starts Electron.
- `api/src/transport_matters/cli/desktop_cmd.py:prepare_desktop_launch` resolves the channel through `transport_matters.channel:resolve_channel_spec`, resolves ports through `_resolve_backend_ports`, builds env, builds the hidden backend command, and creates the Electron route event.
- `api/src/transport_matters/cli/desktop_cmd.py:_resolve_backend_ports` uses `ChannelSpec.proxy_port` and `ChannelSpec.web_port` when `allocate_port_pair_func` is `None`. It only uses dynamic allocation when a caller injects `allocate_port_pair_func`, which the CLI does not do.
- `api/src/transport_matters/cli/desktop_cmd.py:_resolve_backend_ports` does reuse `port_in_use` and `raise_port_in_use`, so the desktop path does not bypass the listener check. It bypasses the richer agent launch resolution and retry seam.
- `api/src/transport_matters/cli/desktop_cmd.py:serve_desktop_backend` only binds the web port via uvicorn. The proxy port is carried in env for downstream captured runs, but the desktop backend itself is not listening on 8787 in the observed stable process.
- `api/src/transport_matters/cli/desktop_cmd.py:spawn_detached_electron` can already launch Electron as a hosted viewer for an existing route URL.

### Channel model

- `api/src/transport_matters/channel.py:ChannelSpec` includes `proxy_port` and `web_port` as first class channel fields.
- `api/src/transport_matters/channel.py:_channel_specs` loads packaged `channel-specs.json` and caches the result.
- `api/src/transport_matters/channel.py:_build_channel_spec` maps JSON `proxyPort` and `webPort` into `ChannelSpec`.
- `desktop/src/env.ts:resolveDesktopChannelSpec` reads the copied channel spec in Electron and chooses the active channel.
- `desktop/src/main.ts:resolveBackendStartupOptions` falls back to channel proxy and web ports when env does not override them.
- `desktop/src/window.ts:rendererUrlForPort` can build a hosted URL for any web port.

## Quality Map

### Current failure mode

`transport-matters desktop` sees the stable web listener and reports a generic port conflict. It does not check `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record` first, so it cannot distinguish an unrelated process from the already running stable desktop backend. The repo already has enough channel runtime state to say “stable is already running at http://127.0.0.1:8788” or to attach a hosted viewer.

### Port stability assumptions

Channel defaults are intended to be stable. `api/src/transport_matters/cli/launch_runtime.py:resolve_launch_ports` treats channel defaults as pinned, and `api/src/transport_matters/cli/test_start.py:test_start_channel_default_port_in_use_fails_fast` asserts fast failure for a busy preview channel port. `api/src/transport_matters/cli/test_desktop.py:test_desktop_channel_default_port_in_use_fails_fast` asserts the same behavior for desktop. `docs/CHANNELS.md` documents stable as 8787 and 8788, and preview as 8797 and 8798. `www/vite.config.ts` proxies dev API calls to 8788. Dynamic channel ports would require a larger product decision because URLs, dev tooling, and test contracts assume stable channel addresses.

### Duplication and definition sites

Authoritative or default copies found:

- `api/src/transport_matters/channel-specs.json`: stable `proxyPort` 8787, stable `webPort` 8788, preview `proxyPort` 8797, preview `webPort` 8798.
- `api/src/transport_matters/config.py:Settings`: `proxy_port` default 8787 and `web_port` default 8788. These still feed direct settings users such as `api/src/transport_matters/addon_runtime.py`, `api/src/transport_matters/cli/diagnose.py`, `api/src/transport_matters/cli/runs_health.py`, and `api/src/transport_matters/__main__.py` when env does not override them.
- `desktop/src/main.ts:DEFAULT_PROXY_PORT`: fallback 8787.
- `desktop/src/window.ts:DEFAULT_WEB_PORT`: fallback 8788.
- `api/src/transport_matters/settings.example.toml`: channel comments list stable 8787 and 8788, preview 8797 and 8798.
- `api/.env.example`: default proxy and web env comments list 8787 and 8788.
- `api/src/transport_matters/cli/_helpers.py:_sample_manifest`: test helper defaults 8787 and 8788.
- `scripts/local-dev-mode.sh`: local dev command pins 8787 and 8788.
- `scripts/install.sh`: installed usage hints reference 8787 and 8788.
- `api/README.md`: usage text references 8787 and 8788.
- `api/justfile`: dev mitmdump recipes bind 8787.
- `www/vite.config.ts`: Vite dev proxy targets 8788.
- `docs/CHANNELS.md`: channel table lists 8787, 8788, 8797, and 8798.

Contract copies that would need review if channel ports become dynamic:

- `api/src/transport_matters/test_channel.py:test_all_channel_specs_loads_packaged_json`.
- `api/src/transport_matters/test_config.py` settings default assertions.
- `api/src/transport_matters/cli/test_start.py`, `api/src/transport_matters/cli/test_start_acceptance.py`, `api/src/transport_matters/cli/test_codex_channel.py`, `api/src/transport_matters/cli/test_desktop.py`, `api/src/transport_matters/cli/test_desktop_runtime.py`, `api/src/transport_matters/cli/test_channel_cmd.py`, `api/src/transport_matters/cli/test_runner.py`, `api/src/transport_matters/cli/test_runtime_home.py`, `api/src/transport_matters/cli/test_runs_health.py`, and `api/src/transport_matters/cli/test_net.py`.
- `api/tests/integration/test_backend_launch_smoke.py`.
- `desktop/src/env.test.ts`, `desktop/src/main.test.ts`, and `desktop/src/window.test.ts`.

### Boundary findings

- The desktop path owns a separate port resolver, `api/src/transport_matters/cli/desktop_cmd.py:_resolve_backend_ports`, instead of reusing `api/src/transport_matters/cli/launch_runtime.py:resolve_launch_ports`. That may be acceptable because desktop starts a resident backend, but it duplicates pinned port semantics and error handling.
- `api/src/transport_matters/cli/__init__.py:desktop` does not expose `--proxy-port`, while `api/src/transport_matters/cli/net.py:raise_port_in_use` may tell desktop users to pass `--proxy-port` on proxy collisions.
- The channel runtime record is only used by channel list, stop, and tail surfaces. Desktop start does not consult it.
- `api/src/transport_matters/__main__.py` is a dev server entry point using `Settings.web_port`; it is adjacent to this issue but not the source of the observed desktop error.

## Plan

### Decision needed

Choose option A for channel launches: detect that the requested channel is already running and either attach a hosted viewer or refuse with a precise message that includes the existing URL and pid.

Reasoning:

- The channel model already treats stable and preview ports as stable addresses.
- The failure is specifically an already running stable channel, not a need for another arbitrary port.
- Auto allocating the next free port would undermine current channel contracts unless the channel model gains a separate instance identity.
- Improving only the generic error would leave the operator unable to recover from the common “already running” case.

Open product choice inside option A: attach by default, or refuse with a clear message. For this user story, attach is likely better because `api/src/transport_matters/cli/desktop_cmd.py:spawn_detached_electron` already supports a hosted viewer for a route URL. Refuse is safer if duplicate Electron windows should be explicit.

### Proposed steps

1. Add a channel runtime preflight in the desktop start path.
   - Use `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record` with `api/src/transport_matters/cli/desktop_runtime.py:desktop_record_path` and `transport_matters.storage_roots:default_storage_root` for the active `ChannelSpec`.
   - If the record is live and the web port responds, format the existing `loopback_http_url(record.web_port)` and the same workspace route shape from `api/src/transport_matters/cli/desktop_cmd.py:build_backend_started_event`.
   - Depending on the decision above, either call `api/src/transport_matters/cli/desktop_cmd.py:spawn_detached_electron` against that route or exit with a precise already running message.

2. Keep unrelated port conflicts on the existing helper seam.
   - Continue using `api/src/transport_matters/cli/net.py:port_in_use` and `api/src/transport_matters/cli/net.py:raise_port_in_use` for non channel owner collisions.
   - Consider a small desktop specific wrapper so the proxy message does not suggest `--proxy-port` until `api/src/transport_matters/cli/__init__.py:desktop` actually exposes that option.

3. Consolidate channel port constants around `channel-specs.json`.
   - Treat `api/src/transport_matters/channel-specs.json` as the source for channel defaults.
   - Keep `api/src/transport_matters/config.py:Settings` defaults only if direct settings users still require a stable fallback, and document that env launch values override them during real runs.
   - Replace Electron fallbacks in `desktop/src/main.ts:DEFAULT_PROXY_PORT` and `desktop/src/window.ts:DEFAULT_WEB_PORT` only after package smoke proves the copied channel spec is always present in packaged and dev launches.

4. Do not wire dynamic allocation into normal channel desktop start yet.
   - Leave `api/src/transport_matters/cli/ports.py:allocate_port_pair` available for explicit future instance mode or tests.
   - If dynamic ports are desired later, model them as a distinct instance concept with explicit URL discovery, not as silent channel fallback.

### Tests and gates

Focused tests to add or update:

- `api/src/transport_matters/cli/test_desktop.py`: live stable record causes attach or precise refusal without spawning `_desktop-backend`.
- `api/src/transport_matters/cli/test_desktop.py`: stale record is ignored and normal port checks still run.
- `api/src/transport_matters/cli/test_desktop.py`: unrelated listener on the channel web port still uses the existing port conflict error.
- `api/src/transport_matters/cli/test_channel_cmd.py`: channel list keeps showing the live pid and ports after the new preflight helper is introduced.
- `desktop/src/main.test.ts`: hosted lifecycle accepts the route URL produced by the attach path.

Suggested commands:

```bash
cd api && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  src/transport_matters/cli/test_desktop.py \
  src/transport_matters/cli/test_desktop_runtime.py \
  src/transport_matters/cli/test_channel_cmd.py \
  src/transport_matters/cli/test_net.py \
  src/transport_matters/test_channel.py
cd api && just check
cd desktop && pnpm test -- src/main.test.ts src/env.test.ts src/window.test.ts
cd desktop && pnpm typecheck
```

Verification run for this scout:

```bash
cd api && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  src/transport_matters/cli/test_net.py \
  src/transport_matters/cli/test_desktop.py::test_desktop_channel_default_port_in_use_fails_fast \
  src/transport_matters/cli/test_start.py::test_start_channel_default_port_in_use_fails_fast \
  src/transport_matters/test_channel.py::test_all_channel_specs_loads_packaged_json
```

Result: 16 passed in 0.05s. `git status --short` was clean before the scout and after the verification run.
