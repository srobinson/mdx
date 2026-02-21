---
title: Vite Ecosystem Stack - Comprehensive 2026 Survey
type: research
tags: [vite, rolldown, biome, eslint, oxlint, vitest, tailwind, github-actions, ci-cd, monorepo, changesets, react, typescript]
summary: Vite 8.0.8 (Rolldown-powered, 10-30x faster builds) is the current stable. Biome v2 gaining for greenfield; ESLint v9 remains default. Vitest 4.1 is the testing standard. Changesets and semantic-release neck-and-neck at ~2.4M weekly downloads. Vite+ (VoidZero) unifying the full toolchain under one CLI.
status: active
source: deep-research
confidence: high
created: 2026-04-10
updated: 2026-04-10
---

## Executive Summary

Vite 8.0.8 (released March 12, 2026) represents the most significant architectural shift since Vite 2, replacing the dual esbuild/Rollup architecture with Rolldown, a single Rust-based bundler delivering 10-30x faster builds. The broader ecosystem is converging around Rust-based tooling: Rolldown for bundling, Oxc for parsing/transforming, Biome/oxlint for linting, and Oxfmt for formatting. VoidZero's Vite+ initiative aims to unify all of these under a single CLI, currently in alpha with public preview targeting early 2026. For linting, Biome v2 is the recommended choice for greenfield React/TypeScript projects, while ESLint v9 (50M+ weekly downloads) remains the safe default for projects with plugin dependencies.

---

## 1. Vite Version and Core Stack

### Current Stable: Vite 8.0.8 (March 12, 2026)

**Rolldown Integration (headline feature)**
- Single Rust-based bundler replaces both esbuild (dev transforms) and Rollup (prod bundling)
- 10-30x faster production builds. Real-world reports: Linear 46s to 6s (87% reduction), community reports of 4m to 30s, 12m to 2m, 78s to 3.5s
- Compatibility layer auto-converts `build.rollupOptions` to `build.rolldownOptions`
- Most existing Vite plugins work without changes

**Other Vite 8 Features**
- Integrated Devtools for module analysis and bundle debugging
- Built-in `resolve.tsconfigPaths` (tsconfig paths support without plugin)
- `emitDecoratorMetadata` support for TypeScript
- WebAssembly SSR (`.wasm?init` imports work in SSR)
- Browser console forwarding via `server.forwardConsole`
- Lightning CSS as default CSS minifier (previously esbuild)

**Requirements**: Node.js 20.19+ or 22.12+

**Framework Plugins (Vite 8)**
| Framework | Plugin | Version | Notes |
|-----------|--------|---------|-------|
| React | `@vitejs/plugin-react` | v6 | Uses Oxc for React Refresh (no Babel dependency) |
| React (SWC) | `@vitejs/plugin-react-swc` | current | SWC for dev transforms |
| Vue | `@vitejs/plugin-vue` | current | First-party |
| Svelte | `@sveltejs/vite-plugin-svelte` | current | SvelteKit uses Vite |
| Solid | `vite-plugin-solid` | current | Community maintained |

**create-vite templates**: vanilla, vanilla-ts, vue, vue-ts, react, react-ts, react-swc, react-swc-ts, preact, preact-ts, lit, lit-ts, svelte, svelte-ts, solid, solid-ts, qwik, qwik-ts

**Migration Path from Vite 6/7**
For complex projects, the recommended two-step approach:
1. Switch to `rolldown-vite` package on Vite 7 (isolates Rolldown issues)
2. Upgrade to Vite 8

HackerNews sentiment (item 47360730): overwhelmingly positive. Common 6-10x build improvements confirmed across large monorepos. Primary concerns: documentation gaps during migration, and one report of doubled bundle sizes. No significant plugin compatibility issues reported.

### Vite+ (VoidZero) - The Unified Toolchain

VoidZero (Evan You's company) is building Vite+ as a unified CLI:
- `vite new` - scaffolding with monorepo support
- `vite test` - Vitest
- `vite lint` - Oxlint (600+ ESLint-compatible rules)
- `vite fmt` - Oxfmt (Prettier-compatible, 36x faster)
- `vite lib` - library bundling via tsdown + Rolldown
- `vite run` - monorepo task runner with caching
- `vite ui` - GUI devtools

Status: alpha, open-sourced under MIT. Public preview targeting early 2026. Commercial licensing from VoidZero, open-source components remain MIT.

---

## 2. "uv" Clarification and Rust-based JS Tooling

### uv is Python-only

uv (astral-sh/uv) is a Rust-based Python package and project manager by the Ruff team. It replaces pip, pip-tools, pipx, poetry, pyenv, twine, and virtualenv. It has no JavaScript equivalent and no integration with JS/TS tooling chains.

There is no JS tool abbreviated as "uv." The user may have been thinking of one of these:
- **unbuild** (unjs/unbuild) - unified build system for JS libraries, not a package manager
- **Bun** - the closest JS parallel to uv's "one tool replaces everything" philosophy

### The Rust-based JS Tooling Landscape (2026)

| Tool | Replaces | Speed Gain | Status |
|------|----------|------------|--------|
| Rolldown | esbuild + Rollup | 10-30x vs Rollup | Stable in Vite 8 |
| Oxc (parser/transformer) | Babel, @typescript-eslint parser | 50-100x | Stable |
| Oxlint | ESLint | 50-100x | Stable, 300+ rules |
| Oxfmt | Prettier | 36x | Beta, 100% JS/TS Prettier conformance |
| Biome | ESLint + Prettier | 10-20x vs ESLint | Stable v2, 423+ rules |
| SWC | Babel | 20x | Stable, used by Next.js |
| Turbopack | Webpack | varies | Stable in Next.js 16 |
| Rspack | Webpack | 5-10x | Stable |

**Key takeaway**: By mid-2026, the fastest tool in every category of the JS toolchain is written in Rust. The VoidZero stack (Rolldown + Oxc + Oxlint + Oxfmt) is converging into the Vite+ unified toolchain.

---

## 3. Lint and Format Tooling

### The Three Contenders

**ESLint v9** (default, 50M+ weekly downloads)
- Flat config is now the default and stable; eslintrc is deprecated
- `defineConfig()` adds type safety for config files
- 700+ rules, 4000+ community plugins
- Full TypeScript support via @typescript-eslint with type-aware rules
- Weaknesses: slow (JS-based), complex configuration

**Biome v2** (~1.5M weekly downloads, 100k+ GitHub stars)
- Combined linter + formatter in single Rust binary
- 423+ lint rules, 96%+ Prettier formatting compatibility
- Type-aware linting added in v2
- 10-20x faster than ESLint
- Weaknesses: ~75-85% typescript-eslint rule coverage, no embedded language formatting (GraphQL, CSS-in-JS), limited HTML/Markdown/SCSS support, VSCode extension reliability issues reported

**Oxlint 0.x** (~500K weekly downloads)
- 300+ rules, 50-100x faster than ESLint, 2x faster than Biome for pure linting
- 43 type-aware rules (based on typescript-go)
- Weaknesses: limited auto-fix, no formatter, minimal plugin ecosystem, no complex per-directory config

### Recommendation Matrix

| Scenario | Recommended Tool |
|----------|-----------------|
| Greenfield React/TS project | Biome v2 (lint + format in one) |
| Existing project with ESLint plugins | Keep ESLint v9 |
| Vue/Svelte/Angular project | ESLint v9 (framework plugins required) |
| CI speed bottleneck in monorepo | Oxlint pre-pass + ESLint for specialized rules |
| Maximum simplicity | Biome v2 |

### Prettier vs Biome Formatter

Biome formatter achieves 96%+ Prettier compatibility for JS/TS/JSX. The gap:
- Biome lacks: HTML, Markdown, SCSS, GraphQL, CSS-in-JS, YAML formatting
- If you only format JS/TS/JSX/JSON/CSS: Biome is a full Prettier replacement
- If you format anything else: keep Prettier for those file types

### HackerNews Sentiment (item 43913950)

Mixed. Successful migrations reported for pure React/TS codebases. Reverts happened when JSX/TSX edge cases surfaced or embedded languages needed formatting. One team found unreported linting issues after reverting from Biome to ESLint, suggesting Biome's rule coverage gaps are real. Oxlint awareness is growing but adoption is nascent.

---

## 4. Directory Structure

### Consensus: Feature-based with colocation

The community has converged on feature-based organization over layer-based (grouping by file type). The principle: "colocate first, extract later."

```
src/
  features/          # Business domains
    auth/
      components/
      hooks/
      api.ts
      types.ts
      auth.test.ts
    dashboard/
      components/
      hooks/
      api.ts
      types.ts
  shared/            # Cross-feature code
    components/      # Reusable UI (Button, Modal, etc.)
    hooks/           # useDebounce, useLocalStorage
    utils/           # Pure utility functions
    types/           # Shared TypeScript types
  pages/             # Route-level components (or routes/)
  lib/               # Third-party wrappers, API clients
  assets/            # Static assets (images, fonts)
  config/            # App configuration
  main.tsx           # Entry point
  App.tsx            # Root component
public/              # Static files served as-is
tests/
  e2e/               # Playwright E2E tests
```

**Key conventions**:
- Files: kebab-case (`auth-form.tsx`)
- Components: PascalCase (`AuthForm`)
- Everything else: camelCase
- Tests: colocated with source (`feature.test.ts` next to `feature.ts`)
- E2E tests: separate `tests/e2e/` directory
- Types: colocated in feature, shared types in `src/shared/types/`
- Import rule: features can only import from `shared/` or ancestor folders within the same feature

**Config files at root**:
```
vite.config.ts
tsconfig.json
tsconfig.app.json (Vite 8 split)
biome.json OR eslint.config.ts
tailwind: configured in CSS via @import "tailwindcss" (v4 removes tailwind.config.js)
```

---

## 5. GitHub Actions for Vite Projects

### Recommended CI Workflow

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ci:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [20, 22]
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4
        with:
          version: 10

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'pnpm'

      - run: pnpm install --frozen-lockfile

      - run: pnpm lint        # biome check OR eslint .
      - run: pnpm typecheck   # tsc --noEmit
      - run: pnpm test        # vitest run
      - run: pnpm build       # vite build

      - uses: actions/upload-artifact@v4
        if: matrix.node-version == 22
        with:
          name: dist
          path: dist/
```

### Caching Strategy

| What | How | Cache Key |
|------|-----|-----------|
| pnpm store | Built into `setup-node` with `cache: 'pnpm'` | `${{ runner.os }}-pnpm-store-${{ hashFiles('**/pnpm-lock.yaml') }}` |
| Vite dep cache | `actions/cache@v4` targeting `node_modules/.vite` | `${{ runner.os }}-vite-${{ hashFiles('**/pnpm-lock.yaml') }}` |
| Vitest cache | `actions/cache@v4` targeting `node_modules/.vitest` | Similar pattern |
| Playwright browsers | `actions/cache@v4` or `playwright-github-action` | `${{ runner.os }}-playwright-${{ hashFiles('**/pnpm-lock.yaml') }}` |

Cold pnpm install: ~1m 20s. Warm cache: ~40s + 10s compression.

### Deployment

For static sites (GitHub Pages), use the official Vite guide:
- `actions/configure-pages` + `actions/upload-pages-artifact` + `actions/deploy-pages`
- Or the community `vite-github-pages-deployer` action

For preview deploys: Vercel/Netlify GitHub integrations handle this automatically on PRs.

---

## 6. Version and Release Management

### Tool Comparison (2026)

| | Changesets | semantic-release | release-please |
|---|---|---|---|
| Weekly downloads | ~2.4M | ~2.3M | ~350K (est.) |
| GitHub stars | ~9.3K | ~23.5K | ~2.5K (est.) |
| Automation level | Manual (changeset files) | Full (commit-driven) | Semi (PR-driven) |
| Monorepo support | Native, first-class | Via community plugin (stale) | Via manifest config |
| Changelog | Generated from changeset descriptions | Generated from commit messages | Generated from commits |
| Human oversight | Required (changeset authoring) | None | PR merge gate |
| Conventional commits | Optional | Required | Required |

### Recommendations

**For monorepos publishing multiple npm packages**: Changesets. It's purpose-built for this. Decouples versioning from commit messages. Manages inter-package dependency bumps automatically. Used by Vite itself, TanStack, shadcn/ui, and most major open-source monorepos.

**For single-package repos wanting full automation**: semantic-release. Zero manual intervention. Best multi-branch support (beta/alpha channels).

**For Google-style PR review gates**: release-please. Creates release PRs that humans review before merging. Good for teams wanting oversight without manual changeset files.

### Conventional Commits Enforcement

Standard stack:
- **commitlint** + **@commitlint/config-conventional**: validates commit messages
- **husky** (or **lefthook**): runs git hooks
- **lint-staged**: runs linters on staged files only
- **commitizen**: interactive CLI for writing conventional commits

Lefthook (Go-based) is gaining ground over husky for performance (parallel hook execution, 10x faster in large projects, no Node.js dependency). For pure JS projects, husky + lint-staged remains the default. For polyglot monorepos, lefthook wins.

---

## 7. Quickstart Templates

### Official

`npm create vite@latest` with templates: react-ts, react-swc-ts, vue-ts, svelte-ts, solid-ts, etc. Minimal by design: no linting, no testing, no CI. Starting point only.

### High-Star Community Templates

| Template | Stars | Stack |
|----------|-------|-------|
| [Vitesse](https://github.com/antfu-collective/vitesse) (antfu) | 9.2K | Vue + UnoCSS + file-based routing + i18n + PWA |
| [React Starter Kit](https://github.com/kriasoft/react-starter-kit) | 23K | React + Material UI + Firebase + TypeScript |
| [vite-react-boilerplate](https://github.com/RicardoValdovinos/vite-react-boilerplate) | 1K | React + TanStack Router/Query + Tailwind + Vitest + Playwright + Storybook + Husky + Commitlint |

### Production-Ready Templates (React + TypeScript + Tailwind + shadcn)

**[vite-react-boilerplate](https://github.com/RicardoValdovinos/vite-react-boilerplate)** (most complete)
- TanStack Router + Query + Table, Zustand, React Hook Form + Zod
- Tailwind CSS, HeadlessUI, Heroicons
- Vitest + React Testing Library + Playwright
- ESLint + Prettier + Husky + Commitizen + Commitlint
- Storybook, i18n, Docker
- Feature-based directory structure

**[react-vite-shadcn-ui](https://github.com/dan5py/react-vite-shadcn-ui)** (shadcn-focused)
- React + Vite + shadcn/ui + Tailwind v4 + TypeScript

**[react-vite-biome-starter](https://github.com/esoterik-dev/react-vite-biome-starter)** (Biome-focused)
- React + TypeScript + Vite + Biome + Husky + Commitizen

### Tailwind v4 + Vite Setup (2026)

Tailwind v4 eliminates `tailwind.config.js`. Setup:
1. `pnpm add -D tailwindcss @tailwindcss/vite`
2. Add `tailwindcss()` to Vite plugins
3. Replace `@tailwind` directives with `@import "tailwindcss"` in CSS
4. Configure via CSS (not JS): `@theme { --color-primary: oklch(...) }`

Full builds 5x faster, incremental builds 100x faster than v3.

### shadcn/ui + Vite Setup

1. Scaffold with `pnpm create vite@latest --template react-ts`
2. Install Tailwind v4 with `@tailwindcss/vite`
3. Configure path aliases in `tsconfig.json` and `vite.config.ts`
4. Run `npx shadcn@latest init`

---

## Testing Stack (2026)

**Vitest 4.1.3** is the standard for Vite projects.

Key features:
- Browser Mode (stable): tests in real browsers, not jsdom
- Visual regression testing: `toMatchScreenshot()` assertion
- Playwright Traces integration
- Async leak detection (`--detect-async-leaks`)
- Test tags for filtering and configuration
- `aroundEach` / `aroundAll` hooks (v4.1)
- Vite 8 compatible

Pair with:
- React Testing Library for component tests
- Playwright for E2E
- MSW for API mocking

---

## Package Manager Recommendation

| Manager | Install Speed | Disk Usage (200 deps) | Best For |
|---------|--------------|----------------------|----------|
| pnpm | 6-8x npm | 124 MB | Monorepos, Vite projects (Vite uses pnpm) |
| Bun | 25-30x npm | 461 MB | Maximum install speed |
| npm | baseline | 487 MB | Maximum compatibility |

Recommendation: **pnpm** for Vite projects. It's what Vite itself uses, has first-class monorepo support, and the best balance of speed/disk/compatibility.

---

## Monorepo Tooling

| | Turborepo | Nx |
|---|---|---|
| Best for | Startups, 3-15 devs, simplicity | Enterprise, 5+ teams, enforced boundaries |
| Task analysis | Package-level (coarse) | File-level (fine-grained) |
| CI benchmark (2026) | 25m 32s | 21m 56s |
| Config | Minimal (turbo.json) | Rich (nx.json + project.json) |
| Remote cache | Vercel (free/paid) | Nx Cloud (free/paid) |

For most teams starting out: Turborepo. Migrate to Nx if you outgrow it.

---

## Sources Consulted

### Official Documentation
- [Vite 8.0 Announcement](https://vite.dev/blog/announcing-vite8)
- [Vite Releases](https://vite.dev/releases)
- [Vite Migration Guide v7 to v8](https://vite.dev/guide/migration)
- [Vitest 4.0 Announcement](https://vitest.dev/blog/vitest-4)
- [Biome Differences with Prettier](https://biomejs.dev/formatter/differences-with-prettier/)
- [Tailwind CSS v4](https://tailwindcss.com/blog/tailwindcss-v4)
- [shadcn/ui Vite Installation](https://ui.shadcn.com/docs/installation/vite)
- [pnpm CI Docs](https://pnpm.io/continuous-integration)

### Analysis and Comparisons
- [PkgPulse: Biome vs ESLint vs Oxlint 2026](https://www.pkgpulse.com/blog/biome-vs-eslint-vs-oxlint-2026)
- [PkgPulse: TanStack Router vs React Router v7](https://www.pkgpulse.com/blog/tanstack-router-vs-react-router-v7-2026)
- [PkgPulse: Turborepo vs Nx 2026](https://www.pkgpulse.com/blog/turborepo-vs-nx-monorepo-2026)
- [The Register: Vite 8 Rolldown 10-30x faster](https://www.theregister.com/2026/03/16/vite_8_rolldown/)
- [Builder.io: Vite 8, Vite+, and Void](https://www.builder.io/blog/vite-8-vite-plus-void)
- [npm trends: changesets vs semantic-release](https://npmtrends.com/@changesets/cli-vs-np-vs-publish-please-vs-release-it-vs-semantic-release)
- [Oleksii Popov: NPM Release Automation Guide](https://oleksiipopov.com/blog/npm-release-automation/)
- [PkgPulse: pnpm vs npm vs yarn vs Bun 2026](https://www.pkgpulse.com/blog/pnpm-npm-yarn-bun-2026)

### Community Discussions
- [HN: Vite 8.0 Is Out (item 47360730)](https://news.ycombinator.com/item?id=47360730) - overwhelmingly positive, 6-10x improvements common
- [HN: Migrating ESLint/Prettier to Biome (item 43913950)](https://news.ycombinator.com/item?id=43913950) - mixed, gaps in embedded languages and framework plugins
- [HN: Vite+ Unified Toolchain (item 45537035)](https://news.ycombinator.com/item?id=45537035)

### VoidZero / Vite+
- [VoidZero: Announcing Vite+](https://voidzero.dev/posts/announcing-vite-plus)
- [VoidZero: What's New Feb 2026](https://voidzero.dev/posts/whats-new-feb-2026)
- [VoidZero: March Launch Week](https://voidzero.dev/posts/whats-new-march-launch-week-2026)

### GitHub Repositories
- [vitejs/vite](https://github.com/vitejs/vite)
- [vitejs/awesome-vite](https://github.com/vitejs/awesome-vite)
- [RicardoValdovinos/vite-react-boilerplate](https://github.com/RicardoValdovinos/vite-react-boilerplate)
- [antfu-collective/vitesse](https://github.com/antfu-collective/vitesse)
- [changesets/changesets](https://github.com/changesets/changesets)
- [googleapis/release-please](https://github.com/googleapis/release-please)

---

## Source Quality Assessment

**High confidence**: Vite version numbers, Rolldown integration details, Vitest features, Tailwind v4 setup, package manager benchmarks. All verified against official docs and multiple independent sources.

**Medium confidence**: Biome adoption trajectory, oxlint rule counts, exact npm download numbers. These change weekly. Biome ecosystem gaps confirmed by HackerNews migration reports.

**Lower confidence**: Vite+ production readiness timeline (VoidZero marketing vs reality). Release management "winner" (no clear winner; both Changesets and semantic-release are ~2.4M downloads). Reddit had zero signal for any of these topics.

---

## Open Questions

1. **Vite+ commercial model**: VoidZero claims MIT for components but "commercial licensing" for Vite+ itself. Unclear what the paid tier includes vs the free version.
2. **Oxfmt stability**: Beta with 100% JS/TS Prettier conformance, but real-world production usage data is thin.
3. **Biome v2 type-aware linting depth**: Claims 75-85% typescript-eslint coverage, but specific gap analysis not well documented.
4. **Rolldown bundle size regression**: One HN commenter reported doubled build sizes. Isolated case or systematic issue? Needs monitoring.
5. **Vite 8 + Tailwind v4 monorepo setup**: The Nx blog covers this but community reports are sparse.
