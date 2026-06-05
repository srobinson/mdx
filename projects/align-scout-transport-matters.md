---
title: Transport Matters Whole App Alignment Scout Against t3code
type: research
tags: [transport-matters, t3code, electron, desktop, architecture, hygiene]
summary: transport-matters keeps a small Electron shell idea from t3code, while the real product divergence is the Python proxy, Postgres session store, wire inspector, canvas, and captured run control plane.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-04
updated: 2026-07-04
---

## Executive Summary

This scout analyzed `transport-matters` on branch `feat/activity-slice-1b-read`, commit `bd64539`, not `main`. The working tree was already dirty before this scout, with 10 entries under `packages/activity` and `pnpm-lock.yaml`; the analysis treats the current tree as the source of truth.

The Electron desktop is an adapted shell, not a close copy of current `t3code`. The biggest divergence is that Transport Matters is a Python owned observability and control plane: proxy capture, breakpoint editing, Postgres session history, canvas managed runs, and desktop backend lifecycle all sit outside t3code's Node and Effect application model.

## Project Metadata

| Area | transport-matters current tree | t3code upstream reference |
| --- | --- | --- |
| Local path | `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters` | `/Users/alphab/Dev/LLM/DEV/helioy/t3code` |
| Branch and commit | `feat/activity-slice-1b-read`, `bd64539` | `review/pingdotgg-main`, `cabc93bad` |
| fmm signal | `.fmm.db` at repo root, plus nested `api/.fmm.db` and `www/.fmm.db` | `.fmm.db` at repo root |
| Scale by fmm | 967 indexed files, 153,629 LOC | 1,938 indexed files, 511,092 LOC |
| Node workspace | pnpm `10.8.1`, root `package.json`, `pnpm-workspace.yaml` | pnpm `10.24.0`, root `package.json`, `pnpm-workspace.yaml` |
| Python workspace | `api/pyproject.toml`, Python `>=3.14`, uv, Hatch, Hatch VCS | No Python app layer in the reference skeleton |
| Main web tooling | Vite, React 19, TypeScript 5.9, Vitest, Playwright, Biome | Vite Plus, TypeScript native preview and tsgo, Vitest through `vp`, Oxlint style linting |
| Desktop tooling | Electron 39, TypeScript NodeNext, Vitest, manual package smoke | Electron 41, vite-plus pack, electron-builder, Effect layers, desktop smoke |
| Release packaging | Python wheel embeds built `www` and `canvas` bundles through Hatch artifacts; root `scripts/release.sh` tags and verifies PyPI | Node package and desktop artifacts through `scripts/build-desktop-artifact.ts`, electron-builder, package registry installers |

Evidence: `package.json`, `pnpm-workspace.yaml`, `tsconfig.base.json`, `desktop/package.json`, `desktop/tsconfig.json`, `desktop/vitest.config.ts`, `api/pyproject.toml`, `scripts/release.sh`, `t3code:package.json`, `t3code:pnpm-workspace.yaml`, `t3code:tsconfig.base.json`, `t3code:apps/desktop/package.json`, `t3code:apps/desktop/vite.config.ts`.

## Repo Map

| Surface | Role | Key evidence |
| --- | --- | --- |
| `api/` | Python product core: mitmproxy addon, FastAPI backend, Postgres session store, CLI launchers, shared proxy process, run manager, desktop backend process support. | `api/src/transport_matters/addon.py::TransportMattersAddon`; `api/src/transport_matters/main.py::create_app`; `api/src/transport_matters/session/writer.py::SessionWriter`; `api/src/transport_matters/run_manager.py::RunManager`; `api/src/transport_matters/cli/desktop_cmd.py::run_desktop_detached` |
| `www/` | React workspace source packages. `shell` composes dev routes, `inspector` is the wire UI, `canvas` is the desktop control surface, `core` holds shared client contracts, `host` holds shared app host primitives. | `www/packages/shell/src/main.tsx`; `www/packages/inspector/src/app.tsx::BrowserAppShell`; `www/packages/canvas/src/session-canvas/SessionCanvasRoute.tsx::SessionCanvasRoute`; `www/packages/core/src/index.ts` |
| `packages/` | Current branch adds `@tm/activity`, a TypeScript server side activity layer reading Postgres records and `tm_events` notifications. | `packages/activity/src/server/index.ts`; `packages/activity/src/adapters/postgresRecords.ts::PostgresActivityReader`; `packages/activity/src/adapters/tmEvents.ts::TmEventsActivityListener` |
| `desktop/` | Thin Electron shell for canvas hosting. It can spawn an Electron owned Python backend or attach to a live detached backend route. | `desktop/src/main.ts::registerAppLifecycle`; `desktop/src/main.ts::registerHostedDesktopLifecycle`; `desktop/src/window.ts::createHostedWindow`; `desktop/src/preload.cts` |
| Build and packaging | Root justfile coordinates Python, web, desktop, and release. Hatch embeds built frontends in the Python wheel. Desktop package smoke verifies a portable Electron package and CommonJS preload. | `justfile`; `api/pyproject.toml`; `desktop/scripts/assert-preload-cjs.mjs`; `desktop/scripts/package-smoke-build.mjs`; `scripts/release.sh` |
| Testing | Root `just test` covers desktop, web shell, activity, and API. API uses pytest, ruff, mypy. Web and desktop use Vitest, with Playwright available for shell end to end and visual tests. | `justfile`; `api/justfile`; `desktop/justfile`; `www/packages/shell/package.json`; `desktop/package.json`; `packages/activity/package.json` |
| Workspace tooling | pnpm workspace includes `packages/*`, `www/packages/*`, and `desktop`; Python stays under `api` with uv. TypeScript strictness comes from root `tsconfig.base.json`, while frontend and desktop each own project configs. | `pnpm-workspace.yaml`; `tsconfig.base.json`; `api/pyproject.toml`; `desktop/tsconfig.json`; `www/packages/*/package.json` |

## Architecture

### Transport Matters product flow

1. CLI launchers create captured runs and environment contracts. Evidence: `api/src/transport_matters/cli/__init__.py`, `api/src/transport_matters/cli/runner.py::run`, `api/src/transport_matters/cli/desktop_cmd.py::prepare_desktop_launch`.
2. The proxy observes wire traffic. Evidence: `api/src/transport_matters/addon.py::TransportMattersAddon`, `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager`, `api/src/transport_matters/pause_session.py::handle_breakpoint`.
3. FastAPI exposes the control plane and serves built products. Evidence: `api/src/transport_matters/main.py::create_app`, `api/src/transport_matters/main.py::mount_frontend_bundles`, `api/src/transport_matters/api/v1/router.py`.
4. Session history is Postgres backed and live through `tm_events`. Evidence: `api/src/transport_matters/session/writer.py::SessionWriter`, `api/src/transport_matters/session/listen.py::SessionEventListener`, `api/src/transport_matters/session/async_dao.py::AsyncSessionDao`.
5. The desktop canvas launches and manages captured agents through the API. Evidence: `api/src/transport_matters/api/v1/run_routes.py::create_run`, `api/src/transport_matters/api/v1/run_routes.py::run_terminal_socket`, `api/src/transport_matters/run_manager.py::RunManager`, `www/packages/canvas/src/session-canvas/SessionCanvasRoute.tsx::SessionCanvasRoute`.

### t3code product flow

`t3code` is a Node and Effect application with `apps/{desktop, server, web, mobile, marketing}` and reusable `packages/{contracts, shared, client-runtime, ssh, tailscale, effect-*}`. Its desktop composes Effect layers in `apps/desktop/src/main.ts`, runs a backend pool with `apps/desktop/src/backend/DesktopBackendManager.ts::makeBackendInstance`, exposes IPC through `apps/desktop/src/ipc/DesktopIpc.ts::make`, and loads a branded desktop app through `apps/desktop/src/window/DesktopWindow.ts::make`.

The inherited idea is the packaged Electron host with a secure preload, main window policy, lifecycle wiring, desktop smoke tests, and workspace tooling. Current t3code has a much richer desktop runtime than this fork uses.

## Desktop Deep Dive

### Key transport-matters desktop files

| File | Key symbols | Role |
| --- | --- | --- |
| `desktop/src/main.ts` | `registerDesktopLifecycleFromEnv`; `registerAppLifecycle`; `registerHostedDesktopLifecycle`; `startBackendAndCreateWindow`; `bindHostedWindowLifecycle`; `awaitPreloadSmokeStatus` | Central Electron main process. Resolves channel identity, chooses hosted attach versus Electron owned backend, starts windows, and drives package smoke. |
| `desktop/src/window.ts` | `createWindowOptions`; `createHostedWindow`; `allowsHostedNavigation`; `shouldOpenExternal`; `showHostedLoadFailure` | BrowserWindow construction and hosted URL safety boundary. Keeps `contextIsolation`, `sandbox`, and `nodeIntegration: false` in one place. |
| `desktop/src/preload.cts` | CommonJS preload bridge at global key `transportMattersDesktop` | Exposes minimal desktop bridge: `appName`, `platform`, and `getPathForFile`. This is far smaller than t3code's `desktopBridge`. |
| `desktop/src/backendProcess.ts` | `buildBackendLaunch`; `launchBackendProcess`; `stopBackendProcess`; `watchBackendExitBeforeReady` | Electron owned Python backend child process support. It shells out to `transport-matters _desktop-backend`. |
| `desktop/src/backendHealth.ts` | `backendHealthUrl`; `waitForBackendHealth`; `isBackendHealthy` | Readiness and health probing for the FastAPI backend. |
| `desktop/src/desktopRuntime.ts` | `readDesktopRuntimeStatus`; `resolveRuntimeStatus`; `reclaimDesktopRuntime`; `liveRuntimePorts`; `parseDesktopRuntimeStatus` | Node side reader for the Python detached runtime record and channel status commands. |
| `desktop/src/hostedLiveness.ts` | `registerHostedBackendLivenessPoll` | Polls a hosted backend from the Electron viewer and quits the viewer after repeated backend health failures. |
| `desktop/src/env.ts` | `ENV`; `resolveDesktopChannelSpec`; `DesktopChannelSpec` | Desktop channel and environment contract reader. Loads copied `channel-specs.json`. |
| `desktop/src/packageSmoke.ts` | `runPackagedAppSmoke`; `findPackagedExecutable` | Portable package smoke runner that launches the built app and waits for the preload smoke marker. |

### Inherited looking pieces

These look inherited or adapted from the t3code Electron skeleton concept, although the current files are not direct one to one copies of t3code's current implementation.

| transport-matters | t3code analogue | Assessment |
| --- | --- | --- |
| `desktop/src/main.ts::registerDesktopLifecycleFromEnv` | `t3code:apps/desktop/src/main.ts`; `t3code:apps/desktop/src/app/DesktopApp.ts::program` | Same high level Electron main entry concern: app identity, readiness, window lifecycle, backend readiness. Transport Matters replaced the Effect layer graph with imperative functions. |
| `desktop/src/window.ts::createWindowOptions` | `t3code:apps/desktop/src/window/DesktopWindow.ts::make`; `t3code:apps/desktop/src/electron/ElectronWindow.ts::make` | Same BrowserWindow safety posture: isolated, sandboxed, no Node integration. Transport Matters only hosts the FastAPI canvas route. |
| `desktop/src/window.ts::allowsHostedNavigation` | `t3code:apps/desktop/src/window/DesktopWindow.ts::isSameOriginRendererNavigation`; `t3code:apps/desktop/src/electron/ElectronProtocol.ts::getDesktopUrl` | Same boundary idea around renderer origin and external navigation. Transport Matters uses loopback HTTP routes rather than a custom desktop protocol. |
| `desktop/src/preload.cts` | `t3code:apps/desktop/src/preload.ts` | Same contextBridge pattern. Transport Matters exposes a minimal bridge, while t3code exposes a large IPC contract through `desktopBridge`. |
| `desktop/vitest.config.ts`; `desktop/src/*.test.ts` | `t3code:apps/desktop/src/*.test.ts` | Same test convention, reduced scope. Transport Matters has 10 desktop tests versus t3code's 49 desktop tests. |
| `pnpm-workspace.yaml`; `tsconfig.base.json` | `t3code:pnpm-workspace.yaml`; `t3code:tsconfig.base.json` | Same monorepo and strict TypeScript baseline, with fewer catalog, patch, and Effect language service conventions. |

### Transport Matters additions

These are product specific and should not be forced back into t3code alignment.

| File | Symbol | Why it is ours |
| --- | --- | --- |
| `desktop/src/backendProcess.ts` | `buildBackendLaunch`; `launchBackendProcess` | Launches the Python CLI command `transport-matters _desktop-backend`, not a Node server package. |
| `desktop/src/backendHealth.ts` | `waitForBackendHealth`; `isBackendHealthy` | Probes FastAPI health over loopback. |
| `desktop/src/desktopRuntime.ts` | `readDesktopRuntimeStatus`; `reclaimDesktopRuntime` | Talks to the Python desktop runtime record and channel status machinery. |
| `desktop/src/hostedLiveness.ts` | `registerHostedBackendLivenessPoll` | Supports detached backend plus hosted Electron viewer mode. |
| `desktop/src/env.ts` | `resolveDesktopChannelSpec`; `ENV` | Reads Transport Matters channel spec and `TRANSPORT_MATTERS_*` process contract. |
| `desktop/src/packageSmoke.ts` | `runPackagedAppSmoke` | Tests our packaged Electron shell and preload marker, independent of t3code release smoke. |
| `api/src/transport_matters/cli/desktop_cmd.py` | `run_desktop_launch`; `run_desktop_detached`; `run_desktop_backend_server`; `serve_desktop_backend` | Python owns desktop backend launch, detached runtime records, uvicorn, and Electron spawn. |
| `api/src/transport_matters/desktop_runtime.py` | `DesktopRuntimeRecord`; `discover_desktop_runtime`; `stop_desktop_record` | Python is the authoritative runtime status and stop owner. |

### Backend process lifecycle

There are two active desktop launch modes.

1. Electron owned backend. `desktop/src/main.ts::registerAppLifecycle` resolves runtime status. If no live matching backend serves the current workspace, it calls `desktop/src/main.ts::startBackendAndCreateWindow`. That launches `desktop/src/backendProcess.ts::launchBackendProcess`, which builds `transport-matters _desktop-backend` through `desktop/src/backendProcess.ts::buildBackendLaunch`. The Python command reaches `api/src/transport_matters/cli/desktop_cmd.py::run_desktop_backend_server` and then `api/src/transport_matters/cli/desktop_cmd.py::serve_desktop_backend`, which runs uvicorn against `api/src/transport_matters/main.py::create_app`. Electron stops its owned child in `desktop/src/main.ts::bindBackendQuitCleanup` through `desktop/src/backendProcess.ts::stopBackendProcess`.
2. Detached backend plus hosted viewer. The CLI path `api/src/transport_matters/cli/desktop_cmd.py::run_desktop_detached` prepares ports and env, starts the backend with `subprocess.Popen`, writes `api/src/transport_matters/desktop_runtime.py::DesktopRuntimeRecord`, waits for readiness, and spawns Electron with `TRANSPORT_MATTERS_DESKTOP_ROUTE_URL`. Electron enters `desktop/src/main.ts::registerHostedDesktopLifecycle`, loads the hosted route, and monitors backend health through `desktop/src/hostedLiveness.ts::registerHostedBackendLivenessPoll`.

The known orphan on close risk is in the detached hosted path. Closing the Electron window reaches `desktop/src/main.ts::bindHostedWindowLifecycle` and quits the Electron app, but no symbol on that path calls `api/src/transport_matters/desktop_runtime.py::stop_desktop_record`. The stop seam exists in Python and is used by `api/src/transport_matters/cli/channel_cmd.py::stop` and `api/src/transport_matters/cli/desktop_recovery.py::_stop_record_or_exit`. The missing alignment is a viewer close event reaching that Python stop seam for detached backends, or an explicit product decision that detached backends intentionally survive viewer close.

## Divergence From t3code Conventions

### Kept conventions

| Convention | Evidence |
| --- | --- |
| pnpm workspace with package level scripts | `pnpm-workspace.yaml`; `package.json`; `desktop/package.json`; `www/packages/*/package.json` |
| Strict TypeScript baseline | `tsconfig.base.json`; `desktop/tsconfig.json`; `www/packages/core/tsconfig.json` |
| Vite and React frontends | `www/vite.shared.ts::productViteConfig`; `www/packages/shell/vite.config.ts::default`; `www/packages/canvas/package.json`; `www/packages/inspector/package.json` |
| Electron with sandboxed preload and secure BrowserWindow defaults | `desktop/src/window.ts::createWindowOptions`; `desktop/src/preload.cts`; `desktop/scripts/assert-preload-cjs.mjs` |
| Vitest for desktop and web unit tests | `desktop/vitest.config.ts`; `desktop/package.json`; `www/packages/shell/package.json`; `packages/activity/package.json` |
| Package exports as boundary declarations | `www/packages/core/package.json`; `www/packages/inspector/package.json`; `www/packages/canvas/package.json`; `packages/activity/package.json` |

### Dropped or replaced conventions

| t3code convention | transport-matters replacement | Evidence |
| --- | --- | --- |
| `apps/*` app topology | Top level `api/`, `desktop/`, `www/packages/*`, `packages/activity` | `pnpm-workspace.yaml`; fmm repo map |
| Node server owns runtime | Python FastAPI and mitmproxy own runtime | `api/src/transport_matters/main.py::create_app`; `api/src/transport_matters/addon.py::TransportMattersAddon` |
| Effect service graph in desktop | Small imperative Electron main process | `desktop/src/main.ts::registerDesktopLifecycleFromEnv`; `t3code:apps/desktop/src/main.ts`; `t3code:apps/desktop/src/app/DesktopApp.ts::program` |
| `packages/contracts` plus schema validated IPC | Minimal preload bridge plus HTTP API contracts in `@tm/core` | `desktop/src/preload.cts`; `www/packages/core/src/transport.ts`; `api/src/transport_matters/api/v1/run_routes.py::CreateRunRequest` |
| vite-plus and `vp` task runner | `just`, uv, pnpm, Vite, Hatch | `justfile`; `api/justfile`; `api/pyproject.toml`; `www/vite.shared.ts::productViteConfig` |
| electron-builder and updater stack | Manual package smoke and Python release flow | `desktop/scripts/package-smoke-build.mjs`; `desktop/src/packageSmoke.ts::runPackagedAppSmoke`; `scripts/release.sh` |
| Custom desktop protocol for renderer | Direct loopback hosted routes | `desktop/src/window.ts::rendererUrlForPort`; `desktop/src/window.ts::createHostedWindow`; `t3code:apps/desktop/src/electron/ElectronProtocol.ts::getDesktopUrl` |
| Rich IPC bridge for local environments, updates, preview automation | HTTP API plus tiny desktop bridge | `t3code:apps/desktop/src/preload.ts`; `desktop/src/preload.cts`; `api/src/transport_matters/api/v1/router.py` |
| WSL, SSH, Tailscale, Clerk, updater, preview webview subsystems | No equivalent in this fork's Electron shell | `t3code:apps/desktop/src/wsl/DesktopWslEnvironment.ts`; `t3code:apps/desktop/src/ssh/DesktopSshEnvironment.ts`; `t3code:apps/desktop/src/backend/DesktopServerExposure.ts`; `desktop/src/main.ts` |

## Genuine Product Divergence With No t3code Equivalent

| Surface | Why divergence is legitimate | Evidence |
| --- | --- | --- |
| Wire proxy and breakpoint editing | Transport Matters observes provider wire bytes and can pause outbound requests before upstream. t3code orchestrates coding agents through its server and provider runtime, not a transparent wire proxy. | `api/src/transport_matters/addon.py::TransportMattersAddon`; `api/src/transport_matters/pause_session.py::handle_breakpoint`; `api/src/transport_matters/api/v1/breakpoint_routes.py::release_flow` |
| Codex explicit HTTPS proxy | Codex traffic capture is a product level feature. t3code talks to provider runtimes through app server abstractions. | `api/src/transport_matters/codex/transport.py`; `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager` |
| Tier 1 capture store | Per run raw and derived wire artifacts are the product source of truth. t3code has orchestration state, not a wire artifact corpus. | `api/src/transport_matters/storage/disk.py::DiskStorageBackend`; `api/src/transport_matters/api/v1/exchanges.py::ExchangeDetailResponse` |
| Postgres session store and transcript correlation | Transport Matters correlates wire and transcript streams and exposes owner scoped session history. | `api/src/transport_matters/session/writer.py::SessionWriter`; `api/src/transport_matters/session/async_dao.py::AsyncSessionDao`; `api/src/transport_matters/session/listen.py::SessionEventListener` |
| Wire inspector UI | The inspector is a purpose built view over captured exchanges, breakpoint state, and transport diagnostics. | `www/packages/inspector/src/app.tsx::BrowserAppShell`; `www/packages/inspector/src/components/ExchangeDetail.tsx::ExchangeDetail` |
| Canvas managed runs | Canvas panes launch captured agents through FastAPI and attach PTYs over WebSocket. t3code desktop focuses on its own app shell, preview, and server connection runtime. | `www/packages/canvas/src/session-canvas/SessionCanvasRoute.tsx::SessionCanvasRoute`; `api/src/transport_matters/run_manager.py::RunManager`; `api/src/transport_matters/api/v1/run_routes.py::run_terminal_socket` |
| Activity package on current branch | `@tm/activity` reads session and run lifecycle data from the Transport Matters Postgres event surface. | `packages/activity/src/server/index.ts`; `packages/activity/src/adapters/tmEvents.ts::TmEventsActivityListener`; `packages/activity/src/adapters/postgresRecords.ts::PostgresActivityReader` |

## Structure and Hygiene Findings

### File and function sizing

| Finding | Severity | Evidence | Recommendation |
| --- | --- | --- | --- |
| `api/src/transport_matters/cli/desktop_cmd.py` is 697 LOC, just under the 700 LOC hard limit. It mixes plan construction, Electron resolution, detached process management, uvicorn serving, env construction, and CLI exit handling. | High | `api/src/transport_matters/cli/desktop_cmd.py::prepare_desktop_launch`; `::run_desktop_launch`; `::run_desktop_detached`; `::serve_desktop_backend`; `::resolve_electron_launch` | Split into `desktop_plan.py`, `desktop_process.py`, and `desktop_electron.py` before adding more desktop behavior. |
| `api/src/transport_matters/run_manager.py` is 682 LOC and `RunManager` is a 574 LOC class. Methods are moderate in size, but the class owns spawn admission, PTY IO, lifecycle events, attachment management, and teardown. | Medium | `api/src/transport_matters/run_manager.py::RunManager` | Keep new run lifecycle features out of this class unless extracted into collaborators first. |
| `desktop/src/main.ts` is 655 LOC. Functions are under the threshold, but the file combines channel identity, hosted attach, owned backend spawn, preload smoke, and lifecycle policy. | Medium | `desktop/src/main.ts::registerDesktopLifecycleFromEnv`; `::registerAppLifecycle`; `::registerHostedDesktopLifecycle`; `::awaitPreloadSmokeStatus` | Extract hosted attach and package smoke into separate modules. |
| `api/src/transport_matters/desktop_runtime.py` is 655 LOC. It is cohesive around runtime records, status, liveness, serialization, and stop, but close enough to the threshold to protect. | Medium | `api/src/transport_matters/desktop_runtime.py::discover_desktop_runtime`; `::stop_desktop_record`; `::desktop_runtime_status_to_json` | Add new desktop runtime behavior through a separate module, then consider moving JSON serialization and liveness probing out. |
| `www/packages/canvas/src/session-canvas/lab/CanvasLabRoute.tsx::CanvasLabRoute` is exactly at the 150 LOC function threshold and the file is 573 LOC. | Medium | `www/packages/canvas/src/session-canvas/lab/CanvasLabRoute.tsx::CanvasLabRoute` | Extract selector wiring or pane rendering before expanding the lab route. |
| t3code desktop has much larger functions and files. Transport Matters should not copy that hygiene profile. | Medium | `t3code:apps/desktop/src/window/DesktopWindow.ts::make`; `t3code:apps/desktop/src/backend/DesktopBackendManager.ts::makeBackendInstance`; `t3code:apps/desktop/src/preview/Manager.ts::Manager` | Align to the concept, not the file sizing. |

### Duplication and boundary risks

| Finding | Evidence | Recommendation |
| --- | --- | --- |
| Cross language environment constants are parallel maintained. Python declares `TRANSPORT_MATTERS_*` keys in `api/src/transport_matters/env_keys.py`, while Electron repeats a subset in `desktop/src/env.ts::ENV`. | `api/src/transport_matters/env_keys.py::ENV_PREFIX`; `api/src/transport_matters/env_keys.py::DESKTOP_ROUTE_URL`; `desktop/src/env.ts::ENV` | Generate a small JSON env contract or keep an explicit test asserting parity. |
| Desktop backend command string is duplicated in Python and TypeScript. | `desktop/src/backendProcess.ts::DESKTOP_BACKEND_COMMAND`; `api/src/transport_matters/cli/desktop_cmd.py::DESKTOP_BACKEND_COMMAND` | Move to generated channel or desktop contract metadata, or add parity tests. |
| Runtime status models are duplicated across Python and TypeScript. Some duplication is necessary at the language boundary, but the contract is ad hoc. | `api/src/transport_matters/desktop_runtime.py::DesktopRuntimeStatusJson`; `desktop/src/desktopRuntime.ts::DesktopRuntimeStatus`; `desktop/src/desktopRuntime.ts::parseDesktopRuntimeStatus` | Prefer a generated schema, or pin the JSON response shape with cross language fixture tests. |
| Desktop hosted lifecycle policy is split across the Electron viewer and Python runtime stop seam. | `desktop/src/main.ts::bindHostedWindowLifecycle`; `desktop/src/hostedLiveness.ts::registerHostedBackendLivenessPoll`; `api/src/transport_matters/desktop_runtime.py::stop_desktop_record` | Decide whether detached backend survives viewer close. If it should stop, route close through a Python stop endpoint or command. |
| `www/packages/shell` is a dev only composer, while production bundles live in `api/src/transport_matters/www` and `api/src/transport_matters/canvas`. This is sound, but easy to confuse with t3code's `apps/web` convention. | `www/packages/shell/package.json`; `www/vite.shared.ts::productViteConfig`; `api/src/transport_matters/main.py::mount_frontend_bundles` | Keep docs explicit that `www/packages/shell` is not a shipped app. |

## Alignment Guidance

1. Preserve t3code alignment at the Electron shell concept level: secure BrowserWindow defaults, preload bridge discipline, package smoke, app identity, and clear desktop lifecycle seams.
2. Do not align product architecture to t3code's Node server, Effect layer graph, IPC contract package, or desktop subsystem sprawl. Those conventions solve different product constraints.
3. For future desktop cleanup, use t3code as a source of seam names, not as a source of file sizes. Good names to borrow are `DesktopLifecycle`, `DesktopWindow`, `DesktopBackendManager`, and `DesktopEnvironment`; avoid importing the Effect runtime model unless the whole desktop moves that way.
4. The most valuable alignment fix is lifecycle clarity: make detached backend ownership explicit. The current code has Python stop machinery, but hosted Electron close does not reach it.
5. The most valuable hygiene fix is to split `api/src/transport_matters/cli/desktop_cmd.py` before the next desktop feature. It sits one small change away from the repo hard limit.

## Open Questions

1. Should a detached desktop backend intentionally survive Electron viewer close, or should viewer close stop it by default? Current evidence shows the stop seam exists but is not wired into hosted window close.
2. Should the TypeScript desktop contract be generated from Python owned env and runtime schemas?
3. Should `desktop/src/main.ts` remain a small imperative shell, or should it be split into named modules that mirror t3code's `DesktopLifecycle`, `DesktopWindow`, and `DesktopEnvironment` boundaries without adopting Effect?
4. Should `@tm/activity` become part of the core workspace topology, or is it branch local experimentation on `feat/activity-slice-1b-read`?
