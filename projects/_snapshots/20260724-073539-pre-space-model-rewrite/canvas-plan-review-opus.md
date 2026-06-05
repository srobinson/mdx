# Canvas Repo Reset Plan — Review (Opus 4.8)

**Target:** `docs/superpowers/plans/2026-07-05-canvas-repo-reset.md`
**Cross-checked against:** working tree (pristine, `git status` clean at `3d658e6`) and scout `~/.mdx/projects/canvas-reset-scout-pr1.md`.
**Method:** read-only. Every path/symbol below verified against the live tree. Citations use path + symbol (never line numbers).

**Verdict: conditional.** The plan's factual base is strong (all Task 2 symbols, imports, LOC, folder counts, and the vitest command claim check out; boundary scoping is sound). But the lab-retirement map (Task 7 / PR 2) has one build-breaking omission, one mischaracterized product-code dependency, and a verification command that is blind to the very docs it prescribes trimming. These should be fixed before PR 2 ships.

---

## Blocker

### B1. `SceneParamControls.test.tsx` is omitted from the deletion map → dangling import, build break

Task 7 deletes `session-canvas/components/SceneParamControls.tsx` (it has no non-lab caller: only `lab/CanvasLabRoute.tsx` imports it, so the "delete unless a non-lab caller is found" condition resolves to delete). The forward-removal map lists `RouteSwitcher.tsx + RouteSwitcher.test.tsx + SceneParamControls.tsx` but **omits `session-canvas/components/SceneParamControls.test.tsx`**, which imports and renders `SceneParamControls` (symbol `SceneParamControls`, imported from `./SceneParamControls`).

Deleting the component without its test leaves a test importing a deleted module. PR 2's own verification runs `pnpm --filter @tm/canvas build` and `typecheck`, both of which fail on the unresolved import. The map is labelled "verified 2026-07-05 by repo-wide grep," but a grep for `canvas-lab` cannot catch this file because it contains no `canvas-lab` string; it breaks only by transitive deletion.

**Fix:** add `session-canvas/components/SceneParamControls.test.tsx` to the delete list.

---

## Major

### M1. `RouteSwitcher.tsx` has a live non-lab caller; Task 5 and Task 7 contradict each other on it

Task 5 (Move map) states categorically: "`RouteSwitcher.tsx` and `SceneParamControls.tsx` are deleted in PR 2 with the lab; **do not move them**." Task 7 hedges the same deletion: "delete it ... **unless a non-lab caller is found**. Verify before deleting."

The non-lab caller exists. `session-canvas/components/CanvasSurface.tsx` (the product surface that Task 5 renames to `workbench/CanvasWorkbench.tsx`) imports `navigateToRoute` from `./RouteSwitcher` and calls it in the command handler (`navigateToRoute(command.path)`). `RouteSwitcher.tsx` exports `navigateToRoute` as generic navigation infrastructure (`export function navigateToRoute(path: string)`), independent of the lab. So the plan's premise "RouteSwitcher exists only to toggle `/canvas` ↔ `/canvas-lab`" is factually wrong, and deleting `RouteSwitcher.tsx` outright breaks `CanvasSurface.tsx`'s import.

Because CanvasSurface still imports `navigateToRoute` throughout PR 2 (its command handler does not move until PR 5), following Task 5's categorical "deleted ... do not move them" is build-breaking within PR 2 itself.

**Fix:** reconcile Task 5 with Task 7. The correct action is keep `navigateToRoute` (keep `RouteSwitcher.tsx`, or extract `navigateToRoute` to a route helper) and remove only the `/canvas-lab` entry from `CANVAS_ROUTES` plus the toggle UI. Delete `SceneParamControls` (no non-lab caller) but not `RouteSwitcher.tsx`.

### M2. PR 2 / Task 7 verification `rg ... www api desktop` cannot confirm the repo-root doc trims the map prescribes

The removal map prescribes trimming `TLDR.md` and "the WWW-workspace-naming note in the repo `CLAUDE.md`." Both live at the repository root and both currently contain `/canvas-lab` (`TLDR.md`, symbol: the `api/src/transport_matters/canvas/` bundle note; root `CLAUDE.md`, same note under "WWW workspace naming").

The PR 2 / Task 7 verification command is scoped to `www api desktop`:

```
rg -n "canvas-lab|CanvasLab|canvasLab" --glob '!**/.archive/**' www api desktop
```

That path list never scans repo-root files (`TLDR.md`, root `CLAUDE.md`) or `docs/`. An executor who forgets those two doc trims still gets a green rg and a false "zero live references." Task 7's own step 4 ("Grep **the repo** for `canvas-lab` ... confirm zero remaining references") is inconsistent with this narrower verification command.

**Fix:** scope the verification to the repo root (e.g. `rg -n "canvas-lab|CanvasLab|canvasLab" --glob '!**/.archive/**' --glob '!**/canvas/assets/**' .`) or add `TLDR.md` and the root `CLAUDE.md` to the scanned set. See also m1 for the built-bundle interaction.

---

## Minor

### m1. The PR 2 rg command, run as written, reports the gitignored built bundle → non-deterministic zero-reference gate

The built canvas bundle at `api/src/transport_matters/canvas/` is gitignored (`.gitignore`: `api/src/transport_matters/canvas/`), not committed. But run **verbatim**, the command lists 5 generated asset files as `canvas-lab` matches:

- `api/src/transport_matters/canvas/assets/CanvasLabRoute-BZqUGcRU.js`
- `api/src/transport_matters/canvas/assets/CanvasLabRoute-DsrHxi64.css`
- `api/src/transport_matters/canvas/assets/RouteSwitcher-DKLNu6MA.js`
- `api/src/transport_matters/canvas/assets/SessionCanvasRoute-BtTos0Ln.js`
- `api/src/transport_matters/canvas/assets/index-B1NFKwFH.js`

This is order-sensitive ripgrep behavior with the multi-path + `--glob` form: `... www api desktop` yields 5 asset hits, while `api` alone, `api` last, or without `--glob` yields 0 (all verified). So the same command returns 5 or 0 depending on argument order and whether a build is present, and the rg runs before the block's own `pnpm build`. "Expected: zero live canvas-lab references" is therefore not reliably met on a built tree, and the map never excludes the built bundle.

**Fix:** exclude the bundle explicitly (`--glob '!**/canvas/assets/**'`) or run against tracked files only (`git grep`). This also resolves M2's scoping cleanly.

### m2. `session-canvas/canvas.css` carries a stale lab comment the "trim comments" list misses

Task 7's stale-comment trim list names `dnd/useCanvasDropTargets.ts`, `components/AmbientBackdrop.tsx`, and `vite.config.ts`. It omits `session-canvas/canvas.css`, which contains a comment referencing `lab/canvas-lab.css (imported by CanvasLabRoute.tsx)`. The map claims to cover every reference; this one survives PR 2 as written.

**Fix:** add `session-canvas/canvas.css` to the comment-trim list.

---

## Nits (not counted)

- **Task 0 verification wording.** `git diff --check -- ...OWNERSHIP.md` checks for whitespace errors and conflict markers, not "docs only, no code behavior change" as the Expected line claims. The command does not verify the stated expectation.
- **Slice numbering.** Slice labels 1–4 map to PRs 1, 3, 4, 5; PR 2 (lab), PR 6, PR 7, PR 8 carry no slice number. Coherent if intentional (slices are the original consensus's four moves), but the numbering no longer tracks PR order.

---

## Verified correct (the five axes)

**Axis 1 — Fact accuracy: PASS.** Every cited path/symbol exists.
- Task 2 move-list, all declared in `viewers/registry.tsx`: `PICKER_PANE_ID`, `TRANSCRIPT_PANE_PREFIX`, `SUBAGENT_PANE_PREFIX`, `RESOURCE_PANE_PREFIX`, `EXCHANGE_PANE_PREFIX`, `resourceRefTitle`, `paneIdForRef`, `titleForRef`, `viewerIdForRef`.
- Keep-list, all present in `viewers/registry.tsx`: `defineViewer`, `registry` (`const registry: ViewerRegistration[]`), `resolveViewer`, `bodyDragForRef`, `renderPaneContent`, `PaneShell`; `registerViewer` present and confirmed dead (no callers in canvas/shell/host/inspector/packages).
- `model/paneRecords.ts` exports `harnessLabel` and `locatorTail` (reuse target, not duplicated). Its `ViewerRegistration.render` returns `React.ReactNode` (a type, no `react` import), matching the deferral rationale.
- `PaneRecord.viewerId` is written by `model/spawn.ts` `createPaneRecord` (`viewerId: viewerIdForRef(ref)`).
- All named model→viewers imports exist exactly as stated: `canvasStore.ts` (`PICKER_PANE_ID, paneIdForRef, titleForRef`), `spawn.ts` (`paneIdForRef, viewerIdForRef`), `canvasStore.persistence.ts` (`titleForRef`), `CanvasSurface.tsx` (`bodyDragForRef, PICKER_PANE_ID, renderPaneContent`), `PaneDock.tsx` (`titleForRef`).
- All LOC claims exact (720/717/594/572/503/500/470/389). All folder counts exact (viewers 58, components 30, model 20, dnd 19, launcher 17, lab 18). session-canvas total 196 TS/TSX/CSS; lab 18. `browserIdentity.test.ts` (PR 8 gate) exists; `rootShell.test.tsx` and `route.test.ts` (PR 2 gate) exist.

**Axis 2 — Verification commands: PASS on the central claim.** Empirically confirmed: the quoted-pipe form `vitest list "paneRecords|canvasStore|registry"` collects zero tests; the space-separated form `vitest list paneRecords canvasStore registry` collects real tests (`canvasStore.test.ts`, `registry.test.ts`, `paneRecords.test.ts`, `canvasStore.persistence.test.ts`, plus `engine/layout/registry.test.ts` via the broad `registry` substring) and exits 0. PR 1's `paneIdentity`/`sessionCanvasBoundary` filters resolve after PR 1 creates those files. (Command scoping caveats captured in M2/m1; note the bare `registry` filter over-collects the non-session-canvas `engine/layout/registry.test.ts`, harmless.)

**Axis 3 — Lab retirement: mostly complete, three gaps above (B1, m2, and the RouteSwitcher characterization in M1).** Confirmed sound elsewhere: deleting `labBoundary.test.ts` leaves `importGraph.ts` and `importGraphBoundary.test.ts` intact (neither references lab). The dnd→`viewers/terminal/pasteRegistry` leak is real (Task 4 target). Every api/desktop breaker is named in the map: `test_static_bundles.py`, `cli/test_desktop.py`, `desktop_runtime.py`, `desktop_cmd.py`, `desktop_launch_config.py`, `desktop/src/window.test.ts`, plus `storageKeys.test.ts`, `app.test.ts`, `route.test.ts`. Every repo-wide `canvas-lab` source site maps to a removal entry **except** `canvas.css` (m2) and the doc-scope/bundle issues (M2, m1).

**Axis 4 — Internal consistency: PASS.** PR renumbering (1–8) is coherent; every cross-reference resolves ("PR 2" for lab, "PR 5" for the runtime seam and CanvasSurface decomposition, "Task 8a and PR 5"). No orphan pointer to the old "Task 7: Demote Lab" (the only "demote" mention is the replacement note). Non-Goals, Acceptance Criteria, Target Mental Model, Target Source Shape, and Dependency Direction are all reconciled with the lab removal and PR-1 rule scoping. (Slice-numbering nit above.)

**Axis 5 — Boundary scoping: PASS, and the deferrals are justified.** PR 1 can make exactly `model !-> viewers` and `persistence !-> viewers` green: the only model→viewers imports are the three production files plus `paneRecords.test.ts` and `canvasStore.test.ts`, all repointed by Task 2; the `persistence/` folder already imports no viewers (rule is a vacuously-green forward guard). Deferring `model !-> React/Zustand` is correct: `canvasStore.ts` and `capturedRunStore.ts` both legitimately `import { create } from "zustand"`, and `paneRecords.ts`'s `React.ReactNode` return type is a type-only coupling an import-graph test cannot see.
