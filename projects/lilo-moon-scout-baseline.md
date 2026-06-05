---
title: lilo-moon-template scout baseline and wave-1 issue contract
type: projects
tags: [lilo-moon-template, scout, moon, oxlint, wave-1, baseline]
summary: Evidence-backed inventory of the 15-file moon baseline and the four serial wave-1 GitHub issues
status: active
created: 2026-08-20
updated: 2026-08-20
project: lilo-moon-template
confidence: high
---

# lilo-moon-template scout: baseline and wave-1 contract

Baseline SHA `1cb4e4166bcb52001a91f005cf5c15196ae5ad96` on `main` (4 commits, clean tree). Live versions: moon 2.5.1, node 24.19.0, pnpm 11.22.0, TypeScript 7.0.2, oxlint 1.79.0, oxfmt 0.64.0, oxlint-tsgolint 7.0.2001. Repo `littleorgans/lilo-moon-template`. Wave-1 issues 1-4 are OPEN on milestone `Template v1`.

This file is a reuse map. The build engineer should bind to the owners named here. A new helper, task, pin, or catalog entry for something already listed is a defect.

## Current State

### Tracked files (15)

`.editorconfig`, `.gitignore`, `.moon/tasks/node.yml`, `.moon/toolchains.yml`, `.moon/workspace.yml`, `.npmrc`, `.oxfmtrc.json`, `.oxlintrc.json`, `justfile`, `moon.yml`, `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, `tsconfig.json`, `tsconfig.options.json`.

On disk, `packages/` exists and is empty (not tracked). `apps/` and `services/` do not exist. No `*.ts` / `*.tsx` / `*.js` / `*.jsx` outside `node_modules` and `.moon/cache`. No `AGENTS.md`, no `.github/`, no `README`, no `vitest.config.*`.

### `.moon/workspace.yml`

`projects.globs`: `apps/*`, `packages/*`, `services/*`. `projects.sources.root`: `.` (the root project). `vcs`: git, `defaultBranch` main, `provider` github.

`moon query projects` returns one project, id `root`. The globs match nothing.

### `.moon/toolchains.yml`

In force, with plugin schema from `moon toolchain info <id>`:

| Toolchain plugin | Plugin version | Config in this repo |
| --- | --- | --- |
| `javascript` | 1.3.0 | `packageManager` pnpm; `inferTasksFromScripts` false; `syncProjectWorkspaceDependencies` true; `dependencyVersionFormat` workspace; `syncPackageManagerField` true |
| `node` | 1.0.4 | `version` 24.19.0 |
| `pnpm` | 1.1.0 | `version` 11.22.0 |
| `typescript` | 1.1.4 | `rootOptionsConfigFileName` tsconfig.options.json; `syncProjectReferences` true; `createMissingConfig` false; `routeOutDirToCache` true |

Rust and Python are commented reservations only (`rust.version` 1.95, `unstable_python.version` 3.13). Do not invent a second toolchain file.

`createMissingConfig: false` means issue 1 must write `packages/<name>/tsconfig.json` itself. Moon will not create it. `syncProjectReferences: true` means moon will rewrite root `tsconfig.json` `references` once members exist. `routeOutDirToCache: true` means moon will point each package `compilerOptions.outDir` at `.moon/cache`.

### `.moon/tasks/node.yml`

`inheritedBy.toolchains`: `javascript`. Every future JS/TS member inherits these tasks unless it sets `workspace.inheritedTasks` the way root does.

`fileGroups`:

- `sources`: `src/**/*`, `package.json`, `tsconfig.json`
- `tests`: `tests/**/*`, `**/*.test.ts`, `**/*.test.tsx`
- `configs`: `tsconfig.json`, `vite.config.*`, `vitest.config.*`

`tasks`:

| Task | `type` | Command | deps | options |
| --- | --- | --- | --- | --- |
| `typecheck` | `build` | `tsc --build --pretty` | `^:typecheck` | `runInCI: always` |
| `test` | `test` | `vitest run` | none | `runInCI: always`; `outputs`: `coverage` |
| `test-watch` | `run` | `vitest` | none | `cache: false`, `persistent: true`, `runInCI: false` |

Root does **not** run these. `moon.yml` `workspace.inheritedTasks.include: []` strips the tasks. Issue 1 is what first exercises `typecheck` and `test`. That is still true: nothing in the graph is named `*:typecheck` or `*:test` today (`moon query tasks` lists only `root:format`, `root:format-check`, `root:lint`, `root:lint-fix`).

Known moon fact, confirmed live: `include: []` does **not** stop fileGroup inheritance. `moon query projects` still merges `src/**/*`, `tests/**/*`, and `vite.config.*` into root `fileGroups` from `.moon/tasks/node.yml`. That is already filed as issue 13. Do not "fix" it inside wave 1.

### `moon.yml` (root)

`layer: application`. Comment in file: the root is a task holder, not a TypeScript project, so it must not inherit `.moon/tasks/node.yml`. That is why `workspace.inheritedTasks.include: []` is set.

Root `fileGroups.sources`: `.moon/**/*`, `apps/**/*`, `packages/**/*`, `services/**/*`, `scripts/**/*`, `package.json`, `pnpm-workspace.yaml`, `tsconfig.options.json`.

Root tasks (these are the only gates that run today):

| Task | `type` | Command | CI |
| --- | --- | --- | --- |
| `lint` | `test` | `oxlint --type-aware --deny-warnings --no-error-on-unmatched-pattern` | `runInCI: always` |
| `lint-fix` | `run` | `oxlint --type-aware --fix --no-error-on-unmatched-pattern` | `cache: false`, `runInCI: false` |
| `format-check` | `test` | `oxfmt --check --no-error-on-unmatched-pattern` | `runInCI: always` |
| `format` | `run` | `oxfmt --no-error-on-unmatched-pattern` | `cache: false`, `runInCI: false` |

Task `type` values are `build` \| `run` \| `test`. Gates are `test`. Mutating fixers are `run`. `just ci` / `moon ci` requested `root:format` and `root:lint-fix` then resolved them away, leaving `root:lint` and `root:format-check`. That classification is doing the job. Do not change it.

Commands live **inline** in this file. `javascript.inferTasksFromScripts` is false. Root `package.json` has no `scripts`. Issue 3's draft sentence "task logic lives in package.json scripts, never inline in moon config" is false of this repo. The established convention (handover, justfile comment, this file) is: moon owns the commands; the justfile aliases moon.

### `tsconfig.options.json`

Shared compiler options a new package must extend. `tsconfig.json` already `extends` this file.

Strictness a new package must satisfy (`compilerOptions`):

- `strict` true
- `noUncheckedIndexedAccess` true
- `exactOptionalPropertyTypes` true
- `noImplicitOverride` true
- `noImplicitReturns` true
- `noFallthroughCasesInSwitch` true
- `noPropertyAccessFromIndexSignature` true
- `useUnknownInCatchVariables` true
- `verbatimModuleSyntax` true
- `isolatedModules` true

Module/target: `target` ES2024, `lib` [ES2024], `module` preserve, `moduleResolution` bundler, `moduleDetection` force, `resolveJsonModule` true.

Emit: `composite` true, `declaration` true, `declarationMap` true, `sourceMap` true, `incremental` true. `tsc --build` already emits declarations under this config. Issue 1's `tsc --emitDeclarationOnly` is a possible extra command, not a missing compiler flag. Prefer proving `typecheck` (`tsc --build --pretty`) plus `routeOutDirToCache` before adding a second tsc invocation.

Also: `skipLibCheck` true, `esModuleInterop` true, `forceConsistentCasingInFileNames` true.

Root `tsconfig.json`: `files` [], `references` [], `compilerOptions.outDir` `.moon/cache/types`. Empty references is correct with zero members.

### `.oxlintrc.json`

Plugins: `typescript`, `unicorn`, `oxc`, `promise`, `import`.

Categories: `correctness` error, `suspicious` error, `perf` error, `pedantic` off.

Explicit rules, all severity `error` (none `warn`):

- `no-unused-vars` (vars all, args after-used, args/vars ignore `^_`, ignoreRestSiblings true, caughtErrors none)
- `typescript/consistent-type-imports` prefer type-imports
- `typescript/no-floating-promises`
- `typescript/no-misused-promises`
- `typescript/await-thenable`
- `typescript/no-explicit-any`
- `promise/prefer-await-to-then`
- `no-console` allow `warn` and `error` (this allowlist is the `console.warn` method, not oxlint warn severity)
- `eqeqeq` always, null ignore

`ignorePatterns`: `**/dist/**`, `**/build/**`, `**/coverage/**`, `**/node_modules/**`, `**/*.gen.*`, `**/_generated/**`.

Repo-wide grep for `warn`: only that `no-console` allowlist, plus `moon.yml` `tasks.lint` flag `--deny-warnings`. No oxlint severity `warn` exists.

### `.oxfmtrc.json` (constrains new code; not in the brief's list but it is the format contract)

`printWidth` 100, `singleQuote` false, `semi` true, `trailingComma` all, `arrowParens` always, `bracketSpacing` true, `endOfLine` lf, `quoteProps` as-needed, `sortImports` true, `sortPackageJson` true. `ignorePatterns`: `**/*.gen.*`, `**/_generated/**`, `pnpm-lock.yaml`.

### `package.json` + `pnpm-workspace.yaml`

Root `package.json` name `lilo-moon-template`, private, `type` module, version 0.0.0.

Exact pins (not catalog): `oxfmt` 0.64.0, `oxlint` 1.79.0, `oxlint-tsgolint` 7.0.2001. Catalog reference: `typescript` `catalog:` which resolves to 7.0.2 (`pnpm-lock.yaml` `importers.` / `catalogs.default.typescript`).

`engines`: node `>=24.19.0`, pnpm `>=11.22.0`. `packageManager`: `pnpm@11.22.0`.

`pnpm-workspace.yaml` `packages` globs already match the moon globs: `apps/*`, `packages/*`, `services/*`.

`catalog` (default):

- `@types/node` ^26.2.0
- `@types/react` ^19.2.18
- `@types/react-dom` ^19.2.4
- `@vitest/coverage-v8` ^4.1.11
- `react` ^19.2.8
- `react-dom` ^19.2.8
- `typescript` ~7.0.2
- `vite` ^8.2.1
- `vitest` ^4.1.11

Named catalog `catalogs.react-peer`: `react` `>=19`, `react-dom` `>=19`. Nothing consumes it yet. Issue 1's library should take React from `react-peer` if it has a React peer, not from the app pin.

Lockfile `oxlint@1.79.0` peer `oxlint-tsgolint: '>=7.0.2001'` is **optional**. That is why a missing tsgolint does not fail `pnpm install`. `--type-aware` is what needs the package at runtime. Pin stays exact 7.0.2001 (the version encodes TypeScript 7.0.2). Do not caret it.

`.npmrc`: `auto-install-peers=false`, `strict-peer-dependencies=true`, `resolution-mode=highest`. `pnpm-lock.yaml` `settings.autoInstallPeers` is true, which disagrees with `.npmrc`. Wave 1 should not "fix" the lockfile setting unless a gate requires it.

Vitest and Vite are catalog-only today. They are **not** root dependencies. Issue 1/2 must add them on the member via `"vitest": "catalog:"` / `"vite": "catalog:"`. Do not pin a second version. Do not add them to root unless a workspace-wide reason appears.

### `justfile`

`set shell := ["bash", "-cu"]`. Comment: aliases over moon; no task logic here.

| Recipe | Body |
| --- | --- |
| `default` | `check` |
| `check` | `moon run root:format root:lint-fix` then `moon check --all` |
| `ci` | `moon ci` |
| `setup` | `moon setup` |
| `clean` | `moon clean` |

There is no separate `fix`. Matches the established `just check` convention.

### Other config that constrains new files

`.editorconfig`: utf-8, lf, indent 2 spaces, final newline, trim trailing whitespace (disabled for `*.md`).

`.gitignore`: `node_modules/`, `.moon/cache/`, `.moon/docker/`, `dist/`, `build/`, `out/`, `coverage/`, `*.tsbuildinfo`, `.env*` with `!.env.example`, `.DS_Store`, `*.pem`.

### Reuse map (bind to these, do not reinvent)

- Reuse: `.moon/tasks/node.yml` `tasks.typecheck` / `tasks.test` / `tasks.test-watch` as the JS member task set. Issue 1 proves them; it does not replace them.
- Reuse: `moon.yml` `tasks.lint` / `tasks.format-check` as the repo-wide gates. New packages do not get their own oxlint task.
- Reuse: `pnpm-workspace.yaml` `catalog` for typescript, vitest, vite, react. New members use `catalog:` / `catalog:react-peer`.
- Reuse: `tsconfig.options.json` via `extends`. Moon `typescript.syncProjectReferences` owns root `references`.
- Reuse: `justfile` `check` / `ci`. Do not add npm scripts that duplicate them (`inferTasksFromScripts` is false).
- Existing infra: empty `packages/` directory plus glob `packages/*` already in both moon and pnpm. Issue 1 drops a member in; it does not change workspace globs.
- Existing infra: catalog already has `react`, `react-dom`, `vite`, `vitest`. Issue 2 naming `pnpm-workspace.yaml` as a touched file is likely a no-op.
- Similar checked and rejected: putting Vite `build`/`dev`/`preview` into `.moon/tasks/node.yml` (issue 2's stated home). That file is inherited by **every** javascript toolchain project, including the publishable library from issue 1. App tasks belong in `apps/<name>/moon.yml` or a new `.moon/tasks/` file inherited only by apps. `node.yml` stays library-safe (typecheck, test, test-watch).
- None found: AGENTS.md, GitHub workflow, apps tree, any TypeScript source, vitest installed in a member. Searches: `git ls-files`, `find` for `*.ts`/`*.tsx`/`*.js`, `moon query projects`, `gh issue view` 1-4.

### Quality map

- Duplication risk: issue 2's stated edit to `.moon/tasks/node.yml` would give the library Vite app tasks. Parallel task sets (library vs app) belong in two files, not one.
- Boundary: root `moon.yml` vs `.moon/tasks/node.yml`. Root is the workspace-wide lint/format holder. Members inherit node tasks. Keep that split.
- Vacuous gate: `root:lint` reports `Finished … on 0 files with 177 rules`. Format is real (`10 files`). Lint is not. Issue 1 is the first thing that can make type-aware lint execute.
- Issue 3 contract vs repo: if AGENTS.md is written to match issue 3's "scripts, never inline in moon config" bullet, the file will be false on day one. Write AGENTS.md to match `moon.yml` + `justfile` as they stand.
- Dead path: none. The reserved rust/python blocks are comments, not dead tasks.
- Grooming: refactor during issue 2 (app tasks not in `node.yml`). Defer fileGroup inheritance to issue 13. Defer lockfile `autoInstallPeers` mismatch.

## Gate Behaviour

Commands run on SHA `1cb4e41`, clean tree, no TypeScript sources.

### `moon check --all`

Exit **0**.

Tail:

```
root:format-check | All matched files use the correct format.
root:format-check | Finished in 5ms on 10 files using 12 threads.
        root:lint | Finished in 13ms on 0 files with 177 rules using 12 threads.
Tasks: 2 completed
```

Only `root:format-check` and `root:lint` ran. No `typecheck`, no `test`. `MOON_CHECK_EXIT=0`.

### `just ci` (`moon ci`)

Exit **0**.

`moon ci` reported base revision N/A, affected all, changed files `package.json`. Requested targets: `root:format`, `root:lint-fix`, `root:lint`, `root:format-check`. Resolved targets: `root:format-check`, `root:lint` (the two `type: test` tasks with `runInCI: always`).

Tail:

```
        root:lint | Finished in 3ms on 0 files with 177 rules using 12 threads.
root:format-check | All matched files use the correct format.
root:format-check | Finished in 5ms on 10 files using 12 threads.
Tasks: 2 completed
```

`JUST_CI_EXIT=0`. Tree still clean after both gates.

The 10 format files are the JSON/YAML tracked set oxfmt natively handles, minus ignored `pnpm-lock.yaml`: `.oxfmtrc.json`, `.oxlintrc.json`, `package.json`, `tsconfig.json`, `tsconfig.options.json`, `.moon/tasks/node.yml`, `.moon/toolchains.yml`, `.moon/workspace.yml`, `pnpm-workspace.yaml`, `moon.yml`. Justfile, editorconfig, gitignore, npmrc are not in that set.

### Does type-aware linting actually run?

**No. The lint gate passes vacuously.**

Evidence:

1. `root:lint` command is `oxlint --type-aware --deny-warnings --no-error-on-unmatched-pattern` (`moon.yml` `tasks.lint`).
2. Both `moon check --all` and `just ci` print `Finished … on 0 files with 177 rules`. `--debug=files` printed nothing.
3. Direct probes (read-only, same flags):
   - `--type-aware --deny-warnings --no-error-on-unmatched-pattern`: exit 0, 177 rules, 0 files.
   - same without `--type-aware`: exit 0, **152** rules, 0 files. The extra 25 rules prove `--type-aware` is honored and `oxlint-tsgolint` is loaded (`node_modules/.bin/tsgolint` exists, lockfile `oxlint@1.79.0(oxlint-tsgolint@7.0.2001)`).
   - `--type-aware --deny-warnings` **without** `--no-error-on-unmatched-pattern`: exit **1**, `No files found to lint.`
4. `--no-error-on-unmatched-pattern` is the flag that turns zero files into exit 0. `--type-aware` is the flag that loads tsgolint. `--deny-warnings` is inert when there are no diagnostics.
5. Type-aware rules in `.oxlintrc.json` (`typescript/no-floating-promises`, `typescript/no-misused-promises`, `typescript/await-thenable`) therefore never see a program.

A gate that passes on an empty repo has proven nothing. Issue 1's "deliberately breaking a type / test" rule, and issue 4's "a PR that introduces an unfixable lint error fails CI", are the first real proofs. Do not treat today's green as type-aware coverage.

## Issue Contract

| # | Goal | Files it will create or modify | Acceptance criteria (stated) | Wave-1 dependency |
| --- | --- | --- | --- | --- |
| 1 | Publishable library exemplar under `packages/`, first exercise of `typecheck` and `test` | **Create** `packages/**` (package.json with exports/types/files/publishConfig, tsconfig extending `tsconfig.options.json`, source, unit test). **Modify** `tsconfig.json` (moon-synced `references`). **Possibly modify** `.moon/tasks/node.yml`. Will also rewrite `pnpm-lock.yaml`. | `moon check --all` runs `typecheck` and `test` on the package and passes. `moon run <pkg>:typecheck` emits declarations to the routed cache outDir. Project references synced by moon. Deliberately breaking a type fails `typecheck`; deliberately breaking a test fails `test`. | None. First serial slice. |
| 2 | App exemplar under `apps/` plus proof that changing the library invalidates the app `build` cache | **Create** `apps/**`. **Modify** `.moon/tasks/node.yml` (as filed: add `build`, `dev`, `preview`). **Named** `pnpm-workspace.yaml` (globs and catalog already have `apps/*`, `vite`, `react`; likely no-op). Consumes #1 via `workspace:`. Will rewrite `tsconfig.json` `references` and `pnpm-lock.yaml`. | `moon run <app>:build` produces `dist/` and caches; second run is a cache hit. Changing the library invalidates the app `build` cache (explicit proof). `moon run <app>:dev` starts and is not cached. `moon check --all` stays green. Typed: `build` is `build`; `dev` and `preview` are `run` with `persistent: true` and `cache: false`. | **Depends on #1** (consumes that library). |
| 3 | Root `AGENTS.md` that is true of the repo as it stands | **Create** `AGENTS.md` only. | A fresh agent given only `AGENTS.md` can add a package and get it through `just check` without asking. Every claim is true of the repo as it actually stands. No aspirational rules. | File-independent. Truth-dependent on #1 (and ideally #2) so "how to add a member" describes a proven path, not a guess. Land after #1. |
| 4 | GitHub Actions `moon ci` plus required status check / branch protection on `main` | **Create** `.github/workflows/**`. Branch protection is a GitHub setting, not a tracked file. | A PR that breaks formatting fails CI. A PR that breaks a type fails CI. A PR that introduces an unfixable lint error fails CI. A PR touching only one project does not rerun the whole repo. Each verified by an actual PR, not by reading the workflow. | Needs #1 so a type/test/lint violation exists to prove. "One project" affected check is stronger after #2 (two members). |

Issue 1 notes: use `tsc --emitDeclarationOnly`, not bundler plugins, because declaration generation through bundlers was breaking on TS 7 RCs. Existing `typecheck` is already `tsc --build --pretty` with `declaration` true. Bind to that unless emitDeclarationOnly is added as an explicit extra.

Issue 2 notes: Vite 8, Rolldown default, React 19 from catalog. No router, no state library.

Issue 3 notes: must cover `just check` vs `just ci`, conventional commits, where task logic lives, no warn level, verification-against-violation, and how to add a workspace member.

Issue 4 notes: `moonrepo/setup-toolchain`, fetch-depth 0, PRs plus pushes to main. Do not cache moon hashes/output dirs. Depot / bazel-remote out of scope.

### Collision set (files two issues both touch)

This is the serial lock. Three files will be mutated by more than one wave-1 issue:

| File | Who writes it | Why |
| --- | --- | --- |
| `.moon/tasks/node.yml` | #1 "possibly"; #2 required as filed | Shared inherited task file. #2 adding `build`/`dev`/`preview` here also lands those tasks on the #1 library. |
| `tsconfig.json` | #1 named; #2 via `typescript.syncProjectReferences` | Root `references` array is moon-managed. Each new member rewrites it. |
| `pnpm-lock.yaml` | #1 and #2 (neither names it; both add a workspace member and catalog consumers) | One lockfile. Parallel installs will conflict. |

Non-colliding creates: `packages/**` (#1 only), `apps/**` (#2 only), `AGENTS.md` (#3 only), `.github/workflows/**` (#4 only).

`pnpm-workspace.yaml` is named only by #2. Current globs already include `apps/*` and `packages/*`. Treat it as a collision only if someone adds a new catalog entry; the catalog already has what #2 needs.

Semantic serial (not a file overlap): #2 consumes #1 via `workspace:`. #4's type-fail and single-project proofs need at least #1, preferably #2. #3's "true as it stands" rule means it should describe the exemplars after they exist.

Recommended order stays 1 → 2 → 3 → 4. For #2, put app tasks in the app's `moon.yml` (or an app-only inherited file) so `.moon/tasks/node.yml` stays a #1 collision only if issue 1 actually edits it.

### Decisions the plan must record

1. App tasks live in `apps/<name>/moon.yml`, not in `.moon/tasks/node.yml`. Deviate only with a written reason.
2. AGENTS.md describes moon-owned commands and justfile aliases, matching this tree. Do not copy issue 3's "package.json scripts, never inline in moon config" sentence unless moon.yml is first rewritten (that rewrite is not in wave 1's file lists).
3. Issue 1 proves `tasks.typecheck` as `tsc --build --pretty` with `routeOutDirToCache`. Add `emitDeclarationOnly` only if `tsc --build` does not satisfy the declaration acceptance line.
4. Every acceptance line is a deliberate violation, not a green `moon check` on the happy path. Today's lint gate is the cautionary case.
