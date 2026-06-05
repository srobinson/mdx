---
title: 'Scout: browser pane (WebContentsView) in the canvas'
type: projects
tags: [transport-matters, scout, canvas, desktop, electron, control-plane, browser-pane]
summary: Reuse map, quality map, and plan for a per-pane Electron WebContentsView driven by the canvas and the director, CDP-attachable by agent-browser
status: active
created: 2026-08-27
updated: 2026-08-27
project: transport-matters
related: [transport-matters-scout-s4-login-detection, tm-controlplane-scout-observe]
confidence: high
---

# Scout: browser pane in the Transport Matters canvas

Read-only scout of `main` at `dd3aa5f0` (every path below was read with `git show dd3aa5f0:<path>`; the
working tree was not consulted). Task statement: `~/.mdx/TMP/pstack/c4dd242f/arena-task.md`. Citations are
path plus symbol. Path shorthands: `desktop/` is `desktop/src/`, `canvas/` is `www/packages/canvas/src/`,
`core/` is `www/packages/core/src/`, `tm/` is `api/src/transport_matters/`.

## Headline

Every renderer-side capability the feature needs has an owner today: pane kinds, palette commands, pane
geometry, drag occlusion, desktop detection, persistence, and the test seams. Three capabilities have no
owner and are net new: a renderer to main channel (the preload exposes three read-only values and no
`ipcRenderer`), a control-plane verb that opens or closes a non-run pane (panes are client-local Zustand
state; the director reaches the canvas only through the run activity stream), and any CDP or remote
debugging flag (none in the desktop). The plan's load-bearing decision is where pane state lives so the
director and the palette stay twin clients without a second copy of it in the Electron main process.

## Reuse Map

### Pane kind registration

- Reuse: `canvas/model/paneRecords.ts` `PaneContentRef`, `CanvasPaneRef`, `ViewerId`, `isPaneContentRef`.
  The discriminated union plus the structural reader guard that persisted refs must pass.
- Reuse: `canvas/model/paneIdentity.ts` `paneIdForRef`, `titleForRef`, `viewerIdForRef`. Three exhaustive
  switches over `ref.kind`; the pane id is also the dedupe key (`terminal` is a singleton id, captured runs
  key on `runKey`). A browser pane needs a per-instance key: precedent is `canvas/model/spawn.ts`
  `labelFor` (monotonic counters persisted on `paneCounters`) and `canvas/model/capturedRunStore.ts`
  `createCapturedRunKey`.
- Reuse: `canvas/viewers/registry.tsx` `defineViewer`, `resolveViewer`, `renderPaneContent`, `PaneShell`,
  `bodyDragForRef`. Lazy chunk precedent: the `TerminalPane` `lazy(() => import(...))` entry. Degradation
  body precedent: `CapturedRunViewer` renders a `role="alert"` div when context is unavailable.
- Reuse: `canvas/model/paneLifecycle.ts` `PaneLifecyclePolicy`, `PANE_LIFECYCLE_POLICIES`,
  `resolvePaneLifecycle`. Per-kind `onMinimize` / `onRestore` / `onClose` hooks fed the ref, run by
  `canvas/model/paneAffordances.ts` `dismissPane` and `invokeDockedPaneRestoreLifecycle`. Precedent
  `canvas/model/capturedRunLifecycle.ts` `capturedRunLifecyclePolicy`. This is the owner for view
  teardown on close and hide/show on dock/restore.
- Reuse: `canvas/model/spawn.ts` `createPaneRecord`, `normalizeRef`; `canvas/model/canvasActions.ts`
  `createSpawnActions.spawnPane` (dedupe, focus, or restore from dock via
  `paneAffordances.ts::runSpawnPaneFlow`), `createPaneLifecycleActions.closePane` / `minimizePane` /
  `restorePaneAtIndex`, and `createCapturedRunActions.dropCapturedRunPane` (precedent for removing panes
  by an external key when the server says a resource is gone).
- Reuse: persistence rides free once the guard accepts the kind: `canvas/model/canvasStore.persistence.ts`
  `CANVAS_STORE_STORAGE_VERSION`, `PersistableCanvasPaneRef` (excludes `dev-blank` only);
  `canvas/infrastructure/persistence/canvasPanePersistence.ts` `rebuildPersistedPanes` /
  `seedPaneFromRecord`. Bump the version if the persisted shape changes (persisted-old-snapshot test per
  house rule).
- Reuse: pane chrome slots `canvas/workbench/chrome/PaneChrome.tsx` (`strip`, `subtitle`, `badge`) via
  `canvas/workbench/PaneWindow.tsx`; precedent `canvas/workbench/chrome/RunVitalsStrip.tsx` for a
  per-kind strip (a URL or navigation bar is the same slot).
- Similar checked and rejected: `registerViewer` in `registry.tsx` (runtime replace) has no production
  caller (searched `registerViewer(` across `www/packages`); do not register the browser viewer at runtime,
  add it to the static `registry` array like every other kind.
- Similar checked and rejected: `{kind:"resource", source:"url"}` in `PaneContentRef` plus
  `canvas/viewers/resource/ResourcePane.tsx`. It fetches content through `core` and renders it in the DOM
  (markdown, image, json, binary); it is a document viewer, not a live page, and its pane id is derived
  from the URL (one pane per URL). Wrong shape for a navigable live view.

### Pane open and close from the palette

- Reuse: `canvas/launcher/commandTypes.ts` `LauncherCommand` (leaf effect union),
  `canvas/launcher/commandRows.ts` `COMMAND_INTERACTIONS` (Enter/arrow lifecycle per command kind),
  `buildDevelopersRows` (the `spawn-terminal` and `spawn-empty-pane` rows are the exact row precedent),
  `interactionFor`.
- Reuse: URL entry. `canvas/launcher/spaceCommandInput.ts` `spaceCommandInputFor` /
  `completeSpaceCommandInput` already render an inline text field in the palette for a command that lacks
  its argument (`create-workdir` without `path`), and `useCommandCenter.ts` `beginSpaceInput` /
  `onInputKeyDown` drive it. Generalise the name, do not add a second input flow.
- Reuse: `canvas/workbench/CanvasCommandDispatcher.ts` `useCanvasCommandHandler`: the one switch that maps
  a `LauncherCommand` to a store action; `spawn-terminal` shows the try/catch shape for a spawn that can
  refuse.
- Reuse: `canvas/model/canvasState.ts` `CanvasStoreActions`, `SpawnPaneOptions` for the store contract.
- Reuse: palette open state and hotkeys: `canvas/launcher/useCommandCenter.ts` (`open`, `close`),
  `canvas/launcher/useLauncherHotkeys.ts`, keybinding registry `canvas/keybindings/registry.ts`.
- Tests: `canvas/launcher/commandRows.test.ts`, `canvas/launcher/useCommandCenter.test.tsx`,
  `canvas/workbench/CanvasCommandDispatcher.test.tsx`, e2e `www/packages/shell/tests/e2e/spawn-palette.spec.ts`
  with `tests/e2e/canvasPane.ts`.

### Pane open and close from the API (director)

- None found for non-run panes. Searches: `pane|canvas` in `tm/api/v1/controlplane_routes.py`,
  `controlplane_mcp.py`, `space_routes.py`, `space_mcp.py`, `packages/gateway/src/app.ts` (hits are the
  Space canvas CRUD, which is canvas identity, not pane contents); `ipcMain|ipcRenderer|WebContentsView|
  BrowserView|contentView` across `desktop`, `www`, `packages` (none). Pane records live in
  `canvas/model/canvasStore.ts` `useCanvasStore` and persist to browser storage keyed by canvas id
  (`canvas/infrastructure/persistence/canvasCacheStorage.ts`, `storageKeys.ts::CANVAS_STORAGE_KEYS`).
  `NOW.md` parking lot records this as intended: "Canvas-layout server store. Client-side today".
- Existing infra, the one server to pane channel: run adoption over the workspace activity SSE. Gateway
  `packages/activity/src/server/activityRouter.ts` (`/workspaces/:workspaceId/activity/stream`), proxied by
  `tm/api/v1/run_proxy.py` `create_run_proxy_mount.workspace_activity_stream` through
  `RunRouteProxy.stream_workspace_activity`; renderer `canvas/infrastructure/stream/useWorkspaceActivityStream.ts`
  on `core/useEventSource.ts` `useEventSource`; `canvas/model/capturedRunAdoption.ts`
  `CapturedRunAdoptionReconciler.applyFrames` turns frames into `adoptCapturedRun` panes, wired in
  `canvas/workbench/SessionCanvasRoute.tsx` `createCapturedRunAdoptionReconciler`. Close in the other
  direction: `tm/controlplane/service.py` `ControlPlaneService.close` terminates the run, the terminal WS
  closes with `run_closed` (`packages/contract/src/runtime/index.ts` `RUN_TERMINAL_CLOSE_REASONS`), and
  `canvas/viewers/terminal/CapturedRunPane.tsx` removes the pane. Proven end to end by
  `canvas/workbench/SessionCanvasRoute.activity.mcp-close.test.tsx`. This is the shape a browser pane
  resource would follow if the server owns pane state: server resource appears, canvas adopts; server
  resource closes, canvas drops.
- Existing infra, control-plane verbs today: REST `tm/api/v1/controlplane_routes.py` (`workspace_summary`,
  `whoami`, `roster`, `conversation`, `watch`, `prompt`, `wait_for_reply`, `launch`, `close`, `interrupt`,
  `unwatch`), MCP `tm/api/v1/controlplane_mcp.py` `create_control_plane_mcp` (same verbs plus `agents`,
  `harnesses`, and the Space tools from `tm/api/v1/space_mcp.py` `register_space_mcp_tools`), both over
  `tm/controlplane/service.py` `ControlPlaneService`. Twin-skin precedent with one shared contract module:
  `space_routes.py` and `space_mcp.py` over `tm/space/service.py` `SpaceCrudService` and
  `tm/api/v1/space_contracts.py`. Typed failure envelope for MCP: `tm/api/v1/mcp_tooling.py`
  `McpToolOutput`, `mcp_tool_result`; REST error mapping `controlplane_routes.py` `CONTROL_PLANE_ERROR_STATUS`
  over `tm/controlplane/errors.py` `ControlPlaneError` codes (`control_plane_unavailable` is the existing
  "no such capability here" code). Principal and authority: `tm/api/v1/controlplane_auth.py`
  `require_control_plane_principal`, `tm/space/authz.py` `require_director`.
- Existing infra, discovery surface: `tm/controlplane/observe_models.py` `SelfIdentityResult` already
  carries local endpoints (`proxy_url`, `inspector_url`) from `principal.identity.as_payload()`; the CDP
  attach point belongs beside them. Desktop runtime facts over HTTP: `tm/api/v1/desktop_runtime.py`
  `get_desktop_runtime` (`webPort`, `proxyPort`, `apiBaseUrl`, `defaultRouteUrl`).
- Existing infra, Python to gateway path: `tm/api/v1/run_proxy.py` `RunRouteProxy.request_http`,
  `forward_http`, `forward_sse`, `_forward_ws`, `require_http_origin`; gateway routes
  `packages/runtime/src/server/runtimeRouter.ts` (`/runs`, `/runs/:runId`, `/runs/:runId/terminate`,
  `/runs/:runId/input`, `/runs/:runId/terminal`, `/terminal`). Non-run gateway resource precedent:
  `packages/runtime/src/service/PlainTerminalSessions.ts` (plain terminals are not runs), mounted through
  `packages/gateway/src/main.ts` `createDefaultRuntimeRouterDeps`.
- Existing infra, readiness: `tm/api/v1/launch_readiness.py` `get_launch_readiness` over
  `tm/captured/readiness.py` `launch_readiness`; canvas `canvas/firstrun/useLaunchReadiness.ts`.
- Existing infra, main process outbound HTTP: `desktop/backendHealth.ts` `isBackendHealthy` /
  `waitForBackendHealth` use `fetch` against the Python loopback port; `desktop/hostedLiveness.ts`
  `registerHostedBackendLivenessPoll` polls it per window. Main has no inbound listener of any kind
  (`desktop/main.ts` only spawns children and creates windows).

### Pane geometry source

- Reuse: `canvas/engine/types.ts` `EngineLayoutState` (`nodes[paneId].rect: WorldRect`, `viewport:
  CanvasViewport {panX, panY, scale}`, `order`, `focusedPaneId`), `PaneNode.lifecycle` and `z`. Store slice
  `useCanvasStore((s) => s.layout)`; surface bounds `canvasStore.bounds` set by the `ResizeObserver` in
  `canvas/workbench/CanvasWorkbench.tsx`.
- Reuse: the projection contract `screen = world * scale + pan` is documented at
  `canvas/dnd/dndSpace.ts` `pointerToWorld` (inverse) and implemented forward, privately, at
  `canvas/interactions/dnd/CanvasDragSessionOverlay.tsx` `projectPaneRect` (CSS px relative to the
  viewport section); `canvas/engine/viewport.ts` `zoomViewportAt` inlines the same algebra. The surface's
  client origin is `CanvasWorkbench.tsx` `dndDeps.getSurfaceOrigin` (`surfaceRef.getBoundingClientRect`).
  Quantisation: `canvas/engine/layout/geometry.ts` `roundWorldRect`, `roundWorldPoint`.
- Fact that shapes the design: the store rect is the settled truth, not the on-screen truth. During a
  resize or free move `canvas/engine/react/PaneFrame.tsx` keeps a local `liveRect` and commits on release;
  during a sortable drag a dnd transform rides on top (`dndPanePosition`); framer-motion springs animate
  x, y, and size (`NORMAL_TRANSITION`, `LAYOUT_MOTION_TRANSITION`), and the world layer transitions the
  camera when `framing` is set (`LayoutCanvas.tsx`). The pane frame element is addressable
  (`data-pane-frame="true"`, `data-pane-id`, body `.pane-frame__body`), and the world element publishes
  its scale (`data-canvas-world`, `data-canvas-scale`, read by `PaneFrame.tsx` `currentWorldScale`). A
  DOM measurement of the frame is the only source that is correct mid-gesture; the store is the source
  that is correct at rest and is what the director can read.
- None found: `IntersectionObserver` (searched `canvas/`). Out-of-viewport clipping must be computed from
  `bounds` and the projected rect.
- Electron 43.0.0 facts, from the installed `electron.d.ts`
  (`node_modules/.pnpm/electron@43.0.0_supports-color@7.2.0/node_modules/electron/electron.d.ts`):
  `BrowserWindow.contentView: View`; `View.addChildView(view, index?)`, `removeChildView`,
  `setBounds(bounds: Rectangle, options?)`, `setVisible`, `getBounds`, `setBorderRadius`, event
  `bounds-changed`; `WebContentsView(options?: {webPreferences, webContents})` with `readonly webContents`.
  The desktop pins `electron: ^43.0.0` in `pnpm-workspace.yaml` catalog.

### Occlusion signals

- Reuse, drag overlay: `canvas/interactions/dnd/dragSessionStore.ts` `useDragSessionStore`,
  `beginDragSession`, `endDragSession`, `selectDragSession`. `session !== null` for the whole of any pane,
  dock, or native file drag (`dragSessionTypes.ts` `CanvasDragSource`); the overlay itself is
  `CanvasDragSessionOverlay` in the `LayoutCanvas` `overlay` slot. Pane lift specifically:
  `canvas/dnd/useReorderSettle.ts` `reorderActive` (already threaded to `zoomLocked`) and `SortablePane`
  `isDragging`.
- Reuse, pane state occluders: `canvasStore.expandedPaneId`, `framing.paneId`, `paneFlyIntent`
  (`canvas/model/paneAffordances.ts`); `PaneNode.lifecycle === "closing"` for the fade-out window
  (`canvas/engine/reducers/layoutState.ts` `CLOSE_DELAY_MS`); `docked` entries are not in `layout.nodes`.
- Palette, dock menu, fullscreen: each is a local `useState` (`canvas/launcher/useCommandCenter.ts` `open`,
  `canvas/workbench/dock/PaneDock.tsx` `open`, `canvas/hooks/useFullscreen.ts` `isFullscreen`). The only
  aggregator is the keybinding engine: `canvas/keybindings/engine.ts` `KeybindingEngineProvider`
  (`registerLauncher`, `registerDock`, `registerFullscreen`) builds a `CommandContext` whose targets expose
  `isOpen()` (`@tm/core/keybindings` `LauncherKeybindingTarget`, `DockKeybindingTarget`,
  `FullscreenKeybindingTarget`). It is pull-only, evaluated on keydown, and not subscribable. See Quality
  Map.
- Other DOM above panes: `CanvasWorkbench.tsx` `canvas-alert-stack` (route alerts, the
  `FirstRunScreen` readiness banner), `CanvasDropHint`, and the host chrome `www/packages/host/src/WindowDragRegion.tsx`
  (desktop only) and `ChannelBadge`, mounted before `#root` by `mountWindowChrome.tsx`. A `WebContentsView`
  composites above all of these; the drag strip in particular must not be covered.
- None found: a scroll container. The canvas pans and zooms by transform (`LayoutCanvas.tsx`); "scrolled
  out" means the projected rect leaves `bounds`.

### Renderer to main IPC

- None found. Searches: `ipcMain|ipcRenderer|\.handle\(|\.invoke\(` in `desktop/`; `ipcRenderer` in `www`
  and `packages`. The preload `desktop/preload.cts` exposes `transportMattersDesktop = {appName, platform,
  getPathForFile}` through `contextBridge.exposeInMainWorld` and nothing else. New code is justified.
- Reuse, the bridge contract: `core/desktopHost.ts` `TransportMattersDesktopBridge` (typed `window`
  augmentation), `DESKTOP_BRIDGE_KEY`, `getDroppedFilePathResolver` (optional capability that returns
  `null` when absent, the degradation shape to copy). Constraints stated in `preload.cts`: CommonJS
  `.cts`, `import = require`, and the bridge key literal duplicated on purpose across the CJS/ESM boundary
  with `desktop/app/packageSmokeLifecycle.ts` `DESKTOP_PRELOAD_BRIDGE_KEY` and `core/desktopHost.ts`
  `DESKTOP_BRIDGE_KEY` ("keep the three in sync"). `desktop/scripts/assert-preload-cjs.mjs` guards the
  emit.
- Tests: `desktop/preload.test.ts` transpiles `preload.cts` and runs it in a `node:vm` context with a stub
  `electron` (`contextBridge`, `webUtils`); extend the stub with `ipcRenderer`. Real-renderer proof:
  `desktop/app/packageSmokeLifecycle.ts` `awaitPreloadSmokeStatus` reads the bridge back with
  `executeJavaScript`.

### Main process per-window services

- Reuse: `desktop/hostedLiveness.ts` `registerHostedBackendLivenessPoll(window, ...)`: the per-window
  service precedent (subscribes `webContents.on("did-finish-load")`, tears down on `window.on("closed")`),
  attached through the `createWindow` decorator `desktop/main.ts` `registerHostedDesktopLifecycle`
  `createWindowWithLiveness`. Window construction: `desktop/window.ts` `createHostedWindow`,
  `createWindowOptions` (sandbox, contextIsolation, no nodeIntegration, preload),
  `registerHostedWindowPolicy` (`will-navigate` same-origin via `allowsHostedNavigation`,
  `setWindowOpenHandler` deny with `shouldOpenExternal` for https, `did-fail-load` dialog),
  `normalizeLoopbackHostedUrl` / `allowedHostedPath` (`/` and `/canvas` only).
- Reuse: the two window creation paths both funnel through `desktop/main.ts` `createMainWindow` and
  `buildMainWindowOptions`: managed (`startBackendAndCreateWindow` with the injected
  `BackendStartupDependencies.createWindow`) and hosted (`registerHostedDesktopLifecycle`);
  `desktop/app/DesktopLifecycle.ts` `bindDesktopWindowLifecycle` recreates a window on `activate`.
  Shutdown ordering: `desktop/app/DesktopShutdown.ts` finalizers via `desktopShutdownFinalizers`.
- Reuse: `desktop/env.ts` `ENV` (`TRANSPORT_MATTERS_*`, mirrored by `tm/env_keys.py`, "rename both
  together") for any opt-in switch; `resolveDesktopChannelSpec` for per-channel facts.
- Tests: `desktop/main.test.ts` (`vi.mock("electron")` with a `BrowserWindow` stub, `createHostedWindowFixture`,
  `registerHostedLifecycleFixture`), `desktop/window.test.ts` `createBrowserWindowFixture`,
  `desktop/main.reclaim.test.ts`, `desktop/main.standalone.test.ts`, `desktop/app/DesktopLifecycle.test.ts`.
  None of the `BrowserWindow` stubs carries `contentView`, `addChildView`, or `getContentBounds`.
- Trap: `desktop/tsconfig.json` `include` is an explicit file list. A new desktop source file compiles only
  after it is added there (`desktop/package.json` `build` runs `tsc -p tsconfig.json`).

### CDP or remote debugging flags

- None found. Searches: `remote-debugging|WebContentsView|BrowserView|commandLine|devtools|Debugger` in
  `desktop/src`; `commandLine` in `desktop`. New code is justified.
- Existing infra, Electron 43.0.0 typings: `app.commandLine.appendSwitch(the_switch, value?)`;
  `webContents.debugger` (`class Debugger`, `attach(protocolVersion?)`) for in-process CDP without a port.
  `agent-browser` requires the port form: `agent-browser connect <port>` or `--cdp <port>`, and
  `agent-browser tab` lists every target of the process (verified from `agent-browser skills get electron`,
  installed at `~/.local/share/mise/installs/node/25/bin/agent-browser`). A `--remote-debugging-port`
  switch applies to the whole process, so the app renderer becomes a target as well as each browser view.
- Placement fact: switches must be appended before `app.whenReady()` resolves. `desktop/main.ts`
  `registerDesktopLifecycleFromEnv` runs at module load, before every `whenReady` in the file, and already
  reads `env` first; it is the site.

### Localhost port discovery

- Reuse, desktop: `desktop/env.ts` `DesktopChannelSpec` (`webPort`, `proxyPort`, `gatewayPort` per channel
  from `channel-specs.json`), `desktop/main.ts` `resolveBackendStartupOptions` with `resolvePort`
  (`ENV.WEB_PORT`, `ENV.PROXY_PORT`, `ENV.GATEWAY_PORT` overrides), `desktop/desktopRuntime.ts`
  `readDesktopRuntimeStatus` (`transport-matters channel status --json`) and `liveRuntimePorts`;
  `desktop/window.ts` `rendererUrlForPort`, `DEFAULT_WEB_PORT`.
- Reuse, Python: `tm/api/v1/desktop_runtime.py` `get_desktop_runtime` over `tm/desktop_runtime.py`
  `discover_desktop_runtime`; `tm/channel.py` `resolve_channel_spec`.
- Reuse, gateway: `packages/gateway/src/main.ts` listens on `127.0.0.1` at `TRANSPORT_MATTERS_GATEWAY_PORT`
  or an ephemeral port and logs the address.
- Reuse, renderer: `core/transport.ts` `apiUrl`, `createApiTransport` (same-origin relative paths; no port
  literal exists in `www`, verified by grep). The window's own origin is `127.0.0.1:<webPort>`.
- Fact: `registerHostedWindowPolicy` governs the app renderer's `webContents` only. A browser view is a
  separate `webContents`; its navigation policy (localhost allowed, off-origin allowed, window.open) has no
  owner and must be stated explicitly (task rubric 3).

### Desktop vs browser-hosted detection

- Reuse: `core/desktopHost.ts` `isDesktopHost`, `globalWindow`, `canResolveDroppedFiles`. Consumers:
  `www/packages/host/src/WindowDragRegion.tsx` (renders nothing in a browser), `canvas/dnd/canvasDrop.ts`
  `DROP_HINT_MESSAGE` ("File drops need the desktop app. URL drags work here.") is the precedent for
  truthful degradation copy. Matrix test precedent: `www/packages/shell/tests/matrix/canvas/canvas-bundle.spec.ts`
  stubs `window.transportMattersDesktop = {}`.
- Reuse, server side: `tm/env_keys.py` `DESKTOP_CLIENT` (set by `tm/cli/desktop_cmd.py`, mirrored in
  `desktop/env.ts`) is how Python already knows a run was launched by the desktop.
- Existing infra for a typed "unavailable" answer: `tm/controlplane/errors.py` `ControlPlaneError` codes
  and `mcp_tooling.py` `McpToolOutput.failure`; `tm/api/v1/runs_unavailable.py` (501 skins mounted when the
  gateway is absent, see `tm/main.py`) is the precedent for a whole surface answering "not here".

### Tests for desktop main and canvas viewers

- Desktop runner: `desktop/vitest.config.ts` (`src/**/*.test.ts`), gate `desktop/justfile` `check:
  typecheck test`, root `justfile` `check`, `test`, `test-js`. Boundary test `desktop/rendererBoundary.test.ts`
  forbids React or a router under `desktop/src`.
- Canvas: `canvas/viewers/registry.test.ts` ("resolves each pane kind", "keeps registry identity aligned
  with the model", "keeps layout geometry out of the viewer registry"), `canvas/model/paneRecords.contract.test.ts`
  (type-level list of `PaneContentRef["kind"]`, must be edited for a new kind),
  `canvas/model/paneIdentity.test.ts`, `canvas/model/paneRecords.test.ts`, `canvas/model/paneLifecycle.test.ts`,
  `canvas/infrastructure/persistence/canvasPanePersistence.test.ts`, `canvas/workbench/CanvasPaneLayer.test.tsx`,
  `canvas/workbench/CanvasWorkbench.test.tsx`, `canvas/sessionCanvasBoundary.test.ts` (import direction:
  model never imports viewers or workbench; persistence never imports viewers), helpers
  `canvas/testUtils.tsx` (`installMockTransport`, `renderWithQuery`, `MockEventSource`) and
  `canvas/workbench/SessionCanvasRoute.testSupport.tsx`. Playwright: `www/packages/shell/tests/e2e/*.spec.ts`.
- Python: `tm/api/v1/test_controlplane_skins.py`, `test_controlplane_action_skins.py`,
  `test_controlplane_mcp_inventory.py`, `test_desktop_runtime.py`, `test_run_proxy_controlplane.py` are the
  skin and proxy test precedents.

## Quality Map

- Duplication / parallel implementation: `desktop/desktopRuntime.ts` `isRecord`, `requireString`,
  `optionalString`, `optionalPort` and `desktop/env.ts` `isRecord`, `requireString`, `optionalString`,
  `requirePort` are two private copies of the same JSON readers with different signatures, and
  `desktop/main.ts` `resolvePort` is a third port validator. `main.ts::hostedRouteHealthUrl` re-parses a
  port out of a URL that `window.ts::rendererUrlForPort` built.
- Duplication / parallel implementation: the electron module mock is hand-rolled five times
  (`main.test.ts`, `main.reclaim.test.ts`, `main.standalone.test.ts`, `window.test.ts`,
  `app/bundledResources.test.ts`, each with `vi.mock("electron")`), and the `BrowserWindow` stub shape is
  repeated inside `main.test.ts` (`createHostedWindowFixture`, `createProbeFixture`). Any per-window view
  service changes the stub in all of them.
- Duplication / parallel implementation: the forward world to screen projection lives once, privately, in
  `canvas/interactions/dnd/CanvasDragSessionOverlay.tsx` `projectPaneRect`, while the inverse is public in
  `canvas/dnd/dndSpace.ts` `pointerToWorld` and the same algebra is inlined in `canvas/engine/viewport.ts`
  `zoomViewportAt`. A second private copy for view bounds would be the fourth site.
- Boundary / design issue: the bridge key literal is triplicated by declared intent (`preload.cts`,
  `desktop/app/packageSmokeLifecycle.ts`, `core/desktopHost.ts`). `desktop` imports no `@tm/*` package
  today (grep `from "@tm/` in `desktop/src`: none), so sharing the constant means a new dependency edge
  from the desktop to `@tm/contract`. A bridge that grows methods makes the hand-kept mirror in
  `core/desktopHost.ts` `TransportMattersDesktopBridge` the contract of record for two build systems.
- Boundary / design issue: "which modal surface is open" has no reactive owner. Launcher, dock, and
  fullscreen each hold a local `useState`; the sole aggregator, `canvas/keybindings/engine.ts`
  `KeybindingEngineProvider`, reads `isOpen()` on keydown and cannot be subscribed to. Occlusion needs a
  subscribable signal. `dragSessionStore.ts` is the pattern that already exists for exactly this class of
  transient UI state.
- Boundary / design issue: `canvas/workbench/PaneWindow.tsx` branches on `pane.contentRef.kind ===
  "captured-run"` to choose the chrome strip and subtitle, a per-kind decision outside the registry, while
  `bodyDrag` is registry-owned. A browser pane's navigation strip would add a second `kind ===` branch.
- Boundary / design issue: adding a pane kind touches nine sites (`PaneContentRef`, `ViewerId`,
  `isPaneContentRef`, `paneIdForRef`, `titleForRef`, `viewerIdForRef`, the `registry` array,
  `paneRecords.contract.test.ts`, `registry.test.ts`). Guarded by the registry identity test, so it is
  safe, not DRY.
- Boundary / design issue: pane geometry has two truths (store rect at rest, DOM during gestures and
  springs, see Reuse Map). A view bounds sync that reads only the store will visibly lag during
  resize, sortable drag, expand/unexpand motion, and camera framing.
- Boundary / design issue: `desktop/tsconfig.json` enumerates source files by hand; a forgotten entry
  compiles nothing and fails at runtime, not at `tsc`.
- Boundary / design issue: `NOW.md` Phase 1 states the standing gate "no new UI until the control-plane
  UI redesign", with first-run work as the only exception. A browser pane is new UI.
- Dead code / obsolete path: `canvas/viewers/registry.tsx` `registerViewer` has no caller in production
  or tests (searched `www/packages`). `canvas/model/paneLifecycle.ts` `registerLifecycle` is called only
  from `paneAffordances.test.ts`.
- Sizing: `desktop/main.ts` is 674 lines (26 under the 700 hard limit); any view wiring pushes it over.
  `desktop/main.test.ts` is 985. `canvas/model/canvasIdentityOwner.ts` 579, `canvas/model/canvasActions.ts`
  572, `canvas/firstrun/FirstRunScreen.tsx` 623, `tm/controlplane/service.py` 668 (a new verb pair lands
  it at the limit), `tm/api/v1/space_mcp.py` 544, `tm/api/v1/controlplane_mcp.py` 511.
- Grooming recommendation:
  - refactor first: split `desktop/main.ts` (move `registerHostedDesktopLifecycle`,
    `startBundledStandalone`, `startAmbientOrManagedBackend`, `launchManagedBackend` into `desktop/app/`)
    and extract one shared electron mock fixture module for the five test files; split
    `tm/controlplane/service.py` before adding verbs.
  - refactor during the slice: promote `projectPaneRect` to `canvas/engine/viewport.ts` as the public
    forward projection and make `zoomViewportAt` use it; lift modal-open state to a subscribable store
    and have the keybinding targets read it; move the chrome strip/subtitle choice into
    `ViewerRegistration`; delete `registerViewer`; fold the three desktop JSON reader sets into one
    module.
  - defer with reason: the nine-site kind fan-out (tested, consistent with every other kind); the
    tsconfig include list (a one-line addition, called out in the slice brief); the bridge key triplicate
    unless the owner accepts the `desktop` to `@tm/contract` edge (record as a decision).

## Plan

- Decision needed: the `NOW.md` "no new UI" gate. The owner has commissioned this feature; record that
  the gate is consciously waived for it, or that it lands behind a flag (`canvas/featureFlags.ts` exists
  for that) so the standing rule survives.
- Decision needed: where pane state lives for director parity. Today panes are client-local; the
  director sees only runs. Two shapes fit the rubric's "no second copy in main": (a) the server owns a
  browser-pane resource (gateway or Python), the canvas adopts and drops it over the activity stream
  exactly as captured runs are adopted (`CapturedRunAdoptionReconciler` precedent), and main renders
  views for panes the renderer tells it about; or (b) the renderer's `canvasStore` stays the owner and
  the control plane reaches it by a new push channel to the renderer plus a renderer to main bridge, in
  which case the director cannot act while no canvas is open. Shape (a) keeps the API-first invariant
  (a headless director gets a typed answer with no renderer present); shape (b) is smaller. Recommend
  (a). Either way `NOW.md` parking lot "Canvas-layout server store" gains a first real entry and must be
  updated.
- Decision needed: CDP exposure form. Process-wide `--remote-debugging-port` (what `agent-browser
  connect` needs; exposes the app renderer too) versus per-view `webContents.debugger` (no port, no
  agent-browser). Recommend the switch, opt-in through a new `ENV` key, loopback only, off in the
  packaged default, and published through `whoami` beside `inspector_url`.
- Decision needed: accept the `desktop` to `@tm/contract` dependency edge to share the bridge key and
  the bridge message types, or keep the triplicate mirror and extend it by hand.
- Proposed steps bound to the reuse map (under recommendation (a) above):
  1. Refactor first (Quality Map): split `desktop/main.ts`; one electron mock fixture; split
     `tm/controlplane/service.py`. Gate green before any feature code.
  2. Contract: add the browser pane resource DTOs to `packages/contract` (wire shape, ids, close
     reasons) beside `packages/contract/src/runtime/index.ts` `RUN_TERMINAL_CLOSE_REASONS`; add the
     `kind: "browser"` variant to `PaneContentRef` with a per-instance key, the three `paneIdentity`
     switches, `isPaneContentRef`, `ViewerId`, and the two contract tests. Bump
     `CANVAS_STORE_STORAGE_VERSION` only if the persisted shape changes.
  3. Control plane: `ControlPlaneService` verbs for open, navigate, close, and list of browser panes,
     REST in `controlplane_routes.py`, MCP in `controlplane_mcp.py`, one shared contracts module (the
     `space_contracts.py` pattern), failures through `ControlPlaneError` / `McpToolOutput`. Attach point
     discovery on `SelfIdentityResult`. Headless and browser-hosted answers are typed
     `control_plane_unavailable`-class failures, never silent.
  4. Canvas adoption: extend the activity stream frames or add a sibling SSE on `useEventSource` so a
     server-created browser pane appears through `spawnPane` and a server-closed one leaves through the
     `dropCapturedRunPane` shape; palette `open-browser` command with the generalised text-input flow
     dispatches to the same server verb (twin clients, one path).
  5. Viewer: `defineViewer` entry rendering the placeholder body and, when `isDesktopHost()` is false,
     the truthful degradation body; lifecycle policy in `PANE_LIFECYCLE_POLICIES` for hide on minimize,
     show on restore, destroy on close; chrome strip through the registry slot added in the grooming
     pass.
  6. Bridge: preload namespace with invoke plus subscribe, typed on `TransportMattersDesktopBridge`,
     optional like `getPathForFile`; `preload.test.ts` stub grows `ipcRenderer`; package smoke reads
     the new key back.
  7. Main: `desktop/app/browserPanes.ts` (name per ownership) attached per window through the
     `createWindow` decorator seam used by `registerHostedBackendLivenessPoll`; bounds from the
     renderer's projected rect (store at rest, frame element during gestures), visibility from the
     modal store plus `dragSessionStore` plus `bounds` clipping; explicit `webPreferences` and
     navigation policy for the view; teardown on window `closed` and in the shutdown finalizers;
     `appendSwitch("remote-debugging-port")` in `registerDesktopLifecycleFromEnv` gated by the `ENV`
     key. Add every new file to `desktop/tsconfig.json`.
  8. Proof: `agent-browser connect <port>`, `agent-browser tab`, `snapshot -i` against a pane opened
     by the MCP verb, scripted and checked in beside `desktop/standaloneSmoke.ts`.
- Tests and gates: `just check` and `just test` at the root (verbatim, per house rule); `desktop`:
  `just check` (typecheck plus vitest), `pnpm package:smoke` for the preload; `www`:
  `pnpm --filter @tm/shell test` in full for the registry and persistence changes (structural rule),
  `pnpm --filter @tm/canvas test` for the kind, dispatcher, and boundary suites; `api`: `just test`
  covering `test_controlplane_skins.py`, `test_controlplane_action_skins.py`,
  `test_controlplane_mcp_inventory.py`, `test_desktop_runtime.py`; e2e `spawn-palette.spec.ts` extended
  for the browser row; the agent-browser attach script as the live gate.
