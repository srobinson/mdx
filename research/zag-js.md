---
title: Zag.js — Headless UI State Machines for a Token-Styled React SPA
type: research
tags: [zag-js, headless-ui, state-machines, react, accessibility, component-strategy, transport-matters]
summary: Framework-agnostic, zero-CSS FSM primitives (Chakra team) that map 1:1 to transport-matters widget pain; strong fit, MIT, React 19 ready, exceptionally maintained.
status: active
source: github-researcher
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

# Zag.js (chakra-ui/zag)

## Executive Summary

Zag is a framework-agnostic library of **headless UI state machines** from the Chakra UI team. Each interactive widget (tabs, dialog, popover, combobox…) is a finite state machine that emits ARIA roles, `data-*` hooks, keyboard handlers, and event wiring as plain prop objects you spread onto **your own markup**. It ships **zero CSS**. For transport-matters (React 19.2 + Vite 8 + plain-CSS/token styling, no component library) it is a near-ideal fit: it solves the accessibility/behaviour layer without touching styling, and its machines map 1:1 onto every hand-rolled-widget pain point.

## What Zag Is and How React Consumes It

Official docs: *"component interactions modelled in a framework agnostic way"* with adapters for React/Solid/Vue/Svelte, and *"The machine APIs are completely unstyled and give you the control to use any styling solution you prefer."* Positioned as *"the next evolution of Chakra UI,"* inspired by Radix UI and React Aria.

Standalone React usage via `@zag-js/react` is four lines plus prop-getter spreads (`examples/next-ts/pages/tabs/basic.tsx`):

```tsx
import { normalizeProps, useMachine } from "@zag-js/react"
import * as tabs from "@zag-js/tabs"

const service = useMachine(tabs.machine, { id: useId(), defaultValue: "nils" })
const api = tabs.connect(service, normalizeProps)
// then: <div {...api.getRootProps()}> ... <button {...api.getTriggerProps({ value })}>
```

You write every DOM element and `className` yourself; `normalizeProps` adapts the machine's output to React props. `@zag-js/react` depends only on `core/store/types/utilities` and re-exports `useMachine`, `normalizeProps`, `mergeProps`, `Portal`.

**Zero styles confirmed (first-hand):** no `.css` file ships in any `packages/machines/*` or `packages/frameworks/*`. The only `style` keys are functional (floating-element coordinates, tab-indicator transform), never theming. `tabs.connect` (`tabs.connect.ts`) emits `role="tablist|tab|tabpanel"`, `aria-orientation`, `aria-selected`, `aria-controls`, `aria-labelledby`, `aria-disabled`, roving `tabIndex`, plus `data-orientation/-focus/-selected/-disabled` styling hooks.

## Machine Coverage Mapped to TM Pain

50+ machines exist (`packages/machines/`). Direct hits for transport-matters:

- **Tabs reinvented 3× with no arrow-key nav** → `@zag-js/tabs`: `tabs.machine.ts` implements `navigate`, `orientation`, and `syncTabIndex` (roving tabindex + arrow/Home/End). **~5 KB gzip.**
- **HoverCard / hand-coded popover positioning + viewport-flip** → `@zag-js/popover`, `@zag-js/tooltip`, `@zag-js/hover-card`, all using `@floating-ui/dom` for flip/shift. **popover ~22 KB, tooltip ~14 KB gzip** (floating-ui is the weight).
- **FullscreenOverlay modal, no focus trap/restore** → `@zag-js/dialog`: `dialog.machine.ts` wires `trapFocus` (via `@zag-js/focus-trap`), `restoreFocus`, `preventScroll` (`remove-scroll`), `hideContentBelow` (`aria-hidden`). Exactly the missing pieces. **~12 KB gzip.**
- **Collapsible sections** → `@zag-js/accordion` (**~2 KB gzip**) or `@zag-js/collapsible`.
- **Net-new gaps (dropdown/combobox/select/datepicker)** → `@zag-js/menu`, `@zag-js/combobox` (**~25 KB gzip**), `@zag-js/select`, `@zag-js/date-picker` all exist.

## Bundle Cost & React 19

Per-machine, tree-shakeable ESM. `@zag-js/core` (~2 KB gzip) is shared once across all machines, so marginal cost is lower than these standalone figures (which bundle each machine's deps):

| Package | gzip | deps | notes |
|---|---|---|---|
| core | ~2 KB | 2 | shared base |
| accordion | ~2 KB | 5 | |
| tabs | ~5 KB | – | |
| dialog | ~12 KB | 9 | focus-trap, remove-scroll, aria-hidden, dismissable |
| tooltip | ~14 KB | – | floating-ui |
| popover | ~22 KB | 10 | floating-ui + focus mgmt |
| combobox | ~25 KB | 10 | |

(bundlephobia, 2026-06-17.) **React 19 compatible**: `@zag-js/react` peer dep is `react >=18.0.0` and it uses native `useSyncExternalStore`. TM's React 19.2 is in range.

## API Ergonomics: Zag vs Ark UI

**Zag direct** = ~4 lines of wiring per component + you author the full DOM tree and spread prop getters. Slightly verbose, but total control over markup, structure, and `className`. You'd typically wrap each machine in one thin local component once.

**Ark UI** (`ark-ui.com`, same Chakra team — Ark wraps Zag) packages each machine into pre-composed framework components (`<Tabs.Root><Tabs.List><Tabs.Trigger/>`), eliminating the `useMachine`/`connect`/`normalizeProps` boilerplate. Both are headless and styleless. Choose **Zag directly** when you want to own composition and keep markup minimal (fits TM's plain-CSS/token posture); choose **Ark** when you'd rather skip per-component wiring and accept its opinionated component structure.

## Maturity

- **Stars:** 5,116 · **Forks:** 258 · **License:** MIT
- **Latest release:** `@zag-js/hotkeys@1.41.2` (2026-06-05); whole monorepo on `1.41.x`. Repo pushed 2026-06-15.
- **Cadence:** `1.0.0` shipped 2025-02-22 → `1.41.2` by mid-2026 ≈ ~41 minor releases in ~16 months (multiple per month). Stable v1 since early 2025.
- **Issue health:** **3 open issues**, 15 open PRs — aggressive triage by the Chakra team.
- **Adoption:** `@zag-js/react` ≈ **1.0M weekly npm downloads** (week of 2026-06-10). Underpins Chakra UI v3 and Ark UI in production.
- **Maintainer:** Chakra UI core team (Segun Adebayo et al.).

## Relevance to transport-matters

High. Zag gives TM accessibility + behaviour (keyboard nav, focus management, positioning, ARIA) without imposing any styling, preserving the Tailwind 4 + CSS-custom-property token system. It retires the three tab reimplementations (gaining arrow-key nav), the hand-rolled popover flip math, and the focus-trap-less modal in one consistent primitive layer, and it covers the not-yet-built dropdown/combobox/select/datepicker. Cost is bounded and pay-per-machine.

## Recommendation

**Adopt Zag directly** for the behaviour layer; keep markup + tokens as-is. Wrap each machine in a thin local component (`<Tabs/>`, `<Dialog/>`, `<Popover/>`) styled with existing CSS tokens. Reconsider **Ark UI** only if the team prefers pre-composed components over writing the wiring once. Either way the styling story is unchanged.

## Sources Consulted

- Repo: `chakra-ui/zag` (shallow clone) — `packages/frameworks/react/src/index.ts`, `examples/next-ts/pages/tabs/basic.tsx`, `packages/machines/tabs/{tabs.connect.ts,tabs.machine.ts}`, `packages/machines/dialog/{dialog.machine.ts,package.json}`, `CHANGELOG.md`
- `gh` repo stats + open issue/PR counts (2026-06-17)
- npm registry (`@zag-js/react` version/deps, downloads), bundlephobia gzip sizes
- Official docs: zagjs.com/overview/introduction

## Open Questions

- SSR/hydration behaviour under TM's Vite SPA (Zag supports SSR ids; verify no hydration flicker for popover/dialog portals).
- Interaction with framer-motion 12 for enter/exit (Zag exposes `@zag-js/presence`; confirm it composes with existing motion).
