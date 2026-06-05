---
title: Park UI — design system on Ark UI + Panda CSS (component strategy evaluation)
type: research
tags: [park-ui, ark-ui, panda-css, component-library, shadcn-model, transport-matters, ui-strategy]
summary: Park UI is a shadcn-style copy-in design system that hard-depends on Panda CSS; reject as a dependency for TM's Tailwind/token stack, but mine its Ark composition + recipe taxonomy as a reference and adopt Ark UI directly.
status: active
source: github-researcher
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

# Park UI

Repo: https://github.com/cschroeter/park-ui · docs https://park-ui.com · 2322 stars, 108 forks, MIT, created 2023-08-02. Single maintainer: Christian Schröter (`grizzly_codes`). Last repo push 2026-04-10; last code commit 2026-02-21. Latest npm `@park-ui/cli@1.0.1` published 2025-11-20 (~7 months before today, 2026-06-17). Issue health is good: 9 open issues, 10 open PRs.

## Executive Summary
Park UI is a **design system, not a runtime library**: a set of Ark UI components pre-styled with a Panda CSS preset (tokens + recipes), distributed shadcn-style via a CLI that copies the source into your repo so you own it. Its styling value is **inseparable from Panda CSS** — the CLI refuses to run without a `panda.config.ts`, and every component imports Panda's generated `styled-system/*`. For a stack that has rejected Panda, Park is unusable as a dependency, but it is a high-quality **reference** for Ark composition patterns and a variant taxonomy you can re-express in Tailwind/plain CSS.

## 1. What Park Is
Two halves, both copy-in as of v1:
- A **Panda preset** (`@park-ui/preset`, now `private` in the workspace — `packages/preset/package.json`) supplying tokens, conditions, animation styles, and ~60 recipes (`packages/preset/src/recipes/*.ts`). Colors are generated from Radix Colors (`@radix-ui/colors` devDep, `packages/preset/generate-colors.ts`).
- **Components** (`components/{react,solid,vue}`) — 62 React UI components in `components/react/src/components/ui/`. Each wraps an Ark UI primitive and binds it to a Panda recipe.

## 2. CRITICAL — Is Park's value separable from Panda? **No.**
Hard coupling is provable in source:
- **CLI aborts without Panda.** `packages/cli/src/commands/add.ts` wraps the whole install in `withPandaConfig(withTSConfig(withConfig(program)))`. `packages/cli/src/utils/panda-config.ts:getConfigPath` looks for `panda.config.ts`; if absent it errors and prints "Visit https://panda-css.com/docs/overview/getting-started". No Panda config → CLI does nothing.
- **CLI mutates your Panda config.** `updatePandaConfig` (same file) loads `panda.config.ts` via `magicast` and `deepMergeObject`s recipe/theme/color imports into it; `packages/cli/src/utils/recipes.ts` AST-injects each recipe into the Panda `recipes`/`slotRecipes` map.
- **Components import Panda codegen output.** `components/react/src/components/ui/button.tsx` imports `styled` from `styled-system/jsx` and `button` from `styled-system/recipes`, then `const BaseButton = styled(ark.button, button)`. `styled-system/*` only exists after `panda codegen` runs against a config containing Park's recipes (`prepare: "panda codegen"` in `components/react/package.json`). No Panda = those imports don't resolve = components don't compile.
- **Recipes are Panda DSL, not CSS.** `packages/preset/src/recipes/button.ts` uses `defineRecipe` from `@pandacss/dev` with Panda token refs (`borderRadius: 'l2'`, `bg: 'colorPalette.solid.bg'`, `textStyle`, `focusVisibleRing`, `layerStyle`). These resolve only through Panda's engine.

**Verdict: if you reject Panda, Park is not usable as-installed at all.**

## 3. Distribution Model — copy-in / own-the-code (shadcn-style)
`npx @park-ui/cli add <component>` fetches registry items and writes them into your repo at aliased paths (`packages/cli/components.json`: `ui → ~/components/ui`, `recipes → ~/theme/recipes`, `theme → ~/theme`). The registry (`packages/preset/registry.json`) lists items typed `registry:ui | registry:recipe | registry:theme | registry:color` with file lists and `registryDependencies` (e.g. color palettes `red`, `green`). What the CLI generates per component: (a) the component `.tsx` (Ark composition + `styled()` binding), and (b) the Panda recipe(s) registered into your `panda.config.ts`. You then run `panda codegen`. So v1 is **more shadcn-like than before** — even the preset is copy-in now, not an installed npm dependency.

## 4. KEY — Could we mine Park as a reference and re-style in Tailwind/CSS?
**Yes, and this is the realistic path.** Each component has two separable layers:
- **Ark composition (valuable, portable).** e.g. `components/react/src/components/ui/dialog.tsx`: `createStyleContext(dialog)` + `withContext(Dialog.Backdrop, 'backdrop')` slot mapping; `button.tsx`: the `ButtonGroup` props-context pattern and loading-state wiring. This logic is pure Ark + React and carries over.
- **Panda styling binding (replaceable).** The `styled(...)`, `styled-system/recipes`, `styled-system/jsx` imports, and `createStyleContext` (a Panda helper that maps slot names to recipe classes).
To mine: keep the Ark structure, drop the `styled-system` imports, and reimplement the thin `styled`/`createStyleContext` seam to apply your own Tailwind/CSS classes; translate each recipe's `variant`/`size` matrix (e.g. `button.ts`'s 5 variants × 7 sizes) into your token system. Practical for simple recipes; slot recipes (dialog, menu, combobox) need a per-slot class map. **Net: treat Park's component files + recipe variants as a styling/structure cheat-sheet, not a build dependency.**

## 5. Theming
Panda semantic tokens + Radix-derived color palettes. `colorPalette.*` token references let any palette be swapped per-subtree; radius via token scale (`l1/l2/l3`); dark mode via Panda `conditions`/`_dark` and semantic token pairs. All of this lives in the preset's `src/theme/tokens/*` and is meaningful only inside Panda.

## 6. Coverage & Frameworks
62 React UI components including the exact gaps TM has: `tabs`, `popover`, `tooltip`, `dialog`, `drawer`, `collapsible`, plus `combobox`, `select`, `menu`, `number-input`, `date-picker`, `color-picker`, `pagination`. Frameworks: **React, Solid, Vue** (separate `components/*` workspaces; Vue support is newer and thinner — see open issue #551). Quality is high: `'use client'`, `forwardRef`, props contexts, a11y-correct Ark primitives.

## 7. Maturity & Risk
- **Versions:** `@park-ui/cli@1.0.1` (2025-11-20), built against `@ark-ui/react@5.30.0` (upstream now 5.37.2) and `@pandacss/dev@1.8.1`. Old `@park-ui/panda-preset@0.43.1` (2024-11-22) is the abandoned pre-v1 line.
- **Cadence:** slow but alive. v1 stabilized late 2025; commits trail off after Feb 2026. GitHub Releases are stale (last cut Nov 2024) — npm is the real signal.
- **Single-maintainer risk: real.** Park is one person (Christian Schröter). Mitigant: the load-bearing primitives underneath — **Ark UI, Zag.js, Panda CSS** — are Chakra-team / Segun Adebayo projects with broad backing. Park is a thin styled layer over robust foundations.
- License MIT (no risk).

## 8. Honest Take
Over "Ark + your own styling," Park adds: a curated recipe/variant taxonomy, ready-made slot wiring, and a generated theme — but **only if you adopt Panda**. The dependency it asks for (Panda's atomic CSS engine + codegen + config) is large and would sit awkwardly beside TM's Tailwind 4 + CSS-token setup. Not worth the hard Panda dependency.

## Relevance to Transport Matters
TM is React 19.2 / Vite / TS, Tailwind 4 + CSS tokens, no component library, needing tabs/popover/tooltip/modal/collapsible + future dropdown/combobox/select.
- **Reject** Park-as-dependency: it forces Panda, which TM's posture excludes.
- **Adopt Ark UI directly** (`@ark-ui/react`) for the headless behavior of those components, styled with TM's existing Tailwind/token system. Ark is the genuinely reusable, well-backed primitive here.
- **Use Park's component files as a reference** for Ark composition and variant structure while writing TM-native styles. This captures ~80% of Park's value at zero coupling cost.

## Sources Consulted
README.md; root + `packages/cli` + `packages/preset` + `components/react` `package.json`; `packages/cli/src/commands/add.ts`; `packages/cli/src/utils/{panda-config,recipes}.ts`; `packages/cli/components.json`; `packages/preset/registry.json`; `packages/preset/src/recipes/button.ts`; `components/react/src/components/ui/{button,dialog}.tsx`; `gh repo/issue/pr` + `npm view` metadata.

## Open Questions
- Effort to reimplement `createStyleContext` for slot recipes against Tailwind (the main porting cost for compound components).
- Whether Ark UI's bundle/SSR characteristics fit TM's Vite SPA (likely fine; not verified here).
