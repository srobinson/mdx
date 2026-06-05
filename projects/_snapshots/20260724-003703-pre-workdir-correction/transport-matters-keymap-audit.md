---
title: Transport Matters — Keyboard Interaction Surface Inventory
type: project
tags: [transport-matters, keyboard, audit]
summary: Complete per-symbol inventory of every keyboard interaction in www/ + desktop/, classified for a centralized cross-OS keyboard strategy. 25 surfaces; desktop has no keyboard layer; accelerators are already cross-OS correct but reimplemented across ~7 uncoordinated window listeners.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-18
updated: 2026-06-18
---

# Keyboard Interaction Surface Inventory

Read-only audit of every keyboard interaction in the repo, to inform one centralized, DRY, cross-OS keyboard system. Electron app: renderer in `www/`, thin shell in `desktop/`. All citations are file + symbol (no line anchors).

## Top findings

1. **No keyboard layer exists in `desktop/` at all.** No `Menu` accelerators, no `globalShortcut`, no `before-input-event`. `desktop/src/window.ts` only registers `will-navigate` and `setWindowOpenHandler`. Every keyboard interaction is renderer-side. A cross-OS strategy is therefore purely a renderer concern today; any OS-native menu accelerator (e.g. surfacing ⌘K in the app menu) would be net-new code in `desktop/src/main.ts` / `window.ts`.
2. **Discrete accelerators are already cross-OS correct — no macOS-only `metaKey` bug.** Both accelerator surfaces gate on `metaKey || ctrlKey` (`useLauncherHotkeys`) or use no modifier at all (`useRouteHotkeys` digit/leader). The risk is not a current bug, it is *future drift*: the cross-OS modifier guard, the `isEditableTarget` yield, and Escape handling are reimplemented across ~7 independent `window` `keydown` listeners with no central dispatcher, no priority, and no ordering contract. **Escape alone is handled by three independent listeners** (`useFullscreen`, `PaneDock`, `useCommandCenter`).
3. **Persistence pattern to mirror** = Zustand `persist` middleware + `createFrontendPersistStorage` + the `FRONTEND_STORAGE_KEYS` registry + per-store `version` + `migrate` function, with a `validate`/`normalize` seam (theme uses `validateThemeDefinition` + `normalizeLegacyTheme`). There is **no Settings page**; "settings" is a launcher command-center scope (`buildSettingsRows`) plus the `SceneParamControls` slider panel. A future user-configurable shortcuts store slots directly into this pattern.

Smaller flags: **Alt+Arrow canvas pan** (`useCanvasViewport.handleKeyDown`) can collide with browser/OS history nav (Alt+Left = Back on Win/Linux). **Tab-hijack** in `CanvasLabRoute` (`preventDefault` on bare Tab) is an a11y/focus-traversal concern. The **shift-suppresses-pane-drag** rule is duplicated across three sites.

---

## A. Discrete accelerators (global `window` keydown)

Category `discrete-accelerator`. These are the primary centralization targets.

| File · symbol | Keys | Modifiers | Does | Platform-correctness | Centralize | User-config candidate |
|---|---|---|---|---|---|---|
| `useLauncherHotkeys` (`session-canvas/launcher/useLauncherHotkeys.ts`) | `K` | `meta` OR `ctrl`, not `alt` | `toggleRoot()` — open/toggle command center at root scope | **Correct.** `metaKey \|\| ctrlKey`, excludes `altKey` | **Yes** — flagship accelerator | Yes |
| `useLauncherHotkeys` | `A` | `meta` OR `ctrl` | `openScope("agents")`, only while palette closed AND `!isEditableTarget` (yields ⌘A Select-All) | **Correct.** Cross-OS + editable guard | **Yes** | Yes |
| `useLauncherHotkeys` | `,` | `meta` OR `ctrl` | `openScope("settings")` from anywhere (incl. while typing) | **Correct.** `,` has no native text role | **Yes** | Yes (⌘, is a macOS Preferences idiom; Ctrl+, is fine elsewhere) |

Note: this surface re-derives the cross-OS guard `(metaKey || ctrlKey) && !altKey` inline. It is the canonical correct form to lift into a shared matcher.

---

## B. Route accelerators (global `window` keydown — `useRouteHotkeys`)

Category `route`. File: `hooks/useRouteHotkeys.ts`, symbol `useRouteHotkeys`. Guarded by `isEditableTarget(e.target)` and **returns early if any of `metaKey`/`ctrlKey`/`altKey` is held** (plain unmodified keys only).

| Keys | Modifiers | Does | Platform-correctness | Centralize | User-config candidate |
|---|---|---|---|---|---|
| `1` `2` `3` `4` | none | `setActiveRoute` → intercept / overlays / trace / recall | **Correct.** No modifier; editable-guarded | **Yes** | Yes |
| `g` then `i`/`o`/`t`/`r` | none | vim leader; same four routes; leader resets after 900ms | **Correct.** No modifier; editable-guarded | **Yes** | Maybe (leader timing/binding) |

**RouteRail reconciliation:** `components/RouteRail.tsx` (symbol `RouteRail`) has **no** keyboard handler — it is pure click navigation (renders the four route buttons; click → `onActiveRouteChange`). All keyboard route-switching lives solely in `useRouteHotkeys`. `RouteRail.test.tsx` co-locates both: it `renderHook(useRouteHotkeys)` and fires `keyDown(window, {key:"2"})` etc. The `keyDown(window, {key:"2", metaKey:true})` case asserts `activeRoute` **stays** `intercept` — it is a *proof of the modifier early-return guard*, not a competing binding. **No duplication, no conflict.**

---

## C. Modifier-held continuous gestures (NOT accelerators)

Category `modifier-held-gesture`. The held modifier gates a pointer/wheel gesture; these should **not** be centralized into an accelerator registry.

| File · symbol | Modifier / keys | Does | Platform | Centralize | Config |
|---|---|---|---|---|---|
| `useCanvasViewport` (`engine/react/useCanvasViewport.ts`), the `sync` effect | `Shift` (keydown/keyup + `blur` clear) | Sets `panReady` so grab cursor appears the moment Shift is down | Shift is universal — correct | **No** | No |
| `useCanvasViewport`, `bindViewport` (`useDrag`) | `Shift` + drag | Shift+drag pans the canvas (plain drag belongs to a pane) | Correct | **No** | No |
| `useCanvasViewport`, `handleWheel` | `Shift` + wheel | Shift+wheel zooms at cursor | Correct | **No** | No |
| `PaneFrame` (`engine/react/PaneFrame.tsx`), `useDrag` callback | `Shift` (suppresses) | If `shiftKey`, abort pane drag so canvas pan wins | Correct | **No** | No |
| `paneDragPointerSensor` (`session-canvas/dnd/paneDragPointerSensor.ts`) | `Shift` (suppresses) | dnd-kit sensor returns `false` when `shiftKey` (same rule as PaneFrame) | Correct | **No** | No |

**DRY note:** the rule "Shift means canvas-pan, not pane-drag" is encoded independently in `PaneFrame`, `paneDragPointerSensor`, and `useCanvasViewport`. One conceptual binding, three sites — a candidate for a single shared predicate even though it is gesture-gating, not an accelerator.

---

## D. Canvas keyboard zoom/pan (element-scoped keydown)

Category between `viewer-local` and `discrete-accelerator`. Bound on the canvas element via `LayoutCanvas` (`onKeyDown={handleKeyDown}`), source in `useCanvasViewport.handleKeyDown`.

| Keys | Modifiers | Does | Platform-correctness | Centralize | Config |
|---|---|---|---|---|---|
| `+` / `=` | none | Keyboard zoom in (centered) | Correct (element-scoped) | Maybe (low priority — element-scoped) | Yes |
| `-` | none | Keyboard zoom out | Correct | Maybe | Yes |
| `Alt` + Arrow (`Left`/`Right`/`Up`/`Down`) | `Alt` | Pan canvas by `KEYBOARD_PAN_STEP` | **Flag:** `Alt+Left/Right` collides with browser/OS history Back/Forward on Win/Linux | Maybe | Yes (rebind away from Alt+Arrow) |

---

## E. Discrete local / global single-key handlers

| File · symbol | Keys | Modifiers | Category | Does | Platform | Centralize | Config |
|---|---|---|---|---|---|---|---|
| `useFullscreen` (`hooks/useFullscreen.ts`) | `Escape` | none | discrete (window) | Exit fullscreen | Correct | Maybe | No (Escape conventional) |
| `PaneDock` (`session-canvas/components/PaneDock.tsx`) `onKeyDown` effect | `Escape` | none | discrete (window) | Close the minimized-panes dock | Correct | Maybe | No |
| `CanvasLabRoute` (`session-canvas/lab/CanvasLabRoute.tsx`) `onKeyDown` effect | `Tab` | none (returns if meta/ctrl/alt) | discrete (window) | `preventDefault` + toggle/hide top-bar (experimental cockpit) | **Flag:** hijacks Tab focus traversal — a11y risk | Maybe | No |
| `CanvasLabRoute`, `onHeaderDoubleClick` | `Shift` + header dblclick | `Shift` | viewer-local (mouse+mod) | `expandPane` else `framePane` | Correct | No | No |
| `CanvasSurface` (`session-canvas/components/CanvasSurface.tsx`), `onHeaderDoubleClick` | `Shift` + header dblclick | `Shift` | viewer-local (mouse+mod) | `expandPane` else `framePane` — **identical to CanvasLabRoute** | Correct | No | No |

**DRY note:** `Shift+header-doubleclick → expand` is duplicated verbatim across `CanvasLabRoute` and `CanvasSurface`.

**Escape coordination:** three independent `window`/element Escape handlers exist (`useFullscreen`, `PaneDock`, `useCommandCenter` capture). No shared ordering — a central layer should arbitrate Escape precedence (palette > dock > fullscreen, or by visibility).

---

## F. Viewer-local element handlers (roving / activation)

Category `viewer-local`. Bound on a specific element's `onKeyDown`; should stay local (focus-scoped patterns), not centralized.

| File · symbol | Keys | Does | Centralize |
|---|---|---|---|
| `SessionPickerPane` (`...viewers/session-picker/SessionPickerPane.tsx`), `handlePickerKey` (fieldset `onKeyDown`) | `ArrowDown` / `ArrowUp` / `Enter` | Move selection; Enter → `spawnOrFocusTranscript` (roving listbox) | **No** |
| `ImageResourceViewer` (`...viewers/resource/ImageResourceViewer.tsx`), `onKeyDown` (button) | `+`/`=` , `-` , `0` | Zoom in / out / reset | **No** (mirrors canvas zoom keys — keep consistent for any rebind) |

---

## G. Component-internal ARIA activation (`role="button"` Space/Enter)

Category `lib-internal` / component-internal. Standard ARIA keyboard activation; do not centralize.

| File · symbol | Keys | Does |
|---|---|---|
| `Toggle` (`components/Toggle.tsx`), `handleKey` | `Space` / `Enter` | Activate the toggle button |
| `components/detail/atoms.tsx` (two `onKeyDown` on role=button atoms) | `Enter` / `Space` | Activate |
| `EditorLedger` (`components/editor/EditorLedger.tsx`) `onKeyDown` | `Enter` / `Space` | Activate ledger control |

---

## H. Library-internal & palette grammar (DO NOT centralize)

| File · symbol | Keys | Does | Why off-limits |
|---|---|---|---|
| `CommandCenter` (`session-canvas/launcher/CommandCenter.tsx`) — Ark UI / zag combobox | Arrows / Enter / Escape (internal) | Listbox navigation + dismissal | Owned by Ark UI internally — document as `lib-internal`, do not reimplement |
| `useCommandCenter` (`session-canvas/launcher/useCommandCenter.ts`), `onEscapeCapture` | `Escape` | Closes the whole palette from any state; `window` listener in **capture phase** (`true`) that runs before Ark's document-level handler, then `stopPropagation` | Deliberate capture-phase override coordinating with Ark. **A central dispatcher MUST preserve window-capture-before-document ordering or palette Escape breaks.** Active only while open |
| `useCommandCenter`, `onInputKeyDown` (input `onKeyDown`) | `ArrowRight` (caret at end), `ArrowLeft` (caret 0), `Backspace` (empty query) | ArrowRight accepts ghost-completion / runs `enter` action; ArrowLeft/Backspace pop scope to root | Palette query grammar, input-scoped |

---

## I. Exported-artifact handler (noted, out of scope)

| File · symbol | Keys | Does | Note |
|---|---|---|---|
| `exportInspect.ts` (`lib/exportInspect.ts`), `EXPORT_COLLAPSE_SCRIPT` | `Enter` / `Space` | Toggle collapsible sections (`role=button` headers) | Inline JS embedded as a **string** into the standalone exported inspect HTML (`renderToStaticMarkup`). Runs in the exported document, **not** the live app. Do not centralize |

---

## Persistence pattern to mirror (for a future shortcuts store)

Source: `stores/persistence.ts`, `stores/themeStore.ts`, `theme/`.

- **Storage helper:** `createFrontendPersistStorage<S>()` wraps `createJSONStorage` over `globalThis.localStorage` (`stores/persistence.ts`). Quota/availability failures are swallowed (`getAvailableStorage`, `markPanelDismissed`).
- **Key registry:** `FRONTEND_STORAGE_KEYS` (`stores/persistence.ts`) — a central `as const` map of store name → localStorage key. Current members: `uiStore`, `themeStore`, `overlaysStore`, `capturedRunStore`, `canvasStore`, `canvasLabStore`, plus `dismissedPanelPrefix`. A shortcuts store adds e.g. `keymapStore: "transport-matters-keymap"` here.
- **Store shape (mirror this):** `useThemeStore = create<ThemeState>()(persist(initializer, { name: FRONTEND_STORAGE_KEYS.themeStore, version: 1, migrate: migrateThemeState }))`. The persisted slice is a `Pick<>` (`PersistedThemeSlice`), not the whole state.
- **Migrate/validate seam:** `migrateThemeState` (rehydration normalizer, the "third persistence seam"), `migrateTheme` → `normalizeLegacyTheme` (`theme/migrate.ts`), and `validateThemeDefinition` (`theme/validate.ts`, ~257 LOC of normalize/validate) + `isRecord` type guard (`theme/types.ts`). This is the model for validating a hand-edited or version-bumped keymap on load.
- **Three Zustand `persist` stores exist:** `themeStore`, `uiStore`, `overlaysStore`. `themeStore` has the richest `version` + `migrate` + `validate` discipline — use it as the template.

**Settings UI:** there is **no** standalone Settings route/page. The launcher command center has a `settings` scope (`commandModel.ts`, `buildSettingsRows(themeName)`, reachable via ⌘,). Live theme tuning is `SceneParamControls` (`session-canvas/components/SceneParamControls.tsx`) — data-driven sliders writing `settings.sceneParams` through `useThemeStore`. A user-configurable shortcuts surface would either become a new launcher scope or a settings panel alongside `SceneParamControls`.

## Desktop keyboard layer

**None.** `desktop/src/` (`main.ts`, `window.ts`, `backendProcess.ts`, `backendHealth.ts`, `packageSmoke.ts`, `env.ts`) defines **no** `Menu` accelerators, **no** `globalShortcut`, and **no** `before-input-event`. The only `webContents` listeners are navigation guards in `window.ts` (`will-navigate`, `setWindowOpenHandler`, `preload-error`/`did-finish-load` in `main.ts`). Confirmed by grep over `desktop/src`. All keyboard behavior is renderer-owned.

## Implications for a centralized cross-OS keyboard system

1. **Single matcher.** Lift the `(metaKey || ctrlKey) && !altKey` cross-OS guard from `useLauncherHotkeys` and the `meta/ctrl/alt` early-return from `useRouteHotkeys` into one shared chord matcher. Today they are independently correct but will drift.
2. **One dispatcher, explicit ordering.** Replace the ~7 independent `window` `keydown` listeners (launcher, route, fullscreen, paneDock, canvasLab Tab, canvasViewport shift-sync, commandCenter Escape-capture) with one registry that owns priority. Escape is the acute case (three handlers). Preserve `useCommandCenter`'s **capture-phase** precedence over Ark.
3. **Keep gestures out.** Modifier-held gestures (Sections C, the canvas pan/zoom in D), roving viewer handlers (F), ARIA activation (G), Ark internals + palette grammar (H), and the exported-artifact handler (I) are not accelerators and should be excluded from the registry.
4. **Reuse `isEditableTarget`** (`lib/domFocus.ts`) as the central editable-yield guard — it is already the shared primitive.
5. **Store via the theme pattern** — `FRONTEND_STORAGE_KEYS` + Zustand `persist` + `version`/`migrate` + a `validate/normalize` seam.
6. **Fix candidates surfaced by the audit:** Alt+Arrow history collision; Tab-hijack a11y; dedupe the three shift-suppresses-pane-drag sites and the two Shift+dblclick expand sites.

## Open questions

- Should OS-native menu accelerators (Electron `Menu`/`globalShortcut`) be in scope, or stay renderer-only? Today desktop has zero keyboard layer.
- Is the leader-key (`g i/o/t/r`) timing/binding worth exposing as configurable, or fixed UX?
- Centralization scope for the canvas zoom keys (`+`/`-`/`0`) shared between `useCanvasViewport` and `ImageResourceViewer` — unify or keep parallel.
