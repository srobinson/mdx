---
title: Transport Matters Keyboard Strategy Spec
type: spec
tags: [transport-matters, keyboard, cross-os, strategy, desktop]
summary: Desktop only keyboard foundation for the Electron canvas, launcher, panes, and dock, with a scalable renderer registry, per OS formatting, Escape arbitration, a gesture modifier store, and one initial Shift or Space canvas gesture setting.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-18
updated: 2026-06-18
---

# Cross OS Keyboard Strategy Spec

This is the authoritative desktop keyboard strategy for Transport Matters. It targets the Electron desktop app only: the canvas, launcher, panes, and dock. The intercept web app remains a separate concept and is untouched.

Inputs synthesized here, both authoritative:

- Audit: `~/.mdx/projects/transport-matters-keymap-audit.md`.
- Research: `~/.mdx/research/transport-matters-cross-os-keyboard-electron.md`.

Code claims were spot checked against the current tree. Citations use file plus symbol only, with no line anchors.

---

## 1. Locked scope: desktop only

Transport Matters has two separate user surfaces.

1. **Intercept web app.** `transport-matters claude` and `transport-matters codex` open the browser based intercept app. Its route tree is Intercept, Overlays, Trace, and Recall. Its route rail and route hotkeys stay as they are.
2. **Desktop app.** `transport-matters desktop` opens the Electron app. This is the canvas surface with launcher, panes, dock, and desktop shell behavior. This is the only target for the keyboard foundation.

### Verified entry and route split

- Desktop launches the hosted renderer at `/canvas`: `desktop/src/main.ts` · `startBackendAndCreateWindow` passes `rendererUrlForPort(options.webPort)` to the window creator, and `desktop/src/window.ts` · `rendererUrlForPort` defaults its route argument to `/canvas`. `desktop/src/window.ts` · `createHostedWindow` then loads that URL.
- The renderer entry mounts one shared root: `www/src/main.ts` · root render mounts `www/src/rootShell.tsx` · `RootShell`.
- `www/src/rootShell.tsx` · `RootShell` chooses the route by calling `www/src/session-canvas/route.ts` · `selectRootRoute`. `selectRootRoute` maps `/canvas` to the canvas branch, `/canvas-lab` to the lab branch, and every other path to the legacy branch.
- The desktop canvas branch mounts `www/src/session-canvas/SessionCanvasRoute.tsx` · `SessionCanvasRoute`, which returns `www/src/session-canvas/components/CanvasSurface.tsx` · `CanvasSurface`. `CanvasSurface` renders `www/src/session-canvas/launcher/CommandCenter.tsx` · `CommandCenter` and `www/src/session-canvas/components/PaneDock.tsx` · `PaneDock` inside the canvas surface.
- The intercept web app branch mounts `www/src/app.tsx` · `App`, which returns `www/src/app.tsx` · `BrowserAppShell`. `BrowserAppShell` calls `www/src/hooks/useRouteHotkeys.ts` · `useRouteHotkeys` and renders `www/src/routeLayout.tsx` · `RouteLayout`. `RouteLayout` renders `www/src/components/RouteRail.tsx` · `RouteRail` for Intercept, Overlays, Trace, and Recall.

**Mount point.** The desktop keybinding system mounts on the desktop branch, as a provider around or inside `SessionCanvasRoute` before `CanvasSurface` renders. It must not mount in `BrowserAppShell`, `RouteLayout`, `RouteRail`, or `useRouteHotkeys`. If a later desktop route is added, the provider moves to a desktop shell that wraps only desktop routes.

### Seed, not ceiling

The current desktop shortcut set is small: the launcher trio, Escape arbitration, and one canvas pan or zoom gesture modifier setting. That set is the seed, not the ceiling. The desktop will accumulate shortcuts as the canvas, panes, resources, and launch flows grow. The foundation is therefore general infrastructure, not a handful of special cases.

Adding a future desktop command should be one registry entry. Making a future command user configurable should be one `configurable` flag plus settings UI exposure. The initial visible configuration remains intentionally narrow.

---

## 2. Goals and non goals

### Goals

1. **Desktop ownership.** Centralize desktop app shortcuts only. Leave the intercept web app and route hotkeys unchanged.
2. **Scalable registry.** Build a renderer owned command registry and engine that support N desktop commands, even though the initial command set is small.
3. **Per OS labels.** Use one formatter for macOS symbols and Windows or Linux word labels.
4. **One platform source.** Derive `$mod` from the desktop preload platform signal and precompile it before tinykeys sees bindings.
5. **Escape arbitration.** Preserve command center capture behavior and move bubble phase Escape ownership into the registry.
6. **Gesture clarity.** Keep held mouse gesture modifiers separate from discrete key commands.
7. **One initial setting.** Expose only the canvas mouse pan or zoom activation modifier, default `Shift`, settable to `Shift` or `Space`.

### Non goals

- No intercept web app changes.
- No `RouteRail` changes.
- No `useRouteHotkeys` changes.
- No route command migration.
- No native menu. Treat it as a hard non goal, probably never.
- No `globalShortcut`.
- No command remapping UI in the first desktop slice.
- No canvas keyboard zoom or pan migration yet.
- No lab migration. `CanvasLabRoute` is being removed soon.
- No changes to Ark, zag, palette query grammar, viewer local roving handlers, ARIA activation handlers, or exported inspect HTML.

### No macOS bug framing

The current launcher accelerators are already cross OS correct. `www/src/session-canvas/launcher/useLauncherHotkeys.ts` · `useLauncherHotkeys` gates on `metaKey || ctrlKey` and excludes `altKey`. The value here is removing future drift and creating a desktop foundation for growth.

---

## 3. Architecture

A renderer owned, layered system under `www/src/keybindings/`. The directory does not exist today and no keyboard library is in `www` dependencies.

| Module | Responsibility |
|---|---|
| `platform` | Resolve `isMac` and `$mod` once at startup from the desktop bridge platform field, with browser fallback for development. |
| `format` | `formatBinding(tokens, platform)`: the only function that turns binding tokens into labels. |
| `registry` | `COMMANDS`: declarative desktop app commands. The initial registry contains the launcher trio and bubble phase Escape commands. |
| `engine` | Dispatcher service. Precompiles `$mod`, builds the tinykeys map, evaluates `when` gates and `priority`, owns bubble phase Escape, and dispatches one command per event. |
| `overrides` | General sparse command override machinery for future N command remapping. The current UI exposes no command remaps. A command becomes eligible later by setting `configurable: true`. |
| `gestures` | Held modifier store for canvas mouse pan or zoom activation, initially `Shift` or `Space`, plus the shared pane drag suppression predicate. |
| `preferences` | Zustand persisted preferences using the theme persistence pattern. Initial active field: `canvasGestureModifier`. Future command overrides can live beside it without changing the engine contract. |

### Command shape

```ts
type Command = {
  id: string
  title: string
  category: string
  defaultKeys: string[]
  when?: ContextPredicate
  configurable?: boolean
  priority?: number
  run: (ctx: CommandContext) => void
}
```

`when`, `priority`, and `configurable` remain general. Current commands can all have `configurable: false`; the infrastructure still supports future configurable commands by flipping that flag.

---

## 4. Cross OS modifier and label model

- **Single `$mod` source.** App level chords are authored with `$mod`, never literal platform checks. `engine` precompiles `$mod` to `Meta` on macOS and `Control` on Windows or Linux before building the tinykeys map. This prevents tinykeys from consulting a different platform source than labels.
- **Preload platform signal.** Extend the existing desktop bridge, `desktop/src/preload.cts` · `desktopApi`, exposed under `desktop/src/main.ts` · `DESKTOP_PRELOAD_BRIDGE_KEY`, with a platform field derived from Node `process.platform`. The bridge already exists, so this is additive.
- **Browser fallback.** Browser development has no desktop bridge. `platform` falls back to `navigator.userAgentData?.platform || navigator.userAgent` only when the bridge is absent.
- **One formatter.** `formatBinding(tokens, platform)` emits Apple symbolic order on macOS, for example `⇧⌘K`, and word labels on Windows or Linux, for example `Ctrl+Shift+K`. No call site formats labels by hand.
- **General formatting.** `format` accepts any future command binding. It is not hardcoded to the initial launcher and Escape set.

---

## 5. Current migration map

The table below is the locked current scope. It maps audited surfaces to active migration, deferred work, or explicit out of scope status.

### Active desktop registry commands

| Surface | Current source | Keys | Disposition |
|---|---|---|---|
| Launcher toggle | `www/src/session-canvas/launcher/useLauncherHotkeys.ts` · `useLauncherHotkeys` | `$mod+K` | registry command `launcher.toggleRoot` |
| Agents scope | `useLauncherHotkeys` | `$mod+A` | registry command `launcher.openAgents` |
| Settings scope | `useLauncherHotkeys` | `$mod+,` | registry command `launcher.openSettings` |
| Dock Escape | `www/src/session-canvas/components/PaneDock.tsx` · `PaneDock` | `Escape` | registry command `ui.closeDock` |
| Fullscreen Escape | `www/src/hooks/useFullscreen.ts` · `useFullscreen` | `Escape` | registry command `ui.exitFullscreen` |

The launcher trio is behavior preserving. The Escape commands preserve the current effects while adding one explicit ordering contract.

### Active gesture and shared interaction work

| Surface | Current source | Trigger | Disposition |
|---|---|---|---|
| Canvas mouse pan readiness | `www/src/engine/react/useCanvasViewport.ts` · `useCanvasViewport` | held modifier | gesture store, default `Shift`, user selectable `Shift` or `Space` |
| Canvas drag pan | `useCanvasViewport` | modifier plus drag | reads gesture store |
| Canvas wheel zoom | `useCanvasViewport` | modifier plus wheel | reads gesture store |
| Pane drag suppression | `www/src/engine/react/PaneFrame.tsx` · `PaneFrame` | modifier held | shared `shouldPanNotDrag` predicate |
| Pane drag sensor suppression | `www/src/session-canvas/dnd/paneDragPointerSensor.ts` · `paneDragPointerSensor` | modifier held | shared `shouldPanNotDrag` predicate |
| Live pane header activation | `www/src/session-canvas/components/CanvasSurface.tsx` · `CanvasSurface` | modifier plus header double click | live canvas only; no lab dedupe target remains after lab removal |

### Deferred desktop work

| Surface | Current source | Reason |
|---|---|---|
| Canvas keyboard zoom in and out | `www/src/engine/react/useCanvasViewport.ts` · `useCanvasViewport` | Deferred. Keep current `+`, `=`, and `-` behavior. |
| Canvas keyboard pan | `useCanvasViewport` | Deferred. Keep current `Alt` plus Arrow behavior for now. The Alt collision and a11y rebind are not in the active scope. |
| Keyboard layout map labels | future `format` extension | Deferred. Keep the formatter shaped so `navigator.keyboard.getLayoutMap()` can be added later. |

### Out of scope, untouched

| Surface | Current source | Disposition |
|---|---|---|
| Intercept web routes | `www/src/hooks/useRouteHotkeys.ts` · `useRouteHotkeys` | Out. Separate intercept web app concept. No migration. |
| Route rail | `www/src/components/RouteRail.tsx` · `RouteRail` | Out. Separate intercept web app concept. No migration. |
| Legacy route layout | `www/src/routeLayout.tsx` · `RouteLayout` | Out. Separate intercept web app concept. No migration. |
| Lab Tab toggle | `www/src/session-canvas/lab/CanvasLabRoute.tsx` · `CanvasLabRoute` | Dropped with lab removal. No migration. |
| Lab header double click | `CanvasLabRoute` | Dropped with lab removal. No migration. |
| Command center Ark keys | `www/src/session-canvas/launcher/CommandCenter.tsx` · `CommandCenter` | Ark and zag own listbox keys. Leave local. |
| Command center Escape capture | `www/src/session-canvas/launcher/useCommandCenter.ts` · `useCommandCenter` | Preserve capture handler. Registry listens in bubble phase only. |
| Palette query grammar | `useCommandCenter` | Input scoped grammar. Leave local. |
| Viewer local roving | `www/src/session-canvas/viewers/session-picker/SessionPickerPane.tsx` · `handlePickerKey` | Leave local. |
| Image viewer zoom | `www/src/session-canvas/viewers/resource/ImageResourceViewer.tsx` | Leave local. |
| ARIA activation | `www/src/components/Toggle.tsx` · `handleKey`; `www/src/components/detail/atoms.tsx`; `www/src/components/editor/EditorLedger.tsx` | Leave local. |
| Exported inspect HTML | `www/src/lib/exportInspect.ts` · `EXPORT_COLLAPSE_SCRIPT` | Runs in exported static HTML, outside the live app. |
| Native menu | desktop main process | Hard non goal. |

---

## 6. Dispatcher and Escape ordering contract

One dispatcher in `engine` owns desktop app key handling. It installs exactly one registry `window` keydown listener in the bubble phase on the desktop route.

- **Single matcher.** The engine builds one tinykeys map from `registry` plus future overrides. It reuses `www/src/lib/domFocus.ts` · `isEditableTarget` for editable target yield.
- **Context gates.** `when` predicates prevent global commands from competing with modal or component owned contexts.
- **Priority.** When several commands share a combo in the same context, the engine fires only the highest priority command whose `when` predicate is true.
- **Future command path.** Adding a desktop command means appending one `Command` entry. No switch statement should special case the initial set.

### Escape order

Escape has multiple owners today. The desktop contract is:

1. Palette first. `www/src/session-canvas/launcher/useCommandCenter.ts` · `useCommandCenter` keeps the capture phase window listener and calls `stopPropagation` while the palette is open.
2. Dock second. `ui.closeDock` runs when the dock is open and the palette is closed.
3. Fullscreen last. `ui.exitFullscreen` runs when fullscreen is active and neither palette nor dock is open.

Bubble phase registry listening is required. A captured and stopped palette Escape never reaches the registry. `when` predicates also stand down dock and fullscreen while the palette is open.

---

## 7. Gesture modifier and initial setting

The gesture store holds the canvas mouse pan or zoom activation modifier. Current behavior uses `Shift`; the setting lets the user choose `Shift` or `Space`.

```ts
type CanvasGestureModifier = "Shift" | "Space"
```

Rules:

- Default is `Shift`.
- Only `Shift` and `Space` are allowed.
- The setting affects mouse drag pan, wheel zoom, and pane drag suppression.
- The setting does not migrate canvas keyboard zoom or keyboard pan.
- The store resets held modifier state on `window` blur.
- Bare modifiers never call `preventDefault`.
- The setting persists through the theme store pattern: `www/src/stores/persistence.ts` · `FRONTEND_STORAGE_KEYS`, Zustand `persist`, `createFrontendPersistStorage`, explicit store `version`, and a migrate or validate seam modeled on `www/src/stores/themeStore.ts` · `migrateThemeState`.

No other command is configurable in the current surface. The command override machinery stays general so future commands can become configurable without changing architecture.

---

## 8. Accessibility and collision posture

- **Routes.** No route shortcut change. The intercept web app keeps `useRouteHotkeys` and `RouteRail` as is.
- **Lab.** No Tab fix is required in this keyboard foundation because `CanvasLabRoute` is being removed soon. Do not migrate lab behavior.
- **Canvas keyboard pan.** `Alt` plus Arrow remains deferred. The collision with browser Back and Forward is recorded, but the rebind is not in the active scope.
- **Reserved combos.** The future override validator must reject OS and browser reserved combos before a command can be saved as configurable.
- **Component ownership.** Ark, zag, roving listbox handlers, and ARIA activation handlers keep local keyboard ownership.

---

## 9. Electron main process boundary

No native menu and no `globalShortcut`. The desktop keyboard system is renderer owned.

---

## 10. Resolved decisions

- **(a) Native menu.** Dropped. Hard non goal, probably never.
- **(b) Storage.** Use renderer `localStorage` through the existing frontend persistence pattern.
- **(c) Configurable surface.** Exactly one current setting: canvas mouse pan or zoom activation modifier, `Shift` or `Space`.
- **(d) Leader key.** Moot for this scope. Route hotkeys belong to the intercept web app and stay untouched.
- **(e) Keyboard layout map.** Deferred. Keep `format` extensible for a future optional layout map.

---

## 11. Implementation phasing

Each slice is PR sized and gates on the repo recipes verbatim: `just check`, `just test`, and `just test-e2e`.

1. **Platform and format.** Add `platform` and `format` plus tests. Extend `desktop/src/preload.cts` · `desktopApi` under `transportMattersDesktop` with `platform`. No behavior change.
2. **Registry and engine.** Add tinykeys, `registry`, and `engine`. Migrate the launcher trio and bubble phase Escape commands. Preserve `useCommandCenter` capture phase Escape. No route work.
3. **Gesture store and predicate dedupe.** Add `gestures`, blur reset, the `Shift` or `Space` canvas gesture modifier, and shared `shouldPanNotDrag`. Keep canvas keyboard zoom and pan unchanged. Reduce header activation scope to the live `CanvasSurface`; lab is not migrated.
4. **Settings picker and persistence.** Add the settings control for `Shift` or `Space`, persist it through `FRONTEND_STORAGE_KEYS` plus Zustand persist, and test reload behavior. Do not add command remapping UI yet.

---

## 12. Testing strategy

Use repo recipes, not hand rolled equivalents.

**Unit via `just test`:**

- `formatBinding`: macOS symbolic labels and Windows or Linux word labels.
- `$mod` precompile: macOS maps to `Meta`, Windows and Linux map to `Control`.
- Launcher commands: `$mod+K`, `$mod+A`, and `$mod+,` preserve current behavior and editable target yielding.
- Escape ordering: palette capture wins, then dock, then fullscreen.
- Gesture store: `Shift` default, `Space` option, blur reset, invalid persisted values reset cleanly.
- `shouldPanNotDrag`: pane drag suppression follows the selected gesture modifier.

**End to end via `just test-e2e`:**

- Desktop `/canvas` route opens the command center with `$mod+K`.
- Escape closes palette before dock or fullscreen.
- Settings can switch the canvas gesture modifier to `Space`, persist, reload, and preserve behavior.
- `Shift` remains the default on a fresh profile.

---

## 13. Review risks

- Do not touch `useRouteHotkeys`, `RouteRail`, or `RouteLayout`.
- Do not mount the desktop keybinding provider on the legacy web app branch.
- Do not shrink the registry or formatter to only the current seed commands.
- Do not add native menu or `globalShortcut` work.
- Do not migrate lab behavior.
- Do not migrate canvas keyboard zoom or pan in this scope.
- Do not introduce command remapping UI beyond the one gesture modifier setting.
- Do not create a second label formatter.
- Do not let Escape run in capture phase from the registry.
- Do not leave duplicate modifier logic in pane dragging once the gesture store lands.
