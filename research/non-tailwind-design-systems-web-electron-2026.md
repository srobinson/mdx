# Non-Tailwind Design Systems for Web + Electron (2026)

> Research synthesis. Reference date **2026-05-29**. Produced by the deep-research harness (108 agents, 26 sources, 23/25 adversarially-verified claims) plus one focused gap-fill pass.
>
> **Question.** Find complete, open-source component-library + design-system repos suitable for building web AND Electron UIs in 2026, with a well-architected theming/design-tokens layer. Prioritize non-Tailwind. Survey both React-first and framework-agnostic. The user is building a Storybook-based component library at `helioy.com` (currently Astro + Tailwind 4) and wants to know what exists before over-investing.
>
> **Scope answers.** Framework: both, weighted React. Styling tech: all four non-Tailwind families (vanilla-extract, Panda, StyleX, CSS Modules / CSS vars). Intent: both adopt and harvest.

## Related Helioy artifacts (cross-links)

- `~/.mdx/research/css-token-foundation-evaluation-open-props.md` — prior CSS token foundation eval (Open Props).
- `~/.mdx/research/react-component-ecosystem-2026.md` — broader React component ecosystem survey.
- `~/.mdx/research/manicure-token-audit.md` (+ `-review`, `-review-supplement`) — token audit for the manicure product.
- `~/.mdx/research/helioy-electron-baseline.md` — three-app + three-package Electron/Web baseline spec.

---

## TL;DR recommendation

**Harvest, do not adopt wholesale.** No single repo is the destination, because the differentiator for helioy.com is the token layer itself, and adopting a styled system buries that under someone else's visual identity.

Target architecture:

1. **Token source of truth in DTCG 2025.10 JSON**, compiled with **Style Dictionary v5** (or Terrazzo). Highest-leverage decision. Decouples the design language from any styling engine; new themes become a data change.
2. **Styling engine: vanilla-extract or Panda CSS.** vanilla-extract for typed theme *contracts* + pure zero-runtime; Panda for semantic-token + simultaneous-runtime-theme ergonomics. Both Electron-clean.
3. **Component behavior: a headless core** (Base UI or React Aria) so accessibility and interaction are solved and you own only the skin.

Study first, in order, for the token layer: **Panda CSS → Mantine → Radix Themes.**

---

## Section 1 — Ranked shortlist (adoptable complete systems)

| Rank | System | Framework | Styling tech | License | Maint. (2026) | Docs | Why it ranks |
|------|--------|-----------|--------------|---------|---------------|------|----------------|
| 1 | **Mantine** | React-first | Native CSS Modules + CSS vars + PostCSS, zero runtime | MIT | v9.2.2, 2026-05-27 | Docs site | Most complete wholesale option. 120+ components, 70+ hooks, dark mode out of the box, CSS-variable tokens via `MantineProvider` + `cssVariablesResolver`. No Tailwind, no CSS-in-JS runtime. Electron-ideal. |
| 2 | **Braid (SEEK)** | React 18/19 | vanilla-extract, zero-runtime atomic CSS | SEEK OSS | v34.2.0, 2026-05-22 | Storybook | Canonical vanilla-extract reference. Themes are importable typed objects passed to `BraidProvider`. Caveat: curated SEEK-brand theme set, not an arbitrary multi-brand generator. Best harvested. |
| 3 | **Radix Themes** | React | Plain CSS + CSS-variable tokens, light/dark via `.light`/`.dark` | MIT (WorkOS) | v3.3.0, active | Docs site | Cleanest pure CSS-variable token contract to study. No Tailwind, no runtime CSS-in-JS. |
| 4 | **Adobe React Spectrum / React Aria** | React | Styling-agnostic (headless) + styled Spectrum | Apache-2.0 | RAC v1.17.0, 2026-04-15; pushed 2026-05-29 | Docs site | The headless option: bring your own token layer. React Aria ships zero styles, exposes state via data-attributes + CSS vars. Deepest a11y + i18n. |
| 5 | **Park UI** | React + Solid + Vue | Ark UI (headless) + Panda | MIT | code alive (pushed 2026-04-10) | Docs site | Harvest-only. `@park-ui/panda-preset` froze Nov 2024 (pivoted to a shadcn-style CLI/registry); v2 added a Tailwind path, so "non-Tailwind" holds only on the Panda variant. |

Foundations excluded from the table because they are not finished UIs: **Panda CSS** and **StyleX** (styling engines), **Base UI** (headless primitives). See Section 2.

---

## Section 2 — Full survey by styling category

### vanilla-extract (zero-runtime CSS-in-TS, typed themes)
- **Braid** — see shortlist. Best complete reference for `createTheme` / `createThemeContract` in a shipping system.
- vanilla-extract's `createThemeContract`: define a typed token shape once, supply N theme implementations against it. Strongest typed-token contract mechanism of any engine here.

### Panda CSS (build-time atomic + recipes)
- **Panda CSS** — v1.11.1, 2026-05-08, actively maintained (2026 CVE bumps confirm liveness). First-class primitive vs semantic token layers, Stitches-style recipes/variants, simultaneous runtime themes via `data-panda-theme`, standalone `@pandacss/token-dictionary` processor. Near-zero runtime (small helper for `css()`); cannot read `useState` inside `css()`, so dynamic styling routes through CSS vars / data-attributes.
- **Park UI** — component kit on top (harvest-only).

### StyleX (Meta, compile-time atomic)
- **StyleX** — a styling library, not a component kit. `defineVars` creates typed CSS-variable token groups; `createTheme` overrides per DOM node (last-applied-wins, unspecified tokens inherit). Static styles compile to zero-runtime atomic CSS; total CSS output plateaus logarithmically with codebase size. Used across Facebook/Instagram/WhatsApp/Threads; OSS version is what Meta runs internally (Jan 2026 engineering blog). Build a system on it, paired with headless primitives.

### CSS Modules / plain CSS-variable token layers
- **Mantine** — rank 1. Reference for a CSS-variable resolver with per-scheme (light/dark) output.
- **Radix Themes** — rank 3. Cleanest token contract.
- **IBM Carbon** (`@carbon/react`) — Sass tokens + CSS custom properties, four built-in themes (2 light / 2 dark), Apache-2.0, active. Enterprise-grade, opinionated identity. No Tailwind, no CSS-in-JS.
- **PrimeReact unstyled mode** — three-tier tokens (primitive → semantic → component) mapped to CSS variables, light/dark presets, MIT. Not Tailwind-required (Tailwind pass-through is optional). The three-tier model is worth studying.

### Headless cores (own the visual + token layer)
- **Base UI** (mui org, from Radix/Floating UI/MUI authors) — v1.0 stable Feb 2026, 35 components, MIT, styling-agnostic, ships no token layer. Cleanest modern headless base for full visual ownership.
- **React Aria / React Stately** — rank 4. Deepest accessibility + i18n.
- **Ark UI / Zag** — headless state machines under Park UI (framework-agnostic).

### Web components (framework-agnostic)
- **Shoelace → Web Awesome** — CSS-custom-property theming, MIT. Shoelace is sunset; active development moved to Web Awesome (Kickstarter-funded, v3 line). Good cross-framework portability, but a React wrapper adds friction vs React-native kits.

### Runtime CSS-in-JS (Electron penalty)
- **Fluent UI v9 / Griffel** (Microsoft, MIT, `@fluentui/react-components` 9.73.8, Apr 2026) — CSS-variable tokens and dark mode are good, but Griffel does runtime atomic rule-merging. AOT extraction exists, but this is the one major system here with a runtime cost. Lower priority for a desktop renderer.

### Deprecated (do not start here)
- **Stitches** — EOL. Repo archived 2026-04-25, last release v1.2.8 (Apr 2022), README marked "Not Actively Maintained." Community migration target: Panda CSS (same ecosystem orbit) or vanilla-extract.

---

## Section 3 — Token-layer architectures worth stealing

Ranked by what they teach:

1. **Panda's primitive-vs-semantic split with simultaneous themes.** Semantic tokens reference base tokens and resolve on conditions (light/dark/brand). Multiple named themes coexist, selected by `data-panda-theme`, switched at runtime (`getTheme`/`injectTheme`) or pregenerated (`staticCss.themes`). Most complete answer to multi-brand + multi-theme + runtime switch.
2. **vanilla-extract / StyleX typed contracts.** `createThemeContract` (vanilla-extract) and `defineVars` + `createTheme` (StyleX) give a typed token *shape* the compiler enforces. Themes become interchangeable implementations of one contract. Makes new themes type-safe rather than stringly-typed.
3. **Mantine's CSS-variable resolver.** `MantineProvider` projects the whole theme into CSS variables; `cssVariablesResolver` returns per-scheme values; `data-mantine-color-scheme` flips them. Cleanest "one provider, all tokens as CSS vars" reference.
4. **PrimeReact's three-tier token model** (primitive → semantic → component). Textbook layering with component-level tokens.

### W3C / DTCG standard state (2026)
- The **Design Tokens Format Module** reached its **"first stable version" (2025.10) on 2025-10-28**. It is a **W3C Community Group Report, not a Recommendation or Standard**, and explicitly not on the standards track. "Stable" = a vendor-neutral production baseline the CG agreed on.
- Defines `$type`s: `color`, `dimension`, `fontFamily`, `fontWeight`, `duration`, `cubicBezier`, `number`; composites `strokeStyle`, `border`, `transition`, `shadow`, `gradient`, `typography`. 2025.10 added standardized theming, modern color spaces, and **resolvers**.
- The live draft at designtokens.org/tr currently shows a "Draft Community Group Report" (07 May 2026) with a "do not implement" banner. That is an editor's draft layered over the frozen 2025.10 release, not its status.

### Tooling that reads/writes DTCG
- **Style Dictionary v5** — DTCG JSON is the default format (first-class since v4); full 2025.10 support still in progress. Pipeline standard for fanning one token source out to CSS vars, Sass, JS/TS, iOS, Android.
- **Terrazzo** (formerly Cobalt UI, MIT) — CLI consuming DTCG, emitting CSS/Sass/JS-TS/JSON/Tailwind. Working toward full 2025.10 + resolvers.
- **Tokens Studio** — Figma-side authoring with a DTCG-aligned export (historically with some vendor extensions).

---

## Section 4 — Headless vs styled, and the Electron note

**Electron rule: prefer build-time, zero-runtime styling.** A desktop renderer pays the runtime CSS-in-JS injection cost on every launch with no SSR upside, because SSR/hydration concerns are irrelevant in Electron.

- **Ideal for Electron:** Mantine (native CSS), Braid/vanilla-extract, Panda, StyleX, Radix Themes, Carbon. All ship static `.css`.
- **Penalty in Electron:** Fluent UI/Griffel and classic runtime CSS-in-JS (Emotion, styled-components, the latter maintenance-only in 2026).

**Headless vs styled is a control/speed tradeoff:**
- Headless (React Aria, Base UI, Ark UI): total token-layer and visual freedom, you own the look. Slower to first pixel, highest ceiling for "unique."
- Styled (Mantine, Radix Themes, Carbon, Spectrum): faster to adopt, harder to fully re-skin away from the original identity.

For "unique UI, trivially," headless core + own token engine wins on ceiling. Styled wins on time-to-first-product.

---

## Section 5 — Recommendation for helioy.com

Situation: Astro + Tailwind 4 today, building a Storybook component library, React-weighted, web + Electron, token layer is the priority, dislikes Tailwind.

1. **Token source of truth in DTCG 2025.10 JSON**, compiled via Style Dictionary v5 (or Terrazzo). Highest leverage. Makes new themes a data change.
2. **Styling engine: vanilla-extract or Panda.** vanilla-extract for typed contracts + pure zero-runtime; Panda for semantic-token + simultaneous-runtime-theme ergonomics. Both Electron-clean.
3. **Component behavior: a headless core** (Base UI or React Aria).

Keep Tailwind 4 for the Astro marketing site if desired; use the non-Tailwind token + engine stack for the app and Electron renderer. The two need not share a styling engine if they share the same DTCG token source.

**Study first for the token layer:** Panda CSS (`docs/theming/tokens`, `docs/guides/multiple-themes`) → Mantine (`MantineProvider` + `cssVariablesResolver`) → Radix Themes (minimal pure-CSS-variable contract).

---

## Verification notes

- Confirmed against primary sources: licenses, framework support, non-Tailwind status, 2026 maintenance for all systems above. 23/25 adversarially-verified claims survived; two killed (StyleX as a cross-platform native unifier; `@park-ui/panda-preset` as the current shipping token mechanism).
- Lower confidence (not opened to the letter this pass): exact PrimeReact license string, Web Awesome v3 release tag, whether Tokens Studio's DTCG export is byte-clean 2025.10 vs vendor-extended.

## Sources (primary unless noted)

- Mantine — https://mantine.dev/ , https://github.com/mantinedev/mantine
- Braid — https://github.com/seek-oss/braid-design-system
- Panda CSS — https://github.com/chakra-ui/panda , https://panda-css.com/docs/theming/tokens , https://panda-css.com/docs/guides/multiple-themes
- StyleX — https://github.com/facebook/stylex , https://stylexjs.com/blog/introducing-stylex/ , https://engineering.fb.com/2026/01/12/web/css-at-scale-with-stylex/ , https://stylexjs.com/docs/api/javascript/createTheme/
- React Spectrum / React Aria — https://github.com/adobe/react-spectrum , https://react-aria.adobe.com/styling
- Park UI — https://park-ui.com/ , https://github.com/chakra-ui/park-ui
- Radix Themes — https://github.com/radix-ui/themes , https://www.radix-ui.com/themes/docs/theme/dark-mode
- Base UI — https://github.com/mui/base-ui , https://www.infoq.com/news/2026/02/baseui-v1-accessible/
- Fluent UI / Griffel — https://github.com/microsoft/fluentui , https://griffel.js.org/react/guides/atomic-css/
- IBM Carbon — https://github.com/carbon-design-system/carbon , https://www.npmjs.com/package/@carbon/styles
- PrimeReact — https://primereact.org/unstyled/ , https://primereact.org/theming/
- Shoelace / Web Awesome — https://github.com/shoelace-style/shoelace , https://shoelace.style/
- Stitches (EOL) — https://github.com/stitchesjs/stitches
- vanilla-extract — https://vanilla-extract.style/documentation/api/create-theme-contract/
- W3C DTCG — https://www.w3.org/community/design-tokens/2025/10/28/design-tokens-specification-reaches-first-stable-version/ , https://www.designtokens.org/tr/drafts/format/
- Style Dictionary — https://styledictionary.com/info/dtcg/ , https://styledictionary.com/versions/v5/migration/
- Terrazzo — https://github.com/terrazzoapp/terrazzo , https://terrazzo.app/docs/guides/dtcg/

## Open questions

- Concrete migration cost of moving the existing helioy.com surface off Tailwind 4 onto a CSS-variable/build-time token layer vs keeping Tailwind 4 for the marketing site only.
- Whether Tokens Studio's DTCG export conforms byte-clean to 2025.10 or carries vendor extensions.
- Open Props comparison vs the above (see `css-token-foundation-evaluation-open-props.md`); reconcile recommendations.
