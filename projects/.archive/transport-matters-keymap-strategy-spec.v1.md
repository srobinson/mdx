---
title: Transport Matters — Cross-OS Keyboard Strategy Spec
type: spec
tags: [transport-matters, keyboard, cross-os, strategy]
summary: Authoritative design for a renderer-owned declarative command/keybinding registry on tinykeys ($mod), one label formatter, a separate modifier-held gesture store, and a curated user-configurable override layer mirroring the theme persist pattern. Synthesizes the keymap audit and the cross-OS research into an exhaustive migration map and PR-sized phasing. Design only, no code.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-18
updated: 2026-06-18
---

# Cross-OS Keyboard Strategy Spec

Single authoritative design for Transport Matters keyboard handling. It replaces the roughly seven uncoordinated renderer `window` keydown listeners with one declarative command/keybinding registry, one per-OS label formatter, one Escape arbitration contract, and a separate modifier-held gesture store, plus a curated user-configurable override layer.

Inputs synthesized here, both authoritative:

- Audit: `~/.mdx/projects/transport-matters-keymap-audit.md` (25-surface inventory, classifications, persistence pattern, desktop keyboard layer state).
- Research: `~/.mdx/research/transport-matters-cross-os-keyboard-electron.md` (recommended architecture, anti-patterns, library evaluation).

Code claims below were spot-checked against the current tree. Two corrections to the inputs are folded in: the desktop preload exists (`desktop/src/preload.cts`, exposing `transportMattersDesktop`), so the platform signal is an additive field on an existing bridge, not a new preload; and the theme migrate seam is exported as `migrateThemeState` (themeStore) plus `normalizeLegacyTheme` and `validateThemeDefinition` (theme), with no exported `migrateTheme`.

All citations are file plus symbol. No line anchors. No version-suffixed naming anywhere.

---

## 1. Goals and non-goals

### Goals

1. **DRY centralization.** One source of truth for every app-level accelerator. Lift the cross-OS modifier guard, the editable-target yield, and Escape arbitration out of the scattered listeners into one dispatcher with explicit priority. The accelerators are already correct (see below); the value is removing future drift across independent copies.
2. **Per-OS display labels.** One pure formatter renders Apple symbolic order on macOS and word-plus-plus joins on Windows and Linux, consumed by the palette, settings, tooltips, and any future native menu.
3. **User configurability.** A curated, deliberately small subset of commands is remappable through a sparse override layer with conflict detection and reset-to-default, persisted with the same discipline as the theme store.
4. **Accessibility and collision fixes.** Resolve the `Alt`+Arrow versus browser Back collision, the bare-`Tab` hijack in the lab cockpit, and the reserved-combo hazard, and keep Ark and zag owning their component-internal keys.

### Explicit non-goal: this is not a macOS bug fix

The discrete accelerators are already cross-OS correct. `useLauncherHotkeys` gates on `(metaKey || ctrlKey) && !altKey`; `useRouteHotkeys` returns early when any of `metaKey`, `ctrlKey`, or `altKey` is held and uses plain keys. There is no current macOS-only `metaKey` defect to repair. Framing this work as a bug fix would understate it and misdirect review.

### Non-goals (v1)

- No `globalShortcut`. No OS-wide combos.
- No native menu bar in the first cut. The main process stays a thin projection; the menu is architected for but deferred (Section 9, decision a).
- No remap-everything. Most bindings stay fixed patterns (Section 7).
- No changes to Ark or zag internals, the palette query grammar, viewer-local roving, ARIA Space and Enter activation, or the exported-artifact handler. These are out of registry scope by design (Section 4 migration map, leave-as-is).
- No behavior regressions. Every migrated binding preserves its current effect; this is a refactor of ownership, not of UX.

---

## 2. Architecture

A renderer-owned, layered system under `www/src/keybindings/`. The directory does not exist today and no keyboard library is in `www` dependencies; both are net-new.

| Module | Responsibility |
|---|---|
| `platform` | Resolve `isMac` and `$mod` once at startup from the desktop bridge platform field, with a `userAgentData`/`userAgent` fallback for the browser-dev path. The single platform authority. |
| `registry` | `COMMANDS`: the declarative array of `Command` entries. The single source of truth for app-level accelerators. |
| `format` | `formatBinding(tokens, platform)`: the only function that turns binding tokens into a per-OS label string. |
| `engine` | The dispatcher service. **Precompiles `$mod` to the concrete `Meta` or `Control` token from `platform`** before building the tinykeys map, so tinykeys never resolves `$mod` itself. Merges registry with overrides, builds the tinykeys map, evaluates `when` gates and `priority`, owns Escape arbitration, dispatches one command per event. |
| `overrides` | Load and save the sparse user override map, detect conflicts at save, reset-to-default, persist via the theme pattern. |
| `gestures` | The modifier-held state store (held-Shift, extensible to Alt and Space) plus the shared pan-not-drag predicate. Separate from accelerators; never routed through the dispatcher. |

### The `Command` type

```ts
type Command = {
  id: string                 // e.g. 'launcher.toggleRoot', 'route.intercept', 'view.zoomIn'
  title: string              // e.g. 'Open command center' (palette + settings label)
  category: string           // grouping in settings
  defaultKeys: string[]      // tinykeys syntax, e.g. ['$mod+K'] or sequences ['1', 'g i']
  when?: ContextPredicate    // gate by active context; false while a modal scope owns keys
  configurable?: boolean     // only true entries are exposed in settings for remap
  priority?: number          // arbitration when several commands share a combo+context (Escape)
  run: (ctx: CommandContext) => void
}
```

`when` and `priority` are the two additions over the research shape, both required by the Escape arbitration contract (Section 5). `run` may dispatch a command id into the engine bus so a future native menu can invoke the same path over IPC (Section 9).

---

## 3. Cross-OS modifier and label model

- **`$mod` resolution, single source.** App-level chords are authored with `$mod`, never with literal `metaKey`. Critically, `platform` is the **sole** platform authority: the `engine` precompiles every `$mod` token to the concrete `Meta` (macOS) or `Control` (Windows and Linux) token, derived from `platform`, **before** handing the `KeyBindingMap` to tinykeys. tinykeys' own `$mod` would resolve from `navigator.platform`, which would make the matcher read a different platform source than the `process.platform` bridge driving labels. Precompiling eliminates that second source: tinykeys never resolves `$mod` itself, so matcher and label always agree. This is the matcher-level equivalent of the current `(metaKey || ctrlKey)` guard, expressed once.
- **`formatBinding(tokens, platform)`.** On macOS it emits symbols in Apple order, Control then Option then Shift then Command (`⌃⌥⇧⌘`), with no separators (`⇧⌘K`). On Windows and Linux it emits words in the order Ctrl, Alt, Shift, Key joined with `+` (`Ctrl+Shift+K`). It is the only place labels are produced; no call site formats ad hoc. Drift between `⌘K`, `Cmd+K`, and `Cmd K` is structurally impossible.
- **Platform detection.** Source of truth is Node's `process.platform`, surfaced to the renderer by extending the existing `transportMattersDesktop` contextBridge object in `desktop/src/preload.cts` with a `platform` field. Today that bridge exposes only `appName` and `getPathForFile`, and `www/src` references no platform signal at all, so this is a small additive change to a live bridge, not a new preload. The browser build has no bridge (the preload comment notes this), so `platform` derives `isMac` from `navigator.userAgentData?.platform || navigator.userAgent` when the bridge is absent. `isMac` and `$mod` are computed once and memoized.

---

## 4. Migration map (core deliverable)

Every keyboard surface enumerated in audit sections A through I, mapped to exactly one disposition: a **registry command** (with its id), the **gesture or shared-interaction** layer, or **leave-as-is**. Citations are file plus symbol.

**Counting model (so every total below reconciles).** The audit headline is **25 surfaces**. This spec enumerates them as **27 collapsed rows**, splitting two audit rows that carry multiple keys: audit B (route digits and the `g` leader) and audit D (the `Alt`+Arrow pan). Those 27 collapsed rows **expand to 32 migration-table entries**, because some single rows fan into several commands. The 32 entries partition as **16 registry commands + 7 gesture/shared + 9 leave-as-is**. So: 25 surfaces → 27 collapsed rows → 32 table entries (16 / 7 / 9).

### Registry commands (audit A, B, D, E partial)

| Audit | Surface (file · symbol) | Keys | Disposition · command id |
|---|---|---|---|
| A | `session-canvas/launcher/useLauncherHotkeys.ts` · `useLauncherHotkeys` | `$mod+K` | registry · `launcher.toggleRoot` |
| A | `useLauncherHotkeys` | `$mod+A` (palette closed, not editable) | registry · `launcher.openAgents` |
| A | `useLauncherHotkeys` | `$mod+,` (also while typing) | registry · `launcher.openSettings` |
| B | `hooks/useRouteHotkeys.ts` · `useRouteHotkeys` | `1`, `g i` | registry · `route.intercept` |
| B | `useRouteHotkeys` | `2`, `g o` | registry · `route.overlays` |
| B | `useRouteHotkeys` | `3`, `g t` | registry · `route.trace` |
| B | `useRouteHotkeys` | `4`, `g r` | registry · `route.recall` |
| D | `engine/react/useCanvasViewport.ts` · `handleKeyDown` | `+`, `=` | registry · `view.zoomIn` (when `canvasViewportFocused`) |
| D | `useCanvasViewport` · `handleKeyDown` | `-` | registry · `view.zoomOut` (when `canvasViewportFocused`) |
| D | `useCanvasViewport` · `handleKeyDown` | `Alt`+`Left` (rebind) | registry · `view.panLeft` (when `canvasViewportFocused`) |
| D | `useCanvasViewport` · `handleKeyDown` | `Alt`+`Right` (rebind) | registry · `view.panRight` (when `canvasViewportFocused`) |
| D | `useCanvasViewport` · `handleKeyDown` | `Alt`+`Up` (rebind) | registry · `view.panUp` (when `canvasViewportFocused`) |
| D | `useCanvasViewport` · `handleKeyDown` | `Alt`+`Down` (rebind) | registry · `view.panDown` (when `canvasViewportFocused`) |
| E | `hooks/useFullscreen.ts` · `useFullscreen` | `Escape` | registry · `ui.exitFullscreen` (when fullscreen) |
| E | `session-canvas/components/PaneDock.tsx` · `PaneDock` onKeyDown effect | `Escape` | registry · `ui.closeDock` (when dock open) |
| E | `session-canvas/lab/CanvasLabRoute.tsx` · `CanvasLabRoute` onKeyDown effect | `Tab` (rebind, stop hijacking) | registry · `lab.toggleTopBar` (when on canvas-lab route) |

**Eleven collapsed rows (audit A, B, D, E) expand to 16 registry commands**: A's 3 rows stay 3 commands; B's 2 rows (digits, leader) fold into 4 `route.*` commands; D's 3 rows expand to 6 (`view.zoomIn`, `view.zoomOut`, four `view.pan*`); E's 3 rows stay 3 commands. The `view.*` and `lab.toggleTopBar` entries carry their current element-scoped semantics through a `when` context gate rather than an element listener, so `useCanvasViewport.handleKeyDown` and the `CanvasLabRoute` Tab effect are retired in favor of registry entries. Rebinds for `view.pan*` and `lab.toggleTopBar` are accessibility fixes (Section 8).

### Gesture and shared-interaction layer (audit C, E partial)

| Audit | Surface (file · symbol) | Trigger | Disposition |
|---|---|---|---|
| C | `engine/react/useCanvasViewport.ts` · `sync` effect | `Shift` keydown/keyup, blur clear (sets `panReady`) | gesture store: held-modifier source |
| C | `useCanvasViewport` · `bindViewport` (`useDrag`) | `Shift` + drag pans | reads gesture store |
| C | `useCanvasViewport` · `handleWheel` | `Shift` + wheel zooms at cursor | reads gesture store |
| C | `engine/react/PaneFrame.tsx` · `useDrag` callback | `Shift` suppresses pane drag | shared `shouldPanNotDrag` predicate |
| C | `session-canvas/dnd/paneDragPointerSensor.ts` · `paneDragPointerSensor` | `Shift` suppresses pane drag | shared `shouldPanNotDrag` predicate |
| E | `session-canvas/lab/CanvasLabRoute.tsx` · `onHeaderDoubleClick` | `Shift` + header dblclick → expand else frame | shared `onHeaderActivate` helper |
| E | `session-canvas/components/CanvasSurface.tsx` · `onHeaderDoubleClick` | `Shift` + header dblclick → expand else frame | shared `onHeaderActivate` helper |

Seven rows. None are accelerators; none enter the dispatcher (Section 6). TM's canvas viewport gesture modifier is `Shift` for both pan (drag) and zoom (wheel); the research generic "SHIFT pan, ALT zoom" describes the design-tool pattern, not TM's literal binding. The `Alt`+Arrow pan in audit D is a discrete keyboard command, not a held gesture, and is handled as a registry command above.

### Leave-as-is (audit F, G, H, I)

| Audit | Surface (file · symbol) | Why off-registry |
|---|---|---|
| F | `...viewers/session-picker/SessionPickerPane.tsx` · `handlePickerKey` | roving listbox, focus-scoped |
| F | `...viewers/resource/ImageResourceViewer.tsx` · onKeyDown | viewer-local zoom; keep labels consistent with `view.zoom*` if rebound |
| G | `components/Toggle.tsx` · `handleKey` | ARIA Space/Enter activation |
| G | `components/detail/atoms.tsx` · role=button onKeyDown handlers | ARIA Enter/Space activation |
| G | `components/editor/EditorLedger.tsx` · onKeyDown | ARIA Enter/Space activation |
| H | `session-canvas/launcher/CommandCenter.tsx` · Ark UI combobox | zag state machine owns Arrow/Enter/Escape/Tab |
| H | `session-canvas/launcher/useCommandCenter.ts` · `onEscapeCapture` | capture-phase palette dismissal; preserved and referenced by Escape arbitration (Section 5) |
| H | `useCommandCenter` · `onInputKeyDown` | palette query grammar (ArrowRight ghost-accept, ArrowLeft/Backspace pop scope) |
| I | `lib/exportInspect.ts` · `EXPORT_COLLAPSE_SCRIPT` | runs inside exported static HTML, not the live app |

Nine rows. `useCommandCenter.onEscapeCapture` stays in place but is load-bearing for arbitration: the dispatcher must not register a competing Escape that would run before it.

**Migration map totals:** 25 audit surfaces → 27 collapsed rows → 32 migration-table entries, partitioned as **16 registry commands** (from 11 collapsed rows), **7 gesture/shared-interaction** (from 7 rows), **9 leave-as-is** (from 9 rows). 11 + 7 + 9 = 27 collapsed rows; 16 + 7 + 9 = 32 table entries. The shared layer also retires three duplicate definitions (the `Shift`-suppresses-pane-drag rule across `PaneFrame`, `paneDragPointerSensor`, and `useCanvasViewport`) and two duplicate definitions (the `Shift`+header-dblclick expand-else-frame across `CanvasLabRoute` and `CanvasSurface`).

---

## 5. Dispatcher and ordering contract

One dispatcher in `engine` owns all app-level key handling. There is exactly one `window` keydown listener for the registry, attached in the **bubble phase**, replacing the scattered ones. Bubble phase is required for Escape correctness: `useCommandCenter.onEscapeCapture` is a capture-phase listener, and a second capture-phase listener on the same target would still fire even after the first calls `stopPropagation` (capture listeners on one target all run before propagation is evaluated). A bubble-phase registry listener never runs once the capture handler has stopped propagation.

- **Single matcher.** The engine builds one tinykeys `KeyBindingMap` from `registry ⊕ overrides` and rebuilds it on override change. tinykeys provides `$mod`, sequences, `key`-based matching, and the form-field ignore default. The editable-target yield reuses `isEditableTarget` (`lib/domFocus.ts`), which treats `input`, `textarea`, `select`, `contenteditable`, and `role="textbox"` as editable.
- **`when`-gating gives Ark one owner per combo per context.** Global commands carry a `when` predicate that is false while a modal scope owns the keys (palette open, Ark dialog open). When the command center is open, the registry stands down and Ark and zag own Arrow, Enter, Escape, and Tab. No global binding for those keys is ever registered for the modal-active context. The invariant is one owner per combo per context.
- **Priority for shared combos.** When more than one command resolves for the same combo in the same context, the engine selects the highest `priority` whose `when` is true and fires exactly that one. This is the rare case; most combos have a single owner via `when`.

### Escape arbitration

Escape has three independent handlers today (`useCommandCenter` capture, `PaneDock`, `useFullscreen`). The contract:

1. **Palette first, by capture phase.** `useCommandCenter.onEscapeCapture` remains a `window` listener in the capture phase that runs before Ark's document-level handler and calls `stopPropagation`, active only while the palette is open. Because the registry listener is bubble-phase, the captured-and-stopped Escape never reaches it. This window-capture-before-document ordering is preserved exactly; breaking it breaks palette Escape.
2. **Dock next.** `ui.closeDock` runs on Escape `when` the dock is open and the palette is closed.
3. **Fullscreen last.** `ui.exitFullscreen` runs on Escape `when` fullscreen and neither palette nor dock is open.

Two mechanisms enforce the order, belt and suspenders: the **phase split** (capture palette handler with `stopPropagation` versus bubble registry listener) guarantees the palette always wins, and the **`when` gates** on `ui.closeDock` and `ui.exitFullscreen` are additionally false while the palette is open, so even if propagation were not stopped neither dock nor fullscreen would fire. Encoded as `priority` among the bubble-phase commands: `ui.closeDock` > `ui.exitFullscreen`. One handler consumes a given Escape.

---

## 6. Modifier-held gesture model

`gestures` holds a small store, `{ shift, alt, space }`, updated on document `keydown` and `keyup`, **reset to all-false on `window` blur** so a modifier cannot stick after an OS combo steals focus. It never calls `preventDefault` on a bare modifier and never routes through the dispatcher. The canvas and panes read the store to choose wheel-zoom versus wheel-pan versus drag-pan.

Two duplications collapse into shared primitives consumed by the gesture layer:

- **`shouldPanNotDrag(event)`** encodes "Shift means canvas-pan, not pane-drag" once. `PaneFrame` (`useDrag` callback) and `paneDragPointerSensor` both call it instead of each re-deriving `shiftKey`. `useCanvasViewport` reads the same held-Shift source.
- **`onHeaderActivate(paneId, shiftKey)`** encodes "expand if Shift else frame" once. `CanvasLabRoute.onHeaderDoubleClick` and `CanvasSurface.onHeaderDoubleClick` both call it.

These are pointer-plus-modifier interactions, not accelerators, so they live beside the gesture store rather than in the command registry.

---

## 7. User-configurable subset

VS Code's override model with Linear's restraint: most bindings are fixed patterns; a deliberately curated subset is remappable. Proposed `configurable: true` set, **9 of 16 commands**:

| Command | Configurable | Rationale |
|---|---|---|
| `launcher.toggleRoot` | yes | flagship accelerator; the one users most want to own |
| `launcher.openAgents` | yes | direct-manipulation accelerator |
| `launcher.openSettings` | yes | `$mod+,` is a macOS idiom; users on other OSes may prefer another combo |
| `route.intercept` | yes | route digits are prime remap targets |
| `route.overlays` | yes | |
| `route.trace` | yes | |
| `route.recall` | yes | |
| `view.zoomIn` | yes | view ergonomics vary by user and keyboard |
| `view.zoomOut` | yes | |
| `view.panLeft/Right/Up/Down` | no | directional; bound to arrow semantics; remapping arrows is low value and high collision risk |
| `ui.exitFullscreen` | no | Escape is conventional and should not be reassigned |
| `ui.closeDock` | no | Escape is conventional |
| `lab.toggleTopBar` | no | experimental cockpit; fix the binding first, expose later |

**Override layer shape.** A sparse map `{ [commandId]: string[] }` holding only the commands the user changed. Defaults stay in `registry`; the engine merges overrides over defaults, last-wins, so reset-to-default is simply dropping the override entry.

**Conflict detection at save.** On save the engine rejects or warns when the proposed keys collide with another binding active in the same `when` context. Same combo plus same context is a conflict; same combo in mutually exclusive contexts is allowed. The matcher also refuses reserved combos (Section 8).

**Reset-to-default.** Per binding, removing the override entry. A global reset clears the map.

**Persistence.** Mirror the theme pattern (Section: persistence). Default location is renderer `localStorage` via the same Zustand `persist` plus `createFrontendPersistStorage` plumbing, keyed by a new `FRONTEND_STORAGE_KEYS.keymapStore`. Durability upgrade to the TM config file is decision b.

---

## 8. Accessibility and collision fixes

1. **`Alt`+Arrow pan versus browser Back.** `Alt`+`Left` and `Alt`+`Right` are history Back and Forward on Windows and Linux. Rebind `view.panLeft/Right/Up/Down` away from `Alt`+Arrow. Recommended default: bare Arrow keys gated on **exact viewport focus**, a `canvasViewportFocused` when-context that is true only when `document.activeElement` is the bare viewport element itself (the `LayoutCanvas` root that carries the canvas `onKeyDown` today), and false whenever a pane, viewer, or editable target holds focus. This gate is mandatory because "focus within the canvas" is unsafe: descendant roving handlers such as `SessionPickerPane.handlePickerKey` call `preventDefault` without `stopPropagation`, so a focus-within Arrow binding would both pan the canvas and fight the listbox. Deriving the context: compare `document.activeElement` against the viewport element ref, or expose a small `canvasViewportFocused` flag from the viewport on its focus and blur. Alternative if exact-viewport-focus proves too restrictive: bind pan to a non-reserved modifier other than `Alt` (Alt is the collision and is also a dead-key hazard). The focus-gate is the recommendation; the modifier is the fallback. Tradeoff: bare arrows can compete with native scroll, but the bare viewport is the scroll owner exactly when it holds focus.
2. **`Tab`-hijack in the lab.** `CanvasLabRoute` calls `preventDefault` on bare `Tab`, which breaks focus traversal and is an a11y defect. Stop hijacking `Tab`: bind `lab.toggleTopBar` to a deliberate non-reserved accelerator (proposed `$mod+/`, subject to conflict check) and remove the bare-`Tab` `preventDefault` entirely.
3. **Reserved-combo avoidance.** The matcher and the override validator refuse to bind OS- and browser-reserved combos (`$mod+Q`, `$mod+W`, `$mod+Tab`, `$mod+Space`, `F11`, `$mod+Shift+3`, `$mod+Shift+4`, and the like). Defaults are linted against this list; user overrides are rejected at save with a clear reason.

---

## 9. Electron main-process boundary

The registry is the single source of truth. The main process stays thin.

- **No `globalShortcut`** in v1. It steals combos OS-wide and hits the documented macOS non-QWERTY layout bug. Reserve only for a genuine OS-global feature, none of which exists yet.
- **Native menu as a deferred projection.** When a native menu is added, generate `MenuItem` accelerators from the same registry entries (`$mod` maps to `CommandOrControl` via an `acceleratorFromTokens` helper), and have each item's `click` send a `command:invoke {id}` IPC message that the renderer dispatches through the engine bus. The menu becomes a projection of the registry, never a parallel copy.
- **Recommendation: defer past the first cut.** Architect for it (the engine exposes a dispatch-by-id bus; tokens are formatter-ready) but do not build the menu or the IPC channel in the initial slices. This is decision a.

---

## 10. Open decisions for Stuart

Each with a recommended default and the one-line tradeoff.

- **(a) Native menu bar now or deferred.** Recommend **deferred**. Tradeoff: a native menu aids discoverability and macOS expectations, but it is net-new main-process and IPC surface that the zero-chrome direction does not need yet; the registry is built to project into it later at no rework.
- **(b) Override storage: TM config file via IPC versus renderer `localStorage`.** Recommend **`localStorage` for v1** (mirrors the already-decided theme persist pattern, no IPC). Tradeoff: the config file gives cross-checkout durability aligned with TM's workspace-identity model, at the cost of an IPC round-trip and main-process file ownership; defer until durability is actually requested.
- **(c) Size and philosophy of the configurable subset.** Recommend the **curated 9** (launcher trio, four routes, two zooms), everything else fixed. Tradeoff: fewer remappable commands means less support burden and clearer muscle memory (Linear's stance), at the cost of power-user flexibility that can be widened later by flipping `configurable` flags.
- **(d) Leader-key (`g i/o/t/r`) timing configurable or fixed.** Recommend **fixed at the current 900ms** for v1, exposed later as a single global setting if asked. Tradeoff: a knob adds surface and test cases for a value few users tune.
- **(e) `navigator.keyboard.getLayoutMap()` for physical-key labels later.** Recommend **defer**, architecting `format` to accept an optional layout map. Tradeoff: it is Chromium-only and therefore viable in Electron, giving accurate non-QWERTY physical-key labels, but it adds async layout resolution that v1's `key`-based labels do not need.

---

## 11. Implementation phasing

Each slice is PR-sized, independently shippable, and behavior-preserving unless it is an explicit fix. These map to future Linear sub-issues or a Slice Build Loop.

1. **Pure foundations.** `platform` and `format` plus unit tests. Extend `desktop/src/preload.cts` `transportMattersDesktop` with `platform`. No behavior change.
2. **Registry and engine, discrete accelerators.** Add tinykeys. Build `registry` and `engine`. Migrate the three launcher chords and four route commands (digits and leader). Delete the `useLauncherHotkeys` and `useRouteHotkeys` window listeners. Behavior identical.
3. **Escape arbitration.** Migrate `useFullscreen` and `PaneDock` Escape into `ui.exitFullscreen` and `ui.closeDock` with `priority` and `when`. Preserve `useCommandCenter.onEscapeCapture` capture ordering.
4. **Gesture store and dedup.** Add `gestures` with the held-Shift source and blur reset. Introduce `shouldPanNotDrag` (dedupe three sites) and `onHeaderActivate` (dedupe two sites). Point `useCanvasViewport` at the store.
5. **Canvas discrete commands and a11y fixes.** Move `+`/`-` and pan into `view.*` registry commands gated on exact viewport focus (`canvasViewportFocused`). Rebind `view.pan*` off `Alt`+Arrow. Fix the `Tab`-hijack via `lab.toggleTopBar`. Retire `useCanvasViewport.handleKeyDown` and the `CanvasLabRoute` Tab effect.
6. **Override layer and settings surface.** Add `overrides` mirroring the theme persist pattern, `FRONTEND_STORAGE_KEYS.keymapStore`, conflict detection, reset-to-default. Surface the `configurable: true` subset in the launcher settings scope with `formatBinding` labels and a record-binding capture.
7. **Deferred: native menu projection.** Only if decision a flips. `acceleratorFromTokens` plus `command:invoke` IPC into the engine bus.

---

## 12. Testing strategy

Gate on the repo recipes verbatim. The www gate is `just check`, `just test`, and `just test-e2e` (Playwright e2e is a separate recipe in `www/justfile`, run by the CI frontend job; it is not covered by `just test`). Do not hand-roll `tsc` or `pytest` invocations.

**Unit (`just test`).**

- `formatBinding`: macOS symbolic Apple order versus Windows and Linux word-plus joins, across single and multi-modifier chords.
- Chord matcher and `when`-gating: `$mod` resolution per platform, editable-target yield, modal-context standdown, sequence (`g i`) timing.
- Override merge and conflict detection: sparse merge last-wins, same-combo-same-context rejected, mutually exclusive contexts allowed, reset-to-default drops the entry, reserved-combo rejection.
- Gesture store: blur reset clears all modifiers; `shouldPanNotDrag` and `onHeaderActivate` shared behavior.

**End-to-end (`just test-e2e`).**

- `$mod+K` (and `$mod+K` resolving to Ctrl in the non-mac path) toggles the command center.
- Route digit and leader bindings switch routes; modifier-held digit does not (the existing early-return proof in `RouteRail.test.tsx` carries over).
- Escape ordering: palette capture beats dock beats fullscreen.
- Override round-trip: remap a configurable command, persist, reload, confirm the new binding fires and the label updates.

---

## 13. Risks and anti-patterns to avoid

Pulled forward from the research so they are enforced in review.

- **Hardcoding `metaKey`.** Use `$mod`. The current code is correct; keep it correct by construction.
- **Two sources of truth across main and renderer.** Derive any menu from the registry; never re-declare combos in the main process.
- **Matching on `keyCode`, `which`, or `code` for letters.** Position-based APIs break non-QWERTY layouts. Match on `key` (tinykeys default).
- **Binding `Alt`-plus-letter as a discrete accelerator.** Option composes dead keys and interferes with IME on macOS. Held-`Alt` for a gesture is fine; `Alt`-letter accelerators are not.
- **`globalShortcut` for in-app shortcuts.** Steals the combo OS-wide and hits the macOS non-QWERTY bug.
- **Hijacking reserved combos.** Never `preventDefault` `$mod+Q/W/Tab/Space`, `F11`, or the screenshot combos. Enforced by the reserved list.
- **No conflict detection.** Silently shadowed bindings are undebuggable. Detect at override save.
- **Label drift.** One `formatBinding`, consumed everywhere. No ad-hoc formatting.
- **Hardcoding what should be configurable.** Keep the override layer plus the curated subset.
- **Sticky modifier state.** Reset the gesture store on `window` blur.
- **Double-handling with Ark and zag.** Never register global Arrow, Enter, Escape, or Tab for a context a component state machine owns. One owner per combo per context.
