---
title: TypeScript Conventions for Agents, 2026
type: research
tags: [typescript, conventions, monorepo, pnpm, moon, tsconfig, esm, biome, oxlint, vitest, effect, ts-rs, branded-types, build]
summary: Condensed operating instructions for agents writing, editing, and reviewing modern TypeScript in an ESM-only, strict, Rust-primary monorepo.
status: active
confidence: high
created: 2026-05-30
updated: 2026-05-30
---
# TypeScript Conventions for Agents, 2026
This file is an instruction guide, not a survey.
Use it when creating, editing, reviewing, or planning TypeScript code.
Prefer the project conventions in front of you when they are explicit.
Use this guide when the repo is silent, inconsistent, or newly scaffolded.
If a local `AGENTS.md`, `CLAUDE.md`, issue body, or design record conflicts
with this file, follow the local source of truth.

This guide is shell-agnostic. It governs the web frontend and any desktop
renderer/main process regardless of whether the shell is Electron or Tauri.
Shell-specific rules (IPC, native bridges, packaging) live elsewhere.

## Agent Rules
Validate before acting.
Read the existing package shape before adding code.
Search before creating helpers, types, interfaces, constants, or files.
Do not introduce duplicate paths for the same behavior.
Delete old paths during refactors unless a staged migration is explicit.
Keep public API (package `exports`) changes deliberate and easy to review.
Keep private implementation changes boring.
Do not expand scope because a pattern looks convenient.
Run the repo's documented checks before claiming done.
If no documented checks exist, run typecheck, lint, format, build, and tests.
Prefer the project's pinned TypeScript and Node versions.
Do not add dependencies casually.
Do not reach for `any`. Reach for `unknown` and narrow.
Do not add a wrapper, abstraction, or generic until a second caller needs it.
Do not hand roll streams, schedulers, retries, or parsers when the project
already has a proven local abstraction.
Treat generated files as read-only outputs; edit the generator source instead.
Write comments only where they prevent real confusion.

## Project Shape
Use a monorepo for any product likely to grow beyond one artifact.
The Helioy target is a Rust-primary Moon monorepo with `packages/` and `apps/`.
TypeScript surfaces are leaf members inside that repo, not a separate repo.
Use pnpm workspaces. pnpm + workspaces is the 2026 default for multi-package
TS projects, and Moon installs and syncs `node_modules` per project.
Put shippable surfaces (web app, desktop renderer) under `apps/`.
Put reusable libraries (shared types, ui, domain logic) under `packages/`.
Keep package directories flat unless a target layout is already locked.
Folder name should match the unscoped package name.
Use kebab case for package names.
Scope internal packages under one npm scope (for example `@littleorgans/*`).
Mark non-published packages with `"private": true`.
Common package suffixes mirror the Rust side where it aids navigation:
- `-core` for domain types and pure logic.
- `-ui` for shared React components.
- `-client` for generated or hand-written API clients.
- `-config` for shared tsconfig, biome, and build presets.
- `-testing` for test helpers and fixtures.
Keep one `tsconfig.base.json` (or a `-config` package) at the root as the
single source of truth for compiler options.

## pnpm Workspaces, Catalogs, and Moon
Declare members in `pnpm-workspace.yaml`.
Use `workspace:*` (or `workspace:^`) for internal package references so the
local source is always linked, never a registry copy.
Use pnpm catalogs for third-party version unification. Define each shared
dependency once under `catalog:`/`catalogs:` in `pnpm-workspace.yaml` and
reference it as `"react": "catalog:"` in member manifests.
Set `catalogMode: strict` so adding an out-of-catalog version errors. This is
the lockfile-for-versions discipline; it stops silent version drift across
packages.
Group catalogs by concern when the tree is large (a `react19` catalog, a
`build` catalog), not one entry per package.
In CI, always install with `--frozen-lockfile`. It fails when `package.json`,
catalog entries, or the lockfile have drifted out of sync.
Let Moon own task orchestration and caching. Define a task once in the root
or a tag config and let projects inherit it; do not redefine `build`, `test`,
`lint` in every `moon.yml`.
Enable `typescript.syncProjectReferences` in Moon so the TS project-reference
graph stays in sync with the Moon project graph automatically.
Use Moon's affected/incremental runs for the inner loop; keep one
full-workspace gate for merge and CI so correctness never depends on the
affected heuristic. This mirrors the Rust two-gate pattern.

## Package Manifest and Exports
Every package is ESM. Set `"type": "module"`.
Define the public surface with the `exports` map, not `main`/`module`.
Point `exports` at built `.js` plus `.d.ts`; add `"types"` conditions first.
Set `"sideEffects": false` on pure library packages to unlock tree-shaking.
Set `"engines": { "node": ">=24" }` to match the LTS baseline.
Use `"private": true` for apps and any package not meant for a registry.
For dual ESM/CJS, prefer ESM-only: Node 23+ can `require()` an ESM package,
so a separate CJS build is usually unnecessary in 2026. Ship CJS only when a
known consumer cannot load ESM.
Keep entry points few and intentional. Each `exports` subpath is API surface.

## tsconfig: 2026 Strictness Baseline
Inherit from one `tsconfig.base.json`. Per-package configs only override paths,
`rootDir`, `outDir`, `composite`, and references.
Non-negotiable compiler flags for 2026:
```jsonc
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "moduleResolution": "bundler",
    "module": "preserve",
    "target": "es2023",
    "lib": ["es2023", "dom", "dom.iterable"],
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  }
}
```
`strict` alone is not enough. `noUncheckedIndexedAccess` and
`exactOptionalPropertyTypes` catch real bugs and are expected in strict 2026
codebases (the mdcontext review treats both as the bar to clear).
`verbatimModuleSyntax: true` forces explicit `import type` / `export type`.
It is mandatory under ESM-only because it makes elision deterministic and
keeps type-only imports out of the emitted JS.
`moduleResolution: "bundler"` is correct for Vite/bundled apps and libraries
built by a bundler. Use `"nodenext"` only for packages executed directly by
Node with no bundler (a CLI, a Node service); those require explicit `.js`
import extensions.
`isolatedModules: true` keeps the code compatible with single-file transpilers
(esbuild, Oxc, swc) that every fast toolchain uses.
`skipLibCheck: true` is pragmatic but it hides errors in dependency `.d.ts`
files; note this when a dependency's types are suspect.
For library packages set `"composite": true` and use project references.
Run type checking with `tsc --noEmit` (or `tsc --build` for references) as a
gate separate from the bundler; bundlers transpile without full type checking.

## TypeScript Version, Compiler, and Target
Track the TS 5.9.x line as the stable baseline; `tsc --init` in 5.9 emits a
trimmed, opinionated config that matches the flags above.
TypeScript 7 (the Go-based native compiler, `tsgo` / `@typescript/native-port`)
is in public beta as of April 2026 with ~10x faster builds and type checking
that is structurally identical to TS 6.0. Treat it as opt-in for fast local
checks and CI acceleration; keep `tsc` as the authoritative gate until the
project explicitly migrates. Do not depend on tsgo-only behavior.
Compile target `es2023` is safe for Node 24 and current browsers. Do not
downlevel further without a stated support requirement.
ESM-only. No `require`, no `__dirname`/`__filename` (use `import.meta.url`),
no CommonJS interop hacks in new code.
Node 24 is the LTS baseline. Node 24 enforces stricter ESM resolution; honor
explicit extensions where the resolution mode requires them.

## Modules and Files
One module = one cohesive responsibility, not one type per file.
Use named exports. Avoid default exports except where a framework demands them
(a route component, a config file).
Avoid barrel (`index.ts`) re-export files that re-export everything. They
defeat tree-shaking, slow the compiler, and create the export-shadowing
problem the mdcontext review documents (the same name exported from three
files). A package's single public `index.ts` mapped through `exports` is fine;
deep internal barrels are not.
Each public type has exactly one canonical definition. If two modules need the
same shape, extract it to a shared `-core`/types module and import it.
Use `import type` for type-only imports (enforced by `verbatimModuleSyntax`).
Keep new files under the repo line limit; treat 700 lines as a hard stop and
~150 lines as a function-length warning, matching the Helioy thresholds.

## API and Type Design
No `any` in new code. Use `unknown` at boundaries and narrow with a guard,
a discriminated check, or a schema parse.
When an escape hatch is unavoidable, make it named and greppable. The
VoltAgent `DangerouslyAllowAny = any` alias is the pattern: a single named type
that code review and lint can audit, instead of scattered bare `any`.
Prefer `interface` for object shapes that may be extended or implemented;
prefer `type` for unions, intersections, mapped, and conditional types.
Model closed sets as discriminated unions with a literal `kind`/`type` tag,
not boolean flags or optional fields. The mdcontext review's recurring fix is
"replace the untyped success/error blob with a discriminated `ToolResult`."
Use branded/nominal types for primitives with domain meaning (an `EntryId`, a
`ScopePath`), so a raw `string` cannot be passed where a validated one is
required:
```ts
type Brand<T, B> = T & { readonly __brand: B };
type UserId = Brand<string, "UserId">;
```
Use `satisfies` to validate a literal against a type while keeping its narrow
inferred type; prefer it over `as`, which silently discards checking.
Use `as const` for literal tuples and config objects; prefer `const` type
parameters over manual `as const` at call sites where supported.
Start with concrete parameter types. Add generics only when a second caller
needs the flexibility; gratuitous generics leak implementation detail and
slow the compiler.
Make readonly the default for data that should not mutate (`readonly` fields,
`ReadonlyArray`, `as const`).

## Runtime Validation and Schema
Validate all external input (network, env, disk, IPC, user) at the boundary.
Types are compile-time only; never trust unparsed `unknown`.
Default to Zod (v4) for general schema validation: it is the 2026 default for
Node APIs, tRPC, and form schemas, and v4 is ~4x faster than v3.
Use Valibot when bundle size dominates (client-side forms, edge functions):
sub-1KB schemas via its modular, tree-shakeable API.
When the project standardizes on Effect, use Effect Schema for data modeling:
it gives two-way encode/decode transformations and integrates with Effect's
error channel, replacing Zod inside Effect code.
Prefer libraries that implement the Standard Schema interface (Zod, Valibot,
ArkType, Effect Schema all do). Standard Schema lets framework code accept any
validator without lock-in, and tRPC, TanStack Form/Router consume it directly.
Derive the static type from the schema (`z.infer`, `Schema.Type`); do not hand
write a parallel interface that can drift from the validator.

## Rust-Generated TypeScript Types
The monorepo is Rust-primary. Wire-facing types (anything serialized across
the Rust/TS boundary) should be generated from the Rust source of truth, not
hand-written on the TS side. Hand-written and generated types coexist by role:
- Generated: DTOs, request/response shapes, enums, and any struct that crosses
  the boundary. ts-rs is the default generator (v12.x, derive macro, emits
  `.ts` at `cargo test` time; serde-attribute aware). See
  `ts-rs-rust-typescript-type-generation-2026.md` for the full assessment and
  `ts-rs-alternatives-rust-typescript-types.md` for when to pick specta,
  typeshare, schemas, or OpenAPI instead.
- Hand-written: UI-only types, view models, component props, and any TS shape
  with no Rust counterpart.
Rules for generated types:
- Treat the generated directory as read-only build output. Never edit it.
  Editing the Rust struct (or its `#[ts(...)]` attribute) is the only correct
  change.
- Pin the generated output to one workspace directory via `TS_RS_EXPORT_DIR`
  in the workspace `.cargo/config.toml` with `relative = true`, so all crates
  export to one place and cross-type imports resolve.
- Set `TS_RS_IMPORT_EXTENSION=.js` (or the `import-esm` feature) when the TS
  side uses `nodenext`/explicit-extension ESM imports.
- Re-export generated types through a single `-core`/`-client` package so app
  code imports from a stable path, not from the raw generated folder.
- Gate drift in CI: run the generator, then `git diff --exit-code` the output
  directory to fail when committed types are stale.
- Wrap or brand generated primitives on the TS side when domain invariants
  matter (a generated `string` id re-branded as `UserId` at the client edge).

## Error Handling
Two disciplined patterns; pick one per package and stay consistent.
1. Plain TypeScript with a `Result` type. Use neverthrow for typed errors in
   otherwise-idiomatic code: it adds value per-function and is the right choice
   for existing or mixed codebases. Return `Result<T, E>`; reserve `throw` for
   truly exceptional, unrecoverable cases.
2. Effect, when the project has adopted it system-wide. Effect's payoff comes
   from end-to-end adoption (typed error channel, dependency injection,
   observability); it is a large commitment, justified for greenfield surfaces
   that buy into the whole runtime. mdcontext uses Effect with `Data.TaggedError`
   and `_tag`-discriminated error unions and codes; follow that shape there.
Do not mix paradigms within one package without reason.
Whichever you pick: errors are typed and matchable at library boundaries, and
converted to user-facing diagnostics only at the edge (the HTTP handler, the
CLI print, the UI toast).
Anti-patterns to avoid (all drawn from the mdcontext review):
- Collapsing a typed error channel into an untyped success blob, then doing a
  runtime `"error" in result` check and casting it back. Use a discriminated
  union result instead.
- `Effect.promise` for fallible I/O (it makes rejections untyped defects); use
  `Effect.tryPromise` with a typed `catch`.
- Swallowing file/network errors into `null`/`continue` with no log; at minimum
  `logWarning` and continue explicitly.
- `console.warn` inside an Effect pipeline; use the Effect logging layer.
- `new RegExp(userInput)` unguarded; it throws an untyped `SyntaxError`.

## Async and Concurrency
Use `async`/`await`; never leave a promise floating (lint for it).
Pass `AbortSignal` through cancellable async APIs; wire it to the platform
abort source (request abort, component unmount, IPC cancel).
Bound concurrency for fan-out work (`p-limit`, `Promise.allSettled` with a
pool, or Effect's `concurrency` option). Unbounded `Promise.all` over a large
list is a resource hazard.
Prefer `Promise.allSettled` when partial failure is acceptable and you need
every result; `Promise.all` when any failure should abort.
Use `using`/`await using` (explicit resource management, stable in TS 5.2+) for
resources with deterministic cleanup (file handles, DB connections, locks),
instead of manual `try/finally`.
Do not hand roll retry, timeout, debounce, or backoff when a vetted utility or
the project's Effect schedule already covers it.

## Dependencies
Before adding a dependency, check:
- Is there already a local helper or an existing catalog entry?
- Is it ESM-native? Avoid CJS-only packages in an ESM-only repo.
- Does it ship its own `.d.ts`, or require a separate `@types/*`?
- Bundle-size and tree-shakeability for anything reaching the browser.
- Maintenance and release cadence.
All shared third-party versions go through the pnpm catalog. Do not pin a
version inline in a member `package.json` when the catalog owns it.
Reasonable 2026 defaults when the repo has not chosen otherwise:
- Validation: `zod` (v4); `valibot` for client bundles; Effect Schema in
  Effect code.
- Result/errors: `neverthrow`, or Effect when adopted.
- Dates: `date-fns` or `Temporal` polyfill; avoid `moment`.
- HTTP: native `fetch`.
- Test: `vitest`.
- IDs: `nanoid` or `crypto.randomUUID()`.

## Logging and Diagnostics
Use one structured logger interface defined once and consumed everywhere (the
VoltAgent `Logger` shape: leveled methods plus `child(bindings)` is a good
template). Do not scatter `console.log` through library code.
Log structured fields, not interpolated strings: `logger.info("session start",
{ sessionId })`, not a formatted message.
Libraries should accept a logger or stay silent; the app owns logger setup and
transport. Keep machine-readable output separate from human output.

## Lints and Formatting
The 2026 landscape has three credible stacks. Pick one per repo:
- Biome (v2.3+, ~423 rules, formatter + linter in one Rust binary, type-aware
  rules and GritQL plugins since v2.0). Best default for new projects: one
  tool, one config, 10-25x faster than ESLint, formatter near-identical to
  Prettier. The Helioy `www` surface already uses Biome.
- oxlint (Oxc, v1.0 stable Aug 2025, 520+ rules, 50-100x faster, used by
  Shopify/Airbnb at scale; JS-plugin and type-aware `tsgolint` support
  maturing through 2026). Best as a blazing-fast lint-only gate, often paired
  with a separate formatter.
- ESLint + Prettier + `@typescript-eslint`. Still the safest choice when you
  depend on type-aware rules at full breadth, framework plugins
  (`eslint-plugin-react-hooks`), or custom rules the faster tools do not yet
  cover.
Recommendation: default to Biome for new TypeScript surfaces (it is already in
this stack). Keep ESLint only where a required type-aware or framework rule has
no Biome/oxlint equivalent. Do not run two overlapping linters by default.
Whatever the choice: lint and format run in CI with warnings treated as errors,
and the type checker (`tsc --noEmit`) is a separate gate from the linter.
Enforce `import type` usage, no-floating-promises, no-explicit-any, and
exhaustive-switch through the chosen linter.

## Type-Safety Escape Hatches
`any`: forbidden in new code. If genuinely required, use the named
`DangerouslyAllowAny` alias so it is greppable and review-visible.
`as` casts: a smell. Each one is an unchecked assertion. Prefer a type guard,
a discriminated narrow, `satisfies`, or a schema parse. Never chain
`as unknown as T` except at a hard external boundary, and comment why.
Non-null `!`: acceptable only where an invariant guarantees non-null and a
comment or adjacent check makes it obvious; do not sprinkle to silence the
compiler.
`@ts-expect-error` over `@ts-ignore` (it fails when the error disappears), with
a one-line reason. Never `@ts-nocheck` a file in new code.
Treat every escape hatch as a reviewable decision, not a default.

## Testing
Vitest is the 2026 default and is already in this repo. It gives native ESM,
TypeScript, and JSX via Oxc/esbuild with no shim, plus built-in v8/istanbul
coverage. Do not introduce Jest into a Vitest repo.
Co-locate unit tests as `*.test.ts` next to the source, or under `tests/` for
integration; follow the existing repo layout.
Use a `tsconfig.test.json` (the desktop surface already does) so test-only
types do not leak into the build config.
Test behavior through the public API, not private fields. The mdcontext review
flags private-field access via `as unknown as {...}` as brittle; prefer
constructor injection so the unit is testable without casts.
Cover boundary and error cases, not just the happy path (empty input, at-budget
boundaries, invalid options that throw) — the review's standing gap.
Use Vitest snapshots where output-shape stability matters.
Validate both human and machine output surfaces when a tool emits both.

## Documentation
Public package exports are API surface; document exported types and functions
with TSDoc where they are meant for external consumers.
Keep README examples in sync with the actual exported API.
For generated types, document the generator and regeneration command, not the
output. Never write prose into a generated file.
Do not add marketing prose where a usage example belongs.

## Build and Bundling
Separate type checking from bundling. `tsc --noEmit` (or `tsc --build` for
project references) is the type gate; the bundler produces JS.
For libraries, prefer tsdown (Rolldown-based, the tsup successor Evan You
signals as the long-term path; emits and bundles `.d.ts`, 3-10x faster, Vite/
Rollup plugin compatible). tsup remains a safe, larger-community choice; both
are acceptable. unbuild fits UnJS/Nuxt projects.
For applications, use Vite. App `dev`/`build` go through Vite's pipeline; the
desktop renderer builds the same way regardless of shell.
Emit `.d.ts` and declaration maps for every published package.
Use `tsc --build` with `composite` project references across internal packages
so incremental builds only recompile changed packages and their dependents.
Let Moon cache build outputs; declare task inputs/outputs so caching is sound.

## CI
Inner loop: Moon affected runs (typecheck, lint, test) on changed projects
plus dependents.
Merge gate (unconditional, full workspace): install `--frozen-lockfile`,
typecheck, lint, format check, build, test, and the Rust-type drift check
(`git diff --exit-code` on the generated TS directory).
Use changesets for versioning and changelogs of published packages; the
changesets GitHub Action opens version PRs and publishes on merge. This is the
2026 standard for pnpm monorepo releases.
Cache the pnpm store and Moon's cache in CI.

## Performance
Clarity first; measure before optimizing.
For browser surfaces: ship ESM, set `"sideEffects": false`, avoid deep barrels,
and prefer tree-shakeable libraries (Valibot over Zod where bytes matter).
Keep generic depth and conditional-type complexity in check; pathological types
slow the compiler and the editor. The TS 7 native compiler mitigates but does
not excuse gratuitous type-level computation.
Use `import type` aggressively so type-only graph nodes never reach the bundle.
Lazy-load heavy, rarely-used modules with dynamic `import()`.

## Metaprogramming
Decorators: use the stage-3 standard decorators (stable, no
`experimentalDecorators`) only where a framework requires them. Do not build
core logic on decorators.
Codegen over reflection: prefer generated types (ts-rs from Rust, schema
inference) over runtime reflection and manual type duplication.
Mapped/conditional types and `infer` are powerful; use them to remove
duplication (the VoltAgent `Infer*` provider utilities are a good model), not
to show off. Keep public-facing types readable.
Avoid runtime metaprogramming (`Proxy`, dynamic property synthesis) in code
that must stay type-safe and tree-shakeable.

## Anti-Patterns
Avoid `any`; use `unknown` plus narrowing, or a named escape-hatch alias.
Avoid `as` and `as unknown as T` outside hard boundaries.
Avoid default exports outside framework-mandated files.
Avoid deep barrel files and the same type exported from multiple modules.
Avoid hand-writing types that should be generated from Rust.
Avoid editing generated type files.
Avoid collapsing typed errors into untyped success/`null` blobs.
Avoid `Effect.promise` (and unhandled rejections generally) for fallible I/O.
Avoid `console.*` in library code; use the structured logger.
Avoid floating promises and unbounded `Promise.all` fan-out.
Avoid inline-pinned dependency versions when a catalog owns them.
Avoid CJS-only dependencies in an ESM-only repo.
Avoid two overlapping linters running by default.
Avoid mixing Effect and plain `Result` paradigms inside one package.
Avoid premature generics and gratuitous type-level computation.
Avoid keeping old and new implementations alive without an approved migration.

## Review Checklist
Before signing off, ask:
- Does this follow the local repo conventions and tsconfig base?
- Did I search for an existing helper, type, or catalog entry first?
- Did I avoid duplicate type definitions and deep barrels?
- Is `any` absent (or routed through the named escape hatch)?
- Are external inputs validated with a schema at the boundary?
- Are wire types generated from Rust, and is the generated dir untouched?
- Are errors typed at library boundaries and converted only at the edge?
- Is the package ESM, with a correct `exports` map and `type: module`?
- Are type-only imports marked `import type`?
- Are shared dependency versions coming from the pnpm catalog?
- Do tests cover error and boundary cases through the public API?
- Did I run typecheck, lint, format, build, and tests (the documented gate)?
- Does the Rust-to-TS drift check pass (generated types committed and fresh)?
If any answer is no, fix it or state the reason explicitly.
