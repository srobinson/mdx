---
title: B3b director surface — list/attach/stop managed runs in the canvas lab
type: sessions
tags: [frontend, transport-matters, plan-b, b3, b3b, captured-run, run-manager, director]
summary: Lab director surface lists /api/runs and attaches/stops them, reusing B3a's per-pane attach-by-runId path; PR #75.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Added a **director surface** to the canvas lab: a live roster of server-managed
captured runs (`GET /api/runs`) with attach-from-list and stop-from-list. An
operator can pick up a running agent they have no pane for, restoring it into a
captured pane bound to its *existing* run id (never a re-spawn). Builds directly
on B3a (PR #74) and reuses its attach-by-runId machinery.

Branch `b3b-director`, sha `dcaacf0`, PR #75. One PR.

## Architecture Decisions

- **`api.ts` `listRuns(filters?)`** → `GET /api/runs?{cli,cwd,state}` → typed
  `RunView[]`. Added `RunView` / `RunState` / `RunFilters` mirroring the backend
  `RunViewModel` (camelCase aliases; `exclude_none` optionals are optional in TS).
  Read-only — listing never spawns.
- **`capturedRunStore.adoptRun(provider, runId)`** is the seam that makes attach
  reuse spawn machinery instead of duplicating it. It binds a pane to an existing
  run id without a POST, returns the key the pane should own, and is **idempotent
  on runId** (reuses the key a sibling pane already owns). It persists like a
  spawned run, so a reload re-attaches via the existing `ensureRun` (which resolves
  the stored id, no spawn). Net effect: the pane WS attaches to the real PTY and
  the backend viewer count ticks up — no second run.
- **`canvasLabStore.attachCapturedRun(provider, runId)`** opens a captured pane via
  `adoptRun` + `seedContentPane`; if a pane for that key is already open (re-click,
  or we spawned it), it focuses it (`focusNode`) instead of stacking a duplicate
  viewer onto one PTY.
- **`DirectorPanel.tsx`** (new, ~120 LOC): local fetch state (`runs`, `loading`,
  `error`, a `stopping` Set for per-row disable). GET on mount + manual Refresh.
  Attach → `attachCapturedRun`; Stop → `deleteRun` then Refresh. Rendered as a
  full-width row in the lab command bar (sibling of `CommandBarSections`), styled
  with existing design tokens only.

## Key reuse / DRY

No parallel attach/stop logic: attach routes through `capturedRunStore` (same path
B3a uses and Stuart live-confirmed); stop reuses `deleteRun`. The director never
spawns an SDK/API client — it binds to the real managed CLI run.

## Performance Notes

Not a perf task. Bundle: `CanvasLabRoute` chunk 18.08 kB (gzip 6.28); `api` chunk
3.88 kB (gzip 1.19). No measurable regression.

## Deviations from Spec

None. Placement chose "a new DirectorPanel component" (sanctioned by the brief)
rendered in the lab command bar as an always-visible full-width row, rather than
behind the existing Layout disclosure (avoids a misleading "Layout" label).

## Open Items

- `viewerCount` in the list only updates on Refresh (mount + manual). A live SSE/WS
  push for the roster would make it real-time; not required by B3b.
- Live e2e (real browser + real agent) not run this session; correctness rests on
  green gates + unit/integration tests + the already-shipped, tested backend
  routes (#72/#73). A human/peer live-confirm pass mirrors the B3a flow.
