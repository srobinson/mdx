# PR #254 review: Codex family

Scope: `origin/main...7c07c92691451f4d6e16ad6983fa73506b28ccc5` on `feat/activity-slice4-contract-pkg`.

Verdict: 2 issues, 1 Major and 1 Minor.

## Findings

### Major: the browser to product plane prohibition is not enforced

Evidence:

- `packages/AGENTS.md:Contract packages` says browser packages consume `@tm/contract` and never import context packages such as `@tm/activity`.
- `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:inspector-canvas import graph boundary` checks Inspector against Canvas and Canvas against Inspector only. It has no browser source to `ACTIVITY_SRC`, `RUNTIME_SRC`, or `GATEWAY_SRC` check.
- The same suite's `resolves the entrypoints the exports maps declare` case deliberately resolves `@tm/activity` from a synthetic Canvas source path. Resolver coverage is valid, but no separate dependency rule rejects that resolved target.
- `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:packageInternalViolations` passes `ACTIVITY_ENTRYPOINT` to `isForbiddenPackageTarget`; `isForbiddenPackageTarget` exempts that entrypoint for every external source file, including files under `www/packages/*`.

Impact: a Canvas or Inspector source file can import the public `@tm/activity` entrypoint and the boundary suite remains green, despite the new package rule identifying that dependency as the path that exposes server dependencies such as `pg` and `fastify`. This leaves the load bearing reason for `@tm/contract` unenforced.

Required correction: add an explicit browser source to product plane context and serving root prohibition while keeping `@tm/common` and `@tm/contract` browser importable. Exercise both a forbidden `@tm/activity` public import and an allowed `@tm/contract/activity` import in the boundary suite.

Confidence: 100.

### Minor: the contract export shape guard accepts internal subpaths

Evidence:

- `packages/AGENTS.md:Import surfaces per package kind` defines one subpath per bounded context and says deep reach ins and unlisted subpaths fail closed.
- `www/packages/shell/src/testSupport/importGraphBoundary.test.ts:isContractSubpathExports` accepts any nonempty `./...` key except `./src...` and any string target without `*`. Consequently maps such as `{"./activity/private":"./src/activity/private.ts"}` and `{"./activity":"./src/activity/private.ts"}` satisfy the function even though they expose an internal or replace the context index.
- The explicit `@tm/contract/activity/internal` resolver assertion covers that one spelling only. It does not make the export map validator fail closed for another nested subpath.

Impact: the precedent test can stay green after a future contract context adds an extra nested public surface or maps a context subpath to a nonindex internal file.

Required correction: constrain keys to one context segment, for example `./<context>`, and constrain each target to the matching `./src/<context>/index.ts`, or derive and validate the entrypoint set from that exact mapping.

Confidence: 95.

## Verified clean areas

- Move integrity: `packages/contract/src/activity/index.ts:activityStatuses`, `ActivityStatus`, `ActivityWireUsageTotals`, `ActivityWireRun`, `ActivityWorkspaceRollup`, `ActivityWorkspaceResponse`, and `ActivityStreamFrame` match their `origin/main` declarations exactly. The five DTO declarations are gone from `packages/activity/src/server/activityRouter.ts`; the status const and type are gone from `packages/activity/src/domain/runActivityContext.ts`; repository search finds one declaration of each in the contract package.
- Consumer wiring: `packages/activity/src/server/activityRouter.ts` imports all five DTOs plus the shared status vocabulary from `@tm/contract/activity`. `packages/activity/src/domain/runActivityContext.ts` imports and reexports the status vocabulary, preserving the existing `./domain` and `@tm/activity` surfaces. `packages/contract/src/activity/activity.test.ts` exercises the new context entrypoint. No stale DTO import remains.
- Package purity: `packages/contract/package.json` has no `dependencies`; `packages/contract/src/activity/index.ts` has no imports and ships only the `activityStatuses` value plus TypeScript types. The const is justified because both domain status vocabulary and wire rollup keys consume the same ordered set. No `pg`, `fastify`, or `@tm/activity` dependency points back into the package.
- Package shape: `packages/contract/package.json:exports` exposes `./activity` only and omits a root barrel. `packages/contract/tsconfig.json` follows the product plane leaf package base and bundler configuration. All new files remain below the 700 LOC guardrail.
- Gates and packaging: `justfile:check`, `justfile:test`, `.github/workflows/ci.yml:product-plane Type check`, and `.github/workflows/ci.yml:product-plane Unit + integration tests` register `@tm/contract`. The gateway embed path is unchanged; `packages/gateway/scripts/build.mjs` bundles transitive TypeScript code into `main.js`, and no contract specific tar, hatch, or embed pipeline was added.
- Observed CI: `gh pr checks 254` reports all nine checks passed, including `product-plane`, `frontend`, `backend package`, and `linux wheel gateway spawn`.
- Worktree: `git status --short` was empty before and after review. Local branch and PR head both resolved to `7c07c92691451f4d6e16ad6983fa73506b28ccc5`.
