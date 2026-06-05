# Canvas PR 2 Review — Retire the Lab

**PR:** #208 · branch `refactor/canvas-retire-lab` · HEAD `43b01b3` (parent `d67e4c1`, PR 1 merged)
**Scope audited:** Task 7 (Retire the Lab) / "PR 2" slice of `docs/superpowers/plans/2026-07-05-canvas-repo-reset.md`
**Diff:** +67/-3969 across 51 files (deliberate cross-package deletion)
**Reviewer:** transport-matters:general:2:7.2 (adversarial, read-only, tree untouched)
**Date:** 2026-07-05

## Verdict: **PASS** — 0 blockers / 0 majors / 0 minors

A clean deletion. It removes the lab and only the lab; `/canvas` behavior, its
route, and its bundle output path are unchanged. Every claim verified first-hand
(grep, file reads, vitest, pytest, production build). No working-tree mutation:
`git status` clean; the build output dir is gitignored.

Evidence of green:
- `pnpm exec vitest run sessionCanvasBoundary route rootShell commandModel app RouteSwitcher storageKeys window` → **121 passed** (12 files).
- `pytest test_static_bundles.py cli/test_desktop.py` → **40 passed**.
- `pnpm --filter @tm/canvas build` (tsc -b + vite) → **built**, 862 modules, no lab chunk, output at `api/src/transport_matters/canvas/` base `/canvas`.

---

## Audit findings (five points, hardest first)

### 1. Zero live `canvas-lab` references, honestly — PASS

Ran the plan's exact grep: `rg -n "canvas-lab|CanvasLab|canvasLab" --glob '!**/.archive/**'
--glob '!**/canvas/assets/**' --glob '!docs/superpowers/**' .` → **exit 1, zero matches.**

The excludes hide nothing real, verified by grepping *without* them:
- The only tracked file in the entire repo containing any `canvas-lab` token is
  `docs/superpowers/plans/2026-07-05-canvas-repo-reset.md` (the plan doc itself,
  legitimately describing the retirement). Excluding `docs/superpowers/` is correct.
- `.archive/**`: zero matches (`rg --no-ignore --glob '**/.archive/**'` empty).
- `canvas/assets/**`: zero tracked files (`git ls-files` count 0); the built bundle is
  generated, gitignored, not committed. Legitimate exclude.

### 2. `RouteSwitcher.tsx` kept and wired — PASS

- File present; `navigateToRoute` still exported.
- `components/CanvasSurface.tsx` still `import { navigateToRoute } from "./RouteSwitcher"`
  and calls `navigateToRoute(command.path)`; the whole package compiles (build passed).
- Only the `/canvas-lab` entry removed from `CANVAS_ROUTES` (now `[{ id: "canvas" }]`).
- Single-option toggle affordance removed via a `if (routes.length <= 1) return null;`
  guard in `RouteSwitcher` — the visible switcher renders nothing with one route, while
  the component and `navigateToRoute` survive for PR 5 relocation. Clean, minimal.
- `RouteSwitcher.test.tsx` present, trimmed of lab cases (test suite green).
- File is NOT deleted. Correct.

### 3. Paired deletions, harness kept — PASS

- `components/SceneParamControls.tsx` **and** `SceneParamControls.test.tsx` both deleted
  together — no dangling import, confirmed by a clean `tsc -b` in the build.
- `shell/src/testSupport/labBoundary.test.ts` deleted (its sole purpose was policing the
  now-gone lab boundary).
- `shell/src/testSupport/importGraph.ts` and `importGraphBoundary.test.ts` both present
  and intact (lab-independent; still back the inspector/canvas boundary tests).

### 4. No collateral damage; api/desktop reconciled — PASS

`/canvas` route and bundle output path unchanged:
- `main.py` `mount_frontend_bundles`: removed only the `/canvas-lab` `add_api_route`;
  kept the `/canvas` route, the `SpaStaticFiles` mount, and the mount-order invariant
  (canvas mount before the `/` catch-all). `canvas_page` handler retained for `/canvas`.
- `test_static_bundles.py`: removed only `test_canvas_lab_serves_the_canvas_bundle`;
  `test_canvas_subpath_falls_back_to_the_canvas_spa` and `test_the_two_bundles_are_distinct`
  (still asserts `"/canvas/assets/" in canvas_index()`) retained — bundle path pinned.

Route-name surface narrowed consistently to `Literal["canvas"]` everywhere:
- `desktop_runtime.py`, `cli/desktop_cmd.py`, `cli/desktop_launch_config.py`
  (`normalize_desktop_route` now rejects anything but `"canvas"`).
- `cli/test_desktop.py`: removed only `test_desktop_route_flag_targets_canvas_lab` and
  its now-unused `Callable` import.
- `desktop/src/window.ts` `allowedHostedPath`: drops `/canvas-lab`, keeps `/` and
  `/canvas`; `window.test.ts` trimmed accordingly (green).
- `shell/src/route.ts` `RootRoute` + `selectRootRoute`, `shell/src/rootShell.tsx`
  route map, `app.tsx` (collapsed to a single `<SessionCanvasRoute />`, removed
  `selectCanvasRoute`/`CanvasLabRoute` lazy/`useMemo`), `index.ts` (removed
  `CanvasLabRoute` export) — all consistent.

### 5. Scope: deletion + trims only — PASS

No PR 3 / PR 4 / PR 5 bleed:
- `model/canvasStore.ts` NOT touched (no store split — PR 3).
- `components/CanvasSurface.tsx` only its `RouteSwitcher` usage remains; NOT decomposed
  (no workbench move — PR 5).
- `dnd/useCanvasDropTargets.ts`: comment-only trim (removed the `/canvas-lab stage`
  mention); the `pasteRegistry` seam is untouched — NOT the PR 4 change.
- `launcher/commandModel.ts`: removed only the `goto /canvas-lab` row from
  `buildCanvasRows`; no file split — NOT the PR 6 launcher decomposition.
- `AmbientBackdrop.tsx`, `canvas.css`, `vite.config.ts`, `storageKeys.ts`,
  `shell/README.md`, `TLDR.md`, `www/packages/canvas/CLAUDE.md`: comment / stale-ref /
  storage-key trims only.

---

## Verification note

The canvas build writes into the gitignored `api/src/transport_matters/canvas/` output
dir (0 tracked files); `git status` is clean after the review. The shared working tree
was left untouched — no branch switch, no temp files, read-only throughout.
