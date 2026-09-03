---
title: "Transport Matters: www/ subtree map"
type: projects
tags: [transport-matters, www, web-frontend, inspector, canvas, roster, overlays, architecture, onboarding]
summary: "Source-verified map of the Transport Matters web frontend, including Inspector, Canvas, roster, overlays, state, server seams, data flows, conventions, performance, and landmines."
status: active
project: tm
related: [tm-map-api-opus, tm-map-shared-grok, tm-map-desktop-luna]
confidence: high
source: e97488ea
created: 2026-09-05
updated: 2026-09-05
---

<!-- fmm:map sha=e97488ea branch=fix/canvas-runs-shared-proxy dirty=false generated=2026-09-05T20:04:59+07:00 files=1865 loc=n/a -->

# `www/` codebase map

Generated: 2026-09-05T20:04:59+07:00  
Commit: `e97488ea`  
Branch: `fix/canvas-runs-shared-proxy`  
Working tree: clean  
Scope: `www/`, plus the API and TypeScript product plane handlers reached directly by browser code  
Index check: `fmm validate` reported all 1,865 source files current at this commit

## Confidence and method

Confidence is high for the static architecture, contracts, and data flow described here. I opened or structurally inspected 158 distinct files represented in the cited evidence set. For every documented server seam, I read both sides: the browser caller and response consumer in `www/`, then the receiving Python route or forwarder and, where applicable, the TypeScript Gateway handler. The three end to end traces were followed through their fetch, stream, store, action, and render stages. Type drift claims were checked against both handwritten browser types and backend parity tests.

Single read inferences are limited to intent and risk judgments such as component role labels, design rationale, and why a performance mechanism exists. The underlying behavior for those judgments remains cited to its implementation or test. No map area was omitted for budget. I did not launch the live frontend and backend, run browser end to end suites, or rebuild packages because this was a read only mapping task with no product code change. I did run `fmm validate` and a mechanical audit that resolved every retained `path:line` citation to an existing file and an in range line.

The checkout began at `730aaa96`, advanced during mapping to `feb6d42c`, then advanced again to `e97488ea` on `fix/canvas-runs-shared-proxy`. I detected both moves before finalization. For the first move, I reviewed the six changed files under `api/src/transport_matters/` and confirmed that `www/` had no diff. For the second, I confirmed that only `TLDR.md` changed and again that `www/` had no diff. I finally reran the index, source citation, stamp, and clean working tree checks against `e97488ea`; all citations in this artifact reflect that head.

## One minute model

`www/` contains two independent React products and one development compositor. The Inspector is the Tailwind web product at `/`; it watches captured exchanges, arms a wire breakpoint, edits a paused request, and releases it. Canvas is the Ark UI plus BEM desktop product at `/canvas`; it manages a spatial workspace of sessions, resources, terminals, captured runs, and native browser views. Each product owns a production entry and stylesheet. The shell imports both products only for local development, tests, and preview. Cross product imports are forbidden and tested. `www/packages/inspector/CLAUDE.md:1`, `www/packages/inspector/CLAUDE.md:8`, `www/packages/canvas/CLAUDE.md:1`, `www/packages/canvas/CLAUDE.md:9`, `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:47`

The browser talks to a same origin Python FastAPI process. Python owns capture, exchange, breakpoint, session, local file, harness, and Space CRUD routes. Managed run, activity, acting context, browsing, and terminal traffic enters Python and is forwarded to the TypeScript Gateway. The API mounts the Gateway forwards before mounting the two static SPAs. `api/src/transport_matters/main.py:552`, `api/src/transport_matters/main.py:565`, `api/src/transport_matters/main.py:588`, `api/src/transport_matters/main.py:637`

## Start here

Read these files in this order for most changes:

1. `www/packages/shell/src/rootShell.tsx:4` for product selection in development.
2. `www/packages/inspector/src/app.tsx:35` or `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:25` for the selected product's top composition.
3. `www/packages/inspector/src/routeLayout.tsx:135` for Inspector view selection, or `www/packages/canvas/src/viewers/registry.tsx:56` for Canvas pane dispatch.
4. `www/packages/core/src/queryKeys.ts:1` and `www/packages/core/src/transport.ts:150` for shared server state and HTTP behavior.
5. `www/packages/inspector/src/stores/uiStore.ts:19` or `www/packages/canvas/src/model/canvasStore.ts:21` for client state.
6. The nearest colocated test and, for Canvas visual code, the nearest side effect CSS import. Colocation is an enforced shipping invariant for resource and terminal viewers. `www/packages/canvas/src/viewers/resource/cssColocation.test.ts:33`, `www/packages/canvas/src/viewers/terminal/cssColocation.test.ts:32`

## Build, development, and serving

### Workspace and commands

The repository uses pnpm `11.18.0`, Node `>=20.19.0`, and a workspace that includes `www/packages/*`. Shared dependency versions pin React 19, TanStack Query, React Virtual, Zustand, Ark UI, dnd-kit, Framer Motion, xterm, Vite, Vitest, and TypeScript. `package.json:6`, `package.json:7`, `pnpm-workspace.yaml:1`, `pnpm-workspace.yaml:23`, `pnpm-workspace.yaml:31`, `pnpm-workspace.yaml:60`

From the repository root:

| Goal | Command | What it does |
| --- | --- | --- |
| Local frontend | `just www dev` | Enters `www/packages/shell` and runs `pnpm dev`. `justfile:49`, `www/packages/shell/justfile:7` |
| Full local stack | `just dev <client> <directory>` | Uses the channel specification, starts the backend in one tmux pane and the Vite shell in another, and injects the backend base URL. `justfile:113`, `scripts/local-dev-mode.sh:45`, `scripts/local-dev-mode.sh:92` |
| Frontend tests | `just www test` | Runs the shell's aggregated Vitest suite. `www/packages/shell/justfile:18` |
| Typecheck frontend | `just www typecheck` | Runs the shell TypeScript build check. The repository `just check` also checks every browser package separately. `www/packages/shell/justfile:30`, `justfile:96` |
| Production bundles | `just build` | Builds Inspector and Canvas separately before the Gateway and Python wheel. `justfile:117` |
| Full frontend gate | `just www check` | Formats, lints, and typechecks. `www/packages/shell/justfile:39` |

Each product's `build` script is `tsc -b && vite build`; `typecheck` is `tsc -b --noEmit`. `www/packages/inspector/package.json:11`, `www/packages/canvas/package.json:12`

### Three Vite configurations

| Config | Role |
| --- | --- |
| `www/packages/inspector/vite.config.ts` | Production Inspector. React plus Tailwind, base `/`, output `api/src/transport_matters/www/`. `www/packages/inspector/vite.config.ts:1`, `www/packages/inspector/vite.config.ts:6` |
| `www/packages/canvas/vite.config.ts` | Production Canvas. React only, base `/canvas`, output `api/src/transport_matters/canvas/`. `www/packages/canvas/vite.config.ts:1`, `www/packages/canvas/vite.config.ts:5` |
| `www/packages/shell/vite.config.ts` | Development and test compositor. It aliases the two package roots to source, imports both CSS roots, and proxies `/api`, `/v1`, and `/health` to the selected backend; WebSocket upgrades are enabled. Its local production output is only for preview and performance tests. `www/packages/shell/vite.config.ts:38`, `www/packages/shell/vite.config.ts:47`, `www/packages/shell/vite.config.ts:60`, `www/packages/shell/vite.config.ts:68` |

`www/vite.shared.ts` is the production config factory. It injects `__TRANSPORT_MATTERS_VERSION__`, preferring `TRANSPORT_MATTERS_VERSION`, then `git describe`, then `dev`; it resolves output paths from the workspace root and empties the target bundle directory. `www/vite.shared.ts:14`, `www/vite.shared.ts:18`, `www/vite.shared.ts:40`, `www/vite.shared.ts:45`

The shell rejects non HTTP proxy targets. With no `TRANSPORT_MATTERS_DEV_API_BASE_URL`, no proxy is installed, so direct `pnpm dev` expects another same origin arrangement or mocked traffic. `www/packages/shell/vite.config.ts:26`, `www/packages/shell/vite.config.ts:38`

### Entry points and render roots

| Entry | Bootstrap sequence |
| --- | --- |
| Shell | Imports Inspector, Canvas, and host CSS; prefetches meta only for Inspector; mounts host chrome before `#root`; then wraps `RootShell` in the shared `QueryClientProvider`. `www/packages/shell/src/main.tsx:1`, `www/packages/shell/src/main.tsx:13`, `www/packages/shell/src/main.tsx:22` |
| Inspector | Imports Inspector and host CSS; prefetches meta; mounts host chrome; renders `App` under the shared query client. `www/packages/inspector/src/main.tsx:1`, `www/packages/inspector/src/main.tsx:9`, `www/packages/inspector/src/main.tsx:18` |
| Canvas | Imports Canvas and host CSS; mounts host chrome; applies persisted theme tokens before React paint; renders `CanvasApp` under the shared query client. `www/packages/canvas/src/main.tsx:1`, `www/packages/canvas/src/main.tsx:9`, `www/packages/canvas/src/main.tsx:13` |

The shell uses exact path equality: only `pathname === "/canvas"` selects Canvas, while every other development shell path selects Inspector. Product components are lazy loaded. `www/packages/shell/src/route.ts:1`, `www/packages/shell/src/rootShell.tsx:4`, `www/packages/shell/src/rootShell.tsx:17`

Host chrome is a separate React root prepended to `<body>`. It contains the window drag region and channel badge and shares the query client. Mounting it before the app root preserves app hit testing by DOM order. `www/packages/host/src/mountWindowChrome.tsx:13`, `www/packages/shell/src/main.tsx:22`

### Production serving and channels

FastAPI serves explicit `/canvas` and then mounts the Canvas SPA before mounting Inspector at `/`; that registration order prevents the Inspector catch all from swallowing Canvas. Unknown non API, non asset paths fall back to each bundle's `index.html`. `api/src/transport_matters/main.py:139`, `api/src/transport_matters/main.py:166`, `api/src/transport_matters/main.py:177`, `api/src/transport_matters/main.py:189`

The desktop renderer defaults to stable web port `8788` and route `/canvas`. `desktop/src/rendererUrl.ts:3`

Channel selection is backend selection, not a frontend build flavor. `scripts/local-dev-mode.sh` reads `TRANSPORT_MATTERS_CHANNEL`, chooses proxy and web ports from the shared JSON, discovers a running channel URL when possible, and passes it to the Vite proxy. `scripts/local-dev-mode.sh:49`, `scripts/local-dev-mode.sh:52`, `scripts/local-dev-mode.sh:75`, `scripts/local-dev-mode.sh:92`

| Channel | Home | Database | Proxy, web, Gateway |
| --- | --- | --- | --- |
| stable | `.transport-matters` | `transport_matters` | 8787, 8788, 8789. `api/src/transport_matters/channel-specs.json:5` |
| preview | `.transport-matters-preview` | `transport_matters_preview` | 8797, 8798, 8799. `api/src/transport_matters/channel-specs.json:22` |
| dev | `.transport-matters-dev` | `transport_matters_dev` | 8807, 8808, 8809. `api/src/transport_matters/channel-specs.json:43` |

The browser learns the channel, cwd, workspace, Space, Worktree, Canvas, harnesses, and optional badge from `/api/meta`. `fetchMeta` converts the backend's snake case identity fields to camel case and brands IDs. The host hides the badge for stable. `www/packages/core/src/transport.ts:280`, `www/packages/core/src/transport.ts:295`, `www/packages/host/src/ChannelBadge.tsx:3`

## Package and ownership map

| Package | Owns | Public surface |
| --- | --- | --- |
| `@tm/shell` | Development composition, Vite and Vitest configuration, Playwright suites, and architecture enforcement tests. Production bundles come from the two product packages. `www/packages/shell/vite.config.ts:60`, `www/packages/shell/src/rootShell.tsx:17` | Internal application package. |
| `@tm/inspector` | Exchange list and detail, breakpoint editor, override editing, route rail, Inspector state, and Tailwind theme. `www/packages/inspector/CLAUDE.md:21` | `.`, `./inspector.css`, `./storageKeys`. `www/packages/inspector/package.json:6` |
| `@tm/canvas` | Spatial workbench, layout engine, launcher, viewers, drag interactions, browser presentation, run lifecycle, themes, and ambient scenes. `www/packages/canvas/CLAUDE.md:29` | `.`, Canvas CSS, storage keys, and ambient background factory. `www/packages/canvas/package.json:6` |
| `@tm/core` | Shared browser transport, query client and keys, exchange stream reducer, low level hooks, generic formatting, shared browser bridges, and frontend wire mirrors. `www/packages/core/package.json:6`, `www/packages/core/src/transport.ts:24`, `www/packages/core/src/queryKeys.ts:1` | `.`, keybindings, testing, and `types/*`. `www/packages/core/package.json:6` |
| `@tm/space-client` | Browser client and URL context utilities for Spaces, Worktrees, Canvases, and acting context. `www/packages/space-client/src/spaceTransport.ts:1` | One `.` entry. `www/packages/space-client/package.json:6` |
| `@tm/host` | Window drag region and environment badge, each outside product UI. `www/packages/host/src/mountWindowChrome.tsx:13` | Component entry and one explicit stylesheet. `www/packages/host/package.json:6` |

Browser code may import public contract leaves such as `@tm/contract/browsing` and `@tm/contract/space`, but may not import product plane implementations such as `@tm/browsing`, `@tm/space`, `@tm/runtime`, or `@tm/gateway`. The shell test resolves aliases and export maps, rejects deep reach ins, and scans browser imports for these forbidden edges. `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:37`, `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:77`, `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:161`

## Route and view map

### Inspector screens

Inspector does not use a URL router. `useUIStore.activeRoute` is a persisted lens over the same run and accepts `intercept`, `overlays`, `trace`, or `recall`. Number key route switching is installed by `useRouteHotkeys`. `www/packages/inspector/src/stores/uiStore.ts:7`, `www/packages/inspector/src/stores/uiStore.ts:17`, `www/packages/inspector/src/app.tsx:56`

| Screen or surface | Top component and behavior |
| --- | --- |
| Waiting entry | `www/packages/inspector/src/routeLayout.tsx:83`, `WaitingScreen`. Replaces the whole normal frame when live view is empty, history is off, and no request is paused. It exposes connection state, arm control, and Show history. `www/packages/inspector/src/routeLayout.tsx:217` |
| Intercept | `www/packages/inspector/src/routeLayout.tsx:135`, `InterceptRoute`. A fixed width virtualized exchange and track list on the left; the right side selects paused editor, exchange detail, hidden history recovery, or empty guidance. `www/packages/inspector/src/routeLayout.tsx:167`, `www/packages/inspector/src/routeLayout.tsx:182` |
| Captured exchange list | `www/packages/inspector/src/components/ExchangeList.tsx:136`. Projects track hierarchy into fixed virtual rows and paints `TrackHeader` or `ExchangeTurnCard`. `www/packages/inspector/src/components/ExchangeList.tsx:152`, `www/packages/inspector/src/components/ExchangeList.tsx:192` |
| Captured exchange detail | `www/packages/inspector/src/components/ExchangeDetail.tsx:210`. Queries one exchange and switches among Inspect, Request, Response, and Transport panels, with an Inspect fullscreen. `www/packages/inspector/src/components/ExchangeDetail.tsx:224`, `www/packages/inspector/src/components/ExchangeDetail.tsx:356` |
| Paused breakpoint editor | `www/packages/inspector/src/components/editor/BreakpointEditor.tsx:20`. Replaces detail whenever `pausedFlow` exists, with Messages, Tools, System, Sampling, provider extras, raw form, actions, and fullscreen. `www/packages/inspector/src/routeLayout.tsx:182`, `www/packages/inspector/src/components/editor/BreakpointEditor.tsx:65`, `www/packages/inspector/src/components/editor/BreakpointEditor.tsx:99` |
| Overlays | `www/packages/inspector/src/components/routes/OverlaysView.tsx:295`. Local curation surface with empty, one draft, and confirmed list states. Its data model does not apply overlays to interception. `www/packages/inspector/src/components/routes/OverlaysView.tsx:9`, `www/packages/inspector/src/components/routes/OverlaysView.tsx:20` |
| Trace | `www/packages/inspector/src/components/routes/TraceView.tsx:1`. Atmospheric placeholder; the route rail marks it SOON. `www/packages/inspector/src/components/RouteRail.tsx:25` |
| Recall | `www/packages/inspector/src/components/routes/RecallView.tsx:1`. Atmospheric placeholder; the route rail marks it SOON. `www/packages/inspector/src/components/RouteRail.tsx:25` |
| Route rail and app bar | `www/packages/inspector/src/routeLayout.tsx:217`. The app bar owns product identity, exchange count, live state, and arm toggle; `RouteRail` changes the store lens. `www/packages/inspector/src/routeLayout.tsx:233`, `www/packages/inspector/src/components/RouteRail.tsx:37` |

### Canvas screens and pane surfaces

`CanvasApp` lazy loads one `SessionCanvasRoute`. That route parses query launch context, verifies Canvas identity, starts launch resolution and streams, shows the first run banner when infrastructure is not ready, and otherwise composes `CanvasWorkbench`. A query flag selected by `isStressCanvas` replaces the workbench with a stress harness. `www/packages/canvas/src/app.tsx:3`, `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:25`, `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:74`

| Screen or surface | Top component and behavior |
| --- | --- |
| Main workbench | `www/packages/canvas/src/workbench/CanvasWorkbench.tsx:25`. Owns ambient backdrop, command center, alerts, drag context, pane layer, dock, and browser placement presentation. `www/packages/canvas/src/workbench/CanvasWorkbench.tsx:132` |
| First run and readiness | `www/packages/canvas/src/firstrun/FirstRunScreen.tsx:51`. Embedded alert with infrastructure checks, harness inventory, refresh, enablement, and provider access tests. The route shows it while readiness is not populated and ready. `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:83` |
| Command center | `www/packages/canvas/src/launcher/CommandCenter.tsx:41`. A scoped command palette for sessions, agents, Spaces, Worktrees, Canvases, browser history, settings, and pane actions. It dispatches domain commands rather than writing layout directly. `www/packages/canvas/src/launcher/CommandCenter.tsx:97` |
| Pane field | `www/packages/canvas/src/workbench/CanvasPaneLayer.tsx:64`. Adapts `canvasStore` records to `LayoutCanvas`, stable render callbacks, DnD, pane chrome, focus, move, resize, expand, and close. `www/packages/canvas/src/engine/react/LayoutCanvas.tsx:112` |
| Dock | `www/packages/canvas/src/workbench/dock/PaneDock.tsx:39`. Local open state over the store's minimized pane records, with restore and close actions. |
| Ambient scene | `www/packages/canvas/src/workbench/background/AmbientBackdrop.tsx:50`. Reads the active theme scene and hosts the runtime scene renderer behind panes. |
| Session roster | `www/packages/canvas/src/viewers/session-picker/SessionPickerPane.tsx:7`. Lists up to 50 local workspace sessions with keyboard selection, open, continue, loading, empty, and retry states. `www/packages/canvas/src/viewers/session-picker/SessionPickerPane.tsx:27`, `www/packages/canvas/src/viewers/session-picker/SessionPickerPane.tsx:51` |
| Transcript | `www/packages/canvas/src/viewers/transcript-chat/TranscriptChatPane.tsx:15`, `TranscriptChatPane`. Loads event backlog, folds events through a reducer, streams new events with gap backfill, filters denylisted native payloads, and renders transcript messages. `www/packages/canvas/src/viewers/transcript-chat/TranscriptChatPane.tsx:36`, `www/packages/canvas/src/viewers/transcript-chat/TranscriptChatPane.tsx:54` |
| Resource | `www/packages/canvas/src/viewers/resource/ResourcePane.tsx:21`. Chooses session resource, local path, or URL handling, then dispatches text, Markdown, JSON, image, binary, exchange redirect, or missing response. `www/packages/canvas/src/viewers/resource/ResourcePane.tsx:36`, `www/packages/canvas/src/viewers/resource/ResourcePane.tsx:111` |
| Provider exchange | `www/packages/canvas/src/viewers/resource/ArkExchangeViewer.tsx:141`. Read only Canvas fork of Inspector detail with Inspect, Request, Response, Events, and Diagnostics tabs and fullscreen. Its comments identify the deliberate fork and omitted Inspector behavior. `www/packages/canvas/src/viewers/resource/ArkExchangeViewer.tsx:1`, `www/packages/canvas/src/viewers/resource/ArkExchangeViewer.tsx:187` |
| Local terminal | `www/packages/canvas/src/viewers/terminal/TerminalPane.tsx:16`. One xterm instance and one local PTY WebSocket per pane. Unmount tears down the socket and terminal. `www/packages/canvas/src/viewers/terminal/TerminalPane.tsx:9` |
| Captured run | `www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx:60`. Idempotently spawns or reattaches a managed run, attaches its PTY, displays protocol errors and scrollback truncation, and keeps final output for most close reasons. `www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx:48`, `www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx:115` |
| Browser pane | `www/packages/canvas/src/viewers/browser/BrowserPane.tsx:71`. Reserves an empty DOM rectangle for a desktop native view when composited; in a browser or failure state it shows truthful fallback copy, an external link, and close. `www/packages/canvas/src/viewers/browser/BrowserPane.tsx:65` |
| Subagent timeline | `www/packages/canvas/src/viewers/placeholder/PlaceholderPane.tsx:43`. Explicit placeholder with identity and provenance. No fetch is made; the real viewer has not landed. `www/packages/canvas/src/viewers/placeholder/PlaceholderPane.tsx:38` |
| Stress harness | `www/packages/canvas/src/perf/SessionCanvasStressRoute.tsx:30`. Synthetic 1, 2, 4, 8, 16, or 30 pane layout with frame measurements for spawn, close, focus, drag, resize, pan, and zoom. `www/packages/canvas/src/perf/SessionCanvasStressRoute.tsx:19`, `www/packages/canvas/src/perf/SessionCanvasStressRoute.tsx:44` |

Every pane kind is registered in one ordered typed registry. The registration owns matching, pane ID, title, optional body drag, chrome subtitle or strip, and renderer. `resolveViewer` throws on an unregistered kind. Terminal and captured run viewers are lazy chunks because xterm is heavy. `www/packages/canvas/src/viewers/registry.tsx:26`, `www/packages/canvas/src/viewers/registry.tsx:40`, `www/packages/canvas/src/viewers/registry.tsx:56`, `www/packages/canvas/src/viewers/registry.tsx:184`

## Component architecture and styling

### Composition patterns

Inspector is prop driven from one product shell. `BrowserAppShell` subscribes to UI state and query hooks, derives run and selection state, starts the exchange stream, and passes a complete view model into `RouteLayout`. `RouteLayout` contains route selection; leaf components own local interaction state and query only the data they display. `www/packages/inspector/src/app.tsx:35`, `www/packages/inspector/src/app.tsx:45`, `www/packages/inspector/src/app.tsx:92`, `www/packages/inspector/src/routeLayout.tsx:217`

Canvas uses a domain model plus registries. `SessionCanvasRoute` owns external identity and readiness. `CanvasWorkbench` subscribes to narrow Zustand selectors and hands stable actions to the engine. `CanvasPaneLayer` resolves each `PaneContentRef` through `viewers/registry.tsx`. Launcher behavior is data driven through command and row registries. `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:25`, `www/packages/canvas/src/workbench/CanvasWorkbench.tsx:36`, `www/packages/canvas/src/viewers/registry.tsx:184`

Canvas pane records are the central discriminated model. Add a new pane by extending the ref union and identity functions, adding a registry entry and lifecycle semantics, then teaching persistence if the pane should survive reload. Do not branch on pane kind in arbitrary components. The registry already centralizes renderer and chrome decisions. `www/packages/canvas/src/model/paneRecords.ts:1`, `www/packages/canvas/src/viewers/registry.tsx:56`

Shared browser primitives live in `@tm/core`, not in either product. Shared visual chrome is limited to `@tm/host`; each product owns its own visual language. The public export maps and import graph tests prevent private reach ins and Inspector to Canvas coupling. `www/packages/core/package.json:6`, `www/packages/host/package.json:6`, `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:47`, `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:118`

### Inspector styles

Inspector has one Tailwind root, `www/packages/inspector/src/inspector.css`. It explicitly scans its package, declares semantic color, typography, radius, and frame tokens under `@theme`, installs resets and global interaction styles, then defines craft primitives such as `.frame`, `.hairline-x`, `.card`, `.label`, and field validation. `www/packages/inspector/src/inspector.css:1`, `www/packages/inspector/src/inspector.css:8`, `www/packages/inspector/src/inspector.css:132`, `www/packages/inspector/src/inspector.css:346`

The Inspector has no runtime theme system. Its accent and token values stay in the stylesheet. Utility class strings are the normal component styling approach. `www/packages/inspector/CLAUDE.md:27`

### Canvas styles and controls

Canvas is Tailwind free. `index.css` imports reset, tokens, launcher base, workbench base, and placeholder CSS. Components with substantial private styling side effect import their colocated stylesheet. `www/packages/canvas/src/index.css:1`, `www/packages/canvas/src/workbench/chrome/PaneChrome.tsx:1`, `www/packages/canvas/src/launcher/CommandCenter.tsx:16`

Canvas uses product prefixed BEM classes such as `canvas-picker__row`, `canvas-pane-*`, and `terminal-pane__surface`. A shell test scans every Canvas `className` literal for Tailwind utility tokens because the composed dev shell can accidentally make stray utilities work while the standalone Canvas bundle ships them unstyled. `www/packages/shell/src/testSupport/canvasTailwindFree.test.ts:1`, `www/packages/shell/src/testSupport/canvasTailwindFree.test.ts:63`

Canvas defaults and layout constants live in `www/packages/canvas/src/styles/tokens.css`; active themes override accent and `--pane-*` knobs inline on `:root`. Similar Inspector values are intentional product copies. Do not combine the token files. `www/packages/canvas/src/styles/tokens.css:1`, `www/packages/canvas/src/styles/tokens.css:54`, `www/packages/canvas/src/styles/tokens.css:68`, `www/packages/canvas/CLAUDE.md:37`

Reusable Canvas buttons, toggles, tooltips, icon factory, pane chrome, state frames, truncation notes, copy controls, code text, and JSON tree live near their owning layer under `workbench/controls`, `icons`, `workbench/chrome`, and `viewers/*/primitives`. Prefer these before adding another visual atom. Existing CSS colocation tests explain that an unimported side effect stylesheet can pass type checks and still disappear from the bundle. `www/packages/canvas/src/viewers/resource/cssColocation.test.ts:33`, `www/packages/canvas/src/viewers/terminal/cssColocation.test.ts:32`

## State management and invalidation

### React Query server state

One shared `QueryClient` defaults to 30 seconds stale time and one retry. Both product roots and host chrome use it. `www/packages/core/src/queryClient.ts:1`, `www/packages/host/src/mountWindowChrome.tsx:17`

Canonical shared keys are in `www/packages/core/src/queryKeys.ts`. They cover exchange lists and details, turn content, session resources, session lists, launch resolution, and session events. Harness inventory and launch readiness use exported constants. Feature local keys exist for overrides, breakpoint status, Spaces, Canvases, runtime templates, local files, browser history, and run reconciliation. `www/packages/core/src/queryKeys.ts:1`, `www/packages/core/src/queryKeys.ts:11`, `www/packages/core/src/queryKeys.ts:25`, `www/packages/core/src/queryKeys.ts:46`

| Cache | Writer and subscribers | Freshness and invalidation |
| --- | --- | --- |
| `['meta']` | `useMeta`; prefetched by Inspector and shell Inspector entry, read by app, badge, overlays, detail, and Canvas identity. `www/packages/core/src/useMeta.ts:12`, `www/packages/inspector/src/main.tsx:9` | Infinite stale time because backend cwd is process fixed. `www/packages/core/src/useMeta.ts:4` |
| `['exchanges', runId]` | `useExchanges` fetches and projects tracks; exchange SSE mutates the list. Inspector list subscribes through `BrowserAppShell`. `www/packages/inspector/src/app.tsx:47`, `www/packages/core/src/exchangeStreamEvents.ts:209` | SSE applies inserts, updates, deletes, and caps at 500. A reconnect of the same stream invalidates the whole exchange prefix for backfill. `www/packages/core/src/transport.ts:22`, `www/packages/inspector/src/hooks/useExchangeStream.ts:64` |
| `['exchange', runId, id]` | `ExchangeDetail` and Canvas `ArkExchangeViewer` fetch it. Breakpoint release invalidates the provisional detail. `www/packages/inspector/src/components/ExchangeDetail.tsx:224`, `www/packages/inspector/src/components/editor/BreakpointEditorActions.ts:142` | Detail query disables retry. Exchange SSE invalidates affected details after an exchange event. `www/packages/inspector/src/components/ExchangeDetail.tsx:228`, `www/packages/core/src/exchangeStreamEvents.ts:246` |
| `['turn-content', runId, id]` and pipeline token keys | Exchange cards and detail sections fetch these lazily. `www/packages/core/src/queryKeys.ts:18`, `www/packages/core/src/transport.ts:188`, `www/packages/core/src/transport.ts:223` | Stream processing invalidates turn content for changed exchange IDs. Pipeline results are server cached when already stamped. `www/packages/core/src/exchangeStreamEvents.ts:246`, `www/packages/core/src/transport.ts:215` |
| `['overrides', runId, trackId]` | `useOverrides` reads and mutates; breakpoint editor subscribes. `www/packages/inspector/src/hooks/useOverrides.ts:22`, `www/packages/inspector/src/components/editor/BreakpointEditorActions.ts:69` | Patch and toggle write response data directly; clear invalidates. `www/packages/inspector/src/hooks/useOverrides.ts:36`, `www/packages/inspector/src/hooks/useOverrides.ts:46`, `www/packages/inspector/src/hooks/useOverrides.ts:51` |
| sessions and events | `useSessions`, transcript backlog, and launch resolution. `www/packages/canvas/src/hooks/useSessions.ts:5`, `www/packages/canvas/src/hooks/useLaunchSession.ts:9` | Ordinary 30 second default for rosters. Launch resolution polls every second until resolved. Session SSE uses `last_seq`; a gap triggers bounded HTTP backfill before the new frame. `www/packages/canvas/src/hooks/useLaunchSession.ts:7`, `www/packages/canvas/src/infrastructure/stream/useSessionEventStream.ts:77` |
| harness inventory | First run surface. `www/packages/canvas/src/firstrun/useHarnessInventory.ts:38` | 30 second stale time; polls every 3 seconds only while startup activity or a confirmed access test is active. `www/packages/canvas/src/firstrun/useHarnessInventory.ts:11`, `www/packages/canvas/src/firstrun/useHarnessInventory.ts:39` |
| launch readiness | `SessionCanvasRoute` gates first run banner. `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:30` | Infinite stale, no mount, reconnect, or focus refetch. Explicit retry owns rechecks; enablement mutation invalidates it. `www/packages/canvas/src/firstrun/useLaunchReadiness.ts:11`, `www/packages/canvas/src/firstrun/FirstRunScreen.tsx:325` |
| Spaces, Canvases, agents, browser history | Launcher hooks and command dispatcher. | Mutations either set returned authoritative data or invalidate the relevant inventory. Preserve each hook's current pattern; for example Space command completion updates or invalidates its inventory rather than mutating pane state ad hoc. `www/packages/canvas/src/launcher/useSpaces.ts:1`, `www/packages/canvas/src/launcher/useCanvases.ts:1`, `www/packages/canvas/src/workbench/spaceCommandDispatcher.ts:125` |

### Persistent and process local stores

| Store or signal | State owner | Writers | Subscribers and persistence |
| --- | --- | --- | --- |
| Inspector `useUIStore` | Route, selected exchange, history option, paused and forwarding flow, auto expand, collapsed tracks. `www/packages/inspector/src/stores/uiStore.ts:19` | App selection and route actions; exchange SSE sets paused and selected state and updates forwarding activity; breakpoint actions start or clear forwarding. `www/packages/inspector/src/app.tsx:35`, `www/packages/inspector/src/hooks/useExchangeStream.ts:20`, `www/packages/inspector/src/components/editor/BreakpointEditorActions.ts:60` | App shell, route layout, editor sections, and hotkeys subscribe. Only route, selection, auto expand, and collapsed tracks persist. History, paused flow, and forwarding state reset on load. `www/packages/inspector/src/stores/uiStore.ts:49`, `www/packages/inspector/src/stores/uiStore.ts:88` |
| Inspector `useOverlaysStore` | Confirmed overlays and at most one draft, including name, scope, override batch, and timestamps. `www/packages/inspector/src/stores/overlaysStore.ts:7`, `www/packages/inspector/src/stores/overlaysStore.ts:43` | Breakpoint Save as overlay creates the draft; `OverlaysView` hydrates cwd, edits, confirms, discards, and deletes. `www/packages/inspector/src/components/editor/BreakpointEditor.tsx:41`, `www/packages/inspector/src/components/routes/OverlaysView.tsx:88` | Persisted as the local curation model. It is separate from backend `useOverrides`; confirmed overlay rows currently have no apply pipeline. `www/packages/inspector/src/stores/overlaysStore.ts:69`, `www/packages/inspector/src/components/routes/OverlaysView.tsx:20` |
| Canvas `useCanvasStore` | Pane records, engine layout, dock, bounds, framing, pane flight intent, counters, and pane actions. It wraps a raw Zustand store behind a narrow hook and imperative port. `www/packages/canvas/src/model/canvasStore.ts:21`, `www/packages/canvas/src/model/canvasStore.ts:31` | `createCanvasActions`, command dispatchers, viewer actions, DnD, and browser stream upserts. `www/packages/canvas/src/model/canvasStore.ts:65`, `www/packages/canvas/src/browsing/useBrowserPaneStream.ts:68` | `CanvasWorkbench`, pane layer, viewers, keybindings, and browser placement subscribe. Persisted per verified Canvas ID through dynamic storage; browser panes and development blank panes are removed from the persisted slice because the server or development owns them. `www/packages/canvas/src/model/canvasStore.persistence.ts:25`, `www/packages/canvas/src/model/canvasStore.persistence.ts:49`, `www/packages/canvas/src/infrastructure/persistence/canvasCacheStorage.ts:6` |
| Private Canvas identity store | Claimed or verified acting context, navigation Space, spawn Worktree, fallback locator, hydration status, and resolution error. `www/packages/canvas/src/model/canvasIdentityOwner.ts:94` | The sole dispatcher verifies launch claims, resolves Workdirs, installs selections, activates per Canvas cache, and rewrites identity URL. A one owner guard rejects a second connection. `www/packages/canvas/src/model/canvasIdentityOwner.ts:175`, `www/packages/canvas/src/model/canvasIdentityOwner.ts:185`, `www/packages/canvas/src/model/canvasIdentityOwner.ts:237` | `SessionCanvasRoute`, workspace hooks, stream gates, and command dispatchers subscribe through exported selectors. This store itself is process local; a small locator and per Canvas cache persist separately. Only this file may call `history.replaceState`, enforced by a shell test. `www/packages/canvas/src/model/canvasIdentityOwner.ts:122`, `www/packages/canvas/src/model/canvasIdentityOwner.ts:508`, `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:56` |
| `useCapturedRunStore` | Run records by stable pane key, launch permission settings, control plane grant, and termination failures. `www/packages/canvas/src/model/capturedRunStore.ts:101`, `www/packages/canvas/src/model/capturedRunStore.ts:172` | Binding ensures an idempotent run, adoption records externally started runs, pane close terminates, and settings commands update policy. In flight spawn promises deduplicate StrictMode; a five slot queue limits concurrent creates; cancellation and minimize intent close race windows. `www/packages/canvas/src/model/capturedRunStore.ts:38`, `www/packages/canvas/src/model/capturedRunStore.ts:50`, `www/packages/canvas/src/model/capturedRunStore.ts:207`, `www/packages/canvas/src/model/capturedRunStore.ts:270` | Captured pane, vitals strip, reconciliation, workbench alerts, and dock subscribe. Run IDs and launch settings persist; transient promise sets and termination failures do not. `www/packages/canvas/src/model/capturedRunStore.ts:340`, `www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx:71` |
| `useBrowserPaneStore` | Stream connection, presenter ID, server presentations, and close failures. `www/packages/canvas/src/browsing/browserPaneStore.ts:8` | Browser SSE applies snapshots, deltas, and closes; close lifecycle records failures. `www/packages/canvas/src/browsing/useBrowserPaneStream.ts:68` | Browser body and chrome subscribe. It never persists, because desired URL and existence are server and pane ref facts. `www/packages/canvas/src/browsing/browserPaneStore.ts:65` |
| `useRunVitalsStore` | Activity rows by run ID and workspace rollup. `www/packages/canvas/src/model/runVitalsStore.ts:11` | Workspace activity SSE reducer writes; route cleanup clears. The same frames feed captured run adoption. `www/packages/canvas/src/workbench/useCapturedRunAdoption.ts:12`, `www/packages/canvas/src/workbench/useCapturedRunAdoption.ts:29` | `RunVitalsStrip` resolves pane key to run ID and subscribes. Nonpersistent; reconnect snapshot reseeds it. `www/packages/canvas/src/workbench/chrome/RunVitalsStrip.tsx:32`, `www/packages/canvas/src/model/runVitalsStore.ts:13` |
| `useDragSessionStore` | One current cross pane drag session. `www/packages/canvas/src/interactions/dnd/dragSessionStore.ts:8` | Module functions begin, retarget, and end. `www/packages/canvas/src/interactions/dnd/dragSessionStore.ts:20` | DnD overlays, browser view occlusion, and presentation subscribe. Process local. `www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:119` |
| `useOverlayStore` | Mirrored launcher, dock, and fullscreen openness. Fullscreen is a count because several viewers can register. `www/packages/canvas/src/interactions/overlayStore.ts:3`, `www/packages/canvas/src/interactions/overlayStore.ts:11` | Keybinding hooks mirror component local open state on effect mount and cleanup. `www/packages/canvas/src/keybindings/engine.ts:135`, `www/packages/canvas/src/keybindings/engine.ts:184` | Keybinding gates and browser placement subscribe so native views hide under modal surfaces. Process local. `www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:97` |
| `useThemeStore` | Full `ThemeDefinition`, live day cycle, cycle, scene tuning. `www/packages/canvas/src/stores/themeStore.ts:9` | Theme commands and scene controls. | Persisted with defensive migration. `useThemeTokens` writes active tokens to `:root`; ambient backdrop subscribes to scene choice. `www/packages/canvas/src/stores/themeStore.ts:85`, `www/packages/canvas/src/stores/themeStore.ts:93`, `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:26` |
| `useKeymapStore` | Canvas gesture modifier only. `www/packages/canvas/src/stores/keymapStore.ts:18` | Settings command and gesture helper. `www/packages/canvas/src/keybindings/gestures.ts:43` | Persisted with validation on every load; global gesture signal subscribes and resets held state when mapping changes. `www/packages/canvas/src/stores/keymapStore.ts:41`, `www/packages/canvas/src/keybindings/gestures.ts:60` |
| Canvas gesture signal | Module state for selected modifier, held state, global document listeners, and `useSyncExternalStore` subscribers. `www/packages/canvas/src/keybindings/gestures.ts:25`, `www/packages/canvas/src/keybindings/gestures.ts:37` | Keydown, keyup, blur, and keymap changes. `www/packages/canvas/src/keybindings/gestures.ts:60`, `www/packages/canvas/src/keybindings/gestures.ts:77` | Canvas viewport subscribes; listeners install lazily once and remain for module lifetime. `www/packages/canvas/src/engine/react/useCanvasViewport.ts:53`, `www/packages/canvas/src/keybindings/gestures.ts:68` |
| Keybinding context | Refs for one launcher, one dock, and a set of fullscreen targets, plus one compiled tinykeys map. `www/packages/canvas/src/keybindings/engine.ts:31`, `www/packages/canvas/src/keybindings/engine.ts:49` | Owner hooks register and unregister targets. `www/packages/canvas/src/keybindings/engine.ts:138`, `www/packages/canvas/src/keybindings/engine.ts:152`, `www/packages/canvas/src/keybindings/engine.ts:167` | `SessionCanvasRoute` provides it around the whole workbench. Command precedence selects one eligible command per binding. `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:76`, `www/packages/canvas/src/keybindings/engine.ts:114` |

Component local state remains local for ephemeral presentation: list waiting preview, active picker row, command palette visibility, dock open state, browser address editing, section collapse, editor tabs, fullscreen, copy feedback, image zoom, and terminal status. Do not promote these to a global store unless another independent owner must coordinate them. The overlay store is the existing coordination signal for modal visibility. `www/packages/inspector/src/components/ExchangeList.tsx:148`, `www/packages/canvas/src/viewers/session-picker/SessionPickerPane.tsx:14`, `www/packages/canvas/src/interactions/overlayStore.ts:3`

### Stream invalidation rules

All four SSE consumers share `useEventSource`, which owns construction, connected state, optional manual reconnect, and teardown. With no reconnect delay the native browser reconnect remains active; with a delay the hook closes and reconstructs the source. `www/packages/core/src/useEventSource.ts:27`, `www/packages/core/src/useEventSource.ts:83`, `www/packages/core/src/useEventSource.ts:101`

* Exchange stream uses native reconnect. Valid events update query data and Inspector UI state. A second open on the same identity invalidates every exchange list as a backfill. `www/packages/inspector/src/hooks/useExchangeStream.ts:28`, `www/packages/inspector/src/hooks/useExchangeStream.ts:46`, `www/packages/inspector/src/hooks/useExchangeStream.ts:64`
* Session event stream reconnects after one second and stamps the latest sequence in the URL. A sequence gap performs HTTP backfill; identity cleanup invalidates in flight backfills. On backfill failure it still emits the arrived frame. `www/packages/canvas/src/infrastructure/stream/useSessionEventStream.ts:15`, `www/packages/canvas/src/infrastructure/stream/useSessionEventStream.ts:27`, `www/packages/canvas/src/infrastructure/stream/useSessionEventStream.ts:77`
* Workspace activity reconnects after one second. The server sends a complete snapshot on every connect, so the client has no cursor or HTTP backfill. `www/packages/canvas/src/infrastructure/stream/useWorkspaceActivityStream.ts:23`, `www/packages/canvas/src/infrastructure/stream/useWorkspaceActivityStream.ts:25`
* Browser pane stream reconnects after one second. Connecting is presenter registration; snapshot replaces observations and mirrors all browser pane refs, delta upserts, closed removes, and keepalive does nothing. `www/packages/canvas/src/browsing/useBrowserPaneStream.ts:14`, `www/packages/canvas/src/browsing/useBrowserPaneStream.ts:16`, `www/packages/canvas/src/browsing/useBrowserPaneStream.ts:68`

## Server seams

### Common transport behavior

`requestApiJson<T>` and `requestApiVoid` use an injectable process global transport. Same origin is the default; tests or hosts can install a base URL transport. JSON success bodies are TypeScript casts, not runtime validation. Non OK failures default to `Error("fallback: status")`; mutation endpoints can opt into `detailAware` parsing for FastAPI validation, Python detail envelopes, and Gateway error envelopes. `www/packages/core/src/transport.ts:35`, `www/packages/core/src/transport.ts:45`, `www/packages/core/src/transport.ts:57`, `www/packages/core/src/transport.ts:97`, `www/packages/core/src/transport.ts:150`

Every browser endpoint below is same origin. Python route composition is in `api/src/transport_matters/main.py:552`. Managed run, activity, acting context, browsing, and terminal rows make a second hop through `api/src/transport_matters/api/v1/run_proxy.py:451` to the Gateway.

### HTTP reads and mutations from `@tm/core`

| Browser call | Sent and received | Backend handler |
| --- | --- | --- |
| `GET /v1/runs/{runId}/exchanges?limit&offset` | Sends numeric pagination; receives `IndexEntry[]`. `www/packages/core/src/transport.ts:170` | Python `list_exchanges`, `api/src/transport_matters/api/v1/exchanges.py:164`. |
| `GET /v1/runs/{runId}/exchanges/{id}` | Receives `ExchangeDetail`: index entry plus original and curated request IR, audit, response IR, transport, events, turn, and diagnostics. `www/packages/core/src/transport.ts:181`, `www/packages/core/src/types/exchanges.ts:1` | Python `get_exchange`, `api/src/transport_matters/api/v1/exchanges.py:188`. |
| `GET .../{id}/turn-content` | Receives `TurnContent` for compact card summaries. `www/packages/core/src/transport.ts:188` | Python `get_turn_content`, `api/src/transport_matters/api/v1/exchanges.py:242`. |
| `GET .../{id}/pipeline_tokens` | Receives `{tokens_before, tokens_after, reason}`; null counts represent a declared degraded path. `www/packages/core/src/transport.ts:195`, `www/packages/core/src/transport.ts:223` | Python `get_pipeline_tokens`, `api/src/transport_matters/api/v1/exchanges.py:267`. |
| `GET /api/meta` or `GET /v1/runs/{runId}/meta` | Receives snake case meta and converts to camel case `Meta`, including branded Space, Worktree, and Canvas IDs. `www/packages/core/src/transport.ts:247`, `www/packages/core/src/transport.ts:280` | Python `get_meta` and `get_run_meta`, `api/src/transport_matters/api/v1/meta.py:112`, `api/src/transport_matters/api/v1/meta.py:137`. |
| `GET /api/capabilities` | Receives managed harness availability. `www/packages/core/src/transport.ts:317` | Python `get_capabilities`, `api/src/transport_matters/api/v1/capabilities.py:43`. |
| `GET /v1/harnesses` | Receives stored harness installation, enablement, compatibility, target, and connection evidence. `www/packages/core/src/transport.ts:326` | Python `get_harnesses`, `api/src/transport_matters/api/v1/harnesses.py:82`. |
| `GET /v1/launch-readiness` | Receives infrastructure readiness and harness scoped checks. `www/packages/core/src/transport.ts:339` | Python `get_launch_readiness`, `api/src/transport_matters/api/v1/launch_readiness.py:11`. |
| `POST /v1/runs` | Sends harness; verified `spaceId`, `anchorWorktreeId`, `canvasId`; target `worktreeId`; optional agent, name, model, effort, continuation, and idempotency key; explicit bypass and control plane grant. Receives `{run: RunView}`. `www/packages/core/src/transport.ts:359`, `www/packages/core/src/transport.ts:400`, `www/packages/core/src/transport.ts:405` | Python origin and mutation check at `api/src/transport_matters/api/v1/run_proxy.py:464`; Gateway validates and creates in `packages/runtime/src/server/runtimeRouter.ts:68`. |
| `GET /v1/agents` | Receives `{items: RuntimeTemplateSummary[]}` and exposes the array. `www/packages/core/src/transport.ts:442` | Python direct `get_agents`, `api/src/transport_matters/api/v1/runtime_template_routes.py:21`. |
| `POST /v1/runs/{runId}/terminate` | No body, no browser response body. `www/packages/core/src/transport.ts:459` | Python mutation forward `api/src/transport_matters/api/v1/run_proxy.py:480`; Gateway terminates and returns `{run}` at `packages/runtime/src/server/runtimeRouter.ts:240`. |
| `GET /v1/runs?state&spaceId&worktreeId` | Optional camel case filters; receives `{items: RunView[], nextCursor}` and exposes items. `www/packages/core/src/transport.ts:498`, `www/packages/core/src/transport.ts:514` | Python forward `api/src/transport_matters/api/v1/run_proxy.py:469`; Gateway list `packages/runtime/src/server/runtimeRouter.ts:191`. |
| `GET /v1/runs/{runId}` | Receives `{run: RunView}`; maps 404 to `null`; supports AbortSignal. `www/packages/core/src/transport.ts:529` | Python forward `api/src/transport_matters/api/v1/run_proxy.py:473`; Gateway lookup `packages/runtime/src/server/runtimeRouter.ts:219`. |
| `GET /v1/workspaces/{workspaceId}/activity?owner` | Receives `ActivityWorkspaceResponse`. Workspace ID is path encoded and owner defaults to `local`. `www/packages/core/src/transport.ts:546` | Python forward `api/src/transport_matters/api/v1/run_proxy.py:494`; Gateway activity snapshot `packages/activity/src/server/activityRouter.ts:103`. |

### Inspector HTTP surface

The Inspector endpoint client is one file, `www/packages/inspector/src/api.ts`. Override scope is `{run_id, track_id}` in query parameters. `www/packages/inspector/src/api.ts:27`

| Browser call | Sent and received | Backend handler |
| --- | --- | --- |
| `GET /api/overrides` | Receives `{overrides, enabled}` for the optional run and track scope. `www/packages/inspector/src/api.ts:35` | Python `get_overrides`, `api/src/transport_matters/api/v1/overrides.py:128`. |
| `PATCH /api/overrides` | Sends `{overrides: Override[]}`; receives authoritative overrides, enabled, optional audit, and optional curated IR. `www/packages/inspector/src/api.ts:42` | Python transaction upserts, recomputes paused preview, synchronizes shared proxy state, and rolls back all local changes on error. `api/src/transport_matters/api/v1/overrides.py:141` |
| `DELETE /api/overrides` | Clears global or scoped overrides, no body. `www/packages/inspector/src/api.ts:57` | Python `delete_overrides`, including shared proxy sync and rollback, `api/src/transport_matters/api/v1/overrides.py:176`. |
| `POST /api/overrides/toggle` | No body; receives `{enabled, audit, curated_ir}`. `www/packages/inspector/src/api.ts:63` | Python `toggle_overrides`, `api/src/transport_matters/api/v1/overrides.py:202`. |
| `GET /api/breakpoint/status` | Receives mode and paused flow summaries. `www/packages/inspector/src/api.ts:75` | Python `get_status`, `api/src/transport_matters/api/v1/breakpoint_routes.py:123`. |
| `POST /api/breakpoint/arm` | No body; response ignored. `www/packages/inspector/src/api.ts:82` | Python `arm_breakpoint`, `api/src/transport_matters/api/v1/breakpoint_routes.py:169`. |
| `POST /api/breakpoint/disarm` | No body; response ignored. `www/packages/inspector/src/api.ts:86` | Python `disarm_breakpoint`, `api/src/transport_matters/api/v1/breakpoint_routes.py:175`. |
| `POST /api/breakpoint/release/{flowId}` | Sends the full edited `InternalRequest`; response ignored. `www/packages/inspector/src/api.ts:90` | Python validates provider stability, serializes with the provider adapter, and releases the waiter. `api/src/transport_matters/api/v1/breakpoint_routes.py:181`, `api/src/transport_matters/api/v1/breakpoint_routes.py:256`. |
| `POST /api/breakpoint/release-unmodified/{flowId}` | No body; response ignored. `www/packages/inspector/src/api.ts:103` | Python releases with original bytes path. `api/src/transport_matters/api/v1/breakpoint_routes.py:198`. |
| `POST /api/breakpoint/drop/{flowId}` | No body; response ignored. `www/packages/inspector/src/api.ts:114` | Python marks dropped and wakes waiter. `api/src/transport_matters/api/v1/breakpoint_routes.py:248`, `api/src/transport_matters/breakpoint.py:159`. |
| `POST /api/breakpoint/re-audit/{flowId}` | No body; receives `{audit, curated_ir, tokens_before}`. `www/packages/inspector/src/api.ts:125` | Python reapplies current scoped override state to original IR and recounts tokens. `api/src/transport_matters/api/v1/breakpoint_routes.py:215`. |
| `GET /api/breakpoint/paused/{flowId}` | Receives one complete `PausedFlow`. `www/packages/inspector/src/api.ts:142` | Python `get_paused_flow`, `api/src/transport_matters/api/v1/breakpoint_routes.py:134`. |

### Canvas session, resource, first run, and Space HTTP surface

| Browser call | Sent and received | Backend handler |
| --- | --- | --- |
| `GET /v1/sessions?owner&limit&workspaceId&purpose&visibility&includeInternal&cursor` | Receives camel case `{items: SessionSummary[], nextCursor}`. `harness` is a client side filter applied after the returned page. `www/packages/canvas/src/infrastructure/api/sessionClient.ts:36`, `www/packages/canvas/src/infrastructure/api/sessionClient.ts:54`, `www/packages/canvas/src/infrastructure/api/sessionClient.ts:63` | Python `list_sessions`, `api/src/transport_matters/api/v1/session_routes.py:108`; Pydantic aliases to camel case in `api/src/transport_matters/api/v1/session_models.py:31`. |
| `GET /v1/sessions/{sessionId}/events?owner&limit&from_seq&to_seq` | Receives `{events: SessionEventView[], nextFromSeq}`. `www/packages/canvas/src/infrastructure/api/sessionEvents.ts:21`, `www/packages/canvas/src/infrastructure/api/sessionEvents.ts:47` | Python `list_session_events`, `api/src/transport_matters/api/v1/session_routes.py:169`; response model at `api/src/transport_matters/api/v1/session_models.py:131`. |
| `GET /v1/sessions/{sessionId}/resources/{resourceId}?owner&range_start&range_end&include_debug` | Receives the discriminated camel case resource union: text, image, binary, JSON, exchange redirect, or missing. `www/packages/canvas/src/infrastructure/api/resourceContent.ts:10`, `www/packages/canvas/src/infrastructure/api/resourceContent.ts:91`, `www/packages/canvas/src/infrastructure/api/resourceContent.ts:128` | Python `get_session_resource`, `api/src/transport_matters/api/v1/session_routes.py:238`; canonical response union in `api/src/transport_matters/session/resource_content_models.py:31`. |
| `GET /api/local-file?path` | Receives the same resource union for an absolute local path. `www/packages/canvas/src/infrastructure/api/resourceContent.ts:117` | Python `local_file_content`, `api/src/transport_matters/api/v1/local_file_routes.py:33`. Image and binary response URLs can subsequently make the browser request `/api/local-file/raw?path`, served by `local_file_raw`. `api/src/transport_matters/api/v1/local_file_routes.py:40` |
| `POST /v1/harnesses/refresh` | No body; receives `{refreshed: boolean}`. `www/packages/canvas/src/firstrun/FirstRunScreen.tsx:282` | Python `refresh_harnesses`, `api/src/transport_matters/api/v1/harnesses.py:87`. |
| `PUT /v1/harnesses/{id}/enablement` | Sends `{enabled}`; response body is unused, then readiness and inventory are refreshed. `www/packages/canvas/src/firstrun/FirstRunScreen.tsx:325` | Python `set_harness_enablement`, `api/src/transport_matters/api/v1/harness_enablement.py:62`. |
| `GET /v1/spaces?limit&cursor` | Receives `SpaceListResponse` with items, cursor, and switcher flag. `www/packages/space-client/src/spaceTransport.ts:16`, `www/packages/space-client/src/spaceTransport.ts:21` | Python `list_spaces`, `api/src/transport_matters/api/v1/space_routes.py:230`. |
| `POST /v1/spaces` | Sends `{name}`; receives `SpaceSummary`. `www/packages/space-client/src/spaceTransport.ts:31` | Python `create_space`, `api/src/transport_matters/api/v1/space_routes.py:260`. |
| `PATCH /v1/spaces/{spaceId}` | Sends `{name}`; receives `SpaceSummary`. `www/packages/space-client/src/spaceTransport.ts:44` | Python `rename_space`, `api/src/transport_matters/api/v1/space_routes.py:334`. |
| `DELETE /v1/spaces/{spaceId}` | No body or response body. `www/packages/space-client/src/spaceTransport.ts:57` | Python `delete_space`, `api/src/transport_matters/api/v1/space_routes.py:352`. |
| `POST /v1/spaces/{spaceId}/worktrees` | Sends `{path}`; receives `{worktree: WorktreeSummary}`. UI language calls this a Workdir while wire and domain type use Worktree. `www/packages/space-client/src/spaceTransport.ts:66` | Python `create_workdir`, `api/src/transport_matters/api/v1/space_routes.py:309`. |
| `GET /v1/spaces/{spaceId}/canvases` | Receives `{items?: CanvasSummary[]}` and maps missing items to `[]`. `www/packages/space-client/src/spaceTransport.ts:80` | Python `list_space_canvases`, `api/src/transport_matters/api/v1/space_routes.py:449`. |
| `POST /v1/spaces/acting-context/verify` | Sends `{candidate:{spaceId,worktreeId,canvasId}, ownerId}`; receives `{receipt, spawnWorktreeId}` or a typed failure code. `www/packages/space-client/src/spaceTransport.ts:88`, `www/packages/space-client/src/spaceTransport.ts:117` | Python origin and mutation forward `api/src/transport_matters/api/v1/run_proxy.py:517`; Gateway validates and verifies in `packages/space/src/server/spaceRouter.ts:31`. |
| `POST /v1/spaces/acting-context/resolve-workdir` | Sends `{cwd, ownerId, spaceId}`; receives the same result union. `www/packages/space-client/src/spaceTransport.ts:99` | Python forward `api/src/transport_matters/api/v1/run_proxy.py:524`; Gateway boundary resolution and context lookup `packages/space/src/server/spaceRouter.ts:40`. |

### Canvas browsing HTTP surface

All browsing calls normalize contract snake case into Canvas domain refs at `browserPaneClient.ts`; no wire shape should escape that module. Python checks Origin on mutations and forwards to the Gateway Browsing context. `www/packages/canvas/src/browsing/browserPaneClient.ts:17`, `api/src/transport_matters/api/v1/browsing_proxy.py:20`

| Browser call | Sent and received | Backend handler |
| --- | --- | --- |
| `POST /v1/canvases/{canvasId}/browser-panes` | Sends `{url,title,origin?}`; receives `BrowserPaneWire`, returns `BrowserPaneRef`. `www/packages/canvas/src/browsing/browserPaneClient.ts:57` | Python `open_browser_pane`, `api/src/transport_matters/api/v1/browsing_proxy.py:37`; Gateway open `packages/browsing/src/server/browsingRouter.ts:86`. |
| `POST /v1/browser-panes/{id}/navigate` | Sends `{url}`; receives and maps one pane. `www/packages/canvas/src/browsing/browserPaneClient.ts:77` | Python `navigate_browser_pane`, `api/src/transport_matters/api/v1/browsing_proxy.py:54`; Gateway navigate `packages/browsing/src/server/browsingRouter.ts:128`. |
| `POST /v1/browser-panes/{id}/history` | Sends `{delta:-1|1}`; receives and maps one pane. `www/packages/canvas/src/browsing/browserPaneClient.ts:90` | Python `step_browser_pane_history`, `api/src/transport_matters/api/v1/browsing_proxy.py:64`; Gateway history `packages/browsing/src/server/browsingRouter.ts:147`. |
| `POST /v1/browser-panes/{id}/reload` | No body; receives and maps one pane. `www/packages/canvas/src/browsing/browserPaneClient.ts:104` | Python `reload_browser_pane`, `api/src/transport_matters/api/v1/browsing_proxy.py:74`; Gateway reload `packages/browsing/src/server/browsingRouter.ts:139`. |
| `POST /v1/browser-panes/close` | Sends `{browser_pane_ids:[id]}`; browser ignores response. `www/packages/canvas/src/browsing/browserPaneClient.ts:114` | Python `close_browser_panes`, `api/src/transport_matters/api/v1/browsing_proxy.py:94`; Gateway returns `{closed,unknown}` at `packages/browsing/src/server/browsingRouter.ts:178`. |
| `POST /v1/browser-panes/{id}/observation` | Sends complete `BrowserPaneObservationWire`: presenter, navigation sequence, observed URL, title, target, load status, failure, history booleans, timestamp. `www/packages/canvas/src/browsing/browserPaneClient.ts:125`, `packages/contract/src/browsing/index.ts:159` | Python `observe_browser_pane`, `api/src/transport_matters/api/v1/browsing_proxy.py:84`; Gateway observation `packages/browsing/src/server/browsingRouter.ts:161`. |
| `GET /v1/browser-history` | Receives `{entries}` and maps each to domain camel case. `www/packages/canvas/src/browsing/browserPaneClient.ts:138` | Python `list_browser_history`, `api/src/transport_matters/api/v1/browsing_proxy.py:104`; Gateway history list `packages/browsing/src/server/browsingRouter.ts:194`. |
| `DELETE /v1/browser-history/{entryId}` | Receives the remaining `{entries}` and redraws from it. `www/packages/canvas/src/browsing/browserPaneClient.ts:151` | Python `remove_browser_history_entry`, `api/src/transport_matters/api/v1/browsing_proxy.py:108`; Gateway remove and list `packages/browsing/src/server/browsingRouter.ts:196`. |

The Gateway also exposes browser pane list, individual delete, and canvas presentation reads, but current `www/` production code does not call them. The stream snapshot is the Canvas list source. `packages/browsing/src/server/browsingRouter.ts:76`, `www/packages/canvas/src/browsing/browserPaneClient.ts:17`

### SSE seams

| Stream | Client URL and frame handling | Backend chain |
| --- | --- | --- |
| Run exchanges | `/v1/runs/{runId}/stream`. Frames include connected, paused, paused tokens, exchange, and deletion data. Parser validates the fields it uses, updates query caches, and coordinates forwarding state. `www/packages/inspector/src/hooks/useExchangeStream.ts:46`, `www/packages/core/src/exchangeStreamEvents.ts:29` | Python `stream_run`, `api/src/transport_matters/api/v1/stream.py:21`. |
| Session events | `/v1/sessions/{sessionId}/events/stream?owner&last_seq`. Each data frame is a `SessionEventView`. `www/packages/canvas/src/infrastructure/api/sessionEvents.ts:66`, `www/packages/canvas/src/infrastructure/stream/useSessionEventStream.ts:49` | Python `stream_session_events`, `api/src/transport_matters/api/v1/session_routes.py:278`. |
| Workspace activity | `/v1/workspaces/{workspaceId}/activity/stream?owner`. Frames are snapshot or delta activity contract values. `www/packages/core/src/transport.ts:562`, `www/packages/canvas/src/infrastructure/stream/useWorkspaceActivityStream.ts:42` | Python SSE forward `api/src/transport_matters/api/v1/run_proxy.py:501`; Gateway subscribes, sends snapshot, then deltas and keepalives at `packages/activity/src/server/activityRouter.ts:124`. |
| Browser panes | `/v1/canvases/{canvasId}/browser-panes/stream?capability&devtools_url|devtools_reason`. Connection query registers a presenter. Frames are complete validated snapshot, delta, closed, or keepalive. `www/packages/canvas/src/browsing/browserPaneClient.ts:44`, `www/packages/canvas/src/browsing/useBrowserPaneStream.ts:16`, `packages/contract/src/browsing/index.ts:184` | Python SSE forward `api/src/transport_matters/api/v1/browsing_proxy.py:43`; Gateway presenter lifecycle and SSE `packages/browsing/src/server/browsingRouter.ts:98`. |

### WebSocket seams

| Socket | Protocol | Backend chain |
| --- | --- | --- |
| `ws(s)://host/api/terminal?cols&rows` | Local terminal. Browser sends binary UTF 8 PTY input and JSON text resize `{type:"resize",cols,rows}`; server binary frames are written to xterm. `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts:1`, `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts:64`, `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts:127` | Python bridge `api/src/transport_matters/api/v1/run_proxy.py:535`; Gateway `/terminal` WebSocket at `packages/runtime/src/server/runtimeRouter.ts:277`. |
| `ws(s)://host/v1/runs/{runId}/terminal?cols&rows` | Managed run attachment. Same PTY frames, plus JSON text control frames such as ready, error, and truncation; text control never reaches xterm. Closing detaches and leaves the run alive. `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts:72`, `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts:127`, `www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx:131` | Python bridge `api/src/transport_matters/api/v1/run_proxy.py:488`; Gateway managed terminal WebSocket `packages/runtime/src/server/runtimeRouter.ts:289`. |

Typed terminal helpers queue keystrokes before open, drop writes after close, flush in order, detach event handlers before deliberate shutdown, and expose close status to the viewer. Preserve those edge behaviors when changing the socket. `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts:97`, `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts:102`, `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts:144`

## End to end data traces

### A. Session roster fetch to painted row

1. The session picker asks for `owner: "local"`, current `workspaceHash`, and limit 50. It owns loading, error plus retry, empty plus refresh, keyboard active row, open, and continue gestures. `www/packages/canvas/src/viewers/session-picker/SessionPickerPane.tsx:7`, `www/packages/canvas/src/viewers/session-picker/SessionPickerPane.tsx:27`
2. `useSessions` creates a canonical `sessionsKey(filters)` and calls `listSessions`. `www/packages/canvas/src/hooks/useSessions.ts:5`
3. `listSessions` builds `/v1/sessions?owner=local&limit=50&workspaceId=...`, casts `SessionListResponse`, then optionally filters harness client side. `www/packages/canvas/src/infrastructure/api/sessionClient.ts:52`, `www/packages/canvas/src/infrastructure/api/sessionClient.ts:54`, `www/packages/canvas/src/infrastructure/api/sessionClient.ts:63`
4. FastAPI `list_sessions` queries the owner scoped session store and serializes `ListSessionsResponse`. Its base model converts Python snake case fields to camel case, matching `SessionSummary`. `api/src/transport_matters/api/v1/session_routes.py:108`, `api/src/transport_matters/api/v1/session_models.py:31`, `api/src/transport_matters/api/v1/session_models.py:56`
5. Query data becomes `sessions`; the component maps every item to an absolute BEM row and uses `sessionId` as key. A click dispatches `spawnOrFocusTranscript(session)` through viewer actions. `www/packages/canvas/src/viewers/session-picker/SessionPickerPane.tsx:33`, `www/packages/canvas/src/viewers/session-picker/SessionPickerPane.tsx:51`
6. `SessionRow` paints title, live badge, provider, harness, status, relative last activity, workspace ID, and optional last message preview. `www/packages/canvas/src/viewers/session-picker/SessionPickerPane.tsx:93`

In this frontend, “roster” means this session picker plus the captured run and activity surfaces. There is no component named `Roster`; the viewer registry routes roster style discovery through `SessionPickerPane`. `www/packages/canvas/src/viewers/registry.tsx:64`, `www/packages/canvas/src/viewers/session-picker/SessionPickerPane.tsx:7`

### B. Open one captured exchange through rendered request JSON

1. `BrowserAppShell` resolves current `runId` from meta, calls `useExchanges(runId, true, pendingTrackStubs)`, and hands entries plus `setSelectedId` to `RouteLayout`. `www/packages/inspector/src/app.tsx:45`, `www/packages/inspector/src/app.tsx:47`, `www/packages/inspector/src/app.tsx:92`
2. `fetchExchanges` sends `GET /v1/runs/{runId}/exchanges?limit&offset`; Python `list_exchanges` returns run scoped index entries. `www/packages/core/src/transport.ts:170`, `api/src/transport_matters/api/v1/exchanges.py:164`
3. `ExchangeList` projects the track tree, virtualizes fixed row estimates with overscan 30, and paints only current `ExchangeTurnCard` rows. `www/packages/inspector/src/components/ExchangeList.tsx:152`, `www/packages/inspector/src/components/ExchangeList.tsx:158`, `www/packages/inspector/src/components/ExchangeList.tsx:192`
4. Clicking a painted card calls `onSelect(entry.id)`, which is the UI store's `setSelectedId`. `www/packages/inspector/src/components/ExchangeTurnCard.tsx:255`, `www/packages/inspector/src/app.tsx:103`
5. With no paused flow and a visible selection, `InterceptRoute` renders `ExchangeDetail(id, metaRunId)`. `www/packages/inspector/src/routeLayout.tsx:182`
6. `ExchangeDetail` queries `exchangeKey(runId,id)`, calls `fetchExchange`, and disables retry. `www/packages/inspector/src/components/ExchangeDetail.tsx:224`
7. `fetchExchange` calls `GET /v1/runs/{runId}/exchanges/{id}`. Python `get_exchange` assembles the detail artifact. `www/packages/core/src/transport.ts:181`, `api/src/transport_matters/api/v1/exchanges.py:188`
8. The user clicks Request in the detail tab bank, which writes local `tab`. The Request branch passes curated request IR when available and falls back to original request IR. `www/packages/inspector/src/components/ExchangeDetail.tsx:356`, `www/packages/inspector/src/components/ExchangeDetail.tsx:450`
9. `JsonView` performs `JSON.stringify(payload, null, 2)`, memoizes line splitting, virtualizes 23 pixel lines with overscan 30, and paints syntax colored visible lines. `www/packages/inspector/src/components/detail/JsonView.tsx:34`, `www/packages/inspector/src/components/detail/JsonView.tsx:39`, `www/packages/inspector/src/components/detail/JsonView.tsx:57`

The Request branch is in the post tab render immediately after the tab bank; verify the exact conditional before changing tabs because Inspect and Transport use richer renderers while Request and Response use `JsonView`. `www/packages/inspector/src/components/ExchangeDetail.tsx:446`, `www/packages/inspector/src/components/ExchangeDetail.tsx:450`

### C. Override edit gesture through sent provider request

This trace uses a system prompt text edit. Tool, message, sampling, tool result, and provider extras editors converge on the same `handleUpsert` endpoint path with different `Override.kind` and target encodings.

1. `SystemPartRow` derives the stable positional target `system:{index}` and configures `useEditableOverride` with `system_part_toggle` and `system_part_text`. The `TextOverrideEditor` sends keystrokes to local state and commits on blur. `www/packages/inspector/src/components/editor/SystemSection.tsx:43`, `www/packages/inspector/src/components/editor/SystemSection.tsx:53`, `www/packages/inspector/src/components/editor/SystemSection.tsx:86`
2. `commitText` emits `{kind:"system_part_text",target,value}` or a null value to remove the override when text equals original. `www/packages/inspector/src/hooks/useEditableOverride.ts:52`
3. `BreakpointEditorPanes` receives `handleUpsert` as `onOverride`; `useBreakpointEditorActions` scopes it by paused `run_id` and `track_id`, then awaits `useOverrides.upsert`. The response replaces local audit and curated IR. `www/packages/inspector/src/components/editor/BreakpointEditor.tsx:113`, `www/packages/inspector/src/components/editor/BreakpointEditorActions.ts:69`, `www/packages/inspector/src/components/editor/BreakpointEditorActions.ts:110`
4. `useOverrides` mutation calls `patchOverrides`; success replaces the scoped query cache. `www/packages/inspector/src/hooks/useOverrides.ts:36`
5. `patchOverrides` sends `PATCH /api/overrides?run_id=...&track_id=...` with JSON `{overrides:[...]}`. `www/packages/inspector/src/api.ts:42`
6. Python treats the batch as a transaction: snapshot scope, upsert every member, recompute paused preview from original IR, synchronize the shared proxy manager for captured runs, and restore the snapshot on any failure. It returns authoritative overrides, enabled, audit, and curated IR. `api/src/transport_matters/api/v1/overrides.py:141`
7. The Forward button invokes `handleForward`. `EditorActions` has separate Drop, Pass Through, and Forward gestures. `www/packages/inspector/src/components/editor/EditorActions.tsx:65`, `www/packages/inspector/src/components/editor/EditorActions.tsx:84`
8. `handleForward` posts the current full `editedIr`, invalidates provisional exchange detail, then either waits for HTTP SSE completion or resolves a WebSocket provisional exchange immediately. `www/packages/inspector/src/components/editor/BreakpointEditorActions.ts:142`, `www/packages/inspector/src/components/editor/BreakpointEditorActions.ts:146`, `www/packages/inspector/src/components/editor/BreakpointEditorActions.ts:158`
9. `releaseFlow` sends the full edited `InternalRequest` to `POST /api/breakpoint/release/{flowId}`. `www/packages/inspector/src/api.ts:90`
10. Python rejects a provider change, serializes with the provider adapter before waking the flow, stores both mutated IR and exact release bytes, then signals the paused request. `api/src/transport_matters/api/v1/breakpoint_routes.py:181`, `api/src/transport_matters/api/v1/breakpoint_routes.py:256`, `api/src/transport_matters/breakpoint.py:144`
11. For HTTP, pause release replaces the mitmproxy request body with those bytes and updates recorded flow state. For Codex WebSocket, it replaces `message.content`, updates state, and rewrites the provisional exchange. `api/src/transport_matters/pause_session.py:350`, `api/src/transport_matters/pause_session.py:373`, `api/src/transport_matters/pause_session.py:400`, `api/src/transport_matters/pause_session.py:426`

Pass Through follows a distinct endpoint because preserving original transport bytes is meaningful. Do not implement it as “Forward original IR”; the backend's unmodified release carries no reserialized payload. `www/packages/inspector/src/api.ts:103`, `api/src/transport_matters/api/v1/breakpoint_routes.py:198`

## Types and drift detection

### Where types live

* `www/packages/core/src/types/ir.ts`, `exchanges.ts`, `overrides.ts`, `capabilities.ts`, `harnessInventory.ts`, `launchReadiness.ts`, `runtimeTemplates.ts`, and `transport.ts` are hand written browser contracts. They are exported through `@tm/core/types/*`. `www/packages/core/package.json:6`
* Session and resource DTOs are hand written beside their Canvas clients in `www/packages/canvas/src/infrastructure/api/sessionClient.ts:3`, `www/packages/canvas/src/infrastructure/api/sessionEvents.ts:3`, and `www/packages/canvas/src/infrastructure/api/resourceContent.ts:3`.
* Cross TypeScript process contracts are hand written in `packages/contract` and exposed only by bounded subpaths for activity, browsing, desktop, runtime, and Space. `packages/contract/package.json:6`
* Space IDs are branded string types; the Space wire module owns identity DTOs and UUID validators. `packages/contract/src/space/wire.ts:4`, `packages/contract/src/space/wire.ts:23`, `packages/contract/src/space/wire.ts:45`
* Browser pane DTOs deliberately remain snake case at the contract boundary. `browserPaneClient` maps them into Canvas refs. Its SSE parser validates every field before admitting a frame. `packages/contract/src/browsing/index.ts:1`, `packages/contract/src/browsing/index.ts:105`, `packages/contract/src/browsing/index.ts:190`
* Python session and resource Pydantic models are backend authorities. Their alias generators serialize session and resource fields to camel case. `api/src/transport_matters/api/v1/session_models.py:31`, `api/src/transport_matters/session/timeline_models.py:38`, `api/src/transport_matters/session/resource_content_models.py:31`

There is no general OpenAPI to TypeScript generator in this frontend. Most HTTP response checks are compile time mirrors plus tests; `requestApiJson<T>` casts successful JSON. Runtime parsing is selective at live stream and identity boundaries. `www/packages/core/src/transport.ts:150`

### How drift is caught

| Contract | Guard |
| --- | --- |
| Python IR and overrides against TypeScript | `api/src/transport_matters/test_type_mirrors.py` parses both languages and compares override literals, model field sets, optionality, normalized types, and content block union. `api/src/transport_matters/test_type_mirrors.py:18`, `api/src/transport_matters/test_type_mirrors.py:67`, `api/src/transport_matters/test_type_mirrors.py:152` |
| Harness descriptor and inventory vocabularies | TypeScript exact union assertions plus deep equality against shared JSON fixtures; Python tests bind the same fixture. `www/packages/core/src/types/harnessDescriptors.test.ts:99`, `www/packages/core/src/types/harnessInventory.test.ts:23`, `www/packages/core/src/types/harnessInventory.test.ts:91` |
| Acting context and Space semantics | Shared snake case parity fixture corpus, branded type assertions, failure code coverage, UUID grammar, and precedence tests. `packages/contract/src/space/fixtures.ts:1`, `packages/contract/src/space/space.test.ts:80`, `packages/contract/src/space/space.test.ts:99`, `packages/contract/src/space/space.test.ts:152` |
| Browser stream | `parseBrowserPaneStreamFrame` rejects malformed or incomplete snapshot, delta, closed, and keepalive frames. `packages/contract/src/browsing/index.ts:190`, `packages/contract/src/browsing/index.ts:226` |
| Exchange stream | Field guards admit paused, paused token, exchange, and delete events before cache writes. `www/packages/core/src/exchangeStreamEvents.ts:29`, `www/packages/core/src/exchangeStreamEvents.ts:69`, `www/packages/core/src/exchangeStreamEvents.ts:134` |
| TypeScript exhaustiveness | Base config enables strict mode, unchecked indexed access, implicit override and return checks, switch fallthrough checks, and casing checks. `tsconfig.base.json:2` |

Runtime validation is uneven by design history. Session SSE only proves parsed JSON has numeric `seq`; activity parsing validates envelope identity more lightly than browser panes; ordinary HTTP bodies are casts. Treat any new external field as untrusted at its client boundary and prefer a focused parser or parity fixture when the field drives branching. `www/packages/canvas/src/infrastructure/stream/useSessionEventStream.ts:111`, `www/packages/core/src/transport.ts:150`

## Conventions a newcomer is likely to violate

1. Keep Inspector and Canvas independent. Never import one from the other, even to reuse a component that looks identical. The architecture test requires zero edges both ways and rejects deep package imports. `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:47`, `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:77`
2. Use the package export map. Browser code may use `@tm/contract/*`, `@tm/core`, `@tm/space-client`, and the declared product leaves. It may not reach into `src/` or import Gateway context implementations. `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:118`, `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:161`
3. Inspector uses Tailwind utilities and `inspector.css` tokens. Canvas uses vanilla product prefixed BEM and colocated CSS. Stray Canvas utility classes can appear correct under the composed shell and fail in its standalone bundle. `www/packages/inspector/src/inspector.css:1`, `www/packages/shell/src/testSupport/canvasTailwindFree.test.ts:1`
4. Keep the token split. Canvas theme tokens and Inspector Tailwind tokens are intentionally duplicated so each production bundle stands alone. `www/packages/canvas/src/styles/tokens.css:1`, `www/packages/inspector/CLAUDE.md:27`
5. Add storage keys only to the owning registry. Both products share one origin; a shell test enforces no collision and the `transport-matters` namespace. `www/packages/canvas/src/infrastructure/persistence/storageKeys.ts:1`, `www/packages/inspector/src/stores/persistence.ts:1`, `www/packages/shell/src/testSupport/storageKeys.test.ts:1`
6. Query keys must include every scope coordinate. Use `queryKeys.ts` for shared entities and feature key helpers for local ones. Do not write a broad string key that can alias another run, session, track, or resource. `www/packages/core/src/queryKeys.ts:7`, `www/packages/core/src/queryKeys.ts:25`, `www/packages/inspector/src/hooks/useOverrides.ts:22`
7. External data is snake case only where the wire contract says so. Session and resource APIs serialize camel case; browsing contracts remain snake case and map at `browserPaneClient`. `api/src/transport_matters/api/v1/session_models.py:31`, `www/packages/canvas/src/browsing/browserPaneClient.ts:17`
8. Preserve explicit loading, empty, error, and retry states. Pane registry has a shared chrome state shell, but data viewers also distinguish fetch states in their own domain language. `www/packages/canvas/src/viewers/registry.tsx:194`, `www/packages/canvas/src/viewers/session-picker/SessionPickerPane.tsx:27`, `www/packages/inspector/src/components/ExchangeDetail.tsx:246`
9. Treat Canvas identity as an owner, not a bag of URL fields. Use exported selectors and `dispatchCanvasIdentity`; only `canvasIdentityOwner.ts` may rewrite the URL or switch dynamic persistence. `www/packages/canvas/src/model/canvasIdentityOwner.ts:122`, `www/packages/canvas/src/model/canvasIdentityOwner.ts:177`, `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:56`
10. Add pane behavior through the domain model, viewer registry, actions, lifecycle, and persistence projection. Avoid another parallel renderer switch. `www/packages/canvas/src/viewers/registry.tsx:56`, `www/packages/canvas/src/model/canvasStore.persistence.ts:25`
11. Browser pane existence and desired navigation are server facts. The browser observation store is a nonpersistent mirror; stream snapshots win. `www/packages/canvas/src/browsing/browserPaneStore.ts:8`, `www/packages/canvas/src/browsing/useBrowserPaneStream.ts:68`
12. Captured terminal socket close means detach. Pane close separately calls managed run termination; preserve that lifecycle distinction. `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts:72`, `www/packages/canvas/src/model/capturedRunStore.ts:270`
13. Keep terminal JSON control frames out of xterm. Binary is PTY output; string frames go only to `onTextFrame`. `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts:127`
14. Inspector fullscreen uses a plain window Escape listener because it has no keybinding provider. Canvas fullscreen must register with its keybinding engine so Escape precedence among launcher, dock, and fullscreen stays coherent. `www/packages/inspector/CLAUDE.md:33`, `www/packages/canvas/src/keybindings/engine.ts:135`
15. Tests are colocated next to units. The shell Vitest config aggregates browser packages into separate jsdom and node projects; pure `.test.ts` avoids jsdom unless listed as DOM dependent. Product plane Node packages run in separate jobs. `www/packages/shell/vite.config.ts:90`, `www/packages/shell/vite.config.ts:101`
16. Playwright owns browser E2E, visual, production matrix, and performance paths under `www/packages/shell/tests`. Read the nearest suite before changing route boot, bundle separation, native browser presentation, or pane motion. `www/packages/shell/playwright.config.ts:22`, `www/packages/shell/playwright.config.ts:44`
17. Run the narrow colocated test, package typecheck, then `just www test` or the relevant Playwright suite. For contract or API seam changes, include the Python parity or handler test and the owning product plane package test. The repository gate checks all frontend packages separately. `justfile:96`, `justfile:107`

## Performance sensitive paths

* Exchange list uses fixed virtual row estimates and overscan 30. Changing row height without changing `TRACK_ROW_HEIGHT` or `EXCHANGE_ROW_HEIGHT` breaks placement. Track projection and collapsed set are memoized. `www/packages/inspector/src/components/ExchangeList.tsx:21`, `www/packages/inspector/src/components/ExchangeList.tsx:152`, `www/packages/inspector/src/components/ExchangeList.tsx:158`
* Request and response JSON split once, then virtualize 23 pixel lines with overscan 30. Keep line height synchronized with font and leading. `www/packages/inspector/src/components/detail/JsonView.tsx:10`, `www/packages/inspector/src/components/detail/JsonView.tsx:34`, `www/packages/inspector/src/components/detail/JsonView.tsx:39`
* Exchange list cache is intentionally capped at 500 entries during stream reduction. `www/packages/core/src/transport.ts:22`, `www/packages/core/src/exchangeStreamEvents.ts:259`
* Inspector text diff is not computed while Edit is active. Myers line diff runs only after the user opens Diff. `www/packages/inspector/src/components/editor/TextOverrideEditor.tsx:149`
* Product routes are lazy. Canvas also lazy loads xterm backed viewers into a shared chunk. `www/packages/shell/src/rootShell.tsx:9`, `www/packages/canvas/src/app.tsx:7`, `www/packages/canvas/src/viewers/registry.tsx:26`
* `LayoutCanvas` isolates a memoized `PaneLayer`; pan and zoom update viewport without rerendering pane contents when node and callback references stay stable. Callers must keep `renderPane` and action callbacks stable. `www/packages/canvas/src/engine/react/LayoutCanvas.tsx:57`, `www/packages/canvas/src/engine/react/LayoutCanvas.tsx:131`
* Size FLIP is suppressed while zoomed because measuring and inverting every pane under scale is expensive. Bulk organize snaps under zoom. `www/packages/canvas/src/engine/react/LayoutCanvas.tsx:137`
* `CanvasWorkbench` memoizes sortable IDs and keeps dimensions under one `ResizeObserver`; avoid deriving new pane arrays on every viewport tick. `www/packages/canvas/src/workbench/CanvasWorkbench.tsx:79`, `www/packages/canvas/src/workbench/CanvasWorkbench.tsx:95`, `www/packages/canvas/src/workbench/CanvasWorkbench.tsx:103`
* Native browser presentation runs requestAnimationFrame only during a settling window or active gesture, subscribes directly to three stores, suppresses equal placement frames, and stops after settled. It also boxes each pane frame once per tick and shares that measurement. `www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:28`, `www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:74`, `www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:105`, `www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:219`
* A stale pane animation marker is discounted after six stationary ticks so a missing animation completion callback cannot pin the browser presentation loop. `www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:30`, `www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:146`
* Captured run spawning uses at most five concurrent slots and deduplicates per pane key before creating a server run. `www/packages/canvas/src/model/capturedRunStore.ts:38`, `www/packages/canvas/src/model/capturedRunStore.ts:50`, `www/packages/canvas/src/model/capturedRunStore.ts:207`
* The explicit Canvas stress route exercises up to 30 panes and records p95 and max frame intervals. Its Playwright performance test is the regression harness for layout motion. `www/packages/canvas/src/perf/SessionCanvasStressRoute.tsx:19`, `www/packages/canvas/src/perf/SessionCanvasStressRoute.tsx:84`, `www/packages/shell/tests/perf/sessionCanvasStress.spec.ts:3`
* The Vitest project split is a performance decision: pure TypeScript tests use Node, while components and a small allowlist use jsdom. `www/packages/shell/vite.config.ts:90`

## Landmines and fragile invariants

1. **Production mount order is semantic.** Canvas must be registered before the Inspector `/` catch all. `api/src/transport_matters/main.py:166`
2. **Development `/canvas/` differs from exact `/canvas`.** Shell selection checks exact equality, so a trailing slash chooses Inspector in the composed shell. Production has an explicit bare route plus a mounted `/canvas` subtree. `www/packages/shell/src/route.ts:3`, `api/src/transport_matters/main.py:183`
3. **The composed shell imports both product styles.** That can conceal accidental Canvas dependence on Inspector generated Tailwind utilities, which is why the Tailwind free source scan exists. `www/packages/shell/src/main.tsx:5`, `www/packages/shell/src/testSupport/canvasTailwindFree.test.ts:1`
4. **Overlay means two different data paths.** `useOverrides` is the backend scoped mutation pipeline used by the breakpoint. `useOverlaysStore` is local named curation and does not apply confirmed overlays. Do not wire one by assuming the other already persists the same model. `www/packages/inspector/src/hooks/useOverrides.ts:26`, `www/packages/inspector/src/components/routes/OverlaysView.tsx:20`
5. **Override targets are positional strings.** System and message edits encode indexes, while tools and tool results encode semantic IDs. Parsing accepts signed integers. Any reorder changes target meaning and needs an explicit migration or remap. `www/packages/inspector/src/lib/overrideTargets.ts:1`, `www/packages/inspector/src/lib/overrideTargets.ts:8`, `www/packages/inspector/src/lib/overrideTargets.ts:28`
6. **Override mutation is transactional across two owners.** Python updates its local store and a captured run's shared proxy; any failure restores the prior local snapshot. Bypassing this endpoint can split behavior between captured and ordinary proxy traffic. `api/src/transport_matters/api/v1/overrides.py:141`
7. **Forward and Pass Through preserve different wire guarantees.** Forward validates serialization before release and supplies exact replacement bytes. Pass Through omits release bytes so original transport bytes remain available. `api/src/transport_matters/api/v1/breakpoint_routes.py:181`, `api/src/transport_matters/api/v1/breakpoint_routes.py:198`
8. **HTTP and Codex WebSocket breakpoint completion differ.** HTTP waits for a later SSE exchange response. WebSocket selects the provisional exchange and resolves immediately; forwarding timeout activity is reset by matching stream frames. `www/packages/inspector/src/components/editor/BreakpointEditorActions.ts:45`, `www/packages/inspector/src/components/editor/BreakpointEditorActions.ts:78`
9. **Trace, Recall, and subagent timeline are deliberate placeholders.** Their visible affordances are not proof of backend wiring. `www/packages/inspector/src/components/RouteRail.tsx:25`, `www/packages/canvas/src/viewers/placeholder/PlaceholderPane.tsx:38`
10. **Session harness filtering happens after one server page.** A launch lookup asks for limit 50 and filters by harness in the client. A matching session outside that page remains invisible to this resolver. `www/packages/canvas/src/hooks/useLaunchSession.ts:15`, `www/packages/canvas/src/infrastructure/api/sessionClient.ts:54`
11. **Canvas cache identity is asynchronous and generation guarded.** A late acting context response must not hydrate or rewrite the newly selected Canvas. Keep generation checks around async resolution and rehydration. `www/packages/canvas/src/model/canvasIdentityOwner.ts:237`, `www/packages/canvas/src/model/canvasIdentityOwner.ts:500`, `www/packages/canvas/src/model/canvasIdentityOwner.ts:518`
12. **Only verified or transport failed claimed Canvas identity can become visible.** Stream startup waits for hydration so a server snapshot cannot be overwritten by persisted restore. `www/packages/canvas/src/model/canvasIdentityOwner.ts:113`, `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:55`
13. **Browser panes are dual rendered.** React paints chrome and a reservation; Electron paints the page in a native view positioned from a bridge frame. DOM overlays, drag covers, dock, launcher, fullscreen, resize reach, and transforms all affect occlusion and geometry. `www/packages/canvas/src/viewers/browser/BrowserPane.tsx:65`, `www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:87`
14. **Browser placement must send an empty frame on unmount.** That is the shell's signal to destroy all native views for the Canvas. `www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:126`
15. **Browser store data is observational.** Writing desired URL into `useBrowserPaneStore` creates a second authority beside Gateway state. `www/packages/canvas/src/browsing/browserPaneStore.ts:8`
16. **Captured run close races are handled before a run ID exists.** Cancellation marks an in flight spawn so its eventual run is terminated and never persisted; minimize intent is deferred and close wins. Preserve the promise and intent sets. `www/packages/canvas/src/model/capturedRunStore.ts:207`, `www/packages/canvas/src/model/capturedRunStore.ts:238`, `www/packages/canvas/src/model/capturedRunStore.ts:294`
17. **Zustand persistence is scoped by Canvas identity.** The storage adapter resolves the key dynamically. Persisting before identity activation or switching keys outside `canvasIdentityOwner` risks cross Canvas pane leakage. `www/packages/canvas/src/infrastructure/persistence/canvasCacheStorage.ts:6`, `www/packages/canvas/src/model/canvasIdentityOwner.ts:508`
18. **Modal openness has two owners by design.** Each component owns local visual state; `useOverlayStore` mirrors it for keybinding and native view occlusion. Fullscreen balance depends on effect cleanup and a count, so imperative writes can strand it above zero. `www/packages/canvas/src/interactions/overlayStore.ts:3`, `www/packages/canvas/src/interactions/overlayStore.ts:30`
19. **The viewer registry's generic cast is guarded by ordering and `canRender`.** Calling a registration without its guard violates the cast's safety argument. `www/packages/canvas/src/viewers/registry.tsx:40`, `www/packages/canvas/src/viewers/registry.tsx:184`
20. **HTTP generic types do not validate production JSON.** Add or extend a boundary parser when malformed data could create invalid state; do not assume the type argument proves wire correctness. `www/packages/core/src/transport.ts:150`
21. **Local file missing states are successful domain responses.** A missing or refused file can arrive as HTTP 200 `kind:"missing"`, so error UI belongs in union rendering as well as query error handling. `www/packages/canvas/src/infrastructure/api/resourceContent.ts:84`, `api/src/transport_matters/api/v1/local_file_routes.py:33`
22. **Host chrome order and pointer behavior matter.** Mounting it before app root is intentional, and the channel badge is data driven by backend meta. `www/packages/shell/src/main.tsx:22`, `www/packages/host/src/ChannelBadge.tsx:3`
23. **Resource and terminal CSS can silently disappear.** Keep side effect imports beside rendering modules; dedicated tests scan every stylesheet in those trees. `www/packages/canvas/src/viewers/resource/cssColocation.test.ts:34`, `www/packages/canvas/src/viewers/terminal/cssColocation.test.ts:39`
24. **There is a production source cycle between `canvasActions.ts` and `browserPaneActions.ts`.** Avoid adding new responsibilities across that seam. Prefer extracting a neutral lifecycle operation if work touches both modules. `www/packages/canvas/src/model/canvasActions.ts:16`, `www/packages/canvas/src/model/browserPaneActions.ts:2`
25. **Large but legal files deserve care.** `FirstRunScreen.tsx` and `canvasActions.ts` are near the repository's 700 line hard file threshold. New cross cutting behavior should be placed with its domain owner or extracted before these files grow past policy. `www/packages/canvas/src/firstrun/FirstRunScreen.tsx:623`, `www/packages/canvas/src/model/canvasActions.ts:608`

## Change recipes

### Add an Inspector exchange field

1. Confirm the backend detail or index serializer and update the hand written type.
2. Extend the relevant stream parser if the field arrives live.
3. Keep query key scope unchanged unless the new value introduces another identity coordinate.
4. Render through the current list card, detail panel, or a shared Inspector primitive.
5. Add a Python to TypeScript mirror or shared fixture if the field changes contract structure. Existing IR parity lives at `api/src/transport_matters/test_type_mirrors.py:152`.

### Add a Canvas pane kind

1. Extend the pane ref union and pane identity in `www/packages/canvas/src/model/paneRecords.ts` and `paneIdentity.ts`.
2. Add one registry record in `www/packages/canvas/src/viewers/registry.tsx:56`.
3. Decide explicit close, minimize, restore, duplicate, and persistence semantics.
4. Add API and stream ownership under `infrastructure` if data is remote.
5. Side effect import colocated CSS from the renderer and add focused tests.
6. Exercise standalone Canvas, because the shell's combined stylesheet can hide boundary mistakes. `www/packages/shell/src/testSupport/canvasTailwindFree.test.ts:1`.

### Add or change a backend call

1. Put shared calls in `@tm/core`, Space calls in `@tm/space-client`, Inspector calls in `inspector/src/api.ts`, and Canvas domain calls under `canvas/src/infrastructure` or `canvas/src/browsing`.
2. Define sent and received shapes at the boundary; preserve snake or camel case exactly as serialized.
3. Verify Python origin handler and, for forwarded contexts, Gateway handler.
4. Add runtime parsing when the response drives a discriminated branch or long lived store.
5. Add an invalidation or authoritative cache write rule and test it.
6. For mutations, use `detailAware` when the operator needs backend cause text. `www/packages/core/src/transport.ts:128`.

## Verification matrix

| Change area | Minimum useful proof |
| --- | --- |
| Pure helper, reducer, or store action | Nearest unit test, then owning package typecheck. |
| Inspector or Canvas component | Nearest Testing Library test, `just www typecheck`, and `just www test`. `www/packages/shell/vite.config.ts:101` |
| CSS or layout | Component test plus relevant Playwright visual or E2E suite; Canvas must be exercised as a standalone product bundle. `www/packages/shell/playwright.config.ts:44` |
| Pane motion or browser placement | Unit geometry tests plus Canvas stress or browser pane Playwright path. `www/packages/canvas/src/browsing/useBrowserPanePresentation.test.tsx:121`, `www/packages/shell/tests/perf/sessionCanvasStress.spec.ts:3` |
| Wire contract | Frontend test and typecheck, backend handler test, and the existing parity gate or a new one. `api/src/transport_matters/test_type_mirrors.py:152` |
| Run, terminal, activity, acting context, or browsing seam | Frontend adapter test, Python forward test, Gateway context test, then an end to end path through the Python origin. `api/src/transport_matters/api/v1/test_run_proxy.py:117` |

## Map maintenance

This map is stamped to commit `e97488ea`. Refresh it after route composition, package boundaries, store ownership, wire contracts, or backend forwarding changes. Recheck all `path:line` citations after any large formatting pass. The highest value structural checks are `fmm validate`, shell import graph tests, Canvas Tailwind scan, storage key uniqueness, package typechecks, and the Python type mirror suite. `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:47`, `www/packages/shell/src/testSupport/canvasTailwindFree.test.ts:63`, `www/packages/shell/src/testSupport/storageKeys.test.ts:11`, `api/src/transport_matters/test_type_mirrors.py:152`
