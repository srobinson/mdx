# PR #254 review — @tm/contract extraction (activity slice 4 PR-1)

**Family:** opus · **Branch:** `feat/activity-slice4-contract-pkg` vs `origin/main`
**Verdict:** CLEAN (pure refactor, precedent-quality). Tree pristine (`git status --short` empty). Gate green.
**Scope:** stand up `@tm/contract`, move activity wire DTOs out of the server package. Zero behavior change.

## Gate observed (run locally, exit 0)
- `pnpm --filter @tm/contract test` → 2 passed
- `pnpm --filter @tm/contract typecheck` → clean
- `pnpm --filter @tm/activity typecheck` → clean (activity now depends on contract)
- `pnpm --filter @tm/shell test importGraphBoundary` → 11 passed

## 1. MOVE integrity — PASS
- 7 symbols now single-owned in `@tm/contract/activity` (`index.ts`): const `activityStatuses`, type `ActivityStatus`, interfaces `ActivityWireUsageTotals` / `ActivityWireRun` / `ActivityWorkspaceRollup` / `ActivityWorkspaceResponse`, and union `ActivityStreamFrame`.
- Zero shape drift: the moved DTO block is byte-identical to the deleted block in `activityRouter.ts` (verified by diffing `git show main:…activityRouter.ts` against the new `index.ts`); `activityStatuses` order preserved and pinned by `activity.test.ts` ("exports the frozen status enum in wire order").
- No leftover/duplicate declarations of the 7 symbols in `activityRouter.ts`. (The remaining `ActivityWorkspaceSubscriptionSource` is a pre-existing DI shape, not a wire DTO, and correctly stays.)
- Imported BACK: `activityRouter.ts` imports the 6 wire symbols + `activityStatuses` from `@tm/contract/activity`; `runActivityContext.ts` imports `ActivityStatus` + `activityStatuses` and re-exports them so `../domain` stays the internal resolution path.
- Consumer coverage complete: 2 direct `@tm/contract/activity` import sites (`activityRouter`, `runActivityContext`); the domain re-export shim keeps `machineTestEvents` / `projections/workspaceActivity` resolving through `./runActivityContext` / `../domain` untouched. Minimal, deliberate blast radius. (Scout's "3" counts the pre-refactor rewire surface; net direct contract imports are 2, and `@tm/activity` typecheck confirms every consumer resolves.)

## 2. Package purity — PASS
- `@tm/contract/package.json`: zero `dependencies`; only devDep `vitest`. Cannot transitively pull `pg`/`fastify`.
- Subpath export map is `{"./activity": "./src/activity/index.ts"}` — no root `"."` barrel, matching the leaf convention documented in `packages/AGENTS.md` ("Contract packages … do not take a single root barrel: each bounded context is a subpath export").
- `tsconfig.json` extends `tsconfig.base.json` + `tsconfig.bundler.json`, `lib: ES2023`, `include: src`. Correct for a browser-importable leaf.
- `activityStatuses` const: the ONLY runtime export (all others are `export interface`/`export type`). Shipping it from a "contract" package is per-spec: AGENTS.md explicitly permits "optional status enums as `as const` values." Types-only would force every consumer to re-declare the wire order — keeping the single `as const` here is the correct call, not a smell.

## 3. Boundary correctness (load-bearing) — PASS, no hole opened
- The single-barrel assertion was generalized (`isSingleBarrel` → `isAllowedRootPackageExports`), not weakened: `activity`/`common`/`gateway`/`runtime` still must be single `"."` barrels; only `name === "contract"` routes to `isContractSubpathExports`, which requires ≥1 subpath key, **rejects** a root `"."`, and rejects `*` wildcards and `./src` / `./src/*` keys. The vacuous-pass guard was extended to include `contract`.
- Reach-ins still fail closed: `@tm/contract/src/activity` and `@tm/contract/activity/internal` are in the "fails closed for deep package imports" list; `@tm/contract/activity` is in the "resolves the entrypoints" list. New test "enforces zero external imports into contract internals" runs `packageInternalViolations(CONTRACT_SRC, [contract/src/activity/index.ts])`.
- `@tm/activity` remains locked: its barrel is still the only allowed surface, and `@tm/activity/domain` / `@tm/activity/src/domain/*` stay in the fail-closed list. The amendment did not touch activity's guarantees.
- "Browser cannot import `@tm/activity`" is held by the pnpm dependency graph: no `www/packages/*/package.json` declares `@tm/activity`, and no browser src imports it. So @tm/contract genuinely delivers a browser-reachable wire seam that carries none of activity's `pg`/`fastify` weight.

## 4. Gating — PASS
- `.github/workflows/ci.yml`: `@tm/contract typecheck` and `@tm/contract test` added in product-plane block, ordered right after `@tm/common`.
- `justfile` `check` and `test`: same two filters added in the same position.
- Did NOT copy the gateway embed pipeline: `packages/contract` has no `build.mjs`, no hatch/tar step, no CI embed. Correct — a pure-types leaf has nothing to bundle.
- `pnpm-lock.yaml`: `packages/contract` importer + `@tm/contract` link into `packages/activity` recorded.

## 5. Precedent quality — clean template, one observation
- Subpath pattern scales to `runtime` with zero fighting: a second context is one more `exports` key (`./runtime`), one more `CONTRACT_ENTRYPOINTS` element, and one more fail-closed list entry. `isContractSubpathExports` already accepts arbitrary subpaths, so no test rewrite needed. The `name === "contract"` special-case is correct because AGENTS.md declares `@tm/contract` the ONLY contract package (runtime is a subpath, not a new package).
- OBSERVATION (not a defect, pre-existing): the boundary test enforces the split via (a) reach-in prohibition and (b) contract-leaf resolution, but it does not itself forbid a browser file from importing the `@tm/activity` *barrel*. That guarantee currently rests on the dep graph + AGENTS.md convention. If a future dev added `@tm/activity` to a browser package's deps, only convention — not this test — would stop the barrel import. Cheap future hardening: an explicit "no www/* → `@tm/activity`" assertion. Out of scope for PR-1.

## Minor (already surfaced in code-review pass; test-support only, non-blocking)
- `importGraphBoundary.test.ts` `isContractSubpathExports`: the value clause `!value.startsWith("./src/*")` is dead — `!value.includes("*")` on the same line already excludes any value with `*`, so contract export *values* are effectively unvalidated while reading as if guarded. Delete it or replace with a real value-shape check. Cosmetic; nothing depends on it.

## Bottom line
Precedent-setting refactor is correct, minimal, and well-tested. Dependency direction is right (contract = zero-dep leaf below activity), duplication is net-negative, the boundary invariant is preserved not weakened, and the subpath pattern is a clean template for runtime. Ship. One dead-clause nit in test-support is the only cleanup item.
