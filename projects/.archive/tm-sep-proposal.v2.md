---
title: Transport Matters www/ Separation Plan (v5) — core kernel + neutral @tm/host + inspector/canvas peers + dev-only shell
type: research
tags: [transport-matters, www, separation, monorepo, canvas, inspector, pnpm-workspace, shell, host, keybindings, theme]
summary: Split www/ into @tm/core (data + keybinding primitives + desktop-detection), @tm/host (DOM chrome), and inspector/canvas peers composed by a dev-only @tm/shell, in a repo-root pnpm workspace. Six behavior-preserving phases. v5 folds in the pre-execution ground-truth review — theme clean break to canvas, the second canvas→inspector leak (ContentBlocks), dead keybinding deletions — and drops changelog archaeology. Self-contained.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-01
updated: 2026-07-02
---

# www/ separation plan (v5)

*(v1–v4 history in `.archive/` and cm. v4 was approved by three reviewers; v5 incorporates the pre-execution ground-truth review of HEAD `4dd7b3e` — every factual claim below is verified against the live tree, not inherited.)*

## 1. Intent & product model

`www/` is one Vite bundle (27.8k LOC, 246 files) serving **two products with opposite UI philosophies**. Share the **domain/data kernel only**, never presentation.

- **Inspector** — Tailwind, completed, the **web** product. Wire-time/reactive: arm a breakpoint, pause the live request, edit in flight, release.
- **Canvas** — **Ark + vanilla BEM CSS (zero Tailwind, verified across all 38 tsx files)**, the **premium desktop** product. Config-time/proactive overlay editing ahead of the request. **No breakpoint.**

**Locked decisions (do not re-litigate):**
- Separate tokens per product; no shared visual base.
- Canvas forks its own Ark exchange viewer; Ark is canvas's target.
- Inspector and canvas are peers; a dev-only shell composes them.
- **Theme clean break (new in v5):** the theme system (`theme/`, `ambient/`, `themeStore`, `useThemeTokens`) is canvas-only. The inspector has no theme UI; its current retinting by a persisted canvas theme is accidental bleed through the shell-level `useThemeTokens` mount and is removed, deliberately. Inspector accent pins to its stylesheet value.

## 2. Workspace decision — CLOSED: repo-root pnpm workspace

JS-only pnpm workspace; `just` stays the cross-language graph. Turborepo/Nx add DAG caching a solo dev doesn't need; uv-workspace is moot (`api/` is one package). Root `pnpm-workspace.yaml` (members `www/packages/*` + `desktop`) gives one install/lockfile. `api/` (Python/uv/hatch) unchanged bar a second bundle. Today's topology (verified): two separate pnpm trees (`www/`, `desktop/`) with own locks and workspace files; `onlyBuiltDependencies:[electron]` lives in `desktop/pnpm-workspace.yaml` and moves to root.

## 3. Dependency graph + final-state FS tree

```
core        # data model, transport, queryClient, keybinding primitives, desktop-detection, formatting, agentPalette
host → core                 # @tm/host: DOM window chrome (ChannelBadge → useMeta)
inspector → {core, host}    # Tailwind web product
canvas    → {core, host}    # Ark/BEM desktop product; owns theme + ambient
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
│   │               #   formatting, agentPalette, contentBlocks helpers, persistence.createFrontendPersistStorage,
│   │               #   desktop-detection, isRecord, @tm/core/keybindings, ./types/*
│   ├── host/       # @tm/host — mountWindowChrome, WindowDragRegion, ChannelBadge + host CSS (dep: @tm/core)  [NEW]
│   ├── inspector/  # @tm/inspector — Tailwind app, breakpoint stack, useExchange(s|Stream)+wired port, detail/editor,
│   │               #   Toggle, icons, TransportMattersIcon, useFullscreenKeybindings, useRouteHotkeys, keymapStore, main.tsx
│   ├── canvas/     # @tm/canvas — session-canvas/engine/ambient/THEME, keybinding engine+gestures, route parsers,
│   │               #   capture stores, themeStore+useThemeTokens, ArkExchangeViewer, BEM CSS, main.tsx
│   └── shell/      # @tm/shell — DEV-ONLY: main.tsx, rootShell (neutral fallback, NO theme mount), RootRoute/selectRootRoute
├── shared/                        # JSON data contracts (unchanged)
└── scripts/                       # release/dev (build BOTH bundles; repo-root paths)
```

## 4. Package boundaries, core surface, enforcement

**`@tm/core` IN** — transport (`apiUrl`, `createApiTransport`, `requestApiJson`, `fetchMeta`); `queryClient` (singleton), `queryKeys`; `useMeta`; neutral fetchers; a **store-free exchange-stream primitive** (pure parsers + the `StreamSideEffects` port, below); `formatting`; `agentPalette`; **content-block helpers** `blockKey`/`blockSummary` (pure derivation over IR content blocks, consumed by both products; extracted from `components/detail/ContentBlocks` in P2); `persistence.createFrontendPersistStorage` (helper only); `isRecord` (generic type guard, today stranded in `theme/types` and imported by `keymapStore`); **desktop-detection** (`isDesktopHost`, `DESKTOP_BRIDGE_KEY`, `globalWindow` — no DOM); **`@tm/core/keybindings`** (`platform`, `Command` types, `gestureModifier`, `domFocus`); explicit type entrypoints `./types/{ir,overrides,exchanges,transport,capabilities,codex,runtimeTemplates}`. Peer deps: `react`, `@tanstack/react-query`.

**`@tm/core` OUT** (verified) — `hooks/exchangeStreamEvents.ts`/`useExchangeStream` → inspector; `types/breakpoints`, `detail/mutations`, `useRouteHotkeys` → inspector; `overlaysStore` → inspector; **all of `theme/` + `ambient/` + `themeStore` + `useThemeTokens` → canvas** (clean break); capture stores + keybinding **engine**/`gestures` + route parsers → canvas.

**Theme clean break mechanics** — `useThemeTokens` writes 7 inline `:root` tokens (`--color-accent`, `--accent-rgb`, 5 `--pane-*`). Only the two accent tokens cross products: they are defined in the inspector's Tailwind `@theme` and consumed by inspector components (`*-accent` utilities in `TrackHeader`, `ExchangeTurnCard`, `ExchangeDetail`, editor components, `ExchangeCard`) and inspector CSS (selection, focus ring, pressed tab, selected row). Canvas CSS (`session-canvas/canvas.css` and siblings) also consumes `--color-accent`/`--accent-rgb` as stylesheet defaults, so in P5 each product defines its own accent defaults in its own token file. The `--pane-*` tokens are canvas pane chrome only. Break: the `useThemeTokens` mount moves out of `RootShell` into the two canvas routes (P1); `isRecord` moves out of `theme/types` (P1) so `keymapStore` keeps zero theme edges; `theme/deps.ts` (theme→ambient wiring) becomes intra-canvas. **Deliberate visible change:** with a persisted canvas theme, the inspector no longer retints; its accent is the stylesheet default.

**Stream side-effect port** — `hooks/exchangeStreamEvents.ts` has 7 `useUIStore` occurrences / 6 `.getState()` reads (verified). Core parsers are pure; the port carries: reads `getForwardingFlowId`, `getPausedFlow`, `getSelectedId`; effects `bumpForwardingActivity()`, `setForwardingFlowId(id|null)`. Inspector's `useExchangeStream` binds the port to `uiStore`.

**Keybinding split** — `engine.ts` has exactly four importers (verified): `hooks/useFullscreen` (used by inspector `ExchangeDetail`), `SessionCanvasRoute`, `PaneDock`, `launcher/useLauncherHotkeys`. `registry.ts` is live, not dead: `engine.ts` imports `COMMANDS` plus the `Command`/`CommandContext`/keybinding-target types from it. Split: core gets `platform`, the `Command` type surface from `registry.ts` (`Command`, `CommandContext`, target types), `gestureModifier` (inspector `keymapStore` + canvas launcher), `domFocus` (`useRouteHotkeys` + `engine` + `gestures`). Inspector extracts `useFullscreenKeybindings` **out of** `engine.ts` plus the fullscreen `COMMANDS` slice, and owns `useRouteHotkeys` + `keymapStore`. Canvas keeps `KeybindingEngineProvider`, launcher/dock hooks, the remaining `engine.ts`, the `COMMANDS` registry remainder, `gestures`, ambient bindings. **Dead code deleted in P1 (verified):** `keybindings/format.ts` only (imported solely by its own test); `format` is NOT part of the core surface. **Gate:** inspector must not import canvas `engine.ts`; graph shows zero inspector↔canvas.

**`route.ts` split** — canvas: `parseCanvasLaunchContext`, `defaultCanvasId`, `worktreeSwitchUrl`, `isStressCanvas`, `CanvasLaunchContext` (type). Shell: `RootRoute`, `selectRootRoute`.

**`lib/` + strays disposition (verified):**
| module | home |
|---|---|
| `formatting`, `agentPalette`, `domFocus`, `gestureModifier`, `queryClient`, `persistence.createFrontendPersistStorage`, `blockKey`/`blockSummary`, `isRecord` | core |
| `overrideTargets`, `overrides`, `exportInspect`, `colorizeLine`, `charAccounting`, `useRouteHotkeys` | inspector |
| `theme/*`, `ambient/*`, `themeStore`, `useThemeTokens`, `theme/deps` | canvas |
| `persistence.FRONTEND_STORAGE_KEYS` | split per product |
| `stores/persistence.ts` registry | split per product (it maps both products' localStorage keys today) |
| `browserIdentity.ts` | **does not exist** (only `browserIdentity.test.ts`, migrated P3) |

**`agentPalette` contract** — maps agent index → `var(--color-agent-rail-N)`, **defines no values and imports no product CSS**. Each product defines the `--agent-rail-*`/`--color-agent-rail-*` token values in its **own** token file.

**`@tm/inspector`** — `app`/`routeLayout`, `uiStore`, breakpoint stack, exchange list+detail, `overlaysStore`, `mutations`, `useExchange(s|Stream)`, `Toggle`, `icons`, `TransportMattersIcon`, `useFullscreenKeybindings`/`useRouteHotkeys`/`keymapStore`, Tailwind `@theme` + `inspector.css`, `index.html`, `main.tsx`. Dep: `tailwindcss`. No theme system.
**`@tm/canvas`** — `session-canvas/**`, `engine/` (pane layout; canvas-only despite the generic name, 28 canvas importers), `ambient/`, `theme/`, keybinding engine+gestures+ambient bindings, route parsers, `themeStore`+`useThemeTokens`, capture stores, canvas components, `ArkExchangeViewer`, BEM CSS, `index.html`, `main.tsx`. Runtime: `@ark-ui/react`, `@dnd-kit/*`, `framer-motion`, `@xterm/*`. No Tailwind, no breakpoint.
**`@tm/host`** (dep `@tm/core`) — `mountWindowChrome()`, `WindowDragRegion`, `ChannelBadge` + `window-drag-region.css`/`channel-badge.css`. Exports `"."` and `./styles.css`; consumers import host CSS in their `main.tsx`. Tailwind-free.
**`@tm/shell`** (dev-only) — `main.tsx`, `rootShell.tsx` (**neutralized non-Tailwind fallback, no theme mount**), `RootRoute`/`selectRootRoute`. Deps `{core, host, inspector, canvas}`. Zero production-imported, zero Tailwind symbols.

**Enforcement** — per-package `exports` maps declare `"."` **plus** the explicit subpaths the plan uses (`./types/*`, `./keybindings`, host `./styles.css`); anything not in the map (any `/src` reach-in) is forbidden. An import-graph **Vitest test resolves by package name**, fails on deep + relative cross-package imports, runs in CI `pnpm test`. Plus a **package.json dep-lint**: `inspector` and `canvas` `dependencies` must never list each other. `dependency-cruiser` optional/deferred.

## 5. Incremental phased plan

Every phase leaves a **working, user-testable app**; each sub-step gates on `just check` + `just test`. `api.ts` (P4) and `index.css` (P5) are cut **once**. **P3 (mechanical) and P4 (semantic) are separate sequential commits.**

**Phase 1 — Groom (in place).** Rename `legacy`→`inspector`; route `useCanvasDropTargets` through `desktopHost`; unify `canvasStore`/`canvasLabStore`; de-dup inspector mutation/sampling/thinking hooks; prune dead `index.css`. **Delete `keybindings/format.ts`** (test-only, verified); `keybindings/registry.ts` stays — `engine.ts` imports `COMMANDS` and the `Command`/`CommandContext`/target types from it, and it splits in P4/P5. **Theme clean break:** move the `useThemeTokens()` mount from `RootShell` into `SessionCanvasRoute` + `CanvasLabRoute`; move `isRecord` from `theme/types` to `lib/`. **Neutralize the `rootShell` Suspense fallback** (currently `min-h-screen bg-canvas text-txt`) to a neutral element. Consolidate `WindowDragRegion` + the `document.body.prepend` bootstrap into `src/host/mountWindowChrome()` with `ChannelBadge`; neutralize their Tailwind to plain CSS. Add the `session-canvas` import-graph boundary test pinning **both** breaches (`ProviderExchangeResourceViewer → ExchangeDetail`; `TranscriptMessage → components/detail/ContentBlocks`). Optional groom: resolve the `ExchangeDetail` component-vs-type name collision. Flag `tm-ui-sep-consensus.md` stale. **USER TEST:** web — arm/pause/edit/release; **inspector keeps its default accent even with a canvas theme active** (the one deliberate visual change); canvas — drag a pane, cycle theme, canvas↔lab; titlebar + badge intact.

**Phase 2 — Sever BOTH canvas→inspector leaks.** (a) Add `ArkExchangeViewer` (read-only) with a render contract + visual snapshot + a **tab-mapping test** (`toDetailTab`: `request`→`request`, `response`→`response`, `diagnostics`→`transport`, default→`inspect`); repoint `ProviderExchangeResourceViewer` + callers (`registry.tsx`, `ResourcePane.tsx`); drop the `ExchangeDetail` import. (b) Extract `blockKey`/`blockSummary` from `components/detail/ContentBlocks` into `lib/contentBlocks.ts` (pure helpers); repoint `TranscriptMessage` + `ContentBlocks`. Flip the P1 test to enforce **no canvas→inspector at all**. Canvas is Tailwind-free. **USER TEST:** open a provider-exchange pane → renders via `ArkExchangeViewer`, snapshot matches; transcript chat renders identically; web detail unchanged.

**Phase 3 — Scaffold repo-root workspace (app identical, one bundle; mechanical).** Move `pnpm-workspace.yaml` to root; add root `package.json`; move `onlyBuiltDependencies:[electron]` to root; delete `www/`+`desktop/` locks + `desktop/pnpm-workspace.yaml`; fix desktop `clean` (no lock). `git mv` the app into `packages/shell/`; relocate `src/host/`→`packages/host`; empty `core`/`inspector`/`canvas` skeletons. **Anchor `vite` `outDir` to the workspace root** — `path.resolve(searchForWorkspaceRoot(process.cwd()), "api/src/transport_matters/www")`. **Update every CI job** (`ci.yml`: `frontend`, `frontend-e2e`, `desktop`, `package`; `release.yml`: `build`): `cache-dependency-path`→root `pnpm-lock.yaml`, `package_json_file`→root, `working-directory`→root or `--filter`. **Scripts:** `local-dev-mode.sh` `www_dir`, `release.sh` `pnpm release`/`pnpm dev` → root/`--filter`; `just www dev`→`pnpm --filter @tm/shell dev`. **Migrate `browserIdentity.test.ts`**: repoint its `ROOT` + `BROWSER_IDENTITY_SURFACES` to the post-scaffold package tree. Update justfiles, `playwright.config` webServer, tsconfigs+`tsconfig.base`, vitest `include`, `biome.json`, `test_type_mirrors.py`, `install-local`, visual fixtures. **Note:** `www/` now names three things — the packages dir, the retired single package, and the built inspector output (`api/.../www`); document the mapping in root `package.json`/CLAUDE.md. **Gate: fresh-clone `just check && just test && just build`.** **USER TEST:** web + desktop pixel-identical.

**Phase 4 — Extract core (cut `api.ts` once; separate commit).** Move the core IN-list into `packages/core`; split `api.ts` (583 LOC, 27 dependents) once. Implement the **stream port** (core pure parsers + the 5-member `StreamSideEffects`; inspector's `useExchangeStream` wires it). Move the **core keybinding primitives** (`platform`, `Command` types, `gestureModifier`, `domFocus`) + desktop-detection into core; `platform` now imports `DESKTOP_BRIDGE_KEY` from core (no host edge). Move `formatting`, `agentPalette`, `contentBlocks`, `isRecord`, `persistence.createFrontendPersistStorage`, `queryClient`. Add `CORE_TYPES_ROOT` to `test_type_mirrors.py` same commit. **Gate: core stream + keybinding code has zero `stores/` imports; core knows no product store names and no theme symbols.** **USER TEST:** web + desktop unchanged; exchanges stream/render, breakpoint pause intact.

**Phase 5 — Split products under shell (cut `index.css` once; one bundle).** `git mv` inspector tree (incl. `Toggle`, `icons`, `TransportMattersIcon`, override/export/colorize/charAccounting, `keymapStore`, `useRouteHotkeys`) and canvas tree (route parsers, keybinding engine+gestures, the `COMMANDS` registry remainder, **theme/ + ambient/ + themeStore + useThemeTokens**). **Extract `useFullscreenKeybindings` out of `engine.ts` into inspector** so inspector stops importing canvas `engine.ts`. Shell shrinks to composer + neutral fallback. Partition `index.css` once: inspector keeps Tailwind `@theme` incl. its accent definitions (`--color-accent: #e8e4dc`, `--accent-rgb`); canvas takes the `--pane-*` tokens, defines its own `--color-accent`/`--accent-rgb` defaults (its CSS consumes them as fallbacks when no theme is active), and copies needed color values incl. `--agent-rail-*`. Split `stores/persistence.ts` (the cross-product localStorage key registry, incl. `FRONTEND_STORAGE_KEYS`) per product. Enforcement gate + dep-lint go green. Add `canvas/CLAUDE.md` + `inspector/CLAUDE.md`. **USER TEST:** identical behavior; both products in the one shell bundle; import graph clean.

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
- **P1 (low):** rename + chrome/fallback neutralization + theme-mount move. Guard: `WindowDragRegion`/`ChannelBadge` tests; import-graph test pins both breaches. The theme-mount move is the one deliberate behavior change; verify inspector renders with default accent under a persisted canvas theme.
- **P2 (med):** `ArkExchangeViewer` parity + `contentBlocks` extraction. Guard: render contract + snapshot + tab-mapping test; transcript-chat render unchanged.
- **P3 (high, mechanical):** repo-root move touches every path artifact (CI jobs, desktop membership, scripts, `browserIdentity.test`). Guard: workspace-root `outDir` + atomic commit + **fresh-clone gate**.
- **P4 (med, semantic):** stream port must preserve pause/forward semantics; keybinding-primitive + desktop-detection extraction must break the `platform`→`host` cycle; `test_type_mirrors.py`. Guard: zero-`stores/`-import gate + `CORE_TYPES_ROOT` same-commit.
- **P5 (med):** token duplication (accepted); `useFullscreenKeybindings` extraction is the make-or-break for inspector⊥canvas. Guard: import-graph + dep-lint gates.
- **P6 (high, topology):** dual-mount ordering / `base:"/canvas"` asset 404 / missing wheel `canvas/**` / per-entry CSS + host chrome + theme bootstrap. Guard: two-dir static test + asset-404 regression + Playwright matrix.

## 7. Out of scope, noted

The backend has one analogous inversion this plan does not touch: launch orchestration lives under `cli/` (7.7k LOC) while the server's `RunManager` consumes it (`captured_run.py` imports `cli.launch_runtime`, `cli.runner`, `cli.launch_profile`, `cli.runtime_home`, `cli.prompt`, `cli.identity`). The 4-file import cycle was fixed (#178); the layer direction was not. Companion track, north-star aligned (CLI and server as twin clients of one launch domain): extract a `launch/` package. Sequence after or interleaved with P3–P6; do not grow it into this plan. Also parked: the triple `desktop_runtime` module name collision (root, `cli/`, `api/v1/`).
