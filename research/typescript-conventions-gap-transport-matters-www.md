---
title: TypeScript Conventions Gap Audit — transport-matters/www
type: research
tags: [typescript, conventions, audit, migration, monorepo, moon, pnpm, biome, vite, react, littleorgans, transport-matters]
summary: Section-by-section audit of transport-matters/www against typescript-conventions-2026, with a prioritized punch list for landing it as a catalog-strict Moon member in littleorgans.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-30
updated: 2026-05-30
---

# TypeScript Conventions Gap Audit — transport-matters/www

## Executive summary

`transport-matters/www` is a Vite + React 19 + TypeScript 5.9 SPA, ESM-only,
Biome-linted, Vitest + Playwright tested. It is already strict and clean on
most code-level conventions (no `any`, no non-null assertions, no default
exports, no barrel files, sole linter is Biome). The gaps are almost entirely
**integration-shaped**, not code-quality-shaped: it is a standalone pnpm
workspace with no catalogs, no Moon membership, an `@scope`-less package name,
and a build that writes into a sibling Python package. Two real code gaps:
the REST boundary in `src/api.ts` asserts `(await res.json()) as T` with no
schema validation, and the wire DTOs in `src/types.ts` are hand-mirrored
against Python Pydantic models (via `api/.../test_type_mirrors.py`) rather
than generated.

Backend reality check: www's backend is the **Python FastAPI** app at
`transport-matters/api` (Pydantic, `requires-python >=3.12`), not Rust. There
is no ts-rs anywhere. The "generated DTO" guidance applies by analogy, not
literally — see Rust-Generated Types section.

**Verdict tally: 14 COMPLIES · 9 GAP · 6 N/A** (section-level).

---

## Open questions (resolved)

**Lint stack.** Confirmed Biome, sole linter. `biome.json` present (v2.4.11
schema), `@biomejs/biome ^2.4.11` in devDeps, scripts `lint`/`format` call
`biome check`/`biome format`. No ESLint or Prettier config or dependency
exists anywhere. No overlapping-linter anti-pattern. COMPLIES.

**Catalogs + Moon membership.** Standalone today. `pnpm-workspace.yaml`
contains only `ignoredBuiltDependencies: [lefthook]` — no `packages:` members,
no `catalog:`/`catalogs:`, no `catalogMode`. Not a Moon project (no `moon.yml`,
not in any workspace `projects:` list). Has its own `pnpm-lock.yaml`,
`justfile`, `lefthook.yml`. Making it catalog-strict + Moon-managed is net-new
wiring (punch list §B).

**tsconfig delta.** Base flags mostly present in `tsconfig.app.json`: `strict`,
`noUncheckedIndexedAccess`, `noImplicitOverride`, `noFallthroughCasesInSwitch`,
`isolatedModules`, `verbatimModuleSyntax`, `moduleResolution: bundler`,
`skipLibCheck`. **Missing vs baseline:** `exactOptionalPropertyTypes`,
`module: preserve` (currently `ESNext`), `target` is `ES2022` (baseline
`es2023`), `lib` lacks `es2023` on the node config, and there is no shared
`tsconfig.base.json` to inherit from. App config also lacks `declaration`/
`declarationMap`/`sourceMap` (acceptable — it is a `noEmit` app, not a library).

**ESM-only / Node.** ESM-only confirmed: `"type": "module"`, no `require`/
`__dirname` in src. **Node baseline is behind:** `"engines": { "node":
">=20.19.0" }` and `@types/node ^25`; the guide mandates `>=24`. Bump to `>=24`.

**Rust-generated types.** None. Wire DTOs (`src/types.ts`, snake_case:
`input_tokens`, `system_parts`) are hand-written and kept in lockstep with
**Python Pydantic** models by an AST-diff test on the Python side
(`api/src/transport_matters/test_type_mirrors.py`, which parses `www/src/
types.ts`). If/when a Rust service enters, generated DTOs would land in a
`packages/*-core` re-export package; today the equivalent is the Python mirror
test. GAP-by-analogy: the mirror test is brittle string parsing, not codegen.

**Error handling.** Raw `throw` (10 sites in src). No neverthrow, no Effect,
no `Result<T,E>`. The REST layer throws `new Error(message)` from
`requestJson`/`throwWithDetail` (`src/api.ts:58-86`) and surfaces via
TanStack Query error state. The SSE boundary instead uses hand-written type
guards (`isValid*Event`, `src/hooks/exchangeStreamEvents.ts:14-127`). Baseline
for a React app at this size implies pattern #1 (typed `Result` via neverthrow)
**only if** the team wants typed errors at the data layer; for a thin SPA over
TanStack Query, raw throw routed to Query error boundaries is defensible. Treat
as P2 / human decision, not a blocker.

---

## Section-by-section verdicts

| Guide section | Verdict | Evidence |
|---|---|---|
| Agent Rules | COMPLIES | No `any`, searchable code, no dup paths observed. |
| Project Shape | GAP | Standalone repo, not a leaf under `apps/`. Package name `transport-matters` is unscoped (needs `@littleorgans/*` or app `private` name). No `tsconfig.base.json`. |
| pnpm Workspaces, Catalogs, Moon | GAP | No catalogs, no `catalogMode: strict`, no Moon `moon.yml`, no `syncProjectReferences`. Standalone `pnpm-lock.yaml`. |
| Package Manifest & Exports | PARTIAL/GAP | `"type": "module"` ✓, `"private": true` ✓. `"engines": ">=20.19.0"` should be `>=24`. App needs no `exports` map (correct — it is an app). |
| tsconfig Strictness | GAP | Missing `exactOptionalPropertyTypes`, `module: preserve`, `target es2023`; no shared base config. Rest present. |
| TS Version / Target / Node | PARTIAL/GAP | TS `^5.9.3` ✓. `target ES2022` (want es2023). Node `>=20.19` (want `>=24`). ESM-only ✓. |
| Modules and Files | COMPLIES | Named exports only (0 default exports in src), no barrel `index.ts`, largest src file `types.ts` 586 LOC < 700 cap. |
| API and Type Design | COMPLIES | Discriminated unions present; snake_case DTOs are interfaces; no `any`. `as` casts (72) are the one smell — see Detailed. |
| Runtime Validation & Schema | GAP | REST boundary uses `(await res.json()) as T` (`src/api.ts:86`), no schema parse. SSE boundary validated by hand-guards. No zod/valibot. |
| Rust-Generated TS Types | N/A (Python) / GAP-by-analogy | No Rust, no ts-rs. DTOs hand-mirrored to Pydantic via `test_type_mirrors.py` AST diff. |
| Error Handling | GAP (mild) | Raw `throw`; no neverthrow/Effect/Result. Acceptable for SPA-over-TanStack-Query; decide on adopt. |
| Async and Concurrency | COMPLIES | `async/await`, no obvious floating promises (`void` used on fire-and-forget invalidations, `exchangeStreamEvents.ts:249`). |
| Dependencies | PARTIAL | All ESM-native, ship own types. But versions are inline-pinned (no catalog yet). `diff ^9` is the only non-obvious dep. |
| Logging and Diagnostics | N/A | Browser SPA; no library-logger requirement. `console.*` audit deferred. |
| Lints and Formatting | COMPLIES | Biome sole linter+formatter, `noExplicitAny: warn`, `noNonNullAssertion: warn`, `useExhaustiveDependencies: warn`. tsc is a separate gate (`typecheck` script). |
| Type-Safety Escape Hatches | PARTIAL | 5 `as unknown as` (3 test-setup, 2 in `InspectTab.tsx:250-251` casting `request_ir`). 72 `as` casts overall — reviewable but not blocking. |
| Testing | COMPLIES | Vitest (no Jest), co-located `*.test.ts(x)`, Playwright e2e+visual, `test-setup.ts` shim, boundary/error tests present (`useExchangeStream.validation.test.tsx`). |
| Documentation | N/A | App, not a published library; no TSDoc-on-exports obligation. |
| Build and Bundling | PARTIAL/GAP | Vite for the app ✓; `tsc -b` type gate ✓. But `build.outDir` writes into `../api/src/transport_matters/www` (couples build to Python sibling). Moon must own caching with declared inputs/outputs. |
| CI | GAP | Local `ci` script (`pnpm lint && typecheck && test && build`) but not wired to Moon affected/merge gates; no `--frozen-lockfile`; no changesets config (`.changeset/` absent though CLI is installed). |
| Performance | COMPLIES | ESM, no deep barrels, `import type` used in `api.ts:1`. |
| Metaprogramming | COMPLIES | No decorators, no `Proxy`, no `experimentalDecorators`. |
| Anti-Patterns | MOSTLY CLEAR | Clear of: `any`, default exports, barrels, two linters, CJS deps. Present: inline-pinned versions (pre-catalog), `as unknown as` x5. |

---

## Detailed findings (evidence)

1. **REST boundary is unvalidated.** `src/api.ts:86` `return (await res.json())
   as T;` and `:60` `const data = (await res.json()) as { detail?: string };`.
   Every REST response is trusted by assertion. The SSE path is the
   counterexample done right (`src/hooks/exchangeStreamEvents.ts:14-127`,
   `isValid*Event` guards narrowing `Record<string, unknown>`). Gap is the
   inconsistency: stream validated, REST not.

2. **DTOs hand-mirrored to Python.** `src/types.ts` (586 LOC) is the canonical
   wire shape, enforced against Pydantic by
   `api/src/transport_matters/test_type_mirrors.py` (parses `types.ts` with a
   regex/AST diff). Brittle: a rename on either side breaks a string matcher,
   not a type. No codegen (ts-rs N/A — backend is Python).

3. **`as` casts (72 in src, non-test).** Concentrated in
   `components/detail/InspectTab.tsx` (8), `ExchangeDetail.tsx` (5),
   `editor/DismissablePanel.tsx` (5). Two `as unknown as` at
   `InspectTab.tsx:250-251` cast `detail.request_ir` to `InternalRequest`.
   These are review-visible, Biome catches new `any` but not `as`. Not a
   blocker; tighten opportunistically.

4. **Build couples to Python sibling.** `vite.config.ts` `build.outDir:
   "../api/src/transport_matters/www"`, `emptyOutDir: true`. In the monorepo
   this relative escape breaks; the app must build to its own `dist/` and the
   Python serving path (if still needed) becomes a copy/packaging step, or the
   coupling is dropped.

5. **Version source-of-truth is a git-describe shell-out.** `vite.config.ts
   resolveVersion()` runs `git describe`. Under atomic monorepo releases the
   version comes from the family tag (`v0.8.0`); this shell-out should read the
   monorepo version, not a per-repo tag.

6. **No `tsconfig.base.json`.** Three configs (`tsconfig.json` solution,
   `tsconfig.app.json`, `tsconfig.node.json`) duplicate flags. Baseline wants
   one root base inherited by per-package overrides.

---

## (a) Prioritized punch list

**P0 — blockers to landing as a Moon member**
- [ ] Add a `moon.yml` to the app and register it in the workspace
      `projects:` (or glob). Inherit `build`/`test`/`lint`/`typecheck` tasks;
      do not redefine per-project.
- [ ] Create root `pnpm-workspace.yaml` member entry (the monorepo currently
      has none) and move www under `apps/transport-matters-www/` (or chosen
      name). Delete www's standalone `pnpm-lock.yaml`; the workspace owns one.
- [ ] Introduce pnpm catalogs and set `catalogMode: strict`; move every
      third-party version (react, react-dom, @tanstack/*, zustand, vite,
      vitest, biome, tailwind, playwright, typescript) to `catalog:`.
- [ ] Decide the package name: `@littleorgans/transport-matters-www` (scoped,
      `private: true`) and rename folder to match unscoped name.
- [ ] Fix `build.outDir`: build to local `dist/`; drop or relocate the
      `../api/...` write (it escapes the package and breaks in-repo).

**P1 — convention conformance**
- [ ] Add `exactOptionalPropertyTypes: true` to the shared base; fix fallout.
- [ ] Set `module: "preserve"`, `target: "es2023"` in the base.
- [ ] Extract `tsconfig.base.json` at monorepo root; have app/node configs
      inherit and override only `paths`/`rootDir`/`outDir`/`composite`.
- [ ] Bump `"engines.node"` to `>=24`; align `@types/node` to the Node 24 line.
- [ ] Enable Moon `typescript.syncProjectReferences`.
- [ ] Validate the REST boundary: introduce a schema (zod v4 from catalog) or
      promote the existing hand-guard pattern to cover `api.ts` responses;
      remove `(await res.json()) as T`.

**P2 — quality / decisions**
- [ ] Replace the brittle `test_type_mirrors.py` string-diff with a real
      contract: generate `types.ts` DTOs from Pydantic (e.g.
      `pydantic2ts`/OpenAPI), or move the canonical schema to one side. Human
      decision (which side owns the wire type).
- [ ] Decide error-handling stance: keep raw `throw` → TanStack Query error
      state (status quo), or adopt neverthrow `Result` at the api layer.
- [ ] Reduce `as` / `as unknown as` (InspectTab.tsx:250-251) via guards.
- [ ] Add `.changeset/config.json` (CLI already installed) or remove the CLI
      if releases are driven purely by the monorepo atomic tag.

---

## (b) Moon / pnpm-catalog wiring steps

1. **Workspace root.** Add/extend `pnpm-workspace.yaml` at
   `littleorgans/littleorgans/`:
   ```yaml
   packages:
     - "apps/*"
     - "packages/*"
   catalogMode: strict
   catalog:
     react: "19.2.5"
     react-dom: "19.2.5"
     typescript: "5.9.3"
     vite: "8.0.8"
     vitest: "4.1.4"
     "@biomejs/biome": "2.4.11"
   catalogs:
     tanstack:
       "@tanstack/react-query": "5.97.0"
       "@tanstack/react-virtual": "3.13.23"
   ```
2. **App manifest.** Rewrite member deps to `"react": "catalog:"`,
   `"@tanstack/react-query": "catalog:tanstack"`, etc. Set name
   `@littleorgans/transport-matters-www`, `"private": true`,
   `"engines.node": ">=24"`.
3. **Moon project.** Add `apps/transport-matters-www/moon.yml`:
   `language: "typescript"`, `type: "application"`, inheriting tasks from a
   root TS tag/preset (build → `vite build`, typecheck → `tsc -b`, lint →
   `biome check .`, test → `vitest run`). Declare `outputs: ["dist/**"]` so
   Moon caches soundly.
4. **Moon toolchain.** In `.moon/toolchains.yml` enable the `typescript`
   toolchain with `syncProjectReferences: true` and pnpm as the package
   manager; in `.moon/workspace.yml` add the `apps/*` / `packages/*` projects
   glob.
5. **tsconfig base.** Add root `tsconfig.base.json` with the 2026 flag set;
   point app/node configs at it via `extends`.
6. **CI gate.** Root `moon ci` (already the Rust gate) gains the TS project;
   install with `--frozen-lockfile`; merge gate runs typecheck + lint +
   format-check + build + test full-workspace, affected runs for inner loop.

## (c) Human decisions required

- **Package name + scope.** `@littleorgans/transport-matters-www` vs a
  `lilo-`/brand-aligned name (direction doc keeps the project name internal;
  user-visible names use littleorgans/`lilo`).
- **Wire-type ownership.** Python Pydantic stays canonical with generated TS
  DTOs, or the type contract moves. Affects whether `test_type_mirrors.py`
  survives or is replaced by codegen.
- **Backend coupling.** Whether www keeps serving from the Python package
  (`api/src/transport_matters/www`) post-migration, or the api is itself pulled
  into the monorepo `python/` tree. Today transport-matters is declared
  **external/out-of-scope** for v0.8.0 (root CLAUDE.md "Bounded contexts"); this
  audit assumes a later phase pulls it in.
- **Error-handling paradigm.** Adopt neverthrow at the data layer or keep raw
  throw → TanStack Query.

## Open questions

- Is transport-matters/www actually slated for v0.8.0, or a later phase? Root
  CLAUDE.md marks transport as external and out of monorepo scope now.
- If the Python api migrates too, the `outDir` coupling and version shell-out
  resolve naturally; if not, www needs a clean `dist/` and a packaging bridge.
