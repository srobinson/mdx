# PR #254 review (Fable) — @tm/contract extraction (Activity slice 4, PR-1)

## SPOT-CHECK — round 3, `fdaf5d8..5ca1956` (2026-07-10): CLEAN, merge-ready

The round-2 minor is resolved exactly as prescribed: `packages/contract/tsconfig.test.json` (extends `./tsconfig.json`, `types: ["node"]`, include `src/**/*.test.ts`, `exclude: []`) wired into the typecheck script (`tsc -p tsconfig.json && tsc -p tsconfig.test.json`). Proven first-hand: `tsc -p tsconfig.test.json --listFiles` shows both test files in the checked set, so the `ActivityWireRun` type-conformance fixture typechecks again. `@types/node` is devDependencies-only, no `dependencies` field exists, purity test passes (contract 3/3, both typecheck configs green). Prod tsconfig untouched: `types: []` intact, browser-neutral. Tree pristine at `5ca1956`.

## DELTA RE-VERIFY — round 2, `7c07c92..fdaf5d8` (2026-07-10)

Two correction commits reviewed (`af58ded` browser-ban enforcement, `fdaf5d8` pure-barrel refactor). **Delta verdict: all correction items faithfully applied and proven; ONE new minor introduced by the delta.** Tree pristine at `fdaf5d8` before and after (the mandated red-proof edits were reverted; `git status --short` empty).

### Item 1 — browser→context ban ENFORCED, proven red-then-green first-hand

Two layers landed. Manifest layer: `depLint.test.ts:forbiddenBrowserProductPlaneDeps` derives the product-plane set dynamically from `readdirSync(packages/)` minus the allowlist `{@tm/common, @tm/contract}` — future context packages are auto-covered. Source layer: `importGraphBoundary.test.ts:browserProductPlaneViolations` scans every www source and flags resolved targets inside activity/runtime/gateway src, with positive and negative unit tests (`isBrowserForbiddenProductPlaneTarget` true for `@tm/activity`, false for `@tm/contract/activity`).

**Red-proof executed as briefed:** temporarily added `"@tm/activity": "workspace:*"` to `www/packages/canvas/package.json` AND `import "@tm/activity";` to `www/packages/canvas/src/index.ts`. Both guards failed RED naming the offenders exactly: depLint `canvas -> @tm/activity`; boundary `www/packages/canvas/src/index.ts -> packages/activity/src/index.ts`. Reverted; suites green again. `@tm/contract/activity` remains allowed (dedicated unit test + full suite green).

### Item 2 — findings 2–4 + nit applied correctly

- `isContractSubpathExports` (finding 2): dead clause gone; keys must match `^\.\/([a-z][a-z0-9-]*)$` (single segment — nested multi-barrel keys now rejected too) and the value must equal exactly `./src/<context>/index.ts`. This closes both the dead-clause and the value-escape gaps completely, stronger than asked.
- `CONTRACT_ENTRYPOINTS` (finding 3): now derived via `contractEntrypointsFromExports(CONTRACT_ROOT)` from `packageExportsMap` — dual-maintenance gone; a null exports map yields `[]`, which fails closed.
- Purity (finding 4): `packagePurity.test.ts` asserts the manifest has no `dependencies` property; tsconfig gains `"types": []`.
- Nit (finding 6): `packageInternalViolations` takes `readonly string[]` only; all five call sites pass arrays.

### Item 3 — pure barrel + wire.ts: BYTE-IDENTICAL

`packages/contract/src/activity/wire.ts` declarations diffed byte-for-byte against the round-1 `index.ts` (which was itself verified against the pre-move originals): **identical**. `index.ts` is now a zero-declaration barrel re-exporting all 7 symbols (`export type` for the 6 types, value re-export for `activityStatuses`). The `./wire` import is intra-package (`packageInternalViolations` filters files inside `packageSrc`, so it never flags it — suite green confirms); `wire.ts` is not in the exports map, so it is not a public entrypoint and external reach-ins to it fail closed (derived entrypoint set contains only `src/activity/index.ts`).

### NEW minor introduced by the delta (the one finding this round)

**`packages/contract/tsconfig.json` now excludes `src/**/*.test.ts`, so the contract tests are typechecked by NO gate.** Proven first-hand: `tsc -p tsconfig.json --listFiles` shows exactly two checked files (`wire.ts`, `index.ts`); vitest runs tests through esbuild transform without type checking. Consequence: `activity.test.ts`'s wire-shaped fixture (`const item: ActivityWireRun = {…}`) — whose entire purpose was a type-level conformance assertion — no longer asserts anything at the type level; a drifted fixture or a type error in contract tests surfaces only if a runtime expect happens to catch it. The exclusion exists because `packagePurity.test.ts` imports `node:fs` which `"types": []` cannot see. Fix that keeps both properties: add `@types/node` to devDependencies and a `tsconfig.test.json` (extends `./tsconfig.json`, `"types": ["node"]`, include tests only), with the typecheck script running both configs — src stays machine-enforced pure, tests stay typechecked (this matches `@tm/common`, whose tests ARE typechecked).

Residual note (not counted): `BROWSER_FORBIDDEN_PRODUCT_PLANE_SRC` hard-codes `[activity, runtime, gateway]` while the depLint layer derives dynamically; a future context package needs a hand-edit at the source layer. Low risk — the manifest layer auto-catches the dep declaration a working import requires anyway.

### Gates re-run on `fdaf5d8` (all green, observed)

contract typecheck + test (3/3 incl. purity), activity typecheck + test (129 passed), FULL `@tm/shell` suite **1157/1157** (156 files — includes the 4 new guard tests), `lint:product-plane` clean (107 files).

---

# Round 1 review (at `7c07c92`) — retained below for the record


- **Branch:** `feat/activity-slice4-contract-pkg`, one commit `7c07c92` vs origin/main `2caadd8`. Tree pristine before and after review (`git status --short` empty; read-only, no repo writes by me or any subagent).
- **Method:** 8 independent finder angles + adversarial verifier (all read-only subagents), plus gates run first-hand.
- **Verdict: CLEAN on correctness, 6 minors.** Zero behavior change confirmed. The move is byte-exact, gating is complete, and the boundary amendment does not weaken the single-barrel invariant for any existing package. The minors are all in the enforcement machinery and the precedent surface, not in shipped runtime code.

## Gates run first-hand (all green, observed exit codes)

| Gate | Result |
|---|---|
| `pnpm --filter @tm/contract typecheck` | pass |
| `pnpm --filter @tm/contract test` | 2/2 pass |
| `pnpm --filter @tm/activity typecheck` | pass |
| `pnpm --filter @tm/activity test` | 129 passed, 9 skipped |
| `pnpm --filter @tm/shell test` (FULL suite, incl. boundary tests) | 156 files, 1153/1153 pass |
| `pnpm lint:product-plane` | 105 files clean |

## Brief point 1 — MOVE integrity: CONFIRMED CLEAN

All 7 symbols (`ActivityWireUsageTotals`, `ActivityWireRun`, `ActivityWorkspaceRollup`, `ActivityWorkspaceResponse`, `ActivityStreamFrame`, `ActivityStatus`, `activityStatuses`) landed in `packages/contract/src/activity/index.ts` with **field-for-field identical shape** (names, `| null` unions, optionality, union arms, const-array members and order) — verified independently by three finder agents and by me against the diff. Repo-wide grep: **zero leftover or duplicate declarations**; the only definition site is the contract module. `activityRouter.ts` imports the wire DTOs from `@tm/contract/activity`; `runActivityContext.ts` imports the status pair back and re-exports (`export type { ActivityStatus }; export { activityStatuses }` — isolatedModules/verbatimModuleSyntax compliant), so `domain/index.ts`, `src/index.ts`, `machineTestEvents.ts`, `runActivityMachine.test.ts`, and `projections/workspaceActivity.ts` all keep resolving unchanged. Exactly the 3 rewired files the scout predicted. `activityRouter.test.ts` wire-literal assertions untouched and green — the wire is byte-identical. No `www/`, `desktop/`, or gateway consumer of any moved symbol exists (gateway sees `ActivityStatus` only transitively via `RunActivityProjection.status`, resolved within activity's own dependency scope — no direct contract dep needed).

## Brief point 2 — Package purity: CONFIRMED (with one hardening gap, finding 4)

`packages/contract/package.json` has **no `dependencies` field at all**; devDeps = `vitest: catalog:` only. The lockfile entry confirms it. Nothing in `src/activity/` imports anything, so pg/fastify cannot be pulled transitively. Exports map is subpath-only (`"./activity": "./src/activity/index.ts"`, no `"."`), matching the locked design. tsconfig mirrors `@tm/common` (extends base+bundler, `lib: ["ES2023"]`, `include: ["src"]`) with `types: ["node"]` deliberately omitted — correct for a browser-neutral leaf, and typecheck passes without `@types/node`. On `activityStatuses` being runtime code in a "contract" package: **fine as shipped**. It is wire-load-bearing (the `status` values and `status_counts` keys ARE the contract), it is the documented exception in the new AGENTS.md text ("optional status enums as `as const` values"), and a types-only alternative would force every consumer to hand-maintain the value list. Keep it.

## Brief point 3 — Boundary correctness: amendment is sound; one pre-existing gap is now load-bearing (finding 1)

The amendment itself **did not open a hole or weaken the invariant**:
- `isAllowedRootPackageExports` routes every non-contract package to the **unchanged** `isSingleBarrel`; the vacuous-pass guard now requires `contract` present, so the check cannot silently skip it.
- Deep imports fail closed: `@tm/contract/src/activity` and `@tm/contract/activity/internal` are asserted unresolvable; `@tm/contract/activity` is asserted resolvable. Verified by running the suite.
- The Set-based `packageInternalViolations` rewrite is behaviorally identical for the four single-entrypoint packages (`path.resolve` is idempotent on the already-absolute entrypoints).
- `packageInternalViolations(CONTRACT_SRC, CONTRACT_ENTRYPOINTS)` backstops reach-ins: any import of a contract `src` file that is not a declared entrypoint fails red, from both planes (`allPackageSourceFiles()` scans `www/packages` AND `packages`).

**However**, the brief's premise "the test FORBIDS browser code importing @tm/activity" was never true, before or after this PR. Adversarially verified: `depLint.test.ts` guards only inspector↔canvas; `crossProductViolations` runs only for inspector↔canvas; the boundary test lists `@tm/activity` as a **legal resolvable entrypoint from canvas**; biome `noRestrictedImports` covers only canvas engine paths; there is no dependency-cruiser or .npmrc. The only real-world guard is pnpm's strict node_modules layout, which is defeated by adding `"@tm/activity": "workspace:*"` to a browser package.json — a one-line change no test flags. Pre-existing, but this PR's AGENTS.md newly asserts the "**never**" rule and the contract seam's whole purpose is to be mandatory, so the gap is now load-bearing. See finding 1.

## Brief point 4 — Gating: CONFIRMED complete, embed pipeline NOT copied

`justfile` `check`/`test` add exactly the two `@tm/contract` filter lines beside `@tm/common`; `ci.yml` product-plane job adds both typecheck and test lines (in the existing job — zero marginal infra; Postgres was already up); `pnpm-workspace.yaml` glob auto-registers; `lint:product-plane` and lefthook globs auto-cover; ≥1 contract test ships so vitest exits zero. `release.yml`/lefthook-typecheck/frontend-job omit contract exactly as they omit common/activity/runtime — consistent, not a gap. **Nothing from gateway's wheel-embed half (build.mjs, hatch artifacts, assert_gateway_wheel.py, CI tar/stage) appears in the diff** — the registration template was copied, the embed pipeline was not.

## Brief point 5 — Precedent quality: good template, four-site ritual to know about

The pattern scales correctly for the intended evolution (ONE contract package, subpath per context — AGENTS.md says so explicitly, which also justifies the `name === "contract"` literal dispatch in the test; revisit only if a second contract-kind package ever appears). What the next context (`./runtime`) must hand-edit in `importGraphBoundary.test.ts`: (a) `CONTRACT_ENTRYPOINTS`, (b) the deep-import fail-closed list, (c) the entrypoint-resolution list. Forgetting (a) is **fail-closed** (a legal `@tm/contract/runtime` import gets flagged as a reach-in with a misleading message) — safe direction, but a maintenance trap; finding 3 removes the worst of it. The exports-shape predicate is looser than its comment claims (finding 2) — worth tightening now since every future contract subpath inherits it.

## Findings ledger (all MINOR, ranked by value; none blocking)

```json
[
  {
    "file": "www/packages/shell/src/testSupport/importGraphBoundary.test.ts",
    "line": 97,
    "summary": "The browser→context-package prohibition the new packages/AGENTS.md declares ('never import context packages such as @tm/activity') is enforced by nothing; the contract seam is optional in practice.",
    "failure_scenario": "A browser package adds '@tm/activity': 'workspace:*' to package.json and barrel-imports it: depLint.test.ts (inspector↔canvas only), the boundary suite (lists @tm/activity as a legal resolvable entrypoint from canvas), biome, and CI all stay green while pg/fastify-adjacent server code enters the browser bundle. Cheapest fix, either or both: extend depLint.test.ts so no www package's declaredDependencies contains a product-plane package other than @tm/contract; or add a directional boundary check (www file → resolved target inside packages/* must be within contract src). Verdict: CONFIRMED."
  },
  {
    "file": "www/packages/shell/src/testSupport/importGraphBoundary.test.ts",
    "line": 183,
    "summary": "isContractSubpathExports polices export-map KEYS but barely polices VALUES, and carries a dead clause: `!value.startsWith(\"./src/*\")` is unreachable after `!value.includes(\"*\")`; the value is never required to resolve inside ./src/, and multi-barrel keys per context (./activity/internal) pass the shape check.",
    "failure_scenario": "A future contract package.json edit pointing a subpath at ./dist/x.js, ../activity/…, or adding a second per-context barrel passes the 'public exports shape' test. Adversarially verified backstop: the per-package internals checks DO catch any resulting .ts reach-in (all-green bypass limited to non-src data files like activity fixtures JSON), so this is defense-in-depth, not an open hole. Fix: drop the dead clause and require values match ./src/<context>/index.ts. Verdict: CONFIRMED (dead clause) / PLAUSIBLE (value gap)."
  },
  {
    "file": "www/packages/shell/src/testSupport/importGraphBoundary.test.ts",
    "line": 24,
    "summary": "CONTRACT_ENTRYPOINTS hand-duplicates the exports-map targets the same file already parses via packageExportsMap — two sources of truth that must be edited in lockstep.",
    "failure_scenario": "The very next planned step (adding ./runtime to the exports map) without the matching CONTRACT_ENTRYPOINTS edit makes a legal @tm/contract/runtime import fail the 'zero external imports into contract internals' test with a misleading reach-in message. Fail-closed (no hole), but a recurring trap for every future context. Fix: derive the entrypoint set from the exports-map values resolved against the package root. Verdict: CONFIRMED."
  },
  {
    "file": "packages/contract/package.json",
    "line": 1,
    "summary": "Zero-runtime-deps is the defining contract-package property (AGENTS.md states it; the seam's browser-safety depends on it) but no test enforces it, and contract sources have no machine guard against node globals.",
    "failure_scenario": "A future edit adds a runtime dep (zod, or an accidental server-type import) and every gate stays green while browser bundles gain product-plane weight. Two one-liners close it: a test asserting contract package.json declares no dependencies field, and `\"types\": []` in packages/contract/tsconfig.json so any NodeJS-global reference in contract sources fails typecheck. Verdict: CONFIRMED."
  },
  {
    "file": "www/packages/shell/src/testSupport/importGraphBoundary.test.ts",
    "line": 236,
    "summary": "allPackageSourceFiles() is unmemoized (recursive readdirSync over both package roots per call) and resolveSourceCandidate's statSync is uncached; the PR adds the 5th full re-walk.",
    "failure_scenario": "Each packageInternalViolations call re-traverses ~556 source files and re-stats up to ~9 candidates per import specifier; identical data 5 times per run, growing per package added. Pre-existing infra (suite still 15.6s total), but memoizing the file list at module scope — mirroring the existing sourceFileCache pattern in importGraph.ts — makes every future contract/context addition near-free. Verdict: CONFIRMED, low."
  },
  {
    "file": "www/packages/shell/src/testSupport/importGraphBoundary.test.ts",
    "line": 213,
    "summary": "packageInternalViolations takes `string | readonly string[]` with a normalization ternary; only the contract call site passes an array.",
    "failure_scenario": "Polymorphic parameter with no payoff: a plain readonly string[] and `[...]` at the four single-entrypoint call sites removes the union and the branch. Trivial. Verdict: CONFIRMED, nit."
  }
]
```

## Explicitly cleared (so nobody re-chases)

- **Wire-literal test fixtures** (`activityRouter.test.ts` hardcoded status_counts; contract test's ordered-enum pin and hand-rolled fixture): deliberate double-entry bookkeeping — deriving expectations from `activityStatuses` would mask exactly the regressions they pin. Not duplication defects.
- **`@types/node` omission**: intentional and correct for a browser-neutral leaf; typecheck passes (run first-hand). Folded the hardening upside into finding 4.
- **Conventions**: no em dashes in any added line (the two in-tree ones pre-date the branch); AGENTS.md self-consistent (four kinds, count updated); package.json/tsconfig field-order matches the @tm/common model; all touched files far under 700 LOC; no DRY violations (old declarations fully deleted).
- **CI placement**: contract lines land in the existing product-plane job — zero marginal infra, the cheap and correct choice.
- **runActivityContext re-export**: not ceremony — it is the zero-churn bridge that keeps 4 internal consumers resolving through ./domain.
