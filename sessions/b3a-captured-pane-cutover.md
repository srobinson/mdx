---
title: B3a — Captured Pane Cutover to Managed /api/runs (Per-Pane Runs)
type: sessions
tags: [frontend, transport-matters, plan-b, run-manager, captured-pane, websocket, zustand]
summary: Cut the captured terminal pane off the /api/captured-runs bridge onto the server-managed /api/runs run-manager, with each pane owning its own run (per-pane runKey), and deleted the bridge.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

B3a retires the `/api/captured-runs` compatibility bridge and moves the captured terminal pane (lab) onto the server-managed run-manager (`/api/runs`, landed in PR #73). Branch `b3a-pane`, PR #74, sha `d03531a`.

The load-bearing decision: **each captured pane owns its own backend run.** Identity is a per-pane `runKey` (`provider:uuid`), so two same-provider panes are two independent runs with two PTYs and isolated input.

## Architecture Decisions

- **Per-pane identity, not per-provider.** First cut keyed `runId` by `provider`; because the RunManager multiplexes viewers onto one PTY, two same-provider panes shared a terminal ("type into one types into all"). Corrected to a per-pane `runKey` minted by `createCapturedRunKey(provider)` (`provider:crypto.randomUUID()`), carried **on the captured-run content ref** (viewer reads its own key), with the lab pane id == runKey (single identity, trivial idempotent restore).
- **Persisted run registry.** New `capturedRunStore` (zustand `persist` via the existing `createFrontendPersistStorage` seam): `runs: Record<runKey, {provider, runId}>`. `ensureRun(runKey, provider, cwd?)` reuses a persisted/in-flight run else spawns once (module-level pending map dedupes React 18 StrictMode double-mount per pane). `clearRun(runKey)` forgets + DELETEs that one run.
- **Lifecycle seam.** Spawn = `POST /api/runs {cli,cwd?}` (HTTP errors surface as a spawn banner); attach = `WS /api/runs/{runId}/terminal?cols&rows`. `useTerminalSession` left UNTOUCHED — the pane renders the attach-terminal child only once `runId` resolves (spawn does not need cols/rows; attach + resize fixes size). WS close = detach (run persists headless); explicit `closePane` → `clearRun(ref.runKey)` DELETEs only that run; reload reconciles persisted `runs` → `restoreCapturedPane` → re-attach by id.
- **Backend deletion + test relocation.** Deleted `api/v1/captured_terminal.py` + router include + the now-dead `run_routes.captured_spawn_request`. Relocated the real-PTY harness (`install_real_pty_manager`, `_python_client_argv`) into `test_run_routes.py`; re-homed nested-capture-only / passthrough / launch-failure coverage onto `_spawn_request` + `POST /api/runs`. resize and ctrl-c/job-control stay covered via the shared bridge in `test_terminal.py`.
- **Renames:** `capturedTerminalSocketUrl` → `runTerminalSocketUrl`; `capturedRunFrames` (`captured-run.*`) → `runTerminalFrames` (`run.error`); added `api.createCapturedRun` / `api.deleteRun`.

## Performance Notes

No perf-specific work. Bundle: terminal-pane chunk ~87.75 kB gzip (xterm-dominated), well under the 200 kB budget. The lazy split for the terminal panes is unchanged.

## Deviations from Spec

- The directive's deliverable #2/#3 said "persist runId in the pane record / for this pane." The first implementation mis-read this as per-provider; corrected to literal per-pane after the user live-flagged the shared-input bug. No dedupe (the original lab allowed multiple same-provider panes; the product wants independent runs).
- Removed `run_routes.captured_spawn_request` (dead once the bridge is gone) per DRY/dead-code, folding its coverage onto `_spawn_request`. The directive only named the bridge file; this is the honest "delete the old path completely."

## Open Items

- **DONE.** Peer FE (Codex, 1:3.2) reviewed; Stuart live-confirmed the panes work (independent runs, no shared input); orchestrator (1:2.1) review applied. Final sha `073cd43`, PR #74.
- **Review fix 1 (a2ea2c9, peer 1:3.2):** the shared viewer registry still keyed the captured-run `paneId` by `provider` (`captured-run:${provider}`), contradicting the per-pane invariant — latent (lab assigns its own ids; production never spawns captured refs) but a real landmine via `paneIdForRef`/`createPaneRecord`. Fixed: `paneId: (ref) => ref.runKey`, dropped the dead `CAPTURED_RUN_PANE_PREFIX`, added a same-provider-distinct-runKeys regression. Now `paneIdForRef(capturedRef) === lab pane id === runKey` end to end.
- **Review fix 2 (073cd43, orchestrator 1:2.1) — MAJOR:** close-during-in-flight-spawn race in `capturedRunStore.clearRun`. It deleted the pending key and returned while `runs[runKey]` was still absent; the in-flight `POST /api/runs` then resolved and persisted the run with no DELETE → orphaned live server run + a zombie restored on reload. Fixed with a per-key cancellation token (`cancelledKeys` Set): `clearRun` marks an in-flight key cancelled (leaving the pending promise); the spawn resolve does an atomic `cancelledKeys.delete(key)` → if cancelled, `DELETE /api/runs/{runId}` and skip persisting. Same shape as the B1b-1 backend close/spawn rollback. Regression: close while POST in flight, resolve after → asserts DELETE fired and `runs[runKey]` not persisted (fails-before/passes-after). The synchronous StrictMode dedup and this post-resolve cancellation are two distinct, composing guards.
- Server-restart survival (run rediscovery) is deferred (Plan-B B5); a persisted `runId` whose backend run died (server restart) attaches → `run.error run_not_found` → banner; user closes + respawns. Acceptable for v1 (survive browser reload, not server restart).

## Gates

- grep `captured-runs` → ZERO across tracked source + rebuilt bundle.
- www: typecheck ✓ · biome ✓ · 608 tests ✓ · build ✓.
- api: `just ci` → 1292 passed (ruff + mypy + import-boundary + pytest) ✓.
