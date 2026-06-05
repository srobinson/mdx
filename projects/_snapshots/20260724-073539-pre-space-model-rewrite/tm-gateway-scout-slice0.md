---
title: Scout & Plan — slice 0, packages/gateway (Fastify composition root)
type: projects
tags: [transport-matters, gateway, slice-0, scout, reuse-map, fastify, p1]
summary: Read-only reuse map + quality map + plan for standing up packages/gateway as the thin Fastify composition root. Baseline main ef11b6c. One decision needed (TS process runner); one gating surface beyond the brief (shell biome enumeration).
status: active
created: 2026-07-04
---

# Scout & Plan — slice 0: packages/gateway

Baseline: `main` @ ef11b6c, tree pristine. Read-only pass; no writes to the
repo. Citations are path + symbol, never line numbers.

## Reuse map

### 1. Canonical scaffold to mirror

Mirror **`@tm/common`** (`packages/common/`), not `@tm/activity` — the Gateway
is a serving root with no domain, so the foundational package's minimal form
fits; Activity's extra surface (`contracts/` include, `resolveJsonModule`, pg
deps) is context baggage the Gateway does not want.

- **package.json** (`packages/common/package.json`): `"name": "@tm/gateway"`,
  `private: true`, `version: 0.1.0`, `type: module`,
  `exports: { ".": "./src/index.ts" }`, scripts `test: vitest run` and
  `typecheck: tsc -p tsconfig.json --noEmit`, devDeps `@types/node` +
  `vitest`. Add dependency `fastify` (see #3).
- **tsconfig** (`packages/common/tsconfig.json`): extends
  `../../tsconfig.base.json` + `../../tsconfig.bundler.json`, `lib: ES2023`,
  `types: ["node"]`, `include: ["src"]`. Note `tsconfig.bundler.json` sets
  `noEmit: true` — no package emits JS, which feeds the Decision below.
- **vitest config**: none found anywhere under `packages/*` — both packages
  run bare `vitest run` on the hoisted root `vitest` devDependency with
  default includes (colocated `src/**/*.test.ts`). Mirror that: no config
  file.
- **Barrel**: `packages/common/src/index.ts` — explicit named re-exports,
  nothing else. The Gateway barrel exports only the composition-root factory.
- **Kind**: `docs/ARCHITECTURE.md` "Product package placement" already names
  the third kind — "Serving roots are a distinct kind from contexts… Today it
  lives as `packages/gateway`" — but `packages/AGENTS.md` documents only
  context and foundational kinds. The slice should add the serving-root kind
  there (doc edit, in scope: it defines the mount contract for later
  contexts).

### 2. Mount-factory contract

**None found.** Searches run: `rg 'createServer|Router|router'` over every
`packages/*/src/index.ts` and `www/packages/*/src/index.ts*` (zero hits);
`packages/activity/src/index.ts` exports domain/ports/adapters symbols only.
Confirmed: `packages/activity/src/server/` holds only `pgContracts.ts` +
`pgContracts.test.ts` (pg NOTIFY channel + table/column constants — wire
vocabulary, not a router).

**Shape to adopt** (new, slice 0 establishes it): a context exposes from its
barrel a router factory returning Fastify's own composition unit —
`create<Context>Router(deps): FastifyPluginAsync` — and the Gateway mounts it
with `app.register(factory(deps), { prefix })`. Two properties make this the
right contract: Fastify plugins are structurally typed, so contexts type
against `fastify` itself and never import the Gateway (dependency stays
downstream-only per `docs/ARCHITECTURE.md` "Target context map"); and
`fastify.inject()` exercises a registered plugin port-less, which is exactly
the slice-0 proof. Since `packages/activity` has no router yet, slice 0
proves the contract against a **fixture** factory owned by the Gateway's own
test.

### 3. Fastify / HTTP server precedent

**None found.** Searches run: `rg 'fastify|express|"hono"|"koa"|h3'` over all
`package.json` files (zero hits) and `rg -i fastify` over the whole tree
(zero hits). No server-bootstrap util exists on the TS side; the Python
uvicorn bootstrap is capture-plane and not a mirror target. Nearest TS spawn
precedent is `desktop/src/backendProcess.ts::launchBackendProcess` (child
spawn + exit watcher), relevant to supervision later, not to slice 0.

**Pin: Fastify major 5** (verified against fastify.dev and the release feed,
2026-07: current line is 5.8.x, e.g. 5.8.2; v5 targets Node >= 20, matching
root `package.json` `engines.node >= 20.19.0` and the CI Node 20 setup).
Suggest `"fastify": "^5.8.2"`. `@fastify/websocket` is NOT needed in slice 0
(fixture router is plain HTTP); it enters with Runtime slice 1.

### 4. importGraphBoundary mechanism

Hybrid, in `www/packages/shell/src/testSupport/importGraphBoundary.test.ts`:

- **Auto-discovered**: the single-barrel test iterates `packages/*` via
  `rootPackageExports()` (`readdirSync` on the repo `packages/` dir) and
  fails any package whose `exports` map is missing or not exactly `{"."}`.
  `packages/gateway` is covered the day the directory exists — shipping the
  exports map is mandatory, not optional. Its vacuous-pass guard
  (`expect.arrayContaining(["activity", "common"])`) must gain `"gateway"`.
- **Explicit per package**: reach-in enforcement is one case per package via
  `packageInternalViolations(SRC, ENTRYPOINT)`. Mirror the existing pair:
  add `GATEWAY_SRC` / `GATEWAY_ENTRYPOINT` consts beside
  `ACTIVITY_SRC`/`COMMON_SRC` and an
  `it("enforces zero external imports into gateway internals")` case.
- **No consumers yet**: the case passes vacuously today and fails closed the
  moment any file imports a gateway internal — that is the point; the
  arrayContaining guard is what prevents the vacuous pass from hiding a
  missing package. Nothing else special is needed.
- **Free coverage**: `allPackageSourceFiles()` already includes
  `sourceFiles(ROOT_PACKAGES)`, so the Gateway's own files are scanned as
  import *sources* with zero edits — a Gateway import of
  `@tm/activity/src/...` internals fails the existing Activity case.
- Optional mirrors: add `"@tm/gateway"` to the "resolves the entrypoints"
  list and a `"@tm/gateway/src/app"`-style specifier to the deep-import
  fail-closed list, matching the `@tm/activity`/`@tm/common` examples.
- Resolution detail: `importGraph.ts::workspacePackageCandidate` probes
  `www/packages/<name>` before `packages/<name>` — no `www/packages/gateway`
  exists, so `@tm/gateway` resolves correctly through the exports map.

### 5. justfile + CI gating (plus one surface the brief did not list)

- **`justfile::check`**: add `pnpm --filter @tm/gateway typecheck` beside the
  `@tm/common` / `{{activity_package}}` lines.
- **`justfile::test`**: add `pnpm --filter @tm/gateway test` (suites run
  serially by design — see the recipe's oversubscription comment; append,
  do not parallelize).
- **CI `.github/workflows/ci.yml`, job `product-plane`**: add
  `pnpm --filter @tm/gateway typecheck` to the "Type check" step and
  `pnpm --filter @tm/gateway test` to the "Unit + integration tests" step.
  (The job's Postgres service is irrelevant to the Gateway but harmless.)
- **Fourth surface (not in the brief)**: biome lint reaches root packages via
  explicit path enumeration in `www/packages/shell/package.json` — the
  `lint`, `lint:fix`, and `format` scripts each list
  `../../../packages/activity`. Add `../../../packages/gateway` to all three
  or the Gateway ships unlinted while looking gated (`just check` runs shell
  `check: format lint typecheck`).
- Non-surfaces: `justfile::test-affected` uses pnpm's changed-since filter
  (no enumeration, auto-covers); `lefthook.yml` pre-commit lint globs only
  `www/**` (Activity is not pre-commit-linted either — existing parity, no
  edit).
- Caution for the builder: `just check` invokes shell `lint:fix`
  (`biome check --write`) — it can modify files. Run gates on a committed
  tree, and do not run them during read-only passes.

### 6. Dev-mode supervision precedent

Python, capture-plane-coupled: `ProcessSupervisor` at
`api/src/transport_matters/supervisor.py` (facade over
`supervisor_core.ProcessSupervisor` / `ManagedProcess`; imports `pty`,
`termios`, `fcntl`) and the shared-proxy model at
`api/src/transport_matters/shared_proxy/process.py`
(`SHARED_PROXY_PROCESS_NAME`, pid-file + supervised `mitmdump` child).
**Reusable as a pattern (pid file, supervised child, health probe), not as
code** for a Node process. The nearest TS shape is
`desktop/src/backendProcess.ts::launchBackendProcess` + `BackendExitWatcher`.
**Slice 0 does not need supervision**: the A-W0 acceptance is boot + inject
fixture test + gates. Dev-mode supervision v1 binds at the slice that wires
the Gateway into dev mode (Runtime P1 S1/S2 territory) — flag carried, no
slice-0 work.

## Quality map

- **Sizing healthy.** Largest source file under `packages/` is
  `packages/activity/src/domain/runActivityMachine.ts` at 446 LOC; largest
  test 627 LOC. Nothing near the 700 guardrail. `importGraphBoundary.test.ts`
  + `importGraph.ts` are well-shaped.
- **No duplication or parallel implementations** found in the touched area.
- **Enumeration sprawl (quiet duplication):** gating one new package touches
  4 files / ~7 lines (justfile x2 recipes, CI x2 steps, shell biome scripts
  x3). Explicit enumeration is the deliberate repo convention (the CI job
  comment says so); a `--filter './packages/*'` glob would auto-cover but
  changes gate semantics. Not slice-0 business.
- **justfile style drift:** `activity_package := "@tm/activity"` variable
  coexists with literal `@tm/common` in the same recipes; the variable adds
  nothing.
- **Stale `.gitkeep` files** in populated dirs
  (`packages/activity/src/{adapters,server,service,projections}/.gitkeep`).
- **Boundary quirk (observation, no action):** the test governing
  `packages/*` boundaries runs in the shell (www) suite, i.e. the CI
  `frontend` job, not `product-plane`. Enforcement is real either way.

**Grooming recommendation: during.** While editing the justfile recipes,
normalize the filter style (drop the single-use variables or use them
consistently) and delete the stale `.gitkeep`s — both are one-line touches in
files the slice already edits. Everything else (enumeration glob, boundary
test home) defer.

## Plan

**Decision needed:** how the Gateway runs as a process. Every `packages/*`
package is library-only and `tsconfig.bundler.json` is `noEmit` — nothing in
the repo can execute TypeScript as a process today, and the Node floor
(`engines.node >= 20.19.0`, CI Node 20) predates native type-stripping.
A-W0's acceptance says the Gateway "boots on a loopback port with a health
route", so slice 0 needs a runner. Recommend **`tsx` as a Gateway
devDependency** with a `start` script (`tsx src/main.ts`) — smallest change,
no emit, no engine bump. Alternatives: raise the Node floor to >= 22.18 for
native type stripping (workspace-wide blast radius), or a `tsc` emit build
(breaks the noEmit convention). The `fastify.inject()` proof is unaffected
either way.

Ordered steps, each bound to the reuse map above:

1. **Scaffold `packages/gateway`** mirroring `@tm/common` (#1): package.json
   (`@tm/gateway`, single-barrel exports map — mandatory on day one per #4),
   tsconfig, no vitest config. Dependency `fastify ^5.8.2` (#3); `start`
   script per the Decision.
2. **Composition root**: `src/app.ts` — `buildGateway()` returning a Fastify
   instance with a health route and a `mountContext(factory, prefix)` seam
   accepting `FastifyPluginAsync` factories (#2); `src/main.ts` — loopback
   listen; `src/index.ts` barrel exporting `buildGateway` (+ the mount seam)
   only.
3. **Mount-contract proof**: colocated `src/app.test.ts` with a fixture
   context-router factory; `fastify.inject()` asserts the health route and
   the fixture route respond, port-less (#2). This is the contract test
   Runtime/Activity mount against downstream.
4. **Boundary suite** (#4): `GATEWAY_SRC`/`GATEWAY_ENTRYPOINT` consts +
   reach-in case + `"gateway"` in the arrayContaining guard (+ optional
   resolves/fail-closed list entries) in
   `www/packages/shell/src/testSupport/importGraphBoundary.test.ts`.
5. **Gates** (#5): justfile `check` + `test` lines; CI `product-plane` two
   step additions; shell biome enumeration x3. Grooming-during rides here.
6. **Docs**: add the serving-root kind + mount-factory contract to
   `packages/AGENTS.md` (#1, #2).

**Tests + gates**: `just check` and `just test` verbatim (never bare
tsc/vitest); the new inject fixture test runs under
`pnpm --filter @tm/gateway test` inside both; the boundary suite runs inside
shell test (root `just test` + CI `frontend`).

**Flagged target / out-of-scope (not planned):** how the browser bundles are
served today (Python `mount_frontend_bundles`: inspector at `/`, canvas at
`/canvas`, embedded in the wheel) and the eventual capture reverse-proxy —
both are Gateway-as-origin target posture, explicitly out of slice 0.
Real Runtime/Activity router mounts are downstream slices.
