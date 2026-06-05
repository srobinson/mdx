---
title: Ark UI — Headless Components for a Plain-CSS Design System
type: research
tags: [ark-ui, headless-ui, zag-js, react, component-library, transport-matters, ui-strategy]
summary: Ark UI is a truly unstyled, Zag-powered headless component library (45+ components) that ships zero CSS and styles via data-* attributes with any CSS solution — strong fit for transport-matters' plain-CSS/token posture.
status: active
source: github-researcher
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

# Ark UI

## Executive Summary

Ark UI (`chakra-ui/ark`, 5,235 stars, MIT) is a headless, accessible UI library of 45+ components built on top of [Zag.js](https://zagjs.com) finite state machines, with first-class packages for React, Vue, Solid, and Svelte. It ships **zero CSS** and is styled entirely through `className` + `data-*` attributes, working with Tailwind, plain CSS, or CSS modules. **Panda CSS is not required** — that coupling belongs to Park UI, a separate styled layer. For transport-matters (React 19, Vite, Tailwind 4 + CSS-token, no component library), Ark is a strong fit: it solves the reinvented-tabs / hand-rolled-popover / no-focus-trap-modal pain without imposing a styling engine or a token system.

## What Ark Is

A headless primitive library. Each component is a set of unstyled, composable parts whose behavior, keyboard interaction, focus management, and ARIA wiring are driven by a Zag.js state machine. Ark is the thin React rendering layer over Zag; the logic lives in `@zag-js/*` packages. README (`packages/react/README.md`) describes it as "a headless, open-source UI library with over 45+ components designed for building reusable, scalable Design Systems." The clone has **61 component directories** under `packages/react/src/components/`.

## Critical Question: Is Ark Truly Unstyled?

**Yes — verified in source.**

- `find packages/react/src -name "*.css"` → **0 files**. Ark ships no stylesheet.
- `packages/react/package.json` sets `"sideEffects": false` and declares **no `@pandacss/*` dependency**. The only "panda" strings in the tree are mock data in tree-view examples (e.g. `{ id: 'node_modules/pandacss', name: 'panda' }`), not real deps.
- Dependencies are exclusively `@zag-js/*` (pinned `1.41.2`) plus `@internationalized/date`. Peer deps are only `react >=18` / `react-dom >=18`.

Park UI is what styles Ark with Panda CSS, but **Ark itself is style-agnostic**. You bring your own CSS.

## How You Style It (Mechanism)

Every part renders through a polymorphic factory element `ark.<tag>` and spreads Zag "connect" props. Example from `packages/react/src/components/tabs/tab-trigger.tsx`:

```tsx
export const TabTrigger = forwardRef<HTMLButtonElement, TabTriggerProps>((props, ref) => {
  const [tabProps, localProps] = splitTriggerProps(props, ['disabled', 'value'])
  const tabs = useTabsContext()
  const mergedProps = mergeProps(tabs.getTriggerProps(tabProps), localProps)
  return <ark.button {...mergedProps} ref={ref} />
})
```

`getTriggerProps()` (from Zag) emits stable hooks for CSS targeting: `data-scope`, `data-part`, `data-state`, and state flags like `data-selected` / `data-orientation` / `data-disabled`. The part vocabulary comes from each component's anatomy — `tabs.anatomy.ts` is literally `export { anatomy as tabsAnatomy } from '@zag-js/tabs'`. First-hand evidence of the contract in source: `data-scope="presence"`, `data-part="root"`, `data-part="child"`, `data-part="parent"`.

So with plain CSS you target:

```css
[data-scope="tabs"][data-part="trigger"] { /* base */ }
[data-scope="tabs"][data-part="trigger"][data-state="active"] { /* selected */ }
```

Or with Tailwind, attach `className` directly and/or use `data-[state=active]:…` variants. Both work because Ark only emits the attributes; it never reads them. (No CSS examples live in the repo itself — concrete styling samples are on ark-ui.com docs, since the repo ships nothing styled.)

## Component Coverage vs transport-matters Needs

All current pain points and likely-future needs are covered (verified present as directories):

| Need (now) | Ark component | Notes |
|---|---|---|
| Tabs w/ arrow-key nav | `tabs` | Keyboard nav via `@zag-js/tabs` machine — replaces the 3x reinvented tabs |
| Hand-coded popover/tooltip | `popover`, `tooltip`, `hover-card` | All three exist as distinct machines |
| Modal w/ focus trap | `dialog` + `focus-trap` | Dedicated `focus-trap` component; dialog/drawer manage scroll-lock + focus |
| Collapsibles | `collapsible`, `accordion` | |

| Likely future | Ark component |
|---|---|
| Combobox / Select / Menu | `combobox`, `select`, `menu`, `listbox`, `navigation-menu` |
| Date picker | `date-picker`, `date-input` (uses `@internationalized/date`) |
| Toast | `toast` |
| Tree view | `tree-view` |

## API Surface

- **Composition**: `Root` / `Trigger` / `Content` part components per the anatomy; plus a `RootProvider` variant (`tabs-root-provider.tsx`) for driving the machine externally.
- **`asChild`** polymorphism: `factory.ts` implements `withAsChild` (credited "to the Radix team") so any part can merge its props/behavior onto a custom child element.
- **Controlled vs uncontrolled**: `value` / `defaultValue` pattern via the underlying Zag machine.
- **React 19**: peer `react >=18` covers 19; `factory.ts` has explicit React-19 `ref` getter handling, and the React CHANGELOG records a React 19 Strict Mode fix for dialog/drawer/popover scroll-lock. React 19 is supported.
- **Bundle / tree-shaking**: `sideEffects: false`, per-component subpath `exports`, and one `@zag-js/*` machine pulled per component → import only what you use.
- **Zag coupling**: every `@zag-js/*` dep is pinned to exactly `1.41.2` against Ark react `5.37.2`. Upgrades move in lockstep; pin both together.

## Accessibility

WAI-ARIA roles, keyboard interaction, and focus management are implemented inside the Zag state machines rather than left to the consumer — this is the core value over hand-rolling. Dedicated `focus-trap` primitive backs dialog/drawer.

## Maturity

- **Stars**: 5,235; **forks**: 201; **license**: MIT; maintained by the Chakra UI team.
- **Latest stable**: `@ark-ui/react@5.37.2`, released **2026-06-08** (9 days before today, 2026-06-17). Repo `pushedAt` is today — very active.
- **Release cadence**: rapid (5.37.0 → .1 → .2 inside ~2 weeks). Stable major **v5**.
- **Health**: only **13 open issues**. Multi-framework parity (React/Vue/Solid at 5.37.x; Svelte trails at 5.22.x).

## Relevance to transport-matters

Ark matches the "fully open, plain-CSS/token-leaning" posture better than any styled library would: no CSS to override, no Panda/Chakra runtime, no design tokens imposed. We keep Tailwind 4 + CSS custom-property tokens and style Ark parts via `data-*` selectors or `className`. It directly retires the tabs/popover/dialog/collapsible duplication and gives a stable upgrade path to combobox/select/menu/date-picker/toast without re-architecting. Cost: a new `@ark-ui/react` dependency tree (≈70 `@zag-js/*` packages, tree-shaken) and lockstep Ark↔Zag version pinning.

## Sources Consulted

- `packages/react/package.json` (deps, peers, `sideEffects`, exports)
- `packages/react/src/components/` (61 dirs), `tabs/tab-trigger.tsx`, `tabs/tabs.anatomy.ts`, `factory.ts`
- `find … -name "*.css"` (0 results), data-attr grep across `src`
- `packages/react/README.md`, `CHANGELOG.md`; `gh repo view` / `gh release list` (stars, releases, issues)

## Open Questions

- Exact gzipped bundle delta for the specific components TM will adopt (measure after install; per-component machines vary).
- Svelte parity lag (5.22 vs 5.37) is irrelevant to TM's React-only use but worth noting if the stack ever diversifies.
