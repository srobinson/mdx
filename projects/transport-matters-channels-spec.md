---
title: Transport Matters channels implementation spec
type: spec
tags: [transport-matters, channels, desktop, electron, postgres, dogfood]
summary: Implement stable and preview side by side by resolving one channel before settings, backend startup, and Electron identity setup.
status: active
source: codebase-analyst
created: 2026-06-20
updated: 2026-06-20
---

# Transport Matters channels implementation spec

## Goal and fixed behavior

Transport Matters gets two runnable channels. `stable` is the default daily driver: bare `transport-matters desktop` resolves to canonical `~/.transport-matters/`, database `transport_matters`, proxy port `8787`, web port `8788`, app name `Transport Matters`, default icon, and no in-window pill. `preview` is the working tree dogfood instance: sibling home `~/.transport-matters-preview/`, database `transport_matters_preview`, proxy port `8797`, web port `8798`, app name `Transport Matters Preview`, preview app id, amber dock icon, and amber `PREVIEW` pill. `release` is the publish action that promotes code from preview to stable.

Live tree corrections to the proposal: standalone `claude` and `codex` currently allocate free ports through `launch_runtime.resolve_launch_ports`; channels replace that default with deterministic channel ports. `desktop` currently has no `--proxy-port` flag, but it resolves a proxy port internally through `desktop_cmd._resolve_backend_ports`. `WindowDragRegion` is a hidden drag map mounted before `#root`; anything visible there sits under the app. The pill belongs in the React shell, while `WindowDragRegion` stays drag only.

## ChannelSpec contract and single source

Add one committed table at `api/src/transport_matters/channel-specs.json`. Format is JSON so Python uses stdlib `json` and Electron uses `fs.readFileSync` without a TOML dependency. This package-local location is the single source. It follows the existing `settings.example.toml` convention and avoids a repo-root file that falls out of wheel and sdist builds.

```json
{
  "schema": 1,
  "channels": [
    {
      "id": "stable",
      "label": "Stable",
      "homeDir": ".transport-matters",
      "databaseName": "transport_matters",
      "proxyPort": 8787,
      "webPort": 8788,
      "electron": {
        "appName": "Transport Matters",
        "appId": "io.helioy.transport-matters",
        "userDataDir": null,
        "dockIcon": "default"
      },
      "badge": null
    },
    {
      "id": "preview",
      "label": "Preview",
      "homeDir": ".transport-matters-preview",
      "databaseName": "transport_matters_preview",
      "proxyPort": 8797,
      "webPort": 8798,
      "electron": {
        "appName": "Transport Matters Preview",
        "appId": "io.helioy.transport-matters.preview",
        "userDataDir": "electron-user-data",
        "dockIcon": "preview-amber"
      },
      "badge": { "text": "PREVIEW", "color": "amber", "hex": "#f59e0b" }
    }
  ]
}
```

Store resolved ports directly in the JSON. Python and TypeScript only read `proxyPort` and `webPort`; neither language computes channel port math.

Python adds `api/src/transport_matters/channel.py` with frozen `ChannelBadge` and `ChannelSpec` models. Exact public fields: `id: str`, `label: str`, `home: Path`, `database_name: str`, `proxy_port: int`, `web_port: int`, `electron_app_name: str`, `electron_app_id: str`, `electron_user_data: Path | None`, `dock_icon: Literal["default", "preview-amber"]`, `badge: ChannelBadge | None`. `ChannelSpec` does not expose `database_url`; URL composition stays in config and channel DB helpers. `ChannelBadge` fields are `text: str`, `color: Literal["amber"]`, `hex: str`. Public functions: `resolve_channel_id(value: str | None, env: Mapping[str, str]) -> str`, `resolve_channel_spec(value: str | None = None, env: Mapping[str, str] = os.environ) -> ChannelSpec`, `activate_channel(value: str | None) -> ChannelSpec`, and `all_channel_specs() -> tuple[ChannelSpec, ...]`. Ids validate against `^[a-z][a-z0-9_]*$` and must exist in `channel-specs.json`.

Packaging: add `api/src/transport_matters/channel-specs.json` to `api/pyproject.toml` under `[tool.hatch.build.targets.wheel].artifacts`, beside `src/transport_matters/settings.example.toml`. Add `src/transport_matters/channel-specs.json` to `[tool.hatch.build.targets.sdist].only-include`. Do not add a `force-include`. `channel.py` reads it with `importlib.resources.files("transport_matters") / "channel-specs.json"`. Desktop adds `desktop/scripts/copy-channel-specs.mjs`, called by `desktop/package.json build`, to copy `../api/src/transport_matters/channel-specs.json` into `desktop/dist/channel-specs.json`. `desktop/src/env.ts` reads `new URL("./channel-specs.json", import.meta.url)` at runtime and exports `resolveDesktopChannelSpec(env)` with the same TypeScript shape. No generated TypeScript constants are allowed.

## Resolution ordering

Add `env_keys.CHANNEL = "TRANSPORT_MATTERS_CHANNEL"`. Add `ChannelOption` in `cli/launch_options.py`: `--channel`, env var `env_keys.CHANNEL`, default hidden from Typer because `activate_channel` applies `stable`.

Call `activate_channel(channel)` as the first executable statement in `cli/__init__.py:claude`, `codex`, `desktop`, and hidden `desktop_backend`. It sets `TRANSPORT_MATTERS_CHANNEL` to the canonical id and clears `config.get_settings` if imported. This happens before `run_start` and `run_codex` call `preflight_session_store_or_exit`, before `desktop_cmd.prepare_desktop_launch` resolves storage and ports, and before `_desktop-backend` reaches `serve_desktop_backend`.

`serve_desktop_backend` order on main is `_apply_desktop_backend_env(plan.env)`, then `preflight_session_store_or_exit()`, then `get_settings.cache_clear()`, then `create_app()`. Preserve that order. The invariant is explicit: the channel env is applied before preflight resolves the DB URL.

`config.Settings` adds `channel: str`. `storage_roots.default_storage_root` returns `Path.home() / spec.homeDir` unless `TRANSPORT_MATTERS_HOME` is explicitly set for test or emergency override. `storage/disk_layout.py:_DEFAULT_ROOT` must become lazy, because it is currently bound at module import and `DiskStorageLayout.__init__` uses it when no root is supplied. Replace the eager constant with a helper that rereads `default_storage_root()` on use so the tier 1 storage cascade holds for preview.

`main.create_app` and `main.lifespan` continue to call `get_settings` lazily; by then the channel env is set. The shared proxy socket remains isolated because `main.lifespan` builds `SharedProxyManager.create(runtime_dir=get_settings().storage_dir / "runtime" / "shared-proxy")`.

Electron adds `ENV.CHANNEL`. In `desktop/src/main.ts:registerDesktopLifecycleFromEnv`, resolve the spec and call `applyChannelIdentity(app, spec)` before package smoke, hosted route, or direct backend startup branches. The helper calls `app.setName(spec.electron.appName)`, `app.setAppUserModelId(spec.electron.appId)`, and for preview `app.setPath("userData", path.join(spec.home, spec.electron.userDataDir))` before `app.whenReady()`. Hosted viewers launched by Python receive the same env from `desktop_cmd.spawn_detached_electron`. Direct Electron launches use `resolveBackendStartupOptions` to pick spec ports and pass `TRANSPORT_MATTERS_CHANNEL` into `backendProcess.buildBackendLaunch`.

## CLI, DB, storage, and ports

Commands taking `--channel`: `transport-matters claude`, `codex`, `desktop`, and hidden `_desktop-backend`. Unknown channels exit 2 and suggest `transport-matters channel list`.

`config.resolve_database_url` keeps the no-config signal. Precedence is still explicit env or config only: `TRANSPORT_MATTERS_DATABASE_URL`, then `[database].url`, else raise `MissingDatabaseConfigError`. When a configured server URL exists, resolve the channel and substitute only the path database name with `spec.database_name`. Invariant: stable and preview land on distinct dbnames on the same configured server, and no env or TOML still raises `MissingDatabaseConfigError`. The no-DB and store-picker work must key off connectivity through `check_session_store`, `preflight_session_store_or_exit`, and `RunManager._ensure_session_store_available`, not a specific missing-config branch.

Add `transport-matters channel` in `api/src/transport_matters/cli/channel_cmd.py` and register it beside `db_app` in `cli/__init__.py`. Subcommands:

1. `list`: prints id, home, database, proxy port, web port, app name, and badge.
2. `ensure-db [channel]`: resolves the channel, requires an explicitly configured server URL, connects to the maintenance database on that same server, creates `spec.database_name` when absent using psycopg SQL identifiers, then calls `session.migrate.apply_migrations` on the resolved channel URL. This makes existing preflight guards pass without relaxing the current DB requirement.
3. `promote preview stable`: promotes code only. It runs the same build and install path as root `just install-local` against the current repo, then prints the stable launch command. It never copies or rewrites `transport_matters_preview` data into `transport_matters`.

Ports: `launch_runtime.resolve_launch_ports` and `desktop_cmd._resolve_backend_ports` should accept channel defaults. When a port flag is omitted, use `spec.proxy_port` or `spec.web_port`; if the resolved port is in use, fail fast with the existing `port_in_use` message. The free allocator remains only for tests and future explicit alternate modes, not for channel defaults.

Storage: `default_storage_root` and the lazy `DiskStorageLayout` default cascade to `workspace.workspace_root`, `workspace.run_root`, the per-run tier 1 tree, settings scaffold, and the shared proxy runtime directory. `_build_desktop_backend_env`, `_build_desktop_backend_command`, `launch_environment.build_launch_env`, and `backendProcess.buildBackendLaunch` must all carry `TRANSPORT_MATTERS_CHANNEL` so addon, backend, child CLIs, and hosted Electron agree.

## Badge wiring

`api/v1/meta.py:MetaResponse` adds `channel: str`, `channel_label: str`, and `channel_badge: ChannelBadgeResponse | None`. Reserve additive space for the no-DB track's `db_status`; do not make channel fields block or rename that future field. `get_meta` builds channel fields from `resolve_channel_spec(settings.channel)`. `get_run_meta` delegates to `get_meta`, so run meta stays consistent.

`www/src/api.ts:Meta` and `fetchMeta` map the new fields. Add `www/src/components/ChannelBadge.tsx` and CSS. It uses `useMeta`, returns null for stable or missing badge, and renders an amber fixed pill for preview. Mount it in `www/src/rootShell.tsx` above the selected route. Keep `WindowDragRegion` as the `aria-hidden` drag region only.

`desktop/src/window.ts:createWindowOptions` accepts `title: string` and receives `spec.electron.appName`; `APP_NAME` becomes the stable default, not the only title. Add a preview icon asset under `desktop/assets/` and set it from the Electron identity helper for preview.

## Justfile

Add root recipe:

```just
channel-restart channel="preview":
    cd "{{www_dir}}" && pnpm install && pnpm build
    cd "{{desktop_dir}}" && pnpm install && pnpm build && pnpm electron:install
    uv run --project "{{api_dir}}" transport-matters channel ensure-db {{channel}}
    TRANSPORT_MATTERS_CHANNEL={{channel}} uv run --project "{{api_dir}}" transport-matters desktop --channel {{channel}}
```

Keep `install-local` stable only, since it overwrites the single global uv tool.

## Slice plan and gates

Common final gate for every slice is the repo recipe, verbatim: root `just check` runs `cd "{{desktop_dir}}" && just check`, `cd "{{www_dir}}" && just check`, `cd "{{api_dir}}" && just check`; root `just test` runs `cd "{{desktop_dir}}" && just test`, `cd "{{www_dir}}" && just test`, `cd "{{api_dir}}" && just test`. Package recipes are also fixed: `desktop check: typecheck test`; `www check: format lint typecheck`; `api check: format lint typecheck`; `api ci: uv run ruff format --check src/`, `uv run ruff check src/`, `uv run mypy src/`, `just migration-smoke`, `uv run python -m pytest`.

1. Channel core. Change `api/src/transport_matters/channel-specs.json`, `api/src/transport_matters/channel.py`, `api/src/transport_matters/env_keys.py`, `api/src/transport_matters/config.py`, `api/src/transport_matters/storage_roots.py`, `api/src/transport_matters/storage/disk_layout.py`, `api/src/transport_matters/settings.example.toml`, `api/pyproject.toml`, and tests `test_channel.py`, `test_config.py`, `test_env_keys.py`. Gate: focused `cd api && just test src/transport_matters/test_channel.py src/transport_matters/test_config.py src/transport_matters/test_env_keys.py`, then common final gate.
2. CLI and port plumbing. Change `launch_options.py`, `cli/__init__.py`, `start_cmd.py`, `codex_cmd.py`, `launch_runtime.py`, `desktop_cmd.py`, `launch_environment.py`, `desktop/src/backendProcess.ts`, and their existing tests. Gate: focused `cd api && just test src/transport_matters/cli/test_start.py src/transport_matters/cli/test_codex.py src/transport_matters/cli/test_desktop.py`, plus `cd desktop && just test`, then common final gate.
3. DB lifecycle and justfile. Change `cli/channel_cmd.py`, `cli/db_cmd.py` only if shared helpers are extracted, `session/migrate.py` only if helper reuse is needed, root `justfile`, and tests for ensure-db using a temporary database name. Gate: focused `cd api && just test src/transport_matters/cli/test_channel_cmd.py src/transport_matters/cli/test_launch_preflight.py`, then `cd api && just ci`, then common final gate.
4. Desktop identity and badge. Change `desktop/src/env.ts`, `desktop/src/main.ts`, `desktop/src/window.ts`, `desktop/package.json`, `desktop/scripts/copy-channel-specs.mjs`, `api/v1/meta.py`, `www/src/api.ts`, `www/src/rootShell.tsx`, `www/src/components/ChannelBadge.tsx`, and tests. Gate: focused `cd desktop && just package-smoke`, `cd www && just test`, `cd api && just test src/transport_matters/api/v1/test_meta.py`, then common final gate.
5. Live smoke and promotion. Change `channel_cmd.py` promote path and docs. Gate: `just channel-restart preview`, verify `/api/meta` on port 8798 reports `preview`, verify an amber `PREVIEW` pill in the desktop, verify stable `/api/meta` on port 8788 still reports `stable`, then run common final gate. Promotion gate: `transport-matters channel promote preview stable`, then `transport-matters desktop` launches stable without moving the preview DB or home.
