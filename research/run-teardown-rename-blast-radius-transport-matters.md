---
title: Run Teardown Rename Blast Radius in Transport Matters
type: research
tags: [transport-matters, b6, api, runs, naming]
summary: Static code review found that stop to terminate is coherent with PTY teardown internals but spans route, schema, frontend helpers, lifecycle stores, health reaping, and tests.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Executive Summary

Transport Matters currently tears down captured runs through `DELETE /api/runs/{run_id}` rather than a `/stop` route. Renaming the B6 teardown verb to `terminate` is consistent with the existing run manager and PTY internals, where `terminate=True` leads to `terminate_terminal_pty()`.

## Project Metadata

- Language: Python backend, TypeScript React frontend.
- Backend framework: FastAPI, Pydantic.
- Frontend framework: React with Zustand state stores.
- Scope reviewed: `api/src`, `www/src`, and colocated tests.
- Method: fmm topology, file outlines, symbol reads, dependency graph checks, then targeted tracked file searches.

## Architecture

Captured run creation and teardown cross the backend run routes, `RunManager`, PTY helpers, frontend API client, and canvas lifecycle policies.

- Backend route entry: `api/src/transport_matters/api/v1/run_routes.py:stop_run` at lines 338 to 351.
- Backend state owner: `api/src/transport_matters/run_manager.py:RunManager.stop` at lines 354 to 357, with teardown in `RunManager._teardown_run` at lines 482 to 523.
- PTY termination helper: `api/src/transport_matters/pty_session.py:terminate_terminal_pty` at lines 129 to 133.
- Frontend API helper: `www/src/api.ts:deleteRun` at lines 412 to 419.
- Frontend lifecycle hook: `www/src/session-canvas/model/capturedRunLifecycle.ts:capturedRunLifecyclePolicy` at lines 13 to 16.

## Key Patterns

- The public route currently uses REST deletion, while internals already use termination vocabulary for the destructive process operation.
- Pane close remains a UI action. It calls captured run teardown as a lifecycle side effect, so `Close` labels do not need automatic rename to `Terminate`.
- `interrupt` is already semantically represented as the result status `interrupted` for Codex turns, making it a good candidate for turn halt rather than run teardown.

## Detailed Findings

### Rename blast radius

Backend API and models:

- `api/src/transport_matters/api/v1/run_routes.py:stop_run`, lines 338 to 351, should become the terminate route handler if B6 changes `POST /v1/runs/{id}/stop` to `/terminate`.
- `api/src/transport_matters/api/v1/run_routes.py:StopRunResponse`, lines 111 to 116, should become `TerminateRunResponse` if response naming follows the verb.
- `api/src/transport_matters/api/v1/run_routes.py:RunViewModel.stop_reason`, line 98, exposes `stopReason` on run views.
- `api/src/transport_matters/run_manager.py:StopReason`, line 55, includes `explicit-stop`, the reason most likely to change.
- `api/src/transport_matters/run_manager.py:RunState.STOPPING`, line 92, exposes `stopping`; if state vocabulary follows the verb, update to `terminating`.
- `api/src/transport_matters/run_manager.py:ManagedRunView.stop_reason`, line 153, and `ManagedRun.stop_reason`, line 173, carry reason state through the manager view.
- `api/src/transport_matters/run_manager.py:RunManager.stop`, lines 354 to 357, is the backend manager method to rename.
- `api/src/transport_matters/cli/runs_health.py:reap_run`, lines 103 to 109, calls `DELETE /api/runs/{run_id}` and must switch to the terminate endpoint.

Frontend API and lifecycle:

- `www/src/api.ts:deleteRun`, lines 412 to 419, should become a terminate helper and use the new route and method.
- `www/src/api.ts:RunState`, line 422, includes `stopping`.
- `www/src/api.ts:RunView.stopReason`, line 444, mirrors the backend field.
- `www/src/session-canvas/model/capturedRunStore.ts:CapturedRunState.stopRun`, line 73, and implementation lines 138 to 160, should follow the new helper name.
- `www/src/session-canvas/model/capturedRunLifecycle.ts:capturedRunLifecyclePolicy`, lines 13 to 16, calls `stopRun` on pane close.
- `www/src/session-canvas/model/canvasStore.ts:useCanvasStore.closePane`, lines 112 to 120, and `closeDockedPane`, lines 123 to 128, remain pane lifecycle verbs.
- `www/src/session-canvas/components/PaneChrome.tsx:PaneChrome`, lines 105 to 114, and `www/src/session-canvas/components/PaneDock.tsx:PaneDock`, lines 147 to 158, expose `Close` labels. These are pane labels, not run API labels.

Tests:

- `api/src/transport_matters/api/v1/test_run_routes.py:test_post_get_attach_detach_and_delete`, lines 54 to 105.
- `api/src/transport_matters/api/v1/test_run_routes.py:test_delete_run_is_idempotent`, lines 148 to 164.
- `api/src/transport_matters/api/v1/test_run_routes.py:test_websocket_stopped_run_sends_typed_error`, lines 262 to 279.
- `api/src/transport_matters/test_run_manager.py:test_explicit_stop_terminates_pty_before_lease_close`, lines 359 to 372.
- `api/src/transport_matters/test_run_manager.py:test_explicit_stop_is_idempotent`, lines 375 to 390.
- `api/src/transport_matters/cli/test_runs_health.py:test_reap_run_returns_true_on_200`, lines 210 to 217.
- `www/src/api.test.ts:describe deleteRun`, lines 156 to 169.
- `www/src/session-canvas/model/capturedRunStore.test.ts`, lines 128 to 164 and 223 to 241.
- `www/src/session-canvas/model/canvasStore.test.ts`, lines 242 to 312.
- `www/src/session-canvas/lab/canvasLabStore.test.ts`, lines 336 to 352 and 402 to 415.

### Collision check

`terminate` is consistent:

- `api/src/transport_matters/run_manager.py:RunManager._teardown_run`, lines 482 to 523, already uses `terminate: bool` and calls the PTY termination path.
- `api/src/transport_matters/pty_session.py:terminate_terminal_pty`, lines 129 to 133, and `terminate_process_group`, lines 136 to 160, are direct implementation matches.
- `api/src/transport_matters/api/v1/terminal_bridge.py` re exports termination helpers at lines 26 to 27 and 73 to 74.
- `api/src/transport_matters/api/v1/terminal.py` aliases `_terminate_terminal_pty` at lines 40 to 41 and calls it at line 103.

`interrupt` is free as a run action name:

- No exact run action, route, or frontend helper named `interrupt` exists in tracked `api/src` and `www/src`.
- Existing `interrupted` usage is Codex turn status, such as `api/src/transport_matters/codex/protocol.py:CODEX_INTERRUPTED_STATUS` at line 26 and `api/src/transport_matters/codex/events.py:CodexTurnStatus` at line 23.
- Frontend handles `interrupted` as a turn status in `www/src/types/codex.ts`, line 53, and visual mapping in `www/src/components/ExchangeDetail.tsx`, line 42.

Avoid `cancel` and `kill` as product teardown names:

- `www/src/session-canvas/model/capturedRunStore.ts` uses cancellation for mid spawn race cleanup through `cancelledKeys`, lines 37 to 43 and 152 to 155.
- `api/src/transport_matters/run_manager.py` uses task cancellation during teardown, lines 506 to 511 and 533 to 536.
- `kill` appears as SIGKILL implementation detail in `api/src/transport_matters/pty_session.py`, lines 153 to 158, and dock UI slang in `www/src/session-canvas/components/PaneDock.tsx`, lines 77 to 80 and 104.

## Dependencies

- FastAPI routing owns HTTP verb and path semantics.
- Pydantic response models shape public JSON field names.
- Zustand stores own captured run lifecycle state and pane close side effects.

## Relevance to Helioy

The rename supports a cleaner operator model: `terminate` for destructive run teardown, `interrupt` for stopping the active turn, and `close` for pane UI lifecycle. This separation matches the existing captured canvas behavior and should reduce ambiguity in future API and UI specifications.

## Open Questions

- Should run view field `stopReason` remain as a generic lifecycle reason, or become `terminationReason` as part of the pre release breaking change?
- Should public state `stopping` become `terminating`, or should state vocabulary stay lifecycle neutral while only the action verb changes?
- Should pane dock comments and CSS class names using `kill` be normalized now, or left as internal UI slang until a broader copy pass?
