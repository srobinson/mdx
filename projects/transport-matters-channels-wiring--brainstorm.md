# Transport Matters channel isolation wiring

## Current resolution map

Storage is rooted by `api/src/transport_matters/storage_roots.py:default_storage_root`. It honors `TRANSPORT_MATTERS_HOME`, else returns `~/.transport-matters` at lines 12 to 24. Workspace and tier 1 run dirs already derive below that root through `default_workspaces_root` at lines 27 to 29, `workspace_root` in `api/src/transport_matters/workspace.py` lines 71 to 80, and `run_root` lines 83 to 92.

Session DB resolution is split. `api/src/transport_matters/config.py:Settings` defines static `proxy_port=8787`, `web_port=8788`, `storage_dir=default_storage_root`, `database_url`, and TOML backed `[database]` fields at lines 70 to 118. `resolve_database_url` returns `settings.database_url or settings.database.url`, else errors, at lines 189 to 193. Runtime startup calls it in `api/src/transport_matters/main.py:lifespan` lines 160 to 166, then opens and migrates the pool in `_start_session_store` lines 106 to 130. Migrations and db CLI resolve the same URL via `api/migrations/env.py:_database_url` lines 18 to 22 and `api/src/transport_matters/cli/db_cmd.py:_resolve_or_exit` lines 36 to 41.

Proxy and web ports enter via `api/src/transport_matters/cli/launch_options.py:ProxyPortOption` and `WebPortOption`, lines 26 to 47, with env vars from `env_keys.py` lines 23 to 24. Launches pass those options through `api/src/transport_matters/cli/__init__.py:claude` lines 243 to 286 and `codex` lines 298 to 339. `prepare_launch` resolves free ports through `resolve_launch_ports` in `api/src/transport_matters/cli/launch_runtime.py` lines 118 to 185. The allocator uses two kernel assigned loopback ports in `api/src/transport_matters/cli/ports.py:allocate_port_pair` lines 39 to 77.

Desktop is a separate path. `api/src/transport_matters/cli/__init__.py:desktop` only exposes `--web-port` and `--storage-dir`, lines 348 to 359. `api/src/transport_matters/cli/desktop_cmd.py:prepare_desktop_launch` resolves ports, storage, backend env, and backend command at lines 93 to 129. `_resolve_backend_ports` allocates when a port is missing, lines 303 to 313. `_resolve_storage_dir` defaults to `default_storage_root`, lines 333 to 336. `_build_desktop_backend_env` writes `TRANSPORT_MATTERS_CWD`, `PROXY_PORT`, `STORAGE_DIR`, and `WEB_PORT`, lines 339 to 357. `serve_desktop_backend` runs uvicorn on `plan.web_port`, lines 265 to 272.

Electron currently has no channel identity. `desktop/src/main.ts:resolveBackendStartupOptions` reads proxy and web env with static defaults, lines 90 to 100. `desktop/src/window.ts:createWindowOptions` hard codes title `Transport Matters` and `titleBarStyle: "hidden"`, lines 20 to 31. The drag strip is mounted before the React root in `www/src/main.tsx` lines 23 to 31 and has drag only CSS in `www/src/components/window-drag-region.css` lines 9 to 18.

## Proposed channel contract

Add one primary knob: `--channel <id>` plus `TRANSPORT_MATTERS_CHANNEL`, with default `release`. Channel ids validate as lowercase words plus digits and underscores. Add `api/src/transport_matters/channel.py:ChannelSpec` with derived fields:

- `home = ~/.transport-matters/{channel}` unless an explicit `TRANSPORT_MATTERS_HOME` is set for tests or emergency override.
- `database_url = postgresql://tm:tm@localhost:55432/transport_matters_{channel}` unless `TRANSPORT_MATTERS_DATABASE_URL` or channel TOML overrides it.
- Ports use a deterministic built in table: `release 8787/8788`, `preview 8887/8888`, `staging 8987/8988`. Unknown channels fail until registered by `transport-matters channel init <id>`, which persists a non colliding ordinal under the base home.
- Electron identity derives as display name `Transport Matters {Channel}`, userData `~/.transport-matters/{channel}/electron-user-data`, and bundle id `io.helioy.transport-matters.{channel}`.

## Change points

1. `api/src/transport_matters/env_keys.py`: add `CHANNEL` and optional `BASE_HOME` beside `HOME`, `PROXY_PORT`, `WEB_PORT`, and `DATABASE_URL`.
2. `api/src/transport_matters/storage_roots.py:default_storage_root`: call `resolve_channel_spec()` and return the channel home. This automatically moves workspaces, run roots, runtime home overlays, and shared proxy runtime dirs because `workspace_root`, `run_root`, and `main.py:lifespan` already compose below settings storage.
3. `api/src/transport_matters/config.py:Settings` and `resolve_database_url`: add `channel`, change port defaults to channel factories, and derive a channel DB when env and TOML are absent. Update `settings.example.toml` to show `transport_matters_release`.
4. `api/src/transport_matters/cli/launch_options.py`: add `ChannelOption`. Thread it through `__init__.py:claude`, `codex`, `desktop`, and `_desktop-backend`. Set the env before `get_settings()` can cache.
5. `api/src/transport_matters/cli/launch_runtime.py:resolve_launch_ports` and `desktop_cmd.py:_resolve_backend_ports`: when ports are not pinned, use `ChannelSpec.proxy_port` and `web_port`, then reuse `port_in_use` for the existing fail fast behavior.
6. `api/src/transport_matters/launch_environment.py:build_launch_env` and `desktop_cmd.py:_build_desktop_backend_env`: include `TRANSPORT_MATTERS_CHANNEL` so addons, child CLIs, and backend share one identity.
7. `api/src/transport_matters/api/v1/meta.py:MetaResponse` and `get_meta`: return `channel`. Map it in `www/src/api.ts:Meta` and `fetchMeta`. Render the badge in a new title bar chrome component inside `RootShell`, because the current pre root `WindowDragRegion` is drag only.
8. `desktop/src/env.ts`, `desktop/src/main.ts:resolveBackendStartupOptions`, and `desktop/src/window.ts:createWindowOptions`: read channel, set app name, set `app.setPath("userData", spec.userData)`, pass a channel title to the BrowserWindow, and package per channel for macOS Dock identity.

## Operator commands

Current `just install-local` overwrites the single global uv tool at `justfile` lines 63 to 71, so preview should run from the repo, not replace release.

- Restart preview from current changes: `just channel-restart preview`, implemented as build www and desktop, `uv run --project api transport-matters channel ensure-db preview`, then `uv run --project api transport-matters desktop --channel preview`.
- Promote preview to staging: `transport-matters channel promote preview staging` copies the preview artifact or editable source pointer into staging, ensures `transport_matters_staging`, runs migrations, and restarts staging.
- Promote staging to release: `transport-matters channel promote staging release --version X.Y.Z` wraps `scripts/release.sh --install X.Y.Z`, then restarts `transport-matters desktop --channel release`.

Riskiest change: channel must resolve before any `get_settings()` cache, uvicorn app creation, or Electron app setup. A late channel would silently cross wire storage, DB, or userData.
