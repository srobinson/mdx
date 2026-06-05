# Canvas PR 7 Review — Isolate Infrastructure

**PR:** #213 · branch `refactor/canvas-infrastructure` · HEAD `1c5476d` (pre-PR main `33b90e4`)
**Scope audited:** Task 8 / "PR 7" slice of `docs/superpowers/plans/2026-07-05-canvas-repo-reset.md`
**Diff:** +88/-68 across 62 files
**Reviewer:** transport-matters:general:2:7.2 (adversarial, read-only; one authorized probe, tree left clean)
**Date:** 2026-07-05

## Verdict: **PASS** — 0 blockers / 0 majors / 0 minors

Pure relocation + import repoint: `api/` → `infrastructure/api/`, `stream/` →
`infrastructure/stream/`, `persistence/` → `infrastructure/persistence/` (terminal
runtime already moved in PR 5). No logic edited in any moved file. Verified by
content-diffing every changed moved file, a full stale-import sweep, a boundary probe
at the new persistence root, and green tests/typecheck/build.

Evidence:
- `pnpm exec vitest run sessionClient sessionEventReducer canvasPanePersistence useSessionEventStream sessionCanvasBoundary` → **31 passed** (5 files; all 6 boundary rules green).
- `pnpm --filter @tm/canvas typecheck` → exit 0. `pnpm --filter @tm/canvas build` → built.

---

## Audit findings (four points, hardest first)

### 1. Pure move, no logic drift — PASS

Git tracks the moves as renames. The files with a non-zero diff changed **only**
relative-import depth (`../` → `../../` / `../../../`), no logic:
- `infrastructure/persistence/canvasPanePersistence.ts`: content-diff vs
  `33b90e4:.../persistence/canvasPanePersistence.ts` shows only the `../../engine` →
  `../../../engine`, `../../engine/layout` → `../../../engine/layout`, `../model/paneRecords`
  → `../../model/paneRecords` fixups (one formatter reflow of the layout import). Every
  function (`seedPaneFromRecord`, `rebuildPersistedCanvasState`, `readPersistedPanes`,
  `dropOrphanedRects`, the guards) is unchanged.
- `infrastructure/persistence/canvasPersistOptions.ts`: only the four `../../` →
  `../../../` / `../` → `../../` import fixups.
- `infrastructure/api/launchResolution.ts`: only `../route` → `../../route`.
- The named pure-rename files are **byte-identical** old vs new (`diff -q` clean):
  `api/sessionClient.ts`, `stream/sessionEventReducer.ts`, `persistence/storageKeys.ts`
  (and the remaining 0-change renames: `resourceContent.ts`, `sessionEvents.ts`,
  `canvasCacheStorage.ts`, `mapIrToChat.ts`, `transcriptDenylist.ts`,
  `useSessionEventStream.ts`).

### 2. All consumers repointed, no stale paths — PASS

- Stale-import sweep of the whole canvas src for imports of the old
  `session-canvas/{api,stream,persistence}/` locations → **none**.
- The old `api/`, `stream/`, `persistence/` folders under `session-canvas/` are deleted
  (absent on disk).
- Every consumer (`model/`, `workbench/`, `viewers/`, `launcher/`, `hooks/`, `stores/`,
  `testUtils.tsx`, `keybindings/gestures.test.ts`) now imports `infrastructure/*`.
- The `@tm/canvas` public export subpath `./storageKeys` in `package.json` is repointed to
  `./src/session-canvas/infrastructure/persistence/storageKeys.ts` (the shell's
  storage-key collision test consumes this — repoint keeps it resolvable).
- `typecheck` and `build` green corroborate no dangling specifier.

### 3. Boundary — PASS

`sessionCanvasBoundary.test.ts` `PERSISTENCE_ROOT` is repointed to
`infrastructure/persistence` (not the deleted `session-canvas/persistence`, which would
scan an absent dir and go vacuously green). **Proven non-vacuous**: an injected
`infrastructure/persistence/__probe__.ts` importing `../../viewers/registry` reddened
`keeps persistence files from importing viewer modules`
(`... -> session-canvas/viewers/registry.tsx`); probe removed, tree clean. The other
five rules (`model !-> viewers`, `dnd !-> viewers/terminal`, `viewers !-> components`,
`viewers/terminal !-> infrastructure/runtime/internal`, raw-URL guard) operate on roots
untouched by this PR and stayed green (5 passed with the probe, all 6 green clean). None
silently broke from the moves.

### 4. Task-8 constraints + no scope bleed — PASS

- **Model DTOs stayed in `model/`.** The moved persistence files import model types
  (`CanvasPaneRef`, `DockedPane`, `PaneContentRef`, `isPaneContentRef` from
  `../../model/paneRecords`) but define none; no model type was dragged into
  `infrastructure/`.
- **React only in hooks.** Grep of `infrastructure/**` for a React import in a non-hook,
  non-test file → none (`useSessionEventStream.ts` is the sole hook and is allowed).
- **No rename** of `session-canvas` (PR 8 not attempted).
- **Only `api`/`stream`/`persistence` moved.** `perf/`, `hooks/`, `engine/`, `model/`,
  `viewers/`, etc. are not relocated; their diffs are import-repoint-only.

---

## Verification note

The one probe was created and removed within a single command sequence; `git status`
clean afterward. The build writes only into the gitignored
`api/src/transport_matters/canvas/` output. Otherwise read-only (`git show` for pre-PR
state, no branch switch).
