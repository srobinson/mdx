# TM UI scout health

Verdict: groom-first.

## Sizing

Minor. No production TS/TSX file in `www/src` or `desktop/src` is over 700 LoC. Biggest source files are `www/src/session-canvas/launcher/commandModel.ts`, `www/src/api.ts`, and `desktop/src/main.ts`. Handwritten file over the limit: `www/src/index.css` at 839 LoC. Test files over the limit: `www/src/components/ExchangeDetail.test.tsx` and `www/src/session-canvas/launcher/commandModel.test.ts`.

Functions over or near 150 LoC: `www/src/components/ExchangeDetail.tsx#ExchangeDetail`, `www/src/session-canvas/model/canvasStore.ts#useCanvasStore`, `www/src/session-canvas/lab/canvasLabStore.ts#useCanvasLabStore`, `www/src/components/detail/ExchangeCard.tsx#ExchangeCard`, `www/src/components/editor/useThinkingOverrides.ts#useThinkingOverrides`, `www/src/engine/react/PaneFrame.tsx#PaneFrame`, `www/src/session-canvas/lab/CanvasLabRoute.tsx#CanvasLabRoute`, `www/src/components/editor/BreakpointEditorActions.ts#useBreakpointEditorActions`, `www/src/components/routes/OverlaysView.tsx#DraftState`. No desktop function is near the threshold; `desktop/src/main.ts#registerAppLifecycle` is the largest.

## Duplication and parallel implementations

Major. The largest drift risk remains `www/src/session-canvas/model/canvasStore.ts#useCanvasStore` versus `www/src/session-canvas/lab/canvasLabStore.ts#useCanvasLabStore`: both own pane lifecycle, captured run spawn, dock, restore, expand, frame, and persistence decisions. `www/src/session-canvas/model/worktreeDefaults.ts#adoptDefaultWorktreePatch` is shared, but the store shells are still parallel.

Major. Route assembly is also forked across `www/src/session-canvas/SessionCanvasRoute.tsx#SessionCanvasRoute`, `www/src/session-canvas/lab/CanvasLabRoute.tsx#CanvasLabRoute`, and `www/src/session-canvas/perf/SessionCanvasStressRoute.tsx#SessionCanvasStressRoute`.

Minor. Repeated mutation detectors live in `www/src/components/detail/mutations.ts#detectMessageMutations` and `www/src/components/detail/mutations.ts#detectMessageMutationsStructural`, with matching system, tool, and tool result pairs. Sampling hooks repeat shape in `www/src/components/editor/useSamplingOverrides.ts#useSamplingOverrides` and `www/src/components/editor/useThinkingOverrides.ts#useThinkingOverrides`.

## Dead code

Major. No active `www/src` or `desktop/src` reference to retired `/api/index`, raw fetch, blocks, or diff endpoints was found. The dead-code risk is the still-wired legacy shell: `www/src/rootShell.tsx#routeComponents` keeps `legacy: LegacyApp`, `www/src/session-canvas/route.ts#selectRootRoute` sends every non canvas path there, and `www/src/stores/uiStore.ts#Route` still exposes `overlays`, `trace`, and `recall`.

## Boundary leaks

Major. `desktop/src/main.ts` stays inside desktop dependencies. The leak is opposite: `www/src/session-canvas/dnd/useCanvasDropTargets.ts#useCanvasDropTargets` reads `window.transportMattersDesktop` directly instead of going through `www/src/desktopHost.ts#DESKTOP_BRIDGE_KEY`. Major. `www/src/api.ts` mixes breakpoint, legacy exchange, managed run, spaces, and runtime template clients and is imported by session canvas API wrappers.

## Test shape

Minor. File presence shows 162 `www` tests and 10 `desktop` tests. `www/src/session-canvas` has 69 tests across 101 source files; `model` has 9 and `lab` has 6. Gaps before new UI work: `www/src/session-canvas/launcher/CommandCenter.tsx`, `www/src/session-canvas/launcher/useLauncherRows.ts`, `www/src/session-canvas/launcher/workdirRows.ts`, `www/src/session-canvas/launcher/FirstRunHint.tsx`, `www/src/session-canvas/api/sessionEvents.ts`, `www/src/session-canvas/api/resourceContent.ts`, `www/src/session-canvas/hooks/useSessionEvents.ts`, `www/src/session-canvas/hooks/useResourceContent.ts`, `www/src/session-canvas/lab/ControlsPanel.tsx`, and `www/src/session-canvas/viewers/terminal/terminalSession.ts`.

## Config sprawl

Minor. Active config count is nine: `www/package.json`, `www/vite.config.ts`, three `www/tsconfig*.json`, `desktop/package.json`, `desktop/vitest.config.ts`, and two `desktop/tsconfig*.json`. The split is understandable, but TypeScript and Vitest dev dependencies are duplicated across both packages.
