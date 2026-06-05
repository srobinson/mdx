---
title: Transport Matters channels — side-by-side dogfooding proposal (LOCKED)
type: proposal
tags: [transport-matters, channels, dogfood, desktop, electron, isolation, postgres]
summary: Run a stable daily-driver instance next to an in-dev preview instance via one --channel knob that fans out to storage root, Postgres DB, ports, and Electron identity; release is the publish action, not a third instance.
status: locked
created: 2026-06-20
updated: 2026-06-20
source: synthesis of brainstorm warroom (Claude + Codex codebase-analysts, Claude deep-research)
inputs:
  - transport-matters-channels-design--brainstorm.md
  - transport-matters-channels-wiring--brainstorm.md
  - transport-matters-channels-research--brainstorm.md
---

# Side-by-side dogfooding: the `stable` + `preview` channel model

## Goal

Dogfood Transport Matters desktop while developing it: run **two instances at once**
on one Mac, fully isolated, trivially (re)startable by both Stuart and agents.

- **`stable`** — the daily driver. The instance Stuart works *in*. Holds real captured history.
- **`preview`** — the in-development build carrying the current working tree. Expected to break.

`release` is **not** a third running instance; it is the act of promoting `preview` into `stable`.

## The single design rule

**One channel id fans out to every isolation dimension.** Don't isolate five things by
hand; isolate one variable and derive the rest. Selection knob:

- CLI: `transport-matters <cmd> --channel <c>`
- Env: `TRANSPORT_MATTERS_CHANNEL`
- Default: `stable` (a bare `transport-matters desktop` with no flag launches the daily driver)

The derivation table (offsets / colors / dbnames) lives in **one committed file** read by
both the Python config layer and the Electron `env.ts`. Never re-encode the port math in two
languages.

## Locked scheme

| Dimension | `stable` (daily driver) | `preview` (in-dev) |
|---|---|---|
| Launch | `transport-matters desktop` | `transport-matters desktop --channel preview` |
| Storage root | canonical `~/.transport-matters/` — **never moves** | sibling `~/.transport-matters-preview/` |
| Tier-1 runs, shared-proxy socket | derived below root (free) | derived below root (free) |
| Postgres DB | `transport_matters` | `transport_matters_preview` (same server, isolated) |
| Proxy / web port | 8787 / 8788 (offset 0) | 8797 / 8798 (offset 1) |
| Electron userData | default | explicit per-channel path |
| App / dock identity | "Transport Matters", default icon | "Transport Matters Preview", appId `…-preview`, **amber** dock icon |
| Title bar | quiet, no pill | **amber `PREVIEW` pill** |

**Why stable keeps the canonical path:** the daily driver's bytes never move, so there is
zero migration risk for the instance holding real history. Only `preview` is a sibling. (No
back-compat burden anyway — private single-user repo — but free safety is worth taking.)

**Why per-channel DB on one server, never shared:** a bad in-dev migration in `preview` must
not be able to corrupt the driving instance's captured history. Same Postgres server/role,
distinct dbname.

## Isolation model — what derives from `c`

The strong finding: **the storage root already cascades.** `TRANSPORT_MATTERS_HOME` drives
tier-1, the per-run dirs, *and* the shared-proxy control socket (`_control_socket_path` in
`shared_proxy/manager.py` is a sha256 of the runtime dir). Point one knob at a per-channel
root and the lock / socket / run surface isolates for free. Only these need their own
derivation:

- **Storage root** — `stable` → canonical path; `preview` → `~/.transport-matters-preview/`.
- **Ports** — `proxy = 8787 + 10·offset`, `web = 8788 + 10·offset`. Block of 10 leaves headroom.
- **Postgres dbname** — `transport_matters_<c>` (honor an explicit `TRANSPORT_MATTERS_DATABASE_URL` / channel TOML override if present).
- **Electron userData** — set the path **explicitly** via `app.setPath('userData', …)`. Electron's `productName`/`name` → path derivation is documented-buggy (`appData` reads `name`, `logs` reads `productName`); don't trust it.
- **App / dock identity** — `app.setName(…)` + per-channel `appId` + tinted icon, all **before app-ready**.

## The channel badge — two surfaces, one source

A window pill alone vanishes on minimize / ⌘-Tab, so channel identity rides **both** surfaces,
fed from one source of truth. Industry signal is overwhelmingly **icon color + the channel word
in the title** (VS Code Insiders green, Discord Canary orange, Chrome Canary gold).

1. **Native (dock / ⌘-Tab):** `app.setName("Transport Matters Preview")` + a tinted dock icon.
   Currently entirely missing — `app.setName`/`setPath` are never called and the window title is
   the hardcoded `APP_NAME`.
2. **In-window pill:** an amber `PREVIEW` pill in the recreated title-bar strip (`www`
   `WindowDragRegion`), for the focused case.

**Threading:** `--channel` / `TRANSPORT_MATTERS_CHANNEL` → a pure `resolve_channel(id)` →
Electron `main` sets name + userData + dock icon before app-ready and forwards the channel in
the backend env → backend adds `channel` / `label` / `color` to `GET /api/meta` (which already
serves CWD) → `WindowDragRegion` reads `/api/meta` and paints the pill. `stable` gets no pill;
only `preview` shouts.

## Operator commands (one per hop, agent-runnable)

```
just channel-restart preview
```
Build www + desktop from the working tree → **ensure `transport_matters_preview` DB exists +
run migrations** → set channel env → relaunch `transport-matters desktop --channel preview`.
Idempotent: tears down the prior preview first.

```
transport-matters channel promote preview stable
```
Promote the **code artifact** (build the working tree and install it as the stable wheel).
Never touches session DBs — `stable`'s captured history is never promoted over.

> Note: `just install-local` overwrites the single global uv tool, so `preview` must run from
> the repo, not replace the installed `stable`.

## Two risks (both already mapped to seams)

1. **The bite — DB must exist before launch.** A fresh channel with a missing or stale
   `transport_matters_preview` face-plants on the existing preflight guards
   (`preflight_session_store_or_exit`, `RunManager._ensure_session_store_available`). So
   `channel-restart` **must** create-db + migrate as a step. This couples directly to the
   no-DB / store-picker work in NOW.md.
2. **Ordering — channel must resolve first.** It must resolve **before** `get_settings()`
   caches, before uvicorn builds the app, and before Electron `app` setup. A late channel
   silently cross-wires storage / DB / userData. (Flagged by the Codex pane as the riskiest
   change.)

## Code seams (file : symbol)

Python / backend:
- `storage_roots.py : default_storage_root` — honors `TRANSPORT_MATTERS_HOME`; returns the channel home. Workspaces, run roots, and the shared-proxy runtime dir already compose below this, so they move for free.
- `config.py : Settings`, `config.py : resolve_database_url` — add `channel`; port defaults become channel factories; derive the channel DB when env + TOML are absent.
- `main.py : lifespan` → `_start_session_store` — opens + migrates the pool against the resolved URL.
- `env_keys.py` — add `CHANNEL` (and an optional base-home override) beside `HOME` / `PROXY_PORT` / `WEB_PORT` / `DATABASE_URL`.
- `cli/launch_options.py` — add a `ChannelOption`; thread through `cli/__init__.py : claude`, `codex`, `desktop`, and the desktop-backend entry. Set the env **before** `get_settings()` can cache.
- `cli/launch_runtime.py : resolve_launch_ports`, `cli/desktop_cmd.py : _resolve_backend_ports` — use the channel proxy/web ports when not pinned; reuse the existing `port_in_use` fail-fast.
- `cli/desktop_cmd.py : prepare_desktop_launch` / `_resolve_storage_dir` / `_build_desktop_backend_env` — carry `TRANSPORT_MATTERS_CHANNEL` so addon, child CLIs, and backend share one identity.
- `cli/ports.py : allocate_port_pair`, `migrations/env.py : _database_url`, `cli/db_cmd.py : _resolve_or_exit` — resolve the same channel URL.
- `api/v1/meta.py : MetaResponse` / `get_meta` — return `channel` / `label` / `color`.

Electron / www:
- `desktop/src/env.ts`, `desktop/src/main.ts : resolveBackendStartupOptions` — read channel; build the channel env.
- `desktop/src/window.ts : createWindowOptions` — channel title; (set `app.setName` + `app.setPath('userData', …)` + dock icon in `main` before app-ready).
- `www/src/main.tsx` (mounts `WindowDragRegion`), `www/src/components/window-drag-region.css`, `www/src/api.ts : Meta` / `fetchMeta` — read `/api/meta`, paint the pill.
- `justfile` — `channel-restart` recipe; keep `install-local` for `stable` only.

A small `ChannelSpec` (one file, e.g. `channel.py`) should own `home`, `database_url`, ports,
Electron identity, and badge color, derived from one channel id — the single source both
languages read.

## Suggested slice order

1. **`ChannelSpec` + resolution-first plumbing** — `channel.py`, `env_keys.py`, `config.py`, `storage_roots.py`; resolve channel before `get_settings()`. Gate: `stable` behaves byte-identically today.
2. **CLI knob + per-channel ports** — `launch_options.py`, `launch_runtime.py`, `desktop_cmd.py`, `ports.py`. Gate: `--channel preview` launches on 8797/8798 against a sibling root.
3. **Ensure-db + `channel-restart` recipe** — db creation/migration step + `justfile`. Gate: fresh `preview` boots past the preflight guards.
4. **Badge** — `meta.py`, `desktop` identity (`app.setName`/`setPath`/icon), `www` pill. Gate: live smoke shows the amber `PREVIEW` pill + distinct dock identity.
5. **`channel promote preview stable`** — promote command. Gate: promotion installs the working-tree build as `stable` without touching session DBs.

Live-launch smoke is the required gate for every launch/desktop/runtime-config slice.
