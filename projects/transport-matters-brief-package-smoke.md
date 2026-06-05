# package:smoke must prove the packaged graph

Repo transport-matters, baseline main c7f19c14. Owner approved follow-up.

## Defect it must catch
In PR #499's fix round, `desktop/src/app/browserPanes/BrowserPaneHost.ts` gained a runtime import of `integerPlacementBounds` from `@tm/contract`. `@tm/contract` is a source-only devDependency of the desktop, omitted from the packaged app, so a packaged app would fail at startup. `pnpm package:smoke` passed because it runs main and preload from beneath `desktop/dist` and Node resolves the missing package through the ancestor `desktop/node_modules`. The reviewer (codex) established this; confirm it by reproducing: reintroduce a runtime `@tm/contract` import on a scratch branch and show the current smoke passes.

## Deliverable
`pnpm --filter transport-matters-desktop package:smoke` (script `package-smoke-build.mjs` + `dist/packageSmoke.js`) runs the packaged output from a relocated copy outside the workspace tree (a temp dir with no ancestor node_modules), so unresolvable runtime imports fail the smoke. Prove it both ways: the reintroduced bad import fails the new smoke; main passes. Keep CI's desktop job unchanged unless the relocation needs it. Also add a cheap static guard if one fits naturally (e.g. a test that desktop production dist has no runtime `@tm/*` import), only if it is not a second implementation of what the smoke now proves.

## Rules
Gates verbatim: desktop `just check`, `pnpm package:smoke`, `just check`, `just test`. Files under 700 lines, DRY, symbols not lines in docs. Push the branch, no PR until review is clean. Road test section in the PR: the two-way proof commands.
