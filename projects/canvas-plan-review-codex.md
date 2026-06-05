# Canvas Plan Review

Worktree status before verdict: pristine. `git status --short` returned no output before review and again after Vitest spot checks.

## Major

### Task 7 misses committed built canvas bundle artifacts, and its verification order catches them before the planned rebuild

Fact: `api/src/transport_matters/canvas/assets/index-B1NFKwFH.js` still references `CanvasLabRoute`, the `/canvas-lab` route selector, and `canvasLabStore`. `api/src/transport_matters/canvas/assets/CanvasLabRoute-BZqUGcRU.js` and `api/src/transport_matters/canvas/assets/CanvasLabRoute-DsrHxi64.css` are committed lab chunks. Task 7's forward-removal map does not name the built bundle assets, while PR 2's required verification runs `rg "canvas-lab|CanvasLab|canvasLab" ... www api desktop` before `pnpm --filter @tm/canvas build`.

Why it matters: as written, PR 2 either fails its first grep because stale built assets remain under `api`, or a worker has to infer an unlisted step. `www/vite.shared.ts` `productViteConfig` writes the canvas bundle to `api/src/transport_matters/canvas` with `emptyOutDir: true`, so the plan should explicitly run the canvas build before the zero-reference grep, or explicitly include the generated bundle refresh/deletion in the removal map.

Evidence: `api/src/transport_matters/canvas/assets/index-B1NFKwFH.js` `CanvasLabRoute`; `api/src/transport_matters/canvas/assets/CanvasLabRoute-BZqUGcRU.js` `CanvasLabRoute`; `www/vite.shared.ts` `productViteConfig`.

### Task 7 says `RouteSwitcher.tsx` can be deleted, but `CanvasSurface.tsx` still imports a non-lab export from that module

Fact: `www/packages/canvas/src/session-canvas/components/CanvasSurface.tsx` imports `navigateToRoute` from `www/packages/canvas/src/session-canvas/components/RouteSwitcher.tsx` inside `useCanvasCommandHandler`. The `RouteSwitcher.tsx` module exports both the lab-facing `RouteSwitcher` component and the non-component `navigateToRoute` helper. Task 5 says `RouteSwitcher.tsx` is deleted in PR 2, while Task 7 only asks workers to confirm `RouteSwitcher` and `SceneParamControls` callers.

Why it matters: deleting the file after checking only the component caller breaks the current `CanvasSurface.tsx` import. If the lab retirement also removes the launcher `goto` command path, the plan should say to remove that command branch and the helper import. If a route navigation helper remains useful, move it to `session-canvas/route.ts` or another non-lab owner before deleting the component module.

Evidence: `www/packages/canvas/src/session-canvas/components/CanvasSurface.tsx` `useCanvasCommandHandler`; `www/packages/canvas/src/session-canvas/components/RouteSwitcher.tsx` `navigateToRoute`; `www/packages/canvas/src/session-canvas/launcher/commandModel.ts` `goto`.

## Minor

### Task 7's live-reference map is not complete for source comments and docs verification

Fact: `www/packages/canvas/src/session-canvas/canvas.css` still references `lab/canvas-lab.css` and `CanvasLabRoute.tsx`, but Task 7's comment-trim list names only `useCanvasDropTargets.ts`, `AmbientBackdrop.tsx`, and `www/packages/canvas/vite.config.ts`. The plan also says PR 2 trims docs, but the zero-reference verification greps only `www api desktop`, so root docs such as `TLDR.md` and `CLAUDE.md` are outside the actual check.

Why it matters: this is smaller than the built-bundle issue because the final grep over `www` would catch `canvas.css`, but the brief asked for a forward-removal map that covers every live reference. The docs omission means a worker can satisfy the listed verification while leaving `/canvas-lab` in project docs.

Evidence: `www/packages/canvas/src/session-canvas/canvas.css` `lab/canvas-lab.css`; `TLDR.md` `WWW workspace naming`; `CLAUDE.md` `WWW workspace naming`.

## Verified Clean Points

- Task 2 identity facts are accurate: `PICKER_PANE_ID`, the pane prefix constants, `resourceRefTitle`, `paneIdForRef`, `titleForRef`, and `viewerIdForRef` exist in `www/packages/canvas/src/session-canvas/viewers/registry.tsx`; `harnessLabel` and `locatorTail` exist in `www/packages/canvas/src/session-canvas/model/paneRecords.ts`; `createPaneRecord` in `www/packages/canvas/src/session-canvas/model/spawn.ts` writes `PaneRecord.viewerId`.
- The space-separated Vitest form works. From `www/packages/shell`, `pnpm exec vitest run paneRecords paneIdentity canvasStore registry sessionCanvasBoundary` exited 0 with 7 files and 75 tests. `pnpm exec vitest run sessionCanvasBoundary route rootShell` exited 0 with 10 files and 68 tests, with the existing jsdom canvas warning.
- Deleting `www/packages/shell/src/testSupport/labBoundary.test.ts` does not remove the import graph harness. `importGraph.ts` is still consumed by `importGraphBoundary.test.ts` and `canvasTailwindFree.test.ts`.
- Boundary scoping is sound for PR 1. Current model to viewers imports are real; current persistence to viewers imports are absent; deferring `model !-> React/Zustand` is justified by `paneRecords.ts` `React.ReactNode`, `canvasStore.ts` `create`, and `capturedRunStore.ts` `create`.
