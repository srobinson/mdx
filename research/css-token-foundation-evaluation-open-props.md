---
title: Open Props as CSS Token Foundation
type: research
tags: [css, design-tokens, design-system, open-props, helioy, vanilla-css]
summary: Open Props is an actively maintained, MIT-licensed bundle of ~330 CSS custom properties shipped as granular ESM/CSS submodules. Adoption is low-risk for a vanilla-CSS design system but offers limited value once tokens are decided.
status: active
source: github-researcher
confidence: high
created: 2026-04-30
updated: 2026-04-30
---

## Executive Summary

`open-props` (Adam Argyle / argyleink) is a CSS custom-properties library: a curated, opinionated set of design tokens distributed as one mega-bundle plus per-category submodules. It is purely tokens (plus optional `normalize`, `buttons`, and a small `theme` switcher), with no class utilities. As of v1.7.23 (Jan 2026) the project is actively maintained by a community after Argyle stepped back, with frequent releases. Adoption is low-cost (drop in a CSS `@import`) and low-lock-in (you just consume CSS variables), but for a small marketing-site design system its main value is *seeding* a token scale rather than long-term dependency.

## What It Is

A bundle of CSS custom properties grouped by category. From the source `src/` directory the categories are:

- **Colors**: 18 named hues x 13 stops (gray, stone, red, pink, purple, violet, indigo, blue, cyan, teal, green, lime, yellow, orange, choco, brown, sand, camo, jungle), in three encodings: sRGB hex (`--blue-5`), HSL (`--blue-5-hsl`), and OKLCH HD (`--blue-5-hd`). Plus brand-color and palette files.
- **Sizes**: rem (`--size-1..15`), px (`--size-px-1..15`), fluid (`clamp(...)`), content widths, header widths, named breakpoints (xxs..xxl), `ch`-relative.
- **Typography (`fonts`)**: family stacks (`--font-sans`, `--font-mono`, plus modern font stacks added in PR #498), weights, sizes (rem + fluid), line-heights, letter-spacing.
- **Borders**: `--radius-1..6`, `--radius-round`, `--radius-blob-*`, `--radius-conditional-*`, border-size scale.
- **Shadows**: `--shadow-1..6`, `--inner-shadow-*`, configurable via `--shadow-color` and `--shadow-strength`. Shipped in adaptive (auto dark via `prefers-color-scheme`) and non-adaptive `shadows.light` / `shadows.dark` variants.
- **Animations**: keyframes plus `--animation-*` shorthands (fade-in, slide-out, shake, ping, blink, float, bounce, pulse, spin).
- **Easing**: `--ease-1..5`, `--ease-in/out/in-out-N`, `--ease-elastic-N`, `--ease-spring-N`, plus Robert Penner classics (PR #559).
- **Aspects**: `--aspect-square`, `--aspect-video`, `--aspect-golden`, etc.
- **Gradients**: 30+ ready gradients (`--gradient-1..30`), recently auto-upgraded to OKLAB/HDR.
- **Z-index**: `--layer-1..5`, `--layer-important`.
- **Media queries**: PostCSS `@custom-media` rules (`--OSdark`, `--motionOK`, etc.) — only useful with PostCSS.
- **Masks**: edge fades, corner cuts.

## Install + Import (npm/bun, no CDN)

```bash
bun add open-props
```

The package's `exports` map (in `package.json`) is the source of truth. Vite resolves bare-specifier CSS imports cleanly via `node_modules`:

```css
/* tokens (everything) */
@import "open-props/style";

/* optional: opinionated CSS reset + light/dark surface vars */
@import "open-props/normalize";

/* opt-in dark/light only — non-adaptive, you control switching */
@import "open-props/normalize/light";
@import "open-props/normalize/dark";

/* manual theme switch (vars under .light / .dark classes instead of media query) */
@import "open-props/switch/light";
@import "open-props/switch/dark";
```

Subset imports — pick categories instead of the full bundle:

```css
@import "open-props/sizes";
@import "open-props/borders";
@import "open-props/fonts";
@import "open-props/easings";
@import "open-props/shadows";          /* adaptive */
@import "open-props/shadows/light";    /* fixed */
@import "open-props/animations";
@import "open-props/gray";              /* one hue */
@import "open-props/blue-hsl";          /* one hue, HSL form */
```

JS import (rare; use only for inline-style props or theming JS):

```js
import OpenProps from "open-props";       // camelCase keys
import { sizes } from "open-props/src/sizes";
```

There's also a JSON design-tokens export (`open-props/tokens`, `open-props/style-dictionary-tokens`) for cross-platform pipelines.

## Customization Story

- **Override individual variables**: trivially. They're plain CSS custom properties on `:where(html)` (specificity 0,0,0). Redeclaring `--size-3: 1.125rem` in your own `:root {}` wins.
- **Subset what you import**: yes, this is the intended path — the `exports` map in `package.json` lists ~50 submodules. Import only `sizes`, `borders`, `fonts` and skip the 18 color packs you don't want.
- **Tree-shake unused tokens**: not at the variable level. CSS custom properties are runtime; a CSS minifier cannot drop unused declarations because it can't statically prove they're unused. Unused `--*` declarations remain in the bundle. The "tree-shake" is manual — done at import-pick time.
- **PostCSS path**: `open-props/postcss/style` returns the unminified PostCSS source if you want to run it through your own PostCSS chain (`postcss-import`, `postcss-preset-env`).

## Architecture Choices

Open Props ships in **four selector flavors**, generated from the same `props.*.js` source files via the `build/props.js` generator:

| Build      | Selector       | When to pick                                                                                  |
| ---------- | -------------- | --------------------------------------------------------------------------------------------- |
| Default    | `:where(html)` | Light DOM. Specificity 0,0,0 — easy to override. The standard choice.                          |
| `nowhere`  | `html`         | Build pipelines that strip `:where()` (rare); legacy browser concerns.                         |
| `prefixed` | `:where(html)` | All vars prefixed `--op-*` to avoid collision with your own tokens or another design system. |
| `shadow`   | `:host`        | Web Components / Shadow DOM consumers — vars become available inside the shadow root.        |

The default `:where()` choice is deliberate and good: zero specificity means your overrides need no `!important` games. It's the right choice for a design system root.

## Versioning + Maintenance (as of 2026-04-30)

- Latest npm: **v1.7.23** (2026-01-31). 5,367 stars, 76 open issues, 210 forks.
- 2026 has shipped 1.7.18 → 1.7.23 in a single late-January burst (release-pipeline fixes + design-token resolver enhancements).
- 2025 saw v1.7.15 (April) and v1.7.16 (July) and v1.7.17 (December) — quiet but real. PRs from external contributors are merging.
- The last "named" release was `v1.6.0 "Step towards v2"` in Sep 2023. The promised v2 has not landed; momentum is incremental on 1.7.x.
- License: MIT. Single-author origin (Adam Argyle, Google) but PR throughput in 2025-2026 is from a wider contributor pool. Treat it as community-maintained.

## Tradeoffs vs Hand-Rolled Tokens

What you **gain**:

- A vetted scale immediately. The size, radius, shadow, and easing scales are the ones a senior frontend engineer would arrive at after a week of work. Skipping that week is real value.
- Shadow tokens that compose via `--shadow-color` + `--shadow-strength` — non-trivial to build right.
- Three color formats (hex / HSL / OKLCH) without you maintaining the conversions.
- Prebuilt fluid `clamp()` size and font scales.
- Optional normalize + buttons if you want a starting style baseline (you can ignore both).

What you **give up**:

- **Naming conventions you didn't choose.** `--size-3`, `--font-size-4`, `--gray-7` are numeric scales. If your design system wants semantic names (`--space-md`, `--font-body`, `--surface-muted`), you're either renaming everything (defeating the point) or maintaining a translation layer.
- **Bytes.** The full bundle is ~50KB minified. Subsetting helps but every imported submodule contributes vars you'll never reference.
- **A coupling to someone else's taste.** Eighteen color hues is too many for most marketing sites. Even if you import only `gray` and one accent, you've got a dozen unused stops in your CSS.
- **Indirection in your own code.** `padding: var(--size-3)` is fine until a designer asks "why is the spacing 16px there?" — the answer ("because Open Props' size-3 is 1rem") is one extra lookup forever.
- **Risk of project stalling.** v2 has been "soon" for 2.5 years. If you adopt and maintenance pauses, you own the fork.

## Recommendation

For a small marketing site / Storybook design system in 2026 with a vanilla-CSS direction: **skip Open Props as a runtime dependency. Use it once as a reference, then hand-roll.**

Reasons:

1. The "win" is the *scale values*, not the package. Copy the size scale, the easing curves, the shadow composition trick — a single 200-line `tokens.css` you own beats a 50KB import you'll never fully use.
2. A design system's tokens are its identity. `--space-md` reads better in your codebase than `--size-3`. You will end up wrapping anyway.
3. Storybook 10 + Astro 6 want a small, predictable token surface for component docs. Open Props' breadth is noise in that context.
4. Open Props' best ideas — the OKLCH colors, the shadow strength composition, the fluid `clamp` sizes, the easing curves — are easy to lift in 30 minutes.
5. Keep the package on the shortlist *if* you later want a quick prototype starter or a normalize.css replacement. The `normalize` submodule alone is a respectable choice.

If you do adopt: import only `open-props/sizes`, `open-props/borders`, `open-props/fonts`, `open-props/easings`, `open-props/shadows/light` + `open-props/shadows/dark`, plus one or two color hues. Wrap the raw vars in semantic tokens at your `:root` layer so consumer components reference *your* names.

## Sources Consulted

- `package.json` — full `exports` map (the canonical install reference).
- `src/index.css`, `src/index.js` — what's in the default bundle.
- `src/props.sizes.css`, `src/props.shadows.css` — token shape examples.
- `src/extra/normalize.css`, `src/extra/theme.css` — opinionated extras.
- `readme.md` — CDN-first; npm details live in `package.json`.
- `CHANGELOG.md` — release cadence (auto-generated).
- GitHub API: stars, issues, latest release, recent commits.

## Open Questions

- Will v2 ever land? The 1.7.x train is merging fixes but the architectural reset (referenced in v1.6.0 release notes) hasn't materialized. If you adopt, plan for 1.7.x being the long-term shape.
- The `open-props.resolver.json` and design-token JSON outputs are recent (2025-2026) work — if Helioy ever needs Style Dictionary or Figma sync, these are worth a second look.
