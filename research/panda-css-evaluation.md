---
title: Panda CSS evaluation for helioy.com (Astro 6 + tokens-first vanilla CSS)
type: research
tags: [css, design-tokens, panda-css, astro, build-tooling, evaluation]
summary: Panda is a build-time CSS-in-JS engine with a strong token system and codegen. For a small dark-only Astro marketing site already running Lightning CSS + custom-properties, it is overkill — the abstraction tax exceeds the win until component count and variant count grow.
status: active
source: github-researcher
confidence: high
created: 2026-04-30
updated: 2026-04-30
---

# Panda CSS evaluation for helioy.com

## Verdict (read this first)

**Stay on hand-rolled vanilla CSS + Lightning CSS for helioy.com.** Panda is well engineered and not a "framework lock-in" trap, but for a brand-new dark-only marketing site with 8 to 12 components, you would buy:

- a generated `styled-system/` directory (CSS, JS factories, types) checked into your repo or `.gitignore`d
- a PostCSS pass that scans every `.astro/.tsx/.jsx` source file
- a TypeScript codegen step you must run before dev/build (`panda codegen` in `prepare`)
- an opinionated breakpoint system (`sm/md/lg/xl/2xl` mobile-first min-width) that you would have to reconcile with your `@custom-media (--bp-md)` setup
- a JS object DSL for styles instead of CSS files

In exchange you get: typed token autocomplete, conditional styles (`_hover`, `lg:`), recipes/cva for variants, and atomic class extraction. None of that is load-bearing for a marketing site whose CSS surface is dominated by a handful of layout primitives, a hero, and prose.

Panda starts paying off around the inflection where (a) you have ten-plus components with three-plus variants each, (b) multiple brand themes or light/dark switching beyond `prefers-color-scheme`, or (c) a team large enough that ad-hoc CSS classes start drifting from tokens. None of those describe helioy.com today.

If you outgrow the hand-rolled setup, Panda is a credible target. The token model maps cleanly onto your existing `:root` custom properties, and the Astro integration is real (sandbox: `sandbox/astro/`). It is not a one-way door.

---

## 1. What Panda actually is

Panda is a **build-time, type-safe CSS-in-JS** engine. It belongs to the same generation as vanilla-extract and Linaria, not the runtime Emotion/styled-components generation.

The pipeline (from `SYSTEM_ARCHITECTURE.md` and `packages/parser`, `packages/generator`):

1. You write style objects in JS/TS/JSX/Astro/Vue/Svelte: `css({ color: 'red.500', _hover: { color: 'red.600' }})`.
2. A PostCSS plugin (`@pandacss/postcss`) or CLI watcher invokes the **Builder** (`packages/node`).
3. The **Parser** (`packages/parser`, ts-morph based) walks each source file's AST, finds calls to `css`, `cva`, `sva`, `styled`, `token`, etc., and statically extracts their style objects.
4. The **StyleEncoder** turns each unique declaration into an atomic class (e.g., `.bg_red_500`, `.fs_lg`).
5. The **Generator** (`packages/generator`) emits a `styled-system/` directory with: CSS (tokens, reset, atomic utilities, keyframes), JS factories per framework, and TypeScript types reflecting your config.
6. PostCSS layers it under `@layer reset, base, tokens, recipes, utilities` — a single line you put in your entry CSS (`packages/cli` README; `sandbox/astro/panda.css`).

**Zero runtime CSS-in-JS.** No serialization, no `<style>` injection. The shipped artifact is plain atomic CSS plus thin JS helper functions that just concatenate class names.

### Comparison

| Tool | When CSS exists | Style author surface | Atomic? | Type-safe tokens? |
|---|---|---|---|---|
| **Panda** | Build time (atomic) | JS object DSL extracted by AST parser | Yes | Yes (codegen) |
| **vanilla-extract** | Build time | `.css.ts` files compiled to CSS | No (per-file) | Yes (TS-native) |
| **Linaria** | Build time | Tagged template literals | No | Limited |
| **Stitches** | Runtime | JS object DSL | Generates atomic at runtime | Yes |
| **Emotion / styled-components** | Runtime | Template literals or objects | No | Limited |
| **Tailwind v4** | Build time (atomic) | Class name strings in JSX | Yes | Theme-driven, no codegen types |
| **Hand-rolled CSS + tokens (yours)** | Source files | Plain CSS | No (intentional) | Linter only |

**Killer feature**: build-time atomic extraction *plus* recipes/variants *plus* generated types from your config. That triplet is what you do not get from Tailwind (no recipes/types from theme), vanilla-extract (no atomic by default), or hand-rolled CSS (no types). The README acknowledgements call this lineage explicitly: Stitches for recipes, Tailwind for JIT, vanilla-extract for utilities, Linaria for atomic strategy.

The cost: every styled element is now a JS object, which means you author styles in `.tsx` rather than `.css`. That moves where CSS lives in your codebase.

## 2. Token system

### How tokens are defined

In `panda.config.ts`, under `theme.tokens` (raw) and `theme.semanticTokens` (contextual). Each token is `{ value: <css value> }` per the W3C Design Tokens draft. From `website/content/docs/theming/tokens.mdx`:

```ts
export default defineConfig({
  theme: {
    tokens: {
      colors: {
        red: { value: '#EE0F0F' }
      },
      spacing: {
        4: { value: '1rem' }
      }
    },
    semanticTokens: {
      colors: {
        text: { value: { base: '{colors.gray.600}', _osDark: '{colors.gray.400}' } },
        danger: { value: '{colors.red}' }
      }
    }
  }
})
```

### What it generates

CSS custom properties on `:root` (and on `.dark`, `[data-theme]`, etc., for conditional semantic tokens). For the example above, Panda emits roughly:

```css
:root {
  --colors-red: #EE0F0F;
  --spacing-4: 1rem;
  --colors-text: var(--colors-gray-600);
  --colors-danger: var(--colors-red);
}
@media (prefers-color-scheme: dark) {
  :root { --colors-text: var(--colors-gray-400); }
}
```

This is **the same artifact you are hand-writing now**. The `:root { --color-text-1: ... }` you have today is what Panda would produce. Panda's value over your current setup is not the CSS variables themselves — it is the typed JS API (`color: 'text'` autocompletes) and the dual resolution mode that lets you use raw values where appropriate.

### Dual resolution mode (worth understanding)

From `SYSTEM_ARCHITECTURE.md` lines 391 to 448, Panda resolves token references two ways:

- `token('colors.red.500')` as a JS CallExpression in object literal → **raw value** `"#ef4444"` inlined at build time
- `"token(colors.red.500)"` as a string pattern → **CSS variable** `var(--colors-red-500)` for runtime theme switching
- `token.var(...)` → forces CSS variable

Practical effect: base tokens get inlined; semantic tokens (with `_osDark` / `_dark` conditions) always become CSS variables because they need to flip at runtime. This is a thoughtful design and you would have to reproduce it manually if you ever want it.

### Fluid type with `clamp()`

Yes. Tokens hold any valid CSS value, so `fontSizes: { hero: { value: 'clamp(2.5rem, 1rem + 5vw, 5rem)' } }` works. `packages/preset-panda/src/typography.ts` shows the default uses static `rem` values, but nothing prevents `clamp()`. `packages/token-dictionary` does not parse the value, it just stores it.

### Semantic vs raw

Modeled identically to your current convention: raw scale (`gray.50…gray.950`) lives under `tokens.colors`, named semantic roles (`text`, `surface`, `border`) live under `semanticTokens.colors` and reference raw tokens with `{colors.gray.600}` interpolation. Conditions (`_dark`, `_osDark`, custom data attributes) make the same semantic token resolve differently. This is exactly what you would otherwise express with two-layer `:root` custom properties — Panda's only structural addition is centralizing the mapping in TS so types follow.

## 3. Breakpoints and responsive design

Panda is **mobile-first min-width media queries** with named breakpoints. Defaults from `packages/preset-panda/src/breakpoints.ts`:

```ts
{ sm: '640px', md: '768px', lg: '1024px', xl: '1280px', '2xl': '1536px' }
```

Authoring (from `website/content/docs/concepts/responsive-design.mdx`):

```tsx
css({
  fontWeight: { base: 'medium', lg: 'bold' },
  padding: ['4', undefined, '8'],   // array syntax mirrors breakpoint order
  // range queries: mdToXl, lgOnly
})
```

Each breakpoint becomes a top-level key on every style object. Panda compiles these to plain `@media (min-width: 1024px)` rules in the `utilities` cascade layer.

### Container queries

Supported via `containerNames` and `containerSizes` in config, plus the same conditional API. Not a first-class focus.

### `@custom-media`

Not used. Panda owns the breakpoint plumbing entirely. Your Lightning CSS `@media (--bp-md)` setup is incompatible at the source level, though both produce identical compiled CSS. If you adopt Panda you would stop writing `@media` in CSS files and start writing `lg: { ... }` keys in JS objects.

### Trade

Your `@custom-media` approach gives you breakpoint definitions in CSS that work with any tool (Lightning CSS, native browser if browsers support it eventually). Panda's `lg:` keys give you per-property responsive values inline at the call site, which is more ergonomic when you are styling components but less portable.

## 4. Build pipeline integration (Astro + Vite)

### What the integration looks like

From `sandbox/astro/` (the canonical example, 7 files total):

```
sandbox/astro/
  astro.config.mjs        # standard Astro config, no Panda integration here
  panda.config.ts         # the Panda config
  panda.css               # one line: @layer reset, base, tokens, recipes, utilities;
  postcss.config.cjs      # plugins: [require('@pandacss/dev/postcss')()]
  package.json            # "prepare": "panda codegen"
```

That is the entire integration. Astro picks up PostCSS automatically, the Panda plugin runs during PostCSS, and `panda codegen` (run as a `prepare` script) writes `styled-system/` so TS types resolve before the first dev start.

### Conflict with Lightning CSS?

**Not directly conflicting, but you would replace your Lightning CSS pipeline.**

Two things to know:

1. Panda has its own optimization pipeline using PostCSS plugins (`postcss-nested`, `postcss-merge-rules`, `postcss-discard-duplicates`, `postcss-minify-selectors`) and **already integrates Lightning CSS internally** as a separate plugin: `packages/plugin-lightningcss/src/index.ts` exposes `pluginLightningcss()` which hooks `'css:optimize'` to call `optimizeLightCss(css, { minify, browserslist })`. So Lightning CSS is the recommended minifier *inside* Panda.
2. Astro's own `vite.css.transformer: 'lightningcss'` would still work on the final CSS bundle. There is no parser-level conflict because Panda emits standard CSS by the time Vite sees it.

Your current `@custom-media` would not survive: Panda emits `@media (min-width: ...)` literally. You would lose your CSS-side breakpoint indirection.

### Generated files in repo

`styled-system/` is written by `panda codegen` (and by the watcher). Standard practice is to gitignore it and run `panda codegen` in `prepare` so installs regenerate it. Sandbox confirms: `package.json` has `"prepare": "panda codegen"`. Some teams check it in for faster CI; the docs lean against it.

The directory contains: `css/index.mjs`, `cva.mjs`, `sva.mjs`, `patterns/`, `recipes/`, `jsx/` (framework-specific factories), `tokens/index.mjs`, `types/*.d.ts`, plus the actual CSS files. From `SYSTEM_ARCHITECTURE.md` the artifact list:

```
artifacts/
├── css/      tokens, reset, static, global, keyframes
├── js/       css, cva, sva, patterns
├── jsx/      styled, factory (per framework)
└── types/    style-props, pattern, recipes types
```

### Dev experience

`panda -w` watches sources and regenerates. Hot reload via PostCSS file dependency registration (`Builder.write(root)` registers HMR deps per `SYSTEM_ARCHITECTURE.md` PostCSS flow). Type errors when you reference a non-existent token. CLI also has `panda studio` (Astro-based local site for browsing tokens visually — `packages/studio`).

## 5. Recipes and patterns (for variants)

This is where Panda earns its keep on larger projects. Two layers:

### `cva` (atomic recipe)

Inspired by Class Variance Authority but bound to your tokens. From `website/content/docs/concepts/recipes.mdx`:

```ts
import { cva } from '../styled-system/css'

const button = cva({
  base: { display: 'flex' },
  variants: {
    visual: {
      solid:   { bg: 'red.200', color: 'white' },
      outline: { borderWidth: '1px', borderColor: 'red.200' }
    },
    size: {
      sm: { padding: '4', fontSize: '12px' },
      lg: { padding: '8', fontSize: '24px' }
    }
  },
  compoundVariants: [
    { visual: 'solid', size: 'lg', css: { fontWeight: 'bold' } }
  ],
  defaultVariants: { visual: 'solid', size: 'lg' }
})

<button className={button({ visual: 'solid', size: 'lg' })}>Go</button>
```

`button` is fully typed: `visual` autocompletes to `'solid' | 'outline'`. Every variant combination is extracted to atomic classes ahead of time, no runtime cost.

### Config recipes (`theme.recipes`)

Same shape, but defined in `panda.config.ts`. The class is named (`className: 'button'`), so DOM stays semantic, and the recipe becomes part of your design system rather than per-component code. Sandbox example: `sandbox/vite-ts/panda.config.ts` lines 49 to 120.

### Slot recipes (`sva`)

For multi-element components (e.g., a Card with header/body/footer). One recipe, multiple slots, single source of truth.

### Patterns (`stack`, `hstack`, `vstack`, `grid`, `flex`, `divider`, `wrap`, `aspectRatio`, `box`, etc.)

Pre-baked layout primitives that compile to atomic CSS. From the README example:

```tsx
<div className={hstack({ gap: '30px', color: 'pink.300' })}>...</div>
```

These are the closest analogue to Tailwind's "compose with utilities" model.

### Storybook story

Yes — `sandbox/storybook/` has a working integration with `@storybook/react`. Story file (`stories/Button.stories.tsx`) imports `css` from `styled-system/css` and renders the component. Storybook picks up the generated CSS through normal entry-point imports. There is no special Storybook plugin needed; PostCSS handles it. Variant matrices via Storybook controls map cleanly onto recipe variants because they are typed.

For your case (8 to 12 components, low variant density), Storybook benefits from recipes only if you have non-trivial variant explosion. If a component has one or two visual states, you can story it with vanilla CSS just as well.

## 6. Adoption signals

Pulled from the live repo (`gh repo view chakra-ui/panda`, npm registry) on 2026-04-30:

- **Stars**: 6,049
- **Forks**: 292
- **License**: MIT
- **Latest release**: `@pandacss/core@1.10.0` on 2026-04-18 (12 days ago)
- **Last push**: 2026-04-26 (4 days ago)
- **Open issues**: 2 (yes, two — extraordinarily low)
- **npm downloads (`@pandacss/dev`)**: ~1.02M for the trailing 30 days
- **Recent commits**: active feature work — `feat: support multi-block conditions` on top of TS 6.0 compatibility refactor, security updates, parser fixes
- **Created**: 2022-07-27. Stable, not new.

Author: Segun Adebayo (Chakra UI creator). The repo is the official successor to Chakra's runtime CSS-in-JS approach.

Health verdict: **healthy and active in 2026**. The 2-open-issues number is striking; either issues get triaged aggressively or the project has reached a stable plateau. Either way, not a project that is dying. v1.10.0 in 2026-04 with TypeScript 6 compatibility means it tracks the ecosystem.

Known users: documented integrations in `sandbox/` for Astro, Next.js (app + pages), Nuxt, Remix, Qwik, Solid, Svelte, Vue, Preact, Gatsby, Docusaurus, Storybook, Waku. Real adopters publicly include Park UI, Ark UI's docs, and several design system projects in the Chakra ecosystem.

## 7. Honest verdict for helioy.com

For your specific situation — 8 to 12 components, dark-only, marketing site, Astro 6 + React 19, already using Lightning CSS + custom-properties + `@custom-media` — Panda is **overkill today**.

### Why

1. **Token system parity**: Your `:root` custom properties already produce the same artifact Panda would emit. There is no CSS output you would gain.
2. **Variant pressure is low**: A marketing site has hero, navigation, footer, a few sections, a card or two. Each has zero to two visual variants. Recipes are valuable above ~3 variants × 3 axes per component.
3. **No theme switching**: Dark-only removes the strongest Panda argument (semantic tokens with conditional resolution).
4. **Authoring shift is real**: You currently co-locate component CSS (good). Panda moves styles into JS objects in TSX/JSX. That is a different mental model and a different file structure. Worth it only if the typed API saves you measurable bug-fix or refactor time.
5. **Build complexity**: Panda adds a `prepare` codegen step, a generated directory, and a PostCSS dependency that owns the entire CSS pipeline. Lightning CSS as your primary transformer is simpler and faster (Lightning CSS in Rust beats most JS toolchains at minification anyway, which is why Panda itself ships `@pandacss/plugin-lightningcss` — `packages/plugin-lightningcss/src/index.ts`).
6. **Astro `.astro` files**: Panda parses `.astro` (sandbox confirms `include: ['./src/**/*.{astro,tsx}']`), but `.astro` component scoped `<style>` blocks are not Panda's domain. You would either fully commit to JS-object styling or live with two systems.

### When Panda starts paying off

Specific triggers, ordered by likelihood for helioy.com:

- **Component library with shared variants across consumers.** If `@helioy/ui` becomes a real package consumed by helioy.com, attention-matters site, context-matters docs, and nancyr — recipes and typed tokens stop being abstraction tax and start being a contract.
- **Multiple themes.** Brand themes per Helioy component (each subproject with its own accent), or per-section themes on one site. Semantic tokens with conditional resolution are exactly the right hammer here.
- **A team beyond you.** Typed token autocomplete prevents drift when more than one person touches styles.
- **Variant matrix explosion.** If a Button needs 3 sizes × 4 visuals × 3 states = 36 combinations, recipes plus Storybook stories are dramatically better than hand-written CSS.

If none of these have happened in six months, you do not need Panda.

### Migration path if you ever do adopt

Low-friction, because token shape transfers:

1. `pnpm add -D @pandacss/dev`, `npx panda init --postcss`.
2. Port `:root` custom properties into `theme.tokens` and `theme.semanticTokens` in `panda.config.ts`. Use `clamp()` strings as token values directly.
3. Add `@layer reset, base, tokens, recipes, utilities;` to your entry CSS and let Panda fill the layers.
4. Convert components incrementally — Panda coexists with vanilla CSS files. Co-located CSS in `.astro` `<style>` blocks keeps working until you move that component over.
5. If you want to keep `@custom-media`, run Panda first and Lightning CSS second on the bundle. Your custom media queries in non-Panda CSS still resolve.

### What I would actually recommend

Stay put. Revisit when you have either (a) a second site sharing components or (b) a real variant matrix on three or more components. The cost of switching later is one afternoon of token transcription, not a rewrite.

---

## Sources consulted

- `/tmp/gh-research/chakra-ui-panda/README.md`
- `/tmp/gh-research/chakra-ui-panda/SYSTEM_ARCHITECTURE.md` (exhaustive — Segun's own architecture doc)
- `packages/preset-panda/src/{breakpoints,spacing,typography,colors,tokens}.ts`
- `packages/preset-base/src/conditions.ts` (full condition list for `_hover`, `_dark`, etc.)
- `packages/plugin-lightningcss/src/{index.ts,optimize-lightningcss.ts}`
- `sandbox/astro/{panda.config.ts,astro.config.mjs,postcss.config.cjs,panda.css,package.json,src/components/button.tsx}`
- `sandbox/storybook/{panda.config.ts,stories/Button.tsx,stories/Button.stories.tsx}`
- `sandbox/vite-ts/panda.config.ts` (recipes example)
- `website/content/docs/installation/astro.mdx`
- `website/content/docs/concepts/responsive-design.mdx`
- `website/content/docs/concepts/recipes.mdx`
- `website/content/docs/theming/tokens.mdx`
- `gh repo view chakra-ui/panda`, `gh release list`, `gh search issues`, npm registry downloads endpoint

## Open questions

- How does `panda codegen` interact with Astro 6's content collections / new Vite plugin shape? Sandbox uses Astro 6.1.5 so the integration works, but I did not trace any Astro-6-specific edge cases.
- Whether your current `@custom-media (--bp-md)` definitions can be programmatically synced to a Panda config object so both systems stay in lockstep during a partial migration. Worth exploring only if you decide to migrate.
- Storybook 10 specifically: the sandbox is on an older Storybook version. The PostCSS path should be unchanged but I did not verify against Storybook 10's Vite builder.
