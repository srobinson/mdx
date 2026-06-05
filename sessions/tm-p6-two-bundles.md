---
title: Transport Matters P6 — two bundles, separate serving
type: sessions
tags: [frontend, transport-matters, separation, vite, fastapi, playwright, ci]
summary: Final phase of the www/ separation — per-product inspector/canvas bundles, dev-only shell, dual API mounts, dual-bundle CI/wheel, real-artifact validation (PR#193)
status: active
source: frontend-engineer
confidence: high
created: 2026-07-02
updated: 2026-07-02
---

# Summary

Shipped Phase 6 of the www/ separation plan v5 on `sep/p6-bundles` (head c26c4c0, PR#193, not merged; base ec354ba). Each product now builds its own production bundle: `@tm/inspector` → `api/src/transport_matters/www/` (base `/`), `@tm/canvas` → `api/src/transport_matters/canvas/` (base `/canvas`). The shell is dev-only and ships in no production bundle. The API serves the two bundles through `mount_frontend_bundles()`; CI, the wheel, and the release chain carry both.

# Architecture Decisions

- **Shared vite factory, not copies**: `www/vite.shared.ts` owns `resolveVersion()` and `productViteConfig({ bundleDir, base, plugins })` with the workspace-root-anchored outDir. Product configs are ~10 lines each; the shell reuses `resolveVersion` only. Lint coverage added via shell biome globs + a lefthook case.
- **Host CSS single path**: `@tm/host` exports `./styles.css` (aggregate `@import` of the two chrome sheets); components no longer self-import CSS; all three entries (shell dev, inspector, canvas) import it. Matches the spec contract; noted in memory as a deliberate exception to the css-co-location rule.
- **Canvas route fork inside the bundle**: `canvas/src/app.tsx` (`selectCanvasRoute` + lazy `SessionCanvasRoute`/`CanvasLabRoute`) because `/canvas-lab` is a live production page (RouteSwitcher, launcher goto, desktop whitelist). Lab stays a lazy chunk. Shell's three-way `selectRootRoute` untouched.
- **Serving topology**: explicit `add_api_route("/canvas")` + `("/canvas-lab")` FileResponse page routes, then `Mount("/canvas")`, then the `/` catch-all. Bare `/canvas` does not match the Mount boundary and the desktop loads exactly that path (`rendererUrlForPort`); `/canvas-lab` sits outside the mount path. Order pinned by tests.
- **Shell dev resolution**: exact-regex aliases (`/^@tm\/inspector$/` etc.) pin dev composition to `packages/*/src` entries; the `$` protects css subpath imports. Shell `vite build` now emits to local `dist/` (perf preview path intact).
- **Product tsconfigs**: mirrored the shell's solution-style shape (app + node references, `tsc -b`), so the new vite configs are typechecked.

# Performance Notes

No regressions by construction: lazy chunk boundaries preserved (lab, terminal pane, theme chunks visible in the canvas build), inspector single-chunk shape unchanged. Canvas bundle assets all under `/canvas/assets/`.

# Deviations from Spec

- Spec's "dual SpaStaticFiles" alone would break bare `/canvas` (desktop) and `/canvas-lab` (wrong SPA served). Added the two explicit page routes; flagged in the PR "Notes for review".
- Spec sketch says `import "./canvas.css"`; the real file is `src/index.css` (exports `./index.css`) — used the real path.
- New product `index.html` files omit the dead `/vite.svg` favicon link (404s today; no public dir). Shell's copy untouched.

# Incidents Resolved During Work

- Stale pre-P3 `www/node_modules` caused 416 vitest failures on clean main (duplicate React via mixed walk-up resolution) and masked `@tm/canvas` never declaring `react-dom`. Deleted the stale tree; declared the dep (commit 5dde1c9).
- 2 visual snapshot failures reproduce identically on clean main (darwin-local drift, version stamp in clip) — pre-existing, not addressed here.

# Post-Review Rounds (roadtest + CI)

- Fix round 1 (27ef129): review Minors — matrix projects register together with their preview servers (argv signal promoted to env for worker-process stability), shell README repointed. Plus Stuart's roadtest catch 1: canvas lost the Tailwind preflight it silently inherited on the shared origin (grid geometry, pane borders, `[hidden]` toggles inert). Canvas vendors the reset (`styles/reset.css`); matrix asserts the reset environment; red-proven.
- Roadtest catch 2 (91093d3): three stray Tailwind utilities inside canvas (engine PaneFrame `absolute outline-none` + `h-full`, picker `sr-only`) died standalone — panes stacked in static flow (+height offset signature), content stopped filling panes. Differential harness (same seeded state + dock-restore replan, dev shell vs built bundle) isolated it: planner identical, positioning CSS missing. Engine owns `pane-frame.css`; static Tailwind-free gate added; both red-proven. Process note: this push landed after a clean review verdict — branch-frozen rule logged.
- CI fix (9c7c4da): rootShell theme-token test asserted a layout-effect-driven global synchronously after a store write; CI's 2-core runner exposed it. `waitFor` on token assertions.

# Verification

`just check` green; `just test` green (desktop 10 files, shell 154 files / 1133 tests, api 1792 tests); `just build` green with both bundles asserted in the wheel; `tests/integration/test_static_bundles.py` 10/10 against real artifacts; Playwright matrix 3/3 (built inspector at `/`, built canvas at `/canvas`, desktop-bridge smoke); chromium e2e 22/22.

# Open Items

- PR#193 awaits review/merge (do-not-merge per brief).
- Pre-existing darwin visual snapshot drift (2 specs) worth a snapshot refresh on main.
- The `frontend-e2e` CI job now builds both products inside the matrix webServers; if CI time grows, the builds could be hoisted to explicit steps with `reuseExistingServer`.
