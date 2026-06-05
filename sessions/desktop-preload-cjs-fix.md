---
title: Desktop Electron preload CommonJS fix + desktop CI gate (PR B)
type: sessions
tags: [frontend, electron, preload, sandbox, commonjs, esm, ci, transport-matters]
summary: Fixed the sandboxed Electron preload (ESM→CommonJS) that crashed `transport-matters desktop`, and closed the CI gap that let it ship green.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

`transport-matters desktop` failed at launch: "Unable to load preload script ... Cannot
use import statement outside a module". The desktop package is `"type": "module"`, so tsc
(NodeNext + verbatimModuleSyntax) emitted `dist/preload.js` as ESM, but the window sets
`webPreferences.sandbox: true` and sandboxed Electron preloads are evaluated as CommonJS.
Latent since the desktop shell/secure-window commits; PR#40 added the first real launch
path and surfaced it. CI never built/ran the desktop package, so it shipped green.

Fix (branch `feat/fix-preload-ci`, desktop/ + ci.yml only — no api/ collision with the
parallel agent-home rename):

- `src/preload.ts` → `src/preload.cts` (tsc emits `dist/preload.cjs`, CommonJS). Authored
  with `import electron = require("electron")` to satisfy verbatimModuleSyntax in a `.cts`.
- `main.ts` `resolvePreloadPath()` → `preload.cjs`.
- New `awaitPreloadSmokeStatus` + `createPreloadProbeWindow`: the package smoke now PROVES
  the preload executed instead of asserting "a window was created".
- `scripts/assert-preload-cjs.mjs` static guard, wired into `build`.
- New `desktop` CI job: typecheck + test + build + xvfb `package:smoke`.

## Architecture Decisions

- **CommonJS preload via `.cts`, not sandbox:false + .mjs.** Keeps the deliberate sandbox
  hardening. `.cts` is the TS-native way to emit `.cjs` from a `type: module` package; no
  bundler added (project uses plain tsc).
- **Smoke probes a hidden `about:blank` window**, reusing `window.ts` `createWindowOptions`
  (the real sandbox prefs). Rationale: no backend runs during the smoke, and the hosted
  `:8788` window's `did-fail-load` → `dialog.showErrorBox` is a modal that blocks headless
  xvfb CI. `about:blank` always commits, so the preload runs deterministically.
- **Two failure signals**: `webContents.on('preload-error')` (definitive failure — catches
  the ESM-in-CJS SyntaxError) plus `executeJavaScript('globalThis.transportMattersDesktop
  ?.appName')` on `did-finish-load` (positive proof the contextBridge exposed the API).
  Anything else fails closed (`preload-timeout`/`preload-bridge-missing`). `readSmokeStatus`
  only accepts `main-window-created`, so a bad preload makes `package:smoke` exit nonzero.
- **Static guard in `build`** asserts `dist/preload.cjs` exists and has no top-level
  import/export — a millisecond check that needs no display, complementing the xvfb smoke.

## Performance Notes

N/A (Electron desktop tooling, not a rendered UI surface).

## Deviations from Spec

- **Removed `preload.test.ts`.** vitest/vite cannot transform a CommonJS `.cts` through its
  ESM pipeline: verbatimModuleSyntax forces `import = require` (which vite's import-analysis
  rejects), and a plain `require` bypasses `vi.mock` (hits the real electron binary). The
  mock-based test was also the exact weak link that let the bug ship. The package smoke
  (real sandboxed preload + bridge read-back) is strictly stronger coverage.
- Coordinator's brief implied keeping `preload.test.ts`; flagged the removal + rationale to
  the coordinator, who owns commits.

## Open Items

- **Linux CI job unverified locally** (developed on macOS). Pinned `ubuntu-22.04` and
  apt-install xvfb + Electron GUI libs (libasound2, libgtk-3-0, libnss3, libgbm1, libatk*,
  libcups2). 22.04 avoids the 24.04 `libasound2`→`libasound2t64` rename. Needs a CI run.
- Minor duplication: bridge key `transportMattersDesktop` + appName `Transport Matters`
  live in both the CJS preload and ESM main/window. Unavoidable across the module-system
  boundary (sandboxed preloads can't require local modules); documented with sync comments.

## Verification (macOS, local)

- typecheck ✓, 27/27 unit tests ✓, build + guard ✓
- real Electron smoke, correct preload → `main-window-created`
- broken ESM preload → guard exit 1 AND smoke `preload-error` (fails closed)
- full `pnpm package:smoke` (electron-packager + run) → `main-window-created`
