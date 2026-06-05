---
title: Cross-OS Keyboard Strategy for an Electron App (Transport Matters)
type: research
tags: [transport-matters, keyboard, electron, cross-os]
summary: A renderer-owned declarative keybinding registry built on tinykeys ($mod) with a contextBridge platform signal, a single label formatter, and a separate modifier-held gesture store is the DRY, scalable, cross-OS architecture; the main process stays a thin projection.
status: active
confidence: high
created: 2026-06-18
updated: 2026-06-18
---

# Cross-OS Keyboard Strategy for an Electron App

## Executive Summary

Transport Matters today hardcodes `metaKey` (macOS-only) across roughly six scattered renderer hooks with no central registry, no keyboard library, and no main-process accelerators. The correct target is a **single renderer-owned declarative command + keybinding registry** that uses the `$mod` cross-platform token (Cmd on macOS, Ctrl on Windows/Linux), drives a thin engine layer over **tinykeys**, formats per-OS display labels through **one pure function**, and models **modifier-held continuous gestures (SHIFT pan / ALT zoom) as a separate state store**, not as discrete accelerators. The Electron main process stays a thin projection: native menu accelerators, when added, are derived from the same registry and dispatch back into the renderer over IPC, so there is exactly one source of truth.

---

## Detailed Findings (by theme)

### 1. Electron accelerator system: when to use each, and the single-source-of-truth boundary

The Electron docs define three distinct mechanisms, each with a different scope ([Electron: Keyboard Shortcuts](https://www.electronjs.org/docs/latest/tutorial/keyboard-shortcuts), [Accelerator](https://www.electronjs.org/docs/latest/api/accelerator)):

- **`CommandOrControl` / `CmdOrCtrl` accelerator token** — a string modifier that resolves to ⌘ on macOS and Ctrl on Windows/Linux. Used in `MenuItem` accelerators and `globalShortcut.register`. This is the main-process equivalent of tinykeys' `$mod`.
- **Menu accelerators (local shortcuts)** — set the `accelerator` on a `MenuItem`; the item's `click` fires on that combo *while the app is focused*. The OS renders the accelerator in the native menu automatically. This is the right home for app-level commands that also belong in the menu bar (New, Quit, Preferences, Find).
- **`globalShortcut` (main process, OS-wide)** — fires *even when the app is not focused*. Use only for true OS-global features (e.g. a system-wide capture toggle). **Two hazards**: it steals the combo from every other app, and there is a long-standing macOS bug where `globalShortcut` fails on non-QWERTY layouts ([Electron docs](https://www.electronjs.org/docs/latest/tutorial/keyboard-shortcuts)). Do **not** use it for in-app shortcuts.
- **Renderer DOM events / `before-input-event`** — for shortcuts handled inside the window, listen to `keydown`/`keyup` in the renderer (this is where a thin-shell app like TM does almost everything). `webContents.on('before-input-event')` lets the *main* process intercept renderer keys before the page sees them; it is a narrow escape hatch (e.g. blocking a devtools combo), not the primary mechanism.

**SSOT across the main/renderer boundary (the DRY core):** define bindings **once in the renderer registry**. The main process should not re-declare combos. When a native menu item needs an accelerator, derive its Electron accelerator string from the same registry entry (`$mod` → `CommandOrControl`) and have the menu item's `click` send an IPC message (`command:invoke {id}`) that the renderer dispatches through the same command bus. The menu becomes a *projection* of the registry, never a parallel copy. For TM specifically — a thin shell with the entire UI in `www/` — almost everything stays renderer-side; the main process holds at most a minimal native menu and zero `globalShortcut` until a genuine OS-global need appears.

### 2. Platform detection in the renderer

`navigator.platform` is deprecated ([MDN: Navigator.platform](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/platform)). The modern web replacement is `navigator.userAgentData.platform`, but it is **Chromium-only** (absent in Firefox/Safari), so pure web code needs a fallback chain `navigator?.userAgentData?.platform || navigator?.platform` ([Bye navigator.platform](https://medium.com/@jortiz.dev/bye-navigator-platform-here-is-the-alternative-939b883bf050)).

**In Electron the correct answer is neither.** Expose Node's `process.platform` (authoritative: `'darwin' | 'win32' | 'linux'`) from the preload script via `contextBridge`, because `contextIsolation` is on and `nodeIntegration` off by default ([Electron tips: detect OS in renderer](https://medium.com/@trungutt/electron-tips-tricks-detect-os-in-renderer-process-3620a34f7f2d)). Compute `isMac` once at startup, memoize it, and feed it to the label formatter and the `$mod` resolution. Keep a `userAgentData`/`userAgent` fallback only for the non-Electron dev/browser path (Vite dev server in a plain browser).

### 3. Display-label conventions per OS

Apple's Style Guide fixes modifier order as **Fn, Control, Option, Shift, Command**, rendered symbolically as **⌃⌥⇧⌘** and the *same order* in words ("Shift-Command-3" matches ⇧⌘3) ([Six Colors](https://sixcolors.com/link/2017/11/the-order-of-modifier-keys-on-the-mac/), [Daring Fireball, Mar 2026](https://daringfireball.net/2026/03/modifier_key_order_for_keyboard_shortcuts)). Symbols: Control ⌃, Option ⌥, Shift ⇧, Command ⌘.

Windows/Linux use **words with `+` joins** in the order **Ctrl+Alt+Shift+Key** (e.g. `Ctrl+Shift+P`). Map `$mod` → ⌘ vs `Ctrl`, `Alt` → ⌥ vs `Alt`, etc. The rule that prevents drift: **one pure `formatBinding(tokens, platform)` function** consumed by every surface (command palette, settings, tooltips, native menu). Never format ad hoc at call sites.

### 4. Declarative keybinding registry patterns (VS Code, Figma, Linear)

**VS Code** is the reference model ([VS Code keybindings docs](https://code.visualstudio.com/docs/configure/keybindings), [DeepWiki: Keybindings and Commands](https://deepwiki.com/microsoft/vscode-docs/6.4-keybindings-and-commands)):
- Bindings are data: `{ key, command, when }`. Defaults ship with the product; user `keybindings.json` rules are **appended at runtime** and override defaults (last-wins).
- **`when` clauses** are boolean context expressions evaluated against context keys (what is focused/visible). This is how the same key does different things in different UI states.
- **Conflict detection**: "Show Same Keybindings" surfaces multiple commands on one combo; this is an explicit feature, not implicit.
- **Reset/remove**: a rule with a leading `-` on the command removes a default binding; user file as override layer means reset = drop the override.

**Figma** ships US-QWERTY-based defaults, lets users pick a keyboard layout, and exposes customization via Preferences → Keyboard Shortcuts; its mnemonic system is **Cmd/Ctrl = general action, Shift = refine/precision, Alt/Option = duplicate/align** ([Figma keyboard layout help](https://help.figma.com/hc/en-us/articles/5665442977431-Select-keyboard-layout), [Figma x Work Louder](https://www.figma.com/blog/figma-work-louder-custom-keyboard/)).

**Linear** is keyboard-first with **sequential chords**: `Cmd/Ctrl+K` command menu, plus `g` then `i`/`v`/`b` navigation and `o` then `_` menus. Shortcuts **cannot be remapped** ("we may consider it in the future"); the philosophy is *pattern-based muscle memory* over per-user customization ([Linear concepts](https://linear.app/docs/conceptual-model), [Linear shortcuts](https://shortcuts.design/tools/toolspage-linear/)). **Directly relevant to TM**, which already uses a vim-style `g` leader prefix in `useRouteHotkeys` — Linear validates that pattern, and tinykeys models it natively (space-separated sequences).

**Takeaway for the registry shape:** model each command as `{ id, title, category, defaultKeys, when, configurable }`, keep user overrides as a **sparse override layer** merged over defaults (VS Code model), detect conflicts at save time, and expose **only the `configurable: true` subset** in Settings (Linear's restraint: most bindings are fixed patterns; only a curated subset is user-editable).

### 5. Modifier-held continuous gestures (SHIFT pan / ALT zoom) — model these separately

Design tools (Photoshop, Framer, Motion, Excalidraw) implement pan/zoom as **spring-loaded modes**: hold Space/Shift/Alt to switch the pointer/wheel interaction mode while held ([Photoshop spacebar pan](https://photoshoptrainingchannel.com/tips/pan-scroll-canvas-using-spacebar/), [Framer canvas](https://www.framer.com/help/articles/how-to-use-the-canvas/), [Motion zoom/pan](https://support.apple.com/guide/motion/zoom-or-pan-the-canvas-motn5f3e474c/mac)). These are **not discrete accelerators** — there is no "command fired on keydown." The correct model is a small **modifier-state store** driven by `keydown`/`keyup` at document level that tracks which modifiers are currently held; the canvas reads that state to choose wheel-zoom vs wheel-pan vs drag-pan.

Critical distinction (resolves an apparent contradiction with §6's "never bind Alt to a letter"): **Alt-held-as-a-gesture-modifier is fine** (no character is produced; you only sample modifier state during a pointer interaction). **Alt-as-a-discrete-letter-accelerator is the anti-pattern**, because Option composes characters/dead keys on macOS. Pan/zoom gestures never type, so they are safe.

Accessibility rules for the gesture store: reset all held state on `window` **blur** (otherwise a modifier "sticks" after an OS combo steals focus), never `preventDefault` a bare modifier, and provide a non-gesture path (buttons/menu zoom) so the feature is not keyboard-trapping. The web pan/zoom literature is thin on a11y, so this is enforced by convention, not a library.

### 6. Library evaluation — recommend **tinykeys**

The blunt finding from a 2025 teardown is that **most JS hotkey libraries are broken for international keyboards** because they match on deprecated/position APIs ([Hazel Duvall: All JS Keyboard Shortcut Libraries Are Broken](https://www.hazelduvall.dev/blog/posts/2025-01-10-all-javascript-keyboard-shortcut-libraries-are-broken.html)):

| Library | Matching API | Status | Verdict |
|---|---|---|---|
| **mousetrap** | `event.which` (obsolete, position-based) | ~11.8k★ but effectively unmaintained | Avoid — layout-broken |
| **hotkeys-js** | `event.keyCode` (deprecated, position-based) | active, popular | Avoid — layout-broken |
| **react-hotkeys-hook** | mixes `code` + `key`, "fires more often than it should" | active | Usable, but over-triggers; heavier React-coupled API |
| **tinykeys** | `key` (case-insensitive) **+** optional `code` | active, 4.1k★, **0 open issues** | **Recommended** |

[tinykeys](https://github.com/jamiebuilds/tinykeys) (~1KB; gzip ~650B) is the standout:
- **`$mod`** token (Meta on macOS, Control on Win/Linux) — exactly the cross-OS primitive needed.
- Matches on **`KeyboardEvent.key`** by default (layout-correct), with explicit `code` matching available (`"Alt+KeyD"`) when physical position is wanted.
- **Native key sequences**: `"g i"` space-separated, 1000ms configurable timeout — maps directly onto TM's existing `g` leader.
- **Optional modifiers**: `"$mod+[Shift]+D"`, and regex groups `"$mod+([0-9])"`.
- Ignores `input`/`textarea`/`select`/`[contenteditable]` unless they are `event.currentTarget` — the sensible default that prevents typing-vs-shortcut collisions.
- `event: "keydown" | "keyup"`, `capture`, and a custom `ignore(event)` filter.
- Ships **`createKeybindingsHandler(map)`** (returns a handler you attach yourself) and **`parseKeybinding()`** (structured representation) — the two primitives a custom engine and label formatter need.

**Recommendation: adopt tinykeys as the low-level matcher, wrapped in a thin TM-owned engine** (registry merge, `when` gating, override application, conflict detection). Do not hand-roll the matcher — tinykeys already solves the layout/sequence/ignore problems correctly. Reserve the "fully hand-rolled" option only if `navigator.keyboard.getLayoutMap()` (Chromium-only) is ever needed for physical-key label display, which is out of scope for v1.

### 7. Coexisting with Ark UI / zag.js (avoid double-handling)

Ark UI is built on zag.js finite-state machines that **own their internal keyboard interactions** (Arrow/Enter/Escape/Tab) and focus management, including focus trapping via `trapFocus`/`modal` on Dialog ([Ark Dialog](https://ark-ui.com/docs/components/dialog), [zag Dialog](https://zagjs.com/components/react/dialog), [Ark Focus Trap](https://ark-ui.com/docs/utilities/focus-trap)). TM's command center already wraps `@ark-ui/react/combobox`, which owns its listbox keys; the custom palette grammar (→/← scope, ⌫ pop) is layered on the combobox input handler.

Rules to avoid double-handling:
1. **Let Ark own component-internal keys.** Never register a global binding for Arrow/Enter/Escape that would also fire inside an open Ark combobox/dialog.
2. **Gate global app commands behind a `when` context** that is false while a modal scope is active (e.g. `when: !modalOpen`). When the Ark dialog is open, the global layer stands down.
3. **tinykeys' form-field ignore** already prevents most collisions with text inputs; the `when` gate covers the non-text modal case (listbox navigation).
4. **One owner per combo per context.** A binding lives either in the registry (app-level) or in an Ark component handler (component-level) — never both for the same active context.

### 8. Anti-patterns to avoid (explicitly requested)

- **Hardcoding `metaKey`** (TM's current state) — macOS-only; breaks every Windows/Linux user. Use `$mod`.
- **Duplicating bindings main-vs-renderer** — two sources of truth drift. Derive the menu from the registry; menu click → IPC → command bus.
- **Matching on `keyCode`/`which`/`code`-for-letters** — position-based APIs break non-QWERTY/international layouts. Match on `key` (tinykeys default).
- **Binding `Alt`+letter as a discrete accelerator** — Option composes dead keys / interferes with IME on macOS ([Hazel Duvall](https://www.hazelduvall.dev/blog/posts/2025-01-10-all-javascript-keyboard-shortcut-libraries-are-broken.html)). (Alt-*held* for a pan/zoom gesture is fine — see §5.)
- **`globalShortcut` for in-app shortcuts** — steals the combo OS-wide and hits the macOS non-QWERTY bug. Reserve for genuine OS-global features only.
- **Hijacking browser/OS-reserved combos** — `Cmd+Q/W/Tab/Space`, `F11`, `Cmd+Shift+3/4`, `Ctrl+Alt+Del`. Never `preventDefault` these.
- **No conflict detection** — silently shadowed bindings are a debugging black hole. Detect at override-save time (same combo + same `when`).
- **Label drift** — ad-hoc per-call-site formatting yields inconsistent `⌘K` vs `Cmd+K` vs `Cmd K`. One `formatBinding` function, period.
- **Hardcoding what should be configurable** — bury the *configurable subset* in code and users cannot remap. Keep an override layer + Settings UI for `configurable: true` commands.
- **Not resetting modifier-held state on blur** — sticky SHIFT/ALT after focus loss corrupts the gesture mode.
- **Double-handling with Ark/zag** — registering global Arrow/Enter/Escape that fights the component state machine.

---

## Recommended Architecture (the concrete shape to adopt)

A renderer-owned, layered system. Five modules, one source of truth.

```
www/src/keybindings/
  platform.ts        # isMac, $mod resolution; from window.tm.platform (contextBridge) w/ UA fallback
  registry.ts        # COMMANDS: declarative array — the single source of truth
  format.ts          # formatBinding(tokens, platform) -> per-OS label string (the ONLY formatter)
  engine.ts          # KeybindingService: merges overrides, builds tinykeys map, when-gating, dispatch
  overrides.ts       # load/save sparse user override map; conflict detection; reset-to-default
  gestures.ts        # modifier-held store (SHIFT pan / ALT zoom) — SEPARATE from accelerators
```

**1. Command registry (SSOT).** A typed array; each entry:
```ts
type Command = {
  id: string                 // 'launcher.toggle', 'route.intercept', 'view.zoomIn'
  title: string              // 'Open command center'
  category: string           // for Settings grouping
  defaultKeys: string[]      // tinykeys syntax: ['$mod+K', '$mod+k'], or sequences ['g i']
  when?: ContextPredicate    // gate by active scope; false while modal owns keys
  configurable?: boolean     // only true entries appear in Settings
  run: (ctx) => void         // or a command-id dispatched to a command bus
}
```
Replace the scattered hooks (`useRouteHotkeys`, `useLauncherHotkeys`, `useFullscreen`, ad-hoc Space/Enter) with registry entries. Component-intrinsic keys (Toggle's Space/Enter, Ark's listbox keys) stay in their components — those are widget semantics, not app commands.

**2. Platform signal.** Preload exposes `process.platform` via `contextBridge` as `window.tm.platform`; `platform.ts` derives `isMac` once and resolves `$mod`. Browser-dev fallback: `userAgentData.platform || userAgent` regex.

**3. Engine over tinykeys.** `KeybindingService` reads `registry ⊕ overrides`, builds a tinykeys `KeyBindingMap` whose handlers check the command's `when` predicate against current context, then dispatch into a command bus. Rebuilds on override change. tinykeys handles `$mod`, sequences, `key`-matching, and form-field ignore; the service adds `when`-gating and override merge.

**4. Label formatter.** `formatBinding(['$mod','Shift','K'], platform)` → `⇧⌘K` on macOS (Apple order ⌃⌥⇧⌘), `Ctrl+Shift+K` on Win/Linux. Used by command palette, Settings, tooltips, and (projected) native menu. Single function = zero drift.

**5. Continuous gestures.** `gestures.ts` keeps a tiny store (`{ shift, alt, space }`) updated on document `keydown`/`keyup`, **reset on `window` blur**. The canvas/pane reads it to switch wheel/drag mode (SHIFT pan, ALT zoom). Never routed through the accelerator registry.

**6. User configurability.** Settings (the existing command-center "settings" scope is the natural home) lists `configurable: true` commands with `formatBinding` labels, a record-new-binding capture, **conflict detection** (reject/ warn on duplicate combo within the same `when`), and **reset-to-default** per binding. Overrides persisted as a sparse `{ id: keys[] }` map (localStorage in renderer, or the TM config file via IPC for durability).

**7. Main process stays thin.** No `globalShortcut`. If/when a native menu is added, generate `MenuItem`s from the registry — `acceleratorFromTokens($mod→CommandOrControl)` — whose `click` sends `command:invoke {id}` IPC; the renderer dispatches through the same command bus. The menu is a projection; the registry is the source of truth.

**Why this shape:** it is DRY (one registry, one formatter, one engine), cross-OS by construction (`$mod` + contextBridge platform), scalable (adding a command = one array entry), layout-correct (tinykeys `key` matching), accessible (gestures separated, blur-reset, no reserved-combo hijack, Ark left to own its keys), and selectively configurable (override layer + curated `configurable` subset, VS Code's model with Linear's restraint).

---

## Sources Consulted

**Official docs**
- Electron — [Keyboard Shortcuts](https://www.electronjs.org/docs/latest/tutorial/keyboard-shortcuts), [Accelerator](https://www.electronjs.org/docs/latest/api/accelerator), [globalShortcut](https://www.electronjs.org/docs/latest/api/global-shortcut)
- MDN — [Navigator.platform (deprecated)](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/platform)
- VS Code — [Keyboard shortcuts](https://code.visualstudio.com/docs/configure/keybindings); DeepWiki — [Keybindings and Commands](https://deepwiki.com/microsoft/vscode-docs/6.4-keybindings-and-commands)
- Ark UI — [Dialog](https://ark-ui.com/docs/components/dialog), [Combobox](https://ark-ui.com/docs/components/combobox), [Focus Trap](https://ark-ui.com/docs/utilities/focus-trap); zag.js — [Dialog](https://zagjs.com/components/react/dialog)
- tinykeys — [GitHub README](https://github.com/jamiebuilds/tinykeys)
- react-hotkeys-hook — [useHotkeys API](https://react-hotkeys-hook.vercel.app/docs/api/use-hotkeys)
- Figma — [Select keyboard layout](https://help.figma.com/hc/en-us/articles/5665442977431-Select-keyboard-layout), [Work Louder keyboard](https://www.figma.com/blog/figma-work-louder-custom-keyboard/)
- Linear — [Concepts](https://linear.app/docs/conceptual-model), [shortcuts list](https://shortcuts.design/tools/toolspage-linear/)

**Analysis / expert commentary**
- Hazel Duvall — [All JavaScript Keyboard Shortcut Libraries Are Broken (2025-01-10)](https://www.hazelduvall.dev/blog/posts/2025-01-10-all-javascript-keyboard-shortcut-libraries-are-broken.html) — primary source for the layout-correctness argument
- Six Colors — [The order of modifier keys on the Mac](https://sixcolors.com/link/2017/11/the-order-of-modifier-keys-on-the-mac/); Daring Fireball — [Modifier Key Order (Mar 2026)](https://daringfireball.net/2026/03/modifier_key_order_for_keyboard_shortcuts)
- [Bye navigator.platform, here is the alternative](https://medium.com/@jortiz.dev/bye-navigator-platform-here-is-the-alternative-939b883bf050); [Electron tips: detect OS in renderer](https://medium.com/@trungutt/electron-tips-tricks-detect-os-in-renderer-process-3620a34f7f2d)
- npm trends — [hotkeys-js vs mousetrap vs tinykeys](https://npmtrends.com/hotkeys-js-vs-mousetrap-vs-tinykeys)
- Canvas gesture patterns — [Photoshop spacebar pan](https://photoshoptrainingchannel.com/tips/pan-scroll-canvas-using-spacebar/), [Framer canvas](https://www.framer.com/help/articles/how-to-use-the-canvas/), [Motion zoom/pan](https://support.apple.com/guide/motion/zoom-or-pan-the-canvas-motn5f3e474c/mac)

**Codebase (current TM state, via Explore agent)**
- Scattered handlers: `www/src/hooks/useRouteHotkeys.ts` (1-4 + `g` leader), `www/src/session-canvas/launcher/useLauncherHotkeys.ts` (⌘K/⌃K), `useFullscreen.ts` (Esc), `Toggle.tsx` (Space/Enter), `ImageResourceViewer.tsx` (+/-/= zoom), `useCommandCenter.ts` (palette nav)
- No central registry, no keyboard library in `www/package.json`, no main-process accelerators/`globalShortcut` in `desktop/`
- Command center already on `@ark-ui/react/combobox`; existing "settings" scope in `commandModel.ts`

## Source Quality Assessment

**High confidence**: the Electron mechanism taxonomy, `$mod`/tinykeys capabilities, VS Code override model, Apple modifier order, and the layout-correctness (key vs code/keyCode) argument are all multi-source and corroborated by primary docs. The tinykeys recommendation rests on official README + an independent critical teardown that *still* singles it out as the exception.

**Medium confidence**: continuous-gesture accessibility is convention-driven (the web literature on pan/zoom a11y is thin); the modifier-held store design is synthesized from how design tools behave, not a cited standard. Linear's "no remapping" is current as documented but could change.

**Gaps**: no first-party benchmark of tinykeys vs react-hotkeys-hook under heavy sequence load; `navigator.keyboard.getLayoutMap()` for physical-key labels was scoped out (Chromium-only) and not deeply evaluated.

## Open Questions

1. Should the override store live in renderer localStorage or the TM config file (via IPC) for cross-checkout durability? (Leaning config file to match TM's workspace-identity model.)
2. Does TM want a native menu bar at all in v1? If not, the main-process projection layer is deferred and the system is purely renderer-side.
3. How large is the *configurable* subset? Linear ships zero remapping; TM should pick a deliberate curated set rather than "everything is configurable."
4. Is `navigator.keyboard.getLayoutMap()` worth adopting later for accurate physical-key labels on non-QWERTY layouts, accepting Chromium-only support (Electron is Chromium, so it is actually viable here)?

## Actionable Takeaways

1. **Adopt tinykeys** as the matcher; do not hand-roll and do not use mousetrap/hotkeys-js (layout-broken) or react-hotkeys-hook (over-triggers).
2. **Build the five-module `www/src/keybindings/` layer**; migrate the six scattered hooks into the registry, leaving widget-intrinsic keys (Toggle, Ark) in place.
3. **Expose `process.platform` via contextBridge**; derive `isMac`/`$mod` once.
4. **One `formatBinding` function**; wire it to palette, Settings, tooltips, (future) menu.
5. **Model SHIFT/ALT pan/zoom as a separate blur-reset gesture store**, never as accelerators.
6. **Gate global commands behind `when`** so Ark/zag own their component keys; one owner per combo per context.
7. **Ship a curated configurable subset** with conflict detection + reset-to-default; persist a sparse override map (prefer the TM config file).
8. Keep the **main process thin**: no `globalShortcut`; derive any native menu from the registry via IPC.
