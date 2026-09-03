---
title: Transport Matters desktop application map
type: projects
tags: [transport-matters, tm, desktop, electron, architecture]
summary: Source-verified map of the Transport Matters desktop shell, gateway integration, IPC, browser panes, packaging, and lifecycle.
status: active
project: tm
confidence: high
source: e97488ea
---

<!-- fmm:map sha=e97488ea branch=fix/canvas-runs-shared-proxy dirty=false generated=2026-09-05T18:50:28+07:00 files=80 loc=11250 -->

# Transport Matters desktop map

## Overview

`desktop/` is the Electron shell. The maintained code owns the Electron main process, a CommonJS sandboxed preload, the loopback web renderer window, one or more third party browser panes, the local CDP front used by those panes, and supervision of a Python backend plus a TypeScript gateway. The renderer UI itself is served by the backend at `/canvas`; there is deliberately no second renderer route tree under `desktop/`, which is enforced by `desktop/src/rendererBoundary.test.ts:16-25`.

Start with `desktop/src/main.ts:33-137`, then follow `desktop/src/app/backendStartup.ts:252-410` for process selection and lifecycle composition, `desktop/src/window.ts:13-154` for the window security boundary, and `desktop/src/app/browserPanes/registerBrowserPaneHost.ts:28-155` for the IPC seam. The source tree is 80 maintained files and 11,250 lines at commit `e97488ea`; `desktop/dist/` is ignored generated output (`desktop/.gitignore:1-5`) and is described below only where packaging behavior depends on it.

The high-level rule is: main owns privileged OS and child-process work; the web renderer owns product UI and communicates through one frozen preload bridge; pane contents are isolated third party pages; the gateway owns run lifecycle and pane state while desktop owns the native views.

## Confidence and method

I opened 87 distinct repository files directly: 78 desktop files and 9 cross-package endpoint, contract, gateway, API, and canvas files. The module inventory covers all 80 maintained files under `desktop/`; two inventory entries are an image asset and `.gitignore`, while the remaining files have source citations. I verified both endpoints of the Electron `tm:browser-panes` seam, the devtools capability seam, browser-pane presentation and observation flow, backend and gateway startup and shutdown, package-smoke preload loading, and the canvas `/canvas` route. For those seams, claims are based on reading the sender, receiver, payload or boundary validator, and relevant tests where present.

Some claims are single-read inferences from an owning file or configuration: leaf-file responsibility rows, the exact OS packaging behavior, the absence of macOS permission prompt handling, and the implications of unsigned output. They are marked as conventions or landmines rather than runtime observations. The typecheck proves that production, test, and script TypeScript graphs compile. The 204-test run proves the checked mock, unit, and integration scenarios. Neither proves a real GUI paint, a signed or notarized macOS artifact, a live control-plane grant, or a packaged standalone run.

The provenance check ran `git diff --stat 730aaa96 e97488ea` and found seven changed files, all under `api/` or `TLDR.md`; no cited `desktop/` file changed. One cited cross-package file, `api/src/transport_matters/main.py`, is in that diff, but its change is in `lifespan` service wiring at lines 438-440, not the cited `/canvas` route at lines 166-190. I reread that changed file at `e97488ea` and retained the current route citation. I did not run `package:smoke`, `standalone:smoke`, `browser-pane-proof`, a manual Electron GUI launch, or a signed/notarized build, so those runtime boundaries remain source-verified rather than executed here.

## Process model and trust boundaries

| Process or context | What it is allowed to do | Source evidence |
| --- | --- | --- |
| Electron main | Has Electron and Node access. It creates `BrowserWindow` and `WebContentsView`, registers `ipcMain`, launches and stops Python and gateway children, opens the local CDP WebSocket front, reads channel configuration, calls the CLI for runtime discovery, shows dialogs, and opens approved external URLs. Main imports these capabilities directly in `desktop/src/main.ts:1-25`, `desktop/src/window.ts:1-5`, `desktop/src/backendProcess.ts:1-5`, and `desktop/src/browserPaneDevtoolsFront.ts:1-6`. | Full privilege is concentrated here. Treat every value arriving from a renderer as external input even though the normal renderer is the app's loopback page. |
| App renderer | The canvas SPA loaded from `http://127.0.0.1:<webPort>/canvas`. Electron disables Node integration, enables context isolation and sandboxing, and supplies only the preload path (`desktop/src/window.ts:32-59`). The renderer can use ordinary browser APIs and the exposed desktop bridge, then makes same-origin HTTP and SSE calls to the backend, as shown by `www/packages/canvas/src/browsing/browserPaneClient.ts:17-27` and `www/packages/canvas/src/browsing/useBrowserPaneStream.ts:16-41`. It cannot require Node or Electron. | The bridge is the only renderer-to-main capability surface. The main side scopes incoming IPC by `event.sender === window.webContents` and drops malformed frames (`desktop/src/app/browserPanes/registerBrowserPaneHost.ts:58-76`, `desktop/src/app/browserPanes/registerBrowserPaneHost.ts:89-155`). |
| Sandboxed preload | Runs as CommonJS because `webPreferences.sandbox` is true. It may require Electron and does not require sibling files; its two runtime literals are inlined (`desktop/src/preload.cts:1-19`). It listens and sends on the pane IPC channel, obtains dropped file paths through `electron.webUtils`, and exposes a frozen API with `contextBridge` (`desktop/src/preload.cts:31-64`). | The emitted file must be `dist/preload.cjs`; loading an ESM preload would fail before the bridge exists. The build guard checks this (`desktop/scripts/assert-preload-cjs.mjs:1-48`). Type-only contract imports in the source compile away; a runtime import from `@tm/contract` would break the package import guard. |
| Browser pane renderer | Each pane is a native `WebContentsView` containing a third party page. It has its own persistent named partition, sandbox, context isolation, no Node integration, web security, no preload, and denied downloads and permission requests (`desktop/src/app/browserPanes/viewPolicy.ts:4-18`, `desktop/src/app/browserPanes/viewPolicy.ts:60-74`). It can navigate only to `http:`, `https:`, or `about:blank` (`desktop/src/app/browserPanes/viewPolicy.ts:20-38`). | A pane cannot directly use the app bridge. Its `window.open` is denied and becomes an `open-request` message emitted by main to the app renderer (`desktop/src/app/browserPanes/viewPolicy.ts:40-56`). |
| Pane CDP client | The canvas or a director connects to a loopback WebSocket endpoint published by main. The connection must present a capability minted by the control plane, and every command rechecks that grant (`desktop/src/browserPaneDevtoolsFront.ts:237-320`). The front exposes only targets belonging to the authorized canvas and routes approved CDP commands to Electron's debugger (`desktop/src/browserPaneDevtoolsFront.ts:322-445`). | This is a second trust boundary. The socket is loopback but capability authorization and canvas scoping are mandatory; unauthenticated upgrades get HTTP 401 and a revoked grant closes the socket with policy violation (`desktop/src/browserPaneDevtoolsFront.ts:242-288`). |

The bridge key and channel are contract literals, duplicated only because the sandbox cannot import the desktop-owned CommonJS mirror. The published contract defines `transportMattersDesktop` and `tm:browser-panes`, and `desktop/src/bridgeKeys.cts` mirrors them (`packages/contract/src/desktop/index.ts:1-15`, `desktop/src/bridgeKeys.cts:1-9`). `desktop/src/bridgeKeys.test.ts:5-14` and `desktop/src/preload.test.ts:34-80` protect the duplication.

## Topology and module map

### Configuration, build, packaging, and scripts

| File | Responsibility |
| --- | --- |
| `desktop/package.json:1-37` | Private Electron package metadata, `dist/main.js` entry, build, dev, package smoke, standalone bundle, standalone smoke, test, and three-project typecheck commands; production dependency is `ws`. |
| `desktop/electron-builder.yml:1-35` | Standalone app configuration: app id, product name, `transport-matters` executable name, `dist` and assets inclusion, Python and gateway `extraResources`, ASAR, macOS dir/DMG targets, Linux dir target, and explicitly unsigned macOS identity. |
| `desktop/justfile:1-31` | Short developer recipes for test, typecheck, build, dev, package smoke, browser pane proof, and the default `check` aggregate. |
| `desktop/tsconfig.json:1-42` | NodeNext strict production compilation from `src` to `dist`; explicitly includes each production module so accidental new entry points do not silently enter the build. |
| `desktop/tsconfig.scripts.json:1-9` | Script compilation project extending the workspace bundler config and including `scripts/*.ts`. |
| `desktop/tsconfig.test.json:1-9` | No-emit test typecheck covering all `.ts` and `.cts` under `src`. |
| `desktop/vitest.config.ts:1-25` | Vitest configuration and a custom CommonJS transform for `.cts` tests, because the preload and bridge-key modules use `export =`. |
| `desktop/assets/preview-amber.png` | Preview and dev channel dock/window icon selected by `channelIdentity.ts`; the code resolves it relative to the compiled app module (`desktop/src/app/channelIdentity.ts:6-10`, `desktop/src/app/channelIdentity.ts:42-45`). |
| `desktop/.gitignore:1-22` | Excludes dependencies, `dist`, compiler metadata, coverage, test output, editor files, OS files, and debug logs. |
| `desktop/scripts/copy-channel-specs.mjs:1-13` | Copies the API channel specification into `dist/channel-specs.json` after TypeScript compilation. |
| `desktop/scripts/assert-preload-cjs.mjs:1-48` | Removes stale pre-rename ESM preload artifacts and fails if `dist/preload.cjs` is missing or contains top-level ESM syntax. |
| `desktop/scripts/assert-packaged-imports.ts:1-71` | Scans emitted JS/CJS/MJS and rejects imports that cannot resolve from the packaged app's relative files, Node builtins, Electron, or manifest production dependencies. |
| `desktop/scripts/packagedDist.mjs:1-9` | Defines `package-smoke` and `standalone` as generated dist entries excluded from the app graph. |
| `desktop/scripts/packagedDist.d.mts:1` | Type declaration for the `isPackagedDistEntry` helper used by the TypeScript packaging guard. |
| `desktop/scripts/package-smoke-build.mjs:1-84` | Builds a hand-rolled Electron package for preload smoke testing, with a macOS `.app` branch and portable Linux/Windows branch, copying only packaged dist entries. |
| `desktop/scripts/bundle-python.mjs:1-194` | Stages relocatable standalone CPython, installs the exact wheel and dependencies, copies the CA bundle and embedded gateway, prunes dangling symlinks, and verifies executable and embedded bundle completeness before electron-builder. |
| `desktop/scripts/browserPaneProof.ts:1-52` | Playwright adapter that launches Electron with `desktopDir`, isolated cwd/env, and a per-run token, then delegates the black-box pane proof. |

### Main-process source

| File | Responsibility |
| --- | --- |
| `desktop/src/main.ts:1-137` | Composition root. Resolves channel identity, chooses package smoke, hosted viewer, or managed lifecycle, decorates every main window with pane hosting, creates the devtools authorizer, and invokes registration at module load. |
| `desktop/src/window.ts:1-154` | Main app window construction, preload path resolution, secure `BrowserWindow` options, loopback URL validation, same-origin navigation policy, safe HTTPS external opening, and load-failure dialog. |
| `desktop/src/preload.cts:1-64` | Sandboxed CommonJS bridge. Publishes app metadata, dropped-file path access, pane presentation/announce/subscription, and the pending devtools endpoint promise. |
| `desktop/src/bridgeKeys.cts:1-9` | Runtime CommonJS mirror of the two contract literals needed by main and the packaged preload smoke. |
| `desktop/src/rendererUrl.ts:1-9` | Pure loopback renderer URL builder, defaulting to port 8788 and `/canvas`. |
| `desktop/src/app/channelIdentity.ts:1-46` | Applies channel app name, application id, channel-specific Electron user-data path, and optional preview dock icon before readiness. |
| `desktop/src/env.ts:1-211` | Canonical environment keys, channel-spec loading and validation, default stable channel, channel home resolution, and source-versus-dist channel-spec path choice. |
| `desktop/src/jsonReaders.ts:1-55` | Boundary readers for records, required/optional strings, ports, and strict string port overrides. |
| `desktop/src/app/hostedLifecycle.ts:1-168` | Hosted-window factory and lifecycle. Creates the window after `app.whenReady`, optionally starts health liveness polling, handles activation and window-all-closed, and derives `/health` from a route URL. |
| `desktop/src/app/DesktopLifecycle.ts:1-113` | Shared Electron/process lifecycle adapter. Registers `before-quit`, POSIX signal forwarding, activation replacement windows, and platform window-close policy. |
| `desktop/src/app/DesktopShutdown.ts:1-82` | Idempotent coordinated shutdown gate. Prevents the first `before-quit`, runs finalizers serially while logging individual failures, then permits and calls `app.quit`. |
| `desktop/src/hostedLiveness.ts:1-73` | Polls a hosted backend once the first page load succeeds, resets on success, quits after three consecutive failures, and cancels timers when the window closes. |
| `desktop/src/app/backendStartup.ts:1-452` | Managed startup orchestration: runtime discovery/reclaim, bundled versus ambient launch, backend and gateway readiness, startup diagnostics, lifecycle binding, and gateway-first finalizer order. |
| `desktop/src/desktopRuntime.ts:1-189` | Reads and validates `transport-matters channel status --json`, accepts only the requested channel, exposes live ports, and invokes `_desktop-reclaim` with bounded CLI timeouts. |
| `desktop/src/backendProcess.ts:1-208` | Builds and spawns the Python `_desktop-backend` child, switches to an absolute bundled interpreter when packaged, drains both pipes, optionally forwards smoke output, and watches pre-readiness exit/error. |
| `desktop/src/backendHealth.ts:1-92` | Loopback `/health` URL, per-probe abort timeout, 250 ms polling interval, and 15 second readiness deadline. |
| `desktop/src/backend/DesktopBackendManager.ts:1-91` | Generic one-child supervisor with single-start guard, exit ownership clearing, memoized stop, and grace-then-force termination. |
| `desktop/src/lifecycle/graceThenForce.ts:1-53` | Sends SIGTERM, waits the configured grace, sends SIGKILL if needed, and resolves even when a wedged child never reports exit. |
| `desktop/src/gateway/gatewayProcess.ts:1-319` | Resolves workspace or packaged gateway entry, builds direct Node/Electron-as-Node launch, injects capture RPC, channel home, database, parent-watch, captures output tail, and spawns the gateway. |
| `desktop/src/app/bundledResources.ts:1-70` | Resolves packaged Python, gateway, and CA paths under `process.resourcesPath`; returns null in dev and builds the packaged child environment. |
| `desktop/src/app/packageSmokeLifecycle.ts:1-128` | Window-only package smoke. Loads the real preload against `about:blank`, checks the exposed bridge in a renderer, writes a marker, and quits without spawning backend or gateway. |
| `desktop/src/packageSmoke.ts:1-213` | Finds a packaged executable safely across macOS/Linux/Windows, launches it with package-smoke env, waits for clean exit, and validates the readiness marker. |
| `desktop/src/standaloneSmoke.ts:1-231` | Black-box standalone app acceptance smoke. Scrubs PATH, seeds fake Codex credentials, launches from cwd `/`, polls backend health, creates a canvas/run, and requires `EXITED`. |
| `desktop/src/browserPaneDevtoolsFront.ts:1-503` | Main-owned loopback WebSocket CDP front. Authorizes capability upgrades, scopes clients to canvases, registers Electron debugger targets, serializes commands per client, rechecks grants, relays events, and closes all resources. |
| `desktop/src/app/browserPanes/viewPolicy.ts:1-74` | Browser pane sandbox posture, persistent partition, URL allowlist, `window.open` relay, permission denial, and download denial. |
| `desktop/src/app/browserPanes/BrowserPaneHost.ts:1-271` | Reconciles complete pane frames into native views, applies bounds/visibility, sequence-gated navigation, observations, history stepping, crash recovery, and destruction. |
| `desktop/src/app/browserPanes/registerBrowserPaneHost.ts:1-155` | Per-window IPC registration, sender scoping, payload parsing, devtools query response, announce handling, host-message send, and close cleanup. |
| `desktop/src/app/browserPanes/BrowserPaneHostRegistry.ts:1-27` | Tracks all live window hosts so pane views are disposed before child processes stop. |
| `desktop/src/mcpClient.ts:1-70` | Minimal bearer-authenticated JSON-RPC MCP client used by the browser pane proof to call control-plane tools. |
| `desktop/src/smokeHttp.ts:1-167` | Loopback HTTP JSON, origin header, free-port, readiness polling, and smoke canvas creation helpers. |
| `desktop/src/browserPaneProof.ts:1-445` | End-to-end pane proof flow: isolated shell, canvas/run, pane open, CDP attach, navigation, history, reload, history assertions, close, and cleanup. |
| `desktop/src/browserPaneProofSupport.ts:1-196` | Pane-proof environment, fake long-lived Codex harness, credential/bearer extraction, local proof pages, agent-browser process wrapper, and tab parsing. |
| `desktop/src/browserPaneProofLifecycle.ts:1-234` | Pane-proof residue identity, stale-run reclamation, resource stack, signal finalizer, and bounded shell teardown. |
| `desktop/src/testing/electronMock.ts:1-266` | Vitest Electron fixture: app, windows, views, sessions, web contents, IPC handler maps, debugger stubs, and reset defaults. |
| `desktop/src/testing/loadCommonJsSource.ts:1-46` | Transpiles/evaluates `.cts` source in a fresh VM with a stubbed `require`, matching Electron's CommonJS preload loading. |

### Tests, one line per maintained test file

| File | Coverage |
| --- | --- |
| `desktop/src/main.test.ts:130-671` | Window security, dual-child readiness/order, startup failures, env/port selection, channel identity, runtime hosting, package smoke, and preload probe. |
| `desktop/src/main.reclaim.test.ts:140-286` | Reclaim of stale or wrong-workspace runtimes and managed backend shutdown before app quit. |
| `desktop/src/main.standalone.test.ts:73-107` | Packaged branch bypasses discovery/reclaim and launches from the buyer home with bundled child env. |
| `desktop/src/main.devtools.test.ts:32-60` | Every lifecycle route uses the pane-decorating window factory and devtools front. |
| `desktop/src/preload.test.ts:34-80` | CommonJS preload dependency restriction, bridge shape, devtools query, frame/announce sends, and subscription fan-out. |
| `desktop/src/window.test.ts:118-346` | URL normalization, secure window options, navigation/external policy, load errors, hosted lifecycle, and liveness. |
| `desktop/src/rendererBoundary.test.ts:16-25` | Prevents a duplicate renderer route tree from being added under desktop. |
| `desktop/src/env.test.ts:7-53` | Env literal parity, home override, stable default, and preview channel resolution. |
| `desktop/src/desktopRuntime.test.ts:13-104` | Runtime JSON parsing, CLI status lookup, wrong-channel fallback, and reclaim command. |
| `desktop/src/backendProcess.test.ts:24-247` | Backend command/env shape, packaged interpreter invocation, stdio drain, smoke forwarding, and pre-readiness failures. |
| `desktop/src/backendHealth.test.ts:9-83` | Health polling, total timeout, per-probe abort, and timer cleanup. |
| `desktop/src/backend/DesktopBackendManager.test.ts:42-93` | Start guard, idempotent stop, exit ownership clearing, and no-op stop. |
| `desktop/src/lifecycle/graceThenForce.test.ts:26-91` | Graceful exit, forced exit, bounded wedged-child resolution, and already-gone child. |
| `desktop/src/gateway/gatewayProcess.test.ts:25-240` | Entry resolution, direct Node/tsx launch, parent watch, channel/database env, output tail, and gateway grace budget. |
| `desktop/src/app/DesktopLifecycle.test.ts:27-200` | Signal behavior, before-quit routing, platform close policy, activation window recreation, and shutdown integration. |
| `desktop/src/app/DesktopShutdown.test.ts:9-198` | Finalizer sequencing, reentrant quit gate, logged failure continuation, and gateway-before-Python order. |
| `desktop/src/app/bundledResources.test.ts:17-50` | Packaged resource path construction, dev null behavior, CA precedence, and child env. |
| `desktop/src/app/browserPanes/viewPolicy.test.ts:19-74` | URL allowlist, denied `window.open`, and once-per-session permission/download denial. |
| `desktop/src/app/browserPanes/BrowserPaneHost.test.ts:66-394` | View reconciliation, seq semantics, history, observations, bounds/visibility, crash recreation, announce replay, and target registration. |
| `desktop/src/app/browserPanes/registerBrowserPaneHost.test.ts:46-195` | Sender scoping, boundary parsing, devtools response/fallback, announce, host message forwarding, and close cleanup. |
| `desktop/src/app/browserPanes/BrowserPaneHostRegistry.test.ts:9-29` | Quit disposal and removal after a window closes independently. |
| `desktop/src/browserPaneDevtoolsFront.test.ts:160-403` | Capability/canvas scoping, rogue origin and no-capability refusal, race handling, protocol errors, target teardown, and destroyed contents. |
| `desktop/src/browserPaneProofLifecycle.test.ts:33-187` | PID identity, residue round trip, reclaim, reverse cleanup, aggregate failures, and signal finalization. |
| `desktop/src/browserPaneProofSupport.test.ts:20-167` | Isolated proof env, fake harness, bearer extraction, local pages, tabs, and nonblocking agent-browser wrapper. |
| `desktop/src/standaloneSmoke.test.ts:11-99` | Isolated standalone env, fake credential, display forwarding, and omission of hosted/package-smoke flags. |
| `desktop/src/packageSmoke.test.ts:20-203` | Package command contract, executable discovery, dangling symlink handling, and smoke marker process. |
| `desktop/src/smokeHttp.test.ts:5-29` | Free-port helper and poll-value success/timeout reporting. |
| `desktop/src/mcpClient.test.ts:4-29` | Structured-content preference, text fallback, and missing payload errors. |
| `desktop/src/bridgeKeys.test.ts:5-14` | Runtime bridge literals equal the published desktop contract. |

## IPC surface

There is exactly one Electron IPC channel in the maintained desktop source. Search evidence is `desktop/src/preload.cts:31-52` and `desktop/src/app/browserPanes/registerBrowserPaneHost.ts:38-81`; there are no other `ipcRenderer`, `ipcMain.handle`, or `ipcRenderer.invoke` calls.

### `tm:browser-panes`

| Direction | Payload | Sender endpoint | Receiver endpoint | Boundary notes |
| --- | --- | --- | --- | --- |
| App renderer to main | A complete `BrowserPanePlacementFrame`: `{ canvasId: string, placements: BrowserPanePlacement[] }`. Each placement has `browserPaneId`, integer `{x,y,width,height}` bounds, `visible`, and a seq-gated navigation intent: `{kind:"url", url, seq}` or `{kind:"history", url, delta:-1|1, seq}` (`packages/contract/src/desktop/index.ts:51-78`). | Canvas rAF presenter computes and sends the full frame through `getBrowserPaneBridge().present(frame)` (`www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:57-133`), then preload calls `ipcRenderer.send` (`desktop/src/preload.cts:47-50`). | `registerBrowserPaneHost` installs an `ipcMain.on` listener per `BrowserWindow` (`desktop/src/app/browserPanes/registerBrowserPaneHost.ts:34-40`, `desktop/src/app/browserPanes/registerBrowserPaneHost.ts:58-77`), then calls `BrowserPaneHost.present` (`desktop/src/app/browserPanes/registerBrowserPaneHost.ts:74-76`). | Crosses the app-renderer to main trust boundary. Main checks sender object identity, validates every nested field, rejects fractional/negative dimensions and invalid navigation, and drops malformed frames without throwing (`desktop/src/app/browserPanes/registerBrowserPaneHost.ts:89-155`). |
| App renderer to main | `{ kind: "announce" }`, with no other fields required. | Preload `browserPanes.announce()` (`desktop/src/preload.cts:51-53`), called after a new browsing stream snapshot (`www/packages/canvas/src/browsing/useBrowserPaneStream.ts:68-78`). | `registerBrowserPaneHost` recognizes the query and calls `host.announce()` (`desktop/src/app/browserPanes/registerBrowserPaneHost.ts:70-72`). | Sender identity is still checked before query handling (`desktop/src/app/browserPanes/registerBrowserPaneHost.ts:58-60`). Announce replays each live observation with a fresh timestamp (`desktop/src/app/browserPanes/BrowserPaneHost.ts:103-110`). |
| App renderer to main | `{ kind: "devtools" }`, a query with no endpoint supplied by the renderer. | Preload sends it once at load (`desktop/src/preload.cts:31-38`). | `registerBrowserPaneHost` waits for the main-owned front and sends a `{kind:"devtools", devtools: DevtoolsEndpoint}` answer (`desktop/src/app/browserPanes/registerBrowserPaneHost.ts:43-67`). | The renderer cannot choose the endpoint. Main returns either `{kind:"live",url}` or `{kind:"unavailable",reason:"devtools_unreachable"}` from its own front (`packages/contract/src/desktop/index.ts:17-24`). |
| Main to app renderer | `{ kind: "devtools", devtools: DevtoolsEndpoint }`. | `registerBrowserPaneHost` calls `webContents.send` only on the window that owns the host (`desktop/src/app/browserPanes/registerBrowserPaneHost.ts:40-42`, `desktop/src/app/browserPanes/registerBrowserPaneHost.ts:61-67`). | Preload's channel listener resolves the pending `browserPanes.devtools` promise (`desktop/src/preload.cts:31-35`, `desktop/src/preload.cts:60-61`); canvas waits for it before declaring a composited presenter (`www/packages/canvas/src/browsing/useBrowserPaneStream.ts:44-65`). | This publishes a capability endpoint to the app renderer, so it is a trust boundary. The endpoint still requires a control-plane capability at WebSocket open and on every command (`desktop/src/browserPaneDevtoolsFront.ts:242-288`). |
| Main to app renderer | `{kind:"observation", browserPaneId, observation}`, `{kind:"open-request",url}`, or `{kind:"gone",browserPaneId,reason:"crashed"|"destroyed"}`. The observation carries `navigation_seq`, `observed_url`, title, target id, load status, failure, history booleans, and timestamp (`packages/contract/src/desktop/index.ts:80-96`, with fields inherited from `packages/contract/src/browsing/index.ts:159-175`). | `BrowserPaneHost` emits observations/gone and view policy emits open requests (`desktop/src/app/browserPanes/BrowserPaneHost.ts:180-204`, `desktop/src/app/browserPanes/BrowserPaneHost.ts:248-257`; `desktop/src/app/browserPanes/viewPolicy.ts:44-55`). The register function sends them to the owning app renderer (`desktop/src/app/browserPanes/registerBrowserPaneHost.ts:40-42`). | Preload receives and fans out host messages to subscribers (`desktop/src/preload.cts:31-37`, `desktop/src/preload.cts:54-58`); canvas handles observations, open requests, and crash reports (`www/packages/canvas/src/browsing/useBrowserPaneHostMessages.ts:18-64`). | The pane page is the origin of `window.open` and navigation events, but it has no preload. Main converts that untrusted event into an app-renderer message. The renderer then calls backend APIs, for example `openBrowserPane` for `open-request` (`www/packages/canvas/src/browsing/useBrowserPaneHostMessages.ts:43-45`). |

`contextBridge.exposeInMainWorld` publishes the frozen object under `transportMattersDesktop` (`desktop/src/preload.cts:43-64`). The bridge contains `appName`, `platform`, `getPathForFile`, and `browserPanes`; there is no generic eval, filesystem, child-process, or arbitrary IPC method.

### Non-Electron IPC surfaces that are easy to confuse with the channel

- The browser pane CDP front is a loopback HTTP upgrade plus WebSocket JSON protocol, not Electron IPC. It listens on an ephemeral `127.0.0.1` port (`desktop/src/browserPaneDevtoolsFront.ts:136-137`, `desktop/src/browserPaneDevtoolsFront.ts:488-495`), accepts only `/devtools/browser/tm?tm_attach=<capability>` (`desktop/src/browserPaneDevtoolsFront.ts:242-250`), and returns 401 for other paths or invalid grants (`desktop/src/browserPaneDevtoolsFront.ts:250-253`).
- Main calls the control plane authorizer at `/v1/controlplane/devtools-authorize` only for a loopback hosted route and with a two second timeout (`desktop/src/main.ts:97-121`). It rejects non-HTTP or non-loopback routes before any request (`desktop/src/main.ts:125-134`).
- The desktop's smoke MCP client is ordinary loopback HTTP POST to `/mcp` with a run bearer and JSON-RPC `tools/call` (`desktop/src/mcpClient.ts:1-59`); it is test tooling, not a renderer bridge.

## Window and browser-pane management

### Main app window

`createHostedWindow` validates that the renderer URL is HTTP, host `127.0.0.1`, and path `/` or `/canvas` (`desktop/src/window.ts:62-79`, `desktop/src/window.ts:131-146`). It creates a hidden 1280 by 900 window with minimum 900 by 600, hidden title bar, macOS traffic-light position, context isolation, no Node integration, sandbox, and the resolved `preload.cjs` (`desktop/src/window.ts:32-59`). It binds:

- Same-origin top-level navigation only (`desktop/src/window.ts:104-112`).
- All `window.open` calls denied; only HTTPS URLs are passed to `shell.openExternal` (`desktop/src/window.ts:114-119`).
- Main-frame load failure to `dialog.showErrorBox` (`desktop/src/window.ts:121-129`).
- `ready-to-show` to `show`, followed by `loadURL` (`desktop/src/window.ts:73-77`).

Window lifecycle is centralized. Activation creates a replacement only when `BrowserWindow.getAllWindows()` is empty (`desktop/src/app/DesktopLifecycle.ts:83-93`); closing all windows requests quit on non-macOS and keeps the default foreground-app behavior on macOS unless explicitly overridden (`desktop/src/app/DesktopLifecycle.ts:95-113`). Managed startup registers this lifecycle even while readiness is pending so a user can activate again after the first window closes (`desktop/src/app/backendStartup.ts:387-409`).

### Pane frame ownership

The canvas renderer owns desired pane layout. It measures the workbench and overlays every animation frame while layout is unsettled, sends only changed complete frames, and sends an empty frame on unmount (`www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:33-41`, `www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:74-133`). The shared contract rounds CSS rectangles before sending them, while the desktop boundary independently requires safe integers because `setBounds` consumes integer coordinates (`packages/contract/src/desktop/index.ts:26-49`; `desktop/src/app/browserPanes/registerBrowserPaneHost.ts:115-124`).

`BrowserPaneHost.present` is a whole-state reconcile, not an event queue (`desktop/src/app/browserPanes/BrowserPaneHost.ts:57-65`, `desktop/src/app/browserPanes/BrowserPaneHost.ts:84-101`):

1. Every placement is added to the desired id set.
2. A new id creates a `WebContentsView`, applies session and view policy, registers its debugger target, observes contents events, and adds it to `window.contentView` (`desktop/src/app/browserPanes/BrowserPaneHost.ts:112-138`).
3. Existing views receive `setBounds` and `setVisible` every frame (`desktop/src/app/browserPanes/BrowserPaneHost.ts:84-92`). A docked but invisible pane remains mounted, so hiding it does not reload it (`desktop/src/app/browserPanes/BrowserPaneHost.ts:57-64`).
4. A placement's navigation is applied only if `seq > appliedSeq`; a URL always loads, and a history intent takes at most one guarded step on an already loaded view (`desktop/src/app/browserPanes/BrowserPaneHost.ts:141-162`, `desktop/src/app/browserPanes/BrowserPaneHost.ts:263-271`). A fresh view created under a history intent loads the supplied URL because it has no history (`desktop/src/app/browserPanes/BrowserPaneHost.ts:141-158`).
5. An id absent from the new frame is removed from `contentView`, unregistered from CDP, and closed unless already destroyed (`desktop/src/app/browserPanes/BrowserPaneHost.ts:94-100`, `desktop/src/app/browserPanes/BrowserPaneHost.ts:206-212`).

The native view is restricted twice. `will-navigate` blocks non-presentable URLs and `setWindowOpenHandler` denies new windows while relaying safe opens (`desktop/src/app/browserPanes/viewPolicy.ts:26-56`). The shared persistent session installs one permission denial and one download denial through a `WeakSet`, so each session receives the policy once (`desktop/src/app/browserPanes/viewPolicy.ts:58-73`).

### Pane observations, crashes, and target lifecycle

The host waits for the CDP target registration promise before its first `loadURL`, which lets the first observation include a target id (`desktop/src/app/browserPanes/BrowserPaneHost.ts:117-135`, `desktop/src/app/browserPanes/BrowserPaneHost.ts:164-176`). It emits:

- `loading` on main-frame start, `loaded` on finish, in-page navigation, and title update (`desktop/src/app/browserPanes/BrowserPaneHost.ts:219-240`).
- A non-`ERR_ABORTED` main-frame failure against the in-flight seq, with the error code and description (`desktop/src/app/browserPanes/BrowserPaneHost.ts:241-247`).
- `gone` after a render-process crash or destruction; the crash path removes the view from the map so the next frame recreates it (`desktop/src/app/browserPanes/BrowserPaneHost.ts:248-259`).

Reports use the committed document seq rather than blindly using the newest requested seq. Before first commit they use the desired URL as the observed URL because Electron can return an empty `getURL()` (`desktop/src/app/browserPanes/BrowserPaneHost.ts:179-203`). This is important when a newer navigation arrives while late events from the previous document are still firing.

`BrowserPaneHostRegistry` tracks hosts per window and its finalizer disposes all remaining views (`desktop/src/app/browserPanes/BrowserPaneHostRegistry.ts:7-25`). `registerBrowserPaneHost` also removes the IPC listener and disposes its host when the window closes (`desktop/src/app/browserPanes/registerBrowserPaneHost.ts:77-81`).

### CDP front and attachment

`main.ts` starts one `BrowserPaneDevtoolsFront` after Electron readiness and gives its promise to every host (`desktop/src/main.ts:47-56`, `:78-89`). Registration attaches Electron's debugger at protocol 1.3 when needed, calls `Target.getTargetInfo`, stores the target by `WebContents`, and relays target-created events only to clients for the same canvas (`desktop/src/browserPaneDevtoolsFront.ts:163-212`).

The front never serves plain HTTP and holds no capability of its own (`desktop/src/browserPaneDevtoolsFront.ts:113-137`). The control plane names the canvas during capability redemption; the caller cannot select a different canvas (`:237-250`). A client command is serialized behind a per-client promise and authorization is repeated before command parsing/execution (`:255-307`). Target attachment rejects a target belonging to another canvas (`:345-357`), and `dispose` terminates clients, unregisters targets, closes WebSockets, closes connections, and closes the server (`:214-222`).

## Backend and gateway integration

### Channel and port resolution

`ENV` centralizes all `TRANSPORT_MATTERS_*` names, including channel, web/proxy/gateway ports, gateway entry, capture RPC URL, channel home, database URL, package smoke, bundled backend binary, and standalone smoke (`desktop/src/env.ts:19-63`). The channel spec has `id`, home, database name, three ports, Electron identity, and optional badge (`:65-86`). The reader defaults to `stable`, validates the JSON schema and every port, and reads `dist/channel-specs.json` when it exists, falling back to the API source JSON in an unbuilt checkout (`:88-129`, `:131-166`). The current channel values live in `api/src/transport_matters/channel-specs.json:1-55`: stable uses 8787/8788/8789, preview 8797/8798/8799, and dev 8807/8808/8809.

`resolveBackendStartupOptions` resolves the requested channel, asks `transport-matters channel status <channel> --json` unless status is injected, uses live runtime ports only when the status is `live` and serves the same canonical workspace, then applies explicit env port overrides over those defaults (`desktop/src/app/backendStartup.ts:108-130`, `desktop/src/app/backendStartup.ts:434-451`). Port strings must be canonical decimal integers in 1 through 65535 (`desktop/src/jsonReaders.ts:38-54`).

### Development and ambient runtime path

When no bundled resources are present, `startAmbientOrManagedBackend` uses `process.cwd()` as the workspace (`desktop/src/app/backendStartup.ts:331-342`). A live runtime serving that exact canonical directory becomes a hosted viewer without spawning children (`:342-351`). For absent, stale, unhealthy, wedged, wrong-workspace, or otherwise unusable status, it invokes `_desktop-reclaim --work-dir <cwd> --channel <id>` via the CLI (`desktop/src/desktopRuntime.ts:102-109`, `:161-175`), reads status again, and hosts the refreshed live runtime if one appeared (`desktop/src/app/backendStartup.ts:354-373`). If reclaim fails, the app shows/logs the startup error and quits (`:354-359`).

Otherwise it launches the managed Python backend and gateway. The backend command is `transport-matters _desktop-backend --work-dir <cwd> --web-port <web> --proxy-port <proxy> --channel <channel>` (`desktop/src/backendProcess.ts:66-99`). Its child environment preserves inherited values, sets channel/cwd, sets `TRANSPORT_MATTERS_GATEWAY_URL=http://127.0.0.1:<gatewayPort>`, and pins proxy/web ports (`:84-99`). The Python app uses that gateway URL to mount the run proxy, as the backend launch comment records (`:93-95`); the API server's gateway mount decision is at `api/src/transport_matters/main.py:556-584`.

The gateway entry resolver first honors `TRANSPORT_MATTERS_GATEWAY_ENTRY` after stat-checking it. Without an override it walks upward from the compiled module directory for `pnpm-workspace.yaml`, then requires `packages/gateway/src/main.ts` (`desktop/src/gateway/gatewayProcess.ts:108-134`). A TypeScript entry is run with `node --import tsx <entry>`; a JavaScript entry is run directly. Dev uses `node`, while managed production composition passes `process.execPath` and `ELECTRON_RUN_AS_NODE=1` (`:137-173`; `desktop/src/app/backendStartup.ts:259-266`).

The gateway child receives its listen port, Python capture RPC URL, and parent-death watch (`desktop/src/gateway/gatewayProcess.ts:145-153`). It also receives the resolved channel home for browser history and a database URL, preferring an explicit env value, otherwise reading `[database].url` from `<channel home>/settings.toml` and replacing only the URL database path with the channel database name (`:154-199`, `:211-250`). The gateway binds loopback and reads these names in `packages/gateway/src/main.ts:44-49`, `:180-184`, `:237-262`, and `:284-307`.

Both children must answer health checks before the first window is created. `startBackendAndCreateWindow` launches Python, launches the gateway, waits for both `/health` endpoints with `Promise.allSettled`, stops gateway then Python on any rejection, reports the backend failure preferentially, and wraps gateway failures with recent gateway output (`desktop/src/app/backendStartup.ts:148-220`). The health loop polls every 250 ms, aborts each fetch at 750 ms, and gives up after 15 seconds (`desktop/src/backendHealth.ts:23-64`). A child that exits before readiness rejects immediately through `watchBackendExitBeforeReady` (`desktop/src/backendProcess.ts:185-207`). There is no process restart loop; the only retry is health polling and the single reclaim/recheck pass.

Child stdio is always drained so a full pipe cannot block startup or runtime; managed launches intentionally do not tee logs to a file. Standalone smoke mode forwards output best-effort to stderr (`desktop/src/backendProcess.ts:138-183`).

### Packaged standalone path

`resolveBundledResources` returns null in dev and, when `app.isPackaged`, resolves `process.resourcesPath/python/bin/python3`, `process.resourcesPath/gateway/main.js`, and `process.resourcesPath/python/certifi-ca-bundle.pem` (`desktop/src/app/bundledResources.ts:27-50`). `packagedBackendEnv` injects the bundled gateway entry, bundled interpreter, and default CA bundle while preserving an explicit `SSL_CERT_FILE` (`:53-70`).

When bundled resources exist, `registerAppLifecycle` bypasses runtime discovery and reclaim (`desktop/src/app/backendStartup.ts:252-295`, `:298-324`). The workspace directory is `options.homeDir` or `app.getPath("home")`, because Finder launches can have cwd `/` (`:306-323`). The backend launcher detects `TRANSPORT_MATTERS_DESKTOP_BACKEND_BIN`, invokes that interpreter directly on the adjacent `transport-matters` console script, and thereby ignores a stale absolute shebang after app relocation (`desktop/src/backendProcess.ts:102-119`). The gateway uses the bundled JS entry override, so it never needs a workspace marker (`desktop/src/gateway/gatewayProcess.ts:114-134`).

The standalone acceptance smoke deliberately launches from cwd `/` with PATH containing only a fake harness and system directories, then requires health and a run reaching `EXITED` (`desktop/src/standaloneSmoke.ts:75-110`, `:131-190`). Its negative assumptions protect against accidentally taking package-smoke or hosted-viewer branches (`:9-13`, `:75-81`).

## Build, packaging, signing, and dev versus packaged differences

### Maintainer build and smoke package

`pnpm --dir desktop build` runs `tsc`, copies channel specs, checks the CommonJS preload, and scans emitted imports (`desktop/package.json:7-18`). `pnpm --dir desktop dev` builds, installs Electron, and runs `electron .`; Electron resolves the package `main` as `dist/main.js` (`desktop/package.json:5-17`).

`pnpm package:smoke` builds, installs Electron, creates a portable Electron package under `dist/package-smoke`, and runs `dist/packageSmoke.js`. On macOS the script copies `Electron.app`, removes the default app archive, and writes app sources under `Contents/Resources/app`; elsewhere it copies the Electron distribution and renames the top-level executable (`desktop/scripts/package-smoke-build.mjs:17-67`). The package smoke sets `DESKTOP_PACKAGE_SMOKE=1` and a marker file, then `packageSmokeLifecycle` proves the real sandboxed preload exposed the bridge in a renderer before quitting (`desktop/src/packageSmoke.ts:44-64`, `:114-123`; `desktop/src/app/packageSmokeLifecycle.ts:34-84`, `:96-127`).

### Standalone distributable

The intended standalone pipeline is:

1. `standalone:bundle-python` runs `scripts/bundle-python.mjs` against the exact wheel. It installs relocatable CPython, dereferences interpreter symlinks, rejects pre-release Python, prunes dangling symlinks, installs the wheel, copies certifi's CA, stages `gateway/main.js`, and verifies the Python console script plus `www`, `canvas`, and `gateway` bundles (`desktop/scripts/bundle-python.mjs:49-146`).
2. `standalone:build` runs the desktop build then `electron-builder --config electron-builder.yml` (`desktop/package.json:15-18`). Electron-builder copies `dist/standalone/python` and `dist/standalone/gateway` as unpacked `extraResources`, excludes standalone and package-smoke output from the app graph, and enables ASAR for the rest (`desktop/electron-builder.yml:1-31`).
3. On macOS it produces a directory app and DMG; on Linux it produces a directory target (`desktop/electron-builder.yml:24-35`). The executable name is pinned to `transport-matters` for non-macOS smoke discovery (`:11-17`).
4. `standalone:smoke` launches the packaged executable as a black box and proves its own bundled backend/gateway path via health and a completed run (`desktop/src/standaloneSmoke.ts:131-190`, `:210-231`).

Signing and notarization are intentionally absent. The builder sets `mac.identity: null` and comments that DMG-1 is unsigned; signing, notarization, Gatekeeper prompt removal, and silent auto-update are a later slice (`desktop/electron-builder.yml:1-8`, `:24-30`). A packaged build therefore must not be treated as signed or notarized.

The packaged import guard is material because `@tm/contract` is a workspace dev dependency with TypeScript exports. It accepts only relative imports, builtins, Electron, or production dependencies from `desktop/package.json` (`desktop/scripts/assert-packaged-imports.ts:1-11`, `:22-59`). The pane host, bridge keys, and preload deliberately avoid runtime contract imports for this reason (`desktop/src/preload.cts:15-19`; `desktop/src/app/browserPanes/viewPolicy.ts:20-24`).

## Data-flow traces

### A. Cold start to the first painted window

The normal managed path is:

1. Electron evaluates `dist/main.js`, which calls `registerDesktopLifecycleFromEnv()` (`desktop/src/main.ts:137`). Registration resolves the channel, applies app name/id/user-data path/icon, and chooses package smoke, hosted route, or managed lifecycle (`desktop/src/main.ts:33-75`).
2. Managed registration creates backend and gateway supervisors, installs shutdown hooks, and waits for `app.whenReady()` (`desktop/src/app/backendStartup.ts:252-295`).
3. Development startup reads runtime status. A same-workspace live runtime takes the hosted branch; otherwise reclaim runs once and then the managed branch is selected (`desktop/src/app/backendStartup.ts:331-384`). Packaged startup skips this discovery and uses the buyer home (`:298-324`).
4. Managed startup calls `startBackendAndCreateWindow` and registers activation/window-close behavior (`desktop/src/app/backendStartup.ts:387-409`). It launches Python and gateway, then waits for both health checks before creating a window (`desktop/src/app/backendStartup.ts:148-203`).
5. `createMainWindow` fills the preload path and delegates to `createHostedWindow` (`desktop/src/app/hostedLifecycle.ts:48-57`). `createHostedWindow` creates a hidden secure `BrowserWindow`, installs navigation policy, requests `http://127.0.0.1:<webPort>/canvas`, and only calls `show()` on `ready-to-show` (`desktop/src/window.ts:62-79`).
6. The backend serves the canvas bundle at `/canvas`; its explicit bare route exists because the shell loads exactly `/canvas` (`api/src/transport_matters/main.py:166-190`). The first visible shell paint is therefore gated by backend and gateway readiness, then Electron's `ready-to-show`, with the renderer's actual UI paint supplied by the backend-served SPA.
7. The sandboxed preload runs as `dist/preload.cjs`, sends the devtools query, installs the host-message listener, and exposes the frozen bridge (`desktop/src/preload.cts:1-6`, `:31-64`). The canvas waits for the devtools promise before declaring a composited presenter (`www/packages/canvas/src/browsing/useBrowserPaneStream.ts:44-65`).

The existing-runtime hosted path skips child launch but still creates the window at `app.whenReady`, derives a health URL from the route, and starts liveness polling after the first successful load (`desktop/src/app/hostedLifecycle.ts:100-150`; `desktop/src/hostedLiveness.ts:61-73`).

### B. Opening a browser pane and navigating it

The desktop applies state; the gateway and renderer own pane intent and persistence. A complete UI path is:

1. Canvas connects to the browsing SSE and receives a snapshot. It applies the snapshot and calls `bridge.announce()` so main can re-observe native targets under the new presenter id (`www/packages/canvas/src/browsing/useBrowserPaneStream.ts:68-78`).
2. Canvas's layout hook measures pane rectangles, builds a complete placement frame, and calls `bridge.present(frame)` only when the frame changes (`www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:74-133`). Preload sends that frame on `tm:browser-panes` (`desktop/src/preload.cts:47-53`).
3. Main's window-scoped listener verifies the sender and parses the frame. `BrowserPaneHost.present` creates a `WebContentsView` if necessary, applies pane security policy, registers its CDP target for the frame's canvas, adds it to `contentView`, sets bounds/visibility, and applies the seq-gated navigation (`desktop/src/app/browserPanes/registerBrowserPaneHost.ts:58-81`; `desktop/src/app/browserPanes/BrowserPaneHost.ts:84-138`).
4. If a page calls `window.open`, the pane policy denies the new window and emits `{kind:"open-request",url}` to the app renderer (`desktop/src/app/browserPanes/viewPolicy.ts:40-55`). Preload delivers it to subscribers; the canvas calls the backend `openBrowserPane` operation with origin `open-request` (`desktop/src/preload.cts:31-37`; `www/packages/canvas/src/browsing/useBrowserPaneHostMessages.ts:30-45`).
5. A user or director opening through the backend causes a browsing snapshot/delta to include the pane. The canvas presents it, and main loads the requested HTTP(S) URL only after target registration (`desktop/src/app/browserPanes/BrowserPaneHost.ts:128-176`).
6. Main observes `did-start-navigation`, `did-finish-load`, title, in-page navigation, and failures, and sends observation messages through preload. The canvas pairs the observation with its current presenter id and reports it back to the backend (`desktop/src/app/browserPanes/BrowserPaneHost.ts:219-247`; `www/packages/canvas/src/browsing/useBrowserPaneHostMessages.ts:30-61`).
7. A later backend navigation increments `seq`; main ignores equal or lower seqs, loads a URL intent, or performs one history step only on an already loaded native history (`desktop/src/app/browserPanes/BrowserPaneHost.ts:152-162`, `:263-271`). A load failure becomes a `failed` observation; a crash emits `gone` and removes the dead view for next-frame recreation (`:241-259`).
8. A composited presenter gets the main-owned endpoint only after main's CDP front has registered the view. The control plane's capability authorizes the pane-only WebSocket, and the front exposes only targets for the authorized canvas (`desktop/src/browserPaneDevtoolsFront.ts:163-212`, `:242-275`, `:322-445`).

The black-box proof exercises this entire chain: it opens a pane through MCP, waits for `presentation.attach`, connects agent-browser to the pane-only front, navigates from page one to page two, steps back, reloads, verifies history, and closes the pane (`desktop/src/browserPaneProof.ts:205-331`).

### C. App quit and child teardown

1. Electron `before-quit` and POSIX `SIGINT`/`SIGTERM` route into `DesktopShutdown`; Windows intentionally does not register signal handlers (`desktop/src/app/DesktopLifecycle.ts:41-67`). Window-all-closed also requests quit on non-macOS (`:83-113`).
2. The first quit event is prevented and `requestQuit()` is memoized, so repeated events share one shutdown promise (`desktop/src/app/DesktopShutdown.ts:27-55`).
3. In the managed composition, finalizers are ordered as per-window finalizers first, then gateway stop, then Python backend stop (`desktop/src/app/backendStartup.ts:267-279`, `:222-234`). The pane registry removes child views and the devtools front closes clients, debugger targets, WebSockets, and its server before children are signalled (`desktop/src/app/browserPanes/BrowserPaneHostRegistry.ts:22-25`; `desktop/src/browserPaneDevtoolsFront.ts:214-222`).
4. Gateway stop uses an 8 second grace budget, sends SIGTERM first, and can force SIGKILL. The direct Node launch matters because a pnpm/tsx wrapper could swallow SIGTERM and prevent gateway-owned run/capture release (`desktop/src/gateway/gatewayProcess.ts:1-34`, `:255-268`; `desktop/src/lifecycle/graceThenForce.ts:5-53`).
5. The gateway handles SIGTERM or parent stdin EOF, stops accepting traffic, closes browsing streams, closes the Fastify app, closes `RunManager` and terminals, releases runtime lease and pools, then exits (`packages/gateway/src/main.ts:349-375`, `:398-425`). The desktop's gateway parent-watch env is what arms stdin EOF handling (`desktop/src/gateway/gatewayProcess.ts:145-153`).
6. Once gateway stop resolves, Python receives the same grace-then-force sequence with the 2 second desktop backend budget (`desktop/src/lifecycle/graceThenForce.ts:1-53`; `desktop/src/backend/DesktopBackendManager.ts:70-90`).
7. Even if a finalizer rejects, `DesktopShutdown` logs it, continues all remaining finalizers, sets the allow-quit flag, and calls `app.quit()` (`desktop/src/app/DesktopShutdown.ts:57-81`). The reentrant `before-quit` event returns immediately because the allow flag is set (`:40-46`).

## Native and OS-specific behavior

- macOS retains traffic lights while hiding the native title bar; non-macOS requests `titleBarOverlay` (`desktop/src/window.ts:44-51`). Preview/dev channel identity may set the macOS dock icon through `app.dock.setIcon` (`desktop/src/app/channelIdentity.ts:26-45`).
- macOS does not quit on `window-all-closed` by default in the shared lifecycle; Linux and Windows do (`desktop/src/app/DesktopLifecycle.ts:95-113`). Hosted lifecycle explicitly opts into quitting when all hosted windows close (`desktop/src/app/hostedLifecycle.ts:141-150`).
- Windows skips POSIX signal listener registration (`desktop/src/app/DesktopLifecycle.ts:57-67`). Child termination code still uses Node signals for managed child processes.
- Package smoke copies `Electron.app` using `/bin/cp -R` on macOS and identifies the executable under `.app/Contents/MacOS`; portable platforms copy Electron's distribution and rename `electron` or `electron.exe` (`desktop/scripts/package-smoke-build.mjs:26-58`; `desktop/src/packageSmoke.ts:67-112`, `:133-165`).
- Channel homes default under the OS home directory, with an optional `TRANSPORT_MATTERS_HOME` base override preserving the channel dot-directory (`desktop/src/env.ts:99-114`). Channel-specific Electron user data is placed under `<channel home>/<userDataDir>` (`desktop/src/app/channelIdentity.ts:26-34`).
- Packaged Finder launches use `app.getPath("home")` for backend workspace selection instead of cwd (`/`), while dev uses `process.cwd()` (`desktop/src/app/backendStartup.ts:306-317`, `:331-338`).
- Standalone and proof tests use OS temporary directories for fake homes, storage, proof pages, package markers, and pane-proof residue; the residue filename is `${tmpdir()}/tm-browser-pane-proof.json` (`desktop/src/browserPaneProofLifecycle.ts:15-18`).
- Browser-pane permissions are intentionally denied at the shared session level, and downloads are prevented (`desktop/src/app/browserPanes/viewPolicy.ts:58-73`). There is no macOS permission prompt handling in desktop code; the pane policy rejects the Electron permission request before an OS prompt can be useful.

## Conventions a newcomer will violate

- Keep the preload CommonJS. Source it as `.cts`, use `import = require` for runtime Electron, keep sibling imports out, and update the preload/package guards if the boundary changes (`desktop/src/preload.cts:1-19`; `desktop/scripts/assert-preload-cjs.mjs:1-48`).
- Keep `@tm/contract` imports type-only in packaged desktop modules. The package ships the emitted desktop graph without workspace dev dependencies, and the import guard checks exactly that graph (`desktop/scripts/assert-packaged-imports.ts:1-11`, `:45-71`).
- Parse external values at boundaries. IPC frames are dropped on malformed shape, runtime JSON is rejected on invalid state/ports, and channel specs are validated before use (`desktop/src/app/browserPanes/registerBrowserPaneHost.ts:89-155`; `desktop/src/desktopRuntime.ts:111-143`; `desktop/src/env.ts:131-166`).
- Prefer whole-state reconciliation for panes. Do not add a second incremental pane command path: the renderer sends all desired placements and main destroys absent ids (`desktop/src/app/browserPanes/BrowserPaneHost.ts:57-65`, `:84-101`).
- Preserve navigation seq semantics. Equal/lower seqs must not rewind a pane; a history intent is one step, never a queue (`desktop/src/app/browserPanes/BrowserPaneHost.ts:141-162`).
- Preserve the gateway-first shutdown order. Python is the capture RPC host; stopping it before gateway release turns orderly run teardown into dead-socket or generic shutdown outcomes (`desktop/src/app/backendStartup.ts:222-234`).
- Always drain child stdout and stderr. Adding a blocking file tee or waiting on a terminal can deadlock a managed child (`desktop/src/backendProcess.ts:138-183`).
- Use the existing `DesktopBackendManager` and `graceThenForce` path for managed children. The manager prevents duplicate starts and memoizes concurrent stops (`desktop/src/backend/DesktopBackendManager.ts:21-90`).
- Hosted routes must stay loopback HTTP and `/` or `/canvas`; external HTTPS navigation belongs to `shell.openExternal` and new windows are denied (`desktop/src/window.ts:82-119`, `:131-146`).
- Window creation must pass through the decorator in `main.ts`, so every window receives a pane host and the devtools front (`desktop/src/main.ts:78-89`). A direct call to `createMainWindow` in a new lifecycle path will silently lose pane support; `desktop/src/main.devtools.test.ts:32-60` guards this.
- Use `app.whenReady()` for window and devtools-front creation, and keep channel identity before readiness so app id, user data, and dock icon are correct from boot (`desktop/src/main.ts:37-50`; `desktop/src/app/channelIdentity.ts:26-39`).
- The renderer's `getPathForFile` is deliberately the only file path bridge. Do not expose general filesystem access (`desktop/src/preload.cts:40-46`).
- Tests load `.cts` with the CommonJS VM helper or Vitest transform. Importing the preload as ordinary ESM gives a false test shape (`desktop/src/testing/loadCommonJsSource.ts:11-45`; `desktop/vitest.config.ts:1-25`).
- Use the desktop package scripts for typecheck. They run production, test, and script projects together (`desktop/package.json:18-18`; `desktop/tsconfig.test.json:1-9`; `desktop/tsconfig.scripts.json:1-9`).

## Landmines and fragile contracts

1. **Packaged preload failure is silent at the window level.** Electron can still create a window after a preload failure, so a smoke that checks only window creation is insufficient. The package smoke executes JavaScript to prove the bridge exists, and the CommonJS guard protects the emitted file (`desktop/src/app/packageSmokeLifecycle.ts:34-84`; `desktop/scripts/assert-preload-cjs.mjs:16-38`).
2. **Stale dist output can hide a source rename.** `tsc` does not delete orphaned files; the preload guard removes old `preload.js` artifacts, but other stale dist files can still confuse manual inspection (`desktop/scripts/assert-preload-cjs.mjs:16-28`). Clean before diagnosing packaging-only behavior.
3. **A workspace dev dependency can pass locally and fail only after packaging.** `@tm/contract` exports TypeScript sources and is not a desktop production dependency. Any value import in emitted desktop code fails on a buyer's machine; run the packaged import guard (`desktop/scripts/assert-packaged-imports.ts:1-11`, `:22-71`).
4. **The gateway wrapper must not be introduced casually.** The direct Node child is required for SIGTERM to reach gateway shutdown and for capture release to complete before the eight second grace budget expires (`desktop/src/gateway/gatewayProcess.ts:1-34`).
5. **Changing runtime budgets requires two sides to move.** The gateway's runtime release/termination budgets are documented beside `DESKTOP_GATEWAY_STOP_GRACE_MS`; the desktop's eight seconds includes the gateway's one second terminate budget, five second release budget, and margin (`desktop/src/gateway/gatewayProcess.ts:26-34`).
6. **The gateway parent stdin pipe is a leak-prevention invariant.** `stdio:"pipe"` plus `GATEWAY_PARENT_WATCH=1` lets gateway stdin EOF self-shutdown even after a hard desktop kill (`desktop/src/gateway/gatewayProcess.ts:145-153`; `packages/gateway/src/main.ts:56-63`, `:106-121`, `:369-375`). Changing stdio to inherited or ignoring the env can leak a gateway.
7. **Managed desktop launches intentionally have no persistent desktop log.** The child pipes are drained and discarded outside standalone smoke; the API's detached CLI owns `desktop.log` instead (`desktop/src/backendProcess.ts:138-147`). A newcomer looking for a managed desktop log will find none.
8. **Runtime reuse is workspace-sensitive.** A live status for another cwd is reclaimed rather than hosted, after canonicalizing real paths and falling back to `resolve` if `realpathSync` fails (`desktop/src/app/backendStartup.ts:412-451`). Do not compare raw path strings.
9. **Packaged and dev startup have different authority.** Packaged startup must not attach to a stray ambient runtime and therefore passes `{runtimeStatus:null}`; dev intentionally discovers and may host or reclaim one (`desktop/src/app/backendStartup.ts:298-351`). Testing packaged behavior with the dev branch produces a false green.
10. **A browser pane's URL policy is duplicated intentionally.** Gateway policy, main's `will-navigate`, and `BrowserPaneHost.#load` all protect the HTTP(S)/blank invariant (`desktop/src/app/browserPanes/viewPolicy.ts:20-55`; `desktop/src/app/browserPanes/BrowserPaneHost.ts:164-169`). `loadURL` does not emit `will-navigate`, so the host must retain its own check (`desktop/src/app/browserPanes/BrowserPaneHost.ts:141-150`).
11. **A renderer crash must remove the map entry immediately.** Keeping a dead view at its old seq prevents the next complete frame from recreating it (`desktop/src/app/browserPanes/BrowserPaneHost.ts:214-259`).
12. **Target ids and presenter ids are different lifetimes.** A new SSE connection mints a presenter id, so the canvas must announce all native observations again; otherwise the gateway cannot pair target ids with the current presenter (`www/packages/canvas/src/browsing/useBrowserPaneStream.ts:72-78`; `desktop/src/app/browserPanes/BrowserPaneHost.ts:103-110`).
13. **CDP commands are authorized twice in time.** Authorization at WebSocket upgrade is insufficient because a director grant can be revoked after connection. `handleCdpMessage` rechecks before every command and closes on failure (`desktop/src/browserPaneDevtoolsFront.ts:277-307`).
14. **CDP canvas scope comes from the control plane, not the URL caller.** The front does not trust a caller-supplied canvas id; it stores the authorizer's returned canvas and checks every target against it (`desktop/src/browserPaneDevtoolsFront.ts:237-250`, `:345-357`).
15. **Unsigned DMGs are expected in this slice.** `identity: null` means a Gatekeeper prompt and lack of notarization are packaging behavior, not necessarily a runtime failure (`desktop/electron-builder.yml:24-30`).
16. **The standalone resource paths must remain outside ASAR.** Python and node-pty native modules cannot load from inside `app.asar`; electron-builder's `extraResources` and `resolveBundledResources` must remain aligned (`desktop/electron-builder.yml:1-8`, `:27-31`; `desktop/src/app/bundledResources.ts:27-50`).
17. **The Python console script's shebang is relocation-sensitive.** Packaged launch invokes the bundled interpreter on that script instead of executing the script itself (`desktop/src/backendProcess.ts:102-119`). A direct console-script spawn will break after moving the app.
18. **Smoke executable discovery must avoid the nested Python console script.** Non-macOS standalone discovery uses the pinned root executable name; recursive discovery can select `resources/python/bin/transport-matters` instead (`desktop/src/packageSmoke.ts:67-99`).
19. **The browser pane proof's residue file is safety-critical.** PID reuse is guarded by exact executable and token matching before signals are sent, and the workdir is reclaimed independently (`desktop/src/browserPaneProofLifecycle.ts:77-120`). Do not simplify it to `process.kill(recordedPid)`.
20. **The first renderer paint is not a local HTML asset.** The shell can be opened only after loopback backend health, and `/canvas` is served by the API package (`desktop/src/app/backendStartup.ts:178-203`; `api/src/transport_matters/main.py:166-190`). A packaged app with missing embedded `canvas` files can pass TypeScript and fail at runtime.

## Verification snapshot

Read-only structural validation passed with `fmm validate` before this map was written. Desktop typecheck passed with `pnpm --dir desktop typecheck`, and the desktop test command passed with 29 test files and 204 tests. No repository files were changed; `git status --short -- desktop` was empty after verification.
