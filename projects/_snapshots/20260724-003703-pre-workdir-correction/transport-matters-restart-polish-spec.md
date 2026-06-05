# Transport Matters restart polish spec

Status: implementation ready. Verified against `feat/desktop-detach` HEAD `5aaddb1` on 2026-06-20 for PR #160.

## Road test verdict

Both defects are real restart lifecycle gaps exposed by slice 1 and slice 2. Reconnect is not feasible cheaply with the current architecture. The KISS fix is to make the hosted Electron viewer exit when its backend dies, then prune remembered captured run panes whose process resident run ids are absent on the fresh backend.

## Issue 1: lingering Electron app

Root cause confirmed. `api/src/transport_matters/cli/channel_cmd.py:stop` resolves the channel record and delegates to `api/src/transport_matters/cli/desktop_runtime.py:stop_desktop_record`, which kills the recorded backend pid. That pid comes from `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached`. The viewer comes from `api/src/transport_matters/cli/desktop_cmd.py:spawn_detached_electron`, uses `subprocess.Popen(... start_new_session=True)`, and the Electron pid is discarded.

The detached viewer enters the hosted path through `desktop/src/main.ts:registerDesktopLifecycleFromEnv` when Python supplies `DESKTOP_ROUTE_URL`. Slice 2 added `desktop/src/main.ts:registerHostedBackendLivenessPoll`; after three failed `/health` probes it calls `window.close()`. `desktop/src/main.ts:bindHostedWindowLifecycle` still keeps the macOS default: `window-all-closed` only quits outside Darwin. On macOS, closing the only window leaves the old app process alive, so CMD Tab shows a second preview app after restart.

Minimal fix: backend loss in a hosted single backend viewer must quit the app. Pass a `quitHostedApp` callback from `desktop/src/main.ts:registerHostedDesktopLifecycle` into `registerHostedBackendLivenessPoll` and call it at the failure threshold instead of `window.close()`. Keep the existing probe source, debounce, and first load gate. Initial load failure remains owned by `desktop/src/window.ts:registerHostedWindowPolicy`.

Also add a hosted only `quitOnWindowAllClosed` option to `desktop/src/main.ts:bindHostedWindowLifecycle` and pass true from `registerHostedDesktopLifecycle`. Leave the default path unchanged so `desktop/src/main.ts:registerAppLifecycle` preserves the foreground, backend owning app lifecycle.

Do not record or kill the Electron pid for this fix. The app already knows the backend is gone, and quitting the app is less state than extending the runtime record.

## Issue 2: stale captured runs on relaunch

Root cause confirmed. The frontend remembers two separate things in browser storage.

Canvas panes are persisted through `www/src/session-canvas/model/canvasStore.ts:useCanvasStore`, `www/src/session-canvas/model/canvasStore.persistence.ts:createCanvasStorePersistOptions`, and `www/src/session-canvas/persistence/canvasPersistOptions.ts:partializeCanvasState`. A captured pane ref stores `kind: "captured-run"` plus `runKey` via `www/src/session-canvas/model/paneRecords.ts:PaneContentRef`.

The actual backend run id is persisted separately by `www/src/session-canvas/model/capturedRunStore.ts:useCapturedRunStore` under `transport-matters-captured-run`. On render, `www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx:CapturedRunPane` seeds `runId` from the persisted entry and `ensureRun` returns that id without calling `www/src/api.ts:createCapturedRun`. `www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx:AttachedRunTerminal` then builds `WS /v1/runs/{id}/terminal` via `www/src/session-canvas/viewers/terminal/terminalSocket.ts:runTerminalSocketUrl`.

The backend cannot satisfy that id after restart. `api/src/transport_matters/main.py:lifespan` creates a fresh `RunManager` on `app.state`; `api/src/transport_matters/run_manager.py:RunManager.__init__` initializes an empty `_runs` dict; `api/src/transport_matters/run_manager.py:RunManager.close` tears down live runs during shutdown. `api/src/transport_matters/api/v1/run_routes.py:run_terminal_socket` calls `bridge_attached_run_terminal`, which calls `api/src/transport_matters/run_manager.py:RunManager.attach`, which calls `api/src/transport_matters/run_manager.py:RunManager.get`. A fresh backend raises `run_not_found` for the old id.

Reconnect verdict: not feasible cheaply. A real reconnect would need a durable supervisor contract for run process identity, PTY handles, terminal fanout, leases, and scrollback rehydration. Current run ownership is intentionally process resident. The cheap API is validation, not reconnect.

Minimal fix: prune stale remembered captured runs before captured terminal content mounts. Reuse `www/src/api.ts:listRuns` once on canvas startup, but make the gate explicit. `www/src/session-canvas/SessionCanvasRoute.tsx:SessionCanvasRoute` owns a local reconciliation state, for example `capturedRunReconciliation: "pending" | "released"`, initialized to `pending` only when `www/src/session-canvas/model/capturedRunStore.ts:useCapturedRunStore.getState().runs` has remembered ids. While pending, pass `capturedRunsReady={false}` into `www/src/session-canvas/components/CanvasSurface.tsx:CanvasSurface` and through `useCanvasPaneRenderer`, so captured run pane content renders a lightweight placeholder instead of `www/src/session-canvas/viewers/registry.tsx:renderPaneContent`. This prevents `www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx:CapturedRunPane` and `AttachedRunTerminal` from mounting, so no first commit WebSocket opens. Picker, transcript, resource, and exchange panes still render immediately; only `captured-run` content is gated.

At reconciliation start, snapshot prune candidates from the current captured run store before issuing `listRuns`: keep a map of `runKey -> runId` for the ids that existed at start. After `listRuns` resolves, build the live run id set and drop only candidates that were in that start snapshot and absent from the live set. A run spawned or persisted during the round trip was not a start candidate, so it survives even if absent from the response. Add a non terminating `dropRun(runKey)` action to `capturedRunStore`. Add a canvas action, for example `dropCapturedRunPane(runKey)` on `www/src/session-canvas/model/canvasStore.ts:useCanvasStore`, that removes open and docked `captured-run` refs with that key and replans the layout without invoking the close lifecycle, so no doomed `terminateRun` call fires. On success or failure, set the gate to released. If `listRuns` fails, keep state and retry on the next route mount; never delete local panes on a transient API failure.

## Slice interaction

Slice 1 remains correct: channel stop kills the backend only. Slice 2 remains the right seam: keep the shared health probe from `desktop/src/backendHealth.ts:isBackendHealthy`, but change the terminal action from close window to quit hosted app. The stale run fix is frontend only; the backend already returns the needed truth through `/v1/runs` and `run_not_found`.

## Slice plan and gates

Slice A: hosted app quit. Touch `desktop/src/main.ts` and `desktop/src/main.test.ts`. Tests: backend liveness failure calls quit; transient failures still recover; pending timeout still clears; hosted `window-all-closed` quits on Darwin only when the hosted option is set; foreground default remains unchanged. Gates: root `just check`; root `just test`; `cd desktop && just check`; `cd desktop && just package-smoke`.

Slice B: stale captured run pruning. Touch `www/src/api.ts` only if `listRuns` needs a small helper extension; otherwise use it as is. Touch `capturedRunStore`, `canvasStore`, `SessionCanvasRoute`, `CanvasSurface`, and adjacent tests. Tests: while reconciliation is pending, captured run pane content does not mount and no `/v1/runs/{id}/terminal` socket opens; picker and transcript panes still render; persisted run id present in `/v1/runs` stays and reattaches after gate release; absent start candidate removes both the run mapping and open or docked pane ref; a run added during the `listRuns` round trip is not pruned; API failure keeps state and releases the gate; no spawn occurs while pruning. Gates: root `just check`; root `just test`; `cd www && just test`.

Live smoke after both slices: run `just channel-restart preview` twice. Expected: preview backend PID changes, exactly one preview app icon remains in CMD Tab, no stale captured run panes render, no failed reattach loop appears, and launching a new captured run from the clean canvas still works.

## Traceability

- stop backend -> `api/src/transport_matters/cli/channel_cmd.py:stop`; `api/src/transport_matters/cli/desktop_runtime.py:stop_desktop_record`
- detached viewer spawn -> `api/src/transport_matters/cli/desktop_cmd.py:spawn_detached_electron`
- hosted path selection -> `desktop/src/main.ts:registerDesktopLifecycleFromEnv`
- hosted liveness -> `desktop/src/main.ts:registerHostedBackendLivenessPoll`; `desktop/src/backendHealth.ts:isBackendHealthy`
- macOS app survival seam -> `desktop/src/main.ts:bindHostedWindowLifecycle`
- canvas ref memory -> `www/src/session-canvas/model/canvasStore.persistence.ts:createCanvasStorePersistOptions`; `www/src/session-canvas/persistence/canvasPersistOptions.ts:partializeCanvasState`
- run id memory -> `www/src/session-canvas/model/capturedRunStore.ts:useCapturedRunStore`
- reconcile gate -> `www/src/session-canvas/SessionCanvasRoute.tsx:SessionCanvasRoute`; `www/src/session-canvas/components/CanvasSurface.tsx:CanvasSurface`
- stale attach path -> `www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx:CapturedRunPane`; `www/src/session-canvas/viewers/terminal/terminalSocket.ts:runTerminalSocketUrl`; `api/src/transport_matters/api/v1/run_routes.py:run_terminal_socket`; `api/src/transport_matters/run_manager.py:RunManager.get`
