# Transport Matters — UI Structural / Boundary Map

**Verdict:** "Two UI layers (Electron desktop vs live web UI)" is an oversimplification bordering on wrong. `desktop/` renders no UI; it is an Electron shell that hosts the `www/` bundle. The real UI duality lives entirely inside `www/`: a breakpoint/intercept inspector vs a session-canvas agent-pane surface — one bundle, forked by URL path.

## 1. desktop/ (Electron) — pure host, zero renderer code
- Main-process entry: `desktop/src/main.ts`. Boots backend + proxy, opens the window.
- Window: `desktop/src/window.ts` `rendererUrlForPort` builds `http://127.0.0.1:{webPort}`; `window.loadURL(rendererUrl)` loads the FastAPI-served `www` bundle. Desktop ships **no renderer React** (there is not one `.tsx` under `desktop/src`).
- Labels: **main** = `main.ts`, `window.ts`, `backendProcess.ts`, `backendHealth.ts`, `desktopRuntime.ts`, `env.ts`; **preload** = `preload.cts`; **renderer** = none (delegated to www).
- Chrome: renders no app UI of its own. Its only DOM contribution (the title-bar drag strip) actually lives in www — `components/WindowDragRegion.tsx` — gated on `isDesktopHost()`.

## 2. www/ — one React bundle, two-tier routing
Single Vite build (`www/package.json` name `transport-matters`), lazy code-split — not multiple bundles.
- **Root fork:** `rootShell.tsx` `RootShell` + `session-canvas/route.ts` `selectRootRoute(pathname)`:
  - `/canvas` → `SessionCanvasRoute` — spawn-agent-into-pane canvas.
  - `/canvas-lab` → `CanvasLabRoute` — the lab.
  - else → `LegacyApp` (`app.tsx` → `routeLayout.tsx`).
- **Inside LegacyApp** (`routeLayout.tsx` `RouteLayout`, sub-routed by `stores/uiStore` `activeRoute`, switched in `components/RouteRail.tsx`):
  - `intercept` → `InterceptRoute`: `ExchangeList` + `BreakpointEditor` + `ExchangeDetail` + `ArmToggle`. **This is the live breakpoint/intercept UI, and it EXISTS today, fully wired** (`ArmToggle` → `hooks/useBreakpoint`; `BreakpointEditor` renders when `pausedFlow` is non-null).
  - `overlays` → `OverlaysView`, `trace` → `TraceView`, `recall` → `RecallView`.
- Session-canvas/spawn surface = `/canvas` (`SessionCanvasRoute`); lab = `/canvas-lab` (`CanvasLabRoute`).

## 3. Boundary
- www branches on Electron via `desktopHost.ts` `isDesktopHost()`, testing `DESKTOP_BRIDGE_KEY` (`"transportMattersDesktop"`) injected by `preload.cts` `contextBridge.exposeInMainWorld`. Consumers: `WindowDragRegion` (desktop-only drag region) and file-drop path resolution (`getPathForFile`).
- xterm agent-pane: `www/src/session-canvas/viewers/terminal/TerminalPane.tsx` (+ `terminalSession.ts`, `terminalSocket.ts`, `CapturedRunPane.tsx`). Lives in **www/**, not desktop/.
- Docs present: `www/README.md` only. **No `CLAUDE.md` in `desktop/` or `www/`; no `README.md` in `desktop/`.**

## 4. Recommendation input
**(a) Framing:** oversimplification. desktop/ is a host, not a UI layer; the two UI surfaces are both in www/ (inspector vs canvas), same bundle, path fork. Desktop can host either surface — it just loads a route URL.

**(b) Draft CLAUDE.md headers:**
- `desktop/CLAUDE.md`: "Electron shell for Transport Matters. Renders no React UI. `main.ts` boots the FastAPI backend + proxy and `window.loadURL`s the www bundle at `http://127.0.0.1:{webPort}`. Source is main-process + `preload.cts` only (preload bridges `window.transportMattersDesktop`). All UI lives in www/."
- `www/CLAUDE.md`: "The entire TM UI: one Vite/React bundle served by the backend, hosted by browser and the Electron shell alike. `rootShell.tsx` forks on path — `/canvas` = agent-pane canvas, `/canvas-lab` = lab, else the inspector app (`app.tsx` → `routeLayout.tsx`), whose `intercept` route is the live wire/breakpoint inspector (`ExchangeList` + `BreakpointEditor`). Desktop-only chrome gates on `isDesktopHost()`."

**(c) Misleading name:** `LegacyApp` / root route `"legacy"` (`rootShell.tsx` `routeComponents`, `route.ts` `RootRoute` + `selectRootRoute`) labels the LIVE flagship intercept inspector as "legacy" — a future agent reads that as deprecated/removable. Identifier-rename candidate (→ `inspector`), not a directory rename. Directory names `desktop/` and `www/` are fine; the real gap is the two missing CLAUDE.md files plus this "legacy" misnomer.
