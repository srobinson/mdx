# Canvas PR 8 Review — Dissolve `session-canvas`

**PR:** #214 · branch `refactor/canvas-rename-workbench` · HEAD `573a111` (pre-PR main `8bd175b`)
**Scope audited:** Task 9 / "PR 8" slice + the owner-resolved shape (dissolve `session-canvas/`, lift children to `canvas/src/`, `workbench/` a sibling)
**Diff:** 208 files
**Reviewer:** transport-matters:general:2:7.2 (adversarial, read-only; authorized probes, tree left clean)
**Date:** 2026-07-05

## Verdict: **PASS** — 0 blockers / 0 majors / 0 minors

Behavior-preserving structural move. `session-canvas/` is dissolved; its children
(`model`, `viewers`, `dnd`, `interactions`, `launcher`, `infrastructure`, `hooks`,
`perf`, `workbench`) are lifted to `www/packages/canvas/src/`, with `workbench/` a
sibling of the rest (no `workbench/workbench` nesting). All six boundary rules bite at
the new roots; the public export surface resolves; docs are de-staled; no behavior
changed. One architectural observation (unscored) below.

Evidence:
- `pnpm exec vitest run importGraphBoundary browserIdentity CanvasWorkbench canvasStore sessionCanvasBoundary` → **53 passed** (4 files) + the boundary suite green (6/6).
- `pnpm --filter @tm/canvas build` → built. `git status` clean.

---

## Audit findings (five points, hardest first)

### 1. All six boundary rules bite at the new roots — PASS

`sessionCanvasBoundary.test.ts` now sits at `canvas/src/` (`CANVAS_SRC =
dirname(import.meta.url)`), and its roots retarget the lifted folders: `MODEL_ROOT`,
`PERSISTENCE_ROOT = infrastructure/persistence`, `DND_ROOT`, `COMPONENTS_ROOT`,
`VIEWERS_ROOT`, `TERMINAL_VIEWER_ROOT`, `RUNTIME_INTERNAL_ROOT =
infrastructure/runtime/internal`. Describe block renamed "canvas boundary".

Clean run: all six green — including `viewers !-> components`, which evaluates **green,
not throw**, now that `components/` does not exist (`sourceFiles` runs over the existing
`VIEWERS_ROOT`; the absent `COMPONENTS_ROOT` is only a containment target, never
`stat`ed). Injected-violation probe: one throwaway violation per rule (model→viewers,
persistence→viewers, dnd→viewers/terminal, viewers→components via a throwaway
`components/__probe__.ts`, viewers/terminal→infrastructure/runtime/internal, and a
raw-URL literal) reddened **all six** simultaneously; probes removed, tree clean.

### 2. Repo-wide `session-canvas` == 0, honestly — PASS

`rg -n "session-canvas" --glob '!docs/superpowers/**' --glob '!**/.archive/**' .` → exit
1, **zero** matches. The excludes hide nothing shipped: every remaining match is under
`docs/superpowers/` — the reset plan doc plus two icon-system planning docs
(`2026-07-05-canvas-icon-system{,-design}.md`), all historical planning artifacts, none
in product code. The `session-canvas/` folder is gone (absent on disk; no empty dir).

### 3. Move fidelity, no behavior drift — PASS

- Lifted files are byte-identical apart from relative-import depth fixups:
  `viewers/registry.tsx` and `infrastructure/persistence/storageKeys.ts` are
  **byte-identical** old vs new; `workbench/CanvasWorkbench.tsx` and `model/canvasStore.ts`
  changed only import specifiers (`../../stores/*` → `../stores/*`, `../route` →
  `./route` / `../workbench/route`) with a formatter reorder. No logic edited.
- **hooks/ merge is clean**: `canvas/src/hooks/` holds both the pre-existing
  `useThemeTokens.ts` + `useThemeTokens.test.tsx` **and** the merged session hooks
  (`useFullscreen`, `useLaunchSession`, `useLocalFileContent`, `useResourceContent`,
  `useSessionEvents`, `useSessions`). No clobber.
- Loose files placed sanely: `workbench/` holds `SessionCanvasRoute.tsx` + `route.ts` +
  `canvas.css`; `canvas/src/` holds `OWNERSHIP.md`, `sessionCanvasBoundary.test.ts`,
  `testUtils.tsx`.
- `SessionCanvasRoute.tsx` kept its name (no `CanvasRoute.tsx` rename — out of scope).

### 4. Import-graph integrity — PASS

`importGraphBoundary.test.ts` and `browserIdentity.test.ts` green. The deep-import
sentinel is now `@tm/canvas/testUtils` (post-dissolve path; `testUtils.tsx` lifted to
`canvas/src/`) and is asserted under "fails closed for deep package imports outside the
exports map" — `testUtils` is **not** in the `package.json` exports map (`.`,
`./ambient/createAmbientBackground`, `./index.css`, `./storageKeys` only), so the "deep
imports blocked" assertion still means something. The exports map is repointed and all
four targets resolve on disk; **no exports path references `session-canvas`**
(`./storageKeys` → `./src/infrastructure/persistence/storageKeys.ts`). Public surface
behavior unchanged.

### 5. Docs de-staled + no scope bleed — PASS

- `canvas/CLAUDE.md` now describes the real structure (`workbench/`, `model/`, `viewers/`,
  `launcher/`, `infrastructure/`), the stale `session-canvas/lab/**` boundary bullet is
  **deleted**, the `useFullscreen` reference de-pathed, and the storageKeys owner line →
  `infrastructure/persistence/storageKeys.ts`.
- `NOW.md` and the inspector comments (`inspector/src/hooks/useFullscreen.ts`,
  `inspector/src/stores/persistence.ts`) are **comment-only** JSDoc path updates — no
  behavior, not scope bleed.
- No file-level rename beyond the folder dissolve; no behavior change anywhere (build +
  boundary + import-graph green).

---

## Design observation (unscored — owner-approved placement)

`route.ts` (the launch-context contract: `CanvasLaunchContext`, `parseCanvasLaunchContext`,
`defaultCanvasId`, plus `worktreeSwitchUrl`) was a neutral top-level sibling pre-dissolve
(`session-canvas/route.ts`) and is now placed under `workbench/`. Seven files outside
`workbench/` import `workbench/route` — `model/{canvasStore,canvasState,canvasStoreLifecycle,
canvasActions,paneRecords}.ts`, `infrastructure/api/launchResolution.ts`,
`hooks/useLaunchSession.ts` — so `model`/`infrastructure`/`hooks` now import upward into
`workbench/`. This is behavior-preserving (the `model→route` dependency pre-existed; only
route's folder moved), follows the plan's "workbench owns route launch context," is
pre-approved by the review brief as a sane placement, and is caught by no boundary rule.
Flagging only for future awareness: if `workbench/` is ever meant to be a pure
composition apex (importable only downward), the pure launch-context contract in
`route.ts` would want a neutral home. Not a defect for this PR.

## Verification note

Probes were authorized by the brief; each created and removed within a single command
sequence, `git status` clean afterward. Build writes only into the gitignored
`api/src/transport_matters/canvas/` output. Otherwise read-only.
