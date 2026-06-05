---
title: Transport Matters Channel Isolation Wiring
type: research
tags: [transport-matters, desktop, channels, postgres, electron]
summary: Wiring plan for deriving storage, database, ports, and Electron identity from one Transport Matters channel id.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Executive Summary

Transport Matters can support simultaneous stable, preview, staging, and release desktop instances by introducing a single channel identity that derives storage, Postgres DB, ports, and Electron identity. The current code already centralizes most launch state, so the key work is early channel resolution and threading the result through Settings, CLI launch options, desktop bootstrap, and `/api/meta`.

## Project Metadata

- Python package: `api/pyproject.toml`, console script `transport-matters`, Python `>=3.14`, FastAPI, Pydantic Settings, mitmproxy, Typer, psycopg, Alembic.
- Web app: `www/package.json`, React 19, Vite 8, TanStack Query, xterm, Zustand, Playwright, Vitest.
- Desktop app: `desktop/package.json`, Electron 39, TypeScript, electron-packager.
- Build gates: root `just check` and `just test` delegate to desktop, www, and api.

## Architecture

Storage is rooted by `api/src/transport_matters/storage_roots.py:default_storage_root` at lines 12 to 24. Workspace and tier 1 run dirs derive below that root through `default_workspaces_root` lines 27 to 29, `api/src/transport_matters/workspace.py:workspace_root` lines 71 to 80, and `run_root` lines 83 to 92.

Database resolution is owned by `api/src/transport_matters/config.py:Settings` lines 50 to 150 and `resolve_database_url` lines 189 to 193. Runtime startup calls it in `api/src/transport_matters/main.py:lifespan` lines 160 to 166, then opens and migrates the pool in `_start_session_store` lines 106 to 130. Migrations and db CLI use the same path via `api/migrations/env.py:_database_url` lines 18 to 22 and `api/src/transport_matters/cli/db_cmd.py:_resolve_or_exit` lines 36 to 41.

Ports enter through `api/src/transport_matters/cli/launch_options.py:ProxyPortOption` and `WebPortOption` lines 26 to 47, then flow through `api/src/transport_matters/cli/__init__.py:claude` lines 243 to 286 and `codex` lines 298 to 339. `api/src/transport_matters/cli/launch_runtime.py:resolve_launch_ports` lines 118 to 185 resolves pinned or allocated ports. `api/src/transport_matters/cli/ports.py:allocate_port_pair` lines 39 to 77 allocates two free loopback ports.

Desktop launch goes through `api/src/transport_matters/cli/desktop_cmd.py:prepare_desktop_launch` lines 79 to 129. `_resolve_backend_ports` lines 303 to 313 allocates missing ports, `_resolve_storage_dir` lines 333 to 336 defaults storage, `_build_desktop_backend_env` lines 339 to 357 writes backend env, and `serve_desktop_backend` lines 252 to 300 runs uvicorn on `plan.web_port`.

Electron currently has no channel identity. `desktop/src/main.ts:resolveBackendStartupOptions` lines 90 to 100 reads proxy and web env with static defaults. `desktop/src/window.ts:createWindowOptions` lines 17 to 42 hard codes title and hidden title bar. The drag strip mounts before React root in `www/src/main.tsx` lines 23 to 31 and is drag only in `www/src/components/window-drag-region.css` lines 9 to 18.

## Detailed Findings

Recommended contract: add `--channel <id>` plus `TRANSPORT_MATTERS_CHANNEL`, default `release`. Add `api/src/transport_matters/channel.py:ChannelSpec` deriving:

- `home = ~/.transport-matters/{channel}` unless `TRANSPORT_MATTERS_HOME` explicitly overrides.
- `database_url = postgresql://tm:tm@localhost:55432/transport_matters_{channel}` unless env or channel TOML overrides.
- ports from a deterministic table: `release 8787/8788`, `preview 8887/8888`, `staging 8987/8988`. Unknown channels fail until initialized into a non colliding persisted ordinal.
- Electron display name, userData, and bundle id from the same channel.

Concrete change points:

1. `api/src/transport_matters/env_keys.py`: add `CHANNEL` and optional `BASE_HOME` near `HOME`, `PROXY_PORT`, `WEB_PORT`, and `DATABASE_URL`.
2. `api/src/transport_matters/storage_roots.py:default_storage_root`: call channel resolution. This moves workspaces, run roots, runtime home overlays, and shared proxy runtime dirs because downstream code composes below settings storage.
3. `api/src/transport_matters/config.py:Settings` and `resolve_database_url`: add `channel`, channel port defaults, and channel DB fallback. Update `settings.example.toml` to show `transport_matters_release`.
4. `api/src/transport_matters/cli/launch_options.py`: add `ChannelOption`. Thread it through `__init__.py:claude`, `codex`, `desktop`, and `_desktop-backend`. Set env before `get_settings()` can cache.
5. `api/src/transport_matters/cli/launch_runtime.py:resolve_launch_ports` and `desktop_cmd.py:_resolve_backend_ports`: use channel ports when not pinned, then reuse `port_in_use` for fail fast checks.
6. `api/src/transport_matters/launch_environment.py:build_launch_env` and `desktop_cmd.py:_build_desktop_backend_env`: include `TRANSPORT_MATTERS_CHANNEL`.
7. `api/src/transport_matters/api/v1/meta.py:MetaResponse` and `get_meta`: return `channel`. Map it in `www/src/api.ts:Meta` and `fetchMeta`. Render the visual badge in a new title bar chrome component inside `RootShell` rather than overloading the pre root drag strip.
8. `desktop/src/env.ts`, `desktop/src/main.ts:resolveBackendStartupOptions`, and `desktop/src/window.ts:createWindowOptions`: read channel, set app name, set `app.setPath("userData", spec.userData)`, pass a channel title, and package per channel for macOS Dock identity.

## Key Patterns

Do not use current `just install-local` for preview because root `justfile` lines 63 to 71 overwrite the single global uv tool. Preview should launch from the repo with `uv run --project api transport-matters desktop --channel preview`.

Recommended commands:

- `just channel-restart preview`: build www and desktop, ensure `transport_matters_preview`, then run preview from the editable repo.
- `transport-matters channel promote preview staging`: copy the preview artifact or source pointer to staging, ensure `transport_matters_staging`, migrate, and restart staging.
- `transport-matters channel promote staging release --version X.Y.Z`: wrap `scripts/release.sh --install X.Y.Z`, then restart `transport-matters desktop --channel release`.

## Dependencies

Critical dependencies are Pydantic Settings for env precedence, Typer for channel options, psycopg and Alembic for channel DB creation and migration, Electron app APIs for userData and app name, and electron-packager for real per channel macOS Dock identity.

## Relevance to Helioy

This fits the Helioy dogfooding workflow: a stable driving channel can supervise work while preview runs current changes with separate DB, storage, ports, and desktop state.

## Open Questions

- Should the stable driving channel be named `release` or should `driving` alias `release`?
- Should arbitrary channel ids be allowed, or should preview, staging, and release be the only first slice?
- Should `channel ensure-db` create databases on the shared local Postgres server, or should each channel own a separate container?

