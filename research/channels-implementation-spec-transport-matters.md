---
title: Transport Matters channels implementation analysis
type: research
tags: [transport-matters, channels, desktop, electron, postgres, fmm]
summary: Verified and corrected the live Transport Matters seams for stable and preview channel isolation.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Executive Summary

Transport Matters can support side by side `stable` and `preview` instances by resolving a single channel id before settings load, backend app creation, and Electron identity setup. The implementation spec at `~/.mdx/projects/transport-matters-channels-spec.md` now incorporates the architect review findings around package data, no-config DB signaling, DRY port data, lazy disk layout defaults, backend preflight ordering, and migration gates.

## Project Metadata

Language and runtime: Python 3.14 backend, TypeScript desktop and web, Node >=20.19, pnpm 10.8.1. Backend framework and libraries: FastAPI, Typer, Pydantic Settings, psycopg, Alembic, mitmproxy. Desktop and web: Electron 39, React 19, Vite 8, TanStack Query, Vitest, Playwright. Build and gates: uv and hatch for the wheel, pnpm for web and desktop, root `just` recipes for `check`, `test`, `build`, and install. The repo is fmm indexed via `.fmm.db`.

## Architecture

The channel implementation crosses four live seams:

1. Backend settings: `api/src/transport_matters/config.py` defines `Settings`, `get_settings`, and `resolve_database_url`; `api/src/transport_matters/storage_roots.py` defines `default_storage_root`; `api/src/transport_matters/main.py` lazily builds FastAPI through `create_app` and starts the shared proxy in `lifespan` under `get_settings().storage_dir / "runtime" / "shared-proxy"`.
2. CLI startup: `api/src/transport_matters/cli/__init__.py` owns `claude`, `codex`, `desktop`, and hidden `_desktop-backend`; `launch_runtime.resolve_launch_ports` currently uses free allocation when ports are omitted; `desktop_cmd._resolve_backend_ports` does the same for desktop backend startup.
3. DB lifecycle: `session_store_preflight.check_session_store` resolves the configured database and connects before launches. `session/migrate.apply_migrations` migrates a reachable database to head. There is no existing create database helper.
4. Desktop and web identity: `desktop/src/env.ts` currently lacks channel keys; `desktop/src/main.ts` starts either a hosted viewer or a backend owned app; `desktop/src/window.ts:createWindowOptions` hard codes `APP_NAME`; `www/src/components/WindowDragRegion.tsx` is drag only; `www/src/rootShell.tsx` is the right visible badge mount.

## Key Patterns

Resolve first, then read settings. Typer command bodies must activate the channel before any call path reaches `preflight_session_store_or_exit`, `prepare_desktop_launch`, or `get_settings`. Electron follows the same pattern: resolve the channel and apply identity before `app.whenReady()`.

Keep package data inside the Python package. The single source should live at `api/src/transport_matters/channel-specs.json`, be included in wheel artifacts and sdist, and be copied into `desktop/dist` by the desktop build. This avoids editable-only success.

Do not fabricate a DB URL. `ChannelSpec` exposes `database_name`, while `config.resolve_database_url` substitutes that name onto an explicitly configured server URL. No env or TOML still raises `MissingDatabaseConfigError`. The future store picker keys off connectivity through `check_session_store` and the existing guards.

The storage root mostly cascades, but `storage/disk_layout.py:_DEFAULT_ROOT` is eager today. The implementation must make it lazy so `DiskStorageLayout.__init__` does not freeze the stable home before channel activation.

## Detailed Findings

The proposal was mostly aligned, but these live tree corrections matter:

- Standalone `claude` and `codex` do not use fixed defaults today. `launch_runtime.resolve_launch_ports` allocates free ports when either port is omitted, so channel work must replace that default with deterministic ports and keep fail fast checks.
- `desktop` does not expose a proxy port flag today, but `desktop_cmd.prepare_desktop_launch` still resolves and passes a proxy port to the backend command. Channel port defaults must be applied there too.
- The visible pill should not be mounted in `WindowDragRegion`. That component is `aria-hidden`, returns only a fixed drag div, and its CSS deliberately keeps it under app hit testing. A `ChannelBadge` mounted in `RootShell` is the cleaner seam.
- Existing DB commands are `transport-matters db status` and `db upgrade`; they migrate a configured database but do not create one. `transport-matters channel ensure-db` needs a new create database step before calling `apply_migrations`.
- `serve_desktop_backend` applies desktop backend env before preflight. The channel env must be present before preflight resolves the database URL.
- Slice 3 must run `cd api && just ci` or at least `just migration-smoke`, because DB lifecycle changes can touch `session/migrate.py` and advisory lock behavior.

## Dependencies

Critical dependency points are `config.get_settings` cache ordering, Typer option parsing, package resource loading, `psycopg` database creation, Alembic migration helpers, Electron `app.setName`, `app.setPath("userData")`, `app.setAppUserModelId`, and TanStack Query meta caching through `www/src/hooks/useMeta.ts`.

## Relevance to Helioy

Channels support Helioy dogfooding by letting the stable daily driver run beside an in development preview without sharing homes, ports, Postgres databases, Electron identity, or dock surfaces. This keeps agent work inside the stable instance while allowing preview to break safely.

## Open Questions

The preview dock icon asset does not exist yet and needs either a committed amber asset or a deterministic generation step. Implementation should verify editable, wheel, sdist, and package smoke paths so the shared JSON is present everywhere it is read.
