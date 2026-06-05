# S3 Review — PR #327 (`@tm/space-client` extraction) — Fable, sole reviewer

**Verdict: pure move, yes. Blockers: 0. Majors: 0. Minors: 0.** Approve.

Scope reviewed: PR #327, base `feat/multi-launch` (merge base `cea43eea`), head `5a561cee`, 40 files, +576/−564. Read-only pass; verification was mechanical (byte-level diffs against the originals), not diff-reading alone.

## 1. Genuine move — CONFIRMED byte-identical

- `canvas/src/route.ts` (old) vs `space-client/src/urlTupleCodec.ts` + residual `route.ts`: concatenated the two new files and diffed against the base file. The only delta is `isStressCanvas` sitting at a different offset (it stayed in `route.ts`). Zero behavioural delta: no reordered guards, no changed defaults, no dropped null checks, no altered error paths in `parseCanvasLaunchContext`, `defaultCanvasId`, `isUsableIdentity`, `resolveCanvasLaunchIdentity`, `worktreeSwitchUrl`, `spaceSwitchUrl`, `canvasSwitchUrl`, or the three private helpers.
- `core/src/spaceTransport.ts` (old) vs `space-client/src/spaceTransport.ts`: identical except (a) the planned deletions (`deleteWorkdir`, `fetchWorktrees`, `fetchWorktree`, `createCanvas`, `updateCanvas` and their now-unused `UpdateCanvasPatch`/`WorktreeId` type imports) and (b) the import re-anchor `./transport` → `@tm/core`. `requestApiJson`/`requestApiVoid` are exported from `core/src/transport.ts` and re-exported through core's barrel, so the re-anchor resolves.
- Moved tests are the same assertions relocated; the only text changes are em-dash removals in two comments (house style, no assertion change). `route.test.ts` retains the `isStressCanvas` case.

## 2. Relative path arithmetic — CLEAN

- Moved sources (`spaceTransport.ts`, `urlTupleCodec.ts`) contain no filesystem joins at all; they are pure browser code.
- `space-client/tsconfig.json` extends `../../../tsconfig.base.json` — correct for the `www/packages/space-client` depth and identical in shape to `core/tsconfig.json` at the same depth.
- `importGraphBoundary.test.ts:SPACE_CLIENT_SRC` anchors to `PACKAGES_ROOT` (www/packages), not `ROOT_PACKAGES` (repo packages) — the correct anchor, unlike `SPACE_SRC` which correctly uses `ROOT_PACKAGES` for the root-level `@tm/space`.
- `shell/vite.config.ts` and `shell/package.json` biome globs use `../space-client`, a correct sibling reference from shell.

## 3. Pruned surface actually dead — CONFIRMED independently

`rg "\b(fetchWorktree|fetchWorktrees|createCanvas\(|updateCanvas|deleteWorkdir)\b"` across `www`, `packages`, and `api/src` at head: zero hits. The `fetchWorktrees` test in `core/src/transport.test.ts` and the create/update/deleteWorkdir cases in the moved `spaceTransport.test.ts` were deleted with their subjects. `fetchCanvases` and `fetchCanvas` are KEPT and exported (`space-client/src/index.ts`); `fetchCanvases` has a live consumer (`canvas/src/launcher/useCanvases.ts:useCanvases`), `fetchCanvas` is deliberately held for S5's child-canvas verification per the plan's keep clause.

## 4. Placement and boundaries — CORRECT

- Package lives at `www/packages/space-client`, covered by the `www/packages/*` workspace glob; browser package in the browser tree, not the root `packages/*` where `@tm/space` (control plane) lives.
- `package.json` exports exactly `{ ".": "./src/index.ts" }`.
- `importGraphBoundary.test.ts` additions are meaningful, not decorative: `@tm/space-client` was added to the resolvable-entrypoints list (browser-importable, as intended) and NOT to `BROWSER_FORBIDDEN_PRODUCT_PLANE_SRC`; deep imports `@tm/space-client/src/urlTupleCodec` and `@tm/space-client/urlTupleCodec` are asserted to fail closed; a new `packageInternalViolations(SPACE_CLIENT_SRC, [SPACE_CLIENT_ENTRYPOINT])` case enforces zero external reach-ins.
- Registered in `justfile` typecheck, `scripts/test-affected.sh` shell-aggregate classification, shell biome lint/format globs, shell vitest DOM and node projects, and `browserIdentity.test.ts` surfaces.

## 5. No compat shim — CONFIRMED

`core/src/index.ts` barrel line deleted; `rg spaceTransport www/packages/core` returns nothing. No re-export, no alias, no lingering `../route` imports of moved symbols anywhere in canvas (only `isStressCanvas`, which legitimately stayed).

## Dependency direction

`@tm/space-client` → `@tm/core` + `@tm/contract`; core does not depend back. No cycle. Canvas gained the `@tm/space-client` workspace dep; lockfile links match the real relative locations.

## CI

All nine jobs green on the PR head, including `desktop · standalone` and `frontend e2e`.

## Notes (non-findings)

- `space-client/tsconfig.json` carries `resolveJsonModule: true` with no JSON imports in the package; it mirrors the sibling `core/tsconfig.json` convention, so I read it as convention-following, not cruft. No action.
- `canvasSwitchUrl` remains untested; this predates the move and the symbol moved byte-identically, so it is S-series scope, not S3's.
