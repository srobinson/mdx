---
title: Transport Matters www/ Separation — Grok Architectural Review (v3)
type: review
tags: [transport-matters, www, separation, monorepo, architecture, review, phasing, build-tooling, host, shell, enforcement]
source: grok
date: 2026-07-02
---

# TM Separation Review (Grok) — v3 Proposal

**Role:** Senior software architect, honest adversarial review.  
**Primary lens:** Phasing realism and build tooling mechanics.  
**Repo:** /Users/alphab/Dev/LLM/DEV/helioy/transport-matters  
**Proposal reviewed:** ~/.mdx/projects/tm-sep-proposal.md (v3)  
**Ground truth:** live current codebase (pre any restructure). No root pnpm-workspace or root package.json. Single monolith under www/. One Vite config with relative outDir. Single FastAPI mount at /. Playwright + www/just + root just all cd into www/. main.tsx + rootShell.tsx inline the chrome + unconditional useThemeTokens + mixed CSS imports. desktop/ has its own pnpm-workspace.yaml (onlyBuiltDependencies) + standalone lock. route.ts contains all context functions. WindowDragRegion/ChannelBadge use only custom BEM CSS (no Tailwind utilities). .github/workflows/{ci.yml,release.yml} exist with www-specific working-directory / package_json_file. scripts/local-dev-mode.sh hardcodes www_dir and `cd $www_dir && pnpm dev`. api/pyproject has only `www/**` artifacts. test_static_canvas.py tests single-mount SPA fallback.

v3 incorporates prior reviews + Codex symbol-by-symbol verification. Notable improvements: dedicated `@tm/host` (neutral chrome), correct splits (parse* to canvas, not core), anchored outDir via searchForWorkspaceRoot, minimal enforcement, early chrome factoring in P1, explicit two-dir + asset-404 tests + Playwright matrix in P6, P3 mechanical vs P4 semantic separate commits, shell kept strictly dev-only with zero prod symbols.

---

## 1. Verdict on the workspace decision (closed)

**Repo-root pnpm workspace (www/packages/* + desktop) remains the right call for a solo developer.** One lockfile, one `pnpm install` at root, `just` continues to own cross-language orchestration. No Turborepo/Nx.

v3 adds `@tm/host` as a first-class peer package (beside core/inspector/canvas/shell). This is the correct placement for presentation-neutral but still DOM chrome (WindowDragRegion, ChannelBadge, mount logic, desktopHost). Core contract correctly excludes CSS/presentation.

**Desktop as workspace member** is accepted (unifies the install story). Tradeoff: desktop's special electron needs (onlyBuiltDependencies) move to root package.json; its local pnpm-workspace.yaml and lock are deleted. Feasible but non-zero mechanical work in P3.

The nesting `www/packages/{core,host,inspector,canvas,shell}` under a workspace root that is the repo root is workable but will require discipline around the "www/" name (source container vs old single package vs the built artifact dir in api/).

Overall: decision is sound. v3's refinements (host, minimal enforcement) make the shape cleaner than v2.

---

## 2. Stress-test of the v3 phased plan

Every phase must leave a **working, user-testable app**. api.ts and index.css cut once. P3/P4 are deliberately split commits.

### Phase 1 — Groom + early host factoring (in place)
**Strong, and improved.**

- Standard renames, desktopHost seam, store unification, hook dedup, dead class prune.
- **New and good:** Factor neutral chrome *before* the big moves: consolidate `WindowDragRegion` + body-prepend + `ChannelBadge` + `desktopHost` into `src/host/mountWindowChrome()`. Neutralize any Tailwind (current evidence: WindowDragRegion and ChannelBadge already use only custom classNames + their own .css; no Tailwind utilities visible). Update the single main.tsx to call `mountWindowChrome()`. Move `useThemeTokens` concern out of rootShell into canvas later.
- Add real `session-canvas` import-graph boundary test for the ExchangeDetail breach.
- Flag the stale consensus doc.

**Mechanics check:** Moving chrome files inside the monolith first is low blast. Imports updated in place. Tests for WindowDragRegion already exist and inject `desktop` prop.

**User test:** Explicitly includes "titlebar drag + channel badge intact". Real and complete.

Risk low. Rollback trivial.

**Note on useMeta in ChannelBadge:** Currently `ChannelBadge` calls `useMeta`. Proposal puts `useMeta` in core. If host imports core, this is fine (host is allowed to depend on core). Verify in the groom that host does not pull inspector stores.

### Phase 2 — Sever the leak
**Solid.**

- Add ArkExchangeViewer with render contract + visual snapshot + **tab-mapping test** (explicit `toDetailTab` cases).
- Repoint callers, drop the import, flip boundary test to enforce.

Current breach confirmed: `ProviderExchangeResourceViewer.tsx` imports from `../../../components/ExchangeDetail`.

User test is precise and testable. Canvas zero-Tailwind after this (verified by reviewer that canvas uses BEM only).

Good guardrails. Risk is implementation effort of the viewer, not the plan.

### Phase 3 — Scaffold repo-root workspace (mechanical commit only)
**The plan has learned from prior reviews.**

Key mechanics in proposal:
- Root `pnpm-workspace.yaml` (members `www/packages/*`, `desktop`).
- Root `package.json` + single lock (delete sub locks + desktop's pnpm-workspace.yaml; move onlyBuiltDependencies to root).
- `git mv` current app content into `packages/shell/` (under www/); relocate `src/host/` → `packages/host`; create core/inspector/canvas skeletons.
- **Critical fix:** Anchor outDir with `path.resolve(searchForWorkspaceRoot(process.cwd()), "api/src/transport_matters/www")` (and same for canvas). No more manual `../` counting. Current vite.config has `outDir: "../api/src/transport_matters/www"`.
- Update *everything*:
  - All CI jobs in `.github/workflows/{ci.yml,release.yml}` (working-directory, package_json_file, cache-dependency-path to root lock, use `--filter` where needed).
  - Scripts: local-dev-mode.sh (currently hardcodes `www_dir="$repo_root/www"` + `cd $www_dir && pnpm dev`), release.sh.
  - justfiles (root changes from `cd www && just` / `cd desktop && pnpm`; define `just www dev` → shell filter).
  - playwright.config.ts (webServer command + later matrix).
  - tsconfigs, biome, vitest include, test_type_mirrors.py, install-local, visual fixtures.
- Gate: **fresh-clone `just check && just test && just build`**.

**Reality check against current code:**
- Root justfile does exactly `cd "{{www_dir}}" && just {{args}}` and same for desktop + parallel test/check.
- www/playwright.config hardcodes `"pnpm dev ..."` and `"pnpm build && pnpm preview"` (executed from www context).
- local-dev-mode.sh has `www_dir=.../www` and `cd $(shell_quote "$www_dir") && ... pnpm dev`.
- CI has `working-directory: www`, `package_json_file: www/package.json`.
- Desktop has its own pnpm-workspace.yaml.
- No root package.json/lock yet.

The checklist is now comprehensive. Using `searchForWorkspaceRoot` is the right engineering answer to the relative-path problem I flagged before.

**Remaining mechanical risks (even with checklist):**
- The `www/packages/...` nesting means "www/" continues to exist as a directory after the move. Scripts/docs/mental model that treat "www/" as "the web app package root" will need ongoing translation.
- "git mv the whole app" + relocate host means a large number of relative imports, CSS @imports, test paths, and alias uses must be updated in the same mechanical commit.
- Shell's own vite.config + index.html will live under the new tree; its dev command will be the one used for the transitional single-bundle experience.
- Desktop clean script change ("no lock to rimraf") is small but real.

**User test** ("web + desktop pixel-identical") is credible **only if** the fresh-clone gate passes. Good that the gate is mandatory.

P3/P4 split into separate commits is excellent discipline (mechanical layout first, then semantic extraction).

Rollback: revert the commit.

### Phase 4 — Extract core (cut api.ts once; semantic commit)
**Clearer boundaries than v2.**

- Core gets transport + singleton queryClient + queryKeys + useMeta + neutral fetchers + **store-free stream primitive** (parsers + `StreamSideEffects` callback port) + formatting + agentPalette + `createFrontendPersistStorage` helper + neutral keybinding primitive (`platform`/`format`/types) + explicit type entrypoints.
- Inspector wires the uiStore effects into the callback port.
- Inspector `keymapStore`/`useFullscreen` bind only the *core* primitive (not canvas engine).
- Canvas keeps its keybinding *engine* (gestures etc.) + `parseCanvasLaunchContext`/`defaultCanvasId` (split out of route.ts; selectRootRoute stays in shell).
- lib/ table is explicit and importer-verified.

**Gate added:** "core stream + keybinding code has zero imports from `stores/`; core does not know product store names."

Current code supports the split: queryClient is a plain singleton; formatting/agentPalette are cross-used; keybindings/platform uses desktopHost (moving to host); some keybinding files already import from stores (those stay inspector or canvas).

`api.ts` cut once.

`test_type_mirrors.py` updated same commit.

User test real (pause/forward semantics must survive the port redesign).

Risk medium (subtle wiring bugs in stream). Guard is good.

### Phase 5 — Split products under shell (cut index.css once)
**Peers + host + dev-only shell is now crisp.**

- Inspector tree (including Toggle, icons, TransportMattersIcon, its stores, override logic, keymapStore bound to core primitive).
- Canvas tree (including its engine + the context parsers split from route.ts).
- Shell shrinks to thin composer: main.tsx, rootShell with **neutralized non-Tailwind Suspense fallback**, selectRootRoute. Zero Tailwind symbols, zero production-imported symbols.
- Host is the neutral chrome peer.
- index.css partitioned once (inspector keeps Tailwind @theme; canvas copies values).
- Enforcement (exports "." + import-graph test) goes green.

**User test** includes import-graph + exports gate.

**One subtle area:** In the transitional single-bundle P5 world, the shell dev server must be able to render either product route. rootShell currently always calls useThemeTokens(). Proposal says neutralized fallback in shell. You will likely need conditional logic or move the hook call inside the canvas lazy route component. Current rootShell.test and unconditional call mean this must be changed in P5.

Also, both product CSS will be in play during the single-bundle phase after the cut.

Risk acceptable with the gates.

### Phase 6 — Two bundles + separate serving
**Best-specified phase yet.**

- Inspector + canvas each get independent `index.html` + `main.tsx` + `vite.config`.
  - Each imports *only its own CSS*.
  - Each calls `@tm/host` `mountWindowChrome()`.
  - Each wraps `QueryClientProvider` with the core `queryClient`.
  - Canvas sets `base: "/canvas"`.
- Shell is dev-only.
- FastAPI: mount `/canvas` (SpaStaticFiles on its dir) then `/` (catch-all).
- pyproject artifacts add `canvas/**`.
- CI + install-local + channel-restart build *both*.
- **Validation added:** two-directory built artifacts + two-bundle static integration test (replace/update test_static_canvas.py) + explicit **asset-404 regression** (`/assets/foo.js` must 404, not serve wrong index) + **Playwright matrix** (inspector at `/`, canvas at `/canvas` with base handling, desktop smoke).
- Desktop loadURL remains `/canvas` (already the default) — verification only.

**Two-bundle dev story** (to write before P6): `just www dev` → shell; per-product `--filter` dev; desktop builds both.

**Mechanics realism check:**
- Current api/main.py has one mount at `/`. Dual mount with order (specific first) + separate directories is straightforward but the SPA fallback logic (`_looks_like_asset_path`, 404 → index.html) must be per-mount or the mount must not leak.
- Vite `base: "/canvas"` makes the canvas bundle emit asset references under `/canvas/assets/...`. The FastAPI mount("/canvas", directory=canvas_dir) must deliver those assets correctly (Starlette mount strips the prefix, so the directory should contain the assets/ subdir as emitted).
- Shell dev resolution: "aliases to packages/*/src + server.fs.allow workspace root". This is needed so that in dev you can still get the composed experience without building the product bundles separately every time. Vite supports it but the config (in the shell package's vite.config or a shared one) must be written carefully so prod builds of inspector/canvas do not accidentally resolve shell or each other.
- Per-product main.tsx will duplicate some boilerplate (StrictMode, QueryClientProvider, mountWindowChrome call, root render). Acceptable for isolation.

**User test** is now the strongest: explicit canvas chrome, titlebar, Ark viewer, separate breakpoint behavior, asset isolation.

Rollback to P5 single-shell state (working by construction).

---

## 3. Findings by severity

### Blockers
- **None hard blockers**, but the following are close if not executed exactly:
  - P3 outDir anchoring must actually use `searchForWorkspaceRoot` (or equivalent) and be validated on fresh clone. Current code uses simple relative; the proposal now prescribes the correct tool.
  - P6 dual-mount + base asset delivery + two-dir test must be proven with real built artifacts, not just unit fakes. Current `test_static_canvas.py` only does single-mount tmp_path.

### Major
- **P3 scope (mechanical but large):** Root workspace + nesting under www/packages + deletion of sub locks + updates to two CI workflows, two scripts, both justfiles, playwright, all ts/biome/vitest configs, desktop clean, local-dev-mode paths, release paths. Even with the excellent checklist, this is a high-churn commit. The "mechanical only" discipline (no behavior changes mixed in) is mandatory.
- **Shell dev resolution and P5/P6 dev story (proposal §5 Phase 6 + §6):** The lazy product route resolution for shell dev is underspecified in implementation detail. It must be written and tested *before* P6. Per-product standalone dev servers must also work cleanly.
- **Theme/CSS isolation in transitional P5 (rootShell + index.css cut):** useThemeTokens currently unconditional in rootShell. Separate token sets + single bundle in P5 means either both CSS files are loaded or conditional application. Proposal says shell rootShell gets neutralized fallback — this must be implemented and the effect verified (inspector route does not pick up canvas vars and vice versa).
- **CI files exist and are www-centric (`.github/workflows/ci.yml`, `release.yml`):** Proposal correctly calls for updates to cache paths, package_json_file, working-directory or filter usage. These changes must land in P3. Current frontend job cds to www and references www/package.json.

### Minor
- Name collision / mental model: "www/" will mean three things after P3 (the directory containing packages/, the old single package, and the built inspector dir under api/). Document the mapping.
- Host package CSS: window-drag-region.css and channel-badge.css must be co-located and imported correctly from the host package in both dev and prod bundles.
- No browserIdentity (proposal correctly drops the non-existent module).
- Stale `tm-ui-sep-consensus.md` is flagged — good.
- Desktop membership: its vitest config, tsconfig etc. must continue to work when pnpm is driven from root workspace.

---

## 4. Misses or better sequencing

**What v3 gets right (credit):**
- Host as separate neutral package (directly addressed prior chrome concern).
- Correct symbol homes (route parsers to canvas, icons to inspector, keybinding engine vs primitive, etc.) with verification notes.
- Anchored outDir instead of relative counting.
- Minimal enforcement (exports + the existing vitest gate; cruiser optional).
- Early factoring of chrome in P1.
- P3/P4 commit split.
- Concrete two-bundle validation artifacts (two-dir test + asset-404 + Playwright matrix).
- "Desktop = verification" framing.
- Explicit two-bundle dev+test story requirement.

**Remaining gaps / suggestions:**

1. **Explicit per-product main.tsx sketches before P5.** Show the two main.tsx files side-by-side (inspector vs canvas) and the host call site. Include where the route-specific prefetch logic lives (currently only for legacy in main.tsx).

2. **P5 transitional shell rootShell theme handling.** Add a concrete change or test in the plan: in shell mode, the canvas route component (or its entry) is responsible for calling useThemeTokens; inspector route must not. Verify no var leakage.

3. **Host package public surface.** Since host will be imported by prod bundles, its package.json "exports" and how CSS is handled (side-effect import or explicit) should be sketched in P3 or P5.

4. **Playwright matrix implementation detail.** Current config is single webServer. The matrix will likely require either env-driven command selection or two separate preview servers on different ports + baseURL per project. Write the shape before P6.

5. **local-dev-mode.sh and "just www dev".** After root workspace, the command that used to be "cd www && pnpm dev" becomes a filtered shell dev. The script also discovers ports and splits tmux for backend + web. It will need to invoke the correct filtered dev (or the shell package) and set DEV_API_BASE_URL. Add to the P3 checklist explicitly.

6. **Asset path verification in dual mount.** Add a tiny assertion in the new static test that canvas assets are served under the expected path when base is set (or confirm the mount + emitted paths).

7. **Consider a tiny shared "chrome host" test util** that both prod mains and the shell dev can use for the prepend logic, to avoid any duplication of the body-prepend pattern.

8. **Enforcement in CI.** The vitest import-graph test must run in the frontend job after P1. If it lives inside the shell or a root test, make sure the CI matrix (which currently has a www-specific frontend job) still executes it after the layout change.

**Sequencing recommendation (tighten risk):**
- P1: Do the host factoring + import-graph test + any neutralization + update main.tsx call site. Run full user test including drag/ badge.
- After P1 lands cleanly, do a small spike on "shell dev with sibling package imports" (even with the old monolith temporarily copied) so the P3 layout change is not also the first time the resolution is tried.
- P3 mechanical only.
- P4 semantic.
- Before starting P6, implement and land the two-bundle dev+test story (including updated playwright matrix and the two-dir static + asset-404 tests). Then the final cut is smaller.

---

## Summary

v3 is the most disciplined and self-correcting version yet. It directly fixed the chrome placement, the route split mistakes, the outDir fragility, the enforcement overkill, and the validation gaps from earlier reviews.

The plan is realistic for a solo developer provided the mechanical discipline of P3 (fresh-clone gate, no behavior changes) is respected and the dev resolution + transitional theme story for the shell are prototyped early.

Primary remaining execution risks are in the P3 layout blast radius (many files, CI + scripts) and the P5/P6 dev experience for the composed vs standalone modes.

**Recommendation:** Execute. The structure (core + host + peers + dev-only shell) is clean. The phasing with explicit gates and the two-bundle validation requirements are senior-level. Get P1 done, prove the shell dev resolution works with the new package layout, then do the mechanical P3 commit.

The result should be maintainable separate products that still give a unified dev experience via the shell.

---

**End of review.** Grounded in the actual files and structure present on 2026-07-02.