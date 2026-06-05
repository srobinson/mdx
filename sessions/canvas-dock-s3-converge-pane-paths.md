---
title: Canvas Dock S3 — converge pane create/restore onto one persisted path
type: sessions
tags: [frontend, transport-matters, canvas-lab, zustand, persistence, dock, dry]
summary: Persisted the full canvasLabStore record set and converged create+restore onto one seedPaneFromRecord primitive so every pane kind round-trips a reload (PR #78).
status: active
source: frontend-engineer
confidence: high
created: 2026-06-10
updated: 2026-06-10
---

## Summary

Shipped Dock S3 (PR #78, branch `feat/canvas-dock-s3-converge-pane-paths`, commit `e7bc60c`
off main `0a11da5`). Converged the canvas lab's pane **create** and **restore** onto a single
path and persisted the whole `canvasLabStore`, fixing two Stuart-found reload bugs whose shared
root cause was a divergent create-vs-restore path:

1. Regular + terminal panes (and docked panes of any non-captured kind) vanished on reload —
   `canvasLabStore` was unpersisted; only `capturedRunStore.minimized` survived, so only captured
   runs came back.
2. A reloaded captured pane dropped its label (`Claude-1` → `Claude`) because the old
   `capturedRunRef` reconstructed the ref without the unpersisted `label`, and the title viewer
   falls back to the bare provider name.

## Architecture Decisions

- **One creation primitive.** `seedPaneFromRecord(state, paneId, ref, rect)` is the sole
  node+ref seed (upsert node at rect + set ref; no planning/focus). The spawn path layers
  create-only concerns via `spawnPaneLayout` (= seedPaneFromRecord + focus + `planLayout` so a
  new pane flies into its slot) and is shared by `addPane`/`addTerminal`/`addCapturedRun` AND the
  in-session `restorePane`. The reload path calls `seedPaneFromRecord` directly at each persisted
  rect (no replan; `organize()` reflows on mount). One create path, distinct from reload only in
  that reload skips replanning.
- **Persisted lab store.** Wrapped `canvasLabStore` in `persist()` under a new
  `FRONTEND_STORAGE_KEYS.canvasLabStore` (`"transport-matters-canvas-lab"`), version 1.
  `partialize` → `{ contentRefs (with label), paneRects (open nodes only), docked (all kinds),
  paneCounters, nextPaneIndex }`. A custom `mergeLabState` rebuilds the canvas (open panes from
  `paneRects` + `contentRefs`) and the dock (`docked`) by folding `seedPaneFromRecord` over the
  records. Fully shape-tolerant (every field `?? default`) so a missing/partial payload (first
  load after upgrade has no key) hydrates clean. Transient camera/animation/focus intentionally
  not persisted.
- **Two-store composition.** The lab record gives kind+label+rect+docked; `capturedRunStore`
  keeps the live `runId`+`minimized` keyed by the same `runKey`. A reloaded captured pane
  re-attaches by id when its viewer mounts (existing B3a/`ensureRun` path) — no re-spawn.
  `capturedRunStore` was left untouched, so S1 in-flight cancellation + S2 minimize-intent are
  intact.
- **Deleted divergence.** Removed `capturedRunRef`, `restoreCapturedPane`, `dockCapturedPane`,
  and `CanvasLabRoute`'s fresh-demo seed effect + captured-only rebuild effect. Reload restore is
  now owned by store hydration, not a mount `useEffect`.

## Performance Notes

No perf-targeted work. `seedPaneFromRecord`'s reload fold uses `nextPaneZ` over the accumulating
node map (O(n²) in pane count, but n is tiny for a lab canvas). `paneRects` collection filters to
`lifecycle === "open"` so closing/docked panes never resurrect.

## Deviations from Spec

- **First-load behavior change (flagged to orchestrator/Stuart).** Deleting the fresh-demo seed
  effect per the directive means a first-ever lab visit now starts empty (panes spawn on demand).
  The motivating upside: an emptied canvas now correctly stays empty across reload instead of
  resurrecting demo panes. A persistence-aware first-load seed (demos as store initial state,
  overwritten by `merge` when persisted data exists) is an easy follow-up if demos-on-first-load
  is wanted.

## Open Items

- Optional: re-add a persistence-aware first-load demo seed if Stuart wants the dense
  expand-mode stress case back on first visit.
- The wire-vs-transcript diff direction is unrelated; not touched.

## Verification

All gates green: `vite build`, `biome check .`, `tsc -b` typecheck, full `vitest` (641 tests),
`rg capturedRunRef src` → 0, one `seedPaneFromRecord` primitive used by both paths.
`canvasLabStore.ts` = 678 LOC (< 700). New tests cover all eight gates: three-kind reload
restore, title/label survival incl. `Claude-1`, post-reload counter continuation (`Claude-3`),
captured re-attach by runId (no re-spawn), minimized-captured stays docked, all-kind docked
round-trip (terminal + regular + captured) at store and route level, and pre-S3/partial-payload
clean load.
