---
title: Transport Matters Restart Polish Lifecycle Findings
type: research
tags: [transport-matters, desktop, restart, run-manager, frontend-state]
summary: Hosted Electron must quit on backend death, while stale captured run ids need a reconcile before attach gate because RunManager reconnect is not cheap.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Executive Summary

A road test of `just channel-restart preview` exposed two lifecycle gaps in PR #160. The detached hosted Electron viewer closes its window after backend death but does not quit on macOS, and the frontend restores captured run panes from localStorage even though fresh backends have no process resident `RunManager` entries for old run ids.

Primary spec: `~/.mdx/projects/transport-matters-restart-polish-spec.md`. Correction round applied on 2026-06-20: captured run reconciliation must gate captured pane content before first attach, and pruning must snapshot candidates before `listRuns`.

## Project Metadata

- Language: Python FastAPI backend, TypeScript React frontend, TypeScript Electron shell.
- Branch: `feat/desktop-detach`.
- Verified HEAD: `5aaddb1`.
- fmm: `.fmm.db` present; fmm indexed 855 files and 135,957 LOC.
- Build and gate recipes: root `just check`, root `just test`, `cd api && just ci`, `cd desktop && just check`, `cd desktop && just package-smoke`, `cd www && just test`.

## Architecture

The detached desktop launch path is owned by `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached`. It starts the backend as the recorded process, writes a runtime record through `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord`, then starts Electron through `api/src/transport_matters/cli/desktop_cmd.py:spawn_detached_electron` without keeping the Electron pid.

The hosted Electron path is selected by `desktop/src/main.ts:registerDesktopLifecycleFromEnv` when `DESKTOP_ROUTE_URL` exists. Hosted liveness is in `desktop/src/main.ts:registerHostedBackendLivenessPoll` and uses `desktop/src/backendHealth.ts:isBackendHealthy`.

Captured run panes have split state. Canvas pane refs live under `www/src/session-canvas/model/canvasStore.ts:useCanvasStore` and persist through `www/src/session-canvas/model/canvasStore.persistence.ts:createCanvasStorePersistOptions`. Backend run ids live under `www/src/session-canvas/model/capturedRunStore.ts:useCapturedRunStore` and are consumed by `www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx:CapturedRunPane`.

Backend run ownership is process resident. `api/src/transport_matters/main.py:lifespan` creates a new `api/src/transport_matters/run_manager.py:RunManager` for each backend process, and `RunManager.__init__` initializes an empty `_runs` map.

## Key Patterns

- Prefer the local lifecycle owner over extra process records. The hosted Electron app already observes backend death, so app quit is simpler than recording and later killing an Electron pid.
- Keep validation separate from recovery. `/v1/runs` can cheaply validate live run ids, but cannot rehydrate PTYs, leases, fanout, or process identity.
- Prune stale UI state explicitly. A stale captured run id should remove its canvas pane and captured run mapping without firing the close lifecycle or a doomed terminate call.

## Detailed Findings

### Lingering Electron process

Confirmed root cause: `api/src/transport_matters/cli/channel_cmd.py:stop` kills the backend through `api/src/transport_matters/cli/desktop_runtime.py:stop_desktop_record`. The hosted viewer remains because `desktop/src/main.ts:registerHostedBackendLivenessPoll` calls `window.close()` and `desktop/src/main.ts:bindHostedWindowLifecycle` preserves macOS last window behavior.

Minimal fix: pass a hosted quit callback from `desktop/src/main.ts:registerHostedDesktopLifecycle` into `registerHostedBackendLivenessPoll` and call it after the failure threshold. Add a hosted only `quitOnWindowAllClosed` option to `bindHostedWindowLifecycle`; keep the foreground `registerAppLifecycle` default unchanged.

### Stale captured runs

Confirmed root cause: `www/src/session-canvas/model/capturedRunStore.ts:useCapturedRunStore` returns a persisted run id without spawning. `www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx:AttachedRunTerminal` then opens a WebSocket for the old run id. Fresh backend attach fails through `api/src/transport_matters/api/v1/run_routes.py:run_terminal_socket`, `api/src/transport_matters/run_manager.py:RunManager.attach`, and `RunManager.get`.

Reconnect feasibility verdict: not cheap. A durable supervisor and PTY rehydration contract would be required. The KISS fix is startup reconciliation with an explicit captured content gate: `www/src/session-canvas/SessionCanvasRoute.tsx:SessionCanvasRoute` owns pending versus released state, captured run content is withheld through `www/src/session-canvas/components/CanvasSurface.tsx:CanvasSurface`, and non captured panes render immediately. Snapshot `runKey -> runId` candidates before `www/src/api.ts:listRuns`; after the response, prune only start snapshot candidates absent from the live set. Runs spawned during the round trip are not candidates and survive.

## Dependencies

Critical dependencies for this slice are Electron app lifecycle events, Zustand persistence, FastAPI WebSocket routing, and the in process `RunManager` state model.

## Relevance to Helioy

This reinforces the Helioy pattern that local UI persistence must distinguish durable product entities from process resident handles. Captured run ids are handles, not durable sessions.

## Open Questions

- Should hosted manual window close always quit the app on macOS for detached channel viewers? The spec recommends yes through a hosted only option.
- Should future reconnect work live in Transport Matters or a higher level Little Organs supervisor? Current evidence points to a supervisor boundary.
