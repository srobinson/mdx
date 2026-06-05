# Canvas PR 5 Review — Workbench Composition + Runtime Adapter Seam

**PR:** #211 · branch `refactor/canvas-workbench-runtime-seam` · HEAD `317615f` (pre-PR main `ed97a4b`)
**Scope audited:** Tasks 5 + 8a / "PR 5" slice of `docs/superpowers/plans/2026-07-05-canvas-repo-reset.md`
**Diff:** +636/-830 across 44 files
**Reviewer:** transport-matters:general:2:7.2 (adversarial, read-only; authorized throwaway probes, tree left clean)
**Date:** 2026-07-05

## Verdict (initial, 317615f): **PASS** — 0 blockers / 0 majors / 1 minor
## Final verdict (re-review, ad9a45d): **PASS** — 0 blockers / 0 majors / 0 minors

> Re-review below (`## Re-review (ad9a45d)`) confirms both the Minor (dropped
> comments) and the design observation (barrel vs adapter) are resolved. The initial
> findings are retained unedited for the record.

Behavior-preserving decomposition + relocation. `CanvasSurface` is split into
`workbench/CanvasWorkbench` (composition) + `CanvasPaneLayer` (rendering) +
`CanvasCommandDispatcher` (commands); `components/` is deleted; terminal transport is
carved into `infrastructure/runtime`; three new boundary rules are added and bite.
All command and render logic is byte-faithful to pre-split. One Minor: the move
dropped several load-bearing "why" comments. One design observation on the seam shape
(below) for the owner's judgment — not a defect.

Evidence of green:
- `pnpm exec vitest run CanvasWorkbench PaneChrome PaneDock terminalSocket CapturedRunPane TerminalPane CanvasDropTargetOverlay sessionCanvasBoundary` → **57 passed** (8 files; all 6 boundary rules green).
- `pnpm --filter @tm/canvas build` (tsc -b + vite) → **built**, terminal/captured-run chunks present.

---

## Audit findings (five points, hardest first)

### 1. All six boundary rules bite — PASS

`sessionCanvasBoundary.test.ts` holds six rules through the `importGraph` mechanism,
no allow-list. The three pre-existing (`model !-> viewers`, `persistence !-> viewers`,
`dnd !-> viewers/terminal`) still bite; the three new ones proven with injected
violations (probe red, removed, `git status` clean):
- `viewers !-> components`: a throwaway `viewers/__probe__.ts` importing a throwaway
  `components/__probe__.ts` reddened it (`... -> session-canvas/components/__probe__.ts`).
- `viewers/terminal !-> infrastructure/runtime/internal`: probe importing
  `internal/terminalSocket` reddened it.
- **Raw-URL literal guard** (the fragile one): a probe with `"/api/terminal/probe"`
  and `"/v1/runs/abc/socket"` string literals in a viewer reddened it, reporting both.
  It is AST-based (`staticLiteralTexts` over string/template literals), excludes
  `RUNTIME_INTERNAL_ROOT` and test-support, and matches `/api/terminal` or `/v1/runs/`.
  **No false positive on legit usage**: the real URL literals live only in
  `internal/terminalSocket.ts` (excluded); `terminalTransport.ts` re-exports with no
  literals; viewers pass builder callbacks; a `POST /v1/runs` reference in a
  `CapturedRunPane` JSDoc comment is not an AST literal (and lacks the trailing slash).
  Suite green with no probes.

### 2. `components/` is gone — PASS

Folder deleted (not just emptied). Grep of canvas src for any import from
`components/` → none (`workbench/controls/*` and `engine/layout/registry` are unrelated
paths). `viewers !-> components` is therefore enforceable and green.

### 3. CanvasSurface split correctness — PASS (with the Minor below)

Diffed against `git show ed97a4b:.../components/CanvasSurface.tsx`:
- `CanvasCommandDispatcher.ts` owns `useCanvasCommandHandler` + `navigateToRoute` and
  imports **no** pane rendering. All nine command cases are present and identical:
  `spawn` (try/catch), `reset-view`, `focus-picker`, `goto`, `cycle-theme`,
  `toggle-bypass-permissions`, `set-canvas-gesture-modifier`, `select-worktree`
  (replaceState + `initializeCanvas`), `open-session`. Same deps array.
  `navigateToRoute` moved from `RouteSwitcher` byte-identically.
- `CanvasPaneLayer.tsx` contains rendering only: `SortablePane`, `paneBodyDrag`,
  `titleIdForPane`, `useCanvasPaneRenderer` (captured-run placeholder, `renderPaneContent`,
  `PaneWindow`, header dbl-click → expand/frame), and the `LayoutCanvas` element. It
  imports **no** command-dispatch code.
- `CanvasWorkbench.tsx` composes: same store selectors, `dndDeps`, `sortablePaneIds`,
  ResizeObserver effect, and `useCanvasDropTargets` as pre-split; renders
  `AmbientBackdrop`, `CommandCenter` (wired to `handleCommand`), `CanvasDropHint`,
  `CanvasPaneDnd`, and delegates rendering to `CanvasPaneLayer` (overlay = `PaneDock` +
  `CanvasDropTargetOverlay`). No behavior inlined or altered.
- `SessionCanvasRoute.tsx` repointed `CanvasSurface` → `CanvasWorkbench` cleanly.

No command or render logic was dropped or altered.

### 4. Terminal runtime seam — PASS (see design observation)

- `internal/terminalSocket.ts` is a **byte-identical** move of the pre-PR
  `viewers/terminal/terminalSocket.ts` (`diff` empty). URL builders
  (`terminalSocketUrl`, `runTerminalSocketUrl`) and `openTerminalSocket` live there.
- Viewers construct no URLs and open no sockets directly: `TerminalPane` passes
  `buildUrl: terminalSocketUrl`, `CapturedRunPane` passes
  `(cols, rows) => runTerminalSocketUrl(runId, cols, rows)`, `terminalSession.ts`
  consumes `openTerminalSocket`. All imported from the `infrastructure/runtime/terminalTransport`
  barrel, never from `internal/`. The URL-literal guard enforces no raw URLs leak into
  viewers. Behavior to terminal/captured-run is unchanged (byte-faithful move + same
  call sites).

### 5. Deletions safe + no scope bleed — PASS

- `CommandBarSections`, `ThemeCycleButton`, `RouteSwitcher` (+ their tests + CSS)
  deleted with **zero** dangling imports (the only residual textual match is a
  `route.ts` comment warning against `navigateToRoute`). `themeStore.ts` only updates a
  doc comment that referenced the deleted `ThemeCycleButton`.
- CSS trims: `route-switcher.css` deleted; `canvas.css`/`pane-dock.css` trims are for
  the deleted legacy chrome. The shared `canvas-command-bar` base the stress route uses
  is not touched (stress route unaffected; build green).
- No launcher-model change (`launcher/commandModel.ts` not in diff — no PR 6 bleed); no
  `api`/`stream`/`persistence` move (only `runtime`/terminal carved — no PR 7 bleed).

---

## Minor

**M1 — Decomposition dropped load-bearing explanatory comments.** The move preserved
behavior but discarded several "why" comments that guard non-obvious invariants:
- `CanvasPaneLayer.tsx` `SortablePane`: the pre-split "Module-stable adapter so the
  memoized PaneLayer keeps bailing on viewport renders" note is gone — it explained why
  the adapter is module-scoped (a refactor that inlines it would silently regress
  memoization).
- `CanvasWorkbench.tsx`: the `sortablePaneIds` "minus the expanded hero (delivery-only
  target)" note and the `renderPane` "stable across viewport-only renders" note dropped.
- `CanvasCommandDispatcher.ts` `spawn`: the rationale for the try/catch
  (`addCapturedRun` throws on a worktree-less canvas) dropped.

Non-behavioral; suggest restoring the memoization and spawn-throw rationale.
Note: the `select-worktree` double-`?` footgun rationale is **not** lost — it is
preserved on `worktreeSwitchUrl` in `route.ts` (with an explicit "NEVER to
navigateToRoute" warning), so dropping it from the call site is acceptable DRY.

## Design observation (not a scored finding — owner judgment)

The brief describes the seam as an adapter with a `TerminalEndpoint` union, a
`browserTerminalTransport`, and an `infrastructure/runtime/useCapturedRunBinding.ts`
hook. **None of those exist.** What shipped is thinner: `terminalTransport.ts` is a
six-line re-export barrel over `internal/terminalSocket`, and viewers bind by passing
`buildUrl` callbacks into `useTerminalSession`. This still satisfies the enforced
contract — transport is isolated behind `infrastructure/runtime`, viewers hold no URLs
or socket lifecycle, and a future `@tm/runtime` client can swap in behind the barrel
without viewer edits provided the exported signatures hold. Whether a re-export barrel
fully realizes Task 8a's "adapter contract the viewer binds to" (vs a runtime-injectable
adapter) is a design call for you. It is behavior-correct and boundary-green either way.

## Verification note

Probes were authorized by the brief; each was created and removed within a single
command sequence, `git status` clean afterward. The build writes only into the
gitignored `api/src/transport_matters/canvas/` output. Otherwise read-only.

---

# Re-review (ad9a45d)

**Fix delta:** `317615f..ad9a45d`, +228/-47 across 9 files (seam + restored comments only).
The decomposition half passed at 317615f stands; this delta is scoped to (a) restoring
the dropped comments and (b) replacing the re-export barrel with a real adapter.

## Final verdict: **PASS** — 0 blockers / 0 majors / 0 minors

Both re-work items landed cleanly; no regression. Evidence:
- `pnpm exec vitest run terminalTransport terminalSocket CapturedRunPane TerminalPane CanvasWorkbench sessionCanvasBoundary` → **44 passed** (6 files; all 6 boundary rules green).
- `pnpm --filter @tm/canvas build` → **built**.

### 1. Adapter is real, not a barrel — PASS

`infrastructure/runtime/terminalTransport.ts` now defines the contract:
- `TerminalEndpoint = { kind: "local" } | { kind: "captured-run"; runId: string }`.
- `interface TerminalTransport { urlFor(endpoint, cols, rows): string; open(term, options): TerminalSocket }`.
- concrete `browserTerminalTransport: TerminalTransport`, its `urlFor` switching on
  endpoint kind to `terminalSocketUrl` / `runTerminalSocketUrl`, its `open` delegating to
  `openTerminalSocket` — backed by `internal/terminalSocket`.

It is genuinely injectable: `useTerminalSession` takes `transport?: TerminalTransport`
defaulting to `browserTerminalTransport` and calls `transportRef.current.open(term,
{ endpoint, cols, rows, ... })`. A substitute `TerminalTransport` (e.g. a future
`@tm/runtime` Gateway client) drops in via that param with no viewer edits. New
`terminalTransport.test.ts` covers it.

### 2. Viewers bind by endpoint — PASS

- `TerminalPane` passes `endpoint: LOCAL_TERMINAL_ENDPOINT` (`{ kind: "local" } satisfies
  TerminalEndpoint`); it imports only the `TerminalEndpoint` type, no URL builder.
- `CapturedRunPane` passes `endpoint: { kind: "captured-run", runId }` and sources
  `{ runId, spawnError }` from `useCapturedRunBinding`. The inline `buildUrl` callback,
  `ensureRun`/`persistedRunId`/`oscColorReplies` wiring, and `spawnErrorMessage` are gone
  from the viewer.
- `useCapturedRunBinding.ts` wraps exactly that: `ensureRun`, persisted-run-id seed
  (reload attaches on first render, no re-spawn), `oscColorReplies`, and spawn-error
  mapping — a byte-faithful extraction of the previously-inline logic (behavior-preserving).
- `terminalSession.ts` replaced `buildUrl` with `endpoint` + injectable `transport`;
  viewers hold no URL construction or socket lifecycle.

### 3. Comments restored — PASS

All four back, in the correct owners:
- `CanvasCommandDispatcher.ts` `spawn`: the `addCapturedRun`-throws / non-fatal / worktreeId
  rationale.
- `CanvasPaneLayer.tsx` `SortablePane`: the "Module-stable adapter so the memoized PaneLayer
  keeps bailing on viewport renders" note.
- `CanvasWorkbench.tsx`: the `sortablePaneIds` "minus the expanded hero (delivery-only
  target)" note and a `renderPane` viewport-stable note (adapted — `CanvasPaneLayer` now
  owns `renderPane`).

### 4. No regression — PASS

- All SIX boundary rules still bite; the three new ones re-probed red (viewers→components,
  viewers/terminal→runtime/internal, and the raw-URL literal guard catching
  `"/api/terminal/..."` + `"/v1/runs/..."`). Tree clean after probes.
- **No false positive on the new adapter**: `terminalTransport.ts` (scanned, not in
  `internal/`) constructs no raw URL literals — it calls the builders — so the URL guard
  stays green. Full suite green.
- Behavior to terminal/captured-run unchanged (endpoint→urlFor yields the same URLs the
  old `buildUrl` did).
- Decomposition half untouched: the delta is 9 files (seam + comment additions only);
  `components/` is still deleted; the three workbench files received comment-only additions,
  no logic change.

The design observation from the initial review is now resolved: the seam is a real,
injectable adapter contract, satisfying Task 8a.
