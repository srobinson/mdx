---
title: UnoCSS evaluation for helioy.com (Astro 6 + tokens-first vanilla CSS)
type: research
tags: [css, design-tokens, unocss, atomic-css, astro, build-tooling, evaluation]
summary: UnoCSS is a fast, presets-based atomic CSS engine with a different philosophy from Panda (no codegen, no IR — direct extractor + generator). For a dark-only Astro marketing site with a small token surface and Lightning CSS already in place, UnoCSS is more invasive than its lightness suggests. Hand-rolled CSS still wins; if forced to switch, UnoCSS is the better pick over Panda for this specific project.
status: active
source: github-researcher
confidence: high
created: 2026-04-30
updated: 2026-04-30
---

# UnoCSS evaluation for helioy.com

## Verdict (read this first)

**Stay on hand-rolled vanilla CSS + Lightning CSS.** UnoCSS is the most architecturally elegant atomic engine on the market and the integration story with Astro is real (`@unocss/astro` is a 124-line wrapper around `@unocss/vite`), but it does not solve a problem helioy.com has today. You would be trading a small set of well-named tokens and a handful of co-located component CSS files for an extractor that scans every `.astro/.tsx/.html` source file, a generator that injects a virtual `uno.css` module, and a class-soup authoring style that competes with Astro's component-scoped CSS rather than complementing it.

UnoCSS pays off around the inflection where (a) you have a dense, repetitive utility surface across many components (think a dashboard or admin UI), (b) you want fast iteration on layout without writing CSS files, or (c) you specifically want pure-CSS icons via `presetIcons` and the inspector workflow. None of those describe a dark-only marketing site with 8 to 12 components.

**If forced to abandon hand-rolled CSS, pick UnoCSS over Panda for this project.** UnoCSS has a smaller install, no codegen step, no `styled-system/` directory to gitignore, and its theme system maps onto CSS variables on demand — which fits your existing `:root` custom properties more naturally than Panda's JS-object DSL. The cost is real (you write class strings in markup instead of CSS files), but the tooling cost is lower than Panda's.

The simplest fact: with `presetWind4`, UnoCSS theme keys are already emitted as CSS variables on demand (`mode: 'on-demand'`, default — see `packages-presets/preset-wind4/src/index.ts:43-44`). Your `:root` tokens and UnoCSS's tokens can coexist; you can also point UnoCSS rules at `var(--your-token)` directly and skip its theme entirely. That makes coexistence cheap if you ever want to layer it in for a specific section.

---

## 1. What UnoCSS actually is

UnoCSS is a **build-time, on-demand atomic CSS generator** with no AST parsing, no IR, and no codegen. The pipeline is dramatically simpler than Panda or even Tailwind v4:

1. **Extractor** runs over source files and pulls candidate tokens via regex-like extractors (default + preset-supplied). No AST. No type information needed.
2. **Generator** (`packages-engine/core/src/generator.ts`, ~1000 lines) takes each candidate string and tries to match it against the active rule set from your presets. If a rule matches, it emits CSS. If not, the candidate is dropped.
3. The matched CSS is concatenated into a virtual module (default id `uno.css`) and served via the Vite plugin (`packages-integrations/vite/src/index.ts`) or Astro integration (`packages-integrations/astro/src/index.ts`).

That is the entire story. There is no compile step that touches your JS, no `.css.ts` to author, no `styled-system/` directory generated, no PostCSS scan over your CSS files (PostCSS is one of many integrations, not the default). Your component code stays as it is; UnoCSS only adds a virtual CSS file.

The README pitch ("no parsing, no AST, no scanning, it's INSTANT") is structurally true. The benchmark folder (`bench/`) compares against Windi/Tailwind JIT and the engine wins on cold-start partly *because* it does not parse — it streams candidates through regex extractors and tests them against rules.

### Killer feature

**Presets as the unit of customization.** UnoCSS ships with no rules at all. The `unocss` package itself is a meta-package; everything (Tailwind-like utilities, attributify mode, icons, web fonts, typography, legacy compat) is a preset that plugs into the generator. The packages directory makes this concrete:

```
packages-presets/
  preset-mini/         (core utilities, the substrate)
  preset-wind3/        (Tailwind v3 compat layer)
  preset-wind4/        (Tailwind v4 compat layer, current recommended)
  preset-attributify/  (group utilities into HTML attributes)
  preset-icons/        (any iconify icon as a single class)
  preset-typography/   (prose styles)
  preset-web-fonts/    (Google/Bunny/ZeoSeven font loading)
  preset-legacy-compat/
  preset-rem-to-px/
  preset-tagify/
```

You compose these in `uno.config.ts`. You can also write a custom preset in ~50 lines that defines exactly the rules and theme keys you want and ship that, ignoring the Tailwind heritage entirely.

### Comparison

| Tool | When CSS exists | Author surface | Atomic? | Codegen step? | Token system |
|---|---|---|---|---|---|
| **UnoCSS** | Build time | Class strings (or attributes) | Yes | No | Theme object → CSS vars on demand |
| **Tailwind v4** | Build time | Class strings | Yes | No (Oxide engine) | `@theme {}` directive in CSS |
| **Windi CSS** | Build time | Class strings | Yes | No | Theme object | (project effectively dormant since 2023) |
| **Panda CSS** | Build time | JS object DSL extracted by ts-morph | Yes | Yes (`styled-system/`) | Token config → CSS vars + TS types |
| **vanilla-extract** | Build time | `.css.ts` files | No | No | TS-native |
| **Hand-rolled (yours)** | Source files | Plain CSS | No | No | `:root` custom properties |

UnoCSS sits between Tailwind v4 and Panda. It is closer to Tailwind in author surface (class strings) but closer to Panda in extensibility (programmable presets, a real engine API). It is not a Tailwind clone — the Tailwind compat is a preset, not the core.

---

## 2. Token / theme system

UnoCSS theme is a plain JS object you pass through `uno.config.ts`. It is deep-merged onto the preset defaults. The shape is conventional:

```ts
// from packages-presets/preset-wind4/src/theme/index.ts
export const theme = {
  font, colors, spacing, breakpoint, verticalBreakpoint,
  text, fontWeight, tracking, leading, textStrokeWidth,
  radius, shadow, insetShadow, dropShadow, textShadow,
  ease, animation, blur, perspective, property,
  default: defaults,
  container,
  aria, media, supports,
}
```

### Does it generate CSS variables or inline values?

**Both, configurable.** This is the load-bearing point for you. `presetWind4` exposes `preflights.theme.mode` with three values (`packages-presets/preset-wind4/src/index.ts:43-44`):

- `'on-demand'` (default): only the theme keys actually referenced by used utilities are emitted as CSS variables under a `theme` layer
- `true`: emit all theme keys as CSS variables
- `false`: inline values directly into rules; no CSS variables (not recommended)

When emitted, theme keys become CSS variables prefixed with `--un-` by default (`variablePrefix` option). The emission code is in `packages-presets/preset-wind4/src/preflights/theme.ts`. It walks the theme object and emits entries like `--colors-blue-500`, `--radius-lg`. There is also an explicit *exclude* list for keys that are never emitted as variables (`spacing`, `breakpoint`, `verticalBreakpoint`, `shadow*`, `animation`, `property`, `aria`, `media`, `supports`, `containers`) because they are used as raw values in rules.

### Can it consume your existing `:root` custom properties?

**Yes, and this is the cleanest integration path.** Two mechanisms:

1. **Pass `var(--your-token)` strings as theme values.** From `docs/config/theme.md`:
   ```ts
   theme: {
     colors: {
       brand: { primary: 'hsl(var(--hue, 217) 78% 51%)' }
     }
   }
   ```
   That is the documented pattern and exactly what you would do.

2. **Write custom rules that reference your variables directly,** bypassing UnoCSS's theme entirely:
   ```ts
   rules: [
     ['text-fg', { color: 'var(--text)' }],
     [/^space-(\d+)$/, ([, n]) => ({ padding: `var(--space-${n})` })],
   ]
   ```
   Full programmatic access; no theme key required.

Either approach makes UnoCSS a *consumer* of your design tokens rather than a competing source of truth. You keep `src/design-system/tokens/*.css` as the canonical token layer; UnoCSS just spits out classes that point at those variables.

### How does the `theme` config relate to runtime CSS vars?

When `mode: 'on-demand'` (the default in `presetWind4`), the engine *tracks* which theme keys get touched during a build (`themeTracking` and `trackedTheme` in `packages-presets/preset-wind4/src/utils.ts`, referenced from `packages-presets/preset-wind4/src/preflights/theme.ts`). Only those keys produce CSS variable output. This keeps the theme layer tight — no orphan custom properties for unused tokens.

Compared to Panda's approach (codegen produces a complete `tokens.css` regardless of usage), UnoCSS's runtime is leaner for small surfaces and more aligned with how you currently think about tokens.

---

## 3. Breakpoints and responsive design

UnoCSS owns its own breakpoint variants. The defaults from `packages-presets/preset-wind4/src/theme/size.ts`:

```ts
export const breakpoint = {
  sm: '40rem', md: '48rem', lg: '64rem', xl: '80rem', '2xl': '96rem',
}
```

Variants resolve as `min-width` media queries by default, with prefixes for max-width (`lt-`, `<`, `max-`) and ranges (`at-`, `~`). The full handling is in `packages-presets/preset-wind4/src/variants/breakpoints.ts`. There is also arbitrary-bracket support via `min-[600px]:` and `max-[800px]:`.

Container queries are first-class: `container.ts` and `containers.maxWidth` theme key, plus `@container` variant support.

Other media variants ship out of the box from `packages-presets/preset-wind4/src/theme/media.ts`: `os_dark`, `os_light`, `motion_ok`, `motion_not_ok`, `high_contrast`, `low_contrast`, `touch`, `pointer`, `mouse`, `hd_color`, etc. These are a richer set than what most token-first sites bother to define manually.

### Coexistence with `@custom-media` and Lightning CSS

This is where you have to be honest. UnoCSS does not read your `@custom-media` declarations. It generates `@media (min-width: 48rem)` directly from its own theme. Two reconciliation paths:

1. **Match the values.** Set UnoCSS's `breakpoint` theme to the same rem values as your `@custom-media (--bp-md)` definitions. UnoCSS emits raw `@media` queries, Lightning CSS leaves them alone. Two parallel sources, identical values. Drift risk if you change one.

2. **Use UnoCSS as the single source.** Drop your `@custom-media` declarations and use `md:` / `lg:` everywhere — both in UnoCSS classes *and* in your hand-written CSS via `@apply` if you adopt `transformerDirectives`. This consolidates breakpoints but ties more of your CSS to UnoCSS's runtime.

Option 1 is the lower-coupling path and works fine. Lightning CSS and UnoCSS do not conflict at the CSS layer — they operate on disjoint concerns. The example in `examples/vite-lightningcss/vite.config.ts` is exactly the topology you would adopt:

```ts
plugins: [UnoCSS()],
css: { transformer: 'lightningcss' },
build: { cssMinify: 'lightningcss' },
```

Both run, they do not fight.

---

## 4. Build pipeline integration

### Astro

`@unocss/astro` is a thin wrapper around the Vite plugin. The whole integration is 124 lines (`packages-integrations/astro/src/index.ts`). What it does:

1. Hooks into `astro:config:setup`.
2. Adds `src/components/**/*` to the UnoCSS `content.filesystem` watch list (so component files outside the route tree are scanned).
3. Optionally injects a CSS reset (`injectReset: true | string`) and the `import "uno.css"` entry into every page (`injectEntry: true`, default).
4. Registers the Vite plugin (`@unocss/vite`) and a small companion plugin that resolves the virtual `uno.css` ID to align with Astro's dev IDs.

Adding it is one line in `astro.config.ts`:

```ts
import UnoCSS from 'unocss/astro'
export default defineConfig({
  integrations: [UnoCSS({ injectReset: true })],
})
```

`uno.config.ts` lives at the project root and is auto-discovered (via `unconfig`). You can also pass options inline.

### Vite + Lightning CSS

There is an explicit example in the repo (`examples/vite-lightningcss/`). It works without contortion because UnoCSS produces a CSS string that Vite hands to its CSS pipeline; Lightning CSS then transforms it the same way it transforms your hand-written CSS. `@custom-media`, nesting, vendor prefixing all still happen.

The one thing to know: UnoCSS's output goes through a **layer system** (`-200` properties, `-150` theme, `-100` base — see `packages-presets/preset-wind4/src/index.ts:140-144`). Lightning CSS handles `@layer` natively, so this is not a problem, but if you also use `@layer` in hand-written CSS, name your layers carefully to avoid ordering surprises.

### Dev experience

- **Inspector** (`packages-integrations/inspector/`): a localhost UI at `/__unocss/` that shows every matched class, the rule that matched, the resulting CSS, and the modules that triggered it. Useful for debugging "why is this class not working" or "where does this token leak from."
- **Playground** (`https://unocss.dev/play/`): try-without-installing.
- **VS Code extension** (`@antfu/unocss`, `packages-integrations/vscode/`): hover for resolved CSS, autocomplete from your config.
- **HMR**: rebuilds on file change without full reload.

The inspector is a genuine differentiator vs. Tailwind/Panda. It makes the engine's behavior introspectable.

### Conflict points with Lightning CSS

None I could find. `examples/vite-lightningcss/vite.config.ts` is a working five-line setup. The two systems own non-overlapping pipeline stages: UnoCSS produces CSS (virtual module), Lightning CSS transforms CSS (Vite's `css.transformer`).

---

## 5. Presets and the configuration story

The recommended preset in 2026 is **`presetWind4`** (Tailwind v4 compat). The repo carries `presetWind3` in parallel for backward compatibility, plus the underlying `presetMini` (which `wind3` and `wind4` both build on).

Active preset ecosystem (from `packages-presets/`):

| Preset | Purpose |
|---|---|
| `preset-mini` | Minimal core utilities (the substrate everything else extends) |
| `preset-wind3` | Tailwind v3 API compatibility |
| `preset-wind4` | Tailwind v4 API compatibility (recommended, current) |
| `preset-attributify` | HTML attribute syntax for utilities |
| `preset-icons` | Any iconify icon as `i-mdi-account` class — pure CSS |
| `preset-typography` | Prose styles for long-form content |
| `preset-web-fonts` | Google/Bunny/Fontsource/ZeoSeven loaders |
| `preset-tagify` | Custom HTML tags become utility classes (`<text-red>`) |
| `preset-legacy-compat` | RGB → HSL fallbacks, etc. |
| `preset-rem-to-px` | Output px instead of rem |

Plus extractors (`extractor-svelte`, `extractor-mdc`, `extractor-pug`, `extractor-arbitrary-variants`) and transformers (`transformer-directives` for `@apply`, `transformer-variant-group` for `hover:(text-red bg-blue)`, `transformer-compile-class` for class consolidation, `transformer-attributify-jsx` for JSX prop syntax).

### Custom presets

The `definePreset` API is documented and stable (`packages-engine/core/src/index.ts`). A custom preset is a function that returns rules, theme keys, variants, shortcuts, postprocessors. The `preset-attributify` source (`packages-presets/preset-attributify/src/index.ts`, ~60 lines) is a readable example: it returns a list of variants and extractors, that's it.

In 2026, most adopters appear to use `presetWind4` + `presetIcons` as the default pair, occasionally adding `presetAttributify` or `presetTypography`. Custom presets are common for component libraries (UI kits ship presets to consumers) but rare for application teams. For helioy.com, the right shape would be: `presetMini` only, plus a tiny custom preset that defines rules pointing at *your* CSS variables. That gives you the engine without inheriting Tailwind's mental model.

---

## 6. Atomic vs component CSS authoring

This is the real question for you. You author component CSS today (`Button.css` co-located with `Button.tsx`). UnoCSS's default mode pushes you toward inline class strings:

```jsx
<button class="px-4 py-2 rounded-md bg-accent text-white hover:bg-accent-hover">
```

That is genuine class soup. UnoCSS provides **four** mitigations:

### 6.1 Shortcuts (the boring, robust answer)

Static or dynamic class aliases in `uno.config.ts`:

```ts
shortcuts: [
  { 'btn': 'px-4 py-2 rounded-md bg-accent text-white hover:bg-accent-hover' },
  [/^btn-(.+)$/, ([, c]) => `bg-${c} hover:bg-${c}-hover px-4 py-2 rounded-md`],
]
```

Then markup is `<button class="btn">`. Shortcuts give you back component-shaped reuse without leaving config. They compose with all variants. This is the canonical UnoCSS answer to your concern.

### 6.2 Attributify mode

Group utilities into HTML attributes:

```html
<button
  bg="accent hover:accent-hover"
  text="white sm"
  p="y-2 x-4"
  border="rounded"
>Click</button>
```

Less soup, but you trade class noise for attribute noise. JSX support exists via `transformer-attributify-jsx`. Most teams who try this end up turning it off.

### 6.3 `@apply` via `transformer-directives`

You can keep your component CSS files and use UnoCSS classes inside them:

```css
/* Button.css */
.button {
  @apply px-4 py-2 rounded-md bg-accent text-white;
  &:hover { @apply bg-accent-hover; }
}
```

This recovers your current authoring style 1:1 while letting UnoCSS own the token mapping. It is the most natural migration path from where you are: component CSS files stay, but classes inside them resolve through UnoCSS's theme. Source: `transformer-directives` in `packages-presets/transformer-directives/`.

### 6.4 `transformer-compile-class`

Specially marked class lists get compiled into a single hashed class at build time. Niche; useful for large utility chains.

### Recommendation if you adopt UnoCSS

Use option 6.3 (`transformer-directives` + `@apply`) for component CSS, *not* inline class strings. That keeps your authoring style intact and treats UnoCSS as a source of named tokens. You give up some of the speed-of-iteration that atomic CSS evangelists love, but you keep the architectural property that matters to you: component styles live next to components.

---

## 7. Adoption signals (April 2026)

- **Stars**: 18,769
- **Forks**: 965
- **Subscribers**: 60
- **Open issues**: 100+ (sample of first page); 159 reported overall
- **License**: MIT
- **Latest release**: `v66.6.8` on 2026-04-08
- **Last push**: 2026-04-29 (active)
- **Recent merged PRs (2026)**: 56 since 2026-01-01 — steady cadence
- **Maintainer**: Anthony Fu (antfu) and a core team. Anthony is also behind Vue Router devtools, Vitest, Slidev, and large parts of the Vue/Vite ecosystem; UnoCSS is part of a maintained portfolio, not a one-person side project.
- **Recent commits** show preset-wind4 still seeing feature work (`feat(preset-wind4): support theme parse in all bracket syntax rule`, `feat(preset-wind4): improve css variable usage in bracket syntax`), language-server fixes for color preview, and consistent maintenance across integrations.

The version number (`v66.x`) is artificial — the team uses an aggressive minor-version policy — but the project is unambiguously healthy in 2026. Compare to Windi CSS, which has been effectively dormant since 2023 and was the project that originally inspired UnoCSS.

Known production users (from public sponsorship and project pages): Nuxt (default styling option), Slidev (Anthony's own slides framework), Vitesse template, multiple Vue-ecosystem projects. The Astro adoption is real but smaller — `@unocss/astro` is a stable integration but most Astro starter content still defaults to Tailwind.

---

## 8. Honest verdict for helioy.com

### Would I adopt UnoCSS for a brand-new dark-only marketing site with 8-12 components?

**No.** Same reasoning as Panda but a different cost profile. With 8-12 components and a fixed dark theme:

- The repetition that atomic CSS optimizes for does not exist yet.
- Co-located component CSS is already the right granularity.
- Your `:root` custom properties already give you typed-feeling tokens (the linter catches typos; Lightning CSS validates `var()` usage).
- Adding UnoCSS adds: a config file, a preset choice you have to maintain, an extractor scanning your sources every build, a virtual `uno.css` module that ships on every page, and a decision-fatigue tax on every styling decision (component CSS vs class string vs `@apply`?).

The marginal CSS bytes saved by atomic extraction on a small site are negligible. Lightning CSS minifies your hand-written CSS aggressively; you are not in territory where atomic deduplication moves the bundle needle.

### When does UnoCSS start paying off?

The crossover lives roughly where one or more of these become true:

1. **Component count above ~25** with significant utility-style repetition (margins, paddings, color variants). At that point, atomic deduplication actually saves bytes and shortcuts replace handfuls of CSS rules.
2. **Multiple themes or skins.** UnoCSS's theme-as-CSS-vars story makes this trivial; hand-rolled CSS makes it explicit but tedious.
3. **You want pure-CSS icons** at scale. `presetIcons` is a genuinely best-in-class implementation — any iconify icon as `class="i-mdi-account"` with no JS, no SVG sprites. This alone is sometimes worth adopting UnoCSS.
4. **Team scaling** where ad-hoc class names start drifting from tokens and you want a hard tokenization boundary.
5. **Layout exploration phase** where iteration speed matters more than architectural cleanliness.

helioy.com today is at none of these.

### UnoCSS vs Panda for this specific project

If forced to abandon hand-rolled CSS, I would pick **UnoCSS** for helioy.com. The reasons are project-specific, not categorical:

| Dimension | UnoCSS | Panda | Which wins for helioy.com |
|---|---|---|---|
| Codegen step | None | `panda codegen` before dev/build, `styled-system/` directory | UnoCSS (less infra) |
| Token integration with existing `:root` vars | Trivial — pass `var(--x)` as theme value, or write custom rules | Possible but Panda prefers its own token config as source of truth | UnoCSS |
| Author surface | Class strings or `@apply` in CSS | JS object DSL | UnoCSS (you can keep CSS files via `@apply`) |
| Astro integration depth | First-party, 124 lines, stable | Real (`sandbox/astro/`) but PostCSS-heavy | UnoCSS |
| Lightning CSS coexistence | Documented example, no conflicts | Compatible but more pipeline surface | UnoCSS |
| TS-typed tokens with autocomplete | Via VS Code extension and language-server | Codegen produces literal types — stronger | Panda |
| Variant API for component patterns | `shortcuts` (string-based, simple) | Recipes/cva (typed, structured) | Panda for complex variants |
| Ecosystem breadth | Huge — icons, fonts, attributify, etc. | Tighter, more opinionated | UnoCSS |
| Bundle size | ~6kb engine (mostly compile-time anyway) | Zero runtime (atomic) | Tie — both are build-time |

For helioy.com's profile (small, dark-only, marketing, tokens-first, you already write CSS files), the practical lifeline is UnoCSS in `@apply` mode: keep `Button.css`, `@apply px-4 py-2 rounded-md` instead of `padding: var(--space-4) var(--space-8); border-radius: var(--radius-md);`. That is a strict reduction in keystrokes if and only if you already think in Tailwind-shaped tokens. If your tokens are designed around your design language (you mentioned fluid type via `clamp()`, motion, layout — these are not Tailwind-shaped), then UnoCSS's preset values will fight you, and you will end up writing a custom preset that mostly re-declares your tokens.

### The ranking, end to end

1. **Hand-rolled CSS + `:root` tokens + Lightning CSS** (current). For 8-12 components, dark-only, this is correct.
2. **UnoCSS with `presetMini` + a tiny custom preset that maps to your existing CSS variables, used via `@apply` in component CSS files.** The migration target if you outgrow option 1. Lower infra cost than Panda.
3. **Panda CSS.** Stronger types, better recipes, but the codegen + JS DSL friction does not justify itself for this site shape.
4. **Tailwind v4.** Viable, but you would inherit Tailwind's token vocabulary wholesale, which conflicts with your "tokens-first design system" philosophy more than UnoCSS does (UnoCSS lets you ignore the Tailwind lineage entirely; Tailwind v4 still expects you to think in its primitives).

The not-a-one-way-door property holds: UnoCSS via `@apply` lets you migrate one component at a time, keep the CSS-file authoring model, and pull the plug if it does not pay off. That is the cheapest experiment if you ever feel the friction of hand-rolled CSS.

---

## Sources consulted

- `README.md` (root)
- `packages-engine/core/src/generator.ts` — engine entry, ~1000 lines
- `packages-engine/core/src/types.ts` — public types
- `packages-engine/core/src/index.ts` — `definePreset` API
- `packages-integrations/astro/src/index.ts` — Astro integration (124 lines)
- `packages-integrations/vite/src/index.ts` — Vite plugin entry
- `packages-presets/preset-wind4/src/index.ts` — `presetWind4` options & layers
- `packages-presets/preset-wind4/src/theme/index.ts` — theme structure
- `packages-presets/preset-wind4/src/theme/size.ts` — breakpoint defaults
- `packages-presets/preset-wind4/src/theme/media.ts` — media variant defaults
- `packages-presets/preset-wind4/src/preflights/theme.ts` — CSS variable emission logic
- `packages-presets/preset-wind4/src/variants/breakpoints.ts` — responsive variant resolution
- `packages-presets/preset-attributify/src/index.ts` — preset architecture sample
- `examples/astro/uno.config.ts` and `examples/astro/astro.config.ts` — Astro setup
- `examples/vite-lightningcss/vite.config.ts` and `uno.config.ts` — Lightning CSS coexistence example
- `docs/config/theme.md` — theme & breakpoint documentation
- `docs/presets/wind4.md` — preset-wind4 migration table and theme defaults
- GitHub: stars, release cadence, recent commits, contributor count, open issue count

## Open questions

- **`presetMini` alone, no Tailwind compat.** Worth a small spike if you ever adopt UnoCSS — strip Tailwind-isms entirely and write rules pointing only at your tokens. The repo does not contain a public example of this minimal posture; you would build it.
- **HMR behavior with Astro 6 islands.** The integration is stable, but Astro 6 changed CSS scoping in some component types. Worth a sandbox before committing.
- **Inspector usefulness in production-equivalent dev.** I did not run the inspector locally; the screenshots in the docs are representative but the actual inspector UX should be tried before assuming it adds value.
