# PR 41 Review: fix-preload-ci

Reviewed commit `d5226f23e39eaba8f8c6a9c83c31f979a9314d84` on branch `feat/fix-preload-ci`.

## Findings

No findings.

- Blockers: 0
- Majors: 0
- Minors: 0

## Verification

- `cd /Users/alphab/Dev/LLM/DEV/helioy/transport-matters-worktrees/fix-preload-ci/desktop && pnpm install && pnpm typecheck && pnpm test && pnpm build`
  - Passed. Vitest reported `6 passed (6)` test files and `27 passed (27)` tests.
  - Build printed `Preload CommonJS guard OK: dist/preload.cjs is CommonJS.`
- `gh -R littleorgans/transport-matters pr checks 41 --watch=false`
  - Passed: `backend · lint`, `backend · test`, `frontend`, `desktop`, `backend · package`.
- `gh -R littleorgans/transport-matters run view 27075712162 --job 79912645830 --log`
  - The `desktop` job ran `xvfb-run --auto-servernum --server-args="-screen 0 1280x900x24" pnpm package:smoke`.
  - The smoke emitted `{"executablePath":"/home/runner/work/transport-matters/transport-matters/desktop/dist/package-smoke/Transport Matters-linux-x64/Transport Matters","status":"main-window-created"}`.
- `desktop/dist/preload.cjs` contains CommonJS output with `require("electron")`, no top level ESM `import` or `export`, and no `desktop/dist/preload.js` artifact was emitted.
- `desktop/src/main.ts:76` points `resolvePreloadPath()` at `preload.cjs`; `desktop/src/window.ts:27` to `desktop/src/window.ts:32` keeps `contextIsolation: true`, `nodeIntegration: false`, and `sandbox: true`.
- `desktop/src/packageSmoke.ts:136` to `desktop/src/packageSmoke.ts:144` accepts only `main-window-created`; `desktop/src/main.ts:254` to `desktop/src/main.ts:293` maps preload error, missing bridge, and timeout to non-success statuses.
- `.github/workflows/ci.yml:134` to `.github/workflows/ci.yml:184` adds the Linux desktop job with typecheck, tests, build, GUI libraries, xvfb, and `pnpm package:smoke`. No `api/` files changed.

## Deviation assessment

- Removing `desktop/src/preload.test.ts` is acceptable. The deleted test mocked Electron and only proved the mock was called. The new packaged Electron smoke exercises the real sandboxed preload path.
- The `about:blank` probe is sound for this regression. It loads a real BrowserWindow with the production preload options, avoids the hosted route dependency, and still proves the bridge is exposed after preload execution.
