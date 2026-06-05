---
title: Transport Matters — Desktop/Canvas UI Component Strategy Proposal
type: proposal
tags: [ui-strategy, component-library, ark-ui, zag-js, panda-css, park-ui, vanilla-css, headless-ui, session-canvas, desktop, transport-matters]
summary: For the desktop/canvas surface (www/src/session-canvas, vanilla CSS), adopt Ark UI as a headless component layer styled via data-* selectors in the existing per-component .css files. Reject Panda and Park as dependencies; mine Park as a styling reference. Tailwind editor/observability area is explicitly out of scope.
status: proposed
created: 2026-06-17
updated: 2026-06-17
decided_by: warroom (4x github-researcher) + firsthand desktop/canvas inventory, orchestrator synthesis
scope: canvas surface only (session-canvas + future desktop UI); Tailwind editor/observability area untouched
research:
  - ~/.mdx/research/zag-js.md
  - ~/.mdx/research/ark-ui.md
  - ~/.mdx/research/panda-css.md
  - ~/.mdx/research/park-ui.md
---

# Transport Matters — Desktop/Canvas UI Component Strategy

## Scope and target (read first)

This proposal targets the **desktop/canvas surface only**: `www/src/session-canvas/` (the canvas, dock, route-switcher, pane chrome, command bar, and resource/terminal viewers that the Electron desktop presents), plus future desktop-presented UI such as the launcher. This surface is **vanilla CSS**: 14 plain `.css` files (~1.4k LOC) imported per component, semantic class names, **zero Tailwind**.

Explicitly out of scope: the Tailwind-based editor/observability area of `www` (`components/editor`, `components/detail`, `routes`). The two styling worlds stay separate by design.

Architecture note: `desktop/` is a thin **Electron shell** (main/preload TS only, no renderer UI) that loads `www` over `http://127.0.0.1:{port}`. The vanilla-CSS surface lives inside `www` under `session-canvas/`; the Electron process itself has a `rendererBoundary.test.ts` keeping React out of the main process.

## Recommendation (TL;DR)

**Adopt Ark UI (`@ark-ui/react`) as a headless behavior layer for the canvas surface. Style its parts via `data-scope`/`data-part`/`data-state` selectors in the existing per-component `.css` files. Reject Panda CSS and Park UI as dependencies. Mine Park UI's component files + recipe taxonomy as a one-time styling reference.**

The four candidate projects form a layered chain plus a styling engine that does not belong on a vanilla-CSS surface at all:

```
Zag.js          finite-state-machine behavior primitives   (logic)
  └─ Ark UI     thin React components over Zag, unstyled    (headless components)   ← ADOPT
       └─ Park  Ark pre-styled with Panda recipes           (Panda-coupled)         ← reject as dep, mine as ref

Panda CSS       build-time atomic-CSS engine + tokens                                ← reject (foreign to a vanilla-CSS surface)
```

We want the behavior layer (Ark, which carries Zag with it). The styling layer is already decided: hand-written vanilla CSS. Ark is the only one of the four that respects that, and it fits a vanilla-CSS surface better than it fits Tailwind.

## Grounded in the canvas surface's actual interactive widgets

Firsthand inventory of `session-canvas/` (71 tsx, ~6.9k LOC; interactive chrome concentrated in `components/`):

| Widget today | Component | Current hand-wiring | Ark/Zag answer |
|---|---|---|---|
| Menu / dropdown | `RouteSwitcher` | hand-wires `aria-haspopup` + `aria-expanded` + `role="menu"`/`menuitem` | `menu`: roving focus, typeahead, positioning, ARIA |
| Command palette | `CanvasCommandBar` + `CommandBarSections` | manual filter + keyboard nav + sectioned list | `combobox`/`listbox`: filtering, active-descendant, sectioning |
| Toolbars + toggle buttons | `PaneChrome`, `PaneWindow`, `PaneDock` | `role="toolbar"`, `aria-pressed`, @dnd-kit | `toolbar` / `toggle` (lower value; current buttons are fine) |
| Toast / status | `aria-live` + `role="alert"`/`"status"` regions | inline live regions | `toast`: queueing, dismiss, a11y announcements |
| Param sliders | `SceneParamControls`, lab `ControlsPanel` | custom numeric controls | `slider` / `number-input` if drag/step needed |

The highest-value targets are `RouteSwitcher` (a menu the code already reimplements by hand) and the command bar. Note: tabs / popover / modal are **not** the canvas pain, those were in the out-of-scope Tailwind editor area.

Blast radius: ~5-8 widget touchpoints inside `session-canvas`, not a rewrite of 71 files.

## The styling fit is cleaner here than with Tailwind

Ark is **verified truly unstyled** (first-hand in source): ships zero `.css`, `sideEffects: false`, dependencies are exclusively `@zag-js/*` + `@internationalized/date`, **no `@pandacss` dependency anywhere**. It styles through stable attributes it emits but never reads: `data-scope`, `data-part`, `data-state`, plus `data-selected`/`data-orientation`/`data-disabled`.

That maps directly onto the canvas's existing idiom, semantic selectors in per-component `.css` files:

```css
/* route-switcher.css — exactly the file that exists today */
[data-scope="menu"][data-part="trigger"] { /* ... */ }
[data-scope="menu"][data-part="item"][data-state="active"] { /* highlighted */ }
[data-scope="menu"][data-part="content"] { /* portal panel */ }
```

No utility classes, no generated directory, no second token system. Attribute selectors are the natural vanilla-CSS way to style headless parts, so the canvas surface is arguably the ideal Ark consumer.

## Why Ark over Zag-direct (the one real fork)

The Zag and Ark research reached the same facts, different recommendations. For this surface, **Ark wins**:

- Both ship zero CSS and style through the same `data-*` attributes, so the vanilla-CSS posture is preserved identically. Zag-direct holds no styling advantage.
- Adopting Ark *is* adopting Zag (Ark pins `@zag-js/*` in lockstep and is a thin React layer over the same machines). Zag-direct means hand-writing `useMachine` + `connect` + `normalizeProps` + the full DOM tree per widget. `RouteSwitcher` already does the equivalent by hand; Ark's `Menu.Root`/`Trigger`/`Content` retires exactly that boilerplate.
- We consume **React only**. Zag's framework-agnosticism buys nothing here.

**Decision: Ark UI as the primary headless layer; reserve Zag-direct as an escape hatch** for a bespoke widget Ark's composition can't express (use Ark's pinned `@zag-js/*` version).

## Why not Panda, why not Park

**Panda CSS — reject.** On a Tailwind surface Panda is a "replacement candidate." On this **vanilla-CSS** surface it is simply a foreign body: it would introduce a build-time atomic-CSS engine, a mandatory `panda codegen` step, and a generated `styled-system/` directory onto a surface that deliberately uses hand-written `.css`. It is **not required by Ark or Zag** (verified: `@ark-ui/react` has zero `@pandacss` dep). No reason to bring it here.

**Park UI — reject as a dependency, mine as reference.** Park is **inseparable from Panda** (provable in source: CLI aborts without `panda.config.ts`, mutates your Panda config, components import generated `styled-system/recipes`). So it cannot be consumed on a Panda-free surface. But each Park component cleanly separates **Ark composition (portable)** from **Panda styling binding (replaceable)**. Treat Park's component files + recipe variant matrices (e.g. menu/combobox slot wiring) as a structural cheat-sheet, re-expressed as vanilla CSS in our `.css` files. ~80% of Park's value at zero coupling.

## Maturity / risk snapshot (verified 2026-06-17)

| Project | Verdict | Stars | Latest | License | Health |
|---|---|---|---|---|---|
| Ark UI | **Adopt** | 5,235 | `@ark-ui/react@5.37.2` (2026-06-08) | MIT | 13 open issues, stable v5, Chakra team |
| Zag.js | Adopt (via Ark) | 5,116 | `1.41.x` (2026-06-05) | MIT | 3 open issues, ~1M weekly dl, stable v1 |
| Panda CSS | Reject | 6,087 | `1.11.3` / `2.0.0-beta.0` | MIT | foreign to a vanilla-CSS surface |
| Park UI | Reject as dep | 2,322 | `@park-ui/cli@1.0.1` (2025-11-20) | MIT | single maintainer; Panda-coupled |

The load-bearing layer we adopt (Ark + Zag) is Chakra-team-backed with multiple releases a month.

## Migration plan

Pilot-first, never a big-bang rewrite, all inside `session-canvas`:

1. **Pilot — `RouteSwitcher` → Ark `Menu`.** It already hand-wires `aria-haspopup`/`aria-expanded`/`role=menu`. Swap to `Menu.*`, style `data-part` selectors in `route-switcher.css`. Validate: keyboard nav + typeahead, positioning, visual parity, framer-motion enter/exit still composes, no portal flicker in the Electron BrowserWindow. Establish the thin local wrapper pattern (`<Menu/>` owning canvas classes).
2. **Command bar → Ark `combobox`/`listbox`.** Move `CanvasCommandBar`/`CommandBarSections` filtering + keyboard nav onto the machine; keep section rendering.
3. **Toasts → Ark `toast`.** Consolidate the `aria-live` status regions into one queued, dismissible primitive.
4. **Net-new on Ark by default.** Future desktop UI (e.g. the launcher) builds dropdowns/selects/menus on Ark from the start, styled in vanilla CSS, using Park files as the structural reference.

**Discipline:** pin `@ark-ui/react` and its `@zag-js/*` together; consume each component through one thin local wrapper that owns the `.css` styling, so the dependency stays one swappable seam. Leave the Tailwind editor area untouched.

## Open questions to close in the pilot

- Portal/hydration behavior of `menu`/`popover` portals inside the Electron BrowserWindow (client-only SPA, likely fine).
- `@zag-js/presence` vs framer-motion 12 for canvas pane enter/exit transitions.
- Bundle delta is low-stakes for a local Electron desktop, but still tree-shake; `combobox` ~25 KB, `menu` lighter.
- Slot-recipe porting effort for compound components (menu/combobox) into per-slot vanilla-CSS class maps.

## Alternatives outside the commissioned scope (flagged, not researched)

This pass evaluated only the Zag/Ark/Panda/Park stack you named. Adjacent headless options for a vanilla-CSS React surface: **Radix Primitives**, **React Aria (Adobe)**, **Base UI (MUI)**, **Headless UI (Tailwind)** — all unstyled, all stylable with plain CSS. General-knowledge characterization only (NOT verified this pass): Ark's edges are broadest component coverage and the `data-*` styling model that suits vanilla CSS; Radix is the incumbent but cadence has slowed; React Aria is the most rigorous on a11y but heavier; Base UI is newer. If you want Ark stress-tested against Radix/React Aria before committing, that is a one-session follow-up.
