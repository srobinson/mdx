# TM UI separation scout

## A. Design system partition

Layer A, Ark canvas target: `www/src/session-canvas/**` with `SessionCanvasRoute`, `CanvasLabRoute`, `SessionCanvasStressRoute`, `CommandCenter`; `www/src/engine/**`; `www/src/ambient/**`; `www/src/theme/**`; `www/src/stores/themeStore`; canvas-only CSS under `session-canvas/**`. Ark usage is `CommandCenter` and `useLauncherRows` through `@ark-ui/react/combobox` and `@ark-ui/react/portal`. Canvas tokens are currently split across global `index.css` `@theme`, `index.launcher.css`, `session-canvas/canvas.css`, `session-canvas/launcher/launcher.css`, and runtime token application in `theme/theme.applyThemeTokens` plus `hooks/useThemeTokens`.

Layer B, Tailwind inspector target: `www/src/app.tsx` `App` and `BrowserAppShell`; `routeLayout.RouteLayout`; `components/ExchangeList`, `ExchangeDetail`, `ArmToggle`, `components/editor/**`, `components/detail/**`, `components/routes/**`; inspector hooks such as `useBreakpoint`, `useExchangeStream`, `useExchanges`, `useOverrides`; `stores/uiStore`. Tailwind has no `tailwind.config`; the active config is `www/vite.config.ts` with `tailwindcss()` and `www/src/index.css` with `@import "tailwindcss"` plus `@theme`.

Zero shared components is refuted. `components/ExchangeDetail` is imported by both `routeLayout.RouteLayout` and `session-canvas/viewers/resource/ProviderExchangeResourceViewer`. That pulls shared inspector components and hooks into A: `components/detail/*`, `components/editor/*`, `components/FullscreenOverlay`, `components/HoverCard`, `components/Toggle`, `hooks/useFullscreen`, `hooks/useMeta`, `hooks/useEditableOverride`, `hooks/useCollapsibleSet`, plus `api.ts`, `stores/uiStore`, `lib/*`, and `types/*`.

Straddlers: `rootShell.RootShell` should become routing only and stop applying `useThemeTokens`; `main.tsx` must stop importing both systems globally; `index.css` must split into neutral base, canvas tokens, inspector Tailwind theme; `api.ts` must split into neutral transport plus canvas and inspector clients; `desktopHost.ts` stays neutral and `useCanvasDropTargets` should call it; `engine/*` moves with canvas unless promoted as a style-free layout package.

## B. Grooming inventory

1. `canvasStore` versus `canvasLabStore` plus three canvas routes: GROOM-FIRST. A-local duplication. Double work: low.
2. `legacy` and `LegacyApp` names: SEPARATION-SEAM. Rename while creating the routing shell. Groom first double work: yes.
3. `useCanvasDropTargets` raw desktop bridge: GROOM-FIRST. Small boundary repair through `desktopHost`. Double work: no.
4. `api.ts` god-client: SEPARATION-SEAM. This is the home split. Groom first double work: yes.
5. Mutation detectors plus sampling/thinking hooks: GROOM-FIRST. B-local duplication. Double work: no.
6. `index.css` at 839 LOC: SEPARATION-SEAM. It holds both token systems. Groom first double work: yes.
7. www test gaps: GROOM-FIRST. Add invariants before moving files. Double work: low if assertions target symbols, not paths.
8. www/desktop config duplication: DEFER. Cross-package build shape should follow the UI boundary decision.

## C. Ordered PR sized plan

Phase 1, grooming first:
1. Canvas store and route grooming: `canvasStore`, `canvasLabStore`, `SessionCanvasRoute`, `CanvasLabRoute`, `SessionCanvasStressRoute`, `labBoundary.test`; gate `just check` and `just test`.
2. Desktop bridge seam: `desktopHost`, `useCanvasDropTargets`, `useCanvasDropTargets.test`; gate `just check` and `just test`.
3. Inspector override dedupe: `components/detail/mutations`, `useSamplingOverrides`, `useThinkingOverrides`, related tests; gate `just check` and `just test`.
4. Boundary tests: assert route names, no raw bridge reads, and current shared `ExchangeDetail` breach as a known failing target or todo; gate `just test`.

Phase 2, separation:
1. Create `www/src/shell`, `www/src/canvas/CLAUDE.md`, `www/src/inspector/CLAUDE.md`.
2. Move A to `canvas/`: `session-canvas`, `engine`, `ambient`, `theme`, `themeStore`, canvas CSS, Ark launcher code.
3. Move B to `inspector/`: `app`, `routeLayout`, inspector components, hooks, `uiStore`, Tailwind theme CSS.
4. Split `api.ts`, `index.css`, and `main.tsx`; keep shell routing-only.
5. Replace `ProviderExchangeResourceViewer -> ExchangeDetail` with a canvas-owned provider viewer or a neutral non-Tailwind data viewer before declaring zero shared components.

Hard ordering: Phase 1.1 before moving canvas; Phase 1.3 before moving inspector; Phase 2.5 before enforcing the shared-component ban.
