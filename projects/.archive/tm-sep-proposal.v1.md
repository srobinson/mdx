---
title: Transport Matters www/ Separation Proposal (v4) — core kernel + neutral @tm/host + inspector/canvas peers + dev-only shell
type: research
tags: [transport-matters, www, separation, monorepo, canvas, inspector, pnpm-workspace, shell, host, keybindings]
summary: Split www/ into @tm/core (data + keybinding primitives + desktop-detection), @tm/host (DOM chrome, depends on core), and inspector/canvas peers, composed for dev by a dev-only @tm/shell, in a repo-root pnpm workspace. Six behavior-preserving phases. v4 lands the keybinding + desktopHost splits and the exports self-contradiction fix; inspector↔canvas is clean by construction.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-01
updated: 2026-07-02
---

# www/ separation proposal (v4)

*(v1–v3 history in cm/git. All three reviewers approved v3 for execution pending the keybinding-split design fix + self-consistency items; v4 applies them. Contested facts were ground-truthed by the orchestrator via grep and are used directly.)*

## Changelog v3→v4
- **Keybinding split (the design gap).** `engine.ts` is SHARED: `hooks/useFullscreen.ts` imports `useFullscreenKeybindings` from `keybindings/engine.ts` and inspector `ExchangeDetail` uses `useFullscreen`; canvas launcher/dock + ambient also import `engine.ts`. Explicit three-way split in §4/P4/P5 (core primitives; inspector extracts `useFullscreenKeybindings`; canvas keeps the engine).
- **`desktopHost` split** (resolves a `platform`→`host` cycle: `keybindings/platform.ts` imports `DESKTOP_BRIDGE_KEY` from `desktopHost`). Detection primitive (`isDesktopHost`, `DESKTOP_BRIDGE_KEY`, `globalWindow`, no DOM) → **core**; DOM chrome (`WindowDragRegion`, `mountWindowChrome`, `ChannelBadge`) → **@tm/host**. `@tm/host` depends on core (`ChannelBadge`→`useMeta`).
- **`agentPalette` → core** as a neutral var-reference mapping (it only references `var(--color-agent-rail-N)`, defines no values; used by inspector `ExchangeTurnCard`/`TrackHeader` + canvas `CommandCenter`). Contract preserved below.
- **Exports fix (Codex Blocker: v3 self-contradicted).** The map declares `"."` **plus** the explicit subpaths the plan uses (`./types/*`, `./keybindings`); "forbid deep imports" = forbid anything **not** in the map (no `/src` reach-in). Not `"."`-only.
- Full `route.ts` canvas split list; `lib/` map completed (`domFocus`, `useRouteHotkeys`, `gestureModifier`); `browserIdentity.test.ts` (module never existed) migrated in P3; host `package.json`/CSS sketched; package.json dep-lint added; `exchangeStreamEvents` nailed to 7 `useUIStore` occ / 6 `getState()` reads → a 5-member port; Grok's dev-experience items folded in as plan content.

## 1. Intent & product model
`www/` is one Vite bundle serving **two products with opposite UI philosophies**. Share the **domain/data kernel only**, never presentation.
- **Inspector** — Tailwind, completed, the **web** product. Wire-time/reactive: arm a breakpoint, pause the live request, edit in flight, release.
- **Canvas** — **Ark + vanilla BEM CSS (zero Tailwind)**, the **premium desktop** product. Config-time/proactive overlay editing ahead of the request. **No breakpoint.** Drift/onboarding is embedded in canvas surfaces, canvas-local.

Locked (do not re-litigate): separate tokens per product (no shared base); canvas **forks its own Ark exchange viewer**; Ark is canvas's target; inspector/canvas are peers; a dev-only shell composes them.

## 2. Workspace decision — CLOSED: repo-root pnpm workspace
JS-only pnpm workspace; `just` stays the cross-language graph. Turborepo/Nx add DAG caching a solo dev doesn't need; uv-workspace is moot (`api/` is one package). Root `pnpm-workspace.yaml` (members `www/packages/*` + `desktop`) gives one install/lockfile, closing debt #8. `api/` (Python/uv/hatch) unchanged bar a second bundle.

## 3. Dependency graph + final-state FS tree
```
core        # data model, transport, queryClient, keybinding primitives, desktop-detection, formatting, agentPalette
host → core                 # @tm/host: DOM window chrome (ChannelBadge → useMeta)
inspector → {core, host}    # Tailwind web product
canvas    → {core, host}    # Ark/BEM desktop product
shell     → {core, host, inspector, canvas}   # DEV-ONLY composer
```
inspector ⊥ canvas (no edge either way) — clean by construction.
```
transport-matters/                 # repo root = pnpm workspace root
├── pnpm-workspace.yaml            # packages: [www/packages/*, desktop]   [MOVED]
├── package.json                   # private root: shared devDeps + onlyBuiltDependencies:[electron] + dep-lint  [NEW]
├── pnpm-lock.yaml                 # single JS lockfile   [www/ + desktop/ locks deleted]
├── justfile                       # cross-language graph (www recipes → pnpm --filter)
├── api/src/transport_matters/
│   ├── main.py                    # dual SpaStaticFiles: mount /canvas, then / (catch-all last)
│   ├── www/                       # built INSPECTOR bundle (served at /)
│   └── canvas/                    # built CANVAS bundle (served at /canvas)   [NEW]
├── desktop/  (workspace member — Electron; window.ts already loads /canvas)
├── www/packages/
│   ├── core/       # @tm/core — transport, queryClient/keys, useMeta, store-free stream primitive + port,
│   │               #   formatting, agentPalette, persistence.createFrontendPersistStorage, desktop-detection,
│   │               #   @tm/core/keybindings {platform, format, Command types, gestureModifier, domFocus}, ./types/*
│   ├── host/       # @tm/host — mountWindowChrome, WindowDragRegion, ChannelBadge + host CSS (dep: @tm/core)  [NEW]
│   ├── inspector/  # @tm/inspector — Tailwind app, breakpoint stack, useExchange(s|Stream)+wired port, detail/editor,
│   │               #   Toggle, icons, TransportMattersIcon, useFullscreenKeybindings, useRouteHotkeys, keymapStore, main.tsx
│   ├── canvas/     # @tm/canvas — session-canvas/engine/ambient/theme, keybinding engine+gestures, route parsers,
│   │               #   capture stores, ArkExchangeViewer, useThemeTokens, BEM CSS, main.tsx
│   └── shell/      # @tm/shell — DEV-ONLY: main.tsx, rootShell (neutral fallback), RootRoute/selectRootRoute
├── shared/                        # JSON data contracts (unchanged)
└── scripts/                       # release/dev (build BOTH bundles; repo-root paths)
```

## 4. Package boundaries, core surface, enforcement
**`@tm/core` IN** — transport (`apiUrl`, `createApiTransport`, `requestApiJson`, `fetchMeta`); `queryClient` (singleton), `queryKeys`; `useMeta`; neutral fetchers; a **store-free exchange-stream primitive** (pure parsers + a `StreamSideEffects` port, below); `formatting`; `agentPalette`; `persistence.createFrontendPersistStorage` (helper only); **desktop-detection** (`isDesktopHost`, `DESKTOP_BRIDGE_KEY`, `globalWindow` — no DOM); **`@tm/core/keybindings`** (`platform`, `format`, `Command` types, `gestureModifier`, `domFocus` — all verified cross-product); explicit type entrypoints `./types/{ir,overrides,exchanges,transport,capabilities,codex,runtimeTemplates}`. Peer deps: `react`, `@tanstack/react-query`.
**`@tm/core` OUT** (verified) — `exchangeStreamEvents`/`useExchangeStream` → inspector; `types/breakpoints`, `detail/mutations`, `useRouteHotkeys` → inspector; `overlaysStore` → inspector; capture stores + keybinding **engine**/`gestures` + route parsers → canvas.

**Stream side-effect port** — `exchangeStreamEvents.ts` has 7 `useUIStore` occurrences / 6 `.getState()` reads. Core parsers are pure; the port carries: reads `getForwardingFlowId`, `getPausedFlow`, `getSelectedId`; effects `bumpForwardingActivity()`, `setForwardingFlowId(id|null)`. Inspector's `useExchangeStream` binds the port to `uiStore`.

**Keybinding split** — core: `platform`, `format`, `Command` types, `gestureModifier` (inspector `keymapStore` + canvas launcher), `domFocus` (`useRouteHotkeys` + `engine` + `gestures`). Inspector: extract `useFullscreenKeybindings` **out of** `engine.ts`; fullscreen `COMMANDS` slice; `useRouteHotkeys` (`app.tsx`); `keymapStore`. Canvas: `KeybindingEngineProvider`, launcher/dock hooks, the remaining `engine.ts`, `gestures`, ambient keybindings. **Gate:** inspector must not import canvas `engine.ts`; graph shows zero inspector↔canvas.

**`route.ts` split** — canvas: `parseCanvasLaunchContext`, `defaultCanvasId`, `worktreeSwitchUrl`, `isStressCanvas`, `CanvasLaunchContext` (type). Shell: `RootRoute`, `selectRootRoute`.

**`lib/` disposition (verified):**
| module | home |
|---|---|
| `formatting`, `agentPalette`, `domFocus`, `gestureModifier`, `queryClient`, `persistence.createFrontendPersistStorage` | core |
| `overrideTargets`, `overrides`, `exportInspect`, `colorizeLine`, `charAccounting`, `useRouteHotkeys` | inspector |
| `persistence.FRONTEND_STORAGE_KEYS` | split per product |
| `browserIdentity.ts` | **does not exist** (only `browserIdentity.test.ts`, migrated P3) |

**`agentPalette` contract** — it maps agent index → `var(--color-agent-rail-N)`, **defines no values and imports no product CSS**. Each product defines the `--agent-rail-*`/`--color-agent-rail-*` tokens in its **own** token file (separate-tokens decision preserved).

**`@tm/inspector`** — `app`/`routeLayout`, `uiStore`, breakpoint stack, exchange list+detail, `overlaysStore`, `mutations`, `useExchange(s|Stream)`, `Toggle`, `icons`, `TransportMattersIcon`, `useFullscreenKeybindings`/`useRouteHotkeys`/`keymapStore`, Tailwind `@theme` + `inspector.css`, `index.html`, `main.tsx`. Dep: `tailwindcss`.
**`@tm/canvas`** — `session-canvas/**`, `engine`/`ambient`/`theme`, keybinding engine+gestures+ambient bindings, route parsers, `themeStore`, capture stores, canvas components, `ArkExchangeViewer`, BEM CSS, `index.html`, `main.tsx`. Runtime: `@ark-ui/react`, `@dnd-kit/*`, `framer-motion`, `@xterm/*`. No Tailwind, no breakpoint.
**`@tm/host`** (dep `@tm/core`) — `mountWindowChrome()`, `WindowDragRegion`, `ChannelBadge` + `window-drag-region.css`/`channel-badge.css`. Exports `"."` (components + `mountWindowChrome`) and `./styles.css`; consumers import host CSS in their `main.tsx` (dev shell once; each prod bundle once). Tailwind-free.
**`@tm/shell`** (dev-only) — `main.tsx`, `rootShell.tsx` (**neutralized non-Tailwind fallback**), `RootRoute`/`selectRootRoute`. Deps `{core, host, inspector, canvas}`. **Zero production-imported, zero Tailwind symbols.**

**Enforcement** — per-package `exports` maps declare `"."` + the explicit subpaths the plan uses (`./types/*`, `./keybindings`, host `./styles.css`); anything not in the map (any `/src` reach-in) is forbidden. An import-graph **Vitest test resolves by package name**, fails on deep + relative cross-package imports, and runs in CI `pnpm test`. Plus a **package.json dep-lint**: `inspector` and `canvas` `dependencies` must never list each other. `dependency-cruiser` is optional/deferred.

## 5. Incremental phased plan
Every phase leaves a **working, user-testable app**; each sub-step gates on `just check` + `just test`. `api.ts` (P4) and `index.css` (P5) are cut **once**. **P3 (mechanical) and P4 (semantic) are separate sequential commits.**

**Phase 1 — Groom (in place).** Rename `legacy`→`inspector`; route `useCanvasDropTargets` through `desktopHost`; unify `canvasStore`/`canvasLabStore`; de-dup inspector mutation/sampling/thinking hooks; prune dead `index.css`. **Neutralize the `rootShell` Suspense fallback** (currently `min-h-screen bg-canvas text-txt`) to a neutral element. Consolidate `WindowDragRegion` + the `document.body.prepend` bootstrap into `src/host/mountWindowChrome()` with `ChannelBadge`; neutralize their Tailwind to plain CSS. Add the `session-canvas` import-graph boundary test pinning the `ProviderExchangeResourceViewer → ExchangeDetail` breach. Flag `tm-ui-sep-consensus.md` stale. **USER TEST:** web — arm/pause/edit/release; canvas — drag a pane, cycle theme, canvas↔lab; titlebar + badge intact. Identical.

**Phase 2 — Sever the ExchangeDetail leak.** Add `ArkExchangeViewer` (read-only) with a render contract + visual snapshot + a **tab-mapping test** (`toDetailTab`: `request`→`request`, `response`→`response`, `diagnostics`→`transport`, default→`inspect`); repoint `ProviderExchangeResourceViewer` + callers (`registry.tsx`, `ResourcePane.tsx`); drop the `ExchangeDetail` import; flip the P1 test to enforce no canvas→inspector. Canvas is Tailwind-free. **USER TEST:** open a provider-exchange pane → renders via `ArkExchangeViewer`, snapshot matches; web detail unchanged.

**Phase 3 — Scaffold repo-root workspace (app identical, one bundle; mechanical).** Move `pnpm-workspace.yaml` to root; add root `package.json`; move `onlyBuiltDependencies:[electron]` to root; delete `www/`+`desktop/` locks + `desktop/pnpm-workspace.yaml`; fix desktop `clean` (no lock). `git mv` the app into `packages/shell/`; relocate `src/host/`→`packages/host`; empty `core`/`inspector`/`canvas` skeletons. **Anchor `vite` `outDir` to the workspace root** — `path.resolve(searchForWorkspaceRoot(process.cwd()), "api/src/transport_matters/www")` (today `../api/...`; stop counting `../`). **Update every CI job** (`ci.yml`: `frontend`, `frontend-e2e`, `desktop`, `package`; `release.yml`: `build`): `cache-dependency-path`→root `pnpm-lock.yaml`, `package_json_file`→root, `working-directory`→root or `--filter`. **Scripts:** `local-dev-mode.sh` `www_dir`, `release.sh` `pnpm release`/`pnpm dev` → root/`--filter`; `just www dev`→`pnpm --filter @tm/shell dev`. **Migrate `browserIdentity.test.ts`** (`www/src/`): repoint its `ROOT` + `BROWSER_IDENTITY_SURFACES` (`package.json`/`index.html`/`vite.config.ts`/`src`/`tests/visual/fixtures`) to the post-scaffold package tree so it guards old-identity strings across `packages/*`, not stale paths. Update justfiles, `playwright.config` webServer, tsconfigs+`tsconfig.base`, vitest `include`, `biome.json`, `test_type_mirrors.py`, `install-local`, visual fixtures. **Note:** `www/` now names three things — the packages dir (`www/packages/`), the retired single package, and the built inspector output (`api/.../www`); document the mapping in the root `package.json`/CLAUDE.md. **Gate: fresh-clone `just check && just test && just build`.** **USER TEST:** web + desktop pixel-identical.

**Phase 4 — Extract core (cut `api.ts` once; separate commit).** Move the core IN-list into `packages/core`; split `api.ts` once. Implement the **stream port** (core pure parsers + the 5-member `StreamSideEffects`; inspector's `useExchangeStream` wires it). Move the **core keybinding primitives** (`platform`, `format`, `Command` types, `gestureModifier`, `domFocus`) + desktop-detection into core; `platform` now imports `DESKTOP_BRIDGE_KEY` from core (no host edge). Move `formatting`, `agentPalette`, `persistence.createFrontendPersistStorage`, `queryClient`. Add `CORE_TYPES_ROOT` to `test_type_mirrors.py` same commit. **Gate: core stream + keybinding code has zero `stores/` imports; core knows no product store names.** **USER TEST:** web + desktop unchanged; exchanges stream/render, breakpoint pause intact.

**Phase 5 — Split products under shell (cut `index.css` once; one bundle).** `git mv` inspector tree (incl. `Toggle`, `icons`, `TransportMattersIcon`, override/export/colorize/charAccounting, `keymapStore`, `useRouteHotkeys`) and canvas tree (route parsers, keybinding engine+gestures). **Extract `useFullscreenKeybindings` out of `engine.ts` into inspector** so inspector stops importing canvas `engine.ts`. Shell shrinks to composer + neutral fallback. Partition `index.css` once (inspector Tailwind `@theme`+`inspector.css`; canvas copies needed color values incl. `--agent-rail-*`). Enforcement gate + dep-lint go green. Add `canvas/CLAUDE.md` + `inspector/CLAUDE.md`. **USER TEST:** identical behavior; both products in the one shell bundle; import graph clean.

**Phase 6 — Two bundles + separate serving.** Each product gets its own `index.html` + `main.tsx` + `vite.config` (inspector `outDir .../www`; canvas `outDir .../canvas`, `base:"/canvas"`). Sketch:
```
inspector/main.tsx: import "./inspector.css"; import "@tm/host/styles.css";
  mountWindowChrome(); createRoot(#root).render(<StrictMode><QueryClientProvider client={queryClient}><InspectorApp/></QueryClientProvider></StrictMode>)
canvas/main.tsx:    import "./canvas.css"; import "@tm/host/styles.css";
  mountWindowChrome(); bootstrapThemeTokens(); createRoot(#root).render(<StrictMode><QueryClientProvider client={queryClient}><CanvasApp/></QueryClientProvider></StrictMode>)
```
Shell drops from prod (dev only). **Shell dev Vite resolution:** aliases `@tm/inspector`/`@tm/canvas` to their `packages/*/src` lazy entries + `server.fs.allow: [workspaceRoot]`. `main.py` dual SpaStaticFiles (`/canvas` then `/`); pyproject `artifacts += "src/transport_matters/canvas/**"`; CI uploads both; `install-local`/`channel-restart` build both. **Validate with REAL two-directory built artifacts:** a two-bundle static integration test (replacing single-bundle `test_static_canvas.py`) + an **asset-404 regression** (`/assets/foo.js`→404, not the wrong SPA); **Playwright matrix** — inspector `/`, canvas `/canvas` (`base`), desktop smoke vs the canvas bundle. Desktop = verification (`rendererUrlForPort` defaults `/canvas`). **USER TEST:** web root = inspector; `/canvas` (and `just desktop dev`) boots canvas — onboarding/panes/theme/`ArkExchangeViewer`/canvas↔lab + titlebar work; breakpoint stays inspector-only.

## 6. Risks & rollback (per phase)
Rollback for every phase = revert the commit (P6 falls back to the working P5 single-bundle state).
- **P1 (low):** rename + chrome/fallback neutralization. Guard: `WindowDragRegion`/`ChannelBadge` tests; import-graph test pins the breach.
- **P2 (med):** `ArkExchangeViewer` parity. Guard: render contract + snapshot + tab-mapping test.
- **P3 (high, mechanical):** repo-root move touches every path artifact (CI jobs, desktop membership, scripts, `browserIdentity.test`). Guard: workspace-root `outDir` + atomic commit + **fresh-clone gate**.
- **P4 (med, semantic):** stream port must preserve pause/forward semantics; keybinding-primitive + desktop-detection extraction must break the `platform`→`host` cycle; `test_type_mirrors.py`. Guard: zero-`stores/`-import gate + `CORE_TYPES_ROOT` same-commit.
- **P5 (med):** token duplication (accepted); `useFullscreenKeybindings` extraction is the make-or-break for inspector⊥canvas. Guard: import-graph + dep-lint gates.
- **P6 (high, topology):** dual-mount ordering / `base:"/canvas"` asset 404 / missing wheel `canvas/**` / per-entry CSS + host chrome + `useThemeTokens`. Guard: two-dir static test + asset-404 regression + Playwright matrix.
