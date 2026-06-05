---
title: Pane Dock S2 — reload-persist minimized state
type: sessions
tags: [frontend, transport-matters, canvas-lab, dock, zustand, persistence]
summary: Persist a per-run minimized flag so a browser reload re-docks a minimized captured pane instead of reopening it.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-10
updated: 2026-06-10
---

# Pane Dock S2 — reload-persist minimized state

PR #77 on branch `feat/canvas-dock-s2-reload-persist` (commit 4f1e2ff), built on S1 (#76).
Spec: `www/.../NOTES/captured-canvas/10-pane-dock-design.md` §I (S2 section authoritative).

## Summary

S1 shipped the dock but left a stated caveat: the mount effect reopened **every** persisted
captured run as an active pane, so a minimized agent reappeared open after a browser reload. S2
closes that. A captured run now carries a persisted `minimized` flag; on mount, flagged runs come
back **docked** and the rest reopen. Restore re-attaches by the kept runId (no re-spawn), exactly
as in S1.

Behavioral contract, all covered by unit tests:
- minimize → reload → still docked
- restore → reopens; reload after restore → open
- close / dock-row [×] → gone; reload → still gone
- agent restore re-attaches by runId, no re-spawn

## Architecture Decisions

- **Flag lives on the captured-run record** (`capturedRunStore.CapturedRunRecord.minimized?`),
  reusing the existing zustand-persist store + B3a runId persistence. No new persistence path was
  added (the lab store stays unpersisted) — this respected the "no parallel persistence path"
  guardrail.
- **Symmetric lifecycle seam.** Extended `PaneLifecyclePolicy` with `onRestore` so the
  minimize/restore/close trio is all seam-dispatched. `labLifecycle` registers captured-run
  `onMinimize` (set flag) / `onRestore` (clear flag) / `onClose` (stopRun, which deletes the record
  so the flag goes with it). `restorePane` now dispatches `onRestore` through `resolvePaneLifecycle`
  — **zero `kind ===` branches in the store**, matching the S1 design lock.
- **`dockCapturedPane`** is the reload counterpart to `restoreCapturedPane`: idempotent, parks a
  captured ref in the dock without opening a pane. Extracted a shared `capturedRunRef(provider,
  runKey)` helper so the open and docked reload paths can't drift (DRY).
- **Mid-spawn minimize is deferred, not dropped** (corrected after review — see below). A minimize
  racing an in-flight spawn has no established record yet, so the flag is held as a
  `minimizedPendingKeys` intent (mirroring `cancelledKeys`) and applied when the spawn resolves and
  persists the record, so it still docks on reload. Close still wins if it also races (its cancel
  clears the intent — a key is cancelled OR minimize-pending, never both).
- **Storage version 2 → 3** with the existing shape-tolerant migrate. Pre-S2 records (no flag) load
  clean and reopen (never lost), proven by a migration test.

## Performance Notes

No perf-sensitive change. Build confirms `capturedRunStore` stays isolated in its own 1.04 kB lazy
chunk (out of the prod `index` bundle) — the isolation guardrail held; no new prod-side importer.

## Deviations from Spec

- The orchestrator directive mentioned "persist the docked set for plain panes as the doc
  specifies." The authoritative S2 spec scopes persistence to **captured runs only** (the lab store
  is unpersisted by design; demo/terminal panes are session-ephemeral in S1 too). Persisting plain
  panes would require a new persistence path, which the "no parallel persistence path" guardrail
  forbids. Scoped to captured runs and flagged in the PR body. No code deviation from the doc.
- Pane labels (e.g. "Claude-1") are not persisted, so a docked-on-reload entry shows the
  provider-derived title. This matches S1's reopened-pane behavior (label already lost on reload).

## Review follow-up (blocker fixed, commit 575cb6d)

Orchestrator review caught a real blocker: the **initial cut no-op'd a mid-spawn minimize** (no
record yet → flag dropped → `ensureRun` resolve persisted the record without `minimized` → reload
reopened instead of docking). I had wrongly written this off as an "accepted tradeoff" leaning on the
"only persist established runs" guardrail. That guardrail means *don't persist a runId-less run*, not
*drop the user's minimize intent*. Fix mirrors the `cancelledKeys` companion-race pattern with a
`minimizedPendingKeys` intent. Tests added: minimize-during-spawn docks on reload; close-wins-over-
mid-spawn-minimize; restore-during-spawn drops the intent. Lesson: a stated behavioral contract
("minimize → reload → still docked") must hold on edges too — an edge where it fails is a bug, not a
documentable limitation.

## Open Items

- Prod adoption of the dock (transcript/resource/exchange/picker panes, picker-close reopen) remains
  a later slice, out of S1/S2 scope.
- If plain-pane reload persistence is ever wanted, it needs a deliberate decision to persist the lab
  store (new path) — currently out of scope by the guardrail.
