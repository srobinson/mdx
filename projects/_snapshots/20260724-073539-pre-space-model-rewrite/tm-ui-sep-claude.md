---
title: Transport Matters www/ UI Design-System Separation — Scout & Plan
type: research
tags: [transport-matters, www, design-system, separation, grooming, ark, tailwind]
summary: One Tailwind v4 @theme substrate + a shared api.ts/useMeta/queryKeys spine straddle both UI layers; "zero shared" is false for infra though true for React leaf components. index.css and api.ts are the double-work traps.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-01
updated: 2026-07-01
---

# www/ UI separation: scout + plan

**Ground-truth correction up front.** Ark UI is imported in exactly **two** files, both under `www/src/session-canvas/launcher` — it is not the design system of Layer A. Both layers style with **Tailwind v4 utility classes drawn from one shared `@theme` block in `www/src/index.css`** (session-canvas: 39 `className=` files, 0 CSS-in-JS; inspector: 25). There is one Tailwind config (`@import "tailwindcss"` + `@theme` in `index.css`, compiled by `@tailwindcss/vite` in `vite.config.ts`), one token set. `desktop/` is not a UI layer: `desktop/src/main.ts` (`BrowserWindow.loadURL`) wraps the FastAPI-served www bundle and ships no renderer (`desktop/src/rendererBoundary.test.ts` enforces this).

## A. Design-system partition (file-level)

**Layer A (canvas):** all of `session-canvas/` (171 files); `ambient/`, `engine/` (pane layout), `keybindings/`, `theme/` (runtime pipeline: `theme/presets`, `dayCycle`, `stores/themeStore`); and the canvas-flavoured components co-located in `components/`: `PaneDock`, `PaneChrome`, `AmbientBackdrop`, `CanvasDropTargetOverlay`, `CanvasDropHint`, `RouteSwitcher`, `SceneParamControls`, `ThemeCycleButton`, `CommandBarSections`.

**Layer B (inspector):** `app.tsx` (`App`/`BrowserAppShell`), `routeLayout.tsx`, `stores/uiStore`, hooks `useExchanges`/`useExchangeStream`/`useBreakpoint`/`useRouteHotkeys`/`useFullscreen`, and the inspector components in `components/`: `ExchangeList`, `ExchangeDetail`, `ExchangePreview`, `ExchangeTurnCard`, `RouteRail`, `ArmToggle`, `TrackHeader`, `editor/*` (`BreakpointEditor`…), `detail/*` (`ExchangeCard`, `InspectTab`, `mutations`…), `routes/*` (`TraceView`, `RecallView`, `OverlaysView`, `RouteAtmosphere`).

Tokens live only in `index.css` `@theme`. No `tailwind.config.*` exists (v4 CSS-first).

**"Zero shared components": SPLIT VERDICT.** True for React *leaf components* — no UI component is imported by both trees (Layer B → Layer A appears only in a test, `ChannelBadge.test.tsx`). **False for shared infra.** Both layers import: `api.ts` (god-client), `hooks/useMeta`, `lib/queryKeys`, `types.ts`, and the single `index.css` token substrate. The theme pipeline (`useThemeTokens` in `rootShell.tsx`) also runs globally across both routes. So "share nothing but the build" is refuted.

**Straddlers / neutral infra + required division:**
- `api.ts` (583 LoC) — split by domain: inspector API (breakpoint/overrides/exchanges/turn-content) vs canvas API (runs/spaces/worktrees/runtime-template) + a neutral core (`apiUrl`, `createApiTransport`, `requestApiJson`, `fetchMeta`).
- `index.css` — keep a neutral base `@theme` (canvas/text/border/typography tokens) global; move layer-specific component classes to `canvas.css` / `inspector.css`.
- `hooks/useMeta`, `lib/queryKeys`, `types.ts` — genuinely shared → neutral `shared/` lib.
- `main.tsx`, `rootShell.tsx`, `session-canvas/route.ts` (`selectRootRoute`), `desktopHost.ts`, `browserIdentity.ts`, `ChannelBadge`, `TransportMattersIcon`, `icons`, `Toggle`, `WindowDragRegion` — routing-only shell / neutral chrome.

## B. Grooming inventory + disposition

1. **canvasStore vs canvasLabStore + 3-way route assembly** — **GROOM-FIRST.** Entirely inside Layer A (`session-canvas/model` + `session-canvas/lab`); the A/B cut never re-touches it.
2. **legacy/LegacyApp misnomer** (`route.ts` `RootRoute`/`selectRootRoute`, `rootShell` `routeComponents.legacy`, `uiStore` Route, `app.tsx` `App`) — **GROOM-FIRST.** Pure identifier rename `legacy`→`inspector`; de-risks Phase 2 by moving well-named files.
3. **useCanvasDropTargets raw `window.transportMattersDesktop`** (`session-canvas/dnd/useCanvasDropTargets`, two sites) — **GROOM-FIRST.** Route through existing `desktopHost.ts`; Layer-A-internal.
4. **api.ts god-client** — **SEPARATION-SEAM. ⚠ DOUBLE-WORK.** Splitting it by domain *is* the neutral division; grooming it first then splitting cuts the same file twice.
5. **dup mutation detectors + sampling/thinking hooks** (`components/detail/mutations`, `components/editor/useSamplingOverrides`/`useThinkingOverrides`) — **GROOM-FIRST**, *verify not cross-layer first*. All copies seen are within Layer B; if `session-canvas` also carries the logic it becomes a shared-util placement question (SEPARATION-SEAM).
6. **index.css 839 LoC** — **SEPARATION-SEAM (partition). ⚠ DOUBLE-WORK.** It is the one shared token+class file feeding both layers; partitioning tokens *is* the cut. Sub-note: pruning dead component classes is GROOM-FIRST-safe (shrinks the eventual cut) and independent.
7. **www test gaps** — **GROOM-FIRST.** Layer-local; add coverage for surfaces about to move so the move-map has a net.
8. **config dup across www/desktop** (`tsconfig.json`, `package.json`) — **DEFER.** Orthogonal to the www-internal A/B cut; a separate monorepo-config concern.

**Double-work flags: #4 (api.ts) and #6 (index.css)** — both ARE the separation seams; do not groom-then-cut.

## C. Ordered PR-sized plan

**Phase 1 (groom-first, each gated on `just check` + `just test`):**
1. Rename `legacy`→`inspector` (`route.ts`, `rootShell.tsx`, `uiStore`, `app.tsx`→`inspectorApp.tsx`).
2. Route `useCanvasDropTargets` desktop read through `desktopHost.ts`.
3. Consolidate `canvasStore`/`canvasLabStore` shells + unify 3-way route assembly.
4. De-dup inspector mutation/sampling/thinking hooks (after cross-layer check).
5. Prune dead `index.css` component classes (shrink only, no token partition).
6. Fill www test gaps for canvas components + inspector routes.

**Phase 2 (separation, assumes Phase 1 landed):**
- Create `www/src/canvas/` (Layer A), `www/src/inspector/` (Layer B), keep `main.tsx`+`rootShell.tsx`+`route.ts` as the routing-only shell.
- Move Layer A dirs/components and Layer B dirs/components per §A.
- Straddler divisions land **with** the move (they define the homes): split `api.ts` → `canvas/api` + `inspector/api` + `shared/apiCore`; split `index.css` → neutral base `@theme` + `canvas.css` + `inspector.css`; relocate `useMeta`/`queryKeys`/`types` to `shared/`.
- Add `www/src/canvas/CLAUDE.md` (Ark-in-launcher, Tailwind tokens, spatial pane/DnD/ambient, engine, theme pipeline) and `www/src/inspector/CLAUDE.md` (Tailwind, breakpoint/intercept list+detail+editor, uiStore).

**Ordering constraints:** P1.1 (rename) must precede shell extraction. #4/#6 partitions must land *inside* Phase 2, never as Phase 1 grooming.
