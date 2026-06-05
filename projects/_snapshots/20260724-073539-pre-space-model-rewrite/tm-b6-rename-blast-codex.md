# B6 run teardown rename blast radius, Codex

Date: 2026-06-15
Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
Scope: `api/src` and `www/src`, plus colocated tests.

## Verdict

Promoting `terminate` to the product and API verb is consistent with the live run and PTY teardown internals. The rename is broader than the route path: it touches the route handler, response model, exposed run state and reason names, frontend API helper, captured run lifecycle names, health reaper, and tests. `interrupt` is free as a run action name today. Existing `interrupted` usage is Codex turn status, so reserving `interrupt` for ESC or turn halt is aligned.

## Current route reality

The live repo has no `/stop`, `/terminate`, or `/interrupt` run verb route. The teardown surface today is `DELETE /api/runs/{run_id}`.

Evidence:

- `api/src/transport_matters/api/v1/run_routes.py:RUNS_ROUTE_PREFIX` sets `/runs` at line 42.
- `api/src/transport_matters/api/v1/run_routes.py:stop_run` is the teardown route, `@router.delete(RUNS_ROUTE_PREFIX + "/{run_id}")`, lines 338 to 351.
- `www/src/api.ts:deleteRun` calls ``/api/runs/${encodeURIComponent(runId)}`` with `{ method: "DELETE" }`, lines 412 to 419.
- Route grep over tracked `api/src` and `www/src` found no current `/stop`, `/terminate`, or `/interrupt` run verb route. The only `/stop` like hit was a comment in `www/src/session-canvas/components/PaneDock.tsx:22`.

## Blast radius if teardown becomes `terminate`

### API route and schema

These should change if the product verb changes from stop to terminate:

- `api/src/transport_matters/api/v1/run_routes.py:stop_run`, lines 338 to 351. Rename the symbol, route method and path, and manager call. Current behavior returns `StopRunResponse` with `stop_reason="explicit-stop"`.
- `api/src/transport_matters/api/v1/run_routes.py:StopRunResponse`, lines 111 to 116. Rename to `TerminateRunResponse` if the response type follows the verb.
- `api/src/transport_matters/api/v1/run_routes.py:StopRunResponse.stop_reason`, line 116. Decide whether public JSON remains `stopReason` for compatibility inside the run view, or becomes `terminationReason`. Pre release status means either is possible, but the name must be consistent.
- `api/src/transport_matters/api/v1/run_routes.py:RunViewModel.stop_reason`, line 98, and `run_view_model`, lines 247 to 267. This exposes `stopReason` on all run views.
- `api/src/transport_matters/run_manager.py:StopReason`, line 55. Current literal set includes `"explicit-stop"`, `"shutdown"`, `"idle-timeout"`, `"natural-exit"`, and `"failed"`. `explicit-stop` is the product reason most likely to become `explicit-terminate` or equivalent.
- `api/src/transport_matters/run_manager.py:RunState.STOPPING`, line 92. If user visible state vocabulary follows the verb, `"stopping"` should become `"terminating"`; this affects filters and frontend types.
- `api/src/transport_matters/run_manager.py:ManagedRunView.stop_reason`, line 153, and `ManagedRun.stop_reason`, line 173. These are the backend view and state fields copied into the API model.
- `api/src/transport_matters/run_manager.py:RunManager.stop`, lines 354 to 357. Rename to `terminate` or similar. It already delegates to `_teardown_run(..., terminate=True, reason=reason)`.
- `api/src/transport_matters/run_manager.py:RunManager.attach`, around lines 324 to 348. It checks `run.stop_reason == "explicit-stop"` and raises `run_stopped` for a stopped run. If the public error follows the verb, `run_stopped` should become `run_terminated`.
- `api/src/transport_matters/api/v1/run_routes.py:_RUN_MANAGER_HTTP_STATUS`, lines 44 to 54. Contains `"run_stopped"` mapping.

### API health and reaping helper

- `api/src/transport_matters/cli/runs_health.py:reap_run`, lines 103 to 109, documents and calls `DELETE {base_url}/api/runs/{run_id}`. This should call the terminate endpoint once the route changes.
- `api/src/transport_matters/cli/runs_health.py:orphan_candidates`, lines 62 to 100, treats terminal state names as `stopping`, `exited`, and `failed`. If `stopping` becomes `terminating`, update the exclusion set and docs.

### API tests

- `api/src/transport_matters/api/v1/test_run_routes.py:test_post_get_attach_detach_and_delete`, lines 54 to 105. Name, route call, expected `stopReason`, and `explicit-stop` expectation change.
- `api/src/transport_matters/api/v1/test_run_routes.py:test_delete_run_is_idempotent`, lines 148 to 164. Name and route method/path change.
- `api/src/transport_matters/api/v1/test_run_routes.py:test_delete_unknown_run_returns_machine_error`, lines 226 to 235. Route method/path change.
- `api/src/transport_matters/api/v1/test_run_routes.py:test_websocket_stopped_run_sends_typed_error`, lines 262 to 279. Name and expected error `run_stopped` change if error vocabulary follows the verb.
- `api/src/transport_matters/test_run_manager.py:test_explicit_stop_terminates_pty_before_lease_close`, lines 359 to 372. Rename test and reason expectations.
- `api/src/transport_matters/test_run_manager.py:test_explicit_stop_is_idempotent`, lines 375 to 390. Rename and update `manager.stop` calls.
- `api/src/transport_matters/test_run_manager.py:test_close_stops_multiple_running_runs`, lines 393 to 410. Rename if state language follows terminate.
- `api/src/transport_matters/test_run_manager.py:test_attach_errors_distinguish_stopped_and_stale_runs`, lines 413 to 431. Rename and update `run_stopped` if changed.
- `api/src/transport_matters/cli/test_runs_health.py:test_orphan_candidates_excludes_terminal_state_stopping`, lines 92 to 96. Update test name and `state="stopping"` if state changes.
- `api/src/transport_matters/cli/test_runs_health.py:test_reap_run_returns_true_on_200`, lines 210 to 217, plus false cases at lines 220 to 237. Update `DELETE` expectations and response state if changed.

### Frontend API surface

- `www/src/api.ts:deleteRun`, lines 412 to 419. Rename to `terminateRun`, switch from DELETE to the terminate route, and update the user visible fallback `Failed to stop run ${runId}`.
- `www/src/api.ts:RunState`, line 422. Update `"stopping"` to `"terminating"` if backend state changes.
- `www/src/api.ts:RunView.stopReason`, line 444. Rename only if the backend response field changes; otherwise leave as the wire field.
- `www/src/api.ts` comments at lines 411, 425, 457, and 459 mention stop or attach and stop. Update comments with the new product verb.

### Frontend captured run lifecycle

- `www/src/session-canvas/model/capturedRunStore.ts:CapturedRunState.stopRun`, line 73, and implementation lines 138 to 160. Rename to `terminateRun` or `terminateCapturedRun` if public store vocabulary follows the API. It imports and calls `deleteRun` at lines 3, 114, and 149.
- `www/src/session-canvas/model/capturedRunLifecycle.ts:capturedRunLifecyclePolicy`, lines 13 to 16. `onClose` currently calls `useCapturedRunStore.getState().stopRun(ref.runKey)`.
- `www/src/session-canvas/model/canvasStore.ts:useCanvasStore.closePane`, lines 112 to 120, and `closeDockedPane`, lines 123 to 128. These remain pane verbs, but their lifecycle side effect will point at the renamed captured run action.
- `www/src/session-canvas/lab/canvasLabStore.ts:closePane`, around lines 190 to 192, and `closeDockedPane`, around lines 229 to 230. Comments mention captured run hooks killing the run via DELETE and `stopRun`.

### Frontend tests and labels

- `www/src/api.test.ts:describe deleteRun`, lines 156 to 169. Rename describe, test title, helper call, expected method, route, and `stopReason` fixture if the wire field changes.
- `www/src/session-canvas/model/capturedRunStore.test.ts` has `deleteRunMock` setup at lines 9 to 16 and reset at line 38, plus tests at lines 128 to 164 and 223 to 241. Rename `stopRun` titles and calls, and update DELETE wording.
- `www/src/session-canvas/model/canvasStore.test.ts` captured run lifecycle tests at lines 242 to 312 say close pane stops the run. Rename assertions only if the mocked helper is renamed.
- `www/src/session-canvas/lab/canvasLabStore.test.ts` captured run teardown tests at lines 336 to 352 and 402 to 415 mention kills, stops, and DELETE.
- `www/src/session-canvas/components/PaneDock.tsx:PaneDock` uses visible `×` and aria label `Close ${title}`, lines 147 to 158. This is a pane close label, so it need not become terminate unless product copy wants destructive run semantics exposed in the dock.
- `www/src/session-canvas/components/PaneChrome.tsx:PaneChrome` uses visible `Close` and aria label `Close ${title}`, lines 105 to 114. Same note as PaneDock.
- `www/src/session-canvas/components/PaneDock.test.tsx` lines 30 to 40, 86 to 99, tests the dock kill action using the visible `Close lab-2` menu item.
- `www/src/session-canvas/components/pane-dock.css` lines 95 to 121 contains comments and class names around the dock kill button.
- `www/src/session-canvas/lab/canvasLabTypes.ts` lines 45 and 51 mention close or kill semantics for captured runs.

### Deliberate non blast radius

The repo has many unrelated `stop_reason` fields for provider and turn semantics. They should not be renamed as part of the B6 run teardown verb unless the operator wants a global semantic rename. Examples:

- `api/src/transport_matters/ir.py:InternalResponse.stop_reason`, line 160.
- `api/src/transport_matters/codex/events.py:CodexTurnSummary.stop_reason`, line 103.
- `api/src/transport_matters/storage/base.py:ResStats.stop_reason`, line 66.
- `www/src/types/codex.ts` includes Codex turn `stop_reason` fields and the `"interrupted"` status. These are response or turn concepts, not captured run teardown.

## Collision check

### `terminate`

`terminate` is already the internal process teardown vocabulary in the run and PTY path. That makes the product verb coherent.

- `api/src/transport_matters/run_manager.py:RunManager._teardown_run`, lines 482 to 523, accepts `terminate: bool`, sets `RunState.STOPPING` while terminating, and calls `terminate_terminal_pty` when `terminate` is true.
- `api/src/transport_matters/pty_session.py:terminate_terminal_pty`, lines 129 to 133, terminates the child process group then closes the terminal master.
- `api/src/transport_matters/pty_session.py:terminate_process_group`, lines 136 to 160, sends SIGTERM then escalates to SIGKILL.
- `api/src/transport_matters/api/v1/terminal_bridge.py` re exports `terminate_terminal_pty` and `terminate_process_group`, lines 26 to 27 and 73 to 74.
- `api/src/transport_matters/api/v1/terminal.py` aliases `_terminate_terminal_pty` and calls it for terminal cleanup, lines 40 to 41 and 103.
- Broader process supervisors also use terminate, for example `api/src/transport_matters/supervisor_core.py:terminate_all`, line 250. This is adjacent infrastructure vocabulary, not a conflicting product verb.

Verdict: no confusion. The product command `terminate run` would read as the user facing version of the same teardown operation.

### `interrupt`

No current run route, function, or frontend helper uses exact `interrupt` as an action. Existing hits are `interrupted` as a Codex turn status and recovery condition:

- `api/src/transport_matters/codex/protocol.py:CODEX_INTERRUPTED_STATUS`, line 26.
- `api/src/transport_matters/codex/events.py:CodexTurnStatus`, line 23, and validation messages at lines 175 to 181.
- `api/src/transport_matters/codex/derivation_engine.py` emits `status="interrupted"`, lines 500 and 510.
- Frontend color and type handling appears in `www/src/types/codex.ts:CodexTurnStatus`, line 53, `www/src/components/ExchangeDetail.tsx`, line 42, and `www/src/components/ExchangeTurnCard.tsx`, line 99.

Verdict: `interrupt` is currently free for the ESC or turn halt action. Its closeness to the existing `interrupted` turn status is beneficial if the action produces that status.

### `cancel` and `kill`

Avoid `cancel` and `kill` as the product teardown verb.

- `www/src/session-canvas/model/capturedRunStore.ts` uses cancel terminology for the mid spawn race, through `cancelledKeys`, lines 37 to 43, and comments around lines 152 to 155. That is an internal cleanup intent.
- `api/src/transport_matters/run_manager.py` and terminal bridge code use `asyncio` cancellation for tasks, for example `_teardown_run` lines 506 to 511 and rollback lines 533 to 536.
- `api/src/transport_matters/codex/test_transport.py` line 81 has upstream `response.cancel`, which is a turn level Codex concept.
- `kill` appears in low level SIGKILL paths such as `api/src/transport_matters/pty_session.py`, lines 153 to 158, and in dock UI copy or comments such as `www/src/session-canvas/components/PaneDock.tsx`, lines 77 to 80 and 104.

Verdict: `cancel` clashes with race handling and upstream response cancellation. `kill` clashes with destructive UI slang and SIGKILL implementation detail. `terminate` is the cleanest run teardown verb.

## Static verification performed

- Used fmm topology and outlines for `api/src`, `www/src`, `api/v1/run_routes.py`, `run_manager.py`, `pty_session.py`, `www/src/api.ts`, `capturedRunStore.ts`, `PaneDock.tsx`, and `PaneChrome.tsx`.
- Used fmm symbol reads for `stop_run`, `RunManager.stop`, `RunManager._teardown_run`, `terminate_terminal_pty`, `deleteRun`, `useCapturedRunStore`, `capturedRunLifecyclePolicy`, `useCanvasStore`, `PaneDock`, and `PaneChrome`.
- Ran tracked file searches for run route aliases and collision terms. No code was modified and no tests were run because this was a read only blast radius review.
