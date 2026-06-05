---
title: lilo-moon-template adjacent scout
type: projects
tags: [lilo-moon-template, scout, reuse, moon, oxlint, audioface, cubicell, b_turbo_template]
summary: Reuse map from b_turbo_template, cubicell, and audioface for wave 1 library and app exemplars.
status: active
project: lilo-moon-template
confidence: high
---

# Adjacent scout: wave 1 exemplars

Read-only audit of the three repos that will adopt the baseline. littleorgans is out of scope; no proposal here requires changing it.

| Repo | HEAD | Role |
|---|---|---|
| `b_templates/lilo-moon-template` | `1cb4e4166bcb52001a91f005cf5c15196ae5ad96` | New baseline (moon 2.5.1, pnpm 11.22.0, TS ~7.0.2, oxlint 1.79.0 + oxfmt 0.64.0). Empty `packages/`. No exemplars, CI, changesets, README, or AGENTS.md. |
| `b_templates/b_turbo_template` | `0cb52904518a50f44bb7174fce68b8f31755264d` | Outgoing template. Turbo 2.10, Biome, pnpm 10.2.0, TS ~5.9.3, Convex. |
| `helioy/cubicell` | `67c6dde0441e12ed5cce3c937d2718110c8691bd` | Single-package Vite React app. oxlint + oxfmt. No workspace. |
| `helioy/audioface` | `fd347d4b6dbece0a37d2c4f2bec9057b1165b9c2` (`phase2-gate-tests`) | pnpm workspace. Five source packages + `apps/studio`. `node --test`. No oxlint. |

Searches run (also reported as none found when empty): `moon.yml` / `.moon/` in cubicell and audioface; `vitest.config.*` in all three adjacent; `composite` in all three adjacent; `publishConfig` / `files` / conditional `exports` on audioface packages; `.changeset/` in cubicell and audioface; oxlint/oxfmt/biome/eslint in audioface; `@vitejs/plugin-react` in the baseline catalog; `packages/react` on disk in audioface; `scripts/start.js` and root `index.js` in b_turbo_template.

## Reuse Map

- Reuse: `helioy/audioface/packages/{cli,core,dom,engine,stores}/package.json` `exports["."]` The library exemplar must be this shape if those five packages are to adopt it unchanged: `"private": true`, `"type": "module"`, `"version": "0.0.0"`, `"exports": { ".": "./src/index.ts" }`. No `main`, `types`, `files`, `scripts`, `publishConfig`, or export conditions. No `dist/`. `cli` and `dom` have no deps; `core` has `zod: "catalog:"`; `engine` has `@audioface/core: "workspace:*"`; `stores` adds `zustand: "catalog:"`.
- Reuse: `helioy/audioface/packages/stores/package.json` `peerDependencies.react` Named catalog `catalog:react-peer` is how a React-using library declares a peer. Only `stores` does this. Baseline already has `pnpm-workspace.yaml` `catalogs.react-peer` (`react` and `react-dom` `>=19`). Audioface's named catalog is `react: ">=18"` only, no `react-dom`. Keep the baseline range.
- Reuse: `helioy/audioface/pnpm-workspace.yaml` `catalog` Default catalog plus `catalog:` / `workspace:*` in package manifests. Baseline already has this, plus `services/*`. Do not copy audioface's `zod` / `zustand` into the language-agnostic catalog.
- Reuse: `helioy/audioface/apps/studio/index.html` plus `apps/studio/src/main.tsx` `createRoot` / `StrictMode`, and `helioy/cubicell/index.html` plus `src/main.tsx` `createRoot` / `StrictMode`. App exemplar needs `index.html` with `script type="module"` into `src/main.tsx`, a mount node, React 19 `createRoot`, and `StrictMode`. Studio mounts `#studioRoot`; cubicell and b_turbo `apps/basic` mount `#root`. Prefer `#root`.
- Reuse: `helioy/audioface/apps/studio/vite.config.ts` `defineConfig` `plugins: [react()]` and `helioy/cubicell/vite.config.ts` `react()`. App exemplar Vite config is `@vitejs/plugin-react` only. Cubicell's `studioPreloadPlugin`, `visualizer`, and `build.rolldownOptions` `codeSplitting.groups` stay in cubicell. b_turbo `apps/basic/vite.config.ts` `tanstackRouter` / `tailwindcss` stay in the outgoing template.
- Reuse: `helioy/audioface/apps/studio/package.json` `scripts.dev` / `scripts.build` and `helioy/cubicell/package.json` `scripts.dev` / `scripts.build`. App needs `vite` (studio also `--host 127.0.0.1 --port 4174 --strictPort`) and `vite build`. Cubicell prefixes with `tsc -b`. Default Vite `outDir` `dist/` and `assetsDir` `assets` in both. Studio has no `preview`; cubicell has `vite preview` and `preview:prod --port 4173`.
- Reuse: `helioy/cubicell/tsconfig.json` `references`, `helioy/audioface/apps/studio/tsconfig.json` `references`, `b_templates/b_turbo_template/apps/basic/tsconfig.json` `references`. App tsconfig is a solution file (`files: []`) referencing `tsconfig.app.json` (DOM, `jsx: "react-jsx"`, `moduleResolution: "bundler"`, `types: ["vite/client"]`) and `tsconfig.node.json` (Node, includes `vite.config.ts`). Env types come from `compilerOptions.types: ["vite/client"]`, not a `vite-env.d.ts` (cubicell and studio). b_turbo `apps/basic/src/app/vite-env.d.ts` is leftover glsl/webgl.
- Reuse: `helioy/audioface/tsconfig.strict.json` `compilerOptions.allowImportingTsExtensions` Required by source-export libraries that import `./foo.ts` (`packages/core/src/index.ts` re-exports `./contracts.ts`). Cubicell `tsconfig.app.json` / `tsconfig.node.json` and b_turbo `packages/typescript-config/base.json` set the same flag with `noEmit: true`. Baseline `tsconfig.options.json` does not.
- Reuse: `helioy/cubicell/package.json` `scripts.check` Format then lint. Matches baseline `justfile` `check` (`moon run root:format root:lint-fix` then `moon check --all`) and b_turbo `package.json` `scripts.check`. Keep that convention. Cubicell `check` mutates (`oxfmt --write`, `oxlint --fix`); CI in the baseline stays read-only via `justfile` `ci` → `moon ci`.
- Reuse: `helioy/cubicell/.oxlintrc.json` `plugins` `react` and `rules["react/rules-of-hooks"]` App overlay only. Baseline `.oxlintrc.json` has no React plugin. The app exemplar (and cubicell on adoption) needs hooks enforcement. Do not lift cubicell's barrel `no-restricted-imports` or `react/only-export-components` warn into the baseline.
- Reuse: `b_templates/b_turbo_template/package.json` `scripts.changeset` / `changeset:version` / `changeset:publish` CLI wiring for issue #6. Keep `commit: false`, `baseBranch: "main"`, `updateInternalDependencies: "patch"` from `.changeset/config.json`. Rewrite `changelog` (today `"alphabio/b_fluid"`) and `ignore` (today `@b/typescript-config`, `@b/tailwind-config`). Do not copy `scripts.release` (versions and publishes in one local shot) or `TMP/release.yml` as-is (Node 20, pnpm 10.2.0, `NPM_TOKEN` commented).
- Reuse: `b_templates/b_turbo_template/lefthook.yaml` `pre-commit` / `commit-msg` / `pre-push` and `commitlint.config.js` `extends` `@commitlint/config-conventional` Wave 2 (lefthook + commitlint). Retarget staged format/lint to oxfmt/oxlint. Drop `rules["scope-enum"]` product scopes (`basic`, `b_components`, …). Add `lefthook install` to `moon setup`; b_turbo never does (`package.json` has no `scripts.prepare`).
- Reuse: `b_templates/b_turbo_template/.github/workflows/ci.yml` `concurrency` plus `pnpm install --frozen-lockfile` CI pattern for issue #4. Drive the gate with `moon ci`, Node 24.19, pnpm 11.22 from `package.json` `packageManager` / `.moon/toolchains.yml`. Do not copy Node 20, hardcoded `pnpm/action-setup` `version: 10.2.0`, Biome jobs, or four copy-pasted setup blocks.
- Reuse: `b_templates/b_turbo_template/package.json` `scripts.preinstall` `pnpx only-allow pnpm` Optional small adapt. Baseline already pins `packageManager` `pnpm@11.22.0`.
- Existing infra: `b_templates/lilo-moon-template/tsconfig.options.json` `compilerOptions.composite` / `declaration` plus `.moon/toolchains.yml` `typescript.syncProjectReferences` Moon will write `tsconfig.json` `references` once exemplars exist. `routeOutDirToCache: true` sends emit to `.moon/cache/types`.
- Existing infra: `b_templates/lilo-moon-template/.moon/tasks/node.yml` `tasks.typecheck` (`tsc --build --pretty`, `deps: ["^:typecheck"]`), `tasks.test` (`vitest run`, `outputs: ["coverage"]`), `tasks.test-watch`. JS projects inherit these. Root `moon.yml` `workspace.inheritedTasks.include: []` correctly excludes the root from them.
- Existing infra: `b_templates/lilo-moon-template/pnpm-workspace.yaml` `catalog` (`typescript ~7.0.2`, `react`/`react-dom` `^19.2.8`, `vite ^8.2.1`, `vitest` / `@vitest/coverage-v8` `^4.1.11`) and `catalogs.react-peer` (`>=19`). Lockfile today only materializes `typescript`; other catalog keys wait on exemplars.
- Existing infra: `b_templates/lilo-moon-template/.oxlintrc.json` plus `moon.yml` `tasks.lint` (`oxlint --type-aware --deny-warnings --no-error-on-unmatched-pattern`) and `.oxfmtrc.json` (`printWidth` 100, `singleQuote` false, `sortImports` true). Workspace-wide gates, not per project.
- Existing infra: `b_templates/lilo-moon-template/.npmrc` `auto-install-peers=false` / `strict-peer-dependencies=true`. b_turbo `.npmrc` `auto-install-peers=true` hides missing peers (audioface `stores` gets `react` installed that way). Keep the baseline.
- Similar checked and rejected: `b_templates/b_turbo_template/turbo.json` entire file. Turbo cannot read Cargo/pyproject graphs. `tasks.test.dependsOn` `^test` is the wrong edge. `tasks.build.env` `VITE_CONVEX_URL` is product. Moon already owns the graph.
- Similar checked and rejected: `b_templates/b_turbo_template/biome.json`, Prettier, markdownlint-cli2. Cubicell and the baseline already collapsed this to oxlint + oxfmt. Biome `formatter.lineWidth` 120 fights oxfmt `printWidth` 100. Biome uses warn-level rules; baseline policy is error or absent.
- Similar checked and rejected: `b_templates/b_turbo_template/packages/typescript-config` (`name` `@b/typescript-config`). Handover already chose root `tsconfig.options.json` plus moon sync over a config package. Extract a pnpm `configDependencies` package at the second consumer, not now. `base.app.json` puts `baseUrl` / `paths` outside `compilerOptions` (dead). README is the string `# tailwind-config`.
- Similar checked and rejected: `b_templates/b_turbo_template/apps/basic` as the app exemplar. TanStack Router, Tailwind 4, Convex, Howler, recharts, framer-motion. Neither cubicell nor audioface studio uses that stack. `apps/basic/src/app/main.tsx` is RouterProvider + web-vitals, not the createRoot shell those two apps share.
- Similar checked and rejected: `helioy/cubicell/.oxlintrc.json` `rules["no-restricted-imports"]` Barrel groups for `domain` / `evaluation` / `transport` / `pose` / `view` / `interaction` / `camera` plus overrides under those trees and `tests/**`. Cubicell architecture, not a language-agnostic baseline.
- Similar checked and rejected: `helioy/cubicell/.oxlintrc.json` `rules["react/only-export-components"]` warn, and `rules["sort-imports"]`. Baseline forbids warn. oxfmt `sortImports: true` already owns import sort.
- Similar checked and rejected: `helioy/cubicell/vite.config.ts` `test.projects` plus `tests/contracts/governance.json` and `scripts/run-contract-tests.mjs`. Playwright Chromium contracts, wall-clock budgets, forbidden `jsdom` / `@testing-library`. App-specific harness. `governance.json` `local.forbiddenImports` includes `jsdom`.
- Similar checked and rejected: `helioy/audioface/package.json` `scripts.test` `node --test` and `test/*.test.mjs`. Tests import `../packages/*/src/index.ts` by path. Baseline inherited task is `vitest run`. Do not make `node --test` the exemplar runner. Audioface keeps its runner until those tests migrate.
- Similar checked and rejected: `b_templates/b_turbo_template/package.json` `devDependencies["jsdom"]` and `devDependencies["@vitejs/plugin-react-swc"]` / `vite-plugin-dts` / `vite-plugin-glsl`. jsdom is unused (no tests, no `environment: "jsdom"`). Only `plugin-react` is imported (`apps/basic/vite.config.ts`). `vite-plugin-dts` is never imported. Cubicell forbids jsdom in unit contracts.
- Similar checked and rejected: `b_templates/b_turbo_template/packages/{ui,b_components}/package.json` `peerDependencies.react` `"catalog:"` App pin as a library peer. Use `catalog:react-peer`.
- Similar checked and rejected: `helioy/audioface/pnpm-workspace.yaml` `catalogs.react-peer` `react: ">=18"` Do not lower the baseline (`>=19` for both react and react-dom).
- Similar checked and rejected: `b_templates/b_turbo_template/package.json` `workspaces`, `main`, `scripts.start`. Dead npm `workspaces` beside `pnpm-workspace.yaml`. `main` `"index.js"` with no file. `scripts.start` `node scripts/start.js` with no file (`scripts/` only has `add-catalog-dep.sh`).
- Similar checked and rejected: `b_templates/b_turbo_template/package.json` `scripts.clean` Deletes `pnpm-lock.yaml`. `devDependencies` dump of app plugins at root (`@tanstack/router-plugin`, both React Vite plugins, `@types/howler`, `tw-animate-css`, `web-vitals`, `dotenv-cli`).
- Similar checked and rejected: `b_templates/b_turbo_template/apps/basic/tsconfig.app.json` `compilerOptions.paths["@shared/*"]` and `["@ui/*"]`. Cross-package path aliases. `packages/shared` does not exist. Consume workspace packages by name.
- Similar checked and rejected: Convex catalog entries and `.env.example` `VITE_CONVEX_URL` / `CONVEX_DEPLOYMENT`. Handover dropped Convex. Env example uses `export KEY=` shell syntax and a real deployment id.
- None found: publishable library packaging. Searched `packages/*/package.json` in audioface and b_turbo for `files`, conditional `exports` (`import`/`types`/`require`), emitted `types`, `publishConfig` on a built package, tsup/unbuild/vite lib mode, `dist/` under `packages/*`. Result: every workspace library exports TypeScript source. b_turbo `@b/typescript-config` has `publishConfig.access: "public"` on a `private` config package with no JS. A dist dual-package exemplar would force a rewrite of audioface's five manifests, `.ts` relative imports, and `node --test` path imports.
- None found: standalone `vitest.config.*` in any adjacent repo. Cubicell inlines `test` in `vite.config.ts`. b_turbo has `scripts.test:base` `vitest run` with no config and no `*.test.ts`. Audioface has no vitest. Coverage thresholds: none (catalog `@vitest/coverage-v8` in the baseline is unused). Issue #5 is new.
- None found: `@vitejs/plugin-react` in `lilo-moon-template/pnpm-workspace.yaml` `catalog`. Audioface catalogs `^6.0.3`; cubicell pins `^6.0.4` in `package.json` `devDependencies`. App exemplar cannot `catalog:` the plugin until it is added.
- None found: `jsx` / `DOM` in `lilo-moon-template/tsconfig.options.json`. App tsconfig must add `jsx: "react-jsx"` and `lib` DOM on the app project, not the shared options file.
- None found: `moon.yml` / `.moon/` in cubicell or audioface. Adoption means adding moon, not matching an existing moon layout.
- None found: changesets in cubicell or audioface. Issue #6 has one donor: b_turbo, and it is Turbo-shaped (see Reuse + rejected).

### Catalog adoption conflicts

| Key | baseline | audioface | cubicell | b_turbo |
|---|---|---|---|---|
| `typescript` | `~7.0.2` | `^5.5.0` → 5.9.3 | `~6.0.3` | `~5.9.3` |
| `pnpm` | `11.22.0` | `10.8.1` | unset (CI `10.17.1`) | `10.2.0` |
| `node` | `24.19.0` | unset | CI 24 | CI 20 |
| `react` / `react-dom` | `^19.2.8` | `^19.2.7` | `^19.2.8` | `^19.2.0` |
| `react-peer` | `>=19` both | `react >=18` only | n/a | peers use default catalog |
| `vite` | `^8.2.1` | `^8.1.3` | `^8.1.5` | catalog `7.1.12` |
| `@vitejs/plugin-react` | missing | `^6.0.3` | `^6.0.4` | root `^5.2.0` |
| `vitest` | `^4.1.11` | none (`node --test`) | `^4.1.10` | root `^4.1.11`, not in catalog |
| `oxlint` / `oxfmt` | `1.79.0` / `0.64.0` | none | `^1.75.0` / `^0.60.0` | Biome 2.3.11 |
| `@types/node` | `^26.2.0` | `^26.1.0` | `^24.13.3` | root `^25.9.5` |

Hard conflicts on adoption: TypeScript 7, pnpm 11, type-aware oxlint. Those are already decided for the baseline. Vite 8 / React 19.2 / plugin-react 6 is the app line cubicell and studio already share; b_turbo Vite 7 / plugin-react 5 is leftover.

### oxlint: cubicell vs baseline

Cubicell enforces, baseline does not:

| Rule / plugin | Cubicell |
|---|---|
| plugin `react` | yes |
| `react/rules-of-hooks` | error |
| `sort-imports` `ignoreDeclarationSort: true` | error |
| `no-unused-vars` `fix.imports: "fix"` | extra fix key |
| `react/only-export-components` `allowConstantExport: true` | **warn** |
| `no-restricted-imports` barrel groups | error, with overrides |
| `ignorePatterns` `artifacts/**`, `docs/**` | extra |

Baseline enforces, cubicell does not:

| Rule / plugin | Baseline |
|---|---|
| plugins `unicorn`, `promise`, `import` | yes |
| `categories` correctness / suspicious / perf → error | yes (`pedantic` off) |
| `typescript/consistent-type-imports` | error |
| `typescript/no-floating-promises` | error (needs `--type-aware` + `oxlint-tsgolint`) |
| `typescript/no-misused-promises` | error |
| `typescript/await-thenable` | error |
| `typescript/no-explicit-any` | error |
| `promise/prefer-await-to-then` | error |
| `no-console` allow `warn`/`error` | error |
| `eqeqeq` always, `null: ignore` | error |
| `ignorePatterns` `**/*.gen.*`, `**/_generated/**` | extra |
| `--type-aware --deny-warnings` | command line, not config |
| `oxlint-tsgolint` `7.0.2001` | package pin |

Audioface: no oxlint config at all. Adoption adds the baseline set.

## Quality Map

- Duplication / parallel implementation: `helioy/audioface/src/*.js` (root `package.json` `exports` `./catalog`, `./contracts`, `bin.audioface` → `bin/audioface.mjs`) beside `packages/*/src`. Documented in `ARCHITECTURE.md` as legacy JS vs Studio/packages. Studio must not import root `src`. `@audioface/cli` `packages/cli/src/index.ts` is a stub; the real CLI is the root bin. `@audioface/dom` is unused except `tsconfig.strict.json` `compilerOptions.paths`.
- Duplication / parallel implementation: source-export libraries in audioface `packages/*/package.json` `exports` and b_turbo `packages/{ui,b_components,b_store}/package.json` `exports` / `main` / `types` all pointing at `src`. Two templates, one shape. Exemplar should encode it once.
- Boundary / design issue: `b_templates/b_turbo_template/package.json` `devDependencies` owns app bundler plugins. Inverts ownership: the app (`apps/basic/package.json`) only lists `@b/typescript-config` as a devDep. Catalog is bypassed (`@tanstack/react-router-devtools` catalog `1.134.9` vs root `^1.167.1`).
- Boundary / design issue: `helioy/audioface/tsconfig.packages.json` is one `noEmit` graph (`include: ["packages/**/*.ts"]`) with `compilerOptions.paths` to each barrel. No per-package `tsconfig.json`. Baseline moon `syncProjectReferences` wants one TS project per package. Binding the exemplar to moon composite is a migration for audioface, not an unchanged drop-in.
- Boundary / design issue: `helioy/cubicell/tsconfig.app.json` does not set `compilerOptions.strict`. Baseline `tsconfig.options.json` does, plus `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`. Cubicell adoption of shared options is a strictness jump, not only a TS 6 → 7 jump.
- Boundary / design issue: `.changeset/config.json` `changelog` repo `alphabio/b_fluid` and `ignore` `@b/*` config packages. Not reusable as-is for issue #6.
- Dead code / obsolete path: `b_templates/b_turbo_template/package.json` `scripts.start` (missing `scripts/start.js`); `main` `"index.js"` (missing); `workspaces`; `devDependencies["@vitejs/plugin-react-swc"]` (README-only in `packages/ui`); `devDependencies["vite-plugin-dts"]`; `packages/b_store/package.json` `scripts.codegen` (no `codegen.ts`); `packages/tailwind-config/package.json` `exports["."]` `./shared-styles.css` (file is `base.css`); `packages/{ui,b_components}/tsconfig.node.json` `include: ["vite.config.ts"]` with no such file.
- Dead code / obsolete path: `helioy/audioface/ARCHITECTURE.md` documents `packages/react`; directory missing; `node_modules/@audioface/react` is a dangling symlink to `../../packages/react`.
- Dead code / obsolete path: b_turbo hollow test graph (`turbo.json` `tasks.test`, `scripts.test`, no package `scripts.test`, no test files). `TMP/release.yml` claimed by `.github/CI-CD-GUIDE.md` as `.github/workflows/release.yml`.
- Dead code / obsolete path: cubicell `.env` exists and is not ignored (`.gitignore` only `*.local`). Keys are unused in `src/` (not `VITE_`-prefixed). Baseline `.gitignore` already ignores `.env*` with `!.env.example`; cubicell should gain that on adoption.
- Grooming recommendation: **refactor during the slice** for the library and app exemplars (source-export package.json, Vite+plugin-react, solution tsconfig, catalog plugin-react). **Refactor during** oxlint: add React plugin + `react/rules-of-hooks` as an app overlay or root plugin once the app exemplar exists; keep type-aware rules at root. **Defer** cubicell barrel `no-restricted-imports`, Playwright governance, audioface `node --test` tree, audioface legacy `src/*.js`, `@audioface/cli`/`dom` stubs. **Do not** refactor b_turbo; it is outgoing. **Defer with reason** extracting a shared config package until cubicell or audioface is the second consumer.

## Plan

- Decision needed: 1. Library exemplar shape. Bind to audioface `exports["."] = "./src/index.ts"` (unchanged adoption) **or** invent dist/`publishConfig`/conditional exports (issue #1 "publishable" wording). Evidence says the consumers are source-export workspace packages. A publish profile can be a later overlay; making dist the only exemplar blocks audioface.
- Decision needed: 2. tsconfig composition. Keep baseline `composite` + `declaration` + moon-synced references (exemplars become real TS projects, `tsc --build` matches `.moon/tasks/node.yml` `typecheck`) **or** match consumer `noEmit` + `allowImportingTsExtensions` (audioface unchanged, moon composite unused). These two flags fight: source `.ts` imports need `allowImportingTsExtensions` + `noEmit`; composite emit does not. Pick one for the exemplar and record the audioface/cubicell migration if composite wins.
- Decision needed: 3. Where React oxlint lives. Root `.oxlintrc.json` gains plugin `react` + `react/rules-of-hooks` when the app exemplar lands, **or** an app-local overlay. Barrel `no-restricted-imports` stays cubicell-only. `react/only-export-components` stays out (warn).
- Decision needed: 4. Issue #6 changesets `access` (`restricted` in b_turbo vs public GitHub packages) and changelog repo (must not ship `alphabio/b_fluid`). Ignore list should name the exemplar private app, not `@b/typescript-config`.
- Decision needed: 5. Catalog additions for the app exemplar: add `@vitejs/plugin-react` `^6.0.4` (cubicell) / `^6.0.3` (audioface). Leave `zod` / `zustand` out of the language-agnostic catalog. Do not add `jsdom`.

- Proposed steps bound to the reuse map:
  1. Library exemplar under `packages/`: audioface `package.json` shape (`private`, `type: module`, `exports["."] → ./src/index.ts`). Internal deps `workspace:*`, third-party `catalog:`. If it touches React, `peerDependencies.react` / `react-dom` `catalog:react-peer` (`>=19`). Barrel `src/index.ts` named exports. No `dist` build unless decision 1 says otherwise.
  2. Library `tsconfig.json` extends `tsconfig.options.json`. Add `allowImportingTsExtensions` only if decision 2 keeps source-export. Let moon fill root `references`. Prove `moon run <lib>:typecheck` (inherited `tsc --build`).
  3. Add `@vitejs/plugin-react` to `pnpm-workspace.yaml` `catalog` before the app (none found in baseline catalog).
  4. App exemplar under `apps/`: `private` + `type: module`; `react`/`react-dom`/`vite`/`@vitejs/plugin-react`/`@types/*` via `catalog:`; workspace lib via `workspace:*`. `index.html` + `src/main.tsx` `createRoot`/`StrictMode`/`#root`. `vite.config.ts` `defineConfig` `{ plugins: [react()] }`. Solution tsconfig app/node split; app adds `jsx: "react-jsx"`, DOM lib, `types: ["vite/client"]`. `scripts.dev` `vite`, `scripts.build` `tsc -b && vite build` (cubicell) or `vite build` (studio). Default `dist/`. No TanStack, Tailwind, Convex, cubicell preload/visualizer, or Playwright.
  5. Inherited moon `test`: add a real `*.test.ts` and a `vitest.config.ts` (or `test` block in `vite.config.ts`, cubicell style) so `.moon/tasks/node.yml` `test` is not a hollow graph like b_turbo. No jsdom. Coverage thresholds wait for issue #5; catalog already has `@vitest/coverage-v8`.
  6. oxlint: keep baseline categories and type-aware rules. Add React plugin + `react/rules-of-hooks` per decision 3. Do not add cubicell barrels or warn-level rules. App overlay may ignore `docs/**` / `artifacts/**` later; baseline already ignores `dist` / `*.gen.*` / `_generated`.
  7. Do not copy b_turbo `turbo.json`, Biome, root `devDependencies`, `workspaces`, `scripts.start`, `scripts.clean`, or CI Node 20. Wave 2 may retarget lefthook/commitlint as noted under Reuse.
  8. Issue #6 (later wave): new `.changeset/config.json` using the three reusable fields; new changelog repo; access per decision 4; ignore the private app exemplar. Workflow: `changesets/action` after `moon ci`, pnpm 11 / Node 24, not `TMP/release.yml`.

- Tests and gates:
  - `just check` then `just ci` (`moon ci`) on the exemplar tree.
  - Standing rule: a gate that passes on an empty repo has proven nothing. After each exemplar: break a type and confirm `typecheck` fails; add an unfixable lint error and confirm `lint` fails; add a failing test and confirm `test` fails; revert.
  - `oxlint --type-aware` must run against real files (tsgolint false-green already happened on this baseline).
  - App: `vite build` produces `dist/index.html`.
  - Library: importer in the app resolves `exports["."]` to `src/index.ts` (or to `dist` if decision 1 goes publishable).
  - Do not run consumer test suites from this baseline. Cubicell Playwright and audioface `node --test` stay in those repos.
